# Phase 01: コード品質改善とレスポンシブ UI - Research

**Researched:** 2026-03-18
**Domain:** Python Tkinter レスポンシブレイアウト（PanedWindow 3ペイン化）
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### レイアウト構成
- 3ペイン構成: サムネイル | プレビュー | ツールを全て PanedWindow で分割
- 現在の左中 PanedWindow + 右固定 Frame を、3ペイン PanedWindow に再構築
- ヘッダー（「✦ PageFolio」+ ステータス）は現状維持（pack(fill="x") で問題なし）
- ウィンドウ最小サイズ: 800x600 を `root.minsize()` で設定

#### パネルサイズ
- サムネイルパネル最小幅: 150px（現状維持）
- プレビューパネル最小幅: 300px（現状維持）
- ツールパネル最小幅: 220px（現在の固定260pxから縮小可能に）
- デフォルト比率: 20:50:30（サムネイル:プレビュー:ツール）

#### バグ修正
- 既知のバグは特になし — コードレビューで Claude が探して修正
- レビュー範囲はレイアウト関連（_build_ui 周辺）を中心に
- レイアウト再構築と同時に修正できるバグを優先

#### リビルド挙動
- _rebuild_ui() でパネル比率がデフォルトにリセットされるのは許容
- パネル比率は設定ファイルに保存しない（セッション内のみ）
- テーマ切替・フォント変更は頻繁ではないので、リセットで問題なし

### Claude's Discretion
- sash（ドラッグ境界線）のスタイル（色・幅）
- PanedWindow の opaqueresize 設定
- 右ペイン内部のスクロール Canvas 構成の調整方法
- レイアウト関連以外のバグ修正の優先判断

### Deferred Ideas (OUT OF SCOPE)
なし — ディスカッションはフェーズスコープ内に収まった
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | ウィンドウリサイズに応じてレイアウトが自動調整される（右側見切れ解消） | 3ペイン PanedWindow で右側も expand=True になり見切れが解消される |
| UI-02 | PanedWindow による分割ペインでユーザーがパネル比率を調整できる | tk.PanedWindow の sash ドラッグで実現。ツールパネルを3つ目のペインとして追加 |
| UI-03 | サムネイルパネルが最小幅を保証し、狭いウィンドウでも消えない | `paned.add(..., minsize=150)` で既に実装済み。3ペイン化後も同じ引数で継続 |
| QUAL-01 | 全体コードレビューでバグを修正する | レイアウト再構築時に発見した問題を同時修正。主要リスクは後述の Integration Points |
</phase_requirements>

---

## Summary

現在の `_build_ui()` は左中を `tk.PanedWindow` で分割し、右ペインを `pack(side="right", fill="y") + pack_propagate(False)` で固定幅として配置している。この構成ではウィンドウを縮小した際に右ペインが優先確保され、中央プレビューが圧迫された後に右ペインが見切れるという問題がある。

修正方針は `_build_ui()` を書き直し、既存の 2ペイン PanedWindow をヘッダー下の全面をカバーする 3ペイン `tk.PanedWindow(orient="horizontal")` に置き換えることである。左（サムネイル）・中（プレビュー）・右（ツール）の3つ全てを `paned.add()` で追加し、各ペインに minsize を設定する。`_build_tools_scrollable()` などの内部メソッドは親ウィジェット引数を受け取る構造のため、ほぼそのまま流用できる。

QUAL-01（コードレビュー）については、レイアウト再構築の過程でコードを精査し、発見した問題を同時修正する。特に `_rebuild_ui()` での状態リセット漏れ、crop モード中の UI 再構築、プラグイン UI フレームの参照などがリスク箇所となる。

**Primary recommendation:** `_build_ui()` を 3ペイン `tk.PanedWindow` に書き直し、右ペインの固定 Frame を廃止する。デフォルト sash 位置は `paned.update_idletasks()` 後に `paned.sash_place()` で初期比率 20:50:30 を設定する。

---

## Standard Stack

