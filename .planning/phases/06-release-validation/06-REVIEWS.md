---
phase: 06
reviewers: [claude, antigravity, grok]
reviewed_at: "2026-10-23T20:17:30.5819223Z"
plans_reviewed: [06-01-PLAN.md, 06-02-PLAN.md, 06-03-PLAN.md, 06-04-PLAN.md, 06-05-PLAN.md, 06-06-PLAN.md]
models:
  claude: "claude-opus-5-5 (reasoning=high)"
  antigravity: "unknown"
  grok: "grok-4.7"
model_sources:
  claude: "pinned"
  antigravity: "unknown"
  grok: "pinned"
---

# Cross-AI Plan Review — Phase 06

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts

なし（今回、計画は変更していない）。
<!-- gsd:plan-revision-conflicts:end -->

各レビューの原文を以下に保持する。引用の誤り・過大な断定は末尾のConsensus Summaryで訂正しており、原文のすべてを採用済みとは扱わない。

## Claude Review

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

---


## Antigravity Review

## 06-01

### 1. 要約
`tools/build_release.py` による PyInstaller `--onedir` 公式ビルドパイプライン（私有 `spec/work/dist` staging → 検査 → 原子的昇格 → `release-report.json` 出力）と、配布同梱物（`distribution/はじめに.md` および `distribution/samples/` 2件）の正本化、ならびに `tests/test_release_build.py` による単体契約テストを構築する計画である。

### 2. 強み
- **既存 `dist/PageFolio` を汚さない隔離ビルド設計**: `.gitignore:10-12` では `!dist/PageFolio` と `!dist/PageFolio/**` が追跡対象として除外解除されており、既存の `dist/PageFolio/ocr_custom_prompt_sample.md:1-7` および `dist/PageFolio/ocr_summary_prompt_sample.md:1-26` がリポジトリに存在する。`.planning/phases/06-release-validation/06-01-PLAN.md:94` が私有作業領域 `dist/.release-work/<run-id>/` で PyInstaller を実行し、`dist/PageFolio-<APP_VERSION>/` へ原子的に昇格する設計は、既存の追跡対象ディレクトリとの衝突を完全に回避できている。
- **アプリ本体のパス解決仕様との整合**: `pagefolio/settings.py:55-61` の `_app_dir()` は `getattr(sys, "frozen", False)` 時に `os.path.dirname(sys.executable)` を返し、サンプルプロンプトや `pagefolio_settings.json` を EXE と同一階層で解決する（`docs/CONFIGURATION.md:107-112`、`pagefolio/ocr_dialog.py:1303-1305`）。`.planning/phases/06-release-validation/06-01-PLAN.md:94` が `PageFolio.exe`、`_internal/`、`はじめに.md`、サンプル2件をルート直下に配置し `pagefolio_settings.json` や `.tmp` の不在を昇格前に検査する設計は、凍結実行時の仕様と正確に一致している。
- **DoD テスト基盤のヘルパー再利用**: `.planning/phases/06-release-validation/06-01-PLAN.md:109` が `tests/test_gsd_dod.py:37-112` の `_read_utf8` / `_git_tracked_files` 等の既存検証パターンを踏襲しており、文字化け（`U+FFFD`）や CRLF/LF 差異に強い検証構造になっている。

### 3. 懸念
- **MEDIUM**: **PyInstaller `--specpath` 指定時の相対パス解決によるビルド失敗リスク**
  - 根拠: `.planning/phases/06-release-validation/06-01-PLAN.md:94` では `Python -m PyInstaller --onedir --noconsole --icon pagefolio.ico --name PageFolio（私有spec/work/distの固定argv、shell=False）` と記載されている。しかし PyInstaller は `--specpath <private_spec_dir>` を指定すると、生成される `.spec` 内のスクリプトパスや `--icon` の相対パスを `--specpath` 基準で解決するため、`pagefolio.py` や `pagefolio.ico` を相対パスで渡すと `dist/.release-work/<run-id>/spec/pagefolio.py` を探して失敗する。
- **MEDIUM**: **`06-01` と `06-02` 間での `distribution/はじめに.md` の二重定義と `must_haves.artifacts` の記載漏れ**
  - 根拠: `.planning/phases/06-release-validation/06-01-PLAN.md:10,91,94` では `06-01-01` で `distribution/はじめに.md` を作成・同梱対象としている一方、`06-01-PLAN.md:25-33` の `must_haves.artifacts` および `06-01-PLAN.md:73-78` の成果物一覧から `distribution/はじめに.md` が漏れている（`.planning/phases/06-release-validation/06-02-PLAN.md:30-32,101-106` の `06-02-02` 側にも作成・更新タスクが存在する）。また、`06-01-01` 実行時点では `pagefolio/constants.py:12` の `APP_VERSION` は `"v1.9.1"` であるため、トレーサービルドの出力先は `dist/PageFolio-v1.9.1` となる点に注意が必要である。
