# Stack Research — v1.9.0「安全性・整合性の是正 + OpenAI プロバイダ追加」

**Domain:** Windows デスクトップ PDF エディタ（Tkinter・PyInstaller配布）への OpenAI(ChatGPT) OCR プロバイダ追加 + 暗号化保存修正 + Python 3.14 Tcl/Tk 環境修復
**Researched:** 2026-08-10
**Confidence:** MEDIUM（公式ドキュメントドメイン `developers.openai.com` + PyMuPDF ベンダーブログ `artifex.com` を複数コミュニティ情報源とクロス照合。実機コード確認は本リポジトリで直接実施し HIGH 相当）

> 本ファイルは v1.9.0 マイルストーンの**新規作業（OpenAI プロバイダ実装・暗号化保存維持・Python 3.14 Tkinter 環境修復）に必要なスタック差分のみ**を扱う。既存で検証済みの周辺技術（`OCRProvider` 抽象化・urllib 直叩き方針・`registry.py` の独立性制約・Claude/Gemini/LM Studio/Tesseract/Ollama/RunPod の6プロバイダ実装・PyMuPDF 基本操作・pytest/ruff 体制）は再調査していない。v1.8.0 までのスタック調査は `.planning/milestones/` 配下のアーカイブまたは git 履歴上の旧 STACK.md を参照。

---

## Recommended Stack

### Core Technologies（v1.9.0 で追加・変更が必要な範囲）

| Technology | Version / Endpoint | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| OpenAI **Chat Completions API** | `POST https://api.openai.com/v1/chat/completions` | OpenAI(ChatGPT) OCR プロバイダの画像 OCR・テキストサマリ送信先 | 既存の `RunPodProvider`（`pagefolio/ocr_providers/runpod.py`）が**すでに OpenAI 互換 Chat Completions 形状**（`messages[].content[].image_url.url` に data URL、`choices[0].message.content` で受信）で実装済み。OpenAI 公式は新規プロジェクトに Responses API を推奨するが、Chat Completions は「無期限サポート・廃止予定なし」と明言されており、既存5プロバイダのパターン（urllib 直叩き・`_raise_mapped_http_error`・`choices[0].message` 形状に近い応答パース）と最小差分で統合できる Chat Completions を採用する（下記「エンドポイント選択」参照）。 |
| OpenAI `/v1/models` (`GET`) | `GET https://api.openai.com/v1/models` | LLM設定ダイアログのモデル一覧取得（`list_models()`） | 既存 Claude/Gemini/RunPod と同型の「モデル一覧を非同期取得してドロップダウンに反映」導線に合わせる。ただし応答に `capabilities`（Claude）や `supportedGenerationMethods`（Gemini）に相当する **vision 対応フラグが存在しない** ため、Claude/Gemini のような自動フィルタは不可（後述 Pitfall）。 |
| `urllib.request` のみ（新規 pip 依存なし） | 標準ライブラリ | OpenAI API 実装手段 | **urllib のみで実装可能: YES**。OpenAI API は素の REST/JSON（`Authorization: Bearer` ヘッダ + JSON body）であり、公式 `openai` SDK 特有の機能（ストリーミングヘルパー等）を使わない限り urllib で完全に代替できる。既存 `RunPodProvider`/`ClaudeProvider`/`GeminiProvider` が同方式で実装済みであり、V14-D-01（新規 pip 依存ゼロ・PyInstaller 肥大化回避）を継続できる。 |

### Environment Fix（新規ライブラリではないが v1.9.0 の必須作業）

