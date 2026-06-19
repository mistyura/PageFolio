# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ja/en LANG キー一致と {sec}/{page} プレースホルダ整合の回帰テスト（Pitfall 3）。

Plan 03-02 で ocr_err_truncated 新規追加・ocr_waiting_retry に {sec} 追加した後の
確定状態（ja/en 同一キー）を回帰防止する。片方の辞書だけ編集する崩れを検出する。
"""

from pagefolio.lang import LANG


def test_lang_keys_parity():
    """LANG['ja'] と LANG['en'] のキー集合が完全一致する。"""
    diff = set(LANG["ja"]) ^ set(LANG["en"])
    assert not diff, f"ja/en の LANG キーが不一致: {diff}"


def test_retry_and_truncated_format_smoke():
    """待機/途切れ文言が {sec}/{page} で KeyError を投げない（{sec} 整合回帰防止）。"""
    for lang in ("ja", "en"):
        d = LANG[lang]
        d["ocr_waiting_retry"].format(page=1, n=1, max=3, sec=5)
        d["ocr_waiting_retry_server"].format(page=1, n=1, max=3, sec=60)
        d["ocr_err_truncated"].format(page=1)
