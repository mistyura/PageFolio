# Feature Research — v1.9.0 新規能力（安全性是正 + OpenAI プロバイダ追加）

**Domain:** Windows デスクトップ PDF エディタ + OCR/LLM 連携（PageFolio）
**Researched:** 2026-08-10
**Confidence:** MEDIUM（OpenAI API 仕様は公式ドキュメント系ページを複数クエリでクロスチェック済み＝MEDIUM。他社 PDF ツールの保存挙動の一次情報は限定的で LOW。デスクトップアプリの原子的保存・設定ダイアログ契約は業界一般則としては十分裏付けあり＝MEDIUM）

このファイルは v1.9.0 の「新規追加分」（既存機能レビュー由来の 8 課題 + OpenAI(ChatGPT) プロバイダのフル実装）に対象を絞った機能ランドスケープである。既存の PDF ページ操作・6 プロバイダ OCR 基盤は再調査していない（`.planning/research/` の過去マイルストーン分析を参照）。

---

## Feature Landscape

### Table Stakes（既存プロバイダと揃えるべき最低限）

#### A. OpenAI(ChatGPT) OCR プロバイダの table stakes

Claude/Gemini プロバイダ（`pagefolio/ocr_providers/claude.py`・`gemini.py`）が既に確立しているパターンに、OpenAI も完全に揃えるべき項目。

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| セッション限定 APIキー入力欄（マスク・`OPENAI_API_KEY` フォールバック） | Claude/Gemini/RunPod と同じ導線がないと「片手落ちのプロバイダ」に見える | LOW | `registry.py` の `PROVIDER_ENV_KEYS` に `"openai": ("OPENAI_API_KEY",)` を追加するだけで `_SENSITIVE_KEYS` 波及も自動化される（V180-ROBUST-02 の一元化ポイント） |
| モデル一覧の動的取得＋未キー時の静的 `RECOMMENDED_MODELS` フォールバック | Claude/Gemini は API 未接続でも選べる（D-08 方針） | MEDIUM | OpenAI `GET /v1/models` は `id`/`object`/`created`/`owned_by` のみを返し、Claude の `capabilities.image_input.supported` のような vision 対応フラグが**ない**。ID の静的プレフィックス判定（例: `gpt-4o`/`gpt-5*`/`o3`/`o4-mini` 系）か固定 `RECOMMENDED_MODELS` に頼る設計が必須（Claude/Gemini より一段複雑） |
| 送信先確認ダイアログ（`api.openai.com` を明示） | 既存の「外部送信を明示する」安全境界（V180-D-02）を維持する必要 | LOW | 既存の送信先確認パターン（`ocr_dialog.py` 側）を踏襲 |
| コスト確認ダイアログ（クラウド送信前に毎回表示） | Claude/Gemini/RunPod と同じく課金発生を警告する必要（D-10/D-11） | MEDIUM | 既存 `_estimate_cost()`（`ocr_dialog.py:928`）はページ数 × 固定 1600 vision トークンという粗い近似（D-10「精度より警告の存在が重要」）。OpenAI は `detail` レベルでトークン数が大きく変動する（low=固定85トークン、high=タイル数依存で1024×1024相当は約765トークン）ため、既存の粗い近似をそのまま流用するか、detail を織り込んだ概算にするかの設計判断が要る |
| バッチOCR（`BatchOCRDialog`）でのクラウド判定・進捗・失敗分離への組み込み | 既存3クラウド系（Claude/Gemini/RunPod）と同格の実行経路が期待される | MEDIUM | `_is_cloud_provider()`（`ocr_dialog.py:905`）が `("claude", "gemini", "runpod")` を**ハードコード**している。OpenAI 追加時にこの判定漏れが起きやすい＝V190-REV-08（プロバイダメタデータ一元化）に強く依存 |
| フォールバック候補への組み込み（明示設定型のみ・自動切替なし） | V180-D-02 の「自動ベンダー切替は不採用」方針を維持 | LOW | 一覧 UI（`llm_config/sections.py`）にプロバイダ名を追加するだけ。ロジック変更は不要 |
| `urllib` 直叩き実装（新規 pip 依存ゼロ） | V14-D-01 方針。全プロバイダ urllib 統一 | LOW-MEDIUM | 実装方式（Chat Completions 相当のステートレス呼び出し）を選べば Claude/Gemini とほぼ同型。後述のとおり Responses API のフル機能は不要 |
| 途切れ検出（`ocr_image_ex` の truncated フラグ） | Claude(`stop_reason`)/Gemini(`finishReason`) と同じ「途切れても部分テキストは破棄しない」方針（D-05） | LOW | OpenAI 相当は `finish_reason == "length"`。同じ判定パターンを踏襲可能 |
| サマリ生成用テキストのみ送信（`complete_text_ex`/`supports_text_prompt`） | 既存プロバイダ全て対応（Tesseract除く） | LOW | Claude/Gemini の `_build_text_payload` と同型の実装で足りる |
| 429/5xx リトライとバックオフ | 既存 `clamp_retry_after`/`interruptible_sleep`（Retry-After 60秒上限クランプ）を共有 | LOW | OpenAI も `Retry-After` ヘッダーを返す設計のため、既存の共有リトライ層（`_raise_mapped_http_error`）にそのまま載せられる |
| APIキーを settings.json に含めない・送信先明示・フォールバック時再確認 | v1.9.0 の明示的な安全境界維持要件（PROJECT.md Key context） | LOW | 既存パターンの横展開のみ |

