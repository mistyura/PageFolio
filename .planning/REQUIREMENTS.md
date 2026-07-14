# Requirements: PageFolio v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化

**Defined:** 2026-07-13
**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする

## v1.8.0 Requirements

本マイルストーンのリリース要件。各要件はロードマップのフェーズへマップされる。

### テンプレート管理（TMPL）

- [x] **V180-TMPL-01**: ユーザーは OCR カスタム/サマリプロンプトを名前付きテンプレートとして保存できる
- [x] **V180-TMPL-02**: ユーザーはテンプレート一覧から選択して切り替えられる（LLM 設定ダイアログ）
- [x] **V180-TMPL-03**: ユーザーはテンプレートを削除・リネームできる
- [x] **V180-TMPL-04**: 外部 md ファイル連動（v1.7.4 の `ocr_custom_prompt.md` / `ocr_summary_prompt.md`）は「アクティブテンプレートのライブ編集」として共存する（書き戻し競合を起こさない）
- [x] **V180-TMPL-05**: テンプレートは全プロバイダで横断共有される（`resolve_ocr_prompt` の優先順位にテンプレート層を挿入・既存 custom > provider別 > 汎用の解決順と両立）

### プロバイダーフォールバック（FALL）

- [x] **V180-FALL-01**: ユーザーはフォールバック順（プロバイダ連鎖）を明示的に設定できる（未設定＝フォールバックしない・安全側既定）
- [x] **V180-FALL-02**: OCR 実行が fatal エラーで停止した際、次のフォールバック候補への切替が**送信先確認ダイアログの再提示つき**で提案される（自動的な別ベンダー送信はしない）
- [x] **V180-FALL-03**: フォールバック切替時、プロバイダ固有の並列度・APIキー解決・レート制限設定が正しく引き継がれる

### バッチ複数ファイル OCR（BATCH）

- [ ] **V180-BATCH-01**: ユーザーは複数 PDF ファイルを一括で OCR キューに投入できる（D&D 対応）
- [ ] **V180-BATCH-02**: キュー一覧でファイルごとの状態（待機/実行中/完了/失敗）と全体進捗を確認できる
- [ ] **V180-BATCH-03**: ファイル単位の失敗は分離され、残りのファイル処理は継続する
- [ ] **V180-BATCH-04**: バッチ全体・ファイル単位のキャンセルができる
- [ ] **V180-BATCH-05**: バッチ完了後、複数ファイル横断の統合サマリを生成できる（v1.6.4 サマリ基盤の延長・入力過大時の事前警告を含むメモリ/コンテキスト管理）

### サムネイル仮想化（PERF）

- [ ] **V180-PERF-01**: 大量ページ PDF で窓内サムネイルが可視範囲のみ実体化され、描画が高速化される（既存 `pagination.py` 窓表示の外層契約は不変）
- [ ] **V180-PERF-02**: `thumb_cache` に LRU eviction が導入され、メモリ使用が有界化される
- [ ] **V180-PERF-03**: `selected_pages` 全ページインデックス不変条件・D&D・窓表示との整合が回帰テストで保証される

### 基盤リファクタリング（REFAC）

- [x] **V180-REFAC-01**: `ocr_providers.py`（1537行）がパッケージ分割される（後方互換 import 維持・`test_imports.py` 先行拡張）
- [x] **V180-REFAC-02**: `dialogs/llm_config.py`（1659行）がパッケージ分割される（後方互換 import 維持・`test_imports.py` 先行拡張）
- [x] **V180-REFAC-03**: `ocr_dialog.py`（2154行）から OCR 実行エンジン（OCRRunEngine）が抽出され、単一ファイル OCR とバッチ OCR で共用される

### 堅牢性（ROBUST）

- [ ] **V180-ROBUST-01**: Blob ライフサイクルのリーク検出が強化され（`FileBlob` リーク検出ロギング等）、Windows AV スキャン衝突（`os.unlink` の `PermissionError`）の回帰テストが整備される
- [x] **V180-ROBUST-02**: `_SENSITIVE_KEYS` がプロバイダ→環境変数マッピングから生成される中央レジストリへ再編される（手動リストの追加漏れリスクを構造的に排除）
- [ ] **V180-ROBUST-03**: ShortcutsDialog の WR-01（キャプチャ対象切替時の前行表示残留）/ WR-02（修飾キーなし単キー登録が通常入力ウィジェットと衝突しうる）が解消される

