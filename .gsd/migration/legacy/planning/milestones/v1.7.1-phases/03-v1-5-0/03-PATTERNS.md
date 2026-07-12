# Phase 3: ページ操作磨き込み + v1.5.0 回帰テスト - Pattern Map

**Mapped:** 2026-07-05
**Files analyzed:** 10（新規1・改修9）
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `pagefolio/page_ops.py`（`_add_watermark_image` 追加） | controller(Mixin) | request-response（UIイベント→fitz変更） | `pagefolio/page_ops.py:180 _add_watermark_text` | exact（同一ファイル内の同型メソッド） |
| `pagefolio/page_ops.py`（`_derotate_rect` 追加） | utility(純関数) | transform | `pagefolio/pagination.py`（純ロジック層パターン） | role-match（配置は static、依存は fitz.Page 1個のみ） |
| `pagefolio/page_ops.py`（`_crop_page`/`_crop_drag_move` 拡張: D-09/D-10/D-11） | controller(Mixin) | CRUD（矩形状態の読み書き） | `pagefolio/page_ops.py:253-347 _canvas_rect_to_pdf`〜`_crop_drag_move` | exact |
| `pagefolio/redact_ops.py`（`_apply_page_edit` 複数矩形化・mosaic block引数化） | controller(Mixin) | CRUD（破壊的PDF編集） | `pagefolio/redact_ops.py:72 _apply_page_edit` | exact |
| `pagefolio/ui_builder.py`（モザイクスライダー・クリアボタン・数値トリミング導線） | component(UI構築) | request-response | `pagefolio/ui_builder.py:200-211 thumb_zoom_scale` | exact |
| `pagefolio/dnd.py`（`compute_dnd_dest_index` 抽出） | utility(純関数) | transform | `pagefolio/pagination.py`（純ロジック層パターン） | role-match |
| `pagefolio/app.py`（`merge_shortcuts`/`shift_variant_keysym` 抽出） | utility(純関数) | transform | `pagefolio/pagination.py`（純ロジック層パターン） | role-match |
| `tests/test_v150_regression.py`（新規） | test | batch | `tests/test_pdf_ops.py:1469 TestContentOpsUndoFix`（FakeApp） + `tests/test_pagination.py`（純関数テスト） | exact（機能ごとに使い分け） |
| `tests/test_pdf_ops.py`（既存 `TestContentOpsUndoFix` へ内容検証追加・画像透かし/derotate/複数矩形/mm トリミング等の新規テストクラス） | test | batch | `tests/test_pdf_ops.py:1469 TestContentOpsUndoFix` | exact |
| `pagefolio/constants.py`（変更なし・`MOSAIC_BLOCK` 既定値として維持のみ） | config | — | 既存のまま | n/a |

## Pattern Assignments

### `pagefolio/page_ops.py` — `_add_watermark_image`（controller, request-response）

**Analog:** `pagefolio/page_ops.py:180-215 _add_watermark_text`

**Core パターン**（`page_ops.py:180-215`）:
```python
def _add_watermark_text(self):
    """選択ページにテキスト透かしを追加する"""
    if not self._check_doc():
        return
    targets = self._get_targets()
    text = simpledialog.askstring(
        self._t("btn_watermark"),
        "透かしテキストを入力してください:\n(例: CONFIDENTIAL, 社外秘)",
        parent=self.root,
    )
    if not text:
        return
    # コンテンツ改変系のため page_edit op（適用前ページ bytes）で undo 対応。
    self._save_undo("page_edit", targets=targets)
    for i in targets:
        page = self.doc[i]
        rect = page.rect
        ...
        page.insert_text(...)
    self._invalidate_thumb_cache(targets)
    self._refresh_all()
    self._set_status(f"透かしを追加しました ({len(targets)} ページ)")
```

