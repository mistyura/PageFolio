# PageFolio — コード最適化プロジェクト

## What This Is

PageFolio の既存コードベースに対する最適化プロジェクト。
バグ修正・リファクタリング・テスト充実の 3 軸で品質を底上げする。

**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする。

## Current Milestone: 未確定（`/gsd-new-milestone` で次マイルストーンを定義する）

v1.9.0 のクローズにより、現在アクティブなマイルストーンはありません。
次の候補は「Next Milestone Goals」を参照してください。

## Last Milestone: v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加 — ✅ Shipped 2026-08-11

> v1.9.0 は全 3 フェーズ（Phase 1〜3・15 プラン）を達成して出荷済み（`APP_VERSION = v1.9.0`・テスト 1404 件グリーン・ruff クリーン）。V190-* 全 27 要件 Complete（被覆 27/27・孤立要件なし）。
> 次マイルストーンは `/gsd-new-milestone` で確定する。

**Goal（達成済み）:** 保存・編集・Undo の失敗時に「操作前の状態へ確実に戻る」安全性を確立し、設定 UI の Apply/Cancel 契約を整合させたうえで、OCR プロバイダ基盤を整理して OpenAI(ChatGPT) を既存プロバイダと同等に追加した。

**Target features（達成済み）:**

1. **保存・編集の安全性（P0/P1）**: パスワード保護PDFの暗号化維持（通常保存/Save As/上書きフォールバック統一・V190-REV-01）・OCR OFF の全経路一貫化（バッチOCR の OFF ガード・`off` をプロバイダ生成不可に・V190-REV-02）・複数ファイル挿入のトランザクション化＋挿入元 Document の `finally` クローズ（V190-REV-03）・ページ複製の Undo 記録を成功後確定（V190-REV-04）
2. **設定 UI の整合性**: 外部プロンプトファイル書き込みを Apply 時へ一本化 or Cancel 時復元（V190-REV-05）・テンプレート切替時の未保存編集確認をファイル連動有無によらず有効化（V190-REV-06）
3. **Undo/Redo 回帰強化**: 復元失敗時のスタック復帰保護と `duplicate`/`merge`/`merge_resize` への 4手往復テスト水平展開（V190-REV-07）
4. **OCR プロバイダ基盤整理 → OpenAI 追加**: プロバイダメタデータ（キー・表示名・クラウド種別・環境変数・既定モデル・送信先・フォールバック可否）の一元定義（V190-REV-08）と、OpenAI(ChatGPT) プロバイダのフル実装（設定UI・セッションAPIキー欄・モデル一覧・送信先確認・コスト確認・バッチOCR対応・フォールバック候補組み込み）
5. **品質保証・持ち越し**: Tkinter 実行環境（Python 3.14.6 / init.tcl）修復と GUI 含む全テスト完走のリリースゲート化・IN-01（保存トースト再試行時の上書き確認再表示）・human-verify / UAT の実機目視を正式実施

**Key context:**
- 出典は `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md`（既存機能レビュー・課題8件と推奨反映順）
- 受け入れ条件に「失敗時に Document・Undo履歴・外部ファイルが操作前の状態へ戻る」ことを明記する
- OCR OFF は通常OCR・バッチOCR・プラグイン経路の全実行経路で同じ意味にする
- OpenAI 追加でも既存の安全境界を維持: APIキーを settings.json に含めない（`_SENSITIVE_KEYS` ガード・V14-D-02）・送信先を明示・フォールバック時に再確認（V180-D-02）
- P0/P1（V190-REV-01〜05）は OpenAI 追加より前に完了させる
- 実装方針は `urllib` 直叩き・新規 pip 依存ゼロ（V14-D-01 踏襲）
- `registry.py` の「Python 標準ライブラリのみ・pagefolio 内部モジュールを import しない」独立性制約（V180-D-01）は維持し、非機密メタデータは別モジュールへ分離する

**実績:**
- Phase 1「保存・編集・設定の安全性是正」— 7/7 プラン・検証 5/5 must-haves（01-06 / 01-07 の 2 回のギャップ是正を経て passed）
- Phase 2「OCR プロバイダ基盤整理 + OpenAI(ChatGPT) 追加」— 4/4 プラン・検証 5/5 must-haves・15/15 要件
- Phase 3「品質保証・リリースゲート」— 4/4 プラン・検証 12/12 must-haves・UAT 19/19 pass（issue 0）。コードレビューで BLOCKER（トースト再試行が別 Document の内容を確定パスへ無確認上書きするデータ損失）を検出し、`bound_doc` による doc 同一性束縛で構造的に解消・回帰テスト 6 件追加。遡及 UAT は実施対象 13 項目 pass / 未実施 2 項目（実 API 課金・`ANTHROPIC_API_KEY` 未設定）
- コードレビュー Critical 0件。セキュリティ監査 threats_open: 0（Phase 1/2 とも verified・ASVS L1）。Nyquist COMPLIANT（3/3 フェーズ validated）
- 技術的負債 10 件（Warning 4 / Info 6）は非ブロッキングとして v1.10.0 へ繰り越し（「Next Milestone Goals」参照）
- マイルストーン詳細: `.planning/milestones/v1.9.0-ROADMAP.md`・`.planning/MILESTONES.md`

<details>
<summary>Previous Milestone: v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化 — ✅ Shipped 2026-07-16</summary>

> v1.8.0 は全 6 フェーズ（Phase 1〜6・22 プラン・53 タスク）を達成して出荷済み（`APP_VERSION = v1.8.0`・テスト 1101 件グリーン・ruff クリーン）。V180-* 全 26 要件 Complete（被覆 26/26・孤立要件なし）。
> 次マイルストーンは `/gsd-new-milestone` で確定する（候補は「Next Milestone Goals」参照）。

