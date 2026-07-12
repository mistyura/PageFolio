# Phase 1: APIキー入力欄（LLM設定への一元化） - Research

**Researched:** 2026-07-05
**Domain:** Tkinter デスクトップアプリ内のシークレット入力 UI 一元化 + 優先順反転（内部リファクタリング、外部ライブラリ追加なし）
**Confidence:** HIGH（全知見が既存コードの直接読解による VERIFIED。外部ライブラリ調査は不要な純内部フェーズ）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** キー入力欄は既存のプロバイダ別セクションフレーム（`claude_section_frame` / `gemini_section_frame` / `runpod_section_frame`）内に各 1 欄追加する。選択中プロバイダの欄だけが見える（既存の `_on_provider_change` セクション切替ロジックを活用・ダイアログ縦長化を最小化）。
- **D-02:** 入力欄は常時マスク（`tk.Entry(show="*")`）とし、横に「👁 表示」トグルボタンを置いて平文確認を可能にする（OCRDialog 既存キー欄の show="*" を踏襲しつつ確認性を追加）。
- **D-03:** 入力欄の直下に TEXT_SUB 色の小注記を表示する：「※ セッション限定（アプリ終了で破棄・設定ファイルには保存されません）」。LANG の ja/en 両辞書へ同一キーで追加。
- **D-04:** 入力キーは OK（適用）押下時に `app._session_api_keys` へ直接格納する。`on_apply` に渡す `llm_settings` dict には**含めない**（settings 流入ガード T-05-12 を構造的に維持）。キャンセルで閉じれば反映されない。
- **D-05:** ダイアログ再オープン時は `_session_api_keys` の既存値をマスク付きでプリフィル表示する（設定済みが一目で分かる・上書き/削除も自然）。
- **D-06:** クリアは「欄を空にして OK」で `_session_api_keys` から削除（以降は環境変数へフォールバック）。専用クリアボタンは設けない。
- **D-07:** 環境変数が設定済みの場合、D-03 の小注記に動的追記する：「環境変数 <ENV名> 設定済み（ここで入力した値が優先されます）」。独立ステータス行は追加しない。
- **D-08:** 両方未設定でクラウド OCR を実行したときのエラー文言を「LLM設定ダイアログで APIキーを入力するか、環境変数 <ENV名> を設定してください」へ更新する（ja/en 両辞書・一元化導線の案内）。
- **D-09:** キー未設定エラー時に LLMConfigDialog を自動オープンしない。文言での誘導のみ（OCRDialog の既存「⚙ LLM 設定…」ボタンで到達可能）。
- **D-10:** LLMConfigDialog 内のモデル一覧取得ボタン（`_refresh_claude_models` / `_refresh_gemini_models` / `_refresh_runpod_models`）は「ダイアログ入力欄のライブ値（OK 前でも）→ 環境変数」の順で解決する。入力直後にその場でモデル取得＝キーの疎通確認ができる。
- **D-11:** モデル取得時にキーがどこにもない場合は現行の静的推奨モデルフォールバック（D-08 系）を維持しつつ、セクション内に「APIキー未設定のため推奨モデル一覧を表示中」のヒントを表示する。

### Claude's Discretion

- 入力欄行のレイアウト詳細（ラベル幅・トグルボタンの文言/アイコン・pack 順）は既存セクションの行構成に合わせて実装時に判断。
- `_resolve_api_key` の優先順反転の実装形（引数追加 or 内部順序入替）と、OCRDialog 撤去に伴う `_needs_session_key` / `_ensure_cloud_session_key` / `_key_frame` の削除・簡素化の範囲は planner/executor 判断。ただし読み取り専用原則（os.environ 書き込み禁止）は維持。

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope（OS キーストア永続化・OAuth は REQUIREMENTS.md の Out of Scope に記載済み）

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V171-KEY-01 | LLM設定ダイアログで Claude/Gemini/RunPod の APIキーを入力でき、`settings.json` へ非永続 | `## Architecture Patterns` Pattern 1（3 セクションへの入力欄追加）・Pattern 2（`_session_api_keys` への直接格納で T-05-12 ガード維持）。既存 `_SENSITIVE_KEYS` ガード（`pagefolio/settings.py:17`）は変更不要 |
| V171-KEY-02 | キー解決順を「入力値→環境変数」へ反転、両方未設定はエラー | `## Common Pitfalls` Pitfall 1・`## Code Examples` の `_resolve_api_key` 反転案。既存 `_ensure_cloud_session_key` の代替関数案（Pitfall 2） |
| V171-KEY-03 | OCRDialog の旧セッションキー入力欄撤去・導線一元化 | `## Architecture Patterns` Pattern 3（撤去対象コード地図）。`## Common Pitfalls` Pitfall 3（撤去に伴うテスト破棄） |
| V171-KEY-04 | RunPod も `_session_api_keys` 機構で扱える | `## Common Pitfalls` Pitfall 1（現行の runpod→claude スロット混入バグの実体）。RunPod 用エラー文言・テストの新設が必要（Pitfall 4） |
| V171-TEST-02 | 優先順解決・非保存ガードの回帰テスト整備 | `## Validation Architecture` の Phase Requirements → Test Map。既存 `TestResolveApiKey`/`TestResolveApiKeyGemini`（`tests/test_ocr.py`）の書き換え + RunPod 用新規クラス追加 + `TestNeedsSessionKey`（`tests/test_provider_ui.py`）の削除 |

</phase_requirements>

## Summary

本フェーズは新規ライブラリを一切導入しない**純粋な内部リファクタリング**である。対象は3ファイル（`pagefolio/ocr.py` の `_resolve_api_key`、`pagefolio/dialogs/llm_config.py` の `LLMConfigDialog`、`pagefolio/ocr_dialog.py` の旧セッションキー UI）に閉じており、`pagefolio/settings.py` の `_SENSITIVE_KEYS` 非保存ガードと `pagefolio/app.py` の `_session_api_keys` 辞書はそのまま再利用できる。

