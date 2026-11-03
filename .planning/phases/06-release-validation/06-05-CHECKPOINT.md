# 06-05 本受入の進行（2026-10-28）

## 現在地（G2完了、G3 W05a確認中）

**利用者指定で中断（2026-10-29 00:28 JST）:** `$gsd-pause-work`。W05a配布版 `W05a_nested-settings_at_production-exe-20261028T152307Z.json` は外側13保持/末尾選択/2入力/内側閉鎖、実前景、正常終了、凍結入力保護を照合しpass（raw4点）。W05a require-pass 3/3成功。全体必須24pass/84not-run+W11対象外2。W05bは `tests/test_startup_windows.py` のmanual native-ocrを実1ページ画像PDF/待機server/実OCRDialog._on_closeへ変更し、No後の同dialog/engine/worker/request完了を記録する段階まで実装。対象6件31.04秒成功（`w05b-real-close-20261029.xml`）、141Python Ruff/format/AST成功。W05b driver・記録helperは未実装、正式人手3行は未実施。G3変更後の全件品質は未実施。中断時に所有検証processなし、実行中テストなし、回答待ちなしを確認。再開は `.continue-here.md` と `.planning/HANDOFF.json` から。

**W05a Python両入口pass・配布版準備中（00:21 JST）:** module `...T151926Z.json` は直接回答全て成立、clean、実x→ux input、同外側grab/窓/入力先、正常回収でpass（raw10点）。必須23pass/85not-run+対象外2。直前 `...T151354Z.json` は開始前のTab/x・selection消失をraw9点と利用者補足「PowerShellへ切り替えたつもりでも設定画面のまま」で未成立保存（module計4attempt）。Altを押したままTabで黒いPowerShellを選び案内を確認する手順で解消。現在PowerShell PID10908の配布版runが動作中。利用者へ外側13→内側LLM変更せず閉じる→13保持→末尾3選択、まだEnterなしの準備を依頼中。GUIを重複起動しない。Computer Useは端末操作禁止のため使っていない。

**W05a/module音の合図で再実行（00:12 JST）:** `...T150929Z.json` はpeer前xで選択範囲が消え、検証snapshotが `selection isn't in widget .!settingsdialog.!entry` となりconnection_failed/10141ms。raw9点をnot-run attemptへ保存（module計3attempt）。driverのW05a案内を「最下部英字欄・先にPowerShell Enter・音の後x」に統一し、peer観測後3秒で音を追加。製品/期限変更なし、141Python format/ruff/AST成功。PowerShell PID21840で新run開始し、4段階を1つの案内で回答待ち。次はrunの人回答・実x・監視・正常回収を照合する。

**W05a/moduleの対象欄を明確化（00:08 JST）:** 再確認 `...T150612Z.json` はcleanで実xが英字欄に入り `ux input` へ変化したが、利用者は通常のフォントサイズ等を見ていたと補足。人の保持確認は未成立なのでnot-run attempt（raw10点）へ保存。PowerShell PID5012で新規run開始、利用者が最下部 `unsaved input` 欄を見つけたと回答済み。その欄の保持→x→ux input変化を確認する手順で回答待ち。120秒watchdogは変更していない。次はログ照合、成立したら配布EXE（実フォントサイズ13→内側LLMを変更せず閉じる→末尾3選択→peer→2で12）へ進む。

**W05a/module再確認中（00:04 JST）:** script `W05a_nested-settings_at_script-20261028T150111Z.json` は実x入力/外側grab/文字・選択保持/同一窓復帰/正常終了を照合しpass（raw10点）。module初回 `...T150224Z.json` はpeer中Tab2回・利用者も「Tabを押した」と回答したためnot-run attemptとしてraw9点を保存。製品失敗へ転用せず、PowerShell PID34748でmodule再確認を開始。復帰後3秒待機、Tab/クリックなしでxだけを入力する案内で回答待ち。必須22pass/86not-run+対象外2。

