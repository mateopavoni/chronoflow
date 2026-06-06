"""Node executors — one async function per node type.

Each executor receives:
  - node: the GraphNode being executed
  - context: the accumulated execution context dict (read-only from executor's POV)

Each executor returns a plain dict (the node's output), which the scheduler
stores as context[node.id] for downstream nodes.

Node types and their contracts (from ARCHITECTURE.md §2):
  start     → returns the trigger_payload
  transform → maps JSONPath expressions from context to a new dict
  http      → real async HTTP request via httpx
  delay     → asyncio.sleep(seconds), returns {"waited": seconds}
  branch    → evaluates condition, returns {"result": bool}
  end       → returns accumulated context (or subset)
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.engine.jsonpath_resolver import (
    evaluate_condition,
    resolve,
    resolve_template,
    resolve_value,
)
from app.schemas.graph import GraphNode

# ─── Executor registry ──────────────────────────────────────────────────────

async def execute_node(node: GraphNode, context: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the correct executor based on node.type."""
    executor = _EXECUTORS.get(node.type)
    if executor is None:
        raise ValueError(f"Unknown node type: '{node.type}'")
    return await executor(node, context)


# ─── Individual executors ───────────────────────────────────────────────────

async def _execute_start(node: GraphNode, context: dict[str, Any]) -> dict[str, Any]:
    """Start node: pass through the trigger_payload as its output.

    The scheduler seeds context["trigger"] before running; start just
    echoes it so downstream nodes can reference "$.start.field" as well
    as "$.trigger.field".
    """
    return dict(context.get("trigger", {}))


async def _execute_transform(node: GraphNode, context: dict[str, Any]) -> dict[str, Any]:
    """Transform node: build a new dict by mapping JSONPath expressions.

    Config shape: { "mappings": { "outputKey": "$.sourceNode.field" } }

    Example:
        config.mappings = { "name": "$.fetch-user.body.name", "amount": "$.trigger.amount" }
        output = { "name": "Alice", "amount": 100 }
    """
    config = node.data.config
    mappings: dict[str, str] = config.get("mappings", {})

    if not mappings:
        # No mappings configured — pass context through (useful for passthrough nodes)
        return {}

    result: dict[str, Any] = {}
    for out_key, jsonpath_expr in mappings.items():
        value = resolve(jsonpath_expr, context)
        result[out_key] = value
    return result


async def _execute_http(node: GraphNode, context: dict[str, Any]) -> dict[str, Any]:
    """HTTP node: performs a real async HTTP request via httpx.

    Config shape:
        { "method": "GET", "url": "https://...", "headers": {}, "body": {} }

    URL and body values support template substitution: "${$.node.field}".
    Headers are passed as-is (no template substitution — rarely needed for demos).

    Returns: { "status": <int>, "body": <json> }

    Error handling:
      - Network errors → raise (scheduler will mark node as failed)
      - Non-2xx responses → still returned as output (caller decides semantics)
      - Timeout (10s) → httpx.TimeoutException propagates
    """
    config = node.data.config
    method: str = config.get("method", "GET").upper()
    raw_url: str = config.get("url", "")
    headers: dict[str, str] = config.get("headers", {})
    raw_body: dict[str, Any] = config.get("body", {})

    # Resolve template placeholders in URL
    url = resolve_template(raw_url, context)

    # Resolve JSONPath values inside the body dict
    body: dict[str, Any] = {
        k: resolve_value(v, context) for k, v in raw_body.items()
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=body if body else None,
        )

    try:
        response_body = response.json()
    except Exception:
        # If the response is not JSON, return it as a string
        response_body = response.text

    return {"status": response.status_code, "body": response_body}


async def _execute_delay(node: GraphNode, context: dict[str, Any]) -> dict[str, Any]:
    """Delay node: sleep for `seconds` to demonstrate async parallelism.

    Config shape: { "seconds": <number> }

    A concrete example: two parallel delay branches (3s + 1s) finish
    in ~3s total (max), not 4s (sum). This is the concrete proof of the
    ready-set scheduler working correctly.
    """
    config = node.data.config
    seconds: float = float(config.get("seconds", 1))
    await asyncio.sleep(seconds)
    return {"waited": seconds}


async def _execute_branch(node: GraphNode, context: dict[str, Any]) -> dict[str, Any]:
    """Branch node: evaluate a condition and route accordingly.

    Config shape: { "condition": "$.node-x.value > 10" }

    Returns { "result": bool } so the scheduler can use it to decide
    which outgoing edges to follow (true branch vs false branch).

    The condition evaluator is hand-written — no eval() — see jsonpath_resolver.py.
    """
    config = node.data.config
    condition: str = config.get("condition", "true")
    result = evaluate_condition(condition, context)
    return {"result": bool(result)}


async def _execute_end(node: GraphNode, context: dict[str, Any]) -> dict[str, Any]:
    """End node: collect and return the accumulated context as the final payload.

    This is what gets stored as WorkflowRun.final_payload.
    We exclude the internal "trigger" key from the output to keep it clean,
    but keep all node outputs.
    """
    # Return a copy without internal "trigger" key so final_payload is tidy
    return {k: v for k, v in context.items() if k != "trigger"}


# ─── Dispatch table ─────────────────────────────────────────────────────────

_EXECUTORS = {
    "start": _execute_start,
    "transform": _execute_transform,
    "http": _execute_http,
    "delay": _execute_delay,
    "branch": _execute_branch,
    "end": _execute_end,
}
