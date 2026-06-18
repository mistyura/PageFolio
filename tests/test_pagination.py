"""pagefolio.pagination 純ロジック層の境界値・往復不変・D&D 換算・選択照合テスト。

全テストは Tk 非依存（ウィジェット起動不要）でヘッドレス実行できる。
named クラスは 02-RESEARCH.md L398-403 / 02-VALIDATION.md Per-Task Map に整合:
    TestWindowBounds=SC1 / TestPageSizePersist=SC2 / TestDndIndexConvert=SC3 /
    TestSelectionAcrossWindows=SC4 / TestWindowFollow=D-11 / TestNavState=D-09
"""

from pagefolio.pagination import (
    clamp_page_size,
    clamp_window_start,
    to_global,
    to_local,
    window_bounds,
    window_for_page,
    window_label,
    window_nav_state,
)


class TestWindowBounds:
    """SC1: 件数で窓を区切り、最終窓の端数を実ページ数でクランプする（D-10）。"""

    def test_middle_window(self):
        assert window_bounds(20, 20, 47) == (20, 40)

    def test_fraction_last_window(self):
        # 端数最終窓・D-10: 件数 20・全 47 → 最終窓 (40, 47)
        assert window_bounds(40, 20, 47) == (40, 47)

    def test_first_window(self):
        assert window_bounds(0, 20, 47) == (0, 20)

    def test_page_size_equals_total(self):
        # 件数 = 全ページ・単一窓
        assert window_bounds(0, 20, 20) == (0, 20)

    def test_page_size_greater_than_total(self):
        # 件数 > 全ページ
        assert window_bounds(0, 50, 20) == (0, 20)

    def test_single_page(self):
        assert window_bounds(0, 20, 1) == (0, 1)

    def test_doc_not_open(self):
        # doc 未オープン
        assert window_bounds(0, 20, 0) == (0, 0)

    def test_exact_divisible_last_window(self):
        assert window_bounds(20, 20, 40) == (20, 40)

    def test_invariant_lo_hi_range(self):
        # 0 <= lo <= hi <= n_pages、hi - lo <= page_size
        for n in (0, 1, 20, 40, 47, 100):
            for size in (10, 20, 50):
                for start in (0, size, size * 2, size * 3):
                    lo, hi = window_bounds(start, size, n)
                    assert 0 <= lo <= hi <= n
                    assert hi - lo <= size


class TestIndexConvert:
    """往復不変条件（プロパティ）をループ網羅。"""

    def test_to_global_basic(self):
        assert to_global(3, 20) == 23
        assert to_global(0, 0) == 0

    def test_to_local_basic(self):
        assert to_local(23, 20) == 3
        assert to_local(0, 0) == 0

    def test_round_trip_global_local_global(self):
        # 任意 g（0..n-1）と任意 start で to_global(to_local(g, start), start) == g
        n = 47
        for g in range(n):
            for start in (0, 20, 40):
                assert to_global(to_local(g, start), start) == g

    def test_round_trip_local_global_local(self):
        # 窓内任意ローカル l（0..size-1）で to_local(to_global(l, start), start) == l
        size = 20
        for start in (0, 20, 40):
            for local in range(size):
                assert to_local(to_global(local, start), start) == local


class TestWindowFollow:
    """D-11: window_for_page が current_page を含む窓の先頭（page_size 倍数）を返す。"""

    def test_window_for_page_boundaries(self):
        assert window_for_page(0, 20) == 0
        assert window_for_page(19, 20) == 0
        assert window_for_page(20, 20) == 20
        assert window_for_page(46, 20) == 40

    def test_window_for_page_smaller_size(self):
        # 件数変更で current が別窓に入る: size 20→10、current=25 → 新 start 20
        assert window_for_page(25, 10) == 20

    def test_window_for_page_is_multiple(self):
        for idx in range(0, 50):
            for size in (10, 20):
                start = window_for_page(idx, size)
                assert start % size == 0
                assert start <= idx < start + size

    def test_window_for_page_invalid_size(self):
        assert window_for_page(5, 0) == 0
        assert window_for_page(5, -10) == 0


class TestClampWindowStart:
    """削除・件数変更後の正規化（window_start を有効な窓先頭へ寄せる）。"""

    def test_clamp_after_delete_shrinks_last_window(self):
        # n が 47→40 に減り window_start=40 が無効 → 窓2（start=20）へ
        assert clamp_window_start(40, 20, 40) == 20

    def test_clamp_after_delete_empties_window(self):
        # n が 25→20 に減り window_start=20 → 窓1（start=0）へ
        assert clamp_window_start(20, 20, 20) == 0

    def test_clamp_valid_start_unchanged(self):
        assert clamp_window_start(20, 20, 47) == 20
        assert clamp_window_start(0, 20, 47) == 0

    def test_clamp_doc_not_open(self):
        assert clamp_window_start(40, 20, 0) == 0

    def test_clamp_invalid_page_size(self):
        assert clamp_window_start(40, 0, 47) == 0

    def test_clamp_returns_valid_window_head(self):
        for n in (1, 20, 25, 40, 47, 100):
            for size in (10, 20, 50):
                for start in (0, size, size * 2, size * 3, 999):
                    result = clamp_window_start(start, size, n)
                    assert result % size == 0
                    assert result < n


