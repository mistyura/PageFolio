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
