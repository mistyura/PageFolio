# Architecture Research — v1.8.0 新機能の既存アーキテクチャ統合

**Domain:** Tkinter デスクトップ PDF エディタ（PageFolio）— Mixin 構成 + 純ロジック層 + producer-consumer OCR パイプライン
**Researched:** 2026-07-13
**Confidence:** HIGH（実コードベース直接精査に基づく。外部ライブラリ調査ではなく自プロジェクトのソース読解が根拠のため、情報源は最上位＝curated 相当）

> 本ファイルは v1.4.0 期（2026-06-06）の旧 ARCHITECTURE.md（OCR プロバイダ抽象化統合）を置き換える。旧内容は `.planning/milestones/v1.4.0-*` にて実装済み・アーカイブ済みのため、v1.8.0 マイルストーンの統合設計に更新した。

このドキュメントは v1.8.0 の新機能（① プロンプト・テンプレートマネージャー、② 明示設定型プロバイダーフォールバック、③ バッチ複数ファイル OCR キュー、④ サムネイル仮想化 PERF-01、⑤ 肥大モジュール分割）を、既存アーキテクチャ（Mixin パターン + `pagination.py`/`md_render.py`/`undo_store.py`/`ocr_pipeline.py` の Tk/fitz 非依存純ロジック層 + producer-consumer OCR パイプライン）へどう統合するかを設計する。

## 現状アーキテクチャ要点（統合設計の前提）

```
PDFEditorApp（8 Mixin 合成）
  ├─ OCRMixin (ocr.py)
  │    build_provider(settings, api_key, plugin_manager) → OCRProvider インスタンス1つ
  │    run_parallel(provider, images_b64, ...)            → 旧式・レガシー並列実行
  │    resolve_ocr_prompt / resolve_summary_prompt          → 純関数（プロンプト解決）
  │
  ├─ ocr_pipeline.py（Tk/fitz 非依存 純ロジック層）
  │    PipelineState（done_count / consec_err_count / fatal_msg / fatal_kind・Lock 保護）
  │    consume_one(provider, item, prompt, state, callbacks...)  ← 1 アイテム消費（リトライ/fatal 判定）
  │    try_enqueue / send_sentinels                              ← 非ブロッキング queue 操作
  │
  ├─ ocr_providers.py（1424行・6プロバイダ + ABC + 3例外）
  │    OCRProvider(ABC) / LMStudioProvider / ClaudeProvider / GeminiProvider /
  │    TesseractProvider / OllamaProvider / RunPodProvider
  │
  └─ ocr_dialog.py（2154行・OCRDialog(tk.Toplevel)）
       producer（メインスレッド, fitz 唯一のアクセス点）:
         _render_next_page() ── after(0) 連鎖 ── fitz.get_pixmap()→b64 → try_enqueue
       consumer（ワーカースレッド × concurrency 本）:
         _worker() → ocr_pipeline.consume_one() に委譲（fitz 一切触らない）
       PipelineState は _start_worker_thread で concurrency 確定後に1個生成・
       全ワーカー共有（decrement_worker で最終ワーカーのみ終了処理）

viewer.py（ViewerMixin）
  ├─ pagination.py（Tk/fitz 非依存）: window_bounds/to_global/to_local/
  │    reconcile_window_start/clamp_page_size  ← 「窓（10〜100ページ）」単位の
  │    ドキュメントレベル・ページネーション。selected_pages は常に全ページ index。
  └─ _build_thumbnails(): 窓 [lo,hi) の**全ページ分**の Frame/Label を毎回生成し
       pack → after(0) 連鎖で PhotoImage を順次差し込む。可視範囲に関わらず
       窓全体（最大100）のウィジェットを即時生成するのが PERF-01 の実体。

settings.py
  外部プロンプトファイル1本立て（V174-2）: CUSTOM_PROMPT_FILE / SUMMARY_PROMPT_FILE
  load_prompt_file/save_prompt_file/prompt_file_exists/load_custom_prompt/load_summary_prompt
  優先順位: 外部mdファイル > settings.json の該当キー
```

