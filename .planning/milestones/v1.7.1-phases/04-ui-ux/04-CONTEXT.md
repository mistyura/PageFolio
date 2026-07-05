# Phase 4: UI/UX 磨き込み + 既知バグ棚卸し - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

ユーザーはショートカットを設定ダイアログの GUI で編集でき（V171-UIUX-01・JSON 直接編集不要化）、エラー表示・文言の一貫性が監査・修正され（V171-UIUX-02・ja/en 辞書の欠落/未使用キー解消・L-5 吸収）、SettingsDialog / LLMConfigDialog の項目配置・セクションが整理される（V171-UIUX-03）。既知軽微バグの棚卸しリストが現行コード照合で確定し、活き残りが解消・テストで担保される（V171-TEST-03・L-6 と重複しない範囲）。v1.7.1 マイルストーンの最終フェーズ。

新機能追加・サムネイル仮想化（PERF-01・将来）・OCR 実行フロー自体の変更・ocr_dialog.py 等の大型構造リファクタはスコープ外。

</domain>

<decisions>
## Implementation Decisions

### ショートカット GUI 編集（V171-UIUX-01）
- **D-01:** 編集 UI は**専用ダイアログ**。SettingsDialog に「⌨ ショートカット設定…」ボタンを追加して開く（既存「LLM設定を開く」ボタンと同型パターン）。
- **D-02:** キー入力は**実キーキャプチャ方式**。対象行の「変更」を押すと入力待ち状態になり、実際にキーを押して取得（Tk の KeyPress イベントから keysym を構築）。
- **D-03:** 対象は **cmd_map の全 11 コマンド**（既定キーあり 8 種 + rotate_right / rotate_left / rotate_180）。rotate 系は「未割当」として表示し GUI から新規割当できる。
- **D-04:** 同一キーの重複割当は**保存時に拒否**（どのコマンドと衝突しているかをエラー表示・保存不可）。後勝ちバインドによる無言の上書きを構造的に防ぐ。
- **D-05:** 変更は**保存で即時反映**。旧バインドを unbind → 新設定で再バインド。バインド処理は現在 `PDFEditorApp.__init__` 内に直書きのため、再実行可能なメソッドへ切り出す（副次効果としてテスト可能化）。
- **D-06:** 既定復帰は**全体リセット＋個別解除**の両導線。settings の `shortcuts` キーは既定との**差分のみ保存**（現行 `merge_shortcuts` の意味論を維持）。
- **D-07:** 一覧のキー表記は**人間可読形式**（「Ctrl+O」「Shift+Delete」等）。内部保存は Tk keysym のまま。keysym↔表示の変換は純関数化してテスト（`merge_shortcuts`/`shift_variant_keysym` と同居が自然）。
- **D-08:** キーを外して**「割当なし（無効化）」にできる**（例: Delete の誤押し防止）。現行実装も keysym が空ならバインドしないため自然に実現可能。

### 文言/エラー一貫性監査（V171-UIUX-02）
- **D-09:** L-5 の未使用キー 2 件（`ocr_provider_off_hint` / `tesseract_not_installed`）は**削除**（ja/en 両辞書から。将来必要になれば再追加）。※`ocr_provider_name_tesseract` は Phase 2 照合で使用中と確定済み。
- **D-10:** 未使用キー監査は **lang.py 全体スキャン**（約 500 キー）。動的参照（キー名合成等）の偽陽性に注意し、個別確認の上で削除。
- **D-11:** 未使用キー検出を**回帰テストとして常設**（`test_lang_parity.py` に「全キーがソースのどこかで参照されている」検査を追加・動的参照用の許可リスト付き）。
- **D-12:** エラー表示監査は 3 点すべてを対象: (a) LANG 経由でない**ハードコード文言の検出と LANG キー化**、(b) **messagebox 種別**（showerror/showwarning/showinfo）の使い分け基準の確立と不一致修正、(c) **ダイアログタイトル・文体**（です/ます調・句点等）の統一。
- **D-13:** 監査結果の記録は Phase 2 前例踏襲: **RESEARCH.md に照合表**（項目 × 判定 × 根拠ファイル:行番号）。

