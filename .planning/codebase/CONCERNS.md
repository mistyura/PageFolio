# コードベース課題一覧 (Concerns)

**分析日:** 2026-05-04

---

## 技術的負債

### [HIGH] Undo/Redo がPDF全体をメモリにコピーする

- **問題:** `pagefolio/file_ops.py` の `_save_undo()` は `self.doc.tobytes()` でPDF全体をバイト列にシリアライズし、最大20件スタックする
- **ファイル:** `pagefolio/file_ops.py:21-31`
- **影響:** 大きなPDFを編集すると操作ごとに数十〜数百MBのメモリが積み上がる。MAX_UNDO=20 × PDFサイズ分がピーク使用量の上限になる
- **修正方針:** ページ単位の差分保持（変更ページのバイト列のみキャッシュ）か、差分操作ログ方式（どのページを回転・削除したかの操作リストを記録）へ移行する

### [HIGH] `_refresh_all()` がサムネイル全件を再描画する

- **問題:** `pagefolio/viewer.py` の `_refresh_all()` は毎回 `_build_thumbnails()` を呼び、全ページのサムネイルウィジェット（Frame・Label）を破棄して再生成する
- **ファイル:** `pagefolio/viewer.py:127-143`, `pagefolio/viewer.py:167-175`
- **影響:** ページ数が増えると（100ページ以上）ページ移動・D&D・回転のたびにUIが詰まる。サムネイルキャッシュ（`thumb_cache`）は画像を保持するが、Tkウィジェットは毎回作り直している
- **修正方針:** 仮想スクロール化（表示範囲のウィジェットのみ生成）、またはウィジェットをプールしてキャッシュ済み画像のみ差し替える方式

### [MEDIUM] グローバル可変辞書 `C` によるテーマ管理

- **問題:** `pagefolio/constants.py:44` の `C = dict(THEMES["dark"])` はモジュールレベルのミュータブルグローバル辞書。`_apply_theme()` が `C.update(...)` でインプレース変更する
- **ファイル:** `pagefolio/constants.py:44`, `pagefolio/settings.py:79-82`
- **影響:** テストの独立性が低下する（あるテストがテーマ変更すると後続テストに影響）。`test_utils.py:TestApplyTheme` で手動ロールバックしている実態がある
- **修正方針:** `_apply_theme()` の戻り値で色辞書を返し、呼び出し元が保持する形にする。またはテーマ名を引数として各描画関数に渡すDI方式

### [MEDIUM] `_rebuild_ui()` が全ウィジェットを破棄して再構築する

- **問題:** テーマ・フォント変更時に `pagefolio/app.py:341-362` の `_rebuild_ui()` が `root.winfo_children()` を全破棄→再生成する
- **ファイル:** `pagefolio/app.py:341-362`
- **影響:** テーマ切替の応答が遅い（特にサムネイル多数時）。ウィジェット参照が一時的に無効になるためエラーが起きやすい。UIの状態（スクロール位置など）がリセットされる
- **修正方針:** `ttk.Style` はセッション中で再設定可能なため、スタイルのみ更新して背景色を直接変更する方式が現実的

### [LOW] `dialogs.py` にフォント生成の重複ロジック

- **問題:** `pagefolio/dialogs.py:254-258` の `PluginDialog._font()` と `dialogs.py:462-467` の `MergeOrderDialog._font()` が `app.py:269-274` の `PDFEditorApp._font()` と同一ロジックを持つ
- **ファイル:** `pagefolio/dialogs.py:254-258`, `pagefolio/dialogs.py:462-467`
- **影響:** フォント生成ロジックを変更するとき3か所を修正する必要がある
- **修正方針:** `pagefolio/settings.py` の `_make_font()` を共通関数として dialogs からも呼び出す

---

## パフォーマンス懸念

### [HIGH] プレビュー生成がメインスレッドをブロックする

- **問題:** `pagefolio/viewer.py:60-65` の `_show_preview()` で `page.get_pixmap()` をメインスレッドで呼ぶ。ズーム `1.5` 倍でレンダリングするため高解像度PDFでは数秒かかる場合がある
- **ファイル:** `pagefolio/viewer.py:61`
- **影響:** プレビュー更新中はTkinterのイベントループがブロックされ、UI全体が応答しなくなる
- **修正方針:** `threading.Thread` または `concurrent.futures.ThreadPoolExecutor` でバックグラウンドレンダリングし、完了後に `root.after()` でUI更新する。ページ切替を連続で行った場合のキャンセル機構も必要

### [HIGH] サムネイル生成も同様にメインスレッドをブロックする