### Core（変更なし — プロジェクト制約）

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.8+ | 実行環境 | プロジェクト固定 |
| tkinter | stdlib | GUI フレームワーク | プロジェクト固定 |
| pymupdf (fitz) | installed | PDF 処理 | プロジェクト固定 |
| Pillow | installed | 画像処理 | プロジェクト固定 |

新規ライブラリの追加は不要。全て標準ライブラリまたは既存依存で実装可能。

**Installation:** 追加インストール不要

---

## Architecture Patterns

### 現在のレイアウト構造（変更前）

```
root
├── header (pack fill="x", side="top")
└── main (pack fill="both", expand=True)
    ├── right Frame (pack side="right", fill="y", pack_propagate=False)  ← 固定幅
    └── paned PanedWindow (pack side="left", fill="both", expand=True)
        ├── left Frame (minsize=150, width=left_width)
        └── center Frame (minsize=300)
```

**問題点:** 右ペインが固定幅で `pack(side="right")` のため、ウィンドウ縮小時に right が優先され left/center が圧迫される。さらに極端に縮小すると right 自体も見切れる。

### 推奨レイアウト構造（変更後）

```
root
├── header (pack fill="x", side="top") — 変更なし
└── paned tk.PanedWindow (pack fill="both", expand=True)
    ├── left Frame (minsize=150, width=left_width)   — thumb panel
    ├── center Frame (minsize=300)                   — preview panel
    └── right Frame (minsize=220, width=right_width) — tools panel
```

### Pattern 1: 3ペイン PanedWindow の構築

**What:** ヘッダー直下の main フレームを廃止し、PanedWindow を直接 root に pack する。
**When to use:** 全ウィジェット間のリサイズを有効にする場合。

```python
# _build_ui() 内
paned = tk.PanedWindow(self.root, orient="horizontal",
                       bg=C["BG_DARK"],
                       sashwidth=5, sashrelief="flat",
                       opaqueresize=True, bd=0)
paned.pack(fill="both", expand=True)

left_width = max(200, int(self.font_size * 18))
left = tk.Frame(paned, bg=C["BG_PANEL"])
self._build_thumb_panel(left)
paned.add(left, minsize=150, width=left_width)

center = tk.Frame(paned, bg=C["BG_DARK"])
self._build_preview(center)
paned.add(center, minsize=300)

right_width = max(260, int(self.font_size * 22))
right = tk.Frame(paned, bg=C["BG_PANEL"])
self._build_tools_scrollable(right)
paned.add(right, minsize=220, width=right_width)
```

### Pattern 2: 初期 sash 位置の設定

**What:** `paned.add()` の `width` パラメータは初期幅のヒントだが、PanedWindow が配置された後に `sash_place()` で明示的に設定する方が確実。
**When to use:** デフォルト比率 20:50:30 を保証したい場合。

```python
def _set_sash_positions(self, paned):
    """ウィンドウ描画後に sash 位置をデフォルト比率で設定"""
    paned.update_idletasks()
    total = paned.winfo_width()
    if total > 100:
        sash0 = int(total * 0.20)  # サムネイル: 20%
        sash1 = int(total * 0.70)  # プレビュー終端: 70%
        paned.sash_place(0, sash0, 0)
        paned.sash_place(1, sash1, 0)
```

`_build_ui()` 末尾で `self.root.after_idle(lambda: self._set_sash_positions(paned))` として呼び出す。

### Pattern 3: ウィンドウ最小サイズ変更

**What:** 現在 `root.minsize(900, 600)` が設定されている。UI-01/03 の受け入れ基準は 800x600 での動作を含む。
**When to use:** minsize 変更時。

```python
self.root.minsize(800, 600)
```

注意: 3ペインの minsize 合計（150 + 300 + 220 = 670px）+ sash幅（5*2 = 10px）= 680px で、800px のウィンドウ最小幅は余裕を持って収まる。

### Pattern 4: _rebuild_ui() での paned 参照管理

