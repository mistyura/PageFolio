# Pitfalls Research

**Domain:** デスクトップ PDF アプリへのマルチプロバイダ クラウド OCR 追加（Python/Tkinter/PyInstaller）
**Researched:** 2026-06-06
**Confidence:** HIGH（コードベース直接調査 + 公式ドキュメント確認済み）

---

## Critical Pitfalls

### Pitfall 1: APIキーの平文漏洩

**What goes wrong:**
`pagefolio_settings.json` に `api_key` フィールドを保存するコードを書いてしまう。設定ダイアログの入力値を他の設定値と同様に `_save_settings(settings)` へ渡すだけで起きる。`settings.py` の `_save_settings` は辞書をそのまま JSON ダンプするため、キーが含まれていれば即座に平文ファイルへ書き込まれる。

**Why it happens:**
既存の `settings.py` パターン（`settings["lm_studio_url"]` など）を踏襲してそのまま API キーを格納しようとするため。UI ダイアログで入力を受け取り、`self.settings["anthropic_api_key"] = entry.get()` と書いた瞬間に次の保存サイクルでファイルへ流れ込む。

**How to avoid:**
- APIキーは `os.environ.get("ANTHROPIC_API_KEY")` / `os.environ.get("GEMINI_API_KEY")` のみから読む。プロセス内メモリ保持は許容だが、`_save_settings()` を呼ぶ前に辞書からキー項目を削除するガード関数を設ける。
- `settings.py` の `_save_settings` の冒頭に `NEVER_PERSIST_KEYS = {"anthropic_api_key", "gemini_api_key"}` を定義し、`{k: v for k, v in settings.items() if k not in NEVER_PERSIST_KEYS}` をダンプするよう変更する。
- `logger.debug("settings: %s", settings)` 等でキーが含まれた辞書をログ出力しないよう注意する。`repr(settings)` でも同様。
- ダイアログ入力欄で受け取ったキーはメモリ変数（`_session_api_key`）に保持し、ダイアログ破棄時にはクリアする。

**Warning signs:**
- `pagefolio_settings.json` に `api_key`, `anthropic`, `gemini`, `secret`, `token` などの文字列が含まれている。
- `git diff` や `git log -p` でキーが含まれたファイルがコミットされている。
- ログファイルに `sk-ant-`, `AI...` 等の文字列が含まれる。

**Phase to address:**
Phase 2（Claude Provider 実装）の着手直前。`_save_settings` のガード処理と環境変数専用読み取り関数を Phase 2 の最初のタスクとして実装する。

---

### Pitfall 2: fitz.Document をワーカースレッドに渡す

**What goes wrong:**
`_worker` メソッドが `self.doc` を直接参照して `self.doc[page_idx]` を呼び出している（現在の `ocr_dialog.py` L475: `b64 = page_to_png_b64(self.doc[page_idx], scale=scale)` ）。これは OCRDialog の `__init__` で `self.doc = doc` として保持している同一オブジェクトを、`threading.Thread` 上から操作している。PyMuPDF 公式ドキュメントは「PyMuPDF does not support running on multiple threads — doing so may cause incorrect behaviour or even crash Python itself」と明言している。現行コードがなぜ動いているかは MuPDF の実装詳細に依存しており、保証されていない。

**Why it happens:**
既存の `_worker` は単一の `fitz.Document` を参照しながらページを逐次レンダリングしており、明示的な並列 `get_pixmap` は行っていないが、Tkinter の `after()` コールバックと `threading.Thread` が同じ `self.doc` を共有している構造になっている。プロバイダ化でレンダリングロジックを移動する際にこの前提を崩しやすい。

**How to avoid:**
- `fitz.Document` オブジェクトはメインスレッド（またはシングルスレッドで動くレンダリング専用ループ）からのみ操作する。
- `_worker` スレッド内では `get_pixmap` を呼ばず、**レンダリング済みの `bytes`（PNG データ）** のみを受け取る設計にする。具体的には、レンダリングをメインスレッドから `after()` で逐次実行し、完了した bytes をキューに入れ、ワーカーがキューを消費してクラウド API に送信する pipeline 構成にする。
- あるいは、仕様書案（§4.3）の「レンダリング→送信→破棄」逐次化を採用し、`_worker` 内でレンダリングと送信を直列に実行する（並列 API 呼び出しは同時並行で行わない）。

