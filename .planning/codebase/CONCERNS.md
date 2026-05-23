# CONCERNS.md
_Generated: 2026-05-23_
_Focus: concerns_

# Codebase Concerns

**Analysis Date:** 2026-05-23

---

## Tech Debt

**Undo スタックの非対称フォーマット:**
- Issue: Undo スタックは操作タイプ別の差分形式（`op` キー付き辞書）を使うが、Redo スタックは常に全体スナップショット（`pdf_bytes`）形式を使う。`_restore_state()` が 2 つのフォーマットを自動判別するディスパッチャとして機能しているが、将来の操作タイプ追加時にパスが増え続ける構造になっている。
- Files: `pagefolio/file_ops.py` (`_save_undo`, `_undo`, `_redo`, `_restore_state`)
- Impact: Redo スタックが全体バイト列を保持するため、大きな PDF では Redo 1 ステップごとにメモリ消費が増える。最大 20 ステップ × `self.doc.tobytes()` のバイト列が蓄積する。
- Fix approach: Redo スタックも差分形式に統一し、`_restore_state` のディスパッチャを整理する。
- Severity: **medium**

**`_do_merge_resize` の Undo が `_save_undo()` をバイパス:**
- Issue: `page_ops.py` の `_do_merge_resize` は `_save_undo()` ヘルパーを使わず、直接 `self._undo_stack.append({"pdf_bytes": ...})` している。MAX_UNDO チェックやスタイルが他の操作と一致しない。
- Files: `pagefolio/page_ops.py` (L402-L413)
- Impact: 将来 `_save_undo` のロジックを変更しても `_do_merge_resize` には反映されない。
- Fix approach: `_save_undo` にスナップショットモード（`op="snapshot"`）を追加し `_do_merge_resize` から呼ぶ形に統一する。
- Severity: **low**

**`constants.py` が 539 行の巨大定数ファイル:**
- Issue: `LANG` 辞書が日英 2 言語で約 400 行を占め、テーマ定義・バージョン・拡張子定数と同居している。
- Files: `pagefolio/constants.py`
- Impact: 言語キーの追加・変更時に全体を把握しにくい。新しい言語を追加する場合はさらに肥大化する。
- Fix approach: `LANG` 辞書を `pagefolio/i18n.py` に分離し、`constants.py` はテーマ・バージョン・拡張子のみを保持する。
- Severity: **low**

**`app.py` 内の `import` がメソッド内部にある:**
- Issue: `app.py` の `__init__` 内で `import pagefolio.settings as _settings_mod` を 2 箇所実行している（L45-46、L342-343）。メソッド内 import はトップレベルよりも IDE の解析が困難。
- Files: `pagefolio/app.py` (L45-46, L342-343)
- Impact: コードの可読性が低下する。
- Fix approach: トップレベルで `import pagefolio.settings as _settings_mod` に移動し、循環 import が発生しないか確認する。
- Severity: **low**

---

## Performance Bottlenecks

**プレビュー生成がページ切替ごとに `doc.tobytes()` を呼ぶ:**
- Problem: `viewer.py` の `_show_preview()` は毎回 `self.doc.tobytes()` でドキュメント全体をバイト列にシリアライズしてからワーカースレッドに渡す。大きな PDF（例: 100 ページ・高解像度画像入り）では数十 MB の直列化がメインスレッドで発生する。
- Files: `pagefolio/viewer.py` (L69)
- Cause: v1.0.1 バグ修正で `filepath` 経由のディスク再読込を廃止し、メモリシリアライズ方式に統一した（正しい決断）が、サイズコストが増した。
- Improvement path: ワーカースレッドへ渡す前に `tobytes()` が実際に必要かチェックし、最後のシリアライズ結果をキャッシュする（`_doc_bytes_cache` フィールド）。ドキュメントが変更されたときのみ再シリアライズする。
- Severity: **medium**

**`thumb_cache` のキャッシュサイズ上限がない:**
- Problem: `self.thumb_cache` 辞書はサイズ制限なく `ImageTk.PhotoImage` オブジェクトを蓄積する。数百ページの PDF を連続して操作すると大量の PIL 画像がメモリに残る。
- Files: `pagefolio/viewer.py` (`_get_thumb_photo`, L155-164)
- Cause: LRU 方式などのエビクション機構がない。
- Improvement path: `functools.lru_cache` ラッパーか、`collections.OrderedDict` を使った上限付き LRU キャッシュを実装する（上限例: 200 エントリ）。
- Severity: **medium**

