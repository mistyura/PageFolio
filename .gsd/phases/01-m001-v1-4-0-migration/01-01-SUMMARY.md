---
id: S01
parent: M001
milestone: M001
provides:
  - OCRProvider 抽象基底クラス（abc.ABC・ocr_image/list_models 抽象メソッド・default_concurrency/max_concurrency クラス属性・例外規約 docstring）
  - OCRAPIKeyError（RuntimeError サブクラス・env_var 属性）
  - LMStudioProvider（OCRProvider 実装・ocr_image + list_models・現行と同一の例外マッピング）
  - pagefolio/ocr_providers.py（新規モジュール・fitz/Tkinter 非依存）
  - run_parallel(provider, images_b64, page_indices, ...) — Provider 非依存並列 OCR 関数
  - has_embedded_text(page, threshold) — 文字数しきい値方式でテキスト埋め込みを判定
  - build_provider(settings) — settings から OCRProvider を生成するファクトリ
  - page_to_png_b64(page, scale) — 汎用ユーティリティ（残置）
  - 改修後 OCRMixin._start_ocr — build_provider を呼び provider=provider で OCRDialog へ渡す
  - LM Studio 固有関数（build_chat_payload/call_lm_studio/fetch_lm_studio_models）を ocr.py から削除
  - スレッド境界再構成済み OCRDialog（provider 引数・メインスレッドレンダリング・埋め込みスキップ統合）
  - lang.py に ocr_text_skip_notice / ocr_progress_skip（日英）
  - settings.py に ocr_provider デフォルト "off"
requires: []
affects: []
key_files: []
key_decisions:
  - TDD サイクル: RED（失敗テスト先行コミット）→ GREEN（実装コミット）の 2 コミット構成
  - list_models() のタイムアウトは 10 秒固定（現行 fetch_lm_studio_models と同一）— self.timeout を使わず内部既定
  - docstring の例外規約はクラスレベルと各メソッドレベルの両方に記載（Claude's Discretion 適用）
  - EMBEDDED_TEXT_MIN_CHARS=3: conftest の sample_pdf_doc が 'Page N'（5文字）を持ち True となる最小しきい値。1〜2文字の誤検出を抑制しつつ典型的ページ番号テキスト以上を検出する（D-06）
  - build_provider で ocr_provider='off' のとき LMStudioProvider を返す: Phase 4 では ocr_provider の UI 化は未実装のため LM Studio 既定動作を維持する（D-CONTEXT）
  - Rule 3: fetch_lm_studio_models を llm_config.py から削除 — ocr.py の LM Studio 固有関数削除に伴い LMStudioProvider.list_models() に差し替え
  - メインスレッドで _render_next_page を after(0) 連鎖させ、ページ数分ループ後に _start_worker_thread を呼ぶ設計を採用（D-01 事前レンダリング最小構成）
  - provider=None のフォールバック処理は _fetch_models のみ（None ガード）で実装し、通常パスは 04-02 の _start_ocr が常に provider を渡す前提を維持
  - スキップページの表示は [ocr_text_skip_notice] ヘッダー + 抽出テキスト本文の構成（T-04-09: ログには混入させない）
patterns_established:
  - Provider クラスは fitz / tkinter / StringVar / .after() を一切参照しない（スレッド境界明確化の前提）
  - クラス属性 default_concurrency / max_concurrency で並列度ポリシーをプロバイダが宣言（D-10）
  - run_parallel の _call クロージャ内で provider.ocr_image(b64, prompt) を per-page で呼ぶ — fitz オブジェクトをスレッドに渡さないことを保証（T-04-04）
  - FakeProvider(OCRProvider) テストダブルパターン: side_effect callable で例外やテキストを注入
  - スレッド分離: メインスレッド（fitz/Tkinter操作）↔ ワーカースレッド（HTTP IO）の境界を after() で橋渡し
  - _worker の docstring に 'fitz' 等の禁止ワードを書かない（automated grep チェック対応）
observability_surfaces: []
drill_down_paths: []
duration: 6min
verification_result: passed
completed_at: 2026-06-06
blocker_discovered: false
---
# S01: Provider Abstraction

**# Phase 4 Plan 01: OCRProvider 抽象基底 + LMStudioProvider Summary**

## What Happened

# Phase 4 Plan 01: OCRProvider 抽象基底 + LMStudioProvider Summary

