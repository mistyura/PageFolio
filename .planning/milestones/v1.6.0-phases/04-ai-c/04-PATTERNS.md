# Phase 4: AI 出力品質（プランC） - Pattern Map

**Mapped:** 2026-06-19
**Files analyzed:** 6（新規 2 / 改修 3 / テスト 1 は新規・1 は既存拡張）
**Analogs found:** 6 / 6（全ファイルに既存アナログあり）

CONTEXT.md は未作成。本マップは 04-RESEARCH.md を正とし、挿入点・既存パターンを実コードで裏取りした結果に基づく。

## File Classification

| 新規/改修ファイル | 役割 | データフロー | 最も近いアナログ | Match Quality |
|-------------------|------|-------------|------------------|---------------|
| `pagefolio/md_render.py`（新規） | utility（純ロジック層） | transform（Markdown 文字列→構造データ） | `pagefolio/pagination.py` | exact（Tk/fitz 非依存純関数集約・同役割同データフロー） |
| `pagefolio/ocr.py`（改修：`PROVIDER_OCR_PROMPTS` + `resolve_ocr_prompt` 追加） | utility（純ロジック層） | transform（プリセット×プロバイダ×カスタム→文字列） | `pagefolio/ocr.py` 既存 `OCR_PROMPTS` / `clamp_retry_after`（同ファイル内の純ユーティリティ前例） | exact |
| `pagefolio/ocr_dialog.py`（改修：`_render_results_ordered` 描画分岐 + `_build` タグ定義 + `_on_run` プロンプト解決差し替え） | component（UI 層・薄い描画層） | request-response（results→tk.Text 描画 / preset→prompt 解決） | `pagefolio/ocr_dialog.py` 既存 `_render_results_ordered` / `_on_run`（1085-1090） | exact（自ファイル既存メソッド拡張） |
| `tests/test_md_render.py`（新規） | test（純関数 unit） | request-response（入力→戻り値アサート） | `tests/test_pagination.py` | exact（純関数 unit・Tk 非生成方針） |
| `tests/test_provider_ui.py`（改修：`resolve_ocr_prompt` テスト群追加） | test（純関数 unit） | request-response | `tests/test_provider_ui.py` 既存 `TestModelSupportsEffort`（非バインドメソッド／純ロジック検証） | exact |
| `pagefolio/lang.py`（改修：raw/rendered トグル等の新規 UI 文言を ja/en 両辞書へ） | config（言語辞書） | — | `pagefolio/lang.py` 既存 `ocr_preset_*` キー（ja:282-284 / en:720-722） | exact |

## Pattern Assignments

### `pagefolio/md_render.py`（utility, transform）

**Analog:** `pagefolio/pagination.py`

**踏襲すべき具体パターン（pagination.py から）:**

- **モジュール docstring の様式**（pagination.py:1-17）：冒頭にライセンスヘッダ 3 行（`# PageFolio - PDF Page Organizer` / `# Copyright (c) 2026 mistyura` / `# Released under the MIT License`）、続けて「Tkinter / fitz 非依存」を明示する純ロジック層宣言。`md_render.py` も同様に「`tkinter` / `fitz` を一切 import しない」を docstring に書く（pagination.py:11 の作法）。

- **純関数の docstring に不変条件・堅牢性ケースを明記**（pagination.py:25-36 の `window_bounds`）：戻り値型・境界ケース（空入力）を docstring に書く。`parse_markdown` の戻り値型 `list[tuple[str, list[tuple[str, str|None]]]]` と `line_kind` の取りうる値（`"md_h1"|"md_h2"|"md_bullet"|"md_code"|""`）を明記する。

- **例外型を必ず指定**（pagination.py:133-137 の `clamp_page_size`）：
```python
try:
    n = int(value)
except (ValueError, TypeError):   # 裸 except 禁止・CLAUDE.md
    return PAGE_SIZE_DEFAULT
```
`md_render.py` のパースで例外捕捉が要る場合は `re` 由来の `re.error` / `ValueError` 等を型指定する。RESEARCH の ReDoS 回避（非貪欲 `.+?` ＋文字クラス `[^`+`]+`）方針（04-RESEARCH.md:429）を踏襲。

