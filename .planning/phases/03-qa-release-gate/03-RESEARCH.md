# Phase 3: 品質保証・リリースゲート - Research

**Researched:** 2026-08-11
**Domain:** pytest/Tkinter 実行環境の切り分け・保存トースト再試行の内部構造リファクタ・遡及 human-verify/UAT の棚卸しと記録・リリース版数文書の整合
**Confidence:** HIGH（本セッションで実機コマンド実行・実コード読解により大半の主張を直接検証済み。ネイティブ層の根本原因のみ LOW〜MEDIUM）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**全テスト完走ゲートの合格条件（V190-QA-01）**
- **D-01:** 「全テスト完走」は **まずタイムボックス付きで根本原因を追い、解消できなければ「定義された分割実行手順で全 1387 件グリーン」を合格とする**。単一プロセス `pytest -q` 一発グリーンを必達にはしない。STATUS_BREAKPOINT クラッシュは**製品コード無実が A/B 検証済み**（STATE.md「Blockers/Concerns」・HEAD 内容 4/4 green・基準内容は累計19回中0クラッシュ）であり、原因未解明のネイティブ層調査で出荷判定をブロックさせないため。ただし分割の**根拠と手順は必ず文書化**する。
- **D-02:** 根本原因追求は **「仮説 2 本を検証したら打ち切り」** を契約とする。2 本とも外れたら分割実行へ確定させる。検証した仮説と**反証データを成果物に残し**、次マイルストーンで同じ地面を掛け直さないようにする。
- **D-03:** STATUS_BREAKPOINT クラッシュで検証する 2 仮説は以下に固定する。1) pytest assertion rewriting 仮説（`--assert=plain` / `-p no:cacheprovider` で再現するか）。2) 二分探索（`tests/test_pdf_ops.py`（01-07 版）の内容を二分探索し、引き金となる最小コード片を特定する）。`_drive_pipeline` の孤児 daemon スレッド仮説は**既に棄却・revert 済み**（再検証しない）。
- **D-04:** もう 1 つの症状（`TclError` によるセットアップ ERROR・毎回異なる 2 件のフレーキー）は **同じ調査プランで並行して切り分ける**が、**別症状として別々に結論を記録**する。

**環境修復の手段と置き場（V190-QA-01）**
- **D-05:** 修復は **切り分け結果駆動**とする。先に実機で再現条件を特定し、その原因に対応する修復だけを入れる。再現しなければ**コード変更ゼロ**で「現行環境では解消済み」と根拠付きで記録して閉じる。予防的な `TCL_LIBRARY`/`TK_LIBRARY` ハードコードは入れない。
- **D-06:** 修復のコード変更は **`tests/` 配下に閉じることを原則**とする。製品コード（`pagefolio/`）への変更が必要と判断された場合は、**先に根拠を提示して判断を仰ぐ**。
- **D-07:** 記録先を 2 系統に分ける。**日常の実行手順**（分割コマンド・リリースゲートの合格条件）は `CLAUDE.md` の「変更時のチェックリスト」へ。**切り分けの実験ログと反証データ**はフェーズ成果物（調査レポート）へ。
- **D-08:** 修復の検証は **同一環境でフルスイートを複数回連続実行**し、クラッシュ 0・ERROR 0 を確認する（回数はプランで確定）。別マシン / CI / 別ユーザーでの確認は本プロジェクトに存在しないため対象外とし、その旨を記録する。

**保存トースト再試行の期待挙動（V190-QA-02）**
- **D-09:** V190-QA-02 の意図は **「再試行時は確認をスキップする」**（IN-01 の Fix 提案どおり）。要件・ROADMAP の現行文言「上書き確認ダイアログが再表示される」は**現状を記述してしまった記述ミス**として扱う。
- **D-10:** スキップの対象は **保存 3 経路すべて**（`_save_file` の上書き確認 `askyesno` / `_save_as` の保存先ピッカー / `_save_compressed` の保存先ピッカー）。再試行時は前回確定した保存先・確認結果を使って黙って再試行する。
- **D-11:** 実現方式は **内部実行関数への分離**。各保存メソッドを「確認・パス選択層」と「実保存層（パスを引数に取る）」に分け、`retry_cb` は実保存層を確定済みパスで直接呼ぶ。フラグ引数追加案・ToastManager 側で状態保持案は不採用。 — **Reversibility:** costly（保存 3 経路すべての関数境界を切り直すため、戻すには 3 経路の再修正が必要）。
- **D-12:** 文言の食い違いは **REQUIREMENTS.md の V190-QA-02 と ROADMAP.md の Success Criteria #2 の両方を訂正**する（「再試行時は上書き確認・保存先選択を再表示せず、前回確定した対象へ黙って再保存する」）。

**human-verify / UAT の範囲と記録（V190-QA-03）**
- **D-13:** 遡及 UAT は **「現行機能に今も未検証のまま生きている挙動」だけを対象**とする。遡及項目を現行コードと照合し、すでに別フェーズで作り直された項目・仕様が変わった項目を除外してからリストを確定する。対象候補は v1.6.0 Phase 4（V16-D-05・Markdown 整形表示 / 実 API 出力品質）、v1.7.1 Phase 4 の 7 件、v1.6.0 Phase 3（V16-QUAL-03）、v1.4.0 Phase 04（`human_needed` のまま）。
- **D-14:** 実 API・課金が必要な項目は **手元にキーがあるプロバイダの分だけ実施**し、キーがない / 課金が発生する項目は **「未実施・理由付き」として Deferred へ明示記録**する。リリース判定はブロックしない。
- **D-15:** 実施形式は **Phase 2 と同型のチェックリスト分割**（項目をグループ分けして複数の human-verify チェックポイントで実施）。結果は **専用成果物 `03-UAT-RESULTS.md`** に「項目・手順・合否・根拠」で記録する。

**リリース確定作業の範囲**
- **D-16:** Phase 3 に含めるのは **`APP_VERSION` の v1.9.0 へのバンプ・`開発履歴.md` の v1.9.0 エントリ追記・README バッジ更新**まで。**PyInstaller リビルド・注釈付きタグ・GitHub Release 公開は含めない**（マイルストーンクローズ後のクイックタスクで実施）。

### Claude's Discretion

