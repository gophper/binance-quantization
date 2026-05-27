# -*- coding: utf-8 -*-
"""回测引擎 - 支持历史数据回测"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Callable, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

YEAR_DAYS = 365.25


@dataclass
class Trade:
    """单笔交易记录"""

    entry_time: datetime
    entry_price: float
    quantity: float
    direction: str = "LONG"
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0
    status: str = "OPEN"
    exit_reason: str = ""
    holding_days: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "entry_time": self.entry_time.isoformat(),
            "entry_price": self.entry_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "direction": self.direction,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "status": self.status,
            "exit_reason": self.exit_reason,
            "holding_days": self.holding_days,
        }


@dataclass
class BacktestResult:
    """回测结果"""

    symbol: str
    strategy_name: str
    start_time: datetime
    end_time: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    trades: List[Trade] = field(default_factory=list)

    def to_dict(self, include_trades: bool = False) -> dict:
        """转换为字典"""
        data = {
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
        }
        if include_trades:
            data["trades"] = [trade.to_dict() for trade in self.trades]
        return data


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        initial_capital: float = 10000,
        commission: float = 0.0002,
        slippage: float = 0.0001,
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.trades: List[Trade] = []
        self.capital_curve: List[float] = []

    def backtest(
        self,
        symbol: str,
        df: pd.DataFrame,
        strategy_func: Callable,
        strategy_name: str = "Test Strategy",
        stop_loss_percent: float = 0.03,
        max_holding_period: Optional[pd.DateOffset] = None,
    ) -> BacktestResult:
        """
        执行回测

        Args:
            symbol: 交易对
            df: K线数据 (包含 open, high, low, close, volume)
            strategy_func: 策略函数，返回Signal或None
            strategy_name: 策略名称
            stop_loss_percent: 止损比例
            max_holding_period: 最大持有时长

        Returns:
            BacktestResult 回测结果
        """
        if df.empty:
            raise ValueError("回测数据为空，无法执行回测")

        self.trades = []
        current_capital = self.initial_capital
        self.capital_curve = [self.initial_capital]
        position: Optional[Trade] = None
        closed_trades: List[Trade] = []

        for idx in range(len(df)):
            history_df = df.iloc[: idx + 1].copy()
            current_row = df.iloc[idx]
            current_time = self._get_row_time(current_row)

            signal = strategy_func(symbol, history_df)

            if position and signal and signal.signal_type == "SELL":
                position = self._close_position(
                    position=position,
                    exit_price=float(current_row["close"]),
                    exit_time=current_time,
                    exit_reason="RSI_SELL_SIGNAL",
                )
                closed_trades.append(position)
                current_capital = self._update_capital(current_capital, position)
                position = None

            if position:
                updated_position = self._check_exit_conditions(
                    position=position,
                    current_row=current_row,
                    stop_loss_percent=stop_loss_percent,
                    max_holding_period=max_holding_period,
                )
                if updated_position.status == "CLOSED":
                    closed_trades.append(updated_position)
                    current_capital = self._update_capital(current_capital, updated_position)
                    position = None
                else:
                    position = updated_position

            if signal and signal.signal_type == "BUY" and not position:
                position = self._open_position(
                    entry_time=current_time,
                    entry_price=float(current_row["close"]),
                    capital=current_capital,
                    direction="LONG",
                )

            self.capital_curve.append(self._calculate_equity(current_capital, position, current_row))

        if position:
            last_row = df.iloc[-1]
            position = self._close_position(
                position=position,
                exit_price=float(last_row["close"]),
                exit_time=self._get_row_time(last_row),
                exit_reason="END_OF_BACKTEST",
            )
            closed_trades.append(position)
            current_capital = self._update_capital(current_capital, position)
            self.capital_curve[-1] = current_capital

        self.trades = closed_trades
        return self._calculate_results(symbol, strategy_name, df, current_capital, closed_trades)

    def _open_position(self, entry_time: datetime, entry_price: float, capital: float, direction: str = "LONG") -> Trade:
        """开仓"""
        actual_entry_price = entry_price * (1 + self.slippage + self.commission)
        quantity = self._calculate_quantity(capital, actual_entry_price)

        return Trade(
            entry_time=entry_time,
            entry_price=actual_entry_price,
            quantity=quantity,
            direction=direction,
            status="OPEN",
        )

    def _close_position(
        self,
        position: Trade,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
    ) -> Trade:
        """平仓"""
        actual_exit_price = exit_price * (1 - self.slippage - self.commission)
        position.exit_time = exit_time
        position.exit_price = actual_exit_price
        position.pnl = (actual_exit_price - position.entry_price) * position.quantity
        position.pnl_percent = (actual_exit_price / position.entry_price) - 1
        position.status = "CLOSED"
        position.exit_reason = exit_reason
        position.holding_days = max((position.exit_time - position.entry_time).days, 0)
        return position

    def _check_exit_conditions(
        self,
        position: Trade,
        current_row: pd.Series,
        stop_loss_percent: float,
        max_holding_period: Optional[pd.DateOffset],
    ) -> Trade:
        """检查退出条件"""
        current_time = self._get_row_time(current_row)
        exit_mark_price = float(current_row["close"]) * (1 - self.slippage - self.commission)
        price_return = (exit_mark_price / position.entry_price) - 1

        if price_return <= -stop_loss_percent:
            return self._close_position(
                position=position,
                exit_price=float(current_row["close"]),
                exit_time=current_time,
                exit_reason="STOP_LOSS",
            )

        if self._reached_max_holding_period(position.entry_time, current_time, max_holding_period):
            return self._close_position(
                position=position,
                exit_price=float(current_row["close"]),
                exit_time=current_time,
                exit_reason="MAX_HOLDING_PERIOD",
            )

        return position

    def _reached_max_holding_period(
        self,
        entry_time: datetime,
        current_time: datetime,
        max_holding_period: Optional[pd.DateOffset],
    ) -> bool:
        """检查是否达到最大持有时长"""
        if max_holding_period is None:
            return False

        entry_ts = pd.Timestamp(entry_time)
        current_ts = pd.Timestamp(current_time)
        max_exit_time = entry_ts + max_holding_period
        return current_ts >= max_exit_time

    def _calculate_quantity(self, capital: float, entry_price: float) -> float:
        """按全仓计算交易数量"""
        if entry_price <= 0:
            raise ValueError("开仓价格必须大于 0")
        return capital / entry_price

    @staticmethod
    def _update_capital(capital: float, trade: Trade) -> float:
        """更新资金"""
        return capital + trade.pnl

    def _calculate_equity(
        self,
        current_capital: float,
        position: Optional[Trade],
        current_row: pd.Series,
    ) -> float:
        """计算当前权益"""
        if not position:
            return current_capital

        marked_exit_price = float(current_row["close"]) * (1 - self.slippage - self.commission)
        return position.quantity * marked_exit_price

    def _calculate_results(
        self,
        symbol: str,
        strategy_name: str,
        df: pd.DataFrame,
        final_capital: float,
        trades: List[Trade],
    ) -> BacktestResult:
        """计算回测结果"""
        start_time = pd.Timestamp(df["open_time"].iloc[0]).to_pydatetime()
        end_time = pd.Timestamp(df["close_time"].iloc[-1]).to_pydatetime()

        total_return = (final_capital - self.initial_capital) / self.initial_capital

        elapsed_days = max((end_time - start_time).total_seconds() / 86400, 1 / YEAR_DAYS)
        years = elapsed_days / YEAR_DAYS
        annual_return = (final_capital / self.initial_capital) ** (1 / years) - 1 if years > 0 else 0.0

        max_drawdown = self._calculate_max_drawdown()
        sharpe_ratio = self._calculate_sharpe_ratio(self.capital_curve)

        winning_trades = [trade for trade in trades if trade.pnl > 0]
        losing_trades = [trade for trade in trades if trade.pnl < 0]

        win_rate = len(winning_trades) / len(trades) if trades else 0.0
        total_profit = sum(trade.pnl for trade in winning_trades)
        total_loss = abs(sum(trade.pnl for trade in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else (999.0 if total_profit > 0 else 0.0)

        avg_win = float(np.mean([trade.pnl_percent for trade in winning_trades])) if winning_trades else 0.0
        avg_loss = float(np.mean([trade.pnl_percent for trade in losing_trades])) if losing_trades else 0.0

        return BacktestResult(
            symbol=symbol,
            strategy_name=strategy_name,
            start_time=start_time,
            end_time=end_time,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            trades=trades,
        )

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.capital_curve:
            return 0.0

        capital_array = np.asarray(self.capital_curve, dtype=float)
        running_max = np.maximum.accumulate(capital_array)
        drawdown = (capital_array - running_max) / running_max
        return float(np.min(drawdown))

    @staticmethod
    def _calculate_sharpe_ratio(capital_curve: List[float], risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        if len(capital_curve) < 2:
            return 0.0

        capital_array = np.asarray(capital_curve, dtype=float)
        returns = np.diff(capital_array) / capital_array[:-1]
        if len(returns) == 0 or np.isclose(returns.std(), 0.0):
            return 0.0

        excess_return = returns.mean() - risk_free_rate / YEAR_DAYS
        return float(excess_return / returns.std() * np.sqrt(YEAR_DAYS))

    @staticmethod
    def _get_row_time(row: pd.Series) -> datetime:
        """从K线行中获取时间"""
        if "close_time" in row:
            return pd.Timestamp(row["close_time"]).to_pydatetime()
        if "open_time" in row:
            return pd.Timestamp(row["open_time"]).to_pydatetime()
        return pd.Timestamp(row.name).to_pydatetime()
