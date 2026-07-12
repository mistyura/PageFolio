# Phase 2: OCR 磨き込み（レビュー残の現行照合と二重実装解消） - Research

**Researched:** 2026-07-05
**Domain:** 既存 Python/Tkinter デスクトップアプリの内部リファクタリング（OCR 実行パイプライン・プラグイン API 堅牢化・小規模バグ修正）。新規外部ライブラリなし。
**Confidence:** HIGH（全項目を現行コード読解で直接検証・行番号付きで確認済み。API 実挙動に依存する項目のみ MEDIUM）

## Summary

本フェーズは新技術の調査ではなく、`260610-aaa-REVIEW.md` の L-1〜L-6（v1.4.0 期レビュー残）を**現行コード（v1.7.0 時点）と照合し、生き残りを確定した上で解消する**作業である。調査の結果、L-1〜L-4 および L-6 の主要項目は**すべて現行コードに生き残っている**ことを確認した（詳細は「レビュー残 生き残り表」を参照）。唯一 `stop_reason`/`finishReason` 途切れ検出（Claude/Gemini の `ocr_image_ex`）のみ v1.6.0 Phase 3 で解消済みであり、L-6 の対象から除外できる。

最大のリスクは V171-OCR-04（L-1: producer-consumer 二重実装の一本化）である。`pagefolio/ocr.py:306 run_with_bounded_buffer` は本番未使用でテスト（`tests/test_ocr.py:1230-1327`）のみが消費しており、実運用は `pagefolio/ocr_dialog.py` の `_render_next_page`/`_worker`（Tkinter `after()` 連鎖 + `queue.Queue` + `threading`）が担っている。両者は待機進捗表示・"skip" ステータス・レンダー失敗時の挙動などで既に乖離しており、CONTEXT.md の D-01 により「`ocr_dialog.py` の実戦挙動を仕様とし、ヘルパー側を書き直す」方向が確定している。新モジュール `pagefolio/ocr_pipeline.py`（D-02）は `pagination.py`/`md_render.py`/`undo_store.py` と同型の「Tk/fitz 非依存純ロジック層」パターンに従うべきだが、producer 側は fitz レンダリングをメインスレッドの `after(0)` 連鎖で行う都合上、`run_with_bounded_buffer` のような「専用 producer スレッド」構造とは異なる分割が必要になる（詳細は Architecture Patterns 参照）。

**Primary recommendation:** L-1（V171-OCR-04）は独立プランへ完全隔離し、`ocr_dialog.py` の consumer ループ（`_worker`）と非ブロッキング producer（`_render_next_page`）を Tk 依存部分（`after`/`winfo_exists`/`self.text` 等）と Tk 非依存部分（キュー操作・リトライバックオフ・進捗計算・完了判定）に分離し、後者を `ocr_pipeline.py` の純関数/軽量クラス群として抽出する。L-2〜L-4・L-6 は独立した小プラン（複数可）として並行または後続実行してよい（相互依存が薄い）。

## User Constraints (from CONTEXT.md)

<user_constraints>
### Locked Decisions

**L-1: producer-consumer 一本化（V171-OCR-04）**
- **D-01:** `ocr_dialog.py` の実戦済み挙動（非ブロッキング put・世代ガード・waiting 進捗・skip status・render 失敗時 on_done）を**仕様**とし、純ロジック層を書き直して dialog がそれを消費する形で一本化する。`ocr.py:306 run_with_bounded_buffer`（本番未使用・テストのみ消費）は現仕様に合わせて置き換える。
- **D-02:** 純ロジック層は**新モジュール `pagefolio/ocr_pipeline.py`**（Tk/fitz 非依存）として切り出す。`pagination.py` / `md_render.py` / `undo_store.py` と同格のプロジェクト既存パターン。テストは `tests/test_ocr_pipeline.py` へ既存 bounded buffer テストを移設・拡充。CLAUDE.md のファイル構成表へ 1 行追記。
- **D-03:** L-6 のうちパイプライン系小物（レンダー失敗ページでプログレスバーが 100% に達しない問題・producer が fatal 後も全ページ render 継続・sentinel `buf.put(None)` の暗黙容量不変条件の明文化）は **L-1 独立プランに吸収**して同時解消する。L-6 一括プランはパイプライン外の小物に絞る。
- **D-04:** 一本化の対象は**複数ページ画像 OCR の実行パイプラインのみ**。サマリ生成（`_summary_worker`・単発 text-only 呼び出し）は現行のまま触らない。
- **制約:** V14-D-05/06（`fitz.get_pixmap()` はメインスレッドのみ・bounded buffer によるメモリ上限保証）を一本化後も維持すること。

**L-4: Tesseract 言語フォールバック（V171-OCR-02）**
- **D-05:** 言語パック検出（`_TESSERACT_LANGS` 相当）は import 時固定をやめ、**プロバイダ生成時に再検出**する（`tesseract --list-langs` を build_provider の都度実行・数十 ms で頻度的に無視可能）。言語パック追加が再起動なしで反映される。
- **D-06:** `ocr_image` は `self.lang`（`tesseract_lang` 設定・配線は `ocr.py:714` で既存）を尊重する。指定言語が利用不可の場合は**段階的縮退**：まず指定言語のうち利用可能な部分集合だけ残し（例: `deu+jpn+eng` → `jpn+eng`）、全滅なら現行の自動決定（jpn 有→`jpn+eng` / なし→`eng`）へ落とす。必ず何かしらで実行でき、エラー中止はしない。
- **D-07:** フォールバック発生時は **OCRDialog 内の非モーダル注記**（進捗ラベル/結果ヘッダ部・WARNING 色・実行は止めない）で「指定言語 xxx は利用不可のため yyy で実行」を 1 回表示する。OCR 結果テキスト自体には混入させない（コピー/保存 raw 維持の V16-D-02 方針と整合）。LANG キーは ja/en 両辞書へ同一キーで追加（既存 `tesseract_lang_fallback` キーの活用・拡張は実装時判断）。

**L-2/L-3: プラグイン OCR registry 堅牢化（V171-OCR-03）**
- **D-08:** 重複名登録ポリシー：**組み込み名**（claude / gemini / lmstudio / tesseract / ollama / runpod / off）との衝突は `logger.warning` して**拒否**（現行の「組み込み勝ち」を維持しつつ可視化）。**プラグイン同士**の重複は `logger.warning` 付きで**後勝ち上書き**（プラグインのリロードで自然に更新される）。
- **D-09:** プラグイン unload 時は registry からの**登録解除のみ**行う。settings の `ocr_provider` は触らない（副作用なし）。unload 後にそのプロバイダで OCR 実行した場合は既存の未知名エラー経路で明示エラーになる。unload 対象の特定のため name→plugin の対応を registry 側で追跡する。
- **D-10:** 公開アクセサは `PluginManager.get_ocr_provider(name) -> cls | None` と `list_ocr_providers() -> list[str]` の 2 メソッド。現存 2 箇所の私有アクセス（`ocr.py:720` / `dialogs/llm_config.py:127`）を置換する。`_provider_registry` は実装詳細として非公開のまま。プラグイン作者向け docstring を整備。

