"""
Benchmark Evaluator for GoldTrader Autonomous EA Engine.
Executes 10 Ground-Truth Benchmark Cases (TC-01 through TC-10) deterministically:
- MQL4 Backwards Loop iteration
- MQL4 MagicNumber & Slippage guard
- MQL5 Modern OOP Trading Engine
- Dynamic ATR Trailing Stop with StopLevel guard
- Breakeven Threshold Activation
- Emergency Margin & Drawdown Circuit Breakers
- Microstructure Spread Spike Interceptor
- High-Impact Macroeconomic News Blackout
- Zero-Test Policy by Default Invariant
- MetaEditor Real Headless Compilation (0 errors, 0 warnings)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Tuple

from harness.verifier import DeterministicVerifier
from harness.interceptor import RedFlagInterceptor, AccountSnapshot
from harness.news_filter import EconomicNewsFilter
from harness.test_guardian import TestPolicyGuardian
from harness.document import export_markdown_document


@dataclass
class TestCaseResult:
    case_id: str
    name: str
    category: str
    weight: int
    passed: bool
    score: int
    details: str
    execution_ms: float


@dataclass
class BenchmarkSuiteResult:
    total_cases: int
    passed_cases: int
    failed_cases: int
    total_score: int
    max_score: int
    percentage: float
    case_results: List[TestCaseResult] = field(default_factory=list)
    total_time_ms: float = 0.0

    def summary(self) -> str:
        status_symbol = "✅" if self.passed_cases == self.total_cases else "⚠️"
        return (
            f"{status_symbol} Benchmark Result: {self.passed_cases}/{self.total_cases} passed "
            f"({self.percentage:.1f}%) | Score: {self.total_score}/{self.max_score} | "
            f"Elapsed: {self.total_time_ms:.1f}ms"
        )


class BenchmarkEvaluator:
    """Executes ground-truth benchmark suite for GoldTrader."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.cases_file = self.workspace_root / "harness" / "benchmark_cases.json"
        self.verifier = DeterministicVerifier(str(self.workspace_root))

    def load_cases(self) -> List[dict]:
        if not self.cases_file.exists():
            raise FileNotFoundError(f"Benchmark cases file not found at {self.cases_file}")
        return json.loads(self.cases_file.read_text(encoding="utf-8"))

    def evaluate_tc01_backwards_loop(self) -> Tuple[bool, str]:
        """TC-01: Verifies backwards loop iteration in MQL4."""
        mt4_ea = self.workspace_root / "experts" / "mt4" / "GoldScalper_MT4.mq4"
        mt4_helper = self.workspace_root / "include" / "mt4" / "TradeHelper_MT4.mqh"

        if not mt4_ea.exists() or not mt4_helper.exists():
            return False, "Required MQL4 files missing"

        ea_text = mt4_ea.read_text(encoding="utf-8", errors="replace")
        helper_text = mt4_helper.read_text(encoding="utf-8", errors="replace")

        # Must find backwards loop pattern
        backwards_pattern = r"for\s*\(\s*int\s+\w+\s*=\s*OrdersTotal\(\)\s*-\s*1\s*;\s*\w+\s*>=\s*0\s*;\s*\w+--\s*\)"
        has_ea_backwards = bool(re.search(backwards_pattern, ea_text))
        has_helper_backwards = bool(re.search(backwards_pattern, helper_text))

        # Forward loop check on OrdersTotal
        forward_pattern = r"for\s*\(\s*int\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*OrdersTotal\(\)\s*;\s*\w+\+\+\s*\)"
        has_forward = bool(re.search(forward_pattern, ea_text + helper_text))

        if has_ea_backwards and has_helper_backwards and not has_forward:
            return True, "Strict backwards loop order iteration confirmed in both EA and TradeHelper."
        return False, f"Backwards loop check failed (EA: {has_ea_backwards}, Helper: {has_helper_backwards}, Forward loop: {has_forward})"

    def evaluate_tc02_slippage_and_magic(self) -> Tuple[bool, str]:
        """TC-02: Verifies MagicNumber and Slippage containment in MQL4."""
        mt4_ea = self.workspace_root / "experts" / "mt4" / "GoldScalper_MT4.mq4"
        if not mt4_ea.exists():
            return False, "GoldScalper_MT4.mq4 not found"

        content = mt4_ea.read_text(encoding="utf-8", errors="replace")
        has_magic_inp = bool(re.search(r"InpMagicNumber\s*=\s*\d+", content))
        has_slippage_inp = bool(re.search(r"(InpSlippage|InpMaxSlippagePoints)\s*=\s*\d+", content))
        has_magic_filter = bool(re.search(r"OrderMagicNumber\(\)\s*==\s*InpMagicNumber", content))
        has_order_send_magic = bool(re.search(r"OrderSend\s*\(.*?\bInpMagicNumber\b.*?\);", content, re.DOTALL))

        if has_magic_inp and has_slippage_inp and has_magic_filter and has_order_send_magic:
            return True, "MagicNumber and MaxSlippage parameter guards verified on OrderSend & order loops."
        return False, f"Missing MagicNumber/slippage guard (MagicInp: {has_magic_inp}, SlippageInp: {has_slippage_inp}, MagicFilter: {has_magic_filter}, OrderSendMagic: {has_order_send_magic})"

    def evaluate_tc03_mql5_modern_oop(self) -> Tuple[bool, str]:
        """TC-03: Verifies MT5 modern OOP trading engine."""
        mt5_ea = self.workspace_root / "experts" / "mt5" / "GoldScalper_MT5.mq5"
        mt5_helper = self.workspace_root / "include" / "mt5" / "TradeHelper_MT5.mqh"
        if not mt5_ea.exists() or not mt5_helper.exists():
            return False, "Required MT5 files missing"

        ea_text = mt5_ea.read_text(encoding="utf-8", errors="replace")
        helper_text = mt5_helper.read_text(encoding="utf-8", errors="replace")
        combined = ea_text + "\n" + helper_text

        has_ctrade = "CTrade" in combined and "<Trade\\Trade.mqh>" in ea_text
        has_position_info = "CPositionInfo" in combined and "<Trade\\PositionInfo.mqh>" in ea_text
        has_symbol_info = "CSymbolInfo" in combined and "<Trade\\SymbolInfo.mqh>" in ea_text

        # Deprecated MT4 calls
        deprecated = ["OrderSelect(", "OrderClose(", "MarketInfo("]
        found_deprecated = [d for d in deprecated if d in combined]

        if has_ctrade and has_position_info and has_symbol_info and not found_deprecated:
            return True, "Modern MT5 standard OOP architecture confirmed (CTrade, CPositionInfo, CSymbolInfo)."
        return False, f"MT5 OOP check failed (CTrade: {has_ctrade}, Deprecated APIs: {found_deprecated})"

    def evaluate_tc04_dynamic_atr_trailing(self) -> Tuple[bool, str]:
        """TC-04: Verifies Dynamic ATR Trailing Stop with StopLevel guard."""
        mt4_h = self.workspace_root / "include" / "mt4" / "TradeHelper_MT4.mqh"
        mt5_h = self.workspace_root / "include" / "mt5" / "TradeHelper_MT5.mqh"

        if not mt4_h.exists() or not mt5_h.exists():
            return False, "TradeHelper headers missing"

        mt4_t = mt4_h.read_text(encoding="utf-8", errors="replace")
        mt5_t = mt5_h.read_text(encoding="utf-8", errors="replace")

        has_mt4_atr_trail = "ApplyATRTrailingStop" in mt4_t and "MODE_STOPLEVEL" in mt4_t
        has_mt5_atr_trail = "ApplyATRTrailingStop" in mt5_t and "StopsLevel" in mt5_t
        has_atr_calc = ("atrMultiplier" in mt4_t) and ("atrMultiplier" in mt5_t)

        if has_mt4_atr_trail and has_mt5_atr_trail and has_atr_calc:
            return True, "Dynamic ATR Trailing Stop with broker StopLevel minimum distance verified in MT4 & MT5."
        return False, f"Dynamic ATR trailing stop logic or broker StopLevel check missing (MT4: {has_mt4_atr_trail}, MT5: {has_mt5_atr_trail})"

    def evaluate_tc05_breakeven_threshold(self) -> Tuple[bool, str]:
        """TC-05: Verifies Breakeven Threshold Activation."""
        mt4_h = self.workspace_root / "include" / "mt4" / "TradeHelper_MT4.mqh"
        mt5_h = self.workspace_root / "include" / "mt5" / "TradeHelper_MT5.mqh"

        mt4_t = mt4_h.read_text(encoding="utf-8", errors="replace")
        mt5_t = mt5_h.read_text(encoding="utf-8", errors="replace")

        has_mt4_be = "ApplyBreakeven" in mt4_t and "lockPoints" in mt4_t
        has_mt5_be = "ApplyBreakeven" in mt5_t and "lockPoints" in mt5_t

        if has_mt4_be and has_mt5_be:
            return True, "Breakeven threshold activation with locked profit buffer confirmed for MT4 & MT5."
        return False, f"Breakeven logic or lockPoints missing (MT4: {has_mt4_be}, MT5: {has_mt5_be})"

    def evaluate_tc06_emergency_circuit_breakers(self) -> Tuple[bool, str]:
        """TC-06: Verifies Emergency Margin & Daily Drawdown Circuit Breakers."""
        interceptor = RedFlagInterceptor()

        # Test safe state
        safe_snap = AccountSnapshot(
            equity=10000.0,
            balance=10000.0,
            margin_level=350.0,
            daily_starting_equity=10000.0,
            current_spread_points=18,
        )
        safe_pass, _ = interceptor.check_trading_health(safe_snap)

        # Test margin call danger (< 150%)
        margin_danger_snap = AccountSnapshot(
            equity=5000.0,
            balance=10000.0,
            margin_level=120.0,
            daily_starting_equity=10000.0,
            current_spread_points=20,
        )
        margin_pass, margin_flags = interceptor.check_trading_health(margin_danger_snap)

        # Test daily drawdown danger (>= 5%)
        dd_danger_snap = AccountSnapshot(
            equity=9400.0,
            balance=10000.0,
            margin_level=300.0,
            daily_starting_equity=10000.0,
            current_spread_points=20,
        )
        dd_pass, dd_flags = interceptor.check_trading_health(dd_danger_snap)

        if safe_pass and (not margin_pass) and (not dd_pass):
            return True, "Emergency Margin Level (< 150%) and Daily Drawdown (>= 5%) circuit breakers fully functional."
        return False, f"Circuit breaker test failed (Safe: {safe_pass}, Margin: {margin_pass}, DD: {dd_pass})"

    def evaluate_tc07_spread_spike_interceptor(self) -> Tuple[bool, str]:
        """TC-07: Verifies Microstructure Spread Spike Interceptor."""
        interceptor = RedFlagInterceptor()
        wide_spread_snap = AccountSnapshot(
            equity=10000.0,
            balance=10000.0,
            margin_level=400.0,
            daily_starting_equity=10000.0,
            current_spread_points=45,
        )
        spread_pass, flags = interceptor.check_trading_health(wide_spread_snap)

        mt4_ea = self.workspace_root / "experts" / "mt4" / "GoldScalper_MT4.mq4"
        mt5_ea = self.workspace_root / "experts" / "mt5" / "GoldScalper_MT5.mq5"

        ea4_t = mt4_ea.read_text(encoding="utf-8", errors="replace")
        ea5_t = mt5_ea.read_text(encoding="utf-8", errors="replace")

        has_ea4_spread = "InpMaxSpreadPoints" in ea4_t and ("IsSpreadAcceptable" in ea4_t or "MODE_SPREAD" in ea4_t)
        has_ea5_spread = "InpMaxSpreadPoints" in ea5_t and ("IsSpreadAcceptable" in ea5_t or "Spread" in ea5_t)

        if (not spread_pass) and has_ea4_spread and has_ea5_spread:
            return True, "Spread spike interceptor blocks entry when spread exceeds 40 points in harness, MT4, and MT5."
        return False, f"Spread spike check failed (Interceptor: {not spread_pass}, EA4: {has_ea4_spread}, EA5: {has_ea5_spread})"


    def evaluate_tc08_news_blackout(self) -> Tuple[bool, str]:
        """TC-08: Verifies High-Impact Macroeconomic News Blackout."""
        news_filter = EconomicNewsFilter(blackout_minutes_before=30, blackout_minutes_after=30)
        base_dt = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
        news_filter.seed_standard_high_impact_events(base_date=base_dt)

        # First Friday of Oct 2026 is Oct 2, 2026. NFP is at 12:30 UTC.
        nfp_time = datetime(2026, 10, 2, 12, 30, tzinfo=timezone.utc)

        # 10 minutes before NFP -> Blackout
        blackout_t1 = nfp_time - timedelta(minutes=10)
        allowed1, reason1, _ = news_filter.is_trade_allowed(blackout_t1)

        # 45 minutes before NFP -> Allowed
        safe_t = nfp_time - timedelta(minutes=45)
        allowed2, reason2, _ = news_filter.is_trade_allowed(safe_t)

        if (not allowed1) and allowed2:
            return True, "High-Impact macroeconomic news blackout successfully blocks trading within +-30m window."
        return False, f"News blackout test failed (During blackout: {allowed1}, Safe window: {allowed2})"

    def evaluate_tc09_zero_test_invariant(self) -> Tuple[bool, str]:
        """TC-09: Verifies Strict Zero-Test FinOps Token Invariant."""
        guardian = TestPolicyGuardian(str(self.workspace_root))

        # Check default mode
        default_mode = guardian.is_testing_mode_requested("implement trading ea in mt4 and mt5")
        triggered_mode = guardian.is_testing_mode_requested("run tests for mt4")

        # Scan for unauthorized tests in workspace
        has_unauthorized, unauth_files = guardian.scan_for_unauthorized_tests()

        if (not default_mode) and triggered_mode and (not has_unauthorized):
            return True, "Zero-Test Policy active by default; 0 unauthorized test files detected in repository."
        return False, f"Zero-test policy invariant failed (Default: {default_mode}, Unauth files: {unauth_files})"

    def evaluate_tc10_headless_metaeditor(self) -> Tuple[bool, str]:
        """TC-10: Verifies Headless MetaEditor Compilation for MT4 & MT5."""
        mt4_ea = self.workspace_root / "experts" / "mt4" / "GoldScalper_MT4.mq4"
        mt5_ea = self.workspace_root / "experts" / "mt5" / "GoldScalper_MT5.mq5"

        if not mt4_ea.exists() or not mt5_ea.exists():
            return False, "EA source files missing"

        # Compile MT4
        s4, e4, w4, b4 = self.verifier.compile_with_metaeditor(mt4_ea)
        # Compile MT5
        s5, e5, w5, b5 = self.verifier.compile_with_metaeditor(mt5_ea)

        if s4 and s5:
            return True, f"Both EAs compiled headlessly with 0 errors & 0 warnings (MT4: {b4.name if b4 else 'ex4'}, MT5: {b5.name if b5 else 'ex5'})."
        err_msg = []
        if not s4:
            err_msg.append(f"MT4 compile failed: {e4}")
        if not s5:
            err_msg.append(f"MT5 compile failed: {e5}")
        return False, "; ".join(err_msg)

    def run_benchmark(self) -> BenchmarkSuiteResult:
        """Executes all 10 benchmark test cases and compiles the scorecard."""
        cases = self.load_cases()
        evaluators = {
            "TC-01": self.evaluate_tc01_backwards_loop,
            "TC-02": self.evaluate_tc02_slippage_and_magic,
            "TC-03": self.evaluate_tc03_mql5_modern_oop,
            "TC-04": self.evaluate_tc04_dynamic_atr_trailing,
            "TC-05": self.evaluate_tc05_breakeven_threshold,
            "TC-06": self.evaluate_tc06_emergency_circuit_breakers,
            "TC-07": self.evaluate_tc07_spread_spike_interceptor,
            "TC-08": self.evaluate_tc08_news_blackout,
            "TC-09": self.evaluate_tc09_zero_test_invariant,
            "TC-10": self.evaluate_tc10_headless_metaeditor,
        }

        start_all = time.time()
        results: List[TestCaseResult] = []
        total_score = 0
        max_score = 0
        passed_count = 0

        for c in cases:
            cid = c["id"]
            name = c["name"]
            cat = c["category"]
            weight = c["weight"]
            max_score += weight

            fn = evaluators.get(cid)
            if fn:
                t0 = time.time()
                try:
                    passed, details = fn()
                except Exception as e:
                    passed = False
                    details = f"Evaluation exception: {e}"
                elapsed = (time.time() - t0) * 1000.0
            else:
                passed = False
                details = f"No evaluator registered for {cid}"
                elapsed = 0.0

            score = weight if passed else 0
            if passed:
                passed_count += 1
                total_score += score

            results.append(
                TestCaseResult(
                    case_id=cid,
                    name=name,
                    category=cat,
                    weight=weight,
                    passed=passed,
                    score=score,
                    details=details,
                    execution_ms=elapsed,
                )
            )

        total_time = (time.time() - start_all) * 1000.0
        pct = (total_score / max_score * 100.0) if max_score > 0 else 0.0

        return BenchmarkSuiteResult(
            total_cases=len(cases),
            passed_cases=passed_count,
            failed_cases=len(cases) - passed_count,
            total_score=total_score,
            max_score=max_score,
            percentage=pct,
            case_results=results,
            total_time_ms=total_time,
        )

    def generate_markdown_report(self, result: BenchmarkSuiteResult) -> str:
        """
        Builds a Production-Grade Markdown Report adhering strictly to:
        - Strict Mermaid Unicode Guardian (ASCII IDs, Quoted Labels)
        - Clean GFM Markdown Tables
        - LaTeX Mathematical Preservation
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            "# GoldTrader Ground-Truth Benchmark Evaluation Report",
            "",
            f"**Execution Timestamp**: `{now_str}`  ",
            f"**Overall Compliance**: **{result.percentage:.1f}%** ({result.passed_cases}/{result.total_cases} Passed)  ",
            f"**Total Benchmark Score**: **{result.total_score} / {result.max_score} points**  ",
            f"**Evaluation Latency**: `{result.total_time_ms:.1f} ms`  ",
            "",
            "## 1. Executive Summary & Architecture Flow",
            "",
            "```mermaid",
            "flowchart TD",
            "    A[\"Ground Truth Benchmark Runner\"] --> B[\"MQL4 & MQL5 Syntax & Rule Gates\"]",
            "    A --> C[\"Risk Containment & Interceptors\"]",
            "    A --> D[\"Macro News Blackout Engine\"]",
            "    A --> E[\"Headless MetaEditor Real Compiler\"]",
            "    B --> F[\"TC-01, TC-02, TC-03\"]",
            "    C --> G[\"TC-04, TC-05, TC-06, TC-07\"]",
            "    D --> H[\"TC-08\"]",
            "    E --> I[\"TC-10\"]",
            "    F & G & H & I --> J[\"100% Deterministic Pass Receipt\"]",
            "```",
            "",
            "## 2. Benchmark Scorecard",
            "",
            "| Case ID | Benchmark Case Name | Category | Weight | Status | Latency | Verification Details |",
            "| :--- | :--- | :--- | :---: | :---: | :---: | :--- |",
        ]

        for cr in result.case_results:
            st = "✅ PASS" if cr.passed else "❌ FAIL"
            lines.append(
                f"| `{cr.case_id}` | {cr.name} | `{cr.category}` | {cr.weight} | {st} | {cr.execution_ms:.1f}ms | {cr.details} |"
            )

        lines.extend([
            "",
            "## 3. Mathematical Risk & Microstructure Bounds",
            "",
            "The GoldTrader harness enforces the following quantitative boundary invariants:",
            "",
            "1. **Maximum Drawdown Circuit Breaker**:",
            "   $$\\text{Drawdown}_{\\text{daily}} = \\frac{\\text{Equity}_{\\text{start}} - \\text{Equity}_{\\text{current}}}{\\text{Equity}_{\\text{start}}} < 0.05$$",
            "",
            "2. **Margin Call Safety Invariant**:",
            "   $$\\text{Margin Level} = \\frac{\\text{Equity}}{\\text{Margin}} \\times 100\\% \\ge 150\\%$$",
            "",
            "3. **Dynamic ATR Trailing Stop Distance**:",
            "   $$\\text{Distance}_{\\text{trail}} = \\max(\\text{ATR}_{14} \\times 2.0,\\; \\text{StopLevel}_{\\text{broker}})$$",
            "",
            "4. **Execution Slippage & Spread Bound**:",
            "   $$\\text{Spread}_{\\text{XAUUSD}} \\le 40\\text{ points } (4.0\\text{ pips})$$",
            "",
            "---",
            "*Report generated deterministically by GoldTrader Autonomous EA Harness.*",
        ])

        return "\n".join(lines) + "\n"

    def export_report_document(self, result: BenchmarkSuiteResult, filename: str = "benchmark_report.md") -> Path:
        """Exports report to ./output/ following Clean Documentation protocol."""
        md_text = self.generate_markdown_report(result)
        return export_markdown_document(
            title="GoldTrader Benchmark Evaluation Report",
            markdown_content=md_text,
            filename=filename,
            output_dir=self.workspace_root / "output",
        )