- 調査プランと実装プランの分割粒度（調査 → 修復 → QA-02 → UAT の 4 プランか、調査と修復を 1 プランに束ねるか）
- D-08 の「複数回連続実行」の具体的な回数（フレーキーの再現率 7/10 という既知値から統計的に妥当な回数を選ぶ）
- 二分探索（D-03 ②）の刻み方と、再現判定に使う試行回数
- 実保存層（D-11）の関数名・シグネチャ・配置（`file_ops.py` 内に閉じるか別ヘルパーへ出すか）
- `03-UAT-RESULTS.md` の具体的な表構成と、human-verify チェックポイントのグループ分け
- CLAUDE.md へ追記する実行手順の記述位置と粒度（「変更時のチェックリスト」直下か独立セクションか）
- 調査レポートのファイル名（`03-TEST-ENV-INVESTIGATION.md` 等）

### Deferred Ideas (OUT OF SCOPE)

- `pytest` 一時ディレクトリの `PermissionError`（`%TEMP%\pytest-of-shdwf` へのアクセス拒否・32 件エラー）— `--basetemp=<短パス>` 指定で回避できることが判明している。本フェーズの調査中に併発したら運用回避で通し、根本対応は対象外
- CI 環境の導入 — 本プロジェクトには存在しない。導入は新しい能力の追加であり別マイルストーンの判断
- `pytest-forked` / `pytest-xdist` によるプロセス分離 — 新規 pip 依存ゼロ方針（V14-D-01）に抵触。分割実行（D-01）で当面をしのぐ
- 単一プロセス完走の達成 — D-01 で分割実行を受容した場合、単一プロセスでの完走は未達のまま残る。反証データとともに次マイルストーン候補として記録する
- 実 API・課金が必要な UAT 項目（D-14 で未実施となった分）— V16-QUAL-03（max_tokens クランプ / 429 リトライの実機検証・v1.6.0 から継続）、新世代 Gemini の thinking 有効時の応答時間・トークン消費実測。理由付きで Deferred へ記録
- LLM 設定ダイアログへの「新世代 Gemini では temperature 欄が無視される」注記（UI 変更）— Phase 2 では合流せず。本フェーズの範囲外
- PyInstaller リビルド・注釈付きタグ付与・GitHub Release 公開（マイルストーンクローズ後のクイックタスク）
- Phase 1/2 で実装済みの機能そのものの変更（回帰が見つかった場合を除く）
- Undo 記録先置き op への水平展開（Phase 1 D-12・次マイルストーン候補）
- `OCR_PRICE_TABLE` 一元化・プラグイン catalog 登録 API（Phase 2 Deferred）
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V190-QA-01 | Tkinter 実行環境の問題（Python 3.14.6 での GUI テストのセットアップエラー）を切り分け・修復し、GUI テストを含む全テストが完走する。完走をリリースゲート条件とする | Standard Stack（環境バージョン実測）、Common Pitfalls Pitfall 1・4、Code Examples の再現試行データ（7/7 grün）、Validation Architecture の分割実行コマンド更新（1370+17=1387） |
| V190-QA-02 | 保存トーストの再試行を実行した際、上書き確認ダイアログを再表示せず前回確定した対象へ黙って再保存する（D-09/D-12 により文言訂正済み） | Architecture Patterns Pattern 1・2、Code Examples（現行3経路全文）、Common Pitfalls Pitfall 2・3（既存テスト3件・文言訂正2箇所） |
| V190-QA-03 | 実機目視による human-verify / UAT を正式に実施し、結果を記録する（v1.4.0/v1.6.0/v1.7.1 で一旦 pass とした項目の正式消化を含む） | Common Pitfalls Pitfall 5（現行照合結果）、Environment Availability（実 API キー availability）、Open Questions #3 |
</phase_requirements>

## Summary

Phase 3 は新機能を作らない「締めのフェーズ」であり、3 本の異なる性質の作業から成る。(1) V190-QA-01: Python 3.14.6 環境で単一プロセス `pytest -q` を実行すると発生していた STATUS_BREAKPOINT クラッシュと `TclError` フレーキーの切り分け・修復（タイムボックス付き仮説検証 → 分割実行の受容）。(2) V190-QA-02: 保存トーストの「再試行」ボタンが確認ダイアログ/保存先ピッカーを毎回再表示してしまう現状を、内部実行関数への分離（確認・パス選択層 と 実保存層 の分離）で解消する小さなリファクタ。(3) V190-QA-03: v1.4.0/v1.6.0/v1.7.1 で「一旦 pass」としてきた遡及 human-verify 項目のうち今も現行コードに生きているものを消化し、`03-UAT-RESULTS.md` へ記録する。

本セッションで最も重要な発見は、**V190-QA-01 の前提条件そのものが変化していること**である。STATE.md が記録する「HEAD 内容で約10回中7回クラッシュ」という repro rate は 01-07 実行時点（Phase 1 途中）のものだが、本セッションで現在の HEAD（Phase 1・Phase 2 完了後・1387 件収集・`tests/test_pdf_ops.py` は 01-07 版のまま無変更）に対して単一プロセス `pytest -q` を **7 回連続実行した結果は 7/7 grün（クラッシュ 0・TclError 0）** だった。これは D-05（切り分け結果駆動・再現しなければコード変更ゼロで解消済みと記録して閉じる）に直結する一次データであり、Phase 3 の Task 0 は「まず現行 HEAD で再現を試みる」ことから始めるべきで、二値仮説（D-03）の検証はそこで実際に再現した場合にのみ着手するのが筋である。

保存トーストの再試行（V190-QA-02）は、`_overwrite_current_file(path, **save_kwargs)`（`file_ops.py:1102`）がすでに「パスを引数に取る実保存層」の形をしており、これに `_save_file`/`_save_as`/`_save_compressed` を揃える作業として位置づけられる。既存のトースト配線テスト（`tests/test_toast.py`）は現状の `retry_cb == app._save_file`（そのまま元メソッドを指す）という契約を直接アサートしており、D-11 実装時にこれら3箇所のテストが意図的に破壊され、書き換えが必要になることが本セッションで確認できた。

