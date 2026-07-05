# Roadmap: PageFolio コード最適化

## Milestones

- ✅ **v1.3.0 コード最適化 MVP** — Phases 1-3 (shipped 2026-06-03) — [archive](milestones/v1.3.0-ROADMAP.md)
- ✅ **v1.4.0 OCR プロバイダ化 + クラウドAPI対応** — Phases 4-7 (shipped 2026-06-14) — [archive](milestones/v1.4.0-ROADMAP.md)
- ✅ **v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト** — Phases 1-4 (shipped 2026-06-16) — [archive](milestones/v1.5.0-ROADMAP.md)
- ✅ **v1.6.0 品質向上・AI強化・設定/UI改善** — Phases 1-4 (shipped 2026-06-20) — [archive](milestones/v1.6.0-ROADMAP.md)
- 🚧 **v1.7.1 現機能ブラッシュアップ + APIキー入力欄** — Phases 1-4 (active, started 2026-07-04)

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

### 🚧 v1.7.1 現機能ブラッシュアップ + APIキー入力欄 (Active)

> **Goal:** 既存機能（UI/UX・OCR・ページ操作）を磨き込み、テスト・安定性を底上げする。あわせて LLM 設定ダイアログにセッション限定の APIキー入力欄を追加し、キー設定導線を一元化する。
> **要件出典:** [REQUIREMENTS.md](REQUIREMENTS.md)（V171-* 全 17 件）
> **フェーズ採番:** マイルストーンごとに Phase 1 起点へリセット（プロジェクト方針）。

- [x] **Phase 1: APIキー入力欄（LLM設定への一元化）** - クラウド3種のキー入力欄追加・入力値優先の解決順反転・OCRDialog 側入力欄の撤去・RunPod のセッションキー対応 + その回帰テスト (completed 2026-07-04)
- [x] **Phase 2: OCR 磨き込み（レビュー残の現行照合と二重実装解消）** - L-6 小物一括解消・tesseract_lang 尊重・プラグイン registry 堅牢化・producer-consumer 一本化（L-1 は独立プランへ隔離） (completed 2026-07-05)
- [x] **Phase 3: ページ操作磨き込み + v1.5.0 回帰テスト** - 画像透かし対応・黒塗り/モザイク・回転/トリミングの棚卸し改善・v1.5.0 新機能の回帰テスト整備 (completed 2026-07-05)
- [ ] **Phase 4: UI/UX 磨き込み + 既知バグ棚卸し** - ショートカット GUI 編集・文言/エラー一貫性監査・ダイアログ整理・既知軽微バグの棚卸しと解消

## Phase Details

> 以下は **アクティブな v1.7.1** のフェーズ詳細。過去マイルストーンの詳細は各アーカイブ（`milestones/*-ROADMAP.md`）を参照。
> L-1〜L-6 は v1.4.0 期レビュー由来のため、各フェーズの計画時に **現行コードとの照合**を行い、v1.6.0〜v1.7.0 で解消済みの項目を除いた「活き残り」のみを対象とする。

### Phase 1: APIキー入力欄（LLM設定への一元化）

**Goal**: ユーザーは Claude / Gemini / RunPod の APIキーを LLM 設定ダイアログで一元的に入力でき、キーは「入力値 → 環境変数」の優先順で解決される（セッション限定・非永続）。
**Depends on**: Nothing (first phase of milestone)
**Requirements**: V171-KEY-01, V171-KEY-02, V171-KEY-03, V171-KEY-04, V171-TEST-02
**Success Criteria** (what must be TRUE):

  1. ユーザーは LLM設定ダイアログで Claude / Gemini / RunPod の APIキーを入力でき、その入力キーでクラウド OCR を実行できる（キーは `pagefolio_settings.json` に保存されない）
  2. キー解決は「ダイアログ入力値 → 環境変数」の優先順で行われ（現行の環境変数優先から反転）、両方未設定でクラウド OCR を開始すると明示的なエラーが表示される
  3. OCRDialog に旧セッションキー入力欄が存在せず、キー設定の導線が LLM設定ダイアログに一元化されている（OCR 実行フローは従来どおり動作する）
  4. RunPod も `_session_api_keys` のセッションキー機構で扱え、環境変数 `RUNPOD_API_KEY` なしでも入力キーだけで OCR を実行できる
  5. 優先順解決（入力値→環境変数→エラー）と `_SENSITIVE_KEYS` 非保存ガードの回帰テストが pytest でグリーン（V171-TEST-02）

**Plans**: 4/4 plans complete
**Wave 1**

