"""JSONPath resolver and condition evaluator.

Two public functions:
  - resolve(expression, context)  → resolves a JSONPath like "$.node-x.field"
  - resolve_template(template, context)  → substitutes "${$.node.field}" in strings
  - evaluate_condition(condition, context)  → evaluates "$.a.val > 10" safely (NO eval)

Security note:
  We intentionally do NOT use Python's `eval()` for conditions.
  The evaluator is a hand-written parser that only supports the documented
  operators (> < >= <= == != && ||). This means we never execute arbitrary
  user-supplied Python — a critical security property for any system that
  runs user-defined code.

Supported condition syntax:
  <expr> <op> <expr>  where expr = JSONPath | number | bool literal | quoted string
  Logical: <cond> && <cond>  |  <cond> || <cond>  (single-level, no nested parens)
"""

from __future__ import annotations

import re
from typing import Any

from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

# ─── JSONPath resolution ────────────────────────────────────────────────────


def resolve(expression: str, context: dict[str, Any]) -> Any:
    """Resolve a JSONPath expression against the execution context dict.

    Args:
        expression: A JSONPath like "$.fetch-user.body.name"
        context: The accumulated execution context (node_id → output).

    Returns:
        The matched value, or None if not found.

    Raises:
        ValueError: If the expression is syntactically invalid JSONPath.
    """
    try:
        parsed = jsonpath_parse(expression)
    except JsonPathParserError as exc:
        raise ValueError(f"Invalid JSONPath '{expression}': {exc}") from exc

    matches = parsed.find(context)
    if not matches:
        return None
    # Return the first match; multi-match is unusual in our schema
    return matches[0].value


def resolve_template(template: str, context: dict[str, Any]) -> str:
    """Substitute all ${...} placeholders in a string with resolved values.

    Example:
        template = "https://api.example.com/users/${$.trigger.user_id}"
        result   = "https://api.example.com/users/42"
    """
    pattern = re.compile(r"\$\{([^}]+)\}")

    def replacer(match: re.Match) -> str:
        expr = match.group(1).strip()
        value = resolve(expr, context)
        if value is None:
            return ""
        return str(value)

    return pattern.sub(replacer, template)


def resolve_value(raw: Any, context: dict[str, Any]) -> Any:
    """If raw is a string starting with '$', treat it as a JSONPath and resolve.

    Otherwise return the raw value. Used by the http executor for body values.
    """
    if isinstance(raw, str) and raw.startswith("$"):
        return resolve(raw, context)
    return raw


# ─── Condition evaluator ────────────────────────────────────────────────────

# Supported binary comparison operators
_COMPARISON_OPS = {">=", "<=", "!=", ">", "<", "=="}

