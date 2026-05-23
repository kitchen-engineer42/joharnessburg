# joharnessburg

**John** —— 一个 Claude Code 插件，通过 skills、hooks、slash commands 和一套小工具包装 Claude Code，让它能在一个长时间运行的会话中完成从非结构化输入（书籍、法规、混合文档）到知识工程再到应用构建的全流程。

插件 slug：`joharnessburg`。读作 "jo-harness-burg"（harness 在中间），或者按城市谐音读 "jo-hannesburg" 也行。

> English README: [`README.md`](README.md)

## 当前状态

**v0.1.9 —— Codex 代码评审修复 + 审计驱动加固。** 基于 Codex（GPT-5.5）对 v0.1.8 的代码评审（`docs/codebase_review_codex_2026-05-23.md`，13 项发现全部为真）以及 v0.1.8 端到端测试（017-test-001）的审计子代理综合结果，本次共修复 19 项问题，分 5 个实施块完成（约 9-12 小时）：

- **Tier 1 正确性 bug**：`init_workspace.py` 现在消费 `templates-active/plan_md_template.md` 和 `claude_addon.md`（v0.1.7 写入但被忽略的契约违规已修复）；`set_template.py` 原子化（先 apply 后写 workspace.json；失败时记录 `active_template_pending` + `active_template_error` 取证字段）；模板 `scripts/`/`commands/`/`agents/` 现强制为 additive-only（与核心文件冲突时跳过 + 警告 + 在 `.applied-metadata.json` 中记录）；`ppx_parse.py` 修复 `HTTPError` 被 `URLError` 屏蔽的 bug（现在 422 响应能正确暴露而不是被报告为"无法连接服务器"）；`reduce_events.py --dry-run` 现为只读（不再悄悄移动格式错误的事件）。
- **Tier 2 防御性 + 审计缺口**：`copy_input` 递归过滤隐藏文件（嵌套 `.git/` 不再泄漏进 `.john/input/`）；`start_john.sh` / `stop_john.sh` 通过 `ps -p $pid -o command=` 验证 PID 身份（防御 macOS PID 复用）；ppx 服务器对 `backend`/`ocr`/`table` 用 Pydantic `Literal` 校验（无效输入返回 422 而非 500）；`knowledge-extractor` 和 `schema-designer` agent prompt 改为字面量 JSON 模板 + 封闭枚举值（消除 v0.1.8 asset_mgmt 10 子代理并行中观察到的 5 种字段名漂移）；`reduce_events.py` 新增 chunk_echo 完整性校验（缺失 chunk_echo 或 chunk_complete 的 chunk 计入 `state.json` 的 `incomplete_chunks`）。
- **文档清理**：删除 `skills/spec-template-manager/`（描述的是 John 显式取代的 spec.md 遗留契约；一行规则迁移到 `using-john`）；重写 PLAN.md §13 反映 v0.1.7+ diff-script 架构 + v0.1.8 按会话隔离；更新 `commands/joharnessburg-template.md` 反映 v0.1.8 多 applied 共存；`local_clients/ppx/README.md` 新增"安全边界"章节；`git rm --cached` 两个被跟踪的 `.pyc` 文件；新增 `scripts/parse_govcn_html.py`（基于标准库的中国政府法规 HTML 备用解析器）+ 参考文档 `skills/parsing/references/gov-cn-html.md`（M6 和 v0.1.8 验证运行都临时重新发明过此解析器——现在统一了，v0.1.7 D6 决定逆转）。
- **FastAPI 服务器测试**：`local_clients/{llm,ppx}/` 各新增 7 个测试（共 14 个），使用 `fastapi.testclient.TestClient`，测试覆盖 healthz、模型路由、Literal 校验、provider 路由 + 错误路径。

**85 个插件单元测试 + 14 个 FastAPI 服务器测试 = 99 个测试全绿。**

**v0.1.8 —— 多模板按会话隔离补丁 + v0.1.7 架构。** v0.1.8 放宽了 `apply_template.py` 的跨模板拒绝逻辑：现在多个已应用的模板目录（`~/.claude/plugins/joharnessburg-applied/` 下）可以自由共存，并行的 Claude Code 会话可以分别使用不同的模板、互不干扰。`--reset-all` 仍可用于显式清盘场景。**65 个单元测试全绿。**

**v0.1.7 —— 本地客户端架构 + 模板 diff-script + 审计驱动的清理。** v0.1.6 之上的一次重大架构重构：

