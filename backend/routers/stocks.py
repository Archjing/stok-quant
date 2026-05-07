"""
美股数据 API
"""
import logging
from typing import Optional
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Query, HTTPException

from backend.crawlers.us_stock_source import USStockSource, MAJOR_US_STOCKS
from backend.crawlers.data_cleaner import USDataCleaner
from backend.data_manager import DataManager

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])
logger = logging.getLogger(__name__)
data_source = USStockSource()
data_mgr = DataManager(request_delay=0.6)


@router.get("/")
def list_stocks(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sector: Optional[str] = None,
):
    """获取美股列表"""
    stocks = data_source.get_stock_list()
    if sector:
        stocks = [s for s in stocks if s.get("sector") == sector]
    total = len(stocks)
    page = stocks[offset:offset + limit]
    return {"total": total, "data": page}


@router.get("/symbols")
def get_symbols():
    """获取所有支持的股票代码"""
    return {"symbols": MAJOR_US_STOCKS, "total": len(MAJOR_US_STOCKS)}


@router.get("/{symbol}")
def get_stock_detail(symbol: str):
    """获取股票详情"""
    info = data_source.get_stock_info(symbol.upper())
    if not info:
        raise HTTPException(404, f"股票 {symbol} 未找到")
    return info


@router.get("/{symbol}/daily")
def get_stock_daily(
    symbol: str,
    years: int = Query(5, ge=1, le=30),
    indicators: bool = Query(False),
):
    """获取日线数据（优先从数据库缓存读取，不足时实时从 yfinance 获取）"""
    sym = symbol.upper()

    # 1) 尝试从数据库读取
    db_rows = data_mgr.get_daily_from_db(sym, years=years)
    if db_rows:
        return {
            "symbol": sym,
            "total": len(db_rows),
            "start_date": str(db_rows[0].date),
            "end_date": str(db_rows[-1].date),
            "source": "db",
            "data": [
                {
                    "date": str(r.date),
                    "open": r.open, "high": r.high, "low": r.low,
                    "close": r.close, "volume": r.volume,
                    "adjusted_close": r.adjusted_close,
                    "sma_20": r.sma_20, "sma_50": r.sma_50, "sma_200": r.sma_200,
                    "ema_12": r.ema_12, "ema_26": r.ema_26,
                    "macd": r.macd, "macd_signal": r.macd_signal, "macd_hist": r.macd_hist,
                    "rsi_14": r.rsi_14,
                    "bb_upper": r.bb_upper, "bb_middle": r.bb_middle, "bb_lower": r.bb_lower,
                    "atr_14": r.atr_14, "volume_sma_20": r.volume_sma_20,
                }
                for r in db_rows
            ],
        }

    # 2) 数据库无数据，fallback 到 yfinance
    logger.info(f"{sym} 数据库无缓存，从 yfinance 实时获取")
    df = data_source.get_full_history(sym, years=years)
    if df.empty:
        raise HTTPException(404, f"股票 {symbol} 无日线数据")

    df = USDataCleaner.clean_daily_data(df)
    if indicators:
        df = USDataCleaner.add_technical_indicators(df)

    return {
        "symbol": sym,
        "total": len(df),
        "start_date": str(df["date"].iloc[0]) if "date" in df.columns else None,
        "end_date": str(df["date"].iloc[-1]) if "date" in df.columns else None,
        "source": "yfinance",
        "data": df.fillna("").to_dict(orient="records"),
    }


@router.get("/{symbol}/financials")
def get_stock_financials(symbol: str):
    """获取财务数据"""
    financials = data_source.get_financials(symbol.upper())
    info = data_source.get_stock_info(symbol.upper())
    return {"symbol": symbol.upper(), "info": info, "financials": financials}


@router.get("/sectors/list")
def list_sectors():
    """获取行业分类列表"""
    from backend.crawlers.us_stock_source import SECTOR_MAP
    sectors = {}
    for symbol, sector in SECTOR_MAP.items():
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(symbol)
    return {
        "sectors": [
            {"name": k, "count": len(v)} for k, v in sectors.items()
        ]
    }
