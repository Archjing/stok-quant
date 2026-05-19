# 多市场扩展最终实施计划

> 目标：在不破坏当前美股功能的前提下，将项目从 **US Stock Quant System** 扩展为支持 **美股 US、A 股 CN、港股 HK** 的多市场股票量化分析与回测系统。

## 1. 当前项目基线

当前系统已经具备以下能力：

- 美股股票列表浏览
- 美股日线数据查询
- 日线、月线、年线 K 线展示
- 技术指标分析：SMA、EMA、MACD、RSI、布林带、ATR、成交量均线
- 单策略回测
- 多策略对比
- 数据懒加载与同步状态管理
- 前端 React + Vite 图表展示
- 后端 FastAPI + SQLAlchemy + SQLite
- Python 环境由 `uv` 管理

当前主要数据源：

- 美股：Yahoo Finance / `yfinance`

当前主要数据模型：

- `USStock`
- `USStockDaily`
- `DataSyncStatus`

当前主要接口：

- `/api/stocks/...`
- `/api/backtest/...`
- `/api/data/...`

## 2. 扩展目标

扩展后系统支持：

| 市场 | 代码 | 范围                     | 数据源     | 货币 |
| ---- | ---- | ------------------------ | ---------- | ---- |
| 美股 | `US` | NASDAQ / NYSE / AMEX 等  | `yfinance` | USD  |
| A 股 | `CN` | 上海 / 深圳 / 北京交易所 | `AkShare`  | CNY  |
| 港股 | `HK` | 港交所                   | `AkShare`  | HKD  |

扩展后功能包括：

1. 多市场股票列表浏览
2. A 股、港股基础信息获取
3. A 股、港股日线数据获取与缓存
4. A 股、港股 K 线浏览
5. A 股、港股技术指标分析
6. A 股、港股单策略回测
7. A 股、港股多策略对比
8. 多市场数据同步与懒加载下载
9. 前端市场切换
10. 不破坏现有美股功能

## 3. 核心实施原则

### 3.1 不立即迁移美股数据库

为降低风险，第一阶段不把现有美股数据迁入新通用表。

保留现有美股链路：

```text
USStockSource -> DataManager -> USStock / USStockDaily -> 当前 API / 回测
```

新增 A 股、港股链路：

```text
AkShare -> MarketDataManager -> MarketStock / MarketDailyBar -> 扩展 API / 回测
```

也就是说：

```text
US: 继续使用旧 DataManager + USStockDaily
CN/HK: 使用新 MarketDataManager + MarketDailyBar
```

### 3.2 统一的是业务数据结构，而非立刻统一数据库

第一阶段统一：

- 标准 OHLCV DataFrame
- API 返回结构
- K 线返回格式
- 回测输入格式

不强制统一：

- 美股数据库表
- 美股现有 DataManager 内部实现

三类数据最终都转换为标准业务结构：

```text
USStockDaily rows -> 标准 OHLCV DataFrame
MarketDailyBar rows -> 标准 OHLCV DataFrame
AkShare raw DataFrame -> 标准 OHLCV DataFrame
```

### 3.3 API 采用统一入口 + market 参数

不新增三套 API：

```text
/api/us/stocks
/api/cn/stocks
/api/hk/stocks
```

统一使用：

```text
/api/stocks/?market=US|CN|HK
/api/stocks/{symbol}/daily?market=US|CN|HK
/api/stocks/{symbol}/kline?market=US|CN|HK
/api/backtest/run?market=US|CN|HK
```

默认值：

```text
market=US
```

这样保持旧调用兼容。

### 3.4 数据源封装，不在 router 中直接调用数据源库

禁止在 router 中直接调用：

```text
yfinance
akshare
```

统一封装成市场数据源：

```text
USMarketSource
CNMarketSource
HKMarketSource
```

router 只调用 DataManager / MarketDataManager。

## 4. 股票代码规范

### 4.1 内部标准格式

| 市场       | 示例     | 内部标准格式 |
| ---------- | -------- | ------------ |
| 美股       | Apple    | `AAPL`       |
| A 股沪市   | 贵州茅台 | `SH.600519`  |
| A 股深市   | 平安银行 | `SZ.000001`  |
| A 股北交所 | 贝特瑞   | `BJ.835185`  |
| 港股       | 腾讯控股 | `HK.00700`   |

说明：

