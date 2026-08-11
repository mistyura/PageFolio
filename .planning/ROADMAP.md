# Roadmap: PageFolio コード最適化

## Milestones

- ✅ **v1.3.0 コード最適化 MVP** — Phases 1-3 (shipped 2026-06-03) — [archive](milestones/v1.3.0-ROADMAP.md)
- ✅ **v1.4.0 OCR プロバイダ化 + クラウドAPI対応** — Phases 4-7 (shipped 2026-06-14) — [archive](milestones/v1.4.0-ROADMAP.md)
- ✅ **v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト** — Phases 1-4 (shipped 2026-06-16) — [archive](milestones/v1.5.0-ROADMAP.md)
- ✅ **v1.6.0 品質向上・AI強化・設定/UI改善** — Phases 1-4 (shipped 2026-06-20) — [archive](milestones/v1.6.0-ROADMAP.md)
- ✅ **v1.7.1 現機能ブラッシュアップ + APIキー入力欄** — Phases 1-4 (shipped 2026-07-05) — [archive](milestones/v1.7.1-ROADMAP.md)
- ✅ **v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化** — Phases 1-6 (shipped 2026-07-16) — [archive](milestones/v1.8.0-ROADMAP.md)
- 🚧 **v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加** — Phases 1-3 (active, started 2026-08-10)

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
V171-* 全 17 要件 Complete（被覆 17/17・孤立要件なし）。締め前監査の 4 件（quick_task 記録マーカー欠落）は v1.4.0/v1.6.0 に続き受容済（STATE.md「Deferred Items」参照）。ShortcutsDialog の非致命的 follow-up（WR-01/WR-02）は v1.8.0 Phase 5 で解消済み。

</details>

<details>
<summary>✅ v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化 (Phases 1-6) — SHIPPED 2026-07-16</summary>

- [x] Phase 1: 基盤分割（肥大モジュールリファクタリング） (4/4 plans) — completed 2026-07-14
- [x] Phase 2: AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック） (6/6 plans) — completed 2026-07-15
- [x] Phase 3: OCR実行エンジン抽出 + E2Eテスト (2/2 plans) — completed 2026-07-15
- [x] Phase 4: バッチ複数ファイルOCR (3/3 plans) — completed 2026-07-16
- [x] Phase 5: 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正） (4/4 plans) — completed 2026-07-16
- [x] Phase 6: 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合） (3/3 plans) — completed 2026-07-16

全フェーズの詳細・成功基準・プラン内訳は [milestones/v1.8.0-ROADMAP.md](milestones/v1.8.0-ROADMAP.md) を参照。
V180-* 全 26 要件 Complete（被覆 26/26・孤立要件なし）。クローズ前監査で検出した quick_task 4 件（v1.4.0 期の記録マーカー欠落）は本クローズで解消済み（`status: complete` 追記）。

</details>

### 🚧 v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加 (Active)

> **Goal:** 保存・編集・Undo の失敗時に「操作前の状態へ確実に戻る」安全性を確立し、設定 UI の Apply/Cancel 契約を整合させたうえで、OCR プロバイダ基盤を整理して OpenAI(ChatGPT) を既存プロバイダと同等に追加する。
> **要件出典:** [REQUIREMENTS.md](REQUIREMENTS.md)（V190-* 全 27 件）
> **フェーズ採番:** マイルストーンごとに Phase 1 起点へリセット（プロジェクト方針）。

- [x] **Phase 1: 保存・編集・設定の安全性是正（失敗時ロールバック担保）** - 保存3経路の暗号化維持・OCR OFF全経路一貫化・複数ファイル挿入/ページ複製・設定UIのApply/Cancel契約・Undo/Redo復元失敗時のスタック保護で「失敗時は操作前状態へ戻る」を確立 (completed 2026-08-11)
- [ ] **Phase 2: OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加** - プロバイダメタデータを単一情報源（catalog）へ一元化し、その上に OpenAI(ChatGPT) を既存5プロバイダと同等の安全境界でOCR/バッチOCR/フォールバックへ追加
- [ ] **Phase 3: 品質保証・リリースゲート** - Tkinter 実行環境を修復してGUIテスト含む全テストを完走させ、保存トースト再試行時の上書き確認再表示とhuman-verify/UATを正式実施してリリース判定を固める

## Phase Details

> 以下は **アクティブな v1.9.0** のフェーズ詳細。過去マイルストーンの詳細は各アーカイブ（`milestones/*-ROADMAP.md`）を参照。

### Phase 1: 保存・編集・設定の安全性是正（失敗時ロールバック担保）

