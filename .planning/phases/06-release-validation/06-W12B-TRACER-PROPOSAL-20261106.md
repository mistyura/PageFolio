# W12b 旧 tracer 消失時の準備案（2026-11-06）

## 結論

W12b の別版2行に指定された 06-01 技術 tracer（v1.9.1、旧 EXE SHA-256 `c082f6f4c35af75f07e574f2ef30f41c25e41965f7f9f17a8b65ac71e9183ba7`、run `2db21a6b3e8b4aed80d92adc3a521668`）は、記録された `%TEMP%` 保持先の指定位置で EXE・埋込 report・外部 report・履歴を確認できなかった。旧 hash を新規 binary に結び直すことはできない。別版2行は `not-run` のままとし、最終固定 EXE v1.10.2（SHA-256 `66be5df663e333057c5c3cde02180857f930d2433e377f69c2838432d49a19d4`）は再 build・変更しない。W12b の残る7行は tracer と別の相手を用いるため、各行の固有ゲートを満たすなら独立に進められる。

元の `06-05-PLAN.md:84-88` は「06-01で作成・保持した実 PyInstaller tracer」を指定し、保持物・manifest・実版・対応実装を照合できなければ当該行を `not-run` とする。**新たな tracer は契約上の相手を自動的に置き換えない。** 採用する場合は新しい来歴を記録し、06-05計画・W12bカードの相手情報を明示的に更新したうえで、実機の両方向を新規に受け入れる必要がある。技術 tracer を公式旧版や最終 EXE 受入済みと呼ばない。

## 読取で確定した根拠

| 項目 | 根拠・判断 |
|---|---|
| 旧生成 | `06-01-SUMMARY.md:79-95` は Task 1 commit `509e05c37a9dbdee0364a36a398ef1c9d6058ac5`、Task 2 commit `db7ba213130cf6e63dc13c69929b001ce58b002f`、59秒の初回 build と32秒の管理済み再 build を記録。Task 2 ログ `06-01-task2-rebuild-cli.txt:1-6` は旧 TEMP 下の `PageFolio-v1.9.1` 成功のみを示す。`06-UAT.md:24-29` が旧 run/hash を台帳上で特定する。 |
| 旧保持先 | `C:\Users\shdwf\AppData\Local\Temp\pf06_tracer_acce06df0c694f10be4a1ed80f690793` の `PageFolio-v1.9.1/release-report.json`、`.release-work/2db21a6b3e8b4aed80d92adc3a521668/report.json`、`.release-history/2db21a6b3e8b4aed80d92adc3a521668` はいずれも存在しない。旧 report の完全な manifest・依存版・tree hash は今回の限定調査では復元できない。広い TEMP 探索は行っていない。 |
| 対応実装 | `git show 509e05c:pagefolio/constants.py` と `git show db7ba21:pagefolio/constants.py` はともに `APP_VERSION = "v1.9.1"`。両 commit 間の `pagefolio/`・入口・icon・配布文書・requirements の差分は空。`db7ba21:pagefolio/startup_win32.py` は `PageFolio.Startup` の固定 namespace、`Local\...Owner`/`.State`、protocol 1 を持つ。現行 `pagefolio/startup_win32.py:443,543-544,693,746,1350` も同じ主要識別子を持つ。ただしソース照合は実機互換の合格証拠ではない。 |
| build の入力と来歴 | `tools/build_release.py:286-301` が入力 manifest を列挙し、`:304-320` が `technical-tracer`・`release_allowed=false`・`manual_uat=not-run` を固定する。`:371-378` の `source_commit`/`dirty_sha256` は入力元で `git rev-parse HEAD` が成功した場合のみ付く。`:391-409` は現 Python の PyInstaller を起動。`:514-520` の CLI 引数は `--output-root` のみで、`--repo` や checkout 指示はない。`:305` により実行した `tools/build_release.py` の親の親が入力元となる。`db7ba21` と現行 CLI の当該コード差分は空。 |
| 環境差 | `db7ba21:requirements.txt` は PyInstaller 6.21.0、PyMuPDF 1.28.0、Pillow 12.3.0、tkinterdnd2 0.6.2。現 `.venv` の読取値は Python 3.15.2、PyInstaller 6.22.3、hooks 2026.9、PyMuPDF 1.28.2、Pillow 13.0.0、tkinterdnd2 0.6.4。現環境利用なら**旧 binary の再現ではなく新しい build**であり、実 report の版を記録して評価する。新規 install は準備案に含めない。 |
| 相手と行数 | `06-UAT.md:1244-1491` に W12b 9行。tracer 指定は `exe-tracer@production-exe`（`:1389-1416`）と `tracer-exe@tracer`（`:1418-1445`）の2行だけ。他7行は同版別配置、script、module との組合せ。最終 EXE は `06-UAT.md:24-26` と `06-BUILD-EVIDENCE.json:81-86` に固定。 |

