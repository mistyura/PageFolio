# PageFolio — コード最適化プロジェクト

## What This Is

PageFolio の既存コードベースに対する最適化プロジェクト。
バグ修正・リファクタリング・テスト充実の 3 軸で品質を底上げする。

**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする。

## Current Milestone: v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化

**Goal:** 独立してきたコンポーネント（OCR・LLMプロバイダー・UI）のシナジーを高め、シームレスで高度なドキュメント処理・要約環境を構築する。

**Target features:**

1. **AI強化**
   - プロンプト・テンプレートマネージャー（v1.7.4 外部 md ファイル連動の発展。複数テンプレートの命名保存・切替 UI）
   - プロバイダーフォールバック（**明示設定型**: ユーザーが設定したフォールバック順のみ・送信先確認の再提示つき。自動的な別ベンダー送信はしない）
2. **堅牢性（PERF-01 + 実在課題）**
   - PERF-01: サムネイル仮想化によるパフォーマンス改善（Future Requirements から昇格）
   - Blob ライフサイクル強化（リーク検出・Windows AV スキャン衝突テスト）
   - 肥大モジュールの分割リファクタリング（`ocr_dialog.py` 2154行 / `ocr_providers.py` 1424行 / `llm_config.py` 1204行）
   - ShortcutsDialog WR-01/WR-02 解消・`_SENSITIVE_KEYS` の中央レジストリ化
3. **品質保証**
   - OCR→サマリの E2E モックテスト拡充（`ocr_pipeline.py` 基盤活用）
   - エラー時リカバリー通知の小粒改善（非モーダル通知の前例踏襲）
   - UI 一貫性監査（スクロールパターン統一・フォントスケーリング）＋ 開発履歴.md v1.7.0 表記整合
4. **バッチ複数ファイル OCR**（大型・**単独フェーズへ隔離**）
   - 複数ファイルの一括 OCR・一括要約のキュー管理（fitz メインスレッド制約を遵守した設計）

**Key context:**
- 不採用確定: API キー/プロンプト履歴の暗号化ローカル保存（V14-D-02 セッション限定方針を維持）・Alpha/Beta/RC 段階リリース（直接リリース運用を維持）
- 作業ブランチ: `dev/v1.8.0`（main 直コミット禁止運用）
- 実コードベースは v1.7.4（GSD 記録の v1.7.1 より 3 ポイントリリース先行: v1.7.2 LLM設定スクロール化・v1.7.3 OCRダイアログ右ペイン再設計・v1.7.4 外部プロンプトファイル連動）を起点とする
- プロバイダーフォールバックは外部送信の明示同意方針（既定 off・コスト確認）と整合させるため「明示設定型」に限定（自動ベンダー切替は不採用）
- human-verify/UAT 実機目視（過去3回一旦 pass）はスコープ外・必要なら要件定義時に追加可能

## Last Milestone: v1.7.1 現機能ブラッシュアップ + APIキー入力欄 — ✅ Shipped 2026-07-05

> v1.7.1 は全 4 フェーズ（Phase 1〜4・16 プラン・41 タスク）を達成して出荷済み（`APP_VERSION = v1.7.1`・テスト 859 件グリーン・ruff クリーン）。V171-* 全 17 要件 Complete（被覆 17/17・孤立要件なし）。
> 次マイルストーンは `/gsd-new-milestone` で確定する（候補は「Next Milestone Goals」参照）。

**Goal（達成済み）:** 既存機能（UI/UX・OCR・ページ操作）を磨き込み、テスト・安定性を底上げした。あわせて LLM 設定ダイアログにセッション限定の APIキー入力欄を追加し、キー設定導線を一元化した。

**Target features（達成済み）:**
- **APIキー入力欄の一元化**: LLMConfigDialog に Claude/Gemini/RunPod のマスク付きキー入力欄・トグル・セッション限定注記を追加。解決優先順を「入力値 → 環境変数」へ反転し、OCRDialog 側の旧セッションキー UI を撤去して導線を一元化（送信先確認ダイアログの RunPod 誤開示 CR-01 も解消）
- **OCR 磨き込み**: プラグイン OCR registry 堅牢化（重複名ポリシー・unload 時登録解除・公開アクセサ）・Tesseract 言語の段階的縮退フォールバック・producer-consumer 実行パイプラインを新設 `ocr_pipeline.py` へ一本化・L-6 小物一括解消
- **ページ操作磨き込み**: 画像（ロゴ）透かし対応・黒塗り/モザイクの連続適用+粒度スライダー・`_derotate_rect` 共通ヘルパーによる回転座標統一（黒塗り/モザイク/トリミングの座標ズレを構造的に解消）
- **UI/UX 磨き込み**: ShortcutsDialog 新設（実キーキャプチャ編集・重複拒否）・SettingsDialog 3セクション再編・LLMConfigDialog 共通/固有グルーピング・i18n/エラー表示一貫性監査（未使用 LANG キー 11件削除）
- **テスト・安定性**: v1.5.0 新機能（TOC 保持・D&D 挿入・ショートカット読込）の回帰テスト整備・APIキー機能の回帰テスト整備・既知軽微バグの棚卸し解消

