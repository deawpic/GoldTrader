"""
CLI Interface for GoldTrader Deterministic Multi-Agent Trading Harness.
Provides commands to initialize tasks, inspect the stack, assemble JIT prompts,
step state transitions, verify MQL code, audit Mermaid diagrams, and export clean reports.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from harness.schemas import TaskFrame, TaskStatus, SystemState, TaskBudget, StrictLevel, TradingRole
from harness.task_stack import TaskStackManager
from harness.state_machine import DeterministicStateMachine
from harness.prompt_builder import PromptOnDemandBuilder
from harness.verifier import DeterministicVerifier
from harness.mermaid_guardian import MermaidUnicodeGuardian
from harness.document import export_markdown_document, audit_document_formatting, get_pdf_export_guidance
from harness.evaluator import BenchmarkEvaluator
from harness.news_filter import EconomicNewsFilter
from harness.backtest_analyzer import MT5BacktestAnalyzer
from harness.wfo_calculator import WalkForwardCalculator


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="GoldTrader Deterministic State Machine & MQL4/MQL5 EA Development Harness",
    )
    parser.add_argument(
        "--stack-file",
        default="stack.json",
        help="Path to stack.json file (default: stack.json)",
    )
    parser.add_argument(
        "--strict-level",
        choices=["lenient", "strict", "hardcore"],
        default="strict",
        help="Enforcement level for Strict Mode (default: strict)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. init
    init_parser = subparsers.add_parser("init", help="Initialize a new root task onto the stack")
    init_parser.add_argument("--task-id", default="GOLD-001", help="ID of root task")
    init_parser.add_argument("--title", required=True, help="Title of root trading task")
    init_parser.add_argument("--desc", default="", help="Description or quantitative criteria")
    init_parser.add_argument(
        "--agent",
        default="strategy_pm",
        choices=["strategy_pm", "quant_architect", "mql4_developer", "mql5_developer", "risk_gatekeeper"],
        help="Initial agent (default: strategy_pm)",
    )
    init_parser.add_argument(
        "--allowed-files",
        nargs="*",
        default=[],
        help="List of allowed files for strict boundary checking",
    )
    init_parser.add_argument(
        "--max-lines",
        type=int,
        default=300,
        help="Max lines changed for atomic blast radius (default: 300)",
    )

    # 2. status
    subparsers.add_parser("status", help="Print current status and Top of Stack")

    # 3. build-prompt
    prompt_parser = subparsers.add_parser("build-prompt", help="Build JIT prompt on demand for Top of Stack")
    prompt_parser.add_argument("--agent", default=None, help="Override target agent")
    prompt_parser.add_argument("--output", default=None, help="Save generated prompt to file")

    # 4. transition
    trans_parser = subparsers.add_parser("transition", help="Apply agent structured output to advance state")
    trans_parser.add_argument(
        "--input",
        required=True,
        help="Raw output text or JSON string from agent, or path to file containing output",
    )

    # 5. verify
    subparsers.add_parser("verify", help="Run deterministic ground-truth verification on current top artifacts")

    # 6. inspect-stack
    subparsers.add_parser("inspect-stack", help="Display visual stack and history in JSON")

    # 7. check-mql (MQL4 / MQL5 static linter)
    mql_parser = subparsers.add_parser("check-mql", help="Run static linter on MQL4 / MQL5 code files")
    mql_parser.add_argument("files", nargs="+", help="Path(s) to .mq4, .mq5, or .mqh files")

    # 8. check-mermaid (Mermaid Unicode Guardian)
    mermaid_parser = subparsers.add_parser("check-mermaid", help="Audit and sanitize Mermaid diagrams in Markdown")
    mermaid_parser.add_argument("file", help="Path to Markdown (.md) file to audit")
    mermaid_parser.add_argument("--fix", action="store_true", help="Auto-heal in-place")

    # 9. export-report
    export_parser = subparsers.add_parser("export-report", help="Export clean UTF-8 markdown document to ./output/")
    export_parser.add_argument("--title", required=True, help="Document Title")
    export_parser.add_argument("--input-file", required=True, help="Input Markdown file")
    export_parser.add_argument("--filename", required=True, help="Target filename in ./output/")

    # 10. compile-mql (Headless MetaEditor compiler)
    compile_parser = subparsers.add_parser("compile-mql", help="Compile MQL4/MQL5 Expert Advisors headlessly via MetaEditor")
    compile_parser.add_argument("files", nargs="+", help="Path(s) to .mq4 or .mq5 files to compile")
    compile_parser.add_argument(
        "--platform",
        choices=["auto", "mt4", "mt5"],
        default="auto",
        help="Force target platform (default: auto)",
    )

    # 11. eval-benchmark (Ground-truth 10-case evaluation)
    bench_parser = subparsers.add_parser("eval-benchmark", help="Execute 10-case Ground Truth benchmark test suite")
    bench_parser.add_argument(
        "--export",
        action="store_true",
        default=True,
        help="Export clean report to ./output/ (default: True)",
    )
    bench_parser.add_argument(
        "--filename",
        default="benchmark_report.md",
        help="Output report filename in ./output/ (default: benchmark_report.md)",
    )

    # 12. check-news (Economic News Blackout Gate)
    news_parser = subparsers.add_parser("check-news", help="Inspect high-impact economic news filter & blackout gate")
    news_parser.add_argument("--symbol", default="XAUUSD", help="Trading symbol (default: XAUUSD)")

    # 13. analyze-backtest (MT5 Strategy Tester Report Analyzer)
    backtest_parser = subparsers.add_parser("analyze-backtest", help="Analyze MT5 Strategy Tester backtest reports")
    backtest_parser.add_argument("path", help="Path to MT5 HTML backtest report or folder of reports")
    backtest_parser.add_argument("--compare", action="store_true", help="Compare multiple reports side-by-side")
    backtest_parser.add_argument("--export", action="store_true", default=True, help="Export clean markdown report to ./output/")
    backtest_parser.add_argument("--filename", default=None, help="Target markdown filename in ./output/")
    backtest_parser.add_argument("--html", action="store_true", help="Generate interactive visual HTML dashboard with equity curves")

    # 14. analyze-wfo (Walk-Forward Optimization Matrix Calculator)
    wfo_parser = subparsers.add_parser("analyze-wfo", help="Calculate Walk-Forward Optimization (WFO) matrix & WFE score")
    wfo_parser.add_argument("path", help="Path to folder containing sequential MT5 backtest HTML reports")
    wfo_parser.add_argument("--split-ratio", type=float, default=0.3, help="Out-of-Sample ratio (default: 0.3)")
    wfo_parser.add_argument("--export", action="store_true", default=True, help="Export clean markdown report to ./output/")
    wfo_parser.add_argument("--filename", default="wfo_matrix_report.md", help="Target markdown filename in ./output/")

    args = parser.parse_args()

    strict_lvl = StrictLevel(args.strict_level)
    stack_mgr = TaskStackManager(file_path=args.stack_file, strict_level=strict_lvl)
    fsm = DeterministicStateMachine(stack_mgr)

    if args.command == "init":
        root_task = TaskFrame(
            task_id=args.task_id,
            title=args.title,
            description=args.desc,
            assigned_agent=args.agent,
            status=TaskStatus.PENDING,
            allowed_files=list(args.allowed_files),
            max_lines_changed=args.max_lines,
        )
        stack_mgr.set_strict_level(strict_lvl)
        stack_mgr.push(root_task)
        initial_state = fsm.state_for_agent(args.agent)
        stack_mgr.set_system_state(initial_state)
        print(f"✅ Initialized GoldTrader task stack with root task '{args.task_id}'.")
        print(f"Current State:  {initial_state.value}")
        print(f"Strict Level:   {strict_lvl.value.upper()}")
        print(f"Top Agent:      {args.agent}")
        if args.allowed_files:
            print(f"Allowed Files:  {', '.join(args.allowed_files)}")

    elif args.command == "status":
        print("=" * 60)
        print(f"⚡ SYSTEM STATE: {stack_mgr.current_state.value}")
        print(f"🛡️ STRICT LEVEL: {stack_mgr.strict_level.value.upper()}")
        print(f"📁 STACK DEPTH:  {len(stack_mgr.stack)}")
        print(f"🔑 SESSION ID:   {stack_mgr.session_id}")
        print("=" * 60)

        top = stack_mgr.peek()
        if top:
            print("🎯 TOP OF STACK (Active Task):")
            print(f"  - Task ID:        {top.task_id}")
            print(f"  - Title:          {top.title}")
            print(f"  - Assigned Agent: {top.assigned_agent}")
            print(f"  - Status:         {top.status.value}")
            print(f"  - Allowed Files:  {', '.join(top.allowed_files) if top.allowed_files else '(unrestricted)'}")
            print(f"  - Max Blast (L):  {top.max_lines_changed}")
            print(f"  - Artifacts:      {', '.join(top.artifacts) if top.artifacts else '(none)'}")
            print(f"  - Retries:        {top.budget.current_retries} / {top.budget.max_retries}")
            print(f"  - Tokens Used:    {top.budget.used_tokens} / {top.budget.max_tokens}")
        else:
            print("Stack is empty (IDLE / COMPLETED).")

        if stack_mgr.history:
            last_hist = stack_mgr.history[-1]
            receipt = last_hist.get("verification_receipt")
            if receipt:
                print("\n🧾 LATEST VERIFICATION RECEIPT:")
                print(f"  - Gate Type:      {receipt.get('gate_type')}")
                print(f"  - Status:         {receipt.get('status')} (Exit Code: {receipt.get('exit_code')})")
                print(f"  - Verified Files: {', '.join(receipt.get('verified_files', []))}")

    elif args.command == "build-prompt":
        top = stack_mgr.peek()
        if not top:
            print("❌ Cannot build prompt: Task stack is empty.", file=sys.stderr)
            sys.exit(1)

        builder = PromptOnDemandBuilder()
        prompt = builder.build_prompt(top, target_agent=args.agent, strict_level=stack_mgr.strict_level)

        if args.output:
            out_path = Path(args.output)
            out_path.write_text(prompt, encoding="utf-8")
            print(f"✅ Prompt saved to {out_path} ({len(prompt)} chars).")
        else:
            print(prompt)

    elif args.command == "transition":
        input_data = args.input
        input_path = Path(input_data)
        if input_path.exists() and input_path.is_file():
            input_data = input_path.read_text(encoding="utf-8")

        res = fsm.step_with_raw_output(input_data)
        print("=" * 60)
        print(f"Transition Result: {'✅ SUCCESS' if res.success else '❌ REJECTED / BLOCKED'}")
        print(f"State Change:      {res.previous_state.value} -> {res.new_state.value}")
        print(f"Next Agent:        {res.next_agent or '(none)'}")
        print(f"Message:           {res.message}")
        if res.rejection_feedback:
            print(f"Feedback/Reason:   {res.rejection_feedback}")
        if res.verification_receipt:
            print(f"Receipt Generated: {res.verification_receipt.status} (Gate: {res.verification_receipt.gate_type})")
        print("=" * 60)
        if not res.success:
            sys.exit(1)

    elif args.command == "verify":
        top = stack_mgr.peek()
        if not top:
            print("❌ Stack is empty.", file=sys.stderr)
            sys.exit(1)

        verifier = DeterministicVerifier()
        v_res = verifier.verify_artifacts(top.artifacts)
        print(v_res.summary())
        if not v_res.passed:
            for err in v_res.errors:
                print(f"  - ❌ {err}")
            sys.exit(1)

    elif args.command == "inspect-stack":
        print(json.dumps(stack_mgr.to_dict(), indent=2, ensure_ascii=False))

    elif args.command == "check-mql":
        verifier = DeterministicVerifier()
        all_passed = True
        for f_path in args.files:
            p = Path(f_path)
            if not p.exists():
                print(f"❌ File not found: {f_path}")
                all_passed = False
                continue
            valid, errs, warns = verifier.verify_mql_file(p)
            print(f"\nAudit: {p.name}")
            if valid:
                print("  ✅ Static Syntax & Rules Passed")
            else:
                all_passed = False
                for err in errs:
                    print(f"  ❌ Error: {err}")
            for w in warns:
                print(f"  ⚠️ Warning: {w}")

        if not all_passed:
            sys.exit(1)

    elif args.command == "check-mermaid":
        p = Path(args.file)
        if not p.exists():
            print(f"❌ File not found: {args.file}")
            sys.exit(1)
        text = p.read_text(encoding="utf-8")
        audit_res = MermaidUnicodeGuardian.audit_markdown_text(text)
        print(f"Audit: {p.name}")
        print(f"  - Mermaid Blocks: {audit_res['block_count']}")
        print(f"  - Status:         {'✅ PASSED' if audit_res['passed'] else '❌ ISSUES DETECTED'}")
        if not audit_res["passed"]:
            for r in audit_res["reports"]:
                for err in r["validation"]["errors"]:
                    print(f"    ❌ Line {err['line_number']}: {err['message']}")
            if args.fix:
                p.write_text(audit_res["sanitized_markdown"], encoding="utf-8")
                print("  🔧 Auto-healed Mermaid diagrams in-place.")
            else:
                print("  💡 Run with --fix to automatically heal diagrams.")
                sys.exit(1)

    elif args.command == "export-report":
        p = Path(args.input_file)
        if not p.exists():
            print(f"❌ File not found: {args.input_file}")
            sys.exit(1)
        content = p.read_text(encoding="utf-8")
        exported = export_markdown_document(
            title=args.title,
            markdown_content=content,
            filename=args.filename,
        )
        print(f"✅ Clean document exported to: ./output/{exported.name}")
        print("\n" + get_pdf_export_guidance())

    elif args.command == "compile-mql":
        verifier = DeterministicVerifier()
        all_passed = True
        for f_path in args.files:
            p = Path(f_path)
            if not p.exists():
                print(f"❌ Source file not found: {f_path}")
                all_passed = False
                continue
            plat = None if args.platform == "auto" else args.platform
            target_plat = plat or ("mt4" if p.suffix.lower() == ".mq4" else "mt5")
            editor_bin = verifier.find_metaeditor(target_plat)
            print(f"\n🔨 Compiling: {p.name}")
            print(f"  - Platform: {target_plat.upper()}")
            print(f"  - Compiler: {editor_bin or '(not found)'}")
            success, errs, warns, out_bin = verifier.compile_with_metaeditor(p, metaeditor_path=editor_bin)
            if success:
                print(f"  ✅ Compilation Succeeded (0 errors, {len(warns)} warnings)")
                if out_bin:
                    print(f"  📦 Generated Binary: {out_bin}")
            else:
                all_passed = False
                print(f"  ❌ Compilation Failed ({len(errs)} error(s)):")
                for err in errs:
                    print(f"    - {err}")
            for w in warns:
                print(f"    ⚠️ Warning: {w}")

        if not all_passed:
            sys.exit(1)

    elif args.command == "eval-benchmark":
        evaluator = BenchmarkEvaluator()
        print("⚡ Running GoldTrader 10-Case Ground-Truth Benchmark Suite...\n")
        res = evaluator.run_benchmark()
        print("=" * 60)
        print(res.summary())
        print("=" * 60)
        for cr in res.case_results:
            icon = "✅" if cr.passed else "❌"
            print(f"  {icon} [{cr.case_id}] {cr.name:<45} ({cr.score}/{cr.weight} pts, {cr.execution_ms:.1f}ms)")
            print(f"     Details: {cr.details}")
        print("=" * 60)
        if args.export:
            out_doc = evaluator.export_report_document(res, filename=args.filename)
            print(f"\n📄 Clean Benchmark Report exported to: ./output/{out_doc.name}")
            print("\n" + get_pdf_export_guidance())
        if res.failed_cases > 0:
            sys.exit(1)

    elif args.command == "check-news":
        news_filter = EconomicNewsFilter()
        news_filter.seed_standard_high_impact_events()
        allowed, reason, ev = news_filter.is_trade_allowed(symbol=args.symbol)
        print(f"⚡ Economic News Blackout Status for {args.symbol}:")
        if allowed:
            print("  ✅ Status: TRADE ALLOWED (No active blackout window)")
        else:
            print("  ⛔ Status: TRADING PAUSED (Blackout window active)")
            print(f"  Reason: {reason}")
        print("\n📅 Upcoming High-Impact Macro Releases:")
        blackouts = news_filter.get_upcoming_blackouts(hours_ahead=720)
        for event, w_start, w_end in blackouts[:5]:
            print(f"  - [{event.currency} {event.impact.value}] {event.title} at {event.scheduled_time.strftime('%Y-%m-%d %H:%M UTC')}")
            print(f"    Window: {w_start.strftime('%H:%M')} -> {w_end.strftime('%H:%M UTC')}")



    elif args.command == "analyze-backtest":
        target_path = Path(args.path)
        if not target_path.exists():
            print(f"❌ Specified path does not exist: {args.path}")
            sys.exit(1)

        html_files = []
        if target_path.is_dir():
            html_files = sorted(list(target_path.glob("*.html")))
            if not html_files:
                print(f"❌ No .html backtest reports found in directory: {args.path}")
                sys.exit(1)
        else:
            html_files = [target_path]

        print(f"🔍 Analyzing MT5 Backtest Report(s): {len(html_files)} file(s) found...")

        if len(html_files) > 1 or args.compare:
            print("📊 Generating Multi-Run Comparative Analysis Matrix...")
            comp_md = MT5BacktestAnalyzer.compare_reports(html_files)
            print("-" * 60)
            # Print brief preview
            lines = comp_md.splitlines()
            for l in lines[:25]:
                print(l)
            print("..." if len(lines) > 25 else "")
            print("-" * 60)
            if args.export:
                out_name = args.filename or "backtest_comparison_report.md"
                out_path = export_markdown_document(
                    title="MT5 Backtest Comparative Analysis",
                    markdown_content=comp_md,
                    filename=out_name,
                )
                print(f"✅ Clean Comparative Report exported to: ./output/{out_path.name}")
        else:
            single_file = html_files[0]
            rep = MT5BacktestAnalyzer.parse_report(single_file)
            audit = rep["audit"]
            metrics = rep["metrics"]
            print("-" * 60)
            print(f"Expert:          {rep['expert']} ({rep['symbol']} {rep['period']})")
            print(f"Net Profit:      ${metrics.get('total_net_profit', '0.00')}")
            print(f"Profit Factor:   {metrics.get('profit_factor', 'N/A')}")
            print(f"Max Equity DD:   {metrics.get('equity_dd_maximal', 'N/A')}")
            print(f"Sharpe Ratio:    {metrics.get('sharpe_ratio', 'N/A')}")
            print(f"Total Trades:    {metrics.get('total_trades', '0')} (Short: {metrics.get('short_trades', '0')} | Long: {metrics.get('long_trades', '0')})")
            print(f"Quant Verdict:   {audit.get('status')} (Score: {audit.get('quant_score')}/100)")
            print("-" * 60)
            if audit.get("warnings"):
                print("⚠️ Warnings:")
                for w in audit["warnings"]:
                    print(f"  - {w}")
            if audit.get("flags"):
                print("❌ Critical Flags:")
                for f in audit["flags"]:
                    print(f"  - {f}")
            print("-" * 60)
            if args.export:
                out_name = args.filename or f"backtest_audit_{single_file.stem}.md"
                md_content = MT5BacktestAnalyzer.generate_markdown(rep)
                out_path = export_markdown_document(
                    title=f"MT5 Backtest Audit - {single_file.name}",
                    markdown_content=md_content,
                    filename=out_name,
                )
                print(f"✅ Clean Backtest Audit Report exported to: ./output/{out_path.name}")

            if args.html:
                html_name = f"dashboard_{single_file.stem}.html"
                html_content = MT5BacktestAnalyzer.generate_html_dashboard(rep)
                out_html_path = Path("output") / html_name
                out_html_path.parent.mkdir(parents=True, exist_ok=True)
                out_html_path.write_text(html_content, encoding="utf-8")
                print(f"📊 Interactive Visual HTML Dashboard exported to: ./output/{html_name}")


    elif args.command == "analyze-wfo":
        target_path = Path(args.path)
        if not target_path.exists():
            print(f"❌ Specified path does not exist: {args.path}")
            sys.exit(1)

        if target_path.is_dir():
            html_files = sorted(list(target_path.glob("*.html")))
        else:
            html_files = [target_path]

        if not html_files:
            print(f"❌ No .html reports found in: {args.path}")
            sys.exit(1)

        print(f"📐 Computing Walk-Forward Optimization Matrix for {len(html_files)} reports...")
        wfo_res = WalkForwardCalculator.analyze_wfo(html_files, oos_ratio=args.split_ratio)
        print("-" * 60)
        print(f"WFE (Walk-Forward Efficiency): {wfo_res['wfe']:.1f}% (Target ≥ 60.0%)")
        print(f"PSR (Parameter Stability):     {wfo_res['psr']:.3f} (Target ≥ 0.700)")
        print(f"DCR (Drawdown Consistency):    {wfo_res['dcr']:.1f}%")
        print(f"Composite WFO Score:           {wfo_res['composite_score']}/100")
        print(f"Robustness Verdict:            {wfo_res['verdict']}")
        print(f"Details:                       {wfo_res['verdict_desc']}")
        print("-" * 60)
        if args.export:
            md_text = WalkForwardCalculator.generate_wfo_markdown_report(wfo_res)
            out_p = export_markdown_document(
                title="Walk-Forward Optimization Matrix Report",
                markdown_content=md_text,
                filename=args.filename,
            )
            print(f"✅ Clean WFO Report exported to: ./output/{out_p.name}")


if __name__ == "__main__":
    main()
