---
phase: 03
status: issues-found
reviewed_files: 10
depth: standard
---

# Phase 3 コードレビュー

## サマリー

Phase 3（V171-PAGE-01/02/03・V171-TEST-01）の4プランは計画・設計どおりに実装されており、`_derotate_rect` を軸にした回転座標の一本化・複数矩形の一括 undo・純関数抽出（`compute_dnd_dest_index`/`merge_shortcuts`/`shift_variant_keysym`）はいずれも意図通り動作する。`pytest`（833件）・`ruff check`・`ruff format --check` は全てクリーンであることを実測で確認した。重大なバグ・セキュリティ問題は見つからなかったが、ドキュメント整合性の未実施と、redact モードの空クリックによる退化矩形蓄積という軽微な見落としがある。

## Critical（バグ・セキュリティ）

なし

## Warning（品質・規約違反）

- **バージョン/開発履歴の未更新（CLAUDE.md 規約違反）**: `CLAUDE.md` の「既知の制限・注意事項」節は本フェーズの成果を指して既に「v1.7.1 Phase 3・D-08 で解消」「v1.7.1 Phase 3・D-05/D-07」と記述しているが、`pagefolio/constants.py` の `APP_VERSION` は `"v1.7.0"` のまま、`開発履歴.md` の最新エントリも v1.7.0（Undo/Redo メモリ最適化）で止まっており、Phase 3 で追加された機能（画像透かし・mm指定トリミング・矢印微調整・crop_info mm表示・黒塗り/モザイクの連続適用/粒度スライダー/複数矩形一括適用）についての新規エントリが存在しない。README.md のバッジも v1.7.0 のまま。CLAUDE.md 自身の「変更時のチェックリスト」（バージョン番号更新・開発履歴追記）が未実施であり、"v1.7.0" と "v1.7.1" が混在する内部矛盾を生んでいる。

- **redact モードでのドラッグなしクリックが退化した0サイズ矩形を暗黙に蓄積する**: `pagefolio/page_ops.py` の `_crop_drag_end` は無条件に `self._crop_drag_move(event)` を呼び、これは `crop_drag_start`（ButtonPress 時点の座標）が設定されていれば実行される。ドラッグせずクリックのみ（Press→即 Release）だった場合、`crop_rect` は `(x, y, x, y)` という非 None の退化タプルになり、`if self.redact_mode and self.crop_rect:`（127行目台）の判定は空タプルではなく「非 None のタプル」を真と評価するため、この0サイズ矩形がそのまま `self._redact_rects` へ追加され、対応する0サイズのオーバーレイ矩形も生成される。適用時 (`_apply_page_edit`) は `_page_rect_from_rel` が幅/高さ1pt未満で `None` を返すため実害はなく最終的にスキップされるが、（1）crop モードの同型操作（`_crop_page`）は `new_rect.width < 1` 判定で `err_crop_small` をユーザーに通知するのに対し redact 側は無言で蓄積するという挙動非対称があり、（2）将来「N個の矩形を蓄積中」のようなカウンタ表示 UI を足す場合に誤カウントの温床になる。テストでもこのゼロドラッグクリックのケースは未カバー（`test_crop_drag_end_accumulates_multi_rect` は実ドラッグのみ検証）。

- **テスト用 FakeApp 定義の3ファイル重複**: `tests/test_pdf_ops.py::TestContentOpsUndoFix._make_app`、`tests/test_page_polish.py::_make_app`、`tests/test_v150_regression.py::TestTocPreservation._make_app` は同一の `FakeApp(FileOpsMixin, PageOpsMixin, RedactOpsMixin)` 定義をほぼそのままコピーしている（03-02-SUMMARY.md でも「コピー流用」と明記された意図的選択）。crossファイルの独立性を優先した判断は理解できるが、Mixin 側のコンストラクタ引数や `_check_doc`/`_get_targets` 等のインターフェースが将来変わった場合、3箇所を同期して修正する必要があり保守コストが高い。`tests/conftest.py` へ共有ファクトリ関数として抽出することを推奨する。

## Info（改善提案）

- `_add_watermark_image`（`pagefolio/page_ops.py`）の JPEG 均一透過値は `a.point(lambda v: int(v * 0.5))` により `int(255 * 0.5) = 127` となり、コメント/03-01-SUMMARY.md記載の「均一128(=50%)」とは実際には1違う（127/255≈49.8%）。実害はないが、`round()` を使えば意図通りの128になり、ドキュメントとの整合も取れる。
- `_mosaic_page`/`_redact_page`（`pagefolio/redact_ops.py`）は複数矩形適用時、同一ページに対して矩形の数だけ個別に `add_redact_annot`+`apply_redactions()` を呼ぶ（1回にバッチ化しない）。意図した設計（矩形ごとの確実な実削除）としては正しいが、矩形数が多い場合はやや非効率。将来的に全矩形を先に `add_redact_annot` してから `apply_redactions()` を1回だけ呼ぶ最適化の余地がある。
- 画像透かし（`_add_watermark_image`）は選択画像を元解像度のまま `insert_image` へ埋め込む（表示サイズは50%に縮小されるが、埋め込みバイト自体はダウンサンプリングされない）。非常に大きな画像（例: 8000×6000px）を選ぶと表示上は小さくても PDF ファイルサイズが大きく膨張し得る。
- `_apply_mosaic` が `settings.get("mosaic_block", MOSAIC_BLOCK)` から取得する値はスライダー（4〜32）経由なら安全域だが、`pagefolio_settings.json` を手動編集等で 0 や負値にされた場合、`_apply_page_edit` 側の `block or MOSAIC_BLOCK` は 0 のみフォールバックし、負値はフォールバックされないまま `_mosaic_page` の `max(1, img.width // block)` に渡る（クラッシュはしないが意図しない極端な粒度になる）。設定読み込み側で range バリデーションを追加すると堅牢性が上がる。
