"""
回测引擎核心 - 事件驱动回测框架
"""
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import date, datetime
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from backend.backtest.strategies import Strategy
from backend.backtest.metrics import calculate_metrics

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """订单"""
    symbol: str
    quantity: int
    order_type: str = "market"   # market, limit, stop
    side: str = "buy"            # buy, sell
    price: Optional[float] = None
    status: str = "pending"      # pending, filled, rejected, cancelled
    filled_price: Optional[float] = None
    filled_time: Optional[datetime] = None
    commission: float = 0.0
    tag: str = ""


@dataclass
class Trade:
    """成交记录"""
    symbol: str
    side: str
    quantity: int
    price: float
    time: datetime
    commission: float = 0.0
    pnl: float = 0.0
    tag: str = ""


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return self.quantity * (self.current_price - self.avg_cost)

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost * 100


@dataclass
class Bar:
    """一根K线"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float = None
    indicators: Dict[str, float] = field(default_factory=dict)

    @property
    def timestamp_str(self) -> str:
        return self.timestamp.strftime("%Y-%m-%d")


@dataclass
class BacktestResult:
    """回测结果"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_bars: int = 0
    initial_cash: float = 100000.0
    end_cash: float = 0.0
    total_trades: int = 0
    total_pnl: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    status: str = "completed"
    error_message: str = ""


class BacktestEngine:
    """事件驱动回测引擎"""

    def __init__(
        self,
        data: pd.DataFrame,
        strategy_class: type,
        symbol: str,
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        self.data = data
        self.strategy_class = strategy_class
        self.symbol = symbol
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage

        self.cash = initial_cash
        self.position = Position(symbol=symbol)
        self.equity_curve: List[float] = []
        self.trades: List[Trade] = []
        self.current_bar: Optional[Bar] = None
        self.strategy: Optional[Strategy] = None
        self._indicator_cache: Dict[str, Any] = {}

    def run(self) -> BacktestResult:
        """运行回测"""
        try:
            self._validate_data()
            self._add_indicators()

            self.strategy = self.strategy_class()
            self.strategy.engine = self
            self.strategy.on_start()

            bars = self._iter_bars()
            for i, bar in enumerate(bars):
                self.current_bar = bar

                # 更新持仓价格
                self.position.current_price = bar.close

                # 调用策略
                try:
                    self.strategy.on_bar(bar)
                except Exception as e:
                    logger.error(f"策略 on_bar 异常: {e}")
                    continue

                # 记录权益
                equity = self.cash + self.position.market_value
                self.equity_curve.append(equity)

            self.strategy.on_stop()
            return self._generate_result()

        except Exception as e:
            logger.exception(f"回测运行失败")
            return BacktestResult(
                status="failed",
                error_message=str(e),
            )

    def buy(self, symbol: str, quantity: int, price: Optional[float] = None,
            tag: str = ""):
        """买入"""
        if not self.current_bar:
            return

        if price is None:
            price = self.current_bar.close * (1 + self.slippage)

        cost = quantity * price
        commission = cost * self.commission
        total_cost = cost + commission

        if total_cost > self.cash:
            logger.debug(f"现金不足: 需要 {total_cost:.2f}, 可用 {self.cash:.2f}")
            return

        self.cash -= total_cost
        prev_cost = self.position.avg_cost * self.position.quantity
        self.position.quantity += quantity
        self.position.avg_cost = (prev_cost + cost) / self.position.quantity

        self.trades.append(Trade(
            symbol=symbol, side="buy", quantity=quantity,
            price=price, time=self.current_bar.timestamp,
            commission=commission, tag=tag,
        ))

    def sell(self, symbol: str, quantity: int, price: Optional[float] = None,
             tag: str = ""):
        """卖出"""
        if not self.current_bar:
            return
        if self.position.quantity < quantity:
            quantity = self.position.quantity
        if quantity <= 0:
            return

        if price is None:
            price = self.current_bar.close * (1 - self.slippage)

        revenue = quantity * price
        commission = revenue * self.commission
        total_revenue = revenue - commission

        # 计算 PnL
        cost_basis = quantity * self.position.avg_cost
        pnl = total_revenue - cost_basis

        self.cash += total_revenue
        self.position.quantity -= quantity

        self.trades.append(Trade(
            symbol=symbol, side="sell", quantity=quantity,
            price=price, time=self.current_bar.timestamp,
            commission=commission, pnl=pnl, tag=tag,
        ))

    def close_position(self, symbol: str, tag: str = ""):
        """平仓"""
        symbol_position = self.position.symbol
        if self.position.quantity > 0:
            self.sell(symbol=symbol_position, quantity=self.position.quantity, tag=tag)

    def get_position(self, symbol: str) -> int:
        """获取持仓数量"""
        return self.position.quantity

    def _validate_data(self):
        if self.data.empty:
            raise ValueError("数据为空")
        required = ["open", "high", "low", "close"]
        for col in required:
            if col not in self.data.columns:
                raise ValueError(f"缺少必需列: {col}")

    def _add_indicators(self):
        """预处理技术指标"""
        from backend.crawlers.data_cleaner import USDataCleaner
        self.data = USDataCleaner.add_technical_indicators(self.data)

    def _iter_bars(self):
        """迭代K线"""
        bars = []
        for _, row in self.data.iterrows():
            if "date" in row or "Date" in row:
                ts = pd.to_datetime(row.get("date") or row.get("Date"))
            elif "timestamp" in row or "Timestamp" in row:
                ts = pd.to_datetime(row.get("timestamp") or row.get("Timestamp"))
            else:
                continue

            bar = Bar(
                symbol=self.symbol,
                timestamp=ts.to_pydatetime(),
                open=float(row.get("open", 0)),
                high=float(row.get("high", 0)),
                low=float(row.get("low", 0)),
                close=float(row.get("close", 0)),
                volume=float(row.get("volume", 0)),
                adjusted_close=float(row.get("adjusted_close", row.get("close", 0))),
                indicators={
                    k: float(v) for k, v in row.items()
                    if k in ["sma_20", "sma_50", "sma_200", "ema_12", "ema_26",
                             "macd", "macd_signal", "macd_hist", "rsi_14",
                             "bb_upper", "bb_middle", "bb_lower", "atr_14",
                             "volume_sma_20"]
                    and pd.notna(v)
                },
            )
            bars.append(bar)
        return bars

    def _generate_result(self) -> BacktestResult:
        """生成回测结果"""
        equity = np.array(self.equity_curve)
        if len(equity) == 0:
            return BacktestResult(status="failed", error_message="无交易数据")

        returns = np.diff(equity) / equity[:-1]
        self.end_cash = self.cash + self.position.market_value

        metrics = calculate_metrics(equity, returns, self.initial_cash, len(self.equity_curve))
        metrics["total_trades"] = len(self.trades)
        metrics["equity_curve"] = self.equity_curve
        metrics["trades"] = self.trades

        return BacktestResult(status="completed", **metrics)
