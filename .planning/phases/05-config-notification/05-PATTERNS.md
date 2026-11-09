# Phase 5: 設定読込・保存失敗の通知 - Pattern Map

**Mapped:** 2026-10-22  
**Files analyzed:** 13（既存変更 12、新設 1）  
**Analogs found:** 13 / 13

## File Classification

| 新設・変更ファイル | 責務 | データフロー | 最も近い既存 analog | 一致度 |
|---|---|---|---|---|
| `pagefolio/settings.py` | utility | file-I/O | 同ファイル `_load_settings` / `_save_settings` | exact |
| `pagefolio/app.py` | controller | event-driven | 同ファイル起動・保存・再構築経路 | exact |
| `pagefolio/toast.py` | component | event-driven | 同ファイル `ToastManager` | exact |
| `pagefolio/ui_builder.py` | component | event-driven | 同ファイル `_build_ui` / `_show_error_or_toast` | exact |
| `pagefolio/lang.py` | config | transform | 同ファイル `LANG` 日英キー | exact |
| `pagefolio/dialogs/settings.py` | component | event-driven | 同ファイル LLM `on_apply` | exact |
| `pagefolio/dialogs/shortcuts.py` | component | event-driven | 同ファイルショートカット保存 | exact |
| `pagefolio/ocr_dialog.py` | component | event-driven | 同ファイル LLM 設定適用 | exact |
| `pagefolio/redact_ops.py` | controller | event-driven | 同ファイルモザイク粒度保存 | exact |
| `pagefolio/viewer.py` | controller | event-driven | 同ファイル倍率・件数保存 | exact |
| `tests/test_settings_keyguard.py` | test | file-I/O | 同ファイル設定 I/O 回帰テスト | exact |
| `tests/test_toast.py` | test | event-driven | 同ファイル Tk / 記録スタブテスト | exact |
| `tests/test_config_notification.py`（新設候補） | test | file-I/O + event-driven | `tests/test_settings_keyguard.py` と `tests/test_toast.py` | role-match |

`tests/test_provider_ui.py` は保存後の画面状態を確認する場合の補助 analog。実装ファイルの採否は計画時に確定する。上表の既存 analog はすべて `git ls-files -- <path>` で追跡済みと確認した。

## Pattern Assignments

### `pagefolio/settings.py`（utility, file-I/O）

**Analog:** 同ファイル。標準ライブラリと package 絶対 import は 6–20 行、機密キー定義は 25–29 行。既存の辞書戻り値は `tests/test_settings_keyguard.py:275-290` が使うため、新しい結果通知 API を導入する際は互換性を保つ。

**読込・既定値補完**（301–311 行）:

```python
path = _get_settings_path()
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for k, v in defaults.items():
        data.setdefault(k, v)
    return data
```

**保存・原本保護**（314–343 行）:

```python
leaked = [k for k in _SENSITIVE_KEYS if k in settings]
to_save = {k: v for k, v in settings.items() if k not in _SENSITIVE_KEYS}
tmp_path = path + ".tmp"
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(to_save, f, ensure_ascii=False, indent=2)
os.replace(tmp_path, path)
```

抜粋の `to_save` は既存コードの機密キー混入分岐に属する。実際には非混入時 `to_save = settings`。`except Exception as e: logger.debug(...)`（306–311、341–343 行）が現在失敗を隠す接点。`.tmp` cleanup は未実装なので、この `os.replace` 前後に追加する。原本に直接書かない。

### `pagefolio/app.py`（controller, event-driven）

**Analog:** 同ファイル。import 群は 6–35 行。起動順は `_load_settings()` が 149 行、`_build_ui()` が 214 行。初期通知状態は画面構築前に App に保持し、構築後に表示する。

**終了時の保存接点**（499–508、575–585 行）:

```python
def _quit(self):
    self._save_window_state()
    if self.doc:
        if messagebox.askyesno(self._t("confirm_title"), self._t("quit_confirm")):
            ...


def _save_window_state(self):
    ...
    self._save_sash_positions()
    self.settings["edit_mode"] = self.edit_mode
    _save_settings(self.settings)
```

確認より先の自動保存を読込失敗時に抑止する位置。明示的変更による保存は `_toggle_lang`（598–603 行）、`_reload_plugins`（633–636 行）、`_apply_llm_settings_live`（668–679 行）、`_apply_settings`（682–695 行）にある。

**メモリ値と画面再構築**（686–716 行）:

```python
self.settings = new_settings
...
_save_settings(new_settings)
self._rebuild_ui()
self._set_status(self._t("status_settings"))
```

失敗時も `self.settings` を維持する。成功と誤認させる表示を抑える判定はここに置ける。`_rebuild_ui()` は root の子を破棄して `_build_ui()` を再実行するため（697–716 行）、未消化通知はウィジェット外の App 状態へ置く。

### `pagefolio/toast.py` / `pagefolio/ui_builder.py`（component, event-driven）

**Analog:** `pagefolio/toast.py:21-106` と `pagefolio/ui_builder.py:184-200`。`tkinter` / `ttk` / `C` import は toast 21–25 行。

**表示契約**（toast 40–62 行）:

```python
def show(self, category, message, retry_cb):
    if self._active_category == category and self._frame is not None:
        self._msg_var.set(message)
        if self._retry_btn is not None:
            self._retry_btn.configure(command=retry_cb)
        return
    self._destroy_frame()
    self._active_category = category
    self._build_frame(category, message, retry_cb)
```

**閉じる操作**（toast 57–62、80–95 行）は `dismiss(category)` と ✕ ボタン。再試行ボタンは現在 `_build_frame` で無条件に作る。設定通知では任意化し、既存 PDF 保存・印刷の callback 契約を保持する。保存失敗を同カテゴリで繰り返し `show` するだけでは「毎回残る」を満たさない。App 側に未消化イベントを保持して順次表示する設計が必要。

