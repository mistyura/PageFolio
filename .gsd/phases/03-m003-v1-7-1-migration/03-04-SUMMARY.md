---
id: S04
parent: M003
milestone: M003
provides:
  - build_keysym_from_event / find_duplicate_binding / keysym_to_display の3純関数（app.py）
  - 再実行可能な _bind_shortcuts() メソッドと self._default_shortcuts / self._cmd_map / self._bound_keysyms インスタンス属性
  - 純関数3種の回帰テスト（test_v150_regression.py）
  - ShortcutsDialog（pagefolio/dialogs/shortcuts.py）— cmd_map 全11コマンドの実キーキャプチャ編集・保存時重複拒否・無効化・全体リセット
  - SettingsDialog の外観/操作/AI・OCR 3セクション再編と app 参照配線（_open_shortcuts_dialog）
  - settings_lm_studio_section 等 🔍→⚙ アイコン改称（C8）
  - LLMConfigDialog の共通/固有グルーピング見出し（llm_config_common_section/llm_config_provider_section）
  - app._apply_llm_settings_live（_rebuild_ui を伴わない軽量 app.settings 即時反映）
  - SettingsDialog(on_llm_apply=...) 経由のネスト適用独立トランザクション化（D-14・C4/C5 解消）
  - LLMConfigDialog._probe_ollama_provider（Ollama モデル取得/接続テストの共通ヘルパー・C2 解消）
  - viewer.py の _show_page_popup が LANG キー経由（popup_page_title/popup_zoom_out/popup_zoom_in/popup_close）で表示される（C6解消）
  - page_ops.py の _split_by_range が showerror+err_title で範囲未入力・範囲形式不正の両分岐を対称に扱う（C7解消）
  - lang.py の確定未使用キー（RESEARCH 9件 + D-11テスト自身が新規発見した2件=計11件）削除・ja/en キー集合一致
  - test_lang_parity.py の test_no_unused_lang_keys（D-11・常設回帰）
requires: []
affects: []
key_files: []
key_decisions:
  - build_keysym_from_event の修飾子連結順は Control, Alt, Shift の順に固定（RESEARCH.md Pattern 1 準拠）
  - _bind_shortcuts() は self._bound_keysyms を使い、再呼び出し時に前回バインドした keysym(shift variant含む)を全て unbind してから再バインドする
  - ShortcutsDialog は保存前は self._shortcuts という一時コピーのみを編集し、保存ボタンを押すまで app.settings / 実バインドへ反映しない（キャンセルで無効化）
  - 保存時は (a) 全体重複再検査 → (b) 既定と異なる項目のみを settings['shortcuts'] へ完全置換 → (c) app._bind_shortcuts() → (d) _save_settings の順で1本道にする
  - SettingsDialog.__init__ に後方互換の app=None を追加し、_open_settings（app.py）から app=self を渡す（既存の位置引数の並びは変更なし）
  - 共通/固有見出しは _on_provider_change 内で each 分岐（claude/gemini/tesseract/else）ごとに before=self.scale_row で再配置する設計にした。既存の specific-frame と effort/temperature frame の挿入ロジック（before=self.scale_row）自体は一切変更していない
  - app._apply_llm_settings_live は self.settings.update(llm_settings) + _save_settings のみを行い、_rebuild_ui() は呼ばない（nested on_apply から呼ぶと開いている SettingsDialog Toplevel まで destroy されるため）
  - SettingsDialog.__init__ の on_llm_apply は末尾の後方互換任意引数とし、_open_llm_config 内の nested on_apply では getattr(self, '_on_llm_apply', None) で防御的に参照する（既存の _on_llm_apply 未設定スタブとの互換維持）
  - _probe_ollama_provider は _probe_lm_provider と同型の update_combo パラメータ化ヘルパーとし、既存のステータス文言（settings_lm_testing/settings_lm_test_ok/settings_lm_test_fail）をそのまま使い回した（lang.py は本プランで変更しない・04-04 へ委譲）
  - D-11 の未使用キー検出テストは grep 相当の引用符付き完全一致方式を採用（AST走査ではなく）。動的キー合成はコードベース全体でゼロ件（RESEARCH Pitfall 3 確認済み）のため十分
  - テスト実装中に D-11 検査自体が新規発見した ocr_progress/ocr_progress_render（Phase 2 の統合プログレス化 D-03 で不要化していた活き残り）も RESEARCH の確定9件と同時に削除した（Rule 1 auto-fix・全件解消 D-19 の趣旨に整合）
  - tesseract_not_installed（削除）と tesseract_not_installed_hint（使用中・維持）はキー名プレフィックス衝突の代表例のため、削除操作は完全一致の該当行のみに限定した
