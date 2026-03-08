"""IntentSpec model - parsed representation of user intent."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntentAction(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    QUERY = "query"


class IntentTarget(BaseModel):
    kind: str
    name: str = ""
    description: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class IntentSpec(BaseModel):
    action: IntentAction
    targets: list[IntentTarget] = Field(default_factory=list)
    context: str = ""
    constraints: list[str] = Field(default_factory=list)
    raw_input: str = ""