**機械保証されている制約（絶対に崩さない）:**
- fitz へのアクセス（`fitz.open`/`page.get_pixmap`/`page.get_text`）はメインスレッドのみ。ワーカースレッドには base64 のみ渡す（V14-D-05/06・D-04/D-05）。
- `fitz.Document` はスレッド間で共有しない。
- `selected_pages` は常に全ページ index（窓ローカルではない）。窓変換は `pagination.py` の純関数のみで行う（散在防止・D-06/D-07）。
- 純ロジック層（`pagination.py`/`md_render.py`/`undo_store.py`/`ocr_pipeline.py`）は `tkinter`/`fitz` を import しない。新規純ロジックもこの規約に従う。

---

## (a) バッチ複数ファイル OCR ── キュー設計

### 制約の再確認
「fitz はメインスレッドのみ・1 doc ずつ」という milestone context の制約は、**複数の `fitz.Document` を同時に開くこと自体を禁止しているわけではない**（PyMuPDF はプロセス内で複数 Document を保持可能）。禁止されているのは「ある Document への fitz 呼び出しをワーカースレッドから行うこと」「複数スレッドが同時に同一/別 Document の fitz API を並行して叩くこと」である。したがって設計方針は：

- **N個のファイルを"順番に"1個ずつ開いて処理し、常にアクティブな `fitz.Document` は最大1個**（現行 OCRDialog が `self.doc`＝アプリの開いている1文書に対して行っていることを、ファイルキューの各要素に対して繰り返すだけ）。
- ページ render（producer）は既存の `_render_next_page` と同じ「メインスレッド + after(0) 連鎖」パターンをそのまま流用できる。consumer（ワーカー）も `ocr_pipeline.consume_one` をそのまま再利用できる。**バッチ機能は producer/consumer の中身を変更しない。ファイルをまたぐループを一段外側に追加するだけ**で済む設計にする。

### 新規モジュール

**`pagefolio/batch_queue.py`（新規・Tk/fitz 非依存の純ロジック層）**
`pagination.py`/`ocr_pipeline.py` と同格の位置づけ。

```python
# 責務: ファイルキューの状態遷移を純粋に管理する（Tk/fitz を一切 import しない）
class BatchQueueState:
    # items: [{"path": str, "status": "pending"|"running"|"done"|"error"|"cancelled",
    #          "error_msg": str|None}]
    def __init__(self, paths): ...
    def current(self): ...          # 実行中/次に実行するアイテムを返す
    def mark_running(self, idx): ...
    def mark_done(self, idx): ...
    def mark_error(self, idx, msg): ...
    def advance(self): ...          # 次の pending アイテムへ進む。無ければ None
    def is_all_finished(self): ...
    def summary_counts(self): ...   # {"done": n, "error": n, "pending": n} 進捗表示用
```
`PipelineState`（ページ単位の producer-consumer 状態）と役割が異なる＝**キュー要素はファイル、ファイル内部は既存の `PipelineState` をそのまま1個ずつ使い回す**という二層構造にする。`test_pagination.py`/`test_ocr_pipeline.py` と同型の `test_batch_queue.py` で状態遷移を単体テスト可能にする（品質保証の柱③にも直結）。

**`pagefolio/ocr_engine.py`（新規・(d) のリファクタと共用）**
現行 `OCRDialog` に埋め込まれている「1ドキュメント分の OCR 実行機」（producer 起動・consumer 起動・進捗コールバック）を、ダイアログの UI から切り離して再利用可能なクラスに抽出する。単一ページ OCR（既存 OCRDialog）とバッチ OCR の両方がこれを呼ぶ。詳細は (d) 参照。

**`pagefolio/dialogs/batch_ocr.py`（新規・UI）**
`BatchOCRDialog(tk.Toplevel)`。ファイル追加/削除リスト・全体進捗・現在処理中ファイル名・キャンセルボタンを持つ。実行ロジック:

