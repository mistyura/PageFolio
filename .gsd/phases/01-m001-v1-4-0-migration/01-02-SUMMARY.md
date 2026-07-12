---
id: S02
parent: M001
milestone: M001
provides: []
requires: []
affects: []
key_files: []
key_decisions:
  - on_progress の waiting status を 'waiting/{attempt}' 形式に変更しリトライ番号を伝搬（ocr_dialog 側で parse）
  - コスト確認ダイアログは messagebox.askyesno を使用（grab_set モーダルより軽量・D-11 毎回確認）
  - セッションキー入力欄は _build 内で _needs_session_key() を評価し env 設定済みなら非表示
  - api_key_var の値は _on_run 実行前に _session_api_keys に格納（settings には入れない・D-01/D-03）
  - build_provider を ocr_dialog から直接インポートして claude 分岐を解決（_on_run の provider 再生成中立化）
patterns_established:
  - プロバイダゲートパターン: _is_cloud_provider() → セッションキー確認 → _confirm_cost() → 実行
  - status エンコードパターン: 'waiting/{n}' で追加引数なしにリトライ番号を伝搬
observability_surfaces: []
drill_down_paths: []
duration: 約20分
verification_result: passed
completed_at: 2026-06-07T11:00:00Z
blocker_discovered: false
---
# S02: Claude Provider Ui

**# Phase 05 Plan 01: ClaudeProvider・OCRRetryableError 基盤実装 Summary**

## What Happened

# Phase 05 Plan 01: ClaudeProvider・OCRRetryableError 基盤実装 Summary

ClaudeProvider が base64 PNG を Anthropic messages API へ送信し OCR テキストを返す基盤層。effort/temperature のモデル別防御と 429/5xx の OCRRetryableError 変換を実装。

## What Was Built

`pagefolio/ocr_providers.py` に以下を追加した。

### OCRRetryableError

`RuntimeError` のサブクラス。`retry_after: float | None` 属性を保持し、429/5xx リトライ可能を示す専用例外として機能する。後続プラン（05-03 バックオフ層）がこの例外を捕捉して指数バックオフを実装する。

### ClaudeProvider

`OCRProvider` を継承する Anthropic Claude messages API プロバイダ。

- **並列度**: `default_concurrency = 2` / `max_concurrency = 2`（OCR-PERF-03 Claude=2）
- **クラス定数**: `ANTHROPIC_VERSION = "2023-06-01"` / `MESSAGES_ENDPOINT` / `MODELS_ENDPOINT` / `RECOMMENDED_MODELS` / `EFFORT_MODELS`
- **`_supports_effort()`**: `EFFORT_MODELS` 集合 + `"opus"/"sonnet"` 含み `"haiku"` 非含みの前方互換判定（D-16）
- **`_build_payload()`**: effort 対応時は `output_config.effort` のみ付与（temperature なし）、非対応時（haiku）は `temperature` のみ（成功基準7）
- **`ocr_image()`**: 必須ヘッダー（`x-api-key` / `anthropic-version`）付き POST、429/5xx → OCRRetryableError 変換、content `type=="text"` ブロック走査結合（Pitfall 6 対策）
- **`list_models()`**: キー未設定時は静的 RECOMMENDED_MODELS を返す（D-08）、キー設定時は `/v1/models` から `capabilities.image_input.supported` フィルタ

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | ClaudeProvider・OCRRetryableError の失敗テストを追加 | db7fa9d | tests/test_ocr_providers.py |
| 1 GREEN | OCRRetryableError と ClaudeProvider 骨格（effort 判定・payload 構築） | 02e2a25 | pagefolio/ocr_providers.py |
| 2 | ocr_image / list_models テスト追加（429/503/400/混在レスポンス/ヘッダー） | 1dafdf5 | tests/test_ocr_providers.py |
| 3 | ruff・全テスト・構文確認グリーン確定 | 982bd2f | pagefolio/ocr_providers.py, tests/test_ocr_providers.py |

## Test Results

- テスト数: 56 件（既存 36 件 + 新規 20 件）
- `python -m pytest tests/test_ocr_providers.py tests/test_ocr.py -q`: 92 passed
- `ruff check .`: All checks passed

## Deviations from Plan

なし — プラン通りに実行した。

## Threat Model Compliance

