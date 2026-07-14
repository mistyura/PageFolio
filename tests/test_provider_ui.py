# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR-UI-01/02/03 向け自動回帰テスト

各ギャップに対して Tk ウィジェット生成を行わず、
ロジック層のみを検証するユニットテスト群。
"""

import types

import pytest

from pagefolio.ocr import (
    DEFAULT_SUMMARY_PROMPT,
    OCR_PROMPTS,
    PROVIDER_SUMMARY_PROMPTS,
    resolve_ocr_prompt,
    resolve_summary_prompt,
)
from pagefolio.ocr_providers import ClaudeProvider

# ══════════════════════════════════════════════════════════════
#  OCR-UI-01: _model_supports_effort（effort/temperature 切替判定）
# ══════════════════════════════════════════════════════════════


def _get_model_supports_effort():
    """LLMConfigDialog._model_supports_effort の非バインドメソッドを返す。

    _build() を呼ばずにメソッドだけを取り出すため Tk 生成は発生しない。
    """
    from pagefolio.dialogs.llm_config import LLMConfigDialog

    return LLMConfigDialog._model_supports_effort


class TestModelSupportsEffort:
    """OCR-UI-01: _model_supports_effort の動作検証。"""

    @pytest.fixture(autouse=True)
    def setup_stub(self):
        """メソッドと最小スタブ self を準備する。"""
        self.fn = _get_model_supports_effort()
        self.stub = types.SimpleNamespace()

    def test_haiku_returns_false(self):
        """haiku モデルは effort 非対応（False）であることを確認する。"""
        assert self.fn(self.stub, "claude-haiku-4-5") is False

    def test_sonnet_returns_true(self):
        """claude-sonnet-4-6 は EFFORT_MODELS に含まれるため True を返す。"""
        assert self.fn(self.stub, "claude-sonnet-4-6") is True

    def test_opus_returns_true(self):
        """claude-opus-4-8 は EFFORT_MODELS に含まれるため True を返す。"""
        assert self.fn(self.stub, "claude-opus-4-8") is True

    def test_unknown_sonnet_prefix_returns_false(self):
        """M-3: EFFORT_MODELS にない sonnet 系モデルは False（prefix 判定撤廃）。"""
        assert self.fn(self.stub, "claude-sonnet-99-0") is False

    def test_unknown_opus_prefix_returns_false(self):
        """M-3: EFFORT_MODELS にない opus 系モデルは False（prefix 判定撤廃）。"""
        assert self.fn(self.stub, "claude-opus-99-0") is False

    def test_haiku_variant_always_false_d16(self):
        """'haiku' を含む名称（将来バージョン含む）は必ず False（D-16）。"""
        assert self.fn(self.stub, "claude-haiku-99-0") is False

    def test_empty_model_returns_false(self):
        """モデル未設定（空文字列）は False を返す。"""
        assert self.fn(self.stub, "") is False


# ══════════════════════════════════════════════════════════════
#  OCR-UI-02: _update_ocr_buttons_state（OCR ボタン無効化ロジック）
# ══════════════════════════════════════════════════════════════


class _ButtonStub:
    """ttk.Button.state() の呼び出しを記録するスタブ。"""

    def __init__(self):
        self.last_state = None

    def state(self, flags):
        """状態フラグを記録する。"""
        self.last_state = flags


def _call_update_ocr_buttons_state(settings, doc, ocr_buttons=None):
    """PDFEditorApp._update_ocr_buttons_state を最小スタブで呼び出す。

    Tk を生成せず settings/doc/_ocr_buttons だけを持つ名前空間で呼ぶ。
    """
    from pagefolio.app import PDFEditorApp

    stub = types.SimpleNamespace(
        settings=settings,
        doc=doc,
    )
    if ocr_buttons is not None:
        stub._ocr_buttons = ocr_buttons
    PDFEditorApp._update_ocr_buttons_state(stub)
    return stub


class TestUpdateOcrButtonsState:
    """OCR-UI-02: _update_ocr_buttons_state の動作検証。"""

    def test_provider_off_with_doc_is_disabled(self):
        """ocr_provider=='off' のとき doc が開いていても OCR ボタンは disabled。"""
        btn = _ButtonStub()
        _call_update_ocr_buttons_state(
            settings={"ocr_provider": "off"},
            doc=object(),
            ocr_buttons=[btn],
        )
        assert btn.last_state == ["disabled"]

    def test_provider_off_without_doc_is_disabled(self):
        """ocr_provider=='off' かつ doc なしでも disabled。"""
        btn = _ButtonStub()
        _call_update_ocr_buttons_state(
            settings={"ocr_provider": "off"},
            doc=None,
            ocr_buttons=[btn],
        )
        assert btn.last_state == ["disabled"]

    def test_provider_lmstudio_with_doc_is_normal(self):
        """ocr_provider=='lmstudio' かつ doc が開いていれば OCR ボタンは !disabled。"""
        btn = _ButtonStub()
        _call_update_ocr_buttons_state(
            settings={"ocr_provider": "lmstudio"},
            doc=object(),
            ocr_buttons=[btn],
        )
        assert btn.last_state == ["!disabled"]

    def test_provider_claude_with_doc_is_normal(self):
        """ocr_provider=='claude' かつ doc が開いていれば OCR ボタンは !disabled。"""
        btn = _ButtonStub()
        _call_update_ocr_buttons_state(
            settings={"ocr_provider": "claude"},
            doc=object(),
            ocr_buttons=[btn],
        )
        assert btn.last_state == ["!disabled"]

    def test_provider_lmstudio_without_doc_is_disabled(self):
        """ocr_provider=='lmstudio' でも doc が None のとき disabled。"""
        btn = _ButtonStub()
        _call_update_ocr_buttons_state(
            settings={"ocr_provider": "lmstudio"},
            doc=None,
            ocr_buttons=[btn],
        )
        assert btn.last_state == ["disabled"]

    def test_no_ocr_buttons_attr_does_not_raise(self):
        """_ocr_buttons 属性が存在しなくても AttributeError を発生させない。"""
        stub = types.SimpleNamespace(
            settings={"ocr_provider": "off"},
            doc=None,
        )
        from pagefolio.app import PDFEditorApp

        PDFEditorApp._update_ocr_buttons_state(stub)

    def test_multiple_buttons_all_get_same_state(self):
        """複数の OCR ボタンがすべて同じ状態に更新されることを確認する。"""
        btns = [_ButtonStub() for _ in range(3)]
        _call_update_ocr_buttons_state(
            settings={"ocr_provider": "off"},
            doc=object(),
            ocr_buttons=btns,
        )
        for b in btns:
            assert b.last_state == ["disabled"]


# ══════════════════════════════════════════════════════════════
#  OCR-UI-03: OCRDialog クラウド/コスト/セッションキー/確認ロジック
# ══════════════════════════════════════════════════════════════


def _make_dialog_stub(settings, provider=None, page_indices=None):
    """OCRDialog のロジックメソッドだけをテストするスタブを返す。

    Tk ウィジェット生成を一切行わず、各メソッドを直接バインドして呼び出す。
    """
    from pagefolio.ocr_dialog import OCRDialog

    stub = types.SimpleNamespace(
        app=types.SimpleNamespace(settings=dict(settings)),
        provider=provider,
        page_indices=list(page_indices or [0, 1, 2]),
    )
    stub._is_cloud_provider = lambda settings=None: OCRDialog._is_cloud_provider(
        stub, settings
    )
    stub._estimate_cost = lambda m, c: OCRDialog._estimate_cost(stub, m, c)
    return stub


def _read_llm_config_package_source():
    """llm_config パッケージ配下の全 .py を sorted glob で連結して返す。

    Phase 1（01-04）で pagefolio/dialogs/llm_config.py が
    pagefolio/dialogs/llm_config/ パッケージへ分割されたため、単一ファイルの
    read_text ではソーススキャンテストが FileNotFoundError になる。
    パッケージ全体を連結することで既存の substring/count アサーションの
    意図（該当シンボル/呼び出しが llm_config 実装のどこかに存在する）を
    そのまま保存する。
    """
    import pathlib

    pkg_dir = pathlib.Path("pagefolio/dialogs/llm_config")
    return "".join(p.read_text(encoding="utf-8") for p in sorted(pkg_dir.glob("*.py")))


class TestLLMConfigProviderValues:
    """Task 2 回帰: provider_combo に gemini が含まれることを確認。"""

    def test_provider_combo_includes_gemini(self):
        """provider_combo の values に 'gemini' が含まれる（OCR-API-02）。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        src = _read_llm_config_package_source()
        assert '"gemini"' in src, (
            "provider_combo の values に 'gemini' が含まれていない"
        )
        fn = LLMConfigDialog._model_supports_effort
        assert callable(fn)

    def test_gemini_section_frame_exists_in_source(self):
        """llm_config パッケージに gemini_section_frame の定義が存在する。"""
        src = _read_llm_config_package_source()
        assert "gemini_section_frame" in src
        assert "gemini_model_var" in src
        assert "_on_provider_change" in src


class TestLLMConfigDialogMRO:
    """Pitfall 3 の headless ガード: tk.Toplevel の MRO 破壊を自動検知する。

    Tk をインスタンス化せず LLMConfigDialog.__mro__ を検査するのみのため、
    ヘッドレス CI でも実行できる（実機描画目視は v1.8.0 スコープ外）。
    """

    def test_tk_toplevel_is_last_in_mro(self):
        """tk.Toplevel が3 Mixin すべてより後ろ（MRO 末尾側）にある。"""
        import tkinter as tk

        from pagefolio.dialogs.llm_config import LLMConfigDialog

        mro = LLMConfigDialog.__mro__
        toplevel_index = mro.index(tk.Toplevel)
        mixin_indices = [
            mro.index(base)
            for base in LLMConfigDialog.__bases__
            if base is not tk.Toplevel
        ]
        assert toplevel_index > max(mixin_indices)

    def test_init_is_consolidated_in_dialog_mixin(self):
        """__init__ が DialogMixin に集約されている（他 Mixin は持たない）。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog
        from pagefolio.dialogs.llm_config.dialog import DialogMixin

        assert LLMConfigDialog.__init__ is DialogMixin.__init__

    def test_key_methods_exist_on_llm_config_dialog(self):
        """_build/_apply/_on_provider_change/_fetch_models_async が存在する。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        for method_name in (
            "_build",
            "_apply",
            "_on_provider_change",
            "_fetch_models_async",
        ):
            assert hasattr(LLMConfigDialog, method_name), (
                f"LLMConfigDialog に {method_name} が存在しない"
            )


