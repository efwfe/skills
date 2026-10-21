#!/usr/bin/env python3
"""Tiny SVG kit reproducing the book's figure style: flat white boxes, thin dark
outlines, vertical step arrows, bold gray callouts joined by a dashed leader,
and number grids/heatmaps with truncated digits.

    from figkit import Fig
    f = Fig(640, 260)
    f.steps(40, 30, ["1) Compute scores", "2) Softmax", "3) Weighted sum"],
            ["dot products", "rows sum to 1", "context vectors"])
    f.caption("Figure 1  Three steps ...")   # optional; the book writes captions in Markdown only
    f.save("fig.svg")   # runs check() first: raises if any element overflows the canvas

Every element's estimated bounding box is tracked; Fig.save() runs check() and
raises (instead of silently clipping) if text or boxes stick out of the canvas.

Run this file to write a demo to ./figkit_demo.svg.
"""
import html, os, shutil, subprocess

INK, FILL, NOTE, HI = "#222", "#fff", "#555", "#fde9a8"   # outline, box, callout text, highlight
FONT = ("font-family='&quot;PingFang SC&quot;,&quot;Hiragino Sans GB&quot;,&quot;Noto Sans CJK SC&quot;,"
        "&quot;Microsoft YaHei&quot;,Helvetica,Arial,sans-serif'")
MONO = ("font-family='&quot;SF Mono&quot;,Menlo,Consolas,&quot;Noto Sans Mono CJK SC&quot;,"
        "&quot;PingFang SC&quot;,monospace'")
WIDE_PUNCT = set("…—–“”‘’")


def esc(s):
    return html.escape(str(s), quote=False)


def text_width(s, size=12, mono=False):
    """Estimated rendered width in px: CJK/full-width ≈ 1em, Latin ≈ 0.55em (0.6em in mono)."""
    w = 0.0
    for ch in str(s):
        if ord(ch) > 0x2E80 or ch in WIDE_PUNCT:
            w += size
        elif mono:
            w += 0.6 * size
        else:
            w += 0.55 * size
    return w


