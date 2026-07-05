---
phase: 04-ui-ux
verified: 2026-07-05T00:00:00Z
status: human_needed
score: 19/19 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "SettingsDialog の「⌨ ショートカット設定…」ボタンから ShortcutsDialog を開き、各行の「変更」を押して実キーを押下し、keysym が正しくキャプチャされる（修飾キー単体 Control_L 等では確定せず待機継続する）ことを目視確認する"
    expected: "行のキー表示が押下したキーの人間可読表記（例: Ctrl+O）へ更新され、修飾キー単体では待機状態が続く"
    why_human: "Tkinter の実 KeyPress イベントはこの環境で自動生成できず、既存テストスイートにも event_generate を使う実ウィジェットテストが存在しない（04-RESEARCH.md D-20 の既定運用）"
  - test: "同一キーを別コマンドへ割り当てて「保存」を押し、衝突コマンド名を含むエラーダイアログが表示され保存が拒否されることを目視確認する"
    expected: "showerror ダイアログに衝突コマンドの表示名が含まれ、settings への書き込みが行われずダイアログも閉じない"
    why_human: "messagebox の実描画・文言の視覚的な正しさは自動テストでは検証できない"
  - test: "ショートカットを保存した直後（ダイアログを閉じる前）に、新しいキーで実際にコマンドが起動することを目視確認する"
    expected: "保存ボタン押下時点で app._bind_shortcuts() が呼ばれ、新キーが即座に有効になる"
    why_human: "実際のキー入力とコマンド実行の因果は Tk イベントループの実挙動でしか確認できない"
  - test: "SettingsDialog が「外観」「操作」「AI・OCR」の3セクションで表示され、見出しの視覚的な区切り・アイコン（⚙）が意図通りであることを目視確認する"
    expected: "3セクションが区切り線とともに順に表示され、旧🔍アイコンが⚙に置き換わっている"
    why_human: "レイアウトの視覚的妥当性はコード上のpack順序からは完全には保証できず実描画の確認が必要"
  - test: "LLMConfigDialog を開き、「選択中プロバイダ固有の設定」「全プロバイダ共通の設定」の2見出しが正しい位置に表示され、プロバイダ切替（LM Studio/Ollama/RunPod/Claude/Gemini/Tesseract/off）で固有セクションが正しく入れ替わることを目視確認する"
    expected: "見出し順序が 固有見出し→固有フレーム→共通見出し→共通パラメータ という設計通りに視覚的に維持される"
    why_human: "before=self.scale_row による挿入順序はコードから論理的に確認済みだが、実際のレイアウト崩れ（余白・折返し等）は実描画でのみ検出できる"
  - test: "外側 SettingsDialog を開いた状態で「⚙ LLM 設定…」から LLMConfigDialog を開き、値を変更して「適用」を押した後、外側 SettingsDialog を「キャンセル」で閉じても、再度設定を開くと LLM 設定の変更が保持されていることを目視確認する"
    expected: "外側キャンセル後も LLM 設定（例: プロバイダ選択やタイムアウト値）が変更後の値のまま維持される"
    why_human: "cascade の単体ロジックは test_provider_ui.py の TestSettingsDialogNestedApplyCascade で回帰テスト済みだが、実際のダイアログ往復操作での見え方は実機確認が望ましい"
  - test: "拡大ポップアップ（サムネイルまたはページをダブルクリック等で開く画面）を lang='en' 設定で開き、タイトル・縮小/拡大/閉じるボタンが英語で表示され日本語が一切出ないことを目視確認する"
    expected: "ポップアップの全文言が英語（Page N / M、Zoom Out、Zoom In、Close）で表示される"
    why_human: "実際のポップアップ描画（フォント・レイアウト込み）は自動テストでは検証できない"
---

# Phase 4: UI/UX 磨き込み + 既知バグ棚卸し Verification Report

