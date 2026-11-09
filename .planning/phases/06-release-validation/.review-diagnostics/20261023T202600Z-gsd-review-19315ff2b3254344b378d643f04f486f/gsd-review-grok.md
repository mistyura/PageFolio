Phase 06 の6計画を、参照元の実装と受入正本まで追って読み取り専用で照合します。まず計画本文と、引用されている現行コード・ゲート資料の所在を確認します。計画は6ファイルとも短いので、本文と受入正本を突き合わせて依存と停止条件を追います。計画の停止条件と実装接点が、現行の定数・設定読込・受入正本と一致するか追います。Phase 06 の6計画は、未実施を合格にせず、Phase 4 の stale と未解除回帰を出荷停止に残す骨格は保てています。実行前に直すべきなのは 06-01 の検証定義です。このままだと、安全境界の試験より前にリポジトリの `dist` へ実 PyInstaller が走り、原本サンプルを巻き込む実装でも検証コマンドを満たせます。pytest は実行していません。未作成の `tools/build_release.py` と `distribution/samples/` は、計画どおり未実装であるだけで欠陥ではありません。

## 06-01

### 要約

`tools/build_release.py` を単一入口にし、既存2サンプルを出力外の正本へバイトコピーしてから、私有領域で onedir を作り、EXE の隣へ同梱して SHA-256 を照合し、検証後だけ版付きフォルダへ公開する計画です。保護対象がある出力先ではビルド前に止まり、失敗物は `INCOMPLETE` として残します。

### 強み

- 正本の配置が現行の消失構造と一致します。サンプルはいま `dist/PageFolio/` だけにあり、`--noconfirm` の再ビルドで消えます（`docs/DEVELOPMENT.md:85-103`）。計画は `copyfile` と元ファイル保持を先に置いています（`.planning/phases/06-release-validation/06-01-PLAN.md:94`）。
- 保護3名は定数のリテラルそのものです（`pagefolio/constants.py:15-22`）。AST 読取なら、`constants.py` 先頭の `lang` / `themes` import（同ファイル `8-9`）を実行せずに済みます。
- 外部ファイルの解決先は frozen 時 `sys.executable` の隣です（`pagefolio/settings.py:33-50,85-101`）。EXE 隣への後処理コピーは、この契約と README の `_internal` 分離（`README.md:21`）に合います。
- 失敗保持、公開直前の再検査、2段階 rename が原子的ではないこと、レポートへの設定本文・APIキー非収集まで書いてあります（`06-01-PLAN.md:94,111`）。
- 禁止事項は `unresolved` のままです（`06-01-PLAN.md:41-47`）。計画合格を出荷承認にしていません。

### 懸念

- **HIGH** — 実ビルドの検証が、境界試験より前にリポジトリの `dist` へ向いています。06-01-01 の2つ目の検証コマンドは `.venv/Scripts/python.exe tools/build_release.py --output-root dist` です（`06-01-PLAN.md:99-100`）。同じタスクの `fails_when` は pytest 側にも「実 PyInstaller 未実行」を要求します（`06-01-PLAN.md:96-98`）。一方 read_first は fake builder と tmp 上のバイト照合です（`06-01-PLAN.md:92`）。argv の本文には `--distpath` / `--workpath` / `--specpath` と入口 `pagefolio.py` がありません（`06-01-PLAN.md:94`）。現行の公式手順は出力先が `dist/PageFolio/` です（`docs/DEVELOPMENT.md:63-78`）。ここを私有領域にしない実装は、追跡済み原本を再作成に巻き込みます。境界試験はその次のタスクです（`06-01-PLAN.md:105-117`）。
- **MEDIUM** — 「旧 `dist/PageFolio` と重なる指定は拒否」と、既定 `--output-root dist` が同じ文にあります（`06-01-PLAN.md:94`）。拒否対象が最終ディレクトリ `dist/PageFolio-<APP_VERSION>` なのか、親の `dist` なのかが未定義です。親まで見ると、中にある追跡済み `dist/PageFolio` のせいで既定コマンドが毎回停止します。最終ディレクトリだけ見ると、兄弟フォルダとして共存できます。`.gitignore:9-14` の再許可と、後段の `dist/` 無視（`.gitignore:74`）は、新規の版付きフォルダを未追跡のまま置く方針と一致します（`06-02-PLAN.md:104`）。
- **MEDIUM** — junction と古 lock の判定 API が未指定です（`06-01-PLAN.md:111`）。Windows の directory junction は `os.path.islink` では見えません。生存未確認の lock を奪わない、までは正しく、PID 再利用とクラッシュ後の永久 lock のどちらで判定するかがありません。
- **LOW** — ガイド `distribution/はじめに.md` を版同期前に同梱します。最終証拠は 06-04 で取り直すと書いてあり、この時点の成果物を v1.10.0 の配布証拠にしなければ問題になりません。