コード調査で3つの重要な事実が判明した。(1) 現行の `_resolve_api_key`（`pagefolio/ocr.py:209`）は claude/gemini/runpod の3プロバイダに既に対応済みで、優先順序（環境変数→セッションキー）を単純に入れ替えるだけで V171-KEY-02 の中核要件を満たせる。(2) `pagefolio/ocr_dialog.py` の `_ensure_cloud_session_key`（:1128）は claude/gemini の2分岐しかなく、runpod 選択時は誤って `_session_api_keys["claude"]` へキーを格納する構造的バグがあり、これが V171-KEY-04 の実体である。撤去することでこのバグ自体は解消するが、代替として「クラウド実行前に鍵が解決可能かだけを確認しエラー表示する」軽量関数が必要（入力 UI 自体は LLMConfigDialog に移るため、値の収集は不要）。(3) `LLMConfigDialog` は `pagefolio/ocr_dialog.py` と `pagefolio/dialogs/settings.py` の2箇所から呼ばれており、後者は `app` インスタンスではなく `SettingsDialog` 経由のため、`_session_api_keys` 辞書への到達経路を新たに設計・配線する必要がある（`PDFEditorApp._open_settings` → `SettingsDialog.__init__` → `SettingsDialog._open_llm_config` → `LLMConfigDialog.__init__` の4段階）。

**Primary recommendation:** `_resolve_api_key` の解決順を反転し、`LLMConfigDialog` に3セクション共通パターンで claude/gemini/runpod 用のマスク付き入力欄を追加、`_session_api_keys` 辞書参照を2つの呼び出し経路（OCRDialog 経由・SettingsDialog 経由）両方に配線し、OCRDialog 側の `_needs_session_key`/`_ensure_cloud_session_key`/`_key_frame`/`api_key_var` を撤去して軽量な鍵存在チェック関数に置換する。既存の env優先を検証するテスト群（`TestResolveApiKey`/`TestResolveApiKeyGemini`）は**新規追加ではなく書き換え**が必要な点に注意。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| APIキー入力 UI（マスク・トグル・注記） | Frontend (Tkinter Dialog) | — | `LLMConfigDialog` は UI 専用クラス。値の永続化判断は持たない |
| キー解決優先順ロジック | Application/Domain (ocr.py) | — | `_resolve_api_key` は Tk 非依存の純関数で、UI からもプロバイダ生成からも共有される単一の真実源 |
| セッションキー保管 | Application State (app.py) | — | `PDFEditorApp._session_api_keys` はプロセスメモリ内のみ・アプリ終了で破棄（永続化層には一切触れない） |
| 非永続化ガード | Persistence (settings.py) | — | `_SENSITIVE_KEYS` は `_save_settings` 内の構造的フィルタ。UI 側が誤って含めても最後の砦として機能 |
| クラウド OCR 実行ゲート | Application (ocr_dialog.py) | Frontend（エラーダイアログ表示） | 実行直前に `_resolve_api_key` を呼び、解決不能なら UI にエラーを出して中断する橋渡し役 |

## Standard Stack

本フェーズは新規パッケージを導入しない。既存スタック（`pyproject.toml`・`requirements.txt` に固定済み）をそのまま使用する。

| Library | Version | Purpose | Provenance |
|---------|---------|---------|--------------|
| Python | 3.8+ | 実行環境 | [VERIFIED: CLAUDE.md] |
| Tkinter (`tkinter`/`tkinter.ttk`) | 標準ライブラリ | `LLMConfigDialog`/`OCRDialog` の UI 部品（`tk.Entry(show="*")` 含む） | [VERIFIED: pagefolio/dialogs/llm_config.py, pagefolio/ocr_dialog.py] |
| pytest | 9.0.2 | 回帰テスト実行（V171-TEST-02） | [VERIFIED: requirements.txt] |
| ruff | 0.15.7 | リント（CLAUDE.md 必須コマンド） | [VERIFIED: requirements.txt] |

**インストールコマンド:** なし（新規依存ゼロ）。

**バージョン検証:** `requirements.txt` に全バージョンが固定済み。本フェーズでの追加・変更は不要。

## Package Legitimacy Audit

**該当なし** — 本フェーズは新規外部パッケージを一切インストールしない（既存 `requirements.txt` の変更なし）。Package Legitimacy Gate はスキップする。

## Architecture Patterns

### System Architecture Diagram

```text
[ユーザー入力]
   │
   ├─▶ LLMConfigDialog（claude/gemini/runpod 各セクション内の APIキー欄）
   │       │  (OK 押下時)
   │       ├─▶ llm_settings dict（api_key 系キーは含めない・既存 _apply() ガード維持）
   │       │       └─▶ on_apply(llm_settings) ─▶ app.settings.update(...) ─▶ _save_settings()
   │       │                                                                    │
   │       │                                                            [_SENSITIVE_KEYS フィルタ]
   │       │                                                                    ▼
   │       │                                                          pagefolio_settings.json
   │       │                                                          （APIキーは書き込まれない）
   │       │
   │       └─▶ app._session_api_keys[provider] = key（dict 直接書込み・settings 経由しない）
   │
   ├─▶ [モデル一覧取得ボタン] ──▶ ライブ Entry 値 → (未入力なら) os.environ ──▶ list_models()
   │
   └─▶ [OCR 実行 / サマリ生成]（OCRDialog._on_run / _on_summary）
           │
           ├─▶ _is_cloud_provider() で分岐
           │
           ├─▶ (新設) _check_cloud_api_key()
           │       └─▶ _resolve_api_key(name, app._session_api_keys)
           │               ├─ 入力値あり → 返す（優先順反転の核心）
           │               ├─ 環境変数あり → 返す（フォールバック）
           │               └─ どちらもなし → OCRAPIKeyError → messagebox エラー表示 → 中断
           │
           └─▶ build_provider(settings, api_key=resolved_key) ──▶ ClaudeProvider/GeminiProvider/RunPodProvider
                                                                        │
                                                                        └─▶ https 外部 API 呼び出し
```

