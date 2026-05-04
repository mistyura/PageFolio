# S01: 基盤と画像対応

**Goal:** requirements.txt を直接依存のみに整理し、PNG/JPG/BMP/TIFF ファイルを PDF と同様に開いて既存の全編集操作が使える状態にする
**Demo:** requirements.txt 固定済み、PNG/JPG/BMP/TIFF ファイルを開いて既存の全編集操作が使える

## Must-Haves

- 1. requirements.txt が直接依存のみ（PyMuPDF, Pillow, tkinterdnd2, pyinstaller, pytest, pytest-cov, ruff）を含む\n2. PNG/JPG/JPEG/BMP/TIFF/TIF ファイルをファイルダイアログ・D&D どちらでも開ける\n3. 画像ファイルで Ctrl+S すると _save_as() にフォールスルーし PDF 保存ダイアログが開く\n4. ruff check && ruff format が通る\n5. pytest が全件パスする

## Integration Closure

constants.py の SUPPORTED_EXTENSIONS / IMAGE_EXTENSIONS を file_ops.py と app.py の 3 箇所（ダイアログフィルター・D&D フィルター・保存フォールスルー）で共有参照し、LANG 辞書経由で UI テキストを管理する

## Verification

- Run the task and slice verification checks for this slice.

## Tasks

- [ ] **T01: requirements.txt 整備** `est:10m`
  現在の pip freeze 全出力を直接依存のみに書き直す。PyMuPDF, Pillow, tkinterdnd2, pyinstaller（実行依存）と pytest, pytest-cov, ruff（dev 依存）をバージョン固定で記載する。無関係パッケージ（altgraph, numpy 等）はすべて除外する（D-01〜D-04）。
  - Files: `requirements.txt`
  - Verify: cat requirements.txt でエントリー数が 7 以下であることを確認

- [ ] **T02: constants.py 拡張子定数・LANG キー追加** `est:20m`
  pagefolio/constants.py に SUPPORTED_EXTENSIONS と IMAGE_EXTENSIONS の 2 定数を追加する（D-05）。LANG['ja'] と LANG['en'] 両方に新規キー filetypes_supported / filetypes_image / status_opened_image / status_image_save_as を追加し、既存キー dnd_drop_hint / dnd_pdf_only / dlg_insert_title の値を UI-SPEC の Copywriting Contract に従い更新する。
  - Files: `pagefolio/constants.py`
  - Verify: python -c "from pagefolio.constants import SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS, LANG; assert '.png' in SUPPORTED_EXTENSIONS; assert 'filetypes_supported' in LANG['ja']" が通る。ruff check pagefolio/constants.py がクリーン

- [ ] **T03: file_ops.py ファイルダイアログ・保存フロー変更** `est:30m`
  _open_file() の filetypes を UI-SPEC の 4 エントリーに変更（D-06）。挿入ダイアログの filetypes も同様に変更。_save_file() に IMAGE_EXTENSIONS チェックを追加し _save_as() フォールスルーを実装（D-11）。単体画像オープン後に status_opened_image を表示する。
  - Files: `pagefolio/file_ops.py`
  - Verify: ruff check pagefolio/file_ops.py がクリーン。python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read())" が通る

- [ ] **T04: app.py D&D フィルター拡張** `est:20m`
  _on_dnd_drop() の '.pdf' ハードコードフィルターを SUPPORTED_EXTENSIONS 定数参照に差し替える（D-07, D-08）。
  - Files: `pagefolio/app.py`
  - Verify: ruff check pagefolio/app.py がクリーン。python -c "import ast; ast.parse(open('pagefolio/app.py', encoding='utf-8').read())" が通る

- [ ] **T05: リント・テスト・受け入れ確認** `est:15m`
  全 py ファイルに対して ruff check && ruff format を実行し警告ゼロを確認する。pytest を実行し全テストがパスすることを確認する。
  - Verify: ruff check . && ruff format . の出力にエラーなし。pytest の出力に FAILED がゼロ

## Files Likely Touched

- requirements.txt
- pagefolio/constants.py
- pagefolio/file_ops.py
- pagefolio/app.py
