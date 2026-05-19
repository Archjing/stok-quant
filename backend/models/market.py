"""
多市场通用数据模型。

第一阶段仅供 CN/HK 新市场链路使用；US 继续使用现有 USStock / USStockDaily。
"""
from sqlalchemy import Column, Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from backend.database import Base


class MarketStock(Base):
    """多市场股票基础信息。"""

    __tablename__ = "market_stocks"

    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(10), index=True, nullable=False)       # US / CN / HK
    symbol = Column(String(20), index=True, nullable=False)       # AAPL / SH.600519 / HK.00700
    raw_symbol = Column(String(20), index=True)                   # AAPL / 600519 / 00700
    name = Column(String(200), nullable=False)
    exchange = Column(String(50), index=True)                     # NASDAQ / NYSE / SH / SZ / BJ / HKEX
    board = Column(String(100))                                   # 主板 / 创业板 / 科创板 / 北交所 / 港股主板
    sector = Column(String(100))
    industry = Column(String(100))
    area = Column(String(100))
    country = Column(String(50))
    currency = Column(String(10))                                 # USD / CNY / HKD

    price = Column(Float)
    change_pct = Column(Float)
    market_cap = Column(Float)
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    dividend_yield = Column(Float)
    turnover_rate = Column(Float)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("market", "symbol", name="uix_market_stock_symbol"),
    )


class MarketDailyBar(Base):
    """多市场日线 OHLCV 数据。"""

    __tablename__ = "market_daily_bars"

    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(10), index=True, nullable=False)
    symbol = Column(String(20), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)

    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    adjusted_close = Column(Float)

    change_pct = Column(Float)
    change_amount = Column(Float)
    amplitude = Column(Float)
    turnover_rate = Column(Float)

    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    ema_12 = Column(Float)
    ema_26 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    rsi_14 = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    atr_14 = Column(Float)
    volume_sma_20 = Column(Float)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("market", "symbol", "date", name="uix_market_symbol_date"),
    )


class MarketSyncStatus(Base):
    """多市场数据同步状态。"""

    __tablename__ = "market_sync_status"

    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(10), index=True, nullable=False)
    symbol = Column(String(20), index=True, nullable=False)
    last_sync_date = Column(Date)
    last_sync_time = Column(DateTime, server_default=func.now(), onupdate=func.now())
    total_rows = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    error_message = Column(String(500))
    retry_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("market", "symbol", name="uix_market_sync_symbol"),
    )
