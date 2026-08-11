---
phase: 01
slug: safety-rollback
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-11
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Phase 1（保存・編集・設定の安全性是正）の 7 プラン（01-01〜01-07）すべてが PLAN 時点で
`<threat_model>` を持つため、register_authored_at_plan_time = true。ASVS L1 / block_on = high の
基準で、各脅威の緩和策が実装に存在するかを検証した（新規脅威スキャンは行っていない）。

本フェーズはネットワーク境界・認証境界を持たないローカル文書操作であり、現実的な脅威は
**ユーザー文書のデータ完全性（サイレントな破損・喪失）**と**暗号化 PDF の平文書き出し**、
**OCR OFF 設定を迂回したクラウド送信**の 3 系統に集中する。

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| アプリ内 Document → ファイルシステム | 暗号化 PDF が平文としてディスクへ書き出され得る境界。`Document.save()` / `tobytes()` の `encryption` 引数が唯一の制御点 | PDF 本文（機密の可能性あり） |
| ユーザーの明示操作 → 暗号化状態の変更 | 「🔒 パスワード → 設定 / 解除」のみが暗号化状態を変えてよい。通常保存はこの境界を越えない | 暗号化フラグ・パスワード |
| UI 表示（`pdf_has_password`）→ 実ファイルの暗号化状態 | 表示と実態の乖離はユーザーの誤認（未保護ファイルを保護済みと誤解）を招く | 表示状態 |
| ローカルのページ画像 → クラウド OCR API（Claude / Gemini / RunPod） | base64 化したページ画像が https で外部送信される境界。OCR OFF はこの境界を完全に閉じる設定 | PDF ページ画像 |
| 設定値 `ocr_provider` → OCRProvider インスタンス生成 | `build_provider` が唯一の正規ファクトリであるべき境界。迂回分岐が抜け道になる | プロバイダ選択値 |
| ダイアログ入力欄 → 作業ディレクトリの外部 md ファイル | ユーザーが外部エディタで管理するプロンプト資産への書き込み境界。Apply 押下のみが越えてよい | プロンプト本文 |
| ダイアログ入力欄 → `pagefolio_settings.json` | API キーを含む LLM 設定の永続化境界。`_SENSITIVE_KEYS` ガードが唯一の防波堤 | API キー（機密） |
| 編集・復元操作 → `fitz.Document` のページ構成 | 中間失敗した操作がページ構成へ部分的に残ると、ユーザーは気づかず破損状態を保存する | PDF ページ内容 |
| Undo スタック → 復元操作 | スタック上の state はユーザーの唯一の復旧手段。失われた瞬間に復旧不能になる | PDF ページ内容 |
| `UndoBlobStore` の tempfile → ファイルシステム | PDF ページ内容が一時ファイルとしてディスク上に置かれる。dispose 漏れは内容の残置になる | PDF ページ内容 |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Information Disclosure | `file_ops.py:_save_as` / `_overwrite_current_file` / `_save_compressed` | high | mitigate | `file_ops.py:1117` `save_kwargs.setdefault("encryption", fitz.PDF_ENCRYPT_KEEP)`、`:1155`（incremental）・`:1184`（フォールバック）・`:1244`（compressed）で明示付与。`tests/test_password.py::TestSavePathsKeepEncryption` 6 件が保存先を開き直して検証 | closed |
| T-01-02 | Tampering | `file_ops.py:_overwrite_current_file` の kwargs 既定化 | medium | mitigate | 単純代入ではなく `setdefault`（`:1117`）。`test_set_password_kwargs_not_overridden` / `test_remove_password_kwargs_not_overridden` で明示指定の非上書きを機械検証 | closed |
| T-01-03 | Spoofing | UI 表示 `pdf_has_password` | medium | mitigate | `file_ops.py:60 derive_pdf_has_password()` による保存 kwargs からの単一地点導出（`:1127` で呼び出し）。`TestDerivePdfHasPassword` + 実ファイル `needs_pass` 照合テスト | closed |
| T-01-04 | Denial of Service | `_overwrite_current_file` の tmp → `os.replace` 経路 | low | accept | 既存実装が失敗時にメモリ上 bytes から Document を復元し例外を再送出する設計。本フェーズは制御フロー未変更。ディスク満杯等は OS 依存で受容（→ AR-01） | closed |
| T-01-05 | Information Disclosure | `ocr.py:build_provider` の `("lmstudio", "", "off")` 同列扱い | high | mitigate | `ocr.py:454` `if name == "off": raise OCRDisabledError()` をプラグイン分岐より前段に配置し、生成そのものを構造的に不可能化。`TestOCRDisabledGuard::test_build_provider_off_raises_ocr_disabled` | closed |
| T-01-06 | Information Disclosure | `ocr_dialog.py:_apply_llm_settings` / `_on_run` の provider 直接構築 | high | mitigate | `ocr_dialog.py:1083`（`_apply_llm_settings`）・`:1363`（`_on_run`）で `off` を文字列比較のみで中断し provider を差し替えない。`test_ocr_dialog_apply_llm_settings_off_aborts` / `test_ocr_dialog_on_run_off_aborts` | closed |
| T-01-07 | Elevation of Privilege | プラグイン登録プロバイダ経由の OFF 迂回 | medium | mitigate | `off` 判定がプラグイン分岐の前段（`ocr.py:454`）にあり到達不能。独自生成経路は `plugins.py` の `_BUILTIN_PROVIDER_NAMES` ホワイトリストで既存ガード済み | closed |
| T-01-08 | Denial of Service | メニュー `entryconfig` 失敗によるアプリ停止 | low | accept | `app.py:356 _update_batch_menu_state` は `try/except Exception as e:` + `logger.debug` 防御を持ち、Tk 未初期化環境でも例外を伝播しない（→ AR-02） | closed |
| T-01-09 | Tampering | `dialogs/llm_config/sections.py:_on_template_change` の即時書き込み | medium | mitigate | `sections.py` から `save_prompt_file` 呼び出しを撤去済み（grep で `sections.py` に該当ゼロ）。書き込みは `dialog.py:466-469`（`_apply`）の 1 経路のみ。`TestApplyOnlyPromptFileWrite` 5 件が実ファイル読み取りで検証 | closed |
| T-01-10 | Information Disclosure | LLM 設定の永続化経路（`_SENSITIVE_KEYS` ガード） | high | mitigate | `settings.py:29 _SENSITIVE_KEYS = sensitive_keys()` / `:310-317` で保存時に除外。本フェーズは settings 保存経路を未変更。`tests/test_settings_keyguard.py` / `tests/test_source_keyguard.py` green を verify ゲートに含めた | closed |
| T-01-11 | Tampering | 作業ディレクトリへの md ファイル自動生成 | low | mitigate | `dialog.py:466` / `:468` の `prompt_file_exists` ガードを維持（D-17）。`test_apply_does_not_create_missing_prompt_files` で tmp_path 配下に新規作成されないことを検証 | closed |
| T-01-12 | Repudiation | 未保存差分の無警告破棄 | medium | mitigate | `sections.py:1156 _has_unsaved_template_changes` からファイル存在分岐を削除（D-18）し、`:1214` で常に確認ダイアログ。`test_selected_template_edit_warns_without_prompt_files` | closed |
| T-01-13 | Tampering | `file_ops.py:_undo` / `_redo` の無防備な `_restore_state` 呼び出し | high | mitigate | `file_ops.py:307-378` で `PartialRestoreError` / 一般例外を捕捉し `_push_evicting` でスタックへ戻し `messagebox.showerror` でブロッキング通知（D-13）。`test_undo_restore_failure_returns_state_to_stack` / `test_undo_retry_after_failure_uses_same_state` | closed |
| T-01-14 | Tampering | `page_ops.py:_do_insert` の無警告部分適用 | high | mitigate | `page_ops.py:808` で挿入済みページ数を追跡し `delete_page(insert_at)` で巻き戻し、巻き戻し不能時のみ残存ページ数を明示した警告（D-08/D-10）。`TestInsertRollback` 5 件 | closed |
| T-01-15 | Information Disclosure | `UndoBlobStore` の tempfile（PDF ページ内容） | medium | mitigate | Undo スタック直接 pop を廃し `_dispose_state`（`file_ops.py:124`）経由へ統一（D-14）。復元失敗時は `_dispose_state` を呼ばず二重解放を回避。`tests/test_undo_stress.py::TestBlobLeakDetection` | closed |
| T-01-16 | Denial of Service | 挿入元 Document のファイルハンドルリーク | medium | mitigate | `page_ops.py:786-787` の `finally: src.close()` で close 保証（D-09）。`test_insert_failure_closes_source_documents` が全 Document の `is_closed` を検証 | closed |
| T-01-17 | Tampering | 巻き戻し時の `delete_page` インデックス誤りによる既存ページ削除 | high | mitigate | 同一インデックス `insert_at` を実挿入数だけ削除する既存パターンを踏襲（`page_ops.py:808`）。ループ変数加算なし。digest 列比較テストで検証 | closed |
| T-01-18a | Tampering | `file_ops.py:_restore_state` の duplicate / merge / merge_resize 逆デルタ（01-05） | medium | mitigate | `TestAllOpsUndoRedoRoundtrip`（`tests/test_pdf_ops.py:946`）で 4 手往復を 3 op へ水平展開し digest 列（順序込み）比較 | closed |
| T-01-18b | Tampering | `file_ops.py:_apply_inverse` が縮小 `remaining_state` から次段逆デルタを構築（01-06） | critical | mitigate | mutation ループ内で適用済み分を蓄積する `_pending_inverse` / `_merge_pending_inverse`（`file_ops.py:154-166`）方式へ変更。Evidence 3 / 4 を 5 手往復テスト化（`TestUndoRedoRestoreFailure` 8 件新設） | closed |
| T-01-19a | Tampering | `merge_resize` のリサイズによるページ寸法の丸め誤差波及（01-05） | low | mitigate | `test_merge_resize_preserves_original_page_dimensions`（`tests/test_pdf_ops.py:1599`）が MediaBox 幅・高さを `pytest.approx` で検証 | closed |
| T-01-19b | Tampering | 内部フラグ `_merged_page_deleted` の次段 state への持ち越し（01-06） | high | mitigate | `file_ops.py:876` `d.pop("_merged_page_deleted", None)` で逆デルタ確定時に共有 dict から除去。`test_merge_resize_undo_partial_retry_then_redo_undo_roundtrip` | closed |
| T-01-20a | Repudiation | D-12 棚卸しの未記録（01-05） | low | mitigate | `01-05-SUMMARY.md`「D-12 棚卸し」節に `_save_undo` 全 16 呼び出し箇所（page_ops.py 13 / dnd.py 2 / redact_ops.py 1）を表として記録し、水平展開を次マイルストーン候補として明示 | closed |
| T-01-20b | Information Disclosure | 蓄積逆デルタ用 Blob の解放漏れ（01-06） | medium | mitigate | `_dispose_state` を `_pending_inverse` まで走査するよう拡張（`file_ops.py:134-137`）。`_merge_pending_inverse` の pop（`:166`）で所有権移譲し二重解放も防止。`test_pending_inverse_blobs_released_on_stack_clear` / `test_partial_retry_roundtrip_no_double_release` | closed |
| T-01-21a | Denial of Service | フルスイート実行時の Tcl/Tk フレーキー ERROR（01-05） | low | accept | STATE.md 記録済みの既知事象。Phase 3（V190-QA-01）が切り分け・修復を引き取る（→ AR-03） | closed |
| T-01-21b | Denial of Service | 逆デルタ蓄積による Undo スタックのメモリ増（01-06） | low | accept | 蓄積は 1 復元操作の対象ページ数が上限で、合流後は 1 世代分へ収束。`MAX_UNDO = 20` + `UndoBlobStore` の 64KiB 以上ディスク退避で従来と同上限。`test_memory_and_blob_invariants` の既存上限アサーションを verify ゲートに含めた（→ AR-04） | closed |
| T-01-22 | Tampering | `file_ops.py:_restore_state` の `page_edit` 分岐 — `delete_page` 成功後の `insert_pdf` 失敗で `captured` を無条件解放しページ内容が恒久喪失（CR-02） | critical | mitigate | option-b で mutation 順序を反転（`insert_pdf` → `delete_page`）し、doc がページ内容を失う瞬間を構造的に排除。ロールバック不能時のみ `_page_edit_inserted`（`file_ops.py:604-613`）を立てる。`test_page_edit_insert_failure_rolls_back_and_retry_preserves_neighbors` が Evidence B 再現手順で検証 | closed |
| T-01-23 | Tampering | 再試行時のインデックスずれによる隣接ページの巻き添え削除 | critical | mitigate | `_page_edit_inserted` マーカー（`file_ops.py:198-206`, `:613`）で再試行が常に整合したインデックス基準で動く。digest 列一致による回帰テストで固定 | closed |
| T-01-24 | Repudiation | 再試行が「エラーなく成功したように見える」のに doc が壊れている（通知ゼロ） | high | mitigate | `PartialRestoreError.content_at_risk`（`file_ops.py:32-41`）を導入し、`:314-319`（undo）・`:357-361`（redo）で `err_undo/redo_restore_failed_content_at_risk`（`lang.py:252-257` ja / `:1006-` en）を `messagebox.showerror` でブロッキング表示。`test_page_edit_unrecoverable_failure_warns_and_preserves_all_pages` が通知キーを assert | closed |
| T-01-25 | Tampering | `insert`（base op）の削除ループ中途失敗 → 再試行での既存ページ過剰削除（WR-05） | high | mitigate | 削除の直前に `_capture_page_blob` を呼び `deleted` を追跡、残り件数のみの `remaining_data = [insert_at, num - deleted]` を `_restore_partial_error` で返す（`file_ops.py:711-737` 付近）。`test_insert_partial_failure_preserves_remaining_and_retry_completes` | closed |
| T-01-26 | Information Disclosure | 保持した復旧用 Blob の解放漏れによるページ内容の残置 | medium | mitigate | `_dispose_state` の走査拡張 + pop による所有権移譲。`test_insert_partial_retry_blobs_released_on_stack_clear` / `test_page_edit_unrecoverable_failure_blobs_released_on_clear` が `_clear_undo_stacks` 後の解放と二重解放ゼロを機械検証 | closed |
| T-01-27 | Denial of Service | 復元ループの例外経路で一時 `fitz.Document` が未クローズのまま積み上がる（WR-04） | medium | mitigate | 対象 7 箇所を `try/finally: tmp.close()` で保護（`file_ops.py` の `finally:` 8 箇所）。`TestTempDocumentCloseGuard::test_temp_documents_are_finally_closed_guard`（`tests/test_pdf_ops.py:2003`）が AST 走査で恒久固定、`test_restore_failure_closes_temp_document` が実行時裏取り | closed |
| T-01-28 | Denial of Service | 復旧用 Blob 保持による Undo スタックのメモリ / ディスク増 | low | accept | 保持は「復旧不能な中間失敗が起きたページ」のみで再試行完了時に解放。`MAX_UNDO = 20` + 64KiB 以上ディスク退避で従来と同上限（→ AR-05） | closed |
| T-01-SC | Tampering | npm / pip / cargo installs（サプライチェーン） | low | accept | 本フェーズは新規パッケージを一切導入しない。`01-RESEARCH.md`「Package Legitimacy Audit」＝対象パッケージなし・`[SLOP]` / `[SUS]` / `[ASSUMED]` いずれもゼロ。`requirements.txt` / `pyproject.toml` は未変更（→ AR-06） | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

