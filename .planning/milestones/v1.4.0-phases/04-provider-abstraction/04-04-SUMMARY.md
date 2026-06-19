---
phase: 04-provider-abstraction
plan: "04"
subsystem: ocr
tags:
  - gap-closure
  - backward-compat
  - cr-02
  - cr-01
  - lmstudio
  - ocr-prov-02
dependency_graph:
  requires:
    - 04-03
  provides:
    - OCR-PROV-02 SATISFIED
  affects:
    - pagefolio/ocr_dialog.py
    - pagefolio/ocr.py
    - pagefolio/lang.py
tech_stack:
  added: []
  patterns:
    - "_on_run でダイアログ UI live 値を読み取り LMStudioProvider を再生成（CR-02）"
    - "_start_ocr の build_provider を try/except ValueError で保護（CR-01）"
key_files:
  modified:
    - pagefolio/ocr_dialog.py
    - pagefolio/ocr.py
    - pagefolio/lang.py
    - 開発履歴.md
decisions:
  - "CR-02: _on_run 内でワーカースレッド起動前に model_var / max_tokens_var / temperature_var / url_var の live 値を読み取り LMStudioProvider として self.provider を再生成する"
  - "CR-01: _start_ocr 内の build_provider を try/except ValueError で保護し messagebox.showerror + logger + return でグレースフルに処理する"
  - "APP_VERSION は v1.3.0 のまま維持（マイルストーン v1.4.0 完了時に繰り上げ）"
metrics:
  duration: "約 10 分"
  completed_date: "2026-06-06"
  tasks: 3
  files_changed: 4
---

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
