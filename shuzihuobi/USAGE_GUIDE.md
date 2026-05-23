# 📖 系统使用指南

## 🎯 三种使用场景

### 场景1: 快速体验系统 (推荐首先尝试)

**目标**: 在5分钟内了解系统的所有功能

```bash
# 1. 进入项目目录
cd /Users/game-netease/PycharmProjects/binance-quantization/v2

# 2. 验证系统 (检查所有文件和模块是否完整)
python verify.py

# 3. 查看快速开始指南
cat QUICKSTART.md

# 4. 运行演示程序 (会演示各项功能)
python demo.py
```

**输出示例**:
```
演示1: 数据管理功能
✓ 成功获取 100 条K线

演示2: 技术指标功能  
✓ RSI: 45.32
✓ MACD: 0.123456
✓ 大趋势判断: uptrend

演示3: 策略引擎功能
✓ 生成交易信号
  交易对: BTCUSDT
  信号类型: BUY
  入场价格: 45000.00
  信心度: 82%

...以此类推
```

### 场景2: 策略回测和优化

**目标**: 验证策略的历史表现，优化参数

```bash
# 1. 运行回测脚本
python backtest.py

# 2. 查看回测结果 (自动生成)
cat backtest_results.json

# 3. 修改参数进行更多回测
# 编辑 config.py 修改指标参数，然后重新运行
nano config.py
python backtest.py
```

**输出示例**:
```
========== 回测结果 ==========
策略: Multi-Indicator
交易对: BTCUSDT

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

### 场景3: 实时自动交易

**目标**: 启动实时交易系统，自动执行策略

```bash
# 1. 配置币安API密钥
cp .env.example .env
# 编辑 .env，填入你的币安API密钥和钉钉webhook
nano .env

# 2. 可选：配置钉钉通知
# 在钉钉创建机器人并获取webhook URL

# 3. 启动交易系统
python main.py
```

**系统会自动**:
- 每60秒检查一次交易信号
- 识别到信号时执行买卖订单
- 监控持仓的止损/止盈
- 发送钉钉消息通知
- 记录详细的交易日志

## 🔧 常见配置修改

### 修改交易品种

编辑 `config.py`:

```python
TRADING_CONFIG = {
    'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],  # 添加你想交易的品种
    'timeframes': ['1h', '4h', '1d'],
    'testnet': True,  # True=测试网, False=主网
}
```

### 调整风险参数

编辑 `config.py`:

```python
RISK_CONFIG = {
    'max_position': 0.50,          # 修改为50%仓位限制
    'max_daily_loss': 0.05,        # 修改为5%单日亏损限制
    'max_drawdown': 0.20,          # 修改为20%最大回撤
    'stop_loss_percent': 0.05,     # 修改为5%止损
    'take_profit_percent': 0.10,   # 修改为10%止盈
}
```

### 修改指标参数

编辑 `config.py`:

```python
INDICATOR_CONFIG = {
    'rsi_period': 14,              # RSI周期
    'rsi_overbought': 70,          # RSI超买线
    'rsi_oversold': 30,            # RSI超卖线
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,               # 布林带周期
    'bb_std': 2,                   # 布林带标准差倍数
    'ma_periods': [20, 50, 200],   # 移动平均线周期
}
```

## 📚 核心API使用示例

### 示例1: 获取K线数据并分析

```python
from data_manager import DataManager
from indicators import IndicatorAnalyzer

# 创建数据管理器
dm = DataManager()

# 获取BTCUSDT的1小时K线，最近100条
df = dm.get_klines('BTCUSDT', '1h', limit=100)

# 分析所有指标
analyzer = IndicatorAnalyzer()
indicators = analyzer.analyze_all(df)

# 输出指标值
print(f"RSI: {indicators['rsi']:.2f}")
print(f"MACD: {indicators['macd']:.6f}")
print(f"MA20: {indicators['ma20']:.2f}")

# 判断大趋势
trend = analyzer.get_trend(df)
print(f"大趋势: {trend}")  # uptrend, downtrend, consolidation
```

### 示例2: 生成交易信号

```python
from strategy_engine import StrategyEngine

engine = StrategyEngine()

# 生成多指标综合策略信号
signal = engine.multi_indicator_strategy('BTCUSDT', df)

if signal:
    print(f"信号: {signal.signal_type}")
    print(f"价格: {signal.price:.2f}")
    print(f"信心度: {signal.confidence:.0%}")
    print(f"原因: {signal.reasons}")
else:
    print("未生成信号")
```

### 示例3: 执行回测

```python
from backtest_engine import BacktestEngine
from strategy_engine import StrategyEngine

# 创建回测引擎
backtest = BacktestEngine(initial_capital=10000)
engine = StrategyEngine()

# 执行回测
result = backtest.backtest(
    symbol='BTCUSDT',
    df=df,
    strategy_func=engine.multi_indicator_strategy,
    strategy_name='My Strategy'
)

