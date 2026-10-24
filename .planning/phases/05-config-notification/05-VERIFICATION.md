---
phase: 05-config-notification
verified: 2026-10-24T11:47:08Z
status: passed
score: 23/23 must-haves verified
covered_files: [".planning/phases/05-config-notification/05-01-PLAN.md",".planning/phases/05-config-notification/05-01-SUMMARY.md",".planning/phases/05-config-notification/05-02-PLAN.md",".planning/phases/05-config-notification/05-02-SUMMARY.md",".planning/phases/05-config-notification/05-03-PLAN.md",".planning/phases/05-config-notification/05-03-SUMMARY.md",".planning/phases/05-config-notification/05-04-PLAN.md",".planning/phases/05-config-notification/05-04-SUMMARY.md",".planning/phases/05-config-notification/05-EVIDENCE.json",".planning/phases/05-config-notification/05-REVIEW-DISPOSITION.md",".planning/phases/05-config-notification/05-REVIEW.md",".planning/phases/05-config-notification/05-SECURITY.md",".planning/phases/05-config-notification/05-UAT.md",".planning/phases/05-config-notification/05-VALIDATION.md",".planning/phases/05-config-notification/05-focus-proof-final/pytest.txt",".planning/phases/05-config-notification/05-focus-proof-final/status.json",".planning/phases/05-config-notification/05-focus-proof-inputs.json","docs/CONFIGURATION.md","pagefolio.py","pagefolio/__init__.py","pagefolio/__main__.py","pagefolio/app.py","pagefolio/batch_ocr_state.py","pagefolio/constants.py","pagefolio/dialogs/__init__.py","pagefolio/dialogs/about.py","pagefolio/dialogs/batch_ocr.py","pagefolio/dialogs/export_images.py","pagefolio/dialogs/llm_config/__init__.py","pagefolio/dialogs/llm_config/dialog.py","pagefolio/dialogs/llm_config/model_fetch.py","pagefolio/dialogs/llm_config/sections.py","pagefolio/dialogs/merge.py","pagefolio/dialogs/password.py","pagefolio/dialogs/plugin.py","pagefolio/dialogs/settings.py","pagefolio/dialogs/shortcuts.py","pagefolio/dnd.py","pagefolio/file_drop.py","pagefolio/file_ops.py","pagefolio/lang.py","pagefolio/md_render.py","pagefolio/ocr.py","pagefolio/ocr_dialog.py","pagefolio/ocr_engine.py","pagefolio/ocr_fallback.py","pagefolio/ocr_pipeline.py","pagefolio/ocr_providers/__init__.py","pagefolio/ocr_providers/base.py","pagefolio/ocr_providers/catalog.py","pagefolio/ocr_providers/claude.py","pagefolio/ocr_providers/errors.py","pagefolio/ocr_providers/gemini.py","pagefolio/ocr_providers/lmstudio.py","pagefolio/ocr_providers/ollama.py","pagefolio/ocr_providers/openai_provider.py","pagefolio/ocr_providers/registry.py","pagefolio/ocr_providers/runpod.py","pagefolio/ocr_providers/tesseract.py","pagefolio/page_ops.py","pagefolio/pagination.py","pagefolio/plugins.py","pagefolio/print_ops.py","pagefolio/redact_ops.py","pagefolio/settings.py","pagefolio/startup_control.py","pagefolio/startup_focus.py","pagefolio/startup_notice.py","pagefolio/startup_win32.py","pagefolio/themes.py","pagefolio/thumb_cache.py","pagefolio/toast.py","pagefolio/ui_builder.py","pagefolio/undo_store.py","pagefolio/viewer.py","plugins/page_info.py","pyproject.toml","requirements.txt","tests/__init__.py","tests/config_notice_support.py","tests/conftest.py","tests/test_batch_ocr_dialog.py","tests/test_batch_ocr_state.py","tests/test_config_notification.py","tests/test_export_images.py","tests/test_font_hardcode_guard.py","tests/test_gsd_dod.py","tests/test_imports.py","tests/test_lang_parity.py","tests/test_md_render.py","tests/test_ocr.py","tests/test_ocr_dialog_center.py","tests/test_ocr_engine.py","tests/test_ocr_fallback.py","tests/test_ocr_pipeline.py","tests/test_ocr_provider_catalog.py","tests/test_ocr_providers.py","tests/test_page_polish.py","tests/test_pagination.py","tests/test_password.py","tests/test_pdf_ops.py","tests/test_plugin_dialog_wheel.py","tests/test_plugins.py","tests/test_print.py","tests/test_prompt_templates.py","tests/test_provider_ui.py","tests/test_save_overwrite.py","tests/test_selection_invariant.py","tests/test_settings_keyguard.py","tests/test_shortcuts_dialog.py","tests/test_source_keyguard.py","tests/test_startup_control.py","tests/test_startup_focus.py","tests/test_startup_notice.py","tests/test_startup_windows.py","tests/test_thumb_cache.py","tests/test_toast.py","tests/test_undo_stress.py","tests/test_utils.py","tests/test_v150_regression.py","tests/test_viewer.py","開発履歴.md"]
covered_digest: "v3:sha256:5e1b3d4ce8b5f5eeed41dcf971459d5fc51edf2105dbbae328e9d52614470d31"
behavior_unverified: 0
overrides_applied: 0
flagged_prohibitions: 0
unclassified_edges: 4
re_verification:
  previous_status: passed
  previous_score: 23/23
  gaps_closed: []
  gaps_remaining: []
  regressions: []
