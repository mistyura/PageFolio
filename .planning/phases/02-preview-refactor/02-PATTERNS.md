# Phase 2: プレビュー最適化とリファクタリング - Pattern Map

**Mapped:** 2026-06-03
**Files analyzed:** 12（新規10 / 修正2）
**Analogs found:** 12 / 12

このフェーズはすべて「既存コードベース内に強い参照モデルが存在する」リファクタ/最適化タスクである。
新規外部ライブラリ導入はなく、参照すべきパターンはすべてリポジトリ内に存在する。

## File Classification

| 新規/修正ファイル | 種別 | Role | Data Flow | 最寄りの Analog | Match Quality |
|-------------------|------|------|-----------|-----------------|---------------|
| `pagefolio/viewer.py` (`_show_preview` 修正) | 修正 | viewer-mixin | file-I/O (render) | `pagefolio/viewer.py` `_get_thumb_photo` (155–164) | exact（同一ファイル内・同一変換） |
| `pagefolio/viewer.py` (`_render_preview_pixmap` 純関数抽出) | 新規メソッド | utility (pure) | transform | `pagefolio/viewer.py` `_get_thumb_photo` (155–164) | exact |
| `pagefolio/dialogs/__init__.py` | 新規 | package-init (re-export) | — | `pagefolio/__init__.py` (1–43) | exact |
| `pagefolio/dialogs/about.py` | 新規 | dialog | request-response | `pagefolio/dialogs.py` `AboutDialog` (24–92) | exact（同コード移設） |
| `pagefolio/dialogs/settings.py` | 新規 | dialog | request-response | `pagefolio/dialogs.py` `SettingsDialog` (98–263) | exact |
| `pagefolio/dialogs/llm_config.py` | 新規 | dialog | request-response | `pagefolio/dialogs.py` `LLMConfigDialog` (264–670) | exact |
| `pagefolio/dialogs/plugin.py` | 新規 | dialog | request-response | `pagefolio/dialogs.py` `PluginDialog` (671–866) | exact |
| `pagefolio/dialogs/merge.py` | 新規 | dialog | request-response | `pagefolio/dialogs.py` `MergeOrderDialog`(867)+`MergeResizeDialog`(1045) | exact |
| `pagefolio/themes.py` | 新規 | config (theme) | — | `pagefolio/constants.py` (8–44) | exact |
| `pagefolio/lang.py` | 新規 | config (i18n) | — | `pagefolio/constants.py` (59–) | exact |
| `pagefolio/constants.py` (再エクスポート化) | 修正 | config (re-export) | — | `pagefolio/__init__.py` (1–43) | exact |
| `tests/test_viewer.py` | 新規 | test | transform | `tests/test_pdf_ops.py` (1–60) | role-match |

## Pattern Assignments

### `pagefolio/viewer.py` — `_render_preview_pixmap` 純関数抽出 + `_show_preview` 同期化（BUG-03 / TEST-02）

**Analog:** `pagefolio/viewer.py` `_get_thumb_photo`（155–164）

このメソッドは既に **メインスレッドで `page.get_pixmap()` を同期呼び出し**し、`tobytes()` を一切使わない。
プレビュー側が踏むべき正解パターンが同一ファイル内に既に存在する。これをプレビュー用に拡張するのが BUG-03 の本質。

**同期 pixmap 生成パターン（コピー元・155–164）:**
```python
def _get_thumb_photo(self, i):
    if i in self.thumb_cache:
        return self.thumb_cache[i]
    page = self.doc[i]
    mat = fitz.Matrix(0.22, 0.22)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    photo = ImageTk.PhotoImage(img)
    self.thumb_cache[i] = photo
    return photo
```

