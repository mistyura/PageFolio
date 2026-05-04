# Phase 1: 基盤と画像対応 - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

`requirements.txt` に直接依存のバージョンを固定してリポジトリに追加し、PNG/JPG/BMP/TIFF 等の画像ファイルを PDF と同様に開いて既存の全編集操作（回転・削除・結合・保存等）が使えるようにする。

</domain>

<decisions>
## Implementation Decisions

### requirements.txt の範囲（MAINT-02）

- **D-01:** 直接依存のみを含める — PyMuPDF, Pillow, tkinterdnd2, pyinstaller
- **D-02:** dev 依存も同じファイルに含める — pytest, pytest-cov, ruff
- **D-03:** pip freeze 由来の無関係パッケージ（altgraph, numpy, opencv-python, pikepdf, pytesseract 等）はすべて除外する
- **D-04:** 現在の `requirements.txt` は pip freeze 全出力になっているため、書き直してから git add する

### ファイルダイアログ・D&D（IMG-01）

- **D-05:** 対応拡張子: PNG/JPG/JPEG/BMP/TIFF/TIF（4形式6拡張子）
- **D-06:** 「開く」ダイアログのデフォルトフィルターは「サポートファイル (*.pdf;*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif)」。PDF のみ・画像のみ・すべてのファイルも追加エントリーとして並べる
- **D-07:** `_on_dnd_drop()` の `.pdf` 拡張子フィルターを、画像拡張子も含む共通定数（例: `SUPPORTED_EXTENSIONS`）に差し替える
- **D-08:** D&D で画像単体をドロップした時の挙動は PDF と同じ流れ — ドキュメントが開いていれば置換確認ダイアログ、なければそのまま開く

### 複数画像の同時開封（IMG-01）

- **D-09:** 複数の画像ファイルを選択または D&D した場合は、既存の複数 PDF と同じ流れ — `MergeOrderDialog` で順序確認後、全ページを結合した 1 ドキュメントとして開く
- **D-10:** PDF と画像が混在していても区別せず同じ `MergeOrderDialog` フローで扱う

### 上書き保存の挙動（IMG-01）

- **D-11:** `self.filepath` が画像拡張子（PNG/JPG 等）を持つ場合、Ctrl+S（上書き保存）は `_save_as()` にフォールスルーして「名前を付けて保存」ダイアログを自動起動する（PyMuPDF は画像形式での保存ができないため、常に PDF で出力）
- **D-12:** タイトルバー・ヘッダーの表示は現在の形式のまま変更なし（`[*] filename.png` のように表示される）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件定義
- `.planning/ROADMAP.md` §Phase 1 — Goal, Success Criteria（4 項目）
- `.planning/REQUIREMENTS.md` §IMG-01, §MAINT-02 — 要件の定義と受け入れ基準

### 変更対象ファイル（コアロジック）
- `pagefolio/file_ops.py` — `_open_file()`, `_open_pdf_path()`, `_save_file()`, `_save_as()` の変更箇所
- `pagefolio/app.py` — `_on_dnd_drop()`, `_on_dnd_enter()`, `_on_dnd_leave()` のファイルタイプ判定変更
- `pagefolio/file_drop.py` — D&D 登録ラッパー（変更不要の可能性が高いが確認要）

### UI・ダイアログ
- `pagefolio/dialogs.py` — `MergeOrderDialog`（複数ファイル結合順序確認ダイアログ。そのまま流用）

### 多言語対応
- `pagefolio/constants.py` — `LANG["ja"]` / `LANG["en"]` 辞書（新規ステータスメッセージ・ファイルタイプ文字列のキー追加が必要）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `FileOpsMixin._open_pdf_path(path)` — `fitz.open(path)` を呼ぶ既存関数。PyMuPDF は画像ファイルを直接 PDF として開けるため、この関数をそのまま流用できる（追加変換コード不要）
- `MergeOrderDialog` (`pagefolio/dialogs.py`) — 複数ファイルの結合順序確認ダイアログ。複数画像の同時開封でそのまま流用
- `FileOpsMixin._save_as()` — 「名前を付けて保存」ダイアログ。画像ファイル時の上書き保存フォールスルー先として使用

### Established Patterns

- **拡張子定数の一元管理:** `pagefolio/constants.py` に `SUPPORTED_EXTENSIONS` または `IMAGE_EXTENSIONS` を追加し、ダイアログフィルター・D&D フィルター・上書き保存判定の 3 箇所で同じ定数を参照することで保守性を確保する
- **ファイルタイプ文字列:** `LANG["ja"]` と `LANG["en"]` 両方に新規キーを追加する（`filetypes_supported`, `filetypes_image` など）
- **_open_pdf_path の使いまわし:** 既存のファイルオープンパイプライン（`fitz.open` → `_refresh_all()` → `fire_event("on_file_open")`）は画像ファイルに対しても変更なしで動作する

### Integration Points

- `_open_file()` の `filedialog.askopenfilenames()` の `filetypes` 引数を変更
- `_on_dnd_drop()` の `[p for p in raw_paths if p.lower().endswith(".pdf")]` フィルターを拡張
- `_save_file()` に `self.filepath` 拡張子チェックを追加（画像なら `_save_as()` にフォールスルー）

</code_context>

<specifics>
## Specific Ideas

- `fitz.open()` で画像を開くと単一ページ PDF として扱われる — 既存の全操作がそのまま動くはず
- `SUPPORTED_EXTENSIONS` は `{".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}` の set が実装しやすい
- `IMAGE_EXTENSIONS` も別途持ち、上書き保存判定（`_save_file()` のフォールスルー条件）に使う

</specifics>

<deferred>
## Deferred Ideas

None — 議論はフェーズスコープ内に留まった。

</deferred>

---

*Phase: 1-基盤と画像対応*
*Context gathered: 2026-05-04*
