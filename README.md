# Saotri Bench

<p align="center">
  <img src="assets/saotri-logo.png" alt="SaotriBench" width="400">
</p>

A coding benchmark for evaluating LLM agents on multi-phase programming tasks. Tests three critical capabilities:

- **Hidden requirement discovery** — inferring undisclosed constraints from structured feedback
- **Long-context retention** — maintaining state and hypotheses across many iterations  
- **Iterative refinement** — systematically improving solutions based on violation signals

```
+-----------------------------------------------------------+
|                    Saotri Bench Flow                      |
+-----------------------------------------------------------+
|                                                           |
|  +-------+   +------------+   +--------+   +-----------+  |
|  | Agent |-->| solution.py|-->| Runner |-->| Evaluator |  |
|  +-------+   +------------+   +--------+   +-----------+  |
|      ^                            |              |        |
|      |                            |              v        |
|      |       +-------------+      |        +----------+   |
|      +-------|feedback.json|<-----+        |Test Cases|   |
|              +-------------+               | (hidden) |   |
|                    |                       +----------+   |
|                    v                                      |
|              +-------------+                              |
|              |  Violations |                              |
|              |  + Coverage |                              |
|              +-------------+                              |
|                                                           |
+-----------------------------------------------------------+
|  Phase 0     Phase 1     Phase 2     ...     Phase N      |
|  +------+    +------+    +------+            +------+     |
|  | Rule |    | Rule |    | Rule |            | Rule |     |
|  |  A   | +  |  A   | +  |  A   | + ... +    |  A   |     |
|  +------+    |  B   |    |  B   |            |  B   |     |
|              +------+    |  C   |            | ...  |     |
|                          +------+            |  Z   |     |
|                                              +------+     |
|  <------- Rules accumulate across phases ----------->     |
+----------------------------------------------------------+
```

## Core Concept

The agent receives only minimal initial information (input/output types, basic problem description). The actual correctness constraints are **not fully disclosed** — the agent must infer them from structured feedback on failed attempts.

Key properties:
- Agent starts with incomplete specification
- Hidden constraints are revealed indirectly through violation feedback
- Each phase introduces new undisclosed requirements that **break the previous solution**
- Success requires systematic exploration, not just code generation

## Installation

```bash
pip install -e .
```

After installation, the `saotri-bench` command becomes available. Alternatively, you can run without installing:

```bash
python -m saotri_bench.cli <command>
```

## Available Tasks

| Task | Difficulty | Phases | Description |
|------|-----------|--------|-------------|
| `task_00_fizzbuzz` | Easy | 3 | FizzBuzz with hidden divisor rules (`%7`, combinations) |
| `task_01_transform_list` | Easy | 3 | List transformation with evolving number handling |
| `task_02_merge_dicts` | Easy | 4 | Dict merge with type-aware conflict resolution |
| `task_03_validate_brackets` | Medium | 5 | Bracket validation with changing contract (bool → exception) |
| `task_04_sort_objects` | Medium | 6 | Object sorting with evolving key format and edge cases |

## Quick Start

> All examples below use `saotri-bench` (requires `pip install -e .`).  
> Without installing, replace `saotri-bench` with `python -m saotri_bench.cli`.

### List available tasks

```bash
saotri-bench list --tasks-dir tasks
```

### Validate a task

```bash
saotri-bench validate --task tasks/task_00_fizzbuzz
```

### Run a task (interactive mode — for agents)

```bash
saotri-bench run --task tasks/task_00_fizzbuzz --workspace ./workspace --poll-interval 2
```

### Run a task (single evaluation)

```bash
saotri-bench run --task tasks/task_00_fizzbuzz --workspace ./workspace --single
```

## How It Works

### For agents (automated)

