# Phase 4: プロバイダ抽象化 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 4-プロバイダ抽象化
**Areas discussed:** スレッド境界の再構成, Provider 境界の純化, 埋め込みテキストの扱い, 並列度ポリシーと後方互換

---

## 議論領域の選択（マルチセレクト）

| Option | Description | Selected |
|--------|-------------|----------|
| スレッド境界の再構成 | _worker 内の fitz レンダリングをワーカー外へ出す方針 | ✓ |
| Provider 境界の純化 | ocr_image() 入力型・埋め込み判定の所在 | ✓ |
| 埋め込みテキストの扱い | 判定基準・UI 表示 | ✓ |
| 並列度ポリシーと後方互換 | 並列度の持ち方・現行公開関数の扱い | ✓ |

**User's choice:** 4領域すべて

---

## スレッド境界の再構成

| Option | Description | Selected |
|--------|-------------|----------|
| 事前レンダリング（最小構成） | メインスレッドで全ページ after() で小分けレンダリング→ワーカーは API のみ。逐次化は Phase 6。基準3を最小変更で満たし UI フリーズも回避。（推奨） | |
| 部分逐次化を今から | レンダリングコーディネータがページ単位でレンダ→キュー→ワーカー消費。Phase 6 の土台だが変更大・スコープ超過リスク。 | |
| 任せる | 計画・実装段階で progress コールバック整合を見ながら最適な出し方を Claude に任せる。 | ✓ |

**User's choice:** 任せる
**Notes:** Claude 基本線として「事前レンダリング最小構成」を採用予定。成功基準3遵守・逐次化は Phase 6 温存。（CONTEXT D-01〜D-03）

---

## Provider 境界の純化

| Option | Description | Selected |
|--------|-------------|----------|
| base64 PNG 文字列 | 現行 call_lm_studio(b64_png) の契約踏襲。全プロバイダ base64 利用で再エンコード不要。（推奨） | ✓ |
| （生 bytes, mime_type） | 生画像 bytes と MIME を渡し base64 化は各 Provider に任せる。将来の非 PNG 対応に有利だが現状利点限定的。 | |
| 任せる | 入力型の最終決定を Claude に任せる。 | |

**User's choice:** base64 PNG 文字列
**Notes:** Provider を「画像 in→テキスト out」に純化、埋め込み判定はメインスレッド側（CONTEXT D-04, D-05）。

---

## 埋め込みテキストの扱い（判定基準）

| Option | Description | Selected |
|--------|-------------|----------|
| 文字数しきい値 | 非空白文字数がしきい値以上ならスキップ。ページ番号・薄い OCR レイヤー等の誤検出を抑制。具体値は計画段階で調整。（推奨） | ✓ |
| 非空白1文字でも | 非空白が1文字でもあればスキップ。シンプルだがスキャン PDF のゴミテキストで誤判定リスク。 | |
| 任せる | 閾値設計を Claude に任せる。 | |

**User's choice:** 文字数しきい値

## 埋め込みテキストの扱い（UI 表示）

| Option | Description | Selected |
|--------|-------------|----------|
| 明示する | 進捗・結果に「テキスト抽出（OCRスキップ）」等を明示。コスト削減効果も伝わる。（推奨） | ✓ |
| 無言で結果に混ぜる | スキップを区別せず抽出テキストを OCR 結果と同じく扱う。シンプルだが振る舞い不透明。 | |
| 任せる | 統合方法・文言詳細を Claude に任せる。 | |

**User's choice:** 明示する
**Notes:** ページ単位適用・日英スキップ通知文言を Phase 4 で最小追加（CONTEXT D-06〜D-09）。

---

## 並列度ポリシーと後方互換（並列度の持ち方）

| Option | Description | Selected |
|--------|-------------|----------|
| Provider のクラス属性 | default_concurrency / max_concurrency をクラス属性で宣言。run_parallel が読み settings 値をクランプ。基準4を自然に満たす。（推奨） | ✓ |
| 呼び出し側から渡す | 現状通り concurrency を引数で渡す。Provider は並列度を知らない。上限担保が呼び出し側に散る。 | |
| 任せる | 表現の細部を Claude に任せる。 | |

**User's choice:** Provider のクラス属性

## 並列度ポリシーと後方互換（現行公開関数の扱い）

| Option | Description | Selected |
|--------|-------------|----------|
| 呼び出し側を更新 | LM Studio 固有関数を Provider へ移し ocr_dialog.py を新 API へ更新。リファクタ目的に合致。汎用 page_to_png_b64 は残置/移設。（推奨） | |
| 薄いラッパーを残す | 既存関数名を薄い互換ラッパーで残し Provider に委譲。変更最小・低リスクだが冗長コードが残る。 | |
| 任せる | 関数ごとに残置/移設/ラッパー化を Claude が判断。 | ✓ |

**User's choice:** 任せる
**Notes:** 基本線は「呼び出し側更新のクリーンなリファクタ」。LM Studio 振る舞い後方互換は成功基準1で担保（CONTEXT D-10〜D-14）。

---

## Claude's Discretion

- スレッド境界の具体的な出し方（事前レンダリングの小分け方法・コーディネータ実装）
- 埋め込みテキスト判定しきい値の具体値
- スキップ結果の結果辞書への統合方法・表示文言の細部
- 現行公開関数の関数ごとの残置/移設/ラッパー化判断
- 例外規約（ConnectionError/TimeoutError/RuntimeError）の Provider 基底への昇格方針

## Deferred Ideas

- 逐次レンダリング化 → Phase 6（OCR-PERF-02）
- `ocr_scale` デフォルト 1.5 化 + トレードオフ UI → Phase 6（OCR-PERF-05）
- クラウド別並列度実値（Gemini=1/Claude=2）・429/5xx バックオフ → Phase 5/6（OCR-PERF-03/04）
- `ocr_provider` enum・プロバイダ選択 UI・APIキー未設定エラー・キーガード → Phase 5
- 本格的な多言語文言整備・README/開発履歴更新 → Phase 7（OCR-QA-02）
- OCR モックテストの本格整備（tests/test_ocr.py）→ Phase 6（OCR-QA-01）
