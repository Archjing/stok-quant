import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  res => res.data,
  err => { console.error('[API Error]', err.message); return Promise.reject(err) },
)

// Stocks
export const listStocks = (params?: any) => http.get('/api/stocks/', { params })
export const getSymbols = () => http.get('/api/stocks/symbols')
export const getStockDetail = (symbol: string) => http.get(`/api/stocks/${symbol}`)
export const getStockDaily = (symbol: string, params?: any) =>
  http.get(`/api/stocks/${symbol}/daily`, { params })
export const getStockFinancials = (symbol: string) =>
  http.get(`/api/stocks/${symbol}/financials`)
export const listSectors = () => http.get('/api/stocks/sectors/list')

// Backtest
export const listStrategies = () => http.get('/api/backtest/strategies')
export const runBacktest = (params: any) =>
  http.post('/api/backtest/run', null, { params })
export const compareStrategies = (params: any) =>
  http.post('/api/backtest/compare', null, { params })