class TestIsCloudProvider:
    """OCR-UI-03: _is_cloud_provider の動作検証。"""

    def test_claude_settings_returns_true(self):
        """settings.ocr_provider == 'claude' のとき True を返す。"""
        stub = _make_dialog_stub(settings={"ocr_provider": "claude"})
        assert stub._is_cloud_provider() is True

    def test_lmstudio_settings_returns_false(self):
        """settings.ocr_provider == 'lmstudio' のとき False を返す。"""
        stub = _make_dialog_stub(settings={"ocr_provider": "lmstudio"})
        assert stub._is_cloud_provider() is False

    def test_off_settings_returns_false(self):
        """settings.ocr_provider == 'off' のとき False を返す。"""
        stub = _make_dialog_stub(settings={"ocr_provider": "off"})
        assert stub._is_cloud_provider() is False

    def test_claude_provider_instance_returns_true(self):
        """provider が ClaudeProvider インスタンスのとき設定に関わらず True。"""
        provider = ClaudeProvider(api_key="x", model="claude-haiku-4-5")
        stub = _make_dialog_stub(
            settings={"ocr_provider": "lmstudio"},
            provider=provider,
        )
        assert stub._is_cloud_provider() is True

    def test_gemini_settings_returns_true(self):
        """settings.ocr_provider == 'gemini' のとき True を返す（Pitfall-F）。"""
        stub = _make_dialog_stub(settings={"ocr_provider": "gemini"})
        assert stub._is_cloud_provider() is True

    def test_gemini_provider_instance_returns_true(self):
        """provider が GeminiProvider インスタンスのとき設定に関わらず True。"""
        from pagefolio.ocr_providers import GeminiProvider

        provider = GeminiProvider(api_key="x", model="gemini-2.5-flash")
        stub = _make_dialog_stub(
            settings={"ocr_provider": "lmstudio"},
            provider=provider,
        )
        assert stub._is_cloud_provider() is True


class TestEstimateCost:
    """OCR-UI-03: _estimate_cost の動作検証。"""

    def test_haiku_1page_returns_correct_cost_string(self):
        """haiku モデルで 1 ページの概算コストを返すことを確認する。

        実装は :.3f フォーマット（小数 3 桁）なので "0.004" を含む。
        """
        stub = _make_dialog_stub(settings={})
        result = stub._estimate_cost("claude-haiku-4-5", 1)
        # "約 $..." または "$..." 形式を含む
        assert "$" in result
        # haiku: (1600*1.0 + 500*5.0) / 1_000_000 = 0.0041 → :.3f で "0.004"
        assert "0.004" in result

    def test_sonnet_more_expensive_than_haiku(self):
        """sonnet は haiku より高価であることを確認する（相対比較）。"""
        stub = _make_dialog_stub(settings={})
        haiku_str = stub._estimate_cost("claude-haiku-4-5", 2)
        sonnet_str = stub._estimate_cost("claude-sonnet-4-6", 2)
        haiku_val = float(haiku_str.replace("約 $", "").replace(" 程度", ""))
        sonnet_val = float(sonnet_str.replace("約 $", "").replace(" 程度", ""))
        assert sonnet_val > haiku_val

    def test_cost_proportional_to_page_count(self):
        """ページ数を 2 倍にするとコストも増加することを確認する。

        実装は :.3f 丸めがあるため完全一致は保証されないが
        2 ページは 1 ページより高い（単調増加）ことを確認する。
        """
        stub = _make_dialog_stub(settings={})
        c1 = stub._estimate_cost("claude-sonnet-4-6", 1)
        c2 = stub._estimate_cost("claude-sonnet-4-6", 2)

        def parse_cost(s):
            """'約 $X.XXX 程度' から float を取り出す。"""
            return float(s.replace("約 $", "").replace(" 程度", "").strip())

        v1 = parse_cost(c1)
        v2 = parse_cost(c2)
        assert v2 > v1

    def test_opus_1page_returns_correct_cost_string(self):
        """opus モデルで 1 ページの概算コストが正しく計算される。

        実装は :.3f 丸めなので 0.0205 → "0.021" を含む。
        """
        stub = _make_dialog_stub(settings={})
        result = stub._estimate_cost("claude-opus-4-8", 1)
        # opus: (1600*5.0 + 500*25.0) / 1_000_000 = 0.0205 → :.3f で "0.021"
        assert "$" in result
        assert "0.021" in result


class TestCheckCloudApiKey:
    """V171-KEY-02/03: _check_cloud_api_key（撤去された _ensure_cloud_session_key の
    後継）の動作検証。値の収集は一切行わず _resolve_api_key の解決可否のみを
    確認する軽量ゲートであることを担保する。
    """

    _ALL_ENV_VARS = (
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "RUNPOD_API_KEY",
    )

    def _make_stub(self, ocr_provider, session_keys=None):
        """_check_cloud_api_key 呼び出し用スタブを返す。

        OCRDialog._check_cloud_api_key は self.app.settings /
        self.app._session_api_keys / self._L（messagebox の parent）を参照する。
        """
        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog

        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(
                settings={"ocr_provider": ocr_provider},
                _session_api_keys=dict(session_keys or {}),
            ),
            provider=None,
            _L=LANG["ja"],
        )
        stub._is_cloud_provider = lambda settings=None: OCRDialog._is_cloud_provider(
            stub, settings
        )
        stub._check_cloud_api_key = lambda settings=None: (
            OCRDialog._check_cloud_api_key(stub, settings)
        )
        return stub

    def _clear_all_env(self, monkeypatch):
        for var in self._ALL_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

    def test_non_cloud_provider_returns_true_without_messagebox(self, monkeypatch):
        """lmstudio 等の非クラウドプロバイダは常に True・messagebox 非呼び出し。"""
        stub = self._make_stub("lmstudio")
        called = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.showerror",
            lambda *a, **kw: called.append((a, kw)),
        )
        assert stub._check_cloud_api_key() is True
        assert called == []

    @pytest.mark.parametrize("provider", ["claude", "gemini", "runpod"])
    def test_unresolved_shows_error_and_returns_false(self, monkeypatch, provider):
        """入力値・環境変数とも未設定なら messagebox.showerror が呼ばれ False を
        返す。"""
        self._clear_all_env(monkeypatch)
        stub = self._make_stub(provider)
        captured = {}

        def mock_showerror(title, msg, parent=None):
            captured["title"] = title
            captured["msg"] = msg
            captured["parent"] = parent

        monkeypatch.setattr("pagefolio.ocr_dialog.messagebox.showerror", mock_showerror)
        assert stub._check_cloud_api_key() is False
        assert captured  # messagebox.showerror が1回呼ばれた
        assert captured["parent"] is stub

    @pytest.mark.parametrize("provider", ["claude", "gemini", "runpod"])
    def test_session_key_resolves_without_messagebox(self, monkeypatch, provider):
        """入力値（セッションキー）が設定済みなら True・messagebox 非呼び出し。"""
        self._clear_all_env(monkeypatch)
        stub = self._make_stub(provider, session_keys={provider: "dummy-test-key"})
        called = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.showerror",
            lambda *a, **kw: called.append((a, kw)),
        )
        assert stub._check_cloud_api_key() is True
        assert called == []

    @pytest.mark.parametrize(
        "provider, env_var",
        [
            ("claude", "ANTHROPIC_API_KEY"),
            ("gemini", "GEMINI_API_KEY"),
            ("runpod", "RUNPOD_API_KEY"),
        ],
    )
    def test_env_var_resolves_without_messagebox(self, monkeypatch, provider, env_var):
        """環境変数のみ設定済みでも True・messagebox 非呼び出し（フォールバック）。"""
        self._clear_all_env(monkeypatch)
        monkeypatch.setenv(env_var, "dummy-env-key")
        stub = self._make_stub(provider)
        called = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.showerror",
            lambda *a, **kw: called.append((a, kw)),
        )
        assert stub._check_cloud_api_key() is True
        assert called == []

    def test_runpod_session_key_does_not_use_claude_slot(self, monkeypatch):
        """RunPod のセッションキーが claude スロットへ誤格納されない（Pitfall 1 回帰）。

        _check_cloud_api_key は値の収集を行わないため、claude スロットのみに
        キーがある状態で runpod を選択すると解決不能（誤って claude 経由で
        解決してしまわない）ことを確認する。
        """
        self._clear_all_env(monkeypatch)
        stub = self._make_stub("runpod", session_keys={"claude": "claude-only-key"})
        called = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.showerror",
            lambda *a, **kw: called.append((a, kw)),
        )
        assert stub._check_cloud_api_key() is False
        assert called


class TestConfirmCost:
    """OCR-UI-03: _confirm_cost の動作検証（messagebox モック）。"""

    def _make_confirm_stub(
        self,
        page_indices,
        model="claude-sonnet-4-6",
        provider="claude",
        runpod_url=None,
        runpod_model=None,
    ):
        """_confirm_cost / _confirm_summary_cost 呼び出し用スタブを返す。

        OCRDialog._confirm_cost / _confirm_summary_cost は self.app.settings /
        self.page_indices / self._L / self（parent として messagebox に渡す）を
        参照する。provider="runpod" の場合、runpod_url / runpod_model を
        settings へ差し込める（CR-01 回帰テスト用）。
        """
        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog

        settings = {"ocr_provider": provider, "claude_model": model}
        if runpod_url is not None:
            settings["runpod_url"] = runpod_url
        if runpod_model is not None:
            settings["runpod_model"] = runpod_model

        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings=settings),
            page_indices=list(page_indices),
            _L=LANG["ja"],
        )
        stub._estimate_cost = lambda m, c: OCRDialog._estimate_cost(stub, m, c)
        stub._confirm_cost = lambda: OCRDialog._confirm_cost(stub)
        stub._confirm_summary_cost = lambda cc: OCRDialog._confirm_summary_cost(
            stub, cc
        )
        return stub

    def test_confirm_cost_calls_askyesno(self, monkeypatch):
        """_confirm_cost は messagebox.askyesno を呼び出すことを確認する。"""
        stub = self._make_confirm_stub(page_indices=[0, 1, 2])
        captured = {}

        def mock_askyesno(title, msg, parent=None):
            """モック: 呼び出し引数を記録して True を返す。"""
            captured["title"] = title
            captured["msg"] = msg
            captured["parent"] = parent
            return True

        monkeypatch.setattr("pagefolio.ocr_dialog.messagebox.askyesno", mock_askyesno)
        result = stub._confirm_cost()
        assert result is True
        # ホスト名が含まれることを確認（D-12）
        assert "api.anthropic.com" in captured["msg"]
        # ページ数が含まれることを確認（D-12）
        assert "3" in captured["msg"]
        # コスト概算が含まれることを確認（D-12）
        assert "$" in captured["msg"]

    def test_confirm_cost_cancel_returns_false(self, monkeypatch):
        """ユーザーがキャンセルしたとき _confirm_cost は False を返す。"""
        stub = self._make_confirm_stub(page_indices=[0])
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda *a, **kw: False,
        )
        assert stub._confirm_cost() is False

    def test_confirm_cost_ok_returns_true(self, monkeypatch):
        """ユーザーが OK を選択したとき _confirm_cost は True を返す。"""
        stub = self._make_confirm_stub(page_indices=[0])
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda *a, **kw: True,
        )
        assert stub._confirm_cost() is True

    def test_confirm_cost_single_page_includes_count(self, monkeypatch):
        """1 ページ選択時、確認メッセージにページ数と $ が含まれることを確認する。"""
        stub = self._make_confirm_stub(page_indices=[0], model="claude-haiku-4-5")
        captured_msg = {}

        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda title, msg, parent=None: captured_msg.update({"msg": msg}) or True,
        )
        stub._confirm_cost()
        assert "1" in captured_msg["msg"]
        assert "$" in captured_msg["msg"]

    def test_confirm_cost_runpod_shows_runpod_host(self, monkeypatch):
        """CR-01: RunPod選択時、_confirm_cost は runpod_url を送信先として開示し
        api.anthropic.com を表示しない。
        """
        stub = self._make_confirm_stub(
            page_indices=[0],
            provider="runpod",
            runpod_url="http://runpod.example/x",
            runpod_model="qwen-vl",
        )
        captured = {}
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost()
        assert "http://runpod.example/x" in captured["msg"]
        assert "api.anthropic.com" not in captured["msg"]

    def test_confirm_summary_cost_runpod_shows_runpod_host(self, monkeypatch):
        """CR-01: RunPod選択時、_confirm_summary_cost も runpod_url を送信先として
        開示し api.anthropic.com を表示しない。
        """
        stub = self._make_confirm_stub(
            page_indices=[0],
            provider="runpod",
            runpod_url="http://runpod.example/x",
            runpod_model="qwen-vl",
        )
        captured = {}
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_summary_cost(1000)
        assert "http://runpod.example/x" in captured["msg"]
        assert "api.anthropic.com" not in captured["msg"]

    def test_confirm_cost_runpod_url_unset_shows_placeholder(self, monkeypatch):
        """runpod_url 未設定時、host は llm_runpod_host_unset のプレースホルダに
        なり api.anthropic.com へフォールバックしない。
        """
        from pagefolio.constants import LANG

        stub = self._make_confirm_stub(
            page_indices=[0],
            provider="runpod",
            runpod_url="",
            runpod_model="qwen-vl",
        )
        captured = {}
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost()
        assert LANG["ja"]["llm_runpod_host_unset"] in captured["msg"]
        assert "api.anthropic.com" not in captured["msg"]


