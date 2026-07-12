---
id: S04
parent: M002
milestone: M002
provides:
  - pagefolio/md_render.py — OCR Markdown を (行種別, インライン span) へ変換する Tk/fitz 非依存純ロジック層
  - parse_markdown(md) — line_kind ∈ {md_h1, md_h2, md_bullet, md_code, ''} の構造データ契約（04-03 が import）
  - _split_inline(text) — **bold** を md_bold span として抽出する内部ヘルパー
  - pagefolio/ocr.py — PROVIDER_OCR_PROMPTS（provider→preset→文言）と純関数 resolve_ocr_prompt
  - resolve_ocr_prompt(preset, provider_name, custom_prompt='') — custom 上書き > プロバイダ別 > 汎用フォールバックの戻り値契約（04-03 が import）
  - PROVIDER_OCR_PROMPTS — claude(XML タグ)/gemini(明示指示) × text/table/markdown のテンプレート定数
  - pagefolio/ocr_dialog.py — _on_run のプロンプト解決を resolve_ocr_prompt(preset, name, custom) へ集約（V16-AI-02 配線）
  - pagefolio/ocr_dialog.py — _build の md_h1/md_h2/md_bullet/md_code/md_bold tk.Text タグ定義（C[]/self._font）
  - pagefolio/ocr_dialog.py — _render_results_ordered の preset=='markdown' 整形描画分岐 + _insert_markdown ヘルパー（V16-AI-01 配線）
requires: []
affects: []
key_files: []
key_decisions:
  - parse_markdown の判定優先順位を code > md_h2 > md_h1 > bullet > 通常段落に固定（in_code フラグでフェンス内見出しを構造的に抑止）
  - _split_inline は **bold** のみ対応（OCR Markdown の現実的サブセット・ネスト非対応）。空リストを返さず [(text, None)] へフォールバック
  - 新規 LANG キー・設定キーともゼロ（本フェーズは rendered 固定・トグル UI なし／04-RESEARCH.md Q1 最小実装）
  - PROVIDER_OCR_PROMPTS は claude/gemini のみ定義し lmstudio/tesseract/off は汎用 OCR_PROMPTS へフォールバック（Pitfall 4: Tesseract は prompt 無視・LMStudio はモデル依存）
  - 解決優先順位を custom_prompt(非空) > PROVIDER_OCR_PROMPTS[provider][preset] > OCR_PROMPTS.get(preset, OCR_PROMPTS['text']) に固定（既存 _on_run/ocr_dialog.py:1090 の既定 text と一致させ挙動を変えない）
  - 全 3 プリセット（text/table/markdown）を claude/gemini 双方で網羅（04-RESEARCH.md Q3 推奨）。claude は XML タグ構造、gemini は明示的・命令的指示文で文言を分離 [ASSUMED]
  - 新規 LANG キー・設定キーともゼロ（プロバイダ別テンプレートは設定不要のソース定数）
  - _on_run の provider 名取得（name）をプロンプト解決の前へ前方移動し、resolve_ocr_prompt(self.preset_var.get(), name, self.custom_prompt) 1 行へ置換。旧 OCR_PROMPTS.get(preset) if/else 分岐を撤廃（カスタム上書き温存は純関数側で担保）
  - md_* タグ定義行を # fmt: off/on + # noqa: E501 で単一行固定（受入基準の単一行 grep ゲートと ruff format 折返しの衝突を解消）
  - raw/rendered 切替トグルは未実装（rendered 固定・新規 LANG/設定キーをゼロに抑える 04-RESEARCH.md Q1 最小実装）。raw 原文はコピー/保存で確認可能
  - Task1/Task2 を単一 feat コミット（48193fb）へ集約（同一ファイル ocr_dialog.py 内で import 共有により密結合・リカバリ一括適用のため per-task アトミックから意図的逸脱）
patterns_established:
  - Markdown 構造データ契約: list[tuple[str, list[tuple[str, str|None]]]] を 04-03 描画分岐が import
  - 純関数 unit テストは OCRDialog 非インスタンス化・Tk 非生成でヘッドレス実行（Pitfall 1 回避）
  - resolve_ocr_prompt の戻り値契約（文字列）を 04-03 の _on_run 差し替えが import
  - 純関数 unit テストは OCRDialog 非インスタンス化・Tk 非生成でヘッドレス実行（TestResolveOcrPrompt）
  - Wave1 純関数 → Wave2 OCRDialog 配線の薄い接続層（描画/解決のロジックは純関数層に集約済）
