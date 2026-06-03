# Phase 3: API 整理と回帰テスト — Research

**Researched:** 2026-06-03
**Domain:** Python モジュール API 設計 / pytest import 回帰テスト
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** REFAC-04 は write 側だけでなく read 側も含めて完全に公開 API 化する。
  `app.py` の直接代入を setter 経由にするだけでなく、`dialogs/merge.py` / `dialogs/llm_config.py` の
  `from pagefolio.settings import _current_font_size` も getter 経由の参照に変更する。
- **D-02:** getter 化により stale binding（import 時点の int 値固定）を修正する。
  dialogs のフォントサイズが「生値（実行時の設定値）」になる軽微な挙動変化を許容する。
- **D-03（不採用）:** app.py の write のみ setter 化し dialogs の read はそのまま残す最小案は不採用。
- **D-04:** `set_current_font_size(size)` は単純代入のみ。クランプ等のバリデーションは入れない。
- **D-05（裁量あり）:** getter 命名（例: `get_current_font_size()`）と `pagefolio/__init__.py` への
  再エクスポート追加は executor 裁量。対称性のため追加を推奨。
- **D-06:** TEST-03 の検証手法は「明示 import 文 + シンボル存在 assert」。`importlib` 動的方式は不採用。
- **D-07:** TEST-03 が最低限カバーするパス（後述の「検証対象 import パス」参照）。
- **D-08:** dialogs モジュールのテストは import のみ・インスタンス化なし。
- **D-09:** import 回帰テストは新規 `tests/test_imports.py` に集約する。

### Claude's Discretion

- getter の正確な名前（`get_current_font_size()` 等）
- `pagefolio/__init__.py` 公開サーフェスへの setter/getter 追加可否（対称性のため追加推奨）
- `test_imports.py` 内のテスト関数の分割粒度と assert の具体形
- 実装順序（REFAC-04 を先に行い、その新 import パスも TEST-03 に含めるのが自然）

### Deferred Ideas (OUT OF SCOPE)

- setter のバリデーション（クランプ 8〜16 等）
- `themes.C` の in-place 更新等、他の private モジュール変数の API 化
- サムネイル仮想化・暗号化 PDF・印刷機能・OCR エンジン拡張（v2 スコープ外）

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REFAC-04 | `settings._current_font_size` への外部アクセスを公開関数に変更する。`set_current_font_size(size)` を `settings.py` に追加し、write 側 (`app.py`) と read 側 (`dialogs/merge.py`, `dialogs/llm_config.py`) 両方を公開 API 経由に変更する | write 側 2 箇所・read 側 3 箇所の行番号を確認済み（後述） |
| TEST-03 | REFAC-01〜04 の import 回帰テストを `tests/test_imports.py`（新規）に整備する | 現行 `__init__.py` の公開サーフェスを実コードから抽出・検証済み（後述） |

</phase_requirements>

---

## Summary

Phase 3 は **2 つの独立した作業** から成る小規模フェーズである。

第一の作業（REFAC-04）は、`pagefolio/settings.py` の可変モジュール変数 `_current_font_size`
に対して外部から直接アクセスしているコードを、新規の公開関数 `set_current_font_size()` /
`get_current_font_size()` 経由に切り替えるリファクタリングである。
変更箇所は write 側 2 箇所（`app.py` 行 51・348）と read 側 3 箇所（`dialogs/merge.py` 行 14・33・213、
`dialogs/llm_config.py` 行 12・51）に限定される。挙動変化は getter 化による stale binding 解消のみで、
これは意図した修正である（D-02）。

第二の作業（TEST-03）は、Phase 1〜3 のリファクタリングで変更された import パスが壊れていないことを
`tests/test_imports.py` に明示 import + assert で記録する。Tk root を必要としない import-only テストで
CI/ヘッドレス環境でも安全に実行できる。

**Primary recommendation:** REFAC-04 を先に実装して setter/getter の import パスを確定させ、
その後 TEST-03 で REFAC-01〜04 すべての import 表面を一括カバーする順序を推奨する。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| フォントサイズ状態の書き込み | API / Backend (settings.py) | — | モジュールレベル状態の変更は `settings.py` が一元管理すべき |
| フォントサイズ状態の読み出し | API / Backend (settings.py) | — | 同上；getter 経由で最新値を返す |
| フォントサイズの UI 適用 | Frontend (app.py, dialogs) | — | 読み出した値を UI に使う責務はフロントエンド側 |
| import 表面の正確性保証 | テスト層 (tests/) | — | 回帰テストで機械的に保証する |

