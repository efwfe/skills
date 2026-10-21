import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from figkit import Fig  # noqa: E402


class TestFigkitCheckOverlap(unittest.TestCase):
    def test_overlapping_texts_raise(self):
        f = Fig(300, 100)
        f.text(10, 20, "abcdefghijklmnopqrstuvwxyz", size=13)
        f.text(40, 20, "abcdefghijklmnopqrstuvwxyz", size=13)
        with self.assertRaises(ValueError) as ctx:
            f.check()
        self.assertIn("文字重叠", str(ctx.exception))

    def test_separated_texts_pass(self):
        f = Fig(400, 80)
        f.text(10, 20, "left", size=13)
        f.text(200, 20, "right", size=13)
        f.check()


if __name__ == "__main__":
    unittest.main()