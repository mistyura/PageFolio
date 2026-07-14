---
phase: 02-ai
verified: 2026-07-14T23:00:00+09:00
status: gaps_found
score: 13/17 must-haves verified
behavior_unverified: 3 # present + wired, no behavioral test exercises the state transition — see behavior_unverified_items
overrides_applied: 0
gaps:
  - truth: "ユーザーは OCR カスタム/サマリプロンプトを名前付きテンプレートとして保存し、一覧から選択・削除・リネームできる（ロードマップ Success Criteria 1 / 02-02 must_haves）"
    status: failed
    reason: "02-REVIEW.md CR-02（未修正・現HEAD 406e9c2 の時点でも解消されていない）。LLMConfigDialog.__init__ が current_settings を dict() の浅いコピーのみ行うため self.current_settings['prompt_templates'] は self.app.settings['prompt_templates'] と同一オブジェクト参照を共有する。sections.py の _on_template_save/_on_template_delete/_on_template_rename は save_template/delete_template/rename_template（settings.py、いずれも in-place 変更）を呼んだ直後に _save_settings(self.current_settings) で即座にディスクへ永続化する。結果、ユーザーが『キャンセル』ボタン（destroy のみ・on_apply を呼ばない）を押しても、直前のテンプレート削除/保存/リネームは既に app.settings と pagefolio_settings.json の両方に確定済みで取り消せない。『キャンセルで変更を破棄する』という一般的なダイアログ契約を裏切るデータ消失リスクであり、テンプレート削除・リネームという本フェーズの中核機能が安全に使えない"
    artifacts:
      - path: "pagefolio/dialogs/llm_config/dialog.py"
        issue: "line 46: self.current_settings = dict(current_settings) — トップレベルのみの浅いコピー。ネストした prompt_templates/items は app.settings と同一参照のまま"
      - path: "pagefolio/dialogs/llm_config/sections.py"
        issue: "line 1269/1275（_on_template_save）・1293/1299（_on_template_delete）・1320/1328（_on_template_rename）が共有参照を in-place 変更した直後に _save_settings() で即時永続化し、Apply/Cancel のゲートを経由しない"
    missing:
      - "dialog.py の __init__ で current_settings を渡す側（呼び出し元 ocr_dialog.py:951-959）または __init__ 内部で prompt_templates（active/items）をディープコピーし、ダイアログ内の CRUD 操作が app.settings を汚染しないようにする（copy.deepcopy 等）"
      - "上記と合わせて『即時確定』の現行仕様を維持するかどうかの設計判断（Apply 経由の一括確定へ変更する場合は _on_template_save 等から _save_settings 呼び出しを外し、_apply 側で一括収集・永続化する）"
      - "最低限の代替策として、_on_template_delete に削除確認（messagebox.askyesno）を追加し誤操作を1段階防止する（02-REVIEW.md Fix 案2）"
