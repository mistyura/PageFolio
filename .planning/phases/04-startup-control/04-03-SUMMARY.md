---
phase: 04-startup-control
plan: "03"
subsystem: startup
tags: [windows, win32, tkinter, focus, modal, undo, ocr, pytest]
requires:
  - phase: 04-02
    provides: 絶対期限・世代検査・再入防止・terminal ACK付きの起動要求
provides:
  - 通常/最大化のplacement、Toplevel別入力先、Tk/nativeモーダルを維持するFocusRestorer
  - 同一process/UI-threadの正規化HWNDと所有popupの検証、前面化一回と有限点滅
  - 実PDF編集・Blob/Undo/Redo・実OCR workerの同一性と処理継続を確認する回帰試験
affects: [04-04, 04-05, startup-control, phase-6-release]
actuals:
  tokens: 26686
  tasks: 2
  commits: 2
plan_head_before: 54cbe4edb977fe95164be7be08f6117a348766bd
plan_head_after: 21156e78f3ebb345fcbc58aad453c7a1583d28b7
tech-stack:
  added: []
  patterns: [Tk mainthread復帰controller, Toplevel別FocusIn観測, 検証済み所有popup優先, 有限停止callback]
key-files:
  created:
    - pagefolio/startup_focus.py
    - tests/test_startup_focus.py
    - .planning/phases/04-startup-control/04-03-EVIDENCE.json
    - .planning/phases/04-startup-control/04-03-red.json
    - .planning/phases/04-startup-control/04-03-red.xml
    - .planning/phases/04-startup-control/04-03-task2-red.json
    - .planning/phases/04-startup-control/04-03-task2-red.xml
  modified:
    - pagefolio/__main__.py
    - pagefolio/app.py
    - pagefolio/startup_win32.py
    - tests/test_startup_windows.py
key-decisions:
  - __main__が同じappへFocusRestorerを1つ結び、backend.restore_windowから委譲する。coordinatorのis_currentを各副作用直前まで維持する
  - Toplevelごとのbinding IDだけを所有し、50msのTk観測timerで発見を補完する。close時に自分のbinding/timerだけを解除する
  - Tk masterとWin32 ownerを別に検証し、native modalの内部focus/grabには触れない
  - 前面化成功とOS拒否を実測で分け、他アプリ前面時の見た目と本番固定名経路は04-05 W06/W12へ渡す
requirements-completed: [V110-FOCUS-01, V110-FOCUS-02]
coverage:
  - id: D1
    description: 通常/最大化の復元、直前入力先とTk/nativeモーダル選択、世代/期限失効
    requirement: V110-FOCUS-01
    verification:
      - kind: unit
        ref: tests/test_startup_focus.py
        status: pass
      - kind: automated_ui
        ref: tests/test_startup_windows.py#test_focus_restore_real_main_windows
        status: pass
    human_judgment: false
  - id: D2
    description: 未保存PDF、同一Document/履歴/Blob、実OCR workerとgenerationを維持し作業を続行
    requirement: V110-FOCUS-02
    verification:
      - kind: integration
        ref: tests/test_startup_focus.py#test_working_state_real_pdf_history_and_blobs_continue
        status: pass
      - kind: integration
        ref: tests/test_startup_focus.py#test_ocr_same_engine_worker_and_generation_complete_after_restore
        status: pass
      - kind: automated_ui
        ref: tests/test_startup_windows.py#test_working_state_real_main_continues
        status: pass
    human_judgment: false
  - id: D3
    description: 前面化拒否時はfocusを奪わず3回/250ms点滅と停止だけを行い、自動再前面化しない
    requirement: V110-FOCUS-01
    verification:
      - kind: unit
        ref: tests/test_startup_focus.py#test_foreground_denied_only_flashes_and_stop_never_retries
        status: pass
      - kind: automated_ui
        ref: .planning/phases/04-startup-control/04-03-EVIDENCE.json
        status: pass
    human_judgment: false
  - id: D4
    description: 他アプリ前面・本番固定名Explorer/端末経路での見た目と利用者の操作感
    verification:
      - kind: manual_procedural
        ref: 04-05-PLAN.md W06/W12
        status: unknown
    human_judgment: true
    rationale: 04-05で実施する利用者確認。OS拒否の自動試験を前面化成功や視覚評価に読み替えない
duration: 35min
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 3: 既存画面のplacement・モーダル・作業継続 Summary

**既存appを再生成せず、正規化した自processのHWNDへ一回だけ復帰し、入力先・モーダル・未保存PDF履歴・OCRを維持する。**

## 実行実績

