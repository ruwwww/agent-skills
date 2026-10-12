# Prometheus & Grafana Telemetry for Quant Trading Systems

## 1. Exporter Architecture

In a quant execution daemon, expose an internal Prometheus metrics server (e.g. on port `9108`) using `prometheus_client`:

```python
from prometheus_client import Gauge, Counter, start_http_server

# Real-time Trading Metrics
GAUGE_EQUITY = Gauge("quant_equity_usd", "Current account equity in USD")
GAUGE_CASH = Gauge("quant_cash_usd", "Current account cash in USD")
GAUGE_UNREALIZED_PNL = Gauge("quant_unrealized_pnl_usd", "Current unrealized PnL in USD")
GAUGE_REALIZED_PNL = Gauge("quant_realized_pnl_usd", "Cumulative realized PnL in USD")
GAUGE_DRAWDOWN_PCT = Gauge("quant_drawdown_pct", "Current drawdown percentage")
GAUGE_MARKET_PRICE = Gauge("quant_market_price_usd", "Latest market mark price", ["symbol"])
GAUGE_POSITION_SIZE = Gauge("quant_position_size", "Current active position size (signed)", ["symbol"])

COUNTER_TRADES_TOTAL = Counter("quant_trades_total", "Total executed trades count")

# Signal Backlog & Pre-Trade Risk Metrics
COUNTER_SIGNALS_TOTAL = Counter("quant_signals_total", "Total signals generated across strategies", ["strategy", "side"])
COUNTER_SIGNALS_EXECUTED = Counter("quant_signals_executed_total", "Total signals approved and executed", ["strategy", "side"])
COUNTER_SIGNALS_REJECTED = Counter("quant_signals_rejected_total", "Total signals rejected by risk filter", ["strategy", "reason"])
GAUGE_SIGNALS_BACKLOG_COUNT = Gauge("quant_signals_backlog_total", "Total signals recorded in persistent backlog")
GAUGE_SIGNAL_LATEST = Gauge("quant_signal_latest_entry", "Latest signal entry and status", ["signal_id", "strategy", "symbol", "side", "status", "rr_ratio"])

# Multi-dimensional Experiment & Alpha Discovery Metrics
GAUGE_EXP_COUNT = Gauge("quant_experiments_total", "Total completed background experiments")
GAUGE_EXP_ALPHA_COUNT = Gauge("quant_exp_alpha_total", "Total experiments yielding positive alpha")

GAUGE_EXP_SHARPE = Gauge("quant_exp_sharpe", "Sharpe ratio of experiment", ["strategy", "symbol", "timeframe"])
GAUGE_EXP_RETURN_PCT = Gauge("quant_exp_return_pct", "Net return pct of experiment", ["strategy", "symbol", "timeframe"])
GAUGE_EXP_PROFIT_FACTOR = Gauge("quant_exp_profit_factor", "Profit factor of experiment", ["strategy", "symbol", "timeframe"])
GAUGE_EXP_WIN_RATE = Gauge("quant_exp_win_rate", "Win rate pct of experiment", ["strategy", "symbol", "timeframe"])
GAUGE_EXP_MAX_DRAWDOWN = Gauge("quant_exp_max_drawdown", "Max drawdown pct of experiment", ["strategy", "symbol", "timeframe"])
GAUGE_EXP_TRADES = Gauge("quant_exp_trades", "Number of trades in experiment", ["strategy", "symbol", "timeframe"])

def start_metrics_server(port: int = 9108):
    start_http_server(port, addr="0.0.0.0")
```

## 2. Docker Compose (Prometheus + Grafana with Network Host)

Using `network_mode: host` avoids port translation overhead and lets Prometheus scrape `localhost:9108` directly:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: quant_prometheus
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./deploy/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.listen-address=0.0.0.0:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: quant_grafana
    restart: unless-stopped
    network_mode: host
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
      - GF_SERVER_HTTP_PORT=3000
    volumes:
      - ./deploy/grafana/provisioning/datasources:/etc/grafana/provisioning/datasources:ro
      - ./deploy/grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./deploy/grafana/dashboards:/var/lib/grafana/dashboards:ro