**Goal（達成済み）:** 独立してきたコンポーネント（OCR・LLMプロバイダー・UI）のシナジーを高め、シームレスで高度なドキュメント処理・要約環境を構築した。

**Target features（達成済み）:**

1. **AI強化**: 名前付きプロンプトテンプレート CRUD（保存/選択/削除/リネーム・外部mdファイル連動・全プロバイダ横断共有）・明示設定型プロバイダーフォールバック（送信先確認再提示つき・自動別ベンダー送信なし）
2. **堅牢性**: サムネイル窓内可視範囲仮想化・`thumb_cache` LRU化・Blob ライフサイクルのリーク検出強化（Windows AV スキャン衝突安全網）・`ocr_providers.py`/`llm_config.py` の責務別パッケージ分割・`_SENSITIVE_KEYS` 中央レジストリ化（`registry.py`）・ShortcutsDialog WR-01/WR-02 解消
3. **品質保証**: `OCRRunEngine` 抽出による OCR→サマリ E2E モックテスト整備・再試行アクション付き非モーダルトースト通知・UI 一貫性監査（スクロール/フォントスケーリング是正）・開発履歴.md 版番整合（V16-D-04 解消）
4. **バッチ複数ファイル OCR**: 独立 `BatchOCRDialog` で複数 PDF の D&D 一括投入・ファイル単位失敗分離・2階層キャンセル・ファイル横断統合サマリ（単独フェーズ隔離・fitz メインスレッド制約遵守）

**Key context:**
- Core Value 直撃バグ（`insert_redo` 非対称復元によるページ重複）を Phase 6 で発見・修正（`delete_redo` 対称パターンへ・D-17）
- プロバイダーフォールバックは「明示設定型」限定を貫徹（自動ベンダー切替は不採用のまま）
- コードレビュー Critical 0件（Warning 3件は Phase 6 で即時修正・回帰テスト追加。WR-01 OCRダイアログ高さクランプ・WR-02 プラグインダイアログスクロール再発・WR-03 トースト retry_cb 取りこぼし）。セキュリティ監査 threats_open: 0（脅威4件 closed）
- 人手 UAT 2件（Phase 6・トースト視認性/マウスホイール操作感）はユーザー実施で全合格
- APP_VERSION バンプがフェーズ実行中は行われず、マイルストーンクローズ時に検出・修正（v1.7.4 → v1.8.0）
- マイルストーン詳細: `.planning/milestones/v1.8.0-ROADMAP.md`・`.planning/MILESTONES.md`

</details>

> 補足: v1.6.1〜v1.7.0（パスワード/印刷・Ollama/RunPod・バグ修正・サマリ安定化・黒塗り/モザイク・undo ディスク退避）は GSD フェーズ外のポイントリリースとして出荷済み。詳細は `.planning/MILESTONES.md` 参照。

<details>
<summary>Previous Milestone: v1.7.1 現機能ブラッシュアップ + APIキー入力欄 — ✅ Shipped 2026-07-05</summary>

> v1.7.1 は全 4 フェーズ（Phase 1〜4・16 プラン・41 タスク）を達成して出荷済み（`APP_VERSION = v1.7.1`・テスト 859 件グリーン・ruff クリーン）。V171-* 全 17 要件 Complete（被覆 17/17・孤立要件なし）。

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
- コードレビュー Critical 0件（Warning 2件は ShortcutsDialog の非致命的 UX 課題・follow-up 候補。v1.8.0 Phase 5 で解消済み）。セキュリティ監査 threats_open: 0（脅威8件 closed）
- 人手 UAT 7件はユーザー判断で一旦 pass（実機目視未検証・コード/自動ゲートは全通過、v1.6.0 Phase 4 と同様の運用）

</details>

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
| テスト | pytest（1404 件・充実） |
| リント | ruff |
| リリースゲート | 単一プロセス `pytest -q` 完走（失敗0・ERROR0・クラッシュなし）。詳細は `CLAUDE.md`「## リリースゲート」節 |

既存コードベースマップ: `.planning/codebase/`

## Constraints

正本は [../CLAUDE.md](../CLAUDE.md)。以下はプランニング時に踏まえるべき要約。

