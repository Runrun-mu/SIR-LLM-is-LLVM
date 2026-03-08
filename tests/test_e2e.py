"""End-to-end tests: snapshot → adapter → generator → files (no LLM needed)."""

import json
import pytest
from pathlib import Path

from sir.ir.schema import Edge, Node, NodeKind, Snapshot
from sir.ir.validator import validate_snapshot
from sir.patch.engine import apply_patch
from sir.patch.schema import Patch, PatchOperation, PatchOpType
from sir.adapter.generic import GenericAdapter
from sir.generator.python_gen import PythonGenerator
from sir.generator.config_gen import ConfigGenerator
from sir.store.file_store import FileStore


class TestE2EManualPatch:
    """Full pipeline using hand-crafted patches (no LLM)."""

    @pytest.fixture
    def store(self, tmp_path):
        store = FileStore(tmp_path)
        store.init("demo_app")
        return store

    def test_full_pipeline(self, store):
        """Test: init → patch → validate → adapt → generate."""
        # Step 1: Load initial snapshot
        snap = store.load_snapshot()
        assert snap.version == 1
        assert len(snap.nodes) == 1  # Just system node

        # Step 2: Apply patch - add auth module with components
        patch = Patch(
            description="Add authentication module",
            operations=[
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "mod_auth", "kind": "module", "name": "Auth",
                    "description": "Authentication module",
                }),
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "cmp_login", "kind": "component", "name": "Login",
                    "description": "Handles user login",
                    "properties": {"methods": ["authenticate", "logout"]},
                }),
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "ent_user", "kind": "entity", "name": "User",
                    "description": "User account",
                    "properties": {"fields": ["username", "email", "password_hash"]},
                }),
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "ent_session", "kind": "entity", "name": "Session",
                    "description": "Login session",
                    "properties": {"fields": ["token", "user_id", "expires_at"]},
                }),
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "ifc_auth", "kind": "interface", "name": "Auth Service",
                    "description": "Authentication service interface",
                    "properties": {"methods": ["login", "register", "verify_token"]},
                }),
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "wf_login", "kind": "workflow", "name": "Login Flow",
                    "description": "User login workflow",
                    "properties": {"steps": ["validate_input", "check_credentials", "create_session", "return_token"]},
                }),
                # Edges: system contains module
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "sys_root", "to": "mod_auth", "type": "contains",
                }),
                # Module contains children
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "mod_auth", "to": "cmp_login", "type": "contains",
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "mod_auth", "to": "ent_user", "type": "contains",
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "mod_auth", "to": "ent_session", "type": "contains",
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "mod_auth", "to": "ifc_auth", "type": "contains",
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "mod_auth", "to": "wf_login", "type": "contains",
                }),
                # Dependencies
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "cmp_login", "to": "ent_user", "type": "depends_on",
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "cmp_login", "to": "ent_session", "type": "depends_on",
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "cmp_login", "to": "ifc_auth", "type": "implements",
                }),
            ],
        )

        snap2 = apply_patch(snap, patch)
        assert snap2.version == 2
        assert len(snap2.nodes) == 7  # sys + 6 new
        assert len(snap2.edges) == 9

        # Step 3: Validate
        result = validate_snapshot(snap2)
        assert result.valid, f"Validation failed: {result.errors}"

        # Step 4: Persist
        store.save_patch(patch, 0)
        store.save_snapshot(snap2)

        # Step 5: Adapt
        adapter = GenericAdapter()
        project = adapter.lower(snap2)
        assert project.project_name == "demo_app"
        assert len(project.nodes) == 6  # excludes system

        # Step 6: Generate
        py_gen = PythonGenerator()
        manifest = py_gen.generate(project, store.output_dir)
        assert len(manifest.entries) > 0
        assert not manifest.has_duplicates()

        # Verify generated files
        assert (store.output_dir / "auth" / "components" / "login.py").exists()
        assert (store.output_dir / "auth" / "models.py").exists()
        assert (store.output_dir / "auth" / "services" / "auth_service.py").exists()
        assert (store.output_dir / "auth" / "workflows" / "login_flow.py").exists()

        # Verify content quality
        login_code = (store.output_dir / "auth" / "components" / "login.py").read_text()
        assert "class Login:" in login_code
        assert "def authenticate" in login_code

        models_code = (store.output_dir / "auth" / "models.py").read_text()
        assert "@dataclass" in models_code
        assert "class User:" in models_code
        assert "class Session:" in models_code

    def test_incremental_patch(self, store):
        """Test applying patches incrementally."""
        snap = store.load_snapshot()

        # Patch 1: Add module
        patch1 = Patch(
            description="Add user module",
            operations=[
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "mod_user", "kind": "module", "name": "User",
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "sys_root", "to": "mod_user", "type": "contains",
                }),
            ],
        )
        snap2 = apply_patch(snap, patch1)
        store.save_patch(patch1, 0)
        store.save_snapshot(snap2)

        # Patch 2: Add component to module
        patch2 = Patch(
            description="Add profile component",
            operations=[
                PatchOperation(op=PatchOpType.ADD_NODE, value={
                    "id": "cmp_profile", "kind": "component", "name": "Profile",
                    "properties": {"methods": ["get_profile", "update_profile"]},
                }),
                PatchOperation(op=PatchOpType.ADD_EDGE, value={
                    "from": "mod_user", "to": "cmp_profile", "type": "contains",
                }),
            ],
        )
        snap3 = apply_patch(snap2, patch2)
        store.save_patch(patch2, 1)
        store.save_snapshot(snap3)

        # Verify
        assert snap3.version == 3
        assert len(snap3.nodes) == 3
        assert store.patch_count() == 2

        result = validate_snapshot(snap3)
        assert result.valid

        # Generate and check
        adapter = GenericAdapter()
        project = adapter.lower(snap3)
        py_gen = PythonGenerator()
        manifest = py_gen.generate(project, store.output_dir)
        assert (store.output_dir / "user" / "components" / "profile.py").exists()

    def test_snapshot_roundtrip(self, store):
        """Test that snapshot survives serialize → deserialize."""
        snap = store.load_snapshot()
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.ADD_NODE, value={
                "id": "mod_test", "kind": "module", "name": "Test Module",
                "description": "A test module",
                "properties": {"key": "value"},
            }),
            PatchOperation(op=PatchOpType.ADD_EDGE, value={
                "from": "sys_root", "to": "mod_test", "type": "contains",
            }),
        ])
        snap2 = apply_patch(snap, patch)
        store.save_snapshot(snap2)

        loaded = store.load_snapshot()
        assert loaded.version == snap2.version
        assert len(loaded.nodes) == len(snap2.nodes)
        assert loaded.get_node("mod_test").name == "Test Module"
        assert loaded.get_node("mod_test").properties == {"key": "value"}


