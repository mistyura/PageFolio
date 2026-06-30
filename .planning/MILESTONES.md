# Milestones

## v1.6.2 Ollama・RunPod プロバイダ追加・設定画面リプレース (Shipped: 2026-06-30)

**Type:** ポイントリリース（GSD フェーズなし・`feature/add-ollama-runpod` ブランチ作業）

**Key accomplishments:**

- LLM（OCR）設定に **Ollama** / **RunPod** プロバイダを追加（`pagefolio/ocr_providers.py` +288 行）
- プロバイダ選択・モデル設定 UI（`pagefolio/dialogs/llm_config.py`）をリプレース（+255 行）
- 新プロバイダを OCR 実行経路（`ocr.py` / `ocr_dialog.py`）へ配線、文言（ja/en 同一キー）・既定設定を追加
- プロバイダ単体テストを追加（`tests/test_ocr_providers.py` +93 行）
- 品質保証: ruff クリーン・pytest 619 件グリーン

**Note:** GSD フェーズ外のブランチ作業。実装コミット `60c3acc` / ビルド `c4fbc2d`、`main` へ PR #26 でマージ（マージコミット `ae16c22`）。注釈付きタグ `v1.6.2`・GitHub Release を Latest 公開（2026-06-30、バイナリ zip は未添付）。本エントリは出荷後に遡及追記。

---

## v1.6.1 パスワード対応・印刷機能・OCR タイムアウト上限拡大 (Shipped: 2026-06-23)

**Type:** ポイントリリース（GSD フェーズなし・クイックタスク 260622 / 260623）

**Key accomplishments:**

- PDF パスワード対応（付与/解除・AES-256・暗号化 PDF の認証オープン）— 新規 `pagefolio/file_ops.py` 連携・`dialogs/password.py`
- 印刷機能（Ctrl+P・既定 PDF ハンドラ送信）— 新規 `pagefolio/print_ops.py`
- OCR テキスト抽出画面・LLM 設定ダイアログのタイムアウト上限を 600 秒 → 900 秒へ拡大（クランプ計 4 箇所）
- 品質保証: ruff クリーン・pytest 613 件グリーン（パスワード/印刷テスト 16 件追加）

**Note:** GSD フェーズ外のクイックタスク群。260622-grm（タイムアウト拡大・`2bff34b`）+ 260623-pwp（パスワード/印刷）を `claude/great-maxwell-k67sbc` ブランチで実装し、260623-rel で `main` へ PR #25 マージ（`fd20608`）・注釈付きタグ `v1.6.1`・GitHub Release を Latest 公開。STATE.md「Quick Tasks Completed」には記録済みだったが MILESTONES.md 未記載のため遡及追記。

---

## v1.6.0 品質向上・AI強化・設定/UI改善 (Shipped: 2026-06-20)

**Phases completed:** 4 phases, 11 plans, 23 tasks

**Known deferred items at close:** 5（Phase 04 04-VERIFICATION.md human_needed〔human-verify スキップ〕+ v1.4.0 期クイックタスク 4 件・既受容。詳細は STATE.md「Deferred Items」）

**Key accomplishments:**

- OCRDialog の数値パラメータ 4 Spinbox と model_combo を読み取り専用化し、LLM 設定の適用結果を全プロバイダ共通箇所で即時同期して OCR パラメータの二重入力（V16-UI-01）を解消した
- H1 回転プレビュー即時反映バグの真因をセレクション意味論と特定し、_rotate_selected で current_page を回転対象へ寄せる原因除去で修正。90/270°入替・180°不変の回転 w/h 単体テストを回帰防止アンカーとして追加。
- OCR 結果 Markdown を (行種別, インライン span) へ変換する Tk/fitz 非依存の純関数 parse_markdown / _split_inline を新設し、9 件の Tk 非生成 unit テストで網羅検証
- 単一プリセットのみだった OCR_PROMPTS を「プリセット × プロバイダ × カスタム」へ昇格させ、Claude=XML タグ／Gemini=明示指示のプロバイダ別テンプレート PROVIDER_OCR_PROMPTS と純関数 resolve_ocr_prompt を pagefolio/ocr.py に新設、6 件の Tk 非生成 unit テストで優先順位とフォールバックを検証

---

## v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト (Shipped: 2026-06-16)

**Phases completed:** 4 phases

**Key accomplishments:**

- PDF ページ操作の拡充: 白紙ページ挿入（`_insert_blank_page`）・テキスト透かし／ページ番号追加（`_add_watermark_text` / `_add_page_numbers`、`insert_text` ベース・テキストのみ）・ページ削除/結合/分割時の TOC（しおり）保持調整（`get_toc`/`set_toc`）を `page_ops.py` に追加した。
- UI/UX 改善: ツールバーのスライダー（`thumb_zoom_scale`）によるサムネイルサイズ動的変更、外部 PDF のサムネイルペインへの D&D 指定位置挿入、`pagefolio_settings.json` の `shortcuts` キーによるショートカット動的読込（ミニマム実装・JSON 編集のみ）を実装した。
- OCR 連携進化: `LLMConfigDialog` にカスタムプロンプト入力欄を追加し、`ocr_custom_prompt` 設定として保存・OCR バックエンドへ受け渡す経路を実装した。
- 品質保証: ruff クリーン・pytest 490 件全通過。

**Note:** 実装は `feature/v1.5.0-improvements` ブランチ（コミット `4d4ee75` 実装 / `0651bb0` マイルストーン文書）。本マイルストーンは別ワークフローで実装され、2026-06-16 に GSD 記録・プロジェクト文書（APP_VERSION/README/開発履歴/PROJECT/STATE/ROADMAP）を遡及的に整合させた。ruff の E501 2 件は整合作業時に修正済み。

---

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
