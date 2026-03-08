# SIR (Software Intent Runtime) - Usage Guide

## Overview

SIR 是一个编译器风格的 Agent 执行架构。核心洞察：**LLM 本质上是编译器**，将人类语言（高级语言）编译成软件制品（代码、配置等）。

SIR 使用 IR（中间表示）作为核心抽象，将"人类意图"经过多阶段编译，最终生成可运行的代码骨架。

```
Human Intent → Intent Parser (LLM) → Patch Builder (LLM) → Patch Engine → Snapshot → Adapter → Generator → Artifacts
```

---

## Quick Start

```bash
# 安装
cd software_intent_runtime
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 初始化项目
mkdir my_project && cd my_project
sir init my_project

# 用 LLM 编译意图（需要 ANTHROPIC_API_KEY）
export ANTHROPIC_API_KEY=sk-ant-...
sir compile "Create an authentication module with login and session management"

# 查看结果
sir snapshot show
sir patch list
sir validate

# 重新生成代码（不调用 LLM）
sir generate
```

---

## Module Reference

### 1. `sir/ir/` - Intermediate Representation

**职责**：定义系统的核心数据模型——图结构的节点和边。

#### `schema.py` - 数据模型

```
NodeKind: system | module | component | interface | entity | capability | workflow | event | constraint
EdgeType: contains | depends_on | implements | emits | consumes | triggers | constrains
```

- **Node**: 图中的一个实体（`id`, `kind`, `name`, `description`, `properties`）
- **Edge**: 节点之间的关系（`from`, `to`, `type`）。`from` 是 Python 关键字，使用 Pydantic alias 处理：`from_node: str = Field(alias="from")`
- **Snapshot**: 某一时刻的完整图状态（`version`, `nodes[]`, `edges[]`）

#### `graph.py` - 图操作

将 Snapshot 包装为 NetworkX DiGraph，提供：
- `children(node_id)` - 查找 contains 子节点
- `ancestors(node_id)` - 查找 contains 父节点
- `has_contains_cycle()` - 检测 contains 边是否成环
- `orphan_nodes()` - 找出没有任何边的节点
- `dangling_edges()` - 找出引用不存在节点的边

#### `validator.py` - 图校验

对 Snapshot 执行完整性校验：
- System 节点唯一
- Node ID 不重复
- 无 dangling edge
- Contains 边构成 DAG（无环）
- 孤立节点警告（warning，不是 error）

---

### 2. `sir/intent/` - Intent Parsing

**职责**：将自然语言解析为结构化的 IntentSpec。

#### `schema.py` - IntentSpec 模型

```python
IntentSpec:
  action: create | modify | delete | query
  targets: [{kind, name, description, properties}]
  context: str
  constraints: [str]
  raw_input: str
```

#### `parser.py` - LLM Intent Parser

- 使用 Claude API（claude-sonnet-4-20250514）
- System prompt 包含所有 NodeKind/EdgeType 枚举 + IntentSpec schema + 当前 snapshot 摘要
- 从 LLM 响应中提取 JSON（支持 markdown code block）

---

### 3. `sir/patch/` - Patch System

**职责**：以原子操作修改 Snapshot。类似 git diff，但作用于图结构。

#### `schema.py` - Patch 模型

```python
PatchOperation:
  op: add_node | remove_node | update_node | add_edge | remove_edge
  value: dict  # node 或 edge 数据

Patch:
  description: str
  operations: [PatchOperation]
```

#### `builder.py` - LLM Patch Builder

- 接收 IntentSpec + 当前 Snapshot，生成 Patch
- Prompt 规定 ID 命名规范：`mod_`, `cmp_`, `ent_`, `ifc_`, `wf_`, `cap_`, `evt_`, `cst_`
- 规定操作顺序：`add_node` 必须在引用该 node 的 `add_edge` 之前

#### `engine.py` - Patch Engine

纯确定性引擎，不调用 LLM：
- `apply_patch(snapshot, patch) -> Snapshot` 返回新 snapshot（版本号 +1）
- `add_node`: 检查 ID 不重复
- `remove_node`: 级联删除所有关联 edge
- `update_node`: 部分字段更新
- `add_edge`: 校验 from/to 节点存在
- `remove_edge`: 精确匹配 from+to

---

### 4. `sir/adapter/` - Adapter Layer

**职责**：将通用 IR Snapshot "降低"（lower）为项目级别的 ProjectSnapshot，生成文件路径。

#### `schema.py` - ProjectNode/ProjectSnapshot

```python
ProjectNode:
  id: str          # proj_{original_id}
  source_id: str   # 原始 IR node ID
  kind: str
  name: str
  path: str        # 生成的相对文件路径
```

#### `generic.py` - Generic Adapter

1:1 映射，基于 contains 层级生成目录路径：

| NodeKind | Path Pattern |
|----------|-------------|
| Module | `{snake_name}/` |
| Component | `{module}/components/{name}.py` |
| Entity | `{module}/models.py` |
| Interface | `{module}/services/{name}.py` |
| Workflow | `{module}/workflows/{name}.py` |
| Others | `{module}/{name}.py` |

通过遍历 contains 边向上查找父 module 来确定路径前缀。

#### `registry.py` - Adapter Registry

注册/查找 adapter 实例。默认提供 `generic` adapter，可通过 `register_adapter()` 扩展。

---

### 5. `sir/generator/` - Code Generation

**职责**：从 ProjectSnapshot 生成实际文件。

#### `python_gen.py` - Python Generator

| NodeKind | 生成内容 |
|----------|---------|
| Entity | `@dataclass` 类，字段来自 `properties.fields` |
| Component | 普通类 + 方法 stub（`pass`） |
| Interface | `ABC` 抽象类 + `@abstractmethod` |
| Workflow | 函数 + step 注释 |
| Module | 目录 + `__init__.py` |

