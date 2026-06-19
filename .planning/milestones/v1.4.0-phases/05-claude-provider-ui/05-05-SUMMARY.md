---
phase: 05-claude-provider-ui
plan: "05"
subsystem: ocr-ui
tags: [ui, security, claude, cost-confirm, session-key, waiting-progress, ocr-dialog]
dependency_graph:
  requires:
    - phase: 05-01
      provides: ClaudeProvider（cost_estimate・effort 判定）
    - phase: 05-02
      provides: ocr_cost_confirm_* / ocr_session_key_label / ocr_waiting_retry 文言
    - phase: 05-03
      provides: build_provider claude 分岐・_resolve_api_key・run_parallel waiting・_session_api_keys
  provides:
    - OCRDialog._is_cloud_provider（pagefolio/ocr_dialog.py）
    - OCRDialog._estimate_cost（pagefolio/ocr_dialog.py）
    - OCRDialog._needs_session_key（pagefolio/ocr_dialog.py）
    - OCRDialog._confirm_cost（pagefolio/ocr_dialog.py）
    - OCRDialog セッションキー入力欄（show="*" マスク・_key_frame）
    - OCRDialog._on_run クラウド実行ゲート（コスト確認・キャンセル可）
    - OCRDialog on_progress の waiting 分岐（ocr_waiting_retry 表示）
    - OCRDialog._on_run の build_provider 経由プロバイダ中立化
  affects:
    - Phase 06（Gemini 対応時に _is_cloud_provider に "gemini" を追加）
tech-stack:
  added: []
  patterns:
    - messagebox.askyesno によるコスト確認ゲート（_confirm_cost・D-11・毎回確認）
    - show="*" マスク Entry + api_key_var（D-04）
    - "waiting/{attempt}" 形式の status でリトライ番号を伝搬（on_progress シグネチャ互換）
    - _needs_session_key で env 設定済みなら入力欄非表示（D-02/D-03）
    - _is_cloud_provider で isinstance ガードを併用（将来 provider 差し替え対応）
key-files:
  created: []
  modified:
    - pagefolio/ocr_dialog.py
    - pagefolio/ocr.py
    - tests/test_ocr.py
key-decisions:
  - "on_progress の waiting status を 'waiting/{attempt}' 形式に変更しリトライ番号を伝搬（ocr_dialog 側で parse）"
  - "コスト確認ダイアログは messagebox.askyesno を使用（grab_set モーダルより軽量・D-11 毎回確認）"
  - "セッションキー入力欄は _build 内で _needs_session_key() を評価し env 設定済みなら非表示"
  - "api_key_var の値は _on_run 実行前に _session_api_keys に格納（settings には入れない・D-01/D-03）"
  - "build_provider を ocr_dialog から直接インポートして claude 分岐を解決（_on_run の provider 再生成中立化）"
patterns-established:
  - "プロバイダゲートパターン: _is_cloud_provider() → セッションキー確認 → _confirm_cost() → 実行"
  - "status エンコードパターン: 'waiting/{n}' で追加引数なしにリトライ番号を伝搬"
requirements-completed: [OCR-UI-03, OCR-SEC-03, OCR-PERF-04]
duration: 約20分
completed: "2026-06-07T11:00:00Z"
---

# Phase 05 Plan 05: クラウド実行ゲート・セッションキー入力・waiting 進捗 SUMMARY

**OCRDialog にクラウド実行前コスト確認ゲート（_confirm_cost・毎回・キャンセル可）・マスク付きセッションキー入力欄（show="*"・非永続化）・run_parallel の waiting 進捗表示（ocr_waiting_retry）を実装し、provider を build_provider 経由で中立化（claude 対応）した。**

## Performance

- **Duration:** 約 20 分
- **Started:** 2026-06-07
- **Completed:** 2026-06-07（Task 1-3 完了・Task 4 は human-verify 待ち）
- **Tasks:** 3/4（Task 4: checkpoint:human-verify 待ち）
- **Files modified:** 3

## Accomplishments

- OCRDialog に `_is_cloud_provider` / `_estimate_cost` / `_needs_session_key` / `_confirm_cost` を追加
- `_on_run` 冒頭にクラウド実行ゲート（セッションキー → コスト確認 → キャンセルで中止）を実装（成功基準5）
- env 未設定時のみマスク付きセッションキー入力欄（show="*"）を表示。値は `_session_api_keys` に格納、settings には入れない（成功基準3・D-01）
- `on_progress` の `status == "waiting/{attempt}"` 分岐で待機中（リトライ n/3）を after(0) 経由で表示（成功基準8・D-15・Pitfall 3）
- `_on_run` の provider 再生成を build_provider 経由に中立化（claude / lmstudio / off 対応・CR-02 後方互換維持）
- `run_parallel` の waiting status を `"waiting/{attempt}"` 形式に変更しリトライ番号を伝搬
- 既存テスト（waiting status 検証）を `startswith("waiting")` に更新、293 tests all passed

