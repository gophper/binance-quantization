# 自动数字货币交易平台 - MVP系统

## 📋 系统概述

这是一个基于需求文档实现的自动化数字货币交易平台MVP（最小可行产品），支持实时交易、回测、风险管理和钉钉通知。

## 🏗️ 系统架构

### 核心模块

1. **数据层** (`data_manager.py`)
   - 多交易所实时K线数据接入（币安合约）
   - 支持1m/5m/15m/30m/1h/4h/1d等多个时间框架
   - 历史数据持久化存储（SQLite）
   - 指标预计算和缓存

2. **指标系统** (`indicators.py`)
   - 趋势类：MA、EMA、MACD、布林带
   - 动量类：RSI、Stochastic(KDJ)、CCI
   - 成交量类：OBV、成交量变化率
   - 自动化指标分析

3. **策略引擎** (`strategy_engine.py`)
   - 多指标组合决策（AND/OR/NOT逻辑）
   - 权重评分系统
   - 三种内置策略：
     * 增强型RSI网格策略
     * 简单MA交叉策略
     * 多指标综合策略
   - 大趋势判断和过滤

4. **交易执行** (`trade_executor.py`)
   - 风险管理系统
   - 仓位管理和限制
   - 止损/止盈自动化
   - 订单管理

5. **回测引擎** (`backtest_engine.py`)
   - 支持历史数据回测
   - 手续费和滑点模拟
   - 详细的绩效指标计算
   - 策略对比分析

6. **通知系统** (`notifier.py`)
   - 钉钉实时通知
   - 买卖信号推送
   - 风险预警
   - 日报总结

7. **主程序** (`main.py`)
   - 实时交易系统
   - 自动信号识别和执行
   - 持仓监控
   - 完整的日志记录

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
DINGDING_WEBHOOK=your_dingding_webhook_url
```

### 3. 配置系统参数

编辑 `config.py` 修改交易对、风险参数等：

```python
TRADING_CONFIG = {
    'symbols': ['BTCUSDT', 'ETHUSDT'],
    'timeframes': ['1h', '4h', '1d'],
    'testnet': True,
}

RISK_CONFIG = {
    'max_position': 0.30,           # 单标的最大仓位：30%
    'max_daily_loss': 0.02,         # 单日最大亏损：2%
    'max_drawdown': 0.15,           # 全仓最大回撤：15%
    'stop_loss_percent': 0.03,      # 止损：3%
    'take_profit_percent': 0.05,    # 止盈：5%
}
```

## 📊 使用方式

### 方式1：运行回测

```bash
python backtest.py
```

输出回测结果并保存到 `backtest_results.json`

### 方式2：运行实时交易系统

```bash
python main.py
```

系统会：
- 每60秒检查一次交易信号
- 自动执行买卖订单
- 监控止损/止盈
- 发送钉钉通知
- 记录详细日志

## 🎯 核心策略详解

### 增强型RSI网格策略

基于需求文档设计的多层确认机制：

```
第一层：技术指标信号（快速响应）
  - RSI < 25 (权重: 0.4)
  - 成交量放大 > 150% (权重: 0.3)
  - 价格突破布林下轨 (权重: 0.3)
  - 总分 > 0.75时触发买入

第二层：成交量确认（防止假突破）
  - 成交量必须放大

第三层：大趋势过滤（避免逆势操作）
  - 上升趋势：只做多
  - 下降趋势：谨慎做多
  - 震荡趋势：双向

第四层：动态仓位管理
  - RSI 20-25: 10% 仓位
  - RSI 15-20: 15% 仓位
  - RSI 10-15: 20% 仓位
  - RSI < 10:  25% 仓位
```

### 多指标综合策略

综合多个指标的权重评分：

- RSI 超卖/超买 (权重: 0.25)
- MACD 金叉/死叉 (权重: 0.25)
- 布林带突破 (权重: 0.2)
- KDJ 超卖 (权重: 0.15)
- 成交量放大 (权重: 0.15)

总评分 >= 0.7 时触发信号

## 📈 风险管理

系统内置完整的风险控制：

1. **仓位管理**
   - 单标的最大仓位限制（默认30%）
   - 自动计算仓位大小

2. **资金管理**
   - 单日最大亏损限制（默认2%）
   - 全仓最大回撤限制（默认15%）

3. **价格保护**
   - 自动止损（默认3%）
   - 自动止盈（默认5%）
   - 移动止损支持

4. **风险预警**
   - 触发限制时自动停止交易
   - 钉钉实时预警通知

## 📁 项目结构

```
v2/
├── config.py              # 配置文件
├── data_manager.py        # 数据管理
├── indicators.py          # 技术指标
├── strategy_engine.py     # 策略引擎
├── backtest_engine.py     # 回测引擎
├── trade_executor.py      # 交易执行
├── notifier.py            # 通知系统
├── main.py                # 实时交易主程序
├── backtest.py            # 回测脚本
├── requirements.txt       # 依赖列表
├── README.md              # 本文件
└── data/                  # 数据文件夹
    ├── cache/             # 缓存数据
    └── trading.db         # 数据库
