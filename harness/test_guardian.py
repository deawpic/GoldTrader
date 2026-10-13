"""
Strict Token Optimization & Test Control Guardian for GoldTrader.
Synthesized from Production Harness Master Standards (MedMate & thlawdeka).
Enforces:
1. Strict Zero-Test Policy by default (Implementation-Only Mode).
2. Explicit Opt-In Trigger checking.
3. Log suppression flags for minimal token waste.
4. Maximum 2 auto-fix attempts limit.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple


TEST_OPT_IN_TRIGGERS: List[str] = [
    "write test",
    "unit test",
    "test this",
    "run tests",
    "generate test suite",
    "เขียนเทส",
    "รันเทส",
]


class TestPolicyGuardian:
    """Enforces Zero-Test by Default and token-optimized testing guardrails."""

    @staticmethod
    def is_testing_mode_activated(prompt: str) -> bool:
        """Checks if prompt contains explicit opt-in trigger keywords."""
        prompt_lower = prompt.lower()
        for trigger in TEST_OPT_IN_TRIGGERS:
            if trigger in prompt_lower:
                return True
        return False

    @staticmethod
    def get_log_suppression_cmd(platform: str, target_path: str) -> List[str]:
        """Returns command with log suppression flags."""
        if platform == "python":
            return ["pytest", target_path, "-q", "--tb=short", "--maxfail=1"]
        elif platform in ("node", "typescript"):
            return ["npx", "vitest", "run", target_path, "--reporter=compact"]
        return [target_path]

    @staticmethod
    def check_auto_fix_limit(current_attempts: int, max_attempts: int = 2) -> Tuple[bool, str]:
        """Enforces hard stop on auto-fix loops."""
        if current_attempts >= max_attempts:
            return False, (
                f"STOP IMMEDIATELY: Maximum auto-fix attempts ({max_attempts}) reached. "
                "Reverting broken changes and escalating to user direction."
            )
        return True, f"Auto-fix attempt {current_attempts + 1} of {max_attempts}."
