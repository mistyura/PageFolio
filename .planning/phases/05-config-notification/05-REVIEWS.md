---
phase: 05
reviewers: [claude, antigravity, grok]
reviewed_at: '2026-10-22T13:36:34.8899582Z'
plans_reviewed: [05-01-PLAN.md, 05-02-PLAN.md, 05-03-PLAN.md, 05-04-PLAN.md]
models:
  claude: "claude-opus-5-5 (reasoning=high)"
  antigravity: "unknown"
  grok: "grok-4.7"
model_sources:
  claude: "pinned"
  antigravity: "unknown"
  grok: "pinned"
---

# Cross-AI Plan Review — Phase 05

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## 実行結果と証拠の扱い

2026-10-22、指定された Claude・Antigravity・Grok を外部CLIの独立セッションで直列実行した。3者とも 05-01〜05-04 の全4計画について応答を取得した。製品コード、計画本文、承認済み決定は変更していない。これは計画レビューであり、Phase 5の実装・UAT合格を示すものではない。

| レビュアー | 結果 | 計画被覆 | モデル情報 | 証拠上の留意点 |
|---|---|---|---|---|
| Claude | 取得成功 | 4/4 | claude-opus-5-5 (reasoning=high)、設定指定 | ソース引用あり。重要な保存経路・既存テストの指摘を親で照合 |
| Antigravity | 取得成功 | 4/4 | unknown | ソース引用あり。モデル名は取得できず、Geminiの設定値から推定しない |
| Grok | 取得成功 | 4/4 | grok-4.7、設定指定 | ソース引用と末尾の「リポジトリは読んでおらず」が矛盾。全体判定は重みを下げ、親で照合した個別指摘のみ確認済みとして採用 |

初回sandbox実行は、ClaudeがECONNREFUSED、Antigravityが認証データ/ログへのアクセス拒否・通信制限、Grokが管理ポリシーロックへのアクセス拒否で実レビューを取得できなかった。それぞれ証拠を退避し、制限外で1回再実行して取得した。runnerの `ok: true` だけでは成功と判定せず、失敗本文・stub・被覆・引用を確認した。特にClaude初回は `stubbed: false` でも接続エラー本文のみであり、不成功として扱った。

ユーザーの再ログイン後の確認では `claude auth status` は `loggedIn: true`、`authMethod: api_key`、`apiKeySource: ANTHROPIC_API_KEY`。この環境ではAPIキー認証が優先されている。取得済みレビューはこの認証経路の成功結果であり、再ログインした別の認証経路を利用したとは断定しない。

## Consensus Summary

**判断: 計画への反映が必要。現時点で実装開始・Phase完了・コミットの合格とはしない。**

### Agreed Strengths

- 読込結果APIの追加と既存dict APIの互換維持、画面構築後の通知、読込失敗時の終了保存抑止は現状の起動順と整合する。`pagefolio/settings.py:301`、`pagefolio/app.py:149`、`pagefolio/ui_builder.py:187`。
- tmpへ書いてからreplaceする保存、機密キー除外、保存失敗時のメモリ値保持を維持する方針は妥当。`pagefolio/settings.py:314`。
- Appが通知状態を所有する方針と、01→02→03→04の直列依存、実EXE受入・版同期をPhase 6へ残す境界は共通して評価された。

### Agreed Concerns

| ID | 優先度 | 対象 | 指摘・根拠・反映方向 |
|---|---|---|---|
| CR-05-01 | HIGH | 05-02/03 | **変更していない操作を明示保存にしない。** Claude/Antigravityが指摘。`pagefolio/dialogs/plugin.py:238` の閉じる操作は無条件に `_reload_plugins` を呼び、`pagefolio/app.py:636` で保存する。単純にexplicit=Trueへ移すと、破損起動後に開いて閉じただけで既定値が原本を上書きする。toggle/rescan/closeの保存責務と再保存の条件を整理し、plugin.pyを変更・試験対象へ加える。親でコード照合済み。 |
| CR-05-02 | HIGH | 05-02/04 | **終了保存失敗で最初の終了を取り消す追加仕様を確定する。** 3者が指摘。計画自身が未承認の裁量と明記（`.planning/phases/05-config-notification/05-02-PLAN.md:134`）。`pagefolio/app.py:499` の終了確認と保存の順序、キャンセル後のフラグ、次の終了で保存を省略する条件を含めて判断する。単に即終了する代替案では通知が見えない問題が残るため、それだけでCFG-02達成としない。 |
| CR-05-03 | MEDIUM | 05-02/03 | **モーダル中の通知可視性と表示時間を保証する。** 3者が指摘。Toastはroot直下（`pagefolio/toast.py:66`）、設定/OCR/Pluginのgrabは `pagefolio/dialogs/settings.py:36`、`pagefolio/ocr_dialog.py:156`、`pagefolio/dialogs/plugin.py:27`。背後で10秒経過して見落とされる可能性を、表示開始・停止・再開の契約と試験に追加する。ソース上の構造は親で確認、実際の遮蔽はUAT未実施。 |
| CR-05-04 | MEDIUM | 05-03 | **保存owner変更に伴う既存テストの移行を計画へ追加する。** Claude/Grokが指摘し親で照合。`tests/test_ocr.py:895` のfake Appには `_persist_settings` がなく、`tests/test_pagination.py:467` は旧保存関数をpatchしてMixinをstubへ適用する。両ファイルは05-03のfiles_modified/局所verifyから漏れている。保存1回・メモリ保持等の意図を維持し、App経由の検証境界へ移す。provider_uiのcallbackなしstubとの互換条件も明示する。 |
| CR-05-05 | MEDIUM | 05-01/04 | **実App試験の隔離と後始末を具体化する。** 3者が指摘。設定JSONだけでなく外部プロンプト基準パス・独立したpluginsディレクトリをimport/初期化前に隔離する。Document/UndoBlobStore/after/after_idle/rootの後始末を、終了キャンセル経路でも保証する。プロセス内実Appが必ずクラッシュするという断定ではなく、隔離設計・teardownの要件として扱う。 |
| CR-05-06 | MEDIUM | 05-02 | **通知イベント切替とプログラム的dismissの遷移を明示する。** Antigravity/Grokが指摘。`pagefolio/toast.py:48` の同カテゴリ早期return、`:57` のdismissを改修する際、旧timer/on_closeの残留を防ぎ、PDF/印刷の成功dismissでも待機通知を再開する。計画には既に消化後after_idle・世代guard・ボタン状態同期があるため、新規欠陥の断定ではなく既存契約を具体的な遷移試験へ落とす。 |
| CR-05-07 | MEDIUM | 05-04 | **formatコマンドを実証済みの対象範囲と一致させる。** 3者が指摘。計画は無限定の `ruff format .`（`.planning/phases/05-config-notification/05-04-PLAN.md:118`）、同日の記録はPython限定includeで成功（`05-PLANNING-CHECKS.md:50`）。pyproject.tomlは変更せず、既存のCLI対象限定と整形後lintを計画へ明記する。今回はformat自体を実行していない。 |

### Divergent Views

- **通知FIFOと集約:** Claudeは無制限FIFOをHIGH、他2者は主にライフサイクル設計として評価した。D-09/D-16は保存失敗を毎回残す決定であり、計画のFIFOを直ちに誤実装とは断定できない。一方ROADMAP成功条件4の「集約」と、100回失敗なら最大1000秒滞留する表示設計の関係は明確化が必要。件数表示への合併や黙った破棄は、このレビューだけで採用しない。
- **corruptとunreadableの上書き許可:** ClaudeはD-13が破損ファイルのみを述べるのにunreadableまで許可を拡張する点を指摘。他2者の明示的な反対/賛成はない。一時ロック後に正常ファイルを既定値で上書きする条件を定義し、D-13の適用範囲を確認する。
- **型不正・BOM:** Claude/Antigravityはdict内部の型不正を指摘、BOMはClaude単独。全面的な設定スキーマ追加へ自動拡大せず、起動に必要な型の最小検証と対象外の明示を検討する。BOM許容も互換性改善案として区別する。
- **LLM互換fallback:** Claudeは一般callback経由のUI再構築を避けて簡素化する案、Grok/Antigravityはcallback有無を防御する案。製品経路とテスト専用stubを区別し、外側Cancel時のLLM即時保存という既存意図を保持する。
- **補助harnessの配置:** Claudeはplanningアーカイブ時にテスト依存が切れる懸念を挙げた。恒久テスト用helperと開発用起動入口の責務を分ける案を検討するが、未来の移動で必ず壊れるという実測結果ではない。

### 親による補正・範囲の限定

1. Grokの「exists分岐を除去すべき」は既に05-01-02に `openを正本` として記載済み（`05-01-PLAN.md:129`）。追加の必須仕様欠落ではなく実装時の確認事項。
2. Grokの「製品呼出し10か所」は列挙すると11の低層呼出し点。ネストLLMの二重保存をまとめた10操作経路と、現行呼出し点数を混同しない。
3. AntigravityのPLAN参照にある1005/1330等は元ファイルの行ではない。終了裁量は `05-02-PLAN.md:134`、formatは `05-04-PLAN.md:118` を正本とする。原文は改変せず下段に保存する。
4. 「値が変わった時だけ保存」は、失敗後に同じ値で再保存する明示操作を妨げないよう設計する。単純な直前のメモリ値比較だけでは未永続化の再試行を抑止し得る。no-op操作と意図的な再保存を区別する。
5. Claudeのショートカット巻き戻り指摘は、設定画面のコピー（`pagefolio/dialogs/settings.py:39`）、別画面によるApp辞書更新（`pagefolio/dialogs/shortcuts.py:280`）、外側Applyによる辞書置換（`pagefolio/app.py:688`）から成立する可能性を確認した。実操作による再現は未実施。今回のレビューで無断修正せず、別件かPhase 5へ含めるかを後続で判断する。
6. AGY/Grokの型不正、Tk可視性、後始末、tmp競合等は、それぞれ根拠と未実測のリスクを分ける。レビュー原文の強い断定を、そのまま検証済み欠陥に昇格しない。

## 検証・コミット判断

- sandbox全件: **36 failed, 1575 passed, 24 errors, 3 warnings / 183.31秒 / exit 1**。Tcl初期化不可とWindows子プロセス失敗を観測。
- 制限外の単一全件: **1 failed, 1634 passed, 0 errors, 1 warning / 354.41秒 / exit 1**。
- 失敗: `tests/test_startup_windows.py::test_focus_restore_real_main_windows[normal-entry-script]`。`_finish` の `child.communicate(timeout=12)` が期限超過し「子process が12秒以内に終了しない」。原因未確定で、環境要因・製品欠陥のいずれとも断定しない。
- 制限外コマンド: `.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_phase5_review_20261022_02"`。
- 旧DEP-05-REGRESSIONの1635 passedは過去の解除証拠として保持するが、今回の全件失敗を上書きしない。計画05-04の再発時停止条件に従い、実装開始前に独立debugで再評価し、単一全件合格の現行証拠を揃える必要がある。本レビューでは状態ファイルや過去の解除記録を書き換えない。
- AGENTS.mdのコミット前pytest合格条件未達のため、レビュー成果物のコミットは保留。テストのskip/除外・製品修正は行っていない。
- Python編集なしのためruff/ASTは今回のレビューでは未実施。レビュー構造、4/4被覆、モデルメタデータ、計画SHA-256不変、証拠コピーのSHA-256一致、diffチェックを別途確認する。

