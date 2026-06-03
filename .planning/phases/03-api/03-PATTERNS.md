# Phase 3: API 整理と回帰テスト — Pattern Map

**Mapped:** 2026-06-03
**Files analyzed:** 5（変更 4 + 新規 1）
**Analogs found:** 5 / 5

---

## File Classification

| 新規/変更ファイル | Role | Data Flow | 最近傍アナログ | 一致度 |
|------------------|------|-----------|--------------|-------|
| `pagefolio/settings.py` | utility | transform | `pagefolio/settings.py` 自身（末尾追加） | exact |
| `pagefolio/app.py` | provider | request-response | `pagefolio/app.py` :49–51, :346–348（変更） | exact |
| `pagefolio/dialogs/merge.py` | component | request-response | `pagefolio/dialogs/llm_config.py`（同じ read パターン） | role-match |
| `pagefolio/dialogs/llm_config.py` | component | request-response | `pagefolio/dialogs/merge.py`（同じ read パターン） | role-match |
| `pagefolio/__init__.py` | config | — | `pagefolio/__init__.py` 既存 settings ブロック（:34–42） | exact |
| `tests/test_imports.py` | test | — | `tests/test_utils.py` / `tests/test_plugins.py` | role-match |

---

## Pattern Assignments

### `pagefolio/settings.py`（utility — モジュール変数アクセサの追加）

**アナログ:** `pagefolio/settings.py` 末尾の既存パターン（ファイル末尾 :106–107）

**既存のモジュール変数定義パターン**（行 106–107）:
```python
# 現在のフォントサイズ（設定から読み込み後に更新）
_current_font_size = 12
```

**追加する setter/getter パターン**（この直後に追記）:
```python
def set_current_font_size(size: int) -> None:
    """外部からフォントサイズを更新する公開 setter。"""
    global _current_font_size
    _current_font_size = size


def get_current_font_size() -> int:
    """現在のフォントサイズを返す公開 getter。呼び出し時に最新値を返す。"""
    return _current_font_size
```

**注意:** `global` 宣言が必須（関数スコープ内でモジュール変数を代入するため）。
`_make_font` 等と同じ「単純ユーティリティ関数」スタイルで記述する。
docstring は日本語（既存の `_make_font` 行 98 の注釈スタイル `"""フォントタプルを生成するグローバルヘルパー"""` に倣う）。

---

### `pagefolio/app.py`（write 側 — setter 経由への変更）

**アナログ:** `pagefolio/app.py` 現行コード（変更対象）

**現行の write パターン — 変更箇所 1（行 49–51）**:
```python
import pagefolio.settings as _settings_mod

_settings_mod._current_font_size = self.font_size
```

**変更後（ファイル先頭の import ブロック :20–24 に追加）**:
```python
from pagefolio.settings import (
    _apply_theme,
    _load_settings,
    _save_settings,
    set_current_font_size,   # 追加
)
```

**変更後（行 51 の代入を置き換え）**:
```python
set_current_font_size(self.font_size)
```

**現行の write パターン — 変更箇所 2（行 346–348）**:
```python
import pagefolio.settings as _settings_mod

_settings_mod._current_font_size = self.font_size
```

**変更後（ローカル import 文ごと削除し setter 呼び出しに置き換え）**:
```python
set_current_font_size(self.font_size)
```

**既存の import ブロック（参照用、行 20–24）**:
```python
from pagefolio.settings import (
    _apply_theme,
    _load_settings,
    _save_settings,
)
```

---

### `pagefolio/dialogs/merge.py`（read 側 — getter 経由への変更）

**アナログ:** `pagefolio/dialogs/llm_config.py`（同じ `_current_font_size` import パターン）

**現行の import パターン（行 14）**:
```python
from pagefolio.settings import _current_font_size
```

**変更後**:
```python
from pagefolio.settings import get_current_font_size
```

**現行の read パターン 1（行 33 — `MergeOrderDialog.__init__`）**:
```python
self._font_size = _current_font_size
```

**変更後（呼び出し時に最新値を取得）**:
```python
self._font_size = get_current_font_size()
```

**現行の read パターン 2（行 213 — `MergeResizeDialog.__init__`）**:
```python
self._font_size = _current_font_size
```

**変更後**:
```python
self._font_size = get_current_font_size()
```

---

### `pagefolio/dialogs/llm_config.py`（read 側 — getter 経由への変更）

**アナログ:** `pagefolio/dialogs/merge.py`（同じパターン）

**現行の import パターン（行 12）**:
```python
from pagefolio.settings import _current_font_size
```

**変更後**:
```python
from pagefolio.settings import get_current_font_size
```

**現行の read パターン（行 49–51 — フォールバック内）**:
```python
try:
    fs = int(self._font(0)[1])
except Exception:
    fs = _current_font_size
```

