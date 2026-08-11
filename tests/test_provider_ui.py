# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR-UI-01/02/03 向け自動回帰テスト

各ギャップに対して Tk ウィジェット生成を行わず、
ロジック層のみを検証するユニットテスト群。
"""

import ast
import pathlib
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

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

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


def _bind_ocr_button_state_methods(stub):
    """`_update_ocr_buttons_state`/`_update_batch_menu_state` を SimpleNamespace
    スタブへバインドする（V190-SAFE-03・D-04 裁量項目の配線が両メソッドを
    直接呼ぶため、未バインドだと AttributeError になる）。
    """
    from pagefolio.app import PDFEditorApp

    if not hasattr(stub, "doc"):
        stub.doc = None
    stub._update_batch_menu_state = lambda: PDFEditorApp._update_batch_menu_state(stub)
    stub._update_ocr_buttons_state = lambda: PDFEditorApp._update_ocr_buttons_state(
        stub
    )
    return stub


def _call_update_ocr_buttons_state(settings, doc, ocr_buttons=None):
    """PDFEditorApp._update_ocr_buttons_state を最小スタブで呼び出す。

    Tk を生成せず settings/doc/_ocr_buttons だけを持つ名前空間で呼ぶ。
    _update_ocr_buttons_state は末尾で _update_batch_menu_state() を直接
    呼ぶため（V190-SAFE-03・D-04・裁量項目の配線）、SimpleNamespace でも
    解決できるよう明示的にバインドする（未バインドだと AttributeError）。
    _tools_menu/_batch_menu_index を持たないスタブでは getattr ガードにより
    no-op で早期 return する（実装側の防御的パターン）。
    """
    from pagefolio.app import PDFEditorApp

    stub = types.SimpleNamespace(
        settings=settings,
        doc=doc,
    )
    if ocr_buttons is not None:
        stub._ocr_buttons = ocr_buttons
    _bind_ocr_button_state_methods(stub)
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

        _bind_ocr_button_state_methods(stub)
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

    def test_missing_ocr_provider_key_matches_build_provider_default(self):
        """01-REVIEW.md WR-02 回帰テスト: settings に "ocr_provider" キーが
        存在しない場合、UI 側（_update_ocr_buttons_state）の活性判定と
        build_provider の実際の挙動が一致することを検証する。

        修正前は UI 側の既定値が "off"（disabled 表示）、build_provider
        側の既定値が "lmstudio"（プロバイダ生成に成功）と食い違っており、
        「見た目は OFF なのに実行経路は動く」という危険な不一致があった。
        通常経路では _load_settings() が常にキーを補完するため顕在化しない
        が、DEFAULT_OCR_PROVIDER への一元化により両者が構造的に一致する
        ことを担保する。
        """
        from pagefolio import ocr as ocr_module

        btn = _ButtonStub()
        settings_without_key = {}  # "ocr_provider" キーなし
        _call_update_ocr_buttons_state(
            settings=settings_without_key,
            doc=object(),
            ocr_buttons=[btn],
        )
        # UI 側: キー欠落時も enable される（build_provider が実際に
        # プロバイダを生成できることと一致させる）
        assert btn.last_state == ["!disabled"]

        # build_provider 側: 同じ「キーなし」設定で例外を出さず生成できる
        # （後方互換契約 test_no_ocr_provider_key_returns_lmstudio_provider
        # と同じ前提）
        provider = ocr_module.build_provider(dict(settings_without_key))
        assert provider is not None

        # 両者の既定値が同一の情報源（DEFAULT_OCR_PROVIDER）であること
        assert ocr_module.DEFAULT_OCR_PROVIDER != "off"


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

    def test_provider_combo_values_include_openai_via_catalog(self):
        """provider_combo の values は catalog.provider_names() 由来であり
        'openai' を含む（V190-OAI-01・02-03 Task 2）。既存 7 プロバイダの
        並び順（off/lmstudio/ollama/runpod/claude/gemini/tesseract）は不変
        のまま openai が末尾に追加される。
        """
        from pagefolio.ocr_providers import catalog

        names = catalog.provider_names()
        assert names == [
            "off",
            "lmstudio",
            "ollama",
            "runpod",
            "claude",
            "gemini",
            "tesseract",
            "openai",
        ]

    def test_openai_section_frame_exists_in_source(self):
        """llm_config パッケージに openai_section_frame の定義が存在する。"""
        src = _read_llm_config_package_source()
        assert "openai_section_frame" in src
        assert "openai_model_var" in src
        assert "openai_api_key_var" in src


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

    def test_openai_settings_returns_true(self):
        """V190-CAT-01: settings.ocr_provider == 'openai' のとき True を返す。"""
        stub = _make_dialog_stub(settings={"ocr_provider": "openai"})
        assert stub._is_cloud_provider() is True

    def test_openai_provider_instance_returns_true(self):
        """provider が OpenAIProvider インスタンスのとき設定に関わらず True。"""
        from pagefolio.ocr_providers import OpenAIProvider

        provider = OpenAIProvider(api_key="x", model="gpt-5.1")
        stub = _make_dialog_stub(
            settings={"ocr_provider": "lmstudio"},
            provider=provider,
        )
        assert stub._is_cloud_provider() is True

    def test_unregistered_plugin_name_returns_false(self):
        """D-04: catalog 未登録のプラグイン名（isinstance ガードにも一致しない）は
        False を返す。"""
        stub = _make_dialog_stub(settings={"ocr_provider": "my-custom-plugin"})
        assert stub._is_cloud_provider() is False


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

    def test_openai_unresolved_shows_error_and_returns_false(self, monkeypatch):
        """V190-CAT-01: openai 未解決なら ocr_api_key_missing_openai 由来の
        エラーが表示され False を返す。"""
        self._clear_all_env(monkeypatch)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        stub = self._make_stub("openai")
        captured = {}

        def mock_showerror(title, msg, parent=None):
            captured["title"] = title
            captured["msg"] = msg
            captured["parent"] = parent

        monkeypatch.setattr("pagefolio.ocr_dialog.messagebox.showerror", mock_showerror)
        assert stub._check_cloud_api_key() is False
        assert captured
        assert "OPENAI_API_KEY" in captured["msg"]
        # env_var 埋め込みだけでは汎用テンプレートとの誤 fallback を検知
        # できない（両テンプレートとも env_var を含むため）。openai 専用
        # 文言（"OpenAI APIキー"）で catalog.api_key_missing_lang_key_for
        # が実際に openai 固有キーへ解決していることを固定する。
        assert "OpenAI APIキー" in captured["msg"]

    def test_openai_session_key_resolves_without_messagebox(self, monkeypatch):
        """openai セッションキーが設定済みなら True・messagebox 非呼び出し。"""
        self._clear_all_env(monkeypatch)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        stub = self._make_stub("openai", session_keys={"openai": "dummy-test-key"})
        called = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.showerror",
            lambda *a, **kw: called.append((a, kw)),
        )
        assert stub._check_cloud_api_key() is True
        assert called == []

    def test_openai_env_var_resolves_without_messagebox(self, monkeypatch):
        """OPENAI_API_KEY 環境変数のみでも True・messagebox 非呼び出し。"""
        self._clear_all_env(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "dummy-env-key")
        stub = self._make_stub("openai")
        called = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.showerror",
            lambda *a, **kw: called.append((a, kw)),
        )
        assert stub._check_cloud_api_key() is True
        assert called == []


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

    def test_confirm_cost_openai_shows_openai_host(self, monkeypatch):
        """V190-OAI-04: openai 選択時、_confirm_cost のメッセージに
        api.openai.com が含まれる。
        """
        stub = self._make_confirm_stub(page_indices=[0, 1], provider="openai")
        captured = {}
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost()
        assert "api.openai.com" in captured["msg"]

    def test_confirm_cost_openai_default_model_used_when_unset(self, monkeypatch):
        """openai_model 未設定時、catalog 既定モデル(gpt-5.1)が
        _estimate_cost へ渡される（レビュー 02-02 の catalog.default_model_for
        経路の機械保証）。
        """
        stub = self._make_confirm_stub(page_indices=[0], provider="openai")
        captured = {}
        original_estimate = stub._estimate_cost

        def _spy(model, count):
            captured["model"] = model
            return original_estimate(model, count)

        stub._estimate_cost = _spy
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno", lambda *a, **kw: True
        )
        stub._confirm_cost()
        assert captured["model"] == "gpt-5.1"


class TestProviderDisplayNameCatalog:
    """V190-CAT-01: 表示名解決2実装（_provider_display_name /
    _provider_key_to_display_name）が catalog を単一情報源として一致する
    ことの機械保証（レビュー 02-02 対応）。
    """

    ALL_PROVIDERS = [
        "off",
        "lmstudio",
        "ollama",
        "runpod",
        "claude",
        "gemini",
        "tesseract",
        "openai",
    ]

    def _stub(self, ocr_provider):
        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog

        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings={"ocr_provider": ocr_provider}),
            provider=None,
            _L=LANG["ja"],
        )
        stub._provider_display_name = lambda: OCRDialog._provider_display_name(stub)
        stub._provider_key_to_display_name = lambda name: (
            OCRDialog._provider_key_to_display_name(stub, name)
        )
        return stub

    @pytest.mark.parametrize("name", ALL_PROVIDERS)
    def test_both_implementations_agree(self, name):
        """8 プロバイダすべてで _provider_display_name と
        _provider_key_to_display_name が同じ表示名を返す。"""
        stub = self._stub(name)
        assert stub._provider_display_name() == stub._provider_key_to_display_name(name)

    def test_empty_string_resolves_as_lmstudio(self):
        """空文字は lmstudio として解決される（既存挙動維持）。"""
        from pagefolio.constants import LANG

        stub = self._stub("")
        expected = LANG["ja"]["ocr_provider_name_lmstudio"]
        assert stub._provider_display_name() == expected
        assert stub._provider_key_to_display_name("") == expected

    def test_unregistered_name_passthrough(self):
        """catalog 未登録の名前はそのまま返る（フォールバック挙動維持）。"""
        stub = self._stub("mystery-plugin")
        assert stub._provider_display_name() == "mystery-plugin"
        assert stub._provider_key_to_display_name("mystery-plugin") == "mystery-plugin"

    def test_openai_display_name(self):
        """openai の表示名が lang.py の ocr_provider_name_openai と一致する。"""
        from pagefolio.constants import LANG

        stub = self._stub("openai")
        assert stub._provider_display_name() == LANG["ja"]["ocr_provider_name_openai"]


class TestFallbackCandidateHostCatalog:
    """V190-CAT-01: _fallback_candidate_host が catalog 経由でも移行前と
    同じ文字列を返すことを固定する（fallback_eligible な各プロバイダ）。
    """

    def _stub(self, settings):
        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog

        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings=settings),
            _L=LANG["ja"],
        )
        stub._fallback_candidate_host = lambda candidate: (
            OCRDialog._fallback_candidate_host(stub, candidate)
        )
        return stub

    def test_claude_returns_fixed_host(self):
        stub = self._stub({})
        assert stub._fallback_candidate_host("claude") == "api.anthropic.com"

    def test_gemini_returns_fixed_host(self):
        stub = self._stub({})
        assert (
            stub._fallback_candidate_host("gemini")
            == "generativelanguage.googleapis.com"
        )

    def test_openai_returns_fixed_host(self):
        stub = self._stub({})
        assert stub._fallback_candidate_host("openai") == "api.openai.com"

    def test_runpod_uses_settings_url(self):
        stub = self._stub({"runpod_url": "http://runpod.example/x"})
        assert stub._fallback_candidate_host("runpod") == "http://runpod.example/x"

    def test_runpod_unset_shows_placeholder(self):
        from pagefolio.constants import LANG

        stub = self._stub({})
        assert (
            stub._fallback_candidate_host("runpod")
            == LANG["ja"]["llm_runpod_host_unset"]
        )

    def test_lmstudio_uses_settings_url(self):
        stub = self._stub({"lm_studio_url": "http://example:9999"})
        assert stub._fallback_candidate_host("lmstudio") == "http://example:9999"

    def test_lmstudio_default_url(self):
        stub = self._stub({})
        assert stub._fallback_candidate_host("lmstudio") == "http://localhost:1234"

    def test_ollama_uses_settings_url(self):
        stub = self._stub({"ollama_url": "http://example:7777"})
        assert stub._fallback_candidate_host("ollama") == "http://example:7777"

    def test_tesseract_returns_display_name(self):
        from pagefolio.constants import LANG

        stub = self._stub({})
        assert (
            stub._fallback_candidate_host("tesseract")
            == LANG["ja"]["ocr_provider_name_tesseract"]
        )


class TestResolvedHostTextUnknown:
    """レビュー MEDIUM-8: catalog 未登録のクラウド継承プラグインで
    _confirm_cost が送信先不明を明示すること（プロバイダ表示名だけで
    済ませていないこと）を固定する。
    """

    def test_unregistered_cloud_plugin_shows_host_unknown(self, monkeypatch):
        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import ClaudeProvider

        class _DummyCloudPlugin(ClaudeProvider):
            """ClaudeProvider を継承した catalog 未登録のダミープラグイン。"""

        settings = {"ocr_provider": "dummy-cloud-plugin"}
        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings=settings),
            page_indices=[0],
            provider=_DummyCloudPlugin(api_key="x", model="dummy-model"),
            _L=LANG["ja"],
        )
        stub._estimate_cost = lambda m, c: OCRDialog._estimate_cost(stub, m, c)
        stub._confirm_cost = lambda: OCRDialog._confirm_cost(stub)

        captured = {}
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost()
        expected_host_text = LANG["ja"]["ocr_host_unknown"].format(
            provider="dummy-cloud-plugin"
        )
        assert expected_host_text in captured["msg"]


class TestVisionUnverifiedNotice:
    """レビュー HIGH 02-02-2: vision 確認済み集合外の openai モデル選択時に
    画像入力未確認の注記が追加されることを固定する。
    """

    def _make_stub(self, openai_model):
        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog

        settings = {"ocr_provider": "openai", "openai_model": openai_model}
        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(settings=settings),
            page_indices=[0],
            _L=LANG["ja"],
        )
        stub._estimate_cost = lambda m, c: OCRDialog._estimate_cost(stub, m, c)
        stub._confirm_cost = lambda: OCRDialog._confirm_cost(stub)
        return stub

    def test_unverified_model_adds_note(self, monkeypatch):
        stub = self._make_stub("gpt-9-hypothetical")
        captured = {}
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost()
        from pagefolio.constants import LANG

        note = LANG["ja"]["ocr_model_vision_unverified"].format(
            model="gpt-9-hypothetical"
        )
        assert note in captured["msg"]

    def test_verified_model_no_note(self, monkeypatch):
        from pagefolio.constants import LANG
        from pagefolio.ocr_providers import OpenAIProvider

        stub = self._make_stub(OpenAIProvider.RECOMMENDED_MODELS[0])
        captured = {}
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda title, msg, parent=None: captured.update({"msg": msg}) or True,
        )
        stub._confirm_cost()
        marker = LANG["ja"]["ocr_model_vision_unverified"].split("{")[0]
        assert marker not in captured["msg"]


class TestConfirmDenialStopsSend:
    """レビュー 02-02 Suggestion 3: 確認ダイアログで「いいえ」を選んだとき
    build_provider にも HTTP 送信にも到達しないことを固定する。
    """

    def test_openai_denial_never_reaches_build_provider_or_http(self, monkeypatch):
        import threading

        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog

        build_calls = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.build_provider",
            lambda *a, **kw: build_calls.append((a, kw)),
        )

        def _raise_if_called(*a, **kw):
            raise AssertionError("urlopen が呼ばれた（HTTP 送信に到達した）")

        monkeypatch.setattr("urllib.request.urlopen", _raise_if_called)
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno", lambda *a, **kw: False
        )

        app = types.SimpleNamespace(
            settings={"ocr_provider": "openai"}, _session_api_keys={}
        )
        fake = types.SimpleNamespace(
            app=app,
            provider=None,
            _started=False,
            _done=False,
            _summary_running=False,
            page_indices=[0],
            _cancel_flag=threading.Event(),
            _L=LANG["ja"],
        )
        fake._is_cloud_provider = lambda settings=None: OCRDialog._is_cloud_provider(
            fake, settings
        )
        fake._check_cloud_api_key = lambda settings=None: True
        fake._estimate_cost = lambda m, c: OCRDialog._estimate_cost(fake, m, c)
        fake._confirm_cost = lambda page_count, settings=None: OCRDialog._confirm_cost(
            fake, page_count, settings
        )

        OCRDialog._on_run(fake)

        assert fake._started is False, "拒否後に OCR 実行が開始されている"
        assert build_calls == [], "拒否後に build_provider が呼ばれた"


class TestTextCapableProvidersParity:
    """レビュー MEDIUM-9: _TEXT_CAPABLE_PROVIDERS が catalog 登録プロバイダの
    うち Provider クラスの supports_text_prompt が真であるプロバイダ名の
    集合と一致することを固定する（追記漏れ検知装置）。
    """

    def test_matches_supports_text_prompt_projection(self):
        from pagefolio.ocr_dialog import _TEXT_CAPABLE_PROVIDERS
        from pagefolio.ocr_providers import (
            ClaudeProvider,
            GeminiProvider,
            LMStudioProvider,
            OllamaProvider,
            OpenAIProvider,
            RunPodProvider,
            TesseractProvider,
            catalog,
        )

        # 名前 → クラスの対応表はテスト側に置く（catalog は Provider を
        # import しない・D-05）。
        name_to_class = {
            "lmstudio": LMStudioProvider,
            "ollama": OllamaProvider,
            "runpod": RunPodProvider,
            "claude": ClaudeProvider,
            "gemini": GeminiProvider,
            "tesseract": TesseractProvider,
            "openai": OpenAIProvider,
        }
        expected = {
            name
            for name in catalog.PROVIDERS
            if name in name_to_class
            and getattr(name_to_class[name], "supports_text_prompt", False)
        }
        assert _TEXT_CAPABLE_PROVIDERS == frozenset(expected)


class TestOpenAIPriceProvenance:
    """レビュー HIGH-2/MEDIUM-16: OpenAI 単価プロヴェナンスの4層検証。

    実際の金額の正しさ自体は 02-CAPABILITY-MATRIX.md の出典 URL・参照日と
    02-04 Task 3B の human-verify（公式価格ページとの突き合わせ）が担保する。
    本テストは (1)両ファイル一致 (2)プロヴェナンス形式妥当性 (3)推奨/既定
    モデル全解決 (4)入出力単価の実世界不変条件、の4層を機械的に固定する
    （辞書同士の一致だけでは「同じ誤値」を防げないため）。
    """

    def test_layer1_price_table_and_source_match_across_files(self):
        from pagefolio.dialogs.batch_ocr import (
            OCR_PRICE_TABLE as batch_table,
        )
        from pagefolio.dialogs.batch_ocr import (
            OPENAI_PRICE_SOURCE as batch_source,
        )
        from pagefolio.ocr_dialog import (
            OCR_PRICE_TABLE as dialog_table,
        )
        from pagefolio.ocr_dialog import (
            OPENAI_PRICE_SOURCE as dialog_source,
        )

        assert dialog_table == batch_table
        assert list(dialog_table) == list(batch_table)
        assert dialog_source == batch_source

    def test_layer2_source_provenance_format(self):
        import re

        from pagefolio.ocr_dialog import OPENAI_PRICE_SOURCE

        assert set(OPENAI_PRICE_SOURCE) == {"url", "retrieved", "unit", "currency"}
        assert OPENAI_PRICE_SOURCE["url"].startswith("https://")
        assert re.fullmatch(r"20\d\d-\d\d-\d\d", OPENAI_PRICE_SOURCE["retrieved"])
        assert OPENAI_PRICE_SOURCE["unit"]
        assert OPENAI_PRICE_SOURCE["currency"]

    def test_layer3_all_recommended_and_default_models_resolve(self):
        from pagefolio.dialogs.batch_ocr import _PRICE_FALLBACK as batch_fallback
        from pagefolio.dialogs.batch_ocr import _lookup_price as batch_lookup
        from pagefolio.ocr_dialog import _PRICE_FALLBACK as dialog_fallback
        from pagefolio.ocr_dialog import _lookup_price as dialog_lookup
        from pagefolio.ocr_providers import OpenAIProvider, catalog

        models = set(OpenAIProvider.RECOMMENDED_MODELS)
        models.add(catalog.default_model_for("openai"))
        for model in models:
            assert dialog_lookup(model) != dialog_fallback, model
            assert batch_lookup(model) != batch_fallback, model

    def test_layer4_price_invariants(self):
        from pagefolio.ocr_dialog import OCR_PRICE_TABLE

        openai_keys = ["gpt-5-nano", "gpt-5-mini", "gpt-5.1", "gpt-5.2", "gpt-4o"]
        for key in openai_keys:
            input_price, output_price = OCR_PRICE_TABLE[key]
            assert input_price > 0, key
            assert output_price > 0, key
            assert input_price < output_price, key


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


def _make_apply_key_stub(
    session_api_keys,
    claude_key="",
    gemini_key="",
    runpod_key="",
    openai_key="",
):
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
        openai_model_var=_GetVarStub("gpt-5.1"),
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
        openai_api_key_var=_GetVarStub(openai_key),
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

    def test_openai_key_not_in_llm_settings(self):
        """V190-OAI-02: openai 欄にダミーキーを入れても llm_settings に
        openai_api_key / OPENAI_API_KEY が含まれない。
        """
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(session, openai_key="sk-DUMMY-TEST-KEY")
        captured = {}
        stub.on_apply = lambda s: captured.update(s)
        LLMConfigDialog._apply(stub)

        assert "openai_api_key" not in captured
        assert "OPENAI_API_KEY" not in captured
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


class TestOpenAiSessionKeySlot:
    """V190-OAI-02: OpenAI 欄の値が _session_api_keys["openai"] に格納され、
    他プロバイダのスロットを汚染しない（TestRunpodSessionKeySlot と同型）。
    """

    def test_openai_key_goes_to_openai_slot(self):
        """openai 欄のダミーキーが _session_api_keys["openai"] に入る。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(session, openai_key="sk-DUMMY-TEST-KEY")
        LLMConfigDialog._apply(stub)

        assert session.get("openai") == "sk-DUMMY-TEST-KEY"

    def test_openai_key_does_not_pollute_claude_slot(self):
        """openai 欄にのみ値を入れても "claude" スロットは汚染されない。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(session, openai_key="sk-DUMMY-TEST-KEY")
        LLMConfigDialog._apply(stub)

        assert "claude" not in session

    def test_empty_openai_key_clears_existing_session_entry(self):
        """空欄で _apply すると既存の openai エントリが除去される（D-06）。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {"openai": "old-dummy-key"}
        stub = _make_apply_key_stub(session, openai_key="")
        LLMConfigDialog._apply(stub)

        assert "openai" not in session

    def test_all_four_slots_independent(self):
        """claude/gemini/runpod/openai の4欄を入力すると各自のスロットへ
        独立格納される。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        session = {}
        stub = _make_apply_key_stub(
            session,
            claude_key="sk-ant-DUMMY",
            gemini_key="AIza-DUMMY",
            runpod_key="rp-DUMMY",
            openai_key="sk-DUMMY",
        )
        LLMConfigDialog._apply(stub)

        assert session["claude"] == "sk-ant-DUMMY"
        assert session["gemini"] == "AIza-DUMMY"
        assert session["runpod"] == "rp-DUMMY"
        assert session["openai"] == "sk-DUMMY"


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
        _bind_ocr_button_state_methods(stub)
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
        _bind_ocr_button_state_methods(stub)
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
        _bind_ocr_button_state_methods(stub)
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
        _bind_ocr_button_state_methods(app_stub)
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
    """D-05（V180-TMPL-04）: _on_template_change の未保存差分確認による
    切替中止（D-05）を実 bound method 呼び出しで検証する
    （02-VERIFICATION.md behavior_unverified_items の1件目・2件目）。

    旧 D-07 は「切替の都度、選択テンプレートの内容で外部ファイルを上書き
    する」ことを検証していたが、v1.9.0 D-15（外部ファイルへの書き込みは
    Apply 押下時の1経路へ一本化）により挙動が反転した。本クラスの
    「上書き」系テストは「切替経路からは一切書き込みが発生しないことの
    検証」へ置き換わっている。
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
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: False,
        )
        save_calls = []
        monkeypatch.setattr(
            "pagefolio.settings.save_prompt_file",
            lambda f, content: save_calls.append((f, content)),
        )

        d._on_template_change()

        assert d.template_var.get() == "A"
        assert d.ocr_prompt_text.get("1.0", "end") == "edited"
        assert save_calls == []

    def test_confirmed_switch_does_not_touch_external_files(self, monkeypatch):
        """未保存差分なしの切替確定後、選択テンプレートの内容は入力欄へ反映
        されるが、外部ファイルへの書き込みは発生しない（v1.9.0 D-15・書き込み
        は Apply のみ）。
        """
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
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: True,
        )
        save_calls = []
        monkeypatch.setattr(
            "pagefolio.settings.save_prompt_file",
            lambda f, content: save_calls.append((f, content)),
        )

        d._on_template_change()

        assert save_calls == []
        assert d._active_template_name == "B"
        assert d.ocr_prompt_text.get("1.0", "end") == "newC"

    def test_no_active_template_warns_on_unsaved_freeform_text(self, monkeypatch):
        """02-REVIEW WR-03 回帰テスト: ファイル非連動・かつ今セッションで
        まだテンプレートを選んでいない（_active_template_name==""）状態でも、
        入力欄に自由入力テキストがあればテンプレート切替時に askyesno による
        確認が発生し、キャンセル（False）を返せば入力内容が保持されたまま
        切替が中止されることを検証する。
        """
        current_settings = {
            "prompt_templates": {
                "active": "",
                "items": {
                    "B": {"custom_prompt": "b", "summary_prompt": "b2"},
                },
            }
        }
        d = _make_template_dialog(
            current_settings,
            active_template_name="",
            template_var_value="B",
            custom_text="typed-but-unsaved",
            summary_text="",
        )
        askyesno_calls = []

        def _fake_askyesno(*a, **k):
            askyesno_calls.append((a, k))
            return False

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            _fake_askyesno,
        )
        save_calls = []
        monkeypatch.setattr(
            "pagefolio.settings.save_prompt_file",
            lambda f, content: save_calls.append((f, content)),
        )

        d._on_template_change()

        assert len(askyesno_calls) == 1
        assert d.template_var.get() == ""
        assert d.ocr_prompt_text.get("1.0", "end") == "typed-but-unsaved"
        assert save_calls == []

    def test_change_leaves_external_md_file_untouched(self, monkeypatch, tmp_path):
        """v1.9.0 D-15 実ファイル検証版: settings._get_base_dir を tmp_path へ
        差し替え、save_prompt_file/prompt_file_exists/load_prompt_file は一切
        monkeypatch せず実関数のまま通す。テンプレート切替後も
        ocr_custom_prompt.md/ocr_summary_prompt.md の内容が作成時のままで
        あることをファイル読み取りで確認する（外部ファイルへの書き込みは
        Apply 押下時のみに一本化された・02-VERIFICATION.md
        behavior_unverified_items[1] の test 欄と対応）。
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

        custom_content = (tmp_path / CUSTOM_PROMPT_FILE).read_text(encoding="utf-8")
        summary_content = (tmp_path / SUMMARY_PROMPT_FILE).read_text(encoding="utf-8")
        assert custom_content == "old-custom"
        assert summary_content == "old-summary"


# ══════════════════════════════════════════════════════════════
#  V190-CFG-01/02（01-03）: Apply 一本化契約と未保存確認の単一経路化を
#  実ファイル検証を含めて固定する回帰テスト群。
# ══════════════════════════════════════════════════════════════


class TestApplyOnlyPromptFileWrite:
    """V190-CFG-01: 外部プロンプトファイルへの書き込みが Apply 押下時
    （`dialog.py:_apply`）のみで発生し、テンプレート切替・Cancel からは
    一切副作用が及ばないことを検証する。
    """

    def test_template_change_does_not_write_prompt_files(self, monkeypatch, tmp_path):
        """テンプレート切替を複数回行っても外部 md ファイルは変化しない。"""
        from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE

        monkeypatch.setattr("pagefolio.settings._get_base_dir", lambda: str(tmp_path))
        (tmp_path / CUSTOM_PROMPT_FILE).write_text("base-custom", encoding="utf-8")
        (tmp_path / SUMMARY_PROMPT_FILE).write_text("base-summary", encoding="utf-8")

        current_settings = {
            "prompt_templates": {
                "active": "A",
                "items": {
                    "A": {"custom_prompt": "a-custom", "summary_prompt": "a-summary"},
                    "B": {"custom_prompt": "b-custom", "summary_prompt": "b-summary"},
                },
            }
        }
        d = _make_template_dialog(
            current_settings,
            active_template_name="A",
            template_var_value="A",
            custom_text="a-custom",
            summary_text="a-summary",
        )
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: True,
        )

        d.template_var.set("B")
        d._on_template_change()
        d.template_var.set("A")
        d._on_template_change()
        d.template_var.set("B")
        d._on_template_change()

        custom_content = (tmp_path / CUSTOM_PROMPT_FILE).read_text(encoding="utf-8")
        summary_content = (tmp_path / SUMMARY_PROMPT_FILE).read_text(encoding="utf-8")
        assert custom_content == "base-custom"
        assert summary_content == "base-summary"

    def test_cancel_leaves_prompt_files_unchanged(self, tmp_path, monkeypatch):
        """入力欄を編集しても Apply を呼ばなければ（＝Cancel）外部ファイルは
        変化しない。Apply を呼ばないことが Cancel の定義であることを明示する。
        """
        from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE

        monkeypatch.setattr("pagefolio.settings._get_base_dir", lambda: str(tmp_path))
        (tmp_path / CUSTOM_PROMPT_FILE).write_text("stable-custom", encoding="utf-8")
        (tmp_path / SUMMARY_PROMPT_FILE).write_text("stable-summary", encoding="utf-8")

        # 入力欄を編集する（_apply は一切呼ばない＝Cancel 経路の模擬）
        stub = _make_apply_key_stub({})
        stub.ocr_prompt_text = _GetTextStub("edited-but-not-applied")
        stub.ocr_summary_prompt_text = _GetTextStub("edited-summary-not-applied")
        stub.destroy()

        custom_content = (tmp_path / CUSTOM_PROMPT_FILE).read_text(encoding="utf-8")
        summary_content = (tmp_path / SUMMARY_PROMPT_FILE).read_text(encoding="utf-8")
        assert custom_content == "stable-custom"
        assert summary_content == "stable-summary"

    def test_apply_writes_input_field_content_not_active_template(
        self, monkeypatch, tmp_path
    ):
        """D-16: Apply が書き込む内容は入力欄の現在値であり、アクティブ
        テンプレートの保存済み値ではない。
        """
        from pagefolio.constants import CUSTOM_PROMPT_FILE
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        monkeypatch.setattr("pagefolio.settings._get_base_dir", lambda: str(tmp_path))
        (tmp_path / CUSTOM_PROMPT_FILE).write_text(
            "X-saved-template-value", encoding="utf-8"
        )

        stub = _make_apply_key_stub({})
        stub.ocr_prompt_text = _GetTextStub("Y-current-input-field-value")

        LLMConfigDialog._apply(stub)

        written = (tmp_path / CUSTOM_PROMPT_FILE).read_text(encoding="utf-8")
        assert written == "Y-current-input-field-value"

    def test_apply_does_not_create_missing_prompt_files(self, monkeypatch, tmp_path):
        """D-17: 外部 md ファイルが存在しない場合、Apply しても新規作成しない。"""
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        monkeypatch.setattr("pagefolio.settings._get_base_dir", lambda: str(tmp_path))

        stub = _make_apply_key_stub({})
        stub.ocr_prompt_text = _GetTextStub("some content")
        stub.ocr_summary_prompt_text = _GetTextStub("some summary")

        LLMConfigDialog._apply(stub)

        assert list(tmp_path.glob("*.md")) == []

    def test_apply_overwrites_externally_edited_file_with_input_content(
        self, monkeypatch, tmp_path
    ):
        """probe: CFG-01 / concurrency — ダイアログ表示中に外部エディタで
        ファイルが直接編集されても、Apply は入力欄の現在値でファイルを
        上書きする（D-16 の WYSIWYG 契約により Apply が最後の書き手になる）。
        """
        from pagefolio.constants import CUSTOM_PROMPT_FILE
        from pagefolio.dialogs.llm_config import LLMConfigDialog

        monkeypatch.setattr("pagefolio.settings._get_base_dir", lambda: str(tmp_path))
        (tmp_path / CUSTOM_PROMPT_FILE).write_text("original", encoding="utf-8")

        stub = _make_apply_key_stub({})
        stub.ocr_prompt_text = _GetTextStub("input-field-current-value")

        # ダイアログ表示中に外部エディタでファイルが直接編集された状況を再現
        (tmp_path / CUSTOM_PROMPT_FILE).write_text(
            "externally-edited", encoding="utf-8"
        )

        LLMConfigDialog._apply(stub)

        written = (tmp_path / CUSTOM_PROMPT_FILE).read_text(encoding="utf-8")
        assert written == "input-field-current-value"

    def test_open_cancel_twice_leaves_files_unchanged(self, tmp_path, monkeypatch):
        """probe: CFG-01 / idempotency — 「開く→編集→Cancel」を2回繰り返しても
        外部ファイルの内容は1度も変化しない。
        """
        from pagefolio.constants import CUSTOM_PROMPT_FILE, SUMMARY_PROMPT_FILE

        monkeypatch.setattr("pagefolio.settings._get_base_dir", lambda: str(tmp_path))
        (tmp_path / CUSTOM_PROMPT_FILE).write_text("stable-custom", encoding="utf-8")
        (tmp_path / SUMMARY_PROMPT_FILE).write_text("stable-summary", encoding="utf-8")

        for _ in range(2):
            # 開く→編集（Apply は呼ばない）→ Cancel（destroy）
            stub = _make_apply_key_stub({})
            stub.ocr_prompt_text = _GetTextStub("edited-but-cancelled")
            stub.ocr_summary_prompt_text = _GetTextStub("edited-summary-cancelled")
            stub.destroy()

        custom_content = (tmp_path / CUSTOM_PROMPT_FILE).read_text(encoding="utf-8")
        summary_content = (tmp_path / SUMMARY_PROMPT_FILE).read_text(encoding="utf-8")
        assert custom_content == "stable-custom"
        assert summary_content == "stable-summary"


class TestUnsavedTemplateChangesSinglePath:
    """V190-CFG-02（D-18）: `_has_unsaved_template_changes` の判定経路が
    外部ファイルの有無に依存しない単一経路になっていることを検証する。
    """

    def test_selected_template_edit_warns_without_prompt_files(self, monkeypatch):
        """アクティブテンプレート選択済み・入力欄が保存済み値から編集済み・
        外部 md ファイルは存在しない状態でも、別テンプレートへ切り替えると
        askyesno が1回呼ばれる（D-18 の直接の回帰テスト）。
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
            custom_text="edited-not-saved",
            summary_text="saved-A2",
        )
        askyesno_calls = []

        def _fake_askyesno(*a, **k):
            askyesno_calls.append((a, k))
            return True

        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            _fake_askyesno,
        )

        d._on_template_change()

        assert len(askyesno_calls) == 1

    def test_selected_template_unedited_does_not_warn(self, monkeypatch):
        """入力欄がアクティブテンプレートの保存済み値と一致していれば
        askyesno は呼ばれない（過検知の防止）。
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
            custom_text="saved-A",
            summary_text="saved-A2",
        )
        askyesno_calls = []
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: askyesno_calls.append(1) or True,
        )

        d._on_template_change()

        assert askyesno_calls == []

    def test_switch_cancel_restores_active_template_selection(self, monkeypatch):
        """probe: CFG-02 / concurrency — 未保存確認で「いいえ」を選ぶと、
        選択が元のアクティブテンプレートへ戻り、入力欄の内容も保持される。
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
            custom_text="edited-not-saved",
            summary_text="saved-A2",
        )
        monkeypatch.setattr(
            "pagefolio.dialogs.llm_config.sections.messagebox.askyesno",
            lambda *a, **k: False,
        )

        d._on_template_change()

        assert d.template_var.get() == "A"
        assert d.ocr_prompt_text.get("1.0", "end") == "edited-not-saved"


