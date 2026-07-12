# Phase 4: UI/UX 磨き込み + 既知バグ棚卸し - Research

**Researched:** 2026-07-05
**Domain:** 既存 Python/Tkinter デスクトップアプリの UI 改修（ショートカット GUI 化）・i18n/文言監査（lang.py 374 キー）・ダイアログ構造整理・既知軽微バグ棚卸し。新規外部ライブラリなし。
**Confidence:** HIGH（全項目を現行コード読解・実行時 grep/Python スクリプトで直接検証。Tk `event.state` のプラットフォーム差のみ MEDIUM）

## Summary

本フェーズは新規技術調査ではなく、(1) ショートカットの GUI 編集機能を新設し、(2) `lang.py`（374 キー — CONTEXT.md の見積り「約500」より少ないが全数確認済み）の未使用キー・文言/messagebox 種別の一貫性を監査・修正し、(3) `SettingsDialog`/`LLMConfigDialog` のセクション構成を整理し、(4) 既知軽微バグの棚卸しリストを現行コード照合で確定・解消する作業である。

lang.py の全 374 キーを実際にコードベース全体（`pagefolio/`・`tests/`・`plugins/`）と突き合わせた結果、**未使用キーは 11 件**（L-5 の残り 2 件 `ocr_provider_off_hint`/`tesseract_not_installed` を含む）確定した。また `pagefolio/viewer.py` のページ拡大ポップアップ（`_show_page_popup`）に **LANG 経由でないハードコード日本語文言が 4 箇所**（ポップアップタイトル + ボタン3つ）見つかり、`self.lang="en"` でも日本語が出る i18n 違反であることを確認した。`pagefolio/page_ops.py:954` では `err_split_no_range`（エラー系キー）が `messagebox.showinfo` + `info_title` で表示されており、直後の行（:958）の同種入力検証エラーが `showerror` + `err_title` を使っている非対称も発見した。

D-17 の「Phase 2 からの明示繰り越し 2 件」のうち、**`RunPodProvider.list_models()` のデッドコード分岐は既に commit `a25d540`（WR-03）で解消済み**であることを確認した（現行コードに `base_url` 変数自体が存在しない）。CONTEXT.md の記述はこの点で古くなっており、Phase 4 の対象からは除外できる。もう1件（Ollama `_fetch_ollama_models`/`_test_ollama_connection` の LM Studio ペアとのほぼ完全重複）は現行コードに**活き残っている**ことを確認した。

