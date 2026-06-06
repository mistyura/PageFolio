---
phase: 04-provider-abstraction
reviewed: 2026-06-06T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - pagefolio/ocr_providers.py
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - pagefolio/__init__.py
  - pagefolio/dialogs/llm_config.py
  - pagefolio/lang.py
  - pagefolio/settings.py
  - tests/test_ocr_providers.py
  - tests/test_ocr.py
findings:
  critical: 2
  warning: 6
  info: 4
  total: 12
status: issues_found
---

# Phase 4: コードレビュー報告書

**Reviewed:** 2026-06-06
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 4 は OCR サブシステムを `OCRProvider` 抽象基底クラスと `LMStudioProvider` 実装にリファクタリングし、`build_provider` ファクトリと `run_parallel` の Provider 非依存化を導入した。スレッド安全性の中核（fitz アクセスをメインスレッドに限定し、ワーカースレッドは `provider.ocr_image` のみを呼ぶ）は概ね正しく実装されている。例外マッピング（ConnectionError / TimeoutError / RuntimeError）もテストで網羅されている。

ただし**重大な不具合が 2 件**ある。

1. **`build_provider` の `ValueError` が未捕捉で UI ハンドラを直撃する**（クラウドプロバイダ設定が混入すると OCR ボタン押下でクラッシュ）。
2. **OCR ダイアログの UI コントロール（モデル / タイムアウト / 最大トークン / 温度）が実際の OCR に反映されない**。Provider は `_start_ocr` で `settings` から一度だけ生成されてダイアログに渡され、ダイアログ内の編集はモデル送信に影響しない。後方互換の LM Studio 経路は「設定どおりに動く」が「ダイアログ上の操作は効かない」という UX バグを抱える。

その他、`run_parallel` のキャンセル時の進捗ズレ、二重 `get_text()` 呼び出し、レンダリングループの広すぎる例外捕捉など。

## Critical Issues

### CR-01: `build_provider` の `ValueError` が UI ハンドラで未捕捉

**File:** `pagefolio/ocr.py:204`（raise）／`pagefolio/ocr.py:240`（呼び出し元）
**Issue:**
`build_provider` は未対応プロバイダ名で `ValueError` を raise する。一方 `_load_settings`（`pagefolio/settings.py:45`）は `ocr_provider` のデフォルトを `"off"` としており、`build_provider` は `"off"` を LM Studio として扱うため通常は問題ない。しかし設定 JSON に `claude` / `gemini` / `tesseract`（Phase 5/6/7 想定値）や任意のタイプミス値が入っていると、`_start_ocr`（line 240）の `build_provider(self.settings)` が `ValueError` を送出する。この呼び出しは Tkinter のボタンコールバック（`_ocr_current_page` / `_ocr_selected_pages` 経由）の中で行われ、try/except で保護されていない。結果として未捕捉例外がイベントループに伝播し、OCR が無言で失敗（あるいはスタックトレースをコンソールに出すだけ）する。ユーザーには何のフィードバックも出ない。

`grep` で確認したとおり `_start_ocr` / `build_provider` 呼び出しを囲む try/except は存在しない。

**Fix:**
`_start_ocr` で `build_provider` を保護し、失敗時はユーザーに通知する。

```python
def _start_ocr(self, page_indices):
    from pagefolio.ocr_dialog import OCRDialog
    from tkinter import messagebox

    try:
        provider = build_provider(self.settings)
    except ValueError as e:
        messagebox.showerror(
            self.lang and LANG[...]["err_title"] or "Error", str(e)
        )
        return
    ...
```

または `build_provider` 側で未対応プロバイダを LM Studio にフォールバックさせ、ログ警告のみとする（後方互換重視の場合）。少なくとも UI 経路で素の例外を伝播させないこと。

### CR-02: OCR ダイアログの設定コントロールが実際の OCR に反映されない