**L-6: 小物一括解消の範囲確定（V171-OCR-01）**
- **D-11:** Phase 2 の対象は `260610-aaa-REVIEW.md` の **L-6 に明記された項目のみ**。照合中に見つかったリスト外の同種軽微事項は Phase 4（V171-TEST-03 既知軽微バグ棚卸し）へ送る（deferred として記録）。
- **D-12:** 現行コード照合の結果（活き残り/解消済み判定）は Phase 2 の **RESEARCH.md に活き残り表**（項目 × 判定 × 根拠ファイル:行番号）として記録する。各項目の解消時には元の `260610-aaa-REVIEW.md` 該当項目へ **✅ + コミットハッシュを追記**（同文書の既存慣行「修正完了時は本文書の該当項目に完了マーク追記」に従う）。
- **D-13:** URL スキーム検証（http/https のみ許可）は LM Studio に限定せず、**ユーザー入力 URL/エンドポイントを持つ全プロバイダ（LM Studio / Ollama / RunPod）へ共通ヘルパーで統一適用**する。これは同一項目の適用先拡張であり D-11 の「新規項目追加」には当たらない。
- **照合の初期見立て（discuss 時スカウト・researcher が最終確定）:**
  - 解消済みの見込み: ClaudeProvider `stop_reason` 途切れ検出（v1.6.0 Phase 3 で `ocr_image_ex` 実装済み）・lang 未使用キーの一部（`ocr_provider_name_tesseract` は `ocr_dialog.py:708` で使用中）
  - 活き残りの見込み: URL スキーム検証なし・Gemini モデル名 URL 未エスケープ（`quote(` 不在）・`_fetch_models`/`_test_connection` 重複（`llm_config.py:1120` / `:1142`）
  - 要照合: Gemini エラー body 切り詰め・"off" 切替時の `_update_ocr_buttons_state()` 未呼出・ClaudeProvider `list_models` ページネーション

### Claude's Discretion
- `ocr_pipeline.py` の API 形状（コールバック境界・関数 vs クラス・引数設計）と、dialog 側の `after()` 描画配線の詳細。
- Tesseract 言語再検出のキャッシュ戦略（生成の都度 subprocess か、短期キャッシュか）と `list_models` との整合。
- `_fetch_models` / `_test_connection` 重複解消の共通化形（ヘルパー抽出 or パラメータ化）。
- フォールバック注記の文言詳細と既存 `tesseract_lang_fallback` キーの再利用/新設判断。

### Deferred Ideas (OUT OF SCOPE)
- 照合中に見つかる L-6 リスト外の軽微事項 → Phase 4（V171-TEST-03 既知軽微バグ棚卸し）へ送る（D-11 の運用ルール。具体項目は本 RESEARCH.md の「Phase 4 への繰り越し候補」に記録）
- サマリ経路（`_summary_worker`）の共通基盤化 → 今回は見送り（D-04）。将来 OCR 基盤を再訪する際の候補
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V171-OCR-01 | L-6 小物が現行コード照合の上で一括解消される | 「レビュー残 生き残り表」の L-6 各項目に根拠行番号を記載。progress bar 100% 問題・sentinel 不変条件は D-03 により L-1 プランへ吸収済みなので V171-OCR-01 の対象からは除外して計画すること |
| V171-OCR-02 | TesseractProvider が `tesseract_lang` 設定を尊重する | `ocr_providers.py:1011-1057`（現状 `self.lang` 完全無視）・`_detect_tesseract()`（:960-994・import 時固定）を確認。`tests/test_ocr_providers.py:1131-1157` の既存フォールバックテストは新ロジックで書き換え必須（挙動が変わる） |
| V171-OCR-03 | プラグイン OCR registry が堅牢化される | `plugins.py:200-219`（重複検証・unload 解除なし）を確認。既存テスト `tests/test_plugins.py:546-601` は `_provider_registry` 直接参照のため新規公開アクセサのテストは追加型で書く（既存テストの破壊的変更は不要） |
| V171-OCR-04 | producer-consumer ロジックが一本化される | `ocr.py:306-498`（未使用ヘルパー）と `ocr_dialog.py:1323-1586`（実運用実装）の乖離点を specific に列挙（Architecture Patterns 参照）。既存 OCR テスト群（`test_ocr.py`・`test_ocr_providers.py`・`test_provider_ui.py`）のグリーン維持が安全網 |
</phase_requirements>

## Architectural Responsibility Map

このアプリは単一プロセスの Tkinter デスクトップアプリであり、Web の階層（Browser/SSR/API/CDN/DB）は存在しない。代わりに以下のレイヤーで責務を割り当てる。

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OCR 実行パイプライン制御（キュー・リトライ・進捗計算） | 純ロジック層（`ocr_pipeline.py`・新設） | — | Tk/fitz 非依存にすることで pytest 直接テスト可能にする（既存 `pagination.py`/`md_render.py` と同じ責務分離） |
| ページレンダリング（fitz→PNG→base64） | UI 層（`ocr_dialog.py`）メインスレッド | — | V14-D-05 制約: `fitz.get_pixmap()` はメインスレッドのみ。パイプライン純ロジック層には fitz を持ち込めない |
| ネットワーク I/O（各プロバイダの HTTP 呼び出し） | プロバイダ層（`ocr_providers.py`） | — | urllib 直叩き（V14-D-01: 新規 pip 依存ゼロ方針） |
| プラグイン登録・ライフサイクル管理 | プラグイン層（`plugins.py`） | UI 層（`llm_config.py` の Combobox 表示） | registry は plugins.py が真の情報源。UI は公開アクセサ経由で参照するのみ（D-10） |
| OCR 実行 UI（進捗表示・キャンセル・結果描画） | UI 層（`ocr_dialog.py`） | — | Tkinter `after()` ベースのイベントループに依存する部分はここに残す |
| 設定値の永続化・APIキー非保存ガード | 設定層（`settings.py`） | — | 本フェーズでは変更しない（Phase 1 で確定済み） |

## Standard Stack

新規ライブラリの追加はない（V14-D-01: urllib 直叩き・新規 pip 依存ゼロ方針を継続）。本フェーズで使用する既存 stdlib モジュール:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `queue.Queue` | stdlib | producer-consumer バッファ（bounded buffer） | 既に `ocr.py`/`ocr_dialog.py` 両方で使用中。スレッドセーフ FIFO の標準解 |
| `threading` | stdlib | ワーカースレッド・Lock 保護共有カウンタ | 既存パターン（`_done_lock`・`_workers_remaining`）を継続 |
| `concurrent.futures.ThreadPoolExecutor` | stdlib | `run_with_bounded_buffer`/`run_parallel` の consumer 並列実行 | 既存パターン継続。一本化後も `ocr_pipeline.py` 内で利用可 |
| `subprocess` | stdlib | Tesseract CLI 呼び出し（`--list-langs` 再検出含む） | 既存 `_detect_tesseract()` パターンを流用（`shell=True` 不使用・引数リスト渡し） |
| `urllib.parse.quote` | stdlib | Gemini モデル名の URL エスケープ（L-6・現状未使用） | 標準ライブラリのみで対応可能。新規 import 追加のみ |
| `urllib.parse.urlsplit` | stdlib | URL スキーム検証（http/https 許可・L-6・D-13） | `urlsplit(url).scheme` で判定。正規表現より堅牢 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `logging` | stdlib | 重複名登録警告・フォールバック通知のログ出力 | D-08（重複名警告）・D-05（再検出のデバッグログ）で使用 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `queue.Queue` bounded buffer 自作維持 | `asyncio` ベースの書き直し | Tkinter の `after()` イベントループと asyncio の統合は複雑化するだけで得るものがない（既存スレッドモデルは十分機能している）。不採用 |
| `urllib.parse.urlsplit` | 正規表現で `^https?://` を判定 | urlsplit の方が IPv6 ホストや認証情報付き URL でも堅牢。標準ライブラリ内で完結するため採用 |

**Installation:** 不要（すべて Python 標準ライブラリ）。

**Version verification:** 本フェーズは新規パッケージを導入しないため `npm view` 等のレジストリ検証は不要。`requirements.txt` に記載の既存パッケージ（PyMuPDF 1.27.2.2 / Pillow 12.2.0 / tkinterdnd2 0.4.3）はこのフェーズで変更しない。

## Package Legitimacy Audit

該当なし — 本フェーズは既存 stdlib（`queue`/`threading`/`subprocess`/`urllib.parse`）のみを使用し、新規外部パッケージのインストールは発生しない。`pyproject.toml`/`requirements.txt` の変更も不要。

## レビュー残 生き残り表（D-12）

`260610-aaa-REVIEW.md` の該当項目を現行コード（2026-07-05 時点）と照合した結果。判定は「活き残り」「解消済み」「要判断（Phase 2 スコープ外への提案含む）」の3種。

