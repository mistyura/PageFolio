# Requirements

## Active

### R006 — プロバイダを切り替えたとき、該当プロバイダのモデル一覧を取得して選択肢に提示する

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-API-03

プロバイダを切り替えたとき、該当プロバイダのモデル一覧を取得して選択肢に提示する

### R007 — APIキーは環境変数からのみ取得し、`pagefolio_settings.json` に書き込まない（`_save_settings()` への流入ガード）

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-SEC-01

APIキーは環境変数からのみ取得し、`pagefolio_settings.json` に書き込まない（`_save_settings()` への流入ガード）

### R008 — APIキー未設定でクラウド OCR を実行しようとしたとき、実行前に明示的なエラーを表示する（黙って失敗しない）

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-SEC-02

APIキー未設定でクラウド OCR を実行しようとしたとき、実行前に明示的なエラーを表示する（黙って失敗しない）

### R009 — 環境変数が未設定のユーザーは、保存されないセッション中メモリのキー入力欄からキーを与えて OCR を実行できる（`os.environ` にも書かない）

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-SEC-03

環境変数が未設定のユーザーは、保存されないセッション中メモリのキー入力欄からキーを与えて OCR を実行できる（`os.environ` にも書かない）

### R010 — ユーザーは SettingsDialog でプロバイダ（off / gemini / claude / lmstudio / tesseract）を選択できる

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-UI-01

ユーザーは SettingsDialog でプロバイダ（off / gemini / claude / lmstudio / tesseract）を選択できる

### R011 — 既定は `ocr_provider: "off"` で、off のとき OCR ボタンを無効化し外部送信・課金を防ぐ

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-UI-02

既定は `ocr_provider: "off"` で、off のとき OCR ボタンを無効化し外部送信・課金を防ぐ

### R012 — クラウドプロバイダ選択時、実行前にページ数 × 概算コストとプライバシー注記の確認ダイアログを表示する（ローカル/Tesseract には表示しない）

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-UI-03

クラウドプロバイダ選択時、実行前にページ数 × 概算コストとプライバシー注記の確認ダイアログを表示する（ローカル/Tesseract には表示しない）

## Validated

### BUG-01 — ページ挿入操作を Undo すると、挿入前の状態に正しく戻る

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

ページ挿入操作を Undo すると、挿入前の状態に正しく戻る

### BUG-02 — 大きな PDF で Undo を実行しても UI がブロックしない

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

大きな PDF で Undo を実行しても UI がブロックしない

### BUG-03 — ページ切り替え時にプレビューのシリアライズを行わない

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

ページ切り替え時にプレビューのシリアライズを行わない

### REFAC-01 — `dialogs.py` を `pagefolio/dialogs/` サブパッケージに分割する

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

`dialogs.py` を `pagefolio/dialogs/` サブパッケージに分割する

### REFAC-02 — `constants.py` を `lang.py` / `themes.py` に分割する

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

`constants.py` を `lang.py` / `themes.py` に分割する

### REFAC-03 — Undo スタックを `collections.deque(maxlen=MAX_UNDO)` に変更する

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Undo スタックを `collections.deque(maxlen=MAX_UNDO)` に変更する

### REFAC-04 — `settings._current_font_size` 外部アクセスを公開関数に変更する

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

`settings._current_font_size` 外部アクセスを公開関数に変更する

### TEST-01 — BUG-01（挿入 Undo）の動作を検証するユニットテスト

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

BUG-01（挿入 Undo）の動作を検証するユニットテスト

### TEST-02 — BUG-03（プレビュー生成）の回帰テスト

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

BUG-03（プレビュー生成）の回帰テスト

### TEST-03 — REFAC-01〜04 の import 回帰テスト

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

REFAC-01〜04 の import 回帰テスト

### R001 — `OCRProvider` 抽象基底クラスを定義し、認識（`recognize`）・モデル一覧取得・並列度ポリシーの共通インターフェースを持つ

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-PROV-01

