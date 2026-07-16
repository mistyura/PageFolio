# Phase 6 Plan 02: スクロール/フォント UI 一貫性監査記録

**監査日:** 2026-07-16
**対象要件:** V180-QA-03（スクロールパターン統一・フォントスケーリング監査）
**方針:** D-10（統一基準）・D-11（個別是正のみ・共通ヘルパー新設なし）・D-12（フォントは数値ハードコードのみ是正）・D-13（フォントのみ回帰テスト化・スクロールは監査記録のみ）

---

## 1. スクロール監査

### 1.1 統一基準（正）

`pagefolio/dialogs/llm_config/dialog.py`（`DialogMixin`）の v1.7.2 実装を統一基準とする。

- `_build_scrollable_area()`（101-156行目）: `Canvas` + `ttk.Scrollbar` + `<Configure>` による `scrollregion` 自動更新
- `Enter`/`Leave` イベントによる `bind_all`/`unbind_all` の**動的**マウスホイール束縛（`<MouseWheel>`/`<Button-4>`/`<Button-5>`）。複数 Canvas が同一ウィンドウに共存する場合でも、マウスがその Canvas 上にある間だけホイールイベントを横取りし、離れたら解除するため意図しない横取りが起きない
- `_compute_dialog_height()`（159-172行目）: `winfo_screenheight()` による高さクランプ（`max_h = max(320, screen_h - 100)`）+ 下部ボタン行（Apply/Cancel）はスクロール領域外に固定配置

### 1.2 監査対象8ファイルの判定表

| # | ファイル | スクロール実装 | ホイール束縛方式 | 高さクランプ | 判定 | 対応 |
|---|---------|---------------|-----------------|-------------|------|------|
| 1 | `pagefolio/dialogs/batch_ocr.py` | `tk.Listbox` + `ttk.Scrollbar`（Canvas不使用） | Listbox 標準機能（Windows既定でホイール動作） | `parent.winfo_height() - 40` でクランプ済み | 一致（Canvas非使用のため基準対象外） | 対応不要 |
| 2 | `pagefolio/dialogs/llm_config/dialog.py` | Canvas + Scrollbar（基準実装そのもの） | 動的 Enter/Leave bind_all/unbind_all | `winfo_screenheight()` クランプ済み | 基準 | 変更なし |
| 3 | `pagefolio/dialogs/llm_config/sections.py` | `tk.Listbox` + `ttk.Scrollbar`（フォールバック順一覧・Canvas不使用） | Listbox 標準機能 | 親ダイアログ（dialog.py）のクランプに従属 | 一致（Canvas非使用のため基準対象外） | 対応不要 |
| 4 | `pagefolio/dialogs/merge.py` | `tk.Listbox` + `ttk.Scrollbar`（Canvas不使用） | Listbox 標準機能 | `parent.winfo_height() - 40` でクランプ済み | 一致（Canvas非使用のため基準対象外） | 対応不要 |
| 5 | `pagefolio/dialogs/plugin.py` | Canvas + Scrollbar | **是正前: ホイール束縛なし** → 是正後: 動的 Enter/Leave bind_all/unbind_all | 高さクランプなし（`h = max(400, int(fs*30))` のみ・screenheight クランプ無し） | **不一致（ホイール）** → 是正済み | **是正**（本プラン Task 2） |
| 6 | `pagefolio/ocr_dialog.py` | Canvas + Scrollbar（`side_canvas`・右ペイン） | 静的 `bind()` の子ウィジェット再帰付与（`_bind_side_wheel_recursive`） | **是正前: クランプなし** → 是正後: `winfo_screenheight()` クランプ追加（`_center()`） | **不一致（高さクランプ）** → 是正済み。ホイール束縛方式（静的再帰）は不一致だが受容差分 | **高さクランプのみ是正**（本プラン Task 2）。ホイール方式は受容差分（1.3節） |
| 7 | `pagefolio/ui_builder.py` | Canvas + Scrollbar（`_build_tools_scrollable`・右ツールパネル / `thumb_canvas`・サムネイル一覧 / `preview_canvas`・プレビュー） | 静的 `bind()`（`_build_tools_scrollable` は子ウィジェット再帰付与・`thumb_canvas`/`preview_canvas` は Canvas 自体への単発 bind） | クランプ対象外（メインウィンドウ本体・ダイアログではない） | 不一致（ホイール方式） | 受容差分（1.3節） |
| 8 | `pagefolio/viewer.py` | Canvas + Scrollbar（ページ拡大ポップアップ） | 静的 `bind()`（Canvas 自体への単発 bind・子ウィジェットなし） | クランプ対象外（ポップアップ・固定サイズ） | 不一致（形式上）だが実質的にリスクなし | 受容差分（1.3節） |