**UI 接続**（ui_builder 184–200 行）:

```python
self._toast = ToastManager(self)
...
if toast is not None:
    toast.show(category, msg, retry_cb=retry_cb)
    return
messagebox.showerror(title, msg)
```

設定通知は非モーダル必須なので、既存 `_show_error_or_toast` の messagebox fallback をそのまま適用しない。再構築ごとに `ToastManager` が新規生成される点を App の再表示処理へ接続する。

### `pagefolio/lang.py`（config, transform）

**Analog:** 同ファイル `LANG`（7 行）。既存対訳は `status_settings`（276、1084 行）、`toast_retry_btn`（692、1492 行）。新しい読込 JSON 破損・読取不能・保存失敗のキーを `ja` と `en` の双方に追加し、`app.py:_t`（590–592 行）から参照する。通知文言には例外文字列と設定パスを補間しない。

### 保存呼出元の画面・Mixin（event-driven）

| 対象 | 直接 analog / 抜粋 | 計画への適用 |
|---|---|---|
| `pagefolio/dialogs/settings.py` | 230–240 行: `self.current_settings.update(llm_settings)` → `_save_settings(self.current_settings)` → `on_llm_apply(dict(llm_settings))` | `app.py:668-679` でも同じ操作を保存する。片側に保存を集約し、外側 Cancel から独立したメモリ反映は残す。 |
| `pagefolio/dialogs/shortcuts.py` | 280–285 行: `self._app.settings["shortcuts"] = diff` → `self._app._bind_shortcuts()` → `_save_settings(self._app.settings)` | UI 更新と保存成否通知を分離する。 |
| `pagefolio/ocr_dialog.py` | 1037–1042 行: `self.app.settings.update(llm_settings)` → `_save_settings(self.app.settings)` | App の共通保存窓口に接続する。後続の prompt キャッシュ同期は残す。 |
| `pagefolio/redact_ops.py` | 256–261 行: `self.settings["mosaic_block"] = int(self.mosaic_block_var.get())` → `_save_settings(self.settings)` | 設定メモリ更新後に保存失敗通知を伝播する。 |
| `pagefolio/viewer.py` | 159–165、180–188 行: `thumb_zoom` / `thumb_page_size` 更新 → `_save_settings(self.settings)` → `_refresh_all()` | 失敗してもメモリ値・再描画を維持する。 |

各 Mixin の遅延 `from pagefolio.settings import _save_settings` は現行パターン。通知の共通化には `app.py` へ保存窓口を作り、これらの呼出元をそこへ寄せると漏れを監査しやすい。これは割当方針であり、既存実装ではない。

### `tests/test_settings_keyguard.py` / `tests/test_config_notification.py`（test, file-I/O）

**Analog:** `tests/test_settings_keyguard.py:145-165,167-212,275-290`。一時パスを注入する（275–286 行）:

```python
settings_path = tmp_path / "partial_settings.json"
monkeypatch.setattr(
    "pagefolio.settings._get_settings_path",
    lambda: str(settings_path),
)
result = _load_settings()
```

既存の `caplog` と入力 dict 非破壊の検査は 167–212 行。新設テストでは `json.dump` / `os.replace` / `open` の失敗を別々に注入し、原本 bytes、`.tmp` cleanup、結果種別を検証する。App の通知回数・終了抑止・明示保存は Tk を使わないスタブで検証する。

### `tests/test_toast.py`（test, event-driven）

**Analog:** 同ファイル。隠し root fixture は 22–34 行、最小 `_FakeApp` は 37–49 行、ウィジェット検証は 60–160 行。

```python
tm.show("save_file", "保存失敗", retry_cb=lambda: None)
first_frame = tm._frame
tm.show("print", "印刷失敗", retry_cb=lambda: None)
assert tm._frame is not first_frame
```

上は 74–86 行の既存挙動。再試行ボタン確認は 101–117 行、閉じるボタンは 119–128 行。同カテゴリ更新と callback 差替えは 130–160 行。通知呼出しだけを記録する `_RecordingToast` は 240–251 行で、App 経路のテストに再利用できる。

## Shared Patterns

- **設定保存の単一経路:** `_save_settings` は `pagefolio/settings.py:314-343` の原子的置換・機密キー除外を維持する。App 以外の直接呼出元は上表の5ファイルにあり、失敗通知の漏れを防ぐため全経路を扱う。
- **通知の所有者:** `ToastManager` は表示ウィジェット（`toast.py:30-106`）、App はセッション中の通知イベント（`app.py:149,697-716`）。`ui_builder.py:184-187` の再生成後に App から未消化通知を復元する。
- **日英の文言:** `pagefolio/lang.py:7,276,692,1084,1492` の同じキーを両言語へ定義し、`app.py:590-592` の `_t` で取得する。
- **既存 PDF トースト互換:** `tests/test_toast.py:60-160,240-251` にある `retry_cb`・`dismiss(category)`・同カテゴリ更新を回帰条件とする。

## No Analog Found

近い analog がないファイルはない。ただし App 側で複数の同文言保存失敗を未消化イベントとして保持し、トーストに順送りする仕組みは既存にない。`toast.py` の単一表示契約を踏まえて設計する。

## Metadata

**Analog search scope:** `pagefolio/`、`pagefolio/dialogs/`、`tests/`  
**Pattern extraction date:** 2026-10-22  
**注意:** RESEARCH の D-14 抑止解除条件と D-16 のキュー消化・時間切れ条件は未確定。計画で明記する。Tk 実ウィジェットテストは研究時に `init.tcl` エラーが出ており、実装時に切り分ける。