#### B. 失敗時ロールバックの table stakes（デスクトップ PDF エディタ一般）

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 原子的保存（一時ファイルへ書き込み→成功時のみ rename で置換） | クラッシュ・ディスクフル・AV スキャン競合で原本を破壊しないことは編集ツールの最低条件。一般的な実装は「同一ディレクトリに一時ファイルを作り `os.replace`/rename で差し替え、失敗時は原本が無傷で残る」パターン | MEDIUM | PageFolio の `_save_as()`/`_overwrite_current_file()` は現状 `doc.save(path)`/`doc.tobytes()` の直接書き込みに近く、原子性が保証されていない。fitz のファイルロック挙動（開いたまま保存）を検証しつつ導入する必要あり |
| 暗号化維持がデフォルト（V190-REV-01） | 保護PDFを編集して保存する操作で暗号化が意図せず外れることは、一般的な PDF ツールでは起きてはならない事故（データ漏洩相当）として扱われる。「維持がデフォルト・解除は明示操作のみ」が業界慣行 | LOW | PyMuPDF は `save()`/`tobytes()` に `encryption=fitz.PDF_ENCRYPT_KEEP` を明示指定しないと暗号化が失われる。フラグ追加のみで解決するが、`_save_as()`・`_overwrite_current_file()`・上書きフォールバックの**3箇所すべて**で統一する必要（V190-REV-01 該当） |
| 複数ファイル取り込みの all-or-nothing（V190-REV-03） | 「3ファイル挿入中2件目で失敗」のとき、1件目だけ挿入されて中途半端な文書になるのはユーザーの直感に反する。一般的な期待は「全部成功 or 全部無かったことになる」 | MEDIUM | 一時 `Document` に全入力を構築してから本体へ一括反映する方式、または挿入済みページ数を追跡して例外時に自動デリートする方式。挿入元 `Document` の `finally` クローズも同時に必要 |
| Undo 記録は操作成功後に確定（V190-REV-04） | 「実行前にログだけ残る」設計は失敗時に不正な Undo エントリを生み、Undo が別のページを消すという重大な誤操作につながる。成功後確定は正しい操作の基本則 | LOW | `_save_undo()` の呼び出し位置を実処理の後ろへ移すだけ（他 op への影響範囲を限定できる） |
| Undo/Redo 復元失敗時のスタック保護（V190-REV-07） | 「元に戻す」操作自体が失敗して履歴を失うのは、Undo 機能の存在意義を壊す。一般的な期待は「復元に失敗したら履歴は失われず、可能なら操作前の状態に留まる」 | MEDIUM | `pop()` してから例外なしで `_restore_state()` する現状設計を、失敗時にスタックへ戻す try/except に変更。部分適用が起き得る op はロールバック可能単位への分割も検討 |
| 明確なエラーメッセージ（何が元に戻ったか） | 失敗時のトースト/ダイアログで「保存できませんでした（変更前の状態を維持）」等の具体性がないと、ユーザーは実データの状態を推測するしかない | LOW | 既存 `ToastManager`（再試行アクション付き非モーダル通知・v1.8.0 Phase 6）を活用すれば新規UI基盤は不要 |
| 部分適用は原則許容しない（許容する場合は明示） | 「一部だけ成功しました」を無警告で許すのは信頼を損なう。許容するなら結果を明示的に列挙する必要がある | LOW（方針決定のみ） | v1.9.0 は基本方針として all-or-nothing を採用（PROJECT.md の受け入れ条件と整合） |

