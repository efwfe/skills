#!/usr/bin/env python3
"""Check every Markdown image link resolves to an existing file.

Usage: uv run python check_images.py <md...>

Relative paths are resolved against the directory of the Markdown file
itself (CommonMark behavior), which is how the book's convention works:
chapters live in <course>/chapters/, figures in <course>/figures/, so a
link reads ![alt](../figures/figN-k.png) regardless of which subfolder
(drafts/, chapters/, specs/) the .md sits in.

Absolute paths and http(s)/data: URLs are skipped. Prints one line per
missing image; exit code 1 if anything is missing, 0 otherwise.
"""
import argparse
import re
import sys
from pathlib import Path

IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
WEB = ("http://", "https://", "data:")


def check(md):
    """Return (total, [(alt, ref, resolved)]) for images in one md file."""
    base = Path(md).resolve().parent
    total, missing = 0, []
    for alt, ref in IMG.findall(Path(md).read_text(encoding="utf-8", errors="ignore")):
        total += 1
        if ref.startswith(WEB):
            continue
        target = (base / ref.split("#", 1)[0].split("?", 1)[0]).resolve()
        if not target.is_file():
            missing.append((alt.strip(), ref, target))
    return total, missing


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Report Markdown image links that do not resolve to files.")
    parser.add_argument("files", nargs="+", help="Markdown files to check")
    args = parser.parse_args(argv)

    missing_total = 0
    for md in args.files:
        total, missing = check(md)
        for alt, ref, target in missing:
            print(f"{md}: missing image ![{alt}]({ref}) -> {target}")
        missing_total += len(missing)
        if missing:
            print(f"{md}: {len(missing)}/{total} images missing")
        else:
            print(f"{md}: {total} image(s) ok")
    if missing_total:
        print(f"FAILED: {missing_total} missing image(s)")
        return 1
    print("OK: all image links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())