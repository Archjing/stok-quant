import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { runBacktest, compareStrategies } from '../api'
import { TrendingUp, Play, BarChart3 } from 'lucide-react'

const STRATEGIES = {
  sma_crossover: { en: 'SMA Crossover', zh: '均线交叉' },
  rsi_mean_reversion: { en: 'RSI Mean Reversion', zh: 'RSI均值回归' },
  macd: { en: 'MACD Trend', zh: 'MACD趋势' },
  buy_and_hold: { en: 'Buy & Hold', zh: '买入持有' },
}

interface FilterOptions {
  sectors: string[]
  exchanges: string[]
  indices: string[]
  market_cap_options: number[]
}

export default function BacktestView() {
  const { t, i18n } = useTranslation()
  const isZh = i18n.language === 'zh'
  const [stocks, setStocks] = useState<any[]>([])
  const [symbol, setSymbol] = useState('AAPL')
  const [strategy, setStrategy] = useState('sma_crossover')
  const [years, setYears] = useState(5)
  const [loading, setLoading] = useState(false)
  const [stocksLoading, setStocksLoading] = useState(true)
  const [result, setResult] = useState<any>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [compareResult, setCompareResult] = useState<any>(null)

  // Filter state
  const [filterType, setFilterType] = useState<string>('')
  const [filterValue, setFilterValue] = useState<string>('')
  const [customSymbols, setCustomSymbols] = useState<string>('')
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    sectors: [],
    exchanges: [],
    indices: [],
    market_cap_options: [],
  })



  // Fetch filter options and initial stocks
  useEffect(() => {
    const fetchFilters = async () => {
      try {
        const res = await fetch('/api/stocks/filters')
        const data = await res.json()
        setFilterOptions(data)
      } catch (e) {
        console.error('Failed to fetch filter options:', e)
      }
    }
    fetchFilters()
    loadStocks()
  }, [])

  const loadStocks = async () => {
    setStocksLoading(true)
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (filterType && filterValue) {
        params.set('filter_type', filterType)
        params.set('filter_value', filterValue)
      }
      const res = await fetch(`/api/stocks/?${params}`)
      const data = await res.json()
      setStocks(data.data || [])
      if (data.data?.length > 0 && !data.data.find((s: any) => s.symbol === symbol)) {
        setSymbol(data.data[0].symbol)
      }
    } catch (e) {
      console.error('Failed to load stocks:', e)
    } finally {
      setStocksLoading(false)
    }
  }

  const applyFilter = () => {
    if (filterType === 'custom') {
      loadCustomStocks()
    } else {
      loadStocks()
    }
  }

  const loadCustomStocks = async () => {
    if (!customSymbols.trim()) return
    setStocksLoading(true)
    try {
      const params = new URLSearchParams({
        limit: '100',
        filter_type: 'custom',
        filter_value: customSymbols,
      })
      const res = await fetch(`/api/stocks/?${params}`)
      const data = await res.json()
      setStocks(data.data || [])
    } catch (e) {
      console.error('Failed to load custom stocks:', e)
    } finally {
      setStocksLoading(false)
    }
  }

  const getFilterTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      sector: t('backtest.bySector'),
      exchange: t('backtest.byExchange'),
      market_cap: t('backtest.byMarketCap'),
      index: t('backtest.byIndex'),
      custom: t('backtest.custom'),
    }
    return labels[type] || type
  }

  const run = async () => {
    setLoading(true)
    setResult(null)
    setCompareResult(null)
    try {
      if (compareMode) {
        const res = await compareStrategies({ symbol, years })
        console.log('Compare result:', res)
        setCompareResult(res)
      } else {
        const res = await runBacktest({ symbol, strategy, years })
        console.log('Backtest result:', res)
        setResult(res)
      }
    } catch (error: any) {
      console.error('Backtest error:', error)
      alert(`回测失败: ${error.message || '未知错误'}`)
    } finally {
      setLoading(false)
    }
  }

  const formatPct = (v: number) => v?.toFixed(2) + '%'
  const formatRatio = (v: number) => v?.toFixed(4) || '-'

  const getStrategyName = (id: string) => {
    return isZh ? STRATEGIES[id as keyof typeof STRATEGIES]?.zh : STRATEGIES[id as keyof typeof STRATEGIES]?.en || id
  }

  const MetricCard = ({ label, value }: { label: string; value: string }) => (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${value.startsWith('-') ? 'negative' : 'positive'}`}>
        {value}
      </div>
    </div>
  )

  return (
    <div style={{ height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Sticky Header: Title + Controls */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        background: 'var(--bg-primary)',
        paddingBottom: 12,
      }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 12 }}>{t('backtest.title')}</h2>
        <div style={{ display: 'flex', gap: 20, alignItems: 'stretch' }}>
          {/* Left: Filter Controls */}
          <div style={{ flex: '0 0 380px', display: 'flex', flexDirection: 'column' }}>
            <div className="card" style={{ padding: '12px 16px', flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', gap: 16, alignItems: 'end', flexWrap: 'wrap' }}>
                <div className="form-group" style={{ minWidth: 100 }}>
                  <label className="form-label">{t('backtest.stockFilter')}</label>
                  <select
                    className="form-select"
                    style={{ fontSize: 13 }}
                    value={filterType}
                    onChange={e => {
                      setFilterType(e.target.value)
                      setFilterValue('')
                      setCustomSymbols('')
                    }}
                  >
                    <option value="">{t('backtest.allStocks')}</option>
                    <option value="sector">{t('backtest.bySector')}</option>
                    <option value="exchange">{t('backtest.byExchange')}</option>
                    <option value="market_cap">{t('backtest.byMarketCap')}</option>
                    <option value="index">{t('backtest.byIndex')}</option>
                    <option value="custom">{t('backtest.custom')}</option>
                  </select>
                </div>

                {filterType === 'sector' && (
                  <div className="form-group" style={{ minWidth: 140 }}>
                    <label className="form-label">&nbsp;</label>
                    <select
                      className="form-select"
                      style={{ fontSize: 13 }}
                      value={filterValue}
                      onChange={e => setFilterValue(e.target.value)}
                    >
                      <option value="">{t('backtest.selectSector')}</option>
                      {filterOptions.sectors.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                )}

                {filterType === 'exchange' && (
                  <div className="form-group" style={{ minWidth: 100 }}>
                    <label className="form-label">&nbsp;</label>
                    <select
                      className="form-select"
                      style={{ fontSize: 13 }}
                      value={filterValue}
                      onChange={e => setFilterValue(e.target.value)}
                    >
                      <option value="">{t('backtest.selectExchange')}</option>
                      {filterOptions.exchanges.map(e => (
                        <option key={e} value={e}>{e}</option>
                      ))}
                    </select>
                  </div>
                )}

                {filterType === 'market_cap' && (
                  <div className="form-group" style={{ minWidth: 110 }}>
                    <label className="form-label">&nbsp;</label>
                    <select
                      className="form-select"
                      style={{ fontSize: 13 }}
                      value={filterValue}
                      onChange={e => setFilterValue(e.target.value)}
                    >
                      <option value="">{t('backtest.selectTop')}</option>
                      {filterOptions.market_cap_options.map(n => (
                        <option key={n} value={String(n)}>Top {n}</option>
                      ))}
                    </select>
                  </div>
                )}

                {filterType === 'index' && (
                  <div className="form-group" style={{ minWidth: 100 }}>
                    <label className="form-label">&nbsp;</label>
                    <select
                      className="form-select"
                      style={{ fontSize: 13 }}
                      value={filterValue}
                      onChange={e => setFilterValue(e.target.value)}
                    >
                      <option value="">{t('backtest.selectIndex')}</option>
                      {filterOptions.indices.map(idx => (
                        <option key={idx} value={idx}>{idx}</option>
                      ))}
                    </select>
                  </div>
                )}

                {filterType === 'custom' && (
                  <div className="form-group" style={{ flex: 1, minWidth: 120 }}>
                    <label className="form-label">&nbsp;</label>
                    <input
                      className="form-input"
                      style={{ fontSize: 13 }}
                      placeholder={t('backtest.customPlaceholder')}
                      value={customSymbols}
                      onChange={e => setCustomSymbols(e.target.value)}
                    />
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">&nbsp;</label>
                  <button
                    className="btn btn-primary"
                    style={{ padding: '6px 12px', fontSize: 13 }}
                    onClick={applyFilter}
                    disabled={!filterType || (filterType !== 'custom' && !filterValue) || (filterType === 'custom' && !customSymbols.trim())}
                  >
                    {t('common.applyFilter')}
                  </button>
                </div>
              </div>

              {filterType && filterValue && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
                  {getFilterTypeLabel(filterType)}: {filterValue}
                </div>
              )}
            </div>
          </div>

          {/* Right: Strategy Controls */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div className="card" style={{ padding: '12px 16px', flex: 1, display: 'flex', flexDirection: 'column' }}>
              {/* Selected Stock Indicator */}
              <div style={{ marginBottom: 12, padding: '8px 12px', background: 'rgba(0, 127, 255, 0.1)', borderRadius: 6, border: '1px solid var(--accent)' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('backtest.selectedStock') || 'Selected Stock'}: </span>
                <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>{symbol}</span>
                {stocks.find(s => s.symbol === symbol) && (
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 8 }}>
                    {stocks.find(s => s.symbol === symbol)?.name}
                  </span>
                )}
              </div>
              
              <div style={{ display: 'flex', gap: 16, alignItems: 'end', flexWrap: 'wrap' }}>
                <div className="form-group" style={{ minWidth: 160 }}>
                  <label className="form-label">{t('backtest.strategyControl')}</label>
                  <select className="form-select" value={strategy} onChange={e => setStrategy(e.target.value)}>
                    <option value="sma_crossover">{getStrategyName('sma_crossover')}</option>
                    <option value="rsi_mean_reversion">{getStrategyName('rsi_mean_reversion')}</option>
                    <option value="macd">{getStrategyName('macd')}</option>
                    <option value="buy_and_hold">{getStrategyName('buy_and_hold')}</option>
                  </select>
                </div>

                <div className="form-group" style={{ width: 80 }}>
                  <label className="form-label">{t('backtest.years')}</label>
                  <input className="form-input" type="number" min={1} max={20}
                    value={years} onChange={e => setYears(Number(e.target.value))} />
                </div>

                <div className="form-group">
                  <label className="form-label">&nbsp;</label>
                  <button className="btn btn-primary" onClick={run} disabled={loading}>
                    <Play size={14} />
                    {loading ? t('backtest.running') : compareMode ? t('backtest.compareAll') : t('backtest.runBacktest')}
                  </button>
                </div>

                <div className="form-group">
                  <label className="form-label">&nbsp;</label>
                  <button
                    className={`btn ${compareMode ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setCompareMode(!compareMode)}
                  >
                    <BarChart3 size={14} />
                    {compareMode ? t('backtest.singleStrategy') : t('backtest.compareAll')}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable Content */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', gap: 20, paddingRight: 8 }}>
        {/* Left: Stock List */}
        <div style={{ flex: '0 0 380px' }}>
          <div
            className="card table-card"
            style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <div className="table-scroll" style={{ flex: 1 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{t('stocks.symbol')}</th>
                    <th>{t('stocks.name')}</th>
                  </tr>
                </thead>
                <tbody>
                  {stocksLoading ? (
                    <tr>
                      <td colSpan={2} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 20 }}>
                        {t('common.loading')}...
                      </td>
                    </tr>
                  ) : stocks.map(s => (
                    <tr
                      key={s.symbol}
                      onClick={() => setSymbol(s.symbol)}
                      style={{
                        cursor: 'pointer',
                        background: symbol === s.symbol ? 'rgba(0, 127, 255, 0.15)' : undefined,
                        borderLeft: symbol === s.symbol ? '3px solid var(--accent)' : '3px solid transparent',
                      }}
                    >
                      <td className="mono" style={{ 
                        color: symbol === s.symbol ? 'var(--accent)' : 'var(--accent)',
                        fontWeight: symbol === s.symbol ? 700 : 400,
                      }}>{s.symbol}</td>
                      <td style={{
                        maxWidth: 180,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        color: symbol === s.symbol ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontWeight: symbol === s.symbol ? 600 : 400,
                      }}>
                        {s.name || s.symbol}
                      </td>
                    </tr>
                  ))}
                  {stocks.length === 0 && !stocksLoading && (
                    <tr>
                      <td colSpan={2} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 20 }}>
                        {t('common.noData')}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div style={{ padding: '8px 12px', fontSize: 11, color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)' }}>
              {stocks.length} {t('backtest.stocks')}
            </div>
          </div>
        </div>

        {/* Right: Results */}
        <div style={{ flex: 1 }}>
          {/* Sticky Metrics Panel */}
          <div style={{ position: 'sticky', top: 0, zIndex: 5, background: 'var(--bg-primary)' }}>
            {/* Compare mode */}
            {compareResult && (
              <div className="card table-card" style={{ marginBottom: 12 }}>
                <div className="card-header">
                  <div className="card-title">{t('backtest.strategyComparison')} - {compareResult.symbol}</div>
                </div>
                <div className="table-scroll" style={{ maxHeight: 200 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>{t('backtest.strategy')}</th>
                        <th>{t('backtest.return')}</th>
                        <th>{t('backtest.sharpe')}</th>
                        <th>{t('backtest.maxDD')}</th>
                        <th>{t('backtest.trades')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {compareResult.strategies && Object.entries(compareResult.strategies).map(([id, s]: [string, any]) => (
                        <tr key={id}>
                          <td style={{ color: 'var(--accent)' }}>{getStrategyName(id)}</td>
                          <td className={`mono ${s.total_return_pct > 0 ? 'metric-positive' : 'metric-negative'}`}>
                            {formatPct(s.total_return_pct)}
                          </td>
                          <td className={`mono ${s.sharpe_ratio > 1 ? 'metric-positive' : 'metric-neutral'}`}>
                            {formatRatio(s.sharpe_ratio)}
                          </td>
                          <td className="mono metric-negative">{formatPct(s.max_drawdown_pct)}</td>
                          <td className="mono">{s.total_trades}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Single result metrics */}
            {result && result.results && (
              <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
                <MetricCard label={t('backtest.totalReturn')} value={formatPct(result.results.total_return_pct)} />
                <MetricCard label={t('backtest.annualizedReturn')} value={formatPct(result.results.annualized_return)} />
                <MetricCard label={t('backtest.sharpeRatio')} value={formatRatio(result.results.sharpe_ratio)} />
                <MetricCard label={t('backtest.sortinoRatio')} value={formatRatio(result.results.sortino_ratio)} />
                <MetricCard label={t('backtest.calmarRatio')} value={formatRatio(result.results.calmar_ratio)} />
                <MetricCard label={t('backtest.maxDrawdown')} value={formatPct(result.results.max_drawdown_pct)} />
                <MetricCard label={t('backtest.volatility')} value={formatPct(result.results.volatility)} />
                <MetricCard label={t('backtest.winRate')} value={formatPct(result.results.win_rate)} />
                <MetricCard label={t('backtest.totalTrades')} value={String(result.results.total_trades || 0)} />
                <MetricCard label={t('backtest.endCash')} value={`$${(result.results.end_cash || 0).toLocaleString()}`} />
              </div>
            )}
          </div>

          {/* Trade Log Table */}
          {result && result.results && (
            <div className="card table-card" style={{ marginTop: 16 }}>
              <div className="card-header">
                <div className="card-title">{t('backtest.tradeLog')}</div>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {result.results.total_trades} {t('backtest.tradeCount')}
                </span>
              </div>
              <div className="table-scroll" style={{ maxHeight: 400 }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: 50 }}>#</th>
                      <th style={{ width: 80 }}>{t('backtest.side')}</th>
                      <th style={{ width: 80 }}>{t('backtest.qty')}</th>
                      <th style={{ width: 100 }}>{t('backtest.price')}</th>
                      <th>{t('backtest.pnl')}</th>
                      <th>{t('backtest.tag')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(result.trades || []).map((t: any, i: number) => (
                      <tr key={i}>
                        <td className="mono" style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
                        <td>
                          <span style={{
                            color: t.side === 'buy' ? 'var(--success)' : 'var(--danger)',
                            fontWeight: 500,
                          }}>
                            {t.side.toUpperCase()}
                          </span>
                        </td>
                        <td className="mono">{t.quantity}</td>
                        <td className="mono">${t.price?.toFixed(2)}</td>
                        <td className={`mono ${t.pnl > 0 ? 'metric-positive' : t.pnl < 0 ? 'metric-negative' : ''}`}>
                          {t.pnl ? `$${t.pnl.toFixed(2)}` : '-'}
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t.tag || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!result && !compareResult && (
            <div className="empty-state" style={{ marginTop: 40 }}>
              <TrendingUp size={48} />
              <h3>{t('backtest.runBacktestPrompt')}</h3>
              <p>{t('backtest.runBacktestPromptDesc')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
