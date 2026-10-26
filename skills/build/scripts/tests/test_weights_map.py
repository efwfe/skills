import io
import json
import os
import struct
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import weights_map as wm  # noqa: E402

CONFIG = {"model_type": "toy", "hidden_size": 8, "num_hidden_layers": 2, "num_attention_heads": 4,
          "num_key_value_heads": 2, "intermediate_size": 16, "vocab_size": 10, "tie_word_embeddings": True}


def tensors(layers=2):
    t = {"model.embed_tokens.weight": [10, 8], "model.norm.weight": [8]}
    for i in range(layers):
        t[f"model.layers.{i}.self_attn.q_proj.weight"] = [8, 8]
        t[f"model.layers.{i}.self_attn.k_proj.weight"] = [4, 8]
        t[f"model.layers.{i}.mlp.up_proj.weight"] = [16, 8]
    return t


def write_safetensors(path, shapes, dtype="F32"):
    header, offset = {"__metadata__": {"format": "pt"}}, 0
    for name, shape in shapes.items():
        n = wm.numel(shape) * wm.DTYPE_BYTES[dtype]
        header[name] = {"dtype": dtype, "shape": shape, "data_offsets": [offset, offset + n]}
        offset += n
    raw = json.dumps(header).encode()
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + b"\0" * offset)


def expected_total(shapes):
    return sum(wm.numel(s) for s in shapes.values())


class RangeHandler(SimpleHTTPRequestHandler):
    """只为测试:支持单段 Range 的静态文件服务。"""

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = Path(self.translate_path(self.path))
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        rng = self.headers.get("Range")
        if rng:
            a, b = rng.split("=")[1].split("-")
            chunk = data[int(a):int(b) + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {a}-{int(a) + len(chunk) - 1}/{len(data)}")
        else:
            chunk = data
            self.send_response(200)
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk)


class TestWeightsMap(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "config.json").write_text(json.dumps(CONFIG))

    def test_single_file_groups_layers(self):
        write_safetensors(self.dir / "model.safetensors", tensors())
        t, cfg, shards = wm.load(str(self.dir))
        self.assertEqual(shards, ["model.safetensors"])
        groups = {g["pattern"]: g for g in wm.group(t)}
        q = groups["model.layers.{i}.self_attn.q_proj.weight"]
        self.assertEqual((q["count"], q["params"], q["shape"]), (2, 128, [8, 8]))
        self.assertNotIn("__metadata__", t)
        self.assertEqual(wm.summarize(t, cfg)["total"], expected_total(tensors()))

    def test_sharded_index(self):
        shapes = tensors()
        names = list(shapes)
        a, b = dict((n, shapes[n]) for n in names[:3]), dict((n, shapes[n]) for n in names[3:])
        write_safetensors(self.dir / "model-00001-of-00002.safetensors", a)
        write_safetensors(self.dir / "model-00002-of-00002.safetensors", b, dtype="BF16")
        index = {"weight_map": {n: "model-00001-of-00002.safetensors" for n in a} |
                 {n: "model-00002-of-00002.safetensors" for n in b}}
        (self.dir / wm.INDEX).write_text(json.dumps(index))
        t, cfg, shards = wm.load(str(self.dir))
        self.assertEqual(len(shards), 2)
        s = wm.summarize(t, cfg)
        self.assertEqual(s["total"], expected_total(shapes))
        self.assertEqual(s["bytes"], expected_total(a) * 4 + expected_total(b) * 2)

    def test_notes_tied_and_gqa(self):
        write_safetensors(self.dir / "model.safetensors", tensors())
        t, cfg, _ = wm.load(str(self.dir))
        notes = " ".join(wm.summarize(t, cfg)["notes"])
        self.assertIn("共用一份权重", notes)
        self.assertIn("GQA", notes)

    def test_layer_count_mismatch_noted(self):
        write_safetensors(self.dir / "model.safetensors", tensors(layers=3))
        t, cfg, _ = wm.load(str(self.dir))
        self.assertIn("实际有 3 层", " ".join(wm.summarize(t, cfg)["notes"]))

    def test_render_expect_and_symbol_column(self):
        write_safetensors(self.dir / "model.safetensors", tensors())
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = wm.main([str(self.dir / "model.safetensors"), "--expect", "100000"])
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("论文符号", out)
        self.assertIn("差距超过 1%", out)
        self.assertIn("`hidden_size`:8", out)          # 单个文件也会读同目录的 config.json

    def test_remote_range_reads_only_header(self):
        for k in ("NO_PROXY", "no_proxy"):      # 本地测试服务器不走代理
            os.environ[k] = "127.0.0.1,localhost"
        write_safetensors(self.dir / "model.safetensors", tensors())
        handler = lambda *a, **k: RangeHandler(*a, directory=str(self.dir), **k)  # noqa: E731
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{srv.server_address[1]}/model.safetensors"
            t, cfg, _ = wm.load(url)
            self.assertEqual(wm.summarize(t, cfg)["total"], expected_total(tensors()))
            self.assertEqual(cfg["hidden_size"], 8)
        finally:
            srv.shutdown()

    def test_bad_file_rejected(self):
        (self.dir / "model.safetensors").write_bytes(struct.pack("<Q", 2**40) + b"x")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(wm.main([str(self.dir)]), 2)


if __name__ == "__main__":
    unittest.main()
