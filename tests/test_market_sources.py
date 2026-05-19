"""Tests for CN/HK market source normalization without network calls."""

from datetime import date

import pandas as pd

from backend.markets.cn import CNMarketSource
from backend.markets.hk import HKMarketSource


def test_cn_source_sample_pool_contains_standard_symbols() -> None:
    source = CNMarketSource()
    stocks = source._sample_stock_list()
    symbols = {item["symbol"] for item in stocks}
    assert "SH.600519" in symbols
    assert "SH.600211" in symbols
    assert "SZ.000001" in symbols
    assert "BJ.835185" in symbols
    xizang = next(item for item in stocks if item["symbol"] == "SH.600211")
    assert xizang["name"] == "西藏药业"
    assert xizang["raw_symbol"] == "600211"
    assert all(item["currency"] == "CNY" for item in stocks)


def test_cn_daily_dataframe_normalization() -> None:
    source = CNMarketSource()
    raw = pd.DataFrame(
        {
            "日期": pd.date_range("2024-01-01", periods=40, freq="D"),
            "开盘": range(100, 140),
            "最高": range(101, 141),
            "最低": range(99, 139),
            "收盘": range(100, 140),
            "成交量": range(1000, 1040),
            "成交额": range(100000, 100040),
            "涨跌幅": [0.1] * 40,
            "换手率": [1.2] * 40,
        }
    )

    df = source.normalize_daily_dataframe(raw)

    assert not df.empty
    assert {"date", "open", "high", "low", "close", "volume", "amount", "adjusted_close"}.issubset(df.columns)
    assert {"sma_20", "ema_12", "macd", "rsi_14", "bb_upper", "atr_14"}.issubset(df.columns)
    assert df["date"].iloc[0] == date(2024, 1, 1)
    assert df["adjusted_close"].iloc[-1] == df["close"].iloc[-1]


def test_hk_source_sample_pool_preserves_five_digit_codes() -> None:
    source = HKMarketSource()
    stocks = source._sample_stock_list()
    symbols = {item["symbol"] for item in stocks}
    assert "HK.00700" in symbols
    assert "HK.00005" in symbols
    assert "HK.00388" in symbols
    assert all(item["raw_symbol"] and len(item["raw_symbol"]) == 5 for item in stocks)
    assert all(item["currency"] == "HKD" for item in stocks)


def test_hk_daily_dataframe_normalization() -> None:
    source = HKMarketSource()
    raw = pd.DataFrame(
        {
            "日期": pd.date_range("2024-01-01", periods=40, freq="D"),
            "开盘": [10 + i * 0.1 for i in range(40)],
            "最高": [10.5 + i * 0.1 for i in range(40)],
            "最低": [9.8 + i * 0.1 for i in range(40)],
            "收盘": [10.2 + i * 0.1 for i in range(40)],
            "成交量": range(2000, 2040),
            "成交额": range(200000, 200040),
        }
    )

    df = source.normalize_daily_dataframe(raw)

    assert not df.empty
    assert {"date", "open", "high", "low", "close", "volume", "amount", "adjusted_close"}.issubset(df.columns)
    assert {"sma_20", "ema_12", "macd", "rsi_14", "bb_upper", "atr_14"}.issubset(df.columns)
    assert df["date"].iloc[0] == date(2024, 1, 1)
    assert df["adjusted_close"].iloc[-1] == df["close"].iloc[-1]
