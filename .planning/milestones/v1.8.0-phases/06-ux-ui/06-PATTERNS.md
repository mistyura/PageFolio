# Phase 6: 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合） - Pattern Map

**Mapped:** 2026-07-16
**Files analyzed:** 11（新規1・改修10）
**Analogs found:** 10 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `pagefolio/toast.py`（新規） | component（Tk 常駐オーバーレイ） | event-driven（表示/dismiss/再試行コールバック） | `pagefolio/dialogs/llm_config/dialog.py`（テーマ/フォント規約の踏襲元） | role-match（同一パターンの新規モジュールなし） |
| `pagefolio/file_ops.py`（`_save_file`/`_save_as`/`_save_compressed` 改修） | service（Mixin） | request-response（同期保存 + 失敗時再試行） | 同ファイル内 `_save_as`/`_save_compressed`（相互に前例） | exact（3メソッドが相互に同型） |
| `pagefolio/file_ops.py`（`_restore_state` の `insert_redo` ブロック修正） | service（Undo/Redo エンジン） | CRUD（デルタ復元） | 同ファイル内 `delete_redo` ブロック（348-358行目） | exact（対称 op として直接倣う） |
| `pagefolio/print_ops.py`（`_print_pdf`/`_send_to_printer` 改修） | service（Mixin） | request-response（同期印刷 + 失敗時再試行） | `pagefolio/file_ops.py` の保存系（同時改修の姉妹パターン） | role-match |
| `pagefolio/ui_builder.py`（`_build_ui()`/`_rebuild_ui()` へ ToastManager 再生成組込） | component（メインウィンドウ構築） | event-driven | 同ファイル内 `_build_menubar()` の `_rebuild_ui()` 再呼び出しパターン（app.py 295-303行目コメント参照の同型問題） | exact |
| `pagefolio/dialogs/plugin.py`（Canvas ホイールバインド追加） | component（ダイアログ） | request-response | `pagefolio/dialogs/llm_config/dialog.py`（`_build_scrollable_area`, 101-156行目） | exact（統一基準そのもの） |
| `pagefolio/ocr_dialog.py`（`_center()` の高さクランプ追加） | component（ダイアログ） | request-response | `pagefolio/dialogs/llm_config/dialog.py`（`_compute_dialog_height`, 159行目〜） | exact |
| `pagefolio/dialogs/about.py`（42行目フォントハードコード是正） | component（ダイアログ） | request-response | 同ファイル内 49行目 `self._font(0)`（他ラベルが既に正しい規約準拠） | exact |
| `tests/test_toast.py`（新規） | test | event-driven | `tests/test_pdf_ops.py`（既存 Undo/Redo テストのスタブパターン） | role-match |
| `tests/test_font_hardcode_guard.py`（新規） | test | batch（ソーススキャン） | `tests/test_source_keyguard.py` | exact |
| `tests/test_pdf_ops.py`（`TestInsertUndoRedo` へ4手往復メソッド追加） | test | CRUD | `tests/test_undo_stress.py::TestBlobLeakDetection::test_double_release_chain_delete_undo_redo_undo`（同型4手パターンの delete 版） | exact |

## Pattern Assignments

### `pagefolio/toast.py`（新規, component, event-driven）

**Analog:** `pagefolio/dialogs/llm_config/dialog.py`（テーマ/フォント規約参照。構造自体に直接の analog なし＝Phase内新設）

**配置オーバーレイパターン（D-05/D-06）:**
```python
# self.root 直下に place() で右下常駐配置
toast_frame = tk.Frame(self.root, bg=C["BG_CARD"], bd=1, relief="solid")
toast_frame.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)
tk.Label(
    toast_frame, textvariable=msg_var, bg=C["BG_CARD"], fg=C["TEXT_MAIN"],
    font=self._font(-1), wraplength=320, justify="left",
).pack(side="left", padx=(12, 4), pady=8)
ttk.Button(
    toast_frame, text=self._t("toast_retry_btn"), style="Accent.TButton",
    command=retry_cb,
).pack(side="left", padx=4)
ttk.Button(
    toast_frame, text="✕", width=2, command=dismiss_cb,
).pack(side="left", padx=(0, 8))
```

**テーマ/フォント規約（プロジェクト CLAUDE.md 準拠。ハードコード禁止）:**
- 色は必ず `C["KEY"]` 辞書経由（`C["BG_CARD"]`/`C["TEXT_MAIN"]`/`C["ACCENT"]` 等）。hex 直書き禁止。
- フォントは `self._font(delta)` ヘルパー。数値リテラルの font タプル禁止（D-12/D-13 の監査対象と同一規約）。
- ボタンスタイル: 再試行＝`"Accent.TButton"`（主要アクション）、✕＝通常 `"TButton"` 相当（幅2の簡易ボタン）。