**Key context:**
- キー解決の優先順を「環境変数優先・未設定時のみ入力値」から「入力値 → 環境変数」へ反転（OCRDialog 側の旧仕様を置き換え）。RunPod もセッションキー機構（`_session_api_keys`）に新規対応
- APIキーの settings.json 非永続化（`_SENSITIVE_KEYS` ガード）は維持（V14-D-02 踏襲）
- L-1〜L-6（v1.4.0 期レビュー由来）は各フェーズ計画時に現行コード照合で「活き残り」を確定した上で解消（v1.6.0〜v1.7.0 で解消済みの項目は対象外に整理）
- コードレビュー Critical 0件（Warning 2件は ShortcutsDialog の非致命的 UX 課題・follow-up 候補）。セキュリティ監査 threats_open: 0（脅威8件 closed）
- 人手 UAT 7件はユーザー判断で一旦 pass（実機目視未検証・コード/自動ゲートは全通過、v1.6.0 Phase 4 と同様の運用）

> 補足: v1.6.1〜v1.7.0（パスワード/印刷・Ollama/RunPod・バグ修正・サマリ安定化・黒塗り/モザイク・undo ディスク退避）は GSD フェーズ外のポイントリリースとして出荷済み。詳細は `.planning/MILESTONES.md` 参照。

<details>
<summary>Previous Milestone: v1.6.0 品質向上・AI強化・設定/UI改善 — ✅ Shipped 2026-06-20</summary>

> v1.6.0 は全 4 フェーズ（Phase 1〜4・11 プラン・23 タスク）を達成して出荷済み（`APP_VERSION = v1.6.0`・テスト 597 件グリーン）。

**Goal（達成済み）:** 体感品質（回転プレビュー即時反映・エラーハンドリング UX）と AI 出力品質（Markdown 整形・プロバイダ別プロンプト最適化）を底上げし、設定の二重化を解消して大量ページ対応で UI を整える。

**Target features:**
- 設定/UI 改善: OCR パラメータ設定の「LLM設定」一元化（S1）・サムネイルサイズスライダーの配置変更（S2）・大量ページのページネーション表示（S3）
- 品質向上（プランA）: 回転状態のプレビュー即時反映（H1）・API キー秘匿の監査（H2）・max_tokens / 429 の実機検証（H5）・エラーハンドリング UX 磨き（M1）
- AI 強化（プランC）: OCR 結果の Markdown 整形表示（M3）・プロバイダ別プロンプト最適化（M4・Claude=XML タグ / Gemini=明示指示）

**Key context:**
- 出典は `.planning/NEXT-MILESTONE-HANDOFF.md`（統合ロードマップ + 2026-06-18 追記の仕様要望 S1〜S3）。
- OAuth 接続は実装しない（確定事項）。Claude/Gemini とも API キー方式のみ・正規 API が非対応・配布バイナリに client secret を埋め込めないため。
- S1: OCR 抽出画面のパラメータ UI は撤去 or 読み取り専用化（実装時判断）。設定は `LLMConfigDialog` に集約。
- S3: D&D・複数選択は全ページインデックス管理のため、ページング導入時に「表示中ページ vs 全ページ」のインデックス整合に注意。表示件数は `pagefolio_settings.json` に永続化。
- H5: max_tokens クランプ / 429 リトライは安全側修正のみでテスト担保。実 API での検証が残課題。

</details>

<details>
<summary>Previous Milestone: v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト — ✅ Shipped 2026-06-16</summary>

> v1.5.0 は全 4 フェーズ（Phase 1〜4）を達成して出荷済み（`APP_VERSION = v1.5.0`）。
> 実装は `feature/v1.5.0-improvements` ブランチで別ワークフローにより完了し、2026-06-16 に文書を整合。

**Goal（達成済み）:** PDF 編集の基本機能を底上げ（白紙ページ挿入・テキスト透かし／ページ番号・TOC 保持）、UI/UX を改善（サムネイルサイズ動的変更・D&D 指定位置挿入・ショートカット動的読込）、OCR にカスタムプロンプトを導入する。

