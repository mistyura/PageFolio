ソースとの突き合わせは終わりました。ここからレビュー本文をまとめます。

# Phase 4 計画レビュー（04-01〜04-05）

**前提:** 読み取り専用のレビューです。ファイルの変更、テストの実行、コミットはしていません。下の `file:line` は実際にファイルを開いて確認した箇所です。Win32 の挙動についての指摘は、私の知識からの推論である場合はそう書いています。

---

## 04-01

### Summary
最初の Wave で二つを片付ける計画です。一つは DoD ゲートの誤判定の修正、もう一つは本番品質の起動 tracer です。DoD の診断は正しいです。`_collect_phase_dirs()` は live のディレクトリをすべて走査対象にするため（`tests/test_gsd_dod.py:129-131`）、未着手の Phase 4 でも赤になります。ただし tracer タスク（04-01-02）は mutex、mapping、overlapped pipe、DACL と label、peer 照合、Tk queue、前面化と点滅、NoticeLease、ネイティブ通知窓をまとめて作り、さらに A1〜A5 を実測する内容です。tracer と呼ぶには大きすぎ、見積もりの 40k tokens・2 tasks とも合っていません。さらに、Windows で単一起動を前面化するときの定石である `AllowSetForegroundWindow` が、全計画を通して出てきません。

### Strengths
- 存在、所有権、API 失敗の三つを別の結果として扱い、`WaitForSingleObject(0)` で所有権を判定しています。`CreateMutexEx` の initial owner は既存の名前に対しては付与されないので、Win32 の仕様に沿った設計です。
- 共有時刻に `GetTickCount64` を選び、deadline を二次起動の開始時に一度だけ決めています。システム時刻の変更に左右されず、プロセス間で比較できます（A5 の方向性は妥当）。
- 名前付きパイプはセッションごとの名前空間を持ちません。セッション番号と SID を pipe 名に含め、`PIPE_REJECT_REMOTE_CLIENTS`、`FILE_FLAG_FIRST_PIPE_INSTANCE`、peer PID 照合を重ねている点は正しいです。
- 未完了の OVERLAPPED とバッファをプロセス終了まで解放しない、という ctypes で見落としやすい寿命管理まで書かれています。
- `pagefolio/__main__.py:19-26` には現在 `finally` がありません。それを踏まえて try/finally で所有権を閉じる構造を新しく追加する、という認識は正確です。
- 製品に排他を外す CLI や環境変数を作らないと明記しています。

