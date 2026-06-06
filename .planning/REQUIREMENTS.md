# Requirements: PageFolio v1.4.0 — OCR プロバイダ化 + クラウドAPI対応

**Milestone:** v1.4.0
**Defined:** 2026-06-06
**Source:** `.planning/PROJECT.md`（Current Milestone）/ `.planning/research/`（STACK・FEATURES・ARCHITECTURE・PITFALLS・SUMMARY）/ 設計正典 `docs/OCRプロバイダ化_見積もり仕様.md`

> スコープ確定: Task 1 で「全部入り（プロバイダ抽象化 + Gemini + Claude + 低スペック対策 + Tesseract + プラグイン登録）」をユーザー選択。
> differentiator（任意）2 機能（コスト確認ダイアログ・セッションメモリキー入力欄）も含めることを 2026-06-06 に確認済み。

---

## v1.4.0 Requirements

REQ-ID 形式: `OCR-[CATEGORY]-[NN]`。v1.3.0（`BUG`/`REFAC`/`TEST`）とは別系統の新カテゴリのため `01` から採番。

### OCR-PROV — プロバイダ抽象化（土台）

- [ ] **OCR-PROV-01**: `OCRProvider` 抽象基底クラスを定義し、認識（`recognize`）・モデル一覧取得・並列度ポリシーの共通インターフェースを持つ
- [ ] **OCR-PROV-02**: 既存 LM Studio OCR を `LMStudioProvider` 実装へリファクタし、既存の OCR 挙動を後方互換で維持する
- [ ] **OCR-PROV-03**: `run_parallel()` をプロバイダ非依存に一般化し、プロバイダ別の並列度を受け取れるようにする

### OCR-API — クラウド API プロバイダ

- [ ] **OCR-API-01**: ユーザーは Claude（messages API・モデル一覧・`ANTHROPIC_API_KEY`）でページを OCR できる
- [ ] **OCR-API-02**: ユーザーは Gemini（generateContent・inline_data・モデル一覧・`GEMINI_API_KEY`/`GOOGLE_API_KEY`）でページを OCR できる
- [ ] **OCR-API-03**: プロバイダを切り替えたとき、該当プロバイダのモデル一覧を取得して選択肢に提示する

### OCR-SEC — セキュリティ（APIキー）

- [ ] **OCR-SEC-01**: APIキーは環境変数からのみ取得し、`pagefolio_settings.json` に書き込まない（`_save_settings()` への流入ガード）
- [ ] **OCR-SEC-02**: APIキー未設定でクラウド OCR を実行しようとしたとき、実行前に明示的なエラーを表示する（黙って失敗しない）
- [ ] **OCR-SEC-03**: 環境変数が未設定のユーザーは、保存されないセッション中メモリのキー入力欄からキーを与えて OCR を実行できる（`os.environ` にも書かない）

### OCR-UI — プロバイダ選択・ダイアログ UI

- [ ] **OCR-UI-01**: ユーザーは SettingsDialog でプロバイダ（off / gemini / claude / lmstudio / tesseract）を選択できる
- [ ] **OCR-UI-02**: 既定は `ocr_provider: "off"` で、off のとき OCR ボタンを無効化し外部送信・課金を防ぐ
- [ ] **OCR-UI-03**: クラウドプロバイダ選択時、実行前にページ数 × 概算コストとプライバシー注記の確認ダイアログを表示する（ローカル/Tesseract には表示しない）
- [ ] **OCR-UI-04**: Opus 系モデル選択時の temperature/effort をモデル別に防御的に扱う（非対応パラメータは送らず、`effort` を提示）

### OCR-PERF — 低スペック対策・安定性

- [ ] **OCR-PERF-01**: テキストが埋め込まれたページは `page.get_text()` の結果を採用し、Vision API 呼び出しをスキップする
- [ ] **OCR-PERF-02**: ページ単位の逐次レンダリング → 送信 → 破棄でメモリ使用量を抑える（全ページ画像の一括保持を廃止）
- [ ] **OCR-PERF-03**: クラウドプロバイダは並列度を抑制する（Gemini=1 / Claude=2、ローカル LM Studio は最大 8）
- [ ] **OCR-PERF-04**: 429 / 5xx 応答に対し指数バックオフでリトライする（最大 3 回・`Retry-After` ヘッダ優先）
- [ ] **OCR-PERF-05**: `ocr_scale` のデフォルトを 1.5 に見直し、速度/コスト ↔ 精度のトレードオフヒントを UI に表示する

### OCR-EXT — 拡張（任意・最終フェーズ）

- [ ] **OCR-EXT-01**: ユーザーは Tesseract（オフライン・無料・精度劣後注記つき）でページを OCR できる
- [ ] **OCR-EXT-02**: PluginManager にカスタム OCR プロバイダ登録フック（`register_ocr_provider`）を追加し、サードパーティが独自バックエンドを登録できる

### OCR-QA — テスト・文言・ドキュメント

- [ ] **OCR-QA-01**: 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定をモックでテストする（`tests/test_ocr.py`）
- [ ] **OCR-QA-02**: プロバイダ名・APIキー未設定・精度注記・コスト警告の多言語文言（`lang.py`）と README/開発履歴を更新する

---

## Future Requirements（次マイルストーン以降）

- OS キーストア連携（Windows Credential Manager）による APIキー永続化 — セキュリティを保ったキー保存。別マイルストーン
- OCR 結果のページ埋め込み（検索可能 PDF 化）— 現状は結果ビューア/エクスポートのみ
- プロバイダ別の詳細な実コスト計測・課金トラッキング

## Out of Scope（v1.4.0 で明確に除外）

- **APIキーの `settings.json` 平文保存** — 認証情報漏洩リスク。環境変数 or セッションメモリのみ（OCR-SEC で代替）
- **クラウド OCR の 8 並列固定** — 429 を頻発させる。プロバイダ別並列度で制御（OCR-PERF-03）
- **公式 SDK（`anthropic` / `google-genai`）採用** — PyInstaller 肥大化。`urllib` 直叩きで実装（確定方針）
- **Tesseract を主役エンジンに据える / LM Studio を GPU 非搭載者の主推奨に据える** — 精度・実用性で期待に応えられない。あくまでオプション/選択肢
- 暗号化 PDF 対応・印刷機能 — 本プロジェクト（最適化 + OCR 拡張）のスコープ外

---

## Traceability

各要件 → フェーズの対応表。ロードマップ作成時に埋める。

| REQ-ID | Phase | Status |
|--------|-------|--------|
| OCR-PROV-01 | — | Pending |
| OCR-PROV-02 | — | Pending |
| OCR-PROV-03 | — | Pending |
| OCR-API-01 | — | Pending |
| OCR-API-02 | — | Pending |
| OCR-API-03 | — | Pending |
| OCR-SEC-01 | — | Pending |
| OCR-SEC-02 | — | Pending |
| OCR-SEC-03 | — | Pending |
| OCR-UI-01 | — | Pending |
| OCR-UI-02 | — | Pending |
| OCR-UI-03 | — | Pending |
| OCR-UI-04 | — | Pending |
| OCR-PERF-01 | — | Pending |
| OCR-PERF-02 | — | Pending |
| OCR-PERF-03 | — | Pending |
| OCR-PERF-04 | — | Pending |
| OCR-PERF-05 | — | Pending |
| OCR-EXT-01 | — | Pending |
| OCR-EXT-02 | — | Pending |
| OCR-QA-01 | — | Pending |
| OCR-QA-02 | — | Pending |

---
*Requirements defined: 2026-06-06 — Milestone v1.4.0 (OCR プロバイダ化 + クラウドAPI対応).*