**抽出すべき純関数ヘルパー（Tk 非依存・テスト対象）** — D-08 の `_render_preview_pixmap(page_idx, zoom)`。
現 `worker()`（83–97）の中核ロジックから `fitz.open(stream=doc_bytes)` の再オープンを除去し、
`self.doc[page_idx]` を直接使う形へ縮約する。戻り値は `(samples, w, h)`（型は executor 裁量・D-08）:
```python
def _render_preview_pixmap(self, page_idx, zoom):
    page = self.doc[page_idx]
    mat = fitz.Matrix(zoom * 1.5, zoom * 1.5)   # 既存スケール則（CLAUDE.md 準拠）を維持
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return bytes(pix.samples), pix.width, pix.height
```
**注意:** `zoom * 1.5` のスケールは CLAUDE.md「プレビューは `self.zoom * 1.5`」の規約。サムネイルの `0.22` と混同しないこと。

**撤廃対象（現 41–127 のうち）:**
- 69 行 `doc_bytes = self.doc.tobytes()` → 削除（SC-1 / TEST-02 の核心）
- 83–97 `worker()` のスレッド + `fitz.open(stream=...)` 再オープン → 同期呼び出しに置換
- 71–81 の `"..."` ローディングプレースホルダー → 同期化後は不要（D-03、撤去可否は executor 裁量）
- 65–66 `self._preview_gen += 1` / `gen` → 同期化後は stale 破棄不要（D-03、撤去時はサムネイル側 `_thumb_gen` への波及がないことを確認）

**維持すべき後処理（_apply 99–125 から）:** 矩形影描画・`create_image`・`scrollregion` 設定（125）は同期版でもそのまま残す（code_context 記載）。

**例外処理パターン（同期版で担保すべき・CLAUDE.md 禁止事項準拠）:**
```python
except Exception as e:
    logger.debug("プレビュー描画例外: %s", e)
```
裸 `except:` 禁止・必ず `logger` 呼び出しを伴うこと（現 94–95 と同形）。

---

### `pagefolio/dialogs/__init__.py` — 後方互換再エクスポート（REFAC-01 / D-07）

**Analog:** `pagefolio/__init__.py`（1–43）

`pagefolio/__init__.py` が `from pagefolio.dialogs import (...)` を行っているため、サブパッケージ化後も
**この import 表面を壊さない**ことが必須（D-07）。`__init__.py` の再エクスポート構造をそのまま踏襲する。

**再エクスポートパターン（コピー元・`__init__.py` 12–18 の形）:**
```python
# pagefolio/dialogs/__init__.py
from pagefolio.dialogs.about import AboutDialog  # noqa: F401
from pagefolio.dialogs.settings import SettingsDialog  # noqa: F401
from pagefolio.dialogs.llm_config import LLMConfigDialog  # noqa: F401
from pagefolio.dialogs.plugin import PluginDialog  # noqa: F401
from pagefolio.dialogs.merge import MergeOrderDialog, MergeResizeDialog  # noqa: F401
```
- `# noqa: F401`（未使用 import 抑止）を各行に付与する点まで `__init__.py` と統一する。
- `pagefolio/__init__.py` の 12–18 が `AboutDialog / MergeOrderDialog / MergeResizeDialog / PluginDialog / SettingsDialog` を要求 → 最低この 5 つは必ず再エクスポート。`LLMConfigDialog` も移設先で公開すること。

---

### `pagefolio/dialogs/{about,settings,llm_config,plugin,merge}.py` — クラス移設（REFAC-01 / D-06）

**Analog:** `pagefolio/dialogs.py` 各クラス（位置は下表）。**コードは原則そのまま移設**（ロジック変更なし）。

| 新ファイル | 移設クラス | 元の行 |
|-----------|-----------|--------|
| `about.py` | `AboutDialog` | 24–97 |
| `settings.py` | `SettingsDialog` | 98–263 |
| `llm_config.py` | `LLMConfigDialog` | 264–670 |
| `plugin.py` | `PluginDialog` | 671–866 |
| `merge.py` | `MergeOrderDialog` + `MergeResizeDialog`（同居） | 867–1191 |

