import sys
sys.path.insert(0, 'd:/ZJ/Dev/Python_Projects/014_stock-us')

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
