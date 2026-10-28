---
phase: 06-release-validation
status: observation-interrupted
created: 2026-10-28
---

# 世代5 W05bの観測中の手動切替

run `31d4388e2cbb4f80944a015b67bc3234` は合格へ変換しない。
原記録は `06-08-w05b-interrupted-session.json`。同確認HWND11930932/primary11436への自動復帰は50ms間隔の外部観測で記録されたが、peer終了時の前景はChatGPT HWND396656/PID18044だった。

| UTC時刻 | 前景 |
|---|---|
| 09:21:29.479383 | ChatGPT |
| 09:21:29.708527 | 同確認画面 |
| 09:21:32.081565 | ChatGPT |
| 09:21:33.650350 | 観測終端もChatGPT |

利用者の最初の回答は「自動で同じ確認画面に戻った」。補足質問「観測が終わりましたの案内を見る前に、ご自身でChatGPTへ切り替えましたか？」への原文回答は「案内を待たず、自分でChatGPTへ切り替えた」。両回答を保持する。

いいえ後の処理維持、同1POST完了、結果表示、利用者による通常終了は成立。primary/peerともalready-exited、残存ownerなし、配布元不変。ただし `peer_returned_to_modal=false` の機械判定を変えない。記録組立のassertが書込前に停止したため、現行PROTECTIONは接続未成立のまま。

このrunの終端不一致には観測中の手動切替が介在した。製品不具合や旧世代3の原因解消とは断定しない。既存 `$gsd-debug phase06-w05b-manual-switch` の切り分けを継続し、次は自動復帰後10秒間無操作を明示した別runでW05bのみ1回確認する。製品・driver・判定条件・期限は変更せず、成功済みocr-singleを再実行しない。
