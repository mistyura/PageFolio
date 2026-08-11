# Phase 3 Plan 2: テスト実行環境 切り分け調査ログ

**調査日:** 2026-08-11
**対象要件:** V190-QA-01
**対象 HEAD:** 03-01 適用後（コミット `e9e277c` 時点）

このレポートは、`.planning/STATE.md`「Blockers/Concerns」が記録する2症状（① `TclError`
によるセットアップ ERROR のフレーキー、② `STATUS_BREAKPOINT` プロセスクラッシュ）を
現行 HEAD で実機再現試行し、その一次データと結論を記録するものである。
「調べる前に直さない」（D-05）に従い、Task 1 の時点ではコード変更を一切行っていない。

---

## 対象環境

すべて当セッションで `.venv` 経由で実行し実測した値のみを記載する。

| 項目 | 実測値 | 実行コマンド |
|------|--------|-------------|
| Python | `3.14.6` | `./.venv/Scripts/python.exe --version` |
| Tcl/Tk | `8.6.15` | `tkinter.Tk().tk.call('info','patchlevel')`（単体生成は成功・クラッシュなし） |
| pytest | `9.1.1` | `import pytest; pytest.__version__` |
| PyMuPDF (fitz) | `('1.28.0', '1.29.0', None)` | `import fitz; fitz.version` |
| pytest 収集件数（`--collect-only -q`） | `1398 tests collected in 0.33s` | `./.venv/Scripts/python.exe -m pytest --collect-only -q --basetemp=...` |

収集件数は 03-RESEARCH.md 時点の 1387 件から **1398 件**へ増えている（03-01 プランで
`tests/test_toast.py` に `retry_skips` 系テスト等が追加されたため）。以降の記録は
この実測値 1398 のみを使用し、リサーチ時点の 1387 という数値は使わない。

---

## 症状 ①: TclError によるセットアップ ERROR

**STATE.md の初出記述（要約）:** requirements.txt 指定バージョンへ揃えた `.venv` でフルテスト
スイート（当時1101件）を複数回連続実行すると、毎回異なる2件が `_tkinter.TclError`（アサーション
失敗ではなく Tk インタプリタ生成失敗。例: `couldn't read file "...ttk/clamTheme.tcl"` だが
実ファイルは存在）で ERROR になることがある（単体実行では常に合格）。1101件の `tk.Tk()`
生成/破棄を単一 pytest プロセスで連続実行することによる Tcl/Tk リソース消耗系のフレーキーと
推定されていた。

**今回の観測結果:** 現行 HEAD（1398件収集）に対して単一プロセス `pytest -q` を **10 回連続
実行**し、各回の出力を機械的に `grep -c "ERROR"` / `grep -l "TclError"` で検査した結果、
**10 回すべてで ERROR 0 件・`TclError` の出現 0 件**だった（下記「再現試行ログ」参照）。

---

## 症状 ②: STATUS_BREAKPOINT クラッシュ

**STATE.md の初出記述（要約）:** 01-07 実行時にオーケストレーターが A/B 検証で特定。フルスイート
`pytest -q`（単一プロセス）が `tests/test_ocr_pipeline.py::TestPipelineHardening::
test_cancel_finite_time_no_deadlock` の実行中に `Windows fatal exception: code 0x80000003`
（STATUS_BREAKPOINT）+ `<freed thread state>` でプロセスごとクラッシュする（HEAD 内容で約10回中
7回・再現率が高い）。**製品コードは無実**と A/B 検証済み（`file_ops.py`/`lang.py` を HEAD にし
テストのみ 01-07 前へ戻すと 4/4 green・基準内容は累計19回中0クラッシュ）。引き金は
`tests/test_pdf_ops.py`（01-07 版）の**存在そのもの**で、`--deselect` でも再現し `--ignore`
では再現しない＝import 時点で成立。モジュールサイズ模倣・`import ast`/`pathlib` の追加のみでは
再現せず、`_drive_pipeline` の孤児 daemon スレッド仮説は棄却・revert 済み。

**今回の観測結果:** 現行 HEAD（`tests/test_pdf_ops.py` は 01-07 版のまま無変更 — 03-RESEARCH.md
の `git log --oneline -- tests/test_pdf_ops.py` 確認結果を継承）に対する同じ 10 回連続実行で、
**プロセスクラッシュ（`Windows fatal exception`）の出現は 0 回**だった。03-RESEARCH.md が
リサーチセッションで実施した独立の 7 回連続実行（7/7 grün）と合算すると、現行 HEAD では
**累計 17 回連続グリーン**（本プランの10回 + リサーチの7回）となる。

