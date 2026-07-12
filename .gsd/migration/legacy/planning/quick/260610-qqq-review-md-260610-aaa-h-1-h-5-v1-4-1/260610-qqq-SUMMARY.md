---
phase: quick-260610-qqq
plan: "01"
subsystem: ocr-backend, llm-config-dialog
tags: [hotfix, ocr, max_tokens, provider, llm-config, resize, v1.4.1]
dependency_graph:
  requires: [quick-260610-aaa]
  provides: [v1.4.1 ホットフィックス H-1〜H-5]
  affects: [pagefolio/ocr.py, pagefolio/ocr_dialog.py, pagefolio/dialogs/llm_config.py]
tech_stack:
  added: []
  patterns:
    - build_provider の mt <= 0 クランプ（claude/gemini）
    - before= アンカーによる pack 順制御
    - _resize_to_fit ヘルパーによる動的 geometry 再計算
key_files:
  created: []
  modified:
    - pagefolio/ocr.py
    - pagefolio/ocr_dialog.py
    - pagefolio/dialogs/llm_config.py
    - pagefolio/constants.py
    - tests/test_ocr.py
    - README.md
    - 開発履歴.md
    - .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md
decisions:
  - "H-1 クランプは mt <= 0 のみ（正値はそのまま）。lmstudio 分岐は変更しない（-1 はモデル最大値委譲として許容）"
  - "H-2 の else → elif name in ('lmstudio', '', 'off') 変更で tesseract/プラグイン登録名に build_provider を適用"
  - "H-5 の _resize_to_fit は tk.TclError を最小スコープで保護（ウィンドウ破棄レースへの配慮）"
metrics:
  duration: "約 20 分（RESUME から）"
  completed_date: "2026-06-10"
  tasks_completed: 3
  files_changed: 8
---

# Quick Task 260610-qqq: H-1〜H-5 v1.4.1 ホットフィックス Summary

**One-liner:** OCR max_tokens クランプ・Tesseract 選択時プロバイダ置換防止・並列度再クランプ・LLM 設定ダイアログのセクション配置修正とリサイズ追従を v1.4.1 として修正

## タスク完了状況

| タスク | 名称 | コミット | 主要変更ファイル |
|--------|------|---------|----------------|
| Task 1 RED | H-1/H-2/H-3 回帰テスト追加 | 1077b06 | tests/test_ocr.py |
| Task 1 GREEN | H-1/H-2/H-3 OCR バックエンド修正 | abf13d7 | pagefolio/ocr.py, pagefolio/ocr_dialog.py |
| Task 2 | H-4/H-5 LLM 設定ダイアログ修正 | e74cb63 | pagefolio/dialogs/llm_config.py |
| Task 3 | バージョン更新・ドキュメント追記・品質ゲート | 1319c12 | pagefolio/constants.py, README.md, 開発履歴.md, .planning/…/REVIEW.md, tests/test_ocr.py |

## 修正内容詳細

### H-1: build_provider の max_tokens クランプ（pagefolio/ocr.py）

`settings.py` の `DEFAULT_SETTINGS` が `"ocr_max_tokens": -1` を既定値として持つため、
`settings.get("ocr_max_tokens", 4096)` のフォールバックが効かず、claude/gemini に
`max_tokens=-1` が渡されていた。Anthropic/Gemini API は正の整数必須のため 400 エラーが
発生する見込みだった。

`build_provider` の claude/gemini 分岐で `mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))`
の後に `mt = 4096 if mt <= 0 else mt` のクランプを追加。lmstudio 分岐は変更しない（-1 はモデル最大値委譲として許容）。

### H-2: Tesseract / プラグインプロバイダの置換防止（pagefolio/ocr_dialog.py）

`_on_run` / `_apply_llm_settings` で `else:` が tesseract・プラグイン登録名を巻き込み
`self.provider` が `LMStudioProvider` で上書きされていた。
`else:` を `elif name in ("lmstudio", "", "off"):` に変更し、それ以外は
`build_provider(self.app.settings, plugin_manager=...)` で再生成する分岐を追加。

`_provider_display_name` にも tesseract 分岐を追加（`ocr_provider_name_tesseract` キーを使用）。

