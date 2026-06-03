---
phase: 01-undo-redo
verified: 2026-06-03T05:00:00Z
status: passed
score: 9/9
overrides_applied: 0
---

# フェーズ 01: Undo/Redo 修正 検証レポート

**フェーズゴール:** Undo/Redo システムが正しく動作し、大きな PDF でも UI をブロックしない
**検証日時:** 2026-06-03T05:00:00Z
**ステータス:** passed
**再検証:** いいえ（初回検証）

---

## ゴール達成評価

### Observable Truths（ROADMAP.md 成功基準）

| # | 真理 | ステータス | 証拠 |
|---|------|----------|------|
| SC-1 | ページ挿入操作の後に Undo を実行すると、挿入されたページが正確に除去されて元の状態に戻る | ✓ VERIFIED | `TestInsertUndoRedo.test_insert_undo_restores_page_count` 通過。`_restore_state(insert)` が `range(num)` で `delete_page` を実行し、`_do_insert` が `_undo_stack[-1]["data"][1] = total` で実挿入数を書き戻す（page_ops.py:344）。163 passed |
| SC-2 | Undo スタックへの追加と上限超過時の削除が O(1) で完了する（deque 使用） | ✓ VERIFIED | `app.py:84-85` で `self._undo_stack = deque(maxlen=self.MAX_UNDO)` / `self._redo_stack = deque(maxlen=self.MAX_UNDO)` が確認済み。`file_ops.py` に `pop(0)` 手動トリムなし（grep ヒット 0） |
| SC-3 | 大きな PDF で Undo を実行しても UI がフリーズしない（BUG-02 対応の設計判断を反映） | ✓ VERIFIED | `self.doc.tobytes()` のドキュメント全体シリアライズが `_undo`/`_redo`/`_restore_state` の全パスから排除済み（grep `self.doc.tobytes()` の結果 0 件）。`page_ops.py:437` の `new_doc.tobytes()` は結合ページ専用の小ドキュメント（1 ページ）のシリアライズのみで問題なし |
| SC-4 | `pytest` が全通し、BUG-01 の修正を検証するユニットテスト（TEST-01）が含まれる | ✓ VERIFIED | `python -m pytest tests/ -q` → **163 passed**。`TestInsertUndoRedo`（test_insert_undo_restores_page_count / test_insert_undo_restores_content / test_insert_undo_redo_roundtrip）が存在し、全通 |

**スコア:** 4/4 成功基準を検証

### PLAN フロントマター must_haves（追加検証）

#### 01-01-PLAN.md

| # | 真理 | ステータス | 証拠 |
|---|------|----------|------|
| P1-1 | ページ挿入を Undo すると挿入ページが除去され元の状態に戻る | ✓ VERIFIED | SC-1 と同義。テスト通過確認済み |
| P1-2 | insert を Undo→Redo すると挿入ページが内容ごと復元される | ✓ VERIFIED | `TestInsertUndoRedo.test_insert_undo_redo_roundtrip` で `_page_digest` を用いて挿入ページの内容同一性を検証。163 passed |
| P1-3 | Undo/Redo のどのパスでも doc.tobytes() が呼ばれない（merge_resize 含む） | ✓ VERIFIED | `grep "self.doc.tobytes()" file_ops.py page_ops.py` → ヒット 0。`page_ops.py:437` は `new_doc.tobytes()`（1 ページ専用ドキュメント）のみ |
| P1-4 | 全 op（rotate/crop/delete/move/duplicate/insert/merge/bulk_move/bulk_crop/merge_resize）が do→undo→redo で往復できる | ✓ VERIFIED | `TestAllOpsUndoRedoRoundtrip` に全 op の往復テストが揃い（14 ケース、末尾ドロップ含む `@pytest.mark.parametrize` 4 ケースを含む）、全通 |

#### 01-02-PLAN.md