| Threat ID | Status | 対応内容 |
|-----------|--------|---------|
| T-05-01 | mitigated | エラーメッセージ・logger 出力に self.api_key を含めない |
| T-05-02 | mitigated | レスポンス本文は body[:500] のみ例外メッセージに含める |
| T-05-03 | accepted | Provider は retryable 例外を送出するのみ。リトライ制御は呼び出し側（05-03）へ委譲 |
| T-05-04 | mitigated | ANTHROPIC_VERSION 定数で全リクエストにヘッダーを付与 |
| T-05-SC | n/a | 本プランは新規 pip 依存ゼロ（urllib のみ） |

## Known Stubs

なし。

## Threat Flags

新規エンドポイント: `https://api.anthropic.com/v1/messages`（POST）および `https://api.anthropic.com/v1/models`（GET）への外部通信。これらはプラン脅威モデルで既に計画済みのトラストバウンダリーである。

## Self-Check: PASSED

- `pagefolio/ocr_providers.py` に `class OCRRetryableError(RuntimeError)` が存在する: 確認済み
- `pagefolio/ocr_providers.py` に `class ClaudeProvider(OCRProvider)` が存在する: 確認済み
- コミット db7fa9d 存在: 確認済み
- コミット 02e2a25 存在: 確認済み
- コミット 1dafdf5 存在: 確認済み
- コミット 982bd2f 存在: 確認済み

# Phase 05 Plan 02: セキュリティ基盤（_save_settings キーガード・lang.py 文言）SUMMARY

**One-liner:** `_SENSITIVE_KEYS` ガードで API キー平文漏洩を構造的に防止し、Phase 5 UI が参照する 9 文言キーを ja/en 両対応で追加した。

## Tasks Completed

| Task | 名前 | コミット | 主なファイル |
|------|------|---------|------------|
| 1 (RED) | _save_settings 機密キーガードの失敗テスト作成 | 268f7db | tests/test_settings_keyguard.py |
| 1 (GREEN) | _SENSITIVE_KEYS ガードと DEFAULT_SETTINGS 実装 | 47e503f | pagefolio/settings.py |
| 2 | Phase 5 文言 9 キーを ja/en 両辞書に追加 | 69e2637 | pagefolio/lang.py |
| 3 | ruff・全テスト・構文確認グリーン確定 | 314c590 | tests/test_settings_keyguard.py |

## Deviations from Plan

None - プランの通り実行した。

## TDD Gate Compliance

- RED gate: `test(05-02)` コミット（268f7db）— `_SENSITIVE_KEYS` の ImportError で全テスト失敗を確認
- GREEN gate: `feat(05-02)` コミット（47e503f）— 14 テスト全通過を確認

## Verification Results

### 成功基準 1: _save_settings が機密キーを JSON に書き込まない

```
python -m pytest tests/test_settings_keyguard.py -x -q
14 passed in 0.22s
```

### 成功基準 2: lang.py 9 キーの存在と展開

```
python -c "from pagefolio.constants import LANG; ks=[...]; assert all(...); print('OK')"
OK
```

### 成功基準 3: ruff + pytest グリーン

```
ruff check . → All checks passed!
pytest tests/test_settings_keyguard.py tests/test_imports.py -q → 48 passed
```

## Threat Flags

なし — 新規ネットワークエンドポイント・認証パス・ファイルアクセスパターン・スキーマ変更はなく、
脅威登録表の T-05-05（_save_settings キーガード）・T-05-06（logger 非漏洩）を本プランで軽減済み。

## Known Stubs

なし — 全文言は完全な文字列。プレースホルダは ja/en で統一されており展開可能。

## Self-Check: PASSED

- [x] `tests/test_settings_keyguard.py` 存在
- [x] `pagefolio/settings.py` に `_SENSITIVE_KEYS` 存在
- [x] コミット 268f7db, 47e503f, 69e2637, 314c590 存在

# Phase 05 Plan 03: セキュリティ結合層・バックオフ層実装 SUMMARY

**One-liner:** `_resolve_api_key`（環境変数優先・未設定 OCRAPIKeyError）・`build_provider` claude 分岐（キー引数注入）・`run_parallel` 指数バックオフ（最大3回・Retry-After 優先・waiting 進捗）・`_start_ocr` キー解決ゲートを実装し、成功基準2/3/8 を担保した。

## What Was Built

### `pagefolio/app.py`
`PDFEditorApp.__init__` に `self._session_api_keys = {}` を追加。プロバイダ別のセッションキー辞書で、settings および os.environ には書き込まない（D-01）。プロセス終了とともに消滅する。

