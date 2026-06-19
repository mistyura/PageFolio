---
phase: 04-ai-c
plan: 02
subsystem: ocr
tags: [ocr, prompt, provider, pure-function, tk-independent, backward-compat]

# Dependency graph
requires:
  - phase: 04
    plan: 01
    provides: 「純関数集約 + Tk 非生成 unit テスト」パターン（アナログ・md_render.py）
provides:
  - "pagefolio/ocr.py — PROVIDER_OCR_PROMPTS（provider→preset→文言）と純関数 resolve_ocr_prompt"
  - "resolve_ocr_prompt(preset, provider_name, custom_prompt='') — custom 上書き > プロバイダ別 > 汎用フォールバックの戻り値契約（04-03 が import）"
  - "PROVIDER_OCR_PROMPTS — claude(XML タグ)/gemini(明示指示) × text/table/markdown のテンプレート定数"
affects: [04-03, ocr_dialog, ai-c]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "プロンプト分岐の純関数集約: Provider クラス内/_on_run に散在させず resolve_ocr_prompt 1 箇所へ（Provider 層の ocr_image(b64, prompt) 文字列契約は不変）"
    - "後方互換の構造的担保: custom_prompt 非空 → 即 return を最優先に固定し既存カスタム上書き挙動を温存（Pitfall 3）"

key-files:
  created: []
  modified:
    - pagefolio/ocr.py
    - tests/test_provider_ui.py

key-decisions:
  - "PROVIDER_OCR_PROMPTS は claude/gemini のみ定義し lmstudio/tesseract/off は汎用 OCR_PROMPTS へフォールバック（Pitfall 4: Tesseract は prompt 無視・LMStudio はモデル依存）"
  - "解決優先順位を custom_prompt(非空) > PROVIDER_OCR_PROMPTS[provider][preset] > OCR_PROMPTS.get(preset, OCR_PROMPTS['text']) に固定（既存 _on_run/ocr_dialog.py:1090 の既定 text と一致させ挙動を変えない）"
  - "全 3 プリセット（text/table/markdown）を claude/gemini 双方で網羅（04-RESEARCH.md Q3 推奨）。claude は XML タグ構造、gemini は明示的・命令的指示文で文言を分離 [ASSUMED]"
  - "新規 LANG キー・設定キーともゼロ（プロバイダ別テンプレートは設定不要のソース定数）"

patterns-established:
  - "resolve_ocr_prompt の戻り値契約（文字列）を 04-03 の _on_run 差し替えが import"
  - "純関数 unit テストは OCRDialog 非インスタンス化・Tk 非生成でヘッドレス実行（TestResolveOcrPrompt）"

requirements-completed: [V16-AI-02]

# Metrics
duration: 4min
completed: 2026-06-19
status: complete
---

# Phase 4 Plan 02: プロバイダ別プロンプト解決純関数層 Summary

**単一プリセットのみだった OCR_PROMPTS を「プリセット × プロバイダ × カスタム」へ昇格させ、Claude=XML タグ／Gemini=明示指示のプロバイダ別テンプレート PROVIDER_OCR_PROMPTS と純関数 resolve_ocr_prompt を pagefolio/ocr.py に新設、6 件の Tk 非生成 unit テストで優先順位とフォールバックを検証**

## Performance

- **Duration:** 約 4 分
- **Completed:** 2026-06-19
- **Tasks:** 2
- **Files modified:** 2（新規 0・既存 2）

## Accomplishments

- `pagefolio/ocr.py` に定数 `PROVIDER_OCR_PROMPTS`（`claude`/`gemini` の 2 プロバイダ × `text`/`table`/`markdown` の 3 プリセット）を `OCR_PROMPTS` 直後へ追加。`claude` は `<task>`/`<rules>` XML タグで「本文のみ・前置きなし」を構造化、`gemini` は命令的な明示指示文で同等の意図を表現。
- 純関数 `resolve_ocr_prompt(preset, provider_name, custom_prompt="")` を追加。優先順位は custom 非空 > プロバイダ別テンプレート > 汎用 `OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])`。Tk/ネットワーク非依存（辞書 get と文字列合成のみ・例外捕捉なし）。
- `tests/test_provider_ui.py` に `TestResolveOcrPrompt`（6 ケース）を末尾追記。custom 上書き／claude・gemini 別テンプレ／lmstudio・tesseract フォールバック／未定義 preset の既定 text フォールバックを網羅。import は `from pagefolio.ocr import OCR_PROMPTS, resolve_ocr_prompt` を既存ブロックへ追加、Tk 生成は不要。
- 04-03（Wave 2 の `_on_run` 差し替え）が import する `resolve_ocr_prompt` の戻り値契約を確定。Provider 層（`_build_payload`/`ocr_image`）は文字列を受けるだけで変更不要。

## Acceptance Criteria 結果

Task 1（ocr.py）:
- `def resolve_ocr_prompt` 1 件・`PROVIDER_OCR_PROMPTS` 参照 2 件以上 — OK
- `set(P)=={'claude','gemini'}`・両者に `markdown` キー存在・`lmstudio`/`tesseract` キー不在 — OK（`python -c` 表明緑）
- custom 上書き温存（`r('table','gemini','C')=='C'`）— OK
- フォールバック（`r('text','tesseract','')==O['text']`・`r('zzz','off','')==O['text']`）— OK
- `ruff check pagefolio/ocr.py` エラー 0 — OK

Task 2（test_provider_ui.py）:
- `class TestResolveOcrPrompt` 1 件・`resolve_ocr_prompt` 出現 6 以上 — OK
- 新規 Tk 生成（`tk.Tk(`）追加なし — OK
- `pytest tests/test_provider_ui.py -q` 全件 passed（47 件）— OK
- `ruff check tests/test_provider_ui.py` エラー 0 — OK
- 回帰: `pytest -q` フルスイート 597 件緑（591 ベースライン + 新規 6）— OK

## Verification

- `python -m pytest tests/test_provider_ui.py -q` → 47 passed
- `python -m pytest -q` → 597 passed
- `ruff check . && ruff format --check .` → All checks passed / 45 files already formatted
- `resolve_ocr_prompt` 内に Tk 依存 import / ネットワーク呼び出しなし（純関数）

## Deviations from Plan

None - plan executed exactly as written.

`tests/test_provider_ui.py` の docstring 1 行が初回 ruff で E501（98>88）に触れたため文言を短縮した（フォーマット調整のみ・挙動への影響なし・Task 2 コミットに同梱）。

## Known Stubs

None.

## Threat Flags

なし（本プランは文字列合成のみで新規の送信経路・入力経路を増やさない。`PROVIDER_OCR_PROMPTS` はソース定数で実行時改変経路なし。`resolve_ocr_prompt` は logger を持たずプロンプト本文をログ出力しない＝threat register T-04-IDISC/T-04-TAMPER の accept 方針どおり）。

## Commits

- `0e55b20` feat(04-02): ocr.py に PROVIDER_OCR_PROMPTS と純関数 resolve_ocr_prompt を追加
- `015cba4` test(04-02): test_provider_ui.py に TestResolveOcrPrompt を追加

## Self-Check: PASSED

- FOUND: pagefolio/ocr.py（resolve_ocr_prompt / PROVIDER_OCR_PROMPTS import OK）
- FOUND: tests/test_provider_ui.py（TestResolveOcrPrompt）
- FOUND commit: 0e55b20
- FOUND commit: 015cba4
