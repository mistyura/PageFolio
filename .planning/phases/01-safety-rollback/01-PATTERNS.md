# Phase 1: 保存・編集・設定の安全性是正 - Pattern Map

**Mapped:** 2026-08-10
**Files analyzed:** 11（変更対象）+ 3（テスト拡張対象）
**Analogs found:** 11 / 11（本フェーズは新規ファイルなし。全て既存ファイルの内部修正であり「analog」は同一ファイル内の隣接する既に正しい実装、または同一責務を持つ姉妹関数）

## 前提

本フェーズは **防御的リファクタリングのみ**（新規ファイル・新規モジュールなし）。したがって「analog」は他ファイルではなく、多くの場合 **同一ファイル内の既に正しい実装**（インクリメンタル保存・`_set_password`/`_remove_password` 等）である。RESEARCH.md に実行時検証済みの根本原因・修正パターンが逐語引用付きで揃っているため、本 PATTERNS.md はそれを「ファイル別・修正意図別」に再構成し、プランナーがそのまま action に貼れる形にする。

## File Classification

| 変更対象ファイル | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `pagefolio/file_ops.py`（`_overwrite_current_file`） | service（永続化） | file-I/O | 同ファイル `_save_file` 内インクリメンタル保存（file_ops.py:666-673） | exact（同一ファイル内の正しい実装） |
| `pagefolio/file_ops.py`（`_save_as`） | service（永続化） | file-I/O | 同ファイル `save_with_password`/`save_without_password`（file_ops.py:21-33） | exact |
| `pagefolio/file_ops.py`（`pdf_has_password` 導出） | utility（純関数） | transform | `tests/test_password.py::TestSetRemovePassword` の既存 `needs_pass` 検証パターン | role-match（テスト側） |
| `pagefolio/file_ops.py`（`_undo`/`_redo`） | service（状態復元） | event-driven | 同ファイル `_push_evicting`/`_clear_redo_stack`（file_ops.py:102-117） | exact |
| `pagefolio/page_ops.py`（`_do_insert`） | service（CRUD: ページ挿入） | file-I/O + CRUD | 同ファイル `_restore_state` の insert op undo 実装（file_ops.py:391-394） | exact（削除ループの巻き戻しパターン） |
| `pagefolio/page_ops.py`（`_duplicate_page`） | service（CRUD: ページ複製） | CRUD | 同ファイル `_save_undo` の呼び出し規約（`file_ops.py:158-159` の `duplicate` op データ構造） | exact |
| `pagefolio/ocr_providers/errors.py`（新規例外型） | model（例外クラス） | transform | 同ファイル `OCRAPIKeyError`/`OCRContextLengthError`（errors.py:7-46） | exact |
| `pagefolio/ocr.py`（`build_provider`） | service（ファクトリ） | request-response | 同ファイル既存の `("lmstudio", "", "off")` 分岐（ocr.py:431-441） | exact |
| `pagefolio/app.py`（`_open_batch_ocr` 周辺・メニュー） | controller（UI 入口） | request-response | 同ファイル `_update_ocr_buttons_state()`（app.py:334-346） | exact |
| `pagefolio/dialogs/batch_ocr.py`（`_on_start_batch`） | controller | request-response | `_build_provider_once`（batch_ocr.py:592-625） | exact |
| `pagefolio/dialogs/llm_config/sections.py`（`_on_template_change`/`_has_unsaved_template_changes`） | provider/hook（ダイアログ状態） | event-driven | 同ファイル・同関数の隣接ロジック（未選択時分岐は変更しない対比対象） | exact |
| `pagefolio/dialogs/llm_config/dialog.py`（Apply ハンドラ） | controller | request-response | 既に正しい参照実装（変更不要・sections.py 側の一本化先） | exact |
| `tests/test_password.py`（拡張） | test | request-response | `TestSetRemovePassword`（test_password.py:129-169） | exact |
| `tests/test_pdf_ops.py`（拡張） | test | CRUD | `TestInsertUndoRedo.test_insert_undo_redo_undo_roundtrip`（test_pdf_ops.py:758-802） | exact |
| `tests/test_provider_ui.py`（拡張） | test | event-driven | `test_no_active_template_warns_on_unsaved_freeform_text`（test_provider_ui.py:2249-2297） | exact |

