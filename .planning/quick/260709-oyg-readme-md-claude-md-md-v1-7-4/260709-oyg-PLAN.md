---
quick_id: 260709-oyg
slug: readme-md-claude-md-md-v1-7-4
date: 2026-07-09
type: quick
mode: quick
status: planned
---

# Plan: README.md・CLAUDE.md・開発履歴.md を v1.7.4 の実コード状態へ同期

## 背景

直前セッションでブランチ `claude/prompt-markdown-formatting-1loozg` を main へマージし
v1.7.4 をリリース済み（コミット `5e013a4` → `515e434` → `3e1cdc7` → `8ef30d5` →
`288002e`）。この間に以下が入った:

1. OCR カスタム/サマリプロンプトの外部 md ファイル読込・入力欄との双方向連動
   （`settings.py`: `load_prompt_file` / `save_prompt_file` / `prompt_file_exists` /
   `load_custom_prompt` / `load_summary_prompt` / `_get_base_dir`、`constants.py`:
   `CUSTOM_PROMPT_FILE` / `SUMMARY_PROMPT_FILE`、`llm_config.py`: `_add_prompt_file_notice`）
2. Markdown 整形表示指定を OCR ダイアログのプリセットへ一本化（LLM 設定の重複
   チェックボックス機構・`resolve_render_markdown` は撤去済み・注記は `_update_preset_note`）
3. クラウド LLM のモデル一覧取得を非同期化（`llm_config.py`: `_fetch_models_async`）+
   プロバイダ別タイムアウト（`ocr_providers.py`: `model_list_timeout` = ローカル 10 /
   Claude・Gemini 30 / RunPod 90 秒）
4. OCR ダイアログ右ペイン（操作ボタン群）を Canvas+Scrollbar の縦スクロール対応（`ocr_dialog.py`）

**確認済みの状態**:
- `APP_VERSION = v1.7.4`（`constants.py`）
- README.md のバージョンバッジは既に `v1.7.4`（同期済み）
- 開発履歴.md は v1.7.4 の冒頭注記・バージョン索引行・本文セクションすべて同期済み
  → **重複追記しない**

**残差分**（今回の同期対象）:
- CLAUDE.md のモジュール構成・OCR モジュール群表・既知の制限が上記 1〜4 を未反映
- README.md の OCR プロバイダ列挙が古い（Ollama / RunPod が欠落。実コードの
  `LLMConfigDialog` は 6 プロバイダ対応）

## 制約

- **ドキュメント同期のみ**。コード変更なし。編集対象は README.md / CLAUDE.md / 開発履歴.md の 3 ファイルのみ。
- コード変更を伴わないため `ruff` / `pytest` は不要（`docs/*.md` は編集対象外）。
- 記述はすべて日本語。
- 開発履歴.md は既に v1.7.4 同期済み → **検証のみ・重複エントリ追記禁止**。

---

## Task 1: CLAUDE.md を v1.7.4 の実コード状態へ同期

**Files**: `CLAUDE.md`

**変更内容**（それぞれ既存文字列をアンカーに Edit で最小差分置換する）:

1. **ファイル構成ツリーのコメント 3 行を更新**
   - `constants.py` の行コメント `# バージョン・ファイル名・拡張子定数（APP_VERSION）+ themes/lang 再エクスポート`
     → 末尾に「OCR プロンプト外部ファイル名」を含める（例: `# バージョン・ファイル名・拡張子・OCR プロンプト外部ファイル名定数（APP_VERSION）+ themes/lang 再エクスポート`）。
   - `settings.py` の行コメント `# 設定ユーティリティ関数`
     → `# 設定ユーティリティ関数（外部プロンプトファイル読込含む）`。
   - `dialogs/` 配下 `llm_config.py` の行コメント `# LLMConfigDialog（OCR プロバイダ / モデル設定）`
     → `# LLMConfigDialog（OCR プロバイダ / モデル設定・非同期モデル取得・外部プロンプト連動注記）`。

