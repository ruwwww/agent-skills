# Canonical Parquet Data Lake (Zero-Duplication & Incremental Sync)

When running background quant daemons and continuous parameter sweep workers, naive collectors re-download historical bars from the exchange every cycle. This causes:
1. **Network & Rate-Limit Churn:** Repeated calls to exchange APIs trigger 429 rate-limit bans or connection drops.
2. **Disk & Data Duplication:** Redundant Parquet files clutter storage with duplicate timestamps.
3. **Execution Delay:** Backtests wait 5–15 seconds per download instead of executing in milliseconds.

## 1. Canonical Store Design

Maintain a single authoritative Parquet file per asset and timeframe:
`data/parquet/{SYMBOL}_{TIMEFRAME}.parquet` (e.g. `BTCUSDT_1h.parquet`).

### Core Rules:
1. **Check Local Cache First:** If the file exists, read `min(timestamp_ms)` and `max(timestamp_ms)` via Polars.
2. **Incremental Sync Forward:** If `(now - max_ts) > timeframe_interval`, only fetch bars where `since = max_ts + 1`.
3. **Incremental Prepend Backward:** If the experiment requires older history than `min_ts`, only fetch `since = target_start` until `min_ts`.
4. **Deduplicate & Upsert:** Merge existing and new slices, run `.unique(subset=['timestamp_ms']).sort('timestamp_ms')`, and overwrite the canonical file.
5. **Instant In-Memory Slice:** Return the requested historical window directly from disk (takes 50–200ms).

## 2. Production Implementation (`ParquetDataLake`)

```python
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
import polars as pl
from src.data.collector import DataCollector

class ParquetDataLake:
    def __init__(self, lake_dir: str = "data/parquet"):
        self.lake_dir = os.path.abspath(lake_dir)
        os.makedirs(self.lake_dir, exist_ok=True)
        self.collector = DataCollector()

    def _get_parquet_path(self, symbol: str, timeframe: str) -> str:
        clean_symbol = symbol.replace("/", "").replace(":", "_").upper()
        return os.path.join(self.lake_dir, f"{clean_symbol}_{timeframe}.parquet")

    def get_or_sync(
        self,
        symbol: str,
        timeframe: str,
        days: int = 14,
        force_refresh: bool = False
    ) -> pl.DataFrame:
        path = self._get_parquet_path(symbol, timeframe)
        target_start_dt = datetime.now(timezone.utc) - timedelta(days=days)
        target_start_ms = int(target_start_dt.timestamp() * 1000)

        existing_df: Optional[pl.DataFrame] = None
        if os.path.exists(path) and not force_refresh:
            try:
                existing_df = pl.read_parquet(path)
            except Exception:
                existing_df = None

        if existing_df is not None and len(existing_df) > 0:
            earliest_ts = existing_df["timestamp_ms"].min()
            latest_ts = existing_df["timestamp_ms"].max()
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

            tf_ms = {
                "1m": 60_000, "5m": 300_000, "15m": 900_000,
                "1h": 3600_000, "4h": 14400_000, "1d": 86400_000
            }.get(timeframe, 900_000)

            new_dfs = [existing_df]

            # 1. Fetch missing older data if requested range extends further back
            if earliest_ts > target_start_ms + tf_ms:
                since_dt = target_start_dt.strftime("%Y-%m-%d %H:%M:%S")
                until_dt = datetime.fromtimestamp(earliest_ts / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                older_df = self.collector.fetch_ohlcv(symbol, timeframe, since_str=since_dt, until_str=until_dt)
                if len(older_df) > 0:
                    new_dfs.append(older_df)

            # 2. Fetch incremental newer data up to now
            if (now_ms - latest_ts) > (tf_ms * 1.5):
                since_dt = datetime.fromtimestamp((latest_ts + 1) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                newer_df = self.collector.fetch_ohlcv(symbol, timeframe, since_str=since_dt)
                if len(newer_df) > 0:
                    new_dfs.append(newer_df)

            if len(new_dfs) > 1:
                combined = pl.concat(new_dfs).unique(subset=["timestamp_ms"]).sort("timestamp_ms")
                combined.write_parquet(path)
                return combined.filter(pl.col("timestamp_ms") >= target_start_ms)
            else:
                return existing_df.filter(pl.col("timestamp_ms") >= target_start_ms)

        # Full initial download if no cache exists
        since_str = target_start_dt.strftime("%Y-%m-%d %H:%M:%S")
        df = self.collector.fetch_ohlcv(symbol, timeframe, since_str=since_str)
        if len(df) > 0:
            df.write_parquet(path)
        return df
```