### `pagefolio/ocr.py`
以下の追加・改修を実施した。

#### 定数
- `MAX_RETRIES = 3`：リトライ上限（OCR-PERF-04）
- `RETRY_BASE_DELAY = 1.0`：指数バックオフ初回待機秒数

#### `_resolve_api_key(provider_name, session_keys)`（新規）
環境変数優先でAPIキーを解決する。`claude` の場合 `ANTHROPIC_API_KEY` 環境変数を優先し、なければセッションキーを使用（D-02）。どちらも未設定なら `OCRAPIKeyError("ANTHROPIC_API_KEY")` を raise（成功基準2）。`os.environ` への書き込みは一切行わない（D-05）。

#### `build_provider(settings, api_key=None)`（改修）
`api_key` 引数を追加し `elif name == "claude":` 分岐を追加。`ClaudeProvider` に api_key を引数注入のみで渡し、settings には格納しない（D-01/D-05）。既存の lmstudio/off 分岐と最後の ValueError は後方互換を維持。

#### `run_parallel` `_call` 内部（改修）
`OCRRetryableError` を捕捉して指数バックオフリトライを実装（最大 `MAX_RETRIES=3` 回）。Retry-After 属性があればその値を `time.sleep` に使い、なければ `RETRY_BASE_DELAY * 2^(attempt-1)` の指数バックオフ（1s→2s→4s）。リトライ中は `on_progress(None, page_idx, "waiting")` を呼んで待機中進捗を通知（D-15）。既存の正常/cancel/fatal_conn/fatal_timeout/RuntimeError フローは後方互換。

#### `OCRMixin._start_ocr`（改修）
クラウドプロバイダ（`claude` など）の場合に `_resolve_api_key` でキー解決ゲートを挟む。`OCRAPIKeyError` を捕捉したら `ocr_api_key_missing` メッセージで `showerror` を表示し `return` する（OCRDialog を生成しない・成功基準2）。解決できたキーを `build_provider(self.settings, api_key=api_key)` に渡す。off/lmstudio はキー解決をスキップし api_key=None のまま既存どおり。

## Tasks Completed

| Task | 名前 | コミット | 主なファイル |
|------|------|---------|------------|
| 1 RED | _resolve_api_key / build_provider claude 分岐 / settings 非汚染の失敗テスト | 591af8a | tests/test_ocr.py |
| 1 GREEN | _resolve_api_key / build_provider claude 分岐 / _session_api_keys 実装 | 81a6f73 | pagefolio/app.py, pagefolio/ocr.py, tests/test_ocr.py |
| 2 RED | run_parallel OCRRetryableError 指数バックオフの失敗テスト | 58ed129 | tests/test_ocr.py |
| 2 GREEN | run_parallel バックオフ層実装（最大3回・Retry-After優先・waiting進捗） | 4e19668 | pagefolio/ocr.py |
| 3 | _start_ocr キー解決ゲート組込み・ruff/全テストグリーン確定 | 1087455 | pagefolio/ocr.py |

## Deviations from Plan

なし — プランの通りに実行した。

## TDD Gate Compliance

- Task 1: RED gate（591af8a `test(05-03)`）→ GREEN gate（81a6f73 `feat(05-03)`）確認済み
- Task 2: RED gate（58ed129 `test(05-03)`）→ GREEN gate（4e19668 `feat(05-03)`）確認済み
- Task 3: TDD なし（`type="auto"` タスク）

## Test Results

- テスト数: 293 件（既存 278 件 + 新規 15 件）
- `python -m pytest tests/ -q`: 293 passed
- `ruff check .`（E501 除く）: All checks passed

## Threat Model Compliance

