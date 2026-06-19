# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""ページネーション純ロジック層 — Tkinter / fitz 非依存。

「表示窓のローカル位置 ↔ 全ページインデックス」変換と窓計算を、
引数→戻り値・状態非依存の純関数に集約する（02-CONTEXT.md integration point）。
散在による窓またぎバグ（selected_pages / D&D の全ページインデックス整合）を
構造的に防ぐため、index 変換ロジックを 1 箇所に閉じ込める。

ここには `fitz` / `tkinter` を一切 import しない（viewer.py:40-49 の純関数作法に倣う）。
件数クランプ関数 `clamp_page_size` の名称はフェーズ内で確定名として固定し（W1）、
02-02 / 02-03 はこの名で import する。

参照決定: D-06（local→global 換算）/ D-07（窓またぎ選択保持）/
D-09（単一窓ナビ）/ D-10（端数最終窓）/ D-11（窓追従）。
"""

# 表示件数（ページサイズ）の許容範囲（D-04）
PAGE_SIZE_MIN = 10
PAGE_SIZE_MAX = 100
PAGE_SIZE_DEFAULT = 20


def window_bounds(window_start, page_size, n_pages):
    """表示窓の半開区間 (lo, hi) を返す。

    最終窓の端数を n_pages でクランプする（D-10）。
    不変条件: 0 <= lo <= hi <= n_pages、hi - lo <= page_size。
    n_pages<=0（doc 未オープン）では (0, 0) を返す（堅牢性・T-2-01）。
    """
    if n_pages <= 0:
        return (0, 0)
    lo = max(0, min(window_start, max(0, n_pages - 1)))
    hi = min(lo + page_size, n_pages)
    return (lo, hi)


def to_global(local_pos, window_start):
    """窓ローカル位置を全ページインデックスへ換算する（D-06）。"""
    return local_pos + window_start


def to_local(global_idx, window_start):
    """全ページインデックスを窓ローカル位置へ換算する（to_global の逆・D-06）。"""
    return global_idx - window_start


def window_for_page(page_idx, page_size):
    """page_idx を含む窓の先頭（page_size 倍数）を返す（D-11 追従の基礎）。

    page_size<=0 では 0 を返す（堅牢性・T-2-01）。
    不変条件: start % page_size == 0 かつ start <= page_idx < start + page_size。
    """
    if page_size <= 0:
        return 0
    return (page_idx // page_size) * page_size


def clamp_window_start(window_start, page_size, n_pages):
    """削除・件数変更後に window_start を有効窓の先頭へ寄せる。

    last_start = ((n_pages-1)//page_size)*page_size で範囲クランプする。
    n_pages<=0 or page_size<=0 では 0 を返す（堅牢性・T-2-01）。
    戻り値は必ず有効窓の先頭（< n_pages かつ % page_size == 0）。
    """
    if n_pages <= 0 or page_size <= 0:
        return 0
    last_start = ((n_pages - 1) // page_size) * page_size
    return max(0, min(window_start, last_start))


def reconcile_window_start(window_start, current_page, page_size, n_pages):
    """描画直前の窓正規化 + D-11 条件付き追従を 1 純関数に集約する。

    手順:
      1. clamp_window_start で window_start を有効窓の先頭へ寄せる
         （削除・件数変更で無効化した窓を救済）。
      2. current_page が正規化後の窓 [lo, hi) の **外** に出ている場合のみ
         window_for_page(current_page, page_size) でその窓へ追従する（D-11）。
         current_page が窓内に収まっている場合は手動ナビ（◀▶）/件数変更が
         設定した窓を温存し、current_page の窓へ snap back しない。

    D-11 原文（02-RESEARCH.md:21）: 「current_page が表示窓外へ出たら、その窓へ
    自動切替」。追従は **窓外条件付き** であり無条件ではない。
    n_pages<=0 or page_size<=0 では 0 を返す（堅牢性・T-2-01）。
    """
    normalized = clamp_window_start(window_start, page_size, n_pages)
    if n_pages <= 0 or page_size <= 0:
        return normalized
    lo, hi = window_bounds(normalized, page_size, n_pages)
    if current_page < lo or current_page >= hi:
        return window_for_page(current_page, page_size)
    return normalized


def window_label(window_start, page_size, n_pages):
    """1 始まりの範囲文字列を返す（D-09/D-10）。

    例: 件数 20・全 47・最終窓 → "41–47 / 全47"。
    n_pages==0 では空ドキュメントを示す既定文字列を返す。
    文言・区切り記号は呼び出し側（02-03 / LANG）の裁量と疎結合にするため
    本関数では数値部分を含む素朴な範囲文字列を生成する。
    """
    if n_pages <= 0:
        return "- / -"
    lo, hi = window_bounds(window_start, page_size, n_pages)
    return f"{lo + 1}–{hi} / 全{n_pages}"


def window_nav_state(window_start, page_size, n_pages):
    """前/次窓ボタンの活性状態 (prev_enabled, next_enabled) を返す。

    単一窓は (False, False)（D-09）。
    prev は lo > 0、next は hi < n_pages のとき有効。
    n_pages<=0 では (False, False) を返す。
    """
    if n_pages <= 0:
        return (False, False)
    lo, hi = window_bounds(window_start, page_size, n_pages)
    return (lo > 0, hi < n_pages)


def clamp_page_size(value):
    """表示件数を [PAGE_SIZE_MIN, PAGE_SIZE_MAX] にクランプする純ロジック（W1）。

    int 化して max(10, min(100, value)) を返す。
    int 化失敗・None・空文字は (ValueError, TypeError) を捕捉して既定 20 を返す
    （裸 except は使わず必ず例外型を指定・CLAUDE.md）。
    Tk 値 var.get() が空文字で送出しうる TclError は呼び出し側 02-03 で
    ハンドルするため、本純関数は Tk 非依存のまま ValueError/TypeError のみ捕捉。
    """
    try:
        n = int(value)
    except (ValueError, TypeError):
        return PAGE_SIZE_DEFAULT
    return max(PAGE_SIZE_MIN, min(PAGE_SIZE_MAX, n))
