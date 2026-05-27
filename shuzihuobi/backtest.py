# -*- coding: utf-8 -*-
"""RSI R1xR2 网格回测脚本"""

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import sys
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd

from backtest_engine import BacktestEngine, BacktestResult
from config import INDICATOR_CONFIG, TRADING_CONFIG
from data_manager import DataManager
from indicators import IndicatorCalculator
from strategy_engine import StrategyEngine

logging.basicConfig(
    level="INFO",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class BacktestRunner:
    """回测执行器"""

    def __init__(self, initial_capital: float = 10000):
        self.strategy_engine = StrategyEngine()
        self.initial_capital = initial_capital
        self.output_dir = Path("data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_sources = [
            ("mainnet_futures", DataManager(testnet=False, market="futures")),
            ("mainnet_spot", DataManager(testnet=False, market="spot")),
        ]

    def load_rsi_backtest_data(
        self,
        symbol: str,
        timeframe: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        warmup_days: int = 60,
    ) -> pd.DataFrame:
        """加载回测数据并预计算 RSI"""
        fetch_start = start_time - timedelta(days=warmup_days)
        last_error = None

        for source_name, data_manager in self.data_sources:
            try:
                df = data_manager.get_klines(symbol, timeframe, limit=1000)
                if df.empty:
                    continue

                df = df.sort_values("open_time").drop_duplicates(subset=["open_time"]).reset_index(drop=True)
                df["open_time"] = pd.to_datetime(df["open_time"])
                df["close_time"] = pd.to_datetime(df["close_time"])
                df = df[(df["open_time"] >= fetch_start) & (df["close_time"] <= end_time)].reset_index(drop=True)

                if df.empty:
                    continue

                if df["close"].nunique() <= 1:
                    logger.warning("%s 数据源价格几乎不变，跳过: %s", source_name, symbol)
                    continue

                df["rsi"] = IndicatorCalculator.calculate_rsi(
                    df["close"],
                    INDICATOR_CONFIG["rsi_period"],
                )

                execution_df = df[df["open_time"] >= start_time].reset_index(drop=True)
                if execution_df.empty:
                    continue

                logger.info("回测使用数据源: %s", source_name)
                return execution_df
            except Exception as exc:
                last_error = exc

        if last_error:
            raise ValueError(
                f"{symbol} 在 {start_time.date()} 至 {end_time.date()} 区间内没有可用的真实历史数据: {last_error}"
            ) from last_error

        raise ValueError(f"{symbol} 在 {start_time.date()} 至 {end_time.date()} 区间内没有可用的真实历史数据")

    def run_single_backtest(
        self,
        symbol: str,
        df: pd.DataFrame,
        r1: int,
        r2: int,
        stop_loss_percent: float,
        max_holding_period: pd.DateOffset,
    ) -> BacktestResult:
        """执行单个参数组合回测"""
        engine = BacktestEngine(initial_capital=self.initial_capital)
        strategy = self.strategy_engine.create_rsi_threshold_strategy(r1, r2)
        strategy_name = f"RSI_R1_{r1}_R2_{r2}"

        return engine.backtest(
            symbol=symbol,
            df=df,
            strategy_func=strategy,
            strategy_name=strategy_name,
            stop_loss_percent=stop_loss_percent,
            max_holding_period=max_holding_period,
        )

    def run_rsi_grid_backtest(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_time: str = "2025-08-25",
        end_time: datetime = None,
        stop_loss_percent: float = 0.10,
    ) -> Dict:
        """执行 RSI R1xR2 网格回测并导出报告"""
        start_ts = pd.Timestamp(start_time)
        end_ts = pd.Timestamp(end_time or datetime.utcnow())

        df = self.load_rsi_backtest_data(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_ts,
            end_time=end_ts,
        )

        logger.info(
            "加载数据完成: %s %s，共 %s 根K线，范围 %s 到 %s",
            symbol,
            timeframe,
            len(df),
            df["open_time"].iloc[0],
            df["close_time"].iloc[-1],
        )

        combo_rows: List[dict] = []
        result_map: Dict[str, BacktestResult] = {}

        for r1 in range(0, 31):
            for r2 in range(60, 101):
                result = self.run_single_backtest(
                    symbol=symbol,
                    df=df,
                    r1=r1,
                    r2=r2,
                    stop_loss_percent=stop_loss_percent,
                    max_holding_period=pd.DateOffset(months=1),
                )
                combo_key = f"R1={r1},R2={r2}"
                result_map[combo_key] = result
                combo_rows.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "r1": r1,
                        "r2": r2,
                        "strategy_name": result.strategy_name,
                        "start_time": result.start_time.isoformat(),
                        "end_time": result.end_time.isoformat(),
                        "total_return": result.total_return,
                        "annual_return": result.annual_return,
                        "max_drawdown": result.max_drawdown,
                        "sharpe_ratio": result.sharpe_ratio,
                        "win_rate": result.win_rate,
                        "profit_factor": result.profit_factor,
                        "total_trades": result.total_trades,
                        "winning_trades": result.winning_trades,
                        "losing_trades": result.losing_trades,
                        "avg_win": result.avg_win,
                        "avg_loss": result.avg_loss,
                        "final_capital": result.final_capital,
                    }
                )

        summary_df = pd.DataFrame(combo_rows)
        ranked_best = summary_df.sort_values(
            by=["total_return", "annual_return", "max_drawdown", "win_rate", "sharpe_ratio"],
            ascending=[False, False, False, False, False],
        ).reset_index(drop=True)
        ranked_worst = summary_df.sort_values(
            by=["total_return", "annual_return", "max_drawdown", "win_rate", "sharpe_ratio"],
            ascending=[True, True, True, True, True],
        ).reset_index(drop=True)

        best_row = ranked_best.iloc[0]
        worst_row = ranked_worst.iloc[0]
        best_key = f"R1={int(best_row['r1'])},R2={int(best_row['r2'])}"
        worst_key = f"R1={int(worst_row['r1'])},R2={int(worst_row['r2'])}"
        best_result = result_map[best_key]
        worst_result = result_map[worst_key]

        report = self._build_analysis_report(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_ts,
            end_time=end_ts,
            summary_df=summary_df,
            ranked_best=ranked_best,
            ranked_worst=ranked_worst,
            best_result=best_result,
            worst_result=worst_result,
        )

        output_paths = self._export_outputs(
            df=df,
            summary_df=summary_df,
            report=report,
            best_result=best_result,
            worst_result=worst_result,
        )

        logger.info("网格回测完成，共测试 %s 个组合", len(summary_df))
        logger.info("最佳组合: %s", best_key)
        logger.info("最差组合: %s", worst_key)

        return {
            "summary_df": summary_df,
            "best_result": best_result,
            "worst_result": worst_result,
            "report": report,
            "output_paths": output_paths,
        }

    def _build_analysis_report(
        self,
        symbol: str,
        timeframe: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        summary_df: pd.DataFrame,
        ranked_best: pd.DataFrame,
        ranked_worst: pd.DataFrame,
        best_result: BacktestResult,
        worst_result: BacktestResult,
    ) -> str:
        """生成分析报告"""
        profitable_count = int((summary_df["total_return"] > 0).sum())
        losing_count = int((summary_df["total_return"] <= 0).sum())

        best_r1_avg = summary_df.groupby("r1")["total_return"].mean().sort_values(ascending=False)
        best_r2_avg = summary_df.groupby("r2")["total_return"].mean().sort_values(ascending=False)
        worst_r1_avg = summary_df.groupby("r1")["total_return"].mean().sort_values(ascending=True)
        worst_r2_avg = summary_df.groupby("r2")["total_return"].mean().sort_values(ascending=True)

        top10 = self._format_summary_table(ranked_best.head(10))
        bottom10 = self._format_summary_table(ranked_worst.head(10))

        return f"""# RSI R1xR2 网格回测分析报告

## 回测设置

- 交易对：`{symbol}`
- 周期：`{timeframe}`
- RSI 设置：`RSI({INDICATOR_CONFIG['rsi_period']}) + Wilder`
- 回测区间：`{start_time.date()}` 至 `{end_time.date()}`
- 买入条件：`RSI < R1`
- 卖出条件：`RSI > R2`
- 止损条件：买入后相对买入价下跌 `10%`
- 超时卖出：持有满 `1` 个月强制卖出
- 参数网格：`R1 = 0..30`，`R2 = 60..100`
- 组合总数：`{len(summary_df)}`

## 总览

- 盈利组合数：`{profitable_count}`
- 亏损或持平组合数：`{losing_count}`
- 平均总收益率：`{summary_df['total_return'].mean():.2%}`
- 中位数总收益率：`{summary_df['total_return'].median():.2%}`
- 平均最大回撤：`{summary_df['max_drawdown'].mean():.2%}`
- 平均胜率：`{summary_df['win_rate'].mean():.2%}`

## 最佳组合

- 参数：`R1={best_result.strategy_name.split('_')[2]}`，`R2={best_result.strategy_name.split('_')[4]}`
- 总收益率：`{best_result.total_return:.2%}`
- 年化收益率：`{best_result.annual_return:.2%}`
- 最大回撤：`{best_result.max_drawdown:.2%}`
- 胜率：`{best_result.win_rate:.2%}`
- 总交易数：`{best_result.total_trades}`
- 盈亏比：`{best_result.profit_factor:.2f}`

## 最差组合

- 参数：`R1={worst_result.strategy_name.split('_')[2]}`，`R2={worst_result.strategy_name.split('_')[4]}`
- 总收益率：`{worst_result.total_return:.2%}`
- 年化收益率：`{worst_result.annual_return:.2%}`
- 最大回撤：`{worst_result.max_drawdown:.2%}`
- 胜率：`{worst_result.win_rate:.2%}`
- 总交易数：`{worst_result.total_trades}`
- 盈亏比：`{worst_result.profit_factor:.2f}`

## Top 10 组合

```text
{top10}
```

## Bottom 10 组合

```text
{bottom10}
```

## 参数表现观察

- 平均表现最好的 `R1`：`{int(best_r1_avg.index[0])}`，平均总收益率 ` {best_r1_avg.iloc[0]:.2%} `
- 平均表现最差的 `R1`：`{int(worst_r1_avg.index[0])}`，平均总收益率 ` {worst_r1_avg.iloc[0]:.2%} `
- 平均表现最好的 `R2`：`{int(best_r2_avg.index[0])}`，平均总收益率 ` {best_r2_avg.iloc[0]:.2%} `
- 平均表现最差的 `R2`：`{int(worst_r2_avg.index[0])}`，平均总收益率 ` {worst_r2_avg.iloc[0]:.2%} `

## 结论

- 表现最好的组合集中在更容易触发买点/更明确触发卖点的参数附近，可从 `Top 10` 继续做稳健性复核。
- 表现较差的组合通常出现在买入过于苛刻或卖出阈值导致退出不理想的区域，建议优先规避 `Bottom 10` 附近参数。
- 已额外导出最佳与最差组合的完整交易明细，便于继续检查持仓时长、退出原因和单笔盈亏分布。
"""

    def _export_outputs(
        self,
        df: pd.DataFrame,
        summary_df: pd.DataFrame,
        report: str,
        best_result: BacktestResult,
        worst_result: BacktestResult,
    ) -> Dict[str, str]:
        """导出结果文件"""
        summary_csv = self.output_dir / "rsi_grid_summary.csv"
        summary_json = self.output_dir / "rsi_grid_summary.json"
        report_path = self.output_dir / "rsi_grid_report.md"
        best_trades_csv = self.output_dir / "rsi_grid_best_trades.csv"
        worst_trades_csv = self.output_dir / "rsi_grid_worst_trades.csv"
        best_chart_path = self.output_dir / "rsi_grid_best_chart.png"
        worst_chart_path = self.output_dir / "rsi_grid_worst_chart.png"

        summary_df.to_csv(summary_csv, index=False, encoding="utf-8-sig")
        summary_df.to_json(summary_json, orient="records", force_ascii=False, indent=2)
        report_path.write_text(report, encoding="utf-8")

        self._trades_to_dataframe(best_result.trades).to_csv(best_trades_csv, index=False, encoding="utf-8-sig")
        self._trades_to_dataframe(worst_result.trades).to_csv(worst_trades_csv, index=False, encoding="utf-8-sig")

        bundle = {
            "best_result": best_result.to_dict(include_trades=True),
            "worst_result": worst_result.to_dict(include_trades=True),
        }
        trades_json = self.output_dir / "rsi_grid_extremes.json"
        trades_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

        self._generate_trade_chart(df, best_result, best_chart_path, "Best Combo")
        self._generate_trade_chart(df, worst_result, worst_chart_path, "Worst Combo")

        return {
            "summary_csv": str(summary_csv),
            "summary_json": str(summary_json),
            "report": str(report_path),
            "best_trades_csv": str(best_trades_csv),
            "worst_trades_csv": str(worst_trades_csv),
            "extremes_json": str(trades_json),
            "best_chart": str(best_chart_path),
            "worst_chart": str(worst_chart_path),
        }

    def _generate_trade_chart(self, df: pd.DataFrame, result: BacktestResult, output_path: Path, title_prefix: str) -> None:
        """生成带买卖点标注的趋势图"""
        chart_df = df.copy()
        chart_df["open_time"] = pd.to_datetime(chart_df["open_time"])
        chart_df["close_time"] = pd.to_datetime(chart_df["close_time"])

        r1, r2 = self._parse_thresholds(result.strategy_name)
        if "rsi" not in chart_df.columns:
            chart_df["rsi"] = IndicatorCalculator.calculate_rsi(chart_df["close"], INDICATOR_CONFIG["rsi_period"])

        fig, (price_ax, rsi_ax) = plt.subplots(
            2,
            1,
            figsize=(18, 10),
            sharex=True,
            gridspec_kw={"height_ratios": [3, 1]},
        )

        price_ax.plot(chart_df["close_time"], chart_df["close"], color="#2563eb", linewidth=1.6, label="Close")
        price_ax.set_title(
            f"{title_prefix} Trend - {result.symbol} - {result.strategy_name}\n"
            f"RSI({INDICATOR_CONFIG['rsi_period']}) Wilder | Total Return {result.total_return:.2%} | Max Drawdown {result.max_drawdown:.2%} | Win Rate {result.win_rate:.2%}"
        )
        price_ax.set_ylabel("Price")
        price_ax.grid(alpha=0.2)

        rsi_ax.plot(
            chart_df["close_time"],
            chart_df["rsi"],
            color="#7c3aed",
            linewidth=1.2,
            label=f"RSI({INDICATOR_CONFIG['rsi_period']})",
        )
        rsi_ax.axhline(r1, color="#16a34a", linestyle="--", linewidth=1, label=f"R1={r1}")
        rsi_ax.axhline(r2, color="#dc2626", linestyle="--", linewidth=1, label=f"R2={r2}")
        rsi_ax.set_ylabel("RSI")
        rsi_ax.set_xlabel("Time")
        rsi_ax.set_ylim(0, 100)
        rsi_ax.grid(alpha=0.2)

        for index, trade in enumerate(result.trades):
            entry_row = self._locate_trade_row(chart_df, trade.entry_time)
            exit_row = self._locate_trade_row(chart_df, trade.exit_time)
            entry_time = pd.Timestamp(trade.entry_time)
            exit_time = pd.Timestamp(trade.exit_time)

            price_ax.scatter(entry_time, trade.entry_price, color="#16a34a", marker="^", s=120, zorder=5)
            rsi_ax.scatter(entry_time, entry_row["rsi"], color="#16a34a", marker="^", s=80, zorder=5)
            entry_note = (
                f"BUY #{index + 1}\n"
                f"RSI={entry_row['rsi']:.2f}\n"
                f"Price={trade.entry_price:,.2f}\n"
                f"Qty={trade.quantity:.4f}"
            )
            price_ax.annotate(
                entry_note,
                xy=(entry_time, trade.entry_price),
                xytext=(10, 18 if index % 2 == 0 else 35),
                textcoords="offset points",
                fontsize=8,
                color="#166534",
                bbox={"boxstyle": "round,pad=0.3", "fc": "#dcfce7", "ec": "#16a34a", "alpha": 0.9},
                arrowprops={"arrowstyle": "->", "color": "#16a34a", "lw": 0.8},
            )

            price_ax.scatter(exit_time, trade.exit_price, color="#dc2626", marker="v", s=120, zorder=5)
            rsi_ax.scatter(exit_time, exit_row["rsi"], color="#dc2626", marker="v", s=80, zorder=5)
            exit_note = (
                f"SELL #{index + 1}\n"
                f"RSI={exit_row['rsi']:.2f}\n"
                f"Price={trade.exit_price:,.2f}\n"
                f"PnL={trade.pnl_percent:.2%}\n"
                f"{trade.exit_reason}"
            )
            price_ax.annotate(
                exit_note,
                xy=(exit_time, trade.exit_price),
                xytext=(10, -55 if index % 2 == 0 else -72),
                textcoords="offset points",
                fontsize=8,
                color="#991b1b",
                bbox={"boxstyle": "round,pad=0.3", "fc": "#fee2e2", "ec": "#dc2626", "alpha": 0.9},
                arrowprops={"arrowstyle": "->", "color": "#dc2626", "lw": 0.8},
            )

        price_ax.legend(loc="upper left")
        rsi_ax.legend(loc="upper left")
        fig.tight_layout()
        fig.savefig(output_path, dpi=180, bbox_inches="tight")
        plt.close(fig)

    @staticmethod
    def _locate_trade_row(df: pd.DataFrame, trade_time) -> pd.Series:
        """定位交易点对应的K线行"""
        trade_ts = pd.Timestamp(trade_time)
        matched = df[df["close_time"] == trade_ts]
        if not matched.empty:
            return matched.iloc[0]

        nearest_index = (df["close_time"] - trade_ts).abs().idxmin()
        return df.loc[nearest_index]

    @staticmethod
    def _parse_thresholds(strategy_name: str) -> tuple[int, int]:
        """从策略名解析阈值"""
        parts = strategy_name.split("_")
        return int(parts[2]), int(parts[4])

    @staticmethod
    def _trades_to_dataframe(trades: List) -> pd.DataFrame:
        """交易记录转换为 DataFrame"""
        rows = [trade.to_dict() for trade in trades]
        columns = [
            "entry_time",
            "entry_price",
            "exit_time",
            "exit_price",
            "quantity",
            "direction",
            "pnl",
            "pnl_percent",
            "status",
            "exit_reason",
            "holding_days",
        ]
        return pd.DataFrame(rows, columns=columns)

    @staticmethod
    def _format_summary_table(df: pd.DataFrame) -> str:
        """格式化摘要表格"""
        display_df = df.loc[
            :,
            [
                "r1",
                "r2",
                "total_return",
                "annual_return",
                "max_drawdown",
                "win_rate",
                "profit_factor",
                "total_trades",
            ],
        ].copy()

        for column in ["total_return", "annual_return", "max_drawdown", "win_rate"]:
            display_df[column] = display_df[column].map(lambda value: f"{value:.2%}")
        display_df["profit_factor"] = display_df["profit_factor"].map(lambda value: f"{value:.2f}")

        return display_df.to_string(index=False)


def main():
    """主函数"""
    runner = BacktestRunner()
    symbol = sys.argv[1] if len(sys.argv) > 1 else TRADING_CONFIG.get("symbols", ["EOSUSDT"])[0]
    results = runner.run_rsi_grid_backtest(symbol=symbol, timeframe="1d")

    logger.info("\n%s", results["report"])
    logger.info("输出文件: %s", results["output_paths"])


if __name__ == "__main__":
    main()