### SettingsDialog / LLMConfigDialog 整理（V171-UIUX-03）
- **D-14:** CONCERNS.md 記録のネストダイアログ fragile を**本フェーズで解消**する: LLMConfigDialog（ネスト側）の「適用」は**その場で確定する独立トランザクション**とし、外側 SettingsDialog のキャンセルは**外側の項目（テーマ/フォント）のみに作用**する。このセマンティクスを回帰テストで固定。
- **D-15:** LLMConfigDialog は**共通/固有の分離明確化**: 「全プロバイダ共通の設定（max_tokens・temperature・タイムアウト・プロンプト等）」と「選択中プロバイダ固有の設定（URL・モデル・APIキー）」を見出し付きで明確にグルーピングし直す。1 枚・プロバイダ選択でセクション切替という現行構造は維持（タブ化・スクロール化はしない）。
- **D-16:** SettingsDialog は**見出し更新＋セクション再構成**: 実態と不一致の「LM Studio (OCR)」見出しを「AI・OCR 設定」等へ改称し、「外観（テーマ/フォント）」「操作（ショートカット）」「AI・OCR」の 3 セクション構成へ再編。D-01 のショートカットボタンはここに収める。

### 既知軽微バグ棚卸し（V171-TEST-03）
- **D-17:** 棚卸しの対象ソースは 4 系統: (1) **Phase 2 からの明示繰り越し 2 件**（Ollama `_fetch_ollama_models`/`_test_ollama_connection` 重複解消・`RunPodProvider.list_models()` のデッドコード分岐）、(2) **CONCERNS.md** の Known Bugs / Fragile Areas / Test Coverage Gaps から軽微バグ相当、(3) **CLAUDE.md / README の既知の制限**から軽微バグ相当（制限として意図されたものは除外）、(4) **dialogs/lang/ui_builder 面の新規コードスキャン**。
- **D-18:** 修正基準は**挙動バグ＋軽微な整理**: 挙動に影響するバグは修正し、繰り越し済みのデッドコード/重複も解消。大型構造改善（ocr_dialog.py 2,154 行の分割等）は対象外とし記録のみ。
- **D-19:** 計画時に確定した活き残りリストは**全件解消**（マイルストーン最終フェーズのため次送りしない）。量が過多の場合のみ planner がプラン分割で対応。
- **D-20:** テスト担保は**テスト可能なものは必須**: ロジックで検証可能な修正は回帰テスト必須。Tk 描画・目視確認が必要な UI 系は VERIFICATION.md の手動確認項目として記録（既存 human-verify 運用と同じ）。

### Claude's Discretion
- ショートカットダイアログのレイアウト詳細（行構成・ボタン配置・キャプチャ中の視覚フィードバック）と、キーキャプチャの実装詳細（modifier の組み立て・Esc でのキャンセル等）。
- keysym↔人間可読表記の変換関数の API 形状・置き場所。
- 未使用キー検出テストの実装方式（AST 走査 or grep ベース）と動的参照許可リストの形。
- messagebox 種別・文体の統一基準の具体内容（監査時に基準案を確定し RESEARCH.md に記録）。
- ネスト同期解消の実装形（LLMConfigDialog の適用を即 `_save_settings` するか、外側の適用経路と分離するか）。
- 新規コードスキャンの深さ・打ち切り判断（dialogs/lang/ui_builder 面を優先し、時間対効果で researcher が判断）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・ロードマップ
- `.planning/REQUIREMENTS.md` — V171-UIUX-01〜03・V171-TEST-03 の要件定義と Key Context
- `.planning/ROADMAP.md` §Phase 4 — 成功基準 4 項目（棚卸しリストは計画時に確定・記録）