### 具体的提案

1. 06-01-01 の pytest は fake builder、私有一時ディレクトリ、builder 引数の断言だけにする。「実 PyInstaller 未実行」は実 CLI の `fails_when` にだけ残す。
2. 実 CLI は 06-01-02 の保護・故障・再ビルド試験が緑になった後に1回だけ実行する。`--distpath` は `dist/.release-work/<run-id>/` 配下であり、`dist` でも `dist/PageFolio` でもないことを argv 断言で固定する。入口は `pagefolio.py`、`shell=False` を本文に書く。
3. 重なり拒否は解決後の最終ディレクトリに限定し、兄弟の追跡済み `dist/PageFolio` は削除・再作成・stage しない、と書く。
4. reparse は祖先を含め `Path.is_junction()` または `FILE_ATTRIBUTE_REPARSE_POINT` で拒否する。lock は PID とプロセス生成時刻が一致するときだけ生存とみなす。

### 総合リスク

**HIGH**。安全方針は実装可能ですが、検証コマンドの取り違えが原本喪失と、全件 pytest への非隔離ビルド混入の両方に届きます。

## 06-02

### 要約

`APP_VERSION` を `v1.10.0` にし、README・開発履歴・同梱ガイド・`docs/DEVELOPMENT.md` を同じ版と非破壊手順へ揃える計画です。版の第二定数は置きません。

### 強み

- 真の情報源はいま `APP_VERSION = "v1.9.1"` で、README バッジも同じ文字列です（`pagefolio/constants.py:12`、`README.md:7`）。計画は CLI へ別定数を足さないと明記しています（`06-02-PLAN.md:89`）。
- 利用者手順はサンプルを実利用名へコピーし、衝突時は両方を残す方針です（`06-02-PLAN.md:104`）。これは `CUSTOM_PROMPT_FILE` / `SUMMARY_PROMPT_FILE`（`pagefolio/constants.py:21-22`）と、Apply 時だけ書き戻す現行契約（`docs/CONFIGURATION.md:114-120`）に沿います。
- 破壊的な退避→再ビルド手順の置換先が、06-01 の単一 CLI です（`docs/DEVELOPMENT.md:85-103`、`06-02-PLAN.md:104`）。
- 文書試験を通すために未完了 UAT を pass へ書き換えない、とあります（`06-02-PLAN.md:87`）。`tests/test_gsd_dod.py:243-249` は、ROADMAP 上未完了の現行フェーズを `validated` 要求から外すので、Phase 6 実行中の draft（`06-VALIDATION.md:4`）と両立します。

### 懸念

- **LOW** — 詳細リンクが `main` 上の GitHub URL です（`06-02-PLAN.md:104`）。このフェーズは merge も Release も含みません（`06-06-PLAN.md:104`）。同梱ガイドが最短手順を持てば、現行 `docs/CONFIGURATION.md:100-125` への到達自体は可能です。試験がリポジトリ内のパス存在だけを見ると、公開ブランチの遅延は検出できません。
- **LOW** — `docs/DEVELOPMENT.md:111` の Ruff `0.15.20` は、ピン `ruff==0.17.1`（`requirements.txt:10`）とずれています。ビルド節の置換範囲外なら残ります。

### 具体的提案

詳細 URL は、同梱ガイドの手順完結を前提に「リポジトリの `docs/CONFIGURATION.md`。公開ブランチはリリース反映後に一致する」と役割を分ける。Ruff の版表記は、今回のビルド節を触るならピンに合わせる。