decision_coverage:
  honored: 21
  total: 22
  not_honored: [D-22]
prohibitions:
  - statement: "設定障害の通知でPDF編集内容まで失われたと誤認させない"
    status: resolved
    verdict: VERIFIED
    classification: HUMAN_RESOLVED
    reason: "05-UAT.md Test 1に利用者の項目別passと記録時刻2026-10-23T18:09:21.4084125Zがある。05-01-PLANの具体的statementへの意味評価として解決。"
  - statement: "設定保存失敗を理由に作業中のPDFを捨てる操作や再起動を促さない"
    status: resolved
    verdict: VERIFIED
    classification: HUMAN_RESOLVED
    reason: "05-UAT.md Test 2に利用者の項目別passと記録時刻2026-10-23T18:09:21.4084125Zがある。05-01-PLANの具体的statementへの意味評価として解決。"
human_verification: []
deferred:
  - truth: "実配布EXE・Python各入口・DPI/UACを含む最終実機受入と版番号/README/開発履歴のリリース同期"
    addressed_in: "Phase 6 / V110-QA-02, V110-QA-03"
    evidence: "ROADMAP Phase 6 SC4/5、06-UAT-CARRYOVER。Phase 5の人手14 passは実EXE受入を代替しない。"
---

# Phase 5: 設定読込・保存失敗の通知 検証報告

**Phase Goal:** 利用者が設定の読込・保存失敗を正しく把握でき、元の設定ファイルと編集操作を失わない。  
**Verified:** 2026-10-24T11:47:08Z（2026-10-24 20:47 JST）
**Status:** passed
**Re-verification:** Yes — 2026-10-23T18:14:21Zのpassed報告後、covered files 11件が変更されfingerprintがstaleになったため差分再検証（実装gapなし）。

前回passed報告（2026-10-23T18:14:21Z）以降、covered filesのうち11件（docs/CONFIGURATION.md、pagefolio/constants.py・lang.py・ocr.py・ocr_dialog.py、tests/config_notice_support.py・conftest.py・test_config_notification.py・test_ocr.py・test_startup_windows.py、開発履歴.md）が変更されて`verification status`がstaleとなった。全変更コミットを差分で評価し、Phase 5のmust-have（設定読込・保存失敗の通知、原本保護、`config_*`日英4キー、通知FIFO/寿命）を弱める変更は無いと確認した。肯定的な実装契約23件と実装gap 0件は維持。禁止事項2件のUAT解決（Test 1・2 pass）とH01〜H14の人手受入結果も履歴として維持する。本検証はpytest/GUIを新規実行していない（並行するPhase 4検証との実Tk/OS名前空間競合を避けるため）。現行の製品・試験バイトに対する親session実測の単一プロセス全件 `2014 passed, 1 warning in 710.70s (0:11:50) / exit 0` を引用する。

**禁止事項2件は利用者の明示判断で解決、flagged 0件。** 内容不明のedge4件は未分類・未解決を維持する。DEP-05-REGRESSION・owner_missing・通知前景不一致の原因未解決と出荷不可は解除せず、DEP-05-REGRESSIONは未解決のままである。

## Goal Achievement

### Observable Truths

