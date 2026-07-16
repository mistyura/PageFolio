# Phase 5: 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正） - Pattern Map

**Mapped:** 2026-07-16
**Files analyzed:** 9（改修4・新設想定5、うち新規モジュールは D-08 の計画時判断待ち）
**Analogs found:** 9 / 9（全ファイル、改修対象そのものが最良の analog＝自己改修のため「既存自身のコード」を analog として扱う）

このフェーズは新機能追加ではなく、既存4ファイルの内部改修＋対応するテストの新設/拡張である。したがって「analog」は他ファイルではなく主に**改修対象ファイル自身の隣接コード**（同一ファイル内の既存パターン）であり、一部のみ他ファイルから流用する（`dnd.py` の座標変換分離パターン等）。

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `pagefolio/viewer.py`（`_build_thumbnails`/`_get_thumb_photo`/`_invalidate_thumb_cache` 改修） | component（Tkinter描画） | event-driven（スクロール/after連鎖） | 自己（同ファイル内 `render_next`/`_thumb_gen` 世代ガード） + `pagefolio/dnd.py`（座標変換分離） | exact（自己改修） |
| `pagefolio/pagination.py`（可視範囲純関数・LRUコンテナ追加） | utility（純ロジック層） | transform | 自己（同ファイル内の既存純関数群） | exact |
| 新規 `pagefolio/thumb_cache.py` または `pagination.py` 追加（D-08 配置次第） | utility（LRUコンテナ） | CRUD（get/put/pop/clear） | `pagefolio/undo_store.py`（`UndoBlobStore` の Tk非依存クラス設計・`__slots__`規約なし版） | role-match |
| `pagefolio/undo_store.py`（`MemBlob`/`FileBlob` に `_released`＋`__del__` 追加） | model（Blobライフサイクル） | event-driven（GC時） | 自己（同ファイル内 `release()`/`__slots__` 規約） | exact |
| `pagefolio/app.py`（フォーカスガード純関数追加・`_bind_shortcuts` 改修） | utility＋controller（ショートカット発火面） | request-response | 自己（同ファイル内 `build_keysym_from_event`/`find_duplicate_binding` 等の純関数群・`_bind_shortcuts`） | exact |
| `pagefolio/dialogs/shortcuts.py`（`_start_capture` のWR-01修正） | component（ダイアログ） | request-response | 自己（同ファイル内 `_end_capture`/`_refresh_row`） | exact |
| `tests/test_pagination.py`（可視範囲純関数・LRUユニットテスト追加） | test | unit | 自己（既存の同ファイル内テストパターン） | exact |
| `tests/test_undo_stress.py`（D-14の3項目追加） | test | stress/unit | 自己（`_make_stress_app`/`FakeApp`パターン） | exact |
| `tests/test_selection_invariant.py`（新規・プロパティ風テスト） | test | property-based | `tests/test_pagination.py`（純関数のみ・Tk root不要のテストスタイル） | role-match |
| `tests/test_shortcuts_dialog.py`（新規・WR-01/WR-02回帰テスト） | test | unit | `tests/test_batch_ocr_dialog.py`（Tk root併用パターン）＋ `tests/test_viewer.py`（純ロジックスタブパターン） | role-match |

## Pattern Assignments

### `pagefolio/viewer.py` の改修（`_build_thumbnails`/`_get_thumb_photo`/`_invalidate_thumb_cache`）

**Analog:** 自己（`pagefolio/viewer.py:280-378`）＋座標変換分離は `pagefolio/dnd.py:12-29,94-106`

**Imports pattern**（`viewer.py:1-25`、変更不要・追加時はここに追記）:
```python
import logging
import tkinter as tk
from tkinter import ttk

import fitz
from PIL import Image, ImageTk

from pagefolio.constants import C
from pagefolio.pagination import (
    clamp_page_size,
    clamp_window_start,
    reconcile_window_start,
    to_global,
    window_bounds,
    window_for_page,
    window_label,
    window_nav_state,
)

logger = logging.getLogger(__name__)
```
LRU/可視範囲純関数を `pagination.py`（または新規モジュール）に追加した場合、ここの import 群に追記する（既存の並び・アルファベット順は緩やかに踏襲）。

