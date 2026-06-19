---
phase: 04-ai-c
verified: 2026-06-20T00:00:00Z
status: human_needed
score: 5/7 truths verified
behavior_unverified: 2
overrides_applied: 0
behavior_unverified_items:
  - truth: "OCRDialog で markdown プリセット結果が読みやすく整形表示される（成功基準1 の実描画の見え方）"
    test: "実機で OCR を markdown プリセットで実行し、OCRDialog の結果テキストに見出し（md_h1/md_h2 が ACCENT 色・太字）・箇条書き（• インデント）・コードブロック（BG_PANEL 背景・Consolas）・**bold** が整形表示され、プレーンテキストより読みやすいことを目視確認する"
    expected: "見出し・箇条書き・コード・太字がタグ整形で視覚的に区別され、素朴 insert より読みやすい"
    why_human: "tk.Text の tag_configure による実描画（色・フォント・余白の見え方）と『読みやすさ』は静的解析では判定不能。テーマ色・フォント解決は実 Tk ルート上でのみ評価できる"
  - truth: "Claude=XML / Gemini=明示指示のプロバイダ別プロンプトで実際に OCR 出力品質が引き出される（成功基準2 の実 API 出力品質）"
    test: "Claude / Gemini 実 API で markdown プリセット OCR を実行し、プロバイダ別テンプレートが期待どおりの構造化 Markdown を引き出すか出力を比較確認する"
    expected: "プロバイダ別最適化プロンプトで、汎用プロンプトと同等以上の構造化された OCR 出力が得られる"
    why_human: "外部 API（Claude / Gemini）への実リクエストが必要で、出力品質は経験的にしか評価できない。コードはテンプレート選択ロジックまでしか保証しない"
human_verification:
  - test: "実機で markdown プリセット OCR を実行し OCRDialog の整形表示（見出し/箇条書き/コード/太字）の見え方と読みやすさを目視確認"
    expected: "md_* タグ整形でプレーンテキストより読みやすく提示される"
    why_human: "tk.Text 実描画と読みやすさは静的解析不能（gate=blocking の human-verify はユーザー判断でスキップ済）"
  - test: "Claude / Gemini 実 API でプロバイダ別プロンプトの OCR 出力品質を確認"
    expected: "プロバイダ別最適化プロンプトで構造化された OCR 出力が得られる"
    why_human: "外部 API への実リクエストと経験的品質評価が必要"
---

# Phase 04: AI 出力品質（プランC） 検証レポート

**Phase Goal:** OCR 結果が Markdown として読みやすく整形表示され、プロバイダ別に最適化されたプロンプトで出力品質が引き出される（既存カスタムプロンプト機構と両立）。
**Verified:** 2026-06-20
**Status:** human_needed
**Re-verification:** No — 初回検証

