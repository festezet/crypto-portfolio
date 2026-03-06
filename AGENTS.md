# AGENTS.md

## Project Overview

**Crypto Portfolio Tracker** is a multi-exchange cryptocurrency portfolio tracking application with automated exit strategies and tax calculation for French tax reporting (FIFO method).

## Key Facts

- **Author**: Fabrice Estezet
- **Stack**: Python 3, Flask, SQLite, Chart.js, CoinGecko API
- **License**: Personal use
- **Status**: Production

## Architecture

```
backend/app.py          → Flask application entry point
backend/api/routes.py   → REST API endpoints
backend/models/         → SQLAlchemy models (Transaction, Crypto, Strategy)
backend/services/       → Business logic (portfolio, tax, import)
frontend/templates/     → Jinja2 HTML templates
frontend/static/        → CSS, JavaScript, Chart.js visualizations
```

## API Endpoints

- `GET /api/portfolio` - Portfolio summary with real-time valuation
- `GET /api/holdings` - Detailed positions with P&L
- `GET /api/transactions` - Transaction history
- `POST /api/import` - Import CSV from Binance/Kucoin
- `GET /api/fiscal/<year>` - Tax report (French FIFO method)
- `GET /api/strategies` - Exit strategy configuration

## Skills Demonstrated

- REST API design with Flask
- Financial calculations (PMP, P&L, FIFO tax)
- Multi-exchange data aggregation
- Real-time price integration via CoinGecko
- SQLite database with SQLAlchemy ORM
- Interactive charts with Chart.js
