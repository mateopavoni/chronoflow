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
import ipaddress
import socket
import ssl
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.engine.jsonpath_resolver import (
    evaluate_condition,
    resolve_mapping_value,
    resolve_template,
    resolve_value,
)
from app.schemas.graph import GraphNode

# ─── Executor registry ──────────────────────────────────────────────────────

# Upper bound on a `delay` node's sleep duration. Without this, an unbounded
# `seconds` value ties up a scheduler task (and the in-process asyncio.Task
# pool) indefinitely — a cheap DoS against the demo's single-process runner.
# A few minutes is generous for demonstrating the ready-set scheduler's
# parallelism while still bounding worst-case run time.
MAX_DELAY_SECONDS = 300  # 5 minutes


def _assert_public_url(url: str) -> None:
    """SSRF guard for the `http` node: block requests to non-public addresses.

    Any authenticated user can point a workflow's `http` node at an arbitrary
    URL, and that request is made *from the server*. Without this check, a
    workflow could reach the Dokku host's internal-only services, the cloud
    metadata endpoint (169.254.169.254), or localhost — a classic SSRF pivot.

    Resolves the hostname and checks every returned address (not just the
    hostname string) since "localhost", decimal/octal IP encodings, or a
    domain that resolves to a private range would all bypass a naive
    string check. Does not fully close DNS-rebinding (the resolved IP could
    change between this check and httpx's own connect) — acceptable for a
    portfolio demo's threat model; revisit with a pinned-resolver transport
    if this ever handles real user data.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"http node: unsupported URL scheme '{parts.scheme}'")
    if not parts.hostname:
        raise ValueError("http node: URL has no hostname")

    try:
        addrinfo = socket.getaddrinfo(parts.hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"http node: could not resolve host '{parts.hostname}'") from exc

    for family, _, _, _, sockaddr in addrinfo:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError(
                f"http node: URL resolves to a non-public address ({ip}) — blocked"
            )

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
    """Transform node: build a new dict by mapping each value to one of 3 forms.

    Config shape: { "mappings": { "outputKey": "<value>" } }

    Each mapping value is resolved as (see resolve_mapping_value):
      - whole-string JSONPath ("$.sourceNode.field")     → typed value, e.g. 100
      - text composed with "$.path" or "${$.path}"       → interpolated string
        ("Hi $.fetch-user.body.name!" and "Hi ${$.fetch-user.body.name}!" both work —
        no need to learn the "${...}" wrapper just to compose a message)
      - plain text with no "$" at all                    → returned unchanged

    Example:
        config.mappings = {
            "name": "$.fetch-user.body.name",
            "greeting": "Hi $.fetch-user.body.name, welcome!",
            "note": "Processed successfully",
        }
        output = { "name": "Alice", "greeting": "Hi Alice, welcome!", "note": "Processed successfully" }
    """
    config = node.data.config
    mappings: dict[str, str] = config.get("mappings", {})

    if not mappings:
        # No mappings configured — pass context through (useful for passthrough nodes)
        return {}

    result: dict[str, Any] = {}
    for out_key, raw_value in mappings.items():
        result[out_key] = resolve_mapping_value(raw_value, context)
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
    _assert_public_url(url)

    # Resolve JSONPath values inside the body dict
    body: dict[str, Any] = {
        k: resolve_value(v, context) for k, v in raw_body.items()
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
            )
    except httpx.TransportError as exc:
        if isinstance(exc.__cause__, ssl.SSLError):
            raise ValueError(
                f"http node: TLS handshake with '{urlsplit(url).hostname}' failed "
                f"({exc.__cause__}) — this is a certificate/SNI problem on the "
                "target server, not ChronoFlow."
            ) from exc
        raise

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

    `seconds` is untrusted (comes from a user-authored workflow config), so
    it's validated here: a negative value is rejected outright (raising
    surfaces as this node's "failed" state via the scheduler, rather than
    silently no-op'ing on asyncio.sleep), and the value is capped at
    MAX_DELAY_SECONDS to bound worst-case run time.
    """
    config = node.data.config
    raw_seconds = config.get("seconds", 1)
    try:
        seconds: float = float(raw_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"delay node: 'seconds' must be a number, got {raw_seconds!r}") from exc
    if seconds < 0:
        raise ValueError(f"delay node: 'seconds' must not be negative (got {seconds})")
    seconds = min(seconds, MAX_DELAY_SECONDS)
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