**Primary recommendation:** Task 0 を「現行 HEAD での再現試行（複数回連続実行）」から始め、再現有無で D-02/D-03（仮説2本）へ進むか D-05（解消済み記録）で閉じるかを分岐させる。V190-QA-02 は `_overwrite_current_file` と同型の「path 引数を取る実保存層」を3経路に展開し、`tests/test_toast.py` の3件の既存アサーションを更新する。V190-QA-03 は D-13 の「現行照合で活き残りを確定」を実際にコードで裏付けてから対象化する（本リサーチで一次候補は現行コードに存在確認済み）。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| pytest 実行環境の切り分け・修復（V190-QA-01） | テストインフラ（`tests/conftest.py`） | — | D-06 により製品コード（`pagefolio/`）への変更は原則対象外。Tcl/Tk・pytest プロセス自体の環境問題であり UI/API 層の責務ではない |
| 保存トースト再試行の内部実行関数分離（V190-QA-02） | Backend（`pagefolio/file_ops.py` の Mixin メソッド） | UI（`ui_builder.py`/`toast.py` は無改造） | 保存の「確認・パス選択」と「実処理」は同一 Mixin 内の責務分離であり、ToastManager 自体は `retry_cb` を差し替えるだけの受け皿（D-11 で ToastManager 側に状態保持案は不採用） |
| human-verify/UAT の実施・記録（V190-QA-03） | ドキュメント/プロセス（`03-UAT-RESULTS.md`） | UI（実機目視対象は Tkinter 各ダイアログ） | 記録責務はフェーズ成果物、確認対象はこれまでの各フェーズが実装した UI/API 層そのもの（新規実装なし） |
| リリース版数文書の同期（D-16） | ドキュメント（`constants.py`/`README.md`/`開発履歴.md`） | — | `APP_VERSION` を単一情報源として3ファイルを同期する既存の確立された作法（CLAUDE.md） |

## Standard Stack

新規ライブラリ追加は**行わない**（V14-D-01: 新規 pip 依存ゼロを維持）。本フェーズは既存スタックの環境修復・内部リファクタ・ドキュメント整合のみで完結する。

### Core（変更なし・確認のみ）

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.1.1 | テストランナー | requirements.txt 固定・`.venv` に実インストール済みで一致確認済み [VERIFIED: `./.venv/Scripts/python.exe -m pytest --version` 相当 `-c "import pytest; print(pytest.__version__)"` 実行結果 `9.1.1`（本セッション実行）] |
| PyMuPDF (fitz) | 1.28.0（MuPDF 1.29.0 同梱） | PDF 操作 | requirements.txt 固定・実インストール一致確認済み [VERIFIED: 本セッション `fitz.version` 実行結果 `('1.28.0', '1.29.0', None)`] |
| Python | 3.14.6 | ランタイム | [VERIFIED: 本セッション `./.venv/Scripts/python.exe --version` 実行結果 `Python 3.14.6`] |
| Tcl/Tk | 8.6.15 | GUI | [VERIFIED: 本セッション `tkinter.Tk().tk.call('info','patchlevel')` 実行結果 `8.6.15`。単体 `tkinter.Tk()` 生成は成功しクラッシュせず] |

### Supporting

なし（本フェーズはコード追加が最小で、既存 `tests/conftest.py` の fixture 拡張と `file_ops.py` の内部関数分離のみ）。

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 単一プロセス `pytest -q` の完走 | `pytest-forked`/`pytest-xdist` によるプロセス分離 | クラッシュを構造的に回避できるが V14-D-01（新規 pip 依存ゼロ）に抵触。CONTEXT.md D-14 相当で Deferred 済み（03-CONTEXT.md `Deferred Ideas`） |
| conftest.py での `TCL_LIBRARY`/`TK_LIBRARY` 明示設定 | 何もしない（現状の探索ロジックのまま） | PITFALLS.md Pitfall 13 が「開発環境のテストは直るが配布 EXE の Tcl/Tk 探索ロジックと衝突する」と明記。D-05 で不採用が既に確定 |

**Installation:** 不要（新規パッケージなし）。

**Version verification:** 上記 Core 表はすべて本セッションで `.venv` 実行により再確認済み（[VERIFIED]）。

## Package Legitimacy Audit

**該当なし。** 本フェーズは新規外部パッケージのインストールを一切行わない（V14-D-01 継続）。Package Legitimacy Gate の実行は不要。

## Architecture Patterns

### System Architecture Diagram（V190-QA-02: 保存トースト再試行フロー）

```
[ユーザー: 保存操作]
        │
        ▼
┌───────────────────────────┐
│ 確認・パス選択層            │  例: _save_file() の askyesno
│ （初回のみ実行される）        │       _save_as()/_save_compressed() の asksaveasfilename
└──────────┬─────────────────┘
           │ 確定パス + save_kwargs
           ▼
┌───────────────────────────┐
│ 実保存層 _do_save_*(path)  │──成功──▶ _set_status / toast.dismiss(category)
│ （path 引数を取る・Tk非依存）│
└──────────┬─────────────────┘
           │ 失敗（Exception）
           ▼
┌───────────────────────────┐
│ _show_error_or_toast(      │
│   category, title, msg,    │
│   retry_cb=_do_save_*(path)) │← retry_cb は「実保存層」を直接指す
└──────────┬─────────────────┘
           │
           ▼
┌───────────────────────────┐
│ ToastManager.show()        │
│ 「再試行」ボタン押下          │──▶ retry_cb() を直接呼ぶ
│                             │     （確認ダイアログ/ピッカーを経由しない）
└───────────────────────────┘
```

現状（修正前）は `retry_cb` が確認・パス選択層を含む元メソッド全体（`self._save_file` 等）を指しているため、再試行のたびに `askyesno`/`asksaveasfilename` が再度開く。D-11 の修正はこの図の「実保存層」を独立関数として切り出し、`retry_cb` の指し先をそちらへ変更するだけで完結する。

### Recommended Project Structure

新規ファイルは作らない。既存構造のまま:
```
pagefolio/
├── file_ops.py          # _save_file/_save_as/_save_compressed を確認層+実保存層へ分離（D-11）
├── ui_builder.py         # _show_error_or_toast は無改造
└── toast.py              # ToastManager は無改造（D-11で状態保持案は不採用）
tests/
├── conftest.py           # V190-QA-01 修復コードの置き場（D-06・再現時のみ）
└── test_toast.py         # 既存3アサーション（後述）の更新が必要
```

### Pattern 1: 実保存層の分離（`_overwrite_current_file` 型を横展開）

