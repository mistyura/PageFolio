# Roadmap: PageFolio コード最適化

## Milestones

- ✅ **v1.3.0 コード最適化 MVP** — Phases 1-3 (shipped 2026-06-03) — [archive](milestones/v1.3.0-ROADMAP.md)
- ✅ **v1.4.0 OCR プロバイダ化 + クラウドAPI対応** — Phases 4-7 (shipped 2026-06-14) — [archive](milestones/v1.4.0-ROADMAP.md)
- ✅ **v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト** — Phases 1-4 (shipped 2026-06-16) — [archive](milestones/v1.5.0-ROADMAP.md)
- ✅ **v1.6.0 品質向上・AI強化・設定/UI改善** — Phases 1-4 (shipped 2026-06-20) — [archive](milestones/v1.6.0-ROADMAP.md)
- ✅ **v1.7.1 現機能ブラッシュアップ + APIキー入力欄** — Phases 1-4 (shipped 2026-07-05) — [archive](milestones/v1.7.1-ROADMAP.md)
- 🚧 **v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化** — Phases 1-6 (active, started 2026-07-13)

> **Note:** v1.6.1〜v1.7.0（パスワード/印刷・Ollama/RunPod・バグ修正・サマリ安定化・黒塗り/モザイク・undo ディスク退避）は GSD フェーズ外のポイントリリースとして出荷済み。詳細は [MILESTONES.md](MILESTONES.md) を参照。

## Phases

<details>
<summary>✅ v1.3.0 コード最適化 MVP (Phases 1-3) — SHIPPED 2026-06-03</summary>

- [x] Phase 1: Undo/Redo 修正 (3/3 plans) — completed 2026-06-03
- [x] Phase 2: プレビュー最適化とリファクタリング (3/3 plans) — completed 2026-06-03
- [x] Phase 3: API 整理と回帰テスト (2/2 plans) — completed 2026-06-03

全フェーズの詳細・成功基準・プラン内訳は [milestones/v1.3.0-ROADMAP.md](milestones/v1.3.0-ROADMAP.md) を参照。

</details>

<details>
<summary>✅ v1.4.0 OCR プロバイダ化 + クラウドAPI対応 (Phases 4-7) — SHIPPED 2026-06-14</summary>

- [x] Phase 4: プロバイダ抽象化 (4/4 plans) — completed 2026-06-06
- [x] Phase 5: Claude Provider + セキュリティ基盤 + プロバイダ選択 UI (5/5 plans) — completed 2026-06-07
- [x] Phase 6: Gemini Provider + 逐次レンダリング最適化 (4/4 plans) — completed 2026-06-07
- [x] Phase 7: Tesseract + PluginManager 拡張 + QA (1/1 plan) — completed 2026-06-14

全フェーズの詳細・成功基準・プラン内訳は [milestones/v1.4.0-ROADMAP.md](milestones/v1.4.0-ROADMAP.md) を参照。
既知の遅延項目（Phase 04 検証ギャップ等）は STATE.md「Deferred Items」を参照。

</details>

<details>
<summary>✅ v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト (Phases 1-4) — SHIPPED 2026-06-16</summary>

- [x] Phase 1: PDF ページ操作・編集機能の拡充 — completed 2026-06-16
- [x] Phase 2: UI / UX とパフォーマンスの改善 — completed 2026-06-16
- [x] Phase 3: AI・OCR連携のさらなる進化 — completed 2026-06-16
- [x] Phase 4: テスト・品質保証 — completed 2026-06-16

全フェーズの詳細・成功基準は [milestones/v1.5.0-ROADMAP.md](milestones/v1.5.0-ROADMAP.md) を参照。
実装は `feature/v1.5.0-improvements` ブランチ（別 WF 実装・2026-06-16 に文書整合）。

</details>

<details>
<summary>✅ v1.6.0 品質向上・AI強化・設定/UI改善 (Phases 1-4) — SHIPPED 2026-06-20</summary>

