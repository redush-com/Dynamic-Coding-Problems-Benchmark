# Dynamic Coding Problems Benchmark (DCP-Bench)
## Technical Specification

## 1. Goal

DCP-Bench evaluates how efficiently an LLM or agent system can produce correct code when:

- the problem specification is revealed over multiple phases,
- correctness constraints grow or become stricter over phases,
- after each submitted attempt the agent receives structured, information-rich evaluation feedback (not merely pass/fail),
- the agent must use that feedback to refine hypotheses and converge to a fully valid solution.

The benchmark must allow comparing:

- different LLMs,
- different agent architectures,
- different tool-using pipelines,

using the same tasks and evaluation protocol.

---

## 2. Key Requirement: Structured Feedback Per Attempt

### 2.1 Mandatory property

For every attempt submitted by the agent, the evaluator MUST return a JSON feedback object that includes:

- a validity state (`valid` / `partially_valid` / `invalid`),
- a list of rule violations with counts and scopes,
- a quantitative coverage score (0.0–1.0),
- invariant satisfaction counts,
- deltas vs the previous attempt.

---

## 3. Entities and Definitions

This section defines all key terms used in DCP-Bench.

### 3.1 Attempt

An **attempt** is a single submission of a solution artifact (code) by the agent for evaluation in the current phase.

- Each attempt produces exactly one feedback object.

### 3.2 Phase

A **phase** is a discrete stage of a task during which a fixed set of rules must be satisfied.

- Across phases, rules evolve (see Section 4). During one phase, rules are constant.

### 3.3 Rule

A **rule** is a named correctness constraint with stable identifier `rule_id`.

A rule is **not** a test. A rule is a semantic constraint such as:

- "do not mutate input"
- "output must include same keys"
- "must be deterministic"
- "idempotent behavior"

Rules are evaluated by running tests, but the agent is not exposed to tests.

### 3.4 Rule Scope

A **scope** is a coarse category describing where a rule is violated, without revealing concrete test inputs.

Scope must not identify specific failing cases; it must be a bucket label such as:

- `"top_level"`
- `"nested_dicts"`
- `"lists"`
- `"float_values"`
- `"tie_breaking"`
- `"dependency_graph"`

Each task defines allowed scope values per rule.

### 3.5 Invariant

An **invariant** is an implicit correctness property not necessarily disclosed to the agent, used to prevent gaming and enforce robustness.

Invariants are evaluated by hidden tests or by evaluator instrumentation.

Invariants must be expressed as:

- boolean checks, or
- property-based checks.

Agents are not told the exact invariant logic.

---

## 4. Rule Evolution Across Phases

### 4.1 Mandatory constraint growth

Each phase MUST introduce at least one new constraint or make a previous constraint strictly stricter.

Formally, the set of valid programs must shrink:

```
ValidSolutions₀ ⊃ ValidSolutions₁ ⊃ ... ⊃ ValidSolutionsₙ
```

### 4.2 Optional partial rule modification

A phase may modify an earlier rule.

A modification is allowed only if it does not expand the valid solution space.

**Allowed modification types:**

- `narrow_scope`: rule applies to fewer places but becomes stricter where it applies
- `add_condition`: rule requires additional condition
- `change_semantics_stricter`: semantics change such that fewer solutions remain valid
- `split_rule`: one rule becomes two rules, both required

**Forbidden modifications:**

- removing a rule
- weakening a rule
- adding exceptions that expand valid solution space

---

## 5. Task Packaging (Repository Layout)

Each task is a directory with the following required files:

```
task_xx_name/
├── problem.md
├── interface.md
├── phases.yaml
├── evaluator.py
├── hidden_rules.py
├── tests_public.py
├── tests_hidden.py
└── generator.md
```

### 5.1 problem.md (agent-visible)

**Must describe:**

- the domain and goal,
- input/output types,
- minimal examples (optional),
- statement that requirements evolve across phases.

**Must not include:**

- hidden rules or invariants,
- evaluator internals,
- test cases beyond small illustrative examples (optional).