**What:** 保存メソッドを「確認・パス選択」と「path を引数に取る実処理」へ分離し、`retry_cb` は実処理側を直接指す。
**When to use:** 「初回は確認するが再試行時は確認をスキップする」という UX 契約を実装するとき全般。
**Example（既存コード・そのまま実在する参照実装）:**
```python
# Source: pagefolio/file_ops.py:1102-1132（本セッションで直接読解・確認済み）
def _overwrite_current_file(self, path, **save_kwargs):
    """開いている元ファイル自身へ上書き保存する。

    ...
    encryption 未指定時は PDF_ENCRYPT_KEEP へ既定化する（D-02）。呼び出し側の
    明示指定（_do_set_password の AES_256 / _remove_password の NONE 等）は
    setdefault のため上書きされない。
    """
    save_kwargs.setdefault("encryption", fitz.PDF_ENCRYPT_KEEP)
    current_has_password = getattr(self, "pdf_has_password", False)
    data = self.doc.tobytes(**save_kwargs)
    self.doc.close()
    try:
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        self.doc = fitz.open(path)
        self.pdf_has_password = derive_pdf_has_password(
            current_has_password, save_kwargs["encryption"]
        )
    except Exception:
        self.doc = fitz.open(stream=data, filetype="pdf")
        raise
```
これは「path を引数に取り、確認ダイアログを一切含まない」実処理層の実例そのものであり、D-11 で `_save_file`/`_save_as`/`_save_compressed` に同型の分離を横展開すればよい。命名は Claude's Discretion（CONTEXT.md）だが、既存の `_overwrite_current_file` との一貫性を考えると `_do_save_file(path)`/`_do_save_as(path)`/`_do_save_compressed(path, save_kwargs)` のような対応が自然。

### Pattern 2: STATUS_BREAKPOINT クラッシュの仮説検証コマンド（D-03）

**What:** D-03 で確定した2仮説の具体的な検証コマンド。
**When to use:** Task 0 で現行 HEAD の再現を試みて実際にクラッシュ/ERROR が再現した場合のみ。
```bash
# 仮説1: pytest assertion rewriting（1コマンドで白黒がつく）
./.venv/Scripts/python.exe -m pytest -q --assert=plain -p no:cacheprovider --basetemp=<短パス>

# 仮説2: 二分探索（tests/test_pdf_ops.py の内容を半分にコメントアウト/削除して再実行を繰り返す）
# 既知の絞り込み: モジュールサイズ模倣・import ast/pathlib の追加のみでは非再現
# → クラス単位（TestPdfOpen/TestPageRotate/... 等）で半分ずつ --deselect し
#   どちらの半分が引き金かを特定していく
```
**Note:** 本セッションでは Task 0 相当の再現試行（7回連続実行）を実施したが 7/7 grün であり、上記コマンドの実行自体には至らなかった（後述 Common Pitfalls / Assumptions Log 参照）。

### Anti-Patterns to Avoid

- **`TCL_LIBRARY`/`TK_LIBRARY` の予防的ハードコード:** D-05 で明示的に不採用。PITFALLS.md Pitfall 13 が配布 EXE の探索ロジックとの衝突を警告している。再現していない問題への予防的コード変更は行わない
- **`retry_cb` にフラグ引数を追加する案:** D-11 で明示的に不採用（メソッド内に分岐が残り、確認・パス選択層と実保存層が引き続き同一関数内に混在する）
- **ToastManager 側での確認済みフラグ/パス保持:** D-11 で明示的に不採用（通知コンポーネントが保存の文脈を知ることになり責務が滲む）

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 複数回実行でのフレーキー検出 | 独自の「N回実行して集計するスクリプト」を新規に書く | シェルの `for` ループで既存 `pytest -q` を素直に複数回呼ぶ（本セッションで実施した方式） | D-08 は「回数はプランで確定」のみを要求しており、専用ツールを作る必要はない。過剰実装を避ける |
| プロセス分離によるクラッシュ回避 | 自前のサブプロセス起動ラッパー | `pytest-forked`/`pytest-xdist`（ただし V14-D-01 により本フェーズでは不採用・Deferred） | 新規 pip 依存ゼロ方針に抵触するため、そもそも「作らない」が正しい判断（分割実行で当面をしのぐ） |
| 保存の「確認済みなら再確認しない」状態管理 | 独自の状態機械やセッションタイムアウト付きフラグ | 単純な「path 引数を持つ関数の直接呼び出し」（Pattern 1） | 過剰設計を避ける。既存の `_overwrite_current_file` パターンで十分要件を満たす |

**Key insight:** 本フェーズの3項目はいずれも「既存の確立されたパターンをそのまま横展開する」性質のタスクであり、新規の抽象化やライブラリ導入を必要としない。

## Common Pitfalls

### Pitfall 1: 「フェーズ発足時の repro rate」を検証せずに仮説検証へ直行する

**What goes wrong:** STATE.md に記録された「HEAD 内容で約10回中7回クラッシュ」を鵜呑みにして D-02/D-03 の仮説検証（`--assert=plain` 実行・二分探索）へ直行すると、そもそも現在のコードベースでは再現しない現象を追いかけて時間を浪費するリスクがある。
**Why it happens:** repro rate は 01-07 実行時点（Phase 1 途中、テスト数 1184 件）のものであり、Phase 1 完了（01-06/01-07 の gap closure）・Phase 2 全体（catalog.py 新設・OpenAI プロバイダ追加・関連テスト約200件追加）を経て現在は 1387 件に増えている。テスト収集順序・メモリ確保パターンが変わりうる。
**How to avoid:** Task 0 で必ず現行 HEAD に対する再現試行を行い（複数回連続実行）、実際に再現するかどうかを最初に確認してから D-02/D-03 へ進むかを判断する。
**Warning signs:** 本セッションで実施した検証データ:
- `./.venv/Scripts/python.exe -m pytest -q --basetemp=<短パス>` を **7 回連続実行 → 7/7 全件 grün（1387 passed、クラッシュ 0、TclError 系 ERROR 0）** [VERIFIED: 本セッションで実行・出力確認済み]
- `tests/test_pdf_ops.py` は STATE.md が言及する「01-07 版」のまま最終更新（コミット `1b0d28f fix(01-07): insert（base op）の削除ループへ部分適用保護を展開（WR-05）`）から無変更 [VERIFIED: `git log --oneline -- tests/test_pdf_ops.py` の先頭コミット]
- インストール済み依存バージョンは `requirements.txt` の固定値と完全一致（PyMuPDF 1.28.0 / pytest 9.1.1 / Python 3.14.6）— 依存バージョンのドリフトが非再現の原因ではない [VERIFIED]
- 分割実行の内訳も更新が必要: STATE.md の「1167 + 17 = 1184」は現在「**1370 + 17 = 1387**」に変わっている（`--ignore=tests/test_ocr_pipeline.py` で1370件・`tests/test_ocr_pipeline.py` 単独で17件、本セッションで `--collect-only` 実行し確認済み）[VERIFIED]

