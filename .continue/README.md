# US Stock Quant System - 量化分析与回测平台

## 🚀 项目简介
这是一个美股量化分析与回测系统，结合 **前端（React + TypeScript） + 后端（FastAPI/Python） + 数据库（SQLite）** 技术栈，支持股票数据管理、策略回测、数据分析与可视化。

---

## 📌 核心功能
1. **股票数据管理**
   - 爬取美股数据并存储到 SQLite 数据库（`data/us_stocks.db`）
   - 提供股票查询接口（`/stocks`）

2. **量化策略回测**
   - 支持多策略开发与历史数据回测
   - 生成回测结果并存储（`data/backtest_results.db`）

3. **数据分析与可视化**
   - 前端集成 ApexCharts 实现交互式 K 线图、策略分析图表
   - 提供股票列表、策略分析、回测结果展示等视图

4. **API 服务**
   - FastAPI 提供 RESTful 接口：
     - 股票数据查询（`/stocks`）
     - 回测执行（`/backtest`）
     - 数据同步（`/data-sync`）

---

## 📁 目录结构
```
.
├── backend/              # Python 后端逻辑（FastAPI + SQLite）
├── frontend/             # React 前端代码（TypeScript + Vite）
├── data/                 # SQLite 数据库文件（股票数据、回测结果）
├── clj/                  # Clojure 项目（辅助计算或策略开发）
├── tests/                # 单元测试与集成测试
├── Dockerfile            # Docker 镜像构建文件
├── docker-compose.yml    # 容器化部署配置
├── README.md             # 当前文件
└── package.json          # 前端依赖管理
```

---

## 🧰 技术栈
### 后端
- **框架**: FastAPI（异步支持）
- **数据库**: SQLite（`data/` 目录）
- **爬虫**: 自定义爬虫模块（`backend/crawlers/`）

### 前端
- **框架**: React + TypeScript
- **图表库**: ApexCharts
- **构建工具**: Vite

### 部署
- **容器化**: Docker + Docker Compose
- **版本控制**: Git

---

## 📌 项目用途
适用于：
- 实时股票数据监控
- 策略回测与性能分析
- 量化模型开发与部署
- 数据可视化与策略优化

---

## 📝 说明
- 通过 `docker-compose.yml` 可实现本地开发与生产部署
- 前端与后端通过 RESTful API 通信
- 数据存储于 SQLite 数据库（`data/` 目录）
- 项目包含完整测试用例（`tests/`）