証拠保存先: [.review-diagnostics/20261022T133806Z-gsd-review-WAaQxg/](.review-diagnostics/20261022T133806Z-gsd-review-WAaQxg/)。各レビュアー原文・失敗時記録・結果JSON・検証記録・計画hashを保存。入力プロンプトと計画コピーは含めない。

## 次の作業

1. `$gsd-plan-phase 5 --reviews` で本報告の確認済み指摘と仕様確認事項を計画へ反映する。レビューだけで計画修正や実装の承認済み扱いにはしない。
2. 既存Windows起動テストの今回の失敗を独立GSD debugで扱い、DEP-05-REGRESSIONの再充足を確認する。
3. 仕様の未確定事項と回帰ゲートを解消後に、Phase 5の実装・検証へ進む。

## Reviewer Responses

以下は各CLIの取得原文。親の補正・証拠評価は上記を優先する。

## Claude Review

# PageFolio Phase 5 計画レビュー（05-01〜05-04）

4計画の記述を実ソース（`pagefolio/settings.py`、`app.py`、`toast.py`、`ui_builder.py`、`dialogs/settings.py`、`dialogs/shortcuts.py`、`dialogs/plugin.py`、`ocr_dialog.py`、`redact_ops.py`、`viewer.py`、`__main__.py`）と既存テストに照らして確認しました。計画が前提にしている現状の把握はおおむね正確です。一方で、**「明示保存」の判定**、**通知の集約**、**既存テストへの影響範囲**の3点に、そのまま実行すると要件違反やゲート失敗につながる穴があります。

---

## 05-01

### Summary
読込結果 API（`SettingsLoadResult`）、App が持つ通知キュー、再試行ボタンなし・期限付きの Toast、読込失敗時の終了保存抑止を、破損設定から実 App まで一続きの経路で検証する計画です。現状の把握は正確です。ただし、BOM 付き JSON の誤分類、読取不能（unreadable）への D-13 の適用、実 App をテストプロセス内で構築するリスクの3点が詰め切れていません。

### Strengths
- `_load_settings()` が例外を握りつぶしている点（`settings.py:301-311`）、`_load_settings` が `_build_ui` より先に呼ばれる点（`app.py:149` → `214-216`）、Toast が `_build_ui` 内で毎回生成される点（`ui_builder.py:187`）を正しく捉え、通知を `after_idle` に遅らせる設計は妥当です。
- 辞書を返す互換 wrapper を残す方針は、既存テスト `tests/test_utils.py:21-57` や `tests/test_settings_keyguard.py:275-289` が戻り値を辞書として使っている事実と整合します。不正 JSON で既定値に戻すテスト（`test_utils.py:50-57`）もそのまま通ります。
- `_quit` が終了確認より先に `_save_window_state` を呼ぶ（`app.py:499-500`）という落とし穴を特定し、終了の Yes/No 両方の分岐で書込0件を検証する設計になっています。
- Toast の retry を任意化し、既定の duration を None にすることで、PDF 保存・印刷の既存の再試行契約（`toast.py:48-55`, `80-87`）を壊さない方針です。

### Concerns
- **MEDIUM — BOM 付き UTF-8 が「破損」と誤分類される。** 読込は `encoding="utf-8"`（`settings.py:304`）なので、BOM があると `json.load` が JSONDecodeError を出します。`docs/CONFIGURATION.md:331` は JSON の直接編集を案内しており、外部プロンプト読込は既に `utf-8-sig` を許容しています（`settings.py:56-58` の説明）。誤って「破損」と表示されたうえ、05-02 の D-13（明示保存は確認なしで上書き）と組み合わさると、利用者が手で直した設定が既定値で上書きされます。
- **MEDIUM — 読取不能（unreadable）にも「明示保存で上書き可」を適用している。** D-13 の対象は「破損ファイルの上で」です。一方、計画は corrupt と unreadable の両方で保護を同じ扱いにし、明示保存で解除します（05-02-01）。AV スキャンや他プロセスの一時ロックで起動時だけ読めなかった**正常な**設定に対し、利用者がサムネイル倍率を一度変えるだけで、全設定が既定値で置き換わります。これは V110-CFG-03 の「無断上書き」にあたります。
- **MEDIUM — 実 App をテストプロセス内で構築する前例がない。** `tests/` 配下で `PDFEditorApp(root)` をプロセス内で生成しているテストはありません（grep 0件）。Phase 4 は subprocess に分け、import 前に `settings._get_base_dir` と `plugins._get_plugins_dir` を差し替えています（`tests/test_startup_windows.py:1434-1445`）。プロセス内の実 App は `root.after(200, …)`（`ui_builder.py:182`）などの予約を残します。CLAUDE.md の症状①（TclError の再発）が出ている単一プロセス全件ゲートの不安定要因になり得ます。また、プラグインのパス解決は `settings._get_base_dir` とは別関数（`plugins.py:21-29`）なので、「パス解決だけを差し替え」と書くだけでは隔離漏れが起きます。
- **LOW — 隠し root（withdraw）では focus/grab 不変の assert が空振りしやすい。** Windows では非前面時に `focus_get()` が None になりやすく、検証として意味をなさない可能性があります。
- **LOW — 型が不正な値は対象外のまま。** `"font_size": "abc"` のような値は、`app.py:150-152` や `587-589` の加算で TypeError になり、通知を出す前に起動が落ちます。範囲外なら、その旨を明記した方が安全です。

### Suggestions
- 読込は `utf-8-sig` にし、BOM 付きを ok に分類するテストを追加する。
- unreadable の扱いをユーザーに確認する。案は「保護を維持し、最初の明示保存の直前に再読込を試みる」または「unreadable では明示保存でも保護を解除しない」。
- TestLoadTracer は Phase 4 の `_spawn`/`_run_scenario` と同じ subprocess 方式にする。プロセス内で行う場合は teardown（after の取消・`doc.close`・`_clear_undo_stacks`・`root.destroy`）を必須条件に加える。差替え対象として `settings._get_base_dir` と `plugins._get_plugins_dir` の両方を明記する。

### Risk Assessment
**MEDIUM**。設計の骨格は正しい一方、誤分類と D-13 の拡大解釈は利用者の設定を失う方向の欠陥です。

---

## 05-02

### Summary
`_save_settings` の bool 化と tmp の後始末、`_persist_settings` による明示保存と自動保存の区別、FIFO 通知のライフサイクル（期限、割込み、再構築からの復元）を導入する、Phase の中心となる計画です。原子的置換と機密キー除外の維持は正確です。ただし **(1) 明示保存の判定が実際の UI 呼出しと合っていない、(2) 集約しない FIFO が ROADMAP の成功条件4と衝突する、(3) 終了を取り消す裁量が未承認の挙動変更である**、の3点が HIGH です。

### Strengths
- 現状の保存は `tmp → os.replace` で、失敗は握りつぶし、cleanup はありません（`settings.py:328-343`）。この把握は正確で、同じ順序を保ったまま bool 化する方針は最小限の変更です。既存の `test_utils.py:398-407`（例外を出さないこと）とも両立します。
- `_SENSITIVE_KEYS` のコピー除外（`settings.py:318-327`）の維持と、秘密 sentinel を使った試験の設計は適切です。
- `_apply_settings` が保存の成否と無関係に `status_settings` を表示する点（`app.py:693-695`）を特定し、成功時だけ表示する条件に変えます。
- `_rebuild_ui` が root の子をすべて破棄する点（`app.py:700-701`）を踏まえ、破棄の前に `dispose(reason="rebuild")` して世代を進める設計は正しいです。

### Concerns
- **HIGH — 「明示保存」の判定が実際の呼出し経路と合っていない（V110-CFG-03 違反の経路が残る）。**
  - `PluginDialog._close` は、変更がなくても必ず `self.app._reload_plugins()` を呼びます（`dialogs/plugin.py:238-240`）。破損設定で起動したあとプラグイン画面を開いて閉じるだけで、既定値の設定が破損ファイルを上書きします。D-13 の前提は「利用者が設定を変更して明示的に保存した場合」です。
  - スライダーの保存は `<ButtonRelease-1>` に結び付いています（`ui_builder.py:240`, `681`）。値を動かさずクリックしただけでも保存が走り、同じ上書きが起きます。
  - プラグインの切替は `_toggle` → `_reload_plugins`（`plugin.py:216`）と、閉じる時の再保存（`plugin.py:239`）の2回保存になります。失敗時は1操作で2件通知されます。05-03 の「一操作一実保存」とも矛盾します。
- **HIGH — 集約しない FIFO が ROADMAP の成功条件4（「同じ設定エラーが続いても通知が集約され」）と衝突する。** 計画は「同文言の合併をしない、上限で捨てない、各10秒」と定めています。保存先が書込不可で失敗が続く場合（frozen 時は exe と同じフォルダが保存先。`settings.py:40-42`）、スライダーを10回離すと約100秒分の通知が順番待ちになります。これは V110-CFG-04 の「重複通知…で編集操作を妨げられない」にも反します。D-16 の「それぞれ通知が残る」の解釈が、成功条件の文言と食い違っています。
- **HIGH — 終了取消の裁量は未承認の挙動変更。** 計画は、通常起動で終了時保存に失敗すると、最初の終了操作を取り消します（`_quit`, `app.py:499-508`）。書込不可の場所に置かれた EXE では、毎回のセッションで最初の ✕ が効かなくなります。計画自身が「未承認」と明記しており、実装前にユーザーの判断が必要です。終了しようとしている利用者にとって通知の実益は小さく、「通知を出したうえで終了は続ける」案も比較材料として提示すべきです。
- **MEDIUM — 通知が見えないまま期限切れになる。** Toast は root の右下に `place` されます（`toast.py:67`）。OCRDialog や SettingsDialog（`grab_set`、`dialogs/settings.py:36`）などの Toplevel が覆っていても、10秒のタイマーは進みます。また PDF 保存・印刷の Toast には期限がないため、それが出ている間、設定通知は無期限に待たされます。
- **LOW — tmp 名の衝突。** `path + ".tmp"` は固定名です。設定ファイルは exe と同じフォルダにあり、別ログインセッションの同時起動は Phase 4 でも許容されています。新しく追加する unlink が、他のプロセスが書いている途中の tmp を消す可能性があります。

### Suggestions
- 明示保存の条件を「保存対象の値が実際に変わった時」に限定する。保存前後の差分で判定するか、スライダーは値の比較で no-op にする。`PluginDialog._close` は `explicit=False` 扱いにするか、変更がなければ保存しない。この境界のテストを TestLoadProtection／TestSaveFlow に追加する。
- 同一原因の通知は「表示中の1件を件数付き（例：×3）で更新し、時間を延長しない」形に集約し、D-16 は件数表示で満たす案をユーザーに確認する。
- 終了取消の採否をユーザー確認に回す。不採用なら「通知を出してそのまま終了」とし、05-04 の説明文と UAT 項目を連動させる。
- 表示時間は、root が前面・可視でモーダルが掛かっていない時だけ進める。待機中は `_set_status` で補助的に知らせることも検討する。
- tmp は `tempfile.mkstemp(dir=同じディレクトリ, prefix=…)` で一意にし、自分が作ったファイルだけを cleanup する。

