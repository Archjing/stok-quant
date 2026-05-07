                                                                                                                       """
数据清洗模块 - 美股数据清洗与标准化
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


class USDataCleaner:
    """美股数据清洗器"""

    @staticmethod
    def clean_daily_data(df: pd.DataFrame) -> pd.DataFrame:
        """清洗日线数据"""
        if df.empty:
            return df

        # 确保日期列
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        # 数值类型转换
        numeric_cols = ["open", "high", "low", "close", "volume", "adjusted_close"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 填充缺失的调整收盘价
        if "adjusted_close" not in df.columns and "close" in df.columns:
            df["adjusted_close"] = df["close"]

        return df.dropna(subset=["close"])

    @staticmethod
    def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """添加常用技术指标"""
        if df.empty or "close" not in df.columns:
            return df

        close = df["close"].values
        high = df["high"].values if "high" in df.columns else close
        low = df["low"].values if "low" in df.columns else close
        volume = df["volume"].values if "volume" in df.columns else np.ones_like(close)

        # SMA
        df["sma_20"] = USDataCleaner._sma(close, 20)
        df["sma_50"] = USDataCleaner._sma(close, 50)
        df["sma_200"] = USDataCleaner._sma(close, 200)

        # EMA
        df["ema_12"] = USDataCleaner._ema(close, 12)
        df["ema_26"] = USDataCleaner._ema(close, 26)

        # MACD
        macd, signal, hist = USDataCleaner._macd(close)
        df["macd"] = macd
        df["macd_signal"] = signal
        df["macd_hist"] = hist

        # RSI
        df["rsi_14"] = USDataCleaner._rsi(close, 14)

        # Bollinger Bands
        bb_upper, bb_mid, bb_lower = USDataCleaner._bollinger(close, 20)
        df["bb_upper"] = bb_upper
        df["bb_middle"] = bb_mid
        df["bb_lower"] = bb_lower

        # ATR
        df["atr_14"] = USDataCleaner._atr(high, low, close, 14)

        # 成交量均线
        df["volume_sma_20"] = USDataCleaner._sma(volume, 20)

        return df

    @staticmethod
    def _sma(data, window):
        series = pd.Series(data)
        return series.rolling(window).mean().values

    @staticmethod
    def _ema(data, window):
        series = pd.Series(data)
        return series.ewm(span=window, adjust=False).mean().values

    @staticmethod
    def _macd(data):
        ema12 = pd.Series(data).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(data).ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd.values, signal.values, hist.values

    @staticmethod
    def _rsi(data, window):
        series = pd.Series(data)
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0).rolling(window).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.values

    @staticmethod
    def _bollinger(data, window):
        series = pd.Series(data)
        sma = series.rolling(window).mean()
        std = series.rolling(window).std()
        return (sma + 2 * std).values, sma.values, (sma - 2 * std).values

    @staticmethod
    def _atr(high, low, close, window):
        hl = pd.Series(high) - pd.Series(low)
        hc = abs(pd.Series(high) - pd.Series(close).shift())
        lc = abs(pd.Series(low) - pd.Series(close).shift())
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.rolling(window).mean().values
