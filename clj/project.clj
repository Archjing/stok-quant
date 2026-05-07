(defproject us-stock-quant "0.1.0"
  :description "US Stock Quant Backtesting DSL"
  :url "https://github.com/yourname/us-stock-quant"
  :license {:name "MIT"}
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [org.clojure/data.csv "1.1.0"]
                 [org.clojure/java.jdbc "0.7.12"]
                 [cheshire "5.12.0"]
                 [clj-http "3.12.3"]
                 [com.fxtlabs/stockings "1.0.0"]]  ; 数据源
  :main ^:skip-aot us-stock-quant.core
  :target-path "target/%s"
  :profiles {:uberjar {:aot :all
                       :jvm-opts ["-Dclojure.compiler.direct-linking=true"]}})