| # | 項目 | 判定 | 根拠（ファイル:行番号） | 対応要件 |
|---|------|------|--------------------------|----------|
| L-1 | producer-consumer 二重実装（`ocr.py::run_with_bounded_buffer` 本番未使用 vs `ocr_dialog.py` 独自実装） | **活き残り** | `ocr.py:306-498`（`run_with_bounded_buffer` は `tests/test_ocr.py:1262,1282,1316` のみが呼び出し、`build_provider`/`OCRMixin` 経由の本番コードからは未参照）。実運用は `ocr_dialog.py:1323-1414`（`_render_next_page`）+ `:1430-1586`（`_worker`） | V171-OCR-04 |
| L-2 | `register_ocr_provider` の名前検証・アンロード解除なし | **活き残り** | `plugins.py:200-219`（重複名チェック皆無・組み込み名との衝突ガードなし）。`plugins.py:152-161`（`unload_plugin` は `_plugins`/`_plugin_modules` のみ削除し `_provider_registry` は無変更） | V171-OCR-03 |
| L-3 | `plugin_manager._provider_registry` への私有属性直接アクセス | **活き残り** | `ocr.py:720`（`if plugin_manager is not None and name in plugin_manager._provider_registry:`）・`dialogs/llm_config.py:127`（`self._plugin_manager._provider_registry.keys()`） | V171-OCR-03 |
| L-4 | TesseractProvider が `tesseract_lang` 設定を無視 | **活き残り** | `ocr_providers.py:1039`（`lang = "jpn+eng" if "jpn" in _TESSERACT_LANGS else "eng"` — `self.lang` 未参照）。`_TESSERACT_LANGS` は `ocr_providers.py:994` でモジュール import 時に一度だけ評価（再起動まで固定）。`self.lang` は `__init__`（:1011-1022）で保持されるのみで `ocr_image` から一切参照されない | V171-OCR-02 |
| L-5 | lang.py 未使用キー 3 件 | **一部解消済み（Phase 2 スコープ外）** | `ocr_provider_name_tesseract` は `ocr_dialog.py:708`（`_provider_display_name`）で使用中 = 解消済み。`ocr_provider_off_hint`/`tesseract_not_installed` の未使用判定は V171-UIUX-02（Phase 4・L-5 吸収）の担当であり本フェーズの対象外（REQUIREMENTS.md Traceability 確認） | 対象外（Phase 4） |
| L-6a | レンダー失敗ページでプログレスバーが 100% に達しない | **活き残り（L-1 プランへ吸収・D-03）** | `ocr_dialog.py:1407-1409`（`_render_next_page` の `except Exception as e:` ブロックで `self.errors[page_idx]` は設定するが `progress_var`/`progress_bar` の更新コールが一切ない。当該ページは `_render_queue` に積まれないため `_worker` 側の統合プログレスにも計上されず、進捗合計が `len(run_pages)` に到達しない） | V171-OCR-04（L-1 プラン内） |
| L-6b | ClaudeProvider `list_models` のページネーション未対応 | **活き残り（軽微・要判断）** | `ocr_providers.py:642-691`（`Anthropic /v1/models` を単発 GET のみ・`has_more`/`after_id` 等のカーソル処理なし）。実害は現行モデル数がページ上限（既定 20 件程度）を超えない限り顕在化しない | V171-OCR-01（対応するか Phase 4 送りか計画時に判断） |
| L-6c | stop_reason（截断検出） | **解消済み** | `ocr_providers.py:608-639`（ClaudeProvider `ocr_image_ex`/`complete_text_ex` が `stop_reason=="max_tokens"` を検出）・`:839-909`（GeminiProvider が `finishReason=="MAX_TOKENS"` を検出）。v1.6.0 Phase 3 で実装済み（D-05 相当） | 対象外（解消済み） |
| L-6d | Gemini エラーメッセージの body 切り詰めなし | **活き残り（Gemini 限定ではなく全プロバイダ共通ヘルパーが対象）** | `ocr_providers.py:193-215`（`_raise_mapped_http_error` の非リトライ系エラーメッセージ `message = f"HTTP {e.code}: {err_body or e.reason}"` に `[:500]` 等の切り詰めなし）。この関数は LMStudio/Claude/Gemini/Ollama/RunPod 全プロバイダの HTTPError ハンドラから共有呼び出しされる（:308,557,828,1158,1388）ため、Gemini 限定ではなく共通ヘルパー1箇所の修正で全プロバイダに波及する | V171-OCR-01 |
| L-6e | LM Studio URL のスキーム未検証 | **活き残り（3プロバイダへ適用拡張・D-13）** | `ocr_providers.py:296`（LMStudioProvider `_post_chat` の `endpoint = self.url.rstrip("/") + "/v1/chat/completions"`）・`:1145`（OllamaProvider 同型）・`:1372`（RunPodProvider 同型）。いずれも `self.url` のスキームを検証せず `urllib.request.Request` に直接渡す | V171-OCR-01 |
| L-6f | Gemini モデル名の URL 未エスケープ | **活き残り** | `ocr_providers.py:706-708,811`（`GENERATE_CONTENT_ENDPOINT.format(model=self.model)` で `self.model` を素の文字列展開。`urllib.parse.quote` 等のエスケープなし。リポジトリ全体で `quote(` の使用箇所ゼロ） | V171-OCR-01 |
| L-6g | producer が fatal 発生後も全ページ render 継続 | **活き残り（L-1 プランへ吸収・D-03）** | `ocr.py:358-386`（`_producer()` は `fatal["msg"]` を一切チェックせず `page_indices` を最後まで走査し続ける）。これは未使用ヘルパー内の挙動だが、一本化後の新パイプラインで踏襲しないよう明記が必要 | V171-OCR-04（L-1 プラン内） |
| L-6h | sentinel `buf.put(None)` の暗黙容量不変条件の明文化 | **活き残り（L-1 プランへ吸収・D-03）** | `ocr.py:383-386`（`finally: for _ in range(workers): buf.put(None)` — バッファ容量 `workers+1` に対し終端シグナル `workers` 個を無条件 blocking put する不変条件が docstring に無い）。`ocr_dialog.py` 側は `put_nowait` + 再試行で同種の課題を回避済み（:1341-1345,1356-1364） | V171-OCR-04（L-1 プラン内） |
| L-6i | `_fetch_models` / `_test_connection` のほぼ完全重複 | **活き残り** | `dialogs/llm_config.py:1120-1141`（`_fetch_models`）と `:1142-1161`（`_test_connection`）はロジックがほぼ同一（`list_models()` 呼び出し + 例外処理 + ステータス表示のみ差分は Combobox 更新の有無） | V171-OCR-01 |
| L-6j | OCR ダイアログ内で "off" 切替時に `app._update_ocr_buttons_state()` 未呼出 | **活き残り** | `ocr_dialog.py:842-957`（`_apply_llm_settings` は `self.app.settings.update()` と provider 再生成のみ行い `self.app._update_ocr_buttons_state()` を呼ばない）。メイン画面のツールバー OCR ボタンは "off" へ切替後も enabled のまま残る可能性がある（`app.py:190-202` の `_update_ocr_buttons_state` が唯一の同期経路） | V171-OCR-01 |
| L-6k | CLAUDE.md「ファイル構成」の更新 | **解消済み** | 260610-fast クイックタスクで対応済み（STATE.md Quick Tasks Completed 参照）。ただし本フェーズで `ocr_pipeline.py` を新設するため D-02 により**再度 1 行追記が必要**（新規追記であり L-6k の再発ではない） | V171-OCR-04（D-02） |

### Phase 4 への繰り越し候補（D-11・スコープ外の発見事項）

照合中に発見した、L-6 に明記されていない類似の軽微事項（V171-TEST-03 へ送る）:

