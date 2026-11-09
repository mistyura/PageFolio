# 2026-10-28 出荷停止解消作業・世代4の再開点

## 完了した変更と検証

- CR-03: OCR off時の旧providerへのサマリ送信をUIと実行入口で遮断し、provider/model表示を修正。v1.10.2へ同期。
- 回帰12ケース追加。単一native全件2083 passed / 2 warnings / 463.98秒 / exit0。147入力の前後一致。Phase05の独立再レビューopen0、再検証23/23 fresh passed。Phase04 fresh passedも保持。
- 世代4は同じ65入力から初回/再build各1回成功。最終EXE `6a0bd182d0ab717f45ddf2f36fd23aaad8aacdc83c264843fbcaab40ced20d3d`、tree `3a21ad1d2e0758cb839c7e48483b9e8a23c95a2f41dccf740eff95624b97b731`。
- 保護3名・通常/破損/読取不能の起動時保持・更新衝突/非衝突・X01〜X05の外部障害成立を記録。X04 write/replaceは初回終了保留後に所有handleで回収。正常終了/passと扱わない。追加guardの停止原本を保持し、未実施2条件だけ続行。
- 実EXE接続: ocr-single `6dd0b4d0997b4b8eb0ccb665ab067123`、W05b `1125b7a0cfad4a4ab00a08b522e5aab1`。それぞれ同1POSTを解放・完了。利用者が合成結果を確認し、通常終了。driver時点ではprimary/peerともalready-exited、残存ownerなし、配布物変更なし。
- W05bはChatGPT前景から同じ確認HWND10686146へ自動復帰。50ms外部観測と利用者原文「自動で同じ確認画面に戻った」、いいえ後の処理継続、同request完了を照合。世代3の失敗原因は未確定のまま、旧記録をpassに書き換えていない。
- `audit --preparation-only` はexit0 / ok=true / phase_complete=false / release_allowed=false。接続準備の停止は解消。本受入とは別。

## 本受入と環境上の制約

- W01/normal@scriptを実施し、利用者の「通常」「はい・1つ・見える。ほかに気づいた点はない」、peer completed141ms、state_preserved/target_correct/focus_correct=true、原本不変・所有process回収を保存。sessionは `06-05-evidence/W01_normal_at_script-20261028T073252Z.json`。
- 本受入への昇格は保留。準備時は最小化だがpeer前にPageFolioへの前景遷移があり、peer直前の最小化維持を確認する連続window状態がない。回答はチャット原文をdriverへ中継し、本人の端末入力とは区別する。台帳はnot-runのままattemptを別保存する。
- W11の環境質問に「使える別ユーザー・別セッションがない」と回答。2行ともnot-run/準備不能。アカウント新設や資格情報取得は行わない。
- 人手passは0/110。Phase06/06-05/06-06と出荷は未完了。準備成功やW05bの診断を110行のpassへ転用しない。

## 次の判断と作業

`06-W11-REPLAN-DRAFT.md` の案A（検証環境を用意）または案B（今回の保証を単一ログインセッション利用へ限定して再計画）について利用者判断が必要。案Bは未承認で、現行要件・監査条件を変更していない。他の本受入は残り、案B承認だけで出荷は許可されない。

既存dirty/index・旧世代・失敗原本は保持。commit/push/公開は未実施。今回のコード変更のテスト成功と未実施受入を分けて扱う。
