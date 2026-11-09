---
phase: 06-release-validation
status: pending
source_phase: 04-startup-control
requirement: V110-QA-02
approved: 2026-10-22
scope_amended: 2026-10-28
scope_approval: W11-B-20261028
---

# Phase 4から移管するWindows最終受入

ユーザー承認により実施時期をPhase 6へ変更。免除や合格判定ではない。
観測正本は [04-WINDOWS-UAT.md](../04-startup-control/04-WINDOWS-UAT.md)、数値は04-05-EVIDENCE.jsonを保持する。

## 2026-10-28 承認済み限定追補

利用者は「案B：単一ログインセッション利用に限定して再計画を承認する」と明示承認。正本は [06-W11-SCOPE-APPROVAL.md](06-W11-SCOPE-APPROVAL.md)。31ケース/110行の全宣言と履歴を保持し、W11の `other-session@script` / `other-session@production-exe` だけを未確認の対象外2行、残る108行を必須とする。下表のnot-runは合格に変更しない。既存の「別session準備不能だけでも出荷停止」の条件はこの2行に限り置換し、他の実機/品質/安全条件は継続する。

| ケース | Phase 6で行う未実施部分 | 状態 |
|---|---|---|
| W01 | 通常/最大化からの最小化復元を実表示で確認 | not-run |
| W02 | 実入力・選択・カーソル・入力先維持 | not-run |
| W03 | 未保存編集と4手Undo/Redoの内容確認 | not-run |
| W04 | fake providerでOCR進捗/完了と状態維持を目視 | not-run |
| W05a/b/c | 入れ子設定・OCR所有messagebox・終了Noの実操作 | not-run |
| W06 | 他process入力中の実OS拒否、有限点滅、15秒後も再前面化なし | not-run |
| W07a/b | slowready/busy実時間証拠と通常表示/期限失効を人手照合 | not-run |
| W08a/b/c/d | 終了・同時claim・旧worker・root消失とOS死亡の観測照合 | not-run |
| W09a/b/c/d | 新通知クリック/入力非干渉/10秒終了、100/150/200%実DPI | not-run |
| W10a/b | medium→elevated/elevated→medium両順、新notice含む4資源/UAC | not-run |
| W11 | 既存別sessionに各1画面、同sessionだけへの復帰と状態不変。将来の保証拡大前の受入として追跡 | not-run / deferred（案B承認、script・production-exeの2行のみ） |
| W12a/c | Python両入口・別配置、Explorer/端末の実入力とforeground照合 | not-run（自動部分は既存pass） |
| W12b/配布統合 | 実PyInstaller EXEとPython/対応版の混在 | not-run（従来からPhase 6担当） |

## 引受とリリース停止条件

- 担当はPhase 6実行担当。Phase 6の計画/UAT/VALIDATIONへ本表全件をID付きで割り当てる。V110-START-01〜03/FOCUS-01/02の最終実機受入も追跡する。
- 実行担当が一時PDF/設定/fake OCR/所有PIDの準備と回収を担い、人がクリック・入力・UAC・既存ユーザー切替・目視を行う。
- 対象commit/OS/Python/Tk/権限/session/入口/観測時刻/判定を記録し、自動・故障注入・実機・未実施を分ける。
- 必須108行に実測根拠付きpassが揃うまでPhase 6完了・リリースを停止する。W11の2行はnot-run/deferredとして残し、正規scope監査に成功した場合だけ今回の必須集合から外す。別項目の準備不能はnot-run/停止を維持し、今回の承認を流用しない。
- W07bの並行負荷15609ms（15.5秒上限を109ms超過）と単独15140msを両方保持する。任意負荷時の上限保証は未実証であり、リリース前に条件と契約の適合性を再評価する。
- 禁止事項3件flagged-unverified、edge5件unclassified/unresolvedを実機証拠と照合し、根拠なくresolvedへ変えない。
- 元の未実施・不採用・時間超過の記録を消さず、新しい証拠を追記する。
