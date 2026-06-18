# Phase 7: Tesseract + PluginManager 拡張 + QA - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

オフライン環境向けの TesseractProvider（サブプロセス直呼び・任意）をプロバイダ一覧に追加し、サードパーティプラグインが独自 OCR バックエンドを `register_ocr_provider` フックで登録できるようにする。また v1.4.0 の締め括りとして全プロバイダの多言語文言・README・開発履歴を整備するフェーズ。

**このフェーズで作るもの（要件）:**
- **OCR-EXT-01**: `TesseractProvider`（subprocess 直呼び・`jpn+eng` 固定 / `jpn` 未インストール時は `eng` フォールバック・精度劣後注記常設）
- **OCR-EXT-02**: `PluginManager.register_ocr_provider(name, cls)` フック。`build_provider` が登録リストを参照し、LLMConfigDialog 展開時に Combobox へ自動追加。
- **OCR-QA-02**: 全プロバイダの未整備文言（Tesseract 専用 + ocr_progress_skip 等の未使用エントリ整理を含む）を `lang.py` で日英対応。README の OCR セクション更新・開発履歴 v1.4.0 追記。

**このフェーズで作らないもの（スコープ外）:**
- OS キーストア連携（Windows Credential Manager）によるキー永続化 → 次マイルストーン
- OCR 結果のページ埋め込み（検索可能 PDF 化）→ 次マイルストーン
- Tesseract の言語パック選択 UI → 任意拡張として将来フェーズ

**絶対条件:**
- **pip 依存ゼロ**: pytesseract パッケージを採用しない。`subprocess.run(["tesseract", ...])` で直呼び（V14-D-01 踏襲）。
- **後方互換**: LM Studio / Claude / Gemini の既存動作を壊さない。
- **Tesseract 未インストール環境**: 選択肢を disabled にし、エラーなく他プロバイダへ誘導。

</domain>

<decisions>
## Implementation Decisions

### Tesseract の検出と UI 制御（OCR-EXT-01）
- **D-01:** Tesseract の存在チェックは**アプリ起動時**に `subprocess.run(["tesseract", "--version"], ...)` で実施。成否を module-level フラグ（例: `_TESSERACT_AVAILABLE`）に保持し、起動後は再検出しない。
- **D-02:** Tesseract 未インストール時は LLMConfigDialog の Combobox で `"tesseract"` エントリを `state="disabled"` でグレーアウトする。クリック時のツールチップや警告メッセージ（インストール案内）を表示する形は Claude 裁量。
- **D-03:** 精度劣後注記は `tesseract` 選択時の**展開欄内に常設ラベル**として表示（Phase 6 の `ocr_scale` ヒントと同じパターン）。コスト確認ダイアログ（Tesseract はオフライン無課金なので不要）は表示しない。
- **D-04:** OCR 言語オプションは **`jpn+eng` 固定**。`jpn` ラングパック未インストール時は `eng` のみにフォールバック（`tesseract --list-langs` で検出）。UI に言語入力欄は追加しない。

### PluginManager 登録フック（OCR-EXT-02）
- **D-05:** `PluginManager` に `register_ocr_provider(name: str, cls: type[OCRProvider])` メソッドを追加。登録データは `_provider_registry: dict[str, type[OCRProvider]]` で保持。
- **D-06:** プラグインは `on_load(app)` 内で `app.plugin_manager.register_ocr_provider("myprovider", MyProvider)` を呼ぶ（既存 `fire_event` パターンとの一貫性）。
- **D-07:** `build_provider(settings, api_key=None)` は既存の `if name in (...)` 分岐の後に `PluginManager._provider_registry` を参照するフォールバックを追加する。`PluginManager` の参照渡し方法（グローバル変数 or 引数追加）は Claude 裁量。
- **D-08:** LLMConfigDialog の Combobox values は**ダイアログ展開時**に `["off", "lmstudio", "claude", "gemini", "tesseract"] + list(plugin_manager._provider_registry.keys())` を取得して設定する。登録タイミングより後に Combobox を開けば必ず反映される。

### ドキュメント整備（OCR-QA-02）
- **D-09:** `lang.py` の整備範囲は**全プロバイダ**を対象とし、Tesseract 専用文言（精度劣後注記・未インストールエラー・`eng` フォールバック通知）を新規追加し、`ocr_progress_skip` 等の未使用エントリを削除または整理する。
- **D-10:** README.md の OCR セクション（既存の OCR 説明部分）を v1.4.0 版に更新。対象: プロバイダ一覧（LM Studio / Claude / Gemini / Tesseract）・環境変数設定方法・Tesseract インストール案内の追加。新規セクション追加ではなく既存記述の発展更新。
- **D-11:** 開発履歴.md に v1.4.0 エントリを追記。OCR プロバイダ化の概要・Phase 4〜7 の変更点サマリーを記載。

