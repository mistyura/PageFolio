---
phase: 03
slug: ocr-a
status: draft
created: 2026-06-19
---

# Phase 3 — 実 API 検証チェックリスト（V16-QUAL-03 / H5・D-08）

> max_tokens クランプと 429/レート制限リトライの実 API 動作をユーザーが任意実行・記録するための手順書。
> 堅牢化ロジック（`clamp_retry_after` 60s クランプ・指数バックオフ・サーキットブレーカー・max_tokens クランプ）は
> `tests/test_ocr.py` で自動テスト済み（D-09: 自動テストは重複追加しない）。本書は実 API での動作確認と実値記録に徹する。

---

## 前提・実行可否

| 項目 | 内容 |
|------|------|
| **必要キー** | `ANTHROPIC_API_KEY`（Claude 検証時）/ `GEMINI_API_KEY` または `GOOGLE_API_KEY`（Gemini 検証時） |
| **キー未設定時** | 本検証はスキップ可。**フェーズ完了をブロックしない**（D-07）。自動テストが堅牢化ロジックを担保している |
| **自動テスト相互参照** | `tests/test_ocr.py::TestBuildProviderMaxTokensClamp`（max_tokens クランプ）/ `TestM5ClampRetryAfter`（Retry-After クランプ）/ サーキットブレーカー・バックオフ群 |
| **課金注意** | 実 API 送信は従量課金が発生する。最小ページ数で実施すること |

---

## 検証 1: max_tokens クランプ・応答途切れ検出（V16-QUAL-04 連携）

**手順:**

1. LLM 設定でプロバイダを Claude または Gemini に設定し、`max_tokens` を意図的に小さく（例 16〜64）設定する。
2. テキスト量の多いページ 1 枚を選択し OCR を実行する。
3. 応答が途中で途切れること、結果ビューアの当該ページに `[p.N: 応答が max_tokens で途切れました。…]`（`ocr_err_truncated`）が**部分テキストの後に**併記されることを確認する。

| 確認項目 | 期待結果 | 結果記入欄 |
|----------|----------|------------|
| 部分テキストが破棄されず表示される | 途中までのテキストが results に残る（D-05） | ☐ pass / ☐ fail： |
| 途切れ専用文言が併記される | `ocr_err_truncated` が当該ページに 1 行表示 | ☐ pass / ☐ fail： |
| 次アクションが理解できる | 「max_tokens を増やして再実行」が読める | ☐ pass / ☐ fail： |

---

## 検証 2: 429 / レート制限リトライ・待機秒数表示

**手順:**

1. 並列度を上げ（または Free Tier 等で）短時間に多数ページの OCR を実行し 429 を誘発する。
2. 進捗ラベルに「約 N 秒待機」（`ocr_waiting_retry`・`{sec}` 反映）が表示され、リトライ番号（`{n}/{max}`）が進むことを確認する。
3. `Retry-After` が極端に大きい場合でも待機が 60 秒上限にクランプされること（表示秒数が最大 60）を確認する。

| 確認項目 | 期待結果 | 結果記入欄 |
|----------|----------|------------|
| 待機表示に実待機秒数が併記される | 「約 N 秒」が表示（N = round(clamp 後 delay)） | ☐ pass / ☐ fail： |
| Retry-After クランプ | 過大値でも表示・実待機が 60 秒以内 | ☐ pass / ☐ fail： |
| リトライ後に成功 or 上限到達で適切に処理 | リトライ消化後に成功/エラー表示 | ☐ pass / ☐ fail： |
| 連続失敗時サーキットブレーカー | 連続 3 失敗で中断し「続きから再実行」可能 | ☐ pass / ☐ fail： |

---

## 検証 3: A2 実値記録（stop_reason / finishReason）

> 03-02 で `stop_reason == "max_tokens"`（Claude）/ `finishReason == "MAX_TOKENS"`（Gemini）を途切れ判定に採用した（A2・`.get()` 安全アクセス）。実 API のレスポンスで実値を記録し、判定値が正しいことを確認する。

| プロバイダ | 期待値 | 実 API 実測値（記入欄） |
|-----------|--------|------------------------|
| Claude `stop_reason`（途切れ時） | `max_tokens` | |
| Claude `stop_reason`（正常時） | `end_turn` 等 | |
| Gemini `finishReason`（途切れ時） | `MAX_TOKENS` | |
| Gemini `finishReason`（正常時） | `STOP` 等 | |

> 実測値が期待値と異なる場合は `pagefolio/ocr_providers.py` の `ocr_image_ex`（Claude `stop_reason` / Gemini `_is_truncated`）の比較文字列を実値へ調整する。

---

## 総合結果

| 項目 | 記入 |
|------|------|
| 検証実施日 | |
| 実施者 | |
| 使用プロバイダ/モデル | |
| 総合判定 | ☐ 全 pass / ☐ 要修正（詳細を上記欄へ） |
