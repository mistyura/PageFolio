---
phase: 02-ocr
plan: 02
subsystem: ocr
tags: [tesseract, ocr-providers, lang-fallback, ocr-dialog, i18n]

requires:
  - phase: 02-01
    provides: "PluginManager.get_ocr_provider/list_ocr_providers 公開アクセサ（本プランは未使用だが同フェーズの土台）"
provides:
  - "TesseractProvider の段階的縮退（effective_lang/lang_fallback・要求言語の利用可能な部分集合を優先し全滅時のみ自動決定へ縮退）"
  - "_detect_tesseract() のプロバイダ生成時都度再評価（import 時固定を撤廃・build_provider/LLMConfigDialog 生成時に呼び直す）"
  - "OCRDialog._maybe_show_lang_fallback_notice による非モーダル WARNING 注記（フォールバック発生時のみ・OCR結果rawに非混入）"
  - "lang.py ocr_tesseract_lang_fallback_notice キー（ja/en・requested/effective プレースホルダ）"
affects: [02-03, 02-04]

tech-stack:
  added: []
  patterns:
    - "provider生成時に都度呼び直す検出関数パターン（_detect_tesseract）をocr.py/llm_config.py双方で統一参照"
    - "段階的縮退ロジックを __init__ で一度だけ確定し実行メソッド（ocr_image）は都度計算しない"
    - "非モーダル注記用の専用StringVar+Labelをprogress_var/self.textとは独立させ、raw結果を汚さない"

key-files:
  created: []
  modified:
    - pagefolio/ocr_providers.py
    - pagefolio/ocr.py
    - pagefolio/dialogs/llm_config.py
    - pagefolio/lang.py
    - pagefolio/ocr_dialog.py
    - tests/test_ocr_providers.py
    - tests/test_provider_ui.py
    - tests/test_ocr.py
    - .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md

key-decisions:
  - "TesseractProvider.__init__ に available_langs=None を追加。None のときのみ内部で _detect_tesseract() を呼び直し、build_provider は明示的に再検出結果を渡す（D-05配線をkey_linksどおりocr.py側に実装）"
  - "段階的縮退ロジックは静的メソッド _resolve_lang(requested_raw, available_langs) に切り出し、要求順を保った部分集合フィルタ→空なら現行自動決定、の2分岐のみで例外を送出しない設計にした"
  - "llm_config.py の _TESSERACT_AVAILABLE/_TESSERACT_LANGS モジュール定数importを完全に廃止し、ダイアログ__init__でself._tesseract_available/self._tesseract_langsとして都度検出結果を保持(Pitfall 2解消)。_apply内の1箇所はgetattrフォールバックでスタブ経由の既存テストとの後方互換を確保"
  - "フォールバック注記は progress_var(頻繁に上書きされる)ではなく専用の_lang_fallback_label/_lang_fallback_notice_varを新設し、provider再生成時（_apply_llm_settings/_on_run）にのみ更新することで「1回のみ表示」を自然に満たす設計にした"

patterns-established:
  - "provider再生成の都度呼ぶ_maybe_show_lang_fallback_noticeパターンは他プロバイダ（claude/gemini等）にlang_fallback属性がなくてもgetattrで安全にNo-opになる"

requirements-completed: [V171-OCR-02]

coverage:
  - id: D1
    description: "TesseractProviderが要求言語(self.lang)のうち利用可能な部分集合を指定順優先で使用し、全滅時のみ自動決定(jpn有→jpn+eng/なし→eng)へ縮退する（段階的縮退・例外を送出しない）"
    requirement: "V171-OCR-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestTesseractProviderOcrImage -k 'effective_lang or lang_fallback or redetect'"
        status: pass
    human_judgment: false
  - id: D2
    description: "言語パック検出(_detect_tesseract)がimport時固定からbuild_provider/LLMConfigDialog生成時の都度呼び出しへ変更され、再起動なしで新規言語パックが反映される"
    requirement: "V171-OCR-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestTesseractProviderOcrImage::test_tesseract_redetect_reflects_new_langpacks"
        status: pass
    human_judgment: false
  - id: D3
    description: "フォールバック発生時にOCRDialog内で非モーダルWARNING色の注記が表示され(要求/実効言語を含む)、OCR結果テキスト(raw)には混入しない。非発生時は表示されない"
    requirement: "V171-OCR-02"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestMaybeShowLangFallbackNotice"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-05
status: complete
---

# Phase 02 Plan 02: Tesseract言語フォールバック堅牢化（V171-OCR-02 / L-4）Summary