### Recommended Project Structure

ファイル追加なし。既存ファイルの内部修正のみ。

```
pagefolio/
├── ocr.py                 # _resolve_api_key の優先順反転（他は変更不要）
├── dialogs/
│   └── llm_config.py       # claude/gemini/runpod 各セクションへ APIキー欄追加・
│                           #   _refresh_*_models のライブ値優先解決・
│                           #   session_api_keys 受け渡し・_apply() での格納処理
├── ocr_dialog.py           # 旧セッションキー UI（_key_frame/api_key_var/
│                           #   _needs_session_key/_ensure_cloud_session_key）撤去・
│                           #   軽量な _check_cloud_api_key() へ置換
├── app.py                  # _open_settings で session_api_keys を SettingsDialog へ渡す
├── dialogs/settings.py     # session_api_keys を受け取り LLMConfigDialog へ中継
└── lang.py                 # 新規/更新文言（D-03/D-07/D-08 系）を ja/en 両方へ
```

### Pattern 1: `_resolve_api_key` の優先順反転（V171-KEY-02 の核心）

**What:** 既存の「環境変数 → セッションキー」を「セッションキー(入力値) → 環境変数」へ入れ替える。3プロバイダ全分岐（claude/gemini/runpod）に同じ変更を適用。gemini の dual env var（`GEMINI_API_KEY` 優先 `GOOGLE_API_KEY` フォールバック）自体の内部順序はそのまま維持し、あくまで「セッションキー vs 環境変数群」の優劣だけを反転する。

**When to use:** `_resolve_api_key` 内の3分岐すべて。

**Example:**
```python
# Source: pagefolio/ocr.py:209 の現行実装からの改修案
def _resolve_api_key(provider_name, session_keys):
    """優先順位: 入力値(session_keys) > 環境変数（V171-KEY-02・優先順反転）。

    注意: os.environ への書き込みは一切行わない（読み取り専用原則は維持）。
    """
    import os
    from pagefolio.ocr_providers import OCRAPIKeyError

    if provider_name == "claude":
        env_var = "ANTHROPIC_API_KEY"
        key = session_keys.get("claude", "")
        if key:
            return key
        key = os.environ.get(env_var)
        if key:
            return key
        raise OCRAPIKeyError(env_var)

    if provider_name == "gemini":
        key = session_keys.get("gemini", "")
        if key:
            return key
        # dual env var の内部優先順は不変（D-06 継承）
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if key:
            return key
        raise OCRAPIKeyError("GEMINI_API_KEY")

    if provider_name == "runpod":
        env_var = "RUNPOD_API_KEY"
        key = session_keys.get("runpod", "")
        if key:
            return key
        key = os.environ.get(env_var)
        if key:
            return key
        raise OCRAPIKeyError(env_var)

    raise OCRAPIKeyError(f"{provider_name.upper()}_API_KEY")
```
この関数は `pagefolio/ocr.py:775` (`_refresh_provider_dependent_ui`/build_provider 呼び出し元)、`pagefolio/ocr_dialog.py` の複数箇所（`_apply_llm_settings`・`_refresh_provider_frame` 相当・`_on_run`）から共通で呼ばれているため、**この1関数を直すだけで全呼び出し経路が一括で反転する**（CONTEXT.md の指摘どおり）。

### Pattern 2: LLMConfigDialog へのプロバイダ別 APIキー欄追加（V171-KEY-01/D-01/D-04/D-05）

**What:** `claude_section_frame` / `gemini_section_frame` / `runpod_section_frame`（`pagefolio/dialogs/llm_config.py:363,399,295`）はそれぞれ独立した `tk.Frame` で、`_on_provider_change` により選択中プロバイダのものだけが `pack()` される。この各フレーム内に既存の「モデル選択行」パターン（`tk.Label(width=20, anchor="w")` + 入力ウィジェット）を踏襲した APIキー行を追加する。

**When to use:** `_build()` 内、各セクションのモデル行の直後（モデル更新ボタン行の前 or 後、実装時判断）。

**Example:**
```python
# Source: pagefolio/dialogs/llm_config.py の既存パターン（claude_model_row 等）を踏襲
# __init__ 引数に session_api_keys=None を追加し、self._session_api_keys として保持
# （dict は複製せずそのまま参照を保持 — SettingsDialog 経由でも app 側の実体を書換えるため）
self._session_api_keys = session_api_keys if session_api_keys is not None else {}

# claude セクション内（他 gemini/runpod も同型で3回）
claude_key_row = tk.Frame(self.claude_section_frame, bg=C["BG_DARK"])
claude_key_row.pack(fill="x", padx=0, pady=2)
tk.Label(
    claude_key_row, text=self._L["llm_api_key_label"],
    bg=C["BG_DARK"], fg=C["TEXT_MAIN"], font=self._font(-1),
    width=20, anchor="w",
).pack(side="left")
self.claude_api_key_var = tk.StringVar(
    value=self._session_api_keys.get("claude", "")  # D-05: プリフィル
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

# 小注記（D-03 + D-07 統合・env 設定済みなら動的追記）
note = self._L["llm_key_session_note"]
if os.environ.get("ANTHROPIC_API_KEY"):
    note += " " + self._L["llm_key_env_set_note"].format(env_var="ANTHROPIC_API_KEY")
tk.Label(
    self.claude_section_frame, text=note,
    bg=C["BG_DARK"], fg=C["TEXT_SUB"], font=self._font(-2),
    wraplength=460, justify="left",
).pack(anchor="w", pady=(0, 2))
```

