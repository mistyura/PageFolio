---
status: resolved
trigger: "W12b/exe-script@production-exe の記録helper dry-runでPython二次のPID照合が失敗。driver記録の peer_identity.pid=2972、resource-audit.pid=24248、owner PID=6432 の関係が不明。"
created: 2026-11-09
updated: 2026-11-09
goal: find_root_cause_only
---

# Debug: W12b Python二次 PID不一致

## Trigger (verbatim, data only)

DATA_START
W12b/exe-script@production-exe の記録helper dry-runでPython二次のPID照合が失敗。driver記録の peer_identity.pid=2972、resource-audit.pid=24248、owner PID=6432 の関係が不明。run: .planning/tmp/release-uat-cd223f3bcaf34f8f84bbe79f17b28129、回答: .planning/phases/06-release-validation/06-05-evidence/W12b_exe-script_at_production-exe-20261109T101932Z.json。仮説: 06-05-w12b-driver.py の _spawn が wrapper PID を記録し、helper(06-05-record-w12b.cjs) は API監査側PIDを期待している。保存済みrun/JSONは変更せず照合のみで原因特定。正式記録・再採取・GUI/再peerはしない。参照: tests/test_startup_windows.py の _spawn、tests/test_w12b_evidence.py、06-W12B-COLLECTION.md。
DATA_END

## Symptoms

- expected: 06-05-record-w12b.cjs の dry-run が W12b/exe-script@production-exe run を受理する（machine の peer_identity と二次 resource-audit の PID/FILETIME が一致）。
- actual: dry-run が Python二次の PID/API監査照合で拒否。w12b-machine の peer_identity.pid=2972、二次 resource-audit.json の pid=24248、一次 owner PID=6432（owner側 API allowed=true / os_error=0、copy ok、closed、provenance matched は確認済み）。
- error: helper dry-run の拒否（Python二次のAPI/監査照合不一致）。helper ソース上の該当文言は `Python二次API/排他証拠不一致`（06-05-record-w12b.cjs:224）。
- timeline: 2026-11-09。同日 W12a 9行（Python二次）は同種照合で全て pass。W12b 初回 run (.planning/tmp/release-uat-49c939698e194790a46b8a927872e6a1) は direct_answer_text null で不成立、承認済み再採取 run が対象 run。
- repro: node .planning/phases/06-release-validation/06-05-record-w12b.cjs を対象 run / 回答 JSON に対して dry-run（正式記録はしない）。

## Constraints (user-imposed)

- 保存済み run ディレクトリ・回答 JSON・証拠・台帳を変更しない。照合（読取）のみ。
- 正式記録・再採取・GUI 起動・再peer をしない。製品/凍結 EXE を変更しない。
- 原因特定のみ（修正は利用者判断後）。pass 判定を緩める方向の結論にしない。
- 注意: HANDOFF.json / .continue-here.md の 2026-11-09 W12b 節は文字化け（?）で日本語が失われている。数値・パスのみ信頼。

## Current Focus

- hypothesis: 確定。driver の `windows._spawn` が返す Popen の `child.pid`（Windows venv の launcher=2972）を `peer_identity.pid` に記録した一方、`resource-audit.json.pid` は実インタプリタ自身の `os.getpid()`（=24248）。helper は両者を `===` で比較している。
- test: 完了（下記 Evidence）。
- expecting: 完了。
- next_action: 完了。2026-11-09 新run release-uat-31b816497292427e97ff6b7cc654c23a で peer_identity.pid=28624=audit.parent_pid、audit.pid=13912≠owner 20264。dry-run validated→利用者「採用」→正式pass記録（W12b_exe-script_at_production-exe-20261109T121614Z.json）。台帳20 pass / 88 not-run / 対象外2。

## Evidence

- timestamp: 2026-11-09 / 調査方法の注記。helper の `--dry-run` 再実行は auto mode の権限分類器に拒否された（実行していない）。代わりに helper 219-224 行の各部分条件を、保存済み JSON を読取のみで個別評価した。run/回答/証拠/台帳への書込みは一切なし。
- timestamp: 2026-11-09 / 失敗条件の特定。06-05-record-w12b.cjs:216-224 の 12 部分条件を個別評価した結果、偽になるのは 219 行の `audit.pid===peer.pid` のみ。
  - 真: result.constructed===0 / audit.owner_result==='existing' / expected-owner.pid===owner.pid(6432) / expected-owner.process_created===owner.created(134386930920738840、正規表現で厳密比較) / audit.verified_owner.pid===6432 / verified_owner.process_created===owner.created / audit.session_id===observed.session_id(1) / audit.allow_foreground.pid===6432 / allowed は boolean(true) / os_error は整数(0) / m.api_return===audit.allow_foreground
  - 偽: `audit.pid===peer.pid`（24248 vs 2972）
