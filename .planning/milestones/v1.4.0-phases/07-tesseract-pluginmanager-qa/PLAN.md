# Phase 7: Tesseract + PluginManager 拡張 + QA — PLAN

**作成:** 2026-06-09
**フェーズ:** 07-tesseract-pluginmanager-qa
**要件:** OCR-EXT-01, OCR-EXT-02, OCR-QA-02
**依存:** Phase 6 完了済み

---

## Goal

オフライン環境でも Tesseract が OCR プロバイダの選択肢として使えるようにし、
サードパーティプラグインが `register_ocr_provider` フックで独自バックエンドを登録できる仕組みを追加する。
v1.4.0 の締め括りとして全プロバイダの多言語文言・README・開発履歴を整備する。

---

## Success Criteria（ROADMAP.md §Phase 7 から転記）

1. Tesseract がインストールされた環境でプロバイダを「tesseract」に選択し OCR を実行できる（精度劣後注記が UI に表示される）
2. Tesseract が未インストールの環境では「tesseract」選択肢が無効化され、エラーなく他プロバイダへ誘導される
3. サードパーティプラグインが `register_ocr_provider` フックで独自バックエンドを登録し、SettingsDialog のプロバイダ一覧に表示できる
4. プロバイダ名・APIキー未設定・精度注記・コスト警告の文言が日英両対応し、README と開発履歴が v1.4.0 の変更を反映している

---

## Threat Model & Risk Mitigation

| # | リスク | カテゴリ | 対策 |
|---|--------|----------|------|
| T1 | `subprocess.run(["tesseract", ...])` に外部入力が混入しコマンドインジェクション | Tampering | `lang` は `_TESSERACT_LANGS` に存在するものか `"eng"` フォールバックのみ使用（D-04）。`shell=False` 固定（引数リスト形式）。 |
| T2 | 大容量 PNG を stdin に渡して長時間ブロック（DoS） | DoS | `subprocess.run(timeout=60)` を設定。`TimeoutError` に変換してワーカースレッドが詰まらないよう処理する。 |
| T3 | プラグインが悪意ある `OCRProvider` サブクラスを登録し任意コードを実行 | Elevation of Privilege | `register_ocr_provider` で `issubclass(cls, OCRProvider)` バリデーションを実施。プラグイン自体の信頼境界はユーザーがプラグインファイルを配置する操作に委ねる（既存 PluginManager の設計方針踏襲）。 |
| T4 | `_TESSERACT_AVAILABLE` フラグが古くなり未インストール状態を見逃す | Information Disclosure | フラグはアプリ起動時に一度だけ評価する（D-01）。起動後に Tesseract をアンインストールしても次回起動時に正しく反映されることをドキュメントに明記する。 |
| T5 | stdin パイプ方式が特定バージョンの Tesseract で未サポート（rc!=0 で silent fail） | Reliability | `returncode != 0` 時に `RuntimeError` を raise し OCR ダイアログのエラー表示に乗せる。ユーザーに原因が伝わる文言を `lang.py` に追加。 |

---

## Wave 1: コア実装（独立した基盤）

Wave 1 内の 3 タスクはファイル重複なし。並列実行可能。

---

### Task 1.1: TesseractProvider 実装（OCR-EXT-01）

**File:** `pagefolio/ocr_providers.py`

**What:**
- モジュール先頭に `import subprocess` を追加
- モジュールレベル関数 `_detect_tesseract()` を定義し、`_TESSERACT_AVAILABLE: bool` と `_TESSERACT_LANGS: frozenset[str]` を初期化
- `TesseractProvider(OCRProvider)` クラスを実装

**How:**

1. `_detect_tesseract()` の実装（D-01）
   - `subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)` で存在チェック
   - 成功した場合は `subprocess.run(["tesseract", "--list-langs"], capture_output=True, timeout=5)` で言語一覧を取得
   - `raw = (r2.stdout or r2.stderr).decode(errors="replace")` で OS 差異を吸収（Windows=stdout / Linux=stderr）
   - `"List of available"` で始まる行を除外して `frozenset` を構築して返す
   - `FileNotFoundError / OSError / subprocess.TimeoutExpired` をすべて捕捉して `(False, frozenset())` を返す
   - モジュール末尾に `_TESSERACT_AVAILABLE, _TESSERACT_LANGS = _detect_tesseract()` を配置

