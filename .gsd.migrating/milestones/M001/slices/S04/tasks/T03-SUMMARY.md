---
id: T03
parent: S04
milestone: M001
key_files:
  - pagefolio/dnd.py
key_decisions:
  - _dnd_drop() の複数選択ルートは既存の単ページルート(dest==src ガード含む)の前に配置し、return で単ページルートをスキップする構造にした（タスクプラン通り）
  - _dnd_start_ghost() のラベル分岐は selected_pages への参照のみで実装し、新しい状態変数は追加しなかった
duration: 
verification_result: passed
completed_at: 2026-05-04T05:04:24.174Z
blocker_discovered: false
---

# T03: dnd.py の _dnd_drop() に複数選択ページの一括移動ルートを追加し、_dnd_start_ghost() のゴーストラベルを N pages 表示に変更した

**dnd.py の _dnd_drop() に複数選択ページの一括移動ルートを追加し、_dnd_start_ghost() のゴーストラベルを N pages 表示に変更した**

## What Happened

T01（file_ops.py の bulk_move 分岐）と T02（constants.py の LANG キー追加）が完了済みであることを確認した上で dnd.py を実装した。

`_dnd_drop()` の変更: `dest = max(0, min(dest, n))` の直後に複数選択ルートを挿入した。`src` が `selected_pages` に含まれ、かつ選択数 > 1 の場合にこのルートが発動する。非選択ページリスト (`non_selected`) を生成し、`dest` から選択ページより前にあるページ数を差し引いた調整済み挿入位置 (`adj_dest`) を計算して `new_order` を構築する。`len(new_order) != n` の安全確認後、`doc.select(new_order)` → `_save_undo("bulk_move", ...)` → カレントページ更新 → キャッシュ無効化 → リフレッシュ → ステータス表示の順で処理し `return`。既存の単ページルートは `if dest == src or dest == src + 1: return` を含めそのまま保持した。

`_dnd_start_ghost()` の変更: `text=f"p.{idx + 1}"` をラベル分岐に差し替え、`idx in self.selected_pages and len(self.selected_pages) > 1` の場合は `f"{len(self.selected_pages)} pages"` を表示するようにした。

## Verification

1. `grep -c "bulk_move\|sorted_sel\|non_selected" pagefolio/dnd.py` → 6（bulk_move×1, sorted_sel×3, non_selected×2）\n2. `ruff check . && ruff format .` → All checks passed / 20 files left unchanged\n3. `pytest --tb=short -q` → 109 passed in 1.00s

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "bulk_move\|sorted_sel\|non_selected" pagefolio/dnd.py` | 0 | ✅ pass | 50ms |
| 2 | `ruff check . && ruff format .` | 0 | ✅ pass | 3000ms |
| 3 | `pytest --tb=short -q` | 0 | ✅ pass | 1000ms |

## Deviations

none

## Known Issues

none

## Files Created/Modified

- `pagefolio/dnd.py`
