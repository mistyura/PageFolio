"""設定通知テスト群全体が D&D のネイティブ初期化に依存しないことを検証する。"""

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
                "tests/test_config_notification.py",
                f"--basetemp={sys.argv[1]}",
            ]
        )
    )
