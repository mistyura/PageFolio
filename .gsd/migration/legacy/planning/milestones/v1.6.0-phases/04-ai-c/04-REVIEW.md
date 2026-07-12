---
phase: 04-ai-c
reviewed: 2026-06-20T00:00:00Z
depth: deep
files_reviewed: 1
files_reviewed_list:
  - pagefolio/ocr_dialog.py
findings:
  critical: 0
  high: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 04 (04-ai-c): コードレビュー報告

**レビュー対象:** コミット `48193fb`（`pagefolio/ocr_dialog.py` のみ・+52/-10）
**深度:** deep（呼び出し先 `resolve_ocr_prompt` / `parse_markdown` / `_format_full_text` / タグ整合まで追跡）
**ステータス:** issues_found（ただし Critical/High 0 件）

## サマリー

3 改修（`_on_run` のプロンプト解決集約・`_build` の md タグ定義・`_render_results_ordered` の markdown 整形分岐）を、呼び出し先モジュール（`pagefolio/ocr.py` の `resolve_ocr_prompt` / `PROVIDER_OCR_PROMPTS`、`pagefolio/md_render.py` の `parse_markdown`）まで跨いで検証しました。

**主要観点はいずれも合格です。**

- **`name` 前方移動（_on_run）**: `name = self.app.settings.get("ocr_provider", "")` を line 1097 へ前方移動し、旧 line 1130 の重複取得を削除。前方移動後の `name == "claude"` / `"gemini"` / `"lmstudio"...` 再生成分岐は同一 `name` を再利用しており **NameError・経路依存の残存なし**。`resolve_ocr_prompt` は `custom_prompt` 最優先→`PROVIDER_OCR_PROMPTS`→`OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])` の順で、旧 if/else（custom 優先・既定 text）と**等価な後方互換を保持**。
- **markdown ガードの後方互換**: `markdown = self.preset_var.get() == "markdown"` を `_insert_results_body` へ伝播し、False 経路は従来の `self.text.insert("end", self.results[page_idx] + "\n")` を**完全温存**。スキップ通知経路（line 1497-1498）も末尾改行が保たれる。
- **裸 except 不使用**: 本差分に新規 `except` なし（既存はすべて型指定済み）。
- **テーマ色**: md タグ 5 個すべて `C["ACCENT"]` / `C["BG_PANEL"]` 経由。ハードコード hex なし。
- **raw 維持**: `_format_full_text`（コピー/保存）は `self.results[page_idx]` を素結合のみで、`parse_markdown` 等の整形混入なし（Pitfall 5 担保）。
- **タグ整合**: `parse_markdown` が産出する行種別（md_h1/md_h2/md_bullet/md_code）＋インライン（md_bold）の**全 5 種が `tag_configure` 済み**で、未定義タグへの `tag_add` による `TclError` は発生しない。
- **セキュリティ**: tk.Text は HTML/JS 実行コンテキストではないため LLM 出力挿入による XSS・コード実行は成立しない。`parse_markdown` の正規表現は非貪欲＋文字クラスのみで ReDoS 線形保証済み（md_render.py:14-16）。情報露出経路なし。

Critical/High 該当なし。以下は品質・保守性に関する Warning / Info です。

## Warnings

### WR-01: `md_code` タグのフォントが `self._font` を経由せずファミリ・ウェイトを固定

**File:** `pagefolio/ocr_dialog.py:511`
**Issue:** 他の md タグ（md_h1/md_h2/md_bold）は `self._font(delta, weight)` 経由でベースサイズ追従・ウェイト指定するが、`md_code` だけ `font=("Consolas", self._font_size())` とファミリを直接タプル指定している。等幅フォントが必要という意図は妥当だが、CLAUDE.md 規約「フォントは `self._font` ヘルパー経由」の例外になっており、(1) ウェイトを変えられない、(2) `self._font` が注入カスタム関数（`font_func`）に差し替えられた場合に **コードブロックだけ注入フォントを無視**して Consolas 固定になる、という一貫性のずれを生む。`_font_size()` は内部で `self._font(0)[1]` を呼ぶため、サイズは追従するが「ファミリだけ別系統」という二重管理になっている。
**Fix:** 等幅指定が必須なら、`_font` ヘルパー側に monospace バリアントを足すか、最低限コメントで「等幅必須のため意図的に `_font` を迂回」と明示し規約例外であることを残す。例:
```python
# md_code は等幅必須のため意図的に _font を迂回（サイズのみ _font_size で追従）
self.text.tag_configure("md_code", background=C["BG_PANEL"], font=("Consolas", self._font_size()))  # noqa: E501
```

### WR-02: `_insert_markdown` / `_insert_results_body` の Tk 描画分岐に直接テストが無い

**File:** `pagefolio/ocr_dialog.py:1465-1521`
**Issue:** `parse_markdown`（純関数）は `tests/test_md_render.py` で網羅テストされ、`resolve_ocr_prompt` も `test_provider_ui.py` で検証済みだが、本差分で新設した **Tk 描画ヘルパー `_insert_markdown` / `_insert_results_body` 自体のテストが存在しない**。特に「行レベルタグの境界（`line_start` 〜 `end-1c`）が改行を含まないこと」「markdown=False 経路の後方互換（末尾改行 1 個）」「複数ページ連結時にページセパレータへ md タグが漏れないこと」は回帰しやすい箇所。pytest 597 passed はこの 3 メソッドの分岐を直接踏んでいない可能性が高い。
**Fix:** `pagination.py` 同様の純関数化が難しい Tk 依存部だが、`page_indices`/`results` をスタブした最小 OCRDialog（あるいは `_insert_markdown` を `text` 引数注入で部分テスト）で、(1) `kind` タグの付与範囲が行本文のみ、(2) markdown=False で raw + "\n"、の 2 ケースだけでも `tag_ranges` をアサートしておくと回帰検出になる。

