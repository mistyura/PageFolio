# Phase 1: 基盤分割（肥大モジュールリファクタリング） - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-13
**Phase:** 1-基盤分割（肥大モジュールリファクタリング）
**Areas discussed:** ocr_providers の分割単位, llm_config の分割戦略, _SENSITIVE_KEYS レジストリの統合範囲, 内部 import の移行方針

---

## ocr_providers の分割単位

### Q1: パッケージの分割粒度

| Option | Description | Selected |
|--------|-------------|----------|
| 1プロバイダ=1ファイル | base.py + errors.py + lmstudio/claude/gemini/tesseract/ollama/runpod.py。各150〜330行。dialogs/ 前例と一貫 | ✓ |
| 系統別グルーピング | openai_compat.py / cloud.py / local.py の3ファイル+基盤。各500〜600行と大きめ | |

### Q2: OpenAI互換系3プロバイダの重複コードの扱い

| Option | Description | Selected |
|--------|-------------|----------|
| 機械的移動に徹する | 共通化せずそのまま移す。挙動不変が最優先・payload の微妙な差分による回帰リスク回避 | ✓ |
| 中間基底クラスを導入 | OpenAICompatProvider で重複吸収。検証コスト増 | |

### Q3: tests/test_ocr_providers.py の分割

| Option | Description | Selected |
|--------|-------------|----------|
| テストは現状維持 | 旧 import パス経由でグリーンのまま通ることが後方互換の検証になる | ✓ |
| テストもプロバイダ別に分割 | ソースと対称になるが変更量・レビュー範囲が拡大 | |

**User's choice:** すべて推奨案を採択
**Notes:** なし

---

## llm_config の分割戦略

### Q1: 単一クラス LLMConfigDialog の分割方式

| Option | Description | Selected |
|--------|-------------|----------|
| Mixin 分割 | dialogs/llm_config/ パッケージ化。PDFEditorApp の 8 Mixin 前例と一貫・機械的移動に近い | ✓ |
| ビルダー関数抽出 | 依存が明示的になるが引数配線の書き換え量が多い | |

### Q2: Mixin の分割軸

| Option | Description | Selected |
|--------|-------------|----------|
| 責務別 | dialog.py（本体+適用+共通）/ sections.py（UI構築）/ model_fetch.py（非同期取得）の3層 | ✓ |
| プロバイダ別 | プロバイダ毎に UI+fetch 同居。共通セクションとの絡みで切り出し線が複雑 | |

### Q3: Phase 2 に向けた事前の仕込み範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 純粋分割のみ | 投機的フック・空セクションは作らない（YAGNI）。Mixin 構造自体が拡張ポイント | ✓ |
| 拡張ポイントを整備 | セクション登録のリスト駆動化等。検証コスト増 | |

**User's choice:** すべて推奨案を採択
**Notes:** なし

---

## _SENSITIVE_KEYS レジストリの統合範囲

### Q1: 中央レジストリの配置場所

| Option | Description | Selected |
|--------|-------------|----------|
| 新 ocr_providers パッケージ内 | ocr_providers/registry.py。プロバイダ定義と同居し「追加時に触る場所が1箇所」 | ✓ |
| 独立モジュール | pagefolio/provider_registry.py。循環リスクは構造的にゼロだが定義と離れる | |
| settings.py 内で完結 | 変更最小だが設定モジュールに埋まり参照の置き場所として不自然 | |

### Q2: レジストリ参照への統合範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 全参照面を統合 | settings 生成 + ocr.py キー解決 + ocr_dialog 送信先確認 + llm_config 環境変数チェックの4箇所 | ✓ |
| _SENSITIVE_KEYS 生成のみ | 要件文言の最小解釈。重複マッピングが残存 | |

### Q3: レジストリの宣言方式

| Option | Description | Selected |
|--------|-------------|----------|
| 宣言的 dict 一本 | registry.py 内の静的 dict。セッションキー名も導出。一覧性が高い | ✓ |
| Provider クラス属性から収集 | 「追加=1ファイル」に忠実だが settings ガードが全 Provider import に依存 | |

**User's choice:** すべて推奨案を採択
**Notes:** Gemini の dual env var 優先順（GEMINI_API_KEY→GOOGLE_API_KEY）は不変で保持

---

## 内部 import の移行方針

### Q1: 内部コードの import パス

| Option | Description | Selected |
|--------|-------------|----------|
| 旧パスのまま維持 | from pagefolio.ocr_providers import X を継続。分割対象外ファイルに差分ゼロ・re-export 面が本番コードで常時検証 | ✓ |
| 新パスへ書き換え | サブモジュール直接 import。差分が広がり re-export 面がテスト専用化 | |

### Q2: __init__.py の re-export 範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 完全再エクスポート | private ヘルパー含む旧モジュールレベル名すべて。import 表面の完全互換 | ✓ |
| 公開シンボル + テスト使用分のみ | 名前空間はクリーンだが見落とし時に ImportError リスク | |

**User's choice:** すべて推奨案を採択
**Notes:** なし

---

## Claude's Discretion

- base.py / errors.py 間のシンボル配置の細目（parse_retry_after 等リトライヘルパーの置き場）
- registry.py の関数 API 設計（名前・シグネチャ）
- test_imports.py へ追加する後方互換テストの具体的なケース構成
- CLAUDE.md のファイル構成表の更新内容

## Deferred Ideas

- OpenAI互換プロバイダの中間基底クラス（OpenAICompatProvider）導入 — 将来の別タスク
- tests/test_ocr_providers.py のプロバイダ別分割 — 将来テストが肥大化した際に検討