# ══════════════════════════════════════════════════════════════
#  V16-UI-01: _sync_param_vars_from_settings（数値パラメータの全プロバイダ共通同期）
# ══════════════════════════════════════════════════════════════


class _VarStub:
    """tk Variable の .set() 呼び出し値を記録するスタブ。"""

    def __init__(self):
        self.value = None

    def set(self, value):
        """set された値を記録する。"""
        self.value = value


def _make_sync_stub(settings):
    """_sync_param_vars_from_settings を Tk 生成なしで呼ぶスタブを返す。"""
    from pagefolio.ocr_dialog import OCRDialog

    stub = types.SimpleNamespace(
        app=types.SimpleNamespace(settings=dict(settings)),
        scale_var=_VarStub(),
        timeout_var=_VarStub(),
        max_tokens_var=_VarStub(),
        temperature_var=_VarStub(),
    )
    stub._sync_param_vars_from_settings = lambda: (
        OCRDialog._sync_param_vars_from_settings(stub)
    )
    return stub


class TestSyncParamVarsFromSettings:
    """V16-UI-01: 数値パラメータが全プロバイダで settings 値へ同期されることを検証。"""

    def test_all_vars_set_from_settings(self):
        """4 変数すべてが settings の ocr_* 値で .set() される。"""
        stub = _make_sync_stub(
            settings={
                "ocr_scale": 2.5,
                "ocr_timeout": 300,
                "ocr_max_tokens": 4096,
                "ocr_temperature": 0.7,
            }
        )
        stub._sync_param_vars_from_settings()
        assert stub.scale_var.value == 2.5
        assert stub.timeout_var.value == 300
        assert stub.max_tokens_var.value == 4096
        assert stub.temperature_var.value == 0.7

    def test_missing_keys_fall_back_to_defaults(self):
        """settings 欠損時は llm_config と整合する既定値へフォールバックする。"""
        stub = _make_sync_stub(settings={})
        stub._sync_param_vars_from_settings()
        assert stub.scale_var.value == 1.5
        assert stub.timeout_var.value == 120
        assert stub.max_tokens_var.value == -1
        assert stub.temperature_var.value == 0.1

    def test_sync_called_for_cloud_provider_settings(self):
        """claude/gemini 等の provider 設定でも全変数が同期される（分岐外実行）。"""
        stub = _make_sync_stub(
            settings={
                "ocr_provider": "claude",
                "ocr_scale": 3.0,
                "ocr_timeout": 60,
                "ocr_max_tokens": 8192,
                "ocr_temperature": 0.0,
            }
        )
        stub._sync_param_vars_from_settings()
        assert stub.scale_var.value == 3.0
        assert stub.timeout_var.value == 60
        assert stub.max_tokens_var.value == 8192
        assert stub.temperature_var.value == 0.0


def _make_apply_llm_settings_stub(settings, provider=None, app_extra=None):
    """_apply_llm_settings を Tk 生成なしで呼ぶスタブを返す。

    D-07: _maybe_show_lang_fallback_notice が参照する属性
    （_lang_fallback_notice_var/_lang_fallback_label/_L）も併せて用意し、
    provider 再生成の try/except に AttributeError が黙って飲み込まれない
    ようにする（試験対象コードパスを実際に通す）。

    app_extra: app 側 SimpleNamespace に追加する属性の dict（L-6j の
    _update_ocr_buttons_state スタブ差し込み等に使用）。省略時は既存の
    app（_update_ocr_buttons_state 属性なし）のまま後方互換を保つ。
    """
    app_kwargs = {"settings": dict(settings)}
    if app_extra:
        app_kwargs.update(app_extra)
    stub = types.SimpleNamespace(
        app=types.SimpleNamespace(**app_kwargs),
        custom_prompt="旧プロンプト",
        provider=provider or ClaudeProvider(api_key="x", model="claude-sonnet-4-6"),
        concurrency=1,
        _refresh_provider_dependent_ui=lambda: None,
        _sync_param_vars_from_settings=lambda: None,
        _update_summary_btn_state=lambda: None,
        progress_var=_VarStub(),
        url_var=_VarStub(),
        model_var=_VarStub(),
        _lang_fallback_notice_var=_VarStub(),
        _lang_fallback_label=types.SimpleNamespace(
            winfo_ismapped=lambda: False,
            pack=lambda **kw: None,
            pack_forget=lambda: None,
        ),
        progress_bar=object(),
        _L={
            "ocr_tesseract_lang_fallback_notice": (
                "⚠ 指定言語 {requested} は利用不可のため {effective} で実行します"
            )
        },
    )
    return stub


class TestApplyLlmSettingsCustomPromptSync:
    """LLM 設定ダイアログでカスタムプロンプトを変更した直後の OCR 実行が
    最新値を使うことを検証する回帰テスト（1回前のプロンプトが使われるバグの修正）。
    """

    def test_custom_prompt_refreshed_after_apply(self, monkeypatch):
        """_apply_llm_settings 後、custom_prompt が app.settings の最新値になる。"""
        from pagefolio.ocr_dialog import OCRDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        stub = _make_apply_llm_settings_stub(
            settings={"ocr_provider": "tesseract", "ocr_custom_prompt": ""}
        )
        OCRDialog._apply_llm_settings(
            stub, {"ocr_custom_prompt": "新しいカスタムプロンプト"}
        )
        assert stub.custom_prompt == "新しいカスタムプロンプト"

    def test_custom_prompt_cleared_when_emptied(self, monkeypatch):
        """空欄に変更した場合も self.custom_prompt が空文字へ同期される。"""
        from pagefolio.ocr_dialog import OCRDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        stub = _make_apply_llm_settings_stub(
            settings={
                "ocr_provider": "tesseract",
                "ocr_custom_prompt": "旧プロンプト",
            }
        )
        OCRDialog._apply_llm_settings(stub, {"ocr_custom_prompt": ""})
        assert stub.custom_prompt == ""


class TestApplyLlmSettingsOffToggleButtons:
    """L-6j: "off" 切替時にツールバー OCR ボタン状態が同期されることを確認する。

    _apply_llm_settings が app._update_ocr_buttons_state() を呼ぶこと
    （provider 再生成の正常系・例外系いずれでも呼ばれること・Pitfall 6）を検証する。
    """

    def test_update_ocr_buttons_state_called_on_off(self, monkeypatch):
        """provider='off' へ切替後、app._update_ocr_buttons_state が呼ばれる。"""
        from pagefolio.ocr_dialog import OCRDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        calls = {"n": 0}
        stub = _make_apply_llm_settings_stub(
            settings={"ocr_provider": "off"},
            app_extra={
                "_update_ocr_buttons_state": lambda: calls.__setitem__(
                    "n", calls["n"] + 1
                )
            },
        )
        OCRDialog._apply_llm_settings(stub, {"ocr_provider": "off"})
        assert calls["n"] == 1

    def test_update_ocr_buttons_state_called_even_on_provider_exception(
        self, monkeypatch
    ):
        """provider 再生成が例外で失敗しても呼ばれる（Pitfall 6）。"""
        from pagefolio.ocr_dialog import OCRDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        # tesseract/プラグイン分岐は build_provider を呼ぶため、これを失敗させる
        monkeypatch.setattr(
            "pagefolio.ocr.build_provider",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        calls = {"n": 0}
        stub = _make_apply_llm_settings_stub(
            settings={"ocr_provider": "some-unknown-provider"},
            app_extra={
                "_update_ocr_buttons_state": lambda: calls.__setitem__(
                    "n", calls["n"] + 1
                )
            },
        )
        OCRDialog._apply_llm_settings(stub, {"ocr_provider": "some-unknown-provider"})
        assert calls["n"] == 1

    def test_no_error_when_app_lacks_update_ocr_buttons_state(self, monkeypatch):
        """app に _update_ocr_buttons_state が無くても例外を出さない（後方互換）。"""
        from pagefolio.ocr_dialog import OCRDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        stub = _make_apply_llm_settings_stub(settings={"ocr_provider": "off"})
        # AttributeError 等を出さず正常終了すること
        OCRDialog._apply_llm_settings(stub, {"ocr_provider": "off"})


class _FakeToplevel:
    """winfo_exists/lift/focus_force のみを備えた tk.Toplevel の最小スタブ。"""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._exists = True
        self.lifted = False
        self.focused = False

    def winfo_exists(self):
        return self._exists

    def lift(self):
        self.lifted = True

    def focus_force(self):
        self.focused = True

    def destroy(self):
        self._exists = False


class TestOpenSettingsDoubleLaunchGuard:
    """設定ダイアログの二重起動ガード（同一 SettingsDialog を使い回す）を検証する。

    ガード前は連続クリック等で SettingsDialog が複数生成され、それぞれが
    current_settings の独立したコピーを持つため、片方の変更がもう片方の
    「適用」/「キャンセル」で消失し得た（適用しても更新されないように見える
    バグの一因）。
    """

    def test_second_call_reuses_existing_dialog(self, monkeypatch):
        """既に開いている間は新規 SettingsDialog を生成せず既存を再利用する。"""
        from pagefolio.app import PDFEditorApp

        monkeypatch.setattr("pagefolio.app.SettingsDialog", _FakeToplevel)
        stub = types.SimpleNamespace(
            root=object(),
            settings={},
            _apply_settings=lambda s: None,
            _apply_llm_settings_live=lambda s: None,
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
        )
        PDFEditorApp._open_settings(stub)
        first = stub._settings_dialog
        PDFEditorApp._open_settings(stub)
        second = stub._settings_dialog

        assert first is second
        assert first.lifted is True
        assert first.focused is True

    def test_new_dialog_created_after_previous_closed(self, monkeypatch):
        """前のダイアログが閉じられていれば新規に生成する。"""
        from pagefolio.app import PDFEditorApp

        monkeypatch.setattr("pagefolio.app.SettingsDialog", _FakeToplevel)
        stub = types.SimpleNamespace(
            root=object(),
            settings={},
            _apply_settings=lambda s: None,
            _apply_llm_settings_live=lambda s: None,
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
        )
        PDFEditorApp._open_settings(stub)
        first = stub._settings_dialog
        first.destroy()
        PDFEditorApp._open_settings(stub)
        second = stub._settings_dialog

        assert first is not second


class TestSettingsDialogOpenLlmConfigPersists:
    """設定ダイアログの LLM 設定サブダイアログで「適用」を押した際に
    即座に永続化されることを検証する回帰テスト。

    修正前は on_apply が self.current_settings（コピー）を更新するだけで
    _save_settings を呼んでいなかったため、LLM 設定側で「適用」した直後に
    外側の設定ダイアログを「キャンセル」で閉じると変更が失われていた
    （「LLM設定が『適用』を押しても更新されない」バグ）。
    """

    def test_llm_apply_saves_immediately(self, monkeypatch):
        """LLM 設定ダイアログの on_apply が _save_settings を呼ぶことを確認する。"""
        import types as _types

        from pagefolio.dialogs.settings import SettingsDialog

        saved = {}
        monkeypatch.setattr(
            "pagefolio.settings._save_settings", lambda settings: saved.update(settings)
        )

        captured_kwargs = {}

        class _FakeLLMConfigDialog:
            def __init__(self, *args, **kwargs):
                captured_kwargs.update(kwargs)

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.LLMConfigDialog", _FakeLLMConfigDialog
        )

        stub = _types.SimpleNamespace(
            current_settings={"ocr_provider": "lmstudio", "ocr_custom_prompt": "old"},
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
            _plugin_manager=None,
        )
        SettingsDialog._open_llm_config(stub)

        # on_apply が呼ばれる前は _save_settings は未実行
        assert saved == {}
        on_apply = captured_kwargs["on_apply"]
        on_apply({"ocr_provider": "claude", "ocr_custom_prompt": "new"})

        assert saved.get("ocr_provider") == "claude"
        assert saved.get("ocr_custom_prompt") == "new"
        assert stub.current_settings["ocr_provider"] == "claude"