patterns_established:
  - 純関数3種の docstring は日本語で D-02/D-04/D-07 のどの決定に対応するかを1行で明記し、raw keysym 文字列を末尾に羅列しない
observability_surfaces: []
drill_down_paths: []
duration: 9min
verification_result: passed
completed_at: 2026-07-05
blocker_discovered: false
---
# S04: Ui Ux

**# Phase 4 Plan 1: ショートカット GUI 編集基盤 Summary**

## What Happened

# Phase 4 Plan 1: ショートカット GUI 編集基盤 Summary

**`app.py` にkeysym組み立て/重複検出/表示変換の3純関数を追加し、`__init__` 直書きバインドを再実行可能な `_bind_shortcuts()` メソッドへ抽出**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-05T09:41:14Z
- **Completed:** 2026-07-05T09:44:31Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `build_keysym_from_event` / `find_duplicate_binding` / `keysym_to_display` の3純関数を `app.py` の既存 `merge_shortcuts`/`shift_variant_keysym` の隣に追加（Tk 非依存・単体呼び出し可能）
- `PDFEditorApp.__init__` の直書きバインドロジック（default_shortcuts辞書・cmd_map辞書・バインドループ）を `_bind_shortcuts()` メソッドへ抽出し、`self._default_shortcuts` / `self._cmd_map` をインスタンス属性化
- `_bind_shortcuts()` は再呼び出し時に `self._bound_keysyms`（前回バインドした keysym・shift variant 含む）を先に unbind してから新設定で再バインドする設計にし、後続 04-02 の ShortcutsDialog 保存経路から再利用可能にした
- 純関数3種の回帰テストを `test_v150_regression.py` に追加（`TestBuildKeysymFromEvent`/`TestFindDuplicateBinding`/`TestKeysymToDisplay`）

## Task Commits

Each task was committed atomically:

1. **Task 1: keysym 組み立て・重複検出・表示変換の純関数を app.py に追加** - `af0968f` (feat)
2. **Task 2: __init__ 直書きバインドを _bind_shortcuts() へ抽出し再実行可能化** - `68f6afe` (refactor)
3. **Task 3: 純関数の回帰テストを test_v150_regression.py へ追加** - `9cdca79` (test)

_Note: Task 1 は tdd="true" 指定だったが、既存の隣接パターン（純関数を先に実装し verify で固定・test は Task 3 で追加）を踏襲した。plan の verify（python ワンライナー assert）で Task 1 完了時点の正当性を確認済み。_

## Files Created/Modified
- `pagefolio/app.py` - 純関数3種（build_keysym_from_event/find_duplicate_binding/keysym_to_display）追加・`_bind_shortcuts()` メソッド新設・`__init__` のバインドロジックをインスタンス属性化＋メソッド呼び出しへ置換
- `tests/test_v150_regression.py` - `TestBuildKeysymFromEvent`/`TestFindDuplicateBinding`/`TestKeysymToDisplay` の3クラスを追加（計12テスト）

