#!/usr/bin/env python3
"""
Standalone MT5 Strategy Tester Report Parser and Analyzer script.
Compatible with direct execution or via GoldTrader harness.
"""

from __future__ import annotations
import argparse
from pathlib import Path
import sys

# Ensure repo root is on sys.path
current = Path(__file__).resolve()
repo_root = current.parents[4]  # .agents/skills/mt5-backtest-analyzer/scripts/mt5_report_parser.py -> root
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from harness.backtest_analyzer import MT5BacktestAnalyzer


def main():
    parser = argparse.ArgumentParser(description="Parse and audit MT5 Strategy Tester reports")
    parser.add_argument("path", help="Path to MT5 HTML backtest report or directory of reports")
    parser.add_argument("--compare", action="store_true", help="Compare multiple reports side-by-side")
    parser.add_argument("--output", default=None, help="Save generated Markdown report to file")
    args = parser.parse_args()

    target_path = Path(args.path)
    if not target_path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    html_files = []
    if target_path.is_dir():
        html_files = sorted(list(target_path.glob("*.html")))
        if not html_files:
            print(f"Error: No .html files found in {args.path}", file=sys.stderr)
            sys.exit(1)
    else:
        html_files = [target_path]

    if len(html_files) > 1 or args.compare:
        md = MT5BacktestAnalyzer.compare_reports(html_files)
    else:
        rep = MT5BacktestAnalyzer.parse_report(html_files[0])
        md = MT5BacktestAnalyzer.generate_markdown(rep)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(md, encoding="utf-8")
        print(f"Report saved to: {out_p}")
    else:
        print(md)


if __name__ == "__main__":
    main()