ROADMAPの4成功基準を先頭に置き、4 PLANの19 truthを具体化として全行照合した。番号5以降は実装上の追加条件を確認する追跡行であり、成功基準を縮小しない。Cは `tests/test_config_notification.py`、Sは `tests/test_settings_keyguard.py`、Tは `tests/test_toast.py` を指す。各挙動の試験は現在入力と同一の最新単一全件で成功したものを再利用する。

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | SC1: 初回不存在は無警告の既定値、破損・読取不能は画面構築後に認識できる | VERIFIED | settings.py:261のopen正本・4分類、app.py:149の読込とUI構築後のschedule。C:1473実App/Toast/PDF tracer、:1595分類、:1601不存在/競合、:1639初回無通知。利用者H01/H02/H03 pass |
| 2 | SC2: 各保存画面で失敗と次回非永続を認識し、偽成功に誘導されない | VERIFIED | app.py:683のbool消費・固定通知、:881の成功時だけstatus。各handler→実persistの統合試験C:408/:576/:656/:911。lang.py:9/:833の日英4キー。H02/H04/H05/H11 pass |
| 3 | SC3: 読込失敗後の自動処理と保存途中の失敗で原本を無断上書きしない | VERIFIED | app.py:766が値収集前に抑止、:683はunreadableのI/O0。settings.py:352の排他的tmp→close→replace・所有tmpだけcleanup。S:16の5障害点と:63既存tmp保持、C:1665終了分岐 |
| 4 | SC4: 連続通知を同時1件に集約し、再構築や通知で編集を妨げない | VERIFIED | app.py:521/:603/:627のApp所有FIFO・event/generation・可視時間、toast.py:86の旧状態破棄後callback。C:116寿命と:1434の100件FIFO、H04/H06/H07/H08/H13/H14 pass |
| 5 | 05-01: DEP-05未解除の条件付き実行・同種再発時停止を保持する | VERIFIED | 05-02-CHECKPOINTの2026-10-23T13:50:58Z判断、CONTEXT D-22、VALIDATION、EVIDENCE.dependencyに承認と停止条件。診断9384268と後続成功は修復主張なし。最新raw全件に同種失敗なし |
| 6 | 05-01 D-01/D-04: 破損起動後、技術詳細なし非モーダル通知で編集継続 | VERIFIED | app.py:627は固定キー→実Toast、messagebox fallbackなし。C:1473で秘密sentinel不在・grabなし・実PDF回転、H01 pass。通知はFrameで新Toplevelなし |
| 7 | 05-01 D-02/D-03: 不存在/JSON/UTF-8/root不正/OSErrorを分類して既定値起動 | VERIFIED | settings.py:308以降FileNotFoundError→missing、decode→corrupt、他例外→unreadable、必須型検査。C:1578〜1635の具体入力と結果assert |
| 8 | 05-01 D-05/D-15: 読込イベントはセッション一つ、再表示で増やさない | VERIFIED | app.py:523の登録済flagは消化/再構築でresetしない。C:1711、寿命の再表示/旧callback試験がseqとqueueをassert |
| 9 | 05-01 D-10/D-11/D-14: 終了自動保存を含め読込失敗中の原本と退避なしを維持 | VERIFIED | app.py:766が自動保存と値収集を抑止。C:1665は確認Yes/No/Documentなし・bytes不変・bakなし、C:1214は収集禁止をassert |
| 10 | 05-02 D-06/D-07/D-08: 一般設定失敗でもメモリ維持、非モーダル通知、成功表示なし | VERIFIED | app.py:881で反映→persist→rebuild、saved時のみstatus。C:1141は実replace失敗下で値/原本/通知/成功表示0、H04/H05 pass |
| 11 | 05-02 D-10/D-12/D-13/D-14/D-20: 原本/tmp保護、corruptだけ明示成功解除、unreadableは再起動まで保存禁止 | VERIFIED | settings.py:352、app.py:683/:766。S:16/:63、C:1128/:1165/:1407が実原本・同セッション権限回復後の抑止・正常再起動をassert。H11 pass |
| 12 | 05-02 D-19: 終了Noは無保存、初回失敗は保持、次の終了は保存省略 | VERIFIED | app.py:669の確認先行→save失敗returnと:766のflag判定。C:1181/:1194/:1364の資源保持・No再確認・明示成功flag解除、H09/H10 pass |
| 13 | 05-02 D-09/D-16: 失敗ごと別イベント、同文言を合併/破棄しない | VERIFIED | app.py:521がseq増分とappend、成功時clearなし。C:1434が100件のevent_id順と生成/消化一致をassert。D-21の長い待ち列は承認された仕様 |
| 14 | 05-02 D-17/D-18: 再構築/言語/カテゴリ競合で未消化保持・同時1件・入力先維持 | VERIFIED | app.py:549/:560/:603/:627/:894、ui_builder.py:187のidle配線、toast.py:86/:109。C:116の9999/10000ms・残6秒・期限とgrab同時・旧callback、実Tk可視性回帰。H04/H06/H08/H14 pass |
| 15 | 05-03 D-06〜09: 言語/plugin/LLM/shortcut/mosaic/thumbnailの全保存元が共通通知とメモリ保持 | VERIFIED | app.py:791/:826/:862、ocr_dialog.py:1044、shortcuts.py:282、redact_ops.py:257、viewer.py:162/:183→persist。C:408/:656/:911の失敗×保護状態、C:1108の非空厳密caller棚卸し |
| 16 | 05-03 D-13/D-20: corrupt明示保存とunreadable明示抑止を各入口で区別 | VERIFIED | 実persistをstub化せず低層結果を制御するC:408/:576/:911。unreadableは低層call_count0・blocked文言・値保持、corrupt成功だけ保護解除 |
| 17 | 05-03: plugin開閉/no-op rescanは無保存、同値明示Applyの再試行を許す | VERIFIED | dialogs/plugin.py:219の前後disabled比較、:241のcloseはdestroyのみ。C:454/:481/:497、利用者H12 pass |
| 18 | 05-03 D-16〜18: 一操作一保存/一失敗一イベント、言語変更/再構築後も表示 | VERIFIED | 共通owner以外の低層callはなし。C:1108のalias/Attribute/re-export監査と各handler回数assert。App queueはwidget破棄の外側に保持。H04/H07/H13 pass |
| 19 | 05-03: 内側LLM Applyは外側Cancelと独立、JSON書込一回 | VERIFIED | dialogs/settings.py:224がLLM部分のみ専用callback/App ownerへ一回委譲、一般callbackへ迂回しない。C:576/:594/:700、provider_ui/OCRの既存保存・キー非流出回帰 |
| 20 | 05-04: D-01〜21を隔離再現し実設定/PDF/prompt/pluginsを変更しない | VERIFIED（自動隔離範囲） | config_notice_support.py:57〜139が設定/base/pluginsを初期化前patch、実PDFはメモリ内。C:1239/:1251/:1265/:1291が原本hash一致・plugin load0・例外cleanup。全手動起動の終了hashは別の証拠限界として後掲 |
| 21 | 05-04: 読込失敗→保存失敗→再構築→保存成功→終了で原本/値/通知が一致 | VERIFIED | C:1309の実App・Document/Undo/Redo identity・原本bytes・4event順・残6秒・正常再読込・Undo/Redo・終了close。別に:1364/:1407/:1434のD-19/20/21状態列 |
| 22 | 05-04: 既存PDF保存/印刷retryとDocument同一性を維持 | VERIFIED | T:437の確認非反復、:538/:595/:702/:827の閉鎖/差替え後別docへ書かない回帰、印刷retry。現行fullにTとtest_pdf_opsを含む。設定側カテゴリ待機/成功dismissはC:116。H08はToast注入であり実OS印刷とは区別 |
| 23 | 05-04: 実測/未実施/未分類を分け、全件とNyquist前にPhase完了としない | VERIFIED | 最新raw status/pytestと103hash一致を独立確認。VALIDATIONはvalidated/compliant/wave0=true、REVIEW clean・disposition3fixed、SECURITY14closed。UATは利用者14passと旧metadata/終了ログ限界を区別。共有PhaseはIn Progressで正式完了を先取りしていない |

