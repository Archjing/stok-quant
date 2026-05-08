import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { BarChart3, TrendingUp, Search, Activity, LineChart, FlaskConical, Github, Globe } from 'lucide-react'
import Dashboard from './views/Dashboard'
import StockList from './views/StockList'
import BacktestView from './views/BacktestView'
import StrategyView from './views/StrategyView'
import AnalysisView from './views/AnalysisView'

function App() {
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const isZh = i18n.language === 'zh'

  const toggleLang = () => {
    const newLang = isZh ? 'en' : 'zh'
    i18n.changeLanguage(newLang)
    localStorage.setItem('lang', newLang)
  }

  const navItems = [
    { path: '/', label: t('nav.dashboard'), icon: BarChart3 },
    { path: '/stocks', label: t('nav.stocks'), icon: Search },
    { path: '/backtest', label: t('nav.backtest'), icon: TrendingUp },
    { path: '/strategies', label: t('nav.strategies'), icon: FlaskConical },
    { path: '/analysis', label: t('nav.analysis'), icon: Activity },
  ]

  return (
    <div className="app-layout">
      {/* Sidebar - Obsidian style */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title" style={{ fontSize: 28, gap: 10 }}>
            <LineChart size={32} />
            {t('app.title')}
          </div>
          <div className="sidebar-subtitle" style={{ fontSize: 14 }}>{t('app.subtitle')}</div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">
            <div className="nav-section-title">{t('nav.navigation')}</div>
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

        <div className="sidebar-footer">
          <button className="lang-toggle" onClick={toggleLang}>
            <Globe size={14} />
            {isZh ? 'en' : '中文'}
          </button>
          <a
            href="#"
            className="nav-item"
            style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '8px 12px' }}
            onClick={e => { e.preventDefault(); window.open('https://github.com', '_blank') }}
          >
            <Github size={14} />
            {t('app.version')}
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