### Pitfall 2: D-11 のリファクタで既存の回帰テスト3件を見落とす

**What goes wrong:** `_save_file`/`_save_as`/`_save_compressed` の内部分離を実装しても、`tests/test_toast.py` に既にある「`retry_cb` は元メソッドそのものを指す」というアサーションを見落とすと、実装は正しいのに既存テストが red になって初めて気づく（あるいは逆に、実装ミスがあってもテストが通ってしまうケースもありうる）。
**Why it happens:** D-11 実装前の設計時点でテストへの影響を洗い出さないと、Task 分割時にテスト修正が漏れる。
**How to avoid:** 以下3箇所を D-11 実装と同一 Task 内で更新する。
**Warning signs（本セッションで直接確認した既存アサーション・修正が必要な箇所）:**
- `tests/test_toast.py:327`（`test_save_file_failure_shows_toast_with_retry` 内）— `assert retry_cb == app._save_file` [VERIFIED: tests/test_toast.py:327]
- `tests/test_toast.py:338`（`test_save_as_failure_then_success_dismisses` 内）— `assert toast.shown[-1][2] == app._save_as` [VERIFIED: tests/test_toast.py:338]
- `tests/test_toast.py:352`（`test_save_compressed_failure_shows_toast` 内）— `assert toast.shown[-1][2] == app._save_compressed` [VERIFIED: tests/test_toast.py:352]

これら3件は D-11 適用後、`retry_cb`/`toast.shown[-1][2]` が「実保存層の呼び出し（例: `functools.partial` や `lambda` で path を束縛したもの）」に変わるため、単純な `==` 比較では意図通り書けない可能性が高い。**検証方法をオブジェクト等価性から「呼び出すと `askyesno`/`asksaveasfilename` を経由せずに保存が完了すること」の振る舞いベースへ変更する**（既存の `IN-01` の Fix 意図に合致する検証に置き換える）ことを推奨する。

### Pitfall 3: V190-QA-02/ROADMAP.md の文言訂正（D-12）を実装タスクと別扱いにして忘れる

**What goes wrong:** D-12 は REQUIREMENTS.md の V190-QA-02 と ROADMAP.md の Success Criteria #2 の**両方**を訂正する決定だが、これはコード実装ではなくドキュメント編集のため、Task リストから漏れやすい。
**Why it happens:** 「実装タスク」中心で Task を切ると、ドキュメント訂正が付随作業として省略されがち。
**How to avoid:** D-11 実装 Task の中、またはその直前に「REQUIREMENTS.md:60 と ROADMAP.md:203 の文言訂正」を明示タスクとして含める。
**Warning signs（現状の文言・訂正対象箇所）:**
- `REQUIREMENTS.md:60` — `- [ ] **V190-QA-02**: 保存トーストの再試行を実行した際、上書き確認ダイアログが再表示される（IN-01・v1.8.0 Phase 6 持ち越し）` [VERIFIED: REQUIREMENTS.md:60]
- `ROADMAP.md:203` — `2. 保存トーストの再試行を実行すると、上書き確認ダイアログが再表示される（V190-QA-02）` [VERIFIED: ROADMAP.md:203]
- D-12 が指定する訂正後の文言: 「再試行時は上書き確認・保存先選択を再表示せず、前回確定した対象へ黙って再保存する」（03-CONTEXT.md:47）

### Pitfall 4: Python 3.14 Tcl/Tk 環境修復を「テスト環境だけ」の問題と誤診断する（PITFALLS.md Pitfall 13）

**What goes wrong:** `conftest.py` へ `TCL_LIBRARY` 等をハードコードすると、開発環境のテストは直るが PyInstaller 配布 EXE（`frozen` 実行時）の Tcl/Tk 探索ロジックと衝突し、配布ビルドが逆に壊れる。
**Why it happens:** 環境変数の上書きは「動いたように見える」ため、根本原因（venv 相対パス誤解決等）に触れずに対症療法で終わらせてしまう。
**How to avoid:** D-05 の通り、修復はコード変更ゼロ（再現しなければ）を第一候補にし、どうしてもコード変更が必要な場合は `frozen` 判定と開発環境判定を分岐させる。
**Warning signs:** 配布 EXE の起動確認時に、開発環境では出なかった Tcl/Tk 関連エラーが新たに出る。

### Pitfall 5: 遡及 UAT 項目を「現行コードに存在しない機能」に対して実施しようとする

**What goes wrong:** v1.4.0/v1.6.0/v1.7.1 の UAT 項目をそのまま `03-UAT-RESULTS.md` へ転記すると、その後の大規模リファクタ（v1.8.0 Phase 1 の肥大モジュール分割、v1.8.0 Phase 3 の OCRRunEngine 抽出）でコード配置や実装詳細が変わっている項目が混入するリスクがある。
**How to avoid:** D-13 の通り、対象化前に現行コードとの照合を行う。本セッションで grep により以下を確認済み（照合結果は Assumptions Log 参照・行番号までの精査はプラン/実行時に必要）:
- `pagefolio/dialogs/llm_config/sections.py` に「選択中プロバイダ固有の設定」「全プロバイダ共通の設定」相当の文言キーが存在 [VERIFIED: grep 結果でファイル一致]
- `pagefolio/dialogs/settings.py` に「外観セクション」「操作セクション」「AI・OCR セクション」のコメント区切りが存在（75/155/172行）[VERIFIED: pagefolio/dialogs/settings.py:75,155,172]
- `pagefolio/dialogs/shortcuts.py` が現存（ShortcutsDialog の配置先）
- `pagefolio/viewer.py` に拡大/縮小ポップアップの文言参照が存在
- LM Studio のモデル切替反映ロジック（v1.4.0 Phase 04 の対象）は現在 `pagefolio/ocr_engine.py`/`ocr_dialog.py` に移動している（v1.8.0 Phase 3 の OCRRunEngine 抽出の影響）— **元の `_on_run`（ocr_dialog.py の旧行番号）という参照は現在では無効**であり、プラン/実行時に `ocr_engine.py` 側の該当箇所を再特定する必要がある