**画像版で置き換える箇所:**
- `simpledialog.askstring` → `filedialog.askopenfilename(filetypes=[(..., "*.png *.jpg *.jpeg")])`（D-04）
- `page.insert_text(...)` → Pillow でアルファ合成済み PNG bytes を作り `page.insert_image(rect, stream=img_bytes)`
- `_save_undo("page_edit", targets=targets)` の呼び出し位置・`_invalidate_thumb_cache`/`_refresh_all`/`_set_status` の並びは完全に同一（変更不要）
- `_check_doc()` → `_get_targets()` → 早期 return（キャンセル時）の順序も同一踏襲

**エラーハンドリング:** `_add_page_numbers`/既存メソッド群は Pillow 例外を扱っていないため、新規で `try/except Exception as e: messagebox.showerror(self._t("err_title"), str(e))` を追加する箇所は `pagefolio/file_ops.py` 系の一般パターン（下記 Shared Patterns 参照）に倣う。

---

### `pagefolio/page_ops.py` — `_derotate_rect`（utility, transform）

**Analog:** `pagefolio/pagination.py`（純ロジック層の設計思想）+ `pagefolio/page_ops.py:253-267 _canvas_rect_to_pdf`（挿入位置）

**既存の`_canvas_rect_to_pdf`**（そのまま維持、直後に一段挟む形）:
```python
def _canvas_rect_to_pdf(self, sx, sy, ex, ey):
    """プレビューキャンバス座標の矩形を PDF 点座標（page 左上原点）へ変換する。
    ...
    トリミング・黒塗り・モザイクの矩形選択が共用する。
    """
    scale = self.zoom * 1.5
    img_offset = 10
    return (
        (sx - img_offset) / scale,
        (sy - img_offset) / scale,
        (ex - img_offset) / scale,
        (ey - img_offset) / scale,
    )
```

**pagination.py の純関数設計原則**（適用すべき型）:
```python
# fitz/tkinter を import しない・引数→戻り値のみで完結・状態を持たない
def window_bounds(window_start, page_size, n_pages):
    if n_pages <= 0:
        return (0, 0)
    lo = max(0, min(window_start, max(0, n_pages - 1)))
    hi = min(lo + page_size, n_pages)
    return (lo, hi)
```

`_derotate_rect(page, x0, y0, x1, y1)` は `page.derotation_matrix` に依存するため完全な fitz 非依存にはできないが、「入力→出力のみ、self に依存しない `@staticmethod`」という pagination.py の設計原則を踏襲する。呼び出し箇所は `_apply_page_edit`（redact_ops.py:92）と `_crop_page` の両方の `_canvas_rect_to_pdf(...)` 直後（mediabox 相対化の前）。

---

### `pagefolio/redact_ops.py` — `_apply_page_edit`（controller, CRUD/破壊的編集）

**Analog:** 同ファイル内 `_apply_page_edit`（72-133行）自身を改修

**現状の核パターン**（複数矩形化・D-05連続適用・D-06粒度引数化の改修起点）:
```python
def _apply_page_edit(self, kind):
    if not self._check_doc():
        return
    if not self.crop_rect:
        messagebox.showinfo(self._t("info_title"), self._t("info_redact_drag"))
        return
    targets = self._get_targets()
    ...
    x0_pdf, y0_pdf, x1_pdf, y1_pdf = self._canvas_rect_to_pdf(*self.crop_rect)
    cur_mb = self.doc[self.current_page].mediabox
    rel = (...)

    self._save_undo("page_edit", targets=targets)   # ← D-07: 複数矩形でも1回だけ呼ぶ位置
    applied = []
    for i in targets:
        page = self.doc[i]
        rect = self._page_rect_from_rel(page, rel)
        if rect is None:
            continue
        try:
            if kind == "redact":
                self._redact_page(page, rect)
            else:
                self._mosaic_page(page, rect)          # ← D-06: block=self.settings[...] を渡す
            applied.append(i)
        except Exception as e:
            logger.error("ページ編集失敗 (kind=%s, page=%s): %s", kind, i, e)
    ...
    self.crop_rect = None
    self._redact_mode_off()   # ← D-05: この呼び出しのみ削除して連続適用化（相互排他ロジックは不変）
    ...
```

