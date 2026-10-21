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

    def test_wikilink_alias_and_heading(self):
        self.assertEqual(lg.LINK.findall("见 [[a-b|别名]] 与 [[c#小节]]"), ["a-b", "c"])


if __name__ == "__main__":
    unittest.main()
