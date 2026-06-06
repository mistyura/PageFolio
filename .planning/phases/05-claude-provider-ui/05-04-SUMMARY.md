---
phase: 05-claude-provider-ui
plan: "04"
subsystem: provider-ui
tags: [ui, provider, claude, effort, ocr-buttons, llm-config-dialog]
dependency_graph:
  requires: [05-01, 05-02, 05-03]
  provides:
    - LLMConfigDialog.provider_var / provider_combo（pagefolio/dialogs/llm_config.py）
    - LLMConfigDialog._on_provider_change（pagefolio/dialogs/llm_config.py）
    - LLMConfigDialog._on_model_change（pagefolio/dialogs/llm_config.py）
    - LLMConfigDialog._model_supports_effort（pagefolio/dialogs/llm_config.py）
    - LLMConfigDialog.claude_model_var / effort_var（pagefolio/dialogs/llm_config.py）
    - PDFEditorApp._ocr_buttons（pagefolio/ui_builder.py）
    - PDFEditorApp._update_ocr_buttons_state（pagefolio/app.py）
  affects:
    - pagefolio/ocr_dialog.py（OCRDialog のプロバイダ参照・Phase 05-05 で対応）
tech_stack:
  added: []
  patterns:
    - Combobox + pack/pack_forget による動的欄切替（_on_provider_change）
    - ClaudeProvider.EFFORT_MODELS 参照による effort/temperature 多層防御
    - getattr ガードによる属性未定義安全フォールバック
key_files:
  created: []
  modified:
    - pagefolio/dialogs/llm_config.py
    - pagefolio/ui_builder.py
    - pagefolio/app.py
decisions:
  - "provider Combobox values は静的リスト ['off','lmstudio','claude']（Phase 6: gemini を追加予定コメント付記）"
  - "_update_ocr_buttons_state は _update_doc_buttons_state から連動呼び出し（設定変更経路をカバー）"
  - "_refresh_claude_models は例外時も静的 RECOMMENDED_MODELS へフォールバック（D-08 一貫適用）"
  - "effort_frame / temperature_frame の pack 順は _on_model_change 呼び出し側が担保（フレーム同士の pack_forget が互いに独立）"
metrics:
  duration: "約 30 分（Task 1 + 2 完了）"
  completed: "2026-06-07T09:35:00Z"
  tasks_completed: 2
  files_modified: 3
---

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
| 3（checkpoint） | ビジュアル確認 | 未完 — human-verify 待ち | — |

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

## Self-Check: PASSED

- `pagefolio/dialogs/llm_config.py` に `provider_var`・`_on_provider_change`・`effort_var` が存在: 確認済み
- `pagefolio/ui_builder.py` に `self._ocr_buttons` 初期化・append が存在: 確認済み
- `pagefolio/app.py` に `_update_ocr_buttons_state` が存在: 確認済み
- llm_config.py の _apply に api_key 系格納なし（grep 確認）: 確認済み
- コミット 7eea42e 存在: 確認済み
- コミット c4f232b 存在: 確認済み
- ruff check + pytest 293 passed: 確認済み
