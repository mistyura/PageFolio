---
phase: 02-ai
plan: 04
subsystem: ai
tags: [ocr-fallback, tkinter, provider-orchestration, settings-snapshot, pytest]

# Dependency graph
requires:
  - phase: 02-ai (plan 01)
    provides: "ocr_fallback.py の next_fallback_candidate/next_summary_candidate（純ロジック層）"
  - phase: 02-ai (plan 03)
    provides: "LLM 設定ダイアログの ocr_fallback_enabled/ocr_fallback_chain 設定 UI（既定 OFF・ホワイトリスト検証済み）"
provides:
  - "OCRDialog のダイアログローカル設定スナップショット（_active_ocr_settings）と6メソッドの settings= 引数一般化"
  - "_propose_fallback/_switch_to_fallback_provider/_validate_provider_readiness によるフォールバック実行時オーケストレーション"
  - "_finish_error/_on_summary_error からのフォールバック提案フック接続"
  - "lang.py の fallback_confirm_*/fallback_reason_*/fallback_exhausted（ja/en）"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ダイアログローカル設定スナップショット（settings=None 引数 + s = settings if settings is not None else self.app.settings）で self.app.settings を書き換えずにプロバイダ切替を実現するパターン"
    - "OCRDialog.__new__(OCRDialog) による Tk 生成なし headless テストスタブ（実際の bound method をそのまま呼べるため lambda 逐一定義が不要）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_dialog.py
    - pagefolio/lang.py
    - tests/test_ocr_fallback.py
    - tests/test_ocr.py
    - tests/test_provider_ui.py

key-decisions:
  - "レビュー HIGH 対応: _on_run 内の全 self.app.settings 参照（name 取得 + build_provider 4箇所）をローカルスナップショット s へ全置換。inspect.getsource(...).count('self.app.settings')==1 で回帰を機械的に防止"
  - "レビュー MEDIUM 対応: _on_summary/_confirm_summary_cost/_check_cloud_api_key もサマリ経路対称に settings= 引数化し、fb スナップショットを _summary_worker まで引き継ぐ"
  - "レビュー LOW 対応: _validate_provider_readiness を新設し、tesseract 未インストール／クラウドキー未解決を build_provider 呼び出し前に検出。実行不可候補は静かに握りつぶさず _fallback_tried へ計上して次候補へ再帰的に進む"
  - "_switch_to_fallback_provider は _fallback_resume フラグで _on_run/_on_summary のコスト確認 askyesno のみをガードし（フォールバック確認ダイアログが送信先確認を兼ねる・D-10/D-11）、APIキー確認（_check_cloud_api_key）はフラグに関わらず必ず実行する"
  - "候補が None（チェーン終端）のときは自動送信も追加確認もせず、text ウィジェットへ fallback_exhausted 通知を追記するのみで留める（D-10）"

patterns-established:
  - "settings=None 引数の一般化は「省略時は self.app.settings、明示時はそのスナップショット」の1行（s = settings if settings is not None else self.app.settings）で統一し、既存呼び出し元は無変更のまま後方互換を保つ"

requirements-completed: [V180-FALL-02, V180-FALL-03]

