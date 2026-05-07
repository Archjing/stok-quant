(ns us-stock-quant.strategies
  "内置策略示例"
  (:require [us-stock-quant.core :refer :all]))


;; ============ SMA Crossover ============

(def sma-crossover
  (strategy
    {:name "SMA Crossover"
     :on-bar (fn [ctx bar]
               (let [pos (get-position ctx (:symbol bar))]
                 (when (and (zero? (:quantity pos))
                            (cross-over? ctx :sma20 :sma50))
                   (buy! ctx (:symbol bar) 100))
                 (when (and (pos? (:quantity pos))
                            (cross-under? ctx :sma20 :sma50))
                   (sell! ctx (:symbol bar) 100))))}))


;; ============ RSI Mean Reversion ============

(def rsi-mean-reversion
  (strategy
    {:name "RSI Mean Reversion"
     :on-bar (fn [ctx bar]
               (let [rsi (:rsi14 bar)
                     pos (get-position ctx (:symbol bar))]
                 (when (and rsi
                            (< rsi 30)
                            (zero? (:quantity pos)))
                   (buy! ctx (:symbol bar) 100))
                 (when (and rsi
                            (> rsi 70)
                            (pos? (:quantity pos)))
                   (sell! ctx (:symbol bar) 100))))}))


;; ============ MACD Strategy ============

(def macd-strategy
  (strategy
    {:name "MACD Trend"
     :on-bar (fn [ctx bar]
               (let [macd (:macd bar)
                     signal (:macd-signal bar)
                     pos (get-position ctx (:symbol bar))
                     prev-macd (get-in @(:data ctx)
                                       [(dec (count @(:data ctx))) :macd])
                     prev-signal (get-in @(:data ctx)
                                         [(dec (count @(:data ctx))) :macd-signal])]
                 (when (and macd signal prev-macd prev-signal
                            (<= prev-macd prev-signal)
                            (> macd signal)
                            (zero? (:quantity pos)))
                   (buy! ctx (:symbol bar) 100))
                 (when (and macd signal prev-macd prev-signal
                            (>= prev-macd prev-signal)
                            (< macd signal)
                            (pos? (:quantity pos)))
                   (sell! ctx (:symbol bar) 100))))}))