- **LOW**: **Windows におけるディレクトリ入替（`os.replace`）の非原子性とロック競合**
  - 根拠: `.planning/phases/06-release-validation/06-01-PLAN.md:94,113` で「staging 成功後にのみ出力先を原子的に入れ替え」「再ビルド時のみ自社 marker 付き既存出力を backup 経由で入替」としているが、Windows の `os.replace` は非空ディレクトリ同士の上書きができず、リネーム中に Explorer やウイルス対策ソフトがハンドルを掴んでいると `PermissionError`（`WinError 5`）が発生しやすい。

### 4. 具体的提案
1. `tools/build_release.py` から PyInstaller を呼び出す際は、`--specpath`・`--workpath`・`--distpath` に加え、`--icon`（`repo_root / "pagefolio.ico"`）およびエントリポイント（`repo_root / "pagefolio.py"`）をすべて `Path.resolve()` した絶対パスで渡すことを `06-01-PLAN.md:94` に明記すること。
2. `06-01-01` では `distribution/はじめに.md` の初期正本を作成して `06-01-PLAN.md:25-33` の `must_haves.artifacts` にも含め、`06-02-02` はその内容を D-01〜D-12 の全要件で完成・検証する役割分担として明文化すること。また、トレーサービルドで生成される `dist/PageFolio-v1.9.1` が後続の `dist/PageFolio-v1.10.0` と干渉しない（またはクリーンアップされる）ことを整理すること。
3. 既存出力の backup 退避・昇格リネームには、Windows 特有の一時的ファイルロックに備えた短時間の段階的リトライ（例: 50ms〜200ms × 数回）と、昇格失敗時に backup を元の場所へ戻すロールバック処理を必ず実装すること。

### 5. 総合リスク
**LOW**

---

## 06-02

### 1. 要約
`pagefolio/constants.py` の `APP_VERSION` を `"v1.10.0"` へ更新し、`README.md`・`開発履歴.md`・`docs/DEVELOPMENT.md`・`distribution/はじめに.md` を同期させた上で、それらの整合性を検証する `tests/test_release_contract.py` を追加する計画である。

### 2. 強み
- **単一情報源（SSOT）原則の徹底**: `AGENTS.md:15-18` の規約通り、`pagefolio/constants.py:12` の `APP_VERSION`、`README.md:5` のバッジ、`開発履歴.md` を同期させ、かつ `.planning/phases/06-release-validation/06-02-PLAN.md:89` で「未実施の EXE/UAT を成功と書かない」制約を課している点は誠実で安全性が高い。
- **`docs/DEVELOPMENT.md` の手動手順との不整合解消**: 現在の `docs/DEVELOPMENT.md:190-209` は `--distpath dist` による `dist/PageFolio/` 出力と手動でのサンプルコピーを案内しており、Phase 6 の D-01/D-02（`dist/PageFolio-v1.10.0` への自動同梱と `はじめに.md` 追加）と乖離している。`.planning/phases/06-release-validation/06-02-PLAN.md:89` がこの更新をスコープに含めている点は的確である。

### 3. 懸念
- **MEDIUM**: **`開発履歴.md` 内の3箇所のバージョン記述構造と Phase 5 記述の更新方法が曖昧**
  - 根拠: 現在の `開発履歴.md` は、(1) 先頭の `## 未リリース — Phase 5 設定の読込・保存失敗通知（2026-10-24）`（`開発履歴.md:3-19`、ここに `全件1789 passed... H01〜H12は12 pass... Nyquistと独立検証は未実施` という古い記述がある）、(2) `## v1.9.1 — 2026-10-22`（`開発履歴.md:23`）、(3) 引用ブロック `> **最終更新**: v1.9.0 — 2026-08-11`（`開発履歴.md:37`）、(4) `## バージョン索引` テーブル（`開発履歴.md:72-80`、`v1.9.0` までしか記載がない）という構造になっている。`.planning/phases/06-release-validation/06-02-PLAN.md:89` の「最新v1.10.0節を同期する」「Phase5履歴の古い受入状況を現在の正本に照合した追記で補い、履歴自体は消さない」だけでは、`## 未リリース` 見出しを `## v1.10.0` に昇格させるのか別節を立てるのか、また `開発履歴.md:37` と `開発履歴.md:74` の索引テーブルをどう更新するのかが曖昧であり、`TestVersionAndDocs` の正規表現と齟齬を生む懸念がある。
- **LOW**: **`distribution/はじめに.md` のバージョン表記と単体テストの結合度**
  - 根拠: `.planning/phases/06-release-validation/06-02-PLAN.md:104` で `distribution/はじめに.md` に `PageFolio-v1.10.0` を明記する設計となっているため、`TestUserGuideContract` でバージョン文字列を検証する際は `pagefolio/constants.py:12` の `APP_VERSION` と連動させるのが望ましい。

