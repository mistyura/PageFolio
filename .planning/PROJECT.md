# PageFolio — コード最適化プロジェクト

## What This Is

PageFolio の既存コードベースに対する最適化プロジェクト。
バグ修正・リファクタリング・テスト充実の 3 軸で品質を底上げする。

**Core Value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする。

## Last Milestone: v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト — ✅ Shipped 2026-06-16

> v1.5.0 は全 4 フェーズ（Phase 1〜4）を達成して出荷済み（`APP_VERSION = v1.5.0`）。
> 実装は `feature/v1.5.0-improvements` ブランチで別ワークフローにより完了し、2026-06-16 に文書を整合。
> 次マイルストーンは `/gsd-new-milestone` で確定する（候補は「Next Milestone Goals」参照）。

**Goal（達成済み）:** PDF 編集の基本機能を底上げ（白紙ページ挿入・テキスト透かし／ページ番号・TOC 保持）、UI/UX を改善（サムネイルサイズ動的変更・D&D 指定位置挿入・ショートカット動的読込）、OCR にカスタムプロンプトを導入する。

**Target features:**
- PDF ページ操作の拡充: 白紙ページ挿入・テキスト透かし／ページ番号追加・ページ操作時の TOC 保持
- UI/UX 改善: サムネイルサイズ動的変更（スライダー）・サムネイルペインへの D&D 指定位置挿入・ショートカット動的読込（JSON ミニマム実装）
- OCR カスタムプロンプト: `LLMConfigDialog` でプロンプトを入力・保存し OCR バックエンドへ受け渡し

**Key context:**
- 透かし・ページ番号は**テキストのみ**（画像ロゴは後回し）。
- ショートカットは**`pagefolio_settings.json` の `shortcuts` キー編集のみ**のミニマム実装（専用 GUI タブなし）。
- 他 OCR プロバイダ対応はスコープ外（既存の Provider 群を踏襲）。
- 整合作業時に ruff E501 2 件を修正（`app.py` / `file_drop.py`）。テスト 490 件グリーン。
- 要件・ロードマップ詳細: `.planning/milestones/v1.5.0-REQUIREMENTS.md` / `.planning/milestones/v1.5.0-ROADMAP.md`

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
| テスト | pytest（現在小規模） |
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

### Active

- 次マイルストーン（v1.6.0 以降）の要件は未定義。`/gsd-new-milestone` で確定する（候補は下記 Next Milestone Goals）

### Out of Scope

- 暗号化 PDF 対応 — 別機能追加であり本プロジェクトの最適化スコープ外
- 印刷機能 — 同上
- OCR エンジンの拡張 — 同上
- プラグイン API バージョン管理 — 今後の別タスク
- UI/UX デザインの変更 — 本プロジェクトは内部品質に集中

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

## Current State

**Shipped: v1.5.0 基本機能・UI/UX改善・OCRカスタムプロンプト (2026-06-16)** — 4 フェーズ。`APP_VERSION = v1.5.0`（テスト 490 件グリーン・ruff クリーン）。

- **ページ操作の拡充:** 白紙ページ挿入・テキスト透かし／ページ番号追加（`insert_text`・テキストのみ）・削除/結合/分割時の TOC 保持調整。
- **UI/UX:** サムネイルサイズ動的変更（`thumb_zoom_scale` スライダー）・サムネイルペインへの D&D 指定位置挿入・ショートカット動的読込（`shortcuts` キー・JSON ミニマム）。
- **OCR:** `LLMConfigDialog` のカスタムプロンプト入力欄・`ocr_custom_prompt` 保存・OCR バックエンドへの受け渡し。
- 実装は `feature/v1.5.0-improvements` ブランチ（別 WF 実装・2026-06-16 に文書整合・ruff E501 2 件修正）。
- マイルストーン詳細: `.planning/milestones/v1.5.0-ROADMAP.md`・`.planning/MILESTONES.md`

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

### Next Milestone Goals (候補・未確定)

次マイルストーン（v1.6.0 以降）の要件は `/gsd-new-milestone` で確定する。現時点の候補:
- v1.5.0 新機能（ページ操作・UI/UX）に対する自動テストの拡充（現状 OCR 系のみ追加・新機能の回帰テスト未整備）
- 透かしの画像（ロゴ）対応・ショートカット設定の GUI 化（v1.5.0 でミニマム実装に留めた拡張）
- v1.4.0 リリースレビューの軽微改善バックログ（L-1〜L-6）の解消
- Phase 04 検証ギャップ（人手テスト）の正式クローズ
- サムネイル仮想化によるパフォーマンス改善（大量ページ対応）
- 印刷機能 / 暗号化 PDF 対応（機能追加。最適化スコープからの拡張）

## Evolution

このドキュメントはフェーズ移行・マイルストーン完了時に更新される。

**フェーズ移行後:**
1. 完了した要件 → Validated へ移動（フェーズ番号を付記）
2. 無効になった要件 → Out of Scope へ移動（理由を付記）
3. 新たに発見された要件 → Active へ追加
4. 決定事項 → Key Decisions を更新

---
*Last updated: 2026-06-16 — Completed milestone v1.5.0 (基本機能・UI/UX改善・OCRカスタムプロンプト).*
