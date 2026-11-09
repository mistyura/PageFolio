照合が終わったので、レビュー本文をまとめます。

# Phase 06 計画 クロスAIレビュー

**前提:** 読み取り専用で実施しました。ファイル編集・テスト・commit はしていません。開いて確認したのは、6つのPLAN、06-CONTEXT/RESEARCH/PATTERNS/VALIDATION/PLANNING-CHECKS/UAT-CARRYOVER、04-WINDOWS-UAT、04-VERIFICATION の frontmatter、STATE、ROADMAP、config.json、AGENTS.md、`pagefolio/constants.py`、`pagefolio/settings.py`、`pagefolio/ocr_providers/ollama.py`、`docs/DEVELOPMENT.md`、`docs/CONFIGURATION.md`、`.gitignore`、`tests/test_startup_windows.py`（該当範囲）、`tests/test_gsd_dod.py`、`.venv` 内の PyInstaller `makespec.py`、および git の状態（diff、eol、remote）です。

**ゲートの扱い:** 人手UATの not-run を合格扱いしない、Phase4 stale と未解決回帰のゲートを外さない、という前提を変えずに評価しています。

---

## 06-01

**要約:** 2サンプルを出力外の正本へバイト単位でコピーし、日本語ガイドと単一CLI `tools/build_release.py` を作ります。CLI は preflight → 私有 run → PyInstaller → 同梱と SHA 照合 → 公開前の再検査 → 昇格 → 公開後照合を行います。tracer（06-01-01）で一経路を通し、06-01-02 で保護・競合・各故障境界を固めます。

**強み**
- 現行のビルド手順は「退避 → `--noconfirm` で再生成 → 復元」です（`docs/DEVELOPMENT.md:85-100`）。この構造的な欠陥を、出力外の正本と事前停止で根本的に置き換える方針は妥当です（`.planning/phases/06-release-validation/06-01-PLAN.md:94`）。
- 保護対象の名前を `pagefolio/constants.py:15,21-22` から AST で読み、二重定義を避けています。frozen 時の基準ディレクトリ `os.path.dirname(sys.executable)`（`pagefolio/settings.py:41-43`）と「EXE と同じ階層」という配置が一致しています。
- 新しい版付き出力は `.gitignore:74` の `dist/` で無視され、既に追跡されている `dist/PageFolio` は残ります。巨大バイナリを stage しない方針と矛盾しません（`.gitignore:10-12,74`）。
- テストは fake builder の呼出回数と、実ディスク上ファイルの前後の bytes/hash で判定します。文字列一致だけの試験を避けています（`06-01-PLAN.md:92`、`tests/conftest.py` を analog に指定）。
- 失敗物は INCOMPLETE として残し、検証前のものを成功扱いしません（D-11）。同梱レポートの自己参照 hash を、外部 run レポートとの組で回避する設計も具体的です（`06-01-PLAN.md:94`）。

