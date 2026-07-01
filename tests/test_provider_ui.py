# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR-UI-01/02/03 向け自動回帰テスト

各ギャップに対して Tk ウィジェット生成を行わず、
ロジック層のみを検証するユニットテスト群。
"""

import types

import pytest

from pagefolio.ocr import OCR_PROMPTS, resolve_ocr_prompt
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
    stub._is_cloud_provider = lambda: OCRDialog._is_cloud_provider(stub)
    stub._estimate_cost = lambda m, c: OCRDialog._estimate_cost(stub, m, c)
    stub._needs_session_key = lambda: OCRDialog._needs_session_key(stub)
    return stub


class TestLLMConfigProviderValues:
    """Task 2 回帰: provider_combo に gemini が含まれることを確認。"""

    def test_provider_combo_includes_gemini(self):
        """provider_combo の values に 'gemini' が含まれる（OCR-API-02）。"""
        import pathlib

        from pagefolio.dialogs.llm_config import LLMConfigDialog

        src = pathlib.Path("pagefolio/dialogs/llm_config.py").read_text(
            encoding="utf-8"
        )
        assert '"gemini"' in src, (
            "provider_combo の values に 'gemini' が含まれていない"
        )
        fn = LLMConfigDialog._model_supports_effort
        assert callable(fn)

    def test_gemini_section_frame_exists_in_source(self):
        """llm_config.py に gemini_section_frame の定義が存在する。"""
        import pathlib

        src = pathlib.Path("pagefolio/dialogs/llm_config.py").read_text(
            encoding="utf-8"
        )
        assert "gemini_section_frame" in src
        assert "gemini_model_var" in src
        assert "_on_provider_change" in src


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


class TestNeedsSessionKey:
    """OCR-UI-03: _needs_session_key の動作検証。"""

    def test_env_set_returns_false(self, monkeypatch):
        """ANTHROPIC_API_KEY が環境変数に設定済みなら False を返す。"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        stub = _make_dialog_stub(settings={"ocr_provider": "claude"})
        assert stub._needs_session_key() is False

    def test_env_unset_cloud_returns_true(self, monkeypatch):
        """ANTHROPIC_API_KEY が未設定かつ claude プロバイダなら True を返す。"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        stub = _make_dialog_stub(settings={"ocr_provider": "claude"})
        assert stub._needs_session_key() is True

    def test_lmstudio_env_unset_returns_false(self, monkeypatch):
        """lmstudio はクラウドではないため env 未設定でも False。"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        stub = _make_dialog_stub(settings={"ocr_provider": "lmstudio"})
        assert stub._needs_session_key() is False

    def test_gemini_env_unset_returns_true(self, monkeypatch):
        """gemini で GEMINI_API_KEY/GOOGLE_API_KEY 両方未設定なら True（D-06）。"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        stub = _make_dialog_stub(settings={"ocr_provider": "gemini"})
        assert stub._needs_session_key() is True

    def test_gemini_gemini_api_key_set_returns_false(self, monkeypatch):
        """GEMINI_API_KEY が設定済みなら gemini でも False。"""
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        stub = _make_dialog_stub(settings={"ocr_provider": "gemini"})
        assert stub._needs_session_key() is False

    def test_gemini_google_api_key_fallback_returns_false(self, monkeypatch):
        """GEMINI_API_KEY 未設定でも GOOGLE_API_KEY があれば False。"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
        stub = _make_dialog_stub(settings={"ocr_provider": "gemini"})
        assert stub._needs_session_key() is False


class TestConfirmCost:
    """OCR-UI-03: _confirm_cost の動作検証（messagebox モック）。"""

    def _make_confirm_stub(self, page_indices, model="claude-sonnet-4-6"):
        """_confirm_cost 呼び出し用スタブを返す。

        OCRDialog._confirm_cost は self.app.settings / self.page_indices /
        self._L / self（parent として messagebox に渡す）を参照する。
        """
        from pagefolio.constants import LANG
        from pagefolio.ocr_dialog import OCRDialog

        stub = types.SimpleNamespace(
            app=types.SimpleNamespace(
                settings={"ocr_provider": "claude", "claude_model": model}
            ),
            page_indices=list(page_indices),
            _L=LANG["ja"],
        )
        stub._estimate_cost = lambda m, c: OCRDialog._estimate_cost(stub, m, c)
        stub._confirm_cost = lambda: OCRDialog._confirm_cost(stub)
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


def _make_apply_llm_settings_stub(settings, provider=None):
    """_apply_llm_settings を Tk 生成なしで呼ぶスタブを返す。"""
    stub = types.SimpleNamespace(
        app=types.SimpleNamespace(settings=dict(settings)),
        custom_prompt="旧プロンプト",
        provider=provider or ClaudeProvider(api_key="x", model="claude-sonnet-4-6"),
        concurrency=1,
        _refresh_provider_dependent_ui=lambda: None,
        _sync_param_vars_from_settings=lambda: None,
        progress_var=_VarStub(),
        url_var=_VarStub(),
        model_var=_VarStub(),
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
