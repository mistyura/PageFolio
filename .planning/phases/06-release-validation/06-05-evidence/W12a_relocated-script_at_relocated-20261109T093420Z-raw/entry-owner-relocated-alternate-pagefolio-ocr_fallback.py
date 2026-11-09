# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""プロバイダーフォールバック純ロジック層 — Tkinter / fitz 非依存。

次候補プロバイダの選択のみを担う（`pagination.py`/`ocr_pipeline.py` と同格の
純ロジック層。02-01-PLAN.md Task 3・02-RESEARCH.md Pattern 6・Architectural
Responsibility Map「次候補プロバイダ選択」）。

フォールバック連鎖は1回限りに制限しない（D-10）: 設定されたチェーンを最後まで
順に辿り、各段の確認・実際のプロバイダ切替・再実行は本モジュールの責務外で
Tk/ネットワーク依存のオーケストレーション層（`ocr_dialog.py`）が担う。

ここには `fitz` / `tkinter` を一切 import しない（`ocr_pipeline.py` の純ロジック
層作法に倣う）。
"""


def next_fallback_candidate(chain, tried):
    """chain の先頭から、まだ試していない最初の候補を返す（D-10）。

    引数を破壊的変更しない純関数。

    引数:
      chain: list[str]  ユーザー設定のフォールバック順プロバイダ名リスト
      tried: set[str]   このダイアログセッション内で既に試行済みのプロバイダ名

    戻り値: 次候補のプロバイダ名。chain が空、または全候補が試行済みなら None
    （D-10: 連鎖は最後まで辿る・1回限りに制限しない）。
    """
    for name in chain:
        if name not in tried:
            return name
    return None


def next_summary_candidate(chain, tried, text_capable):
    """chain から、未試行かつ text_capable に含まれる最初の候補を返す（D-12）。

    全ページ統合サマリ生成のフォールバック専用選択。text プロンプト非対応
    プロバイダ（例: tesseract の `supports_text_prompt() == False`）を候補
    から除外する（D-12・02-RESEARCH.md Open Question 2）。引数を破壊的変更
    しない純関数。

    引数:
      chain:        list[str]  ユーザー設定のフォールバック順プロバイダ名リスト
      tried:        set[str]   既に試行済みのプロバイダ名
      text_capable: set[str]   text プロンプトに対応するプロバイダ名の集合

    戻り値: 次候補のプロバイダ名。該当なしなら None。
    """
    for name in chain:
        if name not in tried and name in text_capable:
            return name
    return None