### 棚卸し・監査の原典
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` §L-5/L-6 — L-5（未使用キー）の原典。解消時に ✅ + コミットハッシュを追記（Phase 2 D-12 と同じ慣行）
- `.planning/phases/02-ocr/02-RESEARCH.md` §Phase 4 への繰り越し候補 — Ollama ペア重複・RunPod `list_models` デッドコードの根拠（ファイル:行番号付き）
- `.planning/codebase/CONCERNS.md` — 既知バグ・Fragile Areas（ネストダイアログ同期の fragile 記述含む）・Test Coverage Gaps の棚卸しソース
- `CLAUDE.md` §既知の制限・注意事項 — 棚卸しソース（制限として意図されたものは除外）

### 先行決定（維持すべき制約）
- `.planning/PROJECT.md` §Key Decisions — V14-D-02（`_SENSITIVE_KEYS` 非保存ガード。LLMConfigDialog 改修時も維持）・V16-D-01/02（純ロジック層パターン）
- `.planning/phases/01-api-llm/01-CONTEXT.md` — Phase 1 の LLMConfigDialog 決定（APIキー欄の配置・セッションキー機構）。D-15 の再グルーピングはこの決定を壊さないこと
- `.planning/phases/03-v1-5-0/03-CONTEXT.md` §D-13 — ショートカット純関数抽出（`merge_shortcuts`/`shift_variant_keysym`）の経緯とテスト整備

（外部 spec/ADR ファイルはなし。要件は上記 planning ドキュメントに集約されている）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pagefolio/app.py:35 merge_shortcuts` / `:43 shift_variant_keysym` — Phase 3 で純関数抽出・テスト済み（`tests/test_v150_regression.py`）。D-06 の差分保存・D-07 の表記変換はこの隣に置くのが自然。
- `pagefolio/app.py:146-186` — default_shortcuts（8 種）・cmd_map（11 種）・バインドループ。D-05 の再実行可能メソッド化の対象。
- `pagefolio/dialogs/settings.py:147-151` — 「LLM設定を開く」ボタン（二重起動ガード付き `_open_llm_config`）。D-01 のショートカットボタンの同型パターン。
- `pagefolio/dialogs/llm_config.py` — プロバイダ別セクション切替（`_on_provider_change`）・`_apply` 適用経路。D-14/D-15 の改修対象（1,418 行）。
- `tests/test_lang_parity.py` — ja/en キー数一致の既存テスト。D-11 の未使用キー検出の追加先。
- `tests/test_provider_ui.py` — ダイアログ連携テストの前例（SimpleNamespace スタブ方式）。D-14 のセマンティクス回帰テストの参考。

### Established Patterns
- ダイアログは `parent`・font 関数・`lang` を受け取り `grab_set()` でモーダル化（dialogs/ 共通作法）。新設ショートカットダイアログも踏襲。
- LANG 新規キーは ja/en 両辞書へ同一キーで追加（`test_lang_parity.py` が監視）。ダイアログ新設・見出し改称で多数のキー追加が発生する。
- テーマ色は `C[...]`・フォントは `self._font(delta)`・破壊的操作は `Danger.TButton`。
- 設定永続化は `pagefolio_settings.json`（`_save_settings()`）。`shortcuts` キーは既存（v1.5.0 JSON ミニマム実装）。
- Tk 非依存ロジックの純関数化＋直接テスト（`pagination.py` / `md_render.py` 方式）— D-07 変換関数・D-11 検査の同型。

### Integration Points
- `pagefolio/dialogs/settings.py` — D-01 ボタン追加・D-16 セクション再構成の本体。ダイアログ新設時は `dialogs/__init__.py` の re-export へ追加。
- `pagefolio/dialogs/llm_config.py:1121 _apply` — D-14 のトランザクション境界。`app._session_api_keys` 直接格納（Phase 1 D-04）は既に「即確定」であり、llm_settings 側の確定タイミングとの整合を確認。
- `pagefolio/lang.py`（1,195 行・約 500 キー）— D-09/D-10 の削除対象・D-12(a) のキー化追加先。
- `pagefolio/dialogs/llm_config.py:1164-1209` — Ollama `_fetch_ollama_models`/`_test_ollama_connection`（棚卸し確定項目 1・Phase 2 の `_probe_lm_provider` 共通化を転用可能）。
- `pagefolio/ocr_providers.py:1397-1424` — `RunPodProvider.list_models()` の無意味分岐（棚卸し確定項目 2）。
- CLAUDE.md §ファイル構成 — ダイアログ新設時（例: `dialogs/shortcuts.py`）は構成表へ 1 行追記。

</code_context>

<specifics>
## Specific Ideas

- ショートカット編集は「行の変更ボタン → そのままキーを押す → 取れる」体験にする（keysym の知識を要求しない）。
- 「押しても効かないキー」を作らない: 重複は保存させない・無効化は明示的な「割当なし」でのみ起こる。
- LLM設定の「適用」はその場で信じられる（外側ダイアログの操作で巻き戻らない）挙動へ統一する。
- マイルストーン最終フェーズなので棚卸しの活き残りは全件倒し、次マイルストーンへ実質的な塩漬けを残さない。

</specifics>

<deferred>
## Deferred Ideas

- ocr_dialog.py（2,154 行）・ocr_providers.py（1,424 行）の大型構造分割（CONCERNS.md Tech Debt）— D-18 で対象外と確定。将来の保守性マイルストーン候補
- ショートカットのプロファイル切替・エクスポート/インポート — 需要があれば将来フェーズ
- MAX_UNDO の設定項目化・thumb_cache の LRU 化など CONCERNS.md の Performance/Scaling 項目 — 軽微バグではないため棚卸し対象外（記録のみ）

</deferred>

---

*Phase: 4-UI/UX 磨き込み + 既知バグ棚卸し*
*Context gathered: 2026-07-05*
