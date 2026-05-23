#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速验证脚本 - 检查所有文件是否存在和基本语法是否正确"""

import os
import py_compile
import sys

def check_files():
    """检查所有必要文件是否存在"""
    print("=" * 60)
    print("文件存在性检查")
    print("=" * 60 + "\n")

    base_path = '/Users/game-netease/PycharmProjects/binance-quantization/v2'

    required_files = [
        'config.py',
        'data_manager.py',
        'indicators.py',
        'strategy_engine.py',
        'backtest_engine.py',
        'trade_executor.py',
        'notifier.py',
        'main.py',
        'backtest.py',
        'demo.py',
        'test.py',
        '__init__.py',
        'requirements.txt',
        'README.md',
        'QUICKSTART.md',
        '.env.example'
    ]

    all_exist = True
    for file in required_files:
        file_path = os.path.join(base_path, file)
        exists = os.path.exists(file_path)
        status = "✓" if exists else "✗"
        print(f"{status} {file:30} {'(' + str(os.path.getsize(file_path) // 1024) + 'KB)' if exists else '(缺失)'}")
        all_exist = all_exist and exists

    print()
    return all_exist

def check_syntax():
    """检查Python文件语法"""
    print("=" * 60)
    print("Python语法检查")
    print("=" * 60 + "\n")

    base_path = '/Users/game-netease/PycharmProjects/binance-quantization/v2'

    py_files = [
        'config.py',
        'data_manager.py',
        'indicators.py',
        'strategy_engine.py',
        'backtest_engine.py',
        'trade_executor.py',
        'notifier.py',
        'main.py',
        'backtest.py',
        'demo.py',
        'test.py',
        '__init__.py'
    ]

    all_valid = True
    for file in py_files:
        file_path = os.path.join(base_path, file)
        try:
            py_compile.compile(file_path, doraise=True)
            print(f"✓ {file:30} 语法正确")
        except py_compile.PyCompileError as e:
            print(f"✗ {file:30} 语法错误: {str(e)}")
            all_valid = False

    print()
    return all_valid

def check_imports():
    """检查关键模块是否能导入"""
    print("=" * 60)
    print("模块导入检查")
    print("=" * 60 + "\n")

    sys.path.insert(0, '/Users/game-netease/PycharmProjects/binance-quantization/v2')

    modules = [
        ('config', ['TRADING_CONFIG', 'RISK_CONFIG']),
        ('indicators', ['IndicatorCalculator', 'IndicatorAnalyzer']),
        ('strategy_engine', ['StrategyEngine', 'Signal']),
        ('data_manager', ['DataManager']),
        ('backtest_engine', ['BacktestEngine', 'BacktestResult']),
        ('trade_executor', ['RiskManager', 'TradeExecutor']),
        ('notifier', ['NotificationManager'])
    ]

    all_ok = True
    for module_name, items in modules:
        try:
            module = __import__(module_name)
            for item in items:
                if not hasattr(module, item):
                    print(f"✗ {module_name:30} 缺失: {item}")
                    all_ok = False
            print(f"✓ {module_name:30} 导入成功")
        except Exception as e:
            print(f"✗ {module_name:30} 导入失败: {str(e)[:40]}")
            all_ok = False

    print()
    return all_ok

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("自动数字货币交易平台 MVP - 快速验证")
    print("=" * 60 + "\n")

    file_check = check_files()
    syntax_check = check_syntax()
    import_check = check_imports()

    # 总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)

    checks = [
        ("文件完整性", file_check),
        ("语法正确性", syntax_check),
        ("导入可用性", import_check)
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{check_name:20} {status}")
        all_passed = all_passed and result

    print("=" * 60)

    if all_passed:
        print("\n✓ 系统验证通过！所有必要的文件和模块都已准备就绪。\n")
        print("=== 系统功能 ===")
        print("✓ 数据管理 - 获取和存储K线数据")
        print("✓ 技术指标 - 计算15+个技术指标")
        print("✓ 策略引擎 - 生成交易信号")
        print("✓ 回测系统 - 历史数据回测")
        print("✓ 风险管理 - 仓位、止损、止盈控制")
        print("✓ 通知系统 - 钉钉实时推送")
        print("✓ 交易执行 - 订单管理和执行")

        print("\n=== 后续步骤 ===")
        print("1. 配置 .env 文件（复制 .env.example）")
        print("2. 安装依赖: pip install -r requirements.txt")
        print("3. 查看文档: README.md 或 QUICKSTART.md")
        print("4. 运行演示: python demo.py")
        print("5. 执行回测: python backtest.py")
        print("6. 实时交易: python main.py")

        print("\n" + "=" * 60 + "\n")
        return 0
    else:
        print("\n✗ 系统验证失败。请检查错误信息。\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())