---

## Standard Stack

### Core（外部ライブラリの追加なし）

このフェーズは既存の Python 標準ライブラリと pytest のみで完結する。
新規の外部ライブラリは不要。

[VERIFIED: コードベース実測]

| 用途 | 使用手段 | 理由 |
|------|---------|------|
| setter/getter 実装 | Python 標準（関数定義のみ） | モジュール変数アクセスは標準機能で十分 |
| import 回帰テスト | pytest（既存、`pyproject.toml` 設定済み） | 既存テストインフラを再利用 |
| lint / format | ruff check / ruff format（既存設定） | CLAUDE.md 必須ルール |

### Package Legitimacy Audit

> 新規外部パッケージのインストールはなし。このセクションは該当なし。

新規インストールパッケージなし — 監査対象ゼロ。

---

## Architecture Patterns

### REFAC-04 の変更パターン

#### setter/getter の追加（settings.py）

`settings.py` 末尾の `_current_font_size = 12` の直後に 2 つの公開関数を追加する。

```python
# Source: コードベース実測 + Python 標準慣習 [VERIFIED]

# 現行（settings.py 末尾）
_current_font_size = 12

# 追加する公開 API
def set_current_font_size(size: int) -> None:
    """外部からフォントサイズを更新する公開 setter。"""
    global _current_font_size
    _current_font_size = size

def get_current_font_size() -> int:
    """現在のフォントサイズを返す公開 getter。呼び出し時に最新値を返す。"""
    return _current_font_size
```

**注意点:** `global` 宣言が必要（関数スコープ内でモジュールレベル変数を代入するため）。
[VERIFIED: Python 言語仕様 `global` ステートメント]

#### write 側の変更（app.py）

| 行番号 | 現行コード | 変更後 |
|--------|-----------|-------|
| 49–51 | `import pagefolio.settings as _settings_mod` + `_settings_mod._current_font_size = self.font_size` | `from pagefolio.settings import set_current_font_size` を先頭 import に追加し、`set_current_font_size(self.font_size)` を呼ぶ |
| 346–348 | `import pagefolio.settings as _settings_mod` + `_settings_mod._current_font_size = self.font_size` | 同上（`import pagefolio.settings as _settings_mod` のローカル import 文も削除） |

**実測確認:** `app.py` の現行 `_settings_mod` ローカル import は `__init__` (:49) と
`_apply_settings` (:346) の 2 箇所にそれぞれ存在する。ファイル先頭の import ブロックへの
`set_current_font_size` 追加でまとめて代替できる。[VERIFIED: コードベース実測]

#### read 側の変更（dialogs/merge.py）

| 行番号 | 現行コード | 変更後 |
|--------|-----------|-------|
| 14 | `from pagefolio.settings import _current_font_size` | `from pagefolio.settings import get_current_font_size` |
| 33 | `self._font_size = _current_font_size` | `self._font_size = get_current_font_size()` |
| 213 | `self._font_size = _current_font_size` | `self._font_size = get_current_font_size()` |

[VERIFIED: コードベース実測]

#### read 側の変更（dialogs/llm_config.py）

| 行番号 | 現行コード | 変更後 |
|--------|-----------|-------|
| 12 | `from pagefolio.settings import _current_font_size` | `from pagefolio.settings import get_current_font_size` |
| 51 | `fs = _current_font_size` | `fs = get_current_font_size()` |

[VERIFIED: コードベース実測]

**llm_config.py の補足:** 行 49–51 は `try: fs = int(self._font(0)[1]) except: fs = _current_font_size`
というフォールバックパターン。`get_current_font_size()` に変更しても意味論は同じ。
[VERIFIED: コードベース実測]

#### `pagefolio/__init__.py` への再エクスポート追加（D-05 推奨）

現行の `__init__.py` は `_apply_theme`, `_make_font` 等の private 関数も再エクスポートしている。
対称性のため、以下を settings ブロックに追加することを推奨する：

