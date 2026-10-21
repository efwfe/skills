---
name: repo
description: Rebuild a GitHub repo from scratch to really understand it. Practice mode (default for self-study) - the user writes the code while Claude coaches with per-component labs, failing tests, oracle outputs from the original repo, tiered hints and reviews. Book mode - Claude writes a from-scratch course for readers who only know basic Python (Raschka "Build X From Scratch" style) with verified code and figures. A fit assessment routes each repo to a full rebuild, a kernel-only rebuild, or a small "baby" version. Use when the user wants to learn a repository by rebuilding it, practice implementing it, or write tutorial chapters about it. Trigger on "from scratch", "从零重建", "自己写一遍", "练习", "抽丝剥茧", "学习这个仓库", "写教程", "/sc:repo".
---

# sc:repo — 把仓库从零重建成课程

> 路径说明:本 skill 目录是 `${CLAUDE_PLUGIN_ROOT}/skills/repo`(作为 sc 插件安装时,该变量会被自动替换成绝对路径);手动安装时就是本 SKILL.md 所在目录(加载时给出的 Base directory)。下文的 `scripts/`、`references/`、`templates/` 都相对这个目录。

把一个陌生仓库,变成"从空文件夹重新长出来"的课程。方法源自 Raschka《Build a LLM From Scratch》(拆解见 `references/pedagogy.md`),泛化到任意仓库。

## 两种模式

| 模式 | 什么时候 | 谁写实现 | 产物 |
|---|---|---|---|
| **练习模式** | 用户自己想学会:"我想自己写一遍""练习""动手""带我做" | 用户 | `lab/`:每个组件一个练习目录(题面、骨架、测试、oracle)+ `PROGRESS.md` |
| **出书模式** | 要写给别人读:"写教程""写课程""写成文章""出书" | Claude | `chapters/`、`figures/`,下文的写作流水线 |

用户没说清时,用一个问题让他选(AskUserQuestion),**练习模式**放第一个并标推荐——亲手重建才学得会。练习模式的完整做法见 `references/practice-mode.md`:阶段 0–2.5 照常做(只为备课),之后不走写作流水线,改成"出题 → 先预测 → 用户实现 → 阶梯提示 → 评审 → 贯通题"的循环。`lab/PROGRESS.md` 存在时,说明用户在继续上次的练习,先读它,从停下的那一级接着练。

下文的总原则、信条和工作流以出书模式为准;其中关于"真实运行、原仓库是预言机、一级只加一个概念、四层贯通"的部分,两种模式都守。

## 总原则

这些规则都是帮你把知识讲清楚的默认做法。规则与"读者能不能看懂"冲突时,以看懂为准;可以破例,但在该章"诚实边界"框或写作备注里写一句理由。检查脚本的"提醒"只是提示,由作者判断。

**读者画像:只会基础 Python。** 假设他会:变量、函数、循环、dict/list、用 uv/pip 装包、照着脚本敲并看输出。**不假设**他会 PyTorch、线性代数、概率——所有前置概念要么写进书的附录 A,要么注册进术语表(见 `references/beginner-reader.md`)。

## 核心信条(十五条)

1. **先失败,再方案**:每个组件前先演示没有它会怎样,而且要**真的运行**给读者看。
2. **骨架先行**:`Dummy*` 占位,项目任何时刻能跑。
3. **阶梯**:玩具 → 真实数据结构 → 真实语义 → 向量化 → 真实规模;每级只加一个概念,接口不变。
4. **原仓库是预言机**:最终输出必须与原仓库同输入下一致;不一致就改教程。
5. **输出必须真实**:代码跑过,输出由脚本写入,绝不由模型"想象"。
6. **手算小例先行**:每个新概念先过一遍极小手算例(纸上和代码各一遍),再讲公式和代码。
7. **形状是一等公民**:每个关键张量写 shape 并逐轴解释,读者永远不迷路。
8. **不变量解释"为什么成立"**:不只给代码,给要证明的性质并写成 `assert`。
9. **评估/基线先行**:训练、优化类内容动手前先量出差距。
10. **诚实边界集中放置**:正文只写已验证的事实,所有"没验证"集中进每章一个"诚实边界"框;统一用"我们",不写元文字。
11. **两级脉络**:`00-scope.md` 先画全书脉络树(stage → 组件 → 子组件,节点标"上游给我 / 我交给下游");每章章首脉络条 + 两级路线图,局部叙述固定五步(承接缺口 → 先失败 → 梯级 → 接口对齐 → 留下缺口,`references/narrative-structure.md`)。
12. **有声音**:并肩搭东西的老手口吻,先画面后术语,用五个心智模型反复说同一件事(见 `references/voice.md`)。
13. **流程带编号、抽象对象细讲**:讲有先后顺序的过程,编号贯穿正文、代码注释、图、输出;token、隐状态、算法中间量这类看不见的东西,至少打印一次真实的值并逐步追踪(见 `references/process-narration.md`)。
14. **主线连贯,支线分流**:稍复杂但不影响主线的内容放附录 B(深入专题),正文只留结论和指路;一两句的放旁枝框;被多章依赖的基础放附录 A(见 `references/appendix-policy.md`)。
15. **四层贯通**:重建不是目的,融会贯通才是。每个本质组件都要在**思想 → 心智模型 → 架构 → 实现**四层之间打通:每章一节"设计取舍"(设计决策卡:问题与约束、备选、选择与代价、证据、约束变了会怎样),全书一张贯通表,收尾一章"融会贯通"把全书串成一张图(见 `references/learning-lens.md`)。