**現行レンダリング連鎖パターン（改修対象そのもの）**（`viewer.py:280-310`）:
```python
def _build_thumbnails(self):
    self._thumb_gen += 1
    gen = self._thumb_gen
    for w in self.thumb_inner.winfo_children():
        w.destroy()
    self.thumb_images.clear()
    if not self.doc:
        return
    lo, hi = window_bounds(self._page_window_start, self._page_size, len(self.doc))
    placeholder_labels = [self._add_thumb_placeholder(i) for i in range(lo, hi)]

    def render_next(i):
        if self._thumb_gen != gen or not self.doc:
            logger.debug(
                "サムネイルレンダリングスキップ: gen=%s, current_gen=%s",
                gen,
                self._thumb_gen,
            )
            return
        if i >= hi:
            return
        photo = self._get_thumb_photo(i)
        frame, lbl = placeholder_labels[i - lo]
        lbl.configure(image=photo)
        self.thumb_images.append(photo)
        self.root.after(0, lambda: render_next(i + 1))

    self.root.after_idle(lambda: render_next(lo))
```
**改修方針（D-01〜D-03）:** `render_next` の呼び出し順を「可視範囲優先キュー→窓内残りは `after_idle`」の2段に変える。`gen`/`self._thumb_gen != gen` の世代ガード条件は**そのまま維持**（呼び出し順序が変わってもガードの成立条件は不変）。可視範囲計算は `dnd.py:94-106` の `_dnd_dest_index` と同じ分離方式（Tk依存の座標収集は `viewer.py` 側メソッド、比較・変換ロジックは `pagination.py` 純関数）に倣うこと。

**現行 thumb_cache（無制限 dict・置換対象）**（`viewer.py:136-154`）:
```python
def _invalidate_thumb_cache(self, pages=None):
    if pages is None:
        self.thumb_cache.clear()
    else:
        for p in pages:
            self.thumb_cache.pop(p, None)

def _get_thumb_photo(self, i):
    if i in self.thumb_cache:
        return self.thumb_cache[i]
    page = self.doc[i]
    zoom = getattr(self, "thumb_zoom_var", None)
    z = zoom.get() if zoom else 1.0
    mat = fitz.Matrix(0.22 * z, 0.22 * z)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    photo = ImageTk.PhotoImage(img)
    self.thumb_cache[i] = photo
    return photo
```
**改修方針（D-05〜D-08）:** `self.thumb_cache = {}`（`app.py:170`）を LRU コンテナのインスタンスへ置換する。呼び出し面（`in` 判定・`[i]` 取得・`[i] =` 代入・`.pop(p, None)`・`.clear()`）は上記コードのまま動くよう、新設 LRU クラスに `__contains__`/`__getitem__`/`__setitem__`/`pop`/`clear` を実装するか、このメソッド自体を新 API（`get`/`put`/`pop`/`clear`）呼び出しへ書き換えるかは計画時判断（RESEARCH.md Pattern 3 の `LruCache` は `get`/`put` 方式）。

**Integration point:** `app.py:170` の `self.thumb_cache = {}` 初期化箇所も同時に改修対象（LRU コンテナのインスタンス生成に置換）。

---

### `pagefolio/pagination.py` への可視範囲純関数・LRU追加

**Analog:** 自己（既存の純関数群スタイル）

**モジュール docstring・非依存宣言パターン**（`pagination.py:1-22`、新規関数追加時もこの方針を厳守）:
```python
"""ページネーション純ロジック層 — Tkinter / fitz 非依存。
...
ここには `fitz` / `tkinter` を一切 import しない（viewer.py:40-49 の純関数作法に倣う）。
"""
```

**既存純関数の型（docstring・不変条件明記・堅牢性コメントの書式）**（`pagination.py:25-46`）:
```python
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
```
新規の可視範囲オフセット計算関数（例: `visible_range(scroll_top_frac, scroll_bottom_frac, lo, hi)` 等の名称は計画時確定）はこの書式（Google風より簡潔な日本語docstring・決定ID引用・堅牢性エッジケースの明記）に従う。**必ず `window_bounds`/`to_global`/`to_local` と合成する形で実装し、新規座標系を作らない**（落とし穴1回避策・PATTERNS.md冒頭の中心的制約）。

**LRUコンテナの配置指針:** RESEARCH.md Pattern 3 の `LruCache`（`OrderedDict` ベース）をこのファイル内に追加するか、独立モジュール（`pagefolio/thumb_cache.py`）に切り出すかは D-08/Open Question 1 のとおり計画時判断。いずれの場合も `pagination.py` の「Tk/fitz 非依存」原則を継承すること。

---

### `pagefolio/undo_store.py` の `MemBlob`/`FileBlob` へのリーク検出追加

**Analog:** 自己（`undo_store.py:36-74`）

