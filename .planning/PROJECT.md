# PageFolio v1.0 改善・exe化プロジェクト

## What This Is

PageFolio は Python (Tkinter + PyMuPDF) で構築された Windows 向け PDF エディタ。ページの閲覧・回転・削除・トリミング・結合・並び替えなどの基本操作を提供する。現在 v0.9.4 で、v1.0 リリースに向けた UI 改善・機能追加・品質向上・exe 化を行う。

## Core Value

PDF の基本的なページ操作（閲覧・回転・削除・トリミング・結合・並び替え）を、軽量かつ直感的な UI で提供すること。

## Requirements

### Validated

- ✓ PDF ファイルの閲覧・ページプレビュー — existing
- ✓ ページの回転（90°単位） — existing
- ✓ ページの削除（複数選択対応） — existing
- ✓ ページのトリミング（ドラッグ選択） — existing
- ✓ 複数 PDF の結合（順序指定ダイアログ） — existing
- ✓ サムネイル D&D によるページ並び替え — existing
- ✓ PDF の挿入（指定位置に別ファイル挿入） — existing
- ✓ Undo / Redo（最大20回） — existing
- ✓ ダーク/ライト/システムテーマ切り替え — existing
- ✓ フォントサイズ設定（8〜16pt） — existing
- ✓ 日本語/英語 UI ローカライゼーション — existing
- ✓ プラグインシステム（イベント駆動型） — existing
- ✓ 複数 PDF 同時オープン（結合モード） — existing
- ✓ サムネイルダブルクリックでページ拡大表示 — existing
- ✓ キーボードショートカット — existing

### Active

- [ ] レスポンシブ UI（ウィンドウサイズに応じたレイアウト調整、右側見切れ解消）
- [ ] D&D ファイルオープン（プレビュー領域へのドロップで PDF を開く、複数ファイル対応）
- [ ] 全体コードレビュー・バグ修正
- [ ] コード品質改善（リファクタリング・可読性・保守性）
- [ ] UX 改善（操作性・フローの最適化）
- [ ] パフォーマンス最適化（大きい PDF での速度・応答性）
- [ ] PyInstaller によるフォルダ形式 exe 化

### Out of Scope

- 印刷機能 — v1.0 後に検討
- パスワード保護 PDF の解除 — 複雑性が高く v1.0 範囲外
- 複数ページ一括トリミング — v1.0 後に検討
- 複数ページ D&D 一括移動 — v1.0 後に検討
- ページ範囲指定での分割保存 — v1.0 後に検討
- インストーラー(.msi) 形式の配布 — フォルダ形式で十分

## Context

- 単一ファイル構成（`pagefolio.py` に全コードが集約、約10万文字）
- Windows 11 がターゲット OS
- pymupdf (fitz) + Pillow が PDF 処理の中核
- windnd ライブラリが既にオプション依存に含まれている（D&D のベース）
- プラグインシステムが実装済み（機能拡張のフレームワーク有り）
- テーマシステムが成熟（ダーク/ライト/システム対応済み）
- 右側ツールパネルがスクロール可能 Canvas 構成で実装されている

## Constraints

- **Tech stack**: Python 3.8+ / Tkinter / pymupdf / Pillow — 変更不可
- **File structure**: 単一ファイル構成（pagefolio.py）を維持
- **OS**: Windows 11 対象
- **exe 化**: PyInstaller 使用、フォルダ形式配布

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| レスポンシブ UI を採用 | 最小サイズ拡大だけでは根本解決にならない | — Pending |
| D&D 先はプレビュー領域 | ユーザーが最も注視するエリアで自然な操作感 | — Pending |
| exe はフォルダ形式 | 起動速度を重視、単一 exe は起動が遅い | — Pending |
| 単一ファイル構成維持 | 既存アーキテクチャを尊重、リスク最小化 | — Pending |

---
*Last updated: 2026-03-18 after initialization*
