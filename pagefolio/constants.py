# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
# https://github.com/mistyura/PageFolio
"""定数定義 — テーマ、バージョン、言語辞書"""

# ===================== カラーテーマ =====================
THEMES = {
    "dark": {
        "BG_DARK": "#1a1a2e",
        "BG_PANEL": "#16213e",
        "BG_CARD": "#0f3460",
        "ACCENT": "#e94560",
        "ACCENT2": "#533483",
        "TEXT_MAIN": "#eaeaea",
        "TEXT_SUB": "#a0a0b0",
        "BTN_HOVER": "#ff6b6b",
        "SUCCESS": "#4ecca3",
        "WARNING": "#ffd460",
        "CROP_ON_BG": "#8b0000",
        "PREVIEW_BG": "#111122",
        "DANGER_BG": "#7c1c2e",
        "DANGER_FG": "#ffaaaa",
    },
    "light": {
        "BG_DARK": "#f0f0f5",
        "BG_PANEL": "#e0e0ea",
        "BG_CARD": "#d0d0dd",
        "ACCENT": "#d63050",
        "ACCENT2": "#7b52ab",
        "TEXT_MAIN": "#1a1a2e",
        "TEXT_SUB": "#555566",
        "BTN_HOVER": "#ff6b6b",
        "SUCCESS": "#2a9d6a",
        "WARNING": "#b8860b",
        "CROP_ON_BG": "#cc3333",
        "PREVIEW_BG": "#c8c8d0",
        "DANGER_BG": "#e8c0c0",
        "DANGER_FG": "#7c1c2e",
    },
}

# 現在テーマの色をモジュールレベルで参照するための辞書（実行時に設定）
C = dict(THEMES["dark"])

# ===================== バージョン =====================
APP_VERSION = "v0.9.8"

# ===================== ファイル名定数 =====================
SETTINGS_FILE = "pagefolio_settings.json"
PLUGINS_DIR = "plugins"
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
        # プレビュー空状態
        "preview_empty1": "📂 ファイルを開いてください",
        "preview_empty2": "Ctrl+O  または右パネル「ファイルを開く」",
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
        "err_crop_small": "範囲が小さすぎます。もう一度ドラッグしてください",
        "err_crop_title": "トリミングエラー",
        "err_crop_msg": (
            "CropBoxの設定に失敗しました。\n範囲を調整して再度お試しください。\n\n{e}"
        ),
        # 挿入・結合ステータス
        "dlg_insert_title": "挿入するPDFを選択（複数可）",
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
        # D&D ファイルオープン
        "dnd_drop_hint": "ここに PDF をドロップ",
        "dnd_pdf_only": "PDF ファイルのみ対応しています",
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
        # Preview empty state
        "preview_empty1": "📂 Open a file to get started",
        "preview_empty2": 'Ctrl+O  or use "Open File" in the right panel',
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
        "err_crop_small": "Selection too small. Please drag again.",
        "err_crop_title": "Crop Error",
        "err_crop_msg": (
            "Failed to set CropBox.\nAdjust the selection and try again.\n\n{e}"
        ),
        # Insert/Merge status
        "dlg_insert_title": "Select PDF(s) to Insert",
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
        # D&D file open
        "dnd_drop_hint": "Drop PDF here",
        "dnd_pdf_only": "Only PDF files are supported",
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
        # Common error
        "err_title": "Error",
        "info_title": "Info",
        "warn_title": "Warning",
        "confirm_title": "Confirm",
    },
}
