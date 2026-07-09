---
quick_id: 260709-pmf
slug: prompt-markdown-formatting-1loozg
date: 2026-07-09
type: quick
mode: quick
status: complete
---

# Plan: プロンプト外部 md ファイル読込・Markdown 描画個別指定・モデル取得タイムアウト見直し（v1.7.4）

> 実装は同日完了 — 実施結果は [SUMMARY.md](./SUMMARY.md) を参照。

## 背景

ユーザー要望（3 点）:

1. 「カスタムプロンプト、サマリプロンプトが巨大化する場合、個別に Markdown 形式に
   指定できるようにする」— 経理書類 OCR のような業務用途ではプロンプトが数十行規模に
   巨大化し（実例プロンプトの提供あり）、出力形式（Markdown テーブル）もプロンプト側で
   指示するようになる。ところが整形描画の判定は `preset == "markdown"`（OCR プリセットの
   ラジオボタン）に固定されており、カスタムプロンプト使用時はプリセット選択が実プロンプト
   へ反映されない（`resolve_ocr_prompt` でカスタムが最優先）にもかかわらず、描画形式だけが
   プリセットに引きずられる不整合があった。特にサマリは専用プロンプト
   （`ocr_summary_prompt`）で Markdown テーブルを生成しても、OCR プリセットが text の
   ままだと素朴描画になっていた。
2. 「クラウド LLM を使用し、モデルを取得する際に（特に RunPod の初回起動）10 秒では
   少ないケースがあるので、見直しを図る」— 全プロバイダの `list_models` が
   `timeout = 10` をハードコードしており、RunPod Serverless のコールドスタート
   （ワーカー起動 + モデルロードで数十秒〜数分）では `timed out after 10s` で失敗する。
   さらにモデル取得は Tk メインスレッドで同期実行されており、タイムアウトを延長すると
   その間 UI がフリーズする問題が連動する。
3. 「カスタムプロンプト、サマリプロンプトを exe ファイルと同じ階層にそれぞれ格納 →
   プログラム内で md ファイルを読込、参照の方式を考えている」— 巨大プロンプトを
   LLM 設定ダイアログの小さな入力欄（3 行 Text）で編集・管理するのは現実的でなく、
   外部エディタで管理できるファイル方式が必要。

## 対応方針

### 1. Markdown 描画の個別指定（V174）

- 純関数 `resolve_render_markdown(preset, custom_prompt, render_markdown)` を
  `ocr.py` へ追加（Tk 非依存）。カスタムプロンプト非空なら個別フラグ、空なら従来どおり
  `preset == "markdown"` を返す（後方互換維持）。
- LLM 設定ダイアログのカスタム/サマリプロンプト欄直下にチェックボックスを新設し、
  設定キー `ocr_custom_prompt_markdown` / `ocr_summary_markdown`（既定 False）として
  永続化。`_apply` は Tk 無しスタブ経路の安全のため getattr フォールバック
  （`_tesseract_langs` と同型パターン）で格納する。
- `OCRDialog._render_results_ordered`（OCR 本文）と `_on_summary_done`（サマリ）の
  整形描画判定を `resolve_render_markdown` へ集約。コピー/保存の raw 維持は不変。

### 2. モデル一覧取得タイムアウトの見直し（V174）

- `OCRProvider` にクラス属性 `model_list_timeout`（既定 10 秒）を新設し、全プロバイダの
  `list_models`（Claude は `_fetch_models_page`）のハードコード 10 秒を置換。
  ローカル（LM Studio / Ollama）は 10 秒のまま、Claude / Gemini は 30 秒、
  RunPod はコールドスタートを見込み 90 秒へ引き上げる。
- タイムアウト延長に伴い、クラウド 3 プロバイダのモデル取得を共有ヘルパー
  `_fetch_models_async`（ワーカースレッド + `after(0)` でメインスレッドへ結果投函・
  `_model_fetch_running` 二重実行ガード・ダイアログ破棄後は結果破棄）による
  バックグラウンド実行へ変更し UI フリーズを解消。エラー時の静的推奨リスト
  フォールバック（D-08）等の既存挙動はコールバック側で維持する。
- RunPod の取得中ステータス文言にコールドスタートの注記を追加（ja/en）。

### 3. プロンプトの外部 md ファイル読込（V174-2）

- 実行ファイル（開発時はプロジェクトルート）と同じ階層の `ocr_custom_prompt.md` /
  `ocr_summary_prompt.md` を読み込み、存在して非空なら LLM 設定の入力欄より優先する
  読込層を `settings.py` に新設（`load_prompt_file` / `load_custom_prompt` /
  `load_summary_prompt`）。ファイル名は `constants.py` の定数
  （`CUSTOM_PROMPT_FILE` / `SUMMARY_PROMPT_FILE`）。
- 配置基準は `_get_settings_path` から抽出する `_get_base_dir()` へ一元化
  （`pagefolio_settings.json` と同じ場所）。
- 読込は OCR 実行（`_on_run`）・サマリ実行（`_on_summary`）のたびに毎回行い、
  外部エディタでの編集を再起動なしで次回実行へ反映する。エンコーディングは
  UTF-8（Windows エディタの BOM 付き `utf-8-sig` も許容）。無効時（不在/空/読込失敗）は
  設定欄へフォールバック（完全な後方互換）。
- LLM 設定ダイアログにファイル検出時のみ「入力欄よりファイル内容を優先」の注記を
  WARNING 色で表示（`_add_prompt_file_notice`）。ファイル使用時も 1. の Markdown
  描画フラグは「カスタム使用中」として適用される。

## 想定される変更ファイル

- `pagefolio/ocr.py`（`resolve_render_markdown` 追加・`_start_ocr` のプロンプト解決変更）
- `pagefolio/ocr_dialog.py`（描画判定の集約・md ファイル毎回再読込）
- `pagefolio/ocr_providers.py`（`model_list_timeout` クラス属性）
- `pagefolio/dialogs/llm_config.py`（チェックボックス・ファイル注記・非同期取得）
- `pagefolio/settings.py`（読込層・`_get_base_dir`・既定値追加）
- `pagefolio/constants.py`（ファイル名定数・`APP_VERSION`）
- `pagefolio/lang.py`（新キー ja/en・RunPod 文言更新）
- `tests/`（test_utils / test_provider_ui / test_ocr / test_ocr_providers）
- `README.md`（バージョンバッジ）・`開発履歴.md`（変更履歴追記）

## 検証方法

- `ruff check . && ruff format .` / `pytest` 全件グリーン。
- 回帰テスト追加:
  - `resolve_render_markdown` の優先順位・後方互換（プリセット準拠/フラグ優先）
  - `_apply` の新フラグ格納・スタブ経路 getattr フォールバック
  - `_on_summary_done` のフラグ別描画（整形/素朴）
  - `model_list_timeout` のプロバイダ別値と urlopen への伝播
  - 外部プロンプトファイルの優先順位/フォールバック/BOM/空ファイル
    （`_get_base_dir` を tmp_path へ monkeypatch し実ファイル非依存化）
- 既存テストへの影響確認: `_make_apply_key_stub` へ新変数追加・
  `TestOnSummaryDone._make_fake` へ `app.settings` 追加（md ファイル不在時は
  従来挙動へフォールバックするため他は無変更で通る設計とする）。
