---
phase: 2
slug: ocr-openai-chatgpt
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-11
updated: 2026-08-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml`（編集禁止 — 既存設定 `testpaths=["tests"]` をそのまま使用） |
| **Quick run command** | `python -m pytest tests/test_ocr_providers.py tests/test_ocr_provider_catalog.py -q` |
| **Full suite command** | `ruff check . && ruff format --check . && python -m pytest -q --ignore=tests/test_ocr_pipeline.py && python -m pytest -q tests/test_ocr_pipeline.py` |
| **Estimated runtime** | Quick 約 1 秒（`test_ocr_providers.py` 193 件 = 0.24s 実測 2026-08-11）／ Full 約 60 秒（`--ignore=tests/test_ocr_pipeline.py` で 1012 passed / 52.4s 実測 + `test_ocr_pipeline.py` 単体実行） |

**分割実行の理由:** STATE.md Blockers に記録のとおり、単一 pytest プロセスでの全件実行は
`tests/test_ocr_pipeline.py::TestPipelineHardening::test_cancel_finite_time_no_deadlock` 付近で
`Windows fatal exception: code 0x80000003` によりプロセスごとクラッシュする既知事象がある
（製品コードは無実と切り分け済み・v1.9.0 Phase 3 / V190-QA-01 で引き取り）。
本フェーズでも同じ分割運用に倣う。

**計測時の注意:** 上記の実測はサンドボックス環境で行ったため、`tmp_path` を使うテストが
`PermissionError: [WinError 5] ... pytest-of-shdwf` でセットアップ ERROR になる。
これは計測環境固有の事象であり製品コードの失敗ではない。実行者は「着手前の失敗件数」を
自分の環境で先に採取し、それとの差分で判定すること（各プランの acceptance_criteria も
絶対件数ではなく「着手前と同数以下」で記述してある）。

---

## Sampling Rate

- **After every task commit:** `python -m pytest tests/test_ocr_providers.py tests/test_ocr_provider_catalog.py tests/test_provider_ui.py -q`（約 8 秒）
- **After every plan wave:** `ruff check . && ruff format --check . && python -m pytest -q --ignore=tests/test_ocr_pipeline.py`（約 55 秒）
- **Before `/gsd-verify-work`:** 分割 Full suite 2 本が着手前と同数以下の失敗件数
- **Max feedback latency:** 60 秒（タスク単位は 8 秒）

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | V190-OAI-03, V190-OAI-12 | — | 存在しないモデル ID を既定値にしない（初回実行の確実な失敗を防ぐ） | checkpoint:decision | —（人手判断・D-09） | n/a | ⬜ pending |
| 2-01-02 | 01 | 1 | V190-CAT-01, V190-OAI-11, V190-OAI-12 | T-02-01, T-02-03, T-02-04, T-02-05, T-02-08 | API キーは引数注入のみ／既定 TLS 検証／空 org·project でヘッダ非付与／表示ホストと送信先の一致 | e2e（HTTP モック） | `python -m pytest tests/test_ocr_providers.py -x -q` | ✅ | ⬜ pending |
| 2-01-03 | 01 | 1 | V190-CAT-02, V190-OAI-02, V190-OAI-13 | T-02-01, T-02-02, T-02-06, T-02-08 | `_SENSITIVE_KEYS` による非永続化／独自リトライ・TLS 迂回の不在／registry 独立性 | unit + 静的解析 + ミューテーション | `python -m pytest tests/test_ocr_provider_catalog.py tests/test_ocr_providers.py -x -q` | ⬜（本タスクが新規作成） | ⬜ pending |
| 2-02-01 | 02 | 2 | V190-CAT-01, V190-OAI-04, V190-OAI-05 | T-02-03, T-02-04, T-02-07 | 送信先ホスト明示の確認ダイアログ／isinstance フォールバック維持 | unit | `python -m pytest tests/test_provider_ui.py tests/test_lang_parity.py tests/test_ocr.py -x -q` | ✅ | ⬜ pending |
| 2-02-02 | 02 | 2 | V190-CAT-01, V190-OAI-06 | T-02-03, T-02-07 | バッチ経路でも同一の同意ゲート（独立実装の挙動一致） | unit | `python -m pytest tests/test_batch_ocr_dialog.py tests/test_batch_ocr_state.py -x -q` | ✅ | ⬜ pending |
| 2-02-03 | 02 | 2 | V190-OAI-04, V190-OAI-05, V190-OAI-06 | T-02-04, T-02-09, T-02-10 | 表示ホスト＝実送信先の機械保証／同意抑止オプションの不在 | unit + ミューテーション | `python -m pytest tests/test_provider_ui.py tests/test_batch_ocr_dialog.py tests/test_lang_parity.py -x -q` | ✅ | ⬜ pending |
| 2-03-01 | 03 | 3 | V190-OAI-03 | T-02-11 | モデル一覧取得はユーザーの明示操作時のみ／0 件・失敗を同一の静的フォールバックへ合流 | unit（純関数 + HTTP モック） | `python -m pytest tests/test_ocr_providers.py -x -q` | ✅ | ⬜ pending |
| 2-03-02 | 03 | 3 | V190-CAT-01, V190-OAI-01, V190-OAI-02 | T-02-13 | combobox は `state="readonly"` + catalog 由来 values のみ／キー欄はマスク表示 | unit | `python -m pytest tests/test_provider_ui.py -x -q` | ✅ | ⬜ pending |
| 2-03-03 | 03 | 3 | V190-OAI-01, V190-OAI-02, V190-OAI-03 | T-02-01, T-02-02, T-02-12 | API キーを `llm_settings` に入れない／取得スレッド二重起動なし／ログにキーを出さない | unit | `python -m pytest tests/test_provider_ui.py tests/test_lang_parity.py tests/test_imports.py -x -q` | ✅ | ⬜ pending |
| 2-04-01 | 04 | 4 | V190-OAI-08, V190-OAI-09, V190-OAI-10 | T-02-05 | org·project の許可文字検証（入力境界）＋制御文字除去（ヘッダ境界）の 2 層防御 | unit | `python -m pytest tests/test_provider_ui.py tests/test_ocr_providers.py tests/test_lang_parity.py tests/test_font_hardcode_guard.py -x -q` | ✅ | ⬜ pending |
| 2-04-02 | 04 | 4 | V190-OAI-07 | T-02-06, T-02-10 | フォールバック各段での送信先再確認／連鎖の自動続行を作らない | unit | `python -m pytest tests/test_ocr_fallback.py tests/test_provider_ui.py -x -q` | ✅ | ⬜ pending |
| 2-04-03 | 04 | 4 | V190-OAI-02, V190-OAI-03, V190-OAI-04, V190-OAI-05, V190-OAI-06, V190-OAI-07, V190-OAI-11 | T-02-14 | 再起動後にキー欄が空／settings.json にキーが無い／確認ダイアログの実描画 | checkpoint:human-verify | —（実 API キー必須・CI 不可） | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**サンプリング連続性:** 自動 `<automated>` を持たないタスクは 2-01-01（checkpoint:decision）と
2-04-03（checkpoint:human-verify）の 2 件のみで、いずれも自動タスクに挟まれている。
自動検証なしのタスクが 3 連続する箇所は存在しない。

---

## Wave 0 Requirements

- [x] `tests/test_ocr_providers.py`（既存・193 件）が OpenAI プロバイダテストの受け皿になる — 新規作成不要
- [x] `tests/test_provider_ui.py` / `tests/test_batch_ocr_dialog.py` / `tests/test_ocr_fallback.py` /
      `tests/test_lang_parity.py` / `tests/test_settings_keyguard.py` / `tests/test_imports.py` /
      `tests/test_font_hardcode_guard.py` すべて既存 — 拡張のみ
- [x] `tests/test_ocr_provider_catalog.py` は**新規**だが、これを参照する最初の自動検証は
      02-01 Task 3（同タスクが作成する）であり、Wave 1 内で自己完結する。
      Wave 1 の先行タスク（02-01 Task 2）の `<automated>` は既存
      `tests/test_ocr_providers.py` のみを参照するため MISSING 依存は存在しない

*結論: 既存インフラで全フェーズ要件の自動サンプリングが成立する。専用の Wave 0 タスクは不要。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OpenAI 実キーでのモデル一覧取得・vision OCR 実行 | V190-OAI-02/03/11 | 実 API キーと課金が必要（CI 不可） | 02-04 Task 3 の手順 (1)。LLM 設定 UI で OpenAI を選択 → セッション限定キー入力 → モデル一覧取得（非チャットモデルの混入が無いことを目視）→ 1 ページ OCR 実行 → アプリ再起動でキー欄が空になることと `pagefolio_settings.json` にキーが無いことを確認 |
| 送信先確認・コスト確認ダイアログの表示 | V190-OAI-04/05/06 | Tkinter モーダルダイアログ（GUI 操作） | 02-04 Task 3 の手順 (2)。OpenAI 選択状態で OCR / バッチ OCR を起動し、`api.openai.com` の明示・対象ページ数・概算コストが読める形で出ることと、「いいえ」で送信されないことを目視確認 |
| フォールバック発動時の送信先再確認 | V190-OAI-07 | 一次プロバイダ失敗を実環境で誘発する必要あり | 02-04 Task 3 の手順 (3)。一次プロバイダのキーを無効化 → OCR 実行 → OpenAI 表示名と `api.openai.com` を含む確認が再提示され、承認後に OCR が完走することを確認 |
| モデル ID の実在確認（D-09） | V190-OAI-03/12 | 実 API キーまたは公式ドキュメント参照が必要 | 02-01 Task 1 の checkpoint:decision。option-a（実キーで `GET /v1/models`）または option-b（公式ドキュメント二次ソース）を選び、確定した `default_model` / `RECOMMENDED_MODELS` / 推論系判定の実例 / 除外対象の実例を SUMMARY へ記録 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies（checkpoint 2 件を除く全 10 タスクが自動コマンド保持）
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references（新規テストファイルは同一 Wave 内・同一タスクで作成される）
- [x] No watch-mode flags（全コマンドが `-q` / `-x` の 1 回実行）
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner sign-off 2026-08-11（`/gsd-validate-phase` による事後監査で `status: validated` へ昇格させること）
