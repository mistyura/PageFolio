# Feature Research

**Domain:** デスクトップ文書処理アプリ（Tkinter/Python・ローカル完結PDF編集 + 複数OCRプロバイダ統合）
**Researched:** 2026-07-13
**Confidence:** MEDIUM（複数ソース間で傾向が一致する部分は MEDIUM、単一ソースのみの部分は LOW と個別に明記）

**対象範囲:** v1.8.0 milestone で新規追加する5機能のみ。既存の外部プロンプトmd連動（v1.7.4）・プロバイダ別プロンプト最適化・コスト確認ダイアログ・サムネイルページネーション窓表示など**既に実装済みの機能は対象外**（milestone_context の "Existing features" 指示に準拠）。

---

## 1. プロンプト・テンプレートマネージャー

v1.7.4 で実装済みの「外部 md ファイル1枚との双方向連動」（`ocr_custom_prompt.md` / `ocr_summary_prompt.md`）を、**複数テンプレートの命名保存・切替**へ拡張する機能。

### Table Stakes（ユーザーが当然期待する挙動）

| 機能 | なぜ期待されるか | 複雑度 | 実装メモ |
|------|----------------|--------|----------|
| 名前を付けて保存 | LM Studio の Presets・PromptLayer の Prompt Registry など、業界標準は「名前付きプリセット/テンプレート」方式（MEDIUM確信）。無名の1枠しかないと「別案を試したら前のプロンプトが消えた」という事故が起きる | LOW | `settings.json` に `{"name": str, "text": str}` のリストを持たせるだけで足りる。DB 不要 |
| 一覧からの選択・切替 | プリセット選択は業界共通の基本UX（LM Studio Presets） | LOW | 既存 `LLMConfigDialog` にコンボボックス/リストボックスを1つ追加する程度 |
| 削除・上書き保存 | 「保存」機能があれば「削除」も期待される（CRUD の基本） | LOW | 確認ダイアログ必須（誤削除防止） |
| 既存の外部mdファイル連動との共存 | v1.7.4 のファイル連動ユーザーを壊さない後方互換が必須 | MEDIUM | 「ファイル連動 = 特別な1エントリ（選べない/常時最優先の項目）」として扱うか、テンプレート一覧の1メンバーとして統合するかの設計判断が必要 |

### Differentiators（差別化要素）

| 機能 | 価値提案 | 複雑度 | 実装メモ |
|------|----------|--------|----------|
| プロバイダ横断でのテンプレート共有 | 既存の「プロバイダ別プロンプト最適化」（Claude=XML/Gemini=明示）と両立させ、1つの命名テンプレートを複数プロバイダで使い回せる | MEDIUM | `resolve_ocr_prompt`（custom > provider別 > 汎用の優先順位）にテンプレート層をどう挟むか設計が必要 |
| プリセット種別（OCR用/サマリ用）のタグ分け | 既存の `preset=="markdown"` 等の区分と自然に統合できる | LOW | 保存データに `kind: "ocr"|"summary"` を持たせるだけ |
| インポート/エクスポート（テンプレート集を .md/.json でファイル共有） | 外部同期なしでプロンプト資産を配布できる | LOW〜MEDIUM | 単純な JSON/MD 書き出し・読み込み。外部送信を伴わないためプライバシー方針と整合 |

### Anti-Features（要注意・過剰実装ライン）