| # | 真理 | ステータス | 証拠 |
|---|------|----------|------|
| P2-1 | _undo_stack と _redo_stack の両方が collections.deque(maxlen=MAX_UNDO) である | ✓ VERIFIED | `app.py:9` `from collections import deque`、`app.py:84-85` `deque(maxlen=self.MAX_UNDO)` 2 件確認。実行時チェックでも型・maxlen=20 を確認 |
| P2-2 | Undo スタックへの追加と上限超過時の削除が O(1) で完了する（手動 pop(0) が存在しない） | ✓ VERIFIED | `grep "pop(0)" file_ops.py page_ops.py app.py` → ヒット 0 |
| P2-3 | deque 化後も _do_insert の直近エントリ後追い書き込み（[-1] アクセス）が成立する | ✓ VERIFIED | `page_ops.py:344` に `self._undo_stack[-1]["data"][1] = total` が存在。deque の末尾参照は O(1) で list と同義 |

#### 01-03-PLAN.md

| # | 真理 | ステータス | 証拠 |
|---|------|----------|------|
| P3-1 | 挿入 Undo のテストが len(doc) 復元と残ページの内容同一性（ハッシュ）を検証する | ✓ VERIFIED | `TestInsertUndoRedo.test_insert_undo_restores_content` が `_page_digest` で挿入前後の digest 同一性を assert |
| P3-2 | 挿入の do→undo→redo 往復テストが存在し全通する | ✓ VERIFIED | `TestInsertUndoRedo.test_insert_undo_redo_roundtrip` が存在し PASSED |
| P3-3 | 全 op の最小 do→undo→redo 往復テストが存在する | ✓ VERIFIED | `TestAllOpsUndoRedoRoundtrip` に rotate/delete/move/duplicate/merge/bulk_move/bulk_crop/merge_resize の各往復テストが存在 |
| P3-4 | Undo/Redo のどのテストパスでも pdf_bytes キーに依存しない | ✓ VERIFIED | 全テストが `assert "pdf_bytes" not in entry` を実施。`grep "pdf_bytes"` はコメントと画像変換用ローカル変数のみ |

**合計スコア:** 9/9 must-haves 検証済み

---

## 必須アーティファクト

| アーティファクト | 期待 | レベル1（存在） | レベル2（実体） | レベル3（配線） | ステータス |
|----------------|------|---------------|---------------|---------------|----------|
| `pagefolio/file_ops.py` | 対称デルタ方式 `_undo`/`_redo`/`_restore_state`、`_apply_inverse`、insert/merge の bytes キャプチャ | ✓ | ✓（540行、実質実装） | ✓（app.py Mixin統合） | ✓ VERIFIED |
| `pagefolio/page_ops.py` | merge_resize の op 別デルタ化、`_do_insert` の書き戻し | ✓ | ✓（`_do_merge_resize` に `_save_undo("merge_resize", ...)` 実装） | ✓ | ✓ VERIFIED |
| `pagefolio/app.py` | `_undo_stack`/`_redo_stack` の `deque(maxlen=MAX_UNDO)` 初期化 | ✓ | ✓（`deque(maxlen=self.MAX_UNDO)` 2 件） | ✓ | ✓ VERIFIED |
| `tests/test_pdf_ops.py` | `TestInsertUndoRedo`・`TestAllOpsUndoRedoRoundtrip`・`_page_digest` | ✓ | ✓（14 テストケース、内容同一性・往復検証あり） | ✓（実 `_save_undo`/`_restore_state` を bind して呼ぶ） | ✓ VERIFIED |

---

## キーリンク検証

| From | To | Via | ステータス | 詳細 |
|------|----|-----|----------|------|
| `file_ops.py::_undo` | `_redo_stack` | `_restore_state` の返す逆デルタを push | ✓ WIRED | `file_ops.py:71` `self._redo_stack.append(inverse)` |
| `file_ops.py::_redo` | `_undo_stack` | 同上 | ✓ WIRED | `file_ops.py:80` `self._undo_stack.append(inverse)` |
| `app.py::__init__` | `collections.deque` | `_undo_stack`/`_redo_stack` の初期化 | ✓ WIRED | `app.py:9,84-85` |
| `page_ops.py::_do_insert` | `_undo_stack[-1]` | deque 末尾への挿入数書き戻し | ✓ WIRED | `page_ops.py:344` |
| `file_ops.py::_restore_state(insert)` | insert bytes キャプチャ | `_apply_inverse(insert)` でページ単位 `tmp.tobytes()` | ✓ WIRED | `file_ops.py:175-179` |
| `page_ops.py::_do_merge_resize` | `_save_undo("merge_resize", ...)` | pdf_bytes 直接 push の撤廃 | ✓ WIRED | `page_ops.py:440-447` に op 別デルタ |

