# CLAUDE.md — PDF Editor AI 開発指示書

このファイルは Claude (AI) がこのプロジェクトを編集・拡張する際に参照する指示書です。

---

## プロジェクト概要

| 項目 | 内容 |
|------|------|
| アプリ名 | PDF Editor |
| 言語 | Python 3.8+ |
| UI フレームワーク | Tkinter（標準ライブラリ） |
| PDF ライブラリ | pymupdf (fitz) |
| 画像ライブラリ | Pillow (PIL) |
| 対象 OS | Windows 11 |
| 現在バージョン | v1.4.0 |

---

## ファイル構成

```
PDF_Editor.zip
├── pdf_editor.py      # アプリ本体（単一ファイル構成）
├── PDF_Editor起動.bat # 起動用バッチ
├── README.md          # エンドユーザー向け使用概要
├── CLAUDE.md          # 本ファイル（AI 向け開発指示書）
└── 開発履歴.md        # 機能追加・変更の履歴
```

---

## クラス構成

### `PDFEditorApp`
メインアプリケーションクラス。`tk.Tk` の root を受け取りすべての UI・ロジックを管理。

| メソッドグループ | 主なメソッド | 役割 |
|-----------------|-------------|------|
| UI 構築 | `_build_styles` `_build_ui` `_build_thumb_panel` `_build_preview` `_build_tools` | 画面レイアウト |
| ファイル操作 | `_open_file` `_save_file` `_save_as` `_quit` | PDF 読み書き・終了 |
| ページ操作 | `_rotate_selected` `_delete_selected` `_move_page` | ページ編集 |
| トリミング | `_toggle_crop_mode` `_crop_drag_start/move/end` `_crop_page` `_crop_reset` | ドラッグ選択トリミング |
| 挿入・結合 | `_insert_from_file` `_merge_pdf` `_do_merge` | 複数ファイル対応 |
| D&D 並び替え | `_dnd_start_ghost` `_dnd_move_ghost` `_dnd_drop` `_dnd_show_indicator` | サムネイル D&D |
| 表示更新 | `_refresh_all` `_build_thumbnails` `_add_thumb` `_show_preview` | 再描画 |
| ナビゲーション | `_prev_page` `_next_page` `_zoom` | プレビュー操作 |

### `MergeOrderDialog`
`tk.Toplevel` サブクラス。複数 PDF の結合順を確認・並び替えするモーダルダイアログ。
`_do_merge(ordered_paths)` コールバックで結果を `PDFEditorApp` に返す。

---

## カラーテーマ定数

```python
BG_DARK   = "#1a1a2e"   # メイン背景
BG_PANEL  = "#16213e"   # パネル背景
BG_CARD   = "#0f3460"   # カード・ボタン背景
ACCENT    = "#e94560"   # アクセント（赤）
ACCENT2   = "#533483"   # サブアクセント（紫）
TEXT_MAIN = "#eaeaea"   # メインテキスト
TEXT_SUB  = "#a0a0b0"   # サブテキスト
SUCCESS   = "#4ecca3"   # 成功・情報（緑）
WARNING   = "#ffd460"   # セクションタイトル（黄）
```

---

## コーディング規約

- **単一ファイル構成を維持する**: `pdf_editor.py` 1 ファイルにすべて収める
- **メソッド名**: `_` プレフィックスで内部メソッドを示す
- **ボタンスタイル**:
  - 通常操作 → `"TButton"`
  - 主要アクション → `"Accent.TButton"`
  - 破壊的操作（削除・終了） → `"Danger.TButton"`
- **状態管理**:
  - `self.doc` — 現在開いている `fitz.Document`（未開時は `None`）
  - `self.current_page` — 0 始まりのページインデックス
  - `self.selected_pages` — `set` で複数選択を管理
- **再描画**: ページ変更後は必ず `self._refresh_all()` を呼ぶ
- **ステータス表示**: 操作完了後は `self._set_status(msg)` でヘッダーに表示
- **ファイル操作前の確認**: `self._check_doc()` で `self.doc` の存在を確認する

---

## 既知の制限・注意事項

- トリミングは **現在表示中のページのみ** 対象（複数ページ一括トリミング未対応）
- D&D によるページ移動は **1ページずつ**（複数選択ページの一括移動未対応）
- 暗号化・パスワード保護 PDF は開けない場合がある
- `set_cropbox` によるトリミングはメタデータ上の cropbox 変更であり、PDF の物理的なページサイズは変わらない
- サムネイルは `fitz.Matrix(0.22, 0.22)` のスケールで生成（変更時はパフォーマンスに注意）
- プレビューは `self.zoom * 1.5` のスケールで生成

---

## 今後の追加予定機能（候補）

- [ ] 複数ページの一括トリミング
- [ ] 複数ページの D&D 一括移動
- [ ] ページの回転状態をプレビューに即時反映
- [ ] PDF のパスワード解除対応
- [ ] 印刷機能
- [ ] アンドゥ／リドゥ（Ctrl+Z / Ctrl+Y）
- [ ] ページ範囲指定での分割保存

---

## 変更時のチェックリスト

- [ ] `python3 -c "import ast; ast.parse(open('pdf_editor.py').read())"` で構文確認
- [ ] `開発履歴.md` に変更内容を追記
- [ ] バージョン番号を更新（本ファイル・開発履歴.md）
- [ ] ZIP を再作成して配布（`README.md` `pdf_editor.py` `PDF_Editor起動.bat` `CLAUDE.md` `開発履歴.md`）
