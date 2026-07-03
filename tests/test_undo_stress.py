"""大規模ドキュメント向け Undo/Redo ストレステスト（v1.7.0）。

100 ページ超の PDF に対して Undo/Redo を連続で繰り返し、
  1. 正当性（ページ数・内容が往復後も一致すること）
  2. メモリ（Python ヒープ増分が上限内・Blob 不変条件でリークなし）
  3. eviction（deque 溢れ時に FileBlob の一時ファイルが物理削除されること）
を自動検証する。

PyMuPDF の C 側アロケーションは tracemalloc に映らないため、リーク検出の
主アサーションは Blob 不変条件（ストア内ファイル数の上限・クリア後の空）
とする。ヒープ増分は補完的な緩い上限。
"""

import collections
import hashlib
import io
import os
import tracemalloc
import types

import fitz
import pytest
from PIL import Image

import pagefolio.file_ops as fo
import pagefolio.redact_ops as ro

# 高解像度画像ベース PDF を模して、非圧縮性のノイズ画像を各ページへ埋め込む
# （テキストのみだと deflate 圧縮で 1 ページが OFFLOAD_THRESHOLD=64KiB を
# 下回り、ディスク退避経路を通らない）。
N_PAGES = 120
CYCLES = 25


def _noise_png(seed, width=180, height=180):
    """sha256 チェーンによる決定的ノイズ RGB 画像の PNG bytes（≈95KiB）。

    ノイズは PNG 圧縮がほぼ効かないため、1 ページの bytes を確実に
    閾値超にできる。乱数を使わないためテストは決定的。
    """
    need = width * height * 3
    chunks = []
    h = hashlib.sha256(seed.encode()).digest()
    while sum(len(c) for c in chunks) < need:
        chunks.append(h)
        h = hashlib.sha256(h).digest()
    raw = b"".join(chunks)[:need]
    img = Image.frombytes("RGB", (width, height), raw)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_stress_app(doc, max_undo=20):
    class FakeApp(fo.FileOpsMixin, ro.RedactOpsMixin):
        MAX_UNDO = max_undo

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


@pytest.fixture(scope="module")
def stress_pdf_bytes():
    """120 ページ・1 ページあたり 64KiB 超の PDF bytes を生成する。

    module スコープで 1 回だけ生成し、各テストは fitz.open(stream=...) で
    独立したコピーを得る（テスト間の doc 汚染防止）。
    """
    doc = fitz.open()
    # 生成コスト削減のためノイズ画像は 8 種を巡回使用する（挿入自体は
    # ページごとに独立なので、1 ページ抽出時の bytes は毎ページ閾値超）
    pngs = [_noise_png(f"pagefolio-stress-{k}") for k in range(8)]
    for i in range(N_PAGES):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Stress Page {i + 1}", fontsize=18)
        page.insert_image(fitz.Rect(100, 150, 500, 550), stream=pngs[i % 8])
    data = doc.tobytes()
    doc.close()
    return data


def _blob_files(app):
    """ストアの一時ディレクトリ内ファイル数（未生成なら 0）。"""
    store = getattr(app, "_undo_blob_store", None)
    return store.file_count() if store else 0


