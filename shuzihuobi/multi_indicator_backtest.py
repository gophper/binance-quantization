# -*- coding: utf-8 -*-
"""多指标增强版 RSI 回测。

策略逻辑：
1. 入场沿用 RSI(6) + Wilder 的极端超卖买点：RSI < 8；
2. 平仓改为多指标确认：RSI > 62 且 (跌破 MA10 或 MACD 死叉)；
3. 加入再入场重置门槛：一次交易结束后，需等 RSI > 10 才允许下一次买入；
4. 保留 10% 止损、手续费与滑点设定。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd

from backtest_engine import BacktestResult, Trade, YEAR_DAYS
from indicators import IndicatorCalculator
from optimized_backtest import OptimizedRsiBacktester, PeriodWindow

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MultiIndicatorStrategyConfig:
    """多指标策略配置。"""

    symbol: str = "BTCUSDT"
    timeframe: str = "1d"
    rsi_period: int = 6
    buy_threshold: float = 8.0
    reentry_reset_rsi: float = 10.0
    sell_rsi_threshold: float = 62.0
    exit_ma_period: int = 10
    stop_loss_percent: float = 0.10
    commission: float = 0.0002
    slippage: float = 0.0001
    initial_capital: float = 10000.0
    warmup_days: int = 120


class MultiIndicatorRsiBacktester:
    """多指标增强版 RSI 回测器。"""

    def __init__(self, config: MultiIndicatorStrategyConfig | None = None):
        self.config = config or MultiIndicatorStrategyConfig()
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
        """补充多指标策略所需列。"""
        prepared = df.copy()
        close = prepared["close"]
        prepared["rsi"] = IndicatorCalculator.calculate_rsi(close, self.config.rsi_period)
        prepared["ma_exit"] = close.rolling(self.config.exit_ma_period).mean()
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
        execution_df = prepared_df[prepared_df["open_time"] >= start_ts].reset_index(drop=True)
        if execution_df.empty:
            raise ValueError(f"{period.name} 在执行区间内没有可用数据")

        return self.run_backtest_on_dataframe(execution_df, period.name)

    def run_backtest_on_dataframe(self, df: pd.DataFrame, strategy_name: str) -> BacktestResult:
        """在已准备好的 DataFrame 上运行回测。"""
        if df.empty:
            raise ValueError("回测数据为空")

        current_capital = self.config.initial_capital
        capital_curve = [current_capital]
        closed_trades: List[Trade] = []
        position: Trade | None = None
        armed_for_entry = True

        for index in range(1, len(df)):
            current = df.iloc[index]
            previous = df.iloc[index - 1]
            current_time = pd.Timestamp(current["close_time"]).to_pydatetime()
            close_price = float(current["close"])
            rsi = current["rsi"]

            if pd.isna(rsi) or pd.isna(current["ma_exit"]) or pd.isna(current["macd_signal"]):
                capital_curve.append(self._calculate_equity(current_capital, position, close_price))
                continue

            if position is None and not armed_for_entry and rsi > self.config.reentry_reset_rsi:
                armed_for_entry = True

            if position:
                exit_mark_price = close_price * (1 - self.config.slippage - self.config.commission)
                price_return = (exit_mark_price / position.entry_price) - 1
                macd_death_cross = (
                    current["macd"] < current["macd_signal"]
                    and previous["macd"] >= previous["macd_signal"]
                )
                ma_break = close_price < float(current["ma_exit"])

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
                    armed_for_entry = False
                elif rsi > self.config.sell_rsi_threshold and (ma_break or macd_death_cross):
                    position = self._close_position(
                        position=position,
                        exit_price=close_price,
                        exit_time=current_time,
                        exit_reason="MULTI_INDICATOR_SELL",
                    )
                    closed_trades.append(position)
                    current_capital += position.pnl
                    position = None
                    armed_for_entry = False

            if position is None and armed_for_entry and rsi < self.config.buy_threshold:
                position = self._open_position(
                    entry_time=current_time,
                    entry_price=close_price,
                    capital=current_capital,
                )

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
                        "buy_threshold": self.config.buy_threshold,
                        "reentry_reset_rsi": self.config.reentry_reset_rsi,
                        "sell_rsi_threshold": self.config.sell_rsi_threshold,
                        "exit_ma_period": self.config.exit_ma_period,
                        "stop_loss_percent": self.config.stop_loss_percent,
                    },
                    **result.to_dict(include_trades=True),
                }
            )

        output_path = self.output_dir / "multi_indicator_backtest_results.json"
        output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return records

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

    periods = [PeriodWindow("2025-08-25 至今", "2025-08-25", datetime.utcnow().strftime("%Y-%m-%d"))]
    backtester = MultiIndicatorRsiBacktester()
    results = backtester.run_period_suite(periods)

    for item in results:
        print(f"=== {item['period']} ===")
        print(f"total_return={item['total_return']:.2%}")
        print(f"annual_return={item['annual_return']:.2%}")
        print(f"max_drawdown={item['max_drawdown']:.2%}")
        print(f"win_rate={item['win_rate']:.2%}")
        print(f"total_trades={item['total_trades']}")
        print()


if __name__ == "__main__":
    main()
