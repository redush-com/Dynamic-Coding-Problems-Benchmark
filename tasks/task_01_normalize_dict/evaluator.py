"""Evaluator for task_01_normalize_dict."""

from __future__ import annotations

import copy
from typing import Any, Callable

from saotri_bench.evaluator import BaseEvaluator
from saotri_bench.models import RuleResult, TestCase


class Evaluator(BaseEvaluator):
    """Evaluator for the normalize_dict task."""

    def check_correct_output(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if output matches expected."""
        input_copy = copy.deepcopy(test_case.input)
        result = solution_fn(input_copy)

        if result == test_case.expected:
            return RuleResult.success()

        scope = test_case.tags[0] if test_case.tags else "unknown"
        return RuleResult.failed(scope=scope)

    def check_no_mutation(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if input was mutated."""
        # Use a copy so that test_case.input is never corrupted
        input_copy = copy.deepcopy(test_case.input)
        solution_fn(input_copy)

        if self._deep_equals(input_copy, test_case.input):
            return RuleResult.success()

        # Determine if mutation is direct or nested
        scope = self._classify_mutation(input_copy, test_case.input)
        return RuleResult.failed(scope=scope)

    def check_deterministic(
        self, solution_fn: Callable[..., Any], test_case: TestCase
    ) -> RuleResult:
        """Check if function is deterministic."""
        results = []
        for _ in range(3):
            input_copy = copy.deepcopy(test_case.input)
            results.append(solution_fn(input_copy))

        if all(self._deep_equals(r, results[0]) for r in results):
            return RuleResult.success()

        return RuleResult.failed(scope="dict_ordering")

    def _deep_equals(self, a: Any, b: Any) -> bool:
        """Deep equality check that handles nested structures."""
        if type(a) != type(b):
            return False
        if isinstance(a, dict):
            if set(a.keys()) != set(b.keys()):
                return False
            return all(self._deep_equals(a[k], b[k]) for k in a)
        if isinstance(a, list):
            if len(a) != len(b):
                return False
            return all(self._deep_equals(x, y) for x, y in zip(a, b))
        return a == b

    def _classify_mutation(self, current: Any, original: Any) -> str:
        """Classify whether mutation is direct or nested."""
        if not isinstance(current, dict) or not isinstance(original, dict):
            return "direct"

        # Check if top-level keys changed
        if set(current.keys()) != set(original.keys()):
            return "direct"

        # Check if any top-level value changed type or direct value
        for key in current:
            curr_val = current[key]
            orig_val = original[key]
            if type(curr_val) != type(orig_val):
                return "direct"
            if not isinstance(curr_val, (dict, list)) and curr_val != orig_val:
                return "direct"

        # If we got here, mutation is in nested structure
        return "nested"
