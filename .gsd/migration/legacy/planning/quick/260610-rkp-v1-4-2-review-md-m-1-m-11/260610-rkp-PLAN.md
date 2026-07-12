---
phase: quick-260610-rkp
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr.py
  - pagefolio/ocr_providers.py
  - pagefolio/dialogs/llm_config.py
  - pagefolio/dialogs/settings.py
  - pagefolio/app.py
  - pagefolio/lang.py
  - pagefolio/constants.py
  - tests/test_ocr.py
  - tests/test_ocr_providers.py
  - tests/test_provider_ui.py
  - README.md
  - 開発履歴.md
  - .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md
autonomous: true
requirements: [M-1, M-2, M-3, M-4, M-5, M-6, M-7, M-8, M-9, M-10, M-11]
must_haves:
  truths:
    - "OCR 実行中にキューが満杯でもメインスレッドが busy-loop / ブロックせず、UI が凍結しない（M-1）"
    - "OCR ダイアログを実行中に閉じても旧ワーカーの after コールバックが TclError を起こさない（M-2）"
    - "effort 非対応モデル（claude-sonnet-4-5 等）に output_config.effort が送られず、未知モデルには effort も temperature も送られない（M-3）"
    - "gemini-2.5-pro 系では thinkingConfig が payload に含まれない（M-4）"
    - "Retry-After が過大値（例 86400）でも上限クランプされ、スリープ中にキャンセルが効く（M-5）"
    - "gemini-2.5-flash のコスト概算が現行価格（高め安全側）で計算される（M-6）"
    - "プラグインプロバイダのコンストラクタ例外が RuntimeError に正規化され、未処理例外にならない（M-7）"
    - "SettingsDialog 経由の LLMConfigDialog でプラグイン登録プロバイダが Combobox に出る（M-8）"
    - "ClaudeProvider レスポンスの text キー欠落ブロックで KeyError が漏れず RuntimeError 規約内に収まる（M-9）"
    - "lang=en でハードコード日本語が表示されず LANG 辞書経由になる（M-10）"
    - "except 句に Exception を含むタプル列挙が解消されている（M-11）"
  artifacts:
    - path: "pagefolio/ocr_dialog.py"
      provides: "M-1 非ブロッキング put 再スケジュール / M-2 世代ガード / M-6 コスト定数辞書 / M-10 i18n / M-11 except 簡約"
    - path: "pagefolio/ocr_providers.py"
      provides: "M-3 effort 判定厳格化 / M-4 pro 系 thinkingConfig 省略 / M-9 KeyError 対応"
    - path: "pagefolio/ocr.py"
      provides: "M-5 刻みスリープ + キャンセル確認 / M-7 プラグイン cls() 例外正規化"
    - path: "pagefolio/dialogs/settings.py"
      provides: "M-8 plugin_manager 引数追加"
    - path: "pagefolio/app.py"
      provides: "M-8 SettingsDialog へ plugin_manager 受け渡し"
    - path: "pagefolio/lang.py"
      provides: "M-10 ja/en キー追加"
  key_links:
    - from: "pagefolio/ocr_dialog.py:_render_next_page"
      to: "self.after(100, self._render_next_page)"
      via: "queue.Full 時の再スケジュール"
      pattern: "after\\(100, self\\._render_next_page\\)"
    - from: "pagefolio/app.py:_open_settings"
      to: "SettingsDialog(plugin_manager=...)"
      via: "plugin_manager の受け渡し"
      pattern: "plugin_manager\\s*="
    - from: "pagefolio/ocr_providers.py:_supports_effort"
      to: "EFFORT_MODELS"
      via: "完全一致のみで True"
      pattern: "in self\\.EFFORT_MODELS"
---

<objective>
v1.4.0 リリースレビュー（260610-aaa-REVIEW.md）の中優先度 M-1〜M-11 を v1.4.2 安定化として修正する。
スレッド/ライフサイクル系（M-1/M-2/M-5）、プロバイダ API 系（M-3/M-4/M-7/M-8/M-9）、
UI/i18n/コスト系（M-6/M-10/M-11）の 3 タスクに加え、最終タスクでバージョン更新・ドキュメント同期を行う。