同一 module 下的多个 Entity 合并到同一个 `models.py` 文件。

#### `config_gen.py` - Config Generator

生成 `sir_project.json` 项目配置文件，包含 module 列表和子组件信息。

---

### 6. `sir/store/` - Persistence

**职责**：管理 `.sir/` 目录结构和 JSON 文件持久化。

```
.sir/
├── config.json           # 项目配置
├── snapshots/
│   ├── v1.json           # 版本快照
│   ├── v2.json
│   └── current.json      # 当前快照（最新版本的拷贝）
└── patches/
    ├── patch_0000.json   # 第一个 patch
    └── patch_0001.json   # 第二个 patch
output/                   # 生成的代码
├── auth/
│   ├── __init__.py
│   ├── models.py
│   ├── components/
│   │   └── login.py
│   ├── services/
│   │   └── auth_service.py
│   └── workflows/
│       └── login_flow.py
└── sir_project.json
```

---

### 7. `sir/pipeline/` - Pipeline Orchestrator

**职责**：编排整个编译流程。

`CompilePipeline.compile(user_input)` 执行：

```
1. load_snapshot()           # 加载当前快照
2. intent_parser.parse()     # LLM: 自然语言 → IntentSpec
3. patch_builder.build()     # LLM: IntentSpec + Snapshot → Patch
4. apply_patch()             # 确定性: Patch + Snapshot → New Snapshot
5. validate_snapshot()       # 校验新快照
6. save_patch() + save_snapshot()  # 持久化
7. adapter.lower()           # IR Snapshot → ProjectSnapshot
8. generator.generate()      # ProjectSnapshot → Files
```

`generate_from_snapshot()` 跳过 LLM 步骤，从当前 snapshot 直接重新生成代码。

---

### 8. `sir/cli/` - CLI Interface

| Command | Description |
|---------|-------------|
| `sir init <name>` | 初始化 .sir/ 目录 + 空 snapshot |
| `sir compile "<intent>"` | 完整 pipeline（需要 API key） |
| `sir snapshot show` | 显示当前 snapshot 摘要 |
| `sir snapshot json` | 输出 snapshot JSON |
| `sir patch list` | 查看 patch 历史 |
| `sir generate` | 从当前 snapshot 重新生成代码 |
| `sir validate` | 校验当前 snapshot |

---

## Core Pipeline Deep Dive

### 数据流

```
"Add auth module"  ──[IntentParser]──>  IntentSpec{action:create, targets:[{kind:module, name:Auth}]}
                                              │
                                              ▼
                   ──[PatchBuilder]──>  Patch{ops: [add_node(mod_auth), add_edge(sys->mod_auth), ...]}
                                              │
Snapshot v1 ──────────[PatchEngine]──> Snapshot v2 (with new nodes/edges)
                                              │
                   ──[Validator]──────> ValidationResult{valid:true}
                                              │
                   ──[GenericAdapter]──> ProjectSnapshot{nodes with file paths}
                                              │
                   ──[PythonGenerator]─> Files on disk (auth/models.py, auth/components/login.py, ...)
```

### IR 图结构示例

```
[system] sys_root: "MyApp"
    ├── [module] mod_auth: "Auth"
    │   ├── [component] cmp_login: "Login"        (implements ifc_auth)
    │   ├── [entity] ent_user: "User"
    │   ├── [entity] ent_session: "Session"
    │   ├── [interface] ifc_auth: "Auth Service"
    │   └── [workflow] wf_login: "Login Flow"
    └── [module] mod_user: "User Management"
        └── [component] cmp_profile: "Profile"
```

contains 边构成树形层级，depends_on/implements 等边表达跨模块关系。

---

## Maintenance Guide

### 添加新的 NodeKind

1. 在 `sir/ir/schema.py` 的 `NodeKind` 枚举中添加新值
2. 在 `sir/adapter/generic.py` 的 `_resolve_path()` 中添加路径规则
3. 在 `sir/generator/python_gen.py` 中添加对应的代码生成函数，并注册到 `_GENERATORS` 字典
4. 更新 intent parser 和 patch builder 的 system prompt（它们动态读取枚举值）
5. 添加测试

### 添加新的 Adapter

1. 创建 `sir/adapter/my_adapter.py`，继承 `Adapter` 基类
2. 实现 `lower(snapshot) -> ProjectSnapshot` 方法
3. 在 `sir/adapter/registry.py` 中注册：`_ADAPTERS["my_adapter"] = MyAdapter`
4. 在 pipeline 中通过 `get_adapter("my_adapter")` 使用

### 添加新的 Generator

1. 创建 `sir/generator/my_gen.py`，继承 `Generator` 基类
2. 实现 `generate(project, output_dir) -> ArtifactManifest`
3. 在 `sir/pipeline/compile.py` 的 `_generate()` 方法中调用

### 修改 LLM Prompt

- Intent parser prompt: `sir/intent/parser.py` 的 `SYSTEM_PROMPT`
- Patch builder prompt: `sir/patch/builder.py` 的 `SYSTEM_PROMPT`
- 两者都使用 f-string 动态注入枚举值和 snapshot 数据

### 数据迁移

snapshot 的 `version` 字段是递增的整数。如果 schema 变更：
1. 所有旧 snapshot JSON 仍然保存在 `.sir/snapshots/v{N}.json`
2. 可以添加 migration 函数在 `FileStore.load_snapshot()` 中做版本适配
3. Pydantic v2 的 `model_validate()` 天然支持向后兼容（新字段有默认值即可）

### 运行测试

```bash
# 全部测试
pytest tests/ -v

# 单个模块
pytest tests/test_ir_schema.py -v

# 只跑 e2e
pytest tests/test_e2e.py -v
```