```
for item in queue (順次・1個ずつ):
    doc = fitz.open(item.path)          # メインスレッド
    engine = OCRRunEngine(doc, page_indices=all_pages, provider, ...)
    engine.run(on_complete=lambda results: ...)  # 既存 producer/consumer 機構を流用
    # engine 完了を待って（after チェーンの最終コールバックで）:
    doc.close()                          # メインスレッドで明示的に解放
    queue.mark_done(idx) / mark_error(idx, msg)
    advance to next file                 # 次ファイルは前ファイル完了後にのみ open
```

- ファイル間は**逐次**（並行 fitz.Document は作らない）。ファイル内のページ並列度（concurrency）は既存設定をそのまま使う。
- キャンセル: 現行ファイルの `_cancel_flag`（ファイルレベル）＋キュー全体の `queue_cancel_flag`（次ファイルへ進まない）の2階層。世代カウンタ（`_run_gen` 相当）もファイルごとに張り直す。
- 結果は「ファイルパス→{page_idx: text}」の辞書としてダイアログが保持し、既存の「一括要約」（`_on_summary`/`resolve_summary_prompt`）をファイル単位にも、任意で「サマリのサマリ（複数文書横断）」にも適用できる形にしておく。
- **アプリの `self.doc`（メインウィンドウで開いているファイル）とは完全に独立**させる。バッチダイアログは自前で `fitz.Document` を開閉するため、Undo スタック・`current_page`・サムネイルキャッシュ等のメイン状態に一切触れない。これにより「1 doc ずつ」制約と「メインスレッドのみ」制約の両方を、既存の状態管理を汚さずに満たせる。

### 統合ポイントまとめ

| 新規/変更 | ファイル | 内容 |
|---|---|---|
| 新規（純ロジック） | `pagefolio/batch_queue.py` | ファイルキュー状態遷移（Tk/fitz 非依存） |
| 新規（実行エンジン抽出） | `pagefolio/ocr_engine.py` | OCRDialog から producer/consumer 駆動部を抽出・再利用可能化（(d)と共用） |
| 新規（UI） | `pagefolio/dialogs/batch_ocr.py` | BatchOCRDialog（キュー管理UI・逐次ファイル処理） |
| 変更 | `pagefolio/ui_builder.py` | バッチOCR起動ボタン/メニュー項目の追加 |
| 変更なし | `ocr_pipeline.py` / `ocr_providers.py` | そのまま再利用（producer/consumer の中身は不変） |

---

## (b) 明示設定型プロバイダーフォールバック ── 挿入層の選定

### 既存3層の役割の切り分け
- `build_provider()`（ocr.py）: settings から**1個の** OCRProvider を生成する純粋なファクトリ。複数プロバイダの概念を知らない。**ここには挟まない**（単一責務を壊さない）。
- `run_parallel()` / `consume_one()`（ocr_pipeline.py）: 1プロバイダに対する**ページ単位のリトライ**（429/5xx の指数バックオフ、`OCRRetryableError`）を扱う層。これは「同一プロバイダ内の一時的失敗からの回復」であり、フォールバック（＝別ベンダーへの切替）とは意味が異なる。**ここにも挟まない**。
- `OCRDialog`（`_worker`/`_finish_error`）: `PipelineState.fatal_msg`/`fatal_kind`（`connection`/`timeout`/`circuit_breaker`＝3連続失敗）を検知して**実行を打ち切る**層。フォールバックが必要になる「プロバイダが使い物にならない」という判定は、まさにこの `fatal_msg`/`fatal_kind` 確定タイミングで既に構造的に検出されている。

→ **フォールバックは `PipelineState` の fatal 確定を受け取った後の、OCRDialog（または (a)/(d) で抽出する `OCRRunEngine`）の制御フローに、既存プリミティブを変更せずオーケストレーション層として追加するのが最も安全。**

### 新規モジュール

