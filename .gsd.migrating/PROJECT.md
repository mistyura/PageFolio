# PageFolio

## What This Is

Windows 向けデスクトップ PDF（および画像）編集ツール。Python + Tkinter で構築され、PyInstaller で exe 配布可能。ページの閲覧・回転・削除・トリミング・複製・結合・分割などの操作を単一 GUI で提供する。v0.9.8.2 時点で PDF 入力に対応済み。

## Core Value

PDF と画像ファイルを開いてページ単位で素早く編集し、保存できること。UIが止まらず、操作が確実に Undo できること。

## Current Milestone: v1.0 画像対応・パフォーマンス・操作性改善

**Goal:** 画像ファイル対応と UI ブロッキング解消を中心に、PDF 編集ツールとしての完成度を高める

**Target features:**
- PNG/JPG/BMP/TIFF 等の画像ファイルを PDF 同様に開いて編集できる（IMG-01）
- プレビュー・サムネイル生成のバックグラウンド化（PERF-01, PERF-02）
- Undo スタックを差分方式に変更してメモリ使用量を削減（UNDO-01）
- 複数選択ページの D&D 一括移動・一括トリミング（PAGE-01, PAGE-02）
- ダイアログのフォント生成統一・requirements.txt バージョン固定（MAINT-01, MAINT-02）

## Requirements

### Validated

- ✓ PDF ファイルを開いてプレビュー・サムネイル表示 — 既存
- ✓ ページの回転（時計回り・反時計回り、単体・複数選択） — 既存
- ✓ ページの削除（単体・複数選択） — 既存
- ✓ ページのトリミング（CropBox、現在ページのみ） — 既存
- ✓ ページの複製 — 既存
- ✓ 外部 PDF からのページ挿入 — 既存
- ✓ 複数 PDF の結合 — 既存
- ✓ PDF の分割保存（ページ範囲指定） — 既存
- ✓ Undo/Redo（全体コピー方式、最大 20 件） — 既存
- ✓ 上書き保存・名前付け保存・圧縮保存 — 既存
- ✓ D&D によるページ並び替え（1 ページずつ） — 既存
- ✓ ファイル D&D（tkinterdnd2） — 既存
- ✓ ダーク・ライトテーマ切替 — 既存
- ✓ フォントサイズ変更 — 既存
- ✓ 閲覧モード・編集モード切替（F5） — 既存
- ✓ 日本語・英語表示切替 — 既存
- ✓ プラグインシステム — 既存
- ✓ ウィンドウ位置・サイズの前回引き継ぎ — 既存
- ✓ PyInstaller による exe 配布 — 既存

### Active

- [ ] PNG/JPG/BMP/TIFF 等の画像ファイルを PDF 同様に開いて編集できる
- [ ] プレビュー生成をバックグラウンド処理し、メインスレッドのブロッキングを解消する
- [ ] サムネイル生成をバックグラウンド処理または遅延生成し、大規模 PDF でのフリーズを解消する
- [ ] Undo スタックを差分方式に変更してメモリ使用量を削減する
- [ ] 複数選択ページを D&D で一括移動できる
- [ ] 複数選択ページに同一トリミングを一括適用できる
- [ ] `dialogs.py` のフォント生成ロジックを `settings.py` の共通関数に統一する
- [ ] `requirements.txt` にバージョンを固定してコミットする

### Out of Scope

- パスワード付き PDF 対応 — 今回スコープ外（別途検討）
- UI テスト追加 — 機能追加・改善に集中するため今回は除外
- LANG 辞書の JSON ファイル分離 — exe 化との互換性確認が必要なため今回は除外
- リアルタイム OCR/編集機能 — 本アプリの対象範囲外

## Context

- Python 3.8+ / Tkinter / PyMuPDF (fitz) 1.27.2.2 / Pillow 12.2.0 / tkinterdnd2 0.4.3
- Mixin 合成パターン（UIBuilderMixin / FileOpsMixin / PageOpsMixin / ViewerMixin / DnDMixin）
- codebase map: `.planning/codebase/`（2026-05-04 分析済み）
- 主な技術的負債: プレビュー・サムネイルのメインスレッドブロック、Undo の全体コピー方式、`_refresh_all()` の全件再描画
- 画像ファイル対応: PyMuPDF は `fitz.open()` で画像ファイル（PNG/JPEG 等）を直接開き、単一ページ PDF として扱える。この仕組みを活用する方針
- Tkinter はシングルスレッド。バックグラウンド処理には `threading.Thread` + `root.after()` でスレッドセーフに UI 更新する

## Constraints

- **Tech stack**: Python + Tkinter — GUI フレームワーク変更は対象外
- **Platform**: Windows 11 — macOS/Linux 対応は今回スコープ外
- **Compatibility**: exe 配布（PyInstaller）との互換性を維持すること
- **Code style**: Ruff チェック必須、`except Exception as e:` 形式、`C["KEY"]` テーマ参照、`self._font(delta)` フォント生成

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 画像ファイルを fitz.open() で PDF として扱う | PyMuPDF が画像→PDF 変換を内部で処理するため実装コスト最小 | — Pending |
| バックグラウンドレンダリングに threading.Thread + root.after() を使用 | Tkinter のシングルスレッド制約を守りつつ非同期化できる最小コスト手段 | — Pending |
| Undo 差分方式: 変更ページのバイト列のみキャッシュ | 全体コピーより大幅にメモリ削減、実装リスクは中程度 | — Pending |

## Evolution

このドキュメントはフェーズ移行・マイルストーン境界で更新する。

**各フェーズ移行後（`/gsd-transition`）:**
1. 無効化された要件 → Out of Scope へ（理由付き）
2. 検証された要件 → Validated へ（フェーズ参照付き）
3. 新たに浮上した要件 → Active へ追加
4. 記録すべき決定 → Key Decisions へ追加
5. "What This Is" がずれていないか確認・更新

**各マイルストーン後（`/gsd-complete-milestone`）:**
1. 全セクションのフルレビュー
2. Core Value の確認
3. Out of Scope の理由が今も有効か監査
4. Context の現状反映

---
*Last updated: 2026-05-04 — Milestone v1.0 started*