## Pattern Assignments

### `pagefolio/file_ops.py` — `_overwrite_current_file` / `_save_as`（D-01・D-02・D-03）

**Analog:** 同ファイル内の既に正しいインクリメンタル保存（file_ops.py:666-673）

**Imports pattern**（file_ops.py:1-14。新規 import は不要。`fitz` は既に import 済み）:
```python
import logging
import os
from tkinter import filedialog, messagebox, simpledialog

import fitz

from pagefolio.constants import IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)
```

**既に正しい参照実装**（変更不要・コピー元）:
```python
# Source: pagefolio/file_ops.py:666-673
try:
    self.doc.save(
        self.filepath, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP
    )
except Exception as e:
    logger.debug("incremental save 失敗、開き直して保存: %s", e)
    self._overwrite_current_file(self.filepath)  # ← D-02 の修正対象
```

**修正パターン（`_overwrite_current_file`・D-02）** — `setdefault` で「未指定時のみ既定化」を実現し、`_set_password`/`_remove_password` の明示 kwargs を上書きしない（Pitfall 1 参照）:
```python
def _overwrite_current_file(self, path, **save_kwargs):
    save_kwargs.setdefault("encryption", fitz.PDF_ENCRYPT_KEEP)
    data = self.doc.tobytes(**save_kwargs)
    ...
```

**修正パターン（`_save_as`・D-01）** — 無条件付与（確認ダイアログなし）:
```python
# Before: self.doc.save(path)
# After:
self.doc.save(path, encryption=fitz.PDF_ENCRYPT_KEEP)
```

**明示 kwargs の対比（影響を受けないことの確認用）**:
```python
# Source: pagefolio/file_ops.py:21-33
def save_with_password(doc, path, password):
    doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password)

def save_without_password(doc, path):
    doc.save(path, encryption=fitz.PDF_ENCRYPT_NONE)
```

**`pdf_has_password` 論理導出パターン（D-03・純関数・実行時 I/O なし）**:
```python
if encryption == fitz.PDF_ENCRYPT_NONE:
    self.pdf_has_password = False
elif encryption == fitz.PDF_ENCRYPT_AES_256:
    self.pdf_has_password = True
else:  # PDF_ENCRYPT_KEEP または未指定
    pass  # 現在値を維持
```

**テストの Error/Assertion パターン（回帰テスト側の analog）**:
```python
# Source: tests/test_password.py:132-141
def test_do_set_password_writes_encrypted(self, tmp_path, monkeypatch):
    out = str(tmp_path / "out.pdf")
    monkeypatch.setattr(file_ops.filedialog, "asksaveasfilename", lambda **kw: out)
    app = _DummyApp(doc=_make_doc(), filepath=None)
    app._do_set_password("secret")
    reopened = fitz.open(out)
    assert reopened.needs_pass
    assert reopened.authenticate("secret") > 0
    reopened.close()
    app.doc.close()
```
D-01〜D-03 の回帰テストはこの型（`fitz.open(out)` → `needs_pass`/`authenticate` を実検証）をそのまま踏襲する。`_DummyApp` フィクスチャは `tests/test_password.py` 冒頭で定義済み（要参照）。

---

### `pagefolio/file_ops.py` — `_undo` / `_redo`（D-13・D-14）

**Analog:** 同ファイル `_push_evicting` / `_clear_redo_stack`（Blob ライフサイクル正規 API）

**現状（逐語・修正対象）**:
```python
# Source: pagefolio/file_ops.py:175-186
def _undo(self):
    if not self._undo_stack:
        self._set_status(self._t("undo_empty"))
        return
    state = self._undo_stack.pop()
    inverse = self._restore_state(state)
    if inverse.get("data") is not state.get("data"):
        self._dispose_state(state)
    self._push_evicting(self._redo_stack, inverse)
    self._set_status(self._t("undo_done"))
```

