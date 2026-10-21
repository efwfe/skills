# scratch

[中文](#中文) | [English](#english)

---

## 中文

一个 [Claude Code](https://claude.com/claude-code) 插件,围绕"真正学懂东西"设计:把文章和 GitHub 项目拆开再从零重建,把可迁移的思想沉淀成个人 dot 库,再把学过的东西画成一张关系图。

### 命令

| 命令 | 作用 | 输入 | 输出 |
|---|---|---|---|
| `/scratch:learn` | **总入口**:判断该用哪个 skill,也能串起完整学习路线;不带参数时报告 dot 库现状 | 任意:链接、正文、仓库、主题 | 调度到下面四个 |
| `/scratch:blog` | 把一篇文章、论文、演讲或设计文档"从零重新长出来":还原问题、推理过程、心智模型,并重画原文图表;可选互动模式(先猜再看、检验题先答) | 链接、PDF、粘贴的正文或文字稿 | 排版好的 HTML 页面 |
| `/scratch:repo` | 从零重建一个仓库。**练习模式**:你写代码,Claude 备好每个组件的题面、骨架、测试和原仓库输出,给阶梯提示、做评审;**出书模式**:Claude 写成面向 Python 初学者的课程(Raschka《Build X From Scratch》方法) | 仓库地址 | `lab/` 练习目录 + 进度;或课程章节、配图 |
| `/scratch:dots` | 提炼项目里"不变的、可迁移的思想"(dot),沉淀进个人 dot 库并发现连接;**对比模式**把解决同一问题的两个项目放一起,提炼共同不变量和张力 | 一个或两个仓库;或"盘点 dot 库" | dot 库的更新 |
| `/scratch:graph` | 把 dot 库画成可交互的关系图:梳理报告、时间轴、先学路线、可能相关的建议,可导出 Mermaid / Obsidian Canvas | dot 库 | `graph.html` + 梳理报告 |

```text
/scratch:learn https://example.com/some-post          # 文章 → scratch:blog
/scratch:learn https://arxiv.org/abs/xxxx.xxxxx       # 论文 → scratch:blog
/scratch:learn https://github.com/owner/repo          # 仓库 → 问你要提炼思想、动手重建还是写成课程
/scratch:repo 我想自己写一遍 https://github.com/owner/repo  # 练习模式
/scratch:dots 对比 owner/a 和 owner/b                  # 对比模式
/scratch:learn 完整学一遍 https://github.com/owner/repo # dots → repo → graph,每步停下来等你
/scratch:learn                                         # 看 dot 库现状和下一步
/scratch:graph                                         # 画关系图,一起梳理
```

各 skill 也能用自然语言直接触发("帮我吃透这篇文章""盘点一下我的 dot 库")。

### 学习路线

```text
scratch:blog   读懂一篇文章 ──┐ 学习记录 projects/blog-*.md
scratch:repo   从零重建仓库 ──┤ 学习记录 projects/course-*.md
scratch:dots   提炼项目思想 ──┴──> dot 库 ~/dot-library ──> scratch:graph 关系图与梳理
```

三个学习 skill 共用一套"四层透镜"(`skills/*/references/learning-lens.md`,三份内容一致):

| 层 | 回答 | 合格的样子 |
|---|---|---|
| 思想 | 它押注了什么? | 剥掉项目名也说得清,说得出"为了 A 放弃了 B" |
| 心智模型 | 脑子里该有什么可运转的模型? | 能预测新情形,知道在哪失效 |
| 架构 | 怎么切成零件、为什么这样切? | 3–7 个零件 + 每条边界一张设计决策卡 |
| 实现 | 关键代码在哪、守护什么? | 指得到 `path:line`,说得出删掉会坏什么 |

"融会贯通"= 四层之间能**上下打通**(从思想追到代码,从代码收回思想),并和已知的东西**横向连上**(同源异形 / 张力 / 依赖 / 传承)。`scratch:graph` 把横向连接画出来,让缺口一眼可见。

### 关系图

`/scratch:graph` 读 dot 库里的 Markdown 和 `[[链接]]`,生成单文件 `graph.html`(离线可用、明暗主题、手机可看):

- 节点:dot、候选、归档、项目、学习记录(文章、论文、演讲、设计文档、课程、对比),以及"悬挂链接"(被引用但没有文件);
- 边:例证、同源异形、张力、依赖、传承,类型从链接所在的小节推断,按 `scratch:dots` 的模板写就对;
- 交互:点击看内容与连接,双击只看两层邻域,搜索,按问题高亮(可升级、半个、没落到代码、孤立、悬挂链接),图例可开关;
- 时间轴:拖动滑块回放这张网是怎么长出来的;
- 点开一个 dot 能看到"先学"路线(沿依赖边)和"可能相关"的建议(一句话相似或共享例证,只是线索,要你确认);
- 报告(`--report`):枢纽、孤岛、张力和上面每类问题,`/scratch:graph` 会挑最值得做的几件和你一起过;
- 导出:`--mermaid` 贴进 Markdown,`--canvas` 在 Obsidian 里打开。

也可以脱离 Claude 直接运行:

```bash
uv run python skills/graph/scripts/learning_graph.py ~/dot-library --report   # --extra ~/notes 加入其他笔记目录
uv run python skills/graph/scripts/learning_graph.py ~/dot-library --no-html --path <dot> --suggest
uv run python skills/graph/scripts/learning_graph.py ~/dot-library --canvas ~/dot-library/graph.canvas
```

### 安装

推荐作为插件安装(Claude Code 2.1.275 及以上可一步完成):

```text
/plugin install scratch --marketplace efwfe/skills
```

或分两步:

```text
/plugin marketplace add efwfe/skills
/plugin install scratch@efwfe-skills
```

更新:在 `/plugin` 的 Marketplaces 页选 efwfe-skills → Update marketplace(或在那里打开自动更新)。插件不固定版本号,每次更新都取仓库最新提交。

<details><summary>不用插件,手动安装</summary>

```bash
git clone https://github.com/efwfe/skills.git ~/Developer/skills
mkdir -p ~/.claude/skills
for s in learn blog repo dots graph; do
  ln -s ~/Developer/skills/skills/$s ~/.claude/skills/scratch-$s
done
```

手动安装时命令没有 `scratch:` 前缀,`${CLAUDE_PLUGIN_ROOT}` 也不会被替换,Claude 会按 SKILL.md 的路径说明改用 skill 所在目录。推荐用插件方式。
</details>

### 依赖

- [`uv`](https://docs.astral.sh/uv/) 与 Python 3.10+:所有脚本通过 `uv run` 运行,除 `scratch:blog` 出页需要的 `markdown` 包外零第三方依赖
- `git` 与 bash:`scratch:dots` 的时间线脚本
- 可选 `gh`:`scratch:dots` 读 Issue/PR 讨论

### dot 库

默认 `~/dot-library/`,可用环境变量 `DOT_LIBRARY` 改。第一次运行 `/scratch:dots` 时会先问你再创建,并 `git init`;之后每次分析都会提交一次,库的历史就是你功底的演化史。

### 目录结构

```text
.claude-plugin/        # plugin.json 与 marketplace.json
skills/
├── learn/             # 调度器
├── blog/  repo/  dots/  graph/
│   ├── SKILL.md       # 入口:触发条件与工作流
│   ├── references/    # 按需读取的方法论
│   ├── scripts/       # 辅助脚本(含 tests/)
│   └── templates/     # 输出模板
scripts/check_sync.py  # 检查共用文件(learning-lens.md)是否同步
```

### 开发

- 改触发条件就改各 `SKILL.md` 顶部 frontmatter 的 `description`。
- 本地试插件:`claude --plugin-dir .`;校验:`claude plugin validate .`。
- 测试:
  ```bash
  (cd skills/repo/scripts && uv run --with pytest -m pytest tests)
  (cd skills/graph/scripts && uv run --with pytest -m pytest tests)
  python3 scripts/check_sync.py
  ```

---

## English

A [Claude Code](https://claude.com/claude-code) plugin built around *actually understanding things*: take a blog post or a GitHub project apart and rebuild it from scratch, distill the transferable ideas into a personal "dot" library, and see how everything you've learned connects.

> The skill prompts are written mostly in Chinese; the skills respond in the language you use.

### Commands

| Command | What it does | Input | Output |
|---|---|---|---|
| `/scratch:learn` | **Entry point**: picks the right skill, can chain a full learning route; with no argument, reports on your dot library | Anything: URL, text, repo, topic | Dispatches to the four below |
| `/scratch:blog` | Regrows an article, paper, talk or design doc from scratch: the problem, the reasoning chain, the mental model, figures redrawn; optional interactive mode (guess first, answer the check questions first) | URL, PDF, pasted text or transcript | A typeset HTML page |
| `/scratch:repo` | Rebuild a repo from scratch. **Practice mode**: you write the code while Claude prepares per-component labs (brief, stubs, tests, oracle outputs), gives tiered hints and reviews. **Book mode**: Claude writes a course for readers who only know basic Python | Repo URL | `lab/` + progress, or chapters and figures |
| `/scratch:dots` | Extracts invariant, transferable ideas ("dots") into your dot library; **compare mode** puts two projects that solve the same problem side by side to find shared invariants and tensions | One or two repos, or "review my dot library" | Updates to the library |
| `/scratch:graph` | Interactive graph of the dot library with a tidy-up report, timeline, prerequisite paths, suggested links, and Mermaid / Obsidian Canvas export | Dot library | `graph.html` + report |

```text
/scratch:learn https://example.com/some-post            # article -> scratch:blog
/scratch:learn https://github.com/owner/repo            # repo -> asks: distill, practice rebuild, or write a course
/scratch:repo practice https://github.com/owner/repo    # practice mode: you write the code
/scratch:dots compare owner/a and owner/b               # compare mode
/scratch:learn full route https://github.com/owner/repo # dots -> repo -> graph, pausing between steps
/scratch:learn                                           # library status and next step
/scratch:graph                                           # draw the graph and tidy up together
```

### Learning route

```text
scratch:blog   understand an article ──┐ record projects/blog-*.md
scratch:repo   rebuild a repo          ──┤ record projects/course-*.md
scratch:dots   distill a project       ──┴──> dot library ~/dot-library ──> scratch:graph
```

The three learning skills share a four-layer lens (`skills/*/references/learning-lens.md`, three identical copies): **idea** (what the author bet on), **mental model** (a model that predicts), **architecture** (parts, boundaries, design-decision cards), **implementation** (`path:line` and what it protects). Real understanding means moving vertically between the layers and connecting horizontally to what you already know (same mechanism / tension / dependency / lineage). `scratch:graph` makes those horizontal connections visible.

### The graph

`/scratch:graph` reads the Markdown and `[[wikilinks]]` in your dot library and writes a single-file `graph.html` (offline, light/dark, phone-friendly). Nodes are dots, candidates, archived dots, projects, learning records (articles, papers, talks, design docs, courses, comparisons), and dangling links. Edge types (example, same mechanism, tension, dependency, lineage) are inferred from the section each link sits in. Click a node for its content, neighbors, prerequisite path and suggested links (hints only; you confirm), double-click for its 2-hop neighborhood, drag the timeline to replay how the library grew, search, and highlight problems (promotable candidates, half dots, no code anchor, orphans, dangling links). Export with `--mermaid` or `--canvas` (Obsidian). Run it standalone with:

```bash
uv run python skills/graph/scripts/learning_graph.py ~/dot-library --report
```

### Installation

```text
/plugin install scratch --marketplace efwfe/skills
```

or in two steps: `/plugin marketplace add efwfe/skills`, then `/plugin install scratch@efwfe-skills`. Update from the Marketplaces tab in `/plugin` (efwfe-skills → Update marketplace, or turn on auto-update there); the plugin is unversioned, so updates track the latest commit. To install without the plugin system, symlink each folder under `skills/` into `~/.claude/skills/` (commands then lose the `scratch:` prefix; the plugin install is recommended).

### Requirements

- [`uv`](https://docs.astral.sh/uv/) and Python 3.10+ (scripts have no third-party dependencies except `markdown` for `scratch:blog`)
- `git` and bash for `scratch:dots`; optionally `gh` for reading issues and PRs

### Development

- Trigger phrases live in each `SKILL.md` frontmatter `description`.
- Try locally with `claude --plugin-dir .`; validate with `claude plugin validate .`.
- Tests: `uv run --with pytest -m pytest tests` inside `skills/repo/scripts` and `skills/graph/scripts`; `python3 scripts/check_sync.py` checks the shared files.
