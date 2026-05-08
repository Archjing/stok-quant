import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import Chart from 'react-apexcharts'
import { listStocks, getStockDaily, getStockKline } from '../api'

// 图表类型
const CHART_TYPES = ['table', 'kline'] as const
type ChartType = typeof CHART_TYPES[number]

// K线周期
const KLINE_PERIODS = ['daily', 'monthly', 'yearly'] as const
type KlinePeriod = typeof KLINE_PERIODS[number]

// 月份名称（英文缩写，用于 tooltip）
const MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/**
 * 将整数时间戳格式化为显示字符串
 * en: 2020-Apr-01
 * zh: 2020-4月-01
 */
const formatTimestamp = (ts: number, lang: 'en' | 'zh' = 'en'): string => {
  const date = new Date(ts)
  const y = date.getFullYear()
  const m = date.getMonth()
  const d = String(date.getDate()).padStart(2, '0')
  if (lang === 'en') {
    return `${y}-${MONTHS_EN[m]}-${d}`
  }
  return `${y}-${m + 1}月-${d}`
}

// 根据数据范围计算 tick 配置（纯数字逻辑，无格式转换）
const calculateTickConfig = (
  data: any[],
  period: KlinePeriod,
): { tickAmount: number } => {
  if (!data || data.length === 0) return { tickAmount: 6 }

  switch (period) {
    case 'daily':
      return { tickAmount: Math.min(data.length, 10) }
    case 'monthly':
      return { tickAmount: Math.min(data.length, 12) }
    case 'yearly':
      return { tickAmount: Math.min(data.length, 8) }
    default:
      return { tickAmount: 8 }
  }
}

