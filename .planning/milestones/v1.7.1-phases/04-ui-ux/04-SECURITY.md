---
phase: 04
slug: ui-ux
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-05
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| ユーザーのキーボード入力 → Tk `<KeyPress>` event → keysym 文字列 | ShortcutsDialog がキャプチャする untrusted なキー入力 | keysym 文字列のみ。固定 `cmd_map` 11 コマンドへの割当キーとしてのみ使用 |
| ShortcutsDialog → `pagefolio_settings.json`（`shortcuts` キー） | 差分保存されるユーザー設定 | keysym 差分のみ。API キー等の機密は含まない |
| LLMConfigDialog の入力（APIキー・URL・モデル）→ `app._session_api_keys` / `app.settings` | APIキーはセッションメモリのみ、settings へは無害な設定値のみ | API キーはメモリのみ・`_SENSITIVE_KEYS` ガードで settings.json への保存をブロック |
| ネスト適用 → `app.settings`（メモリ）+ `pagefolio_settings.json`（ディスク） | D-14 の即時反映境界 | 設定値（プロバイダ選択・タイムアウト等）のみ |
| LANG 辞書 → UI 表示文言 | 静的表示文言（ユーザーデータではない） | 表示文言のみ |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Elevation of Privilege | `build_keysym_from_event`/`_bind_shortcuts`/ShortcutsDialog キャプチャ（keysym→コマンド割当） | low | mitigate | keysym は固定 `self._cmd_map`(11コマンド)へのマッピングにのみ使用。eval/exec/シェル実行への伝播なし（grep確認: 該当箇所なし）。重複は `find_duplicate_binding` で保存前に拒否 | closed |
| T-04-05 | Tampering | ShortcutsDialog 保存時の重複キー無言上書き | low | mitigate | 保存前に全体重複を再検査し衝突があれば書き込みを止める（`shortcuts.py` の save/capture 双方で `find_duplicate_binding` 呼び出しを確認） | closed |
| T-04-02a | Information Disclosure | `shortcuts` の settings 永続化（04-01/04-02） | low | accept | 保存対象は keysym 差分のみ。`_SENSITIVE_KEYS` ガード（settings.py）は本フェーズで変更なく維持 | closed |
| T-04-02b | Information Disclosure | `_apply_llm_settings_live` / ネスト `on_apply` の settings 書き込み（04-03） | high | mitigate | `_apply_llm_settings_live` は API キーを含まない `llm_settings` のみを settings へ書き込む(app.py:572)。`_SENSITIVE_KEYS` ガード不変。api_key が settings に流入しないことを test_provider_ui.py で確認 | closed |
| T-04-06 | Tampering | ネスト適用のディスク/メモリ不整合（C4） | medium | mitigate | 同一トランザクションでディスク保存とメモリ反映を実行。`TestSettingsDialogNestedApplyCascade`（test_provider_ui.py:1428）で外側キャンセル後も設定保持を回帰確認 | closed |
| T-04-07 | Denial of Service | `OllamaProvider.list_models` のネットワーク例外 | low | mitigate | `_probe_ollama_provider`（llm_config.py:1198）が `ConnectionError/TimeoutError/RuntimeError` を捕捉しステータス表示に留める。既存 `_probe_lm_provider` と同型実装を確認 | closed |
| T-04-08 | Denial of Service（機能不全） | 未使用 LANG キー削除時の使用中キー誤削除 | medium | mitigate | 引用符付き完全一致で該当キー行のみ削除。`test_no_unused_lang_keys`（test_lang_parity.py:55）でプレフィックス衝突（`tesseract_not_installed_hint`等）を誤削除しないことをテストで固定。全859テストでKeyError不在を確認 | closed |
| T-04-02c | Information Disclosure | 文言の情報露出（04-04） | low | accept | 追加/変更する文言は UI ラベルのみで機密を含まない | closed |

*Status: open · closed · open — below high 閾値（non-blocking）*
*Severity: critical > high > medium > low — workflow.security_block_on(high) 以上の open のみ threats_open に計上*
*Disposition: mitigate（実装で緩和済み） · accept（文書化されたリスク受容） · transfer（該当なし）*

パッケージインストールなし（stdlib + 既存依存のみ）のため各プランで T-04-SC（サプライチェーン）は非該当。

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-01 | T-04-02a | shortcuts の keysym 差分は機密情報を含まず、settings.json への平文保存は許容範囲（既存 `_SENSITIVE_KEYS` ガードが API キー等の真の機密を別途保護） | Plan-time (04-01/04-02 threat_model) | 2026-07-05 |
| AR-04-02 | T-04-02c | 04-04 で追加/変更した文言は UI 表示ラベルのみで機密情報を含まない | Plan-time (04-04 threat_model) | 2026-07-05 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-05 | 8 | 8 | 0 | orchestrator (L1 grep-depth, register_authored_at_plan_time=true, asvs_level=1 short-circuit) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-05
