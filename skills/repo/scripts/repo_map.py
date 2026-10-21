#!/usr/bin/env python3
"""Map a repo for a from-scratch curriculum: size, entry points, import layers.

Usage: uv run python repo_map.py <repo_dir> [--max-files 400]

Layer 0 = files that import nothing from the repo (leaves, learn first when
building bottom-up). Higher layers depend on lower ones. Cycles are reported.
Python uses ast; JS/TS/Go/Rust use regex (approximate).
"""
import argparse, ast, re, sys
from collections import defaultdict
from pathlib import Path

SKIP = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "target", "vendor", ".tox"}
EXT = {".py": "py", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".go": "go", ".rs": "rs"}
JS_IMP = re.compile(r"""(?:from|require\()\s*['"](\.[^'"]*)['"]""")
GO_IMP = re.compile(r'^\s*(?:import\s+)?(?:\w+\s+)?"([^"]+)"', re.M)
RS_IMP = re.compile(r"^\s*(?:pub\s+)?(?:mod|use\s+crate::)(\w+)", re.M)
ENTRY = re.compile(r"^(main|cli|app|server|train|run|sample|index|__main__)\.\w+$|^manage\.py$")


def collect(root, max_files):
    files = []
    for p in sorted(root.rglob("*")):
        if p.suffix in EXT and p.is_file() and not (set(p.relative_to(root).parts) & SKIP):
            files.append(p)
    return files[:max_files]


def py_imports(path, root, modules):
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except SyntaxError:
        return set()
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module is not None:
            base = "." * n.level + n.module if n.level else n.module
            names.add(base)
            names |= {f"{base}.{a.name}" for a in n.names}
    deps = set()
    for name in names:
        key = name.lstrip(".")
        while key:
            if key in modules and modules[key] != path:
                deps.add(modules[key]); break
            key = key.rpartition(".")[0]
    return deps


def other_imports(path, root, kind, by_stem):
    text = path.read_text(errors="ignore")
    rx = {"js": JS_IMP, "go": GO_IMP, "rs": RS_IMP}[kind]
    deps = set()
    for m in rx.findall(text):
        stem = m.rstrip("/").split("/")[-1].split(".")[0]
        for q in by_stem.get(stem, []):
            if q != path:
                deps.add(q)
    return deps


def layers(graph):
    level, remaining = {}, set(graph)
    while remaining:
        ready = {n for n in remaining if all(d in level for d in graph[n] if d in graph)}
        if not ready:
            return level, remaining  # cycle
        for n in ready:
            level[n] = 1 + max((level[d] for d in graph[n] if d in graph), default=-1)
        remaining -= ready
    return level, set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo"); ap.add_argument("--max-files", type=int, default=400)
    a = ap.parse_args()
    root = Path(a.repo).resolve()
    files = collect(root, a.max_files)
    if not files:
        sys.exit("no source files found")
    loc = {f: sum(1 for _ in f.open(errors="ignore")) for f in files}
    modules = {".".join(f.relative_to(root).with_suffix("").parts).removesuffix(".__init__"): f for f in files if f.suffix == ".py"}
    by_stem = defaultdict(list)
    for f in files:
        by_stem[f.stem].append(f)
    graph = {f: (py_imports(f, root, modules) if f.suffix == ".py" else other_imports(f, root, EXT[f.suffix], by_stem)) for f in files}
    level, cyc = layers(graph)
    fan_in = defaultdict(int)
    for deps in graph.values():
        for d in deps:
            fan_in[d] += 1

    rel = lambda f: str(f.relative_to(root))
    print(f"# {root.name}: {len(files)} files, {sum(loc.values())} LOC\n")
    print("## Entry points")
    for f in files:
        if ENTRY.match(f.name) or (f.suffix == ".py" and "__main__" in f.read_text(errors="ignore")):
            print(f"- {rel(f)} ({loc[f]} LOC)")
    print("\n## Core candidates (most imported)")
    for f, n in sorted(fan_in.items(), key=lambda x: -x[1])[:8]:
        print(f"- {rel(f)}  imported by {n}, {loc[f]} LOC")
    print("\n## Largest files")
    for f, n in sorted(loc.items(), key=lambda x: -x[1])[:8]:
        print(f"- {rel(f)}  {n} LOC")
    print("\n## Import layers (0 = leaf; learn bottom-up, but teach top-down skeleton first)")
    by_level = defaultdict(list)
    for f, l in level.items():
        by_level[l].append(f)
    for l in sorted(by_level):
        print(f"- L{l}: " + ", ".join(f"{rel(f)}({loc[f]})" for f in sorted(by_level[l])[:12]) + (" ..." if len(by_level[l]) > 12 else ""))
    if cyc:
        print("\n## Import cycles (break these when teaching)\n- " + ", ".join(rel(f) for f in sorted(cyc)))


if __name__ == "__main__":
    main()
