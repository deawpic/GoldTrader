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

//+------------------------------------------------------------------+
//| Apply Breakeven Protection (Locks profit to breakeven + lockPts) |
//+------------------------------------------------------------------+
void ApplyBreakeven(string symbol, int magic, double triggerPoints, double lockPoints)
{
   double point = MarketInfo(symbol, MODE_POINT);
   
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderSymbol() == symbol && OrderMagicNumber() == magic)
         {
            if(OrderType() == OP_BUY)
            {
               double currentProfitPoints = (Bid - OrderOpenPrice()) / point;
               double targetSL = OrderOpenPrice() + (lockPoints * point);
               
               if(currentProfitPoints >= triggerPoints && (OrderStopLoss() < targetSL || OrderStopLoss() == 0))
               {
                  if(OrderModify(OrderTicket(), OrderOpenPrice(), targetSL, OrderTakeProfit(), 0, clrBlue))
                  {
                     PrintFormat("MT4 Buy #%d moved to Breakeven (+%.1f pts)", OrderTicket(), lockPoints);
                  }
               }
            }
            else if(OrderType() == OP_SELL)
            {
               double currentProfitPoints = (OrderOpenPrice() - Ask) / point;
               double targetSL = OrderOpenPrice() - (lockPoints * point);
               
               if(currentProfitPoints >= triggerPoints && (OrderStopLoss() > targetSL || OrderStopLoss() == 0))
               {
                  if(OrderModify(OrderTicket(), OrderOpenPrice(), targetSL, OrderTakeProfit(), 0, clrBlue))
                  {
                     PrintFormat("MT4 Sell #%d moved to Breakeven (+%.1f pts)", OrderTicket(), lockPoints);
                  }
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Apply Dynamic Trailing Stop                                      |
//+------------------------------------------------------------------+
void ApplyTrailingStop(string symbol, int magic, double trailPoints, double minProfitPoints)
{
   if(trailPoints <= 0) return;
   double point = MarketInfo(symbol, MODE_POINT);
   double stopLevel = MarketInfo(symbol, MODE_STOPLEVEL);
   if(trailPoints < stopLevel) trailPoints = stopLevel;
   
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderSymbol() == symbol && OrderMagicNumber() == magic)
         {
            if(OrderType() == OP_BUY)
            {
               double profitPoints = (Bid - OrderOpenPrice()) / point;
               if(profitPoints >= minProfitPoints)
               {
                  double targetSL = Bid - (trailPoints * point);
                  if(targetSL > OrderStopLoss() + (5.0 * point))
                  {
                     if(OrderModify(OrderTicket(), OrderOpenPrice(), targetSL, OrderTakeProfit(), 0, clrAqua))
                     {
                        // Trailing stop modified successfully
                     }
                  }
               }
            }
            else if(OrderType() == OP_SELL)
            {
               double profitPoints = (OrderOpenPrice() - Ask) / point;
               if(profitPoints >= minProfitPoints)
               {
                  double targetSL = Ask + (trailPoints * point);
                  if(OrderStopLoss() == 0 || targetSL < OrderStopLoss() - (5.0 * point))
                  {
                     if(OrderModify(OrderTicket(), OrderOpenPrice(), targetSL, OrderTakeProfit(), 0, clrAqua))
                     {
                        // Trailing stop modified successfully
                     }
                  }
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Apply ATR-Based Volatility Trailing Stop                         |
//+------------------------------------------------------------------+
void ApplyATRTrailingStop(string symbol, int timeframe, int magic, int atrPeriod, double atrMultiplier)
{
   double atr = iATR(symbol, timeframe, atrPeriod, 1);
   if(atr <= 0) return;
   
   double trailDistance = atr * atrMultiplier;
   double point = MarketInfo(symbol, MODE_POINT);
   double trailPoints = trailDistance / point;
   double stopLevel = MarketInfo(symbol, MODE_STOPLEVEL);
   if(trailPoints < stopLevel) trailPoints = stopLevel;
   
   ApplyTrailingStop(symbol, magic, trailPoints, trailPoints * 0.5);
}

//+------------------------------------------------------------------+
//| Close Partial Volume (e.g. 50% lot size at first target)         |
//+------------------------------------------------------------------+
bool ClosePartial(string symbol, int magic, double closePercent)
{
   if(closePercent <= 0 || closePercent >= 100) return false;
   double step   = MarketInfo(symbol, MODE_LOTSTEP);
   double minLot = MarketInfo(symbol, MODE_MINLOT);
   
   bool closedAny = false;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderSymbol() == symbol && OrderMagicNumber() == magic)
         {
            double closeLots = OrderLots() * (closePercent / 100.0);
            closeLots = MathFloor(closeLots / step) * step;
            
            if(closeLots >= minLot && closeLots < OrderLots())
            {
               double closePrice = (OrderType() == OP_BUY) ? Bid : Ask;
               if(OrderClose(OrderTicket(), closeLots, closePrice, 20, clrGold))
               {
                  PrintFormat("MT4 Order #%d partially closed (%.2f lots of %.2f)", OrderTicket(), closeLots, OrderLots());
                  closedAny = true;
               }
            }
         }
      }
   }
   return closedAny;
}
