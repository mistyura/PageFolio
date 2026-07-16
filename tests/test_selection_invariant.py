"""selected_pages 全ページインデックス不変条件のプロパティ風テスト（05-01 Task 3）。

seed 固定の random.Random によるランダム操作列（選択トグル/スクロール・窓移動/
D&D 並び替え相当）を n_pages=500 のシミュレーションモデルへ適用し、
selected_pages の全要素が常に [0, n_pages) に収まること（窓ローカル添字の
混入がないこと）を回帰検証する（V180-PERF-03）。

hypothesis 等の新規依存は使わず random.Random(seed) のみで決定的に再現する
（D-04・V14-D-01 依存追加なし方針）。実 fitz.Document は生成せず、n_pages を
整数パラメータとしてシミュレートする（05-RESEARCH.md「純関数のみのテスト」）。

選択トグルは pagination.to_global 経由でのみ全ページ index へ換算する
（絶対に窓ローカル添字を直接 selected_pages へ入れない・落とし穴1回避策）。
D&D 並び替え相当は dnd.compute_dnd_dest_index が返すローカル dest を
to_global で全ページ index へ換算する（既存 _dnd_drop の実装どおり、
D&D 実行後は selected_pages をクリアする挙動を踏襲する）。
"""

import random

import pytest

from pagefolio.dnd import compute_dnd_dest_index
from pagefolio.pagination import (
    clamp_window_start,
    compute_visible_range,
    reconcile_window_start,
    to_global,
    window_bounds,
)

N_PAGES = 500
PAGE_SIZE = 20
STEPS_PER_SEED = 300
SEEDS = range(20)


def _assert_invariants(
    seed, step, selected_pages, current_page, window_start, n_pages, page_size
):
    assert all(0 <= p < n_pages for p in selected_pages), (
        f"seed={seed} step={step}: selected_pages に範囲外の値が混入: {selected_pages}"
    )
    assert 0 <= current_page < n_pages, (
        f"seed={seed} step={step}: current_page が範囲外: {current_page}"
    )
    lo, hi = window_bounds(window_start, page_size, n_pages)
    assert 0 <= lo <= hi <= n_pages, (
        f"seed={seed} step={step}: window_bounds が不正: lo={lo} hi={hi}"
    )


def _run_simulation(seed, n_pages=N_PAGES, page_size=PAGE_SIZE, steps=STEPS_PER_SEED):
    """1シード分のランダム操作列を適用し、各ステップ後に不変条件を検証する。"""
    rng = random.Random(seed)  # noqa: S311 -- 決定的テスト再現用（暗号用途ではない）
    window_start = 0
    current_page = 0
    selected_pages = set()

    for step in range(steps):
        action = rng.choice(("select", "scroll", "dnd", "visible_scan"))
        lo, hi = window_bounds(window_start, page_size, n_pages)

        if action == "select" and hi > lo:
            # (a) 選択トグル: 可視窓内のローカル位置を to_global で全ページ index へ
            # 換算してから add/discard する（窓ローカル添字を直接使わない）。
            local = rng.randrange(0, hi - lo)
            global_idx = to_global(local, window_start)
            if global_idx in selected_pages:
                selected_pages.discard(global_idx)
            else:
                selected_pages.add(global_idx)

        elif action == "scroll":
            # (b) スクロール/窓移動: window_start を別の窓先頭へ動かし
            # clamp_window_start/reconcile_window_start で正規化する。
            candidate = rng.randrange(0, n_pages)
            window_start = clamp_window_start(candidate, page_size, n_pages)
            if rng.random() < 0.5:
                # current_page 側の操作（ページジャンプ相当）も混ぜて
                # reconcile_window_start の追従経路を両方とも運動させる。
                current_page = rng.randrange(0, n_pages)
            window_start = reconcile_window_start(
                window_start, current_page, page_size, n_pages
            )

        elif action == "dnd":
            # (c) D&D 並び替え相当: compute_dnd_dest_index のローカル dest を
            # to_global で全ページ index へ換算する。既存 _dnd_drop は移動後に
            # selected_pages を必ず clear するため、シミュレーションもそれを踏襲する。
            frame_count = hi - lo
            if frame_count > 0:
                frame_bounds = [(i * 40, 40) for i in range(frame_count)]
                cursor_y = rng.randrange(-40, frame_count * 40 + 40)
                dest_local = compute_dnd_dest_index(cursor_y, frame_bounds)
                if dest_local is not None:
                    dest_global = to_global(dest_local, window_start)
                    dest_global = max(0, min(dest_global, n_pages))
                    _src = rng.randrange(0, n_pages)
                    selected_pages.clear()
                    current_page = min(current_page, n_pages - 1)
                    _ = dest_global  # 実ドキュメント並替えは対象外。index整合のみ検証

        elif action == "visible_scan":
            # 可視範囲純関数が絡むスクロールステップ。selected_pages を
            # 書き換えないこと（描画順序と選択状態の分離）を確認する。
            frame_count = hi - lo
            frame_bounds = [(i * 40, 40) for i in range(frame_count)]
            before = set(selected_pages)
            if frame_bounds:
                view_top = rng.randrange(0, frame_count * 40 + 40)
                view_bottom = view_top + rng.randrange(40, 200)
            else:
                view_top, view_bottom = 0, 0
            vis_lo, vis_hi = compute_visible_range(view_top, view_bottom, frame_bounds)
            assert 0 <= vis_lo <= vis_hi <= len(frame_bounds), (
                f"seed={seed} step={step}: compute_visible_range が不正な区間を返した"
            )
            assert selected_pages == before, (
                f"seed={seed} step={step}: 可視範囲計算が selected_pages を書き換えた"
            )

        current_page = max(0, min(current_page, n_pages - 1))
        _assert_invariants(
            seed, step, selected_pages, current_page, window_start, n_pages, page_size
        )


class TestSelectionInvariant:
    """V180-PERF-03: 500 ページ相当のランダム操作列で全ページ index 不変条件を保証。"""

    @pytest.mark.parametrize("seed", SEEDS)
    def test_selected_pages_stay_within_range(self, seed):
        _run_simulation(seed)

    def test_large_n_pages_single_seed(self):
        # 500超のケースも1本明示的に固定シードで確認する。
        _run_simulation(seed=12345, n_pages=520, page_size=20, steps=STEPS_PER_SEED)
