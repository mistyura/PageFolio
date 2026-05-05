---
id: T04
parent: S01
milestone: M001
key_files:
  - pagefolio/app.py
key_decisions:
  - os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS パターンを採用（file_ops.py との一貫性のため）
  - import os を標準ライブラリ import に追加
duration: 
verification_result: passed
completed_at: 2026-05-04T04:01:39.798Z
blocker_discovered: false
---

# T04: `_on_dnd_drop()` の `.pdf` ハードコードフィルターを `SUPPORTED_EXTENSIONS` 定数参照に差し替え、画像ファイルのドロップにも対応した

**`_on_dnd_drop()` の `.pdf` ハードコードフィルターを `SUPPORTED_EXTENSIONS` 定数参照に差し替え、画像ファイルのドロップにも対応した**

## What Happened

`pagefolio/app.py` の `_on_dnd_drop()` メソッドで、ドロップされたファイルをフィルタリングする際に `p.lower().endswith(".pdf")` というハードコード文字列比較が使われていた。これを `os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS` に変更し、`constants.py` で定義された `SUPPORTED_EXTENSIONS` frozenset（PDF + 各種画像拡張子）を参照するよう修正した。合わせて `import os` と `SUPPORTED_EXTENSIONS` の import を追加した。ruff --fix により import 順序も自動整列された（`LANG, SUPPORTED_EXTENSIONS, C` のアルファベット順）。

## Verification

`ruff check pagefolio/app.py` がクリーン、`python -c "import ast; ast.parse(open('pagefolio/app.py', encoding='utf-8').read())"` が構文エラーなしで通過した。

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `ruff check pagefolio/app.py` | 0 | All checks passed | 800ms |
| 2 | `python -c "import ast; ast.parse(open('pagefolio/app.py', encoding='utf-8').read())"` | 0 | 構文OK | 200ms |

## Deviations

ruff --fix による自動実行で import ブロックの並び順が修正された（`LANG, C` → `LANG, SUPPORTED_EXTENSIONS, C` のアルファベット順）。計画外だが正常な整形。

## Known Issues

なし

## Files Created/Modified

- `pagefolio/app.py`
