# ⚡ Strict Token Optimization & Test Policy Directive (Zero-Test by Default)

This policy establishes strict token consumption rules and testing boundaries for GoldTrader.

---

## 1. Default Behavior: Implementation-Only Mode (Zero-Test Policy)

By default, all collaborating agents operate strictly in **Implementation-Only Mode**:
- **DO NOT WRITE TESTS**: Do not generate, mock, or update test suites autonomously.
- **DO NOT EXECUTE TEST RUNNERS**: Do not autonomously execute test runners.
- **DO NOT READ TEST CONTEXT**: Do not load test files into context unless required for broken compilation imports.
- **100% FOCUS ON PRODUCTION CODE & STRATEGY CONTRACTS**: Dedicate all reasoning to production MQL code, strategy logic, and mathematical formulas.

---

## 2. Explicit Opt-In Testing Exception

Transition into **Testing Mode** occurs ONLY when the user prompt contains explicit trigger keywords:
`"write test"`, `"unit test"`, `"test this"`, `"run tests"`, `"generate test suite"`, `"เขียนเทส"`, or `"รันเทส"`.

---

## 3. Testing Mode Guardrails

When testing mode is activated:
1. **Minimal Scope**: Test only the requested function or strategy rule.
2. **Log Suppression**: Suppress traceback logs using `-q --tb=short --maxfail=1`.
3. **Hard Auto-Fix Limit (Max 2 Attempts)**:
   - Iteration 1: Read concise error $\rightarrow$ apply targeted fix.
   - Iteration 2: Re-run once. If still failing, **STOP IMMEDIATELY**, revert changes, and report error signature under 5 lines.

---

## 4. Lightweight Verification Alternative

Prefer fast static linting (`python -m harness.cli check-mql <file>`) over heavy test execution.
When static syntax and rule checks pass with exit code `0`, the task is considered verified.