**Warning signs:**
- `threading.Thread` 上から `self.doc[page_idx]` や `page.get_pixmap()` を直接呼び出しているコード。
- 大きな PDF で断続的にクラッシュする（再現困難な Segfault）。
- `fitz` がインポートされているモジュールを `ThreadPoolExecutor` の `submit` に渡している。

**Phase to address:**
Phase 1（プロバイダ抽象化）のリファクタリング時に `_worker` の構造を見直し、fitz 操作の thread boundary を明確化する。

---

### Pitfall 3: Tkinter ウィジェットをワーカースレッドから直接更新する

**What goes wrong:**
Tkinter はシングルスレッドモデルであり、メインスレッド以外からウィジェット操作を行うと「RuntimeError: main thread is not in main loop」や描画の不整合・クラッシュが発生する。`_worker` を改修する際に `self.progress_var.set(...)` や `self.text.insert(...)` をスレッド内から直接呼び出してしまう。

**Why it happens:**
現行の `_worker` は正しく `self.after(0, lambda: ...)` を使っている（`ocr_dialog.py` L468-473）が、新しい Provider 実装のコールバック（`on_progress` 等）を別モジュールに書く際、`after()` 経由であることを忘れてウィジェット操作を書いてしまう。

**How to avoid:**
- プロバイダ実装（`ocr_providers.py`）はウィジェットを一切参照しない。コールバックは純粋な Python データを返すだけにする。
- `OCRDialog._worker` がコールバックを受け取り、必ず `self.after(0, callback)` でディスパッチするルールを守る。
- ユニットテストでコールバック呼び出しを検証する際も、実 Tkinter を使わずモックで確認する。

**Warning signs:**
- `_worker` や `OCRProvider.ocr_image()` の実装内で `self.widget.config(...)` や `StringVar.set(...)` を直接呼んでいる。
- macOS/Linux では動くが Windows で落ちる（Tkinter の threading 挙動が OS ごとに異なる）。
- `after_idle` / `after()` を使わずに `update()` を直接呼んでいる。

**Phase to address:**
Phase 1 のプロバイダ抽象化で、Provider インターフェースの設計段階から「ウィジェット非参照」を明示する。

---

### Pitfall 4: 全ページ base64 画像の一括メモリ保持

**What goes wrong:**
現行 `_worker` はフェーズ1で全ページを `images = {}` に蓄積してからフェーズ2の並列 API 呼び出しへ渡す（`ocr_dialog.py` L463）。100ページ・scale=2.0 の PDF では、1ページあたり平均 2〜5 MB の base64 文字列が生成されるため、200〜500 MB 以上がヒープに積まれる。低 RAM PC（4〜8 GB）でこれを行うとページング（スワップ）が発生し、処理全体が極端に遅くなる。

**Why it happens:**
並列 API 呼び出しに「全画像が揃っている状態」を要求する設計のため。LM Studio（ローカル）では並列度と待ち時間が小さいため問題が表面化しなかった。クラウド API では 1 ページあたりの待ち時間が長くなるため、パイプライン化の恩恵が大きく、問題もより顕在化する。

**How to avoid:**
仕様書案（§4.3）の通り「レンダリング→送信→破棄」を逐次化する。具体的な実装パターン：
```python
for page_idx in self.page_indices:
    if self._cancel_flag.is_set():
        break
    b64 = page_to_png_b64(self.doc[page_idx], scale=scale)  # メインスレッドで実行
    text = provider.ocr_image(b64, prompt, ...)              # ブロッキング（スレッド内）
    del b64  # 送信直後に破棄
    self.results[page_idx] = text
```
並列度が必要な場合は「N ページのスライディングウィンドウ」で画像を保持し、完了次第破棄する。クラウドプロバイダの推奨並列度は 2〜3（後述 Pitfall 5 参照）のため、ウィンドウサイズも同値で十分。

