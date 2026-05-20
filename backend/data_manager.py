"""
数据管理器 - 懒人下载策略
核心原则：只在需要时下载，下载时遵守限流规则
"""
import time
import random
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
# 懒人下载配置 - 避免被限流的秘诀
# ============================================================
class LazyDownloadConfig:
    """懒人下载配置"""
    # 基础延迟（秒）- 请求间隔
    BASE_DELAY = 2.0
    
    # 随机抖动范围（秒）- 模拟人类行为
    JITTER_RANGE = (0.5, 1.5)
    
    # 限流后重试等待时间（秒）
    RATE_LIMIT_WAIT = 300  # 5分钟
    
    # 单次请求最大重试次数
    MAX_RETRIES = 3
    
    # 批量下载时的组间隔（秒）- 每下载N只股票后休息一下
    BATCH_SIZE = 5
    BATCH_PAUSE = 10  # 每批后休息10秒
    
    # 缓存有效期（天）- 数据多久算"过期"
    CACHE_EXPIRY_DAYS = 7


class DataSyncStatus(Base):
    """数据同步状态"""
    __tablename__ = "data_sync_status"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    last_sync_date = Column(Date, nullable=False)
    last_sync_time = Column(DateTime, server_default=func.now(), onupdate=func.now())
    total_rows = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, syncing, completed, error, rate_limited
    error_message = Column(String(500))
    retry_count = Column(Integer, default=0)


PRICE_CACHE_TTL = 300  # 价格缓存 5 分钟


