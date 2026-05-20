"""Tests for market backtest rules and engine behavior."""

from datetime import datetime

import pandas as pd

from backend.backtest.engine import BacktestEngine
from backend.backtest.market_config import get_market_backtest_config
from backend.backtest.strategies import BuyAndHoldStrategy


class SameDayRoundTripStrategy:
    def on_start(self):
        self.did_buy = False

    def on_bar(self, bar):
        if not self.did_buy:
            self.engine.buy(bar.symbol, quantity=100, tag="buy_first")
            self.did_buy = True
        elif self.engine.get_position(bar.symbol) > 0:
            self.engine.sell(bar.symbol, quantity=100, tag="sell_attempt")

    def on_stop(self):
        pass


class BuyEveryBarStrategy:
    def on_start(self):
        pass

    def on_bar(self, bar):
        self.engine.buy(bar.symbol, quantity=100, tag="buy_every_bar")

    def on_stop(self):
        pass


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03"]),
            "open": [10.0, 10.2, 10.4],
            "high": [10.5, 10.6, 10.7],
            "low": [9.8, 10.0, 10.1],
            "close": [10.0, 10.2, 10.5],
            "volume": [1000, 1200, 1300],
            "adjusted_close": [10.0, 10.2, 10.5],
        }
    )


def test_get_market_backtest_config_cn() -> None:
    config = get_market_backtest_config("CN")

    assert config.market == "CN"
    assert config.currency == "CNY"
    assert config.lot_size == 100
    assert config.t_plus_one is True
    assert config.price_limit is True


def test_backtest_engine_cn_enforces_lot_size_round_down() -> None:
    engine = BacktestEngine(
        data=_sample_df(),
        strategy_class=BuyAndHoldStrategy,
        symbol="SH.600519",
        initial_cash=100000,
        market="CN",
        market_config=get_market_backtest_config("CN"),
    )

    engine.current_bar = engine._iter_bars()[0]
    engine.buy("SH.600519", quantity=150, tag="manual_buy")

    assert engine.position.quantity == 100
    assert engine.trades[-1].quantity == 100


def test_backtest_engine_cn_blocks_same_day_sell_with_t_plus_one() -> None:
    engine = BacktestEngine(
        data=_sample_df(),
        strategy_class=SameDayRoundTripStrategy,
        symbol="SH.600519",
        initial_cash=100000,
        market="CN",
        market_config=get_market_backtest_config("CN"),
    )

    result = engine.run()

    buy_trades = [t for t in result.trades if t.side == "buy"]
    sell_trades = [t for t in result.trades if t.side == "sell"]

    assert buy_trades
    assert len(sell_trades) == 1
    assert sell_trades[0].time.date() == datetime(2024, 1, 3).date()
    assert any(item["reason"] == "t_plus_one" for item in result.rejected_signals)


def test_backtest_engine_cn_blocks_limit_up_locked_buy() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [10.0, 11.0],
            "high": [10.2, 11.0],
            "low": [9.9, 11.0],
            "close": [10.0, 11.0],
            "volume": [1000, 800],
            "adjusted_close": [10.0, 11.0],
        }
    )

    engine = BacktestEngine(
        data=df,
        strategy_class=BuyEveryBarStrategy,
        symbol="SH.600519",
        initial_cash=100000,
        market="CN",
        market_config=get_market_backtest_config("CN"),
        slippage=0.02,
    )

    result = engine.run()

    buy_trades = [t for t in result.trades if t.side == "buy"]
    assert len(buy_trades) == 1
    assert buy_trades[0].time.date() == datetime(2024, 1, 2).date()
    assert any(item["reason"] == "price_limit_up_locked" for item in result.rejected_signals)


def test_backtest_engine_cn_blocks_limit_down_locked_sell() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [10.0, 9.0],
            "high": [10.2, 9.0],
            "low": [9.9, 9.0],
            "close": [10.0, 9.0],
            "volume": [1000, 1500],
            "adjusted_close": [10.0, 9.0],
        }
    )

    engine = BacktestEngine(
        data=df,
        strategy_class=BuyAndHoldStrategy,
        symbol="SH.600519",
        initial_cash=100000,
        market="CN",
        market_config=get_market_backtest_config("CN"),
        slippage=0.02,
    )

    bars = engine._iter_bars()
    engine.current_bar = bars[0]
    engine.buy("SH.600519", quantity=100, tag="manual_buy")
    engine.current_bar = bars[1]
    engine.position.current_price = bars[1].close
    engine.sell("SH.600519", quantity=100, tag="manual_sell")

    assert engine.position.quantity == 100
    assert any(item["reason"] == "price_limit_down_locked" for item in engine.rejected_signals)


def test_backtest_engine_cn_caps_buy_price_at_limit_up() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [10.0, 10.6],
            "high": [10.2, 11.0],
            "low": [9.9, 10.5],
            "close": [10.0, 10.8],
            "volume": [1000, 1200],
            "adjusted_close": [10.0, 10.8],
        }
    )

    engine = BacktestEngine(
        data=df,
        strategy_class=BuyAndHoldStrategy,
        symbol="SH.600519",
        initial_cash=100000,
        market="CN",
        market_config=get_market_backtest_config("CN"),
        slippage=0.05,
    )

    bars = engine._iter_bars()
    engine.current_bar = bars[1]
    engine.buy("SH.600519", quantity=100, tag="manual_buy")

    assert engine.trades[-1].price == 11.0


def test_backtest_engine_cn_floors_sell_price_at_limit_down() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [10.0, 9.4],
            "high": [10.2, 9.5],
            "low": [9.9, 9.0],
            "close": [10.0, 9.2],
            "volume": [1000, 1200],
            "adjusted_close": [10.0, 9.2],
        }
    )

    engine = BacktestEngine(
        data=df,
        strategy_class=BuyAndHoldStrategy,
        symbol="SH.600519",
        initial_cash=100000,
        market="CN",
        market_config=get_market_backtest_config("CN"),
        slippage=0.05,
    )

    bars = engine._iter_bars()
    engine.current_bar = bars[0]
    engine.buy("SH.600519", quantity=100, tag="manual_buy")
    engine.current_bar = bars[1]
    engine.position.current_price = bars[1].close
    engine.position.last_buy_time = datetime(2024, 1, 1)
    engine.sell("SH.600519", quantity=100, tag="manual_sell")

    assert engine.trades[-1].price == 9.0


def test_backtest_engine_result_contains_market_rules() -> None:
    result = BacktestEngine(
        data=_sample_df(),
        strategy_class=BuyAndHoldStrategy,
        symbol="HK.00700",
        initial_cash=100000,
        market="HK",
        market_config=get_market_backtest_config("HK"),
    ).run()

    assert result.market_rules["market"] == "HK"
    assert result.market_rules["currency"] == "HKD"