coverage:
  - id: D1
    description: "_is_cloud_provider/_confirm_cost/_confirm_summary_cost/_check_cloud_api_key/_on_run/_on_summary を settings= 引数で一般化し、_on_run/_on_summary 内の全設定参照をダイアログローカルスナップショット s 経由へ統一（レビュー HIGH/MEDIUM）"
    requirement: "V180-FALL-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestSettingsIsolation"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py (全体・後方互換回帰)"
        status: pass
    human_judgment: false
  - id: D2
    description: "_propose_fallback が fatal 停止時に毎回 messagebox.askyesno で送信先確認を再提示し、理由（connection/timeout/circuit_breaker/api_key_missing/provider_unavailable）を明示する（D-10/D-11）。ocr_fallback_enabled=False では発火しない"
    requirement: "V180-FALL-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestConfirmationGate"
        status: pass
    human_judgment: false
  - id: D3
    description: "_switch_to_fallback_provider が self.app.settings を書き換えずローカルスナップショット fb 上でのみ build_provider を再構築し、max_concurrency を候補プロバイダ別に再クランプする（Pitfall 3/4）"
    requirement: "V180-FALL-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestConfirmationGate::test_approval_switches_and_calls_on_run_with_candidate_settings"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestSettingsIsolation::test_switching_active_snapshot_does_not_mutate_app_settings"
        status: pass
    human_judgment: false
  - id: D4
    description: "サマリ生成失敗（_on_summary_error）にも同じフォールバック連鎖を適用し、next_summary_candidate で text 非対応候補（tesseract）を除外する（D-12・レビュー MEDIUM）"
    requirement: "V180-FALL-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestSummaryFallback"
        status: pass
    human_judgment: false
  - id: D5
    description: "_validate_provider_readiness が tesseract 未インストール／クラウドキー未解決を build 前に検出し、静かな握りつぶしなく次候補へ進む（レビュー LOW・D-11/D-14）"
    requirement: "V180-FALL-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestProviderReadiness"
        status: pass
    human_judgment: false

duration: 約60分
completed: 2026-07-14
status: complete
---

# Phase 02 Plan 04: プロバイダーフォールバック実行時オーケストレーション Summary

**OCRDialog に _propose_fallback/_switch_to_fallback_provider/_validate_provider_readiness を実装し、fatal 停止時に送信先確認ダイアログ再提示つきで手動フォールバックを行う実行時オーケストレーション層を追加（self.app.settings は一切書き換えないダイアログローカルスナップショット方式）**

## Performance

- **Duration:** 約60分
- **Tasks:** 2
- **Files modified:** 5（pagefolio/ocr_dialog.py・pagefolio/lang.py・tests/test_ocr_fallback.py・tests/test_ocr.py・tests/test_provider_ui.py）

## Accomplishments

- `_is_cloud_provider`/`_confirm_cost`/`_confirm_summary_cost`/`_check_cloud_api_key`/`_on_run`/`_on_summary` の6メソッドに `settings=None` 引数を追加し、省略時は従来どおり `self.app.settings` を読む後方互換を維持しつつ、ダイアログローカルなプロバイダ設定スナップショットで判定できるよう一般化した
- レビュー HIGH 対応: `_on_run` 内の provider 再構築（`build_provider` 4箇所 + `name` 取得）を全てローカルスナップショット `s` 経由へ置換し、`inspect.getsource(...).count("self.app.settings")==1` で回帰を機械的に防止した。フォールバック先候補プロバイダで実際に再実行される経路が保証される
- レビュー MEDIUM 対応: `_on_summary`/`_confirm_summary_cost`/`_check_cloud_api_key` も対称に `settings=` を貫通させ、サマリ経路のフォールバック再開でも fb スナップショットが最後まで引き継がれる
- `_propose_fallback(kind, msg, summary=False)` を新設し、`_finish_error`/`_on_summary_error` の末尾から接続。フォールバック連鎖の各段で必ず `messagebox.askyesno` による送信先確認を再提示し（D-10/D-11・「今後表示しない」オプションなし）、`ocr_fallback_enabled=False` では一切発火しない
- `_switch_to_fallback_provider(candidate, summary=False)` を新設し、`self.app.settings` を書き換えずローカルスナップショット `fb` 上でのみ `build_provider` を再構築。候補プロバイダ別の `max_concurrency` で再クランプし（V180-FALL-03・Pitfall 3）、`_fallback_resume` フラグでコスト確認ダイアログの二重表示のみを抑止する
- `_validate_provider_readiness(candidate, settings)` を新設（レビュー LOW）。クラウド候補は `_check_cloud_api_key` の結果を、tesseract 候補は `_detect_tesseract()` の都度検出結果をそのまま使い、実行不可な候補を静かに握りつぶさず次候補へ再帰的に進む
- `lang.py` に `fallback_confirm_title`/`fallback_confirm_msg`/`fallback_reason_*`（5種）/`fallback_exhausted` を ja/en 同一キーで追加
- `tests/test_ocr_fallback.py` に `TestSettingsIsolation`・`TestConfirmationGate`・`TestSummaryFallback`・`TestProviderReadiness`（計18件）を追加。`OCRDialog.__new__(OCRDialog)` による headless インスタンス化パターンで Tk ウィジェット生成を経由せず実メソッドを直接検証する
- フルスイート974件グリーン・ruff クリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: ダイアログローカル設定スナップショット導入とクラウド判定ヘルパーの一般化（Pitfall 4 回避）** - `d2a558a` (feat)
2. **Task 2: _propose_fallback / _switch_to_fallback_provider を実装し、_finish_error/_on_summary_error にフックを追加** - `15e241b` (feat)

