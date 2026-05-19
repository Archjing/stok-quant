"""直接测试后端API - 模拟uvicorn环境"""
import sys
import os
from pathlib import Path

# 动态获取项目根目录
_project_root = Path(__file__).parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

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