**`pagefolio/provider_fallback.py`（新規・純ロジック層）**
```python
def next_fallback_provider(current_provider, fallback_order, already_tried):
    """フォールバック順リストから、まだ試していない次のプロバイダ名を返す。
    None ならフォールバック先なし（既存のエラー表示へフォールバック）。
    Tk/fitz/ネットワーク非依存の純関数。"""
```

### 実行フロー（明示確認つき）

```
1. build_provider(settings) で主プロバイダを生成 → 実行 → PipelineState.fatal_msg 確定
2. fatal_kind in ("connection","timeout","circuit_breaker") かつ
   settings["ocr_fallback_providers"] が非空 かつ
   next_fallback_provider() が None でない場合:
     → 既存の「送信先確認ダイアログ」（コスト確認と同じ UI 部品）を再利用し
       「プロバイダ X が失敗しました。フォールバック先 Y を試しますか？」を明示提示
     → 同意された場合のみ:
         build_provider(settings, provider_override=Y) で Y を生成
         未処理・失敗ページのみを対象に新しい _run_gen で再実行
           （成功済みページは再送信しない＝コスト面で重要）
     → 拒否 or フォールバック先なし の場合は既存のエラー表示へ
```

- **設定の永続化:** `settings["ocr_fallback_providers"] = []`（プロバイダ名の順序付きリスト・既定は空＝オフ。既存の "既定 off" 方針=V14-D-03 と整合）。プロバイダ名の文字列のみで API キーを含まないため `_SENSITIVE_KEYS` の対象外・そのまま JSON 永続化可。
- **APIキー未設定のフォールバック先:** `_resolve_api_key` が `OCRAPIKeyError` を出す場合は、そのフォールバック候補を「使えない」として自動的に次候補へ進める（ユーザーへの確認ダイアログはキーが解決できるプロバイダに対してのみ出す）。
- **禁止事項の遵守:** milestone context の「自動的な別ベンダー送信はしない」を満たすため、フォールバック候補が1個であっても確認ダイアログは必ず経由する（省略しない）。

### 統合ポイントまとめ

| 新規/変更 | ファイル | 内容 |
|---|---|---|
| 新規（純ロジック） | `pagefolio/provider_fallback.py` | フォールバック順の次候補決定（純関数） |
| 変更 | `pagefolio/ocr.py` | `build_provider()` に任意引数 `provider_override` を追加（settings の `ocr_provider` を上書きして同じ設定値で別プロバイダを生成できるようにする軽微な拡張。既存呼び出しは影響なし） |
| 変更 | `pagefolio/ocr_dialog.py`（または (d) 抽出後の `ocr_engine.py`） | `_finish_error` 相当の箇所でフォールバック確認ダイアログ呼び出し・再実行トリガーを追加 |
| 変更 | `pagefolio/settings.py` | `_load_settings()` の defaults に `ocr_fallback_providers: []` を追加 |
| 変更 | `pagefolio/dialogs/llm_config.py`（分割後の新パッケージ内） | フォールバック順の編集 UI（順序リスト・追加/削除/並べ替え）を新セクションとして追加 |
| 変更なし | `ocr_pipeline.py` / `run_parallel` | 単一プロバイダの実行プリミティブは不変 |

---

## (c) サムネイル仮想化（PERF-01）と `pagination.py` の関係

### 現状の2重構造の認識
`pagination.py` の「窓（window）」は**ドキュメントレベルの粗いページネーション**であり、既に「全ページを一度に描画しない」という最適化を担っている（既定20・最大100ページ窓）。しかし `_build_thumbnails()` の実装を見ると、窓の範囲 `[lo, hi)` に含まれる**全ページ分**の Tk ウィジェット（Frame + 2 Label）を `_add_thumb_placeholder` でループ生成し `pack` している。窓を100に設定したユーザーは、スクロール可能な Canvas の可視範囲（実際は10〜15枚程度しか画面に収まらない）に関わらず、常に100個のウィジェットとサムネイル画像を生成・保持することになる。これが PERF-01 の実体的なボトルネックであり、`pagination.py` の窓ロジックだけでは解決しない**別レイヤーの問題**である。

