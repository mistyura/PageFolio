# Phase 2: OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加 - Discussion Log

> **監査証跡専用。** プランニング・リサーチ・実行エージェントへの入力には使用しないこと。
> 決定事項は CONTEXT.md に記録されている。本ログは検討した代替案を保存するためのもの。

**Date:** 2026-08-11
**Phase:** 2-ocr-openai-chatgpt
**Areas discussed:** catalog 一元化の範囲, モデル一覧の取得とフィルタ, パラメータ非互換の分岐方式, OpenAI 固有設定の UI

---

## catalog 一元化の範囲

### Q1: catalog.py に載せるデータの範囲

| Option | Description | Selected |
|--------|-------------|----------|
| プロバイダ単位のメタデータ全部 | ProviderMeta 7 フィールド + API キー欠落 LANG キー。価格表は粒度が違うため除外 | ✓ |
| 価格表まで含めて全部 | OCR_PRICE_TABLE も catalog へ。二重定義は消えるが粒度が混在 | |
| 最小限（OpenAI 追加に必要な分だけ） | 表示名・クラウド判定・host・一覧リストの 4 種に絞る | |

**User's choice:** プロバイダ単位のメタデータ全部（推奨）
**Notes:** 「プロバイダ 1 件につき 1 値」で粒度が揃うものを catalog の境界とした。→ D-01 / D-02

### Q2: 既存参照面（6 面）の移行範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 全参照面を今フェーズで完走 | catalog 追加 → 1 ファイルずつ段階移行 → OpenAI 追加 | ✓ |
| OpenAI が触る面を優先・残りは後回し | フェーズは短くなるが重複が一部残る | |
| 1 プランで一括置換 | プラン数は減るが原因切り分けが困難（研究は不推奨と明記） | |

**User's choice:** 全参照面を今フェーズで完走（推奨）
**Notes:** → D-03（Reversibility: costly）

### Q3: catalog にないプラグインプロバイダの扱い

| Option | Description | Selected |
|--------|-------------|----------|
| 未登録は非クラウド扱い + isinstance フォールバック維持 | 研究推奨。プラグインが既存クラウドプロバイダを継承していればコスト確認が出る | ✓ |
| isinstance 判定を撤去し catalog 一本化 | 判定経路 1 本だが外部送信の明示同意方針が弱まる | |
| プラグインが catalog へ登録できる API を新設 | 拡張性は上がるが新しい能力の追加でスコープ外 | |

**User's choice:** 未登録は非クラウド扱い + isinstance フォールバック維持（推奨）
**Notes:** 判定経路 2 本を承知のうえで安全側を優先。→ D-04（新設 API 案は Deferred へ）

### Q4: default_model と RECOMMENDED_MODELS の一致担保

| Option | Description | Selected |
|--------|-------------|----------|
| catalog を真実源にしテストで一致を機械保証 | catalog は Provider を import せず軽量に保つ | ✓ |
| Provider クラスから catalog が導出 | 重複ゼロだが catalog が重い import 連鎖を背負う | |
| RECOMMENDED_MODELS を catalog へ完全移管 | 真実源は 1 箇所だが Provider の自完結性が失われる | |

**User's choice:** catalog を真実源にしテストで一致を機械保証（推奨）
**Notes:** → D-05 / D-06

---

## モデル一覧の取得とフィルタ

### Q1: コンボボックスへ何を出すか

| Option | Description | Selected |
|--------|-------------|----------|
| 名前ヒューリスティックで絞る | gpt-*/o* 系を採用し embedding/tts/whisper 等を除外。純関数化してテスト | ✓ |
| 生の全一覧をそのまま出す | 新モデルを取りこぼさないが OCR に使えないモデルが混ざる | |
| 静的推奨リストを優先・API 一覧は補完 | 推奨は目立つが他 4 プロバイダと一覧の順序ロジックが異なる | |

**User's choice:** 名前ヒューリスティックで絞る（推奨）
**Notes:** OpenAI の /v1/models には vision 対応フラグが無く Claude 方式の自動フィルタが再現不能。→ D-07

### Q2: 静的フォールバック一覧と既定モデルの確定方法

| Option | Description | Selected |
|--------|-------------|----------|
| 実装時に実キーで取得して確定 | プランに「実キーで GET /v1/models を目視確認」をタスクとして明記 | ✓ |
| リサーチ時点の推定リストで固定 | 実装は止まらないが存在しないモデル名が既定値になるリスク | |
| 静的リストは最小限にし API 取得を主経路に | 陳腐化面は小さいが API キー未設定時の体験が他プロバイダと揃わない | |

**User's choice:** 実装時に実キーで取得して確定（推奨）
**Notes:** リサーチが Gap として残した宿題。→ D-09

### Q3: フィルタ結果 0 件時の振る舞い

| Option | Description | Selected |
|--------|-------------|----------|
| 静的リストへフォールバック | 取得失敗時（V190-OAI-03）と同一経路に合流し失敗パスを 1 本化 | ✓ |
| フィルタを外して生の全一覧を出す | 新モデルを取りこぼさないが embedding 等も混ざる | |
| 空のまま・エラー表示 | 問題は早期に露見するが OCR が使えない状態に陥る | |

**User's choice:** 静的リストへフォールバック（推奨）
**Notes:** → D-08

---

## パラメータ非互換の分岐方式

### Q1: モデル別パラメータ非互換の判定方式

