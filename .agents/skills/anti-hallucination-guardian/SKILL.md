---
name: anti-hallucination-guardian
description: Empirical verification oracle, Ground Truth checks, dependency grounding, and strict token-optimized verification.
risk: critical
source: internal-goldtrader
---

# Anti-Hallucination & Verification Guardian (GoldTrader)

Enforces non-negotiable empirical truth, verifies physical file artifacts, prevents API hallucinations, and controls token usage.

---

## 1. The 4 Iron Laws of Ground Truth

1. **Deterministic Verification (Iron Law)**:
   - NEVER rely on an agent's self-reported "Done" or "Success" statement.
   - All code, formulas, and EAs must be verified using deterministic ground truth: syntax passes, linter exit code `0`, and file existence.
2. **Codebase & Contract Grounding First**:
   - NEVER assume or fabricate file paths, parameter names, or indicator functions.
   - ALWAYS inspect existing codebase files before writing code referencing them.
3. **No Phantom Libraries or APIs**:
   - In MQL4, only use verified MT4 functions (`OrderSend`, `OrderClose`, `MarketInfo`).
   - In MQL5, only use verified MT5 standard trade classes (`CTrade`, `CPositionInfo`, `CSymbolInfo`).
4. **Empirical Evidence Required**:
   - Every claim of resolution must cite exact file paths, line numbers, or execution output.
5. **Strict Machine-Local Path Ban in Saved Documents**:
   - NEVER reference local drive letters (`C:`, `D:`) or URI schemes (`file://`, `file:///...`) when saving or exporting documents, PRDs, specifications, or reports into `./output/`, `docs/`, or project files.
   - All references MUST be repository-relative (`./output/...`, `./experts/...`, `docs/...`) or clean filenames.

---

## 2. Strict Token Optimization Directive (Zero-Test by Default)

1. **Implementation-Only Mode by Default**:
   - DO NOT write unit test suites or mock tests unless the user prompt explicitly triggers Testing Mode.
   - Focus 100% of context window and computation on production MQL code, formulas, and strategy specs.
2. **Opt-In Testing Triggers**:
   - Transition to Testing Mode ONLY if the prompt contains: `"write test"`, `"unit test"`, `"test this"`, `"run tests"`, or `"generate test suite"`.
3. **Log Suppression & 2-Attempt Auto-Fix Cap**:
   - Suppress traceback logs using `-q --tb=short --maxfail=1`.
   - Maximum 2 auto-fix iterations if compilation or tests fail; stop and report concise error signature under 5 lines if still failing.
