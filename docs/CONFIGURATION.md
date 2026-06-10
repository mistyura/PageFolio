<!-- generated-by: gsd-doc-writer -->
# CONFIGURATION.md — PageFolio 設定リファレンス

PageFolio の設定は実行時に自動生成される JSON ファイル `pagefolio_settings.json` に永続化されます。
このファイルはアプリケーションと同じディレクトリ（PyInstaller ビルド時は `.exe` と同じ場所）に保存されます。

---

## 設定ファイルの場所と形式

| 項目 | 内容 |
|------|------|
| ファイル名 | `pagefolio_settings.json` |
| フォーマット | JSON（UTF-8、インデント 2） |
| 自動生成 | 設定変更時またはアプリ終了時に `_save_settings()` が呼ばれた際に作成（起動時は読み取りのみ） |
| 配置場所（通常実行） | プロジェクトルート（`pagefolio.py` と同じディレクトリ） |
| 配置場所（PyInstaller ビルド後） | `.exe` と同じディレクトリ |

設定ファイルを削除するとすべての設定がデフォルトにリセットされます。

---

## 設定項目一覧

### UI / 表示設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `theme` | 任意 | `"dark"` | カラーテーマ。`"dark"` / `"light"` / `"system"` |
| `font_size` | 任意 | `12` | ベースフォントサイズ（pt）。8〜16 の整数 |
| `lang` | 任意 | `"ja"` | UI 言語。`"ja"`（日本語）/ `"en"`（英語） |

**テーマ値の説明:**

| 値 | 説明 |
|----|------|
| `"dark"` | ダークテーマ（既定） |
| `"light"` | ライトテーマ |
| `"system"` | Windows システム設定に追従（`AppsUseLightTheme` レジストリ値を参照） |

---

### OCR 基本設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `ocr_provider` | 任意 | `"off"` | OCR プロバイダ。`"off"` / `"lmstudio"` / `"claude"` / `"gemini"` / `"tesseract"` |
| `ocr_scale` | 任意 | `1.5` | OCR 用ページ画像の解像度倍率。低スペック PC は 1.5 推奨 |
| `ocr_timeout` | 任意 | `120` | OCR HTTP タイムアウト秒数 |
| `ocr_max_tokens` | 任意 | `-1` | OCR 最大出力トークン数。`-1` でモデルの最大値に委ねる（LM Studio 専用） |
| `ocr_temperature` | 任意 | `0.1` | OCR 温度パラメータ。低温（0.0〜0.2）推奨 |
| `ocr_concurrency` | 任意 | `2` | OCR 並列処理数。1〜8（推奨: 2） |
| `ocr_prompt_preset` | 任意 | `"text"` | OCR プロンプトプリセット。`"text"` / `"table"` / `"markdown"` |
| `ocr_effort` | 任意 | `"low"` | Claude Sonnet/Opus 系モデルの推論強度。`"low"` / `"medium"` / `"high"` / `"xhigh"` / `"max"` |

**OCR プロバイダ値の説明:**

| 値 | 説明 |
|----|------|
| `"off"` | OCR 無効（既定） |
| `"lmstudio"` | LM Studio（ローカル Vision LLM） |
| `"claude"` | Claude API（Anthropic） |
| `"gemini"` | Gemini API（Google AI） |
| `"tesseract"` | Tesseract OCR（ローカル、要インストール） |

---

### LM Studio プロバイダ設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `lm_studio_url` | 任意 | `"http://localhost:1234"` | LM Studio サーバの URL |
| `lm_studio_model` | 任意 | `""` | 使用するモデル名。空欄で LM Studio が読み込み済みのモデルを自動使用 |

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
> 環境変数 `GEMINI_API_KEY`（または `GOOGLE_API_KEY`）または OCR ダイアログのキー入力欄（セッションのみ）から設定してください。

---

### Tesseract プロバイダ設定

| キー | 必須 | 既定値 | 説明 |
|------|------|--------|------|
| `tesseract_lang` | 任意 | `"jpn+eng"` | Tesseract に渡す言語コード。`jpn` パックが未インストールの場合は `eng` に自動フォールバック |
| `tesseract_psm` | 任意 | `3` | ページセグメンテーションモード（3=全自動、6=単一ブロック） |

> Tesseract プロバイダを使用するには、別途 Tesseract をインストールし `tesseract` コマンドがパスに通っている必要があります。

---

## 機密情報の取り扱い（セキュリティ）

以下のキーは `_SENSITIVE_KEYS` ガードにより `pagefolio_settings.json` への書き込みが**構造的に禁止**されています。

| キー名 | 説明 |
|--------|------|
| `claude_api_key` / `anthropic_api_key` / `ANTHROPIC_API_KEY` | Anthropic API キー |
| `gemini_api_key` / `google_api_key` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Google API キー |
| `api_key` | 汎用 API キー |

API キーは以下の優先順位で解決されます（設定ファイルへの保存は行われません）:

1. **環境変数**（最優先）
2. **セッションキー**（OCR ダイアログの入力欄・アプリ終了時に消去）

```
# 環境変数の設定例（PowerShell）
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:GEMINI_API_KEY    = "AIza..."
```

---

## 設定ファイルのサンプル

最小構成（すべての値が既定値の場合は省略可）:

```json
{
  "theme": "dark",
  "font_size": 12,
  "lang": "ja",
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
| `ocr_provider` が `"tesseract"` で Tesseract 未インストール | OCR ダイアログで `RuntimeError` | Tesseract をインストールしてパスを通す |
| `lm_studio_url` のサーバが未起動 | OCR 実行時に `ConnectionError` | LM Studio を起動する |

---

## 設定の変更方法

設定は以下の 2 通りの方法で変更できます:

1. **UI から変更**: メニューの「⚙ テーマ・フォント設定…」または「🔍 LLM 設定…」ダイアログ
2. **JSON を直接編集**: アプリ終了後に `pagefolio_settings.json` をテキストエディタで編集

UI から変更した場合は即時に `pagefolio_settings.json` へ書き込まれます。

---

## 関連ファイル

| ファイル | 説明 |
|----------|------|
| `pagefolio/settings.py` | 設定読み書き・テーマ解決・フォント生成ユーティリティ |
| `pagefolio/constants.py` | `SETTINGS_FILE` 定数（ファイル名定義） |
| `pagefolio/themes.py` | `THEMES` 辞書（テーマ定義）と実行時辞書 `C` |
| `pagefolio/ocr.py` | OCR 既定値定数（`DEFAULT_LM_STUDIO_URL` 等）・`build_provider` |
| `pagefolio/ocr_providers.py` | 各 OCR プロバイダの実装 |
