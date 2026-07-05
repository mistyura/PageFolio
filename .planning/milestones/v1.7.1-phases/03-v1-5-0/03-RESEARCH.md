# Phase 3: ページ操作磨き込み + v1.5.0 回帰テスト - Research

**Researched:** 2026-07-05
**Domain:** PyMuPDF (fitz) ページ内容編集（画像埋め込み・回転座標変換・破壊的編集）＋ pytest 純ロジックテスト設計
**Confidence:** HIGH（既存コードパターンの直接延長）/ MEDIUM（PyMuPDF 回転座標変換・alpha 埋め込みの詳細挙動）

## Summary

本フェーズは新規ライブラリを一切追加しない（`PyMuPDF`/`Pillow`/`tkinter`/`tkinterdnd2` は既存依存のまま）。作業の実体は (1) 既存の「テキスト透かし」「トリミング」「黒塗り/モザイク」実装パターンへの機能追加、(2) 3 操作（黒塗り・モザイク・トリミング）に共通する矩形選択が回転表示中のページで座標ズレを起こすバグの構造的解消、(3) v1.5.0 で未テストだった 3 機能（TOC 保持・D&D 指定位置挿入・ショートカット動的読込）への純ロジック抽出＋テスト追加、である。

画像透かし（V171-PAGE-01）はテキスト透かし（`_add_watermark_text`）と全く同じ「ボタン→選択→即適用→`page_edit` undo」の型を踏襲すればよく、新規に必要なのは Pillow によるアルファ合成前処理のみ。回転座標対応（D-08）は PyMuPDF が公式に提供する `page.derotation_matrix` を使えば数学的に自前実装するより確実で、`_canvas_rect_to_pdf` の直後に 1 箇所だけ変換を挟む共通ヘルパーとして実装できる。回帰テスト整備（V171-TEST-01）は `pagination.py` で確立済みの「純ロジック抽出＋直接テスト」パターンと、`TestContentOpsUndoFix` で確立済みの「FakeApp mixin」パターンの使い分けで対応可能。

**Primary recommendation:** 画像透かしはテキスト透かしのコードパスをそのまま複製・改変し、黒塗り/モザイク/トリミングの座標対応は `_canvas_rect_to_pdf` と `_page_rect_from_rel`（および `_crop_page` 内の rel 変換）の間に `page.derotation_matrix` を使う共通ヘルパーを 1 箇所挟む形で実装する。回帰テストは機能ごとに「D&D/ショートカット＝純関数抽出」「TOC＝FakeApp」を使い分け、新規ファイルへ分離する。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 画像透かし埋め込み（V171-PAGE-01） | ページ操作ロジック（`page_ops.py` / Mixin） | — | 単一プロセス Tkinter デスクトップアプリのため tier 分離なし。fitz Document 操作は UI イベントハンドラ内（メインスレッド）で完結 |
| 黒塗り/モザイク改善（V171-PAGE-02） | ページ編集ロジック（`redact_ops.py`） | UI（`ui_builder.py` スライダー/ボタン） | 適用ロジックは Mixin、粒度設定 UI は UIBuilderMixin |
| 回転座標変換ヘルパー（D-08） | 純ロジック層（`page_ops.py` static / 新モジュール候補） | ページ操作 Mixin（呼び出し元） | Tk 非依存にできる計算のため、既存 `pagination.py` 同様の純ロジック層候補 |
| トリミング操作性改善（V171-PAGE-03） | ページ操作ロジック（`page_ops.py`） | UI（矢印キーバインド・crop_info 表示） | 既存 `_crop_page`/`_crop_drag_move` の直接拡張 |
| v1.5.0 回帰テスト（V171-TEST-01） | テストスイート（`tests/`） | 純ロジック抽出対象（`app.py` ショートカットマージ・`dnd.py` 挿入位置計算） | Tk 非依存化できる部分は抽出、doc 操作系は FakeApp |

## Standard Stack

### Core

本フェーズで新規に追加するライブラリはない。既存依存のみを使用する。

| Library | Version（実機確認） | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | 1.27.2.3 [VERIFIED: `python -c "import fitz; print(fitz.__version__)"`] | 画像埋め込み・矩形/回転座標変換・破壊的編集 | 既存全ページ操作の基盤。`requirements.txt` は `1.27.2.2` 固定だが実行環境には後継パッチ版が入っている（差異は無害・パッチレベル） |
| Pillow (PIL) | 12.2.0 [VERIFIED: `python -c "import PIL; print(PIL.__version__)"`] | 画像アルファ合成前処理・モザイク生成 | 既存 `redact_ops.py` の `_mosaic_page` が既に使用 |
| tkinter / ttk | 標準ライブラリ | UI（スライダー・矢印キーバインド・簡易入力ダイアログ） | プロジェクト全体の UI 基盤 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tkinter.simpledialog` | 標準ライブラリ | 数値指定トリミングの mm 入力（D-10・Claude's Discretion で連続 askfloat か専用ダイアログか選択） | 既に `_add_watermark_text`（テキスト入力）・`_split_by_range`（範囲入力）で使用中の型 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pillow でのアルファ合成前処理（D-03 決定済み） | `fitz.Annot.set_opacity()`（注釈ベースの透過） | 注釈は「画像埋め込み」ではなく PDF 注釈オブジェクトになり、`apply_redactions` 等の既存破壊的操作や `page.insert_image` ベースの他コードパスと性質が変わる。CONTEXT.md D-03 で「Pillow でアルファチャンネルを乗算」と明記済みのため採用しない |
| `page.derotation_matrix`（推奨） | 回転角度から手動で三角関数を用いた座標変換を自前実装 | 自前実装は 90/180/270 度の分岐処理とオフセット計算をミスしやすい（符号・ページ幅高さ入れ替えの取り違えが典型的なバグ源）。PyMuPDF 公式提供の行列を使う方が正しさが保証される [CITED: pymupdf.readthedocs.io/en/latest/page.html] |

**Installation:** 不要（新規パッケージなし）。

**Version verification:** 上記の通り `python -c "import fitz; print(fitz.__version__)"` / `python -c "import PIL; print(PIL.__version__)"` で実行環境の実バージョンを確認済み。

## Package Legitimacy Audit

**本フェーズは新規パッケージを一切導入しない。** `requirements.txt`（PyMuPDF/Pillow/tkinterdnd2/pyinstaller、開発依存 pytest/pytest-cov/ruff）は変更不要。したがって Package Legitimacy Gate（`gsd-tools query package-legitimacy check`）は対象パッケージなしのためスキップする。

**Packages removed due to [SLOP] verdict:** none（該当なし）
**Packages flagged as suspicious [SUS]:** none（該当なし）

## Architecture Patterns

### System Architecture Diagram

```text
[ユーザー操作: 右ペインボタン/矢印キー/プレビューキャンバスドラッグ]
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│ UIBuilderMixin (ui_builder.py)                              │
│  - モザイク粒度スライダー (D-06, 新規)                        │
│  - 黒塗り「クリア」ボタン (D-07, 新規)                         │
│  - 数値指定トリミング入力導線 (D-10, 新規)                     │
└───────────────┬───────────────────────────────────────────┘
                │ command=
                ▼
