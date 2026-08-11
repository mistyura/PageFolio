---
phase: 02-ocr-openai-chatgpt
plan: 02
subsystem: ocr
tags: [openai, chatgpt, ocr-provider, catalog, tkinter, messagebox, lang, pytest, mutation-testing]

requires:
  - phase: 02-ocr-openai-chatgpt (02-01)
    provides: "catalog.py（ProviderMeta + PROVIDERS 8件）・OpenAIProvider・02-CAPABILITY-MATRIX.md（単価・vision確認済みモデル・出典）"
provides:
  - "pagefolio/ocr_dialog.py の表示名/クラウド判定/送信先ホスト/APIキー欠落 LANG キーの catalog 移行（7参照面のうち6面完了）"
  - "pagefolio/dialogs/batch_ocr.py の同型独立 catalog 移行（5参照面）"
  - "OpenAI の送信先確認・コスト確認・vision未確認注記を含む安全境界（単発・バッチ両方）"
  - "OCR_PRICE_TABLE への OpenAI 単価5件 + OPENAI_PRICE_SOURCE プロヴェナンス定数（両ファイル同一内容）"
  - "lang.py ja/en への ocr_provider_name_openai・ocr_api_key_missing_openai・ocr_host_unknown・ocr_model_vision_unverified"
affects: [02-03-model-list-ui, 02-04-openai-settings-ui]

actuals:
  tokens: 15080
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "送信先ホスト解決の共通ヘルパー _resolved_host_text をモジュールレベル関数として実装（self._resolved_host_text ではなく _resolved_host_text(name, settings, lang_dict)）。既存フローズンテストスタブ（bare SimpleNamespace + self._L 束縛のみ）から self への新規属性追加なしで到達できるようにするための設計判断"
    - "既存2実装（表示名解決 if 連鎖 / dict）を catalog.display_name_key_for の1経路へ統合しつつ、claude/gemini の isinstance 安全側フォールバックはD-04として維持する2層構造"

key-files:
  created:
    - .planning/phases/02-ocr-openai-chatgpt/02-02-SUMMARY.md
  modified:
    - pagefolio/ocr_dialog.py
    - pagefolio/dialogs/batch_ocr.py
    - pagefolio/lang.py
    - tests/test_provider_ui.py
    - tests/test_batch_ocr_dialog.py

key-decisions:
  - "_resolved_host_text をインスタンスメソッドではなくモジュールレベル関数として実装。既存 TestConfirmCost/TestConfirmSummaryCost 系テストのスタブ（OCRDialog._confirm_cost(stub) の未バインド呼び出しパターン）が self に対して _estimate_cost 等の限定的なメソッドしか束縛していないため、self._resolved_host_text(...) という新規呼び出しを _confirm_cost 内に追加すると AttributeError で既存テストが赤くなる。self._L という既存の束縛済み属性のみを引数として渡す設計にすることで、プラン原文の「プライベートメソッド」という字面より『既存の無改修フローズンテストと両立する自己完結ヘルパー』という設計意図を優先した"
  - "_fallback_candidate_host は catalog.host_for を lmstudio/ollama/tesseract の分岐の外側で _resolved_host_text 経由に統一。'off' はフォールバック候補として実際には到達しない（catalog.PROVIDERS['off'].fallback_eligible=False）ため、'off' に対する _fallback_candidate_host の挙動は本プランの回帰テスト対象から除外した"
  - "OPENAI_PRICE_SOURCE.url は 02-CAPABILITY-MATRIX.md の個別モデルページ source_url ではなく、全モデル一覧を横断する https://developers.openai.com/api/docs/models/all を採用（プロヴェナンス定数は価格表全体に対する1つの一次情報という設計のため）"
  - "ミューテーション検証2で判明した検知力ギャップを是正: 'OPENAI_API_KEY' という env_var 文字列だけをアサートするテストは、msg_key が誤って汎用テンプレート（ocr_api_key_missing）にフォールバックしても env_var 埋め込み自体は正しいままのため検知できない。'OpenAI APIキー' という openai 専用テンプレートの固有文言を直接アサートする形へ強化した"