## Decisions Made
- 修飾子の連結順序を Control → Alt → Shift に固定（RESEARCH.md Pattern 1・Tk bind 構文の慣例順に準拠）
- Alt ビットマスクの既定値は `0x20000`（RESEARCH.md A1: Windows Tk での一般値。実機未検証だがキーワード引数で上書き可能にして将来のプラットフォーム差異に対応できるようにした）
- 純関数の docstring は各々 D-02/D-04/D-07 のどの決定に対応するかを1行で明記し、grep誤検知回避のため raw keysym 文字列を末尾に羅列しない方針を踏襲
- **V171-UIUX-01 は本プラン（基盤）と 04-02（ShortcutsDialog 実装）にまたがる要件のため、REQUIREMENTS.md のチェックボックス/トレーサビリティ表は本プランでは `Pending` のまま維持した（ユーザー向け GUI 編集機能自体は 04-02 完了まで未提供のため）。本 SUMMARY の `requirements-completed` はプラン frontmatter の宣言をそのまま転記している

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - `ruff format` が Task 3 のテストコード改行を自動整形した以外は計画通り。整形後も30テスト全てグリーンであることを再確認済み。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `self._default_shortcuts`（8キー）/ `self._cmd_map`（11キー: rotate_right/rotate_left/rotate_180含む）/ `_bind_shortcuts()` が揃い、04-02 の ShortcutsDialog は「保存 → `app._bind_shortcuts()` 呼び出し」で即時反映を実装できる
- keysym↔表示変換・重複検出の純関数が確定済みのため、04-02 は UI 配線（実キーキャプチャ・保存時重複チェック呼び出し・一覧表示）に専念できる
- ブロッカーなし。フルスイート845件グリーン・ruffクリーン確認済み

---
*Phase: 04-ui-ux*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files exist on disk and all task commit hashes (af0968f, 68f6afe, 9cdca79) are present in git log.

# Phase 4 Plan 2: ショートカット GUI 編集完成 + SettingsDialog セクション再編 Summary

**新設 ShortcutsDialog で cmd_map 全11コマンドを実キーキャプチャ編集・保存時重複拒否可能にし、SettingsDialog を外観/操作/AI・OCR の3セクションへ再編・🔍→⚙アイコン改称**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-05T09:47:00Z
- **Completed:** 2026-07-05T09:59:00Z
- **Tasks:** 3
- **Files modified:** 6 (新規1・修正5)

## Accomplishments
- `pagefolio/dialogs/shortcuts.py` を新設し `ShortcutsDialog(tk.Toplevel)` を実装。cmd_map の全11コマンド（open_file/save_file/undo/redo/save_as/delete/toggle_mode/print_pdf/rotate_right/rotate_left/rotate_180）を一覧表示し、「変更」で実キーキャプチャ（修飾キー単体は確定せず継続待機・Escでキャンセル）、「解除」で無効化、「既定に戻す」で全体リセットできる
- 保存時は全体重複を `find_duplicate_binding` で再検査 → 拒否時は衝突コマンド名を含むエラー表示 → 問題なければ既定と異なる項目のみ `app.settings["shortcuts"]` へ差分格納 → `app._bind_shortcuts()` で即時反映 → `_save_settings` で永続化、の一本道を実装
- `SettingsDialog` を「外観（テーマ/フォント）」「操作（ショートカット）」「AI・OCR」の3セクション構成へ再編し、「操作」セクションに「⌨ ショートカット設定…」ボタン（`_open_shortcuts_dialog`・二重起動ガード付き）を追加
- `SettingsDialog.__init__` に後方互換の `app=None` 引数を追加し、`app.py._open_settings` から `app=self` を渡すことで ShortcutsDialog が `_cmd_map`/`_default_shortcuts`/`_bind_shortcuts` を参照できるようにした
- `settings_lm_studio_section`（旧「🔍 LM Studio (OCR)」→「⚙ AI・OCR 設定」）・`settings_open_llm_config`・`llm_config_heading` の🔍アイコンを⚙系へ改称（C8。既存 `settings_heading`="⚙ 設定" とのアイコン統一）
- ShortcutsDialog 用の全文言（タイトル・11コマンド表示名・列見出し・各操作ボタン・重複エラー・未割当プレースホルダ）と `settings_section_appearance`/`settings_section_operation`/`settings_open_shortcuts` を ja/en 両辞書へ同時追加
- `dialogs/__init__.py` へ `ShortcutsDialog` を re-export・CLAUDE.md のファイル構成表へ `dialogs/shortcuts.py` の1行を追加

