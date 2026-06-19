---
phase: 03
slug: ocr-a
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 出典: `03-RESEARCH.md` §Validation Architecture / §Security Domain。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-cov 7.1.0 |
| **Config file** | `pyproject.toml`（`pythonpath`・S101 除外設定済み・**編集禁止**） |
| **Quick run command** | `python -m pytest tests/test_viewer.py tests/test_settings_keyguard.py tests/test_ocr_providers.py -x` |
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

> Task ID / Plan / Wave はプラン確定時に割当（plan-phase の本ステップは計画前に走るため要件粒度で先行記述）。
> 各行は `03-RESEARCH.md` の Phase Requirements → Test Map に対応。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | V16-QUAL-01 | — | N/A | unit | `python -m pytest tests/test_viewer.py -k rotate -x`（90/270° で pixmap w/h 入替） | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-01 | — | N/A | unit | `python -m pytest tests/test_viewer.py -k rotate_180 -x`（180° で w/h 不変） | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-01 | — | N/A | manual | 手順書: 回転 → 再読込/ページ送り無しで即反映を目視 | ❌ doc | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-02 | T-key-log | `_save_settings` がキー値をログ非出力 | unit (caplog) | `python -m pytest tests/test_settings_keyguard.py -k log -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-02 | T-key-log | 各クラウドプロバイダがキー値をログ非出力 | unit (caplog) | `python -m pytest tests/test_ocr_providers.py -k log -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-02 | T-key-src | `pagefolio/` ソースに実キーパターン不在 | unit (scan) | `python -m pytest tests -k no_real_api_keys -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-02 | T-key-* | 3 経路（設定/ソース/ログ）監査チェックリスト | doc | 監査文書レビュー | ❌ doc | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-03 | T-dos-retry | max_tokens クランプ境界 | unit | `python -m pytest tests/test_ocr.py -k MaxTokensClamp` | ✅ 既存（重複不要） | ✅ green |
| TBD | TBD | TBD | V16-QUAL-03 | T-dos-retry | 429/Retry-After/バックオフ/サーキットブレーカー | unit | `python -m pytest tests/test_ocr.py -k "Backoff or Circuit or ClampRetry"` | ✅ 既存（重複不要） | ✅ green |
| TBD | TBD | TBD | V16-QUAL-03 | T-dos-retry | 実 API でクランプ/429 が期待動作 | manual | 検証チェックリスト文書（D-08） | ❌ doc | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-04 | T-truncate | Claude `stop_reason`=max_tokens で truncated 検出 | unit | `python -m pytest tests/test_ocr_providers.py -k truncat -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-04 | T-truncate | Gemini `finishReason`=MAX_TOKENS で truncated 検出 | unit | `python -m pytest tests/test_ocr_providers.py -k truncat -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-04 | T-truncate | 途切れ時に部分テキスト保持 | unit | `python -m pytest tests/test_ocr_providers.py -k truncat -x`（results 残存をアサート） | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-04 | — | 待機秒数が文言に含まれる | unit | `python -m pytest tests/test_ocr.py -k waiting -x`（LANG `{sec}` 整合） | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V16-QUAL-04 | — | ja/en LANG キー一致 | unit | `python -m pytest -k lang_keys -x`（`set(LANG['ja'])==set(LANG['en'])`） | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_viewer.py` — 回転 w/h 入替テスト追加（V16-QUAL-01: 90/270° 入替・180° 不変）
- [ ] `tests/test_settings_keyguard.py` — caplog ログ非出力テスト追加（V16-QUAL-02 / D-11: `_save_settings`）
- [ ] `tests/test_ocr_providers.py` — 途切れ検出テスト（V16-QUAL-04 / D-05）＋プロバイダ caplog テスト（V16-QUAL-02 / D-11）
- [ ] `tests/`（新規 or 既存）— ソース実キースキャンテスト（V16-QUAL-02 / D-12: `sk-ant-`・`AIza`・長 base64、テストフィクスチャ除外）
- [ ] LANG ja/en キー一致テスト（無ければ追加・`{sec}` プレースホルダ整合の回帰防止）
- [ ] フレームワーク install: **不要**（pytest 既存）

*max_tokens クランプ・429/Retry-After/バックオフ/サーキットブレーカーは既存テスト済み（`test_ocr.py`）。重複追加しない（D-09）。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 回転後の「見た目の即時反映」 | V16-QUAL-01 | GUI 描画の体感は自動アサート困難（pixmap w/h は自動・最終目視は手動） | 手順書: PDF を開く → ページ選択 → 回転ボタン → 再読込/ページ送りせずプレビューが即回ることを目視。複数選択時は対象サムネイルも揃って回ることを確認 |
| 実 API での max_tokens クランプ / 429 リトライ挙動 | V16-QUAL-03 | 実 API は課金・429 再現困難で CI 不安定（D-07） | 検証チェックリスト文書（D-08, `.planning/phases/03-ocr-a/` 内）: 手順・期待結果・結果記入欄。ユーザーが任意実行して記録 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
