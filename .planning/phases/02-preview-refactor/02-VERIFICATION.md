---
phase: 02-preview-refactor
verified: 2026-06-03T07:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 02: プレビュー最適化とリファクタリング 検証レポート

**フェーズゴール:** ページ切り替えのシリアライズが廃止され、主要モジュールの行数が管理可能な水準になる
**検証日時:** 2026-06-03
**ステータス:** passed
**再検証:** No — 初回検証

---

## ゴール達成確認

### 観測可能な真実

| # | 真実 | ステータス | 根拠 |
|---|------|-----------|------|
| 1 | ページ切り替え時に `doc.tobytes()` が呼ばれない（`page.get_pixmap()` 直接呼び出しに変更済み） | ✓ VERIFIED | `grep -c "self.doc.tobytes()" pagefolio/viewer.py` → 0。`_show_preview` は `_render_preview_pixmap` を同期呼び出しし、`page.get_pixmap()` のみを使用。`threading` import も削除済み。 |
| 2 | `pagefolio/dialogs/` サブパッケージが存在し、既存の `from pagefolio.dialogs import ...` import が動作する | ✓ VERIFIED | `from pagefolio.dialogs import AboutDialog, SettingsDialog, PluginDialog, MergeOrderDialog, MergeResizeDialog, LLMConfigDialog` exit 0。`d.__file__` が `dialogs/__init__.py` を指す。旧 `dialogs.py` は削除済み。 |
| 3 | `constants.py` が `lang.py` / `themes.py` に分割され、既存の `C["BG_DARK"]` 等の参照が動作する | ✓ VERIFIED | `from pagefolio.constants import APP_VERSION, LANG, THEMES, C` exit 0。`C["BG_DARK"]` → `"#1a1a2e"` 確認。`_apply_theme` 前後で `id(C)` が一致（in-place 更新保持）。`themes.py`/`lang.py` は葉モジュール（`constants` を import しない）。 |
| 4 | `pytest` が全通し、BUG-03 の回帰テスト（TEST-02）が含まれる | ✓ VERIFIED | `python -m pytest -q` → 165 passed。`tests/test_viewer.py::TestPreviewRender::test_render_does_not_call_tobytes` および `test_render_returns_valid_samples` の 2 テストが pass。 |

**スコア:** 4/4 真実が VERIFIED

---

## 必須アーティファクト確認

| アーティファクト | 期待内容 | ステータス | 詳細 |
|----------------|---------|-----------|------|
| `pagefolio/viewer.py` | 純関数 `_render_preview_pixmap` + 同期化された `_show_preview` | ✓ VERIFIED | 存在・実装あり。定義（40行）と `_show_preview` 内呼び出し（78行）の 2 箇所確認。 |
| `tests/test_viewer.py` | BUG-03 回帰テスト（tobytes スパイ + samples 妥当性） | ✓ VERIFIED | 存在。`class TestPreviewRender` あり。2 テストとも pass。Tkinter 依存なし（純関数テスト）。 |
| `pagefolio/themes.py` | `THEMES` 辞書 + 可変 `C = dict(THEMES["dark"])` | ✓ VERIFIED | 存在。`THEMES = {` が 8 行目。`C = dict(THEMES["dark"])` が 1 箇所のみ。`constants.py` を import しない葉モジュール。 |
| `pagefolio/lang.py` | `LANG` 辞書（純データ・依存なし） | ✓ VERIFIED | 存在。`LANG = {` 確認。`constants.py` を import しない葉モジュール。 |
| `pagefolio/constants.py` | `APP_VERSION`/拡張子定数 + themes/lang 再エクスポート（711 行 → 23 行） | ✓ VERIFIED | 存在。23 行に大幅削減。`from pagefolio.themes import THEMES, C  # noqa: F401` と `from pagefolio.lang import LANG  # noqa: F401` で再エクスポート。`THEMES = {` の定義ブロックなし。 |
| `pagefolio/dialogs/__init__.py` | 後方互換の再エクスポート集約 | ✓ VERIFIED | 存在。`from pagefolio.dialogs.about import AboutDialog  # noqa: F401` 等 5 行の再エクスポート確認。 |
| `pagefolio/dialogs/about.py` | `AboutDialog` | ✓ VERIFIED | `class AboutDialog` 存在。`messagebox` import なし（PATTERNS 指針準拠）。 |
| `pagefolio/dialogs/merge.py` | `MergeOrderDialog` + `MergeResizeDialog` | ✓ VERIFIED | 両クラス存在（22行・200行）。`import fitz` あり（リサイズ計算用）。 |
| `pagefolio/dialogs/settings.py` | `SettingsDialog` | ✓ VERIFIED | `class SettingsDialog` 存在。 |
| `pagefolio/dialogs/llm_config.py` | `LLMConfigDialog` | ✓ VERIFIED | `class LLMConfigDialog` 存在。 |
| `pagefolio/dialogs/plugin.py` | `PluginDialog` | ✓ VERIFIED | `class PluginDialog` 存在。 |

