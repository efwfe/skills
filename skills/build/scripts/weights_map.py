#!/usr/bin/env python3
"""读开放权重的"参数地图":每个权重叫什么、什么形状、在哪一层,合起来多少参数。

只读 safetensors 文件开头的头信息(一段 JSON),不加载权重本身,所以:
- 不需要 PyTorch,零第三方依赖;
- 远程文件只用 HTTP Range 读开头几 KB,不下载整个模型。

用法:
  uv run python weights_map.py <来源> [--expect 参数量] [--json out.json]

<来源> 可以是:
  本地模型目录(含 config.json 与 *.safetensors 或 model.safetensors.index.json)
  单个 .safetensors 文件
  hf:<owner>/<name>[@revision]   Hugging Face 上的模型(需要网络能访问 huggingface.co)
  https://.../model.safetensors   任意支持 Range 的 URL

输出 Markdown:配置要点、按层归并后的参数表(每类权重一行,数字层号折成 {i}),
以及"论文符号"一列留空,由学习者对照论文填写。--expect 给出论文里的参数量时,顺带核对差多少。
"""
import argparse
import json
import re
import struct
import sys
import urllib.error
import urllib.request
from collections import OrderedDict, defaultdict
from pathlib import Path

DTYPE_BYTES = {"F64": 8, "F32": 4, "F16": 2, "BF16": 2, "I64": 8, "I32": 4, "I16": 2, "I8": 1,
               "U8": 1, "BOOL": 1, "F8_E4M3": 1, "F8_E5M2": 1, "U16": 2, "U32": 4, "U64": 8}
CONFIG_KEYS = ("model_type", "architectures", "hidden_size", "num_hidden_layers", "num_attention_heads",
               "num_key_value_heads", "head_dim", "intermediate_size", "vocab_size", "max_position_embeddings",
               "rope_theta", "rms_norm_eps", "tie_word_embeddings", "num_experts", "num_experts_per_tok",
               "sliding_window", "torch_dtype")
INDEX = "model.safetensors.index.json"
MAX_HEADER = 100 * 1024 * 1024


# ---------- 读取 ----------

