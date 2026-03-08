"""IR schema: Node, Edge, and Snapshot Pydantic models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeKind(str, Enum):
    SYSTEM = "system"
    MODULE = "module"
    COMPONENT = "component"
    INTERFACE = "interface"
    ENTITY = "entity"
    CAPABILITY = "capability"
    WORKFLOW = "workflow"
    EVENT = "event"
    CONSTRAINT = "constraint"


class EdgeType(str, Enum):
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    EMITS = "emits"
    CONSUMES = "consumes"
    TRIGGERS = "triggers"
    CONSTRAINS = "constrains"


class Node(BaseModel):
    id: str
    kind: NodeKind
    name: str
    description: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    from_node: str = Field(alias="from")
    to: str
    edge_type: EdgeType = Field(alias="type")
    properties: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class Snapshot(BaseModel):
    version: int = 1
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_node(self, node_id: str) -> Node | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    def to_summary(self) -> str:
        lines = [f"Snapshot v{self.version}: {len(self.nodes)} nodes, {len(self.edges)} edges"]
        for n in self.nodes:
            lines.append(f"  [{n.kind.value}] {n.id}: {n.name}")
        for e in self.edges:
            lines.append(f"  {e.from_node} --{e.edge_type.value}--> {e.to}")
        return "\n".join(lines)
