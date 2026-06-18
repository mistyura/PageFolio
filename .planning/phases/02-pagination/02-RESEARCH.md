# Phase 2: 大量ページのページネーション表示 - Research

**Researched:** 2026-06-18
**Domain:** Tkinter サムネイル窓化（ページネーション）＋「ローカル位置 ↔ 全ページインデックス」変換層
**Confidence:** HIGH（コードベース実地検証ベース。外部依存なし、新規ライブラリなし）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 窓の移動手段は **前/次窓ボタン（◀ ▶）＋「1–20 / 全120」形式の範囲ラベル**。ページ番号ジャンプ入力やドロップダウン選択は採用しない。
- **D-02:** ナビゲーションコントロールの配置は **サムネイル canvas の下（フッター）に独立行**。`_build_thumb_panel` の canvas 群の後に `pack(fill="x")` で追加。
- **D-03:** 表示件数の変更 UI は **フッターのナビ行に置く Spinbox**（「表示: [20]件」等）。設定ダイアログへの集約は採らない。
- **D-04:** 表示件数の **既定値は 20、許容範囲は 10〜100**。
- **D-05:** 表示件数は **`pagefolio_settings.json` に永続化**し次回起動時に復元。`_save_settings()` 経由。永続化キー名は実装裁量（候補 `thumb_page_size`）。
- **D-06:** **D&D 並び替えは表示中の窓内に限定**。ドロップ位置はローカル位置として受け取り、**全ページインデックスへ変換してから** `move_page` / `bulk_move` を適用。`global = local_pos + window_start`。
- **D-07:** **複数選択（`selected_pages`）は窓をまたいで保持**。`selected_pages` は従来どおり**全ページインデックス**を保持。
- **D-08:** **「全選択 / 全解除」ボタンは全ドキュメント対象**（既存 `_select_all` / `_deselect_all` を踏襲）。
- **D-09:** **ページ数が表示件数以下でも常にナビを表示**（単一窓・前/次ボタンは disabled）。「1–8 / 全8」のように表示。
- **D-10:** 端数の最終窓は実ページ数まで表示（例: 件数 20・全 47 → 最終窓「41–47 / 全47」）。
- **D-11:** **表示窓は `current_page` を含む窓へ自動追従**。`current_page` が表示窓外へ出たら、その窓へ自動切替。

### Claude's Discretion
- 永続化キー名（D-05、候補 `thumb_page_size`）。
- 窓オフセット状態の属性名（例: `self._page_window_start` / `self._page_size`）。
- Spinbox の即時反映タイミング（値変更ごと / フォーカスアウト / `<<Increment>>`）。ただし「変更が永続化され再描画される」ことは必須。
- 範囲ラベルの文言・区切り記号（LANG ja/en 同一キー規約に従う）。
- D&D ゴースト/インジケータのローカル↔グローバル変換の実装詳細。ただし「意図したページが正しい全ページ位置へ移動する」ことは必須。

### Deferred Ideas (OUT OF SCOPE)
- サムネイル仮想化（スクロール位置に応じた本格的な遅延ロード基盤）— 本フェーズは「窓で区切る」最小実装に留める。
- クロス窓 D&D（別窓へドラッグして移動）— 不採用（D-06）。
- ページ番号ジャンプ入力 / 窓ドロップダウン選択 — 最小実装では不採用（D-01）。
- 体感品質・回転プレビュー即時反映 / OCR 堅牢性 → Phase 3。
- AI 出力品質 → Phase 4。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V16-UI-03 | 大量ページ PDF でサムネイル一覧を可変件数（既定 20）で区切って表示、表示件数を `pagefolio_settings.json` に永続化、ページング下でも D&D・複数選択が全ページインデックスと整合 | 本書「Architecture Patterns」（変換層の単一集約）、「Validation Architecture」（純ロジックヘルパーのヘッドレス検証）、「Common Pitfalls」（世代ガード・thumb_cache・Spinbox readonly）が実装と検証の技術的裏付けを提供 |
</phase_requirements>

## Summary

本フェーズは新規ライブラリ・外部 API・ネットワーク・永続データ移行を一切伴わない**純粋なローカル UI 改修**である。CONTEXT.md（D-01〜D-11）と canonical_refs が既にコードの行番号レベルまで設計を固めているため、本リサーチは「それらをどう**正しく実装し・どう検証するか**」の技術的裏付けに集中する。

核心は**「表示窓のローカル位置 ↔ 全ページインデックス」変換層**である。現状コードは「サムネイルの並び位置 = 全ページ index」という暗黙の前提（`_refresh_thumbs_selection_only` の `enumerate`、`_add_thumb_placeholder` のクロージャ束縛 `idx=i`、`_dnd_dest_index` のフレーム位置）に依存している。窓化するとこの前提が崩れるため、`global = local + window_start` / `local = global - window_start` の変換を**1 箇所のヘルパーに集約**し、サムネイル描画・選択ハイライト照合・D&D ドロップ先換算のすべてがそれを参照する構成が要となる。