# Tokenizer: captures JSONPath expressions, operators, numbers, strings, bools
_TOKEN_RE = re.compile(
    r"""
    (\$\.[^\s><=!&|]+)      # JSONPath expression starting with $.
    | (>=|<=|!=|>|<|==)     # comparison operator
    | (\|\||&&)              # logical operator
    | (true|false)           # boolean literal
    | "([^"]*)"              # double-quoted string
    | '([^']*)'              # single-quoted string
    | (-?\d+(?:\.\d+)?)      # number (int or float)
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _tokenize(expression: str) -> list[tuple[str, Any]]:
    """Break the condition string into typed tokens.

    Returns list of (kind, value) pairs where kind is one of:
    'jsonpath', 'op', 'logical', 'bool', 'string', 'number'.
    """
    tokens: list[tuple[str, Any]] = []
    pos = 0
    expr = expression.strip()
    while pos < len(expr):
        # Skip whitespace
        if expr[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(expr, pos)
        if m is None:
            raise ValueError(
                f"Unrecognized token in condition at position {pos}: "
                f"'{expr[pos:pos+10]}...'"
            )
        jsonpath, op, logical, bool_lit, dq_str, sq_str, number = m.groups()
        if jsonpath is not None:
            tokens.append(("jsonpath", jsonpath))
        elif op is not None:
            tokens.append(("op", op))
        elif logical is not None:
            tokens.append(("logical", logical))
        elif bool_lit is not None:
            tokens.append(("bool", bool_lit.lower() == "true"))
        elif dq_str is not None:
            tokens.append(("string", dq_str))
        elif sq_str is not None:
            tokens.append(("string", sq_str))
        elif number is not None:
            tokens.append(("number", float(number) if "." in number else int(number)))
        pos = m.end()
    return tokens


def _resolve_token(token: tuple[str, Any], context: dict[str, Any]) -> Any:
    """Resolve a token to a Python value."""
    kind, value = token
    if kind == "jsonpath":
        return resolve(value, context)
    # bool, string, number → return directly
    return value


def _compare(left: Any, op: str, right: Any) -> bool:
    """Apply a comparison operator.

    We coerce both sides to float if possible to handle numeric comparisons
    like "$.score > 10" where the stored value is an int.
    """
    # Attempt numeric coercion for ordered comparisons
    if op in (">", "<", ">=", "<="):
        try:
            l_num = float(left)  # type: ignore[arg-type]
            r_num = float(right)  # type: ignore[arg-type]
            left, right = l_num, r_num
        except (TypeError, ValueError):
            pass  # fall through to raw comparison (might raise, which is fine)

    if op == ">":
        return left > right  # type: ignore[operator]
    if op == "<":
        return left < right  # type: ignore[operator]
    if op == ">=":
        return left >= right  # type: ignore[operator]
    if op == "<=":
        return left <= right  # type: ignore[operator]
    if op == "==":
        # Try numeric equality first (e.g. int 10 == float 10.0)
        try:
            return float(left) == float(right)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return left == right
    if op == "!=":
        try:
            return float(left) != float(right)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return left != right
    raise ValueError(f"Unsupported operator: '{op}'")


def _evaluate_simple(tokens: list[tuple[str, Any]], context: dict[str, Any]) -> bool:
    """Evaluate a simple expression: <value> <op> <value>.

    Exactly 3 tokens expected: left, operator, right.
    """
    if len(tokens) != 3:
        raise ValueError(
            f"Expected <value> <op> <value> (3 tokens), got {len(tokens)} tokens: {tokens}"
        )
    left_tok, op_tok, right_tok = tokens
    if op_tok[0] != "op":
        raise ValueError(f"Expected comparison operator, got '{op_tok}'")

    left = _resolve_token(left_tok, context)
    right = _resolve_token(right_tok, context)
    return _compare(left, op_tok[1], right)


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Safely evaluate a branch condition string against the execution context.

    Supported patterns:
      "$.node.field > 10"
      "$.a.x == 'hello'"
      "$.a.val >= 5 && $.b.active == true"
      "$.a.val > 0 || $.b.flag == false"

    This is NOT eval(). It is a hand-written tokenizer + comparator.
    The only things that can "execute" here are our own _compare() calls.

    Args:
        condition: The condition string from branch node config.
        context: The execution context dict.

    Returns:
        bool — result of the condition.

    Raises:
        ValueError: If the condition is syntactically invalid.
    """
    tokens = _tokenize(condition)

    # Find logical operator positions (&&, ||)
    logical_positions = [i for i, t in enumerate(tokens) if t[0] == "logical"]

    if not logical_positions:
        # Simple expression: left op right
        return _evaluate_simple(tokens, context)

    if len(logical_positions) > 1:
        raise ValueError(
            "Compound conditions with more than one logical operator are not supported. "
            "Use separate branch nodes for complex logic."
        )

    # Single && or ||
    pos = logical_positions[0]
    logical_op = tokens[pos][1]
    left_tokens = tokens[:pos]
    right_tokens = tokens[pos + 1 :]

    left_result = _evaluate_simple(left_tokens, context)
    right_result = _evaluate_simple(right_tokens, context)

    if logical_op == "&&":
        return left_result and right_result
    if logical_op == "||":
        return left_result or right_result

    raise ValueError(f"Unknown logical operator: '{logical_op}'")
