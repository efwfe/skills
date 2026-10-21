#!/usr/bin/env python3
"""可复现性检查:随机调用之前必须有 seed;--run 时每个块跑两次比较输出。

用法:uv run python check_repro.py <md...> [--run]

静态检查(默认):解析 ```python 代码块;出现随机调用(torch.rand/randn/
randint/randperm/multinomial、np.random.*、random.*)时,该调用之前的同一块
或更早的块里必须有对应 seed(torch.manual_seed / np.random.seed / random.seed),
否则按行号报错。只检查这三个库,其余一概不查。规则细则见
references/reproducibility.md。

--run:把每个块(以 `# skip` 开头的除外)提成临时 .py,放进独立子进程各运行
两次比较 stdout,不同则报错;子进程环境固定 PYTHONHASHSEED=0,排除进程间
dict 遍历顺序差异。每块超时 60 秒。依赖前面块定义的块无法单独运行,
--run 会把它们当失败上报。

退出码 0 表示全部通过,1 表示有违规。
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FENCE = re.compile(r"^```")
PY_OPEN = re.compile(r"^```(?:python|py)\s*$")

SEED_HINT = {"torch": "torch.manual_seed(...)", "numpy": "np.random.seed(...)",
             "python": "random.seed(...)"}

SEEDS = {
    "torch": re.compile(r"(?<![\w])torch\.manual_seed\s*\("),
    "numpy": re.compile(r"(?<![\w.])np\.random\.seed\s*\("),
    "python": re.compile(r"(?<![\w.])random\.seed\s*\("),
}

RANDOM_CALLS = [
    ("torch", re.compile(r"(?<![\w])torch\.(rand|randn|randint|randperm|multinomial)\s*\(")),
    ("numpy", re.compile(r"(?<![\w.])np\.random\.([A-Za-z_][A-Za-z0-9_]*)\s*\(")),
    ("python", re.compile(r"(?<![\w.])random\.([A-Za-z_][A-Za-z0-9_]*)\s*\(")),
]
NO_SEED_NAMES = {"numpy": {"seed", "default_rng", "RandomState"},   # default_rng(seed) / RandomState(seed) 自带种子
                 "python": {"seed", "Random"}}                       # random.Random(seed) 是自带种子的局部生成器


def _python_blocks(path):
    """逐块产出 (code_start_line, code_end_line, code),只收 ```python 围栏。"""
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").split("\n")
    in_block = False
    for i, ln in enumerate(lines, 1):
        if not in_block:
            if PY_OPEN.match(ln):
                in_block = True
                start = i + 1
            continue
        if FENCE.match(ln):
            code = "\n".join(lines[start - 1:i - 1])
            if code.strip():
                yield start, i - 1, code
            in_block = False


def seed_violations(path, blocks=None):
    """返回 [(line, call_text, seed_hint)]:随机调用之前没有对应 seed 的违规。

    种子只要出现在该行之前的任何 python 块里就有效;同一行先写 seed
    再调用也算有效(以行为粒度)。
    """
    blocks = list(_python_blocks(path)) if blocks is None else blocks
    last_seed = {}
    out = []
    for start, _, code in blocks:
        for off, ln in enumerate(code.split("\n")):
            line = start + off
            if ln.lstrip().startswith("#"):
                continue
            for kind, seed_re in SEEDS.items():
                if seed_re.search(ln):
                    last_seed[kind] = line
            for kind, call_re in RANDOM_CALLS:
                m = call_re.search(ln)
                if not m:
                    continue
                if kind in NO_SEED_NAMES and m.groups()[-1] in NO_SEED_NAMES[kind]:
                    continue
                if last_seed.get(kind, float("inf")) > line:
                    out.append((line, m.group(0), SEED_HINT[kind]))
    return out


def run_violations(path, blocks=None):
    """把每个块放进两个新子进程各跑一次;返回 [(block_no, msg)] 违规。"""
    blocks = list(_python_blocks(path)) if blocks is None else blocks
    out = []
    for n, (_, _, code) in enumerate(blocks, 1):
        if code.lstrip().startswith("# skip"):
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp = f.name
        env = dict(os.environ, PYTHONHASHSEED="0")
        try:
            results = []
            for _ in range(2):
                try:
                    r = subprocess.run([sys.executable, tmp], capture_output=True,
                                       text=True, timeout=60, env=env)
                    results.append((r.returncode, r.stdout))
                except subprocess.TimeoutExpired:
                    out.append((n, "block %d: 运行超时(>60 秒)" % n))
                    break
            if len(results) == 2:
                if results[0] != results[1]:
                    out.append((n, "block %d: 两次运行输出不同(exit %s / %s)"
                                % (n, results[0][0], results[1][0])))
                elif results[0][0] != 0:
                    out.append((n, "block %d: 运行失败(exit %s,依赖前面块定义的块不能单独 --run)"
                                % (n, results[0][0])))
        finally:
            Path(tmp).unlink(missing_ok=True)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="可复现性检查(references/reproducibility.md)")
    parser.add_argument("files", nargs="+", help="Markdown 章节文件")
    parser.add_argument("--run", action="store_true",
                        help="把每个块放进新进程各运行两次,比较输出(每块超时 60 秒)")
    args = parser.parse_args(argv)

    total = 0
    for f in args.files:
        print(f"== {f} ==")
        if not Path(f).is_file():
            print(f"{f}:1: 文件不存在或无法读取")
            total += 1
            continue
        blocks = list(_python_blocks(f))
        for line, call, hint in seed_violations(f, blocks):
            print(f"{f}:{line}: 随机调用 {call!r} 之前没有 {hint} 种子;细则见 references/reproducibility.md")
            total += 1
        for _, msg in run_violations(f, blocks) if args.run else []:
            print(f"{f}: {msg}")
            total += 1
        print()
    print(f"共 {total} 处违规" if total else "OK: 全部通过")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())