- `dialogs/llm_config.py:1164-1209` の `_fetch_ollama_models`/`_test_ollama_connection` も `_fetch_models`/`_test_connection`（LM Studio 用）とほぼ同一の重複パターンを持つ。L-6i は LM Studio ペアのみを明記しているため、Ollama ペアの解消は D-11 に従い本フェーズの対象外とし、Phase 4（V171-TEST-03）または L-6i 解消時の設計が Ollama にも自然に転用可能な形（共通ヘルパー抽出）であれば計画時に一緒に倒すことを検討してよい（新規スコープではなく既存項目の自然な波及として扱う）。
- `RunPodProvider.list_models()`（`ocr_providers.py:1397-1424`）は `base_url.endswith("/v1")` の分岐が両方とも同じ `endpoint = base_url + "/models"` を返しており、分岐が無意味（デッドコード）。L-6 に明記なし → Phase 4 棚卸し対象として記録。

## Architecture Patterns

### System Architecture Diagram

OCR 実行時のデータフロー（一本化後の目標構成）:

```
[OCRDialog._on_run]  (Tkinter メインスレッド)
        │
        ├─ 埋め込みテキスト判定 (has_embedded_text) ─┐
        │                                            ▼
        │                                    results へ直接投入 (スキップ)
        │
        ▼
[_render_next_page]  after(0) 連鎖・メインスレッドのみ
        │  fitz.Page.get_pixmap() → PNG → base64  (V14-D-05 制約)
        │
        ▼  ocr_pipeline.try_enqueue(buf, item)  ← 新設・非ブロッキング put
   ┌────────────────────────────┐
   │  queue.Queue(maxsize=N+1)  │  ← ocr_pipeline が生成・容量計算を一元化
   └────────────────────────────┘
        │
        ▼  N 本のワーカースレッド (threading.Thread × concurrency)
[ocr_pipeline.consume_one]  ← 新設・Tk 非依存の1アイテム処理関数
        │
        ├─ provider.ocr_image_ex(b64, prompt) ──▶ [OCRProvider サブクラス] ──▶ HTTP/subprocess
        │       │
        │       ├─ OCRRetryableError → interruptible_sleep + リトライ (MAX_RETRIES)
        │       ├─ ConnectionError/TimeoutError → fatal 状態へ (共有 Lock 経由)
        │       └─ 成功 → on_success コールバック (page_idx, text, truncated)
        │
        ▼  コールバック経由でメインスレッドへ復帰
[OCRDialog._on_page_done]  after(0) で呼ばれる・進捗バー/ラベル更新・世代ガード確認
        │
        ▼ (全ワーカー終了後、最終ワーカーが検知)
[OCRDialog._finish_complete / _finish_error / _finish_cancelled]
```

責務境界: 「fitz にアクセスするコード」と「Tkinter の `after`/ウィジェットにアクセスするコード」は `ocr_dialog.py` に残し、「キュー操作・リトライバックオフ・進捗カウント計算・完了判定ロジック」を `ocr_pipeline.py` へ抽出する。抽出後も producer（レンダリング）はメインスレッド駆動のままで構わない — 一本化の目的は「2つの独立した producer-consumer 実装」を「1つの実装 + 1つの呼び出し元」にすることであり、スレッドモデル自体を変える必要はない。

### Recommended Project Structure

```
pagefolio/
├── ocr.py              # 既存: プロンプト解決・build_provider・run_parallel（単発 API 一覧・変更不要）
│                        #   run_with_bounded_buffer は ocr_pipeline.py へ移設し削除
├── ocr_pipeline.py      # 新設: Tk/fitz 非依存の producer-consumer 純ロジック層（D-02）
│                        #   - キュー容量計算 (maxsize = workers + 1)
│                        #   - 非ブロッキング enqueue/sentinel 送出ヘルパー
│                        #   - 1アイテム消費処理（リトライ・バックオフ・fatal 判定）
│                        #   - 共有状態（done_count/consec_err_count/fatal 等）を保持する小さなクラス
├── ocr_dialog.py        # 既存: Tk 依存の UI 配線のみ（after 連鎖・ウィジェット更新）
│                        #   _render_next_page / _worker は ocr_pipeline.* を呼ぶ薄いラッパーへ縮小
├── ocr_providers.py     # 既存: 各プロバイダ実装。L-6e/L-6f/L-6d の共通ヘルパーをここに追加
└── plugins.py           # 既存: register_ocr_provider の堅牢化・公開アクセサ追加（L-2/L-3）

tests/
├── test_ocr_pipeline.py # 新設: run_with_bounded_buffer 由来のテストを移設・拡充（D-02）
├── test_ocr.py          # 既存: run_with_bounded_buffer 専用テストを test_ocr_pipeline.py へ移動後、重複削除
├── test_ocr_providers.py# 既存: URL スキーム検証・Gemini エスケープ・エラー body 切り詰めのテスト追加
├── test_ocr_dialog.py または test_provider_ui.py  # 既存: L-6a（progress bar）・L-6j（off 切替ボタン状態）の回帰テスト追加
└── test_plugins.py      # 既存: 重複名警告・unload 解除・公開アクセサのテスト追加
```

### Pattern 1: Tk 非依存の共有状態オブジェクト

**What:** 現行 `ocr_dialog.py` の `_done_lock`/`_done_count`/`_workers_remaining`/`_fatal_msg`/`_fatal_kind`/`_consec_err_count` は `self.*` 属性として Tkinter インスタンスに直接生えている。これを Tk 非依存の小さな状態クラス（例: `PipelineState`）に切り出し、`ocr_pipeline.py` で定義してテスト可能にする。

**When to use:** L-1 一本化の中心パターン。複数ワーカースレッドが共有カウンタを更新する箇所すべてに適用。

**Example（既存の Tk 依存版・置き換え対象）:**
```python
# Source: pagefolio/ocr_dialog.py:135-143（現状）
self._done_lock = threading.Lock()
self._done_count = 0
self._workers_remaining = 0
self._fatal_msg = None
self._fatal_kind = None
self._consec_err_count = 0
```

**推奨する Tk 非依存版のイメージ（Claude's Discretion・具体形は実装時に確定）:**
```python
# ocr_pipeline.py（新設イメージ）
import threading

class PipelineState:
    """producer-consumer 実行中の共有状態（Tk/fitz 非依存）。"""
    def __init__(self, workers):
        self._lock = threading.Lock()
        self.done_count = 0
        self.consec_err_count = 0
        self.workers_remaining = workers
        self.fatal_msg = None
        self.fatal_kind = None

    def record_success(self):
        with self._lock:
            self.done_count += 1
            self.consec_err_count = 0

    def record_retryable_failure(self, msg, circuit_breaker_threshold):
        with self._lock:
            self.done_count += 1
            self.consec_err_count += 1
            hit_breaker = self.consec_err_count >= circuit_breaker_threshold
            if hit_breaker and self.fatal_msg is None:
                self.fatal_msg = msg
                self.fatal_kind = "circuit_breaker"
            return hit_breaker
```

### Pattern 2: 非ブロッキング producer（Tk `after()` 駆動）

**What:** `ocr_dialog.py:1323-1414`（`_render_next_page`）は fitz レンダリングをメインスレッドで行うため、専用スレッドを持てない。`queue.Full` 時は `_render_idx` を進めずに `after(100, ...)` で自分自身を再スケジュールする。これは `run_with_bounded_buffer` の `_producer`（専用スレッド + `timeout=0.1` busy-wait）とは根本的に異なる駆動方式であり、**一本化後もこの方式を維持する**（D-01: dialog の実戦挙動が仕様）。

**When to use:** producer 側の抽出時、`ocr_pipeline.py` には「キューへの非ブロッキング put を試み、成功/失敗を bool で返す」関数のみを置き、「いつ再試行するか」（`after(100, ...)`）は呼び出し元（`ocr_dialog.py`）の責務として残す。

**Example（現状の該当箇所）:**
```python
# Source: pagefolio/ocr_dialog.py:1397-1406
b64 = page_to_png_b64(page, scale=self._ocr_scale)
try:
    self._render_queue.put_nowait((page_idx, b64))
except queue.Full:
    g = gen
    self.after(100, lambda _g=g: self._render_next_page(_g))
    return
```