**File:** `pagefolio/ocr.py:240-267`（provider 生成と受け渡し）／`pagefolio/ocr_dialog.py:58-66, 433-457, 537-545`
**Issue:**
`_start_ocr` は `settings` から Provider を **1 回だけ**生成し（line 240）、`OCRDialog` に `provider=provider` として渡す。`LMStudioProvider` はコンストラクタ時点の `url / model / timeout / max_tokens / temperature` をインスタンスに固定保持する（`ocr_providers.py:86-90`）。

一方 OCRDialog は `model_var` / `timeout_var` / `max_tokens_var` / `temperature_var` の編集ウィジェットをユーザーに提供する（`ocr_dialog.py:181-292`）。しかし `_on_run`（line 433-457）が UI から読み取るのは `scale`（メインスレッドのレンダリングに使用）と `timeout`（`_effective_timeout` としてエラー表示にのみ使用）だけで、**`model` / `max_tokens` / `temperature` は一切読み取られず、`run_parallel` に渡される `self.provider` も再生成されない**（line 537）。

結果:
- ダイアログでモデルを選び直しても、実際の API リクエストは `settings["lm_studio_model"]` のまま。
- 最大トークン / 温度のスピンボックスを変更しても無視される。
- タイムアウトを変更しても、エラーメッセージの「{timeout} 秒」表示は新しい値になるが、実際の HTTP タイムアウト（`provider.timeout`）は古いまま。つまり表示と実挙動が乖離する（CR-02 の中でも特に紛らわしい）。

これは「ダイアログにコントロールがあるのに効かない」というサイレントな機能不全であり、ユーザーは設定を変えたつもりで変わっていない結果を得る。

**Fix:**
`_on_run` で UI 値を読み取った後に Provider を再生成する（または build 済み settings を上書きして `build_provider` を呼び直す）。

```python
def _on_run(self):
    ...
    # UI 値で Provider を再構築（メインスレッド）
    try:
        max_tokens = max(-1, min(MAX_OCR_MAX_TOKENS, int(self.max_tokens_var.get())))
    except (tk.TclError, ValueError):
        max_tokens = -1
    try:
        temperature = max(0.0, min(2.0, float(self.temperature_var.get())))
    except (tk.TclError, ValueError):
        temperature = 0.1
    self.provider = LMStudioProvider(
        url=self.url_var.get().strip(),
        model=self.model_var.get().strip(),
        timeout=self._ocr_timeout,
        max_tokens=max_tokens,
        temperature=temperature,
    )
```

あるいは、これらのコントロールを OCR ダイアログから削除し LLM 設定ダイアログ（`llm_config.py`）に一本化する（コントロールが効かないなら表示しない方が誠実）。少なくとも「UI に出ているのに効かない」状態は解消すること。

## Warnings

### WR-01: `run_parallel` のキャンセル時に `on_progress` の `done` がスキップ分とズレる可能性

**File:** `pagefolio/ocr.py:128-166`
**Issue:**
`_call` がキャンセル/fatal 時に `("cancel", ...)` を返すと、メインループ（line 164-165）は `continue` して `done` を加算しない。一方 `as_completed` の順序は非決定的で、`status == "cancel"` の future が混じると `done` のカウントが実際の完了ページ数とズレる。`ocr_dialog._worker` の `on_progress` は `done + skipped_count` を進捗バー値に使うため（line 527-531）、キャンセル直後に進捗バーが実態より小さい値で止まる/巻き戻るように見えることがある。致命的ではないが進捗表示の正確性を損なう。
**Fix:** `cancel` ステータスでも進捗カウントの扱いを明示的に定義する（例: cancel は done に含めずバーは現状維持とコメント明記）か、`done` をループ内で「OK/err のみ加算」と統一する。現状は意図が曖昧。

### WR-02: 埋め込みテキスト判定で `get_text()` を 2 回呼ぶ

