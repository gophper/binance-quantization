# -*- coding: utf-8 -*-
"""交易执行和风险管理"""

import logging
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    entry_time: datetime
    direction: str  # LONG or SHORT
    unrealized_pnl: float
    unrealized_pnl_percent: float
    highest_price: float = 0
    lowest_price: float = 0

    def update_price(self, new_price: float):
        """更新当前价格"""
        self.current_price = new_price
        self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
        self.unrealized_pnl_percent = (new_price - self.entry_price) / self.entry_price

        if new_price > self.highest_price:
            self.highest_price = new_price
        if new_price < self.lowest_price or self.lowest_price == 0:
            self.lowest_price = new_price


@dataclass
class Order:
    """交易订单"""
    order_id: str
    symbol: str
    direction: str  # BUY or SELL
    order_type: str  # LIMIT, MARKET
    quantity: float
    price: float
    status: OrderStatus
    created_at: datetime
    filled_quantity: float = 0
    filled_price: float = 0
    commission: float = 0


class RiskManager:
    """风险管理器"""

    def __init__(self, initial_capital: float, risk_config: Dict):
        """
        初始化风险管理器

        Args:
            initial_capital: 初始资金
            risk_config: 风险配置
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_config = risk_config

        # 仓位管理
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []

        # 风险追踪
        self.daily_losses = 0
        self.daily_loss_time = datetime.now()
        self.max_drawdown = 0
        self.peak_capital = initial_capital

    def check_position_limit(self, symbol: str, quantity: float, entry_price: float) -> bool:
        """
        检查仓位限制

        Returns:
            True if 允许开仓, False if 超过限制
        """
        if symbol in self.positions:
            current_qty = self.positions[symbol].quantity
        else:
            current_qty = 0

        new_position_value = (current_qty + quantity) * entry_price
        max_position_value = self.current_capital * self.risk_config['max_position']

        if new_position_value > max_position_value:
            logger.warning(
                f"Position limit exceeded for {symbol}: "
                f"新仓位价值 {new_position_value:.2f} > 最大允许 {max_position_value:.2f}"
            )
            return False

        return True

    def check_daily_loss_limit(self, daily_loss: float) -> bool:
        """
        检查单日亏损限制

        Returns:
            True if 未超过限制, False if 超过限制
        """
        loss_percent = daily_loss / self.initial_capital
        max_loss = self.initial_capital * self.risk_config['max_daily_loss']

        if daily_loss > max_loss:
            logger.error(
                f"Daily loss limit exceeded: {daily_loss:.2f} > {max_loss:.2f}"
            )
            return False

        return True

    def check_drawdown_limit(self) -> bool:
        """
        检查最大回撤限制

        Returns:
            True if 未超过限制, False if 触发
        """
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital

        if drawdown > self.risk_config['max_drawdown']:
            logger.error(
                f"Drawdown limit exceeded: {drawdown:.2%} > {self.risk_config['max_drawdown']:.2%}"
            )
            return False

        self.max_drawdown = max(self.max_drawdown, drawdown)
        return True

    def should_stop_loss(self, symbol: str) -> bool:
        """
        检查是否触发止损

        Returns:
            True if 应该止损, False otherwise
        """
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        loss_percent = (position.current_price - position.entry_price) / position.entry_price

        if loss_percent < -self.risk_config['stop_loss_percent']:
            logger.warning(
                f"Stop loss triggered for {symbol}: "
                f"亏损 {loss_percent:.2%}"
            )
            return True

        return False

    def should_take_profit(self, symbol: str) -> bool:
        """
        检查是否触发止盈

        Returns:
            True if 应该止盈, False otherwise
        """
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        profit_percent = (position.current_price - position.entry_price) / position.entry_price

        if profit_percent > self.risk_config['take_profit_percent']:
            logger.info(
                f"Take profit triggered for {symbol}: "
                f"盈利 {profit_percent:.2%}"
            )
            return True

        return False

    def get_trading_allowed(self) -> bool:
        """
        检查是否允许交易

        Returns:
            True if 允许, False if 已触发风险限制
        """
        # 检查各项限制
        if not self.check_drawdown_limit():
            return False

        return True

    def open_position(self, symbol: str, direction: str, quantity: float,
                     entry_price: float) -> Optional[Position]:
        """
        开仓

        Args:
            symbol: 交易对
            direction: LONG or SHORT
            quantity: 数量
            entry_price: 开仓价格

        Returns:
            Position if 成功, None if 失败
        """
        if not self.check_position_limit(symbol, quantity, entry_price):
            return None

        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            entry_time=datetime.now(),
            direction=direction,
            unrealized_pnl=0,
            unrealized_pnl_percent=0,
            highest_price=entry_price,
            lowest_price=entry_price
        )

        self.positions[symbol] = position
        logger.info(
            f"Position opened: {symbol} {direction} {quantity} @ {entry_price}"
        )

        return position

    def close_position(self, symbol: str, exit_price: float) -> bool:
        """
        平仓

        Args:
            symbol: 交易对
            exit_price: 平仓价格

        Returns:
            True if 成功, False if 失败
        """
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return False

        position = self.positions[symbol]
        realized_pnl = (exit_price - position.entry_price) * position.quantity

        # 更新资金
        self.current_capital += realized_pnl

        logger.info(
            f"Position closed: {symbol} "
            f"Entry: {position.entry_price}, Exit: {exit_price}, "
            f"PnL: {realized_pnl:.2f}"
        )

        del self.positions[symbol]
        return True

    def update_prices(self, price_data: Dict[str, float]):
        """
        更新所有持仓的价格

        Args:
            price_data: {symbol: price} 字典
        """
        for symbol, price in price_data.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)

    def get_position_summary(self) -> Dict:
        """获取持仓汇总"""
        summary = {
            'total_positions': len(self.positions),
            'total_unrealized_pnl': sum(p.unrealized_pnl for p in self.positions.values()),
            'positions': {}
        }

        for symbol, position in self.positions.items():
            summary['positions'][symbol] = {
                'direction': position.direction,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'current_price': position.current_price,
                'unrealized_pnl': position.unrealized_pnl,
                'unrealized_pnl_percent': f"{position.unrealized_pnl_percent:.2%}",
                'entry_time': position.entry_time.isoformat()
            }

        return summary

    def reset_daily_loss(self):
        """重置每日亏损计数"""
        self.daily_losses = 0
        self.daily_loss_time = datetime.now()


class TradeExecutor:
    """交易执行器"""

    def __init__(self, risk_manager: RiskManager, commission: float = 0.0002):
        """
        初始化交易执行器

        Args:
            risk_manager: 风险管理器
            commission: 交易手续费比率
        """
        self.risk_manager = risk_manager
        self.commission = commission
        self.orders: List[Order] = []

    def place_order(self, symbol: str, direction: str, quantity: float,
                   price: float, order_type: str = 'LIMIT') -> Optional[Order]:
        """
        下单

        Args:
            symbol: 交易对
            direction: BUY or SELL
            quantity: 数量
            price: 价格
            order_type: LIMIT or MARKET

        Returns:
            Order if 成功, None if 失败
        """
        if not self.risk_manager.get_trading_allowed():
            logger.error("Trading is not allowed due to risk limits")
            return None

        order_id = f"{symbol}_{int(time.time()*1000)}"

        # 如果是BUY，开多仓
        if direction == 'BUY':
            position = self.risk_manager.open_position(
                symbol, 'LONG', quantity, price
            )
            if position is None:
                return None

        # 如果是SELL，平仓
        elif direction == 'SELL':
            if not self.risk_manager.close_position(symbol, price):
                return None

        order = Order(
            order_id=order_id,
            symbol=symbol,
            direction=direction,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.FILLED,
            created_at=datetime.now(),
            filled_quantity=quantity,
            filled_price=price,
            commission=quantity * price * self.commission
        )

        self.orders.append(order)
        logger.info(f"Order placed: {order_id} {direction} {quantity} {symbol} @ {price}")

        return order

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        for order in self.orders:
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                logger.info(f"Order cancelled: {order_id}")
                return True

        return False

    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """获取订单状态"""
        for order in self.orders:
            if order.order_id == order_id:
                return order.status

        return None

