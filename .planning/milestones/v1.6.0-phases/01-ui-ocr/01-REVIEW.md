---
phase: 01-ui-ocr
reviewed: 2026-06-18T10:02:20Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - pagefolio/ocr_dialog.py
  - pagefolio/ui_builder.py
  - pagefolio/constants.py
  - tests/test_provider_ui.py
  - tests/test_ocr.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues
---

# Phase 01 (01-ui-ocr): コードレビュー報告

**レビュー日時:** 2026-06-18T10:02:20Z
**深度:** standard
**レビュー対象ファイル数:** 5
**ステータス:** issues（助言レベル・ブロックなし）

## サマリー

UI リファクタの差分を敵対的視点でレビューした。フォーカス 5 項目はおおむね健全:

1. **ライブ同期の正当性 (合格):** `_sync_param_vars_from_settings` は `_apply_llm_settings` の line 810 で呼ばれ、LM Studio 専用 `elif` ブロック（line 843）の外・`try` の前にある。全プロバイダ（claude/gemini/lmstudio/off/tesseract）で実行される。claude/gemini 適用後に読み取り専用 Spinbox がスタール値を表示するリスクはない。
2. **読み取り専用の徹底 (合格):** 4 つの数値 Spinbox（scale/timeout/max_tokens/temperature）はすべて `state="readonly"` + `fg=C["TEXT_SUB"]`。readonly は programmatic な `.set()` を妨げないため値表示は維持される。実行時専用フィールド（`force_ocr_var` Checkbutton・セッションキー欄 `_key_frame`・preset）はロックされていない。
3. **機密漏洩 (合格):** 同期パスは値をログ出力も永続化もしない（`logger` 呼び出しなし）。`_SENSITIVE_KEYS` ガード（settings.py）は本差分で未変更。API キーは `llm_settings` に含まれず T-05-12 ガードは維持。
4. **レイアウト退行 (合格):** スライダー不変条件は保持。range 0.5–2.5、`thumb_zoom_var`、`<ButtonRelease-1>` → `_on_thumb_zoom_release` すべて維持。`viewer.py` / `settings.py` は差分に含まれず未変更。
5. **規約:** テーマ色は `C[...]` 経由、フォントは `self._font()`、裸 except・`# type: ignore`・`pyproject.toml` 編集なし。新規 LANG キー追加なし（ja/en パリティ影響なし）。`ruff check` 合格・対象テスト 168 件合格。

検出した課題は助言レベルのみ（BLOCKER なし）。最大の論点は model_combo / fetch ボタンの `state="disabled"` 恒久化に伴う **デッドコード化した `_fetch_models`** と、再表示時に再有効化されない点（WR-01）。

## Warnings

### WR-01: `model_combo` / fetch ボタンの恒久 disabled により `_fetch_models` がデッドコード化

**File:** `pagefolio/ocr_dialog.py:290,297,548-568`
**Issue:**
`model_combo`（line 290）と fetch ボタン（line 297）がビルド時に `state="disabled"` で固定され、これを再有効化する経路が存在しない（`_refresh_provider_dependent_ui` は frame の可視性のみ再評価し state は触らない）。結果として:
- fetch ボタンの `command=self._fetch_models`（line 296）は UI から到達不能。
- `OCRDialog._fetch_models`（line 548-568）はデッドコード。仮に呼ばれても `self.model_combo["values"] = models`（line 567）を disabled な combo に書き込み、ユーザーは選択できない。
LM Studio のモデル取得・選択は `LLMConfigDialog`（独自 `_fetch_models` / `lm_model_combo` / `lm_studio_model` 永続化）へ移管済みのため**機能退行ではない**が、ダイアログ上に操作不能な fetch ボタンが残り誤解を招く。

**Fix:** いずれか。
- (推奨) OCRDialog 側の `_fetch_models` メソッドと fetch ボタン・モデル選択 combo を表示専用ラベル化、もしくは LM Studio 欄から削除し、モデル名は読み取り専用ラベルで表示する。
- 当面残すなら、コメントで「表示専用・操作は LLMConfigDialog 側」と明示し、`_fetch_models` に到達不能である旨を docstring に追記する。

```python
# 例: 表示専用ラベルへ置換（操作は LLM 設定ダイアログ側に集約）
tk.Label(
    mf, textvariable=self.model_var, bg=C["BG_DARK"],
    fg=C["TEXT_SUB"], font=self._font(-1), anchor="w",
).pack(side="left", fill="x", expand=True, padx=4)
```

### WR-02: `_sync_param_vars_from_settings` は `try` の外にあり、不正 settings 値で例外が `_apply_llm_settings` を貫通する

**File:** `pagefolio/ocr_dialog.py:810,875-888`
**Issue:**
`self._sync_param_vars_from_settings()`（line 810）はプロバイダ再生成の `try/except`（line 813-873）より前で呼ばれる。`scale_var` 等は `DoubleVar` / `IntVar` のため、`app.settings` に非数値（例: 外部編集された JSON で `"ocr_timeout": "abc"`）が入っていると `var.set()` が `tk.TclError` を送出し、`_apply_llm_settings` 全体（永続化済みだが provider 再生成前）が中断する。通常経路では `llm_config` が clamp/coerce 済み（line 876-899）のため実害は小さいが、外部編集 settings に対して堅牢でない。

**Fix:** 同期を防御的にするか、`try` 内へ移動する。

```python
def _sync_param_vars_from_settings(self):
    settings = self.app.settings
    try:
        self.scale_var.set(float(settings.get("ocr_scale", 1.5)))
        self.timeout_var.set(int(settings.get("ocr_timeout", 120)))
        self.max_tokens_var.set(int(settings.get("ocr_max_tokens", -1)))
        self.temperature_var.set(float(settings.get("ocr_temperature", 0.1)))
    except (tk.TclError, ValueError, TypeError) as e:
        logger.warning("パラメータ表示の同期に失敗しました: %s", e)
```

## Info

### IN-01: テストスタブの重複（test_ocr.py と test_provider_ui.py で同等の sync スタブを再実装）

**File:** `tests/test_ocr.py:907-923`, `tests/test_provider_ui.py:447-471`
**Issue:**
両テストファイルが「Tk 非生成で `OCRDialog._sync_param_vars_from_settings` を未束縛呼び出しするスタブ」をほぼ同形で重複定義している（`_VarStub` / `SimpleNamespace` + lambda）。将来 var 追加時に二箇所メンテが必要。
**Fix:** `conftest.py` に共通フィクスチャ（例: `make_param_sync_stub`）を切り出して共有する。テスト support のみで挙動影響はなく優先度は低い。

### IN-02: 同期の既定値がマジックナンバーで二重管理

**File:** `pagefolio/ocr_dialog.py:884-887`, `pagefolio/dialogs/llm_config.py:350,388,426,455,880-899`
**Issue:**
既定値 `1.5 / 120 / -1 / 0.1` が `ocr_dialog._sync_param_vars_from_settings` と `llm_config` の双方にハードコードされている。現状は一致しているが（本レビューで照合済み）、片方だけ変更されると表示と実値が乖離する。
**Fix:** 既定値を `constants.py` 等の定数（例: `OCR_PARAM_DEFAULTS`）へ集約し両所から参照する。

---

_Reviewed: 2026-06-18T10:02:20Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