## 工作流

| # | 步骤 | 做什么 | 产物 / 验证 |
|---|---|---|---|
| 0 | 定义 | 克隆、跑起来;写"一句话/黄金路径/终点演示" | `00-scope.md`;**能跑才继续** |
| 0.5 | 适配度评估 | 五问三档(`references/fit-assessment.md`),答案写进 `00-scope.md`;档位有争议先问用户 | A 走 1–9 全流程;B 只重建内核;C 走 baby 模式(`references/baby-mode.md`) |
| 1 | 地图 | `uv run python ${CLAUDE_PLUGIN_ROOT}/skills/repo/scripts/repo_map.py <repo>` | 入口、核心、import 分层;区分 本质/工程/扩展 |
| 2 | 追路径 | 最小输入 + 插桩打印名字与 shape;逐节点做删除实验 | 数据流脊柱 + 本质清单 |
| 2.5 | 架构与思想 | 画架构总图(3–7 个零件、每条边写传什么);每条关键边界写一张设计决策卡;为每个本质组件提炼领域心智模型;填贯通表初稿(`repo-dissection.md` 阶段 2.5) | `00-scope.md` 的"架构与设计决策""领域心智模型""贯通表" |
| 3 | 阶梯 | 为每个本质组件设计 L0…Ln | 每章阶梯草稿 |
| 4 | 前置盘点 | 列出全书用到的所有前置概念,三分:只一章用 → 该章正文/旁枝;多章用 → 附录 A + 术语表;全书脚手架 → 第 1 章 | 前置阶梯清单 + 术语表初稿(`references/beginner-reader.md`) |
| 5 | 规格表 | 每个概念填位置/失败动机/玩具实例/阶梯/不变量/Oracle 对比(`repo-dissection.md` 阶段 6) | 章节规格表 |
| 6 | 对账 | 建 `oracle/`:固定种子保存原仓库输出 | 每章末尾一个 `assert` |
| 7 | 起草 | 事实包 → 大纲 → 起草(宿主会话)→ 隔离上下文审稿 → 初学者通读 → 修订(`references/writing-pipeline.md`) | `chapters/NN.md` |
| 8 | 验证 | `uv run python ${CLAUDE_PLUGIN_ROOT}/skills/repo/scripts/verify_listings.py chapters/NN.md --fill`;再跑 `${CLAUDE_PLUGIN_ROOT}/skills/repo/scripts/lint_chapter.py`、`${CLAUDE_PLUGIN_ROOT}/skills/repo/scripts/check_repro.py` 与 `${CLAUDE_PLUGIN_ROOT}/skills/repo/scripts/check_images.py` | 所有块通过;输出真实;随机块有 seed;lint 零违规 |
| 9 | 画图 | `${CLAUDE_PLUGIN_ROOT}/skills/repo/scripts/figkit.py`(`references/figures.md`) | `figures/*.svg` + `.png`,打开检查 |
| 10 | 融会贯通 | 全部章节完成后写收尾章(`templates/synthesis.md`):回到架构总图、贯通表定稿、设计决策汇总、迁移与改约束练习、真实仓库阅读路线 | `chapters/99-synthesis.md` |

每一步结束前,按对应文档的"默认做法/门禁"自查。**步骤 0 若缺信息(例如终点演示不明),先问用户,不要猜。**

## 文件地图

