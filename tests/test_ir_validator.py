"""Tests for snapshot validation."""

import pytest
from sir.ir.schema import Edge, Node, NodeKind, Snapshot
from sir.ir.validator import validate_snapshot


class TestValidateSnapshot:
    def test_valid_snapshot(self):
        snap = Snapshot(
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="Sys"),
                Node(id="mod", kind=NodeKind.MODULE, name="Mod"),
            ],
            edges=[Edge(**{"from": "sys", "to": "mod", "type": "contains"})],
        )
        result = validate_snapshot(snap)
        assert result.valid
        assert len(result.errors) == 0

    def test_no_system_node(self):
        snap = Snapshot(
            nodes=[Node(id="mod", kind=NodeKind.MODULE, name="Mod")],
        )
        result = validate_snapshot(snap)
        assert not result.valid
        assert any("No system node" in e for e in result.errors)

    def test_multiple_system_nodes(self):
        snap = Snapshot(
            nodes=[
                Node(id="sys1", kind=NodeKind.SYSTEM, name="S1"),
                Node(id="sys2", kind=NodeKind.SYSTEM, name="S2"),
            ],
        )
        result = validate_snapshot(snap)
        assert not result.valid
        assert any("Multiple system" in e for e in result.errors)

    def test_duplicate_node_ids(self):
        snap = Snapshot(
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="S"),
                Node(id="dup", kind=NodeKind.MODULE, name="A"),
                Node(id="dup", kind=NodeKind.MODULE, name="B"),
            ],
        )
        result = validate_snapshot(snap)
        assert not result.valid
        assert any("Duplicate" in e for e in result.errors)

    def test_dangling_edge(self):
        snap = Snapshot(
            nodes=[Node(id="sys", kind=NodeKind.SYSTEM, name="S")],
            edges=[Edge(**{"from": "sys", "to": "ghost", "type": "contains"})],
        )
        result = validate_snapshot(snap)
        assert not result.valid
        assert any("Dangling" in e for e in result.errors)

    def test_contains_cycle(self):
        snap = Snapshot(
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="S"),
                Node(id="a", kind=NodeKind.MODULE, name="A"),
                Node(id="b", kind=NodeKind.MODULE, name="B"),
            ],
            edges=[
                Edge(**{"from": "a", "to": "b", "type": "contains"}),
                Edge(**{"from": "b", "to": "a", "type": "contains"}),
            ],
        )
        result = validate_snapshot(snap)
        assert not result.valid
        assert any("cycle" in e for e in result.errors)

    def test_orphan_warning(self):
        snap = Snapshot(
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="S"),
                Node(id="lonely", kind=NodeKind.MODULE, name="Lonely"),
            ],
        )
        result = validate_snapshot(snap)
        # Orphans are warnings, not errors
        assert result.valid
        assert len(result.warnings) > 0