```

## 3. Prometheus Scrape Configuration (`deploy/prometheus.yml`)

```yaml
global:
  scrape_interval: 2s
  evaluation_interval: 2s

scrape_configs:
  - job_name: "quant_daemon"
    static_configs:
      - targets: ["localhost:9108"]
```

## 4. SQLite Ledger Integration & Exporter Database Sync

Pair Prometheus with an on-disk SQLite database (`data/quant_lab.db`) to record permanent relational logs:
- `experiments`: Tracks `experiment_id`, `strategy_name`, `symbol`, `timeframe`, `bars_tested`, `net_profit`, `return_pct`, `win_rate_pct`, `profit_factor`, `sharpe_ratio`, `max_drawdown_pct`, and parameter JSON.
- `trades`: Individual fill records with price, quantity, fee, and closing PnL.
- `equity_snapshots`: Periodic equity, cash, unrealized/realized PnL, and drawdown percentage for historical replay.

### The SQLite-to-Prometheus Sync Pattern (Crucial for Batch Simulations)
**Pitfall:** Scaled simulations and parameter sweeps often run on-demand via CLI scripts (`run_scaled_simulation.py`) and write directly to SQLite. If the Prometheus exporter daemon only tracks its own internal live loop, Grafana will not show the bulk simulation results, leading users to believe the container or dashboard is broken.

**Solution:** The telemetry daemon must periodically sync aggregate statistics directly from SQLite into Prometheus gauges:
```python
def sync_experiments_from_db(db: ExperimentDB):
    stats = db.get_experiment_summary_stats()
    GAUGE_EXP_COUNT.set(stats["total"])
    GAUGE_EXP_ALPHA_COUNT.set(stats["alpha"])
    for m in stats["matrix"]:
        strat = m["strategy_name"]
        sym = m["symbol"].replace("/", "")
        tf = m["timeframe"]
        GAUGE_EXP_RETURN_PCT.labels(strategy=strat, symbol=sym, timeframe=tf).set(float(m.get("return_pct") or 0.0))
        GAUGE_EXP_SHARPE.labels(strategy=strat, symbol=sym, timeframe=tf).set(float(m.get("sharpe_ratio") or 0.0))
        GAUGE_EXP_PROFIT_FACTOR.labels(strategy=strat, symbol=sym, timeframe=tf).set(float(m.get("profit_factor") or 0.0))
        GAUGE_EXP_WIN_RATE.labels(strategy=strat, symbol=sym, timeframe=tf).set(float(m.get("win_rate_pct") or 0.0))
        GAUGE_EXP_MAX_DRAWDOWN.labels(strategy=strat, symbol=sym, timeframe=tf).set(float(m.get("max_drawdown_pct") or 0.0))
        GAUGE_EXP_TRADES.labels(strategy=strat, symbol=sym, timeframe=tf).set(float(m.get("total_trades") or 0.0))
```
This guarantees that any batch simulation instantly updates Grafana without requiring container restarts or third-party database plugins.

## 5. Dashboard Provisioning & Container Lifecycle

- **No Container Restarts for Metric Updates:** Grafana queries Prometheus dynamically on every dashboard refresh interval (e.g. 2s or 5s). When Prometheus metrics update, Grafana reflects the new data immediately upon browser refresh (F5). Never restart Grafana containers just to pick up new metric values.
- **Visual Section Organization:** Group panels into distinct collapsible rows with explicit headers to avoid user confusion:
  1. *Row 1:* Live Paper Trading Telemetry (Equity, Cash, Mark Price, Realized/Unrealized PnL)
  2. *Row 2:* Live Equity & Asset Curves (Timeseries)
  3. *Row 3:* Scaled Simulations & Multi-Strategy Matrix (Total Runs, Alpha Hits, Asset x Timeframe Heatmap/Bar Gauge, Leaderboard Table)
  4. *Row 4:* Signal Backlog & Pre-Trade Risk Intelligence (Signals Emitted, Executed, Risk Filter Rejections, Recent Backlog Table)

