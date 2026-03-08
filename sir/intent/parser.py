"""LLM intent parser."""

from __future__ import annotations

import json

from sir.intent.schema import IntentSpec
from sir.ir.schema import EdgeType, NodeKind, Snapshot
from sir.llm.provider import LLMProvider

SYSTEM_PROMPT = """You are an intent parser for a software architecture system.
Your job is to parse a human's natural language request into a structured IntentSpec.

Available NodeKinds: {node_kinds}
Available EdgeTypes: {edge_types}

The IntentSpec JSON schema:
{{
  "action": "create" | "modify" | "delete" | "query",
  "targets": [
    {{
      "kind": "<NodeKind value>",
      "name": "<name for the target>",
      "description": "<what this target does>",
      "properties": {{}}  // optional, e.g. {{"methods": ["login", "logout"], "fields": ["username", "password"]}}
    }}
  ],
  "context": "<additional context about the request>",
  "constraints": ["<any constraints mentioned>"]
}}

Current system snapshot summary:
{snapshot_summary}

Rules:
- Always return valid JSON matching the schema above
- Infer reasonable names and descriptions from the user's request
- For "create" actions, identify all logical components the user wants
- For "modify" actions, reference existing targets from the snapshot
- Use appropriate NodeKind values for each target
- Extract any methods, fields, or steps into properties
"""


class IntentParser:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def parse(self, user_input: str, snapshot: Snapshot) -> IntentSpec:
        system = SYSTEM_PROMPT.format(
            node_kinds=", ".join(k.value for k in NodeKind),
            edge_types=", ".join(e.value for e in EdgeType),
            snapshot_summary=snapshot.to_summary(),
        )

        response = self.provider.complete(system=system, user=user_input, max_tokens=2048)
        json_str = _extract_json(response.text)
        data = json.loads(json_str)
        spec = IntentSpec(**data)
        spec.raw_input = user_input
        return spec


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