#### C. 設定ダイアログ Apply/Cancel 契約の table stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Cancel は「変更を一切保存せず閉じる」 | OK/Apply/Cancel の一般的な意味論（OK=保存して閉じる、Apply=保存して開いたまま、Cancel=保存せず閉じる）は Windows/GUI の標準的な期待値 | LOW（方針） | PageFolio の `ShortcutsDialog`（V171-D-05）は既にこの契約を「一時コピー編集→保存ボタンまで実バインド非反映」で正しく満たしている。LLM設定側もこの前例に倣うべき |
| 外部ファイル副作用は Apply/OK 時のみ発生させる（V190-REV-05） | 設定ダイアログを開いている最中（値変更のたび）に外部ファイルへ即書き込みし、Cancel で戻さないのはアンチパターンそのもの。一般的に推奨されるのは「Apply/OK 時にのみ書き込む」か「開始時スナップショットを保持し Cancel で復元する」のいずれか | LOW〜MEDIUM | 「Apply時一本化」は書き込みタイミングを移すだけで LOW。「ライブ連動を維持しつつ Cancel 復元」を選ぶ場合はスナップショット保持・復元ロジックが要り MEDIUM。既存コードは `ocr_custom_prompt.md`/`ocr_summary_prompt.md` に即時書き込みしている現状の問題（`llm_config/sections.py:1142-1247`） |
| 未保存編集の切替確認は「ファイル連動の有無」に依存しない（V190-REV-06） | テンプレート切替時の「未保存です、破棄しますか」確認は、外部ファイルが存在するかどうかで挙動が変わってはならない。ユーザーから見れば「入力欄の中身が消えるかどうか」だけが関心事 | LOW | `_has_unsaved_template_changes()` の判定をファイル連動の有無で分岐させず、入力値とアクティブテンプレート値の比較に一本化する |

---

### Differentiators（OpenAI 固有・追加検討の価値がある要素）

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `detail` レベル選択（low/high/auto） | Claude/Gemini にはない「画像トークンコストを明示的にダイヤルできる」機能。OCR用途は精細さが必要なため既定は `high`/`auto` 寄りが妥当だが、低スペックPC・大量ページ処理でコストを抑えたいユーザーには `low` を選ばせる価値がある | MEDIUM | OpenRouter 等の実測では、low detail は逆に推論モデルが「思考を増やして補償」しコスト増になるケースが報告されている。**OCR という高精度要求タスクでは detail=low を既定にしない**のが妥当な設計判断（コスト確認ダイアログに detail 起因のコスト差を表示できると尚良い） |
| reasoning effort 相当パラメータ（gpt-5系: minimal/low/medium/high/xhigh） | Claude の `effort`（EFFORT_MODELS 限定許可リスト方式）と同型の概念。OCR は基本的に低 effort で十分なため、既定を低めに固定しつつ上級者向けに調整余地を残す差別化になり得る | MEDIUM | Claude と同じ「モデル対応判定の許可リスト」パターン（`EFFORT_MODELS` 相当）を新設すれば実装コストを抑えられる。対応値はモデル世代で異なる（gpt-5 は minimal〜high、gpt-5.6系はnone〜max相当）ため、Claude の「未知モデルはパラメータ省略で前方互換」方針（D-16）をそのまま流用するのが安全 |
| organization/project ID 指定（`OpenAI-Organization`/`OpenAI-Project` ヘッダー） | 複数組織に所属する法人ユーザー・レガシーな user API key を使うユーザーにのみ必要 | LOW（実装自体は単純なヘッダー追加） | **優先度は低い**。大半の個人ユーザー・単一組織ユーザーには不要な設定であり、UIに常時露出させると「何を入れればいいかわからない設定項目」を増やすだけになる。実装するなら「任意入力欄（空なら送信しない）」に限定し、LLM設定の「詳細設定」相当の折りたたみ領域に置くべき |
| コスト表示の粒度向上（detail・タイル数を考慮した概算） | 既存の「ページ数×固定1600トークン」という粗い近似より正確な見積もりを出せる | MEDIUM | ただし D-10 の設計方針（「精度より課金警告の存在が重要」）と価値が競合する。既存プロバイダとの見積もり一貫性を優先し、初期実装では既存の粗い近似方式を踏襲し、detail 別の差だけ簡易的に反映する程度が費用対効果が良い |

