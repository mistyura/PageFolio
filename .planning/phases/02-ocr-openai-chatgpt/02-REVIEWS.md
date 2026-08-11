---
phase: 2
reviewers: [codex]
reviewed_at: 2026-08-11T01:09:18Z
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md]
reviewer_notes:
  codex:
    model: gpt-5.6-sol
    reasoning_effort: low
    repo_access: false
    repo_access_failure: "windows sandbox: CreateProcessAsUserW failed: 5 — codex 側サンドボックスがコマンドを起動できず、実コード照合ができなかった"
---

# Cross-AI Plan Review — Phase 2

> **注意（証拠等級）**: 本レビューは `REVIEWED-WITHOUT-REPO-ACCESS` マーカー付きで返されました。
> codex は実リポジトリのファイルを開けず、提示された計画・リサーチ・コード抜粋のみを根拠に
> レビューしています。したがって実コードに依存する指摘は **断定ではなく要確認事項** として扱い、
> 合議上の重みも source-grounded レビューより下げて解釈してください。

## Codex Review

REVIEWED-WITHOUT-REPO-ACCESS

実行環境で `CreateProcessAsUserW failed: 5 (アクセスが拒否されました)` が発生し、リポジトリ内ファイルを直接開けませんでした。そのため、以下は提示された計画・コード抜粋間の整合性レビューです。実コード依存の指摘は断定せず、要確認事項として扱います。

# 総評

4プランの依存順序、安全境界、APIキー非永続化、catalog の段階移行、既存リトライ基盤の再利用はよく設計されています。一方、OpenAI のモデル能力判定を `/v1/models` のモデルIDだけに依存している点、価格確認の根拠が計画化されていない点、`ProviderMeta` の型契約の内部矛盾、GUIを含む全テスト要件との不整合が残っています。特に「一覧に出たモデルが画像入力・`reasoning_effort` に対応する」という保証がなく、Phase Goalの「既存プロバイダと同等」の達成を妨げる可能性があります。

# Plan 02-01 — catalog・OpenAIProvider・build_provider

## Summary

非UIの縦スライスを先に通し、安全確認UIが完成するまで OpenAI を選択肢へ公開しない順序は適切です。ただし、D-09 checkpoint が `/v1/models` だけで vision 対応やパラメータ互換性まで確定できるように読める点は修正が必要です。

## Strengths

- `registry.py` を環境変数管理、`catalog.py` を非機密メタデータ管理に分離し、`catalog → registry` の一方向依存に限定しています。
- OpenAI をUIへ露出する前に送信先・コスト確認を完成させる依存順序は、安全境界として明確です。
- `LMStudioProvider` の既存 Chat Completions 形状を利用し、独自リトライを作らず共通エラー基盤へ載せる方針は変更面を抑えています。
- APIキーについて、入力、`build_provider`、保存除外、ログ非露出まで複数のテスト層を設けています。
- `is_reasoning_model()` をプロバイダとUIの共通判定源にする方針は、判定不一致を防ぐ有効な設計です。
- ミューテーション検証を含め、テストが単に green であるだけでなく、実際に違反を検知できることまで確認しています。

## Concerns

- **HIGH — `GET /v1/models` だけでは vision 対応を確定できません。** 計画自身が「vision対応フラグがない」と認識している一方、Task 1 の acceptance criteria は実API応答から「vision対応チャットモデル3〜6件」を確定することを要求しています。モデルIDの存在確認と画像入力能力の確認は別問題です。
- **HIGH — reasoningモデル判定の根拠が不足しています。** `^o\d` などの命名規則だけでは、将来または現行の `gpt-*` reasoning対応モデルを取りこぼす可能性があります。Task 1でモデル一覧を見るだけでは、`temperature` と `reasoning_effort` の対応能力は判定できません。
- **MEDIUM — `ProviderMeta.display_name_key` の型契約が矛盾しています。** artifactsでは8フィールドを `str` / `bool` / `str | None` としていますが、Task 2では `off` と `ollama` の `display_name_key=None` を要求しています。どのフィールドがnullableかを明示しないと、実装とテストで解釈が割れます。
- **MEDIUM — catalog の「環境変数名」一元化の定義が曖昧です。** V190-CAT-01は環境変数も単一情報源から解決するとしていますが、実際には `registry.py` がprimaryでcatalogは委譲または非公開です。設計自体は妥当ですが、要件の「1箇所」が catalog 単独を意味しないことを明文化すべきです。
- **MEDIUM — `list_models()` の暫定実装が公開されます。** Plan 01完了からPlan 03完了まで静的一覧だけを返す中間状態になります。UI非公開なので直接的な危険は低いものの、package-level APIから利用可能です。
- **LOW — 構造アサーションが実装詳細へ強く結合しています。** `inspect.getsource()` による文字列禁止はコメントや安全なリファクタでも壊れやすく、挙動テストの補助に留めるべきです。

