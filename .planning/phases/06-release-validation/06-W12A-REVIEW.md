---
phase: 06-release-validation
reviewed: 2026-11-06T15:26:54Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - tests/test_startup_windows.py
  - .planning/phases/06-release-validation/06-05-w12a-driver.py
  - .planning/phases/06-release-validation/06-05-record-w12a.cjs
  - .planning/phases/06-release-validation/06-W12A-COLLECTION.md
  - tests/test_w12a_evidence.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
  necessity: 0
status: clean
---

# W12a 一次・二次入口の独立コードレビュー

## Summary

W12aの5ファイルを標準深度で照合した。`entry-owner-<primary>` は `tests/test_startup_windows.py:3252-3268` で script/module/relocated の実入口へ進み、`:2764-2771,3041` で実 `PDFEditorApp` を構築する。W12a専用の `w12a-manual` marker と120秒watchdogは `:159-160,2403,2995-3002` にあり、既存の通常 cross-entry 自動試験は marker を付けず10秒のまま（`:1487-1515`）。一次 ready 後にpeerを一度だけ起動し、peer終了直後の実 `GetForegroundWindow` と owner PID を記録する（`:3553-3560,3578-3618`）。API許可値は別の `resource-audit.json` にある。設定モーダル等の期待画面は、実前景PIDだけで機械的に同一視せず、手順の利用者直接観察で確認する契約である（`06-W12A-COLLECTION.md:15-25`）。

初回のBLOCKER 3件・WARNING 1件は2026-11-07の限定差分で解消した。新規の実害ある指摘はない。採取・正式人手受入・全件pytest・親再検証は未実施であり、9行は `not-run`、`release_allowed=false` を維持する。実装担当報告の対象30件成功・87件deselected、全Ruff/format/AST/Node成功、対象tracked diffcheck成功を再利用したが、こちらでは実行していない。全tree diffcheckは既存CRLF大量差分で不合格という報告を成功扱いしない。共通監査 `_check_subrow` の実契約（`tests/release_uat_support.py:1707-1759`）と現行W12a台帳の必須欄、W12aカードのみ周辺読取した。

## Narrative Findings (AI reviewer)

### 2026-11-07 限定差分の再監査

- **CR-01 fixed:** `tests/test_startup_windows.py:3551-3557,3677-3730` はW12a `stop` を原本不変の前段assertから外し、run/fixture/roleと一次PID・64bit FILETIMEをreadyと照合する。result未生成なら `_validate_peer` で生存所有者を確認し、その後 `:3708` のstop markerを先に出す。原本/source/親の変化は停止指示後の `provenance-before-stop.json` と結果待機後の `inspection.json.originals_unchanged` に失敗として残る。`tests/test_w12a_evidence.py:313-352` は原本変化時のstop markerと失敗証拠を確認する。ただし試験は既存resultを置くfixtureであり、**生存ownerの実停止は未実測**。
- **CR-02 fixed:** 起動時のmanifestに採用helper自身のSHA-256を保存し、Python CLIの再検査にも含めた（`tests/test_startup_windows.py:71-74,125-137,3465-3475`）。正式採用helperは `pagefolio.py`、新driver、`pagefolio/`・`tests/` 以下の `.py` を再列挙し、保存済みkey集合と各bytes hashを完全比較し、helper自身のhashも照合する（`06-05-record-w12a.cjs:109-128`）。追加・削除・helper変更は `tests/test_w12a_evidence.py:480-489` でdry-run/書込とも全fixture bytes不変の負対照になった。
- **CR-03 fixed:** 利用者の直接回答原文に対象の完全な `a.row` を要求する（`06-05-record-w12a.cjs:166-172`）。表示用answerとraw_inputsに原文を保持する（同`:225-227`）。他行のW12a IDを含む原文は `tests/test_w12a_evidence.py:487-492` が両モードで拒否する。
- **WR-01 fixed:** ownerのreadyには実watchdog登録時刻・期限が付く（`tests/test_startup_windows.py:3172-3180`）。driverは開始後、peer前、観察前、inspect前にstop最大15秒と10秒余白を予約し、足りなければ新しいpeer/待機へ進まずfinallyのstopへ移る（`06-05-w12a-driver.py:40-45,71-101,111-126`）。不足時にstart→stopのみとなる負対照は `tests/test_w12a_evidence.py:356-400`。

以上は修正後のコード・対象試験の読取判定である。親の全件pytestとPhase04/05鮮度再検証、実機の一次画面・実foreground・入力保持、人手回答は別ゲートのまま維持する。

### 修正済み CR-01 — 元ファイル変更時に所有ownerを停止できない