Purpose: クラウド OCR の安定動作（API 400 / レート制限 / キャンセル不能 / UI 凍結）と
規約整合（i18n / except 規約）を底上げし、v1.4.2 として安全にリリースできる状態にする。
Output: 修正済みソース・回帰テスト・バージョン同期済みドキュメント。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md
@.planning/quick/260610-qqq-review-md-260610-aaa-h-1-h-5-v1-4-1/260610-qqq-SUMMARY.md
@pagefolio/ocr_dialog.py
@pagefolio/ocr.py
@pagefolio/ocr_providers.py
@pagefolio/dialogs/llm_config.py
@pagefolio/dialogs/settings.py
@pagefolio/lang.py
</context>

<interface_context>
既存コード上で本プランが触れる主要シグネチャ・契約（実行者がスカベンジャーハント不要なように明記）:

- `OCRDialog._render_next_page(self)` — メインスレッド生産者。`pagefolio/ocr_dialog.py:925`。
  現状 line 977-990 で `while True` + `put(timeout=0.1)` busy-loop。`self._render_idx` を進めて
  末尾で `self.after(0, self._render_next_page)` 連鎖。全ページ完了時 line 946-947 で `put(None)`（無タイムアウト）。
- `OCRDialog._worker(self)` — 消費者スレッド。`pagefolio/ocr_dialog.py:1012`。
  `self.after(0, ...)` でメインスレッドへコールバック（line 964/972/1063/1110/1116/1130/1136/1138/1139）。
- `OCRDialog._on_run(self)` — `pagefolio/ocr_dialog.py:774`。worker 起動前に `self._render_queue` を生成し
  `self._start_worker_thread()` → `self._render_next_page()` の順で開始（line 919-923）。
- `OCRDialog._start_worker_thread(self)` — `pagefolio/ocr_dialog.py:999`。`self.concurrency` 本の
  `threading.Thread(target=self._worker, daemon=True)` を起動。
- `OCRDialog._on_close(self)` / `_clear_text(self)` — `pagefolio/ocr_dialog.py:1228 / 481`。
- `OCRDialog._estimate_cost(self, model, page_count)` — `pagefolio/ocr_dialog.py:539`。価格を if/elif で内蔵。
  返却は line 575 の `f"約 ${cost:.3f} 程度"`。
- `OCRDialog._apply_llm_settings` の except — `pagefolio/ocr_dialog.py:690` に
  `except (ValueError, Exception) as e:`（M-11 対象）。同 line 692 に f-string ハードコード日本語（M-10 対象）。
- `ClaudeProvider._supports_effort(self)` — `pagefolio/ocr_providers.py:255`。
  `EFFORT_MODELS`（line 221、set）。現状 prefix 判定（line 267-268）が緩い。
- `ClaudeProvider._build_payload` — `pagefolio/ocr_providers.py:270`。effort（output_config）/temperature 分岐（line 297-300）。
- `ClaudeProvider.ocr_image` のレスポンス解析 — `pagefolio/ocr_providers.py:364-375`。
  `block["text"]` 直接アクセス、except は `(json.JSONDecodeError, TypeError)` のみ。
- `GeminiProvider._build_payload` — `pagefolio/ocr_providers.py:463`。`thinkingConfig` 固定（line 481）。
- `GeminiProvider.RECOMMENDED_MODELS` — `["gemini-2.5-flash", "gemini-2.5-pro"]`（line 445）。
- `OCRRetryableError.retry_after` — 例外属性（float or None）。
- リトライスリープ箇所: `ocr_dialog.py:1076`（`_time.sleep(delay)`）、`ocr.py:264`（`time.sleep(delay)`）、
  `ocr.py:406`（`time.sleep(delay)`）。いずれも `delay = e.retry_after if ... else 指数バックオフ`。
- `build_provider(settings, api_key=None, plugin_manager=None)` — `pagefolio/ocr.py:456`。
  プラグイン分岐は line 525-527: `cls = registry[name]; return cls()`（無防備・M-7 対象）。
- `LLMConfigDialog` の effort 判定 — `pagefolio/dialogs/llm_config.py:640-649`（prefix 判定残存・M-3 揃え対象）。
- `LLMConfigDialog._refresh_claude_models` / `_refresh_gemini_models` — `pagefolio/dialogs/llm_config.py:731 / 765`。
  except は `(ConnectionError, TimeoutError, RuntimeError, Exception)`（line 743 / 779・M-11 対象）。
