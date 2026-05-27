#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC 市场状态打分脚本。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List

import pandas as pd

from indicators import IndicatorCalculator
from market_regime_backtest import MarketRegimeStrategyConfig, MarketRegimeSwitchBacktester


DEFAULT_HISTORY_START = "2017-08-17"


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    points: float
    max_points: float
    value: str
    rule: str


@dataclass(frozen=True)
class MarketScoreResult:
    symbol: str
    as_of: str
    profile: str
    score: float
    score_state: str
    bull_threshold: float
    bear_threshold: float
    regime_state: str
    daily_close: float
    daily_ma20: float
    daily_ma50: float
    daily_ma200: float
    monthly_close: float
    monthly_rsi: float
    monthly_rsi_prev: float
    monthly_ma5: float
    monthly_ma10: float
    components: List[ScoreComponent]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["components"] = [asdict(component) for component in self.components]
        return payload


class MarketStateScorer:
    """基于高周期结构为市场打分。"""

    def __init__(self, profile_name: str = "daily", symbol: str = "BTCUSDT"):
        self.config = MarketRegimeStrategyConfig.for_profile(profile_name)
        self.config = MarketRegimeStrategyConfig(**{**self.config.__dict__, "symbol": symbol})
        self.backtester = MarketRegimeSwitchBacktester(self.config)

    def score(
        self,
        as_of: str | pd.Timestamp | None = None,
        bull_threshold: float = 80.0,
        bear_threshold: float = 40.0,
    ) -> MarketScoreResult:
        end_ts = pd.Timestamp(as_of or datetime.utcnow().strftime("%Y-%m-%d"))
        start_ts = pd.Timestamp(DEFAULT_HISTORY_START)
        source_df = self.backtester.fetch_spot_klines(
            symbol=self.config.symbol,
            interval="1d",
            start_time=start_ts,
            end_time=end_ts,
        )
        if source_df.empty:
            raise ValueError("没有可用的市场数据")

        prepared = self.backtester.prepare_indicators(source_df)
        regime_state, _ = self.backtester._classify_market_state(prepared)

        price_series = (
            prepared.loc[:, ["open_time", "close"]]
            .drop_duplicates(subset=["open_time"])
            .sort_values("open_time")
            .set_index("open_time")["close"]
        )
        daily_closes = price_series.resample("1D").last().dropna()
        month_closes = daily_closes.resample("MS").last().dropna()

        monthly_rsi = IndicatorCalculator.calculate_rsi(month_closes, self.config.rsi_period)
        monthly_ma5 = month_closes.rolling(5).mean()
        monthly_ma10 = month_closes.rolling(10).mean()
        daily_ma20 = daily_closes.rolling(self.config.trend_ma_period).mean()
        daily_ma50 = daily_closes.rolling(self.config.regime_daily_mid_period).mean()
        daily_ma200 = daily_closes.rolling(self.config.regime_daily_long_period).mean()

        latest = {
            "daily_close": float(daily_closes.iloc[-1]),
            "daily_ma20": float(daily_ma20.iloc[-1]),
            "daily_ma50": float(daily_ma50.iloc[-1]),
            "daily_ma200": float(daily_ma200.iloc[-1]),
            "monthly_close": float(month_closes.iloc[-1]),
            "monthly_rsi": float(monthly_rsi.iloc[-1]),
            "monthly_rsi_prev": float(monthly_rsi.iloc[-2]),
            "monthly_ma5": float(monthly_ma5.iloc[-1]),
            "monthly_ma10": float(monthly_ma10.iloc[-1]),
        }

        components: List[ScoreComponent] = []
        score = 0.0

        rsi = latest["monthly_rsi"]
        if rsi <= 30:
            rsi_points = max(rsi / 30.0 * 8.0, 0.0)
        elif rsi <= 40:
            rsi_points = 8.0 + (rsi - 30.0) / 10.0 * 12.0
        elif rsi <= 50:
            rsi_points = 20.0 + (rsi - 40.0) / 10.0 * 15.0
        else:
            rsi_points = 35.0
        components.append(
            ScoreComponent(
                name="月线 RSI 区间",
                points=round(rsi_points, 2),
                max_points=35.0,
                value=f"{rsi:.2f}",
                rule="RSI 越高越接近牛市区，50 以上给满分",
            )
        )
        score += rsi_points

        score += self._append_binary_component(
            components,
            name="月线 RSI 回升",
            condition=latest["monthly_rsi"] > latest["monthly_rsi_prev"],
            max_points=10.0,
            value=f"{latest['monthly_rsi_prev']:.2f} -> {latest['monthly_rsi']:.2f}",
            rule="本月 RSI 高于上月",
        )
        score += self._append_binary_component(
            components,
            name="月线站上 MA10",
            condition=latest["monthly_close"] > latest["monthly_ma10"],
            max_points=15.0,
            value=f"{latest['monthly_close']:.2f} / {latest['monthly_ma10']:.2f}",
            rule="月线收盘高于 10 月均线",
        )
        score += self._append_binary_component(
            components,
            name="月线 MA5 上穿 MA10",
            condition=latest["monthly_ma5"] > latest["monthly_ma10"],
            max_points=15.0,
            value=f"{latest['monthly_ma5']:.2f} / {latest['monthly_ma10']:.2f}",
            rule="5 月均线高于 10 月均线",
        )
        score += self._append_binary_component(
            components,
            name="日线站上 MA20",
            condition=latest["daily_close"] > latest["daily_ma20"],
            max_points=10.0,
            value=f"{latest['daily_close']:.2f} / {latest['daily_ma20']:.2f}",
            rule="日线收盘高于 MA20",
        )
        score += self._append_binary_component(
            components,
            name="日线站上 MA50",
            condition=latest["daily_close"] > latest["daily_ma50"],
            max_points=5.0,
            value=f"{latest['daily_close']:.2f} / {latest['daily_ma50']:.2f}",
            rule="日线收盘高于 MA50",
        )
        score += self._append_binary_component(
            components,
            name="日线站上 MA200",
            condition=latest["daily_close"] > latest["daily_ma200"],
            max_points=10.0,
            value=f"{latest['daily_close']:.2f} / {latest['daily_ma200']:.2f}",
            rule="日线收盘高于 MA200",
        )

        rounded_score = round(score, 2)
        if rounded_score >= bull_threshold:
            score_state = "bull"
        elif rounded_score <= bear_threshold:
            score_state = "bear"
        else:
            score_state = "neutral"

        return MarketScoreResult(
            symbol=self.config.symbol,
            as_of=end_ts.strftime("%Y-%m-%d"),
            profile=self.config.profile_name,
            score=rounded_score,
            score_state=score_state,
            bull_threshold=bull_threshold,
            bear_threshold=bear_threshold,
            regime_state=regime_state,
            daily_close=round(latest["daily_close"], 2),
            daily_ma20=round(latest["daily_ma20"], 2),
            daily_ma50=round(latest["daily_ma50"], 2),
            daily_ma200=round(latest["daily_ma200"], 2),
            monthly_close=round(latest["monthly_close"], 2),
            monthly_rsi=round(latest["monthly_rsi"], 2),
            monthly_rsi_prev=round(latest["monthly_rsi_prev"], 2),
            monthly_ma5=round(latest["monthly_ma5"], 2),
            monthly_ma10=round(latest["monthly_ma10"], 2),
            components=components,
        )

    @staticmethod
    def _append_binary_component(
        components: List[ScoreComponent],
        name: str,
        condition: bool,
        max_points: float,
        value: str,
        rule: str,
    ) -> float:
        points = max_points if condition else 0.0
        components.append(
            ScoreComponent(
                name=name,
                points=points,
                max_points=max_points,
                value=value,
                rule=rule,
            )
        )
        return points


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="查询 BTC 当前牛熊市场分数")
    parser.add_argument("--symbol", default="BTCUSDT", help="交易对，默认 BTCUSDT")
    parser.add_argument("--date", default=None, help="查询日期，格式 YYYY-MM-DD，默认今天")
    parser.add_argument("--profile", default="daily", help="使用的配置档位，默认 daily")
    parser.add_argument("--bull-threshold", type=float, default=80.0, help="牛市阈值，默认 80")
    parser.add_argument("--bear-threshold", type=float, default=40.0, help="熊市阈值，默认 40")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def format_text(result: MarketScoreResult) -> str:
    lines = [
        f"as_of={result.as_of}",
        f"symbol={result.symbol}",
        f"profile={result.profile}",
        f"score={result.score:.2f}/100",
        f"score_state={result.score_state}",
        f"regime_state={result.regime_state}",
        (
            "monthly: "
            f"rsi={result.monthly_rsi:.2f} prev={result.monthly_rsi_prev:.2f} "
            f"close={result.monthly_close:.2f} ma5={result.monthly_ma5:.2f} ma10={result.monthly_ma10:.2f}"
        ),
        (
            "daily: "
            f"close={result.daily_close:.2f} ma20={result.daily_ma20:.2f} "
            f"ma50={result.daily_ma50:.2f} ma200={result.daily_ma200:.2f}"
        ),
        "components:",
    ]
    for component in result.components:
        lines.append(
            f"- {component.name}: {component.points:.2f}/{component.max_points:.2f} "
            f"(value={component.value}; rule={component.rule})"
        )
    return "\n".join(lines)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    scorer = MarketStateScorer(profile_name=args.profile, symbol=args.symbol)
    result = scorer.score(
        as_of=args.date,
        bull_threshold=args.bull_threshold,
        bear_threshold=args.bear_threshold,
    )

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_text(result))


if __name__ == "__main__":
    main()