| 機能 | 一見良さそうな理由 | 実際の問題 | 代替案 |
|------|---------------------|------------|--------|
| プロンプトのバージョン管理（PromptLayer/LangSmith 型のコミット履歴・タグ・A/Bテスト） | 「プロ向けツールっぽい」高機能感 | PromptLayer/LangSmith はチーム開発・本番運用向けSaaS機能（LOW確信・単一ソース系）。単独デスクトップアプリのローカル完結ツールには過剰。Git的な差分UIの実装・保守コストに見合わない | 「保存＝上書き」のシンプルな最新版のみ管理。差分を見たければ手動で別名保存（"prompt_v2" 等）すれば足りる |
| クラウド同期（複数端末間でテンプレート共有） | 便利そう | 外部送信＝プライバシー方針（既定 off・明示同意）と矛盾。API キーと違い機密性は低いが、無断送信は方針違反 | ローカルファイルのインポート/エクスポートのみに留める |
| テンプレート内での変数プレースホルダ機構（`{{variable}}` 等の動的差し込み） | FlashPrompt 等の Web ツールでは一般的（LOW確信） | OCR/サマリ用途では差し込む変数がほぼ無い（対象はページ画像/OCR結果テキストのみ）。汎用テンプレートエンジンを持ち込むと過剰設計 | 現状通りプレーンテキストのプロンプト全文を保存するだけで十分 |

**最小実装ライン:** `settings.json` に名前付きテンプレート配列を追加 + `LLMConfigDialog` に一覧・保存・削除・適用の4操作。既存の外部mdファイル連動はそのまま「1つの特別枠」として共存させる。
**過剰実装ライン:** バージョン履歴・差分表示・クラウド同期・変数プレースホルダエンジン。

---

## 2. プロバイダーフォールバック（明示設定型）

### Table Stakes

| 機能 | なぜ期待されるか | 複雑度 | 実装メモ |
|------|----------------|--------|----------|
| フォールバック順の明示設定 | LiteLLM・Hermes Agent 等のゲートウェイ実装でも「`fallback_chain` を明示指定すれば自動生成をスキップしその順を優先する」が共通パターン（MEDIUM確信・複数ソース一致） | MEDIUM | `settings.json` にプロバイダ名の順序リストを保持。既存 `build_provider` ファクトリの前段にフォールバックループを追加 |
| 失敗時のみ次プロバイダへ | ユーザーが意図せず複数プロバイダに課金されることを防ぐ最低条件 | MEDIUM | 既存のリトライ/サーキットブレーカー機構（`ocr_pipeline.py` の fatal 判定）と統合。「リトライで直る系のエラー」と「フォールバックすべきエラー」を区別する設計が必要 |
| フォールバック発動時の明示通知 | ユーザーが「どのプロバイダで処理されたか」を把握できないと、想定外の課金/送信に気づけない | LOW | ステータス表示・結果ビューアに使用プロバイダ名を表示するだけで足りる |

### Differentiators

| 機能 | 価値提案 | 複雑度 | 実装メモ |
|------|----------|--------|----------|
| フォールバック時の送信先確認再提示 | 一般的なLLMゲートウェイ実装（LiteLLM等）には見当たらない機能（LOW確信）。既存の「クラウド送信の確認」ダイアログ（`lang.py` の `ocr_cost_confirm_title`：送信先・対象ページ数・概算コスト表示）をフォールバック候補にも再利用すれば、既存プライバシー方針（外部送信は明示同意）と一貫した独自の安全設計になる | MEDIUM | 既存の cost confirm ダイアログをプロバイダ切替のたびに再表示するフローに拡張。UI 再利用度が高く実装コストは抑えられる |
| プロバイダ別の障害理由をログ/結果に残す（どの理由でフォールバックしたか） | デバッグ・信頼性向上に寄与（一般記事でも「フォールバック率とステータスを相関させる」ことが推奨・LOW確信） | LOW | 既存のログ出力パターンに1行追加する程度 |

### Anti-Features（プライバシー方針と矛盾する設計を明確に排除）

