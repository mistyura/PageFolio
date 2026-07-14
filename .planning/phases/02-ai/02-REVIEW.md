---
phase: 02-ai
reviewed: 2026-07-14T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - pagefolio/dialogs/llm_config/dialog.py
  - pagefolio/dialogs/llm_config/sections.py
  - pagefolio/lang.py
  - pagefolio/ocr_dialog.py
  - pagefolio/ocr_fallback.py
  - pagefolio/settings.py
  - tests/test_ocr.py
  - tests/test_ocr_fallback.py
  - tests/test_prompt_templates.py
  - tests/test_provider_ui.py
findings:
  critical: 2
  warning: 3
  info: 1
  total: 6
status: issues_found
---

# Phase 02-ai: Code Review Report

**Reviewed:** 2026-07-14
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the v1.8.0 Phase 2 テンプレート管理 + プロバイダーフォールバック実装
（`LLMConfigDialog` の `dialog.py`/`sections.py`、`ocr_dialog.py` のフォールバック
オーケストレーション、`ocr_fallback.py` の純ロジック層、`settings.py` の
テンプレート CRUD、`lang.py`）。

`ocr_fallback.py` の純ロジック関数（`next_fallback_candidate` /
`next_summary_candidate`）と `settings.py` のテンプレート CRUD 関数はテストで
よく裏付けられており正しく動作する。`lang.py` の ja/en キーは完全に一致（425/425）。

一方で、(1) LLMConfigDialog の初期化時に「無効な選択」を「直前の有効な選択」として
記憶してしまうガード漏れ、(2) テンプレート管理の「保存/削除/リネーム」が
`current_settings` の浅いコピーに起因して `app.settings` を直接ミューテートし
即座にディスクへ永続化するため「キャンセル」ボタンが実質的にテンプレート操作を
取り消せない、という2件のブロッカー相当の欠陥を発見した。加えて、フォールバック
切替後にプロバイダ表示ラベルが更新されない等のUI整合性の欠陥を複数発見した。

## Critical Issues

### CR-01: Tesseract 未インストール時の初期プロバイダガードが自己参照して機能しない

**File:** `pagefolio/dialogs/llm_config/dialog.py:60, 159-169`

**Issue:**
`__init__` で `self._last_valid_provider` を `current_settings.get("ocr_provider", "off")`
から初期化している（60行目）。これは Tesseract の可用性を一切考慮していない。

```python
# dialog.py:60
self._last_valid_provider = current_settings.get("ocr_provider", "off")
```

一方 `_on_provider_change`（159-169行目）は、選択が `"tesseract"` かつ
`self._tesseract_available` が False のとき、選択を `self._last_valid_provider`
に巻き戻して早期 `return` する:

```python
# dialog.py:159-169
if provider == "tesseract" and not self._tesseract_available:
    self.provider_var.set(self._last_valid_provider)
    self._set_lm_status(..., kind="fail")
    return
self._last_valid_provider = provider
```

ユーザーが以前 Tesseract を選択して `pagefolio_settings.json` に
`"ocr_provider": "tesseract"` が永続化された後、別の環境（Tesseract 未導入の
PC・アンインストール後の再起動など）でダイアログを開くと、初期値
`self._last_valid_provider` は **同じく無効な `"tesseract"`** になる。
`_build()` 末尾で最初に呼ばれる `_on_provider_change()`（sections.py:1150）は
ガードに引っかかり `provider_var.set("tesseract")`（実質無変化）をした上で
即 `return` するため、以降の分岐（`_common_section_heading`・
`effort_frame`/`temperature_frame`・`tesseract_section_frame` 等の pack 処理）
が一切実行されない。結果として:

- 「全プロバイダ共通の設定」見出しが表示されない
- temperature Spinbox が表示されず、ユーザーは編集不能（値は初期値のまま固定）
- Tesseract の精度注記フレームも表示されない（早期 return のため）
- プロバイダ combobox は依然として無効な "tesseract" を表示し続ける