**ボタンスタイル定義元（参考。新規 style は不要・既存 style を再利用）:**
```
grep -n "Accent.TButton\|Danger.TButton\|CropOn.TButton" pagefolio/ui_builder.py
```

---

### `pagefolio/file_ops.py`（保存系3メソッド, service, request-response）

**Analog:** 同ファイル内 `_save_as`（682-699行目）・`_save_compressed`（725-753行目）が相互に同型。

**現状パターン（`_save_file`, 647-680行目付近の抜粋）:**
```python
# pagefolio/file_ops.py:673-680
self._set_status(
    self._t("status_saved").format(name=os.path.basename(self.filepath))
)
self.plugin_manager.fire_event("on_file_save", self, self.filepath)
# ↑ 成功パス。ここに toast_manager.dismiss("save") 呼び出しを追加（D-08）
except Exception as e:
    messagebox.showerror(
        self._t("err_save_title"), self._t("err_save_msg").format(e=e)
    )
    # ↑ ここを toast_manager.show("save", msg, retry_cb=self._save_file) へ置換
```

**`_save_as`（694-699行目）・`_save_compressed`（749-753行目）も同型:**
```python
# pagefolio/file_ops.py:694-699
self._set_status(...)
self.plugin_manager.fire_event("on_file_save", self, path)
except Exception as e:
    messagebox.showerror(self._t("err_title"), str(e))
```
成功パスの直後に `dismiss(category)`、except 節の `messagebox.showerror` を `toast_manager.show(category, msg, retry_cb)` へ置換する点は3メソッド共通。カテゴリキーは「同一操作の単純再実行」（D-03）に対応させるため、メソッド単位で分ける想定（例: `"save"`, `"save_as"`, `"save_compressed"`）。

**既存 LANG キー（再利用）:**
```python
# pagefolio/lang.py
"err_save_title": "保存エラー",
"err_save_msg": "保存に失敗しました:\n{e}",
"err_print_title": "印刷エラー",
"err_print_msg": "印刷に失敗しました:\n{e}",
```
**新規追加が必要（ja/en 両方・`test_lang_parity.py` 対象）:**
```python
"toast_retry_btn": "再試行",  # en: "Retry"
```

---

### `pagefolio/file_ops.py`（`_restore_state` の `insert_redo` ブロック, service, CRUD デルタ復元）

**Analog:** 同ファイル内 `delete_redo`（354-358行目）— 対称 op の正しい実装。

**バグ現状（401-407行目。誤り＝再挿入している）:**
```python
elif op == "insert_redo":
    # insert_redo: insert の再実行相当。キャプチャした bytes を昇順で再挿入する
    # （insert→undo→redo の連鎖では「再挿入」が正しい挙動）。
    for page_i, page_bytes in state["data"]:
        tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
        self.doc.insert_pdf(tmp, start_at=page_i)
        tmp.close()
```

**倣うべき対称実装（`delete_redo`, 354-358行目）:**
```python
elif op == "delete_redo":
    # redo: 昇順インデックスのページを逆順で削除（インデックスずれ防止）
    targets = sorted([page_i for page_i, _ in state["data"]], reverse=True)
    for page_i in targets:
        self.doc.delete_page(page_i)
```

**推奨修正（`insert_redo` は「前段 redo で再挿入されたページを取り除く」＝削除であるべき）:**
```python
elif op == "insert_redo":
    # insert_redo state の restore = 前段 redo で再挿入されたページを取り除く
    # （delete_redo と対称: 昇順インデックスを降順で削除しインデックスずれを防止）
    targets = sorted([page_i for page_i, _ in state["data"]], reverse=True)
    for page_i in targets:
        self.doc.delete_page(page_i)
```
`_apply_inverse`（297-304行目の `insert_redo` 分岐）と `_dispose_state`（Blob 解放ロジック）は変更不要。修正範囲は `_restore_state` 内の `insert_redo` ブロック（401-407行目）のみに限定する。

---

### `pagefolio/print_ops.py`（`_print_pdf`/`_send_to_printer`, service, request-response）

**Analog:** `pagefolio/file_ops.py` 保存系（同時改修・同一 D-02 対象群）。

