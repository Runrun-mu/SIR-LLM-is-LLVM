"""SIR MCP Server - expose SIR operations as MCP tools."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server import FastMCP

from sir.adapter.generic import GenericAdapter
from sir.generator.config_gen import ConfigGenerator
from sir.generator.python_gen import PythonGenerator
from sir.generator.schema import ArtifactManifest
from sir.ir.schema import Snapshot
from sir.ir.validator import validate_snapshot
from sir.patch.engine import apply_patch
from sir.patch.schema import Patch
from sir.store.file_store import FileStore

app = FastMCP("sir", instructions="Software Intent Runtime - compile human intent into software artifacts via IR graph")


def _get_store(project_dir: str) -> FileStore:
    return FileStore(Path(project_dir))


def _generate(snapshot: Snapshot, store: FileStore) -> ArtifactManifest:
    adapter = GenericAdapter()
    project = adapter.lower(snapshot)
    py_manifest = PythonGenerator().generate(project, store.output_dir)
    cfg_manifest = ConfigGenerator().generate(project, store.output_dir)
    return ArtifactManifest(entries=py_manifest.entries + cfg_manifest.entries)


@app.tool()
def sir_init(project_dir: str, project_name: str) -> str:
    """Initialize a new SIR project.

    Args:
        project_dir: Absolute path to the project root directory.
        project_name: Name of the project.
    """
    store = _get_store(project_dir)
    if store.is_initialized():
        return "Error: Project already initialized."
    snapshot = store.init(project_name)
    return f"Initialized SIR project '{project_name}' at {project_dir}/.sir/\nInitial snapshot: v{snapshot.version}"


@app.tool()
def sir_snapshot_show(project_dir: str, version: int | None = None) -> str:
    """Show the current IR snapshot as a human-readable summary.

    Args:
        project_dir: Absolute path to the project root directory.
        version: Specific snapshot version to show. Omit for current.
    """
    store = _get_store(project_dir)
    if not store.is_initialized():
        return "Error: Not a SIR project. Run sir_init first."
    snapshot = store.load_snapshot(version=version)
    return snapshot.to_summary()


@app.tool()
def sir_snapshot_json(project_dir: str, version: int | None = None) -> str:
    """Get the current IR snapshot as JSON.

    Args:
        project_dir: Absolute path to the project root directory.
        version: Specific snapshot version. Omit for current.
    """
    store = _get_store(project_dir)
    if not store.is_initialized():
        return "Error: Not a SIR project. Run sir_init first."
    snapshot = store.load_snapshot(version=version)
    return json.dumps(snapshot.model_dump(by_alias=True), indent=2, ensure_ascii=False)


@app.tool()
def sir_validate(project_dir: str) -> str:
    """Validate the current snapshot for structural correctness.

    Checks: unique system node, no duplicate IDs, no dangling edges,
    contains edges form a DAG, no orphan nodes.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    store = _get_store(project_dir)
    if not store.is_initialized():
        return "Error: Not a SIR project. Run sir_init first."
    snapshot = store.load_snapshot()
    result = validate_snapshot(snapshot)
    lines = []
    if result.valid:
        lines.append("Snapshot is valid.")
    else:
        lines.append("Validation FAILED:")
        for err in result.errors:
            lines.append(f"  ERROR: {err}")
    for w in result.warnings:
        lines.append(f"  WARNING: {w}")
    return "\n".join(lines)