## Runtime State Inventory

該当なし。本フェーズはリネーム・改名・移行フェーズではない（V190-QA-02 のリファクタは同一メソッド群の内部構造変更のみで、外部から見える識別子・設定キー・環境変数名の変更を伴わない）。D-16 のバージョン文字列更新（`v1.8.1` → `v1.9.0`）は `APP_VERSION` を単一情報源とする既存の同期作法（CLAUDE.md）に従うのみで、DB/外部サービス/OS登録状態への影響はない。

## Code Examples

### 現状の保存3経路（修正対象・全文）

```python
# Source: pagefolio/file_ops.py:1134-1261（本セッションで直接読解）
def _save_file(self):
    """上書き保存 — 確認ダイアログ付き"""
    if not self.doc:
        messagebox.showinfo(self._t("info_title"), self._t("info_open_first"))
        return
    if not self.filepath:
        self._save_as()
        return
    ext = os.path.splitext(self.filepath)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        self._set_status(self._t("status_image_save_as"))
        self._save_as()
        return
    if not messagebox.askyesno(
        self._t("save_confirm_title"),
        self._t("save_confirm_msg").format(name=os.path.basename(self.filepath)),
    ):
        return
    try:
        try:
            self.doc.save(
                self.filepath, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP
            )
        except Exception as e:
            logger.debug("incremental save 失敗、開き直して保存: %s", e)
            self._overwrite_current_file(self.filepath)
        self._set_status(
            self._t("status_saved").format(name=os.path.basename(self.filepath))
        )
        self.plugin_manager.fire_event("on_file_save", self, self.filepath)
        if getattr(self, "_toast", None) is not None:
            self._toast.dismiss("save_file")
    except Exception as e:
        self._show_error_or_toast(
            "save_file",
            self._t("err_save_title"),
            self._t("err_save_msg").format(e=e),
            self._save_file,   # ← D-11 で「実保存層」へ差し替える対象
        )
```

`_save_as`（file_ops.py:1174-1195）・`_save_compressed`（file_ops.py:1221-1261）も同型で、`retry_cb` にそれぞれ `self._save_as`/`self._save_compressed`（元メソッド全体）を渡している。

### ToastManager の retry_cb 差し替え契約（無改造で再利用する部分）

```python
# Source: pagefolio/toast.py:40-55（本セッションで直接読解）
def show(self, category, message, retry_cb):
    """``category`` のトーストを表示する。
    ...
    この場合も再試行ボタンの
    コールバックは最新の ``retry_cb`` へ差し替える（WR-03）。
    """
    if self._active_category == category and self._frame is not None:
        self._msg_var.set(message)
        if self._retry_btn is not None:
            self._retry_btn.configure(command=retry_cb)
        return
    self._destroy_frame()
    self._active_category = category
    self._build_frame(category, message, retry_cb)
```

D-11 は `retry_cb` に渡す**呼び出し可能オブジェクトの中身**を変えるだけで、`ToastManager.show()`/`_build_frame()` 自体は無改造でよい（CONTEXT.md の記述どおり、本セッションでもコード上で裏付け済み）。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `pytest -q` 全件実行が公式ゲート（前提） | 分割実行（`--ignore=tests/test_ocr_pipeline.py` + 単独実行）を暫定運用として受容 | 01-07 実行時（Phase 1 途中） | D-01 でこれを正式なリリースゲート条件として文書化する。ただし本セッションのデータでは現行 HEAD は単一プロセスでも 7/7 grün のため、Task 0 の再現試行次第では「単一プロセス一発で足りる」へ判断が変わりうる |
| 分割コマンドの内訳が `1167 + 17 = 1184` | 現在は `1370 + 17 = 1387`（Phase 2 でテスト約200件追加） | Phase 2 完了（2026-08-11） | CLAUDE.md/D-07 で記録する「日常の実行手順」は現在の件数で書き直す必要がある |
| 保存トースト再試行 = 元メソッド全体を再実行（確認ダイアログ込み） | 実保存層のみを再実行（確認スキップ） | 本フェーズ（V190-QA-02・D-09〜D-11） | ユーザー体験上「再試行」の語義に合致。IN-01（v1.8.0 Phase 6 06-REVIEW.md）で提起されていたが「future polish」として当時は対象外にされていた項目の正式消化 |

**Deprecated/outdated:**
- 「STATE.md の repro rate（7/10）を Phase 3 実行時の前提としてそのまま使う」という読み方 — 現行コードでの再現試行を経ずに仮説検証へ進むのは非効率（Pitfall 1 参照）

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 7回連続 grün という本セッションの再現試行結果は、次にプラン実行時に同一マシン・同一 `.venv` で再実行しても同様に非再現であり続ける | Summary / Pitfall 1 | 誤りの場合: 実際には低確率で再現するバグが残っており、Task 0 の再現試行回数がたまたま外れ値だった可能性がある。D-08 が要求する「複数回連続実行」をプラン側でも独立に実施すべきで、本リサーチの7回だけで「解消済み」と断定してはならない（プランのTask 0で改めて実施し、本リサーチの結果と合算して証拠とすることを推奨） |
| A2 | STATUS_BREAKPOINT クラッシュが非再現になった原因は「Phase 2 で約200件テストが追加されテスト収集順序/メモリレイアウトが変わったため」という推測 | Pitfall 1 | 因果関係は未証明（相関のみ）。仮に的外れでも Task 0 の判断（再現試行→分岐）には影響しない。ただし D-02 の仮説2本（assertion rewriting / 二分探索）の優先順位づけの参考情報としてのみ扱うこと |
| A3 | v1.4.0 Phase 04 の human-verify 項目（LM Studio モデル切替反映・タイムアウト表示一致）は、v1.8.0 Phase 3 の OCRRunEngine 抽出後も同等の検証観点（UI 変更→実際の HTTP リクエストへの反映）が `ocr_engine.py`/`ocr_dialog.py` のどこかに存在し続けている | Pitfall 5 | 誤りの場合: 該当ロジックが既に別の形（例: 常時再生成方式）に変わっており、この UAT 項目自体が意味を失っている可能性がある。プラン/実行時に `ocr_engine.py` を直接読解し、対象コードの現在地を再確認してから `03-UAT-RESULTS.md` の項目文言を確定させること |
| A4 | D-11 の実保存層の推奨命名（`_do_save_file(path)`/`_do_save_as(path)`/`_do_save_compressed(path, save_kwargs)`）は Claude's Discretion 範囲内の提案であり、既存コードの命名規則（`_overwrite_current_file` 等）と衝突しない | Architecture Patterns Pattern 1 | 誤りの場合でも実害は小さい（命名の選び直しのみ）。CONTEXT.md が明示的に「関数名・シグネチャ・配置は Claude's Discretion」としているため、プランナーが別名を選んでもよい |

