## 04-01

### 1. Summary
`04-01` は、現行リポジトリで唯一失敗している DoD 機械ゲート（[tests/test_gsd_dod.py:185-204](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py#L185-L204)）の不整合を解消する前提タスク（`04-01-01`）と、Windows 名前付きミューテックス・共有メモリ（pagefile-backed mapping）・非同期（overlapped）名前付きパイプ・非活性通知ウィンドウを組み合わせた本番起動 tracer（`04-01-02`）の 2 タスクで構成されている。計画段階の未実証事項 A1〜A5 を `04-TRACER-EVIDENCE.md` に実測記録し、1 件でも未実施・不合格であれば `04-02` 以降へ進まないハードゲートを敷いている点は堅실である一方、Task 2 単体に詰め込まれた Win32 `ctypes` 実装範囲（DACL/SACL Mandatory Label 構築、Overlapped Pipe、共有メモリ seqlock、Win32 ネイティブウィンドウ生成）が非常に大きく、実装複雑性と境界バグのリスクが高い。

### 2. Strengths
- **DoD ゲートの抜け穴を作らない設計**: [tests/test_gsd_dod.py:115-143](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py#L115-L143) の `_collect_phase_dirs()` が `.planning/phases/` 配下の未完了フェーズ（`04-startup-control`）まで無条件に列挙し、[tests/test_gsd_dod.py:156-181](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py#L156-L181) の `_collect_dod_violations()` が `status: validated` を要求して失敗している現状に対し、`04-VALIDATION.md` の偽装昇格やテスト除外ではなく、[.planning/ROADMAP.md:111-156](file:///C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md#L111-L156) および [.planning/ROADMAP.md:204-208](file:///C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md#L204-L208) の現行マイルストーン定義と照合して「未完了 live のみ猶予・完了 live と対象 archive は必須・ROADMAP 記載不備や状態矛盾は違反」とする方針が、[tests/test_gsd_dod.py:249-330](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py#L249-L330) の合成ツリー self-test 構造と完全に整合している。
- **GUI 構築前の排他判定位置の明確さ**: [pagefolio/__main__.py:19-26](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/__main__.py#L19-L26) の `main()` は現在 `TkinterDnD.Tk()` / `tk.Tk()` 生成直後に [pagefolio/app.py:138-218](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L138-L218) の `PDFEditorApp(root)` を呼び、設定読込・プラグイン読込・UI 構築・Undo スタック初期化まで一気に実行する。また [pagefolio.py:11-14](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio.py#L11-L14) も `pagefolio.__main__.main` に委譲しているため、`main()` の root 生成前に `StartupCoordinator.claim()` を置くことで Python 両起動経路の副作用を確実に遮断できる。
- **Tk スレッド安全性の遵守**: IPC 受信スレッドから Tkinter API（`root.after` 含む）を一切呼ばず、`queue.Queue(maxsize=32)` への投入のみを行い、メインスレッド側の `root.after(50, ...)` ポーリングで取り出す設計は、[AGENTS.md:81-83](file:///C:/Users/shdwf/work/project/PageFolio/AGENTS.md#L81-L83) の Tkinter メインスレッド制約に合致している。

### 3. Concerns
- **[HIGH] Task 2 (`04-01-02`) の Win32 セキュリティ記述子・Overlapped I/O・ネイティブウィンドウ一括実装による複雑性とバッファ寿命リスク**:
  - `04-01-02` では標準 `ctypes` のみで (1) Logon SID 抽出と DACL + Medium Mandatory Label（SACL）構築、(2) `CreateFileMappingW` + seqlock 共有メモリ、(3) Overlapped Named Pipe + `CancelIoEx`、(4) `CreateWindowExW` + カスタム `WNDPROC` による非活性ウィンドウを 1 タスクで新規作成する計画となっている。
  - 特に Python の `ctypes` で `CancelIoEx` 後に 500ms で cleanup を打ち切る際、「完了未通知の `OVERLAPPED` / buffer は解放せず process teardown まで保持」とあるが、`GetOverlappedResult` で `ERROR_IO_INCOMPLETE` のままハンドルを `CloseHandle` してもカーネル側 I/O 完了通知が遅延到着し得るため、ローカル変数や GC 対象オブジェクトに `OVERLAPPED` 構造体や送受信バッファを置くとメモリアクセス違反（クラッシュ）を引き起こす。モジュールレベルの退避リスト等で参照を強保持する機構が明示されていない。
- **[MEDIUM] `test_gsd_dod.py` における `.planning/ROADMAP.md` パース仕様の境界条件**:
  - [.planning/ROADMAP.md:18-109](file:///C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md#L18-L109) には `<details>` ブロック内に過去マイルストーンの `- [x] Phase 4: ...`（32行目、61行目、74行目、87行目）が複数存在し、現行マイルストーンは 117行目に `- [ ] **Phase 4: 起動制御と既存画面への復帰**`（太字を含む書式）、206行目の Progress 表に `| 4. 起動制御と既存画面への復帰 | 0/5 | Planned | — |` と記載されている。
  - `04-01-01` で「details 内の過去マイルストーンを除外し、正規化した番号と現行 Phase Details を照合する」とあるが、チェックボックス行の太字（`**Phase 4:...**`）の有無や、Progress 表（[.planning/ROADMAP.md:190-208](file:///C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md#L190-L208) には Milestone summary 表と Phase Progress 表の 2 つのテーブルが存在する）のどちらの表をどうパースするかが曖昧だと、将来の ROADMAP 編集で誤って「判定不能違反」になりやすい。
- **[MEDIUM] A4（Medium / Elevated 双方向共有）の自動・手動検証における UAC 昇格前提**:
  - `04-01-02` の precondition と verify で「対象 Windows で skip なら実証未完了として停止」「A3/A4 は実デスクトップと権限差で確認する」とあるが、通常の非昇格（Medium integrity）プロセスから昇格（High integrity）プロセスを自動生成するには UAC プロンプト承認が必要であり、`pytest` の自動実行だけでは High→Medium の作成順を再現できない。自動テスト部分（`pytest -k tracer`）が検証する範囲と、人間が UAC 昇格を伴って実行するハーネス手順の境界を明確に分離しないと、CI/ローカル単一プロセス `pytest`（[.planning/PROJECT.md:185](file:///C:/Users/shdwf/work/project/PageFolio/.planning/PROJECT.md#L185)）が UAC 待ちや権限不足で失敗する恐れがある。

### 4. Suggestions
- `pagefolio/startup_win32.py` で `CancelIoEx` 後に未完了のまま残った `OVERLAPPED` と `ctypes.create_string_buffer` は、プロセス終了まで GC されないようモジュールスコープの `_LEAKED_OVERLAPPED_BUFFERS: list[ object ]` に明示的に退避させる設計を `04-01-02` の実装仕様に追記すること。
- `04-01-01` の `_read_live_phase_completion` でパースする [.planning/ROADMAP.md:117-120](file:///C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md#L117-L120) と [.planning/ROADMAP.md:204-208](file:///C:/Users/shdwf/work/project/PageFolio/.planning/ROADMAP.md#L204-L208) の正規表現は、`**Phase N:` のような Markdown 強調記号を許容し、2 つ目のテーブル（`| Phase | Plans Complete | Status | Completed |` ヘッダを持つ表）を明示的に特定する仕様に固定すること。
- `tests/test_startup_windows.py` において、単一プロセス `pytest -q` で常時走る自動テスト（同一 integrity での DACL 構造検証・SDDL/ACL 検査・Medium 同士の E2E tracer）と、実機 UAC 昇格を伴う A4 実測スクリプトの役割を分け、通常 `pytest -q` が対話 UAC プロンプトでブロックしないようにすること。

### 5. Risk Assessment
- **Risk Level: HIGH**
- **Justification**: `ctypes` による Win32 セキュリティ記述子（Logon SID + Medium Mandatory Label）・共有メモリ・Overlapped Named Pipe・非活性ネイティブウィンドウという 4 つの低レイヤ機構を `04-01-02` の 1 タスクで新規構築するため、ポインタ寿命・64bit ハンドル型定義・ACL 権限設定のわずかな不備がプロセスハングやクラッシュに直結する。

---

## 04-02

### 1. Summary
`04-02` は、二次起動時の「最大5秒の単一待機期限（D-05/D-06）」「遅延した復帰要求の受信側失効（D-08）」「500ms 固定窓による連打集約（D-03）」「先行プロセスの死亡確認時のみ 1 回だけ行う原子的引き継ぎ（D-07）」、および終了確認キャンセル時の排他維持（[pagefolio/app.py:498-507](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L498-L507)）を実装・検証する計画である。Fake clock を用いた状態遷移単体テスト（`tests/test_startup_control.py`）と実プロセス競合テスト（`tests/test_startup_windows.py`）の二段構えで検証する構成は論理的だが、「公開前死亡」や「スレッド放棄（`WAIT_ABANDONED`）」時のセカンダリ挙動と、終了処理中のタイミング競合に注意すべきエッジケースがある。

### 2. Strengths
- **終了確認キャンセル時の排他維持が既存コード構造と合致**: [pagefolio/app.py:498-507](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L498-L507) の `_quit()` では、`self.doc` が存在する場合に `messagebox.askyesno(...)` が `True` を返したときのみ `self.root.destroy()` を呼ぶ。排他解放を `_quit()` 内ではなく [pagefolio/__main__.py:26](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/__main__.py#L26) の `root.mainloop()` 終了後の `finally` 節に置くことで、終了確認ダイアログ表示中および「いいえ」選択時に所有権が維持される設計が自然に成立する。
- **送信・受信・UI 実行直前の多段失効チェック（D-08）**: 単に二次起動側が 5 秒でタイムアウト終了するだけでなく、`GetTickCount64` ベースの絶対 `deadline_tick` を要求に含め、受信スレッド・Tk メインスレッド取り出し時・各 Win32 副作用呼び出し直前に照合して破棄する設計により、タイムアウト案内後の突然の前面化を構造的に防いでいる。
- **Fake clock による境界値（4999ms / 5000ms、500ms 集約窓）の決定論的テスト**: OS スケジューリング揺らぎの影響を受ける実時間テストと分離し、`tests/test_startup_control.py` で時計・トランスポートを差し替えて厳密な境界値を検証する設計は保守性が高い。

### 3. Concerns
- **[HIGH] 一次プロセスが owner mutex 取得直後・共有メモリ（mapping）公開前にクラッシュした場合のデッドロック/復帰不能リスク**:
  - `04-02-02` では「`_try_takeover` に `takeover_attempted` フラグを設け、識別済み process handle の `WaitForSingleObject(0)==WAIT_OBJECT_0` だけを死亡証拠とする（D-07）。mutex が空く / abandoned という事実だけでは引継がない」とし、さらに「初期 claim で mutex が取得可能でも古い metadata がある場合は生存確認し、process 生存/不明なら GUI を増やさない」としている。
  - しかし、先行プロセス A が(1) mutex 取得 → (2) mapping に旧世代または不完全な metadata を残したまま、あるいは PID 書き込み直後に OS ハンドルを閉じて異常終了し、直後に別プロセスがその PID を再利用した場合や、A が mapping 初期化中に強制終了されて sequence が奇数のまま残った場合、後続のすべての起動が「古い/不正な metadata があり死亡確認不能」と判定して永久に起動できなくなる（V110-START-02「起動途中の異常終了の後に再起動でき、残留ロックで起動不能にならない」に抵触する）恐れがある。
  - Windows の pagefile-backed file mapping（`Local\PageFolio.Startup.State`）は、開いている全プロセスのハンドルが閉じられればカーネルによって破棄されるが、二次起動プロセスが監視ループ中に mapping ハンドルを開きっぱなしにしていると、一次プロセスがクラッシュしても mapping オブジェクトが消滅せず不完全な metadata が残り続ける。
- **[MEDIUM] `root.mainloop()` 終了から `finally` での mutex 解放までの微小窓における二次起動の扱い**:
  - 一次プロセスでユーザーが終了を確定し `self.root.destroy()`（[pagefolio/app.py:504,507](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L504-L507)）が呼ばれた後、`mainloop()` が抜けて `finally` で listener 停止・mapping 破棄・owner mutex 解放が終わるまでの間に二次起動が来ると、一次側はすでに Tk root を破棄しているため復帰 callback を実行できない。
  - このとき一次プロセスが単に IPC を切断・タイムアウトさせると、二次起動側では「一次プロセスが正常終了した直後なのに起動に失敗してエラー案内が出る」ことになる。一次プロセスが正常シャットダウンに入った場合は、二次起動が 5 秒期限内に一次プロセスの終了（または mutex 解放）を検知して正常に引き継げるのか、それとも D-07（「先行プロセスが起動失敗で終了したことを確認できた場合だけ」）との兼ね合いでどう扱うかが計画内で曖昧である。
- **[LOW] 本番固定名（`Local\PageFolio.Startup.Owner`）をそのまま使う subprocess テストの自己干渉**:
  - `04-02-02` で「テストは本番固定名を変更せず、既存 PageFolio の検出時にはそのプロセスを終了させず試験を中断する」とあるが、開発者が PageFolio を開いたまま `pytest` を実行するとテストが中断（fail）するほか、前のテストケースの子プロセス cleanup（最大500ms）がわずかに遅れた場合に次のテストケースと衝突し得る。

### 4. Suggestions
- **共有メモリ（mapping）ハンドル保持期間の最小化と abandoned mutex 時の検証整理**:
  - 二次起動プロセスは `Local\PageFolio.Startup.State` の mapping ハンドルを 5 秒間保持し続けず、スナップショット読み取りの都度 open → read → close するか、一次プロセスが死亡した際に mapping が OS から自動消滅できるようにすること。また、新規起動時に `CreateMutexExW` が `WAIT_ABANDONED` を返した場合（前所有者が異常終了し、現在自プロセスが唯一の mutex 所有者となった場合）かつ他プロセスが生存していない場合は、壊れた共有メモリを自プロセスで初期化して一次起動へ進めるよう条件を明確化すること（そうでないと V110-START-02 の「起動途中の異常終了後に再起動できる」を満たせなくなる）。
- **正常終了（シャットダウン中）と二次起動の競合整理**:
  - 一次プロセスが `_quit()` で `root.destroy()` に入った後に到着した二次起動については、一次プロセスの終了（`WaitForSingleObject(process_handle)` の signaled）を 5 秒期限内に確認して二次起動が引き継げるよう、D-07 の引き継ぎ条件と正常終了直後の再起動（V110-START-02）を整合させること。

### 5. Risk Assessment
- **Risk Level: MEDIUM**
- **Justification**: 期限管理と連打集約のロジック自体は明確で単体テスト容易性も高いが、共有メモリの寿命と `WAIT_ABANDONED` / 初期化途中クラッシュ時の引き継ぎ条件を誤ると、異常終了後に再起動不能になる退行リスクがある。

---

## 04-03

### 1. Summary
`04-03` は、既存画面への復帰時に最小化前のウィンドウ状態（通常/最大化）を復元し（D-02）、モーダルダイアログが開いている場合は最深のモーダルを優先し（D-13）、通常画面では直前の入力フォーカス先を維持し（D-04）、OS に前面化を拒否された場合はタスクバーを有限回（3回・250ms間隔・2秒以内停止）点滅させる（D-14〜D-16）`FocusRestorer` を実装・検証する計画である。既存の編集状態・Undo/Redo スタック・進行中 OCR を維持するテスト計画も具体的だが、現行コードベースの複数ダイアログ実装（`grab_set()` の有無や `_rebuild_ui()` による全ウィジェット破棄）と照合すると、いくつか見落とされている箇所がある。

### 2. Strengths
- **最小化前の状態追跡の正確性**: Windows の `GetWindowPlacement` が最小化中に過去の最大化フラグを保持しない仕様を踏まえ、`FocusRestorer` 側で `last_non_iconic_state` と `normal_geometry` をイベント監視して `SW_RESTORE` 後に復元する設計は、D-02 を満たすうえで適切である。
- **Undo/Redo Blob ライフサイクルおよび OCR 世代管理との非干渉**: [pagefolio/app.py:199-200](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L199-L200) の `_undo_stack` / `_redo_stack` や [pagefolio/ocr_dialog.py:197-202](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_dialog.py#L197-L202) の `self._engine` / `self._run_gen` を再生成せず、かつ [pagefolio/app.py:509-510](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L509-L510) の `_set_status()` や [pagefolio/toast.py:40-55](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/toast.py#L40-L55) の `ToastManager.show()` を呼ばない（D-01）ことで、進行中の OCR ステータス表示や再試行トーストを保護できている。
- **OS 前面化拒否時の抑制的な振る舞い（D-14〜D-16）**: `SetForegroundWindow` を 1 回だけ試行し、失敗時は `FlashWindowEx`（`FLASHW_TRAY`, `uCount=3`, `dwTimeout=250`）＋ 2 秒後の `FLASHW_STOP` のみを予約し、遅延再試行や `focus_force()` / topmost トリックを使わない方針が徹底されている。

### 3. Concerns
- **[HIGH] `_rebuild_ui()` が `root.winfo_children()` を全破棄することによる子 Toplevel 破壊と `last_focus_widget` 陳腐化**:
  - [pagefolio/app.py:696-700](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L696-L700) の `_rebuild_ui()`（言語切替 [pagefolio/app.py:602](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L602) や設定適用 [pagefolio/app.py:693](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L693) で呼ばれる）は、`for w in self.root.winfo_children(): w.destroy()` を実行する。
  - これにより、`last_focus_widget` に保持していたウィジェット参照は破棄済み（`winfo_exists() == 0`）になるだけでなく、もし `FocusRestorer` が `root` 直下に何らかの補助オブジェクトやバインディングを持つ場合に影響を受ける。`04-03-01` では「破棄済み入力先は呼ばず生存 target へ戻る」とあるため ` TclError` は防げるが、`_rebuild_ui()` 直後に二次起動が来た場合のフォールバック先（`root` 自体か特定の初期ウィジェットか）を明示しておく必要がある。
- **[MEDIUM] `grab_set()` を呼ばないダイアログ（`PluginDialog` / `BatchOCRDialog` 等）やネストしたモーダルでの `grab_current()` の挙動**:
  - `04-03-01` では「選択は `root.grab_current` の生存 Toplevel を優先し、所有子を辿って最深の有効 modal を採る。Tk の grab に現れない messagebox / 保存確認は `GetLastActivePopup` ... で検証する」としている。
  - しかし、実コードを確認すると、[pagefolio/dialogs/settings.py:36](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/settings.py#L36)（`SettingsDialog`）、[pagefolio/dialogs/llm_config/dialog.py:82](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/llm_config/dialog.py#L82)（`LLMConfigDialog`）、[pagefolio/dialogs/shortcuts.py:60](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/shortcuts.py#L60)（`ShortcutsDialog`）、[pagefolio/ocr_dialog.py:156](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_dialog.py#L156)（`OCRDialog`）は `self.grab_set()` を呼んでいるが、たとえば `SettingsDialog` から `LLMConfigDialog`（[pagefolio/dialogs/settings.py:242-250](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/settings.py#L242-L250)）や `ShortcutsDialog`（[pagefolio/dialogs/settings.py:272-277](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/dialogs/settings.py#L272-L277)）を開いて閉じた後、子 Toplevel の破棄時に親 `SettingsDialog` へ `grab_set()` を戻していないため、`root.grab_current()` が `None` になるケースがある（`SettingsDialog` はまだ開いて操作中であるにもかかわらず `grab_current()` が空になる）。
  - また、[pagefolio/app.py:318-322](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py#L318-L322) の `BatchOCRDialog` や `PluginDialog` などの生存 Toplevel についても、`grab_current()` だけに頼ると親の `root` だけが選ばれてダイアログが背面に隠れる（D-13 違反）リスクがある。
- **[LOW] `FocusIn` イベント監視による `last_focus_widget` の上書き**:
  - ウィンドウが最小化・非アクティブ化される過程や、モーダルダイアログが開く瞬間に `root` や `Toplevel` 自体に対する `FocusIn` が発火すると、直前にフォーカスしていた `Entry` や `Spinbox` の記録がウィンドウ自体で上書きされることがある。

### 4. Suggestions
- **モーダル・子 Toplevel 探索ロジックの強化（D-13 保護）**:
  - `root.grab_current()` の確認に加え、`root.winfo_children()`（およびその子孫）に存在する生存・可視（`winfo_viewable()` または `wm_state() != 'withdrawn'`）の `tk.Toplevel`（`SettingsDialog`, `LLMConfigDialog`, `ShortcutsDialog`, `OCRDialog`, `BatchOCRDialog`, `PluginDialog` 等）を走査し、ネストした `LLMConfigDialog` を閉じた直後で `grab_current()` が `None` になっていても、開いている最深の `Toplevel` ダイアログを復帰対象として選択できるようにすること。
- **`FocusIn` 記録対象のフィルタリング**:
  - `_remember_focus` で `FocusIn` を記録する際、`event.widget` がトップレベルウィンドウ（`tk.Tk` / `tk.Toplevel`）そのものである場合は、既存の有効な子ウィジェット（`Entry` 等）の記録を上書きしないようにガードを入れること。

### 5. Risk Assessment
- **Risk Level: MEDIUM**
- **Justification**: 既存の編集・OCR 状態を壊さない分離設計は良好だが、Tkinter のネストダイアログ（`SettingsDialog` → `LLMConfigDialog` 閉鎖後など）で `grab_current()` が外れる既存挙動や `FocusIn` の発火順序を考慮しないと、D-13（ダイアログを親の背面に隠さない）や D-04（直前の入力欄維持）を取りこぼすリスクがある。

---

## 04-04

### 1. Summary
`04-04` は、編集画面（Tk root）を生成する前に発生した起動失敗（排他判定不能・既存画面との通信失敗・5秒の準備待機時間切れ）を、フォーカスを奪わない非活性の Win32 ネイティブ小窓で 10 秒間（手動閉鎖可）案内し、原因クラス別の `NoticeLease` ミューテックスで複数プロセス間の連打を 1 つに集約する計画（D-09〜D-12、および D-14 との分離）である。多言語辞書（[pagefolio/lang.py](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/lang.py)）やそのパリティテスト（[tests/test_lang_parity.py](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py)）との接続も考慮されているが、静的検査テストとの整合およびネイティブウィンドウのメッセージループ・フォント周りの詳細に注意点がある。

### 2. Strengths
- **主画面・ToastManager 非依存の起動前通知（D-09〜D-12）**: [pagefolio/toast.py:30-39](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/toast.py#L30-L39) の `ToastManager` は `app.root` 構築後にメインウィンドウ内へオーバーレイ表示する仕組みであるため、起動前の失敗案内には使えない。これを `CreateWindowExW`（`WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW`, `SW_SHOWNOACTIVATE`, `WM_MOUSEACTIVATE -> MA_NOACTIVATE`）で独立実装することで、他アプリや既存 PageFolio のキーボード入力先を一切奪わずに通知できる。
- **原因クラス別のプロセス間集約と期限非延長（D-11）**: 原因ごとに独立した `NoticeLease` を原子的取得（待機時間 0）し、取得できた先頭プロセスだけが 10 秒間の表示を担い、後続プロセスは即座に終了する設計により、連打時の通知増殖と表示時間の延長をシンプルかつ確実に防いでいる。
- **OS 前面化拒否との厳格な分離（D-14）**: `foreground_denied` は `show_startup_failure` の対象外とし、タスクバー点滅のみで完了させる契約が一貫している。

### 3. Concerns
- **[MEDIUM] [tests/test_lang_parity.py:55-75](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py#L55-L75) の `test_no_unused_lang_keys` におけるリテラル文字列スキャンとの整合**:
  - [tests/test_lang_parity.py:68-74](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py#L68-L74) は、`LANG["ja"]` のすべてのキーについて `pagefolio/`・`tests/`・`plugins/` 内の `.py` ファイルに `f'"{key}"'` または `f"'{key}'"` という**引用符付き文字列リテラル**が含まれているかを検査する（`_ALLOWLIST` は現在空集合）。
  - `04-04-01` で追加する 5 キー（`startup_notice_check_failed`, `startup_notice_contact_failed`, `startup_notice_timeout`, `startup_notice_close`, `startup_notice_title`）を、もし `f"startup_notice_{reason.value}"` のように動的文字列合成で参照すると、`test_no_unused_lang_keys` が即座に FAIL する。計画文中に「確認された reason から固定キーを解決」とあるが、必ず辞書マッピング等で 5 キーすべてを完全な文字列リテラルとして `pagefolio/startup_notice.py` 内に記述する必要がある。
- **[MEDIUM] [tests/test_font_hardcode_guard.py:20-37](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_font_hardcode_guard.py#L20-L37) のソーススキャンガードへの抵触リスク**:
  - [tests/test_font_hardcode_guard.py:20](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_font_hardcode_guard.py#L20) は `pagefolio/` 配下の全 `.py` に対して正規表現 `font=\(\s*["\']Segoe UI["\']\s*,\s*\d+` をスキャンしている。`startup_notice.py` や `startup_win32.py` でフォント指定やコメントを書く際にこのパターンにマッチする記述を入れるとガードテストが失敗する。
- **[LOW] Win32 ネイティブ小窓の DPI スケーリングと「閉じる」ボタンの非活性クリック処理**:
  - `WS_EX_NOACTIVATE` を付与した親ウィンドウ上の子 `BUTTON` コントロールをクリックした際、標準の `DefWindowProcW` にそのまま流すとボタンコントロール側が `SetFocus` を試みてアクティブ化やフォーカス遷移を誘発するケースがある。`WM_MOUSEACTIVATE` で `MA_NOACTIVATE` を返すだけでなく、カスタム描画領域のクリック判定またはサブクラス化なしでフォーカスを奪わないことを `04-01-02`（A3）および `04-04-01` で確実に検証する必要がある。

### 4. Suggestions
- `pagefolio/startup_notice.py` では、`StartupFailureReason` から `LANG` キーへの変換に動的文字列結合（f-string）を使わず、`{StartupFailureReason.CHECK_FAILED: "startup_notice_check_failed", ...}` のように全 5 キーを完全な文字列リテラルで明記し、[tests/test_lang_parity.py:55-75](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py#L55-L75) の `_ALLOWLIST` を変更せずにパスさせること。
- 非活性小窓の「閉じる」操作は、子 `HWND` の標準 `BUTTON` コントロールがフォーカスを奪う挙動を避けるため、クライアント領域内のボタン矩形に対する `WM_LBUTTONUP` 判定で `DestroyWindow` を呼ぶ方式を検討すると、`WS_EX_NOACTIVATE` / `MA_NOACTIVATE` の非活性契約（D-12）をより確実に守れる。

### 5. Risk Assessment
- **Risk Level: LOW**
- **Justification**: `04-01` の A3/A4 で非活性ウィンドウと `NoticeLease` のプリミティブが実証された後に実行される Wave 4 であり、主なリスクは `test_lang_parity.py` のリテラル検査規約と Win32 クリック時の非活性維持に限定される。

---

## 04-05

### 1. Summary
`04-05` は、Wave 1〜4 で実装した起動排他・期限失効・引き継ぎ・画面復帰・非活性通知の全経路を統合検証し、Windows 11 実機での受入試験記録（`04-WINDOWS-UAT.md` の W01〜W12）と `04-VALIDATION.md` の更新、および人間による実機検証ゲート（`04-05-02` `checkpoint:human-verify`）を経て `/gsd-validate-phase 4` へ引き渡す最終プランである。自動テスト・故障注入・実機確認・Phase 6（実 EXE 同梱検証）の責務境界が明確に分離されており、未実施項目を合格と偽装しない規律が徹底されている。

### 2. Strengths
- **自動検証と実機 UAT、および Phase 6 範囲の明確な分離**: W01〜W12 のマトリクスにより D-01〜D-16 と V110-START-01〜03 / V110-FOCUS-01〜02 が漏れなくカバーされており、かつ「OS 前面化拒否」「UAC 昇格を伴う権限差」「別ログインセッション」などモックでは証明できない項目を `blocking-human` チェックポイントとして切り出している。また、PyInstaller 実 EXE の最終検証を Phase 6 担当として明記し、Phase 4 時点での `sys.frozen` 単体テストと混同しないよう釘を刺している点も優れている。
- **ユーザー環境を破壊しないテストハーネス設計（T-04-16）**: `tests/test_startup_windows.py` が既存のユーザー PageFolio プロセスを検出した場合に強制終了せず中断すること、および設定やプロンプトファイルを `tmp_path` 等の一時フィクスチャへ隔離して本番ファイルを汚さないことが明記されている。

### 3. Concerns
- **[MEDIUM] 単一プロセス全件 `pytest -q` の実行時間肥大化リスク**:
  - [.planning/phases/04-startup-control/04-VALIDATION.md:22,29](file:///C:/Users/shdwf/work/project/PageFolio/.planning/phases/04-startup-control/04-VALIDATION.md#L22-L29) によると、計画時 baseline の全件 `pytest -q` は 34.31 秒、最長フィードバック時間の目標は 120 秒とされている。
  - しかし、`tests/test_startup_windows.py` には `04-01`〜`04-05` を通じて実 subprocess を起動するテスト（5秒タイムアウト、10秒通知自動閉鎖、閉鎖後15秒間の非復帰観測 `04-04-02`、2〜8プロセス同時起動 `04-02-02`、別配置コピー `04-05-01` 等）が多数追加される。実時間で 5 秒・10 秒・15 秒待つ subprocess テストを複数直列に走らせると、`pytest -q` 全体の実行時間が 120 秒を大きく超過する可能性がある。
- **[LOW] W11（別ログインセッション独立）の実機確認環境**:
  - Windows 11 実機で別ログインセッション（別ローカルユーザーへのサインイン＋ユーザー切り替え）を用意できない開発環境では W11 が `not-run` となるが、`04-05-02` の action で「準備不能は not-run で残し Phase 4 受入を合格にしない」「必須 Windows ケースが fail/not-run なら親へ返して修正または確認を継続し、Phase 完了へ進めない」とあるため、もしシングルユーザー環境だと Phase 4 が完了できなくなる可能性がある。

### 4. Suggestions
- **実 subprocess テストにおけるタイマー定数のテスト用注入（本番デフォルト不変）**:
  - Fake clock 単体テストで 5000ms / 10000ms の数値境界を厳密に保証したうえで、実 subprocess を使う `tests/test_startup_windows.py` の一部ケース（特に「タイムアウト後の 15 秒間非復帰観測」など）では、テスト用 bootstrap の factory 引数経由で待機・通知タイマーを短縮できる仕組み（本番エントリは 5000ms / 10000ms 固定）を用意し、実時間 5 秒・10 秒フル待機は代表の受入ケース 1 件ずつに絞ることで、単一プロセス `pytest -q` を 120 秒以内に収めること。
- **W11（別セッション）の検証手順の具体化**:
  - Windows 11 実機で別アカウントへの切り替えが難しい場合に備え、`Local\` 名前空間オブジェクトが現在のセッション ID スコープ（`\Sessions\<SessionId>\BaseNamedObjects\...`）に生成されていることの Win32 API / カーネルオブジェクトパス確認と、実アカウント切り替えによる確認のどちらを必須条件とするかを `04-WINDOWS-UAT.md` の判定基準に明記しておくこと。

### 5. Risk Assessment
- **Risk Level: LOW**
- **Justification**: 新規のプロダクション機能追加はなく統合テストと実機検証の計画であり、主に実 subprocess テスト群の総実行時間管理と実機 UAT 環境準備（別セッション・昇格権限）の運用面に留意すればよい。

---

## Cross-Plan Comparison & Overall Assessment

| Plan ID | Wave | 主な責務 | Risk Level | 最重要の確認ポイント |
|---|---|---|---|---|
| `04-01` | 1 | DoD ゲート修正＋Win32 排他/IPC/非活性通知の本番 tracer と A1〜A5 実証 | **HIGH** | `CancelIoEx` 後の `OVERLAPPED` バッファ寿命管理、ROADMAP パーサの堅牢性 |
| `04-02` | 2 | 5秒単一期限・受信側失効・500ms 集約・先行プロセス死亡確認後の 1 回引き継ぎ | **MEDIUM** | 共有メモリ公開前クラッシュ / `WAIT_ABANDONED` 時の再起動可能性（V110-START-02） |
| `04-03` | 3 | 最小化前状態復元・最深モーダル優先・直前フォーカス維持・有限タスクバー点滅 | **MEDIUM** | ネストダイアログ閉鎖後の `grab_current()==None` 対策、`_rebuild_ui` との整合 |
| `04-04` | 4 | 起動前失敗の 3 分類・10秒非活性案内・原因別 `NoticeLease` 集約 | **LOW** | [tests/test_lang_parity.py:55-75](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_lang_parity.py#L55-L75) の文字列リテラル参照規約との整合 |
| `04-05` | 5 | 全起動経路の統合テストと Windows 11 実機 UAT（W01〜W12）・DoD 検証接続 | **LOW** | 実 subprocess テスト追加後の単一プロセス `pytest -q` 総実行時間（120秒目標） |

### 全体評価（Overall Conclusion）
Phase 4 の全 5 プラン（`04-01`〜`04-05`）は、承認済み要件（`V110-START-01〜03`, `V110-FOCUS-01〜02`）およびユーザー決定事項 `D-01〜D-16` を漏れなくカバーしており、Wave 1 で技術的不確実性（A1〜A5）と DoD ゲートの前提不整合を解消してから段階的に状態遷移（Wave 2）・UI 復帰（Wave 3）・失敗案内（Wave 4）・実機統合検証（Wave 5）へ進む依存関係も妥当である。既存の [pagefolio/__main__.py](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/__main__.py)、[pagefolio/app.py](file:///C:/Users/shdwf/work/project/PageFolio/pagefolio/app.py)、[tests/test_gsd_dod.py](file:///C:/Users/shdwf/work/project/PageFolio/tests/test_gsd_dod.py) の構造とも正確に噛み合っているため、上記各セクションで指摘した境界条件（特に `04-01` の非同期 I/O バッファ寿命、`04-02` の初期化途中クラッシュ後の再起動、`04-03` の生存 Toplevel 探索フォールバック、`04-04` の `LANG` キーの静的リテラル記述）を実行時に反映することで、安全にフェーズ目標を達成できる。