- 美股继续使用当前格式，避免破坏现有功能。
- A 股必须带交易所前缀。
- 港股必须保留 5 位代码和前导零。

### 4.2 用户输入兼容规则

A 股：

```text
600519     -> SH.600519
SH600519   -> SH.600519
SH.600519  -> SH.600519

000001     -> SZ.000001
SZ000001   -> SZ.000001
SZ.000001  -> SZ.000001

835185     -> BJ.835185
BJ835185   -> BJ.835185
BJ.835185  -> BJ.835185
```

港股：

```text
700        -> HK.00700
00700      -> HK.00700
HK700      -> HK.00700
HK.700     -> HK.00700
HK.00700   -> HK.00700
```

美股：

```text
aapl       -> AAPL
AAPL       -> AAPL
```

### 4.3 新增代码规范工具

新增文件：

```text
backend/markets/symbols.py
```

提供函数：

```text
normalize_symbol(symbol, market)
detect_market(symbol)
detect_exchange(symbol, market)
to_source_symbol(symbol, market)
get_currency(market)
```

## 5. 数据库方案

### 5.1 保留旧表

继续保留：

```text
us_stocks
us_stock_daily
data_sync_status
```

这些表继续服务美股旧链路。

### 5.2 新增通用多市场表

新增文件：

```text
backend/models/market.py
```

新增模型：

```text
MarketStock
MarketDailyBar
MarketSyncStatus
```

### 5.3 `MarketStock`

表名：

```text
market_stocks
```

字段：

```text
id
market              # US / CN / HK
symbol              # AAPL / SH.600519 / HK.00700
raw_symbol          # AAPL / 600519 / 00700
name
exchange            # NASDAQ / NYSE / SH / SZ / BJ / HKEX
board               # 主板 / 创业板 / 科创板 / 北交所 / 港股主板
sector
industry
area
country
currency            # USD / CNY / HKD

price
change_pct
market_cap
pe_ratio
pb_ratio
dividend_yield
turnover_rate

created_at
updated_at
```

唯一约束：

```text
unique(market, symbol)
```

### 5.4 `MarketDailyBar`

表名：

```text
market_daily_bars
```

字段：

```text
id
market
symbol
date

open
high
low
close
volume
amount
adjusted_close

change_pct
change_amount
amplitude
turnover_rate

sma_20
sma_50
sma_200
ema_12
ema_26
macd
macd_signal
macd_hist
rsi_14
bb_upper
bb_middle
bb_lower
atr_14
volume_sma_20

created_at
```

唯一约束：

```text
unique(market, symbol, date)
```

### 5.5 `MarketSyncStatus`

表名：

```text
market_sync_status
```

字段：

```text
id
market
symbol
last_sync_date
last_sync_time
total_rows
status
error_message
retry_count
```

唯一约束：

```text
unique(market, symbol)
```

## 6. 数据源方案

### 6.1 美股 US

继续使用：

```text
yfinance
```

当前阶段保留现有 `USStockSource`。

可新增包装类：

```text
USMarketSource
```

但第一阶段不强制迁移。

### 6.2 A 股 CN

使用：

```text
AkShare
```

需要添加依赖：

```bash
uv add akshare
```

A 股历史行情计划使用：

```python
ak.stock_zh_a_hist(
    symbol="600519",
    period="daily",
    start_date="20200101",
    end_date="20251231",
    adjust="qfq",
)
```

默认复权：

```text
qfq 前复权
```

### 6.3 港股 HK

使用：

```text
AkShare
```

港股历史行情计划使用类似：

```python
ak.stock_hk_hist(
    symbol="00700",
    period="daily",
    start_date="20200101",
    end_date="20251231",
    adjust="qfq",
)
```

实际接口名称和参数以当前 AkShare 版本为准，全部封装在 `HKMarketSource` 中。

## 7. K 线方案

AkShare 可获取 A 股和港股历史 OHLCV 数据，因此可以作为 K 线数据源。

系统统一策略：

```text
数据库保存日线数据
日线 K 线直接返回
月线 K 线由日线聚合
年线 K 线由日线聚合
```

K 线返回格式继续兼容 ApexCharts：

```json
{
  "x": 1717372800000,
  "y": [1680.0, 1700.0, 1660.0, 1695.0]
}
```

统一响应示例：