**サムネイル生成がメインスレッドで `fitz.Matrix` 処理を行う:**
- Problem: `_get_thumb_photo()` は `self.doc[i].get_pixmap()` をメインスレッドで呼んでいる。`_build_thumbnails()` は `root.after_idle` / `root.after` でイベントループに分散させているが、各サムネイルの pixmap 生成はメインスレッドをブロックする。
- Files: `pagefolio/viewer.py` (L155-164, L219-235)
- Cause: `fitz.Document` はスレッドセーフでないため、プレビューのように完全なスレッド分離ができない。
- Improvement path: サムネイル生成前に `fitz.open(stream=doc.tobytes())` で独立したドキュメントコピーを作り、バックグラウンドスレッドで pixmap を生成してから `root.after` でメインスレッドに返す（プレビューと同様の方式）。
- Severity: **medium**

**ポップアップビューアが `self.doc` を直接参照:**
- Problem: `viewer.py` の `_show_page_popup()` の `render_page()` は `self.doc[popup_state["idx"]]` を直接参照し、メインスレッドで `get_pixmap()` を同期実行する。大きなページでは UI が固まる。
- Files: `pagefolio/viewer.py` (L340-375)
- Cause: ポップアップ用のバックグラウンドレンダリングが実装されていない。
- Improvement path: `_show_preview()` と同様にバックグラウンドスレッドに移行する。
- Severity: **low**

---

## Known Limitations

**`set_cropbox` は物理サイズを変えない:**
- Issue: トリミング操作は `fitz.Page.set_cropbox()` で CropBox メタデータのみを変更する。MediaBox（実際の PDF ページサイズ）は変わらない。トリミング後の PDF を他のソフトウェアで開くと余白データが復元される場合がある。
- Files: `pagefolio/page_ops.py` (`_crop_page`)
- Workaround: 「縮小して保存」を使うと `garbage=4, clean=1` が MediaBox 外コンテンツを除去する場合があるが、完全ではない。
- Severity: **medium**

**暗号化・パスワード保護 PDF は開けない:**
- Issue: `fitz.open()` は暗号化 PDF に対してエラーを返すが、アプリ側でのパスワード入力 UI が存在しない。エラーダイアログ（汎用 `messagebox.showerror`）のみが表示される。
- Files: `pagefolio/file_ops.py` (`_open_pdf_path`, L213-241)
- Fix approach: `fitz.Document.needs_pass` を確認し、`simpledialog.askstring` でパスワードを取得して `doc.authenticate(password)` を試行する処理を追加する。
- Severity: **medium**

**`tkinterdnd2` はオプション依存（ファイル D&D が無効化される）:**
- Issue: `file_drop.py` は `tkinterdnd2` の `ImportError` をサイレントにキャッチし、ファイルドラッグ＆ドロップ機能を無効化する。`TkinterDnD.Tk` の代わりに標準 `tk.Tk` で起動した場合も機能が動かない。
- Files: `pagefolio/file_drop.py` (L6-11), `pagefolio/__main__.py`
- Impact: インストール手順の不備でユーザーがサイレントに機能喪失する。
- Fix approach: 起動時に `tkinterdnd2` の利用可否をステータスバーに表示するか、`README.md` に明記する。
- Severity: **low**

**複数選択時のトリミングは現在ページの cropbox 比率を全ページに適用:**
- Issue: 異なるサイズのページが混在する PDF で一括トリミングを実行すると、現在ページの cropbox 比率で全ページに適用される。ページによっては意図しない範囲がトリミングされる可能性がある。
- Files: `pagefolio/page_ops.py` (`_crop_page`, L222-268)
- Severity: **low**

---

## Error Handling Gaps

**ページ結合・リサイズ (`_do_merge_resize`) のエラーが汎用ダイアログ:**
- Issue: `show_pdf_page()` の失敗（例: 破損ページ）は `except Exception as e: messagebox.showerror(...)` のみで処理される。Undo スタックはすでにスナップショットを push 済みなので、失敗後に Undo すれば復元できるが、ユーザーへの案内はない。
- Files: `pagefolio/page_ops.py` (L413-457)
- Fix approach: 例外発生時に「操作に失敗しました。Undo で元に戻せます」などの案内メッセージを追加する。
- Severity: **low**