## Info

### IN-01: `table` プリセットの Markdown テーブル出力は整形されず raw 表示のまま

**File:** `pagefolio/ocr_dialog.py:1487-1489`
**Issue:** `table` プリセットのプロンプト（`PROVIDER_OCR_PROMPTS["claude"]["table"]` 等）は LLM に **Markdown テーブル（`|` 区切り）** を出力させるが、整形ガードは `preset == "markdown"` のみ。よって table 出力の `|...|` 行は `parse_markdown` を通らず素のテキストとして表示される。これは Pitfall 2（text/table に Markdown パーサを当てない構造ガード）として **意図的な設計判断**でありバグではないが、ユーザー視点では「table プリセットなのにテーブル整形されない」という直感との乖離が残る。
**Fix:** 仕様として許容なら対応不要。将来 table を整形対象に含める場合は `markdown = self.preset_var.get() in ("markdown", "table")` への拡張を検討（ただし `parse_markdown` 側にテーブル行種別が未実装のため別途拡張が必要）。

### IN-02: インラインコード（`` `code` ``）は描画されない（`_CODE` 正規表現が呼ばれない）

**File:** `pagefolio/ocr_dialog.py:1474`（描画側）/ 参考: `pagefolio/md_render.py:25,28`（パーサ側）
**Issue:** 本差分は `md_code` を**行レベル（コードフェンス）**専用タグとして配線しているが、`md_render.py` の `_split_inline` は `_BOLD` のみ適用し `_CODE`（インライン `` `...` ``）を一切使わない（`_CODE` は定義のみで未使用 = 04-01 由来のデッドコード）。結果、本文中のインラインコードは整形されず素のバッククォート付きテキストで表示される。本差分のスコープ（04-03 配線）の問題ではなく 04-01（md_render.py）側の積み残しだが、配線結果としてユーザーに見える挙動なので記録する。
**Fix:** 本差分では対応不要。`_CODE` 未使用は md_render.py 側のフォローで `_split_inline` に組み込むか、不要なら `_CODE` 定義を削除する（別フェーズ）。

### IN-03: md_h1 と md_h2 が同一 `C["ACCENT"]` 色で、差別化がフォントサイズのみ

**File:** `pagefolio/ocr_dialog.py:508-509`
**Issue:** h1（`_font(4,"bold")`）と h2（`_font(2,"bold")`）はサイズ差のみで前景色は両方 `C["ACCENT"]`。見出し階層の視認性はサイズ差に依存し、行間が詰まった OCR 結果では h1/h2 の判別がつきにくい場面がありうる。視覚品質のみの軽微事項。
**Fix:** 仕様上問題なければ対応不要。階層強調を上げるなら h2 を `C["TEXT_MAIN"]` 等に変えて色でも差をつける選択肢がある。

### IN-04: `# fmt: off` + `# noqa: E501` による単一行固定が受入基準（grep ゲート）に結合している

**File:** `pagefolio/ocr_dialog.py:505-513`
**Issue:** コメント「受入基準の単一行 grep ゲートを満たすため fmt:off で折返しを抑止」が示すとおり、タグ定義の物理レイアウト（1 行）が **受入基準の grep カウントに合わせて固定**されている。コードの体裁が検証スクリプトの実装詳細に結合しており、将来 grep ゲートが変われば `# fmt: off` の存在理由が失われ、逆に誰かが整形を戻すと受入基準が静かに壊れる。MEMORY の「受入基準 grep は method-scoped にすべき」という既知の落とし穴と同根。
**Fix:** 本差分では動作影響なし。受入基準側を「結果ベース（タグが定義されているか）」へ寄せられれば `# fmt: off` を外して通常整形に戻せる。少なくとも `# fmt: off` のコメントに「この行固定は受入 grep 依存・基準改定時に解除可」と明記しておくと将来の混乱を防げる。

---

## ブロッカーの有無

**ブロッカー: なし（Critical 0 / High 0）。**

## 総評

依頼の 5 観点（`name` 前方移動の NameError/経路依存・markdown ガードの後方互換・裸 except・テーマ色/フォント・raw 維持/セキュリティ）はすべて合格水準です。特に (1) プロンプト解決の `resolve_ocr_prompt` 集約は旧 if/else と等価な後方互換を保ち、(2) markdown 整形は `_insert_results_body` の False 経路で従来挙動を完全温存し、(3) `parse_markdown` の全産出タグが `tag_configure` 済みで未定義タグ例外も起きません。ロジック上の実害バグは検出されませんでした。

残る指摘は品質・保守性に閉じます。優先度順では **WR-02（Tk 描画分岐の直接テスト欠如）** が最も価値が高く、`_insert_markdown` の行レベルタグ境界と markdown=False の後方互換は回帰しやすいため、最小スタブでの `tag_ranges` アサートを 1〜2 ケース足すことを推奨します。次点で **WR-01（md_code フォントの規約例外明示）**。IN 系（table 非整形・インラインコード未描画・見出し同色・fmt:off の grep 結合）はいずれも仕様許容可能で、対応は将来フェーズで構いません。

このまま出荷可能と判断します。

---

_Reviewed: 2026-06-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
