# joharnessburg

**John** 是插件名（slash commands 为 `/john:init`、`/john:status` 等）；**joharnessburg** 是它的分发 marketplace / 仓库名——读作 "jo-harness-burg"（harness 在中间），或者按城市谐音读 "jo-hannesburg" 也行。所以安装命令是 `claude plugin install john@joharnessburg`。

John 通过 skills、hooks、slash commands 和一套小工具包装 Claude Code，让它能在一个长时间运行的会话中完成从非结构化输入（书籍、法规、混合文档）经 **knowledge phases（知识工程）** 到 **app phases（应用构建）** 的全流程，最终产出一个 **knowledge-dense app**：一个用固定机制（mechanism）运行大量均匀知识条目（entries）的应用——条目来自你的语料。产出的应用**默认独立运行**（本地启动、`.env` 配置、不假设任何外部平台）；模板可以叠加平台集成。

项目的规范词汇表在 [`CONTEXT.md`](CONTEXT.md)；若干设计决策记录在 [`docs/adr/`](docs/adr/)。

> English README: [`README.md`](README.md)

## 安装

### Claude Code

```sh
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install john@joharnessburg

# 验证
claude plugin list
# 期望看到：john@joharnessburg 出现在列表里，状态为 enabled
```

### Codex

本仓库同时提供 Codex 插件 manifest 和本地 marketplace：

- 插件 manifest：`plugins/joharnessburg/.codex-plugin/plugin.json`
- Codex marketplace：`.agents/plugins/marketplace.json`

本地开发安装：

```sh
codex plugin marketplace add /path/to/joharnessburg
```

然后在 Codex App 的插件界面启用 `john@joharnessburg`。Codex 中没有 Claude slash command 运行时；对应入口以 skill 形式暴露：

- `John: Init Workspace` —— `/john:init`
- `John: Workspace Status` —— `/john:status`
- `John: Endurance Goal` —— `/john:endurance`
- `John: Archive Workspace` —— `/john:archive`

安装完成后，新开一个 Claude Code 会话时 `using-john` skill 会自动加载——这是 John 的入口定向 skill，Claude 读到它就开始进入 John 的工作模式。在 Codex 中，使用 Codex App 插件界面里的 John skills；底层仍使用同一套 workspace 文件和脚本，只是 slash command 以 skill 形式暴露。

## 快速开始

在项目目录中打开一个新的 Claude Code 会话。`using-john` skill 应该会在会话开始时触发；如果没有，你也可以直接问 Claude "John 是什么？我在这个目录里怎么用？"——这种话术也能触发它。

新 John 项目的自然流程：

