# Roadmap: PageFolio コード最適化

## Milestones

- ✅ **v1.3.0 コード最適化 MVP** — Phases 1-3 (shipped 2026-06-03) — [archive](milestones/v1.3.0-ROADMAP.md)
- ✅ **v1.4.0 OCR プロバイダ化 + クラウドAPI対応** — Phases 4-7 (shipped 2026-06-14) — [archive](milestones/v1.4.0-ROADMAP.md)
- ✅ **v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト** — Phases 1-4 (shipped 2026-06-16) — [archive](milestones/v1.5.0-ROADMAP.md)
- 🚧 **v1.6.0 品質向上・AI強化・設定/UI改善** — Phases 1-4 (active, started 2026-06-18)

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

### 🚧 v1.6.0 品質向上・AI強化・設定/UI改善 (Active)

> **Goal:** 体感品質（回転プレビュー即時反映・エラーハンドリング UX）と AI 出力品質（Markdown 整形・プロバイダ別プロンプト最適化）を底上げし、設定の二重化を解消して大量ページ対応で UI を整える。
> **要件出典:** [REQUIREMENTS.md](REQUIREMENTS.md)（V16-* 全 9 件）/ [NEXT-MILESTONE-HANDOFF.md](NEXT-MILESTONE-HANDOFF.md)

- [x] **Phase 1: 設定/UI 改善（OCR パラメータ一元化・スライダー配置）** — S1 二重設定の解消 + S2 サムネイルスライダーの常時可視化 (completed 2026-06-18)
- [x] **Phase 2: 大量ページのページネーション表示** — S3 サムネイル一覧をページ単位で区切り、D&D・複数選択をインデックス整合 (completed 2026-06-19)
- [x] **Phase 3: 体感品質・回転プレビュー & OCR 堅牢性（プランA）** — H1 回転即時反映 + H2 キー秘匿監査 + H5 実機検証 + M1 エラー UX 磨き (completed 2026-06-19)
- [ ] **Phase 4: AI 出力品質（プランC）** — M3 Markdown 整形表示 + M4 プロバイダ別プロンプト最適化

## Phase Details

> 以下は **アクティブな v1.6.0** のフェーズ詳細。過去マイルストーンの詳細は各アーカイブ（`milestones/*-ROADMAP.md`）を参照。

### Phase 1: 設定/UI 改善（OCR パラメータ一元化・スライダー配置）

**Goal**: OCR パラメータ設定の二重化を解消し、ユーザーが設定を一意に解決できる。加えてサムネイルサイズスライダーが左ペインを縮小しても常に見える。
**Depends on**: Nothing (first phase of milestone)
**Requirements**: V16-UI-01, V16-UI-02
**Success Criteria** (what must be TRUE):

  1. ユーザーは OCR パラメータ（タイムアウト・並列度・リトライ等）を「LLM設定」画面のみで設定でき、その値が一意に OCR 実行へ反映される
  2. OCR テキスト抽出画面のパラメータ入力 UI が廃止または読み取り専用化され、「LLM設定」側の値と矛盾しない（どちらが効くか分からない状態が解消されている）
  3. サムネイルサイズ変更スライダーが、左ペインを縮小しても常に見える位置（「全選択／解除」付近または「ページ一覧」ラベル横）に表示される
  4. スライダーでサムネイルサイズを変更でき、機能は従来どおり動作する

**Plans**: 2/2 plans complete

  - [x] 01-01-PLAN.md — V16-UI-01: OCRDialog 数値パラメータの読み取り専用化 + LLM 設定への編集導線一元化・全プロバイダ共通ライブ同期 — completed 2026-06-18
  - [x] 01-02-PLAN.md — V16-UI-02: サムネイルスライダーを独立全幅行へ移設 + v1.6.0 バージョン同期

**UI hint**: yes

### Phase 2: 大量ページのページネーション表示

**Goal**: 大量ページの PDF でもサムネイル一覧が高速に表示でき、ページング下でも D&D 並び替え・複数選択が全ページインデックスと整合する。
**Depends on**: Phase 1
**Requirements**: V16-UI-03
**Success Criteria** (what must be TRUE):

  1. ユーザーは大量ページの PDF でサムネイル一覧をページ単位（既定 20 ページ）で区切って表示できる
  2. ユーザーは表示件数を変更でき、その値が `pagefolio_settings.json` に永続化されて次回起動時に復元される
  3. ページング表示中でも D&D による並び替えが全ページインデックスと整合し、意図したページが正しい位置へ移動する
  4. ページング表示中でも複数選択（`selected_pages`）が全ページインデックスを正しく指し、ページ操作が選択どおりに適用される

**Plans**: 3/3 plans complete
**Wave 1**

  - [x] 02-01-PLAN.md — V16-UI-03: 窓計算・local↔global 変換の純ロジック層（pagination.py）新設 + 全境界値の純ロジック unit テスト（Wave 0 基盤）

**Wave 2** *(blocked on Wave 1 completion)*

  - [x] 02-02-PLAN.md — V16-UI-03: 表示件数 thumb_page_size 永続化（既定 20・クランプ）+ 窓状態属性 + サムネイル描画/選択照合の窓範囲化