- **import は標準ライブラリ `re` のみ**（V14-D-01 新規依存ゼロ）。RESEARCH コード例（04-RESEARCH.md:261-308）の `parse_markdown` / `_split_inline` シグネチャをそのまま採用する。`_` プレフィックスで内部ヘルパー（`_split_inline`）を示す（pagination.py には内部ヘルパーはないが CLAUDE.md 命名規約）。

---

### `pagefolio/ocr.py`（utility, transform — `resolve_ocr_prompt` 追加）

**Analog:** 同ファイル既存 `OCR_PROMPTS`（ocr.py:19-32）と純ユーティリティ `clamp_retry_after`（ocr.py:58-）

**既存 `OCR_PROMPTS` 構造**（ocr.py:19-32）— これと同じ辞書スタイルで `PROVIDER_OCR_PROMPTS` を直下に追加：
```python
OCR_PROMPTS = {
    "text": ("この画像に写っている…本文のみを出力してください。"),
    "table": ("この画像の表をMarkdownテーブル形式で…"),
    "markdown": ("この画像の内容をMarkdown形式で書き出してください。…"),
}
```

**踏襲すべき具体パターン:**

- **モジュール定数はファイル上部に集約**（ocr.py:18-55 に `OCR_PROMPTS`・`DEFAULT_*`・`MAX_RETRIES` 等が並ぶ）。`PROVIDER_OCR_PROMPTS: dict[str, dict[str, str]]` を `OCR_PROMPTS` の直後（ocr.py:33 付近）に置く。RESEARCH の文言（04-RESEARCH.md:158-177）を採用し、`claude`/`gemini` のみ定義、`lmstudio`/`tesseract`/`off` は未定義のまま汎用フォールバックに委ねる（Pitfall 4）。

- **純関数 docstring に優先順位・後方互換意図を明記**（clamp_retry_after が cap 意図を docstring 化しているのと同様）。`resolve_ocr_prompt(preset, provider_name, custom_prompt="")` のシグネチャ・優先順位（custom 非空 > プロバイダ別 > 汎用フォールバック）を RESEARCH コード例（04-RESEARCH.md:179-190）どおり実装。フォールバックは `OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])`（既存 `_on_run` の ocr_dialog.py:1090 と同じ既定値 `"text"` を踏襲し挙動を変えない）。

- **Tk/ネットワーク非依存を維持**（文字列合成のみ）。`messagebox` 等 Tk 依存 import を関数内へ持ち込まない。

---

### `pagefolio/ocr_dialog.py`（component, request-response — 3 箇所改修）

**Analog:** 同ファイル既存 `_render_results_ordered`（1456-1479）/ `_on_run`（1085-1090）/ `self.text` 生成（488-502）

**改修1: `_on_run` のプロンプト解決差し替え**（現状 ocr_dialog.py:1085-1090）：
```python
# 現状（このブロックを resolve_ocr_prompt 呼び出しへ置換）
if self.custom_prompt:
    self._ocr_prompt = self.custom_prompt
else:
    preset = self.preset_var.get()
    self._ocr_prompt = OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])
```
- provider 名は同メソッド内 `name = self.app.settings.get("ocr_provider", "")`（ocr_dialog.py:1120）で既に取得済み。**ただし取得は 1120 行で 1085 より後**なので、置換時は `name` 取得を前方へ移動するか `resolve_ocr_prompt` 呼び出しを `name` 取得後に移す。
- 置換後：`self._ocr_prompt = resolve_ocr_prompt(self.preset_var.get(), name, self.custom_prompt)`。`from pagefolio.ocr import ... resolve_ocr_prompt` を既存 import（`OCR_PROMPTS` / `build_provider`）に追加。
- カスタム上書き温存（成功基準3・Pitfall 3）は純関数側で担保されるため、UI 側の分岐は不要になる。