# 查看结果
print(f"初始资金: {result.initial_capital:.2f}")
print(f"最终资金: {result.final_capital:.2f}")
print(f"总收益: {result.total_return:.2%}")
print(f"年化收益: {result.annual_return:.2%}")
print(f"最大回撤: {result.max_drawdown:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"胜率: {result.win_rate:.0%}")
print(f"盈亏比: {result.profit_factor:.2f}")
```

### 示例4: 风险管理

```python
from trade_executor import RiskManager
from config import RISK_CONFIG

# 创建风险管理器
rm = RiskManager(initial_capital=10000, risk_config=RISK_CONFIG)

# 检查是否允许交易
if rm.get_trading_allowed():
    # 开仓
    position = rm.open_position('BTCUSDT', 'LONG', 0.5, 45000)
    
    if position:
        print("开仓成功")
        
        # 更新价格
        rm.update_prices({'BTCUSDT': 45500})
        
        # 检查止损
        if rm.should_stop_loss('BTCUSDT'):
            print("触发止损")
            rm.close_position('BTCUSDT', 45500)
        
        # 检查止盈
        if rm.should_take_profit('BTCUSDT'):
            print("触发止盈")
            rm.close_position('BTCUSDT', 45500)
else:
    print("交易被风险限制暂停")
```

### 示例5: 发送通知

```python
from notifier import NotificationManager

notifier = NotificationManager()

# 发送买入信号通知
notifier.notify_buy_signal(signal)

# 发送风险警告
notifier.notify_risk_warning('stop_loss', '触发止损 -3%')

# 发送错误告警
notifier.notify_error('API_ERROR', 'Connection timeout')
```

## 🐛 常见问题排查

### Q1: 运行demo.py时提示"无数据"

**原因**: 无法连接到币安API（网络问题或API限制）

**解决方案**:
1. 检查网络连接
2. 稍等几秒后重新运行
3. 可以尝试运行 `verify.py` 验证系统其他功能

### Q2: 钉钉没有收到通知

**原因**: webhook URL未配置或不正确

**解决方案**:
1. 在 `.env` 中检查 DINGDING_WEBHOOK 是否配置
2. 验证webhook URL的正确性，格式应为:
   `https://oapi.dingtalk.com/robot/send?access_token=xxx`
3. 在钉钉中创建机器人并获取正确的webhook

### Q3: 回测结果显示 0 交易

**原因**: 
- 数据不足（K线数量太少）
- 策略参数设置过于严格，没有信号触发

**解决方案**:
1. 确保使用足够的历史数据 (建议至少200条K线)
2. 调整策略参数，降低信号触发难度
3. 查看 `backtest_results.json` 获取详细信息

### Q4: "ModuleNotFoundError: No module named 'xxx'"

**原因**: 缺少依赖

**解决方案**:
```bash
# 安装所有依赖
pip install -r requirements.txt

# 或者升级pip
pip install --upgrade pip
pip install -r requirements.txt
```

### Q5: 实时交易系统启动后无反应

**原因**: 可能是正常运行，等待60秒的检查周期

**解决方案**:
1. 等待60秒，系统会输出第一次检查结果
2. 按 Ctrl+C 停止程序
3. 查看 `logs/trading.log` 日志文件了解系统状态

## 📊 理解回测结果

### 关键指标说明

| 指标 | 说明 | 好坏范围 |
|-----|------|---------|
| 总收益 | 整个回测期间的收益率 | 越高越好 |
| 年化收益 | 换算成年化的收益率 | >20% 较好 |
| 最大回撤 | 最大的亏损幅度 | 越小越好 |
| 夏普比率 | 风险调整后的收益 | >1.0 较好，>2.0 很好 |
| 胜率 | 盈利交易占比 | >50% 为正 |
| 盈亏比 | 平均盈利/平均亏损 | >1.5 较好 |

### 如何评估策略

1. **收益性**: 查看总收益和年化收益
   - 高收益未必好（可能高风险）
   - 需要考虑最大回撤和夏普比率

2. **风险性**: 查看最大回撤和夏普比率
   - 最大回撤 < 20% 认为较为安全
   - 夏普比率 > 2.0 认为风险调整后收益很好

3. **稳定性**: 查看胜率和盈亏比
   - 胜率高但盈亏比低 = 赚的小亏的大
   - 胜率低但盈亏比高 = 赚的大亏的小

4. **综合评估**: 平衡收益和风险
   ```
   好策略 = 合理的收益 + 可控的风险 + 良好的稳定性
   ```

## 🚀 快速参考

### 最常用的命令

```bash
# 验证系统
python verify.py

# 查看演示
python demo.py

# 运行回测
python backtest.py

# 启动交易
python main.py

# 查看日志
tail -f logs/trading.log

# 查看配置
cat config.py

# 查看文档
cat README.md
```

### 最常修改的配置

```python
# config.py 中的三个主要配置

# 1. 交易品种
TRADING_CONFIG['symbols'] = ['BTCUSDT', 'ETHUSDT']

# 2. 风险参数
RISK_CONFIG['max_position'] = 0.30

# 3. 指标参数
INDICATOR_CONFIG['rsi_period'] = 14
```

### 最常用的类

```python
DataManager()           # 数据管理
IndicatorAnalyzer()     # 指标分析
StrategyEngine()        # 策略生成
BacktestEngine()        # 回测
RiskManager()           # 风险管理
TradeExecutor()         # 交易执行
NotificationManager()   # 通知系统
```

## 💡 最佳实践

### Do's ✅
- ✅ 先运行回测验证策略有效性
- ✅ 从小资金开始实盘交易
- ✅ 定期检查日志和交易记录
- ✅ 监控风险指标，及时调整参数
- ✅ 保持备份重要配置和数据

### Don'ts ❌
- ❌ 不要跳过回测直接实盘
- ❌ 不要频繁修改参数
- ❌ 不要忽视风险管理
- ❌ 不要公开泄露API密钥
- ❌ 不要依赖单一策略

## 📞 获取帮助

1. **查看文档**: 
   - README.md - 详细功能说明
   - QUICKSTART.md - 快速开始
   - 各模块文件的 docstring - API文档

2. **运行演示**:
   - `python demo.py` - 功能演示
   - `python backtest.py` - 回测演示
   - `python test.py` - 系统测试

3. **检查日志**:
   - `logs/trading.log` - 交易日志
   - `backtest_results.json` - 回测结果

4. **查看源代码**:
   - 每个模块都有详细的注释
   - 关键函数都有 docstring

---

**祝你使用愉快！** 🎉