### 4. 具体的提案
1. `06-02-PLAN.md:89` において、`開発履歴.md` の具体的な見出し構成（例: 先頭に `## v1.10.0 — YYYY-MM-DD ...` 節を配置し、`開発履歴.md:3-19` の Phase 5 節には `.planning/phases/05-config-notification/05-UAT.md:46-94` の最終結果「H01〜H14 + Test 1/2 の計16件 pass・Nyquist 検証済」を追記すること、および `開発履歴.md:37` の最終更新行と `開発履歴.md:74` のバージョン索引テーブルに `v1.9.1` / `v1.10.0` を反映すること）を明示すること。
2. `tests/test_release_contract.py` の `TestVersionAndDocs` では、`APP_VERSION`（`pagefolio/constants.py:12`）、`README.md:5` のバッジ、`開発履歴.md` の最新バージョントップ見出し、`distribution/はじめに.md` 内の展開フォルダ名（`f"PageFolio-{APP_VERSION}"`）の4点一致を機械的に検証すること。

### 5. 総合リスク
**LOW**

---

## 06-03

### 1. 要約
審査ツール `tools/verify_release.py`（`bundle` / `exe-smoke` / `exe-functional` / `uat-init` / `uat-validate` / `audit`）を実装し、凍結 EXE に対する機能スモーク（X01〜X06）、ローカル loopback の擬似 Ollama サーバ、Win32/UI 観測、および設定ファイル異常注入の仕組みを構築する計画である。

### 2. 強み
- **Ollama プロバイダを選定したローカル完結テストの妥当性**: `pagefolio/ocr_providers/ollama.py:19,86-156` は API キー（環境変数）を必要とせず、標準ライブラリの `urllib.request.urlopen` で `{base_url}/api/chat`（POST）および `{base_url}/api/tags`（GET）と通信する。また `pagefolio/ocr_dialog.py:1309-1311,1643-1648` は `self.settings.get("ollama_url")` と `self.settings.get("ollama_model")` を直接読み取ってプロバイダを生成するため、作業コピー側の `pagefolio_settings.json` に `ocr_provider="ollama"` と `127.0.0.1:<ephemeral_port>` を書き込む設計（`.planning/phases/06-release-validation/06-03-PLAN.md:115`）は外部通信ゼロで確実に機能する。
- **Phase 4 / Phase 5 の既存観測資産の適切な活用**: `tests/test_startup_windows.py:72-184` の Win32 ウィンドウ列挙・クラッシュ監視や `tests/config_notice_support.py:55-127` の設定ファイル検証パターンを流用し、実 EXE を改変せずに外部から検証するアプローチが明確である。

### 3. 懸念
- **HIGH**: **`W05b`（OCR所有のネイティブ `messagebox`）を「fallback 無効＋fake OCR 応答エラー」で発火させることはコード上不可能**
  - 根拠: `.planning/phases/06-release-validation/06-03-PLAN.md:115` には「`fallbackを無効化して既存LLM/OCR UI経由で開始する。... W05bはfake OCR応答エラーから本物のOCR所有messageboxを表示し人が閉じるカードを用意する`」と記載されている。しかし、`pagefolio/ocr_dialog.py:2030-2064`（`_finish_error`）および `pagefolio/ocr_dialog.py:1946-2015`（`_render_results_ordered` / `_finish_complete`）を確認すると、OCR 実行中の通信エラーや HTTP 500 エラーはダイアログ内のテキストウィジェットと進捗ラベル（`self.progress_var`）に書き込まれるだけで、`messagebox.showerror` 等は一切呼ばれない。`_finish_error` 末尾の `self._propose_fallback(kind, msg)`（`pagefolio/ocr_dialog.py:2063`）も、`ocr_fallback_enabled` が `False` の場合は `pagefolio/ocr_dialog.py:2471-2472` で即座に `return` するため、ネイティブ `messagebox` は絶対に表示されない（なお Python ハーネス版の `tests/test_startup_windows.py:1848-1850` はテストコードから直接 `messagebox.showinfo(..., parent=state["target"])` を呼んでいたため発火していた）。
- **HIGH**: **合成3ページ PDF に埋め込みテキストがあると Vision OCR（Ollama 通信）がスキップされる**
  - 根拠: `.planning/phases/06-release-validation/06-03-PLAN.md:115` で「合成3ページPDFのOCR応答を返す」としているが、`pagefolio/ocr_dialog.py:1718-1725` の `_render_next_page` は `if not self._force_ocr and has_embedded_text(page):` を判定し、ページに埋め込みテキストが存在すると LLM API を呼ばずに埋め込みテキスト抽出で完了させてしまう（`tests/conftest.py:36` のような `page.insert_text(...)` を使うと `has_embedded_text` が真になり得る）。
- **MEDIUM**: **凍結 EXE（`--noconsole`）では `logger.debug` が出力されないため、設定失敗分類を「ログで確認」できない**
  - 根拠: `.planning/phases/06-release-validation/06-03-PLAN.md:115` に「`EXEの設定missing/corrupt/unreadable/write-fail/replace-failは隔離copyに合成JSON、外部CreateFileWのshare制限で読取/削除を拒否するlock、専有tmp衝突等を準備し、実際のエラー分類をログで確認してから使う`」とある。しかし `pagefolio/settings.py:317-319`（`_load_settings_result`）および `pagefolio/settings.py:384-388`（`_save_settings`）は `logger.debug(...)` でしかログを出さず、無改変の凍結 EXE にはファイルロガーや標準出力ハンドラが構成されていないため、外部プロセスから `logger.debug` を読むことはできない。

