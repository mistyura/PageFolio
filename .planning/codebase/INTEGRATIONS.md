# External Integrations

**Analysis Date:** 2026-06-01

## Third-Party Libraries

| Name | Version | Purpose | How used in codebase |
|------|---------|---------|---------------------|
| PyMuPDF (fitz) | 1.27.2.2 | PDF 操作エンジン | `pagefolio/file_ops.py`, `pagefolio/page_ops.py`, `pagefolio/viewer.py`, `pagefolio/ocr.py`, `pagefolio/dialogs.py` で `import fitz` |
| Pillow (PIL) | 12.2.0 | 画像処理・Tk 表示変換 | `pagefolio/viewer.py` で `from PIL import Image, ImageTk` — プレビュー・サムネイル描画 |
| tkinterdnd2 | 0.4.3 | OS ネイティブ D&D | `pagefolio/file_drop.py` と `pagefolio/__main__.py` で条件付きインポート（未インストール時は機能スキップ） |

## File Format Integrations

**PDF (.pdf):**
- 読み取り: `fitz.open(path)` — `pagefolio/file_ops.py`
- 書き出し: `doc.save(path, garbage=4, deflate=True)` — `pagefolio/file_ops.py`
- ページレンダリング: `page.get_pixmap(matrix=fitz.Matrix(...))` — `pagefolio/viewer.py`
- 縮小保存: `doc.save(..., garbage=4, deflate=True, clean=True)` — `pagefolio/file_ops.py`

**画像 (.png / .jpg / .jpeg / .bmp / .tiff / .tif):**
- 読み取り: 画像ファイルを `fitz.open()` で PDF に変換して開く — `pagefolio/file_ops.py`
- Tk 表示: `ImageTk.PhotoImage` 経由 — `pagefolio/viewer.py`
- OCR 送信用変換: `fitz.Page → PNG bytes → base64` — `pagefolio/ocr.py`

**対応拡張子定数:** `pagefolio/constants.py` の `SUPPORTED_EXTENSIONS` / `IMAGE_EXTENSIONS`

## External APIs / Services

**LM Studio (OCR 機能):**
- 種別: ローカル HTTP サーバー（OpenAI 互換 Vision API）
- デフォルト URL: `http://localhost:1234`（設定変更可）
- 実装: `pagefolio/ocr.py` — `urllib.request` で直接 HTTP 通信
- エンドポイント:
  - `POST /v1/chat/completions` — OCR テキスト抽出（画像 base64 付き）
  - `GET /v1/models` — 利用可能モデル一覧取得（`fetch_lm_studio_models()`）
- 認証: なし（ローカル接続のみ）
- 並列処理: `concurrent.futures.ThreadPoolExecutor`（最大 8 並列、デフォルト 2）
- タイムアウト: デフォルト 120 秒（設定変更可）

**推奨モデル:** Qwen2-VL-7B / MiniCPM-V / InternVL2 8B 以上（constants.py の LANG に記載）

## Data Storage

**設定ファイル:**
- ファイル: `pagefolio_settings.json`（実行ディレクトリ、`.gitignore` 対象）
- 形式: JSON
- 実装: `pagefolio/settings.py` — `_load_settings()` / `_save_settings()`
- 保存内容: テーマ、フォントサイズ、ウィンドウジオメトリ、編集モード、LM Studio URL/モデル設定

**プラグインディレクトリ:**
- ディレクトリ: `plugins/`（実行ディレクトリ相対）
- 形式: `.py` ファイル（動的 `importlib.util.spec_from_file_location()` で読み込み）
- 実装: `pagefolio/plugins.py`

**データベース:** なし（ファイルベースのみ）

**キャッシュ:** サムネイルをメモリ内の `self.thumb_cache` 辞書でキャッシュ（`pagefolio/viewer.py`）

## Authentication & Identity

**認証:** なし（スタンドアロン GUI アプリ）

## Monitoring & Observability

**ログ:**
- 標準ライブラリ `logging` を使用
- 各モジュールが `logging.getLogger(__name__)` でロガーを取得
- ログレベル設定は `pagefolio/__main__.py` のエントリーポイントで管理

**エラー追跡:** なし（外部サービス未使用）

## CI/CD & Deployment

**ビルド:** PyInstaller 6.19.0 で Windows `.exe` を生成
**CI パイプライン:** なし（ローカル `pytest` / `ruff` による手動確認）
**配布形式:** GitHub Releases（手動）

## Webhooks & Callbacks

**Incoming:** なし
**Outgoing:** なし（LM Studio への HTTP リクエストは OCR 実行時のみ）

---

*Integration audit: 2026-06-01*
