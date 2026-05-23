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
# BINANCE_REST_URL = "https://api.binance.com"
# BINANCE_FUTURES_URL = "https://fapi.binance.com"

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
    'rsi_period': 14,
    'rsi_overbought': 60,
    'rsi_oversold': 15,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,
    'bb_std': 2,
    'ma_periods': [20, 50, 200],
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

