import { useState } from 'react'
import { runBacktest, compareStrategies, listStrategies } from '../api'
import { TrendingUp, Play, BarChart3 } from 'lucide-react'

const ALL_SYMBOLS = [
  "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "SPY", "QQQ"
]

export default function BacktestView() {
  const [symbol, setSymbol] = useState('AAPL')
  const [strategy, setStrategy] = useState('sma_crossover')
  const [years, setYears] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [compareResult, setCompareResult] = useState<any>(null)

  const run = async () => {
    setLoading(true)
    try {
      if (compareMode) {
        const res = await compareStrategies({ symbol, years })
        setCompareResult(res as any)
        setResult(null)
      } else {
        const res = await runBacktest({ symbol, strategy, years })
        setResult(res as any)
        setCompareResult(null)
      }
    } finally {
      setLoading(false)
    }
  }

  const formatPct = (v: number) => v?.toFixed(2) + '%'
  const formatRatio = (v: number) => v?.toFixed(4) || '-'

  const MetricCard = ({ label, value, positive }: { label: string; value: string; positive?: boolean }) => (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${value.startsWith('-') ? 'negative' : 'positive'}`}>
        {value}
      </div>
    </div>
  )

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 20 }}>Backtest Engine</h2>

      {/* Controls */}
      <div className="card">
        <div style={{ display: 'flex', gap: 16, alignItems: 'end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ minWidth: 140 }}>
            <label className="form-label">Symbol</label>
            <select className="form-select" value={symbol} onChange={e => setSymbol(e.target.value)}>
              {ALL_SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="form-group" style={{ minWidth: 160 }}>
            <label className="form-label">Strategy</label>
            <select className="form-select" value={strategy} onChange={e => setStrategy(e.target.value)}>
              <option value="sma_crossover">SMA Crossover</option>
              <option value="rsi_mean_reversion">RSI Mean Reversion</option>
              <option value="macd">MACD Trend</option>
              <option value="buy_and_hold">Buy & Hold</option>
            </select>
          </div>

          <div className="form-group" style={{ width: 80 }}>
            <label className="form-label">Years</label>
            <input className="form-input" type="number" min={1} max={20}
              value={years} onChange={e => setYears(Number(e.target.value))} />
          </div>

          <div className="form-group">
            <label className="form-label">&nbsp;</label>
            <button className="btn btn-primary" onClick={run} disabled={loading}>
              <Play size={14} />
              {loading ? 'Running...' : compareMode ? 'Compare All' : 'Run Backtest'}
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">&nbsp;</label>
            <button
              className={`btn ${compareMode ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setCompareMode(!compareMode)}
            >
              <BarChart3 size={14} />
              {compareMode ? 'Single Strategy' : 'Compare All'}
            </button>
          </div>
        </div>
      </div>

      {/* Compare mode */}
      {compareResult && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">Strategy Comparison - {compareResult.symbol}</div>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Return</th>
                <th>Sharpe</th>
                <th>Max DD</th>
                <th>Trades</th>
              </tr>
            </thead>
            <tbody>
              {compareResult.strategies && Object.entries(compareResult.strategies).map(([id, s]: [string, any]) => (
                <tr key={id}>
                  <td style={{ color: 'var(--accent)' }}>{id}</td>
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
      )}

      {/* Single result */}
      {result && result.results && (
        <>
          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
            <MetricCard label="Total Return" value={formatPct(result.results.total_return_pct)} />
            <MetricCard label="Annualized Return" value={formatPct(result.results.annualized_return)} />
            <MetricCard label="Sharpe Ratio" value={formatRatio(result.results.sharpe_ratio)} />
            <MetricCard label="Sortino Ratio" value={formatRatio(result.results.sortino_ratio)} />
            <MetricCard label="Calmar Ratio" value={formatRatio(result.results.calmar_ratio)} />
            <MetricCard label="Max Drawdown" value={formatPct(result.results.max_drawdown_pct)} />
            <MetricCard label="Volatility" value={formatPct(result.results.volatility)} />
            <MetricCard label="Win Rate" value={formatPct(result.results.win_rate)} />
            <MetricCard label="Total Trades" value={String(result.results.total_trades || 0)} />
            <MetricCard label="End Cash" value={`$${(result.results.end_cash || 0).toLocaleString()}`} />
          </div>

          <div className="card">
            <div className="card-header">
              <div className="card-title">Trade Log</div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {result.results.total_trades} trades
              </span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Side</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>PnL</th>
                  <th>Tag</th>
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
        </>
      )}

      {!result && !compareResult && (
        <div className="empty-state">
          <TrendingUp size={48} />
          <h3>Run a backtest</h3>
          <p>Select a symbol and strategy, then click "Run Backtest" to see results</p>
        </div>
      )}
    </div>
  )
}