**What:** `_rebuild_ui()` は `root.winfo_children()` を全て destroy してから再構築するため、PanedWindow への参照はインスタンス変数に保存する必要はない。ただし `_set_sash_positions` にアクセスするため、`_build_ui()` がローカル変数 `paned` を after_idle クロージャでキャプチャすれば十分。

### Anti-Patterns to Avoid

- **固定幅パネルの `pack(side="right")`**: 拡大時のみ右が縮まらず、縮小時は見切れる原因。3ペインへの移行で廃止。
- **`pack_propagate(False)` 単独での幅管理**: `PanedWindow` の `minsize`/`width` パラメータに委ねる。
- **`after_idle` なしの `sash_place()`**: ウィジェットが描画される前に呼ぶと `winfo_width()` が 1 を返す。必ず `after_idle` または `after(50, ...)` で遅延させる。
- **`_build_tools_scrollable` 内の `inner.after(300, ...)` の多重呼び出し**: 既存コードは `after_idle`、`after(100)`、`after(300)` の3回スクロールリセットを行っている。これはバグではないが冗長であり、1回に統一できる。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ペイン間ドラッグリサイズ | 自前のドラッグハンドル実装 | `tk.PanedWindow` | Tkinter 標準機能で完全動作 |
| ウィンドウ最小サイズ強制 | Configure イベントでの手動クランプ | `root.minsize()` | OS/Tkinter が自動処理 |
| パネル最小幅強制 | Configure イベントでのチェック | `paned.add(..., minsize=N)` | PanedWindow が sash ドラッグ時に自動制限 |

---

## Common Pitfalls

### Pitfall 1: sash_place() のタイミング

**What goes wrong:** `_build_ui()` 内で `paned.sash_place(0, x, 0)` を直接呼ぶと、ウィジェットがまだ画面に描画されておらず `winfo_width()` が 1 を返すため、比率計算が無意味になる。
**Why it happens:** Tkinter のジオメトリ計算は idle 時に行われる。
**How to avoid:** `paned.update_idletasks()` を呼んだ後でも `winfo_width()` が 0 の場合は `after_idle` または `after(50, ...)` で遅延させる。
**Warning signs:** sash が画面左端に寄った状態で起動する。

### Pitfall 2: _build_tools_scrollable の inner フレーム参照

**What goes wrong:** `_build_tools()` 内で `self._plugin_ui_frame` を `parent`（=inner フレーム）の子として作成しているが、`_rebuild_ui()` で inner が destroy された後も `self._plugin_ui_frame` にアクセスすると例外が発生する可能性がある。
**Why it happens:** `_rebuild_ui()` は `self._plugin_ui_frame` をリセットしない。
**How to avoid:** `_rebuild_ui()` か `_build_tools()` の先頭で `self._plugin_ui_frame = None` とリセットする。または `_build_plugin_ui()` で `winfo_exists()` チェックを行う。
**Warning signs:** テーマ切替後にプラグイン UI が二重表示される、または AttributeError。

### Pitfall 3: crop モード中の _rebuild_ui()

**What goes wrong:** トリミングモードが ON の状態でテーマ切替・フォント変更を行うと、`_rebuild_ui()` が `self.crop_mode = False` にリセットするが、`self.preview_canvas` への crop バインドは再設定される。ただし crop_rect_id、crop_overlay_ids は正しくリセットされている（L1918-1919）。
**Why it happens:** `_rebuild_ui()` の既存実装は概ね適切だが、ボタンスタイルのリセット確認が必要。
**How to avoid:** `_rebuild_ui()` 後に `self.crop_toggle_btn` のスタイルが正しく "TButton"（OFF状態）に戻っているか確認。既存コードは `_build_tools()` が `self.crop_mode_var = tk.BooleanVar(value=False)` で初期化するので問題ない。

### Pitfall 4: 右ペインスクロール Canvas の幅追従

