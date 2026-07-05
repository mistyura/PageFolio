---
phase: 1
slug: 01-api-llm
status: draft
shadcn_initialized: false
preset: none
created: 2026-07-05
---

# Phase 1 — UI Design Contract

> APIキー入力欄（LLM設定への一元化）の視覚・操作契約。gsd-ui-researcher が生成し、gsd-ui-checker が検証する。
>
> **注記:** PageFolio は Tkinter（Python 標準ライブラリ）製の Windows デスクトップアプリであり、Web フロントエンドではない。本契約は shadcn/CSS/レスポンシブ等の Web 前提の概念を用いず、`pagefolio/themes.py` のテーマ辞書・`self._font(delta)` ヘルパー・既存 ttk スタイルに基づいて記述する。

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none（shadcn 等の Web コンポーネントレジストリは非該当。ネイティブ Tkinter/ttk） |
| Preset | not applicable |
| Component library | `tkinter` / `tkinter.ttk` 標準ウィジェット（`tk.Entry`, `tk.Label`, `tk.Frame`, `ttk.Button`, `ttk.Combobox`, `tk.Spinbox`） |
| Icon library | none — 絵文字グリフを直接テキストとして使用（既存パターン: `⚙ LLM 設定…`・`▶ 読み取り実行`・`⏯ 続きから再実行`）。本フェーズは `👁`（表示）/ `🙈`（隠す）を追加 |
| Font | `Segoe UI`（`self._font(delta[, weight])` ヘルパー経由。ベースサイズ `self.font_size`（8〜16・設定で可変）+ delta。**ハードコード禁止**、CLAUDE.md 規約） |

**出典:** RESEARCH.md `## Standard Stack`（新規パッケージ導入なし）・CONTEXT.md D-01/D-02（既存セクションフレーム構造・`show="*"` マスク踏襲）。

---

## Spacing Scale

Tkinter の `pack(padx=…, pady=…)` に基づく、本コードベースの既定スペーシング語彙（`pagefolio/dialogs/llm_config.py` 全体で一貫使用・本フェーズもこれに従う）。

| Token | Value | Usage |
|-------|-------|-------|
| xs | 2px | ボタン同士の横間隔（例: `claude_btn_row` 内 `ttk.Button` の `padx=2`）。新規 👁 トグルボタンも `padx=(2, 0)` でこれに揃える |
| sm | 4px | ラベル→入力欄の横間隔・入力欄内側パディング（例: 全 `tk.Entry`/`tk.Spinbox` の `padx=4`）。新規 APIキー欄もこれに揃える |
| md | 8px 前後 | 行間の垂直マージン（`pady=2` は行内の行間、セクション見出し直後は `pady=(4, 2)`〜`(6, 2)`） |
| lg | 16px | `OCRDialog` 側セクションのインデント（`padx=16`。本フェーズでは撤去対象コード側の値・新規追加なし） |
| xl | 24px | `LLMConfigDialog` 外枠の左右パディング（各 `*_section_frame.pack(padx=24, ...)`） |
| — | 14px（縦のみ） | ダイアログ最上部/最下部の余白（`pady=(14, 10)` 見出し・`pady=(8, 14)` ボタン行） |

**Exceptions:**
- 2px（xs）はテンプレート標準の 8-pt グリッドには乗らないが、本コードベース全体で「隣接ボタン間隔」として一貫使用されている確立済みトークンであり、新規要素もこれを踏襲する（逸脱ではなく既存規約への準拠）。
- 新規 APIキー行・注記ラベルは上記 xs/sm/md/xl のみを使用し、新しい値は導入しない。

---

## Typography

Tkinter に px 単位のフォントサイズ概念はなく、`self._font(delta[, weight])` の **delta（ベースサイズからの相対値）** で管理する。本コードベースの既存パターンから 3 サイズ・2 ウェイトを確定する。

| Role | Size (delta) | Weight | Notes |
|------|--------------|--------|-------|
| 見出し | `self._font(2, "bold")` | bold | ダイアログ見出し「LLM設定」（既存・本フェーズでの新規追加なし） |
| 本文/ラベル | `self._font(-1)` | regular | 行ラベル（`width=20, anchor="w"`）・入力欄テキスト。**新規 APIキー欄のラベル・`tk.Entry` はこれを使用** |
| 小注記/ステータス | `self._font(-2)` | regular | ヒント文言・`_set_lm_status` の状態表示。**新規セッション限定注記（D-03/D-07）・APIキー未設定ヒント（D-11）はこれを使用** |

