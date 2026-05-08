import sys
sys.path.insert(0, 'd:/ZJ/Dev/Python_Projects/014_stock-us')

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
