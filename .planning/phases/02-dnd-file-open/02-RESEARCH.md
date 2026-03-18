# Phase 02: D&D ファイルオープン - Research

**Researched:** 2026-03-18
**Domain:** Tkinter drag-and-drop from OS file manager (Windows), tkinterdnd2, visual feedback on Canvas
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ドロップ対象領域**
- プレビュー領域（preview_canvas）のみがドロップターゲット（ファイル未オープン時も同じ）
- プレビュー領域以外（サムネイル・ツール）へのドロップは無視
- ドラッグ中にプレビュー領域上にいるかどうかでフィードバックを切り替える

**ファイルオープン時の挙動**
- 既にファイルを開いている状態で1ファイルをドロップ → 現在のファイルを閉じて新しいファイルを開く（未保存なら確認ダイアログ）
- 複数ファイルドロップ → 既存の MergeOrderDialog を再利用して結合順を確認

**ビジュアルフィードバック**
- ドラッグ中（プレビュー領域上）: 背景色変更 + 「ここにPDFをドロップ」テキスト表示
- ドラッグ中（プレビュー領域外）: フィードバックなし
- ドロップ後: ステータスバーに「XXX.pdf を開きました」と表示（既存の _set_status を流用）

**複数ファイルの挙動**
- 複数 PDF ドロップ → MergeOrderDialog で結合順を確認してから結合
- PDF と非 PDF が混在 → PDF のみ抽出して処理、非 PDF は無視

**PDF以外のファイル**
- PDF 以外のファイルを1つだけドロップ → ステータスバーにエラー表示（「PDFファイルのみ対応しています」）
- ダイアログは出さない（うるさくならないように）

### Claude's Discretion

- windnd のフック先（root 全体のまま vs preview_canvas のみ）の技術的判断
- ドラッグ中フィードバックの具体的な背景色（テーマカラーから選択）
- フィードバック表示のタイミングとアニメーション
- 未保存確認ダイアログの実装方法（既存の確認フローがあればそれを流用）

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DND-01 | プレビュー領域に PDF をドロップしてファイルを開ける | tkinterdnd2 の `<<Drop>>` イベントと `_open_pdf_path()` の接続パターンを確立 |
| DND-02 | 複数 PDF を同時ドロップすると結合ダイアログが表示される | `widget.tk.splitlist(event.data)` で複数ファイルを分割、既存 MergeOrderDialog へ渡す |
| DND-03 | ドロップ対象エリアにファイルをドラッグするとビジュアルフィードバックが表示される | `<<DropEnter>>` / `<<DropLeave>>` イベントで preview_canvas の背景色とテキストを切り替える |
</phase_requirements>

---

## Summary

本フェーズの中核課題は **Windows エクスプローラーからのファイル D&D を Tkinter Canvas 上の特定ウィジェットに限定して受け取る**こと。現在のコードは `windnd` ライブラリを使いアプリ全体（root）にフックしているが、STATE.md に記録された決定事項「tkinterdnd2 を windnd の代わりに採用」に従い、tkinterdnd2 へ移行する必要がある。

tkinterdnd2 は `preview_canvas.drop_target_register(DND_FILES)` で特定ウィジェットをドロップターゲットに指定できる。さらに `<<DropEnter>>` / `<<DropLeave>>` イベントを持ち、ドラッグ中の視覚フィードバック（DND-03）も実現可能。windnd にはこの per-widget・ enter/leave 機構がない。

最大の統合上の注意点は、tkinterdnd2 が `tk.Tk()` ではなく `TkinterDnD.Tk()` を root として要求すること。既存の `if __name__ == "__main__":` ブロックの1行変更が必須。また、複数ファイルのパスは `event.data` に単一文字列として渡されるため、`widget.tk.splitlist(event.data)` で分割する必要がある（スペース入りパスの正確な処理に必須）。

**Primary recommendation:** tkinterdnd2 0.4.3 を採用し、`preview_canvas` 単体をドロップターゲットに設定する。`<<DropEnter>>` / `<<DropLeave>>` / `<<Drop>>` の3イベントで全要件を満たせる。

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tkinterdnd2 | 0.4.3 | OS→Tkinter ファイル D&D、per-widget ターゲット登録 | STATE.md 決定事項。PyInstaller フック同梱で Phase 4 配布対応が容易。DropEnter/Leave 対応 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | 12.1.1 (installed) | Canvas への画像描画（既存） | D&D フィードバックアイコン表示が必要な場合 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tkinterdnd2 | windnd 1.0.7 | windnd は per-widget 登録・DropEnter/Leave 非対応。DND-03 を windnd で実現するには座標ポーリングが必要で複雑度が上がる。PyInstaller フック不要な点は有利だが Phase 4 配布要件と整合しない |
| tkinterdnd2 | windnd + wm_dropfiles | 座標判定でプレビュー領域外を無視する実装も可能だが、DropEnter/Leave が使えないためフィードバック制御が不確実 |

