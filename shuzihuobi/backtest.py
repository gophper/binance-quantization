# -*- coding: utf-8 -*-
"""回测脚本 - 策略回测和验证"""

import logging
import json
from datetime import datetime, timedelta
from data_manager import DataManager
from strategy_engine import StrategyEngine
from backtest_engine import BacktestEngine
import pandas as pd

logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BacktestRunner:
    """回测执行器"""

    def __init__(self):
        self.data_manager = DataManager()
        self.strategy_engine = StrategyEngine()
        self.backtest_engine = BacktestEngine(initial_capital=10000)

    def run_backtest(self, symbol: str, timeframe: str = '1h',
                    strategy_func=None, strategy_name: str = 'Test Strategy') -> dict:
        """
        执行单个回测

        Args:
            symbol: 交易对
            timeframe: 时间框架
            strategy_func: 策略函数
            strategy_name: 策略名称

        Returns:
            回测结果字典
        """
        logger.info(f"开始回测: {symbol} {timeframe} ({strategy_name})")

        # 获取K线数据
        df = self.data_manager.get_klines(symbol, timeframe, limit=365)

        if df.empty:
            logger.error(f"无法获取 {symbol} 的K线数据")
            return None

        logger.info(f"加载数据: {len(df)} 条K线，时间范围: {df.index[0]} 到 {df.index[-1]}")

        # 使用默认策略
        if strategy_func is None:
            strategy_func = self.strategy_engine.multi_indicator_strategy

        # 执行回测
        result = self.backtest_engine.backtest(
            symbol=symbol,
            df=df,
            strategy_func=strategy_func,
            strategy_name=strategy_name
        )

        return result

    def run_multiple_backtest(self, symbols: list, timeframe: str = '1h',
                             strategies: dict = None) -> dict:
        """
        执行多个回测

        Args:
            symbols: 交易对列表
            timeframe: 时间框架
            strategies: {strategy_name: strategy_func} 字典

        Returns:
            {symbol: {strategy_name: result}} 嵌套字典
        """
        if strategies is None:
            strategies = {
               # 'Multi-Indicator': self.strategy_engine.multi_indicator_strategy,
               # 'MA-Cross': self.strategy_engine.simple_ma_cross_strategy,
                'Enhanced-RSI': self.strategy_engine.enhanced_rsi_grid_strategy
            }

        results = {}

        for symbol in symbols:
            logger.info(f"\n========== 开始回测 {symbol} ==========")
            results[symbol] = {}

            for strategy_name, strategy_func in strategies.items():
                try:
                    result = self.run_backtest(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy_func=strategy_func,
                        strategy_name=strategy_name
                    )

                    if result:
                        results[symbol][strategy_name] = result
                        self._print_result(result)

                except Exception as e:
                    logger.error(f"回测失败 {symbol} {strategy_name}: {str(e)}")

        return results

    def _print_result(self, result):
        """打印回测结果"""
        logger.info(f"""
========== 回测结果 ==========
策略: {result.strategy_name}
交易对: {result.symbol}
时间范围: {result.start_time} 到 {result.end_time}

资金统计:
  初始资金: {result.initial_capital:.2f}
  最终资金: {result.final_capital:.2f}
  总收益: {result.total_return:.2%}
  年化收益: {result.annual_return:.2%}

风险指标:
  最大回撤: {result.max_drawdown:.2%}
  夏普比率: {result.sharpe_ratio:.2f}

交易统计:
  总交易数: {result.total_trades}
  盈利交易: {result.winning_trades}
  亏损交易: {result.losing_trades}
  胜率: {result.win_rate:.2%}
  盈亏比: {result.profit_factor:.2f}
  平均盈利: {result.avg_win:.2%}
  平均亏损: {result.avg_loss:.2%}
=============================
        """)

    def export_results(self, results: dict, output_file: str = 'backtest_results.json'):
        """导出回测结果"""
        export_data = {}

        for symbol, strategies_results in results.items():
            export_data[symbol] = {}
            for strategy_name, result in strategies_results.items():
                export_data[symbol][strategy_name] = result.to_dict()

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"回测结果已导出到: {output_file}")

    def compare_strategies(self, results: dict):
        """比较不同策略的表现"""
        logger.info("\n========== 策略比较 ==========")

        comparison_data = []

        for symbol, strategies_results in results.items():
            for strategy_name, result in strategies_results.items():
                comparison_data.append({
                    '交易对': symbol,
                    '策略': strategy_name,
                    '总收益': f"{result.total_return:.2%}",
                    '年化收益': f"{result.annual_return:.2%}",
                    '最大回撤': f"{result.max_drawdown:.2%}",
                    '夏普比率': f"{result.sharpe_ratio:.2f}",
                    '胜率': f"{result.win_rate:.2%}",
                    '盈亏比': f"{result.profit_factor:.2f}",
                    '交易数': result.total_trades
                })

        if comparison_data:
            df = pd.DataFrame(comparison_data)
            logger.info(f"\n{df.to_string(index=False)}")


def main():
    """主函数"""
    runner = BacktestRunner()

    # 要回测的交易对
    symbols = ['EOSUSDT']

    # 回测结果
    results = runner.run_multiple_backtest(
        symbols=symbols,
        timeframe='1d'
    )

    # 比较策略
    runner.compare_strategies(results)

    # 导出结果
    runner.export_results(results, 'backtest_results.json')

    logger.info("\n回测完成！")


if __name__ == '__main__':
    main()

