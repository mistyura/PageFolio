# Phase 4 の保留観察

- 2026-10-21: 1436件の全件pytest中、既存
  `tests/test_ocr.py::TestRunParallelBackoff::test_exponential_backoff_without_retry_after`
  で、Tk Variable.__del__ の `RuntimeError: main thread is not in main loop` が
  PytestUnraisableExceptionWarningとして1件発生した。1437件の最終実行では
  再現せず（通常のPyMuPDF非推奨警告1件のみ）。原因は未確認。
  起動tracerの実Tkは別processに隔離され、該当OCRコードは変更していないため、
  本タスクでは既存OCR/Tk試験の解放処理へ範囲を広げない。