patterns-established:
  - "送信先ホスト解決を『self に依存しないモジュール関数 + 呼び出し側が self._L を明示的に渡す』形にすることで、Tk 非依存の未バインドスタブテストとの両立を構造的に担保するパターン（今後 catalog 経由の新規ヘルパーを追加する際の前例）"

requirements-completed: [V190-CAT-01, V190-OAI-04, V190-OAI-05, V190-OAI-06]

coverage:
  - id: D1
    description: "ocr_dialog.py の表示名解決2実装（if連鎖/dict）を catalog.display_name_key_for 経由の1経路へ統合し、claude/gemini の isinstance フォールバックはD-04として維持"
    requirement: "V190-CAT-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestProviderDisplayNameCatalog"
        status: pass
    human_judgment: false
  - id: D2
    description: "_is_cloud_provider を catalog.is_cloud_provider 経由へ置換し、isinstance ガードへ OpenAIProvider を追加（単発・バッチ両方）"
    requirement: "V190-CAT-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestIsCloudProvider"
        status: pass
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchIsCloudProviderOpenAI"
        status: pass
    human_judgment: false
  - id: D3
    description: "送信先ホスト解決の共通ヘルパー _resolved_host_text を新設し、_confirm_cost/_confirm_summary_cost/_fallback_candidate_host（単発）・_confirm_cost/_confirm_summary_cost（バッチ）を統一。ホストを解決できないクラウドプロバイダには ocr_host_unknown を明示"
    requirement: "V190-CAT-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestFallbackCandidateHostCatalog"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestResolvedHostTextUnknown"
        status: pass
    human_judgment: false
  - id: D4
    description: "_check_cloud_api_key の APIキー欠落 LANG キー dict を catalog.api_key_missing_lang_key_for 経由へ置換（単発・バッチ両方）"
    requirement: "V190-CAT-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestCheckCloudApiKey"
        status: pass
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchCheckCloudApiKeyOpenAI"
        status: pass
    human_judgment: false
  - id: D5
    description: "openai選択時、OCR実行前に送信先ホスト(api.openai.com)とページ数・概算コストを含む確認ダイアログが表示される（単発・バッチ両方）"
    requirement: "V190-OAI-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestConfirmCost::test_confirm_cost_openai_shows_openai_host"
        status: pass
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchConfirmCostOpenAI"
        status: pass
    human_judgment: false
  - id: D6
    description: "OCR_PRICE_TABLE へ OpenAI 単価5件を追加し、出典URL・参照日・単位・通貨を持つ OPENAI_PRICE_SOURCE 定数を新設（両ファイル完全一致・4層検証）"
    requirement: "V190-OAI-05"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAIPriceProvenance"
        status: pass
    human_judgment: false
  - id: D7
    description: "vision確認済み集合外のopenaiモデル選択時、コスト確認ダイアログ本文へ画像入力未確認の注記が追加される"
    requirement: "V190-OAI-05"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestVisionUnverifiedNotice"
        status: pass
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchConfirmCostOpenAI::test_confirm_cost_openai_vision_unverified_note"
        status: pass
    human_judgment: false
  - id: D8
    description: "バッチOCRでopenaiを使うとき、クラウド判定・集約コスト確認・送信先表示・APIキー欠落エラーが単発OCRと同じ内容で機能する"
    requirement: "V190-OAI-06"
    verification:
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestSingleVsBatchHostParity"
        status: pass
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchConfirmSummaryCostOpenAI"
        status: pass
    human_judgment: false
  - id: D9
    description: "確認ダイアログで「いいえ」を選んだとき build_provider にも HTTP 送信にも到達しないこと（単発・バッチ両方）"
    requirement: "V190-OAI-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestConfirmDenialStopsSend"
        status: pass
      - kind: unit
        ref: "tests/test_batch_ocr_dialog.py::TestBatchConfirmDenialStopsSend"
        status: pass
    human_judgment: false
  - id: D10
    description: "_TEXT_CAPABLE_PROVIDERS が Provider クラスの supports_text_prompt から機械的に導出される集合と一致すること（追記漏れ検知装置）"
    requirement: "V190-CAT-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTextCapableProvidersParity"
        status: pass
    human_judgment: false