**現状（36-47行目, 49-79行目付近）:**
```python
# pagefolio/print_ops.py:43-47（write_print_tempfile 失敗）
messagebox.showerror(...)
# pagefolio/print_ops.py:67-79（_send_to_printer 内）
self._set_status(self._t("status_print_sent").format(name=name))
...
self._set_status(self._t("status_print_opened").format(name=name))
...
except OSError as e:
    logger.exception("既定アプリでのオープンにも失敗: %s", e)
    messagebox.showerror(
        self._t("err_print_title"), self._t("err_print_no_handler")
    )
```
D-02 は `_print_pdf`/`_send_to_printer` を明示指定。一貫性のため両方の `showerror`（`write_print_tempfile` 失敗経路含む）をトースト化対象に含める（RESEARCH.md Open Questions #2 の推奨に従う。同一操作カテゴリ `"print"` として扱う）。成功パス（67行目/74行目 `_set_status`）の直後に `dismiss("print")` を追加。

---

### `pagefolio/ui_builder.py`（`_build_ui()`/`_rebuild_ui()`, component）

**Analog:** 同ファイル内 `_build_menubar()` の `_rebuild_ui()` 再呼び出しパターン（app.py 295-303行目コメント参照）— 同型の「`root.winfo_children()` 全破棄後に再生成が必要なコンポーネント」問題。

**必須対応（Pitfall 2）:** `ToastManager` は `_build_ui()` 内で毎回インスタンス化し直す。`_rebuild_ui()`（app.py 655-680行目）は `self.root` 直下の全ウィジェットを `destroy()` するため、トースト Frame の参照も無効化される。状態復元は不要（テーマ切替でトーストが消えても再表示不要という D-05/D-08 の設計判断どおり）。

---

### `pagefolio/dialogs/plugin.py`（Canvas ホイールバインド追加, component）

**Analog:** `pagefolio/dialogs/llm_config/dialog.py:101-156`（`_build_scrollable_area`）。

**現状（plugin.py 71-72行目）:** `Canvas`/`Scrollbar` の生成のみでホイールバインドなし。

**倣うべき動的バインドパターン（llm_config/dialog.py 101-156行目付近）:**
```python
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

def _bind_wheel(_event=None):
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.bind_all("<Button-4>", _on_mousewheel_linux)
    canvas.bind_all("<Button-5>", _on_mousewheel_linux)

def _unbind_wheel(_event=None):
    canvas.unbind_all("<MouseWheel>")
    canvas.unbind_all("<Button-4>")
    canvas.unbind_all("<Button-5>")

canvas.bind("<Enter>", _bind_wheel)
canvas.bind("<Leave>", _unbind_wheel)
```
（実際の行番号: llm_config/dialog.py 142-149行目に `bind_all`/`unbind_all` 呼び出し実体あり。`_compute_dialog_height` は159行目定義・95行目/316行目で呼び出し）

---

### `pagefolio/ocr_dialog.py`（`_center()` 高さクランプ追加, component）

**Analog:** `pagefolio/dialogs/llm_config/dialog.py:159`（`_compute_dialog_height`）。

**基準実装:**
```python
def _compute_dialog_height(self):
    self.update_idletasks()
    content_h = self._body.winfo_reqheight() + self._btn_row.winfo_reqheight()
    screen_h = self.winfo_screenheight()
    max_h = max(320, screen_h - 100)
    return min(max_h, max(480, content_h + 40))
```
`ocr_dialog.py._center()`（197-207行目付近）の `h = max(680, int(fs * 56))` に `winfo_screenheight()` クランプを追加する形で是正（既存 `_body`/`_btn_row` 相当構造がなければ等価ロジックを導入）。

---

### `pagefolio/dialogs/about.py`（42行目フォントハードコード是正, component）

**Analog:** 同ファイル内49行目 `font=self._font(0)`（VERSION ラベルは既に正しい規約準拠）。

**現状（36-43行目, 実測確認済み）:**
```python
# pagefolio/dialogs/about.py:36-43
tk.Label(
    self,
    text="PageFolio",
    bg=C["BG_DARK"],
    fg=C["ACCENT"],
    font=("Segoe UI", 16, "bold"),
).pack(pady=(20, 2))
```
**是正後:**
```python
font=self._font(6, "bold"),
```
（ベースフォント10との組合せで現状16ptを再現する提案値。実装時に `self._font(0)[1]` の実測値で delta を確定する）

---

### `tests/test_font_hardcode_guard.py`（新規, test, batch）

**Analog:** `tests/test_source_keyguard.py`（grep 型ソーススキャンの直接複製元）。