- `SettingsDialog.__init__(self, parent, current_settings, callback, font_func=None)` —
  `pagefolio/dialogs/settings.py:19`。`_open_llm_config`（line 158）が
  `getattr(self, "_plugin_manager", None)` を渡すが `_plugin_manager` は未設定（常に None・M-8）。
- `app._open_settings` — `pagefolio/app.py:356`:
  `SettingsDialog(self.root, self.settings, self._apply_settings, self._font)`。`self.plugin_manager` 保有。
- LANG 辞書: `pagefolio/lang.py`（ja: line 8、en: line 387）。`constants.py` から再エクスポート。
  既存キー `ocr_provider_name_tesseract` / `ocr_cost_confirm_title` 等は両辞書に存在（251/251 一致）。
- ハードコード日本語（M-10 対象・lang=en でも日本語表示）:
  `ocr_dialog.py:692`（"プロバイダ再生成エラー: {e}"）、`ocr_dialog.py:575`（"約 ${cost:.3f} 程度"）、
  `llm_config.py:738`（"⏳ Claude モデル一覧を取得中…"）、`:749`/`:755`（"環境変数 ANTHROPIC_API_KEY が未設定のため静的リストを表示中"）、
  `:772`（"⏳ Gemini モデル一覧を取得中…"）、`:785`/`:792`（"環境変数 GEMINI_API_KEY/GOOGLE_API_KEY が未設定: 静的リスト表示中"）。
  ※ `:745`/`:781` の warning は logger 出力につき i18n 対象外。
- except タプル列挙（M-11 対象）: `ocr_dialog.py:690`（`(ValueError, Exception)`）、
  `llm_config.py:743`（`(ConnectionError, TimeoutError, RuntimeError, Exception)`）、`llm_config.py:779`（同上）。