> **ID 衝突の注記:** 01-05 と 01-06 の PLAN が同じ `T-01-18`〜`T-01-21` を独立に採番していたため、
> 本レジスタでは 01-05 由来を `a`、01-06 由来を `b` の接尾辞で区別している。

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-04 | `_overwrite_current_file` の tmp → `os.replace` 経路の失敗（ディスク満杯等）は OS 依存の外部要因。既存実装がメモリ上 bytes から Document を復元して例外を再送出する設計を維持しており、データ喪失には至らない | Phase 1 プランナー（01-01-PLAN.md） | 2026-08-11 |
| AR-02 | T-01-08 | メニュー `entryconfig` の失敗は `try/except Exception` + `logger.debug` で吸収され、アプリ停止に至らない。Tk 未初期化環境（テスト等）でも安全 | Phase 1 プランナー（01-02-PLAN.md） | 2026-08-11 |
| AR-03 | T-01-21a | フルスイート実行時のテストインフラ由来の不安定性。製品コードは A/B 検証で無実と確定済み（01-07-SUMMARY.md「Issues Encountered」）。Phase 3（V190-QA-01 テスト安定化）が引き取る。当面の運用は分割実行で 1184 件 green を確認 | ユーザー（01-UAT.md Test 2 で pass 判断） | 2026-08-11 |
| AR-04 | T-01-21b | 逆デルタ蓄積のメモリ増は 1 復元操作の対象ページ数が上限。`MAX_UNDO = 20` と `UndoBlobStore` の 64KiB 以上ディスク退避により従来と同じ上限に収まる | Phase 1 プランナー（01-06-PLAN.md） | 2026-08-11 |
| AR-05 | T-01-28 | 復旧用 Blob 保持は復旧不能な中間失敗が起きたページのみ。再試行完了時に解放され、既存の上限機構内に収まる | Phase 1 プランナー（01-07-PLAN.md） | 2026-08-11 |
| AR-06 | T-01-SC | 本フェーズは新規外部パッケージを一切導入せず、`requirements.txt` / `pyproject.toml` を変更していないため、サプライチェーン面の新規曝露はない | Phase 1 プランナー（全 7 プラン共通） | 2026-08-11 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-11 | 32 | 32 | 0 | /gsd-secure-phase 01（ASVS L1・grep-depth 検証） |

**検証手法（ASVS L1）:** 7 プランの `<threat_model>` から 32 件の脅威レジスタを構築し
（`register_authored_at_plan_time: true`）、`mitigate` 26 件について実装ファイル内に緩和策の
コードが存在することを行番号レベルで確認、`accept` 6 件について受容理由が文書化されている
ことを確認した。新規脅威スキャンは実施していない（レジスタは PLAN 時点で完備の前提）。

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-11
