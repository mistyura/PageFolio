# PageFolio — コード最適化プロジェクト

## What This Is

PageFolio の既存コードベースに対する最適化プロジェクト。
バグ修正・リファクタリング・テスト充実の 3 軸で品質を底上げする。

**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする。

## Context

| 項目 | 内容 |
|------|------|
| リポジトリ | `C:\Users\shdwf\work\project\PageFolio` |
| 言語 | Python 3.8+ / Tkinter |
| 現在バージョン | `pagefolio/constants.py` の `APP_VERSION` を参照 |
| テスト | pytest（現在小規模） |
| リント | ruff |

既存コードベースマップ: `.planning/codebase/`

## Problem Statement

コードベース分析で以下の問題が発見された。

### バグ（動作に影響）

| ID | 問題 | 影響 |
|----|------|------|
| BUG-01 | ページ挿入操作の Undo が何もしない（`state["data"] = [insert_at, 0]` で挿入数が常に 0） | 挿入後に Undo してもページが残る |
| BUG-02 | Undo 実行時に `doc.tobytes()` でフルシリアライズ（Undo/Redo 非対称設計） | 大きな PDF で Undo が重い |
| BUG-03 | プレビュー生成のたびに `doc.tobytes()` でフルシリアライズ | ページ切り替えが遅い |

### 技術的負債（保守性に影響）

| ID | 問題 | 現状 |
|----|------|------|
| DEBT-01 | `dialogs.py` 肥大化 | 1,191 行・6 クラスが 1 ファイルに混在 |
| DEBT-02 | `constants.py` 肥大化 | 711 行・テーマ/言語/バージョンが混在 |
| DEBT-03 | Undo スタックの `list.pop(0)` が O(n) | `collections.deque` で O(1) にできる |
| DEBT-04 | `settings._current_font_size` をモジュール外部から直接書き換え | プライベート変数への外部アクセス |

## Requirements

### Validated

- ✓ Tkinter UI フレームワーク — 既存
- ✓ pymupdf (fitz) による PDF 操作 — 既存
- ✓ Mixin パターンによるモジュール分割 — 既存
- ✓ pytest + ruff によるテスト・リント体制 — 既存

### Active

- [ ] BUG-01: ページ挿入 Undo が正しく元に戻る
- [ ] BUG-02: Undo 実行時のシリアライズコストを削減する
- [ ] BUG-03: プレビュー生成のフルシリアライズを廃止する
- [ ] DEBT-01: `dialogs.py` をダイアログ単位のモジュールに分割する
- [ ] DEBT-02: `constants.py` を `lang.py`・`themes.py` に分割する
- [ ] DEBT-03: Undo スタックを `collections.deque(maxlen=MAX_UNDO)` に変更する
- [ ] DEBT-04: `settings._current_font_size` 外部アクセスを公開関数 `set_current_font_size()` 経由に変更する
- [ ] TEST: 修正・リファクタ各項目に対応するユニットテストを追加する

### Out of Scope

- 暗号化 PDF 対応 — 別機能追加であり本プロジェクトの最適化スコープ外
- 印刷機能 — 同上
- OCR エンジンの拡張 — 同上
- プラグイン API バージョン管理 — 今後の別タスク
- UI/UX デザインの変更 — 本プロジェクトは内部品質に集中

## Key Decisions

| 決定事項 | 根拠 | 状態 |
|---------|------|------|
| BUG-02 対応：差分保存方式ではなくページ単位キャッシュ方式 | Undo スタックの設計を全面置き換えするより、プレビュー側のシリアライズをなくす方が影響範囲が小さい | 検討中 |
| BUG-03 対応：`doc.tobytes()` をバックグラウンドスレッドに渡すのをやめ、ページ単位で `page.get_pixmap()` を直接呼ぶ | fitz のスレッドセーフ制約を迂回しつつ、フルシリアライズを排除できる | 検討中 |
| DEBT-01：dialogs をサブパッケージ `pagefolio/dialogs/` に分割 | `dialogs.py` 単体でのモジュール分割より import パスの変更が最小化される | 検討中 |

## Evolution

このドキュメントはフェーズ移行・マイルストーン完了時に更新される。

**フェーズ移行後:**
1. 完了した要件 → Validated へ移動（フェーズ番号を付記）
2. 無効になった要件 → Out of Scope へ移動（理由を付記）
3. 新たに発見された要件 → Active へ追加
4. 決定事項 → Key Decisions を更新

---
*Last updated: 2026-06-01 after initialization*
