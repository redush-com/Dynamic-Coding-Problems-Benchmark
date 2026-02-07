"""Benchmark runner that orchestrates LLM agents against tasks.

This module connects the CodingAgent (LLM) with the Saotri Bench Runner
(evaluator), automating the read-write-evaluate loop.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent import CodingAgent
from .config import ModelConfig, get_model, list_models
from .llm_client import OpenRouterClient

# Add parent to path so we can import saotri_bench
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from saotri_bench.runner import Runner
from saotri_bench.models import Status


@dataclass
class RunResult:
    """Result of a single agent run on a single task."""

    model_id: str
    model_label: str
    model_tier: str
    task_id: str
    task_name: str
    difficulty: str
    total_phases: int
    phases_completed: int
    total_attempts: int
    final_status: str  # "completed" | "failed"
    phase_results: list[dict[str, Any]]
    token_usage: dict[str, int]
    total_duration_seconds: float
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_label": self.model_label,
            "model_tier": self.model_tier,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "difficulty": self.difficulty,
            "total_phases": self.total_phases,
            "phases_completed": self.phases_completed,
            "total_attempts": self.total_attempts,
            "final_status": self.final_status,
            "phase_results": self.phase_results,
            "token_usage": self.token_usage,
            "total_duration_seconds": self.total_duration_seconds,
            "timestamp": self.timestamp,
        }


def run_agent_on_task(
    model_config: ModelConfig,
    task_dir: Path,
    workspace_dir: Path,
    api_key: str,
    verbose: bool = True,
) -> RunResult:
    """Run a single LLM agent on a single task.

    This creates a Runner and a CodingAgent, then automates the
    generate → evaluate → refine loop.

    Args:
        model_config: LLM model configuration
        task_dir: Path to task directory
        workspace_dir: Path to workspace (will be cleaned)
        api_key: OpenRouter API key
        verbose: Print progress to stdout

    Returns:
        RunResult with all metrics
    """
    # Clean workspace
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Create runner
    runner = Runner(
        task_dir=task_dir,
        workspace_dir=workspace_dir,
        agent_id=model_config.label,
    )
    runner.setup_workspace()

    # Create agent
    client = OpenRouterClient(api_key=api_key)
    agent = CodingAgent(
        model=model_config,
        client=client,
        workspace_dir=workspace_dir,
    )

    task_config = runner.task_config
    total_phases = len(task_config.phases)
    start_time = time.time()

    if verbose:
        print(f"\n{'='*60}")
        print(f"Model: {model_config.label} ({model_config.tier})")
        print(f"Task:  {task_config.name} ({task_config.difficulty.value})")
        print(f"Phases: {total_phases}")
        print(f"{'='*60}")

    # Phase tracking
    phase_results = []
    phases_completed = 0
    final_status = "failed"

    try:
        # Generate initial solution
        if verbose:
            print(f"\n[Phase 0] Generating initial solution...")

        code = agent.generate_solution()
        agent.write_solution(code)

        if verbose:
            print(f"  Generated {len(code)} chars of code")

        # Evaluation loop
        while True:
            # Check limits
            if runner.total_attempts >= task_config.limits.max_total_attempts:
                if verbose:
                    print(f"\n  Max total attempts ({task_config.limits.max_total_attempts}) reached.")
                break

            if runner.phase_attempts >= task_config.limits.max_attempts_per_phase:
                if verbose:
                    print(f"\n  Max phase attempts ({task_config.limits.max_attempts_per_phase}) reached.")
                break

            # Evaluate
            feedback = runner.run_single_attempt()

            if verbose:
                print(f"  Attempt {runner.total_attempts}: "
                      f"status={feedback.status.value}, "
                      f"coverage={feedback.summary.coverage:.1%}")
                if feedback.violations:
                    for v in feedback.violations:
                        print(f"    - {v.rule_id}/{v.scope}: {v.count}")
                if feedback.error:
                    print(f"    ERROR: {feedback.error.message[:100]}")

            # Phase complete?
            if feedback.status == Status.VALID:
                runner.metrics.complete_phase(runner.current_phase.id)
                phases_completed += 1

                phase_results.append({
                    "phase_id": runner.current_phase.id,
                    "status": "completed",
                    "attempts": runner.phase_attempts,
                    "coverage": feedback.summary.coverage,
                })

                if verbose:
                    print(f"  Phase {runner.current_phase.id} COMPLETED!")

                # Advance phase
                if runner._advance_phase():
                    if verbose:
                        print(f"\n[Phase {runner.current_phase.id}] Advancing...")

                    # Run implicit evaluation
                    implicit_fb = runner.run_implicit_evaluation()
                    runner._write_phase_info(
                        phase_transition=True,
                        implicit_feedback=implicit_fb.to_dict(),
                    )

                    if verbose:
                        print(f"  Implicit eval: status={implicit_fb.status.value}, "
                              f"coverage={implicit_fb.summary.coverage:.1%}")

                    if implicit_fb.status == Status.VALID:
                        # Already passing new phase, no need to refine
                        runner.metrics.complete_phase(runner.current_phase.id)
                        phases_completed += 1
                        phase_results.append({
                            "phase_id": runner.current_phase.id,
                            "status": "completed",
                            "attempts": 0,
                            "coverage": implicit_fb.summary.coverage,
                        })
                        if verbose:
                            print(f"  Phase {runner.current_phase.id} COMPLETED (implicit)!")

                        # Try advancing again
                        if not runner._advance_phase():
                            final_status = "completed"
                            if verbose:
                                print("\n  ALL PHASES COMPLETED!")
                            break
                        continue

                    # Need to refine for new phase
                    feedback_data = json.loads(
                        runner.feedback_file.read_text(encoding="utf-8")
                    ) if runner.feedback_file.exists() else implicit_fb.to_dict()

                    # Read phase.json for phase transition context
                    phase_data = json.loads(
                        runner.phase_file.read_text(encoding="utf-8")
                    )

                    code = agent.refine_solution(phase_data)
                    agent.write_solution(code)

                    if verbose:
                        print(f"  Refined solution ({len(code)} chars)")
                    continue
                else:
                    # All phases done
                    final_status = "completed"
                    if verbose:
                        print("\n  ALL PHASES COMPLETED!")
                    break

            # Not valid yet — refine
            feedback_data = feedback.to_dict()
            code = agent.refine_solution(feedback_data)
            agent.write_solution(code)

            if verbose:
                print(f"  Refined solution ({len(code)} chars)")

    except Exception as e:
        if verbose:
            print(f"\n  AGENT ERROR: {e}")
        final_status = "error"

    total_duration = time.time() - start_time

    # Record any unfinished phases
    if phases_completed < total_phases:
        current_phase_id = runner.current_phase.id
        # Check if current phase is already in results
        recorded_phases = {p["phase_id"] for p in phase_results}
        if current_phase_id not in recorded_phases:
            phase_results.append({
                "phase_id": current_phase_id,
                "status": "failed",
                "attempts": runner.phase_attempts,
                "coverage": (
                    runner.previous_feedback.summary.coverage
                    if runner.previous_feedback
                    else 0.0
                ),
            })

    result = RunResult(
        model_id=model_config.id,
        model_label=model_config.label,
        model_tier=model_config.tier,
        task_id=task_config.id,
        task_name=task_config.name,
        difficulty=task_config.difficulty.value,
        total_phases=total_phases,
        phases_completed=phases_completed,
        total_attempts=runner.total_attempts,
        final_status=final_status,
        phase_results=phase_results,
        token_usage=agent.get_total_tokens(),
        total_duration_seconds=total_duration,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    if verbose:
        print(f"\nResult: {phases_completed}/{total_phases} phases, "
              f"{runner.total_attempts} attempts, "
              f"{total_duration:.1f}s, "
              f"tokens: {agent.get_total_tokens()['total_tokens']}")

    return result
