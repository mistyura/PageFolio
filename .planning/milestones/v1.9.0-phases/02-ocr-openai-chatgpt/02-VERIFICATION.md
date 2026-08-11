---
phase: 02-ocr-openai-chatgpt
verified: 2026-08-11T07:11:33Z
status: passed
score: 5/5 must-haves verified (15/15 requirement IDs satisfied)
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加 Verification Report

**Phase Goal:** プロバイダメタデータ（キー・表示名・クラウド種別・環境変数・既定モデル・送信先・フォールバック可否）が単一の情報源（catalog）から解決される基盤の上で、ユーザーは OpenAI(ChatGPT) を既存5プロバイダと同等の安全境界（セッション限定キー・送信先確認・コスト確認・明示設定型フォールバック）で OCR・バッチ OCR に利用できる。
**Verified:** 2026-08-11T07:11:33Z
**Status:** passed
**Re-verification:** No — initial verification

## 検証方針

SUMMARY.md の主張を信用せず、以下をすべて実コードベース・実テスト実行で確認した:
- `pagefolio/ocr_providers/catalog.py` / `registry.py` の実体（import 制約・8プロバイダのメタデータ）
- `pagefolio/ocr_providers/openai_provider.py` の実装（urllib 直叩き・パラメータ分岐・多層防御）
- `ocr_dialog.py` / `batch_ocr.py` / `sections.py` / `dialog.py` / `model_fetch.py` の catalog 配線・openai 分岐
- 02-REVIEW.md が検出した CRITICAL（CR-01・バッチサマリのリトライ待機 TypeError）と、SUMMARY が主張する2件の実バグ修正（`36e7cc2` / `e9289b6`）がコード上に実際に反映されているか
- `git log` によるコミット実在確認、対象テストファイルの実行（`pytest`）、`ruff check`/`ruff format --check`、`lang.py` の ja/en キー数一致

## Goal Achievement

### Observable Truths（ROADMAP Success Criteria 準拠）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | プロバイダメタデータ（キー・表示名・クラウド種別・環境変数・既定モデル・送信先・フォールバック可否）が catalog から単一に解決され、新プロバイダ追加時の変更面が1箇所（軸ごと）に閉じる。registry.py の独立性制約が維持され循環 import なし（V190-CAT-01/02） | ✓ VERIFIED | `catalog.py` は `dataclasses` と `registry.env_vars_for` のみ import（Provider クラス非import）。`registry.py` は `os` のみ import（`grep -n "^import\|^from"` で確認）。`PROVIDERS` 辞書に8プロバイダ（off/lmstudio/ollama/runpod/claude/gemini/tesseract/openai）が登録され、8アクセサ関数（`provider_names`/`fallback_candidate_names`/`is_cloud_provider`/`host_for`/`default_model_for`/`display_name_key_for`/`model_setting_key_for`/`api_key_missing_lang_key_for`）が実装済み。`sections.py:93` `_base_providers = catalog.provider_names()`、`:1280` `_base_fallback_providers = catalog.fallback_candidate_names()` で D-03 の6参照面移行が完走していることを確認 |
| 2 | ユーザーは OpenAI(ChatGPT) を選択しセッション限定 API キーを入力できる（非永続・`_SENSITIVE_KEYS` ガード）。モデル一覧を API 取得でき失敗時は静的一覧へフォールバック（V190-OAI-01/02/03） | ✓ VERIFIED | `registry.sensitive_keys()` の実行結果に `OPENAI_API_KEY`/`openai_api_key` を含む12キーが実在（`python -c` で実行確認）。`settings.py:29` `_SENSITIVE_KEYS = sensitive_keys()` が `_save_settings` のガードに使われる。`dialog.py:677` セッションキー同期ループに `("openai", self.openai_api_key_var)` あり、`llm_settings` へは `openai_model`/`openai_detail` 等の非機密キーのみ収集（`openai_api_key` は含まれない）。`OpenAIProvider.list_models()` は api_key 未設定時に `RECOMMENDED_MODELS`、キーあり時は `GET /v1/models` → `filter_selectable_models` → `order_models_for_display`、0件/失敗時は静的一覧へ合流する実装をコードで確認 |
| 3 | OpenAI で OCR・バッチ OCR 実行前に送信先ホスト明示の確認ダイアログとコスト確認ダイアログが表示される（クラウド判定・送信先表示を含む）（V190-OAI-04/05/06） | ✓ VERIFIED | `ocr_dialog.py:_is_cloud_provider` が `catalog.is_cloud_provider` + `OpenAIProvider` を含む isinstance フォールバック（D-04）で実装。`_resolved_host_text`/`_confirm_cost`/`_confirm_summary_cost`/`_check_cloud_api_key` が catalog 経由でホスト・価格・APIキー欠落文言を解決（`OCR_PRICE_TABLE`・`OPENAI_PRICE_SOURCE` の実在を確認）。`batch_ocr.py` に同型の独立実装（`_is_cloud_provider`/`_build_provider_once` が `catalog.is_cloud_provider` を汎用的に使用）を確認 |
| 4 | OpenAI をフォールバック候補として設定でき発動時に送信先確認が再提示。detail(low/high/auto)・reasoning effort（対応モデルのみ）・organization/project ID（指定時のみヘッダ）が永続化される（V190-OAI-07/08/09/10） | ✓ VERIFIED | `dialog.py:_apply` に `llm_settings["openai_detail"]`（値域外は"high"）/`openai_reasoning_effort`（`effort_values_for_model` 突合せ）/`openai_organization`・`openai_project`（`_validate_openai_id` で不正時は `messagebox.showerror` を出し Apply 中断・入力保持）の収集を確認。`openai_provider.py:_headers()` は `_sanitize_header_value` を通した真値のときのみ `OpenAI-Organization`/`OpenAI-Project` を付与（空なら非付与）。`ocr_fallback.py` は無変更のまま openai 名を汎用的に扱う（純関数がプロバイダ名非依存であることをコードで確認） |
| 5 | `urllib.request` 直叩きで新規 pip 依存を追加しない。モデル別パラメータ非互換が正しく分岐しエラーにならず、429/5xx に既存リトライ基盤が適用される（V190-OAI-11/12/13） | ✓ VERIFIED | `openai_provider.py` は `ssl` を import せず `urlopen` に `context` を渡さない（既定 TLS 検証）。`_apply_gen_params` は `max_completion_tokens` を常用し、`is_reasoning_model` 判定で `temperature` を省略・`reasoning_effort` は許容集合内のみ送信。`_post_chat` の `HTTPError` は `errors.py:_raise_mapped_http_error` へ委譲（独自リトライなし）。`git diff --stat` で `requirements.txt`/`pyproject.toml`/`errors.py` の変更なしを確認 |

