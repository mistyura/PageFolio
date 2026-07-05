"""PDF 操作のテスト。
pagefolio.py のPDF操作ロジックは Tkinter に強く結合しているため、
fitz API を直接使ってアプリと同等の操作が正しく動くことを検証する。
"""

import os
from unittest.mock import patch

import fitz
import pytest

import pagefolio

# ===== PDF 読み込み =====


class TestPdfOpen:
    """PDF ファイルの読み込みテスト"""

    def test_open_valid_pdf(self, sample_pdf):
        """正常な PDF を開ける"""
        doc = fitz.open(sample_pdf)
        assert len(doc) == 3
        doc.close()

    def test_open_returns_correct_page_count(self, sample_pdf):
        """ページ数が正しい"""
        doc = fitz.open(sample_pdf)
        assert len(doc) == 3
        doc.close()

    def test_open_nonexistent_file_raises(self, tmp_path):
        """存在しないファイルを開くとエラー"""
        with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
            fitz.open(str(tmp_path / "nonexistent.pdf"))

    def test_page_text_content(self, sample_pdf):
        """各ページのテキスト内容が正しい"""
        doc = fitz.open(sample_pdf)
        for i in range(3):
            text = doc[i].get_text()
            assert f"Page {i + 1}" in text
        doc.close()


# ===== PDF 保存 =====


class TestPdfSave:
    """PDF ファイルの保存テスト"""

    def test_save_new_file(self, sample_pdf_doc, tmp_path):
        """新しいファイルとして保存できる"""
        save_path = str(tmp_path / "saved.pdf")
        sample_pdf_doc.save(save_path)
        assert os.path.exists(save_path)
        # 再度開いて検証
        doc2 = fitz.open(save_path)
        assert len(doc2) == 3
        doc2.close()

    def test_save_preserves_content(self, sample_pdf_doc, tmp_path):
        """保存後も内容が保持される"""
        save_path = str(tmp_path / "saved.pdf")
        sample_pdf_doc.save(save_path)
        doc2 = fitz.open(save_path)
        for i in range(3):
            text = doc2[i].get_text()
            assert f"Page {i + 1}" in text
        doc2.close()

    def test_incremental_save(self, sample_pdf, tmp_path):
        """incremental 保存（上書き保存のシミュレーション）"""
        import shutil

        copy_path = str(tmp_path / "copy.pdf")
        shutil.copy2(sample_pdf, copy_path)
        doc = fitz.open(copy_path)
        # 変更を加える
        doc[0].insert_text((72, 200), "Modified", fontsize=16)
        doc.save(copy_path, incremental=True, encryption=0)
        doc.close()
        # 再度開いて検証
        doc2 = fitz.open(copy_path)
        text = doc2[0].get_text()
        assert "Modified" in text
        doc2.close()


# ===== ページ回転 =====


class TestPageRotate:
    """ページ回転テスト（_rotate_selected と同等のロジック）"""

    def test_rotate_90(self, sample_pdf_doc):
        """90° 回転"""
        page = sample_pdf_doc[0]
        original = page.rotation
        page.set_rotation((original + 90) % 360)
        assert page.rotation == (original + 90) % 360

    def test_rotate_180(self, sample_pdf_doc):
        """180° 回転"""
        page = sample_pdf_doc[0]
        page.set_rotation(180)
        assert page.rotation == 180

    def test_rotate_360_returns_to_original(self, sample_pdf_doc):
        """360° 回転で元に戻る"""
        page = sample_pdf_doc[0]
        page.set_rotation(0)
        page.set_rotation((page.rotation + 360) % 360)
        assert page.rotation == 0

    def test_rotate_multiple_pages(self, sample_pdf_doc):
        """複数ページの回転"""
        targets = [0, 2]
        for i in targets:
            page = sample_pdf_doc[i]
            page.set_rotation((page.rotation + 90) % 360)
        assert sample_pdf_doc[0].rotation == 90
        assert sample_pdf_doc[1].rotation == 0  # 未変更
        assert sample_pdf_doc[2].rotation == 90


# ===== ページ削除 =====


class TestPageDelete:
    """ページ削除テスト（_delete_selected と同等のロジック）"""

    def test_delete_single_page(self, sample_pdf_doc):
        """1ページ削除"""
        sample_pdf_doc.delete_page(1)  # 2ページ目を削除
        assert len(sample_pdf_doc) == 2

    def test_delete_preserves_other_pages(self, sample_pdf_doc):
        """削除後に残りのページが正しい"""
        sample_pdf_doc.delete_page(1)
        text_0 = sample_pdf_doc[0].get_text()
        text_1 = sample_pdf_doc[1].get_text()
        assert "Page 1" in text_0
        assert "Page 3" in text_1

    def test_delete_multiple_pages_reverse_order(self, sample_pdf_doc):
        """複数ページを逆順で削除（アプリと同じロジック）"""
        targets = sorted([0, 2], reverse=True)
        for i in targets:
            sample_pdf_doc.delete_page(i)
        assert len(sample_pdf_doc) == 1
        assert "Page 2" in sample_pdf_doc[0].get_text()


# ===== ページ挿入 =====


class TestPageInsert:
    """ページ挿入テスト（_do_insert と同等のロジック）"""

    def test_insert_at_head(self, sample_pdf, multi_pdf_files):
        """先頭に挿入"""
        doc = fitz.open(sample_pdf)
        src = fitz.open(multi_pdf_files[0])  # 1ページ
        doc.insert_pdf(src, from_page=0, to_page=len(src) - 1, start_at=0)
        assert len(doc) == 4
        doc.close()
        src.close()

    def test_insert_at_tail(self, sample_pdf, multi_pdf_files):
        """末尾に挿入"""
        doc = fitz.open(sample_pdf)
        original_len = len(doc)
        src = fitz.open(multi_pdf_files[1])  # 2ページ
        doc.insert_pdf(src, from_page=0, to_page=len(src) - 1)
        assert len(doc) == original_len + 2
        doc.close()
        src.close()


# ===== PDF 結合 =====


