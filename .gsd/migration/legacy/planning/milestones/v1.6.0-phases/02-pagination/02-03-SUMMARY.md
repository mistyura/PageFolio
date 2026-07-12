---
phase: 02-pagination
plan: 03
subsystem: pagination-nav-footer
tags: [pagination, navigation, spinbox, dnd, i18n, uat-fix, tdd]
status: complete
requires:
  - 02-01
  - 02-02
provides:
  - "ui_builder.py ナビ/件数フッター行（◀ ▶ ＋ 範囲ラベル ＋ 件数 Spinbox state=readonly）"
  - "viewer.py 窓ナビ/件数変更ハンドラ・_refresh_all 窓正規化（reconcile_window_start 集約）"
  - "viewer.py _move_window 集約（窓移動後 current_page を新窓内へ追従・UAT 項目2 修正）"
  - "dnd.py D&D ドロップ先の local→global 換算（to_global・D-06）"
  - "lang.py 範囲ラベル/件数ラベルの ja/en 同一キー"
  - "pagination.py reconcile_window_start（描画前正規化 + D-11 条件付き追従の純関数）"
affects:
  - "Phase 02 完了（V16-UI-03 充足）。後続 Phase 03 へ"
tech-stack:
  added: []
  patterns:
    - "手動窓ナビと D-11 自動追従の対立をハンドラ層の不変条件（current は常に窓内）で解消"
    - "純関数 reconcile_window_start は (B) 操作による current 押し出し専用追従へ純化"
    - "件数 Spinbox は ttk.Spinbox + state=readonly で範囲外手入力を原理的に排除（Pitfall 3）"
key-files:
  created: []
  modified:
    - "pagefolio/pagination.py"
    - "pagefolio/ui_builder.py"
    - "pagefolio/viewer.py"
    - "pagefolio/dnd.py"
    - "pagefolio/lang.py"
    - "tests/test_pagination.py"
    - "開発履歴.md"
decisions:
  - "ナビ/件数フッターはサムネイル canvas 下の独立行。単一窓でも常に表示しボタンのみ disabled（D-09）"
  - "件数変更は settings へ永続化し即再描画。current を含む窓へ window_for_page で追従（D-03/D-05/D-11）"
  - "D&D ドロップ先はローカル位置を to_global で全ページ index へ変換（D-06）。selected_pages は全ページ index 不変（D-07）"
  - "thumb_cache は窓移動・件数変更でクリアしない（A1・Pitfall 2・TestThumbCacheRetention で自動検証）"
  - "[UAT 項目2 修正] _prev_window/_next_window を _move_window へ集約し窓移動後に current_page を新窓先頭へ追従。reconcile_window_start を (B) 専用追従へ純化し手動ナビの snap back を解消（debug: 260618-pagination-window-nav-snapback）"
metrics:
  completed: 2026-06-19
  files: 7
---

# Phase 02 Plan 03: ナビ/件数フッター UI・窓ハンドラ・D&D 換算 + UAT 項目2 修正 Summary

ページネーションのユーザー導線を完成させた。サムネイル canvas 下に独立フッター行（◀ ▶ ＋ 範囲ラベル ＋ 件数 Spinbox）を構築し、窓移動・件数変更ハンドラ、D&D ドロップ先の local→global 換算（`to_global`）、ja/en 同一 LANG キーを実装。`_refresh_all` の描画前窓正規化を純関数 `reconcile_window_start` に集約した。

UAT 項目2（手動窓ナビ ◀▶ 後に current_page の窓へ snap back する不具合）を `/gsd-debug` で体系的に解決し、Phase 02（V16-UI-03）を充足させた。

## 実装内容（feat 5dcd9e8 / 545f5af）

- **ui_builder.py**: `nav_frame` に ◀ ▶ ボタン・範囲ラベル・件数 `ttk.Spinbox`（`state=readonly`・`from_=10`/`to=100`/`increment=10`）を配置。手入力を排し範囲外値が原理的に入らない（Pitfall 3 / MEMORY: tkinter-readonly-widget-gotchas）。単一窓でも行は常に表示しボタンのみ `disabled`（D-09）。
- **viewer.py**: 窓ナビ/件数変更ハンドラ、`_refresh_all` の `reconcile_window_start` 集約（`clamp_window_start` 正規化 + current 窓外時のみ `window_for_page` 追従）。
- **dnd.py**: D&D ドロップ先のローカル位置を `to_global` で全ページ index へ換算（D-06）。`selected_pages` は全ページ index 不変条件を保持（D-07）。
- **lang.py**: 範囲ラベル・件数ラベルを ja/en 同一キーで追加。
- **開発履歴.md / APP_VERSION**: v1.7.0 へ同期（docs 1bf10aa）。

