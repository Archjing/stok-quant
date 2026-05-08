import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import Chart from 'react-apexcharts'
import { listStocks, getStockDaily, getStockKline } from '../api'

// 图表类型选项
const CHART_TYPES = ['table', 'kline'] as const
type ChartType = typeof CHART_TYPES[number]

// K线周期选项
const KLINE_PERIODS = ['daily', 'monthly', 'yearly'] as const
type KlinePeriod = typeof KLINE_PERIODS[number]

export default function StockList() {
  const { t } = useTranslation()
  const [stocks, setStocks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [daily, setDaily] = useState<any[]>([])
  const [detail, setDetail] = useState<any>(null)

  // 图表类型选择
  const [chartType, setChartType] = useState<ChartType>('table')
  const [chartTypeIndex, setChartTypeIndex] = useState(0)

  // K线周期选择
  const [klinePeriod, setKlinePeriod] = useState<KlinePeriod>('daily')
  const [klinePeriodIndex, setKlinePeriodIndex] = useState(0)
  const [klineData, setKlineData] = useState<any[]>([])
  const [klineSource, setKlineSource] = useState<string>('')
  const [klineLoading, setKlineLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    listStocks({ limit: 100 })
      .then((res: any) => setStocks(res?.data || []))
      .finally(() => setLoading(false))
  }, [])

  const selectStock = async (symbol: string) => {
    setSelected(symbol)
    setChartTypeIndex(0)
    setChartType('table')
    setKlinePeriodIndex(0)
    setKlinePeriod('daily')

    const [dailyRes] = await Promise.all([
      getStockDaily(symbol, { years: 1, indicators: true }),
    ])
    const d = dailyRes as any
    setDaily(d?.data?.slice(-60).reverse() || [])
    setDetail(d)

    // 加载默认 K 线数据（日线）
    loadKlineData(symbol, 'daily')
  }

  // 加载 K 线数据
  const loadKlineData = async (symbol: string, period: KlinePeriod) => {
    setKlineLoading(true)
    try {
      const res = await getStockKline(symbol, { period, years: period === 'yearly' ? 10 : 5 }) as any
      setKlineData(res?.data || [])
      setKlineSource(res?.source || '')
    } catch (err) {
      console.error('K线数据加载失败:', err)
      setKlineData([])
      setKlineSource('error')
    } finally {
      setKlineLoading(false)
    }
  }

  // 切换图表类型
  const cycleChartType = (direction: 1 | -1) => {
    const newIndex = (chartTypeIndex + direction + CHART_TYPES.length) % CHART_TYPES.length
    setChartTypeIndex(newIndex)
    setChartType(CHART_TYPES[newIndex])
  }

  // 切换 K 线周期
  const cycleKlinePeriod = (direction: 1 | -1) => {
    const newIndex = (klinePeriodIndex + direction + KLINE_PERIODS.length) % KLINE_PERIODS.length
    setKlinePeriodIndex(newIndex)
    const newPeriod = KLINE_PERIODS[newIndex]
    setKlinePeriod(newPeriod)
    if (selected) {
      loadKlineData(selected, newPeriod)
    }
  }

  // ApexCharts 配置
  const klineOptions: any = {
    chart: {
      type: 'candlestick',
      height: 350,
      toolbar: { show: true },
      zoom: { enabled: true },
    },
    title: { text: '', align: 'left' },
    xaxis: { type: 'datetime', labels: { style: { fontSize: 11 } } },
    yaxis: {
      tooltip: { enabled: true },
      labels: { style: { fontSize: 11 }, formatter: (val: number) => '$' + val.toFixed(2) },
    },
    plotOptions: {
      candlestick: {
        colors: { upward: '#26a69a', downward: '#ef5350' },
        wick: { useFillColor: true },
      },
    },
  }

  // 表格标题选择器
  const renderTableTitle = () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span className="card-title">{t('stocks.recentPriceHistory')}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <button
          onClick={() => cycleChartType(-1)}
          style={arrowButtonStyle}
        >▲</button>
        <span style={selectorStyle}>
          {chartType === 'table' ? '📊 ' + t('stocks.table') : '🕯️ ' + t('stocks.kline')}
        </span>
        <button
          onClick={() => cycleChartType(1)}
          style={arrowButtonStyle}
        >▼</button>
      </div>
    </div>
  )

  // K线周期选择器
  const renderKlinePeriodSelector = () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <button
        onClick={() => cycleKlinePeriod(-1)}
        style={arrowButtonStyle}
      >▲</button>
      <span style={selectorStyle}>
        {klinePeriod === 'daily' ? '日K' : klinePeriod === 'monthly' ? '月K' : '年K'}
      </span>
      <button
        onClick={() => cycleKlinePeriod(1)}
        style={arrowButtonStyle}
      >▼</button>
    </div>
  )

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
                {chartType === 'table' ? renderTableTitle() : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span className="card-title">{t('stocks.kline')}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <button
                        onClick={() => cycleChartType(-1)}
                        style={arrowButtonStyle}
                      >▲</button>
                      <span style={selectorStyle}>
                        🕯️ {t('stocks.kline')}
                      </span>
                      <button
                        onClick={() => cycleChartType(1)}
                        style={arrowButtonStyle}
                      >▼</button>
                    </div>
                    {renderKlinePeriodSelector()}
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
                      来源: {klineSource || '-'}
                    </span>
                  </div>
                )}
              </div>

              {chartType === 'table' ? (
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
              ) : (
                <div style={{ flex: 1, padding: 16 }}>
                  {klineLoading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 350 }}>
                      <span>加载中...</span>
                    </div>
                  ) : klineData.length > 0 ? (
                    <Chart
                      options={klineOptions}
                      series={[{ data: klineData }]}
                      type="candlestick"
                      height={350}
                    />
                  ) : (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 350 }}>
                      <span>暂无数据</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// 箭头按钮样式
const arrowButtonStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  color: 'var(--text)',
  cursor: 'pointer',
  padding: '2px 8px',
  fontSize: 10,
  lineHeight: 1,
}

// 选择器样式
const selectorStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  borderRadius: 4,
  padding: '2px 8px',
  fontSize: 13,
  minWidth: 70,
  textAlign: 'center',
}