```python
import pathlib
import re

_FONT_HARDCODE_PATTERN = re.compile(r'font=\(\s*["\']Segoe UI["\']\s*,\s*\d+')
_PAGEFOLIO_DIR = pathlib.Path(__file__).resolve().parent.parent / "pagefolio"

def test_no_hardcoded_font_sizes():
    offenders = []
    for py in _PAGEFOLIO_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if _FONT_HARDCODE_PATTERN.search(text):
            offenders.append(str(py))
    assert not offenders, f"フォントサイズのハードコードが検出された: {offenders}"
```
`ui_builder.py` の `font=("Segoe UI", fs)`（変数）や `settings.py` のプレビューラベル（変数）はこの正規表現（`\d+` は数値リテラルのみ）にマッチしないため allowlist 不要。

---

### `tests/test_pdf_ops.py::TestInsertUndoRedo`（4手往復メソッド追加, test, CRUD）

**Analog:** `tests/test_undo_stress.py::TestBlobLeakDetection::test_double_release_chain_delete_undo_redo_undo`（delete 版の同型4手パターン。命名前例として踏襲）。

既存 `test_insert_undo_redo_roundtrip`（718行目付近）は insert→undo→redo の3手までしか検証していない。新規メソッドは `insert → undo → redo → undo`（2回目）の4手目でページ数が正しく往復することを検証する（修正前は5ページになるバグを検出できる形にする）。

## Shared Patterns

### テーマ/フォント/i18n 規約（全改修ファイル共通）
**Source:** `CLAUDE.md`（プロジェクトルート）+ `pagefolio/lang.py` + `pagefolio/themes.py`
**Apply to:** `toast.py`（新規）・`about.py`・`plugin.py` 是正箇所すべて
- 色は `C["KEY"]` 辞書経由（ハードコード hex 禁止）
- フォントは `self._font(delta, weight=None)` ヘルパー（数値リテラル禁止）
- 文言は `LANG` 辞書経由・`self._t(key)`（ja/en 両方に同一キー追加、`test_lang_parity.py` 対象）

### スクロール可能ダイアログ統一基準（D-10）
**Source:** `pagefolio/dialogs/llm_config/dialog.py`（`_build_scrollable_area`: 101-156行目, `_compute_dialog_height`: 159行目〜, 呼び出し元 95行目/316行目）
**Apply to:** `pagefolio/dialogs/plugin.py`（ホイールバインド追加）、`pagefolio/ocr_dialog.py`（高さクランプ追加）
- Canvas + Scrollbar + `<Configure>` による scrollregion 自動更新
- `Enter`/`Leave` による `bind_all`/`unbind_all` の動的マウスホイール束縛（複数 Canvas 共存時の横取り防止）
- `winfo_screenheight()` による高さクランプ + 下部ボタン固定

### Undo/Redo デルタ復元の対称性原則
**Source:** `pagefolio/file_ops.py` の `delete`/`delete_redo`（348-358行目）・`insert`/`insert_undo`（391-400行目）
**Apply to:** `insert_redo` ブロック（401-407行目）の修正
- `_apply_inverse` で計算した逆デルタの `op` 名（`insert_undo`/`insert_redo`/`delete_redo` 等）が `_restore_state` 側でも対称なアクション（挿入↔削除）になっているか常に確認する。本フェーズの D-17 修正はこの原則の1箇所適用。

### `_rebuild_ui()` 再生成対応
**Source:** `pagefolio/app.py`（`_rebuild_ui()`: 655-680行目付近）・`pagefolio/ui_builder.py`（`_build_menubar()` の再呼び出しパターン）
**Apply to:** `pagefolio/toast.py` の `ToastManager` 統合（`ui_builder.py._build_ui()` 内での再インスタンス化）

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pagefolio/toast.py`（新規モジュール自体の構造） | component | event-driven | プロジェクト内に常駐オーバーレイ通知の前例なし（`_set_status` はラベル更新のみで別役割）。RESEARCH.md Pattern 1 のコード例を土台として新規実装する |

## Metadata

**Analog search scope:** `pagefolio/`（file_ops.py, print_ops.py, ui_builder.py, dialogs/, ocr_dialog.py）, `tests/`
**Files scanned:** 上記11ファイル + 分析対象の analog 5ファイル（llm_config/dialog.py, file_ops.py 内 delete_redo, plugin.py, about.py, test_source_keyguard.py, test_undo_stress.py）
**Pattern extraction date:** 2026-07-16