| 機能 | 一見良さそうな理由 | 実際の問題 | 代替案 |
|------|---------------------|------------|--------|
| 自動ベンダー切替（ユーザー未設定でも「動くプロバイダ」に自動フォールバック） | 可用性が上がる（LiteLLM 等の一般的な自動フォールバックのウリ） | **PROJECT.md で明示的に不採用と確定済み**。ユーザーが把握していないプロバイダへ画像/テキストが無断送信されるリスクがあり、既定 off・明示同意という PageFolio の中核方針（V14-D-03）と正面から矛盾する | 「明示設定型」に限定：ユーザーが事前に選んだ順序リストの範囲でのみフォールバックし、かつ切替時に確認を再提示する |
| コスト最適化ルーティング（安いプロバイダへ自動振り分け） | LiteLLM/Bind AI 記事で紹介される「コスト最適化フォールバックチェーン」（LOW確信） | 送信先の予測可能性が下がり、ユーザーの想定と異なる課金先に送られうる | フォールバック順は純粋にユーザー指定の固定順のみ。動的な最適化ロジックは持たない |
| サイレントリトライの上限なし連鎖（全プロバイダを次々自動で試す） | 「とにかく処理を成功させたい」というニーズには合う | 各プロバイダ切替のたびに外部送信が発生するため、確認なしの連鎖は「明示同意」の趣旨を薄める。既存のリトライ（`clamp_retry_after`）と混同すると同一プロバイダへの過剰リトライにもなりうる | フォールバック候補は設定リストの範囲に限定し、各切替で確認を挟む。無限連鎖ではなく明示リストの終端で停止しエラー通知 |

**最小実装ライン:** 設定画面にプロバイダ順序リスト（ドラッグ並べ替え or 上下ボタン）+ 失敗時に次候補へ進む際の確認ダイアログ再提示（既存コスト確認ダイアログの再利用）。
**過剰実装ライン:** 自動ベンダー選択・コスト最適化ルーティング・確認なしの連鎖リトライ。

---

## 3. バッチ複数ファイル OCR

### Table Stakes

| 機能 | なぜ期待されるか | 複雑度 | 実装メモ |
|------|----------------|--------|----------|
| キュー一覧表示（追加したファイル一覧・各ファイルの状態） | AI UX Playground の Batch Processing Queue パターン・Wondershare/ABBYY/Tungsten 等の実装（MEDIUM確信・複数ソース一致）で共通の基本構成 | MEDIUM | ダイアログに Treeview/リストで表示。状態列（待機/処理中/成功/失敗） |
| 個別ファイル進捗 + 全体進捗 | 「今どのファイルの何ページ目か」が分からないと大量処理中の不安が大きい | MEDIUM | 既存 `ocr_pipeline.py`（producer-consumer 純ロジック層）のカウンタ機構をファイル単位に拡張できる可能性が高い（設計時に要確認） |
| 1件の失敗が全体を止めない | 堅牢な実装（KlearStack等）で共通言及される最低条件（LOW確信・単一ソース系だが業界慣行として妥当） | MEDIUM | 失敗ファイルをスキップして次へ進み、最後に失敗一覧を提示 |
| キャンセル（個別/全体） | 既存の OCR 実行にも既にキャンセル機構がある（`interruptible_sleep` 等）ため、バッチでも同水準のキャンセル可能性が期待される | MEDIUM | 既存のキャンセルフラグパターンをキュー全体・個別アイテムの2階層に拡張 |
| D&D による複数ファイル投入 | PageFolio は既に単一ファイル D&D（`file_drop.py`／`tkinterdnd2`）を持つため、複数ファイルOCRでも同じ操作感が期待される | LOW〜MEDIUM | 複数パスのドロップイベントをキューへ追加するだけ。既存 D&D 基盤の再利用度が高い |

### Differentiators

