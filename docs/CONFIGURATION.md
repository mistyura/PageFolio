<!-- generated-by: gsd-doc-writer -->
# CONFIGURATION.md — PageFolio 設定リファレンス

PageFolio の設定は実行時に自動生成される JSON ファイル `pagefolio_settings.json` に永続化されます。
このファイルはアプリケーションと同じディレクトリ（PyInstaller ビルド時は `.exe` と同じ場所）に保存されます。

---

## 設定ファイルの場所と形式

| 項目 | 内容 |
|------|------|
| ファイル名 | `pagefolio_settings.json`（`pagefolio/constants.py` の `SETTINGS_FILE`） |
| フォーマット | JSON（UTF-8、インデント 2） |
| 自動生成 | 設定変更時またはアプリ終了時に `_save_settings()` が呼ばれた際に作成（起動時は読み取りのみ） |
| 書き込み方式 | 一時ファイル（`.tmp`）へ書き込んでから `os.replace()` で原子的に差し替え。書き込み途中のプロセス強制終了・電源断でも JSON が壊れない |
| 配置場所（通常実行） | プロジェクトルート（`pagefolio.py` と同じディレクトリ、`pagefolio/settings.py` の `_get_base_dir()` が解決） |
| 配置場所（PyInstaller ビルド後） | `.exe` と同じディレクトリ（`sys.frozen` 判定） |

設定ファイルを削除するとすべての設定がデフォルトにリセットされます（`_load_settings()` がデフォルト値を返すため）。

---

## 設定項目一覧

### UI / 表示設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `theme` | 任意 | `"dark"` | カラーテーマ。`"dark"` / `"light"` / `"system"` |
| `font_size` | 任意 | `12` | ベースフォントサイズ（pt）。8〜16 の整数（`dialogs/settings.py` で `max(8, min(16, ...))` にクランプ） |
| `lang` | 任意 | `"ja"` | UI 言語。`"ja"`（日本語）/ `"en"`（英語） |
| `thumb_page_size` | 任意 | `20` | サムネイル一覧の 1 窓あたり表示件数。10〜100 の範囲に自動クランプ（`pagination.clamp_page_size`）。範囲外・非数値は既定 20 にフォールバック |

**テーマ値の説明:**

| 値 | 説明 |
|----|------|
| `"dark"` | ダークテーマ（既定） |
| `"light"` | ライトテーマ |
| `"system"` | Windows システム設定に追従（`AppsUseLightTheme` レジストリ値を参照） |

---

### ウィンドウ状態（自動管理）

以下のキーは UI からの手動設定項目ではなく、アプリ終了時に現在の状態が自動保存され、次回起動時に復元されます（`pagefolio/app.py`）。手動で編集も可能ですが、通常は触る必要はありません。

| キー | 説明 |
|------|------|
| `window_geometry` | ウィンドウの位置・サイズ（Tkinter の `geometry()` 文字列、例: `"1200x757+52+52"`） |
| `sash_left` | 左ペイン（サムネイル一覧）の分割バー位置（ピクセル） |
| `sash_right` | 右ペイン（操作パネル）の分割バー位置（ピクセル） |
| `edit_mode` | 起動時のモード。`true`=編集モード / `false`=閲覧モード（F5 キーで切替） |

---

