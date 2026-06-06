# OCR プロバイダ化 + クラウドAPI対応 — 見積もり・仕様書

> 本書は設計検討の成果物（見積もり・仕様）であり、実装は含みません。
> 対象バージョン: PageFolio `v1.3.0` 時点の検討。

## 0. 背景・目的

現行 OCR は **LM Studio（OpenAI互換 Vision API）専用** に実装されており、バックエンドが固定されている。
本検討では以下を実現するための設計方針・工数・段階導入計画をまとめる。

- 現行 OCR を **プロバイダ抽象化**し、複数バックエンドを差し替え可能にする。
- **Google AI Studio (Gemini)** および **Claude (Anthropic) API** に対応する。
- **大きな GPU を積んでいない PC での利用**を主想定とする。

---

## 1. 現状整理（結合度）

LM Studio 依存が複数ファイルに散在している。

| ファイル | LM Studio 依存箇所 |
|----------|--------------------|
| `pagefolio/ocr.py` | `build_chat_payload`（OpenAI形式固定）、`call_lm_studio`、`call_lm_studio_parallel`、`fetch_lm_studio_models`、`OCRMixin` |
| `pagefolio/ocr_dialog.py` | `call_lm_studio_parallel` / `fetch_lm_studio_models` を直 import、`url_var` / `model_var` 前提のUI |
| `pagefolio/settings.py` | `lm_studio_url` / `lm_studio_model` / `ocr_*` のデフォルト値 |
| `pagefolio/ui_builder.py` | OCRボタン（現在ページ / 選択ページ） |
| `pagefolio/lang.py` | OCR関連の文言（`ocr_server_label` 等） |

**資産**: 並列処理 `call_lm_studio_parallel` は「画像→テキスト」関数を並列に回すだけの構造で、
**プロバイダ非依存に分離しやすい**。抽象化の土台は整っている。

**プラグインシステム**: `PDFEditorPlugin` はライフサイクル/UIフックのみを持つイベント通知型で、
「サービス/プロバイダを登録する仕組み」は無い。プロバイダを外部プラグイン化する場合は拡張点の新設が必要（フェーズ4・任意）。

---

## 2. 設計方針（確定）

### 2.1 プロバイダ抽象化（採用方式）
`OCRProvider` インターフェース（`ocr_image()`, `list_models()`, 例外規約）を定義し、
各バックエンドを実装クラスとして並べる。**`urllib` 直叩き**で実装し、依存追加なし・PyInstaller 影響なしとする。

> 公式SDK（`anthropic` / `google-genai`）採用は記述が楽だが、PyInstaller の `.exe` 肥大化・隠れ依存取り込みの難点があるため**不採用**。現行方針（urllib）を踏襲。

### 2.2 プロバイダ選択（確定）
```
ocr_provider: "off" | "gemini" | "claude" | "lmstudio" | "tesseract"
  既定値 = "off"
```
- **"off"**: OCR機能を無効化（OCRボタンを非表示 or disabled）。クラウド課金・外部送信を望まないユーザー向けの安全な既定値。
- 既定プロバイダは「人による」ため固定せず、**ユーザーが明示選択**する方式とする。

### 2.3 APIキー管理（確定）
**環境変数からの読み取りのみ。平文保存は一切禁止。**

| プロバイダ | 参照する環境変数 | 備考 |
|-----------|------------------|------|
| Claude | `ANTHROPIC_API_KEY` | SDK慣例に準拠 |
| Gemini | `GEMINI_API_KEY`（無ければ `GOOGLE_API_KEY` をフォールバック） | 両対応 |
| LM Studio | なし | ローカル |
| Tesseract | なし | ローカル |

- `pagefolio_settings.json` には**キーを一切書かない**（保存するのは `ocr_provider` 選択値と非機密設定のみ）。
- 実行時に `os.environ.get(...)` で読むだけ。プロセス内保持はするがファイルへは永続化しない。
- **キー未設定でクラウドプロバイダを選択した場合**: ダイアログで「環境変数 `XXX` が未設定です」と明示エラー表示。入力欄で受け取って保存はしない（平文NG方針の徹底）。
- （任意の逃げ道）ダイアログ入力させる場合も**そのセッション中だけメモリ保持・JSON非書き込み**に限定。

