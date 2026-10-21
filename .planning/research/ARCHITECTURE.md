# v1.10.0 アーキテクチャ調査

**対象:** PageFolio の起動一意性、既存画面復帰、設定 I/O 通知、配布サンプル同梱
**調査日:** 2026-10-21
**根拠の性質:** 現行ソース・追跡ファイル・既存ドキュメントの読解。Windows 実機動作と新設計は未検証。

## 結論と構成

起動調停は `pagefolio.__main__.main()` の Tk 生成より前に置く。プロセス間で共通の起動識別子を使い、最初のプロセスだけが `PDFEditorApp` を作成する。後続プロセスは既存プロセスへ「画面を表示」の信号だけを送り、GUI を生成せず終了する。識別子へアプリ版・インストール場所・Python/EXE の種別を入れない。同一 Windows ログインセッションに限定する。Windows API・通信方式の具体選定は STACK 調査とフェーズ計画で確定する。

```text
pagefolio.py / python -m pagefolio / 配布 EXE
    -> pagefolio.__main__.main()
       -> 起動調停（同一セッション、全配置・全版共通）
          ├─ 初回: 所有権を保持 -> Tk root -> PDFEditorApp -> mainloop
          │                      └─ アクティベーション受信 -> Tk メインスレッドへ転送
          ├─ 後続: 表示要求を送信 -> 終了（編集画面を作らない）
          └─ 判定失敗: 理由を通知 -> 終了（重複起動へ倒さない）

PDFEditorApp.__init__
    -> settings.py: 読込結果/失敗情報 -> UI 完成後に通知
    -> 操作別の保存呼出し -> settings.py: 保存結果 -> UI で失敗通知

ソース管理のサンプル原本 -> 再現可能なビルド工程 -> 配布先のサンプル
ユーザーの設定・編集用プロンプト -> ビルド上書きから保護
```

現状 `pagefolio.py` は `main()` への委譲、`pagefolio/__main__.py:19-26` は Tk 作成・`PDFEditorApp` 作成・D&D 登録・mainloop だけで、一意性判定はない。両起動経路を同じ `main()` に集約したまま、調停用の新規モジュール（例: `pagefolio/single_instance.py`）をそこから呼ぶ。`PDFEditorApp` や OCR にプロセス判定を混ぜない。[根拠: `pagefolio/__main__.py:19-26`、`pagefolio.py:11-14`]

## コンポーネント境界

| 境界 | 現行と推奨責務 | 統合点 |
|---|---|---|
| `pagefolio/__main__.py` | 全起動方式共通の入口。起動所有権の獲得・後続起動の分岐・所有権の終了時解放を制御。 | `TkinterDnD.Tk()` / `tk.Tk()` より前で判定し、`mainloop()` を `try/finally` で囲む。 |
| 新規 `pagefolio/single_instance.py` | OS 側資源と、後続プロセスからの「画面表示」要求の送受信。UI や PDF を import しない。 | 先行側の受信を `queue` 等へ渡す。Tk 操作は呼ばない。 |
| `pagefolio/app.py` | GUI と文書状態の所有者。起動時診断を UI 完成後に提示し、設定保存結果に応じた通知を出す。 | `__init__` の読込、`_quit()`、`_save_window_state()`、`_apply_settings()`、`_apply_llm_settings_live()` 等。 |
| `pagefolio/settings.py` | JSON 読込/保存の成否と原因を呼出し元へ伝える。機密キー除外と原子的置換は保持。 | `_load_settings()` / `_save_settings()` の互換性を考慮した結果 API。 |
| `pagefolio/toast.py` / `ui_builder.py` | 既存トーストは単一、再試行ボタンが必須。設定失敗に流用する場合は責務と置換動作の設計が必要。 | `_build_ui()` が毎回 `ToastManager` を生成。起動時は未生成。 |
| 新規ビルド工程とサンプル原本 | ソース側原本を入力とし、配布物の２ファイルを検証可能に生成。ユーザー設定と編集用プロンプトをビルド対象と区別。 | `docs/DEVELOPMENT.md` のビルド手順、配布検査。 |

## 起動と画面復帰のデータフロー

