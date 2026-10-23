## Deferred Items

- 最終全件1778 passed時に、`tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_on_success_exception_still_reaches_on_complete`で、別スレッドによるTcl interpreter解放を示すRuntimeWarningを1件観測した。
  status: open
  **Evidence:** `05-03-task3-full/pytest.txt`、exit 0、2 warnings、276.02秒。
  **Scope:** 原因未確定。新規実Tk試験との因果は未確認であり、既存起動3症状の原因解決や再発とは認定しない。推定修復・警告抑止・同条件反復は実施していない。