| 機能 | 価値提案 | 複雑度 | 実装メモ |
|------|----------|--------|----------|
| 一括要約（バッチ内の複数ファイルを跨いだ統合サマリ） | v1.6.0 で実装済みの「全ページ統合サマリ」機能をファイル横断に拡張する形なので、既存資産の延長として差別化しやすい | HIGH | 複数ファイル分のOCR結果テキストを保持しメモリ管理する必要があり、`fitz.Document` のスレッド非共有制約（メインスレッドのみレンダリング）とどう両立させるかが設計上の核心課題 |
| バックグラウンド継続（ダイアログを閉じても処理継続） | ABBYY/Wondershare 等の実装で言及される一般的な期待（MEDIUM確信） | HIGH | Tkinter はシングルウィンドウ・シングルメインループが基本のため、「ダイアログを閉じても止めない」を実現するには進捗をどこに表示し続けるか（ステータスバー常駐等）の UI 設計が別途必要。**大型機能として単独フェーズに隔離**するという PROJECT.md の判断は妥当 |
| 失敗ファイルの一括再試行 | デッドレターキュー的な失敗一覧からの再投入（LOW確信・一般論） | MEDIUM | 失敗一覧を保持しておけば「再試行」ボタンで同じキューに戻すだけ |

### Anti-Features

| 機能 | 一見良さそうな理由 | 実際の問題 | 代替案 |
|------|---------------------|------------|--------|
| 複数ファイルの並列 fitz レンダリング（マルチプロセス/複数ドキュメント同時オープン） | 処理速度が上がりそうに見える | CLAUDE.md に明記の通り `fitz.Document` はスレッド間で共有しない制約があり、複数ファイルの同時レンダリングは安定性リスクが高い。低スペックPC前提（V14-D-05/06）とも矛盾 | ファイル単位は**逐次**処理（1ファイルずつメインスレッドでレンダリング→送信→破棄）とし、並列化は同一ファイル内のページ送信部分（既存の `run_parallel`）に留める |
| バッチ全体を確認なしで一括クラウド送信 | 手間が減る | 大量ファイル×大量ページの一括送信は、既存の「コスト確認ダイアログ」（1ファイル単位の想定）の想定を超えるコスト規模になりうる。無警告での高額課金・大量外部送信は既存プライバシー/コスト方針と矛盾 | バッチ投入時に「対象ファイル数・概算総ページ数・概算コスト」をまとめて確認する集約版ダイアログを表示（既存ダイアログの拡張） |
| キューの永続化（アプリ再起動後もキューを復元） | 便利そう | 未処理ファイルの再現性（元PDFがまだ存在するか等）の担保が難しく、実装コストの割に得られる価値が小さい | 再起動時はキューをクリアし、ユーザーに再度ファイルを追加してもらう単純な設計に留める |

**最小実装ライン:** キュー一覧＋個別/全体進捗＋失敗分離＋D&D投入＋（ダイアログを閉じたら停止する）逐次処理。一括要約は既存の全ページ統合サマリをファイル横断に拡張。
**過剰実装ライン:** バックグラウンド常駐継続・キュー永続化・マルチプロセス並列レンダリング・確認なし一括送信。

---

## 4. サムネイル仮想化（PERF-01）

### 前提（既存実装の把握）

PageFolio は既に `pagination.py` で「窓表示」（既定20件・可視ウィンドウの範囲でしかサムネイルウィジェットを生成しない）を実装済みであり、これ自体が仮想化の実質的な代替パターンになっている。一方で `viewer.py` の `thumb_cache`（`_get_thumb_photo`）は**上限なしの辞書**で、閲覧した全ページの `ImageTk.PhotoImage` を保持し続ける（`_invalidate_thumb_cache` は明示クリアのみで自動 eviction なし）。したがって v1.8.0 の「サムネイル仮想化」は、Web 的な意味での連続スクロール仮想化（react-window 等）ではなく、**大量ページPDF（数百〜数千ページ）でのメモリ・描画コスト抑制**が主眼になる可能性が高い。

### Table Stakes