class DataManager:
    """
    懒人数据管理器
    
    核心策略：
    1. 优先从数据库读取 - 避免不必要的网络请求
    2. 按需下载 - 只在需要时下载数据
    3. 智能限流 - 遵守 yfinance 的请求限制
    4. 静默重试 - 遇到限流时自动等待后重试
    """

    def __init__(self, request_delay: float = LazyDownloadConfig.BASE_DELAY, history_years: int = 10):
        self.source = USStockSource()
        self.delay = request_delay
        self.history_years = history_years
        self.config = LazyDownloadConfig()
        Base.metadata.create_all(bind=engine)

    # ==========================================================
    # 核心：懒人下载单只股票（带智能限流）
    # ==========================================================
    def lazy_download_one(self, symbol: str, years: int = None) -> tuple:
        """
        懒人下载：带智能重试和限流躲避
        
        Returns:
            (success: bool, rows: int, error: str or None)
        """
        if years is None:
            years = self.history_years
            
        symbol = symbol.upper()
        session = SessionLocal()
        
        try:
            # 检查是否最近刚被限流
            sync = session.query(DataSyncStatus).filter_by(symbol=symbol).first()
            if sync and sync.status == "rate_limited":
                wait_time = (datetime.now() - sync.last_sync_time).total_seconds()
                if wait_time < self.config.RATE_LIMIT_WAIT:
                    remaining = int(self.config.RATE_LIMIT_WAIT - wait_time)
                    logger.info(f"{symbol} 还在限流冷却期，还剩 {remaining} 秒")
                    return False, 0, f"rate_limited_wait:{remaining}"
            
            # 尝试下载（带重试）
            for attempt in range(self.config.MAX_RETRIES):
                try:
                    # 智能延迟
                    self._smart_delay(attempt)
                    
                    # 执行下载
                    df = self.source.get_full_history(symbol, years=years)
                    if df.empty:
                        return False, 0, "no_data"
                    
                    # 清洗数据
                    df = USDataCleaner.clean_daily_data(df)
                    df = USDataCleaner.add_technical_indicators(df)
                    
                    # 保存到数据库
                    rows = self._save_daily_to_db(session, symbol, df)
                    self._update_sync_record(session, symbol, df["date"].max(), rows, "completed")
                    session.commit()
                    
                    logger.info(f"✓ {symbol} 下载成功 ({rows} 行)")
                    return True, rows, None
                    
                except Exception as e:
                    error_msg = str(e)
                    if "Rate limited" in error_msg or "Too Many Requests" in error_msg:
                        logger.warning(f"{symbol} 触发达限流，等待 {self.config.RATE_LIMIT_WAIT} 秒...")
                        self._update_sync_record(
                            session, symbol, date.today(), 0, "rate_limited", 
                            f"Rate limited on attempt {attempt + 1}"
                        )
                        session.commit()
                        # 等待冷却期
                        time.sleep(self.config.RATE_LIMIT_WAIT)
                        # 重置状态，允许下次尝试
                        self._update_sync_record(session, symbol, date.today(), 0, "pending")
                        session.commit()
                    else:
                        logger.warning(f"{symbol} 下载失败 (尝试 {attempt + 1}): {error_msg}")
                        if attempt == self.config.MAX_RETRIES - 1:
                            return False, 0, error_msg
                        time.sleep(self.config.BASE_DELAY)
            
            return False, 0, "max_retries_exceeded"
            
        except Exception as e:
            session.rollback()
            logger.error(f"{symbol} 懒人下载异常: {e}")
            return False, 0, str(e)
        finally:
            session.close()

    def _smart_delay(self, attempt: int = 0):
        """智能延迟：基础延迟 + 随机抖动 + 重试递增"""
        base = self.delay * (attempt + 1)  # 重试次数越多，延迟越长
        jitter = random.uniform(*self.config.JITTER_RANGE)
        total = base + jitter
        logger.debug(f"延迟 {total:.1f} 秒...")
        time.sleep(total)

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
                return True
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
        """批量刷新股票实时价格（yfinance 一次调用）"""
        logger.info("刷新股票实时价格...")
        prices = {}
        try:
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
    # 2. 批量下载（懒人友好版）
    # ==========================================================
    def download_all(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        懒人批量下载 - 分批下载，避免限流
        
        策略：
        1. 每下载 N 只股票后休息一下
        2. 遇到限流自动等待
        3. 记录失败项，可以稍后重试
        """
        targets = symbols or MAJOR_US_STOCKS
        total = len(targets)
        results = {"success": 0, "failed": 0, "skipped": 0, "total_rows": 0, "errors": []}
        
        logger.info(f"=" * 50)
        logger.info(f"懒人下载启动: {total} 只股票")
        logger.info(f"每 {self.config.BATCH_SIZE} 只后休息 {self.config.BATCH_PAUSE} 秒")
        logger.info(f"=" * 50)
        
        for i, sym in enumerate(targets, 1):
            success, rows, err = self.lazy_download_one(sym)
            
            if success:
                results["success"] += 1
                results["total_rows"] += rows
            elif err and err.startswith("rate_limited_wait"):
                results["skipped"] += 1
                logger.warning(f"{sym} 跳过（等待限流冷却）")
            elif err == "no_data":
                results["failed"] += 1
                results["errors"].append(f"{sym}: 无数据")
            else:
                results["failed"] += 1
                results["errors"].append(f"{sym}: {err}")
            
            # 进度报告
            if i % 5 == 0 or i == total:
                logger.info(f"  进度: [{i}/{total}] ✓{results['success']} ✗{results['failed']} ⊘{results['skipped']}")
            
            # 批量休息
            if i % self.config.BATCH_SIZE == 0 and i < total:
                logger.info(f"  ..休息 {self.config.BATCH_PAUSE} 秒..")
                time.sleep(self.config.BATCH_PAUSE)
        
        logger.info(f"=" * 50)
        logger.info(f"懒人下载完成: 成功{results['success']}/{total}, 共{results['total_rows']}行")
        logger.info(f"=" * 50)
        return results

    # ==========================================================
    # 3. 增量更新（只更新旧数据）
    # ==========================================================
    def incremental_update(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """增量更新 - 只更新过期或有新数据的股票"""
        targets = symbols or MAJOR_US_STOCKS
        results = {"updated": 0, "no_change": 0, "skipped": 0, "new_rows": 0}
        
        for i, sym in enumerate(targets, 1):
            try:
                status = self._check_data_freshness(sym)
                
                if status == "ok":
                    results["no_change"] += 1
                elif status == "expired":
                    success, rows, err = self.lazy_download_one(sym)
                    if success:
                        results["updated"] += 1
                        results["new_rows"] += rows
                    else:
                        results["skipped"] += 1
                elif status == "missing":
                    success, rows, err = self.lazy_download_one(sym)
                    if success:
                        results["updated"] += 1
                        results["new_rows"] += rows
                    else:
                        results["skipped"] += 1
                        
            except Exception as e:
                logger.warning(f"  {sym} 更新失败: {e}")
                results["skipped"] += 1
            
            if i % 10 == 0:
                logger.info(f"  [{i}/{len(targets)}] 更新{results['updated']} 无变化{results['no_change']} 跳过{results['skipped']}")
        
        return results

    def _check_data_freshness(self, symbol: str) -> str:
        """检查数据新鲜度"""
        session = SessionLocal()
        try:
            sync = session.query(DataSyncStatus).filter_by(symbol=symbol).first()
            if not sync or sync.status != "completed":
                return "missing"
            
            days_old = (date.today() - sync.last_sync_date).days
            if days_old > self.config.CACHE_EXPIRY_DAYS:
                return "expired"
            return "ok"
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
            if status == "rate_limited":
                sync.retry_count = (sync.retry_count or 0) + 1
        else:
            session.add(DataSyncStatus(
                symbol=symbol, 
                last_sync_date=sync_date,
                total_rows=total_rows, 
                status=status, 
                error_message=err_msg
            ))

    # ==========================================================
    # 5. 查询
    # ==========================================================
    def get_daily_from_db(self, symbol: str, years: int = 5) -> Optional[List]:
        """从数据库获取历史数据"""
        session = SessionLocal()
        try:
            cutoff = date.today() - timedelta(days=years * 365)
            rows = session.query(USStockDaily).filter(
                USStockDaily.symbol == symbol, USStockDaily.date >= cutoff
            ).order_by(USStockDaily.date).all()
            # 返回至少20条数据才认为有效
            return rows if len(rows) >= 20 else None
        finally:
            session.close()

    def get_sync_summary(self) -> List[Dict[str, Any]]:
        """获取同步状态汇总"""
        session = SessionLocal()
        try:
            rows = session.query(DataSyncStatus).order_by(DataSyncStatus.symbol).all()
            return [{
                "symbol": r.symbol,
                "last_sync_date": str(r.last_sync_date) if r.last_sync_date else None,
                "days_ago": (date.today() - r.last_sync_date).days if r.last_sync_date else None,
                "total_rows": r.total_rows,
                "status": r.status,
                "error": r.error_message,
            } for r in rows]
        finally:
            session.close()

    def get_missing_symbols(self, symbols: List[str] = None) -> List[str]:
        """获取缺少数据的股票列表"""
        if symbols is None:
            symbols = MAJOR_US_STOCKS
        
        session = SessionLocal()
        try:
            synced = {r.symbol for r in session.query(DataSyncStatus.symbol).filter(
                DataSyncStatus.status == "completed",
                DataSyncStatus.total_rows > 100
            ).all()}
            return [s for s in symbols if s not in synced]
        finally:
            session.close()


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    mgr = DataManager()
    
    if len(sys.argv) < 2:
        print("""
╔════════════════════════════════════════════════════════════╗
║           懒人数据管理器 - CLI                              ║
╠════════════════════════════════════════════════════════════╣
║  download [symbols...]    下载股票数据                     ║
║  update                   增量更新过期数据                  ║
║  status                   查看同步状态                      ║
║  missing                  查看缺少数据的股票                ║
║  test <symbol>            测试下载单只股票                  ║
╚════════════════════════════════════════════════════════════╝
        """)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "download":
        symbols = sys.argv[2:] if len(sys.argv) > 2 else None
        mgr.download_all(symbols)
    elif cmd == "update":
        mgr.incremental_update()
    elif cmd == "status":
        rows = mgr.get_sync_summary()
        if not rows:
            print("  (暂无同步记录)")
        else:
            print(f"  {'代码':<8} {'状态':<12} {'上次同步':<12} {'天数':<6} {'数据行数':<8}")
            print("  " + "-" * 50)
            for s in rows:
                days = s['days_ago'] if s['days_ago'] else 0
                status_icon = "✓" if s['status'] == "completed" else "✗" if s['status'] == "error" else "⊘"
                print(f"  {status_icon} {s['symbol']:<6} {s['status']:<12} {s['last_sync_date'] or '-':<12} {days:<6} {s['total_rows']:<8}")
    elif cmd == "missing":
        missing = mgr.get_missing_symbols()
        print(f"  缺少数据的股票: {len(missing)} 只")
        if missing:
            print(f"  {', '.join(missing[:20])}" + ("..." if len(missing) > 20 else ""))
    elif cmd == "test":
        if len(sys.argv) < 3:
            print("用法: test <symbol>")
            sys.exit(1)
        symbol = sys.argv[2]
        print(f"测试下载 {symbol}...")
        success, rows, err = mgr.lazy_download_one(symbol)
        if success:
            print(f"✓ 成功: {rows} 行")
        else:
            print(f"✗ 失败: {err}")
    else:
        print(f"未知命令: {cmd}")
