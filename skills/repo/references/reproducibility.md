# 可复现性规则(代码经过验证,读者能重跑)

> 一句话:书里每个数字来自真实运行;任何读者按第 1 章给的环境与命令重跑,得到相同输出。
> 术语:可复现(reproducible)= 同环境同输入重跑得到相同输出;随机种子(random seed)= 决定随机数序列起点的整数。
> 工具:静态检查与 `--run` 双跑由 `scripts/check_repro.py` 完成,`scripts/lint_chapter.py` 复用其静态检查(导入,不复制)。

## 规则总表

| 编号 | 规则 | 检查方式 |
|---|---|---|
| R1 种子 | 每个产生随机的代码块,随机调用**之前**有对应 seed(下表);**每块自带种子**,读者能单独运行任一块 | `check_repro.py` 静态 |
| R2 环境 | `pyproject.toml` + `uv.lock` 锁定版本;第 1 章写明 Python 与关键包版本(真实打印得来)、设备 CPU | 发布门禁 |
| R3 输出 | 所有输出由 `verify_listings.py --fill` 真实运行写入;正文引用的数字只来自这些输出 | `verify_listings.py` |
| R4 两次一致 | 同一代码块放进新进程运行两次,输出必须一致 | `check_repro.py --run` |
| R5 浮点比较 | 跨平台可能的末位差异用 `torch.allclose(atol=…)` 断言,不逐位相等 | 审稿 |
| R6 读者复现 | 第 1 章写复现步骤(clone、`uv sync`、运行命令、期望的第一个输出) | 审稿 |

## 种子对照表

| 库 | 判定"用了随机"的写法 | 需要的种子语句 |
|---|---|---|
| torch | `torch.rand` / `torch.randn` / `torch.randint` / `torch.randperm` / `torch.multinomial` | `torch.manual_seed(N)` |
| numpy | `np.random.<任意函数>(`(`np.random.seed` 本身除外) | `np.random.seed(N)` |
| python | `random.<任意函数>(`(`random.seed` 本身除外) | `random.seed(N)` |

- 检查器只检查这三个库,其余(如 dropout、随机初始化的层)一概不查。

- seed 默认写在随机调用**之前**:同一块内更早的行,或前面更早的块;不靠"运行整章时的全局副作用",所以每个会产生随机的块自带种子,种子值写在块里。
- 用局部生成器(`torch.Generator(...)`、`np.random.RandomState(...)`、`random.Random(...)`)也是可复现做法,但检查器只认表中三种 seed;书中统一用三种 seed。
- `check_repro.py` 对违规按行号报错,报"A 之前没有 B 种子"。

## 环境与输出

- 版本锁定:`pyproject.toml` + `uv.lock`,一切用 `uv`;书里写明的版本号必须来自真实打印,不凭记忆。
- 设备统一 CPU,不用 `torch.cuda.*`。
- `torch.use_deterministic_algorithms`:书中默认不需要(它只保证部分算子的逐位一致);训练类章节若开启,写进该章"诚实边界 → 复现条件"。
- 两次一致(`--run`):每个块提成临时 `.py` 放进**新进程**各运行两次,比较 stdout;每块超时 60 秒;进程间 dict 遍历顺序的差异用环境变量 `PYTHONHASHSEED=0` 排除,与可复现无关。
- 依赖前面块定义的块不能单独运行,`--run` 不适用,只做静态检查。

## 读者复现步骤(第 1 章必写)

1. clone 仓库;
2. 进目录后 `uv sync`;
3. 运行第 1 章给出的命令(附第一次的完整输出,读者核对);
4. 期望的第一个输出与书中一致。

- 并在同一处说明:同环境同种子输出应与书中一致;不同平台/包版本可能有末位浮点差异,平台差异处书中用 `torch.allclose(atol=…)` 比较,不要求逐位相等。