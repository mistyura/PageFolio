---
phase: 03-qa-release-gate
plan: 02
subsystem: test-infrastructure
tags: [pytest, tkinter, release-gate, investigation, claude-md, no-code-change]

requires: []
provides:
  - ".planning/phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md — TclError/STATUS_BREAKPOINT 2症状の実機再現試行ログと反証データ（現行HEADでは非再現・累計17回連続グリーン）"
  - "CLAUDE.md『## リリースゲート（全テスト完走条件）』— 単一プロセス pytest -q（1398件）完走を合格条件とする日常実行手順"
affects: [03-03-uat-release]

actuals:
  tokens: 4055
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "「調べる前に直さない」— 予防的コード変更の前に必ず現行HEADで再現試行を行い、再現有無に応じて分岐する（D-05）"
    - "反証データを一次データ（実行コマンド全文・passed/failed/error件数・クラッシュ有無）として成果物に残し、次マイルストーンが同じ地面を掛け直さないようにする（D-02）"
    - "日常手順（CLAUDE.md）と詳細な実験ログ（フェーズ成果物）の記録先を分離する（D-07）"

key-files:
  created:
    - .planning/phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md
  modified:
    - CLAUDE.md

key-decisions:
  - "Task 1（現行HEAD再現試行10回連続実行）でTclError/STATUS_BREAKPOINTの両症状とも0/10で非再現だったため、Task 2は分岐A（D-05: いずれも再現しなかった場合）を採用。tests/conftest.pyへの修復コード追加はゼロ（D-06）"
  - "D-03の2仮説（pytest assertion rewriting / tests/test_pdf_ops.pyの二分探索）は再現しなかったため検証していない。『検証していないものを検証して外れたと書かない』というD-02の趣旨に従い、未着手・次回再発時の入口として保存する形で記録した"
  - "CLAUDE.mdのリリースゲート合格条件は『単一プロセス完走』（分割実行なし）を採用。10回連続実行で非再現が確認できたため、D-01が定める2条件（単一プロセス一発 or 分割実行）のうち単一プロセス側が成立すると判断した"
  - "CI/別マシン確認（PITFALLS.mdのチェック項目）は本プロジェクトに存在しないため対象外とし、D-08が定める『同一環境での複数回連続実行』（本プラン10回+リサーチ7回=累計17回）を統計的代替とした"

requirements-completed: [V190-QA-01]

coverage:
  - id: D1
    description: "現行HEADに対しフルテストスイートを10回連続実行し、各回の実行コマンド・passed/failed/error件数・クラッシュ有無を一次データとして記録した"
    requirement: "V190-QA-01"
    verification:
      - kind: manual
        ref: "03-TEST-ENV-INVESTIGATION.md ## 再現試行ログ（10行の表・全ログをgrep -l Windows fatal exception / grep -l TclErrorで機械的に走査し一致0件を確認）"
        status: pass
    human_judgment: false
  - id: D2
    description: "STATUS_BREAKPOINTクラッシュとTclErrorセットアップERRORが同じ実験内で並行観測されつつ別症状として別々に結論づけられている"
    requirement: "V190-QA-01"
    verification:
      - kind: other
        ref: "grep -c '^## 症状 ①' / '^## 症状 ②' / '^## 結論' (=2) 03-TEST-ENV-INVESTIGATION.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "再現しなかったためpagefolio/にもtests/にもコード変更を入れず『現行環境では解消済み』と一次データ付きで記録して閉じた"
    requirement: "V190-QA-01"
    verification:
      - kind: other
        ref: "git diff --stat -- pagefolio/ tests/ requirements.txt pyproject.toml（出力ゼロ）"
        status: pass
    human_judgment: false
  - id: D4
    description: "リリースゲートの合格条件がCLAUDE.mdから実行可能な形で読め、そのコマンドが失敗0件で完走する"
    requirement: "V190-QA-01"
    verification:
      - kind: unit
        ref: "CLAUDE.md記載コマンド ./.venv/Scripts/python.exe -m pytest -q --basetemp=... の実行結果（1398 passed in 32.70s）"
        status: pass
    human_judgment: false

duration: 約20分
completed: 2026-08-11
status: complete
---

# Phase 3 Plan 2: テスト実行環境の切り分け・リリースゲート確定 Summary

**現行HEAD（1398件収集）に対しフルテストスイートを10回連続実行した結果、TclError/STATUS_BREAKPOINTの両症状とも非再現（累計17回連続グリーン）と確認し、コード変更ゼロで「解消済み」記録を確定。リリースゲートの合格条件（単一プロセス完走）をCLAUDE.mdへ記録した（V190-QA-01）**

## Performance

- **Duration:** 約20分（pytest 10回連続実行の実行時間 約6分半を含む。git commit ログ基準 `51ee276` → `97636d2`）
- **Tasks:** 3 / 3
- **Files modified:** 2（`03-TEST-ENV-INVESTIGATION.md` 新規・`CLAUDE.md`）

## Accomplishments

