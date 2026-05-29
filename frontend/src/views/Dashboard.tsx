import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { BarChart3, TrendingUp, DollarSign, Activity } from 'lucide-react'
import { getSymbols, listStrategies, MARKETS, MarketCode } from '../api'

export default function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    marketCounts: {} as Record<MarketCode, number>,
    totalStocks: 0,
    strategies: 0,
    lastUpdate: '',
  })

  useEffect(() => {

    Promise.all([
      Promise.all(MARKETS.map((item) => getSymbols({ market: item.code }))),
      listStrategies(),
    ]).then(([symbolsResponses, stratsResp]) => {
      const marketCounts = MARKETS.reduce((acc, item, index) => {
        const symData = symbolsResponses[index] as any
        acc[item.code] = symData?.total || 0
        return acc
      }, {} as Record<MarketCode, number>)
      const stratData = stratsResp as any
      setStats({
        marketCounts,
        totalStocks: Object.values(marketCounts).reduce((sum, count) => sum + count, 0),
        strategies: stratData?.strategies?.length || 0,
        lastUpdate: new Date().toLocaleTimeString(),
      })
    })
  }, [])


    const cards = [
    {

      label: t('dashboard.totalStocks'),
      value: stats.totalStocks,
      icon: BarChart3,
      color: 'accent',
      detail: MARKETS.map((item) => `${item.code}: ${(stats.marketCounts[item.code] || 0).toLocaleString()}`).join(' / '),
    },
    { label: t('dashboard.strategies'), value: stats.strategies, icon: TrendingUp, color: 'positive' },
    { label: t('dashboard.dataSource'), value: 'Yahoo + AkShare', icon: DollarSign, color: '' },
    { label: t('dashboard.lastUpdate'), value: stats.lastUpdate || '--', icon: Activity, color: '' },
  ]

  return (

    <div>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 20 }}>{t('dashboard.title')}</h2>

      <div className="stats-grid">
        {cards.map(c => (
                    <div key={c.label} className="stat-card">
            <div className="stat-label">{c.label}</div>
            <div className={`stat-value ${c.color}`}>
              {typeof c.value === 'number' ? c.value.toLocaleString() : c.value}

            </div>
            {c.detail ? (
              <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>{c.detail}</div>
            ) : null}
          </div>
        ))}

      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">{t('dashboard.quickStart')}</div>
        </div>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
          {[
            { title: t('dashboard.browseStocks'), desc: t('dashboard.browseStocksDesc'), path: '/stocks' },
            { title: t('dashboard.runBacktest'), desc: t('dashboard.runBacktestDesc'), path: '/backtest' },
            { title: t('dashboard.viewStrategies'), desc: t('dashboard.viewStrategiesDesc'), path: '/strategies' },
            { title: t('dashboard.technicalAnalysis'), desc: t('dashboard.technicalAnalysisDesc'), path: '/analysis' },
          ].map(item => (
            <a
              key={item.title}
              href={item.path}
              onClick={e => { e.preventDefault(); navigate(item.path) }}
              style={{
                display: 'block',
                padding: 16,
                background: 'var(--bg-primary)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                textDecoration: 'none',
                color: 'var(--text-primary)',
                transition: 'border-color 150ms',
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{item.title}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{item.desc}</div>
            </a>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">{t('dashboard.systemInfo')}</div>
        </div>
                <table className="data-table">
          <tbody>

            <tr><td style={{ width: 200 }}>{t('dashboard.backend')}</td><td>FastAPI + yfinance + AkShare</td></tr>
            <tr><td>{t('dashboard.backtestingEngine')}</td><td>Event-driven Python (Clojure DSL available)</td></tr>
            <tr><td>{t('dashboard.dataSourceFull')}</td><td>Yahoo Finance (yfinance), AkShare</td></tr>
            <tr><td>{t('dashboard.supportedExchanges')}</td><td>US, CN A-share, HK</td></tr>
            <tr><td>{t('dashboard.uiFramework')}</td><td>React + TypeScript + SCSS</td></tr>
            <tr><td>{t('dashboard.clojureDsl')}</td><td>clj/ project for ClojureScript backtesting</td></tr>

          </tbody>
        </table>
      </div>
    </div>
  )
}
