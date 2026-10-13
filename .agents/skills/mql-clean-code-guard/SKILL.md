---
name: mql-clean-code-guard
description: Clean Code, SOLID, operator precedence, array safety, and AI failure-mode checks specialized for MQL4 & MQL5 codebases.
risk: critical
source: community-awesome-skills
---

# MQL Clean Code & Anti-Hallucination Guard

You are reviewing generated or refactored MQL4 and MQL5 code before delivery. Apply these rules as a mandatory quality and correctness pass.

---

## 1. Always-Applied Imperatives for MQL

### Operator Precedence (The Parentheses Invariant)
1. **Explicit Parentheses for Combined Operators**:
   - In MQL4/MQL5, never combine `&&` and `||` in the same logical expression without explicit grouping parentheses.
   - ❌ `if(a && b || c && d)` $\rightarrow$ Dangerous operator precedence.
   - ✅ `if((a && b) || (c && d))` $\rightarrow$ Clear, deterministic evaluation.

### Memory & Array Management
2. **Indicator Resource Cleanup**:
   - In MQL5, every handle allocated via `iCustom`, `iMA`, `iRSI`, `iATR` must have a corresponding `IndicatorRelease(handle)` in `OnDeinit()`.
3. **Dynamic Array Sizing**:
   - Dynamic arrays passed to `CopyBuffer()` or custom calculations must be resized or marked with `ArraySetAsSeries()` properly. Never call `ArraySetAsSeries()` on static/fixed-size arrays to avoid compilation errors.
4. **Buffer Indexing Bounds**:
   - Always verify that the requested bar count is available using `Bars(_Symbol, _Period)` or `iBars()` before accessing historical indices.

### Error Handling & Broker Communication
5. **No Swallowed Errors**:
   - Never ignore return values of `OrderSend()`, `trade.Buy()`, `trade.Sell()`, or `OrderModify()`.
   - Log failed attempts using `PrintFormat()` with `GetLastError()` and descriptive error codes.
6. **No Phantom APIs or Library Hallucinations**:
   - In MT4: Use verified MQL4 functions (`OrderSend`, `OrderSelect`, `OrderClose`, `MarketInfo`, `RefreshRates`). Do not invoke MT5 `CTrade` or `CopyBuffer`.
   - In MT5: Use standard trade classes (`<Trade\Trade.mqh>`, `CTrade`, `CPositionInfo`, `CSymbolInfo`). Do not invoke legacy `OP_BUY` or `OrderSelect`.
7. **No Placeholder Code**:
   - Never output `// add logic here` or `// implement your strategy`. Deliver complete, production-ready, compilable code.

---

## 2. Self-Check Before Delivery Checklist

- [ ] Are all combined `&&` and `||` statements wrapped in explicit parentheses `()`?
- [ ] For MT4 EAs: Is order iteration loop running backwards (`OrdersTotal() - 1 down to 0`)?
- [ ] For MT5 EAs: Are all indicator handles released in `OnDeinit()` with `IndicatorRelease()`?
- [ ] Does the EA have an explicit Stop Loss parameter and dynamic spread check?
- [ ] Are magic numbers isolated and configurable via `input ulong InpMagicNumber`?
- [ ] Has all conversational fluff been stripped from the structured output summary?