### 4. 具体的提案
1. **`W05b` の発火経路の修正**: 無改変の凍結 EXE で `OCRDialog` 所有のネイティブ `messagebox`（`parent=self`）を確実に表示させるため、`06-03-PLAN.md:115` の `W05b` シナリオを以下のいずれか（または両方）に変更すること。
   - **案A（推奨・実行中クローズ確認）**: `W05a` と同様に fake Ollama サーバが応答を遅延（hold）している最中に、`OCRDialog` の閉じるボタン（`WM_CLOSE` / `✕ 閉じる`）を送出して `pagefolio/ocr_dialog.py:2085-2097` の `_on_close()` → `messagebox.askyesno(self._L["confirm_title"], self._L["ocr_close_during_run"], parent=self)` を表示させる（これなら fallback 無効のまま確実に `OCRDialog` 所有のネイティブモーダルが出る）。
   - **案B（フォールバック提案モーダル）**: `W05b` 専用プロファイルとして `ocr_fallback_enabled: true` かつ `ocr_fallback_chain: ["lmstudio"]` を設定し、fake Ollama サーバが接続拒否または3回連続エラー（`CB_CONSECUTIVE_FAILURES = 3`、`pagefolio/ocr_dialog.py:74`）を返して `pagefolio/ocr_dialog.py:2497-2507` の `messagebox.askyesno(..., parent=self)` を発火させる。
2. **合成 PDF の仕様明記**: `X03` / `W05a` / `W05b` で生成する合成3ページ PDF は、`has_embedded_text(page)` が必ず `False` になるよう、テキストを含まないラスタ画像（`page.insert_image`）または図形のみのページとして生成することを `06-03-PLAN.md:115` に明記すること。
3. **設定失敗分類の検証方法の精緻化**: `X04` における `missing` / `corrupt` / `unreadable` / `save-write` / `save-replace` の分類確認は、EXE の内部 `logger.debug` ではなく、(a) 注入前のハーネス側での事前検証、(b) `save-write`（既存 `.tmp` 衝突により `owned_tmp=False` のまま失敗し `.tmp` が残存：`pagefolio/settings.py:377-379,389`）と `save-replace`（対象 `pagefolio_settings.json` を外部プロセスから `CreateFileW` の `FILE_SHARE_READ | FILE_SHARE_WRITE`［`FILE_SHARE_DELETE` なし］で保持することで、起動時読込と `.tmp` 作成は成功しつつ `os.replace` のみ失敗し `.tmp` が自動削除される：`pagefolio/settings.py:381,391`）のファイルシステム状態差、(c) トースト通知文言の差によって判定するよう `06-03-PLAN.md:115` を修正すること。

### 5. 総合リスク
**HIGH**（`W05b` の発火条件および合成 PDF の埋め込みテキスト条件を修正すれば **LOW** に低減可能）

---

## 06-04

### 1. 要約
`tools/build_release.py` を用いて `dist/PageFolio-v1.10.0` の初回クリーンビルドと管理下再ビルドを実行して `06-BUILD-EVIDENCE.json` に記録し、続けて作業コピー上で `verify_release.py` の `bundle` / `exe-smoke` / `exe-functional`（X01〜X05）を実行して `06-EXE-EVIDENCE.json` を作成する計画である。

### 2. 強み
- **出荷フォルダ不汚染の原則**: `.planning/phases/06-release-validation/06-04-PLAN.md:96` において、`dist/PageFolio-v1.10.0` 本体を直接起動するのではなく、一時ディレクトリ上の作業コピーで X01〜X05 を実行し、実行前後で出荷フォルダのファイル集合と全ファイル SHA-256 が不変であることを検証する設計は、配布物のクリーンさを保証する上で非常に優れている。
- **PyInstaller の非決定性に対する現実的な配慮**: `.planning/phases/06-release-validation/06-04-PLAN.md:80` で「二つの実EXEのbit再現性は要求せず、各入力と各成果物のhashを個別に記録する」と明記しており、PE ヘッダや PYZ タイムスタンプによる不要なビルド失敗を防いでいる。

### 3. 懸念
- **HIGH**: **`06-04-01` の `<verify><automated>` が3回目のビルドを実行し、`06-BUILD-EVIDENCE.json` のハッシュ記録を破壊する**
  - 根拠: `.planning/phases/06-release-validation/06-04-PLAN.md:80` の `<action>` では、初回クリーンビルド（1回目）と管理下再ビルド（2回目）を実行し、最終成果物のハッシュを `.planning/phases/06-release-validation/06-BUILD-EVIDENCE.json` に記録する。ところが、直後の `06-04-PLAN.md:85` の `<verify><automated>` に `.venv/Scripts/python.exe tools/build_release.py --output-root dist` が指定されている。PyInstaller の生成 EXE はビルドごとにハッシュが変わるため、`<verify>` で再度 `build_release.py` を走らせると3回目のビルドが実行され、`dist/PageFolio-v1.10.0/PageFolio.exe` と `release-report.json` が上書きされて `06-BUILD-EVIDENCE.json` に記録した SHA-256 と不一致になり、後続の `06-04-02`（`06-04-PLAN.md:96`）および `06-05-01`（`06-05-PLAN.md:74`）の同一性チェックが必ず失敗する。