**Goal**: 保存・複数ファイル挿入・ページ複製・設定 UI 操作・Undo/Redo のいずれかが失敗しても、Document・Undo 履歴・外部ファイルが確実に操作前の状態へ戻り、OCR OFF が通常 OCR・バッチ OCR・プラグイン経路すべてで一貫した意味を持つ。
**Depends on**: Nothing (first phase of milestone)
**Requirements**: V190-SAFE-01, V190-SAFE-02, V190-SAFE-03, V190-SAFE-04, V190-SAFE-05, V190-CFG-01, V190-CFG-02, V190-UNDO-01, V190-UNDO-02
**Success Criteria** (what must be TRUE):

  1. パスワード保護 PDF を「保存」「名前を付けて保存」「上書き（インクリメンタル保存失敗時のフォールバック）」のいずれで実行しても暗号化が維持され、保存後の `pdf_has_password` 表示が実ファイルと一致する（V190-SAFE-01/02）
  2. OCR が OFF のとき、通常 OCR・バッチ OCR・プラグイン経由のいずれからも `off` はプロバイダ生成可能な値として扱われず、バッチ OCR の起動・実行開始ができない（V190-SAFE-03）
  3. 複数ファイル挿入が途中のファイルで失敗しても、ページ数と Undo スタックが操作前と一致し、挿入元 Document は例外発生時も必ずクローズされる。ページ複製が失敗した場合も既存ページと Undo スタックが変化しない（V190-SAFE-04/05）
  4. LLM 設定 UI（LLMConfigDialog）を Cancel しても外部プロンプトファイル（`ocr_custom_prompt.md`/`ocr_summary_prompt.md`）は変更されず、選択済みテンプレートを編集した状態で別テンプレートへ切り替えると外部ファイル連動の有無にかかわらず未保存確認が表示される（V190-CFG-01/02）
  5. Undo/Redo の復元処理が失敗した場合、対象状態がスタックへ戻され履歴が失われず Document が部分変更のまま残らない。`duplicate`/`merge`/`merge_resize` の各 op で do→undo→redo→undo の4手往復回帰テストがページ構成の一致を担保する（V190-UNDO-01/02）

**Plans**: 7/7 plans executed（6 waves・01-06 / 01-07 は検証ギャップ是正プラン。6/7 executed）

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — 保存3経路+縮小保存の暗号化維持と `pdf_has_password` 論理導出（tracer・V190-SAFE-01/02）

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — OCR OFF の全経路一貫化（`OCRDisabledError`・メニュー disabled 化・実行開始/再生成ガード・V190-SAFE-03）
- [x] 01-03-PLAN.md — LLM 設定の Apply/Cancel 契約整合（外部プロンプトファイル書き込みの Apply 一本化・未保存判定の単一経路化・V190-CFG-01/02）

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-04-PLAN.md — 複数ファイル挿入のロールバック・ページ複製の Undo 後置・Undo/Redo 復元失敗時の state 保全（V190-SAFE-04/05・V190-UNDO-01）

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-05-PLAN.md — `duplicate`/`merge`/`merge_resize` の4手往復回帰テストと D-12 棚卸し（V190-UNDO-02）

**Wave 5** *(blocked on Wave 4 completion・gap closure)*

- [x] 01-06-PLAN.md — 部分失敗→再試行後の逆デルタ縮小によるサイレントなページ破損の是正（7 op の逆デルタ蓄積方式・5手往復回帰テスト・V190-UNDO-01 / 01-VERIFICATION.md gap）

**Wave 6** *(blocked on Wave 5 completion・gap closure)*

- [x] 01-07-PLAN.md — page_edit の 2 段階 mutation 中間失敗によるページ内容喪失と隣接ページ巻き添えの是正（CR-02 ロールバック＋専用警告・WR-04 一時 Document の finally 保護・WR-05 insert base op の部分適用保護・V190-UNDO-01 / 01-VERIFICATION.md gap）

**UI hint**: yes

### Phase 2: OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加

**Goal**: プロバイダメタデータ（キー・表示名・クラウド種別・環境変数・既定モデル・送信先・フォールバック可否）が単一の情報源（catalog）から解決される基盤の上で、ユーザーは OpenAI(ChatGPT) を既存5プロバイダと同等の安全境界（セッション限定キー・送信先確認・コスト確認・明示設定型フォールバック）で OCR・バッチ OCR に利用できる。
**Depends on**: Phase 1（V190-SAFE-03 で `off` がプロバイダ生成不可化されてから着手。失敗時ロールバックの安全網が固まっている前提で新プロバイダを追加する）
**Requirements**: V190-CAT-01, V190-CAT-02, V190-OAI-01, V190-OAI-02, V190-OAI-03, V190-OAI-04, V190-OAI-05, V190-OAI-06, V190-OAI-07, V190-OAI-08, V190-OAI-09, V190-OAI-10, V190-OAI-11, V190-OAI-12, V190-OAI-13
**Success Criteria** (what must be TRUE):

  1. プロバイダのキー・表示名・クラウド種別・環境変数・既定モデル・送信先ホスト・フォールバック可否が単一の情報源から解決され、新プロバイダ追加時の変更面が1箇所に閉じる。`pagefolio/ocr_providers/registry.py` の独立性制約（Python 標準ライブラリのみに依存し pagefolio 内部モジュールを import しない）は維持され循環 import が発生しない（V190-CAT-01/02）
  2. ユーザーは OCR プロバイダとして OpenAI(ChatGPT) を選択し、LLM 設定 UI でセッション限定 API キーを入力できる（`pagefolio_settings.json` に非永続・`_SENSITIVE_KEYS` ガード）。モデル一覧を API から取得でき、取得失敗時は静的フォールバック一覧から選択できる（V190-OAI-01/02/03）
  3. OpenAI で OCR・バッチ OCR を実行する前に、送信先ホストを明示した確認ダイアログとコスト確認ダイアログが表示される（クラウド判定・送信先表示を含む）（V190-OAI-04/05/06）
  4. ユーザーは OpenAI をフォールバック候補として設定でき、発動時に送信先確認が再提示される。画像 detail レベル（low/high/auto）・reasoning effort 相当パラメータ（対応モデル選択時のみ有効化）・organization/project ID（指定時のみヘッダ付与）を設定でき、永続化される（V190-OAI-07/08/09/10）
  5. OpenAI プロバイダは `urllib.request` 直叩きで実装され新規 pip 依存を追加しない。モデル別のパラメータ非互換（`max_completion_tokens` を要するモデル・`temperature` を拒否する o-series）が正しく分岐しエラーにならず、429/5xx 応答に既存の指数バックオフ・`Retry-After` 尊重リトライ基盤（`ocr_providers/errors.py`）が適用される（V190-OAI-11/12/13）