**Phase Goal:** ユーザーはショートカットを GUI で編集でき、エラー表示・文言・ダイアログ配置の一貫性が監査・修正され、既知軽微バグの活き残りが解消されてマイルストーンを締められる。
**Verified:** 2026-07-05
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `build_keysym_from_event` が Control ビット付き state と 'o' から `<Control-o>` を、修飾なし state と 'F5' から `<F5>` を返す | ✓ VERIFIED | `pagefolio/app.py:56-73`; `tests/test_v150_regression.py::TestBuildKeysymFromEvent` passes |
| 2 | `find_duplicate_binding` が衝突コマンド名を返し、非衝突/自分自身/空 keysym で None を返す | ✓ VERIFIED | `pagefolio/app.py:76-87`; `tests/test_v150_regression.py::TestFindDuplicateBinding` passes |
| 3 | `keysym_to_display` が Tk keysym を人間可読表記へ変換する | ✓ VERIFIED | `pagefolio/app.py:90-104`; `tests/test_v150_regression.py::TestKeysymToDisplay` passes |
| 4 | `_bind_shortcuts()` は再呼び出し時に前回バインドした keysym を先に unbind してから再バインドする | ✓ VERIFIED | `pagefolio/app.py:228-259`（234行目 unbind ループ→241行目 merge→248行目 bind の順） |
| 5 | アプリ起動時 `__init__` から `_bind_shortcuts()` が呼ばれ、既定8種＋カスタム設定が動作する | ✓ VERIFIED | `pagefolio/app.py:201-226`（`_default_shortcuts`/`_cmd_map` 設定後に `self._bind_shortcuts()` 呼び出し） |
| 6 | SettingsDialog の「⌨ ショートカット設定…」ボタンから ShortcutsDialog が開き、11コマンドが人間可読表記で一覧表示される | ✓ VERIFIED | `pagefolio/dialogs/settings.py:166-170`（`_open_shortcuts_dialog`）; `pagefolio/dialogs/shortcuts.py:27-39`（`_CMD_ORDER` 11件）・`:165-171`（`_display_text` が `keysym_to_display` 経由） |
| 7 | 「変更」で実キー入力待ちになり、修飾キー単体では確定しない | ✓ VERIFIED | `pagefolio/dialogs/shortcuts.py:189-197, 206-235`（`_MODIFIER_KEYSYMS` チェック） |
| 8 | 同一キーを別コマンドへ割り当てて保存すると衝突コマンド名を含むエラーが表示され保存が拒否される | ✓ VERIFIED | `pagefolio/dialogs/shortcuts.py:254-270`（`_on_save` の重複再検査→`messagebox.showerror`→`return`、settings 未書込） |
| 9 | 保存で既定との差分のみが settings へ書かれ `app._bind_shortcuts()` が呼ばれる | ✓ VERIFIED | `pagefolio/dialogs/shortcuts.py:272-283`（diff 計算→`app.settings["shortcuts"]=diff`→`app._bind_shortcuts()`→`_save_settings`） |
| 10 | 「割当なし（無効化）」でキーを外せ、全体リセットと個別解除の両導線が settings から該当分を除去する | ✓ VERIFIED | `pagefolio/dialogs/shortcuts.py:238-251`（`_clear_cmd`/`_on_reset_all`）+ 保存時の diff 再計算ロジック |
| 11 | SettingsDialog が「外観」「操作」「AI・OCR」の3セクション構成で、旧「LM Studio (OCR)」見出しと🔍アイコンが改称されている | ✓ VERIFIED | `pagefolio/dialogs/settings.py:76-187`（3セクション）; `pagefolio/lang.py:495,512,515`（⚙ 系へ改称・旧🔍除去確認済み） |
| 12 | LLMConfigDialog に共通/固有見出しが表示され、1枚・プロバイダ選択でセクション切替という構造は維持される | ✓ VERIFIED | `pagefolio/dialogs/llm_config.py:156-164`(固有見出し)・`:671-680`(共通見出し)・`:1008-1102`(`_on_provider_change` の `before=self.scale_row` 挿入ロジックは変更なし) |
| 13 | LLMConfigDialog の適用が独立トランザクションとして app.settings（メモリ）へ即時反映され、外側キャンセルでも失われない | ✓ VERIFIED | `pagefolio/app.py:572-`(`_apply_llm_settings_live`)、`pagefolio/dialogs/settings.py:224-250`(nested `on_apply` から `_on_llm_apply` 呼び出し)、`tests/test_provider_ui.py::TestSettingsDialogNestedApplyCascade` pass |
| 14 | OCRDialog から開いた LLMConfigDialog の適用経路（`on_apply(llm_settings)` 規約）は本変更で壊れない | ✓ VERIFIED | `pagefolio/ocr_dialog.py:854-862`（`on_apply=self._apply_llm_settings` の呼び出し規約は変更なし・独立実装のまま） |
| 15 | Ollama のモデル取得・接続テストが LM Studio と同型の単一共通ヘルパーへ統合される | ✓ VERIFIED | `pagefolio/dialogs/llm_config.py:1198-1237`（`_probe_ollama_provider` 新設・`_fetch_ollama_models`/`_test_ollama_connection` が1行ラッパー化） |
| 16 | viewer.py の `_show_page_popup` が `self._t()` 経由で表示され `lang='en'` で日本語が出ない | ✓ VERIFIED | `pagefolio/viewer.py:407,494,499,504`; `pagefolio/lang.py:24-27,646-649`(ja/en 両方に `popup_*` キー存在) |
| 17 | `_split_by_range` の範囲未入力エラーが showerror+err_title で表示され、範囲形式不正と対称になる | ✓ VERIFIED | `pagefolio/page_ops.py:954`(`showerror`+`err_title`) と `:958-960`（同型）; `tests/test_pdf_ops.py::test_split_by_range_no_input_shows_error` pass |
| 18 | lang.py の確定未使用9キーが削除され、ja/en キー集合が一致したまま維持される | ✓ VERIFIED | 11キー（RESEARCH確定9件+D-11検査発見2件）を repo 全体 grep で不在確認・`tesseract_not_installed_hint` は温存確認済み・`test_lang_keys_parity` pass |
| 19 | 全 LANG キーがソース参照されることを検査する回帰テストが常設される（D-11） | ✓ VERIFIED | `tests/test_lang_parity.py::test_no_unused_lang_keys`（引用符付き完全一致・`_ALLOWLIST` 機構付き）pass |