- **MEDIUM**: **`06-03` の懸念（合成 PDF の埋め込みテキスト・設定失敗分類の確認手段）の波及**
  - 根拠: `.planning/phases/06-release-validation/06-04-PLAN.md:96` の X03（設定・OCR ダイアログ）および X04（設定通知）は `06-03` の `exe-functional` 実装に依存するため、`06-03` で指摘した合成 PDF の画像ページ化と `CreateFileW` 共有モード制御が正しく実装されている必要がある。

### 4. 具体的提案
1. `06-04-PLAN.md:85`（Task `06-04-01`）の `<verify><automated>` を `build_release.py` の再実行ではなく、`verify_release.py bundle` または `06-BUILD-EVIDENCE.json` と `dist/PageFolio-v1.10.0/release-report.json` のハッシュ一致・2回ビルド履歴存在を検証するコマンド（例: `.venv/Scripts/python.exe tools/verify_release.py bundle --bundle-dir dist/PageFolio-v1.10.0 --build-evidence .planning/phases/06-release-validation/06-BUILD-EVIDENCE.json`）に変更すること。
2. もし `<verify>` 内で `build_release.py` を実行したい場合は、`<action>` 自体で2回実行後に `06-BUILD-EVIDENCE.json` を確定させ、`<verify>` では読み取り専用の検証コマンドのみを実行するように徹底すること。

### 5. 総合リスク
**HIGH**（`06-04-01` の `<verify>` コマンドによる再ビルド上書き問題を修正すれば **LOW**）

---

## 06-05

### 1. 要約
人間による実機 UAT（Phase 4 繰越しの `W01`〜`W12`、Phase 5 繰越しの `H01`〜`H14` + `Test 1`/`Test 2`、Phase 6 の `X06`）の記録テンプレートと実行カードを `06-PRODUCTION-UAT.md` に生成し（`06-05-01`）、ユーザーによる実機確認・記入を経て `verify_release.py uat-validate` で完了検証と上流 UAT 文書への相互リンク同期を行う（`06-05-02`）計画である。

### 2. 強み
- **AI による UAT 捏造の厳格な防止**: `.planning/phases/06-release-validation/06-05-PLAN.md:74,95` で、`06-05-01` 時点では `pending` 状態のテンプレートのみを生成し、`06-05-02` で人間が記入した実績時刻・観察メモ・証跡を `uat-validate` で機械検証する2段階構成（`checkpoint:human-verify`）としており、`.planning/phases/04-startup-control/04-WINDOWS-UAT.md:10-25` や `.planning/phases/05-config-notification/05-UAT.md:1-45` の厳格な証跡要件を満たしている。
- **別 Windows ログインセッション（`W11`）の停止ゲート明文化**: `.planning/phases/06-release-validation/06-05-PLAN.md:95,103` で、同一ユーザー別プロセスでの代用を禁止し、別 Windows アカウント／別ログオンセッションが準備できない場合は `environment-blocked` としてリリース承認を止める設計が明確である。

### 3. 懸念
- **MEDIUM**: **`06-05-02` の前提条件である「親 workflow の `$gsd-execute-phase 04` による stale 再検証」の実行タイミング**
  - 根拠: `.planning/phases/06-release-validation/06-05-PLAN.md:91` の `<preconditions>` に「`親workflowの $gsd-execute-phase 04 による現行入力のstale再検証が完了し、04-VERIFICATIONの対象hash/鮮度が現行と一致する`」とある。現在の `.planning/phases/04-startup-control/04-VERIFICATION.md:4-7` は Phase 5 での `pagefolio/app.py` 等の変更により stale 状態にある。幸い Phase 6 の全計画（`06-01`〜`06-06`）は `04-VERIFICATION.md:6` の `covered_files`（`pagefolio/app.py`、`pagefolio/lang.py`、`pagefolio/startup_*.py`、`tests/test_startup_*.py`、`tests/test_gsd_dod.py`）を一切変更しないため、Phase 6 の実行前または `06-05-02` の前に一度 Phase 4 の再検証を完了させておけばハッシュは維持されるが、オーケストレータがこれを忘れると Wave 5 で停止する。
- **MEDIUM**: **`X06` におけるバージョン確認箇所の記述（「About/タイトルの版」）と実 UI の差異**
  - 根拠: `.planning/phases/06-release-validation/06-05-PLAN.md:95` に「`X06は... About/タイトルの版とfolder/report一致を確認する`」とあるが、PageFolio には独立した「About ダイアログ」は存在せず、`APP_VERSION` はウィンドウタイトルおよびヘッダーラベルに表示される仕様である。人間向け UAT カードに「About ダイアログを開く」と書かれるとテスターが迷う懸念がある。

