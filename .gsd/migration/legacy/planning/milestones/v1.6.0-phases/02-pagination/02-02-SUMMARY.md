---
phase: 02-pagination
plan: 02
subsystem: pagination-window-render
tags: [pagination, window-state, thumbnails, selection, settings, tdd]
status: complete
requires:
  - 02-01
provides:
  - "settings.py DEFAULT_SETTINGS の thumb_page_size（既定 20・範囲 10〜100・後方互換 setdefault）"
  - "app.py 窓状態の単一の真実 self._page_window_start / self._page_size（settings からクランプ復元）"
  - "viewer.py 窓範囲 [lo, hi) 描画と to_global 経由の選択ハイライト照合（全ページ index 不変条件保持）"
affects:
  - "02-03（ナビフッター UI・件数 Spinbox・page_size_var・◀ ▶ で _page_window_start を更新）"
tech-stack:
  added: []
  patterns:
    - "窓ローカル↔全ページ index 変換を 02-01 pagination.py の純関数経由に統一（+ window_start 直書き禁止）"
    - "件数クランプは確定名 clamp_page_size を import 参照（W1・別名/再定義なし）"
    - "TDD（RED→GREEN）で settings 結合の境界値を先に固定"
key-files:
  created: []
  modified:
    - "pagefolio/settings.py"
    - "pagefolio/app.py"
    - "pagefolio/viewer.py"
    - "tests/test_pagination.py"
decisions:
  - "thumb_page_size を _load_settings defaults へ 1 行追加し setdefault で後方互換を担保（移行コード不要・D-04/D-05）"
  - "selected_pages はローカル化せず全ページ index の不変条件を絶対保持（D-07）。照合側を to_global で変換"
  - "thumb_cache は窓移動でクリアしない（キーが全ページ index のため別窓と衝突しない・Pitfall 2・W3）"
metrics:
  duration: 約 12 分
  completed: 2026-06-18
  tasks: 2
  files: 4
---

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