## Open Questions

1. **Task 0 の再現試行で実際にクラッシュ/ERROR が観測された場合、D-02 の「タイムボックス」はどう運用するか**
   - What we know: D-02 は「仮説2本を検証したら打ち切り」を契約としている
   - What's unclear: 1仮説あたりの試行回数・時間の上限が CONTEXT.md に明記されていない（Claude's Discretion 相当だが discretion 一覧にも明記なし）
   - Recommendation: プラン作成時に「各仮説の検証は1コマンド実行+結果確認で完結する（D-03 の設計どおり1コマンドで白黒がつく）」ため、時間ではなく「コマンド実行→結果記録」の1サイクルを1仮説の単位として定義すればタイムボックス化が自然に成立する

2. **本セッションで判明した「1370+17=1387」という更新済み分割数を CLAUDE.md のどこに反映するか**
   - What we know: D-07 は「日常の実行手順は CLAUDE.md の『変更時のチェックリスト』へ」と定めている
   - What's unclear: 分割コマンドの具体的な追記位置・書式（Claude's Discretion 記載のとおり）
   - Recommendation: 「変更時のチェックリスト」の `pytest` 確認項目の直下に、Task 0 の再現試行結果に応じて「単一プロセスで足りる」か「分割コマンド（件数付き）」のどちらかを明記する

3. **遡及 UAT のうち Claude 実 API が必要な項目（v1.6.0 Phase 4 の項目7）の扱い**
   - What we know: 本セッションの環境変数チェックで `GEMINI_API_KEY`/`RUNPOD_API_KEY` は設定済み、`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GOOGLE_API_KEY` は未設定 [VERIFIED: 本セッションで環境変数存在チェック実行]
   - What's unclear: プラン実行時（別セッション/別ユーザー環境）でも同じ鍵の有無が維持されるか
   - Recommendation: D-14 の通り「手元にキーがあるプロバイダの分だけ実施」する。Gemini 分は実施可能、Claude/OpenAI 分は理由付きで Deferred へ記録する運用が、本セッションの環境と一致する

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14.6（`.venv`） | 全テスト実行・GUI テスト | ✓ | 3.14.6 | — |
| Tcl/Tk | GUI テスト（`tkinter.Tk()`） | ✓ | 8.6.15 | — |
| pytest | テスト実行 | ✓ | 9.1.1 | — |
| GEMINI_API_KEY | 遡及 UAT（Gemini 実 API 品質確認） | ✓ | — | — |
| RUNPOD_API_KEY | 遡及 UAT（RunPod 実 API、対象範囲外の可能性が高い） | ✓ | — | — |
| ANTHROPIC_API_KEY | 遡及 UAT（Claude 実 API 品質確認・v1.6.0 Phase 4 項目2） | ✗ | — | D-14 に従い「未実施・理由付き」で Deferred へ記録 |
| OPENAI_API_KEY | v1.9.0 新規 OpenAI プロバイダの UAT（Phase 2 で実施済みのため本フェーズでは対象外の想定） | ✗ | — | Phase 2 の 02-04 実機確認3分割で既に実施済み（STATE.md 参照）。本フェーズで再実施は不要 |
| CI 環境 / 別マシン | PITFALLS.md の「クリーンな別環境での再現確認」チェック項目 | ✗ | — | D-08 により対象外と明示的に受容済み（同一環境での複数回連続実行に置換） |

**Missing dependencies with no fallback:**
- なし（ANTHROPIC_API_KEY の欠如は D-14 のフォールバック運用でブロッカーにならない）

**Missing dependencies with fallback:**
- ANTHROPIC_API_KEY（Deferred 記録で対応）
- CI 環境（同一環境複数回実行で代替、D-08 で確定済み）

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1（`pyproject.toml` の `[tool.pytest.ini_options]` で `testpaths = ["tests"]` 設定済み）[VERIFIED: pyproject.toml:11-13] |
| Config file | `pyproject.toml` |
| Quick run command | `./.venv/Scripts/python.exe -m pytest -q -k "<対象>"` |
| Full suite command | `./.venv/Scripts/python.exe -m pytest -q --basetemp=<短パス>`（1387件・本セッションで7回実行し全件7/7 grün・平均約35秒） |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V190-QA-01 | 現行 HEAD での単一プロセス完走再現試行 | integration（フルスイート複数回実行） | `for i in 1..N; do pytest -q --basetemp=<短パス>$i; done` | ✅ 既存コマンドのみで足りる（新規テストファイル不要） |
| V190-QA-01 | 分割実行コマンドが1387件全件をカバーする | integration | `pytest -q --ignore=tests/test_ocr_pipeline.py`（1370件）+ `pytest -q tests/test_ocr_pipeline.py`（17件） | ✅ 既存（件数を D-07 の記録で更新するのみ） |
| V190-QA-02 | 保存3経路の再試行が確認ダイアログ/ピッカーを再表示しない | unit | `pytest tests/test_toast.py -k "TestSaveFilePathsUseSharedHelper" -x`（3件を D-11 実装後の振る舞いへ書き換え） | ⚠️ 既存3件を修正 Wave 0（Pitfall 2 参照） |
| V190-QA-03 | 遡及 UAT 項目が現行コードと照合され `03-UAT-RESULTS.md` に記録される | manual UAT | `03-UAT-RESULTS.md` 手順実行・記録（自動テスト対象外） | ❌ 新規成果物（D-15） |