### Pattern 3: sentinel（終了シグナル）の非ブロッキング送出と再試行

**What:** consumer に終了を伝える `None` センチネルは workers 本ぶん送る必要があるが、キューが満杯なら送りきれない。`ocr_dialog.py` は非ブロッキングで送れた数を数え、送りきれなければ `after(100, ...)` で残りを再送する。この不変条件（「センチネルは合計 workers 本、送信済み分は再送しない」）は L-6h の明文化対象であり、`ocr_pipeline.py` の docstring に必ず記載すること。

**Example:**
```python
# Source: pagefolio/ocr_dialog.py:1352-1365
sent = 0
for _ in range(self.concurrency):
    try:
        self._render_queue.put_nowait(None)
        sent += 1
    except queue.Full:
        break
if sent < self.concurrency:
    g = gen
    self.after(100, lambda _g=g: self._render_next_page(_g))
```

### Pattern 4: URL スキーム検証の共通ヘルパー（L-6e/D-13）

**What:** LM Studio / Ollama / RunPod の3プロバイダとも、ユーザー入力 URL をそのまま `urllib.request.Request` に渡している。共通ヘルパーを `ocr_providers.py` に1つ追加し、各プロバイダの HTTP 呼び出し直前（`_post_chat`/`list_models` 等）で呼ぶ。

**When to use:** リクエスト送信の直前（コンストラクタでの eager 検証は避ける — 空 URL や入力途中の値でもプロバイダのインスタンス化自体は失敗させない既存方針と整合させる）。

**Example（新設イメージ・Claude's Discretion で最終形は決定）:**
```python
# ocr_providers.py に追加するイメージ
from urllib.parse import urlsplit

_ALLOWED_URL_SCHEMES = ("http", "https")

def _require_http_scheme(url):
    """url のスキームが http/https のみであることを検証する（L-6e・D-13）。

    例外: RuntimeError — スキームが http/https 以外（file:// 等の悪用防止）。
    """
    scheme = urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_URL_SCHEMES:
        raise RuntimeError(f"サポートされていない URL スキームです: {scheme or url}")
```

呼び出し箇所の候補: `LMStudioProvider._post_chat`（:296 の `endpoint` 生成直後）・`LMStudioProvider.list_models`（:370）・`OllamaProvider._post_chat`（:1145）・`OllamaProvider.list_models`（:1220）・`RunPodProvider._post_chat`（:1372）・`RunPodProvider.list_models`（:1409）。既存の例外規約（`ConnectionError`/`TimeoutError`/`RuntimeError`）に沿って `RuntimeError` を選択すること。

### Pattern 5: Gemini モデル名の URL エスケープ（L-6f）

**Example:**
```python
# 変更前: pagefolio/ocr_providers.py:811
endpoint = self.GENERATE_CONTENT_ENDPOINT.format(model=self.model)

# 変更後イメージ
from urllib.parse import quote
endpoint = self.GENERATE_CONTENT_ENDPOINT.format(model=quote(self.model, safe=""))
```

### Anti-Patterns to Avoid

- **ヘルパーの理想仕様に dialog を合わせる（D-01 の逆方向）:** L-1 一本化で `ocr_dialog.py` 側の挙動を `run_with_bounded_buffer` 側に寄せてはいけない。`ocr_dialog.py` は実戦稼働しており回帰リスクが高い。必ず「dialog の挙動を仕様として書き下し、ヘルパー側をそれに合わせる」方向で進める。
- **`_provider_registry` を公開属性化する:** D-10 は公開アクセサメソッド追加を求めているが、`_provider_registry` 自体を `provider_registry`（アンダースコアなし）にリネームして「公開」するのは過剰。既存の私有属性のままにし、アクセサ経由のみで到達可能にする。
- **Tesseract 言語検出をリクエストの都度 subprocess 実行にする:** `ocr_image` 呼び出しの都度 `tesseract --list-langs` を subprocess 実行すると、並列 OCR 中に同時に何本も subprocess が起動し得る。D-05 は「build_provider の都度（＝プロバイダ生成時）」であり「ocr_image 呼び出しの都度」ではない点に注意。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| URL のスキーム判定 | 独自の正規表現（`^https?://`）や文字列 `startswith` チェック | `urllib.parse.urlsplit(url).scheme` | IPv6 ホスト・ポート付き URL・大文字小文字混在スキームなどのエッジケースを標準ライブラリが正しく処理する |
| URL パスセグメントのエスケープ | 手書きの文字置換 | `urllib.parse.quote(value, safe="")` | RFC 3986 準拠のパーセントエンコーディングを保証する |
| producer-consumer の同期プリミティブ | 自作スピンロック・カスタムイベントフラグ | `queue.Queue` + `threading.Lock`/`threading.Event`（既存パターン継続） | 既にプロジェクト全体で確立されたパターンであり、新規実装は回帰リスクを増やすだけ |

**Key insight:** 本フェーズで「新しく作る」べきものはほぼない。既存の 2 つの実装のうち実戦済みの方（`ocr_dialog.py`）を仕様として、未使用の方（`ocr.py::run_with_bounded_buffer`）を作り直すのが唯一の大きな変更である。それ以外（L-2〜L-4・L-6）はすべて数行〜数十行のピンポイント修正であり、新規抽象化を導入する必要はない。

## Runtime State Inventory

> リネーム/リファクタ相当のトリガー（`run_with_bounded_buffer` の `ocr_pipeline.py` への移設・テストファイル移動）に該当するため記載する。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | なし — OCR パイプラインの状態はプロセス内メモリのみで、`pagefolio_settings.json` や外部ストアに永続化される値は存在しない。`tesseract_lang` は既存の settings キーで本フェーズでは変更しない | なし |
| Live service config | なし — 外部サービス（n8n 等）への依存なし。プラグイン登録はプロセス起動時に `discover_plugins()`/`load_all()` でメモリ上に構築されるのみで、ディスク上の別ストアは持たない | なし |
| OS-registered state | なし — Windows タスクスケジューラ等への登録はこのアプリの機能に存在しない | なし |
| Secrets/env vars | なし — 本フェーズは `ANTHROPIC_API_KEY`/`GEMINI_API_KEY`/`RUNPOD_API_KEY` の解決ロジック（Phase 1 で確定）に触れない | なし |
| Build artifacts / installed packages | `run_with_bounded_buffer` を `ocr.py` から削除し `ocr_pipeline.py` へ移設すると、`from pagefolio.ocr import run_with_bounded_buffer` の形で外部 import している箇所があれば壊れる（現状は `tests/test_ocr.py` のみ import しており、プラグイン等の外部コードからの参照は `plugins/page_info.py`（サンプルプラグイン）を含め確認済みで無し）。テスト側の import 文更新と `tests/test_ocr_pipeline.py` への物理移動が必要 | コード編集（import 文更新）+ テストファイル移動。データ移行は不要 |

**結論:** 本フェーズはランタイム状態（DB・外部サービス・OS登録・シークレット）に一切影響しない、コード内シンボル移動のみのリファクタリングである。唯一の実務対応は `run_with_bounded_buffer` の import パス変更（`ocr.py` → `ocr_pipeline.py`）とテストファイルの物理移動。

## Common Pitfalls

### Pitfall 1: producer 側を「専用スレッド」化してしまう
**What goes wrong:** `run_with_bounded_buffer` の `_producer()` は専用 `threading.Thread` として実装されている。一本化時にこの構造をそのまま `ocr_pipeline.py` の「正」として採用すると、`ocr_dialog.py` 側の「メインスレッド `after()` 連鎖でレンダリングする」既存動作（V14-D-05 制約への対応）と衝突する。
**Why it happens:** 2つの実装の表面的な類似性（どちらも producer-consumer）から、「どちらか片方をそのまま採用すればよい」と誤解しやすい。
**How to avoid:** D-01 に従い、producer 側のスレッドモデルは `ocr_dialog.py`（メインスレッド駆動）を正とする。`ocr_pipeline.py` の producer 関連 API は「レンダリング方法」を規定せず「キューへの安全な enqueue/sentinel 送出」のみを提供する薄いユーティリティに留める。
**Warning signs:** `ocr_pipeline.py` に `threading.Thread` を生成するコードが producer 側に現れたら要注意（consumer 側のワーカースレッドは問題ない）。