class TestOpenLlmConfigDoubleLaunchGuard:
    """LLM 設定サブダイアログ（設定画面経由・OCR ダイアログ経由）の
    二重起動ガードを検証する回帰テスト。
    """

    def test_settings_dialog_reuses_existing_llm_config_dialog(self, monkeypatch):
        """SettingsDialog._open_llm_config は既存ダイアログを再利用する。"""
        from pagefolio.dialogs.settings import SettingsDialog

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.LLMConfigDialog", _FakeToplevel
        )
        stub = types.SimpleNamespace(
            current_settings={"ocr_provider": "lmstudio"},
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
            _plugin_manager=None,
        )
        SettingsDialog._open_llm_config(stub)
        first = stub._llm_config_dialog
        SettingsDialog._open_llm_config(stub)
        second = stub._llm_config_dialog

        assert first is second
        assert first.lifted is True

    def test_ocr_dialog_reuses_existing_llm_config_dialog(self, monkeypatch):
        """OCRDialog._open_llm_config は既存ダイアログを再利用する。"""
        from pagefolio.ocr_dialog import OCRDialog

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.LLMConfigDialog", _FakeToplevel
        )
        stub = types.SimpleNamespace(
            _started=False,
            _done=False,
            _summary_running=False,
            app=types.SimpleNamespace(settings={}, plugin_manager=None),
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
            _apply_llm_settings=lambda s: None,
        )
        OCRDialog._open_llm_config(stub)
        first = stub._llm_config_dialog
        OCRDialog._open_llm_config(stub)
        second = stub._llm_config_dialog

        assert first is second
        assert first.lifted is True


# ===== M-8 回帰テスト: SettingsDialog に plugin_manager 引数追加 =====


class TestSettingsDialogPluginManager:
    """M-8: SettingsDialog が plugin_manager を受け取り _plugin_manager に保持する。"""

    def test_settings_dialog_accepts_plugin_manager(self):
        """SettingsDialog.__init__ が plugin_manager 引数を持つ。"""
        import inspect

        from pagefolio.dialogs.settings import SettingsDialog

        sig = inspect.signature(SettingsDialog.__init__)
        assert "plugin_manager" in sig.parameters, (
            "SettingsDialog.__init__ に plugin_manager 引数が存在しない"
        )

    def test_settings_dialog_stores_plugin_manager(self):
        """plugin_manager パラメータが SettingsDialog.__init__ に存在する。"""
        import inspect

        from pagefolio.dialogs.settings import SettingsDialog

        sig_params = list(inspect.signature(SettingsDialog.__init__).parameters.keys())
        assert "plugin_manager" in sig_params


# ══════════════════════════════════════════════════════════════
#  V16-AI-02: resolve_ocr_prompt（プロバイダ別プロンプト解決純関数）
# ══════════════════════════════════════════════════════════════


class TestResolveOcrPrompt:
    """V16-AI-02: resolve_ocr_prompt の優先順位とフォールバックを検証する。

    Tk/ネットワーク非依存の純関数のため、スタブや Tk 生成は一切不要。
    優先順位: custom 上書き > プロバイダ別テンプレート > 汎用 OCR_PROMPTS。
    """

    def test_custom_overrides_provider_template(self):
        """custom_prompt が非空ならプロバイダ別テンプレより優先（成功基準3）。"""
        assert resolve_ocr_prompt("markdown", "claude", "MY CUSTOM") == "MY CUSTOM"

    def test_lmstudio_falls_back_to_generic(self):
        """lmstudio は汎用 OCR_PROMPTS へフォールバックする（Pitfall 4）。"""
        assert resolve_ocr_prompt("text", "lmstudio", "") == OCR_PROMPTS["text"]

    def test_tesseract_falls_back_to_generic(self):
        """tesseract は汎用 OCR_PROMPTS へフォールバックする（Pitfall 4）。"""
        assert resolve_ocr_prompt("text", "tesseract", "") == OCR_PROMPTS["text"]

    def test_claude_markdown_uses_provider_template(self):
        """claude/markdown は汎用プリセットと異なる別テンプレートを返す。"""
        assert resolve_ocr_prompt("markdown", "claude", "") != OCR_PROMPTS["markdown"]

    def test_gemini_markdown_uses_provider_template(self):
        """gemini/markdown は汎用プリセットと異なる別テンプレートを返す。"""
        assert resolve_ocr_prompt("markdown", "gemini", "") != OCR_PROMPTS["markdown"]

    def test_unknown_preset_falls_back_to_text(self):
        """未定義 preset は既定で OCR_PROMPTS['text'] へフォールバックする。"""
        assert resolve_ocr_prompt("zzz", "off", "") == OCR_PROMPTS["text"]


class TestResolveSummaryPrompt:
    """resolve_summary_prompt の優先順位とフォールバックを検証する。

    Tk/ネットワーク非依存の純関数（resolve_ocr_prompt と同型）。
    優先順位: custom 上書き > プロバイダ別テンプレート > DEFAULT_SUMMARY_PROMPT。
    """

    def test_custom_overrides_provider_template(self):
        """custom_prompt が非空ならプロバイダ別テンプレより優先される。"""
        assert resolve_summary_prompt("claude", "MY SUMMARY") == "MY SUMMARY"

    def test_claude_uses_provider_template(self):
        """claude はプロバイダ別サマリテンプレートを返す。"""
        expected = PROVIDER_SUMMARY_PROMPTS["claude"]
        assert resolve_summary_prompt("claude", "") == expected

    def test_gemini_uses_provider_template(self):
        """gemini はプロバイダ別サマリテンプレートを返す。"""
        expected = PROVIDER_SUMMARY_PROMPTS["gemini"]
        assert resolve_summary_prompt("gemini", "") == expected

    def test_lmstudio_falls_back_to_default(self):
        """lmstudio は DEFAULT_SUMMARY_PROMPT へフォールバックする。"""
        assert resolve_summary_prompt("lmstudio", "") == DEFAULT_SUMMARY_PROMPT

    def test_off_falls_back_to_default(self):
        """off / 未知プロバイダは DEFAULT_SUMMARY_PROMPT へフォールバックする。"""
        assert resolve_summary_prompt("off", "") == DEFAULT_SUMMARY_PROMPT
        assert resolve_summary_prompt("unknown_xyz", "") == DEFAULT_SUMMARY_PROMPT


# ══════════════════════════════════════════════════════════════
#  V171-KEY-01/04: LLMConfigDialog._apply の APIキー非流入・
#  _session_api_keys 格納/クリア・RunPod スロット回帰テスト
# ══════════════════════════════════════════════════════════════


class _GetVarStub:
    """tk.StringVar/IntVar/DoubleVar の .get() のみを模したスタブ。"""

    def __init__(self, value):
        self._value = value

    def get(self):
        """設定済みの値をそのまま返す。"""
        return self._value


class _GetTextStub:
    """tk.Text.get(start, end) のみを模したスタブ。"""

    def __init__(self, value=""):
        self._value = value

    def get(self, _start, _end):
        """設定済みの値をそのまま返す（start/end 引数は無視）。"""
        return self._value


def _make_apply_key_stub(session_api_keys, claude_key="", gemini_key="", runpod_key=""):
    """LLMConfigDialog._apply を Tk 生成なしで呼ぶための最小スタブを返す。

    _apply が参照する全属性（プロバイダ別設定行・数値設定・カスタムプロンプト）
    を実際の値で埋め、session_api_keys 引数は複製せず参照をそのまま持たせる
    （app._session_api_keys の実体共有を再現するため）。
    """
    stub = types.SimpleNamespace(
        _session_api_keys=session_api_keys,
        provider_var=_GetVarStub("claude"),
        lm_url_var=_GetVarStub("http://localhost:1234"),
        lm_model_var=_GetVarStub(""),
        ollama_url_var=_GetVarStub("http://localhost:11434"),
        ollama_model_var=_GetVarStub(""),
        runpod_url_var=_GetVarStub(""),
        runpod_model_var=_GetVarStub(""),
        claude_model_var=_GetVarStub("claude-sonnet-4-6"),
        effort_var=_GetVarStub("low"),
        gemini_model_var=_GetVarStub("gemini-2.5-flash"),
        ocr_scale_var=_GetVarStub(1.5),
        ocr_timeout_var=_GetVarStub(120),
        ocr_max_tokens_var=_GetVarStub(-1),
        ocr_prompt_text=_GetTextStub(""),
        ocr_summary_prompt_text=_GetTextStub(""),
        ocr_temperature_var=_GetVarStub(0.1),
        ocr_concurrency_var=_GetVarStub(2),
        claude_api_key_var=_GetVarStub(claude_key),
        gemini_api_key_var=_GetVarStub(gemini_key),
        runpod_api_key_var=_GetVarStub(runpod_key),
        on_apply=None,
        destroy=lambda: None,
    )
    return stub