**懸念**
- **MEDIUM — preflight の重複判定が既定コマンド自身を拒否しうる。** 規則は「ソース/正本/旧dist/PageFolioやrootと重なる指定は拒否」（`06-01-PLAN.md:94`）、研究側は「ソース…親子重複」（`06-RESEARCH.md:224`）です。一方、既定の出力先 `--output-root dist` はリポジトリ（ソース）の子で、`dist/PageFolio` の親でもあります。「ソース」がリポジトリルートを指すのか、判定対象が output-root なのか最終出力先なのかが曖昧です。解釈次第では tracer の verify（`06-01-PLAN.md:99`）が自己拒否で失敗します。
- **MEDIUM — 改行コード変換で SHA 契約が環境依存になる。** 2つの原本は改行が異なります（OCR 用 `i/crlf w/crlf`、サマリ用 `i/lf w/lf`。`git ls-files --eol` の実測）。今の環境は `.gitattributes` がなく `core.autocrlf=false` です。`autocrlf=true`（Git for Windows の既定になりうる）のクローンでは、コミット時やチェックアウト時に正本の bytes が変わります。調査時の固定 hash（`06-RESEARCH.md:205-206`）を試験に埋め込むと、別環境で必ず失敗します。
- **MEDIUM（一部未確認）— icon の相対パスと私有 specpath の組合せ。** 計画は `--icon pagefolio.ico` を相対のまま私有の spec/work/dist と併用します（`06-01-PLAN.md:94`）。PyInstaller は script を spec 相対へ変換しますが（`makespec.py:754`、`make_path_spec_relative` は `:38-52`）、icon は値をそのまま spec に書き込みます（`makespec.py:713`）。spec の実行時に spec ディレクトリ基準で解決されると icon が見つからない可能性があります。この解決規則自体は今回未検証です。
- **LOW-MEDIUM — tracer の成果物が誤認されやすい。** tracer は当時の版で `dist/PageFolio-v1.9.1` を「成功先」として公開します（`06-01-PLAN.md:94`）。実際には Phase4/5 のコードを含む非正式版です。旧 v1.9.1 リリースと取り違えたり、後で W12b の別版として根拠なく流用したりする余地があります。
- **LOW — PyInstaller 子プロセスの暴走対策がない。** 上限時間・stdin 遮断・interrupt 時の扱いが未定義です。確認プロンプトなどで停止したまま固まる余地があります。
- **LOW — 古い lock の回復手順がない。** 「古lockを生存未確認で奪わない」（`06-01-PLAN.md:111`）は安全側ですが、クラッシュ後の運用回復手順がありません。
- **LOW — 公開 rename の一時失敗。** 新しく書いた EXE を AV がスキャン中だと、directory rename が一時的に失敗しえます。現状は即 nonzero なので、成功しにくい状態が繰り返される可能性があります。
- **LOW（性能・ディスク）— 保持物が増え続ける。** `.release-history/<run-id>` は完全な旧 tree を、`.release-work` は work/spec ごと保持します。保持方針がなく、再ビルドのたびに数百MB単位で増えます。
- **LOW（過剰設計）— 1タスクに機能を詰め込みすぎ。** tracer 1タスクに正本・ガイド・lock 以外の全パイプラインと report の組管理が入っています（estimate 34000、confidence low）。個人開発の規模に対して重めですが、D-06/D-11 の要求からはおおむね正当化できます。

**提案**
- preflight の対象を明文化します。output-root そのものではなく、最終出力先・work・history が「`pagefolio/`、`distribution/`、`tools/`、`dist/PageFolio`、ドライブルート」と親子重複しないことを判定する、と書きます。既定の `--output-root dist` が通る正例試験も加えます。
- `distribution/samples/* -text`（または `binary`）を `.gitattributes` に追加し、bytes を固定します。試験は「元ファイルと正本の相互一致」を主にし、固定 hash は補助にとどめます。
- argv の icon・entry は絶対パスにします。`stdin=DEVNULL`、ビルド上限時間、上限超過時は INCOMPLETE で終える規則を明記します。
- tracer は `--output-root` に repo 外の一時ディレクトリなどを指定し、`dist/` に v1.9.1 名の公開物を残さないようにします。
- lock の回復手順（所有 PID と作成時刻が消えたことを確認してから人が解除する）と、history/work の保持上限・手動削除手順を文書化します。

**総合リスク:** MEDIUM

---

## 06-02

**要約:** `APP_VERSION` を v1.10.0 にし、README バッジと開発履歴を同期します。保証範囲（旧版・OS前面化）、利用者向けの更新・衝突時の手順、保守向けの単一CLI手順を文書化し、read-only の契約試験を追加します。

