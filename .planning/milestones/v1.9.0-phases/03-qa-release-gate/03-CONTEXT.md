# Phase 3: 品質保証・リリースゲート - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Python 3.14.6 環境で GUI テストを含む全テストスイートを完走させるための切り分け・修復を行い、その完走条件をリリースゲートとして定義・文書化する。あわせて保存トーストの再試行挙動を確定し、実機目視による human-verify / UAT を正式に実施・記録して v1.9.0 のリリース判定を固める。

**対象要件（3件）:** V190-QA-01, V190-QA-02, V190-QA-03

**このフェーズに含まれないもの:**
- PyInstaller リビルド・注釈付きタグ付与・GitHub Release 公開（マイルストーンクローズ後のクイックタスク。過去の運用 260709-rel / 260722-rel を踏襲）
- Phase 1/2 で実装済みの機能そのものの変更（回帰が見つかった場合を除く）
- 実 API キー・課金が必要で今回用意できない検証項目（Deferred へ理由付きで記録）
- Undo 記録先置き op への水平展開（Phase 1 D-12・次マイルストーン候補）
- `OCR_PRICE_TABLE` 一元化・プラグイン catalog 登録 API（Phase 2 Deferred）

</domain>

<decisions>
## Implementation Decisions

### 全テスト完走ゲートの合格条件（V190-QA-01）

- **D-01:** 「全テスト完走」は **まずタイムボックス付きで根本原因を追い、解消できなければ「定義された分割実行手順で全 1387 件グリーン」を合格とする**。単一プロセス `pytest -q` 一発グリーンを必達にはしない。STATUS_BREAKPOINT クラッシュは**製品コード無実が A/B 検証済み**（STATE.md「Blockers/Concerns」・HEAD 内容 4/4 green・基準内容は累計19回中0クラッシュ）であり、原因未解明のネイティブ層調査で出荷判定をブロックさせないため。ただし分割の**根拠と手順は必ず文書化**する。
- **D-02:** 根本原因追求は **「仮説 2 本を検証したら打ち切り」** を契約とする。2 本とも外れたら分割実行へ確定させる。検証した仮説と**反証データを成果物に残し**、次マイルストーンで同じ地面を掛け直さないようにする。
- **D-03:** STATUS_BREAKPOINT クラッシュで検証する 2 仮説は以下に固定する。
  1. **pytest assertion rewriting 仮説** — `--assert=plain` / `-p no:cacheprovider` で再現するか。STATE.md が確定させた「`tests/test_pdf_ops.py`（01-07 版）の *import 時点* で成立し、`--deselect`（import するが 1 件も実行しない）でも再現、`--ignore`（import しない）では再現しない」という性質を直撃する。コマンド 1 発で白黒がつき、製品コードを触らない。
  2. **二分探索** — `tests/test_pdf_ops.py`（01-07 版）の内容を二分探索し、引き金となる最小コード片を特定する。既に「モジュールサイズ模倣・`import ast`/`pathlib` の追加では再現せず」まで絞り込み済みなので、次の一手として自然。
  - `_drive_pipeline` の孤児 daemon スレッド仮説は**既に棄却・revert 済み**（STATE.md）。再検証しない。
- **D-04:** もう 1 つの症状（`TclError` によるセットアップ ERROR・毎回異なる 2 件のフレーキー）は **同じ調査プランで並行して切り分ける**。両症状とも「フルスイートを単一プロセスで回すと壊れる」同じ実行文脈に現れるため、実験の仕掛け（1387 件を回して観測する）を共有できる。ただし**別症状として別々に結論を記録**し、片方の解消をもう片方の解消と読み替えない。

### 環境修復の手段と置き場（V190-QA-01）

