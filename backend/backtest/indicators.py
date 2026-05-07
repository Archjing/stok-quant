"""
技术指标计算库 - 兼容 TA-Lib 接口
(numpy 实现，避免 TA-Lib C 扩展依赖)
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional


def sma(data: np.ndarray, window: int) -> np.ndarray:
    """简单移动平均"""
    return pd.Series(data).rolling(window).mean().values


def ema(data: np.ndarray, window: int) -> np.ndarray:
    """指数移动平均"""
    return pd.Series(data).ewm(span=window, adjust=False).mean().values


def macd(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD 指标"""
    ema12 = ema(data, 12)
    ema26 = ema(data, 26)
    macd_line = ema12 - ema26
    signal = ema(macd_line, 9)
    hist = macd_line - signal
    return macd_line, signal, hist


def rsi(data: np.ndarray, window: int = 14) -> np.ndarray:
    """RSI 指标"""
    series = pd.Series(data)
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).values


def bollinger(data: np.ndarray, window: int = 20,
              num_std: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """布林带"""
    series = pd.Series(data)
    mid = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (mid + num_std * std).values, mid.values, (mid - num_std * std).values


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
        window: int = 14) -> np.ndarray:
    """ATR 平均真实波幅"""
    hl = pd.Series(high) - pd.Series(low)
    hc = np.abs(pd.Series(high) - pd.Series(close).shift())
    lc = np.abs(pd.Series(low) - pd.Series(close).shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(window).mean().values


def kdj(data: np.ndarray, high: np.ndarray, low: np.ndarray,
        window: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """KDJ 随机指标"""
    hh = pd.Series(high).rolling(window).max()
    ll = pd.Series(low).rolling(window).min()
    rsv = (pd.Series(data) - ll) / (hh - ll) * 100
    
    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    j = 3 * k - 2 * d
    return k.values, d.values, j.values


def obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """OBV 能量潮"""
    obv_vals = np.zeros_like(close)
    for i in range(1, len(close)):
        if close[i] > close[i-1]:
            obv_vals[i] = obv_vals[i-1] + volume[i]
        elif close[i] < close[i-1]:
            obv_vals[i] = obv_vals[i-1] - volume[i]
        else:
            obv_vals[i] = obv_vals[i-1]
    return obv_vals


def williams_r(high: np.ndarray, low: np.ndarray, close: np.ndarray,
               window: int = 14) -> np.ndarray:
    """威廉指标 %R"""
    hh = pd.Series(high).rolling(window).max()
    ll = pd.Series(low).rolling(window).min()
    return ((hh - pd.Series(close)) / (hh - ll) * -100).values


def linear_regression_slope(data: np.ndarray, window: int = 20) -> np.ndarray:
    """线性回归斜率（趋势强度）"""
    result = np.full_like(data, np.nan, dtype=float)
    for i in range(window, len(data)):
        x = np.arange(window)
        y = data[i-window:i]
        if np.all(np.isfinite(y)):
            result[i] = np.polyfit(x, y, 1)[0]
    return result
