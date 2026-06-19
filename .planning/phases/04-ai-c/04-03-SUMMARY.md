---
phase: 04-ai-c
plan: 03
subsystem: ocr
tags: [ocr, ocr-dialog, markdown, tk-text-tag, prompt, provider, wiring, backward-compat]

# Dependency graph
requires:
  - phase: 04
    plan: 01
    provides: "pagefolio/md_render.py — parse_markdown（行種別×インライン span）純関数"
  - phase: 04
    plan: 02
    provides: "pagefolio/ocr.py — resolve_ocr_prompt / PROVIDER_OCR_PROMPTS 純関数"
provides:
  - "pagefolio/ocr_dialog.py — _on_run のプロンプト解決を resolve_ocr_prompt(preset, name, custom) へ集約（V16-AI-02 配線）"
  - "pagefolio/ocr_dialog.py — _build の md_h1/md_h2/md_bullet/md_code/md_bold tk.Text タグ定義（C[]/self._font）"
  - "pagefolio/ocr_dialog.py — _render_results_ordered の preset=='markdown' 整形描画分岐 + _insert_markdown ヘルパー（V16-AI-01 配線）"
affects: [ai-c, phase-04-complete]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "純関数（Wave1）を OCRDialog の薄い描画/解決層へ配線（Wave2）。描画は parse_markdown 戻り値を insert/tag_add するだけ・解決は resolve_ocr_prompt 1 行"
    - "整形は表示専用（tk.Text タグ）に限定し、コピー/保存（_format_full_text）は raw 維持（Pitfall 5）"
    - "preset=='markdown' ガードで text/table/LMStudio/Tesseract 素出力に Markdown パーサを当てない構造的後方互換（Pitfall 2）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_dialog.py

key-decisions:
  - "_on_run の provider 名取得（name）をプロンプト解決の前へ前方移動し、resolve_ocr_prompt(self.preset_var.get(), name, self.custom_prompt) 1 行へ置換。旧 OCR_PROMPTS.get(preset) if/else 分岐を撤廃（カスタム上書き温存は純関数側で担保）"
  - "md_* タグ定義行を # fmt: off/on + # noqa: E501 で単一行固定（受入基準の単一行 grep ゲートと ruff format 折返しの衝突を解消）"
  - "raw/rendered 切替トグルは未実装（rendered 固定・新規 LANG/設定キーをゼロに抑える 04-RESEARCH.md Q1 最小実装）。raw 原文はコピー/保存で確認可能"
  - "Task1/Task2 を単一 feat コミット（48193fb）へ集約（同一ファイル ocr_dialog.py 内で import 共有により密結合・リカバリ一括適用のため per-task アトミックから意図的逸脱）"

patterns-established:
  - "Wave1 純関数 → Wave2 OCRDialog 配線の薄い接続層（描画/解決のロジックは純関数層に集約済）"

requirements-completed: [V16-AI-01, V16-AI-02]

# Metrics
duration: "（リカバリ含む・実装は 48193fb で完了）"
completed: 2026-06-19
status: complete
---

# Phase 4 Plan 03: OCRDialog 配線（Markdown 整形描画 + プロバイダ別プロンプト解決）Summary

**Wave 1 の 2 純関数（parse_markdown / resolve_ocr_prompt）を OCRDialog の 3 箇所へ配線。_on_run のプロンプト合成を resolve_ocr_prompt へ集約（V16-AI-02）、_build に md_* 5 タグを定義、_render_results_ordered に preset=='markdown' 整形描画分岐（_insert_markdown）を追加（V16-AI-01）。コピー/保存は raw 維持。ruff・pytest 597 緑。**

## Performance

- **Completed:** 2026-06-19
- **Tasks:** 3（auto 2 + checkpoint:human-verify 1）
- **Files modified:** 1（pagefolio/ocr_dialog.py・+52/-10）

## Accomplishments