### 4. 具体的提案
1. `06-05-01` が生成する `X06` の人間向け手順カードでは、「About ダイアログ」ではなく実際の表示箇所（メインウィンドウのタイトルバーおよびヘッダー領域の `v1.10.0` 表示）を確認するよう具体的に記述すること。
2. `06-03` で指摘した通り、`06-05-01` が生成する `W05b` の実行カードは、無改変 EXE で実際にネイティブ `messagebox` が発生する手順（OCR 実行中の閉じるボタン押下による確認ダイアログ、または fallback 有効時のフォールバック確認ダイアログ）を案内すること。
3. Phase 6 実行開始前（または Wave 5 突入前）に Phase 4 の stale 再検証を実施し、`.planning/phases/04-startup-control/04-VERIFICATION.md` の `input_digest` を現行ワークツリーに同期させる手順を親ワークフロー側で確実に実行すること。

### 5. 総合リスク
**MEDIUM**（人間の実機操作と別 Windows セッション準備を伴うため）

---

## 06-06

### 1. 要約
全件品質ゲート（Ruff lint/format、AST、単一全件 `pytest`）の証跡を `06-EVIDENCE.json` に固定し、`verify_release.py audit --for-handoff` で全要件・全証跡・配布フォルダ不変性を監査した上で、`06-VERIFICATION.md` とセッション終了申し送りを作成する最終計画である。

### 2. 強み
- **全入力マニフェストとビルド・UAT・品質ゲートの完全な連鎖監査**: `.planning/phases/06-release-validation/06-06-PLAN.md:83,104` が、コード・テスト・ドキュメント・ビルド成果物・UAT 証跡・品質ゲート証跡のすべてのハッシュと時刻順序（`build <= exe <= uat`）を `verify_release.py audit --for-handoff` で機械的に照合する設計になっており、検証漏れや古い証跡の混入を防ぐ仕組みとして完成度が高い。
- **長時間 pytest の安全な再利用条件の定義**: 全件 `pytest` が約4分半（`.planning/STATE.md:49` で 1789 passed in 271.22s）かかることを踏まえ、`06-06-PLAN.md:104` で全入力マニフェストが完全一致する場合の証跡再利用条件と、不一致時の再実行ルールを厳密に定めている。

### 3. 懸念
- **LOW**: **`06-06-02` の `<verify><automated>` による全件 `pytest` の二重実行とタイムスタンプ逆転リスク**
  - 根拠: `.planning/phases/06-release-validation/06-06-PLAN.md:104` の `<action>` では、「`auditより前に06-EVIDENCEへ実commit+dirtyhash/全入力manifest/コマンド/exit/件数/時間/ログhashを記録する`」とし、その後 `verify_release.py audit --for-handoff` を実行して `06-VERIFICATION.md` を作成する。しかし `06-06-PLAN.md:107` の `<verify><automated>` に `.venv/Scripts/python.exe -m pytest -q --basetemp=...` が設定されているため、`<action>` 内で全件 `pytest` を実行した後に `<verify>` でもう一度約270秒の全件 `pytest` が走る構成になっている。

### 4. 具体的提案
1. `06-06-02`（`06-06-PLAN.md:104-109`）では、全件 `pytest` の実行結果をそのまま `06-EVIDENCE.json` に記録するラッパー（または `verify_release.py audit --for-handoff` 自体）を `<verify><automated>` の最終確認コマンドとすることで、約270秒のテストスイートが無駄に2回連続実行されるのを防ぐこと。

### 5. 総合リスク
**LOW**

---

## 横断評価

1. **エッジケースとエラー処理**
   - 設定ファイル関連の5分類（`missing` / `corrupt` / `unreadable` / `save-write` / `save-replace`）や、既存 `dist/PageFolio` の保護、出荷フォルダ `dist/PageFolio-v1.10.0` を直接起動せず作業コピーで検証する設計など、ファイルシステム周りのエッジケースは非常に丁寧に考慮されている。
   - 一方で、**無改変の凍結 EXE における `OCRDialog` の挙動**に関する2つのエッジケース（① `pagefolio/ocr_dialog.py:2030-2064,2471-2472` において fallback 無効時は OCR エラーでネイティブ `messagebox` が出ない点、② `pagefolio/ocr_dialog.py:1718-1725` において合成 PDF に埋め込みテキストがあると Vision OCR がスキップされる点）が見落とされているため、`06-03` の実装前に必ず計画を補正する必要がある。
2. **依存関係と実行順序（Wave 構成）**
   - Wave 1（`06-01` ビルド基盤）→ Wave 2（`06-02` v1.10.0 文書・契約テスト）→ Wave 3（`06-03` 審査ツール `verify_release.py`）→ Wave 4（`06-04` 実ビルドと EXE 自動検証）→ Wave 5（`06-05` 実機 UAT、および `06-06` 最終監査）の依存順序は論理的で破綻がない。
   - ただし、**`06-04-01` の `<verify><automated>` で `build_release.py` を再実行してしまう問題**（`06-04-PLAN.md:85`）は、`06-BUILD-EVIDENCE.json` に記録した EXE の SHA-256 を直後に上書き破壊して後続の `06-04-02`〜`06-06` を連鎖失敗させるため、実行前に修正が必須である。
   - また、`06-05-02` の前提条件である Phase 4 の stale 再検証（`04-VERIFICATION.md` の更新）を Wave 5 開始前までに完了させる段取りを徹底する必要がある。