- [x] Phase 1: 設定/UI 改善（OCR パラメータ一元化・スライダー配置） (2/2 plans) — completed 2026-06-18
- [x] Phase 2: 大量ページのページネーション表示 (3/3 plans) — completed 2026-06-19
- [x] Phase 3: 体感品質・回転プレビュー & OCR 堅牢性（プランA） (3/3 plans) — completed 2026-06-19
- [x] Phase 4: AI 出力品質（プランC） (3/3 plans) — completed 2026-06-20

全フェーズの詳細・成功基準・プラン内訳は [milestones/v1.6.0-ROADMAP.md](milestones/v1.6.0-ROADMAP.md) を参照。
Phase 4 の human-verify チェックポイントはユーザー判断でスキップ（実機目視未検証・コード検証済）。締め前監査の 5 件は受容済（STATE.md「Deferred Items」参照）。

</details>

<details>
<summary>✅ v1.7.1 現機能ブラッシュアップ + APIキー入力欄 (Phases 1-4) — SHIPPED 2026-07-05</summary>

- [x] Phase 1: APIキー入力欄（LLM設定への一元化） (4/4 plans) — completed 2026-07-04
- [x] Phase 2: OCR 磨き込み（レビュー残の現行照合と二重実装解消） (4/4 plans) — completed 2026-07-05
- [x] Phase 3: ページ操作磨き込み + v1.5.0 回帰テスト (4/4 plans) — completed 2026-07-05
- [x] Phase 4: UI/UX 磨き込み + 既知バグ棚卸し (4/4 plans) — completed 2026-07-05

全フェーズの詳細・成功基準・プラン内訳は [milestones/v1.7.1-ROADMAP.md](milestones/v1.7.1-ROADMAP.md) を参照。
V171-* 全 17 要件 Complete（被覆 17/17・孤立要件なし）。締め前監査の 4 件（quick_task 記録マーカー欠落）は v1.4.0/v1.6.0 に続き受容済（STATE.md「Deferred Items」参照）。ShortcutsDialog の非致命的 follow-up（WR-01/WR-02）は v1.8.0 Phase 5 で解消予定。

</details>

### 🚧 v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化 (Active)

> **Goal:** 独立してきたコンポーネント（OCR・LLMプロバイダー・UI）のシナジーを高め、シームレスで高度なドキュメント処理・要約環境を構築する。
> **要件出典:** [REQUIREMENTS.md](REQUIREMENTS.md)（V180-* 全 26 件）
> **フェーズ採番:** マイルストーンごとに Phase 1 起点へリセット（プロジェクト方針）。
> **作業ブランチ:** `dev/v1.8.0`（main 直コミット禁止運用）

- [x] **Phase 1: 基盤分割（肥大モジュールリファクタリング）** - ocr_providers.py/llm_config.py のパッケージ分割 + `_SENSITIVE_KEYS` 中央レジストリ化 (completed 2026-07-14)
- [ ] **Phase 2: AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック）** - 名前付きテンプレート CRUD・全プロバイダ横断共有・明示設定型フォールバック（送信先確認再提示つき）
- [ ] **Phase 3: OCR実行エンジン抽出 + E2Eテスト** - ocr_dialog.py から OCRRunEngine を抽出し単一/バッチ OCR で共用可能化・OCR→サマリ E2E モックテスト整備
- [ ] **Phase 4: バッチ複数ファイルOCR** - 複数 PDF の D&D 一括投入・キュー進捗表示・ファイル単位失敗分離・全体/個別キャンセル・横断統合サマリ（単独フェーズ隔離）
- [ ] **Phase 5: 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正）** - 窓内サムネイル仮想化・thumb_cache LRU化・Blob リーク検出強化・WR-01/WR-02 解消
- [ ] **Phase 6: 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合）** - 再試行付き非モーダルトースト・スクロール/フォントスケーリング監査・開発履歴.md v1.7.0 表記整合

## Phase Details

> 以下は **アクティブな v1.8.0** のフェーズ詳細。過去マイルストーンの詳細は各アーカイブ（`milestones/*-ROADMAP.md`）を参照。