> **Bash ツール不可の補足:** 本セッションでは Bash 実行が拒否されたため、テスト/ruff の再実行は行っていない。ユーザー報告（ruff クリーン・pytest 597 passed）を前提とし、検証はディスク上のソース・テスト・配線の静的解析（goal-backward）で実施した。各純関数には戻り値を直接アサートする unit テストが存在することをソース上で確認済み。

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `parse_markdown` が md_h1/md_h2/md_bullet/md_code/`""` を正しく分類し、フェンス内は見出し判定しない | ✓ VERIFIED | `md_render.py:48-80`（優先順位 code>h2>h1>bullet>段落、`in_code` フラグでフェンス制御）+ `test_md_render.py:20-45` で直接アサート |
| 2 | `parse_markdown` が `**bold**` をインライン span `("bold","md_bold")` として抽出 | ✓ VERIFIED | `md_render.py:28-45`（`_split_inline` / `_BOLD`）+ `test_md_render.py:49-62` |
| 3 | `md_render` は tkinter/fitz 非依存の純ロジック層 | ✓ VERIFIED | `md_render.py:20` で import は `re` のみ。Tk/fitz の import なし（Grep 確認） |
| 4 | `resolve_ocr_prompt` が Claude=XML / Gemini=明示指示のプロバイダ別テンプレートを返す | ✓ VERIFIED | `ocr.py:40-73`（`PROVIDER_OCR_PROMPTS` に claude=`<task>/<rules>`・gemini=命令文）+ `ocr.py:99-101` + `test_provider_ui.py:580-584` |
| 5 | カスタムプロンプト非空時は custom をそのまま返し、未定義時は OCR_PROMPTS へフォールバック（成功基準3 後方互換） | ✓ VERIFIED | `ocr.py:97-102`（優先順位 custom>provider>汎用）+ `test_provider_ui.py:568-588`（custom 上書き・lmstudio/tesseract/off フォールバック）。`_on_run` は `self.custom_prompt` を渡す（`ocr_dialog.py:1099`） |
| 6 | OCRDialog で markdown プリセット結果が md_* タグで整形表示され、読みやすく提示される（成功基準1 の実描画） | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | 構造は完備（`_build` で md_* 5 タグ定義 `ocr_dialog.py:508-512`・`_insert_markdown` `1465-1483`・`preset=="markdown"` ガード `1489`）。ただし実描画の見え方／読みやすさは Tk 実機目視が必要で、gate=blocking の human-verify はユーザー判断でスキップ |
| 7 | プロバイダ別プロンプトで実際に OCR 出力品質が引き出される（成功基準2 の実 API 品質） | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | テンプレート選択ロジック（truth #4）まではコードで保証されるが、実 API 出力品質は外部リクエストと経験的評価が必要で静的検証不能 |

**Score:** 5/7 truths verified（2 present, behavior-unverified）

### 成功基準別 判定

