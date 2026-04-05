# Requirements

## Active

### R001: PDF ファイル読み込み・保存
PDF ファイルを開き、編集後に上書き保存・名前を付けて保存ができること。
- **Status**: validated
- **Validation**: v1.0.0 で実装済み。`_open_file`, `_save_file`, `_save_as` メソッド
- **Owner**: core

### R002: ページサムネイル表示
開いた PDF の全ページをサムネイル一覧で表示し、クリックで選択できること。
- **Status**: validated
- **Validation**: v1.0.0 で実装済み。`_build_thumbnails`, `_add_thumb`
- **Owner**: ui

### R003: プレビュー表示
選択中のページを拡大・縮小可能なプレビューで表示すること。
- **Status**: validated
- **Validation**: v1.0.0 で実装済み。`_show_preview`, `_zoom`
- **Owner**: ui

### R004: ページ回転
選択したページを 90°/180°/270° で回転できること（複数ページ対応）。
- **Status**: validated
- **Validation**: v1.0.0 で実装済み。`_rotate_selected`
- **Owner**: core

### R005: ページ削除
選択したページを削除できること（複数ページ対応）。
- **Status**: validated
- **Validation**: v1.0.0 で実装済み。`_delete_selected`
- **Owner**: core

### R006: ドラッグ選択トリミング
プレビュー上でマウスドラッグして範囲を指定し、トリミングできること。
- **Status**: validated
- **Validation**: v1.2.0 で実装済み。`_toggle_crop_mode`, `_crop_page`
- **Owner**: core

### R007: ページ挿入
別の PDF ファイルからページを挿入できること（複数ファイル対応）。
- **Status**: validated
- **Validation**: v1.1.0 で実装済み。`_insert_from_file`, `_do_insert`
- **Owner**: core

### R008: PDF 結合
複数の PDF ファイルを結合できること。結合順の並び替えダイアログあり。
- **Status**: validated
- **Validation**: v1.1.0 で実装済み。`_merge_pdf`, `MergeOrderDialog`
- **Owner**: core

### R009: ページ分割保存
ページ範囲指定または 1ページずつの分割保存ができること。
- **Status**: validated
- **Validation**: v0.8.0 で実装済み。`_split_by_range`, `_split_each_page`
- **Owner**: core

### R010: D&D ページ並び替え
サムネイルをドラッグ＆ドロップでページ順を変更できること。
- **Status**: validated
- **Validation**: v1.3.0 で実装済み。`_dnd_start_ghost`, `_dnd_drop` 等
- **Owner**: ui

### R011: Undo/Redo
操作の取り消し・やり直しができること（最大20回）。
- **Status**: validated
- **Validation**: v1.4.0 で実装済み。`_save_undo`, `_undo`, `_redo`
- **Owner**: core

### R012: ダーク/ライトテーマ
ダーク・ライト・システムの3テーマを切り替えられること。設定は永続化。
- **Status**: validated
- **Validation**: v0.8.0 で実装済み。`SettingsDialog`, `THEMES` 辞書
- **Owner**: ui

### R013: 複数 PDF 同時オープン
複数ファイルを選択して結合し、1つの文書として開けること。
- **Status**: validated
- **Validation**: v0.7.0 で実装済み。`_open_multiple_pdfs`, `_do_open_merged`
- **Owner**: core

### R014: 複数ページ一括トリミング
選択した複数ページに同じトリミング範囲を一括適用できること。
- **Status**: active
- **Owner**: core
- **Notes**: CLAUDE.md の今後の追加予定機能に記載

### R015: 複数ページ D&D 一括移動
複数選択したページをまとめてドラッグ移動できること。
- **Status**: active
- **Owner**: ui
- **Notes**: CLAUDE.md の今後の追加予定機能に記載

### R016: 印刷機能
開いた PDF を印刷できること。
- **Status**: active
- **Owner**: core
- **Notes**: CLAUDE.md の今後の追加予定機能に記載

### R017: パスワード保護 PDF 対応
パスワード保護された PDF のパスワード入力・解除ができること。
- **Status**: active
- **Owner**: core
- **Notes**: CLAUDE.md の今後の追加予定機能に記載

## Deferred

（なし）

## Out of Scope

（なし）
