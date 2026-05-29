import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Database, DownloadCloud, ArrowUpRight, RefreshCcw, Loader2 } from 'lucide-react'
import {
  MARKETS,
  MarketCode,
  getDataSyncStatus,
  triggerDataDownload,
  triggerDataUpdate,
  refreshMarketPrices,
  refreshStockList,
} from '../api'

export default function DataSyncView() {
  const { t } = useTranslation()
  const [market, setMarket] = useState<MarketCode>('US')
  const [status, setStatus] = useState<any>({ market: 'US', currency: 'USD', running: false, stocks: [] })
  const [loading, setLoading] = useState(false)
  const [actionMessage, setActionMessage] = useState('')
  const [error, setError] = useState('')
  const [busyAction, setBusyAction] = useState<string | null>(null)

  const getErrorText = (err: any) => {
    const respData = err?.response?.data
    if (typeof respData === 'string') {
      return respData
    }
    if (respData?.detail) {
      return typeof respData.detail === 'string'
        ? respData.detail
        : JSON.stringify(respData.detail)
    }
    if (respData && typeof respData === 'object') {
      return JSON.stringify(respData)
    }
    return err?.message || t('dataSync.requestFailed')
  }

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const resp = await getDataSyncStatus({ market })
      setStatus(resp)
    } catch (err: any) {
      setError(getErrorText(err))
    } finally {
      setLoading(false)
    }
  }, [market])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  useEffect(() => {
    if (!status.running) {
      return undefined
    }
    const timer = window.setInterval(fetchStatus, 5000)
    return () => window.clearInterval(timer)
  }, [fetchStatus, status.running])

  const handleSync = async (
    action: 'download' | 'update' | 'refresh',
    fn: (params: any) => Promise<any>,
  ) => {
    setBusyAction(action)
    setActionMessage('')
    setError('')
    try {
      const resp = await fn({ market })
      setActionMessage(resp?.message || t('dataSync.actionSubmitted'))
      await fetchStatus()
    } catch (err: any) {
      setError(getErrorText(err))
    } finally {
      setBusyAction(null)
    }
  }

  const marketLabel = useMemo(
    () => MARKETS.find((item) => item.code === market)?.label || market,
    [market],
  )

  return (
    <div>
      <div className="card-header">
        <div>
          <div className="card-title">{t('dataSync.title')}</div>
          <div className="card-subtitle">{t('dataSync.summary')}</div>
        </div>
        <Database size={20} />
      </div>

      <div className="card" style={{ gap: 16, display: 'grid' }}>
        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ minWidth: 180 }}>
            <label htmlFor="market" style={{ display: 'block', marginBottom: 6, fontSize: 12, color: 'var(--text-muted)' }}>
              {t('dataSync.selectMarket')}
            </label>
            <select
              id="market"
              className="form-select"
              value={market}
              onChange={(event) => setMarket(event.target.value as MarketCode)}
            >
              {MARKETS.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>
              {t('dataSync.currentStatus')}
            </div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <div className="stat-card" style={{ flex: '1 1 180px', padding: '14px' }}>
                <div className="stat-label">{t('dataSync.market')}</div>
                <div className="stat-value">{marketLabel}</div>
              </div>
              <div className="stat-card" style={{ flex: '1 1 180px', padding: '14px' }}>
                <div className="stat-label">{t('dataSync.syncStatus')}</div>
                <div className="stat-value">{status.running ? t('dataSync.statusRunning') : t('dataSync.statusIdle')}</div>
              </div>
              <div className="stat-card" style={{ flex: '1 1 180px', padding: '14px' }}>
                <div className="stat-label">{t('dataSync.currency')}</div>
                <div className="stat-value">{status.currency || '--'}</div>
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary"
            disabled={busyAction !== null}
            onClick={() => handleSync('download', triggerDataDownload)}
          >
            <DownloadCloud size={16} />
            {t('dataSync.btnDownload')}
          </button>
          <button
            className="btn btn-secondary"
            disabled={busyAction !== null}
            onClick={() => handleSync('update', triggerDataUpdate)}
          >
            <ArrowUpRight size={16} />
            {t('dataSync.btnUpdate')}
          </button>
          <button
            className="btn btn-secondary"
            disabled={busyAction !== null}
            onClick={() => handleSync('refresh', refreshMarketPrices)}
          >
            <RefreshCcw size={16} />
            {t('dataSync.btnRefreshPrices')}
          </button>
          <button
            className="btn btn-secondary"
            disabled={busyAction !== null}
            onClick={() => handleSync('symbols', refreshStockList)}
          >
            <Database size={16} />
            {t('dataSync.btnRefreshSymbols')}
          </button>
        </div>

        <div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 10 }}>
            {status.running ? t('dataSync.runningTip') : t('dataSync.idleTip')}
          </div>
          {actionMessage ? (
            <div className="card" style={{ borderColor: 'var(--accent)', background: 'var(--bg-surface)' }}>
              <div style={{ fontSize: 13, color: 'var(--accent)' }}>{actionMessage}</div>
            </div>
          ) : null}
          {error ? (
            <div className="card" style={{ borderColor: 'var(--danger)', background: 'var(--bg-surface)' }}>
              <div style={{ fontSize: 13, color: 'var(--danger)' }}>{error}</div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">{t('dataSync.overviewTitle')}</div>
          <div className="card-subtitle">{t('dataSync.overviewSubtitle')}</div>
        </div>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)' }}>
            <Loader2 size={16} className="spin" />
            {t('common.loading')}
          </div>
        ) : status.stocks?.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('dataSync.tableSymbol')}</th>
                  <th>{t('dataSync.tableStatus')}</th>
                  <th>{t('dataSync.tableLastSync')}</th>
                  <th>{t('dataSync.tableRowCount')}</th>
                </tr>
              </thead>
              <tbody>
                {status.stocks.map((item: any) => (
                  <tr key={item.symbol}>
                    <td className="mono">{item.symbol}</td>
                    <td>{item.status || '--'}</td>
                    <td>{item.last_sync_date || item.last_sync_time || '--'}</td>
                    <td>{item.total_rows ?? '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t('dataSync.empty')}</div>
        )}
      </div>
    </div>
  )
}
