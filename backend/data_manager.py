"""
数据管理器 - 批量下载 / 增量更新 / 数据库缓存
设计原则：
  - 按序下载，避免带宽抢占和 yfinance 限流
  - 每次请求间隔 delay，降低 API 被封风险
  - 每个操作独立 session，消除并发冲突
  - SQLAlchemy merge() 替代手写 upsert，代码简洁
"""
import time
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy import Column, Integer, String, Date, DateTime, Float
from sqlalchemy.sql import func

from backend.database import SessionLocal, engine, Base
from backend.crawlers.us_stock_source import USStockSource, MAJOR_US_STOCKS
from backend.crawlers.data_cleaner import USDataCleaner
from backend.models.stock import USStockDaily

logger = logging.getLogger(__name__)

# ============================================================
# 同步状态表 — 每只股票最后同步日期
# ============================================================
class DataSyncStatus(Base):
    """数据同步状态"""
    __tablename__ = "data_sync_status"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    last_sync_date = Column(Date, nullable=False)
    last_sync_time = Column(DateTime, server_default=func.now(), onupdate=func.now())
    total_rows = Column(Integer, default=0)
    status = Column(String(20), default="pending")   # pending / syncing / completed / error
    error_message = Column(String(500))


class DataManager:
    """数据管理器：下载 / 增量更新 / 缓存查询"""

    def __init__(self, request_delay: float = 0.6, history_years: int = 10):
        self.source = USStockSource()
        self.delay = request_delay      # 每只股票请求间隔（秒）
        self.history_years = history_years
        Base.metadata.create_all(bind=engine)

    # ----------------------------------------------------------
    # 1. 全量下载
    # ----------------------------------------------------------
    def download_all(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """顺序下载所有股票的历史数据"""
        targets = symbols or MAJOR_US_STOCKS
        total = len(targets)
        logger.info(f"全量下载启动: {total} 只股票 × {self.history_years}年, "
                    f"请求间隔 {self.delay}s")

        results = {"success": 0, "failed": 0, "total_rows": 0, "errors": []}

        for i, sym in enumerate(targets, 1):
            rows, err = self._download_one(sym)
            if err:
                results["failed"] += 1
                results["errors"].append(f"{sym}: {err}")
            else:
                results["success"] += 1
                results["total_rows"] += rows

            # 进度
            if i % 5 == 0 or i == total:
                elapsed = (i * self.delay) / 60  # 估算
                logger.info(f"  [{i}/{total}] 成功{results['success']} 失败{results['failed']}  "
                            f"累计{results['total_rows']}行  (约{elapsed:.0f}min)")

        logger.info(f"全量下载完成: 成功{results['success']} / {total}, "
                    f"共{results['total_rows']}行")
        return results

    def _download_one(self, symbol: str) -> tuple:
        """单只股票：下载 → 清洗 → 技术指标 → 入库"""
        session = SessionLocal()
        try:
            df = self.source.get_full_history(symbol, years=self.history_years)
            if df.empty:
                return 0, "无数据"

            df = USDataCleaner.clean_daily_data(df)
            df = USDataCleaner.add_technical_indicators(df)

            rows = self._save_to_db(session, symbol, df)
            self._update_sync_record(session, symbol, df["date"].max(), rows, "completed")
            session.commit()

            time.sleep(self.delay)  # 限速
            return rows, None

        except Exception as e:
            session.rollback()
            logger.warning(f"  {symbol} 下载失败: {e}")
            try:
                self._update_sync_record(session, symbol,
                                         date(2000, 1, 1), 0, "error", str(e)[:500])
                session.commit()
            except Exception:
                session.rollback()
            return 0, str(e)[:200]
        finally:
            session.close()

    # ----------------------------------------------------------
    # 2. 增量更新
    # ----------------------------------------------------------
    def incremental_update(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """增量更新：每个股票只拉取最新数据"""
        targets = symbols or MAJOR_US_STOCKS
        total = len(targets)
        logger.info(f"增量更新启动: {total} 只")

        results = {"updated": 0, "no_change": 0, "failed": 0, "new_rows": 0}

        for i, sym in enumerate(targets, 1):
            try:
                new_rows = self._incremental_one(sym)
                if new_rows > 0:
                    results["updated"] += 1
                    results["new_rows"] += new_rows
                elif new_rows == 0:
                    results["no_change"] += 1
                # new_rows == -1 表示调用了全量下载
            except Exception as e:
                results["failed"] += 1
                logger.warning(f"  {sym} 增量更新失败: {e}")

            if i % 20 == 0 or i == total:
                logger.info(f"  [{i}/{total}] 更新{results['updated']} 无变化"
                            f"{results['no_change']} 失败{results['failed']}  "
                            f"新增{results['new_rows']}行")

        logger.info(f"增量更新完成: 更新{results['updated']}只, "
                    f"新增{results['new_rows']}行")
        return results

    def _incremental_one(self, symbol: str) -> int:
        """单只增量更新"""
        session = SessionLocal()
        try:
            sync = session.query(DataSyncStatus).filter_by(symbol=symbol).first()
            if not sync or not sync.last_sync_date or sync.last_sync_date.year <= 2000:
                # 从未同步 → 全量下载
                self._download_one(symbol)
                return -1

            start = sync.last_sync_date - timedelta(days=5)  # 向前补5天避免gap
            df = self.source.get_daily_data(
                symbol,
                start.strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d"),
            )
            if df.empty:
                return 0

            df = USDataCleaner.clean_daily_data(df)
            df = USDataCleaner.add_technical_indicators(df)

            # 去重：只保留数据库中不存在的日期
            existing = {
                r[0] for r in session.query(USStockDaily.date)
                .filter(USStockDaily.symbol == symbol).all()
            }
            new_df = df[~df["date"].isin(existing)]
            if new_df.empty:
                return 0

            rows = self._save_to_db(session, symbol, new_df)
            total = (sync.total_rows or 0) + rows
            self._update_sync_record(session, symbol, df["date"].max(), total, "completed")
            session.commit()
            return rows
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ----------------------------------------------------------
    # 3. 入库（使用 merge 简化 upsert）
    # ----------------------------------------------------------
    def _save_to_db(self, session, symbol: str, df: pd.DataFrame) -> int:
        """逐行 merge 写入（存在则更新，不存在则插入）"""
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
            session.merge(rec)  # 有则更新，无则插入
            count += 1

            # 每 500 行 flush 一次释放内存
            if count % 500 == 0:
                session.flush()

        session.commit()
        return count

    @staticmethod
    def _f(row, key, default=0.0) -> Optional[float]:
        """安全读取 DataFrame 行，NaN → None"""
        v = row.get(key, default)
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return float(v)

    def _update_sync_record(self, session, symbol: str,
                            sync_date, total_rows: int,
                            status: str, err_msg: str = None):
        """更新同步状态记录"""
        sync = session.query(DataSyncStatus).filter_by(symbol=symbol).first()
        if sync:
            sync.last_sync_date = sync_date
            sync.total_rows = total_rows
            sync.status = status
            sync.error_message = err_msg
        else:
            session.add(DataSyncStatus(
                symbol=symbol, last_sync_date=sync_date,
                total_rows=total_rows, status=status,
                error_message=err_msg,
            ))

    # ----------------------------------------------------------
    # 4. 查询（DB 缓存）
    # ----------------------------------------------------------
    def get_daily_from_db(self, symbol: str, years: int = 5) -> Optional[List]:
        """从 DB 读取日线，不足 20 条返回 None → fallback"""
        session = SessionLocal()
        try:
            cutoff = date.today() - timedelta(days=years * 365)
            rows = (session.query(USStockDaily)
                    .filter(USStockDaily.symbol == symbol, USStockDaily.date >= cutoff)
                    .order_by(USStockDaily.date).all())
            return rows if len(rows) >= 20 else None
        finally:
            session.close()

    def get_sync_summary(self) -> List[Dict[str, Any]]:
        """同步概览"""
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
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    mgr = DataManager(request_delay=0.6)

    if len(sys.argv) < 2:
        print("用法: python -m backend.data_manager [download|update|status] [symbols...]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "download":
        mgr.download_all(sys.argv[2:] or None)
    elif cmd == "update":
        mgr.incremental_update()
    elif cmd == "status":
        rows = mgr.get_sync_summary()
        if not rows:
            print("  (暂无同步记录)")
        for s in rows:
            print(f"  {s['symbol']:6s}  {s['status']:10s}  "
                  f"{s['last_sync_date'] or '-':12s}  "
                  f"{s['total_rows']:5d}行  {s['error'] or ''}")
    else:
        print(f"未知命令: {cmd}")
