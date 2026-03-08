"""Tests for adapter layer."""

import pytest
from sir.adapter.generic import GenericAdapter, _snake
from sir.adapter.registry import get_adapter
from sir.ir.schema import Edge, Node, NodeKind, Snapshot


def _auth_snapshot() -> Snapshot:
    return Snapshot(
        nodes=[
            Node(id="sys", kind=NodeKind.SYSTEM, name="MyApp"),
            Node(id="mod_auth", kind=NodeKind.MODULE, name="Authentication"),
            Node(id="cmp_login", kind=NodeKind.COMPONENT, name="Login Handler"),
            Node(id="ent_user", kind=NodeKind.ENTITY, name="User"),
            Node(id="ent_session", kind=NodeKind.ENTITY, name="Session"),
            Node(id="ifc_auth_service", kind=NodeKind.INTERFACE, name="Auth Service"),
            Node(id="wf_login_flow", kind=NodeKind.WORKFLOW, name="Login Flow"),
        ],
        edges=[
            Edge(**{"from": "sys", "to": "mod_auth", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "cmp_login", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "ent_user", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "ent_session", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "ifc_auth_service", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "wf_login_flow", "type": "contains"}),
        ],
    )


class TestSnakeCase:
    def test_camel(self):
        assert _snake("AuthService") == "auth_service"

    def test_spaces(self):
        assert _snake("Login Handler") == "login_handler"

    def test_already_snake(self):
        assert _snake("auth_module") == "auth_module"


class TestGenericAdapter:
    def test_lower_basic(self):
        adapter = GenericAdapter()
        project = adapter.lower(_auth_snapshot())
        assert project.project_name == "MyApp"
        # System node is excluded
        assert len(project.nodes) == 6

    def test_module_path(self):
        adapter = GenericAdapter()
        project = adapter.lower(_auth_snapshot())
        mod = project.get_node("proj_mod_auth")
        assert mod is not None
        assert mod.path == "authentication/"

    def test_component_path(self):
        adapter = GenericAdapter()
        project = adapter.lower(_auth_snapshot())
        cmp = project.get_node("proj_cmp_login")
        assert cmp is not None
        assert cmp.path == "authentication/components/login_handler.py"

    def test_entity_path(self):
        adapter = GenericAdapter()
        project = adapter.lower(_auth_snapshot())
        ent = project.get_node("proj_ent_user")
        assert ent is not None
        assert ent.path == "authentication/models.py"

    def test_interface_path(self):
        adapter = GenericAdapter()
        project = adapter.lower(_auth_snapshot())
        ifc = project.get_node("proj_ifc_auth_service")
        assert ifc is not None
        assert ifc.path == "authentication/services/auth_service.py"

    def test_workflow_path(self):
        adapter = GenericAdapter()
        project = adapter.lower(_auth_snapshot())
        wf = project.get_node("proj_wf_login_flow")
        assert wf is not None
        assert wf.path == "authentication/workflows/login_flow.py"

    def test_all_nodes_have_source_id(self):
        adapter = GenericAdapter()
        project = adapter.lower(_auth_snapshot())
        for node in project.nodes:
            assert node.source_id != ""


class TestAdapterRegistry:
    def test_get_generic(self):
        adapter = get_adapter("generic")
        assert isinstance(adapter, GenericAdapter)

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown adapter"):
            get_adapter("nonexist")