2. `TesseractProvider` クラスの実装（GeminiProvider をアナログとして踏襲）
   - クラス属性: `default_concurrency = 1`, `max_concurrency = 2`（CPU バウンド・シングルスレッド前提）
   - `RECOMMENDED_LANGS: list[str] = ["jpn+eng", "eng", "jpn"]`
   - `__init__(self, lang="jpn+eng", psm=3, timeout=60)` — API キー不要
   - `ocr_image(self, b64_png, prompt, **kwargs) -> str`:
     - `lang = "jpn+eng" if "jpn" in _TESSERACT_LANGS else "eng"` で D-04 フォールバックを実装（`self.lang` ではなくモジュールフラグ参照）
     - `png_bytes = base64.b64decode(b64_png)` で PNG バイト列に変換（b64 文字列をそのまま渡さないこと）
     - stdin パイプ方式: `subprocess.run(["tesseract", "stdin", "stdout", "-l", lang, "--psm", str(self.psm)], input=png_bytes, capture_output=True, timeout=self.timeout)`
     - `FileNotFoundError` → `RuntimeError("tesseract コマンドが見つかりません")` に変換
     - `subprocess.TimeoutExpired` → `TimeoutError(f"Tesseract がタイムアウトしました ({self.timeout}s)")` に変換
     - `returncode != 0` → `RuntimeError(f"Tesseract エラー (rc={result.returncode}): {err}")` に変換
     - 成功時: `result.stdout.decode("utf-8", errors="replace").strip()` を返す
   - `list_models(self) -> list[str]`: `["tesseract"]` を返す（固定）

3. ファイル先頭の既存 import に `import base64` が存在するか確認し、なければ追加

**Acceptance:**
- `python -c "from pagefolio.ocr_providers import TesseractProvider, _TESSERACT_AVAILABLE, _TESSERACT_LANGS; print('OK')"` が `OK` を出力（import エラーなし）
- `python -c "from pagefolio.ocr_providers import TesseractProvider; assert issubclass(TesseractProvider, __import__('pagefolio.ocr_providers', fromlist=['OCRProvider']).OCRProvider)"` がエラーなし
- `ruff check pagefolio/ocr_providers.py && ruff format pagefolio/ocr_providers.py` がエラーなし
- ※ `TestTesseractProvider` テストは Wave 4 (Task 4.1) で追加するため、Wave 1 時点では import チェックで代替確認する

---

### Task 1.2: PluginManager に register_ocr_provider を追加（OCR-EXT-02）

**File:** `pagefolio/plugins.py`

**What:**
- `PluginManager.__init__` に `self._provider_registry: dict = {}` を追加
- `register_ocr_provider(self, name: str, cls) -> None` メソッドを追加

**How:**

1. `PluginManager.__init__` に追記（既存の `self._disabled = set()` の直後）:
   ```
   self._provider_registry = {}  # OCR プロバイダ登録辞書 {name: OCRProvider サブクラス}
   ```

2. `register_ocr_provider` メソッドの実装:
   - `from pagefolio.ocr_providers import OCRProvider` を関数内 import（循環 import 回避のため）
   - `isinstance(cls, type) and issubclass(cls, OCRProvider)` でバリデーション、失敗時は `TypeError` を raise
   - `self._provider_registry[name] = cls` で登録
   - `logger.debug("OCR プロバイダ登録: %s -> %s", name, cls.__name__)` でログ出力
   - docstring: プラグインの `on_load(app)` 内で `app.plugin_manager.register_ocr_provider("myprovider", MyProvider)` を呼ぶことを明記

3. `fire_event` の `try/except Exception as e` エラー隔離パターン（l.192–196）を参考に、
   プラグインの `register_ocr_provider` 呼び出しがクラッシュを引き起こさない構造であることを確認

