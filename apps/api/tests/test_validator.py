"""Tests for the DAG validator (app/engine/validator.py).

Covers all 6 rules from ARCHITECTURE.md §2:
  1. Exactly one start node
  2. At least one end node
  3. Acyclic (cycle detection)
  4. All nodes reachable from start
  5. Branch nodes have true/false edges
  6. JSONPath references to nonexistent nodes → warning
"""

from __future__ import annotations

from app.engine.validator import validate_graph
from app.schemas.graph import Graph

# ─── Helpers ─────────────────────────────────────────────────────────────────


def make_graph(nodes: list[dict], edges: list[dict]) -> Graph:
    return Graph.model_validate({"nodes": nodes, "edges": edges})


def _node(id: str, type: str, config: dict = {}) -> dict:
    return {
        "id": id,
        "type": type,
        "position": {"x": 0, "y": 0},
        "data": {"label": id, "config": config},
    }


def _edge(id: str, src: str, tgt: str, branch: str | None = None) -> dict:
    d = {"id": id, "source": src, "target": tgt}
    if branch is not None:
        d["data"] = {"branch": branch}
    return d


# ─── Rule 1: exactly one start ────────────────────────────────────────────────


def test_no_start_node():
    graph = make_graph(
        [_node("a", "transform"), _node("b", "end")],
        [_edge("e1", "a", "b")],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("start" in e.lower() for e in result.errors)


def test_multiple_start_nodes():
    graph = make_graph(
        [_node("s1", "start"), _node("s2", "start"), _node("e", "end")],
        [_edge("e1", "s1", "e"), _edge("e2", "s2", "e")],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("start" in e.lower() for e in result.errors)


def test_exactly_one_start():
    graph = make_graph(
        [_node("start", "start"), _node("end", "end")],
        [_edge("e1", "start", "end")],
    )
    result = validate_graph(graph)
    assert result.valid
    assert result.errors == []


# ─── Rule 2: at least one end ─────────────────────────────────────────────────


def test_no_end_node():
    graph = make_graph(
        [_node("start", "start"), _node("t", "transform")],
        [_edge("e1", "start", "t")],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("end" in e.lower() for e in result.errors)


# ─── Rule 3: acyclic ──────────────────────────────────────────────────────────


def test_cycle_detected():
    """A → B → C → B creates a cycle."""
    graph = make_graph(
        [
            _node("start", "start"),
            _node("a", "transform"),
            _node("b", "transform"),
            _node("end", "end"),
        ],
        [
            _edge("e1", "start", "a"),
            _edge("e2", "a", "b"),
            _edge("e3", "b", "a"),  # cycle!
            _edge("e4", "b", "end"),
        ],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("cycle" in e.lower() for e in result.errors)


def test_self_loop_is_a_cycle():
    graph = make_graph(
        [_node("start", "start"), _node("loop", "transform"), _node("end", "end")],
        [
            _edge("e1", "start", "loop"),
            _edge("e2", "loop", "loop"),  # self-loop
            _edge("e3", "loop", "end"),
        ],
    )
    result = validate_graph(graph)
    assert not result.valid


def test_dag_with_multiple_paths_is_valid():
    """Diamond shape: start → (a, b) → end is a valid DAG."""
    graph = make_graph(
        [
            _node("start", "start"),
            _node("a", "delay", {"seconds": 1}),
            _node("b", "delay", {"seconds": 2}),
            _node("end", "end"),
        ],
        [
            _edge("e1", "start", "a"),
            _edge("e2", "start", "b"),
            _edge("e3", "a", "end"),
            _edge("e4", "b", "end"),
        ],
    )
    result = validate_graph(graph)
    assert result.valid


# ─── Rule 4: reachability ─────────────────────────────────────────────────────


def test_unreachable_node():
    """Isolated node 'orphan' is not connected from start."""
    graph = make_graph(
        [
            _node("start", "start"),
            _node("end", "end"),
            _node("orphan", "transform"),
        ],
        [
            _edge("e1", "start", "end"),
            # 'orphan' has no incoming edge from start or end
        ],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("unreachable" in e.lower() for e in result.errors)


# ─── Rule 5: branch edges ─────────────────────────────────────────────────────


def test_branch_missing_true_edge():
    graph = make_graph(
        [
            _node("start", "start"),
            _node("br", "branch", {"condition": "$.trigger.x > 0"}),
            _node("end", "end"),
        ],
        [
            _edge("e1", "start", "br"),
            _edge("e2", "br", "end", branch="false"),  # missing true
        ],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("true" in e.lower() for e in result.errors)


def test_branch_missing_false_edge():
    graph = make_graph(
        [
            _node("start", "start"),
            _node("br", "branch", {"condition": "$.trigger.x > 0"}),
            _node("end", "end"),
        ],
        [
            _edge("e1", "start", "br"),
            _edge("e2", "br", "end", branch="true"),  # missing false
        ],
    )
    result = validate_graph(graph)
    assert not result.valid
    assert any("false" in e.lower() for e in result.errors)


def test_branch_valid():
    graph = make_graph(
        [
            _node("start", "start"),
            _node("br", "branch", {"condition": "$.trigger.x > 0"}),
            _node("pos", "end"),
            _node("neg", "end"),
        ],
        [
            _edge("e1", "start", "br"),
            _edge("e2", "br", "pos", branch="true"),
            _edge("e3", "br", "neg", branch="false"),
        ],
    )
    result = validate_graph(graph)
    assert result.valid


# ─── Rule 6: JSONPath warnings ────────────────────────────────────────────────


def test_jsonpath_reference_to_unknown_node_is_warning():
    graph = make_graph(
        [
            _node("start", "start"),
            _node(
                "t",
                "transform",
                {"mappings": {"x": "$.nonexistent-node.value"}},
            ),
            _node("end", "end"),
        ],
        [_edge("e1", "start", "t"), _edge("e2", "t", "end")],
    )
    result = validate_graph(graph)
    # Valid (no hard errors) but has a warning
    assert result.valid
    assert len(result.warnings) > 0
    assert any("nonexistent-node" in w for w in result.warnings)


def test_jsonpath_reference_to_trigger_is_not_a_warning():
    """$.trigger is a reserved key (the run's trigger_payload), not a node."""
    graph = make_graph(
        [
            _node("start", "start"),
            _node("t", "transform", {"mappings": {"val": "$.trigger.amount"}}),
            _node("end", "end"),
        ],
        [_edge("e1", "start", "t"), _edge("e2", "t", "end")],
    )
    result = validate_graph(graph)
    assert result.valid
    # "trigger" should NOT generate a warning
    assert not any("trigger" in w for w in result.warnings)
