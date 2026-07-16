# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""pagefolio/ ソースのフォントサイズ数値ハードコード検出スキャン（D-13）。

`font=("Segoe UI", 16)` のような数値リテラル指定は `font_size` 設定（8〜16）に
追従しないため、`self._font(delta)` ヘルパー経由への是正漏れを CI で構造的に
再発防止する。tests/test_source_keyguard.py の grep 型ソーススキャンをそのまま
踏襲し、正規表現のみ差し替える。

スキャン対象は pagefolio/ のみ（tests/ のダミー定義を誤検知しない・Pitfall 5）。
"""

import pathlib
import re

# フォントサイズの数値リテラル指定を検出する正規表現（R4）。
# 末尾を \d+ に限定することで、`self.font_size`/`fs`/`size` 等の変数連動箇所には
# マッチしない（数値リテラルのみを検出）。
_FONT_HARDCODE_PATTERN = re.compile(r'font=\(\s*["\']Segoe UI["\']\s*,\s*\d+')

# リポジトリ相対で pagefolio/ を解決（CWD 非依存）
_PAGEFOLIO_DIR = pathlib.Path(__file__).resolve().parent.parent / "pagefolio"


def test_no_hardcoded_font_sizes():
    """pagefolio/ の全 .py にフォントサイズの数値ハードコードが無いことを担保する。

    スキャンは pagefolio/ 限定（tests/ 除外）。1 件でも検出したらファイル名を
    添えて失敗させ、将来の `_font(delta)` 是正漏れを構造的に防ぐ。
    """
    offenders = []
    for py in _PAGEFOLIO_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if _FONT_HARDCODE_PATTERN.search(text):
            offenders.append(str(py))
    assert not offenders, f"フォントサイズのハードコードが検出された: {offenders}"


def test_pattern_matches_only_literals():
    """_FONT_HARDCODE_PATTERN の正負判定（数値リテラルのみ検出）を検証する（R4）。"""
    # 数値リテラル指定 → マッチする
    assert _FONT_HARDCODE_PATTERN.search('font=("Segoe UI", 16')
    assert _FONT_HARDCODE_PATTERN.search('font=("Segoe UI", 16, "bold")')

    # 変数指定 → マッチしない
    assert not _FONT_HARDCODE_PATTERN.search('font=("Segoe UI", self.font_size')
    assert not _FONT_HARDCODE_PATTERN.search('font=("Segoe UI", fs')
    assert not _FONT_HARDCODE_PATTERN.search('font=("Segoe UI", size')
