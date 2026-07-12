# Stack Research

**Domain:** デスクトップ PDF エディタ OCR プロバイダ拡張（Python 3.8+ / Tkinter）
**Researched:** 2026-06-06
**Confidence:** HIGH（Claude・Gemini は公式ドキュメント直接確認。Tesseract は公式 + コミュニティ複数ソース）

---

## 調査スコープ

既存スタック（Tkinter / pymupdf / Pillow / tkinterdnd2）は検証済みのため再調査しない。
本ファイルは v1.4.0 マイルストーンで **追加が必要な技術・API 仕様のみ** を扱う。

---

## 新規追加なし — 依存ゼロの方針確認

**結論: 3 プロバイダ全て `urllib.request` のみで実装可能。新規 pip パッケージは不要。**

| プロバイダ | 実装方式 | 追加 pip 依存 |
|-----------|---------|-------------|
| Claude (Anthropic) | `urllib.request` + JSON | なし |
| Gemini (Google AI Studio) | `urllib.request` + JSON | なし |
| Tesseract | `subprocess.run` (CLI 呼び出し) | `pytesseract` 不要 |

公式 SDK（`anthropic`・`google-genai`）は PyInstaller `.exe` 肥大化・隠れ依存取り込みの問題があるため **採用しない**。
現行 LM Studio 実装（`ocr.py`）が `urllib` 直叩きで実現しているパターンをそのまま踏襲する。

---

## Recommended Stack（新規 API 対応部分）

### Core Technologies（追加なし）

既存コードベースが使用する Python 標準ライブラリのみで対応する。

| 標準ライブラリ | 用途 | 備考 |
|---------------|------|------|
| `urllib.request` | HTTP POST/GET（Claude・Gemini API 呼び出し） | 既存 `ocr.py` で使用中 |
| `urllib.error` | HTTP エラーハンドリング | 既存 `ocr.py` で使用中 |
| `json` | リクエスト/レスポンス JSON 処理 | 既存コード全体で使用中 |
| `base64` | PNG → base64 エンコード | 既存 `ocr.py` の `page_to_png_b64()` で使用中 |
| `os` | 環境変数読み取り（`os.environ.get()`） | APIキー取得に使用 |
| `subprocess` | Tesseract CLI 呼び出し | Tesseract Provider のみ |
| `concurrent.futures` | 並列 OCR（`ThreadPoolExecutor`） | 既存 `call_lm_studio_parallel` のパターンを踏襲 |

---

## API 仕様詳細（実装根拠）

### Claude (Anthropic) API

**信頼度: HIGH** — `platform.claude.com/docs` 公式ドキュメントより直接確認（2026-06-06）

#### エンドポイント・認証

```
POST https://api.anthropic.com/v1/messages
```

必須ヘッダー:
```
x-api-key: <ANTHROPIC_API_KEY>
anthropic-version: 2023-06-01
content-type: application/json
```

環境変数: `ANTHROPIC_API_KEY`

#### 推奨ビジョンモデル（2026-06-06 時点の現行世代）

| モデルエイリアス | API ID（ピン止め） | 価格（入力/出力 MTok） | コンテキスト | 用途 |
|----------------|-----------------|----------------------|------------|------|
| `claude-haiku-4-5` | `claude-haiku-4-5-20251001` | $1 / $5 | 200k | 高速・低コスト・大量ページ処理向け |
| `claude-sonnet-4-6` | `claude-sonnet-4-6`（dateless pin） | $3 / $15 | 1M | バランス型・OCR メイン推奨 |
| `claude-opus-4-8` | `claude-opus-4-8`（dateless pin） | $5 / $25 | 1M | 最高精度・複雑レイアウト |

> **注意:** Claude 4.6 世代以降はモデル ID 自体がピン止めスナップショットであり、エバーグリーンポインタではない。エイリアスを使用しても安全。

#### 画像送信フォーマット（base64）

```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 4096,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": "<base64_encoded_string>"
          }
        },
        {
          "type": "text",
          "text": "この画像のテキストを書き出してください。"
        }
      ]
    }
  ]
}
```

サポートする `media_type`: `image/jpeg`・`image/png`・`image/gif`・`image/webp`
→ PageFolio は `page_to_png_b64()` で PNG 生成済みのため `image/png` で統一する。

#### レスポンス解析

```python
data = json.loads(body)
# content は type=="text" のブロックを走査する
for block in data["content"]:
    if block.get("type") == "text":
        return block["text"]
```

#### `temperature` と `effort` パラメータ

**確認結果（公式ドキュメント）:**

