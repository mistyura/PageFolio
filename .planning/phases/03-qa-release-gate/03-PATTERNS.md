# Phase 3: 品質保証・リリースゲート - Pattern Map

**Mapped:** 2026-08-11
**Files analyzed:** 7 changed/modified + 2 new
**Analogs found:** 7 / 9（新規2件は成果物ドキュメントのため analog 対象外）

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `pagefolio/file_ops.py`（`_save_file`/`_save_as`/`_save_compressed` の分離） | service (Mixin method) | request-response（確認 → 実処理 → エラーハンドリング） | `pagefolio/file_ops.py:1102-1132`（`_overwrite_current_file`。同一ファイル内の既存「実保存層」実装） | exact（同一パターンの横展開） |
| `tests/test_toast.py`（327/338/352行の3アサーション） | test | request-response（振る舞い検証） | 同ファイル `TestSaveFilePathsUseSharedHelper` 既存クラス（304-352行） | exact（同一テストクラスの改修） |
| `tests/conftest.py`（V190-QA-01 修復コード置き場・D-06） | config/fixture | batch（テスト環境セットアップ） | 同ファイル既存 fixture 群（`tmp_settings`/`sample_pdf`/`sample_pdf_doc`/`large_pdf_doc`/`multi_pdf_files`） | exact |
| `pagefolio/constants.py`（`APP_VERSION` バンプ・D-16） | config | transform（定数更新のみ） | 同ファイル `APP_VERSION = "v1.8.1"`（12行目） | exact |
| `README.md`（バッジ更新・D-16） | config/doc | transform | 既存バッジ行（CLAUDE.md が同期対象と規定） | exact |
| `開発履歴.md`（v1.9.0 エントリ追記・D-16） | doc | event-driven（マイルストーン単位の追記） | 既存の直近エントリ（v1.8.1 等） | exact |
| `REQUIREMENTS.md:60` / `ROADMAP.md:203`（D-12 文言訂正） | doc | transform | 既存該当行 | exact |
| `.planning/phases/03-qa-release-gate/03-UAT-RESULTS.md`（新規・D-15） | doc | batch（チェックリスト記録） | Phase 2 の human-verify 3分割実施記録（`.planning/phases/02-ocr-openai-chatgpt/` 配下の検証系成果物） | role-match（フェーズ成果物としての構成を踏襲） |
| 調査レポート（ファイル名 Claude's Discretion・例 `03-TEST-ENV-INVESTIGATION.md`） | doc | event-driven（実験ログ） | Phase 1 の A/B 検証記録（`.planning/STATE.md`「Blockers/Concerns」の記述スタイル） | role-match |

## Pattern Assignments

### `pagefolio/file_ops.py` の保存3経路分離（service, request-response）

**Analog:** `pagefolio/file_ops.py:1102-1132`（`_overwrite_current_file` — 既に「path を引数に取る・確認ダイアログを含まない実処理層」の形）

**参照実装（コピー元パターンそのもの）:**
```python
# Source: pagefolio/file_ops.py:1102-1132
def _overwrite_current_file(self, path, **save_kwargs):
    save_kwargs.setdefault("encryption", fitz.PDF_ENCRYPT_KEEP)
    current_has_password = getattr(self, "pdf_has_password", False)
    data = self.doc.tobytes(**save_kwargs)
    self.doc.close()
    try:
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        self.doc = fitz.open(path)
        self.pdf_has_password = derive_pdf_has_password(
            current_has_password, save_kwargs["encryption"]
        )
    except Exception:
        self.doc = fitz.open(stream=data, filetype="pdf")
        raise
```

**分離対象の現状コード（`_save_file`。他2経路も同型）:**
```python
# Source: pagefolio/file_ops.py:1134-1172
def _save_file(self):
    """上書き保存 — 確認ダイアログ付き"""
    if not self.doc:
        messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
        return
    if not self.filepath:
        self._save_as()
        return
    ext = os.path.splitext(self.filepath)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        self._set_status(self._t("status_image_save_as"))
        self._save_as()
        return
    if not messagebox.askyesno(              # ← 確認・パス選択層（初回のみ実行すべき）
        self._t("save_confirm_title"),
        self._t("save_confirm_msg").format(name=os.path.basename(self.filepath)),
    ):
        return
    try:
        try:
            self.doc.save(
                self.filepath, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP
            )
        except Exception as e:
            logger.debug("incremental save 失敗、開き直して保存: %s", e)
            self._overwrite_current_file(self.filepath)
        self._set_status(
            self._t("status_saved").format(name=os.path.basename(self.filepath))
        )
        self.plugin_manager.fire_event("on_file_save", self, self.filepath)
        if getattr(self, "_toast", None) is not None:
            self._toast.dismiss("save_file")
    except Exception as e:
        self._show_error_or_toast(
            "save_file",
            self._t("err_save_title"),
            self._t("err_save_msg").format(e=e),
            self._save_file,   # ← D-11 で「実保存層」の直接呼び出しへ差し替える対象
        )
```