**強み**
- 真の情報源が `pagefolio/constants.py:12` だけで、CLI に別の版定数を持たせない方針です（`06-02-PLAN.md:89`）。アプリ内の版表示は `pagefolio/dialogs/about.py:49` が `APP_VERSION` を参照しており、整合が取れます。
- `constants.py` は 04-VERIFICATION の `covered_files` に含まれていません（`.planning/phases/04-startup-control/04-VERIFICATION.md:6`）。版の更新で Phase4 の鮮度がさらに悪化することはありません。
- 外部 md 連動の既存契約（存在する場合だけ Apply で書き戻す。`docs/CONFIGURATION.md:120`、`pagefolio/settings.py:85-105`）を維持する方針が明示されています。
- 契約試験に、未完了を validated/pass に書き換えない制約が入っています（`06-02-PLAN.md:85`）。

**懸念**
- **MEDIUM — 既存の未コミット差分が混入する。** `開発履歴.md` には既に 20 行の未コミット差分（2026-10-23 の診断節など）があります（`git diff --stat`）。06-02-01 がこのファイルを編集してタスク commit すると、無関係な既存差分が同じ commit に入ります。execution_rules の「dirty変更…を戻さず」（`06-02-PLAN.md` の execution_rules）は戻さないことしか定めておらず、commit の分離までは扱っていません。
- **MEDIUM — 配布ガイドの詳細リンクが main ブランチ固定。** リンク先は `https://github.com/mistyura/PageFolio/blob/main/docs/CONFIGURATION.md` です（`06-02-PLAN.md:104`）。現在の作業ブランチは `feature/v1.10.0` で、main への merge は本 Phase の範囲外です。出荷時点で main の文書が v1.10.0 の内容になっている保証がありません。試験は「リンク先がローカルで追跡されているか」しか確認しません。リポジトリが公開かどうかは、remote が SSH のため未確認です。
- **LOW — 履歴節の扱いがあいまい。** 「Phase5履歴の古い受入状況を…追記で補い」（`06-02-PLAN.md:89`）の範囲が広く、開発履歴の書式（最新節・最終更新ブロック）のどこに置くかが未定義です。
- **LOW — plugins の扱いが未記載。** 利用者データとして `plugins/`（`pagefolio/constants.py:16`）も EXE と同じ階層に置かれえますが、D-05 の更新手順で触れていません。範囲外の判断なら、その旨を一文書くとよいです。

**提案**
- Phase 6 の開始前に、既存の未コミット差分（`開発履歴.md`、`requirements.txt`、`tests/test_startup_windows.py`）を別 commit で確定するか、明示的に保留にする前提ゲートを置きます。少なくとも hunk 単位で stage することを execution_rules に書きます。
- ガイドのリンクは tag 固定（例 `/blob/v1.10.0/...`）にするか、必要な抜粋を同梱 md にします。tag 作成（`config.json` の `create_tag: true`）との順序も定義します。

**総合リスク:** LOW-MEDIUM

---

## 06-03

**要約:** 未改変の配布EXEを完全コピーして隔離実行し、所有PID・foreground・原本 snapshot を外部から観測する検証CLIを作ります。auditの3モード（allow-pending / for-handoff / 最終）を実装します。既存の Ollama 設定経由で接続する loopback fake OCR と、EXE 用の設定障害（破損 JSON、share 制限による lock、tmp 衝突）を準備します。

**強み**
- 既存 harness の入口は `script/module/relocated` だけで（`tests/test_startup_windows.py:2778-2780`）、`--entry exe` がないことを前提に、frozen 製品を patch しない外部観測型を選んでいます。
- 本番名前空間の扱いは既存 harness の `--production` → `Win32Backend(None)` と、既存 owner 検出時の中断（`tests/test_startup_windows.py:2806-2814`）に合わせています。他の production owner がいれば停止します。
- fake OCR の HTTP 形状は実コードと一致します（`/v1/chat/completions` は `pagefolio/ocr_providers/ollama.py:94`、`/v1/models` は `:170`、応答の `choices[0].message.content` / `finish_reason` は `:135,152-155`）。
- 設定障害の作り方は実装と対応しています。tmp 衝突は `_save_settings` の `open(tmp,"x")`（`pagefolio/settings.py:377-381`）を突きます。読込不能は `except Exception → "unreadable"`（`settings.py:316-320`）を突きます。
- audit の for-handoff と最終監査を分け、正負の fixture で循環依存を避けています（`06-03-PLAN.md:76-84`）。

