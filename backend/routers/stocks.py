"""
美股数据 API
"""
import logging
from typing import Optional, List
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Query, HTTPException

from backend.crawlers.us_stock_source import USStockSource, MAJOR_US_STOCKS, SECTOR_MAP
from backend.crawlers.data_cleaner import USDataCleaner
from backend.data_manager import DataManager

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])
logger = logging.getLogger(__name__)
data_source = USStockSource()
data_mgr = DataManager(request_delay=0.6)

# 指数成分映射
INDEX_CONSTITUENTS = {
    "SPY": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "TSLA",
            "JPM", "V", "UNH", "XOM", "PG", "JNJ", "MA", "HD", "CVX", "MRK",
            "ABBV", "BAC", "PEP", "KO", "COST", "WMT", "ADBE", "CRM", "NFLX",
            "CMCSA", "AVGO", "TMO", "ACN", "DHR", "NEE", "ABT", "DIS", "LIN"],
    "QQQ": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "ADBE",
            "AMD", "NFLX", "PYPL", "INTC", "QCOM", "TXN", "AVGO", "CMCSA"],
    "DIA": ["AAPL", "MSFT", "UNH", "V", "JPM", "JNJ", "WMT", "PG", "HD", "CVX",
            "MMM", "AXP", "BA", "CAT", "CSCO", "KO", "C", "DIS", "XOM", "GS",
            "HD", "IBM", "INTC", "JNJ", "JPM", "MCD", "MRK", "MSFT", "NKE", "PFE"],
}

# 交易所映射
EXCHANGE_MAP = {
    "NASDAQ": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "ADBE",
               "AMD", "INTC", "NFLX", "PYPL", "BIDU", "PDD", "AVGO", "CMCSA",
               "TXN", "QCOM", "BKNG", "ISRG", "GILD", "ADSK", "NTES"],
    "NYSE": ["BRK-B", "JPM", "V", "UNH", "XOM", "PG", "JNJ", "MA", "HD", "CVX",
             "MRK", "ABBV", "BAC", "PEP", "KO", "COST", "WMT", "CRM", "TMO",
             "ACN", "DHR", "NEE", "ABT", "DIS", "LIN", "VZ", "PM", "IBM"],
}


@router.get("/filters")
def get_filter_options():
    """获取筛选选项"""
    # 获取所有板块
    sectors = list(set(SECTOR_MAP.values()))
    sectors = [s for s in sectors if s]
    sectors.sort()
    
    # 获取所有交易所
    exchanges = list(EXCHANGE_MAP.keys())
    
    # 获取指数列表
    indices = list(INDEX_CONSTITUENTS.keys())
    
    return {
        "sectors": sectors,
        "exchanges": exchanges,
        "indices": indices,
        "market_cap_options": [10, 20, 30, 50, 100],
    }


@router.get("/")
def list_stocks(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    filter_type: Optional[str] = Query(None, description="筛选类型: sector|exchange|market_cap|index|custom"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
):
    """获取美股列表（支持多种筛选方式）"""
    stocks = data_mgr.get_stock_list()
    
    # 应用筛选
    if filter_type and filter_value:
        if filter_type == "sector":
            stocks = [s for s in stocks if s.get("sector") == filter_value]
        elif filter_type == "exchange":
            # 从交易所映射获取该交易所的股票
            exchange_stocks = EXCHANGE_MAP.get(filter_value, [])
            stocks = [s for s in stocks if s["symbol"] in exchange_stocks]
        elif filter_type == "market_cap":
            # 按市值排序取前N
            limit_n = int(filter_value)
            stocks_with_cap = [s for s in stocks if s.get("market_cap")]
            stocks_with_cap.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
            stocks = stocks_with_cap[:limit_n]
        elif filter_type == "index":
            # 按指数成分筛选
            index_stocks = INDEX_CONSTITUENTS.get(filter_value, [])
            stocks = [s for s in stocks if s["symbol"] in index_stocks]
        elif filter_type == "custom":
            # 自定义符号列表（逗号分隔）
            custom_symbols = [s.strip().upper() for s in filter_value.split(",")]
            stocks = [s for s in stocks if s["symbol"] in custom_symbols]
    
    total = len(stocks)
    page = stocks[offset:offset + limit]
    return {"total": total, "data": page, "filter_type": filter_type, "filter_value": filter_value}


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
