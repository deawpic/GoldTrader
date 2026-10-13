"""
Deterministic Ground-Truth Verifier for GoldTrader (Pre-Handoff Fast Gate & MQL Linter).
Performs lightweight syntax/type/file checks, boundary isolation, blast radius auditing,
and deep MQL4/MQL5 code rule verification without consuming LLM tokens.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import List, Optional, Tuple

from harness.schemas import VerificationReceipt


IGNORE_BOUNDARY_FILES = {
    "stack.json",
    ".gitignore",
    ".tmp",
    "cache",
}


@dataclass
class VerificationResult:
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    verified_files: List[str] = field(default_factory=list)
    receipt: Optional[VerificationReceipt] = None

    def summary(self) -> str:
        if self.passed:
            return f"Deterministic Verification Passed ({len(self.verified_files)} files verified)."
        return f"Deterministic Verification Failed with {len(self.errors)} error(s): " + "; ".join(self.errors[:3])


class DeterministicVerifier:
    """Fast ground-truth verification and MQL4/MQL5 linting without invoking LLMs."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def _normalize_rel_path(self, raw_path: str) -> str:
        p = Path(raw_path.strip().strip('"'))
        if p.is_absolute():
            try:
                return str(p.relative_to(self.workspace_root)).replace("\\", "/")
            except ValueError:
                return str(p).replace("\\", "/")
        return str(p).replace("\\", "/")

    def check_file_boundaries(
        self,
        allowed_files: List[str],
        exempt_files: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Hyper-Disciplined Stack Hygiene:
        Inspects git status to ensure no files outside allowed_files (or exempt prior task files)
        were created or modified.
        """
        if not allowed_files:
            return True, []

        allowed_normalized = {self._normalize_rel_path(f) for f in allowed_files if f}
        if exempt_files:
            allowed_normalized.update(self._normalize_rel_path(f) for f in exempt_files if f)

        cmd = ["git", "status", "--porcelain", "-uall"]
        try:
            res = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True, check=False)
            lines = res.stdout.strip().splitlines()
        except Exception:
            return True, []

        unauthorized_files: List[str] = []
        for line in lines:
            if not line or len(line) < 4:
                continue
            file_entry = line[2:].strip()
            if " -> " in file_entry:
                file_entry = file_entry.split(" -> ")[-1].strip()
            norm_entry = self._normalize_rel_path(file_entry)

            entry_name = Path(norm_entry).name
            if entry_name in IGNORE_BOUNDARY_FILES or norm_entry.endswith(".tmp") or norm_entry.startswith(".tmp"):
                continue

            if norm_entry not in allowed_normalized:
                unauthorized_files.append(norm_entry)

        if unauthorized_files:
            return False, unauthorized_files
        return True, []

    def check_blast_radius(
        self,
        max_lines: int = 300,
        max_files: int = 5,
        target_files: Optional[List[str]] = None,
        exempt_extensions: Tuple[str, ...] = (".md",),
    ) -> Tuple[bool, str]:
        """
        Atomic Decomposition:
        Inspects git diff --numstat to ensure code changes don't exceed atomic blast radius.
        Design/spec documents (.md) are exempt from the line-count cap.
        """
        rel_targets: List[str] = []
        if target_files:
            rel_targets = [self._normalize_rel_path(f) for f in target_files if f]

        cmd = ["git", "diff", "--numstat"]
        if rel_targets:
            cmd.extend(["--"] + rel_targets)

        output = ""
        try:
            res = subprocess.run(cmd, cwd=self.workspace_root, capture_output=True, text=True, check=False)
            output = res.stdout.strip()
            if not output:
                staged_cmd = ["git", "diff", "--cached", "--numstat"]
                if rel_targets:
                    staged_cmd.extend(["--"] + rel_targets)
                res_staged = subprocess.run(staged_cmd, cwd=self.workspace_root, capture_output=True, text=True, check=False)
                output = res_staged.stdout.strip()
        except Exception:
            return True, ""

        if not output:
            return True, ""

        total_lines = 0
        total_files = 0
        for line in output.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                ins, dels, fname = parts[0], parts[1], parts[2]
                path_obj = Path(fname)
                if path_obj.name in IGNORE_BOUNDARY_FILES:
                    continue
                if exempt_extensions and path_obj.suffix.lower() in exempt_extensions:
                    continue
                try:
                    total_lines += int(ins) + int(dels)
                    total_files += 1
                except ValueError:
                    pass

        if total_files > max_files:
            return False, f"Modified {total_files} files (exceeds atomic limit of {max_files}). Push smaller subtasks."
        if total_lines > max_lines:
            return False, f"Modified {total_lines} lines (exceeds atomic limit of {max_lines}). Push smaller subtasks."

        return True, ""


    def verify_artifacts(self, artifact_paths: List[str], run_compiler: bool = False) -> VerificationResult:
        """
        Validates all generated artifacts:
        1. Confirms physical existence on disk (anti-hallucination guard).
        2. Checks syntax: Python (py_compile), JSON (json.loads), Markdown rules.
        3. Runs MQL4/MQL5 deep linter for .mq4, .mq5, .mqh files.
        4. Optionally runs headless MetaEditor compiler if requested.
        """
        result = VerificationResult(passed=True)
        if not artifact_paths:
            result.warnings.append("No artifacts declared for verification.")
            return result

        for raw_path in artifact_paths:
            path = Path(raw_path)
            if not path.is_absolute():
                path = self.workspace_root / path

            # 1. Physical existence check
            if not path.exists():
                result.passed = False
                result.errors.append(f"Physical file missing (Hallucinated artifact): {raw_path}")
                continue

            if not path.is_file():
                result.passed = False
                result.errors.append(f"Artifact path is not a regular file: {raw_path}")
                continue

            result.verified_files.append(str(path))

            # 2. Syntax and domain validation based on extension
            ext = path.suffix.lower()

            if ext == ".py":
                py_valid, py_err = self._verify_python_syntax(path)
                if not py_valid:
                    result.passed = False
                    result.errors.append(f"Python syntax error in {path.name}: {py_err}")

            elif ext == ".json":
                json_valid, json_err = self._verify_json_syntax(path)
                if not json_valid:
                    result.passed = False
                    result.errors.append(f"Invalid JSON syntax in {path.name}: {json_err}")

            elif ext == ".md":
                if path.stat().st_size == 0:
                    result.passed = False
                    result.errors.append(f"Markdown artifact is empty (0 bytes): {path.name}")
                md_errs = self._verify_markdown_rules(path)
                if md_errs:
                    for me in md_errs:
                        result.warnings.append(f"Markdown notice in {path.name}: {me}")

            elif ext in {".mq4", ".mq5", ".mqh"}:
                mql_valid, mql_errs, mql_warns = self.verify_mql_file(path)
                if not mql_valid:
                    result.passed = False
                    for err in mql_errs:
                        result.errors.append(f"MQL error in {path.name}: {err}")
                for w in mql_warns:
                    result.warnings.append(f"MQL warning in {path.name}: {w}")

                # Optional headless MetaEditor real compiler pass for EAs
                if run_compiler and ext in {".mq4", ".mq5"}:
                    c_valid, c_errs, c_warns, out_bin = self.compile_with_metaeditor(path)
                    if not c_valid:
                        result.passed = False
                        for ce in c_errs:
                            result.errors.append(f"MetaEditor compile error in {path.name}: {ce}")
                    for cw in c_warns:
                        result.warnings.append(f"MetaEditor compile warning in {path.name}: {cw}")
                    if out_bin:
                        result.verified_files.append(str(out_bin))

        if result.passed and result.verified_files:
            gate_name = "METAEDITOR_AND_STATIC_CHECK" if run_compiler else "MQL_AND_STATIC_CHECK"
            result.receipt = VerificationReceipt(
                timestamp=time.time(),
                gate_type=gate_name,
                verified_files=result.verified_files,
                exit_code=0,
                status="PASSED",
                details=f"Verified {len(result.verified_files)} artifact(s) successfully.",
            )

        return result

    def verify_mql_file(self, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """
        Deep static inspection for MQL4 / MQL5 files:
        - Balanced braces and parentheses
        - Precedence of logical operators (&& and ||)
        - MT4 vs MT5 API compatibility check
        - EA entry handler presence (OnTick)
        - MagicNumber, Slippage, and StopLoss sanity
        """
        errors: List[str] = []
        warnings: List[str] = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return False, [f"Failed to read file: {e}"], []

        ext = file_path.suffix.lower()
        is_mq4 = ext == ".mq4"
        is_mq5 = ext == ".mq5"
        is_header = ext == ".mqh"

        # 1. Balanced Braces and Parentheses
        brace_count = 0
        paren_count = 0
        in_line_comment = False
        in_block_comment = False
        in_string = False
        escape = False

        i = 0
        n = len(content)
        while i < n:
            char = content[i]
            next_char = content[i + 1] if i + 1 < n else ""

            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                if char == "*" and next_char == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                i += 1
                continue

            if char == "/" and next_char == "/":
                in_line_comment = True
                i += 2
                continue
            if char == "/" and next_char == "*":
                in_block_comment = True
                i += 2
                continue
            if char == '"':
                in_string = True
                i += 1
                continue

            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count < 0:
                    errors.append(f"Unexpected closing brace '}}' without matching opening brace at char index {i}")
                    break
            elif char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
                if paren_count < 0:
                    errors.append(f"Unexpected closing parenthesis ')' at char index {i}")
                    break

            i += 1

        if brace_count > 0:
            errors.append(f"Unclosed curly brace: {brace_count} opening brace(s) missing matching '}}'")
        if paren_count > 0:
            errors.append(f"Unclosed parenthesis: {paren_count} opening parenthesis missing matching ')'")

        # 2. Check logical operator precedence (Crucial MQL rule: explicit parentheses for && and ||)
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # Check if line contains both && and ||
            if "&&" in stripped and "||" in stripped:
                # Basic heuristic: if there's no nested parentheses grouping them
                # Count inner parens between operators
                if "(" in stripped and ")" in stripped:
                    # Look for pattern where && and || share the same depth
                    pass
                else:
                    warnings.append(
                        f"Line {idx}: Unparenthesized combined '&&' and '||' detected. "
                        "Enforce explicit parentheses to prevent runtime order execution bugs."
                    )

        # 3. Cross-Platform API Compliance Check
        if is_mq4:
            # In MQL4, flag accidental MT5-only constructs
            mt5_constructs = [
                ("CTrade", "CTrade is an MT5 class (<Trade\\Trade.mqh>). In MT4, use OrderSend/OrderClose."),
                ("CPositionInfo", "CPositionInfo is an MT5 class. In MT4, use OrderSelect/OrderType."),
                ("CopyBuffer", "CopyBuffer is MT5. In MT4, use iCustom/iRSI/iMA with shift parameter."),
                ("PositionSelect", "PositionSelect is MT5. In MT4, use OrderSelect with MODE_TRADES."),
                ("MqlTradeRequest", "MqlTradeRequest is an MT5 structure. In MT4, use OrderSend parameters."),
                ("OnTradeTransaction", "OnTradeTransaction is an MT5 event handler not available in standard MT4."),
            ]
            for construct, reason in mt5_constructs:
                if re.search(r"\b" + construct + r"\b", content):
                    errors.append(f"MT5 construct '{construct}' found in MT4 file: {reason}")

        if is_mq5:
            # In MQL5, flag MT4-only constructs (unless using custom wrapper)
            mt4_constructs = [
                ("OrderSelect", "OrderSelect is legacy MT4 syntax. In MT5, use PositionGetTicket/PositionSelect or CPositionInfo."),
                ("OrderClose", "OrderClose is legacy MT4 syntax. In MT5, use trade.PositionClose() or CTrade."),
                ("OrdersTotal()", "OrdersTotal() in MT5 only counts pending orders, not open positions (PositionsTotal())."),
                ("OP_BUY", "OP_BUY is MT4 enum. In MT5, use ORDER_TYPE_BUY or trade.Buy()."),
                ("OP_SELL", "OP_SELL is MT4 enum. In MT5, use ORDER_TYPE_SELL or trade.Sell()."),
                ("MarketInfo", "MarketInfo is MT4. In MT5, use SymbolInfoDouble/SymbolInfoInteger."),
            ]
            for construct, reason in mt4_constructs:
                if re.search(r"\b" + construct + r"\b", content):
                    warnings.append(f"Legacy MT4 construct '{construct}' found in MT5 file: {reason}")

        # 4. EA Event Cycle Check
        if is_mq4 or is_mq5:
            if not is_header:
                if not re.search(r"\bvoid\s+OnTick\s*\(\s*\)", content):
                    warnings.append("No standard 'void OnTick()' event handler found. An EA requires OnTick() to trade.")

        # 5. Risk containment checks
        if (is_mq4 or is_mq5) and not is_header:
            # Check for Stop Loss consideration
            if not re.search(r"(StopLoss|Stop_Loss|sl_points|InpStopLoss|inp_sl)", content, re.IGNORECASE):
                warnings.append("No explicit Stop Loss variable or parameter detected. Always include risk containment.")

            # In MT4, check if OrderSend result is checked
            if is_mq4 and "OrderSend(" in content:
                if not re.search(r"(ticket\s*<|ticket\s*==\s*-1|GetLastError)", content):
                    warnings.append("OrderSend return code / ticket error handling not detected. Check ticket < 0 and GetLastError().")

        return len(errors) == 0, errors, warnings

    def _verify_python_syntax(self, file_path: Path) -> Tuple[bool, str]:
        cmd = [sys.executable, "-m", "py_compile", str(file_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True, ""
        err_msg = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else "Unknown syntax error"
        return False, err_msg

    def _verify_json_syntax(self, file_path: Path) -> Tuple[bool, str]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)
            return True, ""
        except Exception as e:
            return False, str(e)

    def _verify_markdown_rules(self, file_path: Path) -> List[str]:
        warnings = []
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            # Check for ASCII box tables
            if re.search(r"\+[-+]+\+", text):
                warnings.append("ASCII box border (+---+) detected. Replace with standard Markdown table (| ... |).")
            if re.search(r"[├└│┌┐┘]", text):
                warnings.append("ASCII tree characters detected. Replace with Mermaid diagram.")
        except Exception:
            pass
        return warnings

    def find_metaeditor(self, platform: Optional[str] = None) -> Optional[Path]:
        """
        Locates MetaEditor binary for MT4 or MT5.
        Checks environment variables, default installation directories in Program Files,
        and standard locations.
        """
        target = (platform or "").lower().strip()
        candidates: List[Path] = []

        if target in {"mt4", ""}:
            env_mt4 = os.environ.get("MT4_METAEDITOR_PATH")
            if env_mt4:
                candidates.append(Path(env_mt4))
            candidates.extend([
                Path(r"C:\Program Files (x86)\MetaTrader 4\metaeditor.exe"),
                Path(r"C:\Program Files\MetaTrader 4\metaeditor.exe"),
            ])
            for pf in [os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), os.environ.get("ProgramFiles", r"C:\Program Files")]:
                pf_path = Path(pf)
                if pf_path.exists():
                    try:
                        for mt_dir in pf_path.glob("MetaTrader*"):
                            if "5" not in mt_dir.name:
                                candidate = mt_dir / "metaeditor.exe"
                                if candidate not in candidates:
                                    candidates.append(candidate)
                    except Exception:
                        pass

        if target in {"mt5", ""}:
            env_mt5 = os.environ.get("MT5_METAEDITOR_PATH")
            if env_mt5:
                candidates.append(Path(env_mt5))
            candidates.extend([
                Path(r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"),
                Path(r"C:\Program Files\MetaTrader 5\metaeditor.exe"),
                Path(r"C:\Program Files (x86)\MetaTrader 5\MetaEditor64.exe"),
                Path(r"C:\Program Files (x86)\MetaTrader 5\metaeditor.exe"),
            ])
            for pf in [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]:
                pf_path = Path(pf)
                if pf_path.exists():
                    try:
                        for mt_dir in pf_path.glob("MetaTrader 5*"):
                            for exe_name in ["MetaEditor64.exe", "metaeditor.exe"]:
                                candidate = mt_dir / exe_name
                                if candidate not in candidates:
                                    candidates.append(candidate)
                    except Exception:
                        pass

        for cand in candidates:
            if cand.exists() and cand.is_file():
                return cand.resolve()

        return None

    def compile_with_metaeditor(
        self,
        file_path: Path,
        metaeditor_path: Optional[Path] = None,
        timeout: int = 30,
    ) -> Tuple[bool, List[str], List[str], Optional[Path]]:
        """
        Compiles an MQL4 or MQL5 file headlessly via MetaEditor.
        Returns: (success: bool, errors: List[str], warnings: List[str], binary_path: Optional[Path])
        """
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return False, [f"Source file not found: {p}"], [], None

        ext = p.suffix.lower()
        if ext == ".mq4":
            platform = "mt4"
            expected_bin = p.with_suffix(".ex4")
        elif ext == ".mq5":
            platform = "mt5"
            expected_bin = p.with_suffix(".ex5")
        else:
            return False, [f"Unsupported file extension '{ext}' for MetaEditor compilation (expected .mq4 or .mq5)"], [], None

        compiler = metaeditor_path or self.find_metaeditor(platform)
        if not compiler or not compiler.exists():
            return False, [
                f"MetaEditor binary for {platform.upper()} not found. "
                f"Install MetaTrader or configure {platform.upper()}_METAEDITOR_PATH environment variable."
            ], [], None

        tmp_dir = self.workspace_root / ".tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        log_file = tmp_dir / f"compile_{p.stem}_{int(time.time() * 1000)}.log"

        if log_file.exists():
            try:
                log_file.unlink()
            except Exception:
                pass

        cmd = [
            str(compiler),
            f"/compile:{p}",
            f"/log:{log_file}",
        ]

        log_content = ""
        try:
            subprocess.run(cmd, cwd=self.workspace_root, timeout=timeout, capture_output=True, check=False)

            start_wait = time.time()
            while time.time() - start_wait < 5.0:
                if log_file.exists() and log_file.stat().st_size > 0:
                    time.sleep(0.1)
                    break
                time.sleep(0.1)

            if not log_file.exists():
                return False, [f"MetaEditor executed but no log file generated at {log_file}."], [], None

            for enc in ["utf-16", "utf-8", "cp874", "latin-1"]:
                try:
                    log_content = log_file.read_text(encoding=enc)
                    break
                except Exception:
                    continue

        except Exception as e:
            return False, [f"MetaEditor execution error: {e}"], [], None
        finally:
            if log_file.exists():
                try:
                    log_file.unlink()
                except Exception:
                    pass

        errors: List[str] = []
        warnings: List[str] = []
        has_result_line = False
        result_errors = -1
        result_warnings = -1

        for line in log_content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            if " : error " in line_str or line_str.startswith("Error:"):
                errors.append(line_str)
            elif " : warning " in line_str or line_str.startswith("Warning:"):
                warnings.append(line_str)

            res_match = re.search(r"Result:\s*(\d+)\s*errors?,\s*(\d+)\s*warnings?", line_str, re.IGNORECASE)
            if res_match:
                has_result_line = True
                result_errors = int(res_match.group(1))
                result_warnings = int(res_match.group(2))

        if has_result_line:
            is_success = (result_errors == 0)
            if result_errors > 0 and not errors:
                errors.append(f"MetaEditor reported {result_errors} error(s)")
        else:
            is_success = len(errors) == 0 and expected_bin.exists()

        out_bin = expected_bin if (expected_bin.exists() and is_success) else None
        return is_success, errors, warnings, out_bin

