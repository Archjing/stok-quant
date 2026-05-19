"""Tests for market-aware API response shapes."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.market import MarketDailyBar


def _seed_market_daily_rows(market: str, symbol: str, days: int = 40) -> None:
    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        for index in range(days):
            current = date.today() - timedelta(days=days - index)
            existing = (
                db.query(MarketDailyBar)
                .filter_by(market=market, symbol=symbol, date=current)
                .first()
            )
            if existing:
                continue
            price = 100 + index
            db.add(
                MarketDailyBar(
                    market=market,
                    symbol=symbol,
                    date=current,
                    open=price,
                    high=price + 1,
                    low=price - 1,
                    close=price + 0.5,
                    volume=1000 + index,
                    adjusted_close=price + 0.5,
                )
            )
        db.commit()
    finally:
        db.close()


def test_stocks_list_cn_response_shape() -> None:
    client = TestClient(app)
    response = client.get("/api/stocks/", params={"market": "CN", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["market"] == "CN"
    assert payload["currency"] == "CNY"
    assert "total" in payload
    assert isinstance(payload["data"], list)


def test_kline_cn_daily_response_shape_from_db() -> None:
    _seed_market_daily_rows("CN", "SH.600519")
    client = TestClient(app)
    response = client.get(
        "/api/stocks/SH.600519/kline",
        params={"market": "CN", "period": "daily", "years": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["market"] == "CN"
    assert payload["currency"] == "CNY"
    assert payload["symbol"] == "SH.600519"
    assert payload["period"] == "daily"
    assert payload["source"] == "db"
    assert payload["data"]
    assert set(payload["data"][0].keys()) == {"x", "y"}
    assert len(payload["data"][0]["y"]) == 4


def test_backtest_status_hk_missing_response_shape() -> None:
    client = TestClient(app)
    response = client.get("/api/backtest/status/HK.00700", params={"market": "HK"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["market"] == "HK"
    assert payload["currency"] == "HKD"
    assert payload["symbol"] == "HK.00700"
    assert payload["status"] in {"available", "missing", "syncing", "error"}


def test_backfill_indicators_cn_endpoint_rejects_us() -> None:
    client = TestClient(app)
    response = client.post("/api/data/backfill-indicators", params={"market": "US"})

    assert response.status_code == 400
    assert "仅支持 CN/HK" in response.json()["detail"]