## Task Commits

Each task was committed atomically:

1. **Task 1: ShortcutsDialog（実キーキャプチャ編集ダイアログ）を新設** - `9adcf3f` (feat)
2. **Task 2: SettingsDialog を3セクション再編しショートカットボタンを追加** - `2c0eff9` (feat)
3. **Task 3: lang.py に ShortcutsDialog 文言と改称見出しキーを ja/en 同時追加** - `2d74797` (docs)

## Files Created/Modified
- `pagefolio/dialogs/shortcuts.py` - 新規。`ShortcutsDialog(tk.Toplevel)`。実キーキャプチャ・重複検出・無効化・全体リセット・差分保存・即時再バインド
- `pagefolio/dialogs/settings.py` - `_build` を3セクション再編・`_open_shortcuts_dialog` 新設・`__init__` に `app` 引数追加
- `pagefolio/dialogs/__init__.py` - `ShortcutsDialog` の re-export 追加
- `pagefolio/lang.py` - ShortcutsDialog 文言・セクション見出しキー・🔍→⚙ 改称キーを ja/en 同時追加
- `pagefolio/app.py` - `_open_settings` の `SettingsDialog(...)` 呼び出しへ `app=self` を追加（Rule 2 deviation。下記参照）
- `CLAUDE.md` - ファイル構成表へ `dialogs/shortcuts.py` の1行を追加

## Decisions Made
- ShortcutsDialog は保存前状態を `self._shortcuts`（working copy）に閉じ込め、キャンセル時は app へ一切影響しないようにした（安全なプレビュー編集）
- 差分保存は「現在の全11コマンド状態」から「既定と異なるもののみ」を都度再計算して `settings["shortcuts"]` を完全置換する方式にした（マージではなく置換）。これにより全体リセット後の保存で不要な旧差分が settings に残留しない
- 個別「解除」は既定キーがあるコマンドでは `""` を明示的に差分として保存する（無効化を表現するために必要。マージ時 `if func and keysym` の keysym="" 判定で自然にバインドされない）
- SettingsDialog への `app` 引数は既存の位置引数順序を変えずキーワード専用の新規任意引数として追加し、既存呼び出し元（テストの SimpleNamespace スタブ含む）との後方互換を維持した

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] `app.py._open_settings` に `app=self` を追加**
- **Found during:** Task 2（SettingsDialog セクション再編）
- **Issue:** plan の frontmatter `files_modified` には `pagefolio/app.py` が含まれておらず、Task 2 の action 文言も「SettingsDialog.__init__ に任意引数を追加してよい」という記述に留まっていたが、実際に `SettingsDialog` を構築している唯一の本番呼び出し元（`app.py:560` `_open_settings`）を更新しない限り、`SettingsDialog._app` は常に `None` のままとなり、「⌨ ショートカット設定…」ボタンから ShortcutsDialog を開く機能が本番コードで一切動作しない（V171-UIUX-01 の成功基準そのものが達成できない）
- **Fix:** `app.py._open_settings` 内の `SettingsDialog(...)` 呼び出しへ `app=self` を追加（既存の位置引数は変更なし）
- **Files modified:** `pagefolio/app.py`
- **Verification:** `ruff check`/`ruff format --check` クリーン・`pytest tests/test_provider_ui.py -x -q`（`TestOpenSettingsDoubleLaunchGuard` 含む既存回帰）グリーン・`pytest` フルスイート845件グリーン
- **Committed in:** `2c0eff9`（Task 2 commit）

---

**Total deviations:** 1 auto-fixed（Rule 2 — missing critical functionality）
**Impact on plan:** ShortcutsDialog を本番導線から実際に開けるようにするために必須の配線。スコープ拡大ではなく、plan が意図した機能（V171-UIUX-01 成功基準1）を成立させるための不可欠な補完。

