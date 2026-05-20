"""
多市场回测规则配置。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from backend.markets.symbols import get_currency, normalize_market


@dataclass(frozen=True)
class MarketBacktestConfig:
    """市场回测规则配置。"""

    market: str
    currency: str
    lot_size: int | None = 1
    lot_size_overrides: dict[str, int] = field(default_factory=dict)
    t_plus_one: bool = False
    stamp_tax_sell: bool = False
    stamp_duty_rate: float = 0.0
    price_limit: bool = False
    price_limit_pct: float | None = None
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


MARKET_BACKTEST_CONFIGS: dict[str, MarketBacktestConfig] = {
    "US": MarketBacktestConfig(
        market="US",
        currency=get_currency("US"),
        lot_size=1,
        t_plus_one=False,
        stamp_tax_sell=False,
        stamp_duty_rate=0.0,
        price_limit=False,
        price_limit_pct=None,
        notes="US phase-1 defaults: unit lot, no T+1, no stamp duty simulation.",
    ),
    "CN": MarketBacktestConfig(
        market="CN",
        currency=get_currency("CN"),
        lot_size=100,
        t_plus_one=True,
        stamp_tax_sell=True,
        stamp_duty_rate=0.001,
        price_limit=True,
        price_limit_pct=0.10,
        notes="CN phase-2 rules: 100-share lot, T+1 sell restriction, sell-side stamp tax.",
    ),
    "HK": MarketBacktestConfig(
        market="HK",
        currency=get_currency("HK"),
        lot_size=None,
        lot_size_overrides={
            "HK.00700": 100,
            "HK.09988": 100,
            "HK.03690": 100,
            "HK.01810": 200,
            "HK.00005": 400,
            "HK.00941": 500,
            "HK.01299": 200,
            "HK.02318": 500,
            "HK.01398": 1000,
            "HK.03988": 1000,
            "HK.00883": 1000,
            "HK.00857": 2000,
            "HK.01024": 100,
            "HK.09618": 50,
            "HK.09888": 100,
            "HK.02020": 100,
            "HK.02331": 500,
            "HK.02269": 500,
            "HK.00669": 100,
            "HK.00388": 100,
        },
        t_plus_one=False,
        stamp_tax_sell=True,
        stamp_duty_rate=0.0013,
        price_limit=False,
        price_limit_pct=None,
        notes="HK phase-2 rules: board-lot mapping for major symbols, sell-side stamp duty enabled.",
    ),
}


def get_market_backtest_config(market: str) -> MarketBacktestConfig:
    """根据市场获取回测规则配置。"""
    market_code = normalize_market(market)
    return MARKET_BACKTEST_CONFIGS[market_code]