1. `main()` は Tk 作成前に、一意の名前で所有権を原子的に獲得する。同時クリックでも所有者は一つ。所有権が失われるまで先行側のハンドルを生存させ、正常終了時は解放する。強制終了では OS 資源の解放に依存し、残留ファイルの有無で起動可否を決めない。別版・別配置・Python/EXE のプロセスで同じ名前・通信規約を使う。
2. 後続起動は既存側へ復帰要求を送る。先行側がまだ Tk を作成中なら受信準備まで短時間待ち、送信失敗と「既に起動中」を混同しない。通信不能のまま二つ目の編集画面を開かない。今回送るデータは復帰要求だけで、PDF 引数を含めない。
3. 受信側が別スレッドであれば、Tk 操作をそのスレッドで実行せず、メインスレッドの `root.after()` で処理する。既存の UI スレッド制約は `.planning/PROJECT.md:193-196`。最小化解除、可視化、前面表示を試みる。設定ダイアログ等のモーダル子画面が開いていればその画面を尊重し、PDF や未保存編集・OCR の状態には触れない。Windows のフォーカス制限下で前面化できない場合の通知/タスクバー表示は実機で決める。
4. 後続側は要求結果に従い終了。起動判定 API が失敗した場合は「起動済み」と異なるエラーを表示して終了する。`--noconsole` 配布物では標準出力のみでは利用者に伝わらないため、Tk を作らず使える通知経路を用意する。

`PDFEditorApp._quit()` は現在 `_save_window_state()` の後、開いている文書に対して終了確認を行い、確認後に `root.destroy()` する（`pagefolio/app.py:498-507`）。所有権を `_quit()` の冒頭で解放すると確認キャンセル中に二つ目が起動する。所有権の生存期間は `main()` 側の `mainloop()` 完了までとし、例外終了も `finally` で閉じる。復帰イベントは起動直後の UI 未完成時に蓄積し、ルート構築後に処理する。

## 設定 I/O と通知のデータフロー

現行の `_load_settings()` はファイルなしを通常の既定値利用とし、JSON 破損・権限等の例外も同じ既定値へ落として `debug` ログだけに記録する（`pagefolio/settings.py:254-311`）。`PDFEditorApp.__init__` は UI 生成前の `app.py:148` で呼ぶ。UI は `app.py:213-218` に達するまでなく、ステータス欄は `ui_builder.py:136-139`、トーストは `ui_builder.py:187` で初めて作られる。従って読込層は例外を UI 表示せず失敗診断を返し、`app.py` が UI 構築後に一度表示する構成が妥当。ファイル不在と読み込み失敗は必ず区別する。

現行 `_save_settings()` は保存用コピーから `_SENSITIVE_KEYS` を除外し（`settings.py:314-327`）、`.tmp` 書込後 `os.replace` する（`settings.py:328-340`）。例外は `debug` ログのみで、呼び出し元に成否を返さない（`settings.py:341-342`）。保存結果を返す互換 API または別の詳細結果 API を設け、UI 側の共通保存アダプタが失敗通知を出す。保存の失敗は「設定を変更しました」という成功ステータスと併記しない。現行 `app.py:685-694` は結果を見ずに `_rebuild_ui()` と成功表示へ進むので変更点となる。UI 再構築でトースト自体が破棄されるため、保存失敗の通知時点も再構築後に置くか、独立したダイアログを使う。

保存呼出しは `app.py:584,601,635,678,692`、`viewer.py:164,185`、`redact_ops.py:261`、`dialogs/shortcuts.py:285`、`ocr_dialog.py:1042`、`dialogs/settings.py:233` に散在する。特にネスト LLM 適用では `dialogs/settings.py:230-240` と `app.py:677-678` が同じ変更を二度保存する。エラー通知の重複を避けるためこの経路を一度に整理する。`SettingsDialog._apply()` はウィンドウを先に閉じてから callback を呼ぶ（`dialogs/settings.py:279-284`）ので、失敗通知をダイアログ自身へ依存させない。`_quit()` のウィンドウ状態保存失敗は `root.destroy()` 前に通知する。

失敗した設定読込後に既定値を自動保存すると、既存の破損/読込不能な `pagefolio_settings.json` を上書きし得る。読込失敗フラグを保持し、明示的な復旧または原本退避が終わるまで自動保存で置換しない設計を検討する。少なくとも失敗通知で既定値運用と未保存の可能性を明示する。現行 JSON の原子的置換と API キー非永続化は維持し、例外メッセージやログへ設定内容・API キー値を含めない。[根拠: `settings.py:25-29,301-342`、`.planning/PROJECT.md:199-200`]

既存 `ToastManager.show(category, message, retry_cb)` は再試行ボタン必須、別カテゴリの表示を置換する（`toast.py:40-55,80-86`）。保存/印刷の再試行表示と競合するので、設定エラーを無条件に同トーストへ載せない。設定保存失敗を持続表示するなら表示契約を拡張するか `messagebox` 等の独立表示を使う。起動時にはトーストがないため、読込警告は UI 構築後の通知に限定する。[根拠: `ui_builder.py:189-200`]

