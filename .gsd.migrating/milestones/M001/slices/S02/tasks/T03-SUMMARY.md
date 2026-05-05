---
id: T03
parent: S02
milestone: M001
key_files:
  - pagefolio/viewer.py
key_decisions:
  - _add_thumb() は削除せず後方互換メソッドとして残し、_add_thumb_placeholder() を呼ぶ形にリファクタリングした（プラグインや外部コードからの参照を考慮）
  - render_next() 内の stale チェックでは logger.debug でスキップ理由（gen 値）を記録し、診断可能性を確保した
  - after(0, ...) で次フレームをスケジュールすることで Tk イベントループを1フレームずつ解放し UI 応答性を維持する
duration: 
verification_result: passed
completed_at: 2026-05-04T04:21:00.052Z
blocker_discovered: false
---

# T03: _build_thumbnails() を after_idle() プログレッシブローディングに改修し、大規模 PDF でのサムネイル生成時 UI フリーズを解消

**_build_thumbnails() を after_idle() プログレッシブローディングに改修し、大規模 PDF でのサムネイル生成時 UI フリーズを解消**

## What Happened

viewer.py の `_add_thumb()` を `_add_thumb_placeholder()` と `_add_thumb()` の2メソッドに分割した。`_add_thumb_placeholder(i)` はプレースホルダー Label（image なし）・ページ番号 Label・全イベントバインディングを作成して `(frame, lbl)` を返す。`_add_thumb()` は後方互換維持のため残し、内部で `_add_thumb_placeholder()` を呼んで即時レンダリングする形に変更した。

`_build_thumbnails()` は `_thumb_gen` をインクリメントして世代番号を確保し、全ページ分のプレースホルダーを即時作成してから `after_idle()` で `render_next(0)` をスケジュールする。`render_next(i)` は `_thumb_gen != gen` のとき（世代が古い）は `logger.debug` でスキップを記録して早期リターンする。各ページを1枚ずつ `_get_thumb_photo()` でレンダリングし、`lbl.configure(image=photo)` で差し込み、`thumb_images.append(photo)` で GC 防止参照を保持した後、`after(0, lambda: render_next(i + 1))` で次フレームをスケジュールする。これにより UI イベントループを占有せずにサムネイルを逐次描画できる。

ruff check → 行長エラー3件（docstring・リスト内包・logger.debug 呼び出し）を修正して全クリア。108 テストすべてパス。

## Verification

スライス検証コマンド `grep -c '_add_thumb_placeholder\|after_idle\|render_next' pagefolio/viewer.py` → 6（マッチ件数確認）。`ruff check . && ruff format .` → All checks passed! `pytest` → 108 passed in 1.10s。

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c '_add_thumb_placeholder|after_idle|render_next' pagefolio/viewer.py` | 0 | ✅ pass | 120ms |
| 2 | `ruff check . && ruff format .` | 0 | ✅ pass | 3200ms |
| 3 | `pytest --tb=short -q` | 0 | ✅ pass | 1100ms |

## Deviations

none

## Known Issues

none

## Files Created/Modified

- `pagefolio/viewer.py`
