"""
High-Impact Economic News Filter & Blackout Gate for GoldTrader.
Guards XAUUSD trading strategies from extreme volatility, spread widening, and slippage
during major US macroeconomic releases (NFP, CPI, FOMC, PPI, Fed Rate Decisions).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import json
from pathlib import Path
from typing import List, Optional, Tuple

from harness.cache import TierZeroCache


class NewsImpact(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EconomicNewsEvent:
    event_id: str
    title: str
    currency: str
    impact: NewsImpact
    scheduled_time: datetime
    forecast: Optional[str] = None
    previous: Optional[str] = None
    actual: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "currency": self.currency,
            "impact": self.impact.value,
            "scheduled_time": self.scheduled_time.isoformat(),
            "forecast": self.forecast,
            "previous": self.previous,
            "actual": self.actual,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EconomicNewsEvent:
        return cls(
            event_id=data["event_id"],
            title=data["title"],
            currency=data["currency"],
            impact=NewsImpact(data["impact"]),
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]),
            forecast=data.get("forecast"),
            previous=data.get("previous"),
            actual=data.get("actual"),
        )


class EconomicNewsFilter:
    """
    Evaluates whether active trading is allowed based on scheduled macroeconomic announcements.
    XAUUSD is strongly sensitive to USD high-impact news releases.
    """

    def __init__(
        self,
        blackout_minutes_before: int = 30,
        blackout_minutes_after: int = 30,
        cache_db_path: Optional[str] = None,
    ):
        self.minutes_before = blackout_minutes_before
        self.minutes_after = blackout_minutes_after
        self.cache = TierZeroCache(cache_db_path) if cache_db_path else None
        self._events: List[EconomicNewsEvent] = []

    def add_event(self, event: EconomicNewsEvent) -> None:
        self._events.append(event)
        self._events.sort(key=lambda e: e.scheduled_time)

    def load_events_from_json(self, json_file: Path) -> int:
        p = Path(json_file)
        if not p.exists():
            return 0
        data = json.loads(p.read_text(encoding="utf-8"))
        count = 0
        for item in data:
            self.add_event(EconomicNewsEvent.from_dict(item))
            count += 1
        return count

    def seed_standard_high_impact_events(self, base_date: Optional[datetime] = None) -> None:
        """
        Seeds standard recurring high-impact US economic events around base_date
        for deterministic evaluation, stress testing, and offline simulation.
        """
        now = base_date or datetime.now(timezone.utc)
        year, month = now.year, now.month

        # Standard US releases (UTC 12:30 or 18:00):
        # 1. Non-Farm Payrolls (First Friday of the month at 12:30 UTC / 8:30 EST)
        first_day = datetime(year, month, 1, 12, 30, tzinfo=timezone.utc)
        first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
        self.add_event(
            EconomicNewsEvent(
                event_id=f"NFP-{year}-{month:02d}",
                title="US Non-Farm Payrolls (NFP)",
                currency="USD",
                impact=NewsImpact.HIGH,
                scheduled_time=first_friday,
                forecast="180K",
                previous="175K",
            )
        )

        # 2. Consumer Price Index (CPI m/m & y/y around 12th of month at 12:30 UTC)
        cpi_date = datetime(year, month, 12, 12, 30, tzinfo=timezone.utc)
        self.add_event(
            EconomicNewsEvent(
                event_id=f"CPI-{year}-{month:02d}",
                title="US Consumer Price Index (CPI m/m)",
                currency="USD",
                impact=NewsImpact.HIGH,
                scheduled_time=cpi_date,
                forecast="0.2%",
                previous="0.3%",
            )
        )

        # 3. FOMC Interest Rate Decision & Statement (around 20th of month at 18:00 UTC)
        fomc_date = datetime(year, month, 20, 18, 0, tzinfo=timezone.utc)
        self.add_event(
            EconomicNewsEvent(
                event_id=f"FOMC-{year}-{month:02d}",
                title="Federal Reserve FOMC Rate Decision & Press Conference",
                currency="USD",
                impact=NewsImpact.HIGH,
                scheduled_time=fomc_date,
                forecast="5.25%",
                previous="5.25%",
            )
        )

    def is_trade_allowed(
        self,
        check_time: Optional[datetime] = None,
        symbol: str = "XAUUSD",
    ) -> Tuple[bool, Optional[str], Optional[EconomicNewsEvent]]:
        """
        Checks if trading is permitted at check_time.
        Returns:
            (allowed: bool, reason: Optional[str], triggered_event: Optional[EconomicNewsEvent])
        """
        t = check_time or datetime.now(timezone.utc)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)

        # XAUUSD is USD-denominated and primarily driven by USD macroeconomic data
        relevant_currencies = {"USD"}
        if "EUR" in symbol.upper():
            relevant_currencies.add("EUR")
        if "GBP" in symbol.upper():
            relevant_currencies.add("GBP")

        for event in self._events:
            if event.impact != NewsImpact.HIGH:
                continue
            if event.currency not in relevant_currencies:
                continue

            event_time = event.scheduled_time
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)

            window_start = event_time - timedelta(minutes=self.minutes_before)
            window_end = event_time + timedelta(minutes=self.minutes_after)

            if window_start <= t <= window_end:
                mins_to_event = int((event_time - t).total_seconds() / 60)
                if mins_to_event > 0:
                    timing_msg = f"{mins_to_event} min before release"
                elif mins_to_event < 0:
                    timing_msg = f"{abs(mins_to_event)} min after release"
                else:
                    timing_msg = "exact release moment"

                reason = (
                    f"BLACKOUT ACTIVE: [{event.currency} {event.impact.value}] '{event.title}' "
                    f"at {event_time.strftime('%Y-%m-%d %H:%M UTC')} ({timing_msg}). "
                    f"Trading paused {self.minutes_before}m before to {self.minutes_after}m after."
                )
                return False, reason, event

        return True, None, None

    def get_upcoming_blackouts(
        self,
        from_time: Optional[datetime] = None,
        hours_ahead: int = 48,
    ) -> List[Tuple[EconomicNewsEvent, datetime, datetime]]:
        """Returns list of (event, window_start, window_end) within horizon."""
        t = from_time or datetime.now(timezone.utc)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        horizon = t + timedelta(hours=hours_ahead)

        results = []
        for event in self._events:
            if event.impact != NewsImpact.HIGH:
                continue
            ev_t = event.scheduled_time
            if ev_t.tzinfo is None:
                ev_t = ev_t.replace(tzinfo=timezone.utc)
            if t <= ev_t <= horizon:
                w_start = ev_t - timedelta(minutes=self.minutes_before)
                w_end = ev_t + timedelta(minutes=self.minutes_after)
                results.append((event, w_start, w_end))
        return results

    def generate_mql_news_header(self) -> str:
        """
        Generates clean MQL4/MQL5 header code (NewsFilter.mqh)
        for compiling into EAs or offline calendar check.
        """
        code_lines = [
            "//+------------------------------------------------------------------+",
            "//|                                                   NewsFilter.mqh |",
            "//|                        GoldTrader Macroeconomic News Blackout Gate |",
            "//+------------------------------------------------------------------+",
            "#property copyright \"GoldTrader Autonomous EA Engine\"",
            "#property strict",
            "",
            "// High impact news blackout configuration",
            "input group \"=== Economic News Filter ===\"",
            f"input bool   InpUseNewsFilter       = true;  // Enable High-Impact News Filter",
            f"input int    InpNewsMinsBefore      = {self.minutes_before};  // Blackout minutes before news",
            f"input int    InpNewsMinsAfter       = {self.minutes_after};  // Blackout minutes after news",
            "",
            "// Structure for scheduled macroeconomic events",
            "struct SEconomicEvent",
            "{",
            "   datetime releaseTime;  // Server release timestamp",
            "   string   currency;     // E.g. 'USD'",
            "   string   title;        // Event description",
            "};",
            "",
            "// Built-in event table for backtesting and offline verification",
            f"static SEconomicEvent g_newsEvents[{max(1, len(self._events))}];",
            "static int            g_newsEventCount = 0;",
            "",
            "void InitNewsSchedule()",
            "{",
            f"   g_newsEventCount = {len(self._events)};",
        ]

        for i, ev in enumerate(self._events):
            dt_str = ev.scheduled_time.strftime("%Y.%m.%d %H:%M")
            code_lines.extend([
                f'   g_newsEvents[{i}].releaseTime = StringToTime("{dt_str}");',
                f'   g_newsEvents[{i}].currency    = "{ev.currency}";',
                f'   g_newsEvents[{i}].title       = "{ev.title}";',
            ])

        code_lines.extend([
            "}",
            "",
            "bool IsNewsBlackoutActive(datetime currentTime)",
            "{",
            "   if(!InpUseNewsFilter || g_newsEventCount == 0)",
            "      return false;",
            "",
            "   for(int i = 0; i < g_newsEventCount; i++)",
            "   {",
            "      datetime evTime = g_newsEvents[i].releaseTime;",
            "      datetime winStart = evTime - (InpNewsMinsBefore * 60);",
            "      datetime winEnd   = evTime + (InpNewsMinsAfter * 60);",
            "",
            "      if(currentTime >= winStart && currentTime <= winEnd)",
            "      {",
            "         PrintFormat(\"⛔ Trade rejected by NewsFilter: %s (Release: %s)\",",
            "                     g_newsEvents[i].title, TimeToString(evTime, TIME_DATE|TIME_MINUTES));",
            "         return true;",
            "      }",
            "   }",
            "   return false;",
            "}",
            "//+------------------------------------------------------------------+",
        ])
        return "\n".join(code_lines) + "\n"