ユーザーが手動で別プロバイダへ切り替えれば自己修復するが、**初回表示時点で
ダイアログが不完全な状態になる**。テスト（`tests/test_provider_ui.py` 他）にも
`_last_valid_provider`/`tesseract_available` にまつわる検証は無く、この
リグレッションは未検出のまま出荷され得る。

**Fix:** 初期化時に Tesseract 可用性を考慮し、無効な初期選択なら安全なフォール
バック値（例: `"off"`）を使う。

```python
# dialog.py __init__ 内、_detect_tesseract() 呼び出しの後に移動して判定する
self._tesseract_available, self._tesseract_langs = _detect_tesseract()
_initial_provider = current_settings.get("ocr_provider", "off")
if _initial_provider == "tesseract" and not self._tesseract_available:
    _initial_provider = "off"
self._last_valid_provider = _initial_provider
```
（`self.provider_var` の初期値も同じ `_initial_provider` を使うよう
`sections.py` 側と整合させること。あるいは `_on_provider_change` のガード側で
「戻し先も無効ならさらに `"off"` へフォールバックする」二重防御にする。）

---

### CR-02: テンプレートの保存/削除/リネームは「キャンセル」で取り消せない（データ消失リスク）

**File:** `pagefolio/dialogs/llm_config/dialog.py:46`, `pagefolio/dialogs/llm_config/sections.py:1244-1329`, `pagefolio/settings.py:188-237`

**Issue:**
`LLMConfigDialog.__init__`（dialog.py:46）は呼び出し元から渡された
`current_settings`（実体は `app.settings` そのもの。`ocr_dialog.py:951-959` の
`LLMConfigDialog(self, self.app.settings, ...)` 参照）を**浅いコピー**する:

```python
# dialog.py:46
self.current_settings = dict(current_settings)
```

`dict(x)` はトップレベルキーのみを複製し、ネストした値（`prompt_templates`
辞書とその中の `items` 辞書）は**同一オブジェクト参照**を共有する。
`_load_settings()`（settings.py）は常に `prompt_templates` キーへデフォルト値を
補完しているため、実運用ではほぼ確実に
`self.current_settings["prompt_templates"] is self.app.settings["prompt_templates"]`
が成立する。

`sections.py` のテンプレート操作ハンドラは、この共有参照経由で
`settings.py` の CRUD 関数を呼ぶ:

```python
# sections.py:1269 (_on_template_save)
save_template(self.current_settings, name, custom_val, summary_val)
...
_save_settings(self.current_settings)   # 1275行目: 即座にディスクへ永続化

# sections.py:1293 (_on_template_delete)
delete_template(self.current_settings, name)
...
_save_settings(self.current_settings)   # 1299行目

# sections.py:1320 (_on_template_rename)
rename_template(self.current_settings, old_name, new_name)
...
_save_settings(self.current_settings)   # 1328行目
```

`save_template`/`delete_template`/`rename_template`（settings.py:188-237）は
すべて `settings["prompt_templates"]["items"]` を**in-place** で変更する
（例: `settings.py:216` の `tpl["items"].pop(name, None)`）。共有参照のため、
これは `app.settings["prompt_templates"]["items"]` を直接書き換え、さらに
即座に `_save_settings()` でディスクへ書き込む。

結果として、ユーザーがダイアログ上で誤ってテンプレートを「削除」した直後に
（他の変更を破棄するつもりで）「キャンセル」ボタン（`self.destroy` のみを
呼び、`on_apply` は一切呼ばれない）を押しても、**削除は既に確定・永続化済み**
で復元できない。同様に「保存」「リネーム」も Apply を経由せず即時確定する。
「キャンセル」ボタンの一般的な UI 契約（変更を破棄する）を裏切っており、
テンプレートの誤削除は実質的に取り消し不能なデータ消失となる。

