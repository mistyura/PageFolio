"""pagefolio.pagination 純ロジック層の境界値・往復不変・D&D 換算・選択照合テスト。

全テストは Tk 非依存（ウィジェット起動不要）でヘッドレス実行できる。
named クラスは 02-RESEARCH.md L398-403 / 02-VALIDATION.md Per-Task Map に整合:
    TestWindowBounds=SC1 / TestPageSizePersist=SC2 / TestDndIndexConvert=SC3 /
    TestSelectionAcrossWindows=SC4 / TestWindowFollow=D-11 / TestNavState=D-09
"""

import json
import types

from pagefolio.pagination import (
    clamp_page_size,
    clamp_window_start,
    reconcile_window_start,
    to_global,
    to_local,
    window_bounds,
    window_for_page,
    window_label,
    window_nav_state,
)
from pagefolio.settings import _load_settings
from pagefolio.viewer import ViewerMixin


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


class TestReconcileWindowStart:
    """D-11 条件付き追従の純関数仕様。

    reconcile_window_start は「操作で current_page が現窓の外へ押し出された」
    場合のみ window_for_page(current_page) へ追従し、current が窓内なら
    window_start を温存する正規化関数。手動窓ナビ（◀▶）は呼び出し側
    （ViewerMixin._move_window）が current_page を新窓内へ追従させ「current は
    常に窓内」の不変条件を保つため、この純関数には窓外入力として到達しない。
    したがって「手動ナビで current が窓外のまま温存」という入力は仕様外であり、
    純関数単独で (A) 手動離脱 と (B) 押し出し を区別する必要はない
    （対立解消の詳細は TestMoveWindowHandler を参照）。
    """

    def test_current_in_window_preserves_start(self):
        # current_page=25 は窓2 [20,40) 内 → window_start=20 を温存（追従しない）。
        assert reconcile_window_start(20, 25, 20, 47) == 20

    def test_current_outside_window_follows(self):
        # current_page=5（窓1 在）だが window_start=20 → current が窓外。
        # window_for_page(5,20)=0 へ追従（D-11）。
        assert reconcile_window_start(20, 5, 20, 47) == 0

    def test_current_outside_to_later_window_follows(self):
        # current_page=45（窓3 在）だが window_start=0 → 窓外。
        # window_for_page(45,20)=40 へ追従。
        assert reconcile_window_start(0, 45, 20, 47) == 40

    def test_current_at_window_lower_boundary_in(self):
        # current==lo は窓内（境界の包含側）→ 温存。
        assert reconcile_window_start(20, 20, 20, 47) == 20

    def test_current_at_window_upper_boundary_out(self):
        # current==hi（半開区間の外）→ 追従。window_start=20・hi=40・current=40。
        assert reconcile_window_start(20, 40, 20, 47) == 40

    def test_invalid_start_clamped_then_followed(self):
        # 削除等で無効化した window_start=999 はまず clamp、その後 current 追従判定。
        # n=25・size=20 → last_start=20。current=5 は窓2 外 → window_for_page(5)=0。
        assert reconcile_window_start(999, 5, 20, 25) == 0

    def test_invalid_start_clamped_current_in_clamped_window(self):
        # window_start=999→clamp で 20。current=22 は窓2[20,25) 内 → 20 温存。
        assert reconcile_window_start(999, 22, 20, 25) == 20

    def test_doc_not_open(self):
        assert reconcile_window_start(20, 0, 20, 0) == 0

    def test_invalid_page_size(self):
        assert reconcile_window_start(20, 0, 0, 47) == 0

    def test_result_is_valid_window_head(self):
        # 任意入力で戻り値は有効窓先頭（% size == 0 かつ < n）を満たす。
        for n in (1, 20, 25, 40, 47, 100):
            for size in (10, 20, 50):
                for start in (0, size, size * 2, 999):
                    for cur in (0, n // 2, n - 1):
                        result = reconcile_window_start(start, cur, size, n)
                        assert result % size == 0
                        assert 0 <= result < n


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

    # ── settings 結合（02-02 で追加）──
    def test_default_settings_has_thumb_page_size_20(self, monkeypatch, tmp_path):
        """SC2: 設定ファイルなし時 DEFAULT に thumb_page_size==20 が存在する。"""
        path = tmp_path / "absent_settings.json"
        monkeypatch.setattr("pagefolio.settings._get_settings_path", lambda: str(path))
        data = _load_settings()
        assert data["thumb_page_size"] == 20

    def test_legacy_settings_backfilled_by_setdefault(self, monkeypatch, tmp_path):
        """後方互換: thumb_page_size キーなしの旧設定でも 20 が補完される。"""
        path = tmp_path / "legacy_settings.json"
        # thumb_page_size を含まない旧設定ファイル
        path.write_text(
            json.dumps({"theme": "light", "font_size": 14}),
            encoding="utf-8",
        )
        monkeypatch.setattr("pagefolio.settings._get_settings_path", lambda: str(path))
        data = _load_settings()
        assert data["thumb_page_size"] == 20
        # 既存ユーザー値は setdefault により温存される
        assert data["theme"] == "light"
        assert data["font_size"] == 14

    def test_existing_user_value_not_clobbered(self, monkeypatch, tmp_path):
        """既存の thumb_page_size 値は setdefault で温存される（clobber しない）。"""
        path = tmp_path / "user_settings.json"
        path.write_text(
            json.dumps({"thumb_page_size": 50}),
            encoding="utf-8",
        )
        monkeypatch.setattr("pagefolio.settings._get_settings_path", lambda: str(path))
        data = _load_settings()
        assert data["thumb_page_size"] == 50
        # クランプ読み出ししても範囲内なのでそのまま
        assert clamp_page_size(data["thumb_page_size"]) == 50

    def test_clamp_of_loaded_default_is_20(self, monkeypatch, tmp_path):
        """settings → clamp_page_size 結合: 既定値は 20 のまま（W1）。"""
        path = tmp_path / "absent_settings.json"
        monkeypatch.setattr("pagefolio.settings._get_settings_path", lambda: str(path))
        data = _load_settings()
        assert clamp_page_size(data["thumb_page_size"]) == 20

    def test_clamp_of_loaded_out_of_range_value(self, monkeypatch, tmp_path):
        """壊れた設定（範囲外）でも clamp 読み出しで安全側に倒れる。"""
        path = tmp_path / "broken_settings.json"
        path.write_text(
            json.dumps({"thumb_page_size": 9999}),
            encoding="utf-8",
        )
        monkeypatch.setattr("pagefolio.settings._get_settings_path", lambda: str(path))
        data = _load_settings()
        assert clamp_page_size(data["thumb_page_size"]) == 100


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


class TestThumbCacheRetention:
    """A1/Pitfall 2/W2: 窓移動・件数変更ハンドラが thumb_cache をクリアしない。

    _prev_window / _next_window / _on_page_size_change を GUI 起動なしの
    SimpleNamespace スタブへ非束縛で適用し、呼び出し前後で id(thumb_cache) が
    不変であること（= _invalidate_thumb_cache も thumb_cache = {} 再代入も
    行われていない）を自動アサートする。目視 UAT 依存を unit へ昇格させる。
    """

    def _make_stub(self):
        """副作用を無効化した最小スタブ。

        _refresh_all / _set_status / plugin_manager.fire_event は no-op、
        page_size_var は固定値 30 を返す簡易スタブ。doc は長さ 47 の擬似配列
        （_move_window が len(doc) を参照するため）。thumb_cache は既知の dict
        オブジェクト（id 監視対象）。
        """
        cache = {0: object(), 1: object()}
        stub = types.SimpleNamespace(
            _page_window_start=20,
            _page_size=20,
            current_page=25,
            doc=[None] * 47,
            thumb_cache=cache,
            settings={},
            page_size_var=types.SimpleNamespace(get=lambda: 30),
            plugin_manager=types.SimpleNamespace(fire_event=lambda *a, **k: None),
        )
        # 描画・状態表示の委譲を no-op で断つ。_move_window は非束縛適用のため
        # stub 上へ明示束縛する（SimpleNamespace は MRO を持たない）。
        stub._refresh_all = lambda: None
        stub._set_status = lambda msg: None
        stub._move_window = lambda direction: ViewerMixin._move_window(stub, direction)
        return stub

    def test_prev_window_keeps_cache_identity(self):
        stub = self._make_stub()
        before = id(stub.thumb_cache)
        ViewerMixin._prev_window(stub)
        assert id(stub.thumb_cache) == before, (
            "_prev_window が thumb_cache をクリアした"
        )

    def test_next_window_keeps_cache_identity(self):
        stub = self._make_stub()
        before = id(stub.thumb_cache)
        ViewerMixin._next_window(stub)
        assert id(stub.thumb_cache) == before, (
            "_next_window が thumb_cache をクリアした"
        )

    def test_page_size_change_keeps_cache_identity(self, monkeypatch):
        # _on_page_size_change はハンドラ内で pagefolio.settings._save_settings を
        # import して呼ぶため、ディスク書き込みを no-op へ差し替える。
        import pagefolio.settings as settings_mod

        monkeypatch.setattr(settings_mod, "_save_settings", lambda s: None)
        stub = self._make_stub()
        before = id(stub.thumb_cache)
        ViewerMixin._on_page_size_change(stub)
        assert id(stub.thumb_cache) == before, (
            "_on_page_size_change が thumb_cache をクリアした"
        )
        # 副次的に件数が clamp_page_size 経由で反映されることも確認（30 は範囲内）
        assert stub._page_size == 30
        assert stub.settings["thumb_page_size"] == 30

    def test_page_size_change_handles_error_fallback(self, monkeypatch):
        # page_size_var.get() が空文字相当で失敗しても既定 20 へフォールバック。
        import pagefolio.settings as settings_mod

        monkeypatch.setattr(settings_mod, "_save_settings", lambda s: None)
        stub = self._make_stub()

        def _raise():
            raise ValueError("empty")

        stub.page_size_var = types.SimpleNamespace(get=_raise)
        before = id(stub.thumb_cache)
        ViewerMixin._on_page_size_change(stub)
        assert id(stub.thumb_cache) == before
        assert stub._page_size == 20


class TestMoveWindowHandler:
    """手動窓ナビ（◀▶）の不変条件: 窓移動後に current_page が新窓内へ追従する。

    対立解消の要 — ViewerMixin._move_window が current を新窓先頭へ動かすことで
    「current は常に窓内」を保証し、_refresh_all の reconcile_window_start を
    (B) 操作による押し出し専用の追従へ純化する。これにより手動ナビ後に current の
    窓へ snap back する不具合（UAT 項目2 NG）が原理的に発生しなくなる。純関数
    単独では (A) 手動離脱 と (B) 押し出し を区別できないため、区別はこのハンドラ層
    の不変条件確立で担保する（TestReconcileWindowStart docstring 参照）。
    """

    def _make_stub(self, window_start=0, page_size=20, current_page=5, n=47):
        calls = {"page_change": 0}
        stub = types.SimpleNamespace(
            _page_window_start=window_start,
            _page_size=page_size,
            current_page=current_page,
            doc=[None] * n,
            thumb_cache={},
            settings={},
            plugin_manager=types.SimpleNamespace(
                fire_event=lambda *a, **k: calls.__setitem__(
                    "page_change", calls["page_change"] + 1
                )
            ),
        )
        stub._refresh_all = lambda: None
        stub._set_status = lambda msg: None
        stub._move_window = lambda direction: ViewerMixin._move_window(stub, direction)
        stub._calls = calls
        return stub

    def test_next_window_moves_current_into_new_window(self):
        # current=5（窓1 在）で次窓へ → window_start=20・current も新窓先頭 20 へ追従。
        stub = self._make_stub(window_start=0, current_page=5, n=47)
        ViewerMixin._next_window(stub)
        assert stub._page_window_start == 20
        assert stub.current_page == 20
        lo, hi = window_bounds(stub._page_window_start, 20, 47)
        assert lo <= stub.current_page < hi

    def test_prev_window_moves_current_into_new_window(self):
        # current=45（窓3 在）で前窓へ → window_start=20・current も 20 へ追従。
        stub = self._make_stub(window_start=40, current_page=45, n=47)
        ViewerMixin._prev_window(stub)
        assert stub._page_window_start == 20
        assert stub.current_page == 20

    def test_move_window_invariant_keeps_current_inside(self):
        # 旧バグ再現入力（窓2 在で current=窓1）は _move_window 経由では生じ得ない。
        # 任意の窓・方向で移動後、current は必ず新窓内（= window_start）に収まる。
        handlers = ((ViewerMixin._prev_window), (ViewerMixin._next_window))
        for ws in (0, 20, 40):
            for handler in handlers:
                stub = self._make_stub(window_start=ws, current_page=ws, n=47)
                handler(stub)
                lo, hi = window_bounds(
                    stub._page_window_start, stub._page_size, len(stub.doc)
                )
                assert lo <= stub.current_page < hi
                assert stub.current_page == stub._page_window_start

    def test_no_doc_is_noop(self):
        stub = self._make_stub()
        stub.doc = None
        before = stub.current_page
        ViewerMixin._next_window(stub)
        assert stub.current_page == before
        assert stub._calls["page_change"] == 0

    def test_fires_page_change_event(self):
        stub = self._make_stub(window_start=0, current_page=5, n=47)
        ViewerMixin._next_window(stub)
        assert stub._calls["page_change"] == 1
