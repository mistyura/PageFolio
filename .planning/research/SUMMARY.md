# Project Research Summary

**Project:** PageFolio — コード最適化プロジェクト
**Domain:** デスクトップ PDF ツール（Tkinter）への OCR プロバイダ抽象化 + クラウド Vision API 統合
**Researched:** 2026-06-06
**Confidence:** HIGH

## Executive Summary

PageFolio v1.4.0 は、現行の LM Studio 専用 OCR 実装を `OCRProvider` 抽象基底クラスへ置き換え、Claude / Gemini のクラウド Vision API と Tesseract をプラグイン的に差し替え可能にするマイルストーンである。主想定は GPU 非搭載 PC のため、低スペック対策（テキスト埋め込み判定による OCR スキップ・逐次レンダリング・`ocr_scale` 見直し）をコア要件に含める。

実装方針は **「`urllib.request` 直叩き・新規 pip 依存ゼロ」** で確定済み。公式 SDK（anthropic / google-genai）は PyInstaller の `.exe` 肥大化を招くため不採用。Claude / Gemini ともに HTTP + JSON で完結し、Tesseract も `subprocess` 経由の CLI 呼び出しで `pytesseract` 依存を回避する。

最大リスクは 3 点。(1) APIキーの平文漏洩 — `_save_settings()` が設定辞書を丸ごと JSON 保存するため、キーが混入すると平文で書き出される。(2) 全ページ base64 の一括メモリ保持 — 低 RAM 環境で 200〜500 MB がヒープに積まれる。(3) クラウド API のレート制限（特に Gemini Free Tier 10 RPM）— 現行の最大 8 並列は即 429 を誘発する。いずれも設計初期から防御する。

## Key Findings

### Recommended Stack

新規 pip 依存はゼロ。追加は Python 標準ライブラリのみで完結する。`urllib.request` で Claude / Gemini の HTTP API を直叩きし、Tesseract は `subprocess.run` で CLI を呼ぶ。APIキーは `os.environ.get()` で環境変数からのみ取得し、設定ファイルには一切書かない。詳細は [STACK.md](STACK.md) を参照。

**Core technologies:**
- `urllib.request`（標準ライブラリ）: Claude messages API / Gemini generateContent 呼び出し — 依存追加なし・PyInstaller 肥大化を回避
- `subprocess.run`（標準ライブラリ）: Tesseract CLI 呼び出し — `pytesseract` 不要・オフラインフォールバック
- `os.environ.get()`（標準ライブラリ）: APIキー取得 — 環境変数のみ・平文保存禁止の徹底

**矛盾調停（最重要）:** Claude `temperature` の可否について、STACK.md（公式ドキュメント直接確認）を正とし、`temperature` は全モデルで利用可能と確定する。設計の正典は `docs/OCRプロバイダ化_見積もり仕様.md` だが、同仕様書の「Opus 4.7/4.8 は temperature 不可」という記述は誤りであり、API 細部は STACK.md のリサーチ結果で上書きする。ただし `effort` 対応モデル（`claude-haiku-4-5` を除く）の定数管理と、実 API での `temperature`/`effort` 動作確認を Claude Provider 実装フェーズの完了条件に含め、モデル別の防御的実装とする。

### Expected Features

詳細は [FEATURES.md](FEATURES.md) を参照。

**Must have (table stakes):**
- `OCRProvider` 抽象基底 + LM Studio を Provider 実装へリファクタ — 全機能の土台
- 既定 `ocr_provider: "off"` — 外部送信・課金を望まないユーザー向けの安全なデフォルト
- APIキーは環境変数のみ・`_save_settings()` への流入ガード — セキュリティ最低基準
- テキスト埋め込み判定による OCR スキップ — コスト/速度（既にテキストがあるページに OCR をかけない）
- プロバイダ別並列度（Gemini=1 / Claude=2 / LM Studio 最大 8）— レート制限対策
- 逐次レンダリング化 — 低 RAM 環境対策
- 429 / 5xx 指数バックオフリトライ — クラウド API の安定運用

**Should have (competitive):**
- Claude Provider（messages API・effort・モデル一覧 / `ANTHROPIC_API_KEY`）— 高精度クラウド OCR
- Gemini Provider（generateContent・inline_data・モデル一覧 / `GEMINI_API_KEY`・`GOOGLE_API_KEY`）— 高精度クラウド OCR
- OCRDialog のプロバイダ選択 UI・APIキー未設定エラー — ユーザー体験