class TestApiKeyNotInSettings:
    """V171-KEY-01: APIキー入力値が on_apply へ渡る llm_settings dict に含まれない。"""

    def test_claude_key_not_in_llm_settings(self):
        """claude 欄にダミーキーを入れて _apply しても api_key 系キーが現れない。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(session, claude_key="sk-ant-DUMMY-TEST-KEY")
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert not any("api_key" in k.lower() for k in captured), (
            f"llm_settings に api_key 系キーが含まれている: {list(captured.keys())}"
        )

    def test_all_provider_keys_not_in_llm_settings(self):
        """claude/gemini/runpod 全欄にダミーキーを入れても llm_settings は非流入。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(
            session,
            claude_key="sk-ant-DUMMY",
            gemini_key="AIza-DUMMY",
            runpod_key="rp-DUMMY",
        )
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert not any("api_key" in k.lower() for k in captured)


class TestApplyPromptFileWriteback:
    """V174-2: _apply のファイル連動モード（外部 md への書き戻し）を検証する。

    ファイルが既に存在する場合のみ入力欄の内容を書き戻し、
    存在しない場合はファイルを新規作成しない。
    """

    def test_writes_back_when_file_exists(self, monkeypatch):
        """md ファイル存在時は入力欄の内容が save_prompt_file へ渡る。"""
        from pagefolio.dialogs import llm_config as llm_config_mod

        saved = {}
        monkeypatch.setattr(llm_config_mod, "prompt_file_exists", lambda _f: True)
        monkeypatch.setattr(
            llm_config_mod,
            "save_prompt_file",
            lambda f, content: saved.update({f: content}) or True,
        )
        stub = _make_apply_key_stub({})
        stub.ocr_prompt_text = _GetTextStub("カスタム本文")
        stub.ocr_summary_prompt_text = _GetTextStub("サマリ本文")
        llm_config_mod.LLMConfigDialog._apply(stub)

        from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE

        assert saved[CUSTOM_PROMPT_FILE] == "カスタム本文"
        assert saved[SUMMARY_PROMPT_FILE] == "サマリ本文"

    def test_no_write_when_file_missing(self, monkeypatch):
        """md ファイルが無ければ save_prompt_file は呼ばれない（新規作成しない）。"""
        from pagefolio.dialogs import llm_config as llm_config_mod

        saved = {}
        monkeypatch.setattr(llm_config_mod, "prompt_file_exists", lambda _f: False)
        monkeypatch.setattr(
            llm_config_mod,
            "save_prompt_file",
            lambda f, content: saved.update({f: content}) or True,
        )
        stub = _make_apply_key_stub({})
        stub.ocr_prompt_text = _GetTextStub("カスタム本文")
        llm_config_mod.LLMConfigDialog._apply(stub)

        assert saved == {}


class TestSessionKeyStoreAndClear:
    """V171-KEY-01: 非空入力は _session_api_keys へ格納・空欄はクリア（D-04/D-06）。"""

    def test_non_empty_key_stored_in_session(self):
        """非空の claude 欄入力は _session_api_keys["claude"] に格納される。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(session, claude_key="sk-ant-DUMMY-TEST-KEY")
        LLMConfigDialog._apply(stub)

        assert session["claude"] == "sk-ant-DUMMY-TEST-KEY"

    def test_empty_key_clears_existing_session_entry(self):
        """空欄で _apply すると既存の provider エントリが除去される（D-06）。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {"claude": "old-dummy-key"}
        stub = _make_apply_key_stub(session, claude_key="")
        LLMConfigDialog._apply(stub)

        assert "claude" not in session

    def test_whitespace_only_key_treated_as_empty(self):
        """空白のみの入力は空欄扱いでクリアされる（.strip() 適用）。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {"gemini": "old-dummy-key"}
        stub = _make_apply_key_stub(session, gemini_key="   ")
        LLMConfigDialog._apply(stub)

        assert "gemini" not in session


class TestRunpodSessionKeySlot:
    """V171-KEY-04: RunPod 欄の値が _session_api_keys["runpod"] に格納され、
    "claude" スロットを汚染しない（Pitfall 1 の回帰防止）。
    """

    def test_runpod_key_goes_to_runpod_slot(self):
        """runpod 欄のダミーキーが _session_api_keys["runpod"] に入る。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(session, runpod_key="rp-DUMMY-TEST-KEY")
        LLMConfigDialog._apply(stub)

        assert session.get("runpod") == "rp-DUMMY-TEST-KEY"

    def test_runpod_key_does_not_pollute_claude_slot(self):
        """runpod 欄にのみ値を入れても "claude" スロットは汚染されない。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(session, runpod_key="rp-DUMMY-TEST-KEY")
        LLMConfigDialog._apply(stub)

        assert "claude" not in session

    def test_all_three_slots_independent(self):
        """claude/gemini/runpod の3欄を入力すると各自のスロットへ独立格納される。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(
            session,
            claude_key="sk-ant-DUMMY",
            gemini_key="AIza-DUMMY",
            runpod_key="rp-DUMMY",
        )
        LLMConfigDialog._apply(stub)

        assert session["claude"] == "sk-ant-DUMMY"
        assert session["gemini"] == "AIza-DUMMY"
        assert session["runpod"] == "rp-DUMMY"


# ══════════════════════════════════════════════════════════════
#  D-07: OCRDialog._maybe_show_lang_fallback_notice
#  （Tesseract 段階的縮退フォールバックの非モーダル WARNING 注記）
# ══════════════════════════════════════════════════════════════


class _FakeStringVar:
    """tk.StringVar の最小スタブ（Tk 生成なしでロジックのみ検証）。"""

    def __init__(self, value=""):
        self._value = value

    def set(self, value):
        self._value = value

    def get(self):
        return self._value


class _FakeLabel:
    """tk.Label の最小スタブ。pack/pack_forget 呼び出しと表示状態のみ記録する。"""

    def __init__(self):
        self.mapped = False
        self.pack_calls = []
        self.pack_forget_calls = 0

    def winfo_ismapped(self):
        return self.mapped

    def pack(self, **kwargs):
        self.mapped = True
        self.pack_calls.append(kwargs)

    def pack_forget(self):
        self.mapped = False
        self.pack_forget_calls += 1


def _make_lang_fallback_fake(provider):
    """_maybe_show_lang_fallback_notice 用の最小 fake OCRDialog を返す。

    OCR 結果テキスト（raw）への混入がないことも検証できるよう、
    self.text.insert 呼び出しを記録するスタブを併せて用意する。
    """
    from pagefolio.constants import LANG

    text_inserts = []
    fake = types.SimpleNamespace(
        provider=provider,
        _L=LANG["ja"],
        _lang_fallback_notice_var=_FakeStringVar(),
        _lang_fallback_label=_FakeLabel(),
        progress_bar=object(),
        text=types.SimpleNamespace(insert=lambda *a, **k: text_inserts.append((a, k))),
    )
    return fake, text_inserts


class TestMaybeShowLangFallbackNotice:
    """D-07: フォールバック発生時に1回だけ非モーダル注記を表示し、
    OCR 結果 raw には混入させない。非発生時は注記を出さない。"""

    def test_notice_shown_when_fallback_true(self):
        """lang_fallback=True のプロバイダで注記が表示され要求/実効言語を含む"""
        from pagefolio.ocr_dialog import OCRDialog

        provider = types.SimpleNamespace(
            lang_fallback=True, requested_lang="deu+fra", effective_lang="jpn+eng"
        )
        fake, text_inserts = _make_lang_fallback_fake(provider)

        OCRDialog._maybe_show_lang_fallback_notice(fake)

        msg = fake._lang_fallback_notice_var.get()
        assert "deu+fra" in msg
        assert "jpn+eng" in msg
        assert fake._lang_fallback_label.mapped is True
        assert text_inserts == [], "OCR結果テキスト(raw)に注記が混入してはいけない"

    def test_notice_hidden_when_no_fallback(self):
        """lang_fallback=False のときは注記が消え非表示になる"""
        from pagefolio.ocr_dialog import OCRDialog

        provider = types.SimpleNamespace(lang_fallback=False)
        fake, _ = _make_lang_fallback_fake(provider)
        fake._lang_fallback_label.mapped = True  # 前回表示状態を模擬

        OCRDialog._maybe_show_lang_fallback_notice(fake)

        assert fake._lang_fallback_notice_var.get() == ""
        assert fake._lang_fallback_label.mapped is False

    def test_notice_hidden_for_provider_without_lang_fallback_attr(self):
        """lang_fallback 属性を持たないプロバイダ（claude 等）でも例外なく非表示"""
        from pagefolio.ocr_dialog import OCRDialog

        provider = types.SimpleNamespace()  # lang_fallback 属性なし
        fake, _ = _make_lang_fallback_fake(provider)

        OCRDialog._maybe_show_lang_fallback_notice(fake)

        assert fake._lang_fallback_notice_var.get() == ""
        assert fake._lang_fallback_label.mapped is False

    def test_notice_hidden_when_provider_is_none(self):
        """provider が None（未生成）でも例外なく非表示のまま"""
        from pagefolio.ocr_dialog import OCRDialog

        fake, _ = _make_lang_fallback_fake(None)

        OCRDialog._maybe_show_lang_fallback_notice(fake)

        assert fake._lang_fallback_notice_var.get() == ""
        assert fake._lang_fallback_label.mapped is False


# ══════════════════════════════════════════════════════════════
#  D-14: LLMConfigDialog ネスト適用の独立トランザクション化
#  （app._apply_llm_settings_live・SettingsDialog.on_llm_apply cascade）
# ══════════════════════════════════════════════════════════════


