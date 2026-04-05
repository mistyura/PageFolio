# S01: テスト基盤 + ユーティリティ関数テスト

**Goal:** tests/ ディレクトリと conftest.py を作成し、GUI に依存しないユーティリティ関数のテストを整備する
**Demo:** After this: pytest tests/test_utils.py が全てパスする

## Tasks
- [x] **T01: テスト基盤を構築し、ユーティリティ関数35テストを作成（全パス）** — tests/ ディレクトリと tests/__init__.py を作成。conftest.py に tmp_path ベースの一時設定ファイルフィクスチャ、テスト用 PDF 生成フィクスチャを定義する。
  - Estimate: 10min
  - Files: tests/__init__.py, tests/conftest.py
  - Verify: python -c "import tests" && pytest --co tests/
- [x] **T02: 設定・テーマ・フォント関数のテストを作成済み（test_utils.py に含まれる）** — _load_settings, _save_settings, _get_settings_path のテスト。デフォルト値、ファイルなし、不正JSON、読み書き往復。_resolve_theme, _apply_theme のテスト。dark/light/system/不正値。_make_font のテスト。delta・最小値・ weight 。
  - Estimate: 20min
  - Files: tests/test_utils.py
  - Verify: pytest tests/test_utils.py -v
- [x] **T03: _parse_page_ranges テスト作成済み（test_utils.py に含まれる）** — PDFEditorApp._parse_page_ranges の単体テスト。正常系（単一ページ、範囲、複数範囲）、異常系（空文字列、範囲外、不正形式、逆範囲）。メソッドは self を使わないがインスタンス経由で呼ぶため、モックオブジェクトを作成してテストする。
  - Estimate: 15min
  - Files: tests/test_utils.py
  - Verify: pytest tests/test_utils.py -v -k parse_page_ranges
- [x] **T04: S01 検証: ruff + pytest グリーン確認完了** — リントチェックと全テスト実行でグリーン確認。
  - Estimate: 5min
  - Verify: ruff check . && ruff format --check . && pytest tests/test_utils.py -v
