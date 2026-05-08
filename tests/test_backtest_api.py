"""模拟后端环境测试"""
import sys
import os
# 模拟后端启动时的工作目录
os.chdir('d:/ZJ/Dev/Python_Projects/014_stock-us')
sys.path.insert(0, 'd:/ZJ/Dev/Python_Projects/014_stock-us')

print(f"Working dir: {os.getcwd()}")
print(f"DB path: d:/ZJ/Dev/Python_Projects/014_stock-us/data/us_stocks.db")
print(f"DB exists: {os.path.exists('data/us_stocks.db')}")

# 测试导入
from backend.data_manager import DataManager
from backend.crawlers.data_cleaner import USDataCleaner

print("\n1. Creating DataManager (like backend startup)...")
data_mgr = DataManager()
print("   DataManager created!")

print("\n2. Testing get_daily_from_db...")
db_rows = data_mgr.get_daily_from_db('AAPL', years=5)
print(f"   db_rows: {db_rows}")
print(f"   bool(db_rows): {bool(db_rows)}")
print(f"   len(db_rows) >= 20: {len(db_rows) >= 20 if db_rows else False}")

if db_rows and len(db_rows) >= 20:
    print("\n3. Testing clean_daily_data_from_db_rows...")
    df = USDataCleaner.clean_daily_data_from_db_rows(db_rows)
    print(f"   df shape: {df.shape}")
    print(f"   df columns: {list(df.columns)}")
else:
    print("\n   Skipping clean_daily_data_from_db_rows (no data)")