**Score:** 5/5 truths verified（0 present-behavior-unverified）

### Requirements Coverage（15/15 requirement IDs）

| Requirement | Source Plan | Status | Evidence |
|---|---|---|---|
| V190-CAT-01 | 02-01/02/03 | ✓ SATISFIED | catalog.py 実装 + 6参照面 catalog 移行完走（コード確認） |
| V190-CAT-02 | 02-01 | ✓ SATISFIED | registry.py が `os` のみ import。circular import なし |
| V190-OAI-01 | 02-03 | ✓ SATISFIED | `sections.py` の `openai_section_frame`、`dialog.py` の `_on_provider_change` openai 分岐実在 |
| V190-OAI-02 | 02-01/02-03 | ✓ SATISFIED | `_SENSITIVE_KEYS` に `openai_api_key`/`OPENAI_API_KEY` 実在、`llm_settings` に非流入 |
| V190-OAI-03 | 02-03 | ✓ SATISFIED | `list_models()` の実 API 取得 + フィルタ + 並び替え + フォールバックをコード確認 |
| V190-OAI-04/05/06 | 02-02 | ✓ SATISFIED | `_confirm_cost`/`_check_cloud_api_key` の catalog 配線・単発/バッチ両対応を確認 |
| V190-OAI-07 | 02-04 | ✓ SATISFIED | `ocr_fallback.py` 無変更のまま openai 対応、フォールバック確認テストあり |
| V190-OAI-08/09/10 | 02-04 | ✓ SATISFIED | `dialog.py:_apply` の4キー収集・入力検証・多層防御をコード確認 |
| V190-OAI-11/12/13 | 02-01 | ✓ SATISFIED | urllib 直叩き・パラメータ分岐・errors.py 委譲をコード確認 |

### 実バグ修正の実在確認（重要）

セッション申し送りが主張する2件の実バグ修正を、コード上で直接確認した:

