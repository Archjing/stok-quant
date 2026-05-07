                                                                                                                            """
美股数据源 - 基于 yfinance
支持 US stock data: quotes, history, fundamentals, sectors
"""
import time
import random
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


# ---- SP500 + NASDAQ + NYSE 常用股票列表 ----
MAJOR_US_STOCKS = [
    # S&P 500 头部
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "TSLA",
    "JPM", "V", "UNH", "XOM", "PG", "JNJ", "MA", "HD", "CVX", "MRK",
    "ABBV", "BAC", "PEP", "KO", "COST", "WMT", "ADBE", "CRM", "NFLX",
    "CMCSA", "AVGO", "TMO", "ACN", "DHR", "NEE", "ABT", "DIS", "LIN",
    "TXN", "VZ", "PM", "IBM", "QCOM", "AMD", "INTC", "PYPL", "BA",
    "GE", "CAT", "GS", "MS", "C", "WFC", "SPY", "QQQ", "DIA", "IWM",
    # 中概股
    "BABA", "JD", "PDD", "BIDU", "NIO", "LI", "XPEV", "TCOM",
    # ETF
    "VTI", "VOO", "IVV", "VEA", "VWO", "BND", "AGG", "GLD", "SLV",
    # 热门
    "TSM", "ASML", "SAP", "NVS", "NVO", "TM", "SONY", "UL", "RY",
]

# S&P 500 行业分类
SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Consumer Cyclical", "NVDA": "Technology", "META": "Technology",
    "JPM": "Financial Services", "V": "Financial Services", "UNH": "Healthcare",
    "XOM": "Energy", "PG": "Consumer Defensive", "JNJ": "Healthcare",
    "MA": "Financial Services", "HD": "Consumer Cyclical", "CVX": "Energy",
    "MRK": "Healthcare", "ABBV": "Healthcare", "BAC": "Financial Services",
    "PEP": "Consumer Defensive", "KO": "Consumer Defensive", "WMT": "Consumer Defensive",
    "COST": "Consumer Defensive", "ADBE": "Technology", "CRM": "Technology",
    "NFLX": "Communication Services", "TMO": "Healthcare", "ACN": "Technology",
    "DIS": "Communication Services", "LIN": "Basic Materials", "TXN": "Technology",
    "VZ": "Communication Services", "PM": "Consumer Defensive", "IBM": "Technology",
    "QCOM": "Technology", "AMD": "Technology", "INTC": "Technology",
    "BA": "Industrials", "GE": "Industrials", "CAT": "Industrials",
    "GS": "Financial Services", "MS": "Financial Services", "C": "Financial Services",
}


class USStockSource:
    """美国股票数据源 (yfinance)"""

    def __init__(self):
        self._delay_min = 0.3
        self._delay_max = 1.0
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        ]

    def _random_delay(self):
        time.sleep(random.uniform(self._delay_min, self._delay_max))

    def get_stock_list(self) -> List[Dict[str, Any]]:
        """获取美股列表（含基本信息）"""
        stocks = []
        for i, symbol in enumerate(MAJOR_US_STOCKS):
            try:
                info = self.get_stock_info(symbol)
                if info:
                    stocks.append(info)
                self._random_delay()
                if (i + 1) % 20 == 0:
                    logger.info(f"已获取 {i+1}/{len(MAJOR_US_STOCKS)} 只股票信息")
            except Exception as e:
                logger.warning(f"获取 {symbol} 信息失败: {e}")
                continue
        logger.info(f"共获取 {len(stocks)} 只美股信息")
        return stocks

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取单只股票基本信息"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            return {
                "symbol": symbol,
                "name": info.get("longName") or info.get("shortName", ""),
                "exchange": info.get("exchange", "NASDAQ"),
                "sector": SECTOR_MAP.get(symbol) or info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "employees": info.get("fullTimeEmployees"),
                "ipo_year": info.get("ipoYear"),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "eps": info.get("trailingEps"),
            }
        except Exception as e:
            logger.debug(f"获取 {symbol} 信息失败: {e}")
            return None

    def get_daily_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """获取股票日线数据"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, auto_adjust=True)
            if df.empty:
                return pd.DataFrame()
            df = df.reset_index()
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            # yfinance 返回的列: date, open, high, low, close, volume, dividends, stock_splits
            if "close" in df.columns:
                df["adjusted_close"] = df["close"]
            return df
        except Exception as e:
            logger.error(f"获取 {symbol} 日线数据失败: {e}")
            return pd.DataFrame()

    def get_full_history(self, symbol: str, years: int = 10) -> pd.DataFrame:
        """获取完整历史数据"""
        end = datetime.now()
        start = end - timedelta(days=years * 365)
        return self.get_daily_data(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    def get_financials(self, symbol: str) -> Dict[str, Any]:
        """获取财务数据"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            return {
                "roe": info.get("returnOnEquity"),
                "gross_margin": info.get("grossMargins"),
                "operating_margin": info.get("operatingMargins"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "free_cash_flow": info.get("freeCashflow"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "profit_margins": info.get("profitMargins"),
            }
        except Exception as e:
            logger.error(f"获取 {symbol} 财务数据失败: {e}")
            return {}
