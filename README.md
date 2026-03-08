# SIR: Software Intent Runtime

> **LLM is LLVM** — treat Large Language Models as compilers, translating human intent through graph IR into software artifacts.

SIR 是一个编译器风格的软件生成框架。核心思想：人类意图是高级语言，LLM 是编译器前端，IR 图是中间表示，生成的代码是目标产物。

```
Human Intent ──→ Intent Parser (LLM) ──→ Patch Builder (LLM) ──→ Patch Engine
                                                                       │
Artifacts ←── Generator ←── Adapter ←── Validator ←── Snapshot (IR) ◄──┘
```

## Why

直接让 LLM 生成代码有三个问题：

1. **无持久状态** — 每次生成都从零开始，没有架构级别的记忆
2. **无结构校验** — 生成的代码可能编译通过，但架构上可能有循环依赖、孤立模块
3. **增量修改差** — "加个支付模块"需要 LLM 重新理解整个代码库

SIR 用一张**有类型的有向图**表示软件架构，LLM 只负责生成图的 patch（增量修改），其余全部是确定性逻辑：

| 阶段 | 谁做 | 确定性？ |
|------|------|---------|
| 意图解析 | LLM | No |
| Patch 构建 | LLM | No |
| Patch 应用 | Engine | **Yes** |
| 图校验 | Validator | **Yes** |
| 路径生成 | Adapter | **Yes** |
| 代码生成 | Generator | **Yes** |

## Quick Start

```bash
# 安装
git clone https://github.com/Runrun-mu/SIR-LLM-is-LLVM.git
cd SIR-LLM-is-LLVM
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 初始化项目
mkdir demo && cd demo
sir init my_app

# 用 LLM 编译意图
export OPENAI_API_KEY=sk-...
sir compile "Create an authentication module with login and session management"

# 或用其他 provider
sir compile "Add payment module" -p anthropic
sir compile "Add payment module" -p deepseek
sir compile "Add payment module" -p gemini
sir compile "Add payment module" --base-url http://localhost:11434/v1 -m llama3

# 查看结果
sir snapshot show       # 查看架构图
sir validate            # 校验
sir generate            # 重新生成代码（不调 LLM）
sir patch list          # 查看修改历史
```

## IR Graph

架构用有向图表示，节点有类型，边有类型：

```
[system] sys_root: "MyApp"
    ├── contains ──→ [module] mod_auth: "Auth"
    │                   ├── contains ──→ [component] cmp_login: "Login"
    │                   ├── contains ──→ [entity] ent_user: "User"
    │                   ├── contains ──→ [interface] ifc_auth: "Auth Service"
    │                   └── contains ──→ [workflow] wf_login: "Login Flow"
    └── contains ──→ [module] mod_payment: "Payment"
                        └── ...
```

**Node kinds:** `system` `module` `component` `interface` `entity` `capability` `workflow` `event` `constraint`

**Edge types:** `contains` `depends_on` `implements` `emits` `consumes` `triggers` `constrains`

## Patch System

LLM 不直接改图，而是生成 Patch（类似 git diff）：

```json
{
  "description": "Add user entity to auth module",
  "operations": [
    {"op": "add_node", "value": {"id": "ent_user", "kind": "entity", "name": "User", "properties": {"fields": ["username", "email"]}}},
    {"op": "add_edge", "value": {"from": "mod_auth", "to": "ent_user", "type": "contains"}}
  ]
}
```

Patch engine 是**纯确定性**的：同样的 snapshot + 同样的 patch = 同样的结果。Validator 在 patch 应用后自动校验：

- System 节点唯一
- Node ID 不重复
- 无 dangling edge（引用不存在的节点）
- Contains 边构成 DAG（无环）
- 孤立节点警告

## MCP Server

SIR 可以作为 MCP 服务接入 Claude Code / Codex / Cursor：

```bash
# 一键安装
sir mcp install                    # Claude Code（当前项目）
sir mcp install -t codex           # Codex
sir mcp install -s user            # 全局安装

# 手动查看配置
sir mcp config
```

安装后 AI 工具可以调用 9 个工具：