@app.tool()
def sir_apply_patch(project_dir: str, patch_json: str) -> str:
    """Apply a patch to the current snapshot.

    The patch is a JSON object with "description" and "operations" fields.
    Each operation has "op" (add_node/remove_node/update_node/add_edge/remove_edge)
    and "value" (the node or edge data).

    add_node value: {"id": "mod_auth", "kind": "module", "name": "Auth", "description": "...", "properties": {}}
    add_edge value: {"from": "sys_root", "to": "mod_auth", "type": "contains"}
    remove_node value: {"id": "mod_auth"}
    update_node value: {"id": "mod_auth", "name": "New Name"}
    remove_edge value: {"from": "sys_root", "to": "mod_auth"}

    IMPORTANT: add_node must come before any add_edge referencing that node.
    ID conventions: mod_ (module), cmp_ (component), ent_ (entity), ifc_ (interface),
    wf_ (workflow), cap_ (capability), evt_ (event), cst_ (constraint).

    Args:
        project_dir: Absolute path to the project root directory.
        patch_json: Patch as a JSON string.
    """
    store = _get_store(project_dir)
    if not store.is_initialized():
        return "Error: Not a SIR project. Run sir_init first."

    try:
        patch_data = json.loads(patch_json)
        patch = Patch(**patch_data)
        snapshot = store.load_snapshot()
        new_snapshot = apply_patch(snapshot, patch)

        # Validate
        result = validate_snapshot(new_snapshot)
        if not result.valid:
            return "Patch rejected - validation failed:\n" + "\n".join(f"  {e}" for e in result.errors)

        # Persist
        store.save_patch(patch, store.patch_count())
        store.save_snapshot(new_snapshot)

        warnings = ""
        if result.warnings:
            warnings = "\nWarnings:\n" + "\n".join(f"  {w}" for w in result.warnings)

        return (
            f"Patch applied successfully.\n"
            f"Snapshot: v{snapshot.version} -> v{new_snapshot.version}\n"
            f"Nodes: {len(snapshot.nodes)} -> {len(new_snapshot.nodes)}\n"
            f"Edges: {len(snapshot.edges)} -> {len(new_snapshot.edges)}"
            f"{warnings}"
        )
    except Exception as e:
        return f"Error applying patch: {e}"


@app.tool()
def sir_generate(project_dir: str) -> str:
    """Re-generate code artifacts from the current snapshot. No LLM needed.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    store = _get_store(project_dir)
    if not store.is_initialized():
        return "Error: Not a SIR project. Run sir_init first."
    snapshot = store.load_snapshot()
    manifest = _generate(snapshot, store)
    lines = [f"Generated {len(manifest.entries)} artifacts:"]
    for entry in manifest.entries:
        lines.append(f"  {entry.path} ({entry.kind}, {entry.size}B)")
    return "\n".join(lines)


@app.tool()
def sir_patch_list(project_dir: str) -> str:
    """List all applied patches.

    Args:
        project_dir: Absolute path to the project root directory.
    """
    store = _get_store(project_dir)
    if not store.is_initialized():
        return "Error: Not a SIR project. Run sir_init first."
    patches = store.load_patches()
    if not patches:
        return "No patches applied yet."
    lines = []
    for i, p in enumerate(patches):
        lines.append(f"[{i}] {p.description} ({len(p.operations)} ops)")
    return "\n".join(lines)


@app.tool()
def sir_node_kinds() -> str:
    """List all available node kinds and their descriptions."""
    from sir.ir.schema import NodeKind
    descriptions = {
        "system": "Root node representing the entire software system",
        "module": "A cohesive unit of functionality (e.g. 'authentication')",
        "component": "An executable unit within a module (e.g. 'login handler')",
        "interface": "A contract defining a service boundary",
        "entity": "A data model or domain object",
        "capability": "A discrete ability the system provides",
        "workflow": "A multi-step process or business flow",
        "event": "A signal emitted or consumed by components",
        "constraint": "A rule or invariant that must be maintained",
    }
    lines = ["Available NodeKinds:"]
    for k in NodeKind:
        lines.append(f"  {k.value}: {descriptions.get(k.value, '')}")
    return "\n".join(lines)


@app.tool()
def sir_edge_types() -> str:
    """List all available edge types and their descriptions."""
    from sir.ir.schema import EdgeType
    descriptions = {
        "contains": "Compositional hierarchy (must form a DAG)",
        "depends_on": "Runtime or compile-time dependency",
        "implements": "A component realizes an interface",
        "emits": "A component produces an event",
        "consumes": "A component reacts to an event",
        "triggers": "One workflow/component initiates another",
        "constrains": "A constraint applies to a node",
    }
    lines = ["Available EdgeTypes:"]
    for e in EdgeType:
        lines.append(f"  {e.value}: {descriptions.get(e.value, '')}")
    return "\n".join(lines)


if __name__ == "__main__":
    app.run(transport="stdio")
