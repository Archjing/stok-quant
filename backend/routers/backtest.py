"""
回测 API
"""
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException

from backend.crawlers.us_stock_source import USStockSource
from backend.crawlers.data_cleaner import USDataCleaner
from backend.backtest.engine import BacktestEngine
from backend.backtest.strategies import (
    SMACrossoverStrategy,
    RSIMeanReversionStrategy,
    MACDStrategy,
    BuyAndHoldStrategy,
)

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])
logger = logging.getLogger(__name__)
data_source = USStockSource()

# 策略注册表
STRATEGIES = {
    "sma_crossover": SMACrossoverStrategy,
    "rsi_mean_reversion": RSIMeanReversionStrategy,
    "macd": MACDStrategy,
    "buy_and_hold": BuyAndHoldStrategy,
}


@router.get("/strategies")
def list_strategies():
    """获取可用策略列表"""
    return {
        "strategies": [
            {"id": "sma_crossover", "name": "双均线交叉", "params": {"fast": 20, "slow": 50}},
            {"id": "rsi_mean_reversion", "name": "RSI均值回归", "params": {"oversold": 30, "overbought": 70}},
            {"id": "macd", "name": "MACD趋势跟踪", "params": {}},
            {"id": "buy_and_hold", "name": "买入并持有", "params": {"quantity": 100}},
        ]
    }


@router.post("/run")
def run_backtest(
    symbol: str = Query("AAPL", description="股票代码"),
    strategy: str = Query("sma_crossover", description="策略ID"),
    years: int = Query(5, ge=1, le=20, description="回溯年数"),
    initial_cash: float = Query(100000.0, ge=1000),
):
    """运行回测"""
    symbol = symbol.upper()
    strategy_class = STRATEGIES.get(strategy)
    if not strategy_class:
        raise HTTPException(400, f"策略 '{strategy}' 不存在，可用: {list(STRATEGIES.keys())}")

    # 获取数据
    df = data_source.get_full_history(symbol, years=years)
    if df.empty:
        raise HTTPException(404, f"股票 {symbol} 无历史数据")

    df = USDataCleaner.clean_daily_data(df)

    # 运行回测
    engine = BacktestEngine(
        data=df,
        strategy_class=strategy_class,
        symbol=symbol,
        initial_cash=initial_cash,
    )
    result = engine.run()

    return {
        "status": result.status,
        "strategy": strategy,
        "symbol": symbol,
        "start_date": result.start_time,
        "end_date": result.end_time,
        "total_bars": result.total_bars,
        "results": {
            "total_return_pct": result.total_return_pct,
            "annualized_return": result.annualized_return,
            "volatility": result.volatility,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "calmar_ratio": result.calmar_ratio,
            "max_drawdown": result.max_drawdown,
            "max_drawdown_pct": result.max_drawdown_pct,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "total_trades": result.total_trades,
            "initial_cash": result.initial_cash,
            "end_cash": result.end_cash,
            "monthly_returns": result.monthly_returns,
        },
        "equity_curve": result.equity_curve,
        "drawdown_curve": result.drawdown_curve,
        "trades": [
            {"side": t.side, "quantity": t.quantity, "price": t.price,
             "pnl": t.pnl, "tag": t.tag}
            for t in result.trades
        ],
        "error_message": result.error_message,
    }


@router.post("/compare")
def compare_strategies(
    symbol: str = Query("AAPL"),
    years: int = Query(5, ge=1, le=20),
    initial_cash: float = Query(100000.0),
):
    """多策略对比"""
    results = {}
    for sid, sclass in STRATEGIES.items():
        df = data_source.get_full_history(symbol, years=years)
        if df.empty:
            continue
        df = USDataCleaner.clean_daily_data(df)
        engine = BacktestEngine(
            data=df, strategy_class=sclass,
            symbol=symbol, initial_cash=initial_cash,
        )
        result = engine.run()
        results[sid] = {
            "total_return_pct": result.total_return_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown_pct": result.max_drawdown_pct,
            "total_trades": result.total_trades,
            "equity_curve": result.equity_curve[:100],  # 采样
        }
    return {"symbol": symbol, "strategies": results}
