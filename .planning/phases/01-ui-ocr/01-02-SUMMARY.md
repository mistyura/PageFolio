---
phase: 01-ui-ocr
plan: 02
subsystem: ui
tags: [ui, tkinter, thumbnail, layout, versioning]
requires:
  - "pagefolio/viewer.py（_on_thumb_zoom_release・倍率参照、未変更）"
provides:
  - "サムネイルスライダー専用の全幅独立行 zoom_frame（sel_frame の直後・canvas_frame の前）"
  - "v1.6.0 へ更新された APP_VERSION / README バッジ / 開発履歴.md エントリ"
affects:
  - "pagefolio/ui_builder.py（_build_thumb_panel の pack 構造）"
tech_stack:
  added: []
  patterns:
    - "tk.Frame(parent, bg=C['BG_PANEL']) + pack(fill='x') による全幅独立行（hdr/sel_frame と同型）"
key_files:
  created: []
  modified:
    - "pagefolio/ui_builder.py"
    - "pagefolio/constants.py"
    - "README.md"
    - "開発履歴.md"
decisions:
  - "D-07/D-08: スライダーを独立 zoom_frame の全幅行へ移設しボタンとの幅競合を解消"
  - "D-09: 範囲 0.5〜2.5 / thumb_zoom_var / <ButtonRelease-1>→_on_thumb_zoom_release は不変、配置のみ変更"
  - "APP_VERSION を真の情報源とし README バッジ・開発履歴.md を同期（CLAUDE.md 規約）"
metrics:
  duration: "約10分"
  completed: "2026-06-18"
  tasks: 2
  files: 4
status: complete
requirements:
  - V16-UI-02
---

# Phase 01 Plan 02: サムネイルスライダー配置改善・v1.6.0 バージョン同期 Summary

サムネイルサイズ変更スライダーを `sel_frame`（全選択/解除ボタンと同一行・`side="right"`）から、ボタン行直後の新設全幅独立行 `zoom_frame` へ移設し、左ペイン縮小時の幅競合を解消（V16-UI-02・D-07〜D-09）。あわせて `APP_VERSION` を v1.6.0 へ更新し README バッジ・開発履歴.md を同期。挙動（範囲・変数・コールバック）は不変、`viewer.py` / `settings.py` は未変更。

## Tasks Completed

| Task | 名称 | Commit | 主な変更 |
|------|------|--------|----------|
| 1 | サムネイルスライダーを独立全幅行へ移設 | `457f858` | pagefolio/ui_builder.py（zoom_frame 新設・親と pack 引数のみ変更） |
| 2 | APP_VERSION 更新・README バッジ・開発履歴.md 同期 | `dc120c6` | pagefolio/constants.py / README.md / 開発履歴.md |

## Implementation Details

### Task 1: スライダーの独立全幅行への移設

`_build_thumb_panel`（pagefolio/ui_builder.py）内で、`thumb_zoom_var` / `thumb_zoom_scale` の生成とバインドを `sel_frame` 内 `side="right", fill="x", expand=True` から、`sel_frame` の直後・`canvas_frame` の前に新設した `zoom_frame`（`tk.Frame(parent, bg=C["BG_PANEL"])` + `pack(fill="x", padx=6, pady=(0, 4))`）へ移設。スライダーの `pack` を `side="right"` 指定なしの `pack(fill="x", expand=True, padx=2)` にして全幅配置。

不変条件（D-09）はすべて維持: `from_=0.5` / `to=2.5` / `variable=self.thumb_zoom_var` / `orient="horizontal"`、`<ButtonRelease-1>` → `self._on_thumb_zoom_release`、初期値 `self.settings.get("thumb_zoom", 1.0)`。`select_all` / `deselect` ボタン 2 つは `sel_frame` にそのまま残置。

### Task 2: バージョン同期

- `pagefolio/constants.py`: `APP_VERSION` を `"v1.5.0"` → `"v1.6.0"`。
- `README.md`: バージョンバッジを v1.6.0 へ同期（v1.5.0 残存なし）。
- `開発履歴.md`: 索引テーブル行・詳細セクション・「最終更新」行に v1.6.0 Phase 1 エントリを追記。本フェーズ 2 プラン分（V16-UI-01 読み取り専用化 + V16-UI-02 スライダー移設）を 1 エントリにまとめて記載。
- `pyproject.toml` は未編集（CLAUDE.md 禁止事項遵守）。

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `python -c "...ast.parse(ui_builder.py)..."` 構文検証通過。
- `pagefolio/viewer.py` / `pagefolio/settings.py` が本プラン全体（8694c72..HEAD）で git diff 未変更（0 件）。
- `grep 'APP_VERSION = "v1.6.0"' pagefolio/constants.py` 一致、README / 開発履歴.md に v1.6.0 反映、README に v1.5.0 残存なし。
- `pyproject.toml` 未変更（git diff 0 件）。
- `ruff check .` 全通過 / `ruff format --check .` 39 ファイル整形済み。
- `pytest` 493 件全通過。

acceptance_criteria（プラン）はすべて充足:
- zoom_frame が独立 `tk.Frame` として生成され `pack(fill="x", ...)` で全幅配置。
- `thumb_zoom_scale.pack(...)` に `side="right"` を含まない。
- 範囲/変数/orient/バインド不変。
- zoom_frame の pack が canvas_frame の pack より前。
- viewer.py / settings.py 未変更。

## Known Stubs

なし。スタブ・プレースホルダの導入なし（既存ウィジェットの親フレームと pack 引数の変更、および定数/ドキュメントのテキスト更新のみ）。

## Notes for Next Phase

- 手動確認（実行者裁量・未実施）: アプリ起動 → 左ペインを縮小し、スライダーが独立行で全幅・潰れず操作可能、サイズ変更が従来どおり反映されることを目視確認。
- Phase 1（V16-UI-01 + V16-UI-02）は本プランで完了。次は Phase 2（大量ページのページネーション表示・V16-UI-03、高リスク隔離）。

## Self-Check: PASSED

- FOUND: .planning/phases/01-ui-ocr/01-02-SUMMARY.md / pagefolio/ui_builder.py / pagefolio/constants.py / README.md / 開発履歴.md
- FOUND commit: 457f858（Task 1）/ dc120c6（Task 2）