```python
# pagefolio/__init__.py の settings ブロックに追加（推奨）
from pagefolio.settings import (  # noqa: F401
    _apply_theme,
    _detect_system_theme,
    _get_settings_path,
    _load_settings,
    _make_font,
    _resolve_theme,
    _save_settings,
    set_current_font_size,   # 追加
    get_current_font_size,   # 追加
)
```

[VERIFIED: コードベース実測 — 既存パターンと整合]

---

### TEST-03 の検証対象 import パス（完全リスト）

CONTEXT.md D-07 に列挙されたパスを、実コードから確認・突き合わせた結果を示す。

#### 1. 公開 API（REFAC-01/02 後方互換）

```python
# Source: pagefolio/__init__.py 実測 [VERIFIED]
from pagefolio.constants import APP_VERSION, LANG, THEMES, C
```

**確認:** `constants.py` が `lang.py` / `themes.py` から `LANG`, `THEMES`, `C` を再エクスポートしており、
後方互換が維持されていることを実測確認済み。`APP_VERSION = "v1.2.6"` も同ファイルに存在。[VERIFIED]

#### 2. dialogs サブパッケージ（REFAC-01）

```python
# Source: pagefolio/dialogs/__init__.py 実測 [VERIFIED]
from pagefolio.dialogs import (
    AboutDialog,
    MergeOrderDialog,
    MergeResizeDialog,
    PluginDialog,
    SettingsDialog,
)
# 個別サブモジュール
from pagefolio.dialogs.about import AboutDialog
from pagefolio.dialogs.settings import SettingsDialog
from pagefolio.dialogs.plugin import PluginDialog
from pagefolio.dialogs.merge import MergeOrderDialog, MergeResizeDialog
from pagefolio.dialogs.llm_config import LLMConfigDialog
```

**差異検出:** `LLMConfigDialog` は `pagefolio/dialogs/__init__.py` では再エクスポートされているが、
`pagefolio/__init__.py` には含まれていない。[VERIFIED: コードベース実測]
TEST-03 では `pagefolio.dialogs.LLMConfigDialog` のパスを検証対象に含めるべきだが、
`pagefolio.LLMConfigDialog`（トップレベル）は現状公開されていない点に注意。
プランナーはこの差分を認識した上でどちらをテストするか決定すること。

#### 3. 分割新モジュール（REFAC-02）

```python
# Source: pagefolio/lang.py, pagefolio/themes.py 実測 [VERIFIED]
from pagefolio.lang import LANG
from pagefolio.themes import THEMES, C
```

[VERIFIED: 各ファイルの先頭確認済み]

#### 4. settings 新公開 API（REFAC-04）

```python
# Phase 3 実装後に追加
from pagefolio.settings import set_current_font_size
from pagefolio.settings import get_current_font_size
```

[ASSUMED — Phase 3 実装前のため、テスト時点で存在しているはず]

#### 5. パッケージ公開サーフェス（`import pagefolio` 経由）

実測した `dir(pagefolio)` の結果（代表的なシンボル）:

```python
import pagefolio
assert hasattr(pagefolio, 'PDFEditorApp')
assert hasattr(pagefolio, 'APP_VERSION')
assert hasattr(pagefolio, 'LANG')
assert hasattr(pagefolio, 'THEMES')
assert hasattr(pagefolio, 'C')
assert hasattr(pagefolio, 'AboutDialog')
assert hasattr(pagefolio, 'SettingsDialog')
assert hasattr(pagefolio, 'PluginDialog')
assert hasattr(pagefolio, 'MergeOrderDialog')
assert hasattr(pagefolio, 'MergeResizeDialog')
assert hasattr(pagefolio, 'PluginManager')
assert hasattr(pagefolio, 'PDFEditorPlugin')
assert hasattr(pagefolio, 'OCRMixin')
assert hasattr(pagefolio, '_load_settings')
assert hasattr(pagefolio, '_save_settings')
assert hasattr(pagefolio, '_apply_theme')
assert hasattr(pagefolio, '_make_font')
# Phase 3 後に追加（D-05 推奨）
assert hasattr(pagefolio, 'set_current_font_size')
assert hasattr(pagefolio, 'get_current_font_size')
```

[VERIFIED: `dir(pagefolio)` 実測]

---

### Tk ヘッドレス import 安全性（D-08）

**実測結果:** `python -c "import pagefolio.dialogs.about; import pagefolio.dialogs.merge; ..."` を
Tk root なしで実行したところ、全モジュールが例外なく import 完了した。[VERIFIED: 実測]