---

## 3. 各APIの差分

| 項目 | LM Studio（現行） | Google AI Studio (Gemini) | Claude (Anthropic) |
|------|-------------------|---------------------------|---------------------|
| エンドポイント | `{url}/v1/chat/completions` | `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | `https://api.anthropic.com/v1/messages` |
| 認証 | なし（ローカル） | `?key=API_KEY` or `x-goog-api-key` | `x-api-key` + `anthropic-version: 2023-06-01` |
| 画像の渡し方 | `image_url`（data URL） | `inline_data: {mime_type, data}` | `source: {type:"base64", media_type, data}` |
| 本文取得 | `choices[0].message.content` | `candidates[0].content.parts[0].text` | `content[0].text`（`type=="text"` を走査） |
| モデル一覧 | `/v1/models` | `/v1beta/models` | `/v1/models` |
| 温度等 | `temperature` 等利用可 | `generationConfig.temperature` | Opus 4.7/4.8 は `temperature` 不可。`output_config.effort` で制御 |
| 推奨モデル | 任意のローカルVLM | `gemini-2.5-flash` / `gemini-2.5-pro` | `claude-haiku-4-5` / `claude-sonnet-4-6` / `claude-opus-4-8` |
| コスト | 無料（ローカル） | 従量課金 | 従量課金 |

---

## 4. 低スペック（GPU非搭載）PC 向けの考慮

主想定が「大きな GPU が無い PC」であるため、設計の重心が変わる。

### 4.1 プロバイダの主従が逆転
ローカルVLM推論は GPU 非搭載では実用的でない（低速 / VRAM不足）。
→ **クラウドAPI（Gemini / Claude）が主役、LM Studio は GPU がある人向けのオプション**という位置づけ。

### 4.2 そもそもOCRが不要なケースを弾く（優先度: 高）
- PDF がテキスト埋め込み済みなら `page.get_text()`（fitz標準・API/GPU不要・一瞬）で取得可能。
- OCR実行前に「テキストを持っているか」を判定し、持っていれば**API/VLMを呼ばず即返す**。
- スキャン画像PDF（テキスト無し）のときだけ Vision API に回す。
- **効果**: 多くのケースでコスト・待ち時間がゼロになる。低スペック・低コスト両面で効果大。

### 4.3 画像レンダリング負荷・メモリ
- `ocr_scale`（既定2.0）の PDF→PNG 変換（`get_pixmap`）は CPU 処理。低スペックでは無視できない負荷。
  → 既定値を `1.5` 前後へ見直す余地。コスト/速度/精度のトレードオフを UI に明示。
- 現行 `_worker` は全ページの base64 画像を `images` dict に**一括保持**してから並列OCRする。
  低RAM PC で大きな PDF を処理するとメモリ逼迫。
  → クラウド主役なら「レンダリング→送信→破棄」を**ページ単位で逐次化**してメモリに溜めない設計が望ましい
  （fitz の同一 Document 並行アクセス回避と両立させること）。

### 4.4 ネットワーク依存・レート制限
- オフライン不可・回線品質依存になる。タイムアウト/リトライ（429・5xx）設計が必要。
- クラウドの並列度はローカルより**絞る**（現行最大8並列は429を誘発しやすい）。

### 4.5 Tesseract（オプション扱い）
GPU不要・無料の古典OCR。ただし**現状あまり機能していない**との報告あり。
効かない典型要因（「テキストベースでないから」ではなく、画像品質・データ不足が主因）:
- **日本語学習データ未導入**（`jpn.traineddata` / 縦書きは `jpn_vert`）
- **入力解像度不足**（概ね300dpi相当が必要 → `ocr_scale` を上げる）
- **複雑レイアウト（表・段組）に弱い**（前処理＝二値化・傾き補正なしだと顕著）

→ VLM には及ばない前提の**オプション**として `OCRProvider` の1実装に留める。縮退先の主役には据えない。
依存（Tesseract本体・言語データのインストール）が必要な点に注意。

---

## 5. ファイル別 工数見積もり

工数目安: **S = 半日以内 / M = 1日前後 / L = 2日前後**

