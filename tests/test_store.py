"""Tests for file store."""

import pytest
from pathlib import Path
from sir.store.file_store import FileStore
from sir.ir.schema import Node, NodeKind, Snapshot
from sir.patch.schema import Patch, PatchOperation, PatchOpType


@pytest.fixture
def store(tmp_path):
    return FileStore(tmp_path)


class TestFileStore:
    def test_init(self, store):
        snapshot = store.init("test_project")
        assert store.is_initialized()
        assert snapshot.version == 1
        assert len(snapshot.nodes) == 1
        assert snapshot.nodes[0].kind == NodeKind.SYSTEM

    def test_save_and_load_snapshot(self, store):
        store.init("test")
        snap = Snapshot(
            version=2,
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="Test"),
                Node(id="mod", kind=NodeKind.MODULE, name="Mod"),
            ],
        )
        store.save_snapshot(snap)
        loaded = store.load_snapshot()
        assert loaded.version == 2
        assert len(loaded.nodes) == 2

    def test_load_specific_version(self, store):
        store.init("test")
        snap2 = Snapshot(
            version=2,
            nodes=[Node(id="sys", kind=NodeKind.SYSTEM, name="V2")],
        )
        store.save_snapshot(snap2)

        v1 = store.load_snapshot(version=1)
        v2 = store.load_snapshot(version=2)
        assert v1.version == 1
        assert v2.version == 2

    def test_load_nonexistent_raises(self, store):
        store.init("test")
        with pytest.raises(FileNotFoundError):
            store.load_snapshot(version=99)

    def test_save_and_load_patches(self, store):
        store.init("test")
        patch = Patch(
            description="test patch",
            operations=[
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "mod_a", "kind": "module", "name": "A",
                }),
            ],
        )
        store.save_patch(patch, 0)
        patches = store.load_patches()
        assert len(patches) == 1
        assert patches[0].description == "test patch"

    def test_patch_count(self, store):
        store.init("test")
        assert store.patch_count() == 0
        patch = Patch(description="p1", operations=[])
        store.save_patch(patch, 0)
        assert store.patch_count() == 1
        store.save_patch(patch, 1)
        assert store.patch_count() == 2

    def test_not_initialized(self, store):
        assert not store.is_initialized()
