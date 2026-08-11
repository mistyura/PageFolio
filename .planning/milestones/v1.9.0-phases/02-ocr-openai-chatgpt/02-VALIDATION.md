---
phase: 2
slug: ocr-openai-chatgpt
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
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
| **Full suite command** | `ruff check . && ruff format --check . && python -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` |
| **Estimated runtime** | Quick 約 1 秒（`test_ocr_providers.py` 253 件 = 0.34s 実測）／ Full 約 47 秒（**1387 passed / 0 failed** — `/gsd-validate-phase` 事後監査で実測 2026-08-11・HEAD `e0c53c2` + 監査追加テスト 3 件） |

**フェーズ完了後の実測（事後監査 2026-08-11）:** 計画時の 1187 から 1387 へ増加（+200）。
フルスイート 1 回目の実行で `tests/test_ocr_dialog_center.py` の 2 件が Tcl/Tk リソース枯渇
（`_tkinter.TclError`: `tk.tcl` 読込不可）で setup ERROR となる事象を 1 回観測したが、
単体実行では 2 passed、監査中の 2 回目以降のフルスイート実行では 0 error で 1387 passed。
STATE.md 記載の既知環境フレーキー（`test_shortcuts_dialog.py`・`test_toast.py` と同種）であり
製品コードの失敗ではない。Phase 3（V190-QA-01）が blocking gate として引き取る。

**ゲートの確定（02-REVIEWS.md HIGH-6 の解消・2026-08-11 実測で更新）:**

計画時に Windows 11 / Python 3.14 / HEAD=4b7f421 で実測した結果、以前の
「`--ignore=tests/test_ocr_pipeline.py` で分割実行し、失敗件数が着手前と同数以下」という
相対ゲートは**不要**と判明した。

- `python -m pytest -q` → `1029 passed, 158 errors`。158 件はすべて
  `PermissionError: [WinError 5] ... C:\Users\shdwf\AppData\Local\Temp\pytest-of-shdwf` で、
  `tmp_path` フィクスチャがベーステンポラリを走査できないという**環境固有の ACL 事象**。
  テスト本体は 1 件も実行されない setup ERROR であり、製品コードの失敗ではない。
- `python -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` →
  **`1187 passed`（失敗 0・error 0）**。連続 4 回すべて同結果。
  STATE.md Blockers に記録された `Windows fatal exception: code 0x80000003` による
  プロセスクラッシュも本 HEAD では 4/4 回とも再発しなかった。

したがって本フェーズのフルスイートゲートは **絶対ゲート＝失敗 0 件** とする。
`--basetemp` は上記 ACL 事象の回避専用でテストを 1 件も除外しない
（ACL 問題が起きない環境では省略してよい）。CLAUDE.md の「コミット前に `pytest` を通す」
という要求と例外なく一致する。

クラッシュが再発した場合のみ STATE.md の分割運用へ退避し、**その事実と件数を SUMMARY に
記録する**（黙って例外にしない）。Phase 3（V190-QA-01）が引き取る blocking gate は
「全件 1 プロセス完走・失敗 0」で変わらない。

---

## Sampling Rate

