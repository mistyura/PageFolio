# Python 実機受入証拠の再利用境界監査（2026-11-06）

**読取時点:** 2026-11-06 14:05 UTC。正式台帳・UAT・原本・VERIFICATIONは変更していない。constructor-sync全件は実行中で、結果は本監査に含めない。行別の完全な機械可読記録は [06-PYTHON-REUSE-AUDIT-20261106.json](06-PYTHON-REUSE-AUDIT-20261106.json)。

## 判定

06-03-PLAN.md:96-98 は、Python行の再利用を入力・環境・Phase 04 covered_digestの同一性に限定する。現在passのPython-real 20行は、回答証拠のSHA-256と隔離run manifestのコピーSHA-256が各20/20一致し、旧観測の来歴は保全されている。ただし、W05c v3 script 1行は保存された6つの採取入力のうち tests/test_startup_windows.py 全体hashが明示的に不一致。残る19行は回答証拠・コピー済みrun manifestに実行時のharness全体hash、完全なsource_inputs、Phase 04 covered_digestを保存しておらず、現行入力との同一性を証明できない。G3内訳は不一致1・証拠不足5、G3外14は証拠不足14である。**旧passは履歴として有効だが、20行とも現行Python入力のpassへ自動昇格しない。**

保存された20行のOSはWindows build 26300、Python 3.15.2、Tk 9、session 1。現行runの完全な同環境は未観測であり、これも再利用の確証にはしない。Phase 04報告の保存digestは `v4:sha256:d36e0481139353e9293b23be0d3774317565f7b9f2dd12cd5eec955a95693128` だが、読取時点の所有CLIは `stale`。行ごとの保存digestもない。

| 行 | run ID | 回答証拠（06-05-evidence/配下） | harness / Phase 04 の照合 |
|---|---|---|---|
| W01/normal@script | pagefolio-uat-n1grfbx6 | W01_normal_at_script-20261028T100202Z.json | 実行時hash・行別digestなし |
| W01/normal@module | pagefolio-uat-j6e2yx5l | W01_normal_at_module-20261028T100652Z.json | 実行時hash・行別digestなし |
| W01/zoomed@script | pagefolio-uat-pr7_9dnx | W01_zoomed_at_script-20261028T104539Z.json | 実行時hash・行別digestなし |
| W01/zoomed@module | pagefolio-uat-7jhhhzlk | W01_zoomed_at_module-20261028T104658Z.json | 実行時hash・行別digestなし |
| W02/settings@script | pagefolio-uat-1warmump | W02_settings_at_script-20261028T111048Z.json | 実行時hash・行別digestなし |
| W02/settings@module | pagefolio-uat-a2gfwff8 | W02_settings_at_module-20261028T111310Z.json | 実行時hash・行別digestなし |
| W02/thumb@script | pagefolio-uat-5999fjf_ | W02_thumb_at_script-20261028T113122Z.json | 実行時hash・行別digestなし |
| W02/thumb@module | pagefolio-uat-loxxfb1v | W02_thumb_at_module-20261028T113300Z.json | 実行時hash・行別digestなし |
| W02/preview@script | pagefolio-uat-_q4bxekr | W02_preview_at_script-20261028T115040Z.json | 実行時hash・行別digestなし |
| W02/preview@module | pagefolio-uat-6i_e5zfn | W02_preview_at_module-20261028T115223Z.json | 実行時hash・行別digestなし |
| W03/pdf-3page@script | pagefolio-uat-llo79uyj | W03_pdf-3page_at_script-20261028T124500Z.json | 実行時hash・行別digestなし |
| W03/pdf-3page@module | pagefolio-uat-0spbe9t7 | W03_pdf-3page_at_module-20261028T125331Z.json | 実行時hash・行別digestなし |
| W04/ocr-1page@script | pagefolio-uat-hp3zleme | W04_ocr-1page_at_script-20261028T142948Z.json | 実行時hash・行別digestなし |
| W04/ocr-1page@module | pagefolio-uat-ze1w343k | W04_ocr-1page_at_module-20261028T143122Z.json | 実行時hash・行別digestなし |
| W05a/nested-settings@script | pagefolio-uat-1a8d7i3t | W05a_nested-settings_at_script-20261028T150111Z.json | 実行時hash・行別digestなし |
| W05a/nested-settings@module | pagefolio-uat-k5xylf7o | W05a_nested-settings_at_module-20261028T151926Z.json | 実行時hash・行別digestなし |
| W05b/ocr-close-confirm@script | pagefolio-uat-p6cn0k5x | W05b_ocr-close-confirm_at_script-20261031T003108Z.json | 実行時hash・行別digestなし |
| W05b/ocr-close-confirm@module | pagefolio-uat-am_h8ko4 | W05b_ocr-close-confirm_at_module-20261031T003956Z.json | 実行時hash・行別digestなし |
| W05c/quit-no@script | pagefolio-uat-90219b127fbe491a88e7ed17db1df509 | W05c_quit-no_at_script-20261106T104952Z.json | v3保存hash不一致 / 行別digestなし |
| W05c/quit-no@module | pagefolio-uat-idqe4ma0 | W05c_quit-no_at_module-20261031T085031Z.json | 実行時hash・行別digestなし |

