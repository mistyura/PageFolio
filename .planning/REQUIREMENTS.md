# Requirements: PageFolio v1.0

**Defined:** 2026-03-18
**Core Value:** PDF の基本的なページ操作を、軽量かつ直感的な UI で提供すること

## v1 Requirements

Requirements for v1.0 release. Each maps to roadmap phases.

### UI / レスポンシブ

- [x] **UI-01**: ウィンドウリサイズに応じてレイアウトが自動調整される（右側見切れ解消）
- [x] **UI-02**: PanedWindow による分割ペインでユーザーがパネル比率を調整できる
- [x] **UI-03**: サムネイルパネルが最小幅を保証し、狭いウィンドウでも消えない

### D&D ファイルオープン

- [x] **DND-01**: プレビュー領域に PDF をドロップしてファイルを開ける
- [x] **DND-02**: 複数 PDF を同時ドロップすると結合ダイアログが表示される
- [x] **DND-03**: ドロップ対象エリアにファイルをドラッグするとビジュアルフィードバックが表示される

### パフォーマンス

- [ ] **PERF-01**: 大きい PDF を開く際に UI がフリーズしない（非ブロッキング読み込み）
- [ ] **PERF-02**: PDF 読み込み中にステータスバーで進捗が表示される

### コード品質

- [x] **QUAL-01**: 全体コードレビューでバグを修正する
- [ ] **QUAL-02**: 全エラーメッセージが日本語/英語に対応している

### 配布

- [ ] **DIST-01**: PyInstaller onedir 形式で exe パッケージを生成できる
- [ ] **DIST-02**: `--noconsole` モードで正常動作する（sys.stdout ガード）

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### UX 拡張

- **UX-01**: インクリメンタルサムネイルレンダリング（部分的に読み込み完了したページから操作可能）
- **UX-02**: スプラッシュスクリーン（exe 起動時の体感速度向上）
- **UX-03**: プラグインイベントとして D&D 通知を発火

### ページ操作拡張

- **PAGE-01**: 複数ページの一括トリミング
- **PAGE-02**: 複数ページの D&D 一括移動
- **PAGE-03**: ページ範囲指定での分割保存

## Out of Scope

| Feature | Reason |
|---------|--------|
| 単一 exe (--onefile) | 起動が 2-10 秒遅くなる、PyMuPDF バイナリで肥大化 |
| リアルタイムクロッププレビュー | 毎ピクセル再描画で CPU 負荷過大、Tkinter で実用的でない |
| 自動保存 | Undo スタック (20回) で十分、I/O 競合リスク |
| タブ型マルチドキュメント | Tkinter にネイティブタブウィジェットなし、単一ファイル構成と相性悪い |
| PDF テキスト編集・注釈 | 「ページ操作」のコアバリューから外れる、フォント埋め込み等の複雑性 |
| クラウド同期 | ネットワーク I/O 未対応、認証の複雑性 |
| 印刷機能 | v1.0 後に検討 |
| パスワード保護 PDF 解除 | 複雑性が高い |
| インストーラー(.msi) | フォルダ形式で十分 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| QUAL-01 | Phase 1 | Complete (01-01) |
| UI-01 | Phase 1 | Complete (01-01) |
| UI-02 | Phase 1 | Complete (01-01) |
| UI-03 | Phase 1 | Complete (01-01) |
| DND-01 | Phase 2 | Complete (02-01) |
| DND-02 | Phase 2 | Complete (02-01) |
| DND-03 | Phase 2 | Complete (02-01) |
| PERF-01 | Phase 3 | Pending |
| PERF-02 | Phase 3 | Pending |
| QUAL-02 | Phase 3 | Pending |
| DIST-01 | Phase 4 | Pending |
| DIST-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after Plan 02-01 completion (DND-01, DND-02, DND-03 complete)*
