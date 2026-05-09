
> 这是一个 美股量化分析与回测系统 的完整代码项目，结合了 前端（React） + 后端（FastAPI/Python） + 数据库（SQLite） 技术栈，具备以下核心功能：



## 🚀 项目核心功能



### 1. 股票数据管理

- 通过 backend/crawlers/us_stock_source.py 爬取美股数据
- 存储到 data/us_stocks.db 和 data/stocks.db SQLite 数据库
- 提供股票查询接口（backend/routers/stocks.py）

### 2. 量化策略回测

- 使用 backend/backtest/strategies.py 实现策略逻辑
- 通过 backend/backtest/engine.py 执行回测
- 生成回测结果并存储（backend/models/backtest.py）

### 3. 数据分析与可视化

- 前端使用 React + TypeScript（frontend/src/）实现交互式图表
- 集成 ApexCharts（frontend/src/styles/index.scss）
- 提供策略分析、股票列表、K线图等视图（frontend/src/views/）

### 4. API 服务

- 后端基于 FastAPI（backend/main.py），提供 RESTful 接口
- 支持股票数据查询（/stocks）、回测（/backtest）、数据同步（/data-sync）

### 5. 容器化部署

- 使用 Docker（Dockerfile, docker-compose.yml）打包服务
- 支持本地开发和生产环境部署

---



## 📁 关键目录结构

| 目录      | 说明                                                         |
| --------- | ------------------------------------------------------------ |
| backend/  | Python 后端逻辑，包含 FastAPI 服务、数据库操作、策略回测模块 |
| frontend/ | React 前端代码，使用 TypeScript + Vite 构建，包含 UI 和数据可视化 |
| data/     | 存储 SQLite 数据库文件（股票数据、回测结果）                 |
| clj/      | Clojure 回测策略脚本                                         |
| tests/    | 单元测试和集成测试（覆盖 API、数据库、回测逻辑）             |
| log/      | 项目文档、开发日志、部署说明                                 |



## 🧰 工具链

1. **Python**: FastAPI, SQLAlchemy, SQLite
2. **前端**: React, TypeScript, Vite, ApexCharts
3. **构建**: Docker, Docker Compose
4. **测试**: pytest, unittest
5. **版本控制**: Git（ .git/ 目录）