## 推奨する新成果物の準備（承認後に実施）

1. 親が `db7ba213130cf6e63dc13c69929b001ce58b002f` の**最小 source export zip**を、元 repo の製品ソースを編集せず作る。必要な tracked path は `pagefolio.py`、`pagefolio/`、`pagefolio.ico`、`requirements.txt`、`tools/build_release.py`、`distribution/`、`docs/CONFIGURATION.md`、`.gitattributes`。export に tracked `dist/PageFolio.exe` を入れず、旧 EXE として起動しない。zip SHA-256、commit ID と親、`git ls-tree` の path/blob ID 一覧、export 中の各ファイル SHA-256 を保存する。`509e05c` は Task 1 実装の起点、`db7ba21` は Task 2 完了版であり、製品入力が両者で不変なため後者を新 build の候補とする。これは旧 run `2db21…` の入力が完全一致したという主張ではない。
2. build 用には**隔離したローカル Git clone**を空の永続領域に置き、`db7ba21` へ detached checkout する。source zip の展開だけでは CLI report の `source_commit` が `null` になるため、clone の Git metadata が必要。例: `git clone --no-local --no-checkout <元repo絶対パス> <隔離source>`、`git -C <隔離source> checkout --detach db7ba213130cf6e63dc13c69929b001ce58b002f`。clone と zip の対象ファイルを SHA-256 で照合し、`git -C <隔離source> status --porcelain` が空、`rev-parse HEAD` が期待 commit、`git diff HEAD --binary` が空であることを記録する。出力 root は隔離 source 外の新規・空の永続 path（例: `%LOCALAPPDATA%\PageFolio-validation\w12b-tracer-<GUID>\output`）にする。既存の失われた TEMP root と最終 EXE 保持先は使わない。
3. 新 clone の `tools/build_release.py` を現 `.venv/Scripts/python.exe` で `--output-root <新規output>` 指定で1回実行する。**現行 repo 側の build script を実行しない。** CLI 自体は checkout せず、repo を選ぶ CLI 引数もない。成功時に外部 `report.json` と埋込 `release-report.json` の run、`source_commit=db7ba21…`、空差分 SHA-256、入力 manifest、実依存版・Python、APP_VERSION、EXE/tree SHA、`artifact_role=technical-tracer`、`release_allowed=false` を照合・保存する。失敗時は失敗物を保持し、W12b 別版2行を `not-run` のままとする。
4. 対応実装のソース manifest と同世代の自動証拠を照合し、最終 EXE と新 tracer の絶対保持先・run/hash・環境を W12b 相手欄に別々に記録する。実機確認は各配布元の**完全 copy**上で行い、`exe→tracer` と `tracer→exe` の一次1画面・同 session 復帰・元状態維持をそれぞれ人手確認する。新 tracer の build 成功だけで2行を pass にしない。計画/カードの代替来歴変更と正式台帳更新は、利用者が新成果物・変更案を確認した後に行う。

`git clone` はローカルの既存 Git object を使い、追加 package install を要しない。古い requirements と現 `.venv` は一致しないため、事前に「現環境 build の新規成果物を別版相手として認めるか」を明示する必要がある。旧 `c082f6f4…` の再現・元 run の復旧・旧 tree hash の推定はしない。

## 利用者に提示する選択肢と承認境界

| 選択 | 利用者が確認する具体物・効果 | 承認後の作業範囲 |
|---|---|---|
| **A（推奨）新 tracer を準備** | 上記 `db7ba21` の source export zip/manifest、隔離 clone と空の永続 output path、現 `.venv` の依存差、旧 hash を引き継がないこと、2行の計画/カード変更案を確認する。 | **新規技術 tracer を1回 build し、新 run/hash と source/環境 report を採取・照合する承認**。build 後も2行は実機受入まで `not-run`。最終 EXE は不変。正式相手の差替え・人手 UAT はその具体的成果物を示して別途判断する。 |
| **B 別版2行を保留し7行を進める** | 旧 tracer の保持物欠落を認め、別版2行を `not-run` のままにする。 | tracer build なし。残る7行だけ各カードの固有ゲートと人手観察で進める。W12b全件合格や release 承認はしない。 |
| **C 指定済みの旧保存先を確認** | 利用者が旧 binary/report の**具体的な絶対 path**を把握している場合に限る。 | その path だけの read-only SHA/report/manifest 照合。旧記録と一致するまでは別版2行 `not-run`。広域探索や再 build は含めない。 |

現時点では提案の読取調査のみで、source export、clone、build、GUI、pytest、台帳変更は未実施。W12b 別版2行の未準備状態と `release_allowed=false` を維持する。