**改修2: `_build` でのタグ定義**（`self.text = tk.Text(...)` 直後・ocr_dialog.py:488-502 の近傍）：
- 既存 `tk.Text` は `bg=C["BG_CARD"]` / `fg=C["TEXT_MAIN"]` / `font=self._font(-1)` で生成済み。タグ定義もこの**テーマ色 `C[]` ＋ `self._font(delta, weight)` ヘルパー**を厳守（CLAUDE.md ハードコード禁止）：
```python
# _font シグネチャ: _font(delta=0, weight=None) → ("Segoe UI", max(7,10+delta)[, weight])
self.text.tag_configure("md_h1", font=self._font(4, "bold"), foreground=C["ACCENT"])
self.text.tag_configure("md_h2", font=self._font(2, "bold"), foreground=C["ACCENT"])
self.text.tag_configure("md_bullet", lmargin1=20, lmargin2=36)
self.text.tag_configure("md_code", background=C["BG_PANEL"])
self.text.tag_configure("md_bold", font=self._font(-1, "bold"))
```
- `ACCENT` / `BG_PANEL` は themes.py に存在するキー。等幅は `Consolas` を許容するが（RESEARCH 注記）サイズは `self._font_size()`（ocr_dialog.py:150-154）で追従させること。

**改修3: `_render_results_ordered` の描画分岐**（ocr_dialog.py:1456-1479）：
- 既存は `self.text.insert("end", self.results[page_idx] + "\n")`（1466/1468）の素朴 insert。
- **ガード条件 `preset == "markdown"` かつ rendered モード**（Pitfall 2/5）。preset は `self.preset_var.get()` で取得。条件成立時のみ `for kind, spans in parse_markdown(text):` ループで `insert` + `tag_add`（RESEARCH コード例 04-RESEARCH.md:137-146）。非該当は現行の素朴 insert を温存（後方互換）。
- `from pagefolio.md_render import parse_markdown` を追加。
- 描画層は「純関数の戻り値を insert/tag_add するだけ」に薄く保つ（Anti-Pattern 回避・テスト不能化を防ぐ）。

**改修4（任意・Open Question Q1）: `_format_full_text` は変更しない**（ocr_dialog.py:1596-1604）。raw `self.results` を返す現行実装を維持（整形は表示専用・Pitfall 5）。`.md` 保存に raw が最適。

**例外捕捉:** `_on_run` 既存の `except (tk.TclError, ValueError):`（ocr_dialog.py:1078 等）に倣い、描画/パース例外を捕捉する場合は `tk.TclError` 等を型指定（裸 except 禁止）。

---

### `tests/test_md_render.py`（test, 新規）

**Analog:** `tests/test_pagination.py`

**踏襲すべき具体パターン:**

- **Tk 非生成・純関数の戻り値を直接アサート**（test_pagination.py 全体・特に `TestWindowBounds`）。`OCRDialog(...)` を一切インスタンス化しない（Pitfall 1 の Warning sign）。
- **`Test<FeatureName>` クラス + docstring で対応 Req を明記**（test_pagination.py:27 `class TestWindowBounds: """SC1: ..."""`）。例：`class TestParseMarkdown: """V16-AI-01: 行種別/インライン span 分類"""`。
- **境界・不変条件のループ網羅**（test_pagination.py:58-65 `test_invariant_*`）：H1/H2/箇条書き/コードブロック各行種別、`**bold**` / `` `code` `` span、コードフェンス内では行種別判定をしないこと等を網羅。RESEARCH の最小テスト（04-RESEARCH.md:315-322）を起点に拡充。
- import は `from pagefolio.md_render import parse_markdown`（test_pagination.py:12-22 の関数単位 import スタイル）。`tests/**` は S101 除外なので `assert` 直書きでよい。

---

### `tests/test_provider_ui.py`（test, 既存拡張 — `resolve_ocr_prompt` テスト群追加）

**Analog:** 同ファイル既存 `TestModelSupportsEffort`（test_provider_ui.py:31-）

**踏襲すべき具体パターン:**

- **ロジック層のみ検証・Tk ウィジェット生成なし**（ファイル冒頭 docstring test_provider_ui.py:4-8 の方針）。`resolve_ocr_prompt` は純関数なのでスタブすら不要、直接 import して呼ぶ。
- **新規テストクラス追加**（例 `class TestResolveOcrPrompt:`）。RESEARCH の 3 ケース（04-RESEARCH.md:329-336）を実装：
  - `test_custom_overrides_provider_template`：`resolve_ocr_prompt("markdown","claude","MY CUSTOM") == "MY CUSTOM"`（成功基準3・Pitfall 3）
  - `test_lmstudio_falls_back_to_generic`：`resolve_ocr_prompt("text","lmstudio","") == OCR_PROMPTS["text"]`（Pitfall 4）
  - `test_claude_markdown_uses_provider_template`：`!= OCR_PROMPTS["markdown"]`