**Target features:**
- PDF ページ操作の拡充: 白紙ページ挿入・テキスト透かし／ページ番号追加・ページ操作時の TOC 保持
- UI/UX 改善: サムネイルサイズ動的変更（スライダー）・サムネイルペインへの D&D 指定位置挿入・ショートカット動的読込（JSON ミニマム実装）
- OCR カスタムプロンプト: `LLMConfigDialog` でプロンプトを入力・保存し OCR バックエンドへ受け渡し

**Key context:**
- 透かし・ページ番号は**テキストのみ**（画像ロゴは後回し。v1.7.1 Phase 3 で対応済み）。
- ショートカットは**`pagefolio_settings.json` の `shortcuts` キー編集のみ**のミニマム実装（専用 GUI タブなし。v1.7.1 Phase 4 で ShortcutsDialog により GUI 化済み）。
- 他 OCR プロバイダ対応はスコープ外（既存の Provider 群を踏襲。v1.6.2 で Ollama/RunPod を追加済み）。
- 整合作業時に ruff E501 2 件を修正（`app.py` / `file_drop.py`）。テスト 490 件グリーン。
- 要件・ロードマップ詳細: `.planning/milestones/v1.5.0-REQUIREMENTS.md` / `.planning/milestones/v1.5.0-ROADMAP.md`

</details>

<details>
<summary>Previous Milestone: v1.4.0 OCR プロバイダ化 + クラウドAPI対応 — ✅ Shipped 2026-06-14</summary>

> v1.4.0 は全 4 フェーズ（Phase 04〜07）を達成して出荷済み。出荷後の安定化で v1.4.4 まで進行。

**Goal（達成済み）:** 現行 OCR（LM Studio 専用）を `OCRProvider` 抽象化し、Gemini / Claude のクラウドAPIと Tesseract を差し替え可能にする。GPU 非搭載 PC を主想定とした低スペック対策とプラグイン登録機構まで含める。

**Target features:**
- プロバイダ抽象化（`OCRProvider` 基底・LM Studio を Provider 実装へリファクタ・`run_parallel()` 一般化）
- Claude Provider（messages API・effort・モデル一覧 / `ANTHROPIC_API_KEY`）
- Gemini Provider（generateContent・inline_data・モデル一覧 / `GEMINI_API_KEY`・`GOOGLE_API_KEY`）
- 低スペック対策（テキスト埋め込み判定で OCR スキップ・逐次レンダリング・`ocr_scale` 見直し）
- OCRDialog のプロバイダ選択UI・APIキー未設定エラー・`ocr_provider` enum（既定 `off`）
- Tesseract Provider（オプション・精度劣後注記つき）
- PluginManager へのプロバイダ登録フック新設
- テスト・多言語文言・ドキュメント更新

**Key context:**
- APIキーは**環境変数のみ・平文保存禁止**（`pagefolio_settings.json` にキーを書かない）。未設定時は明示エラー、保存しない。
- 既定 `ocr_provider: "off"`（外部送信・課金を望まないユーザー向けの安全側）。
- 実装方針は **urllib 直叩き・依存追加なし**（公式SDK は PyInstaller 肥大化のため不採用）。
- プライバシー（外部送信）・コスト（従量課金）・レート制限（429）に配慮。クラウド並列度はローカルより絞る。
- 後方互換維持（v1.4.0 マイナーバンプ）。
- 設計の出典: `docs/OCRプロバイダ化_見積もり仕様.md`

</details>

## Context

| 項目 | 内容 |
|------|------|
| リポジトリ | `C:\Users\shdwf\work\project\PageFolio` |
| 言語 | Python 3.8+ / Tkinter |
| 現在バージョン | `pagefolio/constants.py` の `APP_VERSION` を参照 |
| テスト | pytest（859 件・充実） |
| リント | ruff |

既存コードベースマップ: `.planning/codebase/`

## Problem Statement

コードベース分析で以下の問題が発見された。

### バグ（動作に影響）

| ID | 問題 | 影響 |
|----|------|------|
| BUG-01 | ページ挿入操作の Undo が何もしない（`state["data"] = [insert_at, 0]` で挿入数が常に 0） | 挿入後に Undo してもページが残る |
| BUG-02 | Undo 実行時に `doc.tobytes()` でフルシリアライズ（Undo/Redo 非対称設計） | 大きな PDF で Undo が重い |
| BUG-03 | プレビュー生成のたびに `doc.tobytes()` でフルシリアライズ | ページ切り替えが遅い |

### 技術的負債（保守性に影響）

