---
phase: 02-pagination
plan: 01
subsystem: pagination-core
tags: [pagination, pure-logic, index-conversion, tdd, fixtures]
status: complete
requires: []
provides:
  - "pagefolio/pagination.py（Tk 非依存の窓計算・local↔global 変換・件数クランプ純関数 8 個）"
  - "tests/test_pagination.py（境界値・往復不変・D&D 換算・窓またぎ選択照合の named テスト 47 件）"
  - "tests/conftest.py large_pdf_doc フィクスチャ（47 ページ）"
affects:
  - "02-02（窓化描画・self._page_window_start/_page_size 初期化・thumb_page_size 永続化）"
  - "02-03（ナビフッター UI・件数 Spinbox・page_size_var）"
tech-stack:
  added: []
  patterns:
    - "純ロジック層を新規モジュールへ集約（viewer.py:40-49 の純関数作法に倣う）"
    - "TDD（RED→GREEN）で境界値を先に固定"
key-files:
  created:
    - "pagefolio/pagination.py"
    - "tests/test_pagination.py"
  modified:
    - "tests/conftest.py"
decisions:
  - "clamp_page_size をフェーズ内確定名として固定し同モジュールへ集約（W1）"
  - "window_label は文言裁量と疎結合にするため素朴な範囲文字列を生成し、テストは数値包含で検証"
  - "純関数は不正引数（page_size<=0 / n_pages<=0）でも例外を投げず安全側へ倒す（T-2-01）"
metrics:
  duration: 約 8 分
  completed: 2026-06-18
  tasks: 2
  files: 3
---

# Phase 02 Plan 01: ページネーション純ロジック層 Summary

表示窓のローカル位置 ↔ 全ページインデックス変換と窓計算を、Tkinter / fitz 非依存の純関数群として新規モジュール `pagefolio/pagination.py` に切り出し、`tests/test_pagination.py` で全境界値・往復不変条件をヘッドレス検証した（Wave 0・テスト基盤）。

## 実装内容

### Task 1: pagination.py 純関数層 + test_pagination.py（TDD）

`pagefolio/pagination.py` に Tk/fitz 非依存の純関数 8 個を実装:

| 関数 | 役割 | 参照決定 |
|------|------|----------|
| `window_bounds(window_start, page_size, n_pages)` | 半開区間 (lo, hi)・最終窓を n_pages でクランプ | D-10 |
| `to_global(local_pos, window_start)` | ローカル位置→全ページ index | D-06 |
| `to_local(global_idx, window_start)` | 全ページ index→ローカル位置 | D-06 |
| `window_for_page(page_idx, page_size)` | page_idx を含む窓先頭（page_size 倍数） | D-11 |
| `clamp_window_start(window_start, page_size, n_pages)` | 削除・件数変更後の有効窓先頭へ寄せ | — |
| `window_label(window_start, page_size, n_pages)` | 1 始まり範囲文字列 | D-09/D-10 |
| `window_nav_state(window_start, page_size, n_pages)` | (prev_enabled, next_enabled) | D-09 |
| `clamp_page_size(value)` | 件数を [10,100] にクランプ・既定 20 | W1 |

TDD で RED（`ModuleNotFoundError` を確認）→ GREEN（47 テスト全 green）。named テストクラスは RESEARCH L398-403 / VALIDATION Per-Task Map に整合:
`TestWindowBounds`(SC1) / `TestPageSizePersist`(SC2) / `TestDndIndexConvert`(SC3) / `TestSelectionAcrossWindows`(SC4) / `TestWindowFollow`(D-11) / `TestNavState`(D-09) ＋ `TestIndexConvert`（往復不変ループ網羅）/ `TestClampWindowStart` / `TestWindowLabel`。

- 往復不変条件 `to_global(to_local(g, s), s) == g` を 0..46 × start∈{0,20,40} で網羅
- 端数最終窓 `window_bounds(40,20,47)==(40,47)`、doc 未オープン `window_bounds(0,20,0)==(0,0)`
- `clamp_page_size` の純ロジック（5→10 / 200→100 / "30"→30 / ""→20 / None→20 / "abc"→20）を `(ValueError, TypeError)` 捕捉で実装（裸 except 不使用・CLAUDE.md 準拠）
- pagination.py は `fitz` / `tkinter` を一切 import しない（grep 確認済み）

### Task 2: conftest.py large_pdf_doc フィクスチャ

`tests/conftest.py` に既存 `sample_pdf_doc` と同じ generator + close 作法で 47 ページ A4 doc を生成する `large_pdf_doc` フィクスチャを追加。件数 20 → 最終窓 41–47（端数最終窓・D-10）の境界値検証に対応。`pytest --fixtures` で認識を確認。

## Deviations from Plan

None - plan executed exactly as written.

（純関数の堅牢化ガード（page_size<=0 / n_pages<=0）は plan の action / threat_model T-2-01 に明記されており、追加ではなく計画どおりの実装。）

## Verification

- `pytest tests/test_pagination.py -x -q`: 47 passed
- `pytest`（全スイート）: 540 passed（回帰なし。ベースライン ~490 + 新規 47 + 既存増分）
- `ruff check .`: All checks passed!
- `ruff format .`: 41 files left unchanged
- pagination.py が `fitz` / `tkinter` を import していないことを grep で確認
- named クラス `grep -c`: TestDndIndexConvert=1 / TestSelectionAcrossWindows=1 / TestPageSizePersist=1

## 後続プランへの引き継ぎ

- 02-02 / 02-03 は `from pagefolio.pagination import ...` で本層を import して窓化する（`clamp_page_size` は確定名・import 名を一致させること）
- 新規 `self.*` 属性（`self._page_window_start` / `self._page_size`）の初期化・`thumb_page_size`（既定 20）永続化は 02-02 で実装
- ナビフッター UI（◀ ▶ / 範囲ラベル / 件数 Spinbox）・`page_size_var` ・LANG キー（ja/en 同一）は 02-03 で実装

## Commits

- d0a36da: feat(02-01) ページネーション純ロジック層と境界値テストを追加
- c8ea317: test(02-01) conftest に 47 ページ large_pdf_doc フィクスチャを追加

## Self-Check: PASSED

- 作成ファイル全て存在: pagefolio/pagination.py / tests/test_pagination.py / tests/conftest.py / 02-01-SUMMARY.md
- コミット全て存在: d0a36da / c8ea317
