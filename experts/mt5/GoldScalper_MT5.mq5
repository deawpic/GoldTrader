//+------------------------------------------------------------------+
//|                                             GoldScalper_MT5.mq5  |
//|                                  Copyright 2026, GoldTrader Quant|
//+------------------------------------------------------------------+
#property copyright "GoldTrader Quant Engine"
#property link      "https://github.com/GoldTrader"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>
#include "..\..\include\mt5\TradeHelper_MT5.mqh"

//--- Input Parameters
input group "=== Strategy Parameters ==="
input int      InpFastEMAPeriod     = 20;        // Fast EMA Period
input int      InpSlowEMAPeriod     = 50;        // Slow EMA Period
input int      InpRSIPeriod         = 14;        // RSI Period
input double   InpRSIOverbought     = 70.0;      // RSI Overbought Level
input double   InpRSIOversold       = 30.0;      // RSI Oversold Level

input group "=== Risk & Order Management ==="
input double   InpRiskPercent       = 1.0;       // Risk Per Trade (% of Equity)
input double   InpStopLossPoints    = 150.0;     // Stop Loss (Points)
input double   InpTakeProfitPoints  = 300.0;     // Take Profit (Points)
input int      InpSlippagePoints    = 25;        // Max Slippage / Deviation
input int      InpMaxSpreadPoints   = 40;        // Max Spread Allowed (Points)
input ulong    InpMagicNumber       = 108855;    // EA Magic Number
input string   InpTradeComment      = "GoldScalp_MT5";

input group "=== Trailing & Breakeven ==="
input bool     InpUseBreakeven      = true;      // Use Breakeven Protection
input double   InpBreakevenTrigger  = 100.0;     // Profit Points to Trigger Breakeven
input double   InpBreakevenLock     = 10.0;      // Profit Points to Lock
input bool     InpUseATRTrailing    = true;      // Use ATR Trailing Stop
input int      InpATRPeriod         = 14;        // ATR Period for Trailing Stop
input double   InpATRMultiplier     = 1.5;       // ATR Multiplier

//--- Global Objects
CTrade         trade;
CPositionInfo  posInfo;
CSymbolInfo    symInfo;

//--- Indicator Handles
int            handleFastEMA        = INVALID_HANDLE;
int            handleSlowEMA        = INVALID_HANDLE;
int            handleRSI            = INVALID_HANDLE;
int            handleATR            = INVALID_HANDLE;

