# Roadmap: PageFolio コード最適化

## Milestones

- ✅ **v1.3.0 コード最適化 MVP** — Phases 1-3 (shipped 2026-06-03) — [archive](milestones/v1.3.0-ROADMAP.md)
- 🔄 **v1.4.0 OCR プロバイダ化 + クラウドAPI対応** — Phases 4-7 (in progress)

## Phases

<details>
<summary>✅ v1.3.0 コード最適化 MVP (Phases 1-3) — SHIPPED 2026-06-03</summary>

- [x] Phase 1: Undo/Redo 修正 (3/3 plans) — completed 2026-06-03
- [x] Phase 2: プレビュー最適化とリファクタリング (3/3 plans) — completed 2026-06-03
- [x] Phase 3: API 整理と回帰テスト (2/2 plans) — completed 2026-06-03

全フェーズの詳細・成功基準・プラン内訳は [milestones/v1.3.0-ROADMAP.md](milestones/v1.3.0-ROADMAP.md) を参照。

</details>

### v1.4.0 OCR プロバイダ化 + クラウドAPI対応 (Phases 4-7)

- [ ] **Phase 4: プロバイダ抽象化** — `OCRProvider` 基底・LM Studio を Provider 実装へ移動・`run_parallel()` 一般化・テキスト埋め込みスキップ
- [x] **Phase 5: Claude Provider + セキュリティ基盤 + プロバイダ選択 UI** — APIキーガード最優先・ClaudeProvider・確認ダイアログ・バックオフ・SettingsDialog UI (completed 2026-06-07)
- [x] **Phase 6: Gemini Provider + 逐次レンダリング最適化** — GeminiProvider・ページ単位逐次化・`ocr_scale` 見直し・OCR モックテスト (検証: gaps_found — SC-2/OCR-PERF-02 BLOCKER → 06-04 ギャップクロージャで対応) (completed 2026-06-07)
- [ ] **Phase 7: Tesseract + PluginManager 拡張 + QA** — TesseractProvider（任意）・プロバイダ登録フック・多言語文言・ドキュメント更新

## Phase Details

### Phase 4: プロバイダ抽象化

**Goal**: プロバイダを差し替え可能にする土台が整い、LM Studio が従来どおり動作する
**Depends on**: Phase 3（v1.3.0 完了済み）
**Requirements**: OCR-PROV-01, OCR-PROV-02, OCR-PROV-03, OCR-PERF-01
**Success Criteria** (what must be TRUE):

  1. LM Studio で OCR を実行したとき、v1.3.0 と同じ結果・同じ UI 操作で完了する（後方互換）
  2. テキストが埋め込まれたページに OCR を実行したとき、API 呼び出しが行われずに `page.get_text()` の結果が返される
  3. ワーカースレッド内で `fitz.Document` / `get_pixmap()` の直接呼び出しが一切存在しない（スレッド境界が明確）
  4. 新しいプロバイダクラスをファイルに追加するだけで `run_parallel()` から呼び出せる（プロバイダ別並列度が受け取れる）**Plans**: 4 plans

**Wave 1**

  - [x] 04-01-PLAN.md — OCRProvider 抽象基底 + OCRAPIKeyError + LMStudioProvider 新設（ocr_providers.py）

**Wave 2** *(blocked on Wave 1 completion)*

  - [x] 04-02-PLAN.md — run_parallel 一般化 + has_embedded_text + build_provider + OCRMixin 中立化（ocr.py）

**Wave 3** *(blocked on Wave 2 completion)*

  - [x] 04-03-PLAN.md — _worker スレッド境界リファクタ + 埋め込みスキップ統合 + 文言/設定追加（ocr_dialog/lang/settings）

**Wave 4** *(gap closure — 04-VERIFICATION.md gaps_found 対応)*

  - [ ] 04-04-PLAN.md — CR-02 _on_run でダイアログ UI 値（model/max_tokens/temperature）を反映し provider 再生成（SC-1 後方互換復元）+ CR-01 _start_ocr の build_provider を try/except ValueError で防護（ocr_dialog/ocr/lang）

