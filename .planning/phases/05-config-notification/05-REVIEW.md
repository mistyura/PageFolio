---
phase: 05-config-notification
reviewed: 2026-11-06T10:29:41Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - .gitattributes
  - README.md
  - distribution/samples/ocr_custom_prompt_sample.md
  - distribution/samples/ocr_summary_prompt_sample.md
  - distribution/はじめに.md
  - docs/CONFIGURATION.md
  - docs/DEVELOPMENT.md
  - pagefolio/constants.py
  - pagefolio/lang.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - requirements.txt
  - tests/config_notice_support.py
  - tests/conftest.py
  - tests/release_fake_ocr.py
  - tests/release_uat_support.py
  - tests/test_config_notification.py
  - tests/test_gc_barrier_guard.py
  - tests/test_ocr.py
  - tests/test_ocr_dialog_provider_refresh.py
  - tests/test_ocr_local_endpoint.py
  - tests/test_release_build.py
  - tests/test_release_contract.py
  - tests/test_release_uat_support.py
  - tests/test_startup_windows.py
  - tools/build_release.py
  - 開発履歴.md
  - pagefolio/__main__.py
  - pagefolio/startup_win32.py
  - pagefolio/startup_wake.py
  - tests/startup_foreground_audit.py
  - tests/startup_wake_child.py
  - tests/test_startup_foreground_audit.py
  - tests/test_startup_wake.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
  necessity: 0
status: clean
---

# Phase 05: コードレビュー報告

## 2026-11-06 現行170入力への独立再結合

**判定: clean。新規 BLOCKER / WARNING / INFO 各0。** 既存34ファイルの standard レビューと CR-01/02/03・WR-01 の fixed を保持し、不変部分の全走査は繰り返していない。前回 v3 単一全件の `../06-release-validation/06-05-evidence/w05c-v3-final-native-20261105/before.json`（170入力）と新全件 `../04-startup-control/04-reverify-20261106-cr02/inputs-after.json` を34件の既存一覧で比較した。両台帳に共通する30件の差は `tests/test_startup_windows.py` と `開発履歴.md` のみ。台帳対象外4件（`.gitattributes`、sample prompt 2件、`docs/CONFIGURATION.md`）は作業ツリーとindexの差分なし。現行34件のうち新台帳にある30件は現在bytesのSHA-256とも一致する。

`tests/test_startup_windows.py:2170-2262` の変更は、native確認窓が可視・親無効化済みになってから `focus-ready` を出す試験時序と、非manualの自動閉鎖期限に限定される。manual経路は自動Noを行わない。`開発履歴.md:5-6` はW05c検証基盤の採用値厳密化・保留境界を記述し、`APP_VERSION` と製品の設定・通知・OCR off 経路は変更していない。Phase04の共有検証CR-02は採用判断の別指摘であり、Phase05のCR-02（通知寿命）のfixedを再openしない。今回の検証側 `decision === '採用'` と28否認回帰は、Phase04の独立レビューで修正確認済み。

再利用した正本 `../04-startup-control/04-reverify-20261106-cr02/{result.json,junit.xml,inputs-before.json,inputs-after.json}` と `../04-startup-control/04-QUALITY-CR02-20261106.json` は、単一全件2361 passed / 2 warnings / exit0、JUnit failure/error/skip 0、stderr空、170入力前後・現行一致、Ruff check / format 148件 / AST exit0を示す。生JUnitを独立集計すると `test_config_notification` 143、`test_settings_keyguard` 26、`test_toast` 38、`test_ocr_dialog_provider_refresh` 18、`test_release_contract` 30、`test_release_uat_support` 243の計498件が全てpass。先行Phase04の299件と公式21/21 passedは `../04-startup-control/04-VERIFICATION.md` に結合済み。本レビューでは pytest・GUI・実EXEを再実行していない。

Phase05の人手H01〜H14と禁止2件の意味評価は過去証拠の継承であり、今回新規実施とはしない。静的UIのV-01/S-01、DEP-05、owner_missing、通知前景不一致、W05cの元No不成立原因は未解除。正式台帳28pass/80必須not-run/対象外2、`ready_for_retry=false`、`release_allowed=false` を維持する。Phase05の独立goal検証は別ゲートであり、本レビューのcleanをその完了や出荷承認に置き換えない。根拠は `05-REVALIDATION-20261106.md`。

## 2026-11-05 W05c計測差分のコード再監査

新たに変化した`tests/test_startup_windows.py`の計測配線と`tests/w05c_evidence.py`/`tests/test_w05c_evidence.py`をstandard深度で確認した。manual native-quit限定の観測で、Phase 05の設定読込・保存owner、通知FIFO、原本保護、OCR off拒否を変更しない。計測失敗やNo未観測を成功へ変換しない。今回の新規Critical/Warning/Info各0。現行2293件/JUnit failure/error/skip0、167入力一致、設定関連対象は全てpass。`05-REVALIDATION-W05C-20261105.md`参照。