export default function StockList() {
  const { t } = useTranslation()
  const [stocks, setStocks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [daily, setDaily] = useState<any[]>([])
  const [detail, setDetail] = useState<any>(null)

  const [chartType, setChartType] = useState<ChartType>('table')
  const [klinePeriod, setKlinePeriod] = useState<KlinePeriod>('daily')
  const [klineData, setKlineData] = useState<any[]>([])
  const [klineSource, setKlineSource] = useState<string>('')
  const [klineLoading, setKlineLoading] = useState(false)

  // 用于计算图表高度的 ref
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const [chartHeight, setChartHeight] = useState(400)

  // 初始加载 - 限制数量，加快首屏
  useEffect(() => {
    setLoading(true)
    listStocks({ limit: 50 })  // 减少初始加载量
      .then((res: any) => setStocks(res?.data || []))
      .finally(() => setLoading(false))
  }, [])

  // 监听容器尺寸变化
  useEffect(() => {
    const updateChartHeight = () => {
      if (chartContainerRef.current) {
        const containerHeight = chartContainerRef.current.clientHeight
        // 留 5% 边距，撑满 95%
        const calculatedHeight = Math.max(300, containerHeight * 0.95)
        setChartHeight(Math.round(calculatedHeight))
      }
    }

    updateChartHeight()
    window.addEventListener('resize', updateChartHeight)
    return () => window.removeEventListener('resize', updateChartHeight)
  }, [chartType])

  const selectStock = async (symbol: string) => {
    setSelected(symbol)

    const [dailyRes] = await Promise.all([
      getStockDaily(symbol, { years: 1, indicators: true }),
    ])
    const d = dailyRes as any
    setDaily(d?.data?.slice(-60).reverse() || [])
    setDetail(d)

    loadKlineData(symbol, 'daily')
  }

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

  const handlePeriodChange = useCallback((period: KlinePeriod) => {
    setKlinePeriod(period)
    if (selected) {
      loadKlineData(selected, period)
    }
  }, [selected])

  // 计算 Y 轴范围（撑满 95%，留 2.5% 边距）
  const yaxisRange = useMemo(() => {
    if (klineData.length === 0) return undefined
    const prices = klineData.flatMap(d => d.y)
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const padding = (max - min) * 0.05 // 上下各 2.5% 边距
    return {
      min: Math.floor((min - padding) * 100) / 100,
      max: Math.ceil((max + padding) * 100) / 100,
    }
  }, [klineData])

  // K 线图配置
  const klineOptions = useMemo(() => {
    const lang: 'en' | 'zh' = t('stocks.symbol') !== 'Symbol' ? 'zh' : 'en'
    const tickCfg = calculateTickConfig(klineData, klinePeriod)

    return {
      chart: {
        type: 'candlestick' as const,
        height: chartHeight,
        toolbar: { 
          show: true,
          tools: { download: false, selection: true, zoom: true, zoomin: true, zoomout: true, pan: true, reset: true }
        },
        zoom: { enabled: true },
        background: 'transparent',
        animations: {
          enabled: true,
          easing: 'easeinout' as const,
          speed: 150,
          animateGradually: { enabled: false },
          dynamicAnimation: { enabled: false },
        },
        redrawOnParentResize: false,
        selection: {
          fill: { color: '#89b4fa', opacity: 0.1 },
        },
      },
      theme: { mode: 'dark' as const },
      grid: {
        borderColor: '#313146',
        strokeDashArray: 3,
        xaxis: { lines: { show: true } },
        yaxis: { lines: { show: true } },
        padding: { left: 0, right: 0 },
      },
      title: { text: '', align: 'left' },
      xaxis: {
        type: 'datetime' as const,
        labels: {
          style: {
            fontSize: 12,
            colors: '#6c7086',
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          },
          formatter: (val: number) => formatTimestamp(val, lang),
        },
        axisBorder: { color: '#313146' },
        axisTicks: { color: '#313146' },
        tickAmount: tickCfg.tickAmount,
        tickPlacement: 'between' as const,
      },
      yaxis: {
        min: yaxisRange?.min,
        max: yaxisRange?.max,
        tooltip: { enabled: true },
        labels: {
          style: {
            fontSize: 12,
            colors: '#6c7086',
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          },
          formatter: (val: number) => '$' + val.toFixed(2),
        },
      },
      plotOptions: {
        candlestick: {
          colors: {
            upward: '#10b981',
            downward: '#f43f5e',
          },
          wick: {
            useFillColor: true,
          },
        },
      },
      tooltip: {
        theme: 'dark' as const,
        style: { fontSize: 12 },
        enabled: true,
        shared: true,
        intersect: false,
        custom: ({ seriesIndex, dataPointIndex, w }: any) => {
          const ts = w.globals.seriesX?.[seriesIndex]?.[dataPointIndex]
          if (ts == null) return ''
          const dateStr = formatTimestamp(ts, lang)
          const o = w.globals.seriesCandleO?.[seriesIndex]?.[dataPointIndex]
          const h = w.globals.seriesCandleH?.[seriesIndex]?.[dataPointIndex]
          const l = w.globals.seriesCandleL?.[seriesIndex]?.[dataPointIndex]
          const c = w.globals.seriesCandleC?.[seriesIndex]?.[dataPointIndex]
          return `<div style="padding:4px 8px;font-size:12px">
            <div><strong>${dateStr}</strong></div>
            <div>O: $${o?.toFixed(2)} H: $${h?.toFixed(2)}</div>
            <div>L: $${l?.toFixed(2)} C: $${c?.toFixed(2)}</div>
          </div>`
        },
      },
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth' as const, width: 1 },
    }
  }, [chartHeight, yaxisRange, klinePeriod])

  // Memoized Chart 组件
  const MemoizedChart = useMemo(() => (
    <Chart
      options={klineOptions as any}
      series={[{ data: klineData }]}
      type="candlestick"
      height={chartHeight}
    />
  ), [klineOptions, klineData, chartHeight])

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
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {/* 左侧：图表类型切换 + 标题 */}
                <div style={titleContainerStyle}>
                  <div 
                    style={switchContainerStyle}
                    onClick={(e) => { e.stopPropagation(); setChartType(chartType === 'table' ? 'kline' : 'table') }}
                  >
                    <span style={chartType === 'table' ? activeLabelStyle : inactiveLabelStyle}>📊</span>
                    <div style={switchTrackStyle}>
                      <div style={{
                        ...switchThumbStyle,
                        transform: chartType === 'kline' ? 'translateX(24px)' : 'translateX(0)',
                      }} />
                    </div>
                    <span style={chartType === 'kline' ? activeLabelStyle : inactiveLabelStyle}>🕯️</span>
                  </div>
                  <span className="card-title">{chartType === 'kline' ? t('stocks.klineChart') : t('stocks.recentPriceHistory')}</span>
                </div>

                {/* 右侧：K线周期选择器 + 日期级别 + 数据源 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {chartType === 'kline' && (
                    <div style={periodGroupStyle}>
                      {(['daily', 'monthly', 'yearly'] as KlinePeriod[]).map(p => (
                        <button
                          key={p}
                          onClick={() => handlePeriodChange(p)}
                          style={klinePeriod === p ? activePeriodStyle : periodStyle}
                        >
                          {p === 'daily' ? '日' : p === 'monthly' ? '月' : '年'}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* 日期级别指示器 */}
                  {chartType === 'kline' && klineData.length > 0 && (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {klineSource === 'db' ? '📦 DB' : klineSource === 'yfinance' ? '📡 网络' : '-'}
                    </span>
                  )}

                  {chartType === 'kline' && (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {klineSource === 'db' ? '📦 DB' : klineSource === 'yfinance' ? '📡 网络' : '-'}
                    </span>
                  )}
                </div>
              </div>

              {/* 表格视图 */}
              <div className="table-scroll" style={{ flex: 1, display: chartType === 'table' ? 'block' : 'none' }}>
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

              {/* K线图视图 - 始终挂载，用CSS控制显隐 */}
              <div 
                ref={chartContainerRef} 
                style={{ 
                  flex: 1, 
                  padding: '8px 16px 16px', 
                  minHeight: 300,
                  display: chartType === 'kline' ? 'block' : 'none' 
                }}
              >
                {klineLoading ? (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: chartHeight }}>
                    <span>加载中...</span>
                  </div>
                ) : klineData.length > 0 ? (
                  MemoizedChart
                ) : (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: chartHeight }}>
                    <span>暂无数据</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ============ 样式定义 ============

