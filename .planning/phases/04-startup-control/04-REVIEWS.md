---
phase: 4
reviewers: [claude, grok, antigravity]
reviewed_at: "2026-10-21T11:32:49.091Z"
plans_reviewed: ["04-01-PLAN.md", "04-02-PLAN.md", "04-03-PLAN.md", "04-04-PLAN.md", "04-05-PLAN.md"]
models:
  claude: "claude-opus-5-5 (reasoning=high)"
  grok: "grok-4.7"
  antigravity: "unknown"
model_sources:
  claude: "pinned"
  grok: "pinned"
  antigravity: "unknown"
---

# Cross-AI Plan Review — Phase 4

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

3者・全5計画のレビュー結果。採否を判断する際は、末尾の [集約・事実確認](#consensus-summary) を優先する。各節の見出し階層とローカルリンクを整え、レビュー本文は保持している。原文は診断証拠へ保存した。

## Claude Review

ソースとの突き合わせは終わりました。ここからレビュー本文をまとめます。

### Phase 4 計画レビュー（04-01〜04-05）

**前提:** 読み取り専用のレビューです。ファイルの変更、テストの実行、コミットはしていません。下の `file:line` は実際にファイルを開いて確認した箇所です。Win32 の挙動についての指摘は、私の知識からの推論である場合はそう書いています。

---

#### 04-01

##### Summary
最初の Wave で二つを片付ける計画です。一つは DoD ゲートの誤判定の修正、もう一つは本番品質の起動 tracer です。DoD の診断は正しいです。`_collect_phase_dirs()` は live のディレクトリをすべて走査対象にするため（`tests/test_gsd_dod.py:129-131`）、未着手の Phase 4 でも赤になります。ただし tracer タスク（04-01-02）は mutex、mapping、overlapped pipe、DACL と label、peer 照合、Tk queue、前面化と点滅、NoticeLease、ネイティブ通知窓をまとめて作り、さらに A1〜A5 を実測する内容です。tracer と呼ぶには大きすぎ、見積もりの 40k tokens・2 tasks とも合っていません。さらに、Windows で単一起動を前面化するときの定石である `AllowSetForegroundWindow` が、全計画を通して出てきません。

##### Strengths
- 存在、所有権、API 失敗の三つを別の結果として扱い、`WaitForSingleObject(0)` で所有権を判定しています。`CreateMutexEx` の initial owner は既存の名前に対しては付与されないので、Win32 の仕様に沿った設計です。
- 共有時刻に `GetTickCount64` を選び、deadline を二次起動の開始時に一度だけ決めています。システム時刻の変更に左右されず、プロセス間で比較できます（A5 の方向性は妥当）。
- 名前付きパイプはセッションごとの名前空間を持ちません。セッション番号と SID を pipe 名に含め、`PIPE_REJECT_REMOTE_CLIENTS`、`FILE_FLAG_FIRST_PIPE_INSTANCE`、peer PID 照合を重ねている点は正しいです。
- 未完了の OVERLAPPED とバッファをプロセス終了まで解放しない、という ctypes で見落としやすい寿命管理まで書かれています。
- `pagefolio/__main__.py:19-26` には現在 `finally` がありません。それを踏まえて try/finally で所有権を閉じる構造を新しく追加する、という認識は正確です。
- 製品に排他を外す CLI や環境変数を作らないと明記しています。

##### Concerns
- **HIGH: `AllowSetForegroundWindow` がない。** Explorer やタスクバーから起動されたとき、前面化の権利を持つのは起動された二次プロセスです。一次プロセスではありません。一次が自分で `SetForegroundWindow` を呼んでも、拒否される経路がよく起こると考えられます（推論）。二次が IPC で要求を送る前に、検証済みの owner PID に対して `AllowSetForegroundWindow(pid)` を呼ぶのが OS が認める方法です。D-14 の「OS 制約を迂回しない」にも反しません。これがないと、D-14 の点滅経路が例外ではなく標準になり、V110-FOCUS-01 の「OS が許せば前面に出る」が実質的に満たせない恐れがあります。
- **HIGH: logon SID による DACL と peer 照合が、昇格プロセスとの共有（A4）を構造的に壊す可能性。** UAC で昇格したトークンと昇格していないトークンは、別のログオンセッションになり、logon SID も別になるはずです（推論。`whoami /logonid` の値が昇格の有無で異なることで確かめられます）。そうだとすると、「現在の logon SID と SYSTEM に限定」「同一 logon を照合」という方式では、medium と elevated の組合せが必ずアクセス拒否になります。A4 は 04-01 の停止条件なので、設計の時点で通らないゲートになりえます。要件の「同一ログインセッション」は TS セッション ID を指しています。user SID と session ID で照合する案と比べて検討すべきです。
- **HIGH: tracer の規模。** 04-01-02 の action は一段落で、`startup_win32.py` の大半（SDDL/ACL、mandatory label、overlapped connect/read/write、CancelIoEx、seqlock、ctypes の WndProc を使う通知窓、NoticeLease）を作らせています。これらはほとんどが 04-02 と 04-04 の仕事を前倒ししたものです。見積もり（40k・confidence low）との差が大きく、途中で止まった場合の巻き戻し単位も大きすぎます。
- **MEDIUM: 実ユーザー環境を汚す。** tracer は subprocess で実際の `main` を起動します。`PDFEditorApp.__init__` は `_load_settings()` を通じて `_get_base_dir()`、つまりリポジトリ直下の実設定を読みます（`pagefolio/settings.py:40-44`, `app.py:148`）。終了時には `_save_window_state()` が実設定を書き換えます（`app.py:574-584`）。設定を一時ディレクトリへ隔離することは 04-05 にしか書かれておらず、04-01〜04-03 の Windows 試験は開発者の `pagefolio_settings.json` を書き換えます。
- **MEDIUM: 本番の固定名で試験すると、開発中の実 PageFolio と衝突する。** 起動中の PageFolio を検出したら中断する方針ですが、中断すると skip 扱いになり、それは不合格と定義されています。したがって開発者がアプリを開いている間は、コミット前の全件 pytest が必ず失敗します。また「検出してから実行する」は原子的ではないので、試験が開発者のウィンドウを前面化してしまう競合も残ります。
- **MEDIUM: A4 は UAC 操作、A3 は目視が必要。** それでも frontmatter は `autonomous: true` です。execute-plan の tracer 規則によれば `<human-check>` があれば checkpoint になりますが、frontmatter と実態が食い違っています。
- **MEDIUM: DoD 修正の順序の落とし穴。** 04-01-01 は「Progress 表の Complete とチェック行 [x] の矛盾」を違反として検出します。一方、execute-plan の `update_roadmap` は SUMMARY の数から Progress 表を自動で `Complete` に書き換えます。04-05 の SUMMARY をコミットした時点で、Progress は Complete、Phase 行は `[ ]`、validate-phase は未実行、という状態になり、全件 pytest が赤になる期間が生じます。また ROADMAP には Phase 行（`ROADMAP.md:117`）と同じ形式の Plan チェック行（`ROADMAP.md:142-154`）が並んでいるので、パーサーは `**Phase N:` で厳密に絞り込む必要があります。
- **LOW: 既存 self-test との互換。** `test_dod_gate_detects_unvalidated_phase` の live ケース（`tests/test_gsd_dod.py:292-296`）は合成ツリーに ROADMAP.md がありません。新しいロジックでは「判定不能」の違反になるので、ラベル一致の assert は通ります。ただし理由文字列の意味が変わるので、意図的な変更として明記したほうがよいです。
- **LOW: A5 の「時刻変更に影響されない」を実測するには、システム時刻を変える必要があります。** 管理者権限が要り、開発機にも影響します。Microsoft の文書で根拠を示せる性質なので、文書の引用で代えるほうが現実的です。

##### Suggestions
- 04-01-02 を二つに分ける。(a) A1〜A5 の成立性を確かめる spike（試験専用または使い捨て）と、(b) mutex、pipe、Tk callback、terminal ACK の最小 tracer です。通知窓と NoticeLease は 04-04 へ移します。
- 二次側の送信直前に `AllowSetForegroundWindow(owner_pid)` を呼ぶ手順を契約に加え、W06/W12 で起動経路ごと（Explorer、ターミナル、EXE）に記録する。
- DACL は SDDL の `D:(A;;<rights>;;;<UserSID>)(A;;GA;;;SY)S:(ML;;NW;;;ME)` 相当にし、照合は user SID と TS session ID で行う案を、A4 の前に机上で比較する。
- 試験の bootstrap では名前空間の接頭辞を注入できるようにし（製品 CLI ではなく bootstrap 内に限る）、大部分の試験を分離された名前で実行する。本番固定名を使う試験は少数に絞り、明示的な marker を付ける。
- DoD の「完了」は Phase 行の `[x]` だけで判定し、Progress=Complete と `[ ]` の組合せは違反ではなく「validate 待ち」として扱う。そうしない場合は、validate-phase を 04-05 の SUMMARY コミットより前に実行する順序を固定する。

##### Risk Assessment
**HIGH。** 方向性は正しいですが、前面化の権利付与が抜けていることと、A4 が構造的に通らない可能性があることの二点で、Wave 1 の停止ゲートで行き詰まる恐れがあります。tracer の規模が過大なことも、そのリスクを大きくしています。

---

#### 04-02

##### Summary
5 秒の絶対期限を一つに固定すること、受信側でも失効を確認すること、500ms の集約、D-07 の一回だけの引継ぎ、の四つを状態遷移として仕上げる計画です。期限の境界値（4999/5000ms）、ACK が期限後に届いた場合、期限前にキューへ入ったが Tk での実行が期限後になった場合、とテスト観点が非常に具体的で、CONTEXT の「受信側にも失効が必要」を正しく実装に落としています。一方で、正常終了直後の再起動が拒否される経路が残っています。

##### Strengths
- `accepted` と terminal を分け、各副作用の直前で期限と generation を再確認する設計は、D-08 の「後から突然前面化する」を構造的に防ぎます。
- D-03 の集約窓を到着のたびに延長しないこと、`foreground_denied` を `completed` に変換しないこと、を明記しています。
- 解放順（listener→失効→IPC→mapping→owner）と、`_quit` の開始を解放条件にしないこと（`app.py:498-507`。キャンセル時は `root.destroy()` されない）を正しく踏まえています。
- `WAIT_ABANDONED` やスレッドの終了をプロセス死と同一視しない、という研究の指摘を反映しています。

##### Concerns
- **HIGH: 正常終了の直後の再起動が「生存しているので拒否」になる経路。** 解放順に「metadata を released にする」手順がありません。mapping は、他のプロセス（待機中の二次プロセスなど）が handle を持っている間、内容が残ります。終了処理中のプロセスは、mutex を解放した後もしばらく生き続けます。atexit による Undo Blob の purge（`pagefolio/undo_store.py:140`）や、非 daemon の `ThreadPoolExecutor` worker の join（`pagefolio/ocr.py:393`）があるためです。この間に利用者が再起動すると、「mutex は取得できたが、古い metadata の PID がまだ生きている」状態になります。計画は「生存または不明なら GUI を増やさない」としているので、起動が失敗します。OCR 実行中に終了してすぐ起動し直す、というよくある操作で V110-START-02 を破ります。
- **MEDIUM: 一次のメインスレッドが重い同期処理中の扱い。** 大きな PDF の保存、`_do_insert`、レンダリング中は 50ms の poll が回りません。その間に二次起動すると、5 秒後に「応答を確認できません」が表示されます。仕様の範囲内ではありますが、Core Value（大きな PDF）と直接ぶつかる場面です。W07 に「一次が忙しい」ケースを明示的に入れるべきです。
- **MEDIUM: 子プロセス生存の上限が 16 秒の試験が全件 pytest に入る。** 2〜8 個の同時起動、ライフサイクル、引継ぎの各試験で、コミットのたびに数分かかる恐れがあります。VALIDATION の目標である 120 秒との整合が計画にありません。
- **LOW: 二次の 5 秒期限は「二次の開始」から測ります。** ところが `pagefolio/__main__.py:8` は `PDFEditorApp`（fitz、PIL、tkinterdnd2、全 Mixin）をモジュールの先頭で import しています。そのため claim の前に重い import が終わってしまい、利用者の体感は 5 秒＋import 時間になります。前面化の権利が失効するまでの時間にも効きます。

##### Suggestions
- 所有者は mutex を解放する前に、mapping へ `state=released`（pid=0、generation を進める）を書き込む。後続は「released なら古い PID の生死を問わず一次になれる」とする。この遷移を lifecycle 試験で固定する（OCR worker が残っている状態の模擬を含める）。
- `__main__.py` の app import を claim の後へ遅らせ、二次は Win32 の境界だけを読み込むようにする。
- Windows subprocess 試験の合計時間に予算を設定し（例: 60 秒）、超える分は fake clock 側へ移す。

##### Risk Assessment
**MEDIUM-HIGH。** 状態機械の設計は優れていますが、metadata の released 化がないために、正常終了後の再起動という基本要件が条件次第で失敗します。

---

#### 04-03

##### Summary
既存の app/doc/Undo/OCR を作り直さずに、最小化前の状態、入力先、最も深いモーダルへ戻す計画です。D-01、D-02、D-04、D-13〜D-16 の対応は網羅されています。ただし、モーダル対象を見つける方法が PageFolio の実際のダイアログ構造と合っていません。

##### Strengths
- `_set_status` やトーストを呼ばないことを観測する試験（D-01）、`focus_force`、topmost、`AttachThreadInput`、擬似キー入力を禁止していること（`app.py:651-652` の `focus_force` を流用しない判断を含む）が適切です。
- 最小化中の `GetWindowPlacement` から過去の最大化状態を推測せず、iconic/withdrawn への遷移で保存値を上書きしない、という研究の注意点を反映しています。
- 点滅の停止 callback が前面化、focus、lift をしないことを明示し、D-16 の「後から勝手に前面化しない」を守っています。
- 04-03-02 で、未保存の doc、4 手の Undo/Redo、遅延させた fake provider による OCR を実際の処理経路で通し、同一性を assert します。成功した回数だけを証拠にしない点が良いです。

##### Concerns
- **HIGH: 最深モーダルの発見が実際のダイアログ構造と合わない。**
  - 入れ子の grab は元に戻りません。`SettingsDialog` が `grab_set()`（`dialogs/settings.py:36`）し、そこから開く `LLMConfigDialog` も `grab_set()` します（`dialogs/llm_config/dialog.py:82`）。Tk の grab は一つだけなので、LLMConfig を閉じると grab はなくなり、親側で張り直す処理もありません（`dialogs/settings.py:209-250`）。その状態では `grab_current()` が None を返し、Settings が開いたままなのに root を前面化します。Settings を隠してしまうので D-13 違反です。
  - 所有関係がありません。grab を使うダイアログ 11 か所（`ocr_dialog.py:156`, `batch_ocr.py:169` など）はどれも `transient()` を呼んでいません。呼んでいるのは `viewer.py:496` だけです。`GetLastActivePopup` は Win32 の所有関係を前提にしているので、所有されていない Toplevel は見つけられないと考えられます（推論）。
  - ネイティブの messagebox の多くは `parent=self` でダイアログに所有されています（`llm_config/sections.py:1469,1504,1547,1568`、`llm_config/dialog.py:554,568`）。そのため root から辿る方法では見つかりません。
- **MEDIUM: HWND の取り方が書かれていない。** Tk の `winfo_id()` は内側の子ウィンドウで、トップレベルのフレームは `wm_frame()` の値か `GetAncestor(GA_ROOT)` で得ます。ここを間違えると `SetForegroundWindow` や `FlashWindowEx` が別の窓に効きます。
- **MEDIUM: 入れ子のイベントループでの再入。** `_quit` の `askyesno`（`app.py:501`）をはじめ、ネイティブダイアログの表示中にも Tk の after は処理されるはずです（推論）。その場合、終了確認の最中に復帰 callback が動きます。W08 の「キャンセルで維持」は試験しますが、「確認ダイアログの表示中に二次起動」したときの対象選択（確認ダイアログを選ぶべき）が明示されていません。
- **LOW: root への `<Configure>` と `<FocusIn>` の bind。** root の bindtag はすべての子ウィジェットに含まれるので、子の Configure が大量に流れてきます。`event.widget is root` で絞り込まないと、描画中に負荷が増えます。
- **LOW: D-02。** 最大化から最小化した窓は、`SW_RESTORE` だけで最大化に戻るのが Windows の通常の挙動です。「SW_RESTORE の後に保存状態に従って geometry を復元する」と書かれていますが、無条件に復元すると OS の復元と競合して、ちらつきや別モニターへの移動を起こします。

##### Suggestions
- 復帰対象は、同じプロセス・同じスレッドの可視で有効なトップレベルを `EnumThreadWindows` で列挙して選ぶ。親が無効化されている子を優先し、Z オーダーが最も上のものを採る。`grab_current()` は補助的な手掛かりにとどめる。
- 「Settings→LLMConfig→閉じる→Settings だけ残る」「OCRDialog の上の messagebox（parent=dialog）」「`_quit` の askyesno の表示中」の三つを W05/W08 と自動試験に明示的に加える。
- HWND は `wm_frame()` または `GetAncestor(GA_ROOT)` に統一し、`OwnedHandle` と同じく型付きの helper に閉じ込める。
- D-02 は「SW_RESTORE を実行して状態を確認し、違うときだけ補正する」と文言を固定する。

##### Risk Assessment
**MEDIUM-HIGH。** 状態を保つ方針は良いものの、D-13（ダイアログを隠さない）が実際のダイアログ構造で破綻する可能性が高いです。

---

#### 04-04

##### Summary
編集画面を作る前の失敗を、3 分類、日英の表示、非活性、10 秒、原因ごとのプロセス間集約で案内する計画です。D-09 の「確認できた事実だけを表示する」、表示文言に技術的な詳細を出さないこと、5 秒の判定 deadline と 10 秒の通知 deadline を別オブジェクトにすること、と主要な契約は正しいです。

##### Strengths
- ToastManager に依存しない独立経路は正しい判断です。ToastManager は `_build_ui` の後でしか存在しません（研究で確認済み）。
- 起動の所有権と通知の所有権を分け、同じ原因の後続起動が共有期限を書き換えられない設計にしています。
- `test_lang_parity.py:40-43,55-75`（キー集合の一致と未使用キーの検出）を検証に含めています。
- 正常復帰と前面化拒否を案内の関数へ入れない、と経路を分けています（D-14）。

##### Concerns
- **MEDIUM: NoticeLease へのアクセスが拒否されたときの実行時の動作が決まっていない。** 計画には「既存案内ありと断定しない」「解決できなければ実装完了を止める」とあります。しかし、実行時にその状況になったとき、案内を出すのか出さないのかが書かれていません。もし出さなければ、黙って終了することになり V110-START-03 違反です。
- **MEDIUM: 言語判定。** `GetUserDefaultUILanguage` を使うと、アプリ内で英語を選んでいる利用者にも日本語の案内が出ます。副作用を避けることが目的なら、`_load_settings()` を使わずに JSON から `lang` だけを読み取り専用で読む方法があります（`settings.py:254` 以降。Phase 5 の自動保存の問題からも独立できます）。
- **LOW: ネイティブ窓の DPI。** リポジトリには DPI awareness の設定がありません（`ctypes`/`DpiAwareness` の grep で 0 件）。高 DPI では文字がぼやけ、サイズも崩れる恐れがあるので、W09 で確認すべきです。
- **LOW: ctypes で `WINFUNCTYPE` の WndProc を作るときは、参照を保持し続けないとクラッシュします。** 計画には明記がありません。
- **LOW: 「期限後の 15 秒間に自動復帰しないこと」の観測を全件 pytest に含めると、時間がかかります。**

##### Suggestions
- lease へのアクセスが拒否された場合は、案内を表示する（最大 10 秒でプロセスも終わる）という fail-open を明文化する。重複表示は、黙って失敗するより害が小さいという判断です。
- 言語は「設定 JSON を読み取り専用で読み、失敗したら OS の UI 言語」の二段にする。
- WndProc の参照を保持すること、DPI の扱いを action に書く。

##### Risk Assessment
**MEDIUM。** 設計は筋が通っています。残る課題は 04-01 由来の A3/A4 の成立と、拒否時の動作の明文化です。

---

#### 04-05

##### Summary
自動受入と Windows 実機の W01〜W12 を分けて記録し、未実施を合格と混同しないための締めの計画です。ケースと D-01〜D-16 の対応表、計測する項目（tick、前面の HWND、画面数）、実 EXE の確認は Phase 6 へ明示的に引き継ぐこと、と証跡の設計は良いです。

##### Strengths
- 自分で起動した PID だけを回収すること、既存の PageFolio を終了させないこと、設定とプロンプトを一時ディレクトリへ隔離すること、利用者ファイルの hash を照合すること（T-04-16）。
- `sys.frozen` の差は identity 関数の試験だけで扱い、実 EXE を試した証拠とは混同しない、という線引き。
- 全件 pytest は単一プロセスで別に実行して所要時間を記録し、分割実行の合算で代えないこと（REQUIREMENTS.md:71）。

##### Concerns
- **MEDIUM: W11（別ログインセッション）が用意できないと、Phase が完了できない。** 「準備不能なら not-run のまま、Phase 4 の受入を合格にしない」と定めています。利用者がアカウントを一つしか持っていない場合、Phase が永久に止まります。代わりに認める手段（2 つ目のアカウントでのユーザー切替など）か、利用者が明示的に受容する手順を事前に決めておくべきです。
- **MEDIUM: 設定とプロンプトの隔離が 04-05 で初めて導入される。** 04-01〜04-03 の試験は、この時点ですでに実設定を書き換えています（04-01 の懸念を参照）。
- **MEDIUM: DoD ゲートとの順序。** 04-01 で述べた「Progress=Complete になってから validate-phase を実行するまでの赤い期間」は、まさにこの計画の SUMMARY をコミットした時点で起きます。
- **LOW: W06 の「OS が許可した試行は拒否の実測に数えない」** は正しい方針です。ただし `AllowSetForegroundWindow` を導入した後は拒否が起きにくくなるので、拒否を実機で観測するための条件（他アプリで入力中、フォアグラウンドロックのタイムアウトなど）を手順に書いておく必要があります。

##### Suggestions
- 設定とプロンプトの隔離 fixture は 04-01 の tracer で作り、以降のすべての Windows 試験で共有する。
- W11 の代わりの手段と、受容を判断する人を決めておく。
- 「04-05 の SUMMARY→validate-phase→ROADMAP の `[x]`→全件 pytest」の順序を、DoD の判定規則と一緒に固定する。

##### Risk Assessment
**MEDIUM。** 記録の設計は堅いですが、完了条件が実行環境（別セッション）と DoD の自動判定の両方に依存しています。

---

#### 計画全体の評価

**全体の判定: MEDIUM-HIGH。** 先に直すべき 3 点は次のとおりです。

1. **`AllowSetForegroundWindow` の追加（04-01/04-03）。** これがないと、通常の起動でも前面化が拒否される経路が多くなり、V110-FOCUS-01 の主経路が点滅だけになる恐れがあります。
2. **昇格トークンでの logon SID の扱い（04-01 の A4）。** UAC の昇格では logon SID が別になる可能性が高いです。現在の DACL と照合の方式では、Wave 1 の停止ゲートが構造的に通らない恐れがあります。user SID＋TS session ID と比べて検討すべきです。
3. **mapping の released 化（04-02）と、モーダル発見方法の修正（04-03）。** 前者は正常終了直後の再起動（V110-START-02）を、後者はダイアログを隠さないこと（D-13）を守るために必要です。

**その他の横断的な懸念:**

- **試験と品質ゲートの緊張関係。** 「単一プロセスの全件 pytest をコミットのたびに実行」「対象の Windows で skip すれば不合格」「本番の固定名で試験」の三つが重なっています。その結果、開発者がアプリを開いているだけで全件 pytest が失敗し、試験自体がデスクトップの前面化や点滅を起こします。名前空間の注入と marker の方針を 04-01 で決めるべきです。
- **規模と見積もり。** 5 計画とも confidence は low で、特に 04-01-02 が過大です。計画間の分担も重なっています（通知 primitive が 04-01 と 04-04 の両方にある）。
- **良い点。** 期限、失効、ACK の区別、未実施と合格の分離、脅威モデル、新しい依存をゼロに保つこと、`pyproject.toml` を変更しないこと、のいずれも徹底されています。CONTEXT の 16 決定への対応漏れはありません。

---

## Grok Review

Phase 4 の5計画を、計画文だけでなく参照先の実コードと照合してレビューします。まず計画本文と起動・終了・ダイアログの実装箇所を読みます。Phase 4 の5計画は、起動判定を Tk 生成前に置く点と、失敗時に画面を増やさない点は現行の入口と要件に合っています。このまま実装へ進むと、通常の2回目起動で前面に出せない、同時起動でパイプが塞がる、試験用の実 `main()` が開発者の設定ファイルを書き換える、の3点がフェーズ目標を外します。

#### 04-01

品質ゲートの修正と、失敗すれば後続を止める本番 tracer という分割は妥当です。Task 2 が mutex、共有メモリ、pipe、ACL、整合性レベル、非活性窓、Tk 接続を1タスクに束ねており、同時接続と前面化の委譲が動作として書かれていません。

##### 強み
- 現行の `main()` は `TkinterDnD.Tk()` または `tk.Tk()`、`PDFEditorApp`、D&D、`mainloop()` の順です（`pagefolio/__main__.py:19-26`）。排他をその前に置く契約は、この順序に対して正しいです。
- `tests/test_gsd_dod.py:115-181` は `.planning/phases/` の全ディレクトリに `status: validated` を要求します。ライブの `04-VALIDATION.md` は `status: draft` なので、今の全件失敗の説明と一致します。未完了ライブだけを外し、アーカイブ済み v1.9.0 は従来どおり必須、という方針は `PROJECT.md:330-342` の意図を保ちます。
- A1〜A5 が1件でも未実施または不合格なら 04-02 へ進まない、という停止条件は明確です。未知世代の拒否、1024 bytes 上限、worker から Tk を触らない、という境界も要件に沿っています。

##### 懸念
- **HIGH**: 前面化を既存プロセスの `SetForegroundWindow` 1回に固定しています（04-01 の Task 2、04-03 も同じ）。ユーザー操作で起動するのは2回目のプロセスで、前面化の許可はそちらが持つのが Windows の規則です。計画内に `AllowSetForegroundWindow` がなく、tracer は pytest が起動した子プロセス同士で成功し得ます。親が前面にある子は、別アプリが前面の本番操作より許可されやすいです。
- **HIGH**: pipe の同時受付が未定義です。`CreateNamedPipe` のインスタンス数を書かない場合、既定は1本です。先に接続した二次起動が完了 ACK まで接続を保持すると、他の二次起動は `ERROR_PIPE_BUSY` になります。V110-START-01 の同時起動と、04-02 の2〜8プロセス試験がここで落ちます。`FILE_FLAG_FIRST_PIPE_INSTANCE` は2本目以降に付けると作成自体が失敗します。
- **HIGH**: 実 `main()` の子プロセスは、リポジトリ直下の設定を読み書きします。`PDFEditorApp.__init__` は `_load_settings()` を呼び（`pagefolio/app.py:148`）、`_quit` は確認ダイアログの前に `_save_window_state()` へ進みます（`pagefolio/app.py:498-507`、`574-584`）。パスはカレントディレクトリではなく `pagefolio/settings.py:32-49` の `_get_base_dir()` です。04-05 まで設定の隔離が無く、隔離方法も `files_modified` に含まれていません。
- **MEDIUM**: mutex の所有スレッドを「明示する」としか書いていません。IPC worker が取得して終了すると、GUI プロセスが生きたまま mutex は abandoned になります。04-02 はその状態を引継ぎ不可の起動失敗にします。
- **MEDIUM**: A4 の合格条件が所有権と `NoticeLease` です。mapping の読取と pipe 接続が、medium 作成・elevated 作成の両順に含まれていません。
- **MEDIUM**: `requirements` に V110-FOCUS-02 まで入っています。この計画の試験は通常 root への復帰 tracer で、未保存編集、Undo、OCR、モーダルの同一性は見ません。計画完了時に要件完了へ倒すと、04-03 より前に達成扱いになります。

##### 提案
- Task 2 の復帰契約に、二次プロセスが接続直後に `AllowSetForegroundWindow(一次PID)` を呼ぶ順序を追加する。その後に一次の Tk スレッドが対象 HWND へ `SetForegroundWindow` を1回呼ぶ。戻り値 0 のときだけ有限の `FlashWindowEx` に進む。tracer は別窓を前面にした状態で二次起動し、pytest の子同士だけで成功にしない。
- pipe は接続ごとにインスタンスを張り、同時受付数を8以上にする。最初の1本だけ `FILE_FLAG_FIRST_PIPE_INSTANCE` を使う。`ERROR_PIPE_BUSY` は同じ5秒期限の中で再接続し、通信失敗へ分類するのは受付不能が期限まで続いたときだけにする。
- 04-01 の Windows 試験から、子プロセスの設定・プロンプト・プラグイン読込を一時ディレクトリへ隔離する。`_get_base_dir()` は `__file__` 基準なので、作業ディレクトリの変更では隔離できません。製品の排他を外す環境変数は作らない、という既存制約のまま、試験プロセスだけパスを差し替える。
- mutex はメインスレッドがプロセス寿命のあいだ保持すると書く。`CreateMutexExW` のアクセスマスクに `SYNCHRONIZE` と解放に必要な権限を含める。
- A4 の実測に、mapping の snapshot 読取と pipe の双方向接続を追加する。

##### リスク評価
**HIGH**。停止ゲートは良い一方、ゲートを通る tracer が本番の前面化と同時起動を代表しません。設定ファイルを上書きし得ます。

#### 04-02

5秒を1回だけ決め、死亡確認と mutex 再取得がそろったときだけ1回引き継ぐ、という D-07 の中核は正しいです。同時起動の集約と、残った mapping の上書きが未完了です。

##### 強み
- 終了確認のキャンセルで排他を解放しない、という指定は現行の `_quit` と一致します。確認は `messagebox.askyesno` でブロックし、Yes のときだけ `root.destroy()` します（`pagefolio/app.py:498-507`）。`mainloop` 終了後の `finally` でだけ mutex を閉じる契約なら、No のあいだ既存画面は残ります。
- `WAIT_ABANDONED` や公開前死亡をプロセス死亡の証拠にしない、期限後の ACK を成功にしない、`foreground_denied` を `completed` へ変えない、という禁止は D-07 と D-08 を満たす書き方です。
- 二次プロセスの上限が、正常 5.5秒、即時失敗の案内 10.5秒、待機後案内 15.5秒と分かれており、試験の16秒打ち切りと対応しています。

##### 懸念
- **HIGH**: 集約窓は最初の `completed` または `foreground_denied` の時刻から500msです。それより前に queue へ入った別 ID は、どちらも副作用の対象です。04-01 で複数 pipe を受けると、短い連打が2回復帰します。D-03 が防ぎたいのはこの連打です。
- **MEDIUM**: mutex を取れても古い metadata が残る場合は生存確認、とあります。二次側が mapping を開いたままだと、名前付き mapping は一次死亡後も残ります。勝者が `CreateFileMapping` の既存オープンを失敗と扱うと、死亡を確認したのに新しい generation を公開できません。
- **MEDIUM**: 所有スレッドだけ死んでプロセスが生きている場合を「起動失敗」へ進める、とあります。そのプロセスの pipe が生きていれば、既存画面への連絡が先です。失敗案内へ直進すると、画面は1つのまま復帰できません。
- **LOW**: 04-02-01 の verify は `-k "deadline or expired or coalesce or protocol"` です。`04-VALIDATION.md:39` はファイル全体をコマンドにしています。実行者がどちらか一方だけを記録すると、欠けるケースを見落とし得ます。

##### 提案
- 処理中の要求がまだ terminal でないあいだに着いた別 ID も、同じ復帰1回へまとめる。窓の開始を「最初の副作用の開始」にし、完了後500msは今の仕様どおり延長しない。
- mutex の勝者は、既存 mapping を seqlock で上書きして新しい generation を公開する、と明記する。生存中または確認不能のプロセスがいるときだけ GUI を作らない。
- abandoned でプロセスが生存しているときは、取得した mutex を返したあと、同じ残余時間でその pipe へ復帰要求を送る。

##### リスク評価
**HIGH**。引継ぎの証拠条件は十分です。同時起動の1回復帰は、04-01 の pipe 仕様が補われない限り試験で赤になるか、誤って複数回前面化します。

#### 04-03

最小化前の状態をメモリに持つ判断は、現行の保存形式では最大化を復元できないことへの正しい対策です。前面化の呼び出し元と、フォーカスの観測位置が、実際の Tk の届き方とずれています。

##### 強み
- 設定に残るのは `root.geometry()` の文字列だけです（`pagefolio/app.py:574-580`）。起動時もその文字列を戻すだけです（`pagefolio/app.py:156-164`）。最小化中の `GetWindowPlacement` から最大化を推定しない、という決定はここを補います。
- メイン画面のキーボード対象は、サムネイルの `thumb_canvas`（`pagefolio/ui_builder.py:245`）と、トリミング中にフォーカスを取る `preview_canvas`（`pagefolio/page_ops.py:403-405`）です。プレビューへ一律に移さない、という D-04 は後者の既存処理と衝突しやすいので、専用の `FocusRestorer` に分けるのは適切です。
- モーダルは `grab_set()` が広く、設定は `pagefolio/dialogs/settings.py:36`、OCR は `pagefolio/ocr_dialog.py:156` です。最深の grab を優先し、ダイアログを閉じたり作り直したりしない契約は D-13 に合っています。終了確認は `tkinter.messagebox` なので、grab に出ない native ダイアログを `GetLastActivePopup` で見る分岐も必要です。
- OCR の世代は `OCRDialog._run_gen`（`pagefolio/ocr_dialog.py:202`）で、実行系は `pagefolio/ocr.py:393` の `ThreadPoolExecutor` です。04-03-02 がこの世代と worker の継続を見にいく指定は、実在する経路です。

##### 懸念
- **HIGH**: 前面化の本体がここでも一次プロセスの `SetForegroundWindow` 1回です。04-01 に許可の委譲が無いため、他アプリが前面の通常操作では拒否が通常経路になり、タスクバー点滅だけが残ります。D-14 の拒否時動作としては整合しますが、成功条件4の「OS が許せば前面」は、許可を持たないプロセスからの呼び出しではほとんど起きません。
- **HIGH**: `last_focus_widget` を root の `FocusIn` で観測する、とあります。Tk の `FocusIn` はフォーカスを得た widget に届き、親の root へは伝播しません。root への `bind` では、入力欄や `thumb_canvas` の移動を記録できません。
- **MEDIUM**: 既存の再表示は `lift()` と `focus_force()` です。設定の再表示が `pagefolio/app.py:650-652`、設定内の別ダイアログが `pagefolio/dialogs/settings.py:217` と `261`、OCR から開く LLM 設定が `pagefolio/ocr_dialog.py:1014-1016` です。復帰処理がこの形を流用すると、D-04 と D-16 に反します。
- **MEDIUM**: メイン編集画面に `Entry` はありません。入力欄はモーダル内です。合成 `Entry` だけで D-04 を合格にすると、`thumb_canvas` と `preview_canvas` のどちらを維持するかが未検証のまま残ります。
- **LOW**: `startup_focus.py` から `app.py` を import すると、`app.py` が fitz と Tk を抱えたまま循環します。計画は生成方向を指定していません。

##### 提案
- 04-01 で受け取った前面化許可のあと、対象 HWND へ1回だけ `SetForegroundWindow` する。許可が無い、または戻り値が 0 のときは `FLASHW_TRAY`、3回、250ms のままにし、2秒後の `FLASHW_STOP` 以外の `after` を予約しない。
- フォーカス観測は `bind_all("<FocusIn>")` にし、このプロセスの生存 widget だけを記録する。復帰時は `winfo_exists()` を確認し、対象を前面化できたあとにだけ `focus_set` する。破棄時に `unbind_all` する。
- 試験の実 widget は `thumb_canvas`、`preview_canvas`、`SettingsDialog` 内の入力、終了確認の `messagebox` にする。`selected_pages`、ダイアログの文字列と selection、`grab_current()` が復帰の前後で同じことも比較する。
- `FocusRestorer` は `__main__` から組み立て、`app.py` は属性を受けるだけにする。

##### リスク評価
**HIGH**。状態の記憶とモーダル優先は実装可能です。フォーカス観測と前面化の呼び出し元を直さないと、自動試験の偽成功のあとで実機の W02 と W06 が落ちます。

#### 04-04

確認できた事実だけで3種類の文言に分け、編集画面と `ToastManager` を使わない、という方針は現行構造に合っています。案内の生存確認が「mutex が存在する」だけだと、落ちた案内のあとで後続が無言終了します。

##### 強み
- `ToastManager` は構築済みの `app` に載せます（`pagefolio/toast.py:33-40`）。判定失敗は `PDFEditorApp` の生成前なので、別の native 窓にする判断は正しいです。
- 文言の使い分けは D-09 に合っています。所有者を確認できた通信失敗だけが「起動済みの画面に接続できませんでした」で、判定不能と時間切れは起動済みと断定しません。
- 日英キーは引用符付きの完全一致で未使用を検出します（`tests/test_lang_parity.py:55-75`）。キーをコードの文字列リテラルとして参照する必要があります。
- 案内の10秒と、二次起動の5秒を別の期限にする、という指定は D-06 と D-10 の混同を防ぎます。

##### 懸念
- **MEDIUM**: 既存 lease の検証で、プロセス死亡後の `WAIT_ABANDONED` を「案内表示中」と扱う余地があります。名前付き mutex は最後の handle が閉じるまで残ります。後続がそれを既存案内とみなして即終了すると、窓は出ていないのに D-11 の再表示も起きません。強制終了後に永久抑止しない、という試験意図とは逆の実装が通り得ます。
- **MEDIUM**: 案内言語を `GetUserDefaultUILanguage` に固定すると、アプリ内の `settings["lang"]` とずれます。計画はこの差を記録する、と書いてあり、Phase 5 の設定失敗通知までは作りません。`_load_settings()` は破損 JSON を飲み込んで既定値を返します（`pagefolio/settings.py:301-311`）。案内のためにこれを読むことは、Phase 5 の新しい通知にはなりません。
- **LOW**: 04-04 は案内の完成なのに 04-03 完了が依存条件です。共有する `__main__.py` と `startup_win32.py` を直列にする理由にはなります。前面化の欠陥が 04-03 に残ったまま案内だけ完成し得ます。

##### 提案
- lease の取得結果を3つに分ける。新規取得と `WAIT_ABANDONED` は、そのプロセスが初回表示から10秒の案内を出す。生存中の所有者を確認できたときだけ、窓を作らず終了する。アクセス拒否は「既存案内あり」にしない。
- 案内言語は、設定読込が既定値へ落ちた場合を含めて `settings` の `lang` を使う。OS 言語は設定が読めない場合の予備にする。
- `startup_notice_*.py` 側の参照は `"startup_notice_check_failed"` のように引用符付きのキー文字列を残す。`lang.py` 内の定義だけでは未使用検査を通りません。

##### リスク評価
**MEDIUM**。分類、10秒、非活性の骨格は足りています。lease の死亡判定を書き足さないと、連打抑止が「案内を出さない」側へ倒れます。

#### 04-05

自動結果と実機結果を分け、未実施を合格にしない記録方式は、このフェーズに必要です。Phase 4 の成功条件に含まれる EXE 混在が、この計画の完了条件からは外れています。

##### 強み
- W01〜W12 は、最小化、入力先、Undo、OCR、モーダル、拒否、5秒、終了、連打、権限、別セッション、入口差を1回ずつ割り当てています。`autonomous: false` の human checkpoint は、OS の前面化と別セッションを mock の成功で代替しないために必要です。
- 既存の PageFolio を検出したら終了させず試験を中断する、自分が起動した PID だけ回収する、という制約は安全です。固定名 `Local\PageFolio.Startup.Owner` を試験でも使う以上、この中断は必須です。
- 実 EXE を実施済みと書かない、`sys.frozen` の識別子試験と配布物試験を分ける、という記録ルールは明確です。配布コマンドの入口は `pagefolio.py` で、中身は同じ `main()` です（`docs/DEVELOPMENT.md:70`、`pagefolio.py:11-14`）。コード経路の一致と、ビルド済み EXE の一致は別の証拠です。

##### 懸念
- **HIGH**: ロードマップの成功条件1は、対応版の Python/EXE 混在でも編集画面が1つ、です（`.planning/ROADMAP.md:131`）。04-05 は実 EXE を Phase 6 へ送り、Phase 4 完了の必須ケースに入れていません。Phase 6 の成功条件4も、同じ EXE での起動・復帰を見ます（`.planning/ROADMAP.md:175-181`）。Phase 4 を完了にすると、条件1の EXE 部分が未観測のまま達成になります。`--noconsole` の onedir では、コンソールへ出した失敗が利用者に見えません。案内が native 窓であることは計画どおりなら満たせますが、その確認が Phase 4 の証拠にありません。
- **MEDIUM**: W11 の別ログインセッションが not-run なら Phase 4 全体を不合格にします。要件どおりの厳しさです。手順が「別セッションを用意する」だけで、Fast User Switching の観測手順がありません。準備できない環境ではフェーズが止まったままになります。
- **MEDIUM**: 全件 pytest のたびに本番名の mutex と実 Tk を使います。開発者の PageFolio が起動中ならスイート全体が中断します。04-01 の設定隔離より前の試験は、中断しない場合に実設定を書き得ます。
- **LOW**: 04-05-01 は `04-VALIDATION.md` を更新しますが、`status: draft` の維持は Task 2 の validate-phase 実走後だけ、と二重に書いてあります。実行途中の編集で `validated` に上げない旨は、Task 1 の action に残す必要があります。現状の文面は残っています。

##### 提案
- Phase 4 の成功条件1に、実配布 EXE の混在確認は Phase 6 の V110-QA-02、Phase 4 は同じ `main()` と固定オブジェクト名まで、と1行追加する。追加しない場合は、04-05 に現行コマンドでの一時 onedir 起動を必須観測として入れる。サンプル同梱の正本作業は Phase 6 のまま分ける。
- W11 に、セッション ID の記録方法と、別セッションで1画面ずつ起動して互いの画面が増えないことの観測欄を、実行担当が追加調査なしで使える粒度で書く。
- 自動の前面化試験は、別プロセスの窓を前面にしてから二次起動する。pytest の子プロセスが前面許可を継承した成功は、W06 の実機合格と別欄のまま維持する。

##### リスク評価
**MEDIUM**。記録の分離は信頼できます。EXE の成功条件を計画文のどこかで揃えないと、Phase 4 完了の宣言がロードマップの文面より広くなります。

#### 横断のリスク

全体リスクは **HIGH** です。D-07 の引継ぎ、受信側の失効、DoD の未完了判定、失敗案内の3分類は、この順で実装してよい水準です。次の3点は計画を直してからが安全です。

| 箇所 | 欠落 | 影響 |
|------|------|------|
| 04-01 Task 2 と 04-03 | 二次プロセスから一次 PID への `AllowSetForegroundWindow` が無い | 通常の2回目起動が拒否扱いになり、点滅だけになる |
| 04-01 の pipe | 同時インスタンスと、処理中要求の集約が無い | 同時・連打で `PIPE_BUSY` か複数回前面化 |
| 04-01〜04-03 の実 `main()` | 子プロセスの設定パス隔離が 04-05 まで無い | `pagefolio_settings.json` の上書き |

この3点を計画へ書いたあとも、A1〜A5 の停止条件は維持するのが妥当です。tracer の合格条件に、別窓が前面の状態での前面化、2プロセス以上の同時接続、試験後に開発者設定のハッシュが変わらないこと、を追加すると、後続の手戻りが減ります。

実コードの入口、終了処理、設定パス、DoD、言語キー検査、OCR 世代は、上記の行番号で照合済みです。テストの実行とファイルの変更はしていません。

##### 変更内容サマリー

**修正対象**: Phase 4 計画レビュー（実装変更なし）

| ファイル | 変更内容 |
|----------|----------|
| なし | 読み取り専用。計画5件と起動・終了・設定・DoD・言語検査の実装を照合した |

##### 修正内容の詳細

製品コードと計画ファイルは変更していません。レビュー結論は、5計画の骨格は要件 D-01〜D-16 に沿う一方、前面化の許可委譲、pipe の同時受付、実 `main()` 試験の設定隔離が未記載で、このままの実行はフェーズ目標を外す、です。

##### 次セッションへの申し送り

###### 未実施（動作確認・テスト）

- 計画の修正は未着手。実装、pytest、ruff は未実行。
- A1〜A5 の Windows 実測は計画上も未実施のまま。

###### 注意点・潜在リスク

- 修正の優先順は、`AllowSetForegroundWindow` の呼び出し位置、pipe の複数インスタンスと処理中の集約、子プロセスの設定隔離。
- `.planning/ROADMAP.md:131` の EXE 混在と、Phase 6 へ送る実 EXE 検証の文面を、実装開始前に揃える。
- `ROADMAP.md` の過去 `<details>` 内に `[x] Phase 4` が5件ある（32、48、61、74、87行）。DoD パーサの合成試験は、この形を入力にする。

###### 実行推奨コマンド（必要な場合）

```
なし（計画修正前のため試験は走らせない）
```

---

## Antigravity Review

#### 04-01

##### 1. Summary
`04-01` は、現行リポジトリで唯一失敗している DoD 機械ゲート（[tests/test_gsd_dod.py:185-204](C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py:185)）の不整合を解消する前提タスク（`04-01-01`）と、Windows 名前付きミューテックス・共有メモリ（pagefile-backed mapping）・非同期（overlapped）名前付きパイプ・非活性通知ウィンドウを組み合わせた本番起動 tracer（`04-01-02`）の 2 タスクで構成されている。計画段階の未実証事項 A1〜A5 を `04-TRACER-EVIDENCE.md` に実測記録し、1 件でも未実施・不合格であれば `04-02` 以降へ進まないハードゲートを敷いている点は堅실である一方、Task 2 単体に詰め込まれた Win32 `ctypes` 実装範囲（DACL/SACL Mandatory Label 構築、Overlapped Pipe、共有メモリ seqlock、Win32 ネイティブウィンドウ生成）が非常に大きく、実装複雑性と境界バグのリスクが高い。

##### 2. Strengths
- **DoD ゲートの抜け穴を作らない設計**: [tests/test_gsd_dod.py:115-143](C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py:115) の `_collect_phase_dirs()` が `.planning/phases/` 配下の未完了フェーズ（`04-startup-control`）まで無条件に列挙し、[tests/test_gsd_dod.py:156-181](C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py:156) の `_collect_dod_violations()` が `status: validated` を要求して失敗している現状に対し、`04-VALIDATION.md` の偽装昇格やテスト除外ではなく、[.planning/ROADMAP.md:111-156](C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md:111) および [.planning/ROADMAP.md:204-208](C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md:204) の現行マイルストーン定義と照合して「未完了 live のみ猶予・完了 live と対象 archive は必須・ROADMAP 記載不備や状態矛盾は違反」とする方針が、[tests/test_gsd_dod.py:249-330](C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py:249) の合成ツリー self-test 構造と完全に整合している。
- **GUI 構築前の排他判定位置の明確さ**: [pagefolio/__main__.py:19-26](C:/Users/shdwf/work/project/PageFolio/pagefolio/__main__.py:19) の `main()` は現在 `TkinterDnD.Tk()` / `tk.Tk()` 生成直後に [pagefolio/app.py:138-218](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:138) の `PDFEditorApp(root)` を呼び、設定読込・プラグイン読込・UI 構築・Undo スタック初期化まで一気に実行する。また [pagefolio.py:11-14](C:/Users/shdwf/work/project/PageFolio/pagefolio.py:11) も `pagefolio.__main__.main` に委譲しているため、`main()` の root 生成前に `StartupCoordinator.claim()` を置くことで Python 両起動経路の副作用を確実に遮断できる。
- **Tk スレッド安全性の遵守**: IPC 受信スレッドから Tkinter API（`root.after` 含む）を一切呼ばず、`queue.Queue(maxsize=32)` への投入のみを行い、メインスレッド側の `root.after(50, ...)` ポーリングで取り出す設計は、[AGENTS.md:81-83](C:/Users/shdwf/work/project/PageFolio/AGENTS.md:81) の Tkinter メインスレッド制約に合致している。

##### 3. Concerns
- **[HIGH] Task 2 (`04-01-02`) の Win32 セキュリティ記述子・Overlapped I/O・ネイティブウィンドウ一括実装による複雑性とバッファ寿命リスク**:
  - `04-01-02` では標準 `ctypes` のみで (1) Logon SID 抽出と DACL + Medium Mandatory Label（SACL）構築、(2) `CreateFileMappingW` + seqlock 共有メモリ、(3) Overlapped Named Pipe + `CancelIoEx`、(4) `CreateWindowExW` + カスタム `WNDPROC` による非活性ウィンドウを 1 タスクで新規作成する計画となっている。
  - 特に Python の `ctypes` で `CancelIoEx` 後に 500ms で cleanup を打ち切る際、「完了未通知の `OVERLAPPED` / buffer は解放せず process teardown まで保持」とあるが、`GetOverlappedResult` で `ERROR_IO_INCOMPLETE` のままハンドルを `CloseHandle` してもカーネル側 I/O 完了通知が遅延到着し得るため、ローカル変数や GC 対象オブジェクトに `OVERLAPPED` 構造体や送受信バッファを置くとメモリアクセス違反（クラッシュ）を引き起こす。モジュールレベルの退避リスト等で参照を強保持する機構が明示されていない。
- **[MEDIUM] `test_gsd_dod.py` における `.planning/ROADMAP.md` パース仕様の境界条件**:
  - [.planning/ROADMAP.md:18-109](C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md:18) には `<details>` ブロック内に過去マイルストーンの `- [x] Phase 4: ...`（32行目、61行目、74行目、87行目）が複数存在し、現行マイルストーンは 117行目に `- [ ] **Phase 4: 起動制御と既存画面への復帰**`（太字を含む書式）、206行目の Progress 表に `| 4. 起動制御と既存画面への復帰 | 0/5 | Planned | — |` と記載されている。
  - `04-01-01` で「details 内の過去マイルストーンを除外し、正規化した番号と現行 Phase Details を照合する」とあるが、チェックボックス行の太字（`**Phase 4:...**`）の有無や、Progress 表（[.planning/ROADMAP.md:190-208](C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md:190) には Milestone summary 表と Phase Progress 表の 2 つのテーブルが存在する）のどちらの表をどうパースするかが曖昧だと、将来の ROADMAP 編集で誤って「判定不能違反」になりやすい。
- **[MEDIUM] A4（Medium / Elevated 双方向共有）の自動・手動検証における UAC 昇格前提**:
  - `04-01-02` の precondition と verify で「対象 Windows で skip なら実証未完了として停止」「A3/A4 は実デスクトップと権限差で確認する」とあるが、通常の非昇格（Medium integrity）プロセスから昇格（High integrity）プロセスを自動生成するには UAC プロンプト承認が必要であり、`pytest` の自動実行だけでは High→Medium の作成順を再現できない。自動テスト部分（`pytest -k tracer`）が検証する範囲と、人間が UAC 昇格を伴って実行するハーネス手順の境界を明確に分離しないと、CI/ローカル単一プロセス `pytest`（[.planning/PROJECT.md:185](C:/Users/shdwf/work/project/PageFolio/.planning/PROJECT.md:185)）が UAC 待ちや権限不足で失敗する恐れがある。

##### 4. Suggestions
- `pagefolio/startup_win32.py` で `CancelIoEx` 後に未完了のまま残った `OVERLAPPED` と `ctypes.create_string_buffer` は、プロセス終了まで GC されないようモジュールスコープの `_LEAKED_OVERLAPPED_BUFFERS: list[ object ]` に明示的に退避させる設計を `04-01-02` の実装仕様に追記すること。
- `04-01-01` の `_read_live_phase_completion` でパースする [.planning/ROADMAP.md:117-120](C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md:117) と [.planning/ROADMAP.md:204-208](C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md:204) の正規表現は、`**Phase N:` のような Markdown 強調記号を許容し、2 つ目のテーブル（`| Phase | Plans Complete | Status | Completed |` ヘッダを持つ表）を明示的に特定する仕様に固定すること。
- `tests/test_startup_windows.py` において、単一プロセス `pytest -q` で常時走る自動テスト（同一 integrity での DACL 構造検証・SDDL/ACL 検査・Medium 同士の E2E tracer）と、実機 UAC 昇格を伴う A4 実測スクリプトの役割を分け、通常 `pytest -q` が対話 UAC プロンプトでブロックしないようにすること。

##### 5. Risk Assessment
- **Risk Level: HIGH**
- **Justification**: `ctypes` による Win32 セキュリティ記述子（Logon SID + Medium Mandatory Label）・共有メモリ・Overlapped Named Pipe・非活性ネイティブウィンドウという 4 つの低レイヤ機構を `04-01-02` の 1 タスクで新規構築するため、ポインタ寿命・64bit ハンドル型定義・ACL 権限設定のわずかな不備がプロセスハングやクラッシュに直結する。

---

#### 04-02

##### 1. Summary
`04-02` は、二次起動時の「最大5秒の単一待機期限（D-05/D-06）」「遅延した復帰要求の受信側失効（D-08）」「500ms 固定窓による連打集約（D-03）」「先行プロセスの死亡確認時のみ 1 回だけ行う原子的引き継ぎ（D-07）」、および終了確認キャンセル時の排他維持（[pagefolio/app.py:498-507](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:498)）を実装・検証する計画である。Fake clock を用いた状態遷移単体テスト（`tests/test_startup_control.py`）と実プロセス競合テスト（`tests/test_startup_windows.py`）の二段構えで検証する構成は論理的だが、「公開前死亡」や「スレッド放棄（`WAIT_ABANDONED`）」時のセカンダリ挙動と、終了処理中のタイミング競合に注意すべきエッジケースがある。

##### 2. Strengths
- **終了確認キャンセル時の排他維持が既存コード構造と合致**: [pagefolio/app.py:498-507](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:498) の `_quit()` では、`self.doc` が存在する場合に `messagebox.askyesno(...)` が `True` を返したときのみ `self.root.destroy()` を呼ぶ。排他解放を `_quit()` 内ではなく [pagefolio/__main__.py:26](C:/Users/shdwf/work/project/PageFolio/pagefolio/__main__.py:26) の `root.mainloop()` 終了後の `finally` 節に置くことで、終了確認ダイアログ表示中および「いいえ」選択時に所有権が維持される設計が自然に成立する。
- **送信・受信・UI 実行直前の多段失効チェック（D-08）**: 単に二次起動側が 5 秒でタイムアウト終了するだけでなく、`GetTickCount64` ベースの絶対 `deadline_tick` を要求に含め、受信スレッド・Tk メインスレッド取り出し時・各 Win32 副作用呼び出し直前に照合して破棄する設計により、タイムアウト案内後の突然の前面化を構造的に防いでいる。
- **Fake clock による境界値（4999ms / 5000ms、500ms 集約窓）の決定論的テスト**: OS スケジューリング揺らぎの影響を受ける実時間テストと分離し、`tests/test_startup_control.py` で時計・トランスポートを差し替えて厳密な境界値を検証する設計は保守性が高い。

##### 3. Concerns
- **[HIGH] 一次プロセスが owner mutex 取得直後・共有メモリ（mapping）公開前にクラッシュした場合のデッドロック/復帰不能リスク**:
  - `04-02-02` では「`_try_takeover` に `takeover_attempted` フラグを設け、識別済み process handle の `WaitForSingleObject(0)==WAIT_OBJECT_0` だけを死亡証拠とする（D-07）。mutex が空く / abandoned という事実だけでは引継がない」とし、さらに「初期 claim で mutex が取得可能でも古い metadata がある場合は生存確認し、process 生存/不明なら GUI を増やさない」としている。
  - しかし、先行プロセス A が(1) mutex 取得 → (2) mapping に旧世代または不完全な metadata を残したまま、あるいは PID 書き込み直後に OS ハンドルを閉じて異常終了し、直後に別プロセスがその PID を再利用した場合や、A が mapping 初期化中に強制終了されて sequence が奇数のまま残った場合、後続のすべての起動が「古い/不正な metadata があり死亡確認不能」と判定して永久に起動できなくなる（V110-START-02「起動途中の異常終了の後に再起動でき、残留ロックで起動不能にならない」に抵触する）恐れがある。
  - Windows の pagefile-backed file mapping（`Local\PageFolio.Startup.State`）は、開いている全プロセスのハンドルが閉じられればカーネルによって破棄されるが、二次起動プロセスが監視ループ中に mapping ハンドルを開きっぱなしにしていると、一次プロセスがクラッシュしても mapping オブジェクトが消滅せず不完全な metadata が残り続ける。
- **[MEDIUM] `root.mainloop()` 終了から `finally` での mutex 解放までの微小窓における二次起動の扱い**:
  - 一次プロセスでユーザーが終了を確定し `self.root.destroy()`（[pagefolio/app.py:504,507](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:504)）が呼ばれた後、`mainloop()` が抜けて `finally` で listener 停止・mapping 破棄・owner mutex 解放が終わるまでの間に二次起動が来ると、一次側はすでに Tk root を破棄しているため復帰 callback を実行できない。
  - このとき一次プロセスが単に IPC を切断・タイムアウトさせると、二次起動側では「一次プロセスが正常終了した直後なのに起動に失敗してエラー案内が出る」ことになる。一次プロセスが正常シャットダウンに入った場合は、二次起動が 5 秒期限内に一次プロセスの終了（または mutex 解放）を検知して正常に引き継げるのか、それとも D-07（「先行プロセスが起動失敗で終了したことを確認できた場合だけ」）との兼ね合いでどう扱うかが計画内で曖昧である。
- **[LOW] 本番固定名（`Local\PageFolio.Startup.Owner`）をそのまま使う subprocess テストの自己干渉**:
  - `04-02-02` で「テストは本番固定名を変更せず、既存 PageFolio の検出時にはそのプロセスを終了させず試験を中断する」とあるが、開発者が PageFolio を開いたまま `pytest` を実行するとテストが中断（fail）するほか、前のテストケースの子プロセス cleanup（最大500ms）がわずかに遅れた場合に次のテストケースと衝突し得る。

##### 4. Suggestions
- **共有メモリ（mapping）ハンドル保持期間の最小化と abandoned mutex 時の検証整理**:
  - 二次起動プロセスは `Local\PageFolio.Startup.State` の mapping ハンドルを 5 秒間保持し続けず、スナップショット読み取りの都度 open → read → close するか、一次プロセスが死亡した際に mapping が OS から自動消滅できるようにすること。また、新規起動時に `CreateMutexExW` が `WAIT_ABANDONED` を返した場合（前所有者が異常終了し、現在自プロセスが唯一の mutex 所有者となった場合）かつ他プロセスが生存していない場合は、壊れた共有メモリを自プロセスで初期化して一次起動へ進めるよう条件を明確化すること（そうでないと V110-START-02 の「起動途中の異常終了後に再起動できる」を満たせなくなる）。
- **正常終了（シャットダウン中）と二次起動の競合整理**:
  - 一次プロセスが `_quit()` で `root.destroy()` に入った後に到着した二次起動については、一次プロセスの終了（`WaitForSingleObject(process_handle)` の signaled）を 5 秒期限内に確認して二次起動が引き継げるよう、D-07 の引き継ぎ条件と正常終了直後の再起動（V110-START-02）を整合させること。

##### 5. Risk Assessment
- **Risk Level: MEDIUM**
- **Justification**: 期限管理と連打集約のロジック自体は明確で単体テスト容易性も高いが、共有メモリの寿命と `WAIT_ABANDONED` / 初期化途中クラッシュ時の引き継ぎ条件を誤ると、異常終了後に再起動不能になる退行リスクがある。

---

#### 04-03

##### 1. Summary
`04-03` は、既存画面への復帰時に最小化前のウィンドウ状態（通常/最大化）を復元し（D-02）、モーダルダイアログが開いている場合は最深のモーダルを優先し（D-13）、通常画面では直前の入力フォーカス先を維持し（D-04）、OS に前面化を拒否された場合はタスクバーを有限回（3回・250ms間隔・2秒以内停止）点滅させる（D-14〜D-16）`FocusRestorer` を実装・検証する計画である。既存の編集状態・Undo/Redo スタック・進行中 OCR を維持するテスト計画も具体的だが、現行コードベースの複数ダイアログ実装（`grab_set()` の有無や `_rebuild_ui()` による全ウィジェット破棄）と照合すると、いくつか見落とされている箇所がある。

##### 2. Strengths
- **最小化前の状態追跡の正確性**: Windows の `GetWindowPlacement` が最小化中に過去の最大化フラグを保持しない仕様を踏まえ、`FocusRestorer` 側で `last_non_iconic_state` と `normal_geometry` をイベント監視して `SW_RESTORE` 後に復元する設計は、D-02 を満たすうえで適切である。
- **Undo/Redo Blob ライフサイクルおよび OCR 世代管理との非干渉**: [pagefolio/app.py:199-200](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:199) の `_undo_stack` / `_redo_stack` や [pagefolio/ocr_dialog.py:197-202](C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_dialog.py:197) の `self._engine` / `self._run_gen` を再生成せず、かつ [pagefolio/app.py:509-510](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:509) の `_set_status()` や [pagefolio/toast.py:40-55](C:/Users/shdwf/work/project/PageFolio/pagefolio/toast.py:40) の `ToastManager.show()` を呼ばない（D-01）ことで、進行中の OCR ステータス表示や再試行トーストを保護できている。
- **OS 前面化拒否時の抑制的な振る舞い（D-14〜D-16）**: `SetForegroundWindow` を 1 回だけ試行し、失敗時は `FlashWindowEx`（`FLASHW_TRAY`, `uCount=3`, `dwTimeout=250`）＋ 2 秒後の `FLASHW_STOP` のみを予約し、遅延再試行や `focus_force()` / topmost トリックを使わない方針が徹底されている。

##### 3. Concerns
- **[HIGH] `_rebuild_ui()` が `root.winfo_children()` を全破棄することによる子 Toplevel 破壊と `last_focus_widget` 陳腐化**:
  - [pagefolio/app.py:696-700](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:696) の `_rebuild_ui()`（言語切替 [pagefolio/app.py:602](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:602) や設定適用 [pagefolio/app.py:693](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:693) で呼ばれる）は、`for w in self.root.winfo_children(): w.destroy()` を実行する。
  - これにより、`last_focus_widget` に保持していたウィジェット参照は破棄済み（`winfo_exists() == 0`）になるだけでなく、もし `FocusRestorer` が `root` 直下に何らかの補助オブジェクトやバインディングを持つ場合に影響を受ける。`04-03-01` では「破棄済み入力先は呼ばず生存 target へ戻る」とあるため ` TclError` は防げるが、`_rebuild_ui()` 直後に二次起動が来た場合のフォールバック先（`root` 自体か特定の初期ウィジェットか）を明示しておく必要がある。
- **[MEDIUM] `grab_set()` を呼ばないダイアログ（`PluginDialog` / `BatchOCRDialog` 等）やネストしたモーダルでの `grab_current()` の挙動**:
  - `04-03-01` では「選択は `root.grab_current` の生存 Toplevel を優先し、所有子を辿って最深の有効 modal を採る。Tk の grab に現れない messagebox / 保存確認は `GetLastActivePopup` ... で検証する」としている。
  - しかし、実コードを確認すると、[pagefolio/dialogs/settings.py:36](C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/settings.py:36)（`SettingsDialog`）、[pagefolio/dialogs/llm_config/dialog.py:82](C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/llm_config/dialog.py:82)（`LLMConfigDialog`）、[pagefolio/dialogs/shortcuts.py:60](C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/shortcuts.py:60)（`ShortcutsDialog`）、[pagefolio/ocr_dialog.py:156](C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_dialog.py:156)（`OCRDialog`）は `self.grab_set()` を呼んでいるが、たとえば `SettingsDialog` から `LLMConfigDialog`（[pagefolio/dialogs/settings.py:242-250](C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/settings.py:242)）や `ShortcutsDialog`（[pagefolio/dialogs/settings.py:272-277](C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/settings.py:272)）を開いて閉じた後、子 Toplevel の破棄時に親 `SettingsDialog` へ `grab_set()` を戻していないため、`root.grab_current()` が `None` になるケースがある（`SettingsDialog` はまだ開いて操作中であるにもかかわらず `grab_current()` が空になる）。
  - また、[pagefolio/app.py:318-322](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py:318) の `BatchOCRDialog` や `PluginDialog` などの生存 Toplevel についても、`grab_current()` だけに頼ると親の `root` だけが選ばれてダイアログが背面に隠れる（D-13 違反）リスクがある。
- **[LOW] `FocusIn` イベント監視による `last_focus_widget` の上書き**:
  - ウィンドウが最小化・非アクティブ化される過程や、モーダルダイアログが開く瞬間に `root` や `Toplevel` 自体に対する `FocusIn` が発火すると、直前にフォーカスしていた `Entry` や `Spinbox` の記録がウィンドウ自体で上書きされることがある。

##### 4. Suggestions
- **モーダル・子 Toplevel 探索ロジックの強化（D-13 保護）**:
  - `root.grab_current()` の確認に加え、`root.winfo_children()`（およびその子孫）に存在する生存・可視（`winfo_viewable()` または `wm_state() != 'withdrawn'`）の `tk.Toplevel`（`SettingsDialog`, `LLMConfigDialog`, `ShortcutsDialog`, `OCRDialog`, `BatchOCRDialog`, `PluginDialog` 等）を走査し、ネストした `LLMConfigDialog` を閉じた直後で `grab_current()` が `None` になっていても、開いている最深の `Toplevel` ダイアログを復帰対象として選択できるようにすること。
- **`FocusIn` 記録対象のフィルタリング**:
  - `_remember_focus` で `FocusIn` を記録する際、`event.widget` がトップレベルウィンドウ（`tk.Tk` / `tk.Toplevel`）そのものである場合は、既存の有効な子ウィジェット（`Entry` 等）の記録を上書きしないようにガードを入れること。

##### 5. Risk Assessment
- **Risk Level: MEDIUM**
- **Justification**: 既存の編集・OCR 状態を壊さない分離設計は良好だが、Tkinter のネストダイアログ（`SettingsDialog` → `LLMConfigDialog` 閉鎖後など）で `grab_current()` が外れる既存挙動や `FocusIn` の発火順序を考慮しないと、D-13（ダイアログを親の背面に隠さない）や D-04（直前の入力欄維持）を取りこぼすリスクがある。

---

#### 04-04

##### 1. Summary
`04-04` は、編集画面（Tk root）を生成する前に発生した起動失敗（排他判定不能・既存画面との通信失敗・5秒の準備待機時間切れ）を、フォーカスを奪わない非活性の Win32 ネイティブ小窓で 10 秒間（手動閉鎖可）案内し、原因クラス別の `NoticeLease` ミューテックスで複数プロセス間の連打を 1 つに集約する計画（D-09〜D-12、および D-14 との分離）である。多言語辞書（[pagefolio/lang.py](C:/Users/shdwf/work/project/PageFolio/pagefolio/lang.py)）やそのパリティテスト（[tests/test_lang_parity.py](C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py)）との接続も考慮されているが、静的検査テストとの整合およびネイティブウィンドウのメッセージループ・フォント周りの詳細に注意点がある。

##### 2. Strengths
- **主画面・ToastManager 非依存の起動前通知（D-09〜D-12）**: [pagefolio/toast.py:30-39](C:/Users/shdwf/work/project/PageFolio/pagefolio/toast.py:30) の `ToastManager` は `app.root` 構築後にメインウィンドウ内へオーバーレイ表示する仕組みであるため、起動前の失敗案内には使えない。これを `CreateWindowExW`（`WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW`, `SW_SHOWNOACTIVATE`, `WM_MOUSEACTIVATE -> MA_NOACTIVATE`）で独立実装することで、他アプリや既存 PageFolio のキーボード入力先を一切奪わずに通知できる。
- **原因クラス別のプロセス間集約と期限非延長（D-11）**: 原因ごとに独立した `NoticeLease` を原子的取得（待機時間 0）し、取得できた先頭プロセスだけが 10 秒間の表示を担い、後続プロセスは即座に終了する設計により、連打時の通知増殖と表示時間の延長をシンプルかつ確実に防いでいる。
- **OS 前面化拒否との厳格な分離（D-14）**: `foreground_denied` は `show_startup_failure` の対象外とし、タスクバー点滅のみで完了させる契約が一貫している。

##### 3. Concerns
- **[MEDIUM] [tests/test_lang_parity.py:55-75](C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py:55) の `test_no_unused_lang_keys` におけるリテラル文字列スキャンとの整合**:
  - [tests/test_lang_parity.py:68-74](C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py:68) は、`LANG["ja"]` のすべてのキーについて `pagefolio/`・`tests/`・`plugins/` 内の `.py` ファイルに `f'"{key}"'` または `f"'{key}'"` という**引用符付き文字列リテラル**が含まれているかを検査する（`_ALLOWLIST` は現在空集合）。
  - `04-04-01` で追加する 5 キー（`startup_notice_check_failed`, `startup_notice_contact_failed`, `startup_notice_timeout`, `startup_notice_close`, `startup_notice_title`）を、もし `f"startup_notice_{reason.value}"` のように動的文字列合成で参照すると、`test_no_unused_lang_keys` が即座に FAIL する。計画文中に「確認された reason から固定キーを解決」とあるが、必ず辞書マッピング等で 5 キーすべてを完全な文字列リテラルとして `pagefolio/startup_notice.py` 内に記述する必要がある。
- **[MEDIUM] [tests/test_font_hardcode_guard.py:20-37](C:/Users/shdwf/work/project/PageFolio/tests/test_font_hardcode_guard.py:20) のソーススキャンガードへの抵触リスク**:
  - [tests/test_font_hardcode_guard.py:20](C:/Users/shdwf/work/project/PageFolio/tests/test_font_hardcode_guard.py:20) は `pagefolio/` 配下の全 `.py` に対して正規表現 `font=\(\s*["\']Segoe UI["\']\s*,\s*\d+` をスキャンしている。`startup_notice.py` や `startup_win32.py` でフォント指定やコメントを書く際にこのパターンにマッチする記述を入れるとガードテストが失敗する。
- **[LOW] Win32 ネイティブ小窓の DPI スケーリングと「閉じる」ボタンの非活性クリック処理**:
  - `WS_EX_NOACTIVATE` を付与した親ウィンドウ上の子 `BUTTON` コントロールをクリックした際、標準の `DefWindowProcW` にそのまま流すとボタンコントロール側が `SetFocus` を試みてアクティブ化やフォーカス遷移を誘発するケースがある。`WM_MOUSEACTIVATE` で `MA_NOACTIVATE` を返すだけでなく、カスタム描画領域のクリック判定またはサブクラス化なしでフォーカスを奪わないことを `04-01-02`（A3）および `04-04-01` で確実に検証する必要がある。

##### 4. Suggestions
- `pagefolio/startup_notice.py` では、`StartupFailureReason` から `LANG` キーへの変換に動的文字列結合（f-string）を使わず、`{StartupFailureReason.CHECK_FAILED: "startup_notice_check_failed", ...}` のように全 5 キーを完全な文字列リテラルで明記し、[tests/test_lang_parity.py:55-75](C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py:55) の `_ALLOWLIST` を変更せずにパスさせること。
- 非活性小窓の「閉じる」操作は、子 `HWND` の標準 `BUTTON` コントロールがフォーカスを奪う挙動を避けるため、クライアント領域内のボタン矩形に対する `WM_LBUTTONUP` 判定で `DestroyWindow` を呼ぶ方式を検討すると、`WS_EX_NOACTIVATE` / `MA_NOACTIVATE` の非活性契約（D-12）をより確実に守れる。

##### 5. Risk Assessment
- **Risk Level: LOW**
- **Justification**: `04-01` の A3/A4 で非活性ウィンドウと `NoticeLease` のプリミティブが実証された後に実行される Wave 4 であり、主なリスクは `test_lang_parity.py` のリテラル検査規約と Win32 クリック時の非活性維持に限定される。

---

#### 04-05

##### 1. Summary
`04-05` は、Wave 1〜4 で実装した起動排他・期限失効・引き継ぎ・画面復帰・非活性通知の全経路を統合検証し、Windows 11 実機での受入試験記録（`04-WINDOWS-UAT.md` の W01〜W12）と `04-VALIDATION.md` の更新、および人間による実機検証ゲート（`04-05-02` `checkpoint:human-verify`）を経て `/gsd-validate-phase 4` へ引き渡す最終プランである。自動テスト・故障注入・実機確認・Phase 6（実 EXE 同梱検証）の責務境界が明確に分離されており、未実施項目を合格と偽装しない規律が徹底されている。

##### 2. Strengths
- **自動検証と実機 UAT、および Phase 6 範囲の明確な分離**: W01〜W12 のマトリクスにより D-01〜D-16 と V110-START-01〜03 / V110-FOCUS-01〜02 が漏れなくカバーされており、かつ「OS 前面化拒否」「UAC 昇格を伴う権限差」「別ログインセッション」などモックでは証明できない項目を `blocking-human` チェックポイントとして切り出している。また、PyInstaller 実 EXE の最終検証を Phase 6 担当として明記し、Phase 4 時点での `sys.frozen` 単体テストと混同しないよう釘を刺している点も優れている。
- **ユーザー環境を破壊しないテストハーネス設計（T-04-16）**: `tests/test_startup_windows.py` が既存のユーザー PageFolio プロセスを検出した場合に強制終了せず中断すること、および設定やプロンプトファイルを `tmp_path` 等の一時フィクスチャへ隔離して本番ファイルを汚さないことが明記されている。

##### 3. Concerns
- **[MEDIUM] 単一プロセス全件 `pytest -q` の実行時間肥大化リスク**:
  - [.planning/phases/04-startup-control/04-VALIDATION.md:22,29](C:/Users/shdwf/work/project/PageFolio/.planning/phases/04-startup-control/04-VALIDATION.md:22) によると、計画時 baseline の全件 `pytest -q` は 34.31 秒、最長フィードバック時間の目標は 120 秒とされている。
  - しかし、`tests/test_startup_windows.py` には `04-01`〜`04-05` を通じて実 subprocess を起動するテスト（5秒タイムアウト、10秒通知自動閉鎖、閉鎖後15秒間の非復帰観測 `04-04-02`、2〜8プロセス同時起動 `04-02-02`、別配置コピー `04-05-01` 等）が多数追加される。実時間で 5 秒・10 秒・15 秒待つ subprocess テストを複数直列に走らせると、`pytest -q` 全体の実行時間が 120 秒を大きく超過する可能性がある。
- **[LOW] W11（別ログインセッション独立）の実機確認環境**:
  - Windows 11 実機で別ログインセッション（別ローカルユーザーへのサインイン＋ユーザー切り替え）を用意できない開発環境では W11 が `not-run` となるが、`04-05-02` の action で「準備不能は not-run で残し Phase 4 受入を合格にしない」「必須 Windows ケースが fail/not-run なら親へ返して修正または確認を継続し、Phase 完了へ進めない」とあるため、もしシングルユーザー環境だと Phase 4 が完了できなくなる可能性がある。

##### 4. Suggestions
- **実 subprocess テストにおけるタイマー定数のテスト用注入（本番デフォルト不変）**:
  - Fake clock 単体テストで 5000ms / 10000ms の数値境界を厳密に保証したうえで、実 subprocess を使う `tests/test_startup_windows.py` の一部ケース（特に「タイムアウト後の 15 秒間非復帰観測」など）では、テスト用 bootstrap の factory 引数経由で待機・通知タイマーを短縮できる仕組み（本番エントリは 5000ms / 10000ms 固定）を用意し、実時間 5 秒・10 秒フル待機は代表の受入ケース 1 件ずつに絞ることで、単一プロセス `pytest -q` を 120 秒以内に収めること。
- **W11（別セッション）の検証手順の具体化**:
  - Windows 11 実機で別アカウントへの切り替えが難しい場合に備え、`Local\` 名前空間オブジェクトが現在のセッション ID スコープ（`\Sessions\<SessionId>\BaseNamedObjects\...`）に生成されていることの Win32 API / カーネルオブジェクトパス確認と、実アカウント切り替えによる確認のどちらを必須条件とするかを `04-WINDOWS-UAT.md` の判定基準に明記しておくこと。

##### 5. Risk Assessment
- **Risk Level: LOW**
- **Justification**: 新規のプロダクション機能追加はなく統合テストと実機検証の計画であり、主に実 subprocess テスト群の総実行時間管理と実機 UAT 環境準備（別セッション・昇格権限）の運用面に留意すればよい。

---

#### Cross-Plan Comparison & Overall Assessment

| Plan ID | Wave | 主な責務 | Risk Level | 最重要の確認ポイント |
|---|---|---|---|---|
| `04-01` | 1 | DoD ゲート修正＋Win32 排他/IPC/非活性通知の本番 tracer と A1〜A5 実証 | **HIGH** | `CancelIoEx` 後の `OVERLAPPED` バッファ寿命管理、ROADMAP パーサの堅牢性 |
| `04-02` | 2 | 5秒単一期限・受信側失効・500ms 集約・先行プロセス死亡確認後の 1 回引き継ぎ | **MEDIUM** | 共有メモリ公開前クラッシュ / `WAIT_ABANDONED` 時の再起動可能性（V110-START-02） |
| `04-03` | 3 | 最小化前状態復元・最深モーダル優先・直前フォーカス維持・有限タスクバー点滅 | **MEDIUM** | ネストダイアログ閉鎖後の `grab_current()==None` 対策、`_rebuild_ui` との整合 |
| `04-04` | 4 | 起動前失敗の 3 分類・10秒非活性案内・原因別 `NoticeLease` 集約 | **LOW** | [tests/test_lang_parity.py:55-75](C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py:55) の文字列リテラル参照規約との整合 |
| `04-05` | 5 | 全起動経路の統合テストと Windows 11 実機 UAT（W01〜W12）・DoD 検証接続 | **LOW** | 実 subprocess テスト追加後の単一プロセス `pytest -q` 総実行時間（120秒目標） |

##### 全体評価（Overall Conclusion）
Phase 4 の全 5 プラン（`04-01`〜`04-05`）は、承認済み要件（`V110-START-01〜03`, `V110-FOCUS-01〜02`）およびユーザー決定事項 `D-01〜D-16` を漏れなくカバーしており、Wave 1 で技術的不確実性（A1〜A5）と DoD ゲートの前提不整合を解消してから段階的に状態遷移（Wave 2）・UI 復帰（Wave 3）・失敗案内（Wave 4）・実機統合検証（Wave 5）へ進む依存関係も妥当である。既存の [pagefolio/__main__.py](C:/Users/shdwf/work/project/PageFolio/pagefolio/__main__.py)、[pagefolio/app.py](C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py)、[tests/test_gsd_dod.py](C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py) の構造とも正確に噛み合っているため、上記各セクションで指摘した境界条件（特に `04-01` の非同期 I/O バッファ寿命、`04-02` の初期化途中クラッシュ後の再起動、`04-03` の生存 Toplevel 探索フォールバック、`04-04` の `LANG` キーの静的リテラル記述）を実行時に反映することで、安全にフェーズ目標を達成できる。

---

## Consensus Summary

**集約判断: 実装開始前に計画修正を推奨（高リスクの設計未確定事項あり）。** これは計画レビューの完了であり、Phase 4 の実装・受入完了ではない。3者とも参照ソースを読んだレビューを返し、04-01〜04-05 の全5計画を扱った。レビュアーの意見は原文を保持し、誤認・未実証の推測・承認済み決定との衝突を以下で補正する。

| レビュアー | 実行結果 | 計画カバレッジ | 記録されたモデル | 全体評価の要旨 |
|---|---|---|---|---|
| Claude | 成功・ソース引用あり | 5/5 | claude-opus-5-5 (reasoning=high) | MEDIUM-HIGH。権限委譲、終了時 metadata、モーダル探索などを懸念 |
| Grok | 成功・ソース引用あり | 5/5 | grok-4.7 | HIGH。権限委譲、同時受付、設定隔離を重視 |
| Antigravity | 成功・ソース引用あり | 5/5 | unknown | 04-01 は HIGH、後続は MEDIUM/LOW。境界条件の補強で達成可能と評価 |

Antigravity の実モデルは CLI 結果から取得できなかった。設定の別キーや製品名から推定しない。3つの CLI に同一の完全なプロンプトを渡し、トークン予算による省略は行っていない。

### Agreed Strengths

- 5秒の絶対期限、受信側と副作用直前の失効検査、accepted と terminal ACK の分離は D-06/D-08 を具体化している。
- Tk 操作をメインスレッドへ限定し、既存 app/doc/Undo/OCR を再作成しない分離方針が現行構造に合う。
- 終了確認キャンセル時は所有権を保持し、死亡確認なしの引継ぎを禁止している。
- 自動試験・故障注入・Windows 実機・未実施を区別し、A1〜A5 と W01〜W12 に停止条件を置いている。
- DoD ゲートは未完了 live と完了済みフェーズを区別して直し、VALIDATION の偽装昇格やテスト除外で回避しない。

### Agreed Concerns

| ID | 優先度 | 支持 | 計画への反映候補と確認根拠 |
|---|---|---|---|
| R1 | 高 | Claude・Grok | **試験用の設定・プロンプト隔離を 04-01 へ前倒しする。** 実 main の tracer は初回から設定を読む。終了確認前にも保存する（pagefolio/app.py:148、498、574）。基準パスは cwd ではなく __file__ 由来（pagefolio/settings.py:32）。隔離の明記は 04-05-PLAN.md:78 まで遅れている。子プロセスの bootstrap で初回から隔離し、利用者ファイルの不変を確認する。 |
| R2 | 高 | Claude・Grok | **二次プロセスからの前面化許可委譲を設計・試験する。** 04-01-PLAN.md:118 と 04-03-PLAN.md:93 は一次側の SetForegroundWindow を記すが、許可委譲を記していない。AllowSetForegroundWindow を検証済み owner PID に対して試み、失敗時・ユーザー入力後の失効も有限点滅へ接続する案を検討する。「必ず拒否される」とは断定しない。 |
| R3 | 高 | Claude・Antigravity | **入れ子を閉じた後のモーダル復帰先を明示する。** SettingsDialog と LLMConfigDialog はそれぞれ grab_set する（pagefolio/dialogs/settings.py:36、pagefolio/dialogs/llm_config/dialog.py:82）。子を開く経路に親 grab の復元は見当たらない（pagefolio/dialogs/settings.py:209）。04-03-PLAN.md:91 の grab/所有 HWND だけでは拾えない状態を試験し、可視 Toplevel・最後の操作先・native popup を含む選択規則を確定する。 |
| R4 | 高 | 3者 | **04-01-02 の実装単位と資源寿命を具体化する。** DACL/label、共有メモリ、overlapped pipe、WndProc、小窓、Tk callback を一度に作る。停止ゲートを維持したまま内部手順・中間検証点を分け、未完了 I/O の buffer/OVERLAPPED と WndProc callback の参照保持、所有スレッド、解放責任を明記する。 |
| R5 | 中〜高 | 3者が異なる境界を指摘 | **所有者終了・古い mapping・再公開の状態遷移を補う。** 04-02-PLAN.md:101 の生存確認・新 generation 公開に、終了中で root はないが process は生存、部分公開、二次が mapping handle を保持、同時引継ぎのケースを追加する。正常終了後の再起動と死亡未確認の引継ぎ禁止を両立させる。具体的な released 状態の採用は設計判断であり、未検証のまま安全としない。 |
| R6 | 中 | 3者 | **通常 pytest と実機 UAT の前提・時間を分けて明記する。** 本番固定名、既存アプリ起動中の中断、UAC、別ログインセッション、実時間5秒/10秒/15秒を扱う。通常全件 pytest が対話待ちにならない構成と、実時間の代表試験・必須実機試験を定義する。120秒目標のために必須試験を無断除外しない。 |

R2 の仕様根拠: 前面化可能なプロセスは別プロセスへ許可を渡せるが、呼出元にも権限が必要で、後続のユーザー入力等で許可は失効する。[Microsoft: AllowSetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-allowsetforegroundwindow)

### Divergent Views

次の指摘は、原文をそのまま採用してはならない。

1. **Grok の「root.bind では子の FocusIn を観測できない」は一律には誤り。** 既定 bindtags は最寄り Toplevel を含むため、root 配下の通常ウィジェットは root の binding 対象になる。別 Toplevel 内の記録と、破棄済み参照・トップレベル自身のイベントによる上書きを個別に設計する。bind_all/unbind_all への全面変更は確定解としない。[Tk: bindtags](https://web.tcl.tk/man/tcl9.1/TkCmd/bindtags.html)
2. **Antigravity の「PluginDialog/BatchOCRDialog に grab_set がない」は実コードと不一致。** pagefolio/dialogs/plugin.py:27 と pagefolio/dialogs/batch_ocr.py:169 に存在する。ただし入れ子閉鎖後の親 grab 不在という別の懸念は残る。
3. **Grok の「CreateNamedPipe の既定インスタンス数は1」は誤り。** nMaxInstances は必須引数である。同時受付数・ERROR_PIPE_BUSY の扱い・FILE_FLAG_FIRST_PIPE_INSTANCE を最初だけに使う規則が計画に未記載、という設計課題として採用する。複数受付と terminal 前の集約を試験するが、現在の計画から必ず二重復帰するとまでは断定しない。[Microsoft: CreateNamedPipeW](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createnamedpipew)
4. **Claude の「UAC 昇格で logon SID が違うため A4 が構造的に通らない」は未確認の仮説。** 本セッションでは medium/elevated の token を実測していない。logon SID・認証 LUID・Terminal Services session ID を混同せず、A4 で対象条件を確認する。User SID へ ACL を広げる提案は自動採用しない。Microsoft の UAC 説明だけでは、この環境の SID 同一性までは確定しない。[Microsoft: UAC の動作](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/how-it-works)
5. **Antigravity の「不正 metadata により永久に起動不能」は過大な断定。** 既存計画には二次の有限期限と全 handle 消滅後の通常起動がある。単発の二次終了後にも永続するとは立証されていない。連続した二次が mapping を保持する場合と、静穏後の新規起動を分けて検証する。なお WAIT_ABANDONED は CreateMutexExW 自体の戻り値ではなく、待機 API の結果として扱う。
6. **NoticeLease アクセス拒否時に無条件で別案内を出す提案は D-11 と衝突する。** 現行の同原因1案内・期限延長なしを維持し、失敗時の実行時挙動を具体化する。設計が成立しない場合は停止ゲートへ戻す。
7. **別セッション実機試験の省略・名前空間確認だけでの置換は承認済み条件を緩める。** W11 を準備できないことは環境前提の課題であり、合格に読み替えない。手順具体化は妥当だが、無断免除はしない。
8. **EXE 検証の Phase 6 引継ぎについて評価が分かれる。** Grok は Phase 4 の成功条件との不整合を HIGH とする一方、Antigravity は責務分離を評価する。PROJECT.md、04-CONTEXT.md、ROADMAP.md:156 は既に Phase 6 担当を明記している。まず Phase 4 の達成証拠と Phase 6 未実施部分を明記し、既存の分担を勝手に移さない。
9. **要件 ID の早期 Complete 化は現在の GSD に防止規則がある。** Grok の懸念は一般的注意として残すが、インストール済み execute-plan.md:518 の Shared-ID gate が、同じ要件を宣言する全計画の SUMMARY 完了まで待つ。現在のワークフローで必ず起きる欠陥とはしない。
10. **DoD の完了判定と GSD 更新順序は具体化が必要。** execute-plan.md:493 の update_roadmap は SUMMARY 数から Progress を Complete にする。04-01 の予定パーサと 04-05 の validate/完了順序の整合を確認する。ただし矛盾を無視する方向へ一律に緩めず、実際の中間状態を合成テストに入れる。
11. **UI 再構築後の focus fallback は有用な追加試験だが、未実装 controller の確定不具合ではない。** pagefolio/app.py:696 は子 widget を破棄するため、再構築後に参照を更新できるか確認する。04-03 は既に破棄済み入力先へのガードを要求している。
12. **通知言語を OS 言語から設定言語へ変更する提案は裁量事項。** 04-04 は設定 I/O 副作用を増やさないため明示的に OS 言語を選んでいる。読み取りを追加するなら Phase 5 との境界と失敗時処理を整理し、レビューだけで方針変更しない。

### 検証・変更範囲

- 実行: .venv/Scripts/python.exe -m pytest -q
- 結果: **1409 passed / 1 failed / 1 warning、33.80秒**。単一プロセスで全件実行。
- 失敗: tests/test_gsd_dod.py::test_completed_phases_are_validated。未完了 Phase 4 の 04-VALIDATION.md が draft であることを既存ゲートが違反とする。04-01-01 が是正対象としている既知の不整合で、今回も再現した。
- **コミット保留。** AGENTS.md の「コミット前に pytest を通す」に従う。テスト除外や VALIDATION の昇格で回避していない。
- 本作業はレビュー資料と診断証拠の追加のみ。PLAN、製品コード、版番号は変更していない。Python 編集がないため ruff/format は実行していない。
- A1〜A5、W01〜W12、実 EXE は本レビューでは未実施。外部レビュアーの source-grounded はソース読取の意味であり、Windows の挙動が実測済みという意味ではない。
- Claude の stderr は認証方式により claude.ai connectors が無効という案内のみ。レビューは成功し、根拠ソースの引用もある。認証情報の値は記録していない。
- 各レビュー原文と非空 stderr、実行結果、計画 SHA-256 は同じフェーズの .review-diagnostics 配下に実行別ディレクトリで保存する。入力プロンプトや計画の複製は保存しない。

### 次の作業

計画への反映は未実施。R1〜R6 と上記の補正を踏まえて次を実行する。

~~~text
$gsd-plan-phase 4 --reviews
~~~

レビュー原文の高優先度指摘であっても、補正・未確認・承認済み決定との衝突を確認してから計画に採否を記録する。