| ID | 問題 | 現状 |
|----|------|------|
| DEBT-01 | `dialogs.py` 肥大化 | 1,191 行・6 クラスが 1 ファイルに混在 |
| DEBT-02 | `constants.py` 肥大化 | 711 行・テーマ/言語/バージョンが混在 |
| DEBT-03 | Undo スタックの `list.pop(0)` が O(n) | `collections.deque` で O(1) にできる |
| DEBT-04 | `settings._current_font_size` をモジュール外部から直接書き換え | プライベート変数への外部アクセス |

## Requirements

### Validated

- ✓ Tkinter UI フレームワーク — 既存
- ✓ pymupdf (fitz) による PDF 操作 — 既存
- ✓ Mixin パターンによるモジュール分割 — 既存
- ✓ pytest + ruff によるテスト・リント体制 — 既存
- ✓ BUG-01: ページ挿入 Undo が正しく元に戻る — Phase 1 で検証（対称デルタ化）
- ✓ BUG-02: Undo 実行時のシリアライズコストを削減する — Phase 1 で検証（doc.tobytes() 全廃）
- ✓ DEBT-03 (REFAC-03): Undo スタックを `collections.deque(maxlen=MAX_UNDO)` に変更する — Phase 1 で検証
- ✓ BUG-03: プレビュー生成のフルシリアライズを廃止する — Phase 2 で検証（`page.get_pixmap()` 同期直接呼び出し・`doc.tobytes()` 全廃）
- ✓ DEBT-01 (REFAC-01): `dialogs.py` をサブパッケージ `pagefolio/dialogs/` に分割する — Phase 2 で検証（後方互換 import 維持）
- ✓ DEBT-02 (REFAC-02): `constants.py` を `lang.py`・`themes.py` に分割する — Phase 2 で検証（再エクスポートで後方互換維持）
- ✓ TEST-02: BUG-03 の回帰テスト（`tests/test_viewer.py`）— Phase 2 で検証
- ✓ DEBT-04 (REFAC-04): `settings._current_font_size` 外部アクセスを公開関数 `set_current_font_size()`/`get_current_font_size()` 経由に変更する — Phase 3 で検証（write/read 両面 API 化・stale binding 解消）
- ✓ TEST-03: import 回帰テスト整備（`tests/test_imports.py`・4クラス34テスト）— Phase 3 で検証（REFAC-01〜04 の全 import パスを保護）
- ✓ OCR-PROV-01/02・OCR-PERF-01: `OCRProvider` 抽象化・LM Studio Provider 化・`run_parallel()` 一般化・埋め込みテキストスキップ — v1.4.0 Phase 04
- ✓ OCR-SEC-01・OCR-PROV-03・OCR-UI-01: APIキー平文保存ガード・Claude Provider・プロバイダ選択 UI・コスト確認 — v1.4.0 Phase 05
- ✓ OCR-PROV-04・OCR-PERF-02/05・OCR-QA-01: Gemini Provider・逐次レンダリング・`ocr_scale` 見直し・OCR モックテスト — v1.4.0 Phase 06
- ✓ OCR-EXT-01/02・OCR-QA-02: Tesseract Provider・`register_ocr_provider` フック・多言語文言/ドキュメント整備 — v1.4.0 Phase 07
- ✓ アーカイブ詳細: `.planning/milestones/v1.4.0-REQUIREMENTS.md`
- ✓ V15-PAGE-01/02/03: 白紙ページ挿入・テキスト透かし／ページ番号追加・ページ操作時の TOC 保持 — v1.5.0 Phase 1
- ✓ V15-UIUX-01/02/03: サムネイルサイズ動的変更・D&D 指定位置挿入・ショートカット動的読込（JSON ミニマム） — v1.5.0 Phase 2
- ✓ V15-OCR-01/02: OCR カスタムプロンプト入力／保存・OCR バックエンドへの受け渡し — v1.5.0 Phase 3
- ✓ V15-QA-01/02: ruff クリーン・pytest 490 件全通過 — v1.5.0 Phase 4（整合時に E501 2 件修正）
- ✓ アーカイブ詳細: `.planning/milestones/v1.5.0-REQUIREMENTS.md`
- ✓ V16-UI-01/02: OCR パラメータの「LLM設定」一元化（OCRDialog 数値 UI 読み取り専用化）・サムネイルスライダー常時可視化 — v1.6.0 Phase 1
- ✓ V16-UI-03: 大量ページのページネーション表示（窓表示・件数永続化・D&D/複数選択の全ページインデックス整合・`pagination.py` 純ロジック層） — v1.6.0 Phase 2
- ✓ V16-QUAL-01/02/03/04: 回転プレビュー即時反映・API キー秘匿の 3 経路回帰テスト化・max_tokens/429 実機検証チェックリスト・エラー UX 磨き — v1.6.0 Phase 3
- ✓ V16-AI-01/02: OCR 結果の Markdown 整形表示（tk.Text タグ）・プロバイダ別プロンプト最適化（Claude=XML/Gemini=明示・カスタム両立） — v1.6.0 Phase 4（human-verify はスキップ・コード検証済）
- ✓ アーカイブ詳細: `.planning/milestones/v1.6.0-REQUIREMENTS.md`
- ✓ V171-KEY-01/02/03/04・V171-TEST-02: LLM設定ダイアログへの APIキー入力欄一元化・キー解決順反転（入力値→環境変数）・OCRDialog 旧キーUI 撤去・RunPod セッションキー対応・送信先確認ダイアログの RunPod 分岐（CR-01 解消） — v1.7.1 Phase 1
- ✓ V171-OCR-01/02/03/04: L-6 小物一括解消・tesseract_lang 尊重・プラグイン registry 堅牢化・producer-consumer 一本化（`ocr_pipeline.py` 新設） — v1.7.1 Phase 2
- ✓ V171-PAGE-01/02/03・V171-TEST-01: 画像透かし対応・黒塗り/モザイク使い勝手改善・回転/トリミング操作性改善（`_derotate_rect` 共通基盤）・v1.5.0 新機能の回帰テスト整備 — v1.7.1 Phase 3
- ✓ V171-UIUX-01/02/03・V171-TEST-03: ショートカット GUI 編集（ShortcutsDialog）・エラー表示/文言一貫性監査（i18n化・messagebox統一・未使用キー削除）・SettingsDialog/LLMConfigDialog セクション再編・既知軽微バグ棚卸し解消 — v1.7.1 Phase 4
- ✓ V180-REFAC-01/02・V180-ROBUST-02: `ocr_providers.py`/`dialogs/llm_config.py` の責務別パッケージ分割・`_SENSITIVE_KEYS` プロバイダ→環境変数中央レジストリ化（`registry.py`新設） — v1.8.0 Phase 1
- ✓ V180-TMPL-01〜05・V180-FALL-01〜03: 名前付きプロンプトテンプレート CRUD（保存/選択/削除/リネーム・外部mdファイル連動・全プロバイダ横断共有）・明示設定型プロバイダーフォールバック（送信先確認再提示つき・自動別ベンダー送信なし） — v1.8.0 Phase 2
- ✓ V180-REFAC-03・V180-QA-01: `ocr_dialog.py` の producer-consumer 駆動部を `OCRRunEngine`（`pagefolio/ocr_engine.py`）へ抽出し `OCRDialog` を薄い委譲ラッパー化・OCR→サマリ E2E モックテスト整備（`tests/test_ocr_engine.py`・実スレッド/キュー駆動） — v1.8.0 Phase 3