**Primary recommendation:** 窓状態（`window_start`・`page_size`）と変換ロジックを **Tkinter 非依存の純関数群**として切り出し（既存の `_render_preview_pixmap` と同じ「純ロジック＋スタブテスト」の作法）、`tests/test_pagination.py` で `types.SimpleNamespace` スタブ＋プロパティ/境界値テストにより不変条件をヘッドレス検証する。ウィジェット描画そのものはテストせず、変換とクランプの数学だけを徹底的にテストする。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 窓範囲の算出（start/size/最終窓端数） | 純ロジック（Tk 非依存ヘルパー） | — | テスト容易性・整合性の単一の真実。描画から分離できる |
| ローカル↔グローバル index 変換 | 純ロジック（Tk 非依存ヘルパー） | — | D-06/D-07 の整合の核。散在させない（CONTEXT integration point） |
| `current_page` の窓追従（D-11） | 純ロジック（窓決定） | 状態更新（`self.*`） | 「current を含む窓」の決定は純関数、属性反映は呼び出し側 |
| サムネイル窓描画 | ViewerMixin（Tkinter） | 純ロジック（窓範囲） | 描画件数を窓範囲に絞る。世代ガード枠組みは維持 |
| ナビ/件数フッター UI | UIBuilderMixin（Tkinter） | settings（永続化） | `_build_thumb_panel` フッター行に閉じる |
| D&D ドロップの index 換算 | DnDMixin（Tkinter イベント） | 純ロジック（変換） | イベント→ローカル位置→グローバル換算→既存 move_page/bulk_move |
| 件数の永続化/復元 | settings.py（DEFAULT_SETTINGS） | — | 既存 `thumb_zoom` と同じ作法 |

## Standard Stack

外部パッケージの新規追加は **なし**。本フェーズは既存スタックのみで完結する。

### Core（既存・変更なし）
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tkinter | 標準ライブラリ | GUI（Spinbox・ボタン・ラベル・Canvas） | プロジェクト全体の UI 基盤 [VERIFIED: codebase] |
| PyMuPDF (fitz) | 1.27.2.2 | ページ数取得・サムネイル描画 | 既存サムネイル生成と同一 [VERIFIED: requirements.txt] |
| Pillow (PIL) | 12.2.0 | サムネイル画像変換 | 既存と同一 [VERIFIED: requirements.txt] |

### 使用する Tkinter ウィジェット（新規利用）
| Widget | Purpose | When to Use |
|--------|---------|-------------|
| `ttk.Spinbox` | 表示件数（10〜100, 既定 20）入力 | D-03/D-04。**`ttk.Spinbox` 推奨**（`tk.Spinbox` ではなく — readonly 表示色とスタイル統合のため。Pitfall 参照） [CITED: docs.python.org/3/library/tkinter.ttk] |
| `ttk.Button` | 前/次窓ボタン（◀ ▶） | D-01。既存プレビュー前/次ページボタンと一貫 [VERIFIED: codebase ui_builder/viewer] |
| `tk.Label` | 範囲ラベル「1–20 / 全120」 | D-01/D-09/D-10 [VERIFIED: codebase] |

**Installation:** 不要（標準ライブラリ・既存依存のみ）。

**Version verification:**
```bash
# 既存依存の確認のみ（新規追加なし）
python -c "import fitz, PIL, tkinter; print(fitz.__doc__[:40])"
```
[VERIFIED: codebase — requirements.txt に pymupdf 1.27.2.2 / Pillow 12.2.0 固定]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ttk.Spinbox` | `tk.Spinbox` | `tk.Spinbox` は readonly 時もスピンボタンが押せ、暗テーマでの readonly 背景色が別オプション指定で扱いづらい（MEMORY: tkinter-readonly-widget-gotchas）。`ttk.Spinbox` は `state="readonly"` でスタイル統合が容易 |
| `ttk.Spinbox` | 前/次窓ボタンのみ＋ラベルクリック編集 | D-03 が Spinbox を明示。代替は採らない |

## Package Legitimacy Audit

> 本フェーズは外部パッケージを**一切インストールしない**（標準ライブラリ + 既存固定依存のみ）。

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| （新規なし） | — | — | — | — | — | N/A |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
                          [窓状態の単一の真実 = self.*]
                          window_start (int) , page_size (int)
                                     │
        ┌────────────────────────────┼───────────────────────────────┐
        │                            │                               │
   [純ロジック層: Tk 非依存ヘルパー]   │                               │
        │                            │                               │
   window_bounds(start,size,n) ──► (lo, hi)   端数最終窓を考慮         │
   to_global(local, start)     ──► global = local + start            │
   to_local(global, start)     ──► local  = global - start           │
   window_for_page(page,size)  ──► start    current_page を含む窓     │
   clamp_window(start,size,n)  ──► 有効な start（削除/件数変更後）      │
        │                            │                               │
        └──────────┬─────────────────┴───────────────┬───────────────┘
                   │                                 │
   描画入力 ──► [ViewerMixin._build_thumbnails]    [DnDMixin._dnd_drop]
        range(lo,hi) のみ描画                  event→canvas y→ローカル dest
        _add_thumb_placeholder(global_i)       to_global(dest,start)→既存 move_page/bulk_move
        世代ガード _thumb_gen 維持                     │
                   │                                 │
   選択照合 ──► [_refresh_thumbs_selection_only]      │
        enumerate(local) → to_global → selected_pages 照合
                   │                                 │
        ┌──────────┴──────────────┐                  │
   [UIBuilderMixin フッター行]      │                  │
   ◀ ▶  「1–20 / 全120」  件数Spinbox │                  │
        │                          │                  │
   窓移動 / 件数変更 ──► _save_settings ──► _invalidate_thumb_cache ──► _refresh_all
                                                       │
                          ページ操作後 current_page 移動 ──► window_for_page で D-11 追従
```

