# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""OCR 結果 Markdown を (行種別, インライン span) へ変換する純ロジック層。

OCR 結果の Markdown 文字列を「行種別 line_kind + インライン span」の
構造データへ変換する純関数 `parse_markdown` と内部ヘルパー `_split_inline`
を集約する。描画ロジックを `ocr_dialog.py`（Tk 依存）にベタ書きすると
テスト不能になるため（04-RESEARCH.md Pitfall 1）、`pagination.py` と同じ
「純関数集約 + Tk 非生成 unit テスト」パターンに倣い変換を 1 箇所へ閉じ込める。

ここには `tkinter` / `fitz` を一切 import しない（pagination.py:11 の純関数作法）。
import は標準ライブラリ `re` のみ（V14-D-01 新規 pip 依存ゼロ）。

ReDoS 回避方針（04-RESEARCH.md:429）: 正規表現は非貪欲 `.+?` ＋文字クラス
`[^`]+` のみを用い量指定子のネストを禁止する（＝線形時間）。行単位処理のため
巨大入力でも処理時間は入力長に対して線形に収まる。
"""

import re

# ReDoS 回避: 非貪欲 + 文字クラスのみ・量指定子のネスト不使用（線形時間）
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+)`")
_BULLET = re.compile(r"^\s*[-*]\s+")


def _split_inline(text):
    """1 行を [(span_text, inline_tag|None), ...] へ分解する純関数。

    `**bold**` のみ扱う（OCR Markdown の現実的サブセット・ネスト非対応）。
    `_BOLD.finditer` で `**…**` を `("...", "md_bold")` として抽出し、
    前後の非マッチ部は `(text, None)`。マッチが無ければ `[(text, None)]`
    を返す（空リストを返さない）。inline_tag ∈ {"md_bold", None}。
    """
    spans = []
    pos = 0
    for m in _BOLD.finditer(text):
        if m.start() > pos:
            spans.append((text[pos : m.start()], None))
        spans.append((m.group(1), "md_bold"))
        pos = m.end()
    if pos < len(text):
        spans.append((text[pos:], None))
    return spans or [(text, None)]


def parse_markdown(md):
    """Markdown 文字列を [(line_kind, spans), ...] へ変換する純関数。

    戻り値型: list[tuple[str, list[tuple[str, str|None]]]]。
    line_kind ∈ {"md_h1", "md_h2", "md_bullet", "md_code", ""（通常段落）}。
    spans は `_split_inline` の戻り値（見出しはプレフィックス除去後の本文を
    1 span として格納）。

    判定優先順位: code > "## "(md_h2) > "# "(md_h1) > 箇条書き(md_bullet) >
    通常段落（""）。コードフェンス（行頭 strip が ``` 始まり）は `in_code`
    フラグでトグルし、フェンス行自体は出力に含めない。フェンス内では
    見出し判定をしない（"# nothead" は md_code のまま）。

    Tk/fitz 非依存。戻り値は test_md_render.py で直接アサートできる。
    """
    out = []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            out.append(("md_code", [(line, None)]))
        elif line.startswith("## "):
            out.append(("md_h2", [(line[3:], None)]))
        elif line.startswith("# "):
            out.append(("md_h1", [(line[2:], None)]))
        elif _BULLET.match(line):
            body = _BULLET.sub("• ", line)
            out.append(("md_bullet", _split_inline(body)))
        else:
            out.append(("", _split_inline(line)))
    return out
