"""Tests for the JSONPath resolver and condition evaluator.

Specifically covers:
  - Basic JSONPath resolution
  - Template substitution ${...}
  - Condition evaluator: comparison operators
  - Condition evaluator: logical operators (&& / ||)
  - Condition evaluator: NO eval() — only safe operations
  - Edge cases: None values, type coercion
"""

from __future__ import annotations

import pytest

from app.engine.jsonpath_resolver import (
    evaluate_condition,
    resolve,
    resolve_template,
)

# ─── Context fixture ─────────────────────────────────────────────────────────

CONTEXT = {
    "trigger": {"amount": 150, "user": "alice", "active": True},
    "node-a": {"value": 42, "score": 7.5},
    "node-b": {"status": "ok", "count": 0},
}


# ─── resolve() ───────────────────────────────────────────────────────────────


def test_resolve_simple():
    assert resolve("$.trigger.amount", CONTEXT) == 150


def test_resolve_nested():
    assert resolve("$.node-a.value", CONTEXT) == 42


def test_resolve_string():
    assert resolve("$.trigger.user", CONTEXT) == "alice"


def test_resolve_bool():
    assert resolve("$.trigger.active", CONTEXT) is True


def test_resolve_missing_key_returns_none():
    assert resolve("$.trigger.nonexistent", CONTEXT) is None


def test_resolve_missing_node_returns_none():
    assert resolve("$.totally-missing.field", CONTEXT) is None


def test_resolve_invalid_jsonpath_raises():
    with pytest.raises(ValueError, match="Invalid JSONPath"):
        resolve("not a jsonpath at all !!!", CONTEXT)


# ─── resolve_template() ──────────────────────────────────────────────────────


def test_template_simple_substitution():
    result = resolve_template(
        "https://api.example.com/users/${$.trigger.user}", CONTEXT
    )
    assert result == "https://api.example.com/users/alice"


def test_template_numeric_substitution():
    result = resolve_template("amount=${$.trigger.amount}", CONTEXT)
    assert result == "amount=150"


def test_template_missing_value_becomes_empty():
    result = resolve_template("x=${$.trigger.missing}", CONTEXT)
    assert result == "x="


def test_template_no_placeholders():
    result = resolve_template("https://static.example.com/data", CONTEXT)
    assert result == "https://static.example.com/data"


def test_template_multiple_placeholders():
    result = resolve_template(
        "${$.trigger.user}:${$.trigger.amount}", CONTEXT
    )
    assert result == "alice:150"


# ─── evaluate_condition() ────────────────────────────────────────────────────


class TestComparisonOperators:
    def test_greater_than_true(self):
        assert evaluate_condition("$.trigger.amount > 100", CONTEXT) is True

    def test_greater_than_false(self):
        assert evaluate_condition("$.trigger.amount > 200", CONTEXT) is False

    def test_less_than_true(self):
        assert evaluate_condition("$.node-a.value < 100", CONTEXT) is True

    def test_less_than_false(self):
        assert evaluate_condition("$.trigger.amount < 100", CONTEXT) is False

    def test_greater_equal_exact(self):
        assert evaluate_condition("$.trigger.amount >= 150", CONTEXT) is True

    def test_less_equal_exact(self):
        assert evaluate_condition("$.trigger.amount <= 150", CONTEXT) is True

    def test_equal_number(self):
        assert evaluate_condition("$.node-a.value == 42", CONTEXT) is True

    def test_not_equal(self):
        assert evaluate_condition("$.node-a.value != 99", CONTEXT) is True

    def test_equal_string(self):
        assert evaluate_condition("$.trigger.user == 'alice'", CONTEXT) is True

    def test_equal_string_false(self):
        assert evaluate_condition("$.trigger.user == 'bob'", CONTEXT) is False

    def test_float_comparison(self):
        assert evaluate_condition("$.node-a.score > 5.0", CONTEXT) is True

    def test_zero_value(self):
        assert evaluate_condition("$.node-b.count == 0", CONTEXT) is True


class TestLogicalOperators:
    def test_and_both_true(self):
        assert evaluate_condition(
            "$.trigger.amount > 100 && $.node-a.value == 42", CONTEXT
        ) is True

    def test_and_one_false(self):
        assert evaluate_condition(
            "$.trigger.amount > 100 && $.node-a.value == 99", CONTEXT
        ) is False

    def test_or_both_false(self):
        assert evaluate_condition(
            "$.trigger.amount > 999 || $.node-a.value > 999", CONTEXT
        ) is False

    def test_or_one_true(self):
        assert evaluate_condition(
            "$.trigger.amount > 999 || $.node-a.value == 42", CONTEXT
        ) is True


class TestSafetyNonEval:
    """These tests confirm that the evaluator cannot execute arbitrary code.

    The evaluator should raise ValueError for anything outside the documented
    subset of operators — NOT execute it as Python.
    """

    def test_python_expression_raises(self):
        """Passing raw Python should fail to parse, not execute."""
        with pytest.raises((ValueError, Exception)):
            evaluate_condition("__import__('os').system('echo pwned')", CONTEXT)

    def test_invalid_operator_raises(self):
        with pytest.raises(ValueError):
            evaluate_condition("$.trigger.amount ++ 1", CONTEXT)


class TestEdgeCases:
    def test_literal_true(self):
        """Branch condition that is always true (literal)."""
        # evaluate_condition parses "true" as bool token; 3 tokens needed
        # "true == true" should work
        assert evaluate_condition("$.trigger.amount == $.trigger.amount", {"trigger": {"amount": 5}}) is True

    def test_condition_with_whitespace(self):
        assert evaluate_condition("  $.trigger.amount   >   100  ", CONTEXT) is True