| 対象 | 現状 | 対応方針 |
|------|------|---------|
| Python 3.14.6 / Tkinter (`init.tcl` 読み込み失敗) | 本リサーチで実機再現を試みたが、現行 `.venv`（`C:\Users\shdwf\work\project\PageFolio\.venv`, Python 3.14.6）では `tkinter.Tk()` 単体実行・`pytest -k "batch_ocr"`・`pytest -k "ocr_dialog or plugin or shortcuts or toast"` のいずれも `_tkinter.TclError` は再現せず（後者は別原因の `PermissionError: [WinError 5]`＝pytest の一時ディレクトリ `%TEMP%\pytest-of-shdwf` へのアクセス拒否で 32 件エラー。init.tcl とは無関係の環境要因、Windows Defender 等のロック競合が疑わしい）。 | 恒久対策として **`TCL_LIBRARY`/`TK_LIBRARY` 環境変数の明示設定**を conftest.py または起動コードに組み込む（`sys.base_prefix` 配下の `tcl/tcl8.6/init.tcl` を `glob` で解決）。原因は Python 3.14 系で複数報告されている Tcl/Tk ライブラリパス解決不具合（`python-build-standalone` issue #913 は 3.14.0/3.14.1 で発生、CPython issue #125235 は venv 使用時に `TCL_LIBRARY` が venv 相対パスに誤解決される既知バグ、3.13 系はバックポート済み・3.14 系での修正状況は未確認）。PageFolio は `.venv` 経由で pytest を実行する構成のため、venv 相対パス誤解決が最有力候補。フェーズ実行時に実機で再現条件（cwd・実行者・antivirus状態）を切り分けたうえで、`TCL_LIBRARY`/`TK_LIBRARY` の明示設定 + 起動時に `tkinter.Tk()` を試行し失敗なら診断メッセージを出すフォールバックを検討する。 |

### Supporting Libraries

なし（新規 pip 依存追加は行わない方針を維持。`requirements.txt` の既存ピン: `PyMuPDF==1.28.0` / `Pillow==12.3.0` / `tkinterdnd2==0.6.2` / `pyinstaller==6.21.0` / `pytest==9.1.1` / `ruff==0.15.20`。インストール済み `fitz.version` 実測値 `('1.28.0', '1.29.0', None)`＝PyMuPDF 1.28.0・MuPDF 1.29.0 で確認済み）。

### Development Tools

変更なし（`ruff` / `pytest` の既存体制を継続。GUI テストの `init.tcl` 起因セットアップエラー修復のみが v1.9.0 の新規タスク）。

---

## OpenAI(ChatGPT) プロバイダ実装仕様

### 1. エンドポイント選択: Chat Completions vs Responses API

| 観点 | Chat Completions（推奨） | Responses API（OpenAI 公式が新規プロジェクトに推奨） |
|------|--------------------------|------------------------------------------------------|
| 画像入力形状 | `content: [{"type":"image_url","image_url":{"url":"data:image/png;base64,...","detail":"auto"}}, {"type":"text","text":prompt}]` | `input: [{"role":"user","content":[{"type":"input_image","image_url":"data:...","detail":"auto"},{"type":"input_text","text":prompt}]}]` |
| 応答形状 | `choices[0].message.content`（文字列） | `output[].content[].text`、または SDK 専用の `output_text` 集約フィールド（生 JSON には無く urllib 直叩きでは自前結合が必要） |
| 途切れ検出 | `choices[0].finish_reason == "length"` | `output[].status` 等（フィールド名がプロバイダごとに異なり要検証） |
| 既存コードとの親和性 | **`RunPodProvider` と実質同一形状**（`image_url`/`choices[0].message.content`/`finish_reason`）。`_extract_text` 相当のパースをほぼ流用できる | 応答パースを新規に書き起こす必要があり、`ClaudeProvider`/`GeminiProvider` とも異なる第3の応答形状が増える |
| サポート方針 | OpenAI 公式が「無期限サポート・廃止予定なし」と明言 | 新規機能はこちらに優先投入される傾向（agentic tool 等） |

**判断: Chat Completions API を採用する。**
理由: (1) 無期限サポートが公式に明言されており廃止リスクがない、(2) 既存 `RunPodProvider` が事実上同一の Chat Completions 互換形状で実装済みのため、OpenAI プロバイダは実質「エンドポイントを固定し認証ヘッダを差し替えた RunPodProvider の派生」として最小差分で実装できる、(3) V190-REV-08（プロバイダメタデータの分散是正）の直後に追加する以上、既存5プロバイダと一貫した実装パターン（`_post_payload` → `_raise_mapped_http_error` → JSON パース）を保つことが保守性上望ましい。Responses API への移行は「新規追加」ではなく将来の全プロバイダ横断リファクタとして別マイルストーンで検討すべき事項であり、v1.9.0 のスコープ外とする。