## UAT 項目2 修正（fix b913119 / debug 26cf5cc）

### 症状
手動の窓ナビ（◀ ▶）で current_page を含まない窓へ移動した直後、`_refresh_all` の正規化が current の窓へ snap back し、見たい窓が表示されない。

### 根本原因
純関数 `reconcile_window_start(window_start, current_page, page_size, n_pages)` は引数だけでは「(A) 手動 ◀▶ で意図的に current から離れた窓へ移動」と「(B) 削除等で current が現窓の外へ押し出された」を区別できない構造的問題。両者とも「current が窓外」へ帰着し、`current=0` と `current=5`（いずれも窓 [0,20) 在・`window_start=20` の窓外）は純関数には同一に見える。当初追加された矛盾する回帰テスト 2 件はこれを純関数単独で解こうとした帰結。

### 解決設計（候補1 採用・区別はハンドラ層で担保）
`_prev_window`/`_next_window` を共通 `_move_window(direction)` へ集約し、**窓移動後に `current_page` を新窓先頭（`= _page_window_start`）へ追従**させ「current は常に窓内」の不変条件を確立。これにより `reconcile_window_start` は (B) 押し出し専用の追従関数として矛盾なく機能する。`_move_window` は既存ナビ作法に合わせ `on_page_change` 発火・`window_label` を `_set_status` 表示。`_on_page_size_change` は従来どおり `window_for_page(current_page)` で current を窓内に保つため整合済み。`selected_pages`（D-07）/ D&D（D-06）に影響なし。フラグ方式（候補2）より集約点の純粋性を保てるため不採用。

### テスト対応
- 矛盾する回帰テスト 2 件（`test_manual_prev/next_window_not_snapped_back`）を削除（`_move_window` 経由では到達不能な仕様外入力）。
- 純関数テスト `TestReconcileWindowStart` の docstring を (B) 専用追従仕様へ修正。
- ハンドラ統合テスト `TestMoveWindowHandler` を新設（窓移動後に `current_page` が新窓内＝`_page_window_start` へ追従・`on_page_change` 発火・doc 未開 no-op を検証）。
- `TestThumbCacheRetention` のスタブを実 doc（長さ 47）＋ `plugin_manager`/`_set_status`/`_move_window` 束縛へ更新し、新ハンドラ経路でも thumb_cache 同一性が不変であることを継続検証。

## Verification

- `ruff check .`: All checks passed!
- `ruff format .`: 41 files left unchanged
- `pytest`（全スイート）: **564 passed**（修正前 561 = 559 passed + 2 failed → 矛盾 2 件削除・新規 5 件追加で 564・既存回帰なし）

## Commits

- 5dcd9e8: feat(02-03) ナビ/件数フッター行を構築しja/en同一LANGキーを追加
- 545f5af: feat(02-03) 窓/件数ハンドラと窓正規化・D&D local→global換算を実装
- 1bf10aa: docs(02-03) 開発履歴にページネーションを追記しAPP_VERSIONをv1.7.0へ同期
- b913119: fix(02-03) 手動窓ナビ後のsnap backを解消(UAT項目2)・current_pageを新窓へ追従
- 26cf5cc: docs(02-03) デバッグセッション記録: 窓ナビ snap back の根本原因と解決設計を resolved 化

## 関連

- デバッグセッション: `.planning/debug/260618-pagination-window-nav-snapback.md`（status: resolved）

## Self-Check: PASSED

- 変更ファイル全て存在: pagefolio/pagination.py / ui_builder.py / viewer.py / dnd.py / lang.py / tests/test_pagination.py / 開発履歴.md
- コミット全て存在: 5dcd9e8 / 545f5af / 1bf10aa / b913119 / 26cf5cc
