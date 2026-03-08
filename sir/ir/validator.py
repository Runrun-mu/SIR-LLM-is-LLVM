"""Graph validation rules for IR snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field

from sir.ir.graph import IRGraph
from sir.ir.schema import NodeKind, Snapshot


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_snapshot(snapshot: Snapshot) -> ValidationResult:
    result = ValidationResult()
    graph = IRGraph(snapshot)

    # Check unique system node
    system_nodes = [n for n in snapshot.nodes if n.kind == NodeKind.SYSTEM]
    if len(system_nodes) == 0:
        result.add_error("No system node found")
    elif len(system_nodes) > 1:
        result.add_error(f"Multiple system nodes found: {[n.id for n in system_nodes]}")

    # Check unique node IDs
    ids = [n.id for n in snapshot.nodes]
    seen: set[str] = set()
    for nid in ids:
        if nid in seen:
            result.add_error(f"Duplicate node ID: {nid}")
        seen.add(nid)

    # Check dangling edges
    for edge in graph.dangling_edges():
        result.add_error(
            f"Dangling edge: {edge.from_node} -> {edge.to} "
            f"(type={edge.edge_type.value})"
        )

    # Check contains DAG
    if graph.has_contains_cycle():
        result.add_error("Contains edges form a cycle")

    # Check orphan nodes
    orphans = graph.orphan_nodes()
    if orphans:
        result.add_warning(f"Orphan nodes (no edges): {orphans}")

    return result
