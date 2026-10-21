# skills

[中文](#中文) | [English](#english)

---

## 中文

一组用于 [Claude Code](https://claude.com/claude-code) 的个人 Skills,围绕"真正学懂东西"设计:把博客、GitHub 项目拆开再从零重建,并把可迁移的思想沉淀下来。

### 包含的 Skills

| Skill | 作用 | 输入 | 输出 |
|---|---|---|---|
| [`blog-from-scratch`](blog-from-scratch/) | 把一篇博客/文章"从零重新长出来":还原问题、推理过程、心智模型,并重画原文图表 | 博客链接或粘贴的正文 | 排版好的 HTML 页面 |
| [`connect-dots`](connect-dots/) | 分析 GitHub 项目,提炼"不变的、可迁移的思想"(dot),沉淀进个人 dot 库并发现 dot 之间的连接 | GitHub 链接或本地仓库路径 | dot 库的更新 |
| [`repo-from-scratch`](repo-from-scratch/) | 把任意仓库变成面向 Python 初学者的"从零构建"教程课程(Raschka《Build X From Scratch》方法) | 仓库地址 | 课程章节、配图、可验证的代码 |

### 安装

Claude Code 会从 `~/.claude/skills/<skill 名>/` 读取 Skill(目录下需有 `SKILL.md`)。

```bash
git clone https://github.com/efwfe/skills.git ~/Developer/skills

# 用符号链接安装,之后 git pull 即可更新
mkdir -p ~/.claude/skills
for s in blog-from-scratch connect-dots repo-from-scratch; do
  ln -s ~/Developer/skills/$s ~/.claude/skills/$s
done
```

只用其中一个,就只链接对应目录。仅在某个项目中使用时,放到该项目的 `.claude/skills/` 即可。

### 依赖

- [`uv`](https://docs.astral.sh/uv/):脚本通过 `uv run` 运行(`blog-from-scratch` 需要 `markdown` 包,`uv run --with markdown` 会自动装)
- Python 3.10+
- `connect-dots` 的时间线脚本需要 `git` 与 bash
- `repo-from-scratch` 的绘图与校验脚本见其 `SKILL.md`

### 使用方式

在 Claude Code 中直接用自然语言触发,或用 `/skill名` 显式调用。

**blog-from-scratch**
```text
帮我吃透这篇文章 https://example.com/some-blog-post
/blog-from-scratch 这篇读不懂,讲讲背后的 intuition:<粘贴正文>
```

**connect-dots**
```text
帮我学习这个项目,提炼 dot https://github.com/owner/repo
/connect-dots 快速 ~/code/some-repo        # 说"快速"走快速模式,默认为互动模式
盘点一下我的 dot 库
```

**repo-from-scratch**
```text
/repo-from-scratch https://github.com/owner/repo
把这个仓库抽丝剥茧写成教程
```

它会先做一个五问"适配度评估",决定走完整重建、仅内核重建,还是 baby 模式(小型实现 + 心智模型卡)。

### 目录结构

```text
<skill>/
├── SKILL.md        # 入口:触发条件与工作流(必需)
├── references/     # 按需读取的方法论与规范
├── scripts/        # 辅助脚本(构建、校验、绘图)
└── templates/      # 输出模板与样式
```

### 编写与调试

- `SKILL.md` 顶部 frontmatter 的 `description` 决定何时触发,改触发词就改这里。
- 脚本路径相对 `SKILL.md` 所在目录;跨项目使用时用绝对路径,如 `~/.claude/skills/<skill>/scripts/...`。
- `repo-from-scratch/scripts/tests/` 含单元测试:`cd repo-from-scratch/scripts && uv run -m pytest tests`。

---

## English

A personal collection of [Claude Code](https://claude.com/claude-code) Skills built around *actually understanding things*: take a blog post or a GitHub project apart, rebuild it from scratch, and keep the transferable ideas.

### Skills

| Skill | What it does | Input | Output |
|---|---|---|---|
| [`blog-from-scratch`](blog-from-scratch/) | Regrows a blog post from scratch: the problem, the reasoning chain, the mental model, with the original figures redrawn. Not a summary or translation. | Blog URL or pasted text | A typeset HTML page |
| [`connect-dots`](connect-dots/) | Analyzes a GitHub project, extracts invariant, transferable ideas ("dots"), adds them to your personal dot library and finds connections between dots | GitHub URL or local repo path | Updates to your dot library |
| [`repo-from-scratch`](repo-from-scratch/) | Turns any repo into a from-scratch course for readers who only know basic Python (Raschka's "Build X From Scratch" approach) | Repo URL | Chapters, figures, verified code |

> Note: the skill prompts themselves are written mostly in Chinese; the skills respond in the language you use.

### Installation

Claude Code loads skills from `~/.claude/skills/<skill-name>/` (each needs a `SKILL.md`).

```bash
git clone https://github.com/efwfe/skills.git ~/Developer/skills

# Install via symlinks so `git pull` updates them
mkdir -p ~/.claude/skills
for s in blog-from-scratch connect-dots repo-from-scratch; do
  ln -s ~/Developer/skills/$s ~/.claude/skills/$s
done
```

Link only the ones you want. For a single project, place them in that project's `.claude/skills/` instead.

### Requirements

- [`uv`](https://docs.astral.sh/uv/): scripts run through `uv run` (`blog-from-scratch` needs `markdown`; `uv run --with markdown` installs it on the fly)
- Python 3.10+
- `git` and bash for `connect-dots`' timeline script
- See `repo-from-scratch/SKILL.md` for its figure and validation scripts

### Usage

Trigger by natural language in Claude Code, or invoke explicitly with `/skill-name`.

**blog-from-scratch**
```text
Help me really understand this post https://example.com/some-blog-post
/blog-from-scratch explain the intuition behind this: <pasted text>
```

**connect-dots**
```text
Learn from this project and extract dots https://github.com/owner/repo
/connect-dots quick ~/code/some-repo        # "quick" = fast mode; interactive by default
Review my dot library
```

**repo-from-scratch**
```text
/repo-from-scratch https://github.com/owner/repo
Write a from-scratch tutorial for this repo
```

It first runs a five-question fit assessment to choose between a full rebuild, a kernel-only rebuild, or baby mode (a small implementation plus a mental-model card).

### Layout

```text
<skill>/
├── SKILL.md        # Entry point: triggers and workflow (required)
├── references/     # Methodology and guidelines, read on demand
├── scripts/        # Helper scripts (build, validate, draw)
└── templates/      # Output templates and styles
```

### Authoring and debugging

- The `description` in each `SKILL.md` frontmatter controls when the skill triggers; edit trigger phrases there.
- Script paths are relative to the `SKILL.md` directory; use absolute paths like `~/.claude/skills/<skill>/scripts/...` from other projects.
- `repo-from-scratch/scripts/tests/` holds unit tests: `cd repo-from-scratch/scripts && uv run -m pytest tests`.