3. **過剰設計・安全性・パフォーマンス**
   - `tools/build_release.py` と `tools/verify_release.py` の2スクリプトへの責務分離は明確であり、アプリ本体（`pagefolio/` 配下）のロジックには `pagefolio/constants.py:12` の `APP_VERSION = "v1.10.0"` 以外一切手を加えないため、Phase 4・Phase 5 で確立した起動制御や設定通知の安定性を損なうリスクが極めて低い。
   - パフォーマンス面では、PyInstaller ビルドと全件 `pytest`（約270秒）が重いため、`06-04-01` と `06-06-02` の `<verify>` での重複実行を排除することで実行時間を大幅に短縮できる。
4. **フェーズ目標の達成可能性**
   - 上記の指摘事項（特に `06-03` の `W05b` 発火手順・合成画像 PDF 化・設定エラー観測方法、および `06-04-01` の `<verify>` コマンド修正）を反映すれば、Phase 6 の全要件（`REL-01`、`DOC-01`、および上流繰越し UAT の完全クローズ）は確実に達成可能である。

---


## Grok Review

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

---


## Consensus Summary

### 総合判定

**実行前の計画修正を推奨。** 3 CLIとも実レビューを返し、各06-01〜06-06の6/6を被覆した。計画レビューの完了であり、実装・実build・実機UAT・Phase完了・出荷承認ではない。Phase4 stale、未解除回帰、W11等のnot-run、出荷停止は維持する。

### Agreed Strengths

- 正本をビルド出力外へ保持し、管理済み出力だけを再生成する設計、版同期後の最終build、原本の前後hash照合は3者が支持した。
- Python注入と実配布EXEの証拠を分け、既存H受入の不要な再実施を避ける方針、全必須人手passと親の独立ゲートまで出荷を止める方針は概ね一致した。
- 6直列waveの依存順と、引渡し監査/最終監査の分離は妥当。未作成の計画成果物は存在しないだけで欠陥とはしない。

### Agreed Concerns

| ID | 優先度 | 対象 | 指摘と統合判断 |
|---|---|---|---|
| R06-01 | HIGH | 06-01 | 私有spec/work/distとentry/iconの絶対パスを明記し、実build前にargv・保護境界の負例を固定する。Claude/Antigravityの相対icon懸念はローカルPyInstallerで確認。`api.py:591-595,727-735`がiconをspecpathへ接続する。一方scriptは`makespec.py:753-754`でspec相対へ変換するため「scriptも必ず失敗」は不採用。計画`:94`に私有領域・shell=Falseは既にあるので、Grokの「安全設計がない」とは扱わず検証順序と明示性を補強する。 |
| R06-02 | MEDIUM | 06-01 | 既定`--output-root dist`と「ソース/旧distとの重なり拒否」の判定対象が曖昧（Claude/Grok）。`.planning/phases/06-release-validation/06-01-PLAN.md:94,111`。最終先・work・history各解決パスの保護条件と、既定コマンドが通る正例を具体化する。 |
| R06-03 | HIGH | 06-04 | actionの初回/再build後、verifyのbuild再実行で証拠を再生成し得る（3者が回数/役割を指摘）。`06-04-PLAN.md:78-86`。2回の実行を一度ずつ記録し、確定後verifyはhash・履歴の読み取り専用照合とする。hashが必ず変わるとは断定しないが、記録済みbinaryを再生成する必要はない。 |
| R06-04 | MEDIUM | 06-04〜06 | Phase4再検証の担当・時機と、修正後の再build/証拠失効/再受入経路を明文化する（3者）。`06-05-PLAN.md:91`、`06-04-PLAN.md:96`。接続準備実証は本受入と別であることを保持し、製品変更後の旧binary観測を再利用しない。 |
| R06-05 | MEDIUM | 06-05 | 対応する別版EXEの出所・版・hash・証拠種別を指定する（Claude/Grok）。`06-05-PLAN.md:80,95`。同版copyは別配置だけを証明する。tracerや試験用別版を本番EXE受入へ混同しない。 |
| R06-06 | MEDIUM | 06-06 | WR-01不適合時の停止・修正/再計画への分岐と利用者承認を明記する（Claude/Grok）。`06-06-PLAN.md:88,92`。15609ms/15140msを保持し、期限延長・負荷条件縮小による黙示合格を禁止する。 |

### ソース照合で採用する個別指摘

