# Phase 2: OCR 磨き込み（レビュー残の現行照合と二重実装解消） - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

v1.4.0 期レビュー残（L-1〜L-4・L-6）を現行コード照合の上で解消し、OCR のプロバイダ/プラグイン基盤と実行パイプラインを堅牢・単一実装にする（V171-OCR-01〜04）。L-1（producer-consumer 一本化）は高リスクのため**フェーズ内の独立プランへ隔離**する（ROADMAP リスク注記）。

新プロバイダ追加・OCR 結果のページ埋め込み・プラグイン API バージョン管理・UI/文言の広域監査（Phase 4 の領分）はスコープ外。

</domain>

<decisions>
## Implementation Decisions

### L-1: producer-consumer 一本化（V171-OCR-04）
- **D-01:** `ocr_dialog.py` の実戦済み挙動（非ブロッキング put・世代ガード・waiting 進捗・skip status・render 失敗時 on_done）を**仕様**とし、純ロジック層を書き直して dialog がそれを消費する形で一本化する。`ocr.py:306 run_with_bounded_buffer`（本番未使用・テストのみ消費）は現仕様に合わせて置き換える。
- **D-02:** 純ロジック層は**新モジュール `pagefolio/ocr_pipeline.py`**（Tk/fitz 非依存）として切り出す。`pagination.py` / `md_render.py` / `undo_store.py` と同格のプロジェクト既存パターン。テストは `tests/test_ocr_pipeline.py` へ既存 bounded buffer テストを移設・拡充。CLAUDE.md のファイル構成表へ 1 行追記。
- **D-03:** L-6 のうちパイプライン系小物（レンダー失敗ページでプログレスバーが 100% に達しない問題・producer が fatal 後も全ページ render 継続・sentinel `buf.put(None)` の暗黙容量不変条件の明文化）は **L-1 独立プランに吸収**して同時解消する。L-6 一括プランはパイプライン外の小物に絞る。
- **D-04:** 一本化の対象は**複数ページ画像 OCR の実行パイプラインのみ**。サマリ生成（`_summary_worker`・単発 text-only 呼び出し）は現行のまま触らない。
- **制約:** V14-D-05/06（`fitz.get_pixmap()` はメインスレッドのみ・bounded buffer によるメモリ上限保証）を一本化後も維持すること。

### L-4: Tesseract 言語フォールバック（V171-OCR-02）
- **D-05:** 言語パック検出（`_TESSERACT_LANGS` 相当）は import 時固定をやめ、**プロバイダ生成時に再検出**する（`tesseract --list-langs` を build_provider の都度実行・数十 ms で頻度的に無視可能）。言語パック追加が再起動なしで反映される。
- **D-06:** `ocr_image` は `self.lang`（`tesseract_lang` 設定・配線は `ocr.py:714` で既存）を尊重する。指定言語が利用不可の場合は**段階的縮退**：まず指定言語のうち利用可能な部分集合だけ残し（例: `deu+jpn+eng` → `jpn+eng`）、全滅なら現行の自動決定（jpn 有→`jpn+eng` / なし→`eng`）へ落とす。必ず何かしらで実行でき、エラー中止はしない。
- **D-07:** フォールバック発生時は **OCRDialog 内の非モーダル注記**（進捗ラベル/結果ヘッダ部・WARNING 色・実行は止めない）で「指定言語 xxx は利用不可のため yyy で実行」を 1 回表示する。OCR 結果テキスト自体には混入させない（コピー/保存 raw 維持の V16-D-02 方針と整合）。LANG キーは ja/en 両辞書へ同一キーで追加（既存 `tesseract_lang_fallback` キーの活用・拡張は実装時判断）。

