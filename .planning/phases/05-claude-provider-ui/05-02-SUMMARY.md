---
phase: 05-claude-provider-ui
plan: "02"
subsystem: settings-security
tags: [security, settings, lang, tdd, key-guard]
dependency_graph:
  requires: [05-01]
  provides: [_SENSITIVE_KEYS, _save_settings-guard, DEFAULT_SETTINGS-extended, lang-phase5-keys]
  affects: [05-03, 05-04, 05-05]
tech_stack:
  added: []
  patterns: [機密キーガード, TDD-RED-GREEN, モジュール定数集合, JSON除外コピー]
key_files:
  created:
    - tests/test_settings_keyguard.py
  modified:
    - pagefolio/settings.py
    - pagefolio/lang.py
decisions:
  - "_SENSITIVE_KEYS を set 型モジュール定数として定義（claude_api_key/gemini_api_key/anthropic_api_key/api_key）"
  - "_save_settings は入力 dict を破壊せず除外コピーを json.dump（非破壊的ガード）"
  - "logger.error はキー名のみ記録しキー値はログに出さない（D-04 準拠）"
  - "claude_model='claude-sonnet-4-6' / ocr_effort='low' を DEFAULT_SETTINGS に追加"
  - "Phase 5 文言 9 キーを ja/en 両辞書に追加（OCR-UI-01 基盤）"
metrics:
  duration: "約 10 分"
  completed: "2026-06-06T16:35:00Z"
  tasks_completed: 3
  files_changed: 3
---

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
