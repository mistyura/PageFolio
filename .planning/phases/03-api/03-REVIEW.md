---
phase: 03-api
reviewed: 2026-06-03T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - pagefolio/settings.py
  - pagefolio/__init__.py
  - pagefolio/app.py
  - pagefolio/dialogs/merge.py
  - pagefolio/dialogs/llm_config.py
  - tests/test_imports.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# フェーズ 03: コードレビュー報告書

**レビュー日時:** 2026-06-03T00:00:00Z
**深度:** standard
**レビュー対象ファイル数:** 6
**ステータス:** issues_found

## サマリー

REFAC-04（`set_current_font_size` / `get_current_font_size` の公開 API 化）と TEST-03（import 回帰テスト追加）を対象にレビュー。

D-02（スタレバインディング）の解消については、`dialogs/merge.py` と `dialogs/llm_config.py` のどちらも `__init__` 内でその都度 `get_current_font_size()` を呼ぶよう変更されており、モジュールロード時に古い値を束縛する問題は正しく解消されている。`global` 宣言も `set_current_font_size` 内で正しく記述されており、setter/getter の実装自体に問題はない。

一方で、CLAUDE.md 規約への違反（裸の `except Exception:` + ロガー欠如）が今回の変更ファイル内に残存しており、さらにデフォルト値の不整合・プライベートシンボルの公開エクスポートという保守上の問題も検出された。

---

## Warnings

### WR-01: `except Exception:` にロガー呼び出しがない（CLAUDE.md 規約違反）

**ファイル:** `pagefolio/dialogs/llm_config.py:48-51`

**Issue:**
今回の変更対象行（`_current_font_size` → `get_current_font_size()` への置き換え）を含むブロックで、例外を捕捉しても `logger` への記録が一切ない。CLAUDE.md は「裸の `except:` 句は禁止。必ず `except Exception as e:` の形で、かつ最低でも `logger` 呼び出しを行う」と定めている。本ブロックは `except Exception:` であり `as e` がないため規約に違反する。

```python
# 現在（違反）
try:
    fs = int(self._font(0)[1])
except Exception:
    fs = get_current_font_size()
```

**Fix:**
```python
try:
    fs = int(self._font(0)[1])
except Exception as e:
    logger.debug("フォントサイズ取得失敗、デフォルト値を使用: %s", e)
    fs = get_current_font_size()
```

---

### WR-02: `font_size` デフォルト値の不整合（`settings.py` vs `app.py`）

**ファイル:** `pagefolio/app.py:48` および `pagefolio/app.py:343`

**Issue:**
`_load_settings()` のデフォルト辞書では `"font_size": 12` を定義している（`settings.py:33`）。しかし `app.py` では `self.settings.get("font_size", 10)` というフォールバックを 2 か所で使用している（`__init__` と `_apply_settings`）。`_load_settings()` が呼ばれた後の `self.settings` に `font_size` キーが存在しない状況は通常起こらないが、設定辞書が外部から渡される `_apply_settings` では `10` というフォールバックが `_current_font_size` の初期値（`12`）および `_load_settings` のデフォルト（`12`）と矛盾する。フォントサイズのデフォルト値が 3 か所でバラバラになっている。

**Fix:**
`settings.py` の `_load_settings` のデフォルト値を単一の正典として扱い、`app.py` のフォールバックを合わせる。

```python
# app.py __init__ (line 48) と _apply_settings (line 343) のどちらも
self.font_size = self.settings.get("font_size", 12)  # 10 → 12 に統一
```

または定数化する:

```python
# settings.py
DEFAULT_FONT_SIZE = 12
_current_font_size = DEFAULT_FONT_SIZE

# app.py
from pagefolio.settings import DEFAULT_FONT_SIZE
self.font_size = self.settings.get("font_size", DEFAULT_FONT_SIZE)
```

---

### WR-03: `test_setter_getter_roundtrip` のリセットが `finally` で保護されていない

**ファイル:** `tests/test_imports.py:202-208`

**Issue:**
```python
def test_setter_getter_roundtrip(self):
    set_current_font_size(14)
    assert get_current_font_size() == 14
    set_current_font_size(12)  # 元に戻す（他テストへの副作用を防ぐ）
```

`assert get_current_font_size() == 14` が失敗した場合（これはテスト自体のバグ検出時に発生し得る）、`set_current_font_size(12)` は実行されず `_current_font_size` が `14` のままになる。後続テストはモジュールグローバル状態として `14` を受け取る。コメントに「他テストへの副作用を防ぐ」と書かれているにもかかわらず、防止が不完全。

**Fix:**
```python
def test_setter_getter_roundtrip(self):
    from pagefolio.settings import get_current_font_size, set_current_font_size
    original = get_current_font_size()
    try:
        set_current_font_size(14)
        assert get_current_font_size() == 14
    finally:
        set_current_font_size(original)  # 失敗時も必ず元に戻す
```

---

## Info

### IN-01: `pagefolio/__init__.py` がプライベートシンボルを公開 API としてエクスポートしている

**ファイル:** `pagefolio/__init__.py:34-43`

**Issue:**
`_load_settings`、`_save_settings`、`_apply_theme`、`_make_font`、`_detect_system_theme`、`_get_settings_path`、`_resolve_theme` という `_` プレフィックスを持つシンボルが `pagefolio` トップレベルから参照可能な状態になっている。これは今回追加された `set_current_font_size` / `get_current_font_size` とは別の既存の問題だが、`test_settings_util_symbols` テストがこれらプライベートシンボルをサーフェス保証として `assert` しており、リファクタリングの障壁となる。Python の慣習では `_` プレフィックスは内部実装を意味する。

**Fix:**
今回の変更スコープ外だが、次回リファクタリングで `__init__.py` から `_` プレフィックスシンボルの再エクスポートを除去し、`test_settings_util_symbols` も削除または公開 API 版に書き換えることを推奨する。

---

### IN-02: `set_current_font_size` に実行時型バリデーションがない

**ファイル:** `pagefolio/settings.py:110-113`

**Issue:**
型アノテーションは `size: int` と宣言されているが、実行時は任意の型を受け付ける。`set_current_font_size("hello")` を呼び出しても例外が発生せず、後続の `max(7, self.font_size + delta)` で `TypeError` が起きるまで問題が顕在化しない。今回の変更範囲（REFAC-04）で新設された関数であり、setter に最低限の型ガードを入れると堅牢性が上がる。

**Fix:**（オプション、Python 3.8 互換）
```python
def set_current_font_size(size: int) -> None:
    """現在のフォントサイズを更新する公開 setter"""
    global _current_font_size
    if not isinstance(size, int):
        raise TypeError(f"font size must be int, got {type(size).__name__}")
    _current_font_size = size
```

ただし CLAUDE.md はバリデーションなしの単純代入（D-04）を設計方針として記録しているため、採否はプロジェクト判断に委ねる。

---

_レビュー日時: 2026-06-03T00:00:00Z_
_レビュアー: Claude (gsd-code-reviewer)_
_深度: standard_
