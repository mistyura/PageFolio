# Phase 2: 大量ページのページネーション表示 - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

大量ページの PDF でもサムネイル一覧をページ単位（既定 20 件）で区切って高速に表示し、**ページング表示中でも D&D 並び替え・複数選択・ページ操作が全ページインデックスと整合する**ようにする。要件は V16-UI-03（S3）。

**核心リスク:** 現状 `_build_thumbnails` は `range(len(self.doc))` で全ページを描画しており、「サムネイルの並び位置 = 全ページインデックス」という暗黙の前提で `selected_pages`・D&D（`_dnd_dest_index` / `_refresh_thumbs_selection_only` の `enumerate`）が成立している。窓表示にすると並び位置がローカル化するため、**「表示窓のローカル位置 ↔ 全ページインデックス」の変換層**を導入することが本フェーズの中核作業となる。

**スコープ外:** 新しいページ操作機能の追加、サムネイル仮想化（描画自体の遅延ロード基盤）の本格導入、UI/UX デザインの刷新。本フェーズは「窓で区切る表示」と「全ページインデックス整合」に集中する。

対象要件: V16-UI-03（大量ページのページネーション表示）

</domain>

<decisions>
## Implementation Decisions

### ページ窓のナビゲーション UI（領域1）
- **D-01:** 窓の移動手段は **前/次窓ボタン（◀ ▶）＋「1–20 / 全120」形式の範囲ラベル**とする。プレビューツールバーの前/次ページボタン UI と一貫させ、実装も軽い。ページ番号ジャンプ入力やドロップダウン選択は採用しない（最小実装）。
- **D-02:** ナビゲーションコントロールの配置は **サムネイル canvas の下（フッター）に独立行**とする。サムネイル一覧を見ながら窓を送れる位置。Phase 1 で整理した `_build_thumb_panel`（ヘッダ → 全選択/解除行 → ズームスライダー独立行 → canvas）の **canvas より下**に新規フッター行を `pack(fill="x")` で追加する。

### 表示件数（ページサイズ）の変更 UI と既定値（領域2）
- **D-03:** 表示件数の変更 UI は **フッターのナビ行に置く Spinbox（「表示: [20]件」等）**とする。窓ナビと近接させ、その場で調整 → 即再描画できる発見性を優先。設定ダイアログへの集約は採らない。
- **D-04:** 表示件数の **既定値は 20（ロードマップ確定）、許容範囲は 10〜100**。下限 10 で 2 桁を保ち、上限 100 で低スペック PC の描画負荷を抑える。
- **D-05:** 表示件数は **`pagefolio_settings.json` に永続化**し、次回起動時に復元する。`_save_settings()` 経由で保存（既存のサムネイルズーム永続化と同じ作法）。永続化キー名は既存命名規約に倣う（例: `thumb_page_size`。最終名は実装裁量）。

### D&D・複数選択のクロス窓スコープ（領域3・インデックス整合の核心）
- **D-06:** **D&D 並び替えは表示中の窓内に限定**する。クロス窓 D&D（別窓へドラッグして移動）は採らない（Tkinter で表示外ページへのドロップ先指示が困難・高リスク）。ドロップ位置はローカル位置として受け取り、**全ページインデックスへ変換してから** `move_page` / `bulk_move` を適用する。`_dnd_dest_index` が返すフレーム位置はローカルなので `global = local_pos + page_offset` で換算する。
- **D-07:** **複数選択（`selected_pages`）は窓をまたいで保持**する。`selected_pages` は従来どおり**全ページインデックス**を保持し、別窓へ移動しても選択状態を維持する。ページ操作（削除・回転・bulk_move 等）は選択どおり全ページに適用される。成功基準 4 の意図に合致。
- **D-08:** **「全選択 / 全解除」ボタンは全ドキュメント対象**（既存 `_select_all` / `_deselect_all` の挙動を踏襲）。表示窓内のみの選択には限定しない。D-07 の窓またぎ保持と整合する。

### ページング適用のしきい値・端数・窓追従（領域4）
- **D-09:** **ページ数が表示件数以下でも常にナビを表示**する（単一窓・前/次ボタンは disabled）。「1–8 / 全8」のように表示し、UI のレイアウトを一定に保つ。件数超過時のみナビを出す方式（出たり消えたりでレイアウトが揺れる）は採らない。
- **D-10:** 端数の最終窓は実ページ数までで表示（例: 件数 20・全 47 ページなら最終窓は「41–47 / 全47」）。
- **D-11:** **表示窓は `current_page` を含む窓へ自動追従**する。プレビューの前/次ページ・D&D・削除などで `current_page` が表示窓外へ出たら、その `current_page` を含む窓へ自動的に切り替える。選択/カレントが常に視認できる状態を保つ。

