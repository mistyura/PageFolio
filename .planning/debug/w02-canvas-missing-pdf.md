---
status: resolved
trigger: W02/thumb@script の直接回答が PDFなし
---

# W02 Canvas受入のPDF準備不足

## 原因と証拠

`06-05-evidence/W02_thumb_at_script-20261028T112320Z.json` の回答は出た/変わった/戻った/PDFなし/1つ。procedure clean、peer completed/47ms、Canvas focusとstate_preservedはtrue、正常回収。ただし `tests/test_startup_windows.py::_prepare_focus_case` のthumb/preview分岐はCanvasへfocus_setするだけでPDFを用意していなかった。空の文書・選択同士の一致は、実PDFでの選択保持受入の根拠にならない。製品の復帰失敗ではなく検証準備の不足。

当該行はnot-run attemptとして回答・原ログ8点を保存済み。過去の生ログを変更しない。

## 修正

- manualのthumb/previewで、既存の隔離PDF準備関数を先に実行する。製品コード・実EXE・凍結65入力は変更しない。
- focus-resultへ実文書ページ数・選択ページ・表示ページを記録する。
- PythonのW02記録helperは、Canvas受入で実文書と範囲内の選択/表示ページが存在することも要求する。
- 既存の実ウィンドウ復帰テストへmanual thumb/preview×script/moduleの4件を追加し、3ページ・有効選択/表示・状態保持・入力先保持を検証する。

## 検証

全141 PythonのRuff check→format→再check、pagefolio.py/driver/test_startup_windows.pyのAST成功。対象pytest実行中: `test_focus_restore_real_main_windows`、`TestCaseCoverage`、`TestEvidenceAudit`。XML: `06-05-evidence/w02-pdf-prep-tests-20261028.xml`。

初回対象pytestは既存18件pass後、新規manual thumbでselected_pages=[]を検出して停止した（1 failed/18 passed/82.34秒）。既存PDF準備の末尾delete操作が選択を解除していたため、manual Canvas準備で2ページ目を明示選択・表示し、再描画する修正を追加した。失敗XML/basetempを保持し、別basetempで対象試験を再実施する。

修正後の追加4件と台帳契約は49 passed/18 deselected/1既知warning/26.88秒。18件は初回成功済みで、今回修正がmanual分岐だけのため対象再実行を限定した（受入ケースの除外ではない）。XML: `06-05-evidence/w02-pdf-prep-fixed-20261028.xml`。全141 PythonのRuff/check/format・ASTも成功。

実画面再受入 `W02_thumb_at_script-20261028T113122Z.json` は出た/変わった/戻った/保たれた/１つ。3ページ、選択[1]・表示1、状態/対象Canvas保持、実前景HWND15995460、peer completed/109ms、procedure clean、正常回収、凍結65入力一致。原本8点を保存し当該行をpass。準備不足は解消した。全件pytestは05確定前に必要で、本診断のresolvedをPhase完了・出荷許可にしない。ビルド再作成は不要（tests/test_startup_windows.pyは配布用65入力に含まれないことを現行release-report.jsonで照合）。