**Score:** 23/23肯定truth verified、0 present-but-behavior-unverified（前回の独立検証結果を同一入力で再利用）。禁止事項2件は別途UATの項目別passで解決した。本verifierがpytestを新規実行したとの主張はしない。

### Prohibitions — 項目別人手判断済み

| 禁止事項（05-01-PLAN frontmatter原文） | 状態 | 根拠 |
|---|---|---|
| 設定障害の通知でPDF編集内容まで失われたと誤認させない | VERIFIED / 人手判断済み | 05-UAT.md Test 1、利用者の明示pass、2026-10-23T18:09:21.4084125Z |
| 設定保存失敗を理由に作業中のPDFを捨てる操作や再起動を促さない | VERIFIED / 人手判断済み | 05-UAT.md Test 2、利用者の明示pass、同時刻 |

PLANには具体的statementがあり、今回のTest 1・2はそれぞれ同じ意味の項目を明示している。PLAN本文・EVIDENCEが「descriptor-less」と呼ぶ旧投影IDにはdescriptor/verification tierがなく、その同一性は推測で確定しない。既存H01〜H14を禁止事項のresolutionへ読み替えず、追加の項目別回答だけを使用した。tier未指定からwired test enforcementは捏造しない。

### Required Artifacts

CLI `query verify.artifacts <各PLAN>` は各exit0、4/4・4/4・3/3・5/5（宣言枠16/16）。存在判定に加え以下の実内容・使用先を確認した。

