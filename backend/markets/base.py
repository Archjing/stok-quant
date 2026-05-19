"""
多市场数据源抽象接口。

各市场数据源负责把外部数据标准化为项目内部统一格式：
- 股票列表：list[dict]
- 日线数据：标准 OHLCV DataFrame
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

import pandas as pd


class BaseMarketSource(ABC):
    """市场数据源基类。"""

    market: str
    currency: str

    @abstractmethod
    def get_stock_list(self) -> list[dict[str, Any]]:
        """获取市场股票列表。"""
        raise NotImplementedError

    @abstractmethod
    def get_stock_info(self, symbol: str) -> dict[str, Any] | None:
        """获取单只股票基础信息。"""
        raise NotImplementedError

    @abstractmethod
    def get_daily_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """获取标准化日线数据。日期格式为 YYYYMMDD。"""
        raise NotImplementedError

    def get_full_history(self, symbol: str, years: int = 10, adjust: str = "qfq") -> pd.DataFrame:
        """获取近 N 年历史日线。"""
        end = datetime.now()
        start = end - timedelta(days=years * 365)
        return self.get_daily_data(
            symbol=symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust=adjust,
        )

    @abstractmethod
    def normalize_daily_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """将外部接口返回数据标准化为内部 OHLCV DataFrame。"""
        raise NotImplementedError