### 1.3 是正箇所と受容差分の根拠

**是正した箇所（本プラン Task 2）:**

1. **`plugin.py`**: プラグイン一覧 Canvas にマウスホイールバインドが一切無く、スクロールバーのドラッグ以外にスクロール手段が無かった（Pitfall 3）。llm_config 基準の動的 Enter/Leave 方式で是正。ダイアログ破棄時の `unbind_all` 漏れを防ぐため `self.bind("<Destroy>", ...)` も追加し、複数 Canvas 共存時の横取りリスクを構造的に排除した。
2. **`ocr_dialog.py`**: `_center()` の高さ算出（`h = max(680, int(fs * 56))`）が画面高でクランプされておらず、低解像度・大フォント環境で下端が画面外に出る可能性があった（Pitfall 4）。llm_config の `_compute_dialog_height()` と同型の `winfo_screenheight()` クランプを追加した。

**受容差分として据え置いた箇所（D-11: 個別是正のみ・回帰面を狭く保つ）:**

1. **`ui_builder.py`（`_build_tools_scrollable`/`thumb_canvas`/`preview_canvas`）**: 静的 `bind()` の再帰付与方式（または Canvas 単発 bind）は llm_config の動的 Enter/Leave 方式と異なるが、**現状問題なく機能している**（メインウィンドウの右ツールパネル・サムネイル一覧・プレビューはそれぞれ単一の主要スクロール領域であり、複数 Canvas が同一操作範囲で競合する実害が報告されていない）。メインウィンドウ本体の中核レイアウトを再設計するリスクは是正便益を上回るため、D-11 に従い据え置く。
2. **`ocr_dialog.py`（`side_canvas`・右ペインのホイール束縛方式）**: 高さクランプは是正したが、ホイール束縛自体は静的再帰方式のまま据え置いた。OCR ダイアログ内に競合する複数スクロール Canvas は存在せず（右ペイン `side_canvas` のみ）、動的方式へ書き換える回帰リスクが是正便益を上回るため、高さクランプのみに是正範囲を限定した（Pitfall 4 の指摘は高さクランプ欠如のみであり、ホイール方式は Pitfall 3 の対象＝`plugin.py`とは別問題）。
3. **`viewer.py`（ページ拡大ポップアップの Canvas）**: 単一 Canvas への単発 `bind()` のみで、子ウィジェットへの再帰も競合するスクロール領域も存在しない。動的 Enter/Leave 方式へ変更する実益が無いため据え置く。
4. **`batch_ocr.py`/`llm_config/sections.py`/`merge.py`（`tk.Listbox`）**: これらは Canvas ベースのスクロール実装ではなく `tk.Listbox` のネイティブスクロール機構を使用している。`tk.Listbox` は Windows 環境でマウスホイールを標準サポートしており、llm_config 基準（Canvas + 動的束縛）の対象範囲外（ウィジェット種別が異なる）。高さは各ダイアログの `__init__` 内で `parent.winfo_height()` を基準にクランプ済みであり、追加是正は不要と判定した。

### 1.4 D-13: スクロールパターンの再発防止について