| Artifact | Expected | Status | Details |
|---|---|---|---|
| pagefolio/settings.py | 分類API/互換dict/原子的bool保存 | VERIFIED | 実open/json.load、必須型検査、機密除外、排他的tmpと実os.replace。Appが結果を消費 |
| pagefolio/app.py | 保存/保護/終了/通知owner | VERIFIED | 実UI初期化と全保存handler、FIFO/世代/可視性/終了へ接続 |
| pagefolio/toast.py | 任意retry・期限・終了理由・idle | VERIFIED | 実Frame/Label/Buttonとafter、dispose/old callback guard。UIBuilderが生成 |
| pagefolio/ui_builder.py / lang.py | Toast再配線/日英固定文 | VERIFIED | 毎回新managerへon_idle、4キーとも日英。設定通知はmodal fallback不使用 |
| pagefolio/dialogs/settings.py | LLM単一owner/外側modal維持 | VERIFIED | 製品open_settingsがownerを注入。LLM/Shortcuts自身のDestroyだけで外側grab復元 |
| その他6保存元ファイル | 結果共通化/操作継続 | VERIFIED | dialogs/plugin.py・shortcuts.py・ocr_dialog.py・redact_ops.py・viewer.pyとappの該当handlerを追跡 |
| tests/test_config_notification.py | 読込・保存・寿命・全入口・複合・隔離 | VERIFIED | 13 Testクラス、52 test関数（param展開前）。実App/実Toastと純状態試験を区別 |
| tests/config_notice_support.py | 恒久隔離/cleanup | VERIFIED | 一時領域・3resolver・限定障害注入・finally原本hash。pytest/harnessの双方が利用 |
| 05-NOTICE-HARNESS.py | 隔離人手入口 | VERIFIED | 祖先探索→恒久helper、実App/ToastとメモリPDF。製品入口への組込なし |
| 05-EVIDENCE.json | command/exit/runtime/hash/限界 | VERIFIED（記録範囲） | latest_automated_verificationとraw一致。旧single_full_current/nyquist fieldsは過去snapshotで、最新版と区別 |
| docs/CONFIGURATION.md / 開発履歴.md | 利用者説明/未リリース記録 | VERIFIED | 読込保護、明示/自動保存、失敗時の値、終了契約、FIFOを記載。版同期はPhase6 |

### Key Link Verification

CLI `query verify.key-links <各PLAN>` は各exit0、2/2・2/2・3/3・2/2（9/9）。パターン一致だけでなく呼出しと戻り値・callbackも追跡した。

| From | To | Via | Status | Details |
|---|---|---|---|---|
| app.__init__ | settings._load_settings_result | 結果status/settings | WIRED | 状態初期化後、UI/menubar後にafter_idle |
| App通知owner | ToastManager | show/on_close | WIRED | event_id+generation一致だけ消化、固定文言 |
| app._persist_settings | settings._save_settings | bool結果 | WIRED | 失敗event生成、明示成功だけ保護解除 |
| UIBuilder._build_ui | App queue | on_idle=_schedule_config_notice | WIRED | rebuild前dispose→新manager→queue再表示 |
| SettingsDialog.on_apply | App._apply_llm_settings_live | _on_llm_apply | WIRED | 外側未適用値と独立した一回保存 |
| OCRDialog | App | app._persist_settings | WIRED | 成否後もprovider/prompt/UI更新を続行 |
| ViewerMixin | App | self._persist_settings | WIRED | 倍率/件数の各実handler→再描画 |
| TestConfigAcceptance | 実App | helper経由の保存/再構築/終了 | WIRED | 隔離原本とDocument/履歴identityをassert |
| VALIDATION | EVIDENCE | 実測表とlatest後続節 | WIRED | 旧結果を残し修正後1797/14UATを追記 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| 読込通知 | load_result.status→message_key→_msg_var | 実設定open/json.load/例外分類 | yes | FLOWING |
| 保存通知 | saved→config_save_failed/blocked | 実tmp書込/close/replace、または原本保護状態 | yes | FLOWING |
| 設定画面/各操作 | app.settingsと各var/binding | UI操作→実handler→共通owner→メモリ反映 | yes | FLOWING |
| 再表示 | event_id/remaining_ms/現在lang | App deque・monotonic可視経過・grab/root状態 | yes | FLOWING |

LANGの固定通知文は実I/O結果を安全に説明する仕様であり、データソース代替の静的stubではない。未消化deque初期値の空も後続enqueue経路があるためstubではない。API/DBは本Phaseに存在しない。

### Behavioral Spot-Checks

並行するPhase 4検証との競合回避と親の指示に従い、サーバー/GUI/pytestを新規起動しなかった（静的チェックのみ実行）。必要な状態遷移を確認する既存named test本文を読み、含まれる最新fullの生ログと入力hashを照合した。