### Concerns
- **HIGH: `AllowSetForegroundWindow` がない。** Explorer やタスクバーから起動されたとき、前面化の権利を持つのは起動された二次プロセスです。一次プロセスではありません。一次が自分で `SetForegroundWindow` を呼んでも、拒否される経路がよく起こると考えられます（推論）。二次が IPC で要求を送る前に、検証済みの owner PID に対して `AllowSetForegroundWindow(pid)` を呼ぶのが OS が認める方法です。D-14 の「OS 制約を迂回しない」にも反しません。これがないと、D-14 の点滅経路が例外ではなく標準になり、V110-FOCUS-01 の「OS が許せば前面に出る」が実質的に満たせない恐れがあります。
- **HIGH: logon SID による DACL と peer 照合が、昇格プロセスとの共有（A4）を構造的に壊す可能性。** UAC で昇格したトークンと昇格していないトークンは、別のログオンセッションになり、logon SID も別になるはずです（推論。`whoami /logonid` の値が昇格の有無で異なることで確かめられます）。そうだとすると、「現在の logon SID と SYSTEM に限定」「同一 logon を照合」という方式では、medium と elevated の組合せが必ずアクセス拒否になります。A4 は 04-01 の停止条件なので、設計の時点で通らないゲートになりえます。要件の「同一ログインセッション」は TS セッション ID を指しています。user SID と session ID で照合する案と比べて検討すべきです。
- **HIGH: tracer の規模。** 04-01-02 の action は一段落で、`startup_win32.py` の大半（SDDL/ACL、mandatory label、overlapped connect/read/write、CancelIoEx、seqlock、ctypes の WndProc を使う通知窓、NoticeLease）を作らせています。これらはほとんどが 04-02 と 04-04 の仕事を前倒ししたものです。見積もり（40k・confidence low）との差が大きく、途中で止まった場合の巻き戻し単位も大きすぎます。
- **MEDIUM: 実ユーザー環境を汚す。** tracer は subprocess で実際の `main` を起動します。`PDFEditorApp.__init__` は `_load_settings()` を通じて `_get_base_dir()`、つまりリポジトリ直下の実設定を読みます（`pagefolio/settings.py:40-44`, `app.py:148`）。終了時には `_save_window_state()` が実設定を書き換えます（`app.py:574-584`）。設定を一時ディレクトリへ隔離することは 04-05 にしか書かれておらず、04-01〜04-03 の Windows 試験は開発者の `pagefolio_settings.json` を書き換えます。
- **MEDIUM: 本番の固定名で試験すると、開発中の実 PageFolio と衝突する。** 起動中の PageFolio を検出したら中断する方針ですが、中断すると skip 扱いになり、それは不合格と定義されています。したがって開発者がアプリを開いている間は、コミット前の全件 pytest が必ず失敗します。また「検出してから実行する」は原子的ではないので、試験が開発者のウィンドウを前面化してしまう競合も残ります。
- **MEDIUM: A4 は UAC 操作、A3 は目視が必要。** それでも frontmatter は `autonomous: true` です。execute-plan の tracer 規則によれば `<human-check>` があれば checkpoint になりますが、frontmatter と実態が食い違っています。
- **MEDIUM: DoD 修正の順序の落とし穴。** 04-01-01 は「Progress 表の Complete とチェック行 [x] の矛盾」を違反として検出します。一方、execute-plan の `update_roadmap` は SUMMARY の数から Progress 表を自動で `Complete` に書き換えます。04-05 の SUMMARY をコミットした時点で、Progress は Complete、Phase 行は `[ ]`、validate-phase は未実行、という状態になり、全件 pytest が赤になる期間が生じます。また ROADMAP には Phase 行（`ROADMAP.md:117`）と同じ形式の Plan チェック行（`ROADMAP.md:142-154`）が並んでいるので、パーサーは `**Phase N:` で厳密に絞り込む必要があります。
- **LOW: 既存 self-test との互換。** `test_dod_gate_detects_unvalidated_phase` の live ケース（`tests/test_gsd_dod.py:292-296`）は合成ツリーに ROADMAP.md がありません。新しいロジックでは「判定不能」の違反になるので、ラベル一致の assert は通ります。ただし理由文字列の意味が変わるので、意図的な変更として明記したほうがよいです。
- **LOW: A5 の「時刻変更に影響されない」を実測するには、システム時刻を変える必要があります。** 管理者権限が要り、開発機にも影響します。Microsoft の文書で根拠を示せる性質なので、文書の引用で代えるほうが現実的です。

### Suggestions
- 04-01-02 を二つに分ける。(a) A1〜A5 の成立性を確かめる spike（試験専用または使い捨て）と、(b) mutex、pipe、Tk callback、terminal ACK の最小 tracer です。通知窓と NoticeLease は 04-04 へ移します。
- 二次側の送信直前に `AllowSetForegroundWindow(owner_pid)` を呼ぶ手順を契約に加え、W06/W12 で起動経路ごと（Explorer、ターミナル、EXE）に記録する。
- DACL は SDDL の `D:(A;;<rights>;;;<UserSID>)(A;;GA;;;SY)S:(ML;;NW;;;ME)` 相当にし、照合は user SID と TS session ID で行う案を、A4 の前に机上で比較する。
- 試験の bootstrap では名前空間の接頭辞を注入できるようにし（製品 CLI ではなく bootstrap 内に限る）、大部分の試験を分離された名前で実行する。本番固定名を使う試験は少数に絞り、明示的な marker を付ける。
- DoD の「完了」は Phase 行の `[x]` だけで判定し、Progress=Complete と `[ ]` の組合せは違反ではなく「validate 待ち」として扱う。そうしない場合は、validate-phase を 04-05 の SUMMARY コミットより前に実行する順序を固定する。