### 2. リクエスト/レスポンス形状（Chat Completions・画像あり）

```
POST https://api.openai.com/v1/chat/completions
Headers:
  Content-Type: application/json
  Authorization: Bearer {OPENAI_API_KEY}

Body:
{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,{b64_png}",
            "detail": "auto"
          }
        },
        {"type": "text", "text": "{prompt}"}
      ]
    }
  ],
  "max_completion_tokens": 4096
}
```

応答（成功時）:

```json
{
  "id": "chatcmpl-...",
  "choices": [
    {
      "message": {"role": "assistant", "content": "OCR結果テキスト"},
      "finish_reason": "stop"
    }
  ]
}
```

`ClaudeProvider._extract_text` / `RunPodProvider.ocr_image` と同型で `result["choices"][0]["message"]["content"]` を取り出し、`finish_reason == "length"` を `truncated` 判定に使う（`ocr_image_ex`/`complete_text_ex` の (text, truncated) 契約に合わせる）。

**base64 画像の渡し方**: `image_url.url` に `data:image/png;base64,{b64_png}` の data URL 文字列を渡す（`b64_png` は既存 `ocr.py` が生成する base64 PNG をそのまま流用可能）。`detail` は `"auto"`（既定）/`"low"`/`"high"` の3値。OCR 用途はページ全体の文字を読み取るため既定 `"auto"` または `"high"` を推奨（`"low"` は低解像度へダウンサンプルされ小さい文字の OCR 精度が落ちるリスクがある）。

### 3. 認証ヘッダ・環境変数

- `Authorization: Bearer {OPENAI_API_KEY}` — 必須。既存 `RunPodProvider`/`ClaudeProvider` と同じ「ヘッダ1本で完結する」パターン。
- `OpenAI-Organization` / `OpenAI-Project` ヘッダ — **単一組織・個人利用では不要**（公式ドキュメント: 複数組織所属時のみ必要）。v1.9.0 の実装では追加しない（既存プロバイダにも組織/プロジェクト概念の入力欄がなく、UI 複雑化を避ける）。将来要望があれば `registry.py` 相当の非機密メタデータ拡張で対応可能。
- 環境変数名: **`OPENAI_API_KEY`**（業界標準の慣例名。`registry.py` の `PROVIDER_ENV_KEYS` へ `"openai": ("OPENAI_API_KEY",)` を追加。Gemini のような複数候補フォールバックは不要）。

### 4. モデル一覧取得（`GET /v1/models`）

```
GET https://api.openai.com/v1/models
Authorization: Bearer {OPENAI_API_KEY}
```

応答:

```json
{
  "object": "list",
  "data": [
    {"id": "gpt-4o-mini", "object": "model", "created": 1686935002, "owned_by": "system"}
  ]
}
```

**重要な差分（Claude/Gemini との非対称性）**: Anthropic の `/v1/models` は `capabilities.image_input.supported`、Gemini の `/v1beta/models` は `supportedGenerationMethods` を返し、`ClaudeProvider.list_models()`/`GeminiProvider.list_models()` はこれで vision 対応モデルのみへ絞り込んでいる。**OpenAI の `/v1/models` にはモデル能力（vision/embedding/audio 等）を示すフィールドが存在しない**（コミュニティでも「`/v1/models` にモデル能力を公開してほしい」という機能要望が未実装のまま挙がっている）。そのため `OpenAIProvider.list_models()` は Claude/Gemini と同じ「フィルタして返す」実装ができず、以下のいずれかで妥協する必要がある:
  - (a) 全モデル ID をそのまま返し、埋め込み・音声・画像生成系モデル名（`embedding`/`whisper`/`tts`/`dall-e`/`moderation` 等の文字列パターン）だけを除外する簡易フィルタ
  - (b) API キー未設定時と同様、`RECOMMENDED_MODELS` 静的リストのみを返す（フィルタ不能である旨を UI に注記）

  実装コストとモデル一覧の陳腐化リスクを比較し、**(a) の名前ベース除外フィルタ**を推奨する（Claude/Gemini ほど正確ではないが、キー未設定時のフォールバックと組み合わせれば実用上十分）。

### 5. モデルラインナップと既定モデル

