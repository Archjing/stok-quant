"""
数据同步 API - 触发批量下载 / 增量更新 / 查看状态。
默认 market=US 保持原美股行为；CN/HK 走 MarketDataManager。
"""
import logging
import threading
from fastapi import APIRouter, HTTPException, Query

from backend.data_manager import DataManager
from backend.market_data_manager import MarketDataManager
from backend.markets.symbols import get_currency, normalize_market, normalize_symbol

router = APIRouter(prefix="/api/data", tags=["Data Sync"])
logger = logging.getLogger(__name__)

_manager = DataManager(request_delay=0.6)
_market_manager = MarketDataManager(request_delay=0.6)
_sync_lock = threading.Lock()
_sync_running = False
_market_sync_running: dict[str, bool] = {"CN": False, "HK": False}
_market_backfill_running: dict[str, bool] = {"CN": False, "HK": False}


def _api_market(market: str) -> str:
    """标准化 API market 参数。"""
    try:
        return normalize_market(market)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def _parse_symbols(symbols: str | None, market: str) -> list[str] | None:
    """解析逗号分隔 symbol 参数。"""
    if not symbols:
        return None
    parsed = [s.strip() for s in symbols.split(",") if s.strip()]
    if market == "US":
        return [s.upper() for s in parsed]
    return [normalize_symbol(s, market) for s in parsed]


@router.get("/status")
def sync_status(market: str = Query("US", description="市场: US|CN|HK")):
    """查看各股票数据同步状态"""
    market_code = _api_market(market)
    if market_code != "US":
        return {
            "market": market_code,
            "currency": get_currency(market_code),
            "running": _market_sync_running.get(market_code, False),
            "stocks": _market_manager.get_sync_summary(market_code),
        }
    return {
        "market": "US",
        "currency": "USD",
        "running": _sync_running,
        "stocks": _manager.get_sync_summary(),
    }


@router.post("/download")
def trigger_download(
    market: str = Query("US", description="市场: US|CN|HK"),
    symbols: str | None = Query(None, description="股票代码，逗号分隔；为空则下载当前市场股票池"),
    years: int | None = Query(None, ge=1, le=30, description="历史年数"),
):
    """触发历史数据下载（后台异步执行）"""
    market_code = _api_market(market)

    if market_code != "US":
        global _market_sync_running
        if _market_sync_running.get(market_code, False):
            raise HTTPException(400, f"{market_code} 同步任务正在进行中")
        target_symbols = _parse_symbols(symbols, market_code)
        _market_sync_running[market_code] = True

        def _run_market():
            try:
                _market_manager.download_all(market_code, symbols=target_symbols, years=years)
            finally:
                _market_sync_running[market_code] = False

        threading.Thread(target=_run_market, daemon=True).start()
        return {
            "market": market_code,
            "currency": get_currency(market_code),
            "message": f"{market_code} 下载已启动",
            "symbols": target_symbols or "market_stock_pool",
            "years": years or _market_manager.history_years,
        }

    global _sync_running
    if _sync_running:
        raise HTTPException(400, "同步任务正在进行中")
    _sync_running = True

    def _run():
        global _sync_running
        try:
            _manager.download_all()
        finally:
            _sync_running = False

    threading.Thread(target=_run, daemon=True).start()
    return {"market": "US", "currency": "USD", "message": "全量下载已启动", "stocks": 81, "years": _manager.history_years}


@router.post("/update")
def trigger_update(
    market: str = Query("US", description="市场: US|CN|HK"),
    symbols: str | None = Query(None, description="股票代码，逗号分隔；为空则更新当前市场股票池"),
):
    """触发增量更新（后台异步执行）"""
    market_code = _api_market(market)

    if market_code != "US":
        if _market_sync_running.get(market_code, False):
            raise HTTPException(400, f"{market_code} 同步任务正在进行中")
        target_symbols = _parse_symbols(symbols, market_code)
        _market_sync_running[market_code] = True

        def _run_market():
            try:
                _market_manager.incremental_update(market_code, symbols=target_symbols)
            finally:
                _market_sync_running[market_code] = False

        threading.Thread(target=_run_market, daemon=True).start()
        return {
            "market": market_code,
            "currency": get_currency(market_code),
            "message": f"{market_code} 增量更新已启动",
            "symbols": target_symbols or "market_stock_pool",
        }

    global _sync_running
    if _sync_running:
        raise HTTPException(400, "同步任务正在进行中")
    _sync_running = True

    def _run():
        global _sync_running
        try:
            _manager.incremental_update()
        finally:
            _sync_running = False

    threading.Thread(target=_run, daemon=True).start()
    return {"market": "US", "currency": "USD", "message": "增量更新已启动"}


@router.post("/refresh-prices")
def refresh_prices(market: str = Query("US", description="市场: US|CN|HK")):
    """立即刷新所有股票实时价格"""
    market_code = _api_market(market)
    try:
        if market_code != "US":
            count = _market_manager.refresh_stock_prices(market_code)
            return {"market": market_code, "currency": get_currency(market_code), "message": "价格已刷新", "count": count}
        count = _manager.refresh_stock_prices()
        return {"market": "US", "currency": "USD", "message": "价格已刷新", "count": count}
    except Exception as e:
        raise HTTPException(500, f"刷新失败: {e}")


@router.post("/backfill-indicators")
def trigger_backfill_indicators(
    market: str = Query("CN", description="市场: CN|HK"),
    symbols: str | None = Query(None, description="股票代码，逗号分隔；为空则回填当前市场已有历史数据的股票"),
):
    """触发 CN/HK 历史技术指标批量回填（后台异步执行）"""
    market_code = _api_market(market)
    if market_code == "US":
        raise HTTPException(400, "backfill-indicators 仅支持 CN/HK")
    if _market_sync_running.get(market_code, False):
        raise HTTPException(400, f"{market_code} 下载/更新任务正在进行中")
    if _market_backfill_running.get(market_code, False):
        raise HTTPException(400, f"{market_code} 指标回填任务正在进行中")

    target_symbols = _parse_symbols(symbols, market_code)
    _market_backfill_running[market_code] = True

    def _run_market_backfill():
        try:
            _market_manager.backfill_technical_indicators(market_code, symbols=target_symbols)
        finally:
            _market_backfill_running[market_code] = False

    threading.Thread(target=_run_market_backfill, daemon=True).start()
    return {
        "market": market_code,
        "currency": get_currency(market_code),
        "message": f"{market_code} 指标回填已启动",
        "symbols": target_symbols or "existing_market_history",
    }