### Active

- v1.8.0 の要件は `.planning/REQUIREMENTS.md` で定義中（AI強化・堅牢性・品質保証・バッチ複数ファイル OCR の 4 本柱）。Phase 1〜3 完了、Phase 4〜6 継続中。

### Out of Scope

- OS キーストア連携（Windows Credential Manager）による APIキー永続化 — セッション限定方針を維持（V14-D-02 踏襲）。永続化は別マイルストーン判断
- OAuth 接続 — 正規 API が非対応・配布バイナリに client secret を埋め込めないため確定除外
- OCR 結果のページ埋め込み（検索可能 PDF 化） — v1.4.0 から継続除外
- プラグイン API バージョン管理 — 今後の別タスク

## Key Decisions

| 決定事項 | 根拠 | 状態 |
|---------|------|------|
| BUG-02 対応：op 別逆デルタによる対称 Undo/Redo 設計 | `doc.tobytes()` 全体シリアライズを撤廃し、op ごとに逆操作を保持することで大きな PDF でも UI をブロックしない | ✓ 検証済み（Phase 1・全 op 往復安全網テストで対称デルタバグ 3 件を発見・修正） |
| BUG-03 対応：`doc.tobytes()` をバックグラウンドスレッドに渡すのをやめ、ページ単位で `page.get_pixmap()` を直接呼ぶ | fitz のスレッドセーフ制約を迂回しつつ、フルシリアライズを排除できる | 検証済み（Phase 2・同期化により `_preview_gen`/プレースホルダ廃止） |
| DEBT-01：dialogs をサブパッケージ `pagefolio/dialogs/` に分割 | `dialogs.py` 単体でのモジュール分割より import パスの変更が最小化される | 検証済み（Phase 2・6クラスを5ファイルへ・`__init__.py` 再エクスポート） |
| DEBT-02：constants を `themes.py`/`lang.py` に分割し再エクスポート | 711行のモジュールを責務別に分割しつつ既存 import 表面を温存 | 検証済み（Phase 2・`C` 識別子保持で in-place 更新を維持） |
| DEBT-04：`_current_font_size` を write/read 両面で公開 API 化（最小案不採用） | write のみ setter 化では dialogs の private import と stale binding が残る。setter/getter 一本化で DEBT-04 の趣旨（外部アクセス全廃）を満たす | 検証済み（Phase 3・`set_current_font_size`/`get_current_font_size`・単純代入のみ D-04） |
| TEST-03：import 回帰テストを単一ファイル `tests/test_imports.py` に集約（明示 import + assert） | 動的 importlib 方式より「何が壊れたか」が一目瞭然。責務を 1 箇所に集約し見通しを確保 | 検証済み（Phase 3・D-06/D-09・Tk 非依存 import のみ） |
| V14-D-01：OCR は `urllib.request` 直叩き・新規 pip 依存ゼロ（公式 SDK 不採用） | PyInstaller 肥大化を回避しつつ全プロバイダを統一実装 | ✓ Good（v1.4.0・Claude/Gemini/Tesseract 全実装で踏襲） |
| V14-D-02：APIキーは環境変数＋セッションメモリのみ・`_SENSITIVE_KEYS` ガードで settings 非永続 | 平文保存による漏洩リスクを構造的に排除 | ✓ Good（v1.4.0 Phase 05・キー名のみログ・値は非出力） |
| V14-D-03：既定 `ocr_provider: "off"` | 外部送信・課金を望まないユーザー向けの安全側デフォルト | ✓ Good（v1.4.0） |
| V14-D-05/06：fitz `get_pixmap()` はメインスレッドのみ・逐次レンダリング（render→送信→破棄） | スレッドセーフ制約の遵守と低スペック PC のメモリ上限保証 | ✓ Good（v1.4.0 Phase 06・bounded buffer で機械保証） |
| V14-D-08：Tesseract / PluginManager 登録フックは最終フェーズ（任意） | スコープ調整時に切りやすい位置に配置 | ✓ Good（v1.4.0 Phase 07・遡及クローズアウトで完了記録） |
| V16-D-01：ページネーションの index 変換を純ロジック層 `pagination.py`（local↔global）へ集約 | viewer/dnd/選択照合の全ページインデックス整合を 1 箇所で機械保証しテスト可能化 | ✓ Good（v1.6.0 Phase 2・窓追従の不変条件で UAT snap back も解消） |
| V16-D-02：Markdown 整形は純関数 `parse_markdown`（Tk 非依存）+ OCRDialog の薄い描画層へ配線・コピー/保存は raw 維持 | 描画ロジックを純関数化して unit テスト可能にし、エクスポートは整形非反映で情報露出経路を増やさない | ✓ Good（v1.6.0 Phase 4・表示専用タグ） |
| V16-D-03：プロバイダ別プロンプトは `resolve_ocr_prompt`（custom > provider別 > 汎用）で純関数解決 | カスタムプロンプト両立を構造的に担保しつつ Claude=XML/Gemini=明示を分離 | ✓ Good（v1.6.0 Phase 4・後方互換） |
| V16-D-04：出荷バージョンを v1.6.0 に確定（途中 v1.7.0 へ一時バンプ後 49e9893 で巻き戻し） | APP_VERSION/README/GSD ラベルの一致を優先。開発履歴.md の v1.7.0 エントリは v1.6.0 へ整合予定 | ⚠️ Revisit（開発履歴.md の版番整合が残課題） |
| V16-D-05：Phase 4 human-verify をユーザー判断でスキップしクローズ | コード・自動ゲートは全通過。実描画/実 API 出力品質のみ未検証で deferred 受容 | ⚠️ Revisit（必要時に実機目視） |
| V171-D-14：ネスト LLMConfigDialog 適用は `app._apply_llm_settings_live`（`_rebuild_ui()` を呼ばない軽量反映）を独立トランザクション化 | nested on_apply から `_rebuild_ui()` を呼ぶと開いている SettingsDialog Toplevel ごと破棄されるため。ディスク/メモリ整合を cascade テストで担保 | ✓ Good（v1.7.1 Phase 4） |
| V171-D-11：未使用 LANG キー検出は引用符付き完全一致（AST走査不採用） | 動的キー合成がコードベース全体でゼロ件（確認済み）のため grep 相当で十分。プレフィックス衝突（`tesseract_not_installed` 等）は完全一致で誤削除を回避 | ✓ Good（v1.7.1 Phase 4・回帰テスト常設） |
| V171-D-05：ShortcutsDialog は保存ボタン押下まで一時コピー（`self._shortcuts`）のみ編集し、実バインド/settings へは未反映（キャンセルで無効化） | 実キーキャプチャの GUI 化で誤操作時の即時反映事故を防ぐ | ✓ Good（v1.7.1 Phase 4） |

