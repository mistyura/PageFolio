# Phase 1: APIキー入力欄（LLM設定への一元化） - Pattern Map

**Mapped:** 2026-07-05
**Files analyzed (create/modify):** 6
**Analogs found:** 6 / 6（本フェーズは新規ファイル追加なし・全て既存ファイルの内部修正）

## File Classification

| Modified File | Role | Data Flow | Closest Analog (in same file / sibling) | Match Quality |
|----------------|------|-----------|-------------------------------------------|---------------|
| `pagefolio/ocr.py`（`_resolve_api_key`） | service（純関数・Tk非依存） | request-response（呼び出し元へキー文字列を返す/raise） | 同関数の現行実装そのもの（`ocr.py:209-266`） | exact（分岐の順序入替のみ） |
| `pagefolio/dialogs/llm_config.py`（`LLMConfigDialog`） | component（Tkinter ダイアログ・UI 構築） | CRUD（設定値の表示・入力・適用） | 同ファイル内の既存「モデル選択行」パターン（`claude_model_row`/`gemini_model_row`、:366-431）・既存 `_apply()`（:1121） | exact（同ファイル内の並行パターン） |
| `pagefolio/ocr_dialog.py`（撤去 + `_check_cloud_api_key` 新設） | controller/component（実行前ゲート） | request-response | 撤去対象そのもの: `_needs_session_key`（:834）/`_ensure_cloud_session_key`（:1128）/`_key_frame`（:472,1041）/`api_key_var`（:117,485） | exact（置換元が同ファイル内に実在） |
| `pagefolio/app.py`（`_open_settings` 引数追加） | controller（アプリ状態からダイアログへの配線） | request-response | 同メソッド既存呼び出し（:475-481、`plugin_manager=` 渡しパターン） | exact |
| `pagefolio/dialogs/settings.py`（`SettingsDialog.__init__`/`_open_llm_config`） | component（中継ダイアログ） | request-response | 同ファイル既存 `current_settings` 保持・`_open_llm_config`（:162-198）のコピー渡しパターン | exact |
| `pagefolio/lang.py`（新規/更新キー） | config（言語辞書） | CRUD（キー追加・キー更新） | 既存 `ocr_api_key_missing` / `ocr_api_key_missing_gemini`（:397-401, 425-429・en側 :952, 980） | exact |

## Pattern Assignments

### `pagefolio/ocr.py` — `_resolve_api_key` 優先順反転（service, request-response）

**Analog:** 関数自身の現行実装

**現行コード**（`pagefolio/ocr.py:209-266`、変更前）:
```python
def _resolve_api_key(provider_name, session_keys):
    import os
    from pagefolio.ocr_providers import OCRAPIKeyError

    if provider_name == "claude":
        env_var = "ANTHROPIC_API_KEY"
        key = os.environ.get(env_var)          # 現行: 環境変数が先
        if key:
            return key
        key = session_keys.get("claude", "")
        if key:
            return key
        raise OCRAPIKeyError(env_var)

    if provider_name == "gemini":
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if key:
            return key
        key = session_keys.get("gemini", "")
        if key:
            return key
        raise OCRAPIKeyError("GEMINI_API_KEY")

    if provider_name == "runpod":
        env_var = "RUNPOD_API_KEY"
        key = os.environ.get(env_var)
        if key:
            return key
        key = session_keys.get("runpod", "")
        if key:
            return key
        raise OCRAPIKeyError(env_var)

    raise OCRAPIKeyError(f"{provider_name.upper()}_API_KEY")
```

**変更方針:** 各分岐内の「環境変数チェック」と「セッションキーチェック」の**呼び出し順序を入れ替えるだけ**（gemini の dual env var 内部順序 `GEMINI_API_KEY` → `GOOGLE_API_KEY` はそのまま維持）。docstring の「優先順位: 環境変数 > セッションキー（D-02）」も「セッションキー(入力値) > 環境変数」へ修正すること。関数シグネチャ・呼び出し元（`build_provider`・`ocr_dialog.py` 各所）は無変更で済む。

**Error handling pattern:** `OCRAPIKeyError(env_var)` を raise（`pagefolio/ocr_providers.py` 定義・`env_var` 属性を持つ）。呼び出し元は `except OCRAPIKeyError:` で捕捉し `messagebox.showerror` へ橋渡しする（下記 `_check_cloud_api_key` 参照）。