スクロールパターンの一致/不一致は「Canvas 生成成功」等の表層的な自動テストでは検出できず（実際にホイールイベントが正しい Canvas へ配送されるかは Tk のイベントループ・ウィジェット階層に依存し、pytest の Tk 非依存/最小生成スタブでは再現性が低い）、構造的にテスト化困難と判断した（CONTEXT.md D-13）。本監査記録が確認範囲・判定根拠・是正内容の唯一の証跡となる。

---

## 2. フォント監査

### 2.1 検出結果

- **是正前:** `pagefolio/dialogs/about.py:42` の `font=("Segoe UI", 16, "bold")` の1箇所のみ（`_FONT_HARDCODE_PATTERN` による `pagefolio/` 全件スキャンで確認）。
- **是正後:** `self._font(4, "bold")` へ変更（本プラン Task 1）。`tests/test_font_hardcode_guard.py::test_no_hardcoded_font_sizes` によりゼロ件を確認済み。

### 2.2 delta 値の確定根拠

`pagefolio/settings.py._load_settings()` の既定値 `"font_size": 12` を実測確認した上で、`delta=4` を採用した（RESEARCH.md Assumption A1 が想定していた base=10 は実際の既定値と異なっていたため、実測値ベースで再確定）。

- 既定値（font_size=12）: `12 + 4 = 16pt` — 是正前の見た目を完全再現
- 最小値（font_size=8）: `8 + 4 = 12pt`
- 最大値（font_size=16）: `16 + 4 = 20pt`

`tkinter.font.Font` による実測（`family="Segoe UI", size=20, weight="bold"`）で "PageFolio" の描画幅は **128px**。About ダイアログの幅は固定 `w=360`（`about.py:30`）であり、左右余白を差し引いても十分収まる（レビューR3の懸念を実測で解消）。

### 2.3 除外対象（D-12）

以下は数値ハードコードではなく変数連動のため、`_FONT_HARDCODE_PATTERN`（`\d+` で数値リテラルのみ検出）に一致せず、是正対象外・allowlist も不要と確認した。

- `pagefolio/ui_builder.py` の `font=("Segoe UI", fs±n)` 系（`fs` 変数連動済み）
- `pagefolio/dialogs/settings.py:148` の `font=("Segoe UI", self.font_var.get())`（フォントプレビュー用の意図的な動的値）
- `pagefolio/dialogs/settings.py:205` の `font=("Segoe UI", size)`（同上・`configure()` 経由の動的更新）

### 2.4 再発防止（D-13）

`tests/test_font_hardcode_guard.py` を新規作成（`tests/test_source_keyguard.py` の grep 型ソーススキャン構造を踏襲）。

- `test_no_hardcoded_font_sizes`: `pagefolio/` 配下全 `.py` を走査し数値リテラルのフォントタプルが存在しないことを担保
- `test_pattern_matches_only_literals`（レビューR4反映）: 正規表現が数値リテラル（`16`）にのみマッチし、変数指定（`self.font_size`/`fs`/`size`）には反応しないことを正負両方向で検証

---

## 3. まとめ

| 項目 | 結果 |
|------|------|
| スクロール是正 | `plugin.py`（ホイール束縛追加）・`ocr_dialog.py`（高さクランプ追加）の2箇所 |
| スクロール受容差分 | `ui_builder.py`（3箇所）・`ocr_dialog.py`（side_canvas ホイール方式）・`viewer.py`（ポップアップ）・Listbox系3ファイル（対象外） |
| 共通ヘルパー新設 | なし（`make_scrollable_frame()` 等は不採用・D-11） |
| フォント是正 | `about.py:42` の1箇所（数値リテラル→`self._font(4, "bold")`） |
| フォント除外対象 | `ui_builder.py`（fs連動）・`settings.py`（プレビュー変数連動）の計3箇所 |
| 回帰テスト新設 | `tests/test_font_hardcode_guard.py`（フォントのみ・D-13） |

V180-QA-03 の受入基準（must_haves.truths 5項目）を本監査記録・本プランのコミット・テストで満たしたことを確認した。

---
*Phase: 06-ux-ui / Plan: 02*
*作成日: 2026-07-16*
