# Dynamic Coding Problems Benchmark (DCP-Bench)
## Technical Specification v1.0 (MVP)

## 1. Goal

DCP-Bench evaluates how efficiently an LLM or agent system can **discover hidden requirements** through iterative feedback.

**Core challenge:** The agent receives only minimal initial information (input/output types, basic problem class). The actual correctness constraints are **not fully disclosed** — the agent must infer them from structured feedback on failed attempts.

Key properties:

- The agent starts with incomplete specification (only essential input/output contract)
- Hidden constraints are revealed indirectly through violation feedback
- Each phase introduces new undisclosed requirements
- The agent must form hypotheses about hidden rules and refine them based on feedback
- Success requires systematic exploration, not just code generation

---

## 2. Core Concepts

### 2.1 Task

A **task** is a single coding problem with multiple phases. Each task has:
- a problem description
- a required function signature
- a set of phases with evolving rules

### 2.2 Phase

A **phase** is a stage of a task with a fixed set of rules. Rules only grow stricter across phases:

```
ValidSolutions₀ ⊇ ValidSolutions₁ ⊇ ... ⊇ ValidSolutionsₙ
```

**Important:** All phases within a task constitute a single continuous run. The agent must maintain state and context across all phases to progressively refine its solution.

### 2.3 Rule

A **rule** is a named correctness constraint (e.g., "no_input_mutation", "deterministic_output").

Rules are checked by the evaluator. The agent sees rule names and descriptions but not the test cases.

### 2.4 Attempt

An **attempt** is a single code submission by the agent. Each attempt produces one feedback response.

### 2.5 Scope

A **scope** is a category label for where a rule violation occurred (e.g., "nested_objects", "edge_cases"). Scopes help the agent understand failure patterns without revealing specific test inputs.

---

## 3. Task Difficulty Levels

Tasks are organized into difficulty levels. Difficulty is determined by multiple factors, not just the number of phases.

### 3.1 Difficulty Factors

| Factor | Description |
|--------|-------------|
| **Number of phases** | More phases = more incremental constraints to satisfy |
| **Phase complexity** | How much each phase adds (simple rule vs complex behavioral constraint) |
| **Hidden states** | Number of edge cases and implicit requirements not obvious from description |
| **Data structure complexity** | Flat vs nested vs recursive vs graph-like structures |
| **Algorithmic depth** | Simple iteration vs dynamic programming vs graph algorithms |
| **Constraint interactions** | How rules interact and conflict with each other |

### 3.2 Difficulty Tiers

| Tier | Phases | Description |
|------|--------|-------------|
| **Easy** | 3–5 | Basic data transformations, simple rules, minimal hidden states |
| **Medium** | 6–15 | Moderate algorithmic complexity, multiple interacting rules |
| **Hard** | 16–30 | Complex algorithms, many edge cases, subtle constraint interactions |
| **Expert** | 31–50 | Deep algorithmic challenges, extensive hidden states, complex structures |

### 3.3 Requirements

- **Minimum phases per task:** 3
- **Maximum phases per task:** 50
- Difficulty must increase gradually within a tier
- Tasks should cover diverse problem domains (strings, graphs, trees, optimization, etc.)

---

## 4. Task Structure

```
tasks/
└── task_01_example/
    ├── task.yaml        # task metadata + phases + rules
    ├── problem.md       # agent-visible problem description
    ├── evaluator.py     # evaluation logic
    └── tests.py         # test cases (not agent-visible)
```

### 4.1 task.yaml

Complete task definition including phases and rules.

```yaml
id: "task_01_normalize_dict"
name: "Normalize Dictionary"
description: "Transform nested dictionaries according to rules"
difficulty: "easy"  # easy | medium | hard | expert

interface:
  function_name: "normalize"
  signature: "def normalize(data: dict) -> dict"
  allowed_imports: ["copy", "collections"]

execution:
  timeout_seconds: 30  # safety limit to prevent infinite loops

phases:
  - id: 0
    description: "Basic normalization"
    rules:
      - id: "correct_output"
        description: "Output matches expected structure"
        scopes: ["flat", "nested", "empty"]
      - id: "no_mutation"
        description: "Input dict must not be modified"
        scopes: ["direct", "nested"]

  - id: 1
    description: "Handle edge cases"
    rules:
      - id: "correct_output"
        description: "Output matches expected structure"
        scopes: ["flat", "nested", "empty", "circular_refs", "large_depth"]
      - id: "no_mutation"
        description: "Input dict must not be modified"
        scopes: ["direct", "nested"]
      - id: "deterministic"
        description: "Same input always produces same output"
        scopes: ["dict_ordering", "float_precision"]

limits:
  max_attempts_per_phase: 10
  max_total_attempts: 50
```

### 4.2 problem.md (agent-visible)

```markdown
# Normalize Dictionary

## Problem
Implement a function that normalizes a nested dictionary...

## Input
- `data`: a dictionary (may be nested)

## Output
- A new dictionary with normalized structure

## Notes
- Requirements become stricter in later phases
- Do not modify the input
```

### 4.3 evaluator.py