- 2/2タスク完了。製品/試験Python 6ファイル、RED証拠4ファイル、測定証拠1ファイル。
- 所要約35分。初期読込開始の厳密時刻は未記録。最初のRED XMLの保存は **2026-10-21T14:05:47Z**、Task2コミットは **14:34:58Z**。RED保存後だけでも29分11秒。
- `actuals.tokens`は永続ledgerのbase..after実diff **106743文字÷4の切上げ26686**。製品・試験・RED/Windows証拠を含み、本SUMMARYを含まない。
- `actuals.commits`は同じbase..afterの`git rev-list --count`実測 **2**。SUMMARY metadata commitはこの測定後。

## タスク別コミット

1. **Task 1: 最小化前の状態とモーダル/入力先を維持して復帰する** — `91861d9`。
2. **Task 2: 実際の編集・Undo/Redo・OCR継続を復帰操作で壊さないことを固定する** — `21156e7`。

削除ファイルなし。追加依存なし。`pyproject.toml`、版番号、README、開発履歴は未変更（版同期は承認済みPhase 6）。

## 実装内容

- `__main__`が同じapp/rootへFocusRestorerを1つ構築し、backend経由でcoordinatorの復帰callbackへ接続する。workerからTkを操作せず、app/doc/stack/OCR/status/Toastは作り直さない。
- root自身のConfigure/Mapだけから最後の非最小化状態と通常geometryを記録する。iconic/withdrawnでは上書きしない。SW_RESTORE後の実状態を再読し、状態または通常geometryが食い違う場合だけ補正する。
- 各ToplevelのFocusInをadd登録し、自分のbinding IDだけ解除する。生存子widgetのfocusをToplevel自身のFocusInで上書きしない。50msのmainthread観測と復帰直前走査で追加dialogを補完し、破棄済み参照を除去する。
- grab、最後の操作Toplevel、生存master、同じUI-threadのZ-order、rootの順で復帰先を選ぶ。grab_set/release、dialog再作成、focus_force、topmost、AttachThreadInput、擬似入力は復帰処理に入れない。
- `GetAncestor(GA_ROOT)`/wm_frameでTk内側HWNDを正規化し、IsWindow・PID・UI-threadを照合する。各Tk Toplevelを起点にGetGUIThreadInfo/GetLastActivePopup/EnumThreadWindows/GW_OWNERを調べ、可視・有効で無効親を持つ検証済みnative popupを優先する。不明owner・循環・別process/UI-thread、検証済みpopupのない無効親には作用しない。
- 各復元、前面化、focus、点滅直前にrequest有効性・backend世代・対象生存/正規化HWND・native modalを再検査する。backendの一回のSetForegroundWindow結果をterminal ACKへ渡す。拒否時はrootのタスクバーHWNDへFLASHW_TRAY/uCount=3/dwTimeout=250、1000ms後に世代/生存確認付きFLASHW_STOPだけを予約し、再前面化timerを残さない。

## 検証結果

| 検証 | 実測 |
|---|---|
| Task1コミット前の単一全件pytest | **1518 passed / 1 warning / 105.56秒** |
| 最終単一全件pytest | **1550 passed / 1 warning / 207.32秒** |
| 復帰単体の最終個別実行 | **27 passed / 1 warning / 0.21秒** |
| 計画指定working_state/modal/ocr抽出 | **9 passed / 13 deselected / 0.21秒** |
| 計画指定Windows focus_restore/working_state抽出 | **20 passed / 28 deselected / 90.17秒** |
| ruff check / ruff format / pagefolio.py AST | **All checks passed! / 97 files left unchanged / AST OK** |
| 最終子process残留 | `_test_scenario_bootstrap` Python **0**（CIM読取） |

抽出のdeselectedは指定`-k`の結果。最終全件に全27単体と全20追加Windowsケースを含み、対象Windowsケースのskipなし。最終warningは既存PyMuPDFのByteString非推奨警告のみ。

最終全件fixtureは `C:/Users/shdwf/AppData/Local/Temp/pytest-of-shdwf/pytest-41`。
生JSONを本実行で読み直した20件を `04-03-EVIDENCE.json` に保存した。

- script/module両入口からthumb/preview、Settings入力、Settings→LLMConfig閉鎖後grabなし、OCR所有native messagebox、終了確認とNo後、UI再構築、normal/iconic、zoomed/iconicを確認（18件）。
- 実main上の未保存PDFを回転/複製/削除し、復帰前後のapp/Document/各履歴エントリ/Blobのidentity・内容digest・選択・statusを比較。復帰後も同じ履歴でUndo→Redo→Undo→Redoを完了（1件）。
- 実OCRDialogのメインスレッドrender→OCRRunEngine→遅延fake providerを通し、同じdialog/run generation/engine/workerで復帰後にOCR結果へ到達（1件）。実API/課金なし。fitz/Tkをworkerへ渡さない。
- WindowsのSetForegroundWindow実結果は **completed 4件 / foreground_denied 16件**。normal/zoomed復元の4件が成功。native OCR/終了確認は正規化Tk親と異なる所有popup HWNDが選択された。入力文字・カーソル/selection・元grab・作業内容は全件保持。
- `focus_correct`は拒否時にfocus_setしない契約も含む。拒否16件を実キーボードfocus復帰成功と解釈しない。実際の見た目と他アプリ前面の確認は04-05 W06/W12。
- 各spawnで設定/2種プロンプト/pluginsとnamespaceを隔離。元設定/2種プロンプトの存在とSHA-256不変をautouse fixture/bootstrapが検証。native確認は自動で有限閉鎖し、人間のクリック/UACを通常pytestへ入れない。
- 既存Phase 1の安全境界・Phase 2のAPIキー非永続/Apply/Cancelも最終全件に含む。