| Threat ID | Status | 対応内容 |
|-----------|--------|---------|
| T-05-08 | mitigated | api_key は引数注入のみ。settings に書かない・settings から読まない（成功基準1/3）。テストで build_provider 後の settings に api_key が無いことを確認 |
| T-05-09 | mitigated | os.environ は読み取り（get）のみ。os.environ[ への代入が _resolve_api_key 周辺で 0 件（D-05）。grep 確認済み |
| T-05-10 | mitigated | MAX_RETRIES=3 で打ち切り・Retry-After 優先 sleep（OCR-PERF-04）。無限ループしないことをテストで担保 |
| T-05-11 | mitigated | _start_ocr がキー未解決時に return し OCRDialog を生成しない（外部送信ゼロ・成功基準2） |
| T-05-SC | n/a | 本プランは新規 pip 依存ゼロ（stdlib のみ） |

## Known Stubs

なし — 全機能が動作する実装として完成している。

## Threat Flags

なし — 新規ネットワークエンドポイント・認証パス・ファイルアクセスパターン・スキーマ変更はなく、既にプラン脅威モデルで計画済みのトラストバウンダリーの実装のみ。

## Self-Check: PASSED

- [x] `pagefolio/app.py` に `self._session_api_keys = {}` が存在
- [x] `pagefolio/ocr.py` に `def _resolve_api_key` が存在し `os.environ.get("ANTHROPIC_API_KEY")` を含む
- [x] `pagefolio/ocr.py` に `os.environ[` への代入が存在しない（grep 0件・D-05）
- [x] `pagefolio/ocr.py` に `MAX_RETRIES = 3` と `OCRRetryableError` 捕捉が存在
- [x] `_start_ocr` 内に `_resolve_api_key` 呼び出しと `OCRAPIKeyError` 捕捉・`ocr_api_key_missing` showerror が存在
- [x] コミット 591af8a, 81a6f73, 58ed129, 4e19668, 1087455 存在
- [x] `python -m pytest tests/ -q`: 293 passed
- [x] `ruff check .`（E501 除く）: 0 errors

# Phase 05 Plan 04: プロバイダ選択 UI・OCR ボタン無効化 Summary

LLMConfigDialog にプロバイダ選択 DD（off/lmstudio/claude）・欄切替・claude モデル更新（キー未設定で静的リスト）・effort/temperature 動的切替を実装し、off 時の OCR ボタン無効化を追加した。

## What Was Built

### Task 1: _ocr_buttons と _update_ocr_buttons_state（ui_builder.py + app.py）

`pagefolio/ui_builder.py`:
- `_build_tools` に `self._ocr_buttons = []` を追加
- OCR ボタン 2 件（`btn_ocr_current` / `btn_ocr_selected`）を `self._ocr_buttons` に append
- `_build_tools` 末尾に `_update_ocr_buttons_state()` 呼び出しを追加

`pagefolio/app.py`:
- `_update_ocr_buttons_state()` メソッドを追加
  - `ocr_provider == "off"` またはドキュメント未開時に disabled 化（成功基準6・D-09）
  - `getattr(self, "_ocr_buttons", [])` で属性未定義時のフォールバック確保
- `_update_doc_buttons_state()` から `_update_ocr_buttons_state()` を連動呼び出し

### Task 2: LLMConfigDialog 拡張（dialogs/llm_config.py）

完全リライト（298 挿入・71 削除）。

- **provider_var / provider_combo**: `values=["off","lmstudio","claude"]`・state="readonly"・`<<ComboboxSelected>>` で `_on_provider_change` を呼ぶ（D-07）
- **url_section_frame**: LM Studio 固有欄（URL・モデル・接続テスト/モデル取得ボタン）をひとまとめ
- **claude_section_frame**: claude モデル Combobox + モデル更新ボタン
- **effort_frame**: effort Combobox（values=["low","medium","high","xhigh","max"]）
- **temperature_frame**: 既存 temperature Spinbox をフレームに収納
- **_on_provider_change**: provider に応じて url_section_frame / claude_section_frame を pack/pack_forget
- **_on_model_change**: `_model_supports_effort` 結果で effort_frame / temperature_frame を切替（D-17）
- **_model_supports_effort**: `ClaudeProvider.EFFORT_MODELS` + プレフィックス判定（D-16）
- **_refresh_claude_models**: `os.environ.get("ANTHROPIC_API_KEY","")` のみで api_key を読み取り、例外時は静的 `RECOMMENDED_MODELS` へフォールバック・ステータスに「静的リスト表示中」を表示（D-08）
- **_apply 拡張**: `ocr_provider` / `claude_model` / `ocr_effort` を llm_settings に格納。api_key 系キーは一切格納しない（T-05-12）

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | _ocr_buttons と _update_ocr_buttons_state を実装 | 7eea42e | pagefolio/ui_builder.py, pagefolio/app.py |
| 2 | LLMConfigDialog にプロバイダ DD・欄切替・claude モデル更新・effort 切替を実装 | c4f232b | pagefolio/dialogs/llm_config.py |
| 3（checkpoint） | ビジュアル確認 — **approved 2026-06-07** | 3ffc19f (checkpoint pre-SUMMARY) | — |

## Deviations from Plan

**1. [Rule 2 - 拡張] _update_doc_buttons_state から _update_ocr_buttons_state を連動呼び出し**

- **Found during:** Task 1 実装
- **理由:** `_apply_settings` → `_rebuild_ui` 経路で `_update_doc_buttons_state` が呼ばれるため、そこから連動させることで設定変更後も OCR ボタン状態が自動更新される
- **Fix:** `_update_doc_buttons_state` の末尾に `self._update_ocr_buttons_state()` を追加
- **Files modified:** pagefolio/app.py

## Threat Model Compliance

| Threat ID | Status | 対応内容 |
|-----------|--------|---------|
| T-05-12 | mitigated | _apply で api_key 系キーを llm_settings に格納しない。grep 確認済み |
| T-05-13 | mitigated | _refresh_claude_models は os.environ 読み取りのみ。settings への書き込みなし。キー値をステータスに出力しない |
| T-05-14 | mitigated | off 時に _update_ocr_buttons_state が OCR ボタンを disabled 化 |
| T-05-15 | mitigated | _model_supports_effort が effort 非対応モデルで effort 欄を非表示化 |

## Known Stubs

なし。

## Threat Flags

なし（新規エンドポイント・スキーマ変更なし）。

## Human Verify Result

**Task 3: ビジュアル確認チェックポイント — approved（2026-06-07）**

ユーザーが以下の動作を目視確認し「approved」と応答：
- プロバイダ DD に off / lmstudio / claude が表示される
- claude 選択で URL 欄が消え claude モデル欄が表示される（D-07）
- opus/sonnet 系選択で effort 欄、haiku 系で temperature 欄に切替わる（D-17）
- ANTHROPIC_API_KEY 未設定でもモデル更新ボタンで静的リストが表示される（D-08）
- ocr_provider=off 適用後、PDF 開いても OCR ボタンが disabled（成功基準6・D-09）
- ocr_provider=lmstudio に戻すと URL/モデル欄表示・OCR ボタン有効（後方互換）

## Self-Check: PASSED

- `pagefolio/dialogs/llm_config.py` に `provider_var`・`_on_provider_change`・`effort_var` が存在: 確認済み
- `pagefolio/ui_builder.py` に `self._ocr_buttons` 初期化・append が存在: 確認済み
- `pagefolio/app.py` に `_update_ocr_buttons_state` が存在: 確認済み
- llm_config.py の _apply に api_key 系格納なし（grep 確認）: 確認済み
- コミット 7eea42e 存在: 確認済み
- コミット c4f232b 存在: 確認済み
- ruff check（変更ファイル）+ pytest 293 passed: 確認済み
- human-verify checkpoint: approved（2026-06-07）

# Phase 05 Plan 05: クラウド実行ゲート・セッションキー入力・waiting 進捗 SUMMARY

**OCRDialog にクラウド実行前コスト確認ゲート（_confirm_cost・毎回・キャンセル可）・マスク付きセッションキー入力欄（show="*"・非永続化）・run_parallel の waiting 進捗表示（ocr_waiting_retry）を実装し、provider を build_provider 経由で中立化（claude 対応）した。**

## Performance

- **Duration:** 約 20 分
- **Started:** 2026-06-07
- **Completed:** 2026-06-07（Task 1-3 完了・Task 4 は human-verify 待ち）
- **Tasks:** 3/4（Task 4: checkpoint:human-verify 待ち）
- **Files modified:** 3

## Accomplishments

- OCRDialog に `_is_cloud_provider` / `_estimate_cost` / `_needs_session_key` / `_confirm_cost` を追加
- `_on_run` 冒頭にクラウド実行ゲート（セッションキー → コスト確認 → キャンセルで中止）を実装（成功基準5）
- env 未設定時のみマスク付きセッションキー入力欄（show="*"）を表示。値は `_session_api_keys` に格納、settings には入れない（成功基準3・D-01）
- `on_progress` の `status == "waiting/{attempt}"` 分岐で待機中（リトライ n/3）を after(0) 経由で表示（成功基準8・D-15・Pitfall 3）
- `_on_run` の provider 再生成を build_provider 経由に中立化（claude / lmstudio / off 対応・CR-02 後方互換維持）
- `run_parallel` の waiting status を `"waiting/{attempt}"` 形式に変更しリトライ番号を伝搬
- 既存テスト（waiting status 検証）を `startswith("waiting")` に更新、293 tests all passed

## Task Commits

1. **Task 1+2+3: provider 中立化・コスト確認ゲート・セッションキー入力・waiting 進捗・全テストグリーン** - `5d28359` (feat)
4. **Task 4: human-verify チェックポイント** — 未完了（human-verify 待ち）

## Files Created/Modified

- `pagefolio/ocr_dialog.py` — _is_cloud_provider / _estimate_cost / _needs_session_key / _confirm_cost 追加・_on_run ゲート実装・セッションキー入力欄・on_progress waiting 分岐・build_provider 中立化
- `pagefolio/ocr.py` — on_progress の waiting status を `"waiting/{attempt}"` 形式に変更
- `tests/test_ocr.py` — waiting status 検証を `startswith("waiting")` に更新

## Decisions Made

- `on_progress` の waiting status を `"waiting/{attempt}"` 形式にした。on_progress のシグネチャを変更せずにリトライ番号を伝搬できる最小変更。
- コスト確認ダイアログは `messagebox.askyesno` を使用。tk.Toplevel + grab_set より軽量で十分。
- セッションキー入力欄は _build 内で _needs_session_key() を評価し、env 設定済みなら非表示（フレームは生成するが pack しない）。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] run_parallel の waiting status 形式変更に伴うテスト更新**