---

## 再現試行ログ

実行コマンド（全10回共通・basetemp のみ回ごとに連番）:
`./.venv/Scripts/python.exe -m pytest -q --basetemp="$LOCALAPPDATA/Temp/pf_pytest_tmp<N>"`

| 実行番号 | コマンド | passed | failed | error | クラッシュ | TclError |
|---------|---------|--------|--------|-------|-----------|----------|
| 1 | `pytest -q --basetemp=...pf_pytest_tmp1` | 1398 | 0 | 0 | なし | なし |
| 2 | `pytest -q --basetemp=...pf_pytest_tmp2` | 1398 | 0 | 0 | なし | なし |
| 3 | `pytest -q --basetemp=...pf_pytest_tmp3` | 1398 | 0 | 0 | なし | なし |
| 4 | `pytest -q --basetemp=...pf_pytest_tmp4` | 1398 | 0 | 0 | なし | なし |
| 5 | `pytest -q --basetemp=...pf_pytest_tmp5` | 1398 | 0 | 0 | なし | なし |
| 6 | `pytest -q --basetemp=...pf_pytest_tmp6` | 1398 | 0 | 0 | なし | なし |
| 7 | `pytest -q --basetemp=...pf_pytest_tmp7` | 1398 | 0 | 0 | なし | なし |
| 8 | `pytest -q --basetemp=...pf_pytest_tmp8` | 1398 | 0 | 0 | なし | なし |
| 9 | `pytest -q --basetemp=...pf_pytest_tmp9` | 1398 | 0 | 0 | なし | なし |
| 10 | `pytest -q --basetemp=...pf_pytest_tmp10` | 1398 | 0 | 0 | なし | なし |

実行時間は 28.13秒〜47.81秒（ディスクキャッシュ等の外部要因でばらつき、後半5回はやや高速）。
全ログを `grep -l "Windows fatal exception" run_*.log` / `grep -l "TclError" run_*.log` で
機械的に走査し、一致ファイル 0 件（該当なし）を確認済み。

`%TEMP%\pytest-of-shdwf` に対する `PermissionError` の併発は今回は発生しなかった
（`--basetemp` を回ごとに別ディレクトリへ振ったため、そもそもロック競合の対象にならなかった
可能性がある。発生しなかった事実のみを記録し、根本対応は行わない）。

---

## 現時点の判定

**症状①（TclError）・症状②（STATUS_BREAKPOINT クラッシュ）ともに「再現しなかった」。**

D-04 に従い、両症状は同一の10回連続実行という実験の中で並行して観測したが、上記のとおり
**節を分けて別々に判定を記録**している。片方の非再現をもう片方の非再現と読み替えてはいない
（症状①は「毎回異なる2件」という統計的フレーキー、症状②は「特定テストの import 時点」という
決定論的な引き金という異なる性質のため、両方が同じ10回で同時に非再現だったことは偶然の一致
ではなく、それぞれ独立に確認された事実として扱う）。

→ **Task 2 は分岐 A（D-05: いずれも再現しなかった場合）へ進む。**

---

## 結論 ①（TclError によるセットアップ ERROR）

**現行環境では再現しない。**

**根拠:** 本プラン Task 1 の10回連続実行（1398件 × 10回 = 13,980 テスト実行相当）で ERROR
0件・`TclError` 出現 0件。03-RESEARCH.md のリサーチセッションでは症状①個別の統計は取っていない
（症状②の再現試行と兼ねた7回実行で TclError 系 ERROR 0件と記録済み・Pitfall 1 参照）ため、
症状①単独の累計は本プランの10回が主たる証拠となる。

過去の観測（STATE.md 記録時点・1101件のスイート）では「約1101件の `tk.Tk()` 生成/破棄を単一
プロセスで連続実行することによる Tcl/Tk リソース消耗系のフレーキー」と推定されていた。現行スイート
は1398件（当時より約300件多い）に増えているにもかかわらず10回連続で非再現であり、「テスト件数の
増加がリソース消耗を悪化させる」という当時の推定を支持するデータは今回得られなかった。

なお、03-01-SUMMARY.md（本フェーズ Plan 1）は「フルスイート実行1回目で `tests/
test_ocr_dialog_center.py` の2テストが `_tkinter.TclError` で ERROR になったが、直後の
再実行では1398/1398 grün」という**1回限りの発生**を記録している。これは本プランの10回連続
実行と矛盾しない（フレーキーの定義上、低確率での単発発生はあり得る。10回中0回だったことは
「解消した」ことの証明ではなく「今回の10回では発現しなかった」という一次データである — 次段落
「未解明のまま残るもの」を参照）。