データ流れの読み方: 全ての index 変換は純ロジック層の 5 関数を経由する。Tkinter 層（描画・イベント）は変換結果を受け取るだけで、`+ window_start` / `- window_start` の算術を直書きしない。これが「変換を 1 箇所に集約」（CONTEXT integration point）の具体形。

### Recommended Project Structure（既存ファイルへの追加。新規ファイルは任意）
```
pagefolio/
├── viewer.py        # _build_thumbnails を窓範囲描画へ / _refresh_thumbs_selection_only に変換 / 窓ヘルパー（純関数）を配置
├── dnd.py           # _dnd_drop / _dnd_dest_index に local→global 変換を挿入
├── ui_builder.py    # _build_thumb_panel に ナビ/件数フッター行を追加
├── settings.py      # DEFAULT_SETTINGS に表示件数キー追加
└── (任意) pagination.py  # 純ロジックヘルパーを独立モジュール化する場合の置き場（裁量）
tests/
└── test_pagination.py   # 新規。窓計算・変換・クランプ・追従の純ロジック検証
```

**純ロジックの配置についての裁量:** 変換ヘルパーは (a) `viewer.py` に Mixin メソッド（`@staticmethod` または `self` 非依存メソッド）として置く、(b) 新規 `pagefolio/pagination.py` にモジュール関数として置く、のどちらでもよい。**(b) のモジュール関数を弱く推奨** — `from pagefolio.pagination import window_bounds` で import でき、テストが Mixin スタブすら不要になり最も軽い。ただし既存 `_render_preview_pixmap` は (a) 方式（Mixin メソッド＋スタブ）で十分機能しているため、どちらでも整合性は保てる。

### Pattern 1: 純ロジック変換層（Tk 非依存）
**What:** 窓計算と index 変換を引数→戻り値の純関数にする。状態（`self.window_start` 等）の読み書きは呼び出し側に残す。
**When to use:** 全ての index 変換・窓境界算出。
**Example:**
```python
# Source: 既存 _render_preview_pixmap（viewer.py:40-49）の純ロジック作法に倣う [VERIFIED: codebase]
def window_bounds(window_start, page_size, n_pages):
    """表示窓 [lo, hi) を返す。最終窓の端数を n_pages でクランプ（D-10）。"""
    if n_pages <= 0:
        return (0, 0)
    lo = max(0, min(window_start, max(0, n_pages - 1)))
    hi = min(lo + page_size, n_pages)
    return (lo, hi)

def to_global(local_pos, window_start):
    return local_pos + window_start          # D-06

def to_local(global_idx, window_start):
    return global_idx - window_start

def window_for_page(page_idx, page_size):
    """page_idx を含む窓の start を返す（D-11 追従の基礎）。"""
    if page_size <= 0:
        return 0
    return (page_idx // page_size) * page_size

def clamp_window_start(window_start, page_size, n_pages):
    """削除・件数変更後に window_start を有効範囲へ寄せる。"""
    if n_pages <= 0 or page_size <= 0:
        return 0
    last_start = ((n_pages - 1) // page_size) * page_size
    return max(0, min(window_start, last_start))
```

### Pattern 2: 設定変更 → 保存 → 無効化 → 再描画（既存定石の踏襲）
**What:** 件数変更・窓移動ハンドラは `_on_thumb_zoom_release`（viewer.py:146-154）と同じ流れにする。
**When to use:** 件数 Spinbox 変更時（保存必須）、窓移動時（保存不要だが再描画必須）。
**Example:**
```python
# Source: viewer.py:146-154 _on_thumb_zoom_release [VERIFIED: codebase]
def _on_page_size_change(self):
    new_size = self.page_size_var.get()        # 10..100 にクランプ済み前提
    self.settings["thumb_page_size"] = new_size
    self._page_size = new_size
    from pagefolio.settings import _save_settings
    _save_settings(self.settings)
    # 件数変更で現窓が無効になりうる → current_page を含む窓へ寄せる（D-11）
    self._page_window_start = window_for_page(self.current_page, new_size)
    self._invalidate_thumb_cache()             # 窓が変わると描画対象が変わる
    self._refresh_all()
```

