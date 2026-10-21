import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import check_repro  # noqa: E402

DATA = HERE / "data"


def run_check(*paths, run=False):
    buf = io.StringIO()
    argv = [str(p) for p in paths] + (["--run"] if run else [])
    with redirect_stdout(buf):
        code = check_repro.main(argv)
    return code, buf.getvalue()


class TestCheckRepro(unittest.TestCase):
    def test_seeded_passes(self):
        code, out = run_check(DATA / "repro-seeded.md")
        self.assertEqual(code, 0, out)

    def test_missing_seed_fails(self):
        code, out = run_check(DATA / "repro-missing-seed.md")
        self.assertEqual(code, 1, out)
        self.assertIn("random.seed(...)", out)

    def test_nondeterministic_block_differs_on_run(self):
        code, out = run_check(DATA / "repro-nondet.md", run=True)
        self.assertEqual(code, 1, out)
        self.assertIn("两次运行输出不同", out)


if __name__ == "__main__":
    unittest.main()