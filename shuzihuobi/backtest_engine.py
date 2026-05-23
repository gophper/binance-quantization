# -*- coding: utf-8 -*-
"""回测引擎 - 支持历史数据回测"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from strategy_engine import StrategyEngine
import json

logger = logging.getLogger(__name__)

YearDays = 365  # 交易手续费率

@dataclass
class Trade:
    """单笔交易记录"""
    entry_time: datetime
    entry_price: float
    exit_time: datetime = None
    exit_price: float = None
    quantity: float = 0
    direction: str = 'LONG'  # LONG or SHORT
    pnl: float = 0
    pnl_percent: float = 0
    status: str = 'OPEN'  # OPEN or CLOSED


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

    def to_dict(self):
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'strategy_name': self.strategy_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': f"{self.total_return:.2%}",
            'annual_return': f"{self.annual_return:.2%}",
            'max_drawdown': f"{self.max_drawdown:.2%}",
            'sharpe_ratio': f"{self.sharpe_ratio:.2f}",
            'win_rate': f"{self.win_rate:.2%}",
            'profit_factor': f"{self.profit_factor:.2f}",
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'avg_win': f"{self.avg_win:.2%}",
            'avg_loss': f"{self.avg_loss:.2%}"
        }


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital: float = 10000, commission: float = 0.0002, slippage: float = 0.0001):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
            commission: 交易手续费 (百分比)
            slippage: 滑点 (百分比)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.strategy_engine = StrategyEngine()
        self.trades: List[Trade] = []
        self.capital_curve = []

    def backtest(self, symbol: str, df: pd.DataFrame, strategy_func,
                strategy_name: str = 'Test Strategy') -> BacktestResult:
        """
        执行回测

        Args:
            symbol: 交易对
            df: K线数据 (包含 open, high, low, close, volume)
            strategy_func: 策略函数，返回Signal或None
            strategy_name: 策略名称

        Returns:
            BacktestResult 回测结果
        """
        self.trades = []
        self.capital_curve = [self.initial_capital]

        current_capital = self.initial_capital
        position = None
        positions = []

        # 遍历每条K线
        for idx in range(1, len(df)):
            # 获取历史数据用于指标计算
            history_df = df.iloc[:idx+1].copy()
            current_row = df.iloc[idx]

            # 生成信号
            signal = strategy_func(symbol, history_df)

            # 处理卖出信号
            if signal and signal.signal_type == 'SELL' and position:
                # 平仓
                trade = self._close_position(position, current_row['close'], current_row['close_time'])
                if trade:
                    positions.append(trade)
                    current_capital = self._update_capital(current_capital, trade)
                position = None

            # 处理买入信号
            if signal and signal.signal_type == 'BUY' and not position:
                # 开仓
                position = self._open_position(
                    entry_time=current_row.name,
                    entry_price=current_row['close'],
                    quantity=self._calculate_quantity(current_capital),
                    close_time=current_row['close_time'],
                    direction='LONG'
                )

            # 更新止损/止盈
            if position:
                position = self._check_exit_conditions(position, current_row)
                if position and position.status == 'CLOSED':
                    positions.append(position)
                    current_capital = self._update_capital(current_capital, position)
                    position = None

            # 记录资金曲线
            self.capital_curve.append(current_capital)

        # 平仓未结束的仓位
        if position:
            position.exit_time = df.iloc[-1].name
            position.exit_price = df.iloc[-1]['close']
            position.pnl = (position.exit_price - position.entry_price) * position.quantity
            position.pnl_percent = (position.exit_price - position.entry_price) / position.entry_price
            position.status = 'CLOSED'
            positions.append(position)
            current_capital = self._update_capital(current_capital, position)

        self.trades = positions

        # 计算回测结果
        result = self._calculate_results(
            symbol, strategy_name, df, current_capital, positions
        )

        return result

    def _open_position(self, entry_time, entry_price, quantity, close_time,direction='LONG') -> Trade:
        """开仓"""
        # 加入滑点和手续费
        actual_price = entry_price * (1 + self.slippage + self.commission)
        print(f"Opening position at {actual_price} for quantity {quantity} at {close_time}")
        return Trade(
            entry_time=entry_time,
            entry_price=actual_price,
            quantity=quantity,
            direction=direction,
            status='OPEN'
        )

    def _close_position(self, position: Trade, exit_price,close_time) -> Trade:
        """平仓"""
        # 加入滑点和手续费
        actual_price = exit_price * (1 - self.slippage - self.commission)
        position.exit_time = datetime.now()
        position.exit_price = actual_price
        position.pnl = (actual_price - position.entry_price) * position.quantity
        position.pnl_percent = (actual_price - position.entry_price) / position.entry_price
        position.status = 'CLOSED'
        print(f"Closing position at {actual_price} for quantity {position.quantity} at {close_time}")
        return position

    def _check_exit_conditions(self, position: Trade, current_row) -> Trade:
        """检查止损/止盈条件"""
        current_price = current_row['close']

        # 计算亏损百分比
        loss_percent = (current_price - position.entry_price) / position.entry_price

        # 止盈: +5%
        if loss_percent >= 0.05:
            return self._close_position(position, current_price, current_row['close_time'])

        # 止损: -3%
        if loss_percent <= -0.03:
            return self._close_position(position, current_price, current_row['close_time'])

        return position

    def _calculate_quantity(self, capital: float, risk_percent: float = 0.02) -> float:
        """计算交易数量"""
        # 每次交易使用资金的2%
        return (capital * risk_percent) / 1000  # 假设价格在1000左右

    def _update_capital(self, capital: float, trade: Trade) -> float:
        """更新资金"""
        return capital + trade.pnl

    def _calculate_results(self, symbol: str, strategy_name: str, df: pd.DataFrame,
                          final_capital: float, trades: List[Trade]) -> BacktestResult:
        """计算回测结果"""
        start_time = pd.to_datetime(df.index[0])
        end_time = pd.to_datetime(df.index[-1])
        # 收益相关指标
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        trading_days = len(df)
        years = trading_days / YearDays
        annual_return = (final_capital / self.initial_capital) ** (1 / years) - 1 if years > 0 else 0

        # 风险指标
        max_drawdown = self._calculate_max_drawdown()
        sharpe_ratio = self._calculate_sharpe_ratio(self.capital_curve)

        # 交易统计
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]

        win_rate = len(winning_trades) / len(trades) if trades else 0
        total_profit = sum([t.pnl for t in winning_trades])
        total_loss = abs(sum([t.pnl for t in losing_trades]))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        avg_win = total_profit / len(winning_trades) if winning_trades else 0
        avg_loss = total_loss / len(losing_trades) if losing_trades else 0

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
            avg_win=avg_win / self.initial_capital,
            avg_loss=avg_loss / self.initial_capital,
            trades=trades
        )

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.capital_curve:
            return 0

        capital_array = np.array(self.capital_curve)
        running_max = np.maximum.accumulate(capital_array)
        drawdown = (capital_array - running_max) / running_max
        max_drawdown = np.min(drawdown)

        return max_drawdown

    def _calculate_sharpe_ratio(self, capital_curve, risk_free_rate=0.02) -> float:
        """计算夏普比率"""
        if len(capital_curve) < 2:
            return 0

        returns = np.diff(capital_curve) / capital_curve[:-1]
        if len(returns) == 0 or returns.std() == 0:
            return 0

        excess_return = returns.mean() - risk_free_rate / YearDays
        sharpe = excess_return / returns.std() * np.sqrt(YearDays)

        return sharpe

