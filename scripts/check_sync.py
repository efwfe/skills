#!/usr/bin/env python3
"""检查各 skill 里应当一致的共用文件(目前是 references/learning-lens.md)是否同步。

用法:python3 scripts/check_sync.py     不一致时退出码 1,并列出与第一份不同的文件。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ["references/learning-lens.md"]


def main():
    bad = 0
    for rel in SHARED:
        copies = sorted(ROOT.glob(f"skills/*/{rel}"))
        if len(copies) < 2:
            continue
        ref = copies[0].read_bytes()
        diff = [c for c in copies[1:] if c.read_bytes() != ref]
        for c in diff:
            print(f"不一致:{c.relative_to(ROOT)} 与 {copies[0].relative_to(ROOT)}")
        bad += len(diff)
        if not diff:
            print(f"一致:{rel}({len(copies)} 份)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
