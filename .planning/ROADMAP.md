# Roadmap: PageFolio コード最適化

## Milestones

- ✅ **v1.3.0 コード最適化 MVP** — Phases 1-3 (shipped 2026-06-03) — [archive](milestones/v1.3.0-ROADMAP.md)
- ✅ **v1.4.0 OCR プロバイダ化 + クラウドAPI対応** — Phases 4-7 (shipped 2026-06-14) — [archive](milestones/v1.4.0-ROADMAP.md)
- ✅ **v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト** — Phases 1-4 (shipped 2026-06-16) — [archive](milestones/v1.5.0-ROADMAP.md)
- ✅ **v1.6.0 品質向上・AI強化・設定/UI改善** — Phases 1-4 (shipped 2026-06-20) — [archive](milestones/v1.6.0-ROADMAP.md)
- ✅ **v1.7.1 現機能ブラッシュアップ + APIキー入力欄** — Phases 1-4 (shipped 2026-07-05) — [archive](milestones/v1.7.1-ROADMAP.md)
- ✅ **v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化** — Phases 1-6 (shipped 2026-07-16) — [archive](milestones/v1.8.0-ROADMAP.md)
- ✅ **v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加** — Phases 1-3 (shipped 2026-08-11) — [archive](milestones/v1.9.0-ROADMAP.md)
- 📋 **v1.10.0 多重起動防止・起動操作の改善** — Phases 4-6 (構成承認済み・計画前)

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
Phase 4 の human-verify チェックポイントはユーザー判断でスキップ（実機目視未検証・コード検証済）。締め前監査の 5 件は受容済（STATE.md「Deferred Items」参照）。→ 未検証項目は v1.9.0 Phase 3（V190-QA-03）で正式消化済み。

</details>

<details>
<summary>✅ v1.7.1 現機能ブラッシュアップ + APIキー入力欄 (Phases 1-4) — SHIPPED 2026-07-05</summary>

- [x] Phase 1: APIキー入力欄（LLM設定への一元化） (4/4 plans) — completed 2026-07-04
- [x] Phase 2: OCR 磨き込み（レビュー残の現行照合と二重実装解消） (4/4 plans) — completed 2026-07-05
- [x] Phase 3: ページ操作磨き込み + v1.5.0 回帰テスト (4/4 plans) — completed 2026-07-05
- [x] Phase 4: UI/UX 磨き込み + 既知バグ棚卸し (4/4 plans) — completed 2026-07-05

全フェーズの詳細・成功基準・プラン内訳は [milestones/v1.7.1-ROADMAP.md](milestones/v1.7.1-ROADMAP.md) を参照。
V171-* 全 17 要件 Complete（被覆 17/17・孤立要件なし）。締め前監査の 4 件（quick_task 記録マーカー欠落）は v1.4.0/v1.6.0 に続き受容済（STATE.md「Deferred Items」参照）。ShortcutsDialog の非致命的 follow-up（WR-01/WR-02）は v1.8.0 Phase 5 で解消済み。人手 UAT 7 件の実機目視は v1.9.0 Phase 3（V190-QA-03）で正式消化済み。

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
V180-* 全 26 要件 Complete（被覆 26/26・孤立要件なし）。クローズ前監査で検出した quick_task 4 件（v1.4.0 期の記録マーカー欠落）は本クローズで解消済み（`status: complete` 追記）。Phase 6 由来の持ち越し（IN-01 保存トースト再試行・4手往復テストの水平展開）は v1.9.0 Phase 1/3 で解消済み。

</details>

<details>
<summary>✅ v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加 (Phases 1-3) — SHIPPED 2026-08-11</summary>

- [x] Phase 1: 保存・編集・設定の安全性是正（失敗時ロールバック担保） (7/7 plans) — completed 2026-08-11
- [x] Phase 2: OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加 (4/4 plans) — completed 2026-08-11
- [x] Phase 3: 品質保証・リリースゲート (4/4 plans) — completed 2026-08-11

