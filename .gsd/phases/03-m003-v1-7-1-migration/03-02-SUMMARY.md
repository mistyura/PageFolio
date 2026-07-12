---
id: S02
parent: M003
milestone: M003
provides:
  - PluginManager.register_ocr_provider の重複名ポリシー（組み込み名衝突拒否・プラグイン間後勝ち上書き、警告付き）
  - unload_plugin 時の OCR プロバイダ registry 解除（owner ベース）
  - PluginManager.get_ocr_provider(name) / list_ocr_providers() 公開アクセサ
  - TesseractProvider の段階的縮退（effective_lang/lang_fallback・要求言語の利用可能な部分集合を優先し全滅時のみ自動決定へ縮退）
  - _detect_tesseract() のプロバイダ生成時都度再評価（import 時固定を撤廃・build_provider/LLMConfigDialog 生成時に呼び直す）
  - OCRDialog._maybe_show_lang_fallback_notice による非モーダル WARNING 注記（フォールバック発生時のみ・OCR結果rawに非混入）
  - lang.py ocr_tesseract_lang_fallback_notice キー（ja/en・requested/effective プレースホルダ）
  - _require_http_scheme(url) 共通ヘルパー（LM Studio/Ollama/RunPod の _post_chat/list_models 計6箇所へ統一適用・http/https 以外は RuntimeError）
  - Gemini モデル名の URL パスセグメントエスケープ（urllib.parse.quote(self.model, safe=\"\")）
  - _raise_mapped_http_error の err_body 500文字切り詰め（全プロバイダ共通ヘルパー経由で LMStudio/Claude/Gemini/Ollama/RunPod 全てに波及）
  - ClaudeProvider.list_models の has_more/last_id カーソルページネーション対応
  - LLMConfigDialog._probe_lm_provider(update_combo) 共通ヘルパー（_fetch_models/_test_connection の重複解消・LM Studio ペアのみ）
  - OCRDialog._apply_llm_settings 末尾での app._update_ocr_buttons_state() 呼び出し（provider再生成の例外有無に関わらず実行）
  - pagefolio/ocr_pipeline.py（Tk/fitz 非依存の producer-consumer 純ロジック層）: PipelineState / consume_one / try_enqueue / send_sentinels
  - ocr_dialog.py の _render_next_page / _worker を ocr_pipeline 経由の薄いラッパーへ縮小（D-01）
  - L-6a: レンダー失敗ページでも進捗が全ページ数（100%）に到達する
  - L-6g: fatal 確定後は producer が残ページの render を継続しない
  - L-6h: sentinel 容量不変条件を ocr_pipeline.py の docstring に明文化
  - ocr.py の未使用 run_with_bounded_buffer 削除（producer-consumer 二重実装解消）
requires: []
affects: []
key_files: []
key_decisions:
  - register_ocr_provider の公開シグネチャは変更せず、ロード中プラグインIDを内部コンテキスト属性(_loading_plugin_id)経由で owner 追跡する方式を採用（D-08/D-09）
  - _provider_registry は私有属性のまま維持し、リネーム公開はしない（get_ocr_provider/list_ocr_providers の薄いアクセサ経由のみ公開）
  - TesseractProvider.__init__ に available_langs=None を追加。None のときのみ内部で _detect_tesseract() を呼び直し、build_provider は明示的に再検出結果を渡す（D-05配線をkey_linksどおりocr.py側に実装）
  - 段階的縮退ロジックは静的メソッド _resolve_lang(requested_raw, available_langs) に切り出し、要求順を保った部分集合フィルタ→空なら現行自動決定、の2分岐のみで例外を送出しない設計にした
  - llm_config.py の _TESSERACT_AVAILABLE/_TESSERACT_LANGS モジュール定数importを完全に廃止し、ダイアログ__init__でself._tesseract_available/self._tesseract_langsとして都度検出結果を保持(Pitfall 2解消)。_apply内の1箇所はgetattrフォールバックでスタブ経由の既存テストとの後方互換を確保
  - フォールバック注記は progress_var(頻繁に上書きされる)ではなく専用の_lang_fallback_label/_lang_fallback_notice_varを新設し、provider再生成時（_apply_llm_settings/_on_run）にのみ更新することで「1回のみ表示」を自然に満たす設計にした
  - _require_http_scheme はリクエスト送信直前（_post_chat/list_models 冒頭）で呼び、コンストラクタでの eager 検証はしない（RESEARCH.md A2・空URL/入力途中でもインスタンス化は失敗させない既存方針を維持）
  - RunPodProvider は既存の api_key/url 未設定チェック（早期 return/raise）の後段に _require_http_scheme を追加し、優先順位（キー未設定→URL未設定→スキーム不正）を保った
  - ClaudeProvider.list_models は _fetch_models_page(after_id) ヘルパーへ1ページ分の HTTP 呼び出しを切り出し、while ループでカーソルを辿る設計にした（1ページ完結時は従来と同一結果で後方互換）
  - _probe_lm_provider の重複解消は LM Studio ペアのみに限定し、Ollama ペア（_fetch_ollama_models/_test_ollama_connection）は D-11 に従い変更していない（Pitfall 5 回避・意図的な暗黙拡張なし）
  - _update_ocr_buttons_state 呼び出しは getattr(self.app, \"_update_ocr_buttons_state\", None) + callable チェックの防御的パターンとし、既存 SimpleNamespace スタブとの後方互換を維持した（新規テスト以外の既存スタブは無変更で通過）
  - D-01 の核心どおり ocr_dialog.py の実戦挙動（非ブロッキング put・世代ガード・waiting 進捗・skip status・render 失敗時の挙動）を仕様として ocr_pipeline.py を書き直した（逆方向は取らなかった）
  - producer 側のスレッドモデルは規定せず、ocr_dialog.py のメインスレッド after() 連鎖のまま維持（V14-D-05・Pitfall 1 回避）。ocr_pipeline.py は enqueue/sentinel の薄いユーティリティのみ提供
  - consume_one が PipelineState への state 更新（record_success/record_retryable_failure/record_fatal/record_page_error）を内部で完結させ、dialog 側コールバック（on_success/on_page_error）は results/errors 辞書のブックキーピングのみ担当する設計にし二重計上を防止した
  - L-6a のレンダー失敗計上は _skipped_pages と同型の _render_failed_pages 集合 + _render_failed_base（再開時基準）で実装し、_done_disp() ヘルパーに done_count+skip+render_failed の合算式を一元化（_render_next_page 2箇所・_worker 1箇所で共有）
  - TestProducerConsumerMemory（run_with_bounded_buffer 専用）と TestCircuitBreaker（サーキットブレーカートリップ判定）は tests/test_ocr_pipeline.py へ移設・PipelineState 直接テストへ置換した。ocr_dialog.py 側は TestRecordCallbacks として results/errors 辞書ブックキーピングのみを検証する薄いテストへ再編（両者ともロジック移動に伴う正当な移設・D-02）
patterns_established:
  - OCR provider registry へのアクセスは常に公開アクセサ(get_ocr_provider/list_ocr_providers)経由。ocr.py/llm_config.py からの _provider_registry 直接参照は禁止
  - provider再生成の都度呼ぶ_maybe_show_lang_fallback_noticeパターンは他プロバイダ（claude/gemini等）にlang_fallback属性がなくてもgetattrで安全にNo-opになる
  - 全プロバイダ共通ヘルパー（_raise_mapped_http_error 等）を変更する際は Pitfall 4 のとおり横断的な既存テストへの影響を確認してから進める
  - producer-consumer の共有状態は PipelineState 経由でのみ更新し、UI 層のコールバックは辞書ブックキーピングのみに限定する（二重計上防止の構造的ガード）
observability_surfaces: []
drill_down_paths: []
duration: 約55分
verification_result: passed
completed_at: 2026-07-05
blocker_discovered: false
---
# S02: Ocr

**# Phase 02 Plan 01: プラグイン OCR provider registry 堅牢化 Summary**

## What Happened

# Phase 02 Plan 01: プラグイン OCR provider registry 堅牢化 Summary

**register_ocr_provider に重複名ポリシー(組み込み名衝突拒否・プラグイン間後勝ち上書き)と unload 時の owner ベース解除を追加し、get_ocr_provider/list_ocr_providers 公開アクセサ経由へ ocr.py/llm_config.py の私有アクセスを置換**

## Performance

- **Duration:** 約20分（実装・テスト作業）
- **Started:** 2026-07-05T07:03:00+09:00
- **Completed:** 2026-07-05T07:23:45+09:00
- **Tasks:** 2 completed
- **Files modified:** 6

## Accomplishments
- `register_ocr_provider` が組み込み名（claude/gemini/lmstudio/tesseract/ollama/runpod/off）との衝突を `logger.warning` のうえ拒否し、プラグイン同士の重複名は後勝ち上書き（警告付き）
- `unload_plugin` で、そのプラグインが登録した OCR プロバイダ登録を owner 追跡に基づき registry から解除
- `PluginManager.get_ocr_provider(name)` / `list_ocr_providers()` 公開アクセサを新設し、`ocr.py:720-721` と `dialogs/llm_config.py:127` の `_provider_registry` 私有アクセスを置換
- REVIEW.md（260610-aaa-v140-review-fixplan）の L-2/L-3 に解消済みマークとコミットハッシュを追記

## Task Commits

Each task was committed atomically:

1. **Task 1: register_ocr_provider 堅牢化・unload 解除・公開アクセサ追加** - `c70ae29` (feat)
2. **Task 2: 私有アクセスの公開アクセサ置換 + REVIEW.md 完了追記** - `3e15369` (refactor), `873d391` (docs)

**Deviation fix:** `51c188b` (fix) — build_provider 変更に伴う既存 M-7 回帰テストの fake スタブ更新

_Note: STATE.md/ROADMAP.md の更新はこの SUMMARY 作成と合わせてオーケストレータが実行（executor エージェントの長時間停止によりオーケストレータが引き継ぎ完了）。_

## Files Created/Modified
- `pagefolio/plugins.py` - `_BUILTIN_PROVIDER_NAMES` 定数・`_provider_owners` 辞書・`_loading_plugin_id` コンテキスト属性・重複名ポリシー・unload 時解除・`get_ocr_provider`/`list_ocr_providers` 公開アクセサ
- `pagefolio/ocr.py` - `build_provider` が `_provider_registry` 直接アクセスから `get_ocr_provider()` 経由へ
- `pagefolio/dialogs/llm_config.py` - Combobox values 生成が `list_ocr_providers()` 経由へ
- `tests/test_plugins.py` - 重複組み込み名拒否・プラグイン間後勝ち上書き・unload 解除・公開アクセサ・build_provider 経由解決の新規テスト
- `tests/test_ocr_providers.py` - build_provider 変更に伴う fake PluginManager スタブ修正
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` - L-2/L-3 に解消済みマーク追記

## Decisions Made
- register_ocr_provider の公開シグネチャ（プラグイン作者向けAPI）は変更せず、load_plugin/enable_plugin が on_load 呼び出し前後で `_loading_plugin_id` を設定/クリアする内部コンテキスト方式で owner 追跡を実現（RESEARCH.md Architecture Patterns 準拠）
- `_provider_registry` はリネーム公開せず私有属性のまま維持し、両アクセサ経由の読み取りのみ許可（RESEARCH.md Anti-Patterns 準拠）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - 本プラン起因の回帰] tests/test_ocr_providers.py の M-7 fake スタブ修正**
- **Found during:** Task 2（私有アクセスの公開アクセサ置換）後の全体テスト実行
- **Issue:** `build_provider` が `_provider_registry` 直接アクセスから `get_ocr_provider()` 呼び出しへ変わったため、`SimpleNamespace(_provider_registry=...)` で作られた既存の fake PluginManager スタブが `AttributeError` になった
- **Fix:** fake スタブを実際の `PluginManager` インスタンス（またはそれと同等の `get_ocr_provider` を持つ実装）を使う形に修正
- **Files modified:** tests/test_ocr_providers.py
- **Verification:** `pytest tests/test_plugins.py tests/test_ocr.py tests/test_provider_ui.py -q` および `pytest -q`（フルスイート）グリーン
- **Committed in:** 51c188b

---

**Total deviations:** 1 auto-fixed（本プラン変更起因の既存テストスタブ修正）
**Impact on plan:** スコープ外の変更なし。公開アクセサ導入という計画の意図から必然的に生じた既存テストの追従修正。

## Issues Encountered
executor エージェントが Task 完了・回帰修正コミット（51c188b）後、SUMMARY.md 作成前の段階で約45分間応答なしとなり停止（`running` ステータスのまま git 状態に変化なし）。ユーザーの判断によりエージェントを停止し、オーケストレータが検証（pytest 全体737件グリーン・ruff クリーン・acceptance_criteria 全項目確認）とこの SUMMARY.md 作成、STATE.md/ROADMAP.md 更新を引き継いで完了させた。実装・テスト内容そのものへの影響はなし。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `get_ocr_provider`/`list_ocr_providers` 公開アクセサが 02-02/02-03/02-04 の土台として利用可能
- `_provider_owners`/`_loading_plugin_id` 追跡機構は plugins.py 内部に閉じており、後続プランの OCR プロバイダ実装（TesseractProvider の tesseract_lang 対応等）に影響しない

---
*Phase: 02-ocr*
*Completed: 2026-07-05*

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

## Self-Check: PASSED

All created/modified files confirmed present on disk. All commit hashes (3448d79, bf723f2, 79fa105, e72fb7e) confirmed present in git log.

# Phase 02 Plan 03: L-6 一括解消（URL検証・Gemini quote・エラー切り詰め・Claude ページネーション・設定重複解消・offボタン同期）Summary

**OCRプロバイダ層のURLスキーム検証統一適用・Gemini quoteエスケープ・エラーbody切り詰め・Claude list_modelsページネーションに加え、LLMConfigDialogの重複解消とoff切替時のOCRボタン状態同期をV171-OCR-01（L-6）として一括実装**

## Performance

- **Duration:** 約35分（調査・実装・テスト作業）
- **Started:** 2026-07-05T01:20:00Z (推定)
- **Completed:** 2026-07-05T01:36:22Z
- **Tasks:** 2 completed
- **Files modified:** 6

## Accomplishments
- `pagefolio/ocr_providers.py` に `_require_http_scheme(url)` 共通ヘルパーと `_ALLOWED_URL_SCHEMES = ("http", "https")` を新設し、LM Studio/Ollama/RunPod の `_post_chat`/`list_models`（計6箇所）へ統一適用（L-6e/D-13）
- Gemini `_post_payload` のエンドポイント生成で `urllib.parse.quote(self.model, safe="")` によりモデル名を URL パスセグメントとしてエスケープ（L-6f）
- `_raise_mapped_http_error` の `err_body` を500文字へ切り詰め。全プロバイダ共通ヘルパー経由のため LMStudio/Claude/Gemini/Ollama/RunPod 全てのエラーメッセージに一貫適用（L-6d）
- `ClaudeProvider.list_models` を `_fetch_models_page(after_id)` へリファクタし、`has_more`/`last_id` カーソルを辿る while ループで全ページのモデルを連結（1ページ完結時は後方互換）（L-6b）
- `LLMConfigDialog._fetch_models`/`_test_connection`（LM Studio 用）の重複ロジックを `_probe_lm_provider(update_combo)` へ集約。呼び出し元シグネチャは不変。Ollama ペアは D-11 に従い対象外のまま維持（L-6i）
- `OCRDialog._apply_llm_settings` 末尾（provider 再生成の try/except 外側）に `app._update_ocr_buttons_state()` 呼び出しを追加し、"off" 切替時にツールバー OCR ボタンが disabled になるよう同期（L-6j）
- `260610-aaa-REVIEW.md` の L-6b/d/e/f/i/j に解消済みマーク＋コミットハッシュを追記（D-12）

## Task Commits

Each task was committed atomically:

1. **Task 1: プロバイダ層 L-6 修正（URL スキーム検証・Gemini quote・エラー body 切り詰め・Claude list_models ページネーション）** - `892244c` (feat)
2. **Task 2: 設定ダイアログ重複解消（L-6i）+ "off" 切替ボタン状態同期（L-6j）+ REVIEW.md 追記** - `14d09f5` (feat), `e129a29` (docs)

## Files Created/Modified
- `pagefolio/ocr_providers.py` - `_require_http_scheme`/`_ALLOWED_URL_SCHEMES` 新設・LM Studio/Ollama/RunPod の6箇所へ適用・Gemini `quote()` エスケープ・`_raise_mapped_http_error` の500文字切り詰め・`ClaudeProvider._fetch_models_page`/`list_models` ページネーション
- `pagefolio/dialogs/llm_config.py` - `_probe_lm_provider(update_combo)` 新設、`_fetch_models`/`_test_connection` を薄いラッパー化
- `pagefolio/ocr_dialog.py` - `_apply_llm_settings` 末尾に `app._update_ocr_buttons_state()` の防御的呼び出しを追加
- `tests/test_ocr_providers.py` - `TestRequireHttpScheme`/`TestUrlSchemeEnforcedOnProviders`/`TestGeminiModelEscape`/`TestErrorBodyTruncation`/`TestClaudeListModelsPagination` を新規追加（計17テスト）
- `tests/test_provider_ui.py` - `_make_apply_llm_settings_stub` に `app_extra` パラメータを追加（後方互換）、`TestApplyLlmSettingsOffToggleButtons`（正常系/例外系/後方互換の3ケース）を新規追加
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` - L-6b/d/e/f/i/j に解消済みマークとコミットハッシュ（892244c, 14d09f5）を追記。L-6a/g/h は L-1 独立プラン（02-04）へ吸収済みである旨を注記

## Decisions Made
- `_require_http_scheme` はリクエスト送信直前（`_post_chat`/`list_models` 冒頭）で呼び、コンストラクタでの eager 検証は行わない（RESEARCH.md A2 の推奨どおり。空 URL や入力途中の値でもプロバイダのインスタンス化自体は失敗させない既存方針と整合）
- `RunPodProvider` は既存の `api_key`/`url` 未設定チェック（早期 raise/return）の後段に `_require_http_scheme` を追加し、例外の優先順位（キー未設定 → URL 未設定 → スキーム不正）を変えなかった
- `ClaudeProvider.list_models` は1ページ分の HTTP 呼び出しを `_fetch_models_page(after_id)` に切り出し、`while True` ループで `has_more`/`last_id` を辿る設計にした（1ページで完結する応答は従来と同一の呼び出し回数・結果になる後方互換）
- `_probe_lm_provider` による重複解消は RESEARCH.md Pitfall 5 のとおり LM Studio ペアのみに限定し、Ollama ペア（`_fetch_ollama_models`/`_test_ollama_connection`）は本プランで変更していない（D-11 の暗黙拡張禁止に従い明示的にスコープ外のまま維持）
- `_update_ocr_buttons_state` 呼び出しは `getattr(self.app, "_update_ocr_buttons_state", None)` + `callable()` チェックの防御的パターンとし、既存の `SimpleNamespace` スタブ（同属性を持たない）を含む既存テストが無改修で通過するようにした

## Deviations from Plan

None - 計画どおり実行した。

## Issues Encountered
None - 計画どおり実行し、既存テストへの回帰は発生しなかった（Pitfall 4 のエラー body 切り詰め横断影響は事前確認済みで既存 assert は全て通過）。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V171-OCR-01（L-6 一括解消）完了。残る L-1（producer-consumer 一本化・独立プラン）は 02-04 の担当
- `_require_http_scheme`/`_probe_lm_provider`/`ClaudeProvider._fetch_models_page` は 02-04 から独立して利用可能（相互依存なし）

---
*Phase: 02-ocr*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files confirmed present on disk. All commit hashes (892244c, 14d09f5, e129a29) confirmed present in git log.

# Phase 02 Plan 04: producer-consumer 一本化（L-1）+ L-6a/L-6g/L-6h 同時解消 Summary

**producer-consumer の二重実装（ocr.py の未使用ヘルパー vs ocr_dialog.py 実戦実装）を新モジュール ocr_pipeline.py（Tk/fitz 非依存）へ一本化し、レンダー失敗時の進捗停滞（L-6a）・fatal 後の render 継続（L-6g）を同時修正、sentinel 容量不変条件（L-6h）を明文化**

## Performance

- **Duration:** 約55分
- **Started:** 2026-07-05T01:41:00Z (推定)
- **Completed:** 2026-07-05T02:36:00Z
- **Tasks:** 3 completed（Task 3 は検証専用・コード変更なし）
- **Files modified:** 7（新設2 / 修正5）

## Accomplishments
- `pagefolio/ocr_pipeline.py` を新設。`PipelineState`（Lock 保護の共有カウンタ・fatal/サーキットブレーカー判定）・`consume_one`（1アイテム消費のリトライ/バックオフ/fatal 判定）・`try_enqueue`/`send_sentinels`（非ブロッキング enqueue/sentinel 送出）を Tk/fitz 非依存の純ロジック層として実装（D-01/D-02）
- `tests/test_ocr.py` の `TestProducerConsumerMemory`（`run_with_bounded_buffer` 専用テスト3件）を `tests/test_ocr_pipeline.py` へ移設し新 API へ書き換え、`render_failure_progress`/`cancel_finite_time_no_deadlock` を新規追加（計17テスト）
- `pagefolio/ocr_dialog.py` の `_render_next_page`/`_worker` を `ocr_pipeline` の関数/`PipelineState` を呼ぶ薄いラッパーへ縮小。散在していた `_done_lock`/`_done_count`/`_workers_remaining`/`_fatal_msg`/`_fatal_kind`/`_consec_err_count` を `self._pstate`（`PipelineState` インスタンス）へ集約
- L-6a: `_render_next_page` の render 失敗 except 節で `_render_failed_pages` へページを計上し progress_var/progress_bar を更新（`_done_disp()` ヘルパーに done_count+skip+render_failed の合算式を一元化）
- L-6g: `_render_next_page` 冒頭に `self._pstate.is_fatal()` 分岐を追加し、fatal 確定後は残ページの render を継続せず sentinel を送出して終了へ向かうようにした
- L-6h: `ocr_pipeline.py` のモジュール docstring に sentinel 容量不変条件（終端シグナルは合計 workers 本・送信済み分は再送しない・バッファ満杯時は部分送出）を明文化
- `pagefolio/ocr.py` の未使用ヘルパー `run_with_bounded_buffer`（本番未参照・テストのみ消費）を削除し、不要になった `queue` import も除去
- `CLAUDE.md` のファイル構成表・OCR モジュール群表に `ocr_pipeline.py`/`test_ocr_pipeline.py` を追記
- `260610-aaa-REVIEW.md` の L-1・L-6a・L-6g・L-6h に解消済みマーク + コミットハッシュを追記（D-12）
- Task 3（回帰ゲート）: OCR テスト群（488件）・フルスイート（780件）・ruff check/format すべてグリーンを確認（コード変更なし）

## Task Commits

Each task was committed atomically:

1. **Task 1: ocr_pipeline.py 新設 + 既存 bounded buffer テスト移設・拡充** - `c4cd9da` (feat)
2. **Task 2: ocr_dialog.py 薄いラッパー化 + L-6a/L-6g 修正 + ocr.py 未使用ヘルパー削除 + CLAUDE.md/REVIEW.md 追記** - `ae97aaa` (feat)
3. **Task 3: 回帰ゲート（既存 OCR テスト群グリーン維持の単独検証）** - コード変更なし（検証のみ・全項目グリーン）

## Files Created/Modified
- `pagefolio/ocr_pipeline.py` - 新設: `PipelineState`/`consume_one`/`try_enqueue`/`send_sentinels`（Tk/fitz 非依存の producer-consumer 純ロジック層）
- `tests/test_ocr_pipeline.py` - 新設: `PipelineState`/enqueue ヘルパー/`consume_one`/移設 producer-consumer テスト/拡充テスト（17件）
- `pagefolio/ocr.py` - `run_with_bounded_buffer` 削除・不要になった `queue` import 除去
- `pagefolio/ocr_dialog.py` - `_render_next_page`/`_worker`/`_start_worker_thread` を `ocr_pipeline` 経由へ縮小。`_record_page_success`/`_record_page_error`（辞書ブックキーピング専用）・`_done_disp()` ヘルパーを新設。`__init__`/`_clear_text`/`_on_run` の共有状態初期化を `self._pstate` へ一本化
- `tests/test_ocr.py` - `TestProducerConsumerMemory`/`TestCircuitBreaker` を移設・再編（`TestRecordCallbacks` へ縮小）。`TestWorkerConcurrency`/`TestClearResetsFatalState`/`TestOcrDialogOnRun`/`TestRenderNextPageQueueFullInvariant`/`TestForceOcrOption` の fake を `_pstate` ベースへ更新
- `CLAUDE.md` - ファイル構成表・OCR モジュール群表に `ocr_pipeline.py`/`test_ocr_pipeline.py` を追記
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` - L-1・L-6a・L-6g・L-6h に解消済みマーク+コミットハッシュを追記

## Decisions Made
- D-01 の核心どおり `ocr_dialog.py` の実戦挙動を仕様として `ocr_pipeline.py` を書き直した（ヘルパー側の理想仕様に dialog を寄せる逆方向は不採用・Pitfall 1）
- producer 側のスレッドモデルは規定せず、`ocr_dialog.py` のメインスレッド `after()` 連鎖のまま維持（V14-D-05 制約・Pitfall 1 回避）。`ocr_pipeline.py` は enqueue/sentinel の薄いユーティリティのみ提供し、専用 producer スレッドを内部に持たない
- `consume_one` が `PipelineState` への state 更新（成功/リトライ失敗/fatal/ページエラー）を内部で完結させ、dialog 側コールバック（`on_success`/`on_page_error`）は `results`/`errors` 辞書のブックキーピングのみを担当する設計にして二重計上を防止した
- L-6a のレンダー失敗計上は `_skipped_pages` と同型の `_render_failed_pages` 集合 + `_render_failed_base`（再開時基準）で実装し、`_done_disp()` ヘルパーに `done_count + skip + render_failed` の合算式を一元化（`_render_next_page` の2箇所・`_worker` の1箇所で共有し二重実装を避けた）
- `TestProducerConsumerMemory`（`run_with_bounded_buffer` 専用）と `TestCircuitBreaker`（サーキットブレーカートリップ判定）は `tests/test_ocr_pipeline.py` へ移設・`PipelineState` 直接テストへ置換した。`ocr_dialog.py` 側は `TestRecordCallbacks` として `results`/`errors` 辞書ブックキーピングのみを検証する薄いテストへ再編（両者ともロジック移動に伴う正当な移設であり、既存 OCR テスト群の意図＝並列・キャンセル・進捗・リトライの回帰なし、は維持されている）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `TestCircuitBreaker`/複数 fake のアーキテクチャ非互換を修正**
- **Found during:** Task 2（`ocr_dialog.py` の PipelineState 一本化）
- **Issue:** `tests/test_ocr.py` の複数の SimpleNamespace fake（`TestWorkerConcurrency`・`TestClearResetsFatalState`・`TestOcrDialogOnRun`・`TestRenderNextPageQueueFullInvariant`・`TestForceOcrOption`・`TestCircuitBreaker`）が旧フラット属性（`_done_lock`/`_done_count`/`_workers_remaining`/`_fatal_msg`/`_fatal_kind`/`_consec_err_count`）に依存しており、`self._pstate` への一本化後は `AttributeError`/アサーション不一致で全て赤化する状態だった
- **Fix:** 各 fake を `_pstate=PipelineState(...)` ベースへ更新し、アサーションも `fake._pstate.xxx` を参照する形へ書き換え。`TestCircuitBreaker`（サーキットブレーカートリップ判定）は既に `tests/test_ocr_pipeline.py::TestPipelineState` で同等以上に検証済みのため、`TestRecordCallbacks`（results/errors 辞書ブックキーピングのみ検証）へ再編した
- **Files modified:** tests/test_ocr.py
- **Verification:** `pytest tests/test_ocr.py tests/test_provider_ui.py tests/test_ocr_pipeline.py -q` 255件グリーン、フルスイート780件グリーン
- **Committed in:** ae97aaa (Task 2 commit)

---

**Total deviations:** 1 auto-fixed（Rule 1: 既存テストのアーキテクチャ変更への追従・PipelineState 一本化に伴う正当な移設）
**Impact on plan:** D-01 が要求する「dialog 側の実戦挙動を仕様として一本化」を完遂するために必須の追従であり、スコープ逸脱はない。ロジック自体（circuit breaker trip・render 失敗計上等）はすべて test_ocr_pipeline.py または test_ocr.py 側で同等以上にカバーされている。

## Issues Encountered
None - 計画どおり実行し、既存テストの追従修正（上記デビエーション）以外の問題は発生しなかった。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V171-OCR-04（L-1 producer-consumer 一本化）完了。L-6a/L-6g/L-6h も同時解消（D-03）
- Phase 02（OCR 磨き込み）の全4プラン（02-01〜02-04）完了。V171-OCR-01〜04 すべて充足
- V14-D-05/06（fitz メインスレッドのみ・バッファ上限 concurrency+1）は一本化後も維持されている

---
*Phase: 02-ocr*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files confirmed present on disk. All commit hashes (c4cd9da, ae97aaa) confirmed present in git log.