class Source:
    """本地目录/文件或远程 URL 的统一读取:read(名字, 起, 止) 与 text(名字)。"""

    def __init__(self, spec):
        self.remote = False
        if spec.startswith("hf:"):
            repo, _, rev = spec[3:].partition("@")
            self.base, self.remote, self.single = f"https://huggingface.co/{repo}/resolve/{rev or 'main'}/", True, None
        elif spec.startswith(("http://", "https://")):
            self.base, self.remote = spec.rsplit("/", 1)[0] + "/", True
            self.single = spec.rsplit("/", 1)[1] if spec.endswith(".safetensors") else None
        else:
            p = Path(spec).expanduser()
            if p.is_file():
                self.base, self.single = p.parent, p.name
            else:
                self.base, self.single = p, None

    def _url(self, name):
        return self.base + name

    def read(self, name, start, end):
        if self.remote:
            req = urllib.request.Request(self._url(name), headers={"Range": f"bytes={start}-{end - 1}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if r.status == 200 and len(data) > end - start:  # 服务器忽略了 Range,只取需要的部分
                data = data[start:end]
            return data
        with open(Path(self.base) / name, "rb") as f:
            f.seek(start)
            return f.read(end - start)

    def text(self, name):
        try:
            if self.remote:
                with urllib.request.urlopen(self._url(name), timeout=60) as r:
                    return r.read().decode("utf-8")
            path = Path(self.base) / name
            return path.read_text(encoding="utf-8") if path.is_file() else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def shard_names(self):
        if self.single:
            return [self.single]
        index = self.text(INDEX)
        if index:
            return sorted(set(json.loads(index)["weight_map"].values()))
        if not self.remote:
            files = sorted(p.name for p in Path(self.base).glob("*.safetensors"))
            if files:
                return files
        return ["model.safetensors"]


def read_header(src, name):
    n = struct.unpack("<Q", src.read(name, 0, 8))[0]
    if n > MAX_HEADER:
        raise ValueError(f"{name}:头长度 {n} 字节不合理,可能不是 safetensors 文件")
    header = json.loads(src.read(name, 8, 8 + n))
    header.pop("__metadata__", None)
    return header


def load(spec):
    src = Source(spec)
    tensors = OrderedDict()
    shards = src.shard_names()
    for shard in shards:
        for k, v in read_header(src, shard).items():
            tensors[k] = {"dtype": v["dtype"], "shape": v["shape"], "shard": shard}
    config = src.text("config.json")
    return tensors, (json.loads(config) if config else {}), shards


# ---------- 归并 ----------

def numel(shape):
    n = 1
    for d in shape:
        n *= d
    return n


def pattern(name):
    """把层号折成 {i}:model.layers.3.mlp.up_proj.weight → model.layers.{i}.mlp.up_proj.weight。"""
    return re.sub(r"\.(\d+)(?=\.)", ".{i}", name)


def group(tensors):
    groups = OrderedDict()
    for name, t in tensors.items():
        key = pattern(name)
        g = groups.setdefault(key, {"pattern": key, "shape": t["shape"], "dtype": t["dtype"],
                                    "count": 0, "params": 0, "shapes": set()})
        g["count"] += 1
        g["params"] += numel(t["shape"])
        g["shapes"].add(tuple(t["shape"]))
    for g in groups.values():
        g["uniform"] = len(g["shapes"]) == 1
        g["shapes"] = sorted(g["shapes"])
    return list(groups.values())


def summarize(tensors, config):
    total = sum(numel(t["shape"]) for t in tensors.values())
    size = sum(numel(t["shape"]) * DTYPE_BYTES.get(t["dtype"], 0) for t in tensors.values())
    dtypes = defaultdict(int)
    for t in tensors.values():
        dtypes[t["dtype"]] += numel(t["shape"])
    names = set(tensors)
    notes = []
    has_head = any(n.endswith("lm_head.weight") for n in names)
    if config.get("tie_word_embeddings") and not has_head:
        notes.append("tie_word_embeddings=true 且文件里没有 lm_head:输出层与词嵌入共用一份权重,参数只算一次")
    elif config.get("tie_word_embeddings") and has_head:
        notes.append("tie_word_embeddings=true 但文件里仍有 lm_head:核对两者是否真的相同")
    layers = config.get("num_hidden_layers")
    if layers:
        seen = {int(m.group(1)) for n in names for m in [re.search(r"\.layers\.(\d+)\.", n)] if m}
        if seen and len(seen) != layers:
            notes.append(f"config 写 num_hidden_layers={layers},权重里实际有 {len(seen)} 层")
    heads, kv, hidden = config.get("num_attention_heads"), config.get("num_key_value_heads"), config.get("hidden_size")
    if heads and kv and heads != kv:
        notes.append(f"注意力头 {heads} 个、KV 头 {kv} 个:分组查询注意力(GQA),每 {heads // kv} 个查询头共用一组 K/V")
    if heads and hidden and config.get("head_dim") and config["head_dim"] * heads != hidden:
        notes.append(f"head_dim×头数 = {config['head_dim'] * heads} ≠ hidden_size {hidden}:注意力内部维度与隐藏维度不同")
    return {"total": total, "bytes": size, "dtypes": dict(dtypes), "notes": notes}


# ---------- 输出 ----------

def human(n):
    for unit, k in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= k:
            return f"{n / k:.2f}{unit}"
    return str(n)


def render(spec, tensors, config, shards, expect=None):
    s = summarize(tensors, config)
    out = [f"# 参数地图:{spec}", ""]
    out.append(f"- 张量 {len(tensors)} 个,分布在 {len(shards)} 个文件")
    out.append(f"- 参数总量:{s['total']:,}({human(s['total'])})")
    out.append(f"- 按存储类型:" + ",".join(f"{d} {human(n)}" for d, n in sorted(s["dtypes"].items())) +
               f";权重文件约 {s['bytes'] / 2**30:.2f} GiB")
    if expect:
        diff = (s["total"] - expect) / expect * 100
        out.append(f"- 对照论文:{expect:,}({human(expect)}),差 {diff:+.2f}%" +
                   ("" if abs(diff) < 1 else " ← 差距超过 1%,查是否共用了嵌入、是否算了偏置或归一化参数、论文是否只算非嵌入参数"))
    out.append("")
    if config:
        out.append("## 配置要点(config.json)")
        out.append("")
        for k in CONFIG_KEYS:
            if k in config:
                out.append(f"- `{k}`:{json.dumps(config[k], ensure_ascii=False)}")
        out.append("")
    if s["notes"]:
        out.append("## 值得注意")
        out.append("")
        out += [f"- {n}" for n in s["notes"]]
        out.append("")
    out.append("## 按层归并的参数表")
    out.append("")
    out.append("| 权重(层号折成 {i}) | 形状 | 份数 | 参数量 | 论文符号 |")
    out.append("|---|---|---|---|---|")
    for g in group(tensors):
        shape = "×".join(map(str, g["shape"])) if g["uniform"] else "不一:" + "; ".join("×".join(map(str, x)) for x in g["shapes"][:3])
        out.append(f"| `{g['pattern']}` | {shape} | {g['count']} | {human(g['params'])} | |")
    out.append("")
    out.append("填\"论文符号\"一列:每个权重对应论文哪个公式里的哪个符号(如 W_Q、W_up);对不上的,记进差异表。")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="读 safetensors 头信息,生成参数地图(不下载权重、不需要 PyTorch)")
    ap.add_argument("source", help="本地模型目录 / .safetensors 文件 / hf:owner/name[@rev] / URL")
    ap.add_argument("--expect", type=float, help="论文里写的参数量(如 1.5e9),用来核对")
    ap.add_argument("--json", help="同时写出结构化结果")
    args = ap.parse_args(argv)
    try:
        tensors, config, shards = load(args.source)
    except (OSError, ValueError, urllib.error.URLError) as e:
        print(f"读取失败:{e}", file=sys.stderr)
        if args.source.startswith("hf:"):
            print("访问不了 huggingface.co 时,可以先在别处下载 config.json 与 *.safetensors 的头,或改用本地目录。",
                  file=sys.stderr)
        return 2
    print(render(args.source, tensors, config, shards, int(args.expect) if args.expect else None))
    if args.json:
        s = summarize(tensors, config)
        groups = [{k: v for k, v in g.items() if k != "shapes"} | {"shapes": [list(x) for x in g["shapes"]]}
                  for g in group(tensors)]
        Path(args.json).write_text(json.dumps({"summary": s, "config": config, "groups": groups,
                                               "shards": shards}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