duration: 16min
completed: 2026-08-11
status: complete
---

# Phase 2 Plan 2: OCR プロバイダ基盤整理 + OpenAI 安全境界 Summary

**単発OCR・バッチOCR両ダイアログのプロバイダメタデータ参照を catalog 経由へ統合し、OpenAI を送信先確認・コスト確認・vision未確認注記・APIキー欠落エラーの完全な安全境界の下で既存5プロバイダと同等に組み込んだ**

## Performance

- **Duration:** 16min（git commit ログ基準・27a9b53 → 77061c4）
- **Started:** 2026-08-11T12:07:25+09:00
- **Completed:** 2026-08-11T12:23:46+09:00
- **Tasks:** 3 / 3
- **Files modified:** 5（ocr_dialog.py・batch_ocr.py・lang.py・test_provider_ui.py・test_batch_ocr_dialog.py）

## Accomplishments

- `ocr_dialog.py` の表示名解決2実装（if 連鎖版・dict 版）を `catalog.display_name_key_for` の1経路へ統合し、claude/gemini の isinstance 安全側フォールバックは D-04 として維持
- `_is_cloud_provider`（単発・バッチ両方）を `catalog.is_cloud_provider` 経由へ置換し、isinstance ガードへ `OpenAIProvider` を追加
- 送信先ホスト解決の共通ヘルパー `_resolved_host_text`（モジュールレベル関数・単発/バッチそれぞれ独立実装）を新設し、`_confirm_cost`/`_confirm_summary_cost`/`_fallback_candidate_host` の host if/elif/else をすべて統一。送信先を解決できないクラウドプロバイダには `ocr_host_unknown` を明示（レビュー MEDIUM-8）
- `_check_cloud_api_key`（単発・バッチ両方）の APIキー欠落 LANG キー dict を `catalog.api_key_missing_lang_key_for` 経由へ置換
- `OCR_PRICE_TABLE` へ OpenAI モデル単価5件（gpt-5-nano/mini/5.1/5.2/gpt-4o）を追加し、出典URL・参照日・単位・通貨を持つ `OPENAI_PRICE_SOURCE` 定数を新設（両ファイル完全一致・宣言順含む）
- openai 選択時、vision 確認済み集合外のモデルではコスト確認ダイアログ本文へ画像入力未確認の注記を追加（レビュー HIGH 02-02-2）
- `_TEXT_CAPABLE_PROVIDERS` へ openai を追加し、Provider クラスの `supports_text_prompt` からの機械的導出との一致をパリティテストで固定（レビュー MEDIUM-9）
- lang.py ja/en へ `ocr_provider_name_openai`・`ocr_api_key_missing_openai`・`ocr_host_unknown`・`ocr_model_vision_unverified` を追加
- 回帰テスト58件超を新規追加し、ミューテーション検証3パターン（host改変・LANGキー固定化・価格逆転）すべてで注入→赤→revert→green を確認

## Task Commits

1. **Task 1: 単発OCRダイアログの catalog 移行と OpenAI 安全境界** - `27a9b53` (feat)
2. **Task 2: バッチOCRダイアログの同型 catalog 移行** - `33921f5` (feat)
3. **Task 3: OpenAI 安全境界の回帰テストとミューテーション検証** - `77061c4` (test)

**Plan metadata:** （本コミットの直後に別途記録）

## Files Created/Modified