class TestPdfMerge:
    """PDF 結合テスト（_do_merge と同等のロジック）"""

    def test_merge_multiple_files(self, sample_pdf, multi_pdf_files):
        """複数ファイルの結合"""
        doc = fitz.open(sample_pdf)
        total_added = 0
        for path in multi_pdf_files:
            src = fitz.open(path)
            doc.insert_pdf(src)
            total_added += len(src)
            src.close()
        # 元3ページ + file1(1) + file2(2) + file3(3) = 9ページ
        assert len(doc) == 3 + total_added
        assert len(doc) == 9
        doc.close()


# ===== PDF 分割 =====


class TestPdfSplit:
    """PDF 分割テスト（_split_by_range / _split_each_page と同等のロジック）"""

    def test_split_by_range(self, sample_pdf, tmp_path):
        """範囲指定分割"""
        doc = fitz.open(sample_pdf)
        # 1-2ページを抽出
        out = fitz.open()
        for page_num in range(0, 2):  # 0-indexed: page 1-2
            out.insert_pdf(doc, from_page=page_num, to_page=page_num)
        out_path = str(tmp_path / "split_1-2.pdf")
        out.save(out_path)
        out.close()

        # 検証
        result = fitz.open(out_path)
        assert len(result) == 2
        assert "Page 1" in result[0].get_text()
        assert "Page 2" in result[1].get_text()
        result.close()
        doc.close()

    def test_split_each_page(self, sample_pdf, tmp_path):
        """1ページずつ分割"""
        doc = fitz.open(sample_pdf)
        n = len(doc)
        for i in range(n):
            out = fitz.open()
            out.insert_pdf(doc, from_page=i, to_page=i)
            out_path = str(tmp_path / f"page_{i + 1:02d}.pdf")
            out.save(out_path)
            out.close()

        # 検証: 各ファイルが存在し1ページ
        for i in range(n):
            path = str(tmp_path / f"page_{i + 1:02d}.pdf")
            assert os.path.exists(path)
            result = fitz.open(path)
            assert len(result) == 1
            assert f"Page {i + 1}" in result[0].get_text()
            result.close()
        doc.close()

    def test_split_single_page_extraction(self, sample_pdf, tmp_path):
        """単一ページ抽出"""
        doc = fitz.open(sample_pdf)
        out = fitz.open()
        out.insert_pdf(doc, from_page=1, to_page=1)  # 2ページ目
        out_path = str(tmp_path / "page2.pdf")
        out.save(out_path)
        out.close()

        result = fitz.open(out_path)
        assert len(result) == 1
        assert "Page 2" in result[0].get_text()
        result.close()
        doc.close()


# ===== トリミング (CropBox) =====


class TestPageCrop:
    """ページトリミング（CropBox 設定）テスト"""

    def test_set_cropbox(self, sample_pdf_doc):
        """CropBox を設定できる"""
        page = sample_pdf_doc[0]
        mb = page.mediabox
        new_rect = fitz.Rect(
            mb.x0 + 50,
            mb.y0 + 50,
            mb.x1 - 50,
            mb.y1 - 50,
        )
        page.set_cropbox(new_rect)
        cb = page.cropbox
        assert abs(cb.x0 - new_rect.x0) < 1
        assert abs(cb.y0 - new_rect.y0) < 1

    def test_cropbox_within_mediabox(self, sample_pdf_doc):
        """CropBox は MediaBox 内に収まる（クランプロジック検証）"""
        page = sample_pdf_doc[0]
        mb = page.mediabox
        # アプリと同じクランプロジック
        eps = 0.01
        new_rect = fitz.Rect(
            max(round(100.0, 2), mb.x0 + eps),
            max(round(100.0, 2), mb.y0 + eps),
            min(round(400.0, 2), mb.x1 - eps),
            min(round(600.0, 2), mb.y1 - eps),
        )
        page.set_cropbox(new_rect)
        cb = page.cropbox
        assert cb.x0 >= mb.x0
        assert cb.y0 >= mb.y0
        assert cb.x1 <= mb.x1
        assert cb.y1 <= mb.y1

    def test_cropbox_reset(self, sample_pdf_doc):
        """CropBox をリセット（MediaBox に戻す）できる"""
        page = sample_pdf_doc[0]
        mb = page.mediabox
        # まずトリミング
        page.set_cropbox(fitz.Rect(50, 50, 400, 600))
        # リセット
        page.set_cropbox(mb)
        cb = page.cropbox
        assert abs(cb.x0 - mb.x0) < 1
        assert abs(cb.y0 - mb.y0) < 1

    def test_cropbox_too_small_is_detectable(self, sample_pdf_doc):
        """サイズが小さすぎるか検出可能"""
        # アプリ内では width < 1 or height < 1 で弾く
        tiny_rect = fitz.Rect(100, 100, 100.5, 100.5)
        assert tiny_rect.width < 1
        assert tiny_rect.height < 1


# ===== Undo/Redo ロジック =====