---

## キーリンク検証

| From | To | Via | ステータス | 詳細 |
|------|----|-----|-----------|------|
| `viewer.py::_show_preview` | `viewer.py::_render_preview_pixmap` | 同期直接呼び出し | ✓ WIRED | `_show_preview` 78 行で `samples, w, h = self._render_preview_pixmap(page_idx, zoom)` |
| `tests/test_viewer.py` | `viewer.py::_render_preview_pixmap` | `SimpleNamespace` スタブバインド | ✓ WIRED | `ViewerMixin._render_preview_pixmap.__get__(stub)` でバインドして直接呼び出し |
| `pagefolio/constants.py` | `pagefolio/themes.py` | 再エクスポート import | ✓ WIRED | `from pagefolio.themes import THEMES, C  # noqa: F401` |
| `pagefolio/constants.py` | `pagefolio/lang.py` | 再エクスポート import | ✓ WIRED | `from pagefolio.lang import LANG  # noqa: F401` |
| `pagefolio/settings.py::_apply_theme` | `pagefolio/themes.py::C` | `C.update()` in-place 更新 | ✓ WIRED | `_apply_theme` 前後で `id(C)` が同一（2516583963072）。識別子保持確認。 |
| `pagefolio/__init__.py` | `pagefolio/dialogs/__init__.py` | `from pagefolio.dialogs import (...)` | ✓ WIRED | `import pagefolio` exit 0。`from pagefolio import app, ui_builder, page_ops` exit 0。 |
| `pagefolio/dialogs/__init__.py` | `dialogs/{about,settings,llm_config,plugin,merge}.py` | 各サブモジュールからの再エクスポート | ✓ WIRED | 全 6 クラスの import が exit 0。 |

---

## データフロートレース（Level 4）

本フェーズはレンダリング経路の同期化リファクタであり、新規データソースの追加はない。`_render_preview_pixmap` は `self.doc[page_idx].get_pixmap()` で実際のピクセルデータを取得し、`Image.frombytes` → `ImageTk.PhotoImage` → `canvas.create_image` に流れる。静的/空データ返却なし。

| アーティファクト | データ変数 | ソース | 実データ生成 | ステータス |
|----------------|-----------|-------|------------|-----------|
| `viewer.py::_render_preview_pixmap` | `pix.samples` | `self.doc[page_idx].get_pixmap()` | fitz ページレンダリング（実PDF） | ✓ FLOWING |
| `viewer.py::_show_preview` | `samples, w, h` | `_render_preview_pixmap` 同期呼び出し | 上記に従属 | ✓ FLOWING |

---

## 動作スポットチェック

| 動作 | コマンド | 結果 | ステータス |
|------|---------|------|-----------|
| `viewer.py` に `tobytes` 呼び出し 0 件 | `grep -c "self.doc.tobytes()" pagefolio/viewer.py` | 0 | ✓ PASS |
| `_render_preview_pixmap` が定義・呼び出し両方存在 | `grep "_render_preview_pixmap" pagefolio/viewer.py` | 2 件（40行・78行） | ✓ PASS |
| `fitz.open(stream=...)` ワーカー再オープン撤廃 | `grep "fitz.open(stream" pagefolio/viewer.py` | 0 件 | ✓ PASS |
| `zoom * 1.5` スケール使用（0.22 ではない） | `grep "zoom \* 1.5" pagefolio/viewer.py` | 47行で確認 | ✓ PASS |
| 裸 except なし | `grep -n "except:" pagefolio/viewer.py` | 0 件 | ✓ PASS |
| dialogs サブパッケージ import | `python -c "from pagefolio.dialogs import AboutDialog, ..."` | exit 0 | ✓ PASS |
| C 識別子保持（_apply_theme 前後） | `id(C)` 比較 | 一致（2516583963072） | ✓ PASS |
| 循環 import なし | `python -c "import pagefolio"` | exit 0 | ✓ PASS |
| Ruff lint | `ruff check .` | `All checks passed!` | ✓ PASS |
| Ruff format | `ruff format --check .` | `31 files already formatted` | ✓ PASS |
| pytest 全通 | `python -m pytest -q` | `165 passed in 1.81s` | ✓ PASS |
| TEST-02 個別実行 | `python -m pytest tests/test_viewer.py -v` | `2 passed in 0.14s` | ✓ PASS |