**W05a/script実行中（2026-10-29 00:00 JST）:** 利用者が画面確認可能と回答し、PowerShell PID33508で `W05a/nested-settings@script` を開始。内側LLM設定はharnessで閉鎖済み。外側の文字・選択を確認→PowerShell Enter→自動復帰後3秒待機→x→直接回答を依頼中。重複起動・自動GUIテストを重ねない。準備時に旧nested callbackのgrab=Noneという誤った検証を検出（初回1failed）。既存製品は外側へgrabを戻すため、外側との一致を検証するよう修正し、nestedの既存/人手向け各script/module計4件が21.40秒で成功。Ruff/141Python format/AST、記録helper構文、入力監視機構確認も成功。製品変更なし。新しい人手3行は未判定、全体21pass/87not-run+W11対象外2のまま。

**最新確定（G2完了）:** `g2-closeout-20261028` の全件品質は2242 passed/2 warnings/534.03秒、161入力変更なし、全141Python Ruff/format/AST成功。W03/W04の6行require-pass成功と合わせG2は完了。全体は必須21pass/87not-run+W11対象外2。現在テスト/GUIは動作していない。次はG3のW05a/nested-settingsのPython→EXEを1行ずつ準備・人手確認する。G3はまだ未実施。

**G2本受入完了・全件品質実行中:** `W04_ocr-1page_at_production-exe-20261028T143434Z.json` は進捗はい/結果見えた/サマリなし、同OCR HWND15138932の実前景、POST1・同page/request/attempt・再送/期限切れ0・正常終了/owner空・配布元保護でpass（raw6点）。EXEのrun_idがUUIDでPythonと形式が異なる点を記録helperで正しく照合するよう修正（manifest/dirname/要求run_idの一致を要求、条件緩和なし）。必須21pass/87not-run+W11対象外2。W03,W04 require-passは6/6成功。`g2-closeout-20261028` の全件品質を23:36:18 JSTに開始、pytest PID9316・exec session56919・161入力。実行中は対象コード・台帳・UAT・品質入力を変更せず、人手GUIを重ねない。次は結果を回収してG3/W05a→W05b→W05cへ進む。

**W04/module確定・配布版準備中:** `W04_ocr-1page_at_module-20261028T143122Z.json` も進捗はい/結果見えた/サマリなし、peer78ms、同一OCR要求/状態保持・実前景・正常回収・保護成功でpass（raw13点）。必須20pass/88not-run+W11対象外2。23:32:25 JST、PowerShell PID30916でW04/production-exeを起動。利用者へ1ページ画像PDFを開く操作だけを依頼中。OCR実行・PowerShell Enter前。次はOCR実行→処理中にPowerShell Enter→自動復帰中の進捗→音/結果→直接回答/通常終了。重複起動しない。

**W04/script確定・module実行中:** `W04_ocr-1page_at_script-20261028T142948Z.json` は進捗はい/合成結果見えた/サマリしていない。peer109ms・同OCR HWND10817902の実前景・同dialog/engine/worker/run generationと同一page/request/attempt・POST1・再送/期限切れ0・通常回収・凍結65入力一致でpass（raw13点）。必須19pass/89not-run+W11対象外2。23:30:40 JST、PowerShell PID23480でW04/moduleを起動し同じ画面確認の回答待ち。重複起動しない。

**実行中:** 利用者が画面確認可能と回答し、23:28:53 JSTにPowerShell PID31352で `W04/ocr-1page@script` の本確認を開始。PowerShell Enter→自動復帰したOCR処理中表示→待機解除・音→合成結果の確認→直接回答の順で依頼済み。完了回答待ち。機構確認と同時実行しない・重複起動しない。

**W04の準備完了:** manual OCR harnessを1ページ画像PDF・実OllamaProvider→127.0.0.1のFakeOcrServerへ接続し、POST1/同一dialog・engine・worker・run generationの保持/解放後の合成結果を記録する方式へ更新。待機上限90秒・provider120秒・harness120秒は延長していない。driverは復帰後8秒の処理中表示を経て解放し、結果を見た利用者に直接回答を求める。W04 EXEも同じserver/外部観測/人手OCR経路を追加。実機追加2入口2passed（w04-manual-ocr-20261028.xml、10.09秒）、全141Python Ruff/format/AST成功・監視機構成功。driver selftest `selftest/W04_ocr-1page_at_script-20261028T141926Z.json` は正常終了/同一要求完了/原本保護成功、受入には転用しない。新規合否記録helper `06-05-record-w04.cjs` と品質入力追加（次回161入力）。まだW04人手passなし。利用者へ約1分の画面確認が今可能か質問中、準備できる回答後にW04/scriptを起動する。

