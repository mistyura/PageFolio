# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
# https://github.com/mistyura/PageFolio
"""言語辞書定義 — LANG（日本語 / 英語）"""

LANG = {
    "ja": {
        # ヘッダー / ステータス
        "status_initial": "ファイルを開いてください",
        # サムネイルパネル
        "panel_pages": "ページ一覧",
        "dnd_hint": "D&D で並替",
        "select_all": "全選択",
        "deselect": "解除",
        # プレビューツールバー
        "btn_prev": "◀",
        "btn_next": "▶",
        "btn_zoom_in": "＋",
        "btn_zoom_out": "－",
        # ツールセクション見出し
        "sec_settings": "⚙ 設定",
        "sec_file": "📂 ファイル",
        "sec_undo": "↩ 元に戻す / やり直す",
        "sec_page": "📄 ページ操作（選択ページ）",
        "sec_crop": "✂ トリミング（現在ページ）",
        "sec_insert": "📎 挿入・結合",
        "sec_plugin": "🔌 プラグイン",
        # 設定セクションボタン
        "btn_settings": "⚙ テーマ・フォント設定…",
        "btn_about": "ℹ About",
        "btn_lang": "🌐 English",
        # ファイルセクションボタン
        "btn_open": "ファイルを開く (Ctrl+O)",
        "btn_save": "上書き保存 (Ctrl+S)",
        "btn_save_as": "名前を付けて保存 (Ctrl+Shift+S)",
        "btn_close_file": "📕 ファイルを閉じる",
        "btn_quit": "✕ 終了",
        # Undo/Redo
        "btn_undo": "↩ Ctrl+Z",
        "btn_redo": "↪ Ctrl+Y",
        # ページ操作
        "lbl_rotate": "回転:",
        "btn_rot_left": "↺ 左90°",
        "btn_rot_right": "↻ 右90°",
        "btn_rot_180": "↕ 180°",
        "btn_delete": "🗑 選択ページを削除 (Del)",
        "btn_duplicate": "📋 現在ページを複製",
        "status_duplicated": "p.{page} を複製して直後に挿入しました",
        # トリミング
        "crop_mode_off": "✂ 範囲選択モード OFF",
        "crop_mode_on": "🔴 範囲選択モード ON  (クリックで OFF)",
        "crop_hint": "プレビュー上でドラッグして範囲を指定",
        "crop_no_sel": "範囲未選択",
        "btn_crop": "✔ 選択範囲でトリミング",
        "btn_crop_reset": "✕ 選択範囲をリセット",
        # 挿入・結合
        "btn_insert_head": "先頭に挿入",
        "btn_insert_tail": "末尾に挿入",
        "btn_insert_pos": "指定位置に挿入…",
        "btn_merge": "PDFを末尾に結合",
        # ページ結合・リサイズ
        "sec_merge_resize": "📐 ページ結合・リサイズ",
        "btn_merge_resize": "🧩 選択ページを結合してリサイズ…",
        "info_merge_resize_min": "結合・リサイズには2ページ以上の選択が必要です",
        "mr_dialog_title": "ページ結合・リサイズ",
        "mr_dialog_heading": "ページ結合・リサイズ",
        "mr_dialog_hint": (
            "選択中の{count}ページを1枚に結合し、合計サイズの新しいページを作成します。\n"
            "例: 2枚のA4を横並びで結合 → 1枚のA3"
        ),
        "mr_direction": "配置方向:",
        "mr_horizontal": "横並び（左→右）",
        "mr_vertical": "縦並び（上→下）",
        "mr_order_label": "結合順（上から順）:",
        "mr_size_preview": "出力サイズ: {w}×{h} pt",
        "mr_apply": "✔ 結合・リサイズ実行",
        "mr_cancel": "キャンセル",
        "status_merge_resize": "{count}ページを結合・リサイズしました ({w}×{h} pt)",
        # 分割
        "sec_split": "✂ 分割",
        "btn_split_range": "📄 範囲を指定して分割…",
        "btn_split_each": "📑 1ページずつ分割…",
        "dlg_split_range_title": "ページ範囲を指定して分割",
        "dlg_split_range_msg": (
            "分割するページ範囲を入力してください。\n\n例:\n"
            "  1-3      → 1〜3ページ目を1ファイルに\n"
            "  1-3, 5-8 → 2ファイルに分割\n"
            "  4        → 4ページ目だけ抽出\n\n"
            "ページ範囲 (1〜{n}):"
        ),
        "dlg_split_save_dir": "分割ファイルの保存先フォルダを選択",
        "status_split_range": "{count}個のPDFに分割しました → {folder}",
        "status_split_each": "{count}ページを個別PDFに分割しました → {folder}",
        "err_split_range": (
            "ページ範囲の入力が正しくありません。\n\n"
            "正しい形式: 1-3, 5-8  または  4\n"
            "ページ番号は 1〜{n} の範囲で指定してください。"
        ),
        "err_split_no_range": "ページ範囲を入力してください。",
        "split_overwrite_title": "上書き確認",
        "split_overwrite_msg": (
            "保存先に同名ファイルが存在します:\n\n{files}\n\n上書きしますか？"
        ),
        # 縮小保存
        "sec_compress": "🗜 縮小保存",
        "btn_save_compressed": "🗜 縮小して保存…",
        "status_compressed": "縮小保存しました: {name}",
        "compress_split_confirm_title": "分割時の縮小保存",
        "compress_split_confirm_msg": (
            "分割したPDFを縮小最適化して保存しますか？\n"
            "（garbage収集 + 圧縮を実行します）\n\n"
            "「はい」を選ぶとファイルサイズが小さくなりますが\n"
            "処理時間が増加する場合があります。"
        ),
        # プラグイン
        "btn_plugin_mgr": "🔌 プラグイン管理…",
        # 閲覧/編集モード
        "mode_view_label": "👁 閲覧モード",
        "mode_edit_label": "📝 編集モード",
        # プレビュー空状態
        "preview_empty1": "📂 ファイルをドラッグ＆ドロップ",
        "preview_empty2": "または Ctrl+O / メニューから「ファイルを開く」",
        # 共通ボタン
        "btn_close": "✕ 閉じる",
        # ステータスメッセージ
        "undo_empty": "元に戻す履歴がありません",
        "redo_empty": "やり直す履歴がありません",
        "undo_done": "元に戻しました",
        "redo_done": "やり直しました",
        "status_settings": "設定を変更しました",
        # ファイル操作
        "filetypes_pdf": "PDFファイル",
        "filetypes_all": "すべて",
        "filetypes_supported": "サポートファイル",
        "filetypes_image": "画像ファイル",
        "status_opened_image": "開きました（画像→PDF変換）: {name}  (1ページ)",
        "status_image_save_as": (
            "画像ファイルは PDF で保存します — 保存先を選択してください"
        ),
        "info_open_first": "先にファイルを開いてください",
        "save_confirm_title": "上書き保存の確認",
        "save_confirm_msg": (
            "以下のファイルを上書き保存します。\n\n{name}\n\n"
            "元のファイルは上書きされます。よろしいですか？"
        ),
        "status_saved": "保存しました: {name}",
        "err_save_title": "保存エラー",
        "err_save_msg": "保存に失敗しました:\n{e}",
        "status_opened": "開きました: {name}  ({n}ページ)",
        "close_confirm": ("現在のファイルを閉じますか？\n（未保存の変更は失われます）"),
        "status_closed": "ファイルを閉じました",
        "status_merged_open": (
            "{count}ファイルを結合して開きました ({total}ページ): {names}"
        ),
        # ページ操作ステータス
        "status_rotated": "{count}ページを{deg}°回転しました",
        "info_no_page_sel": "削除するページを選択してください",
        "warn_del_all_title": "警告",
        "warn_del_all": (
            "すべてのページを削除することはできません。\n"
            "最低1ページは残す必要があります。"
        ),
        "confirm_del": "{count}ページを削除しますか？",
        "status_deleted": "{count}ページを削除しました",
        # トリミング
        "info_crop_drag": "プレビュー上でドラッグしてトリミング範囲を選択してください",
        "status_cropped": "ページ{page}をトリミングしました",
        "status_bulk_cropped": "選択{count}ページをトリミングしました",
        "confirm_bulk_crop": "選択中の{count}ページすべてにトリミングを適用しますか？",
        "err_crop_small": "範囲が小さすぎます。もう一度ドラッグしてください",
        "err_crop_title": "トリミングエラー",
        "err_crop_msg": (
            "CropBoxの設定に失敗しました。\n範囲を調整して再度お試しください。\n\n{e}"
        ),
        # 挿入・結合ステータス
        "dlg_insert_title": "挿入するファイルを選択（PDF/画像、複数可）",
        "dlg_insert_pos_title": "挿入位置",
        "dlg_insert_pos_msg": (
            "何ページ目の後ろに挿入しますか？\n"
            "(0 = 先頭、1〜{n} = そのページの後ろ)\n\n"
            "例: 3 → 3ページ目の後ろに挿入"
        ),
        "status_insert_head": "先頭",
        "status_insert_tail": "末尾",
        "status_insert_pos": "{pos}ページ目の後ろ",
        "status_inserted": "{count}ファイル（計{total}ページ）を{where}に挿入しました",
        "dlg_merge_title": "結合するPDFを選択（複数可・選択順に結合）",
        "status_merged": "{count}ファイル（計{total}ページ）を末尾に結合しました",
        # 終了
        "quit_confirm": "アプリを終了しますか？\n（未保存の変更は失われます）",
        # doc 確認
        "info_no_doc": "先にPDFファイルを開いてください",
        # D&D ステータス
        "status_dnd_moved": "p.{src} → p.{dest} に移動しました",
        "status_bulk_moved": "{count}ページを一括移動しました",
        # D&D ファイルオープン
        "dnd_drop_hint": "ここに PDF / 画像をドロップ",
        "dnd_pdf_only": "PDF または画像ファイル (PNG/JPG/BMP/TIFF) のみ対応しています",
        "dnd_replace_confirm": (
            "現在のファイルを閉じて新しいファイルを開きますか？\n"
            "（未保存の変更は失われます）"
        ),
        # About ダイアログ
        "about_title": "PageFolio について",
        "about_subtitle": "PDF Page Organizer",
        "about_ok": "OK",
        # 設定ダイアログ
        "settings_title": "設定",
        "settings_heading": "⚙ 設定",
        "settings_theme": "テーマ:",
        "settings_theme_dark": "ダーク",
        "settings_theme_light": "ライト",
        "settings_theme_system": "システム設定",
        "settings_font": "フォントサイズ:",
        "settings_font_hint": "pt  (8〜16)",
        "settings_preview_text": "サンプルテキスト  Sample Text  123",
        "settings_apply": "✔ 適用",
        "settings_cancel": "キャンセル",
        # 結合順ダイアログ
        "merge_title": "結合順の確認・変更",
        "merge_heading": "結合順の確認・並び替え",
        "merge_hint": (
            "ファイルを選択して ▲▼ で順番を変更できます\n"
            "確定すると現在のPDFの末尾に順番通り結合されます"
        ),
        "merge_up": "▲ 上へ",
        "merge_down": "▼ 下へ",
        "merge_remove": "✕ 削除",
        "merge_info": "合計 {count} ファイル  /  {total} ページ",
        "merge_confirm": "✔ この順番で結合",
        "merge_cancel": "キャンセル",
        "merge_no_files": "ファイルがありません",
        # プラグインダイアログ
        "plugin_title": "プラグイン管理",
        "plugin_heading": "🔌 プラグイン管理",
        "plugin_dir_label": "プラグインフォルダ: {path}",
        "plugin_empty": (
            "プラグインが見つかりません\n\n"
            "「{dir}」フォルダに .py ファイルを\n配置してください"
        ),
        "plugin_author": "作者: {author}",
        "plugin_rescan": "🔄 再検出",
        "plugin_open_folder": "📁 フォルダを開く",
        "plugin_close": "✔ 閉じる",
        # OCR（LM Studio）
        "sec_ocr": "🔍 OCR（LM Studio）",
        "btn_ocr_current": "🔠 現在ページをテキスト抽出",
        "btn_ocr_selected": "📚 選択ページを一括抽出",
        "ocr_prompt_label": "プロンプト:",
        "ocr_preset_text": "通常テキスト",
        "ocr_preset_table": "表形式",
        "ocr_preset_markdown": "Markdown",
        "ocr_dialog_title": "OCR — LM Studio",
        "ocr_dialog_heading": "🔍 OCR テキスト抽出",
        "ocr_progress_init": "準備中…",
        "ocr_progress": "{cur}/{total} ページ処理中… (p.{page})",
        "ocr_progress_render": "画像変換中… ({cur}/{total})",
        "ocr_progress_ocr": "読み取り完了 ({done}/{total}) — p.{page}",
        "ocr_cancelling": "キャンセル中…",
        "ocr_cancelled": "キャンセルしました",
        "ocr_complete": "完了: {count}/{total} ページ成功",
        "ocr_failed": "失敗しました",
        "ocr_page_separator": "--- Page {page} ---",
        "ocr_page_error": "[エラー] {error}",
        "ocr_text_skip_notice": "p.{page}: テキスト埋め込み済みのためスキップしました",
        "ocr_progress_skip": "埋め込みテキスト抽出 ({done}/{total}) — p.{page}",
        "ocr_copy": "📋 クリップボードにコピー",
        "ocr_copied": "クリップボードにコピーしました",
        "ocr_save": "💾 テキストファイルに保存…",
        "ocr_save_dialog_title": "OCR結果の保存先",
        "ocr_saved": "保存しました: {path}",
        "ocr_cancel": "✕ キャンセル",
        "ocr_close_during_run": (
            "OCR 実行中です。\nウィンドウを閉じると処理は中断されます。\n閉じますか？"
        ),
        "ocr_err_connection": (
            "LM Studio に接続できませんでした。\n"
            "URL: {url}\n\n"
            "LM Studio が起動していること、URL が正しいことを\n"
            "確認してください。\n\n詳細: {error}"
        ),
        "ocr_err_timeout": (
            "OCR がタイムアウトしました ({timeout} 秒)。\n"
            "モデルが大きい場合は設定でタイムアウトを延ばしてください。\n"
            "\n詳細: {error}"
        ),
        "ocr_provider_unsupported": (
            "未対応の OCR プロバイダが設定されています: {name}\n"
            "設定を確認してください。"
        ),
        # Phase 5: Claude Provider / セキュリティ UI 文言（D-06/D-07/D-12/D-15/D-17）
        "ocr_api_key_missing": (
            "APIキーが設定されていません（{env_var}）。"
            "環境変数を設定するか、入力欄にキーを入力してください。"
        ),
        "ocr_session_key_label": "APIキー（このセッションのみ・保存されません）:",
        "ocr_cost_confirm_title": "クラウド送信の確認",
        "ocr_cost_confirm_msg": (
            "送信先: {host}\n"
            "対象: {count} ページ（概算コスト: {cost}）\n\n"
            "ページ画像が外部 API に送信されます。\n"
            "従量課金が発生します。\n"
            "実行しますか？"
        ),
        "ocr_waiting_retry": "p.{page}: レート制限のため待機中（リトライ {n}/{max}）",
        "ocr_provider_label": "OCR プロバイダ:",
        "ocr_provider_name_claude": "Claude (Anthropic)",
        "ocr_provider_name_lmstudio": "LM Studio",
        # Phase 6: Gemini Provider 文言（D-06/D-12）
        "ocr_provider_name_gemini": "Gemini (Google AI)",
        "ocr_api_key_missing_gemini": (
            "Gemini APIキーが設定されていません。"
            "環境変数 GEMINI_API_KEY（または GOOGLE_API_KEY）を設定するか、"
            "入力欄にキーを入力してください。"
        ),
        "ocr_scale_tradeoff_hint": ("低=速い/安い・高=精度。低スペック PC は 1.5 推奨"),
        "ocr_effort_label": "推論強度 (effort):",
        "ocr_provider_off_hint": "OCR は無効です。設定でプロバイダを選択してください。",
        "ocr_model_refresh": "モデル更新",
        # LM Studio 設定
        "settings_lm_studio_section": "🔍 LM Studio (OCR)",
        "settings_lm_url": "URL:",
        "settings_lm_model": "モデル:",
        "settings_lm_model_hint": (
            "（空欄: LM Studio で読み込み済みのモデルを自動使用）"
        ),
        "settings_lm_fetch_models": "📥 モデル一覧を取得",
        "settings_lm_test": "🔌 接続テスト",
        "settings_lm_test_ok": "接続OK ({count} モデル利用可能)",
        "settings_lm_test_fail": "接続失敗: {error}",
        "settings_lm_testing": "⏳ 接続中… ({url})",
        "settings_ocr_scale": "OCR 解像度倍率:",
        "settings_ocr_timeout": "OCR タイムアウト (秒):",
        "settings_ocr_concurrency": "OCR 並列度:",
        "settings_ocr_concurrency_hint": (
            "(1〜8 / 推奨2。LM Studio が並列受付に対応しない場合は1相当)"
        ),
        "settings_open_llm_config": "🔍 LLM 設定…",
        # LLM 設定ダイアログ（OCR と設定で共有）
        "llm_config_title": "LLM 設定",
        "llm_config_heading": "🔍 LLM 設定 (LM Studio)",
        "llm_config_apply": "✓ 適用",
        "llm_config_cancel": "✕ キャンセル",
        # OCR ダイアログ
        "ocr_server_label": "サーバ:",
        "ocr_model_label": "モデル:",
        "ocr_run": "▶ 読み取り実行",
        "ocr_fetch_models": "📥 モデル一覧取得",
        "ocr_open_llm_config": "⚙ LLM 設定…",
        "ocr_clear": "🧹 クリア",
        "ocr_models_fetched": "{count} モデルを取得しました",
        "ocr_models_fetch_fail": "モデル取得失敗: {error}",
        "ocr_models_fetching": "⏳ モデル一覧を取得中… ({url})",
        "ocr_run_first": "「読み取り実行」を押すと開始します",
        "ocr_params_label": "詳細設定:",
        "ocr_scale_short": "解像度:",
        "ocr_timeout_short": "タイムアウト:",
        "ocr_max_tokens_short": "最大トークン:",
        "ocr_max_tokens_hint": "(-1: モデル最大値を使用 / 上限 262144)",
        "ocr_temperature_short": "温度:",
        "ocr_temperature_hint": "(0.0〜0.2推奨)",
        "ocr_params_hint": (
            "ハルシネーション抑制: 温度↓・解像度↑。"
            "推奨モデル: Qwen2-VL-7B / MiniCPM-V / InternVL2 8B 以上"
        ),
        # 共通エラー
        "err_title": "エラー",
        "info_title": "情報",
        "warn_title": "警告",
        "confirm_title": "確認",
    },
    "en": {
        # Header / status
        "status_initial": "Open a file to get started",
        # Thumbnail panel
        "panel_pages": "Pages",
        "dnd_hint": "Drag to reorder",
        "select_all": "Select All",
        "deselect": "Deselect",
        # Preview toolbar
        "btn_prev": "◀",
        "btn_next": "▶",
        "btn_zoom_in": "＋",
        "btn_zoom_out": "－",
        # Tool section titles
        "sec_settings": "⚙ Settings",
        "sec_file": "📂 File",
        "sec_undo": "↩ Undo / Redo",
        "sec_page": "📄 Page Operations",
        "sec_crop": "✂ Crop (Current Page)",
        "sec_insert": "📎 Insert / Merge",
        "sec_plugin": "🔌 Plugins",
        # Settings section buttons
        "btn_settings": "⚙ Theme & Font…",
        "btn_about": "ℹ About",
        "btn_lang": "🌐 日本語",
        # File section buttons
        "btn_open": "Open File (Ctrl+O)",
        "btn_save": "Save (Ctrl+S)",
        "btn_save_as": "Save As (Ctrl+Shift+S)",
        "btn_close_file": "📕 Close File",
        "btn_quit": "✕ Quit",
        # Undo/Redo
        "btn_undo": "↩ Ctrl+Z",
        "btn_redo": "↪ Ctrl+Y",
        # Page operations
        "lbl_rotate": "Rotate:",
        "btn_rot_left": "↺ Left 90°",
        "btn_rot_right": "↻ Right 90°",
        "btn_rot_180": "↕ 180°",
        "btn_delete": "🗑 Delete Selected (Del)",
        "btn_duplicate": "📋 Duplicate Current Page",
        "status_duplicated": "Duplicated p.{page} and inserted after it",
        # Crop
        "crop_mode_off": "✂ Crop Mode OFF",
        "crop_mode_on": "🔴 Crop Mode ON  (click to OFF)",
        "crop_hint": "Drag on preview to select crop area",
        "crop_no_sel": "No selection",
        "btn_crop": "✔ Crop to Selection",
        "btn_crop_reset": "✕ Reset Selection",
        # Insert/Merge
        "btn_insert_head": "Insert at Beginning",
        "btn_insert_tail": "Insert at End",
        "btn_insert_pos": "Insert at Position…",
        "btn_merge": "Merge PDF to End",
        # Page merge & resize
        "sec_merge_resize": "📐 Merge & Resize",
        "btn_merge_resize": "🧩 Merge Selected Pages & Resize…",
        "info_merge_resize_min": "Select 2 or more pages to merge & resize",
        "mr_dialog_title": "Merge & Resize Pages",
        "mr_dialog_heading": "Merge & Resize Pages",
        "mr_dialog_hint": (
            "Combine {count} selected pages into one page sized to fit them all.\n"
            "Ex: 2× A4 side by side → 1× A3"
        ),
        "mr_direction": "Direction:",
        "mr_horizontal": "Horizontal (left→right)",
        "mr_vertical": "Vertical (top→bottom)",
        "mr_order_label": "Merge order (top to bottom):",
        "mr_size_preview": "Output size: {w}×{h} pt",
        "mr_apply": "✔ Apply Merge & Resize",
        "mr_cancel": "Cancel",
        "status_merge_resize": "Merged {count} pages → {w}×{h} pt",
        # Split
        "sec_split": "✂ Split",
        "btn_split_range": "📄 Split by Range…",
        "btn_split_each": "📑 Split Each Page…",
        "dlg_split_range_title": "Split by Page Range",
        "dlg_split_range_msg": (
            "Enter page ranges to split.\n\nExamples:\n"
            "  1-3      → pages 1–3 as one file\n"
            "  1-3, 5-8 → two files\n"
            "  4        → extract page 4 only\n\n"
            "Page range (1–{n}):"
        ),
        "dlg_split_save_dir": "Select folder for split files",
        "status_split_range": "Split into {count} PDF(s) → {folder}",
        "status_split_each": "Split {count} pages into individual PDFs → {folder}",
        "err_split_range": (
            "Invalid page range.\n\n"
            "Correct format: 1-3, 5-8  or  4\n"
            "Page numbers must be between 1 and {n}."
        ),
        "err_split_no_range": "Please enter a page range.",
        "split_overwrite_title": "Confirm Overwrite",
        "split_overwrite_msg": (
            "The following file(s) already exist:\n\n{files}\n\nOverwrite?"
        ),
        # Compress save
        "sec_compress": "🗜 Compress & Save",
        "btn_save_compressed": "🗜 Save Compressed…",
        "status_compressed": "Saved compressed: {name}",
        "compress_split_confirm_title": "Compress Split Files?",
        "compress_split_confirm_msg": (
            "Save split PDFs with size optimization?\n"
            "(Runs garbage collection + compression)\n\n"
            "Choosing 'Yes' reduces file size but may\n"
            "increase processing time."
        ),
        # Plugin
        "btn_plugin_mgr": "🔌 Manage Plugins…",
        # View/Edit mode
        "mode_view_label": "👁 View Mode",
        "mode_edit_label": "📝 Edit Mode",
        # Preview empty state
        "preview_empty1": "📂 Drag & Drop a file here",
        "preview_empty2": 'or Ctrl+O / use "Open File" from the menu',
        # Common button
        "btn_close": "✕ Close",
        # Status messages
        "undo_empty": "Nothing to undo",
        "redo_empty": "Nothing to redo",
        "undo_done": "Undone",
        "redo_done": "Redone",
        "status_settings": "Settings updated",
        # File operations
        "filetypes_pdf": "PDF files",
        "filetypes_all": "All files",
        "filetypes_supported": "Supported Files",
        "filetypes_image": "Image Files",
        "status_opened_image": "Opened (image→PDF): {name}  (1 page)",
        "status_image_save_as": (
            "Image file will be saved as PDF — choose save location"
        ),
        "info_open_first": "Please open a file first",
        "save_confirm_title": "Confirm Overwrite",
        "save_confirm_msg": (
            "Overwrite the following file?\n\n{name}\n\n"
            "This cannot be undone. Continue?"
        ),
        "status_saved": "Saved: {name}",
        "err_save_title": "Save Error",
        "err_save_msg": "Failed to save:\n{e}",
        "status_opened": "Opened: {name}  ({n} pages)",
        "close_confirm": ("Close the current file?\n(Unsaved changes will be lost)"),
        "status_closed": "File closed",
        "status_merged_open": "Opened {count} files merged ({total} pages): {names}",
        # Page operations status
        "status_rotated": "Rotated {count} page(s) by {deg}°",
        "info_no_page_sel": "Please select pages to delete",
        "warn_del_all_title": "Warning",
        "warn_del_all": "Cannot delete all pages.\nAt least one page must remain.",
        "confirm_del": "Delete {count} page(s)?",
        "status_deleted": "Deleted {count} page(s)",
        # Crop
        "info_crop_drag": "Drag on the preview to select a crop area",
        "status_cropped": "Cropped page {page}",
        "status_bulk_cropped": "Trimmed {count} selected page(s)",
        "confirm_bulk_crop": "Apply crop to all {count} selected page(s)?",
        "err_crop_small": "Selection too small. Please drag again.",
        "err_crop_title": "Crop Error",
        "err_crop_msg": (
            "Failed to set CropBox.\nAdjust the selection and try again.\n\n{e}"
        ),
        # Insert/Merge status
        "dlg_insert_title": "Select file(s) to insert (PDF/image)",
        "dlg_insert_pos_title": "Insert Position",
        "dlg_insert_pos_msg": (
            "Insert after which page?\n"
            "(0 = beginning, 1–{n} = after that page)\n\n"
            "Ex: 3 → insert after page 3"
        ),
        "status_insert_head": "beginning",
        "status_insert_tail": "end",
        "status_insert_pos": "after page {pos}",
        "status_inserted": "Inserted {count} file(s) ({total} pages) at {where}",
        "dlg_merge_title": "Select PDF(s) to Merge",
        "status_merged": "Merged {count} file(s) ({total} pages) to end",
        # Quit
        "quit_confirm": "Quit PageFolio?\n(Unsaved changes will be lost)",
        # Check doc
        "info_no_doc": "Please open a PDF file first",
        # D&D status
        "status_dnd_moved": "p.{src} → p.{dest} moved",
        "status_bulk_moved": "Moved {count} page(s)",
        # D&D file open
        "dnd_drop_hint": "Drop PDF or image here",
        "dnd_pdf_only": "Only PDF or image files (PNG/JPG/BMP/TIFF) are supported",
        "dnd_replace_confirm": (
            "Close current file and open the new one?\n(Unsaved changes will be lost)"
        ),
        # About dialog
        "about_title": "About PageFolio",
        "about_subtitle": "PDF Page Organizer",
        "about_ok": "OK",
        # Settings dialog
        "settings_title": "Settings",
        "settings_heading": "⚙ Settings",
        "settings_theme": "Theme:",
        "settings_theme_dark": "Dark",
        "settings_theme_light": "Light",
        "settings_theme_system": "System",
        "settings_font": "Font Size:",
        "settings_font_hint": "pt  (8–16)",
        "settings_preview_text": "Sample Text  サンプルテキスト  123",
        "settings_apply": "✔ Apply",
        "settings_cancel": "Cancel",
        # Merge order dialog
        "merge_title": "Confirm Merge Order",
        "merge_heading": "Confirm & Reorder",
        "merge_hint": (
            "Select a file and use ▲▼ to reorder\nThe PDFs will be merged in this order"
        ),
        "merge_up": "▲ Up",
        "merge_down": "▼ Down",
        "merge_remove": "✕ Remove",
        "merge_info": "Total {count} file(s)  /  {total} pages",
        "merge_confirm": "✔ Merge in This Order",
        "merge_cancel": "Cancel",
        "merge_no_files": "No files",
        # Plugin dialog
        "plugin_title": "Plugin Manager",
        "plugin_heading": "🔌 Plugin Manager",
        "plugin_dir_label": "Plugin folder: {path}",
        "plugin_empty": 'No plugins found\n\nPlace .py files in the\n"{dir}" folder',
        "plugin_author": "Author: {author}",
        "plugin_rescan": "🔄 Rescan",
        "plugin_open_folder": "📁 Open Folder",
        "plugin_close": "✔ Close",
        # OCR (LM Studio)
        "sec_ocr": "🔍 OCR (LM Studio)",
        "btn_ocr_current": "🔠 Extract Text from Current Page",
        "btn_ocr_selected": "📚 Extract Text from Selected Pages",
        "ocr_prompt_label": "Prompt:",
        "ocr_preset_text": "Plain text",
        "ocr_preset_table": "Table",
        "ocr_preset_markdown": "Markdown",
        "ocr_dialog_title": "OCR — LM Studio",
        "ocr_dialog_heading": "🔍 OCR Text Extraction",
        "ocr_progress_init": "Preparing…",
        "ocr_progress": "Processing {cur}/{total} pages… (p.{page})",
        "ocr_progress_render": "Rendering images… ({cur}/{total})",
        "ocr_progress_ocr": "OCR done ({done}/{total}) — p.{page}",
        "ocr_cancelling": "Cancelling…",
        "ocr_cancelled": "Cancelled",
        "ocr_complete": "Done: {count}/{total} page(s) succeeded",
        "ocr_failed": "Failed",
        "ocr_page_separator": "--- Page {page} ---",
        "ocr_page_error": "[Error] {error}",
        "ocr_text_skip_notice": "p.{page}: Skipped (embedded text detected)",
        "ocr_progress_skip": "Embedded text ({done}/{total}) — p.{page}",
        "ocr_copy": "📋 Copy to Clipboard",
        "ocr_copied": "Copied to clipboard",
        "ocr_save": "💾 Save to Text File…",
        "ocr_save_dialog_title": "Save OCR Result",
        "ocr_saved": "Saved: {path}",
        "ocr_cancel": "✕ Cancel",
        "ocr_close_during_run": (
            "OCR is running.\n"
            "Closing the window will cancel the process.\n"
            "Close anyway?"
        ),
        "ocr_err_connection": (
            "Failed to connect to LM Studio.\n"
            "URL: {url}\n\n"
            "Please make sure LM Studio is running\n"
            "and the URL is correct.\n\nDetails: {error}"
        ),
        "ocr_err_timeout": (
            "OCR timed out ({timeout}s).\n"
            "If the model is large, increase the timeout in settings.\n"
            "\nDetails: {error}"
        ),
        "ocr_provider_unsupported": (
            "Unsupported OCR provider configured: {name}\nPlease check your settings."
        ),
        # Phase 5: Claude Provider / security UI messages (D-06/D-07/D-12/D-15/D-17)
        "ocr_api_key_missing": (
            "API key is not configured ({env_var}). "
            "Set the environment variable or enter the key in the input field."
        ),
        "ocr_session_key_label": "API Key (this session only — not saved):",
        "ocr_cost_confirm_title": "Confirm Cloud Submission",
        "ocr_cost_confirm_msg": (
            "Destination: {host}\n"
            "Pages: {count} (estimated cost: {cost})\n\n"
            "Page images will be sent to an external API.\n"
            "Usage charges will apply.\n"
            "Proceed?"
        ),
        "ocr_waiting_retry": "p.{page}: Rate-limited, waiting (retry {n}/{max})",
        "ocr_provider_label": "OCR Provider:",
        "ocr_provider_name_claude": "Claude (Anthropic)",
        "ocr_provider_name_lmstudio": "LM Studio",
        # Phase 6: Gemini Provider messages (D-06/D-12)
        "ocr_provider_name_gemini": "Gemini (Google AI)",
        "ocr_api_key_missing_gemini": (
            "Gemini API key is not configured. "
            "Set the environment variable GEMINI_API_KEY (or GOOGLE_API_KEY), "
            "or enter the key in the input field."
        ),
        "ocr_scale_tradeoff_hint": (
            "Low=fast/cheap, High=accuracy. 1.5 recommended for low-spec PCs."
        ),
        "ocr_effort_label": "Inference Effort:",
        "ocr_provider_off_hint": "OCR is disabled. Select a provider in Settings.",
        "ocr_model_refresh": "Refresh Models",
        # LM Studio settings
        "settings_lm_studio_section": "🔍 LM Studio (OCR)",
        "settings_lm_url": "URL:",
        "settings_lm_model": "Model:",
        "settings_lm_model_hint": "(empty = auto-use model loaded in LM Studio)",
        "settings_lm_fetch_models": "📥 Fetch Models",
        "settings_lm_test": "🔌 Test Connection",
        "settings_lm_test_ok": "Connected ({count} model(s) available)",
        "settings_lm_test_fail": "Connection failed: {error}",
        "settings_lm_testing": "⏳ Connecting… ({url})",
        "settings_ocr_scale": "OCR Resolution Scale:",
        "settings_ocr_timeout": "OCR Timeout (s):",
        "settings_ocr_concurrency": "OCR Concurrency:",
        "settings_ocr_concurrency_hint": (
            "(1-8 / 2 recommended. Effective only if LM Studio serves "
            "requests in parallel)"
        ),
        "settings_open_llm_config": "🔍 LLM Settings…",
        # LLM config dialog (shared by OCR & Settings)
        "llm_config_title": "LLM Settings",
        "llm_config_heading": "🔍 LLM Settings (LM Studio)",
        "llm_config_apply": "✓ Apply",
        "llm_config_cancel": "✕ Cancel",
        # OCR dialog
        "ocr_server_label": "Server:",
        "ocr_model_label": "Model:",
        "ocr_run": "▶ Run OCR",
        "ocr_fetch_models": "📥 Fetch Models",
        "ocr_open_llm_config": "⚙ LLM Settings…",
        "ocr_clear": "🧹 Clear",
        "ocr_models_fetched": "Fetched {count} model(s)",
        "ocr_models_fetch_fail": "Fetch failed: {error}",
        "ocr_models_fetching": "⏳ Fetching models… ({url})",
        "ocr_run_first": 'Press "Run OCR" to start',
        "ocr_params_label": "Advanced:",
        "ocr_scale_short": "Scale:",
        "ocr_timeout_short": "Timeout:",
        "ocr_max_tokens_short": "Max tokens:",
        "ocr_max_tokens_hint": "(-1: use model max / cap 262144)",
        "ocr_temperature_short": "Temp:",
        "ocr_temperature_hint": "(0.0-0.2 recommended)",
        "ocr_params_hint": (
            "To reduce hallucinations: lower temp / raise scale. "
            "Recommended models: Qwen2-VL-7B / MiniCPM-V / InternVL2 8B+"
        ),
        # Common error
        "err_title": "Error",
        "info_title": "Info",
        "warn_title": "Warning",
        "confirm_title": "Confirm",
    },
}
