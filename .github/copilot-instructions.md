# Copilot Instructions

## Build, Test & Lint

### Backend (Python)
- **Install dependencies**: `uv sync` (uses `uv` for fast Python dependency management)
- **Run dev server**: `uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8777`
- **Run all tests**: `uv run pytest`
- **Run specific test file**: `uv run pytest tests/test_backtest_market_rules.py -q`
- **Run single test**: `uv run pytest tests/test_market_api.py::test_market_normalization -v`
- **No built-in linter** — code style is not automated

### Frontend (Node.js)
- **Install dependencies**: `npm install` (from `frontend/` directory)
- **Dev server**: `npm run dev` (runs on port 5173, proxies `/api` to backend)
- **Build**: `npm run build` (TypeScript compile + Vite bundle, outputs to `frontend/dist`)
- **Type check**: Included in `npm run build` via `tsc`
- **No linter** — style/lint checks are not automated

### Docker
- **Build & start**: `docker-compose up --build` (from root)
  - Frontend accessible at `http://localhost:8081`
  - Backend accessible at `http://localhost:8777`, docs at `/docs`

## High-Level Architecture

### Multi-Market Design
The system supports three markets with different trading rules:
- **US**: Single-stock units, no T+1, no price limits, no trading tax
- **CN (A-shares)**: 100-share lots, T+1 restriction, stamp tax on sells, price limits, one-character up/down board restrictions
- **HK**: Board lot sizing by stock, stamp tax on sells

All API endpoints accept `?market=US|CN|HK` parameter (defaults to US). Market-specific logic lives in:
- `backend/markets/base.py`, `backend/markets/cn.py`, `backend/markets/hk.py` — data source adapters & symbol normalization
- `backend/backtest/market_config.py` — backtest rule configuration per market
- `backend/market_data_manager.py` — unified data read/write layer

### Backend (FastAPI + SQLAlchemy + SQLite)

**Key modules:**
- `backend/routers/` — API endpoints for stocks, backtest, data sync
- `backend/backtest/engine.py` — core backtest execution loop
- `backend/backtest/strategies.py` — built-in strategies (SMA Crossover, RSI, MACD, Buy & Hold)
- `backend/backtest/indicators.py` — technical indicators (RSI, MACD, SMA, EMA, Bollinger Bands, ATR)
- `backend/backtest/market_config.py` — market-specific trading rules
- `backend/analyzers/` — technical analysis calculations
- `backend/crawlers/` — US data fetching and cleaning via yfinance
- `backend/markets/symbols.py` — symbol normalization (e.g., `600519` → `SH.600519` for CN, `00700` → `HK.00700` for HK)
- `backend/models/` — Pydantic models for API responses and database schemas
- `backend/database.py` — SQLAlchemy setup and initialization
- `backend/config.py` — settings via `config.yaml` or env vars

**Data sources:**
- US stocks: yfinance via `backend/crawlers/`
- CN/HK stocks: AkShare via `backend/market_data_manager.py`

### Frontend (React + TypeScript + Vite)

**Key structure:**
- `frontend/src/api/` — axios-based API client wrappers
- `frontend/src/views/` — pages (Stock List, Analysis, Backtest, Compare)
- `frontend/src/components/` — reusable UI components (charts, tables, filters)
- `frontend/src/stores/` — state management (likely Zustand or similar)
- `frontend/src/i18n/` — internationalization (Chinese & English)
- `frontend/src/types/` — TypeScript interfaces
- `frontend/src/styles/` — SCSS global styles
- `vite.config.ts` — build config with proxy to backend API

**Charts:** ApexCharts (for candlestick/OHLC) and Recharts (for time-series analysis)

## Key Conventions

### Symbol Normalization
All user input symbols are normalized before API calls:
- **A-shares (CN)**: `600519` / `SH600519` / `SH.600519` all normalize to `SH.600519`
  - Prefix: `SH.` (Shanghai), `SZ.` (Shenzhen), `BJ.` (Beijing)
- **Hong Kong (HK)**: `700` / `00700` / `HK700` / `HK.00700` all normalize to `HK.00700`
- **US**: `aapl` / `AAPL` both normalize to `AAPL` (uppercase)

Normalization happens in `backend/markets/symbols.py`. Tests in `tests/test_market_symbols.py`.

### Backtest Engine Behavior
- **Return data**: Backtest results always include `market_rules` (snapshot of applied trading constraints) plus metrics (Sharpe, Sortino, max drawdown), equity curve, drawdown curve, and trade records
- **Rejected signals**: The engine tracks rejected trades with reasons like `t_plus_one`, `price_limit_up_locked`, `price_limit_down_locked`, `insufficient_cash`, `invalid_quantity`. These are internal but may be exposed in future API updates.
- **Strategy interface**: All strategies implement `on_start()`, `on_bar(bar)`, `on_stop()` lifecycle methods and access `self.engine` for `buy()`, `sell()`, `get_position()` calls
- **Market rules applied**: Backtest engine pulls rules from `get_market_backtest_config(market)` and enforces them during order validation