### Risk Assessment
**HIGH**。上記の HIGH 3件はいずれも、要件の文言（CFG-03 と成功条件4）への違反、または未承認の挙動変更に直結します。

---

## 05-03

### Summary
残る保存元（言語、プラグイン、LLM 2経路、ショートカット、モザイク、サムネイル2種）を `_persist_settings` に寄せ、LLM の二重保存を解消する計画です。二重保存の特定は正確です。ただし **既存テストのスタブが壊れることが `files_modified` に入っていない**こと、互換のための fallback が危険な経路を作ることが問題です。

### Strengths
- LLM の二重保存の指摘は正確です。`dialogs/settings.py:230-240` で `_save_settings(self.current_settings)` を呼んだ直後に `on_llm_apply` が呼ばれ、`app.py:678-679` で再度保存されます。
- 保存に失敗しても `_update_ocr_buttons_state`（`app.py:684`）や provider の再生成（`ocr_dialog.py:1043-1069`）を省略しない方針は、D-08 と整合します。
- AST を使った保存元の棚卸しで、今後の通知漏れを防ぐ発想はよいです。

### Concerns
- **MEDIUM（実行時に必ず表面化）— 既存テストの破損範囲が漏れている。**
  - `tests/test_ocr.py:895-898` の fake app は `SimpleNamespace(settings, _session_api_keys)` だけです。`_apply_llm_settings` が `app._persist_settings` を呼ぶと AttributeError になります。さらに `test_ocr.py:960-982` は `settings_mod._save_settings` が1回呼ばれることを検証しています。
  - `tests/test_pagination.py:467-497` は SimpleNamespace のスタブで `ViewerMixin._on_page_size_change` を呼んでおり、`self._persist_settings` がないため失敗します。
  - 上の2ファイルは 05-03 の `files_modified` に含まれていません。単一プロセスの全件ゲートが赤になり、コミットが止まります。
  - `tests/test_provider_ui.py:1702-1737` は「ダイアログ層で `_save_settings` が呼ばれる」ことを検証しています。保存の責務を App 側へ移すと、この期待は成り立ちません。計画の「期待値を弱めず」と矛盾するため、テストの意図（ネスト Apply → 外側 Cancel でも永続化される）を保ったまま、検証する境界を移す書き換えが必要です。
- **MEDIUM — SettingsDialog の互換 fallback は過剰で、危険な経路を作る。** 製品では `_open_settings` が常に `app` と `on_llm_apply` を渡しています（`app.py:657-666`）。「両方ない場合は一般 callback に重ねた辞書を渡す」経路の callback は、製品では `_apply_settings` です。これが `_rebuild_ui` を呼ぶと root の子をすべて破棄し（`app.py:700-701`）、開いている SettingsDialog／LLMConfigDialog の Toplevel まで消えます。`_initial_settings` を追加する必要も生じます。
- **MEDIUM — 既存の不具合（発見事項）。** SettingsDialog は開いた時点の設定をコピーします（`dialogs/settings.py:39`）。ShortcutsDialog は `app.settings["shortcuts"]` を書き換えて保存します（`dialogs/shortcuts.py:280-285`）。その後に外側の「適用」を押すと、`_apply_settings` が古いショートカットで `self.settings` を置き換えて保存します（`app.py:688`, `693`）。セッション中のキー割当は残るのにディスク上は元に戻り、次回起動で変更が消えます。保存失敗ではありませんが、「次回起動に残らないのに知らされない」という Phase 5 が防ごうとしている症状そのものです。範囲外として黙って見過ごさず、記録するかユーザーに判断を仰ぐべきです。
- **LOW — AST の棚卸しの検出範囲。** `_save_settings(...)` という Name 呼出しだけを数えると、`settings_mod._save_settings(...)` のような属性呼出しや、`pagefolio/__init__.py:34` の再エクスポートを経由したプラグインからの呼出しを見逃します。

### Suggestions
- `tests/test_ocr.py` と `tests/test_pagination.py` を `files_modified` に追加し、スタブに `_persist_settings`（呼出しを記録して bool を返す）を持たせる。
- fallback は「owner がなければ `current_settings` だけを更新し、外側の Apply で永続化する（warning ログ）」に簡素化し、`_initial_settings` を不要にする。
- ショートカットが元に戻る件は、05-03 の範囲で直すか別 issue に切り出すかをユーザーに確認し、どちらにしても記録を残す。
- AST の検査は `ast.Attribute` と `ast.Name` の両方を対象にする。

### Risk Assessment
**MEDIUM**。方向性は正しいものの、テストの影響範囲の見落としで実行が確実に止まります。fallback は不要な危険を持ち込みます。

---

## 05-04

### Summary
複合操作の受入テスト、隔離した手動確認用 harness、証拠記録、説明文書、最終ゲートをまとめる計画です。not-run を pass と混同しない姿勢や、Phase 6 との境界は適切です。ただし harness の置き場所と、format コマンドの扱いに具体的な問題があります。

### Strengths
- 実設定・プロンプトの SHA-256 を実行前後で比較する方式は、Phase 4 の autouse fixture（`tests/test_startup_windows.py:33-53`）と同じ考え方で、実績があります。
- ACL を変えずに I/O 障害を注入する方針、`bound_doc` 回帰の維持、版番号の同期を Phase 6 に残す境界はいずれも妥当です。

### Concerns
- **MEDIUM — harness を `.planning/phases/05-config-notification/05-NOTICE-HARNESS.py` に置き、テストがそこに依存する設計。** マイルストーン完了時には phases が `milestones/` へ移されます（v1.9.0 の前例は `.planning/milestones/v1.9.0-phases/`）。移動した時点で `TestScenarioIsolation` が import できなくなります。ファイル名もハイフンを含み、通常の import ができません。
- **MEDIUM — `ruff format .` をそのまま実行すること。** DEP-05 の解除記録では、Ruff が Markdown のコード例にも適用されるため include を限定した override で実行しています（`05-PLANNING-CHECKS.md:50`）。override なしで実行すると、`.planning` の md や `docs/CONFIGURATION.md` が書き換わる恐れがあります。また format は変更を伴うコマンドで、検証には `--check` が適しています。
- **LOW — human-check の「エージェントが起動し…確認する」。** 入力先が奪われないか、文言が読めるかは人が判断する項目です（`05-VALIDATION.md` の Manual-Only 表と不整合）。実施者を明記してください。
- **LOW — 作業ツリーの衛生。** `開発履歴.md` と `requirements.txt` には既に無関係な未コミット変更があります（git status）。前者を Phase 5 でコミットすると無関係な差分が混ざります。後者が未確定のままでは、全件ゲートの証拠環境（DEP-05 記録にも「未コミットの依存更新を含む環境」とある）を再現できません。
- **LOW — ROADMAP の表記不一致。** 進捗表が「0/TBD」（`ROADMAP.md:229`）のままで、「Plans: 4 plans」（`ROADMAP.md:174`）と食い違っています。

### Suggestions
- harness は `tests/helpers/config_notice_harness.py` などに置き、開発時の起動は `python -m tests.helpers.config_notice_harness --scenario …` とする。隔離は Phase 4 の `_run_scenario` と同じ差替え（`settings._get_base_dir` と `plugins._get_plugins_dir`）を使う。
- format は DEP-05 と同じ override で実行し、そのうえで `ruff format --check` を確認手段にする。
- `requirements.txt` の quick 作業（261022）は、Phase 5 の実行前に決着させる。

### Risk Assessment
**LOW〜MEDIUM**。製品挙動への影響は小さい一方、harness の置き場所がマイルストーン完了時にテスト破損を起こす、時限式の問題です。

---

## 全体のまとめ

| # | 重大度 | 対象 | 要旨 |
|---|---|---|---|
| 1 | HIGH | 05-02/03 | 変更なしの保存（`plugin.py:238-240`、スライダーの ButtonRelease）が「明示保存」扱いになり、破損ファイルを既定値で上書きする |
| 2 | HIGH | 05-02 | 集約しない FIFO が ROADMAP の成功条件4（集約）と V110-CFG-04 に反し、失敗が続くと通知が分単位で滞留する |
| 3 | HIGH | 05-02 | 終了取消の裁量は未承認で、書込不可の配置では毎回のセッションで最初の終了が効かない |
| 4 | MEDIUM | 05-03 | `test_ocr.py` と `test_pagination.py` のスタブ破損が `files_modified` から漏れ、全件ゲートが赤になる |
| 5 | MEDIUM | 05-01/02 | unreadable にも D-13 を適用したため、一時ロックで正常な設定を失う |
| 6 | MEDIUM | 05-01 | BOM 付き JSON が「破損」と誤分類される |
| 7 | MEDIUM | 05-04 | harness を `.planning` に置いたため、マイルストーン完了時にテストが壊れる |
| 8 | MEDIUM | 05-03 | ショートカットが外側 Apply で元に戻る既存の不具合（発見事項） |

**依存の順序**は 01→02→03→04 の直列で妥当です。DEP-05 は充足済みと確認しました（`05-VALIDATION.md:34`、commit `8689c27` がログに存在）。**セキュリティ**面の機密キー除外とログへの非出力は、既存のガードを維持する設計で問題ありません。**性能**は軽微です。保存は小さい JSON であり、毎回の書込は現状と同じです。

**実行前に解消すべき事項：**
- **ユーザー判断が要る3点**：
  - D-16 と成功条件4の調停（通知の集約方式）
  - 終了取消の採否
  - unreadable 時の扱い
- **計画の修正で済む3点**：
  - 「値が変わった時だけ明示保存」とする判定の追加
  - 05-03 の `files_modified` へのテストファイル追加
  - harness の置き場所の変更

これらを反映しないまま実行すると、Phase の目標である「元の設定ファイルを失わない」と「通知が編集を妨げない」の両方に、検証をすり抜ける経路が残ります。


---

## Antigravity Review

## 05-01

### 1. Summary
`05-01-PLAN.md` は、設定ファイル `pagefolio_settings.json` の読込結果分類（`ok` / `missing` / `corrupt` / `unreadable`）の導入、画面構築後の非モーダルトースト通知、および読込失敗時の終了時自動保存抑止（原本保護）を Wave 1 として実装する計画である。既存の辞書戻り値 API（`_load_settings()`）の後方互換性を維持しつつ `_load_settings_result()` を新設する設計や、`_quit()` 内の確認ダイアログ前に呼ばれる `_save_window_state()` を抑止対象に含めている点は、リポジトリの実装構造とよく整合している。一方で、JSON ルートが辞書であっても内部の型が破損している場合の起動時例外防止や、`_build_ui()` と `_rebuild_ui()` の間で `after_idle` コールバックが競合するエッジケースについて、Wave 1 時点での防御条件を明確にする余地がある。