## Issues Encountered
None - ruff format の自動整形（Task 1 の `shortcuts.py` 内 1 行が Task 3 のフォーマットチェックで整形対象と判明・整形後も全テストグリーン再確認済み）以外は計画通り。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-UIUX-01（ショートカット GUI 編集）・V171-UIUX-03（SettingsDialog セクション再編・C8）は本プランで完成
- 実キー入力→保存→即時反映の目視確認は VERIFICATION.md の Manual-Only 項目として記録が必要（04-RESEARCH.md D-20・既存 human-verify 運用と同じ）
- 04-RESEARCH.md の棚卸し確定表（C2/C4/C5/C6/C7・V171-UIUX-02/V171-TEST-03 相当）は本プランの対象外（別プランの担当範囲）のため次プランへ継続
- ブロッカーなし。フルスイート845件グリーン・ruffクリーン確認済み

---
*Phase: 04-ui-ux*
*Completed: 2026-07-05*

## Self-Check: PASSED

# Phase 4 Plan 3: LLMConfigDialog 整理 + Ollama 重複解消 Summary

**LLMConfigDialog に共通/固有見出しを追加しネスト適用を独立トランザクション化（D-14）、Ollamaモデル取得/接続テストをLM Studio型の共通ヘルパーへ統合（C2）**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-05T09:59:00Z
- **Completed:** 2026-07-05T10:15:46Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `LLMConfigDialog._build` に「選択中プロバイダ固有の設定」「全プロバイダ共通の設定」の2見出しラベルを追加し、`_on_provider_change` の各分岐（lmstudio/ollama/runpod/claude/gemini/tesseract/off）で `before=self.scale_row` を使って正しい位置（固有設定の直後・共通パラメータ群の先頭）へ再配置する設計にした。既存の `before=self.scale_row` 挿入ロジック自体は変更していない
- `app.py` に `_apply_llm_settings_live(llm_settings)` を新設し、`self.settings.update()` + `_save_settings()` のみを行う軽量反映（`_rebuild_ui()` は呼ばない）を実装
- `SettingsDialog.__init__` に後方互換の `on_llm_apply=None` 引数を追加し、`_open_llm_config` のネスト `on_apply` から `getattr(self, "_on_llm_apply", None)` 経由で呼び出すことで、外側 SettingsDialog の Apply/Cancel と独立して app.settings（メモリ）へ即時反映するようにした（C4/C5 解消）
- `app._open_settings` の `SettingsDialog(...)` 呼び出しに `on_llm_apply=self._apply_llm_settings_live` を配線
- `LLMConfigDialog._probe_ollama_provider(update_combo)` を新設し、`_fetch_ollama_models`/`_test_ollama_connection` を 1 行ラッパーへ置換。旧重複本体（LM Studio 用 `_probe_lm_provider` とほぼ完全重複していた実装）を除去（C2 解消）
- 新規テストクラス4種を `tests/test_provider_ui.py` へ追加: `TestApplyLlmSettingsLive`（軽量反映の単体検証）・`TestSettingsDialogNestedApplyCascade`（外側キャンセルでも反映が失われないことの回帰）・`TestProbeOllamaProvider`（Combobox反映有無・URL空欄・接続エラー・薄いラッパー化の検証）

## Task Commits

Each task was committed atomically:

1. **Task 1: LLMConfigDialog に共通/固有グルーピング見出しを追加（D-15）** - `d70dc19` (feat)
2. **Task 2: ネスト適用を独立トランザクション化（D-14・C4/C5）+ cascade 回帰テスト** - `bdcc97a` (feat)
3. **Task 3: Ollama モデル取得/接続テストを共通ヘルパーへ統合（C2）** - `f979d37` (refactor)

