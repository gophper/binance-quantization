#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按固定频率监控 WLD 1h RSI(6)，触发阈值时发送企业微信通知。"""

from __future__ import annotations

import argparse
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from data_manager import DataManager
from indicators import IndicatorCalculator


logger = logging.getLogger(__name__)


DEFAULT_SYMBOL = "WLDUSDT"
DEFAULT_INTERVAL = "1h"
DEFAULT_RSI_PERIOD = 6
DEFAULT_HIGH_THRESHOLD = 90.0
DEFAULT_LOW_THRESHOLD = 40.0
DEFAULT_POLL_SECONDS = 60


@dataclass(frozen=True)
class RsiSnapshot:
    symbol: str
    interval: str
    price: float
    rsi: float
    candle_open_time: datetime
    candle_close_time: datetime
    observed_at: datetime


class WeComNotifier:
    """企业微信机器人通知器。"""

    def __init__(self, webhook_url: str):
        if not webhook_url:
            raise ValueError("企业微信 webhook 不能为空")
        self.webhook_url = webhook_url

    def send_text(self, content: str) -> None:
        response = requests.post(
            self.webhook_url,
            json={
                "msgtype": "text",
                "text": {"content": content},
            },
            timeout=10,
        )
        response.raise_for_status()

        payload = response.json()
        if payload.get("errcode") != 0:
            raise ValueError(f"企业微信通知失败: {payload}")


class WldRsiMonitor:
    """WLD RSI 阈值监控器。"""

    def __init__(
        self,
        symbol: str,
        interval: str,
        rsi_period: int,
        high_threshold: float,
        low_threshold: float,
        poll_seconds: int,
        webhook_url: str,
    ):
        if high_threshold <= low_threshold:
            raise ValueError("high_threshold 必须大于 low_threshold")
        if poll_seconds <= 0:
            raise ValueError("poll_seconds 必须大于 0")

        self.symbol = symbol
        self.interval = interval
        self.rsi_period = rsi_period
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.poll_seconds = poll_seconds
        self.data_manager = DataManager(testnet=False, market="spot")
        self.notifier = WeComNotifier(webhook_url)

    def fetch_snapshot(self) -> RsiSnapshot:
        limit = max(100, self.rsi_period * 20)
        df = self.data_manager.get_klines(self.symbol, self.interval, limit=limit)
        if df.empty:
            raise ValueError(f"没有获取到 {self.symbol} {self.interval} K线")

        closes = pd.Series(df["close"], dtype="float64")
        rsi_series = IndicatorCalculator.calculate_rsi(closes, self.rsi_period)
        latest_rsi = rsi_series.iloc[-1]
        if pd.isna(latest_rsi):
            raise ValueError(f"{self.symbol} {self.interval} RSI({self.rsi_period}) 计算结果为空")

        latest = df.iloc[-1]
        return RsiSnapshot(
            symbol=self.symbol,
            interval=self.interval,
            price=float(latest["close"]),
            rsi=float(latest_rsi),
            candle_open_time=latest["open_time"].to_pydatetime(),
            candle_close_time=latest["close_time"].to_pydatetime(),
            observed_at=datetime.now(),
        )

    def maybe_alert(self, snapshot: RsiSnapshot) -> Optional[str]:
        if snapshot.rsi > self.high_threshold:
            direction = "超买"
            threshold_text = f">{self.high_threshold:.2f}"
        elif snapshot.rsi < self.low_threshold:
            direction = "偏弱"
            threshold_text = f"<{self.low_threshold:.2f}"
        else:
            return None

        message = (
            f"WLD 1h RSI 预警\n"
            f"交易对: {snapshot.symbol}\n"
            f"周期: {snapshot.interval}\n"
            f"最新价格: {snapshot.price:.6f}\n"
            f"RSI({self.rsi_period}): {snapshot.rsi:.2f}\n"
            f"状态: {direction} ({threshold_text})\n"
            f"K线开始: {snapshot.candle_open_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"K线结束: {snapshot.candle_close_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"检查时间: {snapshot.observed_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.notifier.send_text(message)
        return direction

    def run_once(self) -> None:
        snapshot = self.fetch_snapshot()
        direction = self.maybe_alert(snapshot)
        if direction:
            logger.info(
                "已发送预警: symbol=%s interval=%s rsi=%.2f price=%.6f status=%s",
                snapshot.symbol,
                snapshot.interval,
                snapshot.rsi,
                snapshot.price,
                direction,
            )
            return

        logger.info(
            "无触发: symbol=%s interval=%s rsi=%.2f price=%.6f thresholds=(%.2f, %.2f)",
            snapshot.symbol,
            snapshot.interval,
            snapshot.rsi,
            snapshot.price,
            self.low_threshold,
            self.high_threshold,
        )

    def run_forever(self) -> None:
        logger.info(
            "启动监控: symbol=%s interval=%s rsi_period=%s high=%.2f low=%.2f poll=%ss",
            self.symbol,
            self.interval,
            self.rsi_period,
            self.high_threshold,
            self.low_threshold,
            self.poll_seconds,
        )
        while True:
            try:
                self.run_once()
            except (requests.RequestException, ValueError) as exc:
                logger.exception("监控执行失败: %s", exc)
            time.sleep(self.poll_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="每分钟监控 WLD 1h RSI(6) 并发送企业微信预警")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help=f"交易对，默认 {DEFAULT_SYMBOL}")
    parser.add_argument("--interval", default=DEFAULT_INTERVAL, help=f"K线周期，默认 {DEFAULT_INTERVAL}")
    parser.add_argument("--rsi-period", type=int, default=DEFAULT_RSI_PERIOD, help=f"RSI 周期，默认 {DEFAULT_RSI_PERIOD}")
    parser.add_argument(
        "--high-threshold",
        type=float,
        default=DEFAULT_HIGH_THRESHOLD,
        help=f"超买阈值，默认 {DEFAULT_HIGH_THRESHOLD}",
    )
    parser.add_argument(
        "--low-threshold",
        type=float,
        default=DEFAULT_LOW_THRESHOLD,
        help=f"偏弱阈值，默认 {DEFAULT_LOW_THRESHOLD}",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=DEFAULT_POLL_SECONDS,
        help=f"轮询秒数，默认 {DEFAULT_POLL_SECONDS}",
    )
    parser.add_argument(
        "--webhook-url",
        default=os.getenv("WECOM_WEBHOOK_URL", ""),
        help="企业微信机器人 webhook，默认读取环境变量 WECOM_WEBHOOK_URL",
    )
    parser.add_argument("--once", action="store_true", help="只检查一次，不进入循环")
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    args = build_parser().parse_args()
    monitor = WldRsiMonitor(
        symbol=args.symbol,
        interval=args.interval,
        rsi_period=args.rsi_period,
        high_threshold=args.high_threshold,
        low_threshold=args.low_threshold,
        poll_seconds=args.poll_seconds,
        webhook_url=args.webhook_url,
    )

    if args.once:
        monitor.run_once()
        return 0

    monitor.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
