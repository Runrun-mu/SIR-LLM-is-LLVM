"""Tests for CLI commands."""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from sir.cli.main import cli
from sir.store.file_store import FileStore


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestCLI:
    def test_init(self, runner, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        result = runner.invoke(cli, ["init", "my_project"])
        assert result.exit_code == 0
        assert "Initialized" in result.output
        assert (project_dir / ".sir").exists()
        assert (project_dir / ".sir" / "snapshots" / "current.json").exists()

    def test_init_twice_fails(self, runner, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        runner.invoke(cli, ["init", "proj"])
        result = runner.invoke(cli, ["init", "proj"])
        assert result.exit_code != 0
        assert "already initialized" in result.output

    def test_snapshot_show(self, runner, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        runner.invoke(cli, ["init", "test_proj"])
        result = runner.invoke(cli, ["snapshot", "show"])
        assert result.exit_code == 0
        assert "test_proj" in result.output

    def test_snapshot_json(self, runner, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        runner.invoke(cli, ["init", "test_proj"])
        result = runner.invoke(cli, ["snapshot", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["version"] == 1

    def test_validate(self, runner, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        runner.invoke(cli, ["init", "test_proj"])
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_patch_list_empty(self, runner, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        runner.invoke(cli, ["init", "test_proj"])
        result = runner.invoke(cli, ["patch", "list"])
        assert result.exit_code == 0
        assert "No patches" in result.output

    def test_generate_initial(self, runner, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        runner.invoke(cli, ["init", "test_proj"])
        result = runner.invoke(cli, ["generate"])
        assert result.exit_code == 0
        assert "Generated" in result.output

    def test_not_initialized(self, runner, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code != 0
        assert "Not a SIR project" in result.output
