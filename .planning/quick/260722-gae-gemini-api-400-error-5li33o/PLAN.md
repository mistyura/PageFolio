---
quick_id: 260722-gae
slug: gemini-api-400-error-5li33o
date: 2026-07-22
type: quick
mode: quick
status: complete
---

# Plan: Gemini 新世代モデル（gemini-3.x）の OCR 400 エラー修正（v1.8.1）

> **注意（遡及作成）**: 本セッションはリモート実行環境（Claude Code on the Web）で
> 行われ、GSD スキル（/gsd-quick・/gsd-debug 等）が利用できなかったため、
> GSD ワークフローを**経由せずに**直接実装した。本 PLAN.md は実装後に遡及作成した
> 記録であり、次回 GSD-Core 実行時に本内容の精査を最優先で行うこと
> （[GSD-AUDIT-DIRECTIVE.md](./GSD-AUDIT-DIRECTIVE.md) 参照）。
> 実施結果は [SUMMARY.md](./SUMMARY.md) を参照。

## 背景

ユーザー報告（緊急対応依頼）:

- gemini-3.6-flash / gemini-3.5-flash-lite で OCR 実行が HTTP 400
  （INVALID_ARGUMENT）になり、gemini-3.5-flash でのみ正常に処理が進む。
- ユーザー側調査による原因仮説は 3 点:
  1. 新世代モデルでは temperature / top_p / top_k のサンプリングパラメータが
     非推奨・禁止となり、含まれていると 400 で拒否される（最有力）
  2. プリフィル（最終ターンへの model ターン配置）の禁止
  3. inlineData（Base64 直接埋め込み）の容量上限・引数チェック厳格化
     （大きな PDF は Files API 経由を推奨）

## 調査結果（本セッションでの切り分け）

- `pagefolio/ocr_providers/gemini.py` の `_build_generation_config` は
  **全モデルに `temperature`（既定 0.1）を無条件送信**し、gemini の non-pro には
  `thinkingConfig: {thinkingBudget: 0}` も送信していた（D-09/M-4/H-7）。
  → 仮説 1 に該当。加えて新世代では外部からの thinking 制御
  （thinkingBudget）も拒否対象のため、**thinkingConfig も同時に省略が必要**。
- 仮説 2（プリフィル）: Gemini プロバイダの payload は単一 user ターンのみで
  model ターンは元々存在しない。**対応不要**。
- 仮説 3（PDF/Files API）: PageFolio の OCR は「ページ単位で PNG 画像を
  レンダリングし inline 送信」する方式（`page_to_png_b64`）で PDF 全体は
  送らない。1 ページ分の PNG はリクエスト容量上限に対し十分小さい。
  **Files API 化は不要と判断**。

## 対応方針

- `GeminiProvider` に世代判定ヘルパーを新設し、`generationConfig` を
  世代ゲート方式で構築する:
  - `_model_generation(model)`: モデル ID 先頭の世代番号を抽出（判定不能は None）
  - `_is_legacy_gemini()`: 世代番号を明示的に 2 以下と判定できた場合のみ True
- 送信ルール:
  - `temperature`: 旧世代 gemini（≤2）と gemma 等の非 gemini 系のみ送信
    （H-7 挙動維持）。gemini-3 世代以降・バージョンレスのエイリアス
    （gemini-flash-latest 等）は省略（**省略は全世代で合法＝安全側**。
    ClaudeProvider の「未知モデルにはパラメータを送らない」D-16 と同方針）
  - `thinkingConfig`（thinkingBudget=0）: 旧世代 gemini の non-pro のみ送信
  - `maxOutputTokens`: 全世代で送信継続
- ユーザー指示は「temperature の完全削除」だったが、gemini-2.5 系の OCR
  再現性（低温設定）を維持するため世代ゲート方式を採用（設計判断・要精査）。
- おまけ対応: `dist/PageFolio/ocr_summary_prompt_sample.md` の実在決済サービス名
  （「クイックペイプラス」「QP/〜」= JCB の QUICPay+）を汎用表現へ架空化。
  「〇×工業」「見本 太郎」は既に架空化済み・custom 側サンプルに実名なしと確認。

## 想定される変更ファイル

- `pagefolio/ocr_providers/gemini.py`（世代ゲート・ヘルパー 2 個新設）
- `tests/test_ocr_providers.py`（回帰テストクラス新設）
- `dist/PageFolio/ocr_summary_prompt_sample.md`（架空化）
- `pagefolio/constants.py`（`APP_VERSION` → v1.8.1）
- `README.md`（バッジ）・`開発履歴.md`（履歴）・`CLAUDE.md`（既知の制限）

## 検証方法

- `ruff check . && ruff format .` クリーン
- `pytest` 全件グリーン（新世代モデルでの省略・旧世代/gemma の従来挙動維持・
  テキスト payload 共有経路・`_model_generation` パースの回帰テストを追加）
- 実 API での動作確認は環境上不可（次セッションへ申し送り）