</interface_context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: スレッド/ライフサイクル安定化（M-1 / M-2 / M-5）</name>
  <files>pagefolio/ocr_dialog.py, pagefolio/ocr.py, tests/test_ocr.py</files>
  <behavior>
    まず tests/test_ocr.py に RED テストを追加する（Tk 非依存に保つ・既存 fixture を踏襲・docstring は 88 字以内で E501 回避）:
    - M-5 retry_after クランプ: 新規ヘルパー `clamp_retry_after(retry_after, cap=60.0)` を pagefolio/ocr.py に
      追加し、`clamp_retry_after(86400.0)==60.0` / `clamp_retry_after(5.0)==5.0` / `clamp_retry_after(0)==0` を検証。
    - M-5 刻みスリープ + キャンセル: 新規ヘルパー `interruptible_sleep(total, is_cancelled, step=0.5)` を
      pagefolio/ocr.py に追加し、is_cancelled が途中 True を返すと total 未満で打ち切ることを検証
      （is_cancelled を呼び出し回数でフリップするモック + monkeypatch で time.sleep を no-op 化し実時間非依存に）。
    - M-1 不変条件: 「queue.Full 時に _render_idx を進めない」を最小スコープで検証する。OCRDialog は Tk 依存のため、
      既存 test_provider_ui.py の Dummy パターンに合わせるか、生産者の enqueue 判定を純関数化して検証する。
  </behavior>
  <action>
    M-1（ocr_dialog.py:_render_next_page line 925-997）: line 977-990 の `while True` + `put(timeout=0.1)` busy-loop を撤廃。
    Vision OCR ページの enqueue を `put_nowait` に変更し、`queue.Full` のときは `_render_idx` を進めず・b64 を破棄せず・
    `self.after(100, self._render_next_page)` で同一ページを再スケジュールして return する。成功時のみ
    `self._render_idx += 1` して末尾で `self.after(0, self._render_next_page)`。全ページ完了時の終了シグナル
    （line 946-947 の `self._render_queue.put(None)` ループ）も `put_nowait` + queue.Full 時 `self.after(100, ...)` 再試行へ変更し、
    無タイムアウト put でメインスレッドがブロックしないようにする。キャンセル分岐（line 931-939）の `put_nowait` は維持。
    **L-1 二重実装の確認**: ocr.py の run_with_bounded_buffer は producer を別スレッドで回す独立実装（本番未使用）のため
    M-1 の Tk after 再スケジュールは適用しない（適用対象は ocr_dialog.py のみ）。M-5 のスリープ修正は ocr.py 側にも適用する。

    M-2（ocr_dialog.py）: `__init__`（line 89 付近）に `self._run_gen = 0` を追加。`_on_run`（worker 起動直前 line 919 付近）で
    `self._run_gen += 1` し `gen = self._run_gen` をローカル捕捉。`_start_worker_thread` / `_render_next_page` / `_worker` に
    gen を伝搬する（`_worker(self, gen)` に変更し `threading.Thread(target=self._worker, args=(gen,), daemon=True)`、
    `_render_next_page` も `self.after(..., lambda g=gen: self._render_next_page(g))` 等で gen を引き回す）。
    `_worker` 内の全 `self.after(0, ...)` 投函前に `if gen != self._run_gen or not self.winfo_exists(): return`（または break）でガード。
    `_finish_complete` / `_finish_cancelled` / `_finish_error` / `_render_results_ordered` / `_on_progress_bar` の
    ウィジェット操作を `try/except tk.TclError` で保護。`_clear_text`（line 481-501）と `_on_close`（line 1228-1241）でも
    `self._run_gen += 1` し旧世代を無効化する。viewer.py の `_preview_gen` 世代ガードパターンに倣うこと。

    M-5（ocr.py / ocr_dialog.py）: pagefolio/ocr.py に `RETRY_AFTER_CAP = 60.0` 定数と
    `clamp_retry_after(retry_after, cap=RETRY_AFTER_CAP)`・`interruptible_sleep(total, is_cancelled, step=0.5)` を追加。
    リトライ待機の sleep を 3 箇所すべてで置換: (1) ocr.py:264（_consumer 内）、(2) ocr.py:406（run_parallel の _call 内）、
    (3) ocr_dialog.py:1076（_worker 内）。各箇所で retry_after 由来の delay を `clamp_retry_after(...)` で 60 秒上限に
    クランプし、`interruptible_sleep(delay, is_cancelled)` でループ内キャンセル確認に置換する
    （ocr_dialog.py 側は `is_cancelled=self._cancel_flag.is_set`、ocr.py 側は既存の `_is_cancelled` / `is_cancelled` を渡す）。
    retry_after が None の指数バックオフ経路は従来どおり（interruptible_sleep を通すだけでよい）。
    禁止事項: 裸 except 不使用（必ず `except Exception as e:`）・`# type: ignore` 無断使用禁止（CLAUDE.md）。
  </action>
  <verify>
    <automated>cd C:\Users\shdwf\work\project\PageFolio; python -m pytest tests/test_ocr.py -x -q</automated>
  </verify>
  <done>
    M-1: _render_next_page に busy-loop / 無タイムアウト put が無く put_nowait + after(100) 再スケジュールになっている
    （grep で `put(timeout=0.1)` と無タイムアウト `put(None)` のブロッキング呼び出しが消えている）。
    M-2: self._run_gen が導入され _worker の after 前に世代+winfo_exists ガードがある。
    M-5: clamp_retry_after / interruptible_sleep が ocr.py に存在し 3 箇所の sleep を置換、RED テストが GREEN。
    pytest tests/test_ocr.py 全パス。
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: プロバイダ API 堅牢化（M-3 / M-4 / M-7 / M-8 / M-9）</name>
  <files>pagefolio/ocr_providers.py, pagefolio/ocr.py, pagefolio/dialogs/llm_config.py, pagefolio/dialogs/settings.py, pagefolio/app.py, tests/test_ocr_providers.py, tests/test_provider_ui.py</files>
  <behavior>
    tests/test_ocr_providers.py に RED テストを追加:
    - M-3: `ClaudeProvider(api_key="", model="claude-sonnet-4-5")._supports_effort() is False`（EFFORT_MODELS 外）。
      `ClaudeProvider(model="claude-sonnet-4-6")._supports_effort() is True`（EFFORT_MODELS 内）。
      未知モデル `ClaudeProvider(model="claude-future-9")._build_payload(b64, "p")` に
      `"output_config" not in payload and "temperature" not in payload`。haiku は temperature を含む。
    - M-4: `GeminiProvider(api_key="", model="gemini-2.5-pro")._build_payload(b64, "p")` の generationConfig に
      `"thinkingConfig" not in cfg`。`gemini-2.5-flash` は `thinkingConfig` を含む。
    - M-9: text キー欠落ブロックを含む擬似 content を解析しても KeyError ではなく、text ありブロックのみ結合される
      （または text が皆無なら RuntimeError）。
    - M-7: build_provider のプラグイン分岐で cls() が例外を投げるダミープラグインを registry に登録した場合、
      RuntimeError に正規化される（素の例外が漏れない）。
    tests/test_provider_ui.py に M-8 回帰: `SettingsDialog.__init__` が `plugin_manager` を受け取り
    `self._plugin_manager` に保持することを検証（既存 Dummy パターンに合わせる）。
  </behavior>
  <action>
    M-3（ocr_providers.py:_supports_effort line 255-268）: prefix フォールバック（line 266-268）を撤廃し
    「effort は EFFORT_MODELS 完全一致時のみ True」に厳格化。_build_payload（line 270-301）は
    判定を `_supports_effort()`（完全一致）と `_supports_temperature()`（`"haiku" in self.model`）に分離し、
    「effort 対応→output_config / haiku→temperature / それ以外（未知モデル）→両方省略」の 3 分岐にする。
    llm_config.py:640-649 の重複 effort 判定も prefix 判定（line 647-649）を撤廃し EFFORT_MODELS 完全一致へ揃える。

    M-4（ocr_providers.py:GeminiProvider._build_payload line 463-483）: `"pro" in self.model` の場合
    generationConfig から `thinkingConfig` を省略する。flash 等は従来どおり `thinkingConfig: {thinkingBudget: 0}` を付与。

    M-7（ocr.py:build_provider line 524-528）: プラグイン分岐の `cls()` を try/except Exception で囲み、失敗時は
    `raise RuntimeError(f"プラグインプロバイダ '{name}' の初期化に失敗しました: {e}") from e` に正規化。
    build_provider の docstring に「プラグインプロバイダは引数なしコンストラクタ `cls()` で実体化する契約」を追記。

    M-8（dialogs/settings.py / app.py）: `SettingsDialog.__init__`（settings.py:19）に `plugin_manager=None` 引数を追加し
    `self._plugin_manager = plugin_manager` を設定（_open_llm_config line 173 の `getattr(self, "_plugin_manager", None)` が
    実体を返すようになる）。app.py:358 の `SettingsDialog(self.root, self.settings, self._apply_settings, self._font)` を
    `plugin_manager=getattr(self, "plugin_manager", None)` を渡す形に更新。

    M-9（ocr_providers.py:ClaudeProvider.ocr_image line 364-375）: `block["text"]` を `block.get("text")` に変更し
    None を除外（`if block.get("type") == "text" and block.get("text")`）、または except に KeyError を追加。
    text が一つも取れなければ既存どおり RuntimeError を送出する。
    禁止事項: 裸 except 不使用・規約遵守。
  </action>
  <verify>
    <automated>cd C:\Users\shdwf\work\project\PageFolio; python -m pytest tests/test_ocr_providers.py tests/test_provider_ui.py -x -q</automated>
  </verify>
  <done>
    M-3: _supports_effort が EFFORT_MODELS 完全一致のみ True、未知モデルの payload に effort/temperature 不在。
    M-4: pro 系 payload に thinkingConfig 不在。M-7: プラグイン cls() 例外が RuntimeError 正規化。
    M-8: SettingsDialog に plugin_manager 引数があり app.py から渡される。M-9: text 欠落で KeyError 非伝播。
    pytest tests/test_ocr_providers.py tests/test_provider_ui.py 全パス。
  </done>