### 総合リスク

**LOW**。版の単一情報源と、未実施を成功と書かない契約は実装可能です。

## 06-03

### 要約

実配布ツリーの完全コピー、所有 PID、証拠 audit、loopback fake OCR、設定障害の準備を作ります。audit は `--allow-pending`、`--for-handoff`、flag なしの3モードで、未実施を pass に補完しません。

### 強み

- HTTP 形状が現行プロバイダと一致します。POST は `{url}/v1/chat/completions`、応答は `choices[0].message.content`、モデル一覧は `data[].id` です（`pagefolio/ocr_providers/ollama.py:94,132-136,158-189`）。`http://127.0.0.1` は許可スキームです（`pagefolio/ocr_providers/base.py:14-32`）。
- 本番 mutex は `Local\PageFolio.Startup` で、版やパスを名前に含めません（`pagefolio/startup_win32.py:442-444,542-543`）。試験引数を EXE へ渡さず、既存 owner がいたら送信しない（`06-03-PLAN.md:100`）は、この共有名前空間で必要です。
- 読取失敗は原本を書き換えません（`pagefolio/settings.py:261-320`）。保存は `pagefolio_settings.json.tmp` を `open(..., "x")` してから `os.replace` です（`pagefolio/settings.py:367-398`）。計画の共有ロックと tmp 専有は、この失敗分類に接続できます（`06-03-PLAN.md:115`）。
- 起動直後の自動保存はありません。`_save_settings` は明示操作か終了時です（`pagefolio/app.py:669-699,766-778`）。起動安定後・終了保存前の hash 比較は成立します。
- 親4ゲートだけ pending の引渡しを、最終合格と分ける fixture が指定されています（`06-03-PLAN.md:77-84`）。循環依存を避ける書き方です。

### 懸念

- **MEDIUM** — audit の正否がフェーズ完了そのものを決めます。fixture 試験を実証拠へ転用しない、とは書いてあります（`06-03-PLAN.md:84`）。3モードの実装ミスは、後続の人手 pass を機械的に通します。負荷は正当で、省略すべき過剰設計ではありません。
- **LOW** — `dist/PageFolio-v1.10.0` は 06-04 で初めてできます（`06-03-PLAN.md:36`、`06-04-PLAN.md:80`）。06-03 の試験は隔離 fixture だけで完結させる必要があります。本文は製品の import と patch を禁止しており、その読みで実装できます（`06-03-PLAN.md:100`）。

### 具体的提案

`TestEvidenceAudit` の負例に、人手 not-run、Phase 4 stale、品質失敗、既知 high 未解消、対象 hash 不一致を `--for-handoff` でも失敗するケースとして残す。現行計画の列挙を実装チェックリストに落とし、fixture の JSON を本番台帳のテンプレートファイルとしてコピーしない。

### 総合リスク

**MEDIUM**。接続先のコードは追えます。リスクは audit の実装複雑さに限られます。

## 06-04

### 要約

v1.10.0 で同じ CLI の初回ビルドと再ビルドを実測し、保護3名の事前停止、起動・更新時の原本保持、未改変 EXE から loopback fake OCR への接続を記録します。

### 強み

- 2つの EXE の bit 一致は要求せず、各入力と各成果物の hash を別記録にします（`06-04-PLAN.md:80`）。要件もサンプルの一致と同手順の再実行です（`.planning/REQUIREMENTS.md:52-54,81-86`）。
- `build成功` と `uat_status=not-run` / `release_allowed=false` を分けています（`06-04-PLAN.md:80`）。
- 保護停止は subprocess 開始前、起動比較は終了時の正当な window 保存より前です（`06-04-PLAN.md:96`）。保存経路は `pagefolio/app.py:766-778` と一致します。
- X01〜X05 の障害が実 EXE で分類できない場合、06-05 へ進みません（`06-04-PLAN.md:96`）。

### 懸念