---

## 要件カバレッジ

| 要件ID | 説明 | 対応プラン | ステータス | 根拠 |
|--------|------|-----------|-----------|------|
| BUG-03 | ページ切り替え時にプレビューのシリアライズを行わない | 02-01 | ✓ SATISFIED | `viewer.py` から `doc.tobytes()` / `threading.Thread` / `fitz.open(stream=)` を完全撤廃。`_render_preview_pixmap` による同期 `get_pixmap()` 呼び出しに置換。 |
| REFAC-01 | `dialogs.py` を `pagefolio/dialogs/` サブパッケージに分割 | 02-03 | ✓ SATISFIED | 6 クラスが 5 ファイルに分割。旧 `dialogs.py` 削除。`__init__.py` 再エクスポートで後方互換維持。 |
| REFAC-02 | `constants.py` を `lang.py` / `themes.py` に分割 | 02-02 | ✓ SATISFIED | `themes.py`（THEMES/C）・`lang.py`（LANG）を新設。`constants.py` は 711 行 → 23 行に削減（再エクスポート構成）。後方互換維持。 |
| TEST-02 | BUG-03（プレビュー生成）の回帰テスト | 02-01 | ✓ SATISFIED | `tests/test_viewer.py::TestPreviewRender` に 2 テスト実装。`tobytes` スパイ（呼び出し 0 を assert）と `samples` 妥当性（`len(samples) == w * h * 3` を assert）。pytest pass 確認。 |

---

## アンチパターン検査

| ファイル | 検査内容 | 結果 |
|---------|---------|------|
| `pagefolio/viewer.py` | `TBD/FIXME/XXX/TODO` マーカー | なし |
| `pagefolio/viewer.py` | `# type: ignore` | なし |
| `pagefolio/viewer.py` | 裸 `except:` | なし（`except Exception as e:` + `logger.debug` 使用） |
| `tests/test_viewer.py` | Tkinter 依存 | なし（純関数テスト） |
| `pagefolio/dialogs/` | 裸 `except:` | なし（全ファイル） |
| `pagefolio/dialogs/` | `# type: ignore` | なし |
| `pagefolio/dialogs/__init__.py` 以外の実装ファイル | `# noqa: F401` | なし（実使用 import のみ・PLAN 規約準拠） |
| `pagefolio/constants.py` | `THEMES = {` 定義ブロック残存 | なし（themes.py に移設済み） |
| `pagefolio/themes.py` / `pagefolio/lang.py` | `from pagefolio.constants` 循環 import | なし（葉モジュール確認済み） |

---

## 注記事項

### `_preview_gen` の取り扱い

`viewer.py` からは `_preview_gen` を完全撤去（同期化により stale 結果問題が消滅）。
ただし `app.py`・`file_ops.py`・`page_ops.py` には `_preview_gen += 1` のインクリメント行が残存している。
これはプラン D-03 の「波及確認後に撤去、ただし viewer.py への影響のみ対象」という裁量指針に従った結果であり、残存する `_preview_gen` インクリメントは `_show_preview` の同期呼び出しに影響しない（ガード条件が viewer.py から撤去されているため）。機能上の問題はなく、将来フェーズでのクリーンアップ対象として記録する。

### SUMMARY 02-02・02-03 のコミット保留について

SUMMARY に「git コマンドがセッション中にブロックされた」旨の記載があるが、実際のコードファイル（`themes.py`、`lang.py`、`constants.py`、`dialogs/` サブパッケージ）は正しく適用されており、`pytest 165 passed`・`ruff check All checks passed` で機能的正確性を確認済み。コミット保留はオーケストレーター側の課題。

---

## ギャップサマリー

**ギャップなし。** 4 つの Success Criteria（SC-1〜SC-4）がすべてコードベースの実証で VERIFIED。

---

_検証日時: 2026-06-03T07:00:00Z_
_検証者: Claude (gsd-verifier)_