┌───────────────────────────────────────────────────────────┐
│ PageOpsMixin (page_ops.py)          RedactOpsMixin           │
│  _add_watermark_image() [新規]       (redact_ops.py)          │
│  _canvas_rect_to_pdf()  ──┐          _apply_page_edit()       │
│  _derotate_rect() [新規]──┼─────────▶ _mosaic_page(block=..)  │
│  _crop_page() [D-09/D-10/D-11 拡張]  _redact_rects[] [D-07]   │
└───────────────┬──────────────────────────┬──────────────────┘
                │ fitz.Page 操作             │ fitz.Page 操作
                ▼                            ▼
        ┌───────────────────────────────────────┐
        │ FileOpsMixin._save_undo("page_edit")   │
        │  → _capture_page_blob (適用前 bytes)   │
        │  → UndoBlobStore (64KiB 閾値でディスク退避)│
        └───────────────┬───────────────────────┘
                        │
                        ▼
                fitz.Document (self.doc) 破壊的変更
                        │
                        ▼
        _invalidate_thumb_cache → _refresh_all → プレビュー/サムネイル再描画


[別経路: v1.5.0 回帰テスト対象の純ロジック抽出]

app.py.__init__ (ショートカットマージ)  ──▶ 抽出先候補: merge_shortcuts() 純関数
dnd.py._dnd_dest_index (D&D 挿入位置)  ──▶ 抽出先候補: compute_dnd_dest_index() 純関数
page_ops.py（削除/結合/分割の TOC 処理） ──▶ 抽出せず FakeApp 経由で直接検証
        │
        ▼
tests/test_v150_regression.py [新規ファイル・D-15]
```

### Recommended Project Structure

新規ファイルの追加はテストのみ。実装は既存モジュールへの追記で完結する。

```
pagefolio/
├── page_ops.py       # + _add_watermark_image / _derotate_rect / crop 系拡張(D-09/D-10/D-11)
├── redact_ops.py      # + mosaic block 引数化(D-06) / 複数矩形一括適用(D-07)
├── ui_builder.py      # + モザイクスライダー / クリアボタン / 数値トリミング導線
├── app.py             # (Claude's Discretion: ショートカットマージを純関数へ抽出する場合はここ or 新規モジュール)
├── dnd.py             # (Claude's Discretion: D&D 挿入位置計算を純関数へ抽出する場合はここに残すか分離)
└── constants.py        # + MOSAIC_BLOCK は既定値として残す（D-06）

tests/
├── test_pdf_ops.py           # 既存 TestContentOpsUndoFix へ内容検証追加(D-14)。画像透かし/複数矩形/derotate/数値トリミングの新規テストクラスを追加してもよいが肥大化防止(D-15)のため新規機能テストは基本的に次のファイルへ
└── test_v150_regression.py   # 新規（D-15・命名は例）: TOC保持/D&D挿入/ショートカット読込の回帰テスト
```

### Pattern 1: 画像透かし（テキスト透かしと同型）

**What:** `_add_watermark_text` と同じ制御フロー（`_get_targets` → 確認 → `_save_undo("page_edit", ...)` → 各ページへ適用 → `_invalidate_thumb_cache` → `_refresh_all`）を、`filedialog.askopenfilename` による画像選択に置き換える。

**When to use:** V171-PAGE-01 全体。

**Example:**
```python
# Source: 既存 pagefolio/page_ops.py:180 _add_watermark_text の型を踏襲（ASSUMED: 未実装コード例）
from PIL import Image
import io

def _add_watermark_image(self):
    """選択ページに画像透かしを追加する（D-01〜D-04）。"""
    if not self._check_doc():
        return
    targets = self._get_targets()
    path = filedialog.askopenfilename(
        title=self._t("btn_watermark_image"),
        filetypes=[(self._t("filetypes_image"), "*.png *.jpg *.jpeg")],
    )
    if not path:
        return
    try:
        with Image.open(path) as im:
            img = im.convert("RGBA")
    except Exception as e:
        messagebox.showerror(self._t("err_title"), str(e))
        return

    # 既存アルファは乗算、なければ 128(=50%) を一様に設定（D-03）
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * 0.5))
    img.putalpha(a)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    iw, ih = img.size

    self._save_undo("page_edit", targets=targets)
    for i in targets:
        page = self.doc[i]
        rect = self._watermark_image_rect(page.rect, iw, ih)
        page.insert_image(rect, stream=img_bytes)  # rotate 引数なし = 水平のまま(D-03)
    self._invalidate_thumb_cache(targets)
    self._refresh_all()
    self._set_status(...)