**Defer (v2+):**
- Tesseract Provider（精度劣後注記つき）— オフラインフォールバック。スコープ調整候補
- PluginManager へのプロバイダ登録フック — 拡張性。最終フェーズ

### Architecture Approach

既存の Mixin 構成（`OCRMixin` in `pagefolio/ocr.py`）を土台に、新規 `ocr_providers.py` を設けて `OCRProvider` 抽象基底と各 Provider 実装を集約する。現行の LM Studio 固有ロジックを Provider 実装へ移動し、`run_parallel()` をプロバイダ別並列度を受け取れるよう一般化する。詳細は [ARCHITECTURE.md](ARCHITECTURE.md) を参照。

**Major components:**
1. `OCRProvider`（抽象基底）— `recognize(image_bytes) -> text` インターフェース・モデル一覧・並列度ポリシー
2. `LMStudioProvider` / `ClaudeProvider` / `GeminiProvider` / `TesseractProvider` — 各実装
3. `OCRMixin.run_parallel()`（一般化）— プロバイダ別 `DEFAULT_CONCURRENCY` で `ThreadPoolExecutor` を駆動・逐次レンダリング対応
4. `has_embedded_text()`（新設）— ページのテキスト埋め込み判定で OCR スキップ
5. `OCRDialog`（拡張）— プロバイダ選択 UI・APIキー未設定エラー表示

### Critical Pitfalls

トップ 5。全文は [PITFALLS.md](PITFALLS.md) を参照。

1. **APIキーの平文漏洩** — `_save_settings()` は設定辞書を丸ごと JSON 保存するため、キーが混入すると平文で書き出される。プロバイダ実装フェーズ開始の **最初のタスク**で `NEVER_PERSIST_KEYS` ガード（環境変数のみ・設定にキーを書かない）を実装する。後回し厳禁。
2. **全ページ base64 の一括メモリ保持** — 100 ページ・scale=2.0 で 200〜500 MB がヒープに積まれる。低スペック対策フェーズの逐次レンダリング化（レンダリング→送信→`del b64`）が最重要パフォーマンス対策。
3. **Gemini Free Tier 10 RPM への過剰並列** — 現行 8 並列は即 429 を誘発。`DEFAULT_CONCURRENCY: Gemini=1, Claude=2` をクラウド Provider 導入時から設ける。
4. **fitz スレッド非安全（既存制約）** — `ThreadPoolExecutor` ワーカーに `self.doc`（`fitz.Document`）を渡せない。抽象化フェーズのリファクタ時に `_worker` 内の fitz 操作のスレッド境界を明確化し、完了条件に含める。
5. **Gemini `candidates` 空・Claude `content` 型混在** — 各プロバイダに専用パーサを実装し、安全フィルタによるブロック（Gemini）と `type != "text"` ブロック（Claude）を防御的に処理する。

## Implications for Roadmap

リサーチに基づく推奨フェーズ構成（**4 フェーズ**）。phase 番号は前マイルストーン（v1.3.0）の最終 Phase 03 から継続し、**Phase 04 から開始**する。

### Phase 04: プロバイダ抽象化（土台）
**Rationale:** 全機能の土台。先に抽象化しないと各 Provider を載せられない。
**Delivers:** `ocr_providers.py` 新設・`OCRProvider` 基底・LM Studio を Provider 実装へ移動・`run_parallel()` 一般化・`has_embedded_text()` 新設。
**Addresses:** プロバイダ抽象化・LM Studio 後方互換維持（table stakes）。
**Avoids:** fitz スレッド非安全（Pitfall #4）— スレッド境界明確化を完了条件に。

### Phase 05: Claude Provider + セキュリティ基盤 + プロバイダ選択 UI
**Rationale:** クラウド導入の最初。セキュリティ基盤（キーガード）を**最優先タスク**として先に敷く。
**Delivers:** `NEVER_PERSIST_KEYS` ガード（最優先）・`ClaudeProvider`・確認ダイアログ・429/5xx 指数バックオフリトライ・OCRDialog プロバイダ選択 UI。
**Uses:** `urllib.request` 直叩き・`ANTHROPIC_API_KEY`（STACK.md）。
**Implements:** APIキー環境変数化・プロバイダ別並列度（Claude=2）。
**完了条件:** 実 API で `temperature` + `effort` の動作確認（`haiku` の `effort` 非対応・`opus` の挙動）。

