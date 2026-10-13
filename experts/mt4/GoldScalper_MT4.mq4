//+------------------------------------------------------------------+
//|                                             GoldScalper_MT4.mq4  |
//|                                  Copyright 2026, GoldTrader Quant|
//+------------------------------------------------------------------+
#property copyright "GoldTrader Quant Engine"
#property link      "https://github.com/GoldTrader"
#property version   "1.00"
#property strict

#include <..\include\mt4\TradeHelper_MT4.mqh>

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
input int      InpSlippage          = 25;        // Max Slippage (Points)
input int      InpMaxSpreadPoints   = 40;        // Max Spread Allowed (Points)
input int      InpMagicNumber       = 108844;    // EA Magic Number
input string   InpTradeComment      = "GoldScalp_MT4";

//--- Global Variables
datetime g_lastBarTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   PrintFormat("GoldScalper_MT4 Initialized on %s. MagicNumber: %d", Symbol(), InpMagicNumber);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Comment("");
}

//+------------------------------------------------------------------+
//| Count active positions for this EA (Backwards loop rule)         |
//+------------------------------------------------------------------+
int CountOpenPositions(int orderType)
{
   int count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
      {
         if(OrderSymbol() == Symbol() && OrderMagicNumber() == InpMagicNumber)
         {
            if(OrderType() == orderType)
               count++;
         }
      }
   }
   return(count);
}

//+------------------------------------------------------------------+
//| Send order with retry logic and error logging                   |
//+------------------------------------------------------------------+
int SendOrderSafe(int orderType, double lot, double slPoints, double tpPoints)
{
   double price = (orderType == OP_BUY) ? Ask : Bid;
   double point = Point;
   
   double sl = 0.0;
   double tp = 0.0;
   
   if(orderType == OP_BUY)
   {
      if(slPoints > 0) sl = price - (slPoints * point);
      if(tpPoints > 0) tp = price + (tpPoints * point);
   }
   else if(orderType == OP_SELL)
   {
      if(slPoints > 0) sl = price + (slPoints * point);
      if(tpPoints > 0) tp = price - (tpPoints * point);
   }
   
   int ticket = -1;
   int maxAttempts = 3;
   
   for(int attempt = 1; attempt <= maxAttempts; attempt++)
   {
      RefreshRates();
      price = (orderType == OP_BUY) ? Ask : Bid;
      
      ticket = OrderSend(Symbol(), orderType, lot, price, InpSlippage, sl, tp, InpTradeComment, InpMagicNumber, 0, (orderType == OP_BUY ? clrGreen : clrRed));
      
      if(ticket > 0)
      {
         PrintFormat("Order #%d executed successfully at price %f", ticket, price);
         return(ticket);
      }
      
      int err = GetLastError();
      PrintFormat("OrderSend attempt %d failed with error %d: %s", attempt, err, ErrorDescription(err));
      
      if(err == 130 || err == 134) // ERR_INVALID_STOPS or ERR_NOT_ENOUGH_MONEY
         break;
         
      Sleep(250);
   }
   
   return(-1);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!IsTradeAllowed() || !IsConnected()) return;
   
   // 1. Dynamic Spread Filter
   if(!IsSpreadAcceptable(Symbol(), InpMaxSpreadPoints))
   {
      Comment(StringFormat("Spread high: %f pts > max %d pts", MarketInfo(Symbol(), MODE_SPREAD), InpMaxSpreadPoints));
      return;
   }
   
   // 2. Bar Filter (Prevent multiple orders on same bar)
   if(Time[0] == g_lastBarTime) return;
   
   // 3. Indicator Calculation on closed bar 1 (No repainting)
   double fastEMA_1 = iMA(Symbol(), Period(), InpFastEMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);
   double slowEMA_1 = iMA(Symbol(), Period(), InpSlowEMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 1);
   double rsi_1     = iRSI(Symbol(), Period(), InpRSIPeriod, PRICE_CLOSE, 1);
   double rsi_2     = iRSI(Symbol(), Period(), InpRSIPeriod, PRICE_CLOSE, 2);
   
   // 4. Strict Logical Parenthesization
   bool isBullishTrend = (fastEMA_1 > slowEMA_1);
   bool isBearishTrend = (fastEMA_1 < slowEMA_1);
   bool rsiCrossUp     = ((rsi_2 <= InpRSIOversold) && (rsi_1 > InpRSIOversold));
   bool rsiCrossDown   = ((rsi_2 >= InpRSIOverbought) && (rsi_1 < InpRSIOverbought));
   
   int buyPositions  = CountOpenPositions(OP_BUY);
   int sellPositions = CountOpenPositions(OP_SELL);
   
   // Buy Signal Entry
   if((isBullishTrend && rsiCrossUp) && (buyPositions == 0))
   {
      double lot = CalculateRiskLotSize(Symbol(), InpRiskPercent, InpStopLossPoints);
      int ticket = SendOrderSafe(OP_BUY, lot, InpStopLossPoints, InpTakeProfitPoints);
      if(ticket > 0)
      {
         g_lastBarTime = Time[0];
      }
   }
   // Sell Signal Entry
   else if((isBearishTrend && rsiCrossDown) && (sellPositions == 0))
   {
      double lot = CalculateRiskLotSize(Symbol(), InpRiskPercent, InpStopLossPoints);
      int ticket = SendOrderSafe(OP_SELL, lot, InpStopLossPoints, InpTakeProfitPoints);
      if(ticket > 0)
      {
         g_lastBarTime = Time[0];
      }
   }
}
