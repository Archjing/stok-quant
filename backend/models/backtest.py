"""
回测结果数据模型
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, JSON
from sqlalchemy.sql import func
from backend.database import Base


class BacktestRun(Base):
    """回测运行记录"""
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))
    strategy_name = Column(String(100))
    symbol = Column(String(10))
    start_date = Column(Date)
    end_date = Column(Date)
    initial_cash = Column(Float, default=100000.0)
    commission = Column(Float, default=0.001)
    slippage = Column(Float, default=0.0005)
    
    # 回测结果
    total_return = Column(Float)           # 总收益率(%)
    annualized_return = Column(Float)      # 年化收益率(%)
    volatility = Column(Float)             # 波动率
    sharpe_ratio = Column(Float)           # 夏普比率
    sortino_ratio = Column(Float)          # 索提诺比率
    calmar_ratio = Column(Float)           # 卡玛比率
    max_drawdown = Column(Float)           # 最大回撤(%)
    max_drawdown_duration = Column(Integer)  # 最大回撤持续天数
    win_rate = Column(Float)               # 胜率(%)
    profit_factor = Column(Float)          # 盈亏比
    total_trades = Column(Integer)         # 总交易次数
    avg_holding_days = Column(Float)       # 平均持仓天数
    
    # 详细数据（JSON）
    equity_curve = Column(JSON)            # 权益曲线
    drawdown_curve = Column(JSON)          # 回撤曲线
    trade_log = Column(JSON)               # 交易日志
    monthly_returns = Column(JSON)         # 月度收益
    benchmark_returns = Column(JSON)       # 基准收益
    
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    error_message = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())