### Phase 1: 基盤分割（肥大モジュールリファクタリング）

**Goal**: 肥大化した OCR プロバイダー/LLM設定モジュールが責務別パッケージに分割され、APIキー秘匿の管理も中央レジストリ化されて、以降の機能追加の土台が整う。
**Depends on**: Nothing (first phase of milestone)
**Requirements**: V180-REFAC-01, V180-REFAC-02, V180-ROBUST-02
**Success Criteria** (what must be TRUE):

  1. `ocr_providers.py`（1537行）が責務別パッケージへ分割され、既存の `from pagefolio.ocr_providers import ...` 等の import が変更なく動作する
  2. `dialogs/llm_config.py`（1659行）が責務別パッケージへ分割され、既存の import パスが変更なく動作する
  3. `_SENSITIVE_KEYS` がプロバイダ→環境変数マッピングから生成される中央レジストリとなり、新プロバイダ追加時に手動リストへの追加漏れが構造的に起きなくなる
  4. 分割前に拡張された `test_imports.py` の後方互換 import テストと既存 pytest 全件がグリーンのまま維持される

**Plans**: 4/4 plans complete
**Wave 1**

- [x] 01-01-PLAN.md — テスト先行拡張（後方互換 import 安全網・Wave 0 必達）[Wave 1]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — ocr_providers パッケージ分割 + registry.py 新設 [Wave 2]

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — _SENSITIVE_KEYS 中央化 + D-09 参照統合（settings/ocr/ocr_dialog）[Wave 3]
- [x] 01-04-PLAN.md — llm_config Mixin パッケージ分割 + D-09 #4（sections env var）[Wave 3]

### Phase 2: AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック）

**Goal**: ユーザーが OCR/サマリ用プロンプトを名前付きテンプレートとして管理する UI と、プロバイダー障害時に安全な手動フォールバックで処理を継続する仕組みを LLM 設定ダイアログに追加する。
**Depends on**: Phase 1（ocr_providers/llm_config のパッケージ構造が固まってから UI を追加し手戻りを防ぐ）
**Requirements**: V180-TMPL-01, V180-TMPL-02, V180-TMPL-03, V180-TMPL-04, V180-TMPL-05, V180-FALL-01, V180-FALL-02, V180-FALL-03
**Success Criteria** (what must be TRUE):

  1. ユーザーは OCR カスタム/サマリプロンプトを名前付きテンプレートとして保存し、一覧から選択・削除・リネームできる（LLM 設定ダイアログ）
  2. 外部 md ファイル連動（v1.7.4 の `ocr_custom_prompt.md`/`ocr_summary_prompt.md`）はアクティブテンプレートのライブ編集として機能し、テンプレート切替時に書き戻し競合が起きない
  3. 保存したテンプレートは Claude/Gemini/LM Studio 等の全プロバイダで共通して選択・適用できる（`resolve_ocr_prompt` の解決順にテンプレート層が挿入され custom > provider別 > 汎用の既存解決順と両立する）
  4. ユーザーはフォールバック順（プロバイダ連鎖）を明示的に設定でき、未設定時はフォールバックが発生しない（安全側既定）
  5. OCR 実行が fatal エラーで停止すると、次のフォールバック候補（並列度・APIキー解決・レート制限設定を正しく引き継いだ状態）への切替が送信先確認ダイアログの再提示つきで提案され、ユーザー承認なしに別ベンダーへ自動送信されることはない

**Plans**: 4 plans
**UI hint**: yes

**Wave 1**

- [ ] 02-01-PLAN.md — テンプレート/フォールバック純ロジック基盤層（settings CRUD・3段解決・ocr_fallback.py）[Wave 1]

**Wave 2** *(blocked on Wave 1)*

- [ ] 02-02-PLAN.md — テンプレート管理 UI（sections.py テンプレートセクション + _apply 収集）[Wave 2]

**Wave 3** *(blocked on Wave 2)*

- [ ] 02-03-PLAN.md — フォールバック設定 UI（🔁セクション・トグル+Listbox+上下ボタン）[Wave 3]