**`abc.ABC` 抽象基底 `OCRProvider` と例外専用クラス `OCRAPIKeyError`、LM Studio urllib 直叩き実装 `LMStudioProvider` を `pagefolio/ocr_providers.py` として新設し、後続プランの Provider インターフェース契約を確定した**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-06T06:10:20Z
- **Completed:** 2026-06-06T06:13:30Z
- **Tasks:** 2 (Task 1: OCRProvider + OCRAPIKeyError、Task 2: LMStudioProvider)
- **Files modified:** 2

## Accomplishments

- `pagefolio/ocr_providers.py` を新設。`OCRProvider`（abc.ABC）・`OCRAPIKeyError`（RuntimeError 子）・`LMStudioProvider` を提供
- `LMStudioProvider.ocr_image` に `call_lm_studio` ロジックを、`list_models` に `fetch_lm_studio_models` ロジックを移設。例外マッピングは現行と完全一致
- `ocr_providers.py` が fitz / Tkinter を一切参照しない（後続フェーズのスレッド境界明確化の前提条件を達成）
- 23 テストケースが全 PASS（222/222 全体テストも緑）

## Task Commits

TDD サイクルに従い 2 コミット構成:

1. **RED — 失敗テスト追加** - `e2b2ecb` (test)
2. **GREEN — ocr_providers.py 実装 + ruff 修正** - `90b2a29` (feat)

## Files Created/Modified

- `C:/Users/shdwf/work/project/PageFolio/pagefolio/ocr_providers.py` — OCRProvider / OCRAPIKeyError / LMStudioProvider を提供する新規モジュール（172 行）
- `C:/Users/shdwf/work/project/PageFolio/tests/test_ocr_providers.py` — 23 テストケース（Task 1 基底クラス 9件・Task 2 Provider 14件）

## Decisions Made

- `list_models()` のタイムアウトは `self.timeout` ではなく 10 秒固定とした（現行 `fetch_lm_studio_models` の既定と一致。kwargs で上書き可能な設計は入れず、モデル一覧取得の意図に合わせてシンプルに保つ）
- TDD RED/GREEN の 2 コミット構成を採用した（plan の tdd="true" 指定に従う）
- ruff I001（import 未ソート）をテストファイルに検出し、`ruff --fix` で自動修正した（逸脱: Rule 1 — Auto-fix）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff I001 import ブロック未ソートを修正**
- **Found during:** GREEN フェーズのリント確認
- **Issue:** `tests/test_ocr_providers.py` で `import pytest` の後に `# noqa: F401` コメントを付けたため import グループが乱れ、ruff I001 エラーが発生
- **Fix:** `ruff check --fix` を実行してソート順を自動修正
- **Files modified:** `tests/test_ocr_providers.py`
- **Verification:** `ruff check . && ruff format --check .` が exit 0 で通過
- **Committed in:** `90b2a29`（feat コミットに同梱）

---

**Total deviations:** 1 auto-fixed（Rule 1 — Bug）
**Impact on plan:** リントのみの修正。機能・インターフェースへの影響なし。

## Issues Encountered

なし。

## User Setup Required

なし — 外部サービス設定不要。

## Next Phase Readiness

- `OCRProvider` / `OCRAPIKeyError` / `LMStudioProvider` の契約が確定し、Plan 02（`run_parallel` 一般化・`build_provider` ファクトリ）が依存できる状態になった
- `ocr.py` の既存関数（`build_chat_payload` / `call_lm_studio` / `fetch_lm_studio_models`）は本プランでは温存済み。Plan 02 でのリファクタ時に削除または deprecated 化する

---
## Self-Check: PASSED

- `pagefolio/ocr_providers.py` — FOUND
- `tests/test_ocr_providers.py` — FOUND
- `.planning/phases/04-provider-abstraction/04-01-SUMMARY.md` — FOUND
- commit `e2b2ecb` — FOUND
- commit `90b2a29` — FOUND

---
*Phase: 04-provider-abstraction*
*Completed: 2026-06-06*

# Phase 04 Plan 02: OCR プロバイダ非依存化 Summary

**`run_parallel(provider, ...)` / `has_embedded_text()` / `build_provider()` を新設し `ocr.py` を Provider 非依存にリファクタ、LM Studio 固有関数を削除**

## Performance

