"""テスト間 GC バリア（tests/conftest.py の teardown フック）の回帰ガード。

バリアが各テストの後始末直後にメインスレッドで gc.collect() することを、
Tk 非依存・決定的に確認する。
自動GCを止めた状態で循環ガベージを作り、次のテスト開始時点で回収済みである
ことを検証する。バリアが無ければ自動GCが止まっているため回収されず、
test_b が必ず失敗する。

背景（tcl-leak-test-ocr）: tkinter の Tk root / Variable は循環ガベージとして
テスト終了後も残り、その回収が run_parallel 等のワーカースレッドの GC で起きると
`RuntimeWarning: the Tcl interpreter is leaked ...`（gh-83274）と
`Variable.__del__` の RuntimeError が無関係なテストに帰属する。
バリアを外すと GC 発火位置次第でこの警告が再発するため、バリア自体の存在を検知する。
"""

import gc
import weakref

import pytest


class _Cycle:
    def __init__(self):
        self.me = self  # 参照カウントでは解放されない循環


_state = {}


@pytest.fixture(scope="module", autouse=True)
def _restore_gc():
    was_enabled = gc.isenabled()
    yield
    if was_enabled:
        gc.enable()


class TestTeardownBarrier:
    """定義順に test_a → test_b の順で実行されることに依存する。

    xdist / ランダム順は未使用。
    """

    def test_a_leaves_cyclic_garbage(self):
        gc.disable()
        obj = _Cycle()
        _state["ref"] = weakref.ref(obj)
        del obj
        assert _state["ref"]() is not None

    def test_b_barrier_collected_it(self):
        ref = _state.get("ref")
        assert ref is not None, "test_a が先に実行されていない"
        assert ref() is None, "teardown 後のメインスレッド gc.collect() が働いていない"
