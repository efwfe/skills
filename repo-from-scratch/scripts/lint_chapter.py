#!/usr/bin/env python3
"""章节规范检查:违规分两级输出——[错误]与[提醒]。

用法:uv run python lint_chapter.py <md...> [--strict]
默认只有[错误]计入退出码(1),[提醒]只打印;加 --strict 后两类都计入。
输出按文件分组,每条违规带 [错误]/[提醒] 前缀、行号与一句说明,
最后一行给两类各自的计数。

规则(全部来自 references/writing-style.md 与 templates/chapter.md):
[错误]
  1. 图片链接按该 md 所在目录解析,必须存在(复用 check_images.py 的解析逻辑);
  2. 必备小节:前置知识、诚实边界、局限、练习(练习下要有"答案要点");
     脉络必备项(两种模式都要):脉络条、路线图图片、承接的缺口、留下的缺口;
     --mode baby 时"小节"必备项变为:心智模型、与真实实现的差距、诚实边界、练习;
[提醒]
  3. ```python 代码块 ≤ 15 行(不计输出块);
  4. 正文行内不出现"未验证/没验证/我没/我们没有运行/没有运行"
     (只在"诚实边界"框内允许);
  5. 正文不出现元文字:Raschka、写作流程、"这对应";
  6. 同目录存在 glossary.md 时,每个术语在被正文使用之前,
     先由该章的"本章新术语"框列出(简易版:按子串匹配);
  7. 代码块里随机调用之前要有对应 seed(torch.manual_seed /
     np.random.seed / random.seed),逻辑复用 check_repro.py(导入,不复制):
     细则见 references/reproducibility.md。
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_images  # 复用图片可解析性检查,不复制解析逻辑
import check_repro  # 复用随机调用前必须有种子的静态检查,不复制逻辑

MAX_LINES = 15
DISCLAIM = re.compile(r"未验证|没验证|我没|我们没有运行|没有运行")
META = re.compile(r"Raschka|写作流程|这对应")
REQUIRED = ("前置知识", "诚实边界", "局限", "练习")
REQUIRED_BABY = ("心智模型", "与真实实现的差距", "诚实边界", "练习")
CRUMBS = (
    (re.compile(r"\*\*脉络条\*\*"), "脉络条(章首一行:`Stage N › 组件 › 子组件`,模板 templates/chapter.md)"),
    (re.compile(r"\*\*承接的缺口\*\*"), "承接的缺口(第一章节前说明上一节点把什么留给我们,模板 templates/chapter.md)"),
    (re.compile(r"\*\*留下的缺口\*\*"), "留下的缺口(小结前说明把什么留给下一节点,模板 templates/chapter.md)"),
)
FENCE = re.compile(r"^```")
HONEST_BOX = re.compile(r"^>\s*\*\*诚实边界\*\*")
NEW_TERMS_BOX = re.compile(r"^>\s*\*\*本章新术语\*\*")
PY_BLOCK = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.S)


def _line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def _parse_glossary(glossary_path):
    """Return term names from the first column of the glossary table."""
    terms = []
    for ln in Path(glossary_path).read_text(encoding="utf-8").split("\n"):
        s = ln.strip()
        if not s.startswith("|") or re.match(r"^\|[\s:|-]+\|", s):
            continue
        cell = ln.split("|")[1].replace("**", "").strip().strip("`").strip()
        if cell and cell != "术语":
            terms.append(cell)
    return terms


def _find_boxes(lines):
    """Return (honest_boxes, terms_boxes) as lists of (start_line, end_line)."""
    honest, terms = [], []
    for i, ln in enumerate(lines, 1):
        if HONEST_BOX.match(ln):
            j = i
            while j + 1 <= len(lines) and lines[j].startswith(">"):
                j += 1
            honest.append((i, j))
        if NEW_TERMS_BOX.match(ln):
            j = i
            while j + 1 <= len(lines) and lines[j].startswith(">"):
                j += 1
            terms.append((i, j))
    return honest, terms


def _in_any(line, boxes):
    return any(a <= line <= b for a, b in boxes)


def _prose_lines(lines, honest_boxes, terms_boxes):
    """Yield (lineno, text) of readable prose: no fences, no box bodies."""
    in_fence = False
    for i, ln in enumerate(lines, 1):
        if FENCE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _in_any(i, honest_boxes) or _in_any(i, terms_boxes):
            continue
        yield i, ln


def _kind(path):
    """chapter | appendix | glossary | map -- non-chapter files skip chapter-only checks."""
    name = Path(path).name
    if name == "glossary.md":
        return "glossary"
    if name.startswith("00-"):
        return "map"
    if name.startswith("appendix-"):
        return "appendix"
    return "chapter"


def lint_file(path, mode="standard"):
    """Return (errors, warnings), each a sorted list of (line, msg)."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.split("\n")
    errors, warns = [], []
    kind = _kind(path)
    required = REQUIRED_BABY if mode == "baby" else REQUIRED
    if kind in ("appendix", "glossary", "map"):
        required = ()

    # 1 [错误] 图片可解析(复用 check_images.py 的逻辑)
    _, missing = check_images.check(str(path))
    for alt, ref, target in missing:
        pos = text.find(f"]({ref})")
        errors.append((_line_of(text, pos) if pos >= 0 else 1,
                       f"图片 ![{alt}]({ref}) 不存在(按本文件所在目录解析到 {target})"))

    # 2 [提醒] 代码块长度
    for m in PY_BLOCK.finditer(text):
        n = len(m.group(1).rstrip("\n").split("\n"))
        if n > MAX_LINES:
            warns.append((_line_of(text, m.start()),
                          f"python 代码块 {n} 行,超过 {MAX_LINES} 行上限;拆成 ≤15 行、带形状打印的小步"))

    # 3/4 [提醒] 免责词与元文字(只查正文;代码块与"诚实边界"框除外)
    honest_boxes, terms_boxes = _find_boxes(lines)
    for i, ln in _prose_lines(lines, honest_boxes, terms_boxes):
        for m in DISCLAIM.finditer(ln):
            warns.append((i, f'正文出现行内免责"{m.group(0)}";边界只允许写在"诚实边界"框内'))
        for m in META.finditer(ln):
            warns.append((i, f'正文出现元文字"{m.group(0)}";不写 Raschka、写作流程、"这对应…的思路"'))

    # 5 [错误] 必备小节(模式决定清单)
    found = {}
    for name in required:
        m = re.search(r"^#{1,6}[ \t]*" + re.escape(name), text, re.M)
        if not m:
            m = re.search(r"^>[ \t]*\*\*" + re.escape(name) + r"\*\*", text, re.M)
        if m:
            found[name] = (_line_of(text, m.start()), m.end())
    for name in required:
        if name not in found:
            errors.append((len(lines), f"缺必备小节:{name}(模板见 templates/chapter.md)"))
    if kind == "appendix" and ("练习" not in text or "答案要点" not in text):
        errors.append((len(lines), "附录缺练习或答案要点(每节末一道\"先预测再运行\"小题,附答案要点)"))
    if "练习" in found and text.find("答案要点", found["练习"][1]) < 0:
        errors.append((found["练习"][0], '"练习"小节之后缺"答案要点"'))

    # 5b [错误] 脉络必备项(两种模式都要:pipeline 检查,PLAN P3c)
    if kind == "chapter":
        for probe, msg in CRUMBS:
            if not probe.search(text):
                errors.append((len(lines), f"缺必备项:{msg}"))
        if not any("roadmap" in ref or "路线图" in alt for alt, ref in check_images.IMG.findall(text)):
            errors.append((len(lines), "缺必备项:路线图图片(章首一张、alt 含\"路线图\"或文件名含 roadmap、当前章高亮,两级路线图见 references/figures.md)"))

    # 6 [提醒] 术语表(简易版):术语在被正文使用前,应先被"本章新术语"框列出
    glossary = path.resolve().parent / "glossary.md"
    if glossary.is_file() and kind == "chapter":
        terms = _parse_glossary(glossary)
        box_text = "\n".join("\n".join(lines[a - 1:b]) for a, b in terms_boxes)
        box_line = min((a for a, _ in terms_boxes), default=None)
        for term in terms:
            if len(term) < 2:
                continue
            for i, ln in _prose_lines(lines, honest_boxes, terms_boxes):
                if ln.lstrip().startswith("#"):
                    continue
                if term in ln:
                    if box_line is None:
                        warns.append((i, f'术语"{term}"在第 {i} 行首次出现,但本章没有"本章新术语"框列出它(来源 glossary.md)'))
                    elif box_line > i:
                        warns.append((i, f'术语"{term}"在第 {i} 行首次出现,但"本章新术语"框在第 {box_line} 行才出现(来源 glossary.md)'))
                    elif term not in box_text:
                        warns.append((i, f'术语"{term}"在第 {i} 行首次出现,但"本章新术语"框未列出它(来源 glossary.md)'))
                    break

    # 7 [提醒] 随机调用前要有种子(复用 check_repro.py 的静态检查)
    for line, call, hint in check_repro.seed_violations(str(path)):
        warns.append((line, f'随机调用 "{call}" 之前没有 {hint} 种子(细则见 references/reproducibility.md)'))
    return sorted(errors), sorted(warns)