- timestamp: 2026-11-09 / 記録側。06-05-w12b-driver.py:315-321 で `child, path = windows._spawn(...)`、337 行 `"pid": child.pid` を `peer_identity.pid` へ保存。`child` は tests/test_startup_windows.py:213-221 の `subprocess.Popen([sys.executable, test_startup_windows.py, "_test_scenario_bootstrap", ...])`（_spawn は 188-209 行）で、`child.pid` は Popen が返す起動直下のプロセス PID。
- timestamp: 2026-11-09 / 監査側。resource-audit の `pid` は tests/test_startup_windows.py:3059-3066 の `self.audit = {"pid": self.pid, "process_created": self._created(GetCurrentProcess()), ...}`、`self.pid` は pagefolio/startup_win32.py:441 の `os.getpid()`。すなわち実際に Tk/スタートアップ処理を行ったインタプリタ自身が書く PID。
- timestamp: 2026-11-09 / venv launcher の実在。`.venv/pyvenv.cfg`: home=...\Python315、version 3.15.1。`.venv/Scripts/python.exe` は 255,200 バイト、基底 `Python315/python.exe` は 105,696 バイト（venv の python.exe は基底インタプリタを子として起動する redirector/launcher の大きさ）。
- timestamp: 2026-11-09 / 同環境での再現実験（読取専用・GUI/PageFolio/EXE を起動しない。スクリプトは scratchpad の C:/Users/shdwf/AppData/Local/Temp/claude/a264c3ea8d67637e/df720764-6efe-4b4b-8310-11e0bdc41513/scratchpad/launcher_check.py）。`.venv/Scripts/python.exe -I launcher_check.py` で、同じ `subprocess.Popen([sys.executable, ...])` に対し `Popen.pid=24888`、子の `os.getpid()=9492`、`match=False`。同じ構成で Popen.pid と実インタプリタ PID が一致しないことを実測。
- timestamp: 2026-11-09 / プロジェクト自身の既知事項。tests/test_startup_windows.py:1243「Windows venvではPopen.pidはlauncher、Tk所有者はその実行process」、同:1513「Windows venv launcher PID と実Python PIDは一致しないことがある。」同:1244 は `owner_pid.value == ready["pid"]`（実行 process の PID）を使い、launcher PID とは比較していない。W12b の driver/helper はこの知見を反映していない。
- timestamp: 2026-11-09 / 時系列整合。w12b-machine.json の events は 1 回の `peer` のみ（state-preparation 10:18:35.185Z → peer 10:18:36.144Z）。audit の `process_created`=134386931157317342 は 2026-11-09T10:18:35.7317Z で、この区間内。owner(6432) は 10:18:12.0739Z 起動で、24248 は 6432 より後に生まれた別プロセス。二次は fixture `peer-141829f1...` の 1 つだけ。
- timestamp: 2026-11-09 / W12a との差。06-05-record-w12a.cjs:91 は `Number.isInteger(peerAudit.pid) && peerAudit.pid !== owner.pid` のみで、Popen 由来の PID との等値比較が無い（W12a driver は `command("peer", ...)` 経由で、peer 側 Popen PID を記録しない）。W12b だけが 06-05-record-w12b.cjs:219 `audit.pid===peer.pid` を持つため、W12a は全 pass で W12b だけ落ちる。
- timestamp: 2026-11-09 / 単体試験が捕捉できなかった理由。tests/test_w12b_evidence.py:100-102 と 208-212 の合成 fixture は `audit.pid == peer_identity.pid == 2345`（launcher を持たない世界）。`audit.pid` と `peer.pid` の関係を壊す変異は rejects リスト（495-556 行）に無く、launcher 経由の実起動を模していない。
- timestamp: 2026-11-09 / 一次 owner 側は健全。w12b-machine.json: owner={pid:6432, created:"134386930920738840"}、owner_after_peer.alive=true / created 一致 / session_id=1 / elevated=false、after_peer={hwnd:462342, pid:6432, title:"設定"}、inspection の primary.identity="same"、stop=[{pid:6432, result:"closed"}]、provenance_after_stop.matched=true、error/stop_error なし、api_return={pid:6432, allowed:true, os_error:0}。
- timestamp: 2026-11-09 / 未記録の事実（証明できない点）。run には 2972 の親子関係（parent_pid）も作成 FILETIME も保存されておらず、2972 は現在存在しない。したがって「2972 が 24248 の親 launcher である」は、上記の機構（実測再現・ファイルサイズ・既存コメント・時系列）からの強い推論であり、この run 単体の記録からは直接証明できない。

## Eliminated

- 「二次が別の run/別 owner を相手にした」: expected-owner.json、audit.verified_owner、allow_foreground の PID/FILETIME は全て run の owner(6432, 134386930920738840) と一致し、一次 owner 側の識別・実前景も一致する。否定。
- 「owner(6432) と peer の取り違え」: 24248 は owner 6432 とは別プロセス（`peerAudit.pid !== owner.pid` は真）。かつ作成時刻は owner の約 23.7 秒後で peer 区間内。否定。
- 「helper が API 監査側の PID を期待し driver が誤って別を保存した」（トリガーの仮説の後半）: 部分的に修正が必要。helper は監査側 PID を `audit.pid` として正しく読んでいる。誤っているのは「driver が launcher PID を『二次 PID』として記録し、helper がそれを実 PID と等値比較する」という両者の組合せ。

