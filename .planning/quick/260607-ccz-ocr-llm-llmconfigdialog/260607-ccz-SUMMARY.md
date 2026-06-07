---
quick_id: 260607-ccz
phase: quick
plan: 260607-ccz
subsystem: ocr-dialog
tags: [ocr, ui, llm-config, live-update, 05-05-followup]
completed_date: "2026-06-07"
duration_estimate: "約20分"

key_files:
  modified:
    - pagefolio/ocr_dialog.py
    - tests/test_ocr.py
    - 開発履歴.md

decisions:
  - "_refresh_provider_dependent_ui を _apply_llm_settings から分離してテスト容易性を確保（Tkinter 不使用テスト実現）"
  - "APP_VERSION は 05-05 マイルストーン未完了のため据え置き（05-05 内追加修正扱い）"
  - "provider 再生成の例外は try/except (ValueError, Exception) で保護しダイアログは閉じない（T-CCZ-03）"

dependency_graph:
  requires:
    - "05-05-PLAN.md Task 1-3（OCRDialog 基盤・セッションキー欄・コスト確認ゲート）"
  provides:
    - "OCRDialog._open_llm_config — LLMConfigDialog 起動ボタン"
    - "OCRDialog._apply_llm_settings — settings 更新・永続化・provider 再生成"
    - "OCRDialog._refresh_provider_dependent_ui — UI 可視性再評価（テスト差し替え可能）"
  affects:
    - "pagefolio/ocr_dialog.py — OCRDialog"
    - "tests/test_ocr.py — TestOcrDialogLlmConfig"
---

# Quick Task 260607-ccz: OCR 画面 LLM 設定ボタン追加 Summary

**一言サマリー**: OCRDialog のプロバイダ表示行に「⚙ LLM 設定…」ボタンを追加し、既存 LLMConfigDialog 経由でプロバイダ・モデルをその場で変更・ライブ反映できるようにした（孤立言語キー `ocr_open_llm_config` の実装）。

---

## 完了タスク

| Task | 名前 | コミット | 主要ファイル |
|------|------|---------|-------------|
| 1 | provider 依存ラベル/欄を self 属性化・LLM 設定ボタンとライブ更新メソッドを追加 | `4a258ff` | pagefolio/ocr_dialog.py |
| 2 | ライブ更新ロジックの単体テストを追加・開発履歴を更新 | `4a1e597` | tests/test_ocr.py, 開発履歴.md |
| R1 | （レビュー修正）ライブ更新時の欄位置崩れを before= アンカーで修正 | `139777c` | pagefolio/ocr_dialog.py |
| R2 | （UAT 修正）lmstudio 切替で欄追加時にボタン行が隠れる不具合を _grow_to_fit で修正 | `f210f76` | pagefolio/ocr_dialog.py |

**Task 3（checkpoint:human-verify, gate=blocking）: approved（2026-06-07）**

UAT 手順 1-4 OK。手順 5 で lmstudio 切替時に LM Studio 欄2行が追加され固定高ウィンドウから最下部ボタン行が押し出される不具合を発見 → `_grow_to_fit`（必要時のみ高さ拡張）で修正し再確認 → **approved**。

---

## 実装内容

### Task 1: pagefolio/ocr_dialog.py の変更

1. **provider 表示値ラベルの self 属性化**
   - `tk.Label(prov_row, text=self._provider_display_name(), ...)` を `self._provider_value_label` として保持

2. **LM Studio 欄フレームの self 属性化**
   - サーバ欄フレームを `self._lmstudio_server_frame`
   - モデル欄フレームを `self._lmstudio_model_frame` として保持

3. **LLM 設定ボタンの追加**
   - `prov_row` 内・値ラベルの右隣に `self._llm_config_btn` を配置
   - 言語キー `ocr_open_llm_config`（既存定義済み）を使用

4. **`_open_llm_config` メソッド新設**
   - 実行中ガード（`self._started and not self._done` → return）
   - `LLMConfigDialog(self, self.app.settings, on_apply=self._apply_llm_settings, ...)` を生成

5. **`_apply_llm_settings` メソッド新設**
   - `app.settings.update(llm_settings)` → `_save_settings(app.settings)` 永続化
   - `_refresh_provider_dependent_ui()` で UI ライブ更新
   - provider 再生成（claude: `build_provider`、lmstudio/off: `LMStudioProvider`）
   - 例外は `try/except (ValueError, Exception)` でキャッチ・ダイアログは閉じない

6. **`_refresh_provider_dependent_ui` メソッド新設**
   - プロバイダ表示ラベル configure
   - LM Studio 欄の pack/pack_forget 切替
   - セッションキー欄の pack/pack_forget 切替

7. **実行中ボタン無効化**
   - `_on_run`: `self._started = True` 直後に `_llm_config_btn.state(["disabled"])`
   - `_clear_text`: `run_btn.state(["!disabled"])` と同時に `_llm_config_btn.state(["!disabled"])`

### Task 2: tests/test_ocr.py への追加

`TestOcrDialogLlmConfig` クラス（5 テスト・Tkinter 不使用）:

| テスト | 検証内容 |
|--------|---------|
| `test_apply_updates_settings` | llm_settings が app.settings に反映される |
| `test_apply_persists_via_save_settings` | `_save_settings` が app.settings 引数で1回呼ばれる |
| `test_apply_regenerates_provider_lmstudio_and_claude` | lmstudio → LMStudioProvider、claude → build_provider 経由 provider |
| `test_apply_does_not_leak_api_key` | api_key 系キーが settings に混入しない |
| `test_open_llm_config_blocked_during_run` | 実行中（`_started=True`, `_done=False`）は LLMConfigDialog が生成されない |

