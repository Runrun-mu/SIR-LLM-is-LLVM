"""Tests for IR graph operations."""

import pytest
from sir.ir.graph import IRGraph
from sir.ir.schema import Edge, EdgeType, Node, NodeKind, Snapshot


def _make_snapshot() -> Snapshot:
    """Create a test snapshot with a simple hierarchy."""
    return Snapshot(
        nodes=[
            Node(id="sys", kind=NodeKind.SYSTEM, name="TestSys"),
            Node(id="mod_auth", kind=NodeKind.MODULE, name="Auth"),
            Node(id="cmp_login", kind=NodeKind.COMPONENT, name="Login"),
            Node(id="ent_user", kind=NodeKind.ENTITY, name="User"),
        ],
        edges=[
            Edge(**{"from": "sys", "to": "mod_auth", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "cmp_login", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "ent_user", "type": "contains"}),
            Edge(**{"from": "cmp_login", "to": "ent_user", "type": "depends_on"}),
        ],
    )


class TestIRGraph:
    def test_build(self):
        snap = _make_snapshot()
        graph = IRGraph(snap)
        assert len(graph.g.nodes) == 4
        assert len(graph.g.edges) == 4

    def test_children(self):
        graph = IRGraph(_make_snapshot())
        children = graph.children("mod_auth")
        assert set(children) == {"cmp_login", "ent_user"}

    def test_ancestors(self):
        graph = IRGraph(_make_snapshot())
        ancestors = graph.ancestors("cmp_login")
        assert ancestors == ["mod_auth"]

    def test_no_contains_cycle(self):
        graph = IRGraph(_make_snapshot())
        assert not graph.has_contains_cycle()

    def test_contains_cycle_detected(self):
        snap = Snapshot(
            nodes=[
                Node(id="a", kind=NodeKind.MODULE, name="A"),
                Node(id="b", kind=NodeKind.MODULE, name="B"),
            ],
            edges=[
                Edge(**{"from": "a", "to": "b", "type": "contains"}),
                Edge(**{"from": "b", "to": "a", "type": "contains"}),
            ],
        )
        graph = IRGraph(snap)
        assert graph.has_contains_cycle()

    def test_orphan_nodes(self):
        snap = Snapshot(
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="Sys"),
                Node(id="orphan", kind=NodeKind.MODULE, name="Orphan"),
            ],
            edges=[],
        )
        graph = IRGraph(snap)
        assert graph.orphan_nodes() == {"orphan"}

    def test_system_not_orphan(self):
        snap = Snapshot(
            nodes=[Node(id="sys", kind=NodeKind.SYSTEM, name="Sys")],
            edges=[],
        )
        graph = IRGraph(snap)
        assert graph.orphan_nodes() == set()

    def test_dangling_edges(self):
        snap = Snapshot(
            nodes=[Node(id="a", kind=NodeKind.MODULE, name="A")],
            edges=[Edge(**{"from": "a", "to": "nonexist", "type": "contains"})],
        )
        graph = IRGraph(snap)
        dangling = graph.dangling_edges()
        assert len(dangling) == 1
