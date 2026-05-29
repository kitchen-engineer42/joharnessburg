# joharnessburg

**John** —— 一个 Claude Code 插件，通过 skills、hooks、slash commands 和一套小工具包装 Claude Code，让它能在一个长时间运行的会话中完成从非结构化输入（书籍、法规、混合文档）到知识工程再到应用构建的全流程。

插件 slug：`joharnessburg`。读作 "jo-harness-burg"（harness 在中间），或者按城市谐音读 "jo-hannesburg" 也行。

> English README: [`README.md`](README.md)

## 安装

```sh
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install john@joharnessburg

# 验证
claude plugin list
# 期望看到：john@joharnessburg 出现在列表里，状态为 enabled
```

安装完成后，新开一个 Claude Code 会话时 `using-john` skill 会自动加载——这是 John 的入口定向 skill，Claude 读到它就开始进入 John 的工作模式。

## 快速开始

在项目目录中打开一个新的 Claude Code 会话。`using-john` skill 应该会在会话开始时触发；如果没有，你也可以直接问 Claude "John 是什么？我在这个目录里怎么用？"——这种话术也能触发它。

新 John 项目的自然流程：

1. **（可选）先应用模板** 来特化 app 家族。看下面的 [模板](#模板) 章节——把模板装到 `~/.claude/plugins/joharnessburg-templates/<name>/`，运行它的 `apply.sh`，然后用 `--plugin-dir` 启动 Claude。如果用 vanilla John，跳过这步。
2. **创建 workspace** —— 运行 `/john:init`（或者直接告诉 Claude "在这个目录里设置 John"）。这会在你的项目里创建 `PLAN.md`、`CLAUDE.md` 和一个 `.john/` 工作目录。
3. **把输入材料放进** `.john/input/`（PDF、法规、样本文档——任何 produced app 需要的素材）。
4. **告诉 Claude 你想构建什么 app**。Claude 会按 `PLAN.md` 里声明的 phase，通过 ralph_loop（迭代驱动器）逐步推进，每个 phase 派发并行的 subagent，最终产出一个可工作的 app。

安装后还有其它 slash command 可用：

- `/john:status` —— 当前 phase + 进度
- `/john:archive` —— 归档已完成的 workspace
- `/endurance` —— 如果会话长时间空闲，重新进入耐久模式

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

等技术团队上自己的生产服务器（on-prem 或别的 provider），把这两个环境变量换掉就行——John 内部不需要任何改动。

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
    templates/                  # 通用 apply.sh + 撰写指南（templates/README.md）；以及已收录的模板
README.md                       # 英文版
README_ZH.md                    # 本文件
LICENSE                         # AGPL-3.0-or-later
```

## 许可

版权所有 (C) 2026 kitchen-engineer42。

John（joharnessburg）是自由软件：你可以在 **GNU Affero 通用公共许可证第 3 版或（由你选择）任何更高版本**（由自由软件基金会发布）的条款下重新分发和/或修改本软件。完整许可证文本见 [`LICENSE`](LICENSE)。

本程序在希望有用的前提下分发，但**不提供任何担保**；甚至不暗含适销性或针对特定用途的适用性担保。

AGPL 的网络使用条款（§13）适用：如果你以网络服务的形式运行 John 的修改版本，你必须向其用户提供修改后的源代码。这是显式的选择——John 面向常常以内部服务形式运行的知识工程流水线设计，我们希望衍生作品保持开源。

如果 AGPL 不适合你的使用场景，请联系版权持有人商谈商业许可。