- **外部本地客户端服务器**（位于 workspace 一级、插件外部）：`/Users/mac/Desktop/john/local_clients/{llm,ppx}/` 下的 FastAPI HTTP 服务器，分别封装 SiliconFlow + DeepSeek（OpenAI 兼容接口）和 `memect-ppx`。John 通过环境变量（`$JOHN_LLM_CLIENT_URL`、`$JOHN_PPX_CLIENT_URL`）调用它们。等技术团队部署生产服务器时，换 URL 即可——John 内部一行代码都不用改。
- **模板 diff-script 架构**：模板现在是通过 `apply_template.py`（一键执行）应用的 diff，不再是会话期间的覆盖层。结果：在 `~/.claude/plugins/joharnessburg-applied/<name>/` 生成一个合并后的插件目录，用户用 `claude --plugin-dir <path>` 启动。合并之后，模板内容就是 John 本身——没有二等公民层。
- **新增 skill** `workerllm-runtime/` 教产出的应用如何调用 LLM 客户端。
- **JSON 规范**已添加到全部 3 个 agent prompt 中（推荐使用全角引号 / `json.dumps()`，避免 M6 阶段观察到的约 10% 缺陷率）。
- **Reducer 隔离机制**：`reduce_events.py` 现在会把格式错误的事件移到 `_quarantine/` 下而不是悄悄跳过；计数会显式上报。
- **ppx ↔ jyppx 术语清理**：13 个文件中的 23 处提及全部对齐。`ppx_parse.py` 现在写入 `"parser": "ppx"`（之前是 `"jyppx"`——v0.1.7 的一次软 schema break）。
- **Bug 修复**：PreCompact hook 的 TOCTOU 竞态、`markitdown_parse.py` 的静默回退、`set_template.py` 中硬编码路径、`init_workspace.py` 中 --force 的 docstring、`workspace_status.py` 的 is_dir 防护。

**64 个单元测试全绿**（53 个来自 v0.1.6 + 6 个 apply_template + 5 个 reset_john 测试）。插件加载内容：8 个核心 meta-skill + 6 个 2skills 阶段 skill + 3 个 2app 阶段 skill + 9 个 platform 集成 skill 桩 + 新的 `workerllm-runtime` skill（共 27 个） + 7 个工具脚本 + 2 个新的模板系统脚本（apply_template、reset_john） + 5 个 slash command + 3 个 hook + 3 个 agent + 2 个带一键 `apply.sh` 的示例模板。M7（交接文档）还在路上。

## 模板（v0.1.7+ diff-script 架构）

模板是 **原始 John 的 diff**，通过一键脚本应用。`/joharnessburg-template <name>` 一条命令完成全流程：在 workspace.json 中设置 active_template、运行 apply.sh、打印启动命令。

- **作者指南**：[`templates/README.md`](templates/README.md) —— 目录结构、应用机制、切换/重置流程。
- **内置示例**：[`templates/examples/slides-from-textbook/`](templates/examples/slides-from-textbook/)（较轻量 —— 1 个 override + 1 个新增）和 [`templates/examples/doc-verification/`](templates/examples/doc-verification/)（较重，KC 风格 —— 2 个 override + 2 个新增）。两者都带 `apply.sh` 软链。

两个内置示例都是**功能演示**，不是生产级模板。团队的生产模板会单独交付。

## 本地客户端（workspace 级别，插件外部）

LLM + ppx 客户端在你的 John workspace 中、**插件外部**：`local_clients/{llm,ppx}/`。它们是独立的 FastAPI 服务器——由团队在本地安装 + 启动；插件的 `parsing` + `workerllm-runtime` skill 教 Claude 通过环境变量配置的 URL（`$JOHN_LLM_CLIENT_URL`、`$JOHN_PPX_CLIENT_URL`）来调用它们。

等技术团队上生产服务器时，把这两个环境变量换成生产 URL 即可；John 内部不需要任何改动。

### 一次性安装（每台机器一次）

前提：你已经有 John workspace（里面包含 `local_clients/`、`setup_john.sh` 等），并且安装了 `uv`（https://docs.astral.sh/uv/）。

```sh
# 1. 把 ppx 引擎 clone 到 workspace 之外的某个位置
git clone https://github.com/kitchen-engineer42/ppx.git ~/code/ppx

# 2. 运行 workspace 的安装脚本——它会创建 venv 并安装两个客户端
cd /path/to/john-workspace
./setup_john.sh
# 首次运行会从 .env.example 创建 .env，并提示你填入密钥。
# 编辑 .env，填入 SILICONFLOW_API_KEY 和 DEEPSEEK_API_KEY，再次运行 setup_john.sh。

# 3. 把 ppx 引擎安装到 ppx 客户端的 venv 中
cd /path/to/john-workspace/local_clients/ppx
uv pip install -e ~/code/ppx

# 4. 验证
cd /path/to/john-workspace
./setup_john.sh
# 应该报告："memect-ppx is installed in the ppx client's venv."
```

### 每个会话的启动