**Installation:**

```bash
pip install tkinterdnd2==0.4.3
```

**Version verification (実施済み):**

```
tkinterdnd2: 0.4.3 (2025-02-28 リリース — 最新)
windnd: 1.0.7 (参照のみ、採用しない)
```

---

## Architecture Patterns

### Recommended Project Structure

既存の単一ファイル構成（`pagefolio.py`）を維持。変更箇所は以下：

```
pagefolio.py
├── import セクション      # tkinterdnd2 の条件付き import を追加
├── _setup_file_drop()     # windnd → tkinterdnd2 に全面書き換え
│   ├── preview_canvas.drop_target_register(DND_FILES)
│   ├── dnd_bind('<<DropEnter>>', on_drag_enter)
│   ├── dnd_bind('<<DropLeave>>', on_drag_leave)
│   └── dnd_bind('<<Drop>>', on_drop)
├── PDFEditorApp           # _on_dnd_enter / _on_dnd_leave / _on_dnd_drop を追加
└── if __name__ == "__main__":
    └── root = TkinterDnD.Tk()  # tk.Tk() から変更（必須）
```

### Pattern 1: tkinterdnd2 初期化（最重要）

**What:** `tk.Tk()` を `TkinterDnD.Tk()` に差し替える。TkDnD の Tcl 拡張が root 初期化時にロードされる。
**When to use:** tkinterdnd2 を使う場合は必須。忘れると `widget.drop_target_register()` 呼び出し時に `AttributeError` が発生する。

```python
# Source: https://github.com/Eliav2/tkinterdnd2
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

# if __name__ == "__main__": ブロック
if _HAS_DND:
    root = TkinterDnD.Tk()
else:
    root = tk.Tk()
```

### Pattern 2: per-widget ドロップターゲット登録

**What:** 特定 Canvas ウィジェットのみをドロップターゲットとして登録する。
**When to use:** プレビュー Canvas のみに D&D を受け付けさせたい場合。

```python
# Source: https://github.com/pmgagne/tkinterdnd2/blob/master/demos/demo_files_and_text.py
def _setup_file_drop(app):
    if not _HAS_DND:
        return
    canvas = app.preview_canvas
    canvas.drop_target_register(DND_FILES)
    canvas.dnd_bind('<<DropEnter>>', app._on_dnd_enter)
    canvas.dnd_bind('<<DropLeave>>', app._on_dnd_leave)
    canvas.dnd_bind('<<Drop>>', app._on_dnd_drop)
```

### Pattern 3: DropEnter / DropLeave によるビジュアルフィードバック

**What:** ドラッグがウィジェット境界に入った/出た瞬間にコールバックが呼ばれる。
**When to use:** DND-03 要件のフィードバック表示制御。

```python
def _on_dnd_enter(self, event):
    """ドラッグがプレビュー領域に入ったとき"""
    self.preview_canvas.configure(bg=C["ACCENT"])  # テーマカラーでハイライト
    # Canvas 中央に「ここにPDFをドロップ」テキスト
    self._dnd_text_id = self.preview_canvas.create_text(
        self.preview_canvas.winfo_width() // 2,
        self.preview_canvas.winfo_height() // 2,
        text="ここにPDFをドロップ",
        fill=C["TEXT_MAIN"],
        font=self._font(4, "bold"),
        tags="dnd_hint"
    )
    return event.action  # 必須: Tcl に action を返す

def _on_dnd_leave(self, event):
    """ドラッグがプレビュー領域から出たとき"""
    self.preview_canvas.configure(bg=C["PREVIEW_BG"])
    self.preview_canvas.delete("dnd_hint")
    return event.action
```

### Pattern 4: Drop イベントとファイルリスト解析

**What:** `event.data` は複数ファイルが1つの文字列で渡される（スペース区切り、ブレース囲み）。`splitlist()` で正確に分割する。
**When to use:** 全 Drop ハンドラで必須。スペース入りパスが含まれる場合に特に重要。

