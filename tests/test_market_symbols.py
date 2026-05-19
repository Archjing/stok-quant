"""Tests for multi-market symbol normalization utilities."""

import pytest

from backend.markets.symbols import (
    SymbolFormatError,
    detect_exchange,
    detect_market,
    get_currency,
    normalize_market,
    normalize_symbol,
    to_source_symbol,
)


def test_normalize_us_symbol() -> None:
    assert normalize_symbol("aapl", "US") == "AAPL"
    assert normalize_symbol(" AAPL ", "US") == "AAPL"
    assert detect_market("AAPL") == "US"
    assert get_currency("US") == "USD"


def test_normalize_cn_symbol_with_exchange_prefixes() -> None:
    assert normalize_symbol("600519", "CN") == "SH.600519"
    assert normalize_symbol("SH600519", "CN") == "SH.600519"
    assert normalize_symbol("SH.600519", "CN") == "SH.600519"
    assert normalize_symbol("000001", "CN") == "SZ.000001"
    assert normalize_symbol("SZ000001", "CN") == "SZ.000001"
    assert normalize_symbol("835185", "CN") == "BJ.835185"
    assert normalize_symbol("BJ.835185", "CN") == "BJ.835185"
    assert detect_exchange("SH.600519", "CN") == "SH"
    assert to_source_symbol("SZ.000001", "CN") == "000001"
    assert get_currency("CN") == "CNY"


def test_normalize_hk_symbol_preserves_leading_zeroes() -> None:
    assert normalize_symbol("700", "HK") == "HK.00700"
    assert normalize_symbol("00700", "HK") == "HK.00700"
    assert normalize_symbol("HK700", "HK") == "HK.00700"
    assert normalize_symbol("HK.700", "HK") == "HK.00700"
    assert normalize_symbol("HK.00700", "HK") == "HK.00700"
    assert detect_exchange("HK.00700", "HK") == "HKEX"
    assert to_source_symbol("HK.00700", "HK") == "00700"
    assert get_currency("HK") == "HKD"


def test_detect_market_heuristics() -> None:
    assert detect_market("HK.00700") == "HK"
    assert detect_market("SH.600519") == "CN"
    assert detect_market("SZ000001") == "CN"
    assert detect_market("700") == "HK"
    assert detect_market("600519") == "CN"


def test_invalid_market_and_symbols_raise() -> None:
    with pytest.raises(SymbolFormatError):
        normalize_market("EU")
    with pytest.raises(SymbolFormatError):
        normalize_symbol("ABC123", "CN")
    with pytest.raises(SymbolFormatError):
        normalize_symbol("123456", "HK")
