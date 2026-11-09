# Phase 4: 起動制御と既存画面への復帰 - Pattern Map

**Mapped:** 2026-10-21  
**Files analyzed:** 7（RESEARCH.md の提案と DoD 修正対象）  
**Analogs found:** 6 / 7（うち Win32 排他・IPC の完全一致は 0）

## File Classification

| 新規・変更ファイル | 役割 | データフロー | 最も近い既存コード | 一致度 |
|---|---|---|---|---|
| `pagefolio/__main__.py` | 起動入口 | request-response / event-driven | `pagefolio/__main__.py`, `pagefolio.py` | 同一ファイル |
| `pagefolio/startup_control.py`（提案） | OS 境界サービス | IPC / event-driven | `pagefolio/print_ops.py`, `pagefolio/viewer.py` | 部分一致。Win32 IPC 類例なし |
| `pagefolio/app.py` | GUI controller | event-driven | `pagefolio/app.py`, `pagefolio/dialogs/settings.py` | 同一ファイル |
| `pagefolio/lang.py` | i18n 設定 | lookup / transform | `pagefolio/lang.py` | 同一ファイル |
| `tests/test_startup_control.py`（提案） | テスト | event-driven / subprocess | `tests/test_shortcuts_dialog.py`, `tests/conftest.py` | 役割一致 |
| `tests/test_gsd_dod.py` | 品質ゲートテスト | file-I/O / batch | `tests/test_gsd_dod.py` | 同一ファイル |
| `.planning/PROJECT.md` | DoD 文書 | 文書 | `.planning/PROJECT.md` | 同一ファイル |

`pagefolio.py` は既存の委譲入口を確認する参照先であり、変更対象と確定したものではない。上記の新規パスも RESEARCH.md:135-137 の提案で、最終的な配置は計画時に決める。

## Pattern Assignments

### `pagefolio/__main__.py`（起動入口）

**Analog:** `pagefolio/__main__.py:8-30`, `pagefolio.py:8-11`。両方とも git 追跡済み。

**現行の単一入口**（`pagefolio/__main__.py:8-26`）:

```python
import tkinter as tk

from pagefolio.app import PDFEditorApp
from pagefolio.file_drop import _setup_file_drop

try:
    from tkinterdnd2 import TkinterDnD

    _HAS_TKDND = True
except ImportError:
    _HAS_TKDND = False


def main():
    if _HAS_TKDND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = PDFEditorApp(root)
    _setup_file_drop(app)
    root.mainloop()
```

`pagefolio.py:8-11` は `from pagefolio.__main__ import main` → `main()` のみ。起動判定はこの共有 `main()` の root 作成より前、一次プロセスの所有権解放は `mainloop()` 終了と初期化例外の両方を包む `finally` に置く。これは**新規に加える必要がある構造**で、既存コードに `finally` はない。`PDFEditorApp` は既存 app・設定・Undo を生成するため二次プロセスでは呼ばない（`pagefolio/app.py:138-218`）。

### `pagefolio/startup_control.py`（OS 境界サービス）

**部分 Analog:** `pagefolio/print_ops.py:13-20,55-91` の OS 依存 API 境界、`pagefolio/viewer.py:352-369` の Tk へ渡す非同期処理。いずれも git 追跡済み。**mutex、named pipe、`ctypes`/`wintypes`、Win32 handle、プロセス間 ACK の既存実装は `pagefolio/`・`tests/` に見つからない。** API 型・戻り値・期限処理は RESEARCH.md:139-169 と Microsoft 一次資料に基づき新規設計する。

**OS 能力判定と失敗分岐**（`pagefolio/print_ops.py:55-91`）:

```python
startfile = getattr(os, "startfile", None)
if startfile is None:
    messagebox.showinfo(self._t("info_title"), self._t("info_print_unsupported"))
    return
try:
    startfile(path, "print")
    return
except OSError as e:
    logger.warning("印刷動詞の起動に失敗、open 動詞で再試行: %s", e)
```

このファイルの GUI 通知は起動前には転用できない。判定失敗と「他の所有者あり」を別の結果にすること、失敗時に GUI 未構築でも案内できることは `04-CONTEXT.md:35-54` の決定。Win32 では関数ごとに `argtypes`/`restype` を明示し、handle を `finally` で閉じる型付き新規実装が必要。具体的な `ctypes` 抜粋は既存コードにはない。