**Pitfall（研究で明記済み・厳守）:**
- D-07: `_save_undo` はターゲットページ集合に対し**必ずループの外側で1回だけ**呼ぶ（`RESEARCH.md` Pitfall 4）。
- D-05: `_redact_mode_off()` の呼び出しだけを削除する。`_toggle_redact_mode`/`_toggle_crop_mode`（37-52行, `page_ops.py:237-251`）の相互排他コードには触れない。

**`_mosaic_page` 粒度引数化**（166-187行）:
```python
@staticmethod
def _mosaic_page(page, rect):
    pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(2, 2))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    small = img.resize(
        (max(1, img.width // MOSAIC_BLOCK), max(1, img.height // MOSAIC_BLOCK)),
        Image.NEAREST,
    )
    ...
```
→ `block=MOSAIC_BLOCK` 引数を追加し呼び出し元 `_apply_mosaic` で `self.settings.get("mosaic_block", MOSAIC_BLOCK)` を渡す。

**`_page_rect_from_rel`**（135-157行）は複数矩形化でもそのまま再利用（矩形ごとに呼ぶループ構造に変わるだけ）。

---

### `pagefolio/ui_builder.py` — モザイクスライダー / クリアボタン（component, request-response）

**Analog:** `pagefolio/ui_builder.py:200-211 thumb_zoom_scale`

```python
zoom_frame = tk.Frame(parent, bg=C["BG_PANEL"])
zoom_frame.pack(fill="x", padx=6, pady=(0, 4))
self.thumb_zoom_var = tk.DoubleVar(value=self.settings.get("thumb_zoom", 1.0))
self.thumb_zoom_scale = ttk.Scale(
    zoom_frame,
    from_=0.5,
    to=2.5,
    variable=self.thumb_zoom_var,
    orient="horizontal",
)
self.thumb_zoom_scale.pack(fill="x", expand=True, padx=2)
self.thumb_zoom_scale.bind("<ButtonRelease-1>", self._on_thumb_zoom_release)
```

**追加先セクション:** `ui_builder.py:583-612`（`f3b = section(self._t("sec_redact"))` 〜 モザイク適用ボタン）。同じ `f3b` フレーム内にスライダー（D-06）とクリアボタン（D-07）を挿入する。ボタン群は既存 `btn(f3b, self._t("btn_apply_mosaic"), self._apply_mosaic, needs_doc=True, edit_only=True)` と同じ `btn()` ヘルパー呼び出しパターンに揃える。

**設定永続化パターン:** `_on_thumb_zoom_release` に相当する `_on_mosaic_block_release` を追加し、`self.settings["mosaic_block"] = int(self.mosaic_block_var.get()); self._save_settings()` の型（`settings.py` の既存保存フロー）に従う。

---

### `pagefolio/dnd.py` — `compute_dnd_dest_index` 抽出（utility, transform）

**Analog:** `pagefolio/dnd.py:74-93 _dnd_dest_index`（抽出元そのもの）+ `pagefolio/pagination.py`（抽出後の純関数配置パターン）

```python
def _dnd_dest_index(self, event):
    """マウス位置から挿入先を計算"""
    frames = self.thumb_inner.winfo_children()
    if not frames:
        return None
    canvas_y = event.y_root - self.thumb_canvas.winfo_rooty()
    cy = self.thumb_canvas.canvasy(canvas_y)
    first_y = frames[0].winfo_y()
    last_frame = frames[-1]
    last_bottom = last_frame.winfo_y() + last_frame.winfo_height()
    if cy < first_y:
        return 0
    if cy > last_bottom:
        return len(frames)
    for i, fr in enumerate(frames):
        fy = fr.winfo_y()
        fh = fr.winfo_height()
        if cy < fy + fh / 2:
            return i
    return len(frames)
```