`OCRProvider` 抽象基底クラスを定義し、認識（`recognize`）・モデル一覧取得・並列度ポリシーの共通インターフェースを持つ

### R002 — 既存 LM Studio OCR を `LMStudioProvider` 実装へリファクタし、既存の OCR 挙動を後方互換で維持する

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-PROV-02

既存 LM Studio OCR を `LMStudioProvider` 実装へリファクタし、既存の OCR 挙動を後方互換で維持する

### R003 — `run_parallel()` をプロバイダ非依存に一般化し、プロバイダ別の並列度を受け取れるようにする

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-PROV-03

`run_parallel()` をプロバイダ非依存に一般化し、プロバイダ別の並列度を受け取れるようにする

### R004 — ユーザーは Claude（messages API・モデル一覧・`ANTHROPIC_API_KEY`）でページを OCR できる

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-API-01

ユーザーは Claude（messages API・モデル一覧・`ANTHROPIC_API_KEY`）でページを OCR できる

### R005 — ユーザーは Gemini（generateContent・inline_data・モデル一覧・`GEMINI_API_KEY`/`GOOGLE_API_KEY`）でページを OCR できる

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-API-02

ユーザーは Gemini（generateContent・inline_data・モデル一覧・`GEMINI_API_KEY`/`GOOGLE_API_KEY`）でページを OCR できる

### R013 — Opus 系モデル選択時の temperature/effort をモデル別に防御的に扱う（非対応パラメータは送らず、`effort` を提示）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-UI-04

Opus 系モデル選択時の temperature/effort をモデル別に防御的に扱う（非対応パラメータは送らず、`effort` を提示）

### R014 — テキストが埋め込まれたページは `page.get_text()` の結果を採用し、Vision API 呼び出しをスキップする

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-PERF-01

テキストが埋め込まれたページは `page.get_text()` の結果を採用し、Vision API 呼び出しをスキップする

### R015 — ページ単位の逐次レンダリング → 送信 → 破棄でメモリ使用量を抑える（全ページ画像の一括保持を廃止）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-PERF-02

ページ単位の逐次レンダリング → 送信 → 破棄でメモリ使用量を抑える（全ページ画像の一括保持を廃止）

### R016 — クラウドプロバイダは並列度を抑制する（Gemini=1 / Claude=2、ローカル LM Studio は最大 8）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-PERF-03

クラウドプロバイダは並列度を抑制する（Gemini=1 / Claude=2、ローカル LM Studio は最大 8）

### R017 — 429 / 5xx 応答に対し指数バックオフでリトライする（最大 3 回・`Retry-After` ヘッダ優先）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-PERF-04

429 / 5xx 応答に対し指数バックオフでリトライする（最大 3 回・`Retry-After` ヘッダ優先）

### R018 — `ocr_scale` のデフォルトを 1.5 に見直し、速度/コスト ↔ 精度のトレードオフヒントを UI に表示する

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-PERF-05

`ocr_scale` のデフォルトを 1.5 に見直し、速度/コスト ↔ 精度のトレードオフヒントを UI に表示する

### R019 — ユーザーは Tesseract（オフライン・無料・精度劣後注記つき）でページを OCR できる

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-EXT-01

ユーザーは Tesseract（オフライン・無料・精度劣後注記つき）でページを OCR できる

### R020 — PluginManager にカスタム OCR プロバイダ登録フック（`register_ocr_provider`）を追加し、サードパーティが独自バックエンドを登録できる

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-EXT-02

PluginManager にカスタム OCR プロバイダ登録フック（`register_ocr_provider`）を追加し、サードパーティが独自バックエンドを登録できる

### R021 — 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定をモックでテストする（`tests/test_ocr.py`）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-QA-01

各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定をモックでテストする（`tests/test_ocr.py`）