## Suggestions

- D-09を次の二段階に分けてください。

  1. `/v1/models`：モデルIDの存在確認
  2. OpenAI公式モデル仕様または最小画像リクエスト：vision入力、`max_completion_tokens`、`temperature`、`reasoning_effort` の対応確認

- `ProviderMeta` の各フィールド型を表で固定し、少なくとも `display_name_key`, `model_setting_key`, `default_model`, `host`, `api_key_missing_lang_key` を `str | None` と明記してください。
- `is_reasoning_model()` のテストに、o-seriesだけでなく、公式にreasoning対応と確認した `gpt-*` モデルも含めてください。
- endpoint host一致テストをPlan 02へ持ち越さず、`catalog.py` と `OpenAIProvider` が同時に追加されるPlan 01で導入すると安全です。

## Risk Assessment

**HIGH**。基盤構造は堅実ですが、モデル能力判定の前提が外れると、初回OCRが失敗するだけでなく、UI表示と送信パラメータの双方が誤るためです。

# Plan 02-02 — OCR・バッチOCRの安全境界

## Summary

単発OCRとバッチOCRを独立実装のまま維持し、共有するのをcatalogデータだけに限定する判断は既存設計と整合しています。最大の不足は、コスト確認に使用するOpenAI単価の決定経路が計画されていない点です。

## Strengths

- host、表示名、クラウド判定、APIキー欠落メッセージの重複箇所を具体的に列挙し、段階的に移行しています。
- catalog未登録プラグインに対する `isinstance` フォールバックを維持し、外部送信確認が消えない安全側の判断を採っています。
- 単発とバッチの対称テスト、価格表一致テスト、hostと実endpointの一致テストを用意しています。
- OpenAIを選択可能にするPlan 03より前に、安全確認経路を完成させています。
- host改変とLANGキー固定化の2種類のミューテーションテストは、catalog移行後の検知力確認として有効です。

## Concerns

- **HIGH — コスト表示の単価ソースがありません。** Plan 01のcheckpointはモデルIDを確定しますが、価格情報の取得・確認は含みません。Plan 02では「公表値」としか書かれておらず、URL、参照日、単位、cached input、モデル別価格差の扱いが未定です。誤った概算は外部送信への同意品質を損ないます。
- **HIGH — vision非対応モデルもコスト確認を通過して選択される可能性があります。** Plan 03のフィルタが非チャットモデルを除くだけなら、テキスト専用チャットモデルが残り得ます。
- **MEDIUM — hostが空の場合の代替表示が曖昧です。** 未登録のクラウド継承プラグインは `isinstance` でクラウド判定される一方、catalog未登録なので `host_for()` は空になります。「プロバイダ表示名を出す」だけでは、実際の送信先を明示する安全契約を満たしません。
- **MEDIUM — `_TEXT_CAPABLE_PROVIDERS` はcatalog外の新たなプロバイダ集合です。** V190-CAT-01の「変更面が1箇所」との境界を明確にしないと、OpenAI追加時の追記漏れ問題が別の集合で残ります。
- **LOW — 「既存テストが無改修でgreen」と、新規catalog仕様への期待値変更が混在しています。** 既存リテラルへのpatchを利用するテストがある場合、無改修greenはむしろpatch断絶を見逃している可能性があります。

## Suggestions