**Wave 3** *(blocked on Wave 2 completion)*

  - [x] 02-03-PLAN.md — V16-UI-03: ナビ/件数フッター UI（◀ ▶ ＋ 範囲ラベル ＋ Spinbox）+ D&D local→global 換算 + current_page 窓追従（D-11）+ i18n/版番同期

**UI hint**: yes

### Phase 3: 体感品質・回転プレビュー & OCR 堅牢性（プランA）

**Goal**: ページ回転がプレビューへ即時反映され、OCR のキー秘匿・レート制限/トークン超過時の挙動が監査・検証され、エラー時にユーザーが次のアクションを理解できる。
**Depends on**: Phase 2
**Requirements**: V16-QUAL-01, V16-QUAL-02, V16-QUAL-03, V16-QUAL-04
**Success Criteria** (what must be TRUE):

  1. ユーザーがページを回転すると、再読込やページ切替を待たずにプレビュー表示へ即時反映される
  2. API キーが設定ファイル・ソースコード・ログに平文露出していないことが監査で再確認され、`_SENSITIVE_KEYS` ガード・環境変数/セッションメモリ限定の挙動が回帰テストで担保されている
  3. max_tokens クランプと 429/レート制限リトライが実 API（または実機相当の検証手順）で期待どおり動作することが検証され、結果が記録されている
  4. レート制限・トークン超過・応答途切れ時に、ユーザーが状況と次のアクション（待機・再試行・設定変更等）を理解できるエラーメッセージ／UX が提示される

**Plans**: 3/3 plans complete
**Wave 1** *(並行実行可・files_modified 重複ゼロ)*

  - [x] 03-01-PLAN.md — V16-QUAL-01: H1 回転プレビュー即時反映（実機 debug で真因特定 → 原因除去・回転 w/h 単体テスト・viewer/page_ops に閉じる）
  - [x] 03-02-PLAN.md — V16-QUAL-04: OCR 堅牢性（ocr_image_ex 段階導入で stop_reason/finishReason 途切れ検出＋部分テキスト保持・待機秒数 {sec} 文言・ja/en 同一 LANG キー）

**Wave 2** *(blocked on 03-02: lang.py 確定後の parity 基準)*

  - [x] 03-03-PLAN.md — V16-QUAL-02/03: H2 キー秘匿監査回帰テスト（caplog 値非出力・ソース実キースキャン・LANG parity）＋ H5 実 API 検証チェックリスト（D-08）＋ 3 経路キー秘匿監査文書（D-10）・pagefolio/ ソース無改変

**UI hint**: yes

### Phase 4: AI 出力品質（プランC）

**Goal**: OCR 結果が Markdown として読みやすく整形表示され、プロバイダ別に最適化されたプロンプトで出力品質が引き出される（既存カスタムプロンプト機構と両立）。
**Depends on**: Phase 3
**Requirements**: V16-AI-01, V16-AI-02
**Success Criteria** (what must be TRUE):

  1. ユーザーは OCR 結果ビューア（`OCRDialog`）で `markdown` プリセット出力を整形表示で閲覧でき、見出し・箇条書き等がプレーンテキストより読みやすく提示される
  2. Claude では XML タグ構造、Gemini では明示指示など、プロバイダ別に最適化されたプロンプトテンプレートで OCR が実行される
  3. プロバイダ別プロンプト最適化が、既存のカスタムプロンプト機構（v1.5.0）と矛盾なく両立し、ユーザーのカスタムプロンプトが引き続き機能する

**Plans**: 2/3 plans executed

**Wave 1** *(並行実行可・files_modified 重複ゼロ — 純ロジック層)*

  - [x] 04-01-PLAN.md — V16-AI-01: Markdown→(行種別, インライン span) 変換の純関数層 `pagefolio/md_render.py`（`parse_markdown`）新設 + `tests/test_md_render.py`（Tk 非生成 unit）
  - [x] 04-02-PLAN.md — V16-AI-02: プロバイダ別プロンプト解決の純関数層（`ocr.py` に `PROVIDER_OCR_PROMPTS`＝Claude=XML/Gemini=明示 + `resolve_ocr_prompt`）+ `tests/test_provider_ui.py` 拡張（カスタム上書き温存・LMStudio/Tesseract フォールバック）

**Wave 2** *(blocked on Wave 1 — 配線/UI)*

  - [ ] 04-03-PLAN.md — V16-AI-01/02: `OCRDialog` 配線（`_on_run` を `resolve_ocr_prompt` へ・`_build` に md_* タグ・`_render_results_ordered` に `preset=="markdown"` 整形描画分岐）+ コピー/保存は raw 維持 + human-verify

**UI hint**: yes

## Progress

**Execution Order (v1.6.0):**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Undo/Redo 修正 | v1.3.0 | 2/2 | Complete    | 2026-06-03 |
| 2. プレビュー最適化とリファクタリング | v1.3.0 | 2/3 | In Progress|  |
| 3. API 整理と回帰テスト | v1.3.0 | 2/2 | Complete | 2026-06-03 |
| 4. プロバイダ抽象化 | v1.4.0 | 1/3 | In Progress|  |
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
| 4. AI 出力品質（プランC） | v1.6.0 | 2/3 | In Progress | - |
