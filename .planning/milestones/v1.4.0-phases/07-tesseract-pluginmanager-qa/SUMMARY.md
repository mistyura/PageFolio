---
phase: 07-tesseract-pluginmanager-qa
plan: PLAN
subsystem: ocr
tags: [tesseract, subprocess, plugin-system, ocr-provider, i18n, docs]

# Dependency graph
requires:
  - phase: 06-gemini-provider
    provides: OCRProvider 抽象基底・build_provider マルチプロバイダ分岐・LLMConfigDialog プロバイダ展開フレーム
provides:
  - TesseractProvider（subprocess 直叩き・pytesseract 非依存のオフライン OCR）
  - PluginManager.register_ocr_provider フック（サードパーティ OCR バックエンド登録）
  - build_provider の plugin_manager 引数 + tesseract 分岐 + プラグインフォールバック
  - LLMConfigDialog の tesseract 展開フレーム・動的プロバイダリスト・未インストール時リセット
  - 全プロバイダの日英文言整備（lang.py）・README/開発履歴の v1.4.0 反映
affects: [プラグイン開発, OCR プロバイダ追加, オフライン OCR]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "subprocess stdin パイプ方式での Tesseract 呼び出し（pytesseract 非依存）"
    - "起動時 1 回評価のフィーチャ検出フラグ（_TESSERACT_AVAILABLE / _TESSERACT_LANGS）"
    - "PluginManager の _provider_registry + register_ocr_provider 登録フック（ローカル import で循環回避）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_providers.py
    - pagefolio/plugins.py
    - pagefolio/ocr.py
    - pagefolio/ocr_dialog.py
    - pagefolio/dialogs/llm_config.py
    - pagefolio/dialogs/settings.py
    - pagefolio/lang.py
    - README.md
    - 開発履歴.md
    - tests/test_ocr_providers.py
    - tests/test_plugins.py
    - tests/test_ocr.py

key-decisions:
  - "Tesseract stdin パイプ方式採用（pytesseract 非依存・Windows 動作確認済み）"
  - "_TESSERACT_AVAILABLE は起動時 1 回評価（仕様として許容・ドキュメント明記）"
  - "shell=False + noqa S603/S607 でコマンドインジェクション対策"
  - "register_ocr_provider はローカル import で循環 import を回避し issubclass(OCRProvider) でバリデーション"
  - "ttk Combobox は個別項目を無効化できないため、未インストール選択時は前プロバイダへリセットする方式"
  - "jpn 言語パック未検出時は eng フォールバック（モジュールフラグ参照）"

patterns-established:
  - "フィーチャ検出: 起動時にモジュールレベルで 1 回だけ外部コマンドの存在・能力を評価しフラグ化"
  - "プロバイダ拡張: build_provider 内蔵分岐 → plugin_manager._provider_registry フォールバックの二段解決"

requirements-completed: [OCR-EXT-01, OCR-EXT-02, OCR-QA-02]

# Metrics
duration: retroactive
completed: 2026-06-09
---

# Phase 07: Tesseract + PluginManager 拡張 + QA Summary

**オフライン OCR（Tesseract）とサードパーティ OCR プロバイダ登録フックを追加し、全プロバイダの文言・ドキュメントを整備して v1.4.0 マイルストーン（OCR プロバイダ化）を締め括った。**

> **遡及クローズアウト記録（2026-06-14）:** 本フェーズは 2026-06-09 にコミット `0c5dbfd`
> で実装・テスト完了していたが、SUMMARY.md 作成と STATE.md / ROADMAP.md 更新が未実施のまま
> 後続作業（v1.4.1〜v1.4.4）が進行していた。`/gsd-execute-phase 07` の safe-resume ゲートが
> 「実装コミットあり・SUMMARY.md 欠落」を検出し、ユーザー承認のもとで executor を実行せず手動
> クローズアウト（既存コード不変）として本サマリーを作成した。実装内容はコミット `0c5dbfd`
> が単一ソース。