class TestApplyLlmSettingsLive:
    """D-14: app._apply_llm_settings_live が app.settings（メモリ）へ即時反映し、
    _rebuild_ui を呼ばない軽量反映であることを検証する。
    """

    def test_updates_memory_settings_without_rebuild(self, monkeypatch):
        """settings が更新され、既存キー（theme 等）は保持され、_rebuild_ui は
        呼ばれない。"""
        from pagefolio.app import PDFEditorApp

        monkeypatch.setattr("pagefolio.app._save_settings", lambda s: None)
        rebuild_calls = {"n": 0}
        stub = types.SimpleNamespace(
            settings={"theme": "dark", "font_size": 10},
            _rebuild_ui=lambda: rebuild_calls.__setitem__("n", rebuild_calls["n"] + 1),
        )
        PDFEditorApp._apply_llm_settings_live(stub, {"ocr_provider": "claude"})

        assert stub.settings["ocr_provider"] == "claude"
        assert stub.settings["theme"] == "dark"
        assert rebuild_calls["n"] == 0

    def test_saves_to_disk(self, monkeypatch):
        """_save_settings が更新後の settings で呼ばれる（ディスク永続化）。"""
        from pagefolio.app import PDFEditorApp

        saved = {}
        monkeypatch.setattr("pagefolio.app._save_settings", lambda s: saved.update(s))
        stub = types.SimpleNamespace(settings={"theme": "dark"})
        PDFEditorApp._apply_llm_settings_live(
            stub, {"claude_model": "claude-sonnet-4-6"}
        )
        assert saved.get("claude_model") == "claude-sonnet-4-6"

    def test_api_key_like_values_not_specially_filtered(self, monkeypatch):
        """本メソッド自体は渡された dict をそのまま反映するだけであり、api_key
        非流入の担保は呼び出し元（LLMConfigDialog._apply・TestApiKeyNotInSettings）
        の責務であることを確認する（api_key を含まない dict なら正常反映）。
        """
        from pagefolio.app import PDFEditorApp

        monkeypatch.setattr("pagefolio.app._save_settings", lambda s: None)
        stub = types.SimpleNamespace(settings={})
        PDFEditorApp._apply_llm_settings_live(stub, {"ocr_provider": "claude"})
        assert not any("api_key" in k.lower() for k in stub.settings)


class TestSettingsDialogNestedApplyCascade:
    """D-14/C4/C5: LLMConfigDialog（ネスト側）の適用が、外側 SettingsDialog の
    Apply/Cancel と独立して app.settings（メモリ）へ即時反映されることを検証する。
    """

    def _patch_fake_llm_config_dialog(self, monkeypatch):
        """LLMConfigDialog を捕捉スタブへ差し替え、渡された kwargs を回収する。"""
        captured_kwargs = {}

        class _FakeLLMConfigDialog:
            def __init__(self, *args, **kwargs):
                captured_kwargs.update(kwargs)

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.LLMConfigDialog", _FakeLLMConfigDialog
        )
        return captured_kwargs

    def test_nested_apply_calls_on_llm_apply_callback(self, monkeypatch):
        """on_llm_apply が設定済みなら、ネスト適用時に新しい llm_settings で
        呼ばれる。"""
        from pagefolio.dialogs.settings import SettingsDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        captured_kwargs = self._patch_fake_llm_config_dialog(monkeypatch)

        live_calls = []
        stub = types.SimpleNamespace(
            current_settings={"ocr_provider": "lmstudio"},
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
            _plugin_manager=None,
            _on_llm_apply=lambda s: live_calls.append(s),
        )
        SettingsDialog._open_llm_config(stub)

        on_apply = captured_kwargs["on_apply"]
        on_apply({"ocr_provider": "claude"})

        assert live_calls == [{"ocr_provider": "claude"}]

    def test_outer_cancel_does_not_revert_memory_reflection(self, monkeypatch):
        """外側 SettingsDialog をキャンセル（外側 callback 非呼び出し）しても、
        ネスト適用済みの LLM 設定は app.settings（メモリ）に残ったまま
        （C4: ディスクとメモリの不整合解消の回帰）。
        """
        from pagefolio.app import PDFEditorApp
        from pagefolio.dialogs.settings import SettingsDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        monkeypatch.setattr("pagefolio.app._save_settings", lambda settings: None)
        captured_kwargs = self._patch_fake_llm_config_dialog(monkeypatch)

        app_stub = types.SimpleNamespace(
            settings={"theme": "dark", "ocr_provider": "lmstudio"}
        )
        settings_dialog_stub = types.SimpleNamespace(
            current_settings={"ocr_provider": "lmstudio"},
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
            _plugin_manager=None,
            _on_llm_apply=lambda s: PDFEditorApp._apply_llm_settings_live(app_stub, s),
        )
        SettingsDialog._open_llm_config(settings_dialog_stub)
        on_apply = captured_kwargs["on_apply"]
        on_apply({"ocr_provider": "claude"})

        # 外側 SettingsDialog._apply/callback は一切呼んでいない（＝キャンセル相当）
        # にもかかわらず app.settings は新しい値のまま。
        assert app_stub.settings["ocr_provider"] == "claude"
        assert app_stub.settings["theme"] == "dark"

    def test_no_on_llm_apply_does_not_raise(self, monkeypatch):
        """on_llm_apply 未設定（後方互換・既存 SimpleNamespace スタブ等）でも
        例外を出さずに完了する。"""
        from pagefolio.dialogs.settings import SettingsDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        captured_kwargs = self._patch_fake_llm_config_dialog(monkeypatch)

        stub = types.SimpleNamespace(
            current_settings={"ocr_provider": "lmstudio"},
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
            _plugin_manager=None,
            # _on_llm_apply 属性を意図的に設定しない
        )
        SettingsDialog._open_llm_config(stub)
        on_apply = captured_kwargs["on_apply"]
        on_apply({"ocr_provider": "claude"})  # 例外なく完了すること

    def test_api_key_not_propagated_through_cascade(self, monkeypatch):
        """LLMConfigDialog._apply が生成する llm_settings（api_key 非流入）が
        そのままネスト経由で app.settings へ渡ってもキー混入しないことを、
        cascade 経路全体で確認する。
        """
        from pagefolio.dialogs.llm_config import LLMConfigDialog
        from pagefolio.dialogs.settings import SettingsDialog

        monkeypatch.setattr("pagefolio.settings._save_settings", lambda settings: None)
        captured_kwargs = self._patch_fake_llm_config_dialog(monkeypatch)

        live_settings = {}
        stub = types.SimpleNamespace(
            current_settings={"ocr_provider": "lmstudio"},
            _font=lambda delta=0, weight=None: ("Segoe UI", 10),
            _plugin_manager=None,
            _on_llm_apply=lambda s: live_settings.update(s),
        )
        SettingsDialog._open_llm_config(stub)
        on_apply = captured_kwargs["on_apply"]

        apply_stub = _make_apply_key_stub({}, claude_key="sk-ant-DUMMY-TEST-KEY")
        apply_stub.on_apply = on_apply
        LLMConfigDialog._apply(apply_stub)

        assert not any("api_key" in k.lower() for k in live_settings)


# ══════════════════════════════════════════════════════════════
#  C2: Ollama モデル取得/接続テストの共通ヘルパー統合
#  （_probe_ollama_provider・_probe_lm_provider 同型）
# ══════════════════════════════════════════════════════════════


class _OllamaComboStub:
    """ttk.Combobox の ["values"] = ... 代入のみを記録するスタブ。"""

    def __init__(self):
        self.values = None

    def __setitem__(self, key, value):
        if key == "values":
            self.values = value


class TestProbeOllamaProvider:
    """C2: _probe_ollama_provider が _probe_lm_provider と同型の共通ヘルパーとして
    Ollama のモデル取得/接続テストを統合していることを検証する。
    """

    def _make_stub(self, url="http://localhost:11434"):
        from pagefolio.constants import LANG
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        status = {}
        stub = types.SimpleNamespace(
            ollama_url_var=_GetVarStub(url),
            ollama_model_combo=_OllamaComboStub(),
            _L=LANG["ja"],
            _set_lm_status=lambda text, kind="info": status.update(
                {"text": text, "kind": kind}
            ),
        )
        stub._probe_ollama_provider = lambda update_combo: (
            LLMConfigDialog._probe_ollama_provider(stub, update_combo)
        )
        return stub, status

    def test_update_combo_true_reflects_models(self, monkeypatch):
        """update_combo=True のとき Combobox の values にモデル一覧が反映される。"""
        stub, status = self._make_stub()
        monkeypatch.setattr(
            "pagefolio.ocr_providers.OllamaProvider.list_models",
            lambda self: ["llava", "llama3.2-vision"],
        )
        stub._probe_ollama_provider(update_combo=True)
        assert stub.ollama_model_combo.values == ["llava", "llama3.2-vision"]
        assert status["kind"] == "ok"

    def test_update_combo_false_does_not_touch_combo(self, monkeypatch):
        """update_combo=False（接続テストのみ）では Combobox の values を変更しない。"""
        stub, status = self._make_stub()
        monkeypatch.setattr(
            "pagefolio.ocr_providers.OllamaProvider.list_models",
            lambda self: ["llava"],
        )
        stub._probe_ollama_provider(update_combo=False)
        assert stub.ollama_model_combo.values is None
        assert status["kind"] == "ok"

    def test_empty_url_shows_fail_status(self):
        """URL 空欄はエラーステータス表示となり Combobox は変更されない。"""
        stub, status = self._make_stub(url="")
        stub._probe_ollama_provider(update_combo=True)
        assert status["kind"] == "fail"
        assert stub.ollama_model_combo.values is None

    def test_connection_error_shows_fail_status(self, monkeypatch):
        """list_models が ConnectionError を送出した場合は fail ステータスになる。"""
        stub, status = self._make_stub()

        def _raise(self):
            raise ConnectionError("boom")

        monkeypatch.setattr(
            "pagefolio.ocr_providers.OllamaProvider.list_models", _raise
        )
        stub._probe_ollama_provider(update_combo=True)
        assert status["kind"] == "fail"

    def test_fetch_and_test_are_thin_wrappers(self):
        """_fetch_ollama_models/_test_ollama_connection が
        _probe_ollama_provider(update_combo=...) を呼ぶ薄いラッパーであり、
        旧重複本体が除去されていることをソース上で確認する。
        """
        src = _read_llm_config_package_source()
        assert "self._probe_ollama_provider(update_combo=True)" in src
        assert "self._probe_ollama_provider(update_combo=False)" in src
        assert src.count("def _test_ollama_connection") == 1


# ══════════════════════════════════════════════════════════════
#  V180-TMPL-01〜05: テンプレート管理セクション（02-02）
# ══════════════════════════════════════════════════════════════


class TestTemplateSection:
    """テンプレートセクション（sections.py）と _apply のアクティブテンプレート
    収集を検証する。V180-TMPL-05（全プロバイダ横断共有）は 02-01 で settings.py
    へ実装済みの load_custom_prompt/load_summary_prompt 経由の解決を、本プランで
    UI 側（_apply の active 収集）から接続できることを確認する。
    """

    def test_template_combo_referenced_in_sections_source(self):
        """sections.py に template_combo/_on_template_change/save_template が
        存在する（source-scan・ヘッドレス検証）。"""
        src = _read_llm_config_package_source()
        assert "template_combo" in src
        assert "_on_template_change" in src
        assert "save_template" in src

    def test_save_template_then_load_custom_prompt_resolves(self):
        """save_template→アクティブ設定で load_custom_prompt がテンプレート値を
        解決する（V180-TMPL-05: 全プロバイダ共通経路の settings dict レベル検証）。
        """
        from pagefolio.settings import load_custom_prompt, save_template

        settings = {"prompt_templates": {"active": "", "items": {}}}
        save_template(settings, "my-template", "custom-value", "summary-value")
        settings["prompt_templates"]["active"] = "my-template"
        assert load_custom_prompt(settings) == "custom-value"

    def test_save_template_then_load_summary_prompt_resolves(self):
        """load_summary_prompt も同様にテンプレート値を解決する。"""
        from pagefolio.settings import load_summary_prompt, save_template

        settings = {"prompt_templates": {"active": "", "items": {}}}
        save_template(settings, "my-template", "custom-value", "summary-value")
        settings["prompt_templates"]["active"] = "my-template"
        assert load_summary_prompt(settings) == "summary-value"

    def test_apply_collects_active_template_preserving_items(self):
        """_apply が prompt_templates の items を保持したまま active を
        現在の選択値（_active_template_name）で差し替えて収集する。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        stub = _make_apply_key_stub({})
        stub.current_settings = {
            "prompt_templates": {
                "active": "old-tpl",
                "items": {
                    "old-tpl": {"custom_prompt": "a", "summary_prompt": "b"},
                    "other-tpl": {"custom_prompt": "c", "summary_prompt": "d"},
                },
            }
        }
        stub._active_template_name = "other-tpl"
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert captured["prompt_templates"]["active"] == "other-tpl"
        assert captured["prompt_templates"]["items"] == {
            "old-tpl": {"custom_prompt": "a", "summary_prompt": "b"},
            "other-tpl": {"custom_prompt": "c", "summary_prompt": "d"},
        }

    def test_apply_without_current_settings_attr_falls_back_gracefully(self):
        """current_settings/_active_template_name 未設定の既存スタブ経路でも
        AttributeError を出さず、空のプレースホルダを収集する（後方互換）。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        stub = _make_apply_key_stub({})
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert captured["prompt_templates"] == {"active": "", "items": {}}