### 5.2 interface.md (agent-visible)

**Must specify:**

- exact function signature,
- allowed imports (if any),
- runtime constraints (time/memory),
- determinism requirements,
- forbidden behaviors (global state, randomness).

### 5.3 phases.yaml (agent-visible)

Defines phases and rule evolution.

**Schema:**

```yaml
phases:
  - id: <int starting from 0>
    added_rules:
      - <rule_id>
      - <rule_id>
    modified_rules:
      - rule_id: <rule_id>
        modification_type: <one of allowed modification types>
        details: <string, human-readable, agent-visible>
```

**Rules:**

- `added_rules` MUST be non-empty for every phase after phase 0.
- `modified_rules` may be empty.
- `details` must be descriptive but must not reveal hidden tests.

### 5.4 evaluator.py (not agent-visible)

**Implements:**

- loading solution code safely,
- running rule checks for current phase,
- running invariant checks,
- computing coverage,
- computing delta vs previous attempt.

### 5.5 hidden_rules.py (not agent-visible)

Defines invariants and hidden constraints to prevent trivial hacking.

### 5.6 tests_public.py / tests_hidden.py (not agent-visible by default)

Both are evaluator-run tests:

- **public tests**: smoke / sanity / format checks
- **hidden tests**: comprehensive checks, invariants, edge cases

Agents do not see tests in official benchmark runs.

### 5.7 generator.md (for benchmark maintainers)

Instructions to generate additional tasks with LLMs in a consistent style.

---

## 6. Evaluation Protocol

### 6.1 Inputs to the agent

For each phase, the agent is given:

- `problem.md`
- `interface.md`
- current phase rule information from `phases.yaml` (added + modified)
- its own previous attempt(s) if the agent stores them (benchmark does not provide memory)

**The agent is NOT given:**

- tests,
- failing inputs,
- stack traces,
- hidden rules.

### 6.2 Agent outputs

For each attempt, the agent outputs a single code artifact containing the required function.

### 6.3 Evaluator outputs to the agent (structured feedback)

For each attempt, the evaluator returns a JSON feedback object (Section 7).

This is the only feedback channel.

---

## 7. Feedback Schema (Complete Semantics)

### 7.1 Canonical JSON Schema

```json
{
  "phase_id": 2,
  "attempt_id": 7,

  "status": "valid",
  "status_reason": "string",

  "violations": [
    {
      "rule_id": "determinism",
      "scope": "dict_order",
      "count": 3,
      "severity": "error"
    }
  ],

  "rule_summary": {
    "rules_total": 5,
    "rules_satisfied": 4,
    "rules_violated": 1
  },

  "validity_coverage": {
    "value": 0.82,
    "definition": "fraction of evaluation cases in this phase where all phase rules are satisfied"
  },

  "invariants": {
    "checked": 6,
    "satisfied": 5,
    "violated": 1
  },

  "delta_from_previous": {
    "previous_attempt_id": 6,
    "coverage_delta": 0.12,
    "improved_rules": ["normalize_numbers"],
    "regressed_rules": []
  }
}
```

### 7.2 Field-by-field definitions (no ambiguity)

#### phase_id (integer)

Current phase index being evaluated (0-based).

#### attempt_id (integer)

Monotonic attempt number within the entire task run.

#### status (string enum)

One of:

- `valid`: the attempt satisfies ALL phase rules AND all invariants checked for this phase
- `partially_valid`: the attempt satisfies some rules but not all; may still satisfy invariants
- `invalid`: the attempt violates core rules OR triggers fatal invariant violations

Status MUST be consistent with violations:

- If any `severity="error"` violation exists, status cannot be `valid`.

#### status_reason (string)

Human-readable, high-level reason without giving away test cases.

**Examples:**

- "Violates determinism under dictionary traversal."
- "Fails idempotency checks under repeated application."

Must not mention specific inputs or provide stack traces.

#### violations (list)

Each element describes one class of violation.

