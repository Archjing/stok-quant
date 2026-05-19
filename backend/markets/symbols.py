"""
多市场股票代码规范化工具。

内部格式：
- US: AAPL
- CN: SH.600519 / SZ.000001 / BJ.835185
- HK: HK.00700
"""
from __future__ import annotations

import re

SUPPORTED_MARKETS = {"US", "CN", "HK"}
MARKET_CURRENCIES = {"US": "USD", "CN": "CNY", "HK": "HKD"}
CN_EXCHANGES = {"SH", "SZ", "BJ"}


class SymbolFormatError(ValueError):
    """股票代码格式错误。"""


def normalize_market(market: str | None) -> str:
    """标准化市场代码。"""
    normalized = (market or "US").strip().upper()
    if normalized not in SUPPORTED_MARKETS:
        raise SymbolFormatError(f"Unsupported market: {market}. Expected one of {sorted(SUPPORTED_MARKETS)}")
    return normalized


def get_currency(market: str | None) -> str:
    """获取市场默认货币。"""
    return MARKET_CURRENCIES[normalize_market(market)]


def detect_market(symbol: str) -> str:
    """根据代码形态粗略识别市场。"""
    raw = _compact(symbol)
    if raw.startswith("HK"):
        return "HK"
    if raw.startswith(("SH", "SZ", "BJ")):
        return "CN"
    if raw.isdigit():
        return "HK" if len(raw) <= 5 else "CN"
    return "US"


def normalize_symbol(symbol: str, market: str | None = None) -> str:
    """按指定市场标准化股票代码。"""
    market_code = normalize_market(market or detect_market(symbol))
    if market_code == "US":
        return normalize_us_symbol(symbol)
    if market_code == "CN":
        return normalize_cn_symbol(symbol)
    if market_code == "HK":
        return normalize_hk_symbol(symbol)
    raise SymbolFormatError(f"Unsupported market: {market}")


def normalize_us_symbol(symbol: str) -> str:
    """标准化美股代码。"""
    raw = _compact(symbol).replace("US", "", 1) if _compact(symbol).startswith("US") else _compact(symbol)
    if not raw:
        raise SymbolFormatError("Empty US symbol")
    return raw.upper()


def normalize_cn_symbol(symbol: str) -> str:
    """标准化 A 股代码为 SH.xxxxxx / SZ.xxxxxx / BJ.xxxxxx。"""
    raw = _compact(symbol)
    match = re.fullmatch(r"(SH|SZ|BJ)?(\d{6})", raw)
    if not match:
        raise SymbolFormatError(f"Invalid CN symbol: {symbol}")
    exchange = match.group(1) or detect_cn_exchange(match.group(2))
    code = match.group(2)
    return f"{exchange}.{code}"


def normalize_hk_symbol(symbol: str) -> str:
    """标准化港股代码为 HK.xxxxx。"""
    raw = _compact(symbol)
    if raw.startswith("HK"):
        raw = raw[2:]
    if not raw.isdigit() or len(raw) > 5:
        raise SymbolFormatError(f"Invalid HK symbol: {symbol}")
    return f"HK.{raw.zfill(5)}"


def detect_exchange(symbol: str, market: str | None = None) -> str | None:
    """识别交易所。"""
    market_code = normalize_market(market or detect_market(symbol))
    normalized = normalize_symbol(symbol, market_code)
    if market_code == "CN":
        return normalized.split(".", 1)[0]
    if market_code == "HK":
        return "HKEX"
    return None


def detect_cn_exchange(code: str) -> str:
    """根据 6 位 A 股代码推断交易所。"""
    if code.startswith(("600", "601", "603", "605", "688", "689", "900")):
        return "SH"
    if code.startswith(("000", "001", "002", "003", "200", "300", "301")):
        return "SZ"
    if code.startswith(("4", "8", "9")):
        return "BJ"
    # 保守 fallback：未知 6 位代码按沪市处理，避免误判为港股。
    return "SH"


def to_source_symbol(symbol: str, market: str | None = None) -> str:
    """转换为数据源常用代码。"""
    market_code = normalize_market(market or detect_market(symbol))
    normalized = normalize_symbol(symbol, market_code)
    if market_code == "CN":
        return normalized.split(".", 1)[1]
    if market_code == "HK":
        return normalized.split(".", 1)[1]
    return normalized


def _compact(symbol: str) -> str:
    """移除常见分隔符并转大写。"""
    if symbol is None:
        raise SymbolFormatError("Symbol cannot be None")
    return str(symbol).strip().upper().replace(".", "").replace("-", "")