### Claude's Discretion
- `_TESSERACT_AVAILABLE` フラグの保持場所（`ocr_providers.py` モジュールレベル or `settings.py` or `app.py` 起動時）
- Tesseract 未インストール時の Combobox disabled 実装の具体（ttk Combobox は `state="disabled"` で全体ロックしかできないため、個別エントリ disabled の代替手段も含め Claude 裁量）
- `PluginManager` への `build_provider` の参照渡し方法（シングルトンパターン・引数追加・`app` 経由）
- `ocr_progress_skip` 等の整理方針の詳細（削除 or コメントアウト or 維持）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・ロードマップ・前フェーズ確定事項
- `.planning/ROADMAP.md` §Phase 7 — Goal・Success Criteria（1〜4）・Requirements（OCR-EXT-01/02・OCR-QA-02）
- `.planning/REQUIREMENTS.md` §OCR-EXT §OCR-QA — 3 要件の詳細定義・Out of Scope（SDK 不採用・settings.json 平文保存禁止）
- `.planning/phases/04-provider-abstraction/04-CONTEXT.md` — V14-D-01（urllib 直叩き・pip 依存ゼロ）・`OCRProvider` 抽象基底の契約
- `.planning/phases/05-claude-provider-ui/05-CONTEXT.md` — セッションキー・`build_provider` のインターフェース確定事項
- `.planning/phases/06-gemini-provider/06-CONTEXT.md` — D-11/D-12（`ocr_scale` ヒント常設パターン・`lang.py` 最小追加）を Tesseract 精度注記で踏襲

### 既存実装ファイル（downstream agent が必ず参照する）
- `pagefolio/ocr_providers.py` — `OCRProvider` 抽象基底クラス・`LMStudioProvider`・`ClaudeProvider`・`GeminiProvider` の実装パターン（TesseractProvider の設計参照）
- `pagefolio/ocr.py` — `build_provider` 関数（L456〜）・`_start_ocr` のプロバイダ取得フロー
- `pagefolio/plugins.py` — `PluginManager` クラス（L80〜）・`on_load` ライフサイクル・`fire_event` パターン
- `pagefolio/dialogs/llm_config.py` — Combobox（L97〜108・L35コメント）・`_on_provider_change`・`_refresh_*_models` の provider 分岐パターン
- `pagefolio/lang.py` — 既存 OCR 文言エントリ・`ocr_progress_skip`（未使用エントリの整理対象）

### 設計の正典
- `docs/OCRプロバイダ化_見積もり仕様.md` — v1.4.0 全体スコープ・Tesseract の位置づけ（オプション・精度劣後注記付き）
- `.planning/research/ARCHITECTURE.md` — `OCRMixin`/`ocr_providers.py` 統合設計・`PluginManager` 連携の設計意図

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LMStudioProvider` / `ClaudeProvider` / `GeminiProvider` のテンプレート（`__init__` 設定注入・`_build_payload`・`ocr_image`・`list_models`）: TesseractProvider もこのパターンで実装（ただし `list_models` は空リスト or `["tesseract"]` を返す）
- `_on_provider_change` と provider 別フレーム pack/pack_forget パターン（llm_config.py）: tesseract 展開フレームも同じ構造で追加
- `ocr_scale` 精度ヒントラベル（llm_config.py）: Tesseract 精度劣後注記の実装参考
- `PluginManager.fire_event` + プラグインの `on_load` パターン（plugins.py）: `register_ocr_provider` を同じライフサイクルに乗せる

### Established Patterns
- **pip 依存ゼロ** (V14-D-01): `subprocess.run(["tesseract", ...])` で実装。pytesseract 不採用。
- **Provider クラス属性**: `default_concurrency = 1`・`max_concurrency = 1`（Tesseract はシングルスレッド前提）
- **スレッド境界** (Phase 4 D-03): fitz レンダリングはメインスレッド・API 呼び出しはワーカー。Tesseract もワーカースレッドで subprocess 呼び出し（fitz アクセスなし）
- **`lang.py` 文言追加パターン**: ja/en 両辞書に同一キーで追加（Phase 5/6 踏襲）
- **Settings 辞書の流れ**: `settings.get("ocr_provider")` → `build_provider` → Provider インスタンス

### Integration Points
- `build_provider` の `elif name == "tesseract":` 分岐追加（ocr.py L456〜）と、後続のプラグイン登録フォールバック
- `LLMConfigDialog.__init__` の Combobox values 動的生成（`plugin_manager._provider_registry` 参照）
- `_TESSERACT_AVAILABLE` フラグによる Combobox disabled 制御
- `PluginManager` への `_provider_registry` 属性・`register_ocr_provider` メソッド追加
- `tests/test_ocr_providers.py` に `TestTesseractProvider` 追加

</code_context>

<specifics>
## Specific Ideas

- Tesseract のフォールバック動作: `jpn` パック未インストールなら `eng` のみで実行し、ユーザーへのフォールバック通知は lang.py の新規キー（例: `tesseract_lang_fallback`）で表示する。
- README の OCR セクション更新イメージ: 既存のスクリーンショットや操作手順を活かしつつ、プロバイダ別セットアップ手順（環境変数・Tesseract インストールコマンド）を追加する形。
- 開発履歴.md は既存フォーマット（バージョン見出し + 変更点箇条書き）を踏襲して v1.4.0 エントリを追記。

</specifics>

<deferred>
## Deferred Ideas

- Tesseract の言語パック選択 UI（ユーザーが `-l` オプションをカスタマイズ）→ 将来フェーズ
- TesseractProvider の精度向上設定（`--psm`・`--oem` 等の公開オプション）→ 将来フェーズ
- OS キーストア連携（Windows Credential Manager）によるキー永続化 → 次マイルストーン
- OCR 結果のページ埋め込み（検索可能 PDF 化）→ 次マイルストーン

</deferred>

---

*Phase: 7-tesseract-pluginmanager-qa*
*Context gathered: 2026-06-09*