## 2026-11-05 現行差分レビュー

旧151入力から変化したPhase 05関連のrelease UAT試験3ファイルは、指定されたW01/W02だけのrequire-pass判定、指定範囲内の未実施拒否、隔離copyでの設定作成と未宣言ファイル拒否を検証する。Phase 05の設定I/O・通知・OCR off製品コードは当時のSHA-256と一致。現行118入力一致のnative全件2254 passedに該当試験も含まれ、追加critical/warning/infoは各0。既存CR-01/02/03・WR-01のfixedとopen0を維持する。Phase 06の未実施80必須行とW11対象外2行をpassへ変更しない。[05-REVALIDATION-20261105.md](05-REVALIDATION-20261105.md)参照。

## 案B・配布文書契約変更後の独立差分レビュー（現行）

前回検証から変わったcovered入力は tests/test_release_contract.py、README.md、distribution/はじめに.md、開発履歴.md。関連するrelease_uat_support.pyの固定承認検証入口と06-W11-SCOPE-APPROVAL.mdも読取照合した。製品・Phase05主要試験・CR-03回帰は不変。新規critical/warning/info各0、CR-01/02/03/WR-01はfixed/open0を維持する。

新文書試験は実文書をread-onlyに読み、7つの独立した保証/未確認語句とFALSE_PASS不存在をassertする。既存の版・Phase05履歴・原本hash・リンク・偽pass禁止assertは削除されていない。台帳試験は固定2キー/31ケース/110カード/108必須/2対象外、W11のnot-run・空観測・空回答を確認する。fixture copyへの承認/scope追加は正規入力の供給であり、期待値を被試験実装から生成する循環oracleではない。語句検査だけで文意の安全を断定せず、3文書の実文面と利用者承認を独立に読んだ。

変更後の全2232件・release_contract30件がpass、現行151入力一致を確認（05-REVERIFY-SCOPE-20261028.json）。新規pytest/GUI/build実行なし。親の旧2231件成功は変更後文書の根拠にしていない。Phase06の108必須行と対象外W11の2行はすべてnot-run、独立最終ゲートと出荷未承認を保持する。以下はCR-03修正時等の履歴。

## CR-03 修正後の独立再レビュー（現行）

gsd-execute-phase 05 の code-review ゲートとして、修正担当とは別の verifier が `pagefolio/ocr_dialog.py`、`tests/test_ocr_dialog_provider_refresh.py`、`tests/test_ocr.py` の差分と関連呼出先を standard の深さで確認した。版同期の `constants.py`・README・開発履歴・配布はじめに・`test_release_contract.py` も照合した。既存34ファイル監査の履歴を継承し、今回34ファイル全体を新規監査したとは扱わない。新規 critical/warning/info 各0、CR-03 fixed、open 0。

off の拒否は summary ボタン判定と `_on_summary` の双方にある。後者は app.settings と明示候補設定のどちらかが off なら、本文構築・プロンプト読込・キー確認・状態変更・thread起動より前で return する。通常再開では設定コピーを使用する既存契約を維持。`_apply_llm_settings` は先にメモリ更新・旧snapshot破棄・共通保存ownerを実行し、保存失敗でもprovider依存UIとsummary状態を更新する。offは旧provider/結果を保持しつつ、表示名off・モデル空にする。再有効化では新providerへ更新する。

追加12ケースは実メソッドを呼び、早期returnを本文構築の例外sentinel・キー/worker未呼出し・状態/結果identityで検証している。表示widgetだけはstubなので実視覚評価ではない。3 providerは旧local型・Claude型・Gemini型という問題の分岐を覆う。既存正常サマリ経路と保存失敗後ライブ更新も本文assertを確認した。JUnitの追加12/12と全2083/2083成功、before/after各147入力の現行一致を独立確認した（`05-REVERIFY-20261028.json`）。新規pytest/GUI/外部送信は行わず、同入力の既存実走を再利用した。

**反証確認:** appがoffでも候補設定だけ有効な呼出しはOR条件で拒否される。旧providerの型が残っても表示・summary能力だけでoffを迂回できない。試験fixtureのapp設定は実製品が常に持つ設定と同じ前提であり、fixture-onlyの偶然依存ではない。実行中に利用者が設定を切り替える操作は既存LLM設定ボタンのdisable境界を持つ。本修正を送信済み通信の取消保証へ拡張しない。

以下の「未解決1件」「独立ではない」「2071件」の記述は発見時/親限定レビュー時の履歴であり、本節が現行判定である。原本は `.planning/debug/ocr-off-summary-evidence/05-REVIEW-before.md`。DEP-05/owner_missing等の原因未解決、Phase 06人手110行not-run、新ビルド・出荷未承認は解除しない。