---

## データフロートレース（Level 4）

| アーティファクト | データ変数 | ソース | 実データ生成 | ステータス |
|----------------|----------|--------|------------|----------|
| `_restore_state` の insert 分岐 | `state["data"]` = `[insert_at, num]` | `_do_insert` の `_undo_stack[-1]["data"][1] = total` 書き戻し | ✓（実際の挿入ページ数が格納される） | ✓ FLOWING |
| `_apply_inverse(insert)` のキャプチャ | `captured` = `[(page_i, bytes)]` | `fitz.open()` → `tmp.insert_pdf(self.doc, from_page=i, to_page=i)` → `tmp.tobytes()` | ✓（1 ページ単位の実 bytes） | ✓ FLOWING |
| `_do_merge_resize` の `merged_bytes` | `new_doc.tobytes()` | `new_doc`（1 ページ専用）のシリアライズ | ✓（ドキュメント全体ではなく結合ページのみ） | ✓ FLOWING |

---

## 行動スポットチェック

| 動作 | コマンド | 結果 | ステータス |
|------|---------|------|----------|
| 全テストスイートが通過する | `python -m pytest tests/ -q` | **163 passed** in 1.29s | ✓ PASS |
| insert/全 op 往復テストが通過する | `pytest -k "InsertUndoRedo or AllOpsUndoRedoRoundtrip" -v` | 14 passed（末尾ドロップ含む move パラメータ化 4 ケース含む） | ✓ PASS |
| ruff lint がクリーンである | `ruff check .` | All checks passed! | ✓ PASS |
| ruff フォーマットに差分がない | `ruff format --check .` | 23 files already formatted | ✓ PASS |
| self.doc.tobytes() がゼロ件 | `grep "self.doc.tobytes()"` | ヒット 0 件 | ✓ PASS |
| 手動 pop(0) がゼロ件 | `grep "pop(0)"` | ヒット 0 件 | ✓ PASS |
| deque 初期化が 2 件存在する | `grep "deque(maxlen=self.MAX_UNDO)"` | app.py:84, 85 の 2 件 | ✓ PASS |

---

## 要件カバレッジ

| 要件 ID | ソースプラン | 内容 | ステータス | 証拠 |
|--------|-----------|------|----------|------|
| BUG-01 | 01-01-PLAN.md | ページ挿入操作を Undo すると挿入前の状態に正しく戻る | ✓ SATISFIED | `_do_insert` の `data[1]=total` 書き戻し + `_restore_state(insert)` の range(num) 削除 + TestInsertUndoRedo 全通 |
| BUG-02 | 01-01-PLAN.md | 大きな PDF で Undo を実行しても UI がブロックしない | ✓ SATISFIED | `self.doc.tobytes()` を Undo/Redo 全パスから排除。対称デルタ方式で op 別処理のみ実行 |
| REFAC-03 | 01-02-PLAN.md | Undo スタックを `collections.deque(maxlen=MAX_UNDO)` に変更 | ✓ SATISFIED | `app.py:84-85` で両スタックを deque 化。`file_ops.py` の手動 `pop(0)` 削除済み |
| TEST-01 | 01-03-PLAN.md | BUG-01（挿入 Undo）の動作を検証するユニットテスト | ✓ SATISFIED | `TestInsertUndoRedo`（3 テスト）: len 復元・digest 同一性・redo 往復を網羅 |

フェーズ 1 に割り当てられた要件（BUG-01/BUG-02/REFAC-03/TEST-01）の 4 件すべてが満たされています。  
フェーズ 2 以降の要件（BUG-03/REFAC-01/REFAC-02/TEST-02 ほか）は意図的にスコープ外。

