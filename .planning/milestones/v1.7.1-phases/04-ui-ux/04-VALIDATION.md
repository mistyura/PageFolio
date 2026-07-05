---
phase: 4
slug: ui-ux
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest -x -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -x -q`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | V171-UIUX-01 | T-04-01 | keysym は固定 cmd_map への割当のみ・eval/exec 不使用 | unit | `pytest tests/test_v150_regression.py -x -q` | ✅ | ⬜ pending |
| 04-01-02 | 01 | 1 | V171-UIUX-01 | T-04-01 | 再バインドは unbind→bind で旧キー残存なし | unit | `pytest tests/test_v150_regression.py -x -q` | ✅ | ⬜ pending |
| 04-01-03 | 01 | 1 | V171-UIUX-01 | — | N/A | unit | `pytest tests/test_v150_regression.py -x -q` | ✅ | ⬜ pending |
| 04-02-01 | 02 | 2 | V171-UIUX-01 | T-04-01 / T-04-05 | 重複割当は保存時に拒否（後勝ち上書き防止） | unit + manual | `python -c "from pagefolio.dialogs import ShortcutsDialog"` | ✅（純関数）/ ❌ W0（実キー入力は手動） | ⬜ pending |
| 04-02-02 | 02 | 2 | V171-UIUX-03 | — | N/A | unit | `pytest tests/test_provider_ui.py -x -q` | ✅ | ⬜ pending |
| 04-02-03 | 02 | 2 | V171-UIUX-01/03 | T-04-02 | 追加/改称文言に機密なし・_SENSITIVE_KEYS 不変 | unit | `pytest tests/test_lang_parity.py -x -q` | ✅ | ⬜ pending |
| 04-03-01 | 03 | 3 | V171-UIUX-03 | — | N/A | unit | `pytest tests/test_provider_ui.py tests/test_lang_parity.py -x -q` | ✅ | ⬜ pending |
| 04-03-02 | 03 | 3 | V171-UIUX-03 | T-04-02 / T-04-06 | api_key が settings に流入しない・ディスク/メモリ整合 | unit | `pytest tests/test_provider_ui.py -x -q` | ❌ W0（cascade テスト新規） | ⬜ pending |
| 04-03-03 | 03 | 3 | V171-TEST-03 | T-04-07 | Ollama 接続例外を捕捉しステータス表示に留める | unit | `pytest tests/test_provider_ui.py -x -q` | ❌ W0（Ollama テスト新規） | ⬜ pending |
| 04-04-01 | 04 | 4 | V171-UIUX-02 | — | N/A | unit + manual | `pytest tests/test_lang_parity.py -x -q` | ✅（キー存在）/ ❌ W0（en 実描画は手動） | ⬜ pending |
| 04-04-02 | 04 | 4 | V171-UIUX-02 | — | N/A | unit | `pytest tests/test_pdf_ops.py -k split -x -q` | ✅（既存拡張） | ⬜ pending |
| 04-04-03 | 04 | 4 | V171-UIUX-02 | T-04-08 | 使用中キー誤削除なし（引用符付き完全一致） | unit | `pytest tests/test_lang_parity.py -x -q` | ✅（既存拡張・D-11 追加） | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

既存インフラ（pytest 9.0.2・`tests/` 一式）が全要件をカバーする。新規テストは既存ファイルへのクラス/関数追加、または既存の SimpleNamespace スタブ方式（Tk 非生成）で自給する。別途の framework install・conftest 追加は不要。

- 新規テスト自給箇所（各タスク内で作成する — 別 Wave 0 プラン不要）:
  - `tests/test_v150_regression.py` — keysym 変換/重複検出/表示変換の純関数テスト（04-01-03）
  - `tests/test_provider_ui.py` — ネスト適用トランザクション cascade テスト（04-03-02）・Ollama 共通ヘルパーテスト（04-03-03）
  - `tests/test_lang_parity.py` — D-11 未使用キー検出テスト（04-04-03）
  - `tests/test_pdf_ops.py` — 分割の範囲未入力 showerror 回帰テスト（04-04-02）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ShortcutsDialog の実キー入力→保存→即時反映 | V171-UIUX-01 | 実 Tk `<KeyPress>` の `event.state`/`event.keysym`（A1 Alt ビット 0x20000 は Windows 実機で要実測）を使う実ウィジェットテストが既存スイートに 1 件も無い | 設定→⌨ ショートカット設定…→任意行「変更」→実キー押下→保存→そのキーで即動作を確認。重複キー保存が拒否されること・「解除」で無効化されることも確認 |
| 拡大ポップアップ文言の en 表示 | V171-UIUX-02 | Tk 実描画の目視（lang='en' でタイトル/ボタンが英語表示） | lang を en にしてサムネイルをダブルクリック→ポップアップのタイトル・縮小/拡大/閉じるが英語表示であることを確認 |
| LLMConfig 共通/固有見出しの表示・ネスト適用の外側キャンセル整合 | V171-UIUX-03 | ダイアログ描画とカスケード操作の目視 | 設定→AI・OCR→LLM 設定で共通/固有の見出しを確認。LLM 設定を適用→外側「キャンセル」→再度開いて LLM 変更が残っていることを確認 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references（新規テストは各タスク内で自給・既存インフラで充足）
- [x] No watch-mode flags
- [x] Feedback latency < 60s（`pytest -x -q` 想定 ~30s）
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (planner)
