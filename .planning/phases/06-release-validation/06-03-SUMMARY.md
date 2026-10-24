---
phase: 06-release-validation
plan: "03"
subsystem: release-uat-tooling
tags: [uat-support, evidence-audit, fake-ocr, win32-ownership, fault-preparation]

requires:
  - phase: 06-release-validation
    provides: 06-01 の配布CLI(release-reportの全名/全hash manifest)と 06-02 の版同期・利用文書
provides:
  - tests/release_uat_support.py: prepare/start/peer/inspect/stop/audit/fault/serve-ocr/resume の検証CLI（製品をimportしない）
  - tests/release_fake_ocr.py: 127.0.0.1専用の合成OCR(待機/成功/エラー)と、埋込文字なし1page画像PDF・3page編集PDFの生成
  - tests/test_release_uat_support.py: 隔離・所有PID・合成OCR・設定障害準備・証拠監査の契約84件
  - 06-UAT-PREPARATION.md: 入口ごとの準備可否・観測限界・実EXEでの未実証点・証拠schema
affects: [06-04, 06-05, 06-06]

plan_head_before: cd8b905f1ae9b70b12c15d43ec1f6ab521d2ae1e
plan_head_after: 7536b8a8cf9385a6bde5f0cc0ea0f02385ddb957

actuals:
  tokens: 45852
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "配布manifest(不変tree)と明示fixture overlay(可変・宣言名のみ)を別manifestで管理し、未宣言差分はstartを拒否"
    - "回収はPID+プロセス生成時刻+image pathの再照合後に所有handleだけで行い、名前一括killをしない"
    - "auditは証拠を読むだけ(全証拠fileのbytes不変を試験)で、失敗・解釈不能はfail closed。成功でもphase_complete/release_allowedはfalse"
    - "設定障害は外部CreateFileW handle(共有なし/delete共有なし)と排他tmp衝突で作り、同等のOS probeで成立を確認。成立しなければNotEstablished(not-run)"

key-files:
  created:
    - tests/release_uat_support.py
    - tests/release_fake_ocr.py
    - tests/test_release_uat_support.py
    - .planning/phases/06-release-validation/06-UAT-PREPARATION.md
  modified: []

key-decisions:
  - "audit入力のschema(BUILD/PROTECTION/MANUAL/EVIDENCE/RELEASE-GATE)は06-UAT-PREPARATION.mdを正本とし、後続の06-04〜06-06担当がそれに従って書く。RELEASE-GATE.mdはrelease-gate付きjsonコードブロックを機械可読部分とする"
  - "fake OCRは描画結果のhashを事前に確定できないため、既定は『最初の1画像をp1へ束縛し、対象ページ数を超える別画像は拒否』。事前登録hashがあれば厳格モード。合成入力の暗号学的証明ではなく、loopback限定・外部転送なし・画像非保存で担保"
  - "要件V110-QA-01/QA-02/DIST-03は、実配布EXE(06-04)・人手受入(06-05/06-06)が未了のためmark-completeしない"

requirements-completed: []

duration: 約3時間（全件ゲート2回=各約6分を含む）
completed: 2026-10-24
status: complete
---

# Phase 6 Plan 03: 実配布EXEの外部観測とfake OCR接続の準備 Summary

**未改変の配布EXEを完全copy・hash固定で隔離し、所有PID(+生成時刻)で起動/回収/観測する検証CLIと、既存Ollama設定へ接続できるloopback合成OCR・設定障害(外部lock/tmp衝突)の準備経路、および5モードの読取専用証拠auditを実装した。準備ツールの合格であり、実配布EXEの実証・人手passではない。**

## Performance

- **Tasks:** 2/2（tdd指定だが、実装を先に書いてから試験を同じ作業内で整えた。下記「計画との差異」）
- **Commits:** 2（measured: `cd8b905..7536b8a`）

## Accomplishments