class TestUndoRedoLogic:
    """Undo/Redo 差分フォーマットのロジックテスト（操作タイプ別方式）"""

    def test_rotate_delta_roundtrip(self, sample_pdf_doc):
        """回転の差分保存と逆操作が正しく動作する"""
        doc = sample_pdf_doc
        original_rotation = doc[0].rotation  # 通常 0

        # 差分保存: 回転前の rotation を記録
        delta = {"op": "rotate", "data": [(0, doc[0].rotation)]}

        # 操作: 90度回転
        doc[0].set_rotation((doc[0].rotation + 90) % 360)
        assert doc[0].rotation == 90

        # Undo: 差分で復元
        for page_i, old_rot in delta["data"]:
            doc[page_i].set_rotation(old_rot)
        assert doc[0].rotation == original_rotation

    def test_delete_delta_roundtrip(self, sample_pdf_doc):
        """削除の差分保存と逆操作（ページ復元）が正しく動作する"""
        doc = sample_pdf_doc
        original_count = len(doc)  # 3ページ

        # 差分保存: 削除対象ページをバイト列で保存（昇順）
        targets = sorted([0])  # ページ0を削除
        delta_data = []
        for i in targets:
            tmp = fitz.open()
            tmp.insert_pdf(doc, from_page=i, to_page=i)
            delta_data.append((i, tmp.tobytes()))
            tmp.close()

        # 操作: ページ削除
        doc.delete_page(0)
        assert len(doc) == original_count - 1

        # Undo: 昇順で再挿入
        for page_i, page_bytes in delta_data:
            tmp = fitz.open(stream=page_bytes, filetype="pdf")
            doc.insert_pdf(tmp, start_at=page_i)
            tmp.close()
        assert len(doc) == original_count
        assert "Page 1" in doc[0].get_text()

    def test_restore_state_no_pdf_bytes_key(self):
        """_restore_state は pdf_bytes キーを含まない op 別 state を受け付ける"""
        # op 別 state（対称デルタ方式）: pdf_bytes キーなし
        state = {
            "op": "rotate",
            "current_page": 0,
            "selected_pages": set(),
            "data": [(0, 0)],
        }
        # pdf_bytes キーが存在しないことを確認
        assert "pdf_bytes" not in state

    def test_restore_state_returns_inverse_delta(self):
        """_restore_state が逆デルタ dict を返す（pdf_bytes キーなし）"""
        import collections

        import fitz

        import pagefolio.file_ops as fo

        # FileOpsMixin のメソッドを Mixin として使う簡易スタブ
        class FakeApp(fo.FileOpsMixin):
            def __init__(self, doc):
                self.doc = doc
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque()
                self._redo_stack = collections.deque()
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

        doc = fitz.open()
        for i in range(3):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)

        app = FakeApp(doc)
        # rotate op の逆デルタ取得テスト
        # 90 度回転を適用済みと仮定し undo state を構築
        app.doc[0].set_rotation(90)
        state = {
            "op": "rotate",
            "current_page": 0,
            "selected_pages": set(),
            "data": [(0, 0)],  # 元の rotation=0 に戻す
        }

        inverse = app._restore_state(state)
        # 逆デルタが返されること（dict 型）
        assert isinstance(inverse, dict)
        # pdf_bytes キーを含まないこと
        assert "pdf_bytes" not in inverse
        # op キーを持つこと
        assert "op" in inverse
        # 回転が元に戻っていること
        assert app.doc[0].rotation == 0
        doc.close()


# ===== insert/merge Undo→Redo ラウンドトリップ =====


class TestInsertMergeUndoRedo:
    """insert/merge の do→undo→redo ラウンドトリップ検証（Task 2 対応）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin を使う FakeApp を生成する"""
        import collections

        import pagefolio.file_ops as fo

        class FakeApp(fo.FileOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque()
                self._redo_stack = collections.deque()
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        return FakeApp(doc)

    def test_insert_undo_removes_inserted_pages(self, sample_pdf_doc, multi_pdf_files):
        """insert → undo で挿入ページが除去され元のページ数に戻る（BUG-01）"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3

        # insert op を _save_undo で記録（insert_at=1, num=0 → 書き戻し後に1）
        app._save_undo("insert", insert_at=1)
        # 実際の挿入（1ページを位置1に）
        src = fitz.open(multi_pdf_files[0])  # 1ページ
        app.doc.insert_pdf(src, start_at=1)
        src.close()
        # 書き戻し
        app._undo_stack[-1]["data"][1] = 1
        assert len(app.doc) == original_count + 1

        # Undo: 挿入ページが除去される
        app._undo()
        assert len(app.doc) == original_count

    def test_insert_undo_redo_roundtrip(self, sample_pdf_doc, multi_pdf_files):
        """insert → undo → redo でページ内容ごと往復する"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        insert_at = 1

        # insert op
        app._save_undo("insert", insert_at=insert_at)
        src = fitz.open(multi_pdf_files[0])  # "File1 Page1" が含まれる1ページ
        app.doc.insert_pdf(src, start_at=insert_at)
        src.close()
        app._undo_stack[-1]["data"][1] = 1
        assert len(app.doc) == original_count + 1

        # Undo
        app._undo()
        assert len(app.doc) == original_count
        # redo スタックに逆デルタが積まれていること
        assert len(app._redo_stack) == 1

        # Redo: 挿入ページが内容ごと復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        # 挿入位置のページに "File1 Page1" テキストが含まれること
        assert "File1 Page1" in app.doc[insert_at].get_text()

    def test_merge_resize_no_pdf_bytes_in_undo_stack(self):
        """_do_merge_resize が pdf_bytes キーを持たない state を undo スタックに積む"""
        import collections

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self):
                doc = fitz.open()
                for _ in range(4):
                    doc.new_page(width=595, height=842)
                self.doc = doc
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque()
                self._redo_stack = collections.deque()
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

            def plugin_manager(self):
                pass

        app = FakeApp()
        # ダミー plugin_manager
        import types

        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        targets = [0, 1]
        app._do_merge_resize(targets, "horizontal", 1190, 842)

        # undo スタックに pdf_bytes キーが含まれないこと
        assert len(app._undo_stack) > 0
        for entry in app._undo_stack:
            assert "pdf_bytes" not in entry, f"pdf_bytes が残存: {entry.keys()}"


# ===== 挿入 Undo/Redo 内容同一性検証 =====


def _page_digest(page):
    """ページのテキスト内容から digest を返す（D-07 内容同一性用）。
    fitz.Page を受け取り、get_text() の文字列を返す。
    sample_pdf_doc/multi_pdf_files は "Page N" / "File1 PageM" 形式のテキストを持つため
    テキストベースの同一性検証が確実・高速。
    """
    return page.get_text().strip()