- **問題:** `pagefolio/viewer.py:115-124` の `_get_thumb_photo()` が全ページ分同期で `get_pixmap()` を呼ぶ
- **ファイル:** `pagefolio/viewer.py:115-124`, `pagefolio/viewer.py:167-175`
- **影響:** 100ページのPDFを開くと全サムネイル生成が完了するまでUIがフリーズする
- **修正方針:** 遅延生成（`thumb_inner` のスクロールイベントを監視し、表示範囲のサムネイルのみ生成）とバックグラウンド事前生成の組み合わせ

### [MEDIUM] ポップアップビューア（`_show_page_popup`）がメインの `self.doc` を直接参照する

- **問題:** `pagefolio/viewer.py:273-279` の `render_page()` は `self.doc[popup_state["idx"]]` でメインドキュメントオブジェクトを参照する
- **ファイル:** `pagefolio/viewer.py:273`
- **影響:** ポップアップ表示中にメインウィンドウで別PDFを開くと、ポップアップが無効なページ参照で例外を起こす可能性がある。ドキュメントの競合アクセスが発生しうる
- **修正方針:** ポップアップ起動時にページのバイト列またはピクスマップをコピーするか、ポップアップ表示中はメイン側の操作をブロックする

### [LOW] D&Dゴーストが `Toplevel` を毎回生成・破棄する

- **問題:** `pagefolio/dnd.py:14-32` の `_dnd_start_ghost()` がドラッグ開始のたびに `tk.Toplevel` を生成する
- **ファイル:** `pagefolio/dnd.py:14-32`
- **影響:** ドラッグが多い場合にウィンドウ生成コストが蓄積するが、通常使用では問題にならない
- **修正方針:** ゴーストウィンドウを初期化時に1回だけ生成し、表示/非表示で制御する

---

## 既知の制限（CLAUDE.md 記載）

### [HIGH] 複数ページの一括トリミング未対応

- **現状:** `pagefolio/page_ops.py:173-222` のトリミングは `self.current_page` の1ページのみ対象
- **影響:** 選択ページをまとめてトリミングできない。ユーザーが複数ページに同じ余白カットを行う場合、1ページずつ手作業が必要
- **修正方針:** `_get_targets()` を活用して選択ページ全件にループ処理するよう拡張（ただし全ページに同一CropBoxを適用するのかページサイズ比率を使うかの設計が必要）

### [HIGH] D&Dによるページ移動が1ページずつ

- **現状:** `pagefolio/dnd.py:90-115` の `_dnd_drop()` は `self._dnd_src_idx`（単一インデックス）のみ移動する
- **影響:** 複数選択状態でもドラッグすると1ページしか移動しない。選択状態が視覚的に残るため混乱を招く可能性がある
- **修正方針:** `self.selected_pages` が空でない場合は選択ページ全件をまとめて移動する処理を実装する

### [MEDIUM] 暗号化PDFを開けない場合がある

- **現状:** `pagefolio/file_ops.py:132` の `fitz.open(path)` でパスワード付きPDFを開くと例外になる
- **影響:** エラーダイアログが表示されるが、パスワード入力の手段がない
- **修正方針:** `fitz.open()` で `fitz.PDF_ENCRYPT_*` を検知し、`simpledialog.askstring` でパスワードを入力させ、`fitz.open(path, password=pw)` で再試行する

### [LOW] CropBoxトリミングはメタデータ変更のみ

- **現状:** `page.set_cropbox()` で設定しても物理的なページサイズは変わらず、ビューア次第では全体が見える場合がある
- **ファイル:** `pagefolio/page_ops.py:207`
- **影響:** 「ページ内容を削除したつもり」のユーザーが実際には内容が残っていることに気づかない可能性がある
- **修正方針:** トリミング適用時に注記メッセージを表示する。完全な切り取りが必要な場合は `page.set_mediabox()` + コンテンツストリームの物理的クリッピングが必要

---

## セキュリティ

### [MEDIUM] プラグインが任意Pythonコードを実行できる

- **問題:** `pagefolio/plugins.py:118-128` の `load_plugin()` が `importlib.util.spec_from_file_location` → `exec_module()` で任意の `.py` ファイルを実行する
- **ファイル:** `pagefolio/plugins.py:118-128`
- **影響:** 悪意のあるプラグインファイルが `plugins/` ディレクトリに置かれた場合、システム上で任意コードが実行される。ファイルD&Dで複数ファイルを渡した場合も同様のリスク
- **現在の緩和:** `_` プレフィックスのファイルは除外、ロード失敗時は例外キャッチして `None` を返す
- **推奨対応:** ユーザー向けにプラグインが信頼済みソースからのみ配置されるよう警告UIを設ける。自動的なプラグインインストール機能は追加しない