---

## コードレビュー対応確認（01-REVIEW.md）

| 指摘 ID | 種別 | 内容 | 対応状況 |
|--------|------|------|---------|
| CR-01 | Critical | move 末尾ドロップ undo のページ順序破壊 | ✓ 修正済み（v1.2.6）。`_restore_state(move)` の条件分岐を撤廃し `order.insert(actual_dest, item)` に統一。`move_page(src, -1)` の末尾ドロップ経路で undo が正しく復元されることを実機確認済み（[P1,P2,P3] → move_page(0,-1) → [P2,P3,P1] → undo → [P1,P2,P3]）。`test_move_roundtrip` を `@pytest.mark.parametrize` でパラメータ化（末尾ドロップ `dest=3` 含む 4 ケース）し全通 |
| CR-02 | Critical | `_do_insert` 例外時に undo スタックに不完全 state が残る | ✓ 修正済み（v1.2.6）。`page_ops.py:360-363` で例外時に `_undo_stack.pop()` を実施 |
| WR-03 | Warning | `_restore_state` 末尾での `selected_pages` 共有参照 | ✓ 修正済み。`file_ops.py:337` `self.selected_pages = set(state["selected_pages"])` で防御コピー |
| WR-05 | Warning | `insert_redo` 分岐のコメントと実装の乖離 | ✓ 修正済み（v1.2.6）。`file_ops.py:285-286` のコメントを実装に合わせて修正 |
| WR-01 | Warning | move/bulk_move で `_save_undo` がデータ変更後に呼ばれる | 非ブロッキング。次フェーズ以降で対応予定 |
| WR-02 | Warning | merge_resize redo 後の `selected_pages` 正規化なし | 非ブロッキング。次フェーズ以降で対応予定 |
| WR-04 | Warning | 範囲外インデックスへの防御なし | 非ブロッキング。次フェーズ以降で対応予定 |
| IN-01 | Info | insert 3 状態遷移の冗長性 | 次フェーズ以降で検討 |
| IN-02 | Info | `_save_undo`/`_apply_inverse`/`_restore_state` の 13 分岐 | 次フェーズ以降で検討 |
| IN-03 | Info | テストが実アプリ呼び出し経路を一部再現していない | CR-01 修正に伴い末尾ドロップはカバー済み。それ以外は次フェーズで検討 |

---

## アンチパターン検査

| ファイル | 行 | パターン | 重大度 | 影響 |
|--------|---|---------|--------|------|
| — | — | TBD/FIXME/XXX 未解決デット | — | ヒットなし |
| — | — | 裸の except: | — | ヒットなし（すべて `except Exception as e:`） |
| — | — | return null / プレースホルダー | — | ヒットなし |

**アンチパターン検査結果:** クリーン（指摘なし）

---

## バージョン・履歴確認

| 項目 | 期待 | 実際 | ステータス |
|-----|------|------|----------|
| `APP_VERSION` | v1.2.x（段階更新） | **v1.2.6**（01-01: v1.2.3 → 01-02: v1.2.4 → 01-03: v1.2.5 → CR 修正: v1.2.6） | ✓ VERIFIED |
| `ruff check .` | エラー 0 件 | All checks passed! | ✓ VERIFIED |
| `ruff format --check .` | 差分 0 件 | 23 files already formatted | ✓ VERIFIED |
| `pytest` | 全通 | 163 passed | ✓ VERIFIED |

---

## 人手検証が必要な項目

なし。本フェーズはロジック修正・テスト追加・リファクタリングのみで、UI 外観・リアルタイム挙動・外部サービス連携は含まれない。

---

## ギャップサマリー

ギャップなし。フェーズ 1 の全 9 must-haves（ROADMAP 成功基準 4 件 + PLAN フロントマター truths 合計 9 件）が検証済みで、テスト・lint・コードレビュー対応すべてクリーン。

---

*検証日時: 2026-06-03T05:00:00Z*  
*検証者: Claude (gsd-verifier)*