- **After every task commit:** `python -m pytest tests/test_ocr_providers.py tests/test_ocr_provider_catalog.py tests/test_provider_ui.py -q`（約 8 秒）
- **After every plan wave:** `ruff check . && ruff format --check . && python -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"`（約 35 秒）
- **Before `/gsd-verify-work`:** Full suite が **失敗 0 件**（`--ignore` 例外なし）
- **All Python edits:** `python -c "import ast,pathlib; ast.parse(pathlib.Path('<file>').read_text(encoding='utf-8'))"`（CLAUDE.md 変更時チェックリストの構文確認・02-REVIEWS.md 全体-2）
- **Max feedback latency:** 60 秒（タスク単位は 8 秒）

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | V190-OAI-03, V190-OAI-12 | T-02-16 | 存在しないモデル ID・能力未確認モデル・出典不明の単価を既定値にしない（Stage A/B 分割・02-REVIEWS.md HIGH-1/HIGH-2） | checkpoint:decision | —（人手判断・D-09。成果物 `02-CAPABILITY-MATRIX.md` の 13 列充足を `python -c` で検査） | n/a | ✅ 実施済（option-b） |
| 2-01-02 | 01 | 1 | V190-CAT-01, V190-OAI-11, V190-OAI-12 | T-02-01, T-02-03, T-02-04, T-02-05, T-02-08 | API キーは引数注入のみ／既定 TLS 検証／空 org·project でヘッダ非付与／表示ホストと送信先の一致 | e2e（HTTP モック） | `python -m pytest tests/test_ocr_providers.py -x -q` | ✅ | ✅ green |
| 2-01-03 | 01 | 1 | V190-CAT-02, V190-OAI-02, V190-OAI-13 | T-02-01, T-02-02, T-02-06, T-02-08 | `_SENSITIVE_KEYS` による非永続化／独自リトライ・TLS 迂回の不在／registry 独立性 | unit + 静的解析 + ミューテーション | `python -m pytest tests/test_ocr_provider_catalog.py tests/test_ocr_providers.py -x -q` | ✅（本タスクが作成済） | ✅ green |
| 2-02-01 | 02 | 2 | V190-CAT-01, V190-OAI-04, V190-OAI-05 | T-02-03, T-02-04, T-02-07 | 送信先ホスト明示の確認ダイアログ／isinstance フォールバック維持 | unit | `python -m pytest tests/test_provider_ui.py tests/test_lang_parity.py tests/test_ocr.py -x -q` | ✅ | ✅ green |
| 2-02-02 | 02 | 2 | V190-CAT-01, V190-OAI-06 | T-02-03, T-02-07 | バッチ経路でも同一の同意ゲート（独立実装の挙動一致） | unit | `python -m pytest tests/test_batch_ocr_dialog.py tests/test_batch_ocr_state.py -x -q` | ✅ | ✅ green |
| 2-02-03 | 02 | 2 | V190-OAI-04, V190-OAI-05, V190-OAI-06 | T-02-04, T-02-09, T-02-10 | 表示ホスト＝実送信先の機械保証／同意抑止オプションの不在 | unit + ミューテーション | `python -m pytest tests/test_provider_ui.py tests/test_batch_ocr_dialog.py tests/test_lang_parity.py -x -q` | ✅ | ✅ green |
| 2-03-01 | 03 | 3 | V190-OAI-03 | T-02-11 | モデル一覧取得はユーザーの明示操作時のみ／0 件・失敗を同一の静的フォールバックへ合流 | unit（純関数 + HTTP モック） | `python -m pytest tests/test_ocr_providers.py -x -q` | ✅ | ✅ green |
| 2-03-02 | 03 | 3 | V190-CAT-01, V190-OAI-01, V190-OAI-02 | T-02-13 | combobox は `state="readonly"` + catalog 由来 values のみ／キー欄はマスク表示 | unit | `python -m pytest tests/test_provider_ui.py -x -q` | ✅ | ✅ green |
| 2-03-03 | 03 | 3 | V190-OAI-01, V190-OAI-02, V190-OAI-03 | T-02-01, T-02-02, T-02-12 | API キーを `llm_settings` に入れない／取得スレッド二重起動なし／ログにキーを出さない | unit | `python -m pytest tests/test_provider_ui.py tests/test_lang_parity.py tests/test_imports.py -x -q` | ✅ | ✅ green |
| 2-04-01 | 04 | 4 | V190-OAI-08, V190-OAI-09, V190-OAI-10 | T-02-05, T-02-21, T-02-22 | org·project の許可文字検証（入力境界）＋制御文字除去（ヘッダ境界）の 2 層防御／effort は readonly 許可リスト + プロバイダ側の最終ガード／不正入力は無言破棄せず明示エラー | unit | `python -m pytest tests/test_provider_ui.py tests/test_ocr_providers.py tests/test_lang_parity.py tests/test_font_hardcode_guard.py -x -q` | ✅ | ✅ green |
| 2-04-02 | 04 | 4 | V190-OAI-07 | T-02-06, T-02-10 | フォールバック各段での送信先再確認／連鎖の自動続行を作らない／発火する例外種別の固定 | unit | `python -m pytest tests/test_ocr_fallback.py tests/test_provider_ui.py -x -q` | ✅ | ✅ green |
| 2-04-3A | 04 | 4 | V190-OAI-01, V190-OAI-02, V190-OAI-03, V190-OAI-09 | T-02-14 | 再起動後にキー欄が空／settings.json にキーが無い／モデル一覧の実描画と並び順 | checkpoint:human-verify | —（実 API キー必須・CI 不可） | n/a | ✅ 人手承認（合格） |
| 2-04-3B | 04 | 4 | V190-OAI-04, V190-OAI-05, V190-OAI-06, V190-OAI-11 | T-02-03, T-02-18, T-02-19 | 確認ダイアログの実描画／「いいえ」で送信されない／表示単価と公式価格ページの突き合わせ | checkpoint:human-verify | —（実 API キー必須・CI 不可） | n/a | ✅ 人手承認（1 回差し戻し後に合格・`36e7cc2`） |
| 2-04-3C | 04 | 4 | V190-OAI-07 | T-02-10 | 到達不能 URL による ConnectionError でフォールバックが発火し送信先が再提示される | checkpoint:human-verify | —（実 API キー必須・CI 不可） | n/a | ✅ 人手承認（合格） |
| 2-04-FIX | 04 | 4 | V190-OAI-01, V190-OAI-02 | T-02-01 | `_apply_llm_settings`／`_on_run` の再生成分岐が openai でも解決済みキーを `build_provider` へ渡す（汎用 else へ落ちない） | unit（回帰・`36e7cc2`） | `python -m pytest tests/test_provider_ui.py -x -q` | ✅ | ✅ green |
| 2-CR-01 | — | 事後 | V190-OAI-06 | T-02-06 | バッチ横断サマリのリトライ待機が `TypeError` でワーカーを落とさない（`interruptible_sleep` に callable を渡す） | unit（回帰・`e9289b6`） | `python -m pytest tests/test_batch_ocr_dialog.py -x -q` | ✅ | ✅ green |
| 2-AUD-01 | — | 監査 | V190-OAI-06 | T-02-06 | 単発側 `_summary_worker` のリトライ待機にもバッチ側と同一の不変条件（WR-01 のパリティ要求） | unit（パリティ・ミューテーション検証済） | `python -m pytest tests/test_batch_ocr_dialog.py -k TestSingleShotSummaryRetrySleepParity -q` | ✅ | ✅ green |
| 2-AUD-02 | — | 監査 | V190-OAI-05 | T-02-18 | `OCR_PRICE_TABLE` の宣言順が部分文字列衝突に対して安全（IN-01 の将来混入ガード） | unit（不変条件ガード・下記注記あり） | `python -m pytest tests/test_provider_ui.py -k test_layer5_key_ordering_is_substring_safe -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**サンプリング連続性:** 自動 `<automated>` を持たないタスクは 2-01-01（checkpoint:decision）と
2-04-3A / 3B / 3C（checkpoint:human-verify）の計 4 件。

2-04-3A / 3B / 3C は 02-REVIEWS.md MEDIUM-14（1 つの巨大な human-verify では失敗時の
原因切り分けが難しい）への対応で 3 分割したため、形式上は「自動 `<automated>` を持たない
タスクが 3 連続」に見える。ただし次の 2 点により実質的なサンプリング欠落は生じない:

1. これらの checkpoint は**コードを 1 行も変更しない**（人手による観察のみ）。実装ドリフトが
   発生する余地がないため、間にサンプリング点が無いことのリスクがそもそも成立しない。
2. それでも「指摘に基づく修正」が発生し得るため、**各 checkpoint の acceptance_criteria に
   フルスイート（失敗 0 件）の再実行を明示的に組み込んだ**。結果として 3A / 3B / 3C の
   各承認時点でフルサンプリングが 1 回ずつ走る。

したがって Nyquist 上の実効サンプリング間隔は checkpoint 1 件ぶん（コード変更ゼロ区間）を
上限とし、要件を満たす。

**2-AUD-02（IN-01 ガード）の検知力に関する正直な注記:**

事後監査で追加した `test_layer5_key_ordering_is_substring_safe` は、現在の
`OCR_PRICE_TABLE`（16 キー）に対しては **部分文字列ペアが 1 件も存在しない**ため
アサーション本体が一度も評価されない（空振り＝vacuous）。
現時点のテーブルについて何かを検証しているわけではない。

このテストの価値は将来の混入防止にある。監査中に 2 パターンのミューテーションで確認した:

- 汎用キー `"gpt-5"` を `"gpt-5-nano"` **より前**に追加 → **RED**（IN-01 が警告した実シナリオを検知）
- 同じキーを最後尾（安全な順序）へ追加 → **GREEN**（誤検知しない）

つまり「今のテーブルが安全であること」ではなく「今後キーを追加したとき順序を誤ったら落ちること」を
固定するガードである。IN-01 の指摘（実装は docstring と異なり完全一致優先ではなく宣言順ループ）
自体は実装側で未解消のまま残っており、これはレビューで info 深度と判定され本フェーズでは
意図的に実装変更しない方針を採ったため（`_lookup_price` の実装は無変更）。

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
| OpenAI 実キーでのモデル一覧取得・設定 UI・キー非永続化 | V190-OAI-01/02/03/09 | 実 API キーが必要（CI 不可）＋ Tkinter 実描画 | **02-04 Task 3A**。OpenAI 選択 → セッション限定キー入力 → モデル一覧取得（先頭が推奨モデル・非チャットモデルの混入が無いことを目視）→ reasoning effort 欄の表示切替と候補値 → 不正 org 値で Apply が明示エラー中断 → アプリ再起動でキー欄が空になることと `pagefolio_settings.json` にキーが無いことを確認 |
| 送信先確認・コスト確認ダイアログの表示と単価の突き合わせ | V190-OAI-04/05/06/11 | Tkinter モーダルダイアログ（GUI 操作）＋ 公式価格ページ参照 | **02-04 Task 3B**。OpenAI 選択状態で単発 / バッチ OCR を起動し、`api.openai.com` の明示・対象ページ数・概算コストが読める形で出ること、「いいえ」で送信されないこと、未確認モデル選択時の注記が出ることを目視。あわせて `OPENAI_PRICE_SOURCE['url']` の公式価格ページと記録単価を突き合わせる（02-REVIEWS.md MEDIUM-16） |
| フォールバック発動時の送信先再確認 | V190-OAI-07 | 一次プロバイダの致命的失敗を実環境で誘発する必要あり | **02-04 Task 3C**。**実コードで確認した発火条件に基づき**、一次プロバイダを LM Studio にして到達不能 URL `http://127.0.0.1:9` を指定 → `ConnectionError` で fatal → OpenAI 表示名と `api.openai.com` を含む確認が再提示され、承認後に OCR が完走することを確認。（無効な API キーによる 401 は `RuntimeError` になり fatal にならないためフォールバックは発火しない — `pagefolio/ocr_providers/errors.py:115-131` / `pagefolio/ocr_pipeline.py:249-269`） |
| モデル ID の実在確認と能力・価格の確定（D-09 + HIGH-1/HIGH-2） | V190-OAI-03/09/12 | 実 API キーまたは公式ドキュメント参照が必要 | 02-01 Task 1 の checkpoint:decision。**Stage A**（`GET /v1/models` で ID 実在）と **Stage B**（公式モデルドキュメントまたは最小実画像リクエストで vision 入力 / `max_completion_tokens` / `temperature` / `reasoning_effort` と許容値域、および公式価格ページから単価・単位・通貨）を別工程で実施し、`02-CAPABILITY-MATRIX.md`（13 列）へ記録する |