### L-2/L-3: プラグイン OCR registry 堅牢化（V171-OCR-03）
- **D-08:** 重複名登録ポリシー：**組み込み名**（claude / gemini / lmstudio / tesseract / ollama / runpod / off）との衝突は `logger.warning` して**拒否**（現行の「組み込み勝ち」を維持しつつ可視化）。**プラグイン同士**の重複は `logger.warning` 付きで**後勝ち上書き**（プラグインのリロードで自然に更新される）。
- **D-09:** プラグイン unload 時は registry からの**登録解除のみ**行う。settings の `ocr_provider` は触らない（副作用なし）。unload 後にそのプロバイダで OCR 実行した場合は既存の未知名エラー経路で明示エラーになる。unload 対象の特定のため name→plugin の対応を registry 側で追跡する。
- **D-10:** 公開アクセサは `PluginManager.get_ocr_provider(name) -> cls | None` と `list_ocr_providers() -> list[str]` の 2 メソッド。現存 2 箇所の私有アクセス（`ocr.py:720` / `dialogs/llm_config.py:127`）を置換する。`_provider_registry` は実装詳細として非公開のまま。プラグイン作者向け docstring を整備。

### L-6: 小物一括解消の範囲確定（V171-OCR-01）
- **D-11:** Phase 2 の対象は `260610-aaa-REVIEW.md` の **L-6 に明記された項目のみ**。照合中に見つかったリスト外の同種軽微事項は Phase 4（V171-TEST-03 既知軽微バグ棚卸し）へ送る（deferred として記録）。
- **D-12:** 現行コード照合の結果（活き残り/解消済み判定）は Phase 2 の **RESEARCH.md に活き残り表**（項目 × 判定 × 根拠ファイル:行番号）として記録する。各項目の解消時には元の `260610-aaa-REVIEW.md` 該当項目へ **✅ + コミットハッシュを追記**（同文書の既存慣行「修正完了時は本文書の該当項目に完了マーク追記」に従う）。
- **D-13:** URL スキーム検証（http/https のみ許可）は LM Studio に限定せず、**ユーザー入力 URL/エンドポイントを持つ全プロバイダ（LM Studio / Ollama / RunPod）へ共通ヘルパーで統一適用**する。これは同一項目の適用先拡張であり D-11 の「新規項目追加」には当たらない。
- **照合の初期見立て（discuss 時スカウト・researcher が最終確定）:**
  - 解消済みの見込み: ClaudeProvider `stop_reason` 途切れ検出（v1.6.0 Phase 3 で `ocr_image_ex` 実装済み）・lang 未使用キーの一部（`ocr_provider_name_tesseract` は `ocr_dialog.py:708` で使用中）
  - 活き残りの見込み: URL スキーム検証なし・Gemini モデル名 URL 未エスケープ（`quote(` 不在）・`_fetch_models`/`_test_connection` 重複（`llm_config.py:1120` / `:1142`）
  - 要照合: Gemini エラー body 切り詰め・"off" 切替時の `_update_ocr_buttons_state()` 未呼出・ClaudeProvider `list_models` ページネーション

