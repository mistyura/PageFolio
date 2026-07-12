---
id: S04
parent: M001
milestone: M001
provides:
  - TesseractProvider（subprocess 直叩き・pytesseract 非依存のオフライン OCR）
  - PluginManager.register_ocr_provider フック（サードパーティ OCR バックエンド登録）
  - build_provider の plugin_manager 引数 + tesseract 分岐 + プラグインフォールバック
  - LLMConfigDialog の tesseract 展開フレーム・動的プロバイダリスト・未インストール時リセット
  - 全プロバイダの日英文言整備（lang.py）・README/開発履歴の v1.4.0 反映
requires: []
affects: []
key_files: []
key_decisions:
  - Tesseract stdin パイプ方式採用（pytesseract 非依存・Windows 動作確認済み）
  - _TESSERACT_AVAILABLE は起動時 1 回評価（仕様として許容・ドキュメント明記）
  - shell=False + noqa S603/S607 でコマンドインジェクション対策
  - register_ocr_provider はローカル import で循環 import を回避し issubclass(OCRProvider) でバリデーション
  - ttk Combobox は個別項目を無効化できないため、未インストール選択時は前プロバイダへリセットする方式
  - jpn 言語パック未検出時は eng フォールバック（モジュールフラグ参照）
patterns_established:
  - フィーチャ検出: 起動時にモジュールレベルで 1 回だけ外部コマンドの存在・能力を評価しフラグ化
  - プロバイダ拡張: build_provider 内蔵分岐 → plugin_manager._provider_registry フォールバックの二段解決
observability_surfaces: []
drill_down_paths: []
duration: retroactive
verification_result: passed
completed_at: 2026-06-09
blocker_discovered: false
---
# S04: Tesseract Pluginmanager Qa

**オフライン OCR（Tesseract）とサードパーティ OCR プロバイダ登録フックを追加し、全プロバイダの文言・ドキュメントを整備して v1.4.0 マイルストーン（OCR プロバイダ化）を締め括った。**

## Accomplishments

- **TesseractProvider（OCR-EXT-01）**: `subprocess` 直叩きでオフライン OCR を実現（pytesseract 非依存）。
  `_detect_tesseract()` が起動時に `--version` / `--list-langs` でインストール有無・言語一覧を評価し
  `_TESSERACT_AVAILABLE` / `_TESSERACT_LANGS` を確定。`ocr_image` は stdin/stdout パイプ方式で実行し、
  FileNotFound→RuntimeError・Timeout→TimeoutError・rc!=0→RuntimeError へ変換。
- **register_ocr_provider フック（OCR-EXT-02）**: `PluginManager._provider_registry` と
  `register_ocr_provider(name, cls)` を追加。`issubclass(cls, OCRProvider)` バリデーション・ローカル
  import による循環 import 回避。プラグインが `on_load` 内で独自バックエンドを登録できる。
- **build_provider 拡張（OCR-EXT-01/02）**: `plugin_manager=None` 引数・`tesseract` 分岐・
  プラグイン登録プロバイダへのフォールバックを追加。呼び出し箇所（ocr.py / ocr_dialog.py）も更新。
- **LLMConfigDialog UI 統合**: tesseract 展開フレーム（精度劣後注記の常設表示）・動的プロバイダリスト・
  未インストール時の選択リセットと案内ステータスを実装。
- **文言・ドキュメント整備（OCR-QA-02）**: Tesseract 向け 4 キーを ja/en 両辞書に追加・未使用エントリ削除・
  OCR 文言のプロバイダ非依存化。README の OCR セクションをマルチプロバイダ（LM Studio/Claude/Gemini/Tesseract）
  対応に更新し、開発履歴.md に v1.4.0 エントリを追記。