→ Tk 依存部分（`winfo_*`/`canvasy`/`event`）を薄いラッパーに残し、「cy と (fy, fh) 列 → index」の核心比較ロジックを module-level 純関数 `compute_dnd_dest_index(cursor_y, frame_bounds)` へ抽出する（RESEARCH.md Pattern 5 のコード例をそのまま採用可）。`_dnd_dest_index` はラッパーとして `frame_bounds = [(fr.winfo_y(), fr.winfo_height()) for fr in frames]` を組み立てて委譲する。

---

### `pagefolio/app.py` — `merge_shortcuts` / `shift_variant_keysym` 抽出（utility, transform）

**Analog:** `pagefolio/app.py:127-166`（抽出元）

```python
default_shortcuts = {
    "open_file": "<Control-o>",
    "save_file": "<Control-s>",
    "undo": "<Control-z>",
    "redo": "<Control-y>",
    "save_as": "<Control-S>",
    "delete": "<Delete>",
    "toggle_mode": "<F5>",
    "print_pdf": "<Control-p>",
}
custom_shortcuts = self.settings.get("shortcuts", {})
shortcuts = {**default_shortcuts, **custom_shortcuts}
...
if (
    keysym.startswith("<Control-")
    and len(keysym) == 11
    and keysym[-2].islower()
):
    ...
```

→ `merge_shortcuts(default_shortcuts, custom_shortcuts)`（後勝ちマージ）と `shift_variant_keysym(keysym)`（Shift大文字補完判定、対象外は None）を module-level 純関数として `app.py` 内に抽出。`__init__` はこれらを呼んで `root.bind()` するだけの薄いループに変える（RESEARCH.md Pattern 6 のコード例採用）。

---

### `tests/test_v150_regression.py`（新規・test, batch）

**Analog A（純関数テスト）:** `tests/test_pagination.py`（合成データで直接呼び出し、Tk/fitz 生成なし）— D&D挿入位置・ショートカットマージ用

**Analog B（FakeApp mixin）:** `tests/test_pdf_ops.py:1469-1519 TestContentOpsUndoFix._make_app`

```python
def _make_app(self, doc):
    import collections
    import types

    import pagefolio.file_ops as fo
    import pagefolio.page_ops as po
    import pagefolio.redact_ops as ro

    class FakeApp(fo.FileOpsMixin, po.PageOpsMixin, ro.RedactOpsMixin):
        MAX_UNDO = 20

        def __init__(self, d):
            self.doc = d
            self.current_page = 0
            self.selected_pages = set()
            self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
            self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
            self._preview_gen = 0
            self._thumb_gen = 0
            self.root = None

        def _check_doc(self):
            return self.doc is not None

        def _get_targets(self):
            return sorted(self.selected_pages) or [self.current_page]

        def _invalidate_thumb_cache(self, *a, **kw):
            pass

        def _refresh_all(self):
            pass

        def _t(self, key):
            return key

        def _set_status(self, *a):
            pass

    app = FakeApp(doc)
    app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
    return app
```

TOC 保持テスト（削除/結合/分割）はこの FakeApp を使い、`app.doc.get_toc()` を直接検証する（`pagefolio/page_ops.py:125-127, 643-650, 727-734, 771-778` の TOC 処理コードパスを exercised）。

**フィクスチャ活用:** `tests/conftest.py` の `sample_pdf_doc` / `large_pdf_doc` / `multi_pdf_files` をそのまま流用。

---

### `tests/test_pdf_ops.py`（既存拡張・test, batch）

**Analog:** 同ファイル `TestContentOpsUndoFix`（1520行以降の `test_insert_blank_roundtrip` 等）

```python
def test_insert_blank_roundtrip(self, sample_pdf_doc):
    """白紙挿入 → undo でページ数が戻る → redo で再挿入"""
    app = self._make_app(sample_pdf_doc)
    app.current_page = 0
    app._insert_blank_page()
    assert len(app.doc) == 4
    assert app.doc[1].get_text().strip() == ""  # 白紙

    app._undo()
    assert len(app.doc) == 3
```

