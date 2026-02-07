# SaotriBench

<p align="center">
  <img src="assets/saotri-logo.png" alt="SaotriBench" width="400">
</p>

A coding benchmark for evaluating LLM agents on multi-phase programming tasks. Tests three critical capabilities:

- **Hidden requirement discovery** — inferring undisclosed constraints from structured feedback
- **Long-context retention** — maintaining state and hypotheses across many iterations  
- **Iterative refinement** — systematically improving solutions based on violation signals

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Saotri Bench Flow                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────┐      ┌─────────────┐      ┌───────────┐      ┌─────────────┐ │
│   │  Agent  │─────▶│  solution.py │─────▶│  Runner   │─────▶│  Evaluator  │ │
│   └─────────┘      └─────────────┘      └───────────┘      └─────────────┘ │
│        ▲                                      │                    │        │
│        │                                      │                    │        │
│        │           ┌─────────────┐            │                    ▼        │
│        └───────────│feedback.json│◀───────────┘           ┌─────────────┐  │
│                    └─────────────┘                        │ Test Cases  │  │
│                          │                                │  (hidden)   │  │
│                          ▼                                └─────────────┘  │
│                    ┌─────────────┐                                          │
│                    │  Violations │                                          │
│                    │  + Coverage │                                          │
│                    └─────────────┘                                          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 0          Phase 1          Phase 2          ...         Phase N    │
│  ┌──────┐         ┌──────┐         ┌──────┐                     ┌──────┐   │
│  │ Rule │         │ Rule │         │ Rule │                     │ Rule │   │
│  │  A   │    +    │  A   │    +    │  A   │    +    ...    +    │  A   │   │
│  └──────┘         │  B   │         │  B   │                     │  B   │   │
│                   └──────┘         │  C   │                     │ ...  │   │
│                                    └──────┘                     │  Z   │   │
│                                                                 └──────┘   │
│  ◀──────────────── Rules accumulate across phases ─────────────────────▶   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Concept

The agent receives only minimal initial information (input/output types, basic problem description). The actual correctness constraints are **not fully disclosed** — the agent must infer them from structured feedback on failed attempts.

Key properties:
- Agent starts with incomplete specification
- Hidden constraints are revealed indirectly through violation feedback
- Each phase introduces new undisclosed requirements
- Success requires systematic exploration, not just code generation

## Installation

```bash
pip install -e .
```

## Quick Start

### List available tasks

```bash
saotri-bench list --tasks-dir tasks
```

### Validate a task

```bash
saotri-bench validate --task tasks/task_00_filter_numbers
```

### Run a task (single evaluation)

```bash
saotri-bench run --task tasks/task_00_filter_numbers --workspace ./workspace --single
```

### Run a task (interactive mode)

```bash
saotri-bench run --task tasks/task_00_filter_numbers --workspace ./workspace
```

In interactive mode, the runner watches for changes to `workspace/solution.py` and evaluates each update.

## Workspace Protocol

When running a task, the runner creates a workspace directory with:

| File | Description |
|------|-------------|
| `problem.md` | Problem description (agent-visible) |
| `task.json` | Task metadata and limits |
| `phase.json` | Current phase info and rules |
| `solution.py` | Agent writes solution here |
| `feedback.json` | Evaluation feedback after each attempt |
| `report.json` | Final metrics report |

## Feedback Format

Each evaluation returns structured JSON feedback:

```json
{
  "phase_id": 1,
  "attempt_id": 5,
  "status": "partially_valid",
  "status_reason": "Fails checks: no_mutation",
  "violations": [
    {"rule_id": "no_mutation", "scope": "direct", "count": 2}
  ],
  "summary": {
    "rules_total": 3,
    "rules_passed": 2,
    "rules_failed": 1,
    "coverage": 0.85
  },
  "delta": {
    "coverage_change": 0.15,
    "new_failures": [],
    "fixed_failures": ["correct_output"]
  }
}
```

## Task Structure

Each task is a directory with:

```
tasks/task_00_filter_numbers/
├── task.yaml       # Task metadata, phases, rules
├── problem.md      # Agent-visible problem description
├── evaluator.py    # Evaluation logic (check_* methods)
└── tests.py        # Test cases (not agent-visible)
```

## Creating New Tasks

1. Create a new directory under `tasks/`
2. Define `task.yaml` with phases and rules
3. Write `problem.md` (what the agent sees)
4. Implement `evaluator.py` with `check_{rule_id}` methods
5. Create `tests.py` with `TEST_CASES` list
6. Validate with `saotri-bench validate --task tasks/your_task`

### Example task.yaml

```yaml
id: "task_00_filter_numbers"
name: "Filter Numbers"
difficulty: "easy"

interface:
  function_name: "filter_numbers"
  signature: "def filter_numbers(numbers: list[int]) -> list[int]"
  allowed_imports: []

execution:
  timeout_seconds: 10

phases:
  - id: 0
    description: "Basic filtering"
    rules:
      - id: "correct_output"
        description: "Output matches expected"
        scopes: ["basic"]

  - id: 1
    description: "Handle edge cases"
    rules:
      - id: "correct_output"
        description: "Output matches expected"
        scopes: ["basic", "zeros", "negatives"]
      - id: "no_mutation"
        description: "Input must not be modified"
        scopes: ["direct"]

limits:
  max_attempts_per_phase: 5
  max_total_attempts: 15
```

## Difficulty Tiers

| Tier | Phases | Description |
|------|--------|-------------|
| Easy | 3–5 | Basic transformations, simple rules |
| Medium | 6–15 | Moderate complexity, multiple interacting rules |
| Hard | 16–30 | Complex algorithms, many edge cases |
| Expert | 31–50 | Deep challenges, extensive hidden states |

## The Name: SAOTRI

**SAOTRI** is an acronym that captures the core dimensions of the benchmark evaluation model:

| Letter | Stands for | Description |
|--------|-----------|-------------|
| **S** | Hidden **S**tate | The concealed environment state — infrastructure, load, constraints invisible to the agent |
| **A** | **A**ctions | The agent's actions, manifested as code patches submitted each attempt |
| **O** | **O**bservations | What the agent perceives — logs, metrics, error signals, structured feedback |
| **T** | Non-stationary **T**ransitions | The environment dynamics that shift across phases — rules accumulate, constraints tighten |
| **R** | **R**esilience function | The reward signal measuring solution robustness and survival under evolving requirements |
| **I** | **I**nvariants | The safety and correctness guarantees — state integrity, data safety, behavioral contracts |

Learn more at [saotri.com](https://saotri.com)

## License

MIT