**理由:** すべての dialogs モジュールは `import tkinter` をファイル先頭で行っているが、
tkinter のクラス定義は import 時には評価されない（インスタンス化なし）。
`fitz.open()` 等の I/O も呼ばれない。CI/ヘッドレス環境でも安全。[VERIFIED]

**注意:** `tkinter` 自体は環境に存在している必要がある（Windows 環境では通常インストール済み）。
`tk.Toplevel()` 等のインスタンス化はしないことが前提（D-08 通り）。

---

### テスト関数の推奨分割粒度（Claude's Discretion）

既存テスト群（`test_utils.py`, `test_plugins.py`）はクラスごとに責務を分離している。
`test_imports.py` では以下の分割を推奨する：

```python
# tests/test_imports.py 推奨構造

class TestConstantsImports:
    """REFAC-02: constants / lang / themes の import パス検証"""

class TestDialogsImports:
    """REFAC-01: dialogs サブパッケージの import パス検証"""

class TestSettingsApiImports:
    """REFAC-04: settings 公開 API の import パス検証"""

class TestPackageSurface:
    """pagefolio トップレベルの公開サーフェス検証"""
```

**理由:** クラス分割によりテスト失敗時に「どのリファクタリングで壊れたか」が
クラス名から即座に判別できる。

---

### Recommended Project Structure（変更対象ファイルのみ）

```
pagefolio/
├── settings.py          # set_current_font_size / get_current_font_size 追加
├── app.py               # 直接代入 2 箇所を setter 経由に変更
├── dialogs/
│   ├── merge.py         # _current_font_size 3 箇所を getter 経由に変更
│   └── llm_config.py   # _current_font_size 2 箇所を getter 経由に変更
└── __init__.py          # setter/getter を再エクスポートに追加（推奨）

tests/
└── test_imports.py      # 新規作成（TEST-03）
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| import パスの正確性検証 | 動的なモジュールスキャン | 明示 import 文 + assert（D-06） | 壊れた箇所が即座にわかる |
| フォントサイズのグローバル状態管理 | 複雑な Observer/Event パターン | 単純な getter/setter（D-04） | リファクタリングは挙動変更を最小化するのが原則 |

---

## Common Pitfalls

### Pitfall 1: `global` 宣言の欠落

**What goes wrong:** `set_current_font_size` 内で `global _current_font_size` を宣言しないと、
関数スコープのローカル変数として扱われ `UnboundLocalError` が発生する。
**Why it happens:** Python は関数内の代入をデフォルトでローカルスコープとして扱う。
**How to avoid:** setter 関数内に `global _current_font_size` を必ず書く。
**Warning signs:** `pytest` 実行時に `UnboundLocalError` が出る。

### Pitfall 2: stale binding の残存

**What goes wrong:** dialogs で `import _current_font_size` のまま（getter に変えず）残すと、
import 時点の値 12 が束縛されたままになり、アプリ起動後に設定変更しても反映されない。
**Why it happens:** `from module import VAR` はその時点の値を変数に束縛する（参照ではなく値コピー）。
**How to avoid:** 使用箇所で `get_current_font_size()` を呼ぶ（D-02）。
**Warning signs:** フォントサイズ変更後にダイアログのサイズが変わらない。

### Pitfall 3: ローカル import 文の削除漏れ（app.py）

**What goes wrong:** `__init__` (:49) と `_apply_settings` (:346) にそれぞれある
`import pagefolio.settings as _settings_mod` のローカル import 文を削除しないと、
不要な import が残り ruff が `F401` を報告する可能性がある。
**How to avoid:** setter への変更と同時にローカル import 文も削除する。

### Pitfall 4: TEST-03 で `LLMConfigDialog` の帰属を誤る

**What goes wrong:** `LLMConfigDialog` は `pagefolio.dialogs` から import 可能だが、
`pagefolio.__init__.py` には再エクスポートされていない。
誤って `from pagefolio import LLMConfigDialog` をテストに書くと失敗する。
**How to avoid:** `from pagefolio.dialogs import LLMConfigDialog` でテストする。
[VERIFIED: コードベース実測]

---

## Code Examples

### setter の実装パターン（REFAC-04）

```python
# Source: pagefolio/settings.py 末尾に追加 [VERIFIED パターン]