| 機能 | なぜ期待されるか | 複雑度 | 実装メモ |
|------|----------------|--------|----------|
| キャッシュの上限（LRU等）による自動 eviction | Tkinter に組み込みの仮想スクロール機構は存在せず（LOW確信）、Canvas+Frame+Scrollbar が標準パターン。大量ウィジェット/画像の事前生成がスクロール性能劣化の主因という一般認識と一致 | MEDIUM | `thumb_cache` を単純dict → `collections.OrderedDict` ベースの LRU に置換し、上限件数（例: 表示中窓の2〜3倍）を超えたら古いものから破棄 |
| 窓移動時の生成コスト削減が体感できる | 既に窓表示があるため「今より遅くならない」が最低ライン。数百ページ規模での実測改善が期待値 | MEDIUM | `_build_thumbnails` の生成タイミング・世代カウンタ（`_thumb_gen`）まわりの見直し |

### Differentiators

| 機能 | 価値提案 | 複雑度 | 実装メモ |
|------|----------|--------|----------|
| 窓サイズ拡張時（最大100件）でも破綻しない設計保証 | `pagination.py` の `PAGE_SIZE_MAX = 100` まで許容している以上、100件窓でもスムーズであることが差別化になる | MEDIUM | 既存の窓表示上限との整合テスト（大量ページPDFでのストレステスト、`test_undo_stress.py` に類する性能テストパターンが流用できる） |
| 遅延生成（窓内でも表示領域に入るまで生成を遅らせる） | 窓を開いた瞬間に20〜100件同時生成するより体感が軽くなる | HIGH | Tkinter のイベントループ・`after()` チェーンとの統合が必要で設計コストが高い。過剰実装ラインに近い |

### Anti-Features

| 機能 | 一見良さそうな理由 | 実際の問題 | 代替案 |
|------|---------------------|------------|--------|
| 連続スクロール型の本格仮想化（Web の react-window 相当をゼロから Tkinter に移植） | 「本物の仮想スクロール」という技術的な魅力 | 既存の窓表示（ページング）UIをスクロール型に作り替えるのはUI設計・D&D・選択照合ロジック（`pagination.py` の local↔global 変換）全体への影響が大きく、既存の枯れた設計（D-06〜D-11 で解消済みの窓またぎバグ）を壊すリスクが高い | 現行の「窓表示 + キャッシュeviction」路線を踏襲し、パフォーマンス問題を局所的に解消する |
| サムネイル生成の別プロセス化 | 応答性が上がりそうに見える | `fitz.Document` のスレッド非共有制約（メインスレッドのみ `get_pixmap()`）と衝突し、プロセス間でのdoc受け渡しは複雑化・不安定化のリスクが高い | メインスレッド同期生成のまま、キャッシュ戦略と生成タイミングの最適化に留める |

**最小実装ライン:** `thumb_cache` の LRU 化（上限付きeviction）+ 大量ページでの性能回帰テスト。
**過剰実装ライン:** 連続スクロール型仮想化への作り替え・別プロセス生成。

---

## 5. エラー時リカバリー通知の改善

### Table Stakes

| 機能 | なぜ期待されるか | 複雑度 | 実装メモ |
|------|----------------|--------|----------|
| 非モーダル表示 | トースト通知は時限式・非モーダルが業界標準（MEDIUM確信・Carbon Design System/LogRocket/Astro UXDS 等複数ソース一致）。現在の `messagebox.showerror()` は全てモーダルでユーザー操作をブロックする | MEDIUM | Toplevel + `overrideredirect` or 通常ウィンドウ内の常駐フレームで自前実装（Tkinter に標準トーストは無い） |
| 具体的な復旧手順の提示 | 「エラーが発生しました」だけでなく次に何をすべきかを示すのが定石（複数ソース一致） | LOW | 既存のエラーメッセージ文言をベースに「原因＋次の一手」形式へ書き換える（i18n=`lang.py` の両言語対応が必須） |
| アクション付き通知は自動消滅させない | タイマーで消えると押す前に消えてしまう事故を防ぐ（複数ソース一致） | LOW | 「再試行」ボタンを持つ通知はユーザーが閉じるまで表示を維持するロジックを実装 |

