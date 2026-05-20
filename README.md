# US Stock Quant System

一个面向美股市场的量化分析与策略回测项目，提供股票数据浏览、技术指标分析、策略回测、多策略对比和数据同步能力，适合用于量化研究、策略验证和教学演示。

## 功能特性

- **美股数据浏览**：支持查看股票列表、基础信息、日线数据和 K 线数据
- **多周期 K 线展示**：支持日线、月线、年线切换，适配前端图表展示
- **技术指标分析**：内置 SMA、EMA、MACD、RSI、布林带、ATR 等常见指标
- **策略回测引擎**：支持单策略回测、收益统计、回撤分析、交易记录输出
- **多策略对比**：可对同一股票运行多种策略并横向比较表现
- **懒加载数据机制**：数据库无缓存时自动触发下载，降低首次使用门槛
- **数据同步管理**：支持全量下载、增量更新、价格刷新和同步状态查看
- **双语言前端界面**：支持中英文切换
- **Clojure DSL 示例**：包含函数式回测策略示例，便于扩展实验
- **Docker 部署支持**：前后端可通过 Docker Compose 一键部署

## 技术栈

- **后端**：FastAPI + SQLAlchemy + SQLite
- **前端**：React 18 + TypeScript + Vite + SCSS
- **图表**：ApexCharts + Recharts
- **数据源**：Yahoo Finance（yfinance）
- **数据处理**：pandas + polars + numpy + scipy + ta + numba
- **扩展实验**：Clojure DSL
- **部署方式**：Docker + Docker Compose + Nginx

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- npm
- 可选：Docker / Docker Compose

### 安装

```bash
# 1. 安装/确认 uv
uv --version

# 2. 同步 Python 依赖（会自动创建 .venv）
uv sync

# 3. 安装前端依赖
cd frontend
npm install
```

### 运行

#### 开发模式

```bash
# 终端1：启动后端
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8777

# 终端2：启动前端
cd frontend
npm run dev
```

启动后可访问：

- 前端开发服务：`http://localhost:5173`
- 后端接口文档：`http://localhost:8777/docs`
- 健康检查：`http://localhost:8777/health`

#### Docker 部署

```bash
# 在项目根目录
docker-compose up --build
```

默认容器说明：

- `frontend`：对外提供 Web 界面
- `backend`：提供 FastAPI 接口和数据服务

## 项目结构

```text
014_stok-quant/
├── backend/                    # 后端服务
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置加载
│   ├── database.py             # 数据库初始化与连接
│   ├── data_manager.py         # 数据管理与同步调度
│   ├── analyzers/              # 技术分析模块
│   ├── backtest/               # 回测引擎、指标和策略
│   ├── crawlers/               # 美股数据抓取与清洗
│   ├── models/                 # 数据模型
│   └── routers/                # API 路由
├── frontend/                   # React 前端应用
│   ├── src/api/                # API 调用封装
│   ├── src/views/              # 页面视图
│   ├── src/components/         # 通用组件
│   ├── src/i18n/               # 国际化资源
│   ├── src/stores/             # 状态管理
│   └── src/styles/             # 样式文件
├── clj/                        # Clojure 回测 DSL 示例
├── data/                       # SQLite 数据库与本地数据
├── tests/                      # 测试代码
├── pyproject.toml              # uv / Python 项目配置
├── uv.lock                     # uv 锁定文件
├── Dockerfile.frontend         # 前端镜像构建文件
├── docker-compose.yml          # 容器编排配置
├── Dockerfile                  # 后端镜像构建文件
└── config.yaml                 # 项目配置文件
```

## 核心模块说明

### 股票数据模块

- 提供股票列表查询、筛选和详情查看
- 支持按行业、交易所、指数、市场规模、自定义股票池筛选
- 支持日线历史数据和 K 线图数据输出
- 支持财务信息查询

### 技术分析模块

- RSI(14)
- MACD / Signal / Hist
- SMA(20/50/200)
- EMA(12/26)
- 布林带（上轨/中轨/下轨）
- ATR(14)
- 成交量均线

### 回测策略模块

当前内置策略包括：

- **SMA Crossover**：双均线交叉策略
- **RSI Mean Reversion**：RSI 均值回归策略
- **MACD Trend**：MACD 趋势跟踪策略
- **Buy and Hold**：买入并持有策略

回测结果支持输出：

- 总收益率
- 年化收益率
- 波动率
- 夏普比率
- Sortino 比率
- Calmar 比率
- 最大回撤
- 胜率
- 盈亏比
- 交易明细
- 资金曲线与回撤曲线

## 主要接口

### 数据接口

- `GET /api/stocks/`：获取股票列表
- `GET /api/stocks/symbols`：获取支持的股票代码
- `GET /api/stocks/{symbol}/daily`：获取股票日线数据
- `GET /api/stocks/{symbol}/kline`：获取 K 线数据
- `GET /api/stocks/{symbol}/financials`：获取财务数据

### 回测接口

- `GET /api/backtest/strategies`：获取可用策略列表
- `POST /api/backtest/run`：执行单策略回测
- `POST /api/backtest/compare`：多策略对比
- `GET /api/backtest/status/{symbol}`：查看股票数据状态
- `POST /api/backtest/warmup`：预热下载指定股票数据

### 数据同步接口

- `GET /api/data/status`：查看同步状态
- `POST /api/data/download`：触发全量下载
- `POST /api/data/update`：触发增量更新
- `POST /api/data/refresh-prices`：刷新实时价格

## 使用说明

1. **首次启动**：后端启动时会自动初始化数据库
2. **浏览股票**：在前端 Stock List 页面查看股票列表与 K 线数据
3. **技术分析**：在 Analysis 页面查看技术指标和近期行情数据
4. **运行回测**：在 Backtest 页面选择股票、策略和回溯年数后执行回测
5. **策略对比**：启用 Compare 模式，对多个策略进行横向比较
6. **数据预热**：如某只股票本地无缓存，系统可在首次请求时自动下载数据
7. **查看文档**：通过 `/docs` 查看 Swagger API 文档

## 注意事项

- 本项目仅用于学习、研究和演示，不构成任何投资建议
- 数据来自 Yahoo Finance，可能存在延迟、缺失或接口限制
- 首次请求某些股票时，可能因懒下载机制产生等待时间
- 若进行批量下载，建议控制调用频率，避免触发数据源限流
- SQLite 适合单机开发与中小规模使用，生产环境可考虑替换为更强的数据库方案

## License

MIT
