import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { BarChart3, TrendingUp, Search, Activity, Settings, LineChart, FlaskConical, Github } from 'lucide-react'
import Dashboard from './views/Dashboard'
import StockList from './views/StockList'
import BacktestView from './views/BacktestView'
import StrategyView from './views/StrategyView'
import AnalysisView from './views/AnalysisView'

function App() {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/stocks', label: 'Stocks', icon: Search },
    { path: '/backtest', label: 'Backtest', icon: TrendingUp },
    { path: '/strategies', label: 'Strategies', icon: FlaskConical },
    { path: '/analysis', label: 'Analysis', icon: Activity },
  ]

  return (
    <div className="app-layout">
      {/* Sidebar - Obsidian style */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">
            <LineChart size={18} />
            US Quant
          </div>
          <div className="sidebar-subtitle">Stock Analysis & Backtesting</div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">
            <div className="nav-section-title">Navigation</div>
            {navItems.map(item => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `nav-item${isActive ? ' active' : ''}`
                }
              >
                <item.icon size={16} />
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>

        <div style={{ padding: '8px', borderTop: '1px solid var(--border-light)' }}>
          <a
            href="#"
            className="nav-item"
            style={{ fontSize: '12px', color: 'var(--text-muted)' }}
            onClick={e => { e.preventDefault(); window.open('https://github.com', '_blank') }}
          >
            <Github size={14} />
            v1.0.0
          </a>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <div className="content-area">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/stocks" element={<StockList />} />
            <Route path="/backtest" element={<BacktestView />} />
            <Route path="/strategies" element={<StrategyView />} />
            <Route path="/analysis" element={<AnalysisView />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default App