## TDD Gate Compliance

- Task1は14件が明示AssertionErrorで失敗したJUnit XMLを保存。対象placementテスト内の「controllerが存在する」assertが未実装を検出したもので、当時placementの動作までは実行していない。収集/構文/import例外の失敗ではなく、`04-03-red.json`の機械判定は`RED_EVIDENCE_OK`。
- Task2の追加回帰は、当初は既存Task1実装が満たしていた。更に再構築後の破棄済みfocus参照の除去をassertし、実際に失敗することを観測した。JUnitと`04-03-task2-red.json`を保存し、`RED_EVIDENCE_OK`と対象AssertionErrorを確認してから修正した。
- OSがnormalへ戻したがgeometryだけ不一致のケースも先にassert失敗を観測し、補正分岐を修正した。最終27件と全1550件でGREEN。
- **RED単独commitなし**。AGENTS.mdの「コミット前pytest合格」を優先し、各タスクの全件GREEN後にatomic commitした。TDDのRED commit契約からの逸脱として明示する。専用REFACTOR commitは不要。

## Deviations from Plan

### 自動修正した問題

**1. [Rule 1 - Bug] Tk Menuの誤認**
- Task1の最初の全件実行で、Menuがwinfo_toplevel()から自身を返しstate()を持たないため、実main初期化が失敗した（11 failed / 1506 passed）。
- ウィンドウstate APIを持つ対象だけを登録し、Menu回帰を追加。`91861d9`で修正し、全1518件合格後にcommit。

**2. [Rule 1 - Bug] 破棄済みfocus/dialog参照の保持**
- Task2の再構築回帰で、操作自体はrootへ安全に戻るがlast_focus_widgetが破棄済み参照を保持すると判明。
- 生存親へ連結し直して破棄済みwindow/binding/focus参照を除去。native所有関係の不明/循環回帰と合わせ、無効親への作用も防止。`21156e7`。

**3. [Rule 1 - Bug] 通常状態一致時のgeometry不一致**
- Task2でSW_RESTORE後にstate=normalだがgeometryだけ異なるfake結果を追加し、実失敗を観測。
- state補正とgeometry補正を分離し、実値が一致していれば書き換えず、不一致時だけ期限/世代検査後に補正。`21156e7`。

Task2の計画対象は主に試験だったが、これらはTask1変更が直接生んだ不備のため、startup_focus/startup_win32への小修正を同タスクへ含めた。追加依存/構成変更なし。

## 実行上の問題

- pytestの一時領域アクセス拒否は正規の昇格で再実行し解消した。試験除外や別の保存先への迂回は行っていない。
- PowerShellのRED JSON変換がCPUを消費して停止したため、同じJUnitをNodeでJSON化して検証。停止したシェルのコマンド行を照合し、そのPID31292だけをtaskkillで終了した。証拠を捏造/省略していない。
- 未解決の実装不具合・既知stub・skipped testなし。計画外の新しいnetwork/auth/schema境界なし。WINDOWSへ記録すべき未実施自動verifyなし。

## 後続への申し送り

- **04-04は開始していない。** 04-05でW06/W12の人間による実前面/他アプリ入力/見た目を確認する。実EXE、ビルドと版同期はPhase 6。
- STATE/ROADMAP/REQUIREMENTS/config/state.jsonは親オーケストレーターが単一書き手。子は更新もcommitもしていない。実装完了2/2とmetrics/decisionsを親が反映する。
- `restore_window(hwnd, is_current=...)`のguardを後続変更でも各副作用直前まで接続し続けること。
- [GetGUIThreadInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getguithreadinfo)、[GetLastActivePopup](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastactivepopup)、[SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow)の公式仕様を実装時に参照した。

## Self-Check: PASSED

- 新規製品/試験ファイル、RED4ファイル、Windows測定証拠、SUMMARYの存在を確認した。
- `91861d9` / `21156e7`の両commitがHEADの祖先であることを`git merge-base --is-ancestor`で確認した。
- `git diff --check`合格。両task commitに追跡ファイルの削除なし。
- 永続ledgerのbase/after、2commit、実diff文字数を読み直した。親所有のplanning変更をstageしていない。
