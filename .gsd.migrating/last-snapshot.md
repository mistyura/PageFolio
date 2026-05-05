# GSD context snapshot (2026-05-04T05:06:55.099Z)

## Active context
Active: M001 / S04 / T05 - test_pdf_ops.py に TestBulkMoveLogic / TestBulkCropLogic テストを追加する

## Top project memories
- [MEM004] (architecture) PyMuPDF の fitz.Document は並行アクセス非対応のため、バックグラウンドスレッドでは専用インスタンスを fitz.open() で作成し finally ブロックで必ず close() する。self.doc を直接スレッドに渡してはならない。
- [MEM005] (gotcha) filepath=None の未保存結合 doc（合併後に保存前の状態）は fitz.open(filepath) できない。この場合は doc.tobytes() をメインスレッドで実行してバイト列に変換してからスレッドを起動し、スレッド内では fitz.open(stream=bytes, filetype='pdf') で開く。
- [MEM006] (pattern) バックグラウンドレンダリングの世代管理パターン: _preview_gen / _thumb_gen カウンターをインクリメントしてローカル変数 gen にコピーし、after(0, callback) でメインスレッドに戻った時点で gen != self._preview_gen なら stale として破棄する。ドキュメント入替時（_open_pdf_path / _do_open_merged / _restore_state）と UI 再構築時（_rebuild_ui）の両方でインクリメントすること。
- [MEM009] (gotcha) fitz.Rect（C 側オブジェクト）は Python 側でスタックに直接保持すると寿命管理の問題が生じる。Undo 差分データに cropbox を保存する際は fitz.Rect ではなくタプル (x0, y0, x1, y1) に変換して保存し、restore 時に fitz.Rect を再構築する。
- [MEM012] (gotcha) dnd.py の _dnd_drop() で _save_undo("move", src=src, actual_dest=actual_dest) を呼ぶタイミングは self.doc.move_page() の実行後かつ actual_dest 確定後でなければならない。actual_dest 未確定の位置で呼ぶと差分データに正しい移動先が記録されず Undo が壊れる。
- [MEM013] (gotcha) _rotate_selected()
…[truncated]