- `pagefolio/ocr_dialog.py` - 表示名/クラウド判定/送信先ホスト/APIキー欠落 LANG キーの catalog 移行、OpenAI 単価・プロヴェナンス定数、vision未確認注記、`_TEXT_CAPABLE_PROVIDERS` への openai 追加
- `pagefolio/dialogs/batch_ocr.py` - 上記と同一挙動の独立実装（catalog データのみ共有・ロジック非共有）
- `pagefolio/lang.py` - ja/en へ OpenAI 関連4キーを追加
- `tests/test_provider_ui.py` - openai ケース追加 + 8新規テストクラス（表示名パリティ・フォールバックホスト・送信先不明・vision未確認注記・拒否時未到達・TEXT_CAPABLE パリティ・価格プロヴェナンス4層）
- `tests/test_batch_ocr_dialog.py` - バッチ側の対称テスト6クラス（クラウド判定・コスト確認・サマリコスト確認・APIキー欠落・単発とのhost一致・拒否時未到達）

## Decisions Made

- **`_resolved_host_text` をモジュールレベル関数として実装:** 既存 `TestConfirmCost`/`TestConfirmSummaryCost` のフローズンスタブ（`OCRDialog._confirm_cost(stub)` の未バインド呼び出しパターンで `self` が `types.SimpleNamespace`）は `_estimate_cost` 等の限定的なメソッドしか束縛していない。`self._resolved_host_text(...)` という新規のインスタンスメソッド呼び出しを追加すると `AttributeError` で無改修の既存テストが赤くなるため、`self._L` という既存の束縛済み属性のみを引数として渡すモジュール関数へ設計変更した。プラン原文は「プライベートメソッド」としていたが、既存フローズンテストとの両立を優先する実装判断として記録する
- **OPENAI_PRICE_SOURCE.url の選定:** 02-CAPABILITY-MATRIX.md は個別モデルページごとに異なる `source_url` を持つが、価格表全体を代表する1つの一次情報として全モデル一覧ページ `https://developers.openai.com/api/docs/models/all` を採用した
- **`_fallback_candidate_host` の `'off'` は回帰テスト対象外:** `catalog.PROVIDERS['off'].fallback_eligible=False` のため実際のフォールバック候補として到達しない。テストは `catalog.fallback_candidate_names()` に含まれる7プロバイダ（claude/gemini/openai/runpod/lmstudio/ollama/tesseract）に限定した

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - テスト検知力ギャップの早期発見と是正] ミューテーション検証2で判明した env_var アサーションの弱さを修正**
- **Found during:** Task 3（ミューテーション検証パターン2実施中）
- **Issue:** `_check_cloud_api_key` の `msg_key` を意図的に固定 LANG キー（`ocr_api_key_missing`）へ変更しても、`test_openai_unresolved_shows_error_and_returns_false` の `"OPENAI_API_KEY" in captured["msg"]` アサーションが green のまま通ってしまった。原因は汎用テンプレート `ocr_api_key_missing` も `{env_var}` プレースホルダを持ち、`primary_env_var("openai")` が正しく `"OPENAI_API_KEY"` を返すため、msg_key の選択ミスとは独立に文字列が一致してしまうこと
- **Fix:** テストへ `"OpenAI APIキー"` という openai 専用テンプレートにしか存在しない固有文言のアサーションを追加し、msg_key の誤フォールバックを直接検知できるようにした
- **Files modified:** `tests/test_provider_ui.py`
- **Verification:** 同一ミューテーション（`msg_key` 固定化）を再度注入し、追加アサーションが赤くなることを確認してから revert
- **Committed in:** `77061c4`

