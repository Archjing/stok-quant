(ns us-stock-quant.core
  "US Stock Quant Backtesting DSL
   Clojure 回测 DSL 核心
   
   用法:
   (def my-strategy
     (strategy {:name \"SMA Crossover\"
                :on-bar (fn [ctx bar]
                          (when (golden-cross? ctx :sma20 :sma50)
                            (buy! ctx (:symbol bar) 100))
                          (when (death-cross? ctx :sma20 :sma50)
                            (sell! ctx (:symbol bar) 100)))}))
   
   (run-backtest my-strategy data {:initial-cash 100000.0})"
  (:require [cheshire.core :as json]
            [clojure.java.io :as io]
            [clojure.data.csv :as csv]))

;; ============ 数据模型 ============

(defrecord Bar [symbol timestamp open high low close volume])

(defrecord Order [symbol quantity side price status])

(defrecord Trade [symbol side quantity price pnl timestamp])

(defrecord Position [symbol quantity avg-cost])

(defrecord BacktestResult [total-return annualized-return sharpe-ratio
                           max-drawdown total-trades win-rate equity-curve
                           trades])

;; ============ 策略 DSL ============

(defprotocol IStrategy
  (on-start [this ctx])
  (on-bar [this ctx bar])
  (on-stop [this ctx]))

(defrecord SimpleStrategy [name on-bar-fn on-start-fn on-stop-fn]
  IStrategy
  (on-start [this ctx]
    (when on-start-fn (on-start-fn ctx)))
  (on-bar [this ctx bar]
    (when on-bar-fn (on-bar-fn ctx bar)))
  (on-stop [this ctx]
    (when on-stop-fn (on-stop-fn ctx))))

(defn strategy
  "定义策略
   opts: {:name \"策略名\"
          :on-bar (fn [ctx bar] ...)
          :on-start (fn [ctx] ...)
          :on-stop (fn [ctx] ...)}"
  [opts]
  (->SimpleStrategy
    (:name opts "")
    (:on-bar opts)
    (:on-start opts)
    (:on-stop opts)))

;; ============ 上下文操作 ============

(defn buy!
  "买入"
  [ctx symbol quantity]
  (swap! (:orders ctx) conj
         (->Order symbol quantity "buy" "market" nil))
  ctx)

(defn sell!
  "卖出"
  [ctx symbol quantity]
  (swap! (:orders ctx) conj
         (->Order symbol quantity "sell" "market" nil))
  ctx)

(defn close-position!
  "平仓"
  [ctx symbol]
  (let [pos (get-in @(:positions ctx) [symbol])]
    (when pos
      (sell! ctx symbol (:quantity pos))))
  ctx)

(defn get-position
  "获取持仓"
  [ctx symbol]
  (get-in @(:positions ctx) [symbol] (->Position symbol 0 0.0)))

;; ============ 指标辅助 ============

(defn cross-over?
  "金叉: short 线上穿 long 线"
  [ctx short-key long-key]
  (let [data @(:data ctx)
        short-vals (mapv #(get % short-key) data)
        long-vals (mapv #(get % long-key) data)]
    (when (and (>= (count short-vals) 2)
               (>= (count long-vals) 2))
      (let [sp (nth short-vals (- (count short-vals) 2))
            sc (last short-vals)
            lp (nth long-vals (- (count long-vals) 2))
            lc (last long-vals)]
        (and (some? sp) (some? sc) (some? lp) (some? lc)
             (<= sp lp) (> sc lc))))))

(defn cross-under?
  "死叉"
  [ctx short-key long-key]
  (let [data @(:data ctx)
        short-vals (mapv #(get % short-key) data)
        long-vals (mapv #(get % long-key) data)]
    (when (and (>= (count short-vals) 2)
               (>= (count long-vals) 2))
      (let [sp (nth short-vals (- (count short-vals) 2))
            sc (last short-vals)
            lp (nth long-vals (- (count long-vals) 2))
            lc (last long-vals)]
        (and (some? sp) (some? sc) (some? lp) (some? lc)
             (>= sp lp) (< sc lc))))))

(defn rsi
  "计算 RSI"
  [prices window]
  (let [deltas (map - (rest prices) (butlast prices))
        gains (map #(max % 0) deltas)
        losses (map #(abs (min % 0)) deltas)
        avg-gain (/ (reduce + (take-last window gains)) window)
        avg-loss (/ (reduce + (take-last window losses)) window)]
    (if (zero? avg-loss) 100
        (- 100 (/ 100 (inc (/ avg-gain avg-loss)))))))

;; ============ 回测引擎 ============

(defn run-backtest
  "运行回测
   strategy: IStrategy 实例
   data: [{:date :open :high :low :close :volume ...}]
   opts: {:initial-cash 100000.0 :commission 0.001}"
  [strategy data opts]
  (let [initial-cash (or (:initial-cash opts) 100000.0)
        commission (or (:commission opts) 0.001)
        ctx (atom {:cash initial-cash
                   :positions (atom {})
                   :orders (atom [])
                   :trades (atom [])
                   :equity (atom [initial-cash])
                   :data (atom [])
                   :bar-index 0})]
    ;; on-start
    (on-start strategy ctx)
    ;; 遍历 K 线
    (doseq [bar (map #(map->Bar %) data)]
      (swap! (:data ctx) conj bar)
      (swap! (:bar-index ctx) inc)
      (on-bar strategy ctx bar)
      ;; 计算权益
      (let [pos-val (reduce + 0 (map (fn [[sym pos]]
                                       (* (:quantity pos) (:close bar)))
                                     @(:positions ctx)))
            total (+ @(:cash ctx) pos-val)]
        (swap! (:equity ctx) conj total)))
    (on-stop strategy ctx)
    ;; 计算结果
    (let [equity @(:equity ctx)
          start-eq (first equity)
          end-eq (last equity)
          total-return (/ (- end-eq start-eq) start-eq)]
      (->BacktestResult
        total-return
        (Math/pow (1+ total-return) (/ 252 (count equity)))  ;; 年化
        0.0  ;; sharpe
        0.0  ;; max-dd
        (count @(:trades ctx))
        0.0
        equity
        @(:trades ctx)))))