1. The runner starts and creates the workspace with `problem.md`, `task.json`, `phase.json`, and an empty `solution.py`
2. The agent reads `problem.md` to understand the task and `phase.json` to see current rules
3. The agent writes its solution to `workspace/solution.py`
4. The runner detects the file change and evaluates the solution
5. The runner writes structured feedback to `workspace/feedback.json`
6. The agent reads feedback, identifies violations, and refines its solution
7. Steps 3–6 repeat until all phases pass or attempt limits are reached

### For manual testing

You can simulate an agent by manually editing `workspace/solution.py` while the runner is active:

```bash
# Terminal 1: Start the runner
saotri-bench run --task tasks/task_00_fizzbuzz --workspace ./workspace --poll-interval 2

# Terminal 2: Write your solution
# Edit workspace/solution.py with your code
# The runner will auto-detect changes and evaluate
```

**Stopping the runner:**
- Type `q` + Enter in the runner terminal
- Or press `Ctrl+C`

### Example walkthrough (task_00_fizzbuzz)

**Phase 0** — You read `problem.md` and write classic FizzBuzz:

```python
def fizzbuzz(n):
    if n % 15 == 0: return "FizzBuzz"
    if n % 3 == 0: return "Fizz"
    if n % 5 == 0: return "Buzz"
    return str(n)
```

Feedback: `status: "valid"` — Phase 0 passes, runner advances to Phase 1.

**Phase 1** — Implicit evaluation runs. Feedback shows violations:
```json
{"rule_id": "correct_output", "scope": "divisible_by_7", "count": 3}
```

You infer: there's a hidden rule for multiples of 7. You add `"Bazz"` handling:

```python
def fizzbuzz(n):
    result = ""
    if n % 3 == 0: result += "Fizz"
    if n % 5 == 0: result += "Buzz"
    if n % 7 == 0: result += "Bazz"
    return result if result else str(n)
```

Phase 1 passes. Phase 2 reveals combination violations (`divisible_by_21`, `divisible_by_35`, `divisible_by_105`). Your Phase 1 solution already handles these — Phase 2 passes too. Task complete!

## Workspace Protocol

When running a task, the runner creates a workspace directory with:

| File | Description |
|------|-------------|
| `problem.md` | Problem description (agent-visible) |
| `task.json` | Task metadata, interface, and limits |
| `phase.json` | Current phase info, rules, and previous feedback |
| `solution.py` | Agent writes solution here (runner watches for changes) |
| `feedback.json` | Evaluation feedback after each attempt |
| `report.json` | Final metrics report (written on session end) |

> **Note:** The `workspace/` directory is gitignored. Each run starts fresh — delete old workspace files before starting a new session if needed.

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

**Status values:**
- `valid` — all rules pass, phase advances
- `partially_valid` — some rules pass, some fail
- `invalid` — no rules pass
- `error` — code failed to execute (syntax error, timeout, import violation)

**Violation scopes** hint at what went wrong without revealing test cases. For example, `"scope": "divisible_by_7"` tells the agent that something related to sevens is failing.

## Task Structure

Each task is a directory with 4 files:

```
tasks/task_00_fizzbuzz/
├── task.yaml       # Task metadata, phases, rules, limits
├── problem.md      # Agent-visible problem description
├── evaluator.py    # Evaluation logic (check_* methods)
└── tests.py        # Test cases with expected values (hidden from agent)
```

## Creating New Tasks

1. Create a new directory under `tasks/` (convention: `task_XX_name`)
2. Define `task.yaml` with phases and rules
3. Write `problem.md` (what the agent sees — keep it minimal for harder tasks)
4. Implement `evaluator.py` with a class `Evaluator(BaseEvaluator)` and `check_{rule_id}` methods
5. Create `tests.py` with a `TEST_CASES` list of `TestCase` objects
6. Validate with `saotri-bench validate --task tasks/your_task`

### Design principles

