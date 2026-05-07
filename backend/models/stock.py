               """
美股数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from backend.database import Base


class USStock(Base):
    """美股基本信息 (S&P 500 + NASDAQ + NYSE)"""
    __tablename__ = "us_stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    exchange = Column(String(50))          # NYSE, NASDAQ, AMEX
    sector = Column(String(100))           # Technology, Healthcare, etc.
    industry = Column(String(100))
    market_cap = Column(Float)             # 市值 (USD)
    employees = Column(Integer)            # 员工数
    ipo_year = Column(Integer)             # IPO年份
    country = Column(String(50), default="US")
    currency = Column(String(10), default="USD")
    
    # 实时估值
    price = Column(Float)
    pe_ratio = Column(Float)               # 市盈率
    pb_ratio = Column(Float)               # 市净率
    ps_ratio = Column(Float)               # 市销率
    dividend_yield = Column(Float)         # 股息率
    beta = Column(Float)                   # Beta系数
    eps = Column(Float)                    # 每股收益
    eps_growth = Column(Float)             # EPS增长率(%)
    revenue_growth = Column(Float)         # 营收增长率(%)
    
    # 财务指标
    roe = Column(Float)                    # 净资产收益率
    gross_margin = Column(Float)           # 毛利率
    operating_margin = Column(Float)       # 营业利润率
    debt_to_equity = Column(Float)         # 负债权益比
    current_ratio = Column(Float)          # 流动比率
    free_cash_flow = Column(Float)         # 自由现金流
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class USStockDaily(Base):
    """美股日线数据"""
    __tablename__ = "us_stock_daily"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    adjusted_close = Column(Float)          # 复权收盘价
    
    # 技术指标（预计算）
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
        UniqueConstraint("symbol", "date", name="uix_symbol_date"),
    )