**Warning signs:**
- `images = {}` へのアペンドがループ終了まで `del` されない。
- `psutil.Process().memory_info().rss` が OCR 中に急増する。
- 大きな PDF で Windows のページングが頻発（タスクマネージャでコミットメモリが急増）。

**Phase to address:**
Phase 3（Gemini Provider 追加 + 逐次レンダリング化）。仕様書作業項目 #9 に対応。

---

### Pitfall 5: クラウド API への過剰並列（429 誘発）

**What goes wrong:**
現行の `MAX_OCR_CONCURRENCY = 8` をクラウドプロバイダにそのまま適用すると、Gemini 無料枠（Free Tier: 10〜15 RPM）や Anthropic の初期枠（Tier 1 の 50 RPM）で即座に 429 エラーが発生する。特に Gemini Free Tier は **10 RPM** という非常に低い上限を持ち、8並列で大量ページ OCR を開始すると最初の数ページで全スロットが 429 になる。

**Why it happens:**
LM Studio はローカルで並列度制限が実質ない。クラウドプロバイダのレート制限はアカウントティアにより大きく異なり、ハードコードした上限が適切とは限らない。

**How to avoid:**
- プロバイダごとに `DEFAULT_CONCURRENCY` と `MAX_CONCURRENCY` を分離する：
  ```
  LM Studio: DEFAULT=2, MAX=8
  Claude:    DEFAULT=2, MAX=4
  Gemini:    DEFAULT=1, MAX=3  # Free Tier では 1 が安全
  Tesseract: DEFAULT=1, MAX=1  # CPU bound、並列化不要
  ```
- 429 レスポンスを受けたら指数バックオフ（初回 1s → 2s → 4s → 8s、最大 3 回）してリトライする。
- `Retry-After` ヘッダー（Anthropic は返す場合がある）を尊重する。
- 529（Anthropic 過負荷）は 429 とは別のエラーコードで、同様にバックオフ対象とする。
- `on_progress` コールバックで 429 をユーザーに「レート制限中、待機中...」と表示する。

**Warning signs:**
- `HTTP 429: rate_limit_error` が OCR 開始直後に連続して発生する。
- `HTTP 529: overloaded_error`（Anthropic 固有）が散発する。
- Gemini の `RESOURCE_EXHAUSTED` エラーが返される。

**Phase to address:**
Phase 2（Claude Provider 実装）から対応。プロバイダ基底クラスのインターフェースに `default_concurrency: int` を持たせ、バックオフロジックを `run_parallel()` に組み込む。

---

### Pitfall 6: レスポンス解析の脆弱性とプロバイダ固有エラー形状の無視

**What goes wrong:**
各プロバイダのレスポンス構造が異なり、単純なキーアクセスでは KeyError / IndexError が発生する。特に問題となるパターン：

- **Gemini**: `candidates[0].content.parts[0].text` — `candidates` が空（安全フィルタによるブロック）の場合 IndexError
- **Claude**: `content[0].text` のような決め打ちアクセス — `content` リストには `type=="thinking"` や `type=="tool_use"` のブロックが混在するため、`type=="text"` のブロックをスキャンする必要がある
- **共通**: HTTP エラー本文が JSON でなく HTML のプロキシエラーページになっている場合の `json.JSONDecodeError`

**Why it happens:**
現行の `call_lm_studio` は `result["choices"][0]["message"]["content"]` の固定アクセスをしている（`ocr.py` L131）。この単純なパターンをクラウドプロバイダへ適用しようとすると、各プロバイダの多様なレスポンス構造に対応できない。

**How to avoid:**
各プロバイダの解析を専用メソッドに分離し、防衛的に書く：

```python
# Gemini
def _parse_gemini(body: dict) -> str:
    candidates = body.get("candidates", [])
    if not candidates:
        # finishReason が SAFETY / RECITATION の場合は candidates が空になる
        reason = body.get("promptFeedback", {}).get("blockReason", "unknown")
        raise RuntimeError(f"Gemini blocked: {reason}")
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [p["text"] for p in parts if "text" in p]
    if not texts:
        raise RuntimeError(f"Gemini: no text in response: {body}")
    return "\n".join(texts)

# Claude
def _parse_claude(body: dict) -> str:
    for block in body.get("content", []):
        if block.get("type") == "text":
            return block["text"]
    raise RuntimeError(f"Claude: no text block in content: {body}")
```

