#!/usr/bin/env python3
"""把 dot 库(以及额外的笔记目录)解析成一张学习关系图。

用法:
  uv run python learning_graph.py [dot库目录] [--extra 目录 ...] [--out graph.html]
                                  [--json graph.json] [--report] [--no-html]

dot 库目录按此顺序确定:参数 → 环境变量 DOT_LIBRARY → ~/dot-library。

节点(按所在目录与文件名推断类型):
  dots/        → dot        已确认的 dot
  candidates/  → candidate  候选 dot
  archive/     → archived   归档的 dot
  projects/    → project    分析过的仓库;文件名 blog-* → blog,course-* → course
  --extra 目录 → note       其他笔记(如 Obsidian 库)
  只被 [[链接]] 引用、没有文件的名字 → ghost(悬挂链接)
index.md / changelog.md / tensions.md 不是节点;tensions.md 里同一行出现的 [[a]] [[b]] 记为张力。

边(按 [[链接]] 所在的小节与行首推断类型):
  "例证" / "本项目涉及的 dot" 小节   → 例证
  "连接" 小节里以 同源异形/张力/依赖/传承 开头的行 → 对应类型
  其他位置                            → 关联
dot→项目的"例证"与项目→dot 的"本项目涉及的 dot"是同一条关系,合并成一条边。

零第三方依赖。
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "templates" / "graph.html"

LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
FIELD = re.compile(r"^\s*-\s*(状态|完整度|例证数|首次记录|最后更新|链接|来源|类型|分析日期|日期|产物)\s*[:：]\s*(.*)$")
ONE_LINER = re.compile(r"^>\s*一句话[^:：]*[:：]\s*(.*)$")
IMPL_LINE = re.compile(r"\*\*实现面\*\*")
PATH_LINE = re.compile(r"`[^`\s]+:\d+")
RELATIONS = ("同源异形", "张力", "依赖", "传承")
DIRECTED = {"依赖", "传承"}
META_FILES = {"index", "changelog", "tensions", "readme"}
KIND_BY_DIR = {"dots": "dot", "candidates": "candidate", "archive": "archived", "projects": "project"}


def resolve_library(arg):
    if arg:
        return Path(arg).expanduser()
    if os.environ.get("DOT_LIBRARY"):
        return Path(os.environ["DOT_LIBRARY"]).expanduser()
    return Path("~/dot-library").expanduser()


def _kind(path, root, extra_roots):
    if any(_is_under(path, r) for r in extra_roots):
        return "note"
    top = path.relative_to(root).parts[0] if len(path.relative_to(root).parts) > 1 else ""
    kind = KIND_BY_DIR.get(top, "note")
    if kind == "project":
        if path.stem.startswith("blog-"):
            return "blog"
        if path.stem.startswith("course-"):
            return "course"
    return kind


def _is_under(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _edge_type(section, line):
    body = re.sub(r"^\s*[-*\d.]+\s*", "", line).lstrip("*")
    if "连接" in section:
        for rel in RELATIONS:
            if body.startswith(rel):
                return rel
    if "例证" in section or "涉及的 dot" in section:
        return "例证"
    for rel in RELATIONS:
        if body.startswith(rel + "：") or body.startswith(rel + ":"):
            return rel
    return "关联"


def parse_note(path):
    """Return (meta, links): meta 是字段字典,links 是 [(目标名, 边类型)]."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    meta = {"title": path.stem, "excerpt": "", "has_impl_path": None}
    links, section = [], ""
    body_lines = []
    for line in text.splitlines():
        h = HEADING.match(line)
        if h:
            if len(h.group(1)) == 1 and meta["title"] == path.stem:
                meta["title"] = h.group(2).strip()
            section = h.group(2).strip()
            continue
        m = FIELD.match(line)
        if m and m.group(2).strip():
            meta[m.group(1)] = m.group(2).strip()
        m = ONE_LINER.match(line)
        if m and m.group(1).strip():
            meta["one_liner"] = m.group(1).strip()
        if IMPL_LINE.search(line):
            meta["has_impl_path"] = bool(PATH_LINE.search(line.split("实现面", 1)[1]))
        if section in ("核心赌注",) and line.strip().startswith("- 一句话") and "one_liner" not in meta:
            val = re.split(r"[:：]", line, maxsplit=1)[-1].strip()
            if val:
                meta["one_liner"] = val
        for target in LINK.findall(line):
            links.append((target.strip(), _edge_type(section, line)))
        if line.strip():
            body_lines.append(line)
    meta["excerpt"] = "\n".join(body_lines)[:900]
    return meta, links