## Current State

**Shipped: v1.7.1 現機能ブラッシュアップ + APIキー入力欄 (2026-07-05)** — 4 フェーズ / 16 プラン / 41 タスク。`APP_VERSION = v1.7.1`（テスト 859 件グリーン・ruff クリーン）。V171-* 全17要件 Complete（被覆17/17・孤立要件なし）。

- **APIキー入力欄:** LLMConfigDialog に Claude/Gemini/RunPod のマスク付き入力欄・トグル・セッション限定注記を追加。解決優先順を「入力値→環境変数」へ反転し、OCRDialog の旧セッションキー UI を撤去して導線を一元化（送信先確認ダイアログの RunPod 誤開示 CR-01 も解消）。
- **OCR 磨き込み:** プラグイン OCR registry 堅牢化（重複名ポリシー・unload 解除・公開アクセサ）・Tesseract 言語の段階的縮退フォールバック・producer-consumer 実行パイプラインを新設 `ocr_pipeline.py` へ一本化・L-6 小物一括解消。
- **ページ操作磨き込み:** 画像（ロゴ）透かし対応・黒塗り/モザイクの連続適用+粒度スライダー・`_derotate_rect` 共通ヘルパーで回転座標を統一。
- **UI/UX 磨き込み:** ShortcutsDialog 新設（実キーキャプチャ・重複拒否）・SettingsDialog 3セクション再編・LLMConfigDialog 共通/固有整理・i18n/エラー表示一貫性監査（未使用キー11件削除）。
- コードレビュー Critical 0件（Warning 2件は ShortcutsDialog の非致命的 follow-up 候補）。セキュリティ監査 threats_open: 0（脅威8件 closed）。人手UAT 7件はユーザー判断で一旦pass（実機目視未検証・コード/自動ゲートは全通過）。
- マイルストーン詳細: `.planning/milestones/v1.7.1-ROADMAP.md`・`.planning/MILESTONES.md`

