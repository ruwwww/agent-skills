# Forex & Commodities Multi-Asset Execution Guide

A comprehensive technical reference for integrating Foreign Exchange (Forex) and Commodity instruments into quantitative trading pipelines, Parquet lakes, and backtesting brokers.

---

## 1. Instrument Specifications & Registry

Unlike crypto (which operates 24/7 with unit-based sizing and percentage fees), Forex operates on standard lot sizes, pip increments, bid/ask spreads, and 24/5 market hours.

| Instrument | Asset Class | Base / Quote | Pip Size | Contract Size (1 Lot) | Default Spread | Market Hours |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **EUR/USD** | Forex Major | EUR / USD | `0.0001` | 100,000 EUR | 0.8 pips ($0.00008) | 24/5 |
| **GBP/USD** | Forex Major | GBP / USD | `0.0001` | 100,000 GBP | 1.2 pips ($0.00012) | 24/5 |
| **USD/JPY** | Forex Major | USD / JPY | `0.01` | 100,000 USD | 0.9 pips (0.009 JPY) | 24/5 |
| **AUD/USD** | Forex Major | AUD / USD | `0.0001` | 100,000 AUD | 1.0 pips ($0.00010) | 24/5 |
| **USD/CAD** | Forex Major | USD / CAD | `0.0001` | 100,000 USD | 1.4 pips ($0.00014) | 24/5 |
| **USD/CHF** | Forex Major | USD / CHF | `0.0001` | 100,000 USD | 1.5 pips ($0.00015) | 24/5 |
| **XAU/USD** | Commodity | XAU / USD | `0.10` | 100 oz (Gold) | 2.5 pips ($0.25) | 24/5 |

---

## 2. PnL & Currency Conversion Rules

### A. USD Quote Currency (`EUR/USD`, `GBP/USD`, `AUD/USD`, `XAU/USD`)
```python
# Raw difference times lot units
if position.side == PositionSide.LONG:
    pnl_usd = (exit_price - entry_price) * units
else:
    pnl_usd = (entry_price - exit_price) * units
```

### B. Non-USD Quote Currency (`USD/JPY`, `EUR/JPY`, `GBPJPY`)
For pairs where JPY is the quote currency, profit is generated in JPY and must be converted to USD by dividing by the closing exchange rate:
```python
raw_diff = (exit_price - entry_price) if position.side == PositionSide.LONG else (entry_price - exit_price)
pnl_usd = (raw_diff * units) / exit_price
```

---

## 3. High-Throughput Forex Data Collection (Yahoo Finance v8)

### Cookie & Crumb Handshake Pattern
Standard endpoints return `HTTP 429` or `401` when hit without an active session. Use a 2-step handshake:
```python
import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
})

# 1. Establish cookie
session.get("https://fc.yahoo.com")

# 2. Extract crumb
crumb = session.get("https://query2.finance.yahoo.com/v1/test/getcrumb").text.strip()

# 3. Query continuous chart
url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1h&period1={p1}&period2={p2}&crumb={crumb}"
resp = session.get(url)
```

### Dynamic 4h Resampling with Polars
Yahoo Finance does not provide native 4h candles. Resample 1h candles into 4h intervals cleanly in Polars:
```python
resampled = (
    df.sort("timestamp")
    .group_by_dynamic("timestamp", every="4h")
    .agg([
        pl.col("timestamp_ms").first().alias("timestamp_ms"),
        pl.col("open").first().alias("open"),
        pl.col("high").max().alias("high"),
        pl.col("low").min().alias("low"),
        pl.col("close").last().alias("close"),
        pl.col("volume").sum().alias("volume"),
    ])
    .drop_nulls()
    .sort("timestamp_ms")
)
```

---

## 4. Realistic Forex Execution in Paper Brokers

1. **Spread Application:**
   ```python
   spread_price = spec.default_spread_pips * spec.pip_size
   half_spread = spread_price / 2.0
   filled_price = exec_price + half_spread if side == OrderSide.BUY else exec_price - half_spread
   ```
2. **ECN Commission:** Model $2.50 per standard 100k lot (`notional * 0.000025`).
3. **Floor Stop Distance:** Floor at `5 * spec.pip_size` (e.g. 5 pips) to prevent micro-fluctuation whip-saw stops.
