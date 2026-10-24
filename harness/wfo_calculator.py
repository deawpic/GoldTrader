"""
Walk-Forward Optimization (WFO) Matrix Calculator for GoldTrader.
Computes Walk-Forward Efficiency (WFE), Parameter Stability Robustness (PSR),
Drawdown Consistency Ratio (DCR), and evaluates strategy edge persistence across multiple runs.
"""

from __future__ import annotations
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from harness.backtest_analyzer import MT5BacktestAnalyzer
from harness.document import export_markdown_document


class WalkForwardCalculator:
    @classmethod
    def analyze_wfo(
        cls,
        file_paths: List[Path | str],
        oos_ratio: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Executes Walk-Forward Optimization (WFO) and parameter robustness analysis
        on a sequential series of MT5 backtest reports.
        """
        reports = [MT5BacktestAnalyzer.parse_report(fp) for fp in file_paths]
        if not reports:
            raise ValueError("No backtest reports provided for WFO analysis.")

        # Sort reports by period or filename
        reports.sort(key=lambda r: (r.get("period", ""), r.get("file_name", "")))
        n = len(reports)

        # Extract numeric metrics
        def to_f(val: Any) -> float:
            if not val:
                return 0.0
            m = re.search(r"[-+]?[0-9]*\.?[0-9]+", str(val).replace(" ", "").replace(",", ""))
            return float(m.group(0)) if m else 0.0

        pfs = [to_f(r["metrics"].get("profit_factor", 1.0)) for r in reports]
        expectancies = [to_f(r["metrics"].get("expected_payoff", 0.0)) for r in reports]
        profits = [to_f(r["metrics"].get("total_net_profit", 0.0)) for r in reports]
        drawdowns = []
        for r in reports:
            eq_str = r["metrics"].get("equity_dd_maximal", "")
            m_pct = re.search(r"\(([0-9.]+)%\)", eq_str)
            drawdowns.append(float(m_pct.group(1)) if m_pct else 5.0)

        # 1. Parameter Stability Robustness (PSR)
        mean_pf = sum(pfs) / len(pfs) if pfs else 1.0
        var_pf = sum((x - mean_pf) ** 2 for x in pfs) / len(pfs) if len(pfs) > 1 else 0.0
        std_pf = math.sqrt(var_pf)
        cv_pf = (std_pf / mean_pf) if mean_pf > 0 else 1.0
        psr = max(0.0, 1.0 - cv_pf)

        # 2. In-Sample vs Out-of-Sample Split (if n >= 2)
        if n >= 2:
            is_count = max(1, int(round(n * (1.0 - oos_ratio))))
            if is_count >= n:
                is_count = n - 1
            is_reports = reports[:is_count]
            oos_reports = reports[is_count:]

            is_exp = sum(expectancies[:is_count]) / is_count
            oos_exp = sum(expectancies[is_count:]) / len(oos_reports)
            is_profit_ann = sum(profits[:is_count]) / is_count
            oos_profit_ann = sum(profits[is_count:]) / len(oos_reports)

            # WFE by expectancy persistence
            if is_exp > 0:
                wfe = (oos_exp / is_exp) * 100.0
            else:
                wfe = 100.0 if oos_exp > 0 else 0.0
        else:
            is_reports = reports
            oos_reports = []
            is_exp = expectancies[0] if expectancies else 0.0
            oos_exp = is_exp
            wfe = 100.0

        # 3. Drawdown Consistency Ratio (DCR)
        max_dd = max(drawdowns) if drawdowns else 5.0
        min_dd = min(drawdowns) if drawdowns else 5.0
        dcr = (min_dd / max_dd) * 100.0 if max_dd > 0 else 100.0

        # 4. Composite WFO Score (0 - 100)
        norm_wfe = min(100.0, max(0.0, wfe))
        norm_psr = min(100.0, max(0.0, psr * 100.0))
        norm_dcr = min(100.0, max(0.0, dcr))
        composite_score = round(0.40 * norm_wfe + 0.35 * norm_psr + 0.25 * norm_dcr, 1)

        # Grading
        if composite_score >= 75.0 and wfe >= 60.0:
            verdict = "GRADE A (ROBUST INSTITUTIONAL EDGE)"
            verdict_desc = "Strategy exhibits high parameter stability and strong Out-of-Sample persistence. Low overfitting risk."
        elif composite_score >= 60.0 and wfe >= 50.0:
            verdict = "GRADE B (MODERATE PERSISTENCE - ACCEPTABLE)"
            verdict_desc = "Acceptable performance consistency; recommend live spread and slippage stress-testing."
        else:
            verdict = "GRADE F (HIGH OVERFITTING RISK - REJECT)"
            verdict_desc = "Significant performance drop or parameter cliff between windows. High probability of curve-fitting."

        return {
            "total_windows": n,
            "reports": reports,
            "wfe": round(wfe, 2),
            "psr": round(psr, 3),
            "dcr": round(dcr, 2),
            "mean_profit_factor": round(mean_pf, 2),
            "std_profit_factor": round(std_pf, 2),
            "max_drawdown": max_dd,
            "composite_score": composite_score,
            "verdict": verdict,
            "verdict_desc": verdict_desc,
        }

    @classmethod
    def generate_wfo_markdown_report(cls, wfo_data: Dict[str, Any]) -> str:
        reports = wfo_data["reports"]
        md = []

        md.append("# 📐 Walk-Forward Optimization (WFO) Matrix & Robustness Report")
        md.append("")
        md.append(f"> **Evaluation Scope:** {wfo_data['total_windows']} Sequential Test Windows | **Composite WFO Score:** **{wfo_data['composite_score']}/100**")
        md.append(f"> **Final Robustness Verdict:** **{wfo_data['verdict']}**")
        md.append("")
        md.append("---")
        md.append("")

        # 1. Executive Walk-Forward Scorecard
        md.append("## 1. 📈 Walk-Forward Efficiency (WFE) Scorecard")
        md.append("")
        md.append("| Metric | Calculated Value | Benchmark / Target | Quant Evaluation |")
        md.append("| :--- | :---: | :---: | :--- |")
        md.append(f"| **Walk-Forward Efficiency (WFE)** | **{wfo_data['wfe']:.1f}%** | $\\ge 60.0\\%$ | {'✅ Robust Persistence' if wfo_data['wfe'] >= 60 else '⚠️ Potential Curve-fit'} |")
        md.append(f"| **Parameter Stability (PSR)** | **{wfo_data['psr']:.3f}** | $\\ge 0.700$ | {'✅ Smooth Parameter Space' if wfo_data['psr'] >= 0.7 else '⚠️ Parameter Cliff Alert'} |")
        md.append(f"| **Drawdown Consistency (DCR)** | **{wfo_data['dcr']:.1f}%** | $\\ge 50.0\\%$ | Capital Preservation Stability |")
        md.append(f"| **Mean Profit Factor (PF)** | {wfo_data['mean_profit_factor']:.2f} $\\pm$ {wfo_data['std_profit_factor']:.2f} | $\\ge 1.60$ | Average Strategy Edge |")
        md.append(f"| **Worst-Case Equity Drawdown** | {wfo_data['max_drawdown']:.2f}% | $\\le 5.0\\%$ | Maximum Historical Pain |")
        md.append("")
        md.append(f"**Verdict Rationale:** {wfo_data['verdict_desc']}")
        md.append("")

        # 2. Window-by-Window Performance Matrix
        md.append("## 2. 🗂️ Sequential Window Performance Matrix")
        md.append("")
        headers = ["Metric"] + [f"**{r['file_name']}**" for r in reports]
        md.append("| " + " | ".join(headers) + " |")
        md.append("| " + " | ".join([":---"] + [":---:" for _ in reports]) + " |")

        def add_row(label: str, key: str):
            row = [f"**{label}**"]
            for r in reports:
                row.append(str(r["metrics"].get(key, "N/A")))
            md.append("| " + " | ".join(row) + " |")

        add_row("Net Profit ($)", "total_net_profit")
        add_row("Profit Factor", "profit_factor")
        add_row("Expected Payoff ($)", "expected_payoff")
        add_row("Max Drawdown", "equity_dd_maximal")
        add_row("Sharpe Ratio", "sharpe_ratio")
        add_row("Total Trades", "total_trades")
        add_row("Short Trades (Win %)", "short_trades")
        add_row("Long Trades (Win %)", "long_trades")
        md.append("")

        # 3. Mathematical Foundations
        md.append("## 3. 📐 Mathematical Formulations")
        md.append("")
        md.append("The Walk-Forward Optimization engine evaluates robustness using the following quantitative definitions:")
        md.append("")
        md.append("1. **Walk-Forward Efficiency (WFE)**:")
        md.append("   $$WFE = \\frac{\\overline{\\text{Expectancy}}_{\\text{OOS}}}{\\overline{\\text{Expectancy}}_{\\text{IS}}} \\times 100\\%$$")
        md.append("")
        md.append("2. **Parameter Stability Robustness (PSR)**:")
        md.append("   $$PSR = \\max\\left(0,\\; 1.0 - \\frac{\\sigma(PF)}{\\mu(PF)}\\right)$$")
        md.append("")
        md.append("3. **Drawdown Consistency Ratio (DCR)**:")
        md.append("   $$DCR = \\frac{\\min(\\text{Drawdown})}{\\max(\\text{Drawdown})} \\times 100\\%$$")
        md.append("")

        return "\n".join(md)
