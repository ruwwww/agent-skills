# High-Performance Scaled Simulation Engine (Alpha Factory)

A reference guide for building high-throughput, multi-core combinatorial backtest engines across multi-asset universes and parameter spaces.

---

## 1. Core Architecture & Process Model

Unlike live trading bots that stream real-time WebSocket ticks 24/7, backtesting is a **finite, batch-oriented compute task**. Running a continuous background loop every 60 seconds burns CPU and locks resources unnecessarily. Instead, operate it as an **on-demand or periodic batch simulation engine** (e.g. executed every few days or on new data arrivals).

```
[ Pre-Synced Parquet Data Lake ]
               │
               ▼
[ Combinatorial Task Generator ] (Cartesian product across strategies, assets, timeframes, params)
               │
               ▼
[ ProcessPoolExecutor (mp_context='spawn') ]
   ├── Worker 1 (Core 1): In-memory simulation over local Parquet
   ├── Worker 2 (Core 2): In-memory simulation over local Parquet
   ├── ...
   └── Worker N (Core N): In-memory simulation over local Parquet
               │ (Throughput: 500 – 750 backtest runs / sec)
               ▼
[ Single-Transaction Atomic SQLite Ingestion ] (executemany in 0.1s)
               │
               ▼
[ Multi-dimensional Prometheus Gauges & Grafana Leaderboard ]
```

---

## 2. Essential Engineering Pitfalls & Fixes

### A. Linux Multiprocessing Deadlocks (`spawn` vs `fork`)
- **Pitfall:** On Linux, `ProcessPoolExecutor` defaults to `fork`. If the parent process has imported logging handlers (`RichHandler`), active threading locks, or network socket patches (`socket.getaddrinfo` DoH patch), child processes will deadlock silently on `executor.submit()` or `future.result()`.
- **Fix:** Always explicitly configure the start context to `spawn`:
  ```python
  import multiprocessing as mp
  from concurrent.futures import ProcessPoolExecutor

  ctx = mp.get_context("spawn")
  with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as executor:
      # Submit tasks cleanly without inheriting locked state
  ```

### B. Broker Logging I/O Bottleneck
- **Pitfall:** An event-driven paper broker logging every order, fill, stop-loss trigger, or trailing stop hit generates 100–300 log lines per run. Across 1,000 parallel simulations, 200,000+ log lines saturate stdout/stderr pipes, causing multi-minute timeouts.
- **Fix:** Pass `verbose=False` to `PaperBroker` and `BacktestEngine` during bulk sweeps:
  ```python
  # Only log when verbose is explicitly enabled
  if self.verbose:
      logger.info(f"Order filled: {order.order_id}")
  ```

### C. SQLite Individual Commit Disaster (fsync Serialization)
- **Pitfall:** Calling `cursor.execute(...)` followed by `conn.commit()` in a loop across 1,000+ simulation results triggers 1,000+ separate disk fsync operations. On modern Linux filesystems with journaling, this can take 180–300+ seconds.
- **Fix:** Group all completed run records into a list and persist in a single atomic transaction via `executemany()`:
  ```python
  def log_experiments_batch(self, experiments: List[Dict[str, Any]]):
      records = [(r["id"], r["strategy"], ...) for r in experiments]
      with self._get_conn() as conn:
          conn.cursor().executemany("""
              INSERT OR REPLACE INTO experiments (...) VALUES (?, ?, ...)
          """, records)
          conn.commit()  # Single fsync: completes 1,600+ records in <0.1s
  ```

---

## 3. Multidimensional Coverage Axis Blueprint

1. **Asset Universe:**
   - Top liquid crypto pairs: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `DOGE/USDT`, `XRP/USDT`, `BNB/USDT`.
   - Pre-sync each pair once into the Canonical Parquet Lake (`data/parquet/`) before starting worker processes.

2. **Timeframes:**
   - `15m`: Intraday volatility & mean-reversion.
   - `1h`: Structural trend-following (sweet spot for fee reduction).
   - `4h`: Macro swing regimes.

3. **Parameter Spaces:**
   - **Trend Following:** Fast EMA (10, 20, 30) $\times$ Slow EMA (40, 60, 100) $\times$ SL ATR (1.2, 1.8, 2.5) $\times$ TP ATR (2.5, 3.5, 5.0) $\times$ Trailing Stop (1.5%, 2.5%).
   - **Mean Reversion:** Bollinger Bands Std (1.8, 2.2, 2.6) $\times$ RSI Oversold (20, 28) $\times$ Overbought (72, 80) $\times$ SL/TP multipliers.
   - **VWAP Momentum:** Band ATR Multiplier (1.8, 2.2, 2.8) $\times$ SL/TP.

---

## 4. Benchmark Throughput

On an 8-core Linux host with 6 dedicated workers:
- **1,620 total backtests** over 45 days of 1h and 4h data.
- Execution time: **2.56 seconds**.
- Throughput: **673 runs/second**.
- Alpha discoveries (Return > 0 & Profit Factor > 1.1): **677 strategies (41.8% hit rate)**.
