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
    # headless インスタンスのため _build() を経由せず、プロバイダ表示ラベル
    # 等の実 Tk ウィジェットは存在しない。_switch_to_fallback_provider が
    # 呼ぶ _refresh_provider_dependent_ui（02-REVIEW WR-01 修正で追加）は
    # ウィジェット依存のため no-op に差し替える（メソッド自体の docstring
    # が明示する「テストでは no-op に差し替え可能」という契約どおり）。
    d._refresh_provider_dependent_ui = lambda: None
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


class TestConfirmationGate:
    """02-04 Task 2: _propose_fallback の承認ゲート再提示
    （D-10/D-11・V180-FALL-02・Pitfall 2・レビュー HIGH）。
    """

    @staticmethod
    def _settings(enabled=True, chain=None, provider="claude"):
        return {
            "ocr_provider": provider,
            "ocr_fallback_enabled": enabled,
            "ocr_fallback_chain": list(chain if chain is not None else ["lmstudio"]),
        }

    def test_askyesno_called_when_enabled(self, monkeypatch):
        """フォールバック有効時、fatal で askyesno が呼ばれる（承認ゲート省略なし）。"""
        d = _make_dialog(self._settings())
        calls = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda *a, **k: calls.append((a, k)) or False,
        )
        d._propose_fallback("connection", "boom")
        assert len(calls) == 1

    def test_approval_switches_and_calls_on_run_with_candidate_settings(
        self, monkeypatch
    ):
        """承認時、_switch_to_fallback_provider→_on_run(resume=True, settings=fb)
        経由で build_provider が ocr_provider==candidate の設定で呼ばれる
        （レビュー HIGH 回帰防止）。
        """
        d = _make_dialog(self._settings())
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno", lambda *a, **k: True
        )
        build_calls = []

        class _FakeProvider:
            max_concurrency = 4
            supports_text_prompt = True

        def _fake_build_provider(settings, **kwargs):
            build_calls.append(dict(settings))
            return _FakeProvider()

        monkeypatch.setattr("pagefolio.ocr.build_provider", _fake_build_provider)
        on_run_calls = []
        d._on_run = lambda **kwargs: on_run_calls.append(kwargs)

        d._propose_fallback("connection", "boom")

        assert len(build_calls) == 1
        assert build_calls[0]["ocr_provider"] == "lmstudio"
        assert len(on_run_calls) == 1
        assert on_run_calls[0]["resume"] is True
        assert on_run_calls[0]["settings"]["ocr_provider"] == "lmstudio"
        assert d.provider is not None
        # self.app.settings 自体は書き換えられない（Pitfall 4・T-02-11）
        assert d.app.settings["ocr_provider"] == "claude"

    def test_rejection_does_not_switch(self, monkeypatch):
        """拒否時は _switch_to_fallback_provider（＝別ベンダー送信）が起きない。"""
        d = _make_dialog(self._settings())
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno", lambda *a, **k: False
        )
        on_run_calls = []
        d._on_run = lambda **kwargs: on_run_calls.append(kwargs)
        d._propose_fallback("connection", "boom")
        assert on_run_calls == []
        assert d.provider is None
        # D-10: 拒否候補も試行済み扱い（連鎖は継続するが自動送信はしない）
        assert "lmstudio" in d._fallback_tried

    def test_disabled_does_not_call_askyesno(self, monkeypatch):
        """ocr_fallback_enabled=False では askyesno が一切呼ばれない
        （V180-FALL-01）。
        """
        d = _make_dialog(self._settings(enabled=False))
        calls = []
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno",
            lambda *a, **k: calls.append(1) or True,
        )
        d._propose_fallback("connection", "boom")
        assert calls == []

    def test_api_key_missing_reason_in_message(self, monkeypatch):
        """api_key_missing 理由が確認文言に明示される（D-11）。"""
        d = _make_dialog(self._settings(chain=["claude"], provider="lmstudio"))
        captured = {}

        def _fake_askyesno(title, msg, **kwargs):
            captured["msg"] = msg
            return False

        monkeypatch.setattr("pagefolio.ocr_dialog.messagebox.askyesno", _fake_askyesno)
        d._propose_fallback("api_key_missing", "no key")
        assert d._L["fallback_reason_api_key_missing"] in captured["msg"]


