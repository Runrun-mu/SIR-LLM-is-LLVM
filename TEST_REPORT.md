# SIR (Software Intent Runtime) - Test Report

**Date**: 2026-03-08
**Python**: 3.12.10
**pytest**: 9.0.2
**Platform**: macOS Darwin 24.6.0 (arm64)

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 78 |
| Passed | 78 |
| Failed | 0 |
| Skipped | 0 |
| Duration | 0.35s |
| Coverage | All non-LLM modules |

## Test Breakdown by Module

### 1. IR Schema (`test_ir_schema.py`) - 8 tests

| Test | Status | Description |
|------|--------|-------------|
| `TestNode::test_create_node` | PASS | Node creation with required fields |
| `TestNode::test_node_with_properties` | PASS | Node with properties dict |
| `TestEdge::test_create_edge_with_alias` | PASS | Edge creation using `from` alias |
| `TestEdge::test_create_edge_with_field_name` | PASS | Edge creation using `from_node` field |
| `TestEdge::test_edge_serialization_by_alias` | PASS | Edge serializes `from_node` as `from` |
| `TestSnapshot::test_empty_snapshot` | PASS | Default empty snapshot |
| `TestSnapshot::test_get_node` | PASS | Node lookup by ID |
| `TestSnapshot::test_node_ids` | PASS | Collect all node IDs |
| `TestSnapshot::test_to_summary` | PASS | Human-readable summary |

### 2. IR Graph (`test_ir_graph.py`) - 8 tests

| Test | Status | Description |
|------|--------|-------------|
| `TestIRGraph::test_build` | PASS | Graph construction from snapshot |
| `TestIRGraph::test_children` | PASS | Find children via contains edges |
| `TestIRGraph::test_ancestors` | PASS | Find parent via contains edges |
| `TestIRGraph::test_no_contains_cycle` | PASS | Valid DAG detection |
| `TestIRGraph::test_contains_cycle_detected` | PASS | Cycle detection in contains edges |
| `TestIRGraph::test_orphan_nodes` | PASS | Detect nodes with no edges |
| `TestIRGraph::test_system_not_orphan` | PASS | System node excluded from orphan check |
| `TestIRGraph::test_dangling_edges` | PASS | Detect edges referencing missing nodes |

### 3. IR Validator (`test_ir_validator.py`) - 7 tests

| Test | Status | Description |
|------|--------|-------------|
| `test_valid_snapshot` | PASS | Valid snapshot passes all checks |
| `test_no_system_node` | PASS | Error: missing system node |
| `test_multiple_system_nodes` | PASS | Error: duplicate system nodes |
| `test_duplicate_node_ids` | PASS | Error: non-unique node IDs |
| `test_dangling_edge` | PASS | Error: edge to missing node |
| `test_contains_cycle` | PASS | Error: cyclic contains edges |
| `test_orphan_warning` | PASS | Warning (not error) for orphans |

### 4. Patch Schema & Engine (`test_patch.py`) - 11 tests

| Test | Status | Description |
|------|--------|-------------|
| `test_create_patch` | PASS | Patch model construction |
| `test_add_node` | PASS | Add node to snapshot |
| `test_add_node_duplicate_fails` | PASS | Reject duplicate node ID |
| `test_remove_node` | PASS | Remove node + cascading edge removal |
| `test_remove_nonexistent_fails` | PASS | Reject removing missing node |
| `test_update_node` | PASS | Update node fields |
| `test_add_edge` | PASS | Add edge between existing nodes |
| `test_add_edge_dangling_fails` | PASS | Reject edge to missing node |
| `test_remove_edge` | PASS | Remove specific edge |
| `test_multi_operation_patch` | PASS | Complex patch with multiple ops |
| `test_add_edge_with_from_node_key` | PASS | Accept `from_node` as alternative key |

### 5. File Store (`test_store.py`) - 7 tests

