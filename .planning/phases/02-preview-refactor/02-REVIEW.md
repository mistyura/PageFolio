---
phase: 02-preview-refactor
reviewed: 2026-06-03T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - pagefolio/viewer.py
  - pagefolio/constants.py
  - pagefolio/themes.py
  - pagefolio/lang.py
  - pagefolio/dialogs/__init__.py
  - pagefolio/dialogs/about.py
  - pagefolio/dialogs/settings.py
  - pagefolio/dialogs/llm_config.py
  - pagefolio/dialogs/plugin.py
  - pagefolio/dialogs/merge.py
  - tests/test_viewer.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 2: コードレビュー報告書

**レビュー日時:** 2026-06-03
**深度:** standard
**レビュー対象ファイル数:** 11
**ステータス:** issues_found

## サマリー

Phase 02 の 3 つの変更（BUG-03 プレビュー同期化 / REFAC-02 constants 分割 / REFAC-01 dialogs サブパッケージ化）をレビューした。

リファクタ 2 件（REFAC-01 / REFAC-02）は極めて健全である。実機検証の結果:

- `themes.py` の `THEMES` / `C`、`lang.py` の `LANG` は分割前と**バイト一致**（AST `literal_eval` 比較で確認）。`LANG` の `ja` / `en` キーは各 230 件で完全に対称、欠落・追加なし。
- 後方互換 import 表面（`from pagefolio.constants import APP_VERSION, LANG, THEMES, C, SETTINGS_FILE, PLUGINS_DIR, SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS` / `from pagefolio.dialogs import ...` 6 クラス）は全解決。`C is themes.C` / `LANG is lang.LANG` の同一識別子も維持され、`settings.py` の `C.update(THEMES[resolved])` in-place 更新が壊れないことを確認。
- `tests/test_viewer.py` は 2 件パス。`sample_pdf_doc` フィクスチャは conftest に存在し、`bytes(pix.samples)` 戻り値検証も妥当。

主要な懸念は BUG-03（プレビュー同期化）に集中する。旧コードはワーカースレッド＋`fitz.open(stream=doc.tobytes())` で描画していたが、新コードは UI スレッド上で `get_pixmap()` を同期呼び出しする。この変更に伴い、(1) 例外捕捉スコープの縮小、(2) UI スレッドブロッキング、(3) プレースホルダ描画の喪失、という 3 点の挙動退行リスクが生じている。いずれも BLOCKER ではないが、修正を推奨する。

セキュリティ上の新規欠陥は検出されなかった（`plugin.py` の `os.startfile` / `subprocess.Popen` は分割前から存在し、固定パスのみ・`# noqa` 既存、本フェーズの変更対象外）。

## Warnings

### WR-01: `Image.frombytes` / `ImageTk.PhotoImage` が try/except の外にあり UI スレッドで未捕捉例外を起こしうる

**File:** `pagefolio/viewer.py:77-83`
**Issue:**
新しい `_show_preview` は `try/except Exception` で `_render_preview_pixmap` のみを囲んでいる（77-81 行）。しかし pixmap → PIL → Tk 変換の `Image.frombytes("RGB", [w, h], samples)`（82 行）と `ImageTk.PhotoImage(img)`（83 行）は try の**外**にある。旧実装ではこの変換はワーカー or `_apply` 内にあり、ワーカー側の `except Exception` が描画系例外も実質的に握っていた。

`alpha=False` の get_pixmap は通常 RGB（n=3）を返すため `len(samples) == w*h*3` は成立するが、CMYK/グレースケール等の特殊カラースペースや破損ページで `samples` 長が不一致になった場合、`Image.frombytes` は `ValueError` を送出する。これが UI スレッド（同期呼び出し）で未捕捉のまま伝播すると、ページ送り・ズーム操作で例外がトレースバックとして表面化し、最悪アプリが不安定化する。BUG-03 の同期化によって捕捉境界が実質的に狭まった退行である。

**Fix:**
変換・描画まで含めて try で囲み、`logger.debug` でログする（既存パターン踏襲）。

```python
        page_idx = self.current_page
        zoom = self.zoom
        try:
            samples, w, h = self._render_preview_pixmap(page_idx, zoom)
            img = Image.frombytes("RGB", [w, h], samples)
            photo = ImageTk.PhotoImage(img)
        except Exception as e:
            logger.debug("プレビュー描画例外: %s", e)
            return
        self.preview_img_ref = photo
        # 以降の create_rectangle / create_image / scrollregion 設定…
```

### WR-02: プレビューが UI スレッドで同期レンダリングされ、大きなページで操作中フリーズが発生しうる

**File:** `pagefolio/viewer.py:51-105`
**Issue:**
旧 `_show_preview` は `threading.Thread(target=worker, daemon=True)` で `get_pixmap()` をバックグラウンド実行し、`_preview_gen` 世代カウンタで stale 結果を破棄していた。新実装はこれを撤廃し UI スレッドで同期描画する。`zoom * 1.5` スケール（高ズーム時は最大 4.5 倍）で高解像度・大判ページをレンダリングすると `get_pixmap` が数百 ms〜秒オーダーかかり、その間 Tk メインループがブロックされてページ送り・ズームの連打が固まる。これは BUG-03（`doc.tobytes()` フルシリアライズ廃止）の意図的な設計判断だが、シリアライズ削減と引き換えに「描画自体の同期ブロッキング」という別種の応答性退行を導入している点に注意が必要。

