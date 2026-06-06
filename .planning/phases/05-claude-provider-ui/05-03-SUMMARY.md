---
phase: 05-claude-provider-ui
plan: "03"
subsystem: ocr-security-backoff
tags: [security, backoff, claude, key-resolution, tdd, session-key]
dependency_graph:
  requires: [05-01, 05-02]
  provides:
    - _resolve_api_key（pagefolio/ocr.py）
    - build_provider claude 分岐（pagefolio/ocr.py）
    - run_parallel OCRRetryableError バックオフ層（pagefolio/ocr.py）
    - _start_ocr キー解決ゲート（pagefolio/ocr.py）
    - _session_api_keys 属性（pagefolio/app.py）
  affects:
    - pagefolio/ocr_dialog.py（05-05 で waiting 進捗を消費）
    - Phase 6 Gemini（run_parallel バックオフは provider 非依存で再利用可能）
tech_stack:
  added: []
  patterns:
    - 環境変数優先キー解決（_resolve_api_key）
    - プロバイダ引数注入（build_provider api_key 引数）
    - 指数バックオフ + Retry-After 優先（run_parallel + OCRRetryableError）
    - セッションキー辞書（_session_api_keys・settings 非書き込み・D-01）
    - TDD RED/GREEN サイクル（pytest + monkeypatch）
key_files:
  created: []
  modified:
    - pagefolio/app.py
    - pagefolio/ocr.py
    - tests/test_ocr.py
decisions:
  - "_resolve_api_key は os.environ.get のみ（読み取り専用）・書き込み禁止（D-05）"
  - "build_provider の claude 分岐は api_key を引数のみで受け取り settings には入れない（D-01/D-05）"
  - "run_parallel バックオフは provider 非依存の共通層として実装（Phase 6 Gemini で再利用可能・D-14）"
  - "_start_ocr の waiting on_progress は done=None で呼ぶ（完了カウントは進めない）"
  - "getattr(self, '_session_api_keys', {}) でテスト経路の安全なフォールバックを確保"
metrics:
  duration: "約 30 分"
  completed: "2026-06-06T16:47:00Z"
  tasks_completed: 3
  files_modified: 3
---

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