def build_graph(root, extra_roots=()):
    root = Path(root)
    extra_roots = [Path(r).expanduser() for r in extra_roots]
    files = []
    for base in [root, *extra_roots]:
        if base.is_dir():
            files += [p for p in sorted(base.rglob("*.md"))
                      if not any(part.startswith(".") for part in p.relative_to(base).parts)]
    nodes, raw_links = {}, []
    tension_lines = []
    for p in files:
        name = p.stem
        if name.lower() in META_FILES and p.parent in (root, *extra_roots):
            if name == "tensions":
                tension_lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            continue
        if name in nodes:  # 全库文件名唯一;重名时保留先遇到的,并记一条问题
            nodes[name].setdefault("flags", []).append("重名")
            continue
        meta, links = parse_note(p)
        base = next((b for b in [root, *extra_roots] if _is_under(p, b)), root)
        nodes[name] = {
            "id": name,
            "kind": _kind(p, root, extra_roots),
            "path": str(p.relative_to(base)) if base == root else str(p),
            **meta,
        }
        raw_links += [(name, t, typ) for t, typ in links]
    for line in tension_lines:
        names = [t.strip() for t in LINK.findall(line)]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                raw_links.append((names[i], names[j], "张力"))

    edges = {}
    for src, dst, typ in raw_links:
        if dst.lower() in META_FILES or src == dst:
            continue
        if dst not in nodes:
            nodes[dst] = {"id": dst, "kind": "ghost", "title": dst, "path": "", "excerpt": ""}
        if typ in DIRECTED:
            key = (src, dst, typ)
        else:
            key = (*sorted((src, dst)), typ)
        e = edges.setdefault(key, {"source": key[0], "target": key[1], "type": typ, "count": 0})
        e["count"] += 1
    # 同一对节点若已有具体关系,去掉多余的"关联"
    typed_pairs = {frozenset((e["source"], e["target"])) for e in edges.values() if e["type"] != "关联"}
    edge_list = [e for e in edges.values()
                 if e["type"] != "关联" or frozenset((e["source"], e["target"])) not in typed_pairs]
    _annotate(nodes, edge_list)
    return {"nodes": list(nodes.values()), "edges": edge_list,
            "library": str(root), "generated": date.today().isoformat()}


def _annotate(nodes, edges):
    deg = defaultdict(int)
    examples = defaultdict(int)
    for e in edges:
        deg[e["source"]] += 1
        deg[e["target"]] += 1
        if e["type"] == "例证":
            for a, b in ((e["source"], e["target"]), (e["target"], e["source"])):
                if nodes[a]["kind"] in ("dot", "candidate", "archived") and nodes[b]["kind"] in ("project", "blog", "course"):
                    examples[a] += 1
    for n in nodes.values():
        n["degree"] = deg[n["id"]]
        flags = n.setdefault("flags", [])
        if n["kind"] in ("dot", "candidate", "archived"):
            n["examples"] = examples[n["id"]]
        if n["degree"] == 0:
            flags.append("孤立")
        if n["kind"] == "ghost":
            flags.append("悬挂链接")
        if n["kind"] in ("dot", "candidate"):
            if n.get("完整度", "").startswith("半"):
                flags.append("半个")
            if n.get("has_impl_path") is False:
                flags.append("没落到代码")
            if n["kind"] == "candidate" and examples[n["id"]] >= 2:
                flags.append("可升级")
            if n["kind"] == "dot" and n["degree"] - examples[n["id"]] == 0:
                flags.append("没有连接")


def components(graph):
    adj = defaultdict(set)
    for e in graph["edges"]:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    seen, comps = set(), []
    for n in graph["nodes"]:
        if n["id"] in seen:
            continue
        stack, comp = [n["id"]], []
        seen.add(n["id"])
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(sorted(comp))
    return sorted(comps, key=len, reverse=True)


KIND_LABEL = {"dot": "dot", "candidate": "候选", "archived": "归档", "project": "项目",
              "blog": "文章", "course": "课程", "note": "笔记", "ghost": "悬挂"}