observability_surfaces: []
drill_down_paths: []
duration: （リカバリ含む・実装は 48193fb で完了）
verification_result: passed
completed_at: 2026-06-19
blocker_discovered: false
---
# S04: Ai C

**# Phase 4 Plan 01: Markdown 整形描画の純ロジック層 Summary**

## What Happened

# Phase 4 Plan 01: Markdown 整形描画の純ロジック層 Summary

**OCR 結果 Markdown を (行種別, インライン span) へ変換する Tk/fitz 非依存の純関数 parse_markdown / _split_inline を新設し、9 件の Tk 非生成 unit テストで網羅検証**

## Performance

- **Duration:** 約 5 分
- **Started:** 2026-06-19T12:23:17Z
- **Completed:** 2026-06-19T12:26:36Z
- **Tasks:** 2
- **Files modified:** 2（新規 2）

## Accomplishments
- `pagefolio/md_render.py` を新設。`parse_markdown` が H1/H2/箇条書き/コードフェンス/通常段落の 5 行種別を分類し、`in_code` フラグでフェンス内の `# nothead` を見出し化しない構造的担保を実装
- `_split_inline` が `**bold**` を `md_bold` span として抽出（ReDoS 回避: 非貪欲 + 文字クラスのみ）
- `tests/test_md_render.py` で 6 行種別ケース + bold span + 行種別語彙の不変条件ループ網羅（計 9 ケース）を Tk 非生成で検証
- 04-03（Wave 2）が import する `parse_markdown` の戻り値契約を確定

## Task Commits

Each task was committed atomically:

1. **Task 1: md_render.py の純関数 parse_markdown / _split_inline を新設** - `f800fa3` (feat)
2. **Task 2: test_md_render.py で parse_markdown を unit 検証** - `b7fca93` (test)

_Note: 本プランは type=tdd だが、アナログ pagination.py に倣い Task 1=純関数モジュール / Task 2=unit テストの 2 ファイル分割構成（plan の tasks 定義どおり）。_

## Files Created/Modified
- `pagefolio/md_render.py` - OCR Markdown → (行種別, インライン span) 変換の Tk/fitz 非依存純ロジック層（import は標準 `re` のみ）
- `tests/test_md_render.py` - parse_markdown / _split_inline の unit テスト（9 ケース・OCRDialog 非インスタンス化）

## Decisions Made
- 判定優先順位 code > md_h2 > md_h1 > bullet > 通常段落に固定。`in_code` フラグでフェンス内を構造的に見出し非化（Pitfall 2 担保）
- `_split_inline` は `**bold**` のみ対応・空リストを返さず `[(text, None)]` フォールバック
- 箇条書き正規表現を `_BULLET = re.compile(r"^\s*[-*]\s+")` としてモジュール定数へ括り出し、match/sub で共用（04-RESEARCH.md のインライン `re.match`/`re.sub` を事前コンパイルへ最適化）

## Deviations from Plan

None - plan executed exactly as written.

（04-RESEARCH.md:266 の `_CODE` パターンは「将来拡張用に定義のみでも可」とされていたが、本タスクで `_BOLD` を使用する要件のみ必須だったため `_CODE` は定義のみ保持。箇条書き正規表現の事前コンパイルは ReDoS/線形時間方針の範囲内の素直な最適化でありロジック変更を伴わない。）

## Issues Encountered
None。`ruff format` が `text[pos:m.start()]` を `text[pos : m.start()]` へ整形した以外に手戻りなし。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `parse_markdown` の戻り値契約（line_kind 語彙・span 形式）が確定。04-03 の `ocr_dialog.py` 描画分岐が `from pagefolio.md_render import parse_markdown` で import 可能
- フルスイート 591 passed（582 ベースライン + 新規 9 件）・既存に赤なし・`ruff check . && ruff format` 通過
- APP_VERSION は中間フェーズのため未バンプ（v1.6.0 据え置き）

## Self-Check: PASSED
- FOUND: pagefolio/md_render.py
- FOUND: tests/test_md_render.py
- FOUND: f800fa3 (Task 1)
- FOUND: b7fca93 (Task 2)

---
*Phase: 04-ai-c*
*Completed: 2026-06-19*

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
