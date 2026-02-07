"""Evaluator for task_00_filter_numbers."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the filter_numbers task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if output matches expected."""
        # Make a copy to avoid mutation issues
        input_copy = copy.deepcopy(test_case.input)
        result = solution_fn(input_copy)

        if result == test_case.expected:
            return RuleResult.success()

        # Determine scope from test case tags
        scope = test_case.tags[0] if test_case.tags else "unknown"
        return RuleResult.failed(scope=scope)

    def check_no_mutation(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if input was mutated."""
        # Use a copy so that test_case.input is never corrupted
        input_copy = copy.deepcopy(test_case.input)
        solution_fn(input_copy)

        if input_copy == test_case.input:
            return RuleResult.success()

        return RuleResult.failed(scope="direct")

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if function is deterministic."""
        results = []
        for _ in range(3):
            input_copy = copy.deepcopy(test_case.input)
            results.append(solution_fn(input_copy))

        if all(r == results[0] for r in results):
            return RuleResult.success()

        return RuleResult.failed(scope="ordering")
