"""
回测 API - 多市场通用版
优先从通用表读取，数据库没有时自动触发按市场懒人下载。
"""

import logging
from fastapi import APIRouter, Query, HTTPException

from backend.market_data_manager import MarketDataManager

from backend.markets.symbols import get_currency, normalize_market, normalize_symbol
from backend.backtest.engine import BacktestEngine
from backend.backtest.market_config import get_market_backtest_config


from backend.backtest.strategies import (
    SMACrossoverStrategy,
    RSIMeanReversionStrategy,
    MACDStrategy,
    BuyAndHoldStrategy,
)

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])
logger = logging.getLogger(__name__)
market_mgr = MarketDataManager()



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


def _api_market(market: str) -> str:
    """标准化 API market 参数。"""
    try:
        return normalize_market(market)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def _get_backtest_data(symbol: str, years: int, market: str = "US") -> tuple:
    """
    获取回测数据 - 优先使用通用表。 

    Returns:
        (df: DataFrame, source: str, error: str or None, normalized_symbol: str)
    """
    market_code = _api_market(market)
    normalized = normalize_symbol(symbol, market_code) if market_code != "US" else symbol.upper()

    db_rows = market_mgr.get_daily_from_db(market_code, normalized, years=years)
    if db_rows:
        logger.info(f"{market_code}/{normalized} ✓ 使用数据库缓存 ({len(db_rows)} 行)")
        return market_mgr.rows_to_dataframe(db_rows), "database", None, normalized

    logger.info(f"{market_code}/{normalized} 数据库暂无此股票，触发懒人下载...")
    success, rows, err = market_mgr.lazy_download_one(market_code, normalized, years=years)
    if success:
        db_rows = market_mgr.get_daily_from_db(market_code, normalized, years=years)
        if db_rows:
            logger.info(f"{market_code}/{normalized} ✓ 懒人下载成功 ({rows} 行)")
            return market_mgr.rows_to_dataframe(db_rows), "downloaded", None, normalized

    if err and isinstance(err, str) and err.startswith("rate_limited_wait:"):
        remaining = err.split(":")[1]
        raise HTTPException(429, f"{normalized} 数据正在下载中，请 {remaining} 秒后再试")

    raise HTTPException(404, f"{market_code}/{normalized} 无历史数据: {err or '下载失败'}")



@router.get("/market-rules")
def get_market_rules(market: str = Query("US", description="市场: US|CN|HK")):
    """获取不同市场的回测规则配置。"""
    market_code = _api_market(market)
    config = get_market_backtest_config(market_code)
    return {
        "market": market_code,
        "currency": get_currency(market_code),
        "rules": config.to_dict(),
    }


@router.post("/run")
def run_backtest(
    symbol: str = Query("AAPL", description="股票代码"),
    strategy: str = Query("sma_crossover", description="策略ID"),
    years: int = Query(5, ge=1, le=20, description="回溯年数"),
    initial_cash: float = Query(100000.0, ge=1000),
    market: str = Query("US", description="市场: US|CN|HK"),
):
    """运行回测"""
    market_code = _api_market(market)
    normalized_symbol = normalize_symbol(symbol, market_code) if market_code != "US" else symbol.upper()
    strategy_class = STRATEGIES.get(strategy)
    if not strategy_class:
        raise HTTPException(400, f"策略 '{strategy}' 不存在，可用: {list(STRATEGIES.keys())}")

    df, data_source_type, _, normalized_symbol = _get_backtest_data(normalized_symbol, years, market_code)
    market_rules = get_market_backtest_config(market_code)

    engine = BacktestEngine(
        data=df,
        strategy_class=strategy_class,
        symbol=normalized_symbol,
        initial_cash=initial_cash,
        market=market_code,
        market_config=market_rules,
    )

    result = engine.run()

    return {
        "status": result.status,
        "strategy": strategy,
        "market": market_code,
        "currency": get_currency(market_code),
        "symbol": normalized_symbol,
        "data_source": data_source_type,
        "market_rules": market_rules.to_dict(),
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
            {"side": t.side, "quantity": t.quantity, "price": t.price, "pnl": t.pnl, "tag": t.tag}
            for t in result.trades
        ],
        "error_message": result.error_message,
    }