### Pattern 3: D&D ドロップの local→global 換算（D-06）
**What:** `_dnd_dest_index` が返すフレーム位置（窓化でローカル）と `_dnd_src_idx`（press 時に束縛する `idx`）を全ページ index へ揃えてから既存ロジックへ渡す。
**When to use:** `_dnd_drop`。
**重要な設計選択（CONTEXT が許す裁量）:** `_add_thumb_placeholder` のクロージャ `idx=i` を**全ページ index のまま束縛**すれば（`for i in range(lo, hi)` の `i` が全ページ index）、`_dnd_src_idx` は最初から全ページ index になり src 側の変換は不要。dest 側だけ `to_global(local_dest, window_start)` を掛ければよい。これが整合の取りやすい構成。
```python
# Source: dnd.py:94-135 を窓化対応 [VERIFIED: codebase]
def _dnd_drop(self, event):
    src = self._dnd_src_idx                       # = 全ページ index（束縛を global に保つ）
    local_dest = self._dnd_dest_index(event)      # フレーム位置 = ローカル
    if local_dest is None or src is None:
        return
    lo, hi = window_bounds(self._page_window_start, self._page_size, len(self.doc))
    dest = to_global(local_dest, lo)              # D-06: global = local + window_start
    # 窓末尾ドロップ（local_dest == 窓内フレーム数）は hi に対応 → 窓末ページの直後
    dest = max(0, min(dest, len(self.doc)))
    # 以降は既存ロジック（bulk_move / move_page）をそのまま。selected_pages は全ページ index（D-07）なので bulk_move は無改修で正しい
```

### Anti-Patterns to Avoid
- **`+ window_start` を複数箇所に直書き:** 変換を散在させると窓またぎバグの温床。必ず純関数 1 箇所経由（CONTEXT integration point の明示要求）。
- **`selected_pages` をローカル index 化する:** D-07 に反する。`selected_pages` は**常に全ページ 0 始まり index の set**という不変条件を絶対に崩さない（page_ops.py が sorted して使う前提・CONTEXT code_context）。
- **`_thumb_gen` 世代ガードを外す/別管理にする:** 窓化しても世代ガードの枠組みはそのまま使う。描画対象を窓範囲に絞るだけ（CONTEXT established patterns）。
- **件数 Spinbox の値を未クランプで使う:** 10〜100 外の値（手入力・空文字）が settings に入ると次回起動で破綻。読み出し時もクランプする。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 複数選択の bulk move 並べ替え | 窓ローカルでの new_order 再計算 | 既存 `bulk_move`（dnd.py:101-117） | `selected_pages` を全ページ index に保てば既存ロジックが無改修で正しい（D-07） |
| 設定の保存/復元 | 独自 JSON 書き込み | `_save_settings()` + `DEFAULT_SETTINGS` の `setdefault` | 機密キーガード・既定値マージが既に実装済み（settings.py:43-76） |
| サムネイル逐次描画の競合制御 | 新しい cancel フラグ | 既存 `_thumb_gen` 世代カウンタ＋`root.after` チェーン | 既に正しく動作。窓化で描画件数が減るのみ |
| ページ操作（回転/削除/移動）の index 適用 | 窓内 index での操作 | 既存 page_ops（`selected_pages` を sorted） | 全ページ index 前提で既に正しい |

**Key insight:** 本フェーズの「新規ロジック」は **index 変換と窓計算だけ**。ページ操作・選択ロジック・描画競合制御・永続化は既存資産が全ページ index 前提で既に正しいので、`selected_pages` の不変条件（全ページ index）を保つ限り再利用できる。新規に書くべきは「窓→描画範囲」「local↔global 変換」の薄い層に限定する。

## Runtime State Inventory

> 本フェーズはローカル UI 改修であり、永続データのキー名やサービス設定の rename を伴わない。新規の永続化キー追加（表示件数）はあるが既存値の移行は不要。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `pagefolio_settings.json` に新規キー（例 `thumb_page_size`）を**追加**。既存キーの rename・移行はなし | `DEFAULT_SETTINGS` に既定 20 を追加。読み出しは `self.settings.get(key, 20)` で旧設定ファイルとも後方互換（既存キー欠落時は既定で補完される `setdefault` 機構あり・settings.py:71-72） |
| Live service config | None — 外部サービス・ネットワーク無関係（ローカル UI） | none |
| OS-registered state | None — Task Scheduler 等への登録なし | none |
| Secrets/env vars | None — API キー・機密無関係。`_SENSITIVE_KEYS` ガードに新規キーは無関係（数値設定） | none |
| Build artifacts | None — パッケージ名・エントリポイント変更なし | none |

**永続化の後方互換:** 旧 `pagefolio_settings.json`（件数キーなし）でも `_load_settings` の `setdefault` で既定 20 が補完されるため、既存ユーザーは無設定で 20 件表示になる。移行コード不要。

## Common Pitfalls

### Pitfall 1: `_refresh_thumbs_selection_only` の enumerate が全ページ index 前提のまま残る
**What goes wrong:** 窓化後も `for i, frame in enumerate(frames)` の `i`（ローカル位置）を `selected_pages`（全ページ index）と直接照合すると、窓 2 以降で選択ハイライトが全ページずれる。
**Why it happens:** 現状コードは「フレーム位置 = 全ページ index」前提（viewer.py:177-179）。
**How to avoid:** `is_sel = to_global(i, self._page_window_start) in self.selected_pages` のように `enumerate` 位置を global へ変換してから照合（CONTEXT canonical_refs が明示）。`is_cur` も同様に `to_global(i, start) == self.current_page`。
**Warning signs:** 窓 2 以降で選択枠が 1 つ上/下にずれる、別ページが選択表示される。

