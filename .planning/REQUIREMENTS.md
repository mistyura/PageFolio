# Requirements: PageFolio

**Defined:** 2026-05-04
**Core Value:** PDF と画像ファイルを開いてページ単位で素早く編集し、保存できること。UI が止まらず、操作が確実に Undo できること。

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### 画像ファイル対応 (IMG)

- [ ] **IMG-01**: PNG/JPG/BMP/TIFF 等の画像ファイルを PDF と同様に開いて閲覧・編集できる（回転・削除・結合等の既存操作が使える）

### パフォーマンス改善 (PERF)

- [ ] **PERF-01**: プレビュー生成をバックグラウンドスレッドで行い、ページ切替・ズーム変更時に UI がブロックされない
- [ ] **PERF-02**: サムネイル生成を遅延生成またはバックグラウンド生成し、100 ページ超の PDF 開封時に UI がフリーズしない

### Undo 改善 (UNDO)

- [ ] **UNDO-01**: Undo スタックを変更ページのみキャッシュする差分方式に変更し、大規模 PDF でのメモリ使用量を削減する

### 複数ページ操作 (PAGE)

- [ ] **PAGE-01**: 複数選択ページを D&D 操作で一括移動できる
- [ ] **PAGE-02**: 複数選択ページに同一 CropBox トリミングを一括適用できる

### 保守性改善 (MAINT)

- [ ] **MAINT-01**: `dialogs.py` のフォント生成ロジック（`_font()` の重複）を `settings.py` の共通関数に統一する
- [ ] **MAINT-02**: `requirements.txt` に全依存ライブラリのバージョンを固定して git に追加する

## v2 Requirements

Deferred to future. Tracked but not in current roadmap.

### セキュリティ・拡張

- **SEC-01**: パスワード付き PDF に対してパスワード入力ダイアログを表示して開けるようにする
- **SEC-02**: tkinterdnd2 未インストール時に案内メッセージを表示する

### テスト・品質

- **TEST-01**: Tkinter UI コンポーネントの自動テストを追加する
- **TEST-02**: ファイル操作フロー（open/save）の統合テストを追加する
- **TEST-03**: トリミング座標変換ロジックの単体テストを追加する

### アーキテクチャ改善

- **ARCH-01**: LANG 辞書を `pagefolio/i18n/` の JSON ファイルに分離する（exe 互換性確認要）
- **ARCH-02**: グローバル `C` 辞書をテスト独立性のために DI 化する
- **ARCH-03**: ポップアップビューアの `self.doc` 競合アクセス問題を修正する

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| パスワード付き PDF 対応 | v2 に延期 — 今回は画像対応とパフォーマンスに集中 |
| UI テスト追加 | 機能追加・改善に集中するため今回は除外 |
| LANG 辞書 JSON 分離 | PyInstaller exe との互換性確認が必要なため延期 |
| グローバル `C` 辞書リアーキテクチャ | 影響範囲が大きくリスクが高いため延期 |
| macOS/Linux 対応 | 対象 OS が Windows 11 のみ |
| リアルタイム OCR | 本アプリの対象範囲外 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MAINT-02 | Phase 1 | Pending |
| IMG-01 | Phase 1 | Pending |
| PERF-01 | Phase 2 | Pending |
| PERF-02 | Phase 2 | Pending |
| UNDO-01 | Phase 3 | Pending |
| PAGE-01 | Phase 4 | Pending |
| PAGE-02 | Phase 4 | Pending |
| MAINT-01 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-04*
*Last updated: 2026-05-04 — Traceability updated after roadmap creation*
