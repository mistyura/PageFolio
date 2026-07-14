# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""pagefolio.ocr_fallback / OCRDialog フォールバックオーケストレーションの
ユニットテスト（Tk/fitz 非依存純ロジック層 + headless スタブ）。

02-01-PLAN.md Task 3・V180-FALL-01/03 の純ロジック部分と、02-04-PLAN.md の
_propose_fallback/_switch_to_fallback_provider/_validate_provider_readiness
（V180-FALL-02/03・D-09〜D-16・レビュー HIGH/MEDIUM/LOW）を検証する
（tests/test_ocr_pipeline.py・tests/test_provider_ui.py と同型のスタイル）。
"""

import types

from pagefolio.ocr_fallback import next_fallback_candidate, next_summary_candidate


def _make_dialog(settings, provider=None, results=None):
    """OCRDialog のフォールバックオーケストレーションメソッドだけを検証する
    headless インスタンスを返す。

    Tk ウィジェット生成（__init__/_build）を一切経由しない
    （OCRDialog.__new__ で tk.Toplevel.__init__ をスキップし、検証に必要な
    属性のみ手動で設定する）。
    """
    from pagefolio.constants import LANG
    from pagefolio.ocr_dialog import OCRDialog

    d = OCRDialog.__new__(OCRDialog)
    d.app = types.SimpleNamespace(
        settings=dict(settings),
        _session_api_keys={},
        plugin_manager=None,
    )
    d._L = LANG["ja"]
    d.provider = provider
    d.page_indices = [0, 1, 2]
    d.results = dict(results if results is not None else {0: "x", 1: "y", 2: "z"})
    d.errors = {}
    d._active_ocr_settings = None
    d._fallback_tried = set()
    d._fallback_resume = False
    d.concurrency = 1
    d._started = False
    d._done = False
    d._summary_running = False
    d.text = None
    return d


class TestDisabledByDefault:
    """chain が空（フォールバック未設定）の安全側既定（V180-FALL-01）。"""

    def test_empty_chain_returns_none(self):
        assert next_fallback_candidate([], set()) is None

    def test_empty_chain_returns_none_for_summary_too(self):
        assert next_summary_candidate([], set(), {"claude", "gemini"}) is None


class TestNextCandidate:
    """next_fallback_candidate のチェーン順走査・試行済み除外（D-10）。"""

    def test_returns_first_when_none_tried(self):
        assert next_fallback_candidate(["claude", "gemini"], set()) == "claude"

    def test_skips_tried_candidates(self):
        assert next_fallback_candidate(["claude", "gemini"], {"claude"}) == "gemini"

    def test_skips_multiple_tried_in_chain_order(self):
        chain = ["claude", "gemini", "runpod"]
        assert next_fallback_candidate(chain, {"claude", "gemini"}) == "runpod"

    def test_all_tried_returns_none(self):
        chain = ["claude", "gemini"]
        assert next_fallback_candidate(chain, {"claude", "gemini"}) is None

    def test_tried_superset_of_chain_returns_none(self):
        chain = ["claude"]
        assert next_fallback_candidate(chain, {"claude", "gemini", "runpod"}) is None

    def test_does_not_mutate_chain_or_tried(self):
        chain = ["claude", "gemini"]
        tried = {"claude"}
        chain_copy = list(chain)
        tried_copy = set(tried)
        next_fallback_candidate(chain, tried)
        assert chain == chain_copy
        assert tried == tried_copy


class TestSummaryCandidateFilter:
    """next_summary_candidate の text_capable フィルタ（D-12・Open Question 2）。"""

    def test_skips_non_text_capable_candidate(self):
        chain = ["tesseract", "claude"]
        text_capable = {"claude", "gemini"}
        assert next_summary_candidate(chain, set(), text_capable) == "claude"

    def test_all_non_capable_returns_none(self):
        chain = ["tesseract", "lmstudio"]
        text_capable = {"claude", "gemini"}
        assert next_summary_candidate(chain, set(), text_capable) is None

    def test_returns_first_capable_untried_candidate(self):
        chain = ["claude", "gemini", "runpod"]
        text_capable = {"claude", "gemini", "runpod"}
        assert next_summary_candidate(chain, {"claude"}, text_capable) == "gemini"

    def test_combines_tried_exclusion_with_capability_filter(self):
        chain = ["tesseract", "claude", "gemini"]
        text_capable = {"claude", "gemini"}
        assert next_summary_candidate(chain, {"claude"}, text_capable) == "gemini"

    def test_does_not_mutate_args(self):
        chain = ["tesseract", "claude"]
        tried = set()
        text_capable = {"claude"}
        chain_copy = list(chain)
        tried_copy = set(tried)
        text_capable_copy = set(text_capable)
        next_summary_candidate(chain, tried, text_capable)
        assert chain == chain_copy
        assert tried == tried_copy
        assert text_capable == text_capable_copy


class TestSettingsIsolation:
    """02-04 Task 1: settings= 引数による一般化とダイアログローカル
    スナップショットの独立性（Pitfall 4・レビュー HIGH の前提条件）。
    """

    def test_is_cloud_provider_uses_explicit_settings(self):
        """settings= を渡すと渡した dict のプロバイダで判定される。"""
        d = _make_dialog({"ocr_provider": "lmstudio"})
        assert d._is_cloud_provider(settings={"ocr_provider": "claude"}) is True
        assert d._is_cloud_provider(settings={"ocr_provider": "lmstudio"}) is False

    def test_is_cloud_provider_defaults_to_app_settings(self):
        """settings 省略時は self.app.settings を読む（後方互換）。"""
        d = _make_dialog({"ocr_provider": "claude"})
        assert d._is_cloud_provider() is True

    def test_check_cloud_api_key_uses_explicit_settings(self, monkeypatch):
        """settings= を渡すと渡した dict のプロバイダでキー解決判定される。"""
        d = _make_dialog({"ocr_provider": "lmstudio"})
        monkeypatch.setattr(
            "pagefolio.ocr._resolve_api_key", lambda name, session_keys: "dummy"
        )
        assert d._check_cloud_api_key(settings={"ocr_provider": "claude"}) is True

    def test_check_cloud_api_key_defaults_to_app_settings(self):
        """settings 省略時は self.app.settings を読む（後方互換）。"""
        d = _make_dialog({"ocr_provider": "lmstudio"})
        assert d._check_cloud_api_key() is True  # 非クラウドなので常に True

    def test_switching_active_snapshot_does_not_mutate_app_settings(self):
        """_active_ocr_settings をフォールバック候補で差し替えても
        self.app.settings は不変（Pitfall 4・T-02-11）。
        """
        d = _make_dialog({"ocr_provider": "claude"})
        original = dict(d.app.settings)
        fb = dict(d.app.settings)
        fb["ocr_provider"] = "gemini"
        d._active_ocr_settings = fb
        assert d.app.settings == original
        assert d.app.settings["ocr_provider"] == "claude"