---

## 結論 ②（STATUS_BREAKPOINT クラッシュ）

**現行環境では再現しない。**

**根拠:** 本プラン Task 1 の10回連続実行 + 03-RESEARCH.md のリサーチセッション7回連続実行、
合計 **17 回連続グリーン**（クラッシュ0件）。再現率 0.7（既知値）の事象が17回連続で一度も
出現しない確率は 0.3^17 ≈ 1.3×10^-9 であり、統計的に「現行 HEAD では成立しない」と言い切れる
水準に達している。

`tests/test_pdf_ops.py`（クラッシュの引き金と特定済みのファイル）は 01-07 実行時点から
無変更（03-RESEARCH.md で `git log --oneline -- tests/test_pdf_ops.py` により確認済み・
本セッションでも再確認は不要と判断——ファイル内容が変わっていないことは前提として引き継ぐ）。
コード自体は変わっていないにもかかわらず非再現となっている。

---

## 未解明のまま残るもの

**根本原因（ネイティブ層）は依然未解明であり、非再現の因果は未証明である。**

03-RESEARCH.md の Assumptions Log A2 は「Phase 2 で約200件テストが増えて収集順序 / メモリ
レイアウトが変わったため」という説明を挙げているが、これは**相関のみの推測**であり、本プランの
17回連続グリーンという結果によって裏付けが強化されたわけではない（テスト件数がさらに1387→1398
へ増えた状態でも非再現が継続しているという新しい一次データが加わっただけで、「なぜ非再現に
なったか」の機序は依然として不明のままである）。

次マイルストーンで症状①・②のいずれかが再発した場合の入口として、D-03 の2仮説コマンドを
そのまま残す:

```bash
# 仮説1: pytest assertion rewriting
./.venv/Scripts/python.exe -m pytest -q --assert=plain -p no:cacheprovider --basetemp=<短パス>

# 仮説2: 二分探索（tests/test_pdf_ops.py をクラス単位で半分ずつ --deselect）
```

---

## 検証しなかった仮説と理由

D-03 で固定された2仮説（① pytest assertion rewriting・② `tests/test_pdf_ops.py` の二分探索）
は、**Task 1 でいずれの症状も再現しなかったため検証していない**。分岐A（D-05）は「再現しな
ければコード変更ゼロ・仮説検証も行わない」ことを前提としており、検証していないものを
「検証して外れた」と書くことは D-02 の趣旨（反証データの正確な記録）に反する。**両仮説は
「未着手・次回再発時の入口として保存」という状態のまま次マイルストーンへ引き継ぐ。**

`_drive_pipeline` の孤児 daemon スレッド仮説は STATE.md の記録どおり既に棄却・revert 済みで
あり、本プランでも再検証していない（03-CONTEXT.md D-03 の指示どおり）。

---

## 対象外とした確認項目

`.planning/research/PITFALLS.md` のチェック項目には「クリーンな別環境（別マシン / CI / 別
ユーザー）でも再現しないことを確認する」という趣旨の項目が含まれる。本プロジェクトには
**CI パイプラインも共有可能な別マシン環境も存在しない**（単一開発者・単一 Windows マシンでの
ローカル開発）ため、この確認は実行不能であり対象外とする（D-08）。

代替として、D-08 が定める「同一環境での複数回連続実行」（本プランの10回 + リサーチの7回 =
累計17回）を統計的な再現性判定の代替手段として採用した。CI 環境の導入は03-CONTEXT.md
「Deferred Ideas」に「新しい能力の追加であり別マイルストーンの判断」として明示的に記録
されており、本フェーズのスコープ外である。

---

## Task 1/2 統合判定サマリ

| 症状 | Task 1（10回） | 03-RESEARCH.md（7回） | 累計 | 判定 | コード変更 |
|------|----------------|------------------------|------|------|-----------|
| ① TclError セットアップ ERROR | 0/10 | 0/7（併発観測） | 0/17 | 現行環境では再現しない | ゼロ |
| ② STATUS_BREAKPOINT クラッシュ | 0/10 | 0/7 | 0/17 | 現行環境では再現しない | ゼロ |

`git diff --stat -- pagefolio/ tests/` は Task 1・Task 2 を通じて出力ゼロ（コード変更なし）。
`tests/conftest.py` への修復コードは D-05 に従い**追加しない**（再現しなかったため）。

以降のリリースゲート合格条件（実行手順）は `CLAUDE.md`「## リリースゲート（全テスト完走
条件）」を参照。