全フェーズの詳細・成功基準・プラン内訳は [milestones/v1.9.0-ROADMAP.md](milestones/v1.9.0-ROADMAP.md) を参照。
フェーズ実行成果物（PLAN/SUMMARY/VERIFICATION/UAT ほか）は [milestones/v1.9.0-phases/](milestones/v1.9.0-phases/) にアーカイブ済み。
V190-* 全 27 要件 Complete（被覆 27/27・孤立要件なし）。検証 3/3 passed・Nyquist COMPLIANT・セキュリティ threats_open 0・UAT 19/19 pass（issue 0）。`APP_VERSION = v1.9.0`・テスト 1404 件グリーン。
Phase 1 は 01-06 / 01-07 の 2 回のギャップ是正を経て passed。Phase 3 のコードレビューで検出した BLOCKER（保存トースト再試行が別 Document を確定パスへ無確認上書きするデータ損失）は `bound_doc` の同一性ガードで構造的に解消済み。
技術的負債 10 件（Warning 4 / Info 6）と遡及 UAT の未実施 2 件（実 API 課金・`ANTHROPIC_API_KEY` 未設定）は非ブロッキングとして次マイルストーンへ繰り越し（PROJECT.md「Next Milestone Goals」参照）。

</details>

### 📋 v1.10.0 多重起動防止・起動操作の改善

**承認:** 2026-10-21 にユーザーが Phase 4〜6 の構成を承認。

**Milestone Goal:** 同一 Windows ログインセッションでの多重起動による作業の分散を防ぎ、既存画面への復帰、設定失敗の把握、サンプル配布の再現性を実現する。

- [x] **Phase 4: 起動制御と既存画面への復帰** - 対応版同士の起動を1画面に制限し、2回目の起動操作から作業中の画面へ戻れる。 (completed 2026-10-22)
- [x] **Phase 5: 設定読込・保存失敗の通知** - 設定エラーを把握でき、元の設定と編集操作が守られる。 (completed 2026-10-24)
- [ ] **Phase 6: サンプル配布とリリース検証** - 2サンプルを再現可能に同梱し、実配布 EXE を含む受入と版情報の整合を確認できる。

各機能フェーズは障害注入・回帰と必要な検証を完了条件に含む。2026-10-22承認によりPhase 4の未実施人手受入はPhase 6のV110-QA-02へ移管する。Phase 4は自動受入・A1〜A5・証拠照合を必須とし、最終実機受入が揃うまでリリースしない。各フェーズ完了前に `/gsd-validate-phase <番号>` を実行し、対応する `NN-VALIDATION.md` を `status: validated` にする。

## Phase Details

### Phase 4: 起動制御と既存画面への復帰

**Goal**: 利用者が2回目に PageFolio を起動しても作業画面が増えず、進行中の作業を保ったまま既存画面へ戻れる。
**Depends on**: Phase 3（v1.9.0 出荷済み）
**Requirements**: V110-START-01, V110-START-02, V110-START-03, V110-FOCUS-01, V110-FOCUS-02
**Success Criteria** (what must be TRUE):
  1. 同一 Windows ログインセッションで、対応版同士の別版・別配置・Python/EXE 混在を含む連続・同時起動をしても、編集画面は1つだけになる。
  2. 正常終了・強制終了・起動途中の異常終了後に再起動でき、終了確認をキャンセルした場合は既存画面がそのまま使用できる。
  3. 排他判定または既存画面への連絡に失敗した場合、利用者は「起動済み」と異なる理由を認識でき、後続起動は追加画面を作らず有限時間で終了する。
  4. 2回目の起動で最小化した既存画面が復元され、OS が許せば前面に出る。前面化を拒否された場合も視覚通知から既存画面を見つけられる。
  5. 未保存編集、Undo/Redo、進行中の OCR、開いているモーダル操作を保ったまま既存画面で作業を続けられる。

**受入範囲改訂（2026-10-22）**: Success Criteriaの実装/自動受入はPhase 4、未実施の最終人手受入はPhase 6。移管正本は[06-UAT-CARRYOVER.md](phases/06-release-validation/06-UAT-CARRYOVER.md)。

**Plans**: 6/6 plans complete（04-06 gap closure 実行済み、Phase正式検証待ち）
**UI hint**: yes

