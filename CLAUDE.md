# CLAUDE.md — PageFolio AI 開発指示書

このファイルは Claude (AI) がこのプロジェクトを編集・拡張する際に参照する指示書です。

---

## プロジェクト概要

| 項目 | 内容 |
|------|------|
| アプリ名 | PageFolio |
| 言語 | Python 3.8+ |
| UI フレームワーク | Tkinter（標準ライブラリ） |
| PDF ライブラリ | pymupdf (fitz) |
| 画像ライブラリ | Pillow (PIL) |
| 対象 OS | Windows 11 |
| 現在バージョン | v0.9.5 |

---

## 開発について

本プロジェクトは **Claude Code**（Anthropic）を活用して開発されています。
`CLAUDE.md` による構造化された AI 開発指示書の運用、`開発履歴.md` による変更管理など、
AI との協調開発のユースケースとして公開しています。

---

## ファイル構成

```
PageFolio/
├── pagefolio.py               # アプリ本体（単一ファイル構成）
├── pagefolio.ico              # アプリアイコン
├── README.md                  # エンドユーザー向け使用概要
├── CLAUDE.md                  # 本ファイル（AI 向け開発指示書）
├── 開発履歴.md                # 機能追加・変更の履歴
└── LICENSE                    # MITライセンス
（実行時に自動生成）
└── pagefolio_settings.json    # ユーザー設定（テーマ・フォントサイズ）
```

---

## クラス構成

### `PDFEditorApp`
メインアプリケーションクラス。`tk.Tk` の root を受け取りすべての UI・ロジックを管理。

| メソッドグループ | 主なメソッド | 役割 |
|-----------------|-------------|------|
| UI 構築 | `_build_styles` `_build_ui` `_build_thumb_panel` `_build_preview` `_build_tools_scrollable` `_build_tools` | 画面レイアウト |
| ファイル操作 | `_open_file` `_open_multiple_pdfs` `_do_open_merged` `_open_pdf_path` `_save_file` `_save_as` `_quit` | PDF 読み書き・終了 |
| ページ操作 | `_rotate_selected` `_delete_selected` | ページ編集 |
| トリミング | `_toggle_crop_mode` `_crop_drag_start/move/end` `_crop_page` `_crop_reset` `_clear_crop_overlay` | ドラッグ選択トリミング |
| 挿入・結合 | `_insert_from_file` `_do_insert` `_merge_pdf` `_do_merge` | 複数ファイル対応 |
| 分割 | `_split_by_range` `_split_each_page` `_parse_page_ranges` `_check_split_overwrite` | ページ範囲分割・1ページ分割 |
| D&D 並び替え | `_dnd_start_ghost` `_dnd_move_ghost` `_dnd_drop` `_dnd_show_indicator` `_dnd_dest_index` `_dnd_destroy_ghost` `_dnd_clear_indicator` | サムネイル D&D（末尾対応済） |
| 表示更新 | `_refresh_all` `_build_thumbnails` `_add_thumb` `_show_preview` `_refresh_thumbs_selection_only` | 再描画 |
| ボタン状態制御 | `_update_doc_buttons_state` | ファイル開閉に応じたボタン活性/非活性 |
| ナビゲーション | `_prev_page` `_next_page` `_zoom` | プレビュー操作 |
| Undo / Redo | `_save_undo` `_undo` `_redo` `_restore_state` | 操作取り消し・やり直し（最大20回） |
| ページ拡大表示 | `_show_page_popup` `_single_click` | サムネイルダブルクリック拡大 |
| サムネイルキャッシュ | `_invalidate_thumb_cache` `_get_thumb_photo` | キャッシュ管理 |
| 設定 | `_open_settings` `_apply_settings` `_rebuild_ui` `_font` | テーマ・フォント設定・UI再構築 |

### `SettingsDialog`
`tk.Toplevel` サブクラス。テーマ（ダーク/ライト/システム）とフォントサイズ（8〜16pt）を設定するモーダルダイアログ。
`_apply(new_settings)` コールバックで `PDFEditorApp._apply_settings` に返す。

### `MergeOrderDialog`
`tk.Toplevel` サブクラス。複数 PDF の結合順を確認・並び替えするモーダルダイアログ。
ファイルを開く（複数選択）・挿入・結合の3か所から共通で利用。
`_do_merge(ordered_paths)` コールバックで結果を `PDFEditorApp` に返す。

---

## カラーテーマ

テーマは `THEMES` 辞書で定義。実行時は `C` 辞書経由で参照。

```python
THEMES = {
    "dark": {
        "BG_DARK": "#1a1a2e",  "BG_PANEL": "#16213e",  "BG_CARD": "#0f3460",
        "ACCENT": "#e94560",   "TEXT_MAIN": "#eaeaea",  "TEXT_SUB": "#a0a0b0",
        "SUCCESS": "#4ecca3",  "WARNING": "#ffd460",    "PREVIEW_BG": "#111122",
        ...
    },
    "light": {
        "BG_DARK": "#f0f0f5",  "BG_PANEL": "#e0e0ea",  "BG_CARD": "#d0d0dd",
        "ACCENT": "#d63050",   "TEXT_MAIN": "#1a1a2e",  "TEXT_SUB": "#555566",
        "SUCCESS": "#2a9d6a",  "WARNING": "#b8860b",    "PREVIEW_BG": "#c8c8d0",
        ...
    },
}
C = dict(THEMES["dark"])  # 実行時に _apply_theme() で更新
```