外部の実利用プロンプト `ocr_custom_prompt.md` / `ocr_summary_prompt.md` は `settings.py:32-44` の `_get_base_dir()` を基準に置かれ、EXE 時は exe ディレクトリ、開発時はプロジェクトルートとなる（`constants.py:21-22`）。`save_prompt_file()` は別 API で失敗時 `False` を返すが、`dialogs/llm_config/dialog.py:619-622` は戻り値を見ていない。この問題は設定 JSON 失敗通知とは別に受入範囲を確認する。サンプルファイルとユーザー編集の実利用ファイルを混同しない。

## 配布ビルドの配置と保護

現行で Git 追跡されるサンプルは `dist/PageFolio/ocr_custom_prompt_sample.md` と `dist/PageFolio/ocr_summary_prompt_sample.md` の２点だけ。`git ls-files` では `*.spec` やビルドスクリプトは見つからず、作業ツリーにも `PageFolio.spec` と `pagefolio/samples/` はない（2026-10-21 確認）。`README.md:19-21` は onedir 配布を案内し、`docs/DEVELOPMENT.md:63-103` は手動 PyInstaller コマンド、追跡済み dist、`--noconfirm` 時のサンプル退避/復元を記載する。**README/開発ガイドの記載はビルド自動化資産の存在を示さない。** 実際の消失は `.planning/quick/260722-rel-v181-merge-release/SUMMARY.md:16-26` に記録されている。

正本を `pagefolio/samples/` 等のソース管理下へ配置し、ビルドスクリプトを新設して、PyInstaller 出力後に２サンプルを exe と同階層へコピーし、存在・内容一致を機械確認する方式を推奨する。ランタイムの `_get_base_dir()` やユーザー用ファイル名を変えず、アプリコードへサンプル展開処理を入れない。ビルド先は使い捨ての staging とし、既存の `dist/PageFolio/` を実利用している場合の `pagefolio_settings.json` や編集用 `ocr_*.md` を無確認で消去しない。配布物へ反映する前に差分とコピー先を検証し、サンプルの原本が dist の再作成で失われないことを確認する。

## 実装順と検証境界

1. 起動識別と通信契約、所有権の寿命、起動中の受信待機を決め、`__main__.py` と新規調停モジュールへ実装。二重 Tk 生成の回帰を防ぐ。
2. 先行側の復帰要求を Tk メインスレッドへ接続。最小化、モーダル画面、OCR 中、強制終了後を Windows で確認する。
3. 設定 I/O の成否伝達と UI 通知を一元化。読込失敗時の原本保護、設定ダイアログの二重保存、全直接保存呼出しを対象にする。
4. サンプル正本と再現可能なビルド工程を追加し、クリーンな onedir 出力と既存のユーザー編集ファイル保護を確認する。

この文書の検証はソース・`git ls-files`・作業ツリーの読解のみで、アプリ起動、PyInstaller ビルド、テストは実施していない。実装フェーズでは同時起動、別版/別配置/Python/EXE、最小化、起動直後、終了確認キャンセル、設定ファイル破損/権限拒否/置換失敗、ビルド２回目を試験する。起動時 PDF 引数引継ぎ、OCR 共通化、一般的な負債解消は今回扱わない。

## 未解決の設計点

- Windows API/IPC の具体選定、先行プロセスがまだ受信準備前の場合の再試行上限、Windows の前面化制限への代替表示。STACK 調査と実機スパイクで確定する。
- 読込失敗後の設定原本退避と再保存を、どの操作で明示的に許可するか。データ保全と通知体験をフェーズ計画で決める。
- `save_prompt_file()` の失敗通知を「設定保存失敗」に含めるか。現行は失敗を戻すが呼出し側は無視している。

## 主な根拠

- 現行ソース: `pagefolio/__main__.py:19-26`、`pagefolio/app.py:138-218,498-510,574-601,667-719`、`pagefolio/settings.py:25-49,254-342`、`pagefolio/ui_builder.py:136-139,187-200`、`pagefolio/toast.py:30-86`。
- 呼出しと画面: `pagefolio/dialogs/settings.py:225-240,279-284`、`pagefolio/dialogs/llm_config/dialog.py:604-622`、`pagefolio/ocr_dialog.py:1037-1047`、`pagefolio/viewer.py:158-185`、`pagefolio/dialogs/shortcuts.py:274-286`。
- 配布・制約: `README.md:19-21`、`docs/DEVELOPMENT.md:63-103`、`.gitignore:9-14,71-75`、`.planning/PROJECT.md:10-22,189-201`、`.planning/notes/GSD_HANDOFF_2026-10-21.md:21-32,102-126`、`.planning/quick/260722-rel-v181-merge-release/SUMMARY.md:16-26`。
