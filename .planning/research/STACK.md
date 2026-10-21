# Stack Research — PageFolio v1.10.0

**対象:** Windows 11 デスクトップ PDF エディタの多重起動防止と既存画面への復帰
**調査日・公式資料アクセス日:** 2026-10-21
**総合確信度:** MEDIUM（Microsoft・Python 公式仕様は照合済み。PageFolio の Windows 配布 EXE による結合検証は未実施）

この文書は v1.10.0 の起動制御に必要な技術選定に限定する。設定失敗通知と配布プロンプトの詳細設計は別の調査で扱う。以下の「推奨」は実装済みを意味しない。

## 結論

**固定名の Windows 名前付き mutex を `ctypes` で `CreateMutexW` し、`ERROR_ALREADY_EXISTS` で二つ目の起動を判定する。** 名前には `Local\` を付け、同一 Windows セッションに閉じる。名前にはバージョン・配置パス・Python/EXE の区別を含めず、配布版と開発版で同じ値を使う。一次プロセスは mutex のハンドルを GUI の存続中保持し、終了時に `CloseHandle` する。OS は強制終了時もプロセスのハンドルを閉じ、最後のハンドルが閉じるとオブジェクトを破棄する。[CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw)・[名前空間](https://learn.microsoft.com/en-us/windows/win32/termserv/kernel-object-namespaces)・[CloseHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle)（各 2026-10-21 閲覧）。

**既存画面への復帰通知には別名の auto-reset 名前付き event を使う。** 一次プロセスが保持し、二次プロセスは `OpenEventW(EVENT_MODIFY_STATE)` → `SetEvent` → `CloseHandle` の順に通知して終了する。一次側は Tk の `root.after()` を適度な周期（例: 100～250 ms）で再登録し、その各回で `WaitForSingleObject(event, 0)` を呼ぶ。`0` は Win32 側の非ブロッキング待機時間であり、`root.after()` の周期ではない。復元と前面化は Tk メインスレッドで処理する。起動直後の「mutex はあるが event はまだない」競合には有限回の再試行と明示的な失敗通知を用意する。[CreateEventW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw)・[OpenEventW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-openeventw)・[SetEvent](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-setevent)・[WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject)（各 2026-10-21 閲覧）。

**新規 pip 依存は不要。** Python 標準ライブラリの `ctypes.WinDLL(..., use_last_error=True)` と `ctypes.wintypes` で `Kernel32.dll` / `User32.dll` を呼ぶ。既存の `requirements.txt` に起動制御用パッケージはなく、`pagefolio/__main__.py` では Tk root を作って直ちに `PDFEditorApp` と `mainloop()` を起動している。mutex 判定は root 作成より前に置く。[Python `ctypes`](https://docs.python.org/3/library/ctypes.html)（2026-10-21 閲覧）、リポジトリ内 `requirements.txt`・`pagefolio/__main__.py`（同日確認）。

## 推奨スタック

| 技術 | バージョン・配置 | 役割 | 採用理由・確信度 |
|---|---|---|---|
| `CreateMutexW` / `CloseHandle` | Windows 11 の Kernel32 API | セッション内で一次プロセスを一つにする | 作成・既存取得が一つの API 呼び出しで判定でき、ハンドルの寿命がプロセスに連動する。MEDIUM（公式仕様を複数ページで照合） |
| `Local\<固定製品ID>.Instance` | 製品単位の固定文字列。例は設計案であり未実装 | Python/EXE・版・配置をまたぐ判定名 | `Local\` はセッション名前空間を明示する。バージョンやパスを混ぜると要件に反する。MEDIUM（名前空間は公式仕様、製品名は設計判断） |
| `CreateEventW` / `OpenEventW` / `SetEvent` | 別名 `Local\<固定製品ID>.Activate` | 二次プロセスから一次プロセスへ復帰要求 | mutex は存在判定、event は通知と責務を分けられる。auto-reset は一度の待機で通知状態を消費する。MEDIUM |
| `WaitForSingleObject(event, 0)` + Tk `root.after()` | 既存 Tk メインスレッド | 通知を GUI スレッドで受ける | Win32 待機の 0 ms は直ちに戻る。`root.after()` は別途適度な間隔で再登録し、ビジーループを避ける。Tk/fitz のメインスレッド制約に合う。MEDIUM（Win32 は公式仕様、Tk 接続は既存構造からの推奨） |
| `ctypes.WinDLL`・`ctypes.wintypes` | Python 標準ライブラリ | Win32 API の型付き呼び出し | 新規依存を増やさず Python と PyInstaller EXE で同じ呼び出しにする。MEDIUM |
| `ShowWindow(SW_RESTORE)` / `SetForegroundWindow` | Windows 11 の User32 API | 最小化された既存画面の復元・前面化試行 | `SW_RESTORE` は復元用。前面化には OS の制約があり成功保証はない。MEDIUM |

### `ctypes` の型・エラー・ハンドル寿命

- `WinDLL("kernel32", use_last_error=True)` の各関数に `argtypes` と `restype` を明示する。`HANDLE` / `HWND` はポインタ幅の `wintypes.HANDLE` / `wintypes.HWND` を使い、既定の C `int` 戻り値に任せない。`LPCWSTR`、`DWORD`、`BOOL` も API 宣言に合わせる。64-bit Windows でのハンドル切り詰めを避ける。[Python `ctypes` の `restype`・`argtypes` と `wintypes.HANDLE`](https://docs.python.org/3/library/ctypes.html)（2026-10-21 閲覧）。
- `CreateMutexW` の戻り値が NULL なら失敗であり、「他の起動が存在」と混同しない。非 NULL の直後に `ctypes.get_last_error()` を読み、`ERROR_ALREADY_EXISTS` のときだけ二次起動とする。`use_last_error=True` と `get_last_error()` は対で使い、後続 API 呼び出しの後に読まない。[CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw)・[Python `ctypes`](https://docs.python.org/3/library/ctypes.html)（2026-10-21 閲覧）。
- mutex は `bInitialOwner=FALSE` として存在判定に用い、`ReleaseMutex` を使う所有権ロックにはしない。一次プロセスはハンドルを保持し、`mainloop()` から抜ける際の `finally` で閉じる。二次プロセスが取得した既存 mutex と event のハンドルも閉じる。強制終了時には OS がハンドルを閉じる。最後のハンドルがなくなるまでオブジェクトが残るため、二次プロセスも速やかに閉じる。[CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw)・[CloseHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle)（2026-10-21 閲覧）。
- mutex と event は**異なる名前**にする。Windows の名前付き mutex/event は同じ名前空間を共有し、他種オブジェクトと衝突すると `ERROR_INVALID_HANDLE` で失敗する。[CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw)・[CreateEventW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw)（2026-10-21 閲覧）。

### 画面復帰の限界

一次プロセスは event を受けたら、同じ Tk スレッドで既存ウィンドウを復元し、必要なら `ShowWindow(SW_RESTORE)`、`SetForegroundWindow` を試す。`ShowWindow` は表示状態を変えるが、`SetForegroundWindow` は呼び出し元と現在の前景プロセス、直近の入力、メニューなどの条件に制約され、条件を満たしても拒否され得る。二次側の `AllowSetForegroundWindow(primary_pid)` は一次 PID を安全に得られ、二次側に前面化権限がある場合の補助手段だが、権限移譲は一時的である。確実な前面化を要件・テストの断定条件にしない。拒否時には既存画面の復元状態を確認し、必要に応じてタスクバー通知を検討する。[ShowWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindow)・[SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow)・[AllowSetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-allowsetforegroundwindow)（各 2026-10-21 閲覧）。

`SetEvent` の成功は「通知状態にした」ことを意味するだけで、画面復帰完了の応答ではない。復帰成功を実機で検証する。短時間に複数の二次起動がある場合、event の通知は回数を保持しないが、画面復帰要求は同一操作として扱える。[SetEvent](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-setevent)（2026-10-21 閲覧）。

## 代替案と採用境界

| 代替案 | 今回採らない理由 | 採る条件 |
|---|---|---|
| PID ファイル・単なるロックファイル | 残骸や同時起動の競合、所有者の生存判定が必要になる | ユーザー単位の厳密な所有権・セキュリティ境界が要件になる場合 |
| `Global\` mutex | 複数 Windows セッションを横断して止めてしまい、今回の「同一セッションに一つ」と合わない | マシン全体で一つに変更する場合 |
| `pywin32` などの追加パッケージ | 必要な Win32 API は `ctypes` で呼べるため、新規依存と配布負担を増やす理由がない | Win32 API 面が大幅に広がり、型定義の保守負担が実測で増えた場合 |
| ウィンドウタイトルやプロセス名による探索だけで重複判定 | タイトルは変更可能で、起動途中にはウィンドウが存在しない | 対象画面を識別する補助用途に限る |

## 実装前に確定・検証する点

1. 固定製品 ID と mutex/event 名を一箇所で定義し、Python 実行、配布 EXE、別版、別配置で同じ名前を使う。過去版にこの制御はないため、制御未実装の旧版まで排他できるとは扱わない。
2. 一次プロセスの mutex 作成後、event 公開前に二次起動した場合の有限再試行、一次起動が Tk 作成中に失敗した場合の通知、API 権限エラー時の動作を明示する。エラーを「すでに起動中」に変換しない。
3. 同じ Windows セッション内での通常権限/管理者権限の混在、ユーザー切替・リモートデスクトップ、強制終了直後の再起動を Windows 11 実機で確かめる。名前付きオブジェクトの既定 ACL は作成者のトークン由来であり、権限差によるアクセス失敗を事前に保証できない。[CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw)（2026-10-21 閲覧）。
4. 固定名 mutex は同じ名前の先取りによる起動妨害が可能である、と Microsoft が注意している。今回の単一セッション運用では受け入れるか、セッション内の悪意ある別プロセスも脅威とみなすかをセキュリティ判断として残す。[CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw)（2026-10-21 閲覧）。

## 根拠の区分

| 区分 | 根拠 | 確信度 |
|---|---|---|
| 既存実装 | `pagefolio/__main__.py`: 起動時に Tk root と `PDFEditorApp` を生成。`requirements.txt`: 起動制御用依存なし。 | HIGH（2026-10-21 のリポジトリ直接確認） |
| OS・Python 仕様 | 上記の Microsoft Learn と Python 公式 `ctypes` 資料。 | MEDIUM（調査シーム `classify-confidence --provider websearch --verified` の判定。公式資料を相互照合） |
| 統合設計 | 固定名 mutex + 別名 event + Tk `after()` の組合せ、起動レース対策。 | MEDIUM（公式 API の組合せからの推奨。実機未検証） |

---
*PageFolio v1.10.0 起動制御スタック調査。アプリ実装は未変更。*