### Phase 06: Gemini Provider + 逐次レンダリング最適化
**Rationale:** メモリ削減（逐次化）と 429 対策を同時達成。Gemini は Free Tier のレート制限が最も厳しいため逐次化と相性が良い。
**Delivers:** `GeminiProvider`・`_worker` 逐次レンダリング化・`ocr_scale` デフォルト見直し（1.5 化）・プロバイダ別並列度（Gemini=1）。
**Uses:** `urllib.request`・`inline_data`・`GEMINI_API_KEY`/`GOOGLE_API_KEY`（STACK.md）。
**Avoids:** base64 一括保持（Pitfall #2）・Gemini 過剰並列（Pitfall #3）。

### Phase 07: Tesseract + PluginManager 拡張（任意）
**Rationale:** オフラインフォールバック。クラウド不可・キー未設定環境向け。スコープ調整の候補。
**Delivers:** `TesseractProvider`（`subprocess` 経由・精度劣後注記）・PluginManager へのプロバイダ登録フック・多言語文言・ドキュメント更新。
**Avoids:** Tesseract 未インストール時の graceful fallback 不備。

### Phase Ordering Rationale

- 抽象化（Phase 04）を最初に置くのは、Provider インターフェースが無いと後続のクラウド実装が載らないため。
- セキュリティ基盤（キーガード）を Phase 05 の最初に置くのは、クラウド導入と同時にキーが設定に流入しうるため。クラウド機能より前にガードを敷く。
- 逐次レンダリング（Phase 06）を Gemini と同フェーズにするのは、Gemini=1 並列が逐次処理と自然に整合し、メモリ削減と 429 対策を一度に検証できるため。
- Tesseract / プラグイン登録（Phase 07）を最後にするのは任意機能であり、スコープ調整時に切りやすいため。

### Research Flags

計画時に追加調査が要りそうなフェーズ:
- **Phase 05:** 実 API での `temperature` + `effort` 動作確認が必須（`haiku` の `effort` 非対応・`opus` の `effort: "low"` 挙動）。実装中に裏取りする。
- **Phase 06:** 逐次化後の `run_parallel()` 活用方針の確定・Gemini Free Tier の実 RPM 確認。

標準パターンで追加調査不要なフェーズ:
- **Phase 04:** 既存コードのリファクタが主体。コードベースは実読済み。

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | 公式 API ドキュメントを直接確認。新規依存ゼロで方針が明確 |
| Features | HIGH | 仕様書を正典とし、temperature 矛盾は STACK 優先で調停済み |
| Architecture | HIGH | 既存 `OCRMixin` / `ocr.py` を実読のうえ統合設計を確定 |
| Pitfalls | HIGH | コードベース直接調査 + 公式エラー仕様（429/5xx・content 型）確認 |

**Overall confidence:** HIGH

### Gaps to Address

- `temperature` / `effort` の実 API 確認: Phase 05 実装中に実リクエストで検証。モデル別に防御的実装し、非対応時は当該パラメータを送らない。
- Gemini Free Tier の実際の RPM: Phase 06 で実測。並列度 1 を起点に、429 が出なければ段階的に緩めるか判断。
- 逐次化後の `run_parallel()` 活用方針: Phase 06 で逐次レンダリングと並列送信の境界を確定。

## Sources

### Primary (HIGH confidence)
- Anthropic 公式 messages API ドキュメント — モデルID・`temperature`/`effort` 可否・`content` ブロック型
- Google Gemini 公式 generateContent ドキュメント — `inline_data`・`candidates` 構造・Free Tier レート制限
- PageFolio コードベース（`pagefolio/ocr.py`・`pagefolio/ocr_dialog.py`・`pagefolio/settings.py`）— 既存 OCR 実装・`_save_settings()`・スレッド境界

### Secondary (MEDIUM confidence)
- `docs/OCRプロバイダ化_見積もり仕様.md` — 設計の正典（確定スコープ・フェーズ分割・工数）。ただし API 細部の temperature 記述は STACK.md で上書き

### Tertiary (LOW confidence)
- Tesseract CLI のオフライン挙動 — Phase 07 前に未インストール Windows 環境で手動確認が必要

---
*Research completed: 2026-06-06*
*Ready for roadmap: yes*