- **MEDIUM** — 操作本文は初回と再ビルドの2回です（`06-04-PLAN.md:80`）。検証ブロックに書かれた CLI は1回です（`06-04-PLAN.md:85-86`）。`fails_when` の「片方欠ける」が pytest 行にも付いており、単体試験の成功を2回の実ビルドと読める余地があります。
- **MEDIUM** — 人手の OCR 接続実証が 06-04-02 にあります（`06-04-PLAN.md:96-102`）。Phase 4 の再検証は 06-05-02 の前提です（`06-05-PLAN.md:91`、`.planning/STATE.md:56`）。ROADMAP は stale 再検証を実機受入の開始条件にしています（`.planning/ROADMAP.md:227`）。現行 `04-VERIFICATION.md:1-7` は `status: passed` のままなので、この接続実証は stale な検証世代のバイナリで「成立」と記録されます。コードが再検証で変わったあと、hash だけ更新して接続実証を流用する手順がありません。
- **LOW** — 導入済み PyInstaller の版は、このセッションでは再確認していません。ピンは `pyinstaller==6.22.3` です（`requirements.txt:5`）。計画の事前条件が読取確認を要求しているので、実行時の確認で足ります。

### 具体的提案

1. 検証コマンドを2行にし、1回目は空の最終先、2回目は同じ引数の管理済み再ビルドとする。pytest の `fails_when` から実ビルド欠落を外す。
2. 06-04-02 の人手接続は、Phase 4 再検証後の hash が 06-04 の証拠と一致するときだけ有効とする。製品バイトが変わったら 06-04 の実ビルドと接続実証をやり直す。

### 総合リスク

**MEDIUM**。実ビルドと原本保護の手順は実装可能です。検証回数と、stale より前の人手成立の記録が弱いです。

## 06-05

### 要約

W01〜W12 の24枝番、WR-01、EXE 固有の X01〜X06 を not-run のカードと台帳に展開し、G1〜G6 を Python のあと EXE の順で人手確認します。Phase 5 の H01〜H14 と意味評価2件は、対象が同じとき再実施しません。

### 強み

- 枝番の集合は移管正本と Windows 受入表に一致します（`06-UAT-CARRYOVER.md:16-28`、`04-WINDOWS-UAT.md:51-75`）。W12a の3×3、W12c の Explorer と端末、API 戻りと実 foreground の分離も元手順と同じです（`04-WINDOWS-UAT.md:74-75,120-122`、`06-05-PLAN.md:80,95`）。
- 初期状態は全 not-run です（`06-05-PLAN.md:80`）。`--allow-pending` の成功は実機合格ではない、と検証に書いてあります（`06-05-PLAN.md:98-100`）。
- 06-05-02 は、Phase 4 の現行入力に対する再検証と、通常 production owner がいないことを開始条件にしています（`06-05-PLAN.md:91`）。mutex がセッション内で一つなので（`pagefolio/startup_win32.py:442-444`）、この事前条件は必要です。
- X05 の「終了 No、初回保存失敗で残り、次回終了は保存を省略」は D-19 と `_quit` の構造に対応します（`.planning/phases/05-config-notification/05-CONTEXT.md:51`、`pagefolio/app.py:669-681,766-778`）。

### 懸念

- **MEDIUM** — X01〜X05 の観察点として「非モーダル文言」がまとめて書かれています（`06-05-PLAN.md:95`）。不存在は警告せず既定値で起動する契約です（`05-CONTEXT.md:21-22`、`.planning/REQUIREMENTS.md:45`）。X01 に通知表示を必須にすると、正しい製品が不合格になります。
- **MEDIUM** — X06 は About とタイトルの版一致を見ます（`06-05-PLAN.md:95`）。About は `APP_VERSION` を表示します（`pagefolio/dialogs/about.py:47-52`）。メインウィンドウのタイトルは `PageFolio` 固定です（`pagefolio/app.py:146`）。タイトルバーへ版を出す変更は、どの計画の `files_modified` にもありません。
- **MEDIUM** — W12b の「対応別版」の第2バイナリの出所がありません（`06-05-PLAN.md:80,95`）。mutex 名は版を含まないため、同じ v1.10.0 のコピーだけでは別版の軸を実測できません。06-01 の v1.9.1 tracer 成果物を残す方針はありますが、06-05 の手順はそれを指定していません。
- **LOW** — 06-04 の接続実証を W04 の目視 pass へ流用できる余地が残ります。計画は別物と書いています（`06-04-PLAN.md:96`、`06-05-PLAN.md:95`）。台帳の `evidence_kind` が分かれていれば防げます。