- [x] 01-01-PLAN.md — キー解決順の反転（入力値→環境変数）+ 解決系テスト（claude/gemini 書き換え・RunPod 新設）+ 新規/更新 LANG 文言（Wave 1）

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — LLMConfigDialog に3プロバイダの APIキー入力欄・トグル・注記追加 + 2経路配線（SettingsDialog 側）+ ライブ値モデル取得 + 非流入/格納/スロット回帰テスト（Wave 2）

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — OCRDialog 旧セッションキー UI/ヘルパー撤去 + 実行前ゲート _check_cloud_api_key 置換 + _open_llm_config 配線 + 後継テスト（Wave 3）

**Wave 4** *(gap closure — 01-VERIFICATION.md CR-01)*

- [x] 01-04-PLAN.md — _confirm_cost / _confirm_summary_cost に runpod 分岐追加（send-to ホスト/モデルの誤開示 CR-01 解消）+ _provider_display_name の runpod 表示名（WR-02）+ 送信先開示の回帰テスト（Wave 4）

**UI hint**: yes

### Phase 2: OCR 磨き込み（レビュー残の現行照合と二重実装解消）

**Goal**: v1.4.0 期レビュー残（L-1〜L-4・L-6）が現行コード照合の上で解消され、OCR のプロバイダ/プラグイン基盤と実行パイプラインが堅牢・単一実装になる。
**Depends on**: Phase 1（ocr.py のキー解決・OCRDialog の UI 確定後に着手し手戻りを防ぐ）
**Requirements**: V171-OCR-01, V171-OCR-02, V171-OCR-03, V171-OCR-04
**Success Criteria** (what must be TRUE):

  1. L-6 小物（プログレス 100% 問題・URL スキーム検証・モデル名エスケープ・`_fetch_models`/`_test_connection` 重複解消 等）が現行コード照合で活き残りを確定した上で一括解消され、OCR 実行・接続テスト・モデル取得が従来どおり動作する
  2. Tesseract OCR が `tesseract_lang` 設定の言語で実行され、指定言語データが利用不可の場合は自動フォールバックしてユーザーにその旨が伝わる（L-4）
  3. プラグイン OCR プロバイダの重複名登録が警告され、プラグイン unload 時に登録解除され、登録済みプロバイダへ公開アクセサで到達できる（L-2/L-3）
  4. producer-consumer ロジックが単一実装に一本化され（`ocr.py` 未使用ヘルパーと `ocr_dialog.py` 独自実装の二重実装解消・L-1）、OCR の並列実行・キャンセル・進捗・リトライが回帰なく動作する（既存 OCR テスト群がグリーン）

**Plans**: 4/4 plans complete

**Wave 1**

- [x] 02-01-PLAN.md — プラグイン OCR registry 堅牢化（重複名警告/拒否・unload 登録解除・公開アクセサ get_ocr_provider/list_ocr_providers・私有アクセス置換）(V171-OCR-03)

**Wave 2** *(blocked on Wave 1)*

- [x] 02-02-PLAN.md — Tesseract 言語尊重 + 段階的縮退フォールバック（プロバイダ生成時再検出・OCRDialog 非モーダル注記）(V171-OCR-02)

**Wave 3** *(blocked on Wave 2)*

- [x] 02-03-PLAN.md — L-6 小物一括解消（URL スキーム検証3プロバイダ・Gemini quote・エラー body 切り詰め・Claude list_models ページネーション・_fetch_models/_test_connection 重複解消・off 切替ボタン同期）(V171-OCR-01)

**Wave 4** *(blocked on Wave 3・高リスク隔離プラン)*

- [x] 02-04-PLAN.md — producer-consumer 一本化（新設 ocr_pipeline.py・run_with_bounded_buffer 削除・L-6a/L-6g/L-6h 吸収・回帰ゲート）(V171-OCR-04)

> **リスク注記:** V171-OCR-04（L-1 一本化）は `ocr.py`/`ocr_dialog.py` を横断する高リスク項目のため、**フェーズ内の独立プラン 02-04 へ隔離**し、他の OCR 磨き込みプラン（02-01/02-02/02-03）完了後の Wave 4 で単独実行・単独検証する。

### Phase 3: ページ操作磨き込み + v1.5.0 回帰テスト

**Goal**: ユーザーは画像（ロゴ）を透かしとして追加でき、黒塗り/モザイク・回転/トリミングが棚卸しで確定した改善により使いやすくなる。v1.5.0 新機能（同じページ操作面）の回帰テストが整備される。
**Depends on**: Phase 2
**Requirements**: V171-PAGE-01, V171-PAGE-02, V171-PAGE-03, V171-TEST-01
**Success Criteria** (what must be TRUE):

  1. ユーザーは画像ファイル（ロゴ等）を透かしとしてページに追加でき、Undo で元に戻せる（v1.5.0 テキストのみ制限の解除）
  2. 黒塗り/モザイクについて棚卸しで確定した改善項目が反映され、改善前より操作しやすい（棚卸し結果と対応は計画時に確定・記録される）
  3. 回転/トリミングについて棚卸しで確定した改善項目が反映される（同上）
  4. v1.5.0 新機能（白紙挿入・テキスト透かし・ページ番号・TOC 保持・D&D 指定位置挿入・ショートカット動的読込）の回帰テストが pytest に整備されグリーン（V171-TEST-01）