### 設計方針：窓（外層）はそのまま・可視範囲仮想化（内層）を追加

`pagination.py` の `to_global`/`to_local`/`window_bounds`/`selected_pages`（常に全ページ index）は D&D・複数選択の整合性を守る不変条件として CONCERNS.md でも「散在すると窓またぎバグを生む」と明記されている、**触ってはいけない層**。したがって：

- **外層（不変）:** `_page_window_start`・`_page_size`（10〜100）・`pagination.py` の窓計算はそのまま。これは「どのページ範囲が候補か」を決めるだけの層として維持する。
- **内層（新規）:** 窓の中でも「Canvas のスクロール位置から見て実際に画面内（＋前後バッファ数行）にあるページだけ」ウィジェットを実体化する、リスト仮想化（windowed list virtualization）パターンを追加する。

### 新規モジュール

**`pagefolio/thumb_virtualizer.py`（新規・Tk/fitz 非依存の純ロジック層）**
`pagination.py` と同じ設計哲学（純関数・状態非依存）で、可視範囲計算だけを担う。

```python
def visible_local_range(scroll_top_px, viewport_height_px, row_height_px,
                         total_rows, buffer_rows=3):
    """スクロール位置と行高さから、実体化すべき窓ローカル index 範囲
    (first_local, last_local) を返す（前後 buffer_rows 分の余裕つき）。
    Tk/fitz 非依存の純関数。test_pagination.py と同型の単体テストが可能。"""
```

- 出力はあくまで「窓ローカル index」であり、実ページへの変換は既存の `pagination.to_global(local_pos, window_start)` にそのまま委譲する（二重変換にならないよう、仮想化層は pagination 層の**上に**乗る形にする。仮想化層が新しいグローバル変換ロジックを独自に持たない）。

### ViewerMixin 側の変更

- `_build_thumbnails()`: 窓 `[lo, hi)` の**全件**に対して即時 `_add_thumb_placeholder` する現行実装をやめ、`thumb_virtualizer.visible_local_range()` が返す可視サブレンジのみ実体化する。
- Canvas の `<Configure>`（サイズ変更）・スクロールバー移動（`yscrollcommand`/`yview` 経由のコールバック）にバインドした `_reflow_thumbnails()` を新設し、スクロールのたびに可視サブレンジを再計算 → 差分だけウィジェットを生成/破棄（またはウィジェットプールを再利用してラベルの `image=` を差し替えるリサイクル方式。生成コストがボトルネックであれば後者を推奨）。
- `thumb_cache`（CONCERNS.md で「無制限に増える」と指摘済み）も、この変更のついでに「窓サイズの2倍程度」を上限とした LRU に縮小する。可視外まで無制限にキャッシュを持つ必要が仮想化によりなくなるため、自然に解消できる。
- 既存の世代カウンタ（`_thumb_gen`）パターンはそのまま流用し、スクロール中に古い再スケジュールが割り込まないようにする。
- `selected_pages`・D&D の座標処理は一切変更しない（常に `pagination.to_global`/`to_local` 経由の全ページ index を使う既存契約を維持）。仮想化はあくまで「どのウィジェットを実体化するか」の描画最適化に閉じる。

### 統合ポイントまとめ

| 新規/変更 | ファイル | 内容 |
|---|---|---|
| 新規（純ロジック） | `pagefolio/thumb_virtualizer.py` | 可視範囲計算（純関数・pagination.py と同格） |
| 変更 | `pagefolio/viewer.py` | `_build_thumbnails()` を可視サブレンジのみ実体化する方式に変更・`_reflow_thumbnails()` 新設・Canvas スクロールイベントへのバインド追加 |
| 変更 | `pagefolio/viewer.py` | `thumb_cache` に LRU 上限を追加（既存 CONCERNS.md 指摘の解消を兼ねる） |
| 変更なし | `pagefolio/pagination.py` | 窓計算・`to_global`/`to_local`・`selected_pages` 契約は完全に不変 |
| 変更なし | `pagefolio/dnd.py` | D&D の index 変換ロジックは不変（仮想化は描画層のみの変更） |