```python
from typing import Any
from dcp_bench.evaluator import BaseEvaluator, RuleResult

class Evaluator(BaseEvaluator):
    def check_correct_output(self, solution_fn, test_case) -> RuleResult:
        """Check if output matches expected."""
        result = solution_fn(test_case.input)
        if result == test_case.expected:
            return RuleResult.passed()
        return RuleResult.failed(scope=self.classify_scope(test_case))
    
    def check_no_mutation(self, solution_fn, test_case) -> RuleResult:
        """Check if input was mutated."""
        import copy
        original = copy.deepcopy(test_case.input)
        solution_fn(test_case.input)
        if test_case.input == original:
            return RuleResult.passed()
        return RuleResult.failed(scope="direct" if is_direct else "nested")
    
    def check_deterministic(self, solution_fn, test_case) -> RuleResult:
        """Check if function is deterministic."""
        results = [solution_fn(copy.deepcopy(test_case.input)) for _ in range(3)]
        if all(r == results[0] for r in results):
            return RuleResult.passed()
        return RuleResult.failed(scope="dict_ordering")
```

### 4.4 tests.py

```python
from dcp_bench.testing import TestCase

TEST_CASES = [
    TestCase(
        input={"a": 1, "b": 2},
        expected={"a": 1, "b": 2},
        phase=0,
        tags=["flat"]
    ),
    TestCase(
        input={"a": {"b": {"c": 1}}},
        expected={"a": {"b": {"c": 1}}},
        phase=0,
        tags=["nested"]
    ),
    # Phase 1 adds more edge cases
    TestCase(
        input=create_deep_dict(depth=100),
        expected=...,
        phase=1,
        tags=["large_depth"]
    ),
]
```

---

## 5. Feedback Schema

Every attempt returns this JSON structure:

```json
{
  "phase_id": 1,
  "attempt_id": 5,
  "status": "partially_valid",
  "status_reason": "Fails determinism checks on dictionary ordering",
  
  "violations": [
    {
      "rule_id": "deterministic",
      "scope": "dict_ordering",
      "count": 3
    }
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
    "fixed_failures": ["no_mutation"]
  }
}
```

### 5.1 Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `phase_id` | int | Current phase (0-indexed) |
| `attempt_id` | int | Attempt number within task |
| `status` | enum | `"valid"` / `"partially_valid"` / `"invalid"` / `"error"` |
| `status_reason` | string | Human-readable explanation |
| `violations` | array | List of rule violations |
| `violations[].rule_id` | string | Which rule was violated |
| `violations[].scope` | string | Category of failure |
| `violations[].count` | int | Number of test cases that failed |
| `summary.rules_total` | int | Total rules in current phase |
| `summary.rules_passed` | int | Rules with zero violations |
| `summary.rules_failed` | int | Rules with at least one violation |
| `summary.coverage` | float | Fraction of test cases passing all rules (0.0-1.0) |
| `delta.coverage_change` | float | Coverage difference from previous attempt (null if first) |
| `delta.new_failures` | array | Rules that regressed |
| `delta.fixed_failures` | array | Rules that improved |

### 5.2 Status Values

- `valid` — All rules pass, ready to advance to next phase
- `partially_valid` — Some rules pass, some fail
- `invalid` — Critical failures (e.g., wrong return type, crashes)
- `error` — Code failed to execute (syntax error, timeout, exception)

### 5.3 Error Handling

If code fails to execute, feedback includes error info:

```json
{
  "status": "error",
  "status_reason": "Runtime error: maximum recursion depth exceeded",
  "error": {
    "type": "RecursionError",
    "message": "maximum recursion depth exceeded",
    "phase": "execution"
  },
  "violations": [],
  "summary": {
    "rules_total": 3,
    "rules_passed": 0,
    "rules_failed": 0,
    "coverage": 0.0
  },
  "delta": null
}
```

---

## 6. Runner Protocol

### 6.1 Session Flow

```
1. Runner loads task
2. For phase_id in 0..N:
   a. Send to agent: problem.md, interface, current phase rules
   b. Loop until valid or max_attempts:
      - Receive code from agent
      - Execute evaluator
      - Return feedback JSON
      - If status == "valid": break
   c. If not valid after max_attempts: task failed
3. Output metrics report
```

### 6.2 Agent Interface

Agent receives per phase:

```json
{
  "task_id": "task_01_normalize_dict",
  "phase_id": 1,
  "problem": "... contents of problem.md ...",
  "interface": {
    "function_name": "normalize",
    "signature": "def normalize(data: dict) -> dict",
    "allowed_imports": ["copy", "collections"]
  },
  "rules": [
    {"id": "correct_output", "description": "Output matches expected structure"},
    {"id": "no_mutation", "description": "Input dict must not be modified"},
    {"id": "deterministic", "description": "Same input always produces same output"}
  ],
  "previous_feedback": { ... }  // null for first attempt
}
```

Agent responds with:

```json
{
  "code": "def normalize(data: dict) -> dict:\n    import copy\n    ..."
}
```

---

## 7. Metrics Report

After task completion, runner outputs:

```json
{
  "task_id": "task_01_normalize_dict",
  "agent_id": "gpt-4-turbo",
  "timestamp": "2025-01-18T12:00:00Z",
  
  "phases": [
    {
      "phase_id": 0,
      "status": "valid",
      "attempts": 2,
      "final_coverage": 1.0,
      "duration_seconds": 45.2
    },
    {
      "phase_id": 1,
      "status": "valid", 
      "attempts": 5,
      "final_coverage": 1.0,
      "duration_seconds": 120.8
    }
  ],
  
  "overall": {
    "status": "completed",
    "total_attempts": 7,
    "total_phases": 2,
    "phases_completed": 2,
    "total_duration_seconds": 166.0
  }
}
```

---

## 8. Implementation Checklist (MVP)

### 8.1 Core Components

- [ ] **Task Loader** — Parse `task.yaml`, load evaluator and tests
- [ ] **Evaluator Base Class** — Abstract class with rule checking interface
- [ ] **Runner** — Orchestrate phases, attempts, feedback loop
- [ ] **Sandbox** — Execute agent code safely (safety timeout, import restrictions)
- [ ] **Metrics Collector** — Track attempts, coverage, generate report

### 8.2 File Structure

```
dcp_bench/
├── __init__.py
├── runner.py           # Main benchmark runner
├── evaluator.py        # Base evaluator class
├── sandbox.py          # Safe code execution
├── models.py           # Data classes (Feedback, TaskConfig, etc.)
├── metrics.py          # Metrics collection and reporting
└── cli.py              # Command-line interface

tasks/
├── task_01_normalize_dict/
├── task_02_dependency_sort/
└── ...
```

### 8.3 MVP Scope

**Include:**
- Single-file Python solutions
- Synchronous evaluation
- JSON feedback per attempt
- Basic sandboxing (safety timeout, restricted imports)
- 2-3 example tasks

**Exclude (post-MVP):**
- Multi-file solutions
- Async/parallel evaluation
- Web UI
- Automatic task generation
- Property-based testing integration

---

## 9. Example Task: Dependency Sort

Complete example to illustrate the spec.

### task.yaml

```yaml
id: "task_02_dependency_sort"
name: "Dependency Sort"
description: "Sort items respecting dependencies"
difficulty: "easy"  # easy | medium | hard | expert

interface:
  function_name: "sort_dependencies"
  signature: "def sort_dependencies(items: list[str], deps: dict[str, list[str]]) -> list[str]"
  allowed_imports: []

execution:
  timeout_seconds: 30  # safety limit to prevent infinite loops

phases:
  - id: 0
    description: "Basic topological sort"
    rules:
      - id: "valid_order"
        description: "Dependencies appear before dependents"
        scopes: ["linear", "branching"]
      - id: "complete"
        description: "All items present in output"
        scopes: ["all"]

  - id: 1
    description: "Handle cycles and edge cases"
    rules:
      - id: "valid_order"
        description: "Dependencies appear before dependents"
        scopes: ["linear", "branching", "complex"]
      - id: "complete"
        description: "All items present in output"
        scopes: ["all"]
      - id: "cycle_detection"
        description: "Raise ValueError on circular dependencies"
        scopes: ["simple_cycle", "indirect_cycle"]

  - id: 2
    description: "Deterministic tie-breaking"
    rules:
      - id: "valid_order"
        description: "Dependencies appear before dependents"
        scopes: ["linear", "branching", "complex"]
      - id: "complete"
        description: "All items present in output"
        scopes: ["all"]
      - id: "cycle_detection"
        description: "Raise ValueError on circular dependencies"
        scopes: ["simple_cycle", "indirect_cycle"]
      - id: "deterministic"
        description: "Alphabetical order for items with equal priority"
        scopes: ["tie_breaking"]

limits:
  max_attempts_per_phase: 10
  max_total_attempts: 30
```

### problem.md

```markdown
# Dependency Sort

## Problem
Given a list of items and their dependencies, return a sorted list where 
each item appears after all its dependencies.

## Input
- `items`: list of unique strings
- `deps`: dict mapping item -> list of items it depends on

## Output
- Sorted list of all items

## Example
```python
items = ["a", "b", "c"]
deps = {"b": ["a"], "c": ["b"]}
# Valid output: ["a", "b", "c"]
```

## Notes
- Requirements become stricter in later phases
- Later phases may require specific error handling
```

---

## 10. Acceptance Criteria

DCP-Bench MVP is complete when:

1. ✅ Runner can load and execute tasks from `task.yaml`
2. ✅ Evaluator returns structured JSON feedback per attempt
3. ✅ Phases progress only when current phase is valid
4. ✅ Feedback includes violations with rule_id, scope, count
5. ✅ Coverage is computed deterministically
6. ✅ Metrics report is generated after task completion
7. ✅ At least 2 example tasks are implemented
8. ✅ Agent code is sandboxed (safety timeout, import restrictions)
9. ✅ Metrics report includes duration per phase and total
10. ✅ Each task has minimum 3 phases
11. ✅ Task difficulty tier matches phase count requirements