class TestInsertUndoRedo:
    """挿入 Undo/Redo の内容同一性・往復検証（TEST-01 / D-07）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin を使う FakeApp を生成する"""
        import collections

        import pagefolio.file_ops as fo

        class FakeApp(fo.FileOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        return FakeApp(doc)

    def test_insert_undo_restores_page_count(self, sample_pdf_doc, multi_pdf_files):
        """insert → undo で len(doc) が元に戻る（BUG-01 ページ数検証）"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3

        # insert: 2ページ PDF を位置1に挿入
        app._save_undo("insert", insert_at=1)
        src = fitz.open(multi_pdf_files[1])  # 2ページ
        app.doc.insert_pdf(src, start_at=1)
        src.close()
        app._undo_stack[-1]["data"][1] = 2
        assert len(app.doc) == original_count + 2

        # Undo: ページ数が元に戻る
        app._undo()
        assert len(app.doc) == original_count

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._redo_stack:
            assert "pdf_bytes" not in entry

    def test_insert_undo_restores_content(self, sample_pdf_doc, multi_pdf_files):
        """insert → undo 後の残ページ digest が挿入前と一致する（D-07 内容同一性）"""
        app = self._make_fake_app(sample_pdf_doc)

        # 挿入前のページ digest を記録
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # insert: 1ページを位置2に挿入
        app._save_undo("insert", insert_at=2)
        src = fitz.open(multi_pdf_files[0])  # 1ページ: "File1 Page1"
        app.doc.insert_pdf(src, start_at=2)
        src.close()
        app._undo_stack[-1]["data"][1] = 1

        # Undo
        app._undo()

        # 残ページの digest が挿入前と一致する
        after_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_digests

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._redo_stack:
            assert "pdf_bytes" not in entry

    def test_insert_undo_redo_roundtrip(self, sample_pdf_doc, multi_pdf_files):
        """do→undo→redo で len と挿入ページ digest が一致する（D-07 redo 往復）"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        insert_at = 1

        # 挿入前の全ページ digest を記録
        before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # insert: 1ページを位置1に挿入（"File1 Page1" テキストを持つ）
        app._save_undo("insert", insert_at=insert_at)
        src = fitz.open(multi_pdf_files[0])  # 1ページ
        inserted_digest = _page_digest(src[0])
        app.doc.insert_pdf(src, start_at=insert_at)
        src.close()
        app._undo_stack[-1]["data"][1] = 1
        assert len(app.doc) == original_count + 1

        # 挿入後の挿入ページ digest を確認
        assert _page_digest(app.doc[insert_at]) == inserted_digest

        # Undo
        app._undo()
        assert len(app.doc) == original_count
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert before_digests == after_undo_digests

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._redo_stack:
            assert "pdf_bytes" not in entry

        # Redo: 挿入ページが内容ごと復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[insert_at]) == inserted_digest

        # Undo/Redo state に pdf_bytes キーが生成されないこと（D-05）
        for entry in app._undo_stack:
            assert "pdf_bytes" not in entry


# ===== 全 op 最小 do→undo→redo 往復テスト（安全網）=====


class TestAllOpsUndoRedoRoundtrip:
    """全 op（rotate/delete/move/duplicate/merge/bulk_move/bulk_crop/merge_resize）
    の最小 do→undo→redo 往復検証（Deferred 安全網 / D-04/D-05 整合）"""

    def _make_fake_app(self, doc):
        """FileOpsMixin を使う FakeApp を生成する"""
        import collections

        import pagefolio.file_ops as fo

        class FakeApp(fo.FileOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        return FakeApp(doc)

    def _make_full_fake_app(self, doc):
        """FileOpsMixin + PageOpsMixin を使う FakeApp を生成する"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_rotate_roundtrip(self, sample_pdf_doc):
        """rotate: 90度回転 → undo で 0 → redo で 90（rotation 属性で検証）"""
        app = self._make_fake_app(sample_pdf_doc)
        targets = [0]
        original_rot = app.doc[0].rotation  # 0

        # do: 90度回転
        app._save_undo("rotate", targets=targets)
        app.doc[0].set_rotation((app.doc[0].rotation + 90) % 360)
        assert app.doc[0].rotation == 90

        # undo
        app._undo()
        assert app.doc[0].rotation == original_rot

        # redo
        app._redo()
        assert app.doc[0].rotation == 90

        # pdf_bytes キーなし
        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_delete_roundtrip(self, sample_pdf_doc):
        """delete: 1ページ削除 → undo で復元（digest 一致）→ redo で再削除"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        target_digest = _page_digest(app.doc[1])

        # do: ページ1を削除
        targets = sorted([1], reverse=True)
        app._save_undo("delete", targets=targets)
        app.doc.delete_page(1)
        assert len(app.doc) == original_count - 1

        # undo: ページが復元される
        app._undo()
        assert len(app.doc) == original_count
        assert _page_digest(app.doc[1]) == target_digest

        # redo: 再削除
        app._redo()
        assert len(app.doc) == original_count - 1

        # undo/redo エントリのトップレベルキーに pdf_bytes がないことを確認
        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    @pytest.mark.parametrize("src,dest", [(0, 2), (0, 3), (2, 0), (1, 3)])
    def test_move_roundtrip(self, sample_pdf_doc, src, dest):
        """move: 実 dnd 規約（actual_dest=最終位置, 末尾ドロップ dest>=n 含む）で
        do→undo で元順序、redo で移動後順序に戻ることを検証（CR-01 回帰防止）。"""
        app = self._make_fake_app(sample_pdf_doc)
        original_order = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # do: _save_undo は操作前に実 actual_dest を保存する必要があるため先に算出
        n = len(app.doc)
        actual_dest = (n - 1) if dest >= n else (dest if dest < src else dest - 1)
        app._save_undo("move", src=src, actual_dest=actual_dest)
        if dest >= n:
            app.doc.move_page(src, -1)
        else:
            app.doc.move_page(src, dest)
        moved_order = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert moved_order != original_order

        # undo: 元の順序に戻る
        app._undo()
        after_undo = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_undo == original_order

        # redo: 移動後の順序に戻る
        app._redo()
        after_redo = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_redo == moved_order

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_duplicate_roundtrip(self, sample_pdf_doc):
        """duplicate: ページ1複製 → undo で元ページ数 → redo で複製ページ復元"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3
        pno = 1
        src_digest = _page_digest(app.doc[pno])

        # do: ページ1を複製
        app._save_undo("duplicate", pno=pno)
        tmp = fitz.open()
        tmp.insert_pdf(app.doc, from_page=pno, to_page=pno)
        app.doc.insert_pdf(tmp, start_at=pno + 1)
        tmp.close()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[pno + 1]) == src_digest

        # undo: 複製ページが削除される
        app._undo()
        assert len(app.doc) == original_count

        # redo: 複製ページが復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[pno + 1]) == src_digest

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_merge_roundtrip(self, sample_pdf_doc, multi_pdf_files):
        """merge: 1ページ PDF を結合 → undo でページ数復元 → redo で再結合"""
        app = self._make_fake_app(sample_pdf_doc)
        original_count = len(app.doc)  # 3

        # do: 1ページ PDF を結合（末尾に追加）
        app._save_undo("merge")
        src = fitz.open(multi_pdf_files[0])  # 1ページ: "File1 Page1"
        merged_digest = _page_digest(src[0])
        app.doc.insert_pdf(src)
        src.close()
        assert len(app.doc) == original_count + 1

        # undo: 結合ページが除去される
        app._undo()
        assert len(app.doc) == original_count

        # redo: 結合ページが内容ごと復元される
        app._redo()
        assert len(app.doc) == original_count + 1
        assert _page_digest(app.doc[original_count]) == merged_digest

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_bulk_move_roundtrip(self, sample_pdf_doc):
        """bulk_move: ページ順序変更 → undo で元順序 → redo で変更後順序"""
        app = self._make_fake_app(sample_pdf_doc)
        original_order = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

        # do: new_order = [2, 0, 1] (ページ2を先頭に)
        new_order = [2, 0, 1]
        app._save_undo("bulk_move", new_order=new_order)
        app.doc.select(new_order)
        reordered = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert reordered != original_order

        # undo: 元の順序に戻る
        app._undo()
        after_undo = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_undo == original_order

        # redo: 変更後の順序に戻る
        app._redo()
        after_redo = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert after_redo == reordered

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_bulk_crop_roundtrip(self, sample_pdf_doc):
        """bulk_crop: 複数ページ cropbox 設定 → undo で元 cropbox → redo で新 cropbox"""
        app = self._make_fake_app(sample_pdf_doc)
        targets = [0, 1]

        # 元の cropbox を記録
        original_cropboxes = [
            (
                app.doc[i].cropbox.x0,
                app.doc[i].cropbox.y0,
                app.doc[i].cropbox.x1,
                app.doc[i].cropbox.y1,
            )
            for i in targets
        ]

        # do: cropbox を縮小
        crop_data = [
            (i, (cb[0], cb[1], cb[2], cb[3]))
            for i, cb in zip(targets, original_cropboxes, strict=True)
        ]
        app._save_undo("bulk_crop", crop_data=crop_data)
        for i in targets:
            mb = app.doc[i].mediabox
            new_rect = fitz.Rect(mb.x0 + 20, mb.y0 + 20, mb.x1 - 20, mb.y1 - 20)
            app.doc[i].set_cropbox(new_rect)
        new_cropboxes = [
            (
                app.doc[i].cropbox.x0,
                app.doc[i].cropbox.y0,
                app.doc[i].cropbox.x1,
                app.doc[i].cropbox.y1,
            )
            for i in targets
        ]

        # undo: 元の cropbox に戻る
        app._undo()
        after_undo_cropboxes = [
            (
                app.doc[i].cropbox.x0,
                app.doc[i].cropbox.y0,
                app.doc[i].cropbox.x1,
                app.doc[i].cropbox.y1,
            )
            for i in targets
        ]
        for orig, after in zip(original_cropboxes, after_undo_cropboxes, strict=True):
            for o, a in zip(orig, after, strict=True):
                assert abs(o - a) < 1.0

        # redo: 縮小後の cropbox に戻る
        app._redo()
        after_redo_cropboxes = [
            (
                app.doc[i].cropbox.x0,
                app.doc[i].cropbox.y0,
                app.doc[i].cropbox.x1,
                app.doc[i].cropbox.y1,
            )
            for i in targets
        ]
        for new_cb, after in zip(new_cropboxes, after_redo_cropboxes, strict=True):
            for n, a in zip(new_cb, after, strict=True):
                assert abs(n - a) < 1.0

        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_merge_resize_roundtrip(self):
        """merge_resize: A4×2 を A3 に結合 → undo で元ページ復元 → redo で再結合"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin):
            MAX_UNDO = 20

            def __init__(self):
                doc = fitz.open()
                for i in range(3):
                    p = doc.new_page(width=595, height=842)
                    p.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
                self.doc = doc
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.lang = "ja"

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp()
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        original_count = len(app.doc)  # 3
        original_digests = [_page_digest(app.doc[i]) for i in range(original_count)]

        # do: ページ0,1を横並びで結合（A3 サイズ）
        targets = [0, 1]
        app._do_merge_resize(targets, "horizontal", 1190, 842)
        # 元3ページ - 2ページ + 1ページ = 2ページ
        assert len(app.doc) == original_count - 1
        # 結合ページのサイズが A3 になっていること
        assert abs(app.doc[0].rect.width - 1190) < 1

        # undo: 元のページ構成に戻る
        app._undo()
        assert len(app.doc) == original_count
        after_undo_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]
        assert original_digests == after_undo_digests

        # redo: 結合後の状態に戻る
        app._redo()
        assert len(app.doc) == original_count - 1
        assert abs(app.doc[0].rect.width - 1190) < 1

        # pdf_bytes キーなし
        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry


# ===== bulk_move ロジック =====


class TestBulkMoveLogic:
    """bulk_move: doc.select() の逆順列ラウンドトリップ検証"""

    def test_bulk_move_select_roundtrip(self, sample_pdf_doc):
        """doc.select(new_order) → 逆順列で doc.select(inverse) → 元の順序に戻る"""
        doc = sample_pdf_doc  # 3ページ: Page 1, Page 2, Page 3
        # ページ 0 と 2 を選択し、末尾に移動する new_order = [1, 0, 2]
        new_order = [1, 0, 2]
        doc.select(new_order)
        assert "Page 2" in doc[0].get_text()
        # 逆順列を計算
        inverse = [0] * len(new_order)
        for i, v in enumerate(new_order):
            inverse[v] = i
        doc.select(inverse)
        assert "Page 1" in doc[0].get_text()
        assert "Page 2" in doc[1].get_text()
        assert "Page 3" in doc[2].get_text()

    def test_bulk_move_new_order_construction(self, sample_pdf_doc):
        """selected_pages + dest から new_order が正しく構築される"""
        doc = sample_pdf_doc  # 3ページ
        n = len(doc)
        selected_pages = {0, 2}  # ページ 0 と 2 を選択
        dest = 3  # 末尾にドロップ
        sorted_sel = sorted(selected_pages)
        non_selected = [p for p in range(n) if p not in selected_pages]
        sel_before_dest = sum(1 for p in selected_pages if p < dest)
        adj_dest = dest - sel_before_dest
        adj_dest = max(0, min(adj_dest, len(non_selected)))
        new_order = non_selected[:adj_dest] + sorted_sel + non_selected[adj_dest:]
        # new_order は permutation
        assert sorted(new_order) == list(range(n))
        # non_selected (page 1) が先頭、選択ページが末尾
        assert new_order == [1, 0, 2]


# ===== bulk_crop ロジック =====


class TestBulkCropLogic:
    """bulk_crop: 複数ページ cropbox ラウンドトリップ検証"""

    def test_bulk_crop_multi_page_roundtrip(self, sample_pdf_doc):
        """複数ページに cropbox 適用 → 旧データで全ページ復元できる"""
        doc = sample_pdf_doc
        targets = [0, 1, 2]
        # 旧 cropbox を保存（Undo データ構築と同じ）
        crop_data = []
        for i in targets:
            cb = doc[i].cropbox
            crop_data.append((i, (cb.x0, cb.y0, cb.x1, cb.y1)))
        # 各ページにトリミング適用
        for i in targets:
            page = doc[i]
            mb = page.mediabox
            new_rect = fitz.Rect(mb.x0 + 20, mb.y0 + 20, mb.x1 - 20, mb.y1 - 20)
            page.set_cropbox(new_rect)
            assert doc[i].cropbox.x0 > crop_data[i][1][0]
        # Undo: 旧 cropbox で復元（_restore_state の bulk_crop ロジックと同等）
        for page_i, (x0, y0, x1, y1) in crop_data:
            doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))
        for i in targets:
            cb = doc[i].cropbox
            assert abs(cb.x0 - crop_data[i][1][0]) < 1
            assert abs(cb.y0 - crop_data[i][1][1]) < 1

    def test_bulk_crop_relative_coords(self, sample_pdf_doc):
        """相対座標変換: 異なる mediabox サイズのページでも比率が保たれる"""
        doc = sample_pdf_doc
        # current_page (0) の mediabox で相対比率を計算
        cur_mb = doc[0].mediabox
        # 中央 50% の領域を選択したとする
        x0_pdf, y0_pdf = cur_mb.width * 0.1, cur_mb.height * 0.1
        x1_pdf, y1_pdf = cur_mb.width * 0.9, cur_mb.height * 0.9
        rel = (
            x0_pdf / cur_mb.width,
            y0_pdf / cur_mb.height,
            x1_pdf / cur_mb.width,
            y1_pdf / cur_mb.height,
        )
        # 同じ比率を別ページに適用
        for i in [0, 1, 2]:
            mb = doc[i].mediabox
            new_x0 = mb.x0 + rel[0] * mb.width
            new_y0 = mb.y0 + rel[1] * mb.height
            new_x1 = mb.x0 + rel[2] * mb.width
            new_y1 = mb.y0 + rel[3] * mb.height
            # 比率が保たれている（X 軸・Y 軸ともに）
            assert abs((new_x0 - mb.x0) / mb.width - rel[0]) < 0.001
            assert abs((new_x1 - mb.x0) / mb.width - rel[2]) < 0.001
            assert abs((new_y0 - mb.y0) / mb.height - rel[1]) < 0.001
            assert abs((new_y1 - mb.y0) / mb.height - rel[3]) < 0.001


