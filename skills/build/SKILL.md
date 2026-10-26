---
name: build
description: Understand a topic or a paper by building it yourself. Stitches the scattered sources (papers, repos, open weights, blog posts, implementation notes) into one clear path from first principles to working code, reconciles where they disagree, then has you build it step by step against the strongest available check, from matching open-weight logits and official code outputs down to the paper's own numbers and toy-scale experiments. Covers paper-only reproduction, paper plus open weights, paper plus code, and whole topics such as "reasoning models" or "KV cache". Practice mode by default (you write the code; Claude prepares labs, tests, hints and reviews); "quick" mode has Claude build it and report. Triggers: "/sc:build", "build X from scratch", "reproduce this paper", "复现这篇论文", "从零实现", "自己构建一个", "把论文和代码拼起来".
---

# sc:build — 自己构建一个,才算真懂

> 路径说明:本 skill 目录是 `${CLAUDE_PLUGIN_ROOT}/skills/build`(作为 sc 插件安装时,该变量会被自动替换成绝对路径);手动安装时就是本 SKILL.md 所在目录(加载时给出的 Base directory)。

研究一个新方向时,想法散在论文、代码仓库、权重配置和零散的实现笔记里,要自己一块块拼起来。这个 skill 替学习者做拼图:**把分散的来源整理成一条从基本原理到能跑的代码的路径,然后让学习者沿着它亲手构建一个**。理解一个东西最好的办法,是自己构建一个。

它和其他命令的分工:`sc:blog` 读懂一篇材料的论证;`sc:repo` 重建一个已有仓库;`sc:dots` 跨项目沉淀思想;**`sc:build` 围绕一个主题或一篇论文,把多个来源合成一条构建路径**,单个仓库只是它的来源之一。

## 一、开始:定主题、定终点、清点来源

1. **一句话主题和终点演示**:学完后亲手跑出什么(例如"一个能在数学题上用多数投票提高正确率的小推理模型")。缺了就先问用户,不要猜。
2. **清点来源**,每个来源一行写进 `sources.md`(模板 `templates/sources.md`):类型、链接、版本(commit / arXiv 版本号 / 权重修订版)、它在路径里扮演的角色(讲原理 / 给规格 / 当裁判 / 补实现细节)、可信度。
   - 用户只给了主题:推荐 1–3 篇奠基或综述论文、1 个小而清楚的参考实现、可用的开放权重,说明为什么选它们,让用户确认后再开始。
   - 论文的原文和图怎么拿全,见 `${CLAUDE_PLUGIN_ROOT}/skills/blog/references/sources.md`。
3. **定场景**,它决定拿什么当裁判(`references/oracles.md`):

| 场景 | 判断依据(从强到弱取最强的一个) |
|---|---|
| 有开放权重 | 同一输入下,你的实现与参考实现的 logits 对上(`allclose`) |
| 有官方代码 | 同一输入、同一种子下,输出与官方代码一致 |
| 只有论文 | 结构类主张精确核对(参数量、形状、复杂度);机制与消融方向在玩具规模上复现 |
| 只有笔记/博客 | 内部一致性 + 不变量 + 玩具实验;结论写得最保守 |

4. **算力预估**:默认学习者只有 CPU。动手前估算参数量、显存/内存、单次运行时间;超出就选更小的权重版本、缩小玩具规模,或先问用户。

## 二、拆解:把来源变成可实现的规格

1. **主张清单** `claims.md`(模板 `templates/claims.md`):把论文(和其他来源)拆成一条条主张,每条标出处,分四级——结构类(能精确核对)/ 机制类(玩具任务上该出现的现象)/ 消融方向(拿掉某部分变好还是变差)/ 头条数字(通常复现不了,照实标出)。**复现的是主张,不是数字。**
2. **规格书** `spec.md`(模板 `templates/spec.md`):每个公式对应一个函数,写清输入输出形状;每个超参数注明出处;**列出所有来源都没写的东西**——初始化、归一化位置、eps、分词、数据处理、学习率调度、采样参数……这张"没写的东西"清单是拼图最费劲的地方,也是最值得学的地方。
3. **对账来源**:同一件事,论文、代码、权重配置、笔记说法不一时,写进 `sources.md` 的差异表,每条写明各自怎么说、以谁为准、为什么。默认:"实际发布的模型是怎么做的"以权重和官方代码为准;"作者本来想怎么做"以论文为准;两边都记。
4. **有开放权重时**,先画参数地图(不下载权重、不需要 PyTorch):