### Risk Assessment
**HIGH。** 方向性は正しいですが、前面化の権利付与が抜けていることと、A4 が構造的に通らない可能性があることの二点で、Wave 1 の停止ゲートで行き詰まる恐れがあります。tracer の規模が過大なことも、そのリスクを大きくしています。

---

## 04-02

### Summary
5 秒の絶対期限を一つに固定すること、受信側でも失効を確認すること、500ms の集約、D-07 の一回だけの引継ぎ、の四つを状態遷移として仕上げる計画です。期限の境界値（4999/5000ms）、ACK が期限後に届いた場合、期限前にキューへ入ったが Tk での実行が期限後になった場合、とテスト観点が非常に具体的で、CONTEXT の「受信側にも失効が必要」を正しく実装に落としています。一方で、正常終了直後の再起動が拒否される経路が残っています。

### Strengths
- `accepted` と terminal を分け、各副作用の直前で期限と generation を再確認する設計は、D-08 の「後から突然前面化する」を構造的に防ぎます。
- D-03 の集約窓を到着のたびに延長しないこと、`foreground_denied` を `completed` に変換しないこと、を明記しています。
- 解放順（listener→失効→IPC→mapping→owner）と、`_quit` の開始を解放条件にしないこと（`app.py:498-507`。キャンセル時は `root.destroy()` されない）を正しく踏まえています。
- `WAIT_ABANDONED` やスレッドの終了をプロセス死と同一視しない、という研究の指摘を反映しています。

### Concerns
- **HIGH: 正常終了の直後の再起動が「生存しているので拒否」になる経路。** 解放順に「metadata を released にする」手順がありません。mapping は、他のプロセス（待機中の二次プロセスなど）が handle を持っている間、内容が残ります。終了処理中のプロセスは、mutex を解放した後もしばらく生き続けます。atexit による Undo Blob の purge（`pagefolio/undo_store.py:140`）や、非 daemon の `ThreadPoolExecutor` worker の join（`pagefolio/ocr.py:393`）があるためです。この間に利用者が再起動すると、「mutex は取得できたが、古い metadata の PID がまだ生きている」状態になります。計画は「生存または不明なら GUI を増やさない」としているので、起動が失敗します。OCR 実行中に終了してすぐ起動し直す、というよくある操作で V110-START-02 を破ります。
- **MEDIUM: 一次のメインスレッドが重い同期処理中の扱い。** 大きな PDF の保存、`_do_insert`、レンダリング中は 50ms の poll が回りません。その間に二次起動すると、5 秒後に「応答を確認できません」が表示されます。仕様の範囲内ではありますが、Core Value（大きな PDF）と直接ぶつかる場面です。W07 に「一次が忙しい」ケースを明示的に入れるべきです。
- **MEDIUM: 子プロセス生存の上限が 16 秒の試験が全件 pytest に入る。** 2〜8 個の同時起動、ライフサイクル、引継ぎの各試験で、コミットのたびに数分かかる恐れがあります。VALIDATION の目標である 120 秒との整合が計画にありません。
- **LOW: 二次の 5 秒期限は「二次の開始」から測ります。** ところが `pagefolio/__main__.py:8` は `PDFEditorApp`（fitz、PIL、tkinterdnd2、全 Mixin）をモジュールの先頭で import しています。そのため claim の前に重い import が終わってしまい、利用者の体感は 5 秒＋import 時間になります。前面化の権利が失効するまでの時間にも効きます。

### Suggestions
- 所有者は mutex を解放する前に、mapping へ `state=released`（pid=0、generation を進める）を書き込む。後続は「released なら古い PID の生死を問わず一次になれる」とする。この遷移を lifecycle 試験で固定する（OCR worker が残っている状態の模擬を含める）。
- `__main__.py` の app import を claim の後へ遅らせ、二次は Win32 の境界だけを読み込むようにする。
- Windows subprocess 試験の合計時間に予算を設定し（例: 60 秒）、超える分は fake clock 側へ移す。