### 2. Strengths
- **既存 `_load_settings()` 呼び出し元・単体テストとの高い後方互換性**: `pagefolio/settings.py:254-311` の `_load_settings()` は辞書を直接返し、`pagefolio/app.py:149-153` や `tests/test_settings_keyguard.py:224-291` が戻り値へ直接添字アクセス・`.get()` を行っている。`SettingsLoadResult(settings, status)` を返す `_load_settings_result()` を新設し、`_load_settings()` をその `.settings` を返すラッパーとして残す設計により、既存テスト資産を壊さずに状態分類を導入できている。
- **UI 構築順序（`_load_settings` → `_build_ui`）に即した通知タイミング設計**: `pagefolio/app.py:149` で `_load_settings()` が呼ばれる時点では、まだ `self._build_ui()`（`pagefolio/app.py:215`）が実行されておらず、`self._toast = ToastManager(self)`（`pagefolio/ui_builder.py:187`）も存在しない。通知イベントを `PDFEditorApp` のキューに一旦保持し、初回 `_build_ui()` / `_build_menubar()`（`pagefolio/app.py:215-216`）完了後に `after_idle` で表示する設計は、V110-CFG-01（「画面構築後の通知」）と実際の初期化順序に正確に対応している。
- **終了確認ダイアログより前に走る `_save_window_state()` の抑止**: `pagefolio/app.py:499-508` の `_quit()` は、502行の `messagebox.askyesno`（終了確認）より前の 500行で無条件に `self._save_window_state()`（`pagefolio/app.py:575-585`）を呼び出し、585行で `_save_settings(self.settings)` を実行している。読込失敗直後から `_settings_autosave_blocked = True` として `_save_window_state()` のディスク書込を抑止し、終了確認で「いいえ（キャンセル）」を選んだ場合も原本不変を検証する計画（`05-01-02`）は、実コードの落とし穴を的確に捉えている。

### 3. Concerns
- **[MEDIUM] ルートが辞書 `{}` だが内部キーの型が不正な JSON に対する起動時耐性 (`pagefolio/settings.py:172, 305-308`, `pagefolio/app.py:150-187`, `pagefolio/ui_builder.py:110`)**:
  `pagefolio/settings.py:305-307` は `data = json.load(f)` の後に `for k, v in defaults.items(): data.setdefault(k, v)` を実行する。`05-01-02` では「JSONDecodeError、UnicodeDecodeError、辞書以外の root は `corrupt`」と定義しているが、ルートが辞書であっても手編集等で内部の型が壊れている場合（例: `{"font_size": "large"}` や `{"prompt_templates": []}`）、`setdefault` では既定値に置き換わらない。その結果、`pagefolio/ui_builder.py:110` の `int(self.font_size * 5.5)` で `TypeError`/`ValueError` が発生したり、`pagefolio/settings.py:172` の `_ensure_template_shape`（`tpl.setdefault("active", "")`）で `AttributeError` が発生したりして、画面構築完了前に起動がクラッシュするリスクがある。
- **[MEDIUM] 初回 `_build_ui` 後の `after_idle` と直後の `_rebuild_ui()` の競合 (`pagefolio/app.py:215-216, 598-603, 697-722`, `pagefolio/ui_builder.py:187`)**:
  `05-01-01` では「`_build_ui`/`_build_menubar` 完了後に `after_idle` で実 Toast へ渡す」としているが、`_build_ui()` は起動時（`pagefolio/app.py:215`）だけでなく `_rebuild_ui()`（`pagefolio/app.py:715`）からも呼ばれる。また、`after_idle` が発火する前に `_toggle_lang()`（`pagefolio/app.py:598`）等で `_rebuild_ui()` が走ると、`pagefolio/app.py:700-701` で旧ウィジェットが破棄され、`pagefolio/ui_builder.py:187` で `self._toast` が新インスタンスに差し替わる。世代管理（`_config_notice_generation`）の本実装は `05-02-02` に割り当てられているため、`05-01` 時点で `_show_next_config_notice()` が最新の `self._toast` を参照し、既に表示中または破棄済みの状態を安全に判定するガードが必要である。
- **[LOW] `os.path.exists(path)` 除去後の Windows 特有の `OSError` サブクラス分類 (`pagefolio/settings.py:303-305`)**:
  現行の `pagefolio/settings.py:303-304` は `if os.path.exists(path): with open(path, ...)` となっている。`05-01-02` で `os.path.exists` を廃して `open()` を単一の判定点とするのは TOCTOU 回避として適切だが、Windows 環境で `pagefolio_settings.json` と同名のディレクトリが存在する場合、`open()` は `IsADirectoryError` ではなく `PermissionError`（`OSError` のサブクラス）を送出する。これが意図どおり `unreadable` として分類され、クラッシュせず既定値で起動することを境界テストに含めるとより堅牢になる。

### 4. Suggestions
- `pagefolio/settings.py:305-308` の `_load_settings_result()`（または `PDFEditorApp.__init__` の `font_size` / `lang` / `theme` 取り出し部、`pagefolio/app.py:150-153`）において、`font_size` が `int`（かつ bool でない）か、`lang` が `LANG` の有効キー（`"ja"` / `"en"`）か、`prompt_templates` が `dict` かといった最小限の型正規化（または不正型検出時の `corrupt` 判定＋既定値フォールバック）を入れることを推奨する。特に `self.lang` が未知の文字列になると `pagefolio/dialogs/settings.py:32` や `pagefolio/dialogs/plugin.py:23` の `LANG[lang]` で `KeyError` が発生する（`pagefolio/app.py:596` の `_t()` は `.get()` だがダイアログ類は直接添字アクセスしている）。
- `05-01-01` で登録する初回 `after_idle` は、`_build_ui()` 内部ではなく `PDFEditorApp.__init__` の `_build_menubar()` 直後（`pagefolio/app.py:216` の後）でスケジュールし、コールバック側（`_show_next_config_notice`）では常にその時点の `getattr(self, "_toast", None)` と `self.root.winfo_exists()` を確認する実装にすることを推奨する。

### 5. Risk Assessment
- **Risk Level: LOW**
- **Justification**: 変更対象が `settings.py`・`app.py`・`toast.py`・`lang.py` の初期化と終了抑止に限られており、既存の `_load_settings()` 辞書互換ラッパーと `ToastManager` の `retry_cb` 任意化によって既存機能を壊すリスクが低い。上記の内部型バリデーション（特に `lang` と `font_size`）を押さえれば安全に実装可能である。

---

## 05-02

### 1. Summary
`05-02-PLAN.md` は、`_save_settings()` の `bool` 戻り値化と `.tmp` クリーンアップ、`PDFEditorApp._persist_settings()` による保存結果・保護解除の一元管理、および連続する保存失敗・UI 再構築（`_rebuild_ui`）・PDF 保存/印刷トーストとの競合に耐える通知 FIFO ライフサイクルを実装する計画である。原子的書込み失敗時の `.tmp` 残留防止（D-12）や、`_apply_settings()` 失敗時の偽成功ステータス抑止（D-07）はソースコードの課題に正確に対応している。ただし、未承認の裁量判断として追加された「通常終了時の `_save_window_state()` 失敗で初回終了をキャンセルする」仕様には UX・ライフサイクル上の懸念（HIGH）があり、また `ToastManager.show()` の同一カテゴリ文言更新ロジックとの整合にも注意が必要である。

### 2. Strengths
- **原子的書込み失敗時の `.tmp` クリーンアップと機密キー保護の両立**: 現行の `pagefolio/settings.py:318-343` は `_SENSITIVE_KEYS` を除外したコピー `to_save` を `path + ".tmp"` に書き出してから `os.replace(tmp_path, path)` を呼ぶが、`json.dump` 途中や `os.replace` で失敗した際に `.tmp` が残留し、かつ呼び出し元に `None`（成功と同区別不能）を返していた。これを `bool` 戻り値＋例外時の `.tmp` 削除（削除失敗時も原本不変かつ `False` 返却）に改める設計は D-12・V110-CFG-03 を確実に満たす。
- **`_apply_settings()` における UI 再構築とステータス表示の精密な分離**: 現行の `pagefolio/app.py:686-695` は `_save_settings(new_settings)` の成否にかかわらず `self._rebuild_ui()` の直後に `self._set_status(self._t("status_settings"))`（`pagefolio/lang.py:276`「設定を変更しました」）を上書き表示している。保存失敗時でもメモリ上のテーマ・フォント・言語反映と `_rebuild_ui()` は継続しつつ（D-08）、`status_settings` の表示だけを成功時に限定する設計（`05-02-01`）は、`_rebuild_ui()` 内の `_build_ui()`（`pagefolio/ui_builder.py:136`）が `status_var` を `status_initial` に初期化する挙動とも綺麗に噛み合う。
- **UI 再構築と他カテゴリトースト割込みに対する通知寿命の分離**: `pagefolio/app.py:700-701` の `_rebuild_ui()` は `self.root.winfo_children()` を全破棄するため、`ToastManager` の Frame（`pagefolio/toast.py:66`）も毎回消滅する。破棄前に `dispose(reason="rebuild")` でタイマーを止め、経過時間を差し引いた `remaining_ms` を `PDFEditorApp` 側に残して新 `ToastManager`（`pagefolio/ui_builder.py:187`）で再表示する設計は、D-16・D-17 を満たす堅牢なアプローチである。

### 3. Concerns
- **[HIGH] 終了時の自動保存（`_save_window_state`）失敗で初回 `_quit()` を中断する裁量仕様の妥当性と確認順序 (`pagefolio/app.py:499-508, 575-585`)**:
  `05-02-PLAN.md`（1005〜1006行「終了時失敗の裁量」）では、通常起動時に `_quit()`（`pagefolio/app.py:499`）が呼ばれ、`_save_window_state()`（500行）の保存が失敗した際、**最初の終了操作を取り消してウィンドウを閉じずにトーストを表示し、2回目の終了操作で閉じられるようにする**としている。しかし、この設計には以下の問題がある：
  1. **利用者の終了意図の阻害（D-18 との緊張関係）**: `_save_window_state()`（`pagefolio/app.py:575-585`）が保存するのはウィンドウ位置・サッシ位置・閲覧/編集モードの自動保存であり、D-14 でも「利用者が設定を変更していない終了時の保存」と整理されている。設定フォルダへの書込権限がない環境等で、利用者がアプリを閉じようと `✕` ボタン（`WM_DELETE_WINDOW`、`pagefolio/app.py:219`）を押したにもかかわらずウィンドウが閉じない挙動は、「通知で操作を妨げない」（V110-CFG-04 / D-18）という原則に反して利用者を困惑させる。
  2. **`self.doc` 終了確認ダイアログ（`pagefolio/app.py:501-505`）との順序不整合**: 現行の `_quit()` は 500行で `self._save_window_state()` を呼び、502行で `if self.doc: if messagebox.askyesno(...):` を呼ぶ。もし 500行の位置で終了保存失敗により return すると、利用者が終了確認で「キャンセル」するつもりだった場合にも `_settings_exit_save_failed = True` がセットされ、逆に終了するつもりだった場合は確認ダイアログすら出ずに無言で終了が無視される。逆に `askyesno` の後に移動すると、利用者が「終了しますか？ → はい」と答えた直後に終了がキャンセルされ、もう一度 `✕` を押して再度「終了しますか？ → はい」と答えなければ終了できない（2回モーダル確認が要求される）。