**最新確定:** `W03_pdf-3page_at_production-exe-20261028T140922Z.json` をpass記録（raw5点）。利用者による準備途中の先頭横/複製4頁/削除後3頁の確認を経て、4手は4 3 4 3・全て横、復帰直後の編集保持はい。peer exit0後に同HWND13898068/一次31832の実前景、procedure clean、利用者終了確認後closed=true、回収は双方already-exited、owner空・凍結65入力/配布元保護成功。W03 require-passは3/3成功。必須18pass/90not-run、W11対象外2。現在起動中の検証画面なし。次はG2/W04の正式1page画像PDF・loopback fake OCR・POST1・進捗/完了の人手確認を準備する。過去のW03不一致attemptは原因未確定のまま保持し、今回成功で書き換えない。

**最新の操作待ち（23:06:52 JST）:** 利用者はPDFパスを貼り付けられなかったと回答。新しいPowerShell PID29248でW03実EXEを起動し、run `6ec3b952ff8e4ac293a74fb15f33bf09`・一次31832・HWND13898068。Computer Useで対象窓を前面化して読取した時点で、合成PDF3ページ/先頭縦向きがすでに開いていたため、開く入力の代行は行っていない。現在は利用者に「編集モードへ切替→先頭を右90°、まだPowerShell Enterは押さない」の1段階目を依頼中。重複起動しない。後続は2頁複製で4→複製頁削除で3の各準備確認→peer→人の4手Undo/Redo。

**再開位置:** 配布版再確認 `W03_pdf-3page_at_production-exe-20261028T134605Z.json` はinterrupted。run `427c74cadfdc4b3dacefb582c85ce67d` はstopped、一次6132 closed・二次23436 already-exited。利用者は準備できず、止まった段階を「1: PDFを開く」と回答。4手の回答なし。原本5点をnot-run attemptへ追加済み。現在は画面/ボタン不明、パス貼付不可、ファイルエラーのどれかを質問中。起動中の検証画面はないため、古いPowerShellへEnterを促さない。17pass/91not-run+W11対象外2、`audit --allow-pending` は17pass時点で整合成功（出荷不可）。

**最新:** W03/script再確認 `W03_pdf-3page_at_script-20261028T124500Z.json` とmodule再確認 `W03_pdf-3page_at_module-20261028T125331Z.json` をpass記録済み。両方4→3→4→3・各回1ページ目横向き、実trace一致、peer93ms、通常回収・deadline markerなし・凍結65入力一致。scriptの抽象的な質問への「分からない」は書き換えず、同runの復帰直後3ページ/1ページ目横向きを追加回答で確認し別欄へ記録。原本10/11点保存。必須17pass/91not-run、W11対象外2not-run。`audit --allow-pending` は16pass時点で構造成功（final既定モードでは未実施行により不合格となることも確認）。

配布版初回 `W03_pdf-3page_at_production-exe-20261028T125745Z.json` は4手の回答が3 3 3 3で不一致。追加回答「1,2」はサムネイルと表示番号の両方で確認した意味。原本5点を保存してnot-run attemptへ記録済み。同じ凍結EXEの診断コピーでは複製→Undo/Redoが二次起動前後とも4→3→4、通常終了。履歴・操作方法が異なるため元の不一致原因は未確定。詳細 `debug/w03-manual-sequence.md`。

22:43:00 JSTにPowerShell PID34264でW03/pdf-3page@production-exe再確認を開始。利用者へ「Enterはまだ押さず、合成PDFを開く→編集モード→先頭右90°→2ページ目を複製、まだ削除せず4ページを確認」の準備途中の回答を依頼中。重複起動しない。確認後に複製された3ページ目を削除し3ページへ戻す。EXE合格記録helperはまだ未実行。06-07-quality.cjsの次回は160入力、G2確定後の全件は未実施。

