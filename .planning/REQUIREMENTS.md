# Requirements: PageFolio v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加

**Defined:** 2026-08-10
**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする。

**出典:**
- `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md`（既存機能レビュー・課題 8 件 V190-REV-01〜08）
- `.planning/research/SUMMARY.md`（v1.9.0 プロジェクトリサーチ・4 次元統合）

**マイルストーン共通の受け入れ条件:**
操作が失敗した場合、Document・Undo 履歴・外部ファイルはいずれも**操作前の状態へ戻る**こと。部分適用を無警告で残さないこと。

---

## v1 Requirements

### 保存・編集の安全性（SAFE）

- [ ] **V190-SAFE-01**: ユーザーがパスワード保護 PDF を「保存」「名前を付けて保存」「上書き（インクリメンタル保存失敗時のフォールバック）」のいずれの経路で保存しても、保存先 PDF の暗号化が維持される（REV-01）
- [ ] **V190-SAFE-02**: 暗号化の解除は「パスワード解除」の明示操作でのみ発生し、通常の保存経路では発生しない。保存後は UI 上の `pdf_has_password` 状態が実ファイルと一致する（REV-01）
- [ ] **V190-SAFE-03**: OCR が OFF のとき、ユーザーはバッチ OCR を起動・実行開始できない。`off` はプロバイダ生成可能な値として扱われず、通常 OCR・バッチ OCR・プラグイン経路のすべてで OFF が同一の意味を持つ（REV-02）
- [ ] **V190-SAFE-04**: 複数ファイル挿入が途中のファイルで失敗した場合、ページ数と Undo スタックが操作前と一致する。挿入元 Document は例外発生時も必ずクローズされる（REV-03）
- [ ] **V190-SAFE-05**: ページ複製が失敗した場合、既存ページと Undo スタックが変化しない（Undo 状態は成功後に確定される）（REV-04）

### 設定 UI の整合性（CFG）

- [ ] **V190-CFG-01**: ユーザーが LLM 設定ダイアログを Cancel した場合、外部プロンプトファイル（`ocr_custom_prompt.md` / `ocr_summary_prompt.md`）は変更されない。外部ファイルへの書き込みは Apply 押下時のみ行われる（REV-05・**Apply 一本化方式で確定**）
- [ ] **V190-CFG-02**: 選択済みテンプレートを編集した状態で別テンプレートへ切り替えると、外部プロンプトファイル連動の有無にかかわらず未保存確認が表示される（REV-06）

### Undo/Redo 堅牢性（UNDO）

- [ ] **V190-UNDO-01**: Undo または Redo の復元処理が失敗した場合、対象状態がスタックへ戻され履歴が失われない。Document が部分的に変更されたまま残らない（REV-07）
- [ ] **V190-UNDO-02**: `duplicate` / `merge` / `merge_resize` の各 op について do→undo→redo→undo の 4 手往復でページ構成が操作前と一致することが回帰テストで担保される（REV-07・v1.8.0 D-17 の水平展開）

### OCR プロバイダ基盤整理（CAT）

- [ ] **V190-CAT-01**: プロバイダのキー・表示名・クラウド種別・環境変数・既定モデル・送信先ホスト・フォールバック可否が単一の情報源から解決され、新プロバイダ追加時の変更面が 1 箇所に閉じる（REV-08）
- [ ] **V190-CAT-02**: 一元化後も `pagefolio/ocr_providers/registry.py` の独立性制約（Python 標準ライブラリのみに依存し pagefolio 内部モジュールを import しない・V180-D-01）が維持され、循環 import が発生しない（REV-08）

### OpenAI(ChatGPT) プロバイダ（OAI）

- [ ] **V190-OAI-01**: ユーザーは OCR プロバイダとして OpenAI(ChatGPT) を選択できる
- [ ] **V190-OAI-02**: ユーザーは LLM 設定ダイアログで OpenAI のセッション限定 API キーを入力でき、そのキーは `pagefolio_settings.json` に永続化されない（`_SENSITIVE_KEYS` ガード・V14-D-02）
- [ ] **V190-OAI-03**: ユーザーは OpenAI のモデル一覧を API から取得して選択でき、取得に失敗した場合は静的フォールバック一覧から選択できる
- [ ] **V190-OAI-04**: OpenAI で OCR を実行する前に、送信先ホストを明示した確認ダイアログが表示される
- [ ] **V190-OAI-05**: OpenAI で OCR を実行する前に、コスト確認ダイアログが表示される
- [ ] **V190-OAI-06**: ユーザーはバッチ OCR で OpenAI を選択・実行できる（クラウド判定・コスト確認・送信先表示を含む）
- [ ] **V190-OAI-07**: ユーザーは OpenAI をフォールバック候補として設定でき、フォールバック発動時に送信先確認が再提示される（V180-D-02 の明示設定型方針を維持）
- [ ] **V190-OAI-08**: ユーザーは OpenAI 実行時の画像 detail レベル（low / high / auto）を選択でき、設定が永続化される
- [ ] **V190-OAI-09**: ユーザーは reasoning effort 相当のパラメータを設定でき、対応モデル選択時のみ有効化される（Claude の `EFFORT_MODELS` 許可リスト方式を踏襲）
- [ ] **V190-OAI-10**: ユーザーは organization / project ID を任意入力でき、指定した場合のみリクエストヘッダへ付与される
- [ ] **V190-OAI-11**: OpenAI プロバイダは `urllib.request` 直叩きで実装され、新規 pip 依存を追加しない（V14-D-01 踏襲）
- [ ] **V190-OAI-12**: モデル別のパラメータ非互換（`max_tokens` 非対応で `max_completion_tokens` を要するモデル、`temperature` を拒否する o-series）が正しく分岐処理され、エラーにならない
- [ ] **V190-OAI-13**: OpenAI の 429 / 5xx 応答に対し既存の指数バックオフ・`Retry-After` 尊重のリトライ基盤（`ocr_providers/errors.py`）が適用される

