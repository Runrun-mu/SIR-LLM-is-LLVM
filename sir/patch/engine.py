"""Patch apply engine - applies patches to snapshots."""

from __future__ import annotations

from sir.ir.schema import Edge, Node, Snapshot
from sir.patch.schema import Patch, PatchOpType


class PatchError(Exception):
    pass


def apply_patch(snapshot: Snapshot, patch: Patch) -> Snapshot:
    """Apply a patch to a snapshot, returning a new snapshot."""
    nodes = list(snapshot.nodes)
    edges = list(snapshot.edges)

    for op in patch.operations:
        if op.op == PatchOpType.ADD_NODE:
            node = Node(**op.value)
            if any(n.id == node.id for n in nodes):
                raise PatchError(f"Node already exists: {node.id}")
            nodes.append(node)

        elif op.op == PatchOpType.REMOVE_NODE:
            node_id = op.value.get("id") or op.path
            before = len(nodes)
            nodes = [n for n in nodes if n.id != node_id]
            if len(nodes) == before:
                raise PatchError(f"Node not found for removal: {node_id}")
            # Also remove edges referencing this node
            edges = [
                e for e in edges
                if e.from_node != node_id and e.to != node_id
            ]

        elif op.op == PatchOpType.UPDATE_NODE:
            node_id = op.value.get("id") or op.path
            found = False
            for i, n in enumerate(nodes):
                if n.id == node_id:
                    update_data = {k: v for k, v in op.value.items() if k != "id"}
                    nodes[i] = n.model_copy(update=update_data)
                    found = True
                    break
            if not found:
                raise PatchError(f"Node not found for update: {node_id}")

        elif op.op == PatchOpType.ADD_EDGE:
            edge_data = dict(op.value)
            # Normalize: accept both "from" and "from_node"
            if "from_node" in edge_data and "from" not in edge_data:
                edge_data["from"] = edge_data.pop("from_node")
            elif "from_node" in edge_data:
                edge_data.pop("from_node")
            edge = Edge(**edge_data)
            node_ids = {n.id for n in nodes}
            if edge.from_node not in node_ids:
                raise PatchError(f"Edge source not found: {edge.from_node}")
            if edge.to not in node_ids:
                raise PatchError(f"Edge target not found: {edge.to}")
            edges.append(edge)

        elif op.op == PatchOpType.REMOVE_EDGE:
            from_node = op.value.get("from") or op.value.get("from_node", "")
            to = op.value.get("to", "")
            before = len(edges)
            edges = [
                e for e in edges
                if not (e.from_node == from_node and e.to == to)
            ]
            if len(edges) == before:
                raise PatchError(f"Edge not found for removal: {from_node} -> {to}")

        else:
            raise PatchError(f"Unknown operation: {op.op}")

    return Snapshot(
        version=snapshot.version + 1,
        nodes=nodes,
        edges=edges,
        metadata=snapshot.metadata,
    )