class Fig:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []
        self.objs, self.fits = [], []          # bboxes to verify, box-overflow messages
        self.parts.append(
            "<defs><marker id='a' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' "
            f"orient='auto'><path d='M0,0 L10,5 L0,10 z' fill='{INK}'/></marker></defs>"
        )

    def _rec(self, desc, x0, y0, x1, y1):
        self.objs.append((desc, x0, y0, x1, y1))

    def _fit(self, msg):
        self.fits.append(msg)

    def box(self, x, y, w, h, text="", hi=False, size=12, bold=False, rx=6, mono=False):
        fill = HI if hi else FILL
        self.parts.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='{rx}' fill='{fill}' stroke='{INK}' stroke-width='1'/>")
        self._rec(f"框 '{text}'".replace("\n", " / "), x, y, x + w, y + h)
        if text:
            lines = str(text).split("\n")
            y0 = y + h / 2 - (len(lines) - 1) * (size + 2) / 2 + size / 3
            for i, ln in enumerate(lines):
                tw = text_width(ln, size, mono)
                if tw > w - 8:
                    self._fit(f"框 '{ln}' 文字宽 {tw:.1f} > 框宽 {w}(需 ≥ {tw + 8:.0f})")
                wt = "bold" if bold else "normal"
                ff = MONO if mono else FONT
                self.parts.append(f"<text x='{x + w / 2}' y='{y0 + i * (size + 2)}' text-anchor='middle' font-size='{size}' font-weight='{wt}' {ff} fill='{INK}'>{esc(ln)}</text>")
                self._rec(f"框内文字 '{ln}'", x + w / 2 - tw / 2, y0 + i * (size + 2) - size, x + w / 2 + tw / 2, y0 + i * (size + 2) + 2)

    def arrow(self, x1, y1, x2, y2, dashed=False):
        d = " stroke-dasharray='4 3'" if dashed else ""
        self.parts.append(f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{INK}' stroke-width='1'{d} marker-end='url(#a)'/>")
        self._rec("箭头", min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    def fan(self, points, x, y, w, gap=8):
        """Arrows from each (x1, y1) in points to targets spread along the segment (x,y)-(x+w,y).

        Fixes the "8 个箭头指向同一点" problem: targets are evenly distributed
        over the width of the target box instead of piling onto one spot."""
        n = len(points)
        for i, (x1, y1) in enumerate(points):
            tx = x + w / 2 if n == 1 else x + gap + (w - 2 * gap) * i / (n - 1)
            self.arrow(x1, y1, tx, y)

    def text(self, x, y, s, size=12, anchor="start", bold=False, color=NOTE, mono=False):
        wt = "bold" if bold else "normal"
        ff = MONO if mono else FONT
        for i, ln in enumerate(str(s).split("\n")):
            self.parts.append(f"<text x='{x}' y='{y + i * (size + 3)}' text-anchor='{anchor}' font-size='{size}' font-weight='{wt}' {ff} fill='{color}'>{esc(ln)}</text>")
            tw = text_width(ln, size, mono)
            if anchor == "start":
                left, right = x, x + tw
            elif anchor == "end":
                left, right = x - tw, x
            else:
                left, right = x - tw / 2, x + tw / 2
            self._rec(f"文字 '{ln}'", left, y + i * (size + 3) - size, right, y + i * (size + 3) + 3)

    def callout(self, x_from, y_from, x, y, s, size=12):
        """Bold gray note at (x, y), dashed arrow back to (x_from, y_from)."""
        self.arrow(x - 6, y - size / 3, x_from, y_from, dashed=True)
        self.text(x, y, s, size=size, bold=True)

    def steps(self, x, y, labels, notes=(), w=190, h=30, gap=34, hi=None):
        """Vertical chain of boxes with arrows and right-hand callouts (Figure 3.12 style)."""
        for i, lab in enumerate(labels):
            by = y + i * (h + gap)
            self.box(x, by, w, h, lab, hi=(hi == i))
            if i < len(labels) - 1:
                self.arrow(x + w / 2, by + h, x + w / 2, by + h + gap)
            if i < len(notes) and notes[i]:
                self.callout(x + w, by + h / 2, x + w + 36, by + h / 2 + 4, notes[i])

    def roadmap(self, x, y, items, current, w=88, h=30, gap=10, size=11, rows=1):
        """Roadmap with the current step highlighted (repeat it at every chapter start).

        rows=2 wraps the strip into two rows (7+7) so long labels keep >= 13px
        text within a <= 760px canvas; a vertical arrow connects the rows."""
        n, idx = len(items), 0
        per = -(-n // rows)
        for r in range(rows):
            count = min(per, n - idx)
            last = None
            for c in range(count):
                i = idx + c
                bx = x + c * (w + gap)
                by = y + r * (h + 24)
                self.box(bx, by, w, h, items[i], hi=(i == current), size=size)
                if c < count - 1:
                    self.arrow(bx + w, by + h / 2, bx + w + gap, by + h / 2)
                last = (bx + w / 2, by + h)
            if r < rows - 1 and count:
                self.arrow(last[0], last[1], x + w / 2, y + (r + 1) * (h + 24) - 4)
            idx += count

    def _chain_widths(self, items, size, min_w):
        """Per-item box widths: max(min_w, widest line + 10) so text never overflows."""
        return [max(min_w, max(text_width(l, size) for l in str(t[0] if isinstance(t, tuple) else t).split("\n")) + 10)
                for t in items]

    def roadmap_tree(self, x, y, stages, current, chain, w=116, h=34, gap=14, size=13,
                     cgap=12, csize=13, min_cw=64, ch=34, sgap=8, ssize=13, min_sw=56, sh=28,
                     chain_current=None):
        """Stage-level roadmap: stage row (current stage highlighted) with a vertical
        arrow into the current stage's component chain; chain items are str or
        (label, [subcomponents...]) and subcomponents get a third row. Sizes default
        to >= 13px; keep the canvas <= 760 wide, check() catches any overflow."""
        for i, s in enumerate(stages):
            bx = x + i * (w + gap)
            self.box(bx, y, w, h, s, hi=(i == current), size=size)
            if i < len(stages) - 1:
                self.arrow(bx + w, y + h / 2, bx + w + gap, y + h / 2)
        cx_c = x + current * (w + gap) + w / 2
        y2 = y + h + 26
        widths = self._chain_widths(chain, csize, min_cw)
        norms = [(t[0] if isinstance(t, tuple) else str(t), t[1] if isinstance(t, tuple) else None) for t in chain]
        bhs = [ch + (len(lbl.split("\n")) - 1) * (csize + 2) for lbl, _ in norms]
        bx = cx_c - widths[0] / 2
        subs_info = []
        for j, (label, subs) in enumerate(norms):
            bh = bhs[j]
            self.box(bx, y2, widths[j], bh, label, hi=(j == chain_current), size=csize)
            if j < len(norms) - 1:
                self.arrow(bx + widths[j], y2 + bh / 2, bx + widths[j] + cgap, y2 + bhs[j + 1] / 2)
            if subs:
                subs_info.append((bx + widths[j] / 2, y2 + bh, subs))
            bx += widths[j] + cgap
        self.arrow(cx_c, y + h, cx_c, y2)
        if subs_info:
            y3 = y2 + max(bhs) + 26
            for cx, bottom, subs in subs_info:
                widths_s = [max(min_sw, text_width(s, ssize) + 10) for s in subs]
                total = sum(widths_s) + sgap * (len(subs) - 1)
                sx = cx - total / 2
                self.arrow(cx, bottom, cx, y3)
                for k, s in enumerate(subs):
                    self.box(sx, y3, widths_s[k], sh, s, hi=False, size=ssize)
                    if k < len(subs) - 1:
                        self.arrow(sx + widths_s[k], y3 + sh / 2, sx + widths_s[k] + sgap, y3 + sh / 2)
                    sx += widths_s[k] + sgap

    @staticmethod
    def _wrap2(s, size, max_w):
        """Greedy wrap into at most two lines by estimated width."""
        if text_width(s, size) <= max_w:
            return [s]
        split = max(1, (len(s) + 1) // 2)
        return [s[:split], s[split:]]

    def roadmap_chain(self, x, y, items, current, h=34, gap=12, size=13, min_w=64,
                      stage=None, up=None, down=None):
        """Component-level mini roadmap: one stage's component chain with the current
        component highlighted; neighbours on both sides show where it sits. stage is
        a stage name drawn top-left. up/down are two independent note blocks, the
        upstream block left below the highlighted node and the downstream block right
        below it, each in its own horizontal range and wrapped to at most two lines;
        a dashed arrow goes from the highlighted node's bottom to each block."""
        widths = self._chain_widths(items, size, min_w)
        bx, cx_h = x, 0.0
        for i, t in enumerate(items):
            self.box(bx, y, widths[i], h, str(t), hi=(i == current), size=size)
            if i == current:
                cx_h = bx + widths[i] / 2
            if i < len(items) - 1:
                self.arrow(bx + widths[i], y + h / 2, bx + widths[i] + gap, y + h / 2)
            bx += widths[i] + gap
        right = bx - gap
        if stage:
            self.text(x, y - 10, stage, size=size, bold=True, color=INK)
        if up or down:
            y0 = y + h + 2 * size + 14
            if up:
                lines = self._wrap2(up, size, max((self.w - 2 * x) / 2 - 8, size))
                self.text(x, y0, "\n".join(lines), size=size, bold=True)
                self.arrow(cx_h, y + h, x + text_width(lines[0], size) / 2, y0 - size - 2, dashed=True)
            if down:
                lines = self._wrap2(down, size, max((self.w - 2 * x) / 2 - 8, size))
                ax = max(right, self.w - x)
                self.text(ax, y0, "\n".join(lines), size=size, bold=True, anchor="end")
                self.arrow(cx_h, y + h, ax - text_width(lines[0], size) / 2, y0 - size - 2, dashed=True)

    def grid(self, x, y, rows, cell=44, fmt="{:.2f}", hi=None, blank=None, labels=None):
        """Number matrix. hi: set of (r,c) to highlight; blank: set of (r,c) drawn empty (masked)."""
        hi, blank = hi or set(), blank or set()
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                cx, cy = x + c * cell, y + r * (cell * 0.6)
                masked = (r, c) in blank
                fill = HI if (r, c) in hi else ("#eee" if masked else FILL)
                self.parts.append(f"<rect x='{cx}' y='{cy}' width='{cell}' height='{cell * 0.6}' fill='{fill}' stroke='{INK}' stroke-width='0.6'/>")
                self._rec(f"格 ({r},{c})", cx, cy, cx + cell, cy + cell * 0.6)
                if not masked:
                    self.parts.append(f"<text x='{cx + cell / 2}' y='{cy + cell * 0.4}' text-anchor='middle' font-size='11' {FONT} fill='{INK}'>{esc(fmt.format(v))}</text>")
                    tw = text_width(fmt.format(v), 11)
                    if tw > cell - 8:
                        self._fit(f"格 ({r},{c}) 数字 '{fmt.format(v)}' 宽 {tw:.1f} > 格宽 {cell}")
                    self._rec(f"格 ({r},{c}) 数字", cx + cell / 2 - tw / 2, cy + cell * 0.4 - 11, cx + cell / 2 + tw / 2, cy + cell * 0.4 + 4)
        if labels:
            for i, lab in enumerate(labels):
                self.text(x - 8, y + i * (cell * 0.6) + cell * 0.4, lab, size=11, anchor="end", color=INK)
                self.text(x + i * cell + cell / 2, y - 6, lab, size=11, anchor="middle", color=INK)

    def bars(self, x, y, labels, values, w=360, h=24, gap=10, fmt="{:.2f}", hi=None, label_w=150, vmax=None):
        """Horizontal bar chart with value labels; hi = index to highlight (the one the figure is about)."""
        vmax = vmax or max(values)
        for i, (lab, v) in enumerate(zip(labels, values)):
            by = y + i * (h + gap)
            self.text(x + label_w - 8, by + h / 2 + 4, lab, size=12, anchor="end", color=INK)
            bw = max(1, w * v / vmax)
            self.parts.append(f"<rect x='{x + label_w}' y='{by}' width='{bw}' height='{h}' fill='{HI if hi == i else '#ddd'}' stroke='{INK}' stroke-width='0.8'/>")
            self._rec(f"条 '{lab}'", x + label_w, by, x + label_w + bw, by + h)
            self.text(x + label_w + bw + 6, by + h / 2 + 4, fmt.format(v), size=12, color=INK)

    def lines(self, x, y, w, h, series, xlabel="", ylabel="", ymax=None, styles=None):
        """Line chart. series = {name: (xs, ys)}; styles = {name: {"dash": ..., "color": ...}}.

        Lines and their legend entries carry the same dash/color. The y axis
        reserves headroom when ymax > max(ys) so flat curves don't sit on the
        frame; distinct styles keep overlapping curves (e.g. a constant and a
        WSD plateau) distinguishable."""
        xs_all = [v for xs, _ in series.values() for v in xs]
        ys_all = [v for _, ys in series.values() for v in ys]
        x0, x1, y1 = min(xs_all), max(xs_all), ymax or max(ys_all)
        self.parts.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='none' stroke='{INK}' stroke-width='0.8'/>")
        self._rec("坐标框", x, y, x + w, y + h)
        dashes = ["", "6 3", "2 3", "8 3 2 3"]
        for k, (name, (xs, ys)) in enumerate(series.items()):
            st = (styles or {}).get(name, {})
            dash = st.get("dash", dashes[k % 4])
            color = st.get("color", INK)
            pts = " ".join(f"{x + (a - x0) / (x1 - x0) * w:.1f},{y + h - b / y1 * h:.1f}" for a, b in zip(xs, ys))
            d = f" stroke-dasharray='{dash}'" if dash else ""
            self.parts.append(f"<polyline points='{pts}' fill='none' stroke='{color}' stroke-width='1.6'{d}/>")
            self.parts.append(f"<line x1='{x + w + 10}' y1='{y + 10 + k * 18}' x2='{x + w + 42}' y2='{y + 10 + k * 18}' stroke='{color}' stroke-width='1.6'{d}/>")
            self._rec(f"图例 '{name}'", x + w + 10, y + 10 + k * 18 - 2, x + w + 42, y + 10 + k * 18 + 2)
            self.text(x + w + 48, y + 14 + k * 18, name, size=12, color=color)
        self.text(x + w / 2, y + h + 18, xlabel, size=11, anchor="middle")
        self.text(x - 8, y + 10, f"{y1:g}", size=11, anchor="end")
        self.text(x - 8, y + h, "0", size=11, anchor="end")
        self.text(x, y + h + 18, f"{x0:g}", size=11)
        self.text(x + w, y + h + 18, f"{x1:g}", size=11, anchor="end")
        if ylabel:
            self.text(x, y - 8, ylabel, size=11)

    def strip(self, x, y, tokens, flags, cell=46, h=30, size=10):
        """Token strip: flagged tokens are highlighted (e.g. tokens that receive
        loss); unflagged stay white. Tokens are monospaced so | reads as |,
        not as l."""
        for i, (t, f) in enumerate(zip(tokens, flags)):
            self.box(x + i * cell, y, cell, h, t, hi=bool(f), size=size, rx=2, mono=True)

    def caption(self, s, x=None, y=None):
        """Caption auto-wrapped to the canvas width; y is the first line's baseline (leave room below).

        Optional: the book writes captions once in Markdown and does not burn
        them into the PNG/SVG."""
        x = 10 if x is None else x
        avail, lines, cur, width = self.w - x - 10, [], "", 0.0
        for ch in s:
            cw = text_width(ch, 12)
            if width + cw > avail:
                lines.append(cur); cur, width = "", 0.0
            cur, width = cur + ch, width + cw
        lines.append(cur)
        s = "\n".join(lines)
        self.text(x, self.h - 12 - 15 * (len(lines) - 1) if y is None else y, s, size=12, color=INK)

    def svg(self):
        return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{self.w}' height='{self.h}' viewBox='0 0 {self.w} {self.h}'>"
                f"<rect width='100%' height='100%' fill='#fff'/>" + "".join(self.parts) + "</svg>")

    def check(self):
        """Raise if any element's estimated bounding box leaves the canvas,
        if any text overflows the box it sits in, or if any two text
        elements' estimated boxes overlap each other."""
        errs = []
        for desc, x0, y0, x1, y1 in self.objs:
            if x0 < -0.5 or y0 < -0.5 or x1 > self.w + 0.5 or y1 > self.h + 0.5:
                errs.append(f"{desc}: ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) 超出画布 {self.w}x{self.h}")
        texts = [t for t in self.objs if "文字" in t[0] or "数字" in t[0]]
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                d1, a1, b1, c1, e1 = texts[i]
                d2, a2, b2, c2, e2 = texts[j]
                if a1 < c2 and a2 < c1 and b1 < e2 and b2 < e1:
                    errs.append(f"文字重叠:{d1}({a1:.0f},{b1:.0f}-{c1:.0f},{e1:.0f}) 与 "
                                f"{d2}({a2:.0f},{b2:.0f}-{c2:.0f},{e2:.0f})")
        errs += self.fits
        if errs:
            raise ValueError("边界检查失败,拒绝生成有问题的图:\n" + "\n".join(f"- {e}" for e in errs))

    def save(self, path, png=True):
        """Write SVG (after check() passes), then rasterise the PNG at 2x.

        Fallback chain: headless Chrome (exact canvas, CJK fonts) ->
        rsvg-convert -> macOS qlmanage + magick -trim. If none is available
        the SVG is kept and a message printed."""
        path = str(path)
        self.check()
        svg = self.svg()
        import xml.dom.minidom
        try:
            xml.dom.minidom.parseString(svg)
        except Exception as e:
            raise ValueError(f"生成的 SVG 不是合法 XML,拒绝写入 {path}: {e}")
        open(path, "w", encoding="utf-8").write(svg)
        if not (png and path.endswith(".svg")):
            return
        dst, here = path[:-4] + ".png", os.path.dirname(os.path.abspath(path))
        ok = lambda: os.path.exists(dst) and os.path.getsize(dst) > 0
        chrome = next((c for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome"), shutil.which("chromium")) if c and os.path.exists(c)), None)
        if chrome:
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                            f"--window-size={self.w},{self.h}", f"--screenshot={os.path.abspath(dst)}", "file://" + os.path.abspath(path)],
                           capture_output=True, timeout=60)
        if not ok() and shutil.which("rsvg-convert"):
            subprocess.run(["rsvg-convert", "-z", "2", "-o", dst, path], capture_output=True)
        if not ok() and shutil.which("qlmanage"):
            subprocess.run(["qlmanage", "-t", "-s", str(max(self.w, self.h) * 2), "-o", here, path], capture_output=True)
            if os.path.exists(path + ".png"):
                os.replace(path + ".png", dst)
                if shutil.which("magick"):
                    subprocess.run(["magick", dst, "-trim", "+repage", "-bordercolor", "white", "-border", "16", dst], capture_output=True)
        if not ok():
            print(f"提示: 无 headless Chrome / rsvg-convert / qlmanage,PNG 未生成,仅保留 SVG: {path}")


if __name__ == "__main__":
    f = Fig(640, 280)
    f.roadmap(10, 12, ["1 Data", "2 Attention", "3 Model", "4 Train", "5 Tune"], current=1, w=112)
    f.steps(40, 70, ["1) Compute scores", "2) Normalize", "3) Weighted sum"], ["dot product of each pair", "softmax: rows sum to 1", "context vectors z(i)"], hi=0)
    f.caption("Figure 1  Demo: roadmap with current step highlighted, steps with gray callouts.")
    f.save("figkit_demo.svg")
    print("wrote figkit_demo.svg")