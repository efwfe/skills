#!/usr/bin/env python3
"""Execute every ```python block of a chapter in one shared namespace (notebook style).

Usage: uv run python verify_listings.py ch01.md [ch02.md ...] [--fill]

Several files run in order in ONE shared namespace, so later chapters can reuse the
classes defined by earlier ones (the book builds up cumulatively).

Fails (exit 1) on the first exception, naming the block. With --fill, each block
that has no following ```text block gets its REAL stdout inserted. Prose must never
quote output that was not produced by this script.
Blocks starting with `# skip` are not executed.
"""
import contextlib, io, re, sys, traceback

FENCE = re.compile(r"```python\n(.*?)```(\n\n```text\n.*?```)?", re.S)


def run_file(path, ns, fill):
    src = open(path).read()
    out_parts, last, n = [], 0, 0
    for m in FENCE.finditer(src):
        code, existing = m.group(1), m.group(2)
        n += 1
        out_parts.append(src[last:m.start()])
        block = f"```python\n{code}```"
        if code.lstrip().startswith("# skip"):
            out_parts.append(block + (existing or ""))
            last = m.end(); continue
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(code, f"{path}#block{n}", "exec"), ns)
        except Exception:
            print(f"FAIL {path} block {n}:\n{code}\n{traceback.format_exc()}", file=sys.stderr)
            sys.exit(1)
        out = buf.getvalue().rstrip()
        if existing:
            block += existing
        elif fill and out:
            block += f"\n\n```text\n{out}\n```"
        out_parts.append(block)
        last = m.end()
    out_parts.append(src[last:])
    print(f"ok: {path}: {n} python blocks executed")
    if fill:
        open(path, "w").write("".join(out_parts))


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    fill = "--fill" in sys.argv
    ns = {"__name__": "__main__"}
    for p in paths:
        run_file(p, ns, fill)


if __name__ == "__main__":
    main()
