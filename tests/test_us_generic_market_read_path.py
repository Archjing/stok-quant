"""Tests for US generic market-table read path migration."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from backend.database import SessionLocal, init_db
from backend.main import app
from backend.models.market import MarketDailyBar, MarketStock, MarketSyncStatus


client = TestClient(app)


def _clear_us_market_rows() -> None:
    db = SessionLocal()
    try:
        db.query(MarketDailyBar).filter(MarketDailyBar.market == "US").delete()
        db.query(MarketStock).filter(MarketStock.market == "US").delete()
        db.query(MarketSyncStatus).filter(MarketSyncStatus.market == "US").delete()
        db.commit()
    finally:
        db.close()


def _seed_us_market_rows(symbol: str = "AAPL", days: int = 260) -> None:
    db = SessionLocal()
    try:
        db.add(
            MarketStock(
                market="US",
                symbol=symbol,
                raw_symbol=symbol,
                name="Apple Inc.",
                exchange="NASDAQ",
                sector="Technology",
                country="US",
                currency="USD",
                price=210.5,
                market_cap=3000000000000.0,
                pe_ratio=31.2,
            )
        )
        start = date.today() - timedelta(days=days)
        for index in range(days):
            current = start + timedelta(days=index)
            price = 100 + index * 0.1
            db.add(
                MarketDailyBar(
                    market="US",
                    symbol=symbol,
                    date=current,
                    open=price,
                    high=price + 1,
                    low=price - 1,
                    close=price + 0.5,
                    volume=1000 + index,
                    adjusted_close=price + 0.5,
                    sma_20=price,
                    sma_50=price,
                    sma_200=price,
                )
            )
        db.add(
            MarketSyncStatus(
                market="US",
                symbol=symbol,
                last_sync_date=date.today(),
                last_sync_time=datetime.now(),
                total_rows=days,
                status="completed",
                error_message=None,
                retry_count=0,
            )
        )
        db.commit()
    finally:
        db.close()


def test_us_stocks_list_reads_from_market_tables() -> None:
    init_db()
    _clear_us_market_rows()
    _seed_us_market_rows()

    response = client.get("/api/stocks/", params={"market": "US", "search": "AAPL"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["market"] == "US"
    assert payload["currency"] == "USD"
    assert payload["total"] >= 1
    assert any(item["symbol"] == "AAPL" for item in payload["data"])


def test_us_daily_and_kline_read_from_market_tables() -> None:
    init_db()
    _clear_us_market_rows()
    _seed_us_market_rows()

    daily = client.get("/api/stocks/AAPL/daily", params={"market": "US", "years": 1})
    assert daily.status_code == 200
    daily_payload = daily.json()
    assert daily_payload["market"] == "US"
    assert daily_payload["symbol"] == "AAPL"
    assert daily_payload["source"] == "db"
    assert daily_payload["total"] > 20

    kline = client.get("/api/stocks/AAPL/kline", params={"market": "US", "period": "daily", "years": 1})
    assert kline.status_code == 200
    kline_payload = kline.json()
    assert kline_payload["market"] == "US"
    assert kline_payload["symbol"] == "AAPL"
    assert kline_payload["period"] == "daily"
    assert kline_payload["source"] == "db"
    assert len(kline_payload["data"]) > 20


def test_us_backtest_and_data_status_read_from_market_tables() -> None:
    init_db()
    _clear_us_market_rows()
    _seed_us_market_rows()

    backtest_status = client.get("/api/backtest/status/AAPL", params={"market": "US"})
    assert backtest_status.status_code == 200
    status_payload = backtest_status.json()
    assert status_payload["market"] == "US"
    assert status_payload["status"] == "available"
    assert status_payload["rows"] > 20

    data_status = client.get("/api/data/status", params={"market": "US"})
    assert data_status.status_code == 200
    data_payload = data_status.json()
    assert data_payload["market"] == "US"
    assert isinstance(data_payload["stocks"], list)
    assert any(item["symbol"] == "AAPL" for item in data_payload["stocks"])

    compare = client.post("/api/backtest/compare", params={"market": "US", "symbol": "AAPL", "years": 1})
    assert compare.status_code == 200
    compare_payload = compare.json()
    assert compare_payload["market"] == "US"
    assert compare_payload["symbol"] == "AAPL"
    assert set(compare_payload["strategies"].keys()) == {
        "sma_crossover",
        "rsi_mean_reversion",
        "macd",
        "buy_and_hold",
    }
