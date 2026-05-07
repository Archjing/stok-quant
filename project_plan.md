# 014_stock-us 美股量化分析系统 - 项目规划

**日期**: 2026-05-07  
**路径**: `D:\ZJ\Dev\Python_Projects\014_stock-us`  
**目标**: 美股量化分析 + 回测系统

---

## 一、项目定位

美股量化分析与回测系统，对标 013_stock 的 A 股项目，但针对美股市场：
- 数据源使用 **yfinance**（Yahoo Finance API）而非东方财富
- 技术栈保留 Python FastAPI 后端 + React 前端
- 引入 **Clojure DSL** 作为回测策略语言（特色功能）
- 支持多策略对比、技术指标预计算、回测引擎

---

## 二、技术架构

```
用户(浏览器) → Nginx(80) → Frontend(React + Vite)
                         → Backend(FastAPI:8000) → yfinance API
                                                  → SQLite(本地存储)
                                                  → Clojure回测引擎
```

### 各层说明

| 层 | 技术选型 | 说明 |
|----|---------|------|
| 前端 | React 18 + TypeScript + Vite | 5个路由页面: Dashboard/Stocks/Backtest/Strategies/Analysis |
| 样式 | 自定义 SCSS (Obsidian风格侧边栏) | 深色面板、毛玻璃效果 |
| 图标 | lucide-react | 轻量图标库 |
| 后端 | FastAPI + Uvicorn | 异步框架, RESTful API |
| 数据库 | SQLite + SQLAlchemy | 本地存储(us_stocks.db) |
| 数据源 | yfinance | 免费美股数据(Yahoo Finance) |
| 回测引擎 | Python (Numba加速) + Clojure DSL | 双引擎设计 |
| 容器化 | Docker + docker-compose | 双服务(前端+后端) |

---

## 三、详细模块设计

### 3.1 后端模块 (`backend/`)

#### 3.1.1 数据模型 (`backend/models/stock.py`)

两张核心表:

**USStock (us_stocks)** — 美股基本信息
- `symbol`: 股票代码 (PK, 如 AAPL)
- `name`: 公司全名
- `exchange`: 交易所 (NYSE/NASDAQ/AMEX)
- `sector`: 行业分类 (Technology/Healthcare/Financial Services 等)
- `industry`: 细分行业
- `market_cap`: 市值 (USD)
- `employees`: 员工数
- 估值字段: `price`, `pe_ratio`, `pb_ratio`, `ps_ratio`, `dividend_yield`, `beta`, `eps`
- 成长字段: `eps_growth`, `revenue_growth`
- 财务字段: `roe`, `gross_margin`, `operating_margin`, `debt_to_equity`, `current_ratio`, `free_cash_flow`

**USStockDaily (us_stock_daily)** — 美股日线数据 + 预计算技术指标
- K线: `symbol`, `date`, `open`, `high`, `low`, `close`, `volume`, `adjusted_close`
- 均线: `sma_20`, `sma_50`, `sma_200`, `ema_12`, `ema_26`
- 动量: `macd`, `macd_signal`, `macd_hist`, `rsi_14`
- 波动: `bb_upper`, `bb_middle`, `bb_lower`, `atr_14`
- 量能: `volume_sma_20`
- 唯一约束: (symbol, date)

#### 3.1.2 数据源 (`backend/crawlers/us_stock_source.py`)

**USStockSource** — yfinance 封装

内置防反爬：
- 随机延迟 `0.3~1.0s`
- User-Agent 轮换
- 每 20 只股票输出一次进度

内置 80+ 股票列表 (`MAJOR_US_STOCKS`)：
- S&P 500 头部 60 只 (AAPL/MSFT/GOOGL/AMZN/NVDA 等)
- 中概股 8 只 (BABA/JD/PDD/NIO 等)
- ETF 9 只 (VTI/VOO/QQQ/GLD 等)
- 国际头部 7 只 (TSM/ASML/NVS 等)

SECTOR_MAP 硬编码 50 只股票的行业映射。

API 方法：
- `get_stock_list()` — 遍历全部股票获取基本信息
- `get_stock_info(symbol)` — 单只股票详情
- `get_daily_data(symbol, start, end)` — 日线历史数据
- `get_full_history(symbol, years)` — 完整历史(默认10年)
- `get_financials(symbol)` — 财务数据(ROE/毛利率/负债比等)

#### 3.1.3 数据清洗 (`backend/crawlers/data_cleaner.py`)