**2. [プラン記述からの実装判断・逸脱ではなく設計具体化] `_resolved_host_text` をインスタンスメソッドではなくモジュールレベル関数として実装**
- **Found during:** Task 1（`_confirm_cost` の catalog 移行実装直後、既存 `TestConfirmCost` 実行時に `AttributeError` で発覚）
- **Issue:** プラン原文は「`ocr_dialog.py` 内のプライベートメソッド」と指定していたが、その通りに `self._resolved_host_text(...)` として実装すると、既存の無改修フローズンテストスタブ（`self` が `_estimate_cost`/`_confirm_cost` 等の限定属性のみを持つ `SimpleNamespace`）で `AttributeError` が発生し、Task 1 の acceptance criteria「既存テストが無改修で green」に違反する
- **Fix:** `_resolved_host_text(name, settings, lang_dict)` というモジュールレベル関数として実装し直し、呼び出し側で `self._L`（既存の束縛済み属性）を明示的に渡す形へ変更した。単発・バッチ両ファイルで同一設計を採用
- **Files modified:** `pagefolio/ocr_dialog.py`, `pagefolio/dialogs/batch_ocr.py`
- **Verification:** `tests/test_provider_ui.py::TestConfirmCost`（無改修分）が green のまま維持されることを確認
- **Committed in:** `27a9b53`, `33921f5`

---

**Total deviations:** 2（1件はテスト検知力の是正・1件は既存テスト互換性を優先した設計具体化）
**Impact on plan:** いずれも正確性・検証品質に直結する必要な対応。スコープ拡大は無し。プランの意図（送信先ホスト解決の一元化・catalog単一情報源化）自体は完全に達成している。

## Issues Encountered

- Task 2 acceptance criteria の1項目（`batch_ocr.py` に `pagefolio.ocr_dialog` の import が無いこと）が、Phase 01 から存在する既存の `from pagefolio.ocr_dialog import SUMMARY_TOO_LONG_CHARS`（定数のみの import・ロジック共有ではない）により機械的にはチェックが赤くなる。この import は本プランの変更対象外（Task 1/2 のいずれの diff にも含まれない）であり、`batch_ocr.py` 冒頭の設計方針コメントが禁じる「`OCRDialog` のロジックimport」には該当しない（定数1つのみ）。既存コードへの遡及修正は本プランのスコープ外と判断し、コード変更は行わずここに記録する
- フルテストスイート実行時、`tests/test_toast.py` で Tcl/Tk の `ttk` テーマファイル読み込みが断続的に失敗する既知の環境フレーキー（STATE.md「v1.8.0 リリース作業で発見」記載の問題と同種）が1回発生した。単体実行では常に green（`pytest tests/test_toast.py` で 16/16 pass）であり、本プランのコード変更とは無関係と判断した。フルスイートは2回目実行で 1270 passed（`test_ocr_pipeline.py` を除く）+ 17 passed（`test_ocr_pipeline.py` 単独）= 1287 passed 全件 green を確認済み

## User Setup Required

None - 本プランは既存コードのリファクタリングとテスト追加のみで、外部サービス設定・APIキー入力を必要としない。

## Next Phase Readiness

- `ocr_dialog.py`/`batch_ocr.py` の catalog 移行が V190-CAT-01 の対象6参照面のうち5面（Task 1: 表示名2/クラウド判定/host3箇所/APIキー欠落dict、Task 2: 同型5箇所）完了。残る `sections.py` の一覧リスト2箇所は 02-03 が担当
- openai の送信先確認・コスト確認・vision未確認注記・APIキー欠落エラーが単発・バッチ両方で既存5プロバイダと同等の安全境界に到達。02-03（LLM設定UIへのopenai追加・combobox露出）はこの安全境界の完成を前提として着手可能
- `OPENAI_PRICE_SOURCE`/`OCR_PRICE_TABLE` のOpenAIエントリが02-04 Task 3B human-verify（公式価格ページとの突き合わせ）の対象として確定済み

## Self-Check: PASSED

All created/modified files and commit hashes verified to exist on disk / in git history.

---
*Phase: 02-ocr-openai-chatgpt*
*Completed: 2026-08-11*