### Differentiators

| 機能 | 価値提案 | 複雑度 | 実装メモ |
|------|----------|--------|----------|
| 低重要度エラーへの「再試行」ボタン標準搭載 | バックグラウンド保存/同期失敗など軽微なエラーに有効という指摘に沿う（MEDIUM確信）。PageFolioの既存リトライ機構（OCR の指数バックオフ等）と自然に統合できる | MEDIUM | 通知UIに「再試行」を配置し、失敗した操作のコールバックを再実行するだけの薄い層で実現可能 |
| エラー種別ごとの復旧導線の出し分け（例: API キー未設定→設定画面へのショートカットボタン） | 既存の「APIキー未設定エラー」等、原因が特定できるケースでは該当ダイアログへの直接導線が高い価値を持つ | MEDIUM | 通知のアクションボタンに `lambda: self._open_llm_config()` 等の導線を紐付けるだけ。既存ダイアログ資産の再利用度が高い |

### Anti-Features

| 機能 | 一見良さそうな理由 | 実際の問題 | 代替案 |
|------|---------------------|------------|--------|
| 全エラーの通知化（致命的エラーも非モーダルトースト化） | 一貫性がありそう | ページ破損・ファイル書き込み失敗など致命的なエラーまで非モーダル化すると見落とされるリスクが高い。PROJECT.md のスコープも「小粒改善（非モーダル通知の前例踏襲）」であり全面置換ではない | 軽微・回復可能なエラー（OCR個別ページ失敗・ネットワーク一時エラー等）のみ非モーダル化。致命的エラーは引き続き `messagebox` のモーダルを維持 |
| 通知センター（過去のエラー履歴を一覧・永続化するパネル） | 高機能に見える | スコープが「小粒改善」である現milestoneの方針と不釣り合い。実装・保守コストが見合わない | 直近のエラーのみ画面上に表示し、履歴の永続化・専用パネルは持たない |

**最小実装ライン:** 軽微エラー向けの非モーダル・自前トースト（アクションボタン1つ・自動消滅なし）を1種類実装し、既存 `messagebox` 呼び出し箇所のうち回復可能なものだけ置き換える。
**過剰実装ライン:** 通知センター・全エラーの非モーダル化・エラー履歴の永続化。

---

## Feature Dependencies

```
[プロンプト・テンプレートマネージャー]
    └──requires──> [v1.7.4 外部mdファイル連動（既存・resolve_ocr_prompt）]

[プロバイダーフォールバック]
    └──requires──> [既存コスト確認ダイアログ（送信先確認の再利用）]
    └──requires──> [既存 build_provider / OCRProvider 抽象化（既存）]
    └──enhances──> [既存リトライ/サーキットブレーカー（ocr_pipeline.py）との境界整理が必須]

[バッチ複数ファイル OCR]
    └──requires──> [既存 D&D 基盤（file_drop.py）]
    └──requires──> [既存 producer-consumer パイプライン（ocr_pipeline.py）のファイル単位拡張]
    └──requires──> [既存 全ページ統合サマリ機能（一括要約の土台）]
    └──conflicts(注意)──> [fitz スレッド非共有制約 — 逐次処理が必須、並列化不可]

[サムネイル仮想化 PERF-01]
    └──requires──> [既存 pagination.py 窓表示（土台として拡張）]
    └──requires──> [既存 thumb_cache（viewer.py）— LRU化対象]

[エラー時リカバリー通知の改善]
    └──requires──> [lang.py 日英キー整合（新規文言追加時の両言語対応）]
    └──enhances──> [バッチOCRの失敗通知・プロバイダーフォールバックの切替通知と自然に統合可能]
```

### Dependency Notes