def main(argv=None):
    parser = argparse.ArgumentParser(description="章节规范检查(references/writing-style.md 的默认做法,分[错误]/[提醒]两级)")
    parser.add_argument("files", nargs="+", help="Markdown 章节文件")
    parser.add_argument("--mode", choices=("standard", "baby"), default="standard",
                        help="baby 模式的必备小节:心智模型、与真实实现的差距、诚实边界、练习")
    parser.add_argument("--strict", action="store_true", help="提醒也计入退出码(默认只打印)")
    args = parser.parse_args(argv)

    err_total = warn_total = 0
    for f in args.files:
        p = Path(f)
        print(f"== {f} ==")
        if not p.is_file():
            print(f"{f}:1: [错误] 文件不存在或无法读取")
            err_total += 1
            print()
            continue
        errors, warns = lint_file(p, args.mode)
        for line, msg in errors:
            print(f"{f}:{line}: [错误] {msg}")
            err_total += 1
        for line, msg in warns:
            print(f"{f}:{line}: [提醒] {msg}")
            warn_total += 1
        print()
    total = err_total + warn_total
    print(f"共 {total} 条违规(错误 {err_total},提醒 {warn_total})")
    if args.strict:
        return 1 if total else 0
    return 1 if err_total else 0


if __name__ == "__main__":
    sys.exit(main())