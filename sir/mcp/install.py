"""One-command installer: generates MCP config JSON for various AI tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def get_server_config() -> dict:
    """Return the MCP server config dict."""
    python = sys.executable
    return {
        "command": python,
        "args": ["-m", "sir.mcp"],
    }


def config_for_claude_code() -> dict:
    return {"mcpServers": {"sir": get_server_config()}}


def config_for_codex() -> dict:
    return {"mcpServers": {"sir": get_server_config()}}


def config_for_cursor() -> dict:
    return {"mcpServers": {"sir": get_server_config()}}


def print_config(tool: str = "claude-code") -> None:
    configs = {
        "claude-code": config_for_claude_code,
        "codex": config_for_codex,
        "cursor": config_for_cursor,
    }
    fn = configs.get(tool, config_for_claude_code)
    print(json.dumps(fn(), indent=2))


def install_claude_code(scope: str = "project") -> Path:
    """Write MCP config for Claude Code.

    Args:
        scope: "project" writes to .mcp.json in cwd,
               "user" writes to ~/.claude/mcp.json.
    """
    config = config_for_claude_code()

    if scope == "user":
        target = Path.home() / ".claude" / "mcp.json"
    else:
        target = Path.cwd() / ".mcp.json"

    # Merge with existing config if present
    if target.exists():
        existing = json.loads(target.read_text())
        existing.setdefault("mcpServers", {})
        existing["mcpServers"]["sir"] = get_server_config()
        config = existing

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, indent=2))
    return target


if __name__ == "__main__":
    import sys
    tool = sys.argv[1] if len(sys.argv) > 1 else "claude-code"
    print_config(tool)
