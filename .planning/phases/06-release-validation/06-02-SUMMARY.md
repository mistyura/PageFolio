---
phase: 06-release-validation
plan: "02"
subsystem: release-docs
tags: [version-sync, readme, release-guide, doc-contract, tdd]

requires:
  - phase: 06-release-validation
    provides: 06-01 の tools/build_release.py・distribution/samples・初期版はじめに.md
provides:
  - APP_VERSION・READMEバッジ・開発履歴最新節/最終更新欄がv1.10.0で一致
  - README「配布版（EXE）の使い方」(サンプルのコピー名・旧フォルダー保持の更新手順・保証範囲と未実施)
  - distribution/はじめに.md の完成版(2用途のコピー名・同名衝突時の両方保持・plugins非移行・旧フォルダーへ戻す手順)
  - docs/DEVELOPMENT.md の配布ビルド節(初回/再ビルド共通CLI・preflight停止・INCOMPLETE・古いlock回復・容量管理・Git扱い)
  - tests/test_release_contract.py: 版/文書/正本サンプルSHA-256/同梱リンク解決/CLI実--helpの契約18件
affects: [06-03, 06-04, 06-05, 06-06]

plan_head_before: 3a2f04f0a457707cf7e59d435340dd284d73f58c
plan_head_after: e748ca880b58f78f12569913ff3ee32c71447d2d

actuals:
  tokens: 4499
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "文書契約はUTF-8のread-only検査。版はAST literalから導き、期待フォルダー名もAPP_VERSION由来で組み立てる"
    - "同梱リンクは実run_build(fake builder)で作った配布tree上で解決し、同梱CONFIGURATIONのSHA-256をreportと照合する"
    - "既存dirtyの開発履歴.mdはHEAD blobへ自hunkだけ適用したblobをupdate-index --cacheinfoでstageし、他hunkを作業木に残す"

key-files:
  created:
    - tests/test_release_contract.py
  modified:
    - pagefolio/constants.py
    - README.md
    - 開発履歴.md
    - distribution/はじめに.md
    - docs/CONFIGURATION.md
    - docs/DEVELOPMENT.md

key-decisions:
  - "ガイド内の詳細リンクは同梱する ./docs/CONFIGURATION.md とし、同梱されない docs/PLUGINS.md はリンクにせずソース内パスのテキストで案内した(配布物だけで辿れない参照を作らない)"
  - "プラグインは自動移行せず、旧フォルダーを保持したまま既存の導入手順へ案内する"
  - "要件V110-DIST-01〜03/QA-03は、実EXEの受入・phase全体ゲート・最終buildが未了のため mark-complete しない"

requirements-completed: []

duration: 約1.5時間(全件ゲート2回=約6分×2を含む)
completed: 2026-10-24
status: complete
---

# Phase 6 Plan 02: 版同期と利用・保守文書の統一 Summary

**APP_VERSION・READMEバッジ・開発履歴をv1.10.0で一致させ、サンプルのコピー運用・旧フォルダー保持の更新・保証範囲/未実施を利用者文書に、初回/再ビルド共通の専用CLIと停止時の行動を保守文書に反映し、版・正本SHA-256・同梱リンクを契約試験で固定した。**

## Performance

- **Tasks:** 2/2(いずれも先に失敗する試験を書いてから実装: RED→GREEN)
- **Commits:** 2(measured: `3a2f04f..e748ca8`)

## Accomplishments

- Task 1: `APP_VERSION = "v1.10.0"`、READMEバッジ、開発履歴の先頭v1.10.0節と最終更新欄を同期。README新節に、サンプルの2用途コピー名、旧フォルダー保持の更新手順、同じ session の対応版同士のみが対象で排他未対応旧版・OS強制前面化拒否は保証外、実機受入/出荷承認は未実施、を記載。既存の「未リリース Phase 5」節は保持し、現行受入(05-UAT.md)への参照を追記。
- Task 2: `distribution/はじめに.md` を完成(短いMarkdown、同名衝突時は両方保持して利用者が選ぶ、plugins非移行、旧フォルダーの`PageFolio.exe`で戻す)。`docs/DEVELOPMENT.md` の退避→復元手順を `tools/build_release.py` 一本へ置換(preflight停止、INCOMPLETE、report、完全な複製上の手動起動、古いlock回復=PID+生成時刻の所有者が終了済みと確認できた場合のみ手動解除、`.release-*`は自動削除せず明示選択した自分のrunだけ回収、旧追跡dist保持・巨大binaryをstageしない)。`docs/CONFIGURATION.md` にサンプルのコピー運用を追記(読込優先順位・UTF-8・Apply書戻しの契約は不変)。
- `tests/test_release_contract.py`: TestVersionAndDocs(7)/TestSampleSources(4)/TestGuideAndWorkflow(7)。正本2サンプルの全文SHA-256、同梱ガイドのリンクが実配布tree内で解決しCONFIGURATIONのSHA-256がreportと一致、CLIの実`--help`の全オプションがDEVELOPMENTに記載、二重の版定数・旧dist削除・巨大stage指示の不在、未実施を合格と書く表現の拒否を検査。

