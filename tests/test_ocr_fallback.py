# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""pagefolio.ocr_fallback のユニットテスト（Tk/fitz 非依存純ロジック層）。

02-01-PLAN.md Task 3・V180-FALL-01/03 の純ロジック部分を検証する
（tests/test_ocr_pipeline.py と同型のスタイル）。
"""

from pagefolio.ocr_fallback import next_fallback_candidate, next_summary_candidate


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
