"""
A 股市场数据源。

数据源：AkShare
内部代码格式：SH.600519 / SZ.000001 / BJ.835185
数据源代码格式：600519 / 000001 / 835185
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from backend.crawlers.data_cleaner import USDataCleaner
from backend.markets.base import BaseMarketSource
from backend.markets.symbols import (
    detect_exchange,
    normalize_symbol,
    to_source_symbol,
)

logger = logging.getLogger(__name__)

CN_SAMPLE_STOCKS: list[dict[str, Any]] = [
    {"symbol": "SH.600519", "raw_symbol": "600519", "name": "贵州茅台", "exchange": "SH", "board": "主板", "industry": "白酒"},
    {"symbol": "SH.601318", "raw_symbol": "601318", "name": "中国平安", "exchange": "SH", "board": "主板", "industry": "保险"},
    {"symbol": "SH.600036", "raw_symbol": "600036", "name": "招商银行", "exchange": "SH", "board": "主板", "industry": "银行"},
    {"symbol": "SH.601899", "raw_symbol": "601899", "name": "紫金矿业", "exchange": "SH", "board": "主板", "industry": "贵金属"},
    {"symbol": "SH.600276", "raw_symbol": "600276", "name": "恒瑞医药", "exchange": "SH", "board": "主板", "industry": "化学制药"},
    {"symbol": "SH.600900", "raw_symbol": "600900", "name": "长江电力", "exchange": "SH", "board": "主板", "industry": "电力"},
    {"symbol": "SH.601088", "raw_symbol": "601088", "name": "中国神华", "exchange": "SH", "board": "主板", "industry": "煤炭"},
    {"symbol": "SH.600030", "raw_symbol": "600030", "name": "中信证券", "exchange": "SH", "board": "主板", "industry": "证券"},
    {"symbol": "SH.601398", "raw_symbol": "601398", "name": "工商银行", "exchange": "SH", "board": "主板", "industry": "银行"},
    {"symbol": "SH.601288", "raw_symbol": "601288", "name": "农业银行", "exchange": "SH", "board": "主板", "industry": "银行"},
    {"symbol": "SZ.000001", "raw_symbol": "000001", "name": "平安银行", "exchange": "SZ", "board": "主板", "industry": "银行"},
    {"symbol": "SZ.000858", "raw_symbol": "000858", "name": "五粮液", "exchange": "SZ", "board": "主板", "industry": "白酒"},
    {"symbol": "SZ.002594", "raw_symbol": "002594", "name": "比亚迪", "exchange": "SZ", "board": "主板", "industry": "汽车整车"},
    {"symbol": "SZ.000333", "raw_symbol": "000333", "name": "美的集团", "exchange": "SZ", "board": "主板", "industry": "家电"},
    {"symbol": "SZ.000651", "raw_symbol": "000651", "name": "格力电器", "exchange": "SZ", "board": "主板", "industry": "家电"},
    {"symbol": "SZ.002415", "raw_symbol": "002415", "name": "海康威视", "exchange": "SZ", "board": "主板", "industry": "计算机设备"},
    {"symbol": "SZ.300750", "raw_symbol": "300750", "name": "宁德时代", "exchange": "SZ", "board": "创业板", "industry": "电池"},
    {"symbol": "SZ.300760", "raw_symbol": "300760", "name": "迈瑞医疗", "exchange": "SZ", "board": "创业板", "industry": "医疗器械"},
    {"symbol": "SZ.300059", "raw_symbol": "300059", "name": "东方财富", "exchange": "SZ", "board": "创业板", "industry": "互联网金融"},
    {"symbol": "SZ.002475", "raw_symbol": "002475", "name": "立讯精密", "exchange": "SZ", "board": "主板", "industry": "消费电子"},
    {"symbol": "SH.688981", "raw_symbol": "688981", "name": "中芯国际", "exchange": "SH", "board": "科创板", "industry": "半导体"},
    {"symbol": "SH.688111", "raw_symbol": "688111", "name": "金山办公", "exchange": "SH", "board": "科创板", "industry": "软件开发"},
    {"symbol": "SH.688012", "raw_symbol": "688012", "name": "中微公司", "exchange": "SH", "board": "科创板", "industry": "半导体设备"},
    {"symbol": "BJ.430047", "raw_symbol": "430047", "name": "诺思兰德", "exchange": "BJ", "board": "北交所", "industry": "生物制品"},
    {"symbol": "BJ.835185", "raw_symbol": "835185", "name": "贝特瑞", "exchange": "BJ", "board": "北交所", "industry": "电池材料"},
]

_FIELD_MAP = {
    "日期": "date",
    "股票代码": "raw_symbol",
    "代码": "raw_symbol",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "振幅": "amplitude",
    "涨跌幅": "change_pct",
    "涨跌额": "change_amount",
    "换手率": "turnover_rate",
}


class CNMarketSource(BaseMarketSource):
    """A 股 AkShare 数据源。"""

    market = "CN"
    currency = "CNY"

    def get_stock_list(self) -> list[dict[str, Any]]:
        """获取 A 股股票列表。失败时返回内置样本池。"""
        try:
            ak = self._akshare()
            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                return self._sample_stock_list()
            return self._normalize_stock_list(df)
        except Exception as exc:
            logger.warning("获取 A 股列表失败，使用样本池: %s", exc)
            return self._sample_stock_list()

    def get_stock_info(self, symbol: str) -> dict[str, Any] | None:
        """获取单只 A 股基础信息。"""
        normalized = normalize_symbol(symbol, self.market)
        stocks = self.get_stock_list()
        for item in stocks:
            if item.get("symbol") == normalized:
                return item
        return {
            "market": self.market,
            "symbol": normalized,
            "raw_symbol": to_source_symbol(normalized, self.market),
            "name": normalized,
            "exchange": detect_exchange(normalized, self.market),
            "currency": self.currency,
            "country": "CN",
        }

    def get_daily_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """获取 A 股历史日线并标准化。"""
        normalized = normalize_symbol(symbol, self.market)
        raw_symbol = to_source_symbol(normalized, self.market)
        ak_adjust = "" if adjust in {"", "none", "None", None} else adjust
        ak = self._akshare()
        errors: list[str] = []

        candidates = [
            (
                "stock_zh_a_hist",
                lambda: ak.stock_zh_a_hist(
                    symbol=raw_symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=ak_adjust,
                    timeout=10,
                ),
            ),
            (
                "stock_zh_a_daily",
                lambda: ak.stock_zh_a_daily(
                    symbol=self._prefixed_source_symbol(normalized),
                    start_date=start_date,
                    end_date=end_date,
                    adjust=ak_adjust,
                ),
            ),
            (
                "stock_zh_a_hist_tx",
                lambda: ak.stock_zh_a_hist_tx(
                    symbol=self._prefixed_source_symbol(normalized),
                    start_date=start_date,
                    end_date=end_date,
                    adjust=ak_adjust,
                    timeout=10,
                ),
            ),
        ]

        for source_name, fetcher in candidates:
            try:
                df = fetcher()
                df = self.normalize_daily_dataframe(df)
                if df.empty:
                    errors.append(f"{source_name}: empty")
                    continue
                df["market"] = self.market
                df["symbol"] = normalized
                df["raw_symbol"] = raw_symbol
                df["data_source"] = source_name
                logger.info("A 股日线获取成功 %s via %s: %s 行", normalized, source_name, len(df))
                return df
            except Exception as exc:
                errors.append(f"{source_name}: {type(exc).__name__}: {exc}")
                logger.warning("A 股日线接口失败 %s via %s: %s", normalized, source_name, exc)

        logger.error("获取 A 股日线失败 %s: %s", normalized, " | ".join(errors))
        return pd.DataFrame()

    def normalize_daily_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """将 AkShare A 股日线字段标准化为 OHLCV。"""
        if df is None or df.empty:
            return pd.DataFrame()

        normalized = df.rename(columns={k: v for k, v in _FIELD_MAP.items() if k in df.columns}).copy()
        required = ["date", "open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in normalized.columns]
        if missing:
            logger.warning("A 股日线缺少必要字段: %s; columns=%s", missing, list(df.columns))
            return pd.DataFrame()

        normalized = USDataCleaner.clean_daily_data(normalized)

        numeric_cols = [
            "amount",
            "change_pct",
            "change_amount",
            "amplitude",
            "turnover_rate",
        ]
        for col in numeric_cols:
            if col in normalized.columns:
                normalized[col] = pd.to_numeric(normalized[col], errors="coerce")

        if "adjusted_close" not in normalized.columns:
            normalized["adjusted_close"] = normalized["close"]

        normalized = USDataCleaner.add_technical_indicators(normalized)
        normalized = normalized.sort_values("date").reset_index(drop=True)
        return normalized

    def _normalize_stock_list(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """标准化 AkShare A 股股票列表。"""
        code_col = self._find_col(df, ["code", "代码", "证券代码"])
        name_col = self._find_col(df, ["name", "名称", "证券简称", "股票简称"])
        if not code_col or not name_col:
            logger.warning("A 股列表字段不符合预期，使用样本池: %s", list(df.columns))
            return self._sample_stock_list()

        stocks: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            raw_code = str(row.get(code_col, "")).strip().zfill(6)
            if not raw_code or raw_code == "000000":
                continue
            try:
                symbol = normalize_symbol(raw_code, self.market)
            except Exception:
                continue
            exchange = detect_exchange(symbol, self.market)
            stocks.append({
                "market": self.market,
                "symbol": symbol,
                "raw_symbol": raw_code,
                "name": str(row.get(name_col, symbol)).strip(),
                "exchange": exchange,
                "board": self._detect_board(symbol),
                "sector": None,
                "industry": None,
                "area": None,
                "country": "CN",
                "currency": self.currency,
                "price": None,
                "change_pct": None,
                "market_cap": None,
                "pe_ratio": None,
                "pb_ratio": None,
                "dividend_yield": None,
                "turnover_rate": None,
            })
        return stocks or self._sample_stock_list()

    def _sample_stock_list(self) -> list[dict[str, Any]]:
        """返回内置 A 股样本池。"""
        return [
            {
                "market": self.market,
                "currency": self.currency,
                "country": "CN",
                "sector": None,
                "area": None,
                "price": None,
                "change_pct": None,
                "market_cap": None,
                "pe_ratio": None,
                "pb_ratio": None,
                "dividend_yield": None,
                "turnover_rate": None,
                **item,
            }
            for item in CN_SAMPLE_STOCKS
        ]

    @staticmethod
    def _detect_board(symbol: str) -> str | None:
        """根据代码识别 A 股板块。"""
        exchange, code = symbol.split(".", 1)
        if exchange == "BJ":
            return "北交所"
        if code.startswith("688"):
            return "科创板"
        if code.startswith(("300", "301")):
            return "创业板"
        return "主板"

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
        """在 DataFrame 中查找候选列名。"""
        lowered = {str(col).lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
            if candidate.lower() in lowered:
                return lowered[candidate.lower()]
        return None

    @staticmethod
    def _prefixed_source_symbol(symbol: str) -> str:
        """转换为 Sina/Tencent 常用带交易所前缀代码，如 sh600519。"""
        exchange, code = symbol.split(".", 1)
        return f"{exchange.lower()}{code}"

    @staticmethod
    def _akshare():
        """延迟导入 AkShare，避免影响不使用 CN/HK 的场景。"""
        import akshare as ak

        return ak