### Risk Assessment
**MEDIUM-HIGH。** 状態機械の設計は優れていますが、metadata の released 化がないために、正常終了後の再起動という基本要件が条件次第で失敗します。

---

## 04-03

### Summary
既存の app/doc/Undo/OCR を作り直さずに、最小化前の状態、入力先、最も深いモーダルへ戻す計画です。D-01、D-02、D-04、D-13〜D-16 の対応は網羅されています。ただし、モーダル対象を見つける方法が PageFolio の実際のダイアログ構造と合っていません。

### Strengths
- `_set_status` やトーストを呼ばないことを観測する試験（D-01）、`focus_force`、topmost、`AttachThreadInput`、擬似キー入力を禁止していること（`app.py:651-652` の `focus_force` を流用しない判断を含む）が適切です。
- 最小化中の `GetWindowPlacement` から過去の最大化状態を推測せず、iconic/withdrawn への遷移で保存値を上書きしない、という研究の注意点を反映しています。
- 点滅の停止 callback が前面化、focus、lift をしないことを明示し、D-16 の「後から勝手に前面化しない」を守っています。
- 04-03-02 で、未保存の doc、4 手の Undo/Redo、遅延させた fake provider による OCR を実際の処理経路で通し、同一性を assert します。成功した回数だけを証拠にしない点が良いです。

### Concerns
- **HIGH: 最深モーダルの発見が実際のダイアログ構造と合わない。**
  - 入れ子の grab は元に戻りません。`SettingsDialog` が `grab_set()`（`dialogs/settings.py:36`）し、そこから開く `LLMConfigDialog` も `grab_set()` します（`dialogs/llm_config/dialog.py:82`）。Tk の grab は一つだけなので、LLMConfig を閉じると grab はなくなり、親側で張り直す処理もありません（`dialogs/settings.py:209-250`）。その状態では `grab_current()` が None を返し、Settings が開いたままなのに root を前面化します。Settings を隠してしまうので D-13 違反です。
  - 所有関係がありません。grab を使うダイアログ 11 か所（`ocr_dialog.py:156`, `batch_ocr.py:169` など）はどれも `transient()` を呼んでいません。呼んでいるのは `viewer.py:496` だけです。`GetLastActivePopup` は Win32 の所有関係を前提にしているので、所有されていない Toplevel は見つけられないと考えられます（推論）。
  - ネイティブの messagebox の多くは `parent=self` でダイアログに所有されています（`llm_config/sections.py:1469,1504,1547,1568`、`llm_config/dialog.py:554,568`）。そのため root から辿る方法では見つかりません。
- **MEDIUM: HWND の取り方が書かれていない。** Tk の `winfo_id()` は内側の子ウィンドウで、トップレベルのフレームは `wm_frame()` の値か `GetAncestor(GA_ROOT)` で得ます。ここを間違えると `SetForegroundWindow` や `FlashWindowEx` が別の窓に効きます。
- **MEDIUM: 入れ子のイベントループでの再入。** `_quit` の `askyesno`（`app.py:501`）をはじめ、ネイティブダイアログの表示中にも Tk の after は処理されるはずです（推論）。その場合、終了確認の最中に復帰 callback が動きます。W08 の「キャンセルで維持」は試験しますが、「確認ダイアログの表示中に二次起動」したときの対象選択（確認ダイアログを選ぶべき）が明示されていません。
- **LOW: root への `<Configure>` と `<FocusIn>` の bind。** root の bindtag はすべての子ウィジェットに含まれるので、子の Configure が大量に流れてきます。`event.widget is root` で絞り込まないと、描画中に負荷が増えます。
- **LOW: D-02。** 最大化から最小化した窓は、`SW_RESTORE` だけで最大化に戻るのが Windows の通常の挙動です。「SW_RESTORE の後に保存状態に従って geometry を復元する」と書かれていますが、無条件に復元すると OS の復元と競合して、ちらつきや別モニターへの移動を起こします。