```json
{
  "market": "CN",
  "symbol": "SH.600519",
  "currency": "CNY",
  "period": "daily",
  "source": "db",
  "data": [
    {
      "x": 1717372800000,
      "y": [1680.0, 1700.0, 1660.0, 1695.0]
    }
  ]
}
```

## 8. 后端新增模块

新增目录：

```text
backend/markets/
```

结构：

```text
backend/markets/
├── __init__.py
├── base.py
├── symbols.py
├── registry.py
├── cn.py
└── hk.py
```

可选后续新增：

```text
backend/markets/us.py
```

### 8.1 `base.py`

定义统一数据源接口：

```text
BaseMarketSource
├── get_stock_list()
├── get_stock_info(symbol)
├── get_daily_data(symbol, start_date, end_date, adjust)
├── get_full_history(symbol, years, adjust)
└── normalize_daily_dataframe(df)
```

### 8.2 `cn.py`

实现：

```text
CNMarketSource
```

职责：

- A 股股票列表
- A 股实时价格
- A 股历史日线
- A 股数据字段标准化
- A 股基础信息

### 8.3 `hk.py`

实现：

```text
HKMarketSource
```

职责：

- 港股股票列表
- 港股实时价格
- 港股历史日线
- 港股数据字段标准化
- 港股基础信息

### 8.4 `registry.py`

提供数据源注册表：

```text
MARKET_SOURCES = {
    "CN": CNMarketSource(),
    "HK": HKMarketSource(),
}
```

第一阶段 `US` 可继续走旧逻辑。

## 9. 新增通用数据管理器

新增文件：

```text
backend/market_data_manager.py
```

核心职责：

```text
get_stock_list(market)
refresh_stock_prices(market)
lazy_download_one(market, symbol, years, adjust)
download_all(market, symbols)
incremental_update(market, symbols)
get_daily_from_db(market, symbol, years)
get_sync_summary(market)
get_missing_symbols(market, symbols)
```

`MarketDataManager` 只服务新市场：

```text
CN
HK
```

美股暂时继续使用现有 `DataManager`。

## 10. API 改造计划

### 10.1 股票 API

修改：

```text
backend/routers/stocks.py
```

新增参数：

```text
market: str = Query("US")
```

需要扩展接口：

```text
GET /api/stocks/?market=US|CN|HK
GET /api/stocks/filters?market=US|CN|HK
GET /api/stocks/symbols?market=US|CN|HK
GET /api/stocks/{symbol}/daily?market=US|CN|HK
GET /api/stocks/{symbol}/kline?market=US|CN|HK
GET /api/stocks/{symbol}/financials?market=US|CN|HK
GET /api/stocks/{symbol}?market=US|CN|HK
```

分发逻辑：

```text
market == US -> 使用现有 DataManager / USStockSource
market == CN/HK -> 使用 MarketDataManager / MarketSource
```

### 10.2 回测 API

修改：

```text
backend/routers/backtest.py
```

新增参数：

```text
market: str = Query("US")
```

扩展：

```text
POST /api/backtest/run?market=US|CN|HK
POST /api/backtest/compare?market=US|CN|HK
GET /api/backtest/status/{symbol}?market=US|CN|HK
POST /api/backtest/warmup?market=US|CN|HK
```

核心函数改为：

```text
_get_backtest_data(symbol, years, market="US")
```

内部：

```text
US -> 旧 DataManager -> USDataCleaner -> 标准 DataFrame
CN/HK -> MarketDataManager -> 标准 DataFrame
```

`BacktestEngine` 暂不修改。

### 10.3 数据同步 API

修改：

```text
backend/routers/data_sync.py
```

新增参数：

```text
market: str = Query("US")
```

扩展：

```text
GET /api/data/status?market=US|CN|HK
POST /api/data/download?market=US|CN|HK
POST /api/data/update?market=US|CN|HK
POST /api/data/refresh-prices?market=US|CN|HK
```

## 11. 标准 OHLCV DataFrame

进入 K 线、分析、回测前，所有市场统一转换为：

```text
date
open
high
low
close
volume
amount
adjusted_close
change_pct
change_amount
amplitude
turnover_rate

sma_20
sma_50
sma_200
ema_12
ema_26
macd
macd_signal
macd_hist
rsi_14
bb_upper
bb_middle
bb_lower
atr_14
volume_sma_20
```

其中：

- `amount` 可为空
- `change_pct` 可为空
- `turnover_rate` 可为空
- 美股旧数据没有的字段返回 `None`