**確実に vision 対応と確認できたモデル**（複数情報源でクロス確認・価格情報つき）: `gpt-4o`（旗艦・vision 対応）、`gpt-4o-mini`（低コスト版）、`gpt-4.1`（テキスト+画像入力）。より新しい世代（`gpt-5` 系）も vision 対応と報告されているが、**モデル名の詳細ラインナップ（サブバリアント名等）は変動が速く、本リサーチ時点の Web 情報の信頼度が低い**ため、実装時に `developers.openai.com/api/docs/models` を再確認すること。

- **既定モデル推奨**: `gpt-4o-mini`。理由: Gemini プロバイダの既定が低コスト・高速枠の `gemini-2.5-flash` であることと平仄を合わせ、OCR は高頻度・低複雑度タスクであるため mini/flash 系のコスト最適モデルを既定とする方針が一貫する（Claude は `claude-sonnet-4-6` を既定にしているが、これは effort パラメータで精度を調整できる設計のため単純比較はしない）。
- **`RECOMMENDED_MODELS` 静的フォールバック**（Claude/Gemini と同型・APIキー未設定時に返す）: `["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"]` を暫定案とし、実装時に最新の vision 対応モデルへ更新すること（Gemini の `RECOMMENDED_MODELS` コメントに倣い「実機検証済み」と明記できるよう、実装フェーズで最低1モデルは実 API 疎通確認を行う）。

### 6. max_tokens 相当パラメータ

| パラメータ名 | 対応 API | 状態 |
|-------------|---------|------|
| `max_tokens` | Chat Completions | **非推奨**（deprecated）。o-series 推論モデルでは使用不可 |
| `max_completion_tokens` | Chat Completions | **採用**。全チャットモデル（gpt-4o/4.1/gpt-5/o-series 含む）で動作する後継パラメータ |
| `max_output_tokens` | Responses API | Chat Completions を採用するため本実装では不使用 |

既存 `build_provider()` の `mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS)); mt = 4096 if mt <= 0 else mt`（Claude/Gemini/RunPod 共通パターン）をそのまま踏襲し、`max_completion_tokens=mt` として送信する。

**temperature の扱い（Claude の `_supports_temperature`/Gemini の `_is_legacy_gemini` と同型の分岐が必要）**: OpenAI の o-series 推論モデル（`o1`/`o3`/`o4-mini` 等）は `temperature` パラメータを拒否し（`400 Unsupported parameter: 'temperature'`、または既定値 1 以外を拒否）、GPT-4o/GPT-4.1/GPT-5（非 o-series）の通常チャットモデルは `temperature` を通常どおり受け付ける。`OpenAIProvider` は Claude の `EFFORT_MODELS`/`_supports_temperature()` と同型の「モデル名が `o1`/`o3`/`o4` 系プレフィックスに一致するか」判定ヘルパーを設け、o-series では `temperature` を省略し、既定チャットモデルでは送信する分岐を実装すること（未知モデルは安全側で省略＝Claude の D-16 前方互換パターンを踏襲）。

### 7. レート制限・429・Retry-After

OpenAI の 429 応答には **`Retry-After` ヘッダが付与される**（組織単位でのレート制限。トークン数/リクエスト数の複合要因）。既存の共有ヘルパー `pagefolio/ocr_providers/errors.py` の `_raise_mapped_http_error()`/`parse_retry_after()` は **ヘッダ名 `Retry-After` を汎用的に読む実装**であり、OpenAI 固有の対応コードを追加する必要はない。429/5xx は `OCRRetryableError(retry_after=...)` へ自動的にマッピングされ、`ocr_pipeline.py` の `clamp_retry_after`/`interruptible_sleep`（60秒上限・キャンセル確認付き待機）にそのまま乗る。**既存基盤の再利用のみで対応可能**（新規コード不要）。

### 8. urllib.request のみで実装可能か — 判定: **YES**