1. **（可选）先应用模板** 来特化 app 家族。看下面的 [模板](#模板) 章节——把模板装到 `~/.claude/plugins/joharnessburg-templates/<name>/`，运行它的 `apply.sh`，然后用 `--plugin-dir` 启动 Claude。如果用 vanilla John，跳过这步。
2. **创建 workspace** —— Claude Code 中运行 `/john:init`（或者直接告诉 Claude "在这个目录里设置 John"）；Codex 中使用 `John: Init Workspace`。这会在你的项目里创建 `PLAN.md`、`CLAUDE.md`、`AGENTS.md` 和一个 `.john/` 工作目录，其中 `.john/brief/` 与 `.john/contracts/` 用于 app-first intent flow。
3. **把输入材料放进** `.john/input/`（PDF、法规、样本文档——任何 produced app 需要的素材）。
4. **让 John 先推断普通用户看到的 app 形态**。John 会先 parse/probe 并抽样 survey 输入；当方向清楚时直接选择最佳默认方案，只有高影响且无法可靠推断的产品取舍才会向用户发起一次小问题批次。用户可以自然语言回答；John 会把中间状态写成固定 JSON，方便工具识别。
5. **从 contract 反推构建**。schema pilot 前，John 会写出 `.john/brief/user_intent.json`、`.john/contracts/app_blueprint.json` 和 `.john/contracts/extraction_plan.json`。后续抽取从公开 app blueprint 反推，最终 UI guardrails 会检查 raw JSON、schema key、skill 名、chunk ID、文件路径、无意义英文变量名等内部痕迹不会泄漏到用户界面。

Codex 兼容说明：

- Codex 插件用 skills 暴露 slash command 等价入口：`John: Init Workspace`、`John: Workspace Status`、`John: Endurance Goal`、`John: Archive Workspace`。
- 如果是在本源码检出目录中使用，而不是安装后的 Codex 插件，使用 `.agents/skills/` 下的项目桥接技能；它们调用的是同一批脚本，只是路径指向源码检出。
- `scripts/app_first_contracts.py` 等 helper 脚本只依赖 Python 标准库。Codex 插件安装场景从已加载的 John plugin root 解析；源码检出场景使用 `plugins/joharnessburg/scripts/<script>.py`。

构建过程中，会话还会*从这次运行中学习*（`skill-evolution` skill，v0.3.x 起）：在 phase 边界把经验教训沉淀到 `.john/lessons/`；skill 调用与 phase 关卡判定会被记录下来，供确定性的 process scorecard（`scripts/process_scorecard.py`）读取；当模板带有 scorer 时，produced app 的 workerLLM skill 还能在构建期间通过留出集门控的编辑循环进行训练。

安装后还有其它 slash command 可用：

- `/john:status` —— 当前 phase + 进度
- `/john:report` —— 生成 run report（scorecard + 结果 + 脱敏后的经验教训；模板维护者做模板演化要汇总的证据——分享永远由人手动进行）
- `/john:archive` —— 归档已完成的 workspace
- `/john:endurance` —— 设置/清除长跑目标（注入 system prompt，跨上下文压缩存活）

## 用 dynamic workflows 运行 John

John 的纵轴——把成百上千的单条目 subagent 扇出（抽取每个 chunk、对每个章节套用每条规则、渲染每张幻灯片）——正好对应 Claude Code 的 **dynamic workflows**：Claude 写一个脚本，在它的上下文之外跑这个扇出，让 worker 之间相互对抗式交叉校验，并把每条结果写进 John 的 event log。`vertical-workflows` skill 教会 Claude 这种 John 形态的扇出；你负责把会话配置好，让 workflow 在**该用的 phase** 上触发，而不是到处乱触发。

**前置条件：** 支持 dynamic workflows 的 Claude Code（research preview；付费计划上的较新版本），并已启用该功能。

**推荐的会话配置**（这些是你的操作——John 会读取它们，但无法替你设置）：

1. **打开 ultracode。** 会话开始时运行 `/effort ultracode`。这才是让 Claude 自主**编写** workflow 的开关；之后 John 的 skills 会把它引导到重型扇出 phase，并把小规模/强耦合/需交互的工作留在内联处理。ultracode 是**单会话**的——新开会话会重置，所以每次都要重设（需要支持 `xhigh` effort 的模型）。
2. **预置你的权限白名单。** workflow 的 subagent 继承你的工具白名单；不在白名单里的 Bash/web/MCP 调用仍会在运行中弹出确认，会卡住无人值守的流水线。长跑前，把 John 的 agent 会用到的工具（Read/Write/Grep/Glob/Bash + 你的 workerLLM 和 ppx 客户端调用）加进白名单。

> **关于关键词触发——无需关闭任何东西。** Claude Code 的单条 prompt workflow 触发词现在是 **`ultracode`**（2026 年中的一次更新把它从 `workflow` 改了过来，并让 Claude 自行判断，偶然提到不再会误触发一次运行）。John 的 skills 和你的消息里频繁出现 "workflow"，这不再会启动运行——所以会话层面只需 `/effort ultracode` 即可；只有当你想要一次性运行时，才在 prompt 里打 `ultracode`。

**降级回退：** 以上都不是必需的。如果 workflows 不可用（较旧的 Claude Code、功能未开、不在 ultracode），John 会用内联 subagent 跑**同样的**扇出——同样的 events、同样的 reducer、同样的 `PLAN.md`、同样的产出。执行层以下什么都不变；你只是拿不到脱离上下文的规模和内建的交叉校验。John 会在第一个扇出 phase 之前检查可用性；如果会话没配置好，它会把上面的配置步骤告诉你。

**耐久模式注意：** 如果你设置了耐久目标（`/john:endurance <goal>`），John 会**假设你已经完成了上面的配置**，长跑过程中不会停下来再次确认——先配置会话，再启动长跑。

## 升级

```sh
claude plugin marketplace update joharnessburg
claude plugin update john@joharnessburg
# 重启 Claude Code 让新版本生效。
```

> 注意：`claude plugin install` 在插件已安装的情况下是 no-op。升级用 `claude plugin update <plugin>@<marketplace>`。第三方 marketplace 默认关闭自动更新；可以通过 `/plugin` UI → Marketplaces → joharnessburg → Enable auto-update 打开。

## 依赖

- **Python 3.10+** —— 插件的工具脚本只用标准库；系统自带的 Python 就够用。
- 非 PDF 文档解析（`markitdown_parse.py`）：`pip install markitdown`。
- PDF 解析：插件外部的 `local_clients/ppx/` FastAPI 服务器，封装 `memect-ppx`。详见下面的 [本地客户端](#本地客户端)。
- 运行时的 workerLLM 调用：插件外部的 `local_clients/llm/` FastAPI 服务器。也在 [本地客户端](#本地客户端) 里。

两个解析器依赖都是可选的。插件无论如何都能安装，`using-john` skill 也能加载；只在调用解析器脚本时，如果依赖缺失，脚本会大声报错并给出安装命令。

## 模板

模板**让 John 针对一类 app 进行特化**。一个模板是**对原始 John 的 diff**，purpose-build 整个 harness 来服务某一类流水线（覆盖某些 skills、添加新的、附带一份初始 `PLAN.md` 骨架）。

三步流程：

```sh
# 1. 安装模板（拷贝或软链到 user-scope 的模板目录）
cp -R /path/to/your-template ~/.claude/plugins/joharnessburg-templates/your-template

# 2. 应用模板（产出合并后的插件到 ~/.claude/plugins/joharnessburg-applied/<name>/）
~/.claude/plugins/joharnessburg-templates/your-template/apply.sh

# 3. 用合并后的插件启动 Claude
cd /path/to/your-project
claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/your-template
```

合并后的插件**就是**那个会话的 John —— 模板的 skill 跟核心 skill 同等加载，没有"模板层"这种二等概念。哪个模板被加载是会话启动时固定的；要切换，退出当前会话用不同的 `--plugin-dir` 重新启动。多个 applied 模板可以共存（并行的 Claude 会话可以用不同模板）。

重置：`rm -rf ~/.claude/plugins/joharnessburg-applied/<name>/`（或者全清 `~/.claude/plugins/joharnessburg-applied/`）。下次不带 `--plugin-dir` 启动就是 vanilla John。

**去哪儿找模板**：本插件不内置示例——这能让 John 的运行时聚焦于你加载的那一个模板（或者完全不用模板）。功能演示性质的参考示例（展示 diff 格式）放在配套工具 **Hamster**（[github.com/kitchen-engineer42/hamster](https://github.com/kitchen-engineer42/hamster)）的 `examples/` 目录下。生产模板由你的团队单独交付。

要自己写模板，看 [`plugins/joharnessburg/templates/README.md`](plugins/joharnessburg/templates/README.md)——里面写了 diff-script 架构、目录结构、`apply.sh` 机制。如果你想要一种有引导的、Claude 驱动的模板写作体验，用 Hamster——它内置了 skills 和方法论，能带 Claude Code 从原始输入开始一步步构建模板。

## 本地客户端

对于 LLM 调用 + PDF 解析，John 通过**外部 FastAPI 服务器**通信——这些服务器跟插件并行运行。它们在**插件外部**（workspace 级别），这样换 provider 不影响 John 本身。

插件的 `parsing` + `workerllm-runtime` skill 教 Claude 通过环境变量配置的 URL 调用它们：

- `$JOHN_LLM_CLIENT_URL`（默认 `http://localhost:8500`）—— workerLLM 客户端（当前封装 SiliconFlow + DeepSeek）。
- `$JOHN_PPX_CLIENT_URL`（默认 `http://localhost:8501`）—— PDF 解析客户端（封装 `memect-ppx`，即 `ppx` 解析引擎，仓库在 [github.com/kitchen-engineer42/ppx](https://github.com/kitchen-engineer42/ppx)）。

想换成你自己的生产服务器（on-prem 或别的 provider）？只要 HTTP 契约一致，把这两个环境变量换掉就行——John 内部不需要任何改动。

### 一次性安装（每台机器一次）

前提：装了 [`uv`](https://docs.astral.sh/uv/)。你需要拿到 John workspace 包（里面包含 `local_clients/` 和 `setup_john.sh`）——如果还没有，联系项目所有者。

```sh
# 1. 把 ppx 引擎 clone 到 workspace 外面某个位置
git clone https://github.com/kitchen-engineer42/ppx.git ~/code/ppx

# 2. 运行 workspace 的安装脚本——创建 venv 并安装两个客户端
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

停止：

```sh
cd /path/to/john-workspace
./stop_john.sh
```

### 端到端验证

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
- `plugins/joharnessburg/skills/workerllm-runtime/SKILL.md` —— 插件中的 skill 如何指导 Claude 调用这些客户端

## 仓库内容

```
.claude-plugin/
  marketplace.json              # Marketplace 目录（这个 repo 同时充当 marketplace）
plugins/
  joharnessburg/                # 插件本体
    .claude-plugin/
      plugin.json               # Claude Code 插件 manifest
    hooks/hooks.json            # Hook 声明（安装时自动注册）
    skills/                     # John 的 meta-skill（加载进 John 包装的 Claude Code 会话）
    commands/                   # Slash command
    scripts/                    # 小型 Python 工具包（ppx 包装、事件 reducer、apply_template 等）
    agents/                     # Subagent 角色定义
    templates/                  # 通用 apply.sh + 撰写指南（templates/README.md）
CONTEXT.md                      # 项目词汇表——规范用语
docs/adr/                       # 架构决策记录（简短）
README.md                       # 英文版
README_ZH.md                    # 本文件
LICENSE                         # MIT
```

## 致谢

- [@HalfMoon001](https://github.com/HalfMoon001) —— 对 John 进行了大量端到端实测，并完成了 `job-runtime` skill 背后的分析（[#2](https://github.com/kitchen-engineer42/joharnessburg/issues/2)）：产出应用的长耗时 I/O 任务模式（任务注册表、槽位租约、排队/生成双预算、可恢复进度）正是基于她的测试与 issue 梳理而规约成形。

## 许可

John（joharnessburg）以 **MIT 许可证**发布——见 [`LICENSE`](LICENSE)。自由使用、fork、在其上构建。

vanilla John 及其配套工具 Hamster 均为 MIT。在 John 之上构建的领域特化变体（例如 KC Agent CLI）可能以单独的商业条款提供。