---

### `pagefolio/dialogs/llm_config.py` — プロバイダ別 APIキー入力欄追加（component, CRUD）

**Analog:** 同ファイル内の既存「モデル選択行」パターン（claude セクション例）

**Imports パターン**（ファイル先頭・変更不要、`os` は既にトップレベルで import 済みか要確認。無ければ関数内 `import os` で局所追加）:
既存コードは `os.environ.get(...)` を `_refresh_runpod_models` などで既に使用しているため、モジュールトップに `import os` が存在する可能性が高い。存在しない場合は他プロバイダ同様にローカル import で揃える。

**Core パターン — claude モデル行**（`pagefolio/dialogs/llm_config.py:363-397`、これを APIキー行のテンプレートにする）:
```python
self.claude_section_frame = tk.Frame(self, bg=C["BG_DARK"])

claude_model_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
claude_model_row.pack(fill="x", padx=0, pady=2)
tk.Label(
    claude_model_row,
    text=self._L["settings_lm_model"],
    bg=C["BG_DARK"], fg=C["TEXT_MAIN"], font=self._font(-1),
    width=20, anchor="w",
).pack(side="left")
self.claude_model_var = tk.StringVar(
    value=self.current_settings.get("claude_model", "claude-sonnet-4-6"),
)
self.claude_model_combo = ttk.Combobox(
    claude_model_row, textvariable=self.claude_model_var,
    font=self._font(-1), values=ClaudeProvider.RECOMMENDED_MODELS,
)
self.claude_model_combo.pack(side="left", fill="x", expand=True, padx=4)
self.claude_model_combo.bind("<<ComboboxSelected>>", self._on_model_change)

claude_btn_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
claude_btn_row.pack(fill="x", padx=0, pady=(4, 2))
ttk.Button(
    claude_btn_row, text=self._L["ocr_model_refresh"],
    command=self._refresh_claude_models,
).pack(side="left", padx=2)
```
→ 同じ `width=20, anchor="w"` ラベル + `pack(side="left", fill="x", expand=True, padx=4)` 入力ウィジェットの行構成で、モデル行の**直後**（Open Question 1 の推奨どおり）に APIキー行を追加する。gemini（:399-431）・runpod（:295-354）も同型で3セクションに複製する。

**新規要素の具体コード**（RESEARCH.md Pattern 2 から転記・そのまま採用可）:
```python
self._session_api_keys = session_api_keys if session_api_keys is not None else {}

claude_key_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
claude_key_row.pack(fill="x", padx=0, pady=2)
tk.Label(
    claude_key_row, text=self._L["llm_api_key_label"],
    bg=C["BG_DARK"], fg=C["TEXT_MAIN"], font=self._font(-1),
    width=20, anchor="w",
).pack(side="left")
self.claude_api_key_var = tk.StringVar(
    value=self._session_api_keys.get("claude", "")
)
self.claude_api_key_entry = tk.Entry(
    claude_key_row, show="*", textvariable=self.claude_api_key_var,
    font=self._font(-1), bg=C["BG_CARD"], fg=C["TEXT_MAIN"],
    insertbackground=C["TEXT_MAIN"], relief="flat",
)
self.claude_api_key_entry.pack(side="left", fill="x", expand=True, padx=4)
self._claude_key_shown = False
def _toggle_claude_key():
    self._claude_key_shown = not self._claude_key_shown
    self.claude_api_key_entry.configure(show="" if self._claude_key_shown else "*")
ttk.Button(
    claude_key_row, text=self._L["llm_key_toggle"], width=4,
    command=_toggle_claude_key,
).pack(side="left", padx=(2, 0))

note = self._L["llm_key_session_note"]
if os.environ.get("ANTHROPIC_API_KEY"):
    note += " " + self._L["llm_key_env_set_note"].format(env_var="ANTHROPIC_API_KEY")
tk.Label(
    self.claude_section_frame, text=note,
    bg=C["BG_DARK"], fg=C["TEXT_SUB"], font=self._font(-2),
    wraplength=460, justify="left",
).pack(anchor="w", pady=(0, 2))
```
gemini は `GEMINI_API_KEY`（+ `GOOGLE_API_KEY` フォールバック表示は D-07 の対象外＝単一env名表示で可）、runpod は `RUNPOD_API_KEY` に置き換えて同型を複製。