根拠:
- OpenAI API は標準的な HTTPS + JSON REST（`Content-Type: application/json` + `Authorization: Bearer`）であり、公式 `openai` SDK が提供する付加価値（型付きレスポンス、自動リトライ、ストリーミングヘルパー、Organization切替の簡便化）はいずれも urllib + 標準 `json` モジュールで代替可能。
- 既存 `RunPodProvider` が「OpenAI 互換 Chat Completions API」を**すでに urllib で実装済み**であり、実質的に実装パターンが実証済み。
- `urllib.request.Request` + `urllib.error.HTTPError`/`URLError` + `socket.timeout` の例外マッピングパターン（`ClaudeProvider`/`GeminiProvider`/`RunPodProvider` 共通）をそのまま流用できる。
- `_require_http_scheme()`（`base.py`）はユーザー入力 URL を持つプロバイダ向けだが、OpenAI は固定エンドポイントのため不要（Claude/Gemini と同様に URL 入力欄なし）。

新規 pip 依存（`openai` パッケージ等）は不要であり、V14-D-01（新規 pip 依存ゼロ）を維持できる。

---

## PyMuPDF 暗号化維持保存（V190-REV-01 対応の技術的裏付け）

### `Document.save()` / `Document.tobytes()` の暗号化関連パラメータ

| パラメータ | 意味 |
|-----------|------|
| `encryption=` | 暗号化方式（`fitz.PDF_ENCRYPT_KEEP` / `fitz.PDF_ENCRYPT_NONE` / `fitz.PDF_ENCRYPT_RC4_128` / `fitz.PDF_ENCRYPT_AES_256` 等）。**未指定時は無暗号化で保存される（=現在の V190-REV-01 バグの直接原因）** |
| `owner_pw=` / `user_pw=` | 新規パスワードを明示設定する場合に使用。UTF-8 40文字以下 |
| `permissions=` | 権限ビットフィールド（`PDF_PERM_ACCESSIBILITY` を含める） |
| `incremental=` | `True` で追記保存（高速）。`outfile` は `Document.name`（元ファイルパス）と一致必須 |

**`encryption=fitz.PDF_ENCRYPT_KEEP` の挙動**: `owner_pw`/`user_pw` を再指定せずとも、**認証済みドキュメントの元の暗号化方式・パスワードをそのまま維持して保存できる**。`Document.save()` と `Document.tobytes()` の両方が同じ `encryption`/`owner_pw`/`user_pw`/`permissions` 引数セットを受け付ける（`tobytes()` も encryption 対応・v1.16.0 で追加、v1.18.3 で owner_pw 未指定時に user_pw を流用する挙動に変更）。

**「名前を付けて保存」（新規パス）への適用**: 非インクリメンタル保存で新しいファイル名へ書き出す場合でも `doc.save(new_path, encryption=fitz.PDF_ENCRYPT_KEEP)` で暗号化を維持できる（インクリメンタル不要）。これは `pagefolio/file_ops.py` の `_save_as()`（V190-REV-01 の主対象）にそのまま適用できる修正パターンである。

**インクリメンタル保存（`_overwrite_current_file()` の主経路）**: `doc.save(doc.name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)` が公式ブログのサンプルコードとして提示されている。ただし `incremental=True` は `Document.can_save_incrementally()` が `True` を返す場合のみ有効（破損PDF・新規作成PDF・一部の構造変更後は不可）。**インクリメンタル保存に失敗した際のフォールバック**（`_overwrite_current_file()` が使う `doc.tobytes(**save_kwargs)` 再生成パス）についても、`save_kwargs` に `encryption=fitz.PDF_ENCRYPT_KEEP` を含めることで同様に暗号化を維持できる（`tobytes()` も同じパラメータ規約のため）。

**注意点（要実機検証項目として明記）**: 複数のコミュニティ情報源間で「暗号化済みファイルはインクリメンタル保存不可」という記述と「`PDF_ENCRYPT_KEEP` + `incremental=True` の組み合わせは `can_save_incrementally()==True` の場合に可能」という記述が両方存在し、完全には一致しない（ドキュメントのバージョンやリビジョンで挙動が変わった可能性がある）。**実装フェーズでは、パスワード保護PDFを実際に開いて `doc.can_save_incrementally()` の戻り値と、`incremental=True + PDF_ENCRYPT_KEEP` での保存結果を実機確認すること**（V190-REV-01 の推奨対応にある「暗号化PDFのSave Asとインクリメンタル保存失敗フォールバックの回帰テスト追加」で自然にカバーされる）。

