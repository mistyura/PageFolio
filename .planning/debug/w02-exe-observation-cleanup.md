---
status: resolved
trigger: W02/thumb@production-exe の前景回答と点観測の不一致・終了確認残存
---

# W02実EXEの観測と通常終了

`W02_thumb_at_production-exe-20261028T113526Z.json` は出た/変わった/戻った/保たれた/１つと回答したが、11:34:45.465Zのafter-peerはPowerShell HWND34344978。追加回答は「5秒を待たずF5を押してPowerShellへ戻った」。観測前の手動切替による不成立を製品失敗にしない。既存runに連続監視がないので自動復帰時刻は確定しない。

終了時は実PDFが開いていたため「確認」(#32770)が残り、S.stopは12秒後にprimaryをterminatedと記録。`stop-diagnostics-12152.json`に確認画面が残る。強制回収を正常終了passへ転用しない。owner空・配布元不変・宣言外変更なし。not-run attemptとして元回答/補足回答/manifest/inspect2点/終了診断/PDFを保存する。

修正は検証driverのみ。W01で検証済みのpeer Popen終了→実前景観測→読み取り専用監視終了→音の順をW02にも適用する。既存の外部待機上限4秒と製品期限は変更しない。利用者は音まで操作せず、音の後に入力を試す。PDFのあるW02実EXEでは回答後に利用者が×→終了確認「はい」で閉じ、実PIDの終了を観測してからS.stopで回収結果を記録する。記録helperも連続監視・peer正常終了・通常終了の根拠を要求する。設定行の既存passは別の正常終了証拠を保持する。

全141 PythonのRuff/format/ASTと既存監視機構の全条件・実API確認が成功。

再確認 `W02_thumb_at_production-exe-20261028T114227Z.json` は0.238秒で同HWND4984276へ自動復帰し、peer終了code0後に実前景が一致。43samples/max_gap10ms/errors0/クリック0/キー0、procedure clean。出た/変わった/戻った/保たれた/１つの直接回答でW02本体の条件は成立。

末尾の通常終了確認は利用者がEnter後に「はい」を押したため、早期の一瞬のprocess確認ではclosed=falseでNotEstablishedとなった。しかし同runの既存S.stop(timeout=12)は強制終了を使わずclosedを観測した。利用者の追加回答「PowerShellでEnterを押した後、終了確認の『はい』を押した」、manifestのprimary exit=closed/peer already-exited・owner空・保護成功・配布元不変を照合。終了前の瞬間判定が早すぎるdriverの問題として、原エラーを変更せずcleanup_reviewへ判断を記録し当該行をpassにした。これは準備不足・強制終了・不明なerrorの一般許容ではない。helperは当該session名・厳密な原エラー・最終closedの組合せだけに限定し、通常の他errorは拒否する。

driverは早期closed=falseで直ちにthrowせず、終了要求後の確認に「はい」を押す案内を出し、既存12秒内の最終回収結果で判定する。期限は延長しない。再変更後の全Ruff/format/AST成功。製品・配布用65入力は不変。全件pytestは未実施のため、resolvedをPhase完了・出荷許可にしない。