class TestUnsavedTemplateChangesSourceGuard:
    """V190-CFG-02（D-18）: `SectionsMixin._has_unsaved_template_changes` の
    構造的不変条件をソース解析で恒久的に固定する（01-03-PLAN.md Task 1）。

    01-03-SUMMARY.md の D-18 決定は「アクティブテンプレート選択済みの場合、
    外部プロンプトファイルの有無で判定経路を分岐させない（常に保存済み値と
    比較する）」というもの。この不変条件は挙動テスト（
    TestUnsavedTemplateChangesSinglePath）だけでは検出できない回帰がある
    ――既存の3テストは外部ファイルが存在しないケースのみを踏むため、もし
    `prompt_file_exists(...)` による早期 False 分岐が再導入されても
    外部ファイル非存在ケースでは挙動が変わらず、3テストとも green のまま
    通ってしまう。そのため tests/test_pdf_ops.py::TestTempDocumentCloseGuard
    と同型の AST 走査ガードを設け、判定経路が単一であることをソースレベルで
    固定する。
    """

    def _get_method_ast(self):
        """`SectionsMixin._has_unsaved_template_changes` の関数定義ノードを
        AST 上で取得して返す。"""
        import inspect
        import textwrap

        from pagefolio.dialogs.llm_config.sections import SectionsMixin

        source = inspect.getsource(SectionsMixin._has_unsaved_template_changes)
        tree = ast.parse(textwrap.dedent(source))
        (func_def,) = [
            node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        return func_def

    def test_method_body_never_references_prompt_file_exists(self):
        """D-18: メソッド本体のどの Name/Call/属性参照にも
        `prompt_file_exists` という識別子が現れないことを AST で検証する
        （ファイル存在有無での早期分岐が再導入されていないことのピン留め）。
        """
        func_def = self._get_method_ast()

        offending = [
            node
            for node in ast.walk(func_def)
            if isinstance(node, ast.Name) and node.id == "prompt_file_exists"
        ]

        assert not offending, (
            "_has_unsaved_template_changes が prompt_file_exists を参照している"
            "（D-18 の単一経路の不変条件に違反）"
        )

    def test_method_source_substring_never_contains_prompt_file_exists(self):
        """AST 走査を補強する副次的な文字列アサーション（inspect.getsource
        の生ソースに 'prompt_file_exists' という文字列が一切現れないこと）。
        """
        import inspect

        from pagefolio.dialogs.llm_config.sections import SectionsMixin

        src = inspect.getsource(SectionsMixin._has_unsaved_template_changes)

        assert "prompt_file_exists" not in src

    def test_unselected_template_guard_branch_still_present(self):
        """Pitfall 5: 未選択時分岐（`if not self._active_template_name:`）が
        D-18 の最小差分適用後も1つだけ残っていることを AST で検証する
        （この分岐を誤って削除すると自由入力の未保存検知が壊れる）。
        """
        func_def = self._get_method_ast()

        guard_ifs = [
            node
            for node in ast.walk(func_def)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.UnaryOp)
            and isinstance(node.test.op, ast.Not)
            and isinstance(node.test.operand, ast.Attribute)
            and node.test.operand.attr == "_active_template_name"
        ]

        assert len(guard_ifs) == 1, (
            "未選択時分岐 `if not self._active_template_name:` の数が想定と"
            f"異なる（検出数: {len(guard_ifs)}）"
        )


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