**`_apply()` での格納処理（D-04/D-06）:**
```python
# Source: pagefolio/dialogs/llm_config.py:1121 _apply() への追加
# llm_settings dict には絶対に入れない（T-05-12 継続）。
# 3プロバイダ全部を毎回同期する（表示中セクションだけでなく、
# ユーザーが provider 切替前に入力した値も保持するため）。
for provider_key, var in (
    ("claude", self.claude_api_key_var),
    ("gemini", self.gemini_api_key_var),
    ("runpod", self.runpod_api_key_var),
):
    key = var.get().strip()
    if key:
        self._session_api_keys[provider_key] = key
    else:
        self._session_api_keys.pop(provider_key, None)  # D-06: 空欄で OK ＝ クリア
```

### Pattern 3: 2つの呼び出し経路への `session_api_keys` 配線（V171-KEY-01 の前提）

**What:** `LLMConfigDialog` は2箇所から呼ばれる。両方とも `_session_api_keys` への到達経路を配線する必要がある。

| 呼び出し元 | 現状 | 必要な変更 |
|-----------|------|-----------|
| `OCRDialog._open_llm_config`（`pagefolio/ocr_dialog.py:859`） | `self.app` を直接保持 | `LLMConfigDialog(..., session_api_keys=self.app._session_api_keys)` を渡すだけ（1行追加） |
| `SettingsDialog._open_llm_config`（`pagefolio/dialogs/settings.py:162`） | `self.app` を保持しない。`current_settings` dict のみ | ①`PDFEditorApp._open_settings`（`pagefolio/app.py:461`）が `SettingsDialog(...)` 呼び出しに `session_api_keys=self._session_api_keys` を追加 → ②`SettingsDialog.__init__` が引数を受け取り `self._session_api_keys` として保持 → ③`SettingsDialog._open_llm_config` が `LLMConfigDialog(..., session_api_keys=self._session_api_keys)` を渡す |

**注意:** `dict` は複製せず参照をそのまま渡すこと。複製すると `LLMConfigDialog._apply()` 内の変更が `app._session_api_keys` の実体に反映されない（OCR 実行時に見えなくなる）。テストコードでも `getattr(self, "_session_api_keys", {})` の安全フォールバックパターン（既存 `ocr.py:778` 等）を踏襲し、`None` 渡しでもクラッシュしないようにする。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| マスク表示付き入力欄 | 独自の文字置換描画 | `tk.Entry(show="*")` + `configure(show="")` トグル | Tkinter 標準機能で十分・既存 `OCRDialog.api_key_entry` と同じ枯れたパターン（`pagefolio/ocr_dialog.py:482`） |
| キーの一時保管 | 独自の暗号化/難読化ラッパー | プロセスメモリ内の平文 dict（`app._session_api_keys`） | セッション限定・非永続の要件（V14-D-02）はメモリ保持だけで満たせる。暗号化は「保存」を前提にした過剰実装であり本フェーズのスコープ外（OS キーストア連携は Out of Scope） |
| キー解決の優先順ロジック | UI 層・プロバイダ層それぞれに個別実装 | `_resolve_api_key` 単一関数への集約（既存踏襲） | 3プロバイダ×複数呼び出し元に分散実装すると反転漏れ・不整合が起きる。既存アーキテクチャが既にこの原則で作られている |

**Key insight:** 本フェーズに「作るべき新機構」はほぼ無い。既存の `_resolve_api_key`/`_session_api_keys`/`_SENSITIVE_KEYS` の3点セットが既に正しい抽象を提供しており、やるべきことは (a) 優先順の入れ替え、(b) 入力 UI の移設、(c) 移設に伴う配線、の3点に限定される。

## Common Pitfalls

### Pitfall 1: RunPod が現行 `_ensure_cloud_session_key` で claude スロットに誤格納される（V171-KEY-04 の実体）

**What goes wrong:** `pagefolio/ocr_dialog.py:1157-1161` の `_ensure_cloud_session_key` は `if name == "gemini": ... else: self.app._session_api_keys["claude"] = key` という2分岐しかなく、`name == "runpod"` のとき `else` に落ちて `_session_api_keys["claude"]` へキーが入る。
**Why it happens:** RunPod 追加時（Phase の RunPod プロバイダ導入）にこの関数が3分岐化されなかった。
**How to avoid:** この関数自体を撤去し（撤去対象と明記済み）、新設する軽量チェック関数では provider 名を直接渡して `_resolve_api_key(name, session_keys)` を呼ぶだけにする。入力 UI が LLMConfigDialog に移るため、この関数はもはや「値を集めて格納する」責務を持たず「解決可能か確認するだけ」になり、構造的にこのバグは再発しなくなる。
**Warning signs:** RunPod 選択時に Claude のセッションキーが上書きされる／RunPod で OCR 実行すると常に鍵未設定エラーになる（新規回帰テストで検出可能）。

### Pitfall 2: `_ensure_cloud_session_key` 撤去後、鍵未解決時の「明示的なエラー」（成功基準2）が消えてしまう

