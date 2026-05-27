# -*- coding: utf-8 -*-
"""系统配置文件"""

import os
from dotenv import load_dotenv

load_dotenv()

# API 配置
# BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', 'your_api_key')
# BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', 'your_api_secret')
# BINANCE_API_KEY = 'M7MpMbSrBfeRrhIlL2TUBeqsA0NvQbiFBN42uaQFxtLi6DqvqHqXq6jc0LocgNzy'
# BINANCE_API_SECRET = 'lrlvs41JDJbB4q6LsGcll0DvRIM36gWocVQ5ZSY3Pkj6H5L3daILboear7K82PKu'

BINANCE_API_KEY = 'VvTraHag5nhdRvHFbWtDjvpUviPyJC9RurEIGWoX987w6Bwb3BfBQeyGToyxljNu'
BINANCE_API_SECRET = 'ROUWsdNcIHKbFiEwurGESxdMel7IbGxfkbdgOddmmVMlvXKkDHMs2TrrlaaLxKGq'
# 币安API基础URL
BINANCE_MAINNET_REST_URL = "https://api.binance.com"
BINANCE_MAINNET_FUTURES_URL = "https://fapi.binance.com"
BINANCE_PUBLIC_DATA_URL = "https://data-api.binance.vision"

BINANCE_REST_URL = "https://testnet.binance.vision"
BINANCE_FUTURES_URL = "https://testnet.binancefuture.com"

#- Spot（现货）测试网: https://testnet.binance.vision - Futures（USDT‑M）测试网: https://testnet.binancefuture.com

# 钉钉通知配置
#DINGDING_WEBHOOK = os.getenv('DINGDING_WEBHOOK', '')
DINGDING_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=your_access_token"

# 交易配置
TRADING_CONFIG = {
    'symbols': ['EOSUSDT'],  # 交易品种
    'timeframes': ['1h', '4h', '1d'],   # 交易时间框架
    'testnet': True,                     # 是否使用测试网络
}

# 风险控制配置
RISK_CONFIG = {
    'max_position': 0.30,           # 单标的最大仓位：30%
    'max_daily_loss': 0.02,          # 单日最大亏损：2%
    'max_drawdown': 0.15,            # 全仓最大回撤：15%
    'stop_loss_percent': 0.03,       # 止损：3%
    'take_profit_percent': 0.05,     # 止盈：5%
}

# 指标配置
INDICATOR_CONFIG = {
    'rsi_period': 6,
    'rsi_overbought': 60,
    'rsi_oversold': 15,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,
    'bb_std': 2,
    'ma_periods': [20, 50, 200],
}

# 市场状态切换策略配置
MARKET_REGIME_CONFIG = {
    'default_profile': 'daily',
    'profiles': {
        'daily': {
            'timeframe': '1d',
            'buy_threshold': 8.0,
            'entry_rebound_threshold': None,
            'entry_requires_price_rise': False,
            'bear_sell_threshold': 62.0,
            'bear_exit_requires_confirmation': False,
            'recovery_sell_threshold': 62.0,
            'reentry_reset_rsi': 10.0,
            'switch_profit_threshold': 0.10,
            'recovery_monthly_rsi_cap': 35.0,
            'exit_ma_period': 10,
            'trend_ma_period': 20,
            'regime_daily_mid_period': 50,
            'regime_daily_long_period': 200,
            'stop_loss_percent': 0.10,
            'max_holding_bars': None,
            'warmup_days': 450,
        },
        'intraday_1h': {
            'timeframe': '1h',
            'buy_threshold': 8.0,
            'entry_rebound_threshold': 12.0,
            'entry_requires_price_rise': True,
            'bear_sell_threshold': 62.0,
            'bear_exit_requires_confirmation': True,
            'recovery_sell_threshold': 62.0,
            'reentry_reset_rsi': 30.0,
            'switch_profit_threshold': 0.04,
            'recovery_monthly_rsi_cap': 35.0,
            'exit_ma_period': 24,
            'trend_ma_period': 48,
            'regime_daily_mid_period': 50,
            'regime_daily_long_period': 200,
            'stop_loss_percent': 0.03,
            'max_holding_bars': 72,
            'warmup_days': 450,
        },
        'intraday_1h_swing': {
            'timeframe': '1h',
            'buy_threshold': 7.0,
            'entry_rebound_threshold': 18.0,
            'entry_requires_price_rise': True,
            'bear_sell_threshold': 66.0,
            'bear_exit_requires_confirmation': True,
            'recovery_sell_threshold': 66.0,
            'reentry_reset_rsi': 40.0,
            'switch_profit_threshold': 0.06,
            'recovery_monthly_rsi_cap': 35.0,
            'exit_ma_period': 24,
            'trend_ma_period': 48,
            'regime_daily_mid_period': 50,
            'regime_daily_long_period': 200,
            'stop_loss_percent': 0.04,
            'max_holding_bars': 240,
            'warmup_days': 450,
        },
    },
}

# 数据存储配置
DATA_CONFIG = {
    'db_path': './data/trading.db',
    'cache_path': './data/cache',
    'max_retries': 3,
    'retry_delay': 5,
}

# 日志配置
LOG_CONFIG = {
    'log_path': './logs',
    'log_level': 'INFO',
    'max_size': '100MB',
}
