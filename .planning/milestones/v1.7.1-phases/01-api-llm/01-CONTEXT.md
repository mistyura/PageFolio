# Phase 1: APIキー入力欄（LLM設定への一元化） - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

ユーザーは Claude / Gemini / RunPod の APIキーを LLM設定ダイアログ（`LLMConfigDialog`）で一元的に入力でき、キーは「入力値 → 環境変数」の優先順で解決される（セッション限定・非永続）。OCRDialog 側の既存セッションキー入力欄は撤去する。優先順解決と `_SENSITIVE_KEYS` 非保存ガードの回帰テストを整備する（V171-KEY-01〜04・V171-TEST-02）。

キーの永続化（OS キーストア連携）・OAuth・新プロバイダ追加はスコープ外。

</domain>

<decisions>
## Implementation Decisions

### 入力欄の配置と見た目
- **D-01:** キー入力欄は既存のプロバイダ別セクションフレーム（`claude_section_frame` / `gemini_section_frame` / `runpod_section_frame`）内に各 1 欄追加する。選択中プロバイダの欄だけが見える（既存の `_on_provider_change` セクション切替ロジックを活用・ダイアログ縦長化を最小化）。
- **D-02:** 入力欄は常時マスク（`tk.Entry(show="*")`）とし、横に「👁 表示」トグルボタンを置いて平文確認を可能にする（OCRDialog 既存キー欄の show="*" を踏襲しつつ確認性を追加）。
- **D-03:** 入力欄の直下に TEXT_SUB 色の小注記を表示する：「※ セッション限定（アプリ終了で破棄・設定ファイルには保存されません）」。LANG の ja/en 両辞書へ同一キーで追加。

### 入力値のライフサイクル
- **D-04:** 入力キーは OK（適用）押下時に `app._session_api_keys` へ直接格納する。`on_apply` に渡す `llm_settings` dict には**含めない**（settings 流入ガード T-05-12 を構造的に維持）。キャンセルで閉じれば反映されない。
- **D-05:** ダイアログ再オープン時は `_session_api_keys` の既存値をマスク付きでプリフィル表示する（設定済みが一目で分かる・上書き/削除も自然）。
- **D-06:** クリアは「欄を空にして OK」で `_session_api_keys` から削除（以降は環境変数へフォールバック）。専用クリアボタンは設けない。

### 環境変数との関係の見せ方
- **D-07:** 環境変数が設定済みの場合、D-03 の小注記に動的追記する：「環境変数 <ENV名> 設定済み（ここで入力した値が優先されます）」。独立ステータス行は追加しない。
- **D-08:** 両方未設定でクラウド OCR を実行したときのエラー文言を「LLM設定ダイアログで APIキーを入力するか、環境変数 <ENV名> を設定してください」へ更新する（ja/en 両辞書・一元化導線の案内）。
- **D-09:** キー未設定エラー時に LLMConfigDialog を自動オープンしない。文言での誘導のみ（OCRDialog の既存「⚙ LLM 設定…」ボタンで到達可能）。

### モデル取得ボタンのキー解決
- **D-10:** LLMConfigDialog 内のモデル一覧取得ボタン（`_refresh_claude_models` / `_refresh_gemini_models` / `_refresh_runpod_models`）は「ダイアログ入力欄のライブ値（OK 前でも）→ 環境変数」の順で解決する。入力直後にその場でモデル取得＝キーの疎通確認ができる。
- **D-11:** モデル取得時にキーがどこにもない場合は現行の静的推奨モデルフォールバック（D-08 系）を維持しつつ、セクション内に「APIキー未設定のため推奨モデル一覧を表示中」のヒントを表示する。