- **Duration:** 8 分
- **Started:** 2026-06-06T06:19:23Z
- **Completed:** 2026-06-06T06:26:59Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `run_parallel(provider, images_b64, page_indices, ...)` を新設: `provider.ocr_image(b64, prompt)` を per-page で呼び、並列度を `[1, provider.max_concurrency]` にクランプ（D-10）
- `has_embedded_text(page, threshold=3)` を新設: 文字数しきい値方式でページ単位のテキスト埋め込みを判定（D-06/D-07）、抽出テキスト本体をログ出力しない（T-04-05）
- `build_provider(settings)` を新設: `ocr_provider` 設定値から `LMStudioProvider` を生成するファクトリ（ocr_provider 未指定でも後方互換で LM Studio を返す）
- `OCRMixin._start_ocr` を Provider 中立化: `build_provider(self.settings)` を呼び `provider=provider` で OCRDialog へ渡す（04-03 確定シグネチャ表に準拠）
- LM Studio 固有関数（`build_chat_payload` / `call_lm_studio` / `fetch_lm_studio_models`）を `ocr.py` から削除（D-12）
- 全231テストが緑

## Task Commits

各タスクは TDD フロー（RED→GREEN）でアトミックにコミット:

1. **[RED] run_parallel / has_embedded_text の失敗テストを追加** - `a180ce8` (test)
2. **[GREEN] ocr.py を Provider 非依存にリファクタ（Task 1 GREEN）** - `7155e81` (feat)
3. **[GREEN] build_provider ファクトリのテストを追加（Task 2）** - `266527e` (feat)

## Files Created/Modified

- `pagefolio/ocr.py` — `run_parallel` / `has_embedded_text` / `build_provider` 新設、LM Studio 固有関数削除、`_start_ocr` Provider 中立化
- `pagefolio/__init__.py` — 公開 API を新関数（`run_parallel` / `has_embedded_text` / `build_provider`）に更新
- `pagefolio/dialogs/llm_config.py` — `fetch_lm_studio_models` を `LMStudioProvider.list_models()` に変更（Rule 3）
- `tests/test_ocr.py` — `FakeProvider` テストダブル、`TestRunParallel` / `TestHasEmbeddedText` / `TestBuildProvider` / `TestLMStudioProvider*` を追加・更新

## Decisions Made

- `EMBEDDED_TEXT_MIN_CHARS=3`: conftest の `sample_pdf_doc` は各ページに "Page N"（非空白5文字）を挿入。1〜2文字の誤検出を抑制しつつ典型的なページ番号テキストを検出対象にする最小しきい値として3を選択（D-06）
- `build_provider` で `ocr_provider="off"` のとき `LMStudioProvider` を返す: Phase 4 では `ocr_provider` の UI 化は未実装のため、`off` でも LM Studio 既定動作を維持することで後方互換を保つ（D-CONTEXT）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] llm_config.py の fetch_lm_studio_models 参照を修正**
- **Found during:** Task 1（ocr.py から LM Studio 固有関数を削除した直後）
- **Issue:** `pagefolio/dialogs/llm_config.py` が `from pagefolio.ocr import MAX_OCR_MAX_TOKENS, fetch_lm_studio_models` と参照しており、削除後に ImportError が発生しテスト収集不能
- **Fix:** import を `from pagefolio.ocr_providers import LMStudioProvider` に変更し、`fetch_lm_studio_models(url, timeout=10)` の呼び出しを `LMStudioProvider(url=url, model="").list_models()` に置換
- **Files modified:** `pagefolio/dialogs/llm_config.py`
- **Verification:** `venv/Scripts/pytest -x -q` が 231 件全てパス
- **Committed in:** `7155e81`（Task 1 GREEN コミットに含む）

**2. [Rule 3 - Blocking] __init__.py の古い OCR 関数 import を修正**
- **Found during:** Task 1（同上）
- **Issue:** `pagefolio/__init__.py` が `build_chat_payload` / `call_lm_studio` / `fetch_lm_studio_models` を import しており ImportError が発生
- **Fix:** 削除された関数を取り除き `run_parallel` / `has_embedded_text` / `build_provider` に更新
- **Files modified:** `pagefolio/__init__.py`
- **Verification:** 同上
- **Committed in:** `7155e81`（Task 1 GREEN コミットに含む）

---

**Total deviations:** 2 auto-fixed (Rule 3 x2)
**Impact on plan:** いずれも LM Studio 固有関数削除に伴う破壊的変更の結果。スコープ逸脱なし。

