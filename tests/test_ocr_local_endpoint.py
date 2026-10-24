"""OCR ダイアログのローカル接続先解決（resolve_local_endpoint）の回帰テスト。

事象: ocr_provider=ollama でも OCR ダイアログの「▶ 読み取り実行」が LM Studio の
URL（lm_studio_url 既定 http://localhost:1234）へ送信され、接続エラーも
「LM Studio に接続できませんでした」と表示されていた
（.planning/debug/ocr-ollama-uses-lmstudio-url.md）。

根因: OCRDialog の url_var / model_var は _start_ocr が常に lm_studio_* で初期化し、
_on_run が ollama でもその値で OllamaProvider を再生成していた。

テスト方針: Tk ウィンドウ・実ネットワークは使わない（SimpleNamespace fake +
未束縛メソッド呼び出し。tests/test_ocr.py::TestOcrDialogOnRun と同型）。
  T1: resolve_local_endpoint 純関数
  T2: _start_ocr が有効プロバイダ用の url/model を OCRDialog へ渡す
  T3: _on_run が有効スナップショットから OllamaProvider を作り表示欄へ書き戻す
  T4: フォールバック lmstudio -> ollama 経路も ollama_url へ送る
  T5: 接続エラー文言がプロバイダ中立（ja/en でプレースホルダ一致）
"""

import string
import threading
import types

import pytest

from pagefolio import ocr
from pagefolio.lang import LANG

LM_URL = "http://localhost:1234"
LM_MODEL = "lm-model"
OLLAMA_URL = "http://127.0.0.1:17327"
OLLAMA_MODEL = "pagefolio-uat-fixture"
RUNPOD_URL = "https://api.runpod.ai/v2/abc123/openai/v1"
RUNPOD_MODEL = "runpod-model"


def _settings(provider, **extra):
    """3 系統のエンドポイント設定をすべて異なる値で持つ設定辞書を返す。"""
    s = {
        "ocr_provider": provider,
        "lm_studio_url": LM_URL,
        "lm_studio_model": LM_MODEL,
        "ollama_url": OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
        "runpod_url": RUNPOD_URL,
        "runpod_model": RUNPOD_MODEL,
        "ocr_timeout": 120,
        "ocr_max_tokens": -1,
        "ocr_temperature": 0.1,
    }
    s.update(extra)
    return s


class _Var:
    """tk.StringVar の最小スタブ（get / set のみ）。"""

    def __init__(self, value=""):
        self._value = value
        self.set_calls = []

    def get(self):
        return self._value

    def set(self, value):
        self.set_calls.append(value)
        self._value = value


# ===== T1: resolve_local_endpoint 純関数 =====