**各ファイル冒頭の import パターン（元 dialogs.py 1–18 から、各ファイルが実際に使う分だけ抜粋）:**
```python
import logging
import tkinter as tk
from tkinter import messagebox, ttk

from pagefolio.constants import APP_VERSION, LANG, PLUGINS_DIR, C
from pagefolio.ocr import MAX_OCR_MAX_TOKENS, fetch_lm_studio_models
from pagefolio.plugins import _get_plugins_dir
from pagefolio.settings import _current_font_size

logger = logging.getLogger(__name__)
```
**注意（分割時のシンボル割り当て）:**
- `about.py`: `APP_VERSION, LANG, C` のみ使用。`messagebox`/`fitz` 不要。
- `llm_config.py`: `MAX_OCR_MAX_TOKENS, fetch_lm_studio_models`（ocr 依存）はここに集約。
- `plugin.py`: `PLUGINS_DIR`, `_get_plugins_dir` を使用。
- `merge.py`: `fitz`（元 11 行）を使用（リサイズ計算）。
- 各ファイルは自分が使う import のみ持つこと（不要 import は Ruff F401 で落ちる）。

**ダイアログ共通の確立パターン（CLAUDE.md / AboutDialog 25–40 準拠、全 dialog ファイルに適用）:**
```python
def __init__(self, parent, font_func, lang="ja"):
    super().__init__(parent)
    self._L = LANG[lang]
    self.configure(bg=C["BG_DARK"])
    self.grab_set()                       # モーダル化
    self._font = font_func
    self._build()
    self.update_idletasks()
    px = parent.winfo_rootx() + parent.winfo_width() // 2
    py = parent.winfo_rooty() + parent.winfo_height() // 2
    self.geometry(f"...+{px - w // 2}+{py - h // 2}")   # 親基準センタリング
```

---

### `pagefolio/themes.py` — THEMES / 可変 C（REFAC-02 / D-04）

**Analog:** `pagefolio/constants.py`（8–44）。`THEMES` 辞書と `C = dict(THEMES["dark"])` を**そのまま移設**。

**最重要制約（D-04・anti-pattern 回避）:** `C` は `settings.py:95` の `C.update(THEMES[resolved])` で **in-place 更新**される。
分割後も `C` の識別子（同一オブジェクト）を保持しなければならない。`C.clear()`/`C.update()` ベースを壊さないこと。
```python
# pagefolio/themes.py（移設元: constants.py 8–44）
THEMES = { "dark": {...}, "light": {...} }
C = dict(THEMES["dark"])   # 実行時に _apply_theme() が C.update() で更新（識別子保持）
```

---

### `pagefolio/lang.py` — LANG 辞書（REFAC-02 / D-06）

**Analog:** `pagefolio/constants.py`（59–711）。`LANG` 辞書（約650行）を**そのまま移設**。依存なし（純データ）。

---

### `pagefolio/constants.py` — 再エクスポート化（REFAC-02 / D-04 / D-07）

**Analog:** `pagefolio/__init__.py`（1–43）の再エクスポート方式。

分割後も `from pagefolio.constants import APP_VERSION, LANG, THEMES, C`（`__init__.py:9` / `settings.py:10` / `dialogs` 各所）を
**そのまま動かす**ため、`constants.py` に残す定数 + 再エクスポートを置く:
```python
# pagefolio/constants.py（分割後）
from pagefolio.themes import THEMES, C  # noqa: F401   # 再エクスポート（識別子保持）
from pagefolio.lang import LANG          # noqa: F401   # 再エクスポート

APP_VERSION = "v1.2.6"
SETTINGS_FILE = "pagefolio_settings.json"
PLUGINS_DIR = "plugins"
SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"})
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"})
```
**循環 import 注意:** `themes.py` / `lang.py` は `constants.py` を import してはならない（純データ・葉モジュール）。依存方向は `constants → {themes, lang}` の一方向。

---

### `tests/test_viewer.py` — 純関数回帰テスト（TEST-02 / D-08 / D-09）