### Data Lazy Loading
Data is downloaded on-demand: first API request to a stock triggers automatic download if not cached. Tests mock this or use `POST /api/backtest/warmup?market=...` to pre-fetch.

### API Response Structure
- All endpoints support `?market=US|CN|HK`; default is US
- Date/time fields use ISO 8601 format
- Market-specific fields may be included based on the market parameter
- Backtest `/run` and `/compare` responses include full metric objects with equity/drawdown curves

### Testing Patterns
- Tests use `conftest.py` for shared fixtures
- Market-specific tests (e.g., `test_backtest_market_rules.py`) instantiate market-aware strategy classes and verify trading constraint enforcement
- API tests check response structure for multi-market support (tests verify that `market` parameter is respected)

## Project Structure Reference

```
backend/
  routers/
    stocks.py       # Stock list, details, daily/kline data, financials
    backtest.py     # Run backtest, compare strategies, market rules, status
    data_sync.py    # Download, update, refresh-prices
  backtest/
    engine.py       # Core backtest loop, order validation, position tracking
    strategies.py   # SMA Crossover, RSI, MACD, Buy & Hold
    indicators.py   # RSI, MACD, SMA, EMA, Bollinger Bands, ATR
    market_config.py# Market-specific trading rules
    metrics.py      # Performance calculation (Sharpe, Sortino, Calmar, max drawdown)
  markets/
    base.py         # Market adapter interface
    cn.py           # CN market data source & rules
    hk.py           # HK market data source & rules
    symbols.py      # Symbol normalization
    registry.py     # Market registry
  models/
    stock.py        # Stock, KLine, daily data models
    backtest.py     # BacktestRequest, BacktestResult models
    market.py       # Market-specific models
  database.py       # SQLAlchemy session factory, init_db()
  config.py         # Settings via config.yaml or env vars
  main.py           # FastAPI app setup

frontend/
  src/
    api/            # axios wrappers for /api/stocks, /api/backtest, /api/data
    views/          # Stock List, Analysis, Backtest, Compare pages
    components/     # Charts, tables, filters
    stores/         # State management
    i18n/           # Translations (Chinese, English)
    types/          # TypeScript interfaces
    styles/         # SCSS global styles

tests/
  test_backtest_market_rules.py  # Market rule enforcement & engine behavior
  test_market_symbols.py         # Symbol normalization tests
  test_market_api.py             # Multi-market API contract tests
  test_backtest_api.py           # Backtest endpoint tests
  ...
```

## MCP Servers (Optional)

### Playwright
If using VS Code or Cursor with Playwright MCP enabled, you can:
- **Browser testing**: Automate frontend UI testing (e.g., stock list navigation, backtest form submission)
- **Web scraping**: Extract data from pages during development
- **Screenshot validation**: Capture and compare UI states

To enable: Configure your AI assistant settings to include the Playwright MCP server. No additional setup needed in this repo—it works out of the box with the existing frontend.

## Common Tasks

### Add a New Backtest Strategy
1. Implement a class in `backend/backtest/strategies.py` with `on_start()`, `on_bar(bar)`, `on_stop()` methods
2. Register it in the strategies list returned by `GET /api/backtest/strategies`
3. Add test in `tests/test_backtest_*.py` to verify market rule enforcement
4. Update frontend to show it in the Backtest page dropdown

### Add Market-Specific Logic
1. Check if logic applies only to one market or all three (CN, HK, US)
2. For market-specific: extend `backend/markets/base.py` in the market subclass (`cn.py`, `hk.py`)
3. For backtest rules: add to `backend/backtest/market_config.py` in `get_market_backtest_config()`
4. Always test with `?market=CN` / `?market=HK` / `?market=US` variants

### Modify Frontend Pages
1. Routes defined in `frontend/src/views/` (React Router)
2. API calls use `frontend/src/api/` axios wrappers
3. Charts use ApexCharts or Recharts; keep responsive
4. i18n strings go in `frontend/src/i18n/` JSON files (Chinese + English)
5. Build and test with `npm run build` before committing

### Debug Backtest Issues
1. Run `uv run pytest tests/test_backtest_market_rules.py -v` to see engine behavior
2. Check `backend/backtest/engine.py` for order validation and `market_config.py` for rule application
3. Backtest results include `market_rules` snapshot—verify expected rules are present
4. Use backend `/docs` (Swagger) to test API payload before wiring frontend
