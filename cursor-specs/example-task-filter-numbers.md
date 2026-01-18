# Example Easy Task (Illustrative Only)

> ⚠️ **Important**
> 
> This is a purely illustrative example created to clearly demonstrate:
> - how a DCP-Bench task is structured
> - how phases evolve
> - how hidden requirements are inferred via feedback
> 
> This is **not**:
> - an optimal benchmark task
> - a final difficulty calibration
> - a recommendation to copy verbatim
> 
> Its sole purpose is to improve understanding of the benchmark design.

---

## Task ID

`task_00_filter_numbers`

---

## 1. High-level Idea (Human Perspective)

At first glance, the task looks trivial:

> "Filter a list of numbers."

However:

- the specification is **intentionally incomplete**
- key constraints are **never stated explicitly**
- the agent must **infer hidden rules** through structured feedback

This makes the task about **specification discovery**, not coding.

---

## 2. Difficulty Classification

```
difficulty: easy
```

### Why this is Easy

- simple input/output types (`list[int]`)
- no advanced algorithms required
- rules are introduced one-by-one
- no conflicting constraints
- shallow hypothesis space

---

## 3. File Structure

```
tasks/
└── task_00_filter_numbers/
    ├── task.yaml
    ├── problem.md
    ├── evaluator.py
    └── tests.py
```

---

## 4. problem.md (Agent-visible)

```markdown
# Filter Numbers

## Problem
Implement a function that processes a list of integers and returns
a filtered list according to some rules.

## Input
- `numbers`: list of integers

## Output
- A new list of integers

## Notes
- Requirements become stricter in later phases
- Do not modify the input list
```

### What the Agent Does NOT Know

- which numbers are considered valid
- whether order matters
- how to handle zero or negative values
- whether duplicates are allowed
- whether mutation is allowed

**All of this must be inferred.**

---

## 5. task.yaml (Complete Task Definition)

```yaml
id: "task_00_filter_numbers"
name: "Filter Numbers"
description: "Filter and transform a list of integers"
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
        description: "Output matches expected filtered list"
        scopes: ["basic"]
  
  - id: 1
    description: "Handle edge values and immutability"
    rules:
      - id: "correct_output"
        description: "Output matches expected filtered list"
        scopes: ["basic", "negatives", "zeros"]
      - id: "no_mutation"
        description: "Input list must not be modified"
        scopes: ["direct"]

  - id: 2
    description: "Determinism and ordering"
    rules:
      - id: "correct_output"
        description: "Output matches expected filtered list"
        scopes: ["basic", "negatives", "zeros", "duplicates"]
      - id: "no_mutation"
        description: "Input list must not be modified"
        scopes: ["direct"]
      - id: "deterministic"
        description: "Same input always produces same output"
        scopes: ["ordering"]

limits:
  max_attempts_per_phase: 5
  max_total_attempts: 15
```

---

## 6. Hidden Semantics (Never Visible to the Agent)

| Concept | Actual Rule |
|---------|-------------|
| Filtering | Keep only positive numbers (> 0) |
| Ordering | Preserve original input order |
| Zero handling | 0 is invalid |
| Negatives | All negative numbers are removed |
| Mutation | Input list must remain unchanged |
| Determinism | No sorting, no set, no nondeterministic behavior |

**The agent never sees these rules directly.**

---

## 7. tests.py (Hidden Test Cases)

```python
from dcp_bench.testing import TestCase

TEST_CASES = [

    # Phase 0 — basic filtering only
    TestCase(
        input=[1, 2, 3],
        expected=[1, 2, 3],
        phase=0,
        tags=["basic"]
    ),
    TestCase(
        input=[1, -2, 3],
        expected=[1, 3],
        phase=0,
        tags=["basic"]
    ),

    # Phase 1 — zeros and immutability
    TestCase(
        input=[0, 1, 2],
        expected=[1, 2],
        phase=1,
        tags=["zeros"]
    ),
    TestCase(
        input=[-1, 0, 3],
        expected=[3],
        phase=1,
        tags=["negatives"]
    ),

    # Phase 2 — duplicates and ordering
    TestCase(
        input=[3, 1, 3, 2],
        expected=[3, 1, 3, 2],
        phase=2,
        tags=["duplicates"]
    ),
]
```

---

## 8. evaluator.py (Simplified)

```python
from dcp_bench.evaluator import BaseEvaluator, RuleResult
import copy

class Evaluator(BaseEvaluator):

    def check_correct_output(self, solution_fn, test_case):
        result = solution_fn(test_case.input)
        if result == test_case.expected:
            return RuleResult.passed()
        return RuleResult.failed(scope=test_case.tags[0])

    def check_no_mutation(self, solution_fn, test_case):
        original = copy.deepcopy(test_case.input)
        solution_fn(test_case.input)
        if test_case.input == original:
            return RuleResult.passed()
        return RuleResult.failed(scope="direct")

    def check_deterministic(self, solution_fn, test_case):
        r1 = solution_fn(test_case.input)
        r2 = solution_fn(test_case.input)
        if r1 == r2:
            return RuleResult.passed()
        return RuleResult.failed(scope="ordering")
```

---

## 9. Example Agent Evolution (Conceptual)

### ❌ Attempt 1 (Phase 0)

```python
def filter_numbers(numbers):
    return numbers
```

**Feedback:**
- `correct_output` ❌ (negatives)

Agent infers: some values must be filtered out

---

### ❌ Attempt 2

```python
def filter_numbers(numbers):
    return [n for n in numbers if n >= 0]
```

**Feedback:**
- Phase 0 ✅
- Phase 1 ❌ (zeros)

Agent infers: 0 is not allowed

---

### ❌ Attempt 3

```python
def filter_numbers(numbers):
    numbers[:] = [n for n in numbers if n > 0]
    return numbers
```

**Feedback:**
- `correct_output` ✅
- `no_mutation` ❌

---

### ✅ Final Solution (Phase 2)

```python
def filter_numbers(numbers):
    return [n for n in numbers if n > 0]
```

---

## 10. What This Easy Task Evaluates

### ✅ What Is Tested

- ability to infer hidden requirements
- hypothesis formation and refinement
- feedback-driven iteration
- maintaining invariants across phases

### ❌ What Is Not Tested

- algorithmic complexity
- optimization
- advanced data structures
- long-term planning