**USDataCleaner** — 美股数据清洗器

- `clean_daily_data(df)` — 列名标准化、日期排序、类型转换
- `add_technical_indicators(df)` — 使用 `ta` 库计算全部技术指标 (SMA/EMA/MACD/RSI/Bollinger/ATR)

#### 3.1.4 回测引擎 (`backend/backtest/`)

**engine.py** — `BacktestEngine`
- 接受 DataFrame + 策略类
- 遍历 K 线执行策略信号
- 支持佣金(默认0.1%)、滑点(默认0.05%)
- 输出: 收益率曲线、回撤曲线、交易记录

**strategies.py** — 4 种内置策略
1. `SMACrossoverStrategy` — 双均线交叉(快线20/慢线50)
2. `RSIMeanReversionStrategy` — RSI均值回归(超卖30/超买70)
3. `MACDStrategy` — MACD趋势跟踪
4. `BuyAndHoldStrategy` — 买入持有基准

**metrics.py** — 评价指标计算
- 年化收益率、夏普比率、索提诺比率、卡玛比率
- 最大回撤、胜率、盈亏比、月收益分布

**indicators.py** — 技术指标函数
- Numba 加速的 SMA/EMA/MACD/RSI/Bollinger
- 作为 `ta` 库的备选实现

#### 3.1.5 API 路由 (`backend/routers/`)

**stocks.py** (`/api/stocks/`)
- `GET /` — 股票列表(分页+行业筛选)
- `GET /symbols` — 所有支持的代码
- `GET /{symbol}` — 股票详情
- `GET /{symbol}/daily` — 日线数据(支持技术指标)
- `GET /{symbol}/financials` — 财务数据
- `GET /sectors/list` — 行业分类

**backtest.py** (`/api/backtest/`)
- `GET /strategies` — 可用策略列表
- `POST /run` — 运行回测
- `POST /compare` — 多策略对比

#### 3.1.6 配置文件 (`config.yaml`)

```yaml
app:
  name: "US Stock Quant System"
  version: "1.0.0"

database:
  type: "sqlite"
  path: "data/us_stocks.db"

crawler:
  data_source: "yfinance"
  sources:
    yfinance: { timeout: 30, max_retries: 3 }
    alpaca: { enabled: false }
    polygon: { enabled: false }

backtest:
  default_commission: 0.001
  default_slippage: 0.0005
  default_initial_cash: 100000.0
  benchmark: "^GSPC"

analysis:
  default_indicators: [sma_20, sma_50, sma_200, ema_12, ema_26, macd, rsi_14, bollinger_20]
  default_filters: { market_cap: { min: 1e9 }, price: { min: 5.0 }, volume: { min: 100000 } }
```

### 3.2 前端模块 (`frontend/`)

#### 3.2.1 路由设计 (React Router)

| 路径 | 组件 | 功能 |
|------|------|------|
| `/` | Dashboard | 市场概览仪表板 |
| `/stocks` | StockList | 股票列表+搜索 |
| `/backtest` | BacktestView | 运行回测+展示结果 |
| `/strategies` | StrategyView | 策略管理 |
| `/analysis` | AnalysisView | 技术分析图表 |

#### 3.2.2 布局

Obsidian 风格侧边栏布局：
- 左侧固定侧边栏 (宽度240px)
- 右侧内容区域 (自适应)
- 导航项：Dashboard / Stocks / Backtest / Strategies / Analysis
- 底部显示版本号

#### 3.2.3 API 层 (`frontend/src/api/index.ts`)

```typescript
// 统一的 API 调用封装
// 所有回调函数式风格，参数自动拼接
```

### 3.3 Clojure 回测 DSL (`clj/`)

#### 3.3.1 设计思路

Clojure 函数式语言天然适合金融领域 DSL（领域特定语言），提供比 Python 更优雅的策略表达方式。

#### 3.3.2 核心抽象

```
Bar           — K线数据模型 {:symbol :timestamp :open :high :low :close :volume}
Order         — 订单模型 {:symbol :quantity :side :price :status}
Trade         — 交易记录 {:symbol :side :quantity :price :pnl :timestamp}
Position      — 持仓 {:symbol :quantity :avg-cost}
BacktestResult — 回测结果 {:total-return :annualized-return :sharpe-ratio ...}
```

#### 3.3.3 策略 DSL 示例