</task>

<task type="auto">
  <name>Task 3: UI / i18n / コスト整合（M-6 / M-10 / M-11）</name>
  <files>pagefolio/ocr_dialog.py, pagefolio/dialogs/llm_config.py, pagefolio/lang.py</files>
  <action>
    M-6（ocr_dialog.py:_estimate_cost line 539-575）: モジュール定数辞書 `OCR_PRICE_TABLE`
    （例: `{"gemini-2.5-flash": (0.30, 2.50), "gemini-2.5-pro": (1.25, 10.0), "claude-haiku": (1.0, 5.0),
    "claude-sonnet": (3.0, 15.0), "claude-opus": (5.0, 25.0)}`、値は (input_$/MTok, output_$/MTok)）を定義し、
    _estimate_cost の if/elif 数値直書きを辞書引き + フォールバック（不明モデルは opus 単価 = 高め安全側）へ置換。
    gemini-2.5-flash の単価を現行実勢の高め（入力 $0.30 / 出力 $2.50 程度）に更新し「課金警告として安全側
    （過小評価しない）」を担保。各単価にモデル名コメントを併記。返却文字列（line 575）は M-10 で i18n 化する。

    M-10（lang.py / ocr_dialog.py / llm_config.py）: ハードコード日本語を LANG 辞書（pagefolio/lang.py の
    ja line 8 / en line 387 両方）へ移す。新規キーは ja/en 両方に同一キーで追加し既存のキー数左右一致を崩さない:
    - `ocr_cost_estimate`（"約 ${cost} 程度" / "approx. ${cost}"）→ _estimate_cost 返却（ocr_dialog.py:575）。
    - `ocr_provider_rebuild_error`（"プロバイダ再生成エラー: {error}" / "Provider rebuild error: {error}"）→ ocr_dialog.py:692。
    - `llm_fetching_claude_models` / `llm_fetching_gemini_models`（"⏳ Claude モデル一覧を取得中…" 等の対訳）→ llm_config.py:738 / 772。
    - `llm_env_key_unset_static`（ANTHROPIC 用）/ `llm_env_key_unset_static_gemini`（GEMINI/GOOGLE 用）
      → llm_config.py:749/755 と 785/792。
    - `llm_model_fetch_failed`（"モデル取得に失敗しました: {error}" / "Failed to fetch models: {error}"）。
    REVIEW 指摘どおり「通信失敗でも『未設定』と表示する誤誘導」を避けるため、env キー未設定文言（キーが本当に無い場合）と
    取得失敗文言（`llm_model_fetch_failed`）を分離し、except 側（M-11 と同じ箇所）は取得失敗文言を表示するよう差し替える。
    各 `self._set_lm_status(...)` / 返却文字列を `self._L["<key>"].format(...)` に置換する。

    M-11（ocr_dialog.py / llm_config.py）: `except (ValueError, Exception) as e:`（ocr_dialog.py:690）と
    `except (ConnectionError, TimeoutError, RuntimeError, Exception) as e:`（llm_config.py:743, 779）を、意図どおりの全捕捉
    `except Exception as e:` に簡約する。except 内のロジック（フォールバック・logger・ステータス表示）は維持し、
    M-10 の文言差し替え（except 側を取得失敗文言へ）と同一ブロックを整合させる。
    禁止事項: 裸 except（`except:`）にはしない・必ず `except Exception as e:` 形。
  </action>
  <verify>
    <automated>cd C:\Users\shdwf\work\project\PageFolio; python -m pytest tests/test_imports.py tests/test_provider_ui.py -x -q; python -c "from pagefolio.lang import LANG; assert set(LANG['ja'])==set(LANG['en']); print('LANG keys OK', len(LANG['ja']))"</automated>
  </verify>
  <done>
    M-6: OCR_PRICE_TABLE 定数辞書が存在し _estimate_cost が辞書引き、gemini-2.5-flash 単価が高め安全側に更新。
    M-10: 対象 8 箇所のハードコード日本語が LANG 辞書経由になり ja/en キー数が一致、env 未設定文言と取得失敗文言が分離。
    M-11: except タプル列挙（Exception 含む）が except Exception as e: に簡約。
    pytest tests/test_imports.py tests/test_provider_ui.py 全パス・LANG ja/en キー一致。
  </done>