テストでは各プロバイダのエラー形状（429 本文 JSON / 安全ブロック / 空レスポンス / HTML エラーページ）をモックして解析関数の動作を検証する。

**Warning signs:**
- `KeyError: 'candidates'` や `IndexError: list index out of range` が OCR 結果エリアに表示される。
- 特定のページのみエラーになるが、他は成功する（安全フィルタによるブロック）。
- エラーメッセージが HTML タグを含む。

**Phase to address:**
Phase 2（Claude Provider）・Phase 3（Gemini Provider）それぞれの実装時。各 Provider のユニットテストで必ず解析関数をモックテストする（仕様書作業項目 #11）。

---

### Pitfall 7: API のドリフト（モデル ID・パラメータ非互換）

**What goes wrong:**
公式ドキュメントで確認した現在の非互換制約：

1. **Claude Opus 4.8 / 4.7**: `temperature` パラメータは使用できない。`output_config.effort` で制御する（`high` = デフォルト）。`temperature` を送ると 400 エラーが返る可能性がある。
2. **Claude Opus 4.8**: 手動 `extended thinking`（`thinking: {type: "enabled", budget_tokens: N}`）は 400 エラー。OCR 用途では thinking は不要なため、`output_config` に `thinking` を含めない。
3. **`anthropic-version` ヘッダー**: `2023-06-01` が必須。省略すると 400 エラー。
4. **Claude モデル ID**: `claude-haiku-4-5-20251001`（Haiku の最新 dated ID）、`claude-sonnet-4-6`（dateless）、`claude-opus-4-8`（dateless）。旧来の `claude-2`, `claude-instant` 等は廃止済み。
5. **Gemini モデル ID**: `gemini-2.5-flash`（SDK からは `gemini-2.5-flash` で参照）。旧来の `gemini-pro-vision` は廃止予定。
6. **Gemini**: `candidates` が空の場合の `finishReason: SAFETY` / `RECITATION` は OCR（PDF 画像）では稀だが、特定のコンテンツで発生する。

**Why it happens:**
仕様書（§3）の API 差分表は現時点の情報だが、モデル名とパラメータは頻繁に変わる。特に Anthropic は Claude 4.x 系のリリースに伴い、`temperature` の挙動・`effort` パラメータの追加・`extended thinking` のインターフェース変更を短期間で行っている。

**How to avoid:**
- `OCRProvider.list_models()` で利用可能モデルを動的取得し、UI のコンボボックスを更新する。モデル ID をハードコードしない。
- プロバイダ別の「非対応パラメータ」リストを持ち、payload 構築時に除外する：
  ```python
  CLAUDE_NO_TEMPERATURE_MODELS = {"claude-opus-4-8", "claude-opus-4-7"}
  if model in CLAUDE_NO_TEMPERATURE_MODELS:
      payload.pop("temperature", None)
      payload["output_config"] = {"effort": "high"}
  ```
- `anthropic-version` ヘッダーは定数で管理し、定期的にドキュメントを確認して更新する。
- モデル一覧 API のレスポンスに `capabilities` フィールドがあれば参照する（Anthropic Models API は `max_input_tokens`, `max_tokens`, `capabilities` を返す）。

**Warning signs:**
- `HTTP 400: invalid_request_error` で「temperature is not supported for this model」が返される。
- `HTTP 400: invalid_request_error` で「anthropic-version header is required」が返される。
- モデル一覧を取得すると UI に表示されているモデル ID がリストに存在しない。

**Phase to address:**
Phase 2（Claude Provider 実装）でペイロード構築ロジックを確立する際に対応。モデル別制約を定数で管理する仕組みを設ける。

---

### Pitfall 8: プライバシー・コスト無確認での大量ページ送信