純粋な性能問題は v1 スコープ外だが、本件は「操作中に UI が応答しなくなる」挙動変化であり、ユーザー体感上のリグレッションとして記録する。

**Fix:**
スコープ外として許容する場合でも、最低限ズーム上限 3.0（`_zoom` の clamp）に対する最大解像度を見積もり、`開発履歴.md` に「プレビューは同期描画になった（大判ページで一時的にブロックしうる）」旨を明記すること。応答性を維持したい場合は、世代カウンタ＋ワーカー方式を残しつつ `doc.tobytes()` だけを `self.doc[page_idx]` 直接参照に置き換える折衷案（BUG-03 の本来の狙いはフルシリアライズ廃止）を検討する。

### WR-03: ローディングプレースホルダ（"..."）の喪失でレンダリング中の視覚フィードバックが消えた

**File:** `pagefolio/viewer.py:74-104`
**Issue:**
旧実装は `worker()` 起動前に Canvas 中央へ `"..."` プレースホルダを即時描画し（旧 69-78 行相当）、レンダリング完了後に `_apply` が `delete("all")` して本画像で置換していた。新実装はこのプレースホルダ描画を削除した。WR-02 の同期ブロッキングと相まって、大判ページではプレースホルダも出ないまま UI が固まり、ユーザーには「無反応」に見える。`_show_preview` 冒頭の `delete("all")`（52 行）で前ページ画像が消え、新画像描画まで空白の Canvas が残る。

**Fix:**
WR-02 を同期方式のまま維持する場合は、`delete("all")` 直後に軽量なプレースホルダ（例: 中央に `self._t(...)` か `"..."`）を描画し `update_idletasks()` で即時反映してから `_render_preview_pixmap` を呼ぶ。あるいは旧ワーカー方式（WR-02 の折衷案）に戻せば本問題も解消する。

## Info

### IN-01: `_preview_gen` 世代カウンタが `_show_preview` から更新されなくなり、状態の一貫性が薄れた

**File:** `pagefolio/viewer.py:51`（撤廃箇所）/ `pagefolio/app.py:89,360` / `pagefolio/file_ops.py:339,400,424,516` / `pagefolio/page_ops.py:461`
**Issue:**
旧 `_show_preview` は `self._preview_gen += 1` でカウンタを進めていたが、同期化に伴い撤廃された。一方 `app.py`・`file_ops.py`・`page_ops.py` は依然 `self._preview_gen += 1` を 7 箇所で実行しており、`viewer.py` 側に消費者が居なくなった。プレビュー描画が同期化された今、これらインクリメントは事実上 no-op の残存状態である（サムネイルは別カウンタ `_thumb_gen` を使うため影響なし）。機能的なバグではないが、保守者に「まだ非同期世代管理が効いている」という誤読を与える。

**Fix:**
本フェーズのスコープ外（viewer.py 以外の編集を伴う）であれば、`開発履歴.md` に「`_preview_gen` はプレビュー同期化により実質未使用化。サムネイルの `_thumb_gen` のみ有効」と注記し、別タスクで他モジュールの `_preview_gen += 1` 撤去を検討する。

### IN-02: `_add_thumb` は未使用のデッドコード（既存・本フェーズ非変更）

**File:** `pagefolio/viewer.py:277-281`
**Issue:**
`_add_thumb(self, i)` はパッケージ全体で呼び出し箇所がない（`._add_thumb(` の grep で 0 件）。`_build_thumbnails` は `_add_thumb_placeholder` ＋遅延 `render_next` を使うため `_add_thumb` は到達不能。ただしこのメソッドは Phase 02 の diff で変更されておらず、分割前から存在する既存デッドコードである。

**Fix:**
本フェーズの責務外だが、別途クリーンアップタスクで削除を推奨。

### IN-03: 旧 `dialogs.py`（モノリス）の削除確認

**File:** `pagefolio/dialogs/__init__.py`（サブパッケージ化）
**Issue:**
REFAC-01 でサブパッケージ `pagefolio/dialogs/` を作成し、旧 `pagefolio/dialogs.py` を削除した想定。同名のモジュールとパッケージが両立すると import 解決が不定になるため、旧 `dialogs.py` が確実に削除されていることが前提（`02-03-PLAN.md` でも指摘）。実機 import 検証では `from pagefolio.dialogs import ...` 6 クラスが正常解決し、`pagefolio.dialogs` がパッケージ（`__init__.py` 経由）として読まれることを確認済み。

**Fix:**
対応不要（確認のための記録）。コミット時に旧 `pagefolio/dialogs.py` が git 上から削除されていることを最終確認すること。

---

_Reviewed: 2026-06-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
