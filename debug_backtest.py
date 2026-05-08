"""Debug backtest API"""
import sys
sys.path.insert(0, 'd:/ZJ/Dev/Python_Projects/014_stock-us')

from backend.data_manager import DataManager
from backend.crawlers.data_cleaner import USDataCleaner

print("Creating DataManager...")
data_mgr = DataManager()
print("Done!")

print("\nTesting get_daily_from_db('AAPL', 5)...")
db_rows = data_mgr.get_daily_from_db('AAPL', years=5)
print(f"Result: {db_rows}")
print(f"Length: {len(db_rows) if db_rows else 0}")