W03初回 `W03_pdf-3page_at_script-20261028T123333Z.json` は未完了attempt（原本9点保存）。Undo1=4横、Redo1=4横、後半は画面消失。一次elapsed122829msと120秒watchdogが整合するが、利用者はCtrl+Yを押しても4ページのままと回答。`debug/w03-manual-sequence.md` で調査中。直接4手とTkショートカット4手の各段厳格化テスト3passed、読み取り専用trace追加2passed、全141Python静的検証成功。21:43:15 JSTにPowerShell PID23264で実操作再確認を開始。PageFolio内で4手を行い、ページ数4桁と向きを直接回答する。人手回答待ちで、同じrunを重複起動しない。

G1のW01全6行・W02全9行がpass。`audit --require-pass W01,W02` はexit0/task_ready=true・対象15/15、Phase完了・出荷はfalse。全体は必須108行中15pass/93not-run、W11対象外2not-run。`g1-closeout-diagnostic-20261028` の全件2237 passed/2 warnings/520.03秒・159入力不変・Ruff/format/AST成功。初回台帳テスト修正済み、次のnative Tcl対照群timeoutは単独23件/全件で再現せず原因未確定として原本と追加診断を保持。製品変更なし。

G2/W03のdriverとmanual PDF準備を実装。manual pdfのみ2ページ目を複製し、回転/複製/削除後3ページ・rotations=[90,0,0]・Undo3/Redo0を記録。復帰後の自動4手をmanual時だけ止め、利用者へ1手ずつ直接質問する。実機26passed/1既知warning/114.92秒（w03-manual-prep-20261028.xml）、全141PythonのRuff/format/ASTと入力監視機構確認成功。新規記録helperは06-05-record-w03-python.cjs（未実行、node --check成功）。21:30:35 JST、利用者の対応可能回答を受け可視PowerShell PID31424でW03/pdf-3page@script開始。人手完了回答待ち。G2変更後の全件品質は組の確定後に評価する。

previewの正本は `W02_preview_at_script-20261028T115040Z.json`、`W02_preview_at_module-20261028T115223Z.json`、`W02_preview_at_production-exe-20261028T115433Z.json`。Pythonは実PDF3ページ・選択[1]/表示1・Canvas focusと状態保持・実前景・全直接回答一致、peer109/93ms、正常回収。EXEは0.191秒で同HWND6750324へ復帰、peer exit0後の実前景、38samples/max_gap13ms/errors0/操作0、全直接回答一致。利用者が×→はいで通常終了しuser_close.closed=true、回収は両process already-exited、owner空・保護成功。原本8/8/5点を保存。全て凍結65入力一致。

G1全件初回 `g1-closeout-20261028` は1510passed/1failed/2warnings/92.09秒・159入力不変。失敗はTestCaseCoverageが台帳全体の未実施を指定ID(W01,W02)の不合格と誤って結びつけていた点。テストを対象IDに限定し、一時copyで未実施行/回答なし虚偽passを明示して拒否を検証するよう修正。実台帳・監査実装は変えていない。対象45passed/1既知warning/15.76秒、全141 Python Ruff/format/AST成功。詳細 `debug/g1-uat-audit-scope.md`。

`g1-closeout-fixed-20261028` は2005 passed/1 failed/2 warnings/240.49秒・159入力不変。契約修正箇所は成功し、別のnative Tcl対照群 `[False-False]` が15秒timeout。停止位置が未採取だったため、子の5秒faulthandlerと親のTimeoutExpired出力保存を追加した。期限・合否条件・製品は変更なし。対象全23件は4.39秒で成功（1既知warning）。原因未確定のため診断付き全件 `g1-closeout-diagnostic-20261028` で実行順依存を調べる。新規人手依頼なし。

thumb Pythonの正本は `W02_thumb_at_script-20261028T113122Z.json` と `W02_thumb_at_module-20261028T113300Z.json`。3ページ/選択[1]/表示1、state/target/Canvas focus一致、実前景一致、procedure clean、全直接回答一致、正常回収・凍結65入力一致。原本8点ずつ保存。

