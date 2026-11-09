---
status: resolved
trigger: "2026-11-06 G3受入後の全件でconstructor通知重複抑制2条件が失敗"
phase: 04-startup-control
---

# コンストラクタ失敗通知の重複抑制試験

## 初回証拠

- 全件: `../phases/04-startup-control/04-reverify-20261106-exe-closeout/`。2397 passed / 2 failed / 2 warnings、725.85秒、exit1。171入力前後不変、Ruff/format/ASTは成功。成功へ換算しない。
- 失敗: `test_constructor_failure_notice_dedup[False]` と `[True]`。legacy join経路の `result.result == 'coalesced'` が不成立。Trueには `notification_unavailable reason=check_failed os_error=0` もある。
- raw: `constructor-notice-dedup-20261106/`。2 fixtureの66ファイルを一意なTEMPからコピーし全hash照合。`copy-manifest.json` と元junit/stdout/stderrを保持。
- Falseのlegacy-join-3は10秒後のfaulthandlerで `NativeNoticeLifetime.show` 内におり、coalesced経路から新規表示へ移っている。

## 現在の仮説と判定条件

試験はownerの通知表示後に7子を起動する一方、通知寿命は1800msに固定されている。子のbootstrap/importが寿命内に終わる同期条件がない。初回の子bootstrap時点は表示後およそ1.47〜1.74秒、以降に通知処理があるため、通知終了後の呼出を重複表示中として判定している可能性が高い。Falseのスタックは新規通知表示へ進んだ事実を示すが、通知呼出tickは原本に無く、時系列の確定には追加計測が必要。

次は同じ既存自動試験に呼出tickを記録し、遅いbootstrapの負対照を1回で採る。通知寿命・製品期限・期待する重複抑制は緩和しない。仮説が成立した場合は子が通知呼出直前まで準備できてからownerを表示する同期へ修正する。製品コードを推測で変更せず、同条件の無計測再試行をしない。

## 負対照での確定

`controlled-red.xml` と `controlled-red-timeline.json`：同じ既存試験の最後の子へbootstrap遅延2.1秒を入れた1条件が失敗した。先行6子は表示後594〜656msで呼び出し、notice_calls=0・元deadline一致。遅い子は表示後2781ms（期限後981ms）に呼び出し、新規通知1回・別deadlineとなった。期限終了後の新規表示は正当であり、試験が「通知表示中の重複」という前提を満たしていなかった。

修正は7子を通知呼出直前まで準備してからownerを起動し、表示ready後に同時解放する同期。子のimport/制御遅延を寿命の前へ移し、実呼出tickが元の表示〜期限内に入ったこともassertする。寿命1800ms、製品期限、重複抑制期待値は不変。遅延なし/2.1秒×通常/legacy ownerの4条件で検証する。

## 継続条件

修正後の4条件と他constructor5件が成功。独立レビューは新規指摘0。単一全件 `04-reverify-20261106-constructor-sync/` は2401 passed/2 warnings、failure/error/skip0、629.77秒、171入力前後/回収時不変、Ruff/149format/AST成功。初回2397/2failedと負対照REDは履歴として保持する。製品不変、寿命1800ms不変。正式親verificationの更新とPython受入の来歴再判定は別作業。

G3の人手受入9/9は保存済み。全体30pass/78not-run/対象外2、release_allowed=false。G4以降の実装・新規実機採取・commitは停止。Phase04のCLI検証はpassed、Phase05は開発履歴追記によるstale。最新の品質失敗を解消した証拠を得るまで後続へ戻らない。
