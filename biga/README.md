# biga – macOS 菜单栏股票价格小插件

功能：
- 展示指定股票的“实时”（轮询刷新）价格
- macOS 下运行，并在顶部菜单栏展示
- **默认不使用 Yahoo**：默认数据源为 Stooq（无需 API Key）

## 运行环境
- macOS
- Python 3.9+（建议 3.10/3.11）

## 安装依赖

```zsh
cd /Users/game-netease/PycharmProjects/binance-quantization/biga
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动（默认：Stooq）

默认展示 `AAPL`，每 10 秒刷新一次。

```zsh
source .venv/bin/activate
python stockmenubar.py
```

自定义股票和刷新间隔：

```zsh
export BIGA_STOCK_SYMBOL=TSLA
export BIGA_REFRESH_SECONDS=5
python stockmenubar.py
```

### Stooq 的代码规则说明
- `AAPL` 会自动映射成 `aapl.us`
- `TSLA` -> `tsla.us`
- `0700.HK` -> `0700.hk`
- 你也可以直接传入 stooq 原生代码，比如：

```zsh
export BIGA_STOCK_SYMBOL=tsla.us
python stockmenubar.py
```

## 可选数据源：Alpha Vantage（需要 Key）

```zsh
export BIGA_PROVIDER=alphavantage
export BIGA_ALPHA_VANTAGE_KEY=你的key
export BIGA_STOCK_SYMBOL=TSLA
python stockmenubar.py
```

## 说明
- Stooq 是免费数据源，可能存在延迟。
- 如果遇到网络/风控导致的拉取失败，菜单栏会显示 `ERR`，并在菜单里显示错误原因。
