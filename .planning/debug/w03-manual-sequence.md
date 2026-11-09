---
status: investigating
trigger: W03の4手確認中に検証用画面が終了し、Redo回答も期待値と異なる
---

# W03の操作確認と時間配分

## 最新: 配布版の4手不一致を切り分け中

本受入再確認 `W03_pdf-3page_at_production-exe-20261028T140922Z.json` は4 3 4 3/全て横/復帰直後の保持はい、通常終了・凍結入力不変でpass。W03 require-passは3/3成功。段階ごとの準備確認は先頭横（call_6dd23058411c41858f57c400fa676201）、複製4頁（call_6226661edf1342cf922282e6762a41ec）、削除後3頁・先頭横（call_f9a57fd30ce0434a811cdbd5f567542d）。Computer Useで対象窓を前面化した時点でPDFはすでに開いており、開く入力や編集操作の代行はしなかった。以降の編集準備/peer/4手/終了は利用者操作のみ。初回3333の原因は未確定であり製品修正による解消とは称さない。原attemptを保持し、現行hashの受入成功とは区別する。

再確認 `W03_pdf-3page_at_production-exe-20261028T134605Z.json` はPDFを開く段階で準備不成立。利用者「4ページにならない・操作できない」、続く段階確認「1: PDFを開く」。rawはEnter1回の後にinterrupted、4手回答なし。runはstopped、一次6132 closed・peer23436 already-exited。原本5点をnot-run attemptへ保存。Computer Useは物理Escapeの停止を検出し、その後の画面操作は行っていない。ファイル自体はrunのfixtures/edit-three-page.pdfに存在（1501bytes）。具体的な開けない状態を追加質問中。

module再観測 `W03_pdf-3page_at_module-20261028T125331Z.json` は4→3→4→3・全て横、trace一致でpass。script/moduleの2行は確定済み。

配布版 `W03_pdf-3page_at_production-exe-20261028T125745Z.json` は利用者が準備3ページ/先頭横を確認した後、4手のページ数を「3 3 3 3」、向きを「全て横」と回答。追加質問の回答「1,2」（call_78a8c0ae76f2486193927a6cc7e18585）はサムネイルと表示番号の両方で確認した意味。peer後の同一窓前景・終了closed・owner空・配布元保護は成立するが、編集継続の期待値不一致は未解決。原回答を保持してnot-run attemptへ記録し、合格にはしない。

診断専用run `release-uat-e4af2709849c485c8ab46d1101648598`（metadata: `w03-exe-undo-evidence/session.json`、acceptance=false）で同じ凍結EXEをComputer Useから操作。合成PDFを開きF5で編集モード、先頭を複製して4ページとし、Ctrl+Zで3ページ/「元に戻しました」、Ctrl+Yで4ページ/「やり直しました」を画面で観測。二次起動PID19652後もCtrl+Zで3、Ctrl+Yで4となった。診断時の一次PID22540、HWND15012436。終了確認「はい」後のS.stop(no-force)は双方already-exited。保存操作なし。

この診断は複製のみの履歴であり、元の回転・複製・削除の履歴とは異なる。入力APIも対象窓をactivateするため、人の復帰後入力と同一とは主張しない。元の不一致原因は未確定。次の本受入では準備中の3→4→3を各段で確認し、同じ履歴を作ったことを直接回答で補強する。製品・凍結配布物は変更していない。

初回 `W03_pdf-3page_at_script-20261028T123333Z.json`、run `pagefolio-uat-pyycc1hv`。復帰は140ms・completed、同HWND14617996、状態保持・手順clean。準備3ページ/rotations=[90,0,0]/Undo3・Redo0。

直接回答は見える→Undo1「4 横」→Redo1「4 横」→Undo2「画面が消えた」→Redo2「画面が消えている」。120秒の試験用watchdogがある一次はelapsed122829msで終了。1手ごとのPowerShell往復で4手の確認が時間内に終わらなかった。期限を延長せず、PageFolio内で4手を確認してまとめて答える案内へ修正する。

ただしRedo1は期限前にYキーの複数押下が観測されている（105.906/107.917秒等）。修飾キーの状態はこの監視では保存していないため、Ctrl+Yが実際に成立したか、製品が応答しなかったかは未確定。利用者へ追加質問中。画面消失だけで説明し切ったことにしない。初回は未完了のattemptとして原文と生ログを保持し、passにしない。

試験用PDFのページ数・回転・Undo/Redo件数を読み取りだけで記録し、次の実操作がどこで止まったかを区別できるようにする。製品コード・配布物は変更しない。

利用者追加回答「Ctrl+Yを押したが4ページのままだった」（call_5ce671a4dab8436a956db14c49d63423）。初回はattemptとして原本9点をhash付き保存。専用exit-auditはこのroleでは作成されないため、終了原因を直接記録したログはない。約120秒の一次終了とwatchdog条件は整合するが、Redo1の不一致を時間切れとして処理しない。

自動継続テストを4手それぞれのページ数・Undo/Redo件数まで厳格化し、Tk Control-z/yイベント経由も追加。直接操作/pdf-shortcuts/OCRの3件が成功（w03-shortcut-diagnostic-20261028.xml、13.03秒）。manual用に50msの読み取り専用状態traceとキー到達時のkeysym/modifiers/操作後ページ数を記録。2入口の追加観測回帰は2 passed/22 deselected（既存22は直前に成功、変更が限定的なため再利用）・8.58秒。全141Python Ruff/format/AST成功。

画面を行き来せず4手後にページ数4桁と向きを答える案内へ変更。期限120秒はそのまま。watchdog発火markerがあればpass記録helperは拒否する。21:43:15 JST、可視PowerShell PID23264で実操作の再観測を開始し、回答待ち。現物台帳W03はnot-runのまま。

再観測 `W03_pdf-3page_at_script-20261028T124500Z.json` は4 3 4 3/全て横、traceも3→4→3→4→3・Undo3/2/3/2/3・Redo0/1/0/1/0。elapsed102266msで通常回収、deadline markerなし。抽象的な「編集が見える」には分からない回答があり、復帰直後・最初のCtrl+Z前の3ページ/1ページ目横向きと説明を具体化して追加質問し、利用者がその表示を確認（call_ddaf7104dc6e46d29753c23963cadf86）。原回答を変更せず追加回答を別記しpass、原本10点保存。実キー到達ファイルは生成されておらず、その採取成功とは称さない。実状態traceと直接回答が照合根拠。初回のRedo不一致は原因未確定・再現なし。

module初回 `W03_pdf-3page_at_module-20261028T124840Z.json` は準備中の2クリックをG1の入力先保持用規則が拒否し、4手質問前にdriver停止。peerはcompleted/63ms・正常回収、not-run attemptで原本9点保存。W03には準備中のクリック禁止という要件がないため、専用w03-preparation区間を使いpeer区間の無操作と区別する。PDF状態/履歴のtrace照合とpeer中のクリック拒否は維持。機構確認に両方向を追加し全条件成功、全141Python静的検証成功。21:52:10 JSTにPowerShell PID28864でmodule再確認中。
