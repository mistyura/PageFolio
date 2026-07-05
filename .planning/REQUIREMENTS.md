# Requirements: PageFolio v1.7.1 現機能ブラッシュアップ + APIキー入力欄

**Defined:** 2026-07-04
**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする

## v1.7.1 Requirements

本マイルストーンのリリース要件。各要件はロードマップのフェーズへマップされる。

### APIキー入力欄（KEY）

- [x] **V171-KEY-01**: ユーザーは LLM設定ダイアログで Claude / Gemini / RunPod の APIキーを入力できる（セッション限定・`settings.json` へは保存されない）
- [x] **V171-KEY-02**: キー解決は「入力値 → 環境変数」の優先順で行われ、両方未設定の場合はエラーが表示される
- [x] **V171-KEY-03**: OCRDialog 側の既存セッションキー入力欄は撤去され、キー設定導線が LLM設定ダイアログに一元化される
- [x] **V171-KEY-04**: RunPod もセッションキー機構（`_session_api_keys`）で扱える

### UI/UX 磨き込み（UIUX）

- [x] **V171-UIUX-01**: ユーザーはショートカットを設定ダイアログの GUI で編集できる（JSON 直接編集不要）
- [ ] **V171-UIUX-02**: エラー表示・文言の一貫性が監査・修正される（ja/en 辞書の欠落/未使用キー含む・L-5 吸収）
- [x] **V171-UIUX-03**: SettingsDialog / LLMConfigDialog の項目配置・セクションが整理される

### OCR 磨き込み（OCR）

- [x] **V171-OCR-01**: L-6 小物が現行コード照合の上で一括解消される（プログレス 100% 問題・URL スキーム検証・モデル名エスケープ・`_fetch_models`/`_test_connection` 重複解消 等）
- [x] **V171-OCR-02**: TesseractProvider が `tesseract_lang` 設定を尊重する（利用不可時は自動フォールバック・L-4）
- [x] **V171-OCR-03**: プラグイン OCR registry が堅牢化される（重複名警告・unload 時登録解除・公開アクセサ・L-2/L-3）
- [x] **V171-OCR-04**: producer-consumer ロジックが一本化される（`ocr.py` 未使用ヘルパーと `ocr_dialog.py` 独自実装の二重実装解消・L-1）

### ページ操作磨き込み（PAGE）

- [x] **V171-PAGE-01**: ユーザーは画像（ロゴ）を透かしとして追加できる（v1.5.0 テキストのみ制限の解除）
- [x] **V171-PAGE-02**: 黒塗り/モザイクの使い勝手が改善される（具体項目は棚卸しで確定）
- [x] **V171-PAGE-03**: 回転/トリミングの操作性が改善される（具体項目は棚卸しで確定）

### テスト・安定性（TEST）

- [x] **V171-TEST-01**: v1.5.0 新機能（白紙挿入・透かし・ページ番号・TOC 保持・D&D 挿入・ショートカット読込）の回帰テストが整備される
- [x] **V171-TEST-02**: APIキー新機能のテストが整備される（優先順解決・非保存ガード回帰）
- [ ] **V171-TEST-03**: 既知軽微バグが棚卸しされ、活き残りが解消される（L-6 の現行照合と重複しない範囲）

## Key Context

- **キー解決の優先順反転**: 現行は「環境変数優先・未設定時のみ入力値」（OCRDialog 側）。本マイルストーンで「入力値 → 環境変数」へ反転する
- **非永続化の維持**: APIキーの `settings.json` 非永続化（`_SENSITIVE_KEYS` ガード）は V14-D-02 を踏襲して維持
- **L-1〜L-6 の鮮度**: v1.4.0 期のレビュー由来のため、v1.6.0〜v1.7.0 で解消済みの項目がある（例: stop_reason 途切れ検出は v1.6.0 Phase 3 で実装済み）。計画時に現行コードと照合し、活き残りのみ対象とする

## Future Requirements

将来リリースへ繰り越し。現ロードマップには含めない。

- **PERF-01**: サムネイル仮想化によるパフォーマンス改善（大量ページ対応）

## Out of Scope

明示的な除外。スコープクリープ防止のため記録。

| Feature | Reason |
|---------|--------|
| OS キーストア連携（Windows Credential Manager）によるキー永続化 | セッション限定方針を維持（V14-D-02）。永続化は別マイルストーン |
| OAuth 接続 | 確定除外事項（正規 API 非対応・配布バイナリに client secret を埋め込めない） |
| OCR 結果のページ埋め込み（検索可能 PDF 化） | v1.4.0 から継続除外 |
| プラグイン API バージョン管理 | 今後の別タスク |

## Traceability

フェーズ割当は 2026-07-04 のロードマップ作成時に確定（v1.7.1 Phase 1〜4・被覆 17/17・孤立要件なし）。

| Requirement | Phase | Status |
|-------------|-------|--------|
| V171-KEY-01 | Phase 1 | Complete |
| V171-KEY-02 | Phase 1 | Complete |
| V171-KEY-03 | Phase 1 | Complete |
| V171-KEY-04 | Phase 1 | Complete |
| V171-UIUX-01 | Phase 4 | Complete |
| V171-UIUX-02 | Phase 4 | Pending |
| V171-UIUX-03 | Phase 4 | Complete |
| V171-OCR-01 | Phase 2 | Complete |
| V171-OCR-02 | Phase 2 | Complete |
| V171-OCR-03 | Phase 2 | Complete |
| V171-OCR-04 | Phase 2 | Complete |
| V171-PAGE-01 | Phase 3 | Complete |
| V171-PAGE-02 | Phase 3 | Complete |
| V171-PAGE-03 | Phase 3 | Complete |
| V171-TEST-01 | Phase 3 | Complete |
| V171-TEST-02 | Phase 1 | Complete |
| V171-TEST-03 | Phase 4 | Pending |
