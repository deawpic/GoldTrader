# Quantitative Risk & Backtest Playbook

This playbook contains reference implementations and formulas adapted for the GoldTrader algorithmic harness.

---

## 1. Core Risk Metric Calculations (Python)

```python
import numpy as np
import pandas as pd
from scipy import stats

class GoldQuantMetrics:
    @staticmethod
    def cornish_fisher_var(returns: pd.Series, confidence: float = 0.95) -> float:
        """Calculate Value at Risk using Cornish-Fisher expansion for non-normal gold returns."""
        z = stats.norm.ppf(confidence)
        s = stats.skew(returns)
        k = stats.kurtosis(returns)  # Fisher kurtosis (normal = 0)
        
        z_cf = (
            z 
            + (z**2 - 1) * s / 6 
            + (z**3 - 3 * z) * k / 24 
            - (2 * z**3 - 5 * z) * (s**2) / 36
        )
        return float(returns.mean() - z_cf * returns.std())

    @staticmethod
    def expected_shortfall_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)."""
        cutoff = np.percentile(returns, (1 - confidence) * 100)
        tail_losses = returns[returns <= cutoff]
        return float(-tail_losses.mean()) if len(tail_losses) > 0 else 0.0

    @staticmethod
    def ulcer_index(equity_curve: pd.Series) -> float:
        """Calculate Ulcer Index measuring depth and duration of drawdowns."""
        peak = equity_curve.cummax()
        drawdown_pct = ((equity_curve - peak) / peak) * 100
        return float(np.sqrt(np.mean(drawdown_pct**2)))
```

---

## 2. Monte Carlo Trade Sequence Permutation

To evaluate whether an EA's drawdown is sensitive to trade sequencing:
1. Extract array of trade P&Ls ($N$ trades).
2. Reshuffle trade order $10,000$ times with replacement.
3. Compute Max Drawdown distribution for all 10,000 simulations.
4. Assess 95th and 99th percentile Worst-Case Drawdowns ($DD_{95}, DD_{99}$).
5. If $DD_{95} > 2 \times Realized\,MaxDD$, the strategy has hidden sequencing vulnerability.