---

## プロンプト・テンプレートマネージャー（settings.py の拡張）

既存の外部プロンプトファイル1本立て方式（`CUSTOM_PROMPT_FILE`/`SUMMARY_PROMPT_FILE`・V174-2）を、複数の**名前付きテンプレート**へ拡張する。

- **保存方式:** JSON 設定への巨大テキスト混入を避けるため、既存パターン（実行ファイルと同階層の外部ファイル）を踏襲し、新設ディレクトリ `prompt_templates/`（exe と同階層）配下に `<template名>.md` を1ファイル1テンプレートとして保存する。API キーではないため機密ガードは不要。
- **`settings.py` への追加関数:** `list_prompt_templates()` / `load_prompt_template(name)` / `save_prompt_template(name, content)` / `delete_prompt_template(name)`。いずれも既存の `load_prompt_file`/`save_prompt_file`（`_get_base_dir()` 基準）を内部で再利用し、ファイル名だけをテンプレート名でパラメータ化する（重複実装を避ける）。
- **優先順位（既存 V174-2 契約を壊さない3層に拡張）:** ①現在選択中の名前付きテンプレート（新規） > ②単一の外部 md ファイル（`ocr_custom_prompt.md`・後方互換） > ③ `settings.json` の `ocr_custom_prompt` 値。`resolve_ocr_prompt`/`load_custom_prompt` のシグネチャは維持し、呼び出し元（`ocr.py:_start_ocr`）で「選択中テンプレート名があればその内容、無ければ従来どおり `load_custom_prompt(settings)`」という薄い分岐を追加するだけで済む。
- **UI:** (d) で分割予定の `llm_config` パッケージ内に新セクション（テンプレート選択ドロップダウン＋名前を付けて保存/削除/名前変更ボタン）として追加する。既存の `_add_prompt_file_notice`（外部ファイル連動注記）と同じ場所に隣接配置し、「外部ファイルが存在する場合はそちらが優先される」旨の注記を踏襲する。

---

## (d) 肥大モジュール分割 ── 安全な切り出し順序

### 結論：ocr_providers.py → llm_config.py → ocr_dialog.py の順

| 順 | モジュール | 現状行数 | 理由 |
|---|---|---|---|
| 1 | `ocr_providers.py` | 1424行 | 結合度が最も低い（各 Provider クラスはほぼ自己完結）。`dialogs.py→dialogs/` 分割（v1.3.0 DEBT-01）と同型の前例あり＝リスク実績が最も少ない。(a)(b) の新規プロバイダ/フォールバック作業が触るファイルなので、複雑化する前に土台を整える。 |
| 2 | `llm_config.py` | 1204行 | UI生成・検証・コスト計算が絡むがスレッド跨ぎの状態は持たない（①②のテンプレート/フォールバックUIがここに追加される前に分割し、追加作業が新旧2つの構造に分散するのを防ぐ） |
| 3 | `ocr_dialog.py` | 2154行 | 最もリスクが高い（`_render_queue`/`_worker_threads`/`_run_gen`/`_pstate`/キャンセルフラグが密結合）。かつ (a) バッチOCRが必要とする「単一ドキュメントOCR実行エンジン」の抽出と**同一作業**なので、バッチOCR着手の直前に行うのが最も手戻りが少ない。 |

### 具体的な切り出し案

**1. `ocr_providers.py` → `pagefolio/ocr_providers/` パッケージ化**
```
pagefolio/ocr_providers/
├── __init__.py     # 後方互換 re-export（from pagefolio.ocr_providers import ClaudeProvider 等を維持）
├── base.py         # OCRProvider(ABC) + OCRAPIKeyError/OCRRetryableError/OCRContextLengthError
├── lmstudio.py      # LMStudioProvider
├── claude.py        # ClaudeProvider
├── gemini.py         # GeminiProvider
├── tesseract.py      # TesseractProvider + _detect_tesseract
├── ollama.py         # OllamaProvider
└── runpod.py         # RunPodProvider
```
`dialogs/__init__.py` が既に確立した「re-export で import パスを維持する」パターンをそのまま踏襲。`ocr.py`/`ocr_pipeline.py`/テスト群からの `from pagefolio.ocr_providers import X` は無変更で動作する。