---

### Anti-Features（やらないほうがよいこと）

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| OpenAI Responses API へのフル移行（`store: true` によるステートフルな会話管理・agentic機能） | 「OpenAI公式の推奨は新規プロジェクトなら Responses API」という一般論に引きずられがち | PageFolio の OCR/サマリ呼び出しは 1 リクエスト完結（ページ毎に独立、会話継続なし）。ステート保持・agentic primitives は PageFolio の利用パターンと無関係で、実装複雑度と攻撃面（サーバー側に会話状態を残す `store:true` のプライバシー含意）だけが増える | Chat Completions 相当のステートレスな単発呼び出し（画像+プロンプトを1リクエストで送り、レスポンスを都度破棄）。Claude/Gemini と同型の構造を維持できる |
| OpenAI 公式 SDK（`openai` パッケージ）の導入 | 「公式SDKの方がメンテナンスが楽」という直感 | V14-D-01（urllib直叩き・新規pip依存ゼロ）に反する。PyInstaller 配布バイナリの肥大化、依存追跡コストの増加を招く。SDK は自動リトライや Retry-After ハンドリングを内包するが、それは urllib でも再現済み（既存 `_raise_mapped_http_error`/`clamp_retry_after`） | urllib 直叩き実装を Claude/Gemini と同パターンで踏襲 |
| organization/project の自動検出・複数組織切替UI | 「せっかくならフル対応したい」という完成度志向 | 明示設定型フォールバック方針（V180-D-02）・ミニマル実装方針と衝突する過剰実装。単一組織ユーザーが大多数の中でUIの複雑さだけが増す | 任意の空欄可・省略可能フィールドとして最小実装に留める（前述 Differentiator 参照） |
| detail=high を常時強制（ユーザー選択なし） | 「精度重視なら常に high の方が安全」という思い込み | 1024×1024画像で約765トークン（low比で約9倍）のコスト増。大量ページのバッチOCRでは無視できない課金差になる | detail を選択可能にしつつ、既定値は精度優先（high/auto）とし、コスト確認ダイアログで概算を明示する |
| 保存の度に毎回パスワード再入力を要求する（暗号化PDF編集時） | 「セキュリティを高めたい」という善意の過剰実装 | PageFolio は既に「開くときのみ `_authenticate_doc` で認証・保存時は暗号化情報を維持するだけ」という設計（暗号化解除は別名保存の🔒セクションのみ）。保存の度に再認証を求めるのは UX コストが高く、既存の明示的解除操作という安全設計の意義を薄める | 現行の「開封時認証・保存時は `PDF_ENCRYPT_KEEP` で維持・解除は明示操作のみ」方針を維持する（V190-REV-01の推奨対応と一致） |
| 部分適用の無警告許容（「n件中m件成功しました」を既定挙動にする） | 「全部失敗よりは一部でも成功した方が親切」という直感 | 複数ファイル挿入やUndo復元のような複合操作で部分適用を許すと、Document・Undo履歴・外部ファイルの状態が相互に矛盾し、後続操作（Undo等）が誤動作する。V190-REV-03/04/07 が扱う根本原因と同種 | all-or-nothingを既定にし、部分適用が構造的に不可避な場合のみ明示的な結果サマリ（成功/失敗の内訳）を表示する |
| 設定ダイアログにライブプレビュー目的の外部ファイル即時書き込みを残す | 「外部エディタで見ているファイルにすぐ反映したい」という利便性重視の要望 | Cancel時に元へ戻らない現状の実装（V190-REV-05）そのもの。副作用が Cancel の意味論を破壊する | Apply/OK 時にのみ書き込むか、開始時スナップショットを保持して Cancel 時に復元する。ライブ連動の利便性が必要なら後者を選ぶ |
| 未保存確認をファイル連動の有無で分岐させる特殊処理 | 「ファイルが無ければ設定値だけの話だから確認は軽くていい」という誤った単純化 | ユーザー体験としては「入力欄の中身が消えるかどうか」だけが重要で、裏側にファイルがあるかどうかは無関係。分岐が残ると V190-REV-06 のような抜け穴を生む | 判定ロジックを「入力値 vs アクティブテンプレート値」の比較一本にする |