**Plans**: 4 plans（4 waves・全 wave 直列。02-01 は D-09 + 能力マトリクス確定の checkpoint:decision、02-04 は 3 分割した実機 human-verify を含む。02-REVIEWS.md 反映済み）

Plans:
**Wave 1**

- [ ] 02-01-PLAN.md — 能力マトリクス確定 + カタログ基盤 + OpenAI プロバイダ + build_provider の縦スライス（tracer・V190-CAT-01/02・V190-OAI-02/11/12/13）

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 02-02-PLAN.md — OCR / バッチ OCR ダイアログの catalog 移行と OpenAI 安全境界（送信先確認・コスト確認・単価プロヴェナンス・APIキー欠落・V190-CAT-01・V190-OAI-04/05/06）

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 02-03-PLAN.md — LLM 設定 UI の OpenAI セクション・セッション限定キー・モデル一覧取得（確認済み優先の並び替え）とプロバイダ一覧の catalog 化（V190-CAT-01・V190-OAI-01/02/03）

**Wave 4** *(blocked on Wave 2/3 completion)*

- [ ] 02-04-PLAN.md — OpenAI 固有パラメータ UI（detail / effort 許可リスト / org / project）・フォールバック候補・ドキュメント・実機確認 3 分割（V190-OAI-07/08/09/10）

**UI hint**: yes

### Phase 3: 品質保証・リリースゲート

**Goal**: Python 3.14.6 環境の Tkinter 実行問題が解消されて GUI テストを含む全テストが完走し、保存トースト再試行時の上書き確認が再表示され、実機目視による human-verify/UAT が正式に実施・記録されてリリース判定ができる。
**Depends on**: Phase 2（新設 OpenAI プロバイダ・catalog リファクタを含めた全コード変更が完了してから全テスト完走ゲートと human-verify を実施する）
**Requirements**: V190-QA-01, V190-QA-02, V190-QA-03
**Success Criteria** (what must be TRUE):

  1. Python 3.14.6 での GUI テストのセットアップエラー（Tkinter 実行環境問題）が切り分け・修復され、GUI テストを含む全テストスイートが完走する。これがリリースの前提条件（ゲート）として扱われる（V190-QA-01）
  2. 保存トーストの再試行を実行すると、上書き確認ダイアログが再表示される（V190-QA-02）
  3. 実機目視による human-verify/UAT が正式に実施され、結果が記録される（v1.4.0/v1.6.0/v1.7.1 で一旦 pass とした項目の正式消化を含む）（V190-QA-03）

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order (v1.9.0):**
Phases execute in numeric order: 1 → 2 → 3

| Phase             | Milestone | Plans Complete | Status      | Completed  |
| ----------------- | --------- | --------------- | ----------- | ---------- |
| 1. Undo/Redo 修正 | v1.3.0    | 7/7 | Complete    | 2026-08-11 |
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
| 2. AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック） | v1.8.0 | 6/6 | Complete | 2026-07-15 |
| 3. OCR実行エンジン抽出 + E2Eテスト | v1.8.0 | 2/2 | Complete | 2026-07-15 |
| 4. バッチ複数ファイルOCR | v1.8.0 | 3/3 | Complete | 2026-07-16 |
| 5. 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正） | v1.8.0 | 4/4 | Complete | 2026-07-16 |
| 6. 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合） | v1.8.0 | 3/3 | Complete | 2026-07-16 |
| 1. 保存・編集・設定の安全性是正（失敗時ロールバック担保） | v1.9.0 | 5/6 | Gap closure planned | - |
| 2. OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加 | v1.9.0 | - | Not started | - |
| 3. 品質保証・リリースゲート | v1.9.0 | - | Not started | - |
