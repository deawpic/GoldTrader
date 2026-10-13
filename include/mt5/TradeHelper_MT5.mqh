//+------------------------------------------------------------------+
//|                                              TradeHelper_MT5.mqh |
//|                                  Copyright 2026, GoldTrader Quant|
//+------------------------------------------------------------------+
#property copyright "GoldTrader Quant Engine"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

class CTradeHelper
{
public:
   //+------------------------------------------------------------------+
   //| Calculate pip value in price units                               |
   //+------------------------------------------------------------------+
   static double GetPipPoint(CSymbolInfo &o_sym)
   {
      if(o_sym.Digits() == 3 || o_sym.Digits() == 5)
         return(o_sym.Point() * 10.0);
      return(o_sym.Point());
   }

   //+------------------------------------------------------------------+
   //| Calculate lot size based on equity risk percentage and SL points |
   //+------------------------------------------------------------------+
   static double CalculateRiskLotSize(CSymbolInfo &o_sym, double riskPercent, double slPoints)
   {
      if(slPoints <= 0) return(o_sym.LotsMin());

      double equity    = AccountInfoDouble(ACCOUNT_EQUITY);
      double riskMoney = equity * (riskPercent / 100.0);
      double tickValue = o_sym.TickValue();
      double tickSize  = o_sym.TickSize();
      double point     = o_sym.Point();

      if(tickSize <= 0) tickSize = point;

      double ticksAtRisk = slPoints * (point / tickSize);
      double moneyPerLotAtRisk = ticksAtRisk * tickValue;

      if(moneyPerLotAtRisk <= 0) return(o_sym.LotsMin());

      double calculatedLot = riskMoney / moneyPerLotAtRisk;
      double step   = o_sym.LotsStep();
      double minLot = o_sym.LotsMin();
      double maxLot = o_sym.LotsMax();

      calculatedLot = MathFloor(calculatedLot / step) * step;

      if(calculatedLot < minLot) calculatedLot = minLot;
      if(calculatedLot > maxLot) calculatedLot = maxLot;

      return(calculatedLot);
   }

   //+------------------------------------------------------------------+
   //| Check if spread is acceptable                                    |
   //+------------------------------------------------------------------+
   static bool IsSpreadAcceptable(CSymbolInfo &o_sym, int maxSpreadPoints)
   {
      o_sym.RefreshRates();
      return(o_sym.Spread() <= maxSpreadPoints);
   }

