# Milestones

## v1.4.0 OCR プロバイダ化 + クラウドAPI対応 (Shipped: 2026-06-14)

**Phases completed:** 4 phases, 14 plans, 26 tasks

**Key accomplishments:**

- `abc.ABC` 抽象基底 `OCRProvider` と例外専用クラス `OCRAPIKeyError`、LM Studio urllib 直叩き実装 `LMStudioProvider` を `pagefolio/ocr_providers.py` として新設し、後続プランの Provider インターフェース契約を確定した
- `run_parallel(provider, ...)` / `has_embedded_text()` / `build_provider()` を新設し `ocr.py` を Provider 非依存にリファクタ、LM Studio 固有関数を削除
- OCRDialog の _worker から fitz アクセスを完全排除し、メインスレッドの after() 小分けレンダリング・埋め込みテキストスキップ統合・run_parallel 結線を実現（Phase 4 三成功基準を UI 層で結実）
- `_on_run` で LMStudioProvider を再生成して OCR UI 値をリクエストに反映（CR-02）し、`_start_ocr` の未捕捉 ValueError を try/except でグレースフル処理（CR-01）。
- `_SENSITIVE_KEYS` ガードで API キー平文漏洩を構造的に防止し、Phase 5 UI が参照する 9 文言キーを ja/en 両対応で追加した。
- `_resolve_api_key`（環境変数優先・未設定 OCRAPIKeyError）・`build_provider` claude 分岐（キー引数注入）・`run_parallel` 指数バックオフ（最大3回・Retry-After 優先・waiting 進捗）・`_start_ocr` キー解決ゲートを実装し、成功基準2/3/8 を担保した。
- プロバイダ選択 UI（SettingsDialog Combobox）・OCR ボタン状態の連動制御・Claude モデル一覧の静的フォールバックを実装（Phase 05-04）
- コスト確認ダイアログ・`waiting/{attempt}` リトライ進捗表示・セッションキー入力欄（settings 非永続）を実装（Phase 05-05）
- x-goog-api-key ヘッダー認証・thinkingBudget=0・dual env var 解決を備えた GeminiProvider を ClaudeProvider テンプレートで実装し、build_provider / _resolve_api_key / _cloud_providers に gemini 配線を追加。
- queue.Queue(maxsize=concurrency+1) による bounded buffer producer-consumer で全ページ base64 一括保持を廃止し、ページ単位 render→送信→破棄パイプラインと Tk 非依存ヘルパーでメモリ上限を機械保証する。
- ocr_scale 既定を 1.5 に変更・Gemini プロバイダを SettingsDialog と OCRDialog に統合し、プロバイダ判定系全メソッド（_is_cloud_provider/_needs_session_key/_provider_display_name/_apply_llm_settings/_confirm_cost）を dual env var 対応で gemini 対応化。
- LM Studio 並列度を `self.concurrency` 本に復元（`threading.Lock` 保護 + 最終ワーカー調整）し、キャンセル時の結果二重挿入を冪等ガードで解消。Python 3.8 互換化と GOOGLE_API_KEY 平文保存防止も同時達成。
- オフライン OCR（Tesseract）とサードパーティ OCR プロバイダ登録フックを追加し、全プロバイダの文言・ドキュメントを整備して v1.4.0 マイルストーン（OCR プロバイダ化）を締め括った。

**Known deferred items at close:** 5（Phase 04 検証ギャップ 1 + クイックタスク完了マーカー欠落 4。詳細は STATE.md「Deferred Items」参照。実作業は v1.4.0〜v1.4.4 として出荷済み）

**Note:** Phase 07 は実装コミット `0c5dbfd`（2026-06-09）で完了済みだったが GSD 記録が未クローズだったため 2026-06-14 に遡及クローズアウト。出荷後 v1.4.1〜v1.4.4 が積層済み。

---

## v1.3.0 コード最適化 MVP (Shipped: 2026-06-03)

**Phases completed:** 3 phases, 8 plans, 3 tasks

**Key accomplishments:**

- `doc.tobytes()` 全体シリアライズを撤廃し全 op を op 別逆デルタで往復させる対称 Undo/Redo 設計への全面刷新（BUG-01 挿入 Undo 修正・BUG-02 フリーズ解消）
- `_undo_stack`/`_redo_stack` を `collections.deque(maxlen=MAX_UNDO)` に変更し `_save_undo` の手動 `list.pop(0)` O(n) トリムを撤廃して上限管理を O(1) に一本化（REFAC-03）
- 挿入 Undo の内容同一性（digest）・redo 往復テスト（D-07）と全 op 最小往復安全網テストを追加し、テストで発見した delete/move/merge_resize の対称デルタバグ 3 件を Rule 1 自動修正（TEST-01 / Deferred 安全網）
- ページ切り替え時の `doc.tobytes()` フルシリアライズを廃止し、`page.get_pixmap()` の同期直接呼び出しへ変更。Tk 非依存の純関数ヘルパー `_render_preview_pixmap` を抽出してテスト可能にし、回帰テスト `tests/test_viewer.py` を新規作成した。
- 711 行の混在モジュール `pagefolio/constants.py` を責務別に3分割（themes.py・lang.py・再エクスポート化した constants.py）し、後方互換 import 表面を完全に維持したリファクタリング。
- Task 3（最終ゲート）
- `set_current_font_size` / `get_current_font_size` 公開 API を settings.py に追加し、app.py・merge.py・llm_config.py の `_current_font_size` 直接アクセスをすべて API 経由に置換（DEBT-04 解消 / D-02 stale binding 修正）。

---
