# Technical Concerns

**Analysis Date:** 2026-06-01

## Known Issues

**ページ回転状態のプレビュー即時反映未対応:**
- Issue: 回転操作後、プレビューは `_refresh_all()` 経由で更新されるが、CLAUDE.md に「ページの回転状態をプレビューに即時反映」が未完了タスクとして明記されている
- Files: `pagefolio/viewer.py`, `pagefolio/page_ops.py`
- Impact: 回転操作後のプレビュー表示に遅延または不整合が生じる可能性がある

**暗号化PDF非対応:**
- Issue: パスワード保護 PDF の開封および解除機能が未実装
- Files: `pagefolio/file_ops.py` (`_open_pdf_path`)
- Impact: パスワード付き PDF を開こうとすると fitz の例外が発生し、エラーダイアログが表示されるだけ

**Undo/Redo 非対称設計:**
- Issue: Undo スタックは操作別差分方式（`op` キー付き辞書）だが、Redo スタックは全体バイト方式（`pdf_bytes`）のまま。`_undo()` 実行時に `doc.tobytes()` でフルシリアライズが走る
- Files: `pagefolio/file_ops.py` (lines 63–93)
- Impact: 大きな PDF で Undo を実行するたびにメモリとシリアライズ処理が重くなる

**insert Undo の挿入ページ数が常に 0:**
- Issue: `_save_undo("insert", ...)` で `state["data"] = [insert_at, 0]` と記録しているが、実際の挿入ページ数は後から入力されておらず `0` のまま。`_restore_state` で `for _ in range(0)` となるため、insert 操作の Undo が実質的に何もしない
- Files: `pagefolio/file_ops.py` (line 51), `pagefolio/file_ops.py` (line 121–123)
- Impact: ページ挿入操作を Undo しても元に戻らない

## Technical Debt

**dialogs.py の肥大化:**
- Issue: `pagefolio/dialogs.py` は 1,191 行に達し、5つの異なるダイアログクラス（`AboutDialog`, `SettingsDialog`, `PluginDialog`, `MergeOrderDialog`, `MergeResizeDialog`, `LLMConfigDialog`）が一つのファイルに詰め込まれている
- Files: `pagefolio/dialogs.py`
- Fix approach: ダイアログごとにモジュール分割する（例: `dialogs/settings.py`, `dialogs/ocr.py` など）

**constants.py の肥大化:**
- Issue: `pagefolio/constants.py` は 711 行に達し、THEMES・C・LANG（ja/en 両方）・APP_VERSION・ファイル拡張子定数がすべて混在している
- Files: `pagefolio/constants.py`
- Fix approach: `lang.py`（LANG辞書）と `themes.py`（THEMES/C）に分割し、constants.py はバージョン・定数のみにする

**Mixin 多重継承による型解析困難:**
- Issue: `PDFEditorApp` が `UIBuilderMixin, FileOpsMixin, PageOpsMixin, ViewerMixin, DnDMixin, OCRMixin` の6クラスを多重継承。各 Mixin が `self.doc`, `self.current_page` 等を直接参照するが、型チェッカーから見ると未定義属性になる
- Files: `pagefolio/app.py` (line 30–32)
- Impact: IDE の補完・静的解析が効きにくい。新規 Mixin 追加時に属性の存在を保証する仕組みがない

**settings モジュールのモジュールレベル副作用:**
- Issue: `app.py` が `import pagefolio.settings as _settings_mod` してから `_settings_mod._current_font_size` を直接書き換えるパターンを使用している。プライベート変数をモジュール外部から操作している
- Files: `pagefolio/app.py` (lines 48–50), `pagefolio/settings.py`
- Fix approach: `set_current_font_size(size)` のような公開関数を追加する

**プラグイン API バージョン管理なし:**
- Issue: `PDFEditorPlugin` 基底クラスにバージョン検証や互換性チェックがない。アプリのバージョンが上がってもプラグインの `on_*` メソッドシグネチャ変更が検知されない
- Files: `pagefolio/plugins.py`
- Fix approach: プラグインに `api_version` 属性を追加し、`load_plugin` 時に互換性を確認する

## Performance Concerns

**プレビュー生成時の毎回フルシリアライズ:**
- Problem: `_show_preview()` が呼ばれるたびに `self.doc.tobytes()` でドキュメント全体をバイト列に変換してバックグラウンドスレッドに渡している
- Files: `pagefolio/viewer.py` (line 69)
- Cause: スレッドに fitz.Document を渡せないため（スレッドセーフでない）のやむを得ない設計だが、数十MB の PDF では毎回シリアライズコストが高い
- Improvement path: ページ単位で `page.get_pixmap()` を呼ぶ方式に変更するか、fitz.Document のページバイトをキャッシュする

**サムネイル生成のスケールがハードコード:**
- Problem: サムネイル生成に `fitz.Matrix(0.22, 0.22)` が固定値で使われている
- Files: `pagefolio/viewer.py`
- Cause: 定数として分離されておらず、変更時に影響範囲が不明瞭
- Improvement path: `constants.py` の定数に移動して調整しやすくする