@staticmethod
def _watermark_image_rect(page_rect, img_w, img_h):
    """ページ中央・ページ幅の約50%に収まるよう縮小した配置矩形を返す（D-02）。"""
    target_w = page_rect.width * 0.5
    scale = target_w / img_w
    target_h = img_h * scale
    # 極端な縦長画像でページ高さを超える場合はクランプ（Claude's Discretion）
    if target_h > page_rect.height * 0.9:
        scale = (page_rect.height * 0.9) / img_h
        target_w = img_w * scale
        target_h = img_h * scale
    x0 = (page_rect.width - target_w) / 2
    y0 = (page_rect.height - target_h) / 2
    return fitz.Rect(x0, y0, x0 + target_w, y0 + target_h)
```

**Pitfall check:** `page.insert_image()` にはページ内容として画像を焼き込む標準経路であり、透過は「画像自体の RGBA/SMask」に依存する（挿入メソッド自体には不透明度引数がない）[CITED: pymupdf.readthedocs.io/en/latest/recipes-images.html]。CONTEXT.md D-03 の記述と整合する。

### Pattern 2: 回転座標の共通逆変換ヘルパー（D-08）

**What:** プレビューは `page.get_pixmap()` で**回転後の見た目**をレンダリングするため（PyMuPDF は `/Rotate` を反映した状態でピクセルを生成する）、`_canvas_rect_to_pdf` が返す座標は「回転後の表示座標系」である。一方 `mediabox`/`cropbox`/`add_redact_annot` は常に**未回転のページ座標系**を要求する [CITED: pymupdf.readthedocs.io/en/latest/page.html — "coordinates must always be provided relative to the unrotated page"]。この不一致が既知の制限（CLAUDE.md「矩形は未回転のページ座標系で適用される」）の原因であり、D-08 はこれを構造的に解消する。

PyMuPDF は `page.rotation_matrix`（未回転→回転後）と `page.derotation_matrix`（回転後→未回転、その逆行列）を公式に提供している [CITED: pymupdf.readthedocs.io/en/latest/page.html]。

**When to use:** `_crop_page`（単一・複数ページ分岐の両方）・`_apply_page_edit`（黒塗り/モザイク）・D-07 複数矩形一括適用の全呼び出し箇所。

**Example:**
```python
# Source: PyMuPDF 公式ドキュメント記載の rotation_matrix/derotation_matrix の使用法を
# 本プロジェクトの既存 _canvas_rect_to_pdf の後段へ適用する形（CITED: pymupdf docs）
@staticmethod
def _derotate_rect(page, x0, y0, x1, y1):
    """表示（回転後）座標系の矩形を、mediabox/cropbox が使う未回転座標系へ変換する。

    page.rotation が 0 のとき恒等変換。90/180/270 のとき page.derotation_matrix
    を用いて正しく逆変換する（D-08）。
    """
    dm = page.derotation_matrix
    p0 = fitz.Point(x0, y0) * dm
    p1 = fitz.Point(x1, y1) * dm
    return (
        min(p0.x, p1.x), min(p0.y, p1.y),
        max(p0.x, p1.x), max(p0.y, p1.y),
    )
