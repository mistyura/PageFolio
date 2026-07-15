# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""サムネイル画像 LRU キャッシュの汎用コンテナ — Tkinter / fitz 非依存。

値は不透明オブジェクト（ImageTk.PhotoImage 等）として扱い型検査しない。
キーは常にページ番号のみ（落とし穴2「thumb_cache と仮想化ウィジェット再利用の
責務混同」回避策・05-CONTEXT.md D-08）。エビクションは純粋 LRU（容量到達時に
最古参照分だけ自然に押し出す・窓移動時の積極パージは設けない・D-07）。

viewer.py の既存呼び出し面（in 判定・[i] 取得・[i]= 代入・pop(p, None)・clear()）
を無改造で維持できるよう dict 風 API を実装する（05-02 統合の前提契約）。

ここには `tkinter` / `fitz` を一切 import しない。
"""

from collections import OrderedDict


class LruCache:
    """容量固定の LRU コンテナ（キー任意・値は不透明オブジェクト）。

    __getitem__ ヒット時・__setitem__ 既存キー更新時に move_to_end で
    recency を更新する。容量超過時は popitem(last=False) で最古参照エントリを
    1件エビクトする。
    """

    def __init__(self, maxsize):
        self._maxsize = maxsize
        self._data = OrderedDict()

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        value = self._data[key]
        self._data.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def __len__(self):
        return len(self._data)

    def pop(self, key, default=None):
        return self._data.pop(key, default)

    def clear(self):
        self._data.clear()