**Wave 4** *(blocked on Wave 3)*

- [ ] 02-04-PLAN.md — フォールバックオーケストレーション（送信先確認再提示・provider 再構築・Pitfall 4 回避）[Wave 4]

### Phase 3: OCR実行エンジン抽出 + E2Eテスト

**Goal**: OCR 実行ロジックが単一ファイル OCR とバッチ OCR で共用できるエンジン（OCRRunEngine）として抽出され、OCR→サマリの一気通貫フローが E2E モックテストで保証される。
**Depends on**: Phase 2（数値順で直前のフェーズ完了後に着手。機能的な直接依存はなく、肥大モジュール分割の一連の作業として実施）
**Requirements**: V180-REFAC-03, V180-QA-01
**Success Criteria** (what must be TRUE):

  1. `ocr_dialog.py`（2154行）から producer-consumer 駆動部が `OCRRunEngine` として抽出され、単一ファイル OCR の実行・進捗・キャンセル・リトライがこれまでどおり動作する
  2. `OCRRunEngine` は独立したモジュールとして import 可能で、次フェーズのバッチ OCR から再利用できる構造になっている
  3. OCR→サマリの一気通貫フローが `OCRRunEngine`/`ocr_pipeline.py` 経由の E2E モックテストで検証され、実 API 非依存で pytest から実行できる

**Plans**: TBD

### Phase 4: バッチ複数ファイルOCR

**Goal**: 新設バッチ OCR ダイアログの UI で、ユーザーは複数の PDF ファイルを一括で OCR キューに投入し、進捗を確認しながら失敗ファイルを分離してバッチ全体を完了させ、統合サマリを得られる。
**Depends on**: Phase 3（OCRRunEngine 抽出直後に着手し、単一ファイル OCR と同じエンジンを再利用する）
**Requirements**: V180-BATCH-01, V180-BATCH-02, V180-BATCH-03, V180-BATCH-04, V180-BATCH-05
**Success Criteria** (what must be TRUE):

  1. ユーザーは複数 PDF ファイルを D&D で一括 OCR キューに投入できる
  2. キュー一覧でファイルごとの状態（待機/実行中/完了/失敗）と全体進捗を確認できる
  3. ファイル単位の失敗は分離され、残りのファイルの処理が継続する（`fitz.Document` のスレッド間共有はせず、ファイル間逐次処理で実現）
  4. ユーザーはバッチ全体、またはファイル単位で処理をキャンセルできる
  5. バッチ完了後、複数ファイル横断の統合サマリを生成でき、入力過大時は事前警告が表示される

**Plans**: TBD
**UI hint**: yes

### Phase 5: 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正）

**Goal**: 大量ページ PDF でもサムネイル描画が高速に保たれ、長時間運用でも Blob リークが検出可能で、ShortcutsDialog の UI 表示・入力衝突バグが解消される。
**Depends on**: Phase 4（大型機能のバッチ OCR が固まった後に、機能的に独立した堅牢性項目をまとめて仕上げる）
**Requirements**: V180-PERF-01, V180-PERF-02, V180-PERF-03, V180-ROBUST-01, V180-ROBUST-03
**Success Criteria** (what must be TRUE):

  1. 大量ページ PDF で窓内サムネイルが可視範囲のみ実体化され、既存 `pagination.py` 窓表示の外層契約（local↔global 変換）を変えずに描画が高速化される
  2. `thumb_cache` に LRU eviction が導入され、大量ページを開いてもメモリ使用が有界に保たれる
  3. `selected_pages` 全ページインデックス不変条件・D&D・窓表示との整合が回帰テストで保証される
  4. Blob ライフサイクルのリーク検出ロギングが強化され、Windows AV スキャンによる `os.unlink` の `PermissionError` 発生時も回帰テストでリークなしと確認できる
  5. ShortcutsDialog でキャプチャ対象を切り替えても前行の「キーを押してください」表示が残留せず、修飾キーなしの単キー登録が通常入力ウィジェットと衝突しなくなる

**Plans**: TBD
**UI hint**: yes