- `temperature` は **全モデルで利用可能**（0.0–1.0、デフォルト 1.0）。Opus 4.8 も同様。
  - 仕様書（`docs/OCRプロバイダ化_見積もり仕様.md`）の「Opus 4.7/4.8 は `temperature` 不可」という記載は **誤り**。`temperature` は全モデルで受け付ける。
- `effort` パラメータは **`output_config` の子フィールド**として指定する（トップレベルではない）。

```json
{
  "output_config": {
    "effort": "low"
  }
}
```

  - `effort` の有効値: `low` / `medium` / `high`（デフォルト）/ `xhigh` / `max`
  - `effort` サポートモデル: `claude-opus-4-8`・`claude-opus-4-7`・`claude-opus-4-6`・`claude-sonnet-4-6`・`claude-opus-4-5`
  - **`claude-haiku-4-5` は `effort` 非対応**（`temperature` のみで制御）
  - OCR 用途では `effort: "low"` でも十分（テキスト書き出しタスクは単純）。コスト・速度優先なら `low` を推奨。

#### モデル一覧取得

```
GET https://api.anthropic.com/v1/models
Headers: x-api-key, anthropic-version: 2023-06-01
```

レスポンス: `data[].id`・`data[].display_name`・`data[].capabilities.image_input.supported` で
ビジョン対応可否を判定できる。

---

### Gemini (Google AI Studio) API

**信頼度: HIGH** — `ai.google.dev/api/generate-content`・`ai.google.dev/gemini-api/docs/models/gemini-2.5-flash` から直接確認（2026-06-06）

#### エンドポイント・認証

```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
```

認証方式は2通り（どちらでも動作）:

| 方式 | 記法 | 推奨度 |
|------|------|-------|
| クエリパラメータ | `?key=$GEMINI_API_KEY` | urllib では URL 文字列に埋め込み可能 |
| リクエストヘッダー | `x-goog-api-key: $GEMINI_API_KEY` | ヘッダー方式が推奨（URL ログへの漏洩を防ぐ） |

**PageFolio の実装方針**: ヘッダー方式（`x-goog-api-key`）を採用し、URL にキーを含めない。

環境変数: `GEMINI_API_KEY`（フォールバック `GOOGLE_API_KEY`）

#### 推奨ビジョンモデル（2026-06-06 時点）

| モデル ID | 入力 | 出力トークン上限 | コンテキスト | 位置づけ |
|-----------|------|----------------|------------|---------|
| `gemini-2.5-flash` | テキスト・画像・動画・音声 | 65,536 | 1,048,576 | コスト効率最優先・OCR メイン推奨 |
| `gemini-2.5-pro` | テキスト・画像・動画・音声・PDF | 65,536 | 1,048,576 | 高精度・複雑レイアウト |

> `gemini-2.5-flash` は stable GA 版として `gemini-2.5-flash` ID で利用可能。
> 旧プレビュー ID `gemini-2.5-flash-preview-09-2025` は **廃止済み（2026-07-09 に完全シャットダウン予定）**。使用しないこと。

#### 画像送信フォーマット（inline_data）

```json
{
  "contents": [
    {
      "parts": [
        {
          "inline_data": {
            "mime_type": "image/png",
            "data": "<base64_encoded_string>"
          }
        },
        {
          "text": "この画像のテキストを書き出してください。"
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.1,
    "maxOutputTokens": 4096
  }
}
```

> **順序**: 公式ドキュメントにより「単一画像 + テキストの場合、テキストプロンプトを画像パートの後に置く」ことが推奨されている。

サポート `mime_type`: `image/png`・`image/jpeg`・`image/webp`・`image/heic`・`image/heif`
→ PageFolio は `image/png` で統一。

**リクエストサイズ制限**: inline_data 使用時は合計 20MB 以内（PNG 変換後の通常 PDF ページなら問題なし）。

#### `generationConfig` パラメータ

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `temperature` | float | ランダム性制御（OCR は 0.1 程度推奨） |
| `maxOutputTokens` | int | 出力トークン上限 |
| `stopSequences` | array | 停止文字列 |
| `candidateCount` | int | 候補数（通常 1） |

#### レスポンス解析

```python
data = json.loads(body)
return data["candidates"][0]["content"]["parts"][0]["text"]
```

#### モデル一覧取得

```
GET https://generativelanguage.googleapis.com/v1beta/models
Headers: x-goog-api-key: $GEMINI_API_KEY
```

レスポンス: `models[].name`（例: `"models/gemini-2.5-flash"`）、
`models[].supportedGenerationMethods` で `generateContent` 対応可否を確認できる。

---

### Tesseract OCR（オプション）