<details>
<summary>Shipped: v1.6.0 品質向上・AI強化・設定/UI改善 (2026-06-20)</summary>

**Shipped: v1.6.0 品質向上・AI強化・設定/UI改善 (2026-06-20)** — 4 フェーズ / 11 プラン / 23 タスク。`APP_VERSION = v1.6.0`（テスト 597 件グリーン・ruff クリーン）。

- **設定/UI 改善:** OCR パラメータの「LLM設定」一元化（OCRDialog 数値 UI 読み取り専用化・全プロバイダ共通ライブ同期）・サムネイルサイズスライダーを独立全幅行へ移設（左ペイン縮小時も常時可視）。
- **大量ページ対応:** サムネイル一覧のページネーション表示（既定 20・窓表示）・件数永続化・ナビフッター。D&D/複数選択の全ページインデックス整合を純ロジック層 `pagination.py`（local↔global 変換）へ集約。
- **体感品質・OCR 堅牢性:** 回転プレビュー即時反映（セレクション意味論の原因除去）・API キー秘匿の 3 経路回帰テスト化・max_tokens/429 実機検証チェックリスト・OCR 応答途切れ検出と部分テキスト保持・待機秒数併記。
- **AI 出力品質:** OCR 結果ビューアの `markdown` プリセットを tk.Text タグで整形表示（見出し/箇条書き/コード/強調）・プロバイダ別プロンプト最適化（Claude=XML タグ/Gemini=明示指示・カスタムプロンプト両立）・コピー/保存は raw 維持。
- Phase 4 の human-verify チェックポイントはユーザー判断でスキップ（実機目視未検証・コード/自動ゲート〔ruff・pytest597・コードレビュー・目標検証〕は通過）。
- マイルストーン詳細: `.planning/milestones/v1.6.0-ROADMAP.md`・`.planning/MILESTONES.md`

</details>

<details>
<summary>Shipped: v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト (2026-06-16)</summary>

**Shipped: v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト (2026-06-16)** — 4 フェーズ。`APP_VERSION = v1.5.0`（テスト 490 件グリーン・ruff クリーン）。