</task>

<task type="auto">
  <name>Task 4: バージョン更新・ドキュメント同期・品質ゲート（v1.4.2）</name>
  <files>pagefolio/constants.py, README.md, 開発履歴.md, .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md</files>
  <action>
    全 M 項目の修正完了後にバージョンを v1.4.2 へ更新する。
    1. pagefolio/constants.py の `APP_VERSION` を `1.4.2`（v1.4.1 の表記形式を踏襲）へ更新。
       v1.4.1 SUMMARY では constants.py の APP_VERSION を更新済みのため同一箇所を更新すること。
    2. README.md のバージョンバッジを v1.4.2 に更新。
    3. 開発履歴.md の先頭へ v1.4.2 エントリを追記（CLAUDE.md の記載ルールに従い M-1〜M-11 の修正概要を日本語で列挙）。
    4. .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md の「中優先度（M）」各見出し（M-1〜M-11）末尾に
       完了マーク（✅）と「対応済み（v1.4.2 / commit: <ハッシュ>）」行を追記する（H-1〜H-5 の既存記載フォーマットに揃える）。
       commit ハッシュは Task 1〜3 の各コミット or 本タスクの最終コミットを参照する。
    5. 最終品質ゲートを実行: `ruff check . && ruff format .`（差分が出たら再フォーマットして再確認）、`pytest`（全件パス）。
       E501 等の lint 違反（v1.4.1 で発生した日本語 docstring 行長超過）に注意。
    バージョン同期 3 点（APP_VERSION / README バッジ / 開発履歴.md 先頭）が一致していることを確認すること
    （CLAUDE.md「バージョン番号は constants.py の APP_VERSION を真の情報源とする」）。
  </action>
  <verify>
    <automated>cd C:\Users\shdwf\work\project\PageFolio; ruff check .; ruff format --check .; python -m pytest -q</automated>
  </verify>
  <done>
    APP_VERSION=1.4.2・README バッジ・開発履歴.md 先頭エントリが v1.4.2 で一致。
    REVIEW.md の M-1〜M-11 全項目に ✅ + commit 追記済み。
    ruff check / format --check 全パス・pytest 全件パス。
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| OCRDialog（メインスレッド）→ ワーカースレッド | render 済み b64 のみ受け渡し（fitz 非共有・D-04） |
| アプリ → クラウド OCR API（Anthropic / Gemini） | ページ画像 base64 が外部 https 送信される |
| アプリ → プラグインプロバイダ | サードパーティ cls() コードを実体化・実行 |
| サーバ → アプリ（Retry-After ヘッダ） | サーバ制御の sleep 秒数（過大値で凍結リスク） |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-rkp-01 | Denial of Service | Retry-After 無検証 sleep（ocr.py / ocr_dialog.py） | mitigate | M-5: clamp_retry_after で 60 秒上限・interruptible_sleep でキャンセル可能化 |
| T-rkp-02 | Denial of Service | producer ブロッキング put（ocr_dialog.py） | mitigate | M-1: put_nowait + after(100) 再スケジュールで UI 凍結を排除 |
| T-rkp-03 | Tampering / Elevation | プラグイン cls() 実体化（ocr.py:build_provider） | mitigate | M-7: try/except Exception で RuntimeError 正規化・未処理例外を防止 |
| T-rkp-04 | Information Disclosure | 抽出テキスト / API キーのログ混入 | accept | 既存ガード（_SENSITIVE_KEYS・抽出テキスト非ログ）を維持・本プランで新規流入なし |
| T-rkp-SC | Tampering | npm/pip 等パッケージ install | accept | 新規依存追加なし（標準ライブラリ + 既存依存のみ）・install タスクなし |
</threat_model>