---

## Feature Dependencies

```
[V190-REV-08: OCRプロバイダメタデータ一元化]
    └──requires-before──> [OpenAI(ChatGPT) プロバイダのフル実装]
                              （_is_cloud_provider・build_provider・フォールバック一覧・
                               表示名/モデル/送信先/APIキーエラー文言が現状複数箇所に
                               ハードコードされているため、先に一元化しないと実装漏れが
                               ほぼ確実に発生する＝V190-REV-08の課題そのもの）

[V190-REV-01〜04: 保存・編集の安全性]
    └──priority-before──> [OpenAI プロバイダ追加]
                              （PROJECT.md 明記の方針。機能追加より安全性修正を先行）

[V190-REV-05: 外部プロンプトファイル書き込みのApply一本化]
    └──shares-root-cause──> [V190-REV-06: テンプレート切替未保存確認]
                              （どちらも「ダイアログの値変更が即座に外部/内部状態へ
                               反映される」という同じ設計上の穴が原因。同一フェーズで
                               まとめて対応すると手戻りが少ない）

[V190-REV-04: 複製Undo記録の成功後確定]
    └──same-pattern-as──> [V190-REV-07: Undo/Redo復元失敗時のスタック保護]
                              （どちらも「Undoスタックの整合性は操作の成否と
                               同期していなければならない」という同一原則。
                               V190-REV-07のduplicate/merge/merge_resize水平展開は
                               v1.8.0 Phase6のinsert_redo対称化(D-17)と同型パターン）

[OpenAI: detail レベル選択] ──enhances──> [コスト確認ダイアログの表示粒度]
[OpenAI: reasoning effort] ──requires──> [Claude effortと同型の許可リスト方式（EFFORT_MODELS相当）]
[OpenAI: モデル一覧取得] ──conflicts-with-simplicity──> [/v1/modelsにvision対応フラグがない制約]
    （Claudeの`capabilities.image_input.supported`のような機械判定ができないため、
     静的プレフィックス判定 or 固定RECOMMENDED_MODELSのどちらかへ設計を倒す必要）
```

### Dependency Notes

- **V190-REV-08 が OpenAI 追加を requires-before する:** `_is_cloud_provider()`（`ocr_dialog.py:905`）が `("claude", "gemini", "runpod")` を直接ハードコードしているなど、プロバイダ名の分岐が `ocr.py`・`ocr_dialog.py`・`llm_config/sections.py`・`llm_config/dialog.py`・`batch_ocr.py`・`lang.py` の少なくとも6箇所に分散している（既存レビューノート該当）。この状態で OpenAI を追加すると、いずれかの分岐に追加漏れが起きて「バッチOCRだけクラウド判定されない」等の再発リスクがある。ロードマップ上は V190-REV-08 を独立フェーズとして OpenAI 追加の直前に置くべき。
- **安全性是正（V190-REV-01〜04）が OpenAI 追加より優先される:** PROJECT.md に明記された確定方針。新機能より既存の安全性欠陥（暗号化解除事故・OCR OFF迂回・非トランザクション挿入・不正Undo履歴）を先に塞ぐ。
- **V190-REV-05/06 は同一フェーズにまとめる価値がある:** 根本原因（値変更が即座に外部/UI状態へ波及する設計）が共通のため、個別修正より一括修正の方が手戻りが少ない。
- **V190-REV-07 の水平展開は v1.8.0 Phase 6 の前例（D-17）を踏襲できる:** `insert_redo`/`delete_redo` の対称化パターンと同じ思想（4手往復 do→undo→redo→undo テスト）を `duplicate`/`merge`/`merge_resize` へ広げる作業であり、新規パターンの発明ではない。