- **R06-07 / HIGH — W05bの発火経路:** `06-03-PLAN.md:115`はfallback無効＋fake OCRエラーを指定。しかし`pagefolio/ocr_dialog.py:2030-2063`は結果欄へ表示し、`:2471-2472`はfallback無効で戻る。Antigravityの指摘を親が確認した。実行中の閉じる確認（`:2085-2097`、parent=self）など、実在するネイティブmodal経路へカードを修正する。代替の操作・状態維持は実機で検証する。
- **R06-08 / MEDIUM — fake OCRの入力/件数:** Claudeの3ページ対1request、Antigravityの埋め込み文字による通信skipを採用。`pagefolio/ocr.py:652-659`で並列度を設定し、`pagefolio/ocr_dialog.py:1717-1737`は埋め込み文字をskipする。画像PDFまたはforce OCR、対象ページ、並列度、ページごとのrequest/再送の同一性を明示する。3ページが常に1requestになるとはみなさない。
- **R06-09 / MEDIUM — 設定失敗の観測:** `pagefolio/app.py:141-144`のloggingはWARNING、`pagefolio/settings.py:314-319,384-393`の分類出力はDEBUG。未改変noconsole EXEからそのログを取得できるという前提は不十分。外部lock/ファイル状態/通知/時点を組み合わせ、何を確認できるか明示する。write/replaceの内部原因を通知だけで区別できるとはしない。
- **R06-10 / MEDIUM — X01と版表示:** Grok指摘を親が確認。`06-05-PLAN.md:95`のX01〜05共通「非モーダル文言」はmissing時の警告なし契約と分ける。`pagefolio/app.py:146`のタイトルはPageFolio固定、`pagefolio/dialogs/about.py:18,49`にはAboutDialogとAPP_VERSIONがある。版確認をAbout・folder・reportへ具体化し、未計画のタイトル変更を要求しない。missingの終了時には正当な設定保存があり得るので、「不存在維持」は起動安定時までとする。
- **R06-11 / MEDIUM — 人手taskの完了監査:** ClaudeはHIGH、Grokは本文の停止条件を肯定。`06-03-PLAN.md:80`と`06-05-PLAN.md:98-100`はallow-pendingを構造監査に限定し、not-runなら未完了と明記している。既にある停止契約を「欠落」と断定しない。ただしtype=autoのverifyとtask完了の誤読を防ぐため、担当ID/subrowのpassを要求する監査か、明示的なblocking-human経路を検討する。`end-of-phase`の利用者方針を無断変更しない。
- **R06-12 / MEDIUM — 既存dirty差分の扱い:** Claudeの指摘。既存requirements/tests/開発履歴の差分を勝手にcommit・取り消ししない。task由来の変更と既存変更を分離してstageする。最終buildの入力固定・commit対応については、現在のcommit+dirtyhash契約から変更するなら計画時に明示する。

### Divergent Views・訂正と保留

- **Antigravityは重みを下げる。** 全6見出しとソース引用はあるが、計画にない`tools/verify_release.py`、`06-EXE-EVIDENCE.json`、`06-PRODUCTION-UAT.md`、`REL-01/DOC-01`を混入している。現行は`tests/release_uat_support.py`等（`06-03-PLAN.md:8-11,24-31`）、要件はV110-DIST/QA。これらの架空契約を採用しない。
- Antigravityの`/api/chat`/`/api/tags`は誤り。現行は`pagefolio/ocr_providers/ollama.py:94,170`の`/v1/chat/completions`/`/v1/models`。「Aboutが存在しない」も上記R06-10に反する。`checkpoint:human-verify`が現PLANにあるという記述も誤り。
- Antigravityの原子的ディレクトリ入替という要約は、`06-01-PLAN.md:111`の「二つのrenameは一括atomicではない」と矛盾する。rollbackは既に計画済み。追加リトライは必須欠陥修正とはしない。
- Claudeの改行懸念は、実測でOCRサンプルCRLF・summaryサンプルLFを確認した。現行copy前後のbytes照合自体は成立する。別cloneで固定hashを使う場合の属性/改行規約の検討事項とする。
- main固定リンク、履歴の索引、保持容量、古lock回復、UAT中断再開は改善候補。今回これらを実装せず、採否は`$gsd-plan-phase 6 --reviews`で決める。
- Grokの実buildをtracer後へ移す提案は現tracer方針との調整が必要。安全境界を実build前に証明する目的を採用し、タスク順変更自体は自動適用しない。

### 検証・来歴

- 外部CLI: Claude / Antigravity / Grokすべて`ok=true, stubbed=false`。各6/6の正確な`## 06-NN`見出しを確認。Antigravityのモデル名は取得不能でunknown。モデルを推測しない。
- 6PLANのレビュー前後SHA-256不一致0。製品コード・計画・STATE・既存dirty差分は編集していない。
- コミット前品質証拠は`05-EVIDENCE.json`のlatest_automated_verification（1797 passed、failed0、errors0、1 warning、exit0）を再利用。tested_files_sha256全103件が現行一致。Python3.15.1/Tk9.0/pytest9.1.1を確認。Phase06計画時にも1797 passedの記録があるが、今回の新規テスト実行とはしない。
- 今回はレビュー文書のみのためPython lint/format・pytestを重複実行せず、文書diffと被覆・hashを検証する。過去成功を回帰原因解決や実機passへ読み替えない。
- 次の入口: `$gsd-plan-phase 6 --reviews`。本レビューで計画修正や実行は開始しない。