## Files Created/Modified
- `pagefolio/dialogs/llm_config.py` - 共通/固有見出しラベル2種を追加し `_on_provider_change` の各分岐へ配置ロジック追加・`_probe_ollama_provider` 新設で Ollama 重複解消
- `pagefolio/dialogs/settings.py` - `SettingsDialog.__init__` に `on_llm_apply=None` 後方互換引数を追加・`_open_llm_config` のネスト `on_apply` から呼び出す配線を追加
- `pagefolio/app.py` - `_apply_llm_settings_live` メソッド新設・`_open_settings` の `SettingsDialog(...)` 呼び出しに `on_llm_apply=self._apply_llm_settings_live` を追加
- `pagefolio/lang.py` - `llm_config_provider_section`/`llm_config_common_section` を ja/en 両辞書へ同時追加
- `tests/test_provider_ui.py` - `TestApplyLlmSettingsLive`/`TestSettingsDialogNestedApplyCascade`/`TestProbeOllamaProvider` の3クラス追加・既存 `TestOpenSettingsDoubleLaunchGuard` の2スタブへ `_apply_llm_settings_live` 属性を追加（新規必須引数への追従）

## Decisions Made
- 共通/固有見出しの配置は、既存の「specific-frame と effort/temperature frame がともに `before=self.scale_row` で挿入される」という構造上の制約から、`_common_section_heading` も `_on_provider_change` の各分岐内で `before=self.scale_row` により都度再配置する設計にした。これにより visual 順序（固有見出し → 固有フレーム → 共通見出し → 共通パラメータフレーム → scale_row）を、既存の specific-frame 挿入ロジックを一切変更せずに実現した
- `_apply_llm_settings_live` は `_rebuild_ui()` を意図的に呼ばない。nested on_apply の実行コンテキストは「SettingsDialog（Toplevel）がまだ開いている最中」であり、`_rebuild_ui()` は `self.root.winfo_children()` を全 destroy するため、そのまま呼ぶと開いている SettingsDialog 自身が破棄されてしまう
- `on_llm_apply` の参照は `getattr(self, "_on_llm_apply", None)` の防御的パターンにした。これは既存の `TestSettingsDialogOpenLlmConfigPersists`（`_on_llm_apply` 属性を持たない SimpleNamespace スタブ）との後方互換を壊さないための選択で、Phase 1-2 で確立済みの `getattr(self, "_plugin_manager", None)` 等と同じ慣習に従う

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 既存 `TestOpenSettingsDoubleLaunchGuard` の2スタブに `_apply_llm_settings_live` 属性を追加**
- **Found during:** Task 2（ネスト適用の独立トランザクション化）
- **Issue:** `app._open_settings` が新たに `on_llm_apply=self._apply_llm_settings_live` を参照するようになったため、この属性を持たない既存の `SimpleNamespace` スタブ（`test_second_call_reuses_existing_dialog`/`test_new_dialog_created_after_previous_closed`）が `AttributeError` で落ちるようになった
- **Fix:** 両テストのスタブへ `_apply_llm_settings_live=lambda s: None` を追加
- **Files modified:** `tests/test_provider_ui.py`
- **Verification:** `pytest tests/test_provider_ui.py -x -q` 全件グリーン
- **Committed in:** `bdcc97a`（Task 2 commit）

---

**Total deviations:** 1 auto-fixed（Rule 3 — blocking issue）
**Impact on plan:** 既存テストスタブの後方互換維持に必要な最小限の追従。スコープ拡大なし。

## Issues Encountered

None - `_probe_ollama_provider` のテストスタブに `_L`（LANG 辞書）属性が漏れていた点のみ実装中に気づき、即座に追加して解決（Task 3 完了前・コミット前に修正済み）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- V171-UIUX-03（SettingsDialog/LLMConfigDialog 整理）・V171-TEST-03（棚卸しの一部・Ollama 重複解消）は本プランで完了
- 04-RESEARCH.md の棚卸し確定表のうち、本プランで解消したのは C2（Ollama 重複）と C4/C5（ネスト同期）のみ。残る C6（viewer.py ハードコード文言）・C7（page_ops.py messagebox 種別不一致）・C8（見出しアイコン改称・D-16 は 04-02 で既に着手済みだが lang.py 未使用9キー削除は未着手）は次プラン（04-04）の担当範囲として継続
- LLMConfigDialog の共通/固有見出し表示・ネスト適用の実挙動目視は VERIFICATION.md の Manual-Only 項目として記録が必要
- ブロッカーなし。フルスイート857件グリーン・ruffクリーン確認済み

