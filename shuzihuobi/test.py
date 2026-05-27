#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试脚本 - 验证系统各模块的正确性"""

import sys
import os

# 确保能导入v2模块
sys.path.insert(0, '/Users/game-netease/PycharmProjects/binance-quantization/v2')

def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试1: 模块导入")
    print("=" * 60)

    try:
        print("导入 config... ", end='')
        import config
        print("✓")

        print("导入 indicators... ", end='')
        from indicators import IndicatorCalculator, IndicatorAnalyzer
        print("✓")

        print("导入 strategy_engine... ", end='')
        from strategy_engine import StrategyEngine, Signal
        print("✓")

        print("导入 data_manager... ", end='')
        from data_manager import DataManager
        print("✓")

        print("导入 backtest_engine... ", end='')
        from backtest_engine import BacktestEngine, BacktestResult
        print("✓")

        print("导入 trade_executor... ", end='')
        from trade_executor import RiskManager, TradeExecutor, Position, Order
        print("✓")

        print("导入 notifier... ", end='')
        from notifier import NotificationManager, DingDingNotifier
        print("✓")

        print("导入 optimized_backtest... ", end='')
        from optimized_backtest import OptimizedRsiBacktester, OptimizedRsiConfig, PeriodWindow
        print("✓")

        print("导入 multi_indicator_backtest... ", end='')
        from multi_indicator_backtest import MultiIndicatorRsiBacktester, MultiIndicatorStrategyConfig
        print("✓")

        print("导入 market_regime_backtest... ", end='')
        from market_regime_backtest import MarketRegimeSwitchBacktester, MarketRegimeStrategyConfig
        print("✓")

        print("导入 market_state_score... ", end='')
        from market_state_score import MarketStateScorer
        print("✓")

        print("\n✓ 所有模块导入成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 导入失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """测试配置文件"""
    print("=" * 60)
    print("测试2: 配置验证")
    print("=" * 60)

    try:
        from config import (
            TRADING_CONFIG, RISK_CONFIG, INDICATOR_CONFIG,
            DATA_CONFIG, LOG_CONFIG
        )

        print(f"✓ 交易配置: {TRADING_CONFIG}")
        print(f"✓ 风险配置: {list(RISK_CONFIG.keys())}")
        print(f"✓ 指标配置: {list(INDICATOR_CONFIG.keys())}")
        print(f"✓ 数据配置: {list(DATA_CONFIG.keys())}")
        print(f"✓ 日志配置: {list(LOG_CONFIG.keys())}")
        print("\n✓ 配置验证成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 配置验证失败: {str(e)}\n")
        return False

def test_indicator_calculator():
    """测试指标计算器"""
    print("=" * 60)
    print("测试3: 指标计算器")
    print("=" * 60)

    try:
        import pandas as pd
        import numpy as np
        from indicators import IndicatorCalculator

        # 创建测试数据
        data = pd.Series(np.random.randn(100).cumsum() + 100)

        calc = IndicatorCalculator()

        print("计算 SMA... ", end='')
        sma = calc.calculate_sma(data, 20)
        assert len(sma) == 100
        print("✓")

        print("计算 EMA... ", end='')
        ema = calc.calculate_ema(data, 20)
        assert len(ema) == 100
        print("✓")

        print("计算 RSI... ", end='')
        rsi = calc.calculate_rsi(data, 14)
        assert len(rsi) == 100
        print("✓")

        print("计算 MACD... ", end='')
        macd, signal, hist = calc.calculate_macd(data)
        assert len(macd) == 100
        print("✓")

        print("计算 Bollinger Bands... ", end='')
        upper, middle, lower = calc.calculate_bollinger_bands(data, 20)
        assert len(upper) == 100
        print("✓")

        print("\n✓ 指标计算器测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 指标计算器测试失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_risk_manager():
    """测试风险管理器"""
    print("=" * 60)
    print("测试4: 风险管理器")
    print("=" * 60)

    try:
        from trade_executor import RiskManager
        from config import RISK_CONFIG

        rm = RiskManager(initial_capital=10000, risk_config=RISK_CONFIG)

        print(f"✓ 初始资金: {rm.initial_capital:.2f}")
        print(f"✓ 当前资金: {rm.current_capital:.2f}")

        print("检查仓位限制... ", end='')
        assert rm.check_position_limit('BTCUSDT', 0.5, 45000)
        print("✓")

        print("开仓... ", end='')
        position = rm.open_position('BTCUSDT', 'LONG', 0.5, 45000)
        assert position is not None
        print("✓")

        print("更新价格... ", end='')
        rm.update_prices({'BTCUSDT': 45500})
        assert rm.positions['BTCUSDT'].current_price == 45500
        print("✓")

        print("平仓... ", end='')
        assert rm.close_position('BTCUSDT', 45500)
        print("✓")

        print("\n✓ 风险管理器测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 风险管理器测试失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_strategy_engine():
    """测试策略引擎"""
    print("=" * 60)
    print("测试5: 策略引擎")
    print("=" * 60)

    try:
        import pandas as pd
        import numpy as np
        from strategy_engine import StrategyEngine
        from datetime import datetime, timedelta

        # 创建测试K线数据
        dates = pd.date_range(start='2024-01-01', periods=100, freq='h')
        df = pd.DataFrame({
            'open_time': dates,
            'open': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 102,
            'low': np.random.randn(100).cumsum() + 98,
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.uniform(1000, 5000, 100)
        })
        df.set_index('open_time', inplace=True)

        engine = StrategyEngine()

        print("测试多指标综合策略... ", end='')
        signal = engine.multi_indicator_strategy('BTCUSDT', df)
        print("✓")

        print("测试MA交叉策略... ", end='')
        signal = engine.simple_ma_cross_strategy('BTCUSDT', df)
        print("✓")

        print("测试增强型RSI网格策略... ", end='')
        signal = engine.enhanced_rsi_grid_strategy('BTCUSDT', df)
        print("✓")

        print("\n✓ 策略引擎测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 策略引擎测试失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_backtest_engine():
    """测试回测引擎"""
    print("=" * 60)
    print("测试6: 回测引擎")
    print("=" * 60)

    try:
        import pandas as pd
        import numpy as np
        from backtest_engine import BacktestEngine
        from strategy_engine import StrategyEngine

        # 创建测试数据
        dates = pd.date_range(start='2024-01-01', periods=200, freq='h')
        df = pd.DataFrame({
            'open_time': dates,
            'open': np.random.randn(200).cumsum() + 100,
            'high': np.random.randn(200).cumsum() + 102,
            'low': np.random.randn(200).cumsum() + 98,
            'close': np.random.randn(200).cumsum() + 100,
            'volume': np.random.uniform(1000, 5000, 200)
        })
        df.set_index('open_time', inplace=True)

        backtest = BacktestEngine(initial_capital=10000)
        engine = StrategyEngine()

        print("运行回测... ", end='')
        result = backtest.backtest(
            'BTCUSDT',
            df,
            engine.multi_indicator_strategy,
            'Test Strategy'
        )
        print("✓")

        assert result is not None
        print(f"✓ 初始资金: {result.initial_capital:.2f}")
        print(f"✓ 最终资金: {result.final_capital:.2f}")
        print(f"✓ 总收益: {result.total_return:.2%}")
        print(f"✓ 最大回撤: {result.max_drawdown:.2%}")
        print(f"✓ 交易数: {result.total_trades}")

        print("\n✓ 回测引擎测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 回测引擎测试失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_optimized_backtest():
    """测试优化版 RSI 回测器"""
    print("=" * 60)
    print("测试7: 优化版 RSI 回测")
    print("=" * 60)

    try:
        import pandas as pd
        from optimized_backtest import OptimizedRsiBacktester, OptimizedRsiConfig

        dates = pd.date_range(start='2024-01-01', periods=40, freq='D')
        close = [
            100, 98, 95, 92, 88, 84, 80, 76, 72, 74,
            76, 79, 82, 86, 90, 94, 98, 101, 104, 107,
            110, 108, 106, 105, 104, 106, 109, 113, 117, 120,
            118, 116, 114, 112, 111, 113, 116, 119, 121, 123,
        ]
        df = pd.DataFrame({
            'open_time': dates,
            'close_time': dates + pd.Timedelta(hours=23, minutes=59, seconds=59),
            'open': close,
            'high': [price * 1.02 for price in close],
            'low': [price * 0.98 for price in close],
            'close': close,
            'volume': [2000 + index * 50 for index in range(len(close))],
        })

        backtester = OptimizedRsiBacktester(
            OptimizedRsiConfig(symbol='BTCUSDT', initial_capital=10000)
        )
        prepared = backtester.prepare_indicators(df)

        print("运行优化版回测... ", end='')
        result = backtester.run_backtest_on_dataframe(prepared, 'Optimized RSI Test')
        print("✓")

        assert result is not None
        assert result.final_capital >= 0
        print(f"✓ 最终资金: {result.final_capital:.2f}")
        print(f"✓ 总收益: {result.total_return:.2%}")
        print(f"✓ 交易数: {result.total_trades}")
        print("\n✓ 优化版 RSI 回测测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 优化版 RSI 回测测试失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_multi_indicator_backtest():
    """测试多指标回测器"""
    print("=" * 60)
    print("测试8: 多指标回测")
    print("=" * 60)

    try:
        import pandas as pd
        from multi_indicator_backtest import MultiIndicatorRsiBacktester, MultiIndicatorStrategyConfig

        dates = pd.date_range(start='2024-01-01', periods=80, freq='D')
        close = [
            120, 118, 115, 110, 105, 100, 96, 93, 90, 88,
            86, 84, 82, 80, 79, 81, 84, 88, 92, 96,
            100, 104, 108, 112, 116, 119, 121, 123, 125, 127,
            129, 131, 132, 133, 131, 128, 126, 124, 122, 120,
            118, 117, 119, 122, 126, 130, 134, 138, 141, 144,
            146, 148, 150, 149, 147, 145, 143, 140, 138, 136,
            134, 133, 132, 134, 137, 140, 143, 145, 147, 149,
            151, 153, 154, 152, 149, 147, 145, 144, 146, 148,
        ]
        df = pd.DataFrame({
            'open_time': dates,
            'close_time': dates + pd.Timedelta(hours=23, minutes=59, seconds=59),
            'open': close,
            'high': [price * 1.02 for price in close],
            'low': [price * 0.98 for price in close],
            'close': close,
            'volume': [3000 + index * 30 for index in range(len(close))],
        })

        backtester = MultiIndicatorRsiBacktester(
            MultiIndicatorStrategyConfig(symbol='BTCUSDT', initial_capital=10000)
        )
        prepared = backtester.prepare_indicators(df)

        print("运行多指标回测... ", end='')
        result = backtester.run_backtest_on_dataframe(prepared, 'Multi Indicator Test')
        print("✓")

        assert result is not None
        assert result.final_capital >= 0
        print(f"✓ 最终资金: {result.final_capital:.2f}")
        print(f"✓ 总收益: {result.total_return:.2%}")
        print(f"✓ 交易数: {result.total_trades}")
        print("\n✓ 多指标回测测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 多指标回测测试失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_market_regime_backtest():
    """测试市场状态切换回测器"""
    print("=" * 60)
    print("测试9: 市场状态切换回测")
    print("=" * 60)

    try:
        import pandas as pd
        from market_regime_backtest import MarketRegimeSwitchBacktester, MarketRegimeStrategyConfig

        dates = pd.date_range(start='2023-01-01', periods=240, freq='D')
        close = []
        price = 160.0
        for index in range(len(dates)):
            if index < 70:
                price -= 1.2
            elif index < 140:
                price += 1.0
            elif index < 180:
                price -= 0.5
            else:
                price += 0.8
            close.append(round(price, 2))

        df = pd.DataFrame({
            'open_time': dates,
            'close_time': dates + pd.Timedelta(hours=23, minutes=59, seconds=59),
            'open': close,
            'high': [price * 1.02 for price in close],
            'low': [price * 0.98 for price in close],
            'close': close,
            'volume': [5000 + index * 10 for index in range(len(close))],
        })

        backtester = MarketRegimeSwitchBacktester(
            MarketRegimeStrategyConfig(symbol='BTCUSDT', initial_capital=10000)
        )
        prepared = backtester.prepare_indicators(df)

        print("运行市场状态切换回测... ", end='')
        result = backtester.run_backtest_on_dataframe(prepared, 'Market Regime Test')
        print("✓")

        assert result is not None
        assert result.final_capital >= 0
        print(f"✓ 最终资金: {result.final_capital:.2f}")
        print(f"✓ 总收益: {result.total_return:.2%}")
        print(f"✓ 交易数: {result.total_trades}")

        hourly_dates = pd.date_range(start='2024-01-01', periods=24 * 120, freq='h')
        hourly_close = []
        price = 120.0
        for index in range(len(hourly_dates)):
            if index < 24 * 30:
                price -= 0.08
            elif index < 24 * 70:
                price += 0.06
            else:
                price += 0.02 if index % 12 < 6 else -0.01
            hourly_close.append(round(price, 4))

        hourly_df = pd.DataFrame({
            'open_time': hourly_dates,
            'close_time': hourly_dates + pd.Timedelta(minutes=59, seconds=59),
            'open': hourly_close,
            'high': [price * 1.01 for price in hourly_close],
            'low': [price * 0.99 for price in hourly_close],
            'close': hourly_close,
            'volume': [2000 + (index % 24) * 15 for index in range(len(hourly_close))],
        })
        hourly_backtester = MarketRegimeSwitchBacktester(
            MarketRegimeStrategyConfig.for_profile('intraday_1h')
        )
        hourly_prepared = hourly_backtester.prepare_indicators(hourly_df)

        print("运行1小时市场状态切换回测... ", end='')
        hourly_result = hourly_backtester.run_backtest_on_dataframe(hourly_prepared, 'Market Regime 1h Test')
        print("✓")

        assert hourly_result is not None
        assert hourly_result.final_capital >= 0
        print(f"✓ 1小时最终资金: {hourly_result.final_capital:.2f}")
        print(f"✓ 1小时总收益: {hourly_result.total_return:.2%}")
        print(f"✓ 1小时交易数: {hourly_result.total_trades}")

        swing_backtester = MarketRegimeSwitchBacktester(
            MarketRegimeStrategyConfig.for_profile('intraday_1h_swing')
        )
        swing_prepared = swing_backtester.prepare_indicators(hourly_df)

        print("运行1小时波段市场状态切换回测... ", end='')
        swing_result = swing_backtester.run_backtest_on_dataframe(
            swing_prepared,
            'Market Regime 1h Swing Test',
        )
        print("✓")

        assert swing_result is not None
        assert swing_result.final_capital >= 0
        print(f"✓ 1小时波段最终资金: {swing_result.final_capital:.2f}")
        print(f"✓ 1小时波段总收益: {swing_result.total_return:.2%}")
        print(f"✓ 1小时波段交易数: {swing_result.total_trades}")
        print("\n✓ 市场状态切换回测测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 市场状态切换回测测试失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_market_state_score():
    """测试市场状态打分脚本逻辑"""
    print("=" * 60)
    print("测试10: 市场状态打分")
    print("=" * 60)

    try:
        from market_state_score import MarketStateScorer

        scorer = MarketStateScorer()
        result = scorer.score(as_of='2026-05-25')

        assert result.score >= 0
        assert result.score <= 100
        assert result.score_state in {'bull', 'neutral', 'bear'}
        assert len(result.components) == 7
        print("运行市场状态打分... ✓")
        print(f"✓ 分数: {result.score:.2f}")
        print(f"✓ 分数状态: {result.score_state}")
        print(f"✓ 档位状态: {result.regime_state}")
        print("\n✓ 市场状态打分测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 市场状态打分测试失败: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

def test_notifier():
    """测试通知系统"""
    print("=" * 60)
    print("测试11: 通知系统")
    print("=" * 60)

    try:
        from notifier import NotificationManager, DingDingNotifier

        print("初始化通知管理器... ", end='')
        notifier = NotificationManager()
        print("✓")

        print("初始化钉钉通知器... ", end='')
        dingding = DingDingNotifier()
        print("✓")

        print("\n✓ 通知系统测试成功\n")
        return True

    except Exception as e:
        print(f"\n✗ 通知系统测试失败: {str(e)}\n")
        return False

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("自动数字货币交易平台 - 系统测试")
    print("=" * 60 + "\n")

    results = {}

    # 运行所有测试
    results['模块导入'] = test_imports()
    results['配置验证'] = test_config()
    results['指标计算器'] = test_indicator_calculator()
    results['风险管理器'] = test_risk_manager()
    results['策略引擎'] = test_strategy_engine()
    results['回测引擎'] = test_backtest_engine()
    results['优化版RSI回测'] = test_optimized_backtest()
    results['多指标回测'] = test_multi_indicator_backtest()
    results['市场状态切换回测'] = test_market_regime_backtest()
    results['市场状态打分'] = test_market_state_score()
    results['通知系统'] = test_notifier()

    # 输出测试总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:20} {status}")

    print("=" * 60)
    print(f"总体结果: {passed}/{total} 通过")
    print("=" * 60)

    if passed == total:
        print("\n✓ 所有测试通过！系统准备就绪。\n")
        print("后续步骤:")
        print("1. 运行 'python demo.py' 查看功能演示")
        print("2. 运行 'python backtest.py' 执行回测")
        print("3. 运行 'python main.py' 启动实时交易")
        print("=" * 60 + "\n")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 个测试失败，请检查错误信息。\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