---

## MVP Definition（v1.9.0 スコープ内の優先順）

### Launch With（v1.9.0 P0/P1 — 必須）

- [ ] 暗号化維持の統一（V190-REV-01）— PDF_ENCRYPT_KEEP を通常保存/Save As/上書きフォールバックの3経路すべてに適用。機密PDFの平文化事故を防ぐ最優先項目
- [ ] OCR OFF の全経路一貫化（V190-REV-02）— `off` をプロバイダ生成不可にし、バッチOCR起動時・開始時にガードを追加
- [ ] 複数ファイル挿入のトランザクション化（V190-REV-03）— all-or-nothing、挿入元Documentの`finally`クローズ
- [ ] ページ複製のUndo記録を成功後確定（V190-REV-04）— 不正Undoによる誤削除を防止

### Add After Validation（v1.9.0 P2 — 基盤整備後に追加）

- [ ] 設定ダイアログのApply時書き込み一本化 or Cancel時復元（V190-REV-05）
- [ ] テンプレート切替の未保存確認をファイル連動有無によらず有効化（V190-REV-06）
- [ ] Undo/Redo復元失敗時のスタック保護＋duplicate/merge/merge_resizeへの4手往復テスト水平展開（V190-REV-07）
- [ ] OCRプロバイダメタデータの一元定義（V190-REV-08）— OpenAI追加の前提条件

### Future Consideration（OpenAI プロバイダ本体・基盤整備後に着手）

- [ ] OpenAI(ChatGPT) プロバイダのコア実装（urllib直叩き・ステートレス単発呼び出し・APIキー/モデル一覧/送信先確認/コスト確認/バッチOCR/フォールバック）— table stakes 部分
- [ ] detail レベル選択（コスト確認ダイアログへの反映込み）— differentiator、コア実装後の拡張として妥当
- [ ] reasoning effort 相当パラメータ（Claude effort と同型の許可リスト方式）— differentiator、コア実装後
- [ ] organization/project ID の任意入力欄（詳細設定領域への格納）— 優先度低。個人・単一組織ユーザーには不要なため v1.9.0 内でも最後尾、v1.9.x/v2 へ先送りしても支障はない

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| 暗号化維持の統一（V190-REV-01） | HIGH（データ漏洩防止） | LOW | P1 |
| OCR OFF全経路一貫化（V190-REV-02） | HIGH（意図しない外部送信防止） | LOW | P1 |
| 複数ファイル挿入トランザクション化（V190-REV-03） | HIGH（データ整合性） | MEDIUM | P1 |
| 複製Undo記録の成功後確定（V190-REV-04） | HIGH（誤削除防止） | LOW | P1 |
| 設定ダイアログApply/Cancel契約整合（V190-REV-05/06） | MEDIUM（意図しない動作変化の防止） | LOW-MEDIUM | P1 |
| Undo/Redo復元失敗保護＋水平展開（V190-REV-07） | MEDIUM（復旧不能事故の防止） | MEDIUM | P2 |
| OCRプロバイダメタデータ一元化（V190-REV-08） | MEDIUM（保守性・OpenAI追加の前提） | MEDIUM | P1（OpenAI追加の直前必須） |
| OpenAI プロバイダ table stakes 一式 | HIGH（機能拡張の主目的） | MEDIUM-HIGH | P2 |
| detail レベル選択 | MEDIUM（コスト最適化） | MEDIUM | P3 |
| reasoning effort 相当 | LOW-MEDIUM（OCR用途では効果限定的） | MEDIUM | P3 |
| organization/project ID | LOW（大半のユーザーに無関係） | LOW | P3 |

**Priority key:**
- P1: v1.9.0 で必須（安全性是正・OpenAI追加の前提条件）
- P2: v1.9.0 のメイン機能（OpenAIプロバイダ本体）
- P3: 拡張余地。v1.9.0内で手が回れば実装、回らなければv1.9.x/v2へ

---

## Competitor / Reference Analysis