# ===== _check_split_overwrite =====


class TestCheckSplitOverwrite:
    """_check_split_overwrite のモックテスト。

    Tkinter の messagebox.askyesno に依存するメソッドを
    モック置換してロジック部分を検証する。
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        """テスト用の簡易オブジェクト"""

        class FakeApp:
            def _t(self, key):
                return key

        self.app = FakeApp()
        self.app._check_split_overwrite = (
            pagefolio.PDFEditorApp._check_split_overwrite.__get__(self.app)
        )

    def test_no_existing_files_returns_true(self, tmp_path):
        """同名ファイルが存在しなければ True を返す（ダイアログ不要）"""
        result = self.app._check_split_overwrite(str(tmp_path), ["a.pdf", "b.pdf"])
        assert result is True

    @patch("pagefolio.page_ops.messagebox.askyesno", return_value=True)
    def test_existing_files_user_accepts(self, mock_ask, tmp_path):
        """同名ファイルが存在し、ユーザーが Yes を選択 → True"""
        (tmp_path / "a.pdf").write_text("dummy")
        result = self.app._check_split_overwrite(str(tmp_path), ["a.pdf", "b.pdf"])
        assert result is True
        mock_ask.assert_called_once()

    @patch("pagefolio.page_ops.messagebox.askyesno", return_value=False)
    def test_existing_files_user_declines(self, mock_ask, tmp_path):
        """同名ファイルが存在し、ユーザーが No を選択 → False"""
        (tmp_path / "a.pdf").write_text("dummy")
        result = self.app._check_split_overwrite(str(tmp_path), ["a.pdf", "b.pdf"])
        assert result is False
        mock_ask.assert_called_once()


# ===== ページ結合・リサイズ =====


class TestMergeResizeLogic:
    """ページ結合・リサイズロジックのテスト (v1.1.0)"""

    def test_horizontal_merge_two_a4_to_a3(self):
        """A4 縦×2 を横並びで結合すると A3 横サイズになる"""
        doc = fitz.open()
        for _ in range(2):
            doc.new_page(width=595, height=842)  # A4 portrait

        targets = [0, 1]
        rects = [doc[i].rect for i in targets]
        out_w = sum(r.width for r in rects)
        out_h = max(r.height for r in rects)

        new_doc = fitz.open()
        new_page = new_doc.new_page(width=out_w, height=out_h)
        offset = 0.0
        for src_pno in targets:
            r = doc[src_pno].rect
            new_page.show_pdf_page(
                fitz.Rect(offset, 0, offset + r.width, r.height), doc, src_pno
            )
            offset += r.width

        assert new_page.rect.width == 1190
        assert new_page.rect.height == 842
        assert len(new_doc) == 1
        new_doc.close()
        doc.close()

    def test_vertical_merge_two_a4(self):
        """A4 縦×2 を縦並びで結合すると幅 595 / 高さ 1684 になる"""
        doc = fitz.open()
        for _ in range(2):
            doc.new_page(width=595, height=842)

        targets = [0, 1]
        rects = [doc[i].rect for i in targets]
        out_w = max(r.width for r in rects)
        out_h = sum(r.height for r in rects)

        new_doc = fitz.open()
        new_page = new_doc.new_page(width=out_w, height=out_h)
        offset = 0.0
        for src_pno in targets:
            r = doc[src_pno].rect
            new_page.show_pdf_page(
                fitz.Rect(0, offset, r.width, offset + r.height), doc, src_pno
            )
            offset += r.height

        assert new_page.rect.width == 595
        assert new_page.rect.height == 1684
        new_doc.close()
        doc.close()

    def test_merge_replaces_originals(self):
        """結合実行で元ページは削除され、合計ページ数が想定通り減る"""
        doc = fitz.open()
        for i in range(4):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), f"P{i + 1}", fontsize=20)
        targets = [1, 2]

        # 結合後の new_page を doc に挿入
        rects = [doc[i].rect for i in targets]
        new_doc = fitz.open()
        new_page = new_doc.new_page(
            width=sum(r.width for r in rects),
            height=max(r.height for r in rects),
        )
        offset = 0.0
        for src_pno in targets:
            r = doc[src_pno].rect
            new_page.show_pdf_page(
                fitz.Rect(offset, 0, offset + r.width, r.height), doc, src_pno
            )
            offset += r.width

        insert_at = targets[0]
        doc.insert_pdf(new_doc, start_at=insert_at)
        new_doc.close()
        for i in sorted(targets, reverse=True):
            doc.delete_page(i + 1)

        # 元 4 ページ - 2 ページ + 1 ページ = 3 ページ
        assert len(doc) == 3
        # 挿入位置に結合ページが入っている
        assert doc[insert_at].rect.width == 1190
        doc.close()

    def test_three_a4_horizontal_merge(self):
        """A4 縦×3 を横並びで結合すると 1785×842 になる"""
        doc = fitz.open()
        for _ in range(3):
            doc.new_page(width=595, height=842)

        targets = [0, 1, 2]
        rects = [doc[i].rect for i in targets]
        out_w = sum(r.width for r in rects)
        out_h = max(r.height for r in rects)
        assert out_w == 595 * 3
        assert out_h == 842
        doc.close()

    def test_mixed_sizes_horizontal(self):
        """サイズが異なるページを横並びで結合（高さは最大値）"""
        doc = fitz.open()
        doc.new_page(width=595, height=842)  # A4
        doc.new_page(width=420, height=595)  # A5
        targets = [0, 1]
        rects = [doc[i].rect for i in targets]
        out_w = sum(r.width for r in rects)
        out_h = max(r.height for r in rects)
        assert out_w == 595 + 420
        assert out_h == 842
        doc.close()


class TestPageEditRedactMosaic:
    """page_edit op（黒塗り・モザイク）の undo/redo 往復と適用ロジックの検証"""

    def _make_fake_app(self, doc):
        """FileOpsMixin + RedactOpsMixin を使う FakeApp を生成する"""
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.redact_ops as ro

        class FakeApp(fo.FileOpsMixin, ro.RedactOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_page_edit_roundtrip(self, sample_pdf_doc):
        """page_edit: 黒塗り → undo で復元（digest 一致）→ redo で再黒塗り"""
        from pagefolio.redact_ops import RedactOpsMixin

        app = self._make_fake_app(sample_pdf_doc)
        before_digest = _page_digest(app.doc[0])
        assert "Page 1" in app.doc[0].get_text()

        # do: 黒塗り適用（テキストを覆う矩形）
        app._save_undo("page_edit", targets=[0])
        RedactOpsMixin._redact_page(app.doc[0], fitz.Rect(60, 50, 300, 110))
        assert "Page 1" not in app.doc[0].get_text()
        after_digest = _page_digest(app.doc[0])

        # undo: ページ内容が完全に復元される
        app._undo()
        assert len(app.doc) == 3
        assert "Page 1" in app.doc[0].get_text()
        assert _page_digest(app.doc[0]) == before_digest

        # redo: 黒塗りが再適用される
        app._redo()
        assert "Page 1" not in app.doc[0].get_text()
        assert _page_digest(app.doc[0]) == after_digest

        # 二往復目も安定（対称 op の入れ替わり検証）
        app._undo()
        assert _page_digest(app.doc[0]) == before_digest

        # pdf_bytes キーなし（op 別デルタ不変条件）
        for entry in list(app._undo_stack) + list(app._redo_stack):
            assert "pdf_bytes" not in entry

    def test_page_edit_multi_page(self, sample_pdf_doc):
        """page_edit: 複数ページ一括適用 → undo で全ページ復元"""
        from pagefolio.redact_ops import RedactOpsMixin

        app = self._make_fake_app(sample_pdf_doc)
        digests = [_page_digest(app.doc[i]) for i in range(3)]

        app._save_undo("page_edit", targets=[0, 1, 2])
        for i in range(3):
            RedactOpsMixin._redact_page(app.doc[i], fitz.Rect(60, 50, 300, 110))
            assert f"Page {i + 1}" not in app.doc[i].get_text()

        app._undo()
        for i in range(3):
            assert _page_digest(app.doc[i]) == digests[i]
            assert f"Page {i + 1}" in app.doc[i].get_text()

    def test_redact_removes_text_permanently(self, sample_pdf_doc):
        """黒塗りは保存後もテキストが復元不能（真の墨消し）"""
        from pagefolio.redact_ops import RedactOpsMixin

        doc = sample_pdf_doc
        RedactOpsMixin._redact_page(doc[0], fitz.Rect(60, 50, 300, 110))
        # 保存 → 再オープンしても消えている
        reopened = fitz.open(stream=doc.tobytes(), filetype="pdf")
        assert "Page 1" not in reopened[0].get_text()
        reopened.close()

    def test_mosaic_removes_text_and_inserts_image(self, sample_pdf_doc):
        """モザイクは下地テキストを実削除し、ピクセル化画像を焼き込む"""
        from pagefolio.redact_ops import RedactOpsMixin

        page = sample_pdf_doc[0]
        n_before = len(page.get_images(full=True))
        RedactOpsMixin._mosaic_page(page, fitz.Rect(60, 50, 300, 110))
        assert "Page 1" not in page.get_text()
        assert len(page.get_images(full=True)) > n_before

    def test_page_rect_from_rel_clamp(self, sample_pdf_doc):
        """相対座標→ページ矩形変換: mediabox クランプと空・微小の除外"""
        from pagefolio.redact_ops import RedactOpsMixin

        page = sample_pdf_doc[0]  # 595x842
        r = RedactOpsMixin._page_rect_from_rel(page, (0.1, 0.1, 0.5, 0.2))
        assert r is not None
        assert abs(r.x0 - 59.5) < 0.01
        assert abs(r.y1 - 168.4) < 0.01

        # 空矩形 → None
        assert RedactOpsMixin._page_rect_from_rel(page, (0.5, 0.5, 0.5, 0.5)) is None
        # ページ外にはみ出す指定はクランプされる
        r2 = RedactOpsMixin._page_rect_from_rel(page, (-0.5, -0.5, 1.5, 1.5))
        assert r2 is not None
        assert r2.x0 == 0 and r2.y0 == 0
        assert r2.x1 == 595 and r2.y1 == 842


class TestContentOpsUndoFix:
    """insert_blank / watermark / page_numbers の undo no-op バグ修正（v1.7.0）。

    旧実装は _save_undo に存在しない op 名を渡しており、undo しても何も
    起こらなかった。insert_blank は既存 insert op、watermark / page_numbers
    は page_edit op へ置き換えて undo/redo 往復を検証する。
    """

    def _make_app(self, doc):
        import collections
        import types

        import pagefolio.file_ops as fo
        import pagefolio.page_ops as po
        import pagefolio.redact_ops as ro

        class FakeApp(fo.FileOpsMixin, po.PageOpsMixin, ro.RedactOpsMixin):
            MAX_UNDO = 20

            def __init__(self, d):
                self.doc = d
                self.current_page = 0
                self.selected_pages = set()
                self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
                self._preview_gen = 0
                self._thumb_gen = 0
                self.root = None

            def _check_doc(self):
                return self.doc is not None

            def _get_targets(self):
                return sorted(self.selected_pages) or [self.current_page]

            def _invalidate_thumb_cache(self, *a, **kw):
                pass

            def _refresh_all(self):
                pass

            def _t(self, key):
                return key

            def _set_status(self, *a):
                pass

        app = FakeApp(doc)
        app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
        return app

    def test_insert_blank_roundtrip(self, sample_pdf_doc):
        """白紙挿入 → undo でページ数が戻る → redo で再挿入"""
        app = self._make_app(sample_pdf_doc)
        app.current_page = 0
        app._insert_blank_page()
        assert len(app.doc) == 4
        assert app.doc[1].get_text().strip() == ""  # 白紙
        # 白紙ページは元ページ（A4 595×842）とサイズ一致（D-14）
        assert app.doc[1].rect.width == app.doc[0].rect.width
        assert app.doc[1].rect.height == app.doc[0].rect.height

        app._undo()
        assert len(app.doc) == 3
        assert "Page 2" in app.doc[1].get_text()

        app._redo()
        assert len(app.doc) == 4
        assert app.doc[1].get_text().strip() == ""
        assert app.doc[1].rect.width == app.doc[0].rect.width
        assert app.doc[1].rect.height == app.doc[0].rect.height

    def test_watermark_roundtrip(self, sample_pdf_doc, monkeypatch):
        """透かし追加 → undo でテキストが消える → redo で再追加"""
        import pagefolio.page_ops as po

        app = self._make_app(sample_pdf_doc)
        app.selected_pages = {0, 1}
        monkeypatch.setattr(
            po.simpledialog, "askstring", lambda *a, **kw: "CONFIDENTIAL"
        )
        app._add_watermark_text()
        assert "CONFIDENTIAL" in app.doc[0].get_text()
        assert "CONFIDENTIAL" in app.doc[1].get_text()
        assert "CONFIDENTIAL" not in app.doc[2].get_text()

        app._undo()
        for i in range(3):
            assert "CONFIDENTIAL" not in app.doc[i].get_text()
        assert "Page 1" in app.doc[0].get_text()  # 元の内容は保持
        assert "Page 2" in app.doc[1].get_text()  # 両選択ページとも元テキスト保持
        assert "Page 3" in app.doc[2].get_text()  # 未選択ページも不変

        app._redo()
        assert "CONFIDENTIAL" in app.doc[0].get_text()
        assert "CONFIDENTIAL" in app.doc[1].get_text()

    def test_page_numbers_roundtrip(self, sample_pdf_doc):
        """ページ番号印字 → undo で消える → redo で再印字"""
        app = self._make_app(sample_pdf_doc)
        app.selected_pages = {0, 1, 2}
        app._add_page_numbers()
        assert "1 / 3" in app.doc[0].get_text()
        assert "3 / 3" in app.doc[2].get_text()

        app._undo()
        assert "1 / 3" not in app.doc[0].get_text()
        assert "Page 1" in app.doc[0].get_text()
        assert "2 / 3" not in app.doc[1].get_text()
        assert "Page 2" in app.doc[1].get_text()
        assert "3 / 3" not in app.doc[2].get_text()
        assert "Page 3" in app.doc[2].get_text()

        app._redo()
        assert "1 / 3" in app.doc[0].get_text()
        assert "3 / 3" in app.doc[2].get_text()
