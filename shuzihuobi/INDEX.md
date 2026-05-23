# 📑 系统文档索引

> 快速导航：找到你需要的文档和功能

## 🎯 按使用场景查找

### 我想快速了解这个系统 (5分钟)
1. **查看** → `PROJECT_SUMMARY.md` 项目总结
2. **运行** → `python verify.py` 系统验证
3. **体验** → `python demo.py` 功能演示

👉 **推荐阅读**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

---

### 我想快速开始使用 (15分钟)
1. **安装** → `pip install -r requirements.txt`
2. **配置** → `cp .env.example .env`
3. **学习** → `cat QUICKSTART.md` 快速开始
4. **运行** → `python demo.py` 看演示

👉 **推荐阅读**: [QUICKSTART.md](QUICKSTART.md)

---

### 我想理解系统架构 (30分钟)
1. **读文档** → `README.md` 了解全景
2. **看代码** → `config.py` 了解配置
3. **研究模块** → 各 `.py` 文件的docstring
4. **查API** → [USAGE_GUIDE.md](USAGE_GUIDE.md) 中的代码示例

👉 **推荐阅读**: [README.md](README.md)

---

### 我想验证交易策略 (10分钟)
1. **运行回测** → `python backtest.py`
2. **查看结果** → `cat backtest_results.json`
3. **理解指标** → [USAGE_GUIDE.md#理解回测结果](USAGE_GUIDE.md)

👉 **推荐阅读**: [USAGE_GUIDE.md](USAGE_GUIDE.md) 的"理解回测结果"部分

---

### 我想启动实时交易 (30分钟)
1. **配置密钥** → 编辑 `.env` 文件
2. **理解系统** → 阅读 `main.py` 的注释
3. **查看日志** → `cat logs/trading.log`
4. **启动交易** → `python main.py`

👉 **推荐阅读**: [USAGE_GUIDE.md#场景3](USAGE_GUIDE.md) 和 `main.py`

---

### 我想自定义策略 (1-2小时)
1. **学习API** → [USAGE_GUIDE.md#核心API使用示例](USAGE_GUIDE.md)
2. **看示例** → 研究 `strategy_engine.py` 中的内置策略
3. **创建策略** → 在 `strategy_engine.py` 中添加新函数
4. **测试策略** → 在 `backtest.py` 中调用你的策略

👉 **推荐阅读**: [strategy_engine.py](strategy_engine.py) 源代码

---

## 📚 按功能查找

### 数据管理
| 需求 | 文件 | 说明 |
|-----|------|------|
| 获取K线数据 | `data_manager.py` | DataManager.get_klines() |
| 保存信号 | `data_manager.py` | DataManager.save_signal() |
| 查询当前价格 | `data_manager.py` | DataManager.get_current_price() |
| 使用示例 | `USAGE_GUIDE.md` | 示例1: 获取K线数据 |

### 技术指标
| 需求 | 文件 | 说明 |
|-----|------|------|
| 计算指标 | `indicators.py` | IndicatorCalculator 类 |
| 分析指标 | `indicators.py` | IndicatorAnalyzer 类 |
| 所有支持的指标 | `README.md` | 完整指标列表 |
| 使用示例 | `USAGE_GUIDE.md` | 示例1 中的指标调用 |

### 交易策略
| 需求 | 文件 | 说明 |
|-----|------|------|
| 生成信号 | `strategy_engine.py` | StrategyEngine 类 |
| 内置策略 | `strategy_engine.py` | 3种策略实现 |
| 自定义策略 | `strategy_engine.py` | 参考内置策略编写 |
| 使用示例 | `USAGE_GUIDE.md` | 示例2: 生成交易信号 |

### 回测系统
| 需求 | 文件 | 说明 |
|-----|------|------|
| 运行回测 | `backtest_engine.py` | BacktestEngine 类 |
| 回测脚本 | `backtest.py` | 多策略回测脚本 |
| 性能指标 | `README.md` | 回测结果说明 |
| 使用示例 | `USAGE_GUIDE.md` | 示例3: 执行回测 |

### 风险管理
| 需求 | 文件 | 说明 |
|-----|------|------|
| 风险控制 | `trade_executor.py` | RiskManager 类 |
| 订单管理 | `trade_executor.py` | TradeExecutor 类 |
| 风险参数 | `config.py` | RISK_CONFIG 字典 |
| 使用示例 | `USAGE_GUIDE.md` | 示例4: 风险管理 |

### 通知系统
| 需求 | 文件 | 说明 |
|-----|------|------|
| 钉钉通知 | `notifier.py` | DingDingNotifier 类 |
| 通知管理 | `notifier.py` | NotificationManager 类 |
| 配置webhook | `.env.example` | DINGDING_WEBHOOK |
| 使用示例 | `USAGE_GUIDE.md` | 示例5: 发送通知 |

### 实时交易
| 需求 | 文件 | 说明 |
|-----|------|------|
| 主程序 | `main.py` | TradingSystem 类 |
| 启动交易 | `main.py` | 运行脚本即可启动 |
| 配置API | `.env.example` | BINANCE_API_KEY 等 |
| 查看日志 | `logs/trading.log` | 交易日志文件 |

---

## 🔍 按关键词查找

### RSI (相对强弱指标)
- **定义**: `indicators.py` - `calculate_rsi()` 函数
- **应用**: `strategy_engine.py` - RSI网格策略
- **配置**: `config.py` - `INDICATOR_CONFIG['rsi_period']`
- **文档**: `README.md` - 技术指标部分

### MACD (指数平滑移动平均线)
- **定义**: `indicators.py` - `calculate_macd()` 函数
- **应用**: `strategy_engine.py` - 多指标策略
- **配置**: `config.py` - MACD 参数
- **文档**: `README.md` - 技术指标部分

### 布林带 (Bollinger Bands)
- **定义**: `indicators.py` - `calculate_bollinger_bands()` 函数
- **应用**: `strategy_engine.py` - 价格突破信号
- **配置**: `config.py` - `bb_period`, `bb_std`
- **文档**: `README.md` - 技术指标部分

### 移动平均线 (MA/EMA)
- **定义**: `indicators.py` - `calculate_sma()`, `calculate_ema()` 函数
- **应用**: `strategy_engine.py` - MA交叉策略
- **配置**: `config.py` - `ma_periods`
- **文档**: `README.md` - 技术指标部分

### 回测 (Backtest)
- **运行**: `python backtest.py`
- **代码**: `backtest_engine.py` - BacktestEngine 类
- **脚本**: `backtest.py` - 回测执行脚本
- **结果**: `backtest_results.json`
- **理解**: `USAGE_GUIDE.md` - 理解回测结果

### 风险管理 (Risk Management)
- **配置**: `config.py` - RISK_CONFIG
- **代码**: `trade_executor.py` - RiskManager 类
- **参数**: max_position, max_daily_loss, max_drawdown
- **说明**: `README.md` - 风险管理部分

### 止损/止盈 (Stop Loss/Take Profit)
- **配置**: `config.py` - stop_loss_percent, take_profit_percent
- **实现**: `trade_executor.py` - `should_stop_loss()`, `should_take_profit()`
- **说明**: `README.md` - 风险管理部分

### 钉钉通知 (DingDing)
- **配置**: `.env` 文件 - DINGDING_WEBHOOK
- **代码**: `notifier.py` - DingDingNotifier 类
- **说明**: `USAGE_GUIDE.md` - Q2: 钉钉没有收到通知

---

## 📖 文档导航

### 核心文档
| 文档 | 内容 | 阅读时间 |
|-----|------|--------|
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | 项目总结和清单 | 10 分钟 |
| [README.md](README.md) | 完整功能说明 | 20 分钟 |
| [QUICKSTART.md](QUICKSTART.md) | 快速开始指南 | 5 分钟 |
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | 详细使用说明 | 30 分钟 |
| [DELIVERY.md](DELIVERY.md) | 交付文档 | 15 分钟 |

### 配置和代码
| 文件 | 内容 | 用途 |
|-----|------|------|
| [config.py](config.py) | 系统配置 | 修改参数 |
| [.env.example](.env.example) | 环境变量示例 | 配置API密钥 |
| 各 `.py` 文件 | 源代码 | 学习实现 |

---

## 🚀 快速命令参考

```bash
# 系统验证
python verify.py

# 功能演示
python demo.py

# 策略回测
python backtest.py

# 实时交易
python main.py

# 查看帮助
cat README.md
cat QUICKSTART.md
cat USAGE_GUIDE.md
```

---

## 📋 问题排查导航

### 系统问题
- **模块导入错误** → [USAGE_GUIDE.md#Q4](USAGE_GUIDE.md) 或运行 `python verify.py`
- **缺少依赖** → 运行 `pip install -r requirements.txt`
- **文件缺失** → 运行 `python verify.py` 检查

### 数据问题
- **无法获取数据** → [USAGE_GUIDE.md#Q1](USAGE_GUIDE.md) 检查网络或API
- **回测数据不足** → [USAGE_GUIDE.md#Q3](USAGE_GUIDE.md) 增加K线数量

### 通知问题
- **钉钉没有收到通知** → [USAGE_GUIDE.md#Q2](USAGE_GUIDE.md) 检查webhook配置

### 交易问题
- **系统无反应** → [USAGE_GUIDE.md#Q5](USAGE_GUIDE.md) 等待60秒或检查日志

### 策略问题
- **没有生成信号** → 检查 `backtest.py` 输出或查看 `config.py` 参数

---

## 🎓 学习建议

### 如果你是初学者
1. 读 [QUICKSTART.md](QUICKSTART.md) - 5分钟快速开始
2. 运行 `python demo.py` - 看功能演示
3. 运行 `python backtest.py` - 看回测结果
4. 读 [README.md](README.md) - 理解各个模块

### 如果你懂交易
1. 读 [README.md](README.md) - 了解系统架构
2. 查看 `strategy_engine.py` - 理解内置策略
3. 参考 `config.py` - 理解参数配置
4. 运行 `python backtest.py` - 回测你的想法

### 如果你是开发者
1. 读 [DELIVERY.md](DELIVERY.md) - 了解项目范围
2. 查看 `PROJECT_SUMMARY.md` - 理解代码统计
3. 研究源代码 - 学习架构设计
4. 运行 `python test.py` - 验证功能

---

## 💡 常用链接

### 立即开始
- 🚀 **最快方式**: `python verify.py` + `python demo.py`
- 📖 **完整方式**: 读 `README.md` + 运行 `python backtest.py`
- 🎯 **实用方式**: 读 `QUICKSTART.md` + 改 `config.py` + 运行 `python backtest.py`

### 深入学习
- 📚 **策略开发**: 研究 `strategy_engine.py`
- 🔧 **参数优化**: 修改 `config.py` 后运行 `python backtest.py`
- 💻 **API使用**: 参考 `USAGE_GUIDE.md` 中的代码示例
- 📊 **回测分析**: 查看 `backtest_results.json`

### 实时交易
- 🔑 **配置密钥**: 编辑 `.env` 文件
- ▶️ **启动系统**: `python main.py`
- 📋 **查看日志**: `tail -f logs/trading.log`
- ⚠️ **风险控制**: 检查 `config.py` 中的 RISK_CONFIG

---

## 📞 常见问题快速解答

**Q: 系统支持哪些功能?**  
A: 数据管理、15+技术指标、3种交易策略、完整回测、风险控制、钉钉通知。详见 [README.md](README.md)

**Q: 如何快速开始?**  
A: 运行 `python verify.py` 和 `python demo.py`，5分钟了解所有功能。

**Q: 如何回测策略?**  
A: 运行 `python backtest.py`，查看 `backtest_results.json` 结果。

**Q: 如何实时交易?**  
A: 配置 `.env` 文件，运行 `python main.py`。需要币安API密钥。

**Q: 如何自定义策略?**  
A: 在 `strategy_engine.py` 中添加新函数，参考现有策略代码。

**Q: 如何修改参数?**  
A: 编辑 `config.py` 文件中的配置参数。

---

## 🎯 下一步

### 推荐流程
1. ✅ 运行 `python verify.py` (1分钟)
2. ✅ 运行 `python demo.py` (2分钟)
3. ✅ 阅读 [QUICKSTART.md](QUICKSTART.md) (5分钟)
4. ✅ 运行 `python backtest.py` (1分钟)
5. ✅ 阅读 [README.md](README.md) (20分钟)
6. ✅ 查看 [USAGE_GUIDE.md](USAGE_GUIDE.md) (30分钟)

**总计**: 不到1小时，完全掌握系统！

---

**祝你使用愉快！** 🎉

*最后更新: 2024年*