_current_font_size = 12  # 既存行（変更なし）


def set_current_font_size(size: int) -> None:
    """現在のフォントサイズを更新する。"""
    global _current_font_size
    _current_font_size = size


def get_current_font_size() -> int:
    """現在のフォントサイズを返す。"""
    return _current_font_size
```

### TEST-03 の assert パターン

```python
# Source: 既存テスト群のパターン踏襲 [VERIFIED]

class TestConstantsImports:
    def test_app_version(self):
        from pagefolio.constants import APP_VERSION
        assert APP_VERSION is not None

    def test_lang_from_lang_module(self):
        from pagefolio.lang import LANG
        assert "ja" in LANG

    def test_themes_from_themes_module(self):
        from pagefolio.themes import THEMES, C
        assert "dark" in THEMES
        assert isinstance(C, dict)

    def test_constants_backward_compat(self):
        from pagefolio.constants import APP_VERSION, LANG, THEMES, C
        assert APP_VERSION is not None
        assert LANG is not None
        assert THEMES is not None
        assert C is not None


class TestDialogsImports:
    def test_dialogs_subpackage(self):
        from pagefolio.dialogs import (
            AboutDialog,
            MergeOrderDialog,
            MergeResizeDialog,
            PluginDialog,
            SettingsDialog,
        )
        # インスタンス化せずシンボル存在のみ確認
        assert AboutDialog is not None
        assert SettingsDialog is not None
        assert PluginDialog is not None
        assert MergeOrderDialog is not None
        assert MergeResizeDialog is not None

    def test_dialogs_individual_modules(self):
        from pagefolio.dialogs.about import AboutDialog
        from pagefolio.dialogs.llm_config import LLMConfigDialog
        from pagefolio.dialogs.merge import MergeOrderDialog, MergeResizeDialog
        from pagefolio.dialogs.plugin import PluginDialog
        from pagefolio.dialogs.settings import SettingsDialog
        assert LLMConfigDialog is not None  # __init__.py には未掲載だが個別モジュールは有効


class TestSettingsApiImports:
    def test_public_setter_exists(self):
        from pagefolio.settings import set_current_font_size
        assert callable(set_current_font_size)

    def test_public_getter_exists(self):
        from pagefolio.settings import get_current_font_size
        assert callable(get_current_font_size)

    def test_setter_getter_roundtrip(self):
        from pagefolio.settings import get_current_font_size, set_current_font_size
        set_current_font_size(14)
        assert get_current_font_size() == 14
        set_current_font_size(12)  # 元に戻す


class TestPackageSurface:
    def test_top_level_symbols(self):
        import pagefolio
        assert hasattr(pagefolio, 'PDFEditorApp')
        assert hasattr(pagefolio, 'APP_VERSION')
        assert hasattr(pagefolio, 'LANG')
        assert hasattr(pagefolio, 'THEMES')
        assert hasattr(pagefolio, 'C')
        assert hasattr(pagefolio, 'PluginManager')
        assert hasattr(pagefolio, 'PDFEditorPlugin')