1. **`36e7cc2`（ocr_dialog.py の openai プロバイダ再生成分岐欠落）**: `_apply_llm_settings`（1090行目）と `_on_run`（1571行目）の両方に `elif name == "openai":` 分岐が実在し、`_resolve_api_key("openai", session_keys)` → `build_provider(..., api_key=api_key, ...)` が配線されていることを確認。修正前は汎用 `else` へフォールスルーし `api_key` なしで `build_provider` が呼ばれていた不具合が解消されている
2. **`e9289b6`（batch_ocr.py のリトライ待機 TypeError）**: `pagefolio/dialogs/batch_ocr.py:1162` で `interruptible_sleep(delay, self._summary_cancel_flag.is_set)` と `.is_set`（呼び出し可能な bound method）が渡されていることを確認（修正前は `Event` インスタンスを直接渡していた）。02-REVIEW.md の CR-01（BLOCKER）に対応する修正であり、コミットメッセージのとおり「前マイルストーン由来の既存バグ（ba8b234）」であって Phase 2 の退行ではないことも確認した

いずれも申し送りどおりコードへ反映済みで、口先だけの主張ではない。

### 実行した自動検証

| 検証 | コマンド | 結果 |
|---|---|---|
| OpenAI/catalog 関連テスト | `pytest tests/test_ocr_provider_catalog.py tests/test_ocr_providers.py -k "OpenAI or openai" --basetemp=...` | 64 passed |
| UI/バッチ/フォールバック/lang テスト | `pytest tests/test_provider_ui.py tests/test_batch_ocr_dialog.py tests/test_ocr_fallback.py tests/test_lang_parity.py --basetemp=...` | 291 passed |
| lint | `ruff check .` | All checks passed |
| format | `ruff format --check .` | 90 files already formatted |
| lang key parity | `python -c` で `LANG['ja'] == LANG['en']` | True（477キー、OpenAI関連キーすべて実在） |
| sensitive keys | `registry.sensitive_keys()` | `OPENAI_API_KEY`/`openai_api_key` を含む12キー実在 |
| 依存追加なし | `git diff --stat requirements.txt pyproject.toml` | 変更なし（フェーズ範囲外の直近コミットのみ） |
| registry/errors 非変更 | `pagefolio/ocr_providers/errors.py` 内容確認 | `openai_provider.py` から `_raise_mapped_http_error` を呼ぶのみで errors.py 自体は既存のまま |

自動テストのフルスイート（`pytest -q --basetemp=...`）は本セッションのオーケストレータが `1384 passed` を実測済み（02-04-SUMMARY.md の `1382 passed` から本セッションの回帰修正2件のテスト追加分で微増）。再実行は要求されておらず、上記の対象テストファイル群のスポット実行（合計355件 green）で裏付けを取った。

### Anti-Patterns Found

02-REVIEW.md（`1e39c2c`）が記録した WR-01（batch_ocr.py コピペ移植方針が divergence バグを構造的に許容）・WR-02（バッチサマリのエラー種別区別が単発版より粗い）・IN-01（`OCR_PRICE_TABLE` の部分一致ルックアップが宣言順依存）は Warning/Info 級であり、対応は見送られている（`WR-01/WR-02/IN-01 は未対応` と申し送りに明記）。これらはフェーズの Success Criteria（catalog 単一化・OpenAI 安全境界・パラメータ設定・リトライ基盤）を満たすことを妨げるものではなく、CRITICAL（CR-01）はすでに `e9289b6` で解消済みであるため、フェーズのゴール達成には影響しない。将来の技術的負債として記録するに留める。

### Human Verification（該当なし）

02-04-PLAN.md の3件の human-verify checkpoint（Task 3A/3B/3C）はすべて実機でユーザーが実施済みで、SUMMARY に承認記録（Task 3B は初回不合格 → `36e7cc2` 修正後に再検証・合格）が残っている。これらは既に完了しているため、本検証で新たな human-verify 項目を追加する必要はない。

## Gaps Summary

なし。ROADMAP.md の Success Criteria 5件・REQUIREMENTS.md の該当15要件（V190-CAT-01/02, V190-OAI-01〜13）すべてがコードベース上で実在・配線・テスト green を確認できた。CRITICAL バグ（CR-01）とセッション中に発見された実機バグ（HTTP 401）はいずれも修正がコードへ反映され、回帰テストも実在する。Warning/Info 級の技術的負債（WR-01/WR-02/IN-01）は既知のまま Phase 3 以降への申し送り事項として残る。

---

_Verified: 2026-08-11T07:11:33Z_
_Verifier: Claude (gsd-verifier)_