コード内コメント（dialog.py:461-469）はこの挙動を意図した設計として説明して
いるが、"キャンセル" というラベルの下でユーザーに誤った期待を抱かせる点、
および削除確認ダイアログ（`_on_template_delete` は削除前に確認を出さない —
アクティブテンプレートの削除防止チェックのみ）が無い点から、データ消失
リスクとして扱う。

**Fix:** 以下のいずれかで対処する。
1. ダイアログを開く際、呼び出し元で `current_settings` を渡す前に
   `prompt_templates` を含めディープコピーする（`copy.deepcopy` あるいは
   `{"active": ..., "items": dict(items)}` の明示的コピー）。これにより
   ダイアログ内の CRUD 操作が呼び出し元の `app.settings` を汚染しなくなる。
   ただし、この場合「即時永続化」という現行仕様自体を見直す必要がある
   （Apply を経ずにテンプレートだけ確定させたいのか、全体を Apply 時に
   一括確定させたいのかの設計判断が必要）。
2. 現行の「即時確定」仕様を維持するなら、`_on_template_delete` に
   `messagebox.askyesno` の削除確認を追加し、少なくとも誤操作を1段階
   防止する。

```python
# 対処案1（推奨）: __init__ でネスト構造もコピーする
import copy
self.current_settings = copy.deepcopy(dict(current_settings))
```

## Warnings

### WR-01: フォールバック切替後、プロバイダ/モデル表示ラベルと LM Studio 欄の可視性が更新されない

**File:** `pagefolio/ocr_dialog.py:808-849, 305, 2367-2418`

**Issue:**
`_provider_display_name()`（808-828行目）と `_provider_model_name()`
（830-849行目）はいずれも `self.app.settings.get("ocr_provider", "")` を
参照して表示文字列を決める。フォールバック実行中は `self._active_ocr_settings`
（`_switch_to_fallback_provider` が構築する `fb` スナップショット）だけが
実際の送信先プロバイダを表す設定であり、`self.app.settings` は
Pitfall 4 の方針どおり一切書き換えられない（`_switch_to_fallback_provider`
コメント参照）。

`_provider_display_name` は `isinstance(self.provider, ClaudeProvider)` 等の
フォールバックも持つが、`or` の左辺 `name == "claude"` が
`self.app.settings` 由来で真のままなので、実際に `self.provider` が
`GeminiProvider` へ差し替わっていても短絡評価でクロード表示のまま残る:

```python
# ocr_dialog.py:818
if name == "claude" or isinstance(self.provider, ClaudeProvider):
    return self._L["ocr_provider_name_claude"]
```

さらに `_build()`（305行目）で一度だけ評価される
`show_lmstudio_fields = not self._is_cloud_provider()` を基準に LM Studio 固有欄
（URL/モデル）の pack 可否が決まるが、`_switch_to_fallback_provider`
（2367-2418行目）はこれらの表示を再評価する処理（`_refresh_provider_dependent_ui`
呼び出し）を一切行わない。そのため、クラウドプロバイダ → `lmstudio` への
フォールバックが発生した場合、実際には LM Studio へリクエストが送られている
にもかかわらず、URL/モデル欄がダイアログ上に一切表示されない（確認・変更手段
がない）。

フォールバック確認ダイアログ（`_propose_fallback` の `askyesno`）自体には
正しい送信先が表示されるため初回の同意は正確だが、その後の常設表示
（ヘッダー行の「OCR プロバイダ:」「モデル:」欄）は古いままとなり、
継続的な透明性という設計目標（D-10〜D-12「必ず送信先を明示する」）を
部分的に損なう。

**Fix:** `_switch_to_fallback_provider` の末尾（provider 差し替え成功後）で
表示更新を明示的に呼ぶ。

```python
# _switch_to_fallback_provider 内、self.provider 差し替え直後に追加
self._refresh_provider_dependent_ui()
```

また `_provider_display_name`/`_provider_model_name` は `self.app.settings`
ではなく `self._active_ocr_settings or self.app.settings` を参照するように
修正し、`_active_provider_name()`（2272-2275行目）と同じパターンへ統一する。

