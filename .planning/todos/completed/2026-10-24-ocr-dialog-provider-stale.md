---
title: LLM設定でプロバイダー/モデルを変えてもOCRダイアログ等の表示が即時反映されない
created: 2026-10-24
source: Phase 06 / 06-04-02 接続実証（ocr-single 1回目）での利用者報告
severity: medium
status: completed
resolved: 2026-10-24
resolved_by: 7fb41a28ada8a2f016dd69942772cdcab9cc727f
---

## 事象（利用者報告・既存バグ）

LLM設定画面からプロバイダー・モデルを変更しても、親画面に即時反映されない（利用者談: 前からあったバグ）。

## 06-04 での観測（2026-10-24 19:32〜19:40、配布EXE v1.10.0 隔離コピー）

- 利用者が LLM設定で Ollama → Gemini に変更。OCRダイアログの表示は「ollama」のままだった。
- 実際の読み取りは Gemini（`gemini-3.1-flash-lite`）へ送られたとみられる: loopback の合成OCRサーバー（ollama_url）は要求を1件も受信せず、結果欄には合成画像に描かれた文字「PageFolio UAT / OCR TEST 0123456789」がそのまま表示された（合成サーバーの応答文「PageFolio UAT 合成OCR結果」ではない）。
- 隔離コピーの設定は終了時に `ocr_provider: gemini` で保存された（overlay 原本は `ollama`）。
- つまり「表示されているプロバイダー」と「実際に送信されるプロバイダー」が食い違う。利用者は意図しない外部APIへ画像を送る可能性がある（今回は合成画像のみ）。

## 対応

v1.10.0 のリリース可否への影響（外部送信先の表示不一致）を Phase 06 の最終ゲートで判断する。修正は別タスク（/gsd-debug または /gsd-quick）。

## 解決（2026-10-24）

コミット 7fb41a2（fix(ocr): LLM設定でプロバイダを変えてもOCRダイアログの表示が古いまま残る問題を修正）で解決。調査記録は `.planning/debug/resolved/ocr-ollama-uses-lmstudio-url.md`。

- 原因は独立した2つ。B1: `_on_run`/`_on_summary` が確定した設定スナップショット（`_active_ocr_settings`）が適用後も残り、表示判定が app.settings より優先していた。B2: `_apply_llm_settings` が表示更新をプロバイダ再生成より前に行い、旧プロバイダの isinstance 判定に引きずられていた。
- 修正: 適用時にスナップショットを破棄し、表示更新を再生成の後へ移した。回帰テスト `tests/test_ocr_dialog_provider_refresh.py`（6件）。
- 範囲: 修正したのは OCR ダイアログの表示（プロバイダ名・モデル名）。本 todo の題にある「親画面」側の他の表示（メイン画面の OCR ボタン状態など）は今回の調査対象外で変更していない。
- 試行1で表示が ollama のまま実送信が Gemini になった事象は、B1/B2 で説明できる（試行2の「ollama 設定でも LM Studio URL へ送信」は別根因 A で、コミット 52258de で修正）。配布EXEでの実機再確認は未実施。