**Acceptance:**
- `pytest tests/test_plugins.py -x` が全テスト通過（既存テストのみ。`TestPluginManagerProviderRegistry` は Wave 4 で追加）
- `python -c "from pagefolio.plugins import PluginManager; pm = PluginManager(); assert pm._provider_registry == {}; print('OK')"` が `OK` を出力
- `python -c "from pagefolio.plugins import PluginManager; pm = PluginManager(); pm.register_ocr_provider('bad', object)"` が `TypeError` を raise すること（手動確認）
- `ruff check pagefolio/plugins.py` がエラーなし
- ※ `TestPluginManagerProviderRegistry` テストは Wave 4 (Task 4.1) で追加するため、Wave 1 時点では python -c コマンドで代替確認する

---

### Task 1.3: build_provider に tesseract 分岐 + plugin_manager フォールバックを追加（OCR-EXT-01/02）

**File:** `pagefolio/ocr.py`（および呼び出し箇所: `pagefolio/dialogs/ocr_dialog.py`・`pagefolio/ocr.py` の `_start_ocr`）

**What:**
- `build_provider` のシグネチャに `plugin_manager=None` を追加（D-07）
- `elif name == "tesseract":` 分岐を追加
- `plugin_manager._provider_registry` へのフォールバックを追加
- 呼び出し箇所に `plugin_manager=self.app.plugin_manager`（または `app.plugin_manager`）を渡すよう更新

**How:**

1. `build_provider(settings, api_key=None)` を `build_provider(settings, api_key=None, plugin_manager=None)` に変更

2. 既存の `elif name == "gemini":` ブロックの末尾（`raise ValueError` の直前）に追加:
   ```
   elif name == "tesseract":
       from pagefolio.ocr_providers import TesseractProvider
       return TesseractProvider(
           lang=settings.get("tesseract_lang", "jpn+eng"),
           psm=int(settings.get("tesseract_psm", 3)),
           timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
       )
   # プラグイン登録プロバイダへのフォールバック
   if plugin_manager is not None and name in plugin_manager._provider_registry:
       cls = plugin_manager._provider_registry[name]
       return cls()
   raise ValueError(f"未対応のプロバイダ: {name}")
   ```

3. `build_provider` の呼び出し箇所を検索し、`plugin_manager=` キーワード引数を追加:
   - `pagefolio/dialogs/ocr_dialog.py` の `build_provider(...)` 呼び出し
   - `pagefolio/ocr.py` 内の `_start_ocr` 等での呼び出し（`app.plugin_manager` を渡す）
   - デフォルト `None` のため既存テストコードへの影響なし

4. `build_provider` の docstring に `plugin_manager` 引数の説明を追加

**Acceptance:**
- `pytest tests/ -x -q` が全テスト通過
- `build_provider({"ocr_provider": "tesseract"})` が `TesseractProvider` インスタンスを返す
- `build_provider({"ocr_provider": "unknown"})` が `ValueError` を raise する
- `ruff check pagefolio/ocr.py` がエラーなし

---

## Wave 2: UI 統合（Wave 1 完了後）

---

### Task 2.1: LLMConfigDialog に tesseract 展開フレームを追加（OCR-EXT-01/02）

**File:** `pagefolio/dialogs/llm_config.py`

**What:**
- `LLMConfigDialog.__init__` に `plugin_manager=None` 引数を追加（D-08）
- Combobox values を動的生成に変更（D-02/D-08）
- tesseract 選択時の展開フレームを追加（D-03）
- Tesseract 未インストール時の選択リセット処理を実装（D-02 代替）
- `_apply` で `tesseract_lang` / `tesseract_psm` を収集して保存

**How:**

1. `__init__(self, parent, font_func, lang, settings, ..., plugin_manager=None)` にシグネチャ変更。
   `self._plugin_manager = plugin_manager` として保持。

2. Combobox values の動的構築（`_build()` 内、Combobox 作成時）:
   - `from pagefolio.ocr_providers import _TESSERACT_AVAILABLE` を import
   - `base = ["off", "lmstudio", "claude", "gemini", "tesseract"]`
   - `extras = list(self._plugin_manager._provider_registry.keys()) if self._plugin_manager else []`
   - `self.provider_combo["values"] = base + extras`
   - Tesseract 未インストール時の説明ラベルを Combobox の下に追加:
     `tk.Label(..., text=self._L["tesseract_not_installed_hint"], fg=C["TEXT_SUB"], font=self._font(-2))`
     （`not _TESSERACT_AVAILABLE` のときのみ表示）