**Blob 正規 API（analog・そのまま利用）**:
```python
# Source: pagefolio/file_ops.py:102-117
def _push_evicting(self, stack, state):
    """deque へ push する前に、溢れて evict される最古 state を解放する。"""
    if stack.maxlen is not None and len(stack) == stack.maxlen and stack:
        self._dispose_state(stack[0])
    stack.append(state)

def _clear_redo_stack(self):
    for st in self._redo_stack:
        self._dispose_state(st)
    self._redo_stack.clear()
```

**修正パターン（D-13/D-14・`_undo`/`_redo` に共通適用）**:
```python
def _undo(self):
    if not self._undo_stack:
        self._set_status(self._t("undo_empty"))
        return
    state = self._undo_stack.pop()
    try:
        inverse = self._restore_state(state)
    except Exception as e:
        self._push_evicting(self._undo_stack, state)  # _dispose_state は呼ばない（Pitfall 4）
        messagebox.showerror(self._t("err_title"), <復元失敗メッセージ>.format(e=e))
        return
    if inverse.get("data") is not state.get("data"):
        self._dispose_state(state)
    self._push_evicting(self._redo_stack, inverse)
    self._set_status(self._t("undo_done"))
```
`messagebox` は同ファイル冒頭で `from tkinter import filedialog, messagebox, simpledialog` として既に import 済み（追加不要）。`_redo` にも同型で適用する。

---

### `pagefolio/page_ops.py` — `_do_insert`（D-08・D-09・D-10）

**Analog:** 同ファイル（`file_ops.py`）の `_restore_state` insert op 巻き戻し実装

**巻き戻しインデックス計算の正規パターン（analog・そのまま踏襲。Pitfall 3 の回避策）**:
```python
# Source: pagefolio/file_ops.py:391-394
elif op == "insert":
    insert_at, num = state["data"]
    for _ in range(num):
        self.doc.delete_page(insert_at)
```

**現状の2バグ（逐語・修正対象）**:
```python
# Source: pagefolio/page_ops.py:756-790
def _do_insert(self, ordered_paths, insert_at):
    self._save_undo("insert", insert_at=insert_at)
    try:
        total = 0
        pos = insert_at
        for path in ordered_paths:
            src = self._open_path_as_pdf(path)
            self.doc.insert_pdf(src, start_at=pos)  # 例外時 src がリーク（バグ1・D-09）
            pos += len(src)
            total += len(src)
            src.close()
        self._undo_stack[-1]["data"][1] = total
        ...
    except Exception as e:
        if self._undo_stack and self._undo_stack[-1].get("op") == "insert":
            self._undo_stack.pop()  # 直接 pop（Blob リーク・規約違反・D-14）
        # 巻き戻しなし＝無警告部分適用（バグ2・D-08/D-10）
```

**修正パターン（D-08〜D-10・D-14）**:
```python
def _do_insert(self, ordered_paths, insert_at):
    self._save_undo("insert", insert_at=insert_at)
    total = 0
    pos = insert_at
    try:
        for path in ordered_paths:
            src = self._open_path_as_pdf(path)
            try:
                self.doc.insert_pdf(src, start_at=pos)
                n = len(src)
                pos += n
                total += n
            finally:
                src.close()  # D-09
        self._undo_stack[-1]["data"][1] = total
        ...
    except Exception as e:
        try:
            for _ in range(total):
                self.doc.delete_page(insert_at)  # D-08: 同一インデックスを total 回（Pitfall 3）
            if self._undo_stack and self._undo_stack[-1].get("op") == "insert":
                self._undo_stack.pop()  # 巻き戻し成功時のみ pop 可
        except Exception:
            self._undo_stack[-1]["data"][1] = total  # D-10: 実挿入数を反映して残す
            messagebox.showwarning(self._t("warn_title"), <残存ページ数を明示するメッセージ>)
        self._invalidate_thumb_cache()
        self._refresh_all()
        messagebox.showerror(self._t("err_title"), str(e))
```
`messagebox` は `page_ops.py` 側でも同様に import 済みか要確認（未 import であれば `file_ops.py:8` と同じ `from tkinter import messagebox` を追加）。

---

### `pagefolio/page_ops.py` — `_duplicate_page`（D-11）

**Analog:** 同ファイル `_save_undo("duplicate", pno=pno)` のデータ構造（軽量・Blob キャプチャなし）

**参照（analog・不変）**:
```python
# Source: pagefolio/file_ops.py:158-159
elif op == "duplicate":
    state["data"] = kwargs["pno"]
```

**現状（逐語・修正対象・`_save_undo` が実処理より先）**:
```python
# Source: pagefolio/page_ops.py:177-193（概要）
def _duplicate_page(self):
    if not self._check_doc():
        return
    pno = self.current_page
    self._save_undo("duplicate", pno=pno)   # ← 実処理前（バグ）
    try:
        tmp = fitz.open()
        tmp.insert_pdf(self.doc, from_page=pno, to_page=pno)
        self.doc.insert_pdf(tmp, start_at=pno + 1)
        tmp.close()
        ...
    except Exception as e:
        messagebox.showerror(self._t("err_title"), str(e))
```

**修正パターン（D-11）**: `_save_undo` を `try` ブロック内・実処理成功後（例外送出しうる全操作完了後）へ移動する。呼び出しシグネチャ（`pno=pno`）は変更不要。

---

### `pagefolio/ocr_providers/errors.py` — OCR OFF 専用例外（D-06）

**Analog:** 同ファイル `OCRAPIKeyError`（環境変数名を保持する軽量例外）

```python
# Source: pagefolio/ocr_providers/errors.py:7-12
class OCRAPIKeyError(RuntimeError):
    """APIキー未設定を示す専用例外。環境変数名を保持する。"""

    def __init__(self, env_var):
        self.env_var = env_var
        super().__init__(f"環境変数 {env_var} が設定されていません")
```

**新設パターン（配置は Claude's Discretion。`errors.py` が既存 precedent と一貫性が高い）**:
```python
class OCRDisabledError(RuntimeError):
    """ocr_provider が明示的に "off" のとき、OCR 実行経路への進入を拒否する専用例外。

    空文字 "" は後方互換のため LM Studio 扱いのまま維持し、対象にしない。
    """
```

**呼び出し元の例外処理 analog（`_start_ocr`・既存の包括捕捉に型を追加する形）**:
```python
# Source: pagefolio/ocr.py:584-596 付近（現状 except ValueError as e: を捕捉）
```
`build_provider` 内・`("lmstudio", "", "off")` 分岐（ocr.py:431-441）を修正し、`"off"` のみ `OCRDisabledError` を送出、`""` は従来どおり `LMStudioProvider` を返す形へ分離する。

---

### `pagefolio/app.py` — バッチ OCR メニュー disabled 化（D-04・D-05）

**Analog:** 同ファイル `_update_ocr_buttons_state()`

```python
# Source: pagefolio/app.py:334-346（現状の通常 OCR ボタン disabled 化ロジック・雛形として踏襲）
```
バッチ OCR メニュー項目にも同型の disabled/label 切替を適用する。ラベルは i18n（`lang.py`）に「（OCR OFF）」併記キーを ja/en 両方に追加（**キー数の左右一致を維持**すること。`pagefolio/CLAUDE.md` 規約）。

---

### `pagefolio/dialogs/batch_ocr.py` — `_on_start_batch`（D-07 二重ガード）

**Analog:** `_build_provider_once`（batch_ocr.py:592-625・`build_provider` を直接呼ぶため D-06 の例外化だけで自然にガードされる）

`_on_start_batch` 実行開始時にも `build_provider` の `OCRDisabledError` を捕捉し、実行前に中断するガードを明示的に追加する（入口 disabled 化に加えた二重防御）。

---

### `pagefolio/dialogs/llm_config/sections.py`（D-15〜D-18）

**撤去対象（`_on_template_change` の即時書き込み）**:
```python
# Source: pagefolio/dialogs/llm_config/sections.py:1240-1245（D-15 で撤去）
if prompt_file_exists(CUSTOM_PROMPT_FILE):
    save_prompt_file(CUSTOM_PROMPT_FILE, custom_val)
if prompt_file_exists(SUMMARY_PROMPT_FILE):
    save_prompt_file(SUMMARY_PROMPT_FILE, summary_val)
```

**変更不要の参照実装（`dialog.py` の Apply ハンドラ・既に正しい・D-15〜D-17 の一本化先）**:
```python
# Source: pagefolio/dialogs/llm_config/dialog.py:445-469
llm_settings["ocr_custom_prompt"] = self.ocr_prompt_text.get("1.0", "end").strip()
llm_settings["ocr_summary_prompt"] = self.ocr_summary_prompt_text.get("1.0", "end").strip()
if _prompt_file_exists(CUSTOM_PROMPT_FILE):
    _save_prompt_file(CUSTOM_PROMPT_FILE, llm_settings["ocr_custom_prompt"])
if _prompt_file_exists(SUMMARY_PROMPT_FILE):
    _save_prompt_file(SUMMARY_PROMPT_FILE, llm_settings["ocr_summary_prompt"])
```

**`_has_unsaved_template_changes` 最小差分（D-18・Pitfall 5 厳守）**: 関数構造（sections.py:1158-1185）を維持し、`if not (prompt_file_exists(...) or prompt_file_exists(...)): return False`（1175-1179行目）の**1ブロックのみ**削除する。`if not self._active_template_name:` ブロック（未選択時ロジック）には触れない。

---

## Shared Patterns

### Undo Blob ライフサイクル規約
**Source:** `pagefolio/file_ops.py:102-117`（`_push_evicting`/`_clear_redo_stack`/`_dispose_state`/`_blob_bytes`）
**Apply to:** `file_ops.py`（`_undo`/`_redo`）、`page_ops.py`（`_do_insert` の undo エントリ処理）
```python
def _push_evicting(self, stack, state):
    if stack.maxlen is not None and len(stack) == stack.maxlen and stack:
        self._dispose_state(stack[0])
    stack.append(state)
```
スタックへの直接 `append`/`pop`/`clear` は禁止。`_do_insert` の `self._undo_stack.pop()`（現状の規約違反）も本フェーズで是正する（D-14）。

### `messagebox` エラー通知パターン
**Source:** `pagefolio/file_ops.py:8`（import 済み）、`page_ops.py` 内の既存 `messagebox.showerror(self._t("err_title"), str(e))` 呼び出し
**Apply to:** `_undo`/`_redo`（D-13）、`_do_insert`（D-10）
モーダル `showerror`/`showwarning` を使う。トースト（`ToastManager`）は本フェーズでは不採用（D-13 で明記済み）。

### i18n 追加パターン
**Source:** `pagefolio/lang.py`（ja/en 辞書。未使用キー回帰テスト常設）
**Apply to:** D-05（バッチOCR メニューラベル併記）、D-10（巻き戻し失敗警告メッセージ）
新規キーは ja/en 両方に同一キーで追加し、キー数の左右一致を維持する。

### 保存 kwargs の「既定化 vs 上書き」判断基準
**Source:** CONTEXT.md `<specifics>` セクション（D-02・D-18 で共通適用された設計判断）
**Apply to:** `_overwrite_current_file`（`setdefault` を使う。単純代入は禁止）
既存の付け忘れ・見落としバグと同型の再発を避けるため、「呼び出し側で毎回明示」ではなく「関数内デフォルトへ構造的に埋め込む」を一貫して選ぶ。

## No Analog Found

なし。本フェーズは全ファイルが既存コードの内部修正であり、修正パターンはすべて同一ファイルまたは近傍ファイルの既存実装から抽出できた（RESEARCH.md の実行時検証込み）。

## Metadata

**Analog search scope:** `pagefolio/file_ops.py`, `pagefolio/page_ops.py`, `pagefolio/ocr.py`, `pagefolio/ocr_providers/errors.py`, `pagefolio/app.py`, `pagefolio/dialogs/batch_ocr.py`, `pagefolio/dialogs/llm_config/{sections,dialog}.py`, `tests/test_password.py`, `tests/test_pdf_ops.py`
**Files scanned:** 9（RESEARCH.md の逐語 VERIFIED 引用 + 本セッションでの直接 Read 2件で裏取り）
**Pattern extraction date:** 2026-08-10
**Note:** RESEARCH.md がコード excerpt を実行時検証・行番号付きで既に網羅しているため、本 PATTERNS.md はそれをファイル別・修正意図別の「analog 対応表」として再構成したものである。プラン作成時は本ファイルと RESEARCH.md の Architecture Patterns / Common Pitfalls セクションを併読すること。