class TestE2EValidation:
    """Test validation catches errors in real pipeline scenarios."""

    def test_patch_then_validate(self):
        """Apply a valid patch then validate the result."""
        snap = Snapshot(
            version=1,
            nodes=[Node(id="sys", kind=NodeKind.SYSTEM, name="App")],
        )
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.ADD_NODE, value={
                "id": "mod_a", "kind": "module", "name": "A",
            }),
            PatchOperation(op=PatchOpType.ADD_EDGE, value={
                "from": "sys", "to": "mod_a", "type": "contains",
            }),
        ])
        snap2 = apply_patch(snap, patch)
        result = validate_snapshot(snap2)
        assert result.valid

    def test_remove_creates_valid_state(self):
        """Removing a node and its edges should leave a valid snapshot."""
        snap = Snapshot(
            version=1,
            nodes=[
                Node(id="sys", kind=NodeKind.SYSTEM, name="App"),
                Node(id="mod_a", kind=NodeKind.MODULE, name="A"),
                Node(id="mod_b", kind=NodeKind.MODULE, name="B"),
            ],
            edges=[
                Edge(**{"from": "sys", "to": "mod_a", "type": "contains"}),
                Edge(**{"from": "sys", "to": "mod_b", "type": "contains"}),
                Edge(**{"from": "mod_a", "to": "mod_b", "type": "depends_on"}),
            ],
        )
        patch = Patch(operations=[
            PatchOperation(op=PatchOpType.REMOVE_NODE, value={"id": "mod_a"}),
        ])
        snap2 = apply_patch(snap, patch)
        result = validate_snapshot(snap2)
        assert result.valid
        assert len(snap2.edges) == 1  # Only sys->mod_b remains
