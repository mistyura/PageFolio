---
phase: 3
slug: qa-release-gate
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-11
updated: 2026-08-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 対象プラン: `03-01` / `03-02` / `03-03` / `03-04`（全 13 タスク）。
> 本ファイルは確定済みプランの内容から書き起こしたものであり、数値・コマンドはプラン本文と一致させること。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1（`pyproject.toml` の `[tool.pytest.ini_options]` で `testpaths = ["tests"]`） |
| **Config file** | `pyproject.toml`（**編集禁止** — CLAUDE.md 禁止事項） |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest -q tests/test_toast.py tests/test_password.py tests/test_save_overwrite.py --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` |
| **Estimated runtime** | quick ≈ 5 秒 / full ≈ 35 秒（03-RESEARCH.md の 7 回連続実行の平均。実測値は 03-02 Task 1 で再取得する） |
| **Lint gate** | `ruff check . && ruff format --check .`（py ファイル編集時は必須） |
| **`--basetemp` の位置づけ** | `%TEMP%\pytest-of-shdwf` のロック競合回避専用。テストを 1 件も除外しない（`-k` / `--ignore` による絞り込みとは別物） |

---

## Sampling Rate

- **After every task commit:** Quick run command（保存経路を触るタスク＝03-01 Task 1）。ドキュメントのみのタスクは当該 `<verify><automated>` の grep コマンド
- **After every plan wave:** Full suite command（Wave 1〜4 の各末尾）
- **Before `/gsd-verify-work`:** Full suite must be green（失敗 0 件・ERROR 0 件・プロセスクラッシュなし）
- **Max feedback latency:** 約 35 秒（フルスイート 1 回ぶん。これを超えるサンプリング点は本フェーズに存在しない）
- **Human checkpoint 間のサンプリング:** 03-03 Task 2 / 3 / 4 は人の観測が判定の主体だが、各 checkpoint の `<verify><automated>` にフルスイートを置き、承認の前後で自動側が緑であることを担保する（3 連続で自動検証が欠落しない）

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Feedback Latency | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|------------------|--------|
| 03-01-01 | 01 | 1 | V190-QA-02 | T-03-01-01 / T-03-01-02 / T-03-01-03 | 再試行は確認・選択時点で束縛した確定パスへのみ書き込み、暗号化指定を落とさない。`doc` 未オープン時は書き込まない | unit（tracer / TDD） | `.\.venv\Scripts\python.exe -m pytest -q tests/test_toast.py tests/test_password.py tests/test_save_overwrite.py --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` | ✅ | ~5s | ⬜ pending |
| 03-01-02 | 01 | 1 | V190-QA-02 | T-03-01-01 / T-03-01-02 | `_save_as` / `_save_compressed` でも `encryption` を保持し、束縛パスが再選択で入れ替わらない | unit（TDD） | `.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` | ✅ | ~35s | ⬜ pending |
| 03-01-03 | 01 | 1 | V190-QA-02 | — | 判定基準（ROADMAP Success Criteria）と実装の食い違いを解消し、誤合否判定を防ぐ | docs-grep | `grep -c "前回確定した対象へ黙って再保存" .planning/REQUIREMENTS.md .planning/ROADMAP.md` | ✅ | <1s | ⬜ pending |
| 03-02-01 | 02 | 2 | V190-QA-01 | T-03-02-01 | ゲート判定を一次データ（10 回ぶんの実行コマンド・件数・クラッシュ有無）で裏付ける | integration（フルスイート 10 回連続） | `.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` | ✅ | ~35s ×10 | ⬜ pending |
| 03-02-02 | 02 | 2 | V190-QA-01 | T-03-02-02 / T-03-02-03 / T-03-02-05 | 修復は `tests/` 配下に閉じ、Tcl/Tk ライブラリパス環境変数の予防的ハードコードと新規 pip 依存を入れない | integration | `.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` | ✅ | ~35s | ⬜ pending |
| 03-02-03 | 02 | 2 | V190-QA-01 | T-03-02-01 | ゲート条件を実行可能な形で固定し、静かな除外でゲートを通す運用を禁じる | docs-grep + full suite | `grep -c "リリースゲート" CLAUDE.md`（記載コマンド自体の実行はフルスイートで担保） | ✅ | <1s / ~35s | ⬜ pending |
| 03-03-01 | 03 | 3 | V190-QA-03 | T-03-03-01 / T-03-03-03 | 遡及項目の文言を書き換えず、API キー値・フルパスを記録へ混入させない | docs-grep | `grep -c "^## 対象確定（現行照合）" .planning/phases/03-qa-release-gate/03-UAT-RESULTS.md` | ✅（Task 1 で新規作成） | <1s | ⬜ pending |
| 03-03-02 | 03 | 3 | V190-QA-03 | T-03-03-01 | 返信にフルパス・API キーを含めない | **human checkpoint（自動コマンドで挙動判定不可 — 判定は人の実機観測、記録先は `03-UAT-RESULTS.md`）**。併走するサンプリング点として `.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` を実行 | ✅ | ~35s（サンプリング点のみ） | ⬜ pending |
| 03-03-03 | 03 | 3 | V190-QA-03 | T-03-03-01 | 同上。「再現できず」を pass へ丸めない | **human checkpoint（同上・記録先 `03-UAT-RESULTS.md`）** + `.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` | ✅ | ~35s（サンプリング点のみ） | ⬜ pending |
| 03-03-04 | 03 | 3 | V190-QA-03 | T-03-03-01 / T-03-03-04 | 実 API 実行時にキー文字列・OCR 全文を記録へ残さない。キー未設定分は「未実施（理由）」 | **human checkpoint（同上・記録先 `03-UAT-RESULTS.md`）** + `.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"` | ✅ | ~35s（サンプリング点のみ） | ⬜ pending |
| 03-03-05 | 03 | 3 | V190-QA-03 | T-03-03-01 / T-03-03-02 | 結果は `pass` / `fail` / `未実施` の 3 値のみ。サマリ内訳の合計が対象確定表の行数と一致（黙って消えた項目がない） | docs-grep | `grep -c "^## サマリ" .planning/phases/03-qa-release-gate/03-UAT-RESULTS.md` | ✅ | <1s | ⬜ pending |
| 03-04-01 | 04 | 4 | —（D-16・要件 ID なし） | T-03-04-01 / T-03-04-04 | `APP_VERSION` を単一情報源とし、`pyproject.toml` を編集しない | smoke（実インポート） | `.\.venv\Scripts\python.exe -c "from pagefolio.constants import APP_VERSION; assert APP_VERSION == 'v1.9.0', APP_VERSION; print(APP_VERSION)"` | ✅ | <2s | ⬜ pending |
| 03-04-02 | 04 | 4 | —（D-16・要件 ID なし） | T-03-04-02 / T-03-04-03 | 既存エントリを壊さず追記し、件数は当セッションの実測のみを出典とする | docs-grep + full suite | `grep -c "APP_VERSION = v1.9.0" 開発履歴.md`（回帰確認はフルスイートで担保） | ✅ | <1s / ~35s | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**自動検証欠落の所在（意図的）:** 03-03 の Task 2 / 3 / 4 の 3 件のみ。いずれも Tk の実描画・実キーイベント・実 API 出力品質という自動化不能な観点であり、`checkpoint:human-verify` として設計されている（D-15）。3 件とも `<verify><automated>` にフルスイートを持つため、サンプリングの連続性（3 連続で自動検証なしにならない）は保たれている。判定そのものの記録先は `.planning/phases/03-qa-release-gate/03-UAT-RESULTS.md`。

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. — 新規テストフレームワーク導入・新規テストファイル新設・`MISSING` 参照はいずれも本フェーズに存在しない（`wave_0_complete: true`）。