- **Weight は regular（既定）と bold の 2 種類のみ**（bold は見出しとボタンラベルに限定・新規要素に bold は使わない）。
- Line height の概念は Tkinter にはない。複数行になり得るラベル（注記・ヒント）は `wraplength=460, justify="left"` を指定する（既存 `lm_status_label`・各セクションのヒントラベルと同一パターン）。新規注記ラベルもこれに揃える。

---

## Color

`pagefolio/themes.py` の `THEMES["dark"]`（既定テーマ）を基準に、実行時は必ず `C["KEY"]` 辞書経由で参照する（生の hex 直書き禁止・CLAUDE.md 規約）。

| Role | Value | Usage |
|------|-------|-------|
| Dominant（60%） | `C["BG_DARK"]` (`#1a1a2e`) | ダイアログ全体の背景・全 `tk.Frame`/`tk.Label` の `bg` |
| Secondary（30%） | `C["BG_CARD"]` (`#0f3460`) | 入力欄の背景（`tk.Entry`/`tk.Spinbox`/`ttk.Combobox` の `bg`）。**新規 APIキー `tk.Entry` の背景はこれを使用** |
| Accent（10%） | `C["ACCENT"]` (`#e94560`) | 見出しテキスト色・`Accent.TButton`（適用ボタン）背景・`_set_lm_status(kind="fail")` の失敗メッセージ文字色（既存 `_set_lm_status` 踏襲）。**新規要素では使用しない**（👁 トグルボタンは通常 `"TButton"` スタイル、APIキー欄自体はアクセント色を使わない） |
| Destructive | `C["DANGER_BG"]` (`#7c1c2e`) / `C["DANGER_FG"]` (`#ffaaaa`) | `Danger.TButton`（削除・終了等）。**本フェーズには破壊的操作なし**（キークリアは欄を空にして OK のみ・確認 UI 不要・D-06）につき未使用 |

**Accent reserved for:** ダイアログ見出しラベルの文字色、`Accent.TButton`（適用ボタン）の背景色、ステータスラベルの `kind="fail"` 文字色。**それ以外の要素（新規 APIキー欄・トグルボタン・注記ラベル）には使用しない。**

**セマンティック色の補足（新規要素が参照する既存色）:**
- `C["TEXT_SUB"]` — セッション限定注記（D-03）・環境変数状態追記（D-07）の文字色
- `C["WARNING"]` — `_set_lm_status(kind="info")` の情報メッセージ文字色（D-11 の「推奨モデル一覧を表示中」ヒントもこの kind を使用）
- `C["SUCCESS"]` — `_set_lm_status(kind="ok")` の成功メッセージ文字色（モデル取得成功時、変更なし）

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | 「適用」ボタン（既存 `llm_config_apply`・`Accent.TButton`）。本フェーズで新規 CTA は追加しない — APIキー入力値はこの既存ボタン押下時に `_session_api_keys` へ確定する（D-04） |
| Empty state（キー欄・環境変数とも未設定でモデル取得） | 「APIキー未設定のため推奨モデル一覧を表示中（{env_var} 環境変数または上の入力欄にキーを入力してください）」（D-11・claude/gemini/runpod の3バリエーション。下記 LANG キー表参照） |
| Error state（両方未設定でクラウド OCR 実行） | 「APIキーが設定されていません（{env_var}）。LLM設定ダイアログで APIキーを入力するか、環境変数を設定してください。」（D-08・claude/gemini/runpod の3バリエーション） |
| Destructive confirmation | 該当なし — キークリアは「欄を空にして OK」のみで完結し、確認ダイアログは設けない（D-06。破壊的操作としての扱いではなく通常の編集操作） |

### LANG キー契約（ja/en 同一キーで追加・更新。`tests/test_lang_parity.py` がキー数一致を検証）

**新規キー:**

