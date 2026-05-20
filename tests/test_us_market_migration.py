"""Tests for US legacy -> generic market table migration."""

from __future__ import annotations

from datetime import date, datetime

from backend.data_manager import DataSyncStatus
from backend.database import SessionLocal, init_db
from backend.models.market import MarketDailyBar, MarketStock, MarketSyncStatus
from backend.models.stock import USStock, USStockDaily
from scripts.migrate_us_to_market_tables import migrate_us_to_market_tables


def _clear_test_tables() -> None:
    db = SessionLocal()
    try:
        db.query(MarketDailyBar).filter(MarketDailyBar.market == "US").delete()
        db.query(MarketStock).filter(MarketStock.market == "US").delete()
        db.query(MarketSyncStatus).filter(MarketSyncStatus.market == "US").delete()
        db.query(USStockDaily).filter(USStockDaily.symbol.in_(["AAPL", "MSFT"])) .delete(synchronize_session=False)
        db.query(USStock).filter(USStock.symbol.in_(["AAPL", "MSFT"])) .delete(synchronize_session=False)
        db.query(DataSyncStatus).filter(DataSyncStatus.symbol.in_(["AAPL", "MSFT"])) .delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _seed_legacy_us_rows() -> None:
    db = SessionLocal()
    try:
        db.add(
            USStock(
                symbol="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                sector="Technology",
                industry="Consumer Electronics",
                market_cap=3000000000000.0,
                country="US",
                currency="USD",
                price=210.5,
                pe_ratio=31.2,
                pb_ratio=45.8,
                dividend_yield=0.45,
            )
        )
        db.add(
            USStockDaily(
                symbol="AAPL",
                date=date(2024, 1, 2),
                open=100.0,
                high=110.0,
                low=99.0,
                close=108.0,
                volume=1000000,
                adjusted_close=108.0,
                sma_20=101.0,
                sma_50=98.0,
                sma_200=90.0,
                ema_12=104.0,
                ema_26=102.0,
                macd=2.0,
                macd_signal=1.5,
                macd_hist=0.5,
                rsi_14=60.0,
                bb_upper=112.0,
                bb_middle=105.0,
                bb_lower=98.0,
                atr_14=3.0,
                volume_sma_20=900000.0,
            )
        )
        db.add(
            DataSyncStatus(
                symbol="AAPL",
                last_sync_date=date(2024, 1, 2),
                last_sync_time=datetime(2024, 1, 2, 15, 30, 0),
                total_rows=1,
                status="completed",
                error_message=None,
                retry_count=0,
            )
        )
        db.commit()
    finally:
        db.close()


def test_us_market_migration_copies_legacy_rows_to_generic_tables() -> None:
    init_db()
    _clear_test_tables()
    _seed_legacy_us_rows()

    stats = migrate_us_to_market_tables()

    assert stats["market"] == "US"
    assert stats["stocks_seen"] >= 1
    assert stats["daily_rows_seen"] >= 1
    assert stats["sync_rows_seen"] >= 1
    assert stats["stocks_inserted"] >= 1
    assert stats["daily_rows_inserted"] >= 1
    assert stats["sync_rows_inserted"] >= 1

    db = SessionLocal()
    try:
        stock = db.query(MarketStock).filter_by(market="US", symbol="AAPL").first()
        assert stock is not None
        assert stock.raw_symbol == "AAPL"
        assert stock.name == "Apple Inc."
        assert stock.exchange == "NASDAQ"
        assert stock.currency == "USD"
        assert stock.market_cap == 3000000000000.0
        assert stock.pe_ratio == 31.2

        bar = db.query(MarketDailyBar).filter_by(market="US", symbol="AAPL", date=date(2024, 1, 2)).first()
        assert bar is not None
        assert bar.close == 108.0
        assert bar.adjusted_close == 108.0
        assert bar.amount is None
        assert bar.sma_20 == 101.0
        assert bar.macd_hist == 0.5

        sync = db.query(MarketSyncStatus).filter_by(market="US", symbol="AAPL").first()
        assert sync is not None
        assert sync.last_sync_date == date(2024, 1, 2)
        assert sync.total_rows == 1
        assert sync.status == "completed"
    finally:
        db.close()


def test_us_market_migration_is_idempotent_and_updates_existing_rows() -> None:
    init_db()
    _clear_test_tables()
    _seed_legacy_us_rows()

    first = migrate_us_to_market_tables()
    second = migrate_us_to_market_tables()

    assert first["stocks_inserted"] >= 1
    assert second["stocks_updated"] >= 1
    assert second["daily_rows_updated"] >= 1
    assert second["sync_rows_updated"] >= 1

    db = SessionLocal()
    try:
        assert db.query(MarketStock).filter_by(market="US", symbol="AAPL").count() == 1
        assert db.query(MarketDailyBar).filter_by(market="US", symbol="AAPL").count() == 1
        assert db.query(MarketSyncStatus).filter_by(market="US", symbol="AAPL").count() == 1
    finally:
        db.close()


def test_us_market_migration_dry_run_does_not_commit() -> None:
    init_db()
    _clear_test_tables()
    _seed_legacy_us_rows()

    stats = migrate_us_to_market_tables(dry_run=True)

    assert stats["dry_run"] is True
    assert stats["stocks_seen"] >= 1
    assert stats["daily_rows_seen"] >= 1
    assert stats["sync_rows_seen"] >= 1

    db = SessionLocal()
    try:
        assert db.query(MarketStock).filter_by(market="US", symbol="AAPL").first() is None
        assert db.query(MarketDailyBar).filter_by(market="US", symbol="AAPL").first() is None
        assert db.query(MarketSyncStatus).filter_by(market="US", symbol="AAPL").first() is None
    finally:
        db.close()
