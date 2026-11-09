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