- **Tech stack**: Python 3.8+ / Tkinter（Windows 11 対象）。PyMuPDF 1.28.0（`fitz`）/ Pillow 12.3.0 / tkinterdnd2 0.6.2、配布は PyInstaller 6.21.0 の onedir。`pyproject.toml` の編集は禁止
- **互換性**: 既存の PDF 操作・OCR プロバイダのインターフェースを壊さない。Undo は操作固有のデルタ dict（full PDF シリアライズではない）で `MAX_UNDO = 20`。ページ単位キャプチャは必ず `_capture_page_blob()` / 復元は `self._blob_bytes()` を経由し、スタックへの直接 `append`/`clear` は禁止（Blob がリークする）
- **スレッド制約**: UI は Tkinter メインスレッド。プレビュー・サムネイル描画は `root.after()` チェーンでメインスレッド処理し、世代カウンタ（`_preview_gen` / `_thumb_gen`）で stale 結果の上書きを防ぐ。OCR は `ThreadPoolExecutor`、fitz のスレッド制約によりバッチ OCR のファイル間は逐次処理
- **CropBox 安全処理**: トリミングは必ず CropBox を MediaBox 内へクランプしてから `set_cropbox()` を呼ぶ（`pagefolio/page_ops.py`）。回転表示中は `_derotate_rect` で表示座標→未回転座標へ変換する
- **品質ゲート**: py ファイル編集後に `ruff check . && ruff format .`、コミット前に `pytest`。リリース判定は `CLAUDE.md`「## リリースゲート」節（単一プロセス完走・失敗0・ERROR0・クラッシュなし）
- **言語**: コミット/PR/コメント/ユーザー応答は日本語、変数名・関数名・クラス名は英語（CLAUDE.md 準拠）
- **禁止**: `pyproject.toml` 編集、裸の `except:`、無断の `# type: ignore`、テーマ色のハードコード（`C["KEY"]` を使う）、フォントサイズのハードコード（`self._font(delta)` を使う・`tests/test_font_hardcode_guard.py` がソーススキャンで検出）
- **Security**: API キーは `pagefolio_settings.json` に保存しない（`_SENSITIVE_KEYS` ガードで除外・セッション限定）。`pagefolio/ocr_providers/registry.py` は Python 標準ライブラリ（`os`）のみに依存し、pagefolio 内部の他モジュールを import しない（循環 import の構造的防止・V180-ROBUST-02）
- **ブランチ運用（v1.10.0 以降）**: `main` へ直接コミット・直接 push しない。詳細は下記 `## ブランチ運用` を参照

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
- ✓ V180-PERF-01/02/03・V180-ROBUST-01・V180-ROBUST-03: サムネイル窓内可視範囲仮想化（`pagination.py` 純関数 + `viewer.py` 統合・デバウンス+アイドル先読み）・`thumb_cache` LRU化（`LruCache`・`THUMB_CACHE_MAX=300`）・`selected_pages` 全ページインデックス不変条件回帰・Blob ライフサイクルのリーク検出強化（`_released`+`__del__`・AV衝突安全網の回帰テスト）・ShortcutsDialog WR-01/WR-02 解消 — v1.8.0 Phase 5
- ✓ V180-QA-02/03/04: 再試行アクション付き非モーダルトースト通知（保存3操作+印刷・`ToastManager`新設）・UI一貫性監査（スクロール/フォントスケーリング是正・8ファイル監査）・開発履歴.md 版番整合（V16-D-04 残課題解消）。あわせて Core Value 直撃バグ（`insert_redo` 非対称復元・ページ重複）を修正（D-17） — v1.8.0 Phase 6
- ✓ V190-QA-01/02/03: Tkinter 実行環境の切り分け（現行 HEAD で `TclError` セットアップ ERROR・`STATUS_BREAKPOINT` クラッシュとも非再現・累計17回連続グリーンを一次データで反証しコード変更ゼロでクローズ）とリリースゲートの合格条件確定（`CLAUDE.md`「## リリースゲート」節・単一プロセス `pytest -q` 完走）・保存トースト再試行の確認再表示解消（確認/パス選択層と実保存層 `_do_save_*` の分離・`functools.partial` によるパス束縛と `bound_doc` による doc 同一性ガード）・遡及 human-verify/UAT の正式実施（実施13 / 未実施2〔実 API 課金・`ANTHROPIC_API_KEY` 未設定〕/ 対象外1 = 計16） — v1.9.0 Phase 3（検証 12/12 must-haves・UAT 19/19 pass・issue 0）
- ✓ V190-CAT-01/02・V190-OAI-01〜13: プロバイダメタデータの単一情報源化（`ocr_providers/catalog.py` 新設・`registry.py` の標準ライブラリのみ依存の独立性制約は維持）と OpenAI(ChatGPT) プロバイダのフル実装（`urllib` 直叩き・新規 pip 依存ゼロ・セッション限定 API キー・モデル一覧取得と静的フォールバック・送信先/コスト確認・バッチ OCR 対応・フォールバック候補組み込み・detail / reasoning effort / organization / project の設定と永続化） — v1.9.0 Phase 2（検証 5/5 must-haves・15/15 要件・実機 human-verify 3 件合格）

### Active

**なし** — v1.9.0 クローズにより全 27 要件（V190-*）が Validated へ移動済み。次マイルストーンの要件は `/gsd-new-milestone` で定義する。

以下は次マイルストーンの要件候補として引き継ぐ申し送り（要件化はまだされていない）:

- **遡及 UAT の未実施 2 項目** — ③ max_tokens クランプ・429 リトライの実 API 検証（V16-QUAL-03 由来）／⑤-Claude の実 API 出力品質（`ANTHROPIC_API_KEY` 未設定）。実 API キー・課金が用意できた時点で消化する。詳細は `milestones/v1.9.0-phases/03-qa-release-gate/03-UAT-RESULTS.md`「## 未実施（理由付き・D-14）」
- **技術的負債 10 件（v1.9.0 コードレビュー由来・Warning 4 / Info 6）** — `page_ops.py` 側の WR-03〜WR-06（一時 Document の finally 保護・insert base op の無意味な Undo エントリ・watermark/page-number ループの例外保護）は `file_ops.py` 側で既に解消済みのパターンの水平展開であり一括で閉じやすい。`file_ops.py` の WR-01（`content_at_risk` が立たない経路）／WR-02（`os.replace` 失敗時の `.tmp` 残置）、Phase 2 の WR-01/02（バッチ OCR コピペ移植の divergence リスク・エラー種別区別の粗さ）・IN-01（`OCR_PRICE_TABLE` の宣言順依存）も同様に非ブロッキング
- **追跡外一時ディレクトリ `UsersshdwfAppDataLocalTemppfb/`** — 過去セッションの pytest basetemp 誤設定の残骸（161 ファイル）が `ruff check .`（無限定）を 31 件のエラーで汚染する。`.gitignore` 追加または削除が望ましい（Phase 3 検証で Info として記録）
- **PyInstaller `--noconfirm` ビルドでサンプルプロンプト 2 ファイルが毎回消える恒久課題** — ソースツリー側へ原本移設 + ビルド後コピーのスクリプト化（260722-rel SUMMARY 由来）
- **新世代 Gemini の temperature 無視に関する UI 注記** — v1.9.0 Phase 2 で OpenAI o-series の temperature 拒否を同型パターンとして扱えるか検討したが未着手（260722-gae 精査項目 3 ②③）