- **D-05:** 修復は **切り分け結果駆動**とする。先に実機で再現条件を特定し、その原因に対応する修復だけを入れる。再現しなければ**コード変更ゼロ**で「現行環境では解消済み」と根拠付きで記録して閉じる。`.venv`（Python 3.14.6）での `tkinter.Tk()` 単体実行は**現在成功している**（Tk 8.6.15・本 discuss で実測）ため、予防的な `TCL_LIBRARY`/`TK_LIBRARY` ハードコードは入れない — PITFALLS §13 が「開発環境のテストは直るが配布 EXE の Tcl/Tk 探索ロジックと衝突して逆に壊れる」と名指しで禁じたパターンだから。
- **D-06:** 修復のコード変更は **`tests/` 配下に閉じることを原則**とする。製品コード（`pagefolio/`）への変更が必要と判断された場合は、**先に根拠（実際にユーザーが遭遇し得る不具合であること）を提示して判断を仰ぐ**。A/B 検証で製品コード無実は確認済みであり、リリース直前のフェーズで製品コードを広く触るのは回帰リスクが高い。
- **D-07:** 記録先を 2 系統に分ける。**日常の実行手順**（分割コマンド・リリースゲートの合格条件）は `CLAUDE.md` の「変更時のチェックリスト」へ — 実行者が必ず見る場所だから。**切り分けの実験ログと反証データ**はフェーズ成果物（調査レポート）へ — 詳細を探しに来る人向け。
- **D-08:** 修復の検証は **同一環境でフルスイートを複数回連続実行**し、クラッシュ 0・ERROR 0 を確認する。フレーキー症状なので 1 回グリーンは証拠にならない。**回数はプランで確定**する。別マシン / CI / 別ユーザーでの確認（PITFALLS のチェック項目）は、本プロジェクトに CI も別環境も存在しないため対象外とし、その旨を記録する。

### 保存トースト再試行の期待挙動（V190-QA-02）

- **D-09:** V190-QA-02 の意図は **「再試行時は確認をスキップする」**（IN-01 の Fix 提案どおり）。要件・ROADMAP の現行文言「上書き確認ダイアログが再表示される」は**現状を記述してしまった記述ミス**として扱う。現行コード（`file_ops.py` の `retry_cb` が `self._save_file` / `self._save_as` / `self._save_compressed` をそのまま指す）は既に再表示するため、文言どおりなら実装ゼロで満たせてしまう。一度確認済みのユーザーが一過性の I/O 失敗で再試行する際に毎回確認させるのは「再試行」という語の普通の意味に反する。
- **D-10:** スキップの対象は **保存 3 経路すべて**（`_save_file` の上書き確認 `askyesno` / `_save_as` の保存先ピッカー / `_save_compressed` の保存先ピッカー）。再試行時は前回確定した保存先・確認結果を使って黙って再試行する。トーストの「再試行」という UX を 3 経路で一貫させるため。
- **D-11:** 実現方式は **内部実行関数への分離**。各保存メソッドを「確認・パス選択層」と「実保存層（パスを引数に取る）」に分け、`retry_cb` は実保存層を確定済みパスで直接呼ぶ。IN-01 の Fix 提案そのものであり、実保存層は Tk 非依存になって回帰テストが書きやすい。フラグ引数追加案（メソッド内に分岐が残る）・ToastManager 側で状態保持案（通知コンポーネントが保存の文脈を知ることになり責務が滲む）は不採用。 — **Reversibility:** costly — 保存 3 経路すべての関数境界を切り直すため、戻すには 3 経路の再修正が必要。既存の `_overwrite_current_file` / `ToastManager` 連携もこの境界の上に載る。
- **D-12:** 文言の食い違いは **REQUIREMENTS.md の V190-QA-02 と ROADMAP.md の Success Criteria #2 の両方を訂正**する（「再試行時は上書き確認・保存先選択を再表示せず、前回確定した対象へ黙って再保存する」）。下流の検証エージェントは ROADMAP の Success Criteria を基準に合否を判定するため、訂正しないと実装と判定基準が正反対になる。

