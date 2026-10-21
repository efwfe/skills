import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import lint_chapter  # noqa: E402

DATA = HERE / "data"
FIXTURES = HERE / "fixtures"


def run_lint(*paths, mode="standard", strict=False):
    buf = io.StringIO()
    argv = ["--mode", mode] + (["--strict"] if strict else []) + [str(p) for p in paths]
    with redirect_stdout(buf):
        code = lint_chapter.main(argv)
    return code, buf.getvalue()


class TestLintChapter(unittest.TestCase):
    def test_clean_passes(self):
        code, out = run_lint(DATA / "clean.md")
        self.assertEqual(code, 0, out)
        self.assertIn("共 0 条违规", out)

    def test_bad_reports_each_rule(self):
        code, out = run_lint(DATA / "bad.md")
        self.assertEqual(code, 1, out)               # 含[错误],默认退出码 1
        self.assertIn("[提醒] python 代码块", out)    # 代码块长度(提醒)
        self.assertIn("[提醒] 正文出现行内免责", out)   # 免责词(提醒)
        self.assertIn("[提醒] 正文出现元文字", out)     # 元文字(提醒)
        self.assertIn("[错误] 缺必备小节", out)         # 必备小节(错误)
        self.assertIn("[错误] 图片", out)             # 图片缺失(错误)
        self.assertIn("共 ", out)

    def test_bad_strict_also_fails(self):
        code, out = run_lint(DATA / "bad.md", strict=True)
        self.assertEqual(code, 1, out)

    def test_glossary_term_must_be_listed(self):
        code, out = run_lint(DATA / "gloss" / "chap.md")
        self.assertEqual(code, 1, out)               # 缺必备小节等[错误]仍在
        self.assertIn('[提醒] 术语"对账"', out)        # 用了但没列出 → [提醒]
        self.assertNotIn('术语"softmax"', out)        # 已列出 → 不违规

    def test_repro_seeded_passes(self):
        code, out = run_lint(DATA / "repro-seeded.md")
        self.assertEqual(code, 0, out)
        self.assertIn("共 0 条违规", out)

    def test_repro_missing_seed_warns(self):
        code, out = run_lint(DATA / "repro-missing-seed.md")
        self.assertEqual(code, 0, out)               # 只含[提醒],默认退出码 0
        self.assertIn("[提醒] 随机调用", out)
        self.assertIn("random.seed", out)

    def test_repro_missing_seed_strict_fails(self):
        code, out = run_lint(DATA / "repro-missing-seed.md", strict=True)
        self.assertEqual(code, 1, out)               # --strict:提醒也计入退出码
        self.assertIn("[提醒] 随机调用", out)


class TestNarrative(unittest.TestCase):
    def test_narr_clean_passes(self):
        code, out = run_lint(FIXTURES / "narr-clean.md")
        self.assertEqual(code, 0, out)
        self.assertIn("共 0 条违规", out)

    def test_narr_missing_crumb(self):
        code, out = run_lint(FIXTURES / "narr-missing-crumb.md")
        self.assertEqual(code, 1, out)
        self.assertIn("脉络条", out)

    def test_narr_crumb_required_in_baby_mode(self):
        code, out = run_lint(FIXTURES / "narr-missing-crumb.md", mode="baby")
        self.assertEqual(code, 1, out)
        self.assertIn("脉络条", out)


class TestBabyMode(unittest.TestCase):
    def test_baby_clean_passes(self):
        code, out = run_lint(FIXTURES / "baby-clean.md", mode="baby")
        self.assertEqual(code, 0, out)
        self.assertIn("共 0 条违规", out)

    def test_baby_missing_gap_section(self):
        code, out = run_lint(FIXTURES / "baby-missing-gap.md", mode="baby")
        self.assertEqual(code, 1, out)
        self.assertIn("缺必备小节:与真实实现的差距", out)

    def test_baby_clean_fails_standard_mode(self):
        code, out = run_lint(FIXTURES / "baby-clean.md", mode="standard")
        self.assertEqual(code, 1, out)
        self.assertIn("缺必备小节:局限", out)          # 标准模式的必备小节不再包含"心智模型"


class TestNonChapterFiles(unittest.TestCase):
    def _write(self, name, body):
        import tempfile
        d = Path(tempfile.mkdtemp())
        f = d / name
        f.write_text(body, encoding="utf-8")
        return f

    def test_glossary_and_map_skip_chapter_requirements(self):
        g = self._write("glossary.md", "# 术语表\n\n| 术语 | 定义 | 先在哪章完整讲 |\n|---|---|---|\n| `对账` | 比较输出 | ch01 |\n")
        m = self._write("00-map.md", "# 全书脉络\n\n一段正文。\n")
        for f in (g, m):
            code, out = run_lint(f)
            self.assertEqual(code, 0, out)
            self.assertNotIn("缺必备", out)

    def test_appendix_only_requires_exercises(self):
        a = self._write("appendix-a-basics.md", "# 附录 A\n\n正文。\n")
        code, out = run_lint(a)
        self.assertEqual(code, 1, out)
        self.assertIn("附录缺练习或答案要点", out)
        self.assertNotIn("脉络条", out)

    def test_roadmap_recognised_by_alt_text(self):
        ok = (DATA / "clean.md").read_text(encoding="utf-8")
        self.assertTrue(any("路线图" in alt or "roadmap" in ref
                            for alt, ref in lint_chapter.check_images.IMG.findall(ok)))

    def test_headings_do_not_count_as_term_use(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "glossary.md").write_text("| 术语 | 定义 | 先在哪章完整讲 |\n|---|---|---|\n| `分词` | 切开 | ch02 |\n", encoding="utf-8")
        f = d / "ch02.md"
        f.write_text("# 第 2 章 分词\n\n> **本章新术语**\n> `分词` 把文字切开。\n", encoding="utf-8")
        code, out = run_lint(f)
        self.assertNotIn('术语"分词"', out)


if __name__ == "__main__":
    unittest.main()