v1.8.0 全 26 要件（V180-*）・v1.9.0 全 27 要件（V190-*）はいずれも上記 Validated へ移動済み。

### Out of Scope

- OS キーストア連携（Windows Credential Manager）による APIキー永続化 — セッション限定方針を維持（V14-D-02 踏襲）。永続化は別マイルストーン判断
- OAuth 接続 — 正規 API が非対応・配布バイナリに client secret を埋め込めないため確定除外
- OCR 結果のページ埋め込み（検索可能 PDF 化） — v1.4.0 から継続除外
- プラグイン API バージョン管理 — 今後の別タスク

## ブランチ運用

v1.10.0 以降に適用。2026-08-12 に確立。**`main` へ直接コミット・直接 push しない。** PageFolio は v1.9.0 を 2026-08-11 に出荷済みで次マイルストーンが未定のため、本ルールの実運用開始は次マイルストーン（v1.10.0 以降）からとなる。

姉妹プロジェクト **numbers**（`feature/v0.18.0`・2026-08-12 確立）を原典とし、**loto**（`main`・2026-08-12 確立）が踏襲した構成に合わせたもの。3 プロジェクトで `.planning/config.json` の `git` セクションは同値。

### 設定（`.planning/config.json` の `git` セクション）

| キー | 値 | 効果 |
|---|---|---|
| `branching_strategy` | `milestone` | マイルストーン最初の `/gsd-execute-phase` でブランチを作成・切替し、そのマイルストーンの全フェーズが同一ブランチへコミットする |
| `milestone_branch_template` | `feature/{milestone}` | PageFolio がこれまで手作業で使ってきた命名（v1.5.0 = `feature/v1.5.0-improvements` → PR #18）を config 化したもの。v1.7.x / v1.8.0 で使われた `dev/v{version}` 系の揺れをこれに一本化する |
| `quick_branch_template` | `quick/{num}-{slug}` | `/gsd-quick` `/gsd-fast` が quick 用ブランチを作る。`{num}` は `.planning/quick/` の採番と同じ quick ID（例 `quick/260812-abc-<slug>`） |

`phase_branch_template` は `branching_strategy: milestone` では使われないが、将来 `phase` へ切り替える場合に備えて既定値のまま残している。

人間向けの開発ガイドとしての同じ規約は [../docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md)「ブランチ運用」「PR プロセス」節と [../CONTRIBUTING.md](../CONTRIBUTING.md) にある（quick `260812-9ev` で整備）。本節は GSD ワークフローが従う正本。

### 分岐元とマージ先

- **フェーズ作業** — `feature/v{version}` 上で行う。`main` へは `/gsd-complete-milestone` のタイミングで PR 経由で一度だけ統合する
- **quick task** — **現行マイルストーンブランチから分岐し、同じブランチへ戻す**。`main` を base にしない
- config が決めるのは**ブランチ名だけ**であり、分岐元は `/gsd-quick` を実行した時点の HEAD で決まる。**quick task を始める前に現在のブランチを確認すること**

### なぜ quick task を `main` へ入れないか

PageFolio は `branching_strategy: "none"` / `quick_branch_template: null` のまま feature ブランチ運用を手作業で行っていたため、config と実運用が乖離していた。v1.8.1 までは PR で統合していた（v1.7.x = PR #30 / merge commit `f2ead82` / 2026-07-05、v1.8.0 = PR #33 / merge commit `8b8b423` / 2026-07-16、v1.8.1 = PR #34 / merge commit `8741bad` / 2026-07-22）が、**v1.9.0 マイルストーンは分岐せず `main` 上で全工程が進行した** — `8741bad` 以降マージコミットは存在せず、2026-07-22〜2026-08-12 の **163 コミット**が `main` の first-parent 上にある。quick task も同様に `main` へ直接入っていた（`260810-f1u` = `a553df7`、`260811-asq` = `3f83067`、`260812-9ev` = `467b092` / `293bb53`）。ブランチ命名も `dev/v1.7.x` / `dev/v1.8.0` / `feature/v1.5.0-improvements`（PR #18）/ `feature/add-ollama-runpod`（PR #26）と揺れていた。

姉妹プロジェクト **numbers** で実際に発生した事故（PageFolio では発生していない、横展開の教訓）: `feature/v0.17.0` が 2026-07-04 に分岐し、2026-07-21 に `main` へ入った quick 3 件（`260721-8hr` = `--mode=scenario` の独立実装 / `260721-9ht` = `make scenario` / `260721-bfc` = `make optimize`、うち `260721-bfc` の `b44b665` を `main` 上で確認）を取り込まないまま進んだ結果、Phase 18（2026-07-26）が **5 日前に `main` で実装済みの機能を作り直していた**。マージ（`cf3bec0` / 2026-08-02）時に一方の実装を破棄する判断が必要になり、さらにクローズ監査の W-1（「実在しない `make optimize` の文書化」）が**誤検出**として発生し revert された（`309fca6` / 2026-08-02。監査が `feature/v0.17.0` の Makefile しか見ておらず、`main` には当該ターゲットが実在していた）。PageFolio の v1.9.0 は `main` 単線で進んだため二重実装には至っていない — あくまで同じ非対称構造から事故が起きうることの実例として参照する。

