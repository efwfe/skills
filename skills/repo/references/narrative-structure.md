# 叙事结构:全局与局部的脉络

写书时两条脉络同时存在:全局(读者永远知道"我在整本书的哪里")与局部(每个组件的讲述沿固定路径流动,不断流)。

## 全局层:全书脉络树

- 全书 = 若干 stage;每个 stage = 组件链(可嵌套子组件)。组件之间是依赖/演进关系:**A 的缺口 → B 来填**。
- 在 `00-scope.md` 里写一棵"全书脉络树"(stage → 组件 → 子组件),每个节点标注三件事:**上游给我什么 / 我做什么 / 我交给下游什么**(输入输出写 shape)。
- 每个 stage 对应一章或多章;一章只讲一个组件(或一个子组件)。章序 = 树的遍历序(stage 内自底向上)。
- 脉络树也是图片的素材:两级路线图都高亮当前位置(见 `figures.md`)。

| 图 | 位置 | figkit 方法 |
|---|---|---|
| stage 级路线图 | 每个 stage 的第一章开头(整棵树,本 stage 展开) | `Fig.roadmap_tree(stages, current, chain)` |
| 组件级小路线图 | stage 内每章开头(stage 固定,当前组件高亮) | `Fig.roadmap_chain(items, current, up=, down=)` |

- stage 的末章结尾画"本 stage 完成 → 下一 stage"过渡,或在小结回指整棵树。
- 每章章首第一行是**脉络条**(面包屑),格式固定:

```
Stage N › 组件 › 子组件
```

## 局部层:每个组件的固定脉流

每个组件的讲述按五步流动,一步不少:

1. **承接缺口**:上一节点把什么问题留给了我们(指向真实章节,不是空话)。
2. **问题与先失败**:先演示"没有它会怎样",必须真实运行(输出来自 `<run>`)。
3. **构造梯级**:L0…Ln,每级只加一个概念,接口不变。
4. **接口对齐**:输入就是上游的输出(核对 shape),本节点的输出 shape 接得住下游;对齐写在梯级代码的 shape 注释里。
5. **留下缺口**:本节还缺什么 → 一句话引出下一节点。

写作必填位置:章首"**承接的缺口**"(第一节之前)、小结前"**留下的缺口**"(与"下一章"预告一致)。空白断言 = 断流。

## GPT 示例(全书脉络树缩略)

```
stage-1 输入表示:tokenizer → {token-id, token-embedding, pos-embedding}
stage-2 模型:attention → causal-attention → multi-head-attention
             → components:{feedforward, layernorm, dropout} → gpt
stage-3 生成:gpt → text-generate
stage-4 训练
stage-5 微调:{classify, instruct}
```

节点标注示例(`Stage 2 › Attention › Causal attention`):

- 上游给我什么:attention 算出的未掩蔽分数,shape `[T, T]`
- 我交给下游什么:只保留历史的上三角分数,shape 仍为 `[T, T]`,交给 multi-head-attention