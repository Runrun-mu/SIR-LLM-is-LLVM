"""JSON config generator."""

from __future__ import annotations

import json
from pathlib import Path

from sir.adapter.schema import ProjectSnapshot
from sir.generator.base import Generator
from sir.generator.schema import ArtifactManifest


class ConfigGenerator(Generator):
    """Generates a project config JSON from ProjectSnapshot."""

    def generate(self, project: ProjectSnapshot, output_dir: Path) -> ArtifactManifest:
        manifest = ArtifactManifest()

        config = {
            "project_name": project.project_name,
            "modules": [],
        }

        for node in project.nodes:
            if node.kind == "module":
                mod_info = {
                    "name": node.name,
                    "path": node.path,
                    "components": [],
                }
                # Find children in this module
                for child in project.nodes:
                    if child.path.startswith(node.path) and child.id != node.id:
                        mod_info["components"].append({
                            "name": child.name,
                            "kind": child.kind,
                            "path": child.path,
                        })
                config["modules"].append(mod_info)

        config_path = "sir_project.json"
        file_path = output_dir / config_path
        content = json.dumps(config, indent=2, ensure_ascii=False)
        file_path.write_text(content)

        manifest.add(
            path=config_path,
            source_node_id="config",
            kind="config",
            size=len(content),
        )

        return manifest
