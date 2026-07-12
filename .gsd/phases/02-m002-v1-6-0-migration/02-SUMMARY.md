---
id: S02
parent: M002
milestone: M002
provides:
  - pagefolio/pagination.py（Tk 非依存の窓計算・local↔global 変換・件数クランプ純関数 8 個）
  - tests/test_pagination.py（境界値・往復不変・D&D 換算・窓またぎ選択照合の named テスト 47 件）
  - tests/conftest.py large_pdf_doc フィクスチャ（47 ページ）
  - settings.py DEFAULT_SETTINGS の thumb_page_size（既定 20・範囲 10〜100・後方互換 setdefault）
  - app.py 窓状態の単一の真実 self._page_window_start / self._page_size（settings からクランプ復元）
  - viewer.py 窓範囲 [lo, hi) 描画と to_global 経由の選択ハイライト照合（全ページ index 不変条件保持）
  - ui_builder.py ナビ/件数フッター行（◀ ▶ ＋ 範囲ラベル ＋ 件数 Spinbox state=readonly）
  - viewer.py 窓ナビ/件数変更ハンドラ・_refresh_all 窓正規化（reconcile_window_start 集約）
  - viewer.py _move_window 集約（窓移動後 current_page を新窓内へ追従・UAT 項目2 修正）
  - dnd.py D&D ドロップ先の local→global 換算（to_global・D-06）
  - lang.py 範囲ラベル/件数ラベルの ja/en 同一キー
  - pagination.py reconcile_window_start（描画前正規化 + D-11 条件付き追従の純関数）
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 
verification_result: passed
completed_at: 
blocker_discovered: false
---
# S02: Pagination

**# Phase 02 Plan 01: ページネーション純ロジック層 Summary**

## What Happened

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

# Phase 02 Plan 02: 窓状態の確立とサムネイル描画・選択照合の窓範囲化 Summary

ページネーションの「窓状態の単一の真実」（`self._page_window_start` / `self._page_size`）を `app.py __init__` に確立し、`viewer.py` のサムネイル描画と選択ハイライト照合を 02-01 の純関数層（`pagefolio.pagination`）経由で窓範囲化した。表示件数 `thumb_page_size` を `pagefolio_settings.json` に永続化（既定 20・範囲 10〜100）し、後方互換（setdefault）と値域クランプ（`clamp_page_size`）を担保した。`selected_pages` は全ページ index の不変条件を一切崩さず、照合側を `to_global` で変換することで窓またぎのハイライトずれ（Pitfall 1）を構造的に解消した。

## 実装内容

### Task 1: settings に thumb_page_size 既定 20 と clamp 読み出し結合（TDD）

- `pagefolio/settings.py` の `_load_settings` defaults dict に `"thumb_page_size": 20` を 1 行追加（既存 `ocr_scale` と同作法・D-04）。`setdefault` マージ機構（71-72 行）により旧設定ファイルでも 20 が補完され、既存ユーザー値は温存される（後方互換・移行コード不要）。新規キーは数値設定で `_SENSITIVE_KEYS` には追加しない。
- 件数クランプは 02-01 で `pagefolio/pagination.py` に確定済みの `clamp_page_size` を import 参照（W1）。settings.py に同等関数を別名/再定義していない（`grep -c 'def clamp_page_size' pagefolio/settings.py` == 0）。
- `tests/test_pagination.py` の `TestPageSizePersist` に settings 結合 assert を追記（monkeypatch で `_get_settings_path` を tmp_path へ差し替え）:
  - 設定ファイルなし時 `_load_settings()['thumb_page_size'] == 20`
  - 旧設定（キーなし）の setdefault 補完・既存 `theme`/`font_size` 温存
  - 既存 `thumb_page_size: 50` を clobber しない
  - `clamp_page_size(_load_settings()['thumb_page_size']) == 20`（settings → clamp 結合・W1）
  - 壊れた設定（9999）でも clamp 読み出しで 100 に倒れる
- TDD: RED で `KeyError: 'thumb_page_size'` を確認 → GREEN で defaults 追加し 13 件 green。

### Task 2: app.py 窓状態初期化 + viewer 描画・選択の窓範囲化

- `pagefolio/app.py` に `from pagefolio.pagination import clamp_page_size` を追加し、`__init__` の状態初期化ブロックに窓状態を追加:
  - `self._page_window_start = 0`（窓オフセット・既定 0）
  - `self._page_size = clamp_page_size(self.settings.get("thumb_page_size", 20))`（settings からクランプ復元・D-05・W1）
