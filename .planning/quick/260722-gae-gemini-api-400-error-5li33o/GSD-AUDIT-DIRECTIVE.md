---
quick_id: 260722-gae
slug: gemini-api-400-error-5li33o
date: 2026-07-22
type: directive
status: complete
priority: highest
completed: 2026-07-22
---

# 【最優先指示書】次回 GSD-Core 実行時: 260722-gae の GSD ワークフロー精査

> **この指示書は、次回 GSD-Core（/gsd-* コマンド）を実行するセッションが
> 他のどの作業よりも先に処理すること。** 処理完了後は本ファイルの
> frontmatter `status` を `pending` → `complete` へ更新し、
> `.planning/STATE.md` の Session Continuity（Resume file）を解除すること。

## 経緯（なぜこの指示書があるか）

2026-07-22 のセッション（リモート実行環境 / Claude Code on the Web・ブランチ
`claude/gemini-api-400-error-5li33o`・コミット `58c0de2`）で、Gemini 新世代モデル
（gemini-3.6-flash / gemini-3.5-flash-lite）の OCR 400 エラー修正（v1.8.1）を
**GSD ワークフローを経由せずに**直接実装・push した。当該環境には GSD スキル
（/gsd-quick・/gsd-debug 等）が存在せず、CLAUDE.md の「GSD Workflow Enforcement」
を満たせなかったためである。PLAN.md / SUMMARY.md は遡及作成した。

このため、**GSD の通常フロー（計画 → 実装 → 検証 → 記録）のうち
「計画時レビュー」と「独立検証」が未実施**のまま main へのマージ候補になっている。

## 精査対象

- ディレクトリ: `.planning/quick/260722-gae-gemini-api-400-error-5li33o/`
  （[PLAN.md](./PLAN.md)（遡及）・[SUMMARY.md](./SUMMARY.md)）
- ブランチ: `claude/gemini-api-400-error-5li33o`（コミット `58c0de2`・push 済み）
- 主変更: `pagefolio/ocr_providers/gemini.py`（`_build_generation_config`
  世代ゲート化・`_model_generation` / `_is_legacy_gemini` 新設）

## 精査項目（/gsd-debug または /gsd-quick 相当の検証フローで実施）

1. ~~**診断の妥当性検証（最重要）**~~ → **✅ 完了（2026-07-22・ユーザー実施）**
   - 手動ビルドによる実機 + 実際の Gemini API キーで、gemini-3.6-flash /
     gemini-3.5-flash-lite の OCR 実行を確認。**400 エラーは解消し問題なし**。
     診断（新世代でのサンプリングパラメータ / thinkingConfig 拒否）と
     世代ゲート方式の修正が実環境で有効と裏付けられた。
   - （任意の残タスク）Gemini API 公式ドキュメント上の該当仕様記述の照合は未実施。
     実機で解消が確認できているため優先度は低。
2. **設計判断のレビュー**
   - ユーザー原指示は「temperature の完全削除」。実装は gemini-2.x 以前の挙動維持を
     優先した「世代ゲート方式」（`_is_legacy_gemini`・D-16 同方針）。この判断の可否を
     ユーザーに確認し、完全削除へ倒す場合は `_build_generation_config` の 2 分岐を
     外す（既存回帰テストの期待値変更を伴う）。
   - 世代判定の正規表現 `gemini-(\d+)` が今後のモデル ID 命名
     （例: `gemini-exp-*`、日付サフィックス付き等）で誤判定しないか。
     判定不能 → 新世代扱い（パラメータ省略）のフォールバックが常に安全側かも再確認。
3. **残課題の処理判断（SUMMARY.md「注意点・潜在リスク」より）**
   - `RECOMMENDED_MODELS` への gemini-3.x 系正式 ID の追加
   - LLM 設定ダイアログの temperature 欄が新世代 Gemini で無視される旨の UI 注記
   - 新世代での thinking 有効時の応答時間・トークン消費の実測
4. **記録の整合性確認**
   - `.planning/STATE.md`（Quick Tasks Completed 表・Session Continuity）、
     `開発履歴.md`（v1.8.1）、`CLAUDE.md`（既知の制限）、README バッジ、
     `APP_VERSION = v1.8.1` の相互整合。
5. **リリース系の未実施作業**（精査パス後）
   - main へのマージ・注釈付きタグ・GitHub Release・PyInstaller リビルド
     （`dist/PageFolio` 更新。今回のサンプルプロンプト架空化は dist 直接編集のため
     リビルド時に上書きされない配置かも確認）。

## 進捗

- 2026-07-22: 項目 1（実機検証）をユーザーが完了 — gemini-3.6-flash /
  gemini-3.5-flash-lite で 400 解消・問題なし。残りは項目 2〜5。
- 2026-07-22: gemini-3.5-flash（従来から正常だったモデル）の退行なしも
  ユーザーが実機確認・問題なし。世代ゲートによるパラメータ省略
  （temperature / thinkingConfig あり→なし）が既存正常系を壊さないことを
  実環境で裏付け。対象 3 モデルすべて実機グリーン。
- 2026-07-22: /gsd-ship セッション（GSD-Core）で項目 2〜4 を完了。
  項目 2: 世代ゲート方式で確定（ユーザー承認）。項目 3: RECOMMENDED_MODELS へ
  gemini-3.x 追加のみ実施・UI 注記/thinking 実測は先送り（ユーザー承認）。
  項目 4: 記録整合を確認し開発履歴.md 索引の v1.8.0 行欠落（既存ギャップ）を追補。
  独立検証: ローカル Windows で pytest 1109 件グリーン・ruff クリーン。
  検証記録 [260722-gae-VERIFICATION.md](./260722-gae-VERIFICATION.md)・
  セキュリティ記録 [260722-gae-SECURITY.md](./260722-gae-SECURITY.md) を作成。
  結果は SUMMARY.md「GSD 精査結果」へ追記済み。項目 5（リリース系）は
  /gsd-ship の PR 作成で継続。

## 完了条件

- 上記 2〜4 を実施し（1 は完了済み）、結果（確認できた事実・修正が必要に
  なった点・受容したリスク）を本ディレクトリの SUMMARY.md へ追記、
  または新規検証記録として保存。
- 本ファイルの `status: complete` 化と STATE.md の Resume file 解除。
