# TICKR — Trading Terminal

A professional trading terminal with real-time charts, stock scanner, and multi-watchlist support.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite + TypeScript |
| Charting | TradingView lightweight-charts v5 |
| State | Zustand |
| Backend | Python FastAPI |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Market Data | ICICI Direct Breeze API (+ mock data fallback) |
| Auth | JWT (RS256) with bcrypt passwords |
| Scheduler | APScheduler (EOD data fetch 3:35 PM IST) |

## Features

- 📈 **Chart Terminal** — Candlestick & line charts, green/red candles, volume bars, price line
- 📊 **Multi-timeframe** — 1D / 1W / 1M with backend aggregation
- 🔌 **Plug-and-play Indicators** — SMA, EMA, BBands (overlay), RSI (sub-chart). Drop a Python file in `backend/app/indicators/plugins/` to add more.
- 🔍 **Stock Scanner** — Technical scans (52-week high, MA Crossover). Drop a file in `backend/app/scanners/plugins/` to add new scanners.
- 📋 **Multi-Watchlist** — Create multiple named watchlists, save scan results as watchlists
- 🌏 **Universe Support** — NIFTY 50, NIFTY NEXT 50, NIFTY 500, NIFTY 1000
- 👤 **Multi-user** — JWT login/register, profile section

## Quick Start

### Prerequisites

- [Node.js 18+](https://nodejs.org)
- [Python 3.11+](https://python.org) ← **Install this first if not done**

### 1. Start the Backend

```bat
cd backend
start.bat
```

Or manually:
```powershell
cd backend
copy .env.example .env   # Edit .env with your credentials
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API Docs: http://localhost:8000/docs

### 2. Start the Frontend

```bat
cd frontend
start.bat
```

Or manually:
```powershell
cd frontend
npm install   # Already done if you followed setup
npm run dev
```

Frontend runs at: http://localhost:5173

### 3. Register & Login

Open http://localhost:5173 → Register a new account → Start trading!

## Configuring the Breeze API

1. Copy `backend/.env.example` to `backend/.env`
2. Fill in your credentials:

```env
BREEZE_API_KEY=your_api_key_here
BREEZE_API_SECRET=your_api_secret_here
BREEZE_SESSION_TOKEN=your_session_token_here
```

3. Session tokens expire daily. Use the endpoint below to refresh:

```
POST /api/scanners/refresh-session?session_token=YOUR_NEW_TOKEN
```

**Until credentials are set**, the app uses realistic mock data automatically — no changes needed.

## Adding a New Indicator (Plug-and-Play)

Create `backend/app/indicators/plugins/my_indicator.py`:

```python
import pandas as pd
from app.indicators.base import BaseIndicator

class MyIndicator(BaseIndicator):
    name = "MACD"
    label = "MACD({fast},{slow},{signal})"
    description = "Moving Average Convergence Divergence"
    category = "momentum"
    overlay = False          # True = on chart, False = sub-chart
    default_params = {"fast": 12, "slow": 26, "signal": 9}
    param_schema = [...]

    def compute(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        # Your computation here
        return df
```

Restart the backend → it auto-discovers the new indicator → appears in the UI dropdown immediately.

## Adding a New Scanner (Plug-and-Play)

Create `backend/app/scanners/plugins/my_scanner.py`:

```python
from app.scanners.base import BaseScanner

class MyScanner(BaseScanner):
    name = "RSI Oversold"
    description = "Stocks with RSI below 30"
    category = "technical"   # or "fundamental" or "plugin"
    param_schema = []

    def run(self, symbols, exchange="NSE", as_of_date=None, **params):
        # Your scan logic here
        return [{"symbol": ..., "price": ..., "change_pct": ...}]
```

Restart the backend → appears in Scanner Setup automatically.

## Project Structure

```
Trading Application/
├── frontend/          # React + Vite
│   ├── src/
│   │   ├── pages/     # ChartPage, ScannerPage, ScanResultsPage, LoginPage
│   │   ├── components/
│   │   │   ├── chart/      # MainChart, SubChart, SymbolBar
│   │   │   ├── indicators/ # IndicatorBar, IndicatorDropdown
│   │   │   ├── watchlist/  # WatchlistPanel
│   │   │   ├── scanner/    # ScannerSetup, ScanResults
│   │   │   └── profile/    # ProfileModal
│   │   ├── store/     # Zustand (auth, chart, watchlist)
│   │   └── api/       # Axios client
│   └── start.bat
│
└── backend/           # Python FastAPI
    ├── app/
    │   ├── indicators/plugins/  # ← Drop indicator plugins here
    │   ├── scanners/plugins/    # ← Drop scanner plugins here
    │   ├── models/    # SQLAlchemy ORM
    │   ├── services/  # BreezeService, Scheduler
    │   └── api/routes/
    ├── .env.example
    └── start.bat
```
