"""JSON file persistence for .sir/ project directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sir.ir.schema import Snapshot
from sir.patch.schema import Patch


class FileStore:
    """Manages .sir/ directory structure and JSON persistence."""

    def __init__(self, project_root: Path) -> None:
        self.root = project_root
        self.sir_dir = project_root / ".sir"
        self.snapshots_dir = self.sir_dir / "snapshots"
        self.patches_dir = self.sir_dir / "patches"
        self.output_dir = project_root / "output"

    def init(self, project_name: str) -> Snapshot:
        """Initialize .sir/ directory with an empty snapshot."""
        self.sir_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(exist_ok=True)
        self.patches_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Write project config
        config = {"name": project_name, "version": "0.1.0"}
        self._write_json(self.sir_dir / "config.json", config)

        # Create initial empty snapshot with system node
        from sir.ir.schema import Node, NodeKind
        snapshot = Snapshot(
            version=1,
            nodes=[Node(id="sys_root", kind=NodeKind.SYSTEM, name=project_name)],
        )
        self.save_snapshot(snapshot)
        return snapshot

    def save_snapshot(self, snapshot: Snapshot) -> Path:
        path = self.snapshots_dir / f"v{snapshot.version}.json"
        data = snapshot.model_dump(by_alias=True)
        self._write_json(path, data)

        # Also save as "current"
        current = self.snapshots_dir / "current.json"
        self._write_json(current, data)
        return path

    def load_snapshot(self, version: int | None = None) -> Snapshot:
        if version is not None:
            path = self.snapshots_dir / f"v{version}.json"
        else:
            path = self.snapshots_dir / "current.json"

        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {path}")

        data = self._read_json(path)
        return Snapshot(**data)

    def save_patch(self, patch: Patch, index: int) -> Path:
        path = self.patches_dir / f"patch_{index:04d}.json"
        self._write_json(path, patch.model_dump())
        return path

    def load_patches(self) -> list[Patch]:
        patches = []
        for path in sorted(self.patches_dir.glob("patch_*.json")):
            data = self._read_json(path)
            patches.append(Patch(**data))
        return patches

    def patch_count(self) -> int:
        return len(list(self.patches_dir.glob("patch_*.json")))

    def is_initialized(self) -> bool:
        return self.sir_dir.exists() and (self.snapshots_dir / "current.json").exists()

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _read_json(self, path: Path) -> Any:
        return json.loads(path.read_text())