- **Found during:** Task 3（テスト実行時）
- **Issue:** 05-03 の既存テストが `status == "waiting"` で検証していたが、実装を `f"waiting/{attempt}"` に変更したためテスト失敗
- **Fix:** `tests/test_ocr.py` の waiting 判定を `c[2].startswith("waiting")` に更新
- **Files modified:** tests/test_ocr.py
- **Verification:** 293 tests all passed
- **Committed in:** 5d28359

---

**Total deviations:** 1 自動修正（Rule 1 - Bug）
**Impact on plan:** テスト更新のみ。on_progress シグネチャ変更はプランの「実装者がシグネチャに整合させる」指示に従ったもの。スコープ超過なし。

## Issues Encountered

なし。

## User Setup Required

なし。

## Next Phase Readiness

- Task 4（human-verify）で `python pagefolio.py` を起動し、claude プロバイダで以下を目視確認する必要がある:
  1. env 未設定でマスク入力欄が出ること（成功基準3）
  2. 空のまま実行するとキー未設定エラーが出ること（成功基準2）
  3. コスト確認ダイアログに送信先・ページ数・概算コスト・プライバシー注記3点が表示されること（成功基準5）
  4. キャンセルで OCR が始まらないこと（成功基準5）
  5. lmstudio で従来どおり動くこと（後方互換・D-13）
  6. settings.json にキー文字列が含まれないこと（成功基準1）

