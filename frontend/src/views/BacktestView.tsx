import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { runBacktest, compareStrategies, listStrategies } from '../api'
import { TrendingUp, Play, BarChart3 } from 'lucide-react'

const ALL_SYMBOLS = [
  "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "SPY", "QQQ"
]

const STRATEGIES = {
  sma_crossover: { en: 'SMA Crossover', zh: '均线交叉' },
  rsi_mean_reversion: { en: 'RSI Mean Reversion', zh: 'RSI均值回归' },
  macd: { en: 'MACD Trend', zh: 'MACD趋势' },
  buy_and_hold: { en: 'Buy & Hold', zh: '买入持有' },
}

export default function BacktestView() {
  const { t, i18n } = useTranslation()
  const isZh = i18n.language === 'zh'
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

  const getStrategyName = (id: string) => {
    return isZh ? STRATEGIES[id as keyof typeof STRATEGIES]?.zh : STRATEGIES[id as keyof typeof STRATEGIES]?.en || id
  }

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
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 20 }}>{t('backtest.title')}</h2>

      {/* Controls */}
      <div className="card">
        <div style={{ display: 'flex', gap: 16, alignItems: 'end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ minWidth: 140 }}>
            <label className="form-label">{t('backtest.symbol')}</label>
            <select className="form-select" value={symbol} onChange={e => setSymbol(e.target.value)}>
              {ALL_SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="form-group" style={{ minWidth: 160 }}>
            <label className="form-label">{t('backtest.strategy')}</label>
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

      {/* Compare mode */}
      {compareResult && (
        <div className="card table-card">
          <div className="card-header">
            <div className="card-title">{t('backtest.strategyComparison')} - {compareResult.symbol}</div>
          </div>
          <div className="table-scroll">
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

      {/* Single result */}
      {result && result.results && (
        <>
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

          <div className="card table-card">
            <div className="card-header">
              <div className="card-title">{t('backtest.tradeLog')}</div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {result.results.total_trades} {t('backtest.tradeCount')}
              </span>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>{t('backtest.side')}</th>
                    <th>{t('backtest.qty')}</th>
                    <th>{t('backtest.symbol')}</th>
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
        </>
      )}

      {!result && !compareResult && (
        <div className="empty-state">
          <TrendingUp size={48} />
          <h3>{t('backtest.runBacktestPrompt')}</h3>
          <p>{t('backtest.runBacktestPromptDesc')}</p>
        </div>
      )}
    </div>
  )
}