**変更後（フォールバック呼び出しを getter に変更）**:
```python
try:
    fs = int(self._font(0)[1])
except Exception:
    fs = get_current_font_size()
```

---

### `pagefolio/__init__.py`（settings ブロックへの再エクスポート追加）

**アナログ:** `pagefolio/__init__.py` 既存 settings ブロック（行 34–42）

**現行の settings ブロック（行 33–42）**:
```python
# 設定ユーティリティ
from pagefolio.settings import (  # noqa: F401
    _apply_theme,
    _detect_system_theme,
    _get_settings_path,
    _load_settings,
    _make_font,
    _resolve_theme,
    _save_settings,
)
```

**変更後（setter/getter を末尾に追加）**:
```python
# 設定ユーティリティ
from pagefolio.settings import (  # noqa: F401
    _apply_theme,
    _detect_system_theme,
    _get_settings_path,
    _load_settings,
    _make_font,
    _resolve_theme,
    _save_settings,
    get_current_font_size,
    set_current_font_size,
)
```

**根拠:** 既存の `__init__.py` は `_apply_theme` / `_make_font` 等のプライベート関数も含めて再エクスポートしている。
`set_current_font_size` / `get_current_font_size` も同じ方針で追加するのが既存パターンと整合する（D-05）。

---

### `tests/test_imports.py`（新規 — import 回帰テスト）

**アナログ 1:** `tests/test_utils.py`（クラス分割・`import pagefolio` パターン）
**アナログ 2:** `tests/test_plugins.py`（クラス分割・シンボル存在確認パターン）

**ファイル先頭の sys.path 設定パターン**（`test_utils.py` 行 11–12 / `test_plugins.py` 行 9–10 から流用）:
```python
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pagefolio
```

**クラス分割パターン**（`test_utils.py` 行 18–19 / `test_plugins.py` 行 16–17 スタイル）:
```python
class TestXxx:
    """責務説明 — どのリファクタリングの検証か明記"""

    def test_yyy(self):
        from pagefolio.xxx import SomeSymbol
        assert SomeSymbol is not None
```

**シンボル存在 assert パターン**（`test_plugins.py` 行 20–23 スタイル）:
```python
def test_init_empty(self):
    pm = pagefolio.PluginManager()
    assert pm.plugins == {}
```

→ `test_imports.py` では `PluginManager()` のようなインスタンス化はしない（D-08）。
代わりに `assert SomeSymbol is not None` または `assert callable(fn)` で完結させる。

**`import pagefolio.settings as _settings_mod` パターン**（`test_utils.py` 行 13）:
```python
import pagefolio.settings as _settings_mod
```
→ `test_imports.py` の `TestSettingsApiImports` 内で setter/getter の roundtrip テストに使える。

**推奨クラス構成**（RESEARCH.md §テスト関数の推奨分割粒度 準拠）:
```
class TestConstantsImports      # REFAC-02: constants / lang / themes
class TestDialogsImports        # REFAC-01: dialogs サブパッケージ
class TestSettingsApiImports    # REFAC-04: settings 公開 API
class TestPackageSurface        # pagefolio トップレベルサーフェス
```

---

## Shared Patterns（共通パターン）

### モジュール先頭 import のスタイル

**出典:** `pagefolio/app.py` 行 20–24 / `pagefolio/__init__.py` 行 34–42

すべての `from pagefolio.settings import ...` は**括弧付き複数行 import** で書く。
単一シンボルでも既存コードの括弧スタイルに揃える。

```python
from pagefolio.settings import (
    existing_func,
    new_func,  # 末尾カンマ付き
)
```

### ロガー定義

**出典:** `pagefolio/settings.py` 行 12 / `pagefolio/dialogs/merge.py` 行 16

変更するファイルはすべてモジュール先頭に以下を持つ（変更不要、確認のみ）:
```python
logger = logging.getLogger(__name__)
```

### テストのヘッドレス安全性

**出典:** `tests/conftest.py` 全体（Tkinter root を立てない設計）

`test_imports.py` のすべてのテストは `import` とシンボル確認のみ。
`tk.Toplevel()` 等のインスタンス化は一切行わない。
`fitz.open()` 等の I/O も行わない（`conftest.py` の `sample_pdf` フィクスチャは不要）。

### ruff 準拠ルール

**出典:** `CLAUDE.md` §禁止事項

- 裸の `except:` 禁止 — `except Exception as e:` 必須
- `# type: ignore` 無断使用禁止
- setter/getter は例外処理不要（単純な代入・参照）だが、`llm_config.py` 行 50 の既存 `except Exception:` は維持する

---

## No Analog Found

アナログなし（全ファイルに明確な既存パターンあり）。

---

## Metadata

**アナログ検索スコープ:** `pagefolio/`, `tests/`
**参照ファイル数:** 7
**パターン抽出日:** 2026-06-03