### Claude's Discretion
- `ocr_pipeline.py` の API 形状（コールバック境界・関数 vs クラス・引数設計）と、dialog 側の `after()` 描画配線の詳細。
- Tesseract 言語再検出のキャッシュ戦略（生成の都度 subprocess か、短期キャッシュか）と `list_models` との整合。
- `_fetch_models` / `_test_connection` 重複解消の共通化形（ヘルパー抽出 or パラメータ化）。
- フォールバック注記の文言詳細と既存 `tesseract_lang_fallback` キーの再利用/新設判断。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### レビュー残の原典（L-1〜L-6 の定義）
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` §低優先度（L） — L-1〜L-6 の該当箇所・行番号・対応案の原典。**照合の起点**であり、解消時に ✅ を追記する対象（D-12）

### 要件・ロードマップ
- `.planning/REQUIREMENTS.md` — V171-OCR-01〜04 の要件定義と Key Context（L 系の鮮度注記：v1.6.0〜v1.7.0 で解消済み項目あり）
- `.planning/ROADMAP.md` §Phase 2 — 成功基準 4 項目とリスク注記（L-1 は独立プランへ隔離）

### 先行決定（維持すべき制約）
- `.planning/PROJECT.md` §Key Decisions — V14-D-01（urllib 直叩き・新規 pip 依存ゼロ）、V14-D-05/06（fitz メインスレッドのみ・bounded buffer メモリ上限保証）、V16-D-02（コピー/保存 raw 維持）
- `.planning/phases/01-api-llm/01-CONTEXT.md` — Phase 1 のキー解決決定（入力値→環境変数・`_resolve_api_key`）。Phase 2 は本決定の上に載る（キー解決には触らない）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pagefolio/ocr.py:306 run_with_bounded_buffer` — 一本化の出発点（本番未使用・`tests/test_ocr.py:1234` 以降の bounded buffer テストのみ消費）。D-01/D-02 で `ocr_pipeline.py` へ置換・移設。
- `pagefolio/ocr_dialog.py:1352 付近` — 実運用の producer-consumer 実装（M-1 非ブロッキング put・M-2 世代ガード適用済み）。**この挙動が一本化の仕様**。
- `pagefolio/pagination.py` / `pagefolio/md_render.py` / `pagefolio/undo_store.py` — 「Tk/fitz 非依存の純ロジック層」パターンの先行例（D-02 の同型）。
- `pagefolio/ocr_providers.py:994-1060 TesseractProvider` — `self.lang` は保持済みだが `ocr_image` が無視（:1039 が自動決定）。`_detect_tesseract()` が再検出の部品に使える。
- `pagefolio/lang.py` `tesseract_lang_fallback`（:449/:1025 ja/en 両対応済み）— D-07 の注記文言に再利用候補。
- `pagefolio/plugins.py:200 register_ocr_provider` / `:88 _provider_registry` — D-08〜D-10 の改修対象。

### Established Patterns
- 純ロジック層は Tk/fitz 非依存で pytest 直接テスト可能にする（pagination.py 方式）。
- LANG 新規キーは ja/en 両辞書へ同一キーで追加（`test_lang_parity.py` が監視）。
- 裸の `except:` 禁止・`logger` 経由の記録（CLAUDE.md 規約）。
- OCR 実行の並列・リトライ・キャンセルは `run_parallel` / `clamp_retry_after` / `interruptible_sleep`（`ocr.py`）— 一本化で挙動を変えないこと（成功基準 4「既存 OCR テスト群がグリーン」）。

### Integration Points
- `pagefolio/ocr.py:714` — `settings.get("tesseract_lang", "jpn+eng")` を TesseractProvider へ渡す配線は既存。プロバイダ側の尊重（D-06）だけが欠けている。
- `pagefolio/ocr.py:720-721` / `pagefolio/dialogs/llm_config.py:127` — `_provider_registry` 私有アクセスの置換箇所（D-10）。
- `pagefolio/dialogs/llm_config.py:1120 _fetch_models` / `:1142 _test_connection` — L-6 重複解消の対象。
- OCRDialog の進捗ラベル（`progress_var` / `_progress_label`）— D-07 のフォールバック注記の表示先候補。

</code_context>

<specifics>
## Specific Ideas

- L-1 一本化は「dialog の挙動をリファレンスにヘルパーを書き直す」方向であり、「ヘルパーの理想仕様に dialog を合わせる」方向ではない（回帰リスクを実戦済みコード側に寄せる）。
- 照合の証跡は行番号付きで残し、「解消済みと判断した理由」を後から検証できるようにする（D-12 の狙い）。

</specifics>

<deferred>
## Deferred Ideas

- 照合中に見つかる L-6 リスト外の軽微事項 → Phase 4（V171-TEST-03 既知軽微バグ棚卸し）へ送る（D-11 の運用ルール。具体項目は RESEARCH.md/実装時に記録）
- サマリ経路（`_summary_worker`）の共通基盤化 → 今回は見送り（D-04）。将来 OCR 基盤を再訪する際の候補

</deferred>

---

*Phase: 2-OCR 磨き込み（レビュー残の現行照合と二重実装解消）*
*Context gathered: 2026-07-05*
