---
phase: 1
slug: safety-rollback
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-10
validated: 2026-08-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 本ファイルは 2026-08-11 の `/gsd-validate-phase 01`（retroactive audit）で
> 実測値に基づき再構成した。全数値はコマンド実行の実測であり転記ではない。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest（`pytest-*` プラグイン追加なし・標準 unittest スタイルの class ベース） |
| **Config file** | `pyproject.toml`（`[tool.pytest.ini_options]`）+ `tests/conftest.py`（共有フィクスチャ） |
| **Quick run command** | `python -m pytest tests/test_password.py tests/test_ocr.py tests/test_provider_ui.py tests/test_pdf_ops.py tests/test_undo_stress.py -q` |
| **Full suite command** | **分割実行**: `python -m pytest -q --ignore=tests/test_ocr_pipeline.py` → `python -m pytest -q tests/test_ocr_pipeline.py` |
| **Estimated runtime** | quick ~31秒（440 tests）/ full ~41秒（1170 + 17 = 1187 tests） |
| **Lint gates** | `ruff check .` / `ruff format --check .`（CLAUDE.md 必須ゲート） |

> **⚠️ フルスイートは分割形式が正**: 単一プロセスの `pytest -q` は
> `tests/test_ocr_pipeline.py::TestPipelineHardening::test_cancel_finite_time_no_deadlock`
> 実行中に Windows fatal exception `0x80000003` でプロセスが落ちることがある（6回中4回）。
> A/B 検証で製品コードは無実と確定済み（T-01-21a・AR-03）。UAT #2 で受容判断済みであり、
> 切り分け・修復は **Phase 3（V190-QA-01）** が引き取る。本フェーズのゲートは分割実行を正とする。
>
> **Windows 環境注記**: `%TEMP%\pytest-of-*` に対して `PermissionError` が出る場合は
> 書き込み可能なディレクトリを `--basetemp` で明示して再実行する（環境要因であり失敗ではない）。

---

## Sampling Rate

