"""US legacy-table to generic multi-market table migration script.

Phase 16.3 step 1:
- USStock -> MarketStock (market=US)
- USStockDaily -> MarketDailyBar (market=US)
- DataSyncStatus -> MarketSyncStatus (market=US)

The migration is designed to be idempotent and safe to re-run.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_manager import DataSyncStatus
from backend.database import SessionLocal, init_db
from backend.models.market import MarketDailyBar, MarketStock, MarketSyncStatus
from backend.models.stock import USStock, USStockDaily


@dataclass
class MigrationStats:
    market: str = "US"
    dry_run: bool = False
    symbols_filter: list[str] | None = None
    stocks_seen: int = 0
    stocks_inserted: int = 0
    stocks_updated: int = 0
    daily_rows_seen: int = 0
    daily_rows_inserted: int = 0
    daily_rows_updated: int = 0
    sync_rows_seen: int = 0
    sync_rows_inserted: int = 0
    sync_rows_updated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class USMarketTableMigrator:
    """Migrate legacy US tables into generic market tables."""

    MARKET = "US"

    def __init__(self, dry_run: bool = False, symbols: list[str] | None = None):
        self.dry_run = dry_run
        self.symbols = [sym.upper() for sym in symbols] if symbols else None
        self.stats = MigrationStats(dry_run=dry_run, symbols_filter=self.symbols)

    def run(self) -> dict[str, Any]:
        init_db()
        session = SessionLocal()
        try:
            self._migrate_stocks(session)
            self._migrate_daily_bars(session)
            self._migrate_sync_status(session)
            if self.dry_run:
                session.rollback()
            else:
                session.commit()
            return self.stats.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _migrate_stocks(self, session) -> None:
        query = session.query(USStock).order_by(USStock.symbol)
        if self.symbols:
            query = query.filter(USStock.symbol.in_(self.symbols))

        for row in query.all():
            self.stats.stocks_seen += 1
            existing = session.query(MarketStock).filter_by(market=self.MARKET, symbol=row.symbol).first()
            if existing:
                self._apply_stock(existing, row)
                self.stats.stocks_updated += 1
            else:
                incoming = MarketStock(market=self.MARKET, symbol=row.symbol)
                self._apply_stock(incoming, row)
                session.add(incoming)
                self.stats.stocks_inserted += 1

    def _migrate_daily_bars(self, session) -> None:
        query = session.query(USStockDaily).order_by(USStockDaily.symbol, USStockDaily.date)
        if self.symbols:
            query = query.filter(USStockDaily.symbol.in_(self.symbols))

        for row in query.all():
            self.stats.daily_rows_seen += 1
            existing = session.query(MarketDailyBar).filter_by(
                market=self.MARKET,
                symbol=row.symbol,
                date=row.date,
            ).first()
            if existing:
                self._apply_daily_bar(existing, row)
                self.stats.daily_rows_updated += 1
            else:
                incoming = MarketDailyBar(market=self.MARKET, symbol=row.symbol, date=row.date)
                self._apply_daily_bar(incoming, row)
                session.add(incoming)
                self.stats.daily_rows_inserted += 1

            if self.stats.daily_rows_seen % 500 == 0:
                session.flush()

    def _migrate_sync_status(self, session) -> None:
        query = session.query(DataSyncStatus).order_by(DataSyncStatus.symbol)
        if self.symbols:
            query = query.filter(DataSyncStatus.symbol.in_(self.symbols))

        for row in query.all():
            self.stats.sync_rows_seen += 1
            existing = session.query(MarketSyncStatus).filter_by(market=self.MARKET, symbol=row.symbol).first()
            if existing:
                self._apply_sync_status(existing, row)
                self.stats.sync_rows_updated += 1
            else:
                incoming = MarketSyncStatus(market=self.MARKET, symbol=row.symbol)
                self._apply_sync_status(incoming, row)
                session.add(incoming)
                self.stats.sync_rows_inserted += 1

    @staticmethod
    def _apply_stock(target: MarketStock, source: USStock) -> None:
        target.raw_symbol = source.symbol
        target.name = source.name or source.symbol
        target.exchange = source.exchange
        target.board = None
        target.sector = source.sector
        target.industry = source.industry
        target.area = None
        target.country = source.country or "US"
        target.currency = source.currency or "USD"
        target.price = source.price
        target.change_pct = None
        target.market_cap = source.market_cap
        target.pe_ratio = source.pe_ratio
        target.pb_ratio = source.pb_ratio
        target.dividend_yield = source.dividend_yield
        target.turnover_rate = None

    @staticmethod
    def _apply_daily_bar(target: MarketDailyBar, source: USStockDaily) -> None:
        target.open = source.open
        target.high = source.high
        target.low = source.low
        target.close = source.close
        target.volume = source.volume
        target.amount = None
        target.adjusted_close = source.adjusted_close
        target.change_pct = None
        target.change_amount = None
        target.amplitude = None
        target.turnover_rate = None
        target.sma_20 = source.sma_20
        target.sma_50 = source.sma_50
        target.sma_200 = source.sma_200
        target.ema_12 = source.ema_12
        target.ema_26 = source.ema_26
        target.macd = source.macd
        target.macd_signal = source.macd_signal
        target.macd_hist = source.macd_hist
        target.rsi_14 = source.rsi_14
        target.bb_upper = source.bb_upper
        target.bb_middle = source.bb_middle
        target.bb_lower = source.bb_lower
        target.atr_14 = source.atr_14
        target.volume_sma_20 = source.volume_sma_20

    @staticmethod
    def _apply_sync_status(target: MarketSyncStatus, source: DataSyncStatus) -> None:
        target.last_sync_date = source.last_sync_date
        target.last_sync_time = source.last_sync_time
        target.total_rows = source.total_rows
        target.status = source.status
        target.error_message = source.error_message
        target.retry_count = source.retry_count


def migrate_us_to_market_tables(*, dry_run: bool = False, symbols: list[str] | None = None) -> dict[str, Any]:
    """Convenience function used by CLI and tests."""
    migrator = USMarketTableMigrator(dry_run=dry_run, symbols=symbols)
    return migrator.run()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate US legacy tables into generic market tables")
    parser.add_argument("--dry-run", action="store_true", help="Scan and simulate migration without committing")
    parser.add_argument(
        "--symbols",
        nargs="*",
        help="Optional list of US symbols to migrate, e.g. AAPL MSFT",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = migrate_us_to_market_tables(dry_run=args.dry_run, symbols=args.symbols)
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