- OpenAI価格確認専用のcheckpointまたは自動化された根拠記録を追加してください。最低限、モデルID、入力/出力単価、単位、通貨、参照URL、参照日をSUMMARYへ残すべきです。
- catalog未登録のクラウド継承プラグインについて、hostを取得できない場合は送信を中止するか、「送信先不明」と明示して追加確認する契約にしてください。
- 単発・バッチ双方で、確認ダイアログの「いいえ」により `build_provider` やHTTP呼び出しへ到達しないことをテストしてください。
- `_TEXT_CAPABLE_PROVIDERS` がCAT要件の対象外である理由を明記するか、`ProviderMeta` に能力フラグとして含めるべきか再検討してください。ただし追加する場合はD-01のlocked scope変更として扱う必要があります。

## Risk Assessment

**HIGH**。安全確認経路そのものは強いものの、表示コストと選択モデル能力の信頼性が未確定で、同意内容が正確でない可能性があります。

# Plan 02-03 — LLM設定UI・モデル一覧

## Summary

UI公開を安全境界完成後に行う順序、APIキーをセッションメモリに限定する配線、既存非同期モデル取得基盤の再利用は適切です。一方、負のキーワードだけによるモデルフィルタは、OCRで利用可能なモデル一覧を保証するには弱すぎます。

## Strengths

- `provider_combo` とフォールバック候補の双方をcatalog由来にし、一覧リテラル移行を完走させています。
- APIキーを `llm_settings` に入れず `_session_api_keys` のみに同期する契約が明確です。
- `_fetch_models_async` を再利用し、二重起動・破棄後callbackの既存安全策を維持しています。
- フィルタをTk・HTTP非依存の純関数に切り出しており、テストしやすい構成です。
- OpenAIセクションを既存ClaudeセクションのUIパターンに合わせ、テーマ・フォント規約を明示しています。

## Concerns

- **HIGH — 除外型フィルタではOCR利用可能性を保証できません。** `embedding`, `tts`, `whisper` 等を除いても、テキスト専用、旧completion、fine-tuned、権限外、画像入力非対応モデルが残る可能性があります。
- **HIGH — 取得失敗時の静的フォールバック経路が二重です。** `list_models()` はHTTP失敗を例外化し、UIの `_on_error` が静的一覧へ戻します。一方、D-08は「取得失敗と0件を同一経路へ合流」としています。最終UI挙動は同じでも、実装経路は同一ではありません。
- **MEDIUM — `image` を除外マーカーに含めるのは過剰除外の可能性があります。** 将来のvision対応モデルIDに `image` が含まれた場合、目的のモデルまで除外します。
- **MEDIUM — モデルリスト取得のエラー処理がOCR実行時と非対称です。** `_raise_mapped_http_error` を使わず単純な `RuntimeError` にするため、429や`Retry-After`がモデル一覧更新では活用されません。要件OAI-13がOCRだけを対象とするなら許容できますが、明記が必要です。
- **MEDIUM — `temperature_frame` の表示制御をOpenAIモデル選択が変更します。** 別プロバイダへ戻ったときに既存各分岐が正しく再表示するか、全プロバイダ往復テストが必要です。
- **LOW — LANGキー追加をTask 2とTask 3の同一コミットへまとめる指示は、「1タスクずつ完了」と緊張します。** 中間状態で未使用キー検査が落ちるなら、Taskの境界自体を組み替えた方が明快です。

## Suggestions

- モデル一覧は次のどちらかにしてください。

  - 公式に画像入力対応が確認されたfamilyの許可リスト
  - API一覧を候補表示しつつ、未検証モデルへ「画像対応未確認」の表示を付け、既定値には使わない

- `filter_chat_models()` を `filter_ocr_capable_models()` と誤解させない命名にするか、能力保証をしないことをdocstringで明記してください。
- HTTP失敗と0件を本当に同一経路にするなら、`list_models()` 自体が両方で `RECOMMENDED_MODELS` を返すよう統一してください。例外をUI表示したいなら、D-08の表現を修正してください。
- provider切替について `openai → claude → gemini → openai` の往復テストを追加し、`temperature_frame`, `effort_frame`, `openai_section_frame` の状態を確認してください。
- `_fetch_models_async` の完了順序が古い結果で新しいselectionを上書きしないか、既存generation guardの有無を実コード確認対象にしてください。

## Risk Assessment

**HIGH**。APIキー管理と非同期UIは堅実ですが、ユーザーへ提示するモデル一覧が実際にOCR可能とは限らず、主要経路の成功率へ直結します。

# Plan 02-04 — 固有設定・フォールバック・実機確認

## Summary

