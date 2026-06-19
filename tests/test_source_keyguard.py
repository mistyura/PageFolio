# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""pagefolio/ ソースの実 API キーパターン埋め込み防止スキャン（D-12）。

実キーがソースへ誤コミットされ git 履歴へ漏れる経路を CI で構造的に再発防止する。
スキャン対象は pagefolio/ のみ（tests/ のダミーキーを誤検知しない・Pitfall 5）。
"""

import pathlib
import re

# 実キー形式の正規表現（誤検知回避のため実キー長近辺の閾値・Pitfall 5）
#   Anthropic: sk-ant-... は 100 字超
#   Google AI: AIza... は 39 字
_KEY_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{30,}"),
]

# リポジトリ相対で pagefolio/ を解決（CWD 非依存）
_PAGEFOLIO_DIR = pathlib.Path(__file__).resolve().parent.parent / "pagefolio"


def test_no_real_api_keys_in_source():
    """pagefolio/ の全 .py に実 API キーパターンが存在しないことを担保する。

    スキャンは pagefolio/ 限定（tests/ 除外）。1 件でも検出したらファイル名と
    パターンを添えて失敗させ、将来の誤コミットを構造的に防ぐ。
    """
    offenders = []
    for py in _PAGEFOLIO_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for pat in _KEY_PATTERNS:
            if pat.search(text):
                offenders.append((str(py), pat.pattern))
    assert not offenders, f"ソースに実 API キーパターンが検出された: {offenders}"
