---
phase: 03-api
plan: "02"
subsystem: tests
tags: [test, import, regression, refac-01, refac-02, refac-04]
dependency_graph:
  requires: ["03-01"]
  provides: ["TEST-03"]
  affects: []
tech_stack:
  added: []
  patterns:
    - "明示 import 文 + シンボル存在 assert によるスモークテスト (D-06)"
    - "Tk root 不要ヘッドレステスト設計 (D-08)"
key_files:
  created:
    - tests/test_imports.py
  modified: []
decisions:
  - "D-06 採用: importlib 動的方式でなく明示 import 文で壊れた箇所を即特定"
  - "LLMConfigDialog は from pagefolio.dialogs import でテスト (トップレベル非公開のため)"
  - "TestSettingsApiImports の roundtrip テスト後は set_current_font_size(12) で副作用を戻す"
metrics:
  duration_minutes: 3
  completed_date: "2026-06-03"
  tasks_completed: 1
  files_changed: 1
---

# Phase 3 Plan 02: TEST-03 Import Regression Tests Summary

## One-liner

明示 import 文 + assert で REFAC-01〜04 の全 import パスを機械保証する 34 テストを tests/test_imports.py に実装（Tk root 不要・ヘッドレス安全）。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | tests/test_imports.py を作成し REFAC-01〜04 の import 回帰テストを実装 | 652894d | tests/test_imports.py |

## What Was Built

`tests/test_imports.py` を新規作成し、以下の 4 テストクラス・34 テスト関数を実装した。

### TestConstantsImports（REFAC-02 検証）

`pagefolio.constants`・`pagefolio.lang`・`pagefolio.themes` からの import が
後方互換を維持していることを 7 テストで検証。

- `from pagefolio.constants import APP_VERSION, LANG, THEMES, C` の一括 import
- `from pagefolio.lang import LANG` で `"ja" in LANG`
- `from pagefolio.themes import THEMES, C` で `"dark" in THEMES` かつ `isinstance(C, dict)`

### TestDialogsImports（REFAC-01 検証）

dialogs サブパッケージと個別モジュール双方からの import を 12 テストで検証。

- `pagefolio.dialogs` 経由で 5 クラス（AboutDialog / SettingsDialog / PluginDialog / MergeOrderDialog / MergeResizeDialog）が import できる
- 個別サブモジュール（`dialogs.about` / `.settings` / `.plugin` / `.merge` / `.llm_config`）からの import
- `LLMConfigDialog` は `pagefolio.dialogs` 経由で公開されており、個別モジュールと両方でテスト
- `from pagefolio import LLMConfigDialog`（トップレベル）は書かない（RESEARCH §Common Pitfalls 4 準拠）

### TestSettingsApiImports（REFAC-04 検証）

`set_current_font_size` / `get_current_font_size` の import と動作を 5 テストで検証。

- `pagefolio.settings` 直接と `pagefolio` トップレベルの両経路を確認
- roundtrip テスト: `set_current_font_size(14)` 後 `get_current_font_size() == 14`、テスト後 `set_current_font_size(12)` で副作用ゼロ

### TestPackageSurface

`import pagefolio` 後のトップレベルシンボル 19 個の存在を 10 テストで検証。
`pagefolio/__init__.py` の再エクスポートブロックと突き合わせ（D-07 準拠）。

## Verification Results

| チェック | 結果 |
|---------|------|
| `pytest tests/test_imports.py -x` | 34/34 PASSED |
| `pytest`（全体） | 199/199 PASSED |
| `ruff check .` | All checks passed |
| `ruff format .` | 32 files left unchanged |
| Tk root なし実行 | 0.12s で完了（ヘッドレス安全確認） |
| `from pagefolio import LLMConfigDialog` 不在 | 確認済み |
| `tk.Toplevel(` 不在 | 確認済み |
| `fitz.open(` 不在 | 確認済み |
| テストクラス数 4 以上 | 4 クラス |

## Deviations from Plan

なし — プラン通りに実行された。

唯一の作業は ruff の E501（行長）と I001（import ソート）エラーへの対応で、
日本語 docstring を短縮し `ruff --fix` でソート自動修正した。
これは実装の誤りではなく日本語文字幅と 88 文字制限の調整であり、逸脱ではない。

## Known Stubs

なし（テストファイルのみ。プロダクションコードの変更なし）。

## Threat Flags

なし（新規攻撃面ゼロ。テストファイル 1 つの追加のみ）。

## Self-Check: PASSED

- [x] `tests/test_imports.py` が存在する: C:/Users/shdwf/work/project/PageFolio/tests/test_imports.py
- [x] コミット 652894d が git log に存在する
- [x] 4 テストクラスが実装されている
- [x] `pytest tests/test_imports.py -x` exit 0（34 passed）
- [x] `pytest`（全体）exit 0（199 passed）
- [x] `ruff check . && ruff format .` exit 0