| Test | Status | Description |
|------|--------|-------------|
| `test_init` | PASS | Initialize .sir/ directory |
| `test_save_and_load_snapshot` | PASS | Snapshot round-trip persistence |
| `test_load_specific_version` | PASS | Load versioned snapshot |
| `test_load_nonexistent_raises` | PASS | Error on missing version |
| `test_save_and_load_patches` | PASS | Patch persistence |
| `test_patch_count` | PASS | Count stored patches |
| `test_not_initialized` | PASS | Detect uninitialized project |

### 6. Adapter (`test_adapter.py`) - 12 tests

| Test | Status | Description |
|------|--------|-------------|
| `test_camel` | PASS | CamelCase to snake_case |
| `test_spaces` | PASS | Spaces to snake_case |
| `test_already_snake` | PASS | snake_case passthrough |
| `test_lower_basic` | PASS | Adapter produces correct node count |
| `test_module_path` | PASS | Module -> directory path |
| `test_component_path` | PASS | Component -> components/{name}.py |
| `test_entity_path` | PASS | Entity -> models.py |
| `test_interface_path` | PASS | Interface -> services/{name}.py |
| `test_workflow_path` | PASS | Workflow -> workflows/{name}.py |
| `test_all_nodes_have_source_id` | PASS | Source ID traceability |
| `test_get_generic` | PASS | Registry returns GenericAdapter |
| `test_get_unknown_raises` | PASS | Registry rejects unknown adapter |

### 7. Generator (`test_generator.py`) - 10 tests

| Test | Status | Description |
|------|--------|-------------|
| `test_simple` | PASS | ClassName: simple name |
| `test_multi_word` | PASS | ClassName: multi-word |
| `test_snake` | PASS | ClassName: snake_case input |
| `test_generate_creates_files` | PASS | All files created on disk |
| `test_entity_has_dataclass` | PASS | Entity generates @dataclass |
| `test_component_has_methods` | PASS | Component generates methods |
| `test_interface_is_abstract` | PASS | Interface generates ABC class |
| `test_workflow_has_steps` | PASS | Workflow generates step comments |
| `test_init_files_created` | PASS | __init__.py in all packages |
| `test_no_duplicate_paths` | PASS | No duplicate artifact paths |
| `test_generate_config` | PASS | JSON config file generated |

### 8. CLI (`test_cli.py`) - 8 tests

| Test | Status | Description |
|------|--------|-------------|
| `test_init` | PASS | `sir init` creates project |
| `test_init_twice_fails` | PASS | Double init rejected |
| `test_snapshot_show` | PASS | `sir snapshot show` output |
| `test_snapshot_json` | PASS | `sir snapshot json` valid JSON |
| `test_validate` | PASS | `sir validate` passes |
| `test_patch_list_empty` | PASS | `sir patch list` empty state |
| `test_generate_initial` | PASS | `sir generate` from initial snapshot |
| `test_not_initialized` | PASS | Commands fail without init |

### 9. End-to-End (`test_e2e.py`) - 5 tests

| Test | Status | Description |
|------|--------|-------------|
| `test_full_pipeline` | PASS | Complete: init -> patch -> validate -> adapt -> generate |
| `test_incremental_patch` | PASS | Two sequential patches stack correctly |
| `test_snapshot_roundtrip` | PASS | Serialize -> deserialize preserves all data |
| `test_patch_then_validate` | PASS | Patched snapshot validates clean |
| `test_remove_creates_valid_state` | PASS | Node removal with cascading edges |

## Test Design Philosophy

1. **Unit Tests**: Each module tested in isolation (schema, graph, validator, patch engine, store, adapter, generator)
2. **Integration Tests**: CLI tests verify the full Click command interface
3. **E2E Tests**: Hand-crafted patches simulate real LLM output to test the complete pipeline without API calls
4. **Error Path Tests**: Every error condition (duplicates, missing nodes, dangling edges, cycles) has explicit test coverage
5. **LLM Boundary**: Intent parser and patch builder are excluded from automated tests (require API key); all other modules are fully testable offline

## Known Exclusions

- `sir/intent/parser.py` - Requires live Claude API; tested manually
- `sir/patch/builder.py` - Requires live Claude API; tested manually
- `sir/pipeline/compile.py` (LLM path) - Full compile with LLM requires API key