- 現行 HEAD（03-01 適用後・1398件収集）に対し `pytest -q --basetemp=...` を **10回連続実行**し、各回の passed/failed/error件数・クラッシュ有無・TclError有無を実行ログから機械的に抽出して記録した（Task 1）。全10回で `passed=1398, failed=0, error=0`、`grep -l "Windows fatal exception"` / `grep -l "TclError"` の一致ファイル 0件を確認
- STATE.md「Blockers/Concerns」が記録する2症状（① TclError セットアップ ERROR・② STATUS_BREAKPOINT クラッシュ）を節を分けて別々に観測・結論づけ（D-04）。両症状とも非再現のため分岐A（D-05）へ進み、`tests/conftest.py` への修復コード追加はゼロ（Task 2）
- 03-RESEARCH.md のリサーチセッション7回連続グリーンと本プランの10回を合算し、**累計17回連続グリーン**（再現率0.7の事象が17回連続で一度も出ない確率 ≈1.3×10^-9）という統計的根拠を残した
- D-03 の2仮説（pytest assertion rewriting / `tests/test_pdf_ops.py` の二分探索）は「再現していないため検証不能」として明示的に未実施のまま記録（検証したと嘘をつかない）
- CI/別環境確認が本プロジェクトに存在しないため対象外である理由を明記（D-08）
- `CLAUDE.md`「## 変更時のチェックリスト」直下に独立セクション「## リリースゲート（全テスト完走条件）」を新設し、単一プロセス `pytest -q`（1398件）の完走を合格条件として記録。`--basetemp` の位置づけ・禁止事項（テスト削除/skip/`-k`/`--ignore` による静かな除外の禁止）・調査レポートへの根拠リンクを明記（Task 3・D-07）
- CLAUDE.md 記載のゲートコマンドを実際に実行し、1398 passed（失敗0件）で完走することを確認済み

## Task Commits

1. **Task 1: 現行HEADでの再現試行（フルスイート10回連続実行）と一次データの記録** - `51ee276` (docs)
2. **Task 2: 判定に応じた切り分け（分岐A: いずれも非再現）の確定** - `f42164e` (docs)
3. **Task 3: リリースゲートの合格条件と実行手順をCLAUDE.mdへ記録（D-07）** - `97636d2` (docs)

## Files Created/Modified

- `.planning/phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md` - 新規。対象環境・症状①②の初出記述と今回の観測結果・10行の再現試行ログ・現時点の判定・結論①②・未解明のまま残るもの・検証しなかった仮説と理由・対象外とした確認項目・Task1/2統合判定サマリ
- `CLAUDE.md` - 「## リリースゲート（全テスト完走条件）」節を新設。既存「## 変更時のチェックリスト」の `pytest` 項目からこの節を参照するよう最小限だけ調整

## Decisions Made

- **分岐A採用（Task2）:** Task1で両症状とも0/10で非再現だったため、D-05の「再現しなければコード変更ゼロで解消済みと記録して閉じる」を適用。予防的な `TCL_LIBRARY`/`TK_LIBRARY` ハードコードは入れていない（PITFALLS.md Pitfall 13 の警告どおり不採用を維持）
- **D-03仮説の非検証を明示:** 「検証していないものを検証して外れたと書かない」という原則に従い、`## 検証しなかった仮説と理由` という専用節を設けて未着手であることを明記した（Claude's Discretion範囲内の追加節。プラン本文が明示的に要求する見出しは分岐Aで `## 結論①/②`・`## 未解明のまま残るもの`・`## 検証しなかった仮説と理由`・`## 対象外とした確認項目` の4種）
- **リリースゲートは単一プロセス完走を採用:** D-01は「単一プロセス一発 or 分割実行」の2択を許容するが、10回連続グリーンという十分な統計的根拠が得られたため分割実行への切り替えは行わず、単一プロセスのコマンドのみをCLAUDE.mdへ記録した

## Deviations from Plan

None - 計画どおりに実行完了。Task 1/2は当初1回のWrite操作で一括作成する案も検討したが、プランのタスク粒度（Task1=一次データ記録・Task2=分岐判定と結論追記）に忠実に沿うため、ファイルをTask1相当の内容で先にコミットし、Task2でその追記分を別コミットとして積み上げる形にした（コミット粒度をプランのタスク境界に一致させるための実装判断であり、プランの`<action>`/`<acceptance_criteria>`自体からの逸脱ではない）。

## Issues Encountered

- リポジトリルートに `UsersshdwfAppDataLocalTemppfb/` という追跡外ディレクトリ（過去セッションの basetemp パス誤解釈によるものと推測される pytest tmp 成果物の残骸）が存在し、`ruff check .` を無限定で実行すると31件のエラーが検出された。これは本プランのファイル変更範囲外であり、`pagefolio/`・`tests/` に限定した `ruff check` では `All checks passed!` を確認済み。このディレクトリの削除は本プランのスコープ外のため対応していない（`git status` には元々 untracked として現れており、本プランの実行前から存在していた）

## User Setup Required

None - 本プランは調査ログの新規作成とCLAUDE.mdへのドキュメント追記のみで完結し、新規依存・環境変数・外部設定を必要としない。

## Next Phase Readiness

- V190-QA-01 は完了。リリースゲートの合格条件（単一プロセス `pytest -q` 完走）が `CLAUDE.md` から実行可能な形で読め、根拠が `03-TEST-ENV-INVESTIGATION.md` へリンクされている
- `.planning/phases/03-qa-release-gate/03-03-PLAN.md`（V190-QA-03・遡及human-verify/UAT）へ進める。D-16が定めるバージョン文書同期（APP_VERSION等）はそちら側の作業範囲

## Self-Check: PASSED

- `test -f .planning/phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md` → FOUND
- `grep -c "^## 再現試行ログ" .planning/phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md` → 1（FOUND）
- `grep -c "^## 結論" .planning/phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md` → 2（FOUND）
- `grep -c "^## リリースゲート" CLAUDE.md` → 1（FOUND）
- コミットハッシュ `51ee276`/`f42164e`/`97636d2` は `git log --oneline --all` に存在（FOUND）
- `git diff --stat -- pagefolio/ requirements.txt pyproject.toml` → 出力空（FOUND・コード変更なしを維持）

---
*Phase: 03-qa-release-gate*
*Completed: 2026-08-11*
