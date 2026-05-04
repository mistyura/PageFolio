# Roadmap: PageFolio v1.0

## Overview

v0.9.8.2 の PDF 編集ツールを v1.0 として完成させる。依存関係の固定と画像ファイル対応から始め、最もリスクの高い UI スレッドブロッキング問題を解消し、Undo の差分方式化と複数ページ操作の強化で仕上げる。4フェーズで8要件を完全にカバーする。

## Phases

- [ ] **Phase 1: 基盤と画像対応** - requirements.txt 固定・画像ファイル（PNG/JPG/BMP/TIFF）を開いて編集できるようにする
- [ ] **Phase 2: バックグラウンドレンダリング** - プレビューとサムネイル生成のメインスレッドブロッキングを解消する
- [ ] **Phase 3: Undo 差分化** - Undo スタックを差分方式に変更し大規模 PDF でのメモリ使用量を削減する
- [ ] **Phase 4: 複数ページ操作と保守** - 複数ページの D&D 一括移動・一括トリミングとフォント生成ロジックの統一

## Phase Details

### Phase 1: 基盤と画像対応
**Goal**: 依存関係が固定され、ユーザーが画像ファイルを PDF と同様に開いて既存の全編集操作を使える
**Depends on**: Nothing (first phase)
**Requirements**: MAINT-02, IMG-01
**Success Criteria** (what must be TRUE):
  1. `requirements.txt` がリポジトリに存在し、全依存ライブラリのバージョンが固定されている
  2. ユーザーが PNG/JPG/BMP/TIFF ファイルをファイルメニュー・D&D どちらでも開ける
  3. 画像ファイルを開いた後、回転・削除・結合・保存などの既存操作がそのまま使える
  4. 画像ファイルはサムネイルとプレビューに正しく表示される
**Plans**: TBD
**UI hint**: yes

### Phase 2: バックグラウンドレンダリング
**Goal**: ページ切替・ズーム変更・大規模 PDF 開封時に UI がフリーズしない
**Depends on**: Phase 1
**Requirements**: PERF-01, PERF-02
**Success Criteria** (what must be TRUE):
  1. ページ切替・ズーム変更中にメインウィンドウの操作が止まらない（UI がブロックされない）
  2. 100ページ超の PDF を開いたとき、全サムネイルの生成完了を待たずにアプリが操作できる
  3. サムネイルは順次表示される（最初は空白 → バックグラウンドで埋まる）
  4. プレビューとサムネイルの表示結果は変更前と同じ（見た目の回帰なし）
**Plans**: TBD

### Phase 3: Undo 差分化
**Goal**: 大規模 PDF でのメモリ使用量が削減され、Undo/Redo の動作が従来と変わらない
**Depends on**: Phase 2
**Requirements**: UNDO-01
**Success Criteria** (what must be TRUE):
  1. 操作後の Undo スタックエントリが変更ページのバイト列のみを保持する（全体コピーではない）
  2. 大規模 PDF（50ページ以上）で複数回操作しても Undo/Redo が正しく機能する
  3. Undo/Redo の操作感（ショートカット・UI）が従来と変わらない
**Plans**: TBD

### Phase 4: 複数ページ操作と保守
**Goal**: 複数選択ページを一括で移動・トリミングできる。ダイアログのフォント生成ロジックが統一されている
**Depends on**: Phase 3
**Requirements**: PAGE-01, PAGE-02, MAINT-01
**Success Criteria** (what must be TRUE):
  1. 複数ページを選択した状態で D&D すると、選択ページ全体が目的位置に移動する
  2. 複数ページを選択した状態でトリミングを適用すると、選択全ページに同一 CropBox が適用される
  3. `dialogs.py` の全ダイアログで `settings.py` の共通フォント関数を使用し、重複コードがない
  4. 既存のシングルページ D&D・トリミングは従来通り動作する
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phase 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 基盤と画像対応 | 0/? | Not started | - |
| 2. バックグラウンドレンダリング | 0/? | Not started | - |
| 3. Undo 差分化 | 0/? | Not started | - |
| 4. 複数ページ操作と保守 | 0/? | Not started | - |