**Tk メインスレッドへの処理移送**（`pagefolio/viewer.py:352-369`）:

```python
def render_rest(idx):
    if self._thumb_gen != gen or not self.doc:
        return
    # ...
    self.root.after_idle(lambda: render_rest(idx + 1))


self.root.after_idle(lambda: render_visible(0))
```

IPC 受信スレッドは Tk を直接呼ばず、復帰要求の処理を GUI 側の `root.after(...)` へ移す。受信時と Tk 実行直前に同じ期限・要求 ID を確認する点は新規契約（RESEARCH.md:145-153）。上の世代ガードは「遅れた callback を捨てる」構造の類例であり、期限・IPC の実装そのものではない。

### `pagefolio/app.py`（既存画面への復帰）

**Analog:** `pagefolio/app.py:217-218,264-272,498-510,641-665`; `pagefolio/dialogs/settings.py:18-36`。git 追跡済み。

**終了確認と root 寿命**（`pagefolio/app.py:498-507`）:

```python
def _quit(self):
    self._save_window_state()
    if self.doc:
        if messagebox.askyesno(self._t("confirm_title"), self._t("quit_confirm")):
            self._clear_undo_stacks()
            self.doc.close()
            self.root.destroy()
    else:
        self._clear_undo_stacks()
        self.root.destroy()
```

`WM_DELETE_WINDOW` は `pagefolio/app.py:217-218` で `_quit` に登録される。キャンセル時は `root.destroy()` されないため、起動所有権も維持する。所有権の解放を `_quit` の呼出し直後に置かず、入口の `mainloop()` 終了後に結び付ける。

**モーダルとフォーカス**（`pagefolio/dialogs/settings.py:18-36`, `pagefolio/app.py:264-272,649-665`）:

```python
class SettingsDialog(tk.Toplevel):
    # ...
    self.grab_set()


focused = self.root.focus_get()
focused_class = focused.winfo_class() if focused else ""

existing = getattr(self, "_settings_dialog", None)
if existing is not None and existing.winfo_exists():
    existing.lift()
    existing.focus_force()
    return
```

既存 `_open_settings()` の `focus_force()` は設定ダイアログを明示的に開く操作用。二次起動からの復帰へ無条件に流用しない。現在の grab と有効な子ダイアログを確認して対象を選び、復帰前の入力先を保持する。最小化・最大化状態と Win32 前面化失敗時の taskbar 点滅は既存類例なし（RESEARCH.md:155-163）。正常復帰では `_set_status()`（`pagefolio/app.py:509-510`）を呼ばない決定（CONTEXT.md:19-26）。

### `pagefolio/lang.py`（i18n）

**Analog:** 同一ファイル `pagefolio/lang.py:7-10,806-808`、利用側 `pagefolio/app.py:593-595`、検証 `tests/test_lang_parity.py:40-43,55-60`。すべて git 追跡済み。

```python
LANG = {
    "ja": {
        "status_initial": "ファイルを開いてください",
        # ...
    },
    "en": {
        "status_initial": "Open a file to get started",
        # ...
    },
}
```

`pagefolio/app.py:593-595` は `LANG[self.lang].get(key, LANG["ja"].get(key, key))` を使う。新しい案内文言を追加するなら ja/en に同一キーを追加し、`tests/test_lang_parity.py:40-43` のキー集合一致と `:55-60` の未使用キー検査を通す。起動前に `app` が無い経路では `_t` に依存せず、言語取得と案内表示の境界を別途定める。

### `tests/test_startup_control.py`（提案、新規テスト）

**Analog:** `tests/test_shortcuts_dialog.py:29-74` の Tk 非依存判定テスト、`tests/conftest.py:16-29` の一時パス fixture、`tests/test_gsd_dod.py:249-275` の合成環境テスト。git 追跡済み。

```python
# tests/test_shortcuts_dialog.py:32-45
class TestShouldSuppressForFocusedInput:
    def test_control_combo_never_suppressed(self):
        assert should_suppress_for_focused_input("<Control-o>", "Entry") is False

    def test_unmodified_key_suppressed_on_entry(self):
        assert should_suppress_for_focused_input("<Delete>", "Entry") is True
```

