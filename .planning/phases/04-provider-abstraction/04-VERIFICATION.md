---
phase: 04-provider-abstraction
verified: 2026-06-06T00:00:00Z
status: gaps_found
score: 3/4 must-haves verified
overrides_applied: 0
gaps:
  - truth: "LM Studio で OCR を実行したとき、v1.3.0 と同じ結果・同じ UI 操作で完了する（後方互換）"
    status: partial
    reason: |
      OCR 結果自体（テキスト抽出）は settings の初期値で動作し形式的に取得できる。しかし v1.3.0 では
      _worker 内で model_var.get() / max_tokens_var.get() / temperature_var.get() を読み取り
      call_lm_studio_parallel へ渡していた（git show e2b2ecb で確認）。Phase 4 リファクタ後は
      _on_run が scale_var / timeout_var のみを読み取り、model / max_tokens / temperature は
      _start_ocr 時点の settings 値に固定される。ダイアログ上のコントロールで変更しても OCR の
      HTTP リクエストには反映されない（CR-02）。表示タイムアウト値と実 HTTP タイムアウトの乖離も発生。
      「同じ UI 操作で完了する」という後方互換が実質的に破れている。
      なお build_provider が ValueError を投げる経路（未対応プロバイダ名の settings 値）については
      _start_ocr に try/except がなく未捕捉のまま Tkinter コールバックに伝播するが（CR-01）、
      デフォルト設定（ocr_provider: "off" → LM Studio 動作）では発生しないため Phase 4 スコープ
      での通常動作は保護されている。
    artifacts:
      - path: "pagefolio/ocr_dialog.py"
        issue: "_on_run が model_var / max_tokens_var / temperature_var を読み取らない。
          _on_run → _render_next_page → _start_worker_thread のパイプライン内で
          self.provider を再生成しないため、ダイアログでモデルを変えても API リクエストに反映されない"
      - path: "pagefolio/ocr.py"
        issue: "_start_ocr の build_provider 呼び出しが try/except で保護されていない（CR-01）。
          settings に 'claude' 等の未対応値が入ると ValueError が Tkinter イベントループに伝播する"
    missing:
      - "_on_run で model_var / max_tokens_var / temperature_var を読み取り、LMStudioProvider を
        再生成するか、またはダイアログの実行前に provider を更新する処理を追加する"
      - "_start_ocr 内の build_provider 呼び出しを try/except ValueError で保護し、ユーザーに
        エラーメッセージ（messagebox.showerror）を表示して return する"
human_verification:
  - test: "ダイアログでモデルを変更してから「読み取り実行」を押し、LM Studio のログで実際に送信された model フィールドを確認する"
    expected: "ダイアログで選択したモデル名が HTTP リクエストの model フィールドに反映されている"
    why_human: "HTTP リクエストの内容を確認するには実際の LM Studio サーバへの接続が必要"
  - test: "ダイアログでタイムアウトを変更して接続を切った LM Studio に対して OCR を実行し、表示メッセージのタイムアウト秒数と実際の待機時間を比較する"
    expected: "表示される「{N}秒でタイムアウト」の N と実際の HTTP タイムアウト秒が一致する"
    why_human: "実際の HTTP タイムアウト挙動の確認は実環境での動作が必要"
---

# Phase 4: プロバイダ抽象化 検証レポート

**フェーズゴール:** プロバイダを差し替え可能にする土台が整い、LM Studio が従来どおり動作する
**検証日時:** 2026-06-06
**ステータス:** gaps_found
**再検証:** No — 初回検証

## ゴール達成状況

### 観測可能な真実（ROADMAP 成功基準）

