# -*- coding: utf-8 -*-
"""主程序 - 实时交易系统"""

import logging
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List
from config import TRADING_CONFIG, RISK_CONFIG, LOG_CONFIG
from data_manager import DataManager
from strategy_engine import StrategyEngine
from trade_executor import RiskManager, TradeExecutor
from notifier import NotificationManager
import json

# 配置日志
os.makedirs(LOG_CONFIG['log_path'], exist_ok=True)
logging.basicConfig(
    level=LOG_CONFIG['log_level'],
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{LOG_CONFIG['log_path']}/trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingSystem:
    """自动交易系统"""

    def __init__(self, config: Dict):
        """
        初始化交易系统

        Args:
            config: 配置字典
        """
        self.config = config
        self.data_manager = DataManager(testnet=True)
        self.strategy_engine = StrategyEngine()
        self.risk_manager = RiskManager(initial_capital=10000, risk_config=RISK_CONFIG)
        self.trade_executor = TradeExecutor(self.risk_manager)
        self.notifier = NotificationManager()

        self.symbols = config['symbols']
        self.timeframes = config['timeframes']
        self.running = False

        logger.info("交易系统初始化完成")

    def run(self, interval_seconds: int = 60):
        """
        运行交易系统

        Args:
            interval_seconds: 检查间隔（秒）
        """
        self.running = True
        logger.info("=== 交易系统启动 ===")

        try:
            while self.running:
                try:
                    self._process_trading_cycle()
                    time.sleep(interval_seconds)
                except Exception as e:
                    logger.error(f"交易循环错误: {str(e)}")
                    self.notifier.notify_error("TRADING_CYCLE_ERROR", str(e))
                    time.sleep(5)

        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭...")
            self._cleanup()

    def _process_trading_cycle(self):
        """处理单个交易循环"""
        for symbol in self.symbols:
            # 获取最新K线数据（使用1h时间框架）
            df = self.data_manager.get_klines(symbol, '1h', limit=100)

            if df.empty:
                logger.warning(f"无法获取 {symbol} 数据")
                continue

            # 分析信号
            signal = self.strategy_engine.multi_indicator_strategy(symbol, df)

            if signal:
                logger.info(f"[{symbol}] 生成信号: {signal.signal_type} @ {signal.price:.2f} (信心度: {signal.confidence:.0%})")

                # 检查风险
                if not self.risk_manager.get_trading_allowed():
                    logger.warning(f"由于风险限制，跳过 {symbol} 的交易")
                    continue

                # 执行交易
                if signal.signal_type == 'BUY':
                    self._execute_buy(symbol, signal)
                elif signal.signal_type == 'SELL':
                    self._execute_sell(symbol, signal)

                # 保存信号到数据库
                self.data_manager.save_signal(
                    symbol=symbol,
                    signal_type=signal.signal_type,
                    price=signal.price,
                    confidence=signal.confidence,
                    indicators=signal.indicators
                )

            # 检查现有持仓的止损/止盈
            self._check_positions(symbol)

        # 输出状态
        self._print_status()

    def _execute_buy(self, symbol: str, signal):
        """执行买入"""
        quantity = self._calculate_position_size(symbol, signal)

        if quantity > 0:
            order = self.trade_executor.place_order(
                symbol=symbol,
                direction='BUY',
                quantity=quantity,
                price=signal.price,
                order_type='MARKET'
            )

            if order:
                self.notifier.notify_buy_signal(signal)
                logger.info(f"[{symbol}] 买入订单已执行: 数量={quantity}, 价格={signal.price:.2f}")

    def _execute_sell(self, symbol: str, signal):
        """执行卖出"""
        if symbol in self.risk_manager.positions:
            order = self.trade_executor.place_order(
                symbol=symbol,
                direction='SELL',
                quantity=self.risk_manager.positions[symbol].quantity,
                price=signal.price,
                order_type='MARKET'
            )

            if order:
                self.notifier.notify_sell_signal(signal)
                logger.info(f"[{symbol}] 卖出订单已执行: 价格={signal.price:.2f}")
        else:
            logger.warning(f"[{symbol}] 没有持仓，无法卖出")

    def _check_positions(self, symbol: str):
        """检查持仓的止损/止盈"""
        if symbol not in self.risk_manager.positions:
            return

        # 获取当前价格
        current_price = self.data_manager.get_current_price(symbol)

        if current_price <= 0:
            return

        # 更新持仓价格
        self.risk_manager.positions[symbol].update_price(current_price)

        # 检查止损
        if self.risk_manager.should_stop_loss(symbol):
            self.notifier.notify_risk_warning(
                'STOP_LOSS',
                f"{symbol} 触发止损, 价格={current_price:.2f}"
            )
            self.trade_executor.place_order(
                symbol=symbol,
                direction='SELL',
                quantity=self.risk_manager.positions[symbol].quantity,
                price=current_price,
                order_type='MARKET'
            )

        # 检查止盈
        if self.risk_manager.should_take_profit(symbol):
            self.notifier.notify_risk_warning(
                'TAKE_PROFIT',
                f"{symbol} 触发止盈, 价格={current_price:.2f}"
            )
            self.trade_executor.place_order(
                symbol=symbol,
                direction='SELL',
                quantity=self.risk_manager.positions[symbol].quantity,
                price=current_price,
                order_type='MARKET'
            )

    def _calculate_position_size(self, symbol: str, signal) -> float:
        """计算仓位大小"""
        # 使用初始资金的2%作为单笔交易风险
        risk_amount = self.risk_manager.initial_capital * 0.02

        # 计算数量
        quantity = risk_amount / signal.price

        return quantity

    def _print_status(self):
        """输出系统状态"""
        positions = self.risk_manager.get_position_summary()

        logger.info(f"""
=== 系统状态 ===
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
当前资金: {self.risk_manager.current_capital:.2f}
持仓数: {positions['total_positions']}
未实现盈亏: {positions['total_unrealized_pnl']:.2f}
已执行订单: {len(self.trade_executor.orders)}
        """)

    def _cleanup(self):
        """清理资源"""
        logger.info("正在平仓所有持仓...")

        for symbol in list(self.risk_manager.positions.keys()):
            current_price = self.data_manager.get_current_price(symbol)
            if current_price > 0:
                self.trade_executor.place_order(
                    symbol=symbol,
                    direction='SELL',
                    quantity=self.risk_manager.positions[symbol].quantity,
                    price=current_price
                )

        # 发送最终报告
        summary = self.risk_manager.get_position_summary()
        logger.info(f"最终资金: {self.risk_manager.current_capital:.2f}")
        logger.info(f"总体收益: {(self.risk_manager.current_capital - self.risk_manager.initial_capital) / self.risk_manager.initial_capital:.2%}")

        self.running = False
        logger.info("=== 交易系统已关闭 ===")

    def stop(self):
        """停止交易系统"""
        self.running = False


if __name__ == '__main__':
    # 创建并运行交易系统
    system = TradingSystem(TRADING_CONFIG)
    system.run(interval_seconds=60)