**Plans**: 4/4 plans complete

**Wave 1**

- [x] 03-01-PLAN.md — 画像透かし（PNG/JPEG・中央/幅50%/50%透過・page_edit undo）(V171-PAGE-01・D-01〜D-04)
- [x] 03-02-PLAN.md — v1.5.0 回帰テスト（TOC 保持・D&D 挿入位置・ショートカット純関数抽出＋内容検証追加）(V171-TEST-01・D-13〜D-16)

**Wave 2** *(blocked on 03-01)*

- [x] 03-03-PLAN.md — 回転/トリミング棚卸し＋回転座標共通ヘルパー基盤（_derotate_rect・矢印微調整・mm 指定・crop_info mm 表示）(V171-PAGE-03・D-08/D-09/D-10/D-11/D-12)

**Wave 3** *(blocked on 03-03)*

- [x] 03-04-PLAN.md — 黒塗り/モザイク棚卸し（連続適用・粒度スライダー・複数矩形一括・回転座標統合）(V171-PAGE-02・D-05/D-06/D-07/D-08)

**UI hint**: yes

### Phase 4: UI/UX 磨き込み + 既知バグ棚卸し

**Goal**: ユーザーはショートカットを GUI で編集でき、エラー表示・文言・ダイアログ配置の一貫性が監査・修正され、既知軽微バグの活き残りが解消されてマイルストーンを締められる。
**Depends on**: Phase 3（ショートカット読込の回帰テスト整備後に GUI 化へ着手）
**Requirements**: V171-UIUX-01, V171-UIUX-02, V171-UIUX-03, V171-TEST-03
**Success Criteria** (what must be TRUE):

  1. ユーザーはショートカットを設定ダイアログの GUI で編集でき、変更が保存・反映される（`pagefolio_settings.json` の直接編集が不要になる）
  2. エラー表示・文言の一貫性が監査され、ja/en 辞書の欠落・未使用キーが解消されている（L-5 吸収・LANG parity テストがグリーン）
  3. SettingsDialog / LLMConfigDialog の項目配置・セクションが整理され、既存の設定機能（テーマ・フォント・LLM 設定等）が回帰なく動作する
  4. 既知軽微バグの棚卸しリストが現行コード照合で確定し（L-6 と重複しない範囲）、活き残りが解消・テストで担保される（V171-TEST-03）

**Plans**: 2/4 plans executed

**Wave 1**

- [x] 04-01-PLAN.md — ショートカット純関数基盤（keysym 変換/重複検出/表示変換）+ `_bind_shortcuts` 抽出 + 純関数テスト（V171-UIUX-01・D-04/D-05/D-07）

**Wave 2** *(blocked on Wave 1)*

- [x] 04-02-PLAN.md — ShortcutsDialog 新設（実キーキャプチャ/重複拒否/無効化/差分保存/即時再バインド）+ SettingsDialog 3セクション再編・🔍→⚙ 改称（V171-UIUX-01/03・D-01/D-02/D-03/D-06/D-08/D-16・C8）

**Wave 3** *(blocked on Wave 2)*

- [ ] 04-03-PLAN.md — LLMConfig 共通/固有グルーピング + ネスト適用トランザクション化 + Ollama 重複解消（V171-UIUX-03/TEST-03・D-14/D-15・C2/C4/C5）

**Wave 4** *(blocked on Wave 3)*

- [ ] 04-04-PLAN.md — 文言/エラー監査（viewer ハードコード i18n 化・分割エラー messagebox 統一・未使用9キー削除・D-11 検出テスト常設）（V171-UIUX-02・D-09/D-11/D-12・C6/C7）

**UI hint**: yes

## Progress

**Execution Order (v1.7.1):**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Undo/Redo 修正 | v1.3.0 | 4/4 | Complete    | 2026-07-04 |
| 2. プレビュー最適化とリファクタリング | v1.3.0 | 3/3 | Complete | 2026-06-03 |
| 3. API 整理と回帰テスト | v1.3.0 | 4/4 | Complete    | 2026-07-05 |
| 4. プロバイダ抽象化 | v1.4.0 | 2/4 | In Progress|  |
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
| 1. APIキー入力欄（LLM設定への一元化） | v1.7.1 | 0/3 | Not started | - |
| 2. OCR 磨き込み（レビュー残の現行照合と二重実装解消） | v1.7.1 | 4/4 | Complete | 2026-07-05 |
| 3. ページ操作磨き込み + v1.5.0 回帰テスト | v1.7.1 | 0/4 | Not started | - |
| 4. UI/UX 磨き込み + 既知バグ棚卸し | v1.7.1 | 1/4 | In Progress | - |
