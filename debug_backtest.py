"""Debug backtest API"""
import sys
import os
from pathlib import Path

# 动态获取项目根目录
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

from backend.data_manager import DataManager
from backend.crawlers.data_cleaner import USDataCleaner

print("Creating DataManager...")
data_mgr = DataManager()
print("Done!")

print("\nTesting get_daily_from_db('AAPL', 5)...")
db_rows = data_mgr.get_daily_from_db('AAPL', years=5)
print(f"Result: {db_rows}")
print(f"Length: {len(db_rows) if db_rows else 0}")
