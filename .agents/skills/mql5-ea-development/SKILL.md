---
name: mql5-ea-development
description: Modern MetaTrader 5 (MT5) MQL5 Expert Advisor (EA) architecture, CTrade class, CopyBuffer, PositionSelect, indicator handles, and event transactions.
risk: critical
source: internal-goldtrader
---

# MQL5 / MT5 Expert Advisor (EA) Development Architecture

Specialized guide for developing modern, object-oriented, production-ready Expert Advisors in MQL5 for MetaTrader 5 (MT5), specifically engineered for **XAUUSD (Gold)** and multi-asset trading.

---

## 1. Modern MQL5 OOP Architecture

MT5 utilizes an event-driven, asynchronous execution model with the Standard Trade Library:

```cpp
#property copyright "GoldTrader Quant Engine"
#property link      "https://github.com/GoldTrader"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

// Global Objects
CTrade         trade;
CPositionInfo  posInfo;
CSymbolInfo    symInfo;

// Inputs
input group "=== Risk Management ==="
input double   InpRiskPercent       = 1.0;       // Risk per trade (%)
input double   InpStopLossPoints    = 150.0;     // Stop Loss in points
input double   InpTakeProfitPoints  = 300.0;     // Take Profit in points
input ulong    InpMagicNumber       = 999888;    // EA Magic Number
input int      InpMaxSpreadPoints   = 40;        // Max Allowed Spread (pts)

// Indicator Handles
int            handleEMA = INVALID_HANDLE;
int            handleRSI = INVALID_HANDLE;
```

---

## 2. Mandatory Rules for MQL5 Development

### Rule 1: Always Use `CTrade` from `<Trade\Trade.mqh>`
Do not manipulate low-level `MqlTradeRequest` manually unless necessary. `CTrade` handles deviations, filling modes (`ORDER_FILLING_FOK`, `ORDER_FILLING_IOC`, `ORDER_FILLING_RETURN`), and magic numbers:

```cpp
int OnInit()
{
   if(!symInfo.Name(_Symbol)) return(INIT_FAILED);
   symInfo.Refresh();
   
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(10);
   trade.SetTypeFillingBySymbol(_Symbol); // Essential for broker execution compatibility
   
   // Initialize Indicators
   handleEMA = iMA(_Symbol, _Period, 50, 0, MODE_EMA, PRICE_CLOSE);
   handleRSI = iRSI(_Symbol, _Period, 14, PRICE_CLOSE);
   
   if(handleEMA == INVALID_HANDLE || handleRSI == INVALID_HANDLE)
   {
      Print("Error creating indicator handles");
      return(INIT_FAILED);
   }
   
   return(INIT_SUCCEEDED);
}
```

### Rule 2: Clean Indicator Resource Deallocation in `OnDeinit()`
Every indicator handle created with `iCustom`, `iMA`, `iRSI`, etc., must be released in `OnDeinit()` to prevent memory leaks in MetaTrader 5:

```cpp
void OnDeinit(const int reason)
{
   if(handleEMA != INVALID_HANDLE) IndicatorRelease(handleEMA);
   if(handleRSI != INVALID_HANDLE) IndicatorRelease(handleRSI);
   Comment("");
}
```

### Rule 3: Proper Array Management with `CopyBuffer()`
Unlike MT4 where indicators return a single `double`, MT5 requires copying data from the indicator handle into a dynamic array:
1. Declare dynamic array.
2. Set indexing direction with `ArraySetAsSeries(arr, true)` so index `0` is the latest bar.
3. Call `CopyBuffer()` and check return value ($> 0$).

```cpp
bool GetIndicatorData(double &rsiVal, double &emaVal)
{
   double rsiArr[];
   double emaArr[];
   
   ArraySetAsSeries(rsiArr, true);
   ArraySetAsSeries(emaArr, true);
   
   if(CopyBuffer(handleRSI, 0, 1, 1, rsiArr) <= 0) return false;
   if(CopyBuffer(handleEMA, 0, 1, 1, emaArr) <= 0) return false;
   
   rsiVal = rsiArr[0]; // Bar 1 (closed bar)
   emaVal = emaArr[0];
   return true;
}
```

### Rule 4: Explicit Parentheses for Combined Logical Operators
Always wrap `&&` and `||` expressions in explicit parentheses `()` to enforce evaluation precedence:

```cpp
// CORRECT: Explicit grouping
if((priceAboveEMA && (rsiValue < 30.0)) || (breakoutLong && volumeConfirmed))
{
   trade.Buy(lotSize, _Symbol, symInfo.Ask(), slPrice, tpPrice, "GoldBuy");
}
```

### Rule 5: Position Auditing with `CPositionInfo`
In MT5 (Hedging accounts), multiple positions can exist on the same symbol. Always filter by Symbol and Magic Number:

```cpp
int CountOpenPositions(ENUM_POSITION_TYPE posType)
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(posInfo.SelectByIndex(i))
      {
         if(posInfo.Symbol() == _Symbol && posInfo.Magic() == InpMagicNumber)
         {
            if(posInfo.PositionType() == posType)
               count++;
         }
      }
   }
   return count;
}
```

---

## 3. Gold (XAUUSD) Specific Real-Time Precautions

1. **Trade Filling Type Resolution**: Gold CFD accounts frequently require `ORDER_FILLING_IOC` or `ORDER_FILLING_RETURN`. Using `ORDER_FILLING_FOK` on an ECN broker will cause order rejections (`TRADE_RETCODE_INVALID_FILL`).
2. **Spread Checks**:
   ```cpp
   symInfo.RefreshRates();
   if(symInfo.Spread() > InpMaxSpreadPoints)
   {
      PrintFormat("Spread %d exceeds max allowed %d. Skipping tick.", symInfo.Spread(), InpMaxSpreadPoints);
      return;
   }
   ```
3. **Lot Calculation on Gold**:
   Gold tick value is calculated using `SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE)`. Always normalize lot sizes using `SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP)`.