### Manual-Only 実施結果（事後監査 2026-08-11 時点）

| Behavior | 結果 | 根拠 |
|----------|------|------|
| 設定 UI・モデル一覧・キー非永続化（Task 3A） | ✅ 合格 | 02-04-SUMMARY.md「Manual-Only Verification 実施結果」。手順 1〜11 をユーザーが実機で実施し承認 |
| 送信先確認・コスト確認・単価突き合わせ（Task 3B） | ✅ 合格（1 回差し戻し） | 初回は `HTTP 401`（APIキー未送信）で不合格 → `36e7cc2` で修正後に再検証し承認。**単価突き合わせは「差し戻しに値する不一致は見つからなかった」という消極的確認**であり、数値一致の積極的証明ではない（02-04-SUMMARY.md の原文どおり） |
| フォールバック発動時の送信先再確認（Task 3C） | ✅ 合格 | 手順 1〜8（`http://127.0.0.1:9` による `ConnectionError` 誘発）をユーザーが実機で実施し承認 |
| モデル ID・能力・価格の確定（Task 1 decision） | ✅ 実施済（option-b） | `OPENAI_API_KEY` が実行環境に無く option-a（実 API）不可のため、CONTEXT.md D-09 が事前承認した公式ドキュメント経路を採用。`02-CAPABILITY-MATRIX.md` の 13 列充足を `python -c` で検査 |

