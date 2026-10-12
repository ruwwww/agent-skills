# Decoupled Signal Engine & Persistent Backlog Architecture

## 1. The Decoupling Principle
Never tightly couple strategy signal generation directly to notification dispatchers (Telegram/Discord) or order execution. In a professional quant stack, the signal generation layer must produce immutable `SignalEvent` objects that flow into a persistent audit ledger before hitting downstream filters.

```
[ Strategy / Alpha Model ]
           │
           ▼
     [ SignalEvent ] ───▶ Technical Indicators Snapshot (ATR, EMA, VWAP, RSI)
           │
           ▼
[ Persistent Backlog Ledger ] ───▶ SQLite (`signal_backlog`) & Parquet Export
           │
           ▼
  [ Pre-Trade Risk Filter ]
     ├── Rejection ───▶ Update Backlog: REJECTED_RISK (Record Reason)
     │                  (SL too tight, Suboptimal R:R, Max Exposure)
     └── Approval  ───▶ Update Backlog: ACCEPTED
                              │
                              ▼
                     [ Execution Engine ] ───▶ PaperBroker / Live Exchange
                              │
                              ▼
                     Update Backlog: EXECUTED (Order ID & Fill Price)
```

## 2. SignalEvent Schema
An immutable dataclass capturing complete decision context:
- `signal_id`: Unique identifier (e.g. `sig_trend_btc_1h_...`)
- `strategy_name`: Name of strategy generating the signal
- `symbol` & `timeframe`: Asset pair and bar period
- `side`: BUY or SELL
- `entry_price`: Reference bar close or trigger price
- `stop_loss` & `take_profit`: Defined price levels
- `risk_reward_ratio`: Automatically calculated as `abs(tp - entry) / abs(entry - sl)`
- `confidence`: Optional model confidence (0.0 to 1.0)
- `indicators_snapshot`: Key indicator values at the exact moment of signal emission (vital for post-trade feature attribution and decay analysis)
- `status`: Enum (`GENERATED`, `ACCEPTED`, `REJECTED_RISK`, `EXECUTED`, `EXPIRED`, `CANCELLED`)
- `execution_notes`: Detailed rejection reasons or order fill information

## 3. Persistent Backlog Storage (SQLite + Parquet Lake Export)
Store every emitted signal in SQLite for fast relational querying, and provide a one-click export to Apache Parquet:
- **SQLite Table:**
  ```sql
  CREATE TABLE IF NOT EXISTS signal_backlog (
      signal_id TEXT PRIMARY KEY,
      strategy_name TEXT NOT NULL,
      symbol TEXT NOT NULL,
      timeframe TEXT NOT NULL,
      side TEXT NOT NULL,
      entry_price REAL NOT NULL,
      stop_loss REAL,
      take_profit REAL,
      trailing_stop_pct REAL,
      confidence REAL,
      indicators_json TEXT,
      status TEXT NOT NULL,
      execution_notes TEXT,
      created_at TIMESTAMP NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_signals_strat_sym ON signal_backlog (strategy_name, symbol, created_at);
  ```
- **Parquet Export for Vectorized Research:**
  Export the backlog to `data/parquet/signals_backlog.parquet` to allow Polars/DuckDB notebooks to perform:
  - Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) analysis.
  - Correlation between indicator values at emission and subsequent forward returns.
  - Identification of false-positive clusters across market regimes.

## 4. Pre-Trade Quantitative Risk Filter
Always place an independent risk gatekeeper between the signal and the broker:
- **Stop Loss Enforcement:** Reject any signal without a defined stop loss.
- **Minimum SL Distance:** Enforce a minimum stop distance (e.g. $\ge 0.3\%$) to avoid fee churn and spread drag.
- **Risk-Reward Threshold:** Require a minimum theoretical R:R ratio (e.g. $\ge 1.2$ or $1.5$).
- **Portfolio Exposure Limits:** Prevent opening positions if maximum concurrent open positions or margin usage is exceeded.
