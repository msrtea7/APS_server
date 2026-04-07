# AVEVA SimCentral MCP — 开发文档

## 架构总览

```
Mac (Client)                          Windows (Server)
─────────────────────────────         ──────────────────────────
MCP Server (Python)                   FastAPI REST Server
  ├── system prompt / skills   ──→      api_server.py
  ├── tool definitions                    └── aveva_tools.py
  └── aveva_client.py          ──HTTP──→       └── simcentralconnect (.NET)
                                                      └── AVEVA SimCentral
```

**核心原则：**
- Server 端只负责执行，不做任何推理
- Client 端负责 context 质量，skills，工具定义
- AVEVA 是 source of truth，不在任何地方维护副本状态
- 静态知识（model 类型、port schema）持久化；动态状态（connector、variable 值）按需 fetch

---

## 命名规范（第0级，写入 system prompt）

### 路径规则

```
变量路径:    {model_name}.{variable_name}         → Feed.T
参数路径:    {model_name}.{parameter_name}         → Feed.FluidType
Port路径:    {model_name}.{port_name}              → Feed.Out
带流名Port:  {model_name}.{port_name}[{stream}]   → DistColumn.Fin[S1]
```

### Few-shot Examples

```
# 读取温度
variable_path = "Feed.T"          # Source 模型，温度变量

# 设定压力
variable_path = "Feed.P"          # Source 模型，压力变量，单位 kPa

# 连接两个 model
from_port = "Feed.Out"
to_port   = "DistColumn.Fin[S1]"  # S1 是 connector 的名字

# 设定参数
parameter_path = "Feed.FluidType"
```

### Variable vs Parameter 区别

| 类型 | 含义 | 工具 | 例子 |
|------|------|------|------|
| Variable | 操作条件，运行时值 | `variable/set` | T, P, W, F |
| Parameter | 模型配置，枚举选项 | `parameter/set` | FluidType, CompBasis |

---

## Skills（第一级）

Skills 放在 **Client 端**，按场景分文件，session 开始时按需加载。

### Skill 文件结构

```
skills/
  aveva_base.md          # 通用规范，命名规则，工具使用说明
  aveva_distillation.md  # 蒸馏场景：model 类型、port、典型变量范围
  aveva_heat_exchange.md # 换热场景
  aveva_reaction.md      # 反应器场景
```

### aveva_distillation.md（第一个 Skill，当前场景）

```markdown
## 可用 Model 类型

| 名称 | AVEVA 路径 | 用途 |
|------|-----------|------|
| Source | Lib:Process.Source | 进料边界 |
| Sink | Lib:Process.Sink | 出料边界 |
| Column | Lib:Process.Column | 蒸馏塔 |
| Drum | Lib:Process.Drum | 闪蒸罐/分离器 |
| HeatExchanger | Lib:Process.HX | 换热器 |

## Column Port 信息

| Port | 方向 | 格式 | 说明 |
|------|------|------|------|
| Fin | in | Column.Fin[{stream_name}] | 进料口，支持多股进料 |
| Vout | out | Column.Vout | 塔顶气相出口 |
| Lout | out | Column.Lout | 塔底液相出口 |

## Source Port 信息

| Port | 方向 | 格式 |
|------|------|------|
| Out | out | Source.Out |

## Sink Port 信息

| Port | 方向 | 格式 |
|------|------|------|
| In | in | Sink.In |

## 典型变量

| 变量 | 单位 | 说明 |
|------|------|------|
| T | K | 温度 |
| P | kPa | 压力 |
| W | kg/s | 质量流量 |
| F | kmol/s | 摩尔流量 |
| z[component] | mole fraction | 摩尔组成 |
| M[component] | - | 非归一化摩尔进料量 |
| Mt | - | 归一化基准，设为 1 |
```

---

## 动态信息管理（第二级）

### 原则

| 信息类型 | 是否持久化 | 存放位置 | 更新方式 |
|---------|-----------|---------|---------|
| Model 类型 + port schema | ✅ 持久化 | Client 端 skill 文件 | 手动维护 |
| 当前 flowsheet connector | ❌ 不持久化 | context | session 开始时 fetch 一次 |
| 当前变量值 | ❌ 不持久化 | context | 按需 fetch |

### 搭建流程（Building）

LLM 自己在操作，所有 tool call 的 result 都在 context 里，不需要额外机制。

```
[tool] add_model(Source) → {model_name: "Feed"}         ← 在 context 里
[tool] add_model(Column) → {model_name: "DistColumn"}   ← 在 context 里
[tool] connect_models(Feed.Out, DistColumn.Fin[S1])     ← 在 context 里
LLM 直接从 context 读取当前拓扑状态，无需额外查询
```

### 分析流程（Analysis）

打开已有 simulation 时，执行一次标准初始化序列：