### Suggestions
- 復帰対象は、同じプロセス・同じスレッドの可視で有効なトップレベルを `EnumThreadWindows` で列挙して選ぶ。親が無効化されている子を優先し、Z オーダーが最も上のものを採る。`grab_current()` は補助的な手掛かりにとどめる。
- 「Settings→LLMConfig→閉じる→Settings だけ残る」「OCRDialog の上の messagebox（parent=dialog）」「`_quit` の askyesno の表示中」の三つを W05/W08 と自動試験に明示的に加える。
- HWND は `wm_frame()` または `GetAncestor(GA_ROOT)` に統一し、`OwnedHandle` と同じく型付きの helper に閉じ込める。
- D-02 は「SW_RESTORE を実行して状態を確認し、違うときだけ補正する」と文言を固定する。

### Risk Assessment
**MEDIUM-HIGH。** 状態を保つ方針は良いものの、D-13（ダイアログを隠さない）が実際のダイアログ構造で破綻する可能性が高いです。

---

## 04-04

### Summary
編集画面を作る前の失敗を、3 分類、日英の表示、非活性、10 秒、原因ごとのプロセス間集約で案内する計画です。D-09 の「確認できた事実だけを表示する」、表示文言に技術的な詳細を出さないこと、5 秒の判定 deadline と 10 秒の通知 deadline を別オブジェクトにすること、と主要な契約は正しいです。

### Strengths
- ToastManager に依存しない独立経路は正しい判断です。ToastManager は `_build_ui` の後でしか存在しません（研究で確認済み）。
- 起動の所有権と通知の所有権を分け、同じ原因の後続起動が共有期限を書き換えられない設計にしています。
- `test_lang_parity.py:40-43,55-75`（キー集合の一致と未使用キーの検出）を検証に含めています。
- 正常復帰と前面化拒否を案内の関数へ入れない、と経路を分けています（D-14）。

### Concerns
- **MEDIUM: NoticeLease へのアクセスが拒否されたときの実行時の動作が決まっていない。** 計画には「既存案内ありと断定しない」「解決できなければ実装完了を止める」とあります。しかし、実行時にその状況になったとき、案内を出すのか出さないのかが書かれていません。もし出さなければ、黙って終了することになり V110-START-03 違反です。
- **MEDIUM: 言語判定。** `GetUserDefaultUILanguage` を使うと、アプリ内で英語を選んでいる利用者にも日本語の案内が出ます。副作用を避けることが目的なら、`_load_settings()` を使わずに JSON から `lang` だけを読み取り専用で読む方法があります（`settings.py:254` 以降。Phase 5 の自動保存の問題からも独立できます）。
- **LOW: ネイティブ窓の DPI。** リポジトリには DPI awareness の設定がありません（`ctypes`/`DpiAwareness` の grep で 0 件）。高 DPI では文字がぼやけ、サイズも崩れる恐れがあるので、W09 で確認すべきです。
- **LOW: ctypes で `WINFUNCTYPE` の WndProc を作るときは、参照を保持し続けないとクラッシュします。** 計画には明記がありません。
- **LOW: 「期限後の 15 秒間に自動復帰しないこと」の観測を全件 pytest に含めると、時間がかかります。**

### Suggestions
- lease へのアクセスが拒否された場合は、案内を表示する（最大 10 秒でプロセスも終わる）という fail-open を明文化する。重複表示は、黙って失敗するより害が小さいという判断です。
- 言語は「設定 JSON を読み取り専用で読み、失敗したら OS の UI 言語」の二段にする。
- WndProc の参照を保持すること、DPI の扱いを action に書く。

### Risk Assessment
**MEDIUM。** 設計は筋が通っています。残る課題は 04-01 由来の A3/A4 の成立と、拒否時の動作の明文化です。

---

## 04-05

### Summary
自動受入と Windows 実機の W01〜W12 を分けて記録し、未実施を合格と混同しないための締めの計画です。ケースと D-01〜D-16 の対応表、計測する項目（tick、前面の HWND、画面数）、実 EXE の確認は Phase 6 へ明示的に引き継ぐこと、と証跡の設計は良いです。

