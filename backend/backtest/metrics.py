"""
回测绩效指标计算
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List


def calculate_metrics(
    equity: np.ndarray,
    returns: np.ndarray,
    initial_cash: float,
    total_bars: int,
    risk_free_rate: float = 0.02,
) -> Dict[str, Any]:
    """计算回测绩效指标"""
    if len(equity) < 2:
        return {"total_return_pct": 0.0, "total_trades": 0}

    end_cash = equity[-1]
    total_return_pct = (end_cash / initial_cash - 1) * 100

    # 年化
    trading_days = max(total_bars, 1)
    years = trading_days / 252
    annualized_return = ((1 + total_return_pct / 100) ** (1 / max(years, 0.01)) - 1) * 100

    # 波动率
    if len(returns) > 1:
        volatility = np.std(returns, ddof=1) * np.sqrt(252) * 100
    else:
        volatility = 0.0

    # 夏普比率
    excess_returns = returns - risk_free_rate / 252
    sharpe_ratio = 0.0
    if np.std(returns, ddof=1) > 0:
        sharpe_ratio = np.mean(excess_returns) / np.std(returns, ddof=1) * np.sqrt(252)

    # 索提诺比率
    downside = returns[returns < 0]
    sortino_ratio = 0.0
    if len(downside) > 1 and np.std(downside, ddof=1) > 0:
        sortino_ratio = np.mean(excess_returns) / np.std(downside, ddof=1) * np.sqrt(252)

    # 最大回撤
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak * 100
    max_drawdown_pct = np.min(drawdown)
    max_drawdown = np.max(peak - equity)

    # 卡玛比率
    calmar_ratio = 0.0
    if abs(max_drawdown_pct) > 0.01:
        calmar_ratio = annualized_return / abs(max_drawdown_pct)

    # 回撤持续天数
    drawdown_series = pd.Series(drawdown)
    is_drawdown = drawdown_series < 0
    max_drawdown_duration = 0
    current_duration = 0
    for val in is_drawdown:
        if val:
            current_duration += 1
            max_drawdown_duration = max(max_drawdown_duration, current_duration)
        else:
            current_duration = 0

    # 月度收益
    monthly_returns = {}
    if len(equity) >= 20:
        try:
            eq_series = pd.Series(equity)
            monthly_ret = eq_series.pct_change().dropna().resample('ME').apply(
                lambda x: (1 + x).prod() - 1
            )
            monthly_returns = {
                str(k.date()): float(v)
                for k, v in monthly_ret.items() if pd.notna(v)
            }
        except Exception:
            pass

    return {
        "total_return_pct": round(total_return_pct, 2),
        "annualized_return": round(annualized_return, 2),
        "volatility": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 4),
        "sortino_ratio": round(sortino_ratio, 4),
        "calmar_ratio": round(calmar_ratio, 4),
        "max_drawdown": round(float(max_drawdown), 2),
        "max_drawdown_pct": round(float(max_drawdown_pct), 2),
        "max_drawdown_duration": int(max_drawdown_duration),
        "end_cash": round(float(end_cash), 2),
        "initial_cash": float(initial_cash),
        "drawdown_curve": drawdown.tolist(),
        "monthly_returns": monthly_returns,
    }