### [LOW] `os.startfile()` のシェルインジェクション（リスク低）

- **問題:** `pagefolio/dialogs.py:413` の `os.startfile(plugins_dir)` はパス文字列をシェルに渡すが、パスは `_get_plugins_dir()` で生成された固定パスのため実際のリスクは低い
- **ファイル:** `pagefolio/dialogs.py:413`
- **影響:** ruff の S606 警告が発生しているが、`# noqa: S606` で抑制済み
- **現在の緩和:** noqa 抑制、パスはユーザー入力でなく固定生成

---

## テストカバレッジの不足

### [HIGH] UIコンポーネントのテストが皆無

- **問題:** `tests/` 配下にTkinterウィジェットを実際に生成・操作するテストが存在しない
- **テスト不足対象:**
  - `pagefolio/ui_builder.py` — `_build_ui()`, `_build_tools()`, `_build_styles()`
  - `pagefolio/viewer.py` — `_show_preview()`, `_build_thumbnails()`
  - `pagefolio/dnd.py` — D&D操作フロー全体
  - `pagefolio/dialogs.py` — 4ダイアログのすべての状態
- **影響:** UIの変更がサイレントバグを引き起こしても自動検知できない
- **修正方針:** `unittest.mock.patch` でTkオブジェクトをモック化するか、`pytest-tk` などのGUIテストライブラリを導入する

### [HIGH] モード切替ロジックの統合テストがない

- **問題:** 閲覧モード→編集モード切替（`_toggle_edit_mode`）に伴うボタン活性状態の変化をテストするケースがない
- **ファイル:** `pagefolio/app.py:198-215`
- **影響:** `_doc_buttons` と `_edit_only_buttons` の管理ミスがテストで検知されない
- **修正方針:** `PDFEditorApp` をヘッドレスで初期化してボタンリストの状態を検証するテストを追加する

### [MEDIUM] ファイル操作 Mixin のUIフロー部分がテスト対象外

- **問題:** `pagefolio/file_ops.py` の `_open_file()` / `_save_file()` / `_save_as()` はファイルダイアログを呼ぶため、ダイアログをモックしないとテストできない。現状のテストは fitz 直接操作のみ
- **ファイル:** `tests/test_pdf_ops.py` — アプリクラスのメソッドを一切呼んでいない
- **影響:** 上書き保存のフォールバックロジック（incremental失敗→tmpファイル経由）が実際にテストされていない
- **修正方針:** `unittest.mock.patch('tkinter.filedialog.askopenfilenames', ...)` でダイアログをモックし、`_open_file()` 〜 `_open_pdf_path()` の流れを統合テストする

### [MEDIUM] トリミング座標変換ロジックのテストがない

- **問題:** `pagefolio/page_ops.py:183-201` の「キャンバス座標→PDFポイント変換」ロジックが単体テストされていない
- **ファイル:** `pagefolio/page_ops.py:183-201`
- **影響:** ズーム倍率やオフセットが変わったときに変換が狂っても自動検知できない
- **修正方針:** `_crop_page()` の座標変換部分を抽出して純粋関数化し、境界値テストを追加する

---

## 保守性

### [MEDIUM] Mixin間の暗黙的な状態依存

- **問題:** `UIBuilderMixin`, `ViewerMixin`, `PageOpsMixin`, `DnDMixin`, `FileOpsMixin` がすべて `self.doc`, `self.current_page`, `self.selected_pages`, `self.thumb_cache`, `self.preview_canvas` などを共有する。どのMixinがどの属性を所有するかが明示されていない
- **ファイル:** `pagefolio/app.py:65-82`（初期化のみ `app.py` が担当）
- **影響:** 新しいMixinを追加するときに属性の衝突・依存関係が把握しにくい。IDEの補完が効かない（型アノテーションが不足）
- **修正方針:** `app.py:__init__` の状態変数に型アノテーションを追加する。長期的にはMixinから `PDFEditorApp` への引数注入パターンへの移行を検討する

### [MEDIUM] `constants.py` にLANG辞書が埋め込まれており肥大化している

- **問題:** `pagefolio/constants.py` は日英2言語のLANG辞書だけで約380行を占め、ファイル全体が471行ある
- **ファイル:** `pagefolio/constants.py:52-471`
- **影響:** 言語を追加する場合や翻訳を修正する場合に、Pythonコードとして管理する必要がある
- **修正方針:** LANG辞書を `pagefolio/i18n/ja.json`, `pagefolio/i18n/en.json` に分離し、`constants.py` で読み込む形にする（ただしexe化との互換性を要確認）