**現行の `__slots__`・release パターン（変更対象）**:
```python
# Source: pagefolio/undo_store.py:57-74
class FileBlob:
    """閾値以上のデータを一時ファイルへ退避する Blob。"""

    __slots__ = ("path", "size")

    def __init__(self, path, size):
        self.path = path
        self.size = size

    def load(self):
        """一時ファイルから bytes を読み出して返す。"""
        with open(self.path, "rb") as f:
            return f.read()

    def release(self):
        """一時ファイルを削除する。ロック等の失敗は purge/atexit に委ねる。"""
        with contextlib.suppress(OSError):
            os.unlink(self.path)
```
**改修方針（D-11〜D-13）:** `__slots__` に `"_released"` を追加し `__init__` で `self._released = False`。`release()` 冒頭で二重呼び出し検出（`if self._released: logger.warning(...); return`）を追加。`__del__` を新設し `sys.is_finalizing()` チェック＋`_released` 判定＋警告ログ＋ベストエフォート `os.unlink` を行う（RESEARCH.md Pattern 4 の提案実装を参照するが、**Anti-Pattern 注記のとおり `except Exception: pass`（メッセージなし）は CLAUDE.md の「裸の except 禁止」規約に抵触するため `except Exception as e:` へ修正すること**）。同じ改修を `MemBlob`（`undo_store.py:36-54`）にも `_released` フラグ導入という形で適用する（メモリ解放のみなので `__del__` でのリーク検出は「解放されずに GC された」警告ログのみで `unlink` 相当の回収処理は不要）。

**Import 追加**（`undo_store.py:23-30`、`sys` を追記）:
```python
import atexit
import contextlib
import logging
import os
import shutil
import tempfile
# 追加: import sys（sys.is_finalizing() 用）

logger = logging.getLogger(__name__)
```

**既存の呼び出し面（変更不要・維持すべき契約）:** `pagefolio/file_ops.py` の `_capture_page_blob`/`_blob_bytes`/`_push_evicting`/`_clear_undo_stacks`（56, 69, 102, 119行目）は Blob の `release()`/`load()` のみ呼ぶため、`_released`/`__del__` 追加後もシグネチャ不変で無改造のはず。ただし `_push_evicting`（スタック溢れ時の release 呼び出し）・`_clear_redo_stack`（redoクリア時の release）が正しく `release()` を呼んでいることを D-14②（double-release検出）テストで確認する対象になる。

---

### `pagefolio/app.py` へのフォーカスガード純関数追加・`_bind_shortcuts` 改修

**Analog:** 自己（`app.py:35-104` の純関数群＋`app.py:229-260` の `_bind_shortcuts`）

**既存の純関数群の書式（新規 `should_suppress_for_focused_input` もこの隣に同形式で追加）**（`app.py:56-87`）:
```python
def build_keysym_from_event(
    state, keysym, shift_mask=0x1, control_mask=0x4, alt_mask=0x20000
):
    """event.state ビットマスクと event.keysym から Tk bind 用文字列を組み立てる。

    ショートカット GUI 編集の実キーキャプチャ方式を支える純関数（V171-UIUX-01・D-02）。
    修飾は Control, Alt, Shift の順で連結し、修飾なしの場合はキー単体を返す。
    """
    mods = []
    if state & control_mask:
        mods.append("Control")
    if state & alt_mask:
        mods.append("Alt")
    if state & shift_mask:
        mods.append("Shift")
    if not mods:
        return f"<{keysym}>"
    return f"<{'-'.join(mods)}-{keysym}>"


def find_duplicate_binding(shortcuts, cmd_name, new_keysym):
    """新規割当キーが自分以外のコマンドと重複していないか判定する。

    重複割当を保存時に拒否する要件を支える純関数（V171-UIUX-01・D-04）。
    衝突しているコマンド名を返し、衝突がなければ None を返す。
    """
    if not new_keysym:
        return None
    for other_cmd, other_keysym in shortcuts.items():
        if other_cmd != cmd_name and other_keysym == new_keysym:
            return other_cmd
    return None
```
新規ガード関数はRESEARCH.md Pattern 5 の提案（`should_suppress_for_focused_input(keysym, focused_widget_class)`）に沿い、この直後（`app.py:87` 付近、`find_duplicate_binding` の後・`keysym_to_display` の前）に追加するのが自然。

