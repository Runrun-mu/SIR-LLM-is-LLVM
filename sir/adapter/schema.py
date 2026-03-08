"""Project-level node and snapshot models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProjectNode(BaseModel):
    id: str
    source_id: str  # ID of the original IR node
    kind: str
    name: str
    path: str  # relative file path for code generation
    description: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class ProjectSnapshot(BaseModel):
    project_name: str
    nodes: list[ProjectNode] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_node(self, node_id: str) -> ProjectNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None
