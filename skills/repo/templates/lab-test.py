"""{NN} {组件名} 的测试。每级一组,测试名带级别,`-k L1` 只跑一级。

impl 默认从本目录导入(用户写的 impl.py);
备课时用 LAB_IMPL=.answers/{NN}-{组件} 指向参考实现,验证测试本身是对的。
"""
import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 每个组件都有 impl.py,按文件路径加载并起唯一模块名,一起跑多个组件时才不会串
_dir = Path(os.environ["LAB_IMPL"]).resolve() if os.environ.get("LAB_IMPL") else HERE
_spec = importlib.util.spec_from_file_location(f"impl_{HERE.name.replace('-', '_')}", _dir / "impl.py")
impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(impl)
ORACLE = HERE.parent / "oracle"


def test_L0_{行为}():
    out = impl.{函数}({极小输入})
    assert out == {手算的期望}, "{这一级的概念:为什么期望是这个}"


def test_L0_{不变量}():
    out = impl.{函数}({输入})
    assert {性质}, "{不变量的含义}"


def test_L1_{退化时与 L0 一致}():
    assert impl.{L1 函数}({退化输入}) == impl.{函数}({同一输入}), "接口不变:退化条件下应与 L0 相同"


def test_L{n}_matches_oracle():
    import json
    expected = json.loads((ORACLE / "{文件}.json").read_text())
    assert impl.{函数}({oracle 输入}) == expected, "与原仓库同输入下的输出一致"