FLAG_HINT = {
    "可升级": "候选已有 ≥2 个例证:用 /scratch:dots 走同源判断,确认后升级",
    "半个": "缺体验面/设计面/实现面中的一面:下次分析时专门留意",
    "没落到代码": "实现面没有 path:line:只停在思想层,下次追到代码",
    "没有连接": "已确认的 dot 却和其他 dot 没有任何关系:想想它和谁同源、和谁拉扯",
    "孤立": "没有任何链接",
    "悬挂链接": "被 [[链接]] 引用但没有文件:建文件,或改正拼写",
    "重名": "全库文件名应唯一,[[链接]] 才不会指错",
}


def report(graph):
    by_kind = defaultdict(list)
    for n in graph["nodes"]:
        by_kind[n["kind"]].append(n["id"])
    by_type = defaultdict(int)
    for e in graph["edges"]:
        by_type[e["type"]] += 1
    out = [f"# 学习关系图报告({graph['library']},{graph['generated']})", ""]
    out.append("节点:" + ",".join(f"{KIND_LABEL.get(k, k)} {len(v)}" for k, v in sorted(by_kind.items())))
    out.append("边:" + (",".join(f"{t} {c}" for t, c in sorted(by_type.items())) or "无"))
    comps = components(graph)
    out.append(f"连通块:{len(comps)} 个(最大的含 {len(comps[0]) if comps else 0} 个节点)")
    out.append("")
    hubs = sorted((n for n in graph["nodes"] if n["kind"] in ("dot", "candidate")),
                  key=lambda n: (-n["degree"], n["id"]))[:5]
    if hubs:
        out.append("## 枢纽(连接最多的 dot)")
        out += [f"- [[{n['id']}]] 连接 {n['degree']},例证 {n.get('examples', 0)}" for n in hubs if n["degree"]]
        out.append("")
    for flag, hint in FLAG_HINT.items():
        hit = [n for n in graph["nodes"] if flag in n.get("flags", [])]
        if hit:
            out.append(f"## {flag}({len(hit)}):{hint}")
            out += [f"- [[{n['id']}]]({KIND_LABEL.get(n['kind'], n['kind'])})" for n in hit[:20]]
            if len(hit) > 20:
                out.append(f"- …… 另有 {len(hit) - 20} 个")
            out.append("")
    small = [c for c in comps[1:] if 1 < len(c) <= 4]
    if small:
        out.append(f"## 孤岛({len(small)}):和主体没有连上的小团,想想它们和主体是什么关系")
        out += ["- " + "、".join(f"[[{x}]]" for x in c) for c in small[:10]]
        out.append("")
    tensions = [e for e in graph["edges"] if e["type"] == "张力"]
    if tensions:
        out.append(f"## 张力({len(tensions)})")
        out += [f"- [[{e['source']}]] × [[{e['target']}]]" for e in tensions[:10]]
        out.append("")
    if not graph["nodes"]:
        out.append("库是空的:先用 /scratch:dots 分析一个项目。")
    return "\n".join(out).rstrip() + "\n"


def render_html(graph, template=TEMPLATE):
    data = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    return Path(template).read_text(encoding="utf-8").replace("/*__GRAPH_DATA__*/null", data)


def main(argv=None):
    ap = argparse.ArgumentParser(description="把 dot 库解析成学习关系图(HTML / JSON / 文字报告)")
    ap.add_argument("library", nargs="?", help="dot 库目录(默认 $DOT_LIBRARY 或 ~/dot-library)")
    ap.add_argument("--extra", action="append", default=[], help="额外扫描的笔记目录,可多次给出")
    ap.add_argument("--out", help="HTML 输出路径(默认 <dot库>/graph.html)")
    ap.add_argument("--json", help="同时写出图数据 JSON")
    ap.add_argument("--report", action="store_true", help="打印文字报告(孤立、悬挂、可升级……)")
    ap.add_argument("--no-html", action="store_true", help="不写 HTML")
    args = ap.parse_args(argv)

    root = resolve_library(args.library)
    if not root.is_dir():
        print(f"找不到 dot 库目录:{root}(用参数或环境变量 DOT_LIBRARY 指定)", file=sys.stderr)
        return 2
    graph = build_graph(root, args.extra)
    if args.json:
        Path(args.json).write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"JSON:{args.json}")
    if not args.no_html:
        out = Path(args.out).expanduser() if args.out else root / "graph.html"
        out.write_text(render_html(graph), encoding="utf-8")
        print(f"HTML:{out}({len(graph['nodes'])} 个节点,{len(graph['edges'])} 条边)")
    if args.report:
        print(report(graph))
    return 0


if __name__ == "__main__":
    sys.exit(main())
