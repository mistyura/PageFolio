---
phase: 03
slug: ocr-a
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-19
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 出典: `03-RESEARCH.md` §Validation Architecture / §Security Domain。
> Per-Task Map は確定プラン（03-01/02/03・最終タスク構造）へ割当済み。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-cov 7.1.0 |
| **Config file** | `pyproject.toml`（`pythonpath`・S101 除外設定済み・**編集禁止**） |
| **Quick run command** | `python -m pytest tests/test_viewer.py tests/test_settings_keyguard.py tests/test_ocr_providers.py tests/test_ocr.py -x` |
| **Full suite command** | `python -m pytest`（現行ベースライン **564 件**） |
| **Estimated runtime** | フル ~30–60 秒（ローカル・実 API 非依存） |

---

## Sampling Rate

- **After every task commit:** 変更モジュールの対象テスト（例 `python -m pytest tests/test_viewer.py -x`）
- **After every plan wave:** `python -m pytest`（564 件全緑）
- **Before `/gsd-verify-work`:** フル全緑 + `ruff check . && ruff format .`
- **Max feedback latency:** ~60 秒

---

## Per-Task Verification Map

> プラン確定後に割当済み（03-01/02/03・最終タスク構造に追従）。
> 各行は `03-RESEARCH.md` の Phase Requirements → Test Map に対応。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-02 | 01 | 1 | V16-QUAL-01 | — | N/A | unit | `python -m pytest tests/test_viewer.py -k rotate -x`（90/270° で pixmap w/h 入替） | ❌ W0→作成 | ⬜ pending |
| 03-01-02 | 01 | 1 | V16-QUAL-01 | — | N/A | unit | `python -m pytest tests/test_viewer.py -k rotate_180 -x`（180° で w/h 不変） | ❌ W0→作成 | ⬜ pending |
| 03-01-03 | 01 | 1 | V16-QUAL-01 | — | N/A | manual | checkpoint: 回転 → 再読込/ページ送り無しで即反映を目視（窓内/スクロール/Phase2 窓ナビ非破壊） | ❌ checkpoint | ⬜ pending |
| 03-02-01 | 02 | 1 | V16-QUAL-04 | T-truncate | 途切れを成功と誤表示しない・部分テキスト保持 | unit | `python -m pytest tests/test_ocr_providers.py -k truncat -x`（stop_reason/finishReason 検出 + results 残存） | ❌ W0→作成 | ⬜ pending |
| 03-02-02 | 02 | 1 | V16-QUAL-04 | — | N/A | unit | `python -m pytest tests/test_ocr.py -k "RetryWaitMessage or wait_message"`（実 delay 由来 round(delay) が文言へ・生 raw_delay 非出） | ❌ W0→作成 | ⬜ pending |
| 03-03-01 | 03 | 2 | V16-QUAL-02 | T-key-log | `_save_settings`/各クラウドプロバイダがキー値をログ非出力（キー名は許容） | unit (caplog) | `python -m pytest tests/test_settings_keyguard.py tests/test_ocr_providers.py -k log -x` | ❌ W0→作成 | ⬜ pending |
| 03-03-02 | 03 | 2 | V16-QUAL-02 | T-key-src | `pagefolio/` ソースに実キーパターン不在 | unit (scan) | `python -m pytest tests/test_source_keyguard.py -x` | ❌ W0→作成 | ⬜ pending |
| 03-03-02 | 03 | 2 | V16-QUAL-04 | — | N/A | unit | `python -m pytest tests/test_lang_parity.py -x`（ja/en キー一致・{sec} プレースホルダ整合） | ❌ W0→作成 | ⬜ pending |
| 03-03-03 | 03 | 2 | V16-QUAL-02 | T-key-* | 3 経路（設定/ソース/ログ）監査チェックリスト | doc | `03-AUDIT-KEY-SECRECY.md` レビュー（自動テスト ID 相互参照） | ❌ doc→作成 | ⬜ pending |
| （既存） | — | — | V16-QUAL-03 | T-dos-retry | max_tokens クランプ境界 | unit | `python -m pytest tests/test_ocr.py -k MaxTokensClamp`（既存・重複追加しない D-09） | ✅ 既存 | ✅ green |
| （既存） | — | — | V16-QUAL-03 | T-dos-retry | 429/Retry-After/バックオフ/サーキットブレーカー | unit | `python -m pytest tests/test_ocr.py -k "Backoff or Circuit or ClampRetry"`（既存・重複追加しない） | ✅ 既存 | ✅ green |
| 03-03-03 | 03 | 2 | V16-QUAL-03 | T-dos-retry | 実 API でクランプ/429 が期待動作 | manual | `03-VERIFICATION-REALAPI.md` 手順実行・記録（D-08） | ❌ doc→作成 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*完了ゲート（CLAUDE.md）: 03-03-03 で 開発履歴.md の既存 v1.7.0 項へ Phase 3 変更を追記 + APP_VERSION を v1.7.0 のまま維持（バンプなし・本マイルストーン完了版番、Phase 2 で設定済）し constants.py / README バッジ / 開発履歴.md の 3 箇所 v1.7.0 一致を確認。版番バンプはマイルストーン完了時。`<acceptance_criteria>` 化済み。*

---

## Wave 0 Requirements

> 本フェーズは独立 Wave 0 を設けず、各タスクが TDD（test-first）でテストを同タスク内に作成する（plan-checker Dim 8a PASS）。下記は各タスクが作成する net-new テスト資産。

- [x] `tests/test_viewer.py` — 回転 w/h 入替テスト（03-01-02: 90/270° 入替・180° 不変）
- [x] `tests/test_ocr_providers.py` — 途切れ検出テスト（03-02-01）+ プロバイダ caplog テスト（03-03-01）
- [x] `tests/test_ocr.py` — 待機文言 delay→sec 直接テスト（03-02-02・`_build_retry_wait_message`）
- [x] `tests/test_settings_keyguard.py` — caplog ログ非出力テスト（03-03-01 / D-11）
- [x] `tests/test_source_keyguard.py` — ソース実キースキャンテスト（03-03-02 / D-12・新規）
- [x] `tests/test_lang_parity.py` — ja/en LANG キー一致テスト（03-03-02・{sec} 整合の回帰防止・新規）
- [x] フレームワーク install: **不要**（pytest 既存）

*max_tokens クランプ・429/Retry-After/バックオフ/サーキットブレーカーは既存テスト済み（`test_ocr.py`）。重複追加しない（D-09）。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 回転後の「見た目の即時反映」 | V16-QUAL-01 | GUI 描画の体感は自動アサート困難（pixmap w/h は自動・最終目視は手動・03-01-03 checkpoint） | PDF を開く → ページ選択 → 回転ボタン → 再読込/ページ送りせずプレビューが即回ることを目視。複数選択時は窓内の対象サムネイルも揃って回ることを確認 |
| 実 API での max_tokens クランプ / 429 リトライ挙動 | V16-QUAL-03 | 実 API は課金・429 再現困難で CI 不安定（D-07） | `03-VERIFICATION-REALAPI.md`（03-03-03 で作成）: 手順・期待結果・結果記入欄。ユーザーが任意実行して記録 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies（plan-checker Dim 8a PASS）
- [x] Sampling continuity: no 3 consecutive tasks without automated verify（Dim 8c PASS）
- [x] Wave 0 covers all MISSING references（net-new テスト資産は各タスクで作成）
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-19