**懸念**
- **MEDIUM — fake OCR の「1件・一度だけ」が既定設定と合わない。** 計画は「合成3ページPDF」（`06-03-PLAN.md:115`）、「同一requestを一度だけ完了」（`:114`）、「一件を受信」（`06-04-PLAN.md:96`）を前提にしています。しかし OCR は `ocr_concurrency`（既定 2。`pagefolio/settings.py:279`、`pagefolio/ocr.py:657`）で並列に送り、ページごとに request が出ます。さらに 429/5xx は最大 `MAX_RETRIES=3` で再送します（`pagefolio/ocr.py:185,352`）。3ページで 1 request にはならず、「request重複」の fails_when に正常動作で引っかかります。
- **LOW（未確認の質問）— W05b を起こすエラー種別が未特定。** `ocr_dialog.py` に showerror/askyesno の経路は複数あります（例 `pagefolio/ocr_dialog.py:1395,2152,2645`）。どの HTTP 応答がリトライなしで OCRDialog 所有の messagebox に至るかは今回追跡していません。
- **LOW — 出荷判定の監査を同じ実行者が持つ。** 出荷判定を担う audit が `tests/` 配下にあり、証拠を記録する同じ実行担当が作ります。親の独立ゲートで緩和されていますが、監査ロジック自体のレビュー観点を親ゲートに明記しておくとよいです。
- **LOW（性能）— ケースごとの完全コピー。** `prepare` はケースごとに配布 tree 全体を `.planning/tmp` へ複製します。25 ID と多数の subrow ではディスクと時間を圧迫します（`.planning/tmp` は `.gitignore:51` の `tmp/` で無視されますが、容量は消費します）。

**提案**
- fake OCR カードで、EXE の作業コピーに `ocr_concurrency=1` と 1ページPDFを指定するか、「ページごとの request 集合が同じで、各 request が一度だけ完了する」に判定を改めます。待機はサーバ側でリトライ不要な時間内に収めます。
- W05b 用のエラー応答（例: リトライ対象外の 4xx）を、06-03-02 の時点で Python 経路により特定・記録します。
- `prepare` は組（G）単位で 1 コピーにし、ケース開始ごとに tree hash を再照合する形にします。

**総合リスク:** MEDIUM

---

## 06-04

**要約:** v1.10.0 で同じCLIを初回と再ビルドの2回実行して証拠化します。保護3名ごとのビルド前停止、起動時の非破壊性、更新・衝突時のコピー手順を実ファイルで確かめ、未改変EXEから loopback fake OCR への接続を実証します。

**強み**
- tracer 時点の版の成果物と最終版を分け、「版だけ後付け」を禁止しています（`06-04-PLAN.md:78`、`06-01-PLAN.md:94`）。
- 起動の非破壊性と、終了時の正当な window 保存を時点で分けています（「起動安定後（終了時の正当なwindow保存より前）」`06-04-PLAN.md:96`）。終了時の自動保存（`docs/CONFIGURATION.md:55`）と矛盾しない、正しい判定設計です。
- bit 再現性を要求せず、各成果物の hash を個別に記録する（`06-04-PLAN.md:78`）のは要件（`.planning/REQUIREMENTS.md` の DIST-02）の範囲に合っています。
- 接続実証が成り立たなければ 06-05 へ進まない、という停止条件があります。

