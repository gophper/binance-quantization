# -*- coding: utf-8 -*-
"""数据层 - K线数据获取和管理"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
import json
import logging
from typing import List, Dict, Optional, Tuple
from config import BINANCE_FUTURES_URL, BINANCE_REST_URL, DATA_CONFIG

logger = logging.getLogger(__name__)

class DataManager:
    """数据管理器 - 获取和存储K线数据"""

    def __init__(self, testnet: bool = True):
        self.futures_url = BINANCE_FUTURES_URL
        self.rest_url = BINANCE_REST_URL
        self.testnet = testnet
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(DATA_CONFIG['db_path']), exist_ok=True)
        conn = sqlite3.connect(DATA_CONFIG['db_path'])
        cursor = conn.cursor()

        # 创建K线数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS klines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open_time INTEGER NOT NULL,
                close_time INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quote_asset_volume REAL,
                trades INTEGER,
                taker_buy_base REAL,
                taker_buy_quote REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe, open_time)
            )
        ''')

        # 创建交易信号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                signal_type TEXT NOT NULL,
                price REAL NOT NULL,
                confidence REAL NOT NULL,
                indicators JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            symbol: 交易对，如 'BTCUSDT'
            interval: 时间框架，如 '1h', '4h', '1d'
            limit: 获取数量

        Returns:
            DataFrame格式的K线数据
        """
        try:
            url = f"{self.futures_url}/fapi/v1/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])

            # 数据类型转换
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume', 'taker_buy_base', 'taker_buy_quote']:
                df[col] = pd.to_numeric(df[col])

            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

            # 保存到数据库
            self._save_klines(symbol, interval, df)

            return df.sort_values('open_time').reset_index(drop=True)

        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {str(e)}")
            # 尝试从数据库读取
            return self._load_klines_from_db(symbol, interval)

    def _save_klines(self, symbol: str, interval: str, df: pd.DataFrame):
        """保存K线数据到数据库"""
        try:
            conn = sqlite3.connect(DATA_CONFIG['db_path'])
            cursor = conn.cursor()

            for _, row in df.iterrows():
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO klines 
                        (symbol, timeframe, open_time, close_time, open, high, low, close, 
                         volume, quote_asset_volume, trades, taker_buy_base, taker_buy_quote)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol, interval,
                        int(row['open_time'].timestamp() * 1000),
                        int(row['close_time'].timestamp() * 1000),
                        float(row['open']), float(row['high']), float(row['low']), float(row['close']),
                        float(row['volume']), float(row['quote_asset_volume']),
                        int(row['trades']), float(row['taker_buy_base']), float(row['taker_buy_quote'])
                    ))
                except sqlite3.IntegrityError:
                    continue

            conn.commit()
            conn.close()
            logger.info(f"Saved {len(df)} klines for {symbol} {interval}")

        except Exception as e:
            logger.error(f"Error saving klines: {str(e)}")

    def _load_klines_from_db(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """从数据库加载K线数据"""
        try:
            conn = sqlite3.connect(DATA_CONFIG['db_path'])
            query = '''
                SELECT open_time, open, high, low, close, volume, close_time, 
                       quote_asset_volume, trades, taker_buy_base, taker_buy_quote
                FROM klines
                WHERE symbol = ? AND timeframe = ?
                ORDER BY open_time DESC
                LIMIT ?
            '''
            df = pd.read_sql_query(query, conn, params=(symbol, interval, limit))
            conn.close()

            if df.empty:
                logger.warning(f"No klines found in database for {symbol} {interval}")
                return pd.DataFrame()

            # 转换时间戳
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

            return df.sort_values('open_time').reset_index(drop=True)

        except Exception as e:
            logger.error(f"Error loading klines from database: {str(e)}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            url = f"{self.futures_url}/fapi/v1/premiumIndex"
            params = {'symbol': symbol}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return float(response.json()['markPrice'])
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {str(e)}")
            return 0.0

    def save_signal(self, symbol: str, signal_type: str, price: float,
                   confidence: float, indicators: Dict):
        """保存交易信号"""
        try:
            conn = sqlite3.connect(DATA_CONFIG['db_path'])
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO signals (symbol, timestamp, signal_type, price, confidence, indicators)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                int(datetime.now().timestamp() * 1000),
                signal_type,
                price,
                confidence,
                json.dumps(indicators)
            ))
            conn.commit()
            conn.close()
            logger.info(f"Saved signal: {symbol} {signal_type} @ {price} (confidence: {confidence})")
        except Exception as e:
            logger.error(f"Error saving signal: {str(e)}")


import os