### Pitfall 2: `thumb_cache` のキーと窓切替時の扱い
**What goes wrong:** `thumb_cache` は `{全ページ index: PhotoImage}`（viewer.py:133-144、`_get_thumb_photo(i)` の `i` は全ページ index）。窓切替で**キャッシュをクリアする必要はない**（キーが全ページ index なので別窓のキャッシュは衝突しない）。誤って窓移動のたびに `_invalidate_thumb_cache()` 全クリアすると、窓を往復するたびに再レンダリングが走り「高速化」という目的に反する。
**Why it happens:** ズーム変更ハンドラ（`_on_thumb_zoom_release`）が全クリアするため、それを窓移動にもコピーしがち。
**How to avoid:** **窓移動では `thumb_cache` をクリアしない**（再描画 `_build_thumbnails` のみ）。クリアが必要なのは「ズーム変更」「件数変更でサイズ感が変わるわけではない（件数はキャッシュ無関係）」… 実際は件数変更でもキャッシュ無効化は不要（画像内容は同じ）。`_invalidate_thumb_cache` は**ズーム変更とページ内容変更（削除/回転/移動）時のみ**。
**Warning signs:** 窓を往復するとサムネイルが毎回ちらつく/遅い。

### Pitfall 3: `ttk.Spinbox` / `tk.Spinbox` の readonly 挙動と即時反映
**What goes wrong:** `tk.Spinbox` は `state="readonly"` にしてもスピンボタン（▲▼）でのインクリメントは効き続け、かつ暗テーマでの readonly 背景色が `readonlybackground` 等の別オプション指定になり扱いづらい（MEMORY: tkinter-readonly-widget-gotchas）。手入力を許すと範囲外（1, 999, 空文字）が入りうる。
**Why it happens:** Tkinter の Spinbox は手入力と矢印操作が別経路。
**How to avoid:**
- `ttk.Spinbox(from_=10, to=100, increment=10)` を使い、`state="readonly"`（手入力禁止・矢印のみ）にすると範囲外値が原理的に入らない。即時反映は `command=...` または `<<Increment>>`/`<<Decrement>>` で拾う。
- 手入力を許す設計にするなら、読み出し時に必ず `max(10, min(100, value))` でクランプし、空文字/非数値は `try/except ValueError` で既定 20 にフォールバック（裸 except 禁止 — `except (ValueError, tk.TclError)`）。
- 値の読み出しは `IntVar` を介する（`var.get()` が空文字時に `TclError` を投げうる点に注意）。
**Warning signs:** 件数に 1 や巨大値が入り窓計算が崩れる、空欄で `TclError`。

### Pitfall 4: 窓末尾への D&D ドロップ位置の換算
**What goes wrong:** `_dnd_dest_index` は窓末尾より下にドロップすると `len(frames)`（窓内フレーム数 = ローカル位置 size）を返す。これを `to_global` すると `window_start + size` になり、最終窓やドキュメント末尾で `len(self.doc)` を超えうる。
**Why it happens:** 「末尾挿入」を表すローカル位置が窓フレーム数と一致するため。
**How to avoid:** `dest = max(0, min(to_global(local_dest, start), len(self.doc)))` で全ページ範囲にクランプ（既存 `_dnd_drop` も `dest = max(0, min(dest, n))` でクランプ済み・dnd.py:100。変換後に同じクランプを適用）。
**Warning signs:** 窓内最後尾へのドロップで IndexError や意図しない位置への移動。

### Pitfall 5: 削除/移動で窓が空・最終窓が縮む・current が窓外
**What goes wrong:** 最終窓のページを全削除すると `window_start` が存在しないページ範囲を指す。件数変更で `current_page` が別窓に入る。
**Why it happens:** 操作後に窓状態を再評価していない。
**How to avoid:** ページ数や current が変わる操作（削除・移動・件数変更・前/次ページ）の直後に必ず `self._page_window_start = clamp_window_start(...)` → さらに D-11 として `window_for_page(self.current_page, size)` で current を含む窓へ寄せる。`_refresh_all` 内で集約するのが安全（描画の直前に窓を正規化）。
**Warning signs:** 空のサムネイルパネル、「41–47 / 全40」のような不整合ラベル。

## Code Examples

### 範囲ラベルの生成（D-09/D-10、1始まり表示・端数）
```python
# Source: viewer.py の page_label パターン（"{i+1} / {n}"）に倣う [VERIFIED: codebase]
def window_label(window_start, page_size, n_pages):
    lo, hi = window_bounds(window_start, page_size, n_pages)
    if n_pages == 0:
        return "- / -"
    # lo, hi は 0始まり半開区間 [lo, hi) → 表示は 1始まり lo+1 .. hi
    return f"{lo + 1}–{hi} / 全{n_pages}"   # 例 "41–47 / 全47"
# 文言・区切り記号は LANG(ja/en 同一キー)規約に従い実装裁量（D-01 discretion）
```