```python
def _on_dnd_drop(self, event):
    """ファイルがドロップされたとき"""
    # フィードバックをリセット
    self.preview_canvas.configure(bg=C["PREVIEW_BG"])
    self.preview_canvas.delete("dnd_hint")

    # ファイルリスト解析（splitlist 必須）
    raw_paths = self.preview_canvas.tk.splitlist(event.data)
    pdf_paths = [p for p in raw_paths if p.lower().endswith('.pdf')]

    if not pdf_paths and raw_paths:
        self._set_status("PDFファイルのみ対応しています")
        return event.action

    if len(pdf_paths) == 1:
        # 1ファイル: 未保存確認 → 開く
        self._open_pdf_with_unsaved_check(pdf_paths[0])
    else:
        # 複数ファイル: MergeOrderDialog へ
        MergeOrderDialog(self.root, pdf_paths, self._do_open_merged)

    return event.action  # 必須
```

### Pattern 5: 未保存確認フロー

**What:** 既存の `_quit()` と同じパターンで `self.doc` 存在チェック → askyesno 確認。
**When to use:** 1ファイルドロップで既存ドキュメントを差し替える前。

```python
def _open_pdf_with_unsaved_check(self, path):
    if self.doc:
        if not messagebox.askyesno(
            self._t("confirm_title"),
            self._t("quit_confirm")  # 既存文字列キーを流用、または専用キーを追加
        ):
            return
        self.doc.close()
        self.doc = None
    self._open_pdf_path(path)
```

### Anti-Patterns to Avoid

- **`tk.Tk()` のまま `drop_target_register()` を呼ぶ**: `AttributeError` になる。`TkinterDnD.Tk()` が必須。
- **`event.data.split()` や `event.data.split('{')` でパスを分割する**: スペース入りパスが壊れる。`widget.tk.splitlist(event.data)` を使う。
- **`event.action` を返さない**: `<<DropEnter>>` / `<<DropLeave>>` / `<<Drop>>` ハンドラは必ず `return event.action` で終わる必要がある（Tcl/Tk との通信）。
- **windnd の `hook_dropfiles(root, ...)` をそのまま残す**: tkinterdnd2 と windnd の混在は不要で混乱を招く。`_setup_file_drop` を完全に書き換える。
- **`_on_dnd_leave` でフィードバック解除し忘れる**: ドロップ後に `preview_canvas` の bg がハイライトのまま残る。`_on_dnd_drop` の先頭でも解除する。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OS → Tkinter ファイル D&D | WinAPI `WM_DROPFILES` の P/Invoke | tkinterdnd2 | スペース入りパス、マルチバイトパス、UNC パスの処理が複雑 |
| ファイルパスのリスト解析 | `event.data.split()` 自前実装 | `widget.tk.splitlist()` | Tcl リスト形式（ブレース囲み）を正確に解析する標準メソッド |
| DropEnter/Leave 座標ポーリング | `after()` ループで mouse 座標と canvas 境界を比較 | tkinterdnd2 の `<<DropEnter>>` / `<<DropLeave>>` | ポーリングは CPU 負荷があり、境界判定にズレが生じる |

**Key insight:** `splitlist()` を使わない実装はスペース入りパス（例: `C:\Users\John Doe\Documents\doc.pdf`）で必ずバグる。

---

## Common Pitfalls

### Pitfall 1: root が `TkinterDnD.Tk()` でない

**What goes wrong:** `preview_canvas.drop_target_register(DND_FILES)` で `AttributeError: 'Canvas' object has no attribute 'drop_target_register'`
**Why it happens:** TkDnD Tcl 拡張は `TkinterDnD.Tk()` 初期化時に root に注入される。`tk.Tk()` を使うとウィジェットに D&D メソッドが生えない。
**How to avoid:** `if __name__ == "__main__":` の `root = tk.Tk()` を `root = TkinterDnD.Tk()` に変更する（1行）。
**Warning signs:** `AttributeError` / `drop_target_register` が見つからない系のエラー。

### Pitfall 2: `event.data` を `split()` で分割

**What goes wrong:** `C:\Users\John Doe\test.pdf` が `['C:\\Users\\John', 'Doe\\test.pdf']` に分割される。
**Why it happens:** tkinterdnd2 は複数ファイルを Tcl リスト形式（スペース区切り、スペース入りパスはブレース `{...}` で囲む）で渡す。
**How to avoid:** 必ず `widget.tk.splitlist(event.data)` を使う。
**Warning signs:** スペースのないパスでは動くがスペース入りパスでエラー/ファイルが見つからない。