datetime       g_lastBarTime        = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!symInfo.Name(_Symbol))
   {
      Print("Failed to initialize CSymbolInfo for ", _Symbol);
      return(INIT_FAILED);
   }
   symInfo.Refresh();

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   // Create Indicators
   handleFastEMA = iMA(_Symbol, _Period, InpFastEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   handleSlowEMA = iMA(_Symbol, _Period, InpSlowEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   handleRSI     = iRSI(_Symbol, _Period, InpRSIPeriod, PRICE_CLOSE);
   handleATR     = iATR(_Symbol, _Period, InpATRPeriod);

   if(handleFastEMA == INVALID_HANDLE || handleSlowEMA == INVALID_HANDLE || handleRSI == INVALID_HANDLE || handleATR == INVALID_HANDLE)
   {
      Print("Error creating indicator handles in OnInit()");
      return(INIT_FAILED);
   }

   PrintFormat("GoldScalper_MT5 Initialized on %s. MagicNumber: %d", _Symbol, InpMagicNumber);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Mandatory resource deallocation in MT5
   if(handleFastEMA != INVALID_HANDLE) IndicatorRelease(handleFastEMA);
   if(handleSlowEMA != INVALID_HANDLE) IndicatorRelease(handleSlowEMA);
   if(handleRSI != INVALID_HANDLE)     IndicatorRelease(handleRSI);
   if(handleATR != INVALID_HANDLE)     IndicatorRelease(handleATR);
   Comment("");
}

//+------------------------------------------------------------------+
//| Count active positions for this EA in MT5                        |
//+------------------------------------------------------------------+
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
   return(count);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) return;

   // 1. Dynamic Spread Check
   if(!CTradeHelper::IsSpreadAcceptable(symInfo, InpMaxSpreadPoints))
   {
      Comment(StringFormat("Spread high: %d pts > max %d pts", symInfo.Spread(), InpMaxSpreadPoints));
      return;
   }

   // 2. Active Trade Maintenance (Breakeven & Trailing Stops)
   if(InpUseBreakeven)
   {
      CTradeHelper::ApplyBreakeven(trade, posInfo, symInfo, InpMagicNumber, InpBreakevenTrigger, InpBreakevenLock);
   }
   if(InpUseATRTrailing)
   {
      CTradeHelper::ApplyATRTrailingStop(trade, posInfo, symInfo, InpMagicNumber, handleATR, InpATRMultiplier);
   }

   // 3. Bar Filter (Only trade once per new bar)
   datetime currentBarTime[];
   ArraySetAsSeries(currentBarTime, true);
   if(CopyTime(_Symbol, _Period, 0, 1, currentBarTime) <= 0) return;

   if(currentBarTime[0] == g_lastBarTime) return;

   // 3. Read Indicator Buffers into dynamic arrays
   double fastEMA[], slowEMA[], rsi[];
   ArraySetAsSeries(fastEMA, true);
   ArraySetAsSeries(slowEMA, true);
   ArraySetAsSeries(rsi, true);

   if(CopyBuffer(handleFastEMA, 0, 1, 2, fastEMA) < 2) return;
   if(CopyBuffer(handleSlowEMA, 0, 1, 2, slowEMA) < 2) return;
   if(CopyBuffer(handleRSI, 0, 1, 2, rsi) < 2)         return;

   // 4. Strict Logical Parenthesization
   bool isBullishTrend = (fastEMA[0] > slowEMA[0]);
   bool isBearishTrend = (fastEMA[0] < slowEMA[0]);
   bool rsiCrossUp     = ((rsi[1] <= InpRSIOversold) && (rsi[0] > InpRSIOversold));
   bool rsiCrossDown   = ((rsi[1] >= InpRSIOverbought) && (rsi[0] < InpRSIOverbought));

   int buyPositions  = CountOpenPositions(POSITION_TYPE_BUY);
   int sellPositions = CountOpenPositions(POSITION_TYPE_SELL);

   symInfo.RefreshRates();

   // Buy Entry
   if((isBullishTrend && rsiCrossUp) && (buyPositions == 0))
   {
      double lot = CTradeHelper::CalculateRiskLotSize(symInfo, InpRiskPercent, InpStopLossPoints);
      double ask = symInfo.Ask();
      double sl  = (InpStopLossPoints > 0) ? ask - (InpStopLossPoints * symInfo.Point()) : 0.0;
      double tp  = (InpTakeProfitPoints > 0) ? ask + (InpTakeProfitPoints * symInfo.Point()) : 0.0;

      if(trade.Buy(lot, _Symbol, ask, sl, tp, InpTradeComment))
      {
         g_lastBarTime = currentBarTime[0];
         PrintFormat("MT5 Buy order opened at %f, lot: %f", ask, lot);
      }
      else
      {
         PrintFormat("MT5 Buy order failed. RetCode: %d, Description: %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
      }
   }
   // Sell Entry
   else if((isBearishTrend && rsiCrossDown) && (sellPositions == 0))
   {
      double lot = CTradeHelper::CalculateRiskLotSize(symInfo, InpRiskPercent, InpStopLossPoints);
      double bid = symInfo.Bid();
      double sl  = (InpStopLossPoints > 0) ? bid + (InpStopLossPoints * symInfo.Point()) : 0.0;
      double tp  = (InpTakeProfitPoints > 0) ? bid - (InpTakeProfitPoints * symInfo.Point()) : 0.0;

      if(trade.Sell(lot, _Symbol, bid, sl, tp, InpTradeComment))
      {
         g_lastBarTime = currentBarTime[0];
         PrintFormat("MT5 Sell order opened at %f, lot: %f", bid, lot);
      }
      else
      {
         PrintFormat("MT5 Sell order failed. RetCode: %d, Description: %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
      }
   }
}