---
*Phase: 04-ui-ux*
*Completed: 2026-07-05*

## Self-Check: PASSED

# Phase 4 Plan 4: 文言/エラー一貫性監査の最終解消 Summary

**viewer.py 拡大ポップアップの LANG キー化（C6）・page_ops.py 分割エラーの messagebox 種別統一（C7）・lang.py 確定未使用11キー削除 + D-11 未使用キー検出回帰テスト常設**

## Performance

- **Duration:** 9 min
- **Started:** 2026-07-05T10:20:00Z
- **Completed:** 2026-07-05T10:29:42Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `pagefolio/viewer.py` の `_show_page_popup`（ポップアップタイトル・縮小/拡大/閉じるボタンの4箇所）を `self._t()` 経由の LANG キー参照へ置き換え、`lang="en"` でも日本語が出ない状態にした（C6 解消）。新規キー `popup_page_title`/`popup_zoom_out`/`popup_zoom_in`/`popup_close` を ja/en 両辞書へ同時追加
- `pagefolio/page_ops.py` の `_split_by_range` で範囲未入力エラーを `messagebox.showinfo`+`info_title` から `messagebox.showerror`+`err_title` へ変更し、直後の範囲形式不正エラーと種別/タイトルを対称化（C7 解消）。回帰テスト `test_split_by_range_no_input_shows_error` を `tests/test_pdf_ops.py` へ追加
- `pagefolio/lang.py` から確定未使用キーを削除: RESEARCH.md 監査表の9件（`ocr_provider_off_hint`/`tesseract_not_installed`/`llm_fetching_ollama_models`/`ocr_fetch_models`/`ocr_models_fetched`/`ocr_models_fetch_fail`/`ocr_models_fetching`/`sec_compress`/`warn_title`）に加え、新設した D-11 テスト自身が発見した `ocr_progress`/`ocr_progress_render`（Phase 2 の統合プログレス化で不要化していた活き残り）の計11件。使用中の `tesseract_not_installed_hint` は完全一致方式により誤削除を回避
- `tests/test_lang_parity.py` へ `test_no_unused_lang_keys`（D-11）を新設。`pagefolio/`（`lang.py` 除く）・`tests/`・`plugins/` 全 `.py` を走査し、各 LANG キーが引用符付き完全一致（`"key"`/`'key'`）でどこかに出現するかを検査。動的参照用の `_ALLOWLIST` 機構（現状ゼロ件）を用意

## Task Commits

Each task was committed atomically:

1. **Task 1: viewer.py の _show_page_popup ハードコード文言を LANG キー化（C6）** - `f4ce6bb` (fix)
2. **Task 2: page_ops.py の分割エラー messagebox 種別/タイトルを統一（C7）** - `b32d83a` (fix)
3. **Task 3: lang.py 確定未使用キーを削除し D-11 未使用キー検出テストを常設** - `dc20c80` (refactor)

## Files Created/Modified
- `pagefolio/viewer.py` - `_show_page_popup` の4箇所のハードコード日本語文言を `self._t()` 経由の LANG キー参照へ変更
- `pagefolio/page_ops.py` - `_split_by_range` の範囲未入力分岐を `showinfo`→`showerror`+`err_title` へ変更
- `pagefolio/lang.py` - popup_* 4キー新規追加（ja/en）・確定未使用11キー削除（ja/en）
- `tests/test_lang_parity.py` - `test_no_unused_lang_keys`（D-11・全キー参照検査・`_ALLOWLIST` 機構）を新設
- `tests/test_pdf_ops.py` - `test_split_by_range_no_input_shows_error`（C7 回帰テスト）を `TestPdfSplit` へ追加