**Analog:** `tests/test_pdf_ops.py`（1–60）+ `tests/conftest.py` の `sample_pdf_doc` フィクスチャ。

`test_pdf_ops.py` の方針（Tkinter を避け fitz ロジックを直接検証）に整合。`conftest.py:43` の `sample_pdf_doc`（3ページ fitz.Document）を再利用する。

**テスト構造パターン（test_pdf_ops.py のクラス構成・命名 `Test<Feature>` 準拠）:**
```python
import fitz
import pytest

class TestPreviewRender:
    def test_render_does_not_call_tobytes(self, sample_pdf_doc, monkeypatch):
        """_render_preview_pixmap / _show_preview 経路が doc.tobytes() を呼ばない（SC-1）"""
        called = {"n": 0}
        orig = fitz.Document.tobytes
        def spy(self, *a, **k):
            called["n"] += 1
            return orig(self, *a, **k)
        monkeypatch.setattr(fitz.Document, "tobytes", spy)
        # 純関数ヘルパーを直接呼ぶ（Tk root 不要）
        ...
        assert called["n"] == 0

    def test_render_returns_valid_samples(self, sample_pdf_doc):
        """get_pixmap で妥当なサイズの samples が得られる（D-09）"""
        ...
```
**D-09 の検証 2 点:** (1) `monkeypatch.setattr(fitz.Document, "tobytes", spy)` で呼び出し回数 0 を確認、(2) 戻り samples 長 == `w * h * 3`（RGB）等で妥当性確認。
**テスト容易性の前提:** 純関数ヘルパーは `self.doc` と `page_idx, zoom` のみに依存し Tk Canvas を触らないこと（D-08）。テストでは軽量スタブ（`doc` 属性だけ持つオブジェクト）にバインドして呼べる形が望ましい。
**S101 免除:** `tests/**/*.py` は `assert` 許可（pyproject 設定済み）。

## Shared Patterns

### 後方互換再エクスポート（最重要・REFAC-01/02 全体）
**Source:** `pagefolio/__init__.py`（1–43）
**Apply to:** `dialogs/__init__.py`, `constants.py`
- 物理ファイルを分割しても公開 import 表面（`from pagefolio.dialogs import ...` / `from pagefolio.constants import APP_VERSION, LANG, THEMES, C`）を一切変えない。
- 各再エクスポート行に `# noqa: F401` を付ける。

### 可変 C dict の識別子保持
**Source:** `pagefolio/settings.py` `_apply_theme`（92–95）
**Apply to:** `themes.py`, `constants.py`
```python
def _apply_theme(theme_name):
    resolved = _resolve_theme(theme_name)
    C.update(THEMES[resolved])   # in-place 更新 — C を別オブジェクトに作り替え禁止
```
- `C` を再代入・再生成してはならない。`settings.py:10` の import も分割後構成へ追従（再エクスポート方式なら物理変更不要）。

### 例外処理（CLAUDE.md 禁止事項）
**Source:** `pagefolio/viewer.py`（94–95）
**Apply to:** `_show_preview` 同期版
```python
except Exception as e:
    logger.debug("...: %s", e)
```
- 裸 `except:` 禁止。必ず `except Exception as e:` + `logger` 呼び出し。

### テーマ色・フォント参照規約
**Apply to:** 移設後の全 dialog ファイル
- 色は `C["KEY"]` で参照（ハードコード hex 禁止）。フォントは `font_func`（`self._font` 相当）経由。移設時にこの参照を壊さない。

## No Analog Found

なし。本フェーズの全ファイルにリポジトリ内の強い参照モデルが存在する。

## Metadata

**Analog search scope:** `pagefolio/`（viewer/dialogs/constants/settings/__init__）, `tests/`
**Files scanned:** viewer.py, __init__.py, settings.py, dialogs.py, constants.py, test_pdf_ops.py, conftest.py
**Pattern extraction date:** 2026-06-03