**`_do_insert` が Undo スタックを先に push する:**
- Issue: `_do_insert` は処理前に `_save_undo("insert", ...)` を呼んでから実際の挿入を試みる。挿入が失敗した場合、Undo スタックに無効な状態が残る可能性がある。（`_undo_stack[-1]["data"][1] = total` で事後補正しているが、例外時は補正されない）
- Files: `pagefolio/page_ops.py` (`_do_insert`, L332-360)
- Fix approach: 挿入が完全に成功してから `_save_undo` を呼ぶ順序に変更する。
- Severity: **medium**

**`_save_file` の incremental 保存失敗 → tmp ファイル保存も失敗した場合:**
- Issue: `_save_file` は incremental 保存失敗時に `.tmp` ファイル経由で保存するフォールバックがあるが、フォールバック自体が失敗した場合も `except Exception as e: messagebox.showerror(...)` が呼ばれるだけで、`.tmp` ファイルが残存する可能性がある。
- Files: `pagefolio/file_ops.py` (L260-278)
- Fix approach: 外側の `except` 内で `os.remove(tmp)` を試みるクリーンアップ処理を追加する。
- Severity: **low**

---

## Security Considerations

**プラグインシステムは任意コードを実行する:**
- Risk: `plugins/` ディレクトリ内の任意の `.py` ファイルが `importlib.util.spec_from_file_location()` + `spec.loader.exec_module()` で実行される。悪意あるプラグインファイルを配置されると、アプリの権限でシステムコードが実行される。
- Files: `pagefolio/plugins.py` (`load_plugin`, L114-148)
- Current mitigation: `discover_plugins` は `_` で始まるファイルをスキップするが、それ以外の制限はない。
- Recommendations: (1) プラグインファイルのハッシュ検証、または (2) アプリ初回起動時にプラグインの存在を確認するプロンプトを表示する。現時点ではローカルツールとしての用途なので優先度は低いが、将来の exe 配布では注意が必要。
- Severity: **medium**

**ファイルパスがサニタイズされずに直接 `fitz.open()` に渡される:**
- Risk: D&D や `filedialog` 経由のパスは基本的に OS が提供するため安全だが、`os.path.splitext(p)[1].lower()` による拡張子チェックのみで内容検証がない。実際には `fitz.open()` が不正ファイルに対して例外を投げるため大きなリスクではない。
- Files: `pagefolio/app.py` (`_on_dnd_drop`, L164-169), `pagefolio/file_ops.py`
- Current mitigation: `fitz.open()` の例外を `messagebox.showerror` で受け取っている。
- Severity: **low**

---

## Test Coverage Gaps

**UI 層（Tkinter コンポーネント）にテストがない:**
- What's not tested: `UIBuilderMixin` (`ui_builder.py`)、`DnDMixin` (`dnd.py`)、`ViewerMixin` (`viewer.py`) のレンダリングパス、各ダイアログクラス (`dialogs.py`) の表示・インタラクション。
- Files: `pagefolio/ui_builder.py`, `pagefolio/viewer.py`, `pagefolio/dnd.py`, `pagefolio/dialogs.py`
- Risk: UI レイアウト変更やスタイル適用のバグが自動検出されない。
- Priority: Low — Tkinter のテストは headless 環境で困難なため、手動確認が現実的。

**`FileOpsMixin` の `_open_file` / `_save_file` / `_close_file` にモックテストがない:**
- What's not tested: `filedialog.askopenfilenames` / `filedialog.asksaveasfilename` のモックによるファイル操作フローのテスト。
- Files: `pagefolio/file_ops.py`
- Risk: ファイル選択ダイアログのキャンセル処理や複数ファイル選択時のフロー変更でリグレッションが起きても検出されない。
- Priority: Medium — `unittest.mock.patch` でモック可能。