## Threat Model Compliance

| Threat ID | Status | 対応内容 |
|-----------|--------|---------|
| T-05-16 | mitigated | show="*" マスク表示でショルダーハックを防ぐ（D-04）。キー値はログ・OCR結果・エラーに出さない |
| T-05-17 | mitigated | _session_api_keys にのみ格納。settings には入れない（D-01）。human-verify 手順7で確認予定 |
| T-05-18 | mitigated | クラウド時のみ _confirm_cost ゲート（毎回・キャンセル可・送信先/ページ数/概算/プライバシー3点） |
| T-05-19 | mitigated | env 未設定 + 入力欄空のとき ocr_api_key_missing を表示し実行しない |
| T-05-20 | mitigated | waiting 進捗更新は after(0) 経由でメインスレッドへ委譲（Pitfall 3 準拠） |
| T-05-SC | n/a | 新規 pip 依存ゼロ |

## Known Stubs

なし。

## Threat Flags

なし（新規ネットワークエンドポイント・スキーマ変更なし）。

## Self-Check: PASSED

- [x] `pagefolio/ocr_dialog.py` に `_is_cloud_provider`・`_estimate_cost`・`_needs_session_key`・`_confirm_cost` が存在
- [x] セッションキー入力欄 `show="*"` が存在（行 327）
- [x] `self.app._session_api_keys["claude"] = key` が存在（settings への api_key 代入は 0 件）
- [x] `_on_run` 冒頭に `_is_cloud_provider()` ゲートと `_confirm_cost()` が存在
- [x] `on_progress` に `status.startswith("waiting")` 分岐が存在
- [x] `_confirm_cost` に host・count・cost の3要素（ocr_cost_confirm_msg）が存在
- [x] `ruff check .` 全チェックパス
- [x] `python -m pytest tests/ -q` 293 passed
- [x] コミット 5d28359 存在