**2. `llm_config.py` → `pagefolio/dialogs/llm_config/` パッケージ化**
```
pagefolio/dialogs/llm_config/
├── __init__.py            # re-export（from pagefolio.dialogs import LLMConfigDialog 維持）
├── dialog.py               # LLMConfigDialog 本体（Toplevel・タブ/セクション構成の骨格）
├── provider_sections.py    # プロバイダ別 UI 生成（_build_claude_section 等）
├── validation.py            # _validate_* 群
├── model_fetch.py            # _fetch_models_async・モデル一覧取得
└── prompt_panel.py            # 新規: テンプレートマネージャー+フォールバック順UI（v1.8.0新規機能はここに追加。既存分割ファイルを太らせない）
```

**3. `ocr_dialog.py` → OCRRunEngine 抽出 + ocr_dialog.py 縮小**
```
pagefolio/ocr_engine.py（新規）
  OCRRunEngine: _start_worker_thread/_worker/_render_next_page/_retry_sentinels/
                provider再生成ロジックを Dialog から独立したクラスへ移動。
                コンストラクタ引数: doc, page_indices, provider, prompt, concurrency,
                                    scale, force_ocr, callbacks(on_progress/on_success/
                                    on_page_error/on_fatal/on_complete)
                起動: engine.start(after_scheduler=self.after)  # Tk の after は呼び出し元から注入
                      （ocr_engine.py 自体は tkinter を import しない設計にできると尚良いが、
                       after() 連鎖の駆動には Tk ウィジェットの after が要るため、
                       「after 関数を注入する」形にして疎結合を保つ）

pagefolio/ocr_dialog.py（縮小後）
  OCRDialog: UI構築・結果表示（Markdown整形・raw保持）・エクスポート・
             サマリ生成UI・OCRRunEngine の生成と結果コールバック配線のみ
```
この抽出により、`BatchOCRDialog`（(a)）は `OCRRunEngine` を「ファイルごとに1個ずつ生成して使い回す」だけで実装でき、producer/consumer ロジックの二重実装を避けられる。

### 分割全体のビルド順序（マイルストーンのフェーズ構成への示唆）

1. **基盤分割:** `ocr_providers.py` パッケージ化 → `llm_config.py` パッケージ化（新機能追加前に土台を整理。後方互換 import テスト `test_imports.py` 拡張必須）
2. **テンプレートマネージャー:** `settings.py` 拡張＋`llm_config/prompt_panel.py` 追加（分割後の構造にそのまま新規UIを追加できる）
3. **プロバイダフォールバック:** `provider_fallback.py` 新設＋`ocr.py`/`ocr_dialog.py` 統合＋`llm_config/prompt_panel.py` へのUI追加
4. **ocr_dialog.py 分割（OCRRunEngine 抽出）:** バッチOCR着手の直前に実施（③の直後・⑤の残り）
5. **バッチ複数ファイル OCR:** `batch_queue.py` + `dialogs/batch_ocr.py`（OCRRunEngine を再利用。milestone context 通り単独フェーズに隔離）
6. **サムネイル仮想化（PERF-01）:** `thumb_virtualizer.py` + `viewer.py` 変更。OCR系の変更と依存関係がないため、2〜5と並行して独立フェーズ化可能
7. **E2E モックテスト拡充:** OCRRunEngine/batch_queue の抽出が完了した後の方がテスト容易性が高い（Tk 非依存の純ロジック層が増えるほどモック不要な単体テストが増やせる）ため、4・5の後に厚めに配置するのが効率的

---

## Anti-Patterns（本統合で踏んではいけない失敗）

### Anti-Pattern 1: フォールバック判定を `run_parallel`/`consume_one` の中に混ぜ込む

