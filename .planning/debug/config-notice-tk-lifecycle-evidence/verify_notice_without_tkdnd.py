"""通知再構築テストが D&D のネイティブ初期化に依存しないことを検証する。"""

import sys
from unittest.mock import patch

import pytest
from tkinterdnd2 import TkinterDnD


def unavailable(_root):
    raise RuntimeError("injected tkdnd package failure")


with patch.object(TkinterDnD, "_require", unavailable):
    raise SystemExit(
        pytest.main(
            [
                "-q",
                "tests/test_config_notification.py::TestNotificationLifecycle::test_real_rebuild_restores_same_notice_in_current_language",
                f"--basetemp={sys.argv[1]}",
            ]
        )
    )
