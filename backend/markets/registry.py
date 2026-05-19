"""市场数据源注册表。"""
from __future__ import annotations

from backend.markets.base import BaseMarketSource
from backend.markets.symbols import normalize_market


def get_market_source(market: str) -> BaseMarketSource:
    """获取指定市场数据源。CN/HK 源会延迟导入，避免无关依赖影响 US 启动。"""
    market_code = normalize_market(market)
    if market_code == "CN":
        from backend.markets.cn import CNMarketSource

        return CNMarketSource()
    if market_code == "HK":
        from backend.markets.hk import HKMarketSource

        return HKMarketSource()
    raise ValueError("US market currently uses the legacy DataManager path")
