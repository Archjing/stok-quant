import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { listStocks, getStockDaily } from '../api'

export default function StockList() {
  const { t } = useTranslation()
  const [stocks, setStocks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [daily, setDaily] = useState<any[]>([])
  const [detail, setDetail] = useState<any>(null)

  useEffect(() => {
    setLoading(true)
    listStocks({ limit: 100 })
      .then((res: any) => setStocks(res?.data || []))
      .finally(() => setLoading(false))
  }, [])

  const selectStock = async (symbol: string) => {
    setSelected(symbol)
    const [dailyRes] = await Promise.all([
      getStockDaily(symbol, { years: 1, indicators: true }),
    ])
    const d = dailyRes as any
    setDaily(d?.data?.slice(-60).reverse() || [])
    setDetail(d)
  }

  if (loading) return <div className="loading">{t('stocks.loading')}</div>

  return (
    <div style={{ display: 'flex', gap: 20, height: 'calc(100vh - 140px)' }}>
      {/* Stock list */}
      <div style={{ flex: 1, maxWidth: 400, display: 'flex', flexDirection: 'column' }}>
        <div className="card table-card" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div className="card-header">
            <div className="card-title">{t('stocks.title')}</div>
          </div>
          <div className="table-scroll" style={{ flex: 1 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('stocks.symbol')}</th>
                  <th>{t('stocks.name')}</th>
                  <th>{t('stocks.price')}</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map((s: any) => (
                  <tr
                    key={s.symbol}
                    onClick={() => selectStock(s.symbol)}
                    style={{
                      cursor: 'pointer',
                      background: selected === s.symbol ? 'var(--bg-active)' : undefined,
                    }}
                  >
                    <td className="mono" style={{ color: selected === s.symbol ? 'var(--selected)' : 'var(--accent)' }}>{s.symbol}</td>
                    <td style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: selected === s.symbol ? 'var(--selected)' : undefined }}>
                      {s.name || '-'}
                    </td>
                    <td className="mono">${s.price?.toFixed(2) || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Detail panel */}
      <div style={{ flex: 2, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {!selected ? (
          <div className="empty-state">
            <h3>{t('stocks.selectStock')}</h3>
            <p>{t('stocks.selectStockDesc')}</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            <div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr 2fr', marginBottom: 16 }}>
              <div className="stat-card">
                <div className="stat-label">{t('stocks.symbol')}</div>
                <div className="stat-value accent">{selected}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">{t('stocks.close')}</div>
                <div className="stat-value">{daily.length > 0 ? `$${daily[daily.length-1]?.close?.toFixed(2)}` : '-'}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">{t('stocks.volume')}</div>
                <div className="stat-value">
                  {daily.length > 0 ? (daily[daily.length-1]?.volume / 1e6).toFixed(1) + 'M' : '-'}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">{t('stocks.dataRange')}</div>
                <div className="stat-value">
                  {detail?.start_date || '-'} ~ {detail?.end_date || '-'}
                </div>
              </div>
            </div>

            <div className="card table-card" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
              <div className="card-header">
                <div className="card-title">{t('stocks.recentPriceHistory')}</div>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('stocks.lastDays')}</span>
              </div>
              <div className="table-scroll" style={{ flex: 1 }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>{t('stocks.date')}</th>
                      <th>{t('stocks.open')}</th>
                      <th>{t('stocks.high')}</th>
                      <th>{t('stocks.low')}</th>
                      <th>{t('stocks.close')}</th>
                      <th>{t('stocks.volume')}</th>
                      <th>{t('stocks.rsi')}</th>
                      <th>{t('stocks.sma')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {daily.slice(0, 30).map((d: any, i: number) => (
                      <tr key={i}>
                        <td className="mono" style={{ fontSize: 12 }}>{d.date}</td>
                        <td className="mono">${d.open?.toFixed(2)}</td>
                        <td className="mono">${d.high?.toFixed(2)}</td>
                        <td className="mono">${d.low?.toFixed(2)}</td>
                        <td className="mono" style={{ fontWeight: 500 }}>${d.close?.toFixed(2)}</td>
                        <td className="mono">{(d.volume / 1e6).toFixed(1)}M</td>
                        <td className="mono">{d.rsi_14 ? d.rsi_14.toFixed(1) : '-'}</td>
                        <td className="mono">{d.sma_20 ? `$${d.sma_20.toFixed(2)}` : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
