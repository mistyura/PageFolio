---
quick_id: 260722-gae
slug: gemini-api-400-error-5li33o
date: 2026-07-22
threats_open: 0
status: secured
---

# セキュリティレビュー: 260722-gae（v1.8.1 Gemini 400 修正）

`main...claude/gemini-api-400-error-5li33o` の全差分（11 ファイル・+405/-12）を対象に
ship 前セキュリティレビューを実施した。**未解決の脅威は 0 件**。

## 差分ごとの所見

| 対象 | 変更内容 | セキュリティ所見 |
|------|----------|------------------|
| `pagefolio/ocr_providers/gemini.py` | generationConfig の世代ゲート化（`_model_generation` / `_is_legacy_gemini` 新設・`RECOMMENDED_MODELS` 追補） | 送信パラメータの**削減**のみで新規入力面なし。正規表現 `gemini-(\d+)` は単純パターンで ReDoS の懸念なし（入力はローカル設定のモデル ID）。API キーの取り扱い・エンドポイント・TLS（https）に変更なし |
| `dist/PageFolio/ocr_summary_prompt_sample.md` | 実在決済サービス名（QUICPay+）を汎用表現へ架空化 | 実在事業者名の削除であり**改善方向**。新たな実在名・個人情報の混入なし |
| `pagefolio/constants.py` | `APP_VERSION` v1.8.0 → v1.8.1 | リスクなし |
| `tests/test_ocr_providers.py` | 回帰テスト追加のみ | リスクなし（ダミーキー `"k"` のみ使用・実キーのハードコードなし） |
| `CLAUDE.md` / `README.md` / `開発履歴.md` / `.planning/*` | ドキュメント | 機密情報（API キー・トークン・内部 URL）の混入なしを確認 |

## 確認済みの不変条件

- API キーは環境変数またはセッションメモリのみ（`_SENSITIVE_KEYS` ガード）— 本差分で変更なし
- クラウド送信はページ単位 PNG の base64 inline のみ（PDF 全体は送らない）— 本差分で変更なし
- 裸の `except:` 句の追加なし

## 結論

**threats_open: 0** — 本差分は攻撃面を拡大せず、実在名称の架空化により
ドキュメント面ではむしろリスクを低減している。ship 可。
