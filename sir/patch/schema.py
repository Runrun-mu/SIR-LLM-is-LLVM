"""Patch and PatchOperation models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PatchOpType(str, Enum):
    ADD_NODE = "add_node"
    REMOVE_NODE = "remove_node"
    UPDATE_NODE = "update_node"
    ADD_EDGE = "add_edge"
    REMOVE_EDGE = "remove_edge"


class PatchOperation(BaseModel):
    op: PatchOpType
    path: str = ""
    value: dict[str, Any] = Field(default_factory=dict)


class Patch(BaseModel):
    description: str = ""
    operations: list[PatchOperation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