- **[MEDIUM] `ToastManager.show()` の同一カテゴリ再表示分岐とイベント単位タイマー・ボタン有無の不整合 (`pagefolio/toast.py:48-55, 80-87`)**:
  現行の `pagefolio/toast.py:48-52` は、`if self._active_category == category and self._frame is not None:` のときに Frame を再構築せず `self._msg_var.set(message)` と `self._retry_btn.configure(command=retry_cb)` だけを行って早期 return する。
  1. `05-02` では設定通知のカテゴリをすべて `"config_notice"` に統一するため、1件目の `"config_notice"` が期限切れまたは閉じられて2件目の `"config_notice"` を表示する際、`_active_category` と `_frame` が確実にクリアされた後で呼ばれるか、あるいは上書き表示されるかで分岐が変わる。もし `_active_category == "config_notice"` が残ったまま `show()` が呼ばれると、48行の早期 return に入って新しい `duration_ms` タイマーや `on_close` コールバックが設定されないバグになる。
  2. 同一カテゴリ内で `retry_cb=None` と `retry_cb=callable` が切り替わるケース（`05-02-02` の「retry有無が変わる同カテゴリ更新もボタン状態を揃える」）では、現行の `_build_frame`（`pagefolio/toast.py:80-88`）は `retry_btn` と `✕` ボタンを左から順に `pack(side="left")` しているため、後から `retry_btn` を pack すると `✕` ボタンの右側に配置されてレイアウト順序が崩れる。
- **[MEDIUM] PDF 保存/印刷トーストが `dismiss()` された際の `on_idle` 発火漏れリスク (`pagefolio/toast.py:57-62`, `pagefolio/file_ops.py:1148, 1162`, `pagefolio/print_ops.py:72, 81`)**:
  PDF 保存や印刷の成功時（`pagefolio/file_ops.py:1162` 等）やドキュメント閉鎖後の再試行時（`pagefolio/file_ops.py:1148`）は、✕ボタンではなく `self._toast.dismiss("save_file")` が直接呼ばれる。`ToastManager.dismiss(category)`（`pagefolio/toast.py:57-62`）と ✕ ボタンの両方が共通の内部クローズ処理を通って `on_idle` を `after_idle` スケジュールしないと、`save_file` トーストに割り込まれた設定通知が、`save_file` 成功消去後に再開されないまま宙に浮くことになる。

### 4. Suggestions
- **終了時保存（`_quit` / `_save_window_state`）の順序と失敗時の扱いの見直し**:
  1. まず `pagefolio/app.py:499-508` の `_quit()` において、`self.doc` が開いている場合の `messagebox.askyesno`（502行）を **`self._save_window_state()` より前** に移動することを強く推奨する。これにより、利用者が終了確認をキャンセルした際に不要なディスク書込や不要な保存失敗トーストが発生する問題自体を根絶できる。
  2. そのうえで、`_save_window_state()` は利用者の明示的な設定変更ではなく終了時のウィンドウ状態記録（自動保存）であるため、もし未承認の「初回終了中断」裁量を維持する場合でも、少なくとも終了確認通過後に1回だけ実行するようにし、可能であれば D-18（操作を妨げない）を優先して「終了時自動保存の失敗では終了自体をブロックしない（または明示変更の保存失敗時のみ通知し、ウィンドウ状態の自動保存失敗では終了を止めない）」選択肢をユーザーまたはチェッカーと再確認することを推奨する。
- **`ToastManager.show()` の Frame 更新方式**: `pagefolio/toast.py:48-55` において、`duration_ms` や `on_close`、または `(retry_cb is None) != (self._retry_btn is None)` が変化する場合は、無理にインプレース更新せず `self._destroy_frame()` して `_build_frame()` で作り直す（または `"config_notice"` のイベント切替時は必ず前の Frame/timer を破棄してから新規作成する）実装にすると、ボタン順序崩れやタイマー設定漏れを構造的に防げる。

### 5. Risk Assessment
- **Risk Level: MEDIUM**
- **Justification**: `ToastManager` のタイマー・世代管理・カテゴリ競合のライフサイクルと、`_quit()` における終了保存失敗時の閉鎖中断ロジックが絡み合うため、コールバック順序や確認ダイアログとの前後関係でエッジケースが生じやすい。

---

## 05-03

### 1. Summary
`05-03-PLAN.md` は、設定を保存する全 UI 経路（言語切替、プラグイン、一般設定、ネスト LLM 設定、OCR ダイアログ内 LLM 設定、ショートカット、モザイク粒度、サムネイル倍率、サムネイル表示件数）を `PDFEditorApp._persist_settings()` へ集約し、さらに `SettingsDialog` 内の LLM 設定適用における二重保存を解消する計画である。`SettingsDialog._open_llm_config` と `PDFEditorApp._apply_llm_settings_live` の二重保存構造は実コードの課題と完全に一致している。しかし、`pagefolio/dialogs/plugin.py` の実コードを検証した結果、**`PluginDialog` の「閉じる」ボタンが無条件に `_reload_plugins()`（＝設定保存）を呼んでおり、未変更で閉じた際の破損ファイル上書き（D-10 違反）およびプラグイン切替時の二重保存（D-16 違反）を引き起こす重大な見落とし（HIGH）** が判明した。

### 2. Strengths
- **ネストされた `LLMConfigDialog` の二重保存バグと外側 Cancel 境界の的確な解消**: 現行の `pagefolio/dialogs/settings.py:224-240` では、`on_apply` 内で `self.current_settings.update(llm_settings)` → `_save_settings(self.current_settings)`（233行）を実行した直後に、`on_llm_apply(dict(llm_settings))`（240行）経由で `pagefolio/app.py:668-685` の `_apply_llm_settings_live` を呼び、679行で2回目の `_save_settings(self.settings)` を実行している。しかも 233行は外側 `SettingsDialog` の `self.current_settings` を保存していた。保存オーナーを `_apply_llm_settings_live`（`self._persist_settings()`）の1回に一本化する `05-03-01` の設計は、二重書込・二重通知の解消と外側未適用設定の漏洩防止を同時に達成している。
- **操作ハンドラにおける UI 反映継続（D-08）の徹底**: `ShortcutsDialog._on_save`（`pagefolio/dialogs/shortcuts.py:280-286`）、`OCRDialog._apply_llm_settings`（`pagefolio/ocr_dialog.py:1038-1060`）、`RedactOpsMixin._on_mosaic_block_release`（`pagefolio/redact_ops.py:258-261`）、`ViewerMixin._on_thumb_zoom_release` / `_on_page_size_change`（`pagefolio/viewer.py:161-188`）のすべてにおいて、保存失敗時にもキーバインド再構築・プロバイダ再生成・キャッシュ無効化・再描画を中断しない方針が明記されており、D-08 と整合している。
- **AST による直接 `_save_settings` 呼び出しの網羅監査**: `TestSaveOriginCoverage` で製品コード内の `_save_settings` 直接呼び出しが `PDFEditorApp._persist_settings` のみに限定されていることを機械的に検査する設計（`05-03-02`）により、将来の保存経路追加時の通知漏れを防止できる。

### 3. Concerns
- **[HIGH] `PluginDialog` の `_toggle` / `_rescan` / `_close` による無条件保存・二重保存と破損原本の上書き (`pagefolio/dialogs/plugin.py:211-240`, `pagefolio/app.py:633-637`)**:
  `pagefolio/dialogs/plugin.py` を確認すると、以下の3箇所がすべて `self.app._reload_plugins()`（`pagefolio/app.py:633-637`）を呼んでいる：
  - `_toggle(self, plugin_id)`（`pagefolio/dialogs/plugin.py:216`）: チェックボックス切替時に呼ばれる。
  - `_rescan(self)`（`pagefolio/dialogs/plugin.py:225`）: 「再検出」ボタン押下時に呼ばれる。
  - `_close(self)`（`pagefolio/dialogs/plugin.py:238-240`）: **「閉じる」ボタン押下時に無条件で `self.app._reload_plugins()` を呼んでから `self.destroy()` する。**
  `05-03-01` の計画では `pagefolio/dialogs/plugin.py` を変更対象（`files_modified`）に含めず、`pagefolio/app.py:633-637` の `_reload_plugins()` 内の `_save_settings(self.settings)` を単純に `self._persist_settings()`（`explicit=True`）へ置き換えるとしている。このまま実装すると以下の2つの欠陥が発生する：
  1. **未変更で「閉じる」を押しただけで破損設定ファイルが上書きされる（V110-CFG-03 / D-10 / D-13 違反）**: 読込失敗（`_settings_autosave_blocked = True`）で起動した後、利用者がプラグイン管理ダイアログを開いて何も変更せずに「閉じる」ボタン（`_close`）を押すと、`_reload_plugins()` → `_persist_settings(explicit=True)` が実行され、**設定を一切変更していないにもかかわらず破損した `pagefolio_settings.json` が既定値で上書きされ、保護フラグまで解除されてしまう**。
  2. **プラグインを1回切り替えて「閉じる」を押すと2回保存・2回失敗通知が発生する（`05-03` の must-have「一操作一保存・一失敗一イベント」違反）**: チェックボックスを1回切り替えた時点で `_toggle` が `_reload_plugins()` を呼び（1回目の保存・失敗通知1個目）、直後に「閉じる」ボタンを押すと `_close` が再び `_reload_plugins()` を呼ぶ（2回目の保存・失敗通知2個目）。また、ウインドウ右上の `✕` で閉じた場合は `_close` を通らないため挙動も不統一である。
- **[MEDIUM] モーダルダイアログ（`grab_set()`）が開いたままの状態での背面トースト表示とタイマー進行 (`pagefolio/dialogs/settings.py:36, 224-250`, `pagefolio/ocr_dialog.py:1021-1042`, `pagefolio/dialogs/plugin.py:27`)**:
  `SettingsDialog`（`pagefolio/dialogs/settings.py:36`）、`OCRDialog`、`PluginDialog`（`pagefolio/dialogs/plugin.py:27`）はいずれも `grab_set()` を行うモーダル `Toplevel` である。
  - `SettingsDialog` からネストして `LLMConfigDialog` を開き、「適用」を押したとき（`pagefolio/dialogs/settings.py:224-240`）、あるいは `OCRDialog` から `LLMConfigDialog` を開いて「適用」を押したとき（`pagefolio/ocr_dialog.py:1031-1042`）、内側の `LLMConfigDialog` は閉じるが、外側の `SettingsDialog` や `OCRDialog`（および `PluginDialog` でトグルした際の `PluginDialog` 自身）は **モーダル（`grab` 保持中）のまま画面前面に残る**。
  - このとき `ToastManager` は背面の `app.root` 右下に配置される（`pagefolio/toast.py:66-67`）ため、外側モーダルダイアログに隠れて見えない可能性があり、また `grab` がモーダル側にあるため利用者はトーストの `✕` ボタンを押せない。さらに背面で 10,000ms タイマーが進行すると、利用者がモーダルダイアログを閉じる前にトーストが自動消去されて見落とされるリスクがある。