### human-verify / UAT の範囲と記録（V190-QA-03）

- **D-13:** 遡及 UAT は **「現行機能に今も未検証のまま生きている挙動」だけを対象**とする。遡及項目を現行コードと照合し、すでに別フェーズで作り直された項目・仕様が変わった項目を除外してからリストを確定する。v1.7.1 の V171-R-05（「活き残り」を確定してから対象化する）と同じやり方。対象候補は v1.6.0 Phase 4（V16-D-05・Markdown 整形表示 / 実 API 出力品質）、v1.7.1 Phase 4 の 7 件、v1.6.0 Phase 3（V16-QUAL-03）、v1.4.0 Phase 04（`human_needed` のまま）。
- **D-14:** 実 API・課金が必要な項目は **手元にキーがあるプロバイダの分だけ実施**し、キーがない / 課金が発生する項目は **「未実施・理由付き」として Deferred へ明示記録**する。リリース判定はブロックしない。全部実施を必須にすると v1.6.0 から続く未実施項目のコストがリリースを止めるため。
- **D-15:** 実施形式は **Phase 2 と同型のチェックリスト分割**（項目をグループ分けして複数の human-verify チェックポイントで実施）。結果は **専用成果物 `03-UAT-RESULTS.md`** に「項目・手順・合否・根拠」で記録し、遡及分と v1.9.0 分を一覧で追えるようにする。Phase 2 では実機 3 分割の human-verify を行って全合格しており、実績のある形式。

### リリース確定作業の範囲

- **D-16:** Phase 3 に含めるのは **`APP_VERSION` の v1.9.0 へのバンプ・`開発履歴.md` の v1.9.0 エントリ追記・README バッジ更新**まで（CLAUDE.md の「変更時のチェックリスト」項目）。Phase 1（01-05 / 01-07）と Phase 2 がこれらを明示的に Phase 3 へ委譲しているため、ここが引受け手になる。**PyInstaller リビルド・注釈付きタグ・GitHub Release 公開は含めない** — 過去マイルストーン（260709-rel / 260722-rel）と同様にマイルストーンクローズ後のクイックタスクで実施する。

### Claude's Discretion

- 調査プランと実装プランの分割粒度（調査 → 修復 → QA-02 → UAT の 4 プランか、調査と修復を 1 プランに束ねるか）
- D-08 の「複数回連続実行」の具体的な回数（フレーキーの再現率 7/10 という既知値から統計的に妥当な回数を選ぶ）
- 二分探索（D-03 ②）の刻み方と、再現判定に使う試行回数
- 実保存層（D-11）の関数名・シグネチャ・配置（`file_ops.py` 内に閉じるか別ヘルパーへ出すか）
- `03-UAT-RESULTS.md` の具体的な表構成と、human-verify チェックポイントのグループ分け
- CLAUDE.md へ追記する実行手順の記述位置と粒度（「変更時のチェックリスト」直下か独立セクションか）
- 調査レポートのファイル名（`03-TEST-ENV-INVESTIGATION.md` 等）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・スコープの一次情報
- `.planning/REQUIREMENTS.md` — V190-* 全 27 要件。Phase 3 は QA-01/02/03 の 3 件（59-61 行目）。**V190-QA-02 の文言は D-12 で訂正対象**
- `.planning/ROADMAP.md` §「Phase 3: 品質保証・リリースゲート」— Goal と 3 つの Success Criteria。**#2 は D-12 で訂正対象**
- `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md` §195 行目付近 — 24 件の GUI テストセットアップエラーの初出（対象はバッチOCR・OCRダイアログ配置・プラグインダイアログ・ショートカットダイアログ・トーストの GUI テスト）