**懸念**
- **MEDIUM — 未コミットの作業ツリーから最終ビルドする余地がある。** 現在 `requirements.txt`（pyinstaller 6.21.0→6.22.3 など）と `tests/test_startup_windows.py` に未コミット差分があります（`git diff requirements.txt`）。研究が VERIFIED とする `pyinstaller==6.22.3`（`06-RESEARCH.md:126`）も未コミットの値です。06-04-01 の precondition は品質ゲートの成功だけを求め（`06-04-PLAN.md:76`）、製品・ビルド入力の clean は要求していません。dirty hash を記録するだけでは、出荷EXEがどの commit とも一致しない状態を許します。
- **MEDIUM — 人手確認が type="auto" に埋め込まれている。** 06-04-02 は type="auto" の中に `<human-check>` を入れています（`06-04-PLAN.md:91,101`）。自動の verify は pytest だけ（`:99`）で、接続実証の回答がなくても通ります。config は `mode: yolo`、`human_verify_mode: end-of-phase`（`.planning/config.json:28,96`）で、execute-plan の checkpoint は `checkpoint:*` か tracer の blocking-human でしか止まりません（`C:/Users/shdwf/.codex/gsd-core/workflows/execute-plan.md:233-234`）。人手待ちを担保しているのは本文の記述だけです。
- **LOW-MEDIUM — 公開先での直接起動が禁止されていない。** 公開先 `dist/PageFolio-v1.10.0` で EXE を直接起動すると、終了時の自動保存でそこに `pagefolio_settings.json` が作られます（`docs/CONFIGURATION.md:17,55`）。その結果、次の再ビルドが D-06 で停止し、配布物に設定ファイルが混入する危険があります。D-12 の「次の実機確認手順」で、必ずコピーして起動するよう明記する指示がありません。
- **LOW — 「クリーン」の定義があいまい。** PyInstaller の全体キャッシュの扱い（`--clean` を付けるか）が未定義です。また 2回の実行に対して verify のコマンドは1行だけです（`06-04-PLAN.md:85`）。

**提案**
- 06-04-01 の precondition に「`pagefolio/`、`pagefolio.py`、`distribution/`、`tools/`、`requirements.txt` などビルド入力が HEAD と一致（未コミット差分なし）」を加え、違反時は停止します。
- 接続実証は `checkpoint:human-verify`（gate="blocking-human"）に分けるか、audit に「指定ケース行が pass でなければ nonzero」になるモードを足して自動 verify にします。
- CLI 成功時の案内文と guide に「公開先では起動せず、別フォルダーへコピーしてから起動する」を入れ、06-01 の試験でその文言を確認します。

**総合リスク:** MEDIUM

---

## 06-05

**要約:** 全24枝番＋WR-01 と X01〜X06 を、入口・条件単位の not-run 行とカードに展開します。G1〜G6（W01〜W05c、W12a/b/c、X01〜X06）を Python → EXE の順で少数ずつ人手受入します。

**強み**
- 移管元（`.planning/phases/06-release-validation/06-UAT-CARRYOVER.md:14-28`）と 04-WINDOWS-UAT（`.planning/phases/04-startup-control/04-WINDOWS-UAT.md:52-75`）の全IDを明示列挙しています（`06-05-PLAN.md:80`）。24＋1 の件数も一致します。
- Phase5 の H01〜H14 と意味評価2件を再実施せず、EXE 固有の新しいID（X系）で記録する方針は、CONTEXT の引継ぎ条件に合っています。
- 06-05-02 の precondition に Phase4 の鮮度（対象 hash の一致）を置いています（`06-05-PLAN.md:91`）。04-VERIFICATION には `covered_files` と `covered_digest` があり（`04-VERIFICATION.md:6-7`）、機械的に照合できます。