### `Document.authenticate()` 後に元の暗号化パラメータを取得できるか

明確な公式ドキュメント記述は確認できなかった（本リサーチの Gap）。ただし `PDF_ENCRYPT_KEEP` は「暗号化方式やパスワードを呼び出し側が再取得・再指定する必要がない」設計になっており、**`_save_as()`/`_overwrite_current_file()` は独自の暗号化検出ロジックを持つ必要がなく、単に `encryption=fitz.PDF_ENCRYPT_KEEP` を渡すだけで足りる**（実装上の代替策として十分・追加の API 調査は不要）。「保存後も `pdf_has_password` の状態が更新されない」という V190-REV-01 の副次課題は、`Document.needs_pass`（保存前の認証要求有無を示す既存プロパティ）を保存後に再チェックする形で解消できる可能性が高いが、これはコード実装時に `pagefolio/file_ops.py` の既存ロジックと合わせて確認すること。

---

## 統合ポイント（既存コードとの接続箇所）

V190-REV-08（プロバイダメタデータ分散是正）の直後に実施する前提で、以下のファイルに `openai` エントリを追加する:

| ファイル | 追加内容 |
|---------|---------|
| `pagefolio/ocr_providers/openai_provider.py`（新規） | `OpenAIProvider(OCRProvider)` — `RunPodProvider` を土台に、固定エンドポイント（`https://api.openai.com/v1/chat/completions`・`/v1/models`）・`OPENAI_API_KEY` 認証・`max_completion_tokens`・o-series 向け `temperature` 省略分岐を実装 |
| `pagefolio/ocr_providers/registry.py` | `PROVIDER_ENV_KEYS` に `"openai": ("OPENAI_API_KEY",)` を追加（標準ライブラリ `os` のみ依存の制約は変更なしで満たせる） |
| `pagefolio/ocr.py`（`build_provider`） | `elif name == "openai":` 分岐を追加（Claude/Gemini と同型の `mt <= 0 → 4096` クランプ・`api_key or ""` 注入パターンを踏襲）。あわせて V190-REV-02（`"off"` を LM Studio 扱いする現行バグ、`name in ("lmstudio", "", "off")` 分岐）の修正が本項の前提となる |
| `pagefolio/ocr.py`（`PROVIDER_OCR_PROMPTS`/`PROVIDER_SUMMARY_PROMPTS`） | 任意: OpenAI 向けプロンプト最適化（XML風 or 明示指示）を追加するか、汎用プロンプトへフォールバックさせるか判断（V16-AI-02 の既存方針では claude/gemini のみ個別定義・それ以外は汎用へフォールバックのため、MVP では追加不要） |
| `pagefolio/dialogs/llm_config/sections.py` | プロバイダ選択肢・フォールバック候補一覧に `openai` を追加 |
| `pagefolio/dialogs/llm_config/dialog.py` / `model_fetch.py` | 設定収集・モデル一覧非同期取得（`_fetch_models_async`）の対象に追加。`model_list_timeout` は Claude/Gemini 同様 30 秒を推奨（クラウド API のネットワーク遅延を見込む・RunPod の 90 秒ほどコールドスタートを要しない） |
| `pagefolio/ocr_dialog.py` | 表示名・モデル・送信先確認・APIキー入力欄の追加 |
| `pagefolio/dialogs/batch_ocr.py` | クラウド判定・コスト確認・送信先表示への追加 |
| `pagefolio/lang.py` | 表示文言（ja/en 両方に同一キー追加・既存ルール準拠） |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| Chat Completions API（画像OCR） | Responses API | 将来的に全プロバイダを Responses 相当の統一インターフェースへ刷新する別マイルストーンを立てる場合、または OpenAI がエージェント機能（web_search/file_search/MCP等）を OCR パイプラインへ統合する要望が出た場合 |
| `max_completion_tokens` | `max_tokens` | 使用しない（非推奨・o-series で使用不可のため） |
| 名前ベース除外フィルタ（`list_models()`） | 静的 `RECOMMENDED_MODELS` のみ返す | 実装コストを最小化したい場合や、OpenAI モデル名の変動リスクを完全に避けたい場合 |
| `OPENAI_API_KEY` 単独 | `OpenAI-Organization`/`OpenAI-Project` ヘッダ追加 | ユーザーから「複数組織のキーを切り替えたい」という要望が出た場合のみ、`registry.py` 相当の非機密メタデータへ拡張 |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| 公式 `openai` Python SDK（pip パッケージ） | PyInstaller バイナリ肥大化・新規 pip 依存追加は v1.9.0 の制約（`urllib` 直叩き・新規 pip 依存ゼロ）に反する。既存5プロバイダとの実装方針一貫性も崩れる | `urllib.request` 直叩き（本ドキュメントの実装仕様どおり） |
| `max_tokens`（Chat Completions） | 非推奨・o-series モデルで 400 エラー | `max_completion_tokens` |
| Responses API の `output_text` フィールドへの依存 | 生 JSON レスポンスには存在せず SDK 側の集約ヘルパーであり、urllib 直叩きでは自前結合が必要になり実装が複雑化する（そもそも本実装では Chat Completions を採用するため無関係） | Chat Completions の `choices[0].message.content` |
| `Document.save()` で `encryption` 引数を省略したまま暗号化PDFを保存 | 暗号化が外れて平文保存される（V190-REV-01 の直接原因） | `encryption=fitz.PDF_ENCRYPT_KEEP`（保存経路統一） |
| Python 3.14 の Tcl/Tk エラーを「コード不具合」と誤診断してアプリケーションコードを変更すること | 既存機能レビュー・本リサーチともに、実行環境（venv の Tcl パス解決・antivirus 起因の一時ディレクトリロック等）に起因する可能性が高いことを確認済み | `TCL_LIBRARY`/`TK_LIBRARY` 環境変数の明示設定 + 実行環境の切り分け（フェーズ実行時に実機再現条件を特定） |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| PyMuPDF `1.28.0`（本リポジトリ実測 `fitz.version == ('1.28.0', '1.29.0', None)`） | Python 3.14.6 | `encryption=`/`owner_pw=`/`user_pw=`/`permissions=` は `save()`/`tobytes()` 両方に古くから存在する安定 API（v1.16.0〜）であり本バージョンでの非互換リスクは低い |
| OpenAI Chat Completions API | 認証ヘッダ形式・エンドポイントパスは長期安定（Chat Completions は無期限サポート表明） | モデル名・`RECOMMENDED_MODELS` の具体的な ID は変動が速いため実装フェーズで再確認が必要 |
| Python 3.14.6 / Tkinter（Tcl/Tk 8.6 系、本リポジトリ実測 `Python314/tcl/tcl8.6` 同梱確認済み） | Windows 11 | 現行 `.venv` では動作確認済み（本リサーチで実機再現せず）。CI/別マシン/別ユーザー権限での再現有無は未確認 — フェーズ実行時に要再検証 |

