
"""
股票数据 API

多市场统一使用 MarketDataManager 读取通用表；
US 的财务详情仍保留 yfinance 直连作为补充信息源。
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException

from backend.crawlers.us_stock_source import USStockSource, MAJOR_US_STOCKS, STOCK_NAMES, SECTOR_MAP

from backend.crawlers.data_cleaner import USDataCleaner
from backend.market_data_manager import MarketDataManager

from backend.markets.registry import get_market_source
from backend.markets.symbols import get_currency, normalize_market, normalize_symbol


router = APIRouter(prefix="/api/stocks", tags=["Stocks"])
logger = logging.getLogger(__name__)
data_source = USStockSource()
market_mgr = MarketDataManager(request_delay=0.6)




def date_to_timestamp(d) -> int:
    """将日期转换为 ApexCharts 需要的时间戳（毫秒）"""
    if isinstance(d, str):
        dt = datetime.strptime(d, "%Y-%m-%d")
    elif isinstance(d, datetime):
        dt = d
    elif hasattr(d, 'to_pydatetime'):
        dt = d.to_pydatetime()
    else:
        dt = datetime.combine(d, datetime.min.time())
    return int(dt.timestamp() * 1000)


def _api_market(market: str) -> str:
    """标准化 API market 参数。"""
    try:
        return normalize_market(market)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def _filter_market_stocks(stocks: list[dict], market: str, filter_type: Optional[str], filter_value: Optional[str]) -> list[dict]:
    """CN/HK 通用列表筛选。第一阶段支持 exchange/board/custom。"""
    if not filter_type or not filter_value:
        return stocks
    if filter_type == "exchange":
        return [s for s in stocks if s.get("exchange") == filter_value]
    if filter_type == "board":
        return [s for s in stocks if s.get("board") == filter_value]
    if filter_type == "custom":
        symbols = {normalize_symbol(s.strip(), market) for s in filter_value.split(",") if s.strip()}
        return [s for s in stocks if s.get("symbol") in symbols]
    return stocks


def _apply_text_search(stocks: list[dict], query: Optional[str]) -> list[dict]:
    """按代码或名称进行文本搜索。"""
    if not query:
        return stocks
    needle = query.strip().lower()
    if not needle:
        return stocks
    return [
        s for s in stocks
        if needle in str(s.get("symbol") or "").lower()
        or needle in str(s.get("name") or "").lower()
    ]





def _market_daily_payload(market: str, symbol: str, rows, source: str, indicators: bool = False) -> dict:
    """构建统一 daily 响应。"""
    df = market_mgr.rows_to_dataframe(rows)
    df = USDataCleaner.clean_daily_data(df)
    if indicators:
        df = USDataCleaner.add_technical_indicators(df)
    return {
        "market": market,
        "currency": get_currency(market),
        "symbol": symbol,
        "total": len(df),
        "start_date": str(df["date"].iloc[0]) if not df.empty else None,
        "end_date": str(df["date"].iloc[-1]) if not df.empty else None,
        "source": source,
        "data": df.fillna("").to_dict(orient="records"),
    }




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


def _static_us_stock_list() -> list[dict]:
    """返回无需网络请求的美股基础列表，避免行情源限流导致列表页不可用。"""
    nasdaq_symbols = set(EXCHANGE_MAP.get("NASDAQ", []))
    return [
        {
            "symbol": symbol,
            "name": STOCK_NAMES.get(symbol, symbol),
            "exchange": "NASDAQ" if symbol in nasdaq_symbols else "NYSE",
            "sector": SECTOR_MAP.get(symbol),
            "price": None,
            "change_pct": None,
            "market_cap": None,
            "pe_ratio": None,
        }
        for symbol in MAJOR_US_STOCKS
    ]


def _apply_us_filters(stocks: list[dict], filter_type: Optional[str], filter_value: Optional[str]) -> list[dict]:
    """美股列表筛选。"""
    if not filter_type or not filter_value:
        return stocks
    if filter_type == "sector":
        return [s for s in stocks if s.get("sector") == filter_value]
    if filter_type == "exchange":
        exchange_stocks = set(EXCHANGE_MAP.get(filter_value, []))
        return [s for s in stocks if s["symbol"] in exchange_stocks]
    if filter_type == "market_cap":
        limit_n = int(filter_value)
        stocks_with_cap = [s for s in stocks if s.get("market_cap")]
        stocks_with_cap.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
        return stocks_with_cap[:limit_n]
    if filter_type == "index":
        index_stocks = set(INDEX_CONSTITUENTS.get(filter_value, []))
        return [s for s in stocks if s["symbol"] in index_stocks]
    if filter_type == "custom":
        custom_symbols = {s.strip().upper() for s in filter_value.split(",") if s.strip()}
        return [s for s in stocks if s["symbol"] in custom_symbols]
    return stocks


@router.get("/filters")
def get_filter_options(market: str = Query("US")):

    """获取筛选选项"""
    market_code = _api_market(market)
    if market_code != "US":
        stocks = market_mgr.get_stock_list(market_code)
        exchanges = sorted({s.get("exchange") for s in stocks if s.get("exchange")})
        boards = sorted({s.get("board") for s in stocks if s.get("board")})
        return {
            "sectors": [],
            "exchanges": exchanges,
            "indices": [],
            "boards": boards,
            "market_cap_options": [],
        }

    sectors = list(set(SECTOR_MAP.values()))
    sectors = [s for s in sectors if s]
    sectors.sort()
    exchanges = list(EXCHANGE_MAP.keys())
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
    filter_type: Optional[str] = Query(None, description="筛选类型: sector|exchange|market_cap|index|custom|board"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
    search: Optional[str] = Query(None, description="按代码或名称搜索"),
    market: str = Query("US", description="市场: US|CN|HK"),
):
    """获取股票列表（支持 US/CN/HK）"""
    market_code = _api_market(market)
    stocks = market_mgr.get_stock_list(market_code)
    if market_code != "US":
        stocks = _filter_market_stocks(stocks, market_code, filter_type, filter_value)
    else:
        stocks = _apply_us_filters(stocks, filter_type, filter_value)
    stocks = _apply_text_search(stocks, search)
    total = len(stocks)
    page = stocks[offset:offset + limit]
    return {
        "market": market_code,
        "currency": get_currency(market_code),
        "total": total,
        "data": page,
        "filter_type": filter_type,
        "filter_value": filter_value,
    }






@router.get("/symbols")
def get_symbols(market: str = Query("US", description="市场: US|CN|HK")):
    """获取所有支持的股票代码"""
    market_code = _api_market(market)
    stocks = market_mgr.get_stock_list(market_code)
    symbols = [s["symbol"] for s in stocks]
    return {"market": market_code, "symbols": symbols, "total": len(symbols)}




# ============ 带 symbol 路径的路由必须放在 /{symbol} 通用路由之前 ============

@router.get("/{symbol}/daily")
def get_stock_daily(
    symbol: str,
    years: int = Query(5, ge=1, le=30),
    indicators: bool = Query(False),
    market: str = Query("US", description="市场: US|CN|HK"),
):
    """获取日线数据（统一使用 MarketDataManager）"""
    market_code = _api_market(market)
    sym = normalize_symbol(symbol, market_code) if market_code != "US" else symbol.upper()
    db_rows = market_mgr.get_daily_from_db(market_code, sym, years=years)
    source = "db"
    if not db_rows:
        ok, _, err = market_mgr.lazy_download_one(market_code, sym, years=years)
        if not ok:
            raise HTTPException(404, f"股票 {symbol} 无日线数据: {err}")
        db_rows = market_mgr.get_daily_from_db(market_code, sym, years=years)
        source = "downloaded"
    if not db_rows:
        raise HTTPException(404, f"股票 {symbol} 无日线数据")
    return _market_daily_payload(market_code, sym, db_rows, source, indicators=indicators)





@router.get("/{symbol}/kline")
def get_stock_kline(
    symbol: str,
    period: str = Query("daily", description="周期: daily|monthly|yearly"),
    years: int = Query(5, ge=1, le=30),
    market: str = Query("US", description="市场: US|CN|HK"),
):
    """
    获取 K 线数据（支持日线、月线、年线）
    用于前端 K 线图展示
    数据格式：{"x": 毫秒时间戳, "y": [open, high, low, close]}
    """
    market_code = _api_market(market)
    if period not in {"daily", "monthly", "yearly"}:
        raise HTTPException(400, "period 仅支持 daily|monthly|yearly")

    import pandas as pd

    sym = normalize_symbol(symbol, market_code) if market_code != "US" else symbol.upper()
    query_years = max(years, 10) if period == "yearly" else max(years, 5) if period == "monthly" else years
    db_rows = market_mgr.get_daily_from_db(market_code, sym, years=query_years)
    source_label = "db"
    if not db_rows:
        ok, _, err = market_mgr.lazy_download_one(market_code, sym, years=query_years)
        if not ok:
            raise HTTPException(404, f"股票 {symbol} K线数据获取失败: {err}")
        db_rows = market_mgr.get_daily_from_db(market_code, sym, years=query_years)
        source_label = "downloaded"
    if not db_rows:
        raise HTTPException(404, f"股票 {symbol} K线数据获取失败")

    df = market_mgr.rows_to_dataframe(db_rows)
    if period == "daily":
        return {
            "market": market_code,
            "currency": get_currency(market_code),
            "symbol": sym,
            "period": "daily",
            "source": source_label,
            "data": [
                {"x": date_to_timestamp(r["date"]), "y": [r["open"], r["high"], r["low"], r["close"]]}
                for r in df.to_dict(orient="records")
            ],
        }

    freq = "M" if period == "monthly" else "Y"
    df["date"] = pd.to_datetime(df["date"])
    df["period"] = df["date"].dt.to_period(freq)
    data = []
    for _, group in df.groupby("period"):
        row = group.iloc[0]
        data.append({
            "x": int(row["date"].timestamp() * 1000),
            "y": [
                float(group["open"].iloc[0]),
                float(group["high"].max()),
                float(group["low"].min()),
                float(group["close"].iloc[-1]),
            ],
        })
    return {
        "market": market_code,
        "currency": get_currency(market_code),
        "symbol": sym,
        "period": period,
        "source": source_label,
        "data": data,
    }




@router.get("/{symbol}/financials")
def get_stock_financials(symbol: str, market: str = Query("US", description="市场: US|CN|HK")):
    """获取财务数据"""
    market_code = _api_market(market)
    if market_code != "US":
        source = get_market_source(market_code)
        sym = normalize_symbol(symbol, market_code)
        info = source.get_stock_info(sym)
        return {"market": market_code, "currency": get_currency(market_code), "symbol": sym, "info": info, "financials": {}}
    financials = data_source.get_financials(symbol.upper())
    info = data_source.get_stock_info(symbol.upper())
    return {"market": "US", "currency": "USD", "symbol": symbol.upper(), "info": info, "financials": financials}



# ============ 通用路由放在最后 ============

@router.get("/{symbol}")
def get_stock_detail(symbol: str, market: str = Query("US", description="市场: US|CN|HK")):
    """获取股票详情"""
    market_code = _api_market(market)
    sym = normalize_symbol(symbol, market_code) if market_code != "US" else symbol.upper()
    stocks = market_mgr.get_stock_list(market_code)
    info = next((item for item in stocks if item.get("symbol") == sym), None)
    if info:
        return info
    if market_code != "US":
        source = get_market_source(market_code)
        info = source.get_stock_info(sym)
        if not info:
            raise HTTPException(404, f"股票 {symbol} 未找到")
        return info
    info = data_source.get_stock_info(sym)
    if not info:
        raise HTTPException(404, f"股票 {symbol} 未找到")
    return info




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