**File:** `pagefolio/ocr_dialog.py:489-493`
**Issue:**
`has_embedded_text(page)` 内部で `page.get_text()` を呼び（`ocr.py:73`）、True の場合に line 493 で再度 `page.get_text()` を呼んで抽出テキストを取得している。同一ページに対する二重レンダリング相当のコストがかかる。大きなページ・多ページ選択時に無駄が累積する（v1 スコープ外の純粋な性能問題ではなく、同一値を 2 回計算する設計上の重複）。
**Fix:** `has_embedded_text` をテキスト本体も返せる補助関数に分けるか、`_render_next_page` 側で 1 回だけ `get_text()` を呼んで文字数判定と本文取得を兼ねる。

```python
try:
    text = page.get_text()
except Exception:
    text = ""
non_ws = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
if non_ws >= EMBEDDED_TEXT_MIN_CHARS:
    self.results[page_idx] = text
    self._skipped_pages.add(page_idx)
else:
    ...
```

### WR-03: レンダリングループの `except Exception` がキャンセル/破棄エラーを誤って errors に記録

**File:** `pagefolio/ocr_dialog.py:486-502`
**Issue:**
`_render_next_page` の `try` は `page = self.doc[page_idx]` から `page_to_png_b64` までを包む。ここで `self.doc` がダイアログ破棄やドキュメントクローズと競合すると、本来のページ変換失敗ではない例外（例: ドキュメントが閉じられた後のアクセス）まで `errors[page_idx] = "image conversion error: ..."` として結果欄に「エラー」表示されてしまう。`_on_close` はレンダリング中でも `destroy()` を呼びうる（`after(0)` 連鎖が 1 ステップ残っている場合）。`_cancel_flag` チェックは line 469 にあるが、`destroy` と `after` コールバックの競合タイミング次第ですり抜ける。
**Fix:** ループ先頭の `_cancel_flag.is_set()` チェックに加え、ドキュメント有効性（`self.doc` が閉じていないか）を確認するか、`except Exception` 内で `_cancel_flag.is_set()` の場合はエラー記録せず静かに中断する。

### WR-04: `provider is None` が `run_parallel` 到達時に AttributeError を起こす

**File:** `pagefolio/ocr_dialog.py:64-66, 537-545`／`pagefolio/ocr.py:112-114`
**Issue:**
`OCRDialog.__init__` は `provider=None` をデフォルト引数として許容する（line 43, 66）。`_fetch_models` は `self.provider is None` をガードしている（line 391）が、`_on_run` → `_worker` → `run_parallel` の経路には `provider is None` ガードが無い。`run_parallel` は冒頭で `provider.default_concurrency`（`ocr.py:113`）にアクセスするため、`provider=None` のまま実行されると `AttributeError` がワーカースレッド内で発生し、UI には何も返らず無言でハングしたように見える。通常経路（`_start_ocr`）では必ず provider が渡るが、直接 `OCRDialog` を生成するテスト/プラグイン/将来コードで踏みうる契約上の穴。
**Fix:** `_on_run` 冒頭で `if self.provider is None: self.progress_var.set(...); return` を追加するか、`__init__` で `provider` 必須（デフォルト削除）にする。

### WR-05: settings デフォルト `ocr_provider="off"` が `build_provider` の分岐コメントと矛盾

**File:** `pagefolio/settings.py:45`／`pagefolio/ocr.py:192-195`
**Issue:**
`_load_settings` のデフォルトは `"ocr_provider": "off"`。`build_provider` は `name in ("lmstudio", "", "off")` を LM Studio として扱う（line 194）。コメントは「"off" は Phase 5 で UI 化。Phase 4 では LM Studio として動作」とある。意図的だが、`"off"` という値が「OCR 無効」を直感的に連想させるのに実際は LM Studio が動くため、設定ファイルを直接見たユーザー/開発者が誤解する。また将来 `"off"` を真の無効化に使う際、デフォルト値との衝突で後方互換を壊すリスクがある。
**Fix:** Phase 4 のデフォルトは `"lmstudio"`（または `""`）にし、`"off"` は Phase 5 で UI と同時に導入する。最低限、`build_provider` と `_load_settings` 双方に「"off" は暫定的に LM Studio 扱い」のコメントを揃え、変更時の注意を残す。