### Pitfall 3: DropEnter フィードバックが Drop 後に残る

**What goes wrong:** ドロップ後もプレビュー Canvas がハイライト色のまま、「ここにPDFをドロップ」テキストが残る。
**Why it happens:** `<<DropLeave>>` は Drop 前には必ずしも発火しない（OS 依存）。`_on_dnd_drop` でも解除処理が必要。
**How to avoid:** `_on_dnd_drop` の先頭で `preview_canvas.configure(bg=C["PREVIEW_BG"])` と `preview_canvas.delete("dnd_hint")` を呼ぶ。
**Warning signs:** Drop 後に背景色が変わったまま残る。

### Pitfall 4: `return event.action` を忘れる

**What goes wrong:** DropEnter/Leave/Drop が正常に動作しない、または Tk エラーが発生する。
**Why it happens:** tkinterdnd2 イベントハンドラは Tcl 側に action 文字列を返す必要がある（`copy` / `move` / `link` / `ask` / `private` / `refuse_drop` など）。
**How to avoid:** ハンドラの最後を必ず `return event.action` にする。
**Warning signs:** D&D が途中でキャンセルされたように見える。

### Pitfall 5: windnd と tkinterdnd2 の混在

**What goes wrong:** 両ライブラリが同時にフックされ、Drop 時に処理が2回走る可能性。
**Why it happens:** 既存の `_setup_file_drop()` が windnd を使っており、tkinterdnd2 への移行時に削除し忘れた場合。
**How to avoid:** `_setup_file_drop()` を完全に tkinterdnd2 実装で置き換え、windnd の import・呼び出しを全て除去する。
**Warning signs:** Drop 時に処理が2回実行される、または競合エラー。

---

## Code Examples

Verified patterns from official sources:

### tkinterdnd2 完全セットアップ例

```python
# Source: https://github.com/pmgagne/tkinterdnd2/blob/master/demos/demo_files_and_text.py
# Source: https://github.com/Eliav2/tkinterdnd2

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _HAS_TKDND = True
except ImportError:
    _HAS_TKDND = False


def _setup_file_drop(app):
    """tkinterdnd2 による D&D。未インストール時はスキップ。"""
    if not _HAS_TKDND:
        return
    canvas = app.preview_canvas
    canvas.drop_target_register(DND_FILES)
    canvas.dnd_bind('<<DropEnter>>', app._on_dnd_enter)
    canvas.dnd_bind('<<DropLeave>>', app._on_dnd_leave)
    canvas.dnd_bind('<<Drop>>', app._on_dnd_drop)


# if __name__ == "__main__":
if _HAS_TKDND:
    root = TkinterDnD.Tk()
else:
    root = tk.Tk()
```

### ファイルリスト分割（スペース対応）

```python
# Source: https://github.com/pmgagne/tkinterdnd2/blob/master/demos/demo_files_and_text.py
def _on_dnd_drop(self, event):
    paths = self.preview_canvas.tk.splitlist(event.data)
    # paths は str のリスト（bytes ではない）
    pdf_paths = [p for p in paths if p.lower().endswith('.pdf')]
    ...
    return event.action
```

### DropEnter フィードバック（テーマカラー使用）