thumb実EXE初回 `W02_thumb_at_production-exe-20261028T113526Z.json` は4秒後にPowerShell前景、利用者「5秒を待たずF5を押してPowerShellへ戻った」、終了確認残存でterminated。not-run attemptとして原本5点を保存した。W01のpeer実終了→前景観測→音・読取専用監視をW02へ共通適用し、PDFのある実EXEで通常終了案内を追加。再確認 `W02_thumb_at_production-exe-20261028T114227Z.json` は0.238秒で実自動復帰、peer exit0後の前景一致、43samples/max_gap10ms/errors0/操作0、全直接回答一致。最後のEnter時点ではまだ終了しておらずdriverの早期判定errorが出たが、利用者がその後「はい」を押し同runの回収結果はclosed。原エラーを保持し、同runの最終正常終了・owner空・保護成功を照合してcleanup_reviewに判断を記録しpassとした。期限延長・強制終了のpass化はしていない。原本5点保存。詳細 `debug/w02-exe-observation-cleanup.md` はresolved。

全141 PythonのRuff/format/AST・監視機構全条件成功。最新全件pytestはまだW01時の2233であり、今回変更後の全件は未実施。次はpreview残り3行→G1 require-pass監査→品質確認。新規commitなし。

配布版設定の再実施 `W02_settings_at_production-exe-20261028T112115Z.json` は準備/復帰後とも同じ設定HWND33624606、13の末尾3選択をEnter前に利用者確認、直接回答は出た/入った/保たれた/１つ。primary closed・peer already-exited・owner空・宣言済み設定のみ変化・配布元不変・凍結65入力一致でpass。原本4点をhash付き保存。

W02/thumb@script `W02_thumb_at_script-20261028T112320Z.json` はPDFなし回答。Canvas入力先だけを設定していたharnessの準備不足でnot-run attemptとして原本8点保存。`gsd-debug` の `debug/w02-canvas-missing-pdf.md` で修正中。manual thumb/previewで既存PDF準備後に2ページ目を選択/表示し再描画、focus-resultへページ数/選択/表示を追加、記録helperも非空を必須化した。新規実機テスト4件を追加。初回は既存18件pass後、PDF準備末尾deleteが選択を解除する点を検出して1failed。明示選択修正後は49passed/18deselected/26.88秒（既存18成功は再利用）。全141 PythonのRuff/format/AST成功。全件pytest未実施、製品65入力は不変。20:30:14 JSTに可視PowerShell PID8476で人手再確認を開始した。

moduleの正本 `W02_settings_at_module-20261028T111310Z.json` は全直接回答一致・procedure clean・実設定前景HWND31785570・peer completed/47ms・状態/対象/入力先保持・正常回収・凍結65入力不変。原本8点をhash付き保存した。

配布版初回 `W02_settings_at_production-exe-20261028T111715Z.json` はtarget-ready/after-peerともメイン1窓のみ。利用者は「メインは出た。設定画面はでていない」、追加で「Enterの後で設定画面を開いた」と回答。入力/保持の回答は後から作った状態のためnot-run attemptに保存し、原本4点を保存した。両process already-exited、owner空、配布元不変。driverの配布版設定手順を実フォントサイズ13の末尾3選択→復帰後2で12に明確化し、設定画面未準備なら二次起動前にNotEstablishedで止めるチェックを追加。全141 Pythonの明示Ruff/check/format・AST成功、全件pytestは未実施。20:19:49 JSTに可視PowerShell PID33580で再実施を開始。今回はEnter前に利用者へ準備状況を確認している。製品・ビルド入力は変更していない。

W02/settings@scriptの初回 `W02_settings_at_script-20261028T110310Z.json` は実キー入力「押していない」・保持「分からない」。追加回答「x を押すタイミングが分からなかった」を含めnot-run attemptと原本8点を保存した。操作順を明確にした別run `W02_settings_at_script-20261028T111048Z.json` は直接回答が出た/入った/保たれた/１つ、procedure clean、実前景HWND40833206、state/target/focus一致、peer completed/78ms、正常回収、凍結65入力不変でpass。原本8点をhash付き保存。10秒ごとのtracebackはharnessのdump_traceback_later(10, repeat=True)による定期採取。stderrは既知の破棄後root後始末DEBUGのみ。製品・driver変更なし。W02記録helper2本を追加。台帳更新後の全件pytestは未実施で、下記2233成功はW01確定時の入力に限定する。