### 品質保証（QA）

- [x] **V180-QA-01**: OCR→サマリの E2E モックテストが整備される（OCRRunEngine / `ocr_pipeline.py` 経由の一気通貫・実 API 非依存）
- [ ] **V180-QA-02**: エラー時リカバリー通知が改善される（再試行アクション付き非モーダルトースト・自動消滅なし・全エラーの非モーダル化はしない）
- [ ] **V180-QA-03**: UI 一貫性が監査・修正される（スクロールパターン統一・フォントスケーリング）
- [ ] **V180-QA-04**: 開発履歴.md の v1.7.0 表記整合が完了する（V16-D-04 残課題）

## Future Requirements

将来リリースへ繰り越し。現ロードマップ対象外。

### バッチ OCR 拡張

- **BATCH-F01**: バッチ OCR のバックグラウンド常駐継続（Tkinter シングルループ制約で UI 設計コスト高）
- **BATCH-F02**: バッチジョブの永続化（アプリ再起動を跨いだ resume）

### テンプレート拡張

- **TMPL-F01**: プロンプトテンプレートのバージョン履歴・差分表示（チーム向け SaaS 機能でデスクトップ単独アプリには過剰）

### パフォーマンス

- **PERF-F01**: サムネイルの連続スクロール型本格仮想化（react-window 相当への作り替え）

## Out of Scope

明示的な除外。スコープクリープ防止のため記録。

| Feature | Reason |
|---------|--------|
| API キー/プロンプト履歴の暗号化ローカル保存 | V14-D-02（セッション限定・非永続）と正面衝突。OS キーストア連携も継続除外 |
| Alpha/Beta/RC 段階リリース | zip+sha256 の直接リリース＋immutable releases 運用を維持。段階管理は GSD フェーズが担う |
| 自動ベンダー切替・コスト最適化ルーティング・確認なし連鎖リトライ | 外部送信の明示同意方針（既定 off・コスト確認）に違反 |
| OAuth 接続 | 正規 API が非対応・配布バイナリに client secret を埋め込めない（v1.6.0 期に確定済み） |
| OCR 結果のページ埋め込み（検索可能 PDF 化） | v1.4.0 から継続除外 |
| tksheet 等の外部ウィジェットライブラリ導入 | 既存 D&D グリッド UI と操作モデルが異なり全面書き換えが必要。新規 pip 依存ゼロ方針（V14-D-01）維持 |
| multiprocessing によるファイル並列 OCR | fitz.Document が picklable でなく PyInstaller frozen 環境の bootstrap が複雑。ファイル間逐次処理で対応 |

## Traceability

フェーズと要件の対応。ロードマップ作成時に更新される。

| Requirement | Phase | Status |
|-------------|-------|--------|
| V180-REFAC-01 | Phase 1 | Complete |
| V180-REFAC-02 | Phase 1 | Complete |
| V180-ROBUST-02 | Phase 1 | Complete |
| V180-TMPL-01 | Phase 2 | Complete |
| V180-TMPL-02 | Phase 2 | Complete |
| V180-TMPL-03 | Phase 2 | Complete |
| V180-TMPL-04 | Phase 2 | Complete |
| V180-TMPL-05 | Phase 2 | Complete |
| V180-FALL-01 | Phase 2 | Complete |
| V180-FALL-02 | Phase 2 | Complete |
| V180-FALL-03 | Phase 2 | Complete |
| V180-REFAC-03 | Phase 3 | Complete |
| V180-QA-01 | Phase 3 | Complete |
| V180-BATCH-01 | Phase 4 | Pending |
| V180-BATCH-02 | Phase 4 | Pending |
| V180-BATCH-03 | Phase 4 | Pending |
| V180-BATCH-04 | Phase 4 | Pending |
| V180-BATCH-05 | Phase 4 | Pending |
| V180-PERF-01 | Phase 5 | Pending |
| V180-PERF-02 | Phase 5 | Pending |
| V180-PERF-03 | Phase 5 | Pending |
| V180-ROBUST-01 | Phase 5 | Pending |
| V180-ROBUST-03 | Phase 5 | Pending |
| V180-QA-02 | Phase 6 | Pending |
| V180-QA-03 | Phase 6 | Pending |
| V180-QA-04 | Phase 6 | Pending |
