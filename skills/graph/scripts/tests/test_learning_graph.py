import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import learning_graph as lg  # noqa: E402

LIB = HERE / "fixtures" / "library"


def edge(graph, a, b, typ):
    return [e for e in graph["edges"] if {e["source"], e["target"]} == {a, b} and e["type"] == typ]


class TestBuildGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = lg.build_graph(LIB)
        cls.nodes = {n["id"]: n for n in cls.g["nodes"]}

    def test_kinds_from_folders_and_prefixes(self):
        kinds = {k: n["kind"] for k, n in self.nodes.items()}
        self.assertEqual(kinds["append-only-log"], "dot")
        self.assertEqual(kinds["content-addressing"], "candidate")
        self.assertEqual(kinds["jj-vcs-jj"], "project")
        self.assertEqual(kinds["blog-git-internals"], "blog")
        self.assertEqual(kinds["event-sourcing"], "ghost")     # 只被链接引用、没有文件

    def test_meta_files_are_not_nodes(self):
        for name in ("index", "changelog", "tensions"):
            self.assertNotIn(name, self.nodes)

    def test_relation_types_from_sections(self):
        self.assertTrue(edge(self.g, "append-only-log", "event-sourcing", "同源异形"))
        self.assertTrue(edge(self.g, "append-only-log", "content-addressing", "依赖"))
        self.assertEqual(len(edge(self.g, "append-only-log", "compaction", "张力")), 1)  # 连接小节 + tensions.md 合并

    def test_example_edges_merge_both_directions(self):
        es = edge(self.g, "append-only-log", "jj-vcs-jj", "例证")
        self.assertEqual(len(es), 1)
        self.assertEqual(es[0]["count"], 2)                  # dot 的例证 + 项目的"本项目涉及的 dot"

    def test_generic_link_dropped_when_typed_exists(self):
        self.assertFalse(edge(self.g, "content-addressing", "blog-git-internals", "关联"))

    def test_flags(self):
        self.assertIn("可升级", self.nodes["content-addressing"]["flags"])
        self.assertIn("半个", self.nodes["compaction"]["flags"])
        self.assertIn("没落到代码", self.nodes["compaction"]["flags"])
        self.assertNotIn("没落到代码", self.nodes["append-only-log"]["flags"])
        self.assertIn("孤立", self.nodes["lonely-idea"]["flags"])

    def test_one_liner_and_fields(self):
        n = self.nodes["append-only-log"]
        self.assertTrue(n["one_liner"].startswith("只追加不修改"))
        self.assertEqual(n["状态"], "已确认")
        self.assertEqual(self.nodes["tj-commander.js"]["one_liner"], "声明式定义命令")

    def test_report_mentions_problems(self):
        text = lg.report(self.g)
        for word in ("可升级", "悬挂链接", "孤立", "张力"):
            self.assertIn(word, text)

    def test_html_embeds_data_safely(self):
        g = {"nodes": [{"id": "x", "kind": "dot", "excerpt": "</script><b>"}], "edges": [],
             "library": "", "generated": ""}
        html = lg.render_html(g)
        self.assertNotIn("/*__GRAPH_DATA__*/null", html)
        self.assertNotIn("</script><b>", html)

    def test_record_prefix_kinds_and_dates(self):
        self.assertEqual(self.nodes["paper-merkle"]["kind"], "paper")
        self.assertEqual(self.nodes["append-only-log"]["date"], "2026-09-01")
        self.assertEqual(self.nodes["paper-merkle"]["date"], "2026-08-20")
        self.assertIn("增长", lg.report(self.g))

    def test_compare_note_is_not_an_example_source(self):
        self.assertEqual(self.nodes["compare-jj-vs-git"]["kind"], "compare")
        self.assertTrue(edge(self.g, "compare-jj-vs-git", "content-addressing", "关联"))
        self.assertEqual(self.nodes["content-addressing"]["examples"], 2)   # 对比笔记不计入例证

    def test_prerequisites_follow_dependency_edges(self):
        order, cycle = lg.prerequisites(self.g, "append-only-log")
        self.assertEqual(order, ["hashing", "content-addressing", "append-only-log"])
        self.assertEqual(cycle, [])

    def test_prerequisites_detect_cycle(self):
        g = {"nodes": [], "edges": [{"source": "a", "target": "b", "type": "依赖"},
                                    {"source": "b", "target": "a", "type": "依赖"}]}
        _, cycle = lg.prerequisites(g, "a")
        self.assertEqual(cycle, ["a", "b"])

    def test_suggest_shared_examples_but_not_linked_pairs(self):
        pairs = {frozenset((s["a"], s["b"])): s for s in lg.suggest(self.g)}
        hit = pairs.get(frozenset(("compaction", "content-addressing")))
        self.assertIsNotNone(hit)
        self.assertIn("jj-vcs-jj", hit["why"])
        self.assertNotIn(frozenset(("append-only-log", "compaction")), pairs)   # 已经连上的不再建议

    def test_mermaid_export(self):
        text = lg.to_mermaid(self.g)
        self.assertTrue(text.startswith("```mermaid\nflowchart LR"))
        self.assertIn("-->|依赖|", text)
        self.assertIn("-.-|张力|", text)

    def test_canvas_export(self):
        c = lg.to_canvas(self.g)
        ids = {n["id"] for n in c["nodes"]}
        self.assertEqual(ids, set(self.nodes))
        dot = next(n for n in c["nodes"] if n["id"] == "append-only-log")
        self.assertEqual((dot["type"], dot["file"]), ("file", "dots/append-only-log.md"))
        ghost = next(n for n in c["nodes"] if n["id"] == "event-sourcing")
        self.assertEqual(ghost["type"], "text")
        self.assertTrue(all(e["fromNode"] in ids and e["toNode"] in ids for e in c["edges"]))

    def test_cli_runs_all_outputs(self):
        import tempfile, io
        from contextlib import redirect_stdout
        d = Path(tempfile.mkdtemp())
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = lg.main([str(LIB), "--out", str(d / "g.html"), "--mermaid", str(d / "g.md"),
                            "--canvas", str(d / "g.canvas"), "--suggest", "--path", "append-only-log"])
        self.assertEqual(code, 0)
        self.assertIn("可能相关", buf.getvalue())
        self.assertIn("1. [[hashing]]", buf.getvalue())
        for f in ("g.html", "g.md", "g.canvas"):
            self.assertTrue((d / f).stat().st_size > 0)

    def test_wikilink_alias_and_heading(self):
        self.assertEqual(lg.LINK.findall("见 [[a-b|别名]] 与 [[c#小节]]"), ["a-b", "c"])


if __name__ == "__main__":
    unittest.main()
