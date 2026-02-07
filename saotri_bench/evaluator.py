"""Base evaluator for Saotri Bench tasks."""

from __future__ import annotations

import copy
from abc import ABC
from collections import defaultdict
from typing import Any, Callable

from .models import Phase, RuleResult, TestCase, Violation


class BaseEvaluator(ABC):
    """Base class for task evaluators.

    Each task must implement an Evaluator class that inherits from this.
    The evaluator must implement check_{rule_id} methods for each rule.
    """

    def evaluate(
        self,
        solution_fn: Callable[..., Any],
        test_cases: list[TestCase],
        phase: Phase,
    ) -> tuple[list[Violation], float]:
        """Evaluate solution against all rules in the current phase.

        Args:
            solution_fn: The solution function to test
            test_cases: All test cases (will be filtered by phase)
            phase: Current phase with rules to check

        Returns:
            Tuple of (violations list, coverage ratio)
        """
        # Filter test cases for current phase (include all from previous phases too)
        relevant_tests = [tc for tc in test_cases if tc.phase <= phase.id]

        if not relevant_tests:
            return [], 1.0

        # Track violations per rule and scope
        violation_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # Track which test cases pass all rules
        tests_passed = 0

        for test_case in relevant_tests:
            test_passed_all = True

            for rule in phase.rules:
                # Find the check method for this rule
                check_method = getattr(self, f"check_{rule.id}", None)
                if check_method is None:
                    raise NotImplementedError(
                        f"Evaluator must implement check_{rule.id} method"
                    )

                # Run the check
                try:
                    result = check_method(solution_fn, test_case)
                except Exception:
                    # If check itself fails, count as violation
                    result = RuleResult.failed(scope="error")

                if not result.passed:
                    test_passed_all = False
                    scope = result.scope or "unknown"
                    violation_counts[rule.id][scope] += 1

            if test_passed_all:
                tests_passed += 1

        # Convert to Violation objects
        violations = []
        for rule_id, scopes in violation_counts.items():
            for scope, count in scopes.items():
                violations.append(Violation(rule_id=rule_id, scope=scope, count=count))

        # Calculate coverage
        coverage = tests_passed / len(relevant_tests) if relevant_tests else 1.0

        return violations, coverage

    def get_rules_summary(
        self, violations: list[Violation], phase: Phase
    ) -> tuple[int, int, int]:
        """Get summary of rules passed/failed.

        Returns:
            Tuple of (total, passed, failed)
        """
        total = len(phase.rules)
        failed_rules = set(v.rule_id for v in violations)
        failed = len(failed_rules)
        passed = total - failed
        return total, passed, failed


# Helper functions for common checks


def check_no_mutation(
    solution_fn: Callable[..., Any], test_input: Any
) -> tuple[bool, str | None]:
    """Check if solution mutates the input.

    Returns:
        Tuple of (passed, scope if failed)
    """
    input_copy = copy.deepcopy(test_input)
    solution_fn(input_copy)

    if input_copy == test_input:
        return True, None

    # Determine scope based on mutation type
    if isinstance(input_copy, dict):
        # Check if it's a nested mutation
        for key, value in test_input.items():
            if key in input_copy and input_copy[key] != value:
                if isinstance(value, (dict, list)):
                    return False, "nested"
        return False, "direct"
    elif isinstance(input_copy, list):
        return False, "direct"

    return False, "direct"


def check_deterministic(
    solution_fn: Callable[..., Any], test_input: Any, runs: int = 3
) -> tuple[bool, str | None]:
    """Check if solution is deterministic.

    Returns:
        Tuple of (passed, scope if failed)
    """
    results = []
    for _ in range(runs):
        input_copy = copy.deepcopy(test_input)
        results.append(solution_fn(input_copy))

    if all(r == results[0] for r in results):
        return True, None

    return False, "ordering"