| # | 真実 | ステータス | 根拠 |
|---|------|-----------|------|
| 1 | LM Studio で OCR を実行したとき、v1.3.0 と同じ結果・同じ UI 操作で完了する（後方互換） | PARTIAL | OCR テキスト取得自体は動作するが、ダイアログで変更した model / max_tokens / temperature が API リクエストに反映されない（v1.3.0 では _worker 内で UI 値を読み取り反映していた。git show e2b2ecb で確認）。CR-02。 |
| 2 | テキストが埋め込まれたページに OCR を実行したとき、API 呼び出しが行われずに page.get_text() の結果が返される | VERIFIED | _render_next_page が has_embedded_text(page) で判定し、True なら page.get_text() を results に投入し _ocr_page_indices に追加しない。_worker の run_parallel には埋め込みページが渡されない。 |
| 3 | ワーカースレッド内で fitz.Document / get_pixmap() の直接呼び出しが一切存在しない（スレッド境界が明確） | VERIFIED | 正規表現で _worker メソッド本体（513-560行）を抽出し get_pixmap / self.doc[ / page_to_png_b64 の不在を自動検証済み。これらは _render_next_page（メインスレッド）にのみ存在する。 |
| 4 | 新しいプロバイダクラスをファイルに追加するだけで run_parallel() から呼び出せる（プロバイダ別並列度が受け取れる） | VERIFIED | OCRProvider 抽象基底（ocr_image / list_models 抽象メソッド / default_concurrency / max_concurrency クラス属性）が定義され、run_parallel は provider.ocr_image と provider.max_concurrency のみに依存する。LMStudioProvider 以外の OCRProvider サブクラスを追加するだけで結線できる。 |

**スコア:** 3/4 真実を検証済み（SC-1 が PARTIAL のため gaps_found）

### 必須アーティファクト

| アーティファクト | 期待内容 | ステータス | 詳細 |
|----------------|---------|-----------|------|
| `pagefolio/ocr_providers.py` | OCRProvider / OCRAPIKeyError / LMStudioProvider | VERIFIED | 193行。`class OCRProvider(abc.ABC)` / `class OCRAPIKeyError(RuntimeError)` / `class LMStudioProvider(OCRProvider)` が存在。fitz / tkinter の import なし。 |
| `pagefolio/ocr.py` | run_parallel / has_embedded_text / build_provider / 改修後 OCRMixin | VERIFIED | run_parallel（82行）/ has_embedded_text（58行）/ build_provider（178行）が存在。LM Studio 固有関数（build_chat_payload / call_lm_studio / fetch_lm_studio_models）は削除済み。 |
| `pagefolio/ocr_dialog.py` | スレッド境界リファクタ済み OCRDialog | PARTIAL | run_parallel の結線・has_embedded_text の結線・self.provider の保持は実装済み。ただし _on_run が model_var / max_tokens_var / temperature_var を読み取らず provider を再生成しないため CR-02 が残存。 |
| `pagefolio/lang.py` | ocr_text_skip_notice（日英） | VERIFIED | ja: 266行 / en: 588行 に {page} プレースホルダ付きで存在。 |
| `pagefolio/settings.py` | ocr_provider デフォルト "off" | VERIFIED | 45行 `"ocr_provider": "off"` が defaults dict に存在。 |
| `tests/test_ocr_providers.py` | OCRProvider / LMStudioProvider テスト群 | VERIFIED | 23テストケース全通過。 |

### キーリンク検証

| From | To | Via | ステータス | 詳細 |
|------|----|-----|-----------|------|
| `pagefolio/ocr_providers.py` | LM Studio /v1/chat/completions | urllib.request.urlopen (LMStudioProvider.ocr_image) | WIRED | 130行 `endpoint = self.url.rstrip("/") + "/v1/chat/completions"` 確認済み |
| `pagefolio/ocr_providers.py` | LM Studio /v1/models | urllib.request.urlopen (LMStudioProvider.list_models) | WIRED | 173行 `endpoint = self.url.rstrip("/") + "/v1/models"` 確認済み |
| `pagefolio/ocr.py run_parallel` | OCRProvider.ocr_image | provider.ocr_image(b64, prompt) を ThreadPoolExecutor で per-page 呼び出し | WIRED | 133行 `text = provider.ocr_image(b64, prompt)` 確認済み |
| `pagefolio/ocr.py build_provider` | pagefolio.ocr_providers.LMStudioProvider | ocr_provider 設定値に基づくファクトリ生成 | WIRED | 196行 `return LMStudioProvider(...)` 確認済み。"lmstudio"/""/""off"" を LM Studio として処理。 |
| `pagefolio/ocr.py OCRMixin._start_ocr` | OCRDialog(provider=...) | build_provider 結果を OCRDialog へ受け渡し | WIRED | 240行 `provider = build_provider(self.settings)` / 264行 `provider=provider` 確認済み |
| `pagefolio/ocr_dialog.py _worker` | pagefolio.ocr.run_parallel | フェーズ2 の API 並列送信を run_parallel(provider, ...) に置換 | WIRED | 537行 `results, errors, fatal_msg, fatal_kind = run_parallel(self.provider, ...)` 確認済み |
| `pagefolio/ocr_dialog.py メインスレッド側` | pagefolio.ocr.has_embedded_text / page_to_png_b64 | レンダリング前にメインスレッドで埋め込み判定 + レンダリング | WIRED | _render_next_page（464行）が has_embedded_text / page_to_png_b64 を呼ぶ |
| `pagefolio/ocr_dialog.py` | OCRProvider (provider 引数) | __init__ で provider を受け取り list_models / run_parallel に使う | WIRED | 42行 `provider=None` 引数 / 66行 `self.provider = provider` 確認済み |

### データフロートレース（Level 4）

| アーティファクト | データ変数 | ソース | 実データが流れるか | ステータス |
|---------------|-----------|-------|-----------------|-----------|
| `OCRDialog._worker → run_parallel` | self.provider | _start_ocr の build_provider（settings 由来） | settings から LMStudioProvider を生成 | FLOWING（初期値のみ） |
| `OCRDialog._on_run → provider` | model / max_tokens / temperature | ダイアログ UI コントロール（model_var 等） | 読み取られない | HOLLOW — ダイアログで変更しても反映されない（CR-02） |

### 行動スポットチェック

| 動作 | コマンド | 結果 | ステータス |
|------|---------|------|-----------|
| OCRProvider / OCRAPIKeyError 基本構造 | `python -c "from pagefolio.ocr_providers import OCRProvider, OCRAPIKeyError, LMStudioProvider; ..."` | OK | PASS |
| run_parallel / has_embedded_text / build_provider インポート | `python -c "from pagefolio.ocr import run_parallel, has_embedded_text, build_provider; ..."` | import OK, build_provider OK | PASS |
| _worker 内の fitz アクセスゼロ | `python -c "import ast,re; ... body=_worker_body; assert 'get_pixmap' not in body; ..."` | OK: _worker is clean | PASS |
| lang / settings の追加確認 | `python -c "from pagefolio.constants import LANG; ...assert d.get('ocr_provider')=='off'; ..."` | lang/settings OK | PASS |
| 全テストスイート | `venv/Scripts/python -m pytest -q` | 231 passed | PASS |
| build_provider に未対応プロバイダ名を渡す | `python -c "from pagefolio.ocr import build_provider; build_provider({'ocr_provider': 'claude'})"` | ValueError が投げられる（未捕捉） | FAIL（CR-01: _start_ocr に try/except なし） |
| _on_run が model_var を読み取るか | AST 解析 `_on_run` メソッドの参照確認 | model_var: False, max_tokens_var: False, temperature_var: False | FAIL（CR-02） |

### 要件カバレッジ

| 要件 ID | フェーズ | 説明 | ステータス | 根拠 |
|---------|---------|------|-----------|------|
| OCR-PROV-01 | Phase 4 | OCRProvider 抽象基底クラスを定義し共通インターフェースを持つ | SATISFIED | OCRProvider(abc.ABC) / ocr_image / list_models / default_concurrency / max_concurrency が存在 |
| OCR-PROV-02 | Phase 4 | 既存 LM Studio OCR を LMStudioProvider 実装へリファクタし後方互換を維持 | PARTIAL | LMStudioProvider 実装は完成しているが、ダイアログ UI コントロールの変更が OCR に反映されない点で後方互換に欠陥がある（CR-02） |
| OCR-PROV-03 | Phase 4 | run_parallel() をプロバイダ非依存に一般化し、プロバイダ別の並列度を受け取れるようにする | SATISFIED | run_parallel(provider, ...) が provider.ocr_image と provider.max_concurrency で動作。FakeProvider テストで多様なプロバイダ型を確認。 |
| OCR-PERF-01 | Phase 4 | テキストが埋め込まれたページは page.get_text() の結果を採用し Vision API 呼び出しをスキップする | SATISFIED | has_embedded_text(page) でメインスレッド側判定し、_ocr_page_indices から除外。_worker の run_parallel には渡されない。 |

### アンチパターン検出

| ファイル | 行 | パターン | 重大度 | 影響 |
|---------|-----|---------|--------|------|
| `pagefolio/ocr_dialog.py` | 433-462 | _on_run が model_var / max_tokens_var / temperature_var を読み取らない | WARNING | ダイアログ上のコントロール変更が OCR リクエストに反映されない（CR-02）。v1.3.0 動作と乖離。 |
| `pagefolio/ocr.py` | 240 | _start_ocr 内の build_provider が try/except で保護されていない | WARNING | 未対応 ocr_provider 設定値（"claude" 等）で ValueError が Tkinter コールバックに素通り（CR-01）。デフォルト設定では発生しない。 |
| `pagefolio/lang.py` | 257, 267, 579, 589 | ocr_progress / ocr_progress_skip が定義されているが ocr_dialog.py で参照されていない | INFO | デッドな辞書エントリ（IN-02）。機能への影響なし。 |
| `pagefolio/ocr.py` | 88 | run_parallel の timeout 引数が受け取られるが使われない | INFO | デッドパラメータ。呼び出し側に誤った期待を持たせる可能性（IN-03）。 |

TBD / FIXME / XXX マーカー: 変更対象ファイル5件すべてで 0 件。

### 人手検証が必要な項目

#### 1. ダイアログでのモデル変更反映確認

**テスト:** LM Studio を起動した状態でモデル一覧を取得し、ダイアログで別のモデルを選択して「読み取り実行」を押す
**期待値:** LM Studio のログで実際に送信された model フィールドがダイアログで選択したモデル名になっている
**人手が必要な理由:** HTTP リクエストの内容確認は実際の LM Studio サーバへの接続が必要

#### 2. タイムアウト表示と実挙動の一致確認

**テスト:** タイムアウトを意図的に短い値（例: 10秒）に変更し、応答の遅い LM Studio に対して OCR を実行する
**期待値:** 表示されるタイムアウトエラーメッセージの秒数が実際に待機した秒数と一致する
**人手が必要な理由:** 実際の HTTP タイムアウト挙動は実環境での動作確認が必要

## ギャップまとめ

**ブロッカー判定:** 成功基準1（後方互換）が PARTIAL。

v1.3.0 の `_worker` はダイアログ UI から `model_var.get()` / `max_tokens_var.get()` / `temperature_var.get()` を読み取り OCR リクエストに反映していた（`git show e2b2ecb:pagefolio/ocr_dialog.py:441-457` で確認）。Phase 4 リファクタ後は `_on_run` が `scale_var` と `timeout_var` しか読み取らず、`self.provider` も再生成しない。OCR テキスト取得という**結果**は得られるが、**「同じ UI 操作で完了する」**という挙動の後方互換が破れている。

**修正方針:**
1. `_on_run` 内で `model_var` / `max_tokens_var` / `temperature_var` を読み取り、`self.provider` を `LMStudioProvider(...)` で再生成する（CR-02 の修正案どおり）
2. `_start_ocr` 内の `build_provider` 呼び出しを `try/except ValueError` で保護し、`messagebox.showerror` でユーザーに通知して `return` する（CR-01 の修正案どおり）

---

_検証日時: 2026-06-06_
_検証者: Claude (gsd-verifier)_
