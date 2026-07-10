# John

> English: [`README.md`](README.md)

John 把非结构化源材料转化为可工作的知识密集型应用。它在一次可持续的运行中贯通知识工程与应用构建，协调大规模逐条目扇出，并把可审计的事件与检查点留在磁盘上。

你可以选择 **Claude Code 或 Codex**。两者都是推荐运行时，共用同一个 John 插件、skills、脚本、hooks、workspace 状态和模板格式。

## 安装与更新

### Claude Code

安装并验证：

```sh
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install john@joharnessburg
claude plugin list
```

然后在当前会话运行 `/reload-plugins`，或启动一个新的 Claude Code 会话。

更新并验证：

```sh
claude plugin marketplace update joharnessburg
claude plugin update john@joharnessburg
claude plugin list
```

更新后运行 `/reload-plugins`，或启动新会话。

### Codex

安装并验证：

```sh
codex plugin marketplace add kitchen-engineer42/joharnessburg
codex plugin add john@joharnessburg
codex plugin list
```

重启 Codex 或新建任务，让插件重新加载。打开 `/hooks`，检查 John 的 hook 定义，确认后再信任；安装插件不会自动信任它的 hooks。

更新并验证：

```sh
codex plugin marketplace upgrade joharnessburg
codex plugin add john@joharnessburg
codex plugin list
```

`codex plugin add` 是幂等操作，会从升级后的 marketplace 快照刷新已安装插件。如果 hook 定义发生变化，再次通过 `/hooks` 审阅，然后重启 Codex 或新建任务。

## 快速开始

用任一运行时打开项目，用可选的输入文件或目录初始化 John，确认生成的 `PLAN.md`，然后描述你想构建的应用。John 会推进知识与应用阶段，同时由 `.john/events/`、`.john/checkpoints/` 和 `.john/runs/` 保存持久证据。

| 操作 | Claude Code | Codex |
|---|---|---|
| 初始化 | `/john:init <input-path>` | “使用 `init-workspace` 从 `<input-path>` 初始化 John。” |
| 查看状态 | `/john:status` | “使用 `workspace-status` 显示 John workspace 状态。” |
| 运行报告 | `/john:report` | “使用 `codex-run-report` 生成 John run report。” |
| 耐久目标 | `/john:endurance <goal>` | “使用 `endurance-goal` 设置 `<goal>`。” |
| 归档 | `/john:archive [label]` | “使用 `archive-workspace` 归档这个 John workspace。” |

John 会同时初始化 `CLAUDE.md` 和 `AGENTS.md`；知识打包时，还会在 `.claude/skills/` 与 `.agents/skills/` 下生成字节一致的项目 skill 树。

## 扩展执行

- **Claude Code：** `vertical-workflows` 可为大规模、均匀的扇出编写 Claude dynamic workflows；不可用时，同样的工作通过内联 subagent 波次执行。
- **Codex：** `codex-vertical-workflows` 使用原生 subagent 波次和持久的 `.john/runs/` ledger，支持重试、对账、状态与取消。

两条路径产生相同的 events，通过相同的抽取审计，归约为相同的 checkpoints，并沿同一个 `PLAN.md` 继续推进。

## 模板

John 模板是一个带版本固定的 diff，用于让共享 harness 适配某一类应用。把模板安装为普通目录、应用一次，然后使用生成的合并插件；同一个 applied 输出服务两个 provider。

```sh
cp -R /path/to/template ~/.claude/plugins/joharnessburg-templates/<name>
~/.claude/plugins/joharnessburg-templates/<name>/apply.sh
```

对于 **Claude Code**，启动输出中给出的路径：

```sh
claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<name>
```

对于 **Codex**，在目标项目中激活同一个合并插件：

```sh
python3 ~/.claude/plugins/joharnessburg-applied/<name>/scripts/activate_codex_template.py \
  --merged-plugin ~/.claude/plugins/joharnessburg-applied/<name> \
  --project-root /path/to/project
```

按输出步骤操作：添加项目本地 marketplace、安装 applied listing、用 `codex plugin list` 验证、在该项目中禁用 vanilla `john@joharnessburg`、通过 `/hooks` 检查并信任 applied hooks，然后重启 Codex。激活只准备项目本地文件；它不会自动修改个人 marketplace 或全局插件状态。

不要在活跃会话仍在使用时删除 applied 目录。模板格式见[模板撰写指南](plugins/joharnessburg/templates/README.md)；双 provider 示例与引导式撰写流程见 [Hamster](https://github.com/kitchen-engineer42/hamster)。

## 前置条件与可选服务

- Python 3.10+，用于 John 的标准库工具。
- 可选的 `markitdown`，用于非 PDF 转换。
- 可选的 PPX 兼容服务，通过 `$JOHN_PPX_CLIENT_URL` 处理高保真 PDF。
- 可选的 OpenAI 兼容 workerLLM 服务，通过 `$JOHN_LLM_CLIENT_URL` 支持 produced app 的运行时模型调用。

没有这些可选服务，John 仍可安装和运行。它们是外部 URL 契约，不是软件包依赖。

## Hook 信任

[`hooks/hooks.json`](plugins/joharnessburg/hooks/hooks.json) 是 John 唯一的 hook 声明。Hooks 会以当前 coding session 的权限执行随附脚本。信任陌生 fork 前，请审阅该文件及其引用脚本。Codex 用户必须通过 `/hooks` 审阅并信任当前定义；仅安装或启用插件不等于信任 hooks。

## 仓库结构

```text
.claude-plugin/marketplace.json       Claude marketplace
.agents/plugins/marketplace.json      Codex marketplace
plugins/joharnessburg/
  .claude-plugin/plugin.json          Claude manifest
  .codex-plugin/plugin.json           Codex manifest
  hooks/                              共享 hook 声明
  skills/                             共享与 provider adapter skills
  commands/                           Claude slash commands
  agents/                             规范 Markdown agents
  codex/agents/                       生成的 Codex agents
  scripts/                            确定性工具
  templates/                          apply 脚本与撰写指南
CONTEXT.md                            规范词汇
```

## 致谢

John 由 [kitchen-engineer42](https://github.com/kitchen-engineer42) 维护，并得到 [@HalfMoon001](https://github.com/HalfMoon001)、[@oubeichen](https://github.com/oubeichen)、[@Ruilin-mmwa](https://github.com/Ruilin-mmwa) 与 [@AnselKocen](https://github.com/AnselKocen) 的贡献和实测证据支持。

## 许可

MIT。见 [`LICENSE`](LICENSE)。