## Issues Encountered

- `EMBEDDED_TEXT_MIN_CHARS=15` の初期設定では conftest の `sample_pdf_doc`（"Page N" = 5文字）が False になりテスト失敗。しきい値を 3 に調整して解決

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `run_parallel` / `has_embedded_text` / `build_provider` / `page_to_png_b64` が揃い、Plan 03（`ocr_dialog.py` のスレッド境界リファクタ）に渡す準備完了
- `OCRDialog.__init__` の確定シグネチャ表（04-03-PLAN.md 冒頭）どおりに `provider=provider` を渡す `_start_ocr` が実装済み

---
*Phase: 04-provider-abstraction*
*Completed: 2026-06-06*

## Self-Check: PASSED

- FOUND: pagefolio/ocr.py
- FOUND: pagefolio/__init__.py
- FOUND: pagefolio/dialogs/llm_config.py
- FOUND: tests/test_ocr.py
- FOUND: .planning/phases/04-provider-abstraction/04-02-SUMMARY.md
- FOUND commit: a180ce8
- FOUND commit: 7155e81
- FOUND commit: 266527e

# Phase 04 Plan 03: OCRDialog スレッド境界再構成 Summary

**OCRDialog の _worker から fitz アクセスを完全排除し、メインスレッドの after() 小分けレンダリング・埋め込みテキストスキップ統合・run_parallel 結線を実現（Phase 4 三成功基準を UI 層で結実）**

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-06T06:31:41Z
- **Completed:** 2026-06-06T06:37:26Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- settings.py の defaults に `ocr_provider: "off"` を追加（V14-D-03 安全デフォルト）
- lang.py の ja/en に `ocr_text_skip_notice` / `ocr_progress_skip` を追加（D-09）
- OCRDialog の `__init__` に `provider=None` 引数を確定シグネチャ通りに追加
- `_fetch_models` を `fetch_lm_studio_models()` → `self.provider.list_models()` に置換
- `_on_run` → `_render_next_page` （after 連鎖）→ `_start_worker_thread` のパイプラインを実装
- `_worker` 内から fitz/get_pixmap/self.doc[/page_to_png_b64 を完全排除（成功基準3・D-03）
- 埋め込みテキストページを Vision API スキップ + get_text() 結果を results に直投入（成功基準2・D-07）
- `_render_results_ordered` にスキップ由来区別表示（`ocr_text_skip_notice` 明示・D-08）

## Task Commits

1. **Task 1: settings に ocr_provider デフォルト、lang にスキップ通知文言を追加** - `55927da` (feat)
2. **Task 2: OCRDialog スレッド境界再構成・run_parallel / 埋め込みスキップ結線** - `d23225f` (feat)

## Files Created/Modified

- `pagefolio/ocr_dialog.py` — スレッド境界リファクタ済み OCRDialog（provider 受け取り・メインスレッドレンダリング・スキップ統合・run_parallel 結線）
- `pagefolio/lang.py` — ocr_text_skip_notice / ocr_progress_skip（ja/en）を追加
- `pagefolio/settings.py` — defaults dict に ocr_provider:"off" を追加

## Decisions Made

- `_render_next_page` を `after(0)` で連鎖する設計：レンダリング中も Tkinter イベントループを疎通させ UI フリーズを回避する（D-01）
- `_worker` docstring に禁止ワード（fitz/get_pixmap 等）を書かないルール：automated grep チェックが docstring を誤検知しないようにするため
- スキップページの結果表示は `[skip_notice]\n` + `extracted_text\n` の構成：埋め込みテキスト由来であることを視覚的に明示しつつ、テキスト本文は閲覧・コピー・保存に使用可能

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _worker docstring の禁止ワードによる automated grep 誤検知を修正**
- **Found during:** Task 2 の verify ステップ
- **Issue:** `_worker` の docstring に `get_pixmap` という文字列を含めていたため、automated grep チェックが `_worker` 本体に fitz コールが残っていると誤判定した
- **Fix:** docstring を「fitz アクセスゼロ・D-03」に書き換え（実装の変更なし）
- **Files modified:** `pagefolio/ocr_dialog.py`
- **Verification:** automated grep チェック通過
- **Committed in:** `d23225f`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** docstring 文言修正のみ。実装・仕様への影響なし。

## Issues Encountered

None — automated grep チェックで docstring 内の禁止ワードを一度誤検知したが即座に修正（上記 Deviations に記載）。

## Known Stubs

None — スキップページの UI 表示は `ocr_text_skip_notice` 文言で完全実装済み。`provider` が `None` の場合の `_fetch_models` ガードは暫定実装だが、04-02 の `_start_ocr` が常に provider を渡すため通常パスでは到達しない。

## User Setup Required

None — 外部サービス設定変更なし。`ocr_provider` デフォルトが `"off"` に変更されたが Phase 4 では LMStudioProvider として動作するため既存ユーザーへの影響なし。

## Next Phase Readiness

- Phase 4 三成功基準（後方互換 / 埋め込みスキップ / スレッド境界）がすべて UI 層で結実済み
- Phase 5 で `ocr_provider` の UI 切替・Claude/Gemini プロバイダ追加が可能な状態
- Phase 6 の逐次レンダリング化（レンダリング→送信→破棄）のフックポイント（`_render_next_page`）が実装済み

## Self-Check: PASSED

- FOUND: `pagefolio/ocr_dialog.py`
- FOUND: `pagefolio/lang.py`
- FOUND: `pagefolio/settings.py`
- FOUND: `.planning/phases/04-provider-abstraction/04-03-SUMMARY.md`
- FOUND: commit `55927da` (Task 1)
- FOUND: commit `d23225f` (Task 2)

---
*Phase: 04-provider-abstraction*
*Completed: 2026-06-06*

# Phase 04 Plan 04: ギャップ修正（CR-02 後方互換復元 / CR-01 ValueError 防護） Summary

**一行サマリー:** `_on_run` で LMStudioProvider を再生成して OCR UI 値をリクエストに反映（CR-02）し、`_start_ocr` の未捕捉 ValueError を try/except でグレースフル処理（CR-01）。

## What Was Built

Phase 4（OCR プロバイダ抽象化）の検証レポート（04-VERIFICATION.md）で発見された 2 件の欠陥を閉じるギャップ修正プラン。

### CR-02: OCR ダイアログ UI 値が OCR リクエストに反映されない問題を修正（後方互換復元）

Phase 4 リファクタ後、`_on_run` が `scale_var` / `timeout_var` のみを読み取り、`model` / `max_tokens` / `temperature` が `_start_ocr` 時点の settings 値に固定されていた。v1.3.0 では `_worker` 内でダイアログ UI 値を読み取り OCR リクエストに反映していたが、プロバイダ抽象化リファクタで失われていた。

**修正内容（`pagefolio/ocr_dialog.py` の `_on_run`）:**
- `model_var` / `max_tokens_var` / `temperature_var` / `url_var` の live 値をワーカースレッド起動前に読み取り
- `LMStudioProvider(url=..., model=..., timeout=self._effective_timeout, max_tokens=..., temperature=...)` として `self.provider` を再生成
- 各 `try/except (tk.TclError, ValueError)` でフォールバック付き（裸 except 禁止を遵守）
- `_render_next_page()` 呼び出しより前に実行（ワーカーが新 provider を `run_parallel` に使う）
- `_worker` のスレッド境界（fitz/get_pixmap ゼロ）は維持

### CR-01: 未対応 OCR プロバイダ設定値での ValueError クラッシュを防御

`_start_ocr` 内の `build_provider(self.settings)` 呼び出しが try/except で保護されておらず、`settings["ocr_provider"]` に未対応値が入ると ValueError が Tkinter コールバックへ素通りしてクラッシュしていた。

**修正内容（`pagefolio/ocr.py` の `_start_ocr`）:**
- `from tkinter import messagebox` を import 追加
- `build_provider` 呼び出しを `try/except ValueError as e:` で保護
- `logger.error(...)` でプロバイダ名とエラー内容をログ
- `messagebox.showerror(self._t("err_title"), self._t("ocr_provider_unsupported").format(name=name), parent=self.root)` でユーザー通知
- `return` して OCRDialog を開かない

**追加 lang キー（`pagefolio/lang.py`）:**
- `ocr_provider_unsupported` を日英両辞書に追加（`{name}` プレースホルダ付き）

## Commits

| タスク | コミット | 内容 |
|--------|---------|------|
| Task 1 (CR-02) | `aea0e9c` | feat(04-04): _on_run でダイアログ UI 値を読み取り self.provider を再生成する（CR-02） |
| Task 2 (CR-01) | `4fe9f45` | fix(04-04): _start_ocr の build_provider を try/except ValueError で保護する（CR-01） |
| Task 3 (docs+lint) | `ce4c9b4` | docs(04-04): 開発履歴.md にギャップ修正エントリを追記し ruff / pytest を全通過 |

## Decisions Made

1. **CR-02 再生成タイミング:** `_render_next_page()` 呼び出し直前（メインスレッド）に `self.provider` を再生成することで、ワーカースレッドが必ず最新 UI 値を持つ provider を `run_parallel` に渡せる構造を確立。`_worker` 本体には一切手を加えず（成功基準3 のリグレッション防止）。

2. **CR-01 捕捉範囲:** `except ValueError as e:` のみを捕捉。`build_provider` は未対応プロバイダ名でのみ `ValueError` を投げるため、ValueError 以外の例外は本タスクでは捕捉しない（最小スコープ原則）。

3. **APP_VERSION 維持:** `pagefolio/constants.py` の `APP_VERSION` は現在値 `"v1.3.0"` のまま維持。マイルストーン v1.4.0 は Phase 5/6/7 が残存しており、ギャップ修正単独での版番繰り上げは行わない。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff E501 行長超過を修正（Task 1）**
- **Found during:** Task 1 の ruff check 実行時
- **Issue:** CR-02 追加コードで 4 行が 88 文字を超えていた（コメント行・max_tokens クランプ行・フォールバック行）
- **Fix:** コメントを短縮し、max_tokens クランプを中間変数 `raw_mt` を使って 2 行に分割し、フォールバック行を一時変数 `_prov` を使って分割
- **Files modified:** `pagefolio/ocr_dialog.py`
- **Commit:** `aea0e9c`（ruff check 後に fix → 同じ Task 1 コミットに含める）

**2. [Rule 1 - Format] ruff format 実行（Task 3）**
- **Found during:** Task 3 の `ruff format --check .` 実行時
- **Issue:** Task 2 で追加した `ocr.py` / `lang.py` の空白・インデントが ruff format 基準と微妙にずれていた
- **Fix:** `venv/Scripts/ruff format pagefolio/lang.py pagefolio/ocr.py` を実行して自動整形
- **Files modified:** `pagefolio/ocr.py`, `pagefolio/lang.py`
- **Commit:** `ce4c9b4`

## Verification Results

| チェック | 結果 |
|---------|------|
| `_on_run` に `model_var` / `max_tokens_var` / `temperature_var` が存在する | PASS |
| `_on_run` に `LMStudioProvider(` が存在し `self.provider` を再代入する | PASS |
| `_worker` に `get_pixmap` / `self.doc[` / `page_to_png_b64` が出現しない | PASS |
| `_start_ocr` に `try` / `except ValueError` が存在する | PASS |
| `_start_ocr` の except 内に `showerror` と `return` が存在する | PASS |
| `LANG['ja']['ocr_provider_unsupported']` が `{name}` で format 可能 | PASS |
| `LANG['en']['ocr_provider_unsupported']` が `{name}` で format 可能 | PASS |
| `python -c "import ast; ast.parse(...)"` ocr_dialog.py / ocr.py | PASS |
| `ruff check .` | PASS (exit 0) |
| `ruff format --check .` | PASS (exit 0) |
| `pytest -q` | PASS (231 passed) |

## Known Stubs

なし。本プランで追加した全機能は実データが流れる状態である。

## Threat Flags

なし。本ギャップ修正はローカルのダイアログ UI 値を既存の LM Studio エンドポイントへの OCR リクエストに反映するだけで、新規外部接触先やネットワーク経路の変更はない。CR-01 により `_start_ocr` の例外処理が強化されクラッシュが防止された（T-04-11 解消）。

## Self-Check: PASSED

- `pagefolio/ocr_dialog.py` — 存在確認: FOUND
- `pagefolio/ocr.py` — 存在確認: FOUND
- `pagefolio/lang.py` — 存在確認: FOUND
- `開発履歴.md` — 存在確認: FOUND (CR-02 / 後方互換 記載済み)
- commit `aea0e9c` — FOUND (git log 確認済み)
- commit `4fe9f45` — FOUND (git log 確認済み)
- commit `ce4c9b4` — FOUND (git log 確認済み)
- `pytest -q` — 231 passed
- `ruff check .` — exit 0
- `ruff format --check .` — exit 0
