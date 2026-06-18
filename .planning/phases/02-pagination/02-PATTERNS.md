# Phase 2: 大量ページのページネーション表示 - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 7（変更 6 + 新規 1〜2）
**Analogs found:** 7 / 7（全ファイルにコードベース内アナログあり）

本フェーズの「新規ロジック」は **index 変換と窓計算の純関数群だけ**である（RESEARCH.md「Don't Hand-Roll / Key insight」）。
ページ操作・選択ロジック・描画競合制御・永続化はすべて既存資産が全ページ index 前提で正しく、`selected_pages` の不変条件（常に全ページ 0 始まり index の set）を保つ限り無改修で再利用できる。
よって本マップは「新規純関数をどの既存純関数の作法に倣うか」と「既存メソッドのどこに local↔global 変換を 1 箇所だけ挿し込むか」に焦点を当てる。

---

## File Classification

| 新規/変更ファイル | Role | Data Flow | 最も近いアナログ | Match |
|---|---|---|---|---|
| `pagefolio/pagination.py`（新規・推奨）または `viewer.py` 内 `@staticmethod` | utility（純ロジック） | transform | `viewer.py` `_render_preview_pixmap`（40-49 = 純ロジック作法） | role-match |
| `pagefolio/viewer.py`（変更） | viewer mixin | event-driven / render | 自ファイル既存メソッド（`_build_thumbnails` / `_refresh_thumbs_selection_only` / `_on_thumb_zoom_release`） | exact（自己改修） |
| `pagefolio/ui_builder.py`（変更） | UI builder mixin | request-response（ウィジェット構築） | 自ファイル `_build_thumb_panel` の `zoom_frame` / `sel_frame` 行（191-211） | exact |
| `pagefolio/dnd.py`（変更） | dnd mixin | event-driven | 自ファイル `_dnd_drop` / `_dnd_dest_index`（73-135） | exact |
| `pagefolio/settings.py`（変更） | config | CRUD（JSON 永続化） | `_load_settings` の `defaults` dict（45-65） | exact |
| `pagefolio/lang.py`（変更） | config（i18n） | — | 既存 `panel_pages` / `select_all` キー（ja:12-15 / en:452-455） | exact |
| `tests/test_pagination.py`（新規） | test | unit（純ロジック検証） | `tests/test_viewer.py` の `_make_stub` 方式（1-62） | exact |

---

## Pattern Assignments

### `pagefolio/pagination.py`（新規・純ロジック変換層, utility/transform）

**Analog:** `pagefolio/viewer.py` `_render_preview_pixmap`（viewer.py:40-49）— Tk 非依存・引数→戻り値・状態非依存の純関数作法。

**配置裁量（RESEARCH.md 推奨）:** モジュール関数として `pagefolio/pagination.py` に置く方式を**弱く推奨**（テストが `from pagefolio.pagination import window_bounds` で済み Mixin スタブ不要）。代替は `viewer.py` に `@staticmethod` を置く方式（test_viewer.py の `__get__(stub)` バインド方式に倣う）。**どちらか一方に統一**すること（RESEARCH.md A2）。

**倣うべき純関数作法（viewer.py:40-49）:**
```python
def _render_preview_pixmap(self, page_idx, zoom):
    """Tk 非依存の純関数プレビューレンダリングヘルパー。"""
    page = self.doc[page_idx]
    mat = fitz.Matrix(zoom * 1.5, zoom * 1.5)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return bytes(pix.samples), pix.width, pix.height
```
→ 同様に「docstring で責務明記・引数のみ参照・戻り値で返す」スタイルで以下 7 関数を実装（RESEARCH.md Pattern 1 / Code Examples にシグネチャと本体案あり）:
`window_bounds(window_start, page_size, n_pages) -> (lo, hi)`、`to_global(local_pos, window_start)`、`to_local(global_idx, window_start)`、`window_for_page(page_idx, page_size) -> start`、`clamp_window_start(window_start, page_size, n_pages)`、`window_label(window_start, page_size, n_pages) -> str`、`window_nav_state(window_start, page_size, n_pages) -> (prev, next)`。

**不変条件（テストで固定）:** `0 <= lo <= hi <= n`、`hi-lo <= page_size`、`to_global(to_local(g,s),s)==g`、`window_for_page` は `% page_size == 0` を保証、`window_nav_state` 単一窓は `(False, False)`（RESEARCH.md Validation Architecture の表）。

