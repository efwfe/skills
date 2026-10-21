---
name: learn
description: scratch 插件的总入口和调度器。用户只给一个链接、一段正文、一个仓库路径或一句"我想学 X",就判断该用哪个学习 skill:文章 → scratch:blog;从零重建仓库 → scratch:repo;提炼项目思想、盘点 dot 库 → scratch:dots;梳理学习之间的联系 → scratch:graph;也能串起来跑完整的学习路线。不带参数时报告 dot 库现状并推荐下一步。当用户说"scratch""/scratch:learn""帮我学这个""我该怎么学这个""学习路线"时使用。
---

# scratch:learn — 学习调度器

scratch 插件有四个学习 skill,共用一套"四层贯通"框架(思想 / 心智模型 / 架构 / 实现,见各 skill 的 `references/learning-lens.md`):

| 命令 | 输入 | 产出 | 大致耗时 |
|---|---|---|---|
| `/scratch:blog` | 文章链接或正文 | 一页"从零重建"的 HTML | 一篇文章 |
| `/scratch:repo` | 仓库 | 从零构建的课程(章节、配图、可验证代码) | 长,按章推进 |
| `/scratch:dots` | 仓库;或"盘点 dot 库" | dot 库的变化(新候选、强化、升级、连接) | 一个项目 |
| `/scratch:graph` | dot 库 | 可交互关系图 + 梳理报告 | 几分钟 |

本 skill 只做调度:判断用哪个、按什么顺序,然后用 Skill 工具调用对应的 skill(名字写全,如 `scratch:blog`),把用户的原始输入原样传过去。具体怎么做,由被调用的 skill 决定。

## 一、路由

按顺序匹配,命中即停:

1. **没有参数** → 状态模式(第三节)。
2. **明确点名**(用户说了 blog / repo / dots / graph,或"盘点""复盘""画图""关系图") → 直接调用对应 skill。
3. **文章**:非代码托管站点的链接,或一段粘贴的文章正文 → `scratch:blog`。
4. **仓库**(GitHub/GitLab 链接或本地仓库路径):
   - 说了"从零""重建""写教程""写课程""抽丝剥茧" → `scratch:repo`;
   - 说了"提炼""思想""dot""沉淀""值得学什么" → `scratch:dots`;
   - 没说意图 → 用一个问题让用户选(AskUserQuestion),选项:**提炼思想**(`scratch:dots`,快,产出 dot)/ **从零重建**(`scratch:repo`,慢,产出课程)/ **完整路线**(第二节)。推荐项放第一个:仓库大、用户没时间 → 提炼思想;小而核心清楚 → 从零重建。
5. **一个主题而不是材料**("我想学 Raft")→ 不要凭记忆讲课。先问用户手里有没有想读的文章或仓库;没有就推荐 1–2 篇原始文章和 1 个小而经典的实现(说明为什么选它们),让用户挑,再按 3、4 路由。
6. 都不像 → 用一句话说明四个命令各做什么,问用户想要哪个。

## 二、完整学习路线

用户要"完整学一遍"时,按顺序串起来,**每一步结束都停下来,告诉用户这一步的产出和下一步做什么,等用户说继续**——每一步都很长,不要一口气跑完:

- **仓库**:`scratch:dots`(先抓核心赌注和 dot,半小时级)→ `scratch:repo`(按 dots 找到的最小内核定黄金路径,从零重建)→ `scratch:graph`(把新 dot 挂进已有知识)。
- **文章**:`scratch:blog` → 如果文章里有通过剥名测试的候选 dot,问用户要不要用 `scratch:dots` 收进库 → `scratch:graph`。
- **一个主题**:先读一两篇原始文章(`scratch:blog`)建立直觉,再挑一个小实现(`scratch:repo`),最后 `scratch:dots` + `scratch:graph`。

前一步的产物是后一步的输入:dots 的"最小内核阅读路线"给 repo 定黄金路径;blog 的心智模型和 repo 的贯通表给 dots 当参照(例证仍然只认原始出处)。

## 三、状态模式(不带参数)

1. 定位 dot 库(`$DOT_LIBRARY` → `~/dot-library/`)。
2. 存在 → 运行 `uv run python ${CLAUDE_PLUGIN_ROOT}/skills/graph/scripts/learning_graph.py <dot库> --report --no-html`,用三五行报告:学过几个项目/文章/课程、有几个 dot、最值得做的一件事(可升级的候选 > 悬挂链接 > 孤岛 > 没落到代码)。
3. 不存在 → 说明 dot 库是什么,建议从 `/scratch:dots <一个你常用的仓库>` 开始。
4. 末尾列出四个命令,各一句话。

## 不要做

- 自己动手做被调用 skill 的活(例如在这里写文章或提炼 dot)。
- 用户意图不清时替他选一条几小时的路线。
- 在完整路线里不停顿地连续调用多个 skill。