### 具体的提案

1. X01 は「通知なし・既定起動・ファイル不存在の維持」。X02 以降だけ種別ごとの非モーダル文言、とする。
2. 版の表示確認は About の `APP_VERSION`、フォルダ名、release report に限定する。タイトルバーは対象外と書く。
3. 別版の相手は、版同期前に残した tracer ビルドか、同じソースで版だけ異なる保存済み onedir の hash を台帳に固定する。同一フォルダの複製は別配置の軸にだけ使う。

### 総合リスク

**MEDIUM**。カードの網羅は足りています。X01、タイトル、別版の3点が、合格条件と現行製品の意味をずらします。

## 06-06

### 要約

W06〜W11 と WR-01 を条件別に実測し、品質ゲートと Phase 4 の鮮度を揃えてから、親の4独立ゲートへ `phase_complete=false` で引き渡します。W11 が準備できない場合は not-run のままタスクを完了にしません。

### 強み

- 時間の数値は元記録と一致します。W07 は初期化 6.5 秒、点滅は 3回/250ms、並行負荷 15609ms と単独 15140ms、上限超過 109ms です（`04-WINDOWS-UAT.md:59-60,92-98,129-132`、`06-UAT-CARRYOVER.md:36`、`06-06-PLAN.md:88`）。
- 別アカウントの新設、資格情報の取得、mock による別 session 合格は禁止です（`06-06-PLAN.md:88`）。W11 の not-run は完了を止めます（`06-UAT-CARRYOVER.md:26,35`）。
- 全件 pytest の成功を、DEP-05、owner_missing、通知前景、Tcl、未分類 edge の原因解決へ転用しない、とあります（`06-06-PLAN.md:104`、`.planning/STATE.md:56-60`）。
- 引渡し監査は親4ゲートの pending を許容し、flag なしの最終監査だけが完了判断の入力です（`06-06-PLAN.md:104-112,136-143`）。完了フラグを監査の前提にしていません。
- DoD 試験は完了フェーズだけを `validated` に要求します（`tests/test_gsd_dod.py:243-249`）。ROADMAP の Phase 6 は `0/6 | Planned` です（`.planning/ROADMAP.md:251`）。実行中に VALIDATION を先に `validated` へする必要はありません。

### 懸念

- **MEDIUM** — WR-01 は「条件と契約の適合を判断」と「契約不適合なら失敗」の両方です（`06-06-PLAN.md:88,92`）。元記録は、任意負荷の上限保証は未実証で、15609ms を消さない、としています（`06-UAT-CARRYOVER.md:36`）。保証範囲は変更しない承認です（`.planning/phases/06-release-validation/06-CONTEXT.md:52-59` の引継ぎ、ユーザー承認の再計画）。「単独条件だけを保証対象に読み替える」判断が、利用者承認なしの適合記録になり得ます。
- **LOW** — 再検証で Phase 4 の製品バイトが変わったときの戻り先は、06-05 の hash 不一致で停止するだけです。再ビルドと、影響する人手行のやり直し順は 06-06 にはありません。停止としては安全です。
- **LOW** — 親4ゲートの実走手順は具体的です（`06-06-PLAN.md:136-139`）。実行主体が親 orchestrator であり、Phase 6 のタスク完了だけではフェーズは終わりません。この分離は意図どおりです。

### 具体的提案

WR-01 の合格を次の3条件同時に限定する。元の 15609ms と 15140ms を台帳に残す。同じ cross_entry 負荷を再計測する。15.5秒を超えた再計測は不適合として出荷を止め、保証範囲を狭める変更は利用者の明示承認がある記録だけを根拠にする。

### 総合リスク