class TestResolveLocalEndpoint:
    """resolve_local_endpoint(settings, name) -> (url, model) | None"""

    def test_lmstudio_uses_lm_studio_keys(self):
        assert ocr.resolve_local_endpoint(_settings("lmstudio"), "lmstudio") == (
            LM_URL,
            LM_MODEL,
        )

    def test_empty_name_is_treated_as_lmstudio(self):
        """空文字は後方互換で lmstudio として解決する（build_provider と同じ）。"""
        assert ocr.resolve_local_endpoint(_settings(""), "") == (LM_URL, LM_MODEL)

    def test_ollama_uses_ollama_keys_not_lm_studio(self):
        url, model = ocr.resolve_local_endpoint(_settings("ollama"), "ollama")
        assert (url, model) == (OLLAMA_URL, OLLAMA_MODEL)
        assert url != LM_URL and model != LM_MODEL

    def test_runpod_uses_runpod_keys(self):
        assert ocr.resolve_local_endpoint(_settings("runpod"), "runpod") == (
            RUNPOD_URL,
            RUNPOD_MODEL,
        )

    def test_defaults_when_keys_missing(self):
        """キー欠落時は各プロバイダの既定 URL・空モデルを返す。"""
        assert ocr.resolve_local_endpoint({}, "lmstudio") == (
            ocr.DEFAULT_LM_STUDIO_URL,
            "",
        )
        assert ocr.resolve_local_endpoint({}, "ollama") == (
            ocr.DEFAULT_OLLAMA_URL,
            "",
        )
        assert ocr.resolve_local_endpoint({}, "runpod") == ("", "")

    def test_default_ollama_url_value(self):
        """Ollama の既定 URL は 11434 番ポート（settings.py の既定値と一致）。"""
        assert ocr.DEFAULT_OLLAMA_URL == "http://localhost:11434"

    def test_ollama_empty_url_falls_back_to_default(self):
        """ollama_url が空文字なら OllamaProvider と同じく既定 URL を表示する。"""
        url, _model = ocr.resolve_local_endpoint(
            {"ollama_url": "", "ollama_model": "m"}, "ollama"
        )
        assert url == ocr.DEFAULT_OLLAMA_URL

    def test_values_are_stripped(self):
        url, model = ocr.resolve_local_endpoint(
            {"ollama_url": "  http://h:1  ", "ollama_model": " m "}, "ollama"
        )
        assert (url, model) == ("http://h:1", "m")

    @pytest.mark.parametrize(
        "name", ["claude", "gemini", "openai", "tesseract", "off", "plugin_xyz"]
    )
    def test_non_local_endpoint_providers_return_none(self, name):
        """ローカル接続先を持たないプロバイダ（クラウド等/off/プラグイン）は None。"""
        assert ocr.resolve_local_endpoint(_settings(name), name) is None


# ===== T2: _start_ocr が有効プロバイダの url/model を OCRDialog へ渡す =====


