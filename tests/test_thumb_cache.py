"""pagefolio.thumb_cache.LruCache のユニットテスト（05-01 Task 1）。

Tk root は生成しない（純クラスのみ）。値は不透明オブジェクトとして扱う。
"""

import pytest

from pagefolio.thumb_cache import LruCache


class TestLruCacheEviction:
    """容量到達後の put で最古参照分だけがエビクトされる（純粋 LRU・D-07）。"""

    def test_oldest_evicted_when_over_capacity(self):
        cache = LruCache(2)
        cache[0] = "a"
        cache[1] = "b"
        cache[2] = "c"
        assert len(cache) == 2
        assert 0 not in cache
        assert 1 in cache
        assert 2 in cache

    def test_no_eviction_within_capacity(self):
        cache = LruCache(3)
        cache[0] = "a"
        cache[1] = "b"
        assert len(cache) == 2
        assert 0 in cache
        assert 1 in cache


class TestLruCacheRecency:
    """__getitem__ による recency 更新後は別キーが先にエビクトされる。"""

    def test_getitem_updates_recency(self):
        cache = LruCache(2)
        cache[0] = "a"
        cache[1] = "b"
        # 0 を読み取って recency を更新 -> 次に古いのは 1
        _ = cache[0]
        cache[2] = "c"
        assert 1 not in cache
        assert 0 in cache
        assert 2 in cache

    def test_setitem_existing_key_updates_recency(self):
        cache = LruCache(2)
        cache[0] = "a"
        cache[1] = "b"
        # 既存キー 0 を再代入 -> recency 更新 -> 次に古いのは 1
        cache[0] = "a2"
        cache[2] = "c"
        assert 1 not in cache
        assert cache[0] == "a2"
        assert 2 in cache


class TestLruCachePopClearContainsLen:
    """pop(既存/欠損, default)・clear()・__contains__・__len__ の挙動。"""

    def test_pop_existing_key(self):
        cache = LruCache(3)
        cache[0] = "a"
        assert cache.pop(0, None) == "a"
        assert 0 not in cache
        assert len(cache) == 0

    def test_pop_missing_key_returns_default(self):
        cache = LruCache(3)
        assert cache.pop(99, None) is None
        assert cache.pop(99, "fallback") == "fallback"

    def test_clear_empties_cache(self):
        cache = LruCache(3)
        cache[0] = "a"
        cache[1] = "b"
        cache.clear()
        assert len(cache) == 0
        assert 0 not in cache
        assert 1 not in cache

    def test_contains_and_len(self):
        cache = LruCache(3)
        assert len(cache) == 0
        assert 0 not in cache
        cache[0] = "a"
        assert 0 in cache
        assert len(cache) == 1


class TestLruCacheMissingKeyError:
    """ミスキー __getitem__ が KeyError を送出する。"""

    def test_getitem_missing_key_raises_keyerror(self):
        cache = LruCache(2)
        with pytest.raises(KeyError):
            _ = cache[999]