| Behavior | Command / evidence | Result | Status |
|---|---|---|---|
| 読込→実Toast→PDF編集、保存失敗→原本保持 | C::TestLoadTracer::test_corrupt_settings_show_one_real_toast_and_keep_pdf_editable、S::TestAtomicSettingsWrite::test_failure_preserves_original_and_cleans_owned_tmp | 最新full内で成功。名前だけでなくassertを読取 | PASS（既存実走再利用） |
| 終了保留/明示回復/再構築/FIFO | C::TestConfigAcceptanceの4状態列、TestNotificationLifecycle | 同上、実資源とfake clockを区別 | PASS（既存実走再利用） |
| 修正CR-01/02 | C::TestToolSaveOrigins::test_real_shortcuts_close_restores_outer_grab、TestNotificationLifecycle::test_real_root_visibility_suspends_same_event | 現行全件2014件に含まれ成功、H13/H14もpass | PASS（親session実走を引用） |
| 現行単一全件 | `.venv/Scripts/python.exe -m pytest -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_focus_proof_final` | raw pytest.txt=1797 passed/1 warning/266.81s、status.json exit0、runner267.655s。selectorなし、100%完走 | PASS |
| 現行単一全件（再検証時点） | 親sessionの`pytest`単一プロセス全件（生ログ: scratchpad `full_pytest_ab.txt`、最終更新20:39:42 JST） | `2014 passed, 1 warning in 710.70s (0:11:50)` / exit 0。実行開始（約20:28）は最終の製品/試験ファイル更新（20:26:52 JST）より後で、対象ファイルはgit上も未変更（clean）のため現行バイトに対する実走 | PASS（本検証は未実行・引用） |
| 検証入力同一性 | verifierのpython hashlib照合、05-focus-proof-inputs.json | 103件、missing/hash不一致0 | PASS（本検証で実行） |
| 品質 | 最新EVIDENCE.review_followupと05-reviewfix-quality.json | Ruff→Python限定format109 unchanged→Ruff→AST→diff成功。修正後検証として提出済み | PASS（既存実走再利用） |

最新1797件と修正前1789件/278.95秒、修正直後1797件/266.50秒、runner時間を区別した。診断423件の原本/コピー/manifest一致は親の通常権限照合結果であり、本verifierの独立原本再hashとは称さない。最新copy manifestとstatusの423記録は読取確認した。

Phase4は04-VERIFICATIONの21truth/参照ファイルを読み、Appの終了確認と資源保持に関する変更箇所を回帰確認した。最新全件に `test_gsd_dod.py / test_startup_control.py / test_startup_focus.py / test_startup_notice.py / test_startup_windows.py` を含む。これらの現行hashも103一致に含まれる。Phase4の実EXE/別session等not-runは継承し、今回の成功で解除しない。

### 再検証の差分評価（stale 11ファイル）

前回報告の`verified`（2026-10-23T18:14:21Z = 2026-10-24 03:14 JST）以降のコミットを`git log`/`git diff 98dd70a^ HEAD`で列挙し、covered filesへの変更を全件確認した。`pagefolio/app.py`・`settings.py`・`toast.py`・`ui_builder.py`・`dialogs/*`・`viewer.py`・`redact_ops.py`は変更なし（Phase 5の通知owner・原子的保存・保存元の実装はバイト不変）。

| ファイル | 変更コミット | 内容 | Phase 5 must-haveへの影響 |
|---|---|---|---|
| pagefolio/lang.py | 52258de/7fb41a2 | `ocr_err_connection`（日英）を`{provider}`/接続先表示のプロバイダ中立文言へ変更。日英キー集合は一致（差分0）、`config_load_corrupt`/`config_load_unreadable`/`config_save_failed`/`config_save_blocked_unreadable`は日英とも非空で不変 | なし（`config_*`4キー不変、パリティ維持） |
| pagefolio/ocr_dialog.py | 52258de/7fb41a2 | 接続先を有効スナップショットから`resolve_local_endpoint`で解決、LLM適用後に`_active_ocr_settings`を破棄、`_refresh_provider_dependent_ui`をprovider再生成のtry/except外側・後へ移動。`saved = self.app._persist_settings()`は保存直後のまま、失敗しても後続のprovider/prompt/UI更新を続行する構造を維持（Truth 15/19・Key Link「OCRDialog→App」） | なし（保存owner経由と失敗後続行は不変。UI更新順の改善のみ） |
| pagefolio/ocr.py | 52258de | `DEFAULT_OLLAMA_URL`と`resolve_local_endpoint`の追加、`_start_ocr`の接続先決定の変更 | なし（設定保存/通知経路に触れない） |
| pagefolio/constants.py | c09baea | `APP_VERSION`を`v1.10.0`へ同期（Phase 6 SC5の範囲） | なし（Phase 5はバージョン同期を明示的にPhase 6へ繰延べ済み） |
| docs/CONFIGURATION.md | 06-01/06-02 | 配布版サンプルプロンプトの説明を追記 | なし（読込保護・明示/自動保存・終了契約・FIFOの記述は不変） |
| tests/config_notice_support.py / test_config_notification.py | 98dd70a/07244dc | 設定通知試験の`TkinterDnD.Tk()`を`tk.Tk()`＋`_setup_file_drop`無効化へ置換（ネイティブD&D拡張ロードという無関係な環境要因から分離） | なし（assert・原本hash・FIFO・Document identity等の検証本体は不変。差分は初期化方式のみで、`pagefolio.app._setup_file_drop`はapp.py:16/921に実在。アサート削除なし）。試験内行番号が最大4行ずれたため、前掲Evidenceの`C:`行番号は±4行の目安 |
| tests/conftest.py | 89582df | `pytest_runtest_teardown`でメインスレッド`gc.collect()`を追加（Tclリーク警告の誤帰属防止） | なし（試験を除外・skipしない。`tests/test_gc_barrier_guard.py`が構造を固定） |
| tests/test_ocr.py | 52258de | `_on_run`の接続先解決変更に合わせ、`lm_studio_model`をsettingsにも設定 | なし（OCR接続先の試験前提の追従） |
| tests/test_startup_windows.py | 3925d5f/3e56452 | Phase 4の前景監査診断ハーネス追加と、引継ぎ敗者`expired`を条件付き（5000〜6000ms・勝者ready差≥4500ms）で許容、`takeover-slow`回帰追加 | なし（Phase 4領域。製品コードと5000ms期限契約は不変。Phase 4のnot-run継承は変わらない） |
| 開発履歴.md | 複数 | 履歴追記 | なし |