## Task Commits

1. **Task 06-02-01:** `c09baea` feat(06-02): APP_VERSIONをv1.10.0へ同期し配布版の利用・保証範囲を文書化
2. **Task 06-02-02:** `e748ca8` feat(06-02): 利用ガイドと保守手順を共通CLI・非破壊更新へ統一

## 検証結果(実測)

| 項目 | 結果 |
| --- | --- |
| Task 1 RED | 4 failed / 7 passed(版/履歴/Phase5参照/README節が未実装) |
| Task 1 局所 | TestVersionAndDocs + TestSampleSources 11 passed |
| Task 2 RED | 5 failed / 13 passed(ガイド・DEVELOPMENT・CONFIGURATION) |
| Task 2 局所 | tests/test_release_contract.py 18 passed(後に noqa 付与のみで再実行 18 passed) |
| Ruff check → format(対象py) → 再check → AST | 全合格(各task) |
| Task 1 commit前 全件(単一プロセス・native) | **1878 passed, 1 warning in 372.39s (0:06:12) / exit 0**。basetemp `C:\Users\shdwf\AppData\Local\Temp\pf06_02_t1_full_17928217677042`、ログ `06-02-task1-full.txt`。除外なし |
| Task 2 commit前 全件(単一プロセス・native) | **1885 passed, 1 warning in 358.66s (0:05:58) / exit 0**。basetemp `C:\Users\shdwf\AppData\Local\Temp\pf06_02_t2_full_179282230223592`、ログ `06-02-task2-full.txt`。-k/--ignore/skip による除外なし。最終commit内容と同一bytesで実行 |

Tcl/Tk 同種失敗・ERROR・クラッシュ・DEP-05/owner_missing/通知前景不一致の再発は、2回の全件とも観測されなかった(原因未解決の状態は変わらず、成功を解除や承認へ読み替えない)。

## Deviations from Plan

### 計画からの差異

**1. [計画との調整] Ruff等の版表記の同期を見送った**
- **理由:** 作業木の `requirements.txt` のpin更新(ruff 0.17.1等)は別作業(quick 261022-qv7)の未commit差分で、本計画では stage/commit できない(R06-12)。docs側だけを0.17.1へ変えると、commit済みのrequirements.txt(0.15.20)と矛盾する。
- **扱い:** `docs/DEVELOPMENT.md`・`docs/GETTING-STARTED.md`・`CONTRIBUTING.md` のRuff/依存版表記(0.15.20等)は変更していない。qv7のrequirements.txt変更がcommitされた後に同期する(要追跡)。依存は変更していない。

**2. [配置] ガイドの展開フォルダー名検査はTask 2に置いた**
- Task 1の挙動記述にはガイドの展開folder名検査があるが、ガイド本体はTask 2の対象ファイルのため、README側(`PageFolio-{APP_VERSION}`)をTask 1、ガイド側をTask 2の試験にした。各commitで試験が緑である状態を保つため。

### Auto-fixed Issues

なし(試験作成中の自作の改行/エスケープ誤りは作成中に修正済みで、commit物には含まれない)。

## 既存dirty差分の保全(R06-12)

- 開始時のhash控え: `開発履歴.md` 8bd3b4bd…、`.planning/STATE.md` 5234d6db…、`requirements.txt` 9aaddf30…、`tests/test_startup_windows.py` e591a7c1…。
- `開発履歴.md` はHEAD blobへ自hunk(v1.10.0節・Phase 5参照1行・最終更新欄)だけ適用したblobを `git update-index --cacheinfo` でstageし、既存の診断/仮想環境の20行は作業木に未commitのまま残した。commit前に `git diff --cached` で自分のhunkのみを確認。
- commit後も requirements.txt / tests/test_startup_windows.py / .planning/STATE.md(本task時点)のhashは開始時と同一。全file addや既存dirtyのcommit/取消は行っていない。

## Authentication Gates

なし。

## Known Stubs

なし。

## Threat Flags

なし(新規ネットワーク/認証経路なし。T-06-04/05は試験で緩和: 原本hash契約・衝突時停止の文書化・未実施を合格と書く表現の拒否)。

## 既知の制限・次への申し送り

- 本計画の合格は**文書/契約の実装合格**であり、実機受入・出荷承認ではない。W01〜W12の実機UAT、実EXEの最終build、Phase 4再検証は未実施(`06-UAT-CARRYOVER.md`)。
- Ruff等の版表記同期は上記のとおり未了(qv7のrequirements.txt commit後)。
- 開発履歴.md の既存dirty 20行(別件)は未commitのまま。

## Self-Check: PASSED

- 作成/変更ファイル: tests/test_release_contract.py, pagefolio/constants.py, README.md, 開発履歴.md, distribution/はじめに.md, docs/CONFIGURATION.md, docs/DEVELOPMENT.md — すべて存在
- コミット: c09baea, e748ca8 — HEAD の祖先として存在
