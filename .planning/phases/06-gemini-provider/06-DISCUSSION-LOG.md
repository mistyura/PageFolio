# Phase 6: Gemini Provider + 逐次レンダリング最適化 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 6-gemini-provider
**Areas discussed:** 逐次レンダリング方式, ocr_scale 1.5 移行とヒント, Gemini パラメータ UI, OCR モックテストの範囲

---

## 逐次レンダリング方式（OCR-PERF-02）

### メモリ上限を保証する逐次化の方式

| Option | Description | Selected |
|--------|-------------|----------|
| 上限付きバッファ(推奨) | producer-consumer。メインが先読みレンダリングし上限 N 枚のキューに積み、ワーカーが消費したら破棄。メモリ上限を保ちつつ LM Studio の並列(最大8)も維持。スレッド境界は fitz=生産者/API=消費者で明確 | ✓ |
| 完全逐次(render1→send1) | 1ページずつ render→send→破棄。メモリ最小だが並列ゼロ。LM Studio の8並列を失う | |
| クラウドのみ逐次・ローカルは現状維持 | クラウドは逐次化・LM Studio は現状(全件一括)のまま。コードパスが2通りに分岐し保守性が下がる | |

**User's choice:** 上限付きバッファ(推奨)

### 先読みバッファの上限枚数

| Option | Description | Selected |
|--------|-------------|----------|
| 並列度連動(推奨) | 上限 = concurrency + 少しの余裕。ワーカーが飢えず、クラウド(1-2)では極小・LM Studio(8)でも上限付き | ✓ |
| 小さめ固定(例: 4枚) | 並列度に関わらず固定上限。シンプルだが LM Studio 8並列時にワーカーが部分的に飢える可能性 | |
| Claude 裁量 | 計画/実装段階で最適値を決める | |

**User's choice:** 並列度連動(推奨)

### 進捗 UI 表示

| Option | Description | Selected |
|--------|-------------|----------|
| 統合プログレス(推奨) | 「処理済み X/総数」の単一バー。逐次化でレンダリングと送信が混ざるため OCR 完了ページ数を主軸に。スキップページも処理済みに含める | ✓ |
| 2段併記を維持 | 現状の「レンダリング中 cur/total」「OCR中 done/total」を併記。逐次化で同時進行し表示が複雑化 | |

**User's choice:** 統合プログレス(推奨)

**Notes:** 上限付きバッファは Phase 4 のスレッド境界（fitz はメインスレッドのみ）と自然に整合する点を評価。

---

## ocr_scale 1.5 移行とヒント（OCR-PERF-05）

### 既存ユーザー(2.0 保存済み)の扱い

| Option | Description | Selected |
|--------|-------------|----------|
| 新規のみ1.5・既存は据え置き(推奨) | DEFAULT_SETTINGS を 1.5 に変更するのみ。保存値がある既存ユーザーはそのまま(2.0)。後方互換最大・ユーザーの明示選択を尊重 | ✓ |
| 旧既定2.0はワンタイム移行 | 保存値が旧既定2.0と一致する場合のみ1.5へ書き換え。全員が恩恵を受けるが意図的2.0と区別不可 | |
| You decide | 計画段階で判断 | |

**User's choice:** 新規のみ1.5・既存は据え置き(推奨)

### トレードオフヒントの提示場所

| Option | Description | Selected |
|--------|-------------|----------|
| 設定欄に常設説明(推奨) | llm_config の ocr_scale スライダー近傍に短い説明を常設。常に見えるので気づかれやすい | ✓ |
| ツールチップ | hover 時のみ表示。UI がすっきりするが初見で気づかれにくい。Tkinter 標準ツールチップが無く実装追加が必要 | |
| 常設説明 + コスト確認にも併記 | 設定欄常設に加え Phase5 のコスト確認ダイアログにも追記。文言が増える | |

**User's choice:** 設定欄に常設説明(推奨)

---

## Gemini パラメータ UI（OCR-API-02）

### Gemini のパラメータ UI / thinking budget の扱い

| Option | Description | Selected |
|--------|-------------|----------|
| temperatureのみ・thinking無効化(推奨) | temperature 欄のみ表示し thinkingBudget=0 で thinking を明示無効化。OCR に思考は不要・flash の既定 ON 問題を回避 | ✓ |
| effort枠を流用し thinking 欄を出す | Phase5 の effort 欄枠組みを流用し thinking budget 選択を出す。OCR では過剰・コスト増・実装複雑化 | |
| You decide | リサーチ/計画段階で Gemini API の thinking 仕様を確認して判断 | |

**User's choice:** temperatureのみ・thinking無効化(推奨)

### Gemini の推奨デフォルトモデル構成

| Option | Description | Selected |
|--------|-------------|----------|
| flash 主推奨 + pro 選択肢(推奨) | 既定 gemini-2.5-flash(コスト効率)、gemini-2.5-pro を選択肢(高精度)。STACK.md 確定。RECOMMENDED_MODELS 静的 + モデル更新ボタンで API 取得 | ✓ |
| さらに絞りたい/議論したい | デフォルトモデル選定やモデル一覧の出し方を追加議論 | |

**User's choice:** flash 主推奨 + pro 選択肢(推奨)

---

## OCR モックテストの範囲（OCR-QA-01）

### 逐次レンダリング(PERF-02)のメモリ非蓄積テスト

| Option | Description | Selected |
|--------|-------------|----------|
| 入れる(推奨) | FakeProvider で ocr_image 呼出時の保持画像数が上限(並列度連動)を超えないことを検証。成功基準2 のリグレッション網 | ✓ |
| 入れない | QA-01 はプロバイダ payload/レスポンス/スキップ判定のみ。逐次化は UAT/目視。成功基準2 の自動検証が欠ける | |
| You decide | 計画段階でテスト可能性を見て判断 | |

**User's choice:** 入れる(推奨)

### Gemini のモックテストの深さ

| Option | Description | Selected |
|--------|-------------|----------|
| 主要4点(推奨) | payload(inline_data/x-goog-api-key/thinkingBudget=0)・レスポンス解析(parts[].text)・list_models(supportedGenerationMethods フィルタ)・dual env var 解決(GEMINI→GOOGLE) | ✓ |
| 最小(payload・レスポンスのみ) | payload 構築とレスポンス解析のみ。list_models/dual env var/thinkingBudget は対象外。カバレッジが薄い | |
| You decide | Claude の既存テスト粒度に揃えて判断 | |

**User's choice:** 主要4点(推奨)

---

## Claude's Discretion

- producer-consumer のバッファ上限の余裕係数・キュー実装の具体形・キャンセル時の in-flight ページ処理
- `OCRAPIKeyError` のフォールバック env 名併記の有無
- Gemini `thinkingConfig.thinkingBudget` の正確なフィールド配置・generationConfig 構造
- バッファ上限テストの切り出し方（producer-consumer を Tk 非依存ヘルパー化するか）
- `ocr_scale` ヒント文言の正確な表現

## Deferred Ideas

- キャンセル時の in-flight ページ処理の細部 → 計画/実装段階
- Gemini の 20MB inline_data 上限超過時のガード → 通常ページでは問題なし・必要なら計画時
- TesseractProvider・PluginManager 登録フック・本格的な多言語文言整備・README/開発履歴更新 → Phase 7
- OS キーストア連携（Windows Credential Manager）→ 次マイルストーン（Out of Scope）
- `ocr_scale` の既存ユーザーへのワンタイム移行 → 今回不採用・将来再検討の余地
