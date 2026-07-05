"""v1.5.0 新機能の回帰テスト（V171-TEST-01・D-13〜D-16）。

テストゼロだった 3 機能を機能ごとに最適な形で検証する:
- TestDndDestIndex: D&D 挿入位置計算（compute_dnd_dest_index・純関数・Tk 非依存）
- TestShortcutMerge: ショートカットのマージ/Shift 大文字補完判定
  （merge_shortcuts / shift_variant_keysym・純関数・Tk 非依存）
- TestTocPreservation: 削除/結合/分割時の TOC 保持・再採番
  （FakeApp mixin 方式・tests/test_pdf_ops.py:1469 TestContentOpsUndoFix と同型）

D-15: test_pdf_ops.py の肥大化防止のため Phase 3 の新規テストは本ファイルへ分離する。
"""

import fitz

from pagefolio.app import merge_shortcuts, shift_variant_keysym
from pagefolio.dnd import compute_dnd_dest_index


class TestDndDestIndex:
    """compute_dnd_dest_index の境界値検証（D-16・合成データ・Tk 不要）。

    3 フレーム（各高さ40・y0=0,40,80）を想定。
    """

    FRAME_BOUNDS = [(0, 40), (40, 40), (80, 40)]

    def test_empty_frame_bounds_returns_none(self):
        assert compute_dnd_dest_index(50, []) is None

    def test_cursor_above_first_frame_returns_zero(self):
        assert compute_dnd_dest_index(-5, self.FRAME_BOUNDS) == 0

    def test_cursor_below_last_frame_returns_len(self):
        # last_y + last_h = 80 + 40 = 120 を超える
        assert compute_dnd_dest_index(125, self.FRAME_BOUNDS) == 3

    def test_cursor_at_first_frame_midpoint_boundary(self):
        # フレーム0の中点は 0+40/2=20。19 は中点未満 → index 0
        assert compute_dnd_dest_index(19, self.FRAME_BOUNDS) == 0
        # 21 は中点超過 → index 1
        assert compute_dnd_dest_index(21, self.FRAME_BOUNDS) == 1

    def test_cursor_at_second_frame_midpoint_boundary(self):
        # フレーム1の中点は 40+40/2=60
        assert compute_dnd_dest_index(59, self.FRAME_BOUNDS) == 1
        assert compute_dnd_dest_index(61, self.FRAME_BOUNDS) == 2

    def test_cursor_past_all_midpoints_but_within_bounds_returns_len(self):
        # フレーム2の中点は 80+40/2=100。101 は last_bottom(120) 以下だが
        # 全フレームの中点を超えるため len(frame_bounds) を返す
        assert compute_dnd_dest_index(101, self.FRAME_BOUNDS) == 3

    def test_single_frame(self):
        bounds = [(0, 40)]
        assert compute_dnd_dest_index(-1, bounds) == 0
        assert compute_dnd_dest_index(19, bounds) == 0
        assert compute_dnd_dest_index(21, bounds) == 1
        assert compute_dnd_dest_index(100, bounds) == 1


class TestShortcutMerge:
    """merge_shortcuts / shift_variant_keysym の検証（D-13・合成データ・Tk 不要）。"""

    def test_merge_shortcuts_custom_overrides_default(self):
        default = {"open_file": "<Control-o>", "save_file": "<Control-s>"}
        custom = {"open_file": "<Control-b>"}
        merged = merge_shortcuts(default, custom)
        assert merged["open_file"] == "<Control-b>"  # 後勝ち
        assert merged["save_file"] == "<Control-s>"  # 未上書きは維持

    def test_merge_shortcuts_custom_adds_new_key(self):
        default = {"open_file": "<Control-o>"}
        custom = {"custom_action": "<Control-k>"}
        merged = merge_shortcuts(default, custom)
        assert merged["open_file"] == "<Control-o>"
        assert merged["custom_action"] == "<Control-k>"

    def test_merge_shortcuts_empty_dicts(self):
        assert merge_shortcuts({}, {}) == {}

    def test_shift_variant_keysym_lowercase_control(self):
        assert shift_variant_keysym("<Control-o>") == "<Control-O>"
        assert shift_variant_keysym("<Control-s>") == "<Control-S>"
        assert shift_variant_keysym("<Control-z>") == "<Control-Z>"

    def test_shift_variant_keysym_non_control_returns_none(self):
        assert shift_variant_keysym("<Delete>") is None
        assert shift_variant_keysym("<F5>") is None

    def test_shift_variant_keysym_already_uppercase_returns_none(self):
        assert shift_variant_keysym("<Control-S>") is None

    def test_shift_variant_keysym_wrong_length_returns_none(self):
        # 修飾キー名が長い keysym（例: <Control-Return>）は対象外
        assert shift_variant_keysym("<Control-Return>") is None