| Tool | Description |
|------|-------------|
| `sir_init` | 初始化 SIR 项目 |
| `sir_apply_patch` | 应用架构 patch |
| `sir_snapshot_show` | 查看架构摘要 |
| `sir_snapshot_json` | 获取完整架构 JSON |
| `sir_validate` | 校验架构正确性 |
| `sir_generate` | 从架构生成代码 |
| `sir_patch_list` | 查看 patch 历史 |
| `sir_node_kinds` | 列出节点类型 |
| `sir_edge_types` | 列出边类型 |

接入后 AI 会自动通过 patch 操作架构图，而不是直接生成代码。详见 [MCP_SETUP.md](MCP_SETUP.md)。

## LLM Providers

默认 OpenAI，支持所有 OpenAI 兼容 API：

| Provider | 环境变量 | 默认模型 |
|----------|---------|---------|
| `openai` | `OPENAI_API_KEY` | gpt-4o |
| `anthropic` | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 |
| `deepseek` | `DEEPSEEK_API_KEY` | deepseek-chat |
| `gemini` | `GEMINI_API_KEY` | gemini-2.0-flash |
| 自定义 | `--base-url` + `--api-key` | `--model` |

```bash
# Ollama 本地模型
sir compile "Add auth" --base-url http://localhost:11434/v1 -m llama3

# vLLM / TGI / 任何 OpenAI 兼容
sir compile "Add auth" --base-url http://my-server:8000/v1 -m my-model --api-key sk-xxx
```

## Generated Code

Generator 根据节点类型生成 Python 骨架：

| Node Kind | 生成内容 |
|-----------|---------|
| Module | 目录 + `__init__.py` |
| Entity | `@dataclass` 类 |
| Component | Class + method stubs |
| Interface | ABC + `@abstractmethod` |
| Workflow | Function + step comments |

```
output/
├── auth/
│   ├── __init__.py
│   ├── models.py              # User, Session dataclasses
│   ├── components/
│   │   └── login.py           # Login class
│   ├── services/
│   │   └── auth_service.py    # AuthService ABC
│   └── workflows/
│       └── login_flow.py      # login_flow() function
└── sir_project.json           # Project config
```

## Project Structure

```
sir/
├── ir/           # Intermediate Representation (Node, Edge, Snapshot, Graph, Validator)
├── intent/       # LLM intent parser (natural language → IntentSpec)
├── patch/        # Patch system (schema, LLM builder, deterministic engine)
├── adapter/      # IR → ProjectSnapshot lowering (path generation)
├── generator/    # Code generation (Python stubs, JSON config)
├── store/        # .sir/ directory persistence (JSON files)
├── pipeline/     # CompilePipeline orchestrator
├── llm/          # Multi-provider LLM abstraction
├── mcp/          # MCP server (9 tools)
└── cli/          # Click CLI
```

## Testing

```bash
pytest tests/ -v    # 105 tests, all passing
```

测试覆盖所有确定性模块（IR、patch engine、validator、adapter、generator、store、CLI、MCP tools）。LLM 相关模块通过 mock provider 测试。

详见 [TEST_REPORT.md](TEST_REPORT.md)。

## Docs

- [GUIDE.md](GUIDE.md) — 模块详解 + 核心链路 + 维护指南
- [TEST_REPORT.md](TEST_REPORT.md) — 测试报告
- [MCP_SETUP.md](MCP_SETUP.md) — MCP 接入指南
- [paper/sir_paper.tex](paper/sir_paper.tex) — 论文（LaTeX）

## The Compiler Analogy

| Compiler | Traditional | SIR |
|----------|------------|-----|
| Source language | C / Java | Natural language |
| Frontend | Lexer + Parser | Intent Parser (LLM) |
| IR | SSA / LLVM IR | Graph IR (nodes + edges) |
| Optimization | Dead code elimination | Patch Builder (LLM) |
| Lowering | IR → machine IR | Adapter (IR → ProjectSnapshot) |
| Backend | x86 / ARM codegen | Python / Config Generator |
| Object files | .o / .class | Generated source files |
| Type checker | Type system | Snapshot Validator |

## License

MIT