## Files Created/Modified

- `pagefolio/ocr_dialog.py` - 6メソッドの settings= 一般化（Task 1）・_propose_fallback/_switch_to_fallback_provider/_validate_provider_readiness/_active_provider_name/_fallback_candidate_host の新設と _finish_error/_on_summary_error へのフック接続（Task 2）
- `pagefolio/lang.py` - fallback_confirm_title/fallback_confirm_msg/fallback_reason_*（5種）/fallback_exhausted を ja/en 追加（Task 2）
- `tests/test_ocr_fallback.py` - TestSettingsIsolation（Task 1）・TestConfirmationGate/TestSummaryFallback/TestProviderReadiness（Task 2）・_make_dialog headless スタブヘルパー
- `tests/test_ocr.py` - 既存スタブ `_is_cloud_provider` の settings 引数対応（Task 1）・`_on_summary_error` スタブへ `_propose_fallback` no-op 追加（Task 2）
- `tests/test_provider_ui.py` - 既存スタブ `_is_cloud_provider`/`_check_cloud_api_key` の settings 引数対応（Task 1）

## Decisions Made

- `_switch_to_fallback_provider` の `try/finally` で `_fallback_resume` フラグをゲート通過直後に必ず False へ戻す設計にした（`_on_run`/`_on_summary` は同期的にコスト確認ゲートを通過してから非同期処理へ進むため、呼び出し直後のリセットで正しく機能する）
- `_propose_fallback` の候補終端（`candidate is None`）は追加の確認ダイアログを出さず、`self.text`（存在すれば）へ `fallback_exhausted` を追記するのみに留めた（D-10 の「現状のエラー表示のみ」の意図を維持しつつ、`fallback_exhausted` LANG キーの未使用検出テストも満たす）
- `_fallback_candidate_host` を新設し、候補プロバイダごとの送信先（クラウドはホスト名、ローカルは接続 URL、Tesseract は表示名）を確認ダイアログへ明示する設計にした（D-11 の「送信先確認」意図を厳密に満たすための Claude's Discretion 領域の実装判断）
- `_TEXT_CAPABLE_PROVIDERS` はモジュール定数として明示リスト化し（claude/gemini/runpod/lmstudio/ollama）、プラグイン登録プロバイダの動的判定は本プランのスコープ外とした（既存の `_base_fallback_providers` と同様の静的リスト方針を踏襲）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 既存テストスタブの `_is_cloud_provider`/`_check_cloud_api_key` ラムダが settings= キーワード引数を受け付けず TypeError**
- **Found during:** Task 1（settings= 引数の一般化後、既存回帰テスト実行時）
- **Issue:** `tests/test_provider_ui.py`・`tests/test_ocr.py` の複数箇所で `stub._is_cloud_provider = lambda: OCRDialog._is_cloud_provider(stub)` のように引数なしラムダで束縛されており、`_on_run`/`_check_cloud_api_key` 内部が `self._is_cloud_provider(settings=s)` を呼ぶよう変更したことで `TypeError: unexpected keyword argument 'settings'` が発生した
- **Fix:** 該当ラムダを `lambda settings=None: OCRDialog._is_cloud_provider(stub, settings)` 等へ更新し、settings 引数を透過させつつ省略時の後方互換を維持
- **Files modified:** tests/test_provider_ui.py, tests/test_ocr.py
- **Verification:** `pytest tests/test_ocr_fallback.py tests/test_ocr.py tests/test_provider_ui.py tests/test_lang_parity.py -x -q` 全件グリーン
- **Committed in:** d2a558a（Task 1 コミット）

