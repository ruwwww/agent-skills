---
name: quant-trading
description: "Use when building quant trading bots or running backtests."
version: 1.0.0
author: Hermes Agent
tags: [quant, trading, backtest, crypto, ccxt, polars, event-driven]
platforms: [linux, macos, windows]
---

# Quantitative Trading & Bot Engineering

A comprehensive guide for building quantitative research pipelines, backtesting engines, and automated execution bots (crypto & equities).

## Key Architecture Principles

1. **Storage, Lake & Throughput First:**
   - Store tick and kline data in columnar format (**Parquet** or **DuckDB**). Avoid row-based databases or raw JSON for historical analysis.
   - Use a **Canonical Parquet Data Lake** (`references/canonical-parquet-lake.md`) to deduplicate downloads across background workers and enable microsecond incremental sync.
   - Use vectorized analytics (**Polars**) for indicator calculation and feature engineering before feeding event-driven simulators.

2. **Network Resilience & ISP DNS Bypass:**
   - In environments with DNS poisoning/ISP filtering on exchange domains (e.g. Binance, Bybit, OKX, Coinbase), standard TLS handshakes fail with hostname mismatch errors.
   - Use a transparent DNS-over-HTTPS (DoH) monkeypatch on `socket.getaddrinfo` to resolve authoritative Cloudflare/Google IPs without requiring root or external VPNs.
   - See `references/isp-dns-bypass.md` for the exact production recipe.

3. **Realistic Execution Friction (Zero-Illusion Backtesting):**
   - **Taker vs Maker Churn:** High-frequency intraday trading with market orders (taker fee ~0.04%-0.06%) rapidly drains capital. 10 trades/day can eat 10-15% of equity per week in fees alone.
   - **Slippage Modeling:** Add at least 1–2 bps slippage on market fills.
   - **Intra-Bar High/Low Stop Triggers:** Check stop-loss and take-profit thresholds against candle highs and lows rather than waiting for bar closes.
   - See `references/friction-and-execution-pitfalls.md`.

## Core Pipeline Components

### 1. Data Collection & Parquet Ingestion
Collect OHLCV data with pagination via CCXT or exchange archives, deduplicate by timestamp, and partition by symbol/interval in Parquet:
```python
import polars as pl

# Fast Parquet schema
df = pl.DataFrame(
    bars,
    schema=["timestamp_ms", "open", "high", "low", "close", "volume"],
    orient="row"
)
df = df.unique(subset=["timestamp_ms"]).sort("timestamp_ms")
df.write_parquet(f"data/parquet/{symbol}_{timeframe}.parquet")
```

### 2. Fast Vectorized Indicators with Polars
Calculate indicators natively in Polars expressions:
- **Daily-Reset VWAP:** `(cum_tp_vol / cum_vol).over("day_id")`
- **ATR:** `max(high - low, abs(high - prev_close), abs(low - prev_close)).ewm_mean(span=period)`
- **EMA:** `col("close").ewm_mean(span=period)`

### 3. Event-Driven Paper Broker
Test strategies using a simulated broker supporting:
- Position tracking (Flat, Long, Short)
- Fixed Stop-Loss, Take-Profit, and Trailing Stops
- Dynamic position sizing: `qty = (equity * risk_pct) / (stop_distance)`
- See `templates/paper_broker_template.py` for a reusable implementation.

### 4. Live Streaming Execution & Background Daemons
- Maintain an in-memory rolling candle window (e.g. last 100-200 bars).
- Subscribe to real-time WebSocket streams (`<symbol>@kline_<timeframe>` or `<symbol>@trade`).
- Recalculate indicators on closed bars and trigger market/limit orders via the execution layer.
- Run as an asynchronous background daemon with PID tracking, log redirection, and graceful signal handling (SIGTERM/SIGINT).

### 5. Telemetry, Dashboards & Automated Experiments (Prometheus + Grafana)
- **User Preference (Monitoring & Observability):** Always use **Grafana** (backed by Prometheus and SQLite) as the primary observability layer for quant systems. Ensure any new telemetry (live execution, background experiment sweeps, and signal backlogs) is directly integrated into provisioned Grafana dashboard panels rather than relying exclusively on CLI logs or external chat bots.
- **Prometheus Exporter (`:9108/metrics`):** Expose real-time gauges for equity, unrealized/realized PnL, current drawdown, live mark price, and active position size.
- **SQLite-to-Prometheus Sync Pattern:** When on-demand batch simulations write directly to SQLite, the exporter daemon must query and sync aggregate statistics (`COUNT(*)`, `MAX(return_pct)`, `MAX(sharpe_ratio)` grouped by strategy/symbol/timeframe) into Prometheus gauges on each sync cycle. This ensures Grafana updates dynamically without requiring container restarts.
- **Signal Backlog Gauges & Counters:** Expose `quant_signals_total`, `quant_signals_executed_total`, `quant_signals_rejected_total`, `quant_signals_backlog_total`, and `quant_signal_latest_entry` so Grafana can render real-time signal flow tables and risk-rejection gauges without external database plugins.
- **Background Experiment Worker:** Run periodic backtest parameter sweeps (e.g. every few days or on-demand rather than constant 24/7 loops) and push completed run metrics (Sharpe, Profit Factor, Win Rate, Return %) to Prometheus gauges and an internal SQLite ledger.
- **Grafana Stack:** Auto-provision Prometheus datasource and JSON dashboards via Docker Compose (`network_mode: host`) with anonymous admin access for zero-auth terminal visualization.
- See `references/grafana-prometheus-telemetry.md` for the complete telemetry architecture, dashboard layout, and container lifecycle.