### Claude's Discretion
- 永続化キー名（D-05）は既存命名規約に倣って実装時に確定してよい（候補: `thumb_page_size`）。
- 窓オフセット状態を保持する属性名（例: `self._page_window_start` / `self._page_size`）は実装裁量。
- Spinbox の即時反映タイミング（値変更ごと / フォーカスアウト / `<<Increment>>`）は既存 UI の作法に合わせて選んでよい。ただし「変更が永続化され、再描画される」ことは必須（D-03/D-05）。
- 範囲ラベルの正確な文言・区切り記号（「1–20 / 全120」「1-20 / 120」等）は LANG 規約（ja/en 同一キー）に従い実装裁量。
- D&D ゴースト/インジケータのローカル↔グローバル変換の実装詳細は裁量。ただし「意図したページが正しい全ページ位置へ移動する」ことは必須（D-06）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・マイルストーン
- `.planning/ROADMAP.md` §"Phase 2: 大量ページのページネーション表示" — Goal と Success Criteria 4 項目
- `.planning/REQUIREMENTS.md` — V16-UI-03 の要件本文（既定 20 ページ単位・件数永続化・D&D/複数選択の全ページインデックス整合）
- `.planning/PROJECT.md` §"Current Milestone: v1.6.0" — S3 の Key context（「表示中ページ vs 全ページ」のインデックス整合に注意・表示件数は settings 永続化）

### 実装対象コード（本フェーズで編集する中核）
- `pagefolio/ui_builder.py` §`_build_thumb_panel`（173-239）— サムネイルパネル構成。ヘッダ（174-189）/ 全選択・解除行 `sel_frame`（191-198）/ ズームスライダー独立行 `zoom_frame`（200-211）/ canvas 群（213-239）。**新規ナビ/件数フッター行は canvas 群の後に追加**する。
- `pagefolio/viewer.py` §`_build_thumbnails`（197-225）— `range(len(self.doc))` で全ページ描画。**窓範囲 `[start, start+size)` のみ描画するよう変更**する中核。`_add_thumb_placeholder(i)`（227-287）は `i`（現状=全ページ index）を press/motion/release/double のクロージャに束縛 → 窓化で `i` を**全ページインデックスのまま**渡すか、ローカル↔グローバル変換を入れるか要設計。
- `pagefolio/viewer.py` §`_refresh_thumbs_selection_only`（174-195）— `enumerate(self.thumb_inner.winfo_children())` の位置 `i` を `selected_pages`（全ページ index）と直接照合。**窓化で `global = local + offset` 変換が必須**。
- `pagefolio/viewer.py` §選択ヘルパー `_toggle_select`（22-27）/ `_select_all`（29-33）/ `_deselect_all`（35-37）/ `_single_click`（296-301）— `selected_pages` は全ページ index 前提（D-07/D-08 で維持）。
- `pagefolio/dnd.py` §`_dnd_dest_index`（73-92）/ `_dnd_drop`（94-135）/ `_dnd_show_indicator`（47-66）— ドロップ先はフレーム位置（**窓化でローカル**になる）。`_dnd_drop` の `src`（`_dnd_src_idx`）と `dest` を**全ページインデックスへ変換**してから `move_page` / `doc.select(new_order)` を呼ぶよう改修。`bulk_move`（101-117）は `selected_pages` 全体（全ページ）で計算するため整合確認が必要。
- `pagefolio/settings.py` §`DEFAULT_SETTINGS`（45-76 付近）— 表示件数の既定値（20）と永続化キーを追加する先。`thumb_zoom` 等と同様の数値設定として追加。
- `pagefolio/viewer.py` §`_on_thumb_zoom_release`（146-154）— 設定保存＋`_invalidate_thumb_cache`＋`_refresh_all` のパターン。件数変更ハンドラはこれを参考にする。