**Score:** 19/19 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/app.py` | keysym純関数3種・`_bind_shortcuts`・`_cmd_map`/`_default_shortcuts`/`_bound_keysyms`・`_apply_llm_settings_live` | ✓ VERIFIED | 全シンボル存在・wired |
| `tests/test_v150_regression.py` | keysym変換・重複検出・表示変換の純関数テスト | ✓ VERIFIED | `TestBuildKeysymFromEvent`/`TestFindDuplicateBinding`/`TestKeysymToDisplay` 存在・pass |
| `pagefolio/dialogs/shortcuts.py` | `ShortcutsDialog` クラス新設 | ✓ VERIFIED | 実装完備・`dialogs/__init__.py` から re-export 確認済み |
| `pagefolio/dialogs/settings.py` | 3セクション再編・`_open_shortcuts_dialog`・`on_llm_apply` 配線 | ✓ VERIFIED | 全て存在し wired |
| `pagefolio/dialogs/__init__.py` | `ShortcutsDialog` re-export | ✓ VERIFIED | `from pagefolio.dialogs.shortcuts import ShortcutsDialog` 確認済み |
| `pagefolio/lang.py` | ShortcutsDialog文言・セクション見出し・改称キー・popup_*・11キー削除 | ✓ VERIFIED | 全キー ja/en 同時存在・削除キーは repo 全体で不参照確認済み |
| `CLAUDE.md` | ファイル構成表への `dialogs/shortcuts.py` 追記 | ✓ VERIFIED | 60行目に記載確認 |
| `pagefolio/dialogs/llm_config.py` | 共通/固有グルーピング見出し・`_probe_ollama_provider` | ✓ VERIFIED | 両方存在・`_on_provider_change` ロジック変更なし確認 |
| `pagefolio/viewer.py` | `_show_page_popup` の LANG キー化 | ✓ VERIFIED | 4箇所とも `self._t()` 経由 |
| `pagefolio/page_ops.py` | `_split_by_range` の messagebox 種別統一 | ✓ VERIFIED | showerror+err_title に統一済み |
| `tests/test_provider_ui.py` | cascade回帰・Ollama共通ヘルパー・API키非流入テスト | ✓ VERIFIED | `TestApplyLlmSettingsLive`/`TestSettingsDialogNestedApplyCascade`/`TestProbeOllamaProvider` 存在・pass |
| `tests/test_pdf_ops.py` | 分割の範囲未入力エラー回帰テスト | ✓ VERIFIED | `test_split_by_range_no_input_shows_error` 存在・pass |
| `tests/test_lang_parity.py` | 未使用キー検出テスト | ✓ VERIFIED | `test_no_unused_lang_keys` 存在・`_ALLOWLIST` 機構付き・pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `PDFEditorApp.__init__` | `self._bind_shortcuts()` | 初回バインド | ✓ WIRED | `app.py:226` |
| `SettingsDialog._open_shortcuts_dialog` | `ShortcutsDialog` | 二重起動ガード付き生成 | ✓ WIRED | `settings.py:252-277` |
| `ShortcutsDialog` 保存 | `find_duplicate_binding` → `settings['shortcuts']` 差分 → `app._bind_shortcuts()` | 保存フロー | ✓ WIRED | `shortcuts.py:254-283` |
| `ShortcutsDialog` | `keysym_to_display`/`build_keysym_from_event` | 表示・キャプチャ | ✓ WIRED | `shortcuts.py:166,220-222` |
| `SettingsDialog` nested `on_apply` | `app._apply_llm_settings_live` | メモリ即時反映 | ✓ WIRED | `settings.py:238-240`, `app.py:572` |
| `app._open_settings` | `SettingsDialog(on_llm_apply=self._apply_llm_settings_live, app=self)` | 配線 | ✓ WIRED | `app.py:561-570` |
| `llm_config._fetch_ollama_models`/`_test_ollama_connection` | `_probe_ollama_provider(update_combo)` | 共通ヘルパー | ✓ WIRED | `llm_config.py:1198-1237` |
| `viewer._show_page_popup` | `self._t('popup_*')` | LANG キー参照 | ✓ WIRED | `viewer.py:407,494,499,504` |
| `page_ops._split_by_range` | `err_title`/`err_split_no_range`（showerror） | messagebox種別統一 | ✓ WIRED | `page_ops.py:954` |
| `test_lang_parity` D-11 検査 | `pagefolio/`/`tests/`/`plugins/` 全ソース走査 | 引用符付きキー literal 照合 | ✓ WIRED | `test_lang_parity.py:24-75` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 純関数3種の代表入力アサート | `pytest tests/test_v150_regression.py -q` | 全件pass | ✓ PASS |
| ja/en LANG キー完全一致 | `pytest tests/test_lang_parity.py -q` | 3 tests pass（parity・format smoke・no_unused_lang_keys） | ✓ PASS |
| ダイアログ連携（SettingsDialog/LLMConfigDialog/Ollama）回帰 | `pytest tests/test_provider_ui.py -q` | 全件pass | ✓ PASS |
| 分割エラー回帰 | `pytest tests/test_pdf_ops.py -k split -q` | pass | ✓ PASS |
| フルスイート回帰 | `pytest -q`（一度のみ実行） | 859 passed | ✓ PASS |
| Lint/Format | `ruff check .` / `ruff format --check .` | クリーン | ✓ PASS |
| 削除された未使用11キーが repo 全体で不参照 | `grep -rn` 各キー | 0件ヒット | ✓ PASS |
| `tesseract_not_installed_hint`（使用中キー）誤削除なし | `python -c "... in LANG['ja']/['en']"` | True/True | ✓ PASS |

Tkinter の実ウィジェット描画・実 KeyPress イベントに依存する項目（ShortcutsDialogのキャプチャ操作・SettingsDialog/LLMConfigDialogの実レイアウト・拡大ポップアップの実描画）はこの環境で自動化できないため、Human Verification セクションへ計上（04-RESEARCH.md D-20 の既定運用）。

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| V171-UIUX-01 | 04-01, 04-02 | ショートカットGUI編集（JSON直接編集不要化） | ✓ SATISFIED | 純関数+`_bind_shortcuts()`（04-01）+ ShortcutsDialog 実装・配線（04-02） |
| V171-UIUX-02 | 04-04 | エラー表示・文言の一貫性監査（ja/en辞書欠落/未使用キー・L-5吸収） | ✓ SATISFIED | C6/C7 解消・未使用11キー削除・D-11回帰テスト常設 |
| V171-UIUX-03 | 04-02, 04-03 | SettingsDialog/LLMConfigDialog の項目配置・セクション整理 | ✓ SATISFIED | 3セクション再編（04-02）+ 共通/固有グルーピング・ネストトランザクション化（04-03） |
| V171-TEST-03 | 04-03 | 既知軽微バグ棚卸し・活き残り解消（L-6と非重複） | ✓ SATISFIED | C1(解消済み確認)〜C9(該当なし確認) 全件処理・C2(Ollama重複)を本フェーズで解消 |

REQUIREMENTS.md のトレーサビリティ表（`| V171-UIUX-01〜03 | Phase 4 | Complete |`・`| V171-TEST-03 | Phase 4 | Complete |`）と一致。オーファン要件なし。

### Anti-Patterns Found

フェーズで変更された全ファイル（`app.py`, `dialogs/shortcuts.py`, `dialogs/settings.py`, `dialogs/llm_config.py`, `viewer.py`, `page_ops.py`, `lang.py`）を TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER でスキャンした結果、デブトマーカーは検出されなかった（`viewer.py` の "placeholder" ヒットはサムネイル遅延表示の正規機能名であり、スタブを意味しない）。

コードレビュー（`04-REVIEW.md`）で以下2件の非クリティカルな警告が検出されている（新規コード品質の情報として記録。フェーズ成功基準そのものは満たされているため gap ではなく info として扱う）:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pagefolio/dialogs/shortcuts.py` | `_start_capture` 189-197 | 別行の「変更」ボタンを連続で押すと前の行の「キーを押してください…」表示が更新されずに残る（データ損失なし・表示のみ） | ⚠️ Warning (info) | UX上の軽微な表示崩れ。`self._shortcuts` のデータには影響しない |
| `pagefolio/dialogs/shortcuts.py` / `app.py` | `_on_capture_keypress` 206-235 / `_bind_shortcuts` | 修飾キーなしの単独キー（例: 素の `5`）でも確定してしまい、`root` へのグローバルバインドのため他のウィジェット（Spinboxへの数字入力等）とキー衝突しうる | ⚠️ Warning (info) | 新規に露出したユーザビリティ上のリスク。データ損失やクラッシュではない |