---

## Confidence Assessment

| 項目 | 確信度 | 理由 |
|------|--------|------|
| OpenAI Chat Completions の画像入力形状・エンドポイント | MEDIUM | `developers.openai.com`（公式ドメイン）を含む複数情報源で一致。ただし WebFetch 経由の要約に一部変動しやすいモデル名列挙が混じるため、モデル名の細部は実装時に再確認を推奨 |
| `max_tokens` → `max_completion_tokens` の非推奨化・o-series の `temperature` 制約 | MEDIUM〜HIGH | 複数の独立情報源（コミュニティ・GitHub issue・公式ヘルプセンター）で一致した記述が多数 |
| PyMuPDF `PDF_ENCRYPT_KEEP` の挙動 | MEDIUM | PyMuPDF 公式ベンダーブログ（artifex.com）のコード例で裏付けあり。ただし「暗号化済みドキュメントのインクリメンタル保存可否」は情報源間で細部が食い違うため実装時の実機検証が必須 |
| Python 3.14 Tcl/Tk 問題の根本原因 | LOW〜MEDIUM | 複数の類似 issue が存在するが根本原因はビルド／実行環境依存で一意に特定できず、本リポジトリの実機では再現しなかった（別のPermissionErrorが混入し診断が複雑化） |
| OpenAI `/v1/models` に vision 能力フラグがないこと | MEDIUM | コミュニティの機能要望スレッドで「未実装」と明言されており、Claude/Gemini との非対称性は実装上重要な制約として確度が高い |