```sh
cd /path/to/john-workspace
./start_john.sh
# 会报告两个客户端的健康状态，并打印需要 export 的环境变量。

# 然后在你打算用 Claude Code 的 shell 中（或持久化到 .zshrc / .bashrc）：
export JOHN_LLM_CLIENT_URL=http://localhost:8500
export JOHN_PPX_CLIENT_URL=http://localhost:8501

# 在你的项目目录下启动 Claude Code：
cd /path/to/your-project
claude
```

停止服务器：

```sh
cd /path/to/john-workspace
./stop_john.sh
```

### Smoke test（端到端验证整条链路）

```sh
# LLM 客户端健康检查 + 提供商清单
curl -s http://localhost:8500/healthz | jq

# 实际调用一次 LLM（应该返回 "OK" 或类似内容）
curl -s http://localhost:8500/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"reply with just OK"}]}' | jq

# ppx 客户端健康检查（应当报告 "ppx: available"）
curl -s http://localhost:8501/healthz | jq
```

### 参考文档

- `local_clients/llm/README.md` —— LLM 客户端的安装 + API 契约
- `local_clients/ppx/README.md` —— ppx 客户端的安装 + API 契约
- Workspace 下的 `/skills/local-clients-builder/` —— 针对不同的 provider 或自建（on-prem）基础设施编写客户端的方法论（与 skill-creator 平行）
- `joharnessburg/skills/workerllm-runtime/SKILL.md` —— 插件中的 skill 如何指导 Claude 调用这些客户端

## 依赖

- **Python 3.10+**（工具脚本只用标准库；系统自带的 Python 就够用）。
- 非 PDF 文档解析（`markitdown_parse.py`）：`pip install markitdown`。
- PDF 解析：v0.1.7+ 通过插件外部的 **ppx-client 服务器**（FastAPI）封装 `memect-ppx`（即 `ppx` 解析引擎，仓库在 `github.com/kitchen-engineer42/ppx`）。插件中的 `scripts/ppx_parse.py` 只是这台服务器的一个瘦 HTTP 客户端；服务器源代码在 `/Users/mac/Desktop/john/local_clients/ppx/`，用 `scripts/start.sh` 启动。ppx 引擎本身需要安装（`uv pip install -e /path/to/ppx`）；`jyppx` 是另一个独立的 builder 项目，它把 ppx 当作库来用，**不是** 驱动 John 所必需的。

两个解析器依赖都是可选的。插件无论如何都能安装、`using-john` skill 都能加载；只在调用解析器脚本时如果依赖缺失，脚本会大声报错并给出安装命令。

## 安装 + 升级

首次安装：

```sh
# Option A —— marketplace 流程（推荐）：
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install joharnessburg@joharnessburg

# 验证
claude plugin list
# 期望看到：joharnessburg@joharnessburg 出现在列表里，状态为 enabled
```

从早期版本升级（v0.1.x → v0.1.7）：

```sh
claude plugin marketplace update joharnessburg
claude plugin update joharnessburg@joharnessburg
# 重启 Claude Code 让新版本生效。
```

> 注意：`claude plugin install` 在插件已安装的情况下是 no-op。升级用 `claude plugin update <plugin>@<marketplace>`。第三方 marketplace 默认关闭自动更新；可以通过 `/plugin` UI → Marketplaces → joharnessburg → Enable auto-update 打开。

安装完成后，在新开的 Claude Code 会话里 `using-john` skill 应该会自动加载。这是 M0 的验收测试。

## 仓库内容

```
.claude-plugin/
  plugin.json         # Claude Code 插件 manifest
  marketplace.json    # 让这个 repo 同时充当 marketplace
hooks/hooks.json      # Hook 声明（安装时自动注册）
skills/               # John 的 meta-skill（layer-2；加载进 John 包装的 Claude Code 会话）
commands/             # Slash command
scripts/              # 小型 Python 工具包（ppx 包装、事件 reducer、scaffolder 等）
agents/               # Subagent 角色定义
templates/            # 模板撰写文档（模板本身单独安装）
README.md             # 本文件（英文版）
README_ZH.md          # 中文版
```

## 设计文档在哪里

实现计划、规格演进、设计对比、开发日志都在 **John workspace** 里——这是开发该插件的独立目录：

- `PLAN.md` —— 实时维护的实现计划（M0 → M7）
- `docs/initial_spec.md` —— 规格的演进 + 用户回复
- `docs/architecture_and_plan.md` —— PLAN.md 之前的草稿
- `docs/ralph_in_john_vs_original.md` —— John 的 ralph-loop 跟 snarktank/ralph 的差异
- `docs/john_vs_open_source_harnesses.md` —— 跟 7 个开源 harness 的新鲜对比
- `CLAUDE.md` —— workspace 记忆
- `DEVLOG.md` —— 仅追加的开发日志

这些不在插件的 repo 里（它们描述的是**怎么构建** John，不是插件本身）。如果你要贡献代码、需要看设计依据，找项目所有者拿 workspace 访问权限。

## 许可

目前仅限内部使用。没有计划对外分发。