**現行の発火面（改修対象）**（`app.py:229-260`）:
```python
def _bind_shortcuts(self):
    """settings["shortcuts"] から現在のキーバインドを（再）構築する（D-05）。

    再呼び出し時は前回バインドした keysym（shift variant 含む）を
    先に unbind してから新設定で再バインドする（旧キーが残らない・Pitfall 1）。
    """
    for old_keysym in getattr(self, "_bound_keysyms", []):
        try:
            self.root.unbind(old_keysym)
        except Exception as e:
            logger.debug("ショートカット unbind 失敗: %s", e)

    custom_shortcuts = self.settings.get("shortcuts", {})
    shortcuts = merge_shortcuts(self._default_shortcuts, custom_shortcuts)

    bound = []
    for cmd_name, keysym in shortcuts.items():
        func = self._cmd_map.get(cmd_name)
        if func and keysym:
            try:
                self.root.bind(keysym, lambda e, f=func: f())
                bound.append(keysym)
                variant = shift_variant_keysym(keysym)
                if variant is not None:
                    self.root.bind(variant, lambda e, f=func: f())
                    bound.append(variant)
            except Exception as ex:
                logger.warning(
                    f"Failed to bind shortcut {keysym} for {cmd_name}: {ex}"
                )
    self._bound_keysyms = bound
```
**改修方針（D-09/D-10、RESEARCH.md Open Question 2 の推奨）:** `self.root.bind(keysym, lambda e, f=func: f())` を、`event`（`e`）を実際に使うラムダへ変更しガード判定を挿入する:
```python
self.root.bind(
    keysym,
    lambda e, f=func, ks=keysym: (
        None
        if should_suppress_for_focused_input(
            ks,
            self.root.focus_get().winfo_class() if self.root.focus_get() else "",
        )
        else f()
    ),
)
```
`variant`（Shift補完版）のバインドにも同様のガードを適用する。`self.root.focus_get()` が `None` を返すケース（フォーカスなし）を防御的に扱うこと（RESEARCH.md Open Question 2 に明記）。

---

### `pagefolio/dialogs/shortcuts.py` の `_start_capture` WR-01修正

**Analog:** 自己（`shortcuts.py:179-204`）

**現行の `_start_capture`/`_end_capture`/`_refresh_row`（改修対象・原因箇所）**:
```python
# Source: pagefolio/dialogs/shortcuts.py:179-204
def _refresh_row(self, cmd_name):
    label = self._key_labels.get(cmd_name)
    if label is not None:
        label.configure(text=self._display_text(cmd_name))

def _refresh_all_rows(self):
    for cmd_name, _label_key in _CMD_ORDER:
        self._refresh_row(cmd_name)

# ── キャプチャ（変更）──────────────────────────────────────────
def _start_capture(self, cmd_name):
    if self._capturing_cmd is not None:
        self._end_capture()
    self._capturing_cmd = cmd_name
    label = self._key_labels.get(cmd_name)
    if label is not None:
        label.configure(text=self._L["shortcuts_capture_waiting"])
    self.bind("<KeyPress>", self._on_capture_keypress)
    self.focus_set()

def _end_capture(self):
    self._capturing_cmd = None
    try:
        self.unbind("<KeyPress>")
    except Exception as e:
        logger.debug("キャプチャ bind 解除失敗: %s", e)
```
**改修方針（CONTEXT.md Discretion欄・WR-01修正案そのもの）:** `_start_capture` 冒頭で旧 `_capturing_cmd` を変数へ保持してから `_end_capture()` を呼び、その旧コマンド名に対して `_refresh_row()` を呼ぶ:
```python
def _start_capture(self, cmd_name):
    if self._capturing_cmd is not None:
        prev_cmd = self._capturing_cmd
        self._end_capture()
        self._refresh_row(prev_cmd)   # ← WR-01修正: 旧行表示を復元
    self._capturing_cmd = cmd_name
    label = self._key_labels.get(cmd_name)
    if label is not None:
        label.configure(text=self._L["shortcuts_capture_waiting"])
    self.bind("<KeyPress>", self._on_capture_keypress)
    self.focus_set()
```
`_refresh_row`（`shortcuts.py:179-182`）・`_display_text`（`shortcuts.py:165-171`）は無改造で流用できる（旧行が捕捉中でなければ通常の keysym 表示に戻る）。

**既存の例外処理規約（踏襲すべき書式）**（`shortcuts.py:199-204`）:
```python
def _end_capture(self):
    self._capturing_cmd = None
    try:
        self.unbind("<KeyPress>")
    except Exception as e:
        logger.debug("キャプチャ bind 解除失敗: %s", e)
```
CLAUDE.md 禁止事項（裸の except 禁止）どおり `except Exception as e:` 形式。新規コードもこの書式を厳守する。

---

## Shared Patterns

