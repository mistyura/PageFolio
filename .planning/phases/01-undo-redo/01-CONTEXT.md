# Phase 1: Undo/Redo 修正 - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Undo/Redo システムの「正確性」と「大きな PDF でのパフォーマンス」を担保する。
スコープは **BUG-01 / BUG-02 / REFAC-03 / TEST-01** のみ。

- BUG-01: ページ挿入操作を Undo すると挿入前の状態に正しく戻る
- BUG-02: 大きな PDF で Undo/Redo を実行しても UI がブロックしない
- REFAC-03: Undo/Redo スタックを `collections.deque(maxlen=MAX_UNDO)` 化
- TEST-01: 挿入 Undo の動作を検証するユニットテスト

新機能追加・プレビュー最適化（BUG-03）・dialogs/constants 分割（REFAC-01/02）・settings 公開 API 化（REFAC-04）は別フェーズ。

</domain>

<decisions>
## Implementation Decisions

### BUG-02: シリアライズ排除の設計方針
- **D-01:** 巻き戻し時の `doc.tobytes()` を **逆操作デルタ方式**で排除する。`_undo()` は `_redo_stack` へ、`_redo()` は `_undo_stack` へ、「フル PDF」ではなく「いま実行する逆操作のデルタ」を積む。順方向 `_save_undo` と同じデルタ機構で対称化し、`tobytes()` を完全に排除する。
- **D-02:** 背景スレッドでの `tobytes()` は採用しない（fitz は `Document` をスレッド間で共有できず、データ競合・クラッシュのリスクが高いため）。
- **D-03:** 元ファイルからの順方向全再適用方式も採用しない（操作数増加で遅くなりうるため）。

### 対称化のリファクタ範囲
- **D-04:** **全 op を完全対称化**する。`rotate`/`crop`/`move`/`bulk_move`/`bulk_crop`/`duplicate` は逆デルタが容易。`insert`/`merge`/`delete` のページ増減系は、巻き戻し（削除）時に **削除するページの bytes をキャプチャ**して redo 用デルタに保持する（`delete` は既に bytes 保持済み、`insert`/`merge` は現状カウントのみなので拡張が必要）。
- **D-05:** `_restore_state` の `pdf_bytes` 分岐は**撤廃**し、全パスで `tobytes()` を排除する。成功基準#3「大きな PDF で Undo してもフリーズしない」を全操作で満たす。

### REFAC-03: deque maxlen の適用範囲
- **D-06:** `_undo_stack` / `_redo_stack` の**両方**を `collections.deque(maxlen=MAX_UNDO)` 化する。メモリ上限を明確化し挙動を一貫させる。redo サイズは undo 回数で決まり通常 MAX_UNDO を超えないため実害なし。

### TEST-01: 検証深度
- **D-07:** 挿入 Undo のテストは **ページ数＋内容同一性**を検証する。挿入→Undo 後に `len(doc)` が元に戻ることに加え、残ったページの同一性（テキストまたはレンダリング/バイトのハッシュ）を確認。**redo 往復**（do→undo→redo）も含める。

### Claude's Discretion
- 各 op の逆デルタの具体的なデータ構造・キャプチャ実装は planner/executor の裁量。
- ハッシュ方式（テキスト抽出 vs pixmap バイト vs page bytes）の選択は planner 裁量。
- `insert`/`merge` の redo 用 bytes キャプチャの具体実装（巻き戻し直前にキャプチャ vs 順方向時に保持）は planner 裁量。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・トレーサビリティ
- `.planning/REQUIREMENTS.md` — BUG-01/BUG-02/REFAC-03/TEST-01 の定義と対象行
- `.planning/ROADMAP.md` §Phase 1 — ゴールと成功基準（4 項目）
- `.planning/PROJECT.md` §Key Decisions — BUG-02 の方針（本 CONTEXT で「逆操作デルタ方式」に確定、PROJECT.md 上は「ページ単位キャッシュ方式・検討中」だった仮置きを上書き）

### 対象コード
- `pagefolio/file_ops.py` §`_save_undo`/`_undo`/`_redo`/`_restore_state`（lines 23–143）— Undo/Redo の中核。`_undo:68` と `_redo:84` の `doc.tobytes()` が BUG-02 の原因。`_restore_state:96` の `pdf_bytes` 分岐が撤廃対象。
- `pagefolio/page_ops.py` §`_do_insert`（lines 332–355）— BUG-01 の挿入実行。`:334` `_save_undo("insert", insert_at=...)`、`:344` `self._undo_stack[-1]["data"][1] = total` で挿入数を書き戻している（`[-1]` アクセスは deque でも O(1)）。
- `pagefolio/app.py` §`MAX_UNDO` 定義・`_undo_stack`/`_redo_stack` 初期化 — REFAC-03 の変更点。

### コードベースマップ
- `.planning/codebase/CONCERNS.md` — 既知の懸念点
- `.planning/codebase/ARCHITECTURE.md` §State Management / Threading — fitz スレッドセーフ制約・Undo limit の記述

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_save_undo(op, **kwargs)`: 既に op 別デルタを保存する分岐構造を持つ。逆デルタ対称化はこの分岐を `_restore_state` 側と対にして拡張すればよい。
- `delete` op のページ bytes キャプチャパターン（`file_ops.py:41-44`、`tmp.insert_pdf` + `tmp.tobytes()`）は、`insert`/`merge` の redo 用 bytes キャプチャにそのまま流用できる。
- `_restore_state` の op 別復元分岐（`file_ops.py:103-136`）— 逆操作の実装場所。

### Established Patterns
- 状態復元後は必ず `_invalidate_thumb_cache()` → `_preview_gen += 1` → `_thumb_gen += 1` → `_refresh_all()` を呼ぶ（`_restore_state:140-143`）。逆デルタ化後もこの後処理は維持する。
- op 別 `state` 辞書（`op`/`current_page`/`selected_pages`/`data`）が Undo エントリの共通スキーマ。redo エントリも同一スキーマに揃えると対称化が自然。

### Integration Points
- `page_ops.py:344` の `_undo_stack[-1]["data"][1] = total` は deque 化後も動作するが、deque への移行時に「直近 push したエントリへの後追い書き込み」が成立することを確認する。
- `MAX_UNDO` は `app.py` でハードコード定義（ARCHITECTURE.md 記載）。deque(maxlen=MAX_UNDO) 化で `_save_undo:59-60` の手動 `pop(0)` トリム処理は不要になり削除できる。

</code_context>

<specifics>
## Specific Ideas

- 設計の核心は「順方向も巻き戻しも同じデルタ機構を使う対称設計」。`pdf_bytes` を一切持たない状態をゴールとする。

</specifics>

<deferred>
## Deferred Ideas

- BUG-03（プレビュー生成のフルシリアライズ廃止 → `page.get_pixmap()` 直接呼び出し）— Phase 2
- REFAC-01（dialogs サブパッケージ分割）/ REFAC-02（constants 分割）— Phase 2
- REFAC-04（settings 公開 API 化）/ TEST-03（import 回帰テスト）— Phase 3
- **全 op 往復テストの網羅**: 「全 op 完全対称化」は全操作のコードに触れるため、TEST-01（挿入中心）の安全網として rotate/delete/move/merge/bulk 系の最小 do→undo→redo 往復テスト追加を planner が検討すること（リスク低減策。TEST-01 のスコープを超える場合は Phase 1 内の追加テストとして扱うか判断）。

</deferred>

---

*Phase: 1-Undo/Redo 修正*
*Context gathered: 2026-06-03*