**What goes wrong:** 現在、鍵未設定時のユーザー向けエラー表示は `_on_run`/`_on_summary` 内の `if not self._ensure_cloud_session_key(): return` というゲートでのみ発生する（`pagefolio/ocr_dialog.py:1187, 1868`）。この関数を単純削除すると、鍵未設定のままプロバイダが再生成され（`_apply_llm_settings`/`_refresh_provider_frame` は `OCRAPIKeyError` を捕捉して `api_key=""` にフォールバックするだけ・`pagefolio/ocr_dialog.py:918-919` 等）、実際の HTTP リクエストが認証エラーで失敗するまでユーザーに分かりやすいエラーが出ない。
**Why it happens:** 「鍵の収集」と「鍵の存在確認」が同じ関数に同居していたため、UI 部分だけ削除すると確認ロジックも一緒に失われる。
**How to avoid:** `_ensure_cloud_session_key` を「値を集める」処理無しの `_check_cloud_api_key()`（仮称）に置き換える。ロジックは `_resolve_api_key(name, session_keys)` を呼び、`OCRAPIKeyError` を捕捉したら D-08 の更新後メッセージ（`{env_var}` を含む）を `messagebox.showerror` で表示し `False` を返す。`_on_run`/`_on_summary` の呼び出し箇所はメソッド名を差し替えるだけで済む。
**Warning signs:** 鍵未設定で OCR 実行した際にエラーメッセージが出ず、ネットワークタイムアウトや 401 エラーが直接表示される（V171-KEY-02 成功基準「明示的なエラー」に違反）。

### Pitfall 3: OCRDialog 撤去に伴うテスト破棄漏れ（`tests/test_provider_ui.py`）

**What goes wrong:** `tests/test_provider_ui.py:189-204` の `_make_dialog_stub` ヘルパーは `stub._needs_session_key = lambda: OCRDialog._needs_session_key(stub)` を束縛しており、`TestNeedsSessionKey` クラス（:335-374、6テスト）がこれを利用する。`_needs_session_key` を `OCRDialog` から削除すると、この6テストは `AttributeError` で失敗する。
**Why it happens:** 撤去対象メソッドへの直接的なテスト依存。
**How to avoid:** `_needs_session_key`/`_ensure_cloud_session_key`/`_key_frame`/`api_key_var` を撤去するタスクと同じタスク内で `TestNeedsSessionKey` クラス全体と `_make_dialog_stub` 内の該当行を削除する（V171-TEST-02 の一部として計画に明記）。
**Warning signs:** `pytest` 実行時に `test_provider_ui.py::TestNeedsSessionKey::*` が `AttributeError: type object 'OCRDialog' has no attribute '_needs_session_key'` で失敗。

### Pitfall 4: `TestResolveApiKey`/`TestResolveApiKeyGemini` は「反転後の新規期待値」への書き換えが必要（新規追加ではない）

**What goes wrong:** `tests/test_ocr.py:531-577`（`TestResolveApiKey`）と `tests/test_ocr.py:1083-1131`（`TestResolveApiKeyGemini`）には `test_env_var_takes_priority_over_session_key` のような、まさに反転対象の挙動を固定するテストが既に存在する。優先順を反転すると、これらのテストは**そのまま矛盾して失敗する**（既存のグリーンテストが新仕様の下でレッドになる想定内の変更）。
**Why it happens:** これらは v1.4.0/v1.6.0 期に「環境変数優先」を回帰防止する目的で書かれたテストであり、本フェーズの仕様変更そのものを検証対象にしている。
**How to avoid:** 新規テスト追加ではなく、既存テストのアサーションと docstring を「入力値優先」に書き換える（例: `test_env_var_takes_priority_over_session_key` → `test_session_key_takes_priority_over_env_var` へリネーム＋期待値反転）。あわせて RunPod 用の同型テストクラス（`TestResolveApiKeyRunPod`）が**現状 `tests/test_ocr.py` に一つも存在しない**ため新設が必要（V171-TEST-02 のギャップ）。
**Warning signs:** 計画で「テスト追加」とだけ書かれ「既存テストの書き換え」が漏れると、実行後に意図的な仕様変更のはずのテストが赤いままになる。

### Pitfall 5: LLMConfigDialog の2つの呼び出し経路のうち一方だけ配線して片方が壊れる

**What goes wrong:** `SettingsDialog` 経由（`pagefolio/dialogs/settings.py`）は `app` インスタンスを保持しないため、`OCRDialog` 経由の配線だけ直して満足すると、設定ダイアログ経由で開いた LLMConfigDialog では `session_api_keys` が渡らず（`None`→空dict fallback）、入力してもプリフィルされず・保存されても実 `app._session_api_keys` に反映されない。
**Why it happens:** `LLMConfigDialog` の呼び出し元が2箇所に分散していることが見落とされやすい。
**How to avoid:** `PDFEditorApp._open_settings`（`app.py:461`）→ `SettingsDialog.__init__`（`dialogs/settings.py:19`）→ `SettingsDialog._open_llm_config`（`dialogs/settings.py:162`）の3段階すべてに `session_api_keys` を配線すること。計画のタスク分割時、この3ファイルの変更を同一タスク（または明示的な依存関係のある連続タスク）にまとめる。
**Warning signs:** 「設定」メニューから開いた LLM設定ダイアログでは APIキーが保存されないが、OCR 実行画面の「⚙ LLM 設定…」から開くと保存される、という非対称な挙動。

## Code Examples

### 現行 `_resolve_api_key`（変更前・参照用）
```python
# Source: pagefolio/ocr.py:209-266（変更前のベースライン）
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
    # gemini / runpod も同型（環境変数優先）
```

### 撤去対象コードの実体確認（V171-KEY-03）
```python
# Source: pagefolio/ocr_dialog.py:834-855（撤去対象）
def _needs_session_key(self):
    """クラウドかつ API キー環境変数が未設定のときに True を返す。"""
    ...

# Source: pagefolio/ocr_dialog.py:1128-1162（撤去対象・置換必要）
def _ensure_cloud_session_key(self):
    """クラウド実行前のセッションキー確認。続行可否を bool で返す。"""
    if not self._needs_session_key():
        return True
    ...
    # runpod 分岐が無いため else で claude スロットに誤格納（Pitfall 1）
```