| Key | ja | en |
|-----|----|----|
| `llm_api_key_label` | `APIキー:` | `API Key:` |
| `llm_key_toggle_show`（トグル初期状態のボタン文言） | `👁 表示` | `👁 Show` |
| `llm_key_toggle_hide`（表示中に切り替わるボタン文言） | `🙈 隠す` | `🙈 Hide` |
| `llm_key_session_note`（D-03） | `※ セッション限定（アプリ終了で破棄・設定ファイルには保存されません）` | `* Session only (discarded on app exit — never saved to the settings file)` |
| `llm_key_env_set_note`（D-07・`{env_var}` プレースホルダ） | `環境変数 {env_var} 設定済み（ここで入力した値が優先されます）` | `Environment variable {env_var} is set (the value entered here takes priority)` |
| `ocr_api_key_missing_runpod`（D-08・RunPod 用新規） | `RunPod APIキーが設定されていません。LLM設定ダイアログで APIキーを入力するか、環境変数 RUNPOD_API_KEY を設定してください。` | `RunPod API key is not set. Enter it in the LLM settings dialog, or set the RUNPOD_API_KEY environment variable.` |

**更新キー（既存キーの文言を D-08/D-11 に合わせて改訂。キー名は変更しない）:**

| Key | ja（更新後） | en（更新後） |
|-----|--------------|--------------|
| `ocr_api_key_missing`（claude 用） | `APIキーが設定されていません（{env_var}）。LLM設定ダイアログで APIキーを入力するか、環境変数を設定してください。` | `API key is not set ({env_var}). Enter it in the LLM settings dialog, or set the environment variable.` |
| `ocr_api_key_missing_gemini` | `Gemini APIキーが設定されていません。LLM設定ダイアログで APIキーを入力するか、環境変数 GEMINI_API_KEY（または GOOGLE_API_KEY）を設定してください。` | `Gemini API key is not set. Enter it in the LLM settings dialog, or set the GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable.` |
| `llm_env_key_unset_static`（claude・D-11） | `APIキー未設定のため推奨モデル一覧を表示中（ANTHROPIC_API_KEY 環境変数または上の入力欄にキーを入力してください）` | `API key not set — showing recommended models (enter a key above or set ANTHROPIC_API_KEY)` |
| `llm_env_key_unset_static_gemini`（D-11） | `APIキー未設定のため推奨モデル一覧を表示中（GEMINI_API_KEY/GOOGLE_API_KEY 環境変数または上の入力欄にキーを入力してください）` | `API key not set — showing recommended models (enter a key above or set GEMINI_API_KEY/GOOGLE_API_KEY)` |
| `llm_env_key_unset_static_runpod`（D-11） | `APIキー未設定のため推奨モデル一覧を表示中（RUNPOD_API_KEY 環境変数または上の入力欄にキーを入力してください）` | `API key not set — showing recommended models (enter a key above or set RUNPOD_API_KEY)` |

**撤去対象キー**（V171-KEY-03・`ocr_dialog.py` の旧セッションキー UI と共に削除。ja/en 両方から削除しキー数一致を維持）:

| Key | 理由 |
|-----|------|
| `ocr_session_key_label` | OCRDialog 側の旧キー入力欄ラベル。導線が LLMConfigDialog に一元化されるため不要 |

---

## Component Contract（Tkinter ウィジェット仕様）

テンプレートの Registry セクションは Web コンポーネントレジストリ専用のため本アプリには非該当。代わりに、本フェーズで `LLMConfigDialog` に追加する具体的なウィジェット構成を契約として明示する（executor の実装ソース・オブ・トゥルース）。

### 追加行の共通パターン（claude / gemini / runpod で同型・3回実装）

各プロバイダセクションフレーム（`claude_section_frame` / `gemini_section_frame` / `runpod_section_frame`）内、**モデル選択行の直後・モデル更新ボタン行の直前**に挿入する（Open Question 1 の推奨解決: 「キー入力 → その場でモデル取得」の操作順を UI 順序でも表現）。

