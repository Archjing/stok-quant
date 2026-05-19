"""测试数据库查询"""
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
    session = SessionLocal()
    print("Session created")
    
    symbol = 'AAPL'
    years = 5
    cutoff = date.today() - timedelta(days=years * 365)
    print(f'Cutoff: {cutoff}')
    
    rows = session.query(USStockDaily).filter(
        USStockDaily.symbol == symbol, 
        USStockDaily.date >= cutoff
    ).order_by(USStockDaily.date).all()
    print(f'Direct query: {len(rows)} rows')
    
    session.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