**分離方針（D-11・Discretion 命名例）:**
- `_save_file` → 確認・パス選択層（`askyesno` を含む・初回呼び出し用）は維持し、実処理（`try: self.doc.save(incremental=True) except: self._overwrite_current_file(...)` 以降のブロック）を `_do_save_file(path)` 等の path 引数を取る内部関数へ切り出す。
- `retry_cb` は `self._save_file` ではなく、確定済み `self.filepath` を束縛した実処理層の呼び出し（`functools.partial(self._do_save_file, path)` または `lambda: self._do_save_file(path)`）を渡す。
- `_save_as`（1174-1195行）・`_save_compressed`（1221-1261行）も同型で、`asksaveasfilename` を含む確認・パス選択層と、`doc.save(path, **save_kwargs)`（または `_overwrite_current_file` 分岐）を含む実処理層へ分離する。
- 暗号化引数（`encryption=fitz.PDF_ENCRYPT_KEEP`）の受け渡しは実処理層側にそのまま残すこと（Phase 1 の暗号化維持ロジック回帰防止・`tests/test_password.py` で検証）。

**エラーハンドリング/トースト連携パターン（無改造で再利用）:**
```python
# Source: pagefolio/ui_builder.py:189-200
def _show_error_or_toast(self, category, title, msg, retry_cb):
    """トースト表示 or messagebox フォールバックを一元化する（レビュー R2）。"""
    toast = getattr(self, "_toast", None)
    if toast is not None:
        toast.show(category, msg, retry_cb=retry_cb)
        return
    messagebox.showerror(title, msg)
```

```python
# Source: pagefolio/toast.py:40-55 (ToastManager.show — 無改造)
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
`ui_builder.py`/`toast.py` は D-11 で無改造。`retry_cb` に渡す callable の中身だけが変わる。

---

### `tests/test_toast.py`（test, request-response 振る舞い検証）

**Analog:** 同ファイル既存クラス `TestSaveFilePathsUseSharedHelper`（304-352行）

**書き換え対象の既存アサーション（オブジェクト等価性 → 振る舞いベースへ）:**
```python
# Source: tests/test_toast.py:310-352
def test_save_file_failure_shows_toast_with_retry(self, monkeypatch):
    monkeypatch.setattr(fo.messagebox, "askyesno", lambda *a, **k: True)
    toast = _RecordingToast()
    app = _FakeFileOpsApp(
        doc=_RaisingThenOkDoc(),
        toast=toast,
        filepath="test.pdf",
        overwrite_error=OSError("overwrite失敗"),
    )
    app._save_file()
    assert len(toast.shown) == 1
    category, msg, retry_cb = toast.shown[0]
    assert category == "save_file"
    assert "保存に失敗しました" in msg
    assert retry_cb == app._save_file          # ← D-11 適用後は破壊されるアサーション（327行）

def test_save_as_failure_then_success_dismisses(self, monkeypatch, tmp_path):
    ...
    app._save_as()  # 1回目: 失敗
    assert toast.shown[-1][0] == "save_as"
    assert toast.shown[-1][2] == app._save_as   # ← 破壊されるアサーション（338行）
    app._save_as()  # 2回目: 成功 → dismiss
    assert toast.dismissed[-1] == "save_as"

def test_save_compressed_failure_shows_toast(self, monkeypatch, tmp_path):
    ...
    app._save_compressed()
    assert toast.shown[-1][0] == "save_compressed"
    assert toast.shown[-1][2] == app._save_compressed  # ← 破壊されるアサーション（352行）
