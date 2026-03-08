"""Tests for MCP server tools."""

import json
import pytest
from pathlib import Path

from sir.mcp.server import (
    sir_init,
    sir_snapshot_show,
    sir_snapshot_json,
    sir_validate,
    sir_apply_patch,
    sir_generate,
    sir_patch_list,
    sir_node_kinds,
    sir_edge_types,
)


@pytest.fixture
def project_dir(tmp_path):
    return str(tmp_path)


class TestMCPTools:
    def test_init(self, project_dir):
        result = sir_init(project_dir, "test_proj")
        assert "Initialized" in result
        assert "test_proj" in result

    def test_init_twice(self, project_dir):
        sir_init(project_dir, "test_proj")
        result = sir_init(project_dir, "test_proj")
        assert "Error" in result

    def test_snapshot_show(self, project_dir):
        sir_init(project_dir, "test_proj")
        result = sir_snapshot_show(project_dir)
        assert "test_proj" in result
        assert "1 nodes" in result

    def test_snapshot_json(self, project_dir):
        sir_init(project_dir, "test_proj")
        result = sir_snapshot_json(project_dir)
        data = json.loads(result)
        assert data["version"] == 1
        assert len(data["nodes"]) == 1

    def test_validate(self, project_dir):
        sir_init(project_dir, "test_proj")
        result = sir_validate(project_dir)
        assert "valid" in result

    def test_apply_patch(self, project_dir):
        sir_init(project_dir, "test_proj")
        patch = {
            "description": "Add auth module",
            "operations": [
                {"op": "add_node", "value": {"id": "mod_auth", "kind": "module", "name": "Auth"}},
                {"op": "add_edge", "value": {"from": "sys_root", "to": "mod_auth", "type": "contains"}},
            ],
        }
        result = sir_apply_patch(project_dir, json.dumps(patch))
        assert "successfully" in result
        assert "v1 -> v2" in result

    def test_apply_patch_invalid(self, project_dir):
        sir_init(project_dir, "test_proj")
        patch = {
            "description": "Bad patch",
            "operations": [
                {"op": "add_edge", "value": {"from": "sys_root", "to": "nonexist", "type": "contains"}},
            ],
        }
        result = sir_apply_patch(project_dir, json.dumps(patch))
        assert "Error" in result

    def test_generate(self, project_dir):
        sir_init(project_dir, "test_proj")
        # Add some nodes first
        patch = {
            "description": "Add module",
            "operations": [
                {"op": "add_node", "value": {"id": "mod_auth", "kind": "module", "name": "Auth"}},
                {"op": "add_node", "value": {"id": "cmp_login", "kind": "component", "name": "Login"}},
                {"op": "add_edge", "value": {"from": "sys_root", "to": "mod_auth", "type": "contains"}},
                {"op": "add_edge", "value": {"from": "mod_auth", "to": "cmp_login", "type": "contains"}},
            ],
        }
        sir_apply_patch(project_dir, json.dumps(patch))
        result = sir_generate(project_dir)
        assert "Generated" in result
        assert "artifacts" in result

    def test_patch_list_empty(self, project_dir):
        sir_init(project_dir, "test_proj")
        result = sir_patch_list(project_dir)
        assert "No patches" in result

    def test_patch_list_after_apply(self, project_dir):
        sir_init(project_dir, "test_proj")
        patch = {
            "description": "Add auth module",
            "operations": [
                {"op": "add_node", "value": {"id": "mod_auth", "kind": "module", "name": "Auth"}},
                {"op": "add_edge", "value": {"from": "sys_root", "to": "mod_auth", "type": "contains"}},
            ],
        }
        sir_apply_patch(project_dir, json.dumps(patch))
        result = sir_patch_list(project_dir)
        assert "Add auth module" in result

    def test_not_initialized(self, project_dir):
        assert "Error" in sir_snapshot_show(project_dir)
        assert "Error" in sir_validate(project_dir)
        assert "Error" in sir_generate(project_dir)

    def test_node_kinds(self):
        result = sir_node_kinds()
        assert "module" in result
        assert "component" in result
        assert "entity" in result

    def test_edge_types(self):
        result = sir_edge_types()
        assert "contains" in result
        assert "depends_on" in result

    def test_full_workflow(self, project_dir):
        """E2E: init -> patch -> validate -> generate -> inspect."""
        # Init
        sir_init(project_dir, "demo")

        # Apply patch with full auth module
        patch = {
            "description": "Add authentication module",
            "operations": [
                {"op": "add_node", "value": {
                    "id": "mod_auth", "kind": "module", "name": "Auth",
                    "description": "Authentication module",
                }},
                {"op": "add_node", "value": {
                    "id": "ent_user", "kind": "entity", "name": "User",
                    "properties": {"fields": ["username", "email"]},
                }},
                {"op": "add_node", "value": {
                    "id": "cmp_login", "kind": "component", "name": "Login",
                    "properties": {"methods": ["authenticate"]},
                }},
                {"op": "add_edge", "value": {"from": "sys_root", "to": "mod_auth", "type": "contains"}},
                {"op": "add_edge", "value": {"from": "mod_auth", "to": "ent_user", "type": "contains"}},
                {"op": "add_edge", "value": {"from": "mod_auth", "to": "cmp_login", "type": "contains"}},
                {"op": "add_edge", "value": {"from": "cmp_login", "to": "ent_user", "type": "depends_on"}},
            ],
        }
        result = sir_apply_patch(project_dir, json.dumps(patch))
        assert "successfully" in result

        # Validate
        assert "valid" in sir_validate(project_dir)

        # Generate
        gen_result = sir_generate(project_dir)
        assert "Generated" in gen_result

        # Check snapshot
        snap = json.loads(sir_snapshot_json(project_dir))
        assert snap["version"] == 2
        assert len(snap["nodes"]) == 4

        # Verify files exist
        assert (Path(project_dir) / "output" / "auth" / "models.py").exists()
        assert (Path(project_dir) / "output" / "auth" / "components" / "login.py").exists()