1. **キー入力行**（`tk.Frame(section_frame, bg=C["BG_DARK"])`, `pack(fill="x", padx=0, pady=2)`）
   - `tk.Label`: `text=L["llm_api_key_label"]`, `width=20`, `anchor="w"`, `font=self._font(-1)`, `bg=C["BG_DARK"]`, `fg=C["TEXT_MAIN"]`, `pack(side="left")`
   - `tk.Entry`: `show="*"`（既定マスク・D-02）, `textvariable=<provider>_api_key_var`, `font=self._font(-1)`, `bg=C["BG_CARD"]`, `fg=C["TEXT_MAIN"]`, `insertbackground=C["TEXT_MAIN"]`, `relief="flat"`, `pack(side="left", fill="x", expand=True, padx=4)`
     - `StringVar` の初期値は `session_api_keys.get("<provider>", "")` でプリフィル（D-05）
   - `ttk.Button`（トグル）: `text=L["llm_key_toggle_show"]` 初期表示, `width=4`, `style="TButton"`（Accent/Danger は使わない）, `pack(side="left", padx=(2, 0))`
     - 押下毎に `entry.configure(show="" if shown else "*")` を切替え、ボタン文言も `llm_key_toggle_show` ⇄ `llm_key_toggle_hide` で切替える
2. **注記ラベル**（キー入力行の直下・`section_frame` 直属。`pack(anchor="w", pady=(0, 2))`）
   - `tk.Label`: `bg=C["BG_DARK"]`, `fg=C["TEXT_SUB"]`, `font=self._font(-2)`, `wraplength=460`, `justify="left"`
   - 文言 = `L["llm_key_session_note"]`。該当する環境変数が設定済みなら `" " + L["llm_key_env_set_note"].format(env_var=...)` を動的追記（D-07）:
     - claude: `ANTHROPIC_API_KEY`
     - gemini: `GEMINI_API_KEY` が設定されていればそれを表示、無ければ `GOOGLE_API_KEY`（既存 dual env var 優先順と整合）
     - runpod: `RUNPOD_API_KEY`

### プロバイダ別の行順序（既存行への挿入位置）

| セクション | 既存の行順 | 変更後の行順 |
|-----------|-----------|-------------|
| claude | `claude_model_row` → `claude_btn_row` | `claude_model_row` → **`claude_key_row`（新規）** → **注記ラベル（新規）** → `claude_btn_row` |
| gemini | `gemini_model_row` → `gemini_btn_row` | `gemini_model_row` → **`gemini_key_row`（新規）** → **注記ラベル（新規）** → `gemini_btn_row` |
| runpod | `runpod_url_row` → `runpod_model_row` → モデルヒントラベル → `runpod_btn_row` | `runpod_url_row` → `runpod_model_row` → モデルヒントラベル → **`runpod_key_row`（新規）** → **注記ラベル（新規）** → `runpod_btn_row` |

### `_apply()` への追加処理（D-04/D-06）

`llm_settings` dict には一切含めない。3プロバイダ分を毎回 `_session_api_keys` へ同期する（Pattern 2 のコード例どおり）:
- 欄が空でない → `session_api_keys[provider] = key.strip()`
- 欄が空 → `session_api_keys.pop(provider, None)`（クリア・D-06）

### 配線契約（表示・保存が機能するための前提・UI と不可分）

`LLMConfigDialog` は2つの呼び出し経路（`OCRDialog` 経由・`SettingsDialog` 経由）を持ち、**両方**に `session_api_keys` 参照（複製せず同一 dict 参照）を配線しない限り、本 UI 契約の D-05（プリフィル）は片方の経路でのみ機能する（RESEARCH.md Pitfall 5）。UI-SPEC としては「見た目・挙動は呼び出し経路によらず同一でなければならない」ことを契約として明記する — `SettingsDialog` 経由で開いた場合も、`OCRDialog` 経由と同じくプリフィル・注記・トグルが機能すること。

### 撤去対象 UI（V171-KEY-03・本契約の対象外領域）

`pagefolio/ocr_dialog.py` の `_key_frame` / `api_key_entry` / `ocr_session_key_label` 表示（旧セッションキー入力欄一式）は撤去する。撤去後、鍵未解決時のフィードバックは `messagebox.showerror` によるエラーダイアログ（上記 Error state コピー）のみとなり、ダイアログ内蔵の入力欄は残らない。

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | 該当なし | not applicable（Tkinter デスクトップアプリ・Web コンポーネントレジストリ不使用） |
| 第三者レジストリ | なし | not applicable |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS（N/A — Tkinter デスクトップアプリにつき shadcn/レジストリ非該当）

**Approval:** pending
