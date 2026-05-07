"""
美股数据 API
"""
import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException

from backend.crawlers.us_stock_source import USStockSource, MAJOR_US_STOCKS
from backend.crawlers.data_cleaner import USDataCleaner

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])
logger = logging.getLogger(__name__)
data_source = USStockSource()


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
    """获取日线数据"""
    df = data_source.get_full_history(symbol.upper(), years=years)
    if df.empty:
        raise HTTPException(404, f"股票 {symbol} 无日线数据")

    df = USDataCleaner.clean_daily_data(df)
    if indicators:
        df = USDataCleaner.add_technical_indicators(df)

    return {
        "symbol": symbol.upper(),
        "total": len(df),
        "start_date": str(df["date"].iloc[0]) if "date" in df.columns else None,
        "end_date": str(df["date"].iloc[-1]) if "date" in df.columns else None,
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