全行の回答証拠参照・run ID・原本コピー参照・保存環境・SHA-256照合結果はJSONの `python_rows` に記録した。20件の raw `run-manifest.json` は `copies.json` 内の保存SHA-256と一致し、台帳の source_commit とも一致した。しかし source_commit は観測時のdirty worktreeのファイルbytesを証明しない。W01〜W05cの直接Python起動は同じ `tests/test_startup_windows.py --uat` ハーネスを使う（06-UAT.md:84以降、tests/test_startup_windows.py:3320以降）。

## 3つのhash領域を分離

- **W05c v3採取入力:** `06-resume-20261106/w05c-v3-plan.json:25-31` と封印された raw `v3-w05c-plan.json` の6ファイル。5ファイル一致、`tests/test_startup_windows.py` だけ保存 `16a7b676d972f8d439161d64c1e5d08a0caa19e1f8034c57bf531dcb8e333469` と現行 `0b788cdf0b1c0dd21ac9b736f5241538dc536998a83ce3432c0c444824e4a481` が不一致。 `tests/w05c_runner.py:17-60` と `06-05-record-w05c-python.cjs:136-146` はファイル全体のhash一致を要求する。
- **凍結build入力65件:** `06-BUILD-EVIDENCE.json:60-62` のmanifest `ae08f9422ee0010bbc827720aae0c1873552d0dd51b63ddf4960baeba036658d`。凍結時の同testファイルは `846ee305e323fed436a2a60741df52135afdb39da35c672ed976d86c123a9b47`。この65件は製品コードだけの集合ではなく、W05c v3の6採取入力とも別。現行worktreeのharnessを旧凍結snapshotへ書き換えない。
- **最終EXE対象:** generation 5 / v1.10.2、EXE `66be5df663e333057c5c3cde02180857f930d2433e377f69c2838432d49a19d4`、tree `b1e55ca6efa3a7bafb4dec9ea9fa2c715dfca6f538ba906632058f912f575d85`。production-exe pass 10行は、台帳のbinary/build-inputと隔離原本manifestのsource EXE/treeが各10/10でこの対象と一致し、回答証拠のhashも10/10一致した。同じ凍結binaryに対する**maintain候補**であり、Python源の変更だけでは旧EXE観測を新binaryへ結び替える必要はない。最終品質・独立ゲート・出荷判断は別途必要。

| EXE行 | run ID | 対象照合 |
|---|---|---|
| W01/normal@production-exe | 0050ee332bb946609795dc8733c8d772 | binary/tree/build入力一致、旧証拠保全 |
| W01/zoomed@production-exe | aa8798df944848fc97c9bc482737c426 | binary/tree/build入力一致、旧証拠保全 |
| W02/settings@production-exe | 51eff5f15d8d40e7bdebde42df216dba | binary/tree/build入力一致、旧証拠保全 |
| W02/thumb@production-exe | 76b1fbb27a9a4469a8d81cd875d37c09 | binary/tree/build入力一致、旧証拠保全 |
| W02/preview@production-exe | dcaff22c626a4230b04d6fb6111f2140 | binary/tree/build入力一致、旧証拠保全 |
| W03/pdf-3page@production-exe | 6ec3b952ff8e4ac293a74fb15f33bf09 | binary/tree/build入力一致、旧証拠保全 |
| W04/ocr-1page@production-exe | 34338c8984bb4cc2bfe8842cfbf80caa | binary/tree/build入力一致、旧証拠保全 |
| W05a/nested-settings@production-exe | 1865104388754612ac38fd00d8f8f2d7 | binary/tree/build入力一致、旧証拠保全 |
| W05b/ocr-close-confirm@production-exe | 6a425e5b5b7c4a71a90ecab623107efa | binary/tree/build入力一致、旧証拠保全 |
| W05c/quit-no@production-exe | 01ec699d960a4b8da489f7407fa31bfb | binary/tree/build入力一致、旧証拠保全 |

## 正式auditの範囲と後続更新案

`tests/release_uat_support.py:1710-1759` の `--require-pass` は、Python-real行の `input_manifest_sha256` を凍結build値へ照合するが、現行harnessの全hashまでは照合しない。`check_resume`（同:1572-1594）もrun ID・EXE/tree・一部環境の比較で、source_inputsとcovered_digestは見ない。既存G3 9/9監査は採用時点の構造・回答・対象照合の記録であり、今回のPython源の鮮度判定ではない。単一全件の成功や開発履歴だけの変更も人手回答を更新しない。

後続の正式更新を行う場合は、まず旧台帳・UAT・W05c v3計画・原本コピーを改変せず保存する。入力同一性を立証できない **Python-real subrowだけ** 旧pass行に `superseded_by` と根拠を追記し、同じ正規cardの新しい有効行を `not-run` で追加する。旧行の回答・run ID・時刻・hash・原本参照を保持し、新行の回答、raw_inputs、observations、observation_basis、answer_provenance、run ID、観測時刻、環境、source_commit、旧観測hashを空にする。build generation 5と新しいPython入力世代を別欄で表し、EXEの10行は維持する。現在の `supersede_rows(ids=...)` はケースID単位でEXE兄弟行も置換する（同:1596-1624）ため使えない。選択的更新後は有効110 cardの一意性と `--allow-pending` を照合し、新たな利用者観測・採用が揃った対象だけ `--require-pass` へ進む。既存W05c記録helperの先頭card検索とgeneration 5前提（`06-05-record-w05c-python.cjs:190-201`）は、新有効行を選択できるよう後続作業で確認が必要。

本監査は正式pass数、`ready_for_retry`、`release_allowed` を変更しない。