- **After every task commit:** Run 各タスクの `<automated>` コマンド（下表 Automated Command 列）
- **After every plan wave:** Run quick run command（~31秒）
- **Before `/gsd-verify-work`:** Full suite（分割実行）+ `ruff check .` + `ruff format --check .` が green
- **Max feedback latency:** 41秒（フルスイート分割実行の実測合計）

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | V190-SAFE-01 | T-01-01 | 「名前を付けて保存」が暗号化 PDF の暗号化を無条件で維持する | integration (tracer) | `pytest tests/test_password.py -x -q` | ✅ | ✅ green |
| 1-01-02 | 01 | 1 | V190-SAFE-01 / 02 | T-01-01 / T-01-02 / T-01-03 | 上書きフォールバック・縮小保存が `PDF_ENCRYPT_KEEP` を `setdefault` で既定化し、明示指定を上書きしない | unit | `pytest tests/test_password.py tests/test_save_overwrite.py -x -q` | ✅ | ✅ green |
| 1-01-03 | 01 | 1 | V190-SAFE-01 / 02 | T-01-01 / T-01-03 | 保存全経路の暗号化維持と `pdf_has_password` の実ファイル一致 | unit | `pytest tests/test_password.py tests/test_save_overwrite.py -q && ruff check . && ruff format --check .` | ✅ | ✅ green |
| 1-02-01 | 02 | 2 | V190-SAFE-03 | T-01-05 | `build_provider("off")` が `OCRDisabledError` を送出し OCRProvider を生成しない | unit | `pytest tests/test_ocr.py -x -q -k "OCRDisabledGuard or BuildProvider or OcrProviderDefault"` | ✅ | ✅ green |
| 1-02-02 | 02 | 2 | V190-SAFE-03 | T-01-06 / T-01-07 / T-01-08 | 入口 disabled 化・実行開始ガード・ダイアログ内再生成ガードの3層で OFF が OCR 実行に入れない | unit | `pytest tests/test_ocr.py tests/test_lang_parity.py tests/test_batch_ocr_dialog.py -x -q` | ✅ | ✅ green |
| 1-02-03 | 02 | 2 | V190-SAFE-03 | T-01-05 / T-01-06 / T-01-07 | OFF ガード全4経路の回帰固定 | unit | `pytest tests/test_ocr.py tests/test_batch_ocr_dialog.py tests/test_lang_parity.py -q && ruff check . && ruff format --check .` | ✅ | ✅ green |
| 1-03-01 | 03 | 2 | V190-CFG-01 / 02 | T-01-09 / T-01-12 | テンプレート切替が外部プロンプトファイルへ書き込まない。未保存判定が外部ファイル有無で分岐しない（D-15 / D-18） | unit (source/AST guard) | `pytest tests/test_provider_ui.py -q -k TestUnsavedTemplateChangesSourceGuard` ⚠️**是正済み**（下記 Audit 参照） | ✅ | ✅ green |
| 1-03-02 | 03 | 2 | V190-CFG-01 | T-01-09 | 旧ライブ連動挙動を前提にした既存テスト4件が新契約へ追従 | unit | `pytest tests/test_provider_ui.py -x -q -k "TemplateChangeFlow"` | ✅ | ✅ green |
| 1-03-03 | 03 | 2 | V190-CFG-01 / 02 | T-01-09 / T-01-10 / T-01-11 / T-01-12 | 書き込みは `dialog.py:_apply` の1経路のみ。Cancel で外部ファイル不変・未作成。編集後の切替は常に未保存確認 | unit | `pytest tests/test_provider_ui.py tests/test_prompt_templates.py tests/test_settings_keyguard.py -q && ruff check . && ruff format --check .` | ✅ | ✅ green |
| 1-04-01 | 04 | 3 | V190-SAFE-04 / 05 | T-01-14 / T-01-16 / T-01-17 | 挿入途中失敗で挿入分を巻き戻し、挿入元 Document を `finally` で必ず close。複製は Undo 後置確定 | unit | `pytest tests/test_pdf_ops.py tests/test_lang_parity.py -x -q` | ✅ | ✅ green |
| 1-04-02 | 04 | 3 | V190-UNDO-01 | T-01-13 / T-01-15 | 復元失敗時に state を `_push_evicting` でスタックへ戻し、`_dispose_state` を呼ばず Blob を温存してブロッキング通知 | unit | `pytest tests/test_pdf_ops.py tests/test_undo_stress.py tests/test_lang_parity.py -x -q` | ✅ | ✅ green |
| 1-04-03 | 04 | 3 | V190-SAFE-04 / 05 · V190-UNDO-01 | T-01-13 / T-01-14 | ロールバック・Undo タイミング・復元失敗の3系統を回帰固定 | unit | `pytest tests/test_pdf_ops.py tests/test_undo_stress.py tests/test_v150_regression.py -q && ruff check . && ruff format --check .` | ✅ | ✅ green |
| 1-05-01 | 05 | 4 | V190-UNDO-02 | T-01-18a | `duplicate`/`merge`/`merge_resize` の do→undo→redo→undo でページ digest 列が一致 | unit | `pytest tests/test_pdf_ops.py -x -q -k "AllOpsUndoRedoRoundtrip"` | ✅ | ✅ green |
| 1-05-02 | 05 | 4 | V190-UNDO-02 | T-01-19a | 境界（単一ページ）・隣接（先頭/末尾）・順序・精度（MediaBox 寸法）・最小入力の5エッジ | unit | `pytest tests/test_pdf_ops.py -x -q -k "AllOpsUndoRedoRoundtrip"` | ✅ | ✅ green |
| 1-05-03 | 05 | 4 | V190-UNDO-02 | T-01-20a / T-01-21a | D-12 棚卸し（`_save_undo` 全16箇所）記録とフェーズゲート | suite gate | `pytest -q && ruff check . && ruff format --check .` ⚠️**分割実行が正**（上記注記） | ✅ | ⚠️ flaky（分割実行で green・T-01-21a） |
| 1-06-00 | 06 | 5 | V190-UNDO-01 | — | 逆デルタのデータモデル変更方式の確定（one-way・REVERSIBILITY GATE） | checkpoint:decision | — （blocking gate・方式 A 選択） | N/A | ✅ 承認済み |
| 1-06-01 | 06 | 5 | V190-UNDO-01 | T-01-18b | `delete`/`delete_redo` で部分失敗→再試行成功後も次段逆デルタが当初データ全件を保持 | unit (tracer) | `pytest tests/test_pdf_ops.py::TestUndoRedoRestoreFailure tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip tests/test_undo_stress.py -q` | ✅ | ✅ green |
| 1-06-02 | 06 | 5 | V190-UNDO-01 | T-01-18b | `page_edit`/`insert_undo`/`insert_redo` へ蓄積方式を展開 | unit | `pytest tests/test_pdf_ops.py tests/test_undo_stress.py -q` | ✅ | ✅ green |
| 1-06-03 | 06 | 5 | V190-UNDO-01 | T-01-19b / T-01-20b / T-01-21b | `merge_resize`系展開・`merge_undo` 非該当ピン・蓄積 Blob の解放と二重解放ゼロ | unit | `pytest tests/test_pdf_ops.py tests/test_undo_stress.py tests/test_lang_parity.py -q` | ✅ | ✅ green |
| 1-07-00 | 07 | 6 | V190-UNDO-01 | — | `page_edit` 2段階 mutation 中間失敗の封じ方の確定（one-way・REVERSIBILITY GATE） | checkpoint:decision | — （blocking gate・option-b 選択） | N/A | ✅ 承認済み |
| 1-07-01 | 07 | 6 | V190-UNDO-01 | T-01-22 / T-01-23 / T-01-24 | mutation 順序反転（insert→delete）で内容喪失を構造的に排除。復旧不能時は `content_at_risk` の強い警告 | unit (tracer) | `pytest tests/test_pdf_ops.py::TestUndoRedoRestoreFailure tests/test_pdf_ops.py::TestPageEditRedactMosaic tests/test_lang_parity.py tests/test_undo_stress.py -q` | ✅ | ✅ green |
| 1-07-02 | 07 | 6 | V190-UNDO-01 | T-01-27 | 復元ループの一時 `fitz.Document` 7箇所を `try/finally` で保護（AST 走査ガードで恒久固定） | unit (AST guard) | `pytest tests/test_pdf_ops.py::TestTempDocumentCloseGuard tests/test_pdf_ops.py::TestUndoRedoRestoreFailure tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip -q` | ✅ | ✅ green |
| 1-07-03 | 07 | 6 | V190-UNDO-01 | T-01-25 / T-01-26 | `insert`（base op）の削除ループへ部分適用保護を展開・Blob 解放を機械検証 | unit | `pytest tests/test_pdf_ops.py tests/test_undo_stress.py tests/test_lang_parity.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### 要件 → テストクラス対応（実測件数・2026-08-11）

| 要件 | 検証テストクラス | 件数 |
|------|------------------|------|
| V190-SAFE-01 / 02 | `tests/test_password.py::TestSavePathsKeepEncryption` / `::TestDerivePdfHasPassword` | 10 / 3 |
| V190-SAFE-03 | `tests/test_ocr.py::TestOCRDisabledGuard` | 8 |
| V190-CFG-01 | `tests/test_provider_ui.py::TestApplyOnlyPromptFileWrite` | 6 |
| V190-CFG-02 | `tests/test_provider_ui.py::TestUnsavedTemplateChangesSinglePath` / `::TestUnsavedTemplateChangesSourceGuard` | 3 / **3（本監査で新設）** |
| V190-SAFE-04 | `tests/test_pdf_ops.py::TestInsertRollback` | 5 |
| V190-SAFE-05 | `tests/test_pdf_ops.py::TestDuplicateUndoTiming` | 2 |
| V190-UNDO-01 | `tests/test_pdf_ops.py::TestUndoRedoRestoreFailure` / `::TestTempDocumentCloseGuard` / `tests/test_undo_stress.py::TestBlobLeakDetection` | 19 / 1 / 7 |
| V190-UNDO-02 | `tests/test_pdf_ops.py::TestAllOpsUndoRedoRoundtrip` | 20 |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.
（pytest・`tests/conftest.py`・`_make_fake_app` / `_make_full_fake_app` / `_make_template_dialog` の
既存ヘルパーで全要件を検証済み。フレームワーク導入も新規フィクスチャ新設も不要だった。）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| コールドスタート・スモーク（新規起動 → PDF を開く → プレビュー/サムネイル表示 → 1操作 → Undo） | Phase Goal 全体 | Tkinter の実 GUI 起動・実描画の目視確認であり、ヘッドレス自動化の対象外（本プロジェクトのテストはロジック層のみを検証する方針） | PageFolio を完全終了 → 新規起動 → エラーなくメインウィンドウ表示 → PDF を開いてプレビュー/サムネイル表示 → 何か1操作して Undo が効くことを確認（UAT #1・2026-08-10 pass） |
| 単一プロセス `pytest -q`（フルスイート）の不安定化の受け入れ判断 | V190-QA-01（Phase 3 が引き取り） | プロセスクラッシュ（Windows fatal exception `0x80000003`）は再現率6回中4回で決定的でなく、判定自体が人の受け入れ判断。製品コードは A/B 検証で無実と確定済み | 分割実行（`pytest -q --ignore=tests/test_ocr_pipeline.py` + `pytest -q tests/test_ocr_pipeline.py`）が全件 green であることを確認したうえで、当面の運用として分割実行を正とすることを承認（UAT #2・2026-08-10 pass・T-01-21a / AR-03） |

*上記2件は要件（V190-*）の振る舞い検証ではなく、フェーズ全体のスモークと CI 運用方針の判断である。
9要件すべての振る舞いは自動テストで検証されているため `nyquist_compliant: true` を維持する。*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 21実タスク全件に `<automated>` あり（Task 0 の checkpoint:decision 2件は blocking gate であり実装タスクではない）
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — 自動 verify なしの連続は最大1（各プランの Task 0 のみ）
- [x] Wave 0 covers all MISSING references — Wave 0 不要（既存インフラで充足）
- [x] No watch-mode flags — 全コマンドが `-q` / `-x -q` の単発実行。`--watch` 系フラグゼロ
- [x] Feedback latency < 41s — quick 31秒 / full（分割）41秒の実測
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-11

---

## Validation Audit 2026-08-11

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

### GAP-01（PARTIAL → RESOLVED）— V190-CFG-02 / D-18 の構造ガード欠落

**検出内容:** `01-03-PLAN.md:113`（Task 1）の `<automated>` コマンドが実行不能だった。

```
python -c "import pagefolio.dialogs.llm_config.sections as m; import inspect;
           src=inspect.getsource(m._has_unsaved_template_changes); ..."