**Manual-Only のまま残る項目:** 上記 4 件はいずれも実 API キー・Tkinter 実描画・外部価格ページ参照を
必要とし CI 化できない。本監査でも自動化していない（自動化には実キーの CI 投入が必要で、
T-02-14（実機確認でのキー漏洩）のリスク面を悪化させるため）。

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies（checkpoint 4 件を除く全 10 タスクが自動コマンド保持）
- [x] Sampling continuity: 2-04-3A/3B/3C の 3 連続 checkpoint は「コード変更ゼロ + 各 checkpoint の acceptance_criteria にフルスイート再実行を組み込み」で実効サンプリングを担保（上記「サンプリング連続性」参照）
- [x] Wave 0 covers all MISSING references（新規テストファイルは同一 Wave 内・同一タスクで作成される）
- [x] `02-CAPABILITY-MATRIX.md` は 02-01 Task 1 が作成し、これを参照する最初のタスクは同一プラン内の Task 2 であるため MISSING 依存は生じない
- [x] No watch-mode flags（全コマンドが `-q` / `-x` の 1 回実行）
- [x] Feedback latency < 60s（Full suite 実測 47 秒）
- [x] `nyquist_compliant: true` set in frontmatter
- [x] 全 14 行の Per-Task Map が実測 green（自動 10 + 事後追加 4）／pending 0 件
- [x] 参照テストクラス 49 件の実在を機械確認（`grep -c "class <name>\b"` が全件 ≥1）

