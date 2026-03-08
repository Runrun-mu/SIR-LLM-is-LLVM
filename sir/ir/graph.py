"""NetworkX graph wrapper for IR snapshots."""

from __future__ import annotations

import networkx as nx

from sir.ir.schema import Edge, EdgeType, Node, Snapshot


class IRGraph:
    """Wraps a Snapshot into a NetworkX DiGraph for analysis."""

    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot = snapshot
        self.g = nx.DiGraph()
        self._build()

    def _build(self) -> None:
        for node in self.snapshot.nodes:
            self.g.add_node(node.id, kind=node.kind, name=node.name)
        for edge in self.snapshot.edges:
            self.g.add_edge(
                edge.from_node, edge.to,
                edge_type=edge.edge_type,
            )

    def children(self, node_id: str) -> list[str]:
        return [
            v for _, v, d in self.g.out_edges(node_id, data=True)
            if d.get("edge_type") == EdgeType.CONTAINS
        ]

    def ancestors(self, node_id: str) -> list[str]:
        return [
            u for u, _, d in self.g.in_edges(node_id, data=True)
            if d.get("edge_type") == EdgeType.CONTAINS
        ]

    def contains_subgraph(self) -> nx.DiGraph:
        sg = nx.DiGraph()
        for u, v, d in self.g.edges(data=True):
            if d.get("edge_type") == EdgeType.CONTAINS:
                sg.add_edge(u, v)
        return sg

    def has_contains_cycle(self) -> bool:
        sg = self.contains_subgraph()
        return not nx.is_directed_acyclic_graph(sg)

    def orphan_nodes(self) -> set[str]:
        """Nodes with no edges at all (excluding system root)."""
        from sir.ir.schema import NodeKind
        orphans = set()
        for nid in self.g.nodes:
            if self.g.in_degree(nid) == 0 and self.g.out_degree(nid) == 0:
                kind = self.g.nodes[nid].get("kind")
                if kind != NodeKind.SYSTEM:
                    orphans.add(nid)
        return orphans

    def dangling_edges(self) -> list[Edge]:
        node_ids = self.snapshot.node_ids()
        dangling = []
        for edge in self.snapshot.edges:
            if edge.from_node not in node_ids or edge.to not in node_ids:
                dangling.append(edge)
        return dangling