deferred: []
behavior_unverified_items:
  - truth: "テンプレート切替時、外部mdファイル連動モードでは未保存差分の確認ダイアログ（askyesno）を挟み、キャンセルで切替を中止する（D-05・02-02 must_haves）"
    test: "実 Tk ウィジェット（LLMConfigDialog インスタンス）を生成し、外部 md ファイルが存在する状態で ocr_prompt_text を編集後 template_combo を別テンプレートへ切替操作し、messagebox.askyesno が呼ばれること・No 応答で選択が元のアクティブテンプレートへ戻り入力欄が変化しないことを確認する"
    expected: "askyesno が呼ばれ、キャンセル（No）で切替が中止され入力欄・アクティブテンプレートが変化しない"
    why_human: "_on_template_change は _build() 実行後の実 Tk ウィジェット（ocr_prompt_text 等）に依存し、tests/test_provider_ui.py::TestTemplateSection は source-scan と非バインドスタブ経由の _apply 検証のみで、この状態遷移を駆動する実 Tk ベースのテストが存在しない（02-02-SUMMARY.md 自身が human_judgment: true と記録）"
  - truth: "テンプレート切替後、選択テンプレートの内容で外部mdファイルを上書きし『アクティブテンプレートのライブ編集内容』の不変条件を保つ（D-07/D-08・02-02 must_haves）"
    test: "上記と同一操作後、ocr_custom_prompt.md/ocr_summary_prompt.md の内容が新しいアクティブテンプレートの内容で上書きされていることをファイル読み取りで確認する"
    expected: "外部ファイルの内容が新アクティブテンプレートの custom_prompt/summary_prompt と一致する"
    why_human: "save_prompt_file 呼び出し（sections.py 1233-1235）を実際に駆動する Tk ベーステストが存在しない（source 確認のみ）"
  - truth: "テンプレート名の重複は保存/リネーム時に messagebox.showerror で拒否される（D-04・02-02 must_haves・UI 経由）"
    test: "実 Tk ウィジェットで _on_template_save/_on_template_rename を askstring モック経由で呼び、既存名を入力した際に messagebox.showerror が呼ばれ save_template/rename_template が呼ばれないことを確認する"
    expected: "showerror が呼ばれ、テンプレート一覧が変化しない"
    why_human: "settings.py の save_template/rename_template（純ロジック）は test_prompt_templates.py::TestDeleteRename で検証済みだが、UI ハンドラの try/except→showerror 経路自体を駆動する実 Tk テストは存在しない"
  - truth: "アクティブテンプレートの削除ボタンは無効化される（D-03・02-02 must_haths・UI 経由）"
    test: "実 Tk ウィジェットでテンプレートを選択しアクティブ化した状態で template_delete_btn の state に 'disabled' が含まれることを確認する"
    expected: "アクティブテンプレート選択時は削除ボタンが disabled、非アクティブ選択時は有効"
    why_human: "_refresh_template_delete_state は実ウィジェット（ttk.Button.state()）に依存し、source-scan のみで実際のボタン状態遷移は未検証（settings.py 側の delete_template ValueError 二重防御は test_prompt_templates.py::TestDeleteRename で検証済み）"
human_verification:
  - test: "外部mdファイル連動モードで未保存差分がある状態でテンプレートを切替え、askyesno が表示されること・キャンセルで切替が中止されることを目視確認する"
    expected: "確認ダイアログが表示され、キャンセルで入力欄・アクティブテンプレートが変化しない"
    why_human: "Tk ウィジェット駆動のテストが存在しないため（behavior_unverified_items 参照）"
  - test: "テンプレート切替後、ocr_custom_prompt.md/ocr_summary_prompt.md の内容が新アクティブテンプレートの内容に置き換わっていることをファイルで確認する"
    expected: "外部ファイル内容が新テンプレート内容と一致する"
    why_human: "Tk ウィジェット駆動のテストが存在しないため"
  - test: "テンプレート名を重複させて保存/リネームした際に showerror が表示されること、アクティブテンプレート選択時に削除ボタンが無効化されていることを目視確認する"
    expected: "重複時はエラー表示、アクティブテンプレートは削除不可（ボタン無効）"
    why_human: "Tk ウィジェット駆動のテストが存在しないため"
  - test: "テンプレートを保存/削除/リネームした直後に『キャンセル』ボタンを押し、pagefolio_settings.json とアプリ内 self.app.settings の両方でその変更が本当に取り消されないこと（＝CR-02 の実害）を実機で確認する"
    expected: "現状は取り消されない（CR-02 の実害を人手で最終確認し、修正要否をユーザーに判断してもらう）"
    why_human: "ディスク書き込み・実ダイアログのライフサイクルを伴うため自動テストで完全再現するより実機確認が確実"
---

# Phase 02: AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック） Verification Report

**Phase Goal:** ユーザーが OCR/サマリ用プロンプトを名前付きテンプレートとして管理する UI と、プロバイダー障害時に安全な手動フォールバックで処理を継続する仕組みを LLM 設定ダイアログに追加する。
**Verified:** 2026-07-14T23:00:00+09:00
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