分岐元をマイルストーンブランチへ揃えれば、この二重実装と監査の誤検出はいずれも原理的に起きない。

### 例外を要する場合

マイルストーン進行中に `main` へ直接入れたい緊急修正が出たときは、**`main` から分岐して `main` へ PR で入れたうえで、直ちに `feature/v{version}` へ `main` を取り込む**こと。取り込みを後回しにすると二重実装リスクが戻る。

## フェーズ完了 DoD

**DoD 本文:** フェーズを完了扱いにする前に `/gsd-validate-phase <番号>` を実走し、対応する `NN-VALIDATION.md` の frontmatter を `status: validated` にすること。

**強制点:** `tests/test_gsd_dod.py::test_completed_phases_are_validated` が `pytest` で自動収集され、適用範囲のフェーズと `NN-VALIDATION.md` の status の乖離を機械的に検知する。「ドキュメントに書いてあるだけでは実行されない」ため、機械ゲートを正本とする（姉妹プロジェクト loto は v0.17.0 で 6 フェーズ全てに validate-phase が走らないまま milestone close まで進み、audit の段階で初めて発覚した。その教訓の横展開）。

**許容条件:** 本ゲートが要求するのは `status: validated` のみで、`nyquist_compliant: false`（validate は走ったがギャップが残る PARTIAL 状態）は許容する。強制するのは「検証を走らせたこと」であり、ギャップをゼロにするコストを常にフェーズ内に抱え込ませない。

**適用範囲: v1.9.0 以降。** ライブの `.planning/phases/*/` と、`.planning/milestones/v{X.Y.Z}-phases/*/` のうちバージョンが v1.9.0 以上のもの。出荷済みフェーズも close 後に検証され続けるため、「アーカイブすればゲートを回避できる」抜け穴はない。`.planning/milestones/` 直下（`v*-phases/` の階層を挟まない配置）は対象外。

**v1.9.0 未満を除外している理由:** v1.4.0 / v1.6.0 / v1.7.1 / v1.8.0 の `*-VALIDATION.md` は `/gsd-validate-phase` の出力ではなく別種のドキュメントで、status 語彙が `approved` / `ready` / `draft` / `planned` / `complete` と揃っておらず、欠落しているフェーズもある。遡及的な生成・修正は行わない（loto の「v0.17.0 以前への遡及生成は見送り確定」と同じ判断）。ただし「除外すれば通る」抜け穴にしないため、除外対象の集合そのものを `test_legacy_exclusions_match_repository` が実ディレクトリと突き合わせて機械固定しており、**除外を増やすにはテスト内の定数を明示的に書き換える必要がある**。

**loto 実装との設計差分:** loto は `ROADMAP.md` の `## Progress` 進捗表から `Status == Complete` の行を拾ってフェーズ番号でディレクトリを解決するが、PageFolio では 3 つの前提が成立しないため走査の入口をディレクトリ列挙へ差し替えている。(1) PageFolio の `## Progress` はマイルストーン単位の表で `Phase` 列を持たない、(2) フェーズ番号をマイルストーンごとに 1 起点へリセットするため番号から一意に解決できない、(3) PyYAML が未インストールのため frontmatter の最小パーサを自前で持つ（新規依存を増やさない）。

**red になったときの対処:** 該当フェーズに対して `/gsd-validate-phase <番号>` を実走する。ギャップ提示では「Skip — mark manual-only」を選べば `nyquist_compliant: false` の PARTIAL のまま `status: validated` にできる。