**`_apply()` への追記パターン**（`pagefolio/dialogs/llm_config.py:1121-1170` の既存収集ロジックに続けて追加）:
```python
for provider_key, var in (
    ("claude", self.claude_api_key_var),
    ("gemini", self.gemini_api_key_var),
    ("runpod", self.runpod_api_key_var),
):
    key = var.get().strip()
    if key:
        self._session_api_keys[provider_key] = key
    else:
        self._session_api_keys.pop(provider_key, None)
```
**重要:** `llm_settings` dict（:1128 以降で構築される辞書、`on_apply(llm_settings)` に渡る）には `api_key` 系を一切追加しないこと（既存の `claude_model`/`ocr_effort` 等の無害な設定値パターンのみに追記対象を限定する）。

**`_refresh_claude_models` のライブ値優先解決（D-10）** — 現行実装（`pagefolio/dialogs/llm_config.py:1047` 付近、`os.environ.get("ANTHROPIC_API_KEY", "")` 直接参照部分）を以下へ変更:
```python
api_key = self.claude_api_key_var.get().strip() or os.environ.get(
    "ANTHROPIC_API_KEY", ""
)
```
`_refresh_gemini_models`（:1083）・`_refresh_runpod_models`（:1017、現行 `os.environ.get("RUNPOD_API_KEY")` 直接参照 — RESEARCH.md 記載の「既知ギャップ」箇所）も同型で `self.gemini_api_key_var` / `self.runpod_api_key_var` を参照するよう変更。

---

### `pagefolio/ocr_dialog.py` — 旧セッションキー UI 撤去 + `_check_cloud_api_key` 新設（controller, request-response）

**撤去対象（読解済み・実在確認済み）:**
| 要素 | 行番号 | 内容 |
|------|--------|------|
| `self.api_key_var = tk.StringVar()` | :117 | フィールド初期化 |
| `self._key_frame = tk.Frame(...)` + `pack()`条件分岐 | :472-485 | 入力欄フレーム構築 |
| `_needs_session_key()` | :834-855 | env変数未設定判定（claude/gemini/runpod 3分岐だが値収集ではなく表示要否判定のみ） |
| `_key_frame.pack()/.pack_forget()` 再表示ロジック | :1041-1046 | プロバイダ切替時の表示更新 |
| `_ensure_cloud_session_key()` | :1128-1162 | 値収集 + claude/gemini 2分岐のみ（runpod 誤格納バグの実体） |
| 呼び出し箇所 | :1187, :1868 | `_on_run`/`_on_summary` 内のゲート |

**置換後（新設 `_check_cloud_api_key`）:**
```python
def _check_cloud_api_key(self):
    """クラウド実行前に APIキーが解決可能か確認する（成功基準2・撤去後の代替）。

    入力 UI は LLMConfigDialog に一元化されたため、この関数は値の収集を
    一切行わず _resolve_api_key の解決可否のみを確認する。
    """
    if not self._is_cloud_provider():
        return True
    from pagefolio.ocr import _resolve_api_key
    from pagefolio.ocr_providers import OCRAPIKeyError

    name = self.app.settings.get("ocr_provider", "")
    session_keys = getattr(self.app, "_session_api_keys", {})
    try:
        _resolve_api_key(name, session_keys)
    except OCRAPIKeyError:
        msg_key = {
            "claude": "ocr_api_key_missing",
            "gemini": "ocr_api_key_missing_gemini",
            "runpod": "ocr_api_key_missing_runpod",  # 新設要
        }.get(name, "ocr_api_key_missing")
        env_var = {
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "runpod": "RUNPOD_API_KEY",
        }.get(name, "")
        messagebox.showerror(
            self._L["err_title"],
            self._L[msg_key].format(env_var=env_var),
            parent=self,
        )
        return False
    return True
```
呼び出し側は `_on_run`（:1187）と `_on_summary`（:1868）の `self._ensure_cloud_session_key()` を `self._check_cloud_api_key()` へ**メソッド名差し替えのみ**で対応。