class TestSummaryFallback:
    """02-04 Task 2: サマリ経路のフォールバック（D-12・レビュー MEDIUM）。"""

    def test_summary_excludes_tesseract_candidate(self, monkeypatch):
        """next_summary_candidate 経由で tesseract が候補から除外される。"""
        settings = {
            "ocr_provider": "claude",
            "ocr_fallback_enabled": True,
            "ocr_fallback_chain": ["tesseract", "gemini"],
        }
        d = _make_dialog(settings)
        captured = {}

        def _fake_askyesno(title, msg, **kwargs):
            captured["msg"] = msg
            return False

        monkeypatch.setattr("pagefolio.ocr_dialog.messagebox.askyesno", _fake_askyesno)
        d._propose_fallback("generic", "summary failed", summary=True)
        # 02-REVIEW WR-04 修正: 確認メッセージは内部キーの生値ではなく
        # ローカライズされた表示名（"Gemini (Google AI)"）で候補を示す。
        assert d._L["ocr_provider_name_gemini"] in captured["msg"]
        assert "gemini" in d._fallback_tried
        assert "tesseract" not in d._fallback_tried

    def test_approval_calls_on_summary_with_candidate_settings(self, monkeypatch):
        """承認時、_switch_to_fallback_provider(summary=True)→
        _on_summary(settings=fb) が候補設定で呼ばれる（レビュー MEDIUM）。
        """
        settings = {
            "ocr_provider": "claude",
            "ocr_fallback_enabled": True,
            "ocr_fallback_chain": ["gemini"],
        }
        d = _make_dialog(settings)
        monkeypatch.setattr(
            "pagefolio.ocr_dialog.messagebox.askyesno", lambda *a, **k: True
        )

        class _FakeProvider:
            max_concurrency = 1
            supports_text_prompt = True

        monkeypatch.setattr(
            "pagefolio.ocr.build_provider", lambda settings, **kw: _FakeProvider()
        )
        monkeypatch.setattr(
            "pagefolio.ocr._resolve_api_key", lambda name, session_keys: "dummy-key"
        )
        summary_calls = []
        d._on_summary = lambda **kwargs: summary_calls.append(kwargs)

        d._propose_fallback("generic", "summary failed", summary=True)

        assert len(summary_calls) == 1
        assert summary_calls[0]["settings"]["ocr_provider"] == "gemini"


class TestProviderReadiness:
    """02-04 Task 2: _validate_provider_readiness の実行不可検出
    （レビュー LOW・D-11/D-14・T-02-14）。
    """

    def test_validate_provider_readiness_false_when_tesseract_missing(
        self, monkeypatch
    ):
        """tesseract 未インストール検出時は False を返す。"""
        monkeypatch.setattr(
            "pagefolio.ocr_providers._detect_tesseract",
            lambda: (False, frozenset()),
        )
        settings = {"ocr_provider": "tesseract"}
        d = _make_dialog(settings)
        assert d._validate_provider_readiness("tesseract", settings) is False

    def test_switch_skips_unavailable_tesseract_and_proposes_next(self, monkeypatch):
        """tesseract が実行不可なら静かに握りつぶさず、試行済みへ計上して
        次候補（lmstudio）へ再帰的に進む（build_provider は tesseract では
        呼ばれない）。
        """
        monkeypatch.setattr(
            "pagefolio.ocr_providers._detect_tesseract",
            lambda: (False, frozenset()),
        )
        settings = {
            "ocr_provider": "claude",
            "ocr_fallback_enabled": True,
            "ocr_fallback_chain": ["tesseract", "lmstudio"],
        }
        d = _make_dialog(settings)
        askyesno_calls = []

        def _fake_askyesno(title, msg, **kwargs):
            askyesno_calls.append(msg)
            return True

        monkeypatch.setattr("pagefolio.ocr_dialog.messagebox.askyesno", _fake_askyesno)

        class _FakeProvider:
            max_concurrency = 8
            supports_text_prompt = True

        build_calls = []

        def _fake_build_provider(settings, **kwargs):
            build_calls.append(dict(settings))
            return _FakeProvider()

        monkeypatch.setattr("pagefolio.ocr.build_provider", _fake_build_provider)
        on_run_calls = []
        d._on_run = lambda **kwargs: on_run_calls.append(kwargs)

        d._propose_fallback("connection", "boom")

        assert "tesseract" in d._fallback_tried
        assert "lmstudio" in d._fallback_tried
        assert len(askyesno_calls) == 2
        # tesseract は readiness=False のため build_provider は呼ばれず、
        # 次候補 lmstudio でのみ呼ばれる（静かな握りつぶし禁止）
        assert len(build_calls) == 1
        assert build_calls[0]["ocr_provider"] == "lmstudio"
        assert len(on_run_calls) == 1
        assert on_run_calls[0]["settings"]["ocr_provider"] == "lmstudio"
