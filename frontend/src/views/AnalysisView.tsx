import { useEffect, useMemo, useRef, useState } from "react";

import { useTranslation } from "react-i18next";
import { Activity } from "lucide-react";
import { getStockDaily, listStocks, MARKETS, type MarketCode } from "../api";

const DEFAULT_SYMBOLS: Record<MarketCode, string> = {
  US: "AAPL",
  CN: "SH.600519",
  HK: "HK.00700",
};

const getCurrencyForMarket = (market: MarketCode) =>
  MARKETS.find((m) => m.code === market)?.currency || "USD";

const toNumber = (value: unknown): number | null => {
  if (value == null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export default function AnalysisView() {
  const { t } = useTranslation();
  const [market, setMarket] = useState<MarketCode>("US");
  const [symbol, setSymbol] = useState("AAPL");
  const [currency, setCurrency] = useState("USD");
  const [stocks, setStocks] = useState<any[]>([]);
  const [stockQuery, setStockQuery] = useState("");
  const [effectiveQuery, setEffectiveQuery] = useState("");
  const [stocksLoading, setStocksLoading] = useState(false);

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const searchSeqRef = useRef(0);

  const loadStocks = async (query = "") => {
    const requestId = ++searchSeqRef.current;
    setStocksLoading(true);
    setCurrency(getCurrencyForMarket(market));

    try {
      const res = (await listStocks({
        limit: 500,
        market,
        search: query.trim() || undefined,
      })) as any;
      if (requestId !== searchSeqRef.current) return;

      const nextStocks = res?.data || [];
      setStocks(nextStocks);
      setEffectiveQuery(query);
      setCurrency(res?.currency || getCurrencyForMarket(market));

      if (nextStocks.length > 0) {
        const fallback = nextStocks.find(
          (s: any) => s.symbol === DEFAULT_SYMBOLS[market],
        );
        setSymbol((current) => {
          if (nextStocks.some((s: any) => s.symbol === current)) {
            return current;
          }
          return fallback?.symbol || nextStocks[0].symbol;
        });
      } else if (!query.trim()) {
        setSymbol(DEFAULT_SYMBOLS[market]);
      }
    } catch (error) {
      if (requestId !== searchSeqRef.current) return;
      console.error("Failed to load analysis stocks:", error);
      setStocks([]);
      setEffectiveQuery(query);
      if (!query.trim()) {
        setSymbol(DEFAULT_SYMBOLS[market]);
      }
    } finally {
      if (requestId === searchSeqRef.current) {
        setStocksLoading(false);
      }
    }
  };

  useEffect(() => {
    setStockQuery("");
    setEffectiveQuery("");
    setData([]);
    loadStocks("");
  }, [market]);

  useEffect(() => {
    const handler = window.setTimeout(() => {
      if (stockQuery.trim() === effectiveQuery.trim()) return;
      loadStocks(stockQuery);
    }, 250);

    return () => window.clearTimeout(handler);
  }, [stockQuery, effectiveQuery, market]);

  const filteredStocks = stocks;

  const selectedStock = useMemo(
    () => stocks.find((s: any) => s.symbol === symbol),
    [stocks, symbol],
  );

  const formatMoney = (value?: number) => {
    const numeric = toNumber(value);
    if (numeric == null) return "-";
    const prefix = currency === "USD" ? "$" : currency === "CNY" ? "¥" : "HK$";
    return `${prefix}${numeric.toFixed(2)}`;
  };

  const formatFixed = (value: unknown, digits: number) => {
    const numeric = toNumber(value);
    return numeric == null ? "-" : numeric.toFixed(digits);
  };

  const formatVolume = (value: unknown) => {
    const numeric = toNumber(value);
    return numeric == null ? "-" : `${(numeric / 1e6).toFixed(1)}M`;
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const normalizedSymbol = selectedStock?.symbol || symbol;
      const res = (await getStockDaily(normalizedSymbol, {
        years: 2,
        indicators: true,
        market,
      })) as any;
      setSymbol(res?.symbol || normalizedSymbol);
      setCurrency(res?.currency || getCurrencyForMarket(market));
      setData(res?.data?.slice(-120).reverse() || []);
    } catch (error) {
      console.error("Failed to load analysis data:", error);
      setData([]);
      alert(`加载分析失败: ${symbol}`);
    } finally {
      setLoading(false);
    }
  };

  const latest = data[data.length - 1] || {};
  const latestClose = toNumber(latest.close);
  const latestSma50 = toNumber(latest.sma_50);
  const latestRsi14 = toNumber(latest.rsi_14);

  const indicators = [
    {
      label: "RSI(14)",
      value: latest.rsi_14,
      warn: (v: number) => v > 70 || v < 30,
    },
    { label: "MACD", value: latest.macd, fmt: (v: number) => v?.toFixed(4) },
    {
      label: "MACD Signal",
      value: latest.macd_signal,
      fmt: (v: number) => v?.toFixed(4),
    },
    {
      label: "MACD Hist",
      value: latest.macd_hist,
      fmt: (v: number) => v?.toFixed(4),
    },
    {
      label: "SMA(20)",
      value: latest.sma_20,
      fmt: (v: number) => formatMoney(v),
    },
    {
      label: "SMA(50)",
      value: latest.sma_50,
      fmt: (v: number) => formatMoney(v),
    },
    {
      label: "SMA(200)",
      value: latest.sma_200,
      fmt: (v: number) => formatMoney(v),
    },
    {
      label: "BB Upper",
      value: latest.bb_upper,
      fmt: (v: number) => formatMoney(v),
    },
    {
      label: "BB Lower",
      value: latest.bb_lower,
      fmt: (v: number) => formatMoney(v),
    },
    {
      label: "ATR(14)",
      value: latest.atr_14,
      fmt: (v: number) => formatMoney(v),
    },
  ];

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 20 }}>
        {t("analysis.title")}
      </h2>

      {/* Controls */}
      <div className="card">
        <div
          style={{
            display: "flex",
            gap: 16,
            alignItems: "end",
            flexWrap: "wrap",
          }}
        >
          <div className="form-group" style={{ minWidth: 120 }}>
            <label className="form-label">{t("common.market")}</label>
            <select
              className="form-select"
              value={market}
              onChange={(e) => setMarket(e.target.value as MarketCode)}
            >
              {MARKETS.map((m) => (
                <option key={m.code} value={m.code}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ minWidth: 260, flex: 1 }}>
            <label className="form-label">{t("stocks.symbol")}</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                className="form-input"
                value={stockQuery}
                onChange={(e) => setStockQuery(e.target.value)}
                placeholder={t("stocks.searchPlaceholder")}
              />
              <button
                className="btn btn-secondary"
                type="button"
                onClick={() => setStockQuery("")}
                disabled={!stockQuery}
                style={{ whiteSpace: "nowrap" }}
              >
                {t("common.clear")}
              </button>
            </div>
          </div>

          <div className="form-group" style={{ minWidth: 220 }}>
            <label className="form-label">{t("stocks.selectStock")}</label>
            <select
              className="form-select"
              value={
                filteredStocks.some((s: any) => s.symbol === symbol)
                  ? symbol
                  : ""
              }
              onChange={(e) => setSymbol(e.target.value)}
              disabled={stocksLoading || filteredStocks.length === 0}
            >
              {filteredStocks.length === 0 ? (
                <option value="">{t("stocks.noMatch")}</option>
              ) : (
                filteredStocks.map((s: any) => (
                  <option key={s.symbol} value={s.symbol}>
                    {s.symbol} {s.name ? `- ${s.name}` : ""}
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">&nbsp;</label>
            <button
              className="btn btn-primary"
              onClick={loadData}
              disabled={loading || stocksLoading || !symbol}
            >
              {loading ? t("common.loading") : t("analysis.loadAnalysis")}
            </button>
          </div>
        </div>

        <div
          style={{
            marginTop: 12,
            fontSize: 12,
            color: "var(--text-muted)",
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <span>
            {t("backtest.selectedStock")}: <strong>{symbol || "-"}</strong>
          </span>
          <span>{selectedStock?.name || "-"}</span>
          <span>
            {filteredStocks.length}/{stocks.length}
          </span>
        </div>

        {effectiveQuery && filteredStocks.length === 0 && !stocksLoading && (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              borderRadius: 8,
              background: "var(--bg-secondary)",
              color: "var(--text-muted)",
              fontSize: 13,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {t("stocks.noMatch")}
            </div>
            <div>“{effectiveQuery}”</div>
          </div>
        )}
      </div>

      {data.length > 0 && (
        <>
          {/* Price & Signal */}
          <div
            className="stats-grid"
            style={{ gridTemplateColumns: "repeat(4, 1fr)" }}
          >
            <div className="stat-card">
              <div className="stat-label">{t("analysis.currentPrice")}</div>
              <div className="stat-value accent">
                {formatMoney(latest.close)}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">{t("analysis.signal")}</div>
              <div
                className={`stat-value ${
                  latestClose != null && latestSma50 != null
                    ? latestClose > latestSma50
                      ? "positive"
                      : "negative"
                    : ""
                }`}
              >
                {latestClose != null && latestSma50 != null
                  ? latestClose > latestSma50
                    ? t("analysis.bullish")
                    : t("analysis.bearish")
                  : "-"}
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-label">{t("analysis.rsiStatus")}</div>
              <div
                className={`stat-value ${
                  latestRsi14 != null
                    ? latestRsi14 > 70
                      ? "negative"
                      : latestRsi14 < 30
                        ? "positive"
                        : ""
                    : ""
                }`}
              >
                {latestRsi14 != null
                  ? latestRsi14 > 70
                    ? t("analysis.overbought")
                    : latestRsi14 < 30
                      ? t("analysis.oversold")
                      : t("analysis.neutral")
                  : "-"}
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-label">{t("stocks.volume")}</div>
              <div className="stat-value">{formatVolume(latest.volume)}</div>
            </div>
          </div>

          {/* Indicators */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                {t("analysis.technicalIndicators")}
              </div>
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {t("analysis.lastUpdated")}: {latest.date}
              </span>
            </div>
            <div
              className="stats-grid"
              style={{ gridTemplateColumns: "repeat(5, 1fr)" }}
            >
              {indicators.map((ind) => (
                <div
                  key={ind.label}
                  className="stat-card"
                  style={{ padding: 12 }}
                >
                  <div className="stat-label">{ind.label}</div>
                  <div
                    className={`stat-value ${
                      toNumber(ind.value) != null &&
                      ind.warn?.(toNumber(ind.value) as number)
                        ? "negative"
                        : ""
                    }`}
                  >
                    {toNumber(ind.value) != null
                      ? ind.fmt
                        ? ind.fmt(toNumber(ind.value) as number)
                        : formatFixed(ind.value, 2)
                      : "-"}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Price table */}
          <div className="card table-card">
            <div className="card-header">
              <div className="card-title">{t("analysis.recentData")}</div>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{t("stocks.date")}</th>
                    <th>{t("stocks.close")}</th>
                    <th>{t("stocks.rsi")}</th>
                    <th>MACD</th>
                    <th>SMA(20)</th>
                    <th>SMA(50)</th>
                    <th>{t("stocks.volume")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.slice(-30).map((d: any, i: number) => {
                    const rowRsi14 = toNumber(d.rsi_14);
                    const rowMacd = toNumber(d.macd);
                    const rowMacdHist = toNumber(d.macd_hist);
                    return (
                      <tr key={i}>
                        <td className="mono" style={{ fontSize: 12 }}>
                          {d.date}
                        </td>
                        <td className="mono" style={{ fontWeight: 500 }}>
                          {formatMoney(d.close)}
                        </td>

                        <td
                          className={`mono ${
                            rowRsi14 != null
                              ? rowRsi14 > 70
                                ? "metric-negative"
                                : rowRsi14 < 30
                                  ? "metric-positive"
                                  : ""
                              : ""
                          }`}
                        >
                          {formatFixed(d.rsi_14, 1)}
                        </td>

                        <td
                          className={`mono ${(rowMacdHist || 0) > 0 ? "metric-positive" : "metric-negative"}`}
                        >
                          {formatFixed(d.macd, 4)}
                        </td>

                        <td className="mono">
                          {d.sma_20 ? formatMoney(d.sma_20) : "-"}
                        </td>
                        <td className="mono">
                          {d.sma_50 ? formatMoney(d.sma_50) : "-"}
                        </td>

                        <td className="mono">{formatVolume(d.volume)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {data.length === 0 && (
        <div className="empty-state">
          <Activity size={48} />
          <h3>{t("analysis.loadAnalysisData")}</h3>
          <p>{t("analysis.loadAnalysisDataDesc")}</p>
        </div>
      )}
    </div>
  );
}
