---
status: resolved
trigger: G1全15行pass後の全件pytestで台帳契約テストが失敗
---

# G1監査テストの対象範囲

`06-05-evidence/g1-closeout-20261028` は1510 passed/1 failed/2 warnings/92.09秒、159入力不変。失敗は `TestCaseCoverage::test_structure_audit_accepts_ledger_and_rejects_false_pass` の「台帳全体に未passがあればW01,W02のrequire-passも失敗する」という誤った前提。G1全15行が合格した時点で、他組93未実施・W11対象外2未実施があっても、指定IDだけのrequire-passは成功するのが正しい。製品・実受入結果・監査実装を変更しない。

テストは対象IDの状態だけに期待値を結び、さらに一時copyのW01行を明示的な未実施にして拒否を常時検証する。回答なしの虚偽passも実台帳の進捗に依存しないよう、テストcopyのanswerを明示的に空にする。現物の回答・判定を消去しない。

全141 PythonのRuff/format/AST成功。対象契約45 passed/1 warning/15.76秒。再実行 `g1-closeout-fixed-20261028` ではこの契約を含む2005件が成功し、別のnative Tcl対照群が15秒timeoutで停止した（1 failed/2 warnings/240.49秒・159入力不変）。初回失敗XML/stdout/stderr/入力hashは各runに保持する。

## native Tcl対照群の診断

失敗は `test_native_tcl_getmessage_stall_recovers_with_product_wake[False-False]`。製品のwakeを無効にした対照子プロセスが終了せず、元コードはTimeoutExpired時の出力を保存していなかったため、停止位置は不明。原因を確定したとは扱わない。

子へ5秒間隔のfaulthandler診断を加え、親は15秒timeoutの例外を再送出する前にstdout/stderrをJSON保存する。合否条件・15秒期限・製品コードは変更しない。対象全23件は `g1-wake-diagnostic-20261028.xml` で23 passed/1 warning/4.39秒。単独では再現しないため、診断付きで全体の実行順を再現する。

診断付き全件 `g1-closeout-diagnostic-20261028` は2237 passed/2 warnings/520.03秒・159入力不変、Ruff/format/AST成功。元のG1監査契約修正は検証済み。native Tcl対照群の一度のtimeoutは原因未確定であり、解消済みとは称さない。再現しない停止事象として初回原本・例外診断を保持する。専用子プロセス残存なしをnative CIMで確認。G1監査と全件成功を根拠に06-05/G2へ進む。