### 関連経緯
- `.planning/phases/01-ui-ocr/01-CONTEXT.md` — Phase 1 でスライダーを独立全幅行へ移設済み（`_build_thumb_panel` の pack 構造）。本フェーズのフッター追加はこの構造の続き。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_build_thumb_panel` の pack 構造**: Phase 1 でヘッダ→全選択行→ズーム行→canvas の独立行構成に整理済み。canvas 群の後に新規 `tk.Frame`（ナビ＋件数フッター）を `pack(fill="x")` で足すだけで D-01/D-02/D-03 のレイアウトを満たせる。
- **`_on_thumb_zoom_release` の保存→無効化→再描画パターン**: 「設定変更 → `_save_settings` → `_invalidate_thumb_cache` → `_refresh_all`」の定石が既にある。件数変更・窓移動ハンドラはこれを踏襲できる。
- **`_refresh_thumbs_selection_only`（画像再生成なしの選択再描画）**: 窓内の選択ハイライト更新に流用できるが、`enumerate` 位置を全ページ index へ変換する一点の改修が要る。
- **`bulk_move` ロジック（`_dnd_drop` 101-117）**: `selected_pages`（全ページ）と `non_selected` から `new_order` を組む処理は全ページ前提で既に正しい。窓化しても選択が全ページ index を保つ（D-07）限り再利用できる。
- **テーマ辞書 `C` / `self._font()` / LANG（ja/en）規約**: 新規ウィジェット・文言も既存規約に従う。

### Established Patterns
- サムネイル描画は `_thumb_gen` 世代カウンタ＋`root.after` チェーンの逐次レンダリング。窓化では描画対象を窓範囲に絞るだけで、世代ガードの枠組みは維持できる（描画件数が減るぶん高速化＝本フェーズの目的に合致）。
- 設定永続化は `_save_settings()` → `pagefolio_settings.json`。`DEFAULT_SETTINGS` に既定を持たせ `self.settings.get(key, default)` で読む。
- `selected_pages` は一貫して**全ページ 0 始まり index の set**。ページ操作（page_ops.py）もこれを sorted して使う（`selected_pages` → 597/776/785 付近）。この不変条件を窓化後も保つことが整合の鍵。

### Integration Points
- **窓状態の単一の真実**: 窓オフセット（start）と窓サイズ（page_size）を `self.*` 属性で一元管理し、`_build_thumbnails`・ナビ UI・`_refresh_thumbs_selection_only`・D&D 変換がすべてこの 2 値を参照する。`selected_pages` / `current_page` / `doc` の順序は従来どおり全ページ基準で不変。
- **ローカル↔グローバル変換は 1 箇所に集約**: `global = local + window_start` / `local = global - window_start` の変換ヘルパーを設け、サムネイル位置・D&D ドロップ先・選択ハイライト照合のすべてで使う（散在させない）。
- **件数/窓ナビ UI は `_build_thumb_panel` のフッター行追加に閉じる**。プレビュー側（preview canvas / current_page）への影響は D-11 の「窓追従」呼び出しのみ。

</code_context>

<specifics>
## Specific Ideas

- ナビは「◀ ▶ ＋ 1–20 / 全120」、件数 Spinbox はその同じフッター行に近接配置（窓を送りながら件数も触れる）。
- 単一窓でも「1–8 / 全8」を常に表示し、ボタンは無効化（レイアウトを揺らさない＝D-09）。
- 操作後に current_page が窓外へ出たら、その窓へ自動でジャンプして選択/カレントを見失わせない（D-11）。
- 「全選択」は全ドキュメント。大量ページでも一括選択 → 一括操作の従来ワークフローを壊さない。

</specifics>

<deferred>
## Deferred Ideas

- サムネイル仮想化（スクロール位置に応じた本格的な遅延ロード基盤）→ 本フェーズは「窓で区切る」最小実装に留める。仮想化はパフォーマンス改善の別タスク候補（PROJECT.md「Next Milestone Goals」に既出）。
- クロス窓 D&D（別窓へドラッグして移動）→ 高リスクのため不採用（D-06）。必要なら将来フェーズで「ジャンプ先指定移動」等の別 UX として検討。
- ページ番号ジャンプ入力 / 窓ドロップダウン選択 → 最小実装では不採用（D-01）。大量窓で不便なら将来の軽微拡張候補。
- 体感品質・回転プレビュー即時反映 / OCR 堅牢性（プランA）→ **Phase 3**。
- AI 出力品質（Markdown 整形・プロバイダ別プロンプト・プランC）→ **Phase 4**。

None outside scope beyond the above — discussion stayed within phase boundary.

</deferred>

---

*Phase: 2-大量ページのページネーション表示*
*Context gathered: 2026-06-18*
