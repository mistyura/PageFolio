---
phase: 06-release-validation
reviewed: 2026-11-06T12:17:57Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - .planning/phases/06-release-validation/06-05-record-w05c-exe.cjs
  - tests/test_w05c_exe_evidence.py
  - .planning/phases/06-release-validation/06-W05C-EXE-COLLECTION.md
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
  necessity: 0
status: clean
---

# W05c 実配布 EXE 採用コードレビュー

## Summary

新規 helper・隔離試験・採取手順を標準深度で照合し、初回の CR-01〜04 と実受入後に見つかった CR-05 はすべて修正差分で解消した。レビュー対象に未解決の指摘はない。実 EXE は単発採取と利用者の7点回答、回収後の別メッセージ「採用してよい」を経て、`W05c/quit-no@production-exe` の1行が正式 `pass` になった。現行台帳は必須108行中30 `pass`・78 `not-run`、W11対象外2行 `not-run` であり、`release_allowed=false` を維持する。

根拠として `tests/release_uat_support.py:885-975,1065-1205,1208-1251,1276-1335,2559-2560,2701-2723` の実 schema と CLI、既存 EXE helper `06-05-record-w01-exe.cjs:29-40`、`06-UAT.md:947-975`、`06-W05C-RETRY-POLICY.md:101-108` を読取確認した。今回の限定差分は `tests/release_uat_support.py:1707-1759` の共通監査契約と、実台帳 `06-MANUAL-EVIDENCE.json:8658-8747` に照合した。実 EXE の raw copy 6件は `06-05-evidence/W05c_quit-no_at_production-exe-20261106T120952Z-raw/copies.json` 記載 hash とすべて一致した。RED 1 failed→GREEN 38 passed、全体 Ruff 149ファイル、対象 AST・Node 構文と `audit --require-pass W05c`／`--allow-pending` の成功は親の実行結果を再利用した。こちらでは pytest・GUI・EXE・audit を再実行していない。新試験追加後の全件 pytest は親が後続で実施予定である。

## Narrative Findings (AI reviewer)

### 2026-11-06 修正再監査

- **CR-01 fixed:** 手順 `06-W05C-EXE-COLLECTION.md:16-26` は CLI の JSON を `ConvertFrom-Json` で読んでから絶対 run path、所有 tmp、manifest の存在を検査する。`release_uat_support.py:2559-2560,2704-2715` の実出力形式に合う。既存 UAT カードの参照コマンドも親が整合済み。
- **CR-02 fixed:** 手順 `06-W05C-EXE-COLLECTION.md:37-80` は確認ダイアログを監視 job が検知した後にのみ No を依頼し、同一 owner のダイアログ消失を検知した時点で `inspect` を同期実行する。`Wait-Job` の成功と `after_no` の前景確認より前にチャット回答を求めない。`release_uat_support.py:1208-1251` の `inspect` は外部 PID・window・実 foreground をその場で保存する。helper は No 直後だけ一次前景を要求し (`06-05-record-w05c-exe.cjs:126-128`)、回答後の前景が別 PID でも owner/peer の同一性を独立に照合する (`同:103-125`)。切替後の別前景は試験 fixture `tests/test_w05c_exe_evidence.py:263-267,368-370` と今回の実 EXE 原本 `06-05-evidence/W05c_quit-no_at_production-exe-20261106T120952Z-raw/` に記録された。
- **CR-03 fixed:** `06-05-record-w05c-exe.cjs:145-160` は最終 inspect、stop 前後 snapshot、最終 manifest の更新時刻、回収完了時刻の全てより後の別直接メッセージだけを採用する。原文・出所参照も観察回答と分離して台帳に残す (`同:210-214`)。回収前の5時点は `tests/test_w05c_exe_evidence.py:436-453` が書込前後不変で拒否する。
- **CR-04 fixed:** `06-05-record-w05c-exe.cjs:155-160` は採用原文を trim 後の4つの肯定形と完全一致で判定し、`同:211-214` は無改変の原文を台帳へ保存する。`06-W05C-EXE-COLLECTION.md:98` は回収後の別質問で許可文言を案内する。`tests/test_w05c_exe_evidence.py:456-494` は4肯定形と原文保存、否定・保留5例の dry-run／書込拒否と全 fixture 不変を確認する。
- **CR-05 fixed:** 共通監査 `tests/release_uat_support.py:1730-1732` は pass 行の `answer` にケース ID `W05c` を要求する。修正後 helper `06-05-record-w05c-exe.cjs:210-215` は `row.answer` に `W05c quit-no production-exe：` を付け、`raw_inputs[0].text` の利用者原文を変えない。試験 fixture は実台帳と同じ `subrow`・`entry`・`evidence_kind`・環境の必須欄を持ち (`tests/test_w05c_exe_evidence.py:117-134,210`)、正式 helper 出力を共有 `_check_subrow(..., strict=True)` へ通す (`同:387-403`)。実台帳の対象行は `answer` にケース ID、`raw_inputs` に無改変原文と別採用回答を保持する (`06-MANUAL-EVIDENCE.json:8704-8737`)。親の `audit --require-pass W05c` は3入口すべて成功、`--allow-pending` も成功した。