**Fields:**

- `rule_id`: stable identifier from task rules
- `scope`: coarse bucket label defined by the task author
- `count`: number of evaluation cases (out of the evaluator's internal case set) that violated this rule in this scope
- `severity`: enum `error` | `warning`

**Rules:**

- An `error` indicates a strict violation affecting validity.
- A `warning` indicates non-fatal issues (e.g., suboptimal stability) and must not prevent `valid` unless configured by the task.

#### rule_summary (object)

- `rules_total`: number of phase rules evaluated (including modified ones)
- `rules_satisfied`: count of rules fully satisfied across evaluator internal case set
- `rules_violated`: count of rules that had at least one error violation

**Consistency constraint:**

```
rules_satisfied + rules_violated == rules_total
```

#### validity_coverage (object)

- `value`: float in [0.0, 1.0]
- `definition`: task-provided string defining how coverage is computed

**Canonical definition for all tasks:**

> Coverage is the fraction of evaluation cases for the current phase for which the solution satisfies ALL phase rules.

**Important:**

- Coverage must be computed over a fixed internal set of evaluation cases for the phase.
- The internal set must be deterministic (seeded).

#### invariants (object)

- `checked`: number of invariants evaluated
- `satisfied`: number satisfied
- `violated`: number violated

Invariant failures can affect status:

- If any invariant is designated "fatal" in `hidden_rules.py`, status MUST be `invalid`.

#### delta_from_previous (object)

Compares current attempt to previous attempt.

**Fields:**

- `previous_attempt_id`: integer or null (null for first attempt)
- `coverage_delta`: `current_coverage - previous_coverage`
- `improved_rules`: list of `rule_id`s whose violation count decreased
- `regressed_rules`: list of `rule_id`s whose violation count increased

**Important:**

- Delta must be computed using the same evaluation case sets.
- If previous attempt does not exist, `coverage_delta` must be `null` and lists empty.

---

## 8. Coverage Computation Requirements

To avoid gaming and ambiguity:

1. Each phase defines a **deterministic set of evaluation cases**:
   - mixture of public-like and hidden-like cases
   - not revealed to agent

2. Coverage is computed as:

```
coverage = (# cases passing all rules) / (total cases)
```

3. The evaluator must log:
   - total case count per phase
   - seed used
   - case generation method (for maintainers)

4. Agents never see these details.

---

## 9. Standard Runner Requirements

A benchmark runner must:

1. Load a task

2. For each phase:
   - reveal phase rules to agent
   - accept agent attempts
   - run evaluator for each attempt
   - return structured feedback

3. Collect metrics:
   - attempts to valid per phase
   - final validity
   - regressions
   - cumulative attempts

---

## 10. Standard Metrics Report

The runner must output a JSON report:

```json
{
  "task_id": "task_03_progressive_optimization",
  "agent_id": "claude_code_4_5",
  "phases": [
    {
      "phase_id": 0,
      "attempts_to_valid": 2,
      "best_coverage": 1.0
    }
  ],
  "overall": {
    "total_attempts": 17,
    "final_status": "valid",
    "total_regressions": 3
  }
}
```

---

## 11. Anti-Gaming Requirements

Tasks must include at least one invariant to prevent trivial strategies, such as:

- hardcoding outputs for known examples
- using introspection to access file system / tests
- relying on non-determinism
- time-based behavior

The evaluator must sandbox execution and restrict imports as needed.

---

## 12. Cursor Implementation Notes (Practical)

For Cursor implementation:

- implement a common runner and task loader
- implement one evaluator template that tasks subclass
- require tasks to provide:
  - rule definitions
  - case generation seed
  - allowed scope labels

---

## 13. Minimal Acceptance Criteria for DCP-Bench

DCP-Bench is considered correctly implemented if:

1. agents receive structured feedback exactly per schema
2. phases evolve with non-empty `added_rules`
3. coverage is deterministic
4. tasks can be extended by adding phases without breaking runner
5. multiple agents can be compared using the same metrics report