## Resolution

- root_cause: 06-05-w12b-driver.py:337 が `peer_identity.pid` に `windows._spawn` の戻り値 Popen の `child.pid` を記録するが、Windows の venv では `.venv/Scripts/python.exe` が launcher で、Popen.pid（2972）は launcher の PID、resource-audit.json の `pid`（24248）は実インタプリタ自身の `os.getpid()` である。06-05-record-w12b.cjs:219 の `audit.pid===peer.pid` が launcher PID と実 PID を等値比較するため、実際には同一の二次起動でも必ず不一致になる。これは driver の記録対象と helper の比較対象のズレであり、W12a には同等の比較が無いため W12a は通過し、tests/test_w12b_evidence.py の合成 fixture が audit.pid==peer.pid としているため単体試験でも検出できなかった。
- 結論（証拠の有効性）: この不一致は「一次 owner 側の証拠が無効」という意味ではなく、driver/helper が別のプロセス（launcher と実プロセス）を記録・比較していることに起因する。一次 owner(6432) の識別・実前景・API 戻り・closed・来歴は全て整合している。ただし、現行 run には二次の親子関係（launcher→実プロセス）が記録されておらず、その紐付けを helper が厳密に検証することはできない。したがって、現行 run をそのまま pass 記録するには判定を緩める（`audit.pid===peer.pid` の除去/緩和）しかなく、これは推奨しない。
- fix: 2026-11-09 利用者が案Aを選択し適用。(1) tests/test_startup_windows.py の Backend audit に `parent_pid: os.getppid()` を追加。(2) 06-05-record-w12b.cjs の照合を `Number.isInteger(audit.pid) && audit.pid!==owner.pid && (audit.pid===peer.pid || audit.parent_pid===peer.pid)` に変更（launcher無し環境では直接一致、venvでは実二次がlauncherの直接の子であることを要求）。driver は変更なし（peer_identity.pid=Popen.pid=launcher のまま）。(3) tests/test_w12b_evidence.py の fixture を launcher 形（peer 2345 / audit.pid 2346 / parent_pid 2345）に変更し、parent_pid=999・parent_pid欠落(None)・audit.pid=owner.pid の3変異を拒否試験に追加。Popen がハンドルを保持するため launcher PID は二次稼働中に再利用されない。以下は検討時の案。
  - 案A（推奨・緩和ではなく強化）: 二次の実プロセス自身が自分の親 PID を監査へ記録し（tests/test_startup_windows.py の audit 辞書 3059-3066 行に `parent_pid: os.getppid()` を追加）、driver は `peer_identity` に launcher PID（Popen.pid）として保存、helper は `audit.parent_pid===peer.pid`（launcher が実プロセスの親）かつ `audit.pid!==owner.pid` を要求する。launcher が無い環境でも「記録した起動直下 PID が実プロセスの親である」ことを確認でき、現行より厳密になる。併せて tests/test_w12b_evidence.py の fixture を launcher 形（audit.pid != peer.pid、audit.parent_pid == peer.pid）に直し、parent_pid 不一致・欠落を拒否する変異を追加する。
  - 案B（非推奨）: driver が `peer_identity.pid` に `audit.pid` を書く、または helper が `audit.pid===peer.pid` を外す。これは同一性を何も検証しなくなる緩和。
  - 案C（非推奨）: launcher を避けて基底インタプリタを直接起動する。venv の site-packages が使えず、実運用の入口と乖離する。
- verification: 独立レビュー（06-W12B-REVIEW.md CR-02）のBL-01/WR-01/WR-02/IN-06を反映（peer.pid整数・非owner明示、埋込audit一致、直接起動受理試験、台帳にaudit_pid/audit_parent_pid）。tests/test_w12b_evidence.py 33 passed。記録付き単一全件 .planning/phases/04-startup-control/04-reverify-20261109-w12b-pid/ で2488 passed・186入力不変。Phase04/05 VERIFICATIONは変更でstale化→独立verifierで指紋更新中。実W12b再採取は未了。修正前の根拠:根拠は上記 Evidence。再現実験は launcher_check.py（Popen.pid=24888 / os.getpid()=9492）。
- impact_note: 06-05-record-w12b.cjs は `helper_sha256`（94 行）と全 `06-05-*.py/.cjs`（87-94 行）、`tests/**/*.py` を含む Python 入力（79-86 行）の hash を run の来歴と照合する。helper・driver・tests のいずれを直しても、保存済み run の来歴が不一致になるため、案A/B/C のどれでも現行 run は正式記録できず、修正後に W12b/exe-script@production-exe を再採取する必要がある（再採取は利用者の明示承認が前提）。
- files_changed: tests/test_startup_windows.py, .planning/phases/06-release-validation/06-05-record-w12b.cjs, tests/test_w12b_evidence.py（製品コード・凍結EXE・保存済みrun・回答JSON・証拠・台帳は未変更）。保存済み run cd223f3b... は来歴不一致となるため正式記録不可のまま保持。
