# 📐 MQL4 & MQL5 Coding Standards (GoldTrader)

Official coding guidelines, syntax conventions, and architectural rules for MT4 and MT5 Expert Advisors.

---

## 1. Syntax & Style Conventions

1. **Logical Operator Precedence**:
   - Always group combined `&&` and `||` conditions in explicit parentheses:
     ```cpp
     if((trendFilter && rsiSignal) || (breakoutSignal && volumeFilter))
     ```
2. **Order Loop Direction (MT4)**:
   - Always iterate backwards from `OrdersTotal() - 1` down to `0` when managing trades.
3. **Indicator Deallocation (MT5)**:
   - Always call `IndicatorRelease(handle)` in `OnDeinit()`.
4. **Variable Naming**:
   - Inputs: Prefix with `Inp` (e.g. `InpStopLossPoints`).
   - Handles: Prefix with `handle` (e.g. `handleEMA`).
   - Global objects: Clear, lowercase camelCase (e.g. `trade`, `posInfo`, `symInfo`).

---

## 2. Cross-Platform Architectural Compatibility

| Concern | MetaTrader 4 (MQL4) | MetaTrader 5 (MQL5) |
| :--- | :--- | :--- |
| **Trade Execution** | `OrderSend(Symbol(), OP_BUY, lot, price, slippage, sl, tp...)` | `trade.Buy(lot, _Symbol, price, sl, tp, comment)` via `<Trade\Trade.mqh>` |
| **Position Access** | `OrderSelect(i, SELECT_BY_POS, MODE_TRADES)` | `posInfo.SelectByIndex(i)` or `PositionGetTicket(i)` |
| **Indicator Access** | `iRSI(Symbol(), Period(), 14, PRICE_CLOSE, shift)` directly returns `double` | Indicator handle $\rightarrow$ `CopyBuffer(handle, 0, shift, count, arr)` |
| **Time Series** | `Open[i]`, `Close[i]`, `High[i]`, `Low[i]`, `Time[i]` | `CopyRates()` or `CopyClose()` into `ArraySetAsSeries()` arrays |
| **Market Info** | `MarketInfo(Symbol(), MODE_SPREAD)` | `SymbolInfoDouble(_Symbol, SYMBOL_ASK)`, `SymbolInfoInteger(_Symbol, SYMBOL_SPREAD)` |
| **Account Info** | `AccountEquity()`, `AccountBalance()` | `AccountInfoDouble(ACCOUNT_EQUITY)`, `AccountInfoDouble(ACCOUNT_BALANCE)` |
