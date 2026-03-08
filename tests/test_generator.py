"""Tests for code generators."""

import pytest
from pathlib import Path

from sir.adapter.generic import GenericAdapter
from sir.adapter.schema import ProjectNode, ProjectSnapshot
from sir.generator.python_gen import PythonGenerator, _class_name
from sir.generator.config_gen import ConfigGenerator
from sir.generator.schema import ArtifactManifest
from sir.ir.schema import Edge, Node, NodeKind, Snapshot


def _auth_snapshot() -> Snapshot:
    return Snapshot(
        nodes=[
            Node(id="sys", kind=NodeKind.SYSTEM, name="MyApp"),
            Node(id="mod_auth", kind=NodeKind.MODULE, name="Auth"),
            Node(id="cmp_login", kind=NodeKind.COMPONENT, name="Login",
                 properties={"methods": ["authenticate", "logout"]}),
            Node(id="ent_user", kind=NodeKind.ENTITY, name="User",
                 properties={"fields": ["username", "email", "password_hash"]}),
            Node(id="ifc_auth_svc", kind=NodeKind.INTERFACE, name="Auth Service",
                 properties={"methods": ["login", "register"]}),
            Node(id="wf_login", kind=NodeKind.WORKFLOW, name="Login Flow",
                 properties={"steps": ["validate_input", "check_credentials", "create_session"]}),
        ],
        edges=[
            Edge(**{"from": "sys", "to": "mod_auth", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "cmp_login", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "ent_user", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "ifc_auth_svc", "type": "contains"}),
            Edge(**{"from": "mod_auth", "to": "wf_login", "type": "contains"}),
        ],
    )


class TestClassName:
    def test_simple(self):
        assert _class_name("User") == "User"

    def test_multi_word(self):
        assert _class_name("auth service") == "AuthService"

    def test_snake(self):
        assert _class_name("login_handler") == "LoginHandler"


class TestPythonGenerator:
    @pytest.fixture
    def output_dir(self, tmp_path):
        return tmp_path / "output"

    @pytest.fixture
    def project(self):
        adapter = GenericAdapter()
        return adapter.lower(_auth_snapshot())

    def test_generate_creates_files(self, project, output_dir):
        gen = PythonGenerator()
        manifest = gen.generate(project, output_dir)
        assert len(manifest.entries) > 0
        for entry in manifest.entries:
            assert (output_dir / entry.path).exists()

    def test_entity_has_dataclass(self, project, output_dir):
        gen = PythonGenerator()
        gen.generate(project, output_dir)
        models = (output_dir / "auth" / "models.py").read_text()
        assert "@dataclass" in models
        assert "class User:" in models
        assert "username" in models

    def test_component_has_methods(self, project, output_dir):
        gen = PythonGenerator()
        gen.generate(project, output_dir)
        content = (output_dir / "auth" / "components" / "login.py").read_text()
        assert "class Login:" in content
        assert "def authenticate" in content
        assert "def logout" in content

    def test_interface_is_abstract(self, project, output_dir):
        gen = PythonGenerator()
        gen.generate(project, output_dir)
        content = (output_dir / "auth" / "services" / "auth_service.py").read_text()
        assert "ABC" in content
        assert "@abstractmethod" in content
        assert "def login" in content

    def test_workflow_has_steps(self, project, output_dir):
        gen = PythonGenerator()
        gen.generate(project, output_dir)
        content = (output_dir / "auth" / "workflows" / "login_flow.py").read_text()
        assert "def login_flow" in content
        assert "validate_input" in content

    def test_init_files_created(self, project, output_dir):
        gen = PythonGenerator()
        gen.generate(project, output_dir)
        assert (output_dir / "auth" / "__init__.py").exists()
        assert (output_dir / "auth" / "components" / "__init__.py").exists()

    def test_no_duplicate_paths(self, project, output_dir):
        gen = PythonGenerator()
        manifest = gen.generate(project, output_dir)
        assert not manifest.has_duplicates()


class TestConfigGenerator:
    def test_generate_config(self, tmp_path):
        adapter = GenericAdapter()
        project = adapter.lower(_auth_snapshot())
        gen = ConfigGenerator()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        manifest = gen.generate(project, output_dir)
        assert len(manifest.entries) == 1
        assert (output_dir / "sir_project.json").exists()

        import json
        config = json.loads((output_dir / "sir_project.json").read_text())
        assert config["project_name"] == "MyApp"
        assert len(config["modules"]) == 1
        assert config["modules"][0]["name"] == "Auth"