### Pitfall 2: `_TESSERACT_LANGS` のグローバル参照箇所を取りこぼす
**What goes wrong:** D-05（再検出化）を `ocr_providers.py` 内だけで完結させると、`dialogs/llm_config.py` の4箇所（:14-15 の import・:142・:646・:970・:1364-1366）が古いモジュール定数を参照し続け、UI 側の言語選択肢と実行時挙動が食い違う。
**Why it happens:** `_TESSERACT_LANGS`/`_TESSERACT_AVAILABLE` はモジュールレベル定数として2ファイルから直接 import されており、片方だけ変更すると不整合が生じる。
**How to avoid:** 再検出関数（例: `_detect_tesseract()` を公開関数化）を `ocr_providers.py` に置き、`llm_config.py` 側も同じ関数を呼ぶよう統一する。またはキャッシュ戦略（Claude's Discretion）を決めた上で両ファイルが同じキャッシュを参照するようにする。
**Warning signs:** UI 上のプロバイダ選択肢は tesseract 利用不可と表示するのに、実行時は動いてしまう（またはその逆）。

### Pitfall 3: 既存テスト `test_lang_fallback_to_eng_when_jpn_not_available` が新ロジックと矛盾する
**What goes wrong:** `tests/test_ocr_providers.py:1131-1157` は「`_TESSERACT_LANGS` に jpn がなければ `-l eng`」という**旧ロジック**（自動決定のみ・`self.lang` 無視）を前提にしている。D-06 の段階的縮退ロジック（`self.lang` の部分集合を優先）を実装すると、このテストの前提（`self.lang` を一切見ない）と衝突し、そのままでは意味が変わってしまう。
**Why it happens:** L-4 の修正は「`self.lang` を尊重する」という仕様変更そのものであり、既存の「`self.lang` を無視した自動決定」テストとは両立しない。
**How to avoid:** このテストは新ロジックに合わせて書き換える（削除ではなく更新）。あわせて `self.lang="deu+jpn+eng"` かつ `_TESSERACT_LANGS={"jpn","eng"}` のような「部分集合縮退」ケースのテストを新規追加する。
**Warning signs:** pytest 実行時にこのテストだけ失敗する、または「意図的な仕様変更」であることがコミットメッセージ/PLAN.md に明記されていない。

### Pitfall 4: `_raise_mapped_http_error` の変更がプロバイダ横断で全テストに波及する
**What goes wrong:** L-6d（エラー body 切り詰め）は Gemini 固有ではなく `_raise_mapped_http_error`（`ocr_providers.py:193-215`）という**全プロバイダ共通**の関数を経由する。ここを変更すると LMStudio/Claude/Gemini/Ollama/RunPod の 5 プロバイダすべてのエラーメッセージ文字列が変わり得る。
**Why it happens:** レビュー原文が「Gemini エラーメッセージの body 切り詰めなし」と Gemini 限定で記述しているため、修正範囲を Gemini だけに限定してしまいがち。
**How to avoid:** `_raise_mapped_http_error` を修正し、`tests/test_ocr_providers.py` 内の全プロバイダの HTTPError 関連テスト（エラーメッセージの完全一致 assert がある場合）を横断的に確認する。
**Warning signs:** Gemini 用テストだけ更新して他プロバイダのエラーメッセージテストが意図せず壊れる（またはメッセージ長の assert が漏れて回帰しない）。

### Pitfall 5: L-6i の重複解消が Ollama ペアへ無断で波及する
**What goes wrong:** `_fetch_models`/`_test_connection`（LM Studio 用）と `_fetch_ollama_models`/`_test_ollama_connection`（Ollama 用）はほぼ同型の重複を持つが、L-6 原文は LM Studio ペアのみを明記している。D-11（リスト外項目は Phase 4 送り）に従わず Ollama ペアまで無断でリファクタすると、フェーズ境界の逸脱になる。
**Why it happens:** 共通ヘルパー抽出という解決策が両ペアに自然に適用できてしまうため、「ついでに直す」誘惑が働く。
**How to avoid:** 計画時に「LM Studio ペアのみ解消」と明記するか、共通ヘルパーの設計自体が Ollama ペアにも波及することを認識した上で PLAN.md にスコープ拡張として明示的に記載する（D-11 は「新規スコープ拡張」を禁止していないが、記録なしの暗黙拡張を禁止している）。
**Warning signs:** コミットメッセージや PLAN.md に Ollama 側の変更理由が書かれていない。

### Pitfall 6: `_apply_llm_settings` への `_update_ocr_buttons_state()` 追加が provider 例外パスを見落とす
**What goes wrong:** L-6j 修正時、`_apply_llm_settings`（`ocr_dialog.py:842-957`）の正常系末尾に `self.app._update_ocr_buttons_state()` を追加するだけでは、provider 再生成が例外で失敗した場合（:952-955 の `except Exception as e:` 分岐）にボタン状態が更新されないままになる可能性がある。
**Why it happens:** 例外分岐は `progress_var` の更新のみ行い、関数の残り（ボタン状態更新）が実行されないまま return するように見えるが、実際は例外後も関数末尾（:957 `self._update_summary_btn_state()`）まで到達する構造になっている点を見落としやすい。
**How to avoid:** `_update_ocr_buttons_state()` の呼び出しは try/except の外側（関数末尾、`_update_summary_btn_state()` 呼び出しの近く）に置き、例外の有無にかかわらず実行されるようにする。
**Warning signs:** provider 再生成が失敗するケース（例: 不正な設定値）で OCR ボタンの活性状態がテストされていない。

## Code Examples

### 現行の `_worker`（consumer）の中核ロジック（一本化の抽出対象）

```python
# Source: pagefolio/ocr_dialog.py:1466-1528（リトライ・fatal 判定の核心部分）
for attempt in range(1, MAX_RETRIES + 1):
    try:
        text, truncated = self.provider.ocr_image_ex(b64, self._ocr_prompt)
        self._record_page_success(page_idx, text, truncated=truncated)
        break
    except OCRRetryableError as e:
        if attempt >= MAX_RETRIES:
            self._record_retryable_failure(page_idx, str(e))
            break
        raw_delay = (
            e.retry_after if e.retry_after is not None
            else 1.0 * (2 ** (attempt - 1))
        )
        delay = clamp_retry_after(raw_delay)
        interruptible_sleep(delay, self._cancel_flag.is_set)
    except ConnectionError as e:
        with self._done_lock:
            if self._fatal_msg is None:
                self._fatal_msg = str(e)
                self._fatal_kind = "connection"
            self._done_count += 1
        break
    # ... TimeoutError / RuntimeError / Exception も同型で処理
```

このロジックは `self.after()` や `self.text`（Tk ウィジェット）に一切依存していない。`ocr_pipeline.py` へそのまま移設可能な部分の代表例。

### 現行の `run_with_bounded_buffer`（置き換え対象・テストのみ消費）

```python
# Source: pagefolio/ocr.py:358-386（producer 部分・fatal 未チェックの欠陥を含む）
def _producer():
    try:
        for page_idx in page_indices:
            if _is_cancelled():
                break
            try:
                b64 = render_fn(page_idx)
            except Exception as e:
                errors[page_idx] = f"render error: {e}"
                continue
            if b64 is None:
                continue
            while True:
                if _is_cancelled():
                    return
                try:
                    buf.put((page_idx, b64), timeout=0.1)
                    break
                except queue.Full:
                    continue
    finally:
        for _ in range(workers):
            buf.put(None)  # L-6h: 無条件 blocking put（容量不変条件の明文化対象）
```

