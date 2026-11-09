---
phase: 04-startup-control
status: automated_passed_pending_verifier
reason: constructor-failure notice試験の時系列前提修正
---

# constructor通知の再検証

初回全件 `04-reverify-20261106-exe-closeout/` は2397 passed / 2 failed / 2 warningsで不合格。元2fixtureの66ファイルをhash照合して `.planning/debug/constructor-notice-dedup-20261106/` へ保全した。調査正本は `.planning/debug/constructor-notice-dedup-20261106.md`。

制御遅延2.1秒のREDでは最後の子が通知期限後981msに呼び出し、正当な新規表示を行っていた。修正は子7個のbootstrapを通知表示前へ移すready/release同期。元1800msの通知寿命・製品期限は変えず、呼出tickが元通知の表示〜期限内であることもassertする。遅延0/2.1秒×通常/legacyの4条件成功、他のconstructor条件5件も成功。全体Ruff check、149ファイルformat check、AST成功。新しい全件成功はまだ未確定。

## 必須ゲートの差分照合

- Nyquist: 既存04要件・タスク被覆を再利用。追加4条件は既存の重複抑制契約を同じ1800msで実測する。制御RED/4GREEN/他5件と、今後の単一全件を根拠にする。未実施をpassへ変えない。
- Security: 直前の不合格全件171入力からの変更は `tests/test_startup_windows.py` と `開発履歴.md` の2件だけ（`fix-input-scope.json`）。製品/起動/通知コード、依存、固定namespace、権限/原本隔離は不変。既存22 closed/open0を再利用し、未解除DEP-05・owner_missing・前景不一致等は解除しない。
- UI: 製品表示の変更なし。既存静的partialを再利用、追加captureなし、scoreはnullのまま。G3の人手受入は品質試験の代用にしない。
- Code review/disposition: 同期修正の独立差分レビュー待ち。既存CR-01/02解消、WR-01 deferredは保持。
- 独立verification: 新全件回収・レビュー解消後に所有CLIで再生成する。現行04は試験変更によりstaleになるため、過去passedを現在の合格と扱わない。

## 最新結果

`04-reverify-20261106-constructor-sync/` の単一全件は2401 passed / 2 warnings、失敗・error・skip0、629.77秒、exit0。171入力の実行前後/回収時は同一、別保存helper3入力も不変、標準エラー空。Ruff check/149 format/ASTもexit0。集約正本は `04-QUALITY-CONSTRUCTOR-20261106.json`。constructor同期の独立レビューは新規指摘0、既知deferredは保持した。独立verifierによる正式再生成はこの後に行う。

Phase05も開発履歴追記によるstaleを再生成する。Phase06のG3 9/9は変更前の入力での監査結果。`06-PYTHON-REUSE-AUDIT-20261106` でPython20行は不一致1/証拠不足19と判定され、旧passを保全して現行入力では再採取が必要。固定EXE10行の来歴は一致。全件成功を人手回答に転用せず、release_allowed=false。G4以降・commit・buildは開始しない。