class TestTocPreservation:
    """削除/結合/分割時の TOC 保持・再採番（D-13・FakeApp mixin 方式）。"""

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

    def test_delete_removes_toc_entries_for_deleted_pages(
        self, sample_pdf_doc, monkeypatch
    ):
        """削除されたページを指す TOC item は消え、他 item は残る。"""
        import pagefolio.page_ops as po

        doc = sample_pdf_doc
        doc.set_toc([[1, "Chapter 1", 1], [1, "Chapter 2", 2], [1, "Chapter 3", 3]])
        app = self._make_app(doc)
        app.selected_pages = {1}  # 0-indexed page 2（Chapter 2）を削除
        monkeypatch.setattr(po.messagebox, "askyesno", lambda *a, **kw: True)

        app._delete_selected()

        assert len(app.doc) == 2
        toc = app.doc.get_toc()
        titles = [item[1] for item in toc]
        assert "Chapter 2" not in titles
        assert "Chapter 1" in titles
        assert "Chapter 3" in titles

    def test_merge_concatenates_toc_with_page_offset(self, sample_pdf_doc, tmp_path):
        """結合後、追加ファイルの TOC がページオフセット付きで連結される。"""
        doc = sample_pdf_doc  # 3 ページ
        doc.set_toc([[1, "Chapter 1", 1]])
        app = self._make_app(doc)

        # 結合元ファイル（2ページ・TOC付き）を tmp_path に作成
        src = fitz.open()
        for p in range(2):
            page = src.new_page(width=595, height=842)
            page.insert_text((72, 72), f"Src Page {p + 1}", fontsize=20)
        src.set_toc([[1, "Appendix", 1]])
        src_path = str(tmp_path / "src_with_toc.pdf")
        src.save(src_path)
        src.close()

        app._do_merge([src_path])

        toc = app.doc.get_toc()
        titles_pnos = {item[1]: item[2] for item in toc}
        assert titles_pnos.get("Chapter 1") == 1
        # 元 doc は 3 ページなので Appendix（結合元1ページ目）は 3+1=4 ページ目
        assert titles_pnos.get("Appendix") == 4

    def test_split_by_range_renumbers_toc_within_range(
        self, sample_pdf_doc, tmp_path, monkeypatch
    ):
        """範囲分割で範囲内 TOC がページ再採番されて出力される。"""
        import pagefolio.page_ops as po

        doc = sample_pdf_doc  # 3 ページ
        doc.set_toc([[1, "Chapter 1", 1], [1, "Chapter 2", 2], [1, "Chapter 3", 3]])
        app = self._make_app(doc)

        monkeypatch.setattr(po.simpledialog, "askstring", lambda *a, **kw: "2-3")
        monkeypatch.setattr(
            po.filedialog, "askdirectory", lambda *a, **kw: str(tmp_path)
        )
        monkeypatch.setattr(po.messagebox, "askyesno", lambda *a, **kw: False)

        app._split_by_range()

        out_path = tmp_path / "split_p2-3.pdf"
        assert out_path.exists()
        out = fitz.open(str(out_path))
        toc = out.get_toc()
        titles_pnos = {item[1]: item[2] for item in toc}
        assert "Chapter 1" not in titles_pnos
        assert titles_pnos.get("Chapter 2") == 1  # 元ページ2 → 分割後1ページ目
        assert titles_pnos.get("Chapter 3") == 2  # 元ページ3 → 分割後2ページ目
        out.close()

    def test_split_each_page_renumbers_toc_per_output(
        self, sample_pdf_doc, tmp_path, monkeypatch
    ):
        """全ページ分割で各出力ファイルの TOC がページ1へ再採番される。"""
        import pagefolio.page_ops as po

        doc = sample_pdf_doc  # 3 ページ
        doc.set_toc([[1, "Chapter 1", 1], [1, "Chapter 2", 2], [1, "Chapter 3", 3]])
        app = self._make_app(doc)

        monkeypatch.setattr(
            po.filedialog, "askdirectory", lambda *a, **kw: str(tmp_path)
        )
        monkeypatch.setattr(po.messagebox, "askyesno", lambda *a, **kw: False)

        app._split_each_page()

        for i, title in enumerate(["Chapter 1", "Chapter 2", "Chapter 3"], start=1):
            out_path = tmp_path / f"split_p{i}.pdf"
            assert out_path.exists()
            out = fitz.open(str(out_path))
            toc = out.get_toc()
            assert toc == [[1, title, 1]]
            out.close()