3. `_on_provider_change` に Tesseract 未インストール時のリセット処理を追加（D-02 代替）:
   ```
   if provider == "tesseract" and not _TESSERACT_AVAILABLE:
       self.provider_var.set(self._last_valid_provider)
       self._set_lm_status(self._L["tesseract_not_installed_hint"], kind="fail")
       return
   self._last_valid_provider = provider
   ```
   `self._last_valid_provider` は `__init__` で `settings.get("ocr_provider", "off")` として初期化。

4. tesseract 展開フレームの構築（GeminiProvider フレームをアナログとして l.219–251 を参考）:
   - `self.tesseract_section_frame = tk.Frame(self, bg=C["BG_DARK"])` を作成
   - 精度劣後注記の常設ラベル（D-03）: `self._L["tesseract_accuracy_warning"]` を `fg=C["WARNING"]` で表示（`ocr_scale` ヒントと同パターン）
   - 言語ラベル（読み取り専用表示）: `_TESSERACT_LANGS` が `"jpn"` を含む場合は `"jpn+eng"`、含まない場合は `"eng"` を表示し、`self._L["tesseract_lang_fallback"]` ラベルを条件表示
   - tesseract フレームは `_on_provider_change` の `elif provider == "tesseract":` で pack / pack_forget を制御

5. `_on_provider_change` の `elif` チェーンに tesseract 分岐を追加:
   ```
   elif provider == "tesseract":
       self.tesseract_section_frame.pack(fill="x", padx=24, pady=(4, 2))
       self.claude_section_frame.pack_forget()
       self.gemini_section_frame.pack_forget()
       self.url_section_frame.pack_forget()
       self.effort_frame.pack_forget()
       self.temperature_frame.pack_forget()
   ```
   また、既存 `else:` ブロック（lmstudio 以外）にも `self.tesseract_section_frame.pack_forget()` を追加。

6. `_apply` メソッドに tesseract 設定の収集を追加:
   - `settings["tesseract_lang"]` は `_TESSERACT_LANGS` 由来の固定値（UI は表示のみ・D-04）
   - 設定保存に `"tesseract_lang"` と `"tesseract_psm"` を含める

7. `LLMConfigDialog` の呼び出し箇所（`pagefolio/dialogs/__init__.py` または `pagefolio/app.py`）で `plugin_manager=self.plugin_manager` を渡すよう更新。

**Acceptance:**
- アプリ起動 → SettingsDialog → プロバイダ Combobox に `"tesseract"` が表示される
- `"tesseract"` 選択時に精度劣後注記ラベルが展開フレーム内に表示される
- Tesseract 未インストールの場合（`_TESSERACT_AVAILABLE = False` をモックして確認）、`"tesseract"` 選択後に前のプロバイダに戻りステータスに案内メッセージが表示される
- `ruff check pagefolio/dialogs/llm_config.py` がエラーなし

---

## Wave 3: 文言・ドキュメント整備（Wave 1 完了後・Wave 2 と並行可）

Wave 3 のタスク 3.1〜3.3 はファイル重複なし。並列実行可能。

---

### Task 3.1: lang.py の整備（OCR-QA-02）

**File:** `pagefolio/lang.py`

**What:**
- Tesseract 専用文言キーを日英両辞書に追加（D-09）
- `ocr_progress_skip` 等の未使用エントリを削除（D-09）
- `sec_ocr` / `ocr_dialog_title` をプロバイダ非依存の表記に変更

**How:**

1. 以下のキーを `"ja"` と `"en"` 両辞書に同一キー名で追加（既存 OCR 文言ブロックの末尾に追加）:

   | キー | 日本語 | 英語 |
   |------|--------|------|
   | `tesseract_accuracy_warning` | `"※ Tesseract の精度は LLM ベースのプロバイダより劣ります"` | `"Note: Tesseract accuracy is lower than LLM-based providers."` |
   | `tesseract_not_installed` | `"Tesseract がインストールされていません（tesseract コマンドが見つかりません）"` | `"Tesseract is not installed (command not found)."` |
   | `tesseract_not_installed_hint` | `"Tesseract がインストールされていません。他のプロバイダを使用してください"` | `"Tesseract is not installed. Please use another provider."` |
   | `tesseract_lang_fallback` | `"jpn 言語パックが見つかりません。eng のみで実行します"` | `"jpn language pack not found. Running with eng only."` |

