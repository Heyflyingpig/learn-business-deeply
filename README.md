# learn-business-deeply

`learn-business-deeply` 是一个面向实习和真实业务学习场景的 Codex Skill。它以本地代码、配置、日志、数据库结构、项目文档和任务历史为证据，帮助学习者从基础原理出发，逐步理解技术在业务中的真实流转方式，并进一步沉淀工程实践、已有优化逻辑和面试迁移能力。

这个 Skill 不把学习过程处理成零散知识点的罗列。它会先展示知识地图并诊断学习者已有的理解，再按照“基础原理 → 业务链路 → 原理与业务映射 → 已有工程设计 → 面试抽象 → 新场景迁移”的顺序展开。学习过程中会持续显示当前阶段，维护重点、疑点、项目证据和理解状态，并在用户明确要求总结时，将完整讨论重写为可供日后复习的中文 Markdown 知识回顾。

## 核心能力

- 使用阶段标识持续展示当前学习进度，长对话中也能判断正在学习哪条主线和哪个知识节点。
- 先建立技术的基础模型，再进入真实业务链路，避免用项目类名和代码细节代替原理解释。
- 基于本地代码、配置、日志、数据库结构和项目文档区分项目事实、分析推断、已有设计与建议方案。
- 使用 Mermaid 描述复杂调用链、数据流、状态变化和组件关系，并用连贯的中文段落解释图中的因果关系。
- 在最终学习文档所在目录维护学习面板，持续记录重点、疑点、证据、误区、关键图和理解状态。
- 支持多轮追问和多条知识主线，并根据知识关系对主线进行新增、合并、拆分或重组。
- 通过预测、诊断、反事实、方案比较和迁移题区分“看过一遍”和“真正理解”。
- 在收到“总结为 Markdown”等明确请求后，读取可获得的完整任务谱系、学习面板和相关代码证据，去重后生成详细知识回顾。

## 目录结构

```text
learn-business-deeply/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── knowledge-review.md
│   ├── learning-notebook.md
│   └── mermaid-guidelines.md
└── scripts/
    └── extract_thread_lineage.py
```

`SKILL.md` 是 Codex 读取的核心执行指令；`agents/openai.yaml` 提供 Skill 的显示名称、默认提示和调用策略；`references/` 保存学习面板、知识回顾和 Mermaid 图的详细规范；`scripts/extract_thread_lineage.py` 用于在生成知识回顾时辅助恢复本地任务及其 fork 谱系。

## 部署方式

这个项目不需要启动服务器或执行构建流程。所谓“部署”，本质上是将完整仓库放入 Codex 的用户级 Skills 目录，使 Codex 能够发现其中的 `SKILL.md`。

### 方式一：使用 Git 安装（推荐）

在 macOS 终端中执行：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/Heyflyingpig/learn-business-deeply.git ~/.codex/skills/learn-business-deeply
```

安装完成后，确认入口文件存在：

```bash
test -f ~/.codex/skills/learn-business-deeply/SKILL.md && echo "Skill installed"
```

随后重新打开 Codex，或者新建一个任务，使 Skill 列表重新加载。

### 方式二：手动安装

从 GitHub 下载仓库压缩包并解压，然后将整个 `learn-business-deeply` 文件夹复制到：

```text
~/.codex/skills/learn-business-deeply
```

复制后必须保持目录结构完整，尤其不能只复制 `SKILL.md`。学习面板规范、知识回顾规范、Mermaid 规则和任务谱系提取脚本都属于 Skill 工作流程的一部分。

### 更新已安装版本

如果使用 Git 安装，可以执行下面的命令获取远端最新版本：

```bash
git -C ~/.codex/skills/learn-business-deeply pull --ff-only
```

更新完成后重新打开 Codex，或者新建一个任务，以确保新的 Skill 指令被加载。

## 使用方式

这个 Skill 默认不进行隐式触发，需要在请求中明确指定 `$learn-business-deeply`。例如：

```text
$learn-business-deeply 我不了解 Redis。请先帮我建立基础模型，再结合当前项目解释 Redis 在业务链路中的作用。
```

也可以直接指定一个本地业务问题：

```text
$learn-business-deeply 请结合当前仓库，帮助我理解这条消息发送链路。先诊断我已有的知识，再展示整体知识地图。
```

学习过程中可以持续追问，也可以告诉 Codex“这是重点”或指出自己的疑点。Skill 会把这些信息同步到与最终笔记同一目录的学习面板。当一个主题讨论充分后，可以明确提出：

```text
请把当前学习任务总结为 Markdown，完整读取有效对话、学习面板和相关代码证据，去重后按知识主线详细重写。
```

这里的“总结”不是简短摘要，而是一份能够在遗忘部分内容后帮助快速恢复完整知识模型的详细回顾文档。

## 使用边界

Skill 会优先读取当前项目中与问题相关的代码、配置、日志、数据库结构和文档，但不会凭空补写业务事实。生成完整知识回顾时，它可能读取本机 Codex 保存的相关任务记录，以恢复压缩前内容和 fork 关系；原始任务记录应保持只读。对于公司内部代码、日志和业务资料，使用者仍需遵守所在组织的数据安全与保密要求，并在对外分享学习文档前检查其中是否包含敏感信息。

## 仓库说明

本 README 面向安装和使用该项目的人；真正控制 Codex 学习流程的是 [`SKILL.md`](SKILL.md)。修改工作流时应更新 `SKILL.md` 及其引用文件，修改安装或使用说明时再更新 README，避免把面向人的仓库介绍与面向 Codex 的执行指令混为一体。
