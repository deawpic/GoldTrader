//+------------------------------------------------------------------+
//|                                              TradeHelper_MT4.mqh |
//|                                  Copyright 2026, GoldTrader Quant|
//+------------------------------------------------------------------+
#property copyright "GoldTrader Quant Engine"
#property strict

//+------------------------------------------------------------------+
//| Calculate pip value in points based on symbol digits             |
//+------------------------------------------------------------------+
double GetPipPoint(string symbol)
{
   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   double point = MarketInfo(symbol, MODE_POINT);
   
   if(digits == 3 || digits == 5)
      return(point * 10.0);
   return(point);
}

//+------------------------------------------------------------------+
//| Calculate lot size based on fixed account risk percentage        |
//+------------------------------------------------------------------+
double CalculateRiskLotSize(string symbol, double riskPercent, double slPoints)
{
   if(slPoints <= 0) return(MarketInfo(symbol, MODE_MINLOT));
   
   double equity = AccountEquity();
   double riskMoney = equity * (riskPercent / 100.0);
   double tickValue = MarketInfo(symbol, MODE_TICKVALUE);
   double tickSize  = MarketInfo(symbol, MODE_TICKSIZE);
   double point     = MarketInfo(symbol, MODE_POINT);
   
   if(tickSize <= 0) tickSize = point;
   
   double ticksAtRisk = slPoints * (point / tickSize);
   double moneyPerLotAtRisk = ticksAtRisk * tickValue;
   
   if(moneyPerLotAtRisk <= 0) return(MarketInfo(symbol, MODE_MINLOT));
   
   double calculatedLot = riskMoney / moneyPerLotAtRisk;
   
   double step   = MarketInfo(symbol, MODE_LOTSTEP);
   double minLot = MarketInfo(symbol, MODE_MINLOT);
   double maxLot = MarketInfo(symbol, MODE_MAXLOT);
   
   calculatedLot = MathFloor(calculatedLot / step) * step;
   
   if(calculatedLot < minLot) calculatedLot = minLot;
   if(calculatedLot > maxLot) calculatedLot = maxLot;
   
   return(calculatedLot);
}

//+------------------------------------------------------------------+
//| Check if spread is within acceptable limits                      |
//+------------------------------------------------------------------+
bool IsSpreadAcceptable(string symbol, int maxSpreadPoints)
{
   double currentSpread = MarketInfo(symbol, MODE_SPREAD);
   return(currentSpread <= maxSpreadPoints);
}