一本化後はこの「専用スレッド + blocking put」構造ではなく、`ocr_dialog.py` の「メインスレッド `after()` + non-blocking put + 再スケジュール」構造を正とする（D-01）。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| producer-consumer が `ocr.py`（未使用）と `ocr_dialog.py`（実運用）に二重実装 | `ocr_pipeline.py` に一本化し、`ocr_dialog.py` は Tk 配線のみの薄いラッパーになる | 本フェーズ（V171-OCR-04） | 保守対象が1箇所になり、L-6a/L-6g/L-6h も同時に解消される |
| `_TESSERACT_LANGS` は起動時1回検出（再起動まで固定） | プロバイダ生成時（`build_provider` 呼び出し毎）に再検出 | 本フェーズ（V171-OCR-02・D-05） | 言語パック追加後の反映に再起動不要になる（数十ms のコスト増と引き換え） |
| `_provider_registry` への直接アクセス | `get_ocr_provider(name)`/`list_ocr_providers()` 経由 | 本フェーズ（V171-OCR-03・D-10） | プラグイン API の安定した公開面ができ、将来の内部実装変更が破壊的変更にならない |

**Deprecated/outdated:**
- `pagefolio/ocr.py::run_with_bounded_buffer`: 一本化後は削除し `ocr_pipeline.py` の新実装に置き換える。本番未使用のまま残すのはコード衛生上望ましくない（L-1 の根本原因）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ocr_pipeline.py` の producer 側は「専用スレッドを持たない」設計にすべき（V14-D-05 制約とメインスレッド `after()` 駆動の両立のため） | Architecture Patterns Pattern 2 | もし将来 fitz レンダリングをワーカースレッドへ移せる制約緩和（例: PyMuPDF の将来バージョンでのスレッドセーフ保証）があれば、この設計判断は再考の余地がある。現時点（PyMuPDF 1.27.2.2）では V14-D-05 制約が有効なため ASSUMED ではなく現行制約からの導出だが、"今後もメインスレッド駆動を維持すべき" という設計方針自体は ASSUMED |
| A2 | URL スキーム検証は「リクエスト送信直前（`_post_chat`/`list_models` 冒頭）」に行うべきで、`__init__` での eager 検証は避けるべき | Architecture Patterns Pattern 4 | 既存の「空URL/未確定入力でもインスタンス化は失敗しない」という暗黙の設計方針からの推測。実際にコンストラクタで検証しても実害がない可能性があり、計画時に実装しやすい方を選んでよい |
| A3 | Tesseract 言語再検出のコストは「プロバイダ生成の都度で頻度的に無視できる」（D-05 原文のコピー） | User Constraints D-05 | 実測していない。低スペック環境や WSL/コンテナ越しの subprocess 起動で数百ms かかる可能性があり、体感遅延が問題になる場合はキャッシュ戦略（Claude's Discretion）の採用が必須になる |

**リスク低減策:** A1/A2 は設計判断であり実装時の柔軟性を残すよう Architecture Patterns セクションで「Claude's Discretion」と明記済み。A3 は実装後に体感確認（`checkpoint:human-verify` 相当の確認）を計画に含めることを推奨。

## Open Questions (RESOLVED)

> 3 問すべて計画時（2026-07-05 /gsd-plan-phase 2）に解決済み。採用結論は各質問末尾の **RESOLVED** 行を参照。

1. **`run_with_bounded_buffer` を完全削除するか、後方互換のため薄いラッパーとして残すか**
   - What we know: 本番コードからの参照はゼロ（`build_provider`/`OCRMixin` から未参照）。テストのみが直接呼んでいる。
   - What's unclear: プラグイン開発者や外部ドキュメント（README 等）がこの関数名を公開 API として言及していないか未確認。
   - Recommendation: `grep -rn "run_with_bounded_buffer" README.md 開発履歴.md plugins/` で外部言及がないことを確認してから完全削除する。あれば非推奨コメント付きでエイリアス関数として残す。
   - **RESOLVED（02-04-PLAN.md Task 2）:** 完全削除を採用。実行時に grep で外部参照ゼロを確認してから削除する手順を Task 2 の action に組み込み済み。

2. **`_fetch_models`/`_test_connection` 統合時の戻り値契約（Combobox 更新の有無）をどう表現するか**
   - What we know: 唯一の実質差分は「取得したモデル一覧を Combobox に反映するか否か」。
   - What's unclear: 共通ヘルパーに bool フラグを渡す方式か、`_fetch_models` が `_test_connection` を内部で呼ぶ方式か、実装上の優劣は僅差。
   - Recommendation: 既存の呼び出し元（ボタンの `command=`）を変えずに済む「内部ヘルパー抽出 + 各関数はそれぞれ薄いラッパーとして残す」方式を推奨（呼び出し元の変更ゼロで済む）。
   - **RESOLVED（02-03-PLAN.md Task 2）:** 推奨どおり共通ヘルパー抽出方式を採用。Combobox 更新の有無は bool フラグでパラメータ化し、`_fetch_models`/`_test_connection` は薄いラッパーとして残す（呼び出し元は不変）。

3. **ClaudeProvider `list_models` ページネーション対応は本フェーズでやるか Phase 4 送りか**
   - What we know: 現行モデル数（`RECOMMENDED_MODELS` 3件 + API から返る実モデル数）はページ上限を超えていない可能性が高い。
   - What's unclear: Anthropic API のデフォルトページサイズと現在の登録モデル総数の実測値。
   - Recommendation: 計画時に「V171-OCR-01 の対象に含めるか」を明示的に判断する。含める場合は `has_more`/`last_id` を辿るループ実装が必要（軽微だが未実装のためゼロから書く）。含めない場合は Phase 4 の V171-TEST-03 棚卸しへ明示的に送る。
   - **RESOLVED（02-03-PLAN.md Task 1）:** 本フェーズ（V171-OCR-01）に含める。スコープ縮小禁止方針に従い `has_more`/`last_id` カーソルを辿るページネーションを実装する。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 標準ライブラリ（`queue`/`threading`/`urllib.parse`/`subprocess`） | 全項目 | ✓ | Python 3.8+ 同梱 | — |
| Tesseract CLI（実機） | V171-OCR-02 の動作確認（`_detect_tesseract`/`ocr_image`） | 要確認（開発機依存） | — | 未インストール環境でも `_detect_tesseract()` は `(False, frozenset())` を返し安全側に倒れる（既存動作）。単体テストは `subprocess.run` を monkeypatch するため実機インストール不要 |
| pytest / ruff（既存開発ツール） | 全項目の検証 | ✓（`requirements.txt`/開発環境に既存） | pytest 9.0.2 / ruff 0.15.7 | — |

**Missing dependencies with no fallback:** なし。

**Missing dependencies with fallback:** Tesseract CLI 実機（テストは monkeypatch でカバーされるため計画・実装に支障なし。実機での最終確認は `checkpoint:human-verify` 推奨）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2（`pytest-cov` 7.1.0 併用） |
| Config file | `pyproject.toml`（`pythonpath = ["src"]` 等・本フェーズでは編集禁止 — CLAUDE.md 規約） |
| Quick run command | `pytest tests/test_ocr.py tests/test_ocr_providers.py tests/test_provider_ui.py tests/test_plugins.py -q` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V171-OCR-04 | 一本化後もバッファ上限（concurrency+1）を超えて画像を同時保持しない | unit | `pytest tests/test_ocr_pipeline.py::TestProducerConsumerMemory::test_in_flight_count_never_exceeds_maxsize -x` | ❌ Wave 0（`test_ocr.py:1240` から移設） |
| V171-OCR-04 | キャンセル時に有限時間で終了しデッドロックしない | unit | `pytest tests/test_ocr_pipeline.py::TestProducerConsumerMemory::test_cancel_terminates_without_deadlock -x` | ❌ Wave 0（移設） |
| V171-OCR-04 | 既存 OCR 実行の並列/リトライ/進捗が回帰しない | regression | `pytest tests/test_ocr.py tests/test_provider_ui.py -q` | ✅（既存） |
| V171-OCR-02 | `self.lang` の言語のうち利用可能な部分集合が優先される | unit | `pytest tests/test_ocr_providers.py::TestTesseractProviderOcrImage -x` | ⚠️ 既存テストは新ロジック向けに更新が必要（Pitfall 3） |
| V171-OCR-02 | プロバイダ生成の都度 `tesseract --list-langs` が再評価される | unit | `pytest tests/test_ocr_providers.py -k tesseract_redetect -x` | ❌ Wave 0（新規） |
| V171-OCR-03 | 組み込み名との重複登録が警告され拒否される | unit | `pytest tests/test_plugins.py -k duplicate_builtin -x` | ❌ Wave 0（新規） |
| V171-OCR-03 | unload 時に registry から登録解除される | unit | `pytest tests/test_plugins.py -k unload_deregisters -x` | ❌ Wave 0（新規） |
| V171-OCR-03 | `get_ocr_provider`/`list_ocr_providers` が正しく動作する | unit | `pytest tests/test_plugins.py -k public_accessor -x` | ❌ Wave 0（新規） |
| V171-OCR-01 | URL スキーム検証（http/https 以外で RuntimeError） | unit | `pytest tests/test_ocr_providers.py -k url_scheme -x` | ❌ Wave 0（新規） |
| V171-OCR-01 | Gemini モデル名が URL エスケープされる | unit | `pytest tests/test_ocr_providers.py -k gemini_model_escape -x` | ❌ Wave 0（新規） |
| V171-OCR-01 | エラー body が一定長で切り詰められる | unit | `pytest tests/test_ocr_providers.py -k error_body_truncat -x` | ❌ Wave 0（新規） |
| V171-OCR-01 | "off" 切替後にツールバー OCR ボタンが disabled になる | unit/integration | `pytest tests/test_provider_ui.py -k off_toggle_buttons -x` | ❌ Wave 0（新規） |
| V171-OCR-01 | レンダー失敗ページでも進捗が 100% に到達する | unit | `pytest tests/test_ocr_pipeline.py -k render_failure_progress -x`（L-1 プラン内） | ❌ Wave 0（新規） |

### Sampling Rate
- **Per task commit:** `pytest tests/test_ocr.py tests/test_ocr_providers.py tests/test_provider_ui.py tests/test_plugins.py -q`
- **Per wave merge:** `pytest`（フルスイート・707件超のグリーン維持を確認）
- **Phase gate:** フルスイート green + `ruff check . && ruff format .` を `/gsd-verify-work` 前に確認

### Wave 0 Gaps
- [ ] `tests/test_ocr_pipeline.py` — 新設。`test_ocr.py:1230-1327` の `TestProducerConsumerMemory` 3件を移設し、`ocr_pipeline.py` の新 API に合わせて書き換える（V171-OCR-04）
- [ ] `tests/test_ocr_providers.py` に URL スキーム検証・Gemini エスケープ・エラー body 切り詰めの新規テストケースを追加（V171-OCR-01）
- [ ] `tests/test_ocr_providers.py::TestTesseractProviderOcrImage::test_lang_fallback_to_eng_when_jpn_not_available` を D-06 の段階的縮退ロジックに合わせて更新 + 部分集合縮退の新規ケース追加（V171-OCR-02）
- [ ] `tests/test_plugins.py` に重複名警告・unload 解除・公開アクセサの新規テストケースを追加（V171-OCR-03）
- [ ] `tests/test_provider_ui.py`（または新設 `tests/test_ocr_dialog.py`）に L-6j（off 切替時のボタン状態）・L-6a（進捗100%到達）の回帰テストを追加
- [ ] フレームワークインストール: 不要（pytest は既存環境にインストール済み）

## Security Domain

> `security_enforcement` の config 設定は未確認（`.planning/config.json` 未読み取り）だが、本アプリはローカル完結のデスクトップアプリであり ASVS の大半（V2 認証・V3 セッション管理・V4 アクセス制御）は非該当。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | ローカル単一ユーザーデスクトップアプリ。APIキーはクラウド OCR プロバイダへの認証であり Phase 1 で対応済み・本フェーズ対象外 |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 該当なし（OS のファイルアクセス権限に委譲） |
| V5 Input Validation | yes | URL スキーム検証（http/https 限定・L-6e/D-13）・Gemini モデル名の URL エスケープ（L-6f）。いずれも `urllib.parse` 標準関数で対応 |
| V6 Cryptography | no | 本フェーズは暗号処理に触れない（HTTPS は urllib 既定の証明書検証に委譲・既存確認済み） |

### Known Threat Patterns for {Python urllib + subprocess desktop app}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| ユーザー設定 URL に `file://`/`ftp://` 等の非 HTTP スキームを指定し、意図しないローカルファイル読み取りや予期しないプロトコルへの接続が発生する | Tampering | `urlsplit(url).scheme in ("http", "https")` の許可リスト検証（L-6e）。実害は「ユーザー自身が自分の設定ファイルを書き換える」場合に限られ攻撃面は小さいが、プラグイン経由の設定汚染や誤操作への防御として有効 |
| Gemini モデル名（ユーザー入力/設定値）に URL 予約文字（`/`,`?`,`#` 等）が含まれ、意図しないエンドポイントへのリクエストになる | Tampering | `urllib.parse.quote(model, safe="")` でパスセグメントとしてエスケープ（L-6f） |
| Tesseract subprocess 呼び出しへの引数インジェクション | Injection | 既に対策済み（`shell=True` 不使用・引数リスト渡し・`-l` 引数の値は `_TESSERACT_LANGS`/`self.lang` 由来の検証済み文字列のみ）。D-06 の段階的縮退実装時も、`self.lang` の値をそのまま `-l` へ渡さず「`_TESSERACT_LANGS` との積集合を取った後の値」のみを渡すことで injection 面を維持すること |