**What goes wrong:**
100 ページの PDF に対してクラウド OCR を実行ボタン一押しで開始できる。`gemini-2.5-flash` のコストは入力トークン $0.15/M（画像は画像トークンで計算）、`claude-haiku-4-5` は $1/M 入力トークン。1 ページが 1000〜4000 トークンの画像に相当すると仮定すると、100 ページで $0.015〜$0.40 程度になるが、高解像度（`ocr_scale=2.0`）・長文ページでは急増する。また、クラウド送信に対してユーザーが明示的な同意をしていない場合のプライバシー問題もある。

**Why it happens:**
既存の LM Studio プロバイダはローカル処理のためコスト・プライバシー問題がなかった。クラウドへの切り替えを「プロバイダ変更」として実装すると、この側面を見落としやすい。

**How to avoid:**
- クラウドプロバイダを選択して実行ボタンを押した際、**実行前確認ダイアログ**を必ず表示する：
  - 「このページの画像が外部クラウドサービス（{provider_name}）に送信されます。」
  - 「対象ページ数: {N} ページ」
  - 「概算コスト: 〜¥{estimate}（参考値）」
  - 「よろしいですか？」
- `ocr_provider == "off"` のまま OCR ボタンを押した場合は「プロバイダが設定されていません」を表示する（デフォルト安全状態の維持）。
- コスト見積もりは簡単な近似式（ページ数 × `ocr_scale^2` × 係数）で十分。正確性より警告の存在が重要。
- 設定で「コスト確認を毎回表示する / 初回のみ / 表示しない」を選べるようにする。

**Warning signs:**
- クラウドプロバイダ選択後に確認なしで実行が始まる。
- OCR ボタンの tooltip/ラベルにプロバイダ名が表示されない。
- API 請求が想定外に高くなった、というユーザー報告。

**Phase to address:**
Phase 2（Claude Provider）実装時に確認ダイアログを同時に実装する。プロバイダ選択 UI の構築と不可分な要件として扱う。

---

### Pitfall 9: PyInstaller での隠れ依存と外部バイナリ未同梱

**What goes wrong:**
Tesseract Provider を実装する際、`pytesseract` ライブラリを採用すると以下が問題になる：

1. **Tesseract 本体（`tesseract.exe`）の未同梱**: PyInstaller は Python パッケージのみを収集し、外部バイナリは自動収集しない。`--add-binary tesseract.exe;.` で明示追加が必要。
2. **言語データ（`tessdata/`）の未同梱**: `jpn.traineddata` / `jpn_vert.traineddata` を `--add-data tessdata;tessdata` で追加しないと日本語 OCR が機能しない。
3. **`pytesseract` の `pytesseract.pytesseract_cmd` パス**: フリーズ（`.exe`）実行時のバイナリパスを動的に設定する必要がある（`sys.frozen` 判定）。

公式 SDK（`anthropic` / `google-genai` パッケージ）を採用した場合も同様の問題がある（隠れ依存の `httpx`, `anyio`, `certifi`, `httpcore` 等が大量に必要で、`.exe` が 100MB 超になる）。これが `urllib` 直叩き方針の根拠であり、仕様書（§2.1）で既に採用済み。

**Why it happens:**
開発環境では `tesseract` がシステムインストールされているため動作する。PyInstaller でビルドした `.exe` を別 PC で実行すると「tesseract is not installed or it's not in your PATH」エラーになる。

**How to avoid:**
- Tesseract Provider は `subprocess` 直叩き（`pytesseract` を使わず `tesseract` コマンドを直接実行）か、`pytesseract` を使う場合は `sys.frozen` 時のバイナリパス設定を忘れない：
  ```python
  import sys, os
  if getattr(sys, "frozen", False):
      import pytesseract
      pytesseract.pytesseract.tesseract_cmd = os.path.join(
          os.path.dirname(sys.executable), "tesseract", "tesseract.exe"
      )
  ```
- `.spec` ファイルに以下を追加する：
  ```python
  binaries=[("path/to/tesseract.exe", "tesseract")],
  datas=[("path/to/tessdata", "tessdata")],
  ```
- Tesseract Provider は Optional 扱い（インストール確認 → 非対応なら graceful fallback）とする。起動時に `shutil.which("tesseract")` で確認し、無ければ選択肢を無効化する。
- クラウドプロバイダ（Claude/Gemini）は `urllib` 標準ライブラリのみで実装するため PyInstaller への追加影響はゼロ。