## Decisions Made
- lang.py の未使用キー検出は AST ではなく grep 相当の「引用符付き完全一致」方式を採用。動的キー合成（f-string 等）はコードベース全体でゼロ件であることを RESEARCH.md で確認済みのため、実装コストの低い方式で十分と判断
- `test_no_unused_lang_keys` の実装・実行の過程で `ocr_progress`/`ocr_progress_render` という RESEARCH.md 確定表には無かった2件の未使用キーを発見。これは Phase 2（OCR磨き込み）の統合プログレス化（D-03）で既に不要化していた活き残りであり、D-19「棚卸しの活き残りは全件解消（次送りしない）」の趣旨および本タスクの目的（未使用キー0件を担保する回帰テストの確立）に照らし、RESEARCH の9件と同時に削除した（詳細は Deviations 参照）
- 削除対象キーの特定は「引用符で囲んだキー名の完全一致」のみで行い、`tesseract_not_installed`（削除）と `tesseract_not_installed_hint`（維持）のようなプレフィックス衝突ペアを誤って巻き込まないことを確認した

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] D-11 検査が新規発見した未使用キー2件（`ocr_progress`/`ocr_progress_render`）を追加削除**
- **Found during:** Task 3（lang.py 確定未使用キー削除・D-11 テスト実装）
- **Issue:** plan/RESEARCH.md の確定未使用リストは9件だったが、新設した `test_no_unused_lang_keys` を実行した時点で `ocr_progress`/`ocr_progress_render` の2件も未使用と判定された。調査の結果、Phase 2（04-03 以前の OCR 磨き込みフェーズ）の統合プログレス化（D-03: レンダリング2段階表示を廃止し `done+skipped/total` の統合表示へ一本化）により、これらのキーは実装上不要になっていたが lang.py には残置されていたことが判明した
- **Fix:** RESEARCH.md 確定9件と同じ完全一致方式で ja/en 両辞書から追加削除。`ocr_progress_init`/`ocr_progress_ocr`（使用中）は維持
- **Files modified:** `pagefolio/lang.py`
- **Verification:** `pytest tests/test_lang_parity.py -x -q` グリーン（`test_no_unused_lang_keys` が未使用0件で通過）・`pytest` フルスイート859件グリーン・`ruff check . && ruff format . --check` クリーン
- **Committed in:** `dc20c80`（Task 3 commit）

---

**Total deviations:** 1 auto-fixed（Rule 1 — bug/dead-code discovered by the very regression test this task establishes）
**Impact on plan:** D-19「棚卸しの活き残りは全件解消」の趣旨と本プランの成功基準（未使用キー0件でテストが成立）を厳密に満たすために必要な追加対応。スコープ拡大ではなく、計画済みタスク（D-11テスト常設）の直接の副産物。

## Issues Encountered

None - 上記デビエーション以外は計画通り。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- V171-UIUX-02（文言/エラー一貫性監査）は本プランで完了。棚卸し確定表（04-RESEARCH.md）の C6・C7・未使用キー全件（RESEARCH 確定9件 + 新規発見2件=計11件）を解消
- Phase 4 の4プラン全完了（04-01 ショートカット基盤・04-02 ShortcutsDialog+SettingsDialog再編・04-03 LLMConfigDialog整理+Ollama重複解消・04-04 本プラン）。V171-UIUX-01〜03・V171-TEST-03 全要件充足
- 拡大ポップアップの実描画（en 表示で日本語が出ないこと）の目視確認は VERIFICATION.md の Manual-Only 項目として記録が必要
- ブロッカーなし。`pytest` フルスイート859件グリーン・`ruff check . && ruff format .` クリーン確認済み

---
*Phase: 04-ui-ux*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files exist on disk (pagefolio/viewer.py, pagefolio/page_ops.py,
pagefolio/lang.py, tests/test_lang_parity.py, tests/test_pdf_ops.py,
.planning/phases/04-ui-ux/04-04-SUMMARY.md) and all task commit hashes
(f4ce6bb, b32d83a, dc20c80) are present in git log.