D-14（内容検証追加）は既存 `test_*_roundtrip` 系メソッドに `get_text()`/ページサイズ一致等の assert を追記するだけで、テスト構造自体は変更しない。画像透かし・derotate・複数矩形・mm トリミング・crop_info フォーマットの新規テストクラスは同ファイル内に追加する場合、`_make_app` ヘルパーをそのまま再利用する（redact_ops もすでに mixin 済み）。

---

## Shared Patterns

### page_edit undo フロー（コンテンツ改変系操作の共通骨格）
**Source:** `pagefolio/page_ops.py:180-215`, `pagefolio/redact_ops.py:64-133`
**Apply to:** 画像透かし追加・黒塗り/モザイク複数矩形適用のすべて
```python
targets = self._get_targets()
# ...ユーザー入力/確認...
self._save_undo("page_edit", targets=targets)   # 1回だけ、ループの外側
for i in targets:
    page = self.doc[i]
    # ページへの破壊的変更
self._invalidate_thumb_cache(targets or applied)
self._refresh_all()
self._set_status(...)
```

### 例外ハンドリング
**Source:** プロジェクト全体の共通作法（`page_ops.py` 各 `except Exception as e: messagebox.showerror(self._t("err_title"), str(e))`）
**Apply to:** 画像ファイル読み込み（Pillow `Image.open`）、mm数値入力パース
```python
try:
    with Image.open(path) as im:
        img = im.convert("RGBA")
except Exception as e:
    messagebox.showerror(self._t("err_title"), str(e))
    return
```

### 純ロジック抽出パターン（Tk/fitz 非依存）
**Source:** `pagefolio/pagination.py`（既定パターン・V16-D-01/D-02）
**Apply to:** `_derotate_rect`（fitz.Page 1個のみ依存の static）・`compute_dnd_dest_index`（完全非依存）・`merge_shortcuts`/`shift_variant_keysym`（完全非依存）
- module-level 関数または `@staticmethod`
- 引数→戻り値のみ、`self`/グローバル状態に依存しない（`_derotate_rect` は例外的に `page` オブジェクトを受け取るが、`page.derotation_matrix` 参照のみで完結させる）
- 呼び出し側（Tk/fitz依存の薄いラッパー）は元のメソッド名のまま残し、内部で純関数へ委譲する

### スライダー設定永続化パターン
**Source:** `pagefolio/ui_builder.py:200-211`（`thumb_zoom_var`/`thumb_zoom_scale`/`_on_thumb_zoom_release`）
**Apply to:** モザイク粒度スライダー（D-06）
```python
self.mosaic_block_var = tk.IntVar(value=self.settings.get("mosaic_block", MOSAIC_BLOCK))
self.mosaic_block_scale = ttk.Scale(f3b, from_=4, to=32, variable=self.mosaic_block_var, orient="horizontal")
self.mosaic_block_scale.pack(fill="x", expand=True, padx=8, pady=(2, 4))
self.mosaic_block_scale.bind("<ButtonRelease-1>", self._on_mosaic_block_release)
```

### LANG 辞書拡張ルール
**Source:** `pagefolio/lang.py`（ja/en 両辞書）+ `tests/test_lang_parity.py`
**Apply to:** 新規ボタン文言（画像透かしボタン・クリアボタン・数値トリミング入力ラベル等）はすべて ja/en 同一キーで追加すること（キー数不一致は `test_lang_parity.py` で検出される）。

## No Analog Found

なし。すべての新規/改修ファイルに対して、同一ファイル内または同一プロジェクト内の直接的な analog が存在する（既存のテキスト透かし・黒塗り/モザイク・pagination.py 純ロジック層・thumb_zoom_scale スライダー・TestContentOpsUndoFix FakeApp のいずれかが厳密に対応）。

## Metadata

**Analog search scope:** `pagefolio/page_ops.py`, `pagefolio/redact_ops.py`, `pagefolio/ui_builder.py`, `pagefolio/dnd.py`, `pagefolio/app.py`, `pagefolio/pagination.py`, `tests/test_pdf_ops.py`, `tests/conftest.py`, `tests/test_pagination.py`
**Files scanned:** 9
**Pattern extraction date:** 2026-07-05