class TestNavState:
    """D-09: 単一窓は (False, False)。中間/先頭/最終窓のナビ活性状態。"""

    def test_single_window(self):
        assert window_nav_state(0, 20, 20) == (False, False)

    def test_single_window_page_size_greater(self):
        assert window_nav_state(0, 50, 20) == (False, False)

    def test_first_window(self):
        # 先頭窓: prev disabled, next enabled
        assert window_nav_state(0, 20, 47) == (False, True)

    def test_middle_window(self):
        assert window_nav_state(20, 20, 47) == (True, True)

    def test_last_window(self):
        # 最終窓: prev enabled, next disabled
        assert window_nav_state(40, 20, 47) == (True, False)

    def test_doc_not_open(self):
        assert window_nav_state(0, 20, 0) == (False, False)


class TestWindowLabel:
    """1 始まり・端数最終窓で正しい範囲文字列を返す（D-09/D-10）。

    LANG 文言を直接アサートせず、数値部分の包含で検証（文言裁量と疎結合）。
    """

    def test_first_window_label(self):
        label = window_label(0, 20, 47)
        assert "1" in label
        assert "20" in label
        assert "47" in label

    def test_fraction_last_window_label(self):
        # 端数最終窓・D-10: "41" 始まり "47" 終わり・全 "47"
        label = window_label(40, 20, 47)
        assert "41" in label
        assert "47" in label

    def test_single_window_label(self):
        label = window_label(0, 20, 8)
        assert "1" in label
        assert "8" in label

    def test_empty_doc_label(self):
        # n_pages==0 では空ドキュメントを示す既定文字列（数値範囲ではない）
        label = window_label(0, 20, 0)
        assert isinstance(label, str)
        assert label != ""


class TestPageSizePersist:
    """SC2: clamp_page_size の純ロジック（件数クランプ・W1）。

    settings 永続化との結合は 02-02 で検証。本クラスは純関数のみ。
    """

    def test_below_min_clamped_to_10(self):
        assert clamp_page_size(5) == 10

    def test_above_max_clamped_to_100(self):
        assert clamp_page_size(200) == 100

    def test_in_range_unchanged(self):
        assert clamp_page_size(20) == 20

    def test_string_numeric(self):
        assert clamp_page_size("30") == 30

    def test_empty_string_default(self):
        assert clamp_page_size("") == 20

    def test_none_default(self):
        assert clamp_page_size(None) == 20

    def test_non_numeric_default(self):
        assert clamp_page_size("abc") == 20

    def test_boundary_values(self):
        assert clamp_page_size(10) == 10
        assert clamp_page_size(100) == 100


class TestDndIndexConvert:
    """SC3・D-06: D&D ドロップ先の local→global 換算と窓末尾の min クランプ。"""

    def test_drop_in_window2(self):
        # 窓2（window_start=20）でローカル dest=3 → 全ページ 23
        assert to_global(3, 20) == 23

    def test_drop_at_window_tail_clamped(self):
        # 窓末尾ドロップは window_bounds の hi（n_pages）でクランプし範囲を超えない
        n_pages = 47
        window_start = 20
        page_size = 20
        _lo, hi = window_bounds(window_start, page_size, n_pages)
        # 窓2 のフレーム数ぶんローカル dest が来ても全ページ範囲を超えない
        local_dest = hi - window_start  # 窓末尾（フレーム数）
        global_dest = min(to_global(local_dest, window_start), n_pages)
        assert global_dest <= n_pages
        assert global_dest == hi  # (40) ＝ 窓末尾の global 位置

    def test_drop_at_last_window_tail_clamped_to_len(self):
        # 端数最終窓（40, 47）の末尾ドロップは len(doc)=47 でクランプ
        n_pages = 47
        window_start = 40
        page_size = 20
        _lo, hi = window_bounds(window_start, page_size, n_pages)
        local_dest = hi - window_start
        global_dest = min(to_global(local_dest, window_start), n_pages)
        assert global_dest == 47


class TestSelectionAcrossWindows:
    """SC4・D-07: selected_pages が窓またぎでも全ページ index を保持し整合する。"""

    def test_local_match_uses_global_index(self):
        # selected_pages={3, 25} を窓2（window_start=20）でローカル照合
        selected_pages = {3, 25}
        window_start = 20
        page_size = 20
        lo, hi = window_bounds(window_start, page_size, 47)
        # 窓2 の各ローカル位置を global へ換算して selected と照合
        highlighted_locals = [
            local
            for local in range(hi - lo)
            if to_global(local, window_start) in selected_pages
        ]
        # global 25 ＝ local 5 のみがハイライト対象
        assert highlighted_locals == [5]

    def test_selected_pages_unchanged_after_match(self):
        # 各エントリは全ページ index（3 / 25）を保持し書き換わらない
        selected_pages = {3, 25}
        snapshot = set(selected_pages)
        window_start = 20
        for local in range(20):
            _ = to_global(local, window_start) in selected_pages
        assert selected_pages == snapshot

    def test_global_in_selected_after_convert(self):
        # to_global(local, 20) が 23 のとき g==23 が selected_pages に含まれる照合が成立
        selected_pages = {3, 23, 25}
        assert to_global(3, 20) == 23
        assert to_global(3, 20) in selected_pages
