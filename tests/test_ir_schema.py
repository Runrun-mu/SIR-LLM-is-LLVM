"""Tests for IR schema models."""

import pytest
from sir.ir.schema import Edge, EdgeType, Node, NodeKind, Snapshot


class TestNode:
    def test_create_node(self):
        node = Node(id="mod_auth", kind=NodeKind.MODULE, name="Auth")
        assert node.id == "mod_auth"
        assert node.kind == NodeKind.MODULE
        assert node.name == "Auth"
        assert node.description == ""
        assert node.properties == {}

    def test_node_with_properties(self):
        node = Node(
            id="ent_user", kind=NodeKind.ENTITY, name="User",
            description="User entity",
            properties={"fields": ["username", "email"]},
        )
        assert node.properties["fields"] == ["username", "email"]


class TestEdge:
    def test_create_edge_with_alias(self):
        edge = Edge(**{"from": "mod_auth", "to": "cmp_login", "type": "contains"})
        assert edge.from_node == "mod_auth"
        assert edge.to == "cmp_login"
        assert edge.edge_type == EdgeType.CONTAINS

    def test_create_edge_with_field_name(self):
        edge = Edge(from_node="a", to="b", edge_type=EdgeType.DEPENDS_ON)
        assert edge.from_node == "a"
        assert edge.edge_type == EdgeType.DEPENDS_ON

    def test_edge_serialization_by_alias(self):
        edge = Edge(from_node="a", to="b", edge_type=EdgeType.CONTAINS)
        data = edge.model_dump(by_alias=True)
        assert "from" in data
        assert "type" in data
        assert data["from"] == "a"


class TestSnapshot:
    def test_empty_snapshot(self):
        snap = Snapshot()
        assert snap.version == 1
        assert snap.nodes == []
        assert snap.edges == []

    def test_get_node(self):
        n = Node(id="x", kind=NodeKind.SYSTEM, name="X")
        snap = Snapshot(nodes=[n])
        assert snap.get_node("x") == n
        assert snap.get_node("y") is None

    def test_node_ids(self):
        snap = Snapshot(nodes=[
            Node(id="a", kind=NodeKind.MODULE, name="A"),
            Node(id="b", kind=NodeKind.MODULE, name="B"),
        ])
        assert snap.node_ids() == {"a", "b"}

    def test_to_summary(self):
        snap = Snapshot(
            version=2,
            nodes=[Node(id="sys", kind=NodeKind.SYSTEM, name="Demo")],
            edges=[],
        )
        summary = snap.to_summary()
        assert "v2" in summary
        assert "1 nodes" in summary
        assert "Demo" in summary