// 标题容器 - 固定定位，开关在左
const titleContainerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
}

// 滑动开关容器 - 固定定位不飘移
const switchContainerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  cursor: 'pointer',
  userSelect: 'none',
  flexShrink: 0, // 防止压缩
}

// 滑动开关轨道 - 固定尺寸
const switchTrackStyle: React.CSSProperties = {
  position: 'relative',
  width: 44,
  height: 24,
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: 12,
  transition: 'all 0.2s ease',
  padding: 2,
  pointerEvents: 'none', // 事件由容器处理
}

// 滑动开关滑块
const switchThumbStyle: React.CSSProperties = {
  position: 'absolute',
  top: 2,
  left: 2,
  width: 18,
  height: 18,
  background: 'var(--accent)',
  borderRadius: '50%',
  transition: 'transform 0.2s ease',
  boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
  pointerEvents: 'none',
}

// 标签样式
const activeLabelStyle: React.CSSProperties = {
  fontSize: 16,
  transition: 'opacity 0.2s',
}

const inactiveLabelStyle: React.CSSProperties = {
  fontSize: 16,
  opacity: 0.5,
  transition: 'opacity 0.2s',
}

// 周期按钮组
const periodGroupStyle: React.CSSProperties = {
  display: 'flex',
  gap: 2,
  padding: 2,
  background: 'var(--bg-secondary)',
  borderRadius: 6,
}

const periodStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  borderRadius: 4,
  color: 'var(--text-muted)',
  cursor: 'pointer',
  padding: '4px 10px',
  fontSize: 12,
  transition: 'all 0.2s',
}

const activePeriodStyle: React.CSSProperties = {
  ...periodStyle,
  background: 'var(--accent)',
  color: '#fff',
  fontWeight: 500,
}
