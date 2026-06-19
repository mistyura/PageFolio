# Phase 5: Claude Provider + セキュリティ基盤 + プロバイダ選択 UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 5-claude-provider-ui
**Areas discussed:** キーの持ち方, プロバイダ選択とモデル一覧, コスト確認ダイアログ, バックオフとモデル別パラメータ防御

---

## キーの持ち方（セキュリティ基盤）

### セッション中 API キーの保持場所

| Option | Description | Selected |
|--------|-------------|----------|
| App の専用一時属性 | settings と別オブジェクトに保持。_save_settings は settings のみ保存で構造的に混入不可。終了で消滅 | ✓ |
| Provider にのみ注入 | build_provider 時に読んで Provider に渡し、アプリ側に残さない | |

### 環境変数と入力欄の優先順位

| Option | Description | Selected |
|--------|-------------|----------|
| 環境変数を優先 | ANTHROPIC_API_KEY があればそれを使い、未設定時のみ入力欄 | ✓ |
| 入力欄を優先 | 入力欄に値があれば環境変数を上書き | |

### セッションキー入力欄の場所

| Option | Description | Selected |
|--------|-------------|----------|
| 実行時ダイアログ内 | クラウド選択かつ未設定時のみ、実行前に表示 | ✓ |
| SettingsDialog 内 | 設定画面のプロバイダ設定欄に置く | |
| 両方 | 事前入力も実行時入力も可能 | |

### 入力欄の表示・取り扱い

| Option | Description | Selected |
|--------|-------------|----------|
| マスク + ログ非出力 | show="*"・キー値をログ/結果/エラーに出さない | ✓ |
| 平文表示 | 入力値をそのまま表示 | |

**User's choice:** App 専用一時属性 / 環境変数優先 / 実行時ダイアログ内 / マスク + ログ非出力
**Notes:** `_save_settings` が settings 辞書をそのまま JSON 化する点が設計の急所。キーを settings に入れないことが唯一かつ最重要のガード。`os.environ` にも書かない（OCR-SEC-03）。

---

## プロバイダ選択とモデル一覧

### プロバイダ選択 UI の位置

| Option | Description | Selected |
|--------|-------------|----------|
| llm_config に集約 | 既存 OCR 設定欄の先頭に provider ドロップダウン、選択で下位欄切替 | ✓ |
| SettingsDialog 直下 | 上位ダイアログに provider 選択、OCR 詳細は llm_config に委譲 | |

### モデル一覧の取得方式

| Option | Description | Selected |
|--------|-------------|----------|
| 静的リスト + 任意で API 更新 | 推奨モデルの静的リストを持ち、「モデル更新」ボタンで list_models 取得。キー未設定/オフラインでも選択肢あり | ✓ |
| 選択時に自動 API 取得 | プロバイダ選択ごとに list_models を自動呼び出し | |

### off の挙動

| Option | Description | Selected |
|--------|-------------|----------|
| ボタンを disabled 化 | off で OCR 関連ボタンを無効化、設定へ誘導 | ✓ |
| 押下時に設定へ誘導 | ボタンは有効のまま、押したらダイアログで誘導 | |

**User's choice:** llm_config に集約 / 静的リスト + 任意で API 更新 / ボタンを disabled 化
**Notes:** STACK.md の推奨モデル（claude-haiku-4-5 / sonnet-4-6 / opus-4-8）を静的リストの初期値にする。

---

## コスト確認ダイアログ

### 概算コストの算出・表示方法

| Option | Description | Selected |
|--------|-------------|----------|
| モデル別単価×ページの粗い範囲 | MTok 価格表を根拠に「約 $X 程度」と範囲表示 | ✓ |
| ページ数と課金注意のみ | 金額は出さずページ数 + 従量課金注意のみ | |

### 「今後表示しない」オプション

| Option | Description | Selected |
|--------|-------------|----------|
| 設けない（毎回確認） | クラウド実行のたびに必ず確認 | ✓ |
| セッション内のみ抑制可 | チェックで当該セッション中は再確認しない | |
| settings に永続化 | 以後恒久に抑制 | |

### プライバシー注記の内容

| Option | Description | Selected |
|--------|-------------|----------|
| 送信先 + 画像送信 + 課金の3点 | ホスト名・画像が外部送信・従量課金を明示 | ✓ |
| 最小（一文） | 「外部に送信されます」の一文のみ | |

**User's choice:** モデル別単価×ページの粗い範囲 / 設けない（毎回確認）/ 送信先 + 画像送信 + 課金の3点
**Notes:** クラウド（claude/gemini）のみ表示。lmstudio/tesseract/off には出さない。キャンセルで中止可。

---

## バックオフとモデル別パラメータ防御

### 429/5xx 指数バックオフの配置

| Option | Description | Selected |
|--------|-------------|----------|
| run_parallel 共通層 + 型付き例外 | Provider が OCRRetryableError(retry_after) を投げ、run_parallel が sleep/回数/進捗を一元管理。Phase 6 で再利用 | ✓ |
| Provider.ocr_image 内 | 各プロバイダが自分の HTTP 呼び出しを内部リトライ | |

### 「待機中」UI の表示

| Option | Description | Selected |
|--------|-------------|----------|
| 既存 on_progress でページ単位表示 | 進捗コールバックで「待機中（リトライ n/3）」表示 | ✓ |
| 専用の待機インジケータ | リトライ中を示す専用表示を新設 | |

### effort/temperature 送信判定の持ち場所

| Option | Description | Selected |
|--------|-------------|----------|
| Provider 内の能力判定 | モデル ID プレフィックス/能力マップで effort 可否判定。payload 構築を Provider に集約 | ✓ |
| UI 側で判定 | llm_config がモデルごとに送るパラメータを判定して渡す | |

### effort パラメータの UI 表示

| Option | Description | Selected |
|--------|-------------|----------|
| 対応モデル時のみ effort 欄 | effort 対応モデル選択時のみ effort ドロップダウン、非対応時は temperature 欄 | ✓ |
| effort は内部固定（low） | UI に出さず内部 low 固定、temperature 欄のみ | |

**User's choice:** run_parallel 共通層 + 型付き例外 / 既存 on_progress でページ単位表示 / Provider 内の能力判定 / 対応モデル時のみ effort 欄
**Notes:** STACK.md 確定 — temperature は全モデル可、effort は output_config.effort・Haiku 非対応。Retry-After ヘッダ優先・最大3回。

---

## Claude's Discretion

- セッションキー属性のデータ構造（単一値 vs プロバイダ別 dict）
- コスト見積もりの係数・トークン換算の粗さ
- `OCRRetryableError` の型名・`run_parallel` への組み込み方（既存 fatal/error 構造との統合）
- モデル能力マップの実装形（プレフィックス判定 vs 明示 dict）
- effort/temperature 欄 UI 切替の具体ウィジェット実装
- Claude payload の `max_tokens` 既定値（STACK.md は 4096 を例示）

## Deferred Ideas

- GeminiProvider・逐次レンダリング化・`ocr_scale` 1.5 化 → Phase 6
- OCR モックテストの本格整備 → Phase 6（Phase 5 では守りの最小テストを検討）
- TesseractProvider・PluginManager 登録フック・多言語文言整備・ドキュメント更新 → Phase 7
- OS キーストア連携によるキー永続化 → 次マイルストーン
