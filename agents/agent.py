"""LLM-based coding agent for Saotri Bench."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import ModelConfig
from .llm_client import OpenRouterClient


SYSTEM_PROMPT = """\
You are a Python coding agent solving programming tasks.
You will be given a problem description and must write a Python function that satisfies all requirements.

RULES:
1. Output ONLY the Python function code inside a ```python block.
2. Do NOT include any test code, print statements, or example usage.
3. Do NOT use imports unless explicitly told they are allowed.
4. The function signature MUST match exactly what is specified.
5. Pay very close attention to the feedback — it tells you exactly which rules/scopes are failing.
6. When you see a phase transition with new rules, adapt your solution to handle them.
7. Think step by step about what each violation scope means and fix accordingly.
"""


@dataclass
class AgentAttempt:
    """Record of a single agent attempt."""

    phase_id: int
    attempt_id: int
    code: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_seconds: float = 0.0


class CodingAgent:
    """LLM agent that reads workspace files and generates solutions."""

    def __init__(
        self,
        model: ModelConfig,
        client: OpenRouterClient,
        workspace_dir: Path,
    ):
        self.model = model
        self.client = client
        self.workspace_dir = Path(workspace_dir)
        self.attempts: list[AgentAttempt] = []
        self.conversation_history: list[dict[str, str]] = []

    def _read_file(self, filename: str) -> str:
        """Read a workspace file, return empty string if missing."""
        path = self.workspace_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _read_json(self, filename: str) -> dict[str, Any]:
        """Read a JSON workspace file."""
        content = self._read_file(filename)
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    def _build_initial_prompt(self) -> str:
        """Build the initial prompt from workspace files."""
        problem = self._read_file("problem.md")
        task_info = self._read_json("task.json")
        phase_info = self._read_json("phase.json")

        interface = task_info.get("interface", {})
        signature = interface.get("signature", "")
        allowed_imports = interface.get("allowed_imports", [])

        rules = phase_info.get("rules", [])
        rules_text = "\n".join(
            f"  - {r['id']}: {r['description']}" for r in rules
        )

        prompt = f"""## Problem
{problem}

## Function Signature
{signature}

## Allowed Imports
{', '.join(allowed_imports) if allowed_imports else 'None'}

## Current Phase: {phase_info.get('phase_id', 0)}
## Rules to satisfy:
{rules_text}

Write the complete function implementation. Output ONLY the code in a ```python block.
"""
        return prompt

    def _build_refinement_prompt(self, feedback: dict[str, Any]) -> str:
        """Build a refinement prompt from feedback."""
        status = feedback.get("status", "unknown")
        status_reason = feedback.get("status_reason", "")
        violations = feedback.get("violations", [])
        summary = feedback.get("summary", {})
        coverage = summary.get("coverage", 0)
        error = feedback.get("error")

        # Read current phase info (may have changed due to phase transition)
        phase_info = self._read_json("phase.json")
        phase_transition = phase_info.get("phase_transition", False)
        rules = phase_info.get("rules", [])

        parts = []

        if phase_transition:
            parts.append("## PHASE TRANSITION — New rules have been added!")
            implicit_eval = phase_info.get("implicit_evaluation")
            if implicit_eval:
                impl_violations = implicit_eval.get("violations", [])
                if impl_violations:
                    parts.append("Your current solution has these issues in the new phase:")
                    for v in impl_violations:
                        parts.append(f"  - Rule '{v['rule_id']}' failed on scope '{v['scope']}' ({v['count']} times)")

        parts.append(f"\n## Evaluation Result: {status}")
        parts.append(f"Reason: {status_reason}")
        parts.append(f"Coverage: {coverage:.1%}")

        if error:
            parts.append(f"\n## ERROR: {error.get('type', 'Unknown')}")
            parts.append(f"Message: {error.get('message', '')}")

        if violations:
            parts.append("\n## Violations:")
            for v in violations:
                parts.append(f"  - Rule '{v['rule_id']}' failed on scope '{v['scope']}' ({v['count']} times)")

        rules_text = "\n".join(f"  - {r['id']}: {r['description']}" for r in rules)
        parts.append(f"\n## Current rules to satisfy:\n{rules_text}")

        parts.append(
            "\nAnalyze the violations carefully. Think about what each scope name implies. "
            "Fix ALL issues and output the COMPLETE updated function in a ```python block."
        )

        return "\n".join(parts)

    def generate_solution(self) -> str:
        """Generate initial solution.

        Returns:
            Generated Python code
        """
        user_prompt = self._build_initial_prompt()

        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        start = time.time()
        response = self.client.chat(self.model, self.conversation_history)
        duration = time.time() - start

        code = OpenRouterClient._extract_code(response.content)

        # Track assistant response in conversation
        self.conversation_history.append(
            {"role": "assistant", "content": response.content}
        )

        attempt = AgentAttempt(
            phase_id=0,
            attempt_id=len(self.attempts),
            code=code,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            duration_seconds=duration,
        )
        self.attempts.append(attempt)

        return code

    def refine_solution(self, feedback: dict[str, Any]) -> str:
        """Refine solution based on feedback.

        Args:
            feedback: Parsed feedback.json content

        Returns:
            Updated Python code
        """
        user_prompt = self._build_refinement_prompt(feedback)

        # Keep conversation context but limit to last few turns to avoid token overflow
        if len(self.conversation_history) > 10:
            # Keep system + first prompt + last 4 turns
            self.conversation_history = (
                self.conversation_history[:3]
                + self.conversation_history[-4:]
            )

        self.conversation_history.append({"role": "user", "content": user_prompt})

        start = time.time()
        response = self.client.chat(self.model, self.conversation_history)
        duration = time.time() - start

        code = OpenRouterClient._extract_code(response.content)

        self.conversation_history.append(
            {"role": "assistant", "content": response.content}
        )

        phase_id = feedback.get("phase_id", 0)
        attempt = AgentAttempt(
            phase_id=phase_id,
            attempt_id=len(self.attempts),
            code=code,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            duration_seconds=duration,
        )
        self.attempts.append(attempt)

        return code

    def write_solution(self, code: str) -> None:
        """Write code to the solution file in workspace."""
        solution_path = self.workspace_dir / "solution.py"
        solution_path.write_text(code, encoding="utf-8")

    def get_total_tokens(self) -> dict[str, int]:
        """Get total token usage across all attempts."""
        prompt = sum(a.prompt_tokens for a in self.attempts)
        completion = sum(a.completion_tokens for a in self.attempts)
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
        }