| Option | Description | Selected |
|--------|-------------|----------|
| 常に新形式を送り、非対応パラメータは省略 | Gemini の _is_legacy_gemini と同型の安全側。未知モデルでも 400 にならない | ✓ |
| 許可リスト方式（Claude の EFFORT_MODELS 踏襲） | 見た目は揃うが未知モデルが常に非対応判定になり集合の永続保守が必要 | |
| 400 応答を見て 1 度だけ再送する適応方式 | モデル名の知識が不要だが失敗経路が増え既存リトライ基盤と相互作用が複雑化 | |

**User's choice:** 常に新形式を送り、非対応パラメータは省略（推奨）
**Notes:** → D-10

### Q2: temperature を送る対象の絞り方

| Option | Description | Selected |
|--------|-------------|----------|
| 推論系モデルには送らない | モデル ID の命名規則で判定。純関数に集約してテスト | ✓ |
| OpenAI には一切送らない | 最も壊れにくいが temperature スライダーが無反応になり UI 上の誤解を生む | |
| 常に送る | 実装は最小だが o-series で 400 になり V190-OAI-12 を満たさない | |

**User's choice:** 推論系モデルには送らない（推奨）
**Notes:** → D-11 / D-13

### Q3: エラーマッピングの方針

| Option | Description | Selected |
|--------|-------------|----------|
| 既存 errors.py をそのまま流用・必要時のみマーカー追加 | 他 5 プロバイダの挙動を変えない | ✓ |
| OpenAI 専用のエラー分岐を新設 | メッセージは正確になるが共通基盤の外に 6 本目の分岐が生まれる | |

**User's choice:** そのまま流用・必要時のみマーカー追加（推奨）
**Notes:** errors.py は既に「OpenAI 互換: context_length_exceeded」マーカーを実装済み。→ D-12

### Q4: 並列度の既定値

| Option | Description | Selected |
|--------|-------------|----------|
| Claude 相当の 2/2 | tier 依存のレート制限に対し保守的。超過分はリトライ基盤に任せる | ✓ |
| もう少し高め（3/4 程度） | スループット優先だが低 tier ユーザーで 429 頻発の恐れ | |

**User's choice:** Claude 相当の 2/2（推奨）
**Notes:** → D-14

---

## OpenAI 固有設定の UI

### Q1: reasoning effort の UI

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAI 専用欄・専用設定キー | Anthropic の effort とは意味論・値域が異なるため分離 | ✓ |
| 既存 effort 欄を共用（ocr_effort を流用） | UI 差分は最小だが値域変更時に一方を壊す | |
| 今回は effort を実装しない | 変更面は減るが V190-OAI-09 未達成 | |

**User's choice:** OpenAI 専用欄・専用設定キー（推奨）
**Notes:** → D-15

### Q2: 「対応モデル選択時のみ有効化」の判定

| Option | Description | Selected |
|--------|-------------|----------|
| temperature 判定と同じ純関数を共用 | 推論系 = temperature 省略 + effort 有効。判定経路 1 本（Phase 1 D-18 と整合） | ✓ |
| 許可リスト（EFFORT_MODELS 相当） | Claude と見た目は揃うが新モデルごとに集合更新が必要 | |
| 常に表示し送信も常に行う | 実装は最小だが非対応モデルで 400 になり要件未達 | |

**User's choice:** temperature 判定と同じ純関数を共用（推奨）
**Notes:** → D-13

### Q3: 画像 detail レベルの既定値

| Option | Description | Selected |
|--------|-------------|----------|
| high | OCR 用途では読み取り精度が最優先。コストは low へ下げて制御 | ✓ |
| auto | バランスは良いが精度低下の原因がユーザーから見えにくい | |
| low | コスト最優先だが小さい文字の誤認識が増え OCR の主目的を損なう | |

**User's choice:** high（推奨）
**Notes:** → D-16

### Q4: organization / project ID の配置

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAI セクション内の通常項目 | 既存 5 プロバイダのセクション構成と揃い実装も最小 | ✓ |
| 折りたたみの詳細設定領域へ格納 | 研究推奨だが既存ダイアログに折りたたみ UI の前例がない | |
| 環境変数のみ対応（UI なし） | 変更面は最小だが「任意入力できる」要件を満たさない | |

**User's choice:** OpenAI セクション内の通常項目（推奨）
**Notes:** 空のときはヘッダを一切付与しない。→ D-17

---

## Claude's Discretion

- 新規プロバイダ実装ファイルの名前（`openai_provider.py` / `openai.py`）
- `ProviderMeta` のフィールド名・`catalog.py` の公開関数シグネチャ
- ヒューリスティックフィルタ（D-07）と推論系判定（D-13）を置くモジュール
- `build_provider` の OpenAI 分岐における `max_tokens <= 0` のクランプ値
- catalog 段階移行（D-03）のプラン分割粒度
- OpenAI モデルの `OCR_PRICE_TABLE` 単価エントリの粒度と未知モデル時の扱い
- 新設テストのファイル配置

## Deferred Ideas

- `OCR_PRICE_TABLE` の一元化（モデル単位データの置き場を作る場合に再検討）
- `dialogs/llm_config/dialog.py` のセッション API キー同期ループの完全動的化（V190-F-03・v2）
- プラグインプロバイダが catalog へメタデータを登録できる API（プラグイン API 拡張のためスコープ外）
- `ocr_dialog.py` の isinstance フォールバック判定の撤去（上記 API 導入後に判定経路を 1 本化）
