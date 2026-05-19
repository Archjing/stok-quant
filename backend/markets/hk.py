"""
港股市场数据源。

数据源：AkShare
内部代码格式：HK.00700
数据源代码格式：00700
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from backend.crawlers.data_cleaner import USDataCleaner
from backend.markets.base import BaseMarketSource
from backend.markets.symbols import normalize_symbol, to_source_symbol

logger = logging.getLogger(__name__)

HK_SAMPLE_STOCKS: list[dict[str, Any]] = [
    {"symbol": "HK.00700", "raw_symbol": "00700", "name": "腾讯控股", "exchange": "HKEX", "board": "Main Board", "industry": "互联网"},
    {"symbol": "HK.09988", "raw_symbol": "09988", "name": "阿里巴巴-W", "exchange": "HKEX", "board": "Main Board", "industry": "互联网零售"},
    {"symbol": "HK.03690", "raw_symbol": "03690", "name": "美团-W", "exchange": "HKEX", "board": "Main Board", "industry": "生活服务"},
    {"symbol": "HK.01810", "raw_symbol": "01810", "name": "小米集团-W", "exchange": "HKEX", "board": "Main Board", "industry": "消费电子"},
    {"symbol": "HK.00005", "raw_symbol": "00005", "name": "汇丰控股", "exchange": "HKEX", "board": "Main Board", "industry": "银行"},
    {"symbol": "HK.00941", "raw_symbol": "00941", "name": "中国移动", "exchange": "HKEX", "board": "Main Board", "industry": "电信运营"},
    {"symbol": "HK.01299", "raw_symbol": "01299", "name": "友邦保险", "exchange": "HKEX", "board": "Main Board", "industry": "保险"},
    {"symbol": "HK.02318", "raw_symbol": "02318", "name": "中国平安", "exchange": "HKEX", "board": "Main Board", "industry": "保险"},
    {"symbol": "HK.01398", "raw_symbol": "01398", "name": "工商银行", "exchange": "HKEX", "board": "Main Board", "industry": "银行"},
    {"symbol": "HK.03988", "raw_symbol": "03988", "name": "中国银行", "exchange": "HKEX", "board": "Main Board", "industry": "银行"},
    {"symbol": "HK.00883", "raw_symbol": "00883", "name": "中国海洋石油", "exchange": "HKEX", "board": "Main Board", "industry": "油气开采"},
    {"symbol": "HK.00857", "raw_symbol": "00857", "name": "中国石油股份", "exchange": "HKEX", "board": "Main Board", "industry": "油气开采"},
    {"symbol": "HK.01024", "raw_symbol": "01024", "name": "快手-W", "exchange": "HKEX", "board": "Main Board", "industry": "互联网"},
    {"symbol": "HK.09618", "raw_symbol": "09618", "name": "京东集团-SW", "exchange": "HKEX", "board": "Main Board", "industry": "互联网零售"},
    {"symbol": "HK.09888", "raw_symbol": "09888", "name": "百度集团-SW", "exchange": "HKEX", "board": "Main Board", "industry": "互联网"},
    {"symbol": "HK.02020", "raw_symbol": "02020", "name": "安踏体育", "exchange": "HKEX", "board": "Main Board", "industry": "体育用品"},
    {"symbol": "HK.02331", "raw_symbol": "02331", "name": "李宁", "exchange": "HKEX", "board": "Main Board", "industry": "体育用品"},
    {"symbol": "HK.02269", "raw_symbol": "02269", "name": "药明生物", "exchange": "HKEX", "board": "Main Board", "industry": "生物科技"},
    {"symbol": "HK.00669", "raw_symbol": "00669", "name": "创科实业", "exchange": "HKEX", "board": "Main Board", "industry": "工业制造"},
    {"symbol": "HK.00388", "raw_symbol": "00388", "name": "香港交易所", "exchange": "HKEX", "board": "Main Board", "industry": "交易所"},
]

_FIELD_MAP = {
    "日期": "date",
    "时间": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "涨跌幅": "change_pct",
    "涨跌额": "change_amount",
    "振幅": "amplitude",
    "换手率": "turnover_rate",
    "代码": "raw_symbol",
    "股票代码": "raw_symbol",
}

_EN_FIELD_MAP = {
    "date": "date",
    "time": "date",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "amount": "amount",
    "turnover": "amount",
    "change_pct": "change_pct",
    "change_percent": "change_pct",
    "change": "change_amount",
    "amplitude": "amplitude",
}


class HKMarketSource(BaseMarketSource):
    """港股 AkShare 数据源。"""

    market = "HK"
    currency = "HKD"

    def get_stock_list(self) -> list[dict[str, Any]]:
        """获取港股股票列表。失败时返回内置样本池。"""
        try:
            ak = self._akshare()
            df = ak.stock_hk_spot_em()
            if df is None or df.empty:
                return self._sample_stock_list()
            return self._normalize_stock_list(df)
        except Exception as exc:
            logger.warning("获取港股列表失败，使用样本池: %s", exc)
            return self._sample_stock_list()

    def get_stock_info(self, symbol: str) -> dict[str, Any] | None:
        """获取单只港股基础信息。"""
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
            "exchange": "HKEX",
            "board": "Main Board",
            "currency": self.currency,
            "country": "HK",
        }

    def get_daily_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """获取港股历史日线并标准化。"""
        normalized = normalize_symbol(symbol, self.market)
        raw_symbol = to_source_symbol(normalized, self.market)
        ak_adjust = "" if adjust in {"", "none", "None", None} else adjust
        ak = self._akshare()
        errors: list[str] = []

        candidates = [
            (
                "stock_hk_hist",
                lambda: ak.stock_hk_hist(
                    symbol=raw_symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=ak_adjust,
                ),
            ),
            (
                "stock_hk_daily",
                lambda: self._filter_hk_daily(
                    ak.stock_hk_daily(symbol=raw_symbol, adjust=ak_adjust),
                    start_date=start_date,
                    end_date=end_date,
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
                logger.info("港股日线获取成功 %s via %s: %s 行", normalized, source_name, len(df))
                return df
            except Exception as exc:
                errors.append(f"{source_name}: {type(exc).__name__}: {exc}")
                logger.warning("港股日线接口失败 %s via %s: %s", normalized, source_name, exc)

        logger.error("获取港股日线失败 %s: %s", normalized, " | ".join(errors))
        return pd.DataFrame()

    def normalize_daily_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """将 AkShare 港股日线字段标准化为 OHLCV。"""
        if df is None or df.empty:
            return pd.DataFrame()

        rename_map: dict[Any, str] = {}
        for col in df.columns:
            col_str = str(col).strip()
            lower = col_str.lower().replace(" ", "_")
            if col_str in _FIELD_MAP:
                rename_map[col] = _FIELD_MAP[col_str]
            elif lower in _EN_FIELD_MAP:
                rename_map[col] = _EN_FIELD_MAP[lower]
        normalized = df.rename(columns=rename_map).copy()

        required = ["date", "open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in normalized.columns]
        if missing:
            logger.warning("港股日线缺少必要字段: %s; columns=%s", missing, list(df.columns))
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
        """标准化 AkShare 港股股票列表。"""
        code_col = self._find_col(df, ["代码", "证券代码", "股票代码", "code", "symbol"])
        name_col = self._find_col(df, ["名称", "证券简称", "股票简称", "name"])
        price_col = self._find_col(df, ["最新价", "最新", "现价", "price", "last"])
        change_col = self._find_col(df, ["涨跌幅", "change_pct", "change_percent"])
        if not code_col or not name_col:
            logger.warning("港股列表字段不符合预期，使用样本池: %s", list(df.columns))
            return self._sample_stock_list()

        stocks: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            raw_code = self._clean_hk_code(row.get(code_col))
            if not raw_code:
                continue
            try:
                symbol = normalize_symbol(raw_code, self.market)
            except Exception:
                continue
            stocks.append({
                "market": self.market,
                "symbol": symbol,
                "raw_symbol": to_source_symbol(symbol, self.market),
                "name": str(row.get(name_col, symbol)).strip(),
                "exchange": "HKEX",
                "board": "Main Board",
                "sector": None,
                "industry": None,
                "area": None,
                "country": "HK",
                "currency": self.currency,
                "price": self._to_float(row.get(price_col)) if price_col else None,
                "change_pct": self._to_float(row.get(change_col)) if change_col else None,
                "market_cap": None,
                "pe_ratio": None,
                "pb_ratio": None,
                "dividend_yield": None,
                "turnover_rate": None,
            })
        return stocks or self._sample_stock_list()

    def _sample_stock_list(self) -> list[dict[str, Any]]:
        """返回内置港股样本池。"""
        return [
            {
                "market": self.market,
                "currency": self.currency,
                "country": "HK",
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
            for item in HK_SAMPLE_STOCKS
        ]

    @staticmethod
    def _clean_hk_code(value: Any) -> str | None:
        """清洗港股代码并保留 5 位前导零。"""
        if value is None:
            return None
        raw = str(value).strip().upper().replace("HK", "").replace(".", "")
        if raw.endswith(".0"):
            raw = raw[:-2]
        if not raw.isdigit():
            return None
        return raw.zfill(5)

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
    def _to_float(value: Any) -> float | None:
        """安全转换浮点数。"""
        try:
            if value is None or value == "":
                return None
            parsed = float(value)
            if pd.isna(parsed):
                return None
            return parsed
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _filter_hk_daily(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
        """stock_hk_daily 不支持日期参数，这里在本地按日期过滤。"""
        if df is None or df.empty or "date" not in df.columns:
            return pd.DataFrame()
        result = df.copy()
        date_values = pd.to_datetime(result["date"])
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        return result[(date_values >= start) & (date_values <= end)]

    @staticmethod
    def _akshare():
        """延迟导入 AkShare，避免影响不使用 CN/HK 的场景。"""
        import akshare as ak

        return ak
