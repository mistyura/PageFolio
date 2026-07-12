---
id: S03
parent: M003
milestone: M003
provides:
  - 画像（PNG/JPEG）透かしをページへ焼き込む _add_watermark_image / _watermark_image_rect（page_ops.py）
  - テキスト透かしボタン直後に結線された画像透かしボタン（ui_builder.py）
  - btn_watermark_image LANG キー（ja/en）
  - tests/test_page_polish.py（Phase 3 新規テスト専用ファイル・D-15）
  - D&D 挿入位置計算の純関数 compute_dnd_dest_index（pagefolio/dnd.py）
  - ショートカットマージ/Shift大文字補完判定の純関数 merge_shortcuts / shift_variant_keysym（pagefolio/app.py）
  - tests/test_v150_regression.py（新規・v1.5.0回帰テスト専用ファイル・D-15）
  - test_pdf_ops.py の TestContentOpsUndoFix への内容検証強化（D-14）
  - 回転座標共通ヘルパー _derotate_rect（page_ops.py・黒塗り/モザイク/トリミングが共用予定）
  - crop_info の mm＋％表示 _format_crop_info（page_ops.py）
  - 矩形の矢印キー微調整 _nudge_crop_rect / _redraw_crop_overlay（page_ops.py・ui_builder.py キーバインド）
  - 数値指定（mm）トリミング compute_margin_crop_rect / _crop_by_margin（page_ops.py・ui_builder.py ボタン・lang.py キー）
  - PT_PER_MM 定数（constants.py・mm↔pt換算の単一情報源）
  - 黒塗り/モザイクの連続適用（_apply_page_edit から _redact_mode_off 呼び出しを削除・D-05）
  - モザイク粒度スライダー mosaic_block_var/scale・_on_mosaic_block_release（settings永続化・D-06）
  - 複数矩形一括適用 self._redact_rects・_clear_redact_rects・クリアボタン（D-07）
  - _apply_page_edit への _derotate_rect 統合（黒塗り/モザイクの回転座標対応・D-08）