- **Each phase must break the previous solution** — a naive solution passing Phase N should fail on Phase N+1
- **Violation scopes are hints, not answers** — they tell the agent *what area* failed, not *what the answer is*
- **Expected values must be consistent across all phases** — the evaluator runs ALL prior-phase tests on the current solution
- **Easy tasks** include examples in `problem.md`; **harder tasks** give only the function signature

### Example task.yaml

```yaml
id: "task_00_fizzbuzz"
name: "FizzBuzz Extended"
description: "Implement FizzBuzz with evolving divisor rules"
difficulty: "easy"

interface:
  function_name: "fizzbuzz"
  signature: "def fizzbuzz(n: int) -> str"
  allowed_imports: []

execution:
  timeout_seconds: 10

phases:
  - id: 0
    description: "Classic FizzBuzz"
    rules:
      - id: "correct_output"
        description: "Output matches expected string"
        scopes: ["divisible_by_3", "divisible_by_5", "divisible_by_15", "plain_number"]

  - id: 1
    description: "New divisor rule"
    rules:
      - id: "correct_output"
        description: "Output matches expected string"
        scopes: ["divisible_by_3", "divisible_by_5", "divisible_by_15", "plain_number", "divisible_by_7"]
      - id: "correct_type"
        description: "Return value must be a string"
        scopes: ["type_check"]

limits:
  max_attempts_per_phase: 5
  max_total_attempts: 15
```

## Sandbox & Security

Solutions run in a sandboxed environment:
- **Restricted imports** — only explicitly allowed modules can be imported
- **Restricted builtins** — dangerous functions (`eval`, `exec`, `open`, `__import__`) are blocked or controlled
- **Timeout enforcement** — code execution is killed after the configured timeout
- **Input immutability** — evaluators use deep copies to prevent test case corruption

## Difficulty Tiers

| Tier | Phases | Description |
|------|--------|-------------|
| Easy | 3–5 | Basic transformations, simple rules |
| Medium | 5–15 | Moderate complexity, multiple interacting rules |
| Hard | 16–30 | Complex algorithms, many edge cases |
| Expert | 31–50 | Deep challenges, extensive hidden states |

## CLI Reference

```bash
# List all tasks
saotri-bench list [--tasks-dir PATH] [--json]

# Validate a task definition
saotri-bench validate --task PATH

# Run interactively (watch for file changes)
saotri-bench run --task PATH [--workspace PATH] [--agent-id ID] [--poll-interval SEC]

# Run single evaluation
saotri-bench run --task PATH --workspace PATH --single
```

## LLM Agent Benchmark

The `agents/` module provides automated benchmarking of LLM models against Saotri Bench tasks via [OpenRouter](https://openrouter.ai/).

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set your OpenRouter API key
cp agents/.env.example agents/.env
# edit agents/.env with your key
```

### Run benchmark

```bash
# Run all 3 models on all tasks
python -m agents.run_benchmark

# Run a specific model tier on a specific task
python -m agents.run_benchmark --tier strong --task task_00_fizzbuzz

# Run all models on one task
python -m agents.run_benchmark --task task_00_fizzbuzz

# List configured models
python -m agents.run_benchmark --list-models
```

### Configured models

| Tier | Model | Description |
|------|-------|-------------|
| `weak` | Gemma 2 9B | Small model, limited reasoning |
| `medium` | Llama 3.3 70B | Solid open-source model |
| `strong` | Claude Sonnet | Top-tier commercial model |

### Example results

```
Task: FizzBuzz Extended [easy] (3 phases)
Model                Tier     Phases       Attempts   Status     Tokens     Time
Claude Sonnet        strong   3/3          3          PASS       2783       10.8s
Llama 3.3 70B        medium   1/3          6          FAIL       7706       27.4s
Gemma 2 9B           weak     1/3          6          FAIL       7953       13.4s
```

Reports are saved to `reports/` as JSON files (per-run details, per-task comparisons, and a full benchmark summary).

See [`agents/README.md`](agents/README.md) for full documentation.

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