**Warning signs:**
- 開発環境での `pytest` は通るが、`dist/PageFolio.exe` を別 PC で実行すると Tesseract エラーが出る。
- `.exe` のファイルサイズが前バージョンより 50MB 以上増えた（SDK 依存の流入）。
- `import anthropic` や `import google.generativeai` がソースコードに現れる。

**Phase to address:**
Phase 4（Tesseract Provider・任意）。Phase 1〜3 は `urllib` 直叩きのため影響なし。

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| 全プロバイダで同一 `ocr_concurrency` 設定を使用 | 設定項目が増えない | Gemini Free Tier で即 429 | never — プロバイダ別 default を持つべき |
| API キーを `settings` 辞書に入れてから `_save_settings` のガードで弾く | 実装が楽 | バグ一つで平文漏洩 | never — 辞書に入れないことが正解 |
| プロバイダ別エラー解析を `try/except KeyError` 一本で行う | コード量が減る | エラー原因が不明瞭、安全ブロックを見逃す | テスト中のみ（本番前に専用パーサに置換） |
| モデル ID をハードコード | ドキュメント不要 | モデル廃止で突然動かなくなる | never — 動的取得 + フォールバック推奨値を持つ |
| バックオフなしで 429 を即エラー表示 | 実装が簡単 | ユーザーが手動リトライを繰り返す | MVP の初期実装のみ（Phase 2 完了前） |
| 逐次レンダリング化を後回しにして全ページ一括レンダリング | Phase 3 まで既存動作を維持 | 低 RAM PC でメモリ逼迫、テスト前に問題発覚困難 | Phase 3 の作業項目 #9 が完了するまでのみ |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Anthropic Messages API | `content[0].text` で決め打ちアクセス | `type=="text"` ブロックを走査して最初のものを取得 |
| Anthropic Messages API | `temperature` を全モデルに送信 | Opus 4.7/4.8 は `output_config.effort` を使用、`temperature` を送らない |
| Anthropic Messages API | `anthropic-version` ヘッダーを省略 | 必ず `"2023-06-01"` を送信（2026-06 時点の最新安定版） |
| Gemini generateContent | `candidates[0].content.parts[0].text` で決め打ち | `candidates` 空チェック → `finishReason` 確認 → `parts` 走査 |
| Gemini generateContent | 画像を `image_url` 形式（OpenAI 互換）で送信 | `inline_data: {mime_type: "image/png", data: "<base64>"}` 形式で送る |
| Gemini generateContent | 429 エラーで処理を中断 | `RESOURCE_EXHAUSTED` エラーコードを検出してバックオフリトライ |
| Tesseract (pytesseract) | 開発環境のシステム `tesseract` に依存 | `.exe` 同梱バイナリのパスを `sys.frozen` で切り替え |
| Tesseract | 日本語データなしで実行 | `lang="jpn"` 指定 + `jpn.traineddata` 同梱を確認 |
| fitz.Document | ThreadPoolExecutor に渡す | レンダリング結果（bytes）のみを渡す |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| 全ページ base64 一括保持 | メモリ使用量がページ数に比例して急増、低 RAM PC でスワップ発生 | ページ単位「レンダリング→送信→破棄」に逐次化 | ページ数が 30〜50 超・`ocr_scale=2.0`・RAM 8GB 未満 |
| クラウドで並列度 8 | OCR 開始直後に 429 エラーが連発 | プロバイダ別 `DEFAULT_CONCURRENCY`（Gemini=1, Claude=2） | Gemini Free Tier は 10 RPM（ほぼ即座に上限到達） |
| `ocr_scale=2.0` のままクラウド送信 | 1ページあたりのデータ量が大きくコスト増・転送遅延増 | クラウド用デフォルトを `1.5` に見直し。UI でコスト/精度のトレードオフを明示 | 低速回線 + 高解像度 + 多ページで体感速度が著しく低下 |
| テキスト埋め込み判定なしで全ページ API 呼び出し | 不要な課金が発生 | `page.get_text().strip()` で判定して非空なら API 呼び出しをスキップ | テキスト埋め込み PDF ではほぼ毎回の無駄な課金 |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `pagefolio_settings.json` への API キー保存 | キーのファイルシステム露出・Git コミットによる漏洩 | `_save_settings()` にブロックリスト処理を追加、キーは環境変数のみ |
| `logger.debug("settings: %s", settings)` でキー含む辞書をログ | ログファイル・デバッグ出力へのキー混入 | 保存前のキー除外辞書のみをログ出力。`repr()` に API キーを含めない |
| ダイアログ入力キーを `self.settings` 辞書に格納 | `_save_settings` の次回呼び出しで自動保存される | キーはセッション専用変数（`_session_key`）に保持し `settings` には入れない |
| エラーメッセージにキー全体を含める | ログ・UI 表示でキーが露出 | エラー表示前にキーを `sk-ant-api...**` 等に伏字化する関数を経由する |
| PyInstaller `.exe` に API キーをハードコード | バイナリを展開するとキーが見える | コンパイル時定数への組み込みは絶対禁止 |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 環境変数未設定時に黙ってクラッシュ | 原因不明でアプリが応答しなくなる | 「環境変数 ANTHROPIC_API_KEY が設定されていません。設定方法: ...」を明確に表示 |
| クラウド送信前に確認なし | 意図せず個人情報を含む PDF ページを外部送信 | プロバイダがクラウド系の場合は必ず外部送信警告ダイアログを表示 |
| 429 エラーを「接続エラー」と誤表示 | ユーザーがネットワーク設定を確認しに行く | エラーコードに応じた説明（「レート制限中。しばらく待ってから再試行してください」） |
| `ocr_provider = "off"` で OCR ボタンが見えたまま | ボタンを押してもエラー表示になる | `off` 状態では OCR ボタンを `disabled` または非表示にする |
| Tesseract の精度が低いことを事前に説明しない | VLM と比較して精度が著しく低い場合にユーザーが困惑 | Tesseract 選択時に「クラウド VLM より精度が劣ります。日本語は jpn.traineddata の事前インストールが必要です」と注記する |

