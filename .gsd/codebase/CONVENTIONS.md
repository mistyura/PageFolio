---
last_mapped_commit: fb41c422035fa9d4fac753920909da56e068555c
---

# PageFolio — コーディング規約 (Conventions)

## 命名規則 (Naming Conventions)

- **モジュール名**: `snake_case.py` (例: `file_ops.py`, `ui_builder.py`)
- **テストファイル**: `test_<module_name>.py` (例: `test_pdf_ops.py`, `test_ocr_pipeline.py`)
- **クラス名**: `PascalCase` (例: `PDFEditorApp`, `SettingsDialog`)
- **Mixin クラス**: サフィックスとして `Mixin` を付与 (例: `UIBuilderMixin`, `ViewerMixin`)
- **ダイアログクラス**: サフィックスとして `Dialog` を付与 (例: `SettingsDialog`, `LLMConfigDialog`)
- **内部メソッド・属性**: 外部から直接アクセスさせない非公開メンバーには `_` を付与 (例: `_refresh_all()`, `self._undo_stack`)
- **Tkinter イベントハンドラ**: `_on_<action>` または `_do_<action>` (例: `_on_summary()`, `_do_merge()`)
- **定数名**: `UPPER_SNAKE_CASE` (例: `APP_VERSION`, `SETTINGS_FILE`)

---

## コーディングスタイル (Code Style)

### 1. テーマカラーの参照
ウィジェットの背景色やテキスト色を指定する際、カラーコード（例: `"#1a1a2e"`）をコード中にハードコードすることは厳禁です。
- 必ず `pagefolio/themes.py` の実行時テーマ辞書である `C` から参照します。
- 使用例: `bg=C["BG_DARK"]`, `fg=C["TEXT_MAIN"]`

### 2. フォントサイズの動的解決
フォントサイズを `font=("Segoe UI", 12)` のように直接固定値で指定することは避けてください。
- ベースフォントサイズ（設定変更可能）に対する相対差分 `delta` を指定して動的に取得します。
- アプリ内では `self._font(delta)` (Mixin 経由) 、ダイアログやユーティリティ内では `get_font(delta)` を呼び出します。
- 使用例: `font=self._font(2)`

### 3. TTK ボタンスタイル
ボタンの視覚的役割に応じて、一貫したスタイル名を設定します。
- **通常操作**: `"TButton"`
- **主要・強調アクション**: `"Accent.TButton"`
- **破壊的操作（削除・クリア・終了）**: `"Danger.TButton"`
- **トリミングモード ON (トグル状態)**: `"CropOn.TButton"`

### 4. 日英辞書の整合性 (Language Parity)
多言語対応ファイル `pagefolio/lang.py` の `LANG` 辞書に新しい文言キーを追加する場合、**必ず `ja` と `en` の両方に同一のキー名で追加**しなければなりません。
- キー数の左右不一致や、プレースホルダー（例: `{name}` などの f-string 変数）の不整合は、自動テスト `tests/test_lang_parity.py` によって厳しくチェックされ、不一致時はテストが失敗します。

---

## エラーハンドリング (Error Handling)

### 1. 裸の except の禁止
例外をキャッチする際は、原因特定を妨げる `except:` (裸の except) を使用せず、必ず `except Exception as e:` または特定の例外型を指定します。

### 2. ダイアログ保護
ダイアログでのエラーは、ユーザーへ通知するために `messagebox.showerror()` を使用してダイアログを閉じさせずにエラー状態を伝え、スタックトレースがコンソールに漏れるのを防ぎます。

### 3. プラグインの保護
サードパーティのプラグインを実行する際、単一のプラグインのクラッシュがアプリ全体のクラッシュやファイル破損を引き起こさないよう、プラグイン呼び出しは個別に `try-except` でラップされています。

---

## ロギング (Logging)

- アプリケーションの動作ログは、Python 標準の `logging` ライブラリを使用して出力します。
- 各ファイルで `logger = logging.getLogger(__name__)` を定義して、モジュール名ごとにロギングを管理します。
- OCR エラーやファイルのディスク退避失敗など、調査に必要な文言は `logger.exception()` または `logger.error()` を使って出力します。