**Undo スタックの先頭要素削除（O(n) 操作）:**
- Problem: `_undo_stack.pop(0)` で先頭から要素を削除している。Python のリストは先頭削除が O(n)
- Files: `pagefolio/file_ops.py` (line 60)
- Improvement path: `collections.deque(maxlen=MAX_UNDO)` に変更する

## Security Considerations

**OCR URL の任意スキーム許可:**
- Risk: `ocr.py` の `urllib.request.Request` に `# noqa: S310` を付与して Ruff の任意スキーム警告を抑止している。ユーザーが悪意ある URL を設定した場合、`file://` 等のスキームでローカルファイルにアクセスされる可能性がある
- Files: `pagefolio/ocr.py` (lines 105, 112, 245, 247)
- Current mitigation: ユーザーが自分で URL を設定する前提（ローカル LM Studio のみ想定）
- Recommendations: URL を `http://` または `https://` で始まるものに限定するバリデーションを追加する

**プラグインによる任意コード実行:**
- Risk: `plugins/` ディレクトリに置かれた `.py` ファイルは `importlib` で無検証に実行される
- Files: `pagefolio/plugins.py` (`load_plugin` メソッド)
- Current mitigation: ユーザーが自分でプラグインを配置する運用前提
- Recommendations: プラグイン実行時の警告ダイアログ、またはハッシュ検証の追加を検討

**プラグインディレクトリのパス探索:**
- Risk: `_get_plugins_dir()` は frozen 実行時に `sys.executable` の親ディレクトリを起点とするため、インストール先によってはシステムディレクトリを指す可能性がある
- Files: `pagefolio/plugins.py` (lines 16–24)

## Scalability Limits

**Undo スタック上限 20 件:**
- Current capacity: `MAX_UNDO = 20`（`pagefolio/app.py` line 33）
- Limit: 削除・挿入の Undo は各ページのバイト列を保持するため、20ページ削除 Undo を保持すると大きなメモリを消費する可能性がある
- Scaling path: ページバイト列を一時ファイルにオフロードするか、上限を設定ファイルで変更可能にする

**大規模 PDF でのサムネイル生成:**
- Current capacity: プログレッシブローディング（`after_idle`）で対応済みだが、100ページを超える PDF でサムネイル全件をキャッシュするとメモリが増大する
- Files: `pagefolio/viewer.py` (`_build_thumbnails`)
- Scaling path: 表示中のビューポート付近のページのみキャッシュする仮想化方式を検討

**設定ファイルのスキーマ管理なし:**
- Current capacity: `pagefolio_settings.json` にキーを追加するだけで設定が増加する。削除されたキーが残留してもエラーにならない
- Files: `pagefolio/settings.py` (`_load_settings`)
- Scaling path: スキーマバージョンを追加し、不要キーの自動クリーンアップを実装する

## Missing Features / TODOs

CLAUDE.md「今後の追加予定機能」より:

- **ページ回転状態のプレビュー即時反映** — 回転後のプレビュー表示に不整合が生じる可能性あり。`pagefolio/viewer.py`, `pagefolio/page_ops.py` が対象
- **PDF パスワード解除対応** — `fitz.Document.authenticate()` を使った解除フローが未実装。`pagefolio/file_ops.py` (`_open_pdf_path`) が対象
- **印刷機能** — 現在は未実装。Windows の `os.startfile` + 印刷動詞での実装が候補

コード内 TODO コメントは grep で検出されず（0件）。

## Dependencies Health

**tkinterdnd2（ファイル D&D）:**
- Risk: `pagefolio/file_drop.py` は `tkinterdnd2` を try/import してサイレントスキップする設計。未インストールの場合ファイル D&D が無効になるが、ユーザーへの明示的な通知がない
- Files: `pagefolio/file_drop.py`
- Impact: インストール漏れ時にサイレントに機能が無効化される

**PyMuPDF (fitz) の API 依存:**
- Risk: `fitz.Matrix`, `fitz.Rect`, `fitz.Page.set_cropbox`, `fitz.Document.select` など多数の fitz API を直接使用。fitz のメジャーバージョンアップで API 変更が生じた場合の影響範囲が広い
- Files: `pagefolio/page_ops.py`, `pagefolio/viewer.py`, `pagefolio/file_ops.py`, `pagefolio/ocr.py`
- Impact: fitz のバージョン固定（`requirements.txt`）は v1.0.0 で実施済みだが、上流の破壊的変更リスクは残る

**OCR 機能が LM Studio 専用:**
- Risk: OCR は LM Studio の OpenAI 互換 API のみ対応。他のローカル LLM サーバー（Ollama 等）や クラウド API（OpenAI, Azure）への移行・拡張が難しい設計
- Files: `pagefolio/ocr.py`, `pagefolio/ocr_dialog.py`
- Impact: LM Studio 以外の環境では OCR 機能が使えない

---

*Concerns audit: 2026-06-01*