参照: [../tests/test_gsd_dod.py](../tests/test_gsd_dod.py) / [quick/260812-and-dod/260812-and-SUMMARY.md](quick/260812-and-dod/260812-and-SUMMARY.md)

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
| V16-D-04：出荷バージョンを v1.6.0 に確定（途中 v1.7.0 へ一時バンプ後 49e9893 で巻き戻し） | APP_VERSION/README/GSD ラベルの一致を優先。開発履歴.md の v1.7.0 エントリは v1.6.0 へ整合予定 | ✅ 解消済み（06-CHANGELOG-AUDIT.md 参照・v1.8.0 Phase 6 で開発履歴.md の日付/版番整合を git タグ履歴・APP_VERSION 変更履歴・MILESTONES.md と突合し確認。懸念されていた v1.7.0 バンプの痕跡は現存せず、v1.6.1 の日付誤記1件を検出・修正） |
| V16-D-05：Phase 4 human-verify をユーザー判断でスキップしクローズ | コード・自動ゲートは全通過。実描画/実 API 出力品質のみ未検証で deferred 受容 | ⚠️ Revisit（必要時に実機目視） |
| V171-D-14：ネスト LLMConfigDialog 適用は `app._apply_llm_settings_live`（`_rebuild_ui()` を呼ばない軽量反映）を独立トランザクション化 | nested on_apply から `_rebuild_ui()` を呼ぶと開いている SettingsDialog Toplevel ごと破棄されるため。ディスク/メモリ整合を cascade テストで担保 | ✓ Good（v1.7.1 Phase 4） |
| V171-D-11：未使用 LANG キー検出は引用符付き完全一致（AST走査不採用） | 動的キー合成がコードベース全体でゼロ件（確認済み）のため grep 相当で十分。プレフィックス衝突（`tesseract_not_installed` 等）は完全一致で誤削除を回避 | ✓ Good（v1.7.1 Phase 4・回帰テスト常設） |
| V171-D-05：ShortcutsDialog は保存ボタン押下まで一時コピー（`self._shortcuts`）のみ編集し、実バインド/settings へは未反映（キャンセルで無効化） | 実キーキャプチャの GUI 化で誤操作時の即時反映事故を防ぐ | ✓ Good（v1.7.1 Phase 4） |
| V180-D-01：プロバイダ→環境変数マッピングの中央レジストリ `registry.py` は Python 標準ライブラリのみに依存し pagefolio 内部モジュールを import しない | settings.py 等から参照される際の循環 import を構造的に防止。新プロバイダ追加時の機密キー定義追加を1ファイルに閉じる | ✓ Good（v1.8.0 Phase 1・V180-ROBUST-02） |
| V180-D-02：プロンプトテンプレートは名前付き保存・全プロバイダ横断共有、フォールバックは明示設定型のみ（自動ベンダー切替は不採用） | 送信先確認ダイアログの再提示を必達とし外部送信の明示同意方針と整合させる | ✓ Good（v1.8.0 Phase 2） |
| V180-D-03：`OCRRunEngine` を独立モジュールとして抽出し単一ファイル OCR とバッチ OCR で共用 | producer-consumer 駆動部の重複実装を避け、バッチ OCR 実装の土台を先に固める | ✓ Good（v1.8.0 Phase 3・Phase 4 が再利用） |
| V180-D-04：バッチ OCR は単独フェーズへ隔離し、`fitz.Document` のスレッド間共有を避けてファイル間は逐次処理 | 大型機能を他の柱と混在させず、fitz のスレッドセーフ制約を構造的に遵守 | ✓ Good（v1.8.0 Phase 4） |
| V180-D-05：サムネイル仮想化・LRUキャッシュは `pagination.py`/`thumb_cache.py` の Tk/fitz 非依存純関数層に集約 | 可視範囲計算・キャッシュ eviction を単体テスト可能にし、viewer.py への統合を薄く保つ | ✓ Good（v1.8.0 Phase 5） |
| V180-D-17：`insert_redo` は `delete_redo` 対称パターン（降順 `delete_page`）へ修正し、修正範囲を `_restore_state` の insert_redo ブロックのみに限定 | Core Value 直撃バグ（insert→undo→redo→undo でページ重複）を最小差分で解消し他 op の対称性を壊さない | ✓ Good（v1.8.0 Phase 6・4手往復回帰テストで担保） |
| V190-D-QA01：テスト環境の2症状（`TclError` / `STATUS_BREAKPOINT`）は「調べる前に直さない」— 現行 HEAD で 10 回連続再現試行を行い、非再現ならコード変更ゼロで反証データ付きに閉じる | 予防的な `TCL_LIBRARY`/`TK_LIBRARY` ハードコード（PITFALLS Pitfall 13 が警告）を入れずに済み、次マイルストーンが同じ地面を掛け直さない一次データが残る | ✓ Good（v1.9.0 Phase 3・累計17回連続グリーン・`03-TEST-ENV-INVESTIGATION.md`） |
| V190-D-QA02：リリースゲートは単一プロセス `pytest -q` 完走を合格条件とし、テストの削除・skip・`-k`/`--ignore` による静かな除外を禁止事項として明記 | 分割実行という回避策に逃げずゲートを1コマンドに固定できる統計的根拠が得られた。除外による「見かけの合格」を構造的に封じる | ✓ Good（v1.9.0 Phase 3・`CLAUDE.md`「## リリースゲート」節） |
| V190-D-QA03：保存トーストの再試行は確認/パス選択層と実保存層（`_do_save_*`）を分離し、`functools.partial` で確定パスを、`bound_doc` で Document 同一性を束縛する | パスのみ束縛して `self.doc` を都度参照すると、トースト表示中に別ファイルを開いた場合に無関係な Document を確定パスへ無確認上書きする（コードレビュー CR-01・データ損失 BLOCKER）。doc 同一性ガードで構造的に排除 | ✓ Good（v1.9.0 Phase 3・回帰テスト6件で担保） |

## Current State

**Shipped: v1.9.0 安全性・整合性の是正 + OpenAI プロバイダ追加 (2026-08-11)** — 3 フェーズ / 15 プラン。`APP_VERSION = v1.9.0`（テスト 1404 件グリーン・ruff クリーン）。V190-* 全27要件 Complete（被覆27/27・孤立要件なし）。