| # | 作業項目 | 対象 | 規模 |
|---|----------|------|------|
| 1 | `OCRProvider` 基底クラス定義（`ocr_image` / `list_models` / 例外規約） | 新規 `ocr_providers.py` | M |
| 2 | LM Studio を Provider 実装へリファクタ | `ocr.py` | M |
| 3 | `call_lm_studio_parallel` を provider非依存の `run_parallel(provider, ...)` に一般化 | `ocr.py` | S |
| 4 | Gemini Provider 実装（payload構築・レスポンス解析・モデル一覧） | `ocr_providers.py` | M |
| 5 | Claude Provider 実装（messages API・effort・モデル一覧） | `ocr_providers.py` | M |
| 6 | OCRDialog のUI改修（プロバイダ選択、APIキー未設定エラー、条件付き表示） | `ocr_dialog.py` | **L** |
| 7 | 設定拡張（`ocr_provider` enum・キー項目は持たない・モデル別デフォルト） | `settings.py` | S |
| 8 | テキスト埋め込み判定によるOCRスキップ | `ocr.py` / `ocr_dialog.py` | S |
| 9 | 逐次レンダリング化（メモリ最適化） | `ocr_dialog.py` | M |
| 10 | 多言語文言追加（プロバイダ名・APIキー未設定・精度注記・コスト警告） | `lang.py` | S |
| 11 | テスト追加（各Providerのpayload構築・レスポンス解析をモックで） | 新規 `tests/test_ocr.py` | M |
| 12 | Tesseract Provider（任意） | `ocr_providers.py` | M |
| 13 | （任意・フェーズ4）PluginManager にプロバイダ登録フック新設 | `plugins.py` / `app.py` | M |
| 14 | ドキュメント更新（開発履歴.md / README / バージョン） | 各md | S |

**合計目安**
- コア（プロバイダ抽象化 + Gemini + Claude + 低スペック対策）: **概ね 6〜8 人日**
- Tesseract 込み: **+1 人日**
- プラグイン登録機構（解釈B）込み: **さらに +2〜3 人日**

---

## 6. 段階導入ロードマップ

1タスクずつ完了させる方針に沿う。

- **フェーズ1**: プロバイダ抽象化（#1〜#3）+ テキスト埋め込み判定（#8）。
  既存挙動を変えずに内部刷新し、テストで担保。
- **フェーズ2**: Claude Provider 追加（#5, #6一部, #7, #10）。APIキーは環境変数参照で最小実装。
- **フェーズ3**: Gemini Provider 追加（#4）+ 逐次レンダリング化（#9）。
- **フェーズ4（任意）**: Tesseract（#12）/ プラグイン登録機構（#13）。

---

## 7. リスク・考慮点

| 項目 | 内容 | 対応方針 |
|------|------|----------|
| プライバシー | クラウドAPIはページ画像を外部送信（現行はローカル完結） | 実行前に明示。既定 `off` で安全側 |
| コスト | 従量課金。大量ページ一括は高額化 | 実行前にページ数×概算コスト表示・確認ダイアログ検討 |
| レート制限 | クラウドで429誘発 | プロバイダごとに並列度上限を分ける |
| メモリ | 大PDF×低RAM で逼迫 | 逐次レンダリング（#9） |
| PyInstaller | 公式SDK採用時に隠れ依存 | urllib 踏襲で回避 |
| 環境変数 | キー未設定での実行 | 明示エラー表示（保存はしない） |

---

## 8. 確定事項 / 未決定事項

### 確定
- 方式: プロバイダ抽象化（`urllib` 直叩き・依存追加なし）。
- プロバイダ: `off` / `gemini` / `claude` / `lmstudio` / `tesseract` の選択式、既定 `off`。
- APIキー: 環境変数のみ（`ANTHROPIC_API_KEY` / `GEMINI_API_KEY`）、**平文保存禁止**、未設定時は明示エラー。
- 低スペック対策: テキスト埋め込み判定でOCRスキップ・逐次レンダリング・`ocr_scale` 見直し。
- Tesseract: オプション扱い（精度劣後注記つき）。

### 未決定（実装前に確定が必要）
- プラグイン登録機構（解釈B）をフェーズ4で実装するか否か。
  → フェーズ1〜3には影響しないため後回し可能。