- **バッチ複数ファイル OCR は最も依存が多く最大の機能**のため、PROJECT.md の判断通り単独フェーズへ隔離するのが妥当。プロンプト・テンプレートマネージャーやエラー通知改善より後の phase に置くのが安全（先行する基盤機能が固まってから着手するほうがリスクが低い）。
- **プロバイダーフォールバックの「送信先確認再提示」は、エラー時リカバリー通知の改善と実装パターンを共有できる**（どちらも「非モーダルで具体的な次の一手を示す」UI）。同一 phase または隣接 phase に置くと UI コンポーネントを再利用しやすい。
- **サムネイル仮想化は他の4機能と機能的な依存がなく独立して着手可能**。既存 `pagination.py`/`viewer.py` の局所改修で完結するため、優先度調整の融通が利きやすい phase 候補。

---

## MVP Definition（v1.8.0 milestone 内でのスコープ判断）

### Launch With（v1.8.0 で確実に入れるべき最小ライン）

- [ ] プロンプト・テンプレートマネージャー: 名前付き保存・一覧選択・削除（CRUD最小4操作）— 既存外部mdファイル連動との共存必須
- [ ] プロバイダーフォールバック: 明示順序設定 + 切替時の送信先確認再提示（既存ダイアログ再利用）
- [ ] サムネイル仮想化: `thumb_cache` の LRU eviction + 大量ページでの性能回帰テスト
- [ ] エラー時リカバリー通知: 軽微エラー向け非モーダルトースト1種（再試行ボタン付き・自動消滅なし）
- [ ] バッチ複数ファイル OCR: キュー一覧 + 個別/全体進捗 + 失敗分離 + D&D投入 + 逐次処理（ダイアログ内完結・バックグラウンド常駐なし）

### Add After Validation（v1.8.x 以降・様子見）

- [ ] バッチOCRの失敗ファイル一括再試行
- [ ] プロンプトテンプレートのインポート/エクスポート（.md/.json）
- [ ] プロバイダー切替理由のログ表示強化

### Future Consideration（v2+・現時点では見送り）

- [ ] バッチOCRのバックグラウンド継続（ダイアログを閉じても処理継続）— Tkinter シングルループ制約下でのUI設計コストが高い
- [ ] プロンプトテンプレートのバージョン履歴・差分表示
- [ ] サムネイルの連続スクロール型本格仮想化

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| プロンプト・テンプレートマネージャー（CRUD） | MEDIUM | LOW | P1 |
| プロバイダーフォールバック（明示設定+確認再提示） | HIGH | MEDIUM | P1 |
| サムネイル仮想化（LRUキャッシュ化） | MEDIUM | MEDIUM | P1 |
| エラー時リカバリー通知（非モーダルトースト） | MEDIUM | MEDIUM | P1 |
| バッチ複数ファイルOCR（キュー最小実装） | HIGH | HIGH | P1（ただし単独フェーズ） |
| バッチOCR 一括要約（ファイル横断サマリ） | MEDIUM | HIGH | P2 |
| プロンプトテンプレートのインポート/エクスポート | LOW | LOW | P2 |
| バッチOCRのバックグラウンド継続 | LOW〜MEDIUM | HIGH | P3 |
| プロンプトのバージョン履歴・差分UI | LOW | HIGH | P3 |
| サムネイル連続スクロール型仮想化 | LOW | HIGH | P3 |

**Priority key:**
- P1: v1.8.0 milestone で必須
- P2: 余裕があれば同milestone、なければ次点
- P3: 将来検討（今回は見送り推奨）

## Competitor Feature Analysis