**信頼度: MEDIUM** — 公式リポジトリ + コミュニティ複数ソースで確認

#### ランタイム依存（pip 外）

Tesseract は **外部バイナリのインストールが必要**。PageFolio の `.exe` には同梱できない。

| コンポーネント | 必須/任意 | 備考 |
|-------------|---------|------|
| Tesseract OCR バイナリ（`tesseract.exe`） | 必須 | Windows は UB Mannheim 提供インストーラを使用 |
| `jpn.traineddata` | 横書き日本語に必須 | インストール時に「Additional language data」で追加 or 手動配置 |
| `jpn_vert.traineddata` | 縦書き日本語に任意 | 縦書きPDFを扱う場合に必要 |

#### 実装方式: `pytesseract` を使わず `subprocess.run` で直接呼び出す

`pytesseract` は薄いラッパーに過ぎず、pip 追加依存になる。
`subprocess.run` で `tesseract` CLI を直接呼び出す方式で **pip 依存ゼロ** を維持する。

```python
import subprocess
import tempfile
import os

def call_tesseract(png_bytes: bytes, lang: str = "jpn") -> str:
    """Tesseract CLI を subprocess 経由で呼び出す（pytesseract 不要）"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(png_bytes)
        tmp_path = f.name
    out_path = tmp_path.replace(".png", "")
    try:
        subprocess.run(
            ["tesseract", tmp_path, out_path, "-l", lang, "--psm", "6"],
            check=True,
            capture_output=True,
        )
        with open(out_path + ".txt", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError("Tesseract が見つかりません。インストールを確認してください。")
    finally:
        for p in [tmp_path, out_path + ".txt"]:
            if os.path.exists(p):
                os.unlink(p)
```

> `stdin/stdout` パイプ方式も技術的に可能だが、`-` 引数での PNG stdin は実装が不安定なため
> 一時ファイル方式を採用する（ページ単位で即削除するためディスク常駐しない）。

#### 解像度・スケール

- Tesseract は概ね 300 dpi 相当の入力を推奨。
- PageFolio の `ocr_scale` を `3.0` 以上（300 dpi 相当）に設定すべき。
- 既定 `ocr_scale=2.0` では精度が低下する可能性がある。Tesseract Provider 使用時は `ocr_scale` の推奨値を UI で明示する。

#### 精度の制約（仕様書の内容を確認・維持）

仕様書に記載の通り、Tesseract は VLM（Vision LLM）には及ばない前提でオプション扱い。
主な劣後要因:

- 複雑レイアウト（表・段組）に弱い
- 手書き文字・装飾フォントは認識率が下がる
- 前処理（二値化・傾き補正）なしでは顕著に精度低下

---

## 仕様書との差分サマリー

既存仕様書（`docs/OCRプロバイダ化_見積もり仕様.md`）の内容との差分を整理する。

| 項目 | 仕様書の記載 | 今回調査の確認結果 | 対応 |
|------|------------|-----------------|------|
| Claude `temperature` 可否 | 「Opus 4.7/4.8 は `temperature` 不可」 | **誤り。全モデルで利用可能**（0.0–1.0） | 仕様修正が必要 |
| Claude `effort` の場所 | `output_config.effort` として示唆 | **正しい**（`output_config: {effort: "low"}` がトップレベルに並ぶ形） | 確認済み |
| Gemini 認証 | `?key=API_KEY` or `x-goog-api-key` | **両方正しい**。ヘッダー方式を推奨 | 実装時はヘッダー採用を明記 |
| Gemini モデル推奨 | `gemini-2.5-flash` / `gemini-2.5-pro` | **正しい**（GA stable。旧 preview ID は廃止済み） | 実装で stable ID を使用 |
| Claude モデル一覧 | `/v1/models` | **正しい**（`capabilities.image_input.supported` でビジョン可否を判定可能） | 確認済み |
| Gemini モデル一覧 | `/v1beta/models` | **正しい**（`supportedGenerationMethods` で `generateContent` 確認） | 確認済み |
| Tesseract 実装 | 記載なし（`OCRProvider` 実装として想定） | `subprocess.run` + 一時ファイル方式で `pytesseract` 不要 | 追加仕様として確定 |

---

## Alternatives Considered

| 採用 | 不採用の代替案 | 不採用理由 |
|------|-------------|----------|
| `urllib.request` 直叩き | `anthropic` SDK | PyInstaller .exe 肥大化・隠れ依存取り込み |
| `urllib.request` 直叩き | `google-genai` SDK | 同上 |
| `subprocess.run` (Tesseract CLI) | `pytesseract` | pip 追加依存（PyInstaller 肥大化）。pytesseract は CLI ラッパーに過ぎず不要 |
| `subprocess.run` (Tesseract CLI) | `easyocr` | PyTorch 依存で著しく重い。.exe 組み込みは非現実的 |
| ヘッダー認証（Gemini） | URL クエリパラメータ認証 | URL ログ・プロセスリストへの API キー漏洩リスク |