**懸念**
- **HIGH — 人手受入タスクの自動 verify が「何もしていなくても」成功する。** 06-05-02 の自動 verify は `audit --allow-pending` だけです（`06-05-PLAN.md:98`）。これは設計上、未実施の行があっても exit 0 を返します（`06-03-PLAN.md:78`）。「担当行がnot-runならtask未完了」という条件は本文の fails_when にしかありません。type="auto" で、`yolo` と `end-of-phase` の設定では checkpoint も発火しません（`execute-plan.md:232-234`、`config.json:28,96`）。実行担当が自動判定だけを見ると、G1〜G6 が not-run のまま SUMMARY が complete になり、進捗も進む経路が残ります（最終的には 06-06-02 の for-handoff が止めますが、それまで台帳と STATE が実態とずれます）。
- **MEDIUM — W12b の「対応版の別版」EXE の入手元が未定義。** 要件は「別版・別配置・Python/EXE 混在」（`.planning/REQUIREMENTS.md` の START-01）、計画は「別配置/対応版の両方向」（`06-05-PLAN.md:80`）です。追跡済みの `dist/PageFolio/PageFolio.exe` は 2026-08-11 の commit（`git log`、v1.9.0 期）で、Phase4 より前の排他未対応旧版なので使えません。もう1つの対応版EXEを、どの版・どのビルドで作るかが計画にありません。
- **MEDIUM — EXE 側の状態準備と観測の限界が入口ごとに明示されていない。** Python 側の W01〜W05c は、harness が状態を自動で準備します（例: 最小化済み、未保存入力・カーソル5・選択1〜7、3ページPDFの回転・複製・削除。`04-WINDOWS-UAT.md:92-96`）。未改変EXEにはこの hook がありません。人が同じ状態を作る必要があり、Undo 履歴や選択などの内部状態は外部から観測できず、目視に頼ります。カードにその区別を入れる指示が弱いです。
- **MEDIUM — タスクが大きく、中断からの再開手順がない。** 06-05-02 は G1〜G6、W12a（3×3）、W12b（双方向・複数組合せ）、X04（7つの保存元 subrow）などで数十回の人手操作になり、1タスクで複数日にまたがる可能性が高いです。途中で中断・再開するときの台帳・run・バイナリの同一性の確認手順が定義されていません。
- **MEDIUM — UAT 中に製品欠陥が見つかった場合の戻り経路がない。** 計画は「異常は直ちに停止」（`06-05-PLAN.md:95`）までです。修正後は EXE の hash が必ず変わり、06-04 の証拠も、それまでの EXE 人手 pass も無効になります。どの証拠が残りどれを取り直すかの規則がありません（再利用規則は「製品・入力・環境の変更後は必要な検証」という一般論だけです。`06-VALIDATION.md:27`）。

**提案**
- audit に `--require-pass <ID,...>`（担当行の全 subrow が実測根拠付き pass でなければ nonzero）を追加し、06-05-02 の自動 verify にします。あわせて G ごとに `checkpoint:human-verify gate="blocking-human"` を置き、構造監査と完了判定を分けます。
- W12b 用の対応別版を定義します。例: 同じ commit で `APP_VERSION` だけ変えた試験用EXEを別 hash で作り、「対応版の別版」の証拠として扱います。ただし production のケースへは流用しない、と書きます。
- 06-05-02 を G1〜G3 / G4 / G5〜G6 程度に分けるか、再開時に「run・台帳・EXE hash・Phase4 digest を再照合してから続ける」手順を明記します。
- 欠陥発見時の無効化マトリクスを VALIDATION に追加します。製品コードを変えた場合は build/protection と全EXE行を取り直し、Python 行は covered digest で判断する、などです。

**総合リスク:** HIGH（主因は人手受入の完了判定が機械的に担保されていないこと）

---

## 06-06

**要約:** G7〜G14（W06〜W11、WR-01）の残りの OS 条件を受け入れます。そのうえで、品質ゲート、Phase4 鮮度、全受入と未解除事項を照合し、`--for-handoff` で親の独立4ゲートへ引き渡します。Phase 完了と出荷は、親の最終監査が成功するまで止めたままです。

