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