# ══════════════════════════════════════════════════════════════
#  Phase 2 Plan 03 Task 3: dialog.py の openai 分岐・往復テスト・
#  model_fetch.py の _refresh_openai_models 配線
# ══════════════════════════════════════════════════════════════


class _FrameStub:
    """tk.Frame の pack/pack_forget を記録する最小スタブ（_FakeLabel と同型）。"""

    def __init__(self):
        self.mapped = False
        self.pack_calls = []
        self.pack_forget_calls = 0

    def pack(self, **kwargs):
        """pack 呼び出しを記録し、表示状態を True にする。"""
        self.mapped = True
        self.pack_calls.append(kwargs)

    def pack_forget(self):
        """pack_forget 呼び出しを記録し、表示状態を False にする。"""
        self.mapped = False
        self.pack_forget_calls += 1


def _make_provider_change_stub(tesseract_available=True):
    """LLMConfigDialog._on_provider_change を Tk 生成なしで呼ぶための
    最小スタブを返す（各プロバイダ固有フレームの pack/pack_forget 状態を
    _FrameStub で記録する）。_on_model_change/_on_openai_model_change/
    _model_supports_effort は実装（DialogMixin の本物のロジック）を
    stub へバインドし、effort/temperature 切替の実挙動を検証できるようにする。
    """
    from pagefolio.dialogs.llm_config import LLMConfigDialog

    stub = types.SimpleNamespace(
        provider_var=_FakeStringVar("off"),
        _tesseract_available=tesseract_available,
        _last_valid_provider="off",
        url_section_frame=_FrameStub(),
        ollama_section_frame=_FrameStub(),
        runpod_section_frame=_FrameStub(),
        claude_section_frame=_FrameStub(),
        gemini_section_frame=_FrameStub(),
        tesseract_section_frame=_FrameStub(),
        openai_section_frame=_FrameStub(),
        _common_section_heading=_FrameStub(),
        effort_frame=_FrameStub(),
        temperature_frame=_FrameStub(),
        scale_row=object(),
        claude_model_var=_FakeStringVar("claude-sonnet-4-6"),
        openai_model_var=_FakeStringVar("gpt-5.1"),
    )
    status_calls = []
    stub._set_lm_status = lambda text, kind="info": status_calls.append((text, kind))
    stub._resize_to_fit = lambda: None
    stub._on_model_change = lambda _event=None: LLMConfigDialog._on_model_change(
        stub, _event
    )
    stub._on_openai_model_change = lambda _event=None: (
        LLMConfigDialog._on_openai_model_change(stub, _event)
    )
    stub._model_supports_effort = lambda model: LLMConfigDialog._model_supports_effort(
        stub, model
    )
    stub._on_provider_change = lambda _event=None: LLMConfigDialog._on_provider_change(
        stub, _event
    )
    stub._status_calls = status_calls
    return stub