これら2件はコードレビューで「non-blocking」と判定済み（critical: 0）であり、V171-UIUX-01の成功基準（GUI編集・保存・反映・JSON直接編集不要化）を損なうものではないため、フェーズの gap には計上しない。将来のフォローアップ候補として記録する。

### Human Verification Required

Tkinter の実ウィジェット描画・実キーイベントに依存するため自動検証できない項目（frontmatter の `human_verification` を参照）:

1. ShortcutsDialog の実キーキャプチャ動作（修飾キー単体では確定しないこと）
2. 重複キー保存時のエラーダイアログ表示
3. 保存直後の即時反映（ダイアログを閉じる前の新キー動作）
4. SettingsDialog の3セクション表示・⚙アイコン改称の視覚確認
5. LLMConfigDialog の共通/固有見出し表示・プロバイダ切替時のレイアウト
6. LLMConfigDialogのネスト適用cascade実挙動（外側キャンセル後もLLM設定が保持される）
7. 拡大ポップアップの`lang='en'`表示（日本語が出ないこと）

### Gaps Summary

構造的な gap は検出されなかった。全19の観測可能な真実（Observable Truths）が既存の自動テスト（859件フルスイートグリーン・`ruff check`/`ruff format`クリーン）とソースコードの直接確認により裏付けられている。4件の要件ID（V171-UIUX-01/02/03, V171-TEST-03）はすべてREQUIREMENTS.mdで「Complete」として記録され、対応するプラン成果物・回帰テストで担保されている。

唯一の残課題は、Tkinter GUIの実描画・実キーイベントに依存する7項目の目視確認であり、これは04-RESEARCH.mdのD-20（Tk実ウィジェット生成テストが既存スイートに存在しないための既定運用）に沿って人間検証項目として計上した。コードレビューで見つかった2件の非クリティカルなShortcutsDialogの挙動上の粗（WR-01: 行切替時のラベル残留、WR-02: 無修飾キーの許容）はデータ損失やクラッシュを伴わず、フェーズの成功基準を損なわないためgapではなくフォローアップ候補として記録した。

---

*Verified: 2026-07-05*
*Verifier: Claude (gsd-verifier)*
