"""CompilePipeline orchestrator - the full compilation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sir.adapter.registry import get_adapter
from sir.adapter.schema import ProjectSnapshot
from sir.generator.config_gen import ConfigGenerator
from sir.generator.python_gen import PythonGenerator
from sir.generator.schema import ArtifactManifest
from sir.intent.parser import IntentParser
from sir.intent.schema import IntentSpec
from sir.ir.schema import Snapshot
from sir.ir.validator import ValidationResult, validate_snapshot
from sir.llm.provider import LLMProvider, create_provider
from sir.patch.builder import PatchBuilder
from sir.patch.engine import apply_patch
from sir.patch.schema import Patch
from sir.store.file_store import FileStore


@dataclass
class CompileResult:
    intent: IntentSpec | None = None
    patch: Patch | None = None
    snapshot: Snapshot | None = None
    project: ProjectSnapshot | None = None
    manifest: ArtifactManifest | None = None
    validation: ValidationResult | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class CompilePipeline:
    """Orchestrates: Intent → Patch → Snapshot → Adapter → Generator → Artifacts."""

    def __init__(self, store: FileStore, provider: LLMProvider | None = None) -> None:
        self.store = store
        self._provider = provider

    def _ensure_llm(self) -> None:
        if self._provider is None:
            self._provider = create_provider()

    @property
    def intent_parser(self) -> IntentParser:
        self._ensure_llm()
        return IntentParser(self._provider)

    @property
    def patch_builder(self) -> PatchBuilder:
        self._ensure_llm()
        return PatchBuilder(self._provider)

    def compile(self, user_input: str) -> CompileResult:
        result = CompileResult()

        try:
            # Load current snapshot
            snapshot = self.store.load_snapshot()

            # Step 1: Parse intent
            intent = self.intent_parser.parse(user_input, snapshot)
            result.intent = intent

            # Step 2: Build patch
            patch = self.patch_builder.build(intent, snapshot)
            result.patch = patch

            # Step 3: Apply patch
            new_snapshot = apply_patch(snapshot, patch)
            result.snapshot = new_snapshot

            # Step 4: Validate
            validation = validate_snapshot(new_snapshot)
            result.validation = validation
            if not validation.valid:
                result.errors.extend(validation.errors)
                return result

            # Step 5: Persist patch and snapshot
            patch_idx = self.store.patch_count()
            self.store.save_patch(patch, patch_idx)
            self.store.save_snapshot(new_snapshot)

            # Step 6: Generate artifacts
            result.project, result.manifest = self._generate(new_snapshot)

        except Exception as e:
            result.errors.append(str(e))

        return result

    def generate_from_snapshot(self) -> tuple[ProjectSnapshot, ArtifactManifest]:
        """Re-generate artifacts from current snapshot without LLM."""
        snapshot = self.store.load_snapshot()
        return self._generate(snapshot)

    def _generate(self, snapshot: Snapshot) -> tuple[ProjectSnapshot, ArtifactManifest]:
        # Adapter lowering
        adapter = get_adapter("generic")
        project = adapter.lower(snapshot)

        # Code generation
        output_dir = self.store.output_dir
        py_gen = PythonGenerator()
        py_manifest = py_gen.generate(project, output_dir)

        cfg_gen = ConfigGenerator()
        cfg_manifest = cfg_gen.generate(project, output_dir)

        # Merge manifests
        combined = ArtifactManifest(
            entries=py_manifest.entries + cfg_manifest.entries,
        )

        return project, combined
