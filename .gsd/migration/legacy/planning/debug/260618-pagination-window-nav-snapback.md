---
slug: 260618-pagination-window-nav-snapback
status: resolved
trigger: uat
goal: find_and_fix
created: 2026-06-18
resolved: 2026-06-19
head: 1bf10aa
phase: 02-03-pagination
---

# Debug: ページネーション窓ナビの snap back（UAT 項目2 NG）

## Symptoms

Phase 02-03 で導入したサムネイルのページネーション（窓表示）において、
手動の窓ナビ（◀ ▶ ボタン）または件数変更で「current_page を含まない窓」へ
移動した直後、`_refresh_all` の正規化処理が current_page の窓へ snap back して
しまい、ユーザーが見たい窓が表示されない（UAT 項目2 NG）。

- 再現手順:
  1. 47 ページ程度の PDF を開く（件数 20、current_page=0、窓1 [0,20) 表示）。
  2. ▶ ボタンで窓2 [20,40) へ移動。
  3. `_refresh_all` が走った直後、表示が窓1 [0,20) へ戻ってしまう。
- 期待: 手動で移動した窓2 が温存されること。

## Current Focus

- **hypothesis:** 純関数 `reconcile_window_start(window_start, current_page, page_size, n_pages)`
  は引数だけでは「(A) 手動 ◀▶ で意図的に current から離れた窓へ移動した」と
  「(B) 削除等で current_page が現窓の外へ押し出された」を区別できない構造的問題。
  両者とも「current が window_start の窓外」という同一状態になり、D-11 は (B) で
  追従すべきと規定するが (A) では追従してはいけない。current=0（窓外）と
  current=5（窓外）は純関数では同一に見えるため片方温存・片方追従は原理的に不可能。
- **next_action:** ハンドラ層（viewer.py）を含む解決設計を確定する。有力候補:
  (1) 手動窓ナビ/件数変更ハンドラ側で current_page も新窓へ追従させ current を
  常に窓内に保つ → `_refresh_all` の追従は (B) のみに作用し矛盾が消える。
  (2) 明示的手動ナビでは正規化追従を抑止するフラグを導入。
  PageFolio の状態管理（selected_pages は全ページ index 不変、current_page は
  0 始まり）と D&D（local→global 換算）への整合性で評価して決める。

## Evidence

- timestamp: 2026-06-18T00:00:00 / source: pytest / `tests/test_pagination.py` 実行結果
  `2 failed, 66 passed`。失敗 2 件は矛盾する回帰テスト:
  - `test_manual_prev_window_not_snapped_back`: `reconcile_window_start(20, 0, 20, 47) == 20` 期待（current=0 が窓外でも温存）→ 実装は 0 を返す
  - `test_manual_next_window_not_snapped_back`: 同上
  一方 `test_current_outside_window_follows`: `reconcile_window_start(20, 5, 20, 47) == 0`（current=5 も同じ窓外だが追従を期待）。
- timestamp: 2026-06-18T00:00:00 / source: source / `pagefolio/pagination.py:73-94`
  `reconcile_window_start` は normalized 窓 [lo,hi) の外に current があれば
  無条件で `window_for_page(current_page)` へ追従する。current=0 と current=5 を
  区別する情報を持たない。
- timestamp: 2026-06-18T00:00:00 / source: source / `pagefolio/viewer.py:188-202`
  `_prev_window` / `_next_window` は `window_start` だけを移動し `current_page` を
  更新しない。このため移動後 current が窓外になり `_refresh_all` の追従で戻される。
- timestamp: 2026-06-18T00:00:00 / source: source / `pagefolio/viewer.py:167-186`
  `_on_page_size_change` は `window_for_page(current_page)` で窓を current へ
  追従させており、件数変更では current は常に窓内（snap back 問題は主にナビ起因）。
- timestamp: 2026-06-18T00:00:00 / source: doc / `02-RESEARCH.md:21`（D-11 原文）
  「表示窓は current_page を含む窓へ自動追従。current_page が表示窓外へ出たら、
  その窓へ自動切替。」 ← (B) のシナリオを規定。手動ナビ (A) は別。

## Resolution

**根本原因（確定）:** 純関数 `reconcile_window_start(window_start, current_page,
page_size, n_pages)` は引数だけでは「(A) 手動 ◀▶ で意図的に current から離れた窓へ
移動」と「(B) 削除等で current が現窓の外へ押し出された」を区別できない構造的問題。
両者とも「current が窓外」へ帰着し、`current=0` と `current=5`（いずれも窓 [0,20) 在・
`window_start=20` の窓外）は純関数には同一に見える。矛盾する回帰テスト 2 件
（`test_manual_prev/next_window_not_snapped_back`）はこれを純関数単独で解こうとした帰結。

**採用設計（候補1）:** 区別はハンドラ層の不変条件確立で担保する。
`pagefolio/viewer.py` の `_prev_window`/`_next_window` を共通 `_move_window(direction)`
へ集約し、**窓移動後に `current_page` を新窓先頭（`= _page_window_start`）へ追従**させ、
「current は常に窓内」を確立。これにより `reconcile_window_start` は (B) 押し出し専用の
追従関数として矛盾なく機能する。`_move_window` は既存ナビ作法に合わせ
`on_page_change` 発火・`window_label` を `_set_status` 表示。`_on_page_size_change` は
従来どおり `window_for_page(current_page)` で current を窓内に保つため整合済み。
`selected_pages`（全ページ index 不変・D-07）/ D&D（local→global・D-06）に影響なし。
フラグ方式（候補2）より集約点の純粋性を保てるため不採用。

**テスト対応:**
- 矛盾する回帰テスト 2 件を削除（`_move_window` 経由では到達不能な仕様外入力のため）。
- 純関数テスト `TestReconcileWindowStart` の docstring を (B) 専用追従仕様へ修正。
- ハンドラ統合テスト `TestMoveWindowHandler` を新設（窓移動後に `current_page` が
  新窓内＝`_page_window_start` へ追従すること・`on_page_change` 発火・doc 未開 no-op を検証）。

**検証結果:** `ruff check . && ruff format .` クリーン / `pytest` **564 passed**
（旧 561 = 559 passed + 2 failed → 矛盾 2 件削除・新規 5 件追加で 564）。

**変更ファイル:** `pagefolio/viewer.py` / `tests/test_pagination.py` /
本セッションファイル。`pagefolio/pagination.py` の `reconcile_window_start` 実装は
そのまま (B) 専用追従として保持（変更なし）。
