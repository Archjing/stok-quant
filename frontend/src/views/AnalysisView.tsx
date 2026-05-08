import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Activity } from 'lucide-react'
import { getStockDaily } from '../api'

const ALL_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "SPY"]

export default function AnalysisView() {
  const { t } = useTranslation()
  const [symbol, setSymbol] = useState('AAPL')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<any[]>([])

  const loadData = async () => {
    setLoading(true)
    const res = await getStockDaily(symbol, { years: 2, indicators: true }) as any
    setData(res?.data?.slice(-120).reverse() || [])
    setLoading(false)
  }

  const latest = data[data.length - 1] || {}

  const indicators = [
    { label: 'RSI(14)', value: latest.rsi_14, warn: (v: number) => v > 70 || v < 30 },
    { label: 'MACD', value: latest.macd, fmt: (v: number) => v?.toFixed(4) },
    { label: 'MACD Signal', value: latest.macd_signal, fmt: (v: number) => v?.toFixed(4) },
    { label: 'MACD Hist', value: latest.macd_hist, fmt: (v: number) => v?.toFixed(4) },
    { label: 'SMA(20)', value: latest.sma_20, fmt: (v: number) => `$${v?.toFixed(2)}` },
    { label: 'SMA(50)', value: latest.sma_50, fmt: (v: number) => `$${v?.toFixed(2)}` },
    { label: 'SMA(200)', value: latest.sma_200, fmt: (v: number) => `$${v?.toFixed(2)}` },
    { label: 'BB Upper', value: latest.bb_upper, fmt: (v: number) => `$${v?.toFixed(2)}` },
    { label: 'BB Lower', value: latest.bb_lower, fmt: (v: number) => `$${v?.toFixed(2)}` },
    { label: 'ATR(14)', value: latest.atr_14, fmt: (v: number) => `$${v?.toFixed(2)}` },
  ]

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 20 }}>{t('analysis.title')}</h2>

      {/* Controls */}
      <div className="card">
        <div style={{ display: 'flex', gap: 16, alignItems: 'end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ minWidth: 140 }}>
            <label className="form-label">{t('stocks.symbol')}</label>
            <select className="form-select" value={symbol} onChange={e => setSymbol(e.target.value)}>
              {ALL_SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">&nbsp;</label>
            <button className="btn btn-primary" onClick={loadData} disabled={loading}>
              {loading ? t('common.loading') : t('analysis.loadAnalysis')}
            </button>
          </div>
        </div>
      </div>

      {data.length > 0 && (
        <>
          {/* Price & Signal */}
          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            <div className="stat-card">
              <div className="stat-label">{t('analysis.currentPrice')}</div>
              <div className="stat-value accent">${latest.close?.toFixed(2)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">{t('analysis.signal')}</div>
              <div className={`stat-value ${
                latest.close > latest.sma_50 ? 'positive' : 'negative'
              }`}>
                {latest.close > latest.sma_50 ? t('analysis.bullish') : t('analysis.bearish')}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">{t('analysis.rsiStatus')}</div>
              <div className={`stat-value ${
                latest.rsi_14 > 70 ? 'negative' : latest.rsi_14 < 30 ? 'positive' : ''
              }`}>
                {latest.rsi_14 > 70 ? t('analysis.overbought') : latest.rsi_14 < 30 ? t('analysis.oversold') : t('analysis.neutral')}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">{t('stocks.volume')}</div>
              <div className="stat-value">
                {latest.volume ? `${(latest.volume / 1e6).toFixed(1)}M` : '-'}
              </div>
            </div>
          </div>

          {/* Indicators */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">{t('analysis.technicalIndicators')}</div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {t('analysis.lastUpdated')}: {latest.date}
              </span>
            </div>
            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
              {indicators.map(ind => (
                <div key={ind.label} className="stat-card" style={{ padding: 12 }}>
                  <div className="stat-label">{ind.label}</div>
                  <div className={`stat-value ${ind.value && ind.warn?.(ind.value) ? 'negative' : ''}`}>
                    {ind.value != null
                      ? (ind.fmt ? ind.fmt(ind.value) : ind.value.toFixed(2))
                      : '-'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Price table */}
          <div className="card table-card">
            <div className="card-header">
              <div className="card-title">{t('analysis.recentData')}</div>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>{t('stocks.date')}</th>
                    <th>{t('stocks.close')}</th>
                    <th>{t('stocks.rsi')}</th>
                    <th>MACD</th>
                    <th>SMA(20)</th>
                    <th>SMA(50)</th>
                    <th>{t('stocks.volume')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.slice(-30).map((d: any, i: number) => (
                    <tr key={i}>
                      <td className="mono" style={{ fontSize: 12 }}>{d.date}</td>
                      <td className="mono" style={{ fontWeight: 500 }}>${d.close?.toFixed(2)}</td>
                      <td className={`mono ${d.rsi_14 > 70 ? 'metric-negative' : d.rsi_14 < 30 ? 'metric-positive' : ''}`}>
                        {d.rsi_14?.toFixed(1) || '-'}
                      </td>
                      <td className={`mono ${(d.macd_hist || 0) > 0 ? 'metric-positive' : 'metric-negative'}`}>
                        {d.macd?.toFixed(4) || '-'}
                      </td>
                      <td className="mono">{d.sma_20 ? `$${d.sma_20.toFixed(2)}` : '-'}</td>
                      <td className="mono">{d.sma_50 ? `$${d.sma_50.toFixed(2)}` : '-'}</td>
                      <td className="mono">{d.volume ? `${(d.volume / 1e6).toFixed(1)}M` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {data.length === 0 && (
        <div className="empty-state">
          <Activity size={48} />
          <h3>{t('analysis.loadAnalysisData')}</h3>
          <p>{t('analysis.loadAnalysisDataDesc')}</p>
        </div>
      )}
    </div>
  )
}