2. 未使用エントリの削除（コードベース全体で参照されていないことを確認してから削除）:
   - `ocr_progress_skip`: `lang.py` に定義されているが `ocr_dialog.py` / `ocr.py` で参照なし → **削除**

3. LM Studio 固有文言の更新（プロバイダ非依存化）:
   - `sec_ocr`: `"🔍 OCR（LM Studio）"` → `"🔍 OCR"` に変更（日英両辞書）
   - `ocr_dialog_title`: `"OCR — LM Studio"` → `"OCR"` に変更（日英両辞書）

**Acceptance:**
- `python -c "from pagefolio.lang import LANG; assert 'tesseract_accuracy_warning' in LANG['ja']"` がエラーなし
- `python -c "from pagefolio.lang import LANG; assert 'ocr_progress_skip' not in LANG['ja']"` がエラーなし
- `python -c "from pagefolio.lang import LANG; assert LANG['ja']['sec_ocr'] == '🔍 OCR'"` がエラーなし
- `ruff check pagefolio/lang.py` がエラーなし

---

### Task 3.2: README.md の OCR セクション更新（OCR-QA-02）

**File:** `README.md`

**What:**
- 既存の OCR 説明セクションを v1.4.0 版に更新（D-10）
- プロバイダ一覧（LM Studio / Claude / Gemini / Tesseract）の追加
- 環境変数設定方法と Tesseract インストール案内の追加

**How:**

1. README.md の既存 OCR セクション（`# OCR` または `## OCR` など）を特定し、以下の内容で更新（新規セクション追加ではなく発展更新）:

   - **プロバイダ一覧表**: 各プロバイダ名・必要な環境変数・特徴（オフライン可否・精度・コスト概要）を表形式で記載
     - LM Studio: ローカル・無料・GPU 推奨
     - Claude: `ANTHROPIC_API_KEY` 環境変数・高精度・有料
     - Gemini: `GEMINI_API_KEY` または `GOOGLE_API_KEY`・高精度・有料
     - Tesseract: ローカル・無料・精度は LLM より劣る・要別途インストール

   - **Tesseract インストール案内**（Windows 向け）:
     - UB Mannheim ビルドのインストール URL: `https://github.com/UB-Mannheim/tesseract/wiki`
     - インストール後に PATH を通す手順
     - 日本語認識のために `jpn` 言語パックを追加する手順

   - **環境変数設定例**:
     ```
     set ANTHROPIC_API_KEY=your_key_here
     set GEMINI_API_KEY=your_key_here
     ```

2. 既存スクリーンショットや操作手順はそのまま活かし、プロバイダ別セットアップを追記する形で統合。

**Acceptance:**
- `README.md` に Tesseract インストール手順が含まれること（`UB-Mannheim` または `tesseract` の文字列で確認）
- プロバイダ一覧に LM Studio / Claude / Gemini / Tesseract が記載されていること
- Markdown が正しく構造化されていること（見出し・表・コードブロックの閉じ忘れなし）

---

### Task 3.3: 開発履歴.md に v1.4.0 エントリを追記（OCR-QA-02）

**File:** `開発履歴.md`

**What:**
- v1.4.0 エントリを先頭に追記（D-11）
- Phase 4〜7 の変更点サマリーを既存フォーマットで記載
- `pagefolio/constants.py` の `APP_VERSION` を `1.4.0` に更新

**How:**

1. `pagefolio/constants.py` を確認し、`APP_VERSION` を現行値から `"1.4.0"` に変更。