**何をやりがちか:** ページ単位のリトライ処理（`OCRRetryableError` の指数バックオフ）と、プロバイダ丸ごと切替のフォールバックを同じ関数内で分岐させる。
**なぜ問題か:** 「一時的な429」と「プロバイダ自体が死んでいる」は意味が異なる意思決定であり、混ぜると `consume_one` が Tk 非依存の純関数でなくなり、確認ダイアログ（Tk 依存）を呼ぶ必要が出てテスト容易性が崩れる。
**代わりにすること:** フォールバックは `PipelineState.fatal_msg` が確定した**後**、UI層（Dialog/Engine の呼び出し元）でのみ判断する。

### Anti-Pattern 2: サムネイル仮想化で `pagination.py` の窓ロジックを二重実装する

**何をやりがちか:** 可視範囲計算のために独自の global index 変換をもう一つ書いてしまう。
**なぜ問題か:** CONCERNS.md が明記する「D&D の窓またぎバグ」の再発パターンそのもの（index 変換ロジックの散在）。
**代わりにすること:** 仮想化層は「窓ローカル index の可視サブレンジ」だけを返す純関数に限定し、グローバル変換は必ず既存の `pagination.to_global`/`to_local` を呼ぶ。

### Anti-Pattern 3: バッチOCRでメインウィンドウの `self.doc`/Undoスタックを共有する

**何をやりがちか:** バッチ処理を「今開いているファイルのOCR」の延長として実装し、ファイルを開くたびに `self.doc` を差し替えてしまう。
**なぜ問題か:** Undo/Redo スタック・`current_page`・サムネイルキャッシュ・世代カウンタが全てメインウィンドウの状態と衝突し、バッチ処理中にユーザーが誤操作するとメインの編集状態を破壊しうる。
**代わりにすること:** `BatchOCRDialog` は自前の `fitz.Document` インスタンスをファイルごとに開閉し、`app.doc`/Undoスタックには一切触れない完全独立ワークフローとする。

---

## Integration Points 総括

### Internal Boundaries（新規/変更コンポーネント間の連携）

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `BatchOCRDialog` ↔ `OCRRunEngine` | 直接呼び出し（ファイルごとに1個生成） | producer/consumer 中身は不変・ファイルループのみ新規 |
| `OCRDialog`/`OCRRunEngine` ↔ `provider_fallback.py` | fatal 確定後の同期呼び出し + 確認ダイアログ | 既存 `build_provider` は変更最小（`provider_override` 追加のみ） |
| `viewer.py` ↔ `thumb_virtualizer.py` | Canvas スクロールイベント→純関数呼び出し | `pagination.py` の窓契約は不変のまま外側に重ねる |
| `llm_config/prompt_panel.py` ↔ `settings.py` | テンプレート一覧/読込/保存の関数呼び出し | 既存 `load_prompt_file`/`save_prompt_file` を再利用（重複実装しない） |
| `ocr_providers/` パッケージ ↔ 既存呼び出し元 | re-export による import パス互換 | `dialogs/__init__.py` と同型パターン（v1.3.0 実績） |

### 既存原則との整合チェックリスト

- [x] fitz はメインスレッドのみ（(a)のバッチも producer は常にメインスレッド after 連鎖）
- [x] `fitz.Document` はスレッド間非共有（ワーカーには base64 のみ）
- [x] 純ロジック層（`batch_queue.py`/`provider_fallback.py`/`thumb_virtualizer.py`）は Tk/fitz 非依存
- [x] `selected_pages`/D&D の全ページ index 契約は不変（仮想化は描画層のみ）
- [x] 世代カウンタパターン（`_run_gen`/`_thumb_gen`）を新規機能でも踏襲
- [x] APIキーは settings.json へ非永続化（フォールバック順リストはプロバイダ名のみで機密情報を含まない）
- [x] 「明示設定型・自動ベンダー切替なし」を UI 確認ダイアログで構造的に担保

---

*Architecture research for: PageFolio v1.8.0 新機能統合*
*Researched: 2026-07-13*
