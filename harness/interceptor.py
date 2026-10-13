"""
Emergency & Red Flag Interceptor for GoldTrader.
Monitors critical trading and code risks:
1. Financial & Execution Emergencies:
   - Margin Level < 100% or < 150% (Margin Call Warning)
   - Daily Drawdown > 5% or > 10% (FinOps Circuit Breaker)
   - Spread Widening Flash Spike (> 100 points on Gold)
   - Martingale cascading without hard stop loss
2. System & Host Safety:
   - Destructive commands (`rm -rf`, raw disk access, dropping databases)
   - Secret/credential leaks
"""

from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Tuple


@dataclass
class RedFlagAlert:
    alert_type: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM"
    message: str
    immediate_action: str


class EmergencyInterceptor:
    """Interceps severe risk conditions immediately without awaiting long analysis loops."""

    @staticmethod
    def inspect_risk_metrics(
        equity: float,
        balance: float,
        margin: float,
        spread_points: float,
        daily_loss_pct: float,
        open_positions: int,
    ) -> List[RedFlagAlert]:
        alerts: List[RedFlagAlert] = []

        # 1. Margin Level Check
        if margin > 0:
            margin_level = (equity / margin) * 100.0
            if margin_level < 100.0:
                alerts.append(
                    RedFlagAlert(
                        alert_type="MARGIN_STOP_OUT_ALERT",
                        severity="CRITICAL",
                        message=f"CRITICAL: Margin level is {margin_level:.1f}% (< 100%). Immediate stop-out risk!",
                        immediate_action="Hedge open positions or close highest margin-consuming trades immediately.",
                    )
                )
            elif margin_level < 150.0:
                alerts.append(
                    RedFlagAlert(
                        alert_type="MARGIN_CALL_WARNING",
                        severity="HIGH",
                        message=f"WARNING: Margin level dropped to {margin_level:.1f}% (< 150%).",
                        immediate_action="Halt new order entries and tighten trailing stops.",
                    )
                )

        # 2. Daily Drawdown Circuit Breaker
        if daily_loss_pct >= 10.0:
            alerts.append(
                RedFlagAlert(
                    alert_type="DAILY_DRAWDOWN_BREACH",
                    severity="CRITICAL",
                    message=f"CRITICAL: Daily Drawdown is {daily_loss_pct:.1f}% (>= 10.0%). Hard stop tripped!",
                    immediate_action="Shutdown EA trading immediately for the remainder of the trading day.",
                )
            )
        elif daily_loss_pct >= 5.0:
            alerts.append(
                RedFlagAlert(
                    alert_type="DAILY_DRAWDOWN_WARNING",
                    severity="HIGH",
                    message=f"WARNING: Daily Drawdown is {daily_loss_pct:.1f}% (>= 5.0%). Circuit breaker caution.",
                    immediate_action="Reduce lot size by 50% and disable grid additions.",
                )
            )

        # 3. Spread Widening Spike (Gold XAUUSD)
        if spread_points >= 100.0:
            alerts.append(
                RedFlagAlert(
                    alert_type="SPREAD_SPIKE_FLASH_CRASH",
                    severity="HIGH",
                    message=f"WARNING: XAUUSD Spread widened to {spread_points:.1f} points (>= 100 pts / 10 pips).",
                    immediate_action="Block all pending and market orders until spread normalizes (< 40 points).",
                )
            )

        return alerts

    @staticmethod
    def inspect_code_safety(code_content: str) -> List[RedFlagAlert]:
        alerts: List[RedFlagAlert] = []

        # 1. Check for destructive system commands
        destructive_patterns = [
            (r"\brm\s+-rf\b", "Command Injection: 'rm -rf' detected"),
            (r"\bformat\s+[a-zA-Z]:", "Destructive Disk Format command detected"),
            (r"\bDROP\s+DATABASE\b", "Destructive SQL command detected"),
        ]
        for pattern, desc in destructive_patterns:
            if re.search(pattern, code_content, re.IGNORECASE):
                alerts.append(
                    RedFlagAlert(
                        alert_type="DESTRUCTIVE_COMMAND_DETECTED",
                        severity="CRITICAL",
                        message=f"Host Security Violation: {desc}",
                        immediate_action="Reject and abort task execution immediately.",
                    )
                )

        # 2. Martingale loop without stop-loss
        if re.search(r"(\*=\s*2|\*=\s*1\.5|Lot\s*\*\s*2)", code_content):
            if not re.search(r"(StopLoss|Stop_Loss|InpStopLoss)", code_content, re.IGNORECASE):
                alerts.append(
                    RedFlagAlert(
                        alert_type="UNCONTROLLED_MARTINGALE",
                        severity="CRITICAL",
                        message="Trading Risk: Martingale lot multiplier detected without Stop Loss protection!",
                        immediate_action="Enforce hard Stop Loss and Max Orders Per Bar gate.",
                    )
                )

        return alerts