- `pagefolio/viewer.py` 冒頭に `from pagefolio.pagination import to_global, window_bounds` を追加。
- `_build_thumbnails`: `lo, hi = window_bounds(self._page_window_start, self._page_size, len(self.doc))` を取り、`placeholder_labels = [self._add_thumb_placeholder(i) for i in range(lo, hi)]`（`i` は全ページ index のまま＝D-06 src 整合）。`render_next` の起点を `lo`・終端を `i >= hi`・`placeholder_labels` 参照を窓ローカル添字 `i - lo` に変更。`_thumb_gen` 世代ガードは一切変更せず（Anti-Pattern「世代ガードを外さない」）。
- `_refresh_thumbs_selection_only`: 照合ループの enumerate 位置 `i` を `g = to_global(i, self._page_window_start)` で全ページ index へ変換し、`is_sel = g in self.selected_pages` / `is_cur = g == self.current_page`（Pitfall 1）。`selected_pages` 自体はローカル化しない（D-07 不変条件を絶対保持）。
- `thumb_cache` は窓移動でクリアしない（キーが全ページ index のため別窓と衝突しない・Pitfall 2・W3 非クリア自動検証に準拠）。`p.{i + 1}` のページ番号ラベルは全ページ index ベースのため改修不要（窓 2 でも実ページ番号を表示）。

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `pytest tests/test_pagination.py::TestPageSizePersist -x -q`: 13 passed
- `pytest tests/test_pagination.py tests/test_viewer.py -q`: 54 passed
- `pytest`（全スイート）: 545 passed（02-01 ベースライン 540 + 本プラン settings 結合 5 件・既存回帰なし）
- `ruff check .`: All checks passed!
- `ruff format --check .`: 41 files already formatted
- grep 受け入れ確認:
  - `grep -c 'window_bounds' pagefolio/viewer.py` == 2（import + 描画範囲）
  - `grep -c 'to_global' pagefolio/viewer.py` == 2（import + 選択照合）
  - `grep -c '_page_window_start' pagefolio/app.py` == 2
  - `grep -c 'def clamp_page_size' pagefolio/settings.py` == 0（別名定義なし・W1）
  - viewer.py / settings.py に裸 except なし

### 受け入れ基準の注記（`range(len(self.doc))`）

プランの受け入れ基準「`grep -c 'range(len(self.doc))' pagefolio/viewer.py` == 0」は、`_build_thumbnails` の全描画撤廃を意図したもの。`_build_thumbnails` からの当該パターンは完全に撤廃済み（`range(lo, hi)` へ置換）。ただし viewer.py 全体では `_select_all`（33 行）の `self.selected_pages = set(range(len(self.doc)))` が 1 件残存する。これは「全選択 = 全ページ index 集合」という D-07 不変条件に沿った**正しい意味論**であり、本プランの対象外（既存挙動・窓化と無関係）。`_build_thumbnails` の全描画撤廃という基準の意図は満たしている。

## 後続プランへの引き継ぎ

- 02-03 はナビフッター UI（◀ ▶ / 範囲ラベル / 件数 Spinbox）を実装し、`page_size_var`・LANG キー（ja/en 同一）を追加する。
- 窓ナビ操作（◀ ▶）は `clamp_window_start` / `window_for_page`（02-01）を使って `self._page_window_start` を更新し `_refresh_all()` を呼ぶ想定。窓状態属性は本プランで初期化済み。
- 件数 Spinbox の確定時は `clamp_page_size`（W1）で `self._page_size` を更新し、`thumb_page_size` を `_save_settings` で永続化する。Tk 値の空文字 TclError は 02-03 呼び出し側でハンドルする（純関数は Tk 非依存）。
- D&D ドロップ先の local→global 換算（`to_global` + 窓末尾 min クランプ）は 02-01 でテスト済み（`TestDndIndexConvert`）。dnd.py の窓化適用が後続で必要なら別プランで対応。

## Commits

- 0744cb5: feat(02-02) thumb_page_size 既定20を追加し件数読み出しをclamp_page_size結合に統一
- 989a08b: feat(02-02) 窓状態属性を初期化しサムネイル描画と選択照合を窓範囲化

## Self-Check: PASSED

- 変更ファイル全て存在: pagefolio/settings.py / pagefolio/app.py / pagefolio/viewer.py / tests/test_pagination.py / 02-02-SUMMARY.md
- コミット全て存在: 0744cb5 / 989a08b

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
