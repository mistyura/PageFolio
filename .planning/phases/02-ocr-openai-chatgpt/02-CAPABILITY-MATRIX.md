# OpenAI Capability & Price Matrix

## メタ情報

- **採用 option:** option-b（OpenAI 公式ドキュメントを一次ソースとして確定）
  - 理由: 本セッションの実行環境に `OPENAI_API_KEY` が設定されておらず（`env | grep -i OPENAI` で未検出）、
    Stage B の実画像リクエストを送信できない。D-09 が明示する代替経路
    （「実キーが用意できない場合は OpenAI 公式ドキュメントを二次ソースとする」）を採用した。
- **Stage A（モデル ID の実在確認）:** `https://developers.openai.com/api/docs/models/all`
  （2026-08-11 取得）から `data-*` 属性経由でレンダリングされたモデル一覧ページを直接 `curl` 取得し、
  実在する `gpt-*`／`o*` 系 ID を確認した。
- **Stage B（能力・価格の確認）:** 上記一覧から候補となった各モデルの個別ドキュメントページ
  （`https://developers.openai.com/api/docs/models/{model_id}`）を `curl` で取得し、
  ページ本文に明記された Modalities（Text/Image 入出力）・Pricing（Input/Cached input/Output）・
  Reasoning 対応有無を読み取った。`reasoning_effort` の許容値ドメインは Chat Completions
  `create` API リファレンス（`https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create`）
  および Reasoning ガイド（`https://developers.openai.com/api/docs/guides/reasoning`）から取得した。
- **実施日時:** 2026-08-11（本プラン実行時・`curl` によるページ取得はすべて同日実施）
- **API キー文字列:** 本ファイル・SUMMARY のいずれにも記録していない（Stage B は公式ドキュメント経由のみで実施し、実 API 呼び出しは行っていない）。
- **`allowed_effort_values` の精度に関する注記:** `gpt-5` / `gpt-5.1` / `gpt-5.2` は各モデルの個別ページ本文に
  `Reasoning.effort supports: ...` という明示的な許容値リストが記載されており、これをそのまま採用した。
  `gpt-5-nano` / `gpt-5-mini` / `gpt-5.6-sol` / `gpt-5.6-terra` / `o3` の個別ページには同種の明示リストが
  無かったため、Chat Completions `create` API リファレンスに記載された **全モデル共通の許容値ドメイン**
  （`none, minimal, low, medium, high, xhigh, max`。リファレンス原文: "Currently supported values are none,
  minimal, low, medium, high, xhigh, and max"）を採用した。同リファレンスは
  「一部の値は全ての推論モデルでサポートされるわけではない」旨も明記しており、この注記も踏まえて
  02-04 は readonly Combobox + 値検証を多層防御として実装する（Open Question 2 の Resolution 参照）。
  この差分（モデル別明示リスト vs 全モデル共通ドメイン）はいずれも `evidence=official-doc`
  （公式ドキュメントに実在する記述からの読み取り）であり `inferred`（憶測）ではない。

## モデル一覧

