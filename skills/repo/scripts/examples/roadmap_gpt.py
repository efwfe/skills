#!/usr/bin/env python3
"""两级路线图示例(按 references/narrative-structure.md 的 GPT 五 stage):
- roadmap_tree.svg:stage 级,全书脉络树,当前 stage(stage-2 模型)高亮并展开组件链;
- roadmap_chain.svg:组件级,stage-2 固定,当前组件 causal-attention 高亮,标注上下游。

运行:uv run python roadmap_gpt.py
输出:scripts/examples/out/ 下的 svg + png。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from figkit import Fig

STAGES = ["stage-1 输入表示", "stage-2 模型", "stage-3 生成", "stage-4 训练", "stage-5 微调"]
CHAIN = ["attention", "causal-attention", "multi-head-attention",
         ("components", ["feedforward", "layernorm", "dropout"]), "gpt"]
CHAIN_PLAIN = ["attention", "causal-attention", "multi-head-attention", "components", "gpt"]

out = Path(__file__).resolve().parent / "out"
out.mkdir(exist_ok=True)

f = Fig(760, 260)
f.roadmap_tree(24, 40, STAGES, current=1, chain=CHAIN, w=120, h=34, gap=14, size=13,
               cgap=12, csize=13, min_cw=64, ch=34, sgap=8, ssize=13, min_sw=56, sh=28)
f.save(out / "roadmap_tree.svg")

g = Fig(760, 175)
g.roadmap_chain(30, 50, CHAIN_PLAIN, current=1, h=34, gap=12, size=13, min_w=64,
                stage="stage-2 模型",
                up="attention 给我:注意力分数",
                down="我交给 multi-head-attention:带因果掩码的权重")
g.save(out / "roadmap_chain.svg")

print("wrote", out / "roadmap_tree.svg", "与", out / "roadmap_chain.svg")