### 未解決症状の一次情報（**最重要 — ここに既存の切り分け結果がすべてある**）
- `.planning/STATE.md` §「Blockers/Concerns」— 2 系統の症状の詳細。①v1.8.0 リリース作業で発見された `TclError` フレーキー（毎回異なる 2 件・単体実行では常に合格）、②01-07 実行時にオーケストレーターが A/B 検証で特定した `STATUS_BREAKPOINT` クラッシュ（**製品コード無実・`--deselect` で再現・`--ignore` で非再現＝import 時点で成立・モジュールサイズ模倣では非再現・孤児 daemon スレッド仮説は棄却済み・当面の運用は分割実行で 1167 + 17 = 1184 全件 green**）。**D-01〜D-04 はすべてこの記述を前提にしている。プラン作成前に必読**
- `.planning/research/PITFALLS.md` §Pitfall 13（506-547 行）— Tkinter 環境修復が「テスト環境だけ」の問題ではない理由。`TCL_LIBRARY` のハードコードが配布 EXE を壊す機序（D-05 の根拠）。§610 行・§637 行のチェック項目
- `.planning/research/STACK.md` §「Python 3.14.6 / Tkinter」行 — 本リサーチでは実機再現せず。CPython #125235（venv 相対パス誤解決・3.13 系は修正済み / 3.14 系は未確認）が有力候補。別途検出された `PermissionError`（pytest 一時ディレクトリ `%TEMP%\pytest-of-shdwf` のロック競合・Windows Defender 疑い）は init.tcl とは無関係
- `.planning/research/SUMMARY.md` §「環境修復」/ §Gaps — STACK と PITFALLS で評価が食い違っている旨（この食い違いの解消が Phase 3 の仕事）

### V190-QA-02 の出典
- `.planning/milestones/v1.8.0-phases/06-ux-ui/06-REVIEW.md` §IN-01（176-187 行）— **Fix 提案が「確認をスキップする低レベル再試行入口」であることの根拠**。要件文言との食い違い（D-09/D-12）はここで確認できる
- `.planning/milestones/v1.8.0-phases/06-ux-ui/06-VERIFICATION.md:116` — IN-01 が future polish として意図的にスコープ外とされた経緯

### 前フェーズの決定（引き継ぎ）
- `.planning/phases/01-safety-rollback/01-CONTEXT.md` — Phase 1 の D-01〜D-19。特に §D-13（Undo 復元失敗は messagebox でブロック通知）は UAT 対象
- `.planning/phases/02-ocr-openai-chatgpt/02-CONTEXT.md` — Phase 2 の D-01〜D-18。OpenAI 関連の UAT 項目はここの決定と照合する
- `.planning/PROJECT.md` §「Key Decisions」— V14-D-01（新規 pip 依存ゼロ・**調査で pytest プラグインを足したくなったときの制約**）、V16-D-05（human-verify スキップ・⚠️ Revisit）、V180-D-17

### アーキテクチャ制約・作法
- `CLAUDE.md` §「変更時のチェックリスト」— ruff / 構文確認 / pytest / 開発履歴.md / **バージョン番号更新（`pagefolio/constants.py` の `APP_VERSION`・開発履歴.md・README バッジ）**。D-07 の追記先・D-16 の作業対象
- `CLAUDE.md` §「言語ルール」— コミットメッセージ・UAT 記録・申し送りはすべて日本語
- `.claude/skills/session-handoff/SKILL.md` — セッション終了時の申し送り書式
- `.planning/codebase/TESTING.md` — pytest の実行コマンド・fixture 構成・テストの書き方（**件数記載は 1109 件で古い。実測 1387 件**）
- `.planning/codebase/CONCERNS.md` — Fragile Areas

