# -*- coding: utf-8 -*-
"""策略引擎 - 多指标组合和权重评分"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
from indicators import IndicatorAnalyzer
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class Signal:
    """交易信号"""
    symbol: str
    signal_type: str  # 'BUY' 或 'SELL'
    price: float
    confidence: float  # 信心度 0-1
    reasons: List[str]  # 信号原因
    indicators: Dict  # 指标值


class StrategyEngine:
    """策略引擎 - 实现多指标组合策略"""

    def __init__(self):
        self.analyzer = IndicatorAnalyzer()

    def enhanced_rsi_grid_strategy(self, symbol: str, df: pd.DataFrame) -> Signal:
        """
        增强型RSI网格策略

        基于需求文档中的示例策略实现
        """
        indicators = self.analyzer.analyze_all(df)
        trend = self.analyzer.get_trend(df)

        reasons = []
        scores = []
        signal_type = None

        # 1. 大趋势判断
        trend_info = self._analyze_trend(df, trend)
        reasons.extend(trend_info['reasons'])

        # 2. 入场信号矩阵
        if trend in ['uptrend', 'consolidation']:
            # 下降趋势或震荡时：谨慎做多
            buy_signal, buy_score = self._check_buy_conditions(indicators, trend)

            if buy_signal:
                signal_type = 'BUY'
                scores.append(buy_score)
                reasons.append(f"买入信号确认 (趋势: {trend})")

        elif trend == 'downtrend':
            # 下降趋势时：寻找反弹
            sell_signal, sell_score = self._check_sell_conditions(indicators, trend)

            if sell_signal:
                signal_type = 'SELL'
                scores.append(sell_score)
                reasons.append(f"卖出信号确认 (趋势: {trend})")

        # 计算置信度
        confidence = sum(scores) / len(scores) if scores else 0.0

        if signal_type and confidence >= 0.7:
            return Signal(
                symbol=symbol,
                signal_type=signal_type,
                price=indicators['current_price'],
                confidence=confidence,
                reasons=reasons,
                indicators=indicators
            )

        return None

    def _analyze_trend(self, df: pd.DataFrame, trend: str) -> Dict:
        """分析大趋势"""
        reasons = []

        if trend == 'uptrend':
            reasons.append("大趋势: 上升趋势 - 倾向做多")
        elif trend == 'downtrend':
            reasons.append("大趋势: 下降趋势 - 谨慎做多")
        else:
            reasons.append("大趋势: 震荡趋势 - 高抛低吸")

        return {'reasons': reasons, 'trend': trend}

    def _check_buy_conditions(self, indicators: Dict, trend: str) -> Tuple[bool, float]:
        """检查买入条件"""
        score = 0.0
        reasons = []

        # 条件A: RSI < 25 (权重: 0.4)
        if indicators.get('rsi', 50) < 25:
            score += 0.4
            reasons.append(f"RSI超卖 ({indicators['rsi']:.2f})")

        # 条件B: 成交量放大 > 150% (权重: 0.3)
        if indicators.get('volume_increase', False):
            score += 0.3
            reasons.append(f"成交量放大 ({indicators['volume_change']:.2f}%)")

        # 条件C: 价格偏离布林下轨 (权重: 0.3)
        if indicators.get('bb_breakout', False):
            current = indicators.get('current_price', 0)
            bb_lower = indicators.get('bb_lower', 0)
            if current < bb_lower:
                score += 0.3
                reasons.append(f"价格突破布林下轨")

        # 额外条件: MACD金叉
        if indicators.get('macd_cross') == 'golden_cross':
            score += 0.1
            reasons.append("MACD金叉")

        # 额外条件: KD超卖
        if indicators.get('kd_oversold', False):
            score += 0.1
            reasons.append(f"KD超卖 (K: {indicators['k_line']:.2f})")

        return score >= 0.7, min(score, 1.0)

    def _check_sell_conditions(self, indicators: Dict, trend: str) -> Tuple[bool, float]:
        """检查卖出条件"""
        score = 0.0
        reasons = []

        # RSI超买 (权重: 0.3)
        if indicators.get('rsi', 50) > 70:
            score += 0.3
            reasons.append(f"RSI超买 ({indicators['rsi']:.2f})")

        # MACD死叉 (权重: 0.4)
        if indicators.get('macd_cross') == 'death_cross':
            score += 0.4
            reasons.append("MACD死叉")

        # 价格突破布林上轨 (权重: 0.3)
        if indicators.get('bb_breakout', False):
            current = indicators.get('current_price', 0)
            bb_upper = indicators.get('bb_upper', 0)
            if current > bb_upper:
                score += 0.3
                reasons.append("价格突破布林上轨")

        return score >= 0.7, min(score, 1.0)

    def simple_ma_cross_strategy(self, symbol: str, df: pd.DataFrame) -> Signal:
        """简单的移动平均线交叉策略"""
        indicators = self.analyzer.analyze_all(df)

        ma20 = indicators.get('ma20', 0)
        ma50 = indicators.get('ma50', 0)
        ma200 = indicators.get('ma200', 0)
        current_price = indicators.get('current_price', 0)
        rsi = indicators.get('rsi', 50)

        reasons = []

        # 买入条件: 快线上穿慢线，且大趋势向上
        if ma20 > ma50 > ma200 and current_price > ma50:
            if rsi < 70:  # 防止过度买入
                return Signal(
                    symbol=symbol,
                    signal_type='BUY',
                    price=current_price,
                    confidence=0.8,
                    reasons=['MA20 > MA50 > MA200', f'RSI: {rsi:.2f} (未超买)'],
                    indicators=indicators
                )

        # 卖出条件: 快线下穿慢线，且大趋势向下
        if ma20 < ma50 < ma200 and current_price < ma50:
            if rsi > 30:  # 防止过度卖出
                return Signal(
                    symbol=symbol,
                    signal_type='SELL',
                    price=current_price,
                    confidence=0.8,
                    reasons=['MA20 < MA50 < MA200', f'RSI: {rsi:.2f} (未超卖)'],
                    indicators=indicators
                )

        return None

    def multi_indicator_strategy(self, symbol: str, df: pd.DataFrame) -> Signal:
        """多指标综合策略"""
        indicators = self.analyzer.analyze_all(df)
        trend = self.analyzer.get_trend(df)

        buy_score = 0.0
        sell_score = 0.0
        buy_reasons = []
        sell_reasons = []

        # RSI信号 (权重: 0.25)
        if indicators['rsi_oversold']:
            buy_score += 0.25
            buy_reasons.append(f"RSI超卖: {indicators['rsi']:.2f}")
        if indicators['rsi_overbought']:
            sell_score += 0.25
            sell_reasons.append(f"RSI超买: {indicators['rsi']:.2f}")

        # MACD信号 (权重: 0.25)
        if indicators['macd_cross'] == 'golden_cross':
            buy_score += 0.25
            buy_reasons.append("MACD金叉")
        elif indicators['macd_cross'] == 'death_cross':
            sell_score += 0.25
            sell_reasons.append("MACD死叉")

        # 布林带信号 (权重: 0.2)
        current = indicators['current_price']
        if current < indicators['bb_lower']:
            buy_score += 0.2
            buy_reasons.append("价格低于布林下轨")
        elif current > indicators['bb_upper']:
            sell_score += 0.2
            sell_reasons.append("价格高于布林上轨")

        # KDJ信号 (权重: 0.15)
        if indicators['kd_oversold']:
            buy_score += 0.15
            buy_reasons.append(f"KDJ超卖: {indicators['k_line']:.2f}")

        # 成交量信号 (权重: 0.15)
        if indicators['volume_increase']:
            if trend == 'uptrend':
                buy_score += 0.15
                buy_reasons.append(f"成交量放大+上升趋势")
            else:
                sell_score += 0.15
                sell_reasons.append(f"成交量放大+下降趋势")

        # 生成信号
        if buy_score >= 0.7 and buy_score > sell_score:
            return Signal(
                symbol=symbol,
                signal_type='BUY',
                price=indicators['current_price'],
                confidence=buy_score,
                reasons=buy_reasons,
                indicators=indicators
            )

        if sell_score >= 0.7 and sell_score > buy_score:
            return Signal(
                symbol=symbol,
                signal_type='SELL',
                price=indicators['current_price'],
                confidence=sell_score,
                reasons=sell_reasons,
                indicators=indicators
            )

        return None

