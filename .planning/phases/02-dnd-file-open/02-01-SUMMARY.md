---
phase: 02-dnd-file-open
plan: 01
subsystem: ui
tags: [tkinterdnd2, dnd, drag-and-drop, tkinter, pdf]

# Dependency graph
requires:
  - phase: 01-code-quality-responsive-ui
    provides: PanedWindow レイアウトと TkinterDnD.Tk() が使えるレスポンシブ UI 基盤
provides:
  - tkinterdnd2 による preview_canvas へのドロップターゲット登録
  - 単一 PDF ドロップ時の未保存確認 → _open_pdf_path 呼び出し
  - 複数 PDF ドロップ時の MergeOrderDialog 呼び出し
  - DropEnter/DropLeave によるビジュアルフィードバック（背景色 + テキスト）
  - _rebuild_ui 後の D&D フック再登録
affects:
  - 03 以降すべての UI 変更フェーズ（preview_canvas の D&D フック維持が必要）

# Tech tracking
tech-stack:
  added: [tkinterdnd2]
  patterns:
    - "TkinterDnD.Tk() でルート初期化（_HAS_TKDND フォールバック付き）"
    - "canvas.drop_target_register(DND_FILES) + canvas.dnd_bind() による領域限定 D&D"
    - "tk.splitlist(event.data) でスペース入りパスを安全に分割"
    - "return event.action を全ハンドラで必ず返す（Tcl 通信維持）"
    - "_rebuild_ui 末尾に _setup_file_drop(self) を追加して D&D フックを再登録"

key-files:
  created: []
  modified:
    - pagefolio.py

key-decisions:
  - "windnd を完全除去し tkinterdnd2 に一本化（PyInstaller バンドリング対応が優れているため）"
  - "DropEnter/DropLeave/Drop の3ハンドラ構成で preview_canvas のみをターゲットに限定"
  - "非 PDF ドロップ時は _set_status → messagebox.showwarning に変更（ステータスバーが右上で気づきにくいという検証フィードバックを反映）"

patterns-established:
  - "D&D セットアップ: _setup_file_drop(app) は _build_ui および _rebuild_ui 末尾の両方で呼ぶ"
  - "DropEnter/DropLeave/Drop: 常に return event.action を返す"

requirements-completed: [DND-01, DND-02, DND-03]

# Metrics
duration: 15min
completed: 2026-03-18
---

# Phase 2 Plan 01: D&D ファイルオープン Summary

**windnd を tkinterdnd2 に移行し、preview_canvas 限定の PDF ドラッグ&ドロップ機能（単一/複数ファイル対応・ビジュアルフィードバック付き）を実装**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-18T20:18:00+09:00
- **Completed:** 2026-03-18T20:28:36+09:00
- **Tasks:** 2 (auto + human-verify)
- **Files modified:** 1

## Accomplishments

- tkinterdnd2 への移行完了（windnd 完全除去）
- preview_canvas 限定ドロップターゲット登録（DropEnter / DropLeave / Drop の3ハンドラ）
- 単一 PDF ドロップ → 未保存確認ダイアログ → _open_pdf_path、複数 PDF → MergeOrderDialog
- ドラッグ中のビジュアルフィードバック（アクセント色背景 + 「ここに PDF をドロップ」テキスト）
- _rebuild_ui 後の D&D フック再登録（テーマ変更後も正常動作）
- 手動テスト全9項目合格（DND-01 / DND-02 / DND-03 すべて確認）

## Task Commits

各タスクは個別にコミット:

1. **Task 1: tkinterdnd2 移行と D&D ハンドラ実装** - `6110922` (feat)
2. **Task 2 検証後修正: 非 PDF ドロップ時に警告ダイアログ表示に変更** - `fdb9cc9` (fix)

## Files Created/Modified

- `pagefolio.py` — tkinterdnd2 import、DND ハンドラ3メソッド（_on_dnd_enter/_on_dnd_leave/_on_dnd_drop）、_setup_file_drop 書き換え、__main__ 変更、LANG 辞書追加

## Decisions Made

- **windnd 完全除去・tkinterdnd2 一本化**: PyInstaller バンドリング対応が優れており、preview_canvas へのピンポイント登録が可能なため採用
- **非 PDF ドロップ時の通知方法変更**: 手動テスト中にステータスバー（右上）は気づきにくいとのフィードバックを受け、messagebox.showwarning に変更

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 非 PDF ドロップ時の通知を警告ダイアログに変更**

- **Found during:** Task 2 検証（human-verify 承認後の追加修正）
- **Issue:** 計画では `_set_status(self._t("dnd_pdf_only"))` でステータスバー表示を指定していたが、ステータスバーが右上に位置しておりユーザーが気づきにくいという検証フィードバックがあった
- **Fix:** `messagebox.showwarning` を使用した警告ダイアログ表示に変更
- **Files modified:** `pagefolio.py`
- **Verification:** 非 PDF ファイルドロップ時に警告ダイアログが表示されることを確認
- **Committed in:** `fdb9cc9` (fix コミット)

---

**Total deviations:** 1 auto-fixed (1 bug — UX 改善)
**Impact on plan:** ユーザー通知方法の改善のみ。機能スコープへの影響なし。

## Issues Encountered

なし。

## User Setup Required

なし — 外部サービス設定不要。

## Next Phase Readiness

- D&D 機能は完全動作。DND-01 / DND-02 / DND-03 すべて満たした
- preview_canvas に dnd_bind が登録されているため、今後 _rebuild_ui を変更する際は `_setup_file_drop(self)` の呼び出しを維持すること
- Phase 3 以降の UI 変更時に D&D フック再登録パターンを踏襲すること

---
*Phase: 02-dnd-file-open*
*Completed: 2026-03-18*