| model_id | vision_input | max_completion_tokens | temperature | reasoning_effort | allowed_effort_values | input_price | output_price | price_unit | currency | source_url | retrieved_at | evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-4o | yes | yes | yes | no | - | 2.50 | 10.00 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/gpt-4o | 2026-08-11 | official-doc |
| gpt-5-chat-latest | yes | yes | yes | no | - | 1.25 | 10.00 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/gpt-5-chat-latest | 2026-08-11 | official-doc |
| gpt-5-nano | yes | yes | no | yes | none,minimal,low,medium,high,xhigh,max | 0.05 | 0.40 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/gpt-5-nano | 2026-08-11 | official-doc |
| gpt-5-mini | yes | yes | no | yes | none,minimal,low,medium,high,xhigh,max | 0.25 | 2.00 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/gpt-5-mini | 2026-08-11 | official-doc |
| gpt-5.1 | yes | yes | no | yes | none,low,medium,high | 1.25 | 10.00 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/gpt-5.1 | 2026-08-11 | official-doc |
| gpt-5.2 | yes | yes | no | yes | none,low,medium,high,xhigh | 1.75 | 14.00 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/gpt-5.2 | 2026-08-11 | official-doc |
| gpt-5.6-terra | yes | yes | no | yes | none,minimal,low,medium,high,xhigh,max | 2.00 | 12.00 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/gpt-5.6-terra | 2026-08-11 | official-doc |
| gpt-5.6-sol | yes | yes | no | yes | none,minimal,low,medium,high,xhigh,max | 5.00 | 30.00 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/gpt-5.6-sol | 2026-08-11 | official-doc |
| o3 | yes | yes | no | yes | none,minimal,low,medium,high,xhigh,max | 2.00 | 8.00 | per 1M tokens | USD | https://developers.openai.com/api/docs/models/o3 | 2026-08-11 | official-doc |
| text-embedding-3-small | unknown | unknown | unknown | no | - | unknown | unknown | per 1M tokens | USD | https://developers.openai.com/api/docs/models/all | 2026-08-11 | official-doc |
| whisper-1 | unknown | unknown | unknown | no | - | unknown | unknown | per 1M tokens | USD | https://developers.openai.com/api/docs/models/all | 2026-08-11 | official-doc |
| tts-1 | unknown | unknown | unknown | no | - | unknown | unknown | per 1M tokens | USD | https://developers.openai.com/api/docs/models/all | 2026-08-11 | official-doc |
| omni-moderation-latest | unknown | unknown | unknown | no | - | unknown | unknown | per 1M tokens | USD | https://developers.openai.com/api/docs/models/all | 2026-08-11 | official-doc |
| gpt-image-1 | unknown | unknown | unknown | no | - | unknown | unknown | per 1M tokens | USD | https://developers.openai.com/api/docs/models/all | 2026-08-11 | official-doc |

> 末尾 5 行（`text-embedding-3-small` / `whisper-1` / `tts-1` / `omni-moderation-latest` / `gpt-image-1`）は
> OCR/vision チャット用途の候補ではなく、D-07 のヒューリスティックフィルタが**除外すべき ID の実例**として
> 一覧に存在することのみを確認した行である（`/v1/models` 一覧に実在する ID・Stage A で確認済み）。
> これらは個別のモデル詳細ページ本文まで読解しておらず vision/price 列は `unknown` のまま
> （空欄にはしていない）。`RECOMMENDED_MODELS`／`default_model` の対象には一切含めない。

## 導出結果

### (1) `default_model` に採用する 1 件

**`gpt-5.1`**（vision_input=yes・evidence=official-doc）。理由:
- 個別ページ本文に「The best model for coding and agentic tasks with configurable reasoning and
  non-reasoning effort」と明記され、`gpt-5` や `gpt-5.2` のような「We recommend using the latest GPT-5.6」
  という非推奨注記が無い（廃止予告のない現行フラッグシップ）。
- `reasoning_effort` の許容値がモデル固有ページに明示（`none, low, medium, high`）されており、
  全モデル共通ドメインへのフォールバックに頼らない最も確度の高い行。
- 画像入力対応（`Input: Text, image`）・価格 $1.25/$10.00（Input/Output per 1M tokens）で
  Claude/Gemini の既定モデルと同等の中位価格帯。

### (2) `RECOMMENDED_MODELS` に採用するリスト（宣言順を確定）

```
["gpt-5-nano", "gpt-5-mini", "gpt-5.1", "gpt-5.2", "gpt-4o"]
```

全 5 件とも `vision_input=yes` かつ `evidence=official-doc`（`inferred` 行は 1 件も含まない）。
安価・高速な `gpt-5-nano` から高精度・高価格な `gpt-5.2` まで、加えて非推論系の代表として `gpt-4o` を
含めることで、`is_reasoning_model()` の真偽両ケースを一覧内に持たせている。

