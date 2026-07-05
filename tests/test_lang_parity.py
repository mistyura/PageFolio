# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ja/en LANG キー一致と {sec}/{page} プレースホルダ整合の回帰テスト（Pitfall 3）。

Plan 03-02 で ocr_err_truncated 新規追加・ocr_waiting_retry に {sec} 追加した後の
確定状態（ja/en 同一キー）を回帰防止する。片方の辞書だけ編集する崩れを検出する。
"""

import os

from pagefolio.lang import LANG

# D-11: 動的キー参照（f-string 等でのキー名合成）用の許可リスト。
# 現状は静的リテラル参照のみでゼロ件（04-RESEARCH.md Pitfall 3 で確認済み）。
# 将来 f"..._label" のような動的合成が発生した場合、理由コメント付きで
# ここへキー名を追加することで誤検出を回避する。
_ALLOWLIST = set()

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LANG_PY_PATH = os.path.normpath(os.path.join(_REPO_ROOT, "pagefolio", "lang.py"))


def _iter_source_files():
    """pagefolio/（lang.py 除く）・tests/・plugins/ 配下の全 .py ファイルパスを返す。"""
    for rel_dir in ("pagefolio", "tests", "plugins"):
        base = os.path.join(_REPO_ROOT, rel_dir)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirnames, filenames in os.walk(base):
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                path = os.path.normpath(os.path.join(dirpath, fn))
                if path == _LANG_PY_PATH:
                    continue  # lang.py 自体は定義側であり使用側ではないため除外
                yield path


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


def test_no_unused_lang_keys():
    """全 LANG キーが pagefolio/・tests/・plugins/ のどこかで参照されている（D-11）。

    引用符付き完全一致（"key" または 'key'）で照合し、部分文字列一致による
    誤判定（例: 削除済み `tesseract_not_installed` と使用中の
    `tesseract_not_installed_hint` のプレフィックス衝突）を避ける。
    """
    combined_parts = []
    for path in _iter_source_files():
        with open(path, encoding="utf-8") as f:
            combined_parts.append(f.read())
    combined = "\n".join(combined_parts)

    unused = [
        key
        for key in LANG["ja"]
        if key not in _ALLOWLIST
        and f'"{key}"' not in combined
        and f"'{key}'" not in combined
    ]
    assert not unused, f"未使用の LANG キーが検出されました: {sorted(unused)}"
