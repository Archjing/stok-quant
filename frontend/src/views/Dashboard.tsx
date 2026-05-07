import { useState, useEffect } from 'react'
import { BarChart3, TrendingUp, DollarSign, Activity } from 'lucide-react'
import { getSymbols, listStrategies } from '../api'

export default function Dashboard() {
  const [stats, setStats] = useState({ stocks: 0, strategies: 0, lastUpdate: '' })

  useEffect(() => {
    Promise.all([
      getSymbols(),
      listStrategies(),
    ]).then(([symbolsResp, stratsResp]) => {
      const symData = symbolsResp as any
      const stratData = stratsResp as any
      setStats({
        stocks: symData?.total || 0,
        strategies: stratData?.strategies?.length || 0,
        lastUpdate: new Date().toLocaleTimeString(),
      })
    })
  }, [])

  const cards = [
    { label: 'US Stocks', value: stats.stocks, icon: BarChart3, color: 'accent' },
    { label: 'Strategies', value: stats.strategies, icon: TrendingUp, color: 'positive' },
    { label: 'Data Source', value: 'Yahoo Finance', icon: DollarSign, color: '' },
    { label: 'Last Update', value: stats.lastUpdate || '--', icon: Activity, color: '' },
  ]

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 20 }}>Dashboard</h2>

      <div className="stats-grid">
        {cards.map(c => (
          <div key={c.label} className="stat-card">
            <div className="stat-label">{c.label}</div>
            <div className={`stat-value ${c.color}`}>
              {typeof c.value === 'number' ? c.value.toLocaleString() : c.value}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Quick Start</div>
        </div>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
          {[
            { title: 'Browse Stocks', desc: 'Search & explore US stocks data', path: '/stocks' },
            { title: 'Run Backtest', desc: 'Test strategies on historical data', path: '/backtest' },
            { title: 'View Strategies', desc: 'Explore quant trading strategies', path: '/strategies' },
            { title: 'Technical Analysis', desc: 'RSI, MACD, Bollinger Bands', path: '/analysis' },
          ].map(item => (
            <a
              key={item.title}
              href={item.path}
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
              onClick={e => {
                e.preventDefault()
                window.location.hash = item.path
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
          <div className="card-title">System Info</div>
        </div>
        <table className="data-table">
          <tbody>
            <tr><td style={{ width: 200 }}>Backend</td><td>FastAPI + yfinance</td></tr>
            <tr><td>Backtesting Engine</td><td>Event-driven Python (Clojure DSL available)</td></tr>
            <tr><td>Data Source</td><td>Yahoo Finance (yfinance)</td></tr>
            <tr><td>Supported Exchanges</td><td>NYSE, NASDAQ, AMEX</td></tr>
            <tr><td>UI Framework</td><td>React + TypeScript + SCSS</td></tr>
            <tr><td>Clojure DSL</td><td>clj/ project for ClojureScript backtesting</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
