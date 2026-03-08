"""Artifact manifest models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArtifactEntry(BaseModel):
    path: str
    source_node_id: str
    kind: str
    size: int = 0


class ArtifactManifest(BaseModel):
    entries: list[ArtifactEntry] = Field(default_factory=list)

    def add(self, path: str, source_node_id: str, kind: str, size: int = 0) -> None:
        self.entries.append(ArtifactEntry(
            path=path, source_node_id=source_node_id, kind=kind, size=size,
        ))

    def paths(self) -> list[str]:
        return [e.path for e in self.entries]

    def has_duplicates(self) -> bool:
        p = self.paths()
        return len(p) != len(set(p))