**`_open_llm_config` は撤去対象外**（:859-880 付近、二重起動ガードのロジックは維持。`LLMConfigDialog(...)` 呼び出し引数に `session_api_keys=self.app._session_api_keys` を1行追加するのみ）:
```python
# 既存の LLMConfigDialog(...) 呼び出しに引数を1つ追加
LLMConfigDialog(
    self,  # or self.app.root 等・既存の第1引数はそのまま
    ...,
    session_api_keys=self.app._session_api_keys,
)
```

**エラー表示パターン（既存踏襲）:** `messagebox.showerror(self._L["err_title"], self._L[msg_key].format(env_var=env_var), parent=self)` — 既存 `_ensure_cloud_session_key` 内の呼び出し形をそのまま踏襲。

---

### `pagefolio/app.py` — `_open_settings` への `session_api_keys` 配線（controller, request-response）

**Analog:** 同メソッドの既存 `plugin_manager=` キーワード引数渡しパターン

**現行コード**（`pagefolio/app.py:461-481`）:
```python
def _open_settings(self):
    existing = getattr(self, "_settings_dialog", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return
    self._settings_dialog = SettingsDialog(
        self.root,
        self.settings,
        self._apply_settings,
        self._font,
        plugin_manager=getattr(self, "plugin_manager", None),
    )
```
**変更方針:** `SettingsDialog(...)` 呼び出しに `session_api_keys=self._session_api_keys` を追加するのみ（`self._session_api_keys` は `app.py:81` で既に `{}` 初期化済み）。dict は複製せず参照をそのまま渡すこと（RESEARCH.md Pattern 3 の注意点）。

---

### `pagefolio/dialogs/settings.py` — `SettingsDialog` の中継配線（component, request-response）

**Analog:** 同ファイルの `current_settings` 保持・`_open_llm_config`（:162-198）のコピー/コールバック渡しパターン

**現行コード**（`pagefolio/dialogs/settings.py:19-31, 162-198`）:
```python
def __init__(
    self, parent, current_settings, callback, font_func=None, plugin_manager=None
):
    ...
    self.current_settings = dict(current_settings)
    ...

def _open_llm_config(self):
    """適用時に current_settings を更新する。"""
    lang = self.current_settings.get("lang", "ja")
    ...
    # LLMConfigDialog(...) 呼び出し（引数は既存 current_settings ベース）
```
**変更方針:**
1. `__init__` シグネチャに `session_api_keys=None` を追加し `self._session_api_keys = session_api_keys if session_api_keys is not None else {}` として保持（`current_settings` は `dict(...)` で複製するのに対し、`session_api_keys` は**複製しない**＝参照をそのまま保持する点に注意。複製すると `app._session_api_keys` の実体に反映されなくなる）。
2. `_open_llm_config` 内の `LLMConfigDialog(...)` 呼び出しに `session_api_keys=self._session_api_keys` を追加。

---

### `pagefolio/lang.py` — 新規/更新文言（config, CRUD）

**Analog:** 既存 `ocr_api_key_missing` / `ocr_api_key_missing_gemini` キー（ja: :397-401, 425-429／en: :952, 980）

**現行 ja コード**（変更対象・D-08 の文言更新元）:
```python
"ocr_api_key_missing": (
    "APIキーが設定されていません（{env_var}）。"
    "環境変数を設定するか、入力欄にキーを入力してください。"
),
...
"ocr_api_key_missing_gemini": (
    "Gemini APIキーが設定されていません。"
    "環境変数 GEMINI_API_KEY（または GOOGLE_API_KEY）を設定するか、"
    "入力欄にキーを入力してください。"
),
```
**新規キー（ja/en 同時追加、キー数一致を維持）:**
- `ocr_api_key_missing_runpod`（新設・RunPod 用。既存 `ocr_api_key_missing`/`_gemini` と対の命名規則）
- `llm_api_key_label`（Pattern 2 のラベル文言、例:「APIキー:」）
- `llm_key_toggle`（トグルボタン文言、例:「👁 表示」/D-02）
- `llm_key_session_note`（D-03 の小注記本文、例:「※ セッション限定（アプリ終了で破棄・設定ファイルには保存されません）」）
- `llm_key_env_set_note`（D-07 の動的追記、`{env_var}` プレースホルダ、例:「環境変数 {env_var} 設定済み（ここで入力した値が優先されます）」）
- `llm_env_key_unset_static`（D-11 のヒント、既存 `_refresh_claude_models` フォールバック文言と整合する形で追加/流用）