---

## What NOT to Use

| 避けるもの | 理由 | 代替 |
|-----------|------|------|
| `anthropic` PyPI パッケージ | PyInstaller で依存ツリーが膨らみ .exe が大幅増量する | `urllib.request` 直叩き |
| `google-genai` PyPI パッケージ | 同上。さらに `grpc` 等の C 拡張を引き込む可能性 | `urllib.request` 直叩き |
| `pytesseract` PyPI パッケージ | CLI ラッパーに過ぎず、pip 依存を増やす価値がない | `subprocess.run(['tesseract', ...])` |
| `easyocr` PyPI パッケージ | PyTorch 依存で数 GB 級。.exe への組み込み不可 | Tesseract（オプション）または クラウド API |
| Gemini `gemini-2.5-flash-preview-09-2025` | 2026-07-09 廃止予定。すでに旧 stable に置き換え済み | `gemini-2.5-flash`（stable） |

---

## 実装パターン（urllib 直叩き共通骨格）

3 プロバイダ共通の `urllib` 呼び出しパターン（`call_lm_studio` の設計を踏襲）:

```python
import json
import socket
import urllib.error
import urllib.request

def _post_json(endpoint: str, payload: dict, headers: dict, timeout: int) -> dict:
    """共通 HTTP POST ユーティリティ（プロバイダ非依存）"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        endpoint,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_body or e.reason}") from e
    except socket.timeout as e:
        raise TimeoutError(f"timed out after {timeout}s") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, socket.timeout):
            raise TimeoutError(f"timed out after {timeout}s") from e
        raise ConnectionError(str(reason)) from e
```

---

## 環境変数規約

| プロバイダ | 一次参照 | フォールバック | 未設定時の挙動 |
|-----------|---------|-------------|-------------|
| Claude | `ANTHROPIC_API_KEY` | なし | ダイアログで「環境変数 `ANTHROPIC_API_KEY` が未設定です」と明示エラー |
| Gemini | `GEMINI_API_KEY` | `GOOGLE_API_KEY` | ダイアログで「環境変数 `GEMINI_API_KEY` が未設定です」と明示エラー |
| LM Studio | なし（ローカル） | — | — |
| Tesseract | なし（バイナリ検索） | — | `FileNotFoundError` を RuntimeError に変換してダイアログ表示 |

`pagefolio_settings.json` には **キーを一切書かない**。`os.environ.get()` で実行時に読むのみ。

---

## Sources

- `platform.claude.com/docs/en/api/messages` — Claude Messages API エンドポイント・ヘッダー・画像フォーマット（HIGH 信頼度）
- `platform.claude.com/docs/en/docs/about-claude/models` — Claude 現行モデル ID・価格・コンテキスト・vision 対応一覧（HIGH 信頼度）
- `platform.claude.com/docs/en/build-with-claude/effort` — `effort` パラメータ仕様・`output_config` 構造・対応モデル一覧（HIGH 信頼度）
- `platform.claude.com/docs/en/api/models/list` — `/v1/models` レスポンス形式・`capabilities.image_input` フィールド（HIGH 信頼度）
- `ai.google.dev/api/generate-content` — Gemini generateContent エンドポイント・inline_data フォーマット・generationConfig（HIGH 信頼度）
- `ai.google.dev/gemini-api/docs/models/gemini-2.5-flash` — gemini-2.5-flash GA stable ID・コンテキスト 1M・multimodal 確認（HIGH 信頼度）
- `ai.google.dev/gemini-api/docs/models/gemini-2.5-pro` — gemini-2.5-pro GA stable ID・コンテキスト 1M・multimodal 確認（HIGH 信頼度）
- `ai.google.dev/gemini-api/docs/vision` — inline_data 構造・parts 配列・20MB 上限・mime_type 一覧（HIGH 信頼度）
- `github.com/tesseract-ocr/tesseract` — Tesseract CLI インターフェース（HIGH 信頼度）
- `pypi.org/project/pytesseract/` + `github.com/madmaze/pytesseract` — pytesseract が CLI ラッパーに過ぎない理由の確認（MEDIUM 信頼度）

---

*Stack research for: PageFolio v1.4.0 OCR プロバイダ化 + クラウド API 対応*
*Researched: 2026-06-06*