正本sessionは06-05-evidence配下の `W01_normal_at_script-20261028T100202Z.json`、`W01_normal_at_module-20261028T100652Z.json`、`W01_normal_at_production-exe-20261028T104332Z.json`、`W01_zoomed_at_script-20261028T104539Z.json`、`W01_zoomed_at_module-20261028T104658Z.json`、`W01_zoomed_at_production-exe-20261028T104946Z.json`。全て直接回答・実観測・正常回収・凍結65入力一致で、原本copy manifestを保存した。不成立attemptは別保持。

`node 06-07-quality.cjs w01-closeout-20261028 05` の単一全件pytestは2233 passed/2 warnings/512.20秒・exit0。証拠 `06-05-evidence/w01-closeout-20261028`、155入力の前後hash不変。pytest PID16940・exec session12713は完了。Ruff check/format/AST成功。`debug/w01-exe-foreground.md` はresolvedとして記録した。今後台帳等が変わるため、この成功を後続の更新済み入力の全件成功へ流用しない。新規commit/pushなし。

## 経過（以下の途中状態は履歴）

06-08は8e83658/4f90cdeで完了。正式な依存照合はPhase04/05ともpassed。台帳確定後の全件2232 passedと151入力不変を本受入開始前に確認した。05-01のカード/台帳/契約は現存実装を照合し、指定クラスを含む192件成功を再利用した。Phase5のH01〜14/意味評価2件は既存正本を保持し再実施しない。

W01/normal@scriptを可視PowerShellから利用者が直接入力した。`W01_normal_at_script-20261028T095542Z.json`。通常・はい・１つ・見える・なし、peer completed/94ms、state_preserved/target_correct/focus_correct=true、最小化から同HWND復元、原本不変、残存processなし。

ただし09:55:09.290477Z、awaiting-enter中のPageFolio前景でEnter(vk13)を検出し、procedure_verdict=keys-suspect/rerun_required=true。本受入passにせず、原文と原ログを保存する。次はPowerShellタイトルバーをクリックして入力先を確実に移してからEnterを押す別runを1回実施する。製品・driver・期限・判定条件は変更しない。

primary stderrの `起動rootの後始末: cannot invoke "winfo" command: application has been destroyed` は `pagefolio/__main__.py:94-100` の破棄済みrootに対する後始末の例外捕捉DEBUG出力。原文を保持し、警告なしとは報告しない。primary正常終了resultと残存なしを別に照合した。未知のクラッシュ/worker例外/Tcl警告が追加発生した場合は停止条件を適用する。

再実施 `W01_normal_at_script-20261028T100202Z.json` は直接入力、procedure clean、peer completed/109ms、同HWND復元・状態保持・正常回収を照合してpassにした。続く `W01_normal_at_module-20261028T100652Z.json` も直接入力、procedure clean、peer completed/78ms、同HWND復元・状態保持・正常回収を照合してpassにした。両runとも製品入力65ファイルは世代5の凍結hashと一致。原ログ8ファイルずつをhash付きで保存し、最初の不成立attemptも保持している。

必須108行中2行pass、106行not-run、W11対象外2行not-run。次はW01/normal@production-exe。今回のattempt・pass追記で台帳入力が変わるため、08末の全件を更新後台帳の合格と称さない。05/06の確定時に品質を再評価する。

配布EXEの初回run `W01_normal_at_production-exe-20261028T101300Z.json` は復元前後の同HWND・同矩形・前景、利用者回答が一致し、追加回答も「最小化前と同じ文字だった」。ただし終了保存した設定ファイルをdriverがoverlay宣言しておらず、verify_after.ok=false。製品の通常保存（app.pyの_quit→_save_window_state）で、配布元不変・正常回収・owner解放は確認できたが、本受入はnot-runのまま原本4ファイルと追加回答をattemptへ保存した。既存runの宣言を書き換えず、新runで設定不存在を事前宣言して再実施する。W01実EXEの質問にもstatus_keptを追加した。現在カード55箇所の準備コマンドに残った旧世代パスを現行世代5へ訂正した（実driverは元から06-BUILD-EVIDENCE.jsonを参照）。