2. `開発履歴.md` の先頭に以下フォーマットで v1.4.0 エントリを追記（既存の最新バージョン見出しより前）:

   ```markdown
   ## v1.4.0 — OCR プロバイダ化 + クラウドAPI対応（2026-06-XX）

   ### 主な変更点

   - **OCRProvider 抽象化（Phase 4）**: OCRProvider 抽象基底クラスを導入。LM Studio を LMStudioProvider として実装し直し、プロバイダ差し替え可能な設計に変更。テキスト埋め込みページの API 呼び出しスキップ、ページ単位の逐次レンダリングによるメモリ最適化。
   - **Claude Provider + セキュリティ基盤（Phase 5）**: Anthropic Claude（messages API）による OCR を追加。APIキーはセッションメモリのみに保持し `settings.json` へ書き込まない設計を実装。コスト確認ダイアログ、指数バックオフリトライを追加。
   - **Gemini Provider（Phase 6）**: Google Gemini（generateContent・inline_data）による OCR を追加。`GEMINI_API_KEY` / `GOOGLE_API_KEY` 環境変数対応。`ocr_scale` デフォルト値を 1.5 に変更し UI にトレードオフヒントを追加。
   - **Tesseract Provider（Phase 7）**: subprocess 直呼びによるオフライン OCR プロバイダを追加。pytesseract 非依存。`jpn` 言語パック未インストール時は `eng` のみで動作。精度劣後注記を UI に常設表示。
   - **PluginManager 拡張（Phase 7）**: `register_ocr_provider` フックにより、サードパーティプラグインが独自 OCR バックエンドを登録可能に。
   - **多言語文言・ドキュメント整備（Phase 7）**: 全プロバイダの日英文言を `lang.py` で整備。README の OCR セクションを v1.4.0 向けに更新。
   ```

3. `README.md` のバージョンバッジを `1.4.0` に更新（バッジが存在する場合）。

**Acceptance:**
- `python -c "from pagefolio.constants import APP_VERSION; assert APP_VERSION == '1.4.0'"` がエラーなし
- `開発履歴.md` の先頭近くに `## v1.4.0` 見出しが存在すること
- `ruff check pagefolio/constants.py` がエラーなし

---

## Wave 4: テスト・最終確認（Wave 1〜3 完了後）

---

### Task 4.1: TestTesseractProvider テストクラスを追加（OCR-EXT-01/02）

**File:** `tests/test_ocr_providers.py`（既存ファイルに追記）、`tests/test_plugins.py`（既存ファイルに追記）

**What:**
- `TestTesseractProviderBasic`: クラス属性・インターフェース準拠の検証
- `TestTesseractProviderOcrImage`: `subprocess.run` を monkeypatch でモックし `ocr_image` の各ケースを検証
- `TestPluginManagerProviderRegistry`: `register_ocr_provider` の動作を検証（`tests/test_plugins.py` に追加）

**How（`tests/test_ocr_providers.py` に追加）:**

1. `TestTesseractProviderBasic` クラス（`TestGeminiProviderBasic` アナログ、l.719–746 参考）:
   - `test_is_ocr_provider_subclass`: `issubclass(TesseractProvider, OCRProvider)` が True
   - `test_instantiation`: `TesseractProvider()` がエラーなし
   - `test_default_concurrency`: `TesseractProvider.default_concurrency == 1`
   - `test_max_concurrency`: `TesseractProvider.max_concurrency == 2`
   - `test_list_models`: `TesseractProvider().list_models() == ["tesseract"]`

2. `TestTesseractProviderOcrImage` クラス（`TestGeminiProviderOcrImage` アナログ、l.825–923 参考）:
   - `test_ocr_image_success(monkeypatch)`:
     - `subprocess.run` を `returncode=0, stdout=b"OCR\n", stderr=b""` を返す fake に差し替え
     - `ocr_image("iVBORw0KGgo=", "describe")` が `"OCR"` を返すことを検証
   - `test_ocr_image_nonzero_returncode_raises_runtime_error(monkeypatch)`:
     - `returncode=1, stderr=b"Error"` を返す fake に差し替え
     - `RuntimeError` が raise されることを検証
   - `test_ocr_image_file_not_found_raises_runtime_error(monkeypatch)`:
     - `subprocess.run` が `FileNotFoundError` を raise する fake に差し替え
     - `RuntimeError` が raise されることを検証（`match="tesseract コマンドが見つかりません"`）
   - `test_ocr_image_timeout_raises_timeout_error(monkeypatch)`:
     - `subprocess.run` が `subprocess.TimeoutExpired` を raise する fake に差し替え
     - `TimeoutError` が raise されることを検証
   - `test_lang_fallback_to_eng_when_jpn_not_available(monkeypatch)`:
     - `ocr_providers._TESSERACT_LANGS` を `frozenset({"eng"})` に差し替え
     - `subprocess.run` をキャプチャして呼び出し引数を検証
     - `-l eng` が渡されることを確認（`-l jpn+eng` ではないこと）