| 成功基準 | 構造（コード）判定 | 実機判定 |
|----------|--------------------|----------|
| 1. markdown 整形表示で読みやすい | ACHIEVED（純関数 + 配線 + 5 タグ + markdown 限定ガード完備） | **human-verify-pending**（実描画の見え方・読みやすさ未確認） |
| 2. プロバイダ別最適化プロンプト | ACHIEVED（Claude=XML/Gemini=明示の定数 + resolve_ocr_prompt 配線完備） | **human-verify-pending**（実 API 出力品質未確認） |
| 3. カスタムプロンプト機構と両立 | **ACHIEVED**（custom 最優先・直接アサートテスト合格・`_on_run` 配線） | コードで完全検証可能・実機確認不要 |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/md_render.py` | `parse_markdown`（純ロジック層・81 行） | ✓ VERIFIED | exists / substantive（81行・全 line_kind 実装） / wired（`ocr_dialog.py:14` が import） |
| `pagefolio/ocr.py` | `PROVIDER_OCR_PROMPTS` + `resolve_ocr_prompt` | ✓ VERIFIED | `ocr.py:40,76`。wired（`ocr_dialog.py:23` が import・`1099` で呼出） |
| `pagefolio/ocr_dialog.py` | `_on_run` 配線・md_* 5 タグ・markdown 分岐・`_insert_markdown` | ✓ VERIFIED | `1099`（resolve）・`508-512`（5 タグ）・`1489`（ガード）・`1465`（ヘルパー） |
| `tests/test_md_render.py` | parse_markdown unit テスト | ✓ VERIFIED | 行種別/bold/フェンス/不変条件を直接アサート |
| `tests/test_provider_ui.py` | resolve_ocr_prompt unit テスト | ✓ VERIFIED | `TestResolveOcrPrompt`（`559-588`）custom/フォールバック/プロバイダ別 |

### Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| `ocr_dialog.py _on_run` | `ocr.py resolve_ocr_prompt` | `resolve_ocr_prompt(self.preset_var.get(), name, self.custom_prompt)`（name はプロンプト解決前 `1097` に取得） | ✓ WIRED（`1099`） |
| `ocr_dialog.py _insert_markdown` | `md_render.py parse_markdown` | `for kind, spans in parse_markdown(text)` → insert + tag_add | ✓ WIRED（`1474-1483`） |
| `ocr_dialog.py _build` タグ | `themes.py C` | `tag_configure(..., foreground=C["ACCENT"]/background=C["BG_PANEL"])` ハードコード無し | ✓ WIRED（`508-512`） |
| `_render_results_ordered` | markdown ガード | `markdown = self.preset_var.get() == "markdown"` → markdown 時のみ `_insert_markdown` | ✓ WIRED（`1489,1518-1521`） |
| コピー/保存 | raw 維持 | `_format_full_text` は `self.results[...]` を結合し raw を返す（タグ/整形無し） | ✓ WIRED（`1638-1646`） |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| V16-AI-01 | 04-01, 04-03 | ✓ SATISFIED（構造）／ ? 実描画は human | `md_render.py` + OCRDialog 整形配線。REQUIREMENTS.md で Complete |
| V16-AI-02 | 04-02, 04-03 | ✓ SATISFIED（構造）／ ? 実 API 品質は human | `PROVIDER_OCR_PROMPTS` + resolve 配線。REQUIREMENTS.md で Complete |

### Anti-Patterns Found

| File | Pattern | Severity |
|------|---------|----------|
| md_render.py / ocr.py / ocr_dialog.py | TODO/FIXME/XXX/HACK/PLACEHOLDER | なし（Grep ヒット 0） |

**軽微な気付き（非ブロッカー）:** `md_render.py:24` の `_CODE`（インラインコード `` `...` `` 用 regex）は定義されているが `_split_inline` で未使用。インライン span はプラン契約上 `md_bold` のみが要件のため目標未達ではない。将来インラインコード対応時の残置とみなせる。

### Human Verification Required

gate=blocking の human-verify チェックポイントがユーザー判断でスキップされたため、以下 2 点が実機未検証で残る（成功基準1/2 の「見え方」「実 API 品質」）。コード構造・配線・後方互換ガードは検証済み。

#### 1. markdown 整形表示の目視確認（成功基準1）
- **Test:** 実機で markdown プリセット OCR を実行し OCRDialog 結果の整形（見出し/箇条書き/コード/太字）の見え方と読みやすさを確認
- **Expected:** md_* タグ整形でプレーンテキストより読みやすい
- **Why human:** tk.Text 実描画と読みやすさは静的解析不能

#### 2. プロバイダ別プロンプトの実 API 出力品質（成功基準2）
- **Test:** Claude / Gemini 実 API で markdown OCR を実行し出力品質を確認
- **Expected:** プロバイダ別テンプレートで構造化された OCR 出力が得られる
- **Why human:** 外部 API リクエストと経験的品質評価が必要

### Gaps Summary

ブロッカー（FAILED truth / MISSING・STUB artifact / NOT_WIRED link / ブロッカー anti-pattern）は **無し**。全 5 成果物が exists+substantive+wired、全 key link が WIRED、後方互換（custom 上書き・コピー/保存 raw 維持・text/table 素朴 insert）も構造的に温存。成功基準3 はコードで完全検証済み。

残るのは成功基準1/2 の「実機での見え方／実 API 出力品質」2 点のみで、これは構造実装完了済みかつ本質的に人間の目視・経験評価を要する性質（behavior-dependent）であり、gate=blocking の human-verify がユーザー判断でスキップされたことに由来する。コード品質起因のギャップではない。

## 総合判断

**コード構造としてはフェーズ目標を満たしている。** 純ロジック層（parse_markdown / resolve_ocr_prompt）は網羅的 unit テストで behavior が直接検証され、OCRDialog への配線・テーマ色準拠・markdown 限定ガード・後方互換（カスタム上書き／コピー保存 raw／text・table 素朴 insert）がすべて確認できた。成功基準3 は完全に ACHIEVED。

**完了可否:** 自動検証範囲ではブロッカー無し（5/7 VERIFIED、残 2 は present-behavior-unverified）。ただし成功基準1/2 の「実描画の見え方」「実 API 出力品質」は構造完備だが実機未検証のため status=human_needed。フェーズを完了扱いにするには、上記 human verification 2 点をユーザーが実機確認するか、スキップ判断を明示的にオーバーライドとして受容する必要がある。コード起因の修正は不要。

---

_Verified: 2026-06-20_
_Verifier: Claude (gsd-verifier)_
