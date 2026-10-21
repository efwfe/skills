#!/usr/bin/env python3
"""把 blog-from-scratch 的 Markdown 成品打包成排版好的单文件 HTML。

用法: uv run --with markdown python build_html.py article.md [-o out.html]

约定(写作时用):
- 提示块:  > [!fail] / [!new] / [!example] / [!gap] / [!model] / [!supp]  后面接正文
- 重画的图: ![图注一句话结论](figures/fig3.svg "原图链接(可选)")  → 内联 SVG,套主题色,加图注
- 沿用原图: ![图注一句话结论](https://…/x.png)  或本地路径 → 带图注的图框;加 --embed-images 则把图下载并内嵌,HTML 自包含
- 其余照常 Markdown(表格、代码块、<details> 都可用)
"""
import argparse, base64, html, mimetypes, re, sys, urllib.request
from pathlib import Path
import markdown

KINDS = {"fail": "先失败", "new": "新东西", "example": "小例子", "gap": "留下缺口",
         "model": "心智模型", "supp": "补充"}
ZOOM = ('<div id="zoom" style="display:none;position:fixed;inset:0;z-index:9;background:rgba(0,0,0,.82);overflow:auto;cursor:zoom-out;padding:24px"></div>'
        '<script>document.querySelectorAll("figure.photo img").forEach(function(i){i.style.cursor="zoom-in";i.onclick=function(){var z=document.getElementById("zoom");'
        'z.innerHTML="";var c=i.cloneNode();c.style.cssText="display:block;margin:0 auto;max-width:none;width:min(1600px,100%);background:#fff";z.appendChild(c);z.style.display="block"};});'
        'document.getElementById("zoom").onclick=function(){this.style.display="none"};</script>')
DEFS = ('<svg width="0" height="0" style="position:absolute"><defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="context-stroke" '
        'style="fill:var(--fg)"/></marker></defs></svg>')


def load_bytes(src: str, base: Path):
    if re.match(r"https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read(), r.headers.get_content_type()
    p = base / src
    if not p.exists():
        sys.exit(f"找不到图文件: {p}")
    return p.read_bytes(), mimetypes.guess_type(p.name)[0] or "image/png"


def inline_figures(md: str, base: Path, embed: bool) -> str:
    def repl(m):
        alt, src, title = m.group(1), m.group(2), m.group(3)
        link = f' <a href="{html.escape(title)}" target="_blank" rel="noopener">原图 ↗</a>' if title else ""
        if src.endswith(".svg") and not src.startswith("http"):
            p = base / src
            if not p.exists():
                sys.exit(f"找不到图文件: {p}")
            svg = re.sub(r"<\?xml.*?\?>|<!DOCTYPE.*?>", "", p.read_text(encoding="utf-8"), flags=re.S).strip()
            svg = re.sub(r"\n\s*\n", "\n", svg)  # 空行会打断 Markdown 的 HTML 块
            return f'\n<figure>\n{svg}\n<figcaption>{html.escape(alt)}{link}</figcaption>\n</figure>\n'
        # 位图(沿用原图):可内嵌为 data URI
        url = src
        if embed:
            data, mime = load_bytes(src, base)
            url = f"data:{mime};base64,{base64.b64encode(data).decode()}"
        if re.match(r"https?://", src) and not title:
            link = f' <a href="{html.escape(src)}" target="_blank" rel="noopener">原图 ↗</a>'
        return (f'\n<figure class="photo"><img src="{url}" alt="{html.escape(alt)}" loading="lazy">'
                f'<figcaption>{html.escape(alt)}{link}</figcaption></figure>\n')
    return re.sub(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)', repl, md)


def split_callouts(md: str) -> str:
    """相邻的 > 引用块会被 Markdown 合并;在每个 `> [!kind]` 前插入分隔符,让它们各成一块。"""
    out, prev_quote = [], False
    for line in md.split("\n"):
        if re.match(r"> \[!(%s)\]" % "|".join(KINDS), line) and prev_quote:
            out += ["", "<!-- -->", ""]
        if line.strip():
            prev_quote = line.startswith(">")
        out.append(line)
    return "\n".join(out)


def callouts(h: str) -> str:
    pat = r"<blockquote>\s*<p>\[!(%s)\]\s*(.*?)</blockquote>" % "|".join(KINDS)
    return re.sub(pat, lambda m: f'<div class="callout {m.group(1)}"><span class="tag">{KINDS[m.group(1)]}</span><p>{m.group(2)}</div>',
                  h, flags=re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("-o", "--out")
    ap.add_argument("--embed-images", action="store_true", help="把沿用的位图下载并内嵌,生成自包含 HTML")
    a = ap.parse_args()
    src = Path(a.md)
    text = split_callouts(inline_figures(src.read_text(encoding="utf-8"), src.parent, a.embed_images))
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else src.stem
    # 文首第一个 '> ' 引用块(来源说明)做成 meta 头
    md = markdown.Markdown(extensions=["tables", "fenced_code", "md_in_html", "toc", "sane_lists"],
                           extension_configs={"toc": {"toc_depth": "2-3", "permalink": False}})
    body = md.convert(text)
    body = re.sub(r"(</h1>)\s*<blockquote>(.*?)</blockquote>", lambda m: f'{m.group(1)}<header class="meta">{m.group(2).strip().replace(chr(10), "<br>")}</header>', body, count=1, flags=re.S)
    body = callouts(body)
    css = (Path(__file__).resolve().parent.parent / "templates" / "style.css").read_text(encoding="utf-8")
    toc = f'<nav class="toc"><div class="toc-title">目录</div>{md.toc}</nav>'
    page = (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
            f'<style>{css}</style></head><body>{DEFS}<div class="layout">{toc}<main>{body}</main></div>{ZOOM}</body></html>')
    out = Path(a.out) if a.out else src.with_suffix(".html")
    out.write_text(page, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