### 品質保証・リリースゲート（QA）

- [ ] **V190-QA-01**: Tkinter 実行環境の問題（Python 3.14.6 での GUI テストのセットアップエラー）を切り分け・修復し、GUI テストを含む全テストが完走する。完走をリリースゲート条件とする
- [ ] **V190-QA-02**: 保存トーストの再試行を実行した際、上書き確認ダイアログが再表示される（IN-01・v1.8.0 Phase 6 持ち越し）
- [ ] **V190-QA-03**: 実機目視による human-verify / UAT を正式に実施し、結果を記録する（v1.4.0 / v1.6.0 / v1.7.1 で一旦 pass とした項目の正式消化）

---

## v2 Requirements

将来リリースへ繰り越し。追跡はするが現ロードマップには含めない。

### OpenAI 拡張

- **V190-F-01**: OpenAI Responses API への移行（ステートフルな会話継続・agentic 機能が必要になった場合）
- **V190-F-02**: organization / project ID の自動検出

### 設定 UI

- **V190-F-03**: `dialogs/llm_config/dialog.py` のセッション API キー同期ループの完全動的化（ウィジェット変数のカタログ駆動化）
- **V190-F-04**: プロンプトテンプレートのバージョン履歴 / 差分表示（v1.8.0 TMPL-F01 継承）

### バッチ OCR / 性能

- **V190-F-05**: バッチ OCR のバックグラウンド常駐継続・ジョブ永続化（v1.8.0 BATCH-F01/F02 継承）
- **V190-F-06**: サムネイルの react-window 相当の本格仮想化（v1.8.0 PERF-F01 継承）

---

## Out of Scope

明示的に除外。スコープクリープ防止のため理由を記録する。

| Feature | Reason |
|---------|--------|
| OpenAI 公式 SDK（`openai` パッケージ）の導入 | V14-D-01（urllib 直叩き・新規 pip 依存ゼロ）に反し、PyInstaller 配布バイナリが肥大化する。既存 5 プロバイダと同じパターンで実装可能なことをリサーチで確認済み |
| OpenAI Responses API へのフル移行 | PageFolio の OCR 呼び出しはステートレスな単発リクエストであり、Responses API の agentic / 状態保持機能が不要。Chat Completions は公式に無期限サポート表明あり |
| `detail=high` の常時強制 | ユーザーのコスト制御を奪う。既定値を high / auto 寄りにしつつ選択可能にする（V190-OAI-08）ことで代替 |
| 外部プロンプトファイルへのライブ即時書き込みの維持 | V190-CFG-01 で Apply 一本化方式を採用したため、ライブ連動 + Cancel 復元案は不採用 |
| 部分適用の無警告許容 | 本マイルストーンの受け入れ条件（失敗時は操作前状態へ戻る）に正面から反する |
| Document 全体スナップショット方式のロールバック | `doc.tobytes()` 全廃という BUG-02 の Key Decision に反し、Core Value（大きな PDF での Undo 性能）を毀損する |
| プロバイダ「ロジック」の共通化（`BatchOCRDialog` から `OCRDialog` のメソッド継承 / import） | `dialogs/batch_ocr.py` の独立性は意図的な設計判断（v1.8.0 Phase 4 懸念 5）。一元化するのは「データ」のみ |
| OAuth 接続 | 正規 API が非対応・配布バイナリに client secret を安全に埋め込めないため確定除外（v1.6.0 から継続） |
| OS キーストア連携（Windows Credential Manager）による API キー永続化 | セッション限定方針を維持（V14-D-02 踏襲）。永続化は別マイルストーン判断 |
| OCR 結果のページ埋め込み（検索可能 PDF 化） | v1.4.0 から継続除外 |

---

## Traceability

どのフェーズがどの要件をカバーするか。ロードマップ作成時に更新する。

| Requirement | Phase | Status |
|-------------|-------|--------|
| V190-SAFE-01 | Phase 1 | Pending |
| V190-SAFE-02 | Phase 1 | Pending |
| V190-SAFE-03 | Phase 1 | Pending |
| V190-SAFE-04 | Phase 1 | Pending |
| V190-SAFE-05 | Phase 1 | Pending |
| V190-CFG-01 | Phase 1 | Pending |
| V190-CFG-02 | Phase 1 | Pending |
| V190-UNDO-01 | Phase 1 | Pending |
| V190-UNDO-02 | Phase 1 | Pending |
| V190-CAT-01 | Phase 2 | Pending |
| V190-CAT-02 | Phase 2 | Pending |
| V190-OAI-01 | Phase 2 | Pending |
| V190-OAI-02 | Phase 2 | Pending |
| V190-OAI-03 | Phase 2 | Pending |
| V190-OAI-04 | Phase 2 | Pending |
| V190-OAI-05 | Phase 2 | Pending |
| V190-OAI-06 | Phase 2 | Pending |
| V190-OAI-07 | Phase 2 | Pending |
| V190-OAI-08 | Phase 2 | Pending |
| V190-OAI-09 | Phase 2 | Pending |
| V190-OAI-10 | Phase 2 | Pending |
| V190-OAI-11 | Phase 2 | Pending |
| V190-OAI-12 | Phase 2 | Pending |
| V190-OAI-13 | Phase 2 | Pending |
| V190-QA-01 | Phase 3 | Pending |
| V190-QA-02 | Phase 3 | Pending |
| V190-QA-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-10*
*Last updated: 2026-08-10 after ROADMAP.md creation (3 phases, 27/27 requirements mapped, no orphans)*
