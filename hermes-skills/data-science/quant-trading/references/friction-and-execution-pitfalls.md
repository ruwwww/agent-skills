# Friction & Quantitative Execution Pitfalls

## 1. The High-Frequency Fee Trap

On retail exchange fee tiers (e.g. Binance Futures VIP0: 0.02% maker, 0.04% taker):
- A 5-minute day trading strategy executing 10–12 trades per day generates ~150 round-trip transactions in 14 days.
- Total fee paid = $2 \times 0.04\% = 0.08\%$ per trade.
- With 1.5x–2x notional exposure, fee burden reaches **12% to 20% of account equity** in two weeks.
- Gross profitability often appears positive ($PF > 1.05$), but net return becomes deeply negative ($ROI < -10\%$).

### Remedies:
1. **Timeframe Horizon:** Shift execution from 1m/5m to 15m/1h to increase average trade holding time and average profit per trade.
2. **Maker Post-Only Orders:** Use limit orders that rest in the orderbook to qualify for maker fees (0.02% or 0% rebate) instead of taking liquidity.
3. **Volatility & Regime Filters:** Require higher expansion thresholds (e.g. $2.0 \times \text{ATR}$ rather than $1.2 \times \text{ATR}$) and volume spikes ($> 1.2 \times \text{MA}$) to filter out low-conviction churn in choppy markets.

## 2. Dynamic Position Sizing (Fixed Fractional Risk)

Never size orders by fixed coin quantity or all-in equity. Size positions using the volatility stop distance:

$$\text{Quantity} = \frac{\text{Account Equity} \times \text{Risk Fraction}}{\text{Entry Price} - \text{Stop Loss Price}}$$

Example:
- Account = $10,000
- Risk per trade = 1.5% ($150)
- ATR = $800, SL Distance ($1.5 \times \text{ATR}$) = $1,200
- $\text{Quantity} = \frac{\$150}{\$1,200} = 0.125 \text{ BTC}$
- If stop loss is hit, maximum loss is strictly capped at $150 (1.5%), preventing account blowups during volatility spikes.