| Feature | LM Studio / PromptLayer / Langfuse | LiteLLM / Hermes Agent（フォールバックゲートウェイ） | 各種商用OCRツール（ABBYY/Wondershare/Tungsten） | Our Approach |
|---------|--------------------------------------|--------------------------------------------------------|--------------------------------------------------------|--------------|
| プロンプト管理 | 名前付きPreset/Registry・変数・タグ | — | — | 名前付きテンプレートCRUD。バージョン履歴等の重量級機能は非採用 |
| プロバイダフォールバック | — | 明示 `fallback_chain` 優先・障害検知→順次試行 | — | 同様に明示順序のみ採用。ただし各切替で送信先確認を再提示（他ツールに無い独自の安全設計） |
| バッチOCRキュー | — | — | キュー一覧・個別進捗・失敗分離・バックグラウンド継続 | キュー一覧・個別進捗・失敗分離までは同水準。バックグラウンド継続はTkinter制約上見送り |
| 通知UX | — | — | — | 業界標準のトースト（非モーダル・アクション付きは自動消滅なし）を軽微エラーのみに適用 |

## Sources

- [Prompt Template | LM Studio](https://lmstudio.ai/docs/app/advanced/prompt-template) — MEDIUM
- [Config Presets | LM Studio](https://lmstudio.ai/docs/app/presets) — MEDIUM
- [Prompt Registry Overview - PromptLayer](https://docs.promptlayer.com/features/prompt-registry/overview) — LOW（単一ソース）
- [Open Source Prompt Management - Langfuse](https://langfuse.com/docs/prompt-management/overview) — LOW（単一ソース）
- [Best Prompt Versioning Tools for LLM Optimization (2025) - PromptLayer Blog](https://blog.promptlayer.com/5-best-tools-for-prompt-versioning/) — LOW
- [LangSmith Prompt Management - How it Works | Mirascope](https://mirascope.com/blog/langsmith-prompt-management) — LOW
- [Fallback Providers | Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers) — MEDIUM
- [Fallbacks (Provider Failover) | liteLLM](https://docs.litellm.ai/docs/proxy/reliability) — MEDIUM
- [Provider fallbacks: Ensuring LLM availability - Statsig](https://www.statsig.com/perspectives/providerfallbacksllmavailability) — LOW
- [Batch Processing Queue · Performance AI UX Pattern | AI UX Playground](https://aiuxplayground.com/pattern/batch-processing-queue/) — MEDIUM
- [Batch processing — ocrmypdf docs](https://ocrmypdf.readthedocs.io/en/latest/batch.html) — LOW
- [Batch Document Processing OCR: Guide from KlearStack](https://klearstack.com/blogs/batch-document-processing-ocr) — LOW
- [How to speed up scrolling responsiveness when displaying lots of text in Tkinter - TutorialsPoint](https://www.tutorialspoint.com/article/how-to-speed-up-scrolling-responsiveness-when-displaying-lots-of-text-in-tkinter) — LOW
- [Scrollable Frames in Tkinter - GeeksforGeeks](https://www.geeksforgeeks.org/python/scrollable-frames-in-tkinter/) — LOW
- [UX Files - The UX of notification toasts](https://benrajalu.net/articles/ux-of-notification-toasts) — MEDIUM
- [Notification pattern - Carbon Design System](https://carbondesignsystem.com/patterns/notification-pattern/) — MEDIUM
- [Notifications - AstroUXDS](https://www.astrouxds.com/patterns/notifications/) — MEDIUM
- [What is a toast notification? Best practices for UX - LogRocket Blog](https://blog.logrocket.com/ux-design/toast-notifications/) — MEDIUM
- 社内コードベース確認: `pagefolio/pagination.py`（窓表示純ロジック）・`pagefolio/viewer.py`（`thumb_cache` eviction無し）・`pagefolio/settings.py`（外部プロンプトファイル連動）・`pagefolio/lang.py`（既存コスト確認ダイアログ文言 `ocr_cost_confirm_title`）・`pagefolio/ocr.py`（`resolve_ocr_prompt` 優先順位） — HIGH（一次情報）

---
*Feature research for: PageFolio v1.8.0（プロンプトテンプレート管理・プロバイダーフォールバック・バッチOCR・サムネイル仮想化・エラー通知改善）*
*Researched: 2026-07-13*