- **06-03-01（隔離・所有・監査）:** `prepare` が `release-report.json` の全名/全hash manifestと配布treeを照合し、リンク/reparse/特殊ファイルを拒否して完全copyする（copy後も配布元の全treeを再照合）。配布manifestとfixture overlay（`pagefolio_settings.json`・2prompt・`.tmp`衝突用の宣言名のみ）は別manifest。未宣言ファイル・配布差分があれば `start` は起動せず拒否。`reset_for_case` は同一Gで所有copyを再利用しoverlayを元へ戻して再照合、同一性不明なら新copyを要求。
- 固定production namespace（`Local\PageFolio.Startup.Owner/.State`）の既存ownerを読取だけで検出して拒否（調査不能も「あり」扱い）。`start` は引数なしで起動しPID・生成時刻・session・elevation・image・foregroundを保存、imageが想定EXEと異なれば**自分の子だけ**回収して拒否。`peer` は一次ownerの生存・同一性とowner確立を確認した場合のみ起動し、主対象(final-release-candidate)と相手(tracer/同版copy)を別欄に記録。`stop` はWM_CLOSE→診断保存→所有handleで終了の順で、PID+生成時刻+imageが一致しなければ触れない（無関係processが無傷であることを試験）。観測者のPython/Tkと同梱report由来のEXE内蔵版は別欄。
- **audit（6モード・相互排他）:** `--allow-pending`（構造のみ・記入済みpassの妥当性は検査）、`--require-pass`（IDをカタログで全subrowへ展開。空指定・未知ID・宣言不足・行欠落・回答不足・hash不一致・not-run/fail・unit/fault-injectionの実機昇格を拒否）、`--build-only`（記録されたoutput-rootの初回/再buildの異なる2run・第三build不可・tracerは数えない・report/同梱hash・history・保護名不在・サンプル/ガイド/docsのSHA。buildを呼ばずmtime/sizeも不変）、`--preparation-only`（保護3名・起動・更新/衝突・1page実接続・native modal・X01〜X05成立・run参照の双方向照合・接続実証のW04転記禁止）、`--for-handoff`（親の4ゲートだけpendingを許容。既知high未解消・fail・未知pending・対象不一致・stale・品質失敗は不合格）、指定なし（最終監査。4ゲート実走反映・ASVS1未評価0・Nyquist実走・未解除事項の根拠付き評価）。全モードの成功出力は `phase_complete=false` / `release_allowed=false`。W12bは主対象のfinal hashとtracer peerの来歴/別版/別hashを独立欄で検査し、主対象欠落・tracer主対象・同版copyの別版主張を拒否。
- **06-03-02（合成OCR・設定障害）:** `FakeOcrServer` は127.0.0.1専用（他hostは構築時拒否）、クライアント実装を持たず外部転送なし。`GET /v1/models` と `POST /v1/chat/completions` が既存 `OllamaProvider` の形状で動くことを実provider呼び出しで確認。hold/release（run内flag fileまたはAPI）、画像hash+page ID+attempt IDの記録、再送を元attemptを消さず残し通常1POST期待を未合格にする、対象外画像・非PNG・非合成入力の拒否、待機上限<provider timeout、429/5xx応答の禁止を実装。`ocr_settings` は `build_provider` が実際に消費するキー（ollama・並列1・fallback無効）で、サマリは自動起動しない。
- 設定障害 `missing/corrupt/unreadable/save-write/save-replace` を外部handle・排他tmp衝突で作り、同等probe（共有違反32）でobserver PID+生成時刻・access/share flagsを記録。製品の `_load_settings_result`/`_save_settings` が各障害を想定どおり（missing/corrupt/unreadable、保存失敗で原本不変・所有tmpのみ消去・先置きtmpは非削除）に扱うことをPython側で確認。tmp衝突は書込開始前失敗と明記。成立しなければexit 3(not-run)。
- 中断/再開: `save_resume_state`/`check_resume`/`supersede_rows`（元passを残し`superseded_by`/理由を追記し新世代not-run行を作る）。

## Task Commits

1. **Task 06-03-01:** `ad13ced` feat(06-03): 未改変配布EXEの隔離copy・所有PID・証拠auditを実装（fake OCRモジュールはimport依存のため同梱）
2. **Task 06-03-02:** `7536b8a` feat(06-03): 既存Ollama設定経由の合成OCRと設定障害の準備経路を固定

## 検証結果(実測)

| 項目 | 結果 |
| --- | --- |
| Task 1 局所 (`TestIsolation`/`TestOwnership`/`TestEvidenceAudit`) | 58 passed（commit前、Task 1のcommit内容と同一のtest file） |
| Task 2 局所 (`TestFakeOcr`/`TestSettingsFaultPreparation`) | 25 passed |
| `tests/test_release_uat_support.py` 全体 | 収集84件（symlink権限が無い環境ではjunctionへ代替。いずれも作れない時のみskip） |
| 変異確認 | 『fixtureの実EXE昇格拒否』『stopの同一性照合』を一時的に無効化すると該当試験が失敗することを確認（その後元へ復元済み） |
| Ruff check → format → 再check → AST | 全合格（117 files）。LF確認済み（`git ls-files --eol` で i/lf w/lf） |
| Task 1 commit前 全件（単一プロセス・native・commit内容と同一bytes） | **1944 passed, 1 warning in 364.82s (0:06:04) / EXIT=0**。basetemp `C:\Users\shdwf\AppData\Local\Temp\pf06_03_t1_full_*`（`$TEMP/t1_basetemp.txt` 参照）、ログ `06-03-task1-full.txt`。-k/--ignore/skipによる除外なし |
| Task 2 commit前 全件（単一プロセス・native・commit内容と同一bytes） | **1969 passed, 1 warning in 361.39s (0:06:01) / EXIT=0**。basetemp `C:\Users\shdwf\AppData\Local\Temp\pf06_03_t2_full_a415ec3d9adf4122`、ログ `06-03-task2-full.txt`。除外なし |