**How（`tests/test_plugins.py` に追加）:**

3. `TestPluginManagerProviderRegistry` クラス:
   - `test_initial_registry_is_empty`: `PluginManager()._provider_registry == {}`
   - `test_register_valid_provider`:
     - `OCRProvider` のダミーサブクラスを作成して `register_ocr_provider("test", DummyProvider)` を呼ぶ
     - `pm._provider_registry["test"] is DummyProvider` を検証
   - `test_register_non_subclass_raises_type_error`:
     - `register_ocr_provider("bad", object)` が `TypeError` を raise することを検証
   - `test_build_provider_uses_registry(monkeypatch)`:
     - `build_provider({"ocr_provider": "test_plugin"}, plugin_manager=pm)` が `DummyProvider` インスタンスを返すことを検証

**Acceptance:**
- `pytest tests/test_ocr_providers.py -x -q` が全テスト通過（既存テスト含む）
- `pytest tests/test_plugins.py -x -q` が全テスト通過（既存テスト含む）
- `pytest -x -q` がフルスイート全テスト通過

---

### Task 4.2: 最終 ruff + pytest フルパス確認

**File:** なし（確認のみ）

**What:**
- `ruff check . && ruff format .` が全ファイルでエラーなし
- `pytest` がフルスイートで全テスト通過
- アプリが起動できること（構文エラーなし）

**How:**

1. `ruff check . && ruff format .` を実行。エラーがある場合は修正。
2. `pytest` を実行。失敗したテストがある場合は Wave 1〜3 の該当タスクに戻って修正。
3. `python -c "from pagefolio.ocr_providers import TesseractProvider, _TESSERACT_AVAILABLE; print('OK', _TESSERACT_AVAILABLE)"` でモジュール起動確認。

**Acceptance:**
- `ruff check .` のエラー出力が空
- `pytest` の最終行が `passed` のみ（`failed` / `error` ゼロ）
- import チェックコマンドが `OK True` または `OK False` を出力する（終了コードが 0）

---

## Test Plan

### Wave 1 完了後の確認コマンド

```bash
# TesseractProvider import チェック（TestTesseractProvider は Wave 4 で追加）
python -c "from pagefolio.ocr_providers import TesseractProvider, _TESSERACT_AVAILABLE, _TESSERACT_LANGS; print('OK', _TESSERACT_AVAILABLE)"

# PluginManager 基本チェック（TestPluginManagerProviderRegistry は Wave 4 で追加）
python -c "from pagefolio.plugins import PluginManager; pm = PluginManager(); assert pm._provider_registry == {}; print('registry OK')"

# build_provider 拡張チェック（既存テスト全通 + tesseract 分岐の基本動作）
pytest tests/ -x -q
python -c "from pagefolio.ocr import build_provider; p = build_provider({'ocr_provider': 'tesseract'}); print(type(p).__name__)"

# リント確認
ruff check pagefolio/ocr_providers.py pagefolio/ocr.py pagefolio/plugins.py
```

### Wave 2 完了後の確認コマンド

```bash
# dialogs テスト（既存の全ダイアログテスト）
pytest tests/ -x -q

# リント確認
ruff check pagefolio/dialogs/llm_config.py
```

### Wave 3 完了後の確認コマンド

```bash
# lang.py 文言キー確認
python -c "from pagefolio.lang import LANG; assert 'tesseract_accuracy_warning' in LANG['ja']; assert 'ocr_progress_skip' not in LANG['ja']; print('OK')"

# バージョン確認
python -c "from pagefolio.constants import APP_VERSION; assert APP_VERSION == '1.4.0'; print('OK')"
```

### Wave 4（フェーズゲート）

```bash
# フルスイート
pytest

# リント・フォーマット
ruff check . && ruff format .

# モジュール起動確認
python -c "from pagefolio.ocr_providers import TesseractProvider, _TESSERACT_AVAILABLE; print('Tesseract available:', _TESSERACT_AVAILABLE)"
```