補足（Wave 0 プランを立てない理由）:

- `tests/test_toast.py`（327 / 338 / 352 行付近）の 3 件のオブジェクト等価性アサーション（`retry_cb == app._save_file` 等）は D-11 の実装で意図的に壊れるが、**書き換えは 03-01 Task 1 / Task 2 の中で TDD の RED→GREEN として実施する**（別プランへ切り出さない）。03-RESEARCH.md「Wave 0 Gaps」が挙げた項目はこれに相当する。
- `tests/conftest.py` は既存。03-02 Task 2 の分岐 B で修復 fixture を追加する可能性があるが、これは切り分け結果駆動（D-05）であり事前の Wave 0 作業ではない。
- 新規 pip 依存（`pytest-xdist` / `pytest-forked` 等）は導入しない（V14-D-01）。

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ショートカット設定の実キーキャプチャ / 衝突拒否 / 保存直後の即時反映（3 項目） | V190-QA-03 | Tk の実キーイベントと実描画は自動テストで再現できない（`tests/test_shortcuts_dialog.py` はロジック層のみ担保） | `03-03-PLAN.md` Task 2 の `how-to-verify` 項目 1〜3。結果は `03-UAT-RESULTS.md` の `## 実施結果` へ転記 |
| 保存トースト再試行の実 UI 挙動（確認ダイアログ・ピッカーが出ないこと / 初回は出ること） | V190-QA-03（V190-QA-02 の実機確認） | トースト UI 上のボタン押下と実ファイルの排他ロックを伴うため自動化しない | `03-03-PLAN.md` Task 2 の `how-to-verify` 項目 4 |
| SettingsDialog 3 セクション表示 / LLMConfigDialog 見出し順序とプロバイダ切替 / 外側 Cancel での設定保持 / 拡大ポップアップの英語表示（4 項目） | V190-QA-03 | 実描画の見え方・見出し順序は目視でしか判定できない | `03-03-PLAN.md` Task 3 の `how-to-verify` 項目 1〜4 |
| Undo 復元失敗時の messagebox ブロック通知 | V190-QA-03 | 復元失敗の実機再現条件を人為的に作る必要がある。再現できない場合は pass ではなく「未実施（理由）」 | `03-03-PLAN.md` Task 3 の `how-to-verify` 項目 5 |
| OCRDialog の markdown 整形表示の見え方 | V190-QA-03 | 「プレーンテキストより読みやすい」の判定が主観的で自動化不能 | `03-03-PLAN.md` Task 4 の `how-to-verify` 項目 1 |
| プロバイダ別プロンプトの実 API 出力品質（Gemini 分 / Claude 分） | V190-QA-03 | 実 API・課金を伴う。`ANTHROPIC_API_KEY` は未設定のため Claude 分は「未実施（キー未設定）」で記録（D-14） | `03-03-PLAN.md` Task 4 の `how-to-verify` 項目 2 / 3 |
| LM Studio のモデル切替反映 / タイムアウト表示と実待機時間の一致 | V190-QA-03 | 外部プロセス（LM Studio）のログ確認と実時間の計測が必要 | `03-03-PLAN.md` Task 4 の `how-to-verify` 項目 4 / 5 |
| max_tokens クランプ / 429 リトライの実 API 検証（V16-QUAL-03） | V190-QA-03 | 課金またはレート制限の意図的な誘発が必要。実施できない場合は「未実施（理由）」 | `03-03-PLAN.md` Task 4 の `how-to-verify` 項目 6 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 13/13 タスクが `<verify><automated>` を持つ（03-03 の human checkpoint 3 件はフルスイートをサンプリング点として保持）
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — 自動検証が付かない連続区間なし（最長は 03-03 Task 2〜4 だが 3 件ともフルスイートを実行する）
- [x] Wave 0 covers all MISSING references — `MISSING` 参照ゼロ（既存 pytest インフラで全要件をカバー）
- [x] No watch-mode flags — 全コマンドが一発完了型（`--watch` / `-f` / watch mode を使用しない）
- [x] Feedback latency < 35s — 最長サンプリング点はフルスイート 1 回（約 35 秒）
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved（2026-08-11・plan revision iteration 1 で確定済みプラン 03-01〜03-04 から書き起こし）