## Gaps to Address

- OpenAI モデルラインナップ（vision 対応の正確なモデル ID 一覧・既定モデルの最終決定）は情報の陳腐化が速いため、**実装フェーズ開始時に `GET /v1/models` を実キーで一度呼び出し、実在するモデル名を確認してから `RECOMMENDED_MODELS` を確定**すること。
- `Document.authenticate()` 後に元の暗号化方式（AES-256 か RC4-128 か等）を明示的に問い合わせる API の有無は未確認（ただし `PDF_ENCRYPT_KEEP` を使う限り実装上は不要）。
- PyMuPDF の「暗号化済みドキュメントに対する `incremental=True` + `PDF_ENCRYPT_KEEP`」の可否は情報源間で細部の食い違いあり。V190-REV-01 の回帰テスト実装時に実機で確定させること。
- Python 3.14 の Tcl/Tk 問題は本リサーチのセッションでは再現せず、根本原因を一意に特定できなかった。フェーズ実行時に「どの実行コンテキスト（CI/手動実行/特定ユーザー）で発生するか」を切り分けたうえで対応要否を判断すること。あわせて、今回発見した無関係な `PermissionError`（pytest 一時ディレクトリのロック競合）も別途切り分けが必要。

## Sources

- [Migrate to the Responses API | OpenAI API](https://developers.openai.com/api/docs/migrate-to-responses) — Chat Completions と Responses API の位置づけ（MEDIUM）
- [Images and vision | OpenAI API](https://developers.openai.com/api/docs/guides/images-vision) — 画像入力（`input_image`/`image_url`/`detail`）の形状（MEDIUM）
- [List models | OpenAI API Reference](https://developers.openai.com/api/reference/resources/models/methods/list) — `GET /v1/models` の応答形状（MEDIUM）
- OpenAI 認証ヘッダ（`Authorization: Bearer`・`OpenAI-Organization`）— OpenAI API Reference・コミュニティ複数情報源クロス確認（MEDIUM）
- `max_tokens`→`max_completion_tokens` 非推奨化・o-series `temperature` 制約 — OpenAI Developer Community 複数スレッド + GitHub issue クロス確認（MEDIUM）
- 429/`Retry-After` の挙動 — OpenAI API エラーコードガイド相当ページ（MEDIUM）
- [How to Save a PDF Document with PyMuPDF: Encryption and Much More! | Artifex](https://artifex.com/blog/how-to-save-a-pdf-document-with-pymupdf-encryption-incremental-saving) — `PDF_ENCRYPT_KEEP`・`incremental`・`save()`/`tobytes()` パラメータのコード例（MEDIUM・PyMuPDF 公式ベンダー発信）
- [Document - PyMuPDF - Read the Docs](https://pymupdf.readthedocs.io/en/latest/document.html) — `Document.save()`/`authenticate()` の一次情報源（参照試行・要約が断片的なため実装時の再確認を推奨）
- [python/cpython#125235](https://github.com/python/cpython/issues/125235) — venv 環境での `TCL_LIBRARY` 誤解決バグ（3.13系で修正・3.14系の状況は未確認、MEDIUM）
- [astral-sh/python-build-standalone#913](https://github.com/astral-sh/python-build-standalone/issues/913) — Python 3.14.0/3.14.1 での init.tcl 問題報告（LOW〜MEDIUM）
- 本リポジトリ実機確認: `pagefolio/ocr_providers/{claude,gemini,runpod,registry,base,errors}.py` 読解、`.venv`（Python 3.14.6）での `tkinter.Tk()` 直接実行・`pytest -k "batch_ocr"` / `pytest -k "ocr_dialog or plugin or shortcuts or toast"` 実行結果、`requirements.txt`・`fitz.version` 実測 — HIGH（一次情報源・コードベース直接確認）

---
*Stack research for: PageFolio v1.9.0（OpenAI OCR プロバイダ追加・暗号化保存維持・Python 3.14 Tcl/Tk 環境修復）*
*Researched: 2026-08-10*
