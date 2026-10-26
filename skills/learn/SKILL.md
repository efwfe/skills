---
name: learn
description: Entry point and dispatcher for the sc learning plugin. Give it a link, pasted text, a repo path, or "I want to learn X" or "build X from scratch", and it routes to the right skill: articles, papers, talks and design docs to sc:blog; rebuilding a repo (hands-on practice or a written course) to sc:repo; building a topic or reproducing a paper from first principles (paper only, paper + open weights, or many scattered sources) to sc:build; distilling a project's ideas, comparing two projects, or reviewing the dot library to sc:dots; organizing connections to sc:graph. Can chain a full learning route, pausing between steps. With no argument, reports dot library status and suggests a next step. Triggers: "/sc:learn", "help me learn this", "帮我学这个", "我该怎么学", "学习路线".
---

# sc:learn — 学习调度器

sc 插件(scratch)有五个学习 skill,共用一套"四层贯通"框架(思想 / 心智模型 / 架构 / 实现,见各 skill 的 `references/learning-lens.md`):

| 命令 | 输入 | 产出 | 大致耗时 |
|---|---|---|---|
| `/sc:blog` | 文章、论文、演讲、设计文档(链接、PDF 或正文) | 一页"从零重建"的 HTML;可选互动模式(先猜再看) | 一篇材料 |
| `/sc:repo` | 仓库 | **练习模式**:你写代码,Claude 出题、给提示、评审;**出书模式**:Claude 写成课程 | 长,按组件推进 |
| `/sc:build` | 一个主题,或一篇论文(可带开放权重、官方代码、笔记) | 从基本原理到能跑代码的路径 + 你亲手构建的实现 + 复现报告 | 长,按里程碑推进 |
| `/sc:dots` | 仓库;两个仓库(对比);或"盘点 dot 库" | dot 库的变化(新候选、强化、升级、张力) | 一个项目 |
| `/sc:graph` | dot 库 | 可交互关系图 + 梳理报告、先学路线、可能相关的建议、Mermaid/Canvas 导出 | 几分钟 |

所有命令是同一个**学习循环**的切面:用(先当黑盒用起来)→ 切(找到能切开的缝、量开销)→ 造(最小重建)→ 验(和裁判对账)→ 融(换零件、移植想法)→ 沉(收尾三问,沉淀成 dot)。详见 `${CLAUDE_PLUGIN_ROOT}/shared/learning-loop.md`。调度时告诉用户这一步在循环的哪里、下一步是什么。

每个命令收尾都会问**三问**:思想(哪个想法换个项目也成立)、直觉(哪个预测错了、修正了什么,记进预测日志)、方法(这次什么学法最管用)。

本 skill 只做调度:判断用哪个、按什么顺序,然后用 Skill 工具调用对应的 skill(名字写全,如 `sc:blog`),把用户的原始输入原样传过去。具体怎么做,由被调用的 skill 决定。

## 一、路由

按顺序匹配,命中即停:

1. **没有参数** → 状态模式(第三节)。
2. **明确点名**(用户说了 blog / repo / dots / graph,或"盘点""复盘""画图""关系图") → 直接调用对应 skill。
3. **要构建/复现**:说了"复现""实现这篇论文""从零实现""自己构建一个""build X from scratch",或给了论文 + 开放权重 → `sc:build`。
4. **文章类材料**:非代码托管站点的链接、论文(arXiv、PDF)、演讲视频、RFC/ADR/PEP 等设计文档,或一段粘贴的正文/文字稿 → `sc:blog`。用户说了"考我""练习""带我读"时,告诉它走互动模式。
5. **仓库**(GitHub/GitLab 链接或本地仓库路径):
   - **两个仓库**,或说了"对比""比较""区别" → `sc:dots` 的对比模式;
   - 说了"自己写""练习""动手""带我做" → `sc:repo` 的练习模式;
   - 说了"写教程""写课程""写成文章" → `sc:repo` 的出书模式;
   - 说了"从零""重建""抽丝剥茧"但没说谁写 → `sc:repo`,由它问练习还是出书;
   - 说了"提炼""思想""dot""沉淀""值得学什么" → `sc:dots`;
   - 没说意图 → 用一个问题让用户选(AskUserQuestion),选项:**提炼思想**(`sc:dots`,快,产出 dot)/ **动手重建**(`sc:repo` 练习模式,慢,你写代码)/ **写成课程**(`sc:repo` 出书模式)/ **完整路线**(第二节)。推荐项放第一个:仓库大、用户没时间 → 提炼思想;小而核心清楚 → 动手重建。
6. **一个主题而不是材料**("我想学推理模型""我想学 Raft")→ `sc:build`:它会推荐来源、让用户确认,再把来源拼成一条从基本原理到能跑代码的路径。用户只想先读懂、不想动手时,改为推荐 1–2 篇原始材料交给 `sc:blog`。
7. 都不像 → 用一句话说明五个命令各做什么,问用户想要哪个。

## 二、完整学习路线

用户要"完整学一遍"时,按顺序串起来,**每一步结束都停下来,告诉用户这一步的产出和下一步做什么,等用户说继续**——每一步都很长,不要一口气跑完:

- **仓库**:`sc:dots`(先抓核心赌注和 dot,半小时级)→ `sc:repo` 练习模式(按 dots 找到的最小内核定黄金路径,你亲手重建)→ `sc:graph`(把新 dot 挂进已有知识)。
- **一个问题的两种做法**:`sc:dots` 对比模式 → 对其中更小的那个走 `sc:repo` 练习模式 → `sc:graph`。
- **文章**:`sc:blog` → 如果文章里有通过剥名测试的候选 dot,问用户要不要用 `sc:dots` 收进库 → `sc:graph`。
- **一个主题**:`sc:build`(把论文、仓库、权重、笔记拼成一条路径,亲手构建)→ 路径里遇到读不懂的奠基论文,插一步 `sc:blog` → 最后 `sc:dots` + `sc:graph`。用户点名要学某个已经在库里的 dot 时,先跑 `learning_graph.py <dot库> --no-html --path <dot>` 看前置路线,从还没学的前置开始。

前一步的产物是后一步的输入:dots 的"最小内核阅读路线"给 repo 定黄金路径;blog 的心智模型和 repo 的贯通表给 dots 当参照(例证仍然只认原始出处)。

## 三、状态模式(不带参数)

1. 定位 dot 库(`$DOT_LIBRARY` → `~/dot-library/`)。
2. 存在 → 运行 `uv run python ${CLAUDE_PLUGIN_ROOT}/skills/graph/scripts/learning_graph.py <dot库> --report --no-html`,用三五行报告:学过几个项目/文章/课程、有几个 dot、直觉命中率与最近一次意外(有预测日志时)、最值得做的一件事(可升级的候选 > 最近的意外 > 悬挂链接 > 孤岛 > 没落到代码)。
3. 不存在 → 说明 dot 库是什么,建议从 `/sc:dots <一个你常用的仓库>` 开始。
4. 末尾列出五个命令,各一句话。

## 不要做

- 自己动手做被调用 skill 的活(例如在这里写文章或提炼 dot)。
- 用户意图不清时替他选一条几小时的路线。
- 在完整路线里不停顿地连续调用多个 skill。