### 6. Multi-Strategy Research Matrix & Overcoming Fee Drag
- **Why Naive Intraday Breakouts Lose:** Testing 5m/15m mean-breakouts (like VWAP or Bollinger bands alone) generates 50+ trades/month. In crypto markets, 0.04% taker fees eat 10%+ of the account before trends mature.
- **Sustained Trend-Following (1h+):** Use higher-timeframe EMA 20/50 + Donchian breakouts with 1.5% ATR trailing stops. Reduces trade churn, lets winners run to 3x+ risk-reward, and generates positive net alpha (+7.42% net on BTC 1h).
- **Leaderboards & Alpha Alerting:** Expose multidimensional gauges (`quant_exp_return_pct{strategy, symbol, timeframe}`) and persist discoveries (`return_pct > 0 and profit_factor > 1.1`) to an automated alert feed and CLI leaderboard.

### 7. Decoupled Signal Architecture & Persistent Backlog Ledger
- **Never couple signal generation directly to execution or chat notifications.**
- Generate immutable `SignalEvent` objects containing technical indicator snapshots at emission.
- Store all signals in a persistent **Signal Backlog** (SQLite + Apache Parquet export) for offline quantitative audit, MFE/MAE analysis, and indicator feature attribution.
- Route signals through a dedicated **Pre-Trade Risk Filter** (verifying stop loss, minimum SL distance, R:R ratio, and portfolio margin limits) before hitting the execution broker.
- See `references/decoupled-signals-and-backlog.md` for the full schema and workflow.

### 8. Repository Hygiene & Version Control in Quant Systems
- **Strict `.gitignore` Boundaries:** Always exclude binary Parquet datasets (`data/parquet/*.parquet`), SQLite databases (`data/*.db`), daemon process IDs (`data/*.pid`), runtime logs (`data/*.log`), and virtual environments (`.venv/`) from version control.
- Keep the Git tree 100% clean and code-only to enable rapid CI/CD, modular refactoring, and multi-agent coordination without repo bloat.

### 9. Scaled Multi-Core Simulation Engine (Alpha Factory)
- **Batch / Periodic Runs over Constant 24/7 Spinning:** Backtesting does not require real-time websocket streams. Avoid burning CPU in rapid 60-second micro-loops; operate it as an on-demand or periodic batch engine (e.g. running sweeps every few days).
- **Multiprocessing Start Method:** Always use `multiprocessing.get_context('spawn')` when worker processes might inherit network patches (DoH monkeypatch), active threading locks, or Rich logging handlers from the parent process to prevent deadlocks.
- **Suppress Verbose Logging:** Pass `verbose=False` to broker and backtest engine instances during bulk parameter sweeps. Eliminates thousands of stdout log lines that bottleneck subprocess pipes.
- **Single-Transaction Batch SQLite Ingestion:** Never commit individual backtest results one by one (`conn.commit()` in a loop triggers thousands of disk fsyncs, taking minutes). Use `executemany()` in a single transaction to persist 1,500+ records in <0.1s.
- **Throughput Benchmark:** Saturated 6-core multiprocessing over pre-synced local Parquet datasets achieves **600–750 backtest runs/second**.
- See `references/scaled-simulation-engine.md` for the complete architecture and parameter grid blueprint.

### 10. Multi-Asset Class Extension: Forex & Commodities
- **Pip & Sizing Mechanics:** Unlike crypto's unit contract, Forex trades in lots (100,000 units standard, 10,000 mini, 1,000 micro). Pips are 0.0001 for 4-digit majors (`EUR/USD`, `GBP/USD`) and 0.01 for JPY pairs (`USD/JPY`) and Gold (`XAU/USD` = $0.10/point).
- **Execution Cost: ECN Spread vs Percentage Fees:** Do not charge crypto taker % fees on Forex; model realistic institutional ECN spreads (e.g. 0.8 pips EUR/USD, 1.2 pips GBP/USD, 2.5 pips Gold) split half-on-entry and half-on-exit with nominal ECN commission ($2.50 per 100k units).
- **Currency Conversion on Non-USD Quote Currency:** When trading JPY-quoted pairs (`USD/JPY`), convert PnL to USD: `pnl_usd = ((exit_price - entry_price) * size) / exit_price`.
- **Zero-Fee Continuous Data Feed:** Ingest historical Forex/Commodity data via Yahoo Finance v8 chart API using an authenticated cookie + crumb handshake (`fc.yahoo.com` -> `query2.finance.yahoo.com/v1/test/getcrumb`). Resample 1h bars into 4h intervals natively using Polars `group_by_dynamic("timestamp", every="4h")`.
- **Dynamic Sizing & Stop Floor:** Use a pip-based floor for stop-loss distance (`5 * pip_size`) instead of crypto's percentage floor, and permit institutional leverage bounds (10x–30x).
- See `references/forex-and-commodities-execution.md` for instrument registries and execution logic.


