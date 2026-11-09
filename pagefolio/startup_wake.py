"""Windows の Tk イベント待ちを投稿メッセージで定期的に起こす。"""

import ctypes as ct
import threading


class UiThreadWake:
    """Tk API に触れず、生成元スレッドへ WM_NULL だけを投稿する。

    Tcl の PeekMessage と GetMessage の間でメッセージが消えると、after の
    期限が来ても GetMessage は戻らない。送信ではなく投稿して待ちを解除する。
    Tk 初期化後に作成し、root の破棄前に close する。
    """

    def __init__(self, api, logger):
        self._api = api
        self._logger = logger
        self._owner = threading.current_thread()
        self._thread_id = threading.get_native_id()
        self._stop = threading.Event()
        self._worker = None

    def start(self):
        if threading.current_thread() is not self._owner:
            raise RuntimeError("UI スレッド以外から見張りを開始できません")
        if self._stop.is_set():
            raise RuntimeError("終了した見張りは再開できません")
        if self._worker is not None:
            return
        worker = threading.Thread(
            target=self._run, daemon=True, name="pagefolio-ui-wake"
        )
        worker.start()
        self._worker = worker

    def _run(self):
        failed = False
        while not self._stop.wait(0.120):
            if not self._owner.is_alive():
                return
            try:
                if not self._api.PostThreadMessageW(self._thread_id, 0, 0, 0):
                    raise OSError(ct.get_last_error(), "WM_NULL の投稿失敗")
            except Exception as e:
                # 連続した失敗は最初の1回のみ記録し、次の周期で再試行する。
                if not failed:
                    self._logger.warning("UI 見張りの投稿失敗: %s", e)
                failed = True
            else:
                failed = False

    def close(self):
        self._stop.set()
        if self._worker is not None:
            # PostThreadMessageW は相手の処理を待たない。投稿中でも完了を待ち、
            # root の破棄や UI スレッド終了後への投稿を防ぐ。
            self._worker.join()