- **Task 1（_on_run・V16-AI-02 配線）:** プロンプト合成（旧 `if self.custom_prompt: ... else: OCR_PROMPTS.get(preset)`）を `self._ocr_prompt = resolve_ocr_prompt(self.preset_var.get(), name, self.custom_prompt)` 1 行へ置換。provider 名 `name` を解決呼び出しの前へ前方移動し NameError を構造的に回避。カスタム上書き温存（成功基準3）は純関数側に委譲。
- **Task 2（_build タグ + _render_results_ordered 分岐・V16-AI-01 配線）:** `self.text` 生成直後に md_h1/md_h2/md_bullet/md_code/md_bold の 5 タグを `tag_configure` で定義（テーマ色は `C["ACCENT"]`/`C["BG_PANEL"]`・フォントは `self._font(delta, weight)`・ハードコード禁止遵守）。`_render_results_ordered` に `preset == "markdown"` ガード付きで `parse_markdown` 戻り値を insert/tag_add する薄い `_insert_markdown` ヘルパーを追加。preset!=markdown は従来の素朴 insert を完全温存。
- **raw 維持:** `_format_full_text`（コピー/保存）は無改変。整形は tk.Text 表示専用に留め、保存ファイルには raw Markdown が出力される（Pitfall 5）。
- **Phase 4 = v1.6.0 最終フェーズの配線完了。** V16-AI-01（Markdown 整形表示）/ V16-AI-02（プロバイダ別プロンプト）の両要件を OCRDialog 上で同時充足。

## Acceptance Criteria 結果

Task 1（_on_run）:
- `resolve_ocr_prompt(` 呼び出し 1 件 + import 行に存在 — OK
- 旧分岐 `OCR_PROMPTS.get(preset` 除去（grep 0）— OK
- `resolve_ocr_prompt(self.preset_var.get(), name` 1 件・`name` 取得が解決行より前 — OK
- ast.parse 例外なし / `ruff check pagefolio/ocr_dialog.py` エラー 0 — OK

Task 2（_build / _render_results_ordered）:
- `tag_configure("md_` 5 件（md_h1/md_h2/md_bullet/md_code/md_bold）— OK
- md_h1 が `C[` 経由（ハードコード非使用）— OK
- `parse_markdown` 2 件以上（import + 呼び出し・実測 3）+ `== "markdown"` ガード存在 — OK
- `_format_full_text` メソッド内に parse_markdown 非混入（awk スコープ抽出 0）— OK
- フルスイート `pytest -q` 597 件緑 / `ruff check` エラー 0 — OK

## Verification

- `ruff check .` → All checks passed
- `ruff format --check .` → 45 files already formatted
- `python -m pytest -q` → 597 passed
- `python -c "import ast; ast.parse(...)"` → 構文確認通過
- human-verify チェックポイント → **ユーザー判断によりスキップ（option 2: 実機目視確認なしで継続完了）**。文言効果（OCR 出力品質向上）は [ASSUMED] のまま実機未検証。後述「Known Stubs / 申し送り」参照。

## Deviations from Plan

- **human-verify チェックポイント（gate=blocking）をスキップ:** プランは実機目視確認（markdown 整形表示・後方互換・コピー raw 維持・カスタム両立）を承認ゲートとして要求していたが、ユーザーが resume 時に「目視確認をスキップして継続を完了」を選択。実装・自動ゲート（ruff/pytest597/受入 grep）は全通過済のため構造的健全性は担保されるが、tk.Text 上の**実描画の見え方**と**プロバイダ別プロンプトの実 API 出力品質**は未検証。
- **executor Bash 権限拒否のリカバリ:** gsd-executor の Bash が ruff/pytest/git で拒否されたため、実装（Edit）適用後の検証・コミット（48193fb）および本継続（SUMMARY/STATE/ROADMAP/docs）をオーケストレータがインラインで実施。
- **単一 feat コミットへ集約:** Task1/Task2 を per-task ではなく 48193fb 1 コミットへ（密結合・一括リカバリのため）。

## Known Stubs

- raw/rendered 切替トグルは未実装（rendered 固定・最小実装の確定方針）。raw はコピー/保存で取得可能。

## Threat Flags

なし。tk.Text.insert はプレーンテキスト挿入でマークアップ/コード実行なし（T-04-INJ mitigate）。整形は表示専用でエクスポートは raw（情報露出経路を増やさない）。parse_markdown は線形時間（ReDoS 回避済・04-01）。

## Commits

- `48193fb` feat(04-03): OCRDialog に Markdown 整形描画とプロバイダ別プロンプト解決を配線

## Self-Check: PASSED

- FOUND: pagefolio/ocr_dialog.py（resolve_ocr_prompt 呼び出し・md_* 5 タグ・parse_markdown 分岐・_insert_markdown）
- FOUND commit: 48193fb
- NOTE: human-verify はユーザー判断でスキップ（実機目視未検証・要件の構造実装は完了）