### 新設 `_check_cloud_api_key`（置換案・全プロバイダ対応）
```python
# 提案: pagefolio/ocr_dialog.py の _ensure_cloud_session_key を置換
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
            "runpod": "ocr_api_key_missing_runpod",  # 新設要（Pitfall 4）
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
呼び出し側は `_on_run`（:1187）と `_on_summary`（:1868）の `self._ensure_cloud_session_key()` を `self._check_cloud_api_key()` へ差し替えるだけ。

### `_refresh_*_models` のライブ値優先解決（D-10）
```python
# Source: pagefolio/dialogs/llm_config.py:1047-1080 の _refresh_claude_models 改修案
def _refresh_claude_models(self):
    self._set_lm_status(self._L["llm_fetching_claude_models"], kind="info")
    # D-10: ライブ入力値 → 環境変数の順（settings への書き込みは行わない）
    api_key = self.claude_api_key_var.get().strip() or os.environ.get(
        "ANTHROPIC_API_KEY", ""
    )
    try:
        models = ClaudeProvider(api_key=api_key, model="").list_models()
    except Exception as e:
        logger.warning(self._L["llm_model_fetch_failed"].format(provider="Claude", e=e))
        models = ClaudeProvider.RECOMMENDED_MODELS
        self.claude_model_combo["values"] = models
        self._set_lm_status(self._L["llm_env_key_unset_static"], kind="info")
        return
    self.claude_model_combo["values"] = models
    if not api_key:
        self._set_lm_status(self._L["llm_env_key_unset_static"], kind="info")
    else:
        self._set_lm_status(
            self._L["settings_lm_test_ok"].format(count=len(models)), kind="ok"
        )