---

## "Looks Done But Isn't" Checklist

- [ ] **環境変数キー読み取り**: `os.environ.get()` で読んでいるが、`settings` 辞書経由で `_save_settings` に流れていないことを確認
- [ ] **クラウドプロバイダ確認ダイアログ**: 「実行」ボタンを押してもクラウド系プロバイダでは確認ダイアログが表示されることを手動確認
- [ ] **429 バックオフ**: モックサーバで 429 を返すテストでリトライ動作を確認（単発エラーで止まっていないか）
- [ ] **fitz スレッド境界**: `threading.Thread` の target 関数内に `self.doc[page_idx]` や `get_pixmap()` の直接呼び出しがないことを grep で確認
- [ ] **Tkinter スレッド安全**: Provider 実装クラス内に `tk.`, `ttk.`, `StringVar`, `after` 等の Tkinter シンボルがないことを確認
- [ ] **Claude content パース**: `content[0].text` でなく `type=="text"` スキャンになっているか
- [ ] **Gemini candidates 空チェック**: `candidates` が空の場合のハンドリングがあるか
- [ ] **anthropic-version ヘッダー**: urllib リクエストに `"anthropic-version": "2023-06-01"` が含まれているか
- [ ] **Opus 4.x の temperature 除外**: `claude-opus-4-7` / `claude-opus-4-8` では `temperature` をペイロードから除外しているか
- [ ] **PyInstaller ビルドでのキー非混入**: `pagefolio_settings.json` を `dist/` ディレクトリで確認し API キーフィールドがないことを確認

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| APIキーの平文保存（コミット前に発覚） | LOW | `_save_settings` のガード追加 + 設定ファイル再生成 |
| APIキーの平文保存（Git コミット済み） | HIGH | `git filter-repo` でコミット履歴から削除 + キー即時失効（API コンソールで失効） + `.gitignore` に設定ファイル追加 |
| fitz スレッドクラッシュ | MEDIUM | `_worker` リファクタリングで fitz 操作をメインスレッドに移動。crash dump が取れない場合は bisect で再現箇所を特定 |
| 意図しないクラウド課金 | MEDIUM | API コンソールで利用上限アラートを設定（予防）。発生後は請求サポートに連絡して免除申請 |
| モデル ID 廃止で突然 400 | LOW | `list_models()` で取得したリストの先頭をフォールバックとして使用 |
| PyInstaller で Tesseract 未同梱 | MEDIUM | `.spec` に `binaries` / `datas` 追加 + `sys.frozen` パス設定 + 再ビルド |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| APIキー平文漏洩 | Phase 2 開始時（最優先） | `pagefolio_settings.json` に `api_key` 系フィールドが存在しないことを pytest で確認 |
| fitz スレッド非安全 | Phase 1（プロバイダ抽象化） | `_worker` 内の fitz 操作を grep で検出するテストを追加 |
| Tkinter スレッド非安全 | Phase 1（Provider インターフェース設計） | Provider クラスの Tkinter 依存を import 検査で検出 |
| 全ページ一括メモリ保持 | Phase 3（逐次レンダリング化 #9） | 大きな PDF でのメモリプロファイリングで確認 |
| クラウド過剰並列・429 | Phase 2（Claude Provider から） | モック 429 サーバでバックオフ動作を確認 |
| レスポンス解析脆弱性 | Phase 2・3 それぞれの実装時 | 各プロバイダのエラー形状モックテスト（#11） |
| API ドリフト（モデル・パラメータ） | Phase 2（Claude Provider 実装） | Opus 4.8 への `temperature` 送信テスト（400 確認） |
| プライバシー・コスト無確認 | Phase 2（Claude Provider と同時） | 手動テスト：クラウドプロバイダで実行ボタン押下時に確認ダイアログが表示されること |
| PyInstaller 隠れ依存・Tesseract 未同梱 | Phase 4（Tesseract・任意） | `dist/PageFolio.exe` を `tesseract` 未インストールの別 PC で実行 |

