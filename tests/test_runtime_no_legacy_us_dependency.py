"""Regression test: backend runtime no longer depends on legacy US data manager path."""

from __future__ import annotations

from pathlib import Path


def test_backend_runtime_no_longer_imports_legacy_us_data_manager() -> None:
    backend_root = Path("backend")
    runtime_files = [
        backend_root / "main.py",
        backend_root / "market_data_manager.py",
        backend_root / "routers" / "stocks.py",
        backend_root / "routers" / "backtest.py",
        backend_root / "routers" / "data_sync.py",
    ]

    legacy_markers = [
        "from backend.data_manager import",
        "USStockDaily",
        "USStock(",
        "DataSyncStatus(",
    ]

    for path in runtime_files:
        content = path.read_text(encoding="utf-8")
        for marker in legacy_markers:
            assert marker not in content, f"legacy marker {marker!r} still found in {path}"