**TesseractProviderへ段階的縮退(effective_lang/lang_fallback)とプロバイダ生成時の都度言語再検出を実装し、フォールバック発生時はOCRDialogの非モーダルWARNING注記(OCR結果rawには非混入)で1回通知する**

## Performance

- **Duration:** 約25分（調査・実装・テスト作業）
- **Started:** 2026-07-05T09:35:00+09:00 (推定)
- **Completed:** 2026-07-05T10:02:13+09:00
- **Tasks:** 2 completed
- **Files modified:** 9

## Accomplishments
- `TesseractProvider.__init__` に `available_langs` 引数を追加し、要求言語(`self.lang`)の「+」区切りのうち利用可能な部分集合を指定順優先で残す段階的縮退を実装（全滅時のみ現行の自動決定へ縮退・エラー中止なし）
- `_detect_tesseract()` を import 時固定からプロバイダ生成時の都度呼び出しへ変更し、`ocr.py::build_provider` が明示的に再検出結果を `TesseractProvider` へ渡すよう配線
- `llm_config.py` の `_TESSERACT_AVAILABLE`/`_TESSERACT_LANGS` モジュール定数参照を廃止し、ダイアログ生成時に同一の `_detect_tesseract()` を呼び直す方式へ統一（Pitfall 2 解消）
- `OCRDialog` にフォールバック専用の非モーダル WARNING ラベルを新設し、`_maybe_show_lang_fallback_notice` で provider 再生成の都度（`_apply_llm_settings`/`_on_run`）表示/非表示を制御。OCR 結果テキスト（`self.text`・コピー/保存 raw 対象）には一切書き込まない
- `lang.py` に `ocr_tesseract_lang_fallback_notice` キー（ja/en・`{requested}`/`{effective}` プレースホルダ）を追加
- REVIEW.md（260610-aaa-v140-review-fixplan）の L-4 に解消済みマークとコミットハッシュを追記

## Task Commits

Each task was committed atomically:

1. **Task 1: Tesseract 言語の段階的縮退 + プロバイダ生成時再検出** - `3448d79` (feat)
2. **Task 2: フォールバック注記文言 + OCRDialog 非モーダル通知** - `bf723f2` (feat), `79fa105` (docs)