---

## Rollback

| 問題 | 対処 |
|------|------|
| `_detect_tesseract()` が起動時に長時間ブロックする | `timeout=5` が機能していることを確認。`subprocess.TimeoutExpired` が `(False, frozenset())` にフォールバックしているか確認。 |
| Tesseract インストール済みなのに `_TESSERACT_AVAILABLE = False` | `tesseract --version` を手動実行して PATH を確認。Windows の場合 `where tesseract` でコマンドが見つかるか確認。 |
| `build_provider` の変更で既存テストが壊れる | `plugin_manager=None` デフォルト引数のため既存テストへの影響はないはず。`TypeError` が出る場合はシグネチャ変更が正しく適用されているか確認。 |
| `LLMConfigDialog` が `plugin_manager` を受け取れず AttributeError | 呼び出し箇所（`app.py` 等）で `plugin_manager=self.plugin_manager` を渡しているか確認。 |
| ruff E501 (行長超過) | `pagefolio/lang.py` の長い文言行は文字列結合（`+` または括弧折り返し）で対処。 |
| 既存テストが `sec_ocr` / `ocr_dialog_title` の古い値を期待している | テスト内の期待値を新しい値に合わせて更新する。 |

---

## Source Audit

### GOAL（ROADMAP Phase 7 Goal）

| アイテム | カバー先 |
|---------|---------|
| オフライン環境でも Tesseract が選択肢として使える | Task 1.1, Task 2.1 |
| サードパーティがカスタムプロバイダを登録できる | Task 1.2, Task 1.3, Task 2.1 |
| 全プロバイダの文言・ドキュメントが整備されている | Task 3.1, Task 3.2, Task 3.3 |

### REQ（phase_req_ids）

| REQ-ID | カバー先 |
|--------|---------|
| OCR-EXT-01 | Task 1.1（TesseractProvider）, Task 1.3（build_provider）, Task 2.1（UI統合） |
| OCR-EXT-02 | Task 1.2（register_ocr_provider）, Task 1.3（フォールバック）, Task 2.1（Combobox動的化） |
| OCR-QA-02 | Task 3.1（lang.py）, Task 3.2（README）, Task 3.3（開発履歴） |

### CONTEXT（Decisions）

| Decision | カバー先 |
|----------|---------|
| D-01: 起動時 `_TESSERACT_AVAILABLE` | Task 1.1 |
| D-02: 未インストール時 選択リセット + 案内ラベル | Task 2.1 |
| D-03: 精度劣後注記の常設ラベル | Task 2.1 |
| D-04: `jpn+eng` 固定・`eng` フォールバック | Task 1.1 |
| D-05: `PluginManager._provider_registry` + `register_ocr_provider` | Task 1.2 |
| D-06: プラグインが `on_load` 内で登録 | Task 1.2（docstring で明示） |
| D-07: `build_provider` に `plugin_manager=None` 引数 | Task 1.3 |
| D-08: Combobox values のダイアログ展開時動的生成 | Task 2.1 |
| D-09: `lang.py` Tesseract 専用文言追加・未使用エントリ削除 | Task 3.1 |
| D-10: README OCR セクション更新 | Task 3.2 |
| D-11: 開発履歴.md v1.4.0 追記 | Task 3.3 |

### RESEARCH（主要発見事項）

| 発見事項 | カバー先 |
|---------|---------|
| stdin パイプ方式（Windows 動作確認済み） | Task 1.1（`ocr_image` 実装） |
| `--list-langs` stdout/stderr 両方確認 | Task 1.1（`_detect_tesseract` 実装） |
| `ocr_progress_skip` は未使用 | Task 3.1（削除対象） |
| ttk Combobox 個別 disabled 不可 → 選択リセット方式 | Task 2.1 |
| `build_provider` シグネチャ変更と呼び出し箇所更新 | Task 1.3 |

**スコープ外（除外確認）:**
- Tesseract 言語パック選択 UI → Deferred
- `--psm`/`--oem` 公開オプション → Deferred
- OS キーストア連携 → 次マイルストーン
- OCR 結果のページ埋め込み → 次マイルストーン
