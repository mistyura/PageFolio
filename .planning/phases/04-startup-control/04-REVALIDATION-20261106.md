# Phase 04 再検証（2026-11-06、native確認窓の試験時序修正後）

## CR-02修正後の現行ゲート（最新）

独立レビューで発見したCR-02は、v3 validatorと正式helperのdecisionを「採用」と厳密比較して修正した。RED XMLで修正前v3の否認受理を再現し、v2/v3×否認7種×dry-run/書込の28ケースと既存肯定例を含む対象107件が成功。独立再レビューでCR-02 fixed、現行critical0/warning1を確認した。旧否認値を新しい採用値へ書き換えて既存証拠を採用する処理はない。

修正後の正本は `04-reverify-20261106-cr02/`。2026-11-06T10:03:26.865Z〜10:13:15.106Z、**2361 passed / 2 warnings / 587.24秒 / exit0**、JUnit failure/error/skip各0、標準エラー空。170入力の前後/現行一致170/170、missing/changed各0。Ruff check・148ファイルformat check・AST全てexit0/標準エラー空。148件にはREDの隔離fixtureにある合成Python2件を含み、製品・試験実装は従来146件。`04-QUALITY-CR02-20261106.json` に原本hash/現行照合を保存した。

Nyquist→Security→既存静的UIの順に新JUnitへ再結合し、Phase04対象299件、W05c証拠39件/runner68件は全てpass。6 PLAN/13タスク/5要件の既存対応に不足なし。ASVS L1の22脅威はclosed/open0、UIはpartial/visual_capture not-run/score nullのまま。Code review/dispositionはCR-01/CR-02 fixed、WR-01 deferred、open0/total3。現マイルストーン先頭フェーズの回帰として同じ全件を再利用し、追加全件を実行しない。残るゲートは独立goal verifierとCLIによるcovered fingerprintの再生成である。

以下の2333件はCR-02修正前の履歴であり、現在のソースの全件成功へ付け替えない。

## 初回証拠と変更範囲（CR-02修正前の履歴）

利用者の「残作業1-3を実施」により、GSD resume → execute-phase 04 の検証再開経路を実行した。既存6 PLAN/6 SUMMARYは再実装しない。過去の失敗原本・未コミット差分を保持する。

単一全件の正本は `04-reverify-20261106-native-fix/`。2026-11-06T08:55:09.309Z〜09:05:11.860Z、pytest **2333 passed / 2 warnings / 600.06秒 / exit 0**。JUnitは2333件、failure/error/skip各0。170入力の前後hash一致、missing/changed各0。Ruff checkはexit0、format checkは146件変更不要、ASTはexit0で、各stderrは空。旧修正後2333件成功の申告には全入力manifestの参照がなく、現在bytesへ再結合できなかったため、この1回だけを新規実行した。

前回v3全件の170入力との差分は `tests/test_startup_windows.py`、`.gitignore`、`開発履歴.md`。製品コードは同一である。native確認窓が可視・親無効化済みになってから `focus-ready` を発行する試験修正を確認した。20秒の出現待機、popup出現起点の30秒自動閉鎖は試験側だけの期限で、製品の二次起動5秒契約を変えない。manual経路は自動Noを行わない。

## 必須ゲート（順に実行）

| 順 | ゲート | 判定 |
|---|---|---|
| 0 | 単一全件・入力同一性 | 上記2333件成功。170入力の現在hashを再照合してから採用する |
| 1 | Nyquist | 6 PLAN/13タスク/5要件と既存Per-Task Mapを照合。DoD19、control52、focus32、foreground_audit24、notice61、wake23、windows88の299件が全てpass。W05c証拠39件/runner40件は別の計測回帰で、人手受入へ算入しない。新規MISSING/PARTIAL 0 |
| 2 | Security | ASVS L1、計画時22脅威の緩和先と現行製品の同一性を確認。試験時序修正は所有popupの読取と既存所有process内の自動対照だけに限定。closed22/open0を継承。人手操作・実EXE・権限差の未受入を免除しない |
| 3 | UI | 製品文言・描画・配置は不変。既存6柱の静的所見だけを再利用し、partial / visual_capture not-run / score nullを保持。実画面/DPI/UAC/EXEを成功扱いにしない |
| 4 | Code review / disposition | 独立レビュー待ち |
| 5 | Regression | 現マイルストーン先頭フェーズ。299件を含む同一全件を利用し、成功済みpytestを重複起動しない |
| 6 | Goal verification | 独立検証・fingerprint再生成待ち |

## 未解除事項

極端な過負荷で送信済みIDNOがMessageBoxを閉じない未解明モード、WR-01の15609ms/15140ms、DEP-05、owner_missing、前景要求元不明、元W05cのNo不成立原因を解決済みにしない。Phase04禁止3件flagged-unverified/edge5件、正式台帳28pass/80必須not-run/対象外2、06-06未開始、出荷不可を維持する。今回の自動成功は正式script/EXE受入ではない。