**強み**
- W11 は準備できなければ not-run のままにし、アカウント新設・資格情報取得・mock での代替を禁止して出荷を止めます（`06-06-PLAN.md:88`、`06-UAT-CARRYOVER.md:26,35`）。
- WR-01 は 15609ms と 15140ms の両方を残し、期限延長や無負荷 pass で置き換えません（`06-06-PLAN.md:88`、`04-WINDOWS-UAT.md:130-131`）。
- Phase4 の禁止3件とedge5件（`04-VERIFICATION.md:18-19`）、Phase5 の edge4件、Phase6 の edge6/禁止6件を別集合で追跡し、根拠なく resolved にしません。
- 引渡し準備（`phase_complete=false`、`release_allowed=false`）、親の4ゲート、最終監査の順序と担当がはっきり分かれています（`06-06-PLAN.md:141`、`06-VALIDATION.md:55-62`）。

**懸念**
- **HIGH — 06-06-01 の自動 verify も `--allow-pending` だけ。** 06-05 と同じ構造です（`06-06-PLAN.md:91,93`）。UAC や別 session のように最も重い人手条件が、機械的な完了判定で担保されていません。
- **MEDIUM — WR-01 が契約不適合だった場合の決定者が未定義。** 計画は「契約不適合ならtask未完了」で止まります。製品を修正するのか、ユーザー承認のうえで契約を見直すのかの分岐と承認者がありません。06-UAT-CARRYOVER の「再計画にはユーザーの明示承認」（`:35`）への接続も明記されていません。
- **MEDIUM（達成可能性）— W11 の準備不能で Phase 6 は完了できない構造。** 現状 W11 は準備不能と記録されています（`06-UAT-CARRYOVER.md:26`）。これは計画の欠陥ではありませんが、Phase 6 の完了は外部資源（既存の別アカウント）に依存し、今のままでは原理的に完了しません。準備できない場合にユーザーへ判断を求めるエスカレーションの経路を計画に置くべきです。
- **LOW — W06 の実 OS 拒否は自然には再現しにくい。** 再試行の上限と、試行ごとの記録方式（成功した前面化試行を拒否として数えない）は既存資料にありますが（`04-WINDOWS-UAT.md:97`）、試行回数の上限がありません。
- **LOW — 品質ゲートと証拠ファイルの関係。** 06-06-02 の全件 pytest（`06-06-PLAN.md:107`）は妥当です。ただし 06-05/06-06 で台帳ファイル（`06-UAT.md`/JSON）を更新すると、TestCaseCoverage などの入力が変わります。「全入力 hash が一致する成功の再利用」は、台帳を確定した後でしか成り立たない点を明記するとよいです。

**提案**
- 06-06-01 にも `--require-pass`（担当ID）と G ごとの blocking-human checkpoint を適用します。
- WR-01 不適合時と W11 準備不能時の分岐を明記します。どちらも「停止 → ユーザーへ選択肢（製品修正・契約再承認・準備継続）を提示」とし、承認がない限り not-run/fail を維持します。
- 06-06-02 の手順に「台帳の確定 → 全件 pytest → 証拠記録 → for-handoff」の順序を固定します。

**総合リスク:** HIGH（06-06-01 の判定担保。設計上の出荷停止ゲート自体は堅固です）

---

## 横断評価

