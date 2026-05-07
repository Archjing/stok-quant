"""
数据管理器 - 批量下载 / 增量更新 / 数据库缓存 / 价格刷新
"""
import time
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy import Column, Integer, String, Date, DateTime, Float
from sqlalchemy.sql import func
import yfinance as yf

from backend.database import SessionLocal, engine, Base
from backend.crawlers.us_stock_source import USStockSource, MAJOR_US_STOCKS, STOCK_NAMES, SECTOR_MAP
from backend.crawlers.data_cleaner import USDataCleaner
from backend.models.stock import USStock, USStockDaily

logger = logging.getLogger(__name__)

# ============================================================
# 同步状态表
# ============================================================
class DataSyncStatus(Base):
    """数据同步状态"""
    __tablename__ = "data_sync_status"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    last_sync_date = Column(Date, nullable=False)
    last_sync_time = Column(DateTime, server_default=func.now(), onupdate=func.now())
    total_rows = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    error_message = Column(String(500))


PRICE_CACHE_TTL = 300  # 价格缓存 5 分钟


class DataManager:
    """数据管理器"""

    def __init__(self, request_delay: float = 0.6, history_years: int = 10):
        self.source = USStockSource()
        self.delay = request_delay
        self.history_years = history_years
        Base.metadata.create_all(bind=engine)

    # ==========================================================
    # 1. 股票列表 + 实时价格（懒加载 + 缓存）
    # ==========================================================
    def get_stock_list(self) -> List[Dict[str, Any]]:
        """获取股票列表（自动判断是否需要刷新价格）"""
        self._ensure_stocks_seeded()
        if self._price_cache_stale():
            self.refresh_stock_prices()
        return self._read_stock_list_from_db()

    def _ensure_stocks_seeded(self):
        """确保 us_stocks 表有基础记录"""
        session = SessionLocal()
        try:
            count = session.query(USStock).count()
            if count > 0:
                return
            # 首次种子化
            for sym in MAJOR_US_STOCKS:
                session.add(USStock(
                    symbol=sym,
                    name=STOCK_NAMES.get(sym, sym),
                    sector=SECTOR_MAP.get(sym),
                    exchange="NASDAQ" if sym in {
                        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                        "ADBE", "AMD", "INTC", "NFLX", "PYPL", "BIDU", "PDD",
                    } else "NYSE",
                ))
            session.commit()
            logger.info(f"us_stocks 表种子化完成: {len(MAJOR_US_STOCKS)} 条")
        finally:
            session.close()

    def _price_cache_stale(self) -> bool:
        """判断价格缓存是否过期"""
        session = SessionLocal()
        try:
            row = session.query(USStock).filter(USStock.price.isnot(None)).first()
            if not row:
                return True  # 从未刷新过
            if not row.updated_at:
                return True
            age = (datetime.now() - row.updated_at).total_seconds()
            return age > PRICE_CACHE_TTL
        finally:
            session.close()

    def _read_stock_list_from_db(self) -> List[Dict[str, Any]]:
        """从 DB 读取股票列表"""
        session = SessionLocal()
        try:
            rows = session.query(USStock).order_by(USStock.symbol).all()
            return [{
                "symbol": r.symbol,
                "name": r.name,
                "exchange": r.exchange,
                "sector": r.sector,
                "price": r.price,
                "change_pct": None,
                "market_cap": r.market_cap,
                "pe_ratio": r.pe_ratio,
            } for r in rows]
        finally:
            session.close()

    def refresh_stock_prices(self) -> int:
        """批量刷新股票实时价格（yfinance 一次调用），返回更新条数"""
        logger.info("刷新股票实时价格...")
        prices, infos = {}, {}
        try:
            # 批量获取行情
            batch = yf.download(
                tickers=" ".join(MAJOR_US_STOCKS),
                period="1d", progress=False, auto_adjust=True,
            )
            if not batch.empty and "Close" in batch.columns:
                last = batch.iloc[-1]
                for sym in MAJOR_US_STOCKS:
                    try:
                        val = last["Close"][sym]
                        if val is not None and not (isinstance(val, float) and pd.isna(val)):
                            prices[sym] = float(val)
                    except (KeyError, TypeError):
                        pass
            logger.info(f"批量获取完毕，成功 {len(prices)}/{len(MAJOR_US_STOCKS)} 只")
        except Exception as e:
            logger.warning(f"批量获取行情失败: {e}")

        # 写入 DB
        session = SessionLocal()
        try:
            count = 0
            for sym in MAJOR_US_STOCKS:
                rec = session.query(USStock).filter_by(symbol=sym).first()
                if not rec:
                    continue
                if sym in prices:
                    rec.price = prices[sym]
                rec.updated_at = datetime.now()
                count += 1
            session.commit()
            logger.info(f"价格缓存已刷新: {count} 只")
            return count
        finally:
            session.close()

    # ==========================================================
    # 2. 全量历史数据下载
    # ==========================================================
    def download_all(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        targets = symbols or MAJOR_US_STOCKS
        total = len(targets)
        logger.info(f"全量下载启动: {total} 只 × {self.history_years}年")

        results = {"success": 0, "failed": 0, "total_rows": 0, "errors": []}

        for i, sym in enumerate(targets, 1):
            rows, err = self._download_one(sym)
            if err:
                results["failed"] += 1
                results["errors"].append(f"{sym}: {err}")
            else:
                results["success"] += 1
                results["total_rows"] += rows
            if i % 5 == 0 or i == total:
                elapsed = (i * self.delay) / 60
                logger.info(f"  [{i}/{total}] 成功{results['success']} 失败{results['failed']}  "
                            f"累计{results['total_rows']}行 ({elapsed:.0f}min)")

        logger.info(f"全量下载完成: 成功{results['success']}/{total}, 共{results['total_rows']}行")
        return results

    def _download_one(self, symbol: str) -> tuple:
        session = SessionLocal()
        try:
            df = self.source.get_full_history(symbol, years=self.history_years)
            if df.empty:
                return 0, "无数据"
            df = USDataCleaner.clean_daily_data(df)
            df = USDataCleaner.add_technical_indicators(df)
            rows = self._save_daily_to_db(session, symbol, df)
            self._update_sync_record(session, symbol, df["date"].max(), rows, "completed")
            session.commit()
            time.sleep(self.delay)
            return rows, None
        except Exception as e:
            session.rollback()
            logger.warning(f"  {symbol} 下载失败: {e}")
            try:
                self._update_sync_record(session, symbol, date(2000, 1, 1), 0, "error", str(e)[:500])
                session.commit()
            except Exception:
                session.rollback()
            return 0, str(e)[:200]
        finally:
            session.close()

    # ==========================================================
    # 3. 增量更新
    # ==========================================================
    def incremental_update(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        targets = symbols or MAJOR_US_STOCKS
        total = len(targets)
        logger.info(f"增量更新启动: {total} 只")
        results = {"updated": 0, "no_change": 0, "failed": 0, "new_rows": 0}
        for i, sym in enumerate(targets, 1):
            try:
                n = self._incremental_one(sym)
                if n > 0:
                    results["updated"] += 1; results["new_rows"] += n
                elif n == 0:
                    results["no_change"] += 1
            except Exception as e:
                results["failed"] += 1
                logger.warning(f"  {sym} 增量更新失败: {e}")
            if i % 20 == 0 or i == total:
                logger.info(f"  [{i}/{total}] 更新{results['updated']} 无变化{results['no_change']} 新增{results['new_rows']}行")
        return results

    def _incremental_one(self, symbol: str) -> int:
        session = SessionLocal()
        try:
            sync = session.query(DataSyncStatus).filter_by(symbol=symbol).first()
            if not sync or not sync.last_sync_date or sync.last_sync_date.year <= 2000:
                self._download_one(symbol)
                return -1
            start = sync.last_sync_date - timedelta(days=5)
            df = self.source.get_daily_data(symbol, start.strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d"))
            if df.empty:
                return 0
            df = USDataCleaner.clean_daily_data(df)
            df = USDataCleaner.add_technical_indicators(df)
            existing = {r[0] for r in session.query(USStockDaily.date).filter(USStockDaily.symbol == symbol).all()}
            new_df = df[~df["date"].isin(existing)]
            if new_df.empty:
                return 0
            rows = self._save_daily_to_db(session, symbol, new_df)
            total = (sync.total_rows or 0) + rows
            self._update_sync_record(session, symbol, df["date"].max(), total, "completed")
            session.commit()
            return rows
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ==========================================================
    # 4. 入库
    # ==========================================================
    def _save_daily_to_db(self, session, symbol: str, df: pd.DataFrame) -> int:
        count = 0
        for _, row in df.iterrows():
            rec = USStockDaily(
                symbol=symbol,
                date=row.get("date"),
                open=self._f(row, "open"),
                high=self._f(row, "high"),
                low=self._f(row, "low"),
                close=self._f(row, "close"),
                volume=self._f(row, "volume"),
                adjusted_close=self._f(row, "adjusted_close", row.get("close")),
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
            session.merge(rec)
            count += 1
            if count % 500 == 0:
                session.flush()
        session.commit()
        return count

    @staticmethod
    def _f(row, key, default=0.0) -> Optional[float]:
        v = row.get(key, default)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return float(v)

    def _update_sync_record(self, session, symbol, sync_date, total_rows, status, err_msg=None):
        sync = session.query(DataSyncStatus).filter_by(symbol=symbol).first()
        if sync:
            sync.last_sync_date = sync_date
            sync.total_rows = total_rows
            sync.status = status
            sync.error_message = err_msg
        else:
            session.add(DataSyncStatus(symbol=symbol, last_sync_date=sync_date,
                                       total_rows=total_rows, status=status, error_message=err_msg))

    # ==========================================================
    # 5. 查询
    # ==========================================================
    def get_daily_from_db(self, symbol: str, years: int = 5) -> Optional[List]:
        session = SessionLocal()
        try:
            cutoff = date.today() - timedelta(days=years * 365)
            rows = session.query(USStockDaily).filter(
                USStockDaily.symbol == symbol, USStockDaily.date >= cutoff
            ).order_by(USStockDaily.date).all()
            return rows if len(rows) >= 20 else None
        finally:
            session.close()

    def get_sync_summary(self) -> List[Dict[str, Any]]:
        session = SessionLocal()
        try:
            rows = session.query(DataSyncStatus).order_by(DataSyncStatus.symbol).all()
            return [{
                "symbol": r.symbol,
                "last_sync_date": str(r.last_sync_date) if r.last_sync_date else None,
                "total_rows": r.total_rows,
                "status": r.status,
                "error": r.error_message,
            } for r in rows]
        finally:
            session.close()


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    mgr = DataManager(request_delay=0.6)
    if len(sys.argv) < 2:
        print("用法: python -m backend.data_manager [download|update|refresh|status] [symbols...]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "download":
        mgr.download_all(sys.argv[2:] or None)
    elif cmd == "update":
        mgr.incremental_update()
    elif cmd == "refresh":
        mgr.refresh_stock_prices()
    elif cmd == "status":
        rows = mgr.get_sync_summary()
        if not rows:
            print("  (暂无同步记录)")
        for s in rows:
            print(f"  {s['symbol']:6s}  {s['status']:10s}  "
                  f"{s['last_sync_date'] or '-':12s}  {s['total_rows']:5d}行  {s['error'] or ''}")
    else:
        print(f"未知命令: {cmd}")