```
`_refresh_gemini_models`/`_refresh_runpod_models` も同型で `self.gemini_api_key_var`/`self.runpod_api_key_var` を参照するよう改修する。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| キー入力導線が OCRDialog（`_key_frame`）と将来的な LLMConfigDialog とで二重化しうる設計 | LLMConfigDialog へ一元化（V171-KEY-03） | 本フェーズ | 導線が1箇所になり、OCR実行画面はキー入力を意識しなくてよくなる（読み取り専用の Spinbox 化と同じ思想を APIキーにも適用） |
| キー解決順「環境変数 → セッションキー」（開発者/CI 環境変数を常に優先する設計） | 「セッションキー(入力値) → 環境変数」（V171-KEY-02） | 本フェーズ | エンドユーザーがダイアログで入力したキーが常に効くようになり、環境変数はデフォルト/フォールバック用途に後退する。既存の「環境変数優先」を前提にしたテストは全て書き換え対象 |
| RunPod のセッションキーが claude スロットに誤って入る２分岐ロジック | provider 名をそのまま渡す共通ロジック（`_resolve_api_key` を直接呼ぶだけ） | 本フェーズ | RunPod 選択時の鍵解決バグが構造的に解消（if/elif の追加ではなく、専用の値収集ロジック自体を削除することで再発を防ぐ） |

**Deprecated/outdated:**
- `OCRDialog._needs_session_key` / `_ensure_cloud_session_key` / `_key_frame` / `api_key_var`: LLMConfigDialog への一元化により撤去（値収集の責務は無くなる）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | APIキー入力欄のトグルボタンラベルは「👁 表示」/非表示の2状態切替（絵文字アイコン使用）で実装可能という前提（D-02 の文言をそのまま踏襲） | Architecture Patterns Pattern 2 | フォント/OS 環境によっては絵文字がグリフ無しで表示される可能性。既存コードベースで既に「⚙ LLM 設定…」「▶ 読み取り実行」等の絵文字ボタンが多用されており（`ocr_dialog.py`/`llm_config.py` 各所）実績パターンのため低リスク |
| A2 | `_apply()` 内で3プロバイダ全ての APIキー入力値を毎回同期する設計（表示中セクションだけでなく非表示セクションの値も保持）が正しい実装方針である | Architecture Patterns Pattern 2 | ユーザーが provider 切替前に入力した値が Apply 時に失われる可能性。ただし D-04/D-05（プリフィル前提）から見て複数プロバイダの値を同時保持する設計が意図と整合すると判断（要 discuss-phase 確認事項ではなく実装確認レベル） |

**この表が示す通り、いずれも実装確認レベルの軽微な仮定であり、要件解釈に関わる重大な仮定はない**（コード調査により大半の疑問が VERIFIED 済みのため）。

## Open Questions (RESOLVED)

1. **RESOLVED: APIキー欄の pack 順序（モデル行の前 or 後）** — Recommendation どおり「モデル取得ボタン行の直前」で確定（01-02-PLAN.md Task 1 に反映済み）
   - What we know: D-01 は「各セクションフレーム内に1欄追加」とのみ指定し、正確な行順序は Claude's Discretion に委ねられている。
   - What's unclear: モデル選択行の直前に置くか直後に置くか（UX 上はモデル取得ボタンの直前＝「まずキーを入れてから疎通確認」の流れが自然）。
   - Recommendation: モデル取得ボタン行の直前（モデル選択行の直後）に配置し、「キー入力 → その場でモデル取得（D-10 の疎通確認体験）」という操作順を UI レイアウトでも表現する。

2. **RESOLVED: RunPod 用エラーメッセージ文言の新規キー名** — Recommendation どおり `ocr_api_key_missing_runpod` を新設で確定（01-01-PLAN.md Task 3 に反映済み）
   - What we know: `ocr_api_key_missing`（claude）・`ocr_api_key_missing_gemini` は既存。RunPod 用は存在しない（Pitfall 4）。
   - What's unclear: 新規キー名を `ocr_api_key_missing_runpod` にするか、既存 `ocr_api_key_missing` を汎用化して `{provider}`/`{env_var}` 両プレースホルダ化するか。
   - Recommendation: 既存パターン踏襲（claude 用・gemini 用が別キーで存在する）を維持し `ocr_api_key_missing_runpod` を新設する方が既存コードとの一貫性が高く、書き換え範囲も小さい。

## Environment Availability

**該当なし** — 本フェーズは code/config のみの変更であり、外部ツール・サービス・ランタイムへの新規依存はない（Tkinter/pytest/ruff は既存環境に導入済み）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2（`pyproject.toml` `[tool.pytest.ini_options]` で `testpaths = ["tests"]`） |
| Config file | `pyproject.toml`（`[tool.pytest.ini_options]`・`[tool.ruff]`） |
| Quick run command | `pytest tests/test_ocr.py -k "ResolveApiKey" -q` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V171-KEY-01 | LLMConfigDialog の APIキー入力値が `llm_settings` dict に含まれない（settings 非流入） | unit | `pytest tests/test_provider_ui.py -k "ApiKeyNotInSettings" -x` | ❌ Wave 0（新規クラス要） |
| V171-KEY-01 | `claude_api_key`/`gemini_api_key`/`runpod_api_key`/`anthropic_api_key`/`GEMINI_API_KEY` 等が `settings.json` に非出力 | unit | `pytest tests/test_settings_keyguard.py -x` | ✅（既存カバー・変更不要） |
| V171-KEY-02 | 入力値(session_keys)が環境変数より優先される（claude） | unit | `pytest tests/test_ocr.py -k "TestResolveApiKey" -x` | ✅ 既存テストの**書き換え要**（Pitfall 4） |
| V171-KEY-02 | 入力値(session_keys)が環境変数より優先される（gemini・dual env var 内部順序は不変） | unit | `pytest tests/test_ocr.py -k "TestResolveApiKeyGemini" -x` | ✅ 既存テストの**書き換え要** |
| V171-KEY-02 | 両方未設定で `OCRAPIKeyError` を raise（claude/gemini） | unit | `pytest tests/test_ocr.py -k "raises or no_env_no_session" -x` | ✅（既存・維持） |
| V171-KEY-02 | 両方未設定でクラウド OCR 実行時に `messagebox.showerror` が呼ばれる（`_check_cloud_api_key`） | unit | `pytest tests/test_provider_ui.py -k "CheckCloudApiKey" -x` | ❌ Wave 0（新規クラス要・旧 `TestNeedsSessionKey` の置換） |
| V171-KEY-04 | RunPod の `_resolve_api_key` が入力値優先/環境変数フォールバック/raise の3ケースを満たす | unit | `pytest tests/test_ocr.py -k "TestResolveApiKeyRunPod" -x` | ❌ Wave 0（新規クラス要・現状ゼロ件） |
| V171-KEY-04 | RunPod セッションキーが `_session_api_keys["runpod"]` に正しく格納される（claude スロットへの誤格納が起きない） | unit | `pytest tests/test_provider_ui.py -k "RunpodSessionKeySlot" -x` | ❌ Wave 0（Pitfall 1 の回帰防止） |
| V171-TEST-02 | 全体回帰（既存707件 + 新規） | full | `pytest` | ✅ |

### Sampling Rate
- **Per task commit:** `pytest tests/test_ocr.py tests/test_provider_ui.py tests/test_settings_keyguard.py -q`
- **Per wave merge:** `pytest`（フルスイート・現状707件がベースライン）
- **Phase gate:** フルスイートグリーン + `ruff check . && ruff format .` クリーンを `/gsd-verify-work` 前に確認

### Wave 0 Gaps
- [ ] `tests/test_ocr.py::TestResolveApiKeyRunPod` — RunPod 版の `_resolve_api_key` テストクラス新設（claude/gemini と同型: env優先→入力優先へ書き換えられた後の3ケース + os.environ非書込み確認）
- [ ] `tests/test_provider_ui.py::TestCheckCloudApiKey`（仮称） — `_check_cloud_api_key` の3プロバイダ分岐 + messagebox 呼び出し確認（`TestNeedsSessionKey` の実質的な後継）
- [ ] `tests/test_provider_ui.py` に LLMConfigDialog の APIキー欄→`llm_settings` 非流入 + `_session_api_keys` 格納/クリアの検証クラス新設
- [ ] `tests/test_lang_parity.py` は既存の ja/en キー集合一致テストがそのまま新規キーもカバーするため追加不要（新規キー追加時に自動検証される）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | エンドユーザー認証機構ではない（外部 API への認証情報の取り扱いのみ） |
| V3 Session Management | no | Web セッションではなくプロセスメモリ内の一時保持（Tkinter デスクトップアプリ） |
| V4 Access Control | no | 単一ユーザーローカルアプリ・アクセス制御要件なし |
| V5 Input Validation | yes | APIキー文字列は `.strip()` のみ実施（既存パターン踏襲）。長さ/文字種の厳密検証は不要（外部 API 側が拒否する） |
| V6 Cryptography | no | 暗号化・保存を行わない設計（メモリ内平文保持がスコープ内の対処＝OS キーストア連携は明示的 Out of Scope） |
| V14 Configuration（機密情報の非平文保存） | yes | `_SENSITIVE_KEYS` による構造的フィルタ（`pagefolio/settings.py:17-28`）。新規 UI もこのガードを迂回しない設計を維持 |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| APIキーが `pagefolio_settings.json` に平文で残留し、リポジトリ/バックアップ経由で漏洩 | Information Disclosure | `_SENSITIVE_KEYS` ガード（既存・変更不要）。UI 側は `llm_settings` dict にキーを一切含めない設計を維持（D-04・T-05-12） |
| APIキーがログ出力される（例外メッセージ・デバッグログ） | Information Disclosure | 既存パターン踏襲: キー名のみ `logger.error`/`logger.warning`、値は出力しない（`_save_settings` の `leaked` ログが前例） |
| ダイアログ画面の共有（スクリーンショット・画面共有）でキーが露出 | Information Disclosure | D-02 の常時マスク（`show="*"`）がデフォルト防御。トグル表示はユーザーの明示操作時のみ |
| `os.environ` への意図しない書き込みによる他プロセスへの影響 | Tampering | `_resolve_api_key`/`_check_cloud_api_key` は読み取り専用原則を維持（Phase 05-03 決定の継続）。書き込みコードパスを一切追加しない |

## Project Constraints (from CLAUDE.md)

以下は `CLAUDE.md` に定義された、本フェーズのプラン・実装が遵守すべき既存プロジェクト規約（locked decisions と同格で扱う）:

- **言語ルール:** すべての返答・コミットメッセージ・PR・申し送りを日本語で記述する（ソースコード中の識別子・ライブラリ名・エラーメッセージ原文は例外）。
- **リント/フォーマット必須:** py ファイル編集後は必ず `ruff check . && ruff format .` を通す。
- **テスト必須:** コミット前に `pytest` をグリーンにする。
- **禁止事項:** `pyproject.toml` の編集・裸の `except:`（必ず `except Exception as e:`）・無断の `# type: ignore`。
- **LANG 辞書:** 新規キーは ja/en 両方へ同一キーで追加し、キー数を一致させる（`tests/test_lang_parity.py` が自動検証）。
- **テーマ色/フォント:** ハードコード禁止。`C["KEY"]` 辞書・`self._font(delta)` ヘルパー経由で参照する（本フェーズの新規 UI 要素も同様）。
- **1タスクずつ完了:** 作業フローとして1タスクを完了させてから次へ進む。
- **変更時チェックリスト:** `開発履歴.md` への追記、`APP_VERSION`（`pagefolio/constants.py`、現行 `v1.7.0`）の更新判断はマイルストーン単位の慣例（v1.6.0/v1.6.1 等）に従い、本フェーズ単独でのバージョン更新は必須ではない（過去のマイルストーンでは通常リリース確定時にまとめて更新）。
- **GSD ワークフロー:** ファイル変更は GSD コマンド経由で行う（本フェーズは `/gsd-plan-phase` → `/gsd-execute-phase` の枠内）。
- **既存決定の継続:** `_resolve_api_key` の読み取り専用原則（Phase 05-03）・`_SENSITIVE_KEYS` 非保存ガード（V14-D-02）は本フェーズでも変更禁止（優先順のみ変更）。

