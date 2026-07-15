"""pagefolio.batch_ocr_state のユニットテスト（Tk/fitz 非依存純ロジック層）。

04-01-PLAN.md Task 1（Wave 0 RED テスト先行）: pagefolio.batch_ocr_state は
まだ実装されていない。ここでは Task 2 が満たすべき仕様として先に6テストを
定義する（import 記法は tests/test_ocr_pipeline.py を踏襲）。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pagefolio.batch_ocr_state import (  # noqa: E402
    STATUS_DONE,
    STATUS_ERROR,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    BatchFileEntry,
    BatchState,
    count_pending,
    enqueue_files,
)


class TestEnqueueFiles:
    def test_enqueue_files(self):
        # 空キューに2パスを enqueue -> 2件
        entries = enqueue_files([], ["a.pdf", "b.pdf"])
        assert len(entries) == 2
        assert {e.path for e in entries} == {"a.pdf", "b.pdf"}

        # 同じパスを再度 enqueue -> 件数不変（dedup）
        entries = enqueue_files(entries, ["a.pdf"])
        assert len(entries) == 2

        # 空リスト enqueue -> 件数不変（空キュー始点の安全性）
        entries = enqueue_files(entries, [])
        assert len(entries) == 2

        # page_counts を渡すと各 entry.page_count に反映される
        entries = enqueue_files(
            [], ["c.pdf", "d.pdf"], page_counts={"c.pdf": 5, "d.pdf": 3}
        )
        by_path = {e.path: e for e in entries}
        assert by_path["c.pdf"].page_count == 5
        assert by_path["d.pdf"].page_count == 3


class TestStateTransitions:
    def test_state_transitions(self):
        entry = BatchFileEntry("x.pdf")
        assert entry.status == STATUS_PENDING

        statuses = {
            STATUS_PENDING,
            STATUS_RUNNING,
            STATUS_DONE,
            STATUS_FAILED,
            STATUS_ERROR,
        }
        assert len(statuses) == 5


class TestProgressAggregation:
    def test_progress_aggregation(self):
        state = BatchState(total_files=3)
        assert state.files_done() == 0
        assert state.remaining() == 3

        state.mark_completed()
        state.mark_failed()
        state.mark_cancelled()

        assert state.files_done() == 3
        assert state.remaining() == 0
        # files_done() は total_files を超えない
        assert state.files_done() <= state.total_files


class TestBrokenPdfErrorStatus:
    def test_broken_pdf_error_status(self):
        entry = BatchFileEntry("broken.pdf", page_count=0)
        entry.status = STATUS_ERROR
        assert entry.status == STATUS_ERROR
        assert entry.page_count == 0


class TestErrorFileExcludedFromTotal:
    def test_error_file_excluded_from_total(self):
        entries = [
            BatchFileEntry("a.pdf"),
            BatchFileEntry("b.pdf"),
            BatchFileEntry("broken.pdf", page_count=0),
        ]
        entries[2].status = STATUS_ERROR

        pending_count = count_pending(entries)
        assert pending_count == 2

        state = BatchState(total_files=pending_count)
        state.mark_completed()
        state.mark_failed()

        assert state.remaining() == 0


class TestNoTkFitzToplevelImport:
    def test_no_tk_fitz_toplevel_import(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "pagefolio",
            "batch_ocr_state.py",
        )
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        top_level_import_lines = [
            line
            for line in lines
            if line.startswith("import ") or line.startswith("from ")
        ]
        for line in top_level_import_lines:
            assert "tkinter" not in line, f"tkinter import 検出: {line!r}"
            assert "fitz" not in line, f"fitz import 検出: {line!r}"
