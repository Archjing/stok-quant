import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error("[API Error]", err.message);
    return Promise.reject(err);
  },
);

// Stocks
export type MarketCode = "US" | "CN" | "HK";

export const MARKETS: { code: MarketCode; label: string; currency: string }[] =
  [
    { code: "US", label: "US 美股", currency: "USD" },
    { code: "CN", label: "CN A股", currency: "CNY" },
    { code: "HK", label: "HK 港股", currency: "HKD" },
  ];

export const listStocks = (params?: any) =>
  http.get("/api/stocks/", { params });
export const getSymbols = (params?: any) =>
  http.get("/api/stocks/symbols", { params });
export const getStockDetail = (symbol: string, params?: any) =>
  http.get(`/api/stocks/${symbol}`, { params });
export const getStockDaily = (symbol: string, params?: any) =>
  http.get(`/api/stocks/${symbol}/daily`, { params });
export const getStockKline = (symbol: string, params?: any) =>
  http.get(`/api/stocks/${symbol}/kline`, { params });
export const getStockFinancials = (symbol: string, params?: any) =>
  http.get(`/api/stocks/${symbol}/financials`, { params });
export const listSectors = () => http.get("/api/stocks/sectors/list");
export const getStockFilters = (params?: any) =>
  http.get("/api/stocks/filters", { params });

// Backtest
export const listStrategies = () => http.get("/api/backtest/strategies");
export const runBacktest = (params: any) =>
  http.post("/api/backtest/run", null, { params });
export const compareStrategies = (params: any) =>
  http.post("/api/backtest/compare", null, { params });

export const getDataSyncStatus = (params?: any) =>
  http.get("/api/data/status", { params });
export const triggerDataDownload = (params?: any) =>
  http.post("/api/data/download", null, { params });
export const triggerDataUpdate = (params?: any) =>
  http.post("/api/data/update", null, { params });
export const refreshMarketPrices = (params?: any) =>
  http.post("/api/data/refresh-prices", null, { params });
export const refreshStockList = (params?: any) =>
  http.post("/api/data/refresh-symbols", null, { params });
