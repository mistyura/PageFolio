# Phase 3: ページ操作磨き込み + v1.5.0 回帰テスト - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

ユーザーは画像（ロゴ）を透かしとしてページに追加でき（V171-PAGE-01・v1.5.0 テキストのみ制限の解除）、黒塗り/モザイク（V171-PAGE-02）と回転/トリミング（V171-PAGE-03）が本 discuss で確定した棚卸し項目の改善により使いやすくなる。v1.5.0 新機能 6 種（白紙挿入・テキスト透かし・ページ番号・TOC 保持・D&D 指定位置挿入・ショートカット動的読込）の回帰テストが整備される（V171-TEST-01）。

ショートカットの GUI 編集・文言/エラー監査（Phase 4 の領分）・サムネイル仮想化（PERF-01・将来）・OCR 系はスコープ外。

</domain>

<decisions>
## Implementation Decisions

### 画像透かし（V171-PAGE-01）
- **D-01:** UI 導線はテキスト透かしと同じミニマムパターン：ボタン → `filedialog` で画像選択 → 既定値で選択ページへ即適用。設定/プレビューダイアログは設けない。
- **D-02:** 既定配置は**ページ中央・アスペクト比保持でページ幅の約 50%** に収まるよう縮小。
- **D-03:** **50% 透過・回転なし**（ロゴは水平のまま）。`insert_image` に不透明度引数はないため Pillow でアルファチャンネルを乗算前処理して埋め込む。透過 PNG の既存アルファは乗算で尊重する。
- **D-04:** 対応形式は **PNG / JPEG のみ**（filedialog のフィルタもこの 2 種）。
- **制約:** undo はテキスト透かしと同じ `page_edit` op（適用前ページ bytes・`_capture_page_blob` 経由の Blob ライフサイクル遵守）。

### 黒塗り/モザイク棚卸し（V171-PAGE-02）— 4 項目全対象
- **D-05:** **連続適用**：適用後も黒塗りモードを常に維持する（現状の自動 OFF を廃止）。終了はトグルボタンで明示的に OFF。トリミングとの相互排他は維持。設定項目化はしない。
- **D-06:** **モザイク粒度**：右ペインのページ編集セクション内にスライダーを追加（サムネイルサイズスライダーと同じ既存パターン）。値は `pagefolio_settings.json` に永続化。現行 `MOSAIC_BLOCK` 定数は既定値として残す。
- **D-07:** **複数矩形の一括適用**：ドラッグ完了のたびに矩形をリストへ追加しオーバーレイ表示。「適用」で全矩形を一括処理・「クリア」で全削除。undo は **1 回の `page_edit` でまとめて戻る**。個別矩形のクリック選択/削除は実装しない。
- **D-08:** **回転表示中の座標対応**：ドラッグ矩形を `page.rotation`（90/180/270）に応じて未回転ページ座標系へ逆変換する**共通ヘルパー**を導入し、黒塗り/モザイク/トリミングの 3 操作すべてで「見たままの位置」に適用されるようにする。純関数化してテストで担保（既知制限「矩形は未回転のページ座標系で適用」の解消）。

### 回転/トリミング棚卸し（V171-PAGE-03）— 3 項目対象・回転側の追加改善は見送り
- **D-09:** **矩形の微調整**：確定後の矩形を矢印キーで 1pt 移動・Shift+矢印で右下辺リサイズ。キーバインドのみで実現（8 方向ハンドルは実装しない）。
- **D-10:** **数値指定トリミング**：「上下左右から何 mm 削るか」の余白幅指定 → 選択ページへ一括適用。矩形座標の直接入力は実装しない。
- **D-11:** **サイズ表示**：crop_info 表示を「45×60mm（28%）」形式（mm 換算＋ページ占有率）へ拡張。
- **D-12:** 回転機能自体の追加改善は見送り（v1.6.0 のプレビュー即時反映で十分・90° 単位維持）。回転絡みは D-08 の座標対応のみ。

### v1.5.0 回帰テスト（V171-TEST-01）
- **D-13:** テストゼロの 3 機能は**ロジック抽出＋FakeApp 併用**：D&D の挿入位置計算・ショートカットのマージ/検証ロジックは純関数へ抽出して直接テスト（`pagination.py` 方式の踏襲）、TOC 保持（削除/結合/分割時）は既存 `TestContentOpsUndoFix` と同じ FakeApp mixin 方式で doc 操作を検証。機能ごとに最適な形を選ぶ。
- **D-14:** 既存 undo 往復テスト 3 件（白紙挿入・テキスト透かし・ページ番号）へ**内容検証を追加**：透かしテキストの `get_text` 抽出確認・白紙ページのサイズ一致等の正常系を足す。
- **D-15:** Phase 3 で追加するテストは**新規ファイルへ分離**（`test_pdf_ops.py` は既に約 1,500 行で肥大化防止。ファイル名・分割単位は planner 判断）。
- **D-16:** D&D テストは**ドロップ座標→挿入位置計算＋ `_do_insert` 経路まで**をカバー。tkinterdnd2 のイベント発火自体は対象外（手動 QA 領域）。

### Claude's Discretion
- 画像透かしの縮小/アルファ乗算の実装詳細（Pillow の合成手順・DPI 扱い）と、ページより大きい/極端に小さい画像のクランプ処理。
- 回転座標逆変換ヘルパーの置き場所（既存 mixin 内 static か新純ロジックモジュールか）と API 形状。
- 複数矩形のオーバーレイ描画方式・矩形リストの状態管理（`crop_rect` との共存形）。
- モザイク粒度スライダーの値域・ステップと settings キー名。
- 数値指定トリミングの入力 UI（simpledialog 連続入力 or 小ダイアログ 1 枚）と mm→pt 換算の丸め。
- 新規テストファイルの命名・分割単位（機能別 1 ファイル or v1.5.0 回帰で 1 ファイル）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・ロードマップ
- `.planning/REQUIREMENTS.md` — V171-PAGE-01〜03・V171-TEST-01 の要件定義と Key Context
- `.planning/ROADMAP.md` §Phase 3 — 成功基準 4 項目（棚卸し結果と対応は計画時に確定・記録される）