2. **`### pagefolio/constants.py` 節に外部プロンプトファイル名定数を追記**
   - 既存の 2 文に続けて 1 文追加: OCR プロンプトの外部ファイル名 `CUSTOM_PROMPT_FILE`（`ocr_custom_prompt.md`）/ `SUMMARY_PROMPT_FILE`（`ocr_summary_prompt.md`）も定義する旨。

3. **`### pagefolio/settings.py` 節に外部プロンプト読込層を追記**
   - 既存の 2 文（設定読み書き・`_SENSITIVE_KEYS` ガード）に続けて 1 文追加: OCR のカスタム/サマリプロンプトの外部 md ファイル読込・書き戻し（`load_prompt_file` / `save_prompt_file` / `prompt_file_exists` / `load_custom_prompt` / `load_summary_prompt`）と配置基準ディレクトリの一元化（`_get_base_dir`・frozen 時は exe ディレクトリ / 開発時はプロジェクトルート）を提供する旨。

4. **OCR モジュール群の表 2 行を更新**
   - `ocr_providers.py` 行の責務説明の末尾に追記: `list_models` のモデル一覧取得タイムアウトはクラス属性 `model_list_timeout`（基底 10 / Claude・Gemini 30 / RunPod 90 秒＝Serverless コールドスタート対応）。
   - `ocr_dialog.py` 行の責務説明の末尾に追記: OCR プリセット横の注記（`_update_preset_note`: カスタムプロンプト使用中はプリセットが表示形式にのみ適用される旨）・右ペイン（「▶ 実行」「📋 結果」セクション）は Canvas+Scrollbar の縦スクロール対応で「✕ 閉じる」はスクロール領域外に常時可視。

5. **`pagefolio/dialogs/` 節の `llm_config.py` 説明を更新**
   - 分割一覧の `llm_config.py`（`LLMConfigDialog`）に、クラウドモデル取得の非同期化（`_fetch_models_async`）・外部プロンプトファイル連動注記（`_add_prompt_file_notice`）を担う旨を短く補足。

6. **「既知の制限・注意事項」セクションに OCR 関連 2 項目を追記**（OCR 既存項目群の近くに追加）
   - **外部プロンプトファイル連動**: OCR のカスタム/サマリプロンプトは、実行ファイル（開発時はプロジェクトルート）と同じ階層の `ocr_custom_prompt.md` / `ocr_summary_prompt.md`（`constants.py` の `CUSTOM_PROMPT_FILE` / `SUMMARY_PROMPT_FILE`）と LLM 設定の入力欄を双方向連動できる。ファイルが存在すればダイアログを開いたとき入力欄へ反映し、適用時に入力欄の内容をファイルへ書き戻す。OCR/サマリ実行時は毎回再読込するため外部エディタでの編集が再起動なしで反映される。ファイルが無ければ従来どおり設定欄のみで完結（`settings.py`）。
   - **モデル一覧取得の非同期化・タイムアウト**: クラウド LLM（Claude / Gemini / RunPod）のモデル一覧取得は LLM 設定ダイアログでバックグラウンドスレッド実行され UI をフリーズさせない（`llm_config.py` の `_fetch_models_async`）。タイムアウトはプロバイダ別クラス属性 `model_list_timeout`（ローカル 10 秒 / Claude・Gemini 30 秒 / RunPod 90 秒）。

**注意**:
- Markdown 整形表示はプリセット（`preset == "markdown"`）へ一本化済み。CLAUDE.md の `ocr_dialog.py` 行の既存記述 `preset=="markdown"` 整形描画は正しいので**変更しない**。撤去済みの `resolve_render_markdown` やチェックボックスへ言及する記述は CLAUDE.md に存在しない（新たに書かない）。
- 今回の対象外の記述（例: RunPod API キーの入力経路など v1.7.1 由来の記述）は触らない。スコープは v1.7.4 の 1〜4 に限定する。

**検証**:
- `grep -nE 'load_prompt_file|model_list_timeout|_fetch_models_async|CUSTOM_PROMPT_FILE|_update_preset_note|_add_prompt_file_notice' CLAUDE.md` が該当行を返す（各シンボルが本文に出現）。
- CLAUDE.md 内で撤去済みシンボル `resolve_render_markdown` が新たに追加されていない（`grep -c 'resolve_render_markdown' CLAUDE.md` が 0）。