class TestOnProviderChangeOpenai:
    """openai 選択時に openai_section_frame が pack され、claude/gemini/
    tesseract が pack_forget されることを確認する（V190-OAI-01）。
    """

    def test_openai_shows_openai_section_and_hides_others(self):
        """openai 選択で openai_section_frame が表示され他が隠れる。"""
        stub = _make_provider_change_stub()
        stub.provider_var.set("openai")
        stub._on_provider_change()

        assert stub.openai_section_frame.mapped is True
        assert stub.claude_section_frame.mapped is False
        assert stub.gemini_section_frame.mapped is False
        assert stub.tesseract_section_frame.mapped is False

    def test_claude_after_openai_hides_openai_section(self):
        """逆に claude を選んだとき openai_section_frame が pack_forget される。"""
        stub = _make_provider_change_stub()
        stub.provider_var.set("openai")
        stub._on_provider_change()
        stub.provider_var.set("claude")
        stub._on_provider_change()

        assert stub.openai_section_frame.mapped is False
        assert stub.claude_section_frame.mapped is True


class TestProviderRoundTripFrameState:
    """レビュー MEDIUM-13: openai → claude → gemini → openai の順に
    _on_provider_change を呼び、各段で temperature_frame/effort_frame/
    openai_section_frame の pack/pack_forget 状態が期待どおりになること。
    最後の openai で 1 回目の openai と同じ状態に戻ることをアサートする
    （分岐の追加漏れ検出装置）。
    """

    def test_round_trip_restores_initial_openai_state(self):
        stub = _make_provider_change_stub()

        # 1 回目: openai（既定モデル gpt-5.1 は推論系 → temperature 省略）
        stub.provider_var.set("openai")
        stub._on_provider_change()
        assert stub.openai_section_frame.mapped is True
        assert stub.temperature_frame.mapped is False
        assert stub.effort_frame.mapped is False
        first_state = (
            stub.openai_section_frame.mapped,
            stub.temperature_frame.mapped,
            stub.effort_frame.mapped,
        )

        # claude（claude-sonnet-4-6 は EFFORT_MODELS 対象 → effort 有効）
        stub.provider_var.set("claude")
        stub._on_provider_change()
        assert stub.openai_section_frame.mapped is False
        assert stub.claude_section_frame.mapped is True
        assert stub.effort_frame.mapped is True
        assert stub.temperature_frame.mapped is False

        # gemini（effort 非対応 → temperature のみ）
        stub.provider_var.set("gemini")
        stub._on_provider_change()
        assert stub.openai_section_frame.mapped is False
        assert stub.claude_section_frame.mapped is False
        assert stub.gemini_section_frame.mapped is True
        assert stub.temperature_frame.mapped is True
        assert stub.effort_frame.mapped is False

        # 2 回目の openai: 1 回目と同じ状態に戻る
        stub.provider_var.set("openai")
        stub._on_provider_change()
        second_state = (
            stub.openai_section_frame.mapped,
            stub.temperature_frame.mapped,
            stub.effort_frame.mapped,
        )
        assert second_state == first_state
        assert stub.gemini_section_frame.mapped is False
        assert stub.claude_section_frame.mapped is False


