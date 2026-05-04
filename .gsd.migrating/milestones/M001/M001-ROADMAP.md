# M001: v1.0 画像対応・パフォーマンス・操作性改善

**Vision:** Windows 向けデスクトップ PDF（および画像）編集ツール。Python + Tkinter で構築され、PyInstaller で exe 配布可能。ページの閲覧・回転・削除・トリミング・複製・結合・分割などの操作を単一 GUI で提供する。v0.9.8.2 をベースに v1.0 として完成させる。

## Success Criteria

- PNG/JPG/BMP/TIFF ファイルをファイルメニュー・D&D どちらでも開き、既存の全編集操作が使える
- ページ切替・ズーム変更・大規模 PDF 開封時に UI がフリーズしない（バックグラウンドレンダリング）
- Undo スタックが差分方式になり、大規模 PDF でのメモリ使用量が削減される
- 複数選択ページを D&D で一括移動・一括トリミングできる
- requirements.txt にバージョン固定済みの依存ライブラリがコミットされている

## Slices

- [ ] **S01: 基盤と画像対応** `risk:medium` `depends:[]`
  > After this: requirements.txt 固定済み、PNG/JPG/BMP/TIFF ファイルを開いて既存の全編集操作が使える

- [ ] **S02: バックグラウンドレンダリング** `risk:medium` `depends:[S01]`
  > After this: 大規模 PDF を開いてページ切替・ズームを操作しても UI が応答し続ける

- [ ] **S03: Undo 差分化** `risk:medium` `depends:[S02]`
  > After this: 大規模 PDF で複数操作後の Undo が動作し、メモリ使用量が全体コピー方式より削減される

- [ ] **S04: 複数ページ操作と保守** `risk:medium` `depends:[S03]`
  > After this: 複数ページを選択して D&D で一括移動、および一括トリミングが動作する

## Boundary Map

Not provided.
