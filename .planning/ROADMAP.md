# Roadmap: PageFolio v1.0

## Overview

PageFolio v0.9.4 から v1.0 へのリリースロードマップ。既存の PDF ページ操作機能はすべて動作済みであり、v1.0 の目標は「品質向上と配布」に集約される。レスポンシブ UI の修正、D&D ファイルオープン、大容量 PDF のパフォーマンス改善、PyInstaller exe 化の 4 段階で、安定した配布可能なデスクトップアプリを完成させる。

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: コード品質改善とレスポンシブ UI** - バグ修正・コードレビューとレイアウト再構築で土台を固める
- [ ] **Phase 2: D&D ファイルオープン** - プレビュー領域へのドラッグ&ドロップで PDF を開く機能を追加
- [ ] **Phase 3: パフォーマンスと品質仕上げ** - 大容量 PDF の非ブロッキング読み込みとエラーメッセージ多言語対応
- [ ] **Phase 4: PyInstaller exe 配布** - onedir 形式で Windows exe パッケージを生成

## Phase Details

### Phase 1: コード品質改善とレスポンシブ UI
**Goal**: ユーザーがウィンドウサイズを自由に変更でき、パネル比率も調整できるレイアウトで快適に操作できる。既存バグが修正され安定した土台がある。
**Depends on**: Nothing (first phase)
**Requirements**: QUAL-01, UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. ウィンドウを任意のサイズにリサイズしても右側ツールパネルが見切れない
  2. サムネイル・プレビュー・ツールパネル間の境界をドラッグして比率を変更できる
  3. ウィンドウを極端に狭くしてもサムネイルパネルが消えず最小幅が保たれる
  4. 既存機能（回転・削除・トリミング・結合・D&D 並び替え・Undo/Redo）が正常動作する
**Plans**: TBD

Plans:
- [ ] 01-01: TBD
- [ ] 01-02: TBD

### Phase 2: D&D ファイルオープン
**Goal**: ユーザーがエクスプローラーから PDF ファイルをプレビュー領域にドラッグ&ドロップするだけでファイルを開ける
**Depends on**: Phase 1
**Requirements**: DND-01, DND-02, DND-03
**Success Criteria** (what must be TRUE):
  1. プレビュー領域に PDF をドロップするとそのファイルが開かれる
  2. 複数の PDF を同時にドロップすると結合ダイアログが表示される
  3. ファイルをプレビュー領域にドラッグ中、ドロップ可能であることを示すビジュアルフィードバックが表示される
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

### Phase 3: パフォーマンスと品質仕上げ
**Goal**: 大容量 PDF を開いても UI がフリーズせず、読み込み進捗が可視化され、全エラーメッセージが多言語対応されている
**Depends on**: Phase 2
**Requirements**: PERF-01, PERF-02, QUAL-02
**Success Criteria** (what must be TRUE):
  1. 100 ページ以上の PDF を開いている間もウィンドウ操作（移動・リサイズ・閉じる）が可能
  2. PDF 読み込み中にステータスバーで「ページ N / M を読み込み中...」のような進捗が表示される
  3. エラーダイアログやステータスメッセージが日本語/英語の両方で表示される
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: PyInstaller exe 配布
**Goal**: Python 環境のない Windows マシンで PageFolio を起動・使用できる配布パッケージが生成される
**Depends on**: Phase 3
**Requirements**: DIST-01, DIST-02
**Success Criteria** (what must be TRUE):
  1. `dist/PageFolio/` フォルダ内の exe をダブルクリックしてアプリが起動する
  2. コンソールウィンドウが表示されない（--noconsole モード）
  3. Python 未インストールの Windows マシンで PDF を開き、編集し、保存できる
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. コード品質改善とレスポンシブ UI | 0/? | Not started | - |
| 2. D&D ファイルオープン | 0/? | Not started | - |
| 3. パフォーマンスと品質仕上げ | 0/? | Not started | - |
| 4. PyInstaller exe 配布 | 0/? | Not started | - |