```python
def _on_dnd_enter(self, event):
    # テーマカラー: ACCENT はドラーク="#e94560", ライト="#d63050"
    self.preview_canvas.configure(bg=C["ACCENT"])
    cx = self.preview_canvas.winfo_width() // 2
    cy = self.preview_canvas.winfo_height() // 2
    self.preview_canvas.create_text(
        cx, cy,
        text=self._t("dnd_drop_hint"),  # "ここにPDFをドロップ" など
        fill=C["TEXT_MAIN"],
        font=self._font(4, "bold"),
        tags="dnd_hint"
    )
    return event.action
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| windnd（root 全体フック） | tkinterdnd2（per-widget ターゲット） | Phase 2（本フェーズ） | DropEnter/Leave で正確な領域判定が可能、PyInstaller 対応改善 |
| `event.data.split()` | `widget.tk.splitlist(event.data)` | tkinterdnd2 標準 | スペース入りパスが正確に処理される |

**Deprecated/outdated in this project:**
- `windnd.hook_dropfiles()`: 除去対象。tkinterdnd2 に完全移行。

---

## Open Questions

1. **未保存確認ダイアログの文字列キー**
   - What we know: `_quit()` が `self._t("quit_confirm")` を使っている。「アプリを終了しますか？」という意味の文字列。
   - What's unclear: D&D で別ファイルを開く場合は「現在のファイルを閉じて新しいファイルを開きますか？」という別メッセージが適切か、既存キーの流用で十分か。
   - Recommendation: 新しいローカライゼーションキー `"dnd_replace_confirm"` を追加する。既存の `quit_confirm` は「終了」の意味なので流用は不自然。

2. **`TkinterDnD.Tk()` と `_rebuild_ui()` の互換性**
   - What we know: `PDFEditorApp._rebuild_ui()` が設定変更時に `_build_ui()` を呼び直す。root は変更しない。
   - What's unclear: `TkinterDnD.Tk()` を root にした場合、`_setup_file_drop()` は `_rebuild_ui()` 後も再呼び出しが必要か（`preview_canvas` が再生成される可能性）。
   - Recommendation: `_setup_file_drop()` を `_rebuild_ui()` 完了後に再呼び出しするか、`preview_canvas` が再生成されるかどうかを実装時に確認する。

3. **tkinterdnd2 未インストール時のフォールバック**
   - What we know: 既存の windnd 実装も `try/except ImportError` でスキップしていた。
   - What's unclear: Phase 4（PyInstaller exe 化）でフォールバックが不要になるが、開発中に tkinterdnd2 なし環境での動作保証が必要か。
   - Recommendation: `_HAS_TKDND` フラグを使い、未インストール時はサイレントスキップ（起動は正常）とする。エラーログは出さない。

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | なし（テストインフラ未構築） |
| Config file | なし — Wave 0 で作成が必要 |
| Quick run command | `python -c "import ast; ast.parse(open('pagefolio.py').read())"` |
| Full suite command | 同上（現時点では構文チェックのみ） |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DND-01 | PDF ドロップで `_open_pdf_path()` が呼ばれる | 手動検証 | — | ❌ 手動のみ |
| DND-02 | 複数 PDF ドロップで MergeOrderDialog が開く | 手動検証 | — | ❌ 手動のみ |
| DND-03 | DropEnter でフィードバック表示、DropLeave/Drop で解除 | 手動検証 | — | ❌ 手動のみ |

> tkinterdnd2 の D&D イベントは OS レベルのマウス操作が必要なため、自動テストは困難。構文チェックと手動検証の組み合わせが現実的。

### Sampling Rate

- **Per task commit:** `python -c "import ast; ast.parse(open('pagefolio.py').read())" && echo "構文OK"`
- **Per wave merge:** 同上
- **Phase gate:** 構文チェック合格 + 手動 D&D 動作確認（PDF 1ファイル、複数ファイル、非 PDF、スペース入りパス）

### Wave 0 Gaps

- [ ] `tests/` ディレクトリ — 現フェーズでは作成不要（手動検証で代替）
- [x] 構文チェックコマンドは既存 CLAUDE.md に記載済み

---

## Sources

### Primary (HIGH confidence)

- PyPI tkinterdnd2 0.4.3 — バージョン確認 (https://pypi.org/project/tkinterdnd2/)
- GitHub pmgagne/tkinterdnd2 demos/demo_files_and_text.py — DropEnter/Leave/Drop パターン (https://github.com/pmgagne/tkinterdnd2/blob/master/demos/demo_files_and_text.py)
- GitHub pmgagne/tkinterdnd2 hook-tkinterdnd2.py — PyInstaller フック内容 (https://github.com/pmgagne/tkinterdnd2/blob/master/hook-tkinterdnd2.py)
- `pip index versions tkinterdnd2` — 最新バージョン 0.4.3 確認済み (2026-03-18 実施)

### Secondary (MEDIUM confidence)

- WebSearch: tkinterdnd2 + PyInstaller + Windows 2024/2025 — PyInstaller フックで DLL バンドル対応
- WebSearch: tkinterdnd2 DropEnter/DropLeave/Drop イベント名確認

### Tertiary (LOW confidence)

- なし

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — pip index で 0.4.3 確認、PyPI で 2025-02-28 リリース確認
- Architecture: HIGH — 公式 demo コードから直接導出
- Pitfalls: HIGH — splitlist/event.action/TkinterDnD.Tk() は tkinterdnd2 ドキュメント・ソースで確認済み

**Research date:** 2026-03-18
**Valid until:** 2026-09-18（tkinterdnd2 は安定ライブラリ、30日超で有効）
