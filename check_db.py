"""检查数据库路径"""
import os
print(f"Current dir: {os.getcwd()}")

from backend.config import get_settings
settings = get_settings()
print(f"DB path from config: {settings.db_path}")
print(f"DB exists: {os.path.exists(settings.db_path)}")

# 检查实际使用的数据库
import sqlite3
conn = sqlite3.connect(settings.db_path)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM us_stock_daily WHERE symbol='AAPL'")
count = cursor.fetchone()[0]
print(f"AAPL rows in this DB: {count}")
conn.close()