出典: ①ROADMAP.md Phase 2 Success Criteria（1〜5・ロードマップ契約）②各 PLAN.md frontmatter の `must_haves.truths`（プラン単位の詳細）。ROADMAP の Success Criteria を優先し、プラン単位の詳細で補完した。

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (SC1) | ユーザーは名前付きテンプレートとして保存し、一覧から選択・削除・リネームできる | ✗ FAILED | 機能自体は settings.py の CRUD 純関数（6関数・test_prompt_templates.py 32件で検証済み）と UI ワイヤリング（sections.py の 3ボタン・combobox）で動作するが、**02-REVIEW.md CR-02（未修正）**: `dialog.py:46` の浅いコピーにより `self.current_settings["prompt_templates"]` が `app.settings["prompt_templates"]` と同一参照。CRUD ハンドラが即座に `_save_settings()` で永続化するため『キャンセル』で取り消せない（データ消失リスク）。gaps 参照 |
| 2 (SC2) | 外部 md ファイル連動はアクティブテンプレートのライブ編集として機能し、テンプレート切替時に書き戻し競合が起きない | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `_on_template_change`（sections.py:1197-1242）に D-05（askyesno 未保存差分確認）→D-07（外部ファイル上書き）のロジックはソース上存在し、02-CONTEXT.md の設計どおり実装されているが、実 Tk ウィジェットでこの状態遷移を駆動するテストが無い（02-02-SUMMARY.md 自身が human_judgment: true と記録）。behavior_unverified_items 参照 |
| 3 (SC3) | 保存したテンプレートは Claude/Gemini/LM Studio 等の全プロバイダで共通して選択・適用できる | ✓ VERIFIED | `load_custom_prompt`/`load_summary_prompt`（settings.py）が3段解決（外部ファイル>アクティブテンプレート>設定欄）を実装し `resolve_ocr_prompt`/`resolve_summary_prompt`（ocr.py）は無改造。`tests/test_provider_ui.py::TestTemplateSection::test_save_template_then_load_custom_prompt_resolves`/`test_save_template_then_load_summary_prompt_resolves`・`tests/test_prompt_templates.py::TestExternalFileSync` で実値検証済み（全 pass） |
| 4 (SC4) | ユーザーはフォールバック順を明示的に設定でき、未設定時はフォールバックが発生しない（安全側既定） | ✓ VERIFIED | `_load_settings()` の既定値 `ocr_fallback_enabled=False`/`ocr_fallback_chain=[]`（settings.py:274-277）。`next_fallback_candidate([], set())` が None を返すことを `tests/test_ocr_fallback.py::TestDisabledByDefault` で検証。UI（sections.py の🔁セクション・トグル既定OFF）・`_apply` 収集（`tests/test_provider_ui.py::TestFallbackSection::test_apply_defaults_when_fallback_attrs_absent`）も検証済み |
| 5 (SC5) | fatal エラー停止時、並列度/APIキー/レート制限を正しく引き継いだ次候補への切替が送信先確認ダイアログの再提示つきで提案され、承認なしに自動送信されない | ✓ VERIFIED | `_propose_fallback`/`_switch_to_fallback_provider`（ocr_dialog.py）が毎回 `messagebox.askyesno` を再提示し、拒否/無効時は送信しない。`tests/test_ocr_fallback.py::TestConfirmationGate::test_approval_switches_and_calls_on_run_with_candidate_settings` が `build_provider` に candidate 設定（`ocr_provider==candidate`）が渡ること・`self.app.settings` が不変であることを実際に bound method 呼び出しで検証（レビュー HIGH 回帰防止: `inspect.getsource(_on_run).count('self.app.settings')==1` も成立を確認済み） |
| 6 | settings.py テンプレート CRUD 純関数（save/get/list/delete/rename/exists）が正しく動作する | ✓ VERIFIED | `tests/test_prompt_templates.py::TestSaveTemplate`/`TestListAndSelect`/`TestDeleteRename` 全 pass。コード確認済み（settings.py:161-237） |
| 7 | アクティブテンプレートの削除は ValueError で拒否される（純ロジック層・D-03） | ✓ VERIFIED | `delete_template`（settings.py:203-216）が active 一致で ValueError。`TestDeleteRename` で検証 |
| 8 | テンプレート名の空文字・重複が純関数で検出される（D-04） | ✓ VERIFIED | `save_template`/`rename_template` の ValueError 送出をテストで確認 |
| 9 | next_fallback_candidate/next_summary_candidate が正しく次候補を選ぶ（tesseract 除外含む・D-10/D-12） | ✓ VERIFIED | `pagefolio/ocr_fallback.py` は Tk/fitz 非依存（grep 確認済み）。`tests/test_ocr_fallback.py::TestNextCandidate`/`TestSummaryCandidateFilter` 全 pass |
| 10 | テンプレート名の重複は保存/リネーム時に UI（messagebox.showerror）で拒否される（D-04・UI 経由） | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `_on_template_save`/`_on_template_rename`（sections.py:1244-1329）の try/except→showerror 経路はソース上存在するが、実 Tk 駆動テストが無い |
| 11 | アクティブテンプレートの削除ボタンは無効化される（D-03・UI 経由） | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `_refresh_template_delete_state`（sections.py:1177-1183）はソース上存在するが、実ウィジェット state の駆動テストが無い |
| 12 | アクティブテンプレート名が `_apply` 経由で `items` を保持したまま永続化される | ✓ VERIFIED | `dialog.py:_apply` の `llm_settings["prompt_templates"]` 収集を `tests/test_provider_ui.py::TestTemplateSection::test_apply_collects_active_template_preserving_items` で検証（実際の `_apply` bound method 呼び出し） |
| 13 | 🔁フォールバック独立セクション（トグル+Listbox+上下ボタン+候補追加/除外）が存在し D-13/14/15/16 を満たす | ✓ VERIFIED | sections.py:995-1123（`fallback_enabled_var`/`fallback_listbox`/`fallback_up_btn`/`fallback_down_btn`/`_base_fallback_providers` 等すべて確認）。候補一覧・ホワイトリスト構築ロジックは分岐のない構築コードでコードレビューにより妥当性確認 |
| 14 | `ocr_fallback_enabled`/`ocr_fallback_chain` が `_apply` 経由でホワイトリスト検証つきで永続化される | ✓ VERIFIED | `tests/test_provider_ui.py::TestFallbackSection::test_apply_collects_fallback_enabled_and_chain`/`test_apply_filters_unknown_provider_from_chain` で実際の `_apply` bound method 呼び出しにより検証 |
| 15 | `_on_run`/`_on_summary` 等6メソッドが `settings=` 引数で一般化され、内部の `self.app.settings` 直参照がスナップショット経由へ統一される（レビュー HIGH/MEDIUM 対応） | ✓ VERIFIED | `inspect.getsource(OCRDialog._on_run).count('self.app.settings')==1`・`_on_summary` も同様に1、をこの検証で実行し成立を確認。シグネチャに `settings` 引数が含まれることも確認 |
| 16 | `_validate_provider_readiness` が実行不可プロバイダ（tesseract 未インストール/クラウドキー未解決）を build 前に検出し、次候補へ進む（レビュー LOW 対応） | ✓ VERIFIED | `tests/test_ocr_fallback.py::TestProviderReadiness` 全 pass（実際の bound method 呼び出し） |
| 17 | フォールバック切替中も `self.app.settings` を一切書き換えない（Pitfall 4） | ✓ VERIFIED | `tests/test_ocr_fallback.py::TestSettingsIsolation`・`TestConfirmationGate::test_approval_switches_and_calls_on_run_with_candidate_settings`（`d.app.settings["ocr_provider"] == "claude"` のまま変化しないことをアサート）で検証 |