残りの固有設定、フォールバック、ドキュメント、人手確認をフェーズ末へ集約する構成は分かりやすいです。ただし、reasoning effortの自由入力、無効値の無言破棄、実機フォールバック手順の再現性に改善余地があります。

## Strengths

- OpenAIのeffortをClaudeの `ocr_effort` から分離し、専用キー・専用ウィジェットにしています。
- UI入力検証に加えてHTTPヘッダ生成直前でも制御文字を拒否する多層防御は適切です。
- org/projectが空ならヘッダ非付与という要件を、単体・通しテスト双方で確認しています。
- フォールバック純ロジックを変更せず、既存の候補リストへの追加だけで対応する方針は変更面を抑えています。
- 実API、Tkモーダル、キー非永続化、バッチ、フォールバックをhuman-verifyへ明示的に落としています。
- APIキーをSUMMARYやスクリーンショットへ記録しない安全配慮があります。

## Concerns

- **HIGH — reasoning effortを自由入力でAPIへ送る方針は「非互換でエラーにならない」というフェーズ成功条件と緊張します。** 未知値をAPIの400へ委ねる設計は、対応モデルのみ有効化という要件を十分に満たさない可能性があります。
- **HIGH — フォールバック実機手順が成立しない可能性があります。** 無効なClaudeキーによる401が既存フォールバック対象でなければ、OpenAI候補へ到達しません。フォールバック発火条件を実コードで確認してから、確実に対象となる失敗方法を指定する必要があります。
- **MEDIUM — `_sanitize_openai_id()` が不正入力を空文字へ黙って変換します。** ユーザーは入力が保存されたと思うのに、実際にはヘッダが送られません。設定Apply時に明示エラーまたは警告を出す方が安全です。
- **MEDIUM — org/projectの許可文字制限が仕様根拠なしに狭い可能性があります。** 制御文字拒否は必要ですが、英数字・ハイフン・アンダースコアだけという制限は将来の正当なIDを弾く可能性があります。
- **MEDIUM — `openai_reasoning_effort` に `_sanitize_openai_id()` を流用するのは責務が不明瞭です。** ヘッダID用の検証とAPI列挙値用の検証は意味が異なります。
- **MEDIUM — human-verifyが大きすぎます。** APIキー再入力、アプリ再起動、バッチ2ファイル、フォールバック障害注入までを1 checkpointにまとめると、失敗時の原因切り分けが難しくなります。
- **LOW — acceptance criteriaのPython例に `.\_headers()` という不正なエスケープがあります。** そのまま実行すると構文エラーになる可能性があります。`._headers()` に修正が必要です。
- **LOW — `grep` コマンドはWindows環境で利用不能な可能性があります。** プロジェクトの実行環境に合わせ `rg` または `Select-String` に統一した方がよいです。

## Suggestions

- reasoning effortはモデル能力表を用意し、モデルごとの許容値だけをreadonly comboboxへ出すか、最低でも不正値を送信前に明示エラーにしてください。
- `_sanitize_openai_id()` は「不正なら空」ではなく、Applyを中止して具体的な入力エラーを表示する契約へ変更してください。provider側の制御文字除去は多層防御として残せます。
- フォールバックhuman-verify前に、既存コードの「どの例外がフォールバック対象か」を確認し、モックまたは確実なretryable failureでシナリオを作ってください。
- human-verifyを以下へ分割すると切り分けやすくなります。

  1. 設定UI・モデル一覧・キー非永続化
  2. 単発OCR・バッチOCR・確認ダイアログ
  3. フォールバック再確認

- 手順中のAPIキーについて、画面録画・ログ・SUMMARYへ値を残さない注意をcheckpoint本文にも明記してください。
- `._headers()` のコマンド誤記を修正し、Windows互換の検証コマンドへ揃えてください。

## Risk Assessment

**MEDIUM-HIGH**。主なセキュリティ対策は良好ですが、パラメータ互換性とフォールバック実機手順が不確実で、ユーザー入力が無言で破棄されるUXリスクがあります。

# 横断的な改善提案

- **HIGH — OpenAI能力マトリクスをPlan 01の成果物に追加する。**

  | Model | Vision input | `max_completion_tokens` | `temperature` | `reasoning_effort` | effort values | Price source |
  |---|---|---|---|---|---|---|

  これを公式資料または最小実API検証で埋め、Plan 02〜04が同じ表を消費する構造にすると、現在分散している推測を排除できます。

