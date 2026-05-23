# -*- coding: utf-8 -*-
"""指标系统 - 技术指标计算"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple
from config import INDICATOR_CONFIG

logger = logging.getLogger(__name__)

class IndicatorCalculator:
    """技术指标计算器"""

    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """简单移动平均线 SMA"""
        return data.rolling(window=period).mean()

    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """指数移动平均线 EMA"""
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """相对强弱指标 RSI

        RSI = 100 - (100 / (1 + RS))
        RS = 平均上升幅 / 平均下降幅
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD指标

        Returns:
            macd_line, signal_line, histogram
        """
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """布林带

        Returns:
            upper_band, middle_band, lower_band
        """
        middle_band = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        return upper_band, middle_band, lower_band

    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均真实波幅 ATR"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """能量潮 OBV"""
        obv = np.where(close > close.shift(1), volume,
                      np.where(close < close.shift(1), -volume, 0))
        obv = pd.Series(obv, index=close.index).cumsum()
        return obv

    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                           period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> Tuple[pd.Series, pd.Series]:
        """随机指标 KDJ

        Returns:
            k_line, d_line
        """
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()

        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
        k_line = k_line.rolling(window=smooth_k).mean()
        d_line = k_line.rolling(window=smooth_d).mean()

        return k_line, d_line

    @staticmethod
    def calculate_volume_change(volume: pd.Series, period: int = 5) -> pd.Series:
        """成交量变化百分比"""
        avg_volume = volume.rolling(window=period).mean()
        volume_change = ((volume - avg_volume) / avg_volume) * 100
        return volume_change


class IndicatorAnalyzer:
    """指标分析器 - 分析指标信号"""

    def __init__(self):
        self.calculator = IndicatorCalculator()
        self.config = INDICATOR_CONFIG

    def analyze_all(self, df: pd.DataFrame) -> Dict:
        """分析所有指标

        Args:
            df: 包含 open, high, low, close, volume 的DataFrame

        Returns:
            包含所有指标值的字典
        """
        indicators = {}

        try:
            # 移动平均线
            indicators['ma20'] = self.calculator.calculate_sma(df['close'], 20).iloc[-1]
            indicators['ma50'] = self.calculator.calculate_sma(df['close'], 50).iloc[-1]
            indicators['ma200'] = self.calculator.calculate_sma(df['close'], 200).iloc[-1]

            # RSI
            rsi = self.calculator.calculate_rsi(df['close'], self.config['rsi_period'])
            indicators['rsi'] = rsi.iloc[-1]
            indicators['rsi_oversold'] = indicators['rsi'] < self.config['rsi_oversold']
            indicators['rsi_overbought'] = indicators['rsi'] > self.config['rsi_overbought']

            # MACD
            macd, signal, histogram = self.calculator.calculate_macd(
                df['close'],
                self.config['macd_fast'],
                self.config['macd_slow'],
                self.config['macd_signal']
            )
            indicators['macd'] = macd.iloc[-1]
            indicators['macd_signal'] = signal.iloc[-1]
            indicators['macd_histogram'] = histogram.iloc[-1]
            indicators['macd_cross'] = self._detect_macd_cross(macd, signal)

            # 布林带
            upper, middle, lower = self.calculator.calculate_bollinger_bands(
                df['close'],
                self.config['bb_period'],
                self.config['bb_std']
            )
            indicators['bb_upper'] = upper.iloc[-1]
            indicators['bb_middle'] = middle.iloc[-1]
            indicators['bb_lower'] = lower.iloc[-1]
            current_price = df['close'].iloc[-1]
            indicators['bb_breakout'] = (current_price < lower.iloc[-1]) or (current_price > upper.iloc[-1])

            # ATR
            atr = self.calculator.calculate_atr(df['high'], df['low'], df['close'])
            indicators['atr'] = atr.iloc[-1]
            indicators['atr_percent'] = (atr.iloc[-1] / current_price) * 100

            # OBV
            obv = self.calculator.calculate_obv(df['close'], df['volume'])
            indicators['obv'] = obv.iloc[-1]

            # KDJ
            k, d = self.calculator.calculate_stochastic(df['high'], df['low'], df['close'])
            indicators['k_line'] = k.iloc[-1]
            indicators['d_line'] = d.iloc[-1]
            indicators['kd_oversold'] = indicators['k_line'] < 20

            # 成交量
            volume_change = self.calculator.calculate_volume_change(df['volume'])
            indicators['volume_change'] = volume_change.iloc[-1]
            indicators['volume_increase'] = indicators['volume_change'] > 50  # 成交量放大超过50%

            # 当前价格
            indicators['current_price'] = current_price
            indicators['current_volume'] = df['volume'].iloc[-1]

        except Exception as e:
            logger.error(f"Error analyzing indicators: {str(e)}")

        return indicators

    @staticmethod
    def _detect_macd_cross(macd: pd.Series, signal: pd.Series) -> str:
        """检测MACD金叉/死叉"""
        if len(macd) < 2 or len(signal) < 2:
            return 'none'

        prev_diff = macd.iloc[-2] - signal.iloc[-2]
        curr_diff = macd.iloc[-1] - signal.iloc[-1]

        if prev_diff < 0 and curr_diff > 0:
            return 'golden_cross'
        elif prev_diff > 0 and curr_diff < 0:
            return 'death_cross'
        else:
            return 'none'

    def get_trend(self, df: pd.DataFrame) -> str:
        """判断大趋势

        Returns:
            'uptrend', 'downtrend', 或 'consolidation'
        """
        try:
            ma200 = self.calculator.calculate_sma(df['close'], 200)
            ma50 = self.calculator.calculate_sma(df['close'], 50)

            current_price = df['close'].iloc[-1]
            ma50_val = ma50.iloc[-1]
            ma200_val = ma200.iloc[-1]

            if current_price > ma50_val > ma200_val:
                return 'uptrend'
            elif current_price < ma50_val < ma200_val:
                return 'downtrend'
            else:
                return 'consolidation'
        except:
            return 'consolidation'