## Sources

### Primary (HIGH confidence)
- `pagefolio/ocr.py`（フェーズ対象コード全読）- producer-consumer 未使用実装・build_provider・プロンプト解決
- `pagefolio/ocr_dialog.py`（フェーズ対象コード全読 2115 行）- 実運用 producer-consumer・進捗表示・LLM設定連携
- `pagefolio/ocr_providers.py`（フェーズ対象コード全読 1424 行）- 全プロバイダ実装・URL構築・エラーマッピング
- `pagefolio/plugins.py`（全読）- PluginManager・register_ocr_provider
- `pagefolio/dialogs/llm_config.py`（該当箇所抜粋）- `_fetch_models`/`_test_connection`重複・`_provider_registry`私有アクセス
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` - L-1〜L-6 原典
- `tests/test_ocr.py`・`tests/test_ocr_providers.py`・`tests/test_plugins.py` - 既存テストパターンと影響範囲確認

### Secondary (MEDIUM confidence)
- `.planning/phases/02-ocr/02-CONTEXT.md` - discuss-phase 時のスカウト結果（本 RESEARCH で最終確定に格上げ）
- `.planning/STATE.md` - v1.4.0〜v1.7.0 の解消履歴（stop_reason 対応の時期特定）

### Tertiary (LOW confidence)
- なし（本フェーズは外部ドキュメント調査を伴わず、すべて自プロジェクトのコード読解で完結）

## Metadata

**Confidence breakdown:**
- レビュー残 生き残り表: HIGH - 全項目を該当ファイルの直接読解・行番号引用で確認済み
- Architecture Patterns（L-1 一本化の設計方針）: MEDIUM - 大枠の方向性（D-01 準拠）は確定だが、`ocr_pipeline.py` の具体的な関数/クラス境界は Claude's Discretion のため実装時に確定
- Common Pitfalls: HIGH - いずれも既存コードの具体的な行・既存テストとの矛盾点を直接特定した実証的な指摘

**Research date:** 2026-07-05
**Valid until:** 30日（プロジェクト内部コードのみに依存し外部 API 仕様変更の影響を受けないため長め。ただし Anthropic/Gemini の API 仕様変更があれば L-6b/L-6d の前提が変わり得る）