#### 修正済み CR-05: ケース ID のない回答により正式行監査が失敗

**初回分類:** BLOCKER／**現状:** fixed  
**File:** `.planning/phases/06-release-validation/06-05-record-w05c-exe.cjs:210`  
**Issue:** 初回 helper は `row.answer` を利用者原文だけにし、共有監査が要求するケース ID `W05c` を含めなかった (`tests/release_uat_support.py:1730-1732`)。実機の初回正式書込後、`audit --require-pass W05c` がこの理由で失敗した。  
**Fix:** 対象行の表示用 `answer` にケース ID を付け、`raw_inputs` に原文を保持する。共有監査を通す統合回帰を追加する。修正後の実台帳・試験で成立を確認した。

#### 修正済み CR-04: 否定の採用回答も原文部分一致で pass になる

**初回分類:** BLOCKER／**現状:** fixed  
**File:** `.planning/phases/06-release-validation/06-05-record-w05c-exe.cjs:155-160`  
**Issue:** `adoption.decision === '採用'` と `adoption.text.includes('採用')` は別々に検査される。利用者の別メッセージ原文が「不採用」「採用しない」でも部分一致は真になるため、記録者が `decision` に「採用」を入れると、直接の拒否を正式 pass に昇格できる。現行の否定試験は `decision` を変更するものだけで、否定原文と肯定 `decision` の不一致を扱っていない (`tests/test_w05c_exe_evidence.py:385-388`)。

**Fix:** 採用原文は有限の明確な肯定形式（例: 「採用」「採用してよい」）に正規化して厳密一致させ、原文自体は別フィールドに無改変保存する。「不採用」「採用しない」と肯定 `decision` の組合せを拒否前後の全ファイル bytes 不変の負対照に追加する。

### 初回指摘の履歴（再監査で解消）

#### 修正済み CR-01: `prepare` の JSON 出力から run を取得できない

**初回分類:** BLOCKER／**現状:** fixed  
**File:** `.planning/phases/06-release-validation/06-W05C-EXE-COLLECTION.md:16`  
**Issue:** `$run = (python ... prepare ...).run` は PowerShell から起動した Python の標準出力文字列に `.run` を適用する。`release_uat_support.py:2559-2560,2704-2715` は JSON テキストを印字するだけで PowerShell オブジェクトを返さないため、`$run` は run path にならず、続く fixture・overlay・start が成立しない。既存 `06-UAT.md:955` にも同じ参照コマンドがある。隔離試験は Python fixture を直接構築するため、この手順を実行していない (`tests/test_w05c_exe_evidence.py:61-77`)。

**Fix:** `prepare` の標準出力を `ConvertFrom-Json` で変換し、`$run` が非空の絶対 run path であることを確認してから次へ進む。UAT カードの参照コマンドも整合させる。

#### 修正済み CR-02: 利用者のチャット回答後にも EXE の前景を要求する

**初回分類:** BLOCKER／**現状:** fixed  
**File:** `.planning/phases/06-release-validation/06-05-record-w05c-exe.cjs:126-129`  
**Issue:** 手順は No 直後の `after_no` を採り、利用者がチャットで直接回答してから回収前の `after_peer` を採る (`06-W05C-EXE-COLLECTION.md:30-39`)。回答のため ChatGPT へ前景が移った正常な場合、`after_no.foreground` が一次 EXE でも `after_peer.foreground` は別 PID となる。helper は両方が一次 PID でなければ拒否し、回答時刻をこの二観測の間に要求する (`06-05-record-w05c-exe.cjs:139-140`)。試験 fixture は両観測の前景を常に primary に固定しており、この経路を検証していない (`tests/test_w05c_exe_evidence.py:252-258`)。

**Fix:** No による画面遷移直後の実前景は `after_no` で判定する。`after_peer` は観測時の実前景を原記録のまま保持し、owner 生存・同一性・peer 消失を別条件で照合する。チャット回答後に前景が切り替わる fixture を追加する。

#### 修正済み CR-03: 最終回収前の「採用」承認で正式 pass にできる

**初回分類:** BLOCKER／**現状:** fixed  
**File:** `.planning/phases/06-release-validation/06-05-record-w05c-exe.cjs:146-150`  
**Issue:** `adoption.approved_at` は直接回答時刻以降であればよく、`after_peer`、`before-stop`、`after-stop`、最終 manifest 回収より後である必要がない。このため回収成否と保護照合が未確定の時点の事前承認を、完成後の証拠に対する明示採用として台帳へ pass 記録できる (`同:196-222`)。実際の肯定 fixture も `approved_at=12:00:07Z`、`after-stop=12:00:08Z` で通る (`tests/test_w05c_exe_evidence.py:211-223,293-299,333-349`)。既存 script v3 は採用時刻を最終イベントと収集完了時刻以降に限定している (`06-05-w05c-v3.cjs:56-58`)。

**Fix:** 明示採用を最終観測・stop・回収後 snapshot の時刻以降に限定し、採用がそれらより前の負対照を追加する。回答時刻と採用時刻は別の直接証拠として維持する。

---

_Reviewer: gsd-code-reviewer_  
_Depth: standard_  
_Reviewed: 2026-11-06T12:17:57Z_
