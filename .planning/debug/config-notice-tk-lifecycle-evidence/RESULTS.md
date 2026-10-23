# 設定通知テストの Tk ライフサイクル調査（2026-10-24）

## 初回失敗

- 元ログ: `.planning/phases/06-release-validation/06-reviews-pytest-native.txt`（原本は保持）。native 単一プロセス全件は `1795 passed, 2 failed, 2 warnings in 269.56s`。
- `test_real_rebuild_restores_same_notice_in_current_language`: `TkinterDnD.Tk()` の `package require tkdnd` が `can't find package tkdnd` を返し、`Unable to load tkdnd library.` で失敗。
- `test_corrupt_settings_show_one_real_toast_and_keep_pdf_editable`: PDF回転後のプレビューで `image "pyimage9" does not exist`。

## 原因の切り分け

- 対象2件のみは `2 passed`、設定通知ファイルは `143 passed`、全件冒頭の3ファイルは `174 passed`。常時失敗ではない。
- `tkinterdnd2/TkinterDnD.py` の `Tk.__init__` は Tk root を生成してから `_require(self)` を呼ぶ。後者が例外を投げた時、生成済みrootを破棄しない。
- `reproduce_orphan_root.py` で `_require` へ故障注入。例外後も `_default_root` が有効なまま残り、新しい `tk.Tk()` 上のCanvasへ暗黙masterの `ImageTk.PhotoImage` を配置すると `image "pyimage1" does not exist`。`master=canvas` では配置成功。2失敗の連鎖機構を実Tkで確認。
- 製品入口 `pagefolio/__main__.py` は単一rootを使い、`root_class.__new__` で先にroot参照を保持して `finally` で破棄する。今回の変更は通知再構築テストの契約から無関係なD&D拡張ロードを外すテスト隔離に限定した。外部 `tkdnd` 読込失敗の間欠的な発生条件までは確定していない。

## 修正と検証

- `tests/test_config_notification.py` の通知再構築1件のみ、rootを `tk.Tk()` にし、同テスト中の `_setup_file_drop` を無効化。通知の実App、表示時間、言語切替、原本保持の検証は維持。
- `verify_notice_without_tkdnd.py` で `_require` を常に例外にして当該テストを実行: `1 passed, 1 warning in 3.19s`。D&Dロード障害から分離できたことを確認。
- `ruff check .`: exit 0（sandbox内ではアクセス拒否の警告3件）。`ruff format . --config "include = ['*.py', '*.pyi', '*.ipynb']"`: sandbox内のアクセス拒否後、正規escalationで exit 0、`111 files left unchanged`。`pagefolio.py` AST: OK。`git diff --check`: OK。
- 最終native全件（専用の新規repo外 `--basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_config_notice_full_20261024_1`）: `1797 passed, 1 warning in 269.43s (0:04:29)`、exit 0。ログ: `full-native-20261024.txt`。唯一の警告は PyMuPDF の Python 3.17 向け `ByteString` deprecation。
- 最終全件後にPythonソースは変更していない。製品コード・版番号は変更なし。既存の DEP-05、owner_missing、通知前景不一致の解消根拠とはしない。

## 入力同一性

検証時のHEAD: `8b513b83da8ca22558f846fdc5ca6c0493932d96`。以下は最終全件後のSHA-256（ソース未変更）。今回の修正ファイルと、既存dirtyの主要入力を記録する。

| ファイル | SHA-256 |
| --- | --- |
| `tests/test_config_notification.py` | `1E65BB12062E5259D6AA4B441830D4C12B35691BE420A925B92701390AF88B7E` |
| `pagefolio/viewer.py` | `78A1D4A59D0C787DA71D23B40219252DE80286BB5734C2D9063E1A4ABCB6D3FA` |
| `tests/config_notice_support.py` | `9590343BEE17FF3919577F1A70E91F6B2EF56F5B101D21B74FFC120402CE008A` |
| `requirements.txt` | `5AFFADBAB19AAC41E06B20142E67DAF1A4326B898D0DE4D34CFDBBFA1B403F74` |
| `tests/test_startup_windows.py` | `B3A4AFCB619284E572628C2925AF3AF4680C424139A8734861712E73355AAA24` |
| `full-native-20261024.txt` | `3941E9E81231265CD5FC7B6ACFC6E42A164E1DD03192D244E09AC34FB142DBE1` |

既存dirtyファイルの内容を本調査では変更していない。`開発履歴.md` へは今回の一行のみ追加した。
