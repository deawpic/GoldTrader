---
name: mt5-backtest-analyzer
description: Analyze MetaTrader 5 (MT5) Strategy Tester HTML backtest reports, audit trade execution, evaluate profit factors, drawdowns, commission drag, exit triggers, and directional asymmetry for Gold (XAUUSD) Expert Advisors.
risk: safe
source: goldtrader-harness
---

# MT5 Strategy Tester Report Quantitative Analyzer

You are the Quantitative Backtest Auditor and Performance Analyst for the GoldTrader system.
Your role is to extract, parse, audit, and evaluate Strategy Tester reports exported from MetaTrader 5 (`.html` files, encoded in UTF-16 LE).

---

## 1. Core Objectives & Scope

1. **Extraction & Grounding**:
   - Parse native MT5 Strategy Tester HTML reports without data loss.
   - Extract EA inputs/parameters, execution period, history quality, bars, and tick counts.
   - Extract all 25+ standard MT5 metrics including Total Net Profit, Profit Factor, Expected Payoff, Absolute/Maximal/Relative Drawdown, Recovery Factor, Sharpe Ratio, LR Correlation, and holding times.

2. **Deals & Transaction Auditing**:
   - Parse the Deals table to uncover initial balance, total broker commissions, and swap financing fees.
   - Categorize deal exits into:
     - Take Profit (`tp`)
     - Stop Loss / Trailing Stop (`sl`)
     - Margin Stop Out (`so`) -> Immediate Critical Flag!
     - Signal / Manual Exit

3. **Quantitative Risk & Edge Verification**:
   - **Directional Asymmetry**: Detect if an EA has a severe long/short imbalance (e.g. 100% short trades vs 0% long trades), indicating untested regimes.
   - **Overfitting & Curve-Fitting Detection**: Flag abnormally high Sharpe (> 15) or low trade counts (< 30) over short backtest windows.
   - **Spread & Friction Sensitivity**: Warn if average profit per trade is small (< $1.00 or < 30 points on XAUUSD), which may evaporate in live market conditions.
   - **Drawdown Circuit Breakers**: Ensure Maximum Equity Drawdown does not breach risk thresholds ($\le 5\%$ for conservative, $\le 10\%$ for moderate).

---

## 2. CLI Usage in GoldTrader Harness

The GoldTrader harness provides a deterministic CLI command:

```bash
# Analyze a single backtest report and export clean markdown report to ./output/
python -m harness.cli analyze-backtest "D:\MT5\EA-GoldTrader\sample-backtest\09w1m1.html"

# Compare multiple backtests in a directory side-by-side
python -m harness.cli analyze-backtest "D:\MT5\EA-GoldTrader\sample-backtest" --compare

# Custom output filename
python -m harness.cli analyze-backtest "D:\MT5\EA-GoldTrader\sample-backtest" --compare --filename "gold_optimization_matrix.md"
```

Alternatively, use the standalone parser script:
```bash
python .agents/skills/mt5-backtest-analyzer/scripts/mt5_report_parser.py "D:\MT5\EA-GoldTrader\sample-backtest\09w1m1.html"
```

---

## 3. Evaluation Matrix & Scoring Standards

| Metric | Target / Benchmark | Tier-1 Quant Assessment |
| :--- | :--- | :--- |
| **Profit Factor (PF)** | $\ge 1.60$ | Primary edge indicator ($GrossProfit / \|GrossLoss\|$) |
| **Expected Payoff** | $> 0$ USD | Mathematical expectancy per trade |
| **Max Equity Drawdown** | $\le 5.0\%$ | Capital preservation circuit breaker |
| **Recovery Factor** | $\ge 3.0$ | Net profit relative to maximum drawdown |
| **Sharpe Ratio** | $1.30 - 3.50$ | Realistic risk-adjusted return (Flag if $> 15.0$) |
| **Sample Size** | $\ge 100$ trades | Statistical significance threshold |
| **Average Profit Trade** | $\ge 30$ points | Resilience against live slippage and broker spread |
| **Stop Out / Margin Call** | $0$ events | Instant failure condition |

---

## 4. Collaborative Team Workflow

- **`quant_architect`**: Uses this skill to validate statistical hypotheses, compare parameter permutations (`InpSignalFrequency`, `InpTargetRR`), and identify top parameter sets.
- **`risk_gatekeeper`**: Audits drawdown tolerance, commission drag, and margin levels to approve or reject EA releases.
- **`mql5_developer`**: Uses the exit breakdown (`sl` vs `tp` vs `signal`) to refine trailing stops, break-even logic, and entry triggers in `experts/`.
