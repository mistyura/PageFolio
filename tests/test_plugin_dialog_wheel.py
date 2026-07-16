# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""``PluginDialog`` のマウスホイール束縛の回帰テスト（WR-02・06-REVIEW.md）。

`<Destroy>` はビンドタグ経由で子ウィジェット破棄時にも伝播するため、
「🔄 再検出」による行 Frame の再構築（`_refresh_list()`）で誤って
グローバルなマウスホイール束縛が解除されないことを検証する。
`tests/test_toast.py` と同方針でモジュール共有の隠しルートを使う。
"""

import pytest

tk = pytest.importorskip("tkinter")

import pagefolio  # noqa: E402
from pagefolio.dialogs.plugin import PluginDialog  # noqa: E402


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except tk.TclError:
        pass


class _FakeApp:
    """`PluginDialog` 単体テスト用の最小スタブ。"""

    def __init__(self):
        self.lang = "ja"
        self.plugin_manager = pagefolio.PluginManager()
        self.font_size = 10
        self.settings = {}

    def _reload_plugins(self):
        pass


def test_rescan_does_not_break_global_mousewheel_binding(tk_root):
    """WR-02: 「🔄 再検出」（`_rescan()` → `_refresh_list()`）で行 Frame が
    破棄されても、ダイアログ自身が破棄されない限りグローバルな
    `<MouseWheel>` 束縛は解除されないままであること。
    """
    app = _FakeApp()
    dlg = PluginDialog(tk_root, app)
    try:
        canvas = dlg._list_canvas

        # <Enter> をシミュレートしてグローバル束縛を有効化する
        canvas.event_generate("<Enter>")
        dlg.update()
        assert canvas.bind_all("<MouseWheel>") != ""

        # 再検出は内部で _list_inner の子ウィジェット（行 Frame / 空表示ラベル）
        # を破棄してから再構築する。この破棄が <Destroy> をダイアログの
        # bindtag へ伝播させても、束縛解除はダイアログ自身の破棄時のみに
        # 限定されているべき。
        dlg._rescan()
        dlg.update()

        assert canvas.bind_all("<MouseWheel>") != ""
    finally:
        dlg.destroy()


def test_dialog_destroy_still_unbinds_global_mousewheel(tk_root):
    """ダイアログ自身が破棄される場合は引き続きグローバル束縛が解除される
    こと（ガード条件が過剰に広くなっていないことの確認）。
    """
    app = _FakeApp()
    dlg = PluginDialog(tk_root, app)
    canvas = dlg._list_canvas

    canvas.event_generate("<Enter>")
    dlg.update()
    assert canvas.bind_all("<MouseWheel>") != ""

    dlg.destroy()
    tk_root.update()

    assert canvas.bind_all("<MouseWheel>") == ""
