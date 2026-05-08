import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Code, BookOpen, Terminal } from 'lucide-react'

const strategies = [
  {
    id: 'sma_crossover',
    name: 'SMA Crossover',
    lang: 'Python',
    desc: {
      en: 'Simple Moving Average Crossover strategy. Buy when short SMA crosses above long SMA, sell when it crosses below.',
      zh: '双均线金叉死叉策略。短期SMA上穿长期SMA时买入，下穿时卖出。'
    },
    code: `class SMACrossoverStrategy(Strategy):
    def on_bar(self, bar):
        sma20 = self.get_indicator("sma_20")
        sma50 = self.get_indicator("sma_50")
        if not sma20 or not sma50:
            return
        # Golden cross: buy
        if sma20 > sma50 and self.prev_sma20 <= self.prev_sma50:
            self.buy(bar.symbol, quantity=100, tag="golden_cross")
        # Death cross: sell
        elif sma20 < sma50 and self.prev_sma20 >= self.prev_sma50:
            self.close_position(bar.symbol, tag="death_cross")
        self.prev_sma20 = sma20
        self.prev_sma50 = sma50`,
  },
  {
    id: 'rsi_mean_reversion',
    name: 'RSI Mean Reversion',
    lang: 'Python',
    desc: {
      en: 'RSI Mean Reversion strategy. Buy when RSI is below 30 (oversold), sell when RSI is above 70 (overbought).',
      zh: 'RSI均值回归策略。RSI低于30超卖时买入，高于70超买时卖出。'
    },
    code: `class RSIMeanReversionStrategy(Strategy):
    def __init__(self, oversold=30, overbought=70):
        self.oversold = oversold
        self.overbought = overbought

    def on_bar(self, bar):
        rsi = self.get_indicator("rsi_14")
        if not rsi:
            return
        pos = self.get_position(bar.symbol)
        if rsi < self.oversold and pos == 0:
            self.buy(bar.symbol, 100, tag="rsi_oversold")
        elif rsi > self.overbought and pos > 0:
            self.close_position(bar.symbol, tag="rsi_overbought")`,
  },
  {
    id: 'macd',
    name: 'MACD Trend',
    lang: 'Python',
    desc: {
      en: 'MACD Trend Following strategy. Buy when MACD line crosses above signal line, sell when it crosses below.',
      zh: 'MACD趋势跟踪策略。MACD线上穿信号线时买入，下穿时卖出。'
    },
    code: `class MACDStrategy(Strategy):
    def on_bar(self, bar):
        macd = self.get_indicator("macd")
        signal = self.get_indicator("macd_signal")
        hist = self.get_indicator("macd_hist")
        if None in (macd, signal, hist):
            return
        pos = self.get_position(bar.symbol)
        if self.prev_hist <= 0 and hist > 0 and pos == 0:
            self.buy(bar.symbol, 100, tag="macd_buy")
        elif self.prev_hist >= 0 and hist < 0 and pos > 0:
            self.close_position(bar.symbol, tag="macd_sell")
        self.prev_hist = hist`,
  },
  {
    id: 'clojure_dsl',
    name: 'SMA Crossover (Clojure DSL)',
    lang: 'Clojure',
    desc: {
      en: 'Clojure functional backtesting DSL version. Using function composition and immutable data.',
      zh: 'Clojure 函数式回测 DSL 版本。使用函数组合+不可变数据。'
    },
    code: `(ns my-strategies
  (:require [us-stock-quant.core :refer :all]))

(def sma-crossover
  (strategy
    {:name "SMA Crossover"
     :on-bar (fn [ctx bar]
               (let [pos (get-position ctx (:symbol bar))]
                 ;; Golden cross
                 (when (and (zero? (:quantity pos))
                            (cross-over? ctx :sma20 :sma50))
                   (buy! ctx (:symbol bar) 100))
                 ;; Death cross
                 (when (and (pos? (:quantity pos))
                            (cross-under? ctx :sma20 :sma50))
                   (sell! ctx (:symbol bar) 100))))})))

;; Run: (run-backtest sma-crossover data {:initial-cash 100000.0})`,
  },
  {
    id: 'clojure_rsi',
    name: 'RSI Mean Rev (Clojure DSL)',
    lang: 'Clojure',
    desc: {
      en: 'Clojure implementation of RSI Mean Reversion strategy, demonstrating functional composition.',
      zh: 'Clojure 实现的RSI均值回归策略，展示函数式组合能力。'
    },
    code: `(ns my-strategies
  (:require [us-stock-quant.core :refer :all]))

(def rsi-mean-reversion
  (strategy
    {:name "RSI Mean Reversion"
     :on-bar (fn [ctx bar]
               (let [rsi (:rsi14 bar)
                     pos (get-position ctx (:symbol bar))]
                 (when (and rsi (< rsi 30) (zero? (:quantity pos)))
                   (buy! ctx (:symbol bar) 100))
                 (when (and rsi (> rsi 70) (pos? (:quantity pos)))
                   (sell! ctx (:symbol bar) 100))))})))`,
  },
]

export default function StrategyView() {
  const { t, i18n } = useTranslation()
  const isZh = i18n.language === 'zh'
  const [activeTab, setActiveTab] = useState('python')

  const python = strategies.slice(0, 3)
  const clojure = strategies.slice(3)

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 20 }}>{t('strategies.title')}</h2>

      <div className="tabs">
        <button className={`tab ${activeTab === 'python' ? 'active' : ''}`}
          onClick={() => setActiveTab('python')}>
          <Code size={14} style={{ marginRight: 4, verticalAlign: -2 }} />
          Python
        </button>
        <button className={`tab ${activeTab === 'clojure' ? 'active' : ''}`}
          onClick={() => setActiveTab('clojure')}>
          <Terminal size={14} style={{ marginRight: 4, verticalAlign: -2 }} />
          Clojure DSL
        </button>
      </div>

      {(activeTab === 'python' ? python : clojure).map((s) => (
        <div key={s.id} className="card">
          <div className="card-header">
            <div>
              <div className="card-title">{s.name}</div>
              <div className="card-subtitle">
                <span style={{
                  display: 'inline-block',
                  padding: '1px 6px',
                  borderRadius: 4,
                  background: s.lang === 'Clojure' ? 'var(--success)' : 'var(--accent)',
                  color: 'var(--bg-primary)',
                  fontSize: 11,
                  fontWeight: 600,
                  marginRight: 8,
                }}>{s.lang}</span>
                {isZh ? s.desc.zh : s.desc.en}
              </div>
            </div>
          </div>
          <pre style={{
            background: 'var(--bg-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            padding: 16,
            fontSize: 12,
            fontFamily: 'var(--font-mono)',
            lineHeight: 1.6,
            overflow: 'auto',
            maxHeight: 300,
            color: 'var(--text-secondary)',
          }}>
            <code>{s.code}</code>
          </pre>
        </div>
      ))}
    </div>
  )
}