### Sampling Rate

- **Per task commit:** D-11 実装時は `pytest tests/test_toast.py tests/test_password.py -q`（保存関連の既存テストファイル）
- **Per wave merge:** `./.venv/Scripts/python.exe -m pytest -q --basetemp=<短パス>`（フルスイート）
- **Phase gate:** D-01 で定義する合格条件（単一プロセス一発 または 分割実行）が green であることを `/gsd-verify-work` 前に確認

### Wave 0 Gaps

- [ ] `tests/test_toast.py`（3箇所: 327/338/352行）— D-11 実装に合わせて `retry_cb` の検証方法をオブジェクト等価性から振る舞いベースへ書き換える必要あり（Pitfall 2）
- [ ] Task 0（再現試行）用の実行ログ記録先 — フェーズ成果物（調査レポート、ファイル名は Claude's Discretion）に「試行回数・結果・コマンド」を記録するテンプレートが必要
- [ ] `03-UAT-RESULTS.md`（新規）— D-15 のフォーマット（項目・手順・合否・根拠）

*(その他の Wave 0 ギャップなし — 既存テストインフラが大半をカバーする)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 本フェーズはローカルアプリのテスト/UX 修正であり認証機構を扱わない |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 該当なし |
| V5 Input Validation | no（新規入力面なし） | D-11 の実保存層は既存 `path`/`save_kwargs` をそのまま受け渡すのみで新規のユーザー入力を追加しない |
| V6 Cryptography | no（変更なし） | `_save_file`/`_save_as`/`_save_compressed` の暗号化維持ロジック（`PDF_ENCRYPT_KEEP`、Phase 1 で確立）はそのまま維持される。D-11 は「path を受け取る位置」を変えるだけで `save_kwargs` の中身（暗号化引数含む）には触れない |

### Known Threat Patterns for {stack}

該当する新規脅威パターンなし。強いて言えば、D-11 のリファクタで暗号化引数（`encryption=fitz.PDF_ENCRYPT_KEEP`）の受け渡しを誤って落とすと Phase 1（V190-SAFE-01）の暗号化維持ロジックが退行するリスクがあるため、D-11 実装時は既存の暗号化維持回帰テスト（`tests/test_password.py`）をフルスイートに含めて確認すること。

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| D-11 リファクタによる暗号化引数の意図しない欠落（既存 Phase 1 の回帰） | Tampering（データ整合性の後退） | `tests/test_password.py` の既存暗号化維持テスト（`test_save_as_keeps_encryption`/`test_save_file_fallback_keeps_encryption`/`test_save_compressed_*_keeps_encryption`）を D-11 実装後も全件 green のまま維持することをタスクの完了条件に含める |

## Sources

### Primary (HIGH confidence — 本セッションで直接検証)

- `pagefolio/file_ops.py:1102-1261`（`_overwrite_current_file`/`_save_file`/`_save_as`/`_save_compressed` 全文読解）
- `pagefolio/ui_builder.py:170-200`（`_show_error_or_toast` 読解）
- `pagefolio/toast.py`（`ToastManager` 全文読解）
- `pagefolio/constants.py`（`APP_VERSION = "v1.8.1"` 確認）
- `tests/conftest.py`（既存 fixture 一覧確認）
- `tests/test_toast.py:304-352`（既存アサーション3件の直接確認）
- `tests/test_pdf_ops.py`（先頭 import 構成・git log での最終更新コミット確認）
- `pyproject.toml`（pytest 設定確認）
- 実機コマンド実行: `python --version`（3.14.6）・`tkinter.Tk()` 生成（Tk 8.6.15）・`pytest --collect-only`（1387件・1370+17分割確認）・`pytest -q` フルスイート7回連続実行（全件grün）・依存バージョン確認（fitz/Pillow/pytest が requirements.txt と完全一致）・環境変数チェック（GEMINI_API_KEY/RUNPOD_API_KEY 設定済み、ANTHROPIC_API_KEY/OPENAI_API_KEY/GOOGLE_API_KEY 未設定）
- `.planning/STATE.md`「Blockers/Concerns」セクション
- `.planning/phases/03-qa-release-gate/03-CONTEXT.md` / `03-DISCUSSION-LOG.md`
- `.planning/milestones/v1.8.0-phases/06-ux-ui/06-REVIEW.md`（IN-01 の原文）・`06-VERIFICATION.md`（IN-01 の scope-out 経緯）
- `.planning/milestones/v1.4.0-phases/04-provider-abstraction/04-VERIFICATION.md`（human_needed 2項目）
- `.planning/milestones/v1.7.1-phases/04-ui-ux/04-UAT.md`（7項目・全件 pass 記録）
- `.planning/milestones/v1.6.0-phases/04-ai-c/04-VERIFICATION.md`（human_needed 2項目のうち markdown 表示分）
- `.planning/milestones/v1.6.0-REQUIREMENTS.md`（V16-QUAL-03 定義）

### Secondary (MEDIUM confidence)

- `.planning/research/PITFALLS.md` Pitfall 13（Python 3.14 Tcl/Tk 環境修復の注意点）
- `.planning/research/STACK.md`（Tcl/Tk 根本原因候補・CPython #125235）
- `.planning/research/SUMMARY.md`（Phase 6/Phase 3 の位置づけ）

### Tertiary (LOW confidence)

- CPython issue #125235 / python-build-standalone issue #913（STACK.md 経由の間接引用・本セッションでは再確認していない）

## Metadata

**Confidence breakdown:**
- 環境切り分け（V190-QA-01）: MEDIUM〜HIGH — 実機再現試行データ（7/7 grün）は HIGH だが、ネイティブ層の根本原因自体は依然未解明（LOW）
- 保存トースト再試行（V190-QA-02）: HIGH — 既存コード・既存テストを全文直接読解済み
- 遡及 UAT（V190-QA-03）: MEDIUM — 候補項目の「現行コードに存在するか」は grep レベルで確認済みだが、詳細な行番号・実装詳細の再照合はプラン/実行時に必要

**Research date:** 2026-08-11
**Valid until:** 7日程度（V190-QA-01 の再現試行データは実行環境依存で変化しうるため短め。他の2項目は安定）