```bash
uv run python ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/weights_map.py <本地目录 | hf:owner/name | URL> --expect <论文里的参数量>
```

   把"论文符号"一列填满:每个权重对应论文哪个公式里的哪个符号;对不上的,进差异表。

## 三、路径:从基本原理到能跑的代码

按 `references/path-design.md` 设计 `00-path.md`(模板 `templates/path.md`):一串里程碑,每个里程碑**结束时手里都有一段能跑、能验证的代码**。

- 从基本原理出发:第一个里程碑只依赖最少的前置(读者会基础 Python),先让最朴素的版本跑起来。
- 每个里程碑只加一个新概念,写清:它解决上一步的什么不足、来自哪个来源(论文第几节 / 仓库 `path:line` / 笔记)、用什么裁判验证、在四层透镜里属于哪一层。
- 路径画完先给用户看一眼,确认后再备课。

## 四、构建

- **练习模式(默认)**:学习者写代码,Claude 当教练。备课、出题、先预测、阶梯提示、评审、贯通题的做法与 `sc:repo` 练习模式相同,见 `${CLAUDE_PLUGIN_ROOT}/skills/repo/references/practice-mode.md`(模板在 `${CLAUDE_PLUGIN_ROOT}/skills/repo/templates/lab-*.md` 与 `lab-test.py`)。区别只在每个里程碑的测试用本 skill 定的裁判:对上 logits、对上官方输出、对上论文的结构数字,或玩具实验的趋势(多种子)。
- **快速模式**(用户说"快速""直接做"):Claude 自己按路径构建并验证,学习者读 `00-path.md` 和报告。路径与报告本身就是一份能交给别人的"清晰路径"。

## 五、验证与报告

- 各场景的验证做法、对不上时怎么逐层定位、怎么用真实权重检验论文主张,见 `references/oracles.md`。
- 收尾写 `report.md`(模板 `templates/report.md`):每条主张一行(复现 / 部分复现 / 未复现 / 无法在此规模检验,附证据与原因);差异表;"没写的东西"最后各取了什么值、依据是什么;四层贯通表;用户自己的话。
- 有 dot 库时写学习记录 `projects/build-<主题>.md`(格式同 `sc:blog` 的学习记录,`类型` 写 `build`),"关联的 dot"只链接库里已有的 dot,候选只写文字,入库走 `/sc:dots`。

## 产物目录

```
build-<主题>/
  sources.md      来源清单 + 差异表
  claims.md       主张清单(四级)
  spec.md         规格书 + "没写的东西"
  00-path.md      从基本原理到能跑的代码的里程碑路径
  lab/            练习模式的练习目录(或快速模式的实现)
  experiments/    玩具实验:脚本、种子、结果 JSON
  report.md       复现报告
```

## 不要做

- 凭记忆补论文没写的细节而不标出来——补了就写进"没写的东西",注明取了什么值、依据是什么。
- 把单次运行、单个种子的结果写成结论;把玩具规模的结果写成"复现了论文的数字"。
- 拿非官方实现当裁判:它只能当对照参考。
- 为了凑齐路径,一次加多个新概念;或者里程碑结束时没有能跑的代码。
- 不看许可证就使用权重或代码:动手前确认用途允许,写进 `sources.md`。

## 文件地图

- `references/path-design.md` — 怎么把分散的来源排成一条从基本原理到能跑代码的路径;一个"推理模型"主题的示例路径
- `references/oracles.md` — 裁判的强弱顺序;只有论文、有权重、有代码三种场景的验证做法;逐层定位;用权重检验主张
- `references/learning-lens.md` — 四层透镜(与 sc:blog、sc:repo、sc:dots 共用)
- `templates/` — `sources.md`、`claims.md`、`spec.md`、`path.md`、`report.md`
- `scripts/weights_map.py` — 读 safetensors 头生成参数地图,零依赖,远程只读头部