### 先行決定（維持すべき制約）
- `.planning/PROJECT.md` §Key Decisions — V16-D-01（pagination 純ロジック層パターン）・V16-D-02（純関数化＋薄い描画層の方針）
- `CLAUDE.md` §既知の制限・注意事項 — 黒塗り/モザイクは破壊的操作・矩形は未回転ページ座標系（**D-08 で解消予定**・解消後は CLAUDE.md の当該記述を更新すること）・CropBox は MediaBox 内クランプ必須
- `CLAUDE.md` §Architectural Constraints — Undo Blob ライフサイクル（`_capture_page_blob` 経由必須・スタック直接 append/clear 禁止）

（外部 spec/ADR ファイルはなし。要件は上記 planning ドキュメントに集約されている）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pagefolio/page_ops.py:180 _add_watermark_text` — 画像透かしの雛形（`_get_targets` → `page_edit` undo → 適用 → `_invalidate_thumb_cache` → `_refresh_all` の作法）。D-01 はこの並びに `insert_image` 版を追加する形。
- `pagefolio/redact_ops.py:72 _apply_page_edit` — 黒塗り/モザイク共通適用フロー。D-05/D-07 の改修起点。`_page_rect_from_rel`（:136）は複数矩形化でも再利用可能。
- `pagefolio/redact_ops.py:166 _mosaic_page` — `MOSAIC_BLOCK`（`constants.py`）参照箇所。D-06 で粒度引数化。
- `pagefolio/page_ops.py:253 _canvas_rect_to_pdf` — キャンバス座標→PDF 座標変換。D-08 の回転逆変換はこの直後に挟む形が自然。
- サムネイルサイズスライダー（`thumb_zoom_scale`・v1.5.0）— D-06 のスライダー実装の既存パターン。
- `tests/test_pdf_ops.py:1469 TestContentOpsUndoFix` — FakeApp mixin 方式の実例（白紙/透かし/ページ番号の undo 往復・D-13/D-14 の出発点）。
- `tests/conftest.py` — `sample_pdf_doc` / `large_pdf_doc` / `multi_pdf_files` フィクスチャ（TOC・挿入テストに流用可）。

### Established Patterns
- Tk 非依存の純ロジック抽出＋直接テスト（`pagination.py` / `md_render.py` / `undo_store.py`）— D-08 ヘルパー・D-13 抽出の同型。
- コンテンツ改変系 undo は `page_edit` op（適用前ページ bytes・v1.7.0 で watermark/page_numbers/insert_blank の no-op undo バグを修正済み）。
- LANG 新規キーは ja/en 両辞書へ同一キーで追加（`test_lang_parity.py` が監視）。ボタン文言・注記の追加時に必須。
- テーマ色は `C[...]`・フォントは `self._font(delta)`・破壊的操作ボタンは `Danger.TButton`。

### Integration Points
- `pagefolio/ui_builder.py:583-609` — ページ編集セクション（redact トグル・適用ボタン群）。D-06 スライダー・D-07 クリアボタンの追加先。
- `pagefolio/app.py:128-156` — ショートカットのマージ（`default_shortcuts` + `settings["shortcuts"]`）。D-13 の抽出対象。
- `pagefolio/file_drop.py` + `app._on_thumb_dnd_drop` / `_on_thumb_dnd_motion` — D&D 挿入位置計算の抽出対象（D-13/D-16）。
- `pagefolio/page_ops.py:124-127, 643-650, 726-734, 770+` — TOC 保持処理（削除/結合/分割）。D-13 の FakeApp テスト対象。
- `pagefolio/page_ops.py:237 _toggle_crop_mode` / `redact_ops.py:37 _toggle_redact_mode` — 相互排他ペア。D-05 のモード維持変更時に整合維持。

### 回帰テストの現状ギャップ（scout 確定）
- テストあり（undo 往復のみ）: 白紙挿入・テキスト透かし・ページ番号（`TestContentOpsUndoFix`）
- テストゼロ: TOC 保持・D&D 指定位置挿入・ショートカット動的読込

</code_context>

<specifics>
## Specific Ideas

- 画像透かしはテキスト透かしと**同じ操作感**（ボタン → 選択 → 即適用）に揃える。ダイアログを増やさない。
- 黒塗りの連続適用は「モードに入ったら塗り続けられる」体験にする（毎回ボタンを押し直させない）。
- 回転座標対応は「見たままの位置に適用される」を 3 操作（黒塗り/モザイク/トリミング）で一貫させる。

</specifics>

<deferred>
## Deferred Ideas

- 矩形の 8 方向ハンドルドラッグリサイズ（D-09 は矢印キーのみ採用）— 需要があれば将来フェーズ
- 矩形の個別クリック選択/削除（D-07 は追加→一括適用/全クリアのみ）— 同上
- 画像透かしの配置/サイズ/不透明度のカスタマイズ UI（D-01 は既定値固定）— 需要があれば将来フェーズ
- タイル敷き詰め透かし・四隅スタンプ配置 — 同上
- 回転側の追加改善（任意角度回転等）— D-12 で見送り

</deferred>

---

*Phase: 3-ページ操作磨き込み + v1.5.0 回帰テスト*
*Context gathered: 2026-07-05*