**判定: 回帰・弱体化なし。** 追加された試験（`test_ocr_dialog_provider_refresh.py`・`test_ocr_local_endpoint.py`・`test_release_*`等）は全件に含まれ成功している。`ruff check pagefolio tests`は`All checks passed!`（静的、本検証で実行）。`APP_VERSION`は`v1.10.0`。

**未コミット内容の注記:** coveredに含まれる`開発履歴.md`と`requirements.txt`は作業ツリーで未コミット変更（他作業由来）を含むため、`covered_digest`にはその未コミット内容が含まれる。`05-CONTEXT.md`は他作業でdirtyだがcovered外であり、編集していない。

### Probe Execution

N/A。scriptsディレクトリとprobe-*.shの宣言はなく、Phaseは設定UI/I/Oでmigration/toolingではない。PLAN/SUMMARYに記載されたedge-probe4件はbehavior/command/descriptorのないメタデータで、実行可能なprobeを特定できない。`unclassified/unresolved`、verification/resolution=nullを維持し、MISSING_PROBEや実行PASSを捏造しない。

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| V110-CFG-01 | 05-01/04 | 不存在無通知、読込失敗を画面構築後認識 | SATISFIED | Truth1/6/7/8、分類と実App tracer、H01/H02/H03 |
| V110-CFG-02 | 05-02/03/04 | 全保存画面の失敗/次回非永続、偽成功なし | SATISFIED | Truth2/10/12/15〜19、全10操作群の実handler試験、H02/H04/H05/H09/H10/H11 |
| V110-CFG-03 | 05-01/02/03/04 | 自動上書き/保存途中破壊を防ぐ | SATISFIED | Truth3/9/11/16/20/21、bytes・tmp・I/O0・正常再読込assert |
| V110-CFG-04 | 05-01/02/03/04 | 通知連打/再構築消失で編集を阻害しない | SATISFIED | Truth4/13/14/18/21/22、FIFO/世代/可視性/外側grab、H04/H06/H07/H08/H13/H14 |

REQUIREMENTSのPhase5割当は上記4IDのみ、全PLANの和集合と一致しORPHANED=0。禁止事項の明示人手判断は今回のUATで解決した。Phase検証の合格と出荷判断は別である。

### Decision Coverage (warning)

CLI実測: total22 / honored21 / not_honored=[D-22]、blocking=false。

1 decision(s) not found in shipped artifacts: **D-22**（条件付き実装再開）。これはsoft warningで判定を変更しない。手動追跡では05-02-CHECKPOINTの再開承認、EVIDENCE.dependency、SUMMARYの9件×3回/1680件成功/未解除/再発時停止を確認した。文言一致heuristicの結果21/22は改変せず残す。

### Test Quality Audit

| Test File | Linked Req | Active test関数数（param前） | Skipped | Circular | Assertion Level | Verdict |
|---|---|---:|---|---|---|---|
| test_config_notification.py | CFG01〜04 | 52 | 0 | 検出なし | 実bytes/値/保存回数/状態列/identity | 十分 |
| test_settings_keyguard.py | CFG01/03 | 22 | 0 | 検出なし | 故障5点・所有tmp・機密/入力非破壊 | 十分 |
| test_toast.py | CFG02/04・既存retry | 37 | 最新fullでskip0 | 検出なし | 実widget・timer・callback・bound_doc | 十分 |
| test_provider_ui.py / test_ocr.py / test_pagination.py | CFG02/03/04 | 223 / 165 / 84 | 0 | 検出なし | 値/呼出回数/OCR状態/選択・再描画 | 十分 |

