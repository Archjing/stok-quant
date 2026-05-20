"""Regression tests for legacy retirement guardrails in phase 16.3 step 4."""

from __future__ import annotations

from pathlib import Path


LEGACY_DEBUG_SCRIPTS = {
    "test_backtest_api.py",
    "test_query.py",
    "test_query2.py",
    "test_offline.py",
    "test_uvicorn_env.py",
}


def test_conftest_excludes_legacy_debug_scripts_from_pytest_collection() -> None:
    content = Path("tests/conftest.py").read_text(encoding="utf-8")
    for script in LEGACY_DEBUG_SCRIPTS:
        assert script in content


def test_legacy_data_manager_is_marked_as_legacy() -> None:
    content = Path("backend/data_manager.py").read_text(encoding="utf-8")
    assert "Legacy US data manager" in content
    assert "不再用于 backend 主运行链路" in content
    assert "MarketDataManager" in content