### Phase 5: Claude Provider + セキュリティ基盤 + プロバイダ選択 UI

**Goal**: APIキー漏洩リスクなしに Claude で OCR が実行でき、ユーザーがプロバイダと実行コストを把握して操作できる
**Depends on**: Phase 4
**Requirements**: OCR-SEC-01, OCR-SEC-02, OCR-SEC-03, OCR-API-01, OCR-API-03, OCR-UI-01, OCR-UI-02, OCR-UI-03, OCR-UI-04, OCR-PERF-03, OCR-PERF-04
**Success Criteria** (what must be TRUE):

  1. `pagefolio_settings.json` に APIキー相当のフィールドが一切書き込まれない（`_save_settings()` ガード有効）
  2. `ANTHROPIC_API_KEY` 未設定の状態で Claude OCR を実行しようとすると、実行前に明示エラーが表示され処理が始まらない
  3. 環境変数が未設定のユーザーがセッション専用入力欄にキーを入力し、そのキーで OCR が実行できる（`os.environ` / `settings` には書き込まれない）
  4. SettingsDialog でプロバイダ（off / gemini / claude / lmstudio / tesseract）を選択したとき、そのプロバイダのモデル一覧が選択肢に反映される
  5. クラウドプロバイダで実行ボタンを押すと、送信先・ページ数・概算コスト・プライバシー注記を含む確認ダイアログが表示され、キャンセルで中止できる
  6. `ocr_provider: "off"` のとき OCR ボタンが無効化されており、外部通信・課金が発生しない
  7. Opus 系モデルで `temperature` を送らず `effort` を使用し、非対応パラメータによる 400 エラーが発生しない
  8. 429 / 5xx 応答時に指数バックオフ（最大 3 回）でリトライし、UI に「待機中」が表示される

**Plans**: 5 plans
**UI hint**: yes

**Wave 1**

  - [x] 05-01-PLAN.md — ClaudeProvider + OCRRetryableError 新設（messages API・effort/temperature 防御・429/5xx 変換・並列度 Claude=2）（ocr_providers.py）
  - [x] 05-02-PLAN.md — _save_settings 機密キーガード（成功基準1・最優先）+ DEFAULT 追加 + Phase 5 文言 ja/en（settings.py/lang.py）

**Wave 2** *(blocked on Wave 1 completion)*

  - [x] 05-03-PLAN.md — build_provider claude 分岐 + _resolve_api_key（env 優先・未設定明示エラー）+ run_parallel 指数バックオフ + _session_api_keys 属性（ocr.py/app.py）

**Wave 3** *(blocked on Wave 1/2 completion)*

  - [x] 05-04-PLAN.md — provider ドロップダウン・モデル更新・effort/temperature 切替 + off で OCR ボタン無効化（llm_config.py/ui_builder.py）
  - [x] 05-05-PLAN.md — コスト確認ゲート + マスク付きセッションキー入力欄（非永続化）+ 待機中表示 + provider 中立化（ocr_dialog.py）

### Phase 6: Gemini Provider + 逐次レンダリング最適化

**Goal**: Gemini で OCR が実行でき、低スペック PC でも全ページ OCR 時のメモリ使用量が許容範囲に収まる
**Depends on**: Phase 5
**Requirements**: OCR-API-02, OCR-PERF-02, OCR-PERF-05, OCR-QA-01
**Success Criteria** (what must be TRUE):

  1. `GEMINI_API_KEY` または `GOOGLE_API_KEY` を設定したユーザーが Gemini で OCR を実行でき、テキストが返される
  2. 100 ページの PDF で OCR 実行中に全ページの base64 画像が同時にメモリに乗らない（ページ単位でレンダリング→送信→破棄）
  3. `ocr_scale` のデフォルトが 1.5 になり、UI にコスト/精度のトレードオフ説明が表示される
  4. 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定がモックテストで検証されている（`tests/test_ocr.py` 通過）