### OCR 基本設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `ocr_provider` | 任意 | `"off"` | OCR プロバイダ。`"off"` / `"lmstudio"` / `"ollama"` / `"runpod"` / `"claude"` / `"gemini"` / `"tesseract"`（＋プラグイン登録プロバイダ） |
| `ocr_scale` | 任意 | `1.5` | OCR 用ページ画像の解像度倍率。1.0〜4.0 にクランプ。低スペック PC は 1.5 推奨 |
| `ocr_timeout` | 任意 | `120` | OCR HTTP タイムアウト秒数。10〜900 にクランプ |
| `ocr_max_tokens` | 任意 | `-1` | OCR 最大出力トークン数。-1〜262144 にクランプ。`-1` は「モデルの最大値に委ねる」（LM Studio / Ollama 専用。Claude / Gemini / RunPod は `-1` 指定時に内部で 4096 にクランプされる） |
| `ocr_temperature` | 任意 | `0.1` | OCR 温度パラメータ。0.0〜2.0 にクランプ。低温（0.0〜0.2）推奨 |
| `ocr_concurrency` | 任意 | `2` | OCR 並列処理数。1〜8 にクランプ（推奨: 2） |
| `ocr_prompt_preset` | 任意 | `"text"` | OCR プロンプトプリセット。`"text"` / `"table"` / `"markdown"` |
| `ocr_custom_prompt` | 任意 | `""` | カスタム OCR プロンプト。非空の場合はプリセットより優先される。外部 md ファイル連動あり（→ [カスタム / サマリプロンプトの仕様](#カスタム--サマリプロンプトの仕様)） |
| `ocr_summary_prompt` | 任意 | `""` | 全ページ統合サマリ生成用のカスタムプロンプト。非空の場合はプロバイダ別既定より優先される。外部 md ファイル連動あり（→ 同上） |
| `ocr_effort` | 任意 | `"low"` | Claude モデルの推論強度。`"low"` / `"medium"` / `"high"` / `"xhigh"` / `"max"`（Claude プロバイダのみ有効） |

**OCR プロバイダ値の説明:**

| 値 | 説明 |
|----|------|
| `"off"` | OCR 無効（既定） |
| `"lmstudio"` | LM Studio（ローカル Vision LLM） |
| `"ollama"` | Ollama（ローカル Vision LLM） |
| `"runpod"` | RunPod Serverless（OpenAI 互換 Vision API） |
| `"claude"` | Claude API（Anthropic） |
| `"gemini"` | Gemini API（Google AI） |
| `"tesseract"` | Tesseract OCR（ローカル、要インストール） |

---

### カスタム / サマリプロンプトの仕様

OCR で実際に送信されるプロンプトと、結果の表示形式は以下のルールで決まります。

**1. プロンプトの優先順位（実行のたびに解決）**

| 種別 | 優先順位（上が最優先） |
|------|------------------------|
| OCR プロンプト | ① 外部ファイル `ocr_custom_prompt.md` → ② アクティブなプロンプトテンプレート（`prompt_templates`） → ③ 設定欄 `ocr_custom_prompt` → ④ プロバイダ別プリセットテンプレート（Claude / Gemini のみ）→ ⑤ 汎用プリセット（`text` / `table` / `markdown`） |
| サマリプロンプト | ① 外部ファイル `ocr_summary_prompt.md` → ② アクティブなプロンプトテンプレート（`prompt_templates`） → ③ 設定欄 `ocr_summary_prompt` → ④ プロバイダ別サマリテンプレート（Claude / Gemini のみ）→ ⑤ 汎用既定（`DEFAULT_SUMMARY_PROMPT`） |

解決ロジックは `pagefolio/ocr.py` の `resolve_ocr_prompt` / `resolve_summary_prompt`（純関数）と
`pagefolio/settings.py` の `load_custom_prompt` / `load_summary_prompt` に集約されています。

**2. 外部 md ファイル連動（巨大プロンプト向け）**

数十行規模の業務用プロンプトは、設定ダイアログの入力欄ではなく外部ファイルで管理できます。

| 項目 | 内容 |
|------|------|
| ファイル名 | `ocr_custom_prompt.md`（OCR 用）/ `ocr_summary_prompt.md`（サマリ用）。`pagefolio/constants.py` の `CUSTOM_PROMPT_FILE` / `SUMMARY_PROMPT_FILE` |
| 配置場所 | `pagefolio_settings.json` と同じディレクトリ（通常実行時はプロジェクトルート、PyInstaller ビルド後は `.exe` と同じ場所） |
| エンコーディング | UTF-8（BOM 付き `utf-8-sig` も許容） |
| 開いたとき | ファイルが存在して非空なら、LLM 設定ダイアログのプロンプト入力欄へ内容を反映（連動中の注記を表示） |
| 適用したとき | ファイルが存在する場合のみ、入力欄の内容をファイルへ書き戻す（settings にも同期保存）。ファイルが無ければ新規作成しない |
| 実行したとき | OCR 実行・サマリ実行のたびにファイルを毎回再読込（外部エディタでの編集がアプリ再起動なしで反映される） |
| 無効時の挙動 | ファイルが不在・空・読込失敗の場合はプロンプトテンプレート → 設定欄の値へフォールバック |

連動を始めるには、空の md ファイルを上記の場所に置くだけです（次回の「適用」から書き込まれます）。
ファイルを削除すれば settings のみの通常動作へ戻ります。

**3. プロンプトテンプレート管理**

`prompt_templates` キーで、OCR プロンプト・サマリプロンプトのペアを名前付きで複数保存・切替できます。

| フィールド | 説明 |
|-----------|------|
| `prompt_templates.active` | 現在アクティブなテンプレート名（空文字 = 未選択・設定欄直接編集と等価） |
| `prompt_templates.items` | `{テンプレート名: {"custom_prompt": str, "summary_prompt": str}}` の辞書 |

CRUD 操作は `pagefolio/settings.py` の `save_template` / `delete_template` / `rename_template` / `get_template` / `list_template_names` で行われます。アクティブなテンプレートは削除できません（先に別のテンプレートへ切替が必要）。

**4. 結果の表示形式（Markdown 整形）**

Markdown 整形表示のオン/オフは **OCR ダイアログのプリセット選択（通常テキスト / 表形式 / Markdown）に一本化**されています。

- プリセット「Markdown」を選ぶと、OCR 本文・サマリとも整形表示（見出し / リスト / テーブルの描画）になります。
- カスタム / サマリプロンプト使用時、プリセットは実プロンプトへ反映されず「表示形式の選択」としてのみ働きます（OCR ダイアログのプリセット横に注記が表示されます）。
- コピー / テキスト保存は常に raw テキストです（整形は表示専用）。

---

### LM Studio プロバイダ設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `lm_studio_url` | 任意 | `"http://localhost:1234"` | LM Studio サーバの URL |
| `lm_studio_model` | 任意 | `""` | 使用するモデル名。空欄で LM Studio が読み込み済みのモデルを自動使用 |

---

### Ollama プロバイダ設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `ollama_url` | 任意 | `"http://localhost:11434"` | Ollama サーバの URL |
| `ollama_model` | 任意 | `""` | 使用するモデル名 |

---

### RunPod プロバイダ設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `runpod_url` | 任意 | `""` | RunPod Serverless エンドポイント URL |
| `runpod_model` | 任意 | `""` | 使用するモデル名。空欄の場合は `"runpod-model"` にフォールバック |

> **API キーについて:** RunPod API キーは `pagefolio_settings.json` には保存されません。
> 環境変数 `RUNPOD_API_KEY` または OCR ダイアログのキー入力欄（セッションのみ）から設定してください。

---

### Claude プロバイダ設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `claude_model` | 任意 | `"claude-sonnet-4-6"` | 使用する Claude モデル ID |

> **API キーについて:** Claude API キーは `pagefolio_settings.json` には保存されません。
> 環境変数 `ANTHROPIC_API_KEY` または OCR ダイアログのキー入力欄（セッションのみ）から設定してください。

---

### Gemini プロバイダ設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `gemini_model` | 任意 | `"gemini-2.5-flash"` | 使用する Gemini モデル ID |

> **API キーについて:** Gemini API キーは `pagefolio_settings.json` には保存されません。
> 環境変数 `GEMINI_API_KEY`（未設定時は `GOOGLE_API_KEY` にフォールバック）または OCR ダイアログのキー入力欄（セッションのみ）から設定してください。

---

### Tesseract プロバイダ設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `tesseract_lang` | 任意 | `"jpn+eng"` | Tesseract に渡す言語コード。`jpn` 言語パックが未検出の場合は保存時に自動的に `"eng"` にフォールバックする（UI 上は選択不可、検出結果に基づく固定値） |
| `tesseract_psm` | 任意 | `3` | ページセグメンテーションモード（3=全自動）。UI からは設定できず、`pagefolio_settings.json` の直接編集でのみ変更可能 |

> Tesseract プロバイダを使用するには、別途 Tesseract をインストールし `tesseract` コマンドがパスに通っている必要があります。API キーは不要です。

---

### プロバイダフォールバック設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `ocr_fallback_enabled` | 任意 | `false` | プロバイダフォールバック機能の有効/無効。既定は無効（安全側） |
| `ocr_fallback_chain` | 任意 | `[]` | フォールバック先プロバイダ名のリスト（実行順）。`ocr_fallback_enabled` が `true` かつ非空の場合のみ機能する |

---

## 機密情報の取り扱い（セキュリティ）

以下のキーは `_SENSITIVE_KEYS` ガードにより `pagefolio_settings.json` への書き込みが**構造的に禁止**されています（`pagefolio/ocr_providers/registry.py` の `sensitive_keys()` が生成する集合、現行 10 エントリ）。

| キー名 | 説明 |
|--------|------|
| `claude_api_key` / `anthropic_api_key` / `ANTHROPIC_API_KEY` | Anthropic API キー |
| `gemini_api_key` / `google_api_key` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Google API キー |
| `runpod_api_key` / `RUNPOD_API_KEY` | RunPod API キー |
| `api_key` | 汎用 API キー |

`_save_settings()` はこれらのキーが混入していないかを保存の都度チェックし、混入していればログへ警告（キー名のみ、値は出力しない）した上で除外して保存します。

API キーは `pagefolio/ocr.py` の `_resolve_api_key()` により以下の優先順位で解決されます（設定ファイルへの保存は行われません）:

1. **セッションキー**（最優先）— OCR ダイアログ / LLM 設定ダイアログのキー入力欄から入力した値。`app._session_api_keys` にのみメモリ上保持され、設定ファイルには一切書き込まれない。アプリ終了時に消去される
2. **環境変数**（セッションキー未設定の場合のフォールバック）

いずれも未設定の場合は `OCRAPIKeyError`（対応する環境変数名を含む）が送出されます。

```
# 環境変数の設定例（PowerShell）
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:GEMINI_API_KEY    = "AIza..."
$env:RUNPOD_API_KEY    = "rpa_..."
```

LM Studio / Ollama はローカルサーバへの接続のみで API キーを必要としません。

---

## 設定ファイルのサンプル

最小構成（すべての値が既定値の場合は省略可）:

```json
{
  "theme": "dark",
  "font_size": 12,
  "lang": "ja",
  "thumb_page_size": 20,
  "ocr_provider": "lmstudio",
  "lm_studio_url": "http://localhost:1234",
  "lm_studio_model": "",
  "ocr_scale": 1.5,
  "ocr_timeout": 120,
  "ocr_max_tokens": -1,
  "ocr_temperature": 0.1,
  "ocr_concurrency": 2,
  "ocr_prompt_preset": "text",
  "claude_model": "claude-sonnet-4-6",
  "ocr_effort": "low",
  "gemini_model": "gemini-2.5-flash"
}
```

---

## 既定値と起動失敗に関する注意

PageFolio のすべての設定キーは任意項目であり、欠損しても起動失敗は発生しません。
設定ファイルが破損・欠損している場合、`_load_settings()` 関数がすべての既定値を返します。

ただし、以下の状況では実行時エラーが発生します:

| 状況 | 症状 | 対処 |
|------|------|------|
| `ocr_provider` が `"claude"` で `ANTHROPIC_API_KEY` 未設定 | OCR ダイアログで `OCRAPIKeyError` | 環境変数を設定、またはダイアログでキーを入力 |
| `ocr_provider` が `"gemini"` で `GEMINI_API_KEY` / `GOOGLE_API_KEY` 未設定 | OCR ダイアログで `OCRAPIKeyError` | 環境変数を設定、またはダイアログでキーを入力 |
| `ocr_provider` が `"runpod"` で `RUNPOD_API_KEY` 未設定 | OCR ダイアログで `OCRAPIKeyError` | 環境変数を設定、またはダイアログでキーを入力 |
| `ocr_provider` が `"tesseract"` で Tesseract 未インストール | OCR ダイアログで `RuntimeError` | Tesseract をインストールしてパスを通す |
| `lm_studio_url` / `ollama_url` / `runpod_url` のサーバが未起動・未設定 | OCR 実行時に `ConnectionError` または `RuntimeError` | サーバを起動する、またはエンドポイント URL を設定する |

---

## 設定の変更方法

設定は以下の 2 通りの方法で変更できます:

1. **UI から変更**: メニューの「⚙ テーマ・フォント設定…」または「🔍 LLM 設定…」ダイアログ
2. **JSON を直接編集**: アプリ終了後に `pagefolio_settings.json` をテキストエディタで編集（`tesseract_psm` など一部のキーは UI から設定できないため直接編集が必要）

UI から変更した場合は即時に `pagefolio_settings.json` へ書き込まれます。

---

## 関連ファイル

| ファイル | 説明 |
|----------|------|
| `pagefolio/settings.py` | 設定読み書き・テーマ解決・フォント生成ユーティリティ（`_SENSITIVE_KEYS` ガード・外部プロンプトファイル読み書き `load_prompt_file` / `save_prompt_file`・プロンプトテンプレート CRUD を含む） |
| `pagefolio/constants.py` | `SETTINGS_FILE` / `CUSTOM_PROMPT_FILE` / `SUMMARY_PROMPT_FILE` 定数（ファイル名定義） |
| `pagefolio/ocr_providers/registry.py` | プロバイダ→環境変数の中央レジストリ（`sensitive_keys()` / `resolve_env_key()`）。標準ライブラリ `os` のみに依存し、循環 import を防ぐ独立モジュール |
| `ocr_custom_prompt.md` / `ocr_summary_prompt.md` | （任意配置）外部プロンプトファイル。存在すれば設定欄と連動する（→ [カスタム / サマリプロンプトの仕様](#カスタム--サマリプロンプトの仕様)） |
| `pagefolio/themes.py` | `THEMES` 辞書（テーマ定義）と実行時辞書 `C` |
| `pagefolio/pagination.py` | `clamp_page_size` 等のページネーション純ロジック（`thumb_page_size` のクランプ範囲定義） |
| `pagefolio/ocr.py` | OCR 既定値定数（`DEFAULT_LM_STUDIO_URL` 等）・`build_provider`・`_resolve_api_key`・`resolve_ocr_prompt` / `resolve_summary_prompt` |
| `pagefolio/ocr_providers/` | 各 OCR プロバイダの実装（LM Studio / Ollama / RunPod / Claude / Gemini / Tesseract、パッケージ分割） |
| `pagefolio/dialogs/llm_config/` | `LLMConfigDialog`（OCR 設定 UI・クランプ処理を含む保存ロジック、パッケージ分割） |