### R022 — プロバイダ名・APIキー未設定・精度注記・コスト警告の多言語文言（`lang.py`）と README/開発履歴を更新する

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: OCR-QA-02

プロバイダ名・APIキー未設定・精度注記・コスト警告の多言語文言（`lang.py`）と README/開発履歴を更新する

### R023 — ユーザーは選択したページの後ろに白紙ページを挿入できる（`_insert_blank_page`）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-PAGE-01

ユーザーは選択したページの後ろに白紙ページを挿入できる（`_insert_blank_page`）

### R024 — ユーザーは選択したページにテキスト形式の透かしやページ番号を追加できる（ミニマム実装としてテキストのみ対応、画像ロゴは除外）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-PAGE-02

ユーザーは選択したページにテキスト形式の透かしやページ番号を追加できる（ミニマム実装としてテキストのみ対応、画像ロゴは除外）

### R025 — ページの削除、結合、分割を実行した際、元のPDFに含まれるしおり（TOC）情報が可能な限り保持・調整される

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-PAGE-03

ページの削除、結合、分割を実行した際、元のPDFに含まれるしおり（TOC）情報が可能な限り保持・調整される

### R026 — ユーザーはツールバーのスライダーを使用して、サムネイルサイズを動的にリサイズできる

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-UIUX-01

ユーザーはツールバーのスライダーを使用して、サムネイルサイズを動的にリサイズできる

### R027 — 外部PDFファイルをサムネイルペイン内の特定位置にドラッグ＆ドロップすることで、その位置にファイルを挿入できる

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-UIUX-02

外部PDFファイルをサムネイルペイン内の特定位置にドラッグ＆ドロップすることで、その位置にファイルを挿入できる

### R028 — `pagefolio_settings.json` を編集することで、各種アクションのキーボードショートカットをカスタマイズ・動的読み込みできる（ミニマム実装）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-UIUX-03

`pagefolio_settings.json` を編集することで、各種アクションのキーボードショートカットをカスタマイズ・動的読み込みできる（ミニマム実装）

### R029 — LLM設定ダイアログ（`LLMConfigDialog`）にカスタムプロンプトを入力できるテキストエリアを追加する

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-OCR-01

LLM設定ダイアログ（`LLMConfigDialog`）にカスタムプロンプトを入力できるテキストエリアを追加する

### R030 — ユーザーが入力したカスタムプロンプトを保存し、OCRバックエンドに渡すことで、任意の構造化データ抽出等の指示を出せる

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-OCR-02

ユーザーが入力したカスタムプロンプトを保存し、OCRバックエンドに渡すことで、任意の構造化データ抽出等の指示を出せる

### R031 — 全ての新規追加コードに対して `ruff check` および `ruff format` を適用し、リント・フォーマットエラーがないこと

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-QA-01

全ての新規追加コードに対して `ruff check` および `ruff format` を適用し、リント・フォーマットエラーがないこと

### R032 — `pytest` による自動テストを実行し、既存機能および新規追加機能（特にカスタムプロンプト連携など）でテストがPassすること

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V15-QA-02

`pytest` による自動テストを実行し、既存機能および新規追加機能（特にカスタムプロンプト連携など）でテストがPassすること

### R033 — ユーザーは LLM設定ダイアログで Claude / Gemini / RunPod の APIキーを入力できる（セッション限定・`settings.json` へは保存されない）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-KEY-01

ユーザーは LLM設定ダイアログで Claude / Gemini / RunPod の APIキーを入力できる（セッション限定・`settings.json` へは保存されない）

### R034 — キー解決は「入力値 → 環境変数」の優先順で行われ、両方未設定の場合はエラーが表示される

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-KEY-02

キー解決は「入力値 → 環境変数」の優先順で行われ、両方未設定の場合はエラーが表示される

### R035 — OCRDialog 側の既存セッションキー入力欄は撤去され、キー設定導線が LLM設定ダイアログに一元化される

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-KEY-03