---

### `pagefolio/viewer.py`（変更, viewer mixin / render）

**Analog:** 自ファイル既存メソッド（自己改修）。

**1. `_build_thumbnails`（197-225）— 窓範囲のみ描画へ。**
現状の全描画箇所（206-207）:
```python
placeholder_labels = [
    self._add_thumb_placeholder(i) for i in range(len(self.doc))
]
```
→ `lo, hi = window_bounds(self._page_window_start, self._page_size, len(self.doc))` を取り、`for i in range(lo, hi)` に変更。**`_add_thumb_placeholder(i)` の `i` は全ページ index のまま渡す**（RESEARCH.md Pattern 3 / A2 = src 側変換が不要になる構成）。`render_next` の `placeholder_labels[i]` 添字は窓ローカルへ要対応（リストは窓分のみ生成されるため `placeholder_labels[i - lo]` 等）。`_thumb_gen` 世代ガード（198-199, 210-216）は**そのまま維持**（RESEARCH.md Anti-Pattern「世代ガードを外さない」）。

**2. `_refresh_thumbs_selection_only`（174-195）— enumerate を global へ変換（Pitfall 1）。**
現状の照合（177-179）:
```python
for i, frame in enumerate(frames):
    is_sel = i in self.selected_pages
    is_cur = i == self.current_page
```
→ `g = to_global(i, self._page_window_start)` を取り、`is_sel = g in self.selected_pages` / `is_cur = g == self.current_page` に変更。**これを怠ると窓 2 以降で選択枠が全ページ分ずれる**（RESEARCH.md Pitfall 1）。`selected_pages` 自体はローカル化しない（D-07 不変条件）。

**3. `_on_thumb_zoom_release`（146-154）— 件数変更・窓移動ハンドラの定石手本。**
```python
def _on_thumb_zoom_release(self, event=None):
    self.settings["thumb_zoom"] = self.thumb_zoom_var.get()
    from pagefolio.settings import _save_settings
    _save_settings(self.settings)
    self._invalidate_thumb_cache()
    self._refresh_all()
```
→ 件数変更ハンドラ `_on_page_size_change` はこの「保存→無効化→再描画」を踏襲。ただし **`_invalidate_thumb_cache` は窓移動では呼ばない**（RESEARCH.md Pitfall 2 / A1: `thumb_cache` は `{全ページ index: PhotoImage}`〔133-144〕なので別窓と衝突せず、窓往復のたびに全クリアすると再レンダリングが走り高速化目的に反する）。件数変更も画像内容は不変のためキャッシュ無効化は本来不要。

**4. `_refresh_all`（157-172）— 窓正規化の集約点。**
ページ数や current が変わる操作後、描画直前にここで `self._page_window_start = clamp_window_start(...)` → `window_for_page(self.current_page, self._page_size)`（D-11 追従）を適用し、ナビ UI 状態（`window_nav_state`）とラベル（`window_label`）を更新するのが安全（RESEARCH.md Pitfall 5）。既存の prev/next ボタン state 制御（165-172）が窓ナビボタン state 制御のパターン手本。

**5. `_single_click`（296-301）/ `_prev_page`・`_next_page`（108-118）— current_page を変える箇所は窓追従のトリガ。** これらの後に `_refresh_all` が呼ばれる流れに窓正規化を載せれば D-11 を一元化できる。

---

### `pagefolio/ui_builder.py`（変更, UI builder mixin）

**Analog:** 自ファイル `_build_thumb_panel` の `zoom_frame`（200-211）/ `sel_frame`（191-198）行。