Tcl/Tk同種失敗・ERROR・クラッシュ・DEP-05/owner_missing/通知前景不一致の再発は2回の全件とも観測されなかった。原因が未解決であることは変わらず、成功を解除や承認へ読み替えない（CLAUDE.mdの症状①は再発し得る）。

## Deviations from Plan

### 計画との差異

**1. [手順] TDDのRED先行は行わなかった**
- 計画は「TestIsolation/TestOwnership/TestEvidenceAuditを先に作り」と指定するが、audit schemaと隔離・所有の設計が相互依存していたため、実装と試験を同じ作業内で整えた。個別のREDコミット・RED出力は保存していない。代わりに、重要な拒否条件（実EXE昇格・stopの同一性照合）を一時的に無効化して該当試験が失敗することを確認した。
**2. [コミット境界] Task 1のcommitにfake OCRモジュールを同梱**
- `release_uat_support.py` が `release_fake_ocr.py` をimportするため、Task 1のcommitに `tests/release_fake_ocr.py` を含めた（試験は `TestFakeOcr`/`TestSettingsFaultPreparation` を除いたtest fileでcommit前の全件ゲートを実施。その後Task 2でそれらを追加）。
**3. [スキーマ確定] 後続計画が書く証拠のschemaを本計画で確定した**
- 06-04〜06-06の台帳は未作成のため、auditが読む各JSONの項目を `06-UAT-PREPARATION.md`「証拠schema」に定義した。06-05-01が作るケースカードの全展開は `TestCaseCoverage` の責務で、auditの宣言下限（W01の条件、W02の条件、W12aの9行、W12bの主対象、W12a以外は実EXE入口の行）はそれより粗い。06-04以降の担当が項目名を変える場合は本ツールとの同時修正が必要。
**4. [fake OCRの限界] 合成入力判定**
- EXE内蔵PyMuPDFの描画結果hashを事前確定できないため、既定は最初の1画像をp1へ束縛する方式。事前登録hash（厳格モード）は用意済み。06-04-02で実EXEの描画hashを得られれば厳格モードへ切り替え可能。

### Auto-fixed Issues

**1. [Rule 1 - Bug] `faultコマンド` がoverlay宣言と実ファイルの不整合を作った**
- **Found during:** Task 2
- **Issue:** `corrupt`/`save-write` で実bytesを書いた後にoverlay manifestへ宣言しておらず、`start` が未宣言差分として拒否する状態になり得た。
- **Fix:** 成立後に実bytesをoverlay正本として宣言。全5種で `verify_copy` が ok かつ overlay 差分なしになることを試験。
- **Commit:** 7536b8a

## 既存dirty差分の保全(R06-12)

開始時のhash控え（`.planning/STATE.md`、`requirements.txt`、`tests/test_startup_windows.py`、`開発履歴.md`、`.planning/config.json`、`.planning/state.json`）を2回のcommit後に再照合し、すべて同一（task由来のstageは作成した4ファイル+追記した2ファイルのみ）。全file add・既存dirtyのcommit/取消は行っていない。SUMMARY/STATE/ROADMAPの更新は別途の記録commitで扱う。

## Authentication Gates

なし。

## Known Stubs

なし。

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: network-listener | tests/release_fake_ocr.py | 127.0.0.1の空きportで待機する検証用HTTPサーバ。非loopbackは構築時拒否・クライアント非実装・画像非保存で計画のT-06-07の範囲。常駐させる場合は`serve-ocr`の停止flagで終了する運用 |

## 既知の制限・次への申し送り

- **本計画の合格は検証ツールの実装合格**であり、実配布EXE（06-04で初めて作る）への接続・native modal・lock成立、W01〜W12・WR-01・X01〜X06の人手passは**すべて未実施(not-run)**。build成功・準備完了・人手pass・Phase完了は別の状態。
- 06-04-01は `06-BUILD-EVIDENCE.json` を、06-04-02は `06-PROTECTION-EVIDENCE.json` と準備カードの `run-ref:` 行を、本ツールのschema（`06-UAT-PREPARATION.md`）どおり書くこと。`audit --build-only` は記録したoutput-rootを読むので、実行時に`dist`を決め打ちしない。
- Win32の観測（foreground・window・elevated・session）は、実機の対話sessionで`inspect`した値を使う。この計画の試験は`cmd.exe`のcopyを擬似EXEとして使うtmp_path内のfixtureで、実配布EXEの証拠ではない。
- 05-CONTEXT D-19/20/21由来のW05b・X05は、06-05-01のカードで操作手順に展開される。本計画は準備経路（hold/release、外部lock）までを用意した。
- Ruff等の依存版表記の同期（06-02で見送り）は本計画の範囲外のまま。

## Self-Check: PASSED

- 作成ファイル: tests/release_uat_support.py, tests/release_fake_ocr.py, tests/test_release_uat_support.py, .planning/phases/06-release-validation/06-UAT-PREPARATION.md — すべて存在
- コミット: ad13ced, 7536b8a — HEAD の祖先として存在