### 実装対象コード
- `pagefolio/file_ops.py:1147-1171`（`_save_file`・`askyesno` 上書き確認 → incremental save → 失敗時 `_overwrite_current_file` フォールバック → `_show_error_or_toast(..., self._save_file)`）
- `pagefolio/file_ops.py:1173-1194`（`_save_as`・`asksaveasfilename` → `doc.save(path, encryption=PDF_ENCRYPT_KEEP)` → `_show_error_or_toast(..., self._save_as)`）
- `pagefolio/file_ops.py:1240-1261`（`_save_compressed`・`_is_current_file` 分岐 → `_show_error_or_toast(..., self._save_compressed)`）
- `pagefolio/ui_builder.py:189-198`（`_show_error_or_toast` — `retry_cb` を ToastManager へ渡す共通入口）
- `pagefolio/toast.py:40-84`（`ToastManager.show` / `_build_frame` — `retry_cb` の差し替え WR-03 対応済み）
- `pagefolio/constants.py` — `APP_VERSION`（D-16）
- `tests/conftest.py` — fixture の集約先（D-06 で修復を入れるならここが第一候補）
- `tests/test_pdf_ops.py` — **STATUS_BREAKPOINT の引き金（01-07 版）。D-03 ② の二分探索対象**
- `tests/test_ocr_pipeline.py` — クラッシュが顕在化する場所（`TestPipelineHardening::test_cancel_finite_time_no_deadlock` 実行中）
- `開発履歴.md` / `README.md` — D-16 の更新対象

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_overwrite_current_file(path, **save_kwargs)`（`file_ops.py`）: 「メモリへシリアライズ → close → tmp 経由 `os.replace` → 開き直し、失敗時は bytes から復元して再送出」というロールバック済みの実装。**すでに「パスを引数に取る実保存層」の形をしている**ため、D-11 の分離はこの形に他の 2 経路を揃える作業になる
- `ToastManager.show(category, message, retry_cb)`（`toast.py`）: category 単位で再試行コールバックを差し替える実装（WR-03 対応済み）。D-11 で `retry_cb` の中身が変わるだけで、ToastManager 自体は無改造でよい
- `_show_error_or_toast(category, title, msg, retry_cb)`（`ui_builder.py`）: トースト非対応時に messagebox へフォールバックする共通入口（v1.8.0 レビュー R2 で共通化済み）。保存 3 経路すべてがここを通るので、D-10 の一貫性を保つのに都合がよい
- `tests/conftest.py` の fixture 群（`sample_pdf` / `sample_pdf_doc` / `large_pdf_doc` / `multi_pdf_files` / `tmp_settings`）: UAT 用の再現手順を自動テスト側で補強するときに流用できる
- Phase 2 の human-verify 3 分割の実施記録: D-15 のチェックポイント設計の雛形

### Established Patterns
- **`pytest` は `.venv` 経由で実行**（`./.venv/Scripts/python.exe -m pytest`）。テスト収集は現在 **1387 件**（0.37 秒で collect 成功）
- **新規 pip 依存ゼロ（V14-D-01）**: 調査で `pytest-forked` / `pytest-xdist` 等を入れたくなっても、これは PROJECT.md の確定方針に抵触する。導入するなら明示的な決定として上げること
- **A/B 検証で原因を切り分ける**（01-07 の実績）: 「製品コードを HEAD にしてテストだけ戻す」形で製品コード無実を証明した手法。D-03 の二分探索も同じ流儀
- **i18n は `pagefolio/lang.py` に ja/en ペアで追加**（未使用キー回帰テストが常設・V171-D-11）。D-11 で新規文言が必要になった場合に適用
- **バージョン更新はマイルストーンクローズ時に検出されがち**（v1.8.0 で `v1.7.4 → v1.8.0` の漏れを検出）。D-16 で Phase 3 が引き受けることでこの再発を防ぐ

### Integration Points
- `file_ops.py` の保存 3 経路 ↔ `ui_builder.py:_show_error_or_toast` ↔ `toast.py:ToastManager`: D-11 の分離はこの 3 層の境界に閉じる
- `tests/test_pdf_ops.py` の import ↔ `tests/test_ocr_pipeline.py` の実行: **クラッシュはこの 2 ファイルの共存で成立する**（片方だけなら再現しない）。D-03 の切り分けはこの関係を軸にする
- `pagefolio/constants.py:APP_VERSION` ↔ `README.md` のバッジ ↔ `開発履歴.md` の最新エントリ: CLAUDE.md が「APP_VERSION を真の情報源とし 3 者を同期させる」と規定（D-16）

</code_context>

<specifics>
## Specific Ideas

- **「調べる前に直さない」** が本フェーズを貫く判断基準として選ばれた。D-05（切り分け結果駆動）・D-06（tests/ に閉じる）・D-03（既知の切り分け結果の続きから入る）はいずれも「症状に対して予防的にコードを足す」ことを退けている。PITFALLS §13 が警告する「動いたように見えて根本原因に触れていない」状態を避けるため
- **「打ち切り基準を先に決める」** という設計が明示的に採られた（D-02 の仮説 2 本）。原因未解明のネイティブ層問題に対して、追求の終わりをあらかじめ契約化することでフェーズがスタックするのを防ぐ。ただし**反証データを残す**ことが条件で、次マイルストーンが同じ地面を掛け直さないようにする
- **要件文言そのものを疑う判断**が行われた（D-09/D-12）。V190-QA-02 は現状を記述してしまっており、文言どおりの実装は「何もしない」に帰着する。文書を直してから実装するという順序が選ばれた
- **リリース作業の線引きは過去の運用を踏襲**（D-16）。バージョン・ドキュメントの整合は GSD フェーズ内、ビルド・タグ・Release はクイックタスク側という v1.6.1 以降の実績どおりの分担
- **CI が存在しないという事実を明示的に受け入れた**（D-08）。PITFALLS のチェック項目「クリーンな別環境でも再現しないことを確認」は本プロジェクトでは実行不能なので、同一環境での複数回実行に置き換え、その旨を記録する

</specifics>

<deferred>
## Deferred Ideas

- **`pytest` 一時ディレクトリの `PermissionError`（`%TEMP%\pytest-of-shdwf` へのアクセス拒否・32 件エラー）** — STACK リサーチが init.tcl 問題とは別に検出した環境要因（Windows Defender 等のロック競合が疑わしい）。`--basetemp=<短パス>` 指定で回避できることが判明している（Phase 2 の実測ベースラインもこの指定つき）。本フェーズの調査中に併発したら運用回避（`--basetemp`）で通し、根本対応は対象外
- **CI 環境の導入** — 「クリーンな別環境で再現しないことを確認する」（PITFALLS のチェック項目）を実行するには CI が必要だが、本プロジェクトには存在しない。導入は新しい能力の追加であり別マイルストーンの判断
- **`pytest-forked` / `pytest-xdist` によるプロセス分離** — クラッシュを構造的に回避できる可能性があるが、新規 pip 依存ゼロ方針（V14-D-01）に抵触する。分割実行（D-01）で当面をしのぐ
- **単一プロセス完走の達成** — D-01 で分割実行を受容した場合、単一プロセスでの完走は未達のまま残る。根本原因の反証データとともに次マイルストーン候補として記録する
- **実 API・課金が必要な UAT 項目**（D-14 で未実施となった分） — V16-QUAL-03（max_tokens クランプ / 429 リトライの実機検証・v1.6.0 から継続）、新世代 Gemini の thinking 有効時の応答時間・トークン消費実測（260722-gae 精査項目 3 ③）。理由付きで Deferred へ記録し、次に実キーが用意できる機会に消化する
- **LLM 設定ダイアログへの「新世代 Gemini では temperature 欄が無視される」注記**（260722-gae 精査項目 3 ②・UI 変更） — Phase 2 で OpenAI の同型パターン（o-series の temperature 拒否）と合流可能か検討する予定だったが Phase 2 では合流しなかった。UI 変更は本フェーズの範囲外

</deferred>

---

*Phase: 3-品質保証・リリースゲート*
*Context gathered: 2026-08-11*
