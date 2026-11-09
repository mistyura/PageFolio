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
