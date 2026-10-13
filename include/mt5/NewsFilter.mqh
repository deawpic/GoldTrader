//+------------------------------------------------------------------+
//|                                                   NewsFilter.mqh |
//|                        GoldTrader Macroeconomic News Blackout Gate |
//+------------------------------------------------------------------+
#property copyright "GoldTrader Autonomous EA Engine"
#property strict

// High impact news blackout configuration
input group "=== Economic News Filter ==="
input bool   InpUseNewsFilter       = true;  // Enable High-Impact News Filter
input int    InpNewsMinsBefore      = 30;  // Blackout minutes before news
input int    InpNewsMinsAfter       = 30;  // Blackout minutes after news

// Structure for scheduled macroeconomic events
struct SEconomicEvent
{
   datetime releaseTime;  // Server release timestamp
   string   currency;     // E.g. 'USD'
   string   title;        // Event description
};

// Built-in event table for backtesting and offline verification
static SEconomicEvent g_newsEvents[3];
static int            g_newsEventCount = 0;

void InitNewsSchedule()
{
   g_newsEventCount = 3;
   g_newsEvents[0].releaseTime = StringToTime("2026.10.02 12:30");
   g_newsEvents[0].currency    = "USD";
   g_newsEvents[0].title       = "US Non-Farm Payrolls (NFP)";
   g_newsEvents[1].releaseTime = StringToTime("2026.10.12 12:30");
   g_newsEvents[1].currency    = "USD";
   g_newsEvents[1].title       = "US Consumer Price Index (CPI m/m)";
   g_newsEvents[2].releaseTime = StringToTime("2026.10.20 18:00");
   g_newsEvents[2].currency    = "USD";
   g_newsEvents[2].title       = "Federal Reserve FOMC Rate Decision & Press Conference";
}

bool IsNewsBlackoutActive(datetime currentTime)
{
   if(!InpUseNewsFilter || g_newsEventCount == 0)
      return false;

   for(int i = 0; i < g_newsEventCount; i++)
   {
      datetime evTime = g_newsEvents[i].releaseTime;
      datetime winStart = evTime - (InpNewsMinsBefore * 60);
      datetime winEnd   = evTime + (InpNewsMinsAfter * 60);

      if(currentTime >= winStart && currentTime <= winEnd)
      {
         PrintFormat("⛔ Trade rejected by NewsFilter: %s (Release: %s)",
                     g_newsEvents[i].title, TimeToString(evTime, TIME_DATE|TIME_MINUTES));
         return true;
      }
   }
   return false;
}
//+------------------------------------------------------------------+