```

呼び出し側は `_canvas_rect_to_pdf(*self.crop_rect)` の戻り値を **そのまま `mb.width` 等で相対化する前に** `self._derotate_rect(page, *canvas_pdf_rect)` へ通す 1 行を各呼び出し箇所（3〜4 箇所）に追加するだけでよい。

**テスト方針（純関数化してテストで担保・CONTEXT.md 指示）:** 小さな `fitz.open()` ドキュメントで `page.set_rotation(90)` 等を設定し、既知の矩形を `_derotate_rect` に通して期待座標と一致するかを検証する。`page` オブジェクトが引数のため `pagination.py` のような完全 fitz 非依存ではないが、`tests/test_pdf_ops.py` の既存 `RedactOpsMixin` テスト群と同じ「小さな fitz.Document を都度生成して検証」パターンに従えばよい。

### Pattern 3: モザイク粒度スライダー（既存 `thumb_zoom_scale` パターンの複製）

**What:** `ui_builder.py:200-211` の `thumb_zoom_scale`（`ttk.Scale` + `tk.DoubleVar` + `<ButtonRelease-1>` で設定保存）と同型のスライダーをページ編集セクション（`f3b`, `ui_builder.py:583` 付近）に追加する。

**Example:**
```python
# Source: 既存 pagefolio/ui_builder.py:203-211 の型を踏襲
self.mosaic_block_var = tk.IntVar(value=self.settings.get("mosaic_block", MOSAIC_BLOCK))
self.mosaic_block_scale = ttk.Scale(
    f3b, from_=4, to=32, variable=self.mosaic_block_var, orient="horizontal"
)
self.mosaic_block_scale.pack(fill="x", expand=True, padx=8, pady=(2, 4))
self.mosaic_block_scale.bind("<ButtonRelease-1>", self._on_mosaic_block_release)
```
```python
# redact_ops.py 側: _mosaic_page を粒度引数化
@staticmethod
def _mosaic_page(page, rect, block=MOSAIC_BLOCK):
    ...
    small = img.resize((max(1, img.width // block), max(1, img.height // block)), Image.NEAREST)
    ...

def _apply_mosaic(self):
    block = int(self.settings.get("mosaic_block", MOSAIC_BLOCK))
    self._apply_page_edit("mosaic", block=block)
```
`MOSAIC_BLOCK` 定数は既定値としてそのまま `constants.py` に残す（CONTEXT.md 明記）。値域・ステップは Claude's Discretion（`from_=4, to=32` は一例）。

### Pattern 4: 複数矩形の一括黒塗り/モザイク（D-07）

**What:** 現行は `self.crop_rect` が単一矩形（ドラッグのたびに上書き）。D-07 は黒塗り/モザイクモード時のみ、ドラッグ完了ごとに矩形をリスト（例: `self._redact_rects: list[tuple]`）へ追加し、既存の 1 矩形だけを消す `_clear_crop_overlay` とは別に全矩形分のオーバーレイ ID を管理する。「クリア」ボタンで全削除。適用は `_save_undo("page_edit", targets=targets)` を **1 回だけ** 呼んでから、各対象ページに対して全矩形を順に適用するループ構造にする（1 回の undo で戻ることを保証・CONTEXT.md 制約）。

**Integration point:** `_crop_drag_start`/`_crop_drag_move`/`_crop_drag_end`（`page_ops.py`）はトリミングと共用のため、`self.redact_mode` のときだけ挙動分岐（今回追加 or 上書き）を入れる。既存の `crop_mode` 単一矩形ロジックには影響を与えない。矩形リストの状態管理・オーバーレイ描画方式の詳細（stipple 併用か単純アウトラインのみか）は CONTEXT.md で Claude's Discretion。

### Pattern 5: D&D 挿入位置計算の純ロジック抽出（D-13）

**What:** `dnd.py:_dnd_dest_index` は `winfo_y()`/`canvasx()` 等の実 Tk ウィジェット依存だが、「カーソル Y 座標 → 挿入先インデックス」の核心計算（フレーム境界との比較）はロジックとして分離できる。`pagination.py` の「Tk/fitz 非依存の純関数を切り出し、描画層は薄いラッパーにする」既定パターン（V16-D-01/D-02）に倣う。

**Example:**
```python
# Source: 既存 pagefolio/dnd.py:74-93 _dnd_dest_index のロジックを抽出
def compute_dnd_dest_index(cursor_y, frame_bounds):
    """cursor_y と各フレームの (y, height) タプル列から挿入先インデックスを返す。

    frame_bounds: [(y0, height), ...]（窓ローカル順）。Tk/fitz 非依存の純関数。
    """
    if not frame_bounds:
        return None
    first_y = frame_bounds[0][0]
    last_y, last_h = frame_bounds[-1]
    if cursor_y < first_y:
        return 0
    if cursor_y > last_y + last_h:
        return len(frame_bounds)
    for i, (fy, fh) in enumerate(frame_bounds):
        if cursor_y < fy + fh / 2:
            return i
    return len(frame_bounds)
```
`_dnd_dest_index` はこの純関数へ `frames` から `(fr.winfo_y(), fr.winfo_height())` を集めて委譲する薄いラッパーへ改修する。テストは実ウィジェットなしで `compute_dnd_dest_index(50, [(0, 40), (40, 40), (80, 40)])` のような合成データで検証できる。抽出先モジュール（`dnd.py` 内 or 新規）は Claude's Discretion。

### Pattern 6: ショートカットのマージ/検証ロジック抽出（D-13）

**What:** `app.py:128-174` の `default_shortcuts` / `custom_shortcuts` マージと、`<Control-x>` → 大文字 `<Control-X>` 追加バインドの判定ロジック（`keysym.startswith("<Control-") and len(keysym) == 11 and keysym[-2].islower()`）は純粋な文字列処理であり、`root.bind()` 呼び出し自体（Tk 依存）と切り離して抽出・直接テストできる。

**Example:**
```python
# Source: 既存 pagefolio/app.py:139-140, 161-169 のロジックを抽出
def merge_shortcuts(default_shortcuts, custom_shortcuts):
    """既定＋ユーザー設定のショートカット辞書をマージする（後勝ち）。"""
    return {**default_shortcuts, **custom_shortcuts}

def shift_variant_keysym(keysym):
    """Control-小文字 の keysym から Shift 補完用の大文字版 keysym を返す。
    対象外パターンは None を返す。"""
    if (
        keysym.startswith("<Control-")
        and len(keysym) == 11
        and keysym[-2].islower()
    ):
        return keysym[:-2] + keysym[-2].upper() + ">"
    return None
```
呼び出し元 `app.py.__init__` はこの 2 関数を呼んで `root.bind()` するだけの薄いループに変える。抽出先（`app.py` 内 module-level 関数 or 新規モジュール）は Claude's Discretion。

### Anti-Patterns to Avoid

- **黒塗り/モザイク/トリミングで座標変換ロジックを個別に重複実装する:** D-08 は「共通ヘルパー」を明示的に要求している（CONTEXT.md）。3 箇所（`_crop_page` 単一/複数、`_apply_page_edit`）にそれぞれ回転補正コードを書くと、次回のバグ修正が 1 箇所で漏れる。
- **画像透かしで `page.insert_image` に不透明度引数を探す:** 存在しない。Pillow 側でアルファを事前合成する（D-03 で確定済み）。
- **モザイク粒度をグローバル定数のまま変更する:** `MOSAIC_BLOCK` を直接書き換えると全ユーザーの既定値が変わってしまう。設定キー経由で既定値として温存する（D-06）。
- **D&D/ショートカットのテストで実際の Tk ルートウィンドウを生成し `winfo_*` に依存する:** CI/ヘッドレス環境で不安定になりやすい。純関数抽出（Pattern 5/6）でこれを回避する。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 回転ページの座標変換 | 独自の三角関数ベースの回転行列実装 | `page.rotation_matrix` / `page.derotation_matrix` [CITED: pymupdf docs] | PyMuPDF 内部の回転処理と完全に整合することが保証される。自前実装は 90/180/270 度分岐やページ幅高さの入れ替えを間違えやすい典型的なバグ源 |
| 画像の半透明合成 | 独自のピクセルごとの alpha ブレンド計算 | Pillow `Image.putalpha()` / `ImageChops` 等の標準 API | Pillow は RGBA 合成のエッジケース（既存アルファの尊重、モード変換）を既にハンドリング済み |
| mm↔pt 単位変換 | 独自の近似値（例: 1mm=2.83pt 決め打ちだが定数を分散させる） | `72 / 25.4` を単一定数として `constants.py` 等に集約 | PDF の 1pt = 1/72 inch は不変の定義。分散すると桁ズレ・丸め誤差の温床になる |

**Key insight:** 本フェーズはいずれも「複雑な計算を自作しない」方向性で、PyMuPDF/Pillow が既に提供する機能（derotation_matrix・alpha 合成）を薄く呼び出すだけで実装できる。自作が必要になった箇所（純ロジック抽出）は逆に「Tk からの分離」というプロジェクト内で確立済みのパターン（`pagination.py`）に従うべきで、新しい抽象を発明する必要はない。

## Runtime State Inventory

> 本フェーズは rename/refactor/migration ではなく機能追加＋座標変換バグ修正のため、このセクションは対象外（スキップ）。

## Common Pitfalls

### Pitfall 1: `insert_image` に既存アルファがない JPEG を渡すと不透明のまま焼き込まれる
**What goes wrong:** JPEG はアルファチャンネルを持たないため、`Image.open(path)` の結果をそのまま `insert_image` に渡すと完全不透明の画像が乗る（D-03 の「50%透過」が効かない）。
**Why it happens:** `.convert("RGBA")` を呼ばずに JPEG を直接使うと Pillow は RGB のまま返す。
**How to avoid:** 必ず `Image.open(path).convert("RGBA")` してから均一 alpha（128）を `putalpha` する。PNG の場合は既存アルファを ×0.5 する（D-03 で明記済み）。
**Warning signs:** テストで透かし適用後にページから抽出した画像の透過が効いていない／`get_text()` では検出できないため、画像バイト自体を検証する必要がある。

### Pitfall 2: `page.derotation_matrix` を `mediabox` ではなく `cropbox` 基準で誤って使う
**What goes wrong:** 既存の `_crop_page`/`_page_rect_from_rel` は `mediabox` を基準に相対座標を計算している。回転変換を挟む位置を間違えると、座標系の基準（mediabox vs cropbox vs page.rect）がずれて二重補正または補正漏れになる。
**Why it happens:** PyMuPDF は `page.rect`（表示矩形・cropbox+回転考慮）と `page.mediabox`（物理定義・回転非考慮）を明確に区別しており [CITED: pymupdf docs discussion #1806]、既存コードは意図的に `mediabox` を使っている（トリミング後もクロップ前の全体を基準にするため）。
**How to avoid:** `_derotate_rect` は「表示座標→未回転座標」の変換のみを担当させ、既存の `mb = page.mediabox` を基準にした相対化ロジック（`rel = x/mb.width` 等）はそのまま温存する。変換の適用順序は「`_canvas_rect_to_pdf` → `_derotate_rect` → 既存の mediabox 相対化」の 1 本道に固定する。
**Warning signs:** 回転 90°/270° のページで矩形の幅と高さが入れ替わって見える、または軸が反転する。

### Pitfall 3: 黒塗り/モザイクの「連続適用」化（D-05）でトリミングとの相互排他が壊れる
**What goes wrong:** 現状 `_toggle_redact_mode`/`_toggle_crop_mode` は互いに相手を OFF にする相互排他。「連続適用（自動 OFF 廃止）」に変更する際、適用後に誤ってモードを OFF にするコード（`_apply_page_edit` 内 `self._redact_mode_off()`）を単純に削除すると、モード状態自体は維持されるが、既存の「他方のモードに切り替えたら自動 OFF」という相互排他の仕組み自体は `_toggle_crop_mode`/`_toggle_redact_mode` 側にあるため触れずに残せる。
**Why it happens:** 「連続適用」と「相互排他」は別々のコードパスにある（適用完了時 vs モード切替時）。混同すると誤って相互排他まで壊しかねない。
**How to avoid:** `_apply_page_edit` 内の `self._redact_mode_off()` 呼び出しのみを削除し、`_toggle_redact_mode`/`_toggle_crop_mode` 内の相互排他コードは変更しない。
**Warning signs:** テストで「黒塗り適用後もモードが ON のまま」を確認した際に、トリミングモードへの切替が黒塗りモードを OFF にしなくなっていないか同時に確認する。

### Pitfall 4: 複数矩形一括適用（D-07）で undo キャプチャのタイミングを誤る
**What goes wrong:** `_save_undo("page_edit", targets=targets)` は「適用前のページ bytes」をキャプチャする。矩形ごとにループの中で毎回 `_save_undo` を呼ぶと、2 個目以降の矩形の undo エントリが「1 個目適用後」の状態を「適用前」として記録してしまい、1 回の undo で完全には戻らなくなる（D-07 は「1 回の `page_edit` でまとめて戻る」ことを要求）。
**Why it happens:** 既存の `_apply_page_edit` は 1 矩形前提で `_save_undo` を 1 回しか呼ばない設計だが、複数矩形化する際にページごとのループと矩形ごとのループの入れ子構造を誤ると多重呼び出しになりやすい。
**How to avoid:** `_save_undo` は対象ページ集合に対して**必ず 1 回だけ**、全矩形適用ループの外側で呼ぶ。
**Warning signs:** 3 矩形適用後に 1 回 undo しても 1 矩形分しか戻らない。

### Pitfall 5: テストで `sample_pdf_doc`（3ページ, A4, テキストのみ）に画像/回転操作の検証を混在させて意図が不明瞭になる
**What goes wrong:** 既存 `conftest.py` の `sample_pdf_doc` はテキストのみの単純フィクスチャ。画像透かしテストで画像データそのものの検証（get_text では検出不能）を怠ると「ページが変更されたことだけ」しか確認できず、実際に画像が正しい位置・透過度で焼き込まれたかを見逃す。
**Why it happens:** 既存の `TestContentOpsUndoFix` はテキスト系操作（`get_text()` で容易に検証可能）に最適化されたパターンのため、画像系の検証観点が抜けやすい。
**How to avoid:** 画像透かしテストでは `page.get_images()` や `page.get_image_info()` でページ内の画像存在・矩形位置を検証する（`get_text()` では検出できないため）。
**Warning signs:** テストが「例外が起きないこと」しか検証していない（グリーンだが無意味なテスト）。

## Code Examples

### mm↔pt 変換（D-10/D-11 共通）

```python
# Source: PDF 仕様上の 1pt = 1/72 inch は既定事実（ASSUMED: 一般 PDF 仕様知識）
PT_PER_MM = 72 / 25.4  # ≈ 2.8346

def pt_to_mm(pt):
    return pt / PT_PER_MM

def mm_to_pt(mm):
    return mm * PT_PER_MM
```

### crop_info 表示拡張（D-11）

```python
# Source: 既存 pagefolio/page_ops.py:326-329 _crop_drag_move の crop_info_var.set() 箇所を拡張
def _format_crop_info(rect_w_pt, rect_h_pt, mb_w_pt, mb_h_pt):
    """「45×60mm（28%）」形式の crop_info 文字列を返す（D-11・純関数）。"""
    w_mm = rect_w_pt / PT_PER_MM
    h_mm = rect_h_pt / PT_PER_MM
    pct = 0.0
    if mb_w_pt > 0 and mb_h_pt > 0:
        pct = (rect_w_pt * rect_h_pt) / (mb_w_pt * mb_h_pt) * 100
    return f"{w_mm:.0f}×{h_mm:.0f}mm（{pct:.0f}%）"
```
`_crop_drag_move` の `self.crop_info_var.set(...)` をこの関数呼び出しに置き換える。純関数化しておけば Tk 非依存でテスト可能。

### 数値指定トリミング（D-10・現在の page.rect 基準を推奨）

```python
# Source: 既存 pagefolio/page_ops.py:349-432 _crop_page の bulk 分岐と同型のクランプロジックを流用
# (ASSUMED: mm 入力の基準を「現在の cropbox」とする実装方針。mediabox 基準にする
#  場合との差異は Open Questions 参照)
def compute_margin_crop_rect(current_cropbox, margin_top_pt, margin_bottom_pt,
                              margin_left_pt, margin_right_pt):
    """現在の cropbox から四辺の余白(pt)を差し引いた新 cropbox を返す（D-10）。
    差し引いた結果が幅/高さ 1pt 未満になる場合は None（安全側フォールバック）。
    """
    x0 = current_cropbox.x0 + margin_left_pt
    y0 = current_cropbox.y0 + margin_top_pt
    x1 = current_cropbox.x1 - margin_right_pt
    y1 = current_cropbox.y1 - margin_bottom_pt
    if x1 - x0 < 1 or y1 - y0 < 1:
        return None
    return (x0, y0, x1, y1)
```

### 矢印キー微調整（D-09）

```python
# Source: 既存 crop_rect（canvas 座標）に対する += 演算の一例（ASSUMED: 未実装コード例）
def _nudge_crop_rect(self, dx_pt, dy_pt, resize=False):
    """確定済み矩形を 1pt 相当の canvas 距離だけ移動/右下辺リサイズする（D-09）。"""
    if not self.crop_rect:
        return
    scale = self.zoom * 1.5  # _canvas_rect_to_pdf と同じスケール
    sx, sy, ex, ey = self.crop_rect
    dx, dy = dx_pt * scale, dy_pt * scale
    if resize:
        ex, ey = ex + dx, ey + dy
    else:
        sx, sy, ex, ey = sx + dx, sy + dy, ex + dx, ey + dy
    self.crop_rect = (sx, sy, ex, ey)
    self._redraw_crop_overlay()  # 既存 _crop_drag_move のオーバーレイ更新部分を再利用
```
矢印キーのバインドは `crop_mode`/`redact_mode` が ON かつ `self.crop_rect` が確定済みのときのみ有効化する（Claude's Discretion: バインド先は `preview_canvas` か `root` か）。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 矩形は未回転ページ座標系にしか正しく適用されない（CLAUDE.md 既知の制限） | `page.derotation_matrix` による表示→未回転座標変換を共通ヘルパー化（D-08） | 本フェーズ（v1.7.1 Phase 3） | 黒塗り/モザイク/トリミングの 3 操作すべてで「見たままの位置」に一貫して適用される。CLAUDE.md §既知の制限・注意事項 の当該記述は本フェーズ完了後に更新が必要（CONTEXT.md canonical_refs に明記済み） |
| 黒塗りモードは適用ごとに自動 OFF | 連続適用（明示トグルのみで OFF）（D-05） | 本フェーズ | 複数箇所を黒塗りする際の操作数が減る |
| テキスト透かしのみ対応 | 画像（ロゴ）透かし対応（D-01〜D-04） | 本フェーズ | v1.5.0 の制限（テキストのみ）解除 |

**Deprecated/outdated:** 特になし（既存 API の非推奨化は本フェーズの対象に含まれない）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | RGBA PNG（アルファ合成済み）を `page.insert_image()` に渡せば PDF 側で半透明表示（SMask）として正しく描画される | Pattern 1 / Code Examples | もし PyMuPDF の `insert_image` が SMask を書き出さない、または一部 PDF ビューアで半透明が反映されない場合、透過表現が効かず D-03 の「50%透過」要件を満たさない。実装後に実際の PDF を PDF ビューアで目視確認する UAT が必須（`checkpoint:human-verify` 推奨） |
| A2 | 数値指定トリミング（D-10）の mm 入力は「現在の cropbox（既存トリミング結果）」を基準に四辺を差し引く（mediabox からの絶対指定ではない） | Code Examples「数値指定トリミング」 | もしユーザー期待が「mediabox からの絶対余白指定」だった場合、既存トリミング済みページに重ねて適用したときの挙動が期待と異なる。CONTEXT.md ではどちらの基準か明記されていないため、planner は discuss 済みの D-10 文言（「上下左右から何mm削るか」）を素直に「現在表示中の状態から削る」と解釈するのが自然だが、計画時に一言確認する価値がある |
| A3 | モザイク粒度スライダーの値域は `from_=4, to=32`（既定 16 = `MOSAIC_BLOCK`）が妥当 | Pattern 3 | 値域が実際の見た目粒度と合わない場合、UAT で再調整が必要になる程度で実害は小さい |
| A4 | ショートカット/D&D の純ロジック抽出は既存モジュール内（`app.py`/`dnd.py`）に留め、新規モジュールを作らない | Pattern 5/6 | 新規モジュール化した方が `pagination.py` パターンに厳密に整合する可能性があるが、抽出範囲が小さいため既存モジュール内 module-level 関数でも実用上問題ない |

**If this table is empty:** N/A（上記 4 件が該当）。

## Open Questions (RESOLVED)

1. **数値指定トリミングの基準（mediabox か 現在の cropbox か）**
   - What we know: CONTEXT.md D-10 は「上下左右から何mm削るか」とだけ記述。矩形座標の直接入力は対象外と明記。
   - What's unclear: 起点が「まっさらな mediabox」か「今表示されている cropbox（既にトリミング済みの場合はその状態）」か。
   - RESOLVED: 「現在の cropbox から差し引く」を既定実装とする（A2）。ページ操作の UX として直感的（「今見えている範囲からさらに削る」）であり、既存のドラッグトリミングとも整合する。→ 03-03 PLAN Task 3 に反映済み。

2. **黒塗り/モザイクの複数矩形オーバーレイの描画方式**
   - What we know: 単一矩形時は 4 象限 stipple（外側を薄暗く）＋実線矩形。CONTEXT.md D-07 は「ドラッグ完了のたびに矩形をリストへ追加しオーバーレイ表示」とだけ指定し、詳細は Claude's Discretion。
   - What's unclear: 複数矩形時も stipple 方式を維持するか、各矩形を単純な実線アウトラインのみにするか（stipple の重ね合わせは計算が複雑になりやすい）。
   - RESOLVED: 複数矩形時は各矩形を実線アウトラインのみで描画し、stipple（外側暗化）は省略する（実装・保守コストが低い）。UAT で見た目の分かりやすさを確認する。→ 03-04 PLAN Task 2 に反映済み。

3. **回転座標ヘルパーの配置場所（page_ops.py static か新規純ロジックモジュールか）**
   - What we know: CONTEXT.md は「純関数化してテストで担保」を要求するが配置は Claude's Discretion。
   - What's unclear: `fitz.Page` オブジェクトを引数に取る時点で `pagination.py` ほど厳密な Tk/fitz 非依存にはできない。
   - RESOLVED: `page_ops.py` 内 `@staticmethod`（Pattern 2 の形・`_derotate_rect`）で実装する。新規モジュール化は本フェーズの投資対効果としては過剰。→ 03-03 PLAN Task 1 に反映済み。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PyMuPDF (fitz) | 全ページ操作・画像埋め込み・回転座標変換 | ✓ [VERIFIED] | 1.27.2.3（実行環境） | — |
| Pillow (PIL) | アルファ合成・モザイク生成 | ✓ [VERIFIED] | 12.2.0（実行環境） | — |
| tkinter / ttk | UI 全般 | ✓（標準ライブラリ・既存アプリ稼働中） | 環境依存 | — |
| tkinterdnd2 | D&D（本フェーズはロジックテストのみで実 D&D イベント発火は対象外・D-16） | ✓（`file_drop.py` に `_HAS_TKDND` フォールバック実装済み） | 0.4.3 | 未インストール時は D&D 無効化（既存フォールバック） |

**Missing dependencies with no fallback:** なし。
**Missing dependencies with fallback:** なし（tkinterdnd2 は既に未インストール時のフォールバックを実装済み）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2（`requirements.txt`） |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`（`testpaths = ["tests"]`） |
| Quick run command | `pytest tests/test_pdf_ops.py tests/test_v150_regression.py -q` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V171-PAGE-01 | 画像透かし追加・undo で元に戻る | unit（FakeApp） | `pytest tests/test_pdf_ops.py -k watermark_image -x` | ❌ Wave 0（新規テストクラス追加） |
| V171-PAGE-02（D-05） | 黒塗り適用後もモードが ON のまま維持される | unit（FakeApp/属性検証） | `pytest tests/test_pdf_ops.py -k redact_mode_persist -x` | ❌ Wave 0 |
| V171-PAGE-02（D-06） | モザイク粒度設定が `_mosaic_page` に反映される | unit | `pytest tests/test_pdf_ops.py -k mosaic_block -x` | ❌ Wave 0 |
| V171-PAGE-02（D-07） | 複数矩形適用が 1 回の undo で全て戻る | unit（FakeApp） | `pytest tests/test_pdf_ops.py -k multi_rect_redact -x` | ❌ Wave 0 |
| V171-PAGE-02/03（D-08） | 回転ページで矩形が見たまま位置に適用される（derotate ヘルパー） | unit（純関数/小 fitz doc） | `pytest tests/test_pdf_ops.py -k derotate -x` | ❌ Wave 0 |
| V171-PAGE-03（D-09） | 矢印キー微調整で crop_rect が期待どおり移動/リサイズ | unit | `pytest tests/test_pdf_ops.py -k nudge_crop -x` | ❌ Wave 0 |
| V171-PAGE-03（D-10） | mm 指定トリミングが cropbox に正しく反映される | unit（純関数 + FakeApp） | `pytest tests/test_pdf_ops.py -k margin_crop -x` | ❌ Wave 0 |
| V171-PAGE-03（D-11） | crop_info が「NN×NNmm（NN%）」形式で表示される | unit（純関数） | `pytest tests/test_pdf_ops.py -k crop_info_format -x` | ❌ Wave 0 |
| V171-TEST-01（TOC） | 削除/結合/分割で TOC が正しく保持・再採番される | unit（FakeApp mixin） | `pytest tests/test_v150_regression.py -k toc -x` | ❌ Wave 0 |
| V171-TEST-01（D&D） | ドロップ座標→挿入位置計算が正しい（純関数） | unit | `pytest tests/test_v150_regression.py -k dnd_dest -x` | ❌ Wave 0 |
| V171-TEST-01（ショートカット） | デフォルト+カスタムのマージ・Shift 大文字補完判定が正しい | unit | `pytest tests/test_v150_regression.py -k shortcuts -x` | ❌ Wave 0 |
| V171-TEST-01（内容検証追加・D-14） | 白紙挿入のページサイズ一致・透かしテキストの `get_text` 抽出確認 | unit（既存テスト拡張） | `pytest tests/test_pdf_ops.py -k roundtrip -x` | ✅ 既存（`TestContentOpsUndoFix`・内容検証追加のみ） |

### Sampling Rate
- **Per task commit:** `pytest tests/test_pdf_ops.py tests/test_v150_regression.py -q`
- **Per wave merge:** `pytest`（フルスイート・707+件を維持しつつ本フェーズ追加分を含める）
- **Phase gate:** フルスイートグリーンを `/gsd-verify-work` 前に確認

### Wave 0 Gaps
- [ ] `tests/test_v150_regression.py` — 新規作成（D-15）。TOC 保持（FakeApp）・D&D 挿入位置計算（純関数）・ショートカットマージ/検証（純関数）の 3 系統を収容
- [ ] `pagefolio/dnd.py` または新規箇所に `compute_dnd_dest_index` 純関数を切り出し（Pattern 5）
- [ ] `pagefolio/app.py` に `merge_shortcuts`/`shift_variant_keysym` 純関数を切り出し（Pattern 6）
- [ ] フレームワークインストール: 不要（pytest は既存 `requirements.txt` に導入済み）

## Security Domain

> `security_enforcement: true`（`.planning/config.json`）・ASVS Level 1

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 本フェーズはローカルデスクトップのページ編集機能で認証境界なし |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 単一ユーザー・ローカルファイルアクセスのみ |
| V5 Input Validation | yes | 画像ファイル選択（`filedialog` フィルタで PNG/JPEG に限定・D-04）、mm 数値入力（負値・過大値のクランプ、Pattern「数値指定トリミング」の `if x1 - x0 < 1` 安全側フォールバックを踏襲） |
| V6 Cryptography | no | 本フェーズはパスワード/暗号化を扱わない（Phase 1 で完了済み・変更なし） |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 悪意ある/破損画像ファイルによる Pillow デコード時のクラッシュ・リソース消費 | Denial of Service | `Image.open()` を `try/except Exception` で保護し `messagebox.showerror` へフォールバック（既存 `_do_export_images` 等の例外ハンドリングパターンを踏襲） |
| 数値トリミング入力での不正値（負のmm・文字列・極端に大きい値）によるページサイズ破壊 | Tampering | `compute_margin_crop_rect` の `if x1 - x0 < 1 or y1 - y0 < 1: return None` 安全側フォールバック（既存 `_crop_page` の `EPS`/`is_empty` チェックと同型） |
| 黒塗り/モザイクは既に破壊的削除（`apply_redactions`）を実施しており本フェーズでは後退させない | Information Disclosure | 複数矩形一括適用（D-07）でも各矩形について既存の `_redact_page`/`_mosaic_page`（下地コンテンツの実削除→焼き込み）を個別に呼ぶ設計を維持し、「複数矩形の一部だけ下地が残る」ことがないようにする |

## Sources

### Primary (HIGH confidence)
- コードベース直接読解: `pagefolio/page_ops.py`, `pagefolio/redact_ops.py`, `pagefolio/file_ops.py`, `pagefolio/dnd.py`, `pagefolio/viewer.py`, `pagefolio/app.py`, `pagefolio/ui_builder.py`, `pagefolio/constants.py`, `pagefolio/settings.py`, `pagefolio/pagination.py`, `tests/test_pdf_ops.py`, `tests/conftest.py`, `tests/test_lang_parity.py`
- 実行環境バージョン確認: `python -c "import fitz; print(fitz.__version__)"` → 1.27.2.3、`python -c "import PIL; print(PIL.__version__)"` → 12.2.0

### Secondary (MEDIUM confidence)
- [PyMuPDF Page — 公式ドキュメント](https://pymupdf.readthedocs.io/en/latest/page.html) — `rotation_matrix`/`derotation_matrix`/`mediabox`/`cropbox`/`page.rect` の定義・回転座標系の扱い
- [PyMuPDF Images recipe — 公式ドキュメント](https://pymupdf.readthedocs.io/en/latest/recipes-images.html) — `insert_image` と透明度・Pixmap alpha 操作
- [PyMuPDF coordinate system(s) Discussion #1806](https://github.com/pymupdf/PyMuPDF/discussions/1806) — mediabox/cropbox/page.rect の関係
- [PyMuPDF alpha transparency Discussion #1006](https://github.com/pymupdf/PyMuPDF/discussions/1006) — PDF における画像透過の扱い（アルファはビットマップ側の属性）

### Tertiary (LOW confidence)
- なし（本フェーズは既存コードベースの直接延長のため、未検証の Web 情報への依存度は低い）

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 新規依存なし、既存 `requirements.txt` と実行環境のバージョンを直接確認済み
- Architecture: HIGH — 全パターンが既存コード（テキスト透かし・pagination.py 純ロジック層・thumb_zoom_scale スライダー）の直接延長
- 回転座標変換（D-08）: MEDIUM — `derotation_matrix` の存在・目的は公式ドキュメントで確認済みだが、本プロジェクトの `_canvas_rect_to_pdf` 座標系との厳密な整合は実装時に小さな fitz.Document で実地検証が必要
- Pitfalls: HIGH — 既存コード構造（`_save_undo` のタイミング・相互排他ロジックの分離）を直接読解した上での分析

**Research date:** 2026-07-05
**Valid until:** 2026-08-04（30日・PyMuPDF/Pillow は安定 API のため長め猶予。ただし derotation_matrix の実地検証は実装直後に再確認すること）
