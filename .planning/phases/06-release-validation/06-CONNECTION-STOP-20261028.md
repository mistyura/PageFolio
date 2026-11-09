# Phase 06 W05b接続実証の停止（2026-10-28）

## CHECKPOINT REACHED

**Type:** human-verify  
**Gate:** blocking-human  
**Plan:** 06-04（世代3）  
**Progress:** 1/2 tasks complete  
**Current Task:** 06-04-02、W05b自動復帰未実証で停止

準備監査はexit1、理由は「接続(w05b-modal): native modal→peer→いいえ→同処理完了の観測が不足です」の1件だけ。06-04-02未完了、06-05停止/06-06not-ready、全110受入not-run、Phase未完了・出荷停止を維持する。同条件再試行・driver/製品修正・追加GUI/build・commitは行っていない。

## 実観測と回答の分離

| 試行 | 記録した事実 | 判定 |
|---|---|---|
| sandbox ocr-single `d04061c65a42406c90736c4a3e183368` | 利用者「PageFolio の画面が見えない」。primary30532はclosed、driver26332は親が作成時刻/command照合後に回収。main session原本なし、manifest/初期証拠あり | 未成立。接続pass禁止 |
| native ocr-single `0d73a0cdf5b8465f9970b3702c2653e7` | 同1POST/1received/released/completed。peer後前景はOCR/primary28824。回答「「PageFolio UAT 合成OCR結果」が表示され、既存画面へ戻れた」。primary28824はterminated、peer28104already-exited、stop診断あり | 合成OCR接続の事実を記録。強制回収を正常終了へ書換えない |
| native w05b-modal `cf52cf1df4db42a3b384db6f13a6c103` | native modal HWND6753582がpeer前後同一。peer後前景はHWND396656/PID18044/「⠴ 実行 フェーズ06 \| PageFolio」でprimary9920と不一致。No後OCR維持、同request完了。primary9920closed/peer4192already-exited | `modal_shown=true`、`peer_returned_to_modal=false`、`answered_no=true`、`same_request_completed=true`。自動復帰未実証 |

W05b元sessionの原文4回答はそのまま保持した。

1. 「確認ダイアログが表示された（ボタンはまだ押していない）」
2. 「同じ確認ダイアログが前面に戻っている」
3. 「OCR ダイアログが残り、処理と入力が維持されている」
4. 「同じ処理が完了し「PageFolio UAT 合成OCR結果」が表示された」

親の追加質問「2 回目の起動後の見え方を確認させてください。確認ダイアログへ PageFolio が自動で戻りましたか、それとも自分で PageFolio に切り替えて確認しましたか？」への補足原文は**「自分で PageFolio に切り替えて確認した」**。`w05b-user-clarification.json`へ別保存し、最初の回答を自動復帰成功と解釈することを取り下げた。元sessionは変更していない。

## 証拠の保全と台帳

原本rootは`C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g3_unreadable_8433fc4ee5324234931fb80ac0f310d1/runs/`。run metadata/evidence/fixture/overlay-source計22ファイルを`06-CONNECTION-STOP-20261028-evidence/runs/`へcopyし、`original-hashes.json`で元path/copy/SHA256を保存した。配布distは再copyせずmanifest全件/EXE/treehashをread-only照合した。

既存`assemble_protection.py` mainは実行せず、`load_session`/`build_connection` helperの出力と派生理由を保持した上で、generation=3の`connection`へ2行を追記した。旧世代/自動保護/設定障害/失敗原本と110not-runは保全。run参照は旧16と新3runを含めて機械同期した。

台帳更新前の局所文書とSTATE/state.jsonも`evidence/before/`へ保存。source session hash・helper生出力・補足・preparation-only stdout/stderr・配布/owner/PID観測・保全最終確認を同dirへ保存した。

EXE SHA256 `9b3ebbce390c3b9f1752a97820a5ef81a0c39b7e148b93717b86bb47f9f5f73b`、tree SHA256 `cce2fd0a99a6f368ab271f9f0b6a212c3984a6387c7684800074434d5152ccf4`は不変。固定namespace ownerなし、今回PID30532/26332/28824/28104/9920/4192は現存なし。W05bのsettings overlay終了時変化は配布immutable treeの変更と区別した。

## 検証と次の入口

Phase04fresh、品質停止resolved、Python137/137一致の2071件成功は維持し、全件を反復しない。製品/tests/版/AGENTS/pyproject/indexは変更していない。

停止同期後の局所DoD/リリース契約の初回は、今回ランナーのbasetemp親directory不存在で30 passed/17 setup errors/1 warning/1.46秒、exit1。`document-tests.stdout.txt`等へ原本保持し、製品/試験assert failureとは区別する。親の指示で既存Temp直下の新規一意pathへ修正し、修正後attemptを1回だけ別ログへ記録した。結果は**47 passed/1 warning/10.77秒/exit0**。最終保全確認も`ok=true`で原本22件/copy全hash不変、137Python/保護対象/index/旧世代/手動台帳/build保全、PID6件なし。正本は`final-verification-corrected.json`と`document-tests-corrected.stdout.txt`。警告は既知PyMuPDF ByteString廃止予告。

次は`$gsd-debug phase06-w05b-manual-switch`。実foreground採取時刻とチャット回答/手動切替による影響を限定調査する。製品不具合や原因を断定せず、既存owner_missing/DEP-05等の原因解決とも混同しない。停止解除の根拠が揃うまで接続再試行・06-05/06・Phase完了・出荷を進めない。