### 前/次窓ボタンの enable/disable（D-09 単一窓でも表示・無効化）
```python
# Source: _refresh_all の prev/next 状態制御パターン（viewer.py:166-172）に倣う [VERIFIED: codebase]
def window_nav_state(window_start, page_size, n_pages):
    """(prev_enabled, next_enabled) を返す。"""
    lo, hi = window_bounds(window_start, page_size, n_pages)
    prev_enabled = lo > 0
    next_enabled = hi < n_pages
    return (prev_enabled, next_enabled)
# 単一窓（n<=size）は両方 False → ボタン disabled だがラベル/行は常に表示（D-09）
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_build_thumbnails` が `range(len(self.doc))` で全描画 | 窓範囲 `range(lo, hi)` のみ描画 | 本フェーズ | 大量ページで描画件数が page_size に上限。高速化＝目的 |
| 「フレーム位置 = 全ページ index」暗黙前提 | 明示的な `local↔global` 変換層 | 本フェーズ | 窓またぎでも選択・D&D が整合 |

**Deprecated/outdated:** なし（既存 API の置換ではなく薄い変換層の追加）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 窓移動時に `thumb_cache` をクリアしないのが正しい（キーが全ページ index のため別窓と衝突しない） | Common Pitfalls 2 | 低 — もし描画不具合があれば窓移動時クリアに切替えれば安全側に倒れる（性能のみ低下）。実装時に窓往復で実機確認すれば確定 |
| A2 | `_add_thumb_placeholder` のクロージャ `idx` を全ページ index で束縛すれば src 変換が不要 | Architecture Pattern 3 | 低 — CONTEXT が「`i` を全ページ index のまま渡すか変換するか要設計」と裁量を明示。どちらでも整合可能。実装時にどちらか一方に統一すること |
| A3 | 件数 Spinbox を `ttk.Spinbox` + `state="readonly"` にするのが範囲外値混入を防ぐ最善策 | Common Pitfalls 3 | 低 — D-03/D-04 を満たす範囲での実装裁量。手入力許可＋クランプでも要件は満たせる |

**確認推奨:** A1・A2 は実装時に窓往復・窓またぎ D&D の実機操作で挙動確認すれば確定する（純ロジックテストに加えた手動確認項目）。

## Open Questions

1. **件数変更時に窓追従でどの窓を表示するか**
   - What we know: D-11 は「current_page を含む窓へ追従」。件数変更は current を含む窓へ寄せる（Pattern 2）。
   - What's unclear: 件数を増やした直後に「現在の窓の先頭ページ」を含む窓に寄せるか「current_page」を含む窓に寄せるか、微妙に表示位置が変わる。
   - Recommendation: D-11 に忠実に **current_page を含む窓**（`window_for_page(current_page, new_size)`）。これで「カレントを見失わない」意図に合致。

2. **Spinbox の即時反映タイミング（裁量 D-05）**
   - What we know: 「変更が永続化され再描画される」ことは必須。
   - What's unclear: 矢印 1 クリックごとに保存/再描画するか、フォーカスアウトでまとめるか。
   - Recommendation: `ttk.Spinbox` readonly + `command=` で矢印ごとに即反映。10 刻み・3 段階程度なので毎回再描画でも負荷は軽微。

## Environment Availability

> ローカル UI 改修。外部ツール・サービス・ネットワーク依存なし。既存実行環境（Python 3.8+ / Tkinter / fitz / Pillow）のみ。

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python tkinter | UI 全般 | ✓（既存） | 標準ライブラリ | — |
| PyMuPDF (fitz) | サムネイル描画・ページ数 | ✓（既存） | 1.27.2.2 | — |
| Pillow | 画像変換 | ✓（既存） | 12.2.0 | — |
| pytest | 検証 | ✓（既存） | 9.0.2 | — |

**Missing dependencies with no fallback:** なし
**Missing dependencies with fallback:** なし

## Validation Architecture

> nyquist_validation 有効（config.json `workflow.nyquist_validation: true`）。本フェーズの正しさは**ほぼ全て「ローカル↔グローバル変換と窓計算」という純ロジックの数学的正しさ**に帰着する。Tkinter ウィジェット描画そのものは検証対象外とし、純関数を `types.SimpleNamespace` スタブまたはモジュール関数として**ヘッドレスでテスト**する（既存 `tests/test_viewer.py` の `_make_stub` 方式が確立済み・本書はこれを踏襲）。

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2（+ pytest-cov 7.1.0） |
| Config file | `pyproject.toml`（`[tool.pytest.ini_options]` testpaths=["tests"]） |
| Quick run command | `pytest tests/test_pagination.py -x` |
| Full suite command | `pytest` |

### 検証対象の純ロジックヘルパー（Tk 非依存・テスト可能形）
本フェーズで切り出すべき純関数（Architecture Patterns 参照）。**全て引数→戻り値、状態非依存、Tkinter 非依存**。

| 関数 | シグネチャ（案） | 不変条件 |
|------|------------------|----------|
| `window_bounds` | `(window_start, page_size, n_pages) -> (lo, hi)` | `0 <= lo <= hi <= n_pages`、`hi - lo <= page_size`、`n==0 → (0,0)` |
| `to_global` | `(local_pos, window_start) -> int` | `to_global(to_local(g, s), s) == g` |
| `to_local` | `(global_idx, window_start) -> int` | 上記逆変換 |
| `window_for_page` | `(page_idx, page_size) -> start` | `start <= page_idx < start + page_size`、`start % page_size == 0` |
| `clamp_window_start` | `(window_start, page_size, n_pages) -> start` | 戻り値は必ず有効窓の先頭（`< n_pages`、`% page_size == 0`） |
| `window_label` | `(window_start, page_size, n_pages) -> str` | 1始まり `lo+1`、端数最終窓は `hi == n_pages`（D-10） |
| `window_nav_state` | `(window_start, page_size, n_pages) -> (prev, next)` | 単一窓は `(False, False)`（D-09） |