class TestUndoRedoStress:
    def test_delete_undo_redo_correctness(self, stress_pdf_bytes):
        """5 ページ削除 → undo → redo → undo を 25 サイクル繰り返しても
        ページ数・内容が正しく往復する。"""
        doc = fitz.open(stream=stress_pdf_bytes, filetype="pdf")
        app = _make_stress_app(doc)
        targets = [10, 25, 50, 75, 100]
        sample_texts = {i: doc[i].get_text()[:60] for i in targets}

        for _cycle in range(CYCLES):
            # do: 削除（降順）
            app._save_undo("delete", targets=targets)
            for i in sorted(targets, reverse=True):
                app.doc.delete_page(i)
            assert len(app.doc) == N_PAGES - len(targets)

            # undo: 復元
            app._undo()
            assert len(app.doc) == N_PAGES
            for i, head in sample_texts.items():
                assert app.doc[i].get_text()[:60] == head

            # redo: 再削除 → undo: 再復元
            app._redo()
            assert len(app.doc) == N_PAGES - len(targets)
            app._undo()
            assert len(app.doc) == N_PAGES

        app._clear_undo_stacks()
        doc.close()

    def test_memory_and_blob_invariants(self, stress_pdf_bytes):
        """連続 Undo/Redo 中の Python ヒープ増分と Blob 不変条件を検証する。

        - ストア内ファイル数は「ライブな state が保持する FileBlob 数」を
          超えない（消費・evict で物理削除される＝リークなし）
        - スタッククリア後はディレクトリが空になる
        - Python ヒープ増分 < 20MB（bytes デルタがヒープに滞留しない）
        """
        doc = fitz.open(stream=stress_pdf_bytes, filetype="pdf")
        app = _make_stress_app(doc)
        targets = [10, 25, 50, 75, 100]

        tracemalloc.start()
        baseline, _ = tracemalloc.get_traced_memory()

        for _cycle in range(30):
            app._save_undo("delete", targets=targets)
            for i in sorted(targets, reverse=True):
                app.doc.delete_page(i)
            app._undo()
            app._redo()
            app._undo()

            # Blob 不変条件: ライブ state は最大で
            # undo スタック全世代 + redo スタック全世代ぶんのページ Blob。
            # 各 state は最大 len(targets) 個のページ Blob を持つ
            live_states = len(app._undo_stack) + len(app._redo_stack)
            assert _blob_files(app) <= live_states * len(targets)

        current, _ = tracemalloc.get_traced_memory()
        heap_growth = current - baseline
        tracemalloc.stop()

        # ページ bytes はディスク退避されるため Python ヒープには滞留しない
        assert heap_growth < 20 * 1024 * 1024, (
            f"Python ヒープ増分が上限超過: {heap_growth / 1024 / 1024:.1f} MB"
        )

        # クリア後は一時ディレクトリごと削除される
        store = app._undo_blob_store
        tmp_dir = store.dir
        assert tmp_dir is not None and os.path.isdir(tmp_dir)
        app._clear_undo_stacks()
        assert not os.path.isdir(tmp_dir)
        assert _blob_files(app) == 0
        doc.close()

    def test_eviction_deletes_oldest_blob_files(self, stress_pdf_bytes):
        """MAX_UNDO+5 回の delete を積むと、evict された最古 state の
        FileBlob が物理削除され、ファイル数がライブ state 分に一致する。"""
        doc = fitz.open(stream=stress_pdf_bytes, filetype="pdf")
        max_undo = 20
        app = _make_stress_app(doc, max_undo=max_undo)

        # 1 回 1 ページ削除 → 復元せず積み続ける（undo スタックだけが伸びる）
        for _n in range(max_undo + 5):
            app._save_undo("delete", targets=[0])
            app.doc.delete_page(0)

        assert len(app._undo_stack) == max_undo  # deque(maxlen) で上限維持
        # evict された 5 世代ぶんの FileBlob は物理削除済み
        # （1 state = 1 ページ Blob・すべて 64KiB 超なので FileBlob）
        assert _blob_files(app) == max_undo

        app._clear_undo_stacks()
        assert _blob_files(app) == 0
        doc.close()

    def test_page_edit_stress_blob_bounded(self, stress_pdf_bytes):
        """page_edit（黒塗り）連続適用 + undo 往復でも Blob が滞留しない。"""
        doc = fitz.open(stream=stress_pdf_bytes, filetype="pdf")
        app = _make_stress_app(doc)
        rect = fitz.Rect(60, 50, 300, 110)

        for cycle in range(15):
            page_i = cycle % 5
            app._save_undo("page_edit", targets=[page_i])
            ro.RedactOpsMixin._redact_page(app.doc[page_i], rect)
            app._undo()
            live_states = len(app._undo_stack) + len(app._redo_stack)
            assert _blob_files(app) <= live_states

        app._clear_undo_stacks()
        assert _blob_files(app) == 0
        doc.close()
