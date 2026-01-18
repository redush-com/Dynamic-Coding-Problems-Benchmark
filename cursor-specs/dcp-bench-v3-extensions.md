# DCP-Bench v3: Extensions Specification

## Strategy Sensitivity, Latent Rules, and Beyond Function-Level Tasks

This document defines mandatory extensions to the DCP-Bench MVP required to elevate the benchmark from strong agent evaluation to **research-grade agent intelligence evaluation**.

The extensions address four critical gaps:

1. Strategy-sensitive code change metrics
2. Detection of useless or destructive edits
3. Latent (unknown) rules and hypothesis discovery
4. A roadmap beyond single-function tasks

---

## 1. Diff-Based Code Change Metrics

### 1.1 Motivation

Current metrics reward end-state correctness but are insensitive to:

- chaotic exploration
- repeated full rewrites
- oscillating solutions
- lack of hypothesis-driven refinement

This extension introduces **code-diff-based metrics** to evaluate **how** an agent converges, not only **whether** it converges.

### 1.2 Definitions

#### 1.2.1 Code Snapshot

A **code snapshot** is the full source code submitted by the agent in an attempt.

Snapshots are stored per attempt:

```
Attempt₀ → Code₀
Attempt₁ → Code₁
...
```

#### 1.2.2 Diff Computation

For each attempt `i > 0`, the runner computes a **normalized diff** between `Codeᵢ₋₁` and `Codeᵢ`.

The diff MUST be computed using a deterministic algorithm (e.g., unified diff or AST-based diff).

### 1.3 Required Metrics

Each attempt MUST record the following metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `lines_added` | int | Number of new lines introduced |
| `lines_removed` | int | Number of removed lines |
| `lines_modified` | int | Lines changed in-place |
| `total_lines_changed` | int | Added + removed + modified |
| `relative_change_ratio` | float | `total_lines_changed / total_lines_in_previous_code` |
| `ast_nodes_changed` (optional) | int | Structural changes at AST level |

### 1.4 Phase-Level Aggregates

For each phase, the runner MUST compute:

```json
{
  "mean_change_ratio": 0.12,
  "max_change_ratio": 0.65,
  "total_lines_changed": 87,
  "rewrite_events": 2
}
```

**Rewrite event** is defined as:

```
relative_change_ratio ≥ 0.5
```

### 1.5 Interpretation (Non-Normative)

- **Low change ratio + steady coverage increase** → hypothesis-driven refinement
- **High variance + rewrites** → brute-force or unstable strategy
- **Rewrites late in phase** → poor abstraction retention

---

## 2. Useless and Destructive Edit Detection

### 2.1 Motivation

An agent can:

- rewrite code without improving correctness
- regress solved constraints
- oscillate between incompatible implementations

These behaviors must be **explicitly measured**.

### 2.2 Definitions

#### 2.2.1 Useful Edit

An edit is **useful** if it satisfies at least one of:

- increases coverage
- fixes a previously failing rule
- reduces violation count for any rule

#### 2.2.2 Useless Edit

An edit is **useless** if:

- code diff is non-empty, AND
- no metric in feedback improves

#### 2.2.3 Destructive Edit

An edit is **destructive** if:

- it introduces new rule violations, OR
- reduces coverage, OR
- reintroduces previously fixed failures

### 2.3 Required Metrics

Each attempt MUST include:

```json
{
  "edit_classification": "useful" | "useless" | "destructive",
  "regressions": ["no_mutation"],
  "improvements": ["deterministic"]
}
```

### 2.4 Aggregate Metrics

At task completion:

```json
{
  "useful_edits": 9,
  "useless_edits": 5,
  "destructive_edits": 3,
  "destructive_ratio": 0.18
}
```

### 2.5 Optional Penalties (Configurable)

Benchmarks MAY define soft penalties:

- high useless edit ratio → strategy inefficiency
- destructive edits after phase midpoint → poor memory

**No hard failure MUST be enforced in MVP.**

---

## 3. Latent / Unknown Rule Mechanism

### 3.1 Motivation

Currently, agents always know:

- what rules exist
- what they are called

In real-world programming:

- requirements are often unnamed
- violations appear as symptoms
- rules are inferred gradually

This extension introduces **latent rules**.

### 3.2 Rule Visibility Levels

Each rule MUST define a visibility level:

| Level | Description |
|-------|-------------|
| `explicit` | Rule id and description visible |
| `latent` | Rule enforced but hidden |
| `revealed` | Previously latent rule now explicit |

### 3.3 Latent Rule Feedback Format

When a latent rule fails, feedback MUST include:

```json
{
  "rule_id": "unknown",
  "scope": "nested",
  "count": 4
}
```

**No description is provided.**

### 3.4 Rule Revelation

A latent rule MAY be revealed when:

- coverage plateaus for K attempts, OR
- phase transition occurs, OR
- agent explicitly requests clarification (see v2 Mechanism 3)

Revelation feedback:

```json
{
  "rule_revealed": {
    "rule_id": "no_input_mutation",
    "description": "Input data must not be modified"
  }
}
```

### 3.5 Metrics for Discovery Ability

```json
{
  "latent_rules_total": 3,
  "latent_rules_inferred_before_reveal": 2,
  "attempts_before_first_latent_fix": 4
}
```

This directly measures **requirement inference skill**.

---

## 4. Roadmap Beyond Function-Level Tasks

### 4.1 Motivation

Function-level tasks test:

- algorithmic reasoning
- local correctness

They do NOT test:

- navigation
- architectural reasoning
- localized fixes
- invariant preservation across files

A clear roadmap is required.

### 4.2 Task Level Classification

Introduce **Task Structural Levels**:

| Level | Description |
|-------|-------------|
| **L1** | Single pure function (current MVP) |
| **L2** | Single file, multiple functions |
| **L3** | Small repository (2–5 files) |
| **L4** | Repo + tests + CI expectations |
| **L5** | Long-horizon evolving codebase |

### 4.3 L2–L3 Task Additions (Planned)

Each non-L1 task MUST define:

```yaml
structure:
  entry_points:
    - file: "main.py"
      functions: ["normalize"]
  editable_files:
    - "main.py"
    - "utils.py"
  read_only_files:
    - "tests.py"
```

### 4.4 New Failure Modes

Non-L1 tasks introduce new rules:

- `no_unrelated_changes`
- `preserve_public_api`
- `localized_fix_required`

These rules are ideal candidates for **latent rules**.

### 4.5 Roadmap Commitment (Required)

DCP-Bench MUST explicitly state:

```
Current release evaluates L1 tasks only.
L2 tasks are planned for v2.x.
L3 tasks are planned for v3.x.
```

This prevents misinterpretation of benchmark scope.

---

## 5. Acceptance Criteria for Research-Grade Rating

DCP-Bench reaches research-grade completeness when:

- ✅ Diff-based metrics are recorded per attempt
- ✅ Useless and destructive edits are classified
- ✅ At least one latent rule exists in ≥50% of tasks
- ✅ Metrics explicitly measure requirement discovery
- ✅ Structural task roadmap is fixed and documented

---

## 6. Summary

| Extension | Purpose | Version Target |
|-----------|---------|----------------|
| Diff-Based Metrics | Measure convergence strategy | v3.0 |
| Edit Classification | Detect useless/destructive behavior | v3.0 |
| Latent Rules | Test requirement inference | v3.0 |
| Task Levels L2–L5 | Beyond function-level evaluation | v3.x+ |

These extensions transform DCP-Bench from a correctness benchmark into a **strategy and intelligence benchmark**.