class TestFallbackSection:
    """フォールバック順設定セクション（sections.py）と _apply の収集を検証する。

    V180-FALL-01（安全側既定）・V180-FALL-03（設定面の永続化）・プロバイダ名
    ホワイトリスト検証（Input Validation・ASVS L1）を確認する。
    """

    def test_fallback_widgets_referenced_in_sections_source(self):
        """sections.py に fallback_listbox/_fallback_move_up/fallback_enabled_var
        が存在する（source-scan・ヘッドレス検証）。"""
        src = _read_llm_config_package_source()
        assert "fallback_listbox" in src
        assert "_fallback_move_up" in src
        assert "fallback_enabled_var" in src

    def test_apply_collects_fallback_enabled_and_chain(self):
        """_apply が ocr_fallback_enabled（bool）と ocr_fallback_chain（list）を
        収集する。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        stub = _make_apply_key_stub({})
        stub.fallback_enabled_var = _GetVarStub(True)
        stub._fallback_known_providers = ["claude", "gemini", "lmstudio"]
        stub._fallback_chain = ["claude", "gemini"]
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert captured["ocr_fallback_enabled"] is True
        assert captured["ocr_fallback_chain"] == ["claude", "gemini"]

    def test_apply_filters_unknown_provider_from_chain(self):
        """既知プロバイダ一覧に無い名前はチェーンから除外される
        （ホワイトリスト検証・Input Validation・ASVS L1）。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        stub = _make_apply_key_stub({})
        stub.fallback_enabled_var = _GetVarStub(True)
        stub._fallback_known_providers = ["claude", "gemini"]
        stub._fallback_chain = ["claude", "not-a-real-provider", "gemini"]
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert captured["ocr_fallback_chain"] == ["claude", "gemini"]

    def test_apply_defaults_when_fallback_attrs_absent(self):
        """fallback_enabled_var/_fallback_chain 未設定の既存スタブ経路でも
        AttributeError を出さず既定値（False・空リスト）を収集する
        （後方互換・V180-FALL-01 安全側既定）。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        stub = _make_apply_key_stub({})
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert captured["ocr_fallback_enabled"] is False
        assert captured["ocr_fallback_chain"] == []


# ══════════════════════════════════════════════════════════════
#  CR-02 回帰: テンプレート Cancel/Apply 契約の回復（02-05・V180-TMPL-01/03）
# ══════════════════════════════════════════════════════════════


class _SetGetVarStub:
    """tk.StringVar 等の .get()/.set() 両方を模した軽量スタブ。

    既存 _GetVarStub は get のみのため、template_var のように set() でも
    駆動するテスト向けに新設する（衝突回避のため別名にする）。
    """

    def __init__(self, value):
        self._value = value

    def get(self):
        """設定済みの値をそのまま返す。"""
        return self._value

    def set(self, value):
        """値を更新する。"""
        self._value = value


class TestTemplateCancelContract:
    """CR-02（02-REVIEW.md）回帰: dialog.py の __init__ ディープコピー分離・
    sections.py の即時 _save_settings 除去・_on_template_delete の askyesno
    削除確認を、実 bound method 呼び出しと source assertion で検証する。
    """

    def test_init_deepcopy_separates_prompt_templates_from_app_settings(self):
        """LLMConfigDialog.__init__ の分離ロジック（dict() 後に prompt_templates
        を copy.deepcopy で分離）により、current_settings["prompt_templates"]
        が入力 app_settings の同キーと別オブジェクトになり、内側の items・
        各テンプレート dict も別オブジェクトである（片方の変更が他方へ
        伝播しない）ことを確認する。

        LLMConfigDialog.__init__ は実 Tk（Toplevel の親ウィジェット）を要求し
        headless では直接呼べないため、dialog.py 実コードと同一の分離手順を
        ここで再現し不変条件そのものをアサートする。あわせて dialog.py の
        実ソースに copy.deepcopy が実在することを source assertion で補強する
        （__init__ 側 + _apply 側の最低2箇所）。
        """
        import copy

        app_settings = {
            "prompt_templates": {
                "active": "tpl-a",
                "items": {
                    "tpl-a": {"custom_prompt": "a", "summary_prompt": "a2"},
                    "tpl-b": {"custom_prompt": "b", "summary_prompt": "b2"},
                },
            }
        }

        # dialog.py __init__ の分離手順を再現:
        #   self.current_settings = dict(current_settings)
        #   self.current_settings["prompt_templates"] = copy.deepcopy(...)
        current_settings = dict(app_settings)
        current_settings["prompt_templates"] = copy.deepcopy(
            app_settings.get("prompt_templates", {"active": "", "items": {}})
        )

        assert (
            current_settings["prompt_templates"] is not app_settings["prompt_templates"]
        )
        assert (
            current_settings["prompt_templates"]["items"]
            is not app_settings["prompt_templates"]["items"]
        )
        assert (
            current_settings["prompt_templates"]["items"]["tpl-a"]
            is not app_settings["prompt_templates"]["items"]["tpl-a"]
        )

        # 片方の変更が他方へ伝播しない
        current_settings["prompt_templates"]["items"]["tpl-a"]["custom_prompt"] = (
            "changed"
        )
        assert (
            app_settings["prompt_templates"]["items"]["tpl-a"]["custom_prompt"] == "a"
        )

        # 実コードが copy.deepcopy を用いていることを補強確認
        src = _read_llm_config_package_source()
        assert "import copy" in src
        assert src.count("copy.deepcopy(") >= 2

    def test_cancel_does_not_mutate_app_settings_then_apply_commits_once(self):
        """CRUD 相当の in-place 変更（保存/削除）を分離済み current_settings に
        対して行った後、on_apply を呼ばなければ（＝Cancel 相当・destroy のみ）
        呼び出し元の app_settings 参照が一切変化しないことを確認する。続けて
        LLMConfigDialog._apply（＝Apply 相当）を呼ぶと、prompt_templates が
        active + items 込みで一度だけ収集されることを確認する。
        """
        import copy

        from pagefolio.dialogs.llm_config import LLMConfigDialog
        from pagefolio.settings import delete_template, save_template

        app_settings = {
            "prompt_templates": {
                "active": "tpl-a",
                "items": {
                    "tpl-a": {"custom_prompt": "a", "summary_prompt": "a2"},
                    "tpl-b": {"custom_prompt": "b", "summary_prompt": "b2"},
                },
            }
        }
        original_snapshot = copy.deepcopy(app_settings)

        stub = _make_apply_key_stub({})
        stub.current_settings = dict(app_settings)
        stub.current_settings["prompt_templates"] = copy.deepcopy(
            app_settings["prompt_templates"]
        )
        stub._active_template_name = "tpl-a"

        # CRUD 相当の in-place 変更（保存 + 削除）を分離済み current_settings
        # に対して直接行う（sections.py のハンドラが行う操作を settings.py の
        # 純関数呼び出しで再現）
        save_template(stub.current_settings, "tpl-c", "c", "c2")
        delete_template(stub.current_settings, "tpl-b")

        # Cancel 相当: on_apply を呼ばない（destroy のみ）→ app_settings は不変
        assert app_settings == original_snapshot

        # Apply 相当: _apply の実 bound method 呼び出しで一括収集される
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert captured["prompt_templates"]["active"] == "tpl-a"
        assert set(captured["prompt_templates"]["items"].keys()) == {
            "tpl-a",
            "tpl-c",
        }
        # _apply 自体は呼び出し元の app_settings を汚染しない
        # （永続化は on_apply コールバック側の責務）
        assert app_settings == original_snapshot

    def test_sections_source_has_no_save_settings_reference(self):
        """sections.py 単体ソースにテンプレート CRUD ハンドラの即時
        _save_settings が一切残っていないことを確認する
        （Task 2 の除去の回帰防止・CR-02）。
        """
        import pathlib

        src = pathlib.Path("pagefolio/dialogs/llm_config/sections.py").read_text(
            encoding="utf-8"
        )
        assert "_save_settings" not in src

    def test_on_template_delete_askyesno_no_aborts_yes_deletes(self, monkeypatch):
        """_on_template_delete は askyesno=False で items 残存・delete_template
        非呼出（早期 return）、askyesno=True で items から削除されることを
        確認する（02-REVIEW Fix 案2）。
        """
        from pagefolio.constants import LANG
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        d = LLMConfigDialog.__new__(LLMConfigDialog)
        d._L = LANG["ja"]
        d._active_template_name = "tpl-active"
        d.current_settings = {
            "prompt_templates": {
                "active": "tpl-active",
                "items": {
                    "tpl-active": {"custom_prompt": "x", "summary_prompt": "y"},
                    "tpl-target": {"custom_prompt": "z", "summary_prompt": "w"},
                },
            }
        }
        d.template_var = _SetGetVarStub("tpl-target")
        reload_calls = []
        d._reload_template_combo = lambda select_name=None: reload_calls.append(
            select_name
        )

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: False,
        )
        d._on_template_delete()
        assert "tpl-target" in d.current_settings["prompt_templates"]["items"]
        assert reload_calls == []

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: True,
        )
        d._on_template_delete()
        assert "tpl-target" not in d.current_settings["prompt_templates"]["items"]
        assert reload_calls == ["tpl-active"]


# ══════════════════════════════════════════════════════════════
#  02-06 gap closure: テンプレート UI ハンドラの behavior_unverified_items
#  （D-03/D-04/D-05/D-07・02-VERIFICATION.md）を実 bound method 呼び出しで
#  検証する。test_ocr_fallback.py の headless スタブ + 実 bound method 呼び出し
#  パターンを LLMConfigDialog 側へ同型移植する。
# ══════════════════════════════════════════════════════════════


class _FakeTemplateText:
    """OCR カスタム/サマリプロンプト入力欄（tk.Text）相当のスタブ。

    get/delete/insert のみを実装し、tk.Text の index 引数（"1.0"/"end" 等）は
    無視して内部バッファ文字列だけを保持する（_on_template_change が
    delete("1.0", "end") → insert("1.0", value) の順で呼ぶ実際の呼び出し方に
    追従する）。
    """

    def __init__(self, value=""):
        self._value = value

    def get(self, _start, _end):
        """設定済みの内部バッファ文字列を返す（index 引数は無視）。"""
        return self._value

    def delete(self, _start, _end):
        """内部バッファを空文字列にする（index 引数は無視）。"""
        self._value = ""

    def insert(self, _index, value):
        """内部バッファへ value を追記する（index 引数は無視）。"""
        self._value += value


class _FakeCombo:
    """ttk.Combobox 相当スタブ。configure(values=...) の呼び出しのみ記録する
    （_reload_template_combo が呼ぶため）。
    """

    def __init__(self):
        self.values = None

    def configure(self, **kwargs):
        """values キーワード引数が渡された場合のみ記録する。"""
        if "values" in kwargs:
            self.values = kwargs["values"]


def _make_template_dialog(
    current_settings,
    active_template_name="",
    template_var_value="",
    custom_text="",
    summary_text="",
):
    """LLMConfigDialog のテンプレート UI ハンドラを Tk 生成なしで駆動する
    headless インスタンスを返す。

    tests/test_ocr_fallback.py の _make_dialog と同型: LLMConfigDialog.__new__
    で __init__/_build を一切経由せず、検証に必要な属性のみ手動で設定する。
    LLMConfigDialog の全 mixin メソッド（_has_unsaved_template_changes 等）は
    実インスタンス上でそのまま使えるため、_on_template_change 内の自己呼び出し
    も実コードで動く。template_delete_btn は既存の _ButtonStub（OCR-UI-02 節で
    定義済み・.state(flags) を記録する ttk.Button 相当スタブ）をそのまま再利用
    する（新規重複定義を避ける）。
    """
    from pagefolio.constants import LANG
    from pagefolio.dialogs.llm_config import LLMConfigDialog

    d = LLMConfigDialog.__new__(LLMConfigDialog)
    d._L = LANG["ja"]
    d.current_settings = current_settings
    d._active_template_name = active_template_name
    d.template_var = _SetGetVarStub(template_var_value)
    d.ocr_prompt_text = _FakeTemplateText(custom_text)
    d.ocr_summary_prompt_text = _FakeTemplateText(summary_text)
    d.template_combo = _FakeCombo()
    d.template_delete_btn = _ButtonStub()
    return d


class TestTemplateChangeFlow:
    """D-05/D-07（V180-TMPL-04）: _on_template_change の未保存差分確認による
    切替中止（D-05）と、切替確定後の外部mdファイル上書き（D-07）を実
    bound method 呼び出しで検証する（02-VERIFICATION.md
    behavior_unverified_items の1件目・2件目）。
    """

    def test_cancel_discards_switch_and_keeps_edited_content(self, monkeypatch):
        """未保存差分ありで askyesno=False（キャンセル）を返すと、切替が中止され
        template_var がアクティブテンプレート名へ戻り、入力欄内容も変化せず、
        save_prompt_file にも到達しない（D-05）。
        """
        current_settings = {
            "prompt_templates": {
                "active": "A",
                "items": {
                    "A": {"custom_prompt": "saved-A", "summary_prompt": "saved-A2"},
                    "B": {"custom_prompt": "b", "summary_prompt": "b2"},
                },
            }
        }
        d = _make_template_dialog(
            current_settings,
            active_template_name="A",
            template_var_value="B",
            custom_text="edited",
            summary_text="saved-A2",
        )
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.prompt_file_exists",
            lambda _f: True,
        )
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: False,
        )
        save_calls = []
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.save_prompt_file",
            lambda f, content: save_calls.append((f, content)),
        )

        d._on_template_change()

        assert d.template_var.get() == "A"
        assert d.ocr_prompt_text.get("1.0", "end") == "edited"
        assert save_calls == []

    def test_confirmed_switch_overwrites_external_files_fake_capture(self, monkeypatch):
        """未保存差分なしの切替確定後、選択テンプレートの内容が入力欄へ反映され、
        save_prompt_file が CUSTOM_PROMPT_FILE/SUMMARY_PROMPT_FILE と新テンプレート
        内容で呼ばれる（D-07・フェイク捕捉版）。
        """
        from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE

        current_settings = {
            "prompt_templates": {
                "active": "A",
                "items": {
                    "A": {"custom_prompt": "saved-A", "summary_prompt": "saved-A2"},
                    "B": {"custom_prompt": "newC", "summary_prompt": "newS"},
                },
            }
        }
        d = _make_template_dialog(
            current_settings,
            active_template_name="A",
            template_var_value="B",
            custom_text="saved-A",
            summary_text="saved-A2",
        )
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.prompt_file_exists",
            lambda _f: True,
        )
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: True,
        )
        save_calls = []
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.save_prompt_file",
            lambda f, content: save_calls.append((f, content)),
        )

        d._on_template_change()

        assert (CUSTOM_PROMPT_FILE, "newC") in save_calls
        assert (SUMMARY_PROMPT_FILE, "newS") in save_calls
        assert d._active_template_name == "B"
        assert d.ocr_prompt_text.get("1.0", "end") == "newC"

    def test_change_overwrites_external_md_file(self, monkeypatch, tmp_path):
        """D-07 実ファイル検証版: settings._get_base_dir を tmp_path へ差し替え、
        save_prompt_file/prompt_file_exists/load_prompt_file は一切
        monkeypatch せず実関数のまま通す。切替後に ocr_custom_prompt.md/
        ocr_summary_prompt.md が新アクティブテンプレートの内容で実際に
        上書きされていることをファイル読み取りで確認する
        （02-VERIFICATION.md behavior_unverified_items[1] の test 欄と一致）。
        """
        from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE

        monkeypatch.setattr("pagefolio.settings._get_base_dir", lambda: str(tmp_path))
        (tmp_path / CUSTOM_PROMPT_FILE).write_text("old-custom", encoding="utf-8")
        (tmp_path / SUMMARY_PROMPT_FILE).write_text("old-summary", encoding="utf-8")

        current_settings = {
            "prompt_templates": {
                "active": "A",
                "items": {
                    "A": {
                        "custom_prompt": "old-custom",
                        "summary_prompt": "old-summary",
                    },
                    "B": {"custom_prompt": "newC", "summary_prompt": "newS"},
                },
            }
        }
        d = _make_template_dialog(
            current_settings,
            active_template_name="A",
            template_var_value="B",
            custom_text="old-custom",
            summary_text="old-summary",
        )
        # 未保存差分は無い想定（入力欄内容がアクティブテンプレート保存済み内容と
        # 一致）だが、askyesno が呼ばれても切替が継続するよう True にしておく
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: True,
        )

        d._on_template_change()

        assert (tmp_path / CUSTOM_PROMPT_FILE).read_text(encoding="utf-8") == "newC"
        assert (tmp_path / SUMMARY_PROMPT_FILE).read_text(encoding="utf-8") == "newS"


class TestTemplateNameValidationUI:
    """D-04（V180-TMPL-03・UI 経由）: _on_template_save/_on_template_rename の
    重複名/空名 messagebox.showerror 拒否経路を実 bound method 呼び出しで
    検証する（02-VERIFICATION.md behavior_unverified_items の3件目）。
    """

    def test_save_rejects_duplicate_name(self, monkeypatch):
        """既存名を askstring で入力すると showerror が呼ばれ、既存テンプレート
        内容が上書きされない。"""
        current_settings = {
            "prompt_templates": {
                "active": "",
                "items": {"dup": {"custom_prompt": "orig", "summary_prompt": "orig2"}},
            }
        }
        d = _make_template_dialog(
            current_settings, custom_text="new", summary_text="new2"
        )
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.simpledialog.askstring",
            lambda *a, **k: "dup",
        )
        error_calls = []
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.showerror",
            lambda *a, **k: error_calls.append((a, k)),
        )

        d._on_template_save()

        assert len(error_calls) == 1
        assert current_settings["prompt_templates"]["items"]["dup"] == {
            "custom_prompt": "orig",
            "summary_prompt": "orig2",
        }

    def test_save_rejects_empty_name(self, monkeypatch):
        """空白のみの名前を askstring で入力すると showerror が呼ばれ、
        テンプレートが追加されない。"""
        current_settings = {"prompt_templates": {"active": "", "items": {}}}
        d = _make_template_dialog(current_settings)
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.simpledialog.askstring",
            lambda *a, **k: "   ",
        )
        error_calls = []
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.showerror",
            lambda *a, **k: error_calls.append((a, k)),
        )

        d._on_template_save()

        assert len(error_calls) == 1
        assert current_settings["prompt_templates"]["items"] == {}

    def test_rename_rejects_duplicate_name(self, monkeypatch):
        """別の既存名を askstring で入力すると showerror が呼ばれ、リネームが
        行われず items のキー集合が変化しない。"""
        current_settings = {
            "prompt_templates": {
                "active": "",
                "items": {
                    "old": {"custom_prompt": "o", "summary_prompt": "o2"},
                    "taken": {"custom_prompt": "t", "summary_prompt": "t2"},
                },
            }
        }
        d = _make_template_dialog(current_settings, template_var_value="old")
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.simpledialog.askstring",
            lambda *a, **k: "taken",
        )
        error_calls = []
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.showerror",
            lambda *a, **k: error_calls.append((a, k)),
        )

        d._on_template_rename()

        assert len(error_calls) == 1
        assert set(current_settings["prompt_templates"]["items"].keys()) == {
            "old",
            "taken",
        }


class TestTemplateDeleteButtonState:
    """D-03（V180-TMPL-03・UI 経由）: _refresh_template_delete_state の削除
    ボタン disabled/!disabled 切替を実 bound method 呼び出しで検証する
    （02-VERIFICATION.md behavior_unverified_items の4件目）。
    """

    def test_active_selection_disables_delete_button(self):
        """アクティブテンプレートを選択中は削除ボタンが disabled になる。"""
        current_settings = {
            "prompt_templates": {
                "active": "A",
                "items": {"A": {"custom_prompt": "a", "summary_prompt": "a2"}},
            }
        }
        d = _make_template_dialog(
            current_settings, active_template_name="A", template_var_value="A"
        )

        d._refresh_template_delete_state()

        assert d.template_delete_btn.last_state == ["disabled"]

    def test_inactive_selection_enables_delete_button(self):
        """非アクティブテンプレートを選択中は削除ボタンが !disabled になる。"""
        current_settings = {
            "prompt_templates": {
                "active": "A",
                "items": {
                    "A": {"custom_prompt": "a", "summary_prompt": "a2"},
                    "B": {"custom_prompt": "b", "summary_prompt": "b2"},
                },
            }
        }
        d = _make_template_dialog(
            current_settings, active_template_name="A", template_var_value="B"
        )

        d._refresh_template_delete_state()

        assert d.template_delete_btn.last_state == ["!disabled"]
