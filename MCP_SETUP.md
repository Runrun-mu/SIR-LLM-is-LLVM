# SIR MCP Server - Setup Guide

SIR 可以作为 MCP (Model Context Protocol) 服务接入 Claude Code、Codex、Cursor 等 AI 工具，让 AI 直接操作软件架构图。

## 一键安装

```bash
cd your-project/
pip install -e /path/to/software_intent_runtime

# Claude Code（写入当前目录 .mcp.json）
sir mcp install

# Codex
sir mcp install -t codex

# Cursor
sir mcp install -t cursor

# 全局安装（写入 ~/.claude/mcp.json，所有项目可用）
sir mcp install -s user
```

安装后**重启你的 AI 工具**即可。

## 手动配置

如果你想自己写配置，运行：

```bash
sir mcp config
```

输出类似：

```json
{
  "mcpServers": {
    "sir": {
      "command": "/Users/you/llm/software_intent_runtime/.venv/bin/python",
      "args": ["-m", "sir.mcp"]
    }
  }
}
```

### Claude Code

将上面的 JSON 写入项目根目录 `.mcp.json`，或全局 `~/.claude/mcp.json`。

### Codex (OpenAI)

将 JSON 写入 `~/.codex/mcp.json` 或项目级 `.codex/mcp.json`。

### Cursor

在 Cursor Settings > MCP 中添加，或写入 `.cursor/mcp.json`。

### 其他支持 MCP 的工具

只要支持 stdio transport 的 MCP 客户端都能接入，command 和 args 同上。

## 暴露的工具

安装后 AI 可以调用以下 9 个工具：

| Tool | Description | 需要 LLM？ |
|------|-------------|-----------|
| `sir_init` | 初始化 SIR 项目 | No |
| `sir_apply_patch` | 对架构图应用 patch | No |
| `sir_snapshot_show` | 查看当前架构摘要 | No |
| `sir_snapshot_json` | 获取架构图完整 JSON | No |
| `sir_validate` | 校验架构图正确性 | No |
| `sir_generate` | 从架构图生成代码 | No |
| `sir_patch_list` | 查看 patch 历史 | No |
| `sir_node_kinds` | 列出所有节点类型 | No |
| `sir_edge_types` | 列出所有边类型 | No |

所有工具都不需要 LLM API key。AI 工具自身就是 LLM，它会：
1. 理解你的需求
2. 调 `sir_node_kinds` / `sir_edge_types` 了解 schema
3. 自己构造 patch JSON
4. 调 `sir_apply_patch` 修改架构图
5. 调 `sir_generate` 生成代码

## 使用示例

安装 MCP 后在 Claude Code / Codex 中直接对话：

```
你: "帮我创建一个电商系统，包含用户、商品和订单三个模块"

AI 会自动:
1. sir_init(".", "ecommerce")
2. sir_node_kinds()  -- 了解有哪些节点类型
3. sir_apply_patch(".", '{"description": "Add ecommerce modules", "operations": [...]}')
4. sir_validate(".")
5. sir_generate(".")
6. 告诉你生成了哪些文件
```

```
你: "给订单模块加一个支付workflow"

AI 会自动:
1. sir_snapshot_show(".")  -- 查看当前架构
2. sir_apply_patch(".", '{"description": "Add payment workflow", "operations": [...]}')
3. sir_generate(".")
```

## Patch JSON 格式参考

AI 在调用 `sir_apply_patch` 时需要构造这样的 JSON：

```json
{
  "description": "Add user module with profile component",
  "operations": [
    {
      "op": "add_node",
      "value": {
        "id": "mod_user",
        "kind": "module",
        "name": "User",
        "description": "User management module"
      }
    },
    {
      "op": "add_node",
      "value": {
        "id": "ent_user",
        "kind": "entity",
        "name": "User",
        "description": "User account",
        "properties": {"fields": ["username", "email", "created_at"]}
      }
    },
    {
      "op": "add_node",
      "value": {
        "id": "cmp_profile",
        "kind": "component",
        "name": "Profile",
        "properties": {"methods": ["get_profile", "update_profile"]}
      }
    },
    {
      "op": "add_edge",
      "value": {"from": "sys_root", "to": "mod_user", "type": "contains"}
    },
    {
      "op": "add_edge",
      "value": {"from": "mod_user", "to": "ent_user", "type": "contains"}
    },
    {
      "op": "add_edge",
      "value": {"from": "mod_user", "to": "cmp_profile", "type": "contains"}
    },
    {
      "op": "add_edge",
      "value": {"from": "cmp_profile", "to": "ent_user", "type": "depends_on"}
    }
  ]
}
```

### 节点 ID 命名规范

| Kind | Prefix | Example |
|------|--------|---------|
| system | `sys_` | `sys_root` |
| module | `mod_` | `mod_auth` |
| component | `cmp_` | `cmp_login` |
| entity | `ent_` | `ent_user` |
| interface | `ifc_` | `ifc_auth_service` |
| workflow | `wf_` | `wf_login_flow` |
| capability | `cap_` | `cap_sso` |
| event | `evt_` | `evt_user_created` |
| constraint | `cst_` | `cst_rate_limit` |

### 操作类型

| op | value 格式 |
|----|-----------|
| `add_node` | `{"id", "kind", "name", "description", "properties"}` |
| `remove_node` | `{"id"}` |
| `update_node` | `{"id", ...fields to update}` |
| `add_edge` | `{"from", "to", "type"}` |
| `remove_edge` | `{"from", "to"}` |

## 直接启动 MCP Server

如果不想用 CLI 安装，也可以直接启动：

```bash
# 方式1: 通过 CLI
sir mcp run

# 方式2: 直接 python
python -m sir.mcp

# 方式3: 模块入口
python -c "from sir.mcp.server import app; app.run(transport='stdio')"
```

## 调试

测试 MCP server 是否正常：

```bash
# 打印配置
sir mcp config

# 手动启动看是否报错
sir mcp run
# (会进入 stdio 等待模式，Ctrl+C 退出)
```

如果 AI 工具连不上，检查：
1. Python 路径是否正确（`sir mcp config` 输出的 command）
2. `sir` 包是否安装在该 Python 环境中
3. AI 工具是否重启过
