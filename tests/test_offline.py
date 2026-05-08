"""测试离线场景 - 模拟断网时的数据库查询"""
import sys
import os
os.chdir('d:/ZJ/Dev/Python_Projects/014_stock-us')
sys.path.insert(0, 'd:/ZJ/Dev/Python_Projects/014_stock-us')

print("测试环境:")
print(f"  工作目录: {os.getcwd()}")
print(f"  Python: {sys.executable}")

# 测试1: 直接查询数据库（不依赖 DataManager）
print("\n测试1: 直接查询数据库")
from backend.database import SessionLocal
from backend.models.stock import USStockDaily
from datetime import date, timedelta

session = SessionLocal()
cutoff = date.today() - timedelta(days=5 * 365)
rows = session.query(USStockDaily).filter(
    USStockDaily.symbol == 'AAPL', 
    USStockDaily.date >= cutoff
).order_by(USStockDaily.date).all()
print(f"  AAPL 查询结果: {len(rows)} 行")
session.close()

# 测试2: 使用 DataManager（这里可能有网络依赖）
print("\n测试2: 使用 DataManager")
from backend.data_manager import DataManager
mgr = DataManager()
result = mgr.get_daily_from_db('AAPL', years=5)
print(f"  DataManager 结果: {len(result) if result else 'None'}")