```python
# session 开始时执行，结果进入 context
open_simulation(sim_name)
show_models_on_flowsheet(sim_name)      # → model 列表
show_connectors_on_flowsheet(sim_name)  # → 拓扑结构
# 按需查询具体 model 的变量和参数
show_one_model_var(sim_name, model_name)
show_one_model_param(sim_name, model_name)
```

用户在 AVEVA 里手动修改后，重新执行初始化序列即可。

---

## 工具列表（精简后）

### 删除

| 工具 | 原因 |
|------|------|
| `take_snapshot` | 空实现，API 调用被注释 |
| `get_simulation_models` | 与 `show_models_on_flowsheet` 重复，后者信息更丰富 |

### 新增

| 工具 | 端点 | 说明 |
|------|------|------|
| `show_all_ports` | `/flowsheet/ports` | 查询 simulation 内所有 model 的 port 信息 |

### 完整工具表

**连接管理（2个）**

| 工具 | 端点 | 方法 |
|------|------|------|
| connect_to_aveva | /connect | POST |
| get_connection_status | /status | GET |

**Simulation 管理（6个）**

| 工具 | 端点 |
|------|------|
| get_available_simulations | GET /simulations |
| create_simulation | POST /simulation/create |
| open_simulation | POST /simulation/open |
| save_simulation | POST /simulation/save |
| close_simulation | POST /simulation/close |
| delete_simulation | POST /simulation/delete |
| rename_simulation | POST /simulation/rename |
| get_simulation_status | POST /simulation/status |

**Model 管理（4个）**

| 工具 | 端点 |
|------|------|
| add_model | POST /model/add |
| remove_model | POST /model/remove |
| remove_multiple_models | POST /model/remove-many |
| rename_model | POST /model/rename |

**Connector 管理（4个）**

| 工具 | 端点 |
|------|------|
| connect_models | POST /connector/connect |
| get_connector_list | POST /connector/list |
| remove_connector | POST /connector/remove |
| remove_multiple_connectors | POST /connector/remove-many |

**Variable 读写（4个）**

| 工具 | 端点 |
|------|------|
| get_variable_value | POST /variable/get |
| set_variable_value | POST /variable/set |
| get_multiple_variables | POST /variable/get-many |
| set_multiple_variables | POST /variable/set-many |

**Parameter 管理（2个）**

| 工具 | 端点 |
|------|------|
| update_parameter | POST /parameter/set |
| update_parameters | POST /parameter/set-many |

**Fluid 管理（2个）**

| 工具 | 端点 |
|------|------|
| create_fluid_complete | POST /fluid/create |
| set_fluid_of_source | POST /fluid/assign |

**Snapshot 管理（2个）**

| 工具 | 端点 |
|------|------|
| create_snapshot | POST /snapshot/create |
| get_all_snapshots | POST /snapshot/list |

**查询 / 探索（5个）**

| 工具 | 端点 | 说明 |
|------|------|------|
| show_models_on_flowsheet | POST /flowsheet/models | model 列表 + 类型 |
| show_connectors_on_flowsheet | POST /flowsheet/connectors | 拓扑连接 |
| show_one_model_param | POST /model/params | 某 model 的参数 |
| show_one_model_var | POST /model/vars | 某 model 的变量 |
| show_all_ports | POST /flowsheet/ports | 所有 model 的 port |

**总计：31个**

---

## 需要修复的问题

### config.py 中的错误 Template

`SIMULATION_TEMPLATES` 里的蒸馏模板有错误，如果被 LLM 当作知识使用会直接导致失败：

```python
# ❌ 错误（当前代码）
{"type": "Distillation", ...}          # 不存在，应为 "Column"
{"from": "Feed.Out", "to": "Column1.Feed"}     # port 名字错
{"from": "Column1.Distillate", ...}             # port 名字错

# ✅ 正确（基于实验验证）
{"type": "Column", ...}
{"from": "Feed.Out", "to": "DistColumn.Fin[S1]"}
{"from": "DistColumn.Lout", "to": "Bottoms.In"}
```

建议：删除 `SIMULATION_TEMPLATES` 和 `AGENT_PROMPTS`，这两块是论文 multi-agent 架构的残留，不需要。

### show_all_ports 需要融合进 Server 端

已有独立脚本 `src/print_all_ports.py`，需要：
1. 将逻辑移入 `aveva_tools.py` 作为 `show_all_ports(sim_name)` 函数
2. 在 `api_server.py` 添加 `POST /flowsheet/ports` 端点
3. 在 `aveva_client.py` 添加对应的 HTTP 封装

---

## 开发优先级

```
P0  修复 config.py 中的错误 template
P0  融合 show_all_ports 进工具链
P1  编写 aveva_distillation.md skill（基于本文档）
P1  删除 take_snapshot 和 get_simulation_models
P2  编写其他场景的 skill 文件
```