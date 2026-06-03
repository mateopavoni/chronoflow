"""DAG Validator — enforces the 6 rules from ARCHITECTURE.md §2.

Rules:
  1. Exactly one `start` node.
  2. At least one `end` node.
  3. Acyclic (DFS cycle detection → ValidationError).
  4. All non-start nodes reachable from start.
  5. Each `branch` node must have exactly one outgoing edge labeled "true"
     and one labeled "false".
  6. JSONPath references to node ids that don't exist → warning (not error).

Returns ValidationResult so the caller can decide whether to 422 or just warn.
"""

from __future__ import annotations

from collections import defaultdict

from app.schemas.graph import Graph
from app.schemas.workflow import ValidationResult


def validate_graph(graph: Graph) -> ValidationResult:
    """Validate the DAG and return a ValidationResult."""
    errors: list[str] = []
    warnings: list[str] = []

    node_ids = {n.id for n in graph.nodes}

    # --- Rule 1: exactly one start node -----------------------------------
    start_nodes = [n for n in graph.nodes if n.type == "start"]
    if len(start_nodes) == 0:
        errors.append("The graph must have exactly one 'start' node (found 0).")
    elif len(start_nodes) > 1:
        ids = ", ".join(n.id for n in start_nodes)
        errors.append(f"The graph must have exactly one 'start' node (found {len(start_nodes)}: {ids}).")

    # --- Rule 2: at least one end node ------------------------------------
    end_nodes = [n for n in graph.nodes if n.type == "end"]
    if len(end_nodes) == 0:
        errors.append("The graph must have at least one 'end' node (found 0).")

    # --- Build adjacency for rules 3, 4, 5 --------------------------------
    # adjacency: source -> list of (target, edge)
    adjacency: dict[str, list[str]] = defaultdict(list)
    # outgoing edges per node (for branch validation)
    outgoing_edges: dict[str, list] = defaultdict(list)

    for edge in graph.edges:
        if edge.source not in node_ids:
            errors.append(f"Edge '{edge.id}' references unknown source node '{edge.source}'.")
        if edge.target not in node_ids:
            errors.append(f"Edge '{edge.id}' references unknown target node '{edge.target}'.")
        adjacency[edge.source].append(edge.target)
        outgoing_edges[edge.source].append(edge)

    # --- Rule 3: acyclic (DFS with coloring) ------------------------------
    # 0=unvisited, 1=in-progress, 2=done
    color: dict[str, int] = {nid: 0 for nid in node_ids}
    cycle_found = False

    def dfs_cycle(node: str) -> None:
        nonlocal cycle_found
        if cycle_found:
            return
        color[node] = 1
        for neighbor in adjacency.get(node, []):
            if color.get(neighbor) == 1:
                cycle_found = True
                errors.append(
                    f"Cycle detected: node '{neighbor}' is visited twice during DFS "
                    f"(back-edge from '{node}')."
                )
                return
            if color.get(neighbor) == 0:
                dfs_cycle(neighbor)
        color[node] = 2

    for nid in node_ids:
        if color[nid] == 0:
            dfs_cycle(nid)
            if cycle_found:
                break  # one cycle error is enough — further traversal may be inconsistent

    # --- Rule 4: all non-start nodes reachable from start -----------------
    if len(start_nodes) == 1 and not cycle_found:
        start_id = start_nodes[0].id
        visited: set[str] = set()
        stack = [start_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    stack.append(neighbor)

        unreachable = node_ids - visited - {start_id}
        if unreachable:
            ids_str = ", ".join(sorted(unreachable))
            errors.append(
                f"Nodes unreachable from 'start': {ids_str}. "
                "Every node must be on a path from start."
            )

    # --- Rule 5: branch nodes must have true/false edges ------------------
    for node in graph.nodes:
        if node.type != "branch":
            continue
        edges_out = outgoing_edges.get(node.id, [])
        branch_labels = {
            e.data.branch
            for e in edges_out
            if e.data is not None and e.data.branch is not None
        }
        if "true" not in branch_labels:
            errors.append(
                f"Branch node '{node.id}' is missing an outgoing edge labeled 'true'."
            )
        if "false" not in branch_labels:
            errors.append(
                f"Branch node '{node.id}' is missing an outgoing edge labeled 'false'."
            )

    # --- Rule 6: JSONPath references to unknown nodes (warnings) ----------
    import re

    jsonpath_node_ref = re.compile(r"\$\.([a-zA-Z0-9_-]+)")

    for node in graph.nodes:
        config = node.data.config or {}
        config_str = str(config)
        for match in jsonpath_node_ref.finditer(config_str):
            referenced = match.group(1)
            # "trigger" is the special key for the run's trigger_payload
            if referenced != "trigger" and referenced not in node_ids:
                warnings.append(
                    f"Node '{node.id}' references '$.{referenced}' in its config, "
                    f"but no node with id '{referenced}' exists in the graph."
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