- **HIGH — 全テストゲートの扱いを明確化する。** プロジェクト指示はコミット前の `pytest` 完走を要求していますが、各プランは `--ignore=tests/test_ocr_pipeline.py` と「失敗件数が同数以下」を許容しています。Phase 3へ持ち越すなら、Phase 2の各コミットを例外扱いする明示承認、既知失敗の正確なbaseline、Phase 3で必ずゼロにするblocking gateが必要です。
- **MEDIUM — 必須構文チェックが計画にありません。** プロジェクトチェックリストの `ast.parse` 確認も各plan verificationまたはphase gateへ追加してください。
- **MEDIUM — 価格表の二重定義を維持するなら、モデル単価・単位・参照日の一致テストを追加する。** 現状は辞書同士の一致しか検証せず、「同じ誤値」を防げません。
- **MEDIUM — catalog移行完了テストを追加する。** 既知host、手書きクラウド集合、表示名dict、APIキー欠落dictが対象ファイルに残っていないことを、限定的なASTまたは`rg`検査でphase gateに置くとCAT-01の完了判定が明確になります。
- **LOW — 4プランとも規模が大きいです。** 各planが50k〜65k tokensで、特にPlan 02は本番2ファイル、LANG、価格、テスト、ミューテーションを抱えています。コミット単位を「単発OCR移行」「バッチ移行」「安全境界テスト」に分けると、D-03の段階移行方針とより一致します。

# 最終リスク評価

**総合リスク: HIGH**

安全性、秘密管理、依存順序、既存基盤の再利用は高品質です。しかし、OpenAIモデルの存在確認を能力確認として扱っている点と、コスト表示の根拠が計画化されていない点が主要なブロッカーです。実装開始前に少なくとも次の3点を修正することを推奨します。

1. vision・reasoning・temperature・effort値域を確認するモデル能力マトリクスを追加する。
2. OpenAI価格の一次ソース・参照日・単位をPlan 02へ追加する。
3. `ProviderMeta` のnullable型、全テスト例外運用、Plan 04の実機フォールバック発火条件を明確化する。

---

## Consensus Summary

単一レビュアー（codex）のみのため合議は成立しません。以下は本レビュー単独の所見を、
`repo_access: false` を織り込んで整理したものです。**採否の前に実コード照合が必須**の項目には
🔍 を付けています。

### Strengths（レビュアーが評価した点）

- 依存順序の設計: 安全確認 UI（02-02）が完成するまで OpenAI を UI へ露出しない（02-03）という
  wave 構成が、外部送信の安全境界として一貫している。
- 秘密情報の扱い: API キーを `llm_settings` に載せず `_session_api_keys` のみへ同期する契約と、
  入力・`build_provider`・保存除外・ログ非露出の多層テストが計画されている。
- 変更面の抑制: 既存 `LMStudioProvider` の Chat Completions 形状と `ocr_providers/errors.py` の
  リトライ基盤を再利用し、独自リトライを新設していない。
- 検証の質: 単に green であることではなく、ミューテーションで検知力そのものを確認している。

### Concerns（優先度順）

**HIGH**

1. **モデル "存在確認" を "能力確認" として扱っている。** `GET /v1/models` はモデル ID の存在しか
   返さず、vision 入力・`reasoning_effort` 対応・`temperature` 可否は判定できない。にもかかわらず
   02-01 Task 1 の acceptance criteria は実 API 応答から「vision 対応チャットモデル 3〜6 件」を
   確定することを要求している。→ 能力マトリクス（Model × vision / `max_completion_tokens` /
   `temperature` / `reasoning_effort` / effort 値域 / 価格ソース）を 02-01 の成果物へ追加し、
   02-02〜02-04 が同一の表を参照する構造にする。
2. **コスト確認の単価ソースが未計画。** 02-02 は「公表値」としか書かれておらず、URL・参照日・単位・
   cached input・モデル別価格差の扱いが未定。誤った概算は「外部送信への同意」の品質を損なう。
3. **除外型フィルタでは OCR 利用可能性を保証できない**（02-03）。`embedding` / `tts` / `whisper` を
   除いても、テキスト専用・旧 completion・fine-tuned・権限外モデルが残り得る。許可リスト方式か、
   未検証モデルへの「画像対応未確認」表示のいずれかへ。
