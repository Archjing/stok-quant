"""
美股数据 API
"""
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException

from backend.crawlers.us_stock_source import USStockSource, MAJOR_US_STOCKS, SECTOR_MAP
from backend.crawlers.data_cleaner import USDataCleaner
from backend.data_manager import DataManager

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])
logger = logging.getLogger(__name__)
data_source = USStockSource()
data_mgr = DataManager(request_delay=0.6)


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
    filter_type: Optional[str] = Query(None, description="筛选类型: sector|exchange|market_cap|index|custom"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
):
    """获取美股列表（支持多种筛选方式）"""
    stocks = data_mgr.get_stock_list()
    
    if filter_type and filter_value:
        if filter_type == "sector":
            stocks = [s for s in stocks if s.get("sector") == filter_value]
        elif filter_type == "exchange":
            exchange_stocks = EXCHANGE_MAP.get(filter_value, [])
            stocks = [s for s in stocks if s["symbol"] in exchange_stocks]
        elif filter_type == "market_cap":
            limit_n = int(filter_value)
            stocks_with_cap = [s for s in stocks if s.get("market_cap")]
            stocks_with_cap.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
            stocks = stocks_with_cap[:limit_n]
        elif filter_type == "index":
            index_stocks = INDEX_CONSTITUENTS.get(filter_value, [])
            stocks = [s for s in stocks if s["symbol"] in index_stocks]
        elif filter_type == "custom":
            custom_symbols = [s.strip().upper() for s in filter_value.split(",")]
            stocks = [s for s in stocks if s["symbol"] in custom_symbols]
    
    total = len(stocks)
    page = stocks[offset:offset + limit]
    return {"total": total, "data": page, "filter_type": filter_type, "filter_value": filter_value}


@router.get("/symbols")
def get_symbols():
    """获取所有支持的股票代码"""
    return {"symbols": MAJOR_US_STOCKS, "total": len(MAJOR_US_STOCKS)}


# ============ 带 symbol 路径的路由必须放在 /{symbol} 通用路由之前 ============

@router.get("/{symbol}/daily")
def get_stock_daily(
    symbol: str,
    years: int = Query(5, ge=1, le=30),
    indicators: bool = Query(False),
):
    """获取日线数据（优先从数据库缓存读取，不足时实时从 yfinance 获取）"""
    sym = symbol.upper()

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


@router.get("/{symbol}/kline")
def get_stock_kline(
    symbol: str,
    period: str = Query("daily", description="周期: daily|monthly|yearly"),
    years: int = Query(5, ge=1, le=30),
):
    """
    获取 K 线数据（支持日线、月线、年线）
    用于前端 K 线图展示
    数据格式：{"x": 毫秒时间戳, "y": [open, high, low, close]}
    """
    sym = symbol.upper()

    if period == "daily":
        db_rows = data_mgr.get_daily_from_db(sym, years=years)
        if db_rows:
            return {
                "symbol": sym,
                "period": "daily",
                "source": "db",
                "data": [
                    {"x": date_to_timestamp(r.date), "y": [r.open, r.high, r.low, r.close]}
                    for r in db_rows
                ],
            }
        logger.info(f"{sym} 日线数据库无缓存，从 yfinance 实时获取")
        df = data_source.get_full_history(sym, years=years)
        if not df.empty:
            return {
                "symbol": sym,
                "period": "daily",
                "source": "yfinance",
                "data": [
                    {"x": date_to_timestamp(r["date"]), "y": [r["open"], r["high"], r["low"], r["close"]]}
                    for r in df.to_dict(orient="records")
                ],
            }

    else:
        # monthly 或 yearly：按周期分组，用第一个交易日的时间戳
        import pandas as pd
        freq = "M" if period == "monthly" else "Y"
        min_years = 5 if period == "monthly" else 10
        db_rows = data_mgr.get_daily_from_db(sym, years=max(years, min_years))
        source_label = "db"
        if db_rows:
            df = pd.DataFrame([
                {"date": r.date, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume}
                for r in db_rows
            ])
        else:
            logger.info(f"{sym} {period} 数据库无缓存，从 yfinance 实时获取")
            df = data_source.get_full_history(sym, years=max(years, min_years))
            if df.empty:
                raise HTTPException(404, f"股票 {symbol} K线数据获取失败")
            source_label = "yfinance"
            df["date"] = pd.to_datetime(df["date"])

        df["date"] = pd.to_datetime(df["date"])
        df["period"] = df["date"].dt.to_period(freq)
        grouped = df.groupby("period")
        data = []
        for _, group in grouped:
            row = group.iloc[0]
            x_val = int(row["date"].timestamp() * 1000)
            y_val = [
                float(group["open"].iloc[0]),
                float(group["high"].max()),
                float(group["low"].min()),
                float(group["close"].iloc[-1]),
            ]
            data.append({"x": x_val, "y": y_val})

        return {
            "symbol": sym,
            "period": period,
            "source": source_label,
            "data": data,
        }

    raise HTTPException(404, f"股票 {symbol} K线数据获取失败")


@router.get("/{symbol}/financials")
def get_stock_financials(symbol: str):
    """获取财务数据"""
    financials = data_source.get_financials(symbol.upper())
    info = data_source.get_stock_info(symbol.upper())
    return {"symbol": symbol.upper(), "info": info, "financials": financials}


# ============ 通用路由放在最后 ============

@router.get("/{symbol}")
def get_stock_detail(symbol: str):
    """获取股票详情"""
    info = data_source.get_stock_info(symbol.upper())
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