## 12. 前端改造计划

### 12.1 API 层

修改：

```text
frontend/src/api/index.ts
```

现有函数已经支持 params，大多只需调用时增加：

```text
market
```

例如：

```text
listStocks({ market, limit: 50 })
getStockDaily(symbol, { market, years: 2, indicators: true })
getStockKline(symbol, { market, period, years })
runBacktest({ market, symbol, strategy, years })
```

### 12.2 市场切换

需要在以下页面增加市场选择器：

```text
StockList.tsx
AnalysisView.tsx
BacktestView.tsx
```

选项：

```text
US 美股
CN A股
HK 港股
```

### 12.3 货币符号适配

| 市场 | 货币符号 |
| ---- | -------- |
| US   | `$`      |
| CN   | `¥`      |
| HK   | `HK$`    |

前端显示价格、K 线 tooltip、回测资金时根据 market / currency 适配。

### 12.4 股票默认值

| 市场 | 默认股票    |
| ---- | ----------- |
| US   | `AAPL`      |
| CN   | `SH.600519` |
| HK   | `HK.00700`  |

### 12.5 筛选项适配

US：

```text
sector
exchange
index
market_cap
custom
```

CN：

```text
exchange: SH / SZ / BJ
board: 主板 / 科创板 / 创业板 / 北交所
index: 沪深300 / 上证50 / 中证500 / 科创50 / 北证50
custom
```

HK：

```text
exchange: HKEX
board: Main Board / GEM
index: 恒生指数 / 国企指数 / 科技指数
custom
```

第一阶段可先支持：

```text
exchange
custom
```

## 13. 回测市场规则

### 13.1 第一阶段

第一阶段复用现有回测引擎：

```text
BacktestEngine
SMACrossoverStrategy
RSIMeanReversionStrategy
MACDStrategy
BuyAndHoldStrategy
```

暂不强制模拟市场规则差异。

### 13.2 后续增强

后续新增：

```text
MarketBacktestConfig
```

规则：

US：

```text
currency = USD
lot_size = 1
```

CN：

```text
currency = CNY
lot_size = 100
t_plus_one = true
stamp_tax_sell = true
price_limit = true
```

HK：

```text
currency = HKD
lot_size = variable
t_plus_one = false
stamp_duty = true
price_limit = false
```

## 14. 样本股票池

### 14.1 A 股样本

```text
SH.600519 贵州茅台
SH.601318 中国平安
SH.600036 招商银行
SH.601899 紫金矿业
SH.600276 恒瑞医药
SH.600900 长江电力
SH.601088 中国神华
SH.600030 中信证券
SH.601398 工商银行
SH.601288 农业银行

SZ.000001 平安银行
SZ.000858 五粮液
SZ.002594 比亚迪
SZ.000333 美的集团
SZ.000651 格力电器
SZ.002415 海康威视
SZ.300750 宁德时代
SZ.300760 迈瑞医疗
SZ.300059 东方财富
SZ.002475 立讯精密

SH.688981 中芯国际
SH.688111 金山办公
SH.688012 中微公司

BJ.430047 诺思兰德
BJ.835185 贝特瑞
```

### 14.2 港股样本

```text
HK.00700 腾讯控股
HK.09988 阿里巴巴-W
HK.03690 美团-W
HK.01810 小米集团-W
HK.00005 汇丰控股
HK.00941 中国移动
HK.01299 友邦保险
HK.02318 中国平安
HK.01398 工商银行
HK.03988 中国银行
HK.00883 中国海洋石油
HK.00857 中国石油股份
HK.01024 快手-W
HK.09618 京东集团-SW
HK.09888 百度集团-SW
HK.02020 安踏体育
HK.02331 李宁
HK.02269 药明生物
HK.00669 创科实业
HK.00388 香港交易所
```

## 15. 分阶段实施计划

## Phase 0：依赖和基础结构

目标：为多市场扩展打底，不影响现有美股功能。

任务：

1. 添加 AkShare 依赖：
   ```bash
   uv add akshare
   ```
2. 新增目录：
   ```text
   backend/markets/
   ```
3. 新增：
   ```text
   backend/markets/__init__.py
   backend/markets/base.py
   backend/markets/symbols.py
   backend/markets/registry.py
   ```
4. 新增通用模型：
   ```text
   backend/models/market.py
   ```