   //+------------------------------------------------------------------+
   //| Apply Breakeven Protection in MT5                                |
   //+------------------------------------------------------------------+
   static void ApplyBreakeven(
      CTrade &o_trade,
      CPositionInfo &o_posInfo,
      CSymbolInfo &o_sym,
      ulong magic,
      double triggerPoints,
      double lockPoints
   )
   {
      o_sym.RefreshRates();
      double point = o_sym.Point();

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(o_posInfo.SelectByIndex(i))
         {
            if(o_posInfo.Symbol() == o_sym.Name() && o_posInfo.Magic() == magic)
            {
               if(o_posInfo.PositionType() == POSITION_TYPE_BUY)
               {
                  double profitPoints = (o_sym.Bid() - o_posInfo.PriceOpen()) / point;
                  double targetSL     = o_posInfo.PriceOpen() + (lockPoints * point);

                  if(profitPoints >= triggerPoints && (o_posInfo.StopLoss() < targetSL || o_posInfo.StopLoss() == 0))
                  {
                     o_trade.PositionModify(o_posInfo.Ticket(), targetSL, o_posInfo.TakeProfit());
                     PrintFormat("MT5 Buy #%d moved to Breakeven (+%.1f pts)", o_posInfo.Ticket(), lockPoints);
                  }
               }
               else if(o_posInfo.PositionType() == POSITION_TYPE_SELL)
               {
                  double profitPoints = (o_posInfo.PriceOpen() - o_sym.Ask()) / point;
                  double targetSL     = o_posInfo.PriceOpen() - (lockPoints * point);

                  if(profitPoints >= triggerPoints && (o_posInfo.StopLoss() > targetSL || o_posInfo.StopLoss() == 0))
                  {
                     o_trade.PositionModify(o_posInfo.Ticket(), targetSL, o_posInfo.TakeProfit());
                     PrintFormat("MT5 Sell #%d moved to Breakeven (+%.1f pts)", o_posInfo.Ticket(), lockPoints);
                  }
               }
            }
         }
      }
   }

   //+------------------------------------------------------------------+
   //| Apply Trailing Stop in MT5                                       |
   //+------------------------------------------------------------------+
   static void ApplyTrailingStop(
      CTrade &o_trade,
      CPositionInfo &o_posInfo,
      CSymbolInfo &o_sym,
      ulong magic,
      double trailPoints,
      double minProfitPoints
   )
   {
      if(trailPoints <= 0) return;
      o_sym.RefreshRates();
      double point = o_sym.Point();
      long stopLevel = o_sym.StopsLevel();
      if(trailPoints < (double)stopLevel) trailPoints = (double)stopLevel;

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(o_posInfo.SelectByIndex(i))
         {
            if(o_posInfo.Symbol() == o_sym.Name() && o_posInfo.Magic() == magic)
            {
               if(o_posInfo.PositionType() == POSITION_TYPE_BUY)
               {
                  double profitPoints = (o_sym.Bid() - o_posInfo.PriceOpen()) / point;
                  if(profitPoints >= minProfitPoints)
                  {
                     double targetSL = o_sym.Bid() - (trailPoints * point);
                     if(targetSL > o_posInfo.StopLoss() + (5.0 * point))
                     {
                        o_trade.PositionModify(o_posInfo.Ticket(), targetSL, o_posInfo.TakeProfit());
                     }
                  }
               }
               else if(o_posInfo.PositionType() == POSITION_TYPE_SELL)
               {
                  double profitPoints = (o_posInfo.PriceOpen() - o_sym.Ask()) / point;
                  if(profitPoints >= minProfitPoints)
                  {
                     double targetSL = o_sym.Ask() + (trailPoints * point);
                     if(o_posInfo.StopLoss() == 0 || targetSL < o_posInfo.StopLoss() - (5.0 * point))
                     {
                        o_trade.PositionModify(o_posInfo.Ticket(), targetSL, o_posInfo.TakeProfit());
                     }
                  }
               }
            }
         }
      }
   }

   //+------------------------------------------------------------------+
   //| Apply ATR-Based Volatility Trailing Stop in MT5                  |
   //+------------------------------------------------------------------+
   static void ApplyATRTrailingStop(
      CTrade &o_trade,
      CPositionInfo &o_posInfo,
      CSymbolInfo &o_sym,
      ulong magic,
      int atrHandle,
      double atrMultiplier
   )
   {
      if(atrHandle == INVALID_HANDLE) return;

      double atrBuf[];
      ArraySetAsSeries(atrBuf, true);
      if(CopyBuffer(atrHandle, 0, 1, 1, atrBuf) <= 0) return;

      double atrValue = atrBuf[0];
      if(atrValue <= 0) return;

      double trailDistance = atrValue * atrMultiplier;
      double trailPoints   = trailDistance / o_sym.Point();
      long stopLevel = o_sym.StopsLevel();
      if(trailPoints < (double)stopLevel) trailPoints = (double)stopLevel;

      ApplyTrailingStop(o_trade, o_posInfo, o_sym, magic, trailPoints, trailPoints * 0.5);
   }

   //+------------------------------------------------------------------+
   //| Close Partial Volume in MT5                                      |
   //+------------------------------------------------------------------+
   static bool ClosePartial(
      CTrade &o_trade,
      CPositionInfo &o_posInfo,
      CSymbolInfo &o_sym,
      ulong magic,
      double closePercent
   )
   {
      if(closePercent <= 0 || closePercent >= 100) return false;
      bool closedAny = false;

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(o_posInfo.SelectByIndex(i))
         {
            if(o_posInfo.Symbol() == o_sym.Name() && o_posInfo.Magic() == magic)
            {
               double closeLots = o_posInfo.Volume() * (closePercent / 100.0);
               closeLots = MathFloor(closeLots / o_sym.LotsStep()) * o_sym.LotsStep();

               if(closeLots >= o_sym.LotsMin() && closeLots < o_posInfo.Volume())
               {
                  if(o_trade.PositionClosePartial(o_posInfo.Ticket(), closeLots))
                  {
                     PrintFormat("MT5 Position #%d partially closed (%.2f lots of %.2f)", o_posInfo.Ticket(), closeLots, o_posInfo.Volume());
                     closedAny = true;
                  }
               }
            }
         }
      }
      return closedAny;
   }
};
