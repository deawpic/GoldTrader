---
name: mql4-ea-development
description: Expert MetaTrader 4 (MT4) MQL4 Expert Advisor (EA) architecture, order pool loops, ticket management, slippage, error retry logic, and XAUUSD execution.
risk: critical
source: internal-goldtrader
---

# MQL4 / MT4 Expert Advisor (EA) Development Architecture

Specialized guide for developing robust, production-ready Expert Advisors in MQL4 for MetaTrader 4 (MT4), with particular focus on high-volatility instruments like **XAUUSD (Gold)**.

---

## 1. Core Architecture & Event Lifecycle

An MT4 Expert Advisor must implement standard event functions:

```cpp
//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Validate account, symbol, inputs, and chart settings
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up visual objects, timers, files
   Comment("");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Guard: Check if trading is allowed and broker is connected
   if(!IsTradeAllowed() || !IsConnected()) return;
   
   // 1. New Bar check (if bar-based)
   // 2. Risk & Margin checks
   // 3. Trailing Stop & Open Position Maintenance
   // 4. Signal Generation & Entry Execution
}
```

---

## 2. Mandatory Rules for MQL4 Development

### Rule 1: Backwards Iteration for Order Pool (Order Loops)
When closing, modifying, or auditing orders using `OrdersTotal()`, you **MUST iterate backwards**. Iterating forwards (`i++`) causes order indices to shift when an order is closed, resulting in skipped orders!

```cpp
// CORRECT: Backwards iteration
for(int i = OrdersTotal() - 1; i >= 0; i--)
{
   if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
   {
      if(OrderSymbol() == Symbol() && OrderMagicNumber() == MagicNumber)
      {
         // Process order...
      }
   }
}

// FORBIDDEN: Forward iteration when modifying or closing
// for(int i = 0; i < OrdersTotal(); i++) // BUG: Skips orders upon OrderClose!
```

### Rule 2: Explicit Parentheses for Combined Logical Operators
In MQL4, combining `&&` and `||` without explicit parentheses causes operator precedence bugs that can trigger erroneous trades.

```cpp
// CORRECT: Explicit grouping
if((isTrendBullish && rsiOversold) || (breakoutBuy && volumeSurge))
{
   ExecuteBuyOrder();
}

// FORBIDDEN: Ambiguous precedence
// if(isTrendBullish && rsiOversold || breakoutBuy && volumeSurge) // BUG PRONE!
```

### Rule 3: Robust `OrderSend` Execution with Slippage & Error Retries
Gold is prone to requotes (`ERR_REQUOTE`, 138), invalid stops (`ERR_INVALID_STOPS`, 130), and busy trade contexts (`ERR_TRADE_CONTEXT_BUSY`, 146).
Always check the ticket return value, refresh rates, and apply retry loops:

```cpp
int SendOrderWithRetry(int type, double lot, double price, int slippage, double sl, double tp, string comment, int magic)
{
   int ticket = -1;
   int maxAttempts = 3;
   
   for(int attempt = 1; attempt <= maxAttempts; attempt++)
   {
      RefreshRates();
      price = (type == OP_BUY) ? Ask : Bid;
      
      ticket = OrderSend(Symbol(), type, lot, price, slippage, sl, tp, comment, magic, 0, (type == OP_BUY ? clrGreen : clrRed));
      
      if(ticket > 0)
      {
         PrintFormat("Order #%d opened successfully at %f", ticket, price);
         return ticket;
      }
      
      int err = GetLastError();
      PrintFormat("OrderSend attempt %d failed with error %d: %s", attempt, err, ErrorDescription(err));
      
      // Stop retrying on terminal errors
      if(err == 130 || err == 134) // ERR_INVALID_STOPS or ERR_NOT_ENOUGH_MONEY
         break;
         
      Sleep(300); // Wait 300ms before retrying
   }
   
   return -1;
}
```

### Rule 4: Pip vs Point Calculation for 4/5 Digits and Gold
Brokers quote Gold in 2 decimals (e.g. 2650.50) or 3 decimals (e.g. 2650.505).
1 Pip is traditionally 0.10 USD on Gold ($10$ points on a 3-digit broker or $1$ point on a 2-digit broker).

```cpp
double GetPipValue()
{
   if(Digits == 3 || Digits == 5)
      return (Point * 10.0);
   return Point;
}
```

### Rule 5: Technical Indicator Direct Double Call with Shift
In MQL4, indicator functions (`iRSI`, `iMA`, `iATR`, `iCustom`) return a `double` directly, taking the bar `shift` as the last parameter.
- `shift = 0`: Current forming bar (repainting possible).
- `shift = 1`: Previous fully closed bar (deterministic, no repainting).

```cpp
// Read previous closed bar to prevent repainting
double prevRSI = iRSI(Symbol(), Period(), 14, PRICE_CLOSE, 1);
double prevEMA = iMA(Symbol(), Period(), 50, 0, MODE_EMA, PRICE_CLOSE, 1);
```

---

## 3. Gold (XAUUSD) Specific Risk Mitigations in MT4

1. **Dynamic Spread Filter**: Gold spreads widen from 15 points to 100+ points during the Asian session, news events, or rollover (23:00 - 00:00 server time).
   ```cpp
   double currentSpread = MarketInfo(Symbol(), MODE_SPREAD);
   if(currentSpread > MaxAllowedSpreadPoints)
   {
      PrintFormat("Spread too high (%f pts > %f max). Skipping entry.", currentSpread, MaxAllowedSpreadPoints);
      return;
   }
   ```
2. **Max Orders Per Bar**: Prevents runaway grid clusters during flash crashes:
   ```cpp
   static datetime lastBarTime = 0;
   if(Time[0] == lastBarTime) return; // Only 1 trade per new bar
   lastBarTime = Time[0];
   ```
3. **Hard Stop Loss Requirement**: Never place an order without a verified Stop Loss. If the broker is an ECN (cannot set SL in `OrderSend`), use `OrderModify` immediately after order creation.