| 観点 | Claude/Gemini（既存実装） | OpenAI（新規追加） | PageFolioの方針 |
|------|---------------------------|----------------------|-------------------|
| モデル一覧取得 | vision対応フラグをAPIが返す（Claude）/ generateContent対応で判定（Gemini） | `/v1/models` は vision対応フラグを返さない | 静的プレフィックス判定 or 固定RECOMMENDED_MODELSで代替（既存のD-08「未キー時は静的リスト」方針を未キー時に限らず併用） |
| effort/reasoning制御 | Claude: `EFFORT_MODELS` 完全一致リストで安全側判定 | gpt-5系で対応値がモデル世代により異なる | Claudeと同型の許可リスト方式を新設し、未知モデルはパラメータ省略（前方互換優先） |
| 画像コスト | Claude/Geminiとも「ページ数×概算固定トークン」の粗い近似 | detail依存で大きく変動（low=85 vs high=約765トークン/1024px） | 既存の粗い近似方式を踏襲しつつ、detail選択時のみ簡易的に係数を反映（過剰な精緻化はしない） |
| 認証ヘッダー | Claude: `x-api-key`、Gemini: `x-goog-api-key`（?key=クエリ不使用） | `Authorization: Bearer` + 任意 `OpenAI-Organization`/`OpenAI-Project` | 既存の「ヘッダー認証・クエリ不使用」方針を踏襲。organization/projectは任意省略可能な詳細設定に留める |
| 暗号化PDF保存 | （PDFツール一般の慣行）維持がデフォルト、解除は明示操作のみ | 該当なし（OCR機能とは無関係の論点） | V190-REV-01でPyMuPDFの`PDF_ENCRYPT_KEEP`を通常保存/Save As/上書きフォールバックの3経路に統一適用 |
| 設定ダイアログ契約 | ShortcutsDialog（V171-D-05）は一時コピー編集→保存ボタンまで非反映、という正しいCancel契約を既に実現 | 該当なし | LLM設定側もShortcutsDialogの前例パターンに倣い、Apply/OK時のみ外部ファイルへ反映する設計に統一 |

---

## Sources

- OpenAI Images and vision guide（`developers.openai.com/api/docs/guides/images-vision`）— detail パラメータ・OCR推奨設定（WebSearch経由、MEDIUM confidence・複数クエリでクロスチェック）
- OpenAI Migrate to the Responses API（`developers.openai.com/api/docs/guides/migrate-to-responses`）— Responses API vs Chat Completions の使い分け指針（MEDIUM confidence）
- OpenAI Reasoning models guide（`developers.openai.com/api/docs/guides/reasoning`）— reasoning_effort パラメータの値域（MEDIUM confidence）
- OpenAI Rate limits guide（`developers.openai.com/api/docs/guides/rate-limits`）— 429/Retry-After挙動（MEDIUM confidence）
- OpenAI API Reference / models endpoint（`platform.openai.com/docs/api-reference`）— `/v1/models` レスポンス形式（MEDIUM confidence）
- OpenAI Developer Community スレッド（organization/projectヘッダーの要否）（MEDIUM confidence・複数スレッドで一致した記述）
- OpenRouter Blog「Choosing the Optimal Image Input Detail Level in LLMs」— detail=lowが必ずしも安上がりでない実測（MEDIUM confidence）
- Foxit公式ドキュメント（保護PDFの取り扱い一般論）— Acrobat/PDF-XChangeとの横比較は一次情報が限定的で確度LOW。PageFolio既存実装（`_authenticate_doc`・パスワード解除は別名保存の専用セクションのみ）との整合を優先根拠とした
- デスクトップアプリの原子的保存パターン（一時ファイル+rename、`.bak`フォールバック）に関する複数の技術記事（MEDIUM confidence・一般的なUNIX/Windows双方で確立されたパターン）
- ダイアログボタン意味論（OK/Apply/Cancel）に関する一般的なUI設計解説（NN/g関連含む）（MEDIUM confidence）
- PageFolio既存コード調査: `pagefolio/ocr_providers/claude.py`・`gemini.py`・`registry.py`、`pagefolio/ocr_dialog.py`（`_estimate_cost`・`_is_cloud_provider`）、`.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md`（HIGH confidence・一次情報＝自プロジェクトコード）

---
*Feature research for: PageFolio v1.9.0（安全性・整合性の是正 + OpenAI プロバイダ追加）*
*Researched: 2026-08-10*