ショートカット GUI 編集（V171-UIUX-01）は新規ダイアログ追加だが、実キーキャプチャ（D-02）は Tk の `event.state` ビットマスク（Shift=0x1・Control=0x4）と `event.keysym` の組み合わせで実現可能（標準 Tk 挙動・[Tk bind マニュアル](https://www.tcl-lang.org/man/tcl8.4/TkCmd/bind.htm) 参照）。既存テストスイートには実 Tk ウィジェット生成・`event_generate` を使うテストが**1件も存在しない**（全テストは unbound method + `SimpleNamespace` スタブ方式）ため、実キー入力の目視確認は VALIDATION.md の Manual-Only 項目とし、キーマージ・重複検出・keysym↔表示変換ロジックは純関数として抽出し自動テストする方針が既存パターンと整合する。

**Primary recommendation:** ショートカット GUI 化は新規 `dialogs/shortcuts.py`（`SettingsDialog` から起動・既存「LLM設定を開く」ボタンと同型パターン）として実装し、`app.py:146-186` の直書きバインドロジックを `_bind_shortcuts()`（再実行可能メソッド）へ抽出する。lang.py 監査は grep ベースの機械的全数チェックで再現性を担保し（本 RESEARCH.md の照合表を出発点に使う）、`test_lang_parity.py` へ未使用キー検出テストを追加する。SettingsDialog/LLMConfigDialog 整理は D-14〜D-16 の設計判断をそのまま実装対象にする。棚卸しは本 RESEARCH.md の照合表で活き残り 11 件相当を確定済みなので、計画時に個別プランへの割当のみ行えばよい。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ショートカット GUI 編集（V171-UIUX-01）**
- **D-01:** 編集 UI は専用ダイアログ。SettingsDialog に「⌨ ショートカット設定…」ボタンを追加して開く（既存「LLM設定を開く」ボタンと同型パターン）。
- **D-02:** キー入力は実キーキャプチャ方式。対象行の「変更」を押すと入力待ち状態になり、実際にキーを押して取得（Tk の KeyPress イベントから keysym を構築）。
- **D-03:** 対象は cmd_map の全 11 コマンド（既定キーあり 8 種 + rotate_right / rotate_left / rotate_180）。rotate 系は「未割当」として表示し GUI から新規割当できる。
- **D-04:** 同一キーの重複割当は保存時に拒否（どのコマンドと衝突しているかをエラー表示・保存不可）。後勝ちバインドによる無言の上書きを構造的に防ぐ。
- **D-05:** 変更は保存で即時反映。旧バインドを unbind → 新設定で再バインド。バインド処理は現在 `PDFEditorApp.__init__` 内に直書きのため、再実行可能なメソッドへ切り出す（副次効果としてテスト可能化）。
- **D-06:** 既定復帰は全体リセット＋個別解除の両導線。settings の `shortcuts` キーは既定との差分のみ保存（現行 `merge_shortcuts` の意味論を維持）。
- **D-07:** 一覧のキー表記は人間可読形式（「Ctrl+O」「Shift+Delete」等）。内部保存は Tk keysym のまま。keysym↔表示の変換は純関数化してテスト（`merge_shortcuts`/`shift_variant_keysym` と同居が自然）。
- **D-08:** キーを外して「割当なし（無効化）」にできる（例: Delete の誤押し防止）。現行実装も keysym が空ならバインドしないため自然に実現可能。

**文言/エラー一貫性監査（V171-UIUX-02）**
- **D-09:** L-5 の未使用キー 2 件（`ocr_provider_off_hint` / `tesseract_not_installed`）は削除（ja/en 両辞書から。将来必要になれば再追加）。※`ocr_provider_name_tesseract` は Phase 2 照合で使用中と確定済み。
- **D-10:** 未使用キー監査は lang.py 全体スキャン（約 500 キー）。動的参照（キー名合成等）の偽陽性に注意し、個別確認の上で削除。
- **D-11:** 未使用キー検出を回帰テストとして常設（`test_lang_parity.py` に「全キーがソースのどこかで参照されている」検査を追加・動的参照用の許可リスト付き）。
- **D-12:** エラー表示監査は 3 点すべてを対象: (a) LANG 経由でないハードコード文言の検出と LANG キー化、(b) messagebox 種別（showerror/showwarning/showinfo）の使い分け基準の確立と不一致修正、(c) ダイアログタイトル・文体（です/ます調・句点等）の統一。
- **D-13:** 監査結果の記録は Phase 2 前例踏襲: RESEARCH.md に照合表（項目 × 判定 × 根拠ファイル:行番号）。

**SettingsDialog / LLMConfigDialog 整理（V171-UIUX-03）**
- **D-14:** CONCERNS.md 記録のネストダイアログ fragile を本フェーズで解消する: LLMConfigDialog（ネスト側）の「適用」はその場で確定する独立トランザクションとし、外側 SettingsDialog のキャンセルは外側の項目（テーマ/フォント）のみに作用する。このセマンティクスを回帰テストで固定。
- **D-15:** LLMConfigDialog は共通/固有の分離明確化: 「全プロバイダ共通の設定（max_tokens・temperature・タイムアウト・プロンプト等）」と「選択中プロバイダ固有の設定（URL・モデル・APIキー）」を見出し付きで明確にグルーピングし直す。1 枚・プロバイダ選択でセクション切替という現行構造は維持（タブ化・スクロール化はしない）。
- **D-16:** SettingsDialog は見出し更新＋セクション再構成: 実態と不一致の「LM Studio (OCR)」見出しを「AI・OCR 設定」等へ改称し、「外観（テーマ/フォント）」「操作（ショートカット）」「AI・OCR」の 3 セクション構成へ再編。D-01 のショートカットボタンはここに収める。

**既知軽微バグ棚卸し（V171-TEST-03）**
- **D-17:** 棚卸しの対象ソースは 4 系統: (1) Phase 2 からの明示繰り越し 2 件（Ollama `_fetch_ollama_models`/`_test_ollama_connection` 重複解消・`RunPodProvider.list_models()` のデッドコード分岐）、(2) CONCERNS.md の Known Bugs / Fragile Areas / Test Coverage Gaps から軽微バグ相当、(3) CLAUDE.md / README の既知の制限から軽微バグ相当（制限として意図されたものは除外）、(4) dialogs/lang/ui_builder 面の新規コードスキャン。
- **D-18:** 修正基準は挙動バグ＋軽微な整理: 挙動に影響するバグは修正し、繰り越し済みのデッドコード/重複も解消。大型構造改善（ocr_dialog.py 2,154 行の分割等）は対象外とし記録のみ。
- **D-19:** 計画時に確定した活き残りリストは全件解消（マイルストーン最終フェーズのため次送りしない）。量が過多の場合のみ planner がプラン分割で対応。
- **D-20:** テスト担保はテスト可能なものは必須: ロジックで検証可能な修正は回帰テスト必須。Tk 描画・目視確認が必要な UI 系は VERIFICATION.md の手動確認項目として記録（既存 human-verify 運用と同じ）。

### Claude's Discretion
- ショートカットダイアログのレイアウト詳細（行構成・ボタン配置・キャプチャ中の視覚フィードバック）と、キーキャプチャの実装詳細（modifier の組み立て・Esc でのキャンセル等）。
- keysym↔人間可読表記の変換関数の API 形状・置き場所。
- 未使用キー検出テストの実装方式（AST 走査 or grep ベース）と動的参照許可リストの形。
- messagebox 種別・文体の統一基準の具体内容（監査時に基準案を確定し RESEARCH.md に記録）。
- ネスト同期解消の実装形（LLMConfigDialog の適用を即 `_save_settings` するか、外側の適用経路と分離するか）。
- 新規コードスキャンの深さ・打ち切り判断（dialogs/lang/ui_builder 面を優先し、時間対効果で researcher が判断）。

### Deferred Ideas (OUT OF SCOPE)
- ショートカットのプロファイル切替・エクスポート/インポート — 需要があれば将来フェーズ
- ocr_dialog.py（2,154 行）・ocr_providers.py（1,524 行）の大型構造分割（CONCERNS.md Tech Debt）— D-18 で対象外と確定。将来の保守性マイルストーン候補
- MAX_UNDO の設定項目化・thumb_cache の LRU 化など CONCERNS.md の Performance/Scaling 項目 — 軽微バグではないため棚卸し対象外（記録のみ）
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V171-UIUX-01 | ユーザーはショートカットを設定ダイアログの GUI で編集できる | `app.py:35-50`（純関数 `merge_shortcuts`/`shift_variant_keysym`・再利用可能）・`app.py:146-186`（抽出対象のバインドロジック・11 コマンドの cmd_map）を確認。Tk `event.state`/`event.keysym` によるキャプチャ方式・重複検出・keysym↔表示変換の設計を Architecture Patterns に記載 |
| V171-UIUX-02 | エラー表示・文言の一貫性が監査・修正される | lang.py 374 キー全数監査で未使用 11 件確定（表参照）。`viewer.py:407,494,499,503` のハードコード日本語・`page_ops.py:954` の messagebox 種別/タイトル不一致を具体的に検出済み |
| V171-UIUX-03 | SettingsDialog / LLMConfigDialog の項目配置・セクションが整理される | `dialogs/settings.py:173-207`（ネストダイアログ起動・即時 `_save_settings` 済みだが app 側 in-memory 反映は外側 Apply 依存）・`dialogs/llm_config.py:1320-1418`（`_apply` の共通/固有混在構造）を確認。CONCERNS.md「Dialog-Level Settings Synchronization」と突き合わせ済み |
| V171-TEST-03 | 既知軽微バグが棚卸しされ、活き残りが解消される | 「棚卸し 生き残り確定表」に Phase 2 繰り越し 2 件（1 件は解消済みと判明）・CONCERNS.md 由来・新規スキャン発見分を統合して記載 |

</phase_requirements>

## Architectural Responsibility Map

単一プロセスの Tkinter デスクトップアプリのため Web 階層（Browser/SSR/API/CDN/DB）は存在しない。本フェーズの capability を既存レイヤーへ割り当てる。

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ショートカットのマージ・重複検出・keysym↔表示変換 | 純ロジック層（`app.py` モジュール関数・`merge_shortcuts`/`shift_variant_keysym` と同居） | — | Tk 非依存にして pytest 直接テスト可能にする（`pagination.py`/`md_render.py` と同じ責務分離パターン） |
| 実キーキャプチャ（KeyPress イベント処理） | UI 層（新設 `dialogs/shortcuts.py`） | — | Tk `event.state`/`event.keysym` に直接依存するため純ロジック層には持ち込めない |
| バインド/アンバインドの実行 | UI 層（`app.py` の新設 `_bind_shortcuts()`） | — | `self.root.bind`/`unbind` は Tk ウィジェット操作そのもの |
| lang.py キー使用状況の監査 | 開発時ツール（テスト/監査スクリプト） | — | 実行時の UI レイヤーではなく静的解析。`test_lang_parity.py` に常設 |
| messagebox 種別・文体の統一 | UI 層（各 Mixin/dialogs の呼び出し箇所） | 文言層（`lang.py`） | 呼び出しパターンの修正は UI 層、文言自体は lang.py |
| SettingsDialog/LLMConfigDialog のセクション再編 | UI 層（`dialogs/settings.py`・`dialogs/llm_config.py`） | — | Tkinter ウィジェット構築ロジックそのもの |
| 既知軽微バグ棚卸し（Ollama 重複解消等） | UI 層 / プロバイダ層（該当箇所ごと） | — | バグごとに所在レイヤーが異なる（本 RESEARCH.md の照合表を参照） |

## Standard Stack

新規ライブラリの追加はない。本フェーズは既存 stdlib（`tkinter`）とプロジェクト既存パターンのみを使用する。

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tkinter` | 標準ライブラリ | ダイアログ構築・KeyPress イベント処理 | 既存全ダイアログと同一基盤 |
| `tkinter.ttk` | 標準ライブラリ | ボタン・Combobox 等のウィジェット | 既存パターン踏襲（`Accent.TButton`等のスタイル） |
| `ast`（監査テストで使用する場合） | 標準ライブラリ | lang.py 未使用キー検出の静的解析 | D-11 の実装方式候補（Claude's Discretion） |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` | 標準ライブラリ | grep ベースのキー参照検出（AST の代替） | D-11 実装を grep ベースにする場合 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| grep ベースのキー使用検出（文字列 `"key_name"` の直接一致） | `ast` によるソース解析（`Str`/`Constant` ノード走査） | AST の方が文字列連結やコメント誤検出に強いが実装コストが高い。本コードベースは動的キー合成（f-string 等）が現状ゼロ（後述 Pitfall 参照）なので grep ベースで十分 |
| 実キーキャプチャの `event.state` ビットマスク判定 | modifier キー単体の `KeyPress`/`KeyRelease` を追跡して手動で状態管理 | `event.state` の方が実装が単純。Windows 専用アプリ（CLAUDE.md 対象 OS）なので `event.state` の意味論が一貫しており採用して問題ない |

**Installation:** 不要（すべて Python 標準ライブラリ）。

**Version verification:** 新規パッケージなし。`requirements.txt` 記載の既存パッケージ（PyMuPDF 1.27.2.2 / Pillow 12.2.0 / tkinterdnd2 0.4.3）は本フェーズで変更しない。

## Package Legitimacy Audit

該当なし — 本フェーズは stdlib（`tkinter`/`ast`/`re`）のみを使用し、新規外部パッケージのインストールは発生しない。`pyproject.toml`/`requirements.txt` の変更も不要。

## 棚卸し 生き残り確定表（D-13・D-17）

`260610-aaa-REVIEW.md`・`02-RESEARCH.md`・`CONCERNS.md`・CLAUDE.md 既知の制限・新規コードスキャンを現行コード（2026-07-05 時点）と照合した結果。

| # | 出所 | 項目 | 判定 | 根拠（ファイル:行番号） | 対応要件 |
|---|------|------|------|--------------------------|----------|
| C1 | Phase 2 繰り越し(1) | `RunPodProvider.list_models()` の `base_url.endswith("/v1")` デッドコード分岐 | **解消済み（対象外）** | `ocr_providers.py:1493-1524`（現行実装に `base_url` 変数自体が存在しない。`git log` 確認: commit `a25d540` "fix(02): WR-03 remove dead branch in RunPod list_models endpoint build" で解消） | 対象外（V171-TEST-03 から除外） |
| C2 | Phase 2 繰り越し(2) | `_fetch_ollama_models`/`_test_ollama_connection` が LM Studio ペア（`_fetch_models`/`_test_connection`→`_probe_lm_provider` に統合済み）とほぼ完全重複 | **活き残り** | `dialogs/llm_config.py:1161-1183`（`_fetch_ollama_models`）・`:1185-1206`（`_test_ollama_connection`）。両者は `update_combo` 相当の分岐のみが差分で `_probe_lm_provider`（:1120-1150）と同型の重複パターン。ステータス文言も `settings_lm_testing`/`settings_lm_test_ok`/`settings_lm_test_fail` を使い回しており `llm_fetching_ollama_models`（lang.py:509/1098）キーが未配線のまま放置されている | V171-TEST-03 |
| C3 | CONCERNS.md Known Bugs | undo no-op（insert_blank/watermark/page_numbers）・watermark rotate=45 | **解消済み（対象外）** | v1.7.0 で修正済みと CONCERNS.md 自身に明記（`page_ops.py` の `page_edit`/`insert` op 化）。Phase 4 のスコープ外 | 対象外 |
| C4 | CONCERNS.md Fragile Areas | Dialog-Level Settings Synchronization（SettingsDialog↔LLMConfigDialog↔OCRDialog） | **活き残り（部分的に v1.6.3 で緩和済み）** | `dialogs/settings.py:188-197`（`on_apply` は `current_settings.update` + `_save_settings` を即座に実行 = ディスクへは即時反映済み）。しかし `app.settings`（メモリ上）は外側 `SettingsDialog._apply`（:209-215）が呼ばれ `callback(new_settings)` が実行されるまで更新されない。外側を「キャンセル」すると **ディスクは更新済み・メモリは旧値のまま** という不整合状態が生じ得る（次回起動まで顕在化しない静かな不整合） | V171-UIUX-03（D-14） |
| C5 | CONCERNS.md Test Coverage Gaps | Multi-Dialog Cascade Interactions（未テスト） | **活き残り（テスト整備要）** | `tests/` 全体に SettingsDialog/LLMConfigDialog の cascade シナリオを検証するテストが存在しない（`test_provider_ui.py` は個別メソッドの unbound テストのみ） | V171-UIUX-03（D-14 の回帰テスト） |
| C6 | 新規スキャン（lang/dialogs） | `pagefolio/viewer.py` のページ拡大ポップアップに LANG 経由でないハードコード日本語文言 | **活き残り（新規発見）** | `viewer.py:407`（`popup.title(f"ページ {i + 1} / {n}")`）・`:494`（`text="🔍 縮小"`）・`:499`（`text="🔍 拡大"`）・`:503`（`text="✕ 閉じる"`）。同メソッド `_show_page_popup`（:388 開始）は `self` を持ち `self._t()` が呼べるにもかかわらず未使用。`lang="en"` でも日本語表示される i18n 違反（M-10 相当のパターンが未修正のまま残存） | V171-UIUX-02（D-12a） |
| C7 | 新規スキャン（messagebox 種別） | `page_ops.py:954` で `err_split_no_range`（エラー系キー名）を `messagebox.showinfo` + `info_title` で表示。直後 :958 の同種検証エラーは `showerror` + `err_title` | **活き残り（新規発見）** | `page_ops.py:945-961`（`_do_split` 内。範囲未入力は showinfo、範囲形式不正は showerror という非対称） | V171-UIUX-02（D-12b/c） |
| C8 | 新規スキャン（見出しアイコン不整合） | `settings_lm_studio_section`/`llm_config_heading`/`settings_open_llm_config` に 🔍（虫眼鏡=検索/OCR を連想）アイコンが使われているが、実態は「設定」全般（Ollama/RunPod/Claude/Gemini/Tesseract 全プロバイダ設定 + タイムアウト/並列度等）を扱うダイアログ | **活き残り（D-16 と同時解消が自然）** | `lang.py:469`（`"🔍 LM Studio (OCR)"`）・`:486`（`"🔍 LLM 設定…"`）・`:489`（`"🔍 LLM 設定"`）。設定系は通常 ⚙ を使う（`settings_heading`:"⚙ 設定"）のと不整合 | V171-UIUX-03（D-16） |
| C9 | CLAUDE.md/README 既知の制限 | 既知の制限セクションの各項目（印刷 Windows 限定・黒塗り/モザイク破壊的操作・cropbox 非物理変更等） | **該当なし（すべて意図された制限）** | 全項目を確認したが「制限として意図されたものは除外」（D-17(3)）に該当し、軽微バグとして扱うべき項目は見つからなかった | 対象外 |

### lang.py 未使用キー監査（D-09/D-10・全 374 キー総当たり）

`pagefolio/`（lang.py 除く）・`tests/`・`plugins/` 全体を対象に、374 キーそれぞれの文字列リテラル出現有無を機械的に検証した（Python スクリプトによる全数チェック。動的キー合成 `f"..."` パターンはコードベース内にゼロ件であることも確認済み — 後述 Pitfall 3 参照）。

| # | キー名 | 判定 | 根拠 |
|---|--------|------|------|
| 1 | `ocr_provider_off_hint` | 未使用 | `lang.py:445/1037` のみに存在。L-5 記載の残り2件のうちの1件（D-09 で削除確定済み） |
| 2 | `tesseract_not_installed` | 未使用 | `lang.py:451/1043` のみに存在。L-5 記載の残り2件のうちの1件（D-09 で削除確定済み）。**注意:** `tesseract_not_installed_hint`（別キー・`llm_config.py:145-148,973-976` で使用中）と混同しないこと |
| 3 | `llm_fetching_ollama_models` | 未使用 | `lang.py:509/1098` のみ。本来 `_fetch_ollama_models`（llm_config.py:1170）が使うべきだが実装時に `settings_lm_testing` を使い回してしまい未配線（C2 の重複解消と同時に解消可能） |
| 4 | `ocr_fetch_models` | 未使用 | `lang.py:526/1115` のみ。ボタン文言は実際には `settings_lm_fetch_models`（llm_config.py:219,291）を使用しており重複定義の可能性 |
| 5 | `ocr_models_fetched` | 未使用 | `lang.py:529/1118` のみ。実際のステータス表示は `settings_lm_test_ok`（llm_config.py 各所）を使用 |
| 6 | `ocr_models_fetch_fail` | 未使用 | `lang.py:530/1119` のみ。実際は `settings_lm_test_fail` を使用 |
| 7 | `ocr_models_fetching` | 未使用 | `lang.py:531/1120` のみ。実際は `settings_lm_testing` を使用 |
| 8 | `sec_compress` | 未使用 | `lang.py:174/773` のみ。`ui_builder.py` の `section()` 呼び出し一覧（14 箇所）に `sec_compress` は含まれない。圧縮保存機能自体は `page_ops.py:977,1021` に現存するが専用セクション見出しは持たない構造になっている（見出し削除時の残骸） |
| 9 | `warn_title` | 未使用 | `lang.py:587/1176` のみ。実際の warning ダイアログは個別タイトル（`warn_del_all_title` 等）を使用しており汎用 `warn_title` は呼ばれていない |

**結論:** D-10 の見積り「約500キー」に対し実数は 374 キー。未使用 9 件 + L-5 既知 2 件（`ocr_provider_off_hint`/`tesseract_not_installed`、上表 1・2 と重複計上）で **確定未使用は 9 件**（L-5 の2件を含む）。全件 D-09 の方針（削除）に従ってよいが、4〜7 番は「本来使われるべきだったが配線し忘れた」ケース（C2 の Ollama 重複解消時に正しく配線すれば削除ではなく活用も選択肢）である点を計画時に判断すること。8番・9番は素直に削除でよい。

## Architecture Patterns

### System Architecture Diagram

ショートカット GUI 編集のデータフロー（新設）:

```
[SettingsDialog] ── 「⌨ ショートカット設定…」ボタン（D-01・二重起動ガード付き既存パターン踏襲）
        │
        ▼
[ShortcutsDialog（新設 dialogs/shortcuts.py）]
        │  cmd_map の 11 コマンドを一覧表示
        │  各行:「コマンド名 | 現在のキー（人間可読表記）| 変更ボタン | 解除ボタン」
        │
        ├─ 「変更」クリック → キャプチャ待機状態
        │       │
        │       ▼
        │  [KeyPress イベント] → event.state（Shift/Control ビット）+ event.keysym
        │       │  純関数 build_keysym(state, keysym) で "<Control-r>" 等の Tk 表記へ変換
        │       ▼
        │  一時保持（保存前は app へ反映しない）
        │
        ├─ 「保存」→ 重複チェック（純関数 find_duplicate_binding・D-04）
        │       │  重複あり → エラー表示・保存拒否
        │       │  重複なし → settings["shortcuts"] へ差分保存
        │       ▼
        │  [app._bind_shortcuts()]（新設・再実行可能メソッド）
        │       │  旧バインド + shift variant を unbind
        │       │  新設定で merge_shortcuts → root.bind 再実行
        │       ▼
        │  即時反映（ダイアログを閉じなくても新キーで動作）
        │
        └─ 「既定に戻す」（全体）/「解除」（個別）→ settings["shortcuts"] から該当分を削除 → 上記と同じ再バインド経路
```

責務境界: 「Tk `event.state`/`event.keysym` に触れるコード」と「`root.bind`/`unbind` を呼ぶコード」は `dialogs/shortcuts.py`/`app.py` に残し、「マージ・重複判定・表示変換」は Tk 非依存の純関数として `app.py` モジュールレベル（既存 `merge_shortcuts`/`shift_variant_keysym` と同居）に置く。

### Recommended Project Structure

```
pagefolio/
├── app.py                    # 既存: merge_shortcuts/shift_variant_keysym に加え
│                              #   新規純関数（keysym→表示変換・重複検出・cmd_map 定義の集約）
│                              #   _bind_shortcuts() をロジックとして新設（D-05）
├── dialogs/
│   ├── shortcuts.py           # 新設: ShortcutsDialog（D-01・実キーキャプチャ UI・D-02）
│   ├── settings.py             # 既存: 「⌨ ショートカット設定…」ボタン追加・3セクション再編（D-16）
│   └── llm_config.py           # 既存: 共通/固有グルーピング再編（D-15）・Ollama 重複解消（C2）
├── viewer.py                   # 既存: _show_page_popup のハードコード文言を self._t() 経由へ修正（C6）
├── page_ops.py                 # 既存: messagebox 種別/タイトル不一致修正（C7）
└── lang.py                     # 既存: 未使用キー削除（D-09・9件）・新規キー追加（ショートカットUI文言等）

tests/
├── test_v150_regression.py     # 既存: merge_shortcuts/shift_variant_keysym テストの隣に
│                                #   D-04（重複検出）・D-07（keysym↔表示変換）純関数テストを追加
├── test_lang_parity.py         # 既存: 未使用キー検出テストを追加（D-11）
└── test_provider_ui.py または新設 test_dialog_cascade.py
                                 # 既存/新設: D-14 ネストダイアログのトランザクション境界回帰テスト
```

### Pattern 1: Tk 非依存の純関数として keysym 変換・重複検出を実装

**What:** `merge_shortcuts`/`shift_variant_keysym`（`app.py:35-50`）と同じレベルの Tk 非依存モジュール関数として、(a) Tk keysym 文字列（例 `"<Control-o>"`）を人間可読表記（例 `"Ctrl+O"`）へ変換する関数、(b) `event.state`/`event.keysym` から Tk keysym 文字列を組み立てる関数、(c) 現在の shortcuts dict に対して新規割当が重複していないか判定する関数、の3つを追加する。

**When to use:** D-04（重複検出）・D-07（表示変換）の実装全体。

**Example（既存の隣接パターン・そのまま参考にする）:**
```python
# Source: pagefolio/app.py:35-50（既存・Tk/fitz 非依存の純関数）
def merge_shortcuts(default_shortcuts, custom_shortcuts):
    """既定＋ユーザー設定のショートカット辞書をマージする（後勝ち）。"""
    return {**default_shortcuts, **custom_shortcuts}


def shift_variant_keysym(keysym):
    """Control-小文字 の keysym から Shift 補完用の大文字版 keysym を返す。"""
    if keysym.startswith("<Control-") and len(keysym) == 11 and keysym[-2].islower():
        return keysym[:-2] + keysym[-2].upper() + ">"
    return None
```

**推奨する新規関数のイメージ（Claude's Discretion・具体形は実装時に確定）:**
```python
# app.py に追加するイメージ（テスト容易性のため Tk 非依存を維持）
_MOD_ORDER = ("Control", "Alt", "Shift")  # Tk バインド構文の慣例順


def build_keysym_from_event(state, keysym, shift_mask=0x1, control_mask=0x4, alt_mask=0x20000):
    """event.state ビットマスクと event.keysym から Tk bind 用の keysym 文字列を組み立てる。

    modifier のみの keysym（Control_L 等）は呼び出し側で無視すること
    （実際のキー入力を待つ・Pitfall 2 参照）。
    """
    mods = []
    if state & control_mask:
        mods.append("Control")
    if state & alt_mask:
        mods.append("Alt")
    if state & shift_mask:
        mods.append("Shift")
    if not mods:
        return f"<{keysym}>"
    return f"<{'-'.join(mods)}-{keysym}>"


def find_duplicate_binding(shortcuts, cmd_name, new_keysym):
    """new_keysym が cmd_name 以外の既存コマンドと重複していないか判定する（D-04）。

    戻り値: 衝突しているコマンド名（str）、なければ None。
    """
    if not new_keysym:
        return None
    for other_cmd, other_keysym in shortcuts.items():
        if other_cmd != cmd_name and other_keysym == new_keysym:
            return other_cmd
    return None


def keysym_to_display(keysym):
    """Tk keysym 文字列を人間可読表記へ変換する（D-07）。

    例: "<Control-o>" → "Ctrl+O"、"<Delete>" → "Delete"、"<F5>" → "F5"
    """
    if not keysym:
        return ""
    inner = keysym.strip("<>")
    parts = inner.split("-")
    *mods, key = parts
    display_mods = {"Control": "Ctrl", "Alt": "Alt", "Shift": "Shift"}
    out = [display_mods.get(m, m) for m in mods]
    out.append(key.upper() if len(key) == 1 else key)
    return "+".join(out)
```

### Pattern 2: 再バインド可能なメソッドへの抽出（D-05）

**What:** `app.py:146-186` の `__init__` 直書きバインドロジックを `_bind_shortcuts()` メソッドへ切り出し、初回呼び出し（`__init__` から）と GUI 編集後の再呼び出しの両方に対応させる。再呼び出し時は **旧バインドと shift variant の両方を unbind** してから再バインドしないと、キー変更前の旧キーが古いコマンドに紐づいたまま残る（Pitfall 1 参照）。

**When to use:** D-05 全体。ShortcutsDialog の「保存」ボタンのコールバックから呼ぶ。

**Example（現状の抽出対象・そのまま）:**
```python
# Source: pagefolio/app.py:157-186（現状 __init__ 内の直書き）
custom_shortcuts = self.settings.get("shortcuts", {})
shortcuts = merge_shortcuts(default_shortcuts, custom_shortcuts)

cmd_map = {
    "open_file": self._open_file,
    # ... 11 コマンド
}

for cmd_name, keysym in shortcuts.items():
    func = cmd_map.get(cmd_name)
    if func and keysym:
        try:
            self.root.bind(keysym, lambda e, f=func: f())
            variant = shift_variant_keysym(keysym)
            if variant is not None:
                self.root.bind(variant, lambda e, f=func: f())
        except Exception as ex:
            logger.warning(f"Failed to bind shortcut {keysym} for {cmd_name}: {ex}")
```

**抽出後のイメージ（Claude's Discretion・cmd_map の定義場所も検討対象）:**
```python
def _bind_shortcuts(self):
    """settings["shortcuts"] から現在のバインドを（再）構築する（D-05）。

    再呼び出し時は self._bound_keysyms（前回バインドした keysym 一覧）を
    先に unbind してから新しいバインドを張る。
    """
    for old_keysym in getattr(self, "_bound_keysyms", []):
        try:
            self.root.unbind(old_keysym)
        except Exception as e:
            logger.debug("ショートカット unbind 失敗: %s", e)

    custom_shortcuts = self.settings.get("shortcuts", {})
    shortcuts = merge_shortcuts(self._default_shortcuts, custom_shortcuts)
    bound = []
    for cmd_name, keysym in shortcuts.items():
        func = self._cmd_map.get(cmd_name)
        if func and keysym:
            try:
                self.root.bind(keysym, lambda e, f=func: f())
                bound.append(keysym)
                variant = shift_variant_keysym(keysym)
                if variant is not None:
                    self.root.bind(variant, lambda e, f=func: f())
                    bound.append(variant)
            except Exception as ex:
                logger.warning(f"Failed to bind shortcut {keysym} for {cmd_name}: {ex}")
    self._bound_keysyms = bound
```

### Pattern 3: LLMConfigDialog 適用の独立トランザクション化（D-14）

**What:** 現状 `dialogs/settings.py:188-197` の `on_apply` は既に `_save_settings()` をその場で呼んでおり「ディスクへの永続化」自体は独立トランザクション化されている（v1.6.3 で修正済み）。しかし `app.settings`（メモリ上の実行時状態）は外側 `SettingsDialog._apply`（:209-215）経由でしか更新されないため、**外側キャンセル時にディスクとメモリが食い違う**（C4 参照）。D-14 を満たすには、ネスト適用時に `app` 側のコールバック（例: `app._apply_settings` 相当）も同時に呼び、UI 再構築まで含めて完結させる必要がある。

**When to use:** D-14 の実装全体。`on_apply` コールバックのシグネチャ変更（`SettingsDialog` → `app` への直接コールバック引き回し）が必要になる可能性がある。

**Example（現状・修正対象）:**
```python
# Source: pagefolio/dialogs/settings.py:188-197
def on_apply(llm_settings):
    self.current_settings.update(llm_settings)
    from pagefolio.settings import _save_settings
    _save_settings(self.current_settings)
    # ← ここで app.settings（メモリ）・UI 再構築が反映されていない
```

**修正方針のイメージ（Claude's Discretion）:** `SettingsDialog` に `apply_callback`（app 側の `_apply_settings` 相当）を追加引数として渡し、`on_apply` 内で `self.current_settings` の更新・保存に加えて `apply_callback(dict(self.current_settings))` を呼ぶことで、外側ダイアログの Apply/Cancel と独立して即座に `app.settings` と UI へ反映する。外側の「キャンセル」ボタンは（LLM 設定がすでに確定済みのため）テーマ/フォント欄の変更のみを破棄する formalな意味になる。

### Pattern 4: messagebox 種別・タイトルの統一基準（D-12b/c）

**What:** 現行コードの実態から帰納した基準案（監査で確認した 60 箇所超の呼び出しパターンから抽出）:
- `showerror` + `err_title`: 操作が失敗し、ユーザーの入力/状態を正す必要がある場合（例外捕捉時・不正な範囲指定等）
- `showwarning` + 個別タイトル（`warn_del_all_title` 等）: 破壊的操作の実行前確認や、入力自体は正しいが結果が危険な場合
- `showinfo` + `info_title`: 破壊的でない案内・状態通知（「ファイルを開いてください」等）
- `askyesno` + `confirm_title`: ユーザーに Yes/No の意思決定を求める場合

**When to use:** D-12(b) の基準として RESEARCH.md に確定。C7（`page_ops.py:954`）はこの基準に従うと「範囲文字列が空」は**入力を正すべきエラー**に近く `showerror`+`err_title` へ統一するのが妥当（直後の :958 と対称にする）。

### Anti-Patterns to Avoid

- **`_show_page_popup` のような「`self` があるのに `self._t()` を使わない」ハードコード:** C6 のパターン。新規 UI コードでは必ず LANG キー経由にする。既存の類似メソッド（`ui_builder.py` の `section()` 呼び出し等）を確認してから実装する。
- **重複キー検出を「保存後にエラーメッセージを出す」だけで終わらせる:** D-04 は「保存を拒否する」ことが要件。UI 側で重複時に保存ボタンを無効化するか、保存処理内で例外的に return して settings への書き込み自体を止めること。
- **`_bind_shortcuts()` の再呼び出しで unbind を忘れる:** 旧キーがコマンドに紐づいたまま残ると「変更したのに古いキーも効く」というユーザーから見て説明しづらいバグになる（Pitfall 1）。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| キー修飾子の判定 | 独自のグローバル修飾キー追跡（KeyPress/KeyRelease で Control_L 等を手動フラグ管理） | `event.state` ビットマスク（Shift=0x1・Control=0x4） | Tk 標準機能で十分・Windows専用アプリなので state の意味論が安定している（[Tk bind マニュアル](https://www.tcl-lang.org/man/tcl8.4/TkCmd/bind.htm)） |
| lang.py 未使用キー検出 | 手作業でのキー洗い出し（374 件を目視） | 本 RESEARCH.md の grep ベース全数チェック手法（Python スクリプトで再現可能）をそのままテスト化 | 手作業は見落とし・再現性なしのリスクが高い。機械的チェックなら D-11 の常設回帰テストにそのまま転用できる |
| ダイアログ間の設定同期 | 独自のイベントバス/Observer パターンを新規導入 | 既存の「コールバック引き回し」パターン（`on_apply` 引数）を素直に拡張 | 3階層ダイアログ（Settings→LLMConfig→OCR）程度の規模でイベントバスは過剰設計。既存パターンの延長で解決可能（Pattern 3 参照） |

**Key insight:** 本フェーズも新規抽象化はほぼ不要。既存の `merge_shortcuts`/`shift_variant_keysym` パターンを横展開し、既存の「純関数 + 薄い Tk 配線」という規約（`pagination.py`/`md_render.py`/`ocr_pipeline.py`）に従うだけでよい。

## Runtime State Inventory

> 本フェーズは新規ダイアログ追加・既存メソッド抽出（`_bind_shortcuts`）・lang.py キー削除を含むため、リファクタ相当のトリガーに該当し記載する。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `pagefolio_settings.json` の `shortcuts` キー（既存・差分保存の意味論は変更しない）。lang.py キー削除は `settings.json` に保存された値には影響しない（キーは UI 文言用でユーザーデータではない） | なし（既存の差分保存ロジックをそのまま使う） |
| Live service config | なし — 本フェーズは外部サービス（n8n 等）に依存しない | なし |
| OS-registered state | なし — Windows タスクスケジューラ等の登録はこのアプリの機能に存在しない | なし |
| Secrets/env vars | なし — 本フェーズは APIキー解決ロジック（Phase 1 確定）に触れない | なし |
| Build artifacts / installed packages | なし — 新規ファイル追加（`dialogs/shortcuts.py`）のみで、既存モジュールの import パス破壊的変更はない想定。ただし `app.py` の `cmd_map`/`default_shortcuts` を `_bind_shortcuts()` へ移す際、これらを参照する既存テスト（`test_v150_regression.py`）の import 元を変更しないよう注意 | コード編集のみ（`test_v150_regression.py` の `from pagefolio.app import merge_shortcuts, shift_variant_keysym` は影響を受けない想定） |

**結論:** 本フェーズはランタイム状態（DB・外部サービス・OS登録・シークレット）に一切影響しない。唯一の実務対応は `app.py` 内でのメソッド抽出時に既存 import パスを壊さないことの確認。

## Common Pitfalls

### Pitfall 1: 再バインド時に旧キーの unbind を忘れる
**What goes wrong:** D-05 の「保存で即時反映」を素朴に実装すると、新しいキーをバインドするだけで旧キー（および shift variant）を unbind し忘れ、「新キーでも旧キーでも同じコマンドが動く」状態になる。さらに旧キーが**別コマンドへの再割当先**だった場合、2つのコマンドが同じキーで発火する事態になり得る。
**Why it happens:** `root.bind(keysym, func)` は指定した keysym への新規バインドを追加するだけで、他の keysym への既存バインドには影響しない。
**How to avoid:** Pattern 2 のように、バインド済み keysym 一覧（`_bound_keysyms`）を保持し、再バインド前に全て unbind してから新しい shortcuts dict で再構築する。
**Warning signs:** キー変更後に旧キーを押しても（変更したはずのコマンドが）まだ反応する。

### Pitfall 2: 修飾キー単体の KeyPress をキャプチャ結果として確定してしまう
**What goes wrong:** ユーザーが Ctrl を押した瞬間に `KeyPress` イベントが発火し、`event.keysym` が `"Control_L"` になる。これをそのままキャプチャ結果として `<Control_L>` のような無意味な keysym を保存してしまう。
**Why it happens:** 修飾キー単体でも `KeyPress` イベントは発火する。ユーザーは「Ctrl を押しながら別のキーを押す」つもりで、まだ完了していない。
**How to avoid:** `event.keysym` が `Control_L`/`Control_R`/`Alt_L`/`Alt_R`/`Shift_L`/`Shift_R`/`Caps_Lock`/`Num_Lock` 等の修飾キー単体名のときはキャプチャを継続し、実際の非修飾キーが押されるまで待つ。
**Warning signs:** ショートカット一覧に `Ctrl+Control_L` のような表示が出る。

### Pitfall 3: lang.py 未使用キー検出で動的キー合成を見落とす（現状はゼロ件だが将来注意）
**What goes wrong:** `self._L[f"foo_{suffix}"]` のような動的キー合成があると、grep ベースの文字列一致チェックが「未使用」と誤検出（false positive）する。
**Why it happens:** 静的解析は文字列リテラルの完全一致でしか検出できない。
**How to avoid:** 本 RESEARCH.md 作成時点でコードベース全体を `_t(f"` / `_L[f"` / `_L.get(f"` パターンで検索し、**動的キー合成は現状ゼロ件**であることを確認済み（`_provider_display_name` 等の類似処理も全て分岐ごとの静的リテラル参照）。D-11 の回帰テストにはこの前提が崩れた場合の許可リスト機構（キー名のプレフィックスやコメントで除外指定できる仕組み）を用意しておくと将来の再発を防げる。
**Warning signs:** 新規実装で `f"..._label"` のようなキー名合成パターンが増えたら要注意。

### Pitfall 4: C2（Ollama 重複解消）と lang.py 未使用キー削除（4〜7番）を独立に扱ってしまう
**What goes wrong:** Ollama ペアの重複を `_probe_lm_provider` 型の共通ヘルパーへ統合する際、`llm_fetching_ollama_models`/`ocr_fetch_models` 等の未配線キーをそのまま削除してしまうと、後から「Ollama 専用の文言が欲しい」という要望が出た時に再実装が必要になる。逆に「削除せず配線する」を選ぶ場合、共通ヘルパーの設計（`_probe_lm_provider` は LM Studio 専用の文言 `settings_lm_testing` 等を使っている）との整合を取る必要がある。
**Why it happens:** C2（棚卸し）と lang.py 監査（D-10）は別の要件（V171-TEST-03 と V171-UIUX-02）に属するが、実装上は同じコード箇所（`llm_config.py` の Ollama セクション）に触れる。
**How to avoid:** 計画時にこの2つを同一プラン内の連続タスクとして扱い、「Ollama 重複解消時に未配線キーをどう扱うか」を1回の設計判断で確定する（削除 or 配線、どちらでも良いが両方を別々のタスクで矛盾なく行う）。
**Warning signs:** 同じ `llm_config.py` の同じ行範囲を別々のプランが別々の意図で編集し、片方の変更がもう片方でコンフリクトする。

### Pitfall 5: D-14 のネスト同期修正が LLMConfigDialog 単独起動経路（OCRDialog からの起動）を壊す
**What goes wrong:** `LLMConfigDialog` は `SettingsDialog` 経由だけでなく `OCRDialog`（「⚙ LLM 設定…」ボタン）からも起動される。Pattern 3 の修正（`apply_callback` 引数追加）を `SettingsDialog` 起動経路にのみ実装すると、`OCRDialog` 起動経路の `on_apply` シグネチャと不整合が生じる可能性がある。
**Why it happens:** `LLMConfigDialog.__init__` の `on_apply` コールバックは呼び出し元ごとに異なる実装（`SettingsDialog._open_llm_config.on_apply` と `OCRDialog` 側の同名メソッド）を持つ。
**How to avoid:** `LLMConfigDialog` 自体のインターフェース（`on_apply(llm_settings)` の呼び出し規約）は変更せず、`SettingsDialog` 側の `on_apply` 実装だけを「即座に app へ反映する」ように変更する（`OCRDialog` 側は元々ネストしていないので影響なし）。
**Warning signs:** `OCRDialog` から LLM 設定を開いて適用した際に例外が発生する、またはモデル選択が反映されない。

## Code Examples

### 現行のショートカットバインド（抽出前・そのまま参考）
```python
# Source: pagefolio/app.py:146-186
default_shortcuts = {
    "open_file": "<Control-o>",
    "save_file": "<Control-s>",
    "undo": "<Control-z>",
    "redo": "<Control-y>",
    "save_as": "<Control-S>",
    "delete": "<Delete>",
    "toggle_mode": "<F5>",
    "print_pdf": "<Control-p>",
}
custom_shortcuts = self.settings.get("shortcuts", {})
shortcuts = merge_shortcuts(default_shortcuts, custom_shortcuts)

cmd_map = {
    "open_file": self._open_file,
    "save_file": self._save_file,
    "undo": self._undo,
    "redo": self._redo,
    "save_as": self._save_as,
    "delete": self._delete_selected,
    "toggle_mode": self._toggle_edit_mode,
    "print_pdf": self._print_pdf,
    "rotate_right": lambda: self._rotate_selected(90),
    "rotate_left": lambda: self._rotate_selected(270),
    "rotate_180": lambda: self._rotate_selected(180),
}
```

### KeyPress イベントからの keysym 構築（Tk 標準機構・[出典](https://www.tcl-lang.org/man/tcl8.4/TkCmd/bind.htm)）
```python
# ShortcutsDialog 内のキャプチャハンドラのイメージ
_MODIFIER_KEYSYMS = {
    "Control_L", "Control_R", "Alt_L", "Alt_R",
    "Shift_L", "Shift_R", "Caps_Lock", "Num_Lock",
}

def _on_capture_keypress(self, event):
    if event.keysym in _MODIFIER_KEYSYMS:
        return  # Pitfall 2: 修飾キー単体では確定しない
    new_keysym = build_keysym_from_event(event.state, event.keysym)
    # duplicate check → find_duplicate_binding(...)
    # UI へ反映（保存前の一時状態）
```

### 既存 messagebox 呼び分けの対称パターン（修正参考・page_ops.py 分割処理）
```python
# Source: pagefolio/page_ops.py:945-961（C7 修正対象）
if not range_str.strip():
    messagebox.showinfo(self._t("info_title"), self._t("err_split_no_range"))  # 修正対象
    return
ranges = self._parse_page_ranges(range_str, n)
if ranges is None:
    messagebox.showerror(
        self._t("err_title"), self._t("err_split_range").format(n=n)
    )  # こちらの kind/title と揃える
    return
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| ショートカットは `pagefolio_settings.json` の直接編集のみ | 設定ダイアログ GUI から実キーキャプチャで編集 | 本フェーズ（V171-UIUX-01） | JSON 直接編集の知識不要になり、重複割当も構造的に防止される |
| LLMConfigDialog のネスト適用がディスクのみ即時反映・メモリ/UI は外側依存 | ネスト適用が app のメモリ状態・UI まで即座に反映する独立トランザクション | 本フェーズ（V171-UIUX-03・D-14） | 外側キャンセル時のディスク/メモリ不整合が解消される |
| 「LM Studio (OCR)」という実態と不一致の見出し（6+プロバイダ対応済み） | 「AI・OCR 設定」等の実態に即した見出し・3セクション構成 | 本フェーズ（V171-UIUX-03・D-16） | ユーザーが実際の機能範囲を見出しから正しく推測できる |

**Deprecated/outdated:**
- `pagefolio/lang.py` の未使用 9 キー（`ocr_provider_off_hint`・`tesseract_not_installed`・`llm_fetching_ollama_models`・`ocr_fetch_models`・`ocr_models_fetched`・`ocr_models_fetch_fail`・`ocr_models_fetching`・`sec_compress`・`warn_title`）: 削除対象（一部は Ollama 重複解消時の配線先として再利用可能・Pitfall 4 参照）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `event.state` の Alt ビットマスクは Windows Tk で `0x20000` である | Architecture Patterns Pattern 1・Code Examples | プラットフォーム/Tcl-Tkバージョンにより Alt のビット位置が異なる場合がある。CLAUDE.md の対象 OS は Windows 11 のみなので実害は限定的だが、実装時に実機で `event.state` の実測値を確認すること（`checkpoint:human-verify` 相当） |
| A2 | messagebox 種別の統一基準（Pattern 4 の4分類）は現行コードの実態から帰納した基準であり、プロジェクトのどこにも明文化された既存規約はない | Architecture Patterns Pattern 4 | この基準自体がユーザーの意図と異なる可能性がある。discuss-phase で確定した「Claude's Discretion」領域なので、計画時にこの基準案を採用するか、別の基準を立てるかは実装者の判断に委ねられる |
| A3 | lang.py 未使用キー 9 件は「本当に不要」であり、動的参照や将来の再利用予定がない | lang.py 未使用キー監査表 | grep ベースの検出のため、コメントやドキュメント内の参照（コード実行には影響しないが意図を示す記述）までは検出していない。削除前に git blame 等で導入経緯を確認すると安全（特に4〜7番は Ollama 実装時の配線し忘れの可能性が高い） |

**リスク低減策:** A1 は実装時の実機確認（Windows 11 環境）で解消可能。A2 は discuss-phase 済みの Claude's Discretion 領域のため計画時にそのまま採用してよい。A3 は削除前に `git log -p -- pagefolio/lang.py` で各キーの追加コミットを確認することを推奨。

## Open Questions

1. **D-14 のネスト同期修正で `apply_callback` を追加する場合、`LLMConfigDialog.__init__` のシグネチャを変更するか、`SettingsDialog._open_llm_config` 内の `on_apply` クロージャだけで完結させるか**
   - What we know: `LLMConfigDialog` 自体は `on_apply(llm_settings)` という単純なコールバック契約のみを持ち、呼び出し元（`SettingsDialog`/`OCRDialog`）ごとに異なる実装を注入している
   - What's unclear: `SettingsDialog` が `app` の `_apply_settings` を直接呼べるようにするには、`SettingsDialog.__init__` に新しい引数（例: `apply_callback`）を追加する必要があるか、既存の `callback`（外側の Apply 用）を再利用して条件分岐するか
   - Recommendation: `SettingsDialog.__init__` に新規引数を追加せず、既存の `self.callback`（外側 Apply 用）とは別に `app` 側から渡される軽量な `on_llm_apply` 相当の関数を任意引数として受け取る形にすると後方互換を壊さない（Pitfall 5 の OCRDialog 経路には影響しない設計にできる）

2. **lang.py 未使用キー 4〜7番（`llm_fetching_ollama_models` 等）を削除するか、Ollama 重複解消時に正しく配線するか**
   - What we know: これらのキーは明らかに「Ollama 用に用意されたが実装時に使われなかった」形跡がある（Claude/Gemini/RunPod は対応する `llm_fetching_X_models` キーを実際に使っている）
   - What's unclear: Ollama 専用の文言を持たせる価値があるか（`_probe_lm_provider` 型の共通ヘルパーに統合すると LM Studio と同じ汎用文言になり、Ollama 固有キーは自然と不要になる可能性がある）
   - Recommendation: C2（Ollama 重複解消）の実装方針が「共通ヘルパーへの統合」なら、これらのキーは削除でよい（Pitfall 4 参照）。個別実装を維持するなら配線する

## Environment Availability

該当なし — 本フェーズはコード/文言/UI 改修のみで、新規の外部ツール・サービス・ランタイム依存は発生しない（既存 Windows 11 + Python 3.8+ + Tkinter 環境で完結）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml`（`[tool.pytest.ini_options]`・`testpaths = ["tests"]`） |
| Quick run command | `pytest tests/test_v150_regression.py tests/test_lang_parity.py tests/test_provider_ui.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V171-UIUX-01 | `merge_shortcuts`/新規 keysym 変換・重複検出純関数の正当性 | unit | `pytest tests/test_v150_regression.py -k shortcut -x` | ✅（既存ファイルへ追加） |
| V171-UIUX-01 | 実キーキャプチャ UI（KeyPress→保存→即時反映） | manual-only | — | ❌ Wave 0（VALIDATION.md 手動確認項目として記録） |
| V171-UIUX-02 | lang.py 未使用キー検出の回帰 | unit | `pytest tests/test_lang_parity.py -x` | ✅（既存ファイルへ追加） |
| V171-UIUX-02 | messagebox 種別/タイトル統一の回帰（C7 修正確認） | unit | `pytest tests/test_pdf_ops.py -k split -x` | ✅（既存ファイルの該当テストを拡張） |
| V171-UIUX-03 | LLMConfigDialog ネスト適用の独立トランザクション性（D-14） | unit | `pytest tests/test_provider_ui.py -k nested -x` | ❌ Wave 0（新規テスト追加） |
| V171-TEST-03 | C2（Ollama 重複解消後の共通ヘルパー） | unit | `pytest tests/test_provider_ui.py -k ollama -x` | ❌ Wave 0（新規テスト追加） |

### Sampling Rate
- **Per task commit:** `pytest tests/test_v150_regression.py tests/test_lang_parity.py tests/test_provider_ui.py -x`
- **Per wave merge:** `pytest`（フルスイート・707件超をグリーン維持）
- **Phase gate:** フルスイートグリーン + `ruff check . && ruff format .` 通過を `/gsd-verify-work` 前に確認

### Wave 0 Gaps
- [ ] D-14（ネスト同期）の cascade シナリオテスト新規追加（`test_provider_ui.py` へのクラス追加、または `test_dialog_cascade.py` 新設）
- [ ] C2（Ollama 重複解消）の共通ヘルパーテスト新規追加
- [ ] ShortcutsDialog の keysym 変換・重複検出純関数のテスト（新規関数のため既存ファイルなし・`test_v150_regression.py` へ追加が自然）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | デスクトップアプリでユーザー認証機構自体が存在しない（対象外） |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 単一ユーザーローカルアプリのため該当なし |
| V5 Input Validation | yes | ショートカットキー入力（Tk keysym 文字列としてのみ扱い、シェルコマンド実行等には一切使わない）・重複検出はロジックレベルのバリデーション |
| V6 Cryptography | no | 本フェーズはパスワード/暗号化機能を変更しない（既存 AES-256 実装は対象外） |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 設定ファイル（`pagefolio_settings.json`）への機密情報混入 | Information Disclosure | 既存 `_SENSITIVE_KEYS` ガード（`settings.py:17-28`）を維持。本フェーズはこのガードに触れない |
| ショートカット GUI がキー入力を任意のコマンド文字列として実行してしまう | Elevation of Privilege（該当性は低いが設計上の注意点） | keysym はあくまで `cmd_map` の固定キー集合（11種）へのマッピングのみに使い、ユーザー入力文字列を `eval`/`exec`/シェルコマンドとして解釈しない（現行 `cmd_map` 設計を維持すれば自然に満たされる） |

## Sources

### Primary (HIGH confidence)
- 現行コード直接読解: `pagefolio/app.py`・`pagefolio/lang.py`・`pagefolio/viewer.py`・`pagefolio/page_ops.py`・`pagefolio/dialogs/settings.py`・`pagefolio/dialogs/llm_config.py`・`pagefolio/ocr_providers.py`・`pagefolio/settings.py`・`pagefolio/constants.py`
- Python スクリプトによる lang.py 374 キー全数機械チェック（本セッション実行・grep 相当の文字列一致検証）
- `git log --oneline -- pagefolio/ocr_providers.py` によるコミット履歴確認（RunPod デッドコード解消の裏取り・commit `a25d540`）
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md`（L-5/L-6 原典）
- `.planning/phases/02-ocr/02-RESEARCH.md`（Phase 4 への繰り越し候補の原典）
- `.planning/codebase/CONCERNS.md`（Fragile Areas・Known Bugs・Test Coverage Gaps）
- `.planning/phases/01-api-llm/01-CONTEXT.md`・`.planning/phases/03-v1-5-0/03-CONTEXT.md`（先行決定の確認）

### Secondary (MEDIUM confidence)
- [Tk bind マニュアル](https://www.tcl-lang.org/man/tcl8.4/TkCmd/bind.htm) — event pattern 構文・modifier 指定順
- [Tkinter Event Binding - Python Tutorial](https://www.pythontutorial.net/tkinter/tkinter-event-binding/) — `event.keysym`/`event.char` の使い分け

### Tertiary (LOW confidence)
- なし（本フェーズは全て HIGH/MEDIUM 根拠に基づく）

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 新規パッケージなし、既存 stdlib のみ
- Architecture: HIGH — 全パターンは現行コードの直接読解と既存確立パターン（`pagination.py`/`ocr_pipeline.py`型）の踏襲
- 棚卸し（V171-TEST-03）: HIGH — grep/git log による裏取り済み。C1（RunPod）は commit ハッシュまで特定
- lang.py 監査（V171-UIUX-02）: HIGH — 374キー全数の機械的検証（Python スクリプト実行結果）
- Tk `event.state` の Alt ビットマスク: MEDIUM — Windows Tk での一般的な値だが実機未検証（A1 参照）

**Research date:** 2026-07-05
**Valid until:** 30日（安定した stdlib/既存パターンの応用が中心のため、コード変更が早いフェーズではない）