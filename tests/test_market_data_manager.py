"""Tests for MarketDataManager conversion helpers and stock seeding."""

import pandas as pd

from backend.market_data_manager import MarketDataManager
from backend.markets.symbols import get_currency


def test_market_data_manager_seeds_cn_and_hk_stock_lists() -> None:
    mgr = MarketDataManager(request_delay=0)

    cn_stocks = mgr.get_stock_list("CN")
    hk_stocks = mgr.get_stock_list("HK")

    assert any(item["symbol"] == "SH.600519" for item in cn_stocks)
    assert any(item["symbol"] == "HK.00700" for item in hk_stocks)
    assert all(item["currency"] == get_currency(item["market"]) for item in cn_stocks + hk_stocks)


def test_market_data_manager_f_value_handles_missing_and_numeric_values() -> None:
    assert MarketDataManager._f_value(None) is None
    assert MarketDataManager._f_value("") is None
    assert MarketDataManager._f_value(float("nan")) is None
    assert MarketDataManager._f_value("12.34") == 12.34
    assert MarketDataManager._f_value("bad") is None


def test_market_data_manager_max_date_handles_timestamp_and_date_values() -> None:
    df = pd.DataFrame({"date": pd.to_datetime(["2024-01-01", "2024-01-03", "2024-01-02"])})
    assert str(MarketDataManager._max_date(df)) == "2024-01-03"

    empty_df = pd.DataFrame({"date": []})
    assert MarketDataManager._max_date(empty_df) is None