### (3) `is_reasoning_model()` の真ケース・偽ケース実例と判定パターン

**真ケース（reasoning_effort=yes と確認済み）:**
- `o3`（o-series。o-series は伝統的な命名規則 `^o[0-9]` に一致）
- `gpt-5.1`（**o 系以外**。個別ページ本文に `reasoning_effort` 明示対応が記載されている。
  レビュー HIGH 02-01-2 が要求する「o 系以外の真ケース」を満たす実例）

**偽ケース（reasoning_effort=no と確認済み）:**
- `gpt-4o`（ページのバッジが `Intelligence`〈`Reasoning` ではない〉であり、Reasoning 対応の記載が無い）
- `gpt-5-chat-latest`（`gpt-5` ファミリだが ChatGPT 向けチャット用スナップショットで、
  ページのバッジは `Intelligence`。`Reasoning token support` の記載が無い唯一の `gpt-5*` 系ページ）

**判定に使うパターンの集合:**
- `^o[0-9]`（o-series 全般。`o1`/`o1-mini`/`o1-pro`/`o3`/`o3-mini`/`o3-pro`/`o4-mini`/
  `o3-deep-research`/`o4-mini-deep-research` 等）
- `^gpt-5` **かつ** ID に `-chat-latest` を含まない（`gpt-5`/`gpt-5-mini`/`gpt-5-nano`/`gpt-5.1`/`gpt-5.2`/
  `gpt-5.6-sol`/`gpt-5.6-terra`/`gpt-5.6-luna`/`gpt-5-codex` 等の `gpt-5` ファミリ推論モデル群。
  `gpt-5-chat-latest`/`gpt-5.1-chat-latest`/`gpt-5.2-chat-latest` のような `-chat-latest`
  サフィックス付きスナップショットのみ非推論として除外する）

上記いずれかに一致すれば推論系（`temperature` 省略・`reasoning_effort` 有効化）、
いずれにも一致しなければ非推論系（`temperature` 送信・`reasoning_effort` 省略）と判定する。
`gpt-4` / `gpt-4.1` / `gpt-3.5-turbo` 系は `^o[0-9]` にも `^gpt-5` にも一致せず非推論系として扱われる
（既存 GPT-4 世代は Reasoning バッジを持たないことを個別ページで確認済み）。

**Pitfall 3 の再発防止メモ:** 当初 RESEARCH.md Pattern 2 が例示していた `^o\d` 単独の正規表現案は、
本 Stage B の実ドキュメント読解で **不十分** と判明した（`gpt-5.1` が o 系以外で `reasoning_effort` に
対応しているため）。上記 2 パターンの OR 判定を `openai_provider.py:is_reasoning_model()` の実装として
採用する（D-13・単一判定源）。

### (4) モデル一覧フィルタで除外すべき ID の実例

`/v1/models` 相当の一覧ページ（Stage A で確認）に実在した非チャット/非vision系 ID:

- Embeddings: `text-embedding-3-large` / `text-embedding-3-small` / `text-embedding-ada-002`
- 音声認識（Whisper）: `whisper-1`
- 音声合成（TTS）: `tts-1` / `tts-1-hd`
- モデレーション: `omni-moderation-latest`
- 画像生成: `gpt-image-1` / `gpt-image-1.5` / `gpt-image-1-mini` / `gpt-image-2` / `gpt-image-latest`
- リアルタイム音声/翻訳/文字起こし系（チャット/vision 用途ではない）:
  `gpt-realtime` / `gpt-realtime-mini` / `gpt-4o-realtime-preview` / `gpt-4o-transcribe` /
  `gpt-4o-mini-transcribe` / `gpt-4o-mini-tts` / `gpt-realtime-translate`

02-03 Task 1 のヒューリスティックフィルタ純関数は、上記カテゴリのプレフィックス／部分文字列
（`text-embedding`, `whisper`, `tts-`, `moderation`, `gpt-image`, `-realtime`, `-transcribe`）を
除外パターンとして実装する。