**What goes wrong:** 3ペイン化後に右ペインをユーザーがリサイズすると、`_build_tools_scrollable()` の inner フレーム幅がキャンバス幅に追従しない場合がある。
**Why it happens:** 既存の `canvas.bind("<Configure>", ...)` でキャンバス幅変更時に `itemconfigure("inner_window", width=e.width)` を呼んでいるため、通常は問題ない。
**How to avoid:** 3ペイン化後も同じバインドが機能することを確認。sash ドラッグ時にもキャンバスが Configure イベントを受け取ることを確認する（通常は自動的に発火する）。
**Warning signs:** 右ペインを広くしてもボタンが左に固まったまま。

### Pitfall 5: MAX_UNDO 定数の未定義リスク

**What goes wrong:** `self.MAX_UNDO` が `__init__` で参照されているが（`_save_undo` 内 L994: `if len(self._undo_stack) > self.MAX_UNDO`）、クラス変数またはインスタンス変数として定義されているか確認が必要。
**Why it happens:** コードレビュー（QUAL-01）での確認項目。
**How to avoid:** `__init__` で `self.MAX_UNDO = 20` として定義されているか、クラス変数として `MAX_UNDO = 20` があるか確認する。

---

## Code Examples

### 3ペイン PanedWindow への _build_ui() 書き換え

```python
# Source: Tkinter 標準ライブラリ + 現在コードの流用
def _build_ui(self):
    header_h = max(56, int(self.font_size * 5))
    header = tk.Frame(self.root, bg=C["BG_PANEL"], height=header_h)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)
    tk.Label(header, text="✦ PageFolio", bg=C["BG_PANEL"],
             fg=C["ACCENT"], font=self._font(6, "bold")).pack(side="left", padx=20, pady=12)
    self.status_var = tk.StringVar(value=self._t("status_initial"))
    tk.Label(header, textvariable=self.status_var,
             bg=C["BG_PANEL"], fg=C["SUCCESS"],
             font=self._font(-1)).pack(side="right", padx=20)

    # 3ペイン PanedWindow — ヘッダー直下に直接配置
    paned = tk.PanedWindow(self.root, orient="horizontal", bg=C["BG_DARK"],
                           sashwidth=5, sashrelief="flat",
                           opaqueresize=True, bd=0)
    paned.pack(fill="both", expand=True)

    left_width = max(200, int(self.font_size * 18))
    left = tk.Frame(paned, bg=C["BG_PANEL"])
    self._build_thumb_panel(left)
    paned.add(left, minsize=150, width=left_width)

    center = tk.Frame(paned, bg=C["BG_DARK"])
    self._build_preview(center)
    paned.add(center, minsize=300)

    right_width = max(260, int(self.font_size * 22))
    right = tk.Frame(paned, bg=C["BG_PANEL"])
    self._build_tools_scrollable(right)
    paned.add(right, minsize=220, width=right_width)

    # デフォルト比率設定（描画後に実行）
    def _set_sash():
        paned.update_idletasks()
        total = paned.winfo_width()
        if total > 100:
            paned.sash_place(0, int(total * 0.20), 0)
            paned.sash_place(1, int(total * 0.70), 0)
    self.root.after_idle(_set_sash)
```

### minsize 変更

```python
# __init__ 内
self.root.minsize(800, 600)  # 900 → 800 に変更
```

### _rebuild_ui() での paned 参照は不要

