"""
回测 API - 懒人版
优先从数据库读取，数据库没有时自动触发懒人下载
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException

from backend.crawlers.us_stock_source import USStockSource
from backend.crawlers.data_cleaner import USDataCleaner
from backend.data_manager import DataManager
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
data_mgr = DataManager()

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


def _get_backtest_data(symbol: str, years: int) -> tuple:
    """
    获取回测数据 - 懒人策略
    
    流程：
    1. 先检查数据库有没有
    2. 数据库有 → 直接返回
    3. 数据库没有 → 自动触发懒人下载 → 返回或报错
    
    Returns:
        (df: DataFrame, source: str, error: str or None)
    """
    symbol = symbol.upper()
    
    # 1. 优先从数据库读取
    db_rows = data_mgr.get_daily_from_db(symbol, years=years)
    if db_rows:
        logger.info(f"{symbol} ✓ 使用数据库缓存 ({len(db_rows)} 行)")
        df = USDataCleaner.clean_daily_data_from_db_rows(db_rows)
        return df, "database", None
    
    # 2. 数据库没有，自动触发懒人下载
    logger.info(f"{symbol} 数据库暂无此股票，触发懒人下载...")
    success, rows, err = data_mgr.lazy_download_one(symbol, years=years)
    
    if success:
        # 下载成功，再查一次数据库
        db_rows = data_mgr.get_daily_from_db(symbol, years=years)
        if db_rows:
            logger.info(f"{symbol} ✓ 懒人下载成功 ({rows} 行)")
            df = USDataCleaner.clean_daily_data_from_db_rows(db_rows)
            return df, "downloaded", None
    
    # 3. 下载失败
    if err and err.startswith("rate_limited_wait:"):
        remaining = err.split(":")[1]
        raise HTTPException(429, f"{symbol} 数据正在下载中，请 {remaining} 秒后再试")
    
    raise HTTPException(404, f"{symbol} 无历史数据: {err or '下载失败'}")


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

    # 获取数据（懒人策略）
    df, data_source_type, err = _get_backtest_data(symbol, years)
    
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
        "data_source": data_source_type,  # 告诉前端数据来源
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
    symbol = symbol.upper()
    
    # 获取数据（懒人策略）- 只需获取一次
    df, data_source_type, err = _get_backtest_data(symbol, years)
    
    results = {}
    for sid, sclass in STRATEGIES.items():
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
            "equity_curve": result.equity_curve[:100],
        }
    return {"symbol": symbol, "data_source": data_source_type, "strategies": results}


@router.get("/status/{symbol}")
def get_data_status(symbol: str):
    """获取股票数据状态"""
    symbol = symbol.upper()
    db_rows = data_mgr.get_daily_from_db(symbol, years=10)
    
    if db_rows:
        return {
            "symbol": symbol,
            "status": "available",
            "rows": len(db_rows),
            "start_date": str(db_rows[0].date) if db_rows else None,
            "end_date": str(db_rows[-1].date) if db_rows else None,
            "source": "database",
        }
    
    # 检查是否正在下载
    from backend.database import SessionLocal
    from backend.data_manager import DataSyncStatus
    session = SessionLocal()
    try:
        sync = session.query(DataSyncStatus).filter_by(symbol=symbol).first()
        if sync:
            if sync.status == "rate_limited":
                wait_time = (datetime.now() - sync.last_sync_time).total_seconds()
                return {
                    "symbol": symbol,
                    "status": "rate_limited",
                    "wait_seconds": int(300 - wait_time) if wait_time < 300 else 0,
                    "source": "yfinance",
                }
            elif sync.status == "syncing":
                return {
                    "symbol": symbol,
                    "status": "syncing",
                    "source": "yfinance",
                }
    finally:
        session.close()
    
    return {
        "symbol": symbol,
        "status": "missing",
        "rows": 0,
        "source": "none",
        "hint": "调用 /api/backtest/run 时会自动下载"
    }


@router.post("/warmup")
def warmup_data(
    symbols: str = Query(..., description="股票代码，逗号分隔"),
):
    """预热数据 - 后台下载指定股票"""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    results = {"submitted": [], "already_has": [], "rate_limited": []}
    
    for sym in symbol_list[:20]:  # 最多20只
        db_rows = data_mgr.get_daily_from_db(sym, years=5)
        if db_rows:
            results["already_has"].append(sym)
        else:
            from backend.database import SessionLocal
            from backend.data_manager import DataSyncStatus
            session = SessionLocal()
            try:
                sync = session.query(DataSyncStatus).filter_by(symbol=sym).first()
                if sync and sync.status == "rate_limited":
                    results["rate_limited"].append(sym)
                else:
                    results["submitted"].append(sym)
                    # 触发懒人下载（异步会更好，这里简化处理）
                    data_mgr.lazy_download_one(sym)
            finally:
                session.close()
    
    return {
        "message": f"预热请求已提交",
        "submitted": results["submitted"],
        "already_has": results["already_has"],
        "rate_limited": results["rate_limited"],
        "note": "数据将在后台下载，首次回测可能需要等待"
    }