5. 确保 `init_db()` 能创建新表。

验收：

- `uv sync` 成功
- 后端可启动
- 新表可自动创建
- 现有美股功能不受影响

## Phase 1：实现 A 股数据源 CN

目标：后端能获取 A 股股票列表和历史日线。

任务：

1. 新增：
   ```text
   backend/markets/cn.py
   ```
2. 实现 `CNMarketSource`
3. 实现 A 股代码转换
4. 实现 A 股列表获取
5. 实现 A 股日线获取
6. 实现中文字段到标准 OHLCV 字段映射
7. 默认使用前复权 `qfq`
8. 使用样本 A 股池做 fallback

验收：

- 能获取 `SH.600519` 日线
- DataFrame 字段标准化成功
- 技术指标可计算

## Phase 2：实现港股数据源 HK

目标：后端能获取港股股票列表和历史日线。

任务：

1. 新增：
   ```text
   backend/markets/hk.py
   ```
2. 实现 `HKMarketSource`
3. 实现港股代码标准化，保留 5 位代码
4. 实现港股列表获取
5. 实现港股日线获取
6. 实现字段标准化
7. 使用样本港股池做 fallback

验收：

- 能获取 `HK.00700` 日线
- 港股代码前导零不丢失
- DataFrame 字段标准化成功

## Phase 3：实现 MarketDataManager

目标：A 股和港股可以缓存入库、从库读取、懒加载下载。

任务：

1. 新增：
   ```text
   backend/market_data_manager.py
   ```
2. 实现：
   ```text
   get_stock_list(market)
   lazy_download_one(market, symbol, years, adjust)
   get_daily_from_db(market, symbol, years)
   download_all(market, symbols)
   incremental_update(market, symbols)
   get_sync_summary(market)
   refresh_stock_prices(market)
   ```
3. 保存 `MarketStock`
4. 保存 `MarketDailyBar`
5. 保存 `MarketSyncStatus`
6. 接入技术指标计算

验收：

- `CN/SH.600519` 可入库
- `HK/HK.00700` 可入库
- 再次查询优先走 DB
- 同步状态可查询

## Phase 4：扩展股票 API

目标：`/api/stocks` 支持 `market=US|CN|HK`。

任务：

1. 修改：
   ```text
   backend/routers/stocks.py
   ```
2. 所有相关接口增加 `market` 参数
3. `US` 走旧逻辑
4. `CN/HK` 走 `MarketDataManager`
5. 统一 daily 返回结构
6. 统一 kline 返回结构
7. 月线、年线继续由日线聚合

验收：

```text
GET /api/stocks/?market=CN
GET /api/stocks/?market=HK
GET /api/stocks/SH.600519/daily?market=CN&years=3&indicators=true
GET /api/stocks/HK.00700/daily?market=HK&years=3&indicators=true
GET /api/stocks/SH.600519/kline?market=CN&period=daily
GET /api/stocks/HK.00700/kline?market=HK&period=daily
```

均可正常返回。

## Phase 5：扩展回测 API

目标：A 股、港股可以复用现有回测引擎。

任务：

1. 修改：
   ```text
   backend/routers/backtest.py
   ```
2. `_get_backtest_data()` 增加 `market`
3. `US` 走旧逻辑
4. `CN/HK` 走 `MarketDataManager`
5. 返回标准 DataFrame 给 `BacktestEngine`
6. 返回结果增加：
   ```text
   market
   currency
   data_source
   ```

验收：

```text
POST /api/backtest/run?market=CN&symbol=SH.600519&strategy=sma_crossover&years=5
POST /api/backtest/run?market=HK&symbol=HK.00700&strategy=sma_crossover&years=5
POST /api/backtest/compare?market=CN&symbol=SH.600519&years=5
POST /api/backtest/compare?market=HK&symbol=HK.00700&years=5
```

均可正常运行。

## Phase 6：扩展数据同步 API

目标：A 股、港股支持同步状态、批量下载、增量更新。

任务：

1. 修改：
   ```text
   backend/routers/data_sync.py
   ```
2. 增加 `market` 参数
3. `US` 走旧逻辑
4. `CN/HK` 走 `MarketDataManager`
5. 支持样本股票池下载
6. 支持自定义股票下载

验收：

```text
GET /api/data/status?market=CN
GET /api/data/status?market=HK
POST /api/data/download?market=CN
POST /api/data/download?market=HK
POST /api/data/update?market=CN
POST /api/data/update?market=HK
```