```
**推奨改修方針:** `retry_cb == app._save_file` のようなオブジェクト等価性を、「`retry_cb()` を呼んだときに `askyesno`/`asksaveasfilename` が再度呼ばれないこと」を検証するモンキーパッチ済みスパイへ置き換える（`monkeypatch.setattr(fo.messagebox, "askyesno", <呼ばれたら fail するダミー>)` を `retry_cb()` 呼び出し直前に差し替える等）。既存の `_RecordingToast`/`_FakeFileOpsApp`/`_RaisingThenOkDoc` フィクスチャ構造はそのまま流用可能。

---

### `tests/conftest.py`（V190-QA-01 修復コード置き場・D-06、config/fixture, batch）

**Analog:** 同ファイル既存 fixture 群

```python
# Source: tests/conftest.py:14-90 概要（既存 fixture シグネチャ）
@pytest.fixture()
def tmp_settings(tmp_path): ...

@pytest.fixture()
def sample_pdf(tmp_path): ...

@pytest.fixture()
def sample_pdf_doc(): ...

@pytest.fixture()
def large_pdf_doc(): ...

@pytest.fixture()
def multi_pdf_files(tmp_path): ...
```
D-05/D-06 により「再現しなければコード変更ゼロ」が第一候補。もし D-03 の仮説検証の結果、テスト側に環境修復コード（例: `--basetemp` の固定化、`autouse` fixture でのクリーンアップ強化）が必要になった場合は、上記と同じ `@pytest.fixture()` デコレータ・関数命名規則（`snake_case`・docstring 冒頭に一文要約）に揃えること。**製品コード（`pagefolio/`）へは触れない**のが原則（D-06）。

---

### `pagefolio/constants.py`（`APP_VERSION` バンプ・D-16、config, transform）

**Analog:** 同ファイル 12行目自身
```python
# Source: pagefolio/constants.py:12
APP_VERSION = "v1.8.1"
```
→ `"v1.9.0"` へ更新。CLAUDE.md により README.md のバッジ・開発履歴.md の最新エントリと3点同期が必須（D-16）。

---

## Shared Patterns

### 保存失敗時のトースト/メッセージボックス振り分け
**Source:** `pagefolio/ui_builder.py:189-200`（`_show_error_or_toast`）
**Apply to:** `_save_file`/`_save_as`/`_save_compressed` の分離後もすべて同じ入口を通す。無改造。

### 実処理層（path 引数を取る・Tk 非依存）の切り出し
**Source:** `pagefolio/file_ops.py:1102-1132`（`_overwrite_current_file`）
**Apply to:** `_save_file`/`_save_as`/`_save_compressed` 3経路すべて（D-11）。命名は `_do_save_file(path)` / `_do_save_as(path)` / `_do_save_compressed(path, save_kwargs)` 等（Discretion）。

### 暗号化維持（Phase 1 の既存回帰防止）
**Source:** `pagefolio/file_ops.py:1117`（`save_kwargs.setdefault("encryption", fitz.PDF_ENCRYPT_KEEP)`）、`tests/test_password.py` の既存テスト
**Apply to:** D-11 の分離実装後も `tests/test_password.py` をフルスイートに含めて green を維持すること（`test_save_as_keeps_encryption` 等）。

### バージョン文書3点同期
**Source:** `pagefolio/constants.py:12`（`APP_VERSION`）を単一情報源として README.md バッジ・開発履歴.md 最新エントリを同期（CLAUDE.md 既定ルール）
**Apply to:** D-16 の作業。

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `03-UAT-RESULTS.md`（新規） | doc | batch | プロジェクト内に厳密な同型フォーマットは存在しないが、Phase 2 の human-verify 3分割実施記録の構成（項目・手順・合否）を雛形として踏襲する（D-15 が明示） |
| 調査レポート（テスト環境切り分けログ、新規） | doc | event-driven | 専用の調査レポート雛形は過去フェーズに存在しないが、`.planning/STATE.md`「Blockers/Concerns」の記述形式（症状・検証手法・反証データ）を踏襲する |

## Metadata

**Analog search scope:** `pagefolio/file_ops.py`, `pagefolio/ui_builder.py`, `pagefolio/toast.py`, `pagefolio/constants.py`, `tests/test_toast.py`, `tests/conftest.py`
**Files scanned:** 6（RESEARCH.md が既に本セッションで全文読解済みのため重複読解を回避し、差分検証のみ実施）
**Pattern extraction date:** 2026-08-11
