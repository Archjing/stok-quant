"""Tests for backtest compare endpoint response shape and completeness."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.stock import USStockDaily


def _seed_us_daily_rows(symbol: str, days: int = 260) -> None:
    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        for index in range(days):
            current = date.today() - timedelta(days=days - index)
            existing = (
                db.query(USStockDaily)
                .filter_by(symbol=symbol, date=current)
                .first()
            )
            if existing:
                continue
            price = 100 + index * 0.2
            db.add(
                USStockDaily(
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


def test_backtest_compare_returns_all_registered_strategies() -> None:
    _seed_us_daily_rows("AAPL")
    client = TestClient(app)

    response = client.post(
        "/api/backtest/compare",
        params={"symbol": "AAPL", "years": 1, "market": "US"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["market"] == "US"
    assert payload["currency"] == "USD"
    assert payload["symbol"] == "AAPL"
    assert "strategies" in payload
    assert set(payload["strategies"].keys()) == {
        "sma_crossover",
        "rsi_mean_reversion",
        "macd",
        "buy_and_hold",
    }