### Tk/fitz 非依存の純ロジック層への集約（Established Pattern）
**Source:** `pagefolio/pagination.py`（モジュール全体）・`pagefolio/undo_store.py`（モジュール全体）・`pagefolio/app.py:35-104`
**Apply to:** 可視範囲純関数（`pagination.py`）・LRUコンテナ・フォーカスガード判定関数（`app.py`）のすべて
```python
"""XXX純ロジック層 — Tkinter / fitz 非依存。
...
ここには `fitz` / `tkinter` を一切 import しない。
"""
```
新規純関数は必ず module-level function（クラスメソッドでなく）とし、Tk依存の座標収集/ウィジェット参照は呼び出し側（`viewer.py`/`app.py` の薄いラッパー）に残す。

### 世代カウンタによる陳腐化結果破棄（Established Pattern）
**Source:** `pagefolio/viewer.py:280-282,294`（`self._thumb_gen`）
```python
def _build_thumbnails(self):
    self._thumb_gen += 1
    gen = self._thumb_gen
    ...
    def render_next(i):
        if self._thumb_gen != gen or not self.doc:
            return
```
デバウンス改修（D-02）後もこのガード条件はそのまま再利用する。新設のデバウンスタイマー自体も同様に「タイマー発火時に現在の gen と一致するか」を確認すること。

### 例外処理（裸の except 禁止・CLAUDE.md 規約）
**Source:** `pagefolio/app.py:141-142,236-239,256-259`・`pagefolio/dialogs/shortcuts.py:202-204`
```python
try:
    ...
except Exception as e:
    logger.debug("...: %s", e)   # または logger.warning(f"...: {ex}")
```
`__del__` 内の例外握り潰し（Blobリーク検出）もこの規約に従う。RESEARCH.md Pattern 4 のサンプルにある `except Exception: pass`（メッセージなし）はそのまま使わず修正すること。

### 純関数のみのテスト（Tk root不要・推奨アプローチ）
**Source:** `tests/test_pagination.py`（既存全体）・`tests/test_viewer.py:15-23`
```python
def _make_stub(doc):
    stub = types.SimpleNamespace(doc=doc)
    stub._render_preview_pixmap = ViewerMixin._render_preview_pixmap.__get__(stub)
    return stub
```
D-04 のプロパティ風テスト（`test_selection_invariant.py`）・可視範囲純関数/LRUのユニットテストはこの形式（`types.SimpleNamespace` スタブ＋対象メソッドをバインド、または純関数を直接呼ぶだけ）を踏襲し、`fitz.Document`/`tk.Tk()` の生成コストを避ける。

### Blobテストハーネス（`FakeApp`パターン）
**Source:** `tests/test_undo_stress.py:54-81`
```python
def _make_stress_app(doc, max_undo=20):
    class FakeApp(fo.FileOpsMixin, ro.RedactOpsMixin):
        MAX_UNDO = max_undo

        def __init__(self, d):
            self.doc = d
            self.current_page = 0
            self.selected_pages = set()
            self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
            self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
            self._preview_gen = 0
            self._thumb_gen = 0

        def _invalidate_thumb_cache(self, *a, **kw):
            pass
        ...
    app = FakeApp(doc)
    app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
    return app
```
D-14 の3項目（`os.unlink` を `PermissionError` にmock／insert→undo→redo→undo連鎖でdouble-release検出／`test_undo_stress.py`との連動tmpdir監視）はこのハーネスへ直接追加する。

### 実 Tk root を使うテストパターン（`ShortcutsDialog`テストで必要な場合）
**Source:** `tests/test_batch_ocr_dialog.py`（モジュールスコープ fixture）
```python
@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()
```
`test_shortcuts_dialog.py` は WR-01（`_start_capture`/`_end_capture`/`_refresh_row` の実ウィジェット状態検証）にこのパターンの流用を検討する。WR-02（フォーカスガード純関数自体のテスト）は Tk root 不要な純関数呼び出しのみで足りる。

## No Analog Found

該当なし。全ファイルが既存ファイルの内部改修または既存テストパターンの直接延長であり、ゼロから設計する新規analogレスファイルはない（新規モジュール `pagefolio/thumb_cache.py` を採用する場合でも `undo_store.py` を role-match analogとして扱える）。

## Metadata

**Analog search scope:** `pagefolio/`（`viewer.py`・`pagination.py`・`undo_store.py`・`app.py`・`dnd.py`・`dialogs/shortcuts.py`）・`tests/`（`test_pagination.py`・`test_viewer.py`・`test_undo_stress.py`・`test_batch_ocr_dialog.py`）
**Files scanned:** 9（全文読解）
**Pattern extraction date:** 2026-07-16
