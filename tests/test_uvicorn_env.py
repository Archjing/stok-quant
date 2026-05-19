"""模拟 uvicorn 启动环境"""
import sys
import os
from pathlib import Path

# 动态获取项目根目录
_project_root = Path(__file__).parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

# 模拟 uvicorn "uv run uvicorn backend.main:app" 启动
# uvicorn 会把启动命令的目录作为工作目录

print("=" * 50)
print("模拟 uvicorn 启动环境")
print("=" * 50)

# 1. 检查当前工作目录
print(f"\n1. Current working dir: {os.getcwd()}")

# 2. 检查 Python sys.path
print(f"\n2. sys.path[0] (first entry): {sys.path[0] if sys.path else 'empty'}")

# 3. 模拟 backend/__init__.py 的路径设置
# 如果 uvicorn 从 backend/ 目录启动，__file__ 会指向错误位置
# 但实际应该是从项目根目录启动

from backend.config import get_settings
settings = get_settings()
print(f"\n3. Config db_path: {settings.db_path}")

# 5. 检查数据库是否存在
db_abs_path = os.path.abspath(settings.db_path)
print(f"4. DB absolute path: {db_abs_path}")
print(f"5. DB exists: {os.path.exists(db_abs_path)}")

# 6. 检查 AAPL 数据
if os.path.exists(db_abs_path):
    import sqlite3
    conn = sqlite3.connect(db_abs_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM us_stock_daily WHERE symbol='AAPL'")
    count = cursor.fetchone()[0]
    print(f"6. AAPL rows: {count}")
    conn.close()

# 7. 测试 DataManager
print("\n7. Testing DataManager...")
from backend.data_manager import DataManager
mgr = DataManager()
result = mgr.get_daily_from_db('AAPL', years=5)
print(f"   get_daily_from_db result: {len(result) if result else 'None'} rows")

print("\n" + "=" * 50)