### WR-06: タイムアウトエラー表示の値が実際の HTTP タイムアウトと一致しない

**File:** `pagefolio/ocr_dialog.py:456, 613-623`／`pagefolio/ocr_providers.py:140`
**Issue:**
CR-02 の派生。`_on_run` は `_effective_timeout = self._ocr_timeout`（UI 値）を保存し、`_finish_error` のタイムアウトメッセージで `{timeout}` にこの UI 値を使う（line 621）。しかし実際の `urlopen` タイムアウトは `provider.timeout`（`settings["ocr_timeout"]` 由来の生成時の値）であり、ダイアログでタイムアウトを変更しても実 HTTP タイムアウトは変わらない。よってタイムアウト発生時に「{N} 秒でタイムアウト」と表示される N が、実際に待った秒数と食い違う。ユーザーの設定変更が効いていない事実が、誤った数値表示によって覆い隠される。
**Fix:** CR-02 を修正して Provider を UI 値で再生成すれば自動的に整合する。CR-02 を見送る場合でも、表示する `{timeout}` は `provider.timeout` を参照すべき。

## Info

### IN-01: `OCRProvider` クラスより後に `OCRAPIKeyError` が定義されている

**File:** `pagefolio/ocr_providers.py:16-63`
**Issue:** docstring（line 23）で `OCRProvider` の例外規約に `OCRAPIKeyError` を挙げているが、`OCRAPIKeyError` の定義は line 58 で `OCRProvider`（line 16）より後にある。実害は無い（クラス本体内で参照していないため）が、可読性のため例外クラスを基底クラスより前に置く方が自然。
**Fix:** `OCRAPIKeyError` を `OCRProvider` の前へ移動。

### IN-02: 未使用の言語キー `ocr_progress` / `ocr_progress_skip`

**File:** `pagefolio/lang.py:257, 267, 579, 589`
**Issue:** `ocr_progress` と `ocr_progress_skip` は ja/en 双方に定義されているが、`ocr_dialog.py` を grep した限り参照されていない（使われているのは `ocr_progress_init` / `ocr_progress_render` / `ocr_progress_ocr`）。デッドな辞書エントリ。
**Fix:** 使用予定がなければ削除。将来用に残すならコメントで明示。

### IN-03: `run_parallel` の `timeout` 引数が未使用

**File:** `pagefolio/ocr.py:88, 100-101`
**Issue:** `run_parallel` は `timeout=None` を受け取るが本体で一切使用せず、docstring も「未使用（Provider が内部で保持する）」と認める。シグネチャに残るデッドパラメータで、呼び出し側に誤った期待（ここで渡せば効く）を抱かせる。
**Fix:** 引数を削除するか、明示的に `# 後方互換のため受容・無視` のコメントを付ける。

### IN-04: `LMStudioProvider.__init__` の `**kwargs` 非対応で将来のファクトリ拡張に摩擦

**File:** `pagefolio/ocr_providers.py:76`／`pagefolio/ocr.py:196-202`
**Issue:** `build_provider` は LMStudio に固定キーワードを並べて生成しているが、Phase 5/6/7 でプロバイダごとに異なる引数を渡す際、各分岐で同様の定型コードが増える見込み。`ocr_image(self, b64_png, prompt, **kwargs)` は `**kwargs` を受けるが未使用（line 32, 115, 121）で、API パラメータ（temperature 等）を per-call で渡す余地が活かされていない。
**Fix:** v1 スコープ外（設計改善）。将来 per-call パラメータを `ocr_image(**kwargs)` 経由で受け渡す設計にすれば、Provider 再生成（CR-02）に頼らず温度/最大トークンを動的に変えられる。

---

_Reviewed: 2026-06-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
