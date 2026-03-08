"""Python code generator - generates dataclass/class stubs from ProjectSnapshot."""

from __future__ import annotations

import re
from pathlib import Path

from sir.adapter.schema import ProjectNode, ProjectSnapshot
from sir.generator.base import Generator
from sir.generator.schema import ArtifactManifest


def _class_name(name: str) -> str:
    """Convert a name to PascalCase class name."""
    parts = re.split(r"[\s_\-]+", name)
    return "".join(p.capitalize() for p in parts)


def _generate_entity(node: ProjectNode) -> str:
    cls = _class_name(node.name)
    fields = node.properties.get("fields", [])
    lines = [
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass",
        f"class {cls}:",
        f'    """{node.description or node.name} entity."""',
    ]
    if fields:
        for f in fields:
            fname = f if isinstance(f, str) else f.get("name", "field")
            ftype = "str" if isinstance(f, str) else f.get("type", "str")
            lines.append(f"    {fname}: {ftype} = None")
    else:
        lines.append(f"    id: str = None")
    lines.append("")
    return "\n".join(lines)


def _generate_component(node: ProjectNode) -> str:
    cls = _class_name(node.name)
    methods = node.properties.get("methods", [])
    lines = [
        "from __future__ import annotations",
        "",
        "",
        f"class {cls}:",
        f'    """{node.description or node.name} component."""',
        "",
    ]
    if methods:
        for m in methods:
            mname = m if isinstance(m, str) else m.get("name", "method")
            lines.append(f"    def {mname}(self):")
            lines.append(f"        pass")
            lines.append("")
    else:
        lines.append(f"    def execute(self):")
        lines.append(f"        pass")
        lines.append("")
    return "\n".join(lines)


def _generate_interface(node: ProjectNode) -> str:
    cls = _class_name(node.name)
    methods = node.properties.get("methods", [])
    lines = [
        "from __future__ import annotations",
        "",
        "from abc import ABC, abstractmethod",
        "",
        "",
        f"class {cls}(ABC):",
        f'    """{node.description or node.name} interface."""',
        "",
    ]
    if methods:
        for m in methods:
            mname = m if isinstance(m, str) else m.get("name", "method")
            lines.append(f"    @abstractmethod")
            lines.append(f"    def {mname}(self):")
            lines.append(f"        pass")
            lines.append("")
    else:
        lines.append(f"    @abstractmethod")
        lines.append(f"    def execute(self):")
        lines.append(f"        pass")
        lines.append("")
    return "\n".join(lines)


def _generate_workflow(node: ProjectNode) -> str:
    fname = re.sub(r"[\s\-]+", "_", node.name).lower()
    steps = node.properties.get("steps", [])
    lines = [
        "from __future__ import annotations",
        "",
        "",
        f"def {fname}():",
        f'    """{node.description or node.name} workflow."""',
    ]
    if steps:
        for step in steps:
            sname = step if isinstance(step, str) else step.get("name", "step")
            lines.append(f"    # Step: {sname}")
    lines.append(f"    pass")
    lines.append("")
    return "\n".join(lines)


def _generate_generic(node: ProjectNode) -> str:
    fname = re.sub(r"[\s\-]+", "_", node.name).lower()
    lines = [
        "from __future__ import annotations",
        "",
        "",
        f"# {node.kind}: {node.name}",
        f"# {node.description}" if node.description else "",
        "",
    ]
    return "\n".join(line for line in lines if line is not None)


_GENERATORS = {
    "entity": _generate_entity,
    "component": _generate_component,
    "interface": _generate_interface,
    "workflow": _generate_workflow,
}


class PythonGenerator(Generator):
    """Generates Python code stubs from ProjectSnapshot."""

    def generate(self, project: ProjectSnapshot, output_dir: Path) -> ArtifactManifest:
        manifest = ArtifactManifest()
        # Track entity nodes that share the same models.py path
        entity_groups: dict[str, list[ProjectNode]] = {}

        for node in project.nodes:
            if node.kind == "entity":
                entity_groups.setdefault(node.path, []).append(node)
                continue

            # Module nodes are directories, not files
            if node.kind == "module":
                dir_path = output_dir / node.path
                dir_path.mkdir(parents=True, exist_ok=True)
                self._ensure_init(dir_path, output_dir)
                continue

            gen_fn = _GENERATORS.get(node.kind, _generate_generic)
            content = gen_fn(node)
            file_path = output_dir / node.path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create __init__.py in directories
            self._ensure_init(file_path.parent, output_dir)

            file_path.write_text(content)
            manifest.add(
                path=node.path,
                source_node_id=node.source_id,
                kind=node.kind,
                size=len(content),
            )

        # Generate grouped entity files (models.py)
        for path, nodes in entity_groups.items():
            content = self._generate_entity_group(nodes)
            file_path = output_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_init(file_path.parent, output_dir)
            file_path.write_text(content)
            manifest.add(
                path=path,
                source_node_id=nodes[0].source_id,
                kind="entity",
                size=len(content),
            )

        return manifest

    def _generate_entity_group(self, nodes: list[ProjectNode]) -> str:
        lines = [
            "from __future__ import annotations",
            "",
            "from dataclasses import dataclass",
            "",
        ]
        for node in nodes:
            cls = _class_name(node.name)
            fields = node.properties.get("fields", [])
            lines.append("")
            lines.append("@dataclass")
            lines.append(f"class {cls}:")
            lines.append(f'    """{node.description or node.name} entity."""')
            if fields:
                for f in fields:
                    fname = f if isinstance(f, str) else f.get("name", "field")
                    ftype = "str" if isinstance(f, str) else f.get("type", "str")
                    lines.append(f"    {fname}: {ftype} = None")
            else:
                lines.append(f"    id: str = None")
            lines.append("")
        return "\n".join(lines)

    def _ensure_init(self, directory: Path, root: Path) -> None:
        """Ensure __init__.py exists in directory and all parents up to root."""
        current = directory
        while current != root and current.is_relative_to(root):
            init_file = current / "__init__.py"
            if not init_file.exists():
                init_file.write_text("")
            current = current.parent