### Claude's Discretion
- 入力欄行のレイアウト詳細（ラベル幅・トグルボタンの文言/アイコン・pack 順）は既存セクションの行構成に合わせて実装時に判断。
- `_resolve_api_key` の優先順反転の実装形（引数追加 or 内部順序入替）と、OCRDialog 撤去に伴う `_needs_session_key` / `_ensure_cloud_session_key` / `_key_frame` の削除・簡素化の範囲は planner/executor 判断。ただし読み取り専用原則（os.environ 書き込み禁止）は維持。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・ロードマップ
- `.planning/REQUIREMENTS.md` — V171-KEY-01〜04・V171-TEST-02 の要件定義と Key Context（優先順反転・非永続維持）
- `.planning/ROADMAP.md` §Phase 1 — 成功基準 5 項目（本フェーズの検証対象）

### 先行決定（維持すべき制約）
- `.planning/PROJECT.md` §Key Decisions — V14-D-02（`_SENSITIVE_KEYS` ガード・settings 非永続）、Phase 05-03 決定（`_resolve_api_key` は os.environ 読み取り専用）
- `.planning/STATE.md` §Blockers/Concerns — Phase 1 留意（解決順のみ反転・ガード維持）

（外部 spec/ADR ファイルはなし。要件は上記 planning ドキュメントに集約されている）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pagefolio/ocr.py:209 _resolve_api_key(provider_name, session_keys)` — 既に claude/gemini/runpod 3 種対応済み。現行は「環境変数 → セッションキー」順。**この関数内の順序を反転するのが本丸**（全呼び出し経路が一括で反転される）。
- `pagefolio/dialogs/llm_config.py` — プロバイダ別セクションフレーム（claude/gemini/runpod）が既存。`_on_provider_change` の表示切替・`_apply`（llm_config.py:1121）の適用経路に乗せられる。
- `pagefolio/app.py:81 self._session_api_keys = {}` — セッションキー辞書は既存。RunPod スロット追加は辞書キー追加のみ。
- `pagefolio/settings.py _SENSITIVE_KEYS` — 非保存ガード（RUNPOD_API_KEY 含む）は整備済み。
- 既存テスト: `tests/test_settings_keyguard.py` / `tests/test_ocr.py` / `tests/test_provider_ui.py` — V171-TEST-02 の回帰テストの追加先候補。

### Established Patterns
- キー値はログ・settings に一切出さない（キー名のみログ可・V14-D-02 / Phase 05-02 決定）。
- LANG 新規キーは ja/en 両辞書へ同一キーで追加（キー数一致・test_lang_parity.py が監視）。
- テーマ色は `C[...]`・フォントは `self._font(delta)` 経由（CLAUDE.md 規約）。

### Integration Points
- **撤去対象:** `pagefolio/ocr_dialog.py` の `_needs_session_key()`（:834）・`_ensure_cloud_session_key()`（:1128）・`_key_frame` / `api_key_var`（:473, :1041 の pack 制御含む）。OCR 実行フロー（`_on_run` / `_on_summary`）は撤去後も従来どおり動作させる。
- **既知ギャップ:** `_ensure_cloud_session_key` は claude/gemini のみ分岐で、runpod 選択時に入力キーが claude スロットへ入る（V171-KEY-04 の実体）。撤去により解消されるが、回帰テストで runpod スロットの正しさを担保すること。
- `pagefolio/dialogs/llm_config.py:1020 _refresh_runpod_models` — 現行は `os.environ.get("RUNPOD_API_KEY")` 直接参照。D-10 のライブ値優先解決へ変更。
- エラー文言: `pagefolio/lang.py` の `ocr_api_key_missing` / `ocr_api_key_missing_gemini` / RUNPOD 系文言（lang.py:483, :1036）を D-08 の導線案内へ更新。

</code_context>

<specifics>
## Specific Ideas

- 「入力→即モデル取得」をキーの疎通確認手段として使える体験にする（D-10 の狙い）。
- 小注記 1 行に「セッション限定」と「環境変数との優先関係」を統合し、セクションの行数増を最小に抑える（D-03 + D-07）。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope（OS キーストア永続化・OAuth は REQUIREMENTS.md の Out of Scope に記載済み）

</deferred>

---

*Phase: 1-APIキー入力欄（LLM設定への一元化）*
*Context gathered: 2026-07-04*