**Score:** 13/17 truths verified（3 present-behavior-unverified・1 failed）

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/ocr_fallback.py` | 次候補選択の純関数2本（Tk/fitz 非依存） | ✓ VERIFIED | 56行・`next_fallback_candidate`/`next_summary_candidate` 実装。`import (tkinter|fitz)` 0件 |
| `pagefolio/settings.py`（拡張） | テンプレート CRUD 6関数 + 3デフォルトキー + 3段プロンプト解決 | ✓ VERIFIED | 364行。全関数・デフォルトキー存在確認済み |
| `pagefolio/dialogs/llm_config/sections.py`（拡張） | 📄テンプレートセクション + 🔁フォールバックセクション | ✓ VERIFIED | 1403行。両セクションのウィジェット・ハンドラ全存在確認済み |
| `pagefolio/dialogs/llm_config/dialog.py`（拡張） | `_apply` でのテンプレート/フォールバック収集 | ✓ VERIFIED（ただし CR-02 起因の設計欠陥あり） | `_apply`（359-500行）に `prompt_templates`/`ocr_fallback_enabled`/`ocr_fallback_chain` 収集を確認。`current_settings` の浅いコピー（46行）が CR-02 の根本原因 |
| `pagefolio/ocr_dialog.py`（拡張） | `_propose_fallback`/`_switch_to_fallback_provider`/`_validate_provider_readiness`/`_active_ocr_settings` | ✓ VERIFIED | 2474行。全メソッド・属性存在確認済み。フック接続（`_finish_error`/`_on_summary_error`末尾）も確認 |
| `pagefolio/lang.py`（拡張） | `tmpl_*`/`fallback_*` キー（ja/en 一致） | ✓ VERIFIED | `test_lang_parity.py` 含むフルスイート pass。ja/en キー完全一致（425/425・02-REVIEW.md 記載） |
| `tests/test_prompt_templates.py` | 新規テストファイル | ✓ VERIFIED | 32件、全 pass |
| `tests/test_ocr_fallback.py` | 新規テストファイル | ✓ VERIFIED | 拡張含め全 pass（`TestDisabledByDefault`/`TestNextCandidate`/`TestSummaryCandidateFilter`/`TestSettingsIsolation`/`TestConfirmationGate`/`TestSummaryFallback`/`TestProviderReadiness`） |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `settings._load_settings` defaults | `pagefolio_settings.json`（既存ファイル） | `setdefault` マイグレーションループ | ✓ WIRED | `python -c` での実値確認済み（プラン記載どおり） |
| `load_custom_prompt`/`load_summary_prompt` | 全 OCR プロバイダ | `resolve_ocr_prompt`/`resolve_summary_prompt`（ocr.py・無改造） | ✓ WIRED | シグネチャ不変確認済み・全プロバイダ共通経路がテストで検証済み |
| `template_combo` の `<<ComboboxSelected>>` | `_on_template_change` | tkinter イベントバインド | ✓ WIRED（ソース確認・実行時挙動は behavior_unverified） | sections.py で bind 確認 |
| `dialog.py._apply` | `_apply_llm_settings`（ocr_dialog.py） | `on_apply(llm_settings)` コールバック | ✓ WIRED | `self.app.settings.update(llm_settings)`→`_save_settings` 経路を確認 |
| `fallback_enabled_var` トグル | `fallback_list_frame` の pack/pack_forget | `_on_fallback_toggle` | ✓ WIRED（ソース確認） | `_on_provider_change` と同型パターンで実装確認 |
| `_finish_error`/`_on_summary_error` 末尾 | `_propose_fallback` | 直接呼び出し | ✓ WIRED | ocr_dialog.py:1919/2268 で確認 |
| `_propose_fallback` | `ocr_fallback.next_fallback_candidate`/`next_summary_candidate` | import + 呼び出し | ✓ WIRED | ocr_dialog.py で import・呼び出し確認 |
| `_switch_to_fallback_provider` | `_on_run(resume=True, settings=fb)` / `_on_summary(settings=fb)` | 直接呼び出し | ✓ WIRED（テストで実証） | `TestConfirmationGate`/`TestSummaryFallback` で `build_provider` が candidate 設定で呼ばれることを実証 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| フォールバック純ロジック・テンプレートCRUD・UI wiring・オーケストレーション全テスト | `pytest tests/test_prompt_templates.py tests/test_ocr_fallback.py tests/test_provider_ui.py tests/test_lang_parity.py -q` | 170 passed | ✓ PASS |
| フルスイート回帰なし確認 | `pytest -q` | 974 passed | ✓ PASS |
| lint/format | `ruff check . && ruff format --check .` | All checks passed / 72 files already formatted | ✓ PASS |
| `_on_run`/`_on_summary` の app.settings 直参照解消（レビュー HIGH/MEDIUM 回帰防止） | `python -c "inspect.getsource(...).count('self.app.settings')"` | on_run=1, on_summary=1 | ✓ PASS |
| CR-01/CR-02 の現況確認（未修正であることの直接コード確認） | `Read`/`grep`/`git blame` による現HEAD確認 | CR-01: dialog.py:60（`_last_valid_provider` が `_detect_tesseract()` 前に初期化）・CR-02: dialog.py:46（浅いコピー）+ sections.py:1275/1299/1328（即時 `_save_settings`）とも現状変更なし | ✗ FAIL（未修正の確認） |

### Probe Execution

該当なし（本フェーズに `scripts/*/tests/probe-*.sh` 形式のプローブは定義されていない）。Step 7b の behavioral spot-check とテストスイート実行で代替。

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| V180-TMPL-01 | 02-01, 02-02 | 名前付きテンプレート保存 | ⚠ SATISFIED（gap: CR-02） | CRUD 純関数・UI 配線は機能するが、保存操作がキャンセル不能で即時永続化される安全性欠陥あり |
| V180-TMPL-02 | 02-02 | 一覧選択切替 | ⚠ SATISFIED（human 未検証） | combobox・`_on_template_change` はソース上実装済みだが実 Tk 駆動テストなし |
| V180-TMPL-03 | 02-01, 02-02 | 削除・リネーム | ⚠ SATISFIED（gap: CR-02） | 同上。純ロジック層の ValueError 二重防御は健全だが UI 経由の即時永続化がキャンセル契約を破る |
| V180-TMPL-04 | 02-01, 02-02 | 外部mdファイル連動との共存 | ⚠ SATISFIED（human 未検証） | D-05/D-07 実装済みだが実 Tk 駆動テストなし |
| V180-TMPL-05 | 02-01, 02-02 | 全プロバイダ横断共有 | ✓ SATISFIED | `load_custom_prompt`/`load_summary_prompt` 経由でテスト実証済み |
| V180-FALL-01 | 02-01, 02-03 | フォールバック順の明示設定・安全側既定 | ✓ SATISFIED | 既定 OFF・空チェーンをテストで確認 |
| V180-FALL-02 | 02-04 | fatal 時の確認ダイアログ再提示つき提案 | ✓ SATISFIED | `TestConfirmationGate` で実証 |
| V180-FALL-03 | 02-01, 02-03, 02-04 | 並列度・APIキー・レート制限の正しい引き継ぎ | ✓ SATISFIED | `_switch_to_fallback_provider` の `max_concurrency` 再クランプ・`_resolve_api_key` 呼び出し・`TestSettingsIsolation`/`TestConfirmationGate` で実証 |

REQUIREMENTS.md Phase 2 Traceability（8件）と各 PLAN.md frontmatter の `requirements:` 宣言を突合した結果、孤立要件（ORPHANED）は無し。8件すべてがいずれかのプランに宣言されている。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pagefolio/dialogs/llm_config/dialog.py` | 46 | 浅いコピー（`dict(current_settings)`）でネスト辞書 `prompt_templates` が `app.settings` と共有参照になる | 🛑 Blocker | CR-02: テンプレート CRUD 操作がキャンセル不能・即時永続化される（データ消失リスク） |
| `pagefolio/dialogs/llm_config/sections.py` | 1269-1275, 1293-1299, 1319-1328 | CRUD ハンドラが Apply/Cancel を経由せず `_save_settings()` を即座に呼ぶ | 🛑 Blocker | 上記と同一原因（CR-02 の直接的な発火点） |
| `pagefolio/dialogs/llm_config/dialog.py` | 60 | `self._last_valid_provider = current_settings.get("ocr_provider", "off")` が `_detect_tesseract()`（63行）より前に評価され、Tesseract 可用性を考慮しない | ⚠️ Warning | CR-02-01（02-REVIEW.md CR-01）: Tesseract 未インストール環境で `pagefolio_settings.json` に `"ocr_provider": "tesseract"` が残っていると初回表示が不完全になる。**Phase 1 の機械的パッケージ分割（commit `4a17921`）由来の既存バグで Phase 2 が新規導入したものではないが、本フェーズが同ファイルを重点的に拡張したにもかかわらず未修正のまま残存**。Phase 2 の TMPL/FALL の各 must-have truth には抵触しないため gaps には計上しないが、別途の修正タスクを推奨 |
| `pagefolio/ocr_dialog.py` | 2367-2418 (`_switch_to_fallback_provider`) | フォールバック切替成功後に `_refresh_provider_dependent_ui()` を呼ばず、プロバイダ表示ラベル（`_provider_display_name`/`_provider_model_name`）が `self.app.settings` 参照のまま更新されない | ⚠️ Warning | 02-REVIEW.md WR-01。送信先確認ダイアログ自体は正しい情報を表示するため V180-FALL-02 の同意フローは健全だが、切替後の常設表示が古いプロバイダのままになり透明性がやや損なわれる |
| `pagefolio/ocr_dialog.py` | 2024-2025 (`_on_summary`) | `s = settings if settings is not None else self.app.settings`（コピーなし）で `_active_ocr_settings` が `app.settings` のエイリアスになる（`_on_run` は `dict(...)` でコピーする非対称） | ℹ️ Info | 02-REVIEW.md WR-02。現状は読み取り専用のみで実害なしだが、将来の書き込み追加時に Pitfall 4 が破られやすい構造 |
| `pagefolio/ocr_dialog.py` | 1283-1290 | 未知クラウドプロバイダの APIキー未設定メッセージが Claude 固有文言 (`ocr_api_key_missing`) にフォールバックする | ℹ️ Info | 02-REVIEW.md WR-03。プレースホルダで env_var 自体は正しく埋まるため実害は軽微 |

デバッグマーカー（TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER）の grep スキャンでは、本フェーズが変更した6ファイル（settings.py・ocr_fallback.py・sections.py・dialog.py・ocr_dialog.py・lang.py）に該当なし（lang.py の「CR-01」コメントは無関係な旧 v1.7.1 期の UI プレースホルダ文言コメントで本フェーズの CR-01 とは無関係）。

### Human Verification Required

frontmatter の `human_verification`（4件）を参照。いずれもテンプレート切替・重複拒否・削除ボタン無効化の実 Tk 挙動、および CR-02 の実害（キャンセルで取り消せないこと）の実機確認。

### Gaps Summary

**ブロッカー（1件・CR-02）:** LLMConfigDialog がテンプレート CRUD 操作（保存/削除/リネーム）を「キャンセル」で取り消せない設計欠陥が未修正のまま残っている。`dialog.py:46` の浅いコピーによりネスト辞書 `prompt_templates` が `app.settings` と共有参照になり、`sections.py` の各ハンドラが即座に `_save_settings()` でディスクへ確定させるため、Apply/Cancel という一般的なダイアログ契約が守られない。これは 02-REVIEW.md で CRITICAL として報告され、直後のコミット（現HEAD `406e9c2`）はレビュー報告の追加のみで修正は行われていない。テンプレート削除・リネームという本フェーズの中核機能（V180-TMPL-01/03・ロードマップ Success Criteria 1）が安全に使えない状態であり、gaps_found の根拠とする。

**参考（gaps には非計上・別件推奨）:** CR-01（Tesseract 未インストール時の `_last_valid_provider` 初期化バグ）は 02-REVIEW.md で CRITICAL 認定されているが、Phase 1 の機械的パッケージ分割（commit `4a17921`）に由来する既存バグであり、Phase 2 の対象要件（V180-TMPL-01〜05・V180-FALL-01〜03）のいずれの must-have にも抵触しない。ただし本フェーズが同じ `dialog.py` を重点的に拡張しながら見過ごされた点、および CRITICAL 認定である点を踏まえ、別途の修正タスク（新規バグ修正）として速やかに着手することを推奨する。

**未検証（human_needed 相当・3件）:** テンプレート切替の D-05（未保存差分確認）/D-07（外部ファイル上書き）フロー、D-04（重複名拒否 UI）、D-03（削除ボタン無効化 UI）は、実装はソース上確認できるが実 Tk ウィジェットを駆動する自動テストが存在しない（02-02-SUMMARY.md 自身も D4 を human_judgment: true と記録済み）。フォールバック側（02-04）は headless スタブによる実メソッド呼び出しテストで十分に実証されているのに対し、テンプレート側（02-02）の UI ハンドラ層はテストカバレッジの質に非対称なギャップがある。

**確実に機能している部分:** 純ロジック層（settings.py の CRUD 6関数・ocr_fallback.py の2関数）、テンプレートの全プロバイダ横断共有（V180-TMPL-05）、フォールバックのオーケストレーション全体（V180-FALL-01〜03・レビュー HIGH/MEDIUM/LOW 対応含む）は、実際の bound method 呼び出しによる behavioral テストで裏付けられており、高い信頼度で正しく動作する。

---

_Verified: 2026-07-14T23:00:00+09:00_
_Verifier: Claude (gsd-verifier)_