---

### WR-02: `_on_summary` は `_active_ocr_settings` を防御的コピーせず `app.settings` を直接エイリアスする

**File:** `pagefolio/ocr_dialog.py:2024-2025`（対比: `1328-1330`）

**Issue:**
`_on_run` は設定スナップショットを確定する際に明示的にコピーする:

```python
# ocr_dialog.py:1328-1330
self._active_ocr_settings = (
    settings if settings is not None else dict(self.app.settings)
)
```

一方 `_on_summary` は同じ役割の変数を代入する際にコピーしない:

```python
# ocr_dialog.py:2024-2025
s = settings if settings is not None else self.app.settings
self._active_ocr_settings = s
```

`settings=None`（通常のサマリ実行）のとき `self._active_ocr_settings` は
`self.app.settings` そのものへのエイリアスになる。現状のコードはこの `s` を
読み取り専用でしか使っておらず直ちに実害はないが、`_on_run` と挙動が
非対称であり、将来 `_on_summary` 系の経路に `s[...] = ...` のような
書き込みが追加された場合、Pitfall 4（「app.settings は一切書き換えない」）
が静かに破られる回帰を生みやすい構造になっている。

**Fix:** `_on_run` と同じ防御的コピーへ統一する。

```python
s = settings if settings is not None else dict(self.app.settings)
```

---

### WR-03: `_check_cloud_api_key`/表示系ヘルパーの「未知プロバイダ」フォールバック文言が `ocr_api_key_missing`（Claude 用文言）に固定される

**File:** `pagefolio/ocr_dialog.py:1283-1290`

**Issue:**
```python
msg_key = {
    "claude": "ocr_api_key_missing",
    "gemini": "ocr_api_key_missing_gemini",
    "runpod": "ocr_api_key_missing_runpod",
}.get(name, "ocr_api_key_missing")
```
プラグイン登録プロバイダ等、`claude`/`gemini`/`runpod` 以外のクラウド系
プロバイダ名（`_is_cloud_provider` はこの3種のみを isinstance でクラウド
判定するため通常到達しないが、プラグインが `OCRAPIKeyError` を送出する
実装をした場合など）でこの分岐に入ると、`env_var` はプラグイン名に応じて
正しく解決されるにもかかわらず、メッセージ本文は Claude 固有の文言
（`ocr_api_key_missing`。`{env_var}` プレースホルダのみ汎用）を使う。
実害は限定的（プレースホルダで env_var 自体は正しく埋まる）だが、
「Claude 固有の言い回し」が他プロバイダのエラーにも出てしまう点は
軽微な文言不整合。

**Fix:** 汎用フォールバック文言（`ocr_api_key_missing` はプレースホルダのみ
なら現状でも大きな実害はないため、優先度は低い。将来プラグインプロバイダが
このエラー経路を使う場合に備え、汎用文言をコメントで明示しておくとよい）。

## Info

### IN-01: `_has_unsaved_template_changes` は「外部ファイル連動モード」以外では常に False を返す

**File:** `pagefolio/dialogs/llm_config/sections.py:1154-1175`

**Issue:**
コメント（1158-1161行目）で明示されている意図的な設計だが、通常モード
（外部 md ファイル未使用）でテンプレートを切り替えると、入力欄の未保存の
編集内容は確認なしに黙って破棄される。D-05 の対象が明示的に「外部ファイル
連動モードでは」に限定されているため意図的な仕様だが、通常モードでも
入力欄の内容とアクティブテンプレートの保存済み内容が異なる場合に同様の
確認を出すことは、ユーザー体験として一貫性があり検討の価値がある
（バグではなく改善余地としての記録）。

**Fix:** 対応不要（設計判断として容認可能）。将来的にテンプレート未保存
差分の確認を全モードへ拡張する場合は `_has_unsaved_template_changes` の
早期 return を外す。

---

_Reviewed: 2026-07-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