**追加位置:** canvas 群（213-239）の**後ろ**に新規フッター `tk.Frame` を `pack(fill="x")` で追加（D-02）。`zoom_frame` と同じ作法:
```python
zoom_frame = tk.Frame(parent, bg=C["BG_PANEL"])
zoom_frame.pack(fill="x", padx=6, pady=(0, 4))
self.thumb_zoom_var = tk.DoubleVar(value=self.settings.get("thumb_zoom", 1.0))
...
self.thumb_zoom_scale.bind("<ButtonRelease-1>", self._on_thumb_zoom_release)
```
→ フッター行に以下を配置（RESEARCH.md Standard Stack ウィジェット表）:
- `ttk.Button`（◀ / ▶）— `sel_frame` のボタン作法（193-198）を踏襲。`command=self._prev_window` / `_next_window`。state 制御は `_refresh_all` の prev/next パターン（viewer.py:165-172）に倣う。
- `tk.Label` — 範囲ラベル「1–20 / 全120」。`hdr` の Label 作法（176-189）。
- `ttk.Spinbox(from_=10, to=100, increment=10, state="readonly")` ＋ `tk.IntVar`（`self.page_size_var`）。初期値は `self.settings.get("thumb_page_size", 20)`（zoom の `self.settings.get("thumb_zoom", 1.0)` と同作法・202 行）。`command=self._on_page_size_change`。**`tk.Spinbox` ではなく `ttk.Spinbox` + `state="readonly"`** を使う（RESEARCH.md Pitfall 3 / MEMORY: tkinter-readonly-widget-gotchas — 範囲外値の混入と暗テーマ readonly 背景色問題を回避）。

色は必ず `C["..."]`、フォントは `self._font(...)`（CLAUDE.md 規約）。

---

### `pagefolio/dnd.py`（変更, dnd mixin / event-driven）

**Analog:** 自ファイル `_dnd_drop`（94-135）/ `_dnd_dest_index`（73-92）。

**`_dnd_drop`（94-135）— src は global のまま・dest だけ変換（D-06 / Pattern 3）。**
現状の冒頭（95-100）:
```python
src = self._dnd_src_idx
dest = self._dnd_dest_index(event)
if dest is None or src is None:
    return
n = len(self.doc)
dest = max(0, min(dest, n))
```
→ `_dnd_src_idx` は `_add_thumb_placeholder` のクロージャ束縛を全ページ index のまま保つ（viewer.py:242-243 の `idx=i` が `for i in range(lo, hi)` の `i` = 全ページ index）ので **src 変換は不要**。`dest` のみ:
```python
lo, hi = window_bounds(self._page_window_start, self._page_size, n)
dest = to_global(dest_local, lo)            # D-06: global = local + window_start
dest = max(0, min(dest, n))                 # 既存クランプ（100 行）を変換後に適用（Pitfall 4）
```
以降の `bulk_move`（101-117）/ `move_page`（118-135）は**無改修**。`selected_pages` が全ページ index を保つ限り（D-07）`new_order` 組み立て（103-107）はそのまま正しい（RESEARCH.md Don't Hand-Roll）。

**`_dnd_dest_index`（73-92）/ `_dnd_show_indicator`（47-66）:** 返す値は窓内フレーム位置（ローカル）のまま。インジケータ描画はローカルのフレーム配列（`thumb_inner.winfo_children()`）で完結するため変換不要。**変換は `_dnd_drop` の 1 箇所のみ**に集約（RESEARCH.md Anti-Pattern「`+ window_start` を散在させない」）。

---

### `pagefolio/settings.py`（変更, config / CRUD）

**Analog:** `_load_settings` の `defaults` dict（45-65）。

`defaults` に既存の数値設定（例 `"ocr_scale": 1.5` / 53 行）と同作法で 1 行追加:
```python
"thumb_page_size": 20,   # D-04: 既定 20、許容 10〜100
```
`setdefault` マージ機構（71-72）により旧 `pagefolio_settings.json`（キー無）でも 20 が補完される（後方互換・移行コード不要）。読み出しは `self.settings.get("thumb_page_size", 20)`。
**クランプ:** 手入力経路を作る場合は読み出し時に `max(10, min(100, value))`、空文字/非数値は `except (ValueError, tk.TclError)` で既定 20 フォールバック（裸 except 禁止・CLAUDE.md）。`ttk.Spinbox` readonly 採用なら原理的に範囲外は入らないが、settings 直読み時のクランプは堅牢性として推奨（RESEARCH.md Pitfall 3 / Security V5）。新規キーは数値設定で `_SENSITIVE_KEYS` 無関係。

---

### `pagefolio/lang.py`（変更, i18n）

**Analog:** 既存 `panel_pages` / `select_all` / `deselect` / `dnd_hint`（ja:12-15 / en:452-455）。

範囲ラベル等の新規キーを **ja / en 両方に同一キーで追加**（CLAUDE.md「LANG の新規キーは ja/en 両方に同一キーで」）。文言・区切り記号は実装裁量（D-01）。例: `"window_label"`（フォーマット文字列）、`"page_size_label"`（「表示:」「Show:」）等。`window_label` の f-string 生成は純関数側（pagination.py）で組むため、LANG にはフォーマット雛形のみ置く設計でもよい。