## Task Commits

1. **Task 1+2+3: provider 中立化・コスト確認ゲート・セッションキー入力・waiting 進捗・全テストグリーン** - `5d28359` (feat)
4. **Task 4: human-verify チェックポイント** — 未完了（human-verify 待ち）

## Files Created/Modified

- `pagefolio/ocr_dialog.py` — _is_cloud_provider / _estimate_cost / _needs_session_key / _confirm_cost 追加・_on_run ゲート実装・セッションキー入力欄・on_progress waiting 分岐・build_provider 中立化
- `pagefolio/ocr.py` — on_progress の waiting status を `"waiting/{attempt}"` 形式に変更
- `tests/test_ocr.py` — waiting status 検証を `startswith("waiting")` に更新

## Decisions Made

- `on_progress` の waiting status を `"waiting/{attempt}"` 形式にした。on_progress のシグネチャを変更せずにリトライ番号を伝搬できる最小変更。
- コスト確認ダイアログは `messagebox.askyesno` を使用。tk.Toplevel + grab_set より軽量で十分。
- セッションキー入力欄は _build 内で _needs_session_key() を評価し、env 設定済みなら非表示（フレームは生成するが pack しない）。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] run_parallel の waiting status 形式変更に伴うテスト更新**

- **Found during:** Task 3（テスト実行時）
- **Issue:** 05-03 の既存テストが `status == "waiting"` で検証していたが、実装を `f"waiting/{attempt}"` に変更したためテスト失敗
- **Fix:** `tests/test_ocr.py` の waiting 判定を `c[2].startswith("waiting")` に更新
- **Files modified:** tests/test_ocr.py
- **Verification:** 293 tests all passed
- **Committed in:** 5d28359

---

**Total deviations:** 1 自動修正（Rule 1 - Bug）
**Impact on plan:** テスト更新のみ。on_progress シグネチャ変更はプランの「実装者がシグネチャに整合させる」指示に従ったもの。スコープ超過なし。

## Issues Encountered

なし。

## User Setup Required

なし。

## Next Phase Readiness

- Task 4（human-verify）で `python pagefolio.py` を起動し、claude プロバイダで以下を目視確認する必要がある:
  1. env 未設定でマスク入力欄が出ること（成功基準3）
  2. 空のまま実行するとキー未設定エラーが出ること（成功基準2）
  3. コスト確認ダイアログに送信先・ページ数・概算コスト・プライバシー注記3点が表示されること（成功基準5）
  4. キャンセルで OCR が始まらないこと（成功基準5）
  5. lmstudio で従来どおり動くこと（後方互換・D-13）
  6. settings.json にキー文字列が含まれないこと（成功基準1）

## Threat Model Compliance

| Threat ID | Status | 対応内容 |
|-----------|--------|---------|
| T-05-16 | mitigated | show="*" マスク表示でショルダーハックを防ぐ（D-04）。キー値はログ・OCR結果・エラーに出さない |
| T-05-17 | mitigated | _session_api_keys にのみ格納。settings には入れない（D-01）。human-verify 手順7で確認予定 |
| T-05-18 | mitigated | クラウド時のみ _confirm_cost ゲート（毎回・キャンセル可・送信先/ページ数/概算/プライバシー3点） |
| T-05-19 | mitigated | env 未設定 + 入力欄空のとき ocr_api_key_missing を表示し実行しない |
| T-05-20 | mitigated | waiting 進捗更新は after(0) 経由でメインスレッドへ委譲（Pitfall 3 準拠） |
| T-05-SC | n/a | 新規 pip 依存ゼロ |

## Known Stubs

なし。

## Threat Flags

なし（新規ネットワークエンドポイント・スキーマ変更なし）。

## Self-Check: PASSED

- [x] `pagefolio/ocr_dialog.py` に `_is_cloud_provider`・`_estimate_cost`・`_needs_session_key`・`_confirm_cost` が存在
- [x] セッションキー入力欄 `show="*"` が存在（行 327）
- [x] `self.app._session_api_keys["claude"] = key` が存在（settings への api_key 代入は 0 件）
- [x] `_on_run` 冒頭に `_is_cloud_provider()` ゲートと `_confirm_cost()` が存在
- [x] `on_progress` に `status.startswith("waiting")` 分岐が存在
- [x] `_confirm_cost` に host・count・cost の3要素（ocr_cost_confirm_msg）が存在
- [x] `ruff check .` 全チェックパス
- [x] `python -m pytest tests/ -q` 293 passed
- [x] コミット 5d28359 存在
