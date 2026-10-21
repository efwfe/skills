#!/usr/bin/env python3
"""Fill {{CODE:id}} markers in an LLM-written chapter with real code from a lab file.

Usage: uv run python assemble_chapter.py labs/ch03.py draft.md -o chapters/ch03.md

A lab file is plain Python split into blocks by lines `# %% id`. The LLM writes prose only and
refers to code by id; this script inserts the code verbatim, so the model can never alter or
invent code. Unused or unknown ids are errors (exit 1).
"""
import argparse, re, sys


def blocks(lab):
    parts = re.split(r"^# %% (\S+)\n", open(lab).read(), flags=re.M)
    return {parts[i]: parts[i + 1].strip("\n") for i in range(1, len(parts), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lab"); ap.add_argument("draft"); ap.add_argument("-o", required=True)
    a = ap.parse_args()
    code, text = blocks(a.lab), open(a.draft).read()
    used = re.findall(r"\{\{CODE:(\S+?)\}\}", text)
    bad = [u for u in used if u not in code]
    unused = [k for k in code if k not in used]
    if bad or unused:
        sys.exit(f"unknown ids: {bad}; unused ids: {unused}")
    text = re.sub(r"\{\{CODE:(\S+?)\}\}", lambda m: f"```python\n{code[m.group(1)]}\n```", text)
    open(a.o, "w").write(text)
    print(f"assembled {len(used)} blocks -> {a.o}")


if __name__ == "__main__":
    main()