### Phase 要件 → テストマップ
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V16-UI-03（SC1） | 件数で窓に区切る・最終窓端数（D-10） | unit | `pytest tests/test_pagination.py::TestWindowBounds -x` | ❌ Wave 0 |
| V16-UI-03（SC2） | 件数が settings に永続化・復元、範囲外クランプ | unit | `pytest tests/test_pagination.py::TestPageSizePersist -x` | ❌ Wave 0 |
| V16-UI-03（SC3） | D&D ドロップ local→global 換算が正しい全ページ位置（D-06） | unit | `pytest tests/test_pagination.py::TestDndIndexConvert -x` | ❌ Wave 0 |
| V16-UI-03（SC4） | 窓またぎで selected_pages が全ページ index を保持（D-07） | unit | `pytest tests/test_pagination.py::TestSelectionAcrossWindows -x` | ❌ Wave 0 |
| D-11 | current_page 窓追従（操作後に current を含む窓） | unit | `pytest tests/test_pagination.py::TestWindowFollow -x` | ❌ Wave 0 |
| D-09 | 単一窓でもナビ表示・前/次 disabled | unit | `pytest tests/test_pagination.py::TestNavState -x` | ❌ Wave 0 |

### 検証すべき不変条件・境界値・プロパティ（具体列挙）

**変換の往復不変条件（プロパティ）:**
- 任意の `g`（0..n-1）と窓 start に対し `to_global(to_local(g, start), start) == g`。
- 窓内の任意ローカル `l`（0..size-1）に対し `to_local(to_global(l, start), start) == l`。

**`window_bounds` 境界値:**
- 件数 = 全ページ数ちょうど（例 size=20, n=20）→ 単一窓 `(0, 20)`、次窓なし。
- 件数 > 全ページ数（例 size=50, n=20）→ `(0, 20)`、単一窓。
- 1 ページ PDF（n=1, size=20）→ `(0, 1)`、ラベル「1–1 / 全1」、ナビ両 disabled。
- 端数最終窓（size=20, n=47, window_start=40）→ `(40, 47)`、ラベル「41–47 / 全47」。
- ちょうど割り切れる最終窓（size=20, n=40, window_start=20）→ `(20, 40)`、次窓なし。
- n=0（doc 未オープン）→ `(0, 0)`、ラベル「- / -」、ナビ両 disabled。

**`window_for_page`（D-11 追従）:**
- `window_for_page(0, 20) == 0`、`window_for_page(19, 20) == 0`、`window_for_page(20, 20) == 20`、`window_for_page(46, 20) == 40`。
- 件数変更で current が別窓に入る: size 20→10、current=25 のとき新 start = `window_for_page(25, 10) == 20`。

**`clamp_window_start`（削除/件数変更後の正規化）:**
- 削除で最終窓が縮む: size=20, n が 47→40 に減り window_start=40 → clamp で `((40-1)//20)*20 == 20`。窓 2（20–40）へ寄る。
- 削除で窓が空になる: size=20, n が 25→20 に減り window_start=20 → clamp で `((20-1)//20)*20 == 0`。窓 1 へ。
- size 変更でオフセットが窓境界からずれる: window_start=15, size=10 → clamp 後 start は有効窓先頭（実装が `% page_size` を保証する場合）。**注意:** `clamp_window_start` 単体は範囲クランプのみ。境界整列は `window_for_page(current_page, size)` 側で担保するため、両者の役割分担をテストで固定する。

**D&D 換算（SC3・D-06）:**
- window_start=20, local_dest=3 → global_dest=23。
- 窓末尾ドロップ（local_dest = 窓内フレーム数）→ `min(to_global(...), len(doc))` でクランプされ doc 範囲内。
- src は全ページ index で束縛（Pattern 3 / A2）→ `bulk_move` が `selected_pages`（全ページ index）でそのまま正しい new_order を組むことを、窓 2 表示中・複数選択（窓 1 と窓 2 にまたがる選択）で検証。

**選択の窓またぎ保持（SC4・D-07）:**
- `selected_pages = {3, 25}`（窓 1 と窓 2 の両方）。窓 2（start=20, size=20）表示中、`_refresh_thumbs_selection_only` 相当の照合で local 5（=global 25）がハイライト対象、local の他は非ハイライト。`selected_pages` の中身は操作前後で全ページ index のまま不変。
- 全選択 `_select_all` → `selected_pages == set(range(n))`（窓に依存しない・D-08）。窓を移動しても集合は不変。

**`window_nav_state`（D-09）:**
- 単一窓（n<=size）→ `(False, False)`、ただしラベル行は描画される（描画はウィジェットテスト外だが、状態関数が両 False を返すことを単体検証）。
- 中間窓 → `(True, True)`、先頭窓 → `(False, True)`、最終窓 → `(True, False)`。