### [LOW] `_build_tools()` がUI構築と状態管理を混在させている

- **問題:** `pagefolio/ui_builder.py:344-533` の `_build_tools()` 内で `_doc_buttons` と `_edit_only_buttons` リストへの追加が行われる。UIの宣言的な構築とボタン状態管理のロジックが1メソッドに混在
- **ファイル:** `pagefolio/ui_builder.py:347-348`
- **影響:** ボタンを追加するときに状態管理リストへの登録を忘れやすい
- **修正方針:** ボタン生成のヘルパー `btn()` 関数（現状はローカル関数）を明示的なデコレータかビルダークラスに格上げする

---

## 依存関係リスク

### [MEDIUM] `tkinterdnd2` がオプション依存で機能が分岐する

- **問題:** `pagefolio/file_drop.py:6-11` でインポートを `try/except ImportError` でラップし、未インストール時はファイルD&Dを無効化するサイレント分岐がある
- **ファイル:** `pagefolio/file_drop.py:6-11`
- **影響:** ユーザーが `tkinterdnd2` を知らないままインストールすると、D&D機能が使えない状態で使い続ける。インストールガイドへの誘導がない
- **推奨対応:** 起動時またはD&D操作時に「D&D を有効にするには tkinterdnd2 が必要です」と案内するUIを追加する

### [MEDIUM] PyMuPDF (fitz) の破壊的バージョン変更リスク

- **問題:** `pymupdf` は内部APIが変更されることがある。現在 `v1.27.2.2` を使用しているが `requirements.txt` にバージョンが指定されていない（`requirements.txt` は `??` 状態でgitに未追加）
- **ファイル:** `requirements.txt`（未コミット）
- **影響:** `pip install` で最新版が入り、`fitz.Rect`, `page.get_pixmap()` 等のAPIが変わると動作不全になる
- **推奨対応:** `requirements.txt` に `PyMuPDF==1.27.2.2` のように固定バージョンを指定してコミットする

### [LOW] Windows専用API依存

- **問題:** `pagefolio/settings.py:58-68` の `_detect_system_theme()` が `winreg` を使用。`pagefolio/dialogs.py:413` が `os.startfile()` を使用（macOS/Linux では `xdg-open` フォールバックあり）
- **ファイル:** `pagefolio/settings.py:58`, `pagefolio/dialogs.py:413-417`
- **影響:** Windows以外のOSではシステムテーマ検出が機能しない（`dark` にフォールバック）。ただし対象OSがWindows 11のみのため実用上は問題なし
- **現在の緩和:** `xdg-open` フォールバックがあり、`winreg` 例外はキャッチ済み

---

## スケーリング上の限界

### [HIGH] 大きなPDFファイル（100ページ超）での操作性

- **問題:** 上記の「サムネイル全件再描画」「Undo全体コピー」「メインスレッドブロック」が組み合わさり、大規模PDFでは顕著に劣化する
- **症状:** 100ページのPDF開封後、ページ移動のたびに0.5〜数秒のUIフリーズが発生しうる
- **修正優先度:** パフォーマンス改善（バックグラウンドレンダリング + 仮想スクロール）が最優先

---

## 将来の改善候補（優先度付き）

| 優先度 | 項目 | 対応ファイル |
|--------|------|-------------|
| HIGH | バックグラウンドプレビュー生成（UIブロック解消） | `pagefolio/viewer.py` |
| HIGH | サムネイル仮想スクロール（大規模PDF対応） | `pagefolio/viewer.py` |
| HIGH | Undo差分方式への移行（メモリ削減） | `pagefolio/file_ops.py` |
| HIGH | 複数ページ一括D&D移動 | `pagefolio/dnd.py` |
| HIGH | UIテストの追加 | `tests/` |
| MEDIUM | 複数ページ一括トリミング | `pagefolio/page_ops.py` |
| MEDIUM | パスワード付きPDF対応 | `pagefolio/file_ops.py` |
| MEDIUM | `tkinterdnd2` 未インストール時の案内UI | `pagefolio/file_drop.py`, `pagefolio/ui_builder.py` |
| MEDIUM | `requirements.txt` のバージョン固定とコミット | `requirements.txt` |
| MEDIUM | LANG辞書のJSONファイル分離 | `pagefolio/constants.py` |
| LOW | フォント生成ロジックの共通化 | `pagefolio/dialogs.py`, `pagefolio/settings.py` |
| LOW | 型アノテーションの追加（Mixin間の属性依存を明示化） | `pagefolio/app.py` |

---

*課題分析日: 2026-05-04*
