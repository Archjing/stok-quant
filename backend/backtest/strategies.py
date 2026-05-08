"""
策略基类与内置策略
"""
from typing import Optional


class Strategy:
    """策略基类 - 用户继承此类实现自定义策略"""

    engine = None  # BacktestEngine 实例

    def on_start(self):
        """回测开始回调"""
        pass

    def on_bar(self, bar):
        """每根K线回调"""
        raise NotImplementedError

    def on_stop(self):
        """回测结束回调"""
        pass

    def buy(self, symbol: str, quantity: int, price: Optional[float] = None, tag: str = ""):
        """买入"""
        if self.engine:
            self.engine.buy(symbol, quantity, price, tag)

    def sell(self, symbol: str, quantity: int, price: Optional[float] = None, tag: str = ""):
        """卖出"""
        if self.engine:
            self.engine.sell(symbol, quantity, price, tag)

    def close_position(self, symbol: str, tag: str = ""):
        """平仓"""
        if self.engine:
            self.engine.close_position(symbol, tag)

    def get_position(self, symbol: str) -> int:
        """获取持仓数量"""
        return self.engine.get_position(symbol) if self.engine else 0

    def get_indicator(self, name: str, default: Optional[float] = None) -> Optional[float]:
        """获取当前K线的技术指标值"""
        if self.engine and self.engine.current_bar:
            return self.engine.current_bar.indicators.get(name, default)
        return default


# ============ 内置示例策略 ============

class SMACrossoverStrategy(Strategy):
    """双均线金叉死叉策略"""

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prev_fast = 0.0
        self.prev_slow = 0.0

    def on_bar(self, bar):
        fast_sma = self.get_indicator(f"sma_{self.fast_period}")
        slow_sma = self.get_indicator(f"sma_{self.slow_period}")
        if fast_sma is None or slow_sma is None:
            return

        # 金叉：快线上穿慢线
        if self.prev_fast <= self.prev_slow and fast_sma > slow_sma:
            self.close_position(bar.symbol)
            self.buy(bar.symbol, quantity=100, tag="golden_cross")

        # 死叉：快线下穿慢线
        elif self.prev_fast >= self.prev_slow and fast_sma < slow_sma:
            self.close_position(bar.symbol)
            if self.get_indicator("rsi_14", 50) > 30:
                self.sell(bar.symbol, quantity=100, tag="death_cross")

        self.prev_fast = fast_sma
        self.prev_slow = slow_sma


class RSIMeanReversionStrategy(Strategy):
    """RSI均值回归策略"""

    def __init__(self, oversold: int = 30, overbought: int = 70):
        self.oversold = oversold
        self.overbought = overbought

    def on_bar(self, bar):
        rsi = self.get_indicator("rsi_14")
        if rsi is None:
            return

        position = self.get_position(bar.symbol)

        if rsi < self.oversold and position == 0:
            self.buy(bar.symbol, quantity=100, tag="rsi_oversold")
        elif rsi > self.overbought and position > 0:
            self.close_position(bar.symbol, tag="rsi_overbought")


class MACDStrategy(Strategy):
    """MACD 趋势跟踪策略"""

    def __init__(self):
        self.prev_hist = 0.0

    def on_bar(self, bar):
        macd = self.get_indicator("macd")
        signal = self.get_indicator("macd_signal")
        hist = self.get_indicator("macd_hist")
        if None in (macd, signal, hist):
            return

        position = self.get_position(bar.symbol)

        # MACD上穿信号线 -> 买入
        if self.prev_hist <= 0 and hist > 0 and position == 0:
            self.buy(bar.symbol, quantity=100, tag="macd_buy")
        # MACD下穿信号线 -> 卖出
        elif self.prev_hist >= 0 and hist < 0 and position > 0:
            self.close_position(bar.symbol, tag="macd_sell")

        self.prev_hist = hist


class BuyAndHoldStrategy(Strategy):
    """买入并持有策略（基准）"""

    def __init__(self, quantity: int = 100):
        self.quantity = quantity

    def on_bar(self, bar):
        if self.get_position(bar.symbol) == 0:
            self.buy(bar.symbol, quantity=self.quantity, tag="buy_hold")