修正確認の初回対象テストは23 passed後、台帳のpreparation.status='established'が既存契約の列挙外と判明して停止。記録helperと2行を既定の'prepared'へ訂正する。回答・観測・判定を変更しない。

訂正後の対象テスト29 passed/1既知DeprecationWarning。全Pythonの明示Ruff check/formatとAST確認成功（directory checkのos error 5警告は保持し、同じ全140ファイルを明示して警告なく再検証）。全件pytestは05の確定前に必要。

配布EXE再確認 `W01_normal_at_production-exe-20261028T101828Z.json` は設定保存の保護検査が成功し、画面状態・矩形・status_keptも一致した。ただし4秒後の前景はPowerShell。利用者は「PageFolioが戻った後、自分でPowerShellへ切り替えた」と回答したため、製品不具合と断定せず観測不成立のattemptとして原本4ファイルを保存した。driverに復帰後10秒間の無操作案内を追加（観測時間/製品期限は変更なし）。新runの可視PowerShell PID13080を19:20:34 JSTに起動し、回答待ち。追加helper `06-05-record-w01-exe.cjs` は実前景・同HWND/矩形・直接回答・事前overlay宣言・正常終了・配布元不変を全て要求する。未実行。

そのrun `W01_normal_at_production-exe-20261028T102221Z.json` はbefore-minimizeが既にiconic、終端前景PowerShell、status_kept入力「尾内」のためnot-run attemptを追加。原本4ファイル保存済み。利用者は「10秒待って確認を完了した」「PageFolioが手前に出て、そのまま10秒間表示された」と回答したが、点観測と食い違うため本受入を止めた。`gsd-debug` 初期化、`.planning/debug/w01-exe-foreground.md` に調査を記録。製品は変更せず、独立診断 `.planning/debug/w01-exe-observe.py` で既存読み取り専用InputMonitorと4/10/14秒の実前景を採取する。診断はacceptance=false。19:28:57 JSTに可視PowerShell PID28416で起動し、直接回答待ち。通常状態確認前の最小化は二次起動せず停止する。新規診断Pythonを含む全Ruff/format/AST成功。実EXEpass記録helperはまだ実行していない。

診断 `observe-20261028T103018Z.json` では0.192秒でPageFolioへ自動復帰、その2.232秒後にPowerShell上の左クリックと前景移動を記録。最大gap13ms/errorsなしの1656samplesで確認した。利用者の「していない」との相違は保持し、クリック主体は断定しない。正式driverでW01のpeer区間のみ連続監視し、他ウィンドウクリックも汚染判定するよう補助を追加した。元状態/最小化の不足はpeerせず停止し、既存4秒観測の終了後だけ音を鳴らす。既存監視+追加3条件の機構確認は、偽サンプラ引数型のテスト修正後に全成功。全Python141ファイルのRuff/format/AST成功。正式runを19:35:37 JSTに可視PowerShell PID32296で開始し、回答待ち。製品・ビルド入力・EXE・期限は変更なし。全件pytestは本受入の安定した区切りで必要。

最新: `W01_normal_at_production-exe-20261028T104332Z.json` を正式passへ記録。元状態を起動直後に記録して最小化後のEnter1回に簡略化し、peerの所有Popenハンドルで正常終了code=0を観測した直後に実前景を取得（外部待機上限4秒・製品期限不変）。0.244秒で同HWND3871154へ自動復帰、正常終了10:43:03.014292Z後の10:43:03.110169Zで実前景一致。監視42samples/max_gap20ms/errors0/クリック0、同矩形、全直接回答一致。正常終了・owner空・配布元不変・設定のみ宣言済みoverlay変更。凍結65入力hashも一致。過去の不成立5attemptは保持。必須108行中3pass/105not-run、W11対象外2not-run。次はW01/zoomed@script。詳細はdebug w01-exe-foregroundを参照。