Plans:
**Wave 1**
- [x] 04-01-PLAN.md — 品質ゲート前提修正と本番起動tracer（Wave 1）

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 04-02-PLAN.md — 5秒の要求失効・終了競合・1回引継ぎ（Wave 2、04-01依存）

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 04-03-PLAN.md — 状態と入力先を保つ既存画面/モーダル復帰（Wave 3、04-02依存）

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 04-04-PLAN.md — 非活性の10秒案内とプロセス間集約（Wave 4、04-03依存）

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 04-05-PLAN.md — 自動受入・証拠照合とPhase 6実機受入移管（Wave 5、04-04依存）

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 04-06-PLAN.md — CR-01: backend構築失敗の独立案内と部分初期化資源の安全な解放（04-05依存）

共有する起動入口・OS境界・Windows試験と「1タスクずつ」の規約により直列実行する。Phase 4の版番号・README・開発履歴同期および実EXE配布統合はPhase 6へ引き継ぐ。

### Phase 5: 設定読込・保存失敗の通知

**Goal**: 利用者が設定の読込・保存失敗を正しく把握でき、元の設定ファイルと編集操作を失わない。
**Depends on**: Phase 4
**Requirements**: V110-CFG-01, V110-CFG-02, V110-CFG-03, V110-CFG-04
**Success Criteria** (what must be TRUE):
  1. `pagefolio_settings.json` の初回不存在なら警告なしで既定値から起動し、破損・読取不能なら画面構築後に失敗を認識できる。
  2. 設定を保存する各画面で失敗したとき、利用者は変更が次回起動に残らないことを認識でき、成功表示に誤誘導されない。
  3. 読込失敗後の自動処理や保存途中の失敗で、既存設定ファイルが無断で上書き・破壊されない。
  4. 同じ設定エラーが続いても通知が集約され、ダイアログの連打や画面再構築による通知消失で編集を妨げられない。

**Plans**: 4/4 plans complete
**UI hint**: yes

**実行依存**: `DEP-05-REGRESSION`は未充足・原因未確定のまま。2026-10-23の利用者判断により、診断commit `9384268`を採用してPhase 5へ進むことを条件付き承認済み。実装前の診断版単一全件は1637 passed / 1 warning / 263.66秒 / exit 0で対象hash一致。05-01実装後の単一全件は1660 passed / 1 warning / 234.19秒 / exit 0。どちらの成功も原因修復や依存解除とは扱わない。後続の単一全件ゲートで同種失敗が再発したら実装・後続実行・コミットを停止し、最初の失敗出力とresult.json/traceback.log・poll/reader/process診断を保持して `$gsd-debug continue dep-05-regression` で再開する。独立修復`8689c27`の成功とレビュー時1 failed/1634 passedは履歴として保持。05-01〜04は実装済み。最終1797 passed / 1 warning / 266.81秒、独立レビューclean・Nyquist validated・Security14 closed・人手14 pass。2026-10-24の利用者による意味評価2件の項目別passを05-UATへ記録し、最終検証passed（23/23）・人手計16 passとして正式完了。Phase 4報告のstale再検証とPhase 6実EXE受入は後続に残す。owner_missing・通知前景不一致も原因未確定で、条件付き実装承認と再発時停止を維持する。詳細は `debug/dep-05-regression.md`、`05-VALIDATION.md`、`05-01-SUMMARY.md`。

Plans:
**Wave 1**
- [x] 05-01-PLAN.md — 設定読込失敗の実App通知tracerと原本保護（Wave 1）

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 05-02-PLAN.md — 保存結果・原子的保存と通知ライフサイクル（Wave 2、05-01依存）

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 05-03-PLAN.md — 全保存元の共通経路化とLLM二重保存の解消（Wave 3、05-02依存）

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 05-04-PLAN.md — 複合操作受入・隔離harness・説明と品質ゲート（Wave 4、05-03依存）

### Phase 6: サンプル配布とリリース検証