class TestStartOcrPassesActiveEndpoint:
    def _fake_app(self, settings):
        return types.SimpleNamespace(
            settings=settings,
            _session_api_keys={},
            root=None,
            doc=object(),
            lang="ja",
            _t=lambda key: key,
            _font=lambda *a, **k: None,
        )

    def _run_start_ocr(self, monkeypatch, settings):
        import pagefolio.ocr_dialog as ocr_dialog

        captured = {}

        def _fake_dialog(*args, **kwargs):
            captured.update(kwargs)
            return object()

        monkeypatch.setattr(ocr_dialog, "OCRDialog", _fake_dialog)
        ocr.OCRMixin._start_ocr(self._fake_app(settings), [0])
        return captured

    def test_ollama_passes_ollama_url_and_model(self, monkeypatch):
        got = self._run_start_ocr(monkeypatch, _settings("ollama"))
        assert got["url"] == OLLAMA_URL
        assert got["model"] == OLLAMA_MODEL
        assert got["provider"].url == OLLAMA_URL

    def test_lmstudio_passes_lm_studio_url_and_model(self, monkeypatch):
        got = self._run_start_ocr(monkeypatch, _settings("lmstudio"))
        assert got["url"] == LM_URL
        assert got["model"] == LM_MODEL

    def test_runpod_passes_runpod_url_and_model(self, monkeypatch):
        monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
        got = self._run_start_ocr(monkeypatch, _settings("runpod"))
        assert got["url"] == RUNPOD_URL
        assert got["model"] == RUNPOD_MODEL

    def test_cloud_provider_keeps_legacy_lm_studio_initial_values(self, monkeypatch):
        """ローカル接続先を持たないプロバイダは従来どおり lm_studio_* を初期値に渡す
        （非表示欄の初期値であり送信先ではない。挙動を変えない）。"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        got = self._run_start_ocr(monkeypatch, _settings("claude"))
        assert got["url"] == LM_URL
        assert got["model"] == LM_MODEL


# ===== T3 / T4 共通: _on_run を Tk なしで駆動する fake =====


def _make_run_dialog(settings, url=LM_URL, model=LM_MODEL):
    """_on_run を Tk 生成なしで呼べる fake OCRDialog を返す。

    url / model は OCRDialog 生成時の初期値（_start_ocr が渡す url_var/model_var の
    初期値）を模す。既定は修正前の _start_ocr と同じ lm_studio_* 固定値。
    """
    from pagefolio.ocr_dialog import OCRDialog

    class _Bar(dict):
        def configure(self, **kw):
            self.update(kw)

    app = types.SimpleNamespace(
        settings=dict(settings), _session_api_keys={}, plugin_manager=None
    )
    fake = types.SimpleNamespace(
        app=app,
        provider=None,
        _started=False,
        _done=False,
        progress_var=types.SimpleNamespace(set=lambda _v: None),
        progress_bar=_Bar(),
        _progress_label=types.SimpleNamespace(configure=lambda **kw: None),
        cancel_btn=types.SimpleNamespace(state=lambda _s: None),
        run_btn=types.SimpleNamespace(state=lambda _s: None),
        resume_btn=types.SimpleNamespace(state=lambda _s: None),
        _llm_config_btn=types.SimpleNamespace(state=lambda _s: None),
        _cancel_flag=threading.Event(),
        page_indices=[0],
        results={},
        errors={},
        _skipped_pages=set(),
        _truncated_pages=set(),
        _render_failed_pages=set(),
        concurrency=1,
        _render_idx=0,
        _pstate=None,
        _worker_threads=[],
        _run_gen=0,
        text=types.SimpleNamespace(delete=lambda *a: None),
        scale_var=types.SimpleNamespace(get=lambda: "1.5"),
        timeout_var=types.SimpleNamespace(get=lambda: "120"),
        preset_var=types.SimpleNamespace(get=lambda: "text"),
        url_var=_Var(url),
        model_var=_Var(model),
        max_tokens_var=types.SimpleNamespace(get=lambda: "-1"),
        temperature_var=types.SimpleNamespace(get=lambda: "0.1"),
        force_ocr_var=types.SimpleNamespace(get=lambda: False),
        custom_prompt="",
        _L={"ocr_progress_init": "init"},
        summary_result=None,
        _summary_truncated=False,
        _summary_running=False,
        _summary_cancel_flag=threading.Event(),
        summary_btn=types.SimpleNamespace(state=lambda _s: None),
    )
    fake._is_cloud_provider = lambda settings=None: False
    fake._render_next_page = lambda gen=None: None
    fake._start_worker_thread = lambda gen=None: None
    fake._maybe_show_lang_fallback_notice = lambda: None
    fake._can_resume = lambda: False
    fake._refresh_provider_dependent_ui = lambda: None
    fake._validate_provider_readiness = lambda candidate, s: True
    # フォールバック経路（_switch_to_fallback_provider が呼ぶ self._on_run）用に束縛
    fake._on_run = lambda **kw: OCRDialog._on_run(fake, **kw)
    return fake


# ===== T3: _on_run が有効スナップショットの url/model を使う =====


class TestOnRunUsesActiveEndpoint:
    def test_ollama_provider_gets_ollama_url_and_model(self):
        """ocr_provider=ollama なら OllamaProvider は ollama_url/model を持つ。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import OllamaProvider

        # url_var/model_var は修正前の _start_ocr と同じく LM Studio 値で初期化
        fake = _make_run_dialog(_settings("ollama"))
        OCRDialog._on_run(fake)

        assert isinstance(fake.provider, OllamaProvider)
        assert fake.provider.url == OLLAMA_URL, (
            f"Ollama の送信先が LM Studio の値になっている: {fake.provider.url}"
        )
        assert fake.provider.model == OLLAMA_MODEL

    def test_ollama_run_writes_endpoint_back_to_display_vars(self):
        """送信先と表示欄（url_var / model_var）が食い違わないよう書き戻す。"""
        from pagefolio.ocr_dialog import OCRDialog

        fake = _make_run_dialog(_settings("ollama"))
        OCRDialog._on_run(fake)

        assert fake.url_var.get() == OLLAMA_URL
        assert fake.model_var.get() == OLLAMA_MODEL

    def test_lmstudio_provider_gets_lm_studio_url_and_model(self):
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import LMStudioProvider

        fake = _make_run_dialog(_settings("lmstudio"))
        OCRDialog._on_run(fake)

        assert isinstance(fake.provider, LMStudioProvider)
        assert fake.provider.url == LM_URL
        assert fake.provider.model == LM_MODEL
        assert fake.url_var.get() == LM_URL
        assert fake.model_var.get() == LM_MODEL

    def test_runpod_run_writes_endpoint_back_to_display_vars(self):
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import RunPodProvider

        fake = _make_run_dialog(_settings("runpod"))
        OCRDialog._on_run(fake)

        assert isinstance(fake.provider, RunPodProvider)
        assert fake.provider.url == RUNPOD_URL
        assert fake.url_var.get() == RUNPOD_URL
        assert fake.model_var.get() == RUNPOD_MODEL

    def test_explicit_settings_snapshot_wins_over_app_settings(self):
        """settings= で渡されたスナップショットが app.settings より優先される
        （フォールバック経路が候補設定を渡す契約）。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import OllamaProvider

        fake = _make_run_dialog(_settings("lmstudio"))
        OCRDialog._on_run(fake, settings=_settings("ollama"))

        assert isinstance(fake.provider, OllamaProvider)
        assert fake.provider.url == OLLAMA_URL
        assert fake.url_var.get() == OLLAMA_URL

    def test_cloud_provider_does_not_touch_endpoint_vars(self, monkeypatch):
        """ローカル接続先を持たないプロバイダは url_var/model_var を書き換えない。"""
        from pagefolio.ocr_dialog import OCRDialog

        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        fake = _make_run_dialog(_settings("gemini"))
        OCRDialog._on_run(fake)

        assert fake.url_var.set_calls == []
        assert fake.model_var.set_calls == []


# ===== T4: フォールバック lmstudio -> ollama =====


class TestFallbackLmstudioToOllama:
    def test_fallback_to_ollama_sends_to_ollama_url(self):
        """LM Studio が失敗して Ollama へフォールバックしたとき、実送信先は
        ollama_url になる（_switch_to_fallback_provider -> _on_run(settings=fb)）。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import OllamaProvider

        fake = _make_run_dialog(_settings("lmstudio"))
        # 一次実行（lmstudio）後の状態: スナップショット確定済み・表示欄は LM Studio
        fake._active_ocr_settings = dict(fake.app.settings)
        fake.provider = None
        fake._fallback_resume = False

        OCRDialog._switch_to_fallback_provider(fake, "ollama")

        assert isinstance(fake.provider, OllamaProvider)
        assert fake.provider.url == OLLAMA_URL, (
            f"フォールバック先 Ollama が LM Studio の URL へ送る: {fake.provider.url}"
        )
        assert fake.provider.model == OLLAMA_MODEL
        assert fake.url_var.get() == OLLAMA_URL
        # app.settings は書き換えない（Pitfall 4）
        assert fake.app.settings["ocr_provider"] == "lmstudio"

    def test_fallback_ollama_to_lmstudio_does_not_inherit_ollama_url(self):
        """逆方向（ollama -> lmstudio）でも、直前の ollama の表示値を引き継がない。"""
        from pagefolio.ocr_dialog import OCRDialog
        from pagefolio.ocr_providers import LMStudioProvider

        fake = _make_run_dialog(_settings("ollama"), url=OLLAMA_URL, model=OLLAMA_MODEL)
        fake._active_ocr_settings = dict(fake.app.settings)
        fake._fallback_resume = False

        OCRDialog._switch_to_fallback_provider(fake, "lmstudio")

        assert isinstance(fake.provider, LMStudioProvider)
        assert fake.provider.url == LM_URL
        assert fake.provider.model == LM_MODEL


