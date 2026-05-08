"""直接测试后端API - 模拟uvicorn环境"""
import sys
import os

# 模拟 uvicorn 从项目根目录启动
os.chdir('d:/ZJ/Dev/Python_Projects/014_stock-us')
sys.path.insert(0, 'd:/ZJ/Dev/Python_Projects/014_stock-us')

from backend.config import get_settings
print(f"Settings DB path: {get_settings().db_path}")

# 导入并测试整个流程
from backend.routers.backtest import _get_backtest_data, data_mgr

print("\nTesting _get_backtest_data('AAPL', 5)...")
try:
    df, source, err = _get_backtest_data('AAPL', 5)
    print(f"Success! source={source}, df.shape={df.shape if df is not None else None}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
