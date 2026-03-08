"""LLM patch builder - generates patches from IntentSpec + Snapshot."""

from __future__ import annotations

import json

from sir.intent.schema import IntentSpec
from sir.ir.schema import EdgeType, NodeKind, Snapshot
from sir.llm.provider import LLMProvider
from sir.patch.schema import Patch

SYSTEM_PROMPT = """You are a patch builder for a software architecture graph.
Given an IntentSpec (what the user wants) and the current Snapshot (current state),
generate a Patch that transforms the snapshot to fulfill the intent.

Available NodeKinds: {node_kinds}
Available EdgeTypes: {edge_types}

ID naming conventions:
- System: sys_<name>
- Module: mod_<name>
- Component: cmp_<name>
- Interface: ifc_<name>
- Entity: ent_<name>
- Capability: cap_<name>
- Workflow: wf_<name>
- Event: evt_<name>
- Constraint: cst_<name>

The Patch JSON schema:
{{
  "description": "<what this patch does>",
  "operations": [
    {{
      "op": "add_node" | "remove_node" | "update_node" | "add_edge" | "remove_edge",
      "value": {{...}}  // node or edge data
    }}
  ]
}}

For add_node, value should be: {{"id": "...", "kind": "...", "name": "...", "description": "...", "properties": {{}}}}
For remove_node, value should be: {{"id": "..."}}
For update_node, value should be: {{"id": "...", <fields to update>}}
For add_edge, value should be: {{"from": "<source_id>", "to": "<target_id>", "type": "<EdgeType>"}}
For remove_edge, value should be: {{"from": "<source_id>", "to": "<target_id>"}}

IMPORTANT RULES:
1. add_node MUST come before any add_edge that references that node
2. All node IDs must be unique
3. All edge references must point to existing or newly added nodes
4. Use "contains" edges to establish parent-child hierarchy (System contains Modules, Modules contain Components, etc.)
5. Use appropriate edge types for relationships

Current snapshot:
{snapshot_json}

IntentSpec:
{intent_json}

Return ONLY valid JSON matching the Patch schema.
"""


class PatchBuilder:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def build(self, intent: IntentSpec, snapshot: Snapshot) -> Patch:
        snapshot_data = snapshot.model_dump(by_alias=True)
        intent_data = intent.model_dump()

        system = SYSTEM_PROMPT.format(
            node_kinds=", ".join(k.value for k in NodeKind),
            edge_types=", ".join(e.value for e in EdgeType),
            snapshot_json=json.dumps(snapshot_data, indent=2),
            intent_json=json.dumps(intent_data, indent=2),
        )

        response = self.provider.complete(system=system, user="Generate the patch.", max_tokens=4096)
        json_str = _extract_json(response.text)
        data = json.loads(json_str)
        return Patch(**data)


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    text = text.strip()
    start = text.index("{")
    end = text.rindex("}") + 1
    return text[start:end]