- `references/practice-mode.md` — 练习模式:备课门禁、每级练习循环、提示阶梯、评审与收尾
- `references/learning-lens.md` — 四层透镜(思想/心智模型/架构/实现)、纵向贯通与横向连接、设计决策卡、贯通自测题(三个 skill 共用)
- `references/pedagogy.md` — 书的 12 条教学手法 + 一节的标准节奏 + 给基础薄弱读者的讲解顺序 + 每个组件的脉络规则
- `references/narrative-structure.md` — 全局脉络树与局部五步脉流、脉络条格式、两级路线图的位置与图注
- `references/beginner-reader.md` — 读者画像、前置阶梯盘点规则、附录 A 目录与术语表条目格式
- `references/appendix-policy.md` — 什么放正文、旁枝框、附录 B 还是附录 A:判断标准、附录项写法、正文指路格式
- `references/repo-dissection.md` — 抽丝剥茧流程(阶段 0–8,含 0.5 适配度评估)+ 章节规格表 + 各类仓库脊柱
- `references/fit-assessment.md` — 适配度五问 + A/B/C 三档(阶段 0.5 用)
- `references/baby-mode.md` — C 档专用:心智模型卡、baby 实现、对照表、差距小节
- `references/writing-style.md` — 口吻、章节骨架、默认做法(≤15 行、免责集中、无元文字、"我们"统一)
- `references/process-narration.md` — 讲有先后顺序的过程:编号贯穿四处、每步四件事、抽象对象打印真实值、逐步追踪表
- `references/voice.md` — 叙述声音与五个心智模型:老手口吻、画面→失败→名字→小例子→一般形式、固定位置的话、声音自检
- `references/reproducibility.md` — 可复现性默认做法:随机调用前有 seed、环境锁定、输出由脚本写入、第 1 章复现步骤
- `references/writing-pipeline.md` — 写作流水线、起草/审稿/初学者通读提示词、baby 模式补充、发布门禁
- `references/figures.md` — 图的特征、类型表、图注单写规则、边界检查与 PNG 回退链
- `templates/lab-readme.md` · `templates/lab-progress.md` · `templates/lab-test.py`(练习模式)
- `templates/chapter.md` · `templates/synthesis.md`(收尾章"融会贯通")· `templates/appendix-basics.md` · `templates/appendix-deepdive.md` · `templates/glossary.md` · `templates/scope.md`(00-scope.md)· `templates/mental-model-card.md`(领域心智模型卡;baby 模式的主交付物)
- `scripts/repo_map.py` · `assemble_chapter.py` · `verify_listings.py` · `figkit.py` · `check_images.py` · `lint_chapter.py` · `check_repro.py`(均用 `uv run python` 运行,零第三方依赖)


## 学习记录(有 dot 库时)

如果用户有 dot 库(`$DOT_LIBRARY` 或 `~/dot-library/` 存在;**不存在就跳过,不要创建**),写一条学习记录 `projects/course-<课程名>.md`,让 `/sc:graph` 能把这次学习画进关系图。在 `00-scope.md` 定稿后写第一版,收尾章写完后更新"核心心智模型"(取自贯通表):

```markdown
# <标题>

- 类型:course
- 来源:<原始链接>
- 产物:<本地路径>
- 日期:YYYY-MM-DD

## 核心心智模型
- <一句话>

## 关联的 dot
- [[<已存在的 dot 名>]]:<一句话说明关系>

## 候选 dot(未入库)
- <名字>:<剥名后的一句话>(用 /sc:dots 收入)
```

- `## 关联的 dot` 只链接 `index.md` 里**已经存在**的 dot,关系要具体到共同机制;找不到就留空。不确定的连接不写——宁可漏连,不可错连。
- 候选 dot 只写文字、不加 `[[ ]]`,**不在 `dots/`、`candidates/` 里建文件**:入库要走 `/sc:dots` 的四个测试和同源判断。
- 写完在 dot 库里 `git add projects/course-<课程名>.md && git commit -m "sc:repo: <标题>"`。

## 约定

- 产物目录:`<course>/{00-scope.md, oracle/, chapters/, figures/, facts/}`;附录 A 与术语表作为 `chapters/` 下的独立文件;附录 B 的各项放在 `chapters/appendix-b-*.md`。
- Python 一律 `uv`。
- 事实溯源:引用原仓库写 `path:line`;没核对的数字不写(写进"诚实边界"框)。
- 仓库较大时,先问用户要学哪条黄金路径,不要试图一次覆盖整个仓库。

## 不要做

- 按文件树顺序讲;一上来贴完整类;为"完整"讲每个配置项。
- 一个代码块超过 15 行(超了就拆成带打印的小步)。
- 在正文写"我没验证/未验证/我没有运行"——集中进"诚实边界"框。
- 提 Raschka、写作流程、"这对应…的思路"这些元文字;正文说"我们"不说"我"。
- 术语不定义就用;同一概念讲完后再反复重讲。
- 让模型生成代码输出;让起草的上下文审自己的稿。
- 写成说明文档:先罗列参数再举例;营销腔和权威腔。
- 把工程细节(分布式、缓存、CLI)塞进主线 —— 放"工程篇"。
- 只讲"怎么写"不讲"为什么这样设计":每个本质组件都要有设计取舍与它在架构总图里的位置;把架构写成目录清单、把心智模型写成比喻。