**分類:** BLOCKER  
**File:** `tests/test_startup_windows.py:3527-3532,3657-3668`、`.planning/phases/06-release-validation/06-05-w12a-driver.py:93-108`  
**Issue:** `start` 時の `manifest.originals_before` と現行 `_fingerprints()` の一致を、`peer`/`inspect` だけでなく `stop` に入る前にも `assert` する。採取中に元設定・2 prompt のいずれかが変わると、driverの `finally` が `stop` を呼んでもこの assert で中断し、`:3661` の所有 fixture への `stop` marker が作られない。ownerは120秒watchdog待ちとなり、手順 `06-W12A-COLLECTION.md:15` の通常回収が成立しない。元ファイル変更を正式採用で拒否することと、所有PIDの回収は別の境界である。  
**Fix:** 原本不変の事前検査は `peer`/`inspect` に限定する。`stop` はmanifest内の所有run・fixture・PIDを確認して先にstop markerを出し、結果を待ってから原本・source・親鮮度の不一致を失敗証拠として保存する。変更原本の負対照で、正式採用は拒否しつつ、所有ownerが通常停止することを検証する。

### 修正済み CR-02 — 採取後に追加されたPython入力と採用helperの変更を見落とす

**分類:** BLOCKER  
**File:** `tests/test_startup_windows.py:55-68,119-129`、`.planning/phases/06-release-validation/06-05-record-w12a.cjs:108-111`、`tests/test_w12a_evidence.py:288-306,361-404`  
**Issue:** Python側の `_check_formal_provenance` は列挙し直した入力mapとの完全一致を要求するが、正式採用helperは**保存済みkeyのhashだけ**を調べる。`stop` 後から採用までに `pagefolio/` や `tests/` に新しい `.py` が増えても、採用helperは新keyの存在を検出せず、旧runを現行入力の証拠として `pass` にできる。また採用を左右する新しい `06-05-record-w12a.cjs` 自体は起動時のsource_inputsにもraw来歴にも含まれない。既存試験は変更済みkeyの改変しか負対照に持たない。  
**Fix:** helperでも現行の入力path集合を同じ規則で再列挙し、保存済みkey集合とbytes hashの両方を比較する。採用helper自身のSHA-256もrun/採用記録の来歴に保存し、変更時の扱いを明示する。採取後の新規 `.py` とhelper変更を dry-run/書込双方で拒否し、全ファイル不変を検証する。

### 修正済み CR-03 — 別のW12a行の回答原文を対象行へ転記できる

**分類:** BLOCKER  
**File:** `.planning/phases/06-release-validation/06-05-record-w12a.cjs:149-155,208-222`、`tests/release_uat_support.py:1730-1732`  
**Issue:** `direct_answer.row === a.row` はJSONの記入欄だけを検査し、利用者原文 `direct_answer.text` は `W12a` を含むだけで通る。たとえば `W12a/script-script@script` の原文を `W12a/script-module@script` のJSONに写し、`row` 欄とその原文のhashを合わせれば、対象行の `answer` とUATカードに別行の回答を転記できる。共通 `_check_subrow` もケースID `W12a` までしか検査しない。  
**Fix:** 原文内に**対象の完全な `a.row`** を要求し、表示用 `row.answer` へは正確な行IDを付け、無改変原文を `raw_inputs` に保存する。別行IDを含む回答原文の拒否と無変更を単体試験に加える。

### 修正済み WR-01 — 120秒watchdogに対する終盤の余白が足りない

**分類:** WARNING  
**File:** `.planning/phases/06-release-validation/06-05-w12a-driver.py:25-36,53-82,93-108`、`.planning/phases/06-release-validation/06-W12A-COLLECTION.md:15`  
**Issue:** 手順の最大105秒は各 `subprocess.run` timeoutと固定待機の合計（30+20+20+15+5+15）である。CLI内部のhashやPhase04照会は各timeoutに含まれるが、プロセス生成・driver側の処理は別にかかる。`:81` は経過100秒未満なら `inspect` に進めるため、直後のinspect最大5秒とstop最大15秒だけで120秒のwatchdog期限に達し、処理の余白がない。高負荷時にはwatchdogが通常stopより先に発火し、正式行は採取失敗となる。  
**Fix:** owner ready時刻・watchdog期限をdriverへ渡し、peer前・観察前・inspect前に実残時間からstopと十分な後処理余白を予約する。時間不足なら新規peerや待機を行わず、所有runを直ちに通常回収して `not-run` にする。手順の「105秒以内」はオーバーヘッドを含む実測上限ではないと明記する。

## 未解決・検証境界

修正後の所有owner通常停止は単体fixtureでは生存プロセスまで実測していない。親が計画する全件とPhase04/05鮮度の再検証が必要。実機の前景・設定モーダル・入力保持、人手の3点回答と回収後の別採用回答はこのレビューでは未観測であり、自動試験成功から pass に転用しない。