```clojure
(def my-strategy
  (strategy {:name "SMA Crossover"
             :on-bar (fn [ctx bar]
                       ;; 金叉买入
                       (when (cross-over? ctx :sma20 :sma50)
                         (buy! ctx (:symbol bar) 100))
                       ;; 死叉卖出
                       (when (cross-under? ctx :sma20 :sma50)
                         (sell! ctx (:symbol bar) 100)))}))
```

#### 3.3.4 内置辅助函数

- `cross-over?` / `cross-under?` — 金叉/死叉判断
- `rsi` — RSI 计算
- `buy!` / `sell!` / `close-position!` — 交易指令
- `get-position` — 查询持仓

#### 3.3.5 项目依赖 (`project.clj`)

- Clojure 1.11.1
- data.csv — CSV 导入导出
- java.jdbc — 数据库访问
- cheshire — JSON 处理
- clj-http — HTTP 客户端
- stockings — 金融数据源

### 3.4 Docker 部署 (`docker-compose.yml`)

双服务架构，无独立 Nginx 容器：
- **frontend**: Node 20 构建 → nginx:alpine 运行时 (端口80)
- **backend**: python:3.12-slim (端口8000)
- 网络: us-stock-network
- 持久化: `./data` → `/app/data`

Dockerfile.frontend 多阶段构建 (与 013_stock 一致)：
1. Node 20 阶段: npm install + npm run build
2. nginx:alpine 阶段: 复制 dist + nginx.conf

Dockerfile 后端：
- python:3.12-slim → pip install requirements.txt → uvicorn 启动

nginx.conf 反向代理：
- `/` → 静态文件
- `/api/` → proxy_pass backend:8000

### 3.5 本地启动脚本

**backend/start.bat** — FastAPI + Uvicorn (8000端口, 热重载)
**frontend/start.bat** — Vite 开发服务器 (5173端口)

---

## 四、与 013_stock 对比

| 维度 | 013_stock (A股) | 014_stock-us (美股) |
|------|-----------------|-------------------|
| 数据源 | akshare (东方财富) | yfinance (Yahoo Finance) |
| 覆盖范围 | A股全市场(5000+) | 美股头部(80+) |
| 前端 | Vue 3 + Element Plus | React 18 + TS |
| 回测引擎 | ❌ 无 | ✅ 双引擎(Python+Clojure) |
| 技术指标 | ❌ 无 | ✅ ta库 + Numba加速 |
| 策略管理 | ❌ 无 | ✅ 4种内置策略 + Clojure DSL |
| Docker | 三服务(+ streamlit) | 双服务 |
| 财务数据 | akshare 86列财务指标 | yfinance 基础财务 |
| 防反爬 | 新增 anti_block.py | 内置随机延迟+UA |

---

## 五、当前状态与待办

### ✅ 已完成
- [x] 项目框架搭建 (FastAPI + React + Docker)
- [x] 美股数据源 (yfinance, 80+ 股票)
- [x] 数据模型设计 (USStock + USStockDaily)
- [x] 技术指标计算 (SMA/EMA/MACD/RSI/Bollinger/ATR)
- [x] 回测引擎 (4种策略 + 评价指标)
- [x] Clojure 回测 DSL (策略定义 + 指标辅助)
- [x] Docker 部署 (双服务)
- [x] Nginx 反向代理

### 🔄 待完成
- [ ] 数据库持久化存储 (当前 yfinance 实时获取, 未写入 SQLite)
- [ ] 前端页面完整开发 (API 对接 + 数据展示)
- [ ] Clojure DSL 与 Python 后端集成
- [ ] 定时数据采集任务
- [ ] Alpaca/Polygon 数据源备选
- [ ] 策略回测结果可视化(Plotly/Dash)
- [ ] 部署到云服务器

---

## 六、关键问题记录

1. **yfinance 限流**: 当前已加随机延迟(0.3~1.0s)，但仍受 Yahoo Finance API 频率限制
2. **数据库未落地**: stocks.py 路由直连 yfinance 实时获取，未缓存到 SQLite；backtest.py 同理每次调用都重新获取数据
3. **Clojure 集成**: clj/ 目录独立，尚未与 Python 后端集成（计划通过 subprocess 调用来桥接）
4. **SECTOR_MAP 硬编码**: 50只股票的行业分类硬编码在 us_stock_source.py 中，扩展性差
5. **S&P 500 全量**: 当前只取了头部60只，未包含 S&P 500 全部成分股

---

*文档生成时间: 2026-05-07*
*基于对 014_stock-us 项目全部代码的分析整理*