**永続化（SC2）:**
- `DEFAULT_SETTINGS` に件数キーが存在し既定が 20。旧設定ファイル（キー無）を `_load_settings` 相当で読むと 20 が補完される（後方互換）。
- 範囲外値（5 / 200 / 空文字）の読み出しクランプが 10..100 に収まる。これは settings 読み出しヘルパー（クランプ関数）を 1 つ設けて単体テストするのが確実。

### Sampling Rate
- **Per task commit:** `pytest tests/test_pagination.py -x`（純ロジックは高速・全数即時）
- **Per wave merge:** `pytest`（全スイート — 既存 test_viewer / test_pdf_ops との回帰確認）
- **Phase gate:** `pytest` 全緑 ＋ `ruff check . && ruff format .` 通過後に `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_pagination.py` — 上記 7 テストクラス（窓計算・変換・追従・クランプ・D&D換算・選択保持・ナビ状態）。covers V16-UI-03 / D-06〜D-11。
- [ ] 純ロジックヘルパーの配置確定（`pagefolio/pagination.py` モジュール関数 推奨、または viewer.py の `@staticmethod`）— テストの import 先が決まる。
- [ ] （任意）件数クランプ読み出しヘルパー（10..100 + 既定 20 フォールバック）を settings.py か pagination.py に追加 → SC2 のクランプテスト対象。
- フレームワーク install は不要（pytest 既存）。既存フィクスチャ（`sample_pdf_doc` 3ページ）は小さいため、窓化テスト用に **多ページ doc を生成する新フィクスチャ**（例 47 ページ）を conftest に追加すると境界値テストが書きやすい（任意・裁量）。

## Security Domain

> `security_enforcement: true` / `security_asvs_level: 1`。ただし本フェーズは**ローカル UI のページネーション表示のみ**で、認証・セッション・ネットワーク送信・外部入力・暗号・機密の取り扱いを**一切含まない**。攻撃面は実質的に存在しない。

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 認証要素なし |
| V3 Session Management | no | セッションなし |
| V4 Access Control | no | アクセス制御対象なし |
| V5 Input Validation | yes（限定的） | 件数 Spinbox の値域クランプ（10..100）と空文字/非数値の `except (ValueError, tk.TclError)` フォールバック。範囲外値が settings に永続化されないこと。これは堅牢性であってセキュリティ脅威ではないが、入力検証として記録 |
| V6 Cryptography | no | 暗号操作なし |

### Known Threat Patterns for {Tkinter ローカル UI}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 件数の範囲外/不正値で窓計算が破綻（DoS 的な自己障害） | Denial of Service（ローカル・自己起因） | 読み出し時クランプ + 例外フォールバック既定 20。`_save_settings` の機密キーガードは数値設定に無関係 |
| API キー等の機密混入 | Information Disclosure | 本フェーズで追加するのは数値設定のみ。`_SENSITIVE_KEYS` ガード（settings.py:81-84）は既存。新規キーは機密に該当しない |

**結論:** セキュリティ上の新規脅威なし。入力検証（件数クランプ）のみ堅牢性として実装・テストする。

## Sources

### Primary (HIGH confidence)
- `pagefolio/viewer.py`（実地読込）— `_build_thumbnails`(197-225) / `_add_thumb_placeholder`(227-287) / `_refresh_thumbs_selection_only`(174-195) / `_render_preview_pixmap`(40-49 = 純ロジック作法の手本) / `_on_thumb_zoom_release`(146-154 = 保存→無効化→再描画定石)
- `pagefolio/dnd.py`（実地読込）— `_dnd_dest_index`(73-92) / `_dnd_drop`(94-135 = bulk_move/move_page ロジック) / `_dnd_show_indicator`(47-66)
- `pagefolio/ui_builder.py`（実地読込）— `_build_thumb_panel`(173-239 = フッター追加先の pack 構造)
- `pagefolio/settings.py`（実地読込）— `_load_settings` defaults(45-76) / `_save_settings` 機密ガード(79-84)
- `tests/test_viewer.py` / `tests/conftest.py`（実地読込）— 純ロジック + SimpleNamespace スタブ検証の確立パターン、フィクスチャ
- `.planning/phases/02-pagination/02-CONTEXT.md` — D-01〜D-11 確定事項・canonical_refs・integration points
- `.planning/REQUIREMENTS.md` — V16-UI-03 本文
- `.planning/config.json` — nyquist_validation/security 設定

### Secondary (MEDIUM confidence)
- Python ttk.Spinbox の `state="readonly"` 挙動（標準ライブラリ知識・docs.python.org tkinter.ttk）

### Tertiary (LOW confidence)
- なし

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 新規依存なし、既存固定バージョンを実地確認
- Architecture: HIGH — CONTEXT の integration points と実コードの暗黙前提（enumerate/クロージャ束縛）を突き合わせて変換層を導出
- Pitfalls: HIGH — 実コードの該当行から具体的に特定（選択 enumerate、thumb_cache キー、D&D 末尾クランプ）
- Validation: HIGH — 既存 test_viewer.py の純ロジック検証作法が直接適用可能

**Research date:** 2026-06-18
**Valid until:** 2026-07-18（安定・ローカルコードベース。外部変化要因なし）