### H-3: 並列度の再クランプ（pagefolio/ocr_dialog.py）

provider 再生成後に `self.concurrency = max(1, min(self.provider.max_concurrency, self.concurrency))` を
実行。`GeminiProvider.max_concurrency = 1` が尊重されるようになった。
`_on_run` では `self._render_queue = queue.Queue(maxsize=self.concurrency + 1)` の直前に挿入。

### H-4: LLM 設定ダイアログのセクション配置修正（pagefolio/dialogs/llm_config.py）

`scale_row = tk.Frame(...)` を `self.scale_row = tk.Frame(...)` に変更（self 属性化）。
`_on_provider_change` / `_on_model_change` の全プロバイダ別セクション pack 呼び出しに
`before=self.scale_row` を追加し、セクションが「適用/キャンセル」ボタン行より上に表示されるよう修正。

### H-5: LLM 設定ダイアログのリサイズ追従（pagefolio/dialogs/llm_config.py）

`__init__` の幅 `w` を `self._dialog_w` に変更して保持。
`_resize_to_fit` ヘルパーを追加し `update_idletasks()` → `winfo_reqheight()` から高さを再計算し、
現在位置（`winfo_x()/winfo_y()`）を維持したまま `geometry()` を再適用。
`_on_provider_change` の各分岐末尾と `_on_model_change` 末尾で呼び出す。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] テストファイルの E501 行長超過**
- 発見タスク: Task 3 品質ゲート
- 内容: RED フェーズで追加したテストの日本語 docstring が 88 文字超
- 修正: docstring を短縮して ruff E501 をクリア
- 対象ファイル: tests/test_ocr.py
- コミット: 1319c12（Task 3 コミットに含む）

## 品質ゲート結果

- `ruff check .` : 全パス
- `ruff format --check .` : 全パス（差分なし）
- `pytest` : 405 件全パス

## テスト結果

| テストスイート | 件数 | 結果 |
|---------------|------|------|
| tests/test_ocr.py | 含む | PASS |
| tests/test_ocr_providers.py | 含む | PASS |
| tests/test_provider_ui.py | 含む | PASS |
| 全体 | 405 | PASS |

## バージョン同期確認

| 場所 | 値 |
|------|-----|
| pagefolio/constants.py APP_VERSION | v1.4.1 |
| README.md バッジ | v1.4.1 |
| 開発履歴.md 先頭エントリ | v1.4.1 |

## Known Stubs

なし

## Threat Flags

なし

## 申し送り

### H-1 実 API 未検証の注意

H-1（max_tokens クランプ）はコードレビューに基づく安全側の判断として実施済み。
ただし実際の Anthropic / Gemini API に対して `ocr_max_tokens=-1` を渡した際に 400 エラーが
発生することは実機では未検証（REVIEW.md「着手時の注意」記載通り）。

クランプ自体は安全側（正の整数を保証）であり、実機環境でも正しく動作するはずだが、
次の機会に実 API（API キーあり環境）で確認することを推奨する。

### 次セッションへの申し送り

- v1.4.2 安定化（M-1〜M-11）への着手時は REVIEW.md を参照
- 特に M-1（producer の blocking put）/ M-2（世代ガード欠如）は L-1（二重実装）との
  絡みがあるため、ocr.py ヘルパーと ocr_dialog.py 独自実装の両方を確認すること
- M-3（_supports_effort の誤判定）はリリース後に claude 最新モデル更新で顕在化しやすいため注意

## Self-Check: PASSED

- [x] pagefolio/ocr.py 存在確認: FOUND
- [x] pagefolio/ocr_dialog.py 存在確認: FOUND
- [x] pagefolio/dialogs/llm_config.py 存在確認: FOUND
- [x] pagefolio/constants.py APP_VERSION=v1.4.1 確認: FOUND
- [x] コミット 1077b06 存在: FOUND
- [x] コミット abf13d7 存在: FOUND
- [x] コミット e74cb63 存在: FOUND
- [x] コミット 1319c12 存在: FOUND
- [x] pytest 405 件全パス: CONFIRMED
- [x] ruff check/format --check 全パス: CONFIRMED
