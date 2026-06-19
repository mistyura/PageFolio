---
phase: 04-ai-c
plan: 01
subsystem: ocr
tags: [markdown, parser, pure-function, regex, redos, tk-independent]

# Dependency graph
requires:
  - phase: 02
    provides: pagination.py の「純関数集約 + Tk 非生成 unit テスト」パターン（アナログ）
provides:
  - "pagefolio/md_render.py — OCR Markdown を (行種別, インライン span) へ変換する Tk/fitz 非依存純ロジック層"
  - "parse_markdown(md) — line_kind ∈ {md_h1, md_h2, md_bullet, md_code, ''} の構造データ契約（04-03 が import）"
  - "_split_inline(text) — **bold** を md_bold span として抽出する内部ヘルパー"
affects: [04-03, ocr_dialog, ai-c]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "純ロジック層分離: 描画変換を Tk 依存モジュールにベタ書きせず純関数へ集約（pagination.py 踏襲）"
    - "ReDoS 回避: 正規表現は非貪欲 .+? + 文字クラス [^`]+ のみ・量指定子のネスト禁止（線形時間）"

key-files:
  created:
    - pagefolio/md_render.py
    - tests/test_md_render.py
  modified: []

key-decisions:
  - "parse_markdown の判定優先順位を code > md_h2 > md_h1 > bullet > 通常段落に固定（in_code フラグでフェンス内見出しを構造的に抑止）"
  - "_split_inline は **bold** のみ対応（OCR Markdown の現実的サブセット・ネスト非対応）。空リストを返さず [(text, None)] へフォールバック"
  - "新規 LANG キー・設定キーともゼロ（本フェーズは rendered 固定・トグル UI なし／04-RESEARCH.md Q1 最小実装）"

patterns-established:
  - "Markdown 構造データ契約: list[tuple[str, list[tuple[str, str|None]]]] を 04-03 描画分岐が import"
  - "純関数 unit テストは OCRDialog 非インスタンス化・Tk 非生成でヘッドレス実行（Pitfall 1 回避）"

requirements-completed: [V16-AI-01]

# Metrics
duration: 5min
completed: 2026-06-19
status: complete
---

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