requires: []
affects: []
key_files: []
key_decisions:
  - PNG は既存アルファを0.5乗算、JPEGはconvert(\"RGBA\")後に均一128(=50%)をputalphaで付与（D-03）
  - _watermark_image_rect は幅50%縮小を既定としつつ、縦長画像で高さがページ高さ90%を超える場合は高さ基準へクランプ（Claude's Discretion）
  - undo は _save_undo(\"page_edit\", targets=targets) を適用ループの外側で1回だけ呼ぶ（page_ops.py 内 grep で出現1回を確認）
  - _dnd_dest_index はTk依存部（winfo_*/canvasy/event）のみ残し、cursor_y と frame_bounds 列からの index 算出は compute_dnd_dest_index へ完全委譲
  - merge_shortcuts/shift_variant_keysym は app.py module-level関数として抽出（新規モジュール化はRESEARCH.md A4の通り投資対効果が低いため見送り）
  - TOC回帰テストは削除・結合・分割（範囲/全ページ）の4パターンをFakeAppで直接検証（must_havesの3機能を上回る網羅）
  - _derotate_rect は page.rotation==0 のとき早期に恒等（min/max正規化のみ）を返し、90/180/270 のみ page.derotation_matrix を計算する（無回転ページでの余計な行列計算を回避）
  - crop_info（_format_crop_info）は _canvas_rect_to_pdf 後・derotate 前の値をそのまま使う（画面上で選択した見たままのサイズを mm 表示するのが自然なため。derotate は _crop_page 適用時のみ必要）
  - 矢印キー微調整は preview_canvas への bind とし、_crop_drag_start 内で focus_set() してキー入力を受理できるようにする（Tk はクリック後でないとキーイベントを渡さないため）
  - 数値指定トリミングの mm 入力は simpledialog.askfloat の4連続呼び出し（上→下→左→右）とし、専用ダイアログは作らない。基準は「現在の cropbox」（A2・RESEARCH.md で解決済みの Open Question）
  - _crop_by_margin の undo は新規 op を作らず既存 bulk_crop を流用（file_ops.py の _apply_inverse がすでに対称処理を実装済みのため）
  - _apply_page_edit(kind, block=None) へシグネチャ変更。block はモザイク時のみ使用し、redact 時は無視される（呼び出し側 _apply_mosaic が settings 値を解決して渡す）
  - 複数矩形は self._redact_rects（蓄積）＋現在の self.crop_rect の合算から構築し、単一矩形の既存フロー（crop_rectのみ）との後方互換を保つ
  - _redact_rects/_redact_rect_overlay_ids は _toggle_redact_mode 進入時に lazy init（app.py __init__ は変更しない）。_crop_drag_end 側でも getattr 防御的初期化を二重で持たせ、テストや異常系での AttributeError を防ぐ
  - 複数矩形の持続オーバーレイは実線アウトラインのみ（stipple省略・RESEARCH.md Open Question 2 の解決どおり）
  - _apply_page_edit 適用後の後片付けで _redact_mode_off は呼ばない（D-05）が、_clear_crop_overlay/_clear_redact_rects は呼ぶ（オーバーレイ・蓄積矩形は毎回クリア、モードのみ維持）
patterns_established:
  - 画像系操作の undo/redo 検証は page.get_images() で行う（get_text() では画像の存在を検出できないため・Pitfall 5）
  - 純関数抽出後も既存メソッド名・シグネチャ・実際のTk/fitz呼び出し順序は完全に不変（挙動保存のリファクタリング）
  - derotate → mediabox相対化 の適用順序固定パターンは 03-04（黒塗り/モザイクの複数矩形対応）でも _apply_page_edit 側から同じ _derotate_rect を呼ぶ形で再利用される
  - _derotate_rect の呼び出しは _crop_page（03-03）と _apply_page_edit（本プラン）の2箇所に集約され、いずれも _canvas_rect_to_pdf 直後・mediabox相対化前の同一順序を守る（回転座標変換ロジックの重複実装防止・03-CONTEXT.md D-08）
observability_surfaces: []
drill_down_paths: []
duration: 18min
verification_result: passed
completed_at: 2026-07-05
blocker_discovered: false
---
# S03: V1 5 0

**# Phase 3 Plan 1: 画像透かし（V171-PAGE-01）Summary**

## What Happened

# Phase 3 Plan 1: 画像透かし（V171-PAGE-01）Summary

**PNG/JPEG画像をページ中央・幅約50%・50%透過で焼き込む `_add_watermark_image`/`_watermark_image_rect` を実装し、既存テキスト透かしと同型の page_edit undo で完全復元可能にした**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-05T05:50:37Z
- **Completed:** 2026-07-05T05:56:00Z
- **Tasks:** 2
- **Files modified:** 4（うち新規1）

## Accomplishments
- `pagefolio/page_ops.py` に `_add_watermark_image`（ボタン→ファイル選択→即適用→page_edit undo）と `_watermark_image_rect`（中央配置・幅50%縮小・縦長クランプの純関数）を追加
- PNG の既存アルファは0.5乗算、JPEGはRGBA変換後に均一50%透過を付与（D-03）。破損/非対応画像は `try/except Exception` で保護し `messagebox.showerror` へフォールバック（T-3-01）
- `ui_builder.py` にテキスト透かしボタン直後で `_add_watermark_image` へ結線した画像透かしボタンを追加、`lang.py` ja/en 両辞書へ `btn_watermark_image` を同一キーで追加
- `tests/test_page_polish.py` を新規作成（D-15・Phase 3 の新規テスト専用ファイル）。純関数（中央配置・幅50%・クランプ）、PNG/JPEG埋め込み確認、undo往復、未選択時no-op、破損画像ハンドリング、LANGパリティの計9テストを追加

## Task Commits

Each task was committed atomically:

1. **Task 1: 画像透かしの適用ロジック（_add_watermark_image / _watermark_image_rect）** - `d876cd9` (feat)
2. **Task 2: 透かしボタンのUI結線とLANGキー追加** - `d43fe17` (feat)

**Plan metadata:** (このコミットで追加)

## Files Created/Modified
- `pagefolio/page_ops.py` - `_add_watermark_image`/`_watermark_image_rect` を追加（`from PIL import Image`/`import io` を冒頭に追加）
- `pagefolio/ui_builder.py` - テキスト透かしボタン直後に画像透かしボタンを結線
- `pagefolio/lang.py` - ja/en 両辞書へ `btn_watermark_image` キーを追加
- `tests/test_page_polish.py` (新規) - `TestImageWatermarkRect`/`TestImageWatermark`/`TestImageWatermarkLang` の3クラス9テスト

## Decisions Made
- D-03 に忠実に PNG は既存アルファ×0.5、JPEGは`convert("RGBA")`後に均一128を`putalpha`（画像自体のRGBA/SMaskに依存する`insert_image`の仕様どおり）
- D-02 の「ページ幅約50%・アスペクト比保持」に加え、縦長画像がページ高さの90%を超える場合は高さ基準へクランプ（Claude's Discretion・RESEARCH.md Pattern 1 のコード例を踏襲）
- undo は `_save_undo("page_edit", targets=targets)` を適用ループの外側で1回だけ呼ぶ既存パターンを完全踏襲（複数ページ選択時も1回のundoで全ページ復元）

## Deviations from Plan

None - plan executed exactly as written（RESEARCH.md/PATTERNS.md のコード例をほぼそのまま採用）。

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-PAGE-01 完了。03-02（黒塗り/モザイク棚卸し・OCR系並行プラン）へ進行可能
- 画像透かしの実描画（半透明・SMask）は end-of-phase human-verify 対象として残存（03-CONTEXT.md/03-RESEARCH.md A1・VALIDATION.md Manual-Only 明記済み）
- `pytest` フルスイート 787件グリーン（従来780件から+7）・`ruff check`/`ruff format --check` クリーン

---
*Phase: 03-v1-5-0*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/page_ops.py
- FOUND: tests/test_page_polish.py
- FOUND: .planning/phases/03-v1-5-0/03-01-SUMMARY.md
- FOUND: d876cd9 (Task 1 commit)
- FOUND: d43fe17 (Task 2 commit)

# Phase 3 Plan 2: v1.5.0 回帰テスト整備（V171-TEST-01）Summary

**D&D挿入位置計算とショートカットマージを純関数へ抽出し、TOC保持・D&D・ショートカットの3系統回帰テストを新規ファイルへ整備、既存undo往復テストへ内容検証を追加**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-05T14:57:21Z（前タスク完了直後）
- **Completed:** 2026-07-05T15:07:07Z
- **Tasks:** 3
- **Files modified:** 4（うち新規1）

## Accomplishments
- `pagefolio/dnd.py` に `compute_dnd_dest_index(cursor_y, frame_bounds)` 純関数を抽出。`_dnd_dest_index` は Tk 依存部（`winfo_*`/`canvasy`/`event`）のみ残す薄いラッパーへ改修
- `pagefolio/app.py` に `merge_shortcuts(default, custom)` / `shift_variant_keysym(keysym)` 純関数を抽出。`__init__` のショートカットマージ・Shift大文字補完ループを委譲する薄い形へ改修
- `tests/test_v150_regression.py` を新規作成（D-15）。`TestDndDestIndex`（境界値7件）・`TestShortcutMerge`（マージ/判定7件）・`TestTocPreservation`（削除/結合/範囲分割/全ページ分割の4件）で計18テストを追加
- `tests/test_pdf_ops.py` の `TestContentOpsUndoFix` 既存3メソッドへ内容検証を追記（D-14）: 白紙挿入のページサイズ一致・透かし/ページ番号の undo 後元コンテンツ保持を全選択ページ分（未選択ページ含む）で厚く検証
- `pytest` フルスイート 805 件グリーン（従来787件から+18）・`ruff check`/`ruff format --check` クリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: 純ロジック抽出（compute_dnd_dest_index / merge_shortcuts / shift_variant_keysym）** - `8ed8217` (refactor)
2. **Task 2: 回帰テスト新規ファイル（D&D 位置・ショートカット・TOC 保持）** - `37cb618` (test)
3. **Task 3: 既存 undo 往復テストへ内容検証を追加（D-14）** - `f879091` (test)
4. **[フォローアップ] ruff format 整形（shift_variant_keysym 条件式1行化）** - `d215972` (style)

**Plan metadata:** (このコミットで追加)

## Files Created/Modified
- `pagefolio/dnd.py` - `compute_dnd_dest_index` 純関数を追加、`_dnd_dest_index` を薄いラッパー化
- `pagefolio/app.py` - `merge_shortcuts`/`shift_variant_keysym` 純関数を追加、`__init__` から委譲
- `tests/test_v150_regression.py` (新規) - `TestDndDestIndex`/`TestShortcutMerge`/`TestTocPreservation` の3クラス18テスト
- `tests/test_pdf_ops.py` - `test_insert_blank_roundtrip`/`test_watermark_roundtrip`/`test_page_numbers_roundtrip` へ内容検証assert追記

## Decisions Made
- `_dnd_dest_index`/ショートカットループの委譲は完全に挙動保存（既存 `root.bind`・`event`/`winfo_*` 呼び出し順序は不変）。抽出はロジックのみで実挙動は変えない（RESEARCH.md A4・脅威登録T-3-02の要求通り）
- TOC回帰テストは must_haves で言及された「削除/結合/分割」の3機能を、分割については範囲指定と全ページ分割の2パターンに分けて検証し網羅性を高めた（`_split_by_range`/`_split_each_page` 両方のTOC再採番コードパスを exercise）
- 内容検証の追加は既存テスト構造（メソッド数・assert前後関係）を一切変更せず、正常系assertの追記のみに留めた（D-14の「テスト構造は変えず」制約を厳守）

## Deviations from Plan

None - plan executed exactly as written（RESEARCH.md Pattern 5/6のコード例をそのまま採用、FakeApp mixinはtest_pdf_ops.pyの既存実装を再利用）。

唯一の追加作業は `ruff format` によるコードスタイル自動整形（`shift_variant_keysym` の複数行if文を1行へ短縮）で、これは Rule 3（ブロッキング解消・リント整合）に該当する軽微な自動修正。

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-TEST-01 完了。D&D・ショートカット・TOC保持の回帰網が張られ、以降のページ操作磨き込み（03-03/03-04）が既存挙動を壊していないか継続的に検証可能
- Wave 1（03-01・03-02）完了。Wave 2（03-03: 黒塗り/モザイク・回転座標対応）へ進行可能
- `pytest` フルスイート805件グリーン・`ruff check`/`ruff format --check`クリーン

---
*Phase: 03-v1-5-0*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/dnd.py
- FOUND: pagefolio/app.py
- FOUND: tests/test_v150_regression.py
- FOUND: tests/test_pdf_ops.py
- FOUND: 8ed8217 (Task 1 commit)
- FOUND: 37cb618 (Task 2 commit)
- FOUND: f879091 (Task 3 commit)
- FOUND: d215972 (follow-up style commit)

# Phase 3 Plan 3: 回転/トリミング棚卸し（V171-PAGE-03）Summary

**page.derotation_matrix を使う共通ヘルパー_derotate_rectで黒塗り/モザイク/トリミングの座標ズレを構造的に解消し、矢印キー微調整・mm指定トリミング・crop_infoのmm＋%表示を実装**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-05T06:14:00Z（前プラン完了直後・読解含む）
- **Completed:** 2026-07-05T06:21:53Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `pagefolio/page_ops.py` に静的メソッド `_derotate_rect(page, x0, y0, x1, y1)` を追加。`page.rotation==0` で恒等（正規化のみ）、90/180/270 で `page.derotation_matrix` により表示座標→未回転座標へ正しく逆変換する（D-08）。`_crop_page` の単一・bulk 両分岐へ `_canvas_rect_to_pdf` 直後・mediabox 相対化前の1本道で統合し、次プラン（03-04）の黒塗り/モザイクからも再利用可能な共通ヘルパーとして確立
- `_format_crop_info` 純関数を追加し、`_crop_drag_move`（→ `_redraw_crop_overlay` へ抽出後）の crop_info 表示を「45×60mm（28%）」形式へ拡張（D-11）。`PT_PER_MM = 72/25.4` を `constants.py` に単一情報源として新設
- `_nudge_crop_rect(dx_pt, dy_pt, resize=False)` を追加。確定済み矩形を矢印キーで1pt移動、Shift+矢印で右下辺リサイズ（D-09）。オーバーレイ再描画は `_redraw_crop_overlay` へ抽出し、ドラッグ中と矢印微調整の両方から共用。`preview_canvas` へ矢印/Shift+矢印バインドを追加し、`_crop_drag_start` で `focus_set()` してキー入力を受理可能にした
- `compute_margin_crop_rect` 純関数と `_crop_by_margin` メソッドを追加（D-10）。「上下左右から何mm削るか」を `simpledialog.askfloat` の連続入力で受け取り、現在の cropbox（A2）から差し引く。undo は既存 `bulk_crop` op を再利用。差引結果が幅/高さ1pt未満なら安全側フォールバック（None・T-3-03）
- `tests/test_page_polish.py` へ `TestDerotateRect`（回転0恒等＋90/180/270 roundtrip）・`TestFormatCropInfo`・`TestCropPolish`（移動/リサイズ/未確定no-op/モードOFF）・`TestMarginCrop`（純関数＋FakeApp適用/undo/キャンセル）の4クラス計19テストを追加

## Task Commits

Each task was committed atomically:

1. **Task 1: 回転座標共通ヘルパー_derotate_rect + トリミング統合 + crop_info mm表示（D-08/D-11）** - `f4b948e` (feat)
2. **Task 2: 矩形の矢印キー微調整_nudge_crop_rect（D-09）** - `2bbbe39` (feat)
3. **Task 3: 数値指定（mm）トリミング_crop_by_margin（D-10）** - `d0a272f` (feat)

**Plan metadata:** (このコミットで追加)

## Files Created/Modified
- `pagefolio/page_ops.py` - `_derotate_rect`（静的）・`_format_crop_info`（純関数）・`_redraw_crop_overlay`（抽出）・`_nudge_crop_rect`・`compute_margin_crop_rect`（純関数）・`_crop_by_margin` を追加。`_crop_page`（単一/bulk）へ derotate 統合、`_crop_drag_start` へ `focus_set()`
- `pagefolio/ui_builder.py` - preview_canvas へ矢印/Shift+矢印キーバインド追加、トリミングセクションへ `btn_crop_margin` ボタン追加
- `pagefolio/lang.py` - ja/en 両辞書へ `btn_crop_margin`/`dlg_crop_margin_title`/`crop_margin_top`/`crop_margin_bottom`/`crop_margin_left`/`crop_margin_right` を追加
- `pagefolio/constants.py` - `PT_PER_MM = 72 / 25.4` を追加
- `tests/test_page_polish.py` - `TestDerotateRect`/`TestFormatCropInfo`/`TestCropPolish`/`TestMarginCrop`の4クラス19テストを追加

## Decisions Made
- `_derotate_rect` は回転0のとき `page.derotation_matrix` を計算せず早期returnで min/max 正規化のみ行う（無回転ページでの余計な行列計算回避・パフォーマンス配慮）
- crop_info（mm表示）は derotate 前の canvas→pdf 変換値をそのまま使う。ユーザーが画面上で見て選択したサイズをそのまま mm 表示するのが直感的なため（derotate は `_crop_page` の実適用時のみ必要という PLAN.md の役割分担どおり）
- 数値指定トリミングは専用ダイアログを新設せず `simpledialog.askfloat` の4連続呼び出し（Claude's Discretion・RESEARCH.md/CONTEXT.md で明示的に選択可とされた形）
- `_crop_by_margin` の undo は新規 op を作らず既存 `bulk_crop`（file_ops.py の `_apply_inverse` が既に対称処理実装済み）を再利用し、undo/redo ロジックの分散を避けた

## Deviations from Plan

None - plan executed exactly as written（RESEARCH.md Pattern 2/Code Examples のコード例をほぼそのまま採用、PATTERNS.md の既存 analog をそのまま踏襲）。

## Issues Encountered

`zip()` に `strict=` 引数を要求する ruff B905 警告が `TestDerotateRect` のroundtripテストで発生。`strict=True` は Python 3.10+ 限定のため CLAUDE.md の Python 3.8+ 互換制約に抵触すると判断し、`zip()` を使わず `range(4)` によるインデックスループへ書き換えて解消（Rule 1 - リント整合の軽微な自動修正）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-PAGE-03 完了。共通ヘルパー `_derotate_rect` が確立されたため、03-04（黒塗り/モザイク棚卸し・D-05連続適用/D-06モザイク粒度/D-07複数矩形/D-08統合）は `_apply_page_edit` からこのヘルパーを呼ぶだけで座標対応を再利用できる
- 矩形ドラッグ/矢印微調整の操作感（視覚的な見た目）は end-of-phase human-verify 対象として残存（PLAN.md verify セクション・VALIDATION.md Manual-Only 明記済み）
- `pytest` フルスイート 822件グリーン（従来805件から+17: derotate系7・crop_polish系5・margin_crop系5）・`ruff check`/`ruff format --check` クリーン
- CLAUDE.md §既知の制限「矩形は未回転のページ座標系で適用される」は本プラン（トリミング側）では解消済みだが、黒塗り/モザイク側の統合は03-04完了後にまとめて更新予定（03-CONTEXT.md canonical_refs 明記どおり）

---
*Phase: 03-v1-5-0*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/page_ops.py
- FOUND: tests/test_page_polish.py
- FOUND: .planning/phases/03-v1-5-0/03-03-SUMMARY.md
- FOUND: f4b948e (Task 1 commit)
- FOUND: 2bbbe39 (Task 2 commit)
- FOUND: d0a272f (Task 3 commit)

# Phase 3 Plan 4: 黒塗り/モザイク棚卸し（V171-PAGE-02）Summary

**黒塗り/モザイクを連続適用可能にし、モザイク粒度スライダー・複数矩形一括適用（1回undo）・page.derotation_matrixによる回転座標対応を`_apply_page_edit`へ統合**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-05T06:26:00Z（前プラン03-03完了直後・読解含む）
- **Completed:** 2026-07-05T06:44:02Z
- **Tasks:** 2
- **Files modified:** 6（うちCLAUDE.md追記1）

## Accomplishments
- `_apply_page_edit` の後片付けから `_redact_mode_off()` 呼び出しのみを削除し、黒塗り/モザイク適用後もモードが維持される連続適用を実現（D-05）。トリミングとの相互排他ロジック（`_toggle_redact_mode`/`_toggle_crop_mode`）は不変
- `_mosaic_page` に `block` 引数を追加（既定 `MOSAIC_BLOCK`・後方互換）。`ui_builder.py` にモザイク粒度スライダー（`mosaic_block_var`/`mosaic_block_scale`）を追加し、`_on_mosaic_block_release` で `settings["mosaic_block"]` へ永続化（D-06）
- `_apply_page_edit` を複数矩形対応へ改修。`self._redact_rects`（ドラッグ完了ごとに蓄積・`_crop_drag_end` の redact モード分岐）＋現在の `crop_rect` から対象矩形集合を構築し、`_save_undo` はターゲットページ集合に対しループの外側で必ず1回だけ呼ぶ（D-07・Pitfall4）。「クリア」ボタン（`_clear_redact_rects`）で全矩形・オーバーレイを削除可能
- 各矩形の座標変換に 03-03 で確立した `_derotate_rect`（`page.derotation_matrix`）を統合し、`_canvas_rect_to_pdf → _derotate_rect → mediabox相対化` の1本道で黒塗り/モザイク/トリミングの3操作すべてが回転座標に対応（D-08）。CLAUDE.md の既知の制限「矩形は未回転のページ座標系で適用される」の記述を解消後の内容へ更新
- `tests/test_page_polish.py` へ `TestRedactPolish` を追加（連続適用・モザイク粒度差・後方互換・settings連携・複数矩形一括適用+単一undo・`_save_undo`単一呼出し・回転90度derotate位置一致・クリア機能・ドラッグ蓄積・LANGパリティの計13テスト）

## Task Commits

Each task was committed atomically:

1. **Task 1: 連続適用（D-05）＋モザイク粒度スライダー（D-06）** - `128e938` (feat)
2. **Task 2: 複数矩形の一括適用（D-07）＋回転座標対応の統合（D-08）** - `dabcdec` (feat)
3. **CLAUDE.md既知の制限のD-08解消後更新** - `6669fa3` (docs)

**Plan metadata:** (このコミットで追加)

## Files Created/Modified
- `pagefolio/redact_ops.py` - `_apply_mosaic`/`_apply_page_edit`/`_mosaic_page` の改修、`_on_mosaic_block_release`・`_clear_redact_rects` を追加、`_toggle_redact_mode`/`_redact_mode_off` へ複数矩形状態のlazy init/クリアを統合
- `pagefolio/page_ops.py` - `_crop_drag_end` へ redact モードの複数矩形蓄積分岐（`_redact_rects`・持続オーバーレイ）を追加
- `pagefolio/ui_builder.py` - モザイク粒度スライダーと「クリア」ボタンを f3b セクションへ追加
- `pagefolio/lang.py` - `mosaic_block_label`/`btn_redact_clear` を ja/en 両辞書へ追加
- `tests/test_page_polish.py` - `TestRedactPolish` クラス（13テスト）を追加
- `CLAUDE.md` - 既知の制限の「矩形は未回転のページ座標系で適用される」を D-08 解消後の内容（見たままの位置に適用）へ更新、D-05/D-06/D-07 の挙動を追記

## Decisions Made
- `_apply_page_edit(kind, block=None)` へシグネチャ変更。block はモザイク時のみ意味を持ち、`_apply_mosaic` が `settings.get("mosaic_block", MOSAIC_BLOCK)` を解決して渡す（`MOSAIC_BLOCK` 定数は不変のまま既定値として温存）
- 複数矩形は `self._redact_rects`（蓄積）＋現在の `self.crop_rect` の合算から構築し、単一矩形のみの既存フロー（crop_rectのみセット）との後方互換を保った
- `_redact_rects`/`_redact_rect_overlay_ids` は `_toggle_redact_mode` 進入時に lazy init（app.py `__init__` は変更しない）。`_crop_drag_end` 側でも `getattr` 防御的初期化を二重に持たせ、異常系での AttributeError を防止
- 複数矩形の持続オーバーレイは実線アウトラインのみ（stipple省略・RESEARCH.md Open Question 2 の解決どおり採用）
- `_apply_page_edit` 適用後の後片付けで `_redact_mode_off` は呼ばない（D-05）が、`_clear_crop_overlay`/`_clear_redact_rects` は呼ぶ（オーバーレイ・蓄積矩形は毎回クリアしモードのみ維持する設計）

## Deviations from Plan

None - plan executed exactly as written（RESEARCH.md Pattern 2/4・PATTERNS.md の既存 analog をほぼそのまま採用）。

## Issues Encountered

`ruff format` が `ui_builder.py` の `.bind("<ButtonRelease-1>", self._on_mosaic_block_release)` を1行へ再整形（改行折返しの自動整形差分）。フォーマッタの自動整形結果をそのまま採用（Rule 1 - リント整合の軽微な自動修正）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-PAGE-02 完了。黒塗り/モザイクの棚卸し4項目（D-05〜D-08）すべて実装済み
- `_derotate_rect` の実プレビュー上での回転座標対応（見た目の位置一致）・複数矩形の連続ドラッグ操作感は end-of-phase human-verify 対象として残存（03-CONTEXT.md/03-RESEARCH.md・VALIDATION.md Manual-Only 明記済み）
- `pytest` フルスイート 833件グリーン（従来822件から+11）・`ruff check`/`ruff format --check` クリーン
- Phase 3 の全4プラン（03-01〜03-04）完了。V171-PAGE-01（03-01）・V171-TEST-01（03-02）・V171-PAGE-03（03-03）・V171-PAGE-02（本プラン03-04）で全要件充足。Phase 3 完了、Phase 4（UI/UX磨き込み+既知バグ棚卸し）へ進行可能

---
*Phase: 03-v1-5-0*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/redact_ops.py
- FOUND: pagefolio/page_ops.py
- FOUND: pagefolio/ui_builder.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_page_polish.py
- FOUND: CLAUDE.md
- FOUND: 128e938 (Task 1 commit)
- FOUND: dabcdec (Task 2 commit)
- FOUND: 6669fa3 (CLAUDE.md update commit)