---

## Sources

- [Anthropic API Errors — HTTP error codes, 529 overloaded, rate limit](https://platform.claude.com/docs/en/api/errors) — HIGH confidence（公式ドキュメント）
- [Anthropic Models Overview — model IDs, effort parameter, temperature restrictions](https://platform.claude.com/docs/en/docs/about-claude/models/overview) — HIGH confidence（公式ドキュメント）
- [Anthropic Effort Parameter — effort levels, temperature incompatibility on Opus 4.7/4.8](https://platform.claude.com/docs/en/build-with-claude/effort) — HIGH confidence（公式ドキュメント）
- [Anthropic Extended Thinking — manual thinking 400 on Opus 4.8/4.7](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) — HIGH confidence（公式ドキュメント）
- [Gemini API Rate Limits — RPM/TPM/RPD per tier](https://ai.google.dev/gemini-api/docs/rate-limits) — HIGH confidence（公式ドキュメント）
- [Gemini API Text Generation — response structure, candidates, parts](https://ai.google.dev/gemini-api/docs/text-generation) — HIGH confidence（公式ドキュメント）
- [Gemini API Vision — inline_data format, base64 image](https://ai.google.dev/gemini-api/docs/vision) — HIGH confidence（公式ドキュメント）
- [PyMuPDF Thread Safety — multiprocessing recipes, no multithreading support](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html) — HIGH confidence（公式ドキュメント）
- [PyInstaller Hidden Imports — add-binary, tessdata bundling](https://pyinstaller.org/en/stable/usage.html) — HIGH confidence（公式ドキュメント）
- [PyInstaller + Tesseract issue #5601](https://github.com/pyinstaller/pyinstaller/issues/5601) — MEDIUM confidence（GitHub Issue）
- コードベース直接調査: `pagefolio/ocr.py`, `pagefolio/ocr_dialog.py`, `pagefolio/settings.py` — HIGH confidence（実コード）

---
*Pitfalls research for: マルチプロバイダ クラウド OCR 追加（Gemini/Claude/Tesseract）to PageFolio v1.4.0*
*Researched: 2026-06-06*