**バックグラウンドレンダリング (`_show_preview` のスレッド処理) にテストがない:**
- What's not tested: プレビュー世代カウンター (`_preview_gen`) による stale 破棄の動作、スレッドレースコンディション。
- Files: `pagefolio/viewer.py` (L65-127)
- Risk: スレッド競合によるクラッシュが再現困難で気づきにくい。
- Priority: Medium — 世代カウンターのロジック部分は単体テスト可能。

**`_do_insert` の Undo スタック事後補正 (`_undo_stack[-1]["data"][1] = total`) がテストされていない:**
- What's not tested: 挿入失敗時の Undo スタック状態。
- Files: `pagefolio/page_ops.py` (L344)
- Risk: 挿入失敗後に Undo を実行した場合、`total=0` のまま存在するエントリが `delete_page` を 0 回実行して正常に終了するように見えるが、スタックに残り続ける。
- Priority: Low

---

## Scaling Limits

**大規模 PDF での Undo スタックメモリ消費:**
- Current capacity: Undo は最大 20 ステップ。削除操作の差分は削除ページのバイト列（`tmp.tobytes()`）を保存する。
- Limit: 100 ページ × 1MB/page の PDF で delete 20 回実行すると、Undo スタックだけで理論上最大 2GB 消費する（実際は削除対象が少ない場合は低い）。
- Scaling path: `MAX_UNDO` の設定画面での変更機能を追加する、または Undo スタック全体のバイト上限を設ける。
- Files: `pagefolio/file_ops.py` (L59), `pagefolio/app.py` (L30)
- Severity: **medium**

**サムネイルキャッシュのページ数上限なし:**
- Current capacity: `thumb_cache` 辞書は無制限。
- Limit: 500 ページ PDF × (サムネイル約 80×113px RGB) ≒ 約 13MB — 許容範囲だが、高解像度 PDF では倍増する。
- Scaling path: 前述のとおり LRU キャッシュ（上限 200 エントリ等）を実装する。
- Files: `pagefolio/viewer.py` (`_get_thumb_photo`)
- Severity: **medium**

---

## Dependencies at Risk

**`pymupdf` (fitz) の API 変更:**
- Risk: `fitz.Page.set_rotation`、`set_cropbox`、`show_pdf_page` 等の API は PyMuPDF のバージョンごとにシグネチャが変わることがある。`requirements.txt` にバージョンを固定済みだが、将来のアップグレードで動作が変わる可能性がある。
- Impact: PDF 操作の全機能に影響する。
- Migration plan: `pytest` のテストスイートが fitz API の動作を直接検証しているため、アップグレード時はテストで検出可能。
- Severity: **low**

**`tkinterdnd2` が Windows 専用ライブラリ:**
- Risk: `tkinterdnd2` は Windows・macOS・Linux 各プラットフォームで動作するが、アクティブなメンテナンス状況が限定的。
- Impact: ファイルドラッグ＆ドロップ機能。
- Migration plan: オプション依存として扱われているため、機能喪失はサイレントにスキップされる（現在の設計のまま）。
- Severity: **low**

**`Segoe UI` フォントが Windows 固有:**
- Risk: `app.py` の `_font()` と `settings.py` の `_make_font()` が "Segoe UI" をハードコードしている。macOS / Linux では代替フォントが自動適用されるが、レイアウト崩れが起きる可能性がある。
- Files: `pagefolio/app.py` (L282-283), `pagefolio/settings.py` (L87-90), `pagefolio/ui_builder.py`
- Impact: 現在は Windows 11 専用ツールとして設計されているため実害なし。クロスプラットフォーム対応時に影響する。
- Severity: **low**

---

## Missing Critical Features

**パスワード保護 PDF の解除 UI:**
- Problem: 暗号化 PDF はエラーダイアログのみで開けない。`CLAUDE.md` の「今後の追加予定機能」にも記載されている。
- Blocks: パスワード付き PDF の全編集操作。

**回転状態のプレビュー即時反映:**
- Problem: CLAUDE.md の TODO 項目。回転操作後にプレビューが更新されるまでわずかなラグがある（バックグラウンドスレッド処理のため）。回転直後のサムネイルが古い状態を一瞬表示することがある。
- Files: `pagefolio/viewer.py` (`_build_thumbnails`, `_show_preview`)
- Blocks: ユーザー体験の向上。

---

*Concerns audit: 2026-05-23*