**テスト方針**: `_refresh_provider_dependent_ui` を no-op に差し替えた `types.SimpleNamespace` fake で未束縛呼び出し（既存 `TestStartOcrCloudGate` の手法を踏襲）。

---

## 進行状態

**Task 1-2 完了（コミット済み）・Task 3 human-verify 待ち**

Task 3 は `type="checkpoint:human-verify"` かつ `gate="blocking"` のため、本タスクでは実行しない。
オーケストレータ（または人間）が Task 3 の検証を行う必要がある。

---

## 検証結果

- `ruff check .`: グリーン
- `ruff format --check .`: グリーン（35 files already formatted）
- `pytest tests/test_ocr.py`: 58 passed
- `pytest`（全体）: 300 passed
- `python -c "import ast; ast.parse(open('pagefolio/ocr_dialog.py', encoding='utf-8').read())"`: 構文エラーなし

---

## Deviations from Plan

**オーケストレータレビューによる追加修正（コミット `139777c`）**:

- **症状**: `_refresh_provider_dependent_ui` で `pack_forget()` 後に素の `pack()` で再表示すると、Tkinter のスレーブリスト末尾に追加され、LM Studio 欄／セッションキー欄がライブ切替時にダイアログ最下部へ移動してしまうレイアウト崩れ（エグゼキュータも申し送りで同リスクに言及）。
- **原因**: `pack()` は `before=`/`after=` を指定しないと現在パック済みウィジェットの末尾に配置されるため、元の挿入位置が保持されない。
- **対応**: `params_row`（詳細設定行）と進行表示ラベルを `self._params_row` / `self._progress_label` として self 属性化し、`_refresh_provider_dependent_ui` で LM Studio 欄を `before=self._params_row`、セッションキー欄を `before=self._progress_label` で再表示して元位置を保持。
- **検証**: `ruff check .` グリーン、`pytest` 300 passed（リグレッションなし）。初期ビルドは自然順で正しいため build 側は変更不要、`_refresh` のみ対応。

**UAT で発見された追加修正（コミット `f210f76`）**:

- **症状**: claude（LM Studio 欄なし）で開いた OCR ダイアログを lmstudio へ切替えると LM Studio 欄2行が追加され、固定高ウィンドウから最下部のボタン行（実行/キャンセル/閉じる等）が押し出されてクリップされる。
- **原因**: ダイアログは `_center` で固定高に設定されており、ライブ更新で行が増えてもウィンドウが追従しない。`result_frame` の expand では吸収しきれず content 高がウィンドウ高を超過。
- **対応**: `_refresh_provider_dependent_ui` 末尾に `_grow_to_fit()` を追加。`update_idletasks` 後に `winfo_reqheight() > winfo_height()` のとき、位置・幅を維持したまま高さのみ拡張（縮小はしない＝トグル往復で揺れない）。`tk.TclError` は握りつぶし（ウィンドウ破棄競合対策）。
- **検証**: ユーザー目視で再確認 → approved（2026-06-07）。

ただし以下の軽微な設計上の判断を記録する:

**設計判断（偏差ではなくプランの具体化）**:
- `_apply_llm_settings` の docstring を 88 文字以内に収めるため日本語表現を短縮（ruff E501 対応）
- `_apply_llm_settings` 内の `(f)` ラベルコメント（「provider インスタンスの再生成」）が `_refresh_provider_dependent_ui` の呼び出し後にあるが、プランの手順 (c)〜(g) に従い UI 更新と provider 再生成は同メソッド内で順次実行している

---

## Known Stubs

なし — 全フィールドは実装済みコードパスに接続されている。

---

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: confirmed-mitigated | pagefolio/ocr_dialog.py | T-CCZ-01: _apply_llm_settings は api_key 系を含まない llm_settings のみ受け取り、_save_settings 内部の _SENSITIVE_KEYS ガードが最後の砦として機能（実装確認済み） |
| threat_flag: confirmed-mitigated | pagefolio/ocr_dialog.py | T-CCZ-02: 実行中（_started and not _done）は _open_llm_config で即 return・ボタンも disabled（実装確認済み） |
| threat_flag: confirmed-mitigated | pagefolio/ocr_dialog.py | T-CCZ-03: provider 再生成を try/except (ValueError, Exception) で保護・失敗時は logger.error + progress_var 表示のみ（実装確認済み） |

---

## Self-Check: PASSED

- `pagefolio/ocr_dialog.py` に `_open_llm_config` が存在する: ✓
- `pagefolio/ocr_dialog.py` に `_apply_llm_settings` が存在する: ✓
- `pagefolio/ocr_dialog.py` に `self._llm_config_btn` が存在する: ✓
- `pagefolio/ocr_dialog.py` に `self._provider_value_label` が存在する: ✓
- `pagefolio/ocr_dialog.py` に `self._lmstudio_server_frame` / `_lmstudio_model_frame` が存在する: ✓
- `tests/test_ocr.py` に `TestOcrDialogLlmConfig` が存在する: ✓
- コミット `4a258ff` (Task 1): ✓
- コミット `4a1e597` (Task 2): ✓
- `ruff check .` グリーン: ✓
- `pytest` 300 passed: ✓
