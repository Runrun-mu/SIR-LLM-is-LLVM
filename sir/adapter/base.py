"""Abstract adapter base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sir.adapter.schema import ProjectSnapshot
from sir.ir.schema import Snapshot


class Adapter(ABC):
    """Transforms an IR Snapshot into a project-specific ProjectSnapshot."""

    @abstractmethod
    def lower(self, snapshot: Snapshot) -> ProjectSnapshot:
        """Lower IR snapshot to project-level representation."""
        ...
