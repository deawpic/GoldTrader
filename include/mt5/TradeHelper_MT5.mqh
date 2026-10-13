//+------------------------------------------------------------------+
//|                                              TradeHelper_MT5.mqh |
//|                                  Copyright 2026, GoldTrader Quant|
//+------------------------------------------------------------------+
#property copyright "GoldTrader Quant Engine"
#property strict

#include <Trade\SymbolInfo.mqh>

class CTradeHelper
{
public:
   //+------------------------------------------------------------------+
   //| Calculate pip value in price units                               |
   //+------------------------------------------------------------------+
   static double GetPipPoint(CSymbolInfo &sym)
   {
      if(sym.Digits() == 3 || sym.Digits() == 5)
         return(sym.Point() * 10.0);
      return(sym.Point());
   }

   //+------------------------------------------------------------------+
   //| Calculate lot size based on equity risk percentage and SL points |
   //+------------------------------------------------------------------+
   static double CalculateRiskLotSize(CSymbolInfo &sym, double riskPercent, double slPoints)
   {
      if(slPoints <= 0) return(sym.LotsMin());

      double equity    = AccountInfoDouble(ACCOUNT_EQUITY);
      double riskMoney = equity * (riskPercent / 100.0);
      double tickValue = sym.TickValue();
      double tickSize  = sym.TickSize();
      double point     = sym.Point();

      if(tickSize <= 0) tickSize = point;

      double ticksAtRisk = slPoints * (point / tickSize);
      double moneyPerLotAtRisk = ticksAtRisk * tickValue;

      if(moneyPerLotAtRisk <= 0) return(sym.LotsMin());

      double calculatedLot = riskMoney / moneyPerLotAtRisk;
      double step   = sym.LotsStep();
      double minLot = sym.LotsMin();
      double maxLot = sym.LotsMax();

      calculatedLot = MathFloor(calculatedLot / step) * step;

      if(calculatedLot < minLot) calculatedLot = minLot;
      if(calculatedLot > maxLot) calculatedLot = maxLot;

      return(calculatedLot);
   }

   //+------------------------------------------------------------------+
   //| Check if spread is acceptable                                    |
   //+------------------------------------------------------------------+
   static bool IsSpreadAcceptable(CSymbolInfo &sym, int maxSpreadPoints)
   {
      sym.RefreshRates();
      return(sym.Spread() <= maxSpreadPoints);
   }
};