**完了条件**:
- 上記 1〜6 の追記が反映され、settings.py / constants.py / ocr_providers.py / ocr_dialog.py / llm_config.py の責務説明が v1.7.4 の実コード（外部プロンプト読込・非同期モデル取得・プロバイダ別タイムアウト・右ペインスクロール・プリセット注記）と一致する。

---

## Task 2: README.md の OCR プロバイダ列挙同期 + 外部プロンプトファイルの言及、開発履歴.md の同期検証

**Files**: `README.md`, `開発履歴.md`

**変更内容**:

1. **README.md — OCR プロバイダ列挙を実コードへ同期**（実コードの `LLMConfigDialog` は
   LM Studio / Ollama / Claude / Gemini / RunPod / Tesseract の 6 プロバイダ対応。現状の
   README は 4 つしか挙げていない）
   - 「使い方の例 > OCR によるテキスト抽出」の本文中「プロバイダ（LM Studio / Claude / Gemini / Tesseract のいずれか）」を、6 プロバイダ（LM Studio / Ollama / Claude / Gemini / RunPod / Tesseract）を含む表記へ更新。
   - 「機能一覧」表の `🔍 OCR テキスト抽出` 行「LM Studio / Claude / Gemini / Tesseract の複数プロバイダに対応」を同様に 6 プロバイダ表記へ更新。

2. **README.md — 外部プロンプトファイル方式を 1 文追記**（v1.7.4 の end-user 向け機能）
   - 「使い方の例 > OCR によるテキスト抽出」の末尾に 1 文追加: カスタムプロンプト・サマリプロンプトが巨大になる場合、実行ファイルと同じ階層に `ocr_custom_prompt.md` / `ocr_summary_prompt.md` を置くと外部エディタで管理でき、LLM 設定の入力欄と双方向連動する旨。

3. **開発履歴.md — v1.7.4 同期の検証のみ（原則変更なし）**
   - 冒頭「最終更新」注記・「バージョン索引」の v1.7.4 行・本文 `## v1.7.4 …` セクションがすべて存在し `APP_VERSION = v1.7.4` と整合していることを確認する。
   - **既に完全同期済みのため新規エントリは追記しない**。齟齬（版番・日付・リンクアンカーの不一致など）が実際に見つかった場合のみ、その 1 点を最小修正する。見つからなければ変更なしで良い。

**検証**:
- `grep -c 'Ollama' README.md` と `grep -c 'RunPod' README.md` がともに 1 以上（OCR 節・機能一覧の両方で 6 プロバイダ表記になったことを確認）。
- `grep -c 'ocr_custom_prompt.md' README.md` が 1 以上（外部プロンプトファイルの言及が入った）。
- `grep -c 'v1.7.4' 開発履歴.md` が 3 以上（冒頭注記・索引・本文見出しが揃っている）で、v1.7.4 の重複エントリが増えていない。

**完了条件**:
- README.md の OCR プロバイダ表記が実コード（6 プロバイダ）と一致し、外部プロンプト md ファイル方式が使い方に 1 文で示されている。
- 開発履歴.md は v1.7.4 が既に正しく同期済みであることを確認済み（重複追記なし）。

---

## 検証（全体）

```
grep -nE 'load_prompt_file|model_list_timeout|_fetch_models_async|CUSTOM_PROMPT_FILE|_update_preset_note|_add_prompt_file_notice' CLAUDE.md
grep -c 'Ollama' README.md
grep -c 'RunPod' README.md
grep -c 'ocr_custom_prompt.md' README.md
grep -c 'v1.7.4' 開発履歴.md
```

- コード変更なしのため `ruff` / `pytest` は不要。
- 3 ファイル（README.md / CLAUDE.md / 開発履歴.md）以外は変更しない。

## 成功基準

- CLAUDE.md のモジュール責務記述・OCR モジュール群表・既知の制限が v1.7.4 の実コード状態と一致する。
- README.md の OCR プロバイダ列挙が実コード（6 プロバイダ）へ同期され、外部プロンプトファイル方式が言及される。
- 開発履歴.md は v1.7.4 が同期済みであることを検証済み（重複追記なし）。