## Files Created/Modified
- `pagefolio/ocr_providers.py` - `TesseractProvider.__init__` に `available_langs` 引数・`_resolve_lang` 静的メソッド（段階的縮退）・`effective_lang`/`lang_fallback`/`requested_lang` 属性追加。`_detect_tesseract()` のdocstring更新（都度呼び出し可能である旨）。モジュールレベルの `_TESSERACT_AVAILABLE`/`_TESSERACT_LANGS` 固定変数を削除
- `pagefolio/ocr.py` - `build_provider` の tesseract 分岐で `_detect_tesseract()` を呼び直し `available_langs` を明示的に `TesseractProvider` へ渡す配線を追加
- `pagefolio/dialogs/llm_config.py` - `_TESSERACT_AVAILABLE`/`_TESSERACT_LANGS` の直接importを廃止し `_detect_tesseract` 関数importへ変更。`__init__` で `self._tesseract_available`/`self._tesseract_langs` を都度検出。4箇所の参照を self 属性経由へ置換（`_apply` 内の1箇所は既存スタブテスト互換のため getattr フォールバック付き）
- `pagefolio/lang.py` - `ocr_tesseract_lang_fallback_notice` キーを ja/en 両辞書へ追加
- `pagefolio/ocr_dialog.py` - `_lang_fallback_notice_var`/`_lang_fallback_label`（WARNING色・非モーダル）を新設。`_maybe_show_lang_fallback_notice` メソッドを追加し `_apply_llm_settings`/`_on_run` の provider 再生成後に呼び出し
- `tests/test_ocr_providers.py` - 旧ロジック前提テスト `test_lang_fallback_to_eng_when_jpn_not_available` を新ロジックへ書き換え。段階的縮退（部分集合保持・全滅時自動決定・完全一致でfallback無し・空lang時の自動決定一致）・再検出反映の新規テスト5件を追加
- `tests/test_provider_ui.py` - `TestMaybeShowLangFallbackNotice`（フォールバック表示/非表示/OCR結果raw非混入の回帰テスト4件）を新規追加。`_make_apply_llm_settings_stub` に `_lang_fallback_notice_var`/`_lang_fallback_label`/`_L` を追加し既存テストが例外を黙って握りつぶさないよう修正
- `tests/test_ocr.py` - `_on_run` を呼ぶ既存 fake スタブ2箇所に `_maybe_show_lang_fallback_notice` の no-op を追加（本プラン変更による回帰修正）
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` - L-4 に解消済みマークとコミットハッシュ（3448d79, bf723f2）を追記

## Decisions Made
- `TesseractProvider.__init__` は `available_langs=None` を既定とし、None のときのみ内部で `_detect_tesseract()` を呼ぶ後方互換設計（既存 `TesseractProvider()` 呼び出しは無変更で動作）。`ocr.py::build_provider` は key_links の指示どおり明示的に再検出結果を渡す配線を追加した
- 段階的縮退は `_resolve_lang(requested_raw, available_langs)` という副作用のない静的メソッドに切り出し、`__init__` 時点で一度だけ計算して `effective_lang`/`lang_fallback` に確定（`ocr_image` は都度計算しない・RESEARCH.md の指示どおり）
- フォールバック注記は `progress_var`（OCR実行中に頻繁に上書きされる）とは独立した専用ラベルにし、provider 再生成のタイミングのみで更新することで「同一実行内で1回のみ」を自然に満たす設計にした（進捗ループ内では一切触れない）
- `llm_config.py::_apply` 内の `tesseract_lang` 設定値算出箇所は `getattr(self, "_tesseract_langs", frozenset())` で防御し、既存の `LLMConfigDialog._apply(stub)` 形式の単体テスト（Tk 生成なし SimpleNamespace スタブ）との後方互換を維持（Phase 05-03 の `_session_api_keys` と同型パターン）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - 本プラン起因の回帰] `_on_run` を呼ぶ既存 fake スタブが `_maybe_show_lang_fallback_notice` 未定義で AttributeError**
- **Found during:** Task 2（OCRDialog 非モーダル通知実装）後の全体テスト実行
- **Issue:** `tests/test_ocr.py` の `TestClearResetsFatalState`/`TestOcrDialogOnRun`/`TestForceOcrOption` が `types.SimpleNamespace` fake で `OCRDialog._on_run(fake)` を未束縛呼び出ししており、新規追加した `self._maybe_show_lang_fallback_notice()` 呼び出しで `AttributeError` を送出していた
- **Fix:** 該当 fake スタブ2箇所に `fake._maybe_show_lang_fallback_notice = lambda: None` を追加
- **Files modified:** tests/test_ocr.py
- **Verification:** `pytest tests/ -q` フルスイート 746 件グリーン
- **Committed in:** bf723f2（Task 2 コミットに含む）

**2. [Rule 1 - テストが例外を黙って握り潰していた問題] `_apply_llm_settings` の既存スタブテストが AttributeError を except で吸収し無自覚に通過**
- **Found during:** Task 2 実装後の全体テスト実行で表面化した潜在バグの発見的確認
- **Issue:** `tests/test_provider_ui.py::TestApplyLlmSettingsCustomPromptSync` のスタブ（`_make_apply_llm_settings_stub`）が `_lang_fallback_notice_var`/`_lang_fallback_label`/`_L` を持たないため、`_apply_llm_settings` 内の broad `except Exception` に新規コードの `AttributeError` が飲み込まれ、テストは意図した provider 再生成コードパスを実際には検証していなかった
- **Fix:** スタブへ必要な属性（`_lang_fallback_notice_var`/`_lang_fallback_label`/`_L`）を追加し、例外を発生させず本来のコードパスを通すよう修正
- **Files modified:** tests/test_provider_ui.py
- **Verification:** `pytest tests/test_provider_ui.py -q` グリーン（79件）・フルスイートグリーン
- **Committed in:** bf723f2（Task 2 コミットに含む）

---

**Total deviations:** 2 auto-fixed（本プラン変更起因の既存テストスタブ修正・いずれも Rule 1）
**Impact on plan:** スコープ外の変更なし。新規コード追加に伴う既存テストの追従修正のみ。

## Issues Encountered
None - 計画どおり実行し、発見した回帰はすべて自動修正で解消した。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `TesseractProvider.effective_lang`/`lang_fallback`/`requested_lang` 属性と `OCRDialog._maybe_show_lang_fallback_notice` は 02-03/02-04（L-6 一括プラン等）から独立して利用可能
- L-2〜L-4 が本フェーズで解消済み（02-01: L-2/L-3、02-02: L-4）。残る L-1（producer-consumer 一本化・独立プラン）と L-6（小物一括）は後続プランの担当

---
*Phase: 02-ocr*
*Completed: 2026-07-05*