- **[LOW] `tests/test_provider_ui.py:1702-1738` の既存スタブと `SettingsDialog._open_llm_config` フォールバックの互換性**:
  `tests/test_provider_ui.py:1723-1727` の `test_llm_apply_saves_immediately` で使われている `SimpleNamespace` スタブは `current_settings`・`_font`・`_plugin_manager` のみを持ち、`_on_llm_apply` も `_app` も `callback` も持たない。`05-03-01` で「`_on_llm_apply` と `_app` の両方ない単体利用では必須の一般 `callback` へ渡す」と実装する際、`getattr(self, "callback", None)` で防御しないと、当該テストで `AttributeError: ' types.SimpleNamespace' object has no attribute 'callback'` が発生する。

### 4. Suggestions
- **`PluginDialog`（`pagefolio/dialogs/plugin.py`）の保存契約の整理**:
  `05-03-01` の `files_modified` に `pagefolio/dialogs/plugin.py` を追加し、`_close()`（`pagefolio/dialogs/plugin.py:238-240`）から無条件の `self.app._reload_plugins()` 呼び出しを除去する（`_toggle()` と `_rescan()` で既に即時反映・保存されているため、`_close()` は `self.destroy()` のみでよい。あるいは `_reload_plugins(save=True)` のように引数を分け、変更を伴う `_toggle`、および `disabled_plugins` に変化があった場合のみ `_persist_settings()` を呼ぶ）ことを強く推奨する。これにより「開いて閉じただけで破損原本を上書きする」問題と「トグル後に閉じると二重保存になる」問題の両方が解決する。
- **モーダル `Toplevel` 表示中のトースト可視性/タイマー保護**:
  `self.root.grab_current()` が `None` でない（モーダルダイアログが `grab` を握っている）間は、設定通知トーストの表示開始（または 10,000ms カウントダウンの開始）をモーダル終了後まで保留するか、あるいはモーダル解除時に残り時間を確保する設計を検討すると、ネスト LLM 適用や OCR ダイアログ内 LLM 適用での通知見落としを防げる。
- **`SettingsDialog._open_llm_config` の後方互換フォールバック**:
  `pagefolio/dialogs/settings.py:238-240` の変更では、`on_llm_apply` → `_app._apply_llm_settings_live` → `getattr(self, "callback", None)` の順で探索し、`tests/test_provider_ui.py:1702-1738` の `test_llm_apply_saves_immediately` は `05-03-01` の計画どおり新オーナー境界（`_on_llm_apply` または `_persist_settings`）を検証するように更新することを推奨する。

### 5. Risk Assessment
- **Risk Level: MEDIUM**
- **Justification**: 10箇所の保存経路の統合自体は明確だが、`PluginDialog._close()` が無条件に `_reload_plugins()` を呼んでいる既存実装（`pagefolio/dialogs/plugin.py:238-240`）を見落とすと、D-10（原本保護）と D-16（一操作一保存）の両方に直接違反するため、計画への反映が必要である。

---

## 05-04

### 1. Summary
`05-04-PLAN.md` は、読込失敗・明示保存失敗・UI 再構築・保存成功・終了までを通しで検証する複合受入テスト（`TestConfigAcceptance`）、実環境の設定や外部プロンプトを汚染しない手動確認用ハーネス（`05-NOTICE-HARNESS.py`）とその隔離テスト（`TestScenarioIsolation`）、および `docs/CONFIGURATION.md`・`開発履歴.md`・`05-VALIDATION.md`・`05-EVIDENCE.json` の整備を行う Wave 4 計画である。テスト・ハーネスによる実ファイル汚染防止（SHA-256 前後一致検証）や、未実施の人手確認を `pending` のまま区別する方針は非常に厳格で信頼性が高い。注意点として、実 `PDFEditorApp` を使う複合テストでのリソース解放（`UndoBlobStore` / `fitz.Document`）と、`docs/CONFIGURATION.md` 内の複数箇所に散在する旧仕様記述の洗い出しを徹底する必要がある。

### 2. Strengths
- **実利用ファイル（設定・外部プロンプト・プラグイン）の完全隔離とハッシュ検証**: `pagefolio/settings.py:32-49` および `pagefolio/plugins.py` は実行基準ディレクトリ（開発時はプロジェクトルート）直下の `pagefolio_settings.json`、`ocr_custom_prompt.md`、`ocr_summary_prompt.md`、`plugins/` を参照する。`05-04-01` が `05-NOTICE-HARNESS.py` の隔離を `TestScenarioIsolation` で自動テストし、実利用ファイルの存在と SHA-256 不変を assert する設計は、T-05-12（障害注入による利用者ファイル破壊）への対策として優れている。
- **PDF 保存/印刷の再試行契約（`bound_doc` 同一性チェック）との回帰検証**: `pagefolio/file_ops.py:1135-1169` の `_do_save_file` 等は `bound_doc` 同一性確認と `self._toast.dismiss("save_file")` に依存している。設定通知のキュー・タイマー機構を導入した状態でも、この PDF 保存/印刷トーストの再試行と設定通知の再開が両立することを複合シナリオで検証する設計は、Phase 3（v1.9.0）の安全境界を確実に維持している。
- **証拠に基づく品質ゲート運用**: `05-VALIDATION.md:32-47` の `DEP-05-REGRESSION` 照合、単一プロセス全件 `pytest`、および人手未実施項目の `pending` 維持が明確に規定されており、形骸化を防いでいる。

### 3. Concerns
- **[MEDIUM] 実 `PDFEditorApp` 複合テストにおける `fitz.Document`・`UndoBlobStore`・Tk タイマーの teardown 漏れリスク (`pagefolio/app.py:499-508`, `pagefolio/file_ops.py:229-241`)**:
  `05-04-01` の `TestConfigAcceptance`（および `05-01-01` の `TestLoadTracer`）では、実 `PDFEditorApp` 上で PDF を開いてページ操作・Undo/Redo を行い、さらに `_quit()` の終了抑止・終了保存失敗の分岐をテストする。`_quit()` がキャンセルまたは中断された分岐では、`self._clear_undo_stacks()`（`pagefolio/file_ops.py:229-241`）や `self.doc.close()`（`pagefolio/app.py:504`）が呼ばれない。テストの `finally`（または fixture teardown）で明示的に `app._toast.dispose()`、`app._clear_undo_stacks()`、`app.doc.close()` を呼ばないまま一時ディレクトリを終了すると、Windows 上でファイルハンドルが残って `--basetemp` の削除権限エラーや後続テストへの `after` タイマー残留を引き起こす懸念がある。
- **[MEDIUM] `ruff format .` 実行時の対象ファイルと `05-NOTICE-HARNESS.py` の配置 (`05-04-PLAN.md:1330`, `.planning/phases/05-config-notification/05-PLANNING-CHECKS.md:50`)**:
  `05-04-01` は `.planning/phases/05-config-notification/05-NOTICE-HARNESS.py` を作成し、`05-04-02` は `.venv/Scripts/ruff.exe check .` と `.venv/Scripts/ruff.exe format .` を実行する。`.planning/` 配下の `.py` ファイルも Ruff のデフォルト探索対象に含まれるため、`05-NOTICE-HARNESS.py` が Ruff の lint/format 規約（行長・import 順・変数付き `except Exception as e:` 等）に最初から準拠していないと `05-04-02` で差分が生じる。また、`05-PLANNING-CHECKS.md:50` で言及されている Markdown コードブロックへの Ruff format の影響有無も実行時に確認が必要である。
- **[LOW] `docs/CONFIGURATION.md` 内の複数箇所に散在する自動保存・破損時挙動の記述 (`docs/CONFIGURATION.md:15, 20, 47, 310-312, 333`)**:
  `05-04-02` の `<read_first>` は「`docs/CONFIGURATION.md` の設定ファイル節」を挙げているが、実際の `docs/CONFIGURATION.md` では以下の複数セクションに関連記述が分散している：
  - 15行（「設定ファイルの場所と形式」表）: `設定変更時またはアプリ終了時に _save_settings() が呼ばれた際に作成`
  - 47行（「ウィンドウ状態（自動管理）」）: `アプリ終了時に現在の状態が自動保存され、次回起動時に復元されます`
  - 310〜312行（「既定値と起動失敗に関する注意」）: `設定ファイルが破損・欠損している場合、_load_settings() 関数がすべての既定値を返します`
  - 333行（「設定の変更方法」）: `UI から変更した場合は即時に pagefolio_settings.json へ書き込まれます`
  一箇所のみの追記にとどまると文書内で説明が矛盾するため、上記すべての箇所を整合させる必要がある。

### 4. Suggestions
- `tests/test_config_notification.py` で実 `PDFEditorApp` を生成するヘルパー/fixture には、必ず `finally` で ` ToastManager.dispose()`（未消化 `after` / `after_idle` の `after_cancel` 含む）、`app._clear_undo_stacks()`、および `if app.doc is not None: app.doc.close()` を実行する共通クリーンアップを組み込むことを推奨する。
- `docs/CONFIGURATION.md` の更新では、15行・47行（読込失敗時は明示保存が成功するまで終了時自動保存を行わない旨）、310〜312行（初回不存在は無警告、破損・読取不能時は非モーダル通知を出して既定値で起動し原本を上書きしない旨）、333行（保存失敗時は非モーダル通知を出し、変更は現在の画面メモリにのみ維持され次回起動には残らない旨）を一括で同期することを推奨する。

### 5. Risk Assessment
- **Risk Level: LOW**
- **Justification**: 製品コードの外部仕様変更を含まず、受入テスト・隔離ハーネス・ドキュメント更新が中心であるためリスクは低い。テスト teardown でのハンドル・タイマー解放を徹底すれば安定して完走できる。

---

## Cross-Plan Synthesis & Overall Assessment

### 計画間の依存関係と整合性
4つのプラン（`05-01` → `05-02` → `05-03` → `05-04`）は、設定読込と初期通知（Wave 1）→ 原子的保存結果と通知 FIFO ライフサイクル（Wave 2）→ 全保存経路の統合（Wave 3）→ 複合検証とドキュメント（Wave 4）へと段階的に積み上げる構成になっており、ファイル競合のない直列実行（Wave 1〜4）として妥当である。要件 V110-CFG-01〜04 および CONTEXT.md の D-01〜D-18 もすべてタスクへ割り当てられている。

### 実装前に解消・留意すべき重要事項（優先順）
1. **[HIGH / 05-03] `PluginDialog._close()` の無条件保存による原本上書き・二重保存 (`pagefolio/dialogs/plugin.py:216, 225, 238-240`)**:
   `PluginDialog` は「閉じる」ボタン押下時（`_close`）にも無条件で `self.app._reload_plugins()` を呼んでいる。`05-03-01` に `pagefolio/dialogs/plugin.py` を加え、変更がない「閉じる」操作で `_persist_settings(explicit=True)` が走らないよう修正する必要がある。
