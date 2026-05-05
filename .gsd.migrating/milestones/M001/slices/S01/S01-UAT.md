# S01: 基盤と画像対応 — UAT

**Milestone:** M001
**Written:** 2026-05-04T04:04:26.541Z

# S01: 基盤と画像対応 — UAT

**Milestone:** M001
**Written:** 2026-05-04

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: 本スライスはファイル開封フロー・保存フォールスルー・D&D フィルターの変更であり、pytest による自動テスト108件と ruff によるリント確認で機能契約を十分に検証できる。GUI 起動なしでコアロジックを確認可能。

## Preconditions

- Python 環境に PyMuPDF, Pillow, tkinterdnd2 がインストール済みであること
- `pagefolio/` パッケージがインポート可能であること
- テスト用 PDF および PNG/JPG ファイルが用意可能であること

## Smoke Test

```
python -c "from pagefolio.constants import SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS; print(SUPPORTED_EXTENSIONS)"
```
→ `frozenset({'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'})` が出力されれば基本動作OK。

## Test Cases

### 1. requirements.txt エントリー数確認

1. `grep -c '==' requirements.txt` を実行する
2. **Expected:** 出力が `7` である

### 2. 定数インポートと内容確認

1. `python -c "from pagefolio.constants import SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS, LANG; assert '.png' in SUPPORTED_EXTENSIONS; assert '.pdf' in SUPPORTED_EXTENSIONS; assert '.bmp' in IMAGE_EXTENSIONS; assert 'filetypes_supported' in LANG['ja']; assert 'status_opened_image' in LANG['en']; print('OK')"` を実行する
2. **Expected:** `OK` が出力される

### 3. file_ops.py 構文確認

1. `python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read())"` を実行する
2. **Expected:** エラーなく完了する

### 4. app.py D&D フィルター確認

1. `python -c "import ast; ast.parse(open('pagefolio/app.py', encoding='utf-8').read())"` を実行する
2. **Expected:** エラーなく完了する

### 5. 全テストスイート実行

1. `pytest` を実行する
2. **Expected:** 108 passed、FAILED ゼロ

### 6. リント確認

1. `ruff check . && ruff format .` を実行する
2. **Expected:** All checks passed / N files left unchanged（エラーなし）

## Edge Cases

### 画像拡張子の大文字小文字

1. `python -c "from pagefolio.constants import SUPPORTED_EXTENSIONS; print('.PNG'.lower() in SUPPORTED_EXTENSIONS)"` を実行する
2. **Expected:** `True` が出力される（拡張子は小文字で格納されているため、比較時に lower() が必要）

### 保存フォールスルーロジック確認

1. `python -c "from pagefolio.constants import IMAGE_EXTENSIONS; assert '.png' in IMAGE_EXTENSIONS; assert '.pdf' not in IMAGE_EXTENSIONS; print('OK')"` を実行する
2. **Expected:** `OK` が出力される（PDF は IMAGE_EXTENSIONS に含まれないため通常保存される）

## Failure Signals

- `pytest` に FAILED が1件でも出る場合 → テスト回帰が発生している
- `ruff check .` にエラーが出る場合 → コーディング規約違反
- `import pagefolio.constants` で ImportError が出る場合 → 定数定義に構文エラー

## Not Proven By This UAT

- GUI 上での実際のファイルダイアログ動作（ファイルタイプフィルターの表示確認）
- 実際の PNG/JPG ファイルを開いてサムネイル・プレビューが正しく描画されること
- D&D で画像ファイルをドロップした際の実際の UI 動作
- 画像ファイルを開いた後に Ctrl+S で _save_as() ダイアログが開くことの実動作確認
- Windows 11 実機での tkinterdnd2 ドロップイベント受信確認

## Notes for Tester

- GUI テストは `python pagefolio.py` で起動し、PNG/JPG ファイルをドラッグ&ドロップまたはファイルメニューから開いて手動確認が必要
- 保存フォールスルーは画像ファイルを開いた状態で Ctrl+S を押し、PDF 保存ダイアログが開くことで確認できる
- ステータスバーに「画像として開きました」等の status_opened_image メッセージが表示されることを確認すること