**Goal**: 配布担当者が同じ手順で安全にサンプル付き EXE を再生成でき、利用者と検証担当者が v1.10.0 の受入結果を確認できる。
**Depends on**: Phase 4, Phase 5
**Requirements**: V110-DIST-01, V110-DIST-02, V110-DIST-03, V110-QA-01, V110-QA-02, V110-QA-03
**Success Criteria** (what must be TRUE):
  1. 2種のサンプルプロンプトの正本がビルド出力先の外で保持され、クリーンビルドと再ビルドの双方で配布 EXE と同階層に存在し、正本との SHA-256 一致を確認できる。利用者は既存の外部プロンプト利用手順で使える。
  2. 利用者が編集した設定と実利用プロンプトが、アプリ起動・再ビルド・配布物反映の後も元の内容を保つ。
  3. 保守担当者が起動競合・初期化失敗・設定 I/O 障害・同梱不備の自動テストと、必須の lint・format・構文確認・全件テストを通せる。
  4. 検証担当者が Windows 11 の Python 各起動経路と実際の PyInstaller onedir 配布 EXE で起動・復帰・設定通知・同梱を確認し、実施結果と未実施項目を区別して記録できる。
  5. 利用者がアプリ・README・開発履歴で一致する v1.10.0 の版番号と変更内容、排他未対応旧版と OS 前面化制約の説明を確認できる。

**引受必須**: [06-UAT-CARRYOVER.md](phases/06-release-validation/06-UAT-CARRYOVER.md)の全未実施人手項目。別session、DPI/UAC、OS拒否、操作状態維持を含む。not-run/failが残ればPhase 6完了・リリースを停止する。

**Plans**: 1/6 plans executed

Plans:
**Wave 1**
- [x] 06-01-PLAN.md — 専用CLIの実onedir tracerと非破壊ビルド境界（Wave 1）

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 06-02-PLAN.md — v1.10.0・サンプル利用・更新/再ビルド説明の同期（Wave 2）

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 06-03-PLAN.md — 実EXE観測adapterとfake OCR/設定障害の準備（Wave 3）

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 06-04-PLAN.md — 最終版の実初回/再ビルド・原本保護・EXE接続実証（Wave 4）

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 06-05-PLAN.md — 全ケースカードと操作状態/混在入口/EXE設定受入（Wave 5）

**Wave 6** *(blocked on Wave 5 completion)*
- [ ] 06-06-PLAN.md — OS条件/別session受入と品質・鮮度・出荷停止照合（Wave 6）

共有する配布tree・証拠台帳・Windows foregroundと1タスクずつの規約により直列。全24枝番＋WR-01は06-VALIDATIONへ割当済み。Phase4 stale再検証が実機受入開始/完了の前提で、W11未準備・必須not-run/failはPhase6完了/出荷を停止する。計画合格は製品実装・実機合格ではない。

## Progress

**Milestone summary:**

| Milestone | Phases | Plans | Status | Shipped |
| --------- | ------ | ----- | ------ | ------- |
| v1.3.0 コード最適化 MVP | 3 | 8 | ✅ Complete | 2026-06-03 |
| v1.4.0 OCR プロバイダ化 + クラウドAPI対応 | 4 | 14 | ✅ Complete | 2026-06-14 |
| v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト | 4 | — | ✅ Complete | 2026-06-16 |
| v1.6.0 品質向上・AI強化・設定/UI改善 | 4 | 11 | ✅ Complete | 2026-06-20 |
| v1.7.1 現機能ブラッシュアップ + APIキー入力欄 | 4 | 16 | ✅ Complete | 2026-07-05 |
| v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化 | 6 | 22 | ✅ Complete | 2026-07-16 |
| v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加 | 3 | 15 | ✅ Complete | 2026-08-11 |
| v1.10.0 多重起動防止・起動操作の改善 | 3 | 16（Phase 4:6、Phase 5:4、Phase 6:6） | Phase 5完了・Phase 6計画済み。Phase 4報告stale・回帰原因未解決・出荷停止を維持 | — |

各マイルストーンのフェーズ単位の内訳は上記 `<details>` ブロックおよび各アーカイブ
（`milestones/*-ROADMAP.md`）を参照。

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 4. 起動制御と既存画面への復帰 | 6/6 | Complete | 2026-10-22 |
| 5. 設定読込・保存失敗の通知 | 4/4 | Complete | 2026-10-24 |
| 6. サンプル配布とリリース検証 | 1/6 | Planned | — |