class TestOnOpenaiModelChange:
    """推論系モデル ID で temperature_frame が pack_forget され、非推論系で
    pack されることを確認する（D-13・単一判定源）。
    """

    def test_reasoning_gpt5_family_hides_temperature_frame(self):
        """gpt-5.1（o 系以外の推論系実例）で temperature_frame が隠れる。"""
        stub = _make_provider_change_stub()
        stub.openai_model_var.set("gpt-5.1")
        stub._on_openai_model_change()
        assert stub.temperature_frame.mapped is False
        assert stub.effort_frame.mapped is False

    def test_reasoning_o_series_hides_temperature_frame(self):
        """o3（o-series の推論系実例）で temperature_frame が隠れる。"""
        stub = _make_provider_change_stub()
        stub.openai_model_var.set("o3")
        stub._on_openai_model_change()
        assert stub.temperature_frame.mapped is False

    def test_non_reasoning_model_shows_temperature_frame(self):
        """gpt-4o（非推論系実例）で temperature_frame が表示される。"""
        stub = _make_provider_change_stub()
        stub.openai_model_var.set("gpt-4o")
        stub._on_openai_model_change()
        assert stub.temperature_frame.mapped is True
        assert stub.effort_frame.mapped is False

    def test_chat_latest_suffix_treated_as_non_reasoning(self):
        """gpt-5-chat-latest（-chat-latest サフィックス）は非推論扱い。"""
        stub = _make_provider_change_stub()
        stub.openai_model_var.set("gpt-5-chat-latest")
        stub._on_openai_model_change()
        assert stub.temperature_frame.mapped is True