**2026-10-28 CR-03修正後追補:** v1.10.2のoffガードと表示修正を親エージェントが限定再レビューし、CR-03をfixedとした。修正前9件の回帰失敗を確認後、関連213 passed・単一native全件2083 passed/2 warnings/463.98秒/exit0、入力hash不変。証拠とレビュー範囲は `.planning/debug/ocr-off-summary.md`。独立再レビューではない。以下は発見時の記録として保持し、原本全体は `ocr-off-summary-evidence/05-REVIEW-before.md` に保存。W05b・現行ビルド・実機受入・出荷停止は未解除。

**レビュー日時:** 2026-10-28T06:01:09Z
**深度:** standard
**対象ファイル:** 34
**状態:** clean（CR-03修正後の追補。以下の発見時記録は履歴）

## Summary

前回レビューの CR-01・CR-02・WR-01 は修正済みの記録と現行の該当経路を照合し、fixed を維持した。追加の設定切替経路に、OCR を `off` にした後もサマリ作成が有効表示になる欠陥を1件検出した。今回の未解決指摘は BLOCKER 1件、WARNING 0件、INFO 0件。

`check evaluation-scope --phase 05 --since 172e993ea61a3b31ffb5a533964481a4dfdb6240 --raw` は `status: degraded`、`reason: no-task-commits-since`、`source: phase-range` を返した。そのため Phase 6 の配布・試験関連まで広がった27ファイルを対象に含め、未コミットで Phase 5 の通知や版記録へ影響する起動経路と試験補助の7ファイルも追加した。前回の21ファイルに関する判定は既存レビューを継承し、現行差分・関連呼出先を重点的に確認した。構造プリパスと外部レビューレーンの指定はない。

## Narrative Findings (AI reviewer)

### CR-03 — BLOCKER: OCR を無効にしても旧プロバイダでサマリを送信できる

**File:** `C:\Users\shdwf\work\project\PageFolio\pagefolio\ocr_dialog.py:1193-1201`、`C:\Users\shdwf\work\project\PageFolio\pagefolio\ocr_dialog.py:813-825`、`C:\Users\shdwf\work\project\PageFolio\pagefolio\ocr_dialog.py:2218-2253`、`C:\Users\shdwf\work\project\PageFolio\pagefolio\ocr_dialog.py:2375-2379`
**Issue:** OCR 完了後、開いたままのダイアログで LLM 設定を `off` にすると、`_apply_llm_settings` は旧 `provider` を保持する。一方、`_update_summary_btn_state` は設定値を確認せず、既存結果と旧 `provider.supports_text_prompt` でサマリボタンを有効にする。`_on_summary` にも `off` の入口ガードがない。旧 LM Studio provider の headless 実メソッド確認では `ocr_provider='off'` でもボタンが `['!disabled']`、cloud 判定が `False` となる。この場合キー確認を通過し、`_summary_worker` が旧 provider の `complete_text_ex(full_text, prompt)` を呼ぶため、無効設定後も OCR 本文を旧接続先へ送信できる。旧 Claude provider ではボタンが有効で表示名も旧 Claude のまま残り、クリック後に `off` の API キー欠落という誤通知を出す。
**Fix:** ボタン状態とサマリ入口の両方で有効設定の `ocr_provider == 'off'` を拒否し、無効時の表示名も設定値を優先する。旧 provider を保持する設計を続ける場合は、無効時にその能力・型を実行可否判定へ使わない。ローカル/クラウド両方で OCR 結果を得てから `off` に切り替える回帰を追加する。

```python
if self.app.settings.get("ocr_provider") == "off":
    self.summary_btn.state(["disabled"])
    return  # _update_summary_btn_state の冒頭

# _on_summary の状態変更・キー確認より前にも同じ off ガードを置く。
```

## 前回指摘の対応継承

| ID | 判定 | 根拠 |
|---|---|---|
| CR-01（BLOCKER） | fixed | `7bbb06c` の内側 Shortcuts 終了時の grab 復元、実 Tk の save/cancel/wm 回帰、利用者 H13 pass。 |
| CR-02（BLOCKER） | fixed | `7bbb06c` の可視時間・FIFO・最小化復帰、利用者 H14 pass。 |
| WR-01（WARNING） | fixed | `2654882` の入力先同一性判定。Entry 以外と None を verified と記録しない。 |

## 検証と限界

- 今回はコード・既存証拠の照合と上記 headless 実メソッド確認を行った。GUI と `pytest` は新規実行していない。
- 親の入力ハッシュ照合で再利用可能と確認された既存の全件試験は `2071 passed / 2 warnings / 480.86s / exit 0`（`.planning/debug/quality-gate-unblock-20261028/full.json`、`full.xml`、`environment.json`）。CR-03 の条件は既存試験で検出されていないため、全件成功を本指摘の解消根拠にはしない。
- 前回の H13/H14 は既存 CR-01/CR-02 の解消根拠であり、新規 CR-03 の確認ではない。Phase 6 の W05b 自動復帰、DEP-05/owner_missing などの未解決条件と出荷停止は本レビューでは解除しない。
- 製品・試験・版・共有状態は変更していない。レビュー記録だけを更新し、commit は行っていない。

---

_Reviewed: 2026-10-28T06:01:09Z_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