**Plans**: 4 plans

**Wave 1** *(並列・ファイル非重複)*

  - [x] 06-01-PLAN.md — GeminiProvider 新設（inline_data・x-goog-api-key・thinkingBudget=0・dual env var）+ build_provider/_resolve_api_key/_cloud_providers gemini 配線 + Gemini モックテスト（ocr_providers/ocr/test_ocr*）
  - [x] 06-03-PLAN.md — ocr_scale 既定 1.5 + 設定欄トレードオフ常設ヒント + gemini UI 欄（llm_config）+ OCRDialog プロバイダ判定の gemini 対応 + 日英文言 + APP_VERSION/開発履歴/README 同期（settings/lang/llm_config/ocr_dialog/constants）

**Wave 2** *(blocked on Wave 1 — ocr.py / ocr_dialog.py 共有)*

  - [x] 06-02-PLAN.md — producer-consumer 逐次レンダリング（run_with_bounded_buffer・全ページ一括保持廃止・ワーカー内 fitz アクセスゼロ・統合プログレス）+ メモリ非蓄積リグレッションテスト（ocr/ocr_dialog/test_ocr）

**Wave 3** *(gap closure — 06-VERIFICATION.md gaps_found / 06-REVIEW.md CR-01・CR-02 対応・blocked on Wave 2)*

  - [x] 06-04-PLAN.md — CR-01 _start_worker_thread を concurrency 本のワーカー起動へ（LM Studio 後方互換復元・OCR-PERF-02）+ 終了シグナル concurrency 本 + done カウンタ Lock 化 + 全ワーカー終了後の単一終了処理 + CR-02 _finish_* 冪等ガード（結果二重挿入防止）+ 並列度/冪等性回帰テスト + WR-01/02/03 技術的負債解消（ocr_dialog/ocr/settings/llm_config/test_ocr）

### Phase 7: Tesseract + PluginManager 拡張 + QA

**Goal**: オフライン環境でも Tesseract が選択肢として使えて、サードパーティがカスタムプロバイダを登録でき、全プロバイダの文言・ドキュメントが整備されている
**Depends on**: Phase 6
**Requirements**: OCR-EXT-01, OCR-EXT-02, OCR-QA-02
**Success Criteria** (what must be TRUE):

  1. Tesseract がインストールされた環境でプロバイダを「tesseract」に選択し OCR を実行できる（精度劣後注記が UI に表示される）
  2. Tesseract が未インストールの環境では「tesseract」選択肢が無効化され、エラーなく他プロバイダへ誘導される
  3. サードパーティプラグインが `register_ocr_provider` フックで独自バックエンドを登録し、SettingsDialog のプロバイダ一覧に表示できる
  4. プロバイダ名・APIキー未設定・精度注記・コスト警告の文言が日英両対応し、README と開発履歴が v1.4.0 の変更を反映している

**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Undo/Redo 修正 | v1.3.0 | 3/3 | Complete | 2026-06-03 |
| 2. プレビュー最適化とリファクタリング | v1.3.0 | 3/3 | Complete | 2026-06-03 |
| 3. API 整理と回帰テスト | v1.3.0 | 2/2 | Complete | 2026-06-03 |
| 4. プロバイダ抽象化 | v1.4.0 | 3/3 | Complete | 2026-06-06 |
| 5. Claude Provider + セキュリティ基盤 + プロバイダ選択 UI | v1.4.0 | 5/5 | Complete    | 2026-06-07 |
| 6. Gemini Provider + 逐次レンダリング最適化 | v1.4.0 | 4/4 | Complete    | 2026-06-07 |
| 7. Tesseract + PluginManager 拡張 + QA | v1.4.0 | 0/? | Not started | - |