# ===== T5: 接続エラー文言のプロバイダ中立化 =====


def _placeholders(text):
    return {f for _lit, f, _spec, _conv in string.Formatter().parse(text) if f}


class TestConnectionErrorMessage:
    def test_lang_has_identical_placeholder_sets_with_provider_and_url(self):
        ja = _placeholders(LANG["ja"]["ocr_err_connection"])
        en = _placeholders(LANG["en"]["ocr_err_connection"])
        assert ja == en, f"ja/en のプレースホルダが不一致: {ja} vs {en}"
        assert {"provider", "url", "error"} <= ja

    @pytest.mark.parametrize("lang", ["ja", "en"])
    def test_lang_text_does_not_hardcode_lm_studio(self, lang):
        assert "LM Studio" not in LANG[lang]["ocr_err_connection"]

    def _make_dialog(self, settings, provider, lang="ja"):
        from pagefolio.ocr_dialog import OCRDialog

        d = OCRDialog.__new__(OCRDialog)
        d.app = types.SimpleNamespace(settings=dict(settings))
        d._L = LANG[lang]
        d.provider = provider
        d._active_ocr_settings = None
        d._done = False
        d.results = {}
        d.errors = {}
        d.progress_var = _Var()
        d._progress_label = types.SimpleNamespace(configure=lambda **kw: None)
        d.inserted = []
        d.text = types.SimpleNamespace(
            insert=lambda _pos, s: d.inserted.append(s), see=lambda *a: None
        )
        d.cancel_btn = types.SimpleNamespace(state=lambda *a: None)
        d.copy_btn = types.SimpleNamespace(state=lambda *a: None)
        d.save_btn = types.SimpleNamespace(state=lambda *a: None)
        # 古い LM Studio 値が残っていても文言に出ないことを確認するため意図的に設定
        d.url_var = _Var(LM_URL)
        d.timeout_var = _Var(120)
        d._after_run_ui_reset = lambda: None
        d._append_resume_hint = lambda: None
        d._render_results_ordered = lambda: None
        d._can_resume = lambda: False
        d._propose_fallback = lambda kind, msg, summary=False: None
        return d

    def _message(self, d):
        from pagefolio.ocr_dialog import OCRDialog

        OCRDialog._finish_error(d, "[WinError 10061] refused", kind="connection")
        return "".join(d.inserted)

    @pytest.mark.parametrize("lang", ["ja", "en"])
    def test_ollama_error_names_ollama_and_its_url(self, lang):
        from pagefolio.ocr_providers import OllamaProvider

        provider = OllamaProvider(url=OLLAMA_URL, model=OLLAMA_MODEL)
        d = self._make_dialog(_settings("ollama"), provider, lang)
        msg = self._message(d)

        assert "ollama" in msg
        assert OLLAMA_URL in msg
        assert "LM Studio" not in msg
        assert LM_URL not in msg
        assert "[WinError 10061] refused" in msg

    def test_gemini_error_names_gemini_not_lm_studio(self):
        from pagefolio.ocr_providers import GeminiProvider

        provider = GeminiProvider(api_key="x", model="gemini-2.5-flash")
        d = self._make_dialog(_settings("gemini"), provider)
        msg = self._message(d)

        assert LANG["ja"]["ocr_provider_name_gemini"] in msg
        assert "generativelanguage.googleapis.com" in msg
        assert "LM Studio" not in msg
        assert LM_URL not in msg

    def test_lmstudio_error_still_names_lm_studio_and_url(self):
        from pagefolio.ocr_providers import LMStudioProvider

        provider = LMStudioProvider(url=LM_URL, model=LM_MODEL)
        d = self._make_dialog(_settings("lmstudio"), provider)
        msg = self._message(d)

        assert "LM Studio" in msg
        assert LM_URL in msg