- **保存・編集の安全性:** 保存3経路＋縮小保存に `encryption=PDF_ENCRYPT_KEEP` を構造的に既定化しパスワード保護 PDF の平文化を全経路で排除。`pdf_has_password` を `derive_pdf_has_password` 純関数で単一導出化。
- **OCR OFF の全経路一貫化:** `build_provider` の `off` 分岐を専用例外 `OCRDisabledError` で拒否し、通常 OCR・バッチ OCR・ダイアログ内 provider 再生成・メニュー入口の 4 経路を同一の意味へ統一。
- **失敗時ロールバックの構造化:** 複数ファイル挿入の巻き戻し＋`finally` クローズ・ページ複製の Undo 記録後置化・`_undo`/`_redo` 復元失敗時の `_push_evicting` による state 保全とブロッキング通知。部分失敗→再試行後に逆デルタが縮小するサイレントなページ破損を 7 op で解消（`_pending_inverse` 方式）。`page_edit` の 2 段階 mutation を順序反転（`insert_pdf`→`delete_page`）してページ内容の恒久喪失を構造的に排除。
- **設定 UI の Apply/Cancel 契約:** 外部プロンプトファイルへの書き込みを Apply 押下時の 1 経路へ一本化し、テンプレート切替の未保存確認をファイル連動有無に依存しない単一判定へ統一。
- **OCR プロバイダ基盤整理:** `ocr_providers/catalog.py` を新設しプロバイダメタデータ（キー・表示名・クラウド種別・環境変数・既定モデル・送信先ホスト・フォールバック可否）を単一情報源化（6/6 参照面移行完走）。`registry.py` の標準ライブラリのみ依存の独立性制約は維持。
- **OpenAI(ChatGPT) プロバイダ:** `urllib` 直叩き・新規 pip 依存ゼロで実装。セッション限定 API キー・モデル一覧の実 API 取得＋静的フォールバック・送信先/コスト確認・バッチ OCR 対応・明示設定型フォールバック候補・detail / reasoning effort / organization / project の設定と永続化。実機確認で API キー未送信の実バグを発見・修正。
- **品質保証・リリースゲート:** テスト環境の 2 症状（`TclError` セットアップ ERROR・`STATUS_BREAKPOINT` クラッシュ）を 10 回連続実行で非再現と一次データで反証しコード変更ゼロでクローズ（累計 17 回連続グリーン）。リリースゲートを単一プロセス `pytest -q` 完走に確定。保存トースト再試行の確認再表示を確認層/実保存層の分離で解消し、コードレビュー BLOCKER（別 Document の無確認上書き）を `bound_doc` の同一性ガードで構造的に排除。遡及 human-verify/UAT を正式実施（実施 13 / 未実施 2 / 対象外 1）。
- コードレビュー Critical 0件。セキュリティ監査 threats_open: 0（Phase 1/2 とも verified・ASVS L1）。Nyquist COMPLIANT（3/3 validated）。UAT 19/19 pass・issue 0。
- 技術的負債 10 件（Warning 4 / Info 6）は非ブロッキングとして v1.10.0 へ繰り越し。
- マイルストーン詳細: `.planning/milestones/v1.9.0-ROADMAP.md`・`.planning/MILESTONES.md`

<details>
<summary>Shipped: v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化 (2026-07-16)</summary>

**Shipped: v1.8.0 実用性の最大化・エコシステム洗練・堅牢性強化 (2026-07-16)** — 6 フェーズ / 22 プラン / 53 タスク。`APP_VERSION = v1.8.0`（テスト 1101 件グリーン・ruff クリーン）。V180-* 全26要件 Complete（被覆26/26・孤立要件なし）。

- **基盤分割:** `ocr_providers.py`/`dialogs/llm_config.py` を責務別パッケージへ分割し、プロバイダ→環境変数の中央レジストリ `registry.py` を新設（`_SENSITIVE_KEYS` 中央化）。
- **AI強化:** 名前付きプロンプトテンプレート CRUD（外部mdファイル連動・全プロバイダ横断共有）と明示設定型プロバイダーフォールバック（送信先確認再提示つき）を実装。
- **OCR実行エンジン抽出:** `ocr_dialog.py` から `OCRRunEngine` を抽出し単一/バッチ OCR で共用可能化、実スレッド駆動の E2E モックテストを整備。
- **バッチ複数ファイルOCR:** 独立 `BatchOCRDialog` で D&D 一括投入・3列Treeview二段進捗・2階層キャンセル・ファイル横断統合サマリを実装。
- **堅牢性強化:** サムネイル窓内可視範囲仮想化・`thumb_cache` LRU化・Blob リーク検出強化（Windows AV 衝突安全網）・ShortcutsDialog WR-01/WR-02 解消。
- **品質保証仕上げ:** 再試行付き非モーダルトースト通知・UI一貫性監査（スクロール/フォント是正）・Core Value 直撃バグ（`insert_redo` 非対称復元）修正・開発履歴.md 版番整合（V16-D-04 解消）。
- コードレビュー Critical 0件（Warning 3件は Phase 6 で即時修正・回帰テスト追加）。セキュリティ監査 threats_open: 0（脅威4件 closed）。人手UAT 2件（Phase 6）は全合格。
- マイルストーン詳細: `.planning/milestones/v1.8.0-ROADMAP.md`・`.planning/MILESTONES.md`

</details>

<details>
<summary>Shipped: v1.7.1 現機能ブラッシュアップ + APIキー入力欄 (2026-07-05)</summary>

**Shipped: v1.7.1 現機能ブラッシュアップ + APIキー入力欄 (2026-07-05)** — 4 フェーズ / 16 プラン / 41 タスク。`APP_VERSION = v1.7.1`（テスト 859 件グリーン・ruff クリーン）。V171-* 全17要件 Complete（被覆17/17・孤立要件なし）。

- **APIキー入力欄:** LLMConfigDialog に Claude/Gemini/RunPod のマスク付き入力欄・トグル・セッション限定注記を追加。解決優先順を「入力値→環境変数」へ反転し、OCRDialog の旧セッションキー UI を撤去して導線を一元化（送信先確認ダイアログの RunPod 誤開示 CR-01 も解消）。
- **OCR 磨き込み:** プラグイン OCR registry 堅牢化（重複名ポリシー・unload 解除・公開アクセサ）・Tesseract 言語の段階的縮退フォールバック・producer-consumer 実行パイプラインを新設 `ocr_pipeline.py` へ一本化・L-6 小物一括解消。
- **ページ操作磨き込み:** 画像（ロゴ）透かし対応・黒塗り/モザイクの連続適用+粒度スライダー・`_derotate_rect` 共通ヘルパーで回転座標を統一。
- **UI/UX 磨き込み:** ShortcutsDialog 新設（実キーキャプチャ・重複拒否）・SettingsDialog 3セクション再編・LLMConfigDialog 共通/固有整理・i18n/エラー表示一貫性監査（未使用キー11件削除）。
- コードレビュー Critical 0件（Warning 2件は ShortcutsDialog の非致命的 follow-up 候補・v1.8.0 Phase 5 で解消済み）。セキュリティ監査 threats_open: 0（脅威8件 closed）。人手UAT 7件はユーザー判断で一旦pass（実機目視未検証・コード/自動ゲートは全通過）。
- マイルストーン詳細: `.planning/milestones/v1.7.1-ROADMAP.md`・`.planning/MILESTONES.md`