```

---

## Runtime State Inventory

> このフェーズはコード編集のみで、データベース・OS 登録状態・ビルド成果物の変更を伴わない。

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — 設定 JSON のスキーマ変更なし | なし |
| Live service config | None — n8n / 外部サービス不使用 | なし |
| OS-registered state | None | なし |
| Secrets/env vars | None — API キー等の変更なし | なし |
| Build artifacts | None — パッケージ名・pyproject.toml 変更なし | なし |

---

## Environment Availability

> Step 2.6: このフェーズは既存 Python 環境と pytest のみを使用する。

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.8+ | 全コード | ✓ | 実行環境に存在（コードベース動作確認済み） | — |
| pytest | TEST-03 | ✓ | 9.0.2（`pyproject.toml` 固定） | — |
| ruff | SC-3 lint | ✓ | 0.15.7（`pyproject.toml` 固定） | — |
| fitz (PyMuPDF) | 既存テスト | ✓ | 1.27.2.2（`pyproject.toml` 固定） | — |

**Missing dependencies with no fallback:** なし

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_imports.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REFAC-04 | `set_current_font_size` が呼び出し後に `get_current_font_size()` で取得できる | unit | `pytest tests/test_imports.py::TestSettingsApiImports -x` | ❌ Wave 0 |
| REFAC-04 | `app.py` が `_settings_mod._current_font_size` を直接書き換えていない | 静的検証 | `grep -r "_settings_mod._current_font_size" pagefolio/app.py` が空 | ❌ Wave 0（手動確認） |
| TEST-03 | REFAC-01〜04 の全 import パスが例外なく import できる | import smoke | `pytest tests/test_imports.py -x` | ❌ Wave 0 |

### Sampling Rate

- **タスクコミット前:** `pytest tests/test_imports.py -x`
- **フェーズゲート:** `pytest && ruff check . && ruff format .`

### Wave 0 Gaps

- [ ] `tests/test_imports.py` — TEST-03 の import 回帰テスト（新規作成が必要）

---

## Security Domain

> `security_enforcement` の明示設定なし（= 有効として扱う）。

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | setter は単純代入のみ（D-04）; バリデーションは意図的に省略 |
| V6 Cryptography | no | — |

**このフェーズは内部 API リファクタリングのみであり、ユーザー入力・認証・通信は関与しない。**
セキュリティ上の懸念点なし。

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 3 実装後に `set_current_font_size` / `get_current_font_size` が `settings.py` に存在する前提で TEST-03 のテストコードを例示した | Code Examples | 実装前にテストを書くと `ImportError` になるが、これは意図した順序（REFAC-04 先行）で解消される |
| A2 | `llm_config.py` 行 51 の `fs = _current_font_size` は例外フォールバックとしての使用であり、getter 化しても意味論は変わらない | Architecture Patterns | `get_current_font_size()` が例外を投げる可能性があるが、getter は単純なモジュール変数参照のため例外は発生しない |

**A1 はリスクがほぼゼロ（実装順序で制御可能）、A2 も setter が単純代入のため安全。**

---

## Open Questions

1. **`LLMConfigDialog` を `pagefolio/__init__.py` に追加するか否か**
   - What we know: 現状 `__init__.py` に未掲載、`pagefolio/dialogs/__init__.py` には存在
   - What's unclear: 意図的に除外されたのか、Phase 2 のリファクタリングで追加漏れなのか
   - Recommendation: Phase 3 スコープ外として触れない。必要なら別タスクで判断。

2. **`app.py` のローカル import 文（`import pagefolio.settings as _settings_mod`）の削除タイミング**
   - What we know: 2 箇所のローカル import（行 49, 346）は setter 化後に不要になる
   - Recommendation: setter 呼び出しへの変更と同じコミットで削除する（ruff F401 を防ぐため）

---

## Sources

### Primary (HIGH confidence)

- `pagefolio/settings.py` — `_current_font_size` 変数の実在確認（行 107）
- `pagefolio/app.py` — write 側 2 箇所の実在確認（行 51, 348）
- `pagefolio/dialogs/merge.py` — read 側 3 箇所の実在確認（行 14, 33, 213）
- `pagefolio/dialogs/llm_config.py` — read 側 2 箇所の実在確認（行 12, 51）
- `pagefolio/__init__.py` — 公開サーフェス全体の実測
- `pagefolio/dialogs/__init__.py` — dialogs 再エクスポート表面の実測
- `pagefolio/constants.py`, `pagefolio/lang.py`, `pagefolio/themes.py` — 分割後モジュールの実在確認
- `python -c "import pagefolio.dialogs.* ..."` 実行 — ヘッドレス import 安全性の実測確認
- `python -c "import pagefolio; print(dir(pagefolio))"` 実行 — 公開サーフェス一覧の実測

### Secondary (MEDIUM confidence)

- `.planning/phases/03-api/03-CONTEXT.md` — ユーザー決定の参照元

### Tertiary (LOW confidence)

なし

---

## Metadata

**Confidence breakdown:**
- REFAC-04 変更箇所の特定: HIGH — コードベース実測、行番号確認済み
- TEST-03 検証対象パス: HIGH — `__init__.py` 実測 + `dir()` 実行で確認済み
- Tk ヘッドレス import 安全性: HIGH — 実行確認済み
- getter/setter の実装パターン: HIGH — Python 標準言語仕様に基づく

**Research date:** 2026-06-03
**Valid until:** フェーズ完了まで（変更対象ファイルが少なく安定）