**更新（D-08）:** `ocr_api_key_missing` / `ocr_api_key_missing_gemini` の文言に「LLM設定ダイアログで APIキーを入力するか」という導線案内を追加する形へ書き換える（環境変数名の案内はそのまま維持）。ja/en 両方を同時に更新すること。

**注意:** `tests/test_lang_parity.py` が ja/en のキー集合一致を自動検証するため、追加は必ず両言語同時に行う。

---

## Shared Patterns

### 非保存ガード（`_SENSITIVE_KEYS`）
**Source:** `pagefolio/settings.py:17-28, 89-101`
**Apply to:** `llm_config.py` の `_apply()`・`app.py`/`dialogs/settings.py` の設定保存経路すべて
```python
_SENSITIVE_KEYS = {
    "claude_api_key", "gemini_api_key", "google_api_key", "anthropic_api_key",
    "api_key", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY",
    "runpod_api_key", "RUNPOD_API_KEY",
}
```
本フェーズはこのセットへの変更不要（`llm_settings` dict に API キーを含めない設計を維持するだけで、この関数は最後の砦として機能する）。

### セッションキー保管の単一の真実源
**Source:** `pagefolio/app.py:81`（`self._session_api_keys = {}`）
**Apply to:** `llm_config.py`（書込み元）・`ocr.py::_resolve_api_key`（読取り）・`ocr_dialog.py::_check_cloud_api_key`（読取り）
プロセスメモリ内 dict をそのまま参照渡しで共有する。複製しないこと。

### キー解決の単一関数集約
**Source:** `pagefolio/ocr.py:209 _resolve_api_key`
**Apply to:** `ocr_dialog.py::_check_cloud_api_key`・将来のプロバイダ生成コード（`build_provider`）
UI 層・実行ゲート層はいずれもこの関数を呼ぶのみで、優先順ロジックを再実装しない。

### エラー表示パターン
**Source:** `pagefolio/ocr_dialog.py`（撤去前の `_ensure_cloud_session_key` 内 `messagebox.showerror` 呼び出し）
**Apply to:** `_check_cloud_api_key`
```python
messagebox.showerror(self._L["err_title"], self._L[msg_key].format(env_var=env_var), parent=self)
```

### LANG 追加の作法
**Source:** `pagefolio/lang.py`（ja/en 並行辞書構造）
**Apply to:** 新規キー全て
ja/en 同一キー名・同時追加。`tests/test_lang_parity.py` が自動検証。

## No Analog Found

該当なし（本フェーズは新規ファイルを一切作成せず、全修正が既存ファイル内の並行パターン・同一関数の改修に閉じるため）。

## Test Pattern Notes（PATTERNS ではなく既存テスト構造の参照・planner向け補足）

- `tests/test_ocr.py:531-577 TestResolveApiKey`・`:1083-1131 TestResolveApiKeyGemini` — 優先順反転に伴い**書き換え必須**（新規追加ではない）。同型で `TestResolveApiKeyRunPod` を新設。
- `tests/test_provider_ui.py:184-375 _make_dialog_stub` / `TestNeedsSessionKey` — `_needs_session_key` 撤去に伴い削除必須。後継 `TestCheckCloudApiKey`（仮称）を新設。
- `tests/test_settings_keyguard.py` — 変更不要（既存カバレッジで新規キーも自動検証される非保存ガード）。

## Metadata

**Analog search scope:** `pagefolio/ocr.py`, `pagefolio/dialogs/llm_config.py`, `pagefolio/ocr_dialog.py`, `pagefolio/app.py`, `pagefolio/dialogs/settings.py`, `pagefolio/lang.py`, `pagefolio/settings.py`
**Files scanned:** 7（対象修正ファイル自身が最良のアナログであるため、外部ディレクトリ探索は不要と判断）
**Pattern extraction date:** 2026-07-05