2. **[HIGH / 05-02] `_quit()` における終了確認ダイアログと `_save_window_state()` の順序および初回終了中断の裁量 (`pagefolio/app.py:499-508`)**:
   `_quit()` で `messagebox.askyesno` より前に `_save_window_state()` が呼ばれている構造を見直し、終了確認を先に通過させるべきである。また、ウィンドウ状態の自動保存失敗によって利用者のウィンドウ閉鎖操作（`✕` ボタン）をキャンセルする裁量仕様が D-18（操作を妨げない）と整合するか、実行前に判断を確定させることが望ましい。
3. **[MEDIUM / 05-02 & 05-03] `ToastManager` の同一カテゴリ更新・`dismiss()` 時の `on_idle` 連携・モーダル `grab` 中の表示 (`pagefolio/toast.py:48-62`, `pagefolio/dialogs/settings.py:36`)**:
   `"config_notice"` の連続イベント表示でタイマーやボタン構成がスキップされないこと、および `dismiss("save_file")` 等のプログラム的消去でも待機中の設定通知が再開されることを `05-02-02` で確実に実装する必要がある。


---

## Grok Review

Phase 5 の4計画を、リポジトリの実装と突き合わせて確認します。まず計画本文と、設定読込・保存・通知の現行コードを読みます。計画の主張を、設定 I/O・起動順・保存呼び出し元の実装と照合します。Phase 5 の4計画は、設定の読込失敗と保存失敗を利用者へ伝え、原本を守るという目標に沿っています。現行コードの握りつぶし箇所と呼び出し順も合っています。実行前に埋めるべきなのは、未承認の終了キャンセル、既存テストの取りこぼし、モーダル表示中に消える通知、隔離のパッチ先です。

## 05-01

読込結果を辞書 API と分け、画面構築後に一度だけ知らせ、終了確認より前の自動保存を止める構成は、現行の起動順に合っています。実アプリを通す tracer と、プラグインディレクトリの隔離先が計画に足りません。

**Strengths**

- 読込は `PDFEditorApp.__init__` の `self.settings = _load_settings()`（`pagefolio/app.py:149`）で、`_build_ui()`（同 215 行）より前です。トーストは `_build_ui` の末尾で毎回作り直されます（`pagefolio/ui_builder.py:184-187`）。画面構築後の `after_idle` という順序は、この事実に合っています。
- `_load_settings()` は `JSONDecodeError` も `OSError` も `except Exception` で握りつぶし、既定値だけを返します（`pagefolio/settings.py:301-311`）。`SettingsLoadResult` を足し、既存の `_load_settings()` は辞書を返す wrapper に残す契約は、`tests/test_settings_keyguard.py` と `tests/test_utils.py:21-57` の添字アクセスを壊しません。
- `_quit()` は確認ダイアログより先に `_save_window_state()` を呼びます（`pagefolio/app.py:499-508`、保存本体は 575-585 行）。破損ファイルは、終了をキャンセルしてもここで上書きされ得ます。D-10 と D-14 をこの地点へ置くのは正しいです。
- 排他の解放は `_quit()` の中にはありません。`mainloop` 終了後の `finally` で `coordinator.close()` されます（`pagefolio/__main__.py:83-94`）。保存を抑止して `root.destroy()` を呼ばなければ、ロックは残ります。
- 文言は固定文で、例外文字列とパスを補間しないと明記しています。現行の `logger.debug("設定ファイル読み込み失敗: %s", e)`（`pagefolio/settings.py:310`）は `JSONDecodeError` の断片をログへ載せ得るので、型と `errno` だけにする方針は T-05-02 に合います。
- `DEP-05-REGRESSION` は `.planning/phases/05-config-notification/05-VALIDATION.md:32-46` で充足と記録され、`8689c2720e38fc2397407e38317687d1952b22f6` は現在の `HEAD` の祖先です。Wave 1 の停止条件は、この記録と一致しています。

**Concerns**

- **MEDIUM:** 不存在の判定に、現行の `os.path.exists` 先行（`pagefolio/settings.py:303`）を残すと、読取不能を「初回不存在」と誤分類します。CPython の `os.path.exists` は `os.stat` の `OSError` を握って `False` を返します。その結果は `missing` になり、D-10 の自動保存抑止が掛かりません。計画は「open を正本」と書いていますが、現行分岐を残した場合の失敗形がタスク本文にありません。
- **MEDIUM:** `TestLoadTracer` は実 `PDFEditorApp` を組み立てます。ユニットテストで `PDFEditorApp()` を直接生成している既存例はなく、起動試験は別プロセスです。`__init__` は `PluginManager.load_all` を呼び、プラグインディレクトリは `_get_plugins_dir()`（`pagefolio/plugins.py:21-29`）です。設定パスだけを差し替えても、リポジトリの `plugins/` と外部プロンプトの基準ディレクトリは動きます。
- **LOW:** 英語文言は「同義」とだけあり、日本語3文のような固定文がありません。`_t()` はキー欠落時にキー名を出します（`pagefolio/app.py:594-596`）。日英どちらかの追加漏れが、そのまま画面へ出ます。
- **LOW:** 未知例外の失敗種別が、`corrupt` と `unreadable` のどちらに落ちるか未指定です。辞書以外の root は `corrupt` と書いてあるので、`json.load` の `[]` や `null` を型検査する前に広い `except Exception` へ入れると、文言が揺れます。

**Suggestions**

- 読込は `exists()` で分岐せず、`open` の `FileNotFoundError` だけを `missing` にしてください。`UnicodeDecodeError` と `json.JSONDecodeError` と非 `dict` root を `corrupt`、それ以外の `OSError` を `unreadable` にしてください。
- tracer の隔離先を、`pagefolio.settings._get_settings_path`、`pagefolio.settings._get_base_dir`、`pagefolio.plugins._get_plugins_dir` の3つと書いてください。`root` は `try/finally` で破棄してください。
- `config_load_corrupt`、`config_load_unreadable`、`config_save_failed` の英語文を、日本語と同じ固定文で計画に書いてください。

**Risk Assessment:** MEDIUM。読込 API と終了前の上書き防止は、現行の欠陥にそのまま対応します。隔離が設定パスだけだと、tracer が実プラグインと実プロンプトへ触れます。

## 05-02

保存の成否を `bool` で返し、明示保存の成功時だけ原本保護を外す契約は、D-08、D-12、D-13、D-14 を満たせます。終了時の最初の失敗で閉じない裁量と、既存トーストの同カテゴリ更新が、この計画の実装リスクです。

**Strengths**

- `_save_settings()` は一時ファイルへ書いてから `os.replace` しますが、失敗時に `.tmp` を消さず、戻り値もありません（`pagefolio/settings.py:328-342`）。失敗点ごとの原本バイト一致と `.tmp` 削除は、この穴に対応しています。
- 機密キーが無いとき、保存対象は入力辞書そのものです（同 327 行）。キーがあるときだけコピーします（324-325 行）。入力を変更しない既存契約（`tests/test_settings_keyguard.py` の非破壊試験）を維持する指示は正しいです。
- `_apply_settings()` は保存結果を見ずに `_rebuild_ui()` のあと `status_settings`（「設定を変更しました」）を出します（`pagefolio/app.py:686-695`）。このラベルの色は成功色です（`pagefolio/ui_builder.py:136-141`）。失敗時にこの表示を出さない条件は、D-07 に合っています。再構築直後の初期文言は「ファイルを開いてください」（`pagefolio/lang.py:24`）なので、失敗時は成功色の設定完了文を避けられます。
- 通知の正本を App の FIFO に置き、`ToastManager` は表示だけにする判断は、現行契約と一致します。同カテゴリは文言だけ更新し（`pagefolio/toast.py:48-52`）、別カテゴリはフレームを破棄し（53-55 行）、再試行ボタンは常に作ります（80-87 行）。`_rebuild_ui()` は子を全部捨てて新しい `ToastManager` を作ります（`pagefolio/app.py:697-716`、`pagefolio/ui_builder.py:187`）。ウィジェットを正本にすると D-17 は満たせません。
- 保護解除を「明示保存の成功だけ」に限定しているため、終了時保存の失敗や抑止で破損原本が復活しません。

**Concerns**

- **HIGH:** 「終了時失敗の裁量」は、最初の終了保存失敗で `root.destroy()` を取り消し、次の終了操作では同じ保存を省略して閉じます。これは D-01〜D-18 の利用者決定ではなく、計画自身が未承認と書いています。設定ディレクトリが書けない環境では、起動のたびに1回目の終了が拒否されます。フラグはプロセス内だけで、明示保存が成功するまで次の起動でも同じ二段終了になります。排他は `root` が残る間保持されるので、1回目の終了拒否はロックの観点では安全です。閉じる操作の意味が変わります。
- **MEDIUM:** 設定通知の category を常に `config_notice` にすると、次のイベントの `show()` が `pagefolio/toast.py:48-52` の早期 return に入ります。文言だけ変わり、タイマーは初回のまま、`on_close` も次の `event_id` に結び付きません。D-16 の「1失敗1イベント、10秒ずつ」は、前フレームを破棄してから次を出す実装でないと成立しません。計画は同カテゴリ更新の維持と、イベントごとの消化を両方要求しています。
- **MEDIUM:** 表示開始から 10,000ms で消化する契約は、モーダルの `grab_set()` と重なります。設定ダイアログ（`pagefolio/dialogs/settings.py:36`）、ショートカット（`pagefolio/dialogs/shortcuts.py:60`）、OCR ダイアログ（`pagefolio/ocr_dialog.py:156`）、LLM 設定（`pagefolio/dialogs/llm_config/dialog.py:82`）が該当します。LLM 適用はダイアログを閉じてから `on_apply` を呼びますが（同 685-687 行）、親の設定ダイアログは grab を持ったままです。トーストはルート上の Frame なので、grab 中は ✕ を押せません。タイマーだけが進むと、利用者がダイアログを閉じる前にイベントが期限消化されます。
- **LOW:** `_save_window_state()` は保存の前に `window_geometry`、サッシ、`edit_mode` をメモリへ書き込みます（`pagefolio/app.py:575-585`）。抑止中もメモリ収集を許すと、その後の明示保存が、利用者が触っていないウィンドウ状態まで書き込みます。D-08 の「戻さない」とは別の混入です。

**Suggestions**

- 終了失敗で閉じない挙動は、実装前の確認項目にしてください。承認までは、失敗通知を出したうえで既存の終了確認へ進む案と、二段終了案のどちらを製品にするかを計画の checkpoint に残してください。
- `config_notice` の次表示は、`dismiss` または `dispose` のあとだけ `show()` すると書いてください。同カテゴリの早期 return では `event_id` を進めないテストを、9,999ms と 10,000ms の境界に含めてください。
- `grab_current()` が他の Toplevel を指している間は `shown_at` を始めず、grab 解放後の `after_idle` で残り時間を開始してください。
- 読込保護中の終了は、ジオメトリ収集も `_persist_settings(explicit=False)` の前で止めるか、収集したキーを明示保存の辞書へ混ぜない条件を書いてください。

**Risk Assessment:** HIGH。原子的保存と保護解除の本体は実装可能です。未承認の終了キャンセルをこのまま実装すると、保存不能な環境の終了手順が恒久的に変わります。

## 05-03