class TestOnOpenaiModelChangeStructure:
    """AST ベースの構造アサーション（D-13）。dialog.py の
    _on_openai_model_change 関数ノードに正規表現呼び出し・集合リテラル・
    文字列 prefix 比較が現れず、is_reasoning_model の呼び出しが存在する
    ことを固定する。
    """

    @staticmethod
    def _func():
        source = (
            REPO_ROOT / "pagefolio" / "dialogs" / "llm_config" / "dialog.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_on_openai_model_change"
            ):
                return node
        raise AssertionError("_on_openai_model_change が見つからない")

    def test_calls_is_reasoning_model(self):
        fn = self._func()
        call_names = [
            n.func.id
            for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        ]
        assert "is_reasoning_model" in call_names

    def test_no_regex_reference(self):
        fn = self._func()
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
        assert "re" not in names
        assert not any(a in ("match", "search", "fullmatch") for a in attrs)

    def test_no_set_literal(self):
        fn = self._func()
        assert not any(isinstance(n, (ast.Set, ast.SetComp)) for n in ast.walk(fn))

    def test_no_string_prefix_comparison(self):
        fn = self._func()
        attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
        assert "startswith" not in attrs


class TestRefreshOpenaiModels:
    """_refresh_openai_models の配線・D-08 観測同一性・S5 回帰を検証する。"""

    @staticmethod
    def _make_stub(api_key=""):
        from pagefolio.constants import LANG

        status_calls = []
        async_calls = []

        stub = types.SimpleNamespace(
            openai_api_key_var=_FakeStringVar(api_key),
            openai_model_var=_FakeStringVar("gpt-5.1"),
            openai_model_combo={"values": []},
            _L=LANG["ja"],
        )
        stub._set_lm_status = lambda text, kind="info": status_calls.append(
            (text, kind)
        )

        def _fake_fetch_models_async(fetch_fn, on_success, on_error):
            async_calls.append(
                {
                    "fetch_fn": fetch_fn,
                    "on_success": on_success,
                    "on_error": on_error,
                }
            )

        stub._fetch_models_async = _fake_fetch_models_async
        return stub, status_calls, async_calls

    def test_fetch_models_async_called_once_with_openai_list_models(self, monkeypatch):
        """(a)(b): _fetch_models_async を 1 回だけ呼び、渡す callable は
        OpenAIProvider.list_models である。
        """
        from pagefolio.dialogs.llm_config import model_fetch as model_fetch_mod

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        stub, _status, async_calls = self._make_stub(api_key="sk-test")
        model_fetch_mod.ModelFetchMixin._refresh_openai_models(stub)

        assert len(async_calls) == 1
        fetch_fn = async_calls[0]["fetch_fn"]
        assert fetch_fn.__self__.__class__.__name__ == "OpenAIProvider"
        assert fetch_fn.__func__.__name__ == "list_models"

    def test_env_fallback_used_when_input_empty(self, monkeypatch):
        """(c): 入力欄が空のとき _env_fallback("openai") 経由で
        OPENAI_API_KEY が使われる。
        """
        from pagefolio.dialogs.llm_config import model_fetch as model_fetch_mod

        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-fallback")
        stub, _status, async_calls = self._make_stub(api_key="")
        model_fetch_mod.ModelFetchMixin._refresh_openai_models(stub)

        fetch_fn = async_calls[0]["fetch_fn"]
        assert fetch_fn.__self__.api_key == "sk-env-fallback"

    def test_on_error_matches_zero_result_fallback_of_list_models(self, monkeypatch):
        """(d): _on_error 実行後の combobox values と、list_models の 0 件
        合流が返す値が完全一致し、_set_lm_status に渡された LANG キーも一致
        すること（D-08 の観測同一性・レビュー MEDIUM-11）。
        """
        from pagefolio.dialogs.llm_config import model_fetch as model_fetch_mod
        from pagefolio.ocr_providers import OpenAIProvider

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        stub, status_calls, async_calls = self._make_stub(api_key="sk-test")
        model_fetch_mod.ModelFetchMixin._refresh_openai_models(stub)

        on_error = async_calls[0]["on_error"]
        on_error(RuntimeError("boom"))

        # list_models() が api_key 無し（または 0 件合流）のとき返す値と一致
        zero_result_fallback = list(OpenAIProvider.RECOMMENDED_MODELS)
        assert stub.openai_model_combo["values"] == zero_result_fallback

        error_status_text = status_calls[-1][0]
        assert error_status_text == stub._L["llm_env_key_unset_static_openai"]

    def test_on_success_and_on_error_never_touch_openai_model_var(self, monkeypatch):
        """(e): _on_success / _on_error のどちらも openai_model_var.set を
        呼ばない（遅延到達した結果が新しい選択を上書きしない・レビュー S5）。
        """
        from pagefolio.dialogs.llm_config import model_fetch as model_fetch_mod

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        stub, _status, async_calls = self._make_stub(api_key="sk-test")
        model_fetch_mod.ModelFetchMixin._refresh_openai_models(stub)

        set_calls = []
        original_set = stub.openai_model_var.set
        stub.openai_model_var.set = lambda v: (set_calls.append(v), original_set(v))

        on_success = async_calls[0]["on_success"]
        on_error = async_calls[0]["on_error"]
        on_success(["gpt-5.1", "gpt-4o"])
        on_error(RuntimeError("boom"))

        assert set_calls == []

    def test_no_threading_reference_in_refresh_openai_models(self):
        """(f): AST ベースで _refresh_openai_models 関数ノードに threading
        を参照する ast.Attribute/ast.Name が無いことを確認する。
        """
        tree = ast.parse(
            (
                REPO_ROOT / "pagefolio" / "dialogs" / "llm_config" / "model_fetch.py"
            ).read_text(encoding="utf-8")
        )
        fn = next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "_refresh_openai_models"
        )
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        assert "threading" not in names