**MEDIUM**。出荷停止のゲートは計画として閉じられます。WR-01 の判断文だけが、未解決の時間超過を狭い合格へ変える穴です。現行環境では W11 が not-run のため、計画を正しく実行しても Phase 6 完了と v1.10.0 リリースは停止します。これは欠陥ではありません。

## 横断評価

依存順 `06-01 → 02 → 03 → 04 → 05 → 06` は、版を上げてから最終ビルドし、その hash の EXE で人手受入する順として成立します。共有する配布ツリーと foreground を直列にする判断も、mutex が `Local\PageFolio.Startup` の一つであることに合っています。

停止条件は計画群として維持されています。not-run の補完禁止、W11 の準備不能、Phase 4 stale、DEP-05 / owner_missing / 通知前景 / Tcl / 未分類 edge、親ゲート前の `release_allowed=false` は、06-03 の audit と 06-06 の done 条件に残っています。Phase 5 の完了済み人手受入を、配布 EXE の新規受入へ流用する書き方にもなっていません。

安全性は、事前停止、私有作業領域、設定本文をレポートへ出さないこと、loopback 以外へ転送しないこと、所有 PID 以外を止めないこと、新規 install をしないこと、まで一貫しています。過剰なのは audit の状態数ではなく、06-01 が同じ失敗条件を単体試験と実ビルドの両方へ貼っている点です。

性能上の全件 pytest 反復は、入力 hash が一致するとき再利用できます（`06-VALIDATION.md:27,124`）。実 PyInstaller を `tests/test_release_build.py` に入れると、この再利用が効かず、全件のたびに配布物へ触れます。

フェーズ目標のうち、再現可能な同梱、非破壊、版の同期、自動試験は、上記の修正後に到達できます。実機を含む Phase 6 完了と出荷は、全必須人手の pass、Phase 4 の再検証、未解除回帰の保持、親の独立監査が揃うまで止まる計画です。W11 が準備不能のままなので、その停止は現時点の正しい終状態です。

実行前の修正順は次のとおりです。

1. 06-01 の pytest と実 CLI の失敗条件を分離し、実ビルドを境界試験の後、私有 `--distpath` 付きに移す。
2. 06-04 の検証を初回と再ビルドの2コマンドにし、人手接続の有効期限を Phase 4 再検証後の hash に結ぶ。
3. 06-05 で X01、ウィンドウタイトル、別版バイナリの意味を現行コードに合わせて狭める。
4. 06-06 で WR-01 の不適合を、保証範囲の読み替えでは合格にできないようにする。

### 変更内容サマリー

**修正対象**: Phase 06 計画の読み取り専用レビュー（実装変更なし）

| ファイル | 変更内容 |
|----------|----------|
| なし | 計画・ソースの参照のみ。編集、テスト実行、commit はしていない |

### 修正内容の詳細

6計画を現行の定数、設定の読込・原子的保存、Ollama の HTTP 形、起動 mutex、Phase 4 受入数値、DoD 試験の完了判定に突き合わせた。未作成のビルド成果物は欠陥にしていない。not-run、Phase 4 stale、未解除回帰は合格へ読み替えていない。

### 次セッションへの申し送り

#### 未実施（動作確認・テスト）

- pytest、Ruff、実 PyInstaller、実 EXE 起動は未実施。
- 導入済み PyInstaller の版と、現行ワークツリーの dirty diff の中身は再確認していない。ピンは `requirements.txt:5` の `pyinstaller==6.22.3`。
- 計画修正後に、06-01 の argv が `dist/PageFolio` を出力先にしないことを試験で固定する。

#### 注意点・潜在リスク

- 06-01 を直さずに実行すると、検証コマンドが追跡済みサンプルの再作成と衝突し得る。
- W11 が準備不能の間は、Phase 6 完了とリリースを止める。アカウント新設や mock 合格は使わない。
- WR-01 の 15609ms / 15140ms は残す。15.5秒超過の再現を、保証範囲の縮小で pass にしない。
- Phase 4 の `04-VERIFICATION.md` は歴史上 `passed` のままで、現行 STATE は stale。再検証前の EXE 観測を最終受入にしない。

#### 実行推奨コマンド（必要な場合）

```
なし（このセッションはレビューのみ）
```