```python
# 既存の _rebuild_ui() はそのまま流用可能
# winfo_children() で全 destroy → _build_ui() で再構築される
# _build_ui() 内の after_idle クロージャが paned をキャプチャするため参照保存不要
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 右ペイン固定幅 `pack(side="right")` | 3ペイン `tk.PanedWindow` の3番目のペイン | Phase 1 実装時 | UI-01/UI-02/UI-03 対応、右見切れ解消 |
| `root.minsize(900, 600)` | `root.minsize(800, 600)` | Phase 1 実装時 | 800px 幅での動作保証 |

---

## Open Questions

1. **MAX_UNDO 定数の定義場所**
   - What we know: `_save_undo()` で `self.MAX_UNDO` を参照している（L994）
   - What's unclear: `__init__` に `self.MAX_UNDO = 20` があるか未確認（L610-665 を精査したが見当たらない）
   - Recommendation: 実装時に `__init__` を確認し、なければ追加する（QUAL-01 の修正対象）

2. **`_build_tools_scrollable` 内の多重 after() スクロールリセット**
   - What we know: `after_idle`・`after(100)`・`after(300)` の3回呼び出しがある（L882-884）
   - What's unclear: これが特定の競合条件への対処として意図的なものか
   - Recommendation: 冗長であればコードレビュー（QUAL-01）で整理する対象だが、動作に問題がなければ低優先度

3. **sash の色・スタイル（Claude's Discretion）**
   - What we know: 現在 `sashrelief="flat"` `sashwidth=5` で実装済み
   - What's unclear: テーマ切替時に sash 色が変わるか（`tk.PanedWindow` の `bg` はテーマ色を使用）
   - Recommendation: `bg=C["BG_DARK"]` を維持し、sash が自然に溶け込む設定で問題なし

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | なし（テストファイル未存在） |
| Config file | なし — Wave 0 で作成不要（GUI アプリ、手動テストのみ） |
| Quick run command | `python -c "import ast; ast.parse(open('pagefolio.py').read()); print('OK')"` |
| Full suite command | `python pagefolio.py`（手動起動・目視確認） |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | ウィンドウリサイズ後に右ペインが見切れない | manual | 手動：ウィンドウを狭くして右ツールパネルを確認 | N/A |
| UI-02 | sash ドラッグでパネル比率変更できる | manual | 手動：各 sash をドラッグして動作確認 | N/A |
| UI-03 | 極端に狭いウィンドウでサムネイルパネルが消えない | manual | 手動：最小サイズ 800x600 まで縮小して確認 | N/A |
| QUAL-01 | 構文エラーがない | automated | `python -c "import ast; ast.parse(open('pagefolio.py').read())"` | ❌ コマンドのみ |
| QUAL-01 | 既存機能が正常動作する | manual | 手動：回転・削除・トリミング・結合・D&D・Undo/Redo | N/A |

### Sampling Rate

- **実装タスク完了ごと:** `python -c "import ast; ast.parse(open('pagefolio.py').read()); print('構文OK')" `
- **フェーズ完了時:** 手動でアプリ起動し、全既存機能を一通り確認

### Wave 0 Gaps

テストフレームワークの導入は Phase 1 のスコープ外。GUI の手動テストが主体となる。自動化可能な構文チェックのみ各タスク後に実行する。

---

## Sources

### Primary (HIGH confidence)

- Tkinter 標準ライブラリ（Python 3.8+ 同梱）— PanedWindow API 直接確認
- `pagefolio.py` L720-755 — 既存 `_build_ui()` の実装（直接読取）
- `pagefolio.py` L846-884 — 既存 `_build_tools_scrollable()` の実装（直接読取）
- `pagefolio.py` L758-793 — 既存 `_build_thumb_panel()` の実装（直接読取）
- `pagefolio.py` L1907-1926 — 既存 `_rebuild_ui()` の実装（直接読取）
- `.planning/phases/01-code-quality-responsive-ui/01-CONTEXT.md` — ユーザー決定事項（直接読取）

### Secondary (MEDIUM confidence)

- CLAUDE.md — クラス構成・コーディング規約・状態管理ルール（直接読取）
- `.planning/REQUIREMENTS.md` — UI-01/02/03、QUAL-01 受け入れ基準（直接読取）

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 既存コードを直接確認、新規ライブラリなし
- Architecture: HIGH — Tkinter PanedWindow は標準機能、既存コードの構造を精査済み
- Pitfalls: MEDIUM-HIGH — コードを直接読んで特定したリスク、一部実行時確認が必要

**Research date:** 2026-03-18
**Valid until:** 2026-06-18（Tkinter 標準ライブラリは変化が少ないため90日）