**2. [Rule 1 - Bug] `_on_summary_error` の既存テストスタブに `_propose_fallback` 属性がなく AttributeError**
- **Found during:** Task 2（`_on_summary_error` 末尾へのフック接続後、既存回帰テスト実行時）
- **Issue:** `tests/test_ocr.py::TestOnSummaryErrorKinds._make_fake` が生成する `types.SimpleNamespace` スタブに `_propose_fallback` が定義されておらず、新規フック呼び出しで `AttributeError` が発生した
- **Fix:** スタブへ `_propose_fallback=lambda kind, msg, summary=False: recorded.update(fallback=(kind, summary))` の no-op 記録用ラムダを追加
- **Files modified:** tests/test_ocr.py
- **Verification:** `pytest tests/test_ocr.py -x -q` 全件グリーン
- **Committed in:** 15e241b（Task 2 コミット）

**3. [Rule 3 - Blocking] `tests/test_ocr.py` の Edit ツール書き込みで CRLF 全体変換が発生し diff が巨大化**
- **Found during:** Task 1〜2 のコミット準備（`git diff` で全3015行が変更扱いになる異常を検知）
- **Issue:** `tests/test_ocr.py` は元々 LF 改行のみだが、Edit ツールでの部分編集後にファイル全体が CRLF へ変換され、実際の変更（2〜3行）とは無関係に全行が diff に現れた（コミット粒度・可読性を損なう）
- **Fix:** ファイルを Python で読み込み `\r\n` → `\n` へ一括正規化してから保存し直し、実質的な差分（意図した数行のみ）に戻した
- **Files modified:** tests/test_ocr.py
- **Verification:** 正規化後に `git diff --stat` が意図通りの数行差分のみを示すことを確認。フルスイート再実行で974件グリーンを再確認
- **Committed in:** d2a558a / 15e241b（該当行のみがそれぞれのタスクコミットに含まれる）

---

**Total deviations:** 3 auto-fixed（Rule 1 × 2・Rule 3 × 1）
**Impact on plan:** いずれも本プランの settings= 一般化・フォールバックフック接続という核心変更に直接起因する既存テストの後方互換調整、または編集ツールの副作用是正であり、実装ロジックへの影響やスコープクリープはない。

## Issues Encountered

Task 1/Task 2 は実装上は密結合（Task 2 のオーケストレーションは Task 1 の settings= 一般化なしには機能しない）だが、`git add -p`（ハンク単位）とファイル部分切り出しにより、それぞれのタスクの `<files>` 記載範囲（Task 1: `pagefolio/ocr_dialog.py, tests/test_ocr_fallback.py`／Task 2: 同 + `pagefolio/lang.py`）に沿った独立コミットへ正確に分離した。両コミット単体でそれぞれの acceptance criteria（Task 1 は `pytest tests/test_provider_ui.py tests/test_ocr.py -x -q` 等）が通過することを個別に検証済み。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2（AI強化: プロンプト・テンプレート管理 + プロバイダーフォールバック）の全4プラン（02-01〜02-04）が完了し、V180-TMPL-01〜05・V180-FALL-01〜03 の全8要件が実装・テスト済み
- フォールバック実行時オーケストレーションは「明示設定型・自動送信なし」方針（PROJECT.md）を厳守: 既定 OFF・毎回送信先確認・self.app.settings 非汚染をコードレベルで機械保証
- ブロッカーなし。Phase 3（OCR実行エンジン抽出 + E2Eテスト）は本フェーズの完了に依存しない独立フェーズ

---
*Phase: 02-ai*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: pagefolio/ocr_dialog.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_ocr_fallback.py
- FOUND: tests/test_ocr.py
- FOUND: tests/test_provider_ui.py
- FOUND: d2a558a (Task 1 commit)
- FOUND: 15e241b (Task 2 commit)