OCRDialog 側の既存セッションキー入力欄は撤去され、キー設定導線が LLM設定ダイアログに一元化される

### R036 — RunPod もセッションキー機構（`_session_api_keys`）で扱える

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-KEY-04

RunPod もセッションキー機構（`_session_api_keys`）で扱える

### R037 — ユーザーはショートカットを設定ダイアログの GUI で編集できる（JSON 直接編集不要）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-UIUX-01

ユーザーはショートカットを設定ダイアログの GUI で編集できる（JSON 直接編集不要）

### R038 — エラー表示・文言の一貫性が監査・修正される（ja/en 辞書の欠落/未使用キー含む・L-5 吸収）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-UIUX-02

エラー表示・文言の一貫性が監査・修正される（ja/en 辞書の欠落/未使用キー含む・L-5 吸収）

### R039 — SettingsDialog / LLMConfigDialog の項目配置・セクションが整理される

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-UIUX-03

SettingsDialog / LLMConfigDialog の項目配置・セクションが整理される

### R040 — L-6 小物が現行コード照合の上で一括解消される（プログレス 100% 問題・URL スキーム検証・モデル名エスケープ・`_fetch_models`/`_test_connection` 重複解消 等）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-OCR-01

L-6 小物が現行コード照合の上で一括解消される（プログレス 100% 問題・URL スキーム検証・モデル名エスケープ・`_fetch_models`/`_test_connection` 重複解消 等）

### R041 — TesseractProvider が `tesseract_lang` 設定を尊重する（利用不可時は自動フォールバック・L-4）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-OCR-02

TesseractProvider が `tesseract_lang` 設定を尊重する（利用不可時は自動フォールバック・L-4）

### R042 — プラグイン OCR registry が堅牢化される（重複名警告・unload 時登録解除・公開アクセサ・L-2/L-3）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-OCR-03

プラグイン OCR registry が堅牢化される（重複名警告・unload 時登録解除・公開アクセサ・L-2/L-3）

### R043 — producer-consumer ロジックが一本化される（`ocr.py` 未使用ヘルパーと `ocr_dialog.py` 独自実装の二重実装解消・L-1）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-OCR-04

producer-consumer ロジックが一本化される（`ocr.py` 未使用ヘルパーと `ocr_dialog.py` 独自実装の二重実装解消・L-1）

### R044 — ユーザーは画像（ロゴ）を透かしとして追加できる（v1.5.0 テキストのみ制限の解除）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-PAGE-01

ユーザーは画像（ロゴ）を透かしとして追加できる（v1.5.0 テキストのみ制限の解除）

### R045 — 黒塗り/モザイクの使い勝手が改善される（具体項目は棚卸しで確定）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-PAGE-02

黒塗り/モザイクの使い勝手が改善される（具体項目は棚卸しで確定）

### R046 — 回転/トリミングの操作性が改善される（具体項目は棚卸しで確定）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-PAGE-03

回転/トリミングの操作性が改善される（具体項目は棚卸しで確定）

### R047 — v1.5.0 新機能（白紙挿入・透かし・ページ番号・TOC 保持・D&D 挿入・ショートカット読込）の回帰テストが整備される

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-TEST-01

v1.5.0 新機能（白紙挿入・透かし・ページ番号・TOC 保持・D&D 挿入・ショートカット読込）の回帰テストが整備される

### R048 — APIキー新機能のテストが整備される（優先順解決・非保存ガード回帰）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-TEST-02

APIキー新機能のテストが整備される（優先順解決・非保存ガード回帰）

### R049 — 既知軽微バグが棚卸しされ、活き残りが解消される（L-6 の現行照合と重複しない範囲）

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: none yet

Legacy ID: V171-TEST-03

既知軽微バグが棚卸しされ、活き残りが解消される（L-6 の現行照合と重複しない範囲）

## Deferred

## Out of Scope
