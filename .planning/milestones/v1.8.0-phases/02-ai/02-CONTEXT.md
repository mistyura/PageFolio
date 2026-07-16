# Phase 2: AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック） - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

ユーザーが OCR/サマリ用プロンプトを名前付きテンプレートとして管理する UI（LLM 設定ダイアログ内）と、プロバイダー障害時に安全な手動フォールバックで処理を継続する仕組みを追加する。

対象要件: V180-TMPL-01〜05（テンプレート管理）・V180-FALL-01〜03（プロバイダーフォールバック）。

**スコープ外:** `ocr_dialog.py` の分割・OCRRunEngine 抽出（Phase 3）・バッチ複数ファイル OCR（Phase 4）・自動ベンダー切替やコスト最適化ルーティング（PROJECT.md で確定除外）。

</domain>

<decisions>
## Implementation Decisions

### テンプレート保存モデル
- **D-01:** テンプレートは「ペア保存」方式。1テンプレート = カスタムプロンプト + サマリプロンプトの組。UI はテンプレート選択欄1つで両方が同時に切り替わる（別々の独立した一覧は不採用）。
- **D-02:** 永続化形式は `pagefolio_settings.json` 内の辞書構造（既存の `_load_settings`/`_save_settings` パターンをそのまま延長）。専用ディレクトリの個別 md ファイル方式は不採用（PITFALLS.md 落とし穴で「v1.8.0 スコープ内はベタ書き許容」とされている想定どおり）。
- **D-03:** 使用中（アクティブ）テンプレートの削除は禁止する。削除ボタンを無効化するか、削除前に他テンプレートへの切替を促す（誤操作でカスタムプロンプトが消える事故を防止）。
- **D-04:** テンプレート名の重複は保存時に拒否する。`ShortcutsDialog` の重複拒否パターン（保存時に同名があればエラー表示）を踏襲する。

### 外部mdファイル連動との共存
- **D-05:** テンプレート切替時、外部 md ファイル（`ocr_custom_prompt.md`/`ocr_summary_prompt.md`）に未保存の変更がある場合は確認ダイアログ（`messagebox.askyesno`）を挟む。キャンセルで切替を中止する（PITFALLS.md 落とし穴6の推奨策）。
- **D-06:** ファイル連動モード（外部ファイルが存在する状態）で新規テンプレートを「保存」する際は、現在の入力欄の内容（開いた時点で外部ファイル内容が反映済み）をそのままテンプレートへコピーする。
- **D-07:** テンプレート切替後は、選択したテンプレートの内容で外部 md ファイルを上書きする（既存の「適用時に入力欄→ファイルへ書き戻し」挙動を踏襲）。外部ファイルは常に「現在アクティブなテンプレートのライブ編集内容」という位置づけを維持し、複数テンプレートの概念を外部ファイル側には持ち込まない。
- **D-08:** 外部ファイル内容と現在のテンプレート内容の不一致（外部エディタでの編集済み）を検知する専用UIは新設しない。既存の `_add_prompt_file_notice`（「ファイル連動中」注記）をそのまま流用し、D-05 の切替時確認ダイアログのみで十分とする。

### フォールバック実行時の挙動
- **D-09:** フォールバック候補へ切替えた後、OCR は未処理ページのみ再開する。既存の resume/`_pending_pages()` 仕組みをそのまま流用し、成功済みページは保持したまま失敗/未処理ページのみ新プロバイダで再実行する。
- **D-10:** フォールバック連鎖は1回限りに制限しない。設定されたチェーンを最後まで順に辿り、各段で送信先確認ダイアログを毎回再提示する（自動連鎖送信はしない方針との整合・CR-01 パターン踏襲）。
- **D-11:** フォールバックの発火条件は `PipelineState.fatal_msg` が確定する全ケース（サーキットブレーカー発動・connection/timeout・APIキー未設定）とする。APIキー未設定を理由とするフォールバック提案時は、確認ダイアログにその理由を明示する（PITFALLS.md 落とし穴8で言及される「静かな握りつぶし」を防ぐ）。
- **D-12:** 全ページ統合サマリ生成時の失敗にも同じフォールバック順を適用する。既存の `_confirm_summary_cost` 等サマリ専用確認経路を流用し、OCR と同様の挙動にする。

### フォールバック順設定UI
- **D-13:** フォールバック順の並び替えUIは「リスト + 上へ/下へボタン」方式。`MergeOrderDialog`（`pagefolio/dialogs/merge.py`）の `tk.Listbox` + 上へ/下へボタンパターンをそのまま流用する（ドラッグ&ドロップは不採用・実装コスト回避）。
- **D-14:** フォールバック候補には全プロバイダを一覧に含める（APIキー未設定のプロバイダも表示）。未設定のまま実行された場合は D-11 の発火条件どおり「APIキー未設定」を明示エラーとして扱い、次のフォールバック候補へ進む。
- **D-15:** フォールバック設定UIは LLM 設定ダイアログ内に新規独立セクション（例:「🔁 フォールバック」）として配置する。既存の「OCRプロバイダ選択」セクションへの埋め込みは行わない（sections.py の既存責務別 Mixin 構造をそのまま拡張）。
- **D-16:** フォールバック設定の初期表示は「有効化トグル + 順序リスト」。既定は「フォールバックなし（空リスト・トグルOFF）」で確定済み（V180-FALL-01）。トグルをONにすると順序リストが現れる構成とし、未設定ユーザーにもフォールバック機能の存在が分かりやすい形にする。

