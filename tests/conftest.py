"""Pytest configuration for local repository imports."""

# Legacy / manual-debug scripts kept out of automated pytest collection.
collect_ignore_glob = [
    "test_backtest_api.py",
    "test_query.py",
    "test_query2.py",
    "test_offline.py",
    "test_uvicorn_env.py",
]

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
