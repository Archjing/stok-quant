"""
多市场数据管理器。

第一阶段仅服务 CN/HK；US 继续使用现有 DataManager。
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Any

import pandas as pd

from backend.crawlers.data_cleaner import USDataCleaner
from backend.database import Base, SessionLocal, engine
from backend.markets.registry import get_market_source
from backend.markets.symbols import get_currency, normalize_market, normalize_symbol
from backend.models.market import MarketDailyBar, MarketStock, MarketSyncStatus

logger = logging.getLogger(__name__)


class MarketDownloadConfig:
    """多市场下载配置。"""

    CACHE_EXPIRY_DAYS = 7
    REQUEST_DELAY = 0.6
    BATCH_SIZE = 5
    BATCH_PAUSE = 5


class MarketDataManager:
    """CN/HK 多市场数据管理器。"""

    def __init__(self, request_delay: float = MarketDownloadConfig.REQUEST_DELAY, history_years: int = 10):
        self.request_delay = request_delay
        self.history_years = history_years
        self.config = MarketDownloadConfig()
        Base.metadata.create_all(bind=engine)

    # ==========================================================
    # 股票列表
    # ==========================================================
    def get_stock_list(self, market: str) -> list[dict[str, Any]]:
        """获取市场股票列表，优先读取 DB，无缓存时从数据源种子化。"""
        market_code = self._new_market(market)
        self._ensure_stocks_seeded(market_code)
        return self._read_stock_list_from_db(market_code)

    def _ensure_stocks_seeded(self, market: str) -> None:
        """确保 market_stocks 中已有指定市场股票记录。"""
        session = SessionLocal()
        try:
            exists = session.query(MarketStock).filter_by(market=market).first()
            if exists:
                return

            source = get_market_source(market)
            if market == "CN" and hasattr(source, "_sample_stock_list"):
                stocks = source._sample_stock_list()
            elif market == "HK" and hasattr(source, "_sample_stock_list"):
                stocks = source._sample_stock_list()
            else:
                stocks = source.get_stock_list()
            for item in stocks:
                stock = MarketStock(
                    market=market,
                    symbol=item.get("symbol"),
                    raw_symbol=item.get("raw_symbol"),
                    name=item.get("name") or item.get("symbol"),
                    exchange=item.get("exchange"),
                    board=item.get("board"),
                    sector=item.get("sector"),
                    industry=item.get("industry"),
                    area=item.get("area"),
                    country=item.get("country"),
                    currency=item.get("currency") or get_currency(market),
                    price=self._f_value(item.get("price")),
                    change_pct=self._f_value(item.get("change_pct")),
                    market_cap=self._f_value(item.get("market_cap")),
                    pe_ratio=self._f_value(item.get("pe_ratio")),
                    pb_ratio=self._f_value(item.get("pb_ratio")),
                    dividend_yield=self._f_value(item.get("dividend_yield")),
                    turnover_rate=self._f_value(item.get("turnover_rate")),
                )
                if stock.symbol and stock.name:
                    self._upsert_stock(session, stock)
            session.commit()
            logger.info("%s 股票列表种子化完成: %s 条", market, len(stocks))
        finally:
            session.close()

    def _read_stock_list_from_db(self, market: str) -> list[dict[str, Any]]:
        """从 DB 读取股票列表。"""
        session = SessionLocal()
        try:
            rows = session.query(MarketStock).filter_by(market=market).order_by(MarketStock.symbol).all()
            return [self._stock_to_dict(row) for row in rows]
        finally:
            session.close()

    # ==========================================================
    # 下载与同步
    # ==========================================================
    def lazy_download_one(self, market: str, symbol: str, years: int | None = None, adjust: str = "qfq") -> tuple[bool, int, str | None]:
        """按需下载单只股票历史日线并入库。"""
        market_code = self._new_market(market)
        normalized = normalize_symbol(symbol, market_code)
        years = years or self.history_years
        session = SessionLocal()
        try:
            source = get_market_source(market_code)
            self._update_sync_record(session, market_code, normalized, date.today(), 0, "syncing")
            session.commit()

            time.sleep(self.request_delay)
            df = source.get_full_history(normalized, years=years, adjust=adjust)
            if df is None or df.empty:
                self._update_sync_record(session, market_code, normalized, date.today(), 0, "error", "no_data")
                session.commit()
                return False, 0, "no_data"

            df = USDataCleaner.clean_daily_data(df)
            df = USDataCleaner.add_technical_indicators(df)

            rows = self._save_daily_to_db(session, market_code, normalized, df)
            sync_date = self._max_date(df) or date.today()
            self._update_sync_record(session, market_code, normalized, sync_date, rows, "completed")
            self._upsert_stock_from_source(session, market_code, normalized)
            session.commit()
            logger.info("%s/%s 下载成功: %s 行", market_code, normalized, rows)
            return True, rows, None
        except Exception as exc:
            session.rollback()
            logger.exception("%s/%s 下载失败", market_code, normalized)
            try:
                self._update_sync_record(session, market_code, normalized, date.today(), 0, "error", str(exc)[:500])
                session.commit()
            except Exception:
                session.rollback()
            return False, 0, str(exc)
        finally:
            session.close()

    def download_all(self, market: str, symbols: list[str] | None = None, years: int | None = None, adjust: str = "qfq") -> dict[str, Any]:
        """批量下载指定市场股票。"""
        market_code = self._new_market(market)
        if symbols is None:
            symbols = [item["symbol"] for item in self.get_stock_list(market_code)]
        targets = [normalize_symbol(sym, market_code) for sym in symbols]
        results: dict[str, Any] = {"market": market_code, "success": 0, "failed": 0, "total_rows": 0, "errors": []}

        for index, sym in enumerate(targets, 1):
            ok, rows, err = self.lazy_download_one(market_code, sym, years=years, adjust=adjust)
            if ok:
                results["success"] += 1
                results["total_rows"] += rows
            else:
                results["failed"] += 1
                results["errors"].append(f"{sym}: {err}")
            if index % self.config.BATCH_SIZE == 0 and index < len(targets):
                time.sleep(self.config.BATCH_PAUSE)
        return results

    def incremental_update(self, market: str, symbols: list[str] | None = None, adjust: str = "qfq") -> dict[str, Any]:
        """增量更新过期或缺失数据。"""
        market_code = self._new_market(market)
        if symbols is None:
            symbols = [item["symbol"] for item in self.get_stock_list(market_code)]
        results = {"market": market_code, "updated": 0, "no_change": 0, "skipped": 0, "new_rows": 0}

        for sym in symbols:
            normalized = normalize_symbol(sym, market_code)
            status = self._check_data_freshness(market_code, normalized)
            if status == "ok":
                results["no_change"] += 1
                continue
            ok, rows, _ = self.lazy_download_one(market_code, normalized, years=self.history_years, adjust=adjust)
            if ok:
                results["updated"] += 1
                results["new_rows"] += rows
            else:
                results["skipped"] += 1
        return results

    def refresh_stock_prices(self, market: str) -> int:
        """刷新股票价格。第一阶段以重新拉取列表价格为主，失败不影响历史数据。"""
        market_code = self._new_market(market)
        source = get_market_source(market_code)
        stocks = source.get_stock_list()
        session = SessionLocal()
        try:
            count = 0
            for item in stocks:
                symbol = item.get("symbol")
                if not symbol:
                    continue
                rec = session.query(MarketStock).filter_by(market=market_code, symbol=symbol).first()
                if not rec:
                    continue
                rec.price = self._f_value(item.get("price"))
                rec.change_pct = self._f_value(item.get("change_pct"))
                rec.turnover_rate = self._f_value(item.get("turnover_rate"))
                count += 1
            session.commit()
            return count
        finally:
            session.close()

    def backfill_technical_indicators(self, market: str, symbols: list[str] | None = None) -> dict[str, Any]:
        """批量回填指定市场历史日线的技术指标。"""
        market_code = self._new_market(market)
        targets = self._get_backfill_targets(market_code, symbols)
        results: dict[str, Any] = {
            "market": market_code,
            "symbols_total": len(targets),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "updated_rows": 0,
            "errors": [],
        }

        for index, sym in enumerate(targets, 1):
            ok, rows, status = self._backfill_one_symbol(market_code, sym)
            if ok:
                if rows > 0:
                    results["processed"] += 1
                    results["updated_rows"] += rows
                else:
                    results["skipped"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"{sym}: {status}")
            if index % self.config.BATCH_SIZE == 0 and index < len(targets):
                time.sleep(self.config.BATCH_PAUSE)
        return results

    # ==========================================================
    # 查询
    # ==========================================================
    def get_daily_from_db(self, market: str, symbol: str, years: int = 5) -> list[MarketDailyBar] | None:
        """从 DB 获取历史日线。"""
        market_code = self._new_market(market)
        normalized = normalize_symbol(symbol, market_code)
        session = SessionLocal()
        try:
            cutoff = date.today() - timedelta(days=years * 365)
            rows = session.query(MarketDailyBar).filter(
                MarketDailyBar.market == market_code,
                MarketDailyBar.symbol == normalized,
                MarketDailyBar.date >= cutoff,
            ).order_by(MarketDailyBar.date).all()
            return rows if len(rows) >= 20 else None
        finally:
            session.close()

    def get_sync_summary(self, market: str) -> list[dict[str, Any]]:
        """获取同步状态汇总。"""
        market_code = self._new_market(market)
        session = SessionLocal()
        try:
            rows = session.query(MarketSyncStatus).filter_by(market=market_code).order_by(MarketSyncStatus.symbol).all()
            return [
                {
                    "market": row.market,
                    "symbol": row.symbol,
                    "last_sync_date": str(row.last_sync_date) if row.last_sync_date else None,
                    "days_ago": (date.today() - row.last_sync_date).days if row.last_sync_date else None,
                    "total_rows": row.total_rows,
                    "status": row.status,
                    "error": row.error_message,
                }
                for row in rows
            ]
        finally:
            session.close()

    def get_missing_symbols(self, market: str, symbols: list[str] | None = None) -> list[str]:
        """获取缺少历史数据的股票。"""
        market_code = self._new_market(market)
        if symbols is None:
            symbols = [item["symbol"] for item in self.get_stock_list(market_code)]
        targets = [normalize_symbol(sym, market_code) for sym in symbols]
        session = SessionLocal()
        try:
            synced = {
                row.symbol
                for row in session.query(MarketSyncStatus.symbol).filter(
                    MarketSyncStatus.market == market_code,
                    MarketSyncStatus.status == "completed",
                    MarketSyncStatus.total_rows > 20,
                ).all()
            }
            return [sym for sym in targets if sym not in synced]
        finally:
            session.close()

    # ==========================================================
    # 转换工具
    # ==========================================================
    def rows_to_dataframe(self, rows: list[MarketDailyBar]) -> pd.DataFrame:
        """将 MarketDailyBar 行转换为标准 DataFrame。"""
        return pd.DataFrame([self._daily_row_to_dict(row) for row in rows])

    # ==========================================================
    # 内部方法
    # ==========================================================
    def _save_daily_to_db(self, session, market: str, symbol: str, df: pd.DataFrame) -> int:
        count = 0
        for _, row in df.iterrows():
            rec = MarketDailyBar(
                market=market,
                symbol=symbol,
                date=row.get("date"),
                open=self._f(row, "open"),
                high=self._f(row, "high"),
                low=self._f(row, "low"),
                close=self._f(row, "close"),
                volume=self._f(row, "volume"),
                amount=self._f(row, "amount"),
                adjusted_close=self._f(row, "adjusted_close", row.get("close")),
                change_pct=self._f(row, "change_pct"),
                change_amount=self._f(row, "change_amount"),
                amplitude=self._f(row, "amplitude"),
                turnover_rate=self._f(row, "turnover_rate"),
                sma_20=self._f(row, "sma_20"),
                sma_50=self._f(row, "sma_50"),
                sma_200=self._f(row, "sma_200"),
                ema_12=self._f(row, "ema_12"),
                ema_26=self._f(row, "ema_26"),
                macd=self._f(row, "macd"),
                macd_signal=self._f(row, "macd_signal"),
                macd_hist=self._f(row, "macd_hist"),
                rsi_14=self._f(row, "rsi_14"),
                bb_upper=self._f(row, "bb_upper"),
                bb_middle=self._f(row, "bb_middle"),
                bb_lower=self._f(row, "bb_lower"),
                atr_14=self._f(row, "atr_14"),
                volume_sma_20=self._f(row, "volume_sma_20"),
            )
            self._upsert_daily_bar(session, rec)
            count += 1
            if count % 500 == 0:
                session.flush()
        return count

    def _upsert_stock_from_source(self, session, market: str, symbol: str) -> None:
        """从数据源基础信息补齐 MarketStock。"""
        source = get_market_source(market)
        info = source.get_stock_info(symbol) or {}
        rec = MarketStock(
            market=market,
            symbol=symbol,
            raw_symbol=info.get("raw_symbol"),
            name=info.get("name") or symbol,
            exchange=info.get("exchange"),
            board=info.get("board"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            area=info.get("area"),
            country=info.get("country"),
            currency=info.get("currency") or get_currency(market),
            price=self._f_value(info.get("price")),
            change_pct=self._f_value(info.get("change_pct")),
            market_cap=self._f_value(info.get("market_cap")),
            pe_ratio=self._f_value(info.get("pe_ratio")),
            pb_ratio=self._f_value(info.get("pb_ratio")),
            dividend_yield=self._f_value(info.get("dividend_yield")),
            turnover_rate=self._f_value(info.get("turnover_rate")),
        )
        self._upsert_stock(session, rec)

    @staticmethod
    def _upsert_stock(session, incoming: MarketStock) -> None:
        """按 (market, symbol) 更新或插入股票基础信息。"""
        existing = session.query(MarketStock).filter_by(market=incoming.market, symbol=incoming.symbol).first()
        if existing:
            for attr in [
                "raw_symbol", "name", "exchange", "board", "sector", "industry", "area", "country", "currency",
                "price", "change_pct", "market_cap", "pe_ratio", "pb_ratio", "dividend_yield", "turnover_rate",
            ]:
                value = getattr(incoming, attr)
                if value is not None:
                    setattr(existing, attr, value)
        else:
            session.add(incoming)

    @staticmethod
    def _upsert_daily_bar(session, incoming: MarketDailyBar) -> None:
        """按 (market, symbol, date) 更新或插入日线数据。"""
        existing = session.query(MarketDailyBar).filter_by(
            market=incoming.market,
            symbol=incoming.symbol,
            date=incoming.date,
        ).first()
        if existing:
            for attr in [
                "open", "high", "low", "close", "volume", "amount", "adjusted_close",
                "change_pct", "change_amount", "amplitude", "turnover_rate",
                "sma_20", "sma_50", "sma_200", "ema_12", "ema_26", "macd", "macd_signal", "macd_hist",
                "rsi_14", "bb_upper", "bb_middle", "bb_lower", "atr_14", "volume_sma_20",
            ]:
                setattr(existing, attr, getattr(incoming, attr))
        else:
            session.add(incoming)

    def _update_sync_record(self, session, market: str, symbol: str, sync_date, total_rows: int, status: str, err_msg: str | None = None) -> None:
        sync = session.query(MarketSyncStatus).filter_by(market=market, symbol=symbol).first()
        if sync:
            sync.last_sync_date = sync_date
            sync.total_rows = total_rows
            sync.status = status
            sync.error_message = err_msg
            if status == "error":
                sync.retry_count = (sync.retry_count or 0) + 1
        else:
            session.add(MarketSyncStatus(
                market=market,
                symbol=symbol,
                last_sync_date=sync_date,
                total_rows=total_rows,
                status=status,
                error_message=err_msg,
                retry_count=1 if status == "error" else 0,
            ))

    def _check_data_freshness(self, market: str, symbol: str) -> str:
        session = SessionLocal()
        try:
            sync = session.query(MarketSyncStatus).filter_by(market=market, symbol=symbol).first()
            if not sync or sync.status != "completed" or not sync.last_sync_date:
                return "missing"
            days_old = (date.today() - sync.last_sync_date).days
            return "expired" if days_old > self.config.CACHE_EXPIRY_DAYS else "ok"
        finally:
            session.close()

    def _get_backfill_targets(self, market: str, symbols: list[str] | None = None) -> list[str]:
        if symbols:
            return [normalize_symbol(sym, market) for sym in symbols]

        session = SessionLocal()
        try:
            rows = (
                session.query(MarketDailyBar.symbol)
                .filter(MarketDailyBar.market == market)
                .distinct()
                .order_by(MarketDailyBar.symbol)
                .all()
            )
            return [row.symbol for row in rows]
        finally:
            session.close()

    def _backfill_one_symbol(self, market: str, symbol: str) -> tuple[bool, int, str | None]:
        session = SessionLocal()
        try:
            rows = (
                session.query(MarketDailyBar)
                .filter(
                    MarketDailyBar.market == market,
                    MarketDailyBar.symbol == symbol,
                )
                .order_by(MarketDailyBar.date)
                .all()
            )
            if len(rows) < 20:
                return True, 0, "not_enough_rows"

            df = self.rows_to_dataframe(rows)
            df = USDataCleaner.clean_daily_data(df)
            if df.empty or len(df) < 20:
                return True, 0, "not_enough_rows"

            df = USDataCleaner.add_technical_indicators(df)
            updated_rows = self._save_daily_to_db(session, market, symbol, df)
            sync_date = self._max_date(df) or date.today()
            self._update_sync_record(session, market, symbol, sync_date, updated_rows, "completed")
            session.commit()
            logger.info("%s/%s 指标回填成功: %s 行", market, symbol, updated_rows)
            return True, updated_rows, None
        except Exception as exc:
            session.rollback()
            logger.exception("%s/%s 指标回填失败", market, symbol)
            try:
                self._update_sync_record(session, market, symbol, date.today(), 0, "error", str(exc)[:500])
                session.commit()
            except Exception:
                session.rollback()
            return False, 0, str(exc)
        finally:
            session.close()

    @staticmethod
    def _stock_to_dict(row: MarketStock) -> dict[str, Any]:
        return {
            "market": row.market,
            "symbol": row.symbol,
            "raw_symbol": row.raw_symbol,
            "name": row.name,
            "exchange": row.exchange,
            "board": row.board,
            "sector": row.sector,
            "industry": row.industry,
            "area": row.area,
            "country": row.country,
            "currency": row.currency,
            "price": row.price,
            "change_pct": row.change_pct,
            "market_cap": row.market_cap,
            "pe_ratio": row.pe_ratio,
            "pb_ratio": row.pb_ratio,
            "dividend_yield": row.dividend_yield,
            "turnover_rate": row.turnover_rate,
        }

    @staticmethod
    def _daily_row_to_dict(row: MarketDailyBar) -> dict[str, Any]:
        return {
            "market": row.market,
            "symbol": row.symbol,
            "date": row.date,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
            "amount": row.amount,
            "adjusted_close": row.adjusted_close,
            "change_pct": row.change_pct,
            "change_amount": row.change_amount,
            "amplitude": row.amplitude,
            "turnover_rate": row.turnover_rate,
            "sma_20": row.sma_20,
            "sma_50": row.sma_50,
            "sma_200": row.sma_200,
            "ema_12": row.ema_12,
            "ema_26": row.ema_26,
            "macd": row.macd,
            "macd_signal": row.macd_signal,
            "macd_hist": row.macd_hist,
            "rsi_14": row.rsi_14,
            "bb_upper": row.bb_upper,
            "bb_middle": row.bb_middle,
            "bb_lower": row.bb_lower,
            "atr_14": row.atr_14,
            "volume_sma_20": row.volume_sma_20,
        }

    @staticmethod
    def _max_date(df: pd.DataFrame):
        if "date" not in df.columns or df.empty:
            return None
        max_val = df["date"].max()
        if hasattr(max_val, "date"):
            return max_val.date()
        return max_val

    @staticmethod
    def _f(row: pd.Series, key: str, default: Any = None) -> float | None:
        value = row.get(key, default)
        return MarketDataManager._f_value(value)

    @staticmethod
    def _f_value(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            if pd.isna(value):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _new_market(market: str) -> str:
        market_code = normalize_market(market)
        if market_code == "US":
            raise ValueError("MarketDataManager only manages CN/HK in the first migration phase")
        return market_code