→ AttributeError: module 'pagefolio.dialogs.llm_config.sections'
  has no attribute '_has_unsaved_template_changes'
```

`_has_unsaved_template_changes` はモジュールレベル関数ではなく `SectionsMixin`（`sections.py:44`）の
メソッド（`:1156`）であるため、当該コマンドは一度も成立していなかった。結果として D-18 の
**構造的不変条件**（判定関数に `prompt_file_exists` 分岐が復活しないこと）を固定する自動ガードが
テストスイートに存在しなかった。

**なぜ既存の挙動テストでは不十分か:** `TestUnsavedTemplateChangesSinglePath` の3件はいずれも
外部プロンプトファイルが**存在しない**条件を踏む。`prompt_file_exists(...)` による早期 False 分岐が
再導入されても、この条件下では挙動が変わらず3件とも green のまま通過してしまう。

**是正（テストのみ・実装コード無改変）:** `tests/test_provider_ui.py` へ
`TestUnsavedTemplateChangesSourceGuard`（3メソッド）を新設。01-07 が確立した
`tests/test_pdf_ops.py::TestTempDocumentCloseGuard` と同型の AST 走査ガードで、
(1) メソッド本体に `prompt_file_exists` 参照がゼロ（AST の `ast.Name` 走査）、
(2) 生ソース文字列にも該当なし（属性アクセス形式での再導入も捕捉する補強）、
(3) Pitfall 5 対策として未選択時分岐 `if not self._active_template_name:` が1つだけ残存、
の3点を固定した。

- `tests/test_provider_ui.py::TestUnsavedTemplateChangesSourceGuard::test_method_body_never_references_prompt_file_exists`
- `tests/test_provider_ui.py::TestUnsavedTemplateChangesSourceGuard::test_method_source_substring_never_contains_prompt_file_exists`
- `tests/test_provider_ui.py::TestUnsavedTemplateChangesSourceGuard::test_unselected_template_guard_branch_still_present`

**再検証コマンド:** `python -m pytest tests/test_provider_ui.py -q -k TestUnsavedTemplateChangesSourceGuard` → 3 passed

### 監査時の実測結果

| ゲート | コマンド | 結果 |
|--------|----------|------|
| Quick | `pytest tests/test_password.py tests/test_ocr.py tests/test_provider_ui.py tests/test_pdf_ops.py tests/test_undo_stress.py -q` | 440 passed（31秒） |
| Full A | `pytest -q --ignore=tests/test_ocr_pipeline.py` | 1170 passed（40秒・監査前 1167 + 新規3） |
| Full B | `pytest -q tests/test_ocr_pipeline.py` | 17 passed（0.5秒） |
| Lint | `ruff check .` | All checks passed! |
| Format | `ruff format --check .` | 87 files already formatted |

### 監査対象外（既存の別トラック）

`01-REVIEW.md`（iteration 3）の Warning 6件（WR-01〜WR-06）は本フェーズ9要件の
カバレッジギャップではなく、隣接コードパスの品質課題である（`01-VERIFICATION.md` が
Success Criterion 5 に非抵触と判定済み・critical 0）。Nyquist 監査の対象範囲外として
そのトラックへ残す。
