"""CLI entry point using Click."""

from __future__ import annotations

import json
from pathlib import Path

import click

from sir.ir.validator import validate_snapshot
from sir.llm.provider import PRESETS, create_provider
from sir.pipeline.compile import CompilePipeline
from sir.store.file_store import FileStore


def _get_store() -> FileStore:
    return FileStore(Path.cwd())


def _ensure_init(store: FileStore) -> None:
    if not store.is_initialized():
        raise click.ClickException(
            "Not a SIR project. Run 'sir init <name>' first."
        )


@click.group()
def cli():
    """Software Intent Runtime - compile human intent into software artifacts."""
    pass


@cli.command()
@click.argument("project_name")
def init(project_name: str):
    """Initialize a new SIR project."""
    store = _get_store()
    if store.is_initialized():
        raise click.ClickException("Project already initialized.")
    snapshot = store.init(project_name)
    click.echo(f"Initialized SIR project '{project_name}'")
    click.echo(f"  .sir/ directory created")
    click.echo(f"  Initial snapshot: v{snapshot.version}")


@cli.command()
@click.argument("intent", type=str)
@click.option("--provider", "-p", default="openai",
              help=f"LLM provider: {', '.join(PRESETS)} or custom")
@click.option("--api-key", envvar=None, default=None,
              help="API key (or set provider-specific env var)")
@click.option("--model", "-m", default=None,
              help="Model name override")
@click.option("--base-url", default=None,
              help="Custom OpenAI-compatible base URL")
def compile(intent: str, provider: str, api_key: str | None, model: str | None, base_url: str | None):
    """Compile a human intent into code artifacts.

    \b
    Examples:
      sir compile "Add auth module"
      sir compile "Add auth module" -p openai
      sir compile "Add auth module" -p deepseek
      sir compile "Add auth module" -p gemini
      sir compile "Add auth module" --base-url http://localhost:11434/v1 -m llama3
    """
    store = _get_store()
    _ensure_init(store)

    llm = create_provider(provider=provider, api_key=api_key, model=model, base_url=base_url)
    pipeline = CompilePipeline(store, provider=llm)

    click.echo(f"Compiling: {intent}")
    click.echo(f"  Provider: {provider} ({llm.__class__.__name__})")

    result = pipeline.compile(intent)

    if not result.success:
        click.echo("Compilation failed:")
        for err in result.errors:
            click.echo(f"  ERROR: {err}")
        raise SystemExit(1)

    click.echo(f"  Intent: {result.intent.action.value} -> {len(result.intent.targets)} targets")
    click.echo(f"  Patch: {len(result.patch.operations)} operations")
    click.echo(f"  Snapshot: v{result.snapshot.version} ({len(result.snapshot.nodes)} nodes)")
    click.echo(f"  Artifacts: {len(result.manifest.entries)} files generated")

    if result.validation and result.validation.warnings:
        for w in result.validation.warnings:
            click.echo(f"  WARNING: {w}")

    click.echo("Done.")


@cli.group("snapshot")
def snapshot_group():
    """Manage snapshots."""
    pass


@snapshot_group.command("show")
@click.option("--version", "-v", type=int, default=None, help="Snapshot version")
def snapshot_show(version: int | None):
    """Show the current or specified snapshot."""
    store = _get_store()
    _ensure_init(store)
    snapshot = store.load_snapshot(version=version)
    click.echo(snapshot.to_summary())


@snapshot_group.command("json")
@click.option("--version", "-v", type=int, default=None)
def snapshot_json(version: int | None):
    """Dump snapshot as JSON."""
    store = _get_store()
    _ensure_init(store)
    snapshot = store.load_snapshot(version=version)
    click.echo(json.dumps(snapshot.model_dump(by_alias=True), indent=2, ensure_ascii=False))


@cli.group("patch")
def patch_group():
    """Manage patches."""
    pass


@patch_group.command("list")
def patch_list():
    """List all applied patches."""
    store = _get_store()
    _ensure_init(store)
    patches = store.load_patches()
    if not patches:
        click.echo("No patches applied yet.")
        return
    for i, p in enumerate(patches):
        click.echo(f"  [{i}] {p.description} ({len(p.operations)} ops)")


@cli.command()
def generate():
    """Re-generate artifacts from the current snapshot (no LLM needed)."""
    store = _get_store()
    _ensure_init(store)
    pipeline = CompilePipeline(store)
    project, manifest = pipeline.generate_from_snapshot()
    click.echo(f"Generated {len(manifest.entries)} artifacts:")
    for entry in manifest.entries:
        click.echo(f"  {entry.path} ({entry.kind})")


@cli.command()
def validate():
    """Validate the current snapshot."""
    store = _get_store()
    _ensure_init(store)
    snapshot = store.load_snapshot()
    result = validate_snapshot(snapshot)

    if result.valid:
        click.echo("Snapshot is valid.")
    else:
        click.echo("Validation FAILED:")
        for err in result.errors:
            click.echo(f"  ERROR: {err}")

    for w in result.warnings:
        click.echo(f"  WARNING: {w}")


@cli.group("mcp")
def mcp_group():
    """MCP server management."""
    pass


@mcp_group.command("install")
@click.option("--tool", "-t", default="claude-code",
              type=click.Choice(["claude-code", "codex", "cursor"]),
              help="Target AI tool")
@click.option("--scope", "-s", default="project",
              type=click.Choice(["project", "user"]),
              help="project = .mcp.json in cwd, user = ~/.claude/mcp.json")
def mcp_install(tool: str, scope: str):
    """Install SIR as an MCP server for your AI tool.

    \b
    Examples:
      sir mcp install                          # .mcp.json in current dir
      sir mcp install -t codex                 # for Codex
      sir mcp install -s user                  # global ~/.claude/mcp.json
    """
    from sir.mcp.install import install_claude_code, print_config
    if tool in ("claude-code", "codex", "cursor"):
        path = install_claude_code(scope=scope)
        click.echo(f"MCP config written to {path}")
        click.echo(f"Server command: python -m sir.mcp")
        click.echo(f"Restart {tool} to activate.")
    else:
        print_config(tool)


@mcp_group.command("config")
@click.option("--tool", "-t", default="claude-code",
              type=click.Choice(["claude-code", "codex", "cursor"]))
def mcp_config(tool: str):
    """Print the MCP config JSON (for manual setup)."""
    from sir.mcp.install import print_config
    print_config(tool)


@mcp_group.command("run")
def mcp_run():
    """Start the MCP server (stdio transport)."""
    from sir.mcp.server import app
    app.run(transport="stdio")


if __name__ == "__main__":
    cli()