## Performance

- **Duration:** 遡及記録（実作業は 2026-06-09 セッション内で完了）
- **Completed:** 2026-06-09T19:23:49+09:00（コミット `0c5dbfd`）
- **Tasks:** 6（Wave 1〜4、PLAN.md 定義の全タスク）
- **Files modified:** 12（実装・テスト・ドキュメント）

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

## Task Commits

実装は v1.4.0 フェーズ締め括りとして単一コミットにまとめてコミットされた（タスク単位の原子コミットではない）:

1. **Wave 1〜4 全タスク（Task 1.1〜4.2）** - `0c5dbfd` (feat) — TesseractProvider + PluginManager OCR フック追加 — Phase 07 完了

## Files Created/Modified

- `pagefolio/ocr_providers.py` - `_detect_tesseract()` / `_TESSERACT_AVAILABLE` / `_TESSERACT_LANGS` / `TesseractProvider` を追加
- `pagefolio/plugins.py` - `_provider_registry` + `register_ocr_provider` フックを追加
- `pagefolio/ocr.py` - `build_provider` に `plugin_manager` 引数・tesseract 分岐・プラグインフォールバックを追加
- `pagefolio/ocr_dialog.py` - `build_provider` 呼び出しに `plugin_manager` を伝搬
- `pagefolio/dialogs/llm_config.py` - tesseract 展開フレーム・動的プロバイダリスト・未インストール時リセット
- `pagefolio/dialogs/settings.py` - LLMConfigDialog への plugin_manager 受け渡し
- `pagefolio/lang.py` - Tesseract 文言 4 キー（ja/en）追加・未使用エントリ削除・OCR 文言のプロバイダ非依存化
- `README.md` - OCR セクションをマルチプロバイダ対応に更新（Tesseract インストール案内含む）
- `開発履歴.md` - v1.4.0 エントリ追記
- `tests/test_ocr_providers.py` - `TestTesseractProviderBasic` / `TestTesseractProviderOcrImage`
- `tests/test_plugins.py` - `TestPluginManagerProviderRegistry`
- `tests/test_ocr.py` - build_provider 拡張に伴うテスト調整

## Success Criteria — 達成状況

1. ✅ Tesseract 選択でプロバイダを使用でき、精度劣後注記が UI に表示される（Task 1.1 / 2.1）
2. ✅ 未インストール時は選択がリセットされ案内へ誘導（Task 2.1）
3. ✅ `register_ocr_provider` でサードパーティが登録可能、プロバイダ一覧に表示（Task 1.2 / 1.3 / 2.1）
4. ✅ プロバイダ名・APIキー・精度注記・コスト警告が日英対応、README/開発履歴が v1.4.0 反映（Task 3.1〜3.3）

## Verification（クローズアウト時点・2026-06-14）

- Phase 07 固有テスト 16 件全通過（`TestTesseractProviderBasic` 6 + `TestTesseractProviderOcrImage` 5 + `TestPluginManagerProviderRegistry` 5）※ venv/Scripts/pytest.exe
- `build_provider({'ocr_provider':'tesseract'})` → `TesseractProvider` を返す
- `build_provider({'ocr_provider':'<unknown>'})` → `ValueError`
- `lang.py`: `tesseract_accuracy_warning` が ja/en に存在、`ocr_progress_skip` は削除済み
- 開発履歴.md に `## v1.4.0` エントリ存在
- 後続の v1.4.1〜v1.4.4（490 tests グリーン）が本コミットの上に積層され、リグレッションなく稼働中

## Notes

- 本フェーズ完了後、コードベースは quick タスク群を経て v1.4.4 まで進行済み（APP_VERSION は実装当時の `1.4.0` から現在 `v1.4.4`）。
- Deferred（次マイルストーン）: Tesseract 言語パック選択 UI、`--psm`/`--oem` 公開オプション、OS キーストア連携、OCR 結果のページ埋め込み。