## Sources

### Primary (HIGH confidence — 直接コード読解)
- `pagefolio/ocr.py:190-267` — `_resolve_api_key` 現行実装（3プロバイダ対応・環境変数優先の実体）
- `pagefolio/ocr.py:625-720` — `build_provider` ファクトリ（api_key 引数注入・settings 非書込み原則）
- `pagefolio/dialogs/llm_config.py`（全文） — `LLMConfigDialog` の構造（セクションフレーム・`_on_provider_change`・`_refresh_*_models`・`_apply`）
- `pagefolio/ocr_dialog.py:100-130, 460-500, 825-1210, 1270-1330, 1855-1880` — 旧セッションキー UI（`_key_frame`/`api_key_var`/`_needs_session_key`/`_ensure_cloud_session_key`）と呼び出し経路（`_on_run`/`_on_summary`/`_apply_llm_settings`/`_refresh_provider_frame`）
- `pagefolio/settings.py:1-108` — `_SENSITIVE_KEYS`・`_save_settings`・`_load_settings` デフォルト値
- `pagefolio/dialogs/settings.py`（全文） — `SettingsDialog` から `LLMConfigDialog` を開く別経路（`app` インスタンス非保持の事実）
- `pagefolio/app.py:81, 460-482` — `_session_api_keys` 初期化・`_open_settings` の呼び出し引数
- `pagefolio/lang.py:390-435, 473-485, 555-570` — 既存エラー文言・ヒント文言のキー名と現行テキスト
- `tests/test_ocr.py:528-599, 1080-1133` — `TestResolveApiKey`/`TestResolveApiKeyGemini`（書き換え対象の実体）
- `tests/test_provider_ui.py:184-375` — `_make_dialog_stub`/`TestNeedsSessionKey`（撤去対象の実体）
- `tests/test_settings_keyguard.py`（全文） — 既存非保存ガードテスト（変更不要な既存カバレッジ）
- `tests/test_lang_parity.py`（全文） — ja/en キー一致の自動検証機構
- `.planning/config.json` — `nyquist_validation: true`・`security_enforcement: true`（本 RESEARCH.md のセクション構成根拠）
- `requirements.txt`・`pyproject.toml` — 依存バージョン固定・pytest/ruff 設定

### Secondary (MEDIUM confidence)
なし（本フェーズは外部ドキュメント参照不要な内部リファクタリングのため）

### Tertiary (LOW confidence)
なし

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 新規依存ゼロ、既存 `requirements.txt` の直接確認のみ
- Architecture: HIGH — 全パターンが既存コードの直接読解に基づく（推測ではなく実装済みコードの構造分析）
- Pitfalls: HIGH — 5件全てが既存コードの具体的な行番号・既存テストの具体的な失敗モードに基づく（仮説ではなく確認済みの構造的事実）

**Research date:** 2026-07-05
**Valid until:** 60日（内部リファクタリングのため陳腐化リスクは低いが、Phase 2〜4 での `ocr.py`/`ocr_dialog.py` 変更により行番号が前後する可能性あり。実装直前に該当行を再確認すること）