```python
# tests/conftest.py:16-29
@pytest.fixture()
def tmp_settings(tmp_path):
    settings_path = tmp_path / "pagefolio_settings.json"

    def write_fn(data):
        settings_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    return settings_path, write_fn
```

純粋な期限判定・状態遷移は実 Tk を起こさず検査し、OS API/IPC 失敗は差替え可能な境界に故障注入する。別プロセス同時起動・実 Windows の前面化は**既存テスト類例なし**。RESEARCH.md:256-282 の検証計画に沿って新規 harness と実機記録を用意する。

### `tests/test_gsd_dod.py`（DoD ゲート）

**Analog:** 同一ファイル `tests/test_gsd_dod.py:115-182,185-204,245-275`。git 追跡済み。

```python
# tests/test_gsd_dod.py:129-143
live_root = planning_dir / "phases"
if live_root.is_dir():
    dirs.extend(p for p in live_root.iterdir() if p.is_dir())
# ... v1.9.0 以降の archive も dirs に追加
return sorted(dirs)
```

```python
# tests/test_gsd_dod.py:155-172
violations: list[tuple[str, str]] = []
for phase_dir in _collect_phase_dirs(repo_root):
    label = f"{phase_dir.parent.name}/{phase_dir.name}"
    validation_files = sorted(phase_dir.glob("*-VALIDATION.md"))
    if len(validation_files) != 1:
        violations.append((label, "..."))
        continue
    status = _read_validation_status(validation_files[0])
```

`tests/test_gsd_dod.py:249-256` の `_build_synthetic_repo(tmp_path, files)` は任意の `.planning/` 合成ツリーを作る。未完了 live、完了 live、ROADMAP 記載なし、v1.9.0 以降 archive の4件を独立ケースで固定し、曖昧な ROADMAP は明示的に失敗させる。実リポジトリの `test_completed_phases_are_validated()`（`:185-204`）は空集合でも失敗する設計を維持する。`04-VALIDATION.md` の仮作成でゲートを通さない。

### `.planning/PROJECT.md`（DoD 文書）

**Analog:** 同一ファイル `.planning/PROJECT.md:330-344`。git 追跡済み。`## フェーズ完了 DoD` の `:332` は完了前の validate を要求する一方、`:338` は live 全ディレクトリを対象と記述する。ゲート修正と同じ作業で「未完了 live は検証未要求、完了 live と適用範囲内 archive は要求」を明文化する。ドキュメント更新対象であり Python のコード抜粋はない。

## Shared Patterns

### Tk と非同期境界

`pagefolio/viewer.py:352-369` の `root.after_idle(...)` と世代チェックを参照。IPC worker は UI ウィジェットに触れず、期限切れ要求を Tk 実行前に破棄する。既存の `pagefolio/app.py:264-272` は `root.focus_get()` で現在の入力先を調べる。

### 生存期間と失敗時の後始末

`pagefolio/app.py:498-507` は確認キャンセルなら root を残す。`pagefolio/__main__.py:19-26` には現状 `finally` がないため、起動所有権と IPC の後始末は新規に追加する。`pagefolio/print_ops.py:55-91` は OS 機能不在・API エラーを分ける近接例だが、起動前案内の UI をそのままコピーしない。

### 言語と案内

`pagefolio/lang.py:7-10,806-808` の日英対称キー、`tests/test_lang_parity.py:40-43` の一致検査を適用。通常復帰の追加通知は CONTEXT.md の決定で不要。失敗案内は主画面生成前にも成立させる。

## No Analog Found

| 対象 | 役割 | フロー | 理由 |
|---|---|---|---|
| `pagefolio/startup_control.py` の Win32 mutex・IPC 部分 | OS 境界サービス | IPC / event-driven | `pagefolio/` と `tests/` に `ctypes`、named pipe、mutex、ACK の実装がない。RESEARCH.md の Microsoft API 契約で新規設計する。 |
| `tests/test_startup_control.py` の複数 OS プロセス GUI 試験 | テスト | subprocess / event-driven | 既存に同等の起動競合ハーネスがない。 |

## Metadata

**検索範囲:** `pagefolio/`, `tests/`, `pagefolio.py`, `.planning/PROJECT.md`。  
**確認した既存ファイル:** 13。  
**追跡確認:** 本文で名指しした現存アナログは `git ls-files -- <path>` で追跡を確認。  
**抽出日:** 2026-10-21。