**フェーズ目標と依存順序**
- 6 wave の直列順（ビルド CLI → 版と文書 → 観測準備 → 最終ビルドと実証 → 一般受入 → OS条件と最終照合）は、成果物の生成順として実装可能です。06-02 の版同期の後に 06-04 で最終ビルドする、という「版の後付け禁止」の順序も正しいです。
- **MEDIUM — Phase4 の stale 再検証にタスクの持ち主がいない。** 06-05-02 の前提として必須ですが（`06-05-PLAN.md:91`）、Phase 6 のどの計画にも実施タスクがなく、「親workflowの `$gsd-execute-phase 04`」に委ねています（`.planning/STATE.md:319`）。Phase 4 は 6/6 が完了済みです（`.planning/ROADMAP.md:249`）。execute-phase がこの状態で再検証だけを実行するかは、今回の資料では確認できませんでした（未確認の質問）。実施の時機は Wave 4 完了後〜Wave 5 開始前が最も合理的です。`tests/test_startup_windows.py`（現在未コミット差分あり）は covered_files に含まれる（`04-VERIFICATION.md:6`）ため、その確定後に行う必要があります。

**ゲートの維持（強み）**
- not-run を pass にしない、Phase4 stale、DEP-05・owner_missing・通知前景不一致・Tcl警告・未分類edgeの再発時停止、期限延長・skip・除外の禁止、全件単一プロセス pytest。これらが全6計画の execution_rules と VALIDATION に一貫して書かれており、骨抜きにする記述は見当たりません（`06-VALIDATION.md:26-30,124-128`）。

**主な横断リスク（重要度順）**
1. **HIGH:** 人手受入（06-04-02、06-05-02、06-06-01）が type="auto" と `--allow-pending` で書かれています。`yolo` と `end-of-phase` の設定では、機械的な停止点がありません。最終の for-handoff で出荷は止まりますが、途中のタスク完了と STATE が実態から外れます。
2. **MEDIUM:** 製品修正や再ビルド後の証拠無効化規則がありません。バイナリ hash に縛られた全EXE人手 pass が一度に無効になるため、修正の可能性が高い本 Phase（WR-01、未解決回帰）では計画に組み込むべきです。
3. **MEDIUM:** 未コミットの作業ツリー（`requirements.txt`、`開発履歴.md`、`tests/test_startup_windows.py`）が、commit の分離、Phase4 鮮度、ビルド入力の同一性の3点に影響します。Phase 6 開始前に処置を決めるゲートが必要です。
4. **MEDIUM:** 改行コード（混在 eol × autocrlf）、preflight の判定のあいまいさ、icon の相対パスなど、ビルド CLI の実装細部に別環境や自己拒否で失敗する要因があります。
5. **MEDIUM:** W12b の対応別版と fake OCR の並列・リトライの扱いが、受入定義と製品の既定動作とずれています。

**過剰設計・性能・安全性**
- 安全側の設計（reparse 拒否、lock、公開前の再検査、history、rollback）は D-06/D-11 と ASVS L1 の範囲内でおおむね妥当ですが、作業量は大きめです。性能面は、history・work・UAT コピーの無期限保持によるディスク増加だけが目立ちます。
- 秘密情報の扱い（設定本文やAPIキーを収集しない、hash だけを記録）は `pagefolio/settings.py:352-365` の既存ガードと整合しています。

**未確認の質問（推測で断定しない項目）**
- GitHub リポジトリは公開か。main 固定リンクは配布利用者に届くか。
- PyInstaller 6.22.3 は、spec 実行時に相対 icon を spec ディレクトリ基準で解決するか（`makespec.py:713` の書込みまでは確認済み）。
- Phase 4 の再検証を実行する具体的なコマンドと、成果物（新しい `covered_digest`）の生成手順。
- fake OCR のどの応答が、リトライなしで OCRDialog 所有の messagebox（W05b）に至るか。

**総合判定:** 計画は依存順序・被覆（要件6、決定16、W24＋WR-01、X6）・停止ゲートの面で完成度が高く、実装可能です。ただし、人手受入の完了を機械的に担保する仕組み、修正時の証拠無効化規則、Phase4 再検証の持ち主、ビルド前の作業ツリーの扱い、の4点を実行前に補強することを推奨します。補強がなければフェーズ全体のリスクは **HIGH**、補強すれば **MEDIUM** です。
