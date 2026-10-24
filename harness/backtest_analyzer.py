"""
MT5 Strategy Tester Report Quantitative Analyzer for GoldTrader.
Parses MetaTrader 5 Strategy Tester HTML reports (UTF-16 LE), extracts all settings,
performance metrics, deal logs, and generates quant audits and comparative reports.
"""

from __future__ import annotations
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class MT5BacktestAnalyzer:
    @staticmethod
    def read_html(file_path: Path | str) -> str:
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"Backtest file not found: {file_path}")
        try:
            return p.read_text(encoding="utf-16")
        except Exception:
            return p.read_text(encoding="utf-8", errors="ignore")

    @classmethod
    def parse_report(cls, file_path: Path | str) -> Dict[str, Any]:
        p = Path(file_path)
        content = cls.read_html(p)

        report: Dict[str, Any] = {
            "file_name": p.name,
            "file_path": f"./{p.name}",
            "title": "",
            "broker_build": "",
            "expert": "",
            "symbol": "",
            "period": "",
            "inputs": {},
            "metrics": {},
            "deals_summary": {
                "initial_deposit": 0.0,
                "total_commission": 0.0,
                "total_swap": 0.0,
                "exit_reasons": {},
                "deal_count": 0,
            },
            "audit": {},
        }

        # 1. Header Information
        title_m = re.search(r'<div style="font: 14pt Tahoma"><b>(.*?)</b>', content)
        if title_m:
            report["title"] = title_m.group(1).strip()

        build_m = re.search(r'<div style="font: 10pt Tahoma"><b>(.*?)</b>', content)
        if build_m:
            report["broker_build"] = build_m.group(1).strip()

        # 2. Settings & EA Parameters
        expert_m = re.search(r'>Expert:</td>\s*<td[^>]*><b>(.*?)</b></td>', content, re.IGNORECASE)
        if expert_m:
            report["expert"] = re.sub(r'<[^>]+>', '', expert_m.group(1)).strip()

        symbol_m = re.search(r'>Symbol:</td>\s*<td[^>]*><b>(.*?)</b></td>', content, re.IGNORECASE)
        if symbol_m:
            report["symbol"] = re.sub(r'<[^>]+>', '', symbol_m.group(1)).strip()

        period_m = re.search(r'>Period:</td>\s*<td[^>]*><b>(.*?)</b></td>', content, re.IGNORECASE)
        if period_m:
            report["period"] = re.sub(r'<[^>]+>', '', period_m.group(1)).strip()

        inputs_matches = re.findall(r'<td[^>]*><b>([^<=]+)=([^<]+)</b></td>', content)
        for k, v in inputs_matches:
            report["inputs"][k.strip()] = v.strip()

        # 3. Strategy Tester Metrics
        def extract_metric(pattern: str) -> Optional[str]:
            m = re.search(r'>\s*' + pattern + r'\s*:\s*</td>\s*<td[^>]*>(.*?)</td>', content, re.IGNORECASE)
            if m:
                return re.sub(r'<[^>]+>', '', m.group(1)).strip()
            return None

        metric_patterns = {
            "history_quality": r"History Quality",
            "bars": r"Bars",
            "ticks": r"Ticks",
            "symbols": r"Symbols",
            "total_net_profit": r"Total Net Profit",
            "gross_profit": r"Gross Profit",
            "gross_loss": r"Gross Loss",
            "balance_dd_abs": r"Balance Drawdown Absolute",
            "equity_dd_abs": r"Equity Drawdown Absolute",
            "balance_dd_maximal": r"Balance Drawdown Maximal",
            "equity_dd_maximal": r"Equity Drawdown Maximal",
            "balance_dd_relative": r"Balance Drawdown Relative",
            "equity_dd_relative": r"Equity Drawdown Relative",
            "profit_factor": r"Profit Factor",
            "expected_payoff": r"Expected Payoff",
            "margin_level": r"Margin Level",
            "recovery_factor": r"Recovery Factor",
            "sharpe_ratio": r"Sharpe Ratio",
            "z_score": r"Z-Score",
            "ahpr": r"AHPR",
            "ghpr": r"GHPR",
            "lr_correlation": r"LR Correlation",
            "lr_std_error": r"LR Standard Error",
            "total_trades": r"Total Trades",
            "total_deals": r"Total Deals",
            "short_trades": r"Short Trades \(won %\)",
            "long_trades": r"Long Trades \(won %\)",
            "profit_trades": r"Profit Trades \(% of total\)",
            "loss_trades": r"Loss Trades \(% of total\)",
            "largest_profit_trade": r"Largest profit trade",
            "largest_loss_trade": r"Largest loss trade",
            "average_profit_trade": r"Average profit trade",
            "average_loss_trade": r"Average loss trade",
            "max_consecutive_wins": r"Maximum consecutive wins \(\$\)",
            "max_consecutive_losses": r"Maximum consecutive losses \(\$\)",
            "maximal_consecutive_profit": r"Maximal consecutive profit \(count\)",
            "maximal_consecutive_loss": r"Maximal consecutive loss \(count\)",
            "avg_consecutive_wins": r"Average consecutive wins",
            "avg_consecutive_losses": r"Average consecutive losses",
            "corr_profit_mfe": r"Correlation \(Profits,MFE\)",
            "corr_profit_mae": r"Correlation \(Profits,MAE\)",
            "corr_mfe_mae": r"Correlation \(MFE,MAE\)",
            "min_holding_time": r"Minimal position holding time",
            "max_holding_time": r"Maximal position holding time",
            "avg_holding_time": r"Average position holding time",
        }

        for k, pat in metric_patterns.items():
            val = extract_metric(pat)
            if val is not None:
                report["metrics"][k] = val

        # 4. Deals Parsing (Deposit, Commissions, Swaps, Exit Reasons)
        deals_idx = content.find("<b>Deals</b>")
        if deals_idx != -1:
            deals_chunk = content[deals_idx:]
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', deals_chunk, re.DOTALL)
            exit_reasons: Dict[str, int] = {
                "Take Profit": 0,
                "Stop Loss / Trailing SL": 0,
                "Stop Out": 0,
                "Signal / Manual Exit": 0,
            }
            initial_deposit = 0.0
            total_comm = 0.0
            total_swap = 0.0
            deal_count = 0
            time_series = []
            peak_balance = 0.0
            hourly_pnl = {h: 0.0 for h in range(24)}
            hourly_trades = {h: 0 for h in range(24)}

            for r in rows:
                cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)]
                if len(cells) >= 13:
                    deal_count += 1
                    deal_type = cells[3].lower()
                    direction = cells[4].lower()
                    comm_str = cells[8].replace(" ", "").replace(",", "")
                    swap_str = cells[9].replace(" ", "").replace(",", "")
                    profit_str = cells[10].replace(" ", "").replace(",", "")
                    comment = cells[12].strip().lower()

                    time_str = cells[0]
                    if deal_type == "balance" and initial_deposit == 0.0:
                        try:
                            initial_deposit = float(profit_str)
                            peak_balance = initial_deposit
                            time_series.append({
                                "time": time_str,
                                "balance": initial_deposit,
                                "profit": 0.0,
                                "drawdown": 0.0
                            })
                        except ValueError:
                            pass

                    try:
                        total_comm += float(comm_str)
                    except ValueError:
                        pass

                    try:
                        total_swap += float(swap_str)
                    except ValueError:
                        pass

                    if direction == "out":
                        try:
                            bal = float(cells[11].replace(" ", "").replace(",", ""))
                            prof = float(profit_str)
                            peak_balance = max(peak_balance, bal)
                            dd_pct = ((peak_balance - bal) / peak_balance) * 100 if peak_balance > 0 else 0.0
                            time_series.append({
                                "time": time_str,
                                "balance": bal,
                                "profit": round(bal - initial_deposit, 2),
                                "drawdown": round(dd_pct, 2)
                            })
                            # Hour parsing
                            dt_hour = int(time_str.split()[1].split(":")[0])
                            hourly_pnl[dt_hour] = round(hourly_pnl[dt_hour] + prof, 2)
                            hourly_trades[dt_hour] += 1
                        except Exception:
                            pass

                        if "tp" in comment:
                            exit_reasons["Take Profit"] += 1
                        elif "sl" in comment:
                            exit_reasons["Stop Loss / Trailing SL"] += 1
                        elif "so" in comment or "stop out" in comment:
                            exit_reasons["Stop Out"] += 1
                        else:
                            exit_reasons["Signal / Manual Exit"] += 1

            report["deals_summary"]["initial_deposit"] = initial_deposit
            report["deals_summary"]["total_commission"] = round(total_comm, 2)
            report["deals_summary"]["total_swap"] = round(total_swap, 2)
            report["deals_summary"]["exit_reasons"] = exit_reasons
            report["deals_summary"]["deal_count"] = deal_count
            report["deals_summary"]["time_series"] = time_series
            report["deals_summary"]["hourly_pnl"] = hourly_pnl
            report["deals_summary"]["hourly_trades"] = hourly_trades

        # 5. Quantitative Risk & Edge Audit
        report["audit"] = cls.audit_report(report)

        return report

    @classmethod
    def audit_report(cls, report: Dict[str, Any]) -> Dict[str, Any]:
        metrics = report.get("metrics", {})
        deals = report.get("deals_summary", {})
        audit: Dict[str, Any] = {
            "flags": [],
            "warnings": [],
            "strengths": [],
            "quant_score": 100,
            "status": "PASS",
        }

        def to_float(val: Optional[str]) -> float:
            if not val:
                return 0.0
            # Handle forms like "18.21 (1.74%)" or "226.69"
            m = re.search(r"[-+]?[0-9]*\.?[0-9]+", val.replace(" ", "").replace(",", ""))
            return float(m.group(0)) if m else 0.0

        net_profit = to_float(metrics.get("total_net_profit"))
        profit_factor = to_float(metrics.get("profit_factor"))
        expected_payoff = to_float(metrics.get("expected_payoff"))
        recovery_factor = to_float(metrics.get("recovery_factor"))
        sharpe = to_float(metrics.get("sharpe_ratio"))
        total_trades = int(to_float(metrics.get("total_trades")))
        avg_profit = to_float(metrics.get("average_profit_trade"))
        avg_loss = abs(to_float(metrics.get("average_loss_trade")))
        init_deposit = deals.get("initial_deposit", 0.0)

        # Parse drawdown percent
        eq_dd_str = metrics.get("equity_dd_maximal", "")
        eq_dd_pct = 0.0
        pct_m = re.search(r"\(([0-9.]+)%\)", eq_dd_str)
        if pct_m:
            eq_dd_pct = float(pct_m.group(1))

        # Check 1: Profit Factor
        if profit_factor >= 2.0:
            audit["strengths"].append(f"Exceptional Profit Factor: {profit_factor:.2f} (Target ≥ 1.6)")
        elif profit_factor >= 1.5:
            audit["strengths"].append(f"Solid Profit Factor: {profit_factor:.2f}")
        elif profit_factor < 1.2:
            audit["flags"].append(f"Low Profit Factor: {profit_factor:.2f} (Edge is dangerously thin)")
            audit["quant_score"] -= 20

        # Check 2: Max Drawdown Gate
        if eq_dd_pct <= 5.0:
            audit["strengths"].append(f"Conservative Drawdown: {eq_dd_pct:.2f}% (Circuit breaker limit 5%)")
        elif eq_dd_pct <= 10.0:
            audit["warnings"].append(f"Moderate Drawdown: {eq_dd_pct:.2f}% (Acceptable under 10%)")
            audit["quant_score"] -= 10
        else:
            audit["flags"].append(f"High Drawdown: {eq_dd_pct:.2f}% (Exceeds institutional tolerance)")
            audit["quant_score"] -= 25

        # Check 3: Directional Bias Check (Short vs Long)
        short_str = metrics.get("short_trades", "")
        long_str = metrics.get("long_trades", "")
        short_count = int(to_float(short_str))
        long_count = int(to_float(long_str))
        if total_trades > 20:
            if short_count == 0 or long_count == 0:
                audit["warnings"].append(
                    f"Severe Directional Asymmetry: 100% {'Short' if short_count > 0 else 'Long'} trades "
                    f"({max(short_count, long_count)} vs 0). Strategy only tested in one directional regime."
                )
                audit["quant_score"] -= 15

        # Check 4: Trade Sample Size
        if total_trades < 30:
            audit["warnings"].append(f"Small Sample Size: {total_trades} trades. High statistical variance risk.")
            audit["quant_score"] -= 15
        elif total_trades >= 100:
            audit["strengths"].append(f"Robust Sample Size: {total_trades} trades executed.")

        # Check 5: Sharpe Ratio Anomaly / Curve-fitting Red Flag
        if sharpe > 15.0:
            audit["warnings"].append(
                f"Abnormally high Sharpe Ratio ({sharpe:.2f}). Typical indicator of short-period over-fitting or lack of market regime diversity."
            )
        elif sharpe >= 1.5:
            audit["strengths"].append(f"Attractive Risk-Adjusted Return (Sharpe {sharpe:.2f})")

        # Check 6: Average Win vs Broker Friction / Spread Sensitivity
        if avg_profit < 1.0:
            audit["flags"].append(
                f"Tiny Average Profit (${avg_profit:.2f}/trade). Highly vulnerable to XAUUSD spread expansion and slippage in live trading."
            )
            audit["quant_score"] -= 20

        # Check 7: Stop Out Alert
        so_count = deals.get("exit_reasons", {}).get("Stop Out", 0)
        if so_count > 0:
            audit["flags"].append(f"Margin Call / Stop Out Detected ({so_count} times)! Instant Fail.")
            audit["quant_score"] = 0
            audit["status"] = "FAIL"

        # Determine Final Status
        if audit["status"] != "FAIL":
            if audit["quant_score"] >= 80:
                audit["status"] = "GRADE A (APPROVED)"
            elif audit["quant_score"] >= 65:
                audit["status"] = "GRADE B (ACCEPTABLE WITH REFINEMENTS)"
            elif audit["quant_score"] >= 50:
                audit["status"] = "GRADE C (NEEDS TUNING)"
            else:
                audit["status"] = "GRADE F (REJECTED)"

        return audit

    @classmethod
    def generate_markdown(cls, report: Dict[str, Any]) -> str:
        metrics = report.get("metrics", {})
        inputs = report.get("inputs", {})
        deals = report.get("deals_summary", {})
        audit = report.get("audit", {})

        md = []
        md.append(f"# 📊 MT5 Backtest Quantitative Audit: {report.get('expert', 'EA')}")
        md.append("")
        md.append(f"> **File:** `{report.get('file_name')}` | **Symbol:** `{report.get('symbol', 'XAUUSD')}` | **Timeframe:** `{report.get('period', 'N/A')}`")
        md.append(f"> **Broker / Environment:** `{report.get('broker_build', 'MT5')}`")
        md.append(f"> **Overall Quant Verdict:** **{audit.get('status', 'PENDING')}** (Score: {audit.get('quant_score', 0)}/100)")
        md.append("")
        md.append("---")
        md.append("")

        # 1. Executive Performance Summary
        md.append("## 1. 📈 Executive Performance Summary")
        md.append("")
        md.append("| Metric | Value | Benchmark / Target | Evaluation |")
        md.append("| :--- | :--- | :--- | :--- |")
        md.append(f"| **Initial Deposit** | ${deals.get('initial_deposit', 0.0):,.2f} | Baseline Capital | Grounded |")
        md.append(f"| **Total Net Profit** | **${metrics.get('total_net_profit', '0.00')}** | Positive ROI | {'✅ Profit' if float(metrics.get('total_net_profit', 0)) > 0 else '❌ Loss'} |")
        md.append(f"| **Profit Factor (PF)** | **{metrics.get('profit_factor', 'N/A')}** | $\\ge 1.60$ | {'✅ Healthy' if float(metrics.get('profit_factor', 0)) >= 1.6 else '⚠️ Low'} |")
        md.append(f"| **Expected Payoff** | ${metrics.get('expected_payoff', 'N/A')} | $> 0$ | Statistical Edge |")
        md.append(f"| **Equity Max Drawdown** | **{metrics.get('equity_dd_maximal', 'N/A')}** | $\\le 10.0\\%$ | {'✅ Controlled' if '%)' in metrics.get('equity_dd_maximal', '') and float(re.search(r'([0-9.]+)%', metrics.get('equity_dd_maximal')).group(1)) <= 10 else '⚠️ High'} |")
        md.append(f"| **Recovery Factor** | {metrics.get('recovery_factor', 'N/A')} | $\\ge 3.0$ | Capital Rebound Edge |")
        md.append(f"| **Sharpe Ratio** | {metrics.get('sharpe_ratio', 'N/A')} | $\\ge 1.30$ | Risk-Adjusted Return |")
        md.append(f"| **Total Trades** | {metrics.get('total_trades', '0')} | $\\ge 100$ | Sample Significance |")
        md.append(f"| **Broker Commissions** | ${deals.get('total_commission', 0.0):,.2f} | Transaction Cost | Friction Drag |")
        md.append(f"| **Swap / Financing** | ${deals.get('total_swap', 0.0):,.2f} | Rollover Fee | Overnight Cost |")
        md.append("")

        # 2. Execution & Trade Distribution
        md.append("## 2. 🎯 Execution & Microstructure Distribution")
        md.append("")
        md.append("| Distribution Metric | Long Trades | Short Trades | Overall / Total |")
        md.append("| :--- | :--- | :--- | :--- |")
        md.append(f"| **Trade Count (Win %)** | {metrics.get('long_trades', '0 (0.0%)')} | {metrics.get('short_trades', '0 (0.0%)')} | {metrics.get('total_trades', '0')} |")
        md.append(f"| **Profitable vs Loss** | - | - | {metrics.get('profit_trades', 'N/A')} Win / {metrics.get('loss_trades', 'N/A')} Loss |")
        md.append(f"| **Average Trade Return** | - | - | Win: +${metrics.get('average_profit_trade', '0')} / Loss: -${abs(float(metrics.get('average_loss_trade', 0))):.2f} |")
        md.append(f"| **Consecutive Streaks** | - | - | Max Wins: {metrics.get('max_consecutive_wins', 'N/A')} / Max Losses: {metrics.get('max_consecutive_losses', 'N/A')} |")
        md.append(f"| **Position Holding Time** | Min: {metrics.get('min_holding_time', 'N/A')} | Max: {metrics.get('max_holding_time', 'N/A')} | Avg: {metrics.get('avg_holding_time', 'N/A')} |")
        md.append("")

        # 3. Exit Reasons Breakdown
        md.append("### 🚪 Deal Exit Breakdown")
        md.append("")
        exits = deals.get("exit_reasons", {})
        md.append("| Exit Trigger | Count | Percentage |")
        md.append("| :--- | :--- | :--- |")
        total_exits = sum(exits.values()) or 1
        for k, v in exits.items():
            pct = (v / total_exits) * 100
            md.append(f"| **{k}** | {v} | {pct:.1f}% |")
        md.append("")

        # 4. Quant Risk Gate Audit
        md.append("## 3. 🧪 Quant Risk Gate & Anti-Overfitting Audit")
        md.append("")
        if audit.get("strengths"):
            md.append("#### ✅ Strengths & Edge Confirmations")
            for s in audit["strengths"]:
                md.append(f"- {s}")
            md.append("")

        if audit.get("warnings"):
            md.append("#### ⚠️ Risk Warnings & Regime Sensitivities")
            for w in audit["warnings"]:
                md.append(f"- {w}")
            md.append("")

        if audit.get("flags"):
            md.append("#### ❌ Critical Flags / Breaches")
            for f in audit["flags"]:
                md.append(f"- **{f}**")
            md.append("")

        # 5. Active EA Parameters
        md.append("## 4. ⚙️ Active Strategy Parameters (Settings)")
        md.append("")
        md.append("| Parameter | Value |")
        md.append("| :--- | :--- |")
        for k, v in inputs.items():
            md.append(f"| `{k}` | `{v}` |")
        md.append("")

        # 6. Actionable Quant Recommendations
        md.append("## 5. 💡 Actionable EA Optimization Recommendations")
        md.append("")
        md.append("1. **Session & Spread Guarding**:")
        md.append("   - Ensure `InpMaxSpread` is tuned to gold market rollover hours ($> 40$ points pause).")
        md.append("2. **Directional Balance Audit**:")
        if "100% Short" in str(audit.get("warnings", [])):
            md.append("   - Investigate why Long trades were never triggered: inspect bullish filter thresholds or trend indicators in `experts/`.")
        else:
            md.append("   - Both Long and Short logic are active; continue Walk-Forward Analysis across high-volatility months.")
        md.append("3. **Commission Friction Mitigation**:")
        md.append(f"   - Broker commissions totaled ${deals.get('total_commission', 0):.2f}. Ensure target profit per trade exceeds 3x typical spread costs.")
        md.append("")

        return "\n".join(md)

    @classmethod
    def compare_reports(cls, file_paths: List[Path | str]) -> str:
        reports = [cls.parse_report(fp) for fp in file_paths]
        md = []
        md.append("# 📊 MT5 Backtest Comparative Matrix")
        md.append("")
        md.append(f"> Comparison of {len(reports)} backtest runs for strategy optimization and parameter selection.")
        md.append("")
        md.append("---")
        md.append("")

        # Comparative Table
        md.append("## 1. 📈 Side-by-Side Performance Comparison")
        md.append("")
        headers = ["Metric"] + [f"**{r['file_name']}**" for r in reports]
        md.append("| " + " | ".join(headers) + " |")
        md.append("| " + " | ".join([":---"] + [":---:" for _ in reports]) + " |")

        def add_row(label: str, key: str, is_metric: bool = True):
            row = [f"**{label}**"]
            for r in reports:
                if is_metric:
                    val = r["metrics"].get(key, "N/A")
                else:
                    val = str(r.get(key, "N/A"))
                row.append(str(val))
            md.append("| " + " | ".join(row) + " |")

        add_row("Net Profit ($)", "total_net_profit")
        add_row("Profit Factor", "profit_factor")
        add_row("Expected Payoff ($)", "expected_payoff")
        add_row("Max Equity DD", "equity_dd_maximal")
        add_row("Recovery Factor", "recovery_factor")
        add_row("Sharpe Ratio", "sharpe_ratio")
        add_row("Total Trades", "total_trades")
        add_row("Short Trades (Win %)", "short_trades")
        add_row("Long Trades (Win %)", "long_trades")
        add_row("Avg Profit Trade ($)", "average_profit_trade")
        add_row("Avg Loss Trade ($)", "average_loss_trade")

        # Commission and Score
        row_comm = ["**Total Commission ($)**"] + [f"${r['deals_summary'].get('total_commission', 0.0):.2f}" for r in reports]
        md.append("| " + " | ".join(row_comm) + " |")

        row_score = ["**Quant Score**"] + [f"{r['audit'].get('quant_score', 0)}/100" for r in reports]
        md.append("| " + " | ".join(row_score) + " |")

        row_verdict = ["**Verdict**"] + [r['audit'].get('status', 'PENDING') for r in reports]
        md.append("| " + " | ".join(row_verdict) + " |")
        md.append("")

        # Parameter Differences
        md.append("## 2. ⚙️ Parameter Variations Across Runs")
        md.append("")
        all_param_keys = set()
        for r in reports:
            all_param_keys.update(r["inputs"].keys())

        # Find differing params
        diff_params = []
        for k in sorted(all_param_keys):
            vals = [r["inputs"].get(k, "N/A") for r in reports]
            if len(set(vals)) > 1:
                diff_params.append((k, vals))

        if diff_params:
            p_headers = ["Parameter"] + [f"**{r['file_name']}**" for r in reports]
            md.append("| " + " | ".join(p_headers) + " |")
            md.append("| " + " | ".join([":---"] + [":---:" for _ in reports]) + " |")
            for k, vals in diff_params:
                md.append("| " + f"`{k}`" + " | " + " | ".join([f"`{v}`" for v in vals]) + " |")
            md.append("")
        else:
            md.append("*No parameter differences detected across reports.*")
            md.append("")

        # Quant Recommendation
        best_report = max(reports, key=lambda r: r['audit'].get('quant_score', 0))
        md.append("## 3. 🏆 Lead Quant Recommendation")
        md.append("")
        md.append(f"Based on the multi-dimensional risk-reward evaluation, **`{best_report['file_name']}`** is the top-performing candidate:")
        md.append(f"- **Quant Score:** {best_report['audit'].get('quant_score', 0)}/100 ({best_report['audit'].get('status')})")
        md.append(f"- **Net Profit:** ${best_report['metrics'].get('total_net_profit')}")
        md.append(f"- **Profit Factor:** {best_report['metrics'].get('profit_factor')}")
        md.append(f"- **Max Drawdown:** {best_report['metrics'].get('equity_dd_maximal')}")
        md.append("")

        return "\n".join(md)


    @classmethod
    def generate_html_dashboard(cls, report: Dict[str, Any]) -> str:
        """
        Generates a standalone, dark-themed interactive HTML visual dashboard.
        Features interactive equity curve, underwater drawdown area chart, hourly PnL heatmap,
        and directional/exit distribution powered by Chart.js.
        """
        metrics = report.get("metrics", {})
        inputs = report.get("inputs", {})
        deals = report.get("deals_summary", {})
        audit = report.get("audit", {})

        time_series = deals.get("time_series", [])
        hourly_pnl = deals.get("hourly_pnl", {h: 0 for h in range(24)})
        hourly_trades = deals.get("hourly_trades", {h: 0 for h in range(24)})
        exits = deals.get("exit_reasons", {})

        # Subsample time series if too many points for fast chart rendering
        if len(time_series) > 300:
            step = len(time_series) // 250
            chart_ts = time_series[::step]
            if time_series[-1] != chart_ts[-1]:
                chart_ts.append(time_series[-1])
        else:
            chart_ts = time_series

        chart_labels = [p["time"] for p in chart_ts]
        chart_balance = [p["balance"] for p in chart_ts]
        chart_drawdown = [p["drawdown"] for p in chart_ts]

        # Hourly data
        hours_labels = [f"{h:02d}:00" for h in range(24)]
        hours_pnl_data = [hourly_pnl.get(h, 0.0) for h in range(24)]
        hours_trades_data = [hourly_trades.get(h, 0) for h in range(24)]

        # Exit data
        exit_labels = list(exits.keys())
        exit_counts = list(exits.values())

        # Long vs Short
        short_val = int(re.search(r"\d+", str(metrics.get("short_trades", "0"))).group(0)) if re.search(r"\d+", str(metrics.get("short_trades", "0"))) else 0
        long_val = int(re.search(r"\d+", str(metrics.get("long_trades", "0"))).group(0)) if re.search(r"\d+", str(metrics.get("long_trades", "0"))) else 0

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GoldTrader Visual Dashboard - {report.get('expert', 'EA')}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --gold: #f59e0b;
            --green: #10b981;
            --red: #ef4444;
            --blue: #3b82f6;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-primary);
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .brand {{ display: flex; align-items: center; gap: 12px; }}
        .brand h1 {{ font-size: 24px; font-weight: 700; color: var(--gold); }}
        .badge {{
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.2);
            color: var(--green);
            border: 1px solid var(--green);
        }}
        .badge.warn {{ background: rgba(245, 158, 11, 0.2); color: var(--gold); border-color: var(--gold); }}
        .badge.fail {{ background: rgba(239, 68, 68, 0.2); color: var(--red); border-color: var(--red); }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
        }}
        .kpi-title {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }}
        .kpi-val {{ font-size: 22px; font-weight: 700; }}
        .kpi-val.pos {{ color: var(--green); }}
        .kpi-val.neg {{ color: var(--red); }}
        .kpi-val.gold {{ color: var(--gold); }}

        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 20px;
            margin-bottom: 24px;
        }}
        .col-12 {{ grid-column: span 12; }}
        .col-6 {{ grid-column: span 6; }}
        .col-4 {{ grid-column: span 4; }}
        @media (max-width: 900px) {{
            .col-6, .col-4 {{ grid-column: span 12; }}
        }}

        .chart-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }}
        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .chart-header h3 {{ font-size: 16px; font-weight: 600; }}
        .chart-container {{ position: relative; height: 320px; width: 100%; }}
        .chart-container.small {{ height: 260px; }}

        .table-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            overflow-x: auto;
        }}
        table {{ width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }}
        th, td {{ padding: 10px 14px; border-bottom: 1px solid var(--border-color); }}
        th {{ color: var(--text-secondary); font-weight: 600; }}
        tr:last-child td {{ border-bottom: none; }}
        code {{ background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace; color: var(--gold); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <h1>⚡ GoldTrader Visual Backtest Dashboard</h1>
            </div>
            <div>
                <span class="badge {'warn' if 'B' in str(audit.get('status')) else 'fail' if 'FAIL' in str(audit.get('status')) else ''}">
                    {audit.get('status', 'PENDING')} (Score: {audit.get('quant_score', 0)}/100)
                </span>
            </div>
        </header>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Initial Deposit</div>
                <div class="kpi-val">${deals.get('initial_deposit', 0.0):,.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Total Net Profit</div>
                <div class="kpi-val {'pos' if float(metrics.get('total_net_profit', 0)) > 0 else 'neg'}">
                    ${metrics.get('total_net_profit', '0.00')}
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Profit Factor</div>
                <div class="kpi-val gold">{metrics.get('profit_factor', 'N/A')}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Expected Payoff</div>
                <div class="kpi-val">${metrics.get('expected_payoff', 'N/A')}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Max Drawdown</div>
                <div class="kpi-val {'neg' if '%)' in metrics.get('equity_dd_maximal', '') and float(re.search(r'([0-9.]+)%', metrics.get('equity_dd_maximal')).group(1)) > 5 else 'pos'}">
                    {metrics.get('equity_dd_maximal', 'N/A')}
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Sharpe Ratio</div>
                <div class="kpi-val">{metrics.get('sharpe_ratio', 'N/A')}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Total Trades</div>
                <div class="kpi-val">{metrics.get('total_trades', '0')}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Broker Commission</div>
                <div class="kpi-val neg">${deals.get('total_commission', 0.0):,.2f}</div>
            </div>
        </div>

        <div class="chart-grid">
            <!-- Balance & Profit Curve -->
            <div class="col-12 chart-card">
                <div class="chart-header">
                    <h3>📈 Cumulative Balance Growth Curve</h3>
                    <span style="font-size: 13px; color: var(--text-secondary);">{report.get('expert', '')} on {report.get('symbol', 'XAUUSD')} {report.get('period', '')}</span>
                </div>
                <div class="chart-container">
                    <canvas id="equityChart"></canvas>
                </div>
            </div>

            <!-- Underwater Drawdown Area Chart -->
            <div class="col-12 chart-card">
                <div class="chart-header">
                    <h3>🌊 Underwater Drawdown (%) Area Chart</h3>
                    <span style="font-size: 13px; color: var(--text-secondary);">Circuit Breaker Limit: 5.0%</span>
                </div>
                <div class="chart-container small">
                    <canvas id="drawdownChart"></canvas>
                </div>
            </div>

            <!-- Hourly Distribution -->
            <div class="col-6 chart-card">
                <div class="chart-header">
                    <h3>🕒 Hourly Profitability & Session Volume</h3>
                    <span style="font-size: 12px; color: var(--gold);">London / NY Sessions highlighted</span>
                </div>
                <div class="chart-container">
                    <canvas id="hourlyChart"></canvas>
                </div>
            </div>

            <!-- Exits & Direction Breakdown -->
            <div class="col-3 chart-card">
                <div class="chart-header">
                    <h3>🚪 Deal Exit Triggers</h3>
                </div>
                <div class="chart-container small">
                    <canvas id="exitChart"></canvas>
                </div>
            </div>

            <div class="col-3 chart-card">
                <div class="chart-header">
                    <h3>⚖️ Long vs Short Distribution</h3>
                </div>
                <div class="chart-container small">
                    <canvas id="directionChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Strategy Parameters -->
        <div class="table-card">
            <h3 style="margin-bottom: 14px; color: var(--gold);">⚙️ Active EA Parameters & Settings</h3>
            <table>
                <thead>
                    <tr>
                        <th>Parameter</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f"<tr><td><code>{k}</code></td><td><strong>{v}</strong></td></tr>" for k, v in inputs.items())}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const ctxEquity = document.getElementById('equityChart').getContext('2d');
        new Chart(ctxEquity, {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_labels)},
                datasets: [{{
                    label: 'Account Balance ($)',
                    data: {json.dumps(chart_balance)},
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.08)',
                    fill: true,
                    tension: 0.1,
                    pointRadius: 1,
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#94a3b8', maxTicksLimit: 10 }} }},
                    y: {{ grid: {{ color: '#334155' }}, ticks: {{ color: '#94a3b8' }} }}
                }},
                plugins: {{ legend: {{ labels: {{ color: '#f8fafc' }} }} }}
            }}
        }});

        const ctxDD = document.getElementById('drawdownChart').getContext('2d');
        new Chart(ctxDD, {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_labels)},
                datasets: [{{
                    label: 'Drawdown Depth (%)',
                    data: {json.dumps([-dd for dd in chart_drawdown])},
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.25)',
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                    borderWidth: 1.5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ display: false }} }},
                    y: {{ grid: {{ color: '#334155' }}, ticks: {{ color: '#ef4444' }} }}
                }},
                plugins: {{ legend: {{ labels: {{ color: '#f8fafc' }} }} }}
            }}
        }});

        const ctxHourly = document.getElementById('hourlyChart').getContext('2d');
        new Chart(ctxHourly, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(hours_labels)},
                datasets: [{{
                    label: 'Hourly Net PnL ($)',
                    data: {json.dumps(hours_pnl_data)},
                    backgroundColor: {json.dumps(['#10b981' if p >= 0 else '#ef4444' for p in hours_pnl_data])},
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#94a3b8' }} }},
                    y: {{ grid: {{ color: '#334155' }}, ticks: {{ color: '#94a3b8' }} }}
                }},
                plugins: {{ legend: {{ display: false }} }}
            }}
        }});

        const ctxExit = document.getElementById('exitChart').getContext('2d');
        new Chart(ctxExit, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(exit_labels)},
                datasets: [{{
                    data: {json.dumps(exit_counts)},
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#3b82f6'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', boxWidth: 12 }} }} }}
            }}
        }});

        const ctxDir = document.getElementById('directionChart').getContext('2d');
        new Chart(ctxDir, {{
            type: 'doughnut',
            data: {{
                labels: ['Short Trades', 'Long Trades'],
                datasets: [{{
                    data: [{short_val}, {long_val}],
                    backgroundColor: ['#f59e0b', '#3b82f6'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8', boxWidth: 12 }} }} }}
            }}
        }});
    </script>
</body>
</html>
"""
        return html