@router.post("/compare")
def compare_strategies(
    symbol: str = Query("AAPL"),
    years: int = Query(5, ge=1, le=20),
    initial_cash: float = Query(100000.0),
    market: str = Query("US", description="市场: US|CN|HK"),
):
    """多策略对比"""
    market_code = _api_market(market)
    normalized_symbol = normalize_symbol(symbol, market_code) if market_code != "US" else symbol.upper()
    df, data_source_type, _, normalized_symbol = _get_backtest_data(normalized_symbol, years, market_code)
    market_rules = get_market_backtest_config(market_code)

    results = {}
    for sid, sclass in STRATEGIES.items():
        engine = BacktestEngine(
            data=df,
            strategy_class=sclass,
            symbol=normalized_symbol,
            initial_cash=initial_cash,
            market=market_code,
            market_config=market_rules,
        )

        result = engine.run()
        results[sid] = {
            "total_return_pct": result.total_return_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown_pct": result.max_drawdown_pct,
            "total_trades": result.total_trades,
            "equity_curve": result.equity_curve[:100],
        }

    return {
        "market": market_code,
        "currency": get_currency(market_code),
        "symbol": normalized_symbol,
        "data_source": data_source_type,
        "market_rules": market_rules.to_dict(),
        "strategies": results,
    }






@router.get("/status/{symbol}")
def get_data_status(symbol: str, market: str = Query("US", description="市场: US|CN|HK")):
    """获取股票数据状态"""
    market_code = _api_market(market)
    normalized = normalize_symbol(symbol, market_code) if market_code != "US" else symbol.upper()
    db_rows = market_mgr.get_daily_from_db(market_code, normalized, years=10)

    if db_rows:
        return {
            "market": market_code,
            "currency": get_currency(market_code),
            "symbol": normalized,
            "status": "available",
            "rows": len(db_rows),
            "start_date": str(db_rows[0].date) if db_rows else None,
            "end_date": str(db_rows[-1].date) if db_rows else None,
            "source": "database",
        }

    summaries = market_mgr.get_sync_summary(market_code)
    sync = next((item for item in summaries if item["symbol"] == normalized), None)
    if sync and sync.get("status") == "syncing":
        return {
            "market": market_code,
            "currency": get_currency(market_code),
            "symbol": normalized,
            "status": "syncing",
            "source": "database",
        }
    if sync and sync.get("status") == "error":
        return {
            "market": market_code,
            "currency": get_currency(market_code),
            "symbol": normalized,
            "status": "error",
            "source": "database",
            "error": sync.get("error"),
        }
    return {
        "market": market_code,
        "currency": get_currency(market_code),
        "symbol": normalized,
        "status": "missing",
        "rows": 0,
        "source": "none",
        "hint": "调用 /api/backtest/run 时会自动下载",
    }



@router.post("/warmup")
def warmup_data(
    symbols: str = Query(..., description="股票代码，逗号分隔"),
    market: str = Query("US", description="市场: US|CN|HK"),
):
    """预热数据 - 下载指定股票"""
    market_code = _api_market(market)
    if market_code == "US":
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        symbol_list = [normalize_symbol(s.strip(), market_code) for s in symbols.split(",") if s.strip()]

    results = {"submitted": [], "already_has": [], "failed": []}
    for sym in symbol_list[:20]:
        db_rows = market_mgr.get_daily_from_db(market_code, sym, years=5)
        if db_rows:
            results["already_has"].append(sym)
            continue
        ok, _, err = market_mgr.lazy_download_one(market_code, sym)
        if ok:
            results["submitted"].append(sym)
        else:
            results["failed"].append({"symbol": sym, "error": err})

    return {
        "market": market_code,
        "currency": get_currency(market_code),
        "message": "预热请求已处理",
        **results,
    }


