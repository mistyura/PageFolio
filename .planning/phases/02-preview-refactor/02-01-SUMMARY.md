---
phase: 02-preview-refactor
plan: "01"
subsystem: viewer
tags: [bug-fix, refactor, performance, test]
dependency_graph:
  requires: []
  provides: [BUG-03-fix, TEST-02]
  affects: [pagefolio/viewer.py, tests/test_viewer.py]
tech_stack:
  added: []
  patterns: [pure-function-extraction, sync-render, monkeypatch-spy]
key_files:
  created: [tests/test_viewer.py]
  modified: [pagefolio/viewer.py]
decisions:
  - "D-01: プレビューレンダリングをメインスレッド同期呼び出しに変更（ワーカースレッド廃止）"
  - "D-03: _preview_gen ガードとローディングプレースホルダーを viewer.py から撤去（同期化で不要、他ファイルの _preview_gen には波及なし）"
  - "D-08: _render_preview_pixmap を Tk 非依存の純関数として抽出（テスト容易性向上）"
  - "threading import を削除（F401 回避）"
metrics:
  duration: "約15分"
  completed: "2026-06-03T05:15:00Z"
  tasks_completed: 3
  files_changed: 2
---

# Phase 02 Plan 01: BUG-03 修正 + TEST-02 回帰テスト Summary

**概要:** ページ切り替え時の `doc.tobytes()` フルシリアライズを廃止し、`page.get_pixmap()` の同期直接呼び出しへ変更。Tk 非依存の純関数ヘルパー `_render_preview_pixmap` を抽出してテスト可能にし、回帰テスト `tests/test_viewer.py` を新規作成した。

## タスク完了状況

| タスク | 名前 | コミット | 主要ファイル |
|--------|------|---------|-------------|
| 1 | `_render_preview_pixmap` 純関数抽出・`_show_preview` 同期化 | 62b8a7f | pagefolio/viewer.py |
| 2 | `tests/test_viewer.py` 作成（TEST-02） | e91bf1b | tests/test_viewer.py |
| 3 | Ruff・pytest 全通確認（最終ゲート） | — | 変更なし |

## 変更内容

### pagefolio/viewer.py

- `_render_preview_pixmap(self, page_idx, zoom)` メソッドを新設。`self.doc[page_idx].get_pixmap(matrix=fitz.Matrix(zoom * 1.5, zoom * 1.5), alpha=False)` を直接呼び出し、`(bytes(pix.samples), pix.width, pix.height)` を返す純関数。`doc.tobytes()` を一切呼ばない。
- `_show_preview` からワーカースレッド（`threading.Thread`）、`fitz.open(stream=doc_bytes)` 再オープン、`doc.tobytes()` 呼び出しを撤廃。`_render_preview_pixmap` の同期呼び出しに置き換え。
- `_preview_gen` ガード（65–66, 100行）・ローディングプレースホルダー（71–81行）を撤去。同期化により stale 結果問題が消滅。他ファイルの `_preview_gen` インクリメント箇所（`app.py`, `file_ops.py`, `page_ops.py`）には波及なし（grep 確認済み）。
- `threading` import を削除（F401 回避）。
- 例外処理は `except Exception as e:` + `logger.debug` で維持（裸 except 禁止規約準拠）。
- `scrollregion` 設定・矩形影描画・`create_image` の後処理は変更なしで維持。

### tests/test_viewer.py（新規）

- `class TestPreviewRender` を定義。
- `test_render_does_not_call_tobytes`: `monkeypatch.setattr(fitz.Document, "tobytes", spy)` で呼び出し回数をスパイし、`_render_preview_pixmap` 呼び出し後に `called["n"] == 0` を assert（SC-1）。
- `test_render_returns_valid_samples`: 戻り値 `(samples, w, h)` の型・長さ（`len(samples) == w * h * 3`）・正値を assert（D-09）。
- `types.SimpleNamespace` の軽量スタブで Tk root 不要なテストを実現。`tkinter` / `ImageTk` / `Canvas` 依存なし。

## 検証結果

```
grep -c "self.doc.tobytes()" pagefolio/viewer.py  => 0  ✓（SC-1）
grep "_render_preview_pixmap" pagefolio/viewer.py  => 2件以上  ✓（定義 + 呼び出し）
grep "fitz.open(stream" pagefolio/viewer.py        => 0  ✓
grep -n "except:" pagefolio/viewer.py              => 0  ✓
python -m pytest tests/test_viewer.py -x           => 2 passed  ✓（TEST-02）
python -m pytest -q                                => 147 passed  ✓（回帰なし）
ruff check .                                       => All checks passed  ✓
ruff format --check .                              => 24 files already formatted  ✓
```

## 成功基準

- [x] ページ切り替え時に `doc.tobytes()` が呼ばれず `page.get_pixmap()` 直接呼び出しに変更済み（ROADMAP SC-1 / BUG-03）
- [x] `_render_preview_pixmap` が Tk 非依存の純関数として抽出され、`_show_preview` が同期呼び出しする
- [x] `tests/test_viewer.py`（TEST-02）が tobytes 不使用と samples 妥当性を検証し pytest 全通（ROADMAP SC-4）

## 逸脱内容（Deviations from Plan）

なし — プランの指示通りに実装。

`_preview_gen` と ローディングプレースホルダーの撤去はプラン D-03 でも裁量扱いとされており、波及確認（grep）後に撤去した（viewer.py からの撤去のみ、他ファイルの `_preview_gen` インクリメントは保持）。

## Self-Check: PASSED

- `pagefolio/viewer.py`: 存在確認 FOUND
- `tests/test_viewer.py`: 存在確認 FOUND
- コミット `62b8a7f`: FOUND
- コミット `e91bf1b`: FOUND
