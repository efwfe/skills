---
name: graph
description: Draw the personal dot library (dots, candidates, project notes, and learning records from sc:blog and sc:repo) as an interactive relationship graph with a tidy-up report: hubs, islands, dangling links, promotable candidates, half dots, dots never traced to code, tensions. Also timeline replay, prerequisite paths, suggested links, and Mermaid / Obsidian Canvas export. Use to organize and review how the things you have learned connect. Triggers: "/sc:graph", "knowledge graph", "画出我的知识图谱", "梳理 dot 库", "学习之间的联系", "可视化学习关系".
---

# sc:graph — 把学过的东西画成一张图

> 路径说明:本 skill 目录是 `${CLAUDE_PLUGIN_ROOT}/skills/graph`(作为 sc 插件安装时,该变量会被自动替换成绝对路径);手动安装时就是本 SKILL.md 所在目录(加载时给出的 Base directory)。

一张图回答两件事:**我学过的东西之间连上了没有**,以及**下一步该补哪里**。图只读 dot 库里的 Markdown 和 `[[链接]]`,不需要另外维护数据。

## 一、生成

1. 定位 dot 库:用户本次指定的路径 → 环境变量 `DOT_LIBRARY` → `~/dot-library/`。目录不存在就告诉用户先用 `/sc:dots` 分析一个项目,不要自己建。
2. 运行(零第三方依赖):

```bash
uv run python ${CLAUDE_PLUGIN_ROOT}/skills/graph/scripts/learning_graph.py <dot库> --report
# 可选:--extra ~/notes 把别的笔记目录也画进来;--json out.json 导出图数据;--out 指定 HTML 位置
```

其他用法(可以和上面合在一条命令里):

| 参数 | 用途 |
|---|---|
| `--path <dot>` | 学这个 dot 之前要先学什么:沿"依赖"边按先学后学排好;依赖成环会提示(常见原因是把张力写成了依赖) |
| `--suggest [N]` | 可能相关但还没连上的 dot 对:一句话字面相似,或共享同一个例证来源。**只是线索**,要用户按同源判断三条确认 |
| `--mermaid out.md` | 导出 Mermaid 图,可贴进 Markdown、GitHub 或 Obsidian |
| `--canvas out.canvas` | 导出 Obsidian Canvas;放在 dot 库目录里,节点会直接链接到对应文件 |

3. 产物是 `<dot库>/graph.html`:单文件、离线可用、明暗主题、手机可看。它是生成物,确认 dot 库的 `.gitignore` 里有 `graph.html`,没有就加上。
4. 把 HTML 路径给用户。当前环境支持直接发送文件时,把它发给用户。

## 二、图怎么读

| 元素 | 含义 |
|---|---|
| 实心圆 | 已确认的 dot(蓝)、项目(绿)、学习记录(按 `projects/` 里的文件名前缀:`blog-` 文章、`paper-` 论文、`talk-` 演讲、`doc-` 设计文档、`course-` 课程)、归档(灰)、其他笔记(石板灰) |
| 空心圆 | 候选 dot |
| 虚线空心圆 | 悬挂链接:被 `[[链接]]` 引用,但库里没有这个文件 |
| 边 | 例证(绿)、同源异形(蓝)、张力(红虚线)、依赖(紫箭头)、传承(棕点线箭头)、关联(灰) |
| 圆的大小 | 连接越多越大 |

交互:点节点看内容、连接、问题标记、"先学"路线和"可能相关"建议;有日期的库会出现时间轴滑块,拖动它回放这张网是怎么长出来的(日期取"首次记录""分析日期""日期");双击节点只看它的两层邻域;搜索框按名字和一句话过滤;"高亮"下拉框按问题过滤(可升级、半个、没落到代码、没有连接、孤立、悬挂链接);图例可以点击,开关某类节点或边。

边的类型从 `[[链接]]` 所在位置推断,所以写 dot 时按 `sc:dots` 的模板写,图就是对的:
- `## 例证` 和项目笔记的 `## 本项目涉及的 dot` 小节 → 例证;
- `## 连接` 小节里以 同源异形 / 张力 / 依赖 / 传承 开头的行 → 对应类型;
- `tensions.md` 里同一行出现的两个链接 → 张力;
- 其他位置 → 关联。

## 三、梳理(和用户一起过一遍报告)

`--report` 输出的每一类问题都对应一个动作。按下面的顺序,每类最多拿 3 个出来和用户过,不要一次倒一长串:

| 报告里的 | 意味着 | 动作 |
|---|---|---|
| 可升级 | 候选已有 ≥2 个例证 | 交给 `/sc:dots`,走同源判断三条,用户确认后升级 |
| 悬挂链接 | 链接指向不存在的文件 | 问用户:是拼错了(改链接),还是一个值得记的想法(用 `/sc:dots` 建候选) |
| 孤岛 / 没有连接的 dot | 学过但没挂到别的知识上 | **先问用户**:"它和库里哪个想法像、和哪个拉扯?"用户说出来后再按同源判断三条核对,通过才写进 `## 连接` |
| 没落到代码 / 半个 | 只停在思想层,或缺一面 | 记进建议:下次分析项目时专门追到 `path:line` |
| 枢纽 | 功底所在 | 提醒用户给它们写"我自己的话" |
| 张力 | 两个想法互相拉扯 | 让用户说出各自在什么场景占上风,补进 `tensions.md` |
| 可能相关(`--suggest`) | 字面相似或共享例证,但还没连上 | 一次拿一对,**先问用户**它们是不是同一个机制;写得出共同机制、区别、对两边都成立的那句话才连,否则放过 |
| 先学路线(`--path`) | 用户想学某个 dot 时 | 按顺序给出前置;前置里还是候选或半个的,提示先补它 |

规则与 `sc:dots` 一致:**思考留给用户**(能让用户先说的,Claude 后说);**宁可漏连,不可错连**;不代写"我自己的话";改 dot 文件前先读,只追加或局部修改;改完在 dot 库里 `git add -A && git commit -m "sc:graph: 梳理"`。

最后给用户的回复要短:图的路径、一句话说整体形状(几个连通块、枢纽是谁),以及最值得做的 1–3 件事。