4. **reasoning effort の自由入力**（02-04）は「パラメータ非互換でエラーにならない」という Phase
   成功条件と矛盾する。未知値を API の 400 に委ねる設計は要件 V190-OAI-09 を満たさない可能性。
5. 🔍 **フォールバックの実機検証手順が成立しない可能性**（02-04）。無効な Claude キーによる 401 が
   既存フォールバック対象でなければ OpenAI 候補へ到達しない。→ 実コードで「どの例外が
   フォールバック対象か」を確認してから手順を確定する。
6. **全テストゲートの扱いが不整合。** CLAUDE.md はコミット前 `pytest` 完走を要求しているが、各
   プランは `--ignore=tests/test_ocr_pipeline.py` と「失敗件数が同数以下」を許容している。
   Phase 3 へ持ち越すなら、Phase 2 各コミットの例外扱いを明示承認し、既知失敗の正確な baseline と
   Phase 3 での blocking gate を定義する必要がある。

**MEDIUM**

7. `ProviderMeta` の nullable 契約が矛盾（artifacts は 8 フィールドを `str`/`bool`/`str | None`、
   Task 2 は `off`/`ollama` の `display_name_key=None` を要求）。フィールド単位で型表を固定する。
8. catalog 未登録のクラウド継承プラグインは `isinstance` でクラウド判定されるのに `host_for()` が
   空になり、「送信先を明示する」安全契約を満たさない。送信中止か「送信先不明」の追加確認へ。
9. `_TEXT_CAPABLE_PROVIDERS` が catalog 外の新たなプロバイダ集合になっており、V190-CAT-01 の
   「変更面が 1 箇所」の境界が曖昧。対象外とする理由を明記するか `ProviderMeta` へ能力フラグ化
   （後者は D-01 の locked scope 変更として扱う必要あり）。
10. モデル一覧取得のエラー処理が OCR 実行時と非対称（`_raise_mapped_http_error` 不使用のため
    429/`Retry-After` が効かない）。V190-OAI-13 が OCR のみ対象なら、その旨を明記する。
11. 取得失敗時のフォールバック経路が二重（`list_models()` が例外化 → UI `_on_error` が静的一覧）で、
    D-08 の「取得失敗と 0 件を同一経路へ合流」と実装経路が一致しない。
12. `_sanitize_openai_id()` が不正入力を**無言で空文字化**する。Apply 時に明示エラーへ。
    また ヘッダ ID 用検証を `openai_reasoning_effort`（API 列挙値）へ流用するのは責務が不明瞭。
13. `temperature_frame` の表示制御を OpenAI モデル選択が変更するため、
    `openai → claude → gemini → openai` の往復テストが必要。
14. human-verify（02-04）が 1 checkpoint に集中しすぎ。①設定 UI・モデル一覧・キー非永続化 /
    ②単発・バッチ OCR と確認ダイアログ / ③フォールバック再確認 の 3 分割を推奨。
15. `ast.parse` 構文チェック（CLAUDE.md チェックリスト項目）が各 plan の verification に無い。
16. 価格表の二重定義は「辞書同士の一致」しか検証しておらず、**同じ誤値**を防げない。

**LOW**

17. `inspect.getsource()` による構造アサーションは実装詳細への結合が強く壊れやすい。
18. 02-04 acceptance criteria の Python 例に `.\_headers()` という不正エスケープ（`._headers()` へ）。
19. 検証コマンドの `grep` は Windows 環境で不可の可能性。`rg` / `Select-String` へ統一。
20. 各 plan が 50k〜65k tokens と大きい。特に 02-02 はコミット単位を
    「単発 OCR 移行 / バッチ移行 / 安全境界テスト」へ分割すると D-03 の段階移行方針と整合する。

### Divergent Views

単一レビュアーのため該当なし。複数視点が必要なら `--gemini` / `--claude` を追加して再実行する。

### Overall Risk

**HIGH**（codex 評価）。安全境界・秘密管理・依存順序・既存基盤の再利用は高品質だが、
「モデル存在確認を能力確認として扱っている」点と「コスト表示の根拠が未計画」の 2 点が
実装開始前のブロッカーとされている。