---

### `tests/test_pagination.py`（新規, test / unit）

**Analog:** `tests/test_viewer.py`（1-62）— 純関数 + `_make_stub` 方式。

pagination.py を**モジュール関数**で実装した場合は `_make_stub` 不要で直接 import:
```python
from pagefolio.pagination import window_bounds, to_global, window_for_page  # 等
```
`viewer.py` の `@staticmethod` 方式にした場合は test_viewer.py:15-23 の `__get__(stub)` バインド方式を踏襲。

**テストクラス構成（RESEARCH.md Validation Architecture / Phase要件→テストマップ）:** `TestWindowBounds`（D-10 端数）・`TestPageSizePersist`（SC2 クランプ）・`TestDndIndexConvert`（SC3）・`TestSelectionAcrossWindows`（SC4・D-07）・`TestWindowFollow`（D-11）・`TestNavState`（D-09）。境界値は RESEARCH.md「検証すべき不変条件・境界値」を網羅（n=0/n=1/件数≧全ページ/端数最終窓/往復不変条件）。

**フィクスチャ:** 既存 `sample_pdf_doc`（conftest.py:43-53, 3 ページ）は窓化境界値には小さい。**47 ページ等の多ページ doc フィクスチャを conftest に追加**すると境界テストが書きやすい（RESEARCH.md Wave 0 Gaps・任意）。ただし純関数は doc 不要（引数で n_pages を渡す）ため、変換/窓計算テストはフィクスチャ無しで書けるものが大半。`tests/**` は S101 除外済み（assert 可・CLAUDE.md）。

---

## Shared Patterns

### 設定変更 → 保存 → (無効化) → 再描画
**Source:** `pagefolio/viewer.py` `_on_thumb_zoom_release`（146-154）
**Apply to:** 件数変更ハンドラ `_on_page_size_change`、窓移動ハンドラ `_prev_window`/`_next_window`
**注意:** 件数変更は `_save_settings` 必須・窓移動は保存不要。**いずれも `_invalidate_thumb_cache` は呼ばない**（thumb_cache キーが全ページ index のため／RESEARCH.md Pitfall 2）。

### local↔global 変換の単一集約
**Source:** `pagefolio/pagination.py`（新規・本フェーズで作成）
**Apply to:** `_build_thumbnails`（描画範囲）・`_refresh_thumbs_selection_only`（選択照合）・`_dnd_drop`（ドロップ先換算）・`_refresh_all`（窓正規化/D-11 追従）
**不変条件:** `selected_pages` は常に全ページ 0 始まり index の set。ローカル化しない（D-07・RESEARCH.md Anti-Pattern）。

### 永続化（既定値マージ + 後方互換）
**Source:** `pagefolio/settings.py` `_load_settings` defaults（45-65）+ `setdefault`（71-72）
**Apply to:** `thumb_page_size`（既定 20）の追加。旧設定ファイル後方互換は `setdefault` が自動担保。

### ボタン enable/disable 状態制御
**Source:** `pagefolio/viewer.py` `_refresh_all`（165-172）prev/next 制御
**Apply to:** 窓ナビ ◀ ▶ ボタン（`window_nav_state` の (prev, next) を `.state(["!disabled"]/["disabled"])` へ反映）。単一窓でも行は常に描画・ボタンのみ disabled（D-09）。

### 純ロジックのヘッドレス検証
**Source:** `tests/test_viewer.py` `_make_stub`（15-23）+ `pyproject.toml` testpaths
**Apply to:** `tests/test_pagination.py`（モジュール関数なら直接 import で更に軽量）。

---

## No Analog Found

なし。本フェーズで触れる全ファイルに同一/近接のコードベース内アナログが存在する。
唯一の「新規」要素である純関数変換層も `_render_preview_pixmap`（viewer.py:40-49）という確立済みの Tk 非依存純関数作法に倣える。

---

## Metadata

**Analog search scope:** `pagefolio/`（viewer.py / dnd.py / ui_builder.py / settings.py / lang.py）、`tests/`（test_viewer.py / conftest.py）
**Files scanned:** 7
**Pattern extraction date:** 2026-06-18