- import：`from pagefolio.ocr import resolve_ocr_prompt, OCR_PROMPTS`。

---

### `pagefolio/lang.py`（config — ja/en 両辞書へ新規 UI 文言）

**Analog:** 既存 `ocr_preset_*` キー（ja:282-284 / en:720-722）

**踏襲すべき具体パターン:**

- **新規キーは ja / en 両辞書に同一キーで追加**（CLAUDE.md LANG ルール・Pitfall 6）。既存 `ocr_preset_markdown` が ja:284 / en:722 で対になっているのと同様。raw/rendered トグル等の文言を導入する場合（Open Question Q1 で要否確定）、両方へ。
- **`test_lang_parity.py` が対称性を担保**（test_lang_parity.py:13-16 `set(ja) ^ set(en)` が空であること）。プレースホルダ付き文言を足す場合は `test_retry_and_truncated_format_smoke`（同:19-25）に倣い `.format()` スモークを追加検討。
- 永続化が必要なら（Q1）`pagefolio/settings.py` の `DEFAULT_SETTINGS` に `ocr_render_mode` を `setdefault`/既定追加（`_SENSITIVE_KEYS` 対象外・無害値）。test_pagination.py:296-336 の `thumb_page_size` setdefault 後方互換テストが settings 拡張のテスト前例。

## Shared Patterns

### 純ロジック層分離（最重要・横断）
**Source:** `pagefolio/pagination.py`（全体）/ `pagefolio/ocr.py:58-`（純ユーティリティ）
**Apply to:** `md_render.py`・`ocr.py` の `resolve_ocr_prompt`
変換・解決ロジックは Tk/fitz 非依存純関数へ集約し、UI 層（`ocr_dialog.py`）は戻り値を描画するだけに薄く保つ。これにより Tk を生成しない unit テスト（582 件ベースライン方針）が書ける。Anti-Pattern「描画メソッドにベタ書き」を回避。

### テーマ色は `C[]` 経由
**Source:** `pagefolio/ocr_dialog.py:86,173,174,490-492`（`C["BG_DARK"]` / `C["ACCENT"]` / `C["BG_CARD"]` 等）
**Apply to:** `_build` のタグ定義（`tag_configure` の foreground/background）
16 進ハードコード禁止。`md_h1`/`md_h2` は `C["ACCENT"]`、`md_code` 背景は `C["BG_PANEL"]`。

### フォントは `self._font(delta, weight)` ヘルパー
**Source:** `pagefolio/ocr_dialog.py:144-148`（`_default_font(delta=0, weight=None)`）, 多数の `font=self._font(...)` 利用（175,187,194,493 等）
**Apply to:** 見出しタグの font 定義
サイズ直値禁止。`self._font(4, "bold")` 等。等幅サイズ追従に `self._font_size()`（150-154）。

### 例外型指定（裸 except 禁止）
**Source:** `pagefolio/pagination.py:135`（`except (ValueError, TypeError):`）/ `pagefolio/ocr_dialog.py:1078`（`except (tk.TclError, ValueError):`）
**Apply to:** `md_render.py` のパース・`ocr_dialog.py` の描画
必ず `except Exception as e:` または具体型。`re.error`/`tk.TclError`/`ValueError` を文脈に応じ指定。

### LANG ja/en 対称
**Source:** `pagefolio/lang.py:282-284 / 720-722`、`tests/test_lang_parity.py`
**Apply to:** 新規 UI 文言追加時すべて
両辞書同一キー。`test_lang_parity.py` で回帰防止。

### 新規依存ゼロ（V14-D-01）
**Apply to:** 全ファイル
`re` / `tkinter` 標準ライブラリのみ。外部 Markdown ライブラリ（markdown/mistune/tkhtmlview）は不採用。

## No Analog Found

なし。全 6 ファイルに既存のクローズな前例（純関数集約＝pagination.py、純ロジック unit＝test_pagination.py / test_provider_ui.py、LANG＝既存 ocr_preset キー、UI 描画＝ocr_dialog.py 自身の既存メソッド）が存在する。

## Metadata

**Analog search scope:** `pagefolio/`（pagination.py / ocr.py / ocr_dialog.py / lang.py / themes.py）, `tests/`（test_pagination.py / test_provider_ui.py / test_lang_parity.py）
**Files scanned:** 8
**Pattern extraction date:** 2026-06-19
