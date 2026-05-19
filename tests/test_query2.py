"""测试 DataManager"""
import sys
import os
from pathlib import Path

# 动态获取项目根目录
_project_root = Path(__file__).parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

from backend.database import SessionLocal
from backend.models.stock import USStockDaily
from datetime import date, timedelta

try:
    print("1. Creating DataManager...")
    from backend.data_manager import DataManager
    mgr = DataManager()
    print("   DataManager created!")
    
    print("\n2. Calling get_daily_from_db...")
    result = mgr.get_daily_from_db('AAPL', 5)
    print(f"   Result: {result}")
    print(f"   Type: {type(result)}")
    if result:
        print(f"   Length: {len(result)}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