---

## コーディング規約

- **単一ファイル構成を維持する**: `pagefolio.py` 1 ファイルにすべて収める
- **メソッド名**: `_` プレフィックスで内部メソッドを示す
- **ボタンスタイル**:
  - 通常操作 → `"TButton"`
  - 主要アクション → `"Accent.TButton"`
  - 破壊的操作（削除・終了） → `"Danger.TButton"`
  - トリミングモード ON → `"CropOn.TButton"`
- **状態管理**:
  - `self.doc` — 現在開いている `fitz.Document`（未開時は `None`）
  - `self.current_page` — 0 始まりのページインデックス
  - `self.selected_pages` — `set` で複数選択を管理
  - `self._undo_stack` / `self._redo_stack` — Undo/Redo スタック
  - `self.thumb_cache` — サムネイルキャッシュ辞書
  - `self._doc_buttons` — ファイル依存ボタンのリスト（doc未開時に disabled）
  - `self._pending_click` — ダブルクリック競合防止用の遅延クリックID
  - `self.settings` — 設定辞書（テーマ、フォントサイズ）
  - `self.font_size` — 現在のベースフォントサイズ（8〜16）
- **再描画**: ページ変更後は必ず `self._refresh_all()` を呼ぶ
- **ステータス表示**: 操作完了後は `self._set_status(msg)` でヘッダーに表示
- **ファイル操作前の確認**: `self._check_doc()` で `self.doc` の存在を確認する
- **トリミング安全処理**: CropBox は必ず MediaBox 内にクランプしてから `set_cropbox` を呼ぶ
- **テーマ色の参照**: グローバル定数ではなく `C["BG_DARK"]` 等のテーマ辞書を使う
- **フォントサイズ**: ハードコードせず `self._font(delta)` ヘルパーを使う（ベース + delta）
- **設定保存**: `pagefolio_settings.json` に JSON で永続化（`_save_settings()`）

---

## Language

タスクリスト（TodoWrite）の内容を含め、すべての返答を日本語で行うこと。

---

## 言語ルール

本プロジェクトでは、以下の出力を**原則日本語**で記述すること。

| 対象 | 例 |
|------|-----|
| コミットメッセージ | `ページ回転機能のバグを修正` |
| ブランチ説明・PR タイトル / 本文 | `サムネイルD&Dの末尾ドロップ対応` |
| GitHub Issue のタイトル / コメント | `トリミング後にプレビューが更新されない` |
| コードレビューのフィードバック | `この条件分岐は不要では？` |
| `開発履歴.md` の記載 | 既存ルール通り |
| セッション終了時の申し送り | 既存ルール通り |
| ユーザーへの応答・説明 | 会話はすべて日本語 |

**例外（英語のまま）**:
- ソースコード中の変数名・関数名・クラス名
- ライブラリ名・コマンド名（`pymupdf`, `git push` など）
- エラーメッセージの引用（原文ママ）

---

## 既知の制限・注意事項

- トリミングは **現在表示中のページのみ** 対象（複数ページ一括トリミング未対応）
- D&D によるページ移動は **1ページずつ**（複数選択ページの一括移動未対応）
- 暗号化・パスワード保護 PDF は開けない場合がある
- `set_cropbox` によるトリミングはメタデータ上の cropbox 変更であり、PDF の物理的なページサイズは変わらない
- サムネイルは `fitz.Matrix(0.22, 0.22)` のスケールで生成（変更時はパフォーマンスに注意）
- プレビューは `self.zoom * 1.5` のスケールで生成
- 右ペインはスクロール可能な Canvas 構成（`_build_tools_scrollable` で実装）

---

## 今後の追加予定機能（候補）

- [ ] 複数ページの一括トリミング
- [ ] 複数ページの D&D 一括移動
- [ ] ページの回転状態をプレビューに即時反映
- [ ] PDF のパスワード解除対応
- [ ] 印刷機能
- [x] ページ範囲指定での分割保存
- [x] PyInstaller による exe 化・配布対応

---

## 変更時のチェックリスト

- [ ] `python3 -c "import ast; ast.parse(open('pagefolio.py').read())"` で構文確認
- [ ] `開発履歴.md` に変更内容を追記
- [ ] バージョン番号を更新（本ファイル・開発履歴.md）

---

## セッション終了時のルール

作業が完了したら、依頼されなくても必ず日本語で以下の形式で申し送りを出力すること。
この出力はclaude.aiに貼り付けてNotionを更新するために使用する。

### 変更内容サマリー

**修正対象**: （バグ番号・機能名など）

| ファイル | 変更内容 |
|----------|----------|
| ファイルパス | 変更内容の概要 |

### 修正内容の詳細

（バグ修正なら症状・原因・対応内容を記載）

### 次セッションへの申し送り

#### 未実施（動作確認・テスト）
- 確認が必要な事項を箇条書き

#### 注意点・潜在リスク
- 動作上の注意点や将来の改善候補

#### 実行推奨コマンド（必要な場合）
```
pytest tests/ など
```
