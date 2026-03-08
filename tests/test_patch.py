"""Tests for patch schema and engine."""

import pytest
from sir.ir.schema import Edge, Node, NodeKind, Snapshot
from sir.patch.engine import PatchError, apply_patch
from sir.patch.schema import Patch, PatchOperation, PatchOpType


def _base_snapshot() -> Snapshot:
    return Snapshot(
        version=1,
        nodes=[Node(id="sys", kind=NodeKind.SYSTEM, name="Test")],
        edges=[],
    )


class TestPatchSchema:
    def test_create_patch(self):
        patch = Patch(
            description="test patch",
            operations=[
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "mod_a", "kind": "module", "name": "A",
                }),
            ],
        )
        assert len(patch.operations) == 1
        assert patch.operations[0].op == PatchOpType.ADD_NODE


class TestPatchEngine:
    def test_add_node(self):
        snap = _base_snapshot()
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.ADD_NODE, value={
                "id": "mod_auth", "kind": "module", "name": "Auth",
            }),
        ])
        result = apply_patch(snap, patch)
        assert len(result.nodes) == 2
        assert result.version == 2
        assert result.get_node("mod_auth") is not None

    def test_add_node_duplicate_fails(self):
        snap = _base_snapshot()
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.ADD_NODE, value={
                "id": "sys", "kind": "module", "name": "Dup",
            }),
        ])
        with pytest.raises(PatchError, match="already exists"):
            apply_patch(snap, patch)

    def test_remove_node(self):
        snap = Snapshot(
            version=1,
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="Test"),
                Node(id="mod_a", kind=NodeKind.MODULE, name="A"),
            ],
            edges=[Edge(**{"from": "sys", "to": "mod_a", "type": "contains"})],
        )
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.REMOVE_NODE, value={"id": "mod_a"}),
        ])
        result = apply_patch(snap, patch)
        assert len(result.nodes) == 1
        assert len(result.edges) == 0  # Edge also removed

    def test_remove_nonexistent_fails(self):
        snap = _base_snapshot()
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.REMOVE_NODE, value={"id": "ghost"}),
        ])
        with pytest.raises(PatchError, match="not found"):
            apply_patch(snap, patch)

    def test_update_node(self):
        snap = Snapshot(
            version=1,
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="Test"),
                Node(id="mod_a", kind=NodeKind.MODULE, name="A"),
            ],
        )
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.UPDATE_NODE, value={
                "id": "mod_a", "name": "Auth", "description": "Auth module",
            }),
        ])
        result = apply_patch(snap, patch)
        node = result.get_node("mod_a")
        assert node.name == "Auth"
        assert node.description == "Auth module"

    def test_add_edge(self):
        snap = Snapshot(
            version=1,
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="Test"),
                Node(id="mod_a", kind=NodeKind.MODULE, name="A"),
            ],
        )
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.ADD_EDGE, value={
                "from": "sys", "to": "mod_a", "type": "contains",
            }),
        ])
        result = apply_patch(snap, patch)
        assert len(result.edges) == 1

    def test_add_edge_dangling_fails(self):
        snap = _base_snapshot()
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.ADD_EDGE, value={
                "from": "sys", "to": "nonexist", "type": "contains",
            }),
        ])
        with pytest.raises(PatchError, match="not found"):
            apply_patch(snap, patch)

    def test_remove_edge(self):
        snap = Snapshot(
            version=1,
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="Test"),
                Node(id="mod_a", kind=NodeKind.MODULE, name="A"),
            ],
            edges=[Edge(**{"from": "sys", "to": "mod_a", "type": "contains"})],
        )
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.REMOVE_EDGE, value={
                "from": "sys", "to": "mod_a",
            }),
        ])
        result = apply_patch(snap, patch)
        assert len(result.edges) == 0

    def test_multi_operation_patch(self):
        snap = _base_snapshot()
        patch = Patch(
            description="Add auth module with login component",
            operations=[
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "mod_auth", "kind": "module", "name": "Auth",
                }),
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "cmp_login", "kind": "component", "name": "Login",
                    "properties": {"methods": ["authenticate", "logout"]},
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "sys", "to": "mod_auth", "type": "contains",
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "mod_auth", "to": "cmp_login", "type": "contains",
                }),
            ],
        )
        result = apply_patch(snap, patch)
        assert len(result.nodes) == 3
        assert len(result.edges) == 2
        assert result.version == 2

    def test_add_edge_with_from_node_key(self):
        """Test that both 'from' and 'from_node' keys work for add_edge."""
        snap = Snapshot(
            version=1,
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="Test"),
                Node(id="mod_a", kind=NodeKind.MODULE, name="A"),
            ],
        )
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.ADD_EDGE, value={
                "from_node": "sys", "to": "mod_a", "type": "contains",
            }),
        ])
        result = apply_patch(snap, patch)
        assert len(result.edges) == 1