**Approval:** planner sign-off 2026-08-11（初版）／ 2026-08-11 更新（02-REVIEWS.md 反映:
テストゲートを絶対ゲート＝失敗 0 件へ変更、human-verify を 3 分割、`ast.parse` 構文ゲート追加、
能力マトリクスを Manual-Only へ追加）／ **2026-08-11 `/gsd-validate-phase` 事後監査で
`status: validated` へ昇格**（下記監査記録参照）。

---

## Validation Audit 2026-08-11

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |

**監査対象 HEAD:** `e0c53c2`（Phase 2 の全 4 プラン + コードレビュー修正 `e9289b6` を含む）

### 検出したギャップと対応

| # | 種別 | 内容 | 対応 |
|---|------|------|------|
| G-1 | MISSING | `ocr_dialog.py::_summary_worker` の `OCRRetryableError` リトライ待機経路が無テスト。バッチ側は CR-01 修正（`e9289b6`）で固定されたが単発側は未固定で、02-REVIEW.md **WR-01** が要求した「リトライ待機のパリティ担保」が未達だった | `tests/test_batch_ocr_dialog.py::TestSingleShotSummaryRetrySleepParity`（2 件）を追加。**ミューテーション検証済**: `interruptible_sleep(delay, self._summary_cancel_flag.is_set)` から `.is_set` を落とす（CR-01 と同型の bug を単発側へ注入）と 2 件とも RED、revert で GREEN |
| G-2 | MISSING | `_lookup_price` の宣言順依存（02-REVIEW.md **IN-01**）に不変条件テストが無い。誤単価は T-02-18（誤単価による同意の質の毀損）に直結 | `tests/test_provider_ui.py::TestOpenAIPriceProvenance::test_layer5_key_ordering_is_substring_safe` を追加。**ミューテーション検証済**（RED/GREEN 両方向）。ただし現テーブルに対しては空振り＝将来混入ガード — 上記「2-AUD-02 の検知力に関する正直な注記」参照 |
| G-3 | 未マップ | `36e7cc2`（APIキー未送信バグ）・`e9289b6`（CR-01）の回帰テストは実在するが Per-Task Map に行が無かった | `2-04-FIX` / `2-CR-01` の 2 行を Map へ追記（テスト新規作成は不要・実在確認のみ） |

### 実測

- フルスイート `python -m pytest -q --basetemp=...` → **1387 passed / 0 failed**（監査前ベースライン 1382 + 追加テスト 3 件 + フレーキー解消分 2 件）
- `ruff check .` → All checks passed／`ruff format --check .` → 90 files already formatted
- 自動コマンド 10 件を個別実行し全件 green（最長 6.4 秒 = `2-02-03`）
- **実装ファイルは無変更**（`git diff pagefolio/` が空。監査で追加したのはテストのみ）

### 未解消のまま残す項目（意図的）

- **IN-01 の実装側**: `_lookup_price` の docstring（「完全一致優先」）と実装（宣言順ループ）の乖離は
  未修正。レビュー深度 info かつ本フェーズのスコープ外と判断し、テストによる将来ガードのみを設置した。
  実装の是正が必要なら Phase 3 以降で扱う
- **WR-02**（バッチサマリが `OCRContextLengthError`/`TimeoutError` を単発側のように区別しない）:
  ユーザー体験の一貫性に関する warning であり、フェーズ要件（V190-CAT/OAI 系 15 件）のいずれにも
  紐づかないため本監査の対象外。Nyquist 上のサンプリング欠落ではない
- **Tcl/Tk 環境フレーキー**: Phase 3（V190-QA-01）が blocking gate として引き取る既知課題
