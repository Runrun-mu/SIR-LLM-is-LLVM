"""Generic passthrough adapter - maps IR nodes to project nodes with path conventions."""

from __future__ import annotations

import re

from sir.adapter.base import Adapter
from sir.adapter.schema import ProjectNode, ProjectSnapshot
from sir.ir.graph import IRGraph
from sir.ir.schema import EdgeType, NodeKind, Snapshot


def _snake(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    s = re.sub(r"[\s\-]+", "_", s)
    return s.lower()


class GenericAdapter(Adapter):
    """1:1 passthrough adapter with path generation based on contains hierarchy."""

    def lower(self, snapshot: Snapshot) -> ProjectSnapshot:
        graph = IRGraph(snapshot)
        project_name = ""
        for n in snapshot.nodes:
            if n.kind == NodeKind.SYSTEM:
                project_name = n.name
                break

        project_nodes: list[ProjectNode] = []
        module_paths: dict[str, str] = {}  # node_id -> module dir name

        # First pass: find module paths
        for node in snapshot.nodes:
            if node.kind == NodeKind.MODULE:
                mod_dir = _snake(node.name)
                module_paths[node.id] = mod_dir

        # Second pass: generate all project nodes
        for node in snapshot.nodes:
            if node.kind == NodeKind.SYSTEM:
                continue

            path = self._resolve_path(node, graph, module_paths)
            project_nodes.append(ProjectNode(
                id=f"proj_{node.id}",
                source_id=node.id,
                kind=node.kind.value,
                name=node.name,
                path=path,
                description=node.description,
                properties=node.properties,
            ))

        return ProjectSnapshot(
            project_name=project_name,
            nodes=project_nodes,
        )

    def _resolve_path(self, node, graph: IRGraph, module_paths: dict[str, str]) -> str:
        snake_name = _snake(node.name)

        # Find parent module
        parent_module = self._find_parent_module(node.id, graph)
        mod_dir = module_paths.get(parent_module, "") if parent_module else ""

        if node.kind == NodeKind.MODULE:
            return f"{snake_name}/"

        if node.kind == NodeKind.COMPONENT:
            if mod_dir:
                return f"{mod_dir}/components/{snake_name}.py"
            return f"components/{snake_name}.py"

        if node.kind == NodeKind.ENTITY:
            if mod_dir:
                return f"{mod_dir}/models.py"
            return "models.py"

        if node.kind == NodeKind.INTERFACE:
            if mod_dir:
                return f"{mod_dir}/services/{snake_name}.py"
            return f"services/{snake_name}.py"

        if node.kind == NodeKind.WORKFLOW:
            if mod_dir:
                return f"{mod_dir}/workflows/{snake_name}.py"
            return f"workflows/{snake_name}.py"

        if node.kind in (NodeKind.CAPABILITY, NodeKind.EVENT, NodeKind.CONSTRAINT):
            if mod_dir:
                return f"{mod_dir}/{snake_name}.py"
            return f"{snake_name}.py"

        return f"{snake_name}.py"

    def _find_parent_module(self, node_id: str, graph: IRGraph) -> str | None:
        """Walk up contains edges to find the parent module."""
        for u, _, d in graph.g.in_edges(node_id, data=True):
            if d.get("edge_type") == EdgeType.CONTAINS:
                kind = graph.g.nodes[u].get("kind")
                if kind == NodeKind.MODULE:
                    return u
                # Recurse up
                result = self._find_parent_module(u, graph)
                if result:
                    return result
        return None
