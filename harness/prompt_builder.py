"""
Prompt on Demand Builder for GoldTrader (JIT Context Assembler).
Constructs minimal, token-optimized, grounded prompts just-in-time for trading agents
(Strategy PM, Quant Architect, MQL4 Developer, MQL5 Developer, Risk Gatekeeper).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional

from harness.schemas import TaskFrame, StrictLevel
from harness.git_diff import GitDeltaExtractor


ROLE_SKILL_MAP: Dict[str, str] = {
    "strategy_pm": ".agents/skills/trading-spec-driven/SKILL.md",
    "quant_architect": ".agents/skills/quant-analyst/SKILL.md",
    "mql4_developer": ".agents/skills/mql4-ea-development/SKILL.md",
    "mql5_developer": ".agents/skills/mql5-ea-development/SKILL.md",
    "risk_gatekeeper": ".agents/skills/risk-manager/SKILL.md",
}


STRUCTURED_OUTPUT_INSTRUCTIONS = """
### 📋 MANDATORY STRUCTURED OUTPUT FORMAT
You MUST respond with a single valid JSON object adhering to this schema:
```json
{
  "action": "complete | pop_task | push_task | request_review | submit_review | fail",
  "status": "completed | in_progress | changes_requested | approved | failed",
  "summary": "Ultra-concise 1 sentence summary (max 250 characters, zero conversational fluff)",
  "artifacts": [
    "experts/mt4/GoldEA.mq4"
  ],
  "subtasks": [
    {
      "task_id": "SUBTASK-xxx",
      "title": "Subtask title",
      "assigned_agent": "strategy_pm | quant_architect | mql4_developer | mql5_developer | risk_gatekeeper",
      "description": "Details",
      "allowed_files": ["experts/mt4/GoldEA.mq4"]
    }
  ],
  "review_feedback": null,
  "metrics": {
    "tokens_estimated": 500,
    "cost_usd": 0.005
  }
}
```
* Note: 'subtasks' is only required when action is 'push_task'.
* 'review_feedback' is required when status is 'changes_requested' (max 1000 characters).
"""


class PromptOnDemandBuilder:
    """Assembles fresh, zero-bloat JIT prompts for agents with Strict Mode constraints."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.delta_extractor = GitDeltaExtractor(str(self.workspace_root))

    def load_skill_template(self, agent_role: str) -> str:
        """Loads persona and guidelines from .agents/skills/<role>/SKILL.md."""
        skill_rel_path = ROLE_SKILL_MAP.get(agent_role)
        if skill_rel_path:
            skill_path = self.workspace_root / skill_rel_path
            if skill_path.exists():
                try:
                    with open(skill_path, "r", encoding="utf-8") as f:
                        return f.read().strip()
                except Exception:
                    pass

        return f"You are {agent_role}, an elite quantitative algorithmic trading engineering agent."

    def build_prompt(
        self,
        task: TaskFrame,
        target_agent: Optional[str] = None,
        extra_instructions: Optional[str] = None,
        include_diff: bool = True,
        strict_level: StrictLevel = StrictLevel.STRICT,
    ) -> str:
        """
        Builds a complete, token-optimized prompt on demand.
        Combines:
        1. Agent Persona/Template
        2. Top of Stack (Current Task)
        3. Strict Mode Constraints (Allowed Files, Atomic Blast Radius, Zero Fluff)
        4. Artifacts Delta (Git diff / snippets)
        5. Anti-hallucination & MQL coding directives
        6. Structured Output Contract
        """
        agent = target_agent or task.assigned_agent
        template = self.load_skill_template(agent)

        prompt_parts: List[str] = []

        # 1. System/Skill Header
        prompt_parts.append(f"# ROLE PROFILE: {agent}")
        prompt_parts.append(template)
        prompt_parts.append("\n---\n")

        # 2. Strict Mode Banner (Opinionated Mode)
        if strict_level in (StrictLevel.STRICT, StrictLevel.HARDCORE):
            is_design_role = agent in ("strategy_pm", "quant_architect")
            rule_two = (
                "2. **Strategy Specification Completeness**: Write fully specified Markdown trading specifications "
                "with exact math formulas ($inline$, $$display$$) and clear entry/exit logic.\n"
                if is_design_role
                else f"2. **Atomic Decomposition**: Keep code changes under {task.max_lines_changed} lines. If task is large, `push_task` smaller subtasks first.\n"
            )
            prompt_parts.append("## 🚨 STRICT / OPINIONATED MODE ACTIVE")
            prompt_parts.append(
                "1. **Hyper-Disciplined Stack Hygiene**: NEVER touch or edit files outside `Allowed Files` below. "
                "The harness runs deterministic boundary checks and will REJECT unauthorized file modifications.\n"
                + rule_two
                + "3. **Mandatory Verification before Pop**: Never claim completion without empirical proof (exit code 0 / syntax linter).\n"
                "4. **Visual & Diagram Protocol**: NEVER use ASCII art / text box tables (+----+). Use Mermaid code blocks or GFM tables.\n"
                "5. **Zero Fluff & Extreme Brevity**: Do not include conversational pleasantries, greetings, or apologies. "
                "Keep `summary` strictly under 250 characters.\n"
            )

        # 3. Top of Stack Focus
        prompt_parts.append("## 🎯 CURRENT TASK (Top of Stack)")
        prompt_parts.append(f"- **Task ID**: {task.task_id}")
        if task.parent_id:
            prompt_parts.append(f"- **Parent Task**: {task.parent_id}")
        prompt_parts.append(f"- **Title**: {task.title}")
        prompt_parts.append(f"- **Current Status**: {task.status.value}")
        prompt_parts.append(f"- **Retry Attempt**: {task.budget.current_retries} / {task.budget.max_retries}")

        if task.allowed_files:
            prompt_parts.append(f"- **🔒 Allowed Files Boundary**: {', '.join(task.allowed_files)} (STRICT: modifications outside this list are forbidden)")
        else:
            prompt_parts.append("- **Allowed Files Boundary**: Any relevant workspace files")

        prompt_parts.append(f"\n### Task Description:\n{task.description}\n")

        # 4. Artifacts & Git Unified Diff
        if task.artifacts:
            prompt_parts.append("### 📦 Associated Artifacts:")
            for art in task.artifacts:
                prompt_parts.append(f"- `{art}`")

            if include_diff:
                diff_content = self.delta_extractor.get_diff(task.artifacts)
                if diff_content:
                    prompt_parts.append("\n### 🔍 Git Delta (Unified Diff):")
                    prompt_parts.append(f"```diff\n{diff_content}\n```")
                else:
                    prompt_parts.append("\n### 📄 File Snippets:")
                    for art in task.artifacts[:2]:
                        snippet = self.delta_extractor.get_file_content_snippet(art, max_lines=60)
                        prompt_parts.append(f"**{art}:**\n```\n{snippet}\n```")

        # 5. Extra instructions / Feedback
        if extra_instructions:
            prompt_parts.append(f"\n### ⚠️ Notice / Specific Directives:\n{extra_instructions}\n")

        # 6. Anti-Hallucination, MQL Quality & Token Optimization Directives
        prompt_parts.append("\n## 🛡️ EXECUTION DIRECTIVES (Zero-Test & MQL Precision)")
        prompt_parts.append(
            "- **MQL Operator Precedence**: ALWAYS use explicit parentheses `()` when combining logical operators `&&` and `||`.\n"
            "- **No Phantom APIs**: Verify built-in functions. In MT4 use `OrderSend/OrderClose/OrderSelect`; in MT5 use `CTrade/CopyBuffer`.\n"
            "- **Risk Invariant**: Every EA MUST feature Stop Loss and Spread checks to protect against Gold flash crashes.\n"
            "- **Zero-Test by Default**: DO NOT write or execute unit tests unless the task explicitly requested them.\n"
            "- **Deterministic Verification**: Verify code with static linter (exit code 0).\n"
        )

        # 7. Structured Output Contract
        prompt_parts.append(STRUCTURED_OUTPUT_INSTRUCTIONS)

        return "\n".join(prompt_parts)
