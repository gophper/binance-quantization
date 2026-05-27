# -*- coding: utf-8 -*-
"""市场状态切换策略回测。

策略逻辑：
1. 基础入场仍使用 RSI(6) + Wilder 的极端超卖买点：RSI < 8；
2. 默认按熊市反弹策略处理：RSI > 62 直接止盈；
3. 若持仓已获得足够利润，且月线 RSI 仍处低位但开始回升，同时日线重回 MA20 上方，
   则切换到修复/趋势持有模式；
4. 切换后改为多指标退出：RSI > 62 且 (跌破 MA10 或 MACD 死叉)；
5. 交易结束后，需等待 RSI > 10 才允许下一次重新入场。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd

from backtest_engine import BacktestResult, Trade, YEAR_DAYS
from config import MARKET_REGIME_CONFIG
from indicators import IndicatorCalculator
from optimized_backtest import OptimizedRsiBacktester, PeriodWindow

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketRegimeStrategyConfig:
    """市场状态切换策略配置。"""

    profile_name: str = "daily"
    symbol: str = "BTCUSDT"
    timeframe: str = "1d"
    rsi_period: int = 6
    buy_threshold: float = 8.0
    entry_rebound_threshold: float | None = None
    entry_requires_price_rise: bool = False
    bear_sell_threshold: float = 62.0
    bear_exit_requires_confirmation: bool = False
    recovery_sell_threshold: float = 62.0
    reentry_reset_rsi: float = 10.0
    switch_profit_threshold: float = 0.10
    recovery_monthly_rsi_cap: float = 35.0
    exit_ma_period: int = 10
    trend_ma_period: int = 20
    regime_daily_mid_period: int = 50
    regime_daily_long_period: int = 200
    stop_loss_percent: float = 0.10
    commission: float = 0.0002
    slippage: float = 0.0001
    initial_capital: float = 10000.0
    max_holding_bars: int | None = None
    warmup_days: int = 450

    @classmethod
    def for_profile(cls, profile_name: str) -> "MarketRegimeStrategyConfig":
        """按策略档位生成配置。"""
        profiles = MARKET_REGIME_CONFIG.get("profiles", {})
        if profile_name not in profiles:
            raise ValueError(f"未知策略档位: {profile_name}")
        return cls(profile_name=profile_name, **profiles[profile_name])


class MarketRegimeSwitchBacktester:
    """市场状态切换回测器。"""

    def __init__(self, config: MarketRegimeStrategyConfig | None = None):
        self.config = config or MarketRegimeStrategyConfig.for_profile("daily")
        self.output_dir = Path("data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_loader = OptimizedRsiBacktester()

    def fetch_spot_klines(
        self,
        symbol: str,
        interval: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> pd.DataFrame:
        """复用现货 K 线抓取逻辑。"""
        return self.data_loader.fetch_spot_klines(symbol, interval, start_time, end_time)

    def prepare_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """补充日线指标列。"""
        prepared = df.copy()
        close = prepared["close"]
        prepared["rsi"] = IndicatorCalculator.calculate_rsi(close, self.config.rsi_period)
        prepared["ma10"] = close.rolling(self.config.exit_ma_period).mean()
        prepared["ma20"] = close.rolling(self.config.trend_ma_period).mean()
        prepared["ma50"] = close.rolling(50).mean()
        prepared["ma200"] = close.rolling(200).mean()
        prepared["ema12"] = close.ewm(span=12, adjust=False).mean()
        prepared["ema26"] = close.ewm(span=26, adjust=False).mean()
        prepared["macd"] = prepared["ema12"] - prepared["ema26"]
        prepared["macd_signal"] = prepared["macd"].ewm(span=9, adjust=False).mean()
        return prepared

    def run_period_backtest(self, period: PeriodWindow) -> BacktestResult:
        """按指定区间执行回测。"""
        start_ts = pd.Timestamp(period.start)
        end_ts = pd.Timestamp(period.end)
        fetch_start = start_ts - pd.Timedelta(days=self.config.warmup_days)
        source_df = self.fetch_spot_klines(
            symbol=self.config.symbol,
            interval=self.config.timeframe,
            start_time=fetch_start,
            end_time=end_ts,
        )
        if source_df.empty:
            raise ValueError(f"{period.name} 没有可用数据")

        prepared_df = self.prepare_indicators(source_df)
        history_prefix_df = prepared_df[prepared_df["open_time"] < start_ts].reset_index(drop=True)
        execution_df = prepared_df[prepared_df["open_time"] >= start_ts].reset_index(drop=True)
        if execution_df.empty:
            raise ValueError(f"{period.name} 在执行区间内没有可用数据")

        return self.run_backtest_on_dataframe(
            execution_df,
            period.name,
            history_prefix_df=history_prefix_df,
        )

    def run_backtest_on_dataframe(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        history_prefix_df: pd.DataFrame | None = None,
    ) -> BacktestResult:
        """在已准备好的 DataFrame 上运行回测。"""
        if df.empty:
            raise ValueError("回测数据为空")

        history_prefix_df = history_prefix_df if history_prefix_df is not None else pd.DataFrame(columns=df.columns)
        current_capital = self.config.initial_capital
        capital_curve = [current_capital]
        closed_trades: List[Trade] = []
        position: Trade | None = None
        armed_for_entry = True
        oversold_ready = False
        recovery_mode = False
        entry_bar_index: int | None = None

        for index in range(1, len(df)):
            if history_prefix_df.empty:
                history_df = df.iloc[: index + 1].reset_index(drop=True)
            else:
                history_df = pd.concat([history_prefix_df, df.iloc[: index + 1]], ignore_index=True)
            current = df.iloc[index]
            previous = df.iloc[index - 1]
            current_time = pd.Timestamp(current["close_time"]).to_pydatetime()
            close_price = float(current["close"])
            rsi = current["rsi"]

            if pd.isna(rsi):
                capital_curve.append(self._calculate_equity(current_capital, position, close_price))
                continue

            market_state, _ = self._classify_market_state(history_df)

            if position is None and not armed_for_entry and rsi > self.config.reentry_reset_rsi:
                armed_for_entry = True
                oversold_ready = False

            if position:
                exit_mark_price = close_price * (1 - self.config.slippage - self.config.commission)
                price_return = (exit_mark_price / position.entry_price) - 1
                holding_bars = index - entry_bar_index if entry_bar_index is not None else 0
                macd_death_cross = (
                    current["macd"] < current["macd_signal"]
                    and previous["macd"] >= previous["macd_signal"]
                )
                ma_break = pd.notna(current["ma10"]) and close_price < float(current["ma10"])
                bear_exit_signal = rsi > self.config.bear_sell_threshold
                if self.config.bear_exit_requires_confirmation:
                    bear_exit_signal = bear_exit_signal and (ma_break or macd_death_cross)

                should_switch = (
                    not recovery_mode
                    and market_state in {"recovery", "bull"}
                    and price_return >= self.config.switch_profit_threshold
                )
                if should_switch:
                    recovery_mode = True

                if price_return <= -self.config.stop_loss_percent:
                    position = self._close_position(
                        position=position,
                        exit_price=close_price,
                        exit_time=current_time,
                        exit_reason="STOP_LOSS",
                    )
                    closed_trades.append(position)
                    current_capital += position.pnl
                    position = None
                    entry_bar_index = None
                    armed_for_entry = False
                    oversold_ready = False
                    recovery_mode = False
                elif self.config.max_holding_bars is not None and holding_bars >= self.config.max_holding_bars:
                    position = self._close_position(
                        position=position,
                        exit_price=close_price,
                        exit_time=current_time,
                        exit_reason="MAX_HOLD",
                    )
                    closed_trades.append(position)
                    current_capital += position.pnl
                    position = None
                    entry_bar_index = None
                    armed_for_entry = False
                    oversold_ready = False
                    recovery_mode = False
                elif not recovery_mode and bear_exit_signal:
                    position = self._close_position(
                        position=position,
                        exit_price=close_price,
                        exit_time=current_time,
                        exit_reason="BEAR_RSI_SELL",
                    )
                    closed_trades.append(position)
                    current_capital += position.pnl
                    position = None
                    entry_bar_index = None
                    armed_for_entry = False
                    oversold_ready = False
                    recovery_mode = False
                elif recovery_mode and rsi > self.config.recovery_sell_threshold and (ma_break or macd_death_cross):
                    exit_reason = "RECOVERY_MA_BREAK_SELL" if ma_break else "RECOVERY_MACD_SELL"
                    position = self._close_position(
                        position=position,
                        exit_price=close_price,
                        exit_time=current_time,
                        exit_reason=exit_reason,
                    )
                    closed_trades.append(position)
                    current_capital += position.pnl
                    position = None
                    entry_bar_index = None
                    armed_for_entry = False
                    oversold_ready = False
                    recovery_mode = False

            if position is None and armed_for_entry:
                if self.config.entry_rebound_threshold is None:
                    if rsi < self.config.buy_threshold:
                        position = self._open_position(
                            entry_time=current_time,
                            entry_price=close_price,
                            capital=current_capital,
                        )
                        entry_bar_index = index
                        oversold_ready = False
                        recovery_mode = False
                else:
                    if rsi < self.config.buy_threshold:
                        oversold_ready = True
                    rebound_signal = (
                        oversold_ready
                        and pd.notna(previous["rsi"])
                        and previous["rsi"] < self.config.entry_rebound_threshold <= rsi
                    )
                    price_confirmed = (
                        not self.config.entry_requires_price_rise
                        or close_price > float(previous["close"])
                    )
                    if rebound_signal and price_confirmed:
                        position = self._open_position(
                            entry_time=current_time,
                            entry_price=close_price,
                            capital=current_capital,
                        )
                        entry_bar_index = index
                        oversold_ready = False
                        recovery_mode = False

            capital_curve.append(self._calculate_equity(current_capital, position, close_price))

        if position:
            last_row = df.iloc[-1]
            position = self._close_position(
                position=position,
                exit_price=float(last_row["close"]),
                exit_time=pd.Timestamp(last_row["close_time"]).to_pydatetime(),
                exit_reason="END_OF_BACKTEST",
            )
            closed_trades.append(position)
            current_capital += position.pnl
            capital_curve[-1] = current_capital

        return self._build_result(
            df=df,
            strategy_name=strategy_name,
            final_capital=current_capital,
            trades=closed_trades,
            capital_curve=capital_curve,
        )

    def run_period_suite(self, periods: Iterable[PeriodWindow]) -> List[dict]:
        """执行一组区间回测并导出结果。"""
        records = []
        for period in periods:
            result = self.run_period_backtest(period)
            records.append(
                {
                    "period": period.name,
                    "start": period.start,
                    "end": period.end,
                    "config": {
                        "profile_name": self.config.profile_name,
                        "timeframe": self.config.timeframe,
                        "buy_threshold": self.config.buy_threshold,
                        "entry_rebound_threshold": self.config.entry_rebound_threshold,
                        "entry_requires_price_rise": self.config.entry_requires_price_rise,
                        "bear_sell_threshold": self.config.bear_sell_threshold,
                        "bear_exit_requires_confirmation": self.config.bear_exit_requires_confirmation,
                        "recovery_sell_threshold": self.config.recovery_sell_threshold,
                        "switch_profit_threshold": self.config.switch_profit_threshold,
                        "recovery_monthly_rsi_cap": self.config.recovery_monthly_rsi_cap,
                        "max_holding_bars": self.config.max_holding_bars,
                    },
                    **result.to_dict(include_trades=True),
                }
            )

        output_path = self.output_dir / f"market_regime_backtest_{self.config.profile_name}.json"
        output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return records

    def _classify_market_state(self, history_df: pd.DataFrame) -> Tuple[str, dict]:
        """基于月线修复程度判断市场状态。"""
        if history_df.empty:
            return "bear", {}

        price_series = (
            history_df.loc[:, ["open_time", "close"]]
            .drop_duplicates(subset=["open_time"])
            .sort_values("open_time")
            .set_index("open_time")["close"]
        )
        daily_closes = price_series.resample("1D").last().dropna()
        if daily_closes.empty:
            return "bear", {}

        current_daily_close = float(daily_closes.iloc[-1])
        daily_ma20 = daily_closes.rolling(self.config.trend_ma_period).mean()
        daily_ma50 = daily_closes.rolling(self.config.regime_daily_mid_period).mean()
        daily_ma200 = daily_closes.rolling(self.config.regime_daily_long_period).mean()
        latest_daily_ma20 = daily_ma20.iloc[-1] if len(daily_ma20) else np.nan
        latest_daily_ma50 = daily_ma50.iloc[-1] if len(daily_ma50) else np.nan
        latest_daily_ma200 = daily_ma200.iloc[-1] if len(daily_ma200) else np.nan

        month_closes = daily_closes.resample("MS").last().dropna()
        monthly_rsi = IndicatorCalculator.calculate_rsi(month_closes, self.config.rsi_period)
        monthly_ma5 = month_closes.rolling(5).mean()
        monthly_ma10 = month_closes.rolling(10).mean()

        latest_rsi = monthly_rsi.iloc[-1] if len(monthly_rsi) else np.nan
        prev_rsi = monthly_rsi.iloc[-2] if len(monthly_rsi) > 1 else np.nan
        latest_close = month_closes.iloc[-1] if len(month_closes) else np.nan
        latest_ma5 = monthly_ma5.iloc[-1] if len(monthly_ma5) else np.nan
        latest_ma10 = monthly_ma10.iloc[-1] if len(monthly_ma10) else np.nan

        recovery = (
            pd.notna(latest_rsi)
            and pd.notna(prev_rsi)
            and latest_rsi <= self.config.recovery_monthly_rsi_cap
            and latest_rsi > prev_rsi
            and pd.notna(latest_daily_ma20)
            and current_daily_close > float(latest_daily_ma20)
        )
        bull = (
            pd.notna(latest_rsi)
            and pd.notna(latest_ma5)
            and pd.notna(latest_ma10)
            and pd.notna(latest_daily_ma200)
            and latest_rsi > 50
            and latest_close > latest_ma10
            and latest_ma5 > latest_ma10
            and current_daily_close > float(latest_daily_ma200)
        )

        if bull:
            state = "bull"
        elif recovery:
            state = "recovery"
        else:
            state = "bear"

        return state, {
            "monthly_rsi": latest_rsi,
            "monthly_rsi_prev": prev_rsi,
            "monthly_close": latest_close,
            "monthly_ma5": latest_ma5,
            "monthly_ma10": latest_ma10,
            "daily_close": current_daily_close,
            "daily_ma20": latest_daily_ma20,
            "daily_ma50": latest_daily_ma50,
            "daily_ma200": latest_daily_ma200,
        }

    def _open_position(self, entry_time: datetime, entry_price: float, capital: float) -> Trade:
        actual_entry_price = entry_price * (1 + self.config.slippage + self.config.commission)
        quantity = capital / actual_entry_price
        return Trade(
            entry_time=entry_time,
            entry_price=actual_entry_price,
            quantity=quantity,
            direction="LONG",
            status="OPEN",
        )

    def _close_position(
        self,
        position: Trade,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
    ) -> Trade:
        actual_exit_price = exit_price * (1 - self.config.slippage - self.config.commission)
        position.exit_time = exit_time
        position.exit_price = actual_exit_price
        position.pnl = (actual_exit_price - position.entry_price) * position.quantity
        position.pnl_percent = (actual_exit_price / position.entry_price) - 1
        position.status = "CLOSED"
        position.exit_reason = exit_reason
        position.holding_days = max((position.exit_time - position.entry_time).days, 0)
        return position

    def _build_result(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        final_capital: float,
        trades: List[Trade],
        capital_curve: List[float],
    ) -> BacktestResult:
        start_time = pd.Timestamp(df["open_time"].iloc[0]).to_pydatetime()
        end_time = pd.Timestamp(df["close_time"].iloc[-1]).to_pydatetime()
        total_return = (final_capital - self.config.initial_capital) / self.config.initial_capital

        elapsed_days = max((end_time - start_time).total_seconds() / 86400, 1 / YEAR_DAYS)
        years = elapsed_days / YEAR_DAYS
        annual_return = (
            (final_capital / self.config.initial_capital) ** (1 / years) - 1 if years > 0 else 0.0
        )

        winning_trades = [trade for trade in trades if trade.pnl > 0]
        losing_trades = [trade for trade in trades if trade.pnl < 0]
        total_profit = sum(trade.pnl for trade in winning_trades)
        total_loss = abs(sum(trade.pnl for trade in losing_trades))

        return BacktestResult(
            symbol=self.config.symbol,
            strategy_name=strategy_name,
            start_time=start_time,
            end_time=end_time,
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=self._calculate_max_drawdown(capital_curve),
            sharpe_ratio=self._calculate_sharpe_ratio(capital_curve),
            win_rate=len(winning_trades) / len(trades) if trades else 0.0,
            profit_factor=total_profit / total_loss if total_loss > 0 else (999.0 if total_profit > 0 else 0.0),
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=float(np.mean([trade.pnl_percent for trade in winning_trades])) if winning_trades else 0.0,
            avg_loss=float(np.mean([trade.pnl_percent for trade in losing_trades])) if losing_trades else 0.0,
            trades=trades,
        )

    def _calculate_equity(self, current_capital: float, position: Trade | None, close_price: float) -> float:
        if not position:
            return current_capital
        marked_exit_price = close_price * (1 - self.config.slippage - self.config.commission)
        return float(position.quantity * marked_exit_price)

    @staticmethod
    def _calculate_max_drawdown(capital_curve: List[float]) -> float:
        capital_array = np.asarray(capital_curve, dtype=float)
        if capital_array.size == 0:
            return 0.0
        running_max = np.maximum.accumulate(capital_array)
        drawdown = (capital_array - running_max) / running_max
        return float(np.min(drawdown))

    @staticmethod
    def _calculate_sharpe_ratio(capital_curve: List[float], risk_free_rate: float = 0.02) -> float:
        capital_array = np.asarray(capital_curve, dtype=float)
        if capital_array.size < 2:
            return 0.0
        returns = np.diff(capital_array) / capital_array[:-1]
        if returns.size == 0 or np.isclose(returns.std(), 0.0):
            return 0.0
        excess_return = returns.mean() - risk_free_rate / YEAR_DAYS
        return float(excess_return / returns.std() * np.sqrt(YEAR_DAYS))


def main():
    """运行默认区间回测。"""
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    profile_name = sys.argv[1] if len(sys.argv) > 1 else MARKET_REGIME_CONFIG.get("default_profile", "daily")
    periods = [PeriodWindow("2025-08-25 至今", "2025-08-25", datetime.utcnow().strftime("%Y-%m-%d"))]
    backtester = MarketRegimeSwitchBacktester(MarketRegimeStrategyConfig.for_profile(profile_name))
    results = backtester.run_period_suite(periods)

    for item in results:
        print(f"profile={profile_name}")
        print(f"=== {item['period']} ===")
        print(f"total_return={item['total_return']:.2%}")
        print(f"annual_return={item['annual_return']:.2%}")
        print(f"max_drawdown={item['max_drawdown']:.2%}")
        print(f"win_rate={item['win_rate']:.2%}")
        print(f"total_trades={item['total_trades']}")
        print()


if __name__ == "__main__":
    main()