```

## 🔧 核心API

### DataManager 数据管理

```python
dm = DataManager()

# 获取K线数据
df = dm.get_klines('BTCUSDT', '1h', limit=100)

# 获取当前价格
price = dm.get_current_price('BTCUSDT')

# 保存交易信号
dm.save_signal('BTCUSDT', 'BUY', 50000, 0.85, indicators)
```

### IndicatorAnalyzer 指标分析

```python
analyzer = IndicatorAnalyzer()

# 分析所有指标
indicators = analyzer.analyze_all(df)

# 获取大趋势
trend = analyzer.get_trend(df)
```

### StrategyEngine 策略引擎

```python
engine = StrategyEngine()

# 执行增强型RSI网格策略
signal = engine.enhanced_rsi_grid_strategy('BTCUSDT', df)

# 执行多指标综合策略
signal = engine.multi_indicator_strategy('BTCUSDT', df)
```

### BacktestEngine 回测

```python
backtest = BacktestEngine(initial_capital=10000)

# 运行回测
result = backtest.backtest(
    'BTCUSDT',
    df,
    strategy_func,
    'My Strategy'
)

# 查看结果
print(result.total_return)     # 总收益
print(result.max_drawdown)     # 最大回撤
print(result.sharpe_ratio)     # 夏普比率
```

### RiskManager 风险管理

```python
rm = RiskManager(10000, RISK_CONFIG)

# 检查仓位限制
if rm.check_position_limit('BTCUSDT', qty, price):
    # 开仓
    position = rm.open_position('BTCUSDT', 'LONG', qty, price)

# 更新价格
rm.update_prices({'BTCUSDT': 50000})

# 获取持仓汇总
summary = rm.get_position_summary()
```

### NotificationManager 通知

```python
notifier = NotificationManager()

# 发送买入信号通知
notifier.notify_buy_signal(signal)

# 发送卖出信号通知
notifier.notify_sell_signal(signal)

# 发送风险警告
notifier.notify_risk_warning('stop_loss', '触发止损')
```

## 📊 回测结果示例

```
========== 回测结果 ==========
策略: Multi-Indicator
交易对: BTCUSDT
时间范围: 2024-01-01 到 2024-01-31

资金统计:
  初始资金: 10000.00
  最终资金: 10850.00
  总收益: 8.50%
  年化收益: 104.68%

风险指标:
  最大回撤: -2.45%
  夏普比率: 2.34

交易统计:
  总交易数: 12
  盈利交易: 9
  亏损交易: 3
  胜率: 75.00%
  盈亏比: 3.45
  平均盈利: 1.25%
  平均亏损: -0.85%
```

## 📝 日志

所有交易和系统事件都会记录到日志文件：

```
logs/
└── trading.log    # 实时交易日志
```

## ⚙️ 高级配置

### 修改指标参数

编辑 `config.py` 中的 `INDICATOR_CONFIG`：

```python
INDICATOR_CONFIG = {
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,
    'bb_std': 2,
    'ma_periods': [20, 50, 200],
}
```

### 自定义策略

创建新的策略函数：

```python
def my_custom_strategy(symbol: str, df: pd.DataFrame) -> Signal:
    """自定义策略"""
    analyzer = IndicatorAnalyzer()
    indicators = analyzer.analyze_all(df)
    
    # 实现你的交易逻辑
    if your_condition:
        return Signal(
            symbol=symbol,
            signal_type='BUY',
            price=indicators['current_price'],
            confidence=0.8,
            reasons=['你的理由'],
            indicators=indicators
        )
    
    return None

# 在回测中使用
result = backtest.backtest('BTCUSDT', df, my_custom_strategy)
```

## 🐛 故障排除

### 连接币安API失败

1. 检查网络连接
2. 验证API密钥和密钥是否正确
3. 确认API密钥有正确的权限

### 没有收到钉钉通知

1. 检查DINGDING_WEBHOOK配置
2. 测试webhook URL的有效性
3. 检查钉钉机器人是否正确配置

### 回测数据不足

1. 确保有足够的历史数据
2. 增加limit参数获取更多K线
3. 使用较长的时间框架

## 📚 参考资源

- [币安API文档](https://binance-docs.github.io/apidocs/)
- [技术分析基础](https://www.investopedia.com/terms/t/technicalanalysis.asp)
- [量化交易基础](https://github.com/ccxt/ccxt)

## 📄 许可证

MIT License

## 👨‍💻 开发者

基于需求文档的MVP实现

## 🔄 后续开发计划

### 第二期功能
- [ ] 机器学习信号优化
- [ ] 扩展指标库到30+
- [ ] 策略市场功能
- [ ] 可视化策略构建器
- [ ] Web后台管理界面
- [ ] 移动端APP

### 第三期功能
- [ ] 跨交易所套利策略
- [ ] 期权对冲策略
- [ ] 社交跟单系统
- [ ] 机构级风控系统

---

**最后更新**: 2024年

**状态**: MVP版本 - 可用于测试和演示

**注意**: 在实盘交易前，请充分测试策略并理解其风险。虚拟交易可能无法完全反映实盘交易的滑点和费用。