<verification>
- 各タスクの <verify> automated が GREEN。
- 全体: `ruff check .` / `ruff format --check .` 全パス、`pytest` 全件パス（v1.4.1 時点 405 件 + 本プラン追加分）。
- grep 確認: `_render_next_page` に `put(timeout=0.1)` busy-loop と無タイムアウト `put(None)` が残っていない。
- grep 確認: `except (` で Exception を含むタプル列挙が ocr_dialog.py / llm_config.py に残っていない。
- LANG ja/en キー数一致（`set(LANG['ja']) == set(LANG['en'])`）。
- バージョン同期 3 点一致（APP_VERSION / README バッジ / 開発履歴.md）。
</verification>

<success_criteria>
- M-1〜M-11 の 11 項目すべてが REVIEW.md の対応方針どおりに修正され、✅ + commit が追記されている。
- L-1 二重実装（ocr.py の run_with_bounded_buffer / ocr_dialog.py 独自実装）の両方への M-1/M-2/M-5 影響を確認済み
  （M-5 のスリープ修正は両者に適用、M-1 の Tk after 再スケジュールは ocr_dialog.py 側のみ）。
- 回帰テスト（RED→GREEN）が追加され pytest 全件パス、ruff 全パス。
- APP_VERSION=1.4.2 で 3 点同期。すべての成果物が日本語で記述されている。
</success_criteria>

<output>
Create `.planning/quick/260610-rkp-v1-4-2-review-md-m-1-m-11/260610-rkp-SUMMARY.md` when done
</output>