T冒頭の既存`pytest.importorskip("tkinter")`はTk未導入時の条件分岐で、今回のWindows全件ではskipされていない。skip decoratorなし。原本expected bytesは試験が用意した独立入力であり、被試験関数で生成した期待値ではない。保存用temporary fixture書込も循環oracleではない。外部実装とのparity要件はない。

**反証確認:** 「全入口」は単なる呼出数テストではなく、alias/Attribute/re-exportを解決し期待caller非空をassertしている。「入力先verified」はNoneや非Entryを区別する最終コードを確認し、自動focusの取得不能を人手passへ転用していない。未捕捉error pathとして手動harnessの全終了hashログは実証されておらず、後掲制限に残す。実装を部分充足と断定する追加根拠は検出しなかった。

### Anti-Patterns Found

| File | Line / location | Pattern | Severity | Impact |
|---|---|---|---|---|
| 05-EVIDENCE.json / 05-VALIDATION.md / 05-UAT.md | 過去snapshot/旧本文 | nyquist draft等の旧値と最新validated/1797が併存 | Info | 時点を区別すれば実測と矛盾しない。古い値を現行合否へ流用しない |
| tests/test_provider_ui.py | 480 | 文字列中の`$X.XXX` | Info | 料金表示regexの説明であり未参照のXXX債務コメントではない |
| pagefolio/viewer.py | 遅延描画部 | placeholder/空初期状態 | Info | 実renderが後続で埋める既存表示部品。stub不成立 |
| 05-UI-REVIEW.md | V-01/S-01 | ✕の説明、固定幅320pxの境界 | Advisory | 静的UI推奨で実クリッピング等の欠陥は未実証。Phase6実画面/DPI確認へ残す |

前回の独立検証では、変更実装と要件リンク試験に未参照TBD/FIXME/XXXの債務コメント、空handler、console-only、ダミーデータ固定を検出しなかった。BLOCKER=0。今回の差分では新たな実装変更や反証を認めず、同一入力の結果を再利用した。UI推奨のAdvisoryは当該監査の性質を示すもので、今回の新規blockerではない。

### Advisory (New Scope, Unevidenced)

なし。今回の差分再検証で、新たな未証明のStep 7 blockerは見つかっていない。

### 完了した人手判断（履歴）

既存H01〜H12は利用者の2026-10-24明示回答による12pass、修正7bbb06c後H13/H14は別の2pass。修正前/後を区別し、その14件を再要求しない。05-04のdeferred human-checkはこの証拠で満たされている。

前回のhuman_neededを生んだ禁止事項1・2は、05-UAT.md末尾のTest 1・2として項目別に利用者がpassを回答した（両記録時刻2026-10-23T18:09:21.4084125Z）。これにより現在のhuman_verificationは空。旧投影IDと内容不明のedge4件に解決済みの意味を付与しない。

### Deferred Items / 残存制約

- 実配布EXE・各起動経路・DPI/UAC・Phase4移管UATはROADMAP Phase6 SC4と06-UAT-CARRYOVER。全必須passまでリリース停止。APP_VERSION/README同期はSC5。
- Phase5の禁止2件は本Phaseの項目別UATで解決した。Phase4の禁止3件の移管記録をPhase5へ流用していない。
- DEP-05（DEP-05-REGRESSIONは未解決のまま）・owner_missing・通知前景不一致は原因未確定。同種再発時は実装/後続実行/commit停止と最初の失敗保存を維持。今回の成功を修復や出荷承認としない。
- Tcl別thread解放RuntimeWarningは05-03-deferred-items.mdのopenを維持。最新warning1件はPyMuPDF ByteString非推奨であり、未観測を原因解決としない。
- 手動harness全起動の正常終了・原本hash照合結果はstdout/stderrから確認不能。自動TestScenarioIsolationの原本hash/実plugin load0/例外cleanupの証明と区別する。残存processの強制終了や実設定操作は実施していない。
- UI静的22/24は独立visual合格ではない。固定幅/閉鎖操作の意味・テーマ/DPIはPhase6最終実画面受入に留意。

### 判定

実装上の具体的な不足を示すgapsは0件、全4要件の肯定的契約23/23は前回の独立検証で実証済み。保留された禁止事項2件は今回の項目別UAT回答で解決し、現在のhuman_verificationは空。よって総合statusは **passed**。旧投影IDとedge4件は内容不明のままであり、この判定によって解決済みとはしない。DEP-05等の停止条件とPhase6の実機受入・出荷停止も維持する。

covered_files/covered_digestは、前回と同じ122件の集合を入力した `query verification.fingerprint .planning/phases/05-config-notification <既存covered_files>` のexit0出力をそのまま転記した（PLAN/SUMMARY自動追加）。手計算hashや旧digest流用なし。実装/共有文書の編集・commitは行っていない。

---

_Verifier: gsd-verifier_

