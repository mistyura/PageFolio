# Phase 4 — API Coverage Matrix

**Generated:** 2026-07-15（`/gsd-plan-phase --reviews` の API Coverage Decision Checkpoint 由来）
**Detector result:** `detected: true`

## 検出のコンテキスト（重要）

API Coverage 検出器は、04-02/04-03-PLAN.md の `<threat_model>` 内トラストバウンダリ記述
「BatchOCRDialog → クラウド OCR API（ページ画像 b64 PNG が外部 API へ https 送信される境界）」
の語句「API」に反応して発火した。

**本フェーズは新規の外部 API / SDK / サービスを統合しない。** バッチ OCR は、既存の OCR
プロバイダ抽象層（`pagefolio/ocr_providers/`・`build_provider`・`OCRRunEngine`）を**ファイル
ごとに再利用**するのみである。プロバイダ（Claude / Gemini / RunPod / LM Studio / Ollama /
Tesseract）と各エンドポイントは v1.4.0（Phase 4/5/6）で統合済み・v1.8.0 Phase 1/3 で
パッケージ化/エンジン抽出済みであり、本フェーズはその「呼ぶ側」に過ぎない（RESEARCH.md
State of the Art・`ocr_engine.py` 再利用方針）。したがって列挙すべき「新規 API 能力面」は
存在せず、既存統合面の**全面再利用＝全面カバー**が本マトリクスの実態である。

## Capability Surface（バッチが消費する既存プロバイダ能力）

| Capability | 消費経路（バッチ側） | Disposition | 備考 |
|------------|---------------------|-------------|------|
| `provider.ocr_image_ex`（ページ画像 OCR・途切れ検出） | `OCRRunEngine`（ファイルごと新規生成）経由・04-02 | INTEGRATE（再利用） | 単一ファイル OCR と同一。新規実装なし |
| `provider.complete_text_ex`（text-only 補完＝統合サマリ） | `_batch_summary_worker`・04-03 | INTEGRATE（再利用） | ファイル横断連結テキストを渡すのみ（D-15） |
| `provider.supports_text_prompt`（サマリ可否フラグ） | `_on_batch_summary` のゲート・04-03 | INTEGRATE（再利用） | 既存 `_on_summary` と同型 |
| API キー解決（`_resolve_api_key` / `registry.primary_env_var`） | provider 構築時・04-02 | INTEGRATE（再利用） | 値は Engine へ渡さず構築済み provider のみ（T-04-02） |
| コスト確認（`_confirm_cost` / `_confirm_summary_cost`） | `_confirm_batch_cost` / `_on_batch_summary`・04-02/04-03 | INTEGRATE（移植・同一挙動） | 合計ページ/文字数を渡す（D-03/D-14）。同意ゲート維持 |
| `provider.list_models`（モデル一覧取得） | — | OPT-OUT | モデル/プロバイダ選択は既存 `LLMConfigDialog` に一元化済み。バッチは D-04 の独立設計上、アプリ設定のプロバイダをそのまま使い、モデル選択 UI を再実装しない（1行理由: バッチはプロバイダ設定の消費者であり選択 UI の提供者ではない） |

## 判定

- 新規外部 API 統合: **なし**（既存プロバイダ層の再利用のみ）
- 消費する既存能力面: すべて INTEGRATE（再利用/移植）
- OPT-OUT: `list_models`（モデル選択 UI は `LLMConfigDialog` に一元化済み・D-04 独立設計のためバッチでは非提供）
- 新規パッケージ導入: なし（RESEARCH.md Package Legitimacy Audit: 該当なし）

> 本マトリクスは検出器発火（threat_model の「API」語）への手続き的応答であり、実態は
> 「既存統合面の全面再利用」である。新規 API サーフェスのチェリーピッキングは発生していない。
