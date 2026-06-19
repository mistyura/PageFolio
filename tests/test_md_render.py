# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""V16-AI-01: parse_markdown の行種別/インライン span 分類を検証。Tk 非生成。

全テストは Tk 非依存（ウィジェット起動不要・OCRDialog 非インスタンス化）で
ヘッドレス実行できる（04-RESEARCH.md Pitfall 1 の Warning sign を回避）。
pagefolio.md_render の純関数 parse_markdown / _split_inline を直接アサートする。
"""

from pagefolio.md_render import _split_inline, parse_markdown

# 全 line_kind 種別（不変条件ループ網羅用）
_ALL_KINDS = {"md_h1", "md_h2", "md_bullet", "md_code", ""}


class TestParseMarkdown:
    """V16-AI-01: 行種別/インライン span 分類の純関数契約を検証する。"""

    def test_h1_detected(self):
        # H1 検出・本文から '# ' プレフィックスを除去
        assert parse_markdown("# Title")[0] == ("md_h1", [("Title", None)])

    def test_h2_detected(self):
        # H2 検出・本文から '## ' プレフィックスを除去
        assert parse_markdown("## Sub")[0] == ("md_h2", [("Sub", None)])

    def test_bullet_detected(self):
        # '- ' / '* ' の双方で md_bullet、本文は '• ' 始まりへ正規化
        for src in ("- item", "* item"):
            kind, spans = parse_markdown(src)[0]
            assert kind == "md_bullet"
            assert spans[0][0].startswith("• ")

    def test_codeblock_no_heading(self):
        # コードフェンス内の '# ' 行は md_h1 ではなく md_code（in_code フラグ）
        out = parse_markdown("```\n# nothead\n```")
        assert out[0][0] == "md_code"
        assert out[0] == ("md_code", [("# nothead", None)])
        # フェンス行自体は出力に含めない（1 行のみ）
        assert len(out) == 1

    def test_plain_paragraph(self):
        # 通常段落の line_kind は ''（空文字）
        kind, spans = parse_markdown("hello")[0]
        assert kind == ""
        assert spans == [("hello", None)]

    def test_bold_inline_span(self):
        # 箇条書き本文中の **bold** が md_bold span として抽出される
        kind, spans = parse_markdown("- **bold** item")[0]
        assert kind == "md_bullet"
        assert ("bold", "md_bold") in spans

    def test_no_bold_single_span(self):
        # bold を含まない行は span 1 個（[(text, None)]）
        assert _split_inline("plain text") == [("plain text", None)]

    def test_split_inline_bold_and_trailing(self):
        # _split_inline が **bold** と後続非マッチ部を分割
        spans = _split_inline("**bold** x")
        assert ("bold", "md_bold") in spans
        assert (" x", None) in spans

    def test_invariant_line_kind_in_vocabulary(self):
        # 不変条件: 全行の line_kind は定義済み語彙のいずれか
        sample = "# H1\n## H2\n- bullet\n* star\nplain\n```\ncode\n```"
        for kind, spans in parse_markdown(sample):
            assert kind in _ALL_KINDS
            # span は必ず 1 個以上（空リストを返さない）
            assert len(spans) >= 1
            for span_text, tag in spans:
                assert isinstance(span_text, str)
                assert tag in (None, "md_bold")