可正常执行。

## Phase 7：前端市场切换

目标：前端可浏览、分析、回测 US/CN/HK。

任务：

1. 修改：
   ```text
   frontend/src/api/index.ts
   frontend/src/views/StockList.tsx
   frontend/src/views/AnalysisView.tsx
   frontend/src/views/BacktestView.tsx
   frontend/src/i18n/zh.ts
   frontend/src/i18n/en.ts
   ```
2. 增加市场选择器
3. 所有 API 调用传入 `market`
4. 根据市场切换默认股票
5. 根据 `currency` 显示 `$` / `¥` / `HK$`
6. K 线 tooltip 适配货币
7. 回测结果资金单位适配
8. 筛选项按市场变化

验收：

- Stock List 可切换 US/CN/HK
- A 股可查看 K 线
- 港股可查看 K 线
- Analysis 页面可分析 A 股/港股
- Backtest 页面可回测 A 股/港股
- 美股原功能保持正常

## Phase 8：文档和测试

目标：完善文档，补充测试，确保迁移稳定。

任务：

1. 更新 `README.md`
2. 说明多市场支持范围
3. 说明 AkShare 数据源
4. 说明 A 股/港股回测第一阶段暂不模拟特殊交易规则
5. 补充测试：
   ```text
   symbol normalize tests
   CN source smoke tests
   HK source smoke tests
   MarketDataManager tests
   kline response tests
   backtest market tests
   ```

验收：

- README 清楚说明 US/CN/HK
- 测试通过
- 启动脚本不受影响
- Docker 构建仍可用

## 16. 后续增强计划

### 16.1 市场规则回测

后续新增：

```text
MarketBacktestConfig
```

支持：

- A 股 100 股一手
- A 股 T+1
- A 股涨跌停
- A 股印花税
- 港股不同 lot size
- 港股印花税和交易费
- 港股无固定涨跌停

### 16.2 指数和行业

A 股增强：

```text
沪深300
上证50
中证500
科创50
创业板指
北证50
行业分类
概念板块
```

港股增强：

```text
恒生指数
国企指数
恒生科技指数
港股通成分
行业分类
```

### 16.3 美股迁移到通用表

待 CN/HK 稳定后，考虑迁移美股到：

```text
MarketStock
MarketDailyBar
MarketSyncStatus
```

迁移步骤：

1. 写迁移脚本
2. 将 `USStockDaily` 复制到 `MarketDailyBar`，`market=US`
3. 将 `USStock` 复制到 `MarketStock`，`market=US`
4. API 全部读通用表
5. 旧表保留一段时间
6. 稳定后废弃旧表

## 17. 风险和约束

### 17.1 AkShare 接口变化

AkShare 底层接口可能变化，因此必须封装在 `CNMarketSource` / `HKMarketSource` 中。

### 17.2 数据请求频率

A 股和港股数量较多，不建议默认全市场下载。

第一阶段策略：

```text
默认样本池
按需懒加载
支持手动批量下载
```

### 17.3 SQLite 数据量

全量多年数据可能较大。第一阶段继续使用 SQLite，后续如数据规模增长可考虑 PostgreSQL。

### 17.4 回测真实性

第一阶段 A 股/港股回测复用现有引擎，暂不模拟全部市场交易制度。

需要在 README 中说明。

## 18. 最终执行顺序

推荐严格按以下顺序执行：

```text
Phase 0  依赖和基础结构
Phase 1  A 股数据源 CN
Phase 2  港股数据源 HK
Phase 3  MarketDataManager
Phase 4  股票 API market 参数
Phase 5  回测 API market 参数
Phase 6  数据同步 API market 参数
Phase 7  前端市场切换
Phase 8  文档和测试
```

每个阶段完成后都必须确认：

```text
现有美股功能仍然正常
后端可启动
前端可启动
核心 API 可访问
```

## 19. 当前阶段明确不做的事项

第一轮实现中暂不做：

1. 不立即迁移美股旧表到通用表
2. 不默认下载全量 A 股/港股
3. 不实现完整 A 股 T+1 / 涨跌停 / 印花税规则
4. 不实现完整港股 lot size / 印花税 / 交易费规则
5. 不强制引入 Tushare Token
6. 不替换 SQLite

这些作为后续增强项。