### Phase 6: 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合）

**Goal**: エラー時のリカバリー導線・UI の一貫性が磨き込まれ、開発履歴.md の版番表記が整合してマイルストーンを締められる。
**Depends on**: Phase 5（堅牢性強化後の最終仕上げとして UI 一貫性を監査する）
**Requirements**: V180-QA-02, V180-QA-03, V180-QA-04
**Success Criteria** (what must be TRUE):

  1. 軽微なエラー発生時、再試行アクション付きの非モーダルトースト通知が表示され自動消滅しない（全エラーの非モーダル化はせず、既存の重大エラー用ダイアログは維持される）
  2. スクロールパターン（Canvas+Scrollbar 等）とフォントスケーリングがダイアログ間で監査され、不一致箇所が是正される
  3. 開発履歴.md の v1.7.0 表記が実際のバージョン履歴と整合する（V16-D-04 残課題の解消）

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order (v1.8.0):**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase             | Milestone | Plans Complete | Status      | Completed  |
| ----------------- | --------- | --------------- | ----------- | ---------- |
| 1. Undo/Redo 修正 | v1.3.0    | 1/4 | In Progress|  |
| 2. プレビュー最適化とリファクタリング | v1.3.0 | 3/3 | Complete | 2026-06-03 |
| 3. API 整理と回帰テスト | v1.3.0 | 2/2 | Complete | 2026-06-03 |
| 4. プロバイダ抽象化 | v1.4.0 | 4/4 | Complete | 2026-06-06 |
| 5. Claude Provider + セキュリティ基盤 + プロバイダ選択 UI | v1.4.0 | 5/5 | Complete | 2026-06-07 |
| 6. Gemini Provider + 逐次レンダリング最適化 | v1.4.0 | 4/4 | Complete | 2026-06-07 |
| 7. Tesseract + PluginManager 拡張 + QA | v1.4.0 | 1/1 | Complete | 2026-06-14 |
| 1. PDF ページ操作・編集機能の拡充 | v1.5.0 | — | Complete | 2026-06-16 |
| 2. UI / UX とパフォーマンスの改善 | v1.5.0 | — | Complete | 2026-06-16 |
| 3. AI・OCR連携のさらなる進化 | v1.5.0 | — | Complete | 2026-06-16 |
| 4. テスト・品質保証 | v1.5.0 | — | Complete | 2026-06-16 |
| 1. 設定/UI 改善（OCR パラメータ一元化・スライダー配置） | v1.6.0 | 2/2 | Complete | 2026-06-18 |
| 2. 大量ページのページネーション表示 | v1.6.0 | 3/3 | Complete | 2026-06-19 |
| 3. 体感品質・回転プレビュー & OCR 堅牢性（プランA） | v1.6.0 | 3/3 | Complete | 2026-06-19 |
| 4. AI 出力品質（プランC） | v1.6.0 | 3/3 | Complete | 2026-06-20 |
| 1. APIキー入力欄（LLM設定への一元化） | v1.7.1 | 4/4 | Complete | 2026-07-04 |
| 2. OCR 磨き込み（レビュー残の現行照合と二重実装解消） | v1.7.1 | 4/4 | Complete | 2026-07-05 |
| 3. ページ操作磨き込み + v1.5.0 回帰テスト | v1.7.1 | 4/4 | Complete | 2026-07-05 |
| 4. UI/UX 磨き込み + 既知バグ棚卸し | v1.7.1 | 4/4 | Complete | 2026-07-05 |
| 1. 基盤分割（肥大モジュールリファクタリング） | v1.8.0 | 4/4 | Complete | 2026-07-14 |
| 2. AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック） | v1.8.0 | 0/4 | Not started | - |
| 3. OCR実行エンジン抽出 + E2Eテスト | v1.8.0 | TBD | Not started | - |
| 4. バッチ複数ファイルOCR | v1.8.0 | TBD | Not started | - |
| 5. 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正） | v1.8.0 | TBD | Not started | - |
| 6. 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合） | v1.8.0 | TBD | Not started | - |
