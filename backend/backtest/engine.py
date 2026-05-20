"""
回测引擎核心 - 事件驱动回测框架
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backend.backtest.market_config import MarketBacktestConfig, get_market_backtest_config
from backend.backtest.metrics import calculate_metrics
from backend.backtest.strategies import Strategy

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """订单"""

    symbol: str
    quantity: int
    order_type: str = "market"
    side: str = "buy"
    price: Optional[float] = None
    status: str = "pending"
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
    last_buy_time: Optional[datetime] = None

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
    prev_close: Optional[float] = None
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
    market_rules: Dict[str, Any] = field(default_factory=dict)
    rejected_signals: List[Dict[str, Any]] = field(default_factory=list)
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
        market: str = "US",
        market_config: Optional[MarketBacktestConfig] = None,
    ):
        self.data = data
        self.strategy_class = strategy_class
        self.symbol = symbol
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.market = market
        self.market_config = market_config or get_market_backtest_config(market)

        self.cash = initial_cash
        self.position = Position(symbol=symbol)
        self.equity_curve: List[float] = []
        self.trades: List[Trade] = []
        self.rejected_signals: List[Dict[str, Any]] = []
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

            for bar in self._iter_bars():
                self.current_bar = bar
                self.position.current_price = bar.close

                try:
                    self.strategy.on_bar(bar)
                except Exception as exc:
                    logger.error("策略 on_bar 异常: %s", exc)
                    continue

            equity = self.cash + self.position.market_value
            self.equity_curve.append(equity)

            self.strategy.on_stop()
            return self._generate_result()
        except Exception as exc:
            logger.exception("回测运行失败")
            return BacktestResult(status="failed", error_message=str(exc))

    def buy(self, symbol: str, quantity: int, price: Optional[float] = None, tag: str = ""):
        """买入"""
        if not self.current_bar:
            return

        quantity = self._normalize_buy_quantity(quantity)
        if quantity <= 0:
            self._record_rejected_signal("buy", symbol, quantity, "invalid_quantity", tag)
            return
        if self._is_price_limit_buy_blocked():
            logger.debug("涨跌停限制生效，A 股涨停一字板当日不可买入")
            self._record_rejected_signal("buy", symbol, quantity, "price_limit_up_locked", tag)
            return

        if price is None:
            price = self.current_bar.close * (1 + self.slippage)
        price = self._normalize_execution_price("buy", price)

        cost = quantity * price
        commission = cost * self.commission
        total_cost = cost + commission
        if total_cost > self.cash:
            logger.debug("现金不足: 需要 %.2f, 可用 %.2f", total_cost, self.cash)
            self._record_rejected_signal("buy", symbol, quantity, "insufficient_cash", tag)
            return

        self.cash -= total_cost
        prev_cost = self.position.avg_cost * self.position.quantity
        self.position.quantity += quantity
        self.position.avg_cost = (prev_cost + cost) / self.position.quantity
        self.position.last_buy_time = self.current_bar.timestamp

        self.trades.append(
            Trade(
                symbol=symbol,
                side="buy",
                quantity=quantity,
                price=price,
                time=self.current_bar.timestamp,
                commission=commission,
                tag=tag,
            )
        )

    def sell(self, symbol: str, quantity: int, price: Optional[float] = None, tag: str = ""):
        """卖出"""
        if not self.current_bar:
            return

        if self.position.quantity < quantity:
            quantity = self.position.quantity
        quantity = self._normalize_sell_quantity(quantity)
        if quantity <= 0:
            self._record_rejected_signal("sell", symbol, quantity, "invalid_quantity", tag)
            return
        if self._is_t_plus_one_blocked():
            logger.debug("T+1 限制生效，当日买入仓位不可卖出")
            self._record_rejected_signal("sell", symbol, quantity, "t_plus_one", tag)
            return
        if self._is_price_limit_sell_blocked():
            logger.debug("涨跌停限制生效，A 股跌停一字板当日不可卖出")
            self._record_rejected_signal("sell", symbol, quantity, "price_limit_down_locked", tag)
            return

        if price is None:
            price = self.current_bar.close * (1 - self.slippage)
        price = self._normalize_execution_price("sell", price)

        revenue = quantity * price
        commission = revenue * self.commission
        stamp_duty = 0.0
        if self.market_config.stamp_tax_sell or self.market_config.stamp_duty_rate > 0:
            stamp_duty = revenue * self.market_config.stamp_duty_rate
        total_revenue = revenue - commission - stamp_duty

        cost_basis = quantity * self.position.avg_cost
        pnl = total_revenue - cost_basis

        self.cash += total_revenue
        self.position.quantity -= quantity
        if self.position.quantity == 0:
            self.position.avg_cost = 0.0
            self.position.last_buy_time = None

        self.trades.append(
            Trade(
                symbol=symbol,
                side="sell",
                quantity=quantity,
                price=price,
                time=self.current_bar.timestamp,
                commission=commission + stamp_duty,
                pnl=pnl,
                tag=tag,
            )
        )


    def close_position(self, symbol: str, tag: str = ""):
        """平仓"""
        if self.position.quantity > 0:
            self.sell(symbol=self.position.symbol, quantity=self.position.quantity, tag=tag)

    def get_position(self, symbol: str) -> int:
        """获取持仓数量"""
        return self.position.quantity

    def _normalize_buy_quantity(self, quantity: int) -> int:
        lot_size = self.market_config.lot_size
        if quantity <= 0:
            return 0
        if not lot_size or lot_size <= 1:
            return quantity
        return (quantity // lot_size) * lot_size

    def _normalize_sell_quantity(self, quantity: int) -> int:
        lot_size = self.market_config.lot_size
        if quantity <= 0:
            return 0
        if not lot_size or lot_size <= 1:
            return quantity
        if quantity == self.position.quantity:
            return quantity
        return (quantity // lot_size) * lot_size

    def _is_t_plus_one_blocked(self) -> bool:
        if not self.market_config.t_plus_one or not self.current_bar or not self.position.last_buy_time:
            return False
        return self.position.last_buy_time.date() >= self.current_bar.timestamp.date()

    def _record_rejected_signal(self, side: str, symbol: str, quantity: int, reason: str, tag: str = "") -> None:
        if not self.current_bar:
            return
        self.rejected_signals.append(
            {
                "time": self.current_bar.timestamp,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "reason": reason,
                "tag": tag,
            }
        )

    def _price_limit_bounds(self) -> tuple[Optional[float], Optional[float]]:
        if not self.current_bar or not self.market_config.price_limit:
            return None, None
        if not self.current_bar.prev_close or self.current_bar.prev_close <= 0:
            return None, None

        pct = float(self.market_config.price_limit_pct or 0)
        prev_close = float(self.current_bar.prev_close)
        limit_up = prev_close * (1 + pct)
        limit_down = prev_close * (1 - pct)
        return limit_up, limit_down

    def _normalize_execution_price(self, side: str, price: float) -> float:
        limit_up, limit_down = self._price_limit_bounds()
        if side == "buy" and limit_up is not None:
            return min(price, limit_up)
        if side == "sell" and limit_down is not None:
            return max(price, limit_down)
        return price

    def _is_price_limit_buy_blocked(self) -> bool:
        if not self.current_bar or not self.market_config.price_limit:
            return False

        limit_up, _ = self._price_limit_bounds()
        if limit_up is None:
            return False

        eps = max(abs(limit_up) * 1e-6, 1e-8)
        return self.current_bar.low >= limit_up - eps and self.current_bar.close >= limit_up - eps

    def _is_price_limit_sell_blocked(self) -> bool:
        if not self.current_bar or not self.market_config.price_limit:
            return False

        _, limit_down = self._price_limit_bounds()
        if limit_down is None:
            return False

        eps = max(abs(limit_down) * 1e-6, 1e-8)
        return self.current_bar.high <= limit_down + eps and self.current_bar.close <= limit_down + eps


    def _validate_data(self):

        if self.data.empty:
            raise ValueError("数据为空")
        for col in ["open", "high", "low", "close"]:
            if col not in self.data.columns:
                raise ValueError(f"缺少必需列: {col}")

    def _add_indicators(self):
        """预处理技术指标"""
        from backend.crawlers.data_cleaner import USDataCleaner

        self.data = USDataCleaner.add_technical_indicators(self.data)

    def _iter_bars(self):
        """迭代K线"""
        bars = []
        prev_close: Optional[float] = None
        for _, row in self.data.iterrows():
            if "date" in row or "Date" in row:
                ts = pd.to_datetime(row.get("date") or row.get("Date"))
            elif "timestamp" in row or "Timestamp" in row:
                ts = pd.to_datetime(row.get("timestamp") or row.get("Timestamp"))
            else:
                continue

            close = float(row.get("close", 0))
            bar = Bar(
                symbol=self.symbol,
                timestamp=ts.to_pydatetime(),
                open=float(row.get("open", 0)),
                high=float(row.get("high", 0)),
                low=float(row.get("low", 0)),
                close=close,
                volume=float(row.get("volume", 0)),
                adjusted_close=float(row.get("adjusted_close", row.get("close", 0))),
                prev_close=prev_close,
                indicators={
                    k: float(v)
                    for k, v in row.items()
                    if k in [
                        "sma_20",
                        "sma_50",
                        "sma_200",
                        "ema_12",
                        "ema_26",
                        "macd",
                        "macd_signal",
                        "macd_hist",
                        "rsi_14",
                        "bb_upper",
                        "bb_middle",
                        "bb_lower",
                        "atr_14",
                        "volume_sma_20",
                    ]
                    and pd.notna(v)
                },
            )
            bars.append(bar)
            prev_close = close
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
        metrics["market_rules"] = self.market_config.to_dict()
        metrics["rejected_signals"] = self.rejected_signals

        return BacktestResult(status="completed", **metrics)



