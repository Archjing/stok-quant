"""
数据同步 API - 触发批量下载 / 增量更新 / 查看状态
"""
import logging
import threading
from fastapi import APIRouter, HTTPException

from backend.data_manager import DataManager

router = APIRouter(prefix="/api/data", tags=["Data Sync"])
logger = logging.getLogger(__name__)

_manager = DataManager(request_delay=0.6)
_sync_lock = threading.Lock()
_sync_running = False


@router.get("/status")
def sync_status():
    """查看各股票数据同步状态"""
    return {
        "running": _sync_running,
        "stocks": _manager.get_sync_summary(),
    }


@router.post("/download")
def trigger_download():
    """触发全量历史数据下载（后台异步执行）"""
    global _sync_running
    if _sync_running:
        raise HTTPException(400, "同步任务正在进行中")
    _sync_running = True

    def _run():
        global _sync_running
        try:
            _manager.download_all()
        finally:
            _sync_running = False

    threading.Thread(target=_run, daemon=True).start()
    return {"message": "全量下载已启动", "stocks": 81, "years": _manager.history_years}


@router.post("/update")
def trigger_update():
    """触发增量更新（后台异步执行）"""
    global _sync_running
    if _sync_running:
        raise HTTPException(400, "同步任务正在进行中")
    _sync_running = True

    def _run():
        global _sync_running
        try:
            _manager.incremental_update()
        finally:
            _sync_running = False

    threading.Thread(target=_run, daemon=True).start()
    return {"message": "增量更新已启动"}