### Strengths
- 自分で起動した PID だけを回収すること、既存の PageFolio を終了させないこと、設定とプロンプトを一時ディレクトリへ隔離すること、利用者ファイルの hash を照合すること（T-04-16）。
- `sys.frozen` の差は identity 関数の試験だけで扱い、実 EXE を試した証拠とは混同しない、という線引き。
- 全件 pytest は単一プロセスで別に実行して所要時間を記録し、分割実行の合算で代えないこと（REQUIREMENTS.md:71）。

### Concerns
- **MEDIUM: W11（別ログインセッション）が用意できないと、Phase が完了できない。** 「準備不能なら not-run のまま、Phase 4 の受入を合格にしない」と定めています。利用者がアカウントを一つしか持っていない場合、Phase が永久に止まります。代わりに認める手段（2 つ目のアカウントでのユーザー切替など）か、利用者が明示的に受容する手順を事前に決めておくべきです。
- **MEDIUM: 設定とプロンプトの隔離が 04-05 で初めて導入される。** 04-01〜04-03 の試験は、この時点ですでに実設定を書き換えています（04-01 の懸念を参照）。
- **MEDIUM: DoD ゲートとの順序。** 04-01 で述べた「Progress=Complete になってから validate-phase を実行するまでの赤い期間」は、まさにこの計画の SUMMARY をコミットした時点で起きます。
- **LOW: W06 の「OS が許可した試行は拒否の実測に数えない」** は正しい方針です。ただし `AllowSetForegroundWindow` を導入した後は拒否が起きにくくなるので、拒否を実機で観測するための条件（他アプリで入力中、フォアグラウンドロックのタイムアウトなど）を手順に書いておく必要があります。

### Suggestions
- 設定とプロンプトの隔離 fixture は 04-01 の tracer で作り、以降のすべての Windows 試験で共有する。
- W11 の代わりの手段と、受容を判断する人を決めておく。
- 「04-05 の SUMMARY→validate-phase→ROADMAP の `[x]`→全件 pytest」の順序を、DoD の判定規則と一緒に固定する。

### Risk Assessment
**MEDIUM。** 記録の設計は堅いですが、完了条件が実行環境（別セッション）と DoD の自動判定の両方に依存しています。

---

## 計画全体の評価

**全体の判定: MEDIUM-HIGH。** 先に直すべき 3 点は次のとおりです。

1. **`AllowSetForegroundWindow` の追加（04-01/04-03）。** これがないと、通常の起動でも前面化が拒否される経路が多くなり、V110-FOCUS-01 の主経路が点滅だけになる恐れがあります。
2. **昇格トークンでの logon SID の扱い（04-01 の A4）。** UAC の昇格では logon SID が別になる可能性が高いです。現在の DACL と照合の方式では、Wave 1 の停止ゲートが構造的に通らない恐れがあります。user SID＋TS session ID と比べて検討すべきです。
3. **mapping の released 化（04-02）と、モーダル発見方法の修正（04-03）。** 前者は正常終了直後の再起動（V110-START-02）を、後者はダイアログを隠さないこと（D-13）を守るために必要です。

**その他の横断的な懸念:**

- **試験と品質ゲートの緊張関係。** 「単一プロセスの全件 pytest をコミットのたびに実行」「対象の Windows で skip すれば不合格」「本番の固定名で試験」の三つが重なっています。その結果、開発者がアプリを開いているだけで全件 pytest が失敗し、試験自体がデスクトップの前面化や点滅を起こします。名前空間の注入と marker の方針を 04-01 で決めるべきです。
- **規模と見積もり。** 5 計画とも confidence は low で、特に 04-01-02 が過大です。計画間の分担も重なっています（通知 primitive が 04-01 と 04-04 の両方にある）。
- **良い点。** 期限、失効、ACK の区別、未実施と合格の分離、脅威モデル、新しい依存をゼロに保つこと、`pyproject.toml` を変更しないこと、のいずれも徹底されています。CONTEXT の 16 決定への対応漏れはありません。
