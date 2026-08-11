# Roadmap: PageFolio コード最適化

## Milestones

- ✅ **v1.3.0 コード最適化 MVP** — Phases 1-3 (shipped 2026-06-03) — [archive](milestones/v1.3.0-ROADMAP.md)
- ✅ **v1.4.0 OCR プロバイダ化 + クラウドAPI対応** — Phases 4-7 (shipped 2026-06-14) — [archive](milestones/v1.4.0-ROADMAP.md)
- ✅ **v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト** — Phases 1-4 (shipped 2026-06-16) — [archive](milestones/v1.5.0-ROADMAP.md)
- ✅ **v1.6.0 品質向上・AI強化・設定/UI改善** — Phases 1-4 (shipped 2026-06-20) — [archive](milestones/v1.6.0-ROADMAP.md)
- ✅ **v1.7.1 現機能ブラッシュアップ + APIキー入力欄** — Phases 1-4 (shipped 2026-07-05) — [archive](milestones/v1.7.1-ROADMAP.md)
- ✅ **v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化** — Phases 1-6 (shipped 2026-07-16) — [archive](milestones/v1.8.0-ROADMAP.md)
- ✅ **v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加** — Phases 1-3 (shipped 2026-08-11) — [archive](milestones/v1.9.0-ROADMAP.md)
- 📋 **次マイルストーン** — 未確定（`/gsd-new-milestone` で定義する）

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

### 📋 次マイルストーン（未確定）

アクティブなマイルストーンはありません。`/gsd-new-milestone` で次マイルストーンの
questioning → research → requirements → roadmap を実行してください。

候補は [PROJECT.md](PROJECT.md)「Next Milestone Goals」を参照。

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

各マイルストーンのフェーズ単位の内訳は上記 `<details>` ブロックおよび各アーカイブ
（`milestones/*-ROADMAP.md`）を参照。