全保存元を `_persist_settings` へ寄せ、設定ダイアログ内の LLM 二重保存をやめる範囲は、現行の呼び出し一覧と一致します。計画の `files_modified` に、その変更で落ちる既存テストが入っていません。

**Strengths**

- 製品コードの `_save_settings(` は次の10か所だけです。`pagefolio/app.py:585`（終了）、602（言語）、636（プラグイン）、679（LLM 即時反映）、693（一般設定）、`pagefolio/dialogs/settings.py:233`、`pagefolio/ocr_dialog.py:1042`、`pagefolio/dialogs/shortcuts.py:285`、`pagefolio/redact_ops.py:261`、`pagefolio/viewer.py:164` と 185。計画の10経路はこの一覧と一致します。プラグイン配下に設定保存はありません。
- ネストした LLM 適用は、ダイアログのコピー全体を保存し（`pagefolio/dialogs/settings.py:224-233`）、続けて `on_llm_apply` から `app.settings` を再度保存します（`pagefolio/app.py:668-679`）。外側で未適用のテーマやフォントが、1回目の書込に含まれます。保存 owner を `on_llm_apply` 側の1回に寄せる修正は、この二重化を断ちます。
- OCR 側は保存のあとで provider 再生成とプロンプト同期を続けます（`pagefolio/ocr_dialog.py:1037-1059`）。失敗してもここを `return` しない指示は、D-08 と現行の後処理に合っています。
- 外部プロンプトの `save_prompt_file()`（`pagefolio/dialogs/llm_config/dialog.py:619-622`）を今回の通知対象にしない判断は、保留の V110-F-04 と一致します。
- 低層の直接呼び出しを AST で照合し、空の期待リストで通さない、という検査は、呼び出し漏れを検知できます。

**Concerns**

- **HIGH:** `tests/test_ocr.py` と `tests/test_pagination.py` が 05-03 の変更ファイルにありません。局所 verify にも入りません。`OCRDialog._apply_llm_settings` の fake は `app` に `settings` しか持たず（`tests/test_ocr.py:895-898`）、`test_apply_persists_via_save_settings` は `pagefolio.settings._save_settings` が1回呼ばれることを断言します（960-982 行）。`off` の試験も同じ関数を monkeypatch しています（2035-2053 行）。`viewer.py` を `self._persist_settings` に変えると、`ViewerMixin._on_page_size_change` をスタブから呼ぶ `tests/test_pagination.py:467-475` は、スタブにそのメソッドが無く `AttributeError` になります。全件ゲートまで落ち方が見えません。
- **MEDIUM:** `tests/test_provider_ui.py:2433-2449` は、`_on_llm_apply` も `_app` も `callback` も無いスタブで「例外を出さない」ことを固定しています。計画の互換経路は、両方無いとき一般 callback を呼ぶと書いてあります。このスタブには `callback` もありません。製品の `SettingsDialog.__init__` は `callback` を必須引数にしています（`pagefolio/dialogs/settings.py:19-38`）。未束縛呼び出しの既存契約と、製品の必須引数が、計画の一文では分かれません。
- **MEDIUM:** ショートカット保存は、キー割り当てを変えた直後に無条件でダイアログを閉じます（`pagefolio/dialogs/shortcuts.py:280-286`）。ダイアログは `grab_set()` です（60 行）。失敗トーストが閉じたダイアログの「成功したように見える終了」と同時に出ます。D-07 は成功文言の抑止だけを要求しており、ダイアログを開いたまま失敗を見せる条件がありません。
- **LOW:** `tests/test_provider_ui.py:2322` と 2340 行は `pagefolio.app._save_settings` を差し替えています。`app.py` は関数をモジュール先頭で import しています（`pagefolio/app.py:25-26`）。呼び出しを `pagefolio.settings._save_settings` へ移すと、このパッチは本番の保存に届きません。ファイル自体は変更対象に入っているので、spy の移し先をタスク内で指定すれば足ります。

**Suggestions**

- 05-03 の `files_modified` と verify に `tests/test_ocr.py` と `tests/test_pagination.py` を追加してください。断言は「`_save_settings` が1回」を維持し、fake には App の `_persist_settings` を経由させてください。
- `on_llm_apply` も `_app` も無い経路は、`callback` が呼び出し可能なら開始時コピーへ LLM 値だけを重ねて1回呼ぶ、どれも無ければ保存せず例外にもしない、と分けてください。`test_no_on_llm_apply_does_not_raise` をその形で残してください。
- ショートカット、モザイク、サムネイルは、失敗時も binding と再描画を維持し、ダイアログを閉じる場合は閉じたあとに未消化イベントが残ることを `TestToolSaveOrigins` で断言してください。

**Risk Assessment:** MEDIUM。保存元の棚卸しは足りています。記載どおりのファイルだけを編集すると、Wave 3 の局所試験は通り、全件の `test_ocr.py` と `test_pagination.py` が落ちます。

## 05-04

複合操作の受入、人手確認を pending のまま残す証拠、版番号を Phase 6 へ残す境界は、今回の完了条件に合っています。検証コマンドの `ruff format .` は、同じ日の回帰修復で Markdown まで巻き込むことが記録されています。

**Strengths**

- 自動試験の成功を人手の pass に変えない、not-run を pass にしない、という条件は、2026-10-22 の受入再計画と一致します。実 EXE の最終受入を Phase 6 に残す記載も一致します。
- `docs/CONFIGURATION.md:308-333` は、破損と欠損を同じ「既定値を返す」と書き、UI 変更は即時に JSON へ書かれると書いています。D-02、D-10、D-12、失敗時のメモリ保持をここに追記する対象ファイルは正しいです。
- `APP_VERSION` は既に `v1.9.1` です（`pagefolio/constants.py:12`）。Phase 5 で版と README バッジを動かさない指示は、Phase 6 の版同期と矛盾しません。
- `nyquist_compliant` を証拠前に `true` にしない、probe 4件と prohibition 2件を証拠なしで resolved にしない、という停止条件は、`05-VALIDATION.md:5-6` と `84-86` の現状に合っています。
- 障害注入を `TemporaryDirectory` に閉じ、実設定の SHA-256 を前後で比べる試験は、T-05-12 に対する直接の緩和です。

**Concerns**

- **MEDIUM:** 05-04-02 の検証は `ruff format .` です。`.planning/debug/dep-05-regression.md:75-76` では、Ruff 0.17.1 の既定 format が Markdown のコード例まで対象にし、`--exclude "*.md"` でも適用され、アクセス拒否も起きたと記録されています。回避は CLI の `include` で Python に限った、とあります。計画のコマンドをそのまま実行すると、説明文の更新と無関係な Markdown 差分か、format の非0終了になります。`pyproject.toml` は規約で編集できません。
- **MEDIUM:** harness の隔離文は「import 前に一時ディレクトリへ寄せる」と書いてあります。プラグイン経路は `_get_base_dir()` を見ません（`pagefolio/plugins.py:21-29`）。設定とプロンプトだけを一時ディレクトリへ移しても、`plugins/` の読込はリポジトリ側のままです。実ファイルの SHA-256 が一致しても、プラグインの `on_load` が別のファイルを書いた可能性は、この断言では見えません。
- **LOW:** 人手確認は Phase 末にエージェントが harness を起動すると書いてあります。フォーカスと「編集を続行できる」感覚は、`05-VALIDATION.md:79-82` で手動の理由になっています。自動の `focus_get()` 一致と、この人手確認のどちらが prohibition 2件を閉じるかが、タスク完了条件では分かれていません。未実施を pending に残す文はあるので、完了判定そのものは守れます。
- **LOW:** `05-RESEARCH.md` の Open Question 3 は、まだ `DEP-05-REGRESSION` を未充足と書いています。実行正本は `05-VALIDATION.md` と 05-01 の前提です。調査メモを前提確認に使うと、充足済みの依存で停止します。

**Suggestions**

- format は回帰修復と同じく、Python だけを `include` したコマンドに置き換えてください。終了値、差分の有無、Markdown を触っていないことを `05-EVIDENCE.json` に残してください。
- harness と `TestScenarioIsolation` に `pagefolio.plugins._get_plugins_dir` の差し替えを必須にしてください。比較する原本は、設定 JSON、2種の実プロンプト、`plugins/` 配下としてください。
- prohibition 2件は、固定文言の目視結果が `05-UAT.md` に書かれるまで `flagged-unverified` のままにしてください。自動試験の pass で閉じない文を、05-04-02 の acceptance に残してください。

**Risk Assessment:** MEDIUM。証拠と未実施の分離は十分です。format コマンドとプラグイン隔離をそのまま実行すると、検証作業が製品挙動と別の差分を作ります。

## 横断

依存順は現行の欠陥に合っています。Wave 1 が読込状態と終了前の書込抑止を作り、Wave 2 が保存の `bool` と通知の寿命を作り、Wave 3 がその入口へ残りの呼び出しを乗せ、Wave 4 が複合列と証拠を見ます。Wave 2 の前に言語切替や OCR が `_save_settings()` を直接呼ぶ間は、失敗通知も保護解除もそこへ届きません。最終状態の前に途中 wave を完了扱いにしない、という各計画の全件ゲートが、その窓を閉じます。

D-01〜D-18 と V110-CFG-01〜04 は、4計画の対応表に各1回以上現れます。外部プロンプト通知、退避コピー、版同期、実 EXE 受入は、計画の対象外として一貫しています。カバレッジ表の COVERED は「タスクが割り当て済み」という意味であり、既存テストが新しい owner に付いていることまでは示していません。

全体のリスクは **HIGH** です。骨格を実行すれば4要件に届きます。その前に、終了を1回拒否する未承認の裁量、`tests/test_ocr.py` と `tests/test_pagination.py` の更新、モーダル grab 中は通知タイマーを始めないこと、設定パスに加えてプラグインディレクトリを隔離すること、を計画へ書き足す必要があります。

### 変更内容サマリー

**修正対象**: Phase 5 計画レビュー（実装変更なし）

| ファイル | 変更内容 |
|----------|----------|
| なし | リポジトリは読んでおらず、編集していない |

### 修正内容の詳細

05-01〜05-04 を、`pagefolio/settings.py`、`app.py`、`toast.py`、保存呼び出し元、既存テストと照合した。コード変更は行っていない。

### 次セッションへの申し送り

#### 未実施（動作確認・テスト）

- 計画の修正は未実施。pytest も ruff も実行していない。
- 終了保存失敗で閉じない裁量は、利用者の承認が未記録のまま。
- `DEP-05-REGRESSION` の commit `8689c27` が `HEAD` の祖先であることだけ確認した。全件 pytest の再実行はしていない。

#### 注意点・潜在リスク

- 実行に進むなら、05-02 の終了キャンセル、05-03 の `tests/test_ocr.py` と `tests/test_pagination.py`、モーダル中の 10 秒タイマー、`_get_plugins_dir` の隔離、`ruff format` の Python 限定を先に計画へ反映する。
- `05-RESEARCH.md` の依存記述は古い。前提確認は `05-VALIDATION.md` を使う。

#### 実行推奨コマンド（必要な場合）

```
なし（レビューのみ。実装後のゲートは各 PLAN の単一プロセス pytest）
```


---