### Claude's Discretion
- テンプレートデータの settings.json 内スキーマ詳細（キー名・テンプレート辞書の具体的な構造）
- フォールバック順設定の内部データ構造（settings.json への保存キー名・リスト形式）
- 新規独立セクション（D-15）を sections.py 内のどのメソッド分割単位に配置するか
- 送信先確認ダイアログ再提示（D-10）の具体的なメッセージ文言（フォールバック理由の表示方法）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・フェーズ定義
- `.planning/REQUIREMENTS.md` — V180-TMPL-01〜05・V180-FALL-01〜03 の要件文言（本フェーズの対象8要件）
- `.planning/ROADMAP.md` — Phase 2 の Goal・Success Criteria（成功基準5項目）・依存関係（Phase 1 完了前提）

### リサーチ成果物
- `.planning/research/SUMMARY.md` — テンプレート/フォールバックの推奨アプローチ（settings.py 拡張・PipelineState.fatal_msg 確定後のオーケストレーション層としてのフォールバック設計）
- `.planning/research/PITFALLS.md` — 落とし穴6（外部mdファイル書き戻し競合）・落とし穴7（同意方針迂回）・落とし穴8（設定引き継ぎミス）— 本フェーズの中心的リスク3点

### 前フェーズの決定事項
- `.planning/phases/01-foundation-split/01-CONTEXT.md` — D-06「Phase 2向けの投機的な仕込みはしない（純粋分割のみ）」・Mixin 責務別3層構造（`dialog.py`/`sections.py`/`model_fetch.py`）が本フェーズの拡張ポイントであることの確認

### 前例パターン（コード内）
- `pagefolio/dialogs/shortcuts.py` — ShortcutsDialog の保存時重複拒否パターン（D-04 の踏襲元）
- `pagefolio/dialogs/merge.py` — MergeOrderDialog の `tk.Listbox` + 上へ/下へボタンによる並び替えUI（D-13 の踏襲元）
- `pagefolio/dialogs/llm_config/dialog.py` — `_add_prompt_file_notice`（外部ファイル連動注記・D-08 で流用）・`_apply`（適用時の書き戻し処理）
- `pagefolio/dialogs/llm_config/sections.py` — カスタム/サマリプロンプト入力欄の現行UI構造（テンプレート選択UIの挿入位置）
- `pagefolio/ocr_dialog.py` — `_confirm_cost`/`_confirm_summary_cost`/`_check_cloud_api_key`（送信先確認・APIキー確認の既存フロー。フォールバック確認ダイアログ再提示の踏襲元）
- `pagefolio/ocr_pipeline.py` — `PipelineState.fatal_msg`/`fatal_kind`（フォールバック発火条件の判定源）
- `pagefolio/ocr.py` — `resolve_ocr_prompt`/`resolve_summary_prompt`（custom > provider別 > 汎用の解決順。テンプレート層挿入対象）
- `pagefolio/settings.py` — `load_prompt_file`/`save_prompt_file`/`load_custom_prompt`/`load_summary_prompt`（外部ファイル連動の既存実装）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MergeOrderDialog`（`pagefolio/dialogs/merge.py`）: リスト+上へ/下へボタンの並び替えUI完成形。フォールバック順設定UIにそのまま流用できる
- `ShortcutsDialog`（`pagefolio/dialogs/shortcuts.py`）: 保存時の重複拒否パターン。テンプレート名重複チェックに流用できる
- `pagefolio/dialogs/llm_config/` の責務別3層 Mixin 構造（`dialog.py`/`sections.py`/`model_fetch.py`）: テンプレート管理・フォールバック設定の新規セクションはこの構造にそのまま追加できる（Phase 1 の D-06 により投機的な仕込みはされていないが、構造自体が拡張ポイント）

### Established Patterns
- 外部ファイル連動の双方向バインディング（`settings.py` の `load_prompt_file`/`save_prompt_file`/`prompt_file_exists`）: テンプレート切替時もこのパターンの上に「アクティブテンプレート」という概念を薄く重ねる（D-05〜D-08）
- 送信先確認ダイアログの毎回表示・プロバイダ別分岐（`ocr_dialog.py` の `_confirm_cost`/`_confirm_summary_cost`、v1.7.1 CR-01 のプロバイダ分岐パターン）: フォールバック確認ダイアログもこのパターンを踏襲（D-10）
- `resolve_ocr_prompt`/`resolve_summary_prompt` の優先順位純関数（custom > provider別 > 汎用）: テンプレート層はこの解決順の中に新しい優先度として挿入される（V180-TMPL-05）

### Integration Points
- `pagefolio_settings.json` へのテンプレート辞書・フォールバック順リストの追加（`_load_settings`/`_save_settings` のデフォルト値拡張）
- `PipelineState.fatal_msg`/`fatal_kind` 確定後、OCRDialog の完了処理（`ocr_dialog.py` の producer-consumer 終了処理付近）にフォールバック提案フックを追加
- `build_provider` ファクトリをフォールバック候補ごとに独立して呼び出し、`max_concurrency`・APIキー解決・`clamp_retry_after` をプロバイダ単位で再評価する（PITFALLS.md 落とし穴8対応）

</code_context>

<specifics>
## Specific Ideas

- テンプレートは「ペア保存」（カスタム+サマリの組・D-01）で、UI操作は既存の MergeOrderDialog・ShortcutsDialog の完成済みパターンをそのまま流用する方針で一貫している（新規UIパターンの発明を避ける）
- フォールバックは「明示設定型・自動送信なし」の確定方針（PROJECT.md）を最優先し、連鎖の各段で必ず送信先確認ダイアログを再提示する（D-10）

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope（4領域とも計画どおり完了。スコープ外提案は出なかった）

</deferred>

---

*Phase: 2-AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック）*
*Context gathered: 2026-07-14*
