# Requirements — PageFolio コード最適化

## v1 Requirements

### バグ修正

- [ ] **BUG-01**: ページ挿入操作を Undo すると、挿入前の状態に正しく戻る
  - 現状: `_save_undo("insert", ...)` で挿入ページ数が常に 0 → Undo が何もしない
  - 対象: `pagefolio/file_ops.py` (line 51, 121–123)

- [ ] **BUG-02**: 大きな PDF で Undo を実行しても UI がブロックしない
  - 現状: Undo 時に `doc.tobytes()` でフルシリアライズが走る
  - 対象: `pagefolio/file_ops.py` (lines 63–93)

- [ ] **BUG-03**: ページ切り替え時にプレビューのシリアライズを行わない
  - 現状: `_show_preview()` ごとに `self.doc.tobytes()` を呼んでバックグラウンドスレッドに渡す
  - 対象: `pagefolio/viewer.py` (line 69)
  - 変更方針: ページ単位で `page.get_pixmap()` を直接呼ぶ方式に変更

### リファクタリング

- [ ] **REFAC-01**: `dialogs.py` を `pagefolio/dialogs/` サブパッケージに分割する
  - 現状: 1,191 行・6 クラスが 1 ファイルに混在
  - 分割案: `__init__.py`, `about.py`, `settings.py`, `plugin.py`, `merge.py`, `llm_config.py`

- [ ] **REFAC-02**: `constants.py` を `lang.py` / `themes.py` に分割する
  - 現状: 711 行・テーマ/言語/バージョン/拡張子定数が混在
  - 分割案: `lang.py`（LANG辞書）、`themes.py`（THEMES・C）、`constants.py`（バージョン・拡張子）

- [ ] **REFAC-03**: Undo スタックを `collections.deque(maxlen=MAX_UNDO)` に変更する
  - 現状: `list.pop(0)` が O(n)
  - 対象: `pagefolio/file_ops.py`

- [ ] **REFAC-04**: `settings._current_font_size` 外部アクセスを公開関数に変更する
  - 現状: `app.py` が `_settings_mod._current_font_size` を直接書き換え
  - 変更後: `set_current_font_size(size)` 関数を `settings.py` に追加し、`app.py` から呼ぶ

### テスト

- [ ] **TEST-01**: BUG-01（挿入 Undo）の動作を検証するユニットテスト
  - テスト場所: `tests/test_pdf_ops.py`

- [ ] **TEST-02**: BUG-03（プレビュー生成）の回帰テスト
  - `_show_preview()` が `tobytes()` を呼ばないことを確認
  - テスト場所: `tests/test_utils.py` または新規 `tests/test_viewer.py`

- [ ] **TEST-03**: REFAC-01〜04 の import 回帰テスト
  - 既存の import パスが壊れていないことを確認
  - テスト場所: `tests/` 各ファイル

## v2 Requirements（スコープ外・将来）

- 暗号化 PDF 対応（パスワード解除フロー）
- 印刷機能
- プラグイン API バージョン管理
- OCR エンジン拡張（Ollama / OpenAI 対応）
- サムネイル仮想化（大規模 PDF でのメモリ最適化）

## Out of Scope

- UI/UX デザインの変更 — 本プロジェクトは内部品質改善に集中
- 新機能追加 — バグ修正・リファクタのみ
- `pyproject.toml` / `ruff.toml` の変更 — CLAUDE.md 禁止事項

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| BUG-01 | Phase 1: Undo/Redo 修正 | Pending |
| BUG-02 | Phase 1: Undo/Redo 修正 | Pending |
| REFAC-03 | Phase 1: Undo/Redo 修正 | Pending |
| TEST-01 | Phase 1: Undo/Redo 修正 | Pending |
| BUG-03 | Phase 2: プレビュー最適化とリファクタリング | Pending |
| REFAC-01 | Phase 2: プレビュー最適化とリファクタリング | Pending |
| REFAC-02 | Phase 2: プレビュー最適化とリファクタリング | Pending |
| TEST-02 | Phase 2: プレビュー最適化とリファクタリング | Pending |
| REFAC-04 | Phase 3: API 整理と回帰テスト | Pending |
| TEST-03 | Phase 3: API 整理と回帰テスト | Pending |

---
*Requirements defined: 2026-06-01*
