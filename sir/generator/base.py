"""Abstract generator base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from sir.adapter.schema import ProjectSnapshot
from sir.generator.schema import ArtifactManifest


class Generator(ABC):
    """Generates code artifacts from a ProjectSnapshot."""

    @abstractmethod
    def generate(self, project: ProjectSnapshot, output_dir: Path) -> ArtifactManifest:
        """Generate artifacts and return a manifest."""
        ...
