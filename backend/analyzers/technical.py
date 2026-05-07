"""
技术分析模块
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TechnicalSignal:
    """技术信号"""
    symbol: str
    trend: str          # bullish, bearish, neutral
    momentum: str       # overbought, oversold, neutral
    volatility: str     # high, normal, low
    strength: float     # 0-100
    signals: list       # 具体信号列表
    score: float        # 综合评分


class TechnicalAnalyzer:
    """技术分析器"""

    def analyze(self, df: pd.DataFrame, symbol: str) -> TechnicalSignal:
        """综合分析"""
        if df.empty or "close" not in df.columns:
            return TechnicalSignal(symbol, "neutral", "neutral", "neutral", 0, [], 50)

        close = df["close"].values
        signals = []
        score = 50  # 中性分

        # SMA 趋势判断
        sma20 = self._safe_get(df, "sma_20")
        sma50 = self._safe_get(df, "sma_50")
        sma200 = self._safe_get(df, "sma_200")

        if sma20 and sma50 and sma200:
            # 多头排列: 20 > 50 > 200
            if sma20[-1] > sma50[-1] > sma200[-1]:
                signals.append("多头排列")
                score += 15
            # 空头排列: 20 < 50 < 200
            elif sma20[-1] < sma50[-1] < sma200[-1]:
                signals.append("空头排列")
                score -= 15
            else:
                signals.append("均线交织")
                score += 0

        # MACD 信号
        macd = self._safe_get(df, "macd")
        macd_signal = self._safe_get(df, "macd_signal")
        macd_hist = self._safe_get(df, "macd_hist")

        if macd is not None and macd_signal is not None and len(macd) >= 2:
            if macd[-1] > macd_signal[-1]:
                signals.append("MACD金叉")
                score += 10
            else:
                signals.append("MACD死叉")
                score -= 10

        # RSI
        rsi = self._safe_get(df, "rsi_14")
        if rsi is not None:
            last_rsi = rsi[-1]
            if last_rsi > 70:
                signals.append(f"RSI超买({last_rsi:.1f})")
                score -= 10
            elif last_rsi < 30:
                signals.append(f"RSI超卖({last_rsi:.1f})")
                score += 10
            else:
                signals.append(f"RSI中性({last_rsi:.1f})")

        # 布林带位置
        close_last = close[-1]
        bb_upper = self._safe_get(df, "bb_upper")
        bb_lower = self._safe_get(df, "bb_lower")
        if bb_upper is not None and bb_lower is not None:
            if close_last > bb_upper[-1]:
                signals.append("突破布林上轨")
                score -= 8
            elif close_last < bb_lower[-1]:
                signals.append("跌破布林下轨")
                score += 8

        # 趋势判断
        trend = "bullish" if score > 55 else ("bearish" if score < 45 else "neutral")
        momentum = "overbought" if (rsi is not None and rsi[-1] > 70) else \
                   ("oversold" if (rsi is not None and rsi[-1] < 30) else "neutral")
        volatility = "high" if "跌破布林" in str(signals) or "突破布林" in str(signals) \
                     else "normal"

        return TechnicalSignal(
            symbol=symbol,
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            strength=min(max(score, 0), 100),
            signals=signals,
            score=score,
        )

    @staticmethod
    def _safe_get(df: pd.DataFrame, col: str) -> Optional[np.ndarray]:
        if col in df.columns and len(df) > 0:
            vals = df[col].values
            if np.any(np.isfinite(vals)):
                return vals
        return None