- **ページ操作の拡充:** 白紙ページ挿入・テキスト透かし／ページ番号追加（`insert_text`・テキストのみ）・削除/結合/分割時の TOC 保持調整。
- **UI/UX:** サムネイルサイズ動的変更（`thumb_zoom_scale` スライダー）・サムネイルペインへの D&D 指定位置挿入・ショートカット動的読込（`shortcuts` キー・JSON ミニマム）。
- **OCR:** `LLMConfigDialog` のカスタムプロンプト入力欄・`ocr_custom_prompt` 保存・OCR バックエンドへの受け渡し。
- 実装は `feature/v1.5.0-improvements` ブランチ（別 WF 実装・2026-06-16 に文書整合・ruff E501 2 件修正）。
- マイルストーン詳細: `.planning/milestones/v1.5.0-ROADMAP.md`・`.planning/MILESTONES.md`

</details>

<details>
<summary>Shipped: v1.4.0 OCR プロバイダ化 + クラウドAPI対応 (2026-06-14)</summary>

**Shipped: v1.4.0 OCR プロバイダ化 + クラウドAPI対応 (2026-06-14)** — 4 フェーズ / 14 プラン / 26 タスク。出荷後の安定化で v1.4.4 まで進行（テスト 490 件グリーン・ruff クリーン）。

- **OCR プロバイダ抽象化:** `OCRProvider` 基底 + `build_provider` ファクトリ。LM Studio / Claude / Gemini / Tesseract の 4 バックエンドを差し替え可能。
- **セキュリティ:** APIキーは環境変数＋セッションメモリのみ。`_SENSITIVE_KEYS` ガードで settings.json への平文流入を構造的に防止。
- **低スペック対策:** 埋め込みテキストスキップ・逐次レンダリング（bounded buffer）・`ocr_scale` 既定 1.5 でメモリ上限を保証。
- **拡張性:** `PluginManager.register_ocr_provider` でサードパーティがカスタム OCR バックエンドを登録可能。
- **UX:** プロバイダ選択 UI・コスト確認ダイアログ・指数バックオフリトライ・日英文言整備。
- マイルストーン詳細: `.planning/milestones/v1.4.0-ROADMAP.md`・`.planning/MILESTONES.md`
- 既知の遅延項目: Phase 04 検証ギャップ 1 + クイックタスク完了マーカー欠落 4（STATE.md「Deferred Items」・実作業は出荷済み）

</details>

<details>
<summary>Shipped: v1.3.0 コード最適化 MVP (2026-06-03)</summary>

**Shipped: v1.3.0 コード最適化 MVP (2026-06-03)** — 3 フェーズ / 8 プラン / 全 10 要件達成。

- **Undo/Redo:** `doc.tobytes()` 全廃の対称デルタ設計。deque(maxlen) で O(1) スタック管理。大きな PDF でも非ブロッキング。
- **プレビュー:** `page.get_pixmap()` 同期直接呼び出しでフルシリアライズを排除。
- **構造:** `dialogs/` サブパッケージ化、`constants.py` を `lang.py`/`themes.py` に分割（後方互換 import 維持）。
- **API:** `settings` のプライベート変数外部アクセスを公開 API 化（stale binding 解消）。
- **テスト:** Undo 往復・プレビュー回帰・import 回帰を整備。**pytest 199 件全通・ruff クリーン**。
- コードベースマップ: `.planning/codebase/` / マイルストーン詳細: `.planning/milestones/v1.3.0-ROADMAP.md`・`.planning/MILESTONES.md`

</details>

### Next Milestone Goals

- v1.8.0 で吸収済み: PERF-01（サムネイル仮想化）・ShortcutsDialog WR-01/WR-02・開発履歴.md の v1.7.0 表記整合（V16-D-04 残課題）
- 未吸収（将来候補）: human-verify/UAT の実機目視の正式実施（v1.4.0 Phase04・v1.6.0 Phase04・v1.7.1 Phase04 で計3回ユーザー判断により一旦pass・コード/自動ゲートは全通過）

## Evolution

このドキュメントはフェーズ移行・マイルストーン完了時に更新される。

**フェーズ移行後:**
1. 完了した要件 → Validated へ移動（フェーズ番号を付記）
2. 無効になった要件 → Out of Scope へ移動（理由を付記）
3. 新たに発見された要件 → Active へ追加
4. 決定事項 → Key Decisions を更新

---
*Last updated: 2026-07-14 — v1.8.0 Phase 3（OCR実行エンジン抽出 + E2Eテスト）完了. Working branch: dev/v1.8.0.*