</details>

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

**v1.9.0 で吸収済み:** IN-01（保存トースト再試行の確認再表示・V190-QA-02）、4手往復回帰テストの `duplicate`/`merge`/`merge_resize` への水平展開（V190-UNDO-02）、human-verify/UAT の実機目視の正式実施（V190-QA-03・v1.4.0/v1.6.0/v1.7.1 で 3 回続いた「一旦 pass」運用の解消）、Tkinter 実行環境問題のクローズ（V190-QA-01）。

**v1.10.0 候補（v1.9.0 由来・優先度順）:**

1. **技術的負債 10 件の解消** — `page_ops.py` 側 WR-03〜WR-06 は `file_ops.py` 側で解消済みパターンの水平展開で一括処理しやすい。`file_ops.py` WR-01/02、Phase 2 の WR-01/02・IN-01 も同枠
2. **未実施 UAT 2 項目の消化** — max_tokens クランプ・429 リトライの実 API 検証（V16-QUAL-03 由来・v1.6.0 から 3 マイルストーン持ち越し）／⑤-Claude 実 API 出力品質。実 API キー・課金の用意が前提
3. **バッチ OCR の divergence 構造の解消** — `dialogs/batch_ocr.py` のコピペ移植（v1.8.0 Phase 4 の意図的判断）が単発版とのズレを構造的に許容している。共通化の是非を判断する
4. **リポジトリ衛生** — 追跡外 `UsersshdwfAppDataLocalTemppfb/` の削除 or `.gitignore` 追加、PyInstaller ビルドでサンプルプロンプトが消える恒久課題のスクリプト化

**v2 候補（STATE.md「Deferred Items」参照）:** バッチ OCR のバックグラウンド常駐継続・ジョブ永続化（BATCH-F01/F02）、プロンプトテンプレートのバージョン履歴/差分表示（TMPL-F01）、サムネイルの react-window 相当本格仮想化（PERF-F01）、OpenAI Responses API 移行（V190-F-01）、organization/project ID 自動検出（V190-F-02）、セッション API キー同期ループの完全動的化（V190-F-03）、OS キーストア連携による API キー永続化。

## Evolution

このドキュメントはフェーズ移行・マイルストーン完了時に更新される。

**フェーズ移行後:**
1. 完了した要件 → Validated へ移動（フェーズ番号を付記）
2. 無効になった要件 → Out of Scope へ移動（理由を付記）
3. 新たに発見された要件 → Active へ追加
4. 決定事項 → Key Decisions を更新

---
*Last updated: 2026-08-12 quick 260812-and — `## フェーズ完了 DoD` 節を `## ブランチ運用` の直後に新設し、機械ゲート `tests/test_gsd_dod.py`（6 テスト）を追加。適用範囲は v1.9.0 以降で、v1.9.0 未満の除外集合はテストが実ディレクトリと突き合わせて固定する。loto 実装は前提（ROADMAP の Phase 列 / フェーズ番号の連番性 / PyYAML）が PageFolio で成立しないため走査の入口をディレクトリ列挙へ差し替えた。3 プロジェクト比較の差分 #1〜#5 がこれで全て完了。前回更新: 2026-08-12 quick 260812-a8u — `## Constraints` 節を `## Context` の直後に新設（9 項目・正本は CLAUDE.md でその要約）。260812-9tv で暫定的に `## Context` 表へ置いていたブランチ運用ポインタを Constraints 末尾へ移設し、loto/numbers と同型（末尾がブランチ運用ポインタ）にした。CLAUDE.md・`pagefolio/` ソースは無変更。前回更新: 2026-08-12 quick 260812-9tv — ブランチ運用を姉妹プロジェクト（numbers `feature/v0.18.0` が原典・loto `main` が踏襲）と統一。`.planning/config.json` の `git` セクション 3 キー（`branching_strategy` = `milestone` / `milestone_branch_template` = `feature/{milestone}` / `quick_branch_template` = `quick/{num}-{slug}`）を 3 プロジェクト同値へ更新し、`## ブランチ運用` 節（5 部構成）を `## Key Decisions` の直前に新設、`## Context` 表へ入口 1 行を追加。発効は v1.10.0 以降。`git` 以外の config セクション・`pagefolio/` ソースは無変更。前回更新: 2026-08-11 after v1.9.0 milestone — マイルストーンクローズに伴う全項目の進化レビュー実施。v1.9.0 を Current State へ昇格し v1.8.0 以前を `<details>` へ格納、Context のテスト件数を実測 1404 件へ同期しリリースゲート行を追加、Active を空にして次マイルストーン候補（技術的負債 10 件・未実施 UAT 2 項目ほか）を Next Milestone Goals へ整理。Core Value・Out of Scope は再確認のうえ変更なし。前回更新: 2026-08-11 Phase 3 UAT 完了。*
