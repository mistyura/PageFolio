# Phase 4: AI 出力品質（プランC） - Research

**Researched:** 2026-06-19
**Domain:** Tkinter での Markdown 整形描画（`tk.Text` タグ）／ クラウド LLM プロバイダ別プロンプト最適化
**Confidence:** HIGH（対象コードは全て本セッションで実読。新規外部依存を導入しないため不確実性が低い）

## Summary

本フェーズは PageFolio の既存 OCR サブシステム（`pagefolio/ocr_dialog.py` の `OCRDialog`、`pagefolio/ocr_providers.py` の各 Provider、`pagefolio/ocr.py` の `OCR_PROMPTS` とユーティリティ）への **純加算的な拡張** で完結する。新規コンポーネントの導入や外部 I/O の追加は不要で、(1) OCR 結果テキストエリア（既存の `tk.Text`）に Markdown 整形を施す描画ロジックの追加、(2) プロバイダ別の OCR プロンプトテンプレートの追加、の 2 点が中核となる。いずれも既存のデータフロー（`_render_results_ordered` への描画分岐追加、`_on_run` でのプロンプト合成箇所の差し替え）に挿し込む形で実現できる。

`tk.Text` は `tag_configure` / `tag_add` によるリッチテキスト・スタイリングを標準ライブラリのみで提供する [CITED: docs.python.org/3/library/tkinter.html]。したがって V16-AI-01（Markdown 整形表示）は **新規 pip 依存ゼロ（V14-D-01 厳守）** で達成可能であり、外部 Markdown ライブラリ（`markdown` / `mistune` / `tkhtmlview`）はいずれもこの環境に未インストール [VERIFIED: `python -c "import markdown/mistune/tkhtmlview"` が全て ModuleNotFoundError] であることを確認した。標準ライブラリ実装を最優先で採用する。

V16-AI-02（プロバイダ別プロンプト）は、現状の単一 `OCR_PROMPTS` 辞書（`pagefolio/ocr.py:19-32`）を「プリセット × プロバイダ」の 2 軸で解決する純関数へ昇格させ、`_on_run`（`ocr_dialog.py:1085-1090`）のプロンプト合成箇所をその純関数呼び出しに置き換えることで実現する。カスタムプロンプト（v1.5.0 由来・設定キー `ocr_custom_prompt`）は **最優先（上書き）** の現行挙動（`ocr_dialog.py:1086-1087`）を温存することで成功基準3（両立）を満たす。

**Primary recommendation:** `tk.Text` のタグ機能で見出し・箇条書き・コード・強調をスタイリングする純標準ライブラリ実装を採用し、Markdown→（行種別, スタイルタグ）への変換を Tk 非依存の純関数（新規 `pagefolio/md_render.py`）に集約する。プロンプト解決も純関数 `resolve_ocr_prompt(preset, provider, custom_prompt)` として `pagefolio/ocr.py` に集約し、`pagination.py` / `test_provider_ui.py` と同じ「純関数＋Tk非依存テスト」パターンに倣う。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Markdown→スタイル変換（行種別判定・インライン span 抽出） | 純ロジック層（新規 `md_render.py`） | — | Tk/fitz 非依存で単体テスト可能にするため（`pagination.py` 前例） |
| `tk.Text` へのタグ適用・描画 | UI 層（`ocr_dialog.py`） | 純ロジック層 | `tag_configure`/`tag_add` は Tk 依存。変換結果（純データ）を受けて描画のみ担う |
| raw/rendered 切替 | UI 層（`ocr_dialog.py`） | 設定層（`settings.py`） | Radiobutton/トグルは Tk。永続化が要るなら settings キー |
| OCR プロンプト解決（プリセット×プロバイダ×カスタム） | 純ロジック層（`ocr.py`） | — | 文字列合成のみ。Tk/ネットワーク非依存で純関数化 |
| プロンプト送信（ペイロード組立） | プロバイダ層（`ocr_providers.py`） | — | 既存の `_build_payload` が prompt を受け取る。**変更不要**（プロンプト文字列のみ差し替え） |
| エクスポート（コピー/保存） | UI 層（`ocr_dialog.py`） | — | `_format_full_text` は raw テキストを返す。整形は表示のみで出力は raw 維持 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tkinter` (`tk.Text`) | 標準ライブラリ（Tk 8.6） | Markdown 整形のリッチテキスト描画（`tag_configure`/`tag_add`） | 標準同梱・新規依存ゼロ（V14-D-01）。既存 `OCRDialog.text` がそのまま使える [VERIFIED: `tkinter.TkVersion == 8.6`] |
| `re`（標準） | 標準ライブラリ | Markdown 行種別判定・インライン span（`**bold**` / `` `code` ``）抽出 | 軽量・依存ゼロ。OCR Markdown は見出し/箇条書き/表/強調/コードの限定サブセットで足りる |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| （なし） | — | — | 本フェーズで新規ライブラリは追加しない |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tk.Text` タグ自前実装 | `tkhtmlview`（Markdown→HTML→Tk 描画） | 新規 pip 依存が増え V14-D-01 に違反。未インストール [VERIFIED: import 失敗]。不採用 |
| `re` ベースの軽量パーサ | `markdown` / `mistune`（本格 Markdown パーサ） | 新規依存。HTML 中間表現を経るため `tk.Text` 直描画とは噛み合わない。未インストール [VERIFIED: import 失敗]。不採用 |
| カスタムプロンプト＝最優先（上書き） | プリセット＋ユーザー追記（合成） | 合成は既存挙動（上書き）を変え後方互換を壊すリスク。成功基準3 は「カスタムが引き続き機能」＝現行の上書き温存が最も安全 |

**Installation:**
```bash
# 新規インストールなし（標準ライブラリのみ）
```

**Version verification:** 本フェーズは新規パッケージを導入しないため、ecosystem registry 照会は不要。`tkinter`（Tk 8.6）と `re` は CPython 標準同梱。外部 Markdown ライブラリ 3 種が未インストールであることを確認済み [VERIFIED: ローカル `python -c` 実行]。

## Package Legitimacy Audit

> 本フェーズは外部パッケージを **一切インストールしない**（V14-D-01 新規 pip 依存ゼロ方針）。したがって legitimacy 監査の対象パッケージは存在しない。

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| （該当なし） | — | — | — | — | — | 新規依存なし |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V16-AI-01 | `OCRDialog` で `markdown` プリセット出力を整形表示し、プレーンテキストより見出し・箇条書き等を読みやすく提示する | 「Architecture Patterns: Pattern 1（`tk.Text` タグ描画）」「Don't Hand-Roll」「Validation Architecture」で実装手法・テスト方針を提示 |
| V16-AI-02 | プロバイダ別プロンプトテンプレート最適化（Claude=XML タグ構造 / Gemini=明示指示）。カスタムプロンプト機構（v1.5.0）と両立 | 「Architecture Patterns: Pattern 2（プロンプト解決純関数）」「Code Examples」「Common Pitfalls: Pitfall 3（カスタム両立）」で合成モデルと統合点を特定 |

## Architecture Patterns

### System Architecture Diagram

```
[ユーザーが OCR 実行 (_on_run)]
        │
        ├─ プロンプト解決（V16-AI-02 の挿入点）
        │     resolve_ocr_prompt(preset, provider_name, custom_prompt)  ← 新規純関数 (ocr.py)
        │        │  custom_prompt が非空 → custom をそのまま返す（上書き＝現行挙動温存）
        │        │  空 → PROVIDER_OCR_PROMPTS[provider_name][preset] を返す
        │        │       （未定義の provider/preset は汎用 OCR_PROMPTS にフォールバック）
        │        ▼
        │     self._ocr_prompt（文字列）
        │        ▼
        │  [ワーカースレッド] provider.ocr_image_ex(b64, self._ocr_prompt)
        │        ▼  ← Provider の _build_payload は prompt を受けるだけ（変更不要）
        │     Claude/Gemini/LMStudio/Tesseract API
        │        ▼
        │     results[page_idx] = text（raw Markdown 文字列・破棄せず保持）
        │
        ▼
[完了 → _render_results_ordered]（V16-AI-01 の挿入点）
        │
        ├─ preset == "markdown" かつ rendered モード？
        │     YES → md_render.parse_markdown(text) → [(line_kind, [(span_text, style)...]), ...]  ← 新規純関数 (md_render.py)
        │            → tk.Text.insert + tag_add で見出し/箇条書き/コード/強調をスタイリング
        │     NO  → 従来どおり text.insert("end", raw)  （後方互換）
        ▼
[コピー/保存 (_format_full_text)] ← raw テキストを返す（整形は表示のみ・出力は raw 維持）
```

### Recommended Project Structure
```
pagefolio/
├── md_render.py     # 新規: Markdown→(行種別, スタイル span) 変換の純関数群（Tk/fitz 非依存）
├── ocr.py           # 既存: OCR_PROMPTS に加え PROVIDER_OCR_PROMPTS + resolve_ocr_prompt() を追加
├── ocr_dialog.py    # 既存: _render_results_ordered に Markdown 描画分岐、_build に raw/rendered トグル、_on_run のプロンプト合成を resolve_ocr_prompt() へ
├── ocr_providers.py # 既存: 原則変更なし（プロンプト文字列を差し替えるだけで _build_payload は不変）
└── lang.py          # 既存: 新規 UI 文言（raw/rendered トグル等）を ja/en 両辞書に同一キーで追加
tests/
├── test_md_render.py    # 新規: parse_markdown の純関数テスト（Tk 不要）
└── test_provider_ui.py  # 既存に resolve_ocr_prompt のテストを追加（または test_ocr.py）
```

### Pattern 1: `tk.Text` タグによる Markdown 整形描画（純関数 + 薄い描画層）

**What:** Markdown 文字列を「行種別（見出し H1/H2、箇条書き、コードブロック、通常段落）」と「インライン span（強調 `**…**`、インラインコード `` `…` ``）」へ分解する **純関数**（`md_render.parse_markdown`）を作り、`OCRDialog` 側は変換結果を受けて `tag_configure`（スタイル定義）＋ `insert`＋`tag_add`（適用）するだけにする。
**When to use:** `preset == "markdown"` かつ rendered 表示モードのとき。それ以外（text/table プリセット、raw モード）は従来の素朴な `insert` を維持。
**Example:**
```python
# Source: docs.python.org/3/library/tkinter.html （tag_configure / tag_add）
# ── 描画層（ocr_dialog.py）: スタイル定義は _build で一度だけ ──
# テーマ色は C[] 経由（CLAUDE.md 規約・ハードコード禁止）
self.text.tag_configure("md_h1", font=self._font(4, "bold"), foreground=C["ACCENT"])
self.text.tag_configure("md_h2", font=self._font(2, "bold"), foreground=C["ACCENT"])
self.text.tag_configure("md_bullet", lmargin1=20, lmargin2=36)
self.text.tag_configure("md_code", font=("Consolas", self._font_size()), background=C["BG_PANEL"])
self.text.tag_configure("md_bold", font=self._font(-1, "bold"))

# ── 適用（_render_results_ordered から呼ぶ薄いメソッド）──
for kind, spans in parse_markdown(self.results[page_idx]):   # ← 純関数の戻り値
    start = self.text.index("end-1c")
    for span_text, inline_tag in spans:
        s = self.text.index("end-1c")
        self.text.insert("end", span_text)
        if inline_tag:
            self.text.tag_add(inline_tag, s, "end-1c")
    self.text.insert("end", "\n")
    if kind:                       # 行レベルタグ（md_h1 等）を行全体へ
        self.text.tag_add(kind, start, "end-1c")
```
**Note:** フォントサイズは `self._font(delta)` ヘルパー経由（CLAUDE.md「ハードコード禁止」）。コードブロックの等幅は `Consolas` を許容するが、`self._font_size()` でサイズは追従させる。

### Pattern 2: プロバイダ別プロンプトを純関数で解決（カスタム上書きを温存）

**What:** 現状の `_on_run`（`ocr_dialog.py:1085-1090`）にある「カスタム優先・なければプリセット」分岐を、`ocr.py` の純関数 `resolve_ocr_prompt(preset, provider_name, custom_prompt)` に切り出す。プロバイダ別テンプレートは `PROVIDER_OCR_PROMPTS: dict[str, dict[str, str]]`（provider→preset→文言）で定義し、未定義は汎用 `OCR_PROMPTS` へフォールバック。
**When to use:** `_on_run` のプロンプト確定箇所。`name = self.app.settings.get("ocr_provider", "")` は既にこの近傍で取得済み（`ocr_dialog.py:1120`）なので provider 名は容易に渡せる。
**Example:**
```python
# Source: 既存 ocr_dialog.py:1085-1090 を純関数化
# ── ocr.py（純ロジック層）──
PROVIDER_OCR_PROMPTS = {
    "claude": {
        # Claude は XML タグで構造を明示すると精度が上がる [ASSUMED]
        "markdown": (
            "<task>画像内の文書を Markdown で書き出す</task>\n"
            "<rules>見出し(#)・箇条書き(-)・表(|)を構造どおり使う。"
            "装飾的な前置きや説明文は出力しない。本文のみ。</rules>"
        ),
        # text / table も同様に XML タグ化
    },
    "gemini": {
        # Gemini は明示的・命令的な指示を好む [ASSUMED]
        "markdown": (
            "次の画像を OCR し、結果を Markdown 形式で出力してください。"
            "必ず見出し・リスト・表を元の構造どおりに再現し、"
            "前置き・後書き・コードフェンスは付けず本文のみを返してください。"
        ),
    },
    # lmstudio / tesseract は汎用プロンプトのまま（後述 Pitfall 4）
}

def resolve_ocr_prompt(preset, provider_name, custom_prompt=""):
    """OCR プロンプトを解決する純関数（Tk/ネットワーク非依存）。

    優先順位: custom_prompt（非空）> プロバイダ別テンプレート > 汎用プリセット。
    後方互換: custom_prompt 上書きは現行 _on_run 挙動を温存する（成功基準3）。
    """
    if custom_prompt:
        return custom_prompt
    by_provider = PROVIDER_OCR_PROMPTS.get(provider_name, {})
    if preset in by_provider:
        return by_provider[preset]
    return OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])
```

### Anti-Patterns to Avoid
- **`tk.Text` 描画ロジックを `OCRDialog` メソッド内にベタ書き:** Tk 非依存テストが書けず 582 件ベースラインに回帰を足せない。変換は必ず純関数（`md_render.py`）へ分離する（`pagination.py` 前例）。
- **`_build_payload` を provider ごとに改造してプロンプトを埋め込む:** プロンプトは「文字列」として Provider に渡る既存契約（`ocr_image(b64, prompt)`）を壊す。Provider 層は触らず、文字列だけ差し替える。
- **エクスポート（コピー/保存）を整形済みテキストにする:** `_format_full_text`（`ocr_dialog.py:1596`）は raw Markdown を返すべき。整形は「表示」だけ。タグはクリップボード/ファイルに乗らないので raw 維持が正しい。
- **カスタムプロンプトをプロバイダテンプレートと機械合成する:** 現行は「カスタムがあれば完全上書き」。合成すると既存ユーザーのカスタム文言の意図が壊れる。上書きを温存する。
- **`markdown` プリセット以外でも整形描画を走らせる:** text/table プリセットや LMStudio/Tesseract の素出力に Markdown パーサを当てると誤整形する。`preset == "markdown"` をガード条件にする。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| リッチテキスト描画（色・太字・字下げ） | スクロール付きカスタムキャンバス描画 | `tk.Text` の `tag_configure`/`tag_add`（既存 `self.text`） | 標準機能。折返し・スクロール・選択コピーが無料で付く [CITED: docs.python.org] |
| 完全な CommonMark 準拠パース | 全 Markdown 仕様の自前実装 | OCR が出す限定サブセット（見出し/箇条書き/表/強調/コード）だけ `re` で扱う | OCR 出力は限定的。完全準拠は過剰。ネストや脚注は範囲外 |
| プロンプト分岐の散在 | 各 Provider クラス内に if 分岐 | `resolve_ocr_prompt` 純関数 1 箇所に集約 | テスト可能・1 箇所変更。Provider 層は文字列を受けるだけの契約を維持 |
| 表（Markdown table）の桁揃え描画 | `tk.Text` 内での厳密な表レイアウト | 等幅タグ（`md_code`/`Consolas`）で行をそのまま表示 or 段階導入で表は raw 表示 | `tk.Text` は表セル整列に不向き。MVP では「読みやすさ」が満たせれば十分（成功基準1） |

**Key insight:** OCR 結果の Markdown は「人間が読みやすい程度の整形」が目的（成功基準1）であり、ブラウザ級の完全レンダリングは不要。`tk.Text` タグ＋限定サブセットパーサが「最小実装で読みやすさを満たす着地点」。

## Runtime State Inventory

> 本フェーズはコード加算（新規モジュール + 既存メソッドへの分岐追加）であり、rename/migration ではない。ただし設定キーの追加可能性があるため軽く点検する。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | なし（OCR 結果は永続化しない。M2「結果永続化」は本マイルストーン非選択・REQUIREMENTS.md L37） | none |
| Live service config | なし（外部サービス登録の string 変更なし） | none |
| OS-registered state | なし | none |
| Secrets/env vars | 既存の API キー（`ANTHROPIC_API_KEY`/`GEMINI_API_KEY`/`GOOGLE_API_KEY`）のみ。本フェーズで新規キーや名称変更なし。プロンプト文言に秘匿情報は含めない | none |
| Build artifacts | なし（新規 `md_render.py` は通常 import。PyInstaller spec は明示列挙でなくパッケージ取り込みのため追加対応不要だが、計画時に PageFolio.spec の hiddenimports を一応確認） | 計画時に PageFolio.spec を確認（おそらく不要） |

**新規に追加しうる設定キー:** raw/rendered の表示モードを永続化する場合のみ `ocr_render_mode`（例: `"raw"` / `"rendered"`）を `DEFAULT_SETTINGS` に追加（無害な設定値。`_SENSITIVE_KEYS` 対象外）。永続化不要ならセッション内 `tk.BooleanVar` のみで `setdefault` も不要。**この要否は discuss-phase で確定すべき（下記 Open Questions Q1）。**

## Common Pitfalls

### Pitfall 1: Tk 依存で描画ロジックを書きテスト不能になる
**What goes wrong:** `_render_results_ordered` に Markdown 整形を直書きすると、テストに Tk root が必要になる。だが本リポジトリのテストは Tk を一切生成しない [VERIFIED: tests/ 配下に `tk.Tk()`/`tkinter` import がゼロ]。結果、回帰テストが追加できず 582 件ベースラインを守れない。
**Why it happens:** UI と変換を 1 メソッドに混在させるため。
**How to avoid:** Markdown→構造データの変換を `md_render.parse_markdown`（純関数）に切り出し、`test_md_render.py` で戻り値（タプルのリスト）をアサートする。描画メソッドは「純関数の戻り値を `insert`/`tag_add` するだけ」に薄くする（`pagination.py` / `test_pagination.py` の前例に倣う）。
**Warning signs:** テストで `OCRDialog(...)` をインスタンス化しようとしている → 設計が間違っている合図。

### Pitfall 2: `markdown` 以外のプリセットや非対応プロバイダに整形を当てる
**What goes wrong:** text/table プリセットの素テキストや LMStudio/Tesseract の生出力に Markdown パーサを適用すると、`#` 始まりの行を誤って見出し化する等の誤整形。
**How to avoid:** 描画分岐の条件を `preset == "markdown"`（かつ rendered モード）に厳格化。table プリセットは Markdown テーブルだが「表整形描画」は MVP 範囲外（Don't Hand-Roll 参照）として raw 表示でもよい。
**Warning signs:** 通常テキスト OCR で行頭記号が勝手に装飾される。

### Pitfall 3: カスタムプロンプトの後方互換破壊（成功基準3）
**What goes wrong:** プロバイダ別テンプレート導入時に、既存ユーザーの `ocr_custom_prompt` が無視される／テンプレートと合成されて意図が変わる。
**Why it happens:** プロンプト解決の優先順位を変えてしまうため。現行は `if self.custom_prompt: 上書き`（`ocr_dialog.py:1086-1087`）。
**How to avoid:** `resolve_ocr_prompt` で **custom_prompt 非空 → そのまま return** を最優先に固定。プロバイダテンプレートは custom が空のときだけ効く。これを `test_..._custom_overrides_provider_template` で明示的に回帰テスト化する。
**Warning signs:** カスタムプロンプト設定済みなのに OCR 文言がテンプレートに変わる。

### Pitfall 4: LMStudio / Tesseract への波及
**What goes wrong:** Tesseract は `prompt` を **完全に無視する**（`ocr_providers.py:806` 「Tesseract では無視される」）。LMStudio は任意のローカルモデルでありプロンプト感度が不定。ここに Claude/Gemini 向けの XML/明示指示を当てても無意味〜逆効果。
**How to avoid:** `PROVIDER_OCR_PROMPTS` に `claude`/`gemini` のみ定義し、`lmstudio`/`tesseract`/`off` は **汎用 `OCR_PROMPTS` フォールバック**（`resolve_ocr_prompt` の既定動作）に任せる。Tesseract は文言が何であれ結果不変なので明示テンプレ不要。
**Warning signs:** Tesseract 経路のテストでプロンプト差が結果に影響する想定を書いてしまう（実際には無影響）。

### Pitfall 5: エクスポートにタグ/整形が漏れる
**What goes wrong:** 整形表示を導入した後、コピー/保存が「見た目」を反映しようとして壊れる、あるいは raw とずれる。
**How to avoid:** `_format_full_text`（`ocr_dialog.py:1596-1604`）は `self.results`（raw 文字列）を返す現行実装を維持。整形は表示専用。Markdown の raw こそ `.md` 保存に最適（`_save_to_file` は既に `.md` フィルタを持つ・`ocr_dialog.py:1621`）。
**Warning signs:** 保存した `.md` にタグ名や装飾文字が混入する。

### Pitfall 6: LANG キーの ja/en 非対称
**What goes wrong:** raw/rendered トグル等の新規 UI 文言を ja だけに足すと `test_lang_parity.py` が落ちる。
**How to avoid:** 新規キーは必ず ja（`lang.py:8` 起点）と en（`lang.py:456` 起点）の両方へ同一キーで追加（CLAUDE.md「LANG ルール」）。既存 preset キー（`ocr_preset_markdown` 等）は両辞書に揃っている [VERIFIED: grep で ja 282-284 行 / en 720-722 行に対応確認]。

## Code Examples

### 例: Markdown 限定サブセットの行種別パース（純関数・`md_render.py`）
```python
# Source: 新規実装（OCR が出す Markdown サブセットに限定）
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+)`")

def _split_inline(text):
    """1 行を [(span_text, inline_tag|None), ...] に分解する純関数。

    **bold** と `code` のみ扱う（OCR Markdown の現実的サブセット）。
    """
    spans, pos = [], 0
    # 簡易: bold を優先抽出（ネストは扱わない＝OCR 出力では稀）
    for m in _BOLD.finditer(text):
        if m.start() > pos:
            spans.append((text[pos:m.start()], None))
        spans.append((m.group(1), "md_bold"))
        pos = m.end()
    if pos < len(text):
        spans.append((text[pos:], None))
    return spans or [(text, None)]

def parse_markdown(md):
    """Markdown 文字列を [(line_kind, spans), ...] へ変換する純関数。

    line_kind: "md_h1"|"md_h2"|"md_bullet"|"md_code"|""（通常段落）。
    Tk/fitz 非依存。戻り値は test_md_render.py で直接アサートできる。
    """
    out = []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            out.append(("md_code", [(line, None)]))
        elif line.startswith("## "):
            out.append(("md_h2", [(line[3:], None)]))
        elif line.startswith("# "):
            out.append(("md_h1", [(line[2:], None)]))
        elif re.match(r"^\s*[-*]\s+", line):
            body = re.sub(r"^\s*[-*]\s+", "• ", line)
            out.append(("md_bullet", _split_inline(body)))
        else:
            out.append(("", _split_inline(line)))
    return out
```

### 例: 純関数テスト（Tk 不要・`test_md_render.py`）
```python
# Source: test_pagination.py / test_provider_ui.py のパターン
from pagefolio.md_render import parse_markdown

def test_h1_detected():
    assert parse_markdown("# Title")[0][0] == "md_h1"

def test_bullet_and_bold():
    kind, spans = parse_markdown("- **bold** item")[0]
    assert kind == "md_bullet"
    assert ("bold", "md_bold") in spans
```

### 例: プロンプト解決テスト（カスタム上書き温存・成功基準3）
```python
# Source: 既存 _on_run 挙動の純関数化を検証
from pagefolio.ocr import resolve_ocr_prompt, OCR_PROMPTS

def test_custom_overrides_provider_template():
    assert resolve_ocr_prompt("markdown", "claude", "MY CUSTOM") == "MY CUSTOM"

def test_lmstudio_falls_back_to_generic():
    assert resolve_ocr_prompt("text", "lmstudio", "") == OCR_PROMPTS["text"]

def test_claude_markdown_uses_provider_template():
    assert resolve_ocr_prompt("markdown", "claude", "") != OCR_PROMPTS["markdown"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 単一 `OCR_PROMPTS`（プリセットのみ） | プリセット × プロバイダの 2 軸解決（`resolve_ocr_prompt`） | 本フェーズ | Claude/Gemini で精度向上。LMStudio/Tesseract は汎用フォールバックで不変 |
| OCR 結果は素テキスト表示のみ | `markdown` プリセットを `tk.Text` タグで整形表示 | 本フェーズ | 読みやすさ向上（成功基準1）。raw/rendered 切替で原文も確認可能 |

**Deprecated/outdated:** なし。既存 API・データフローを破壊しない加算的拡張。

## Assumptions Log

> 以下は `[ASSUMED]`（本セッションで外部検証していない訓練知識）。discuss-phase でのユーザー確認、または実 API 検証（QUAL-03 で確立した「実機相当検証手順」に準拠）を推奨。

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Claude は XML タグ（`<task>`/`<rules>` 等）で指示を構造化すると OCR 精度・遵守率が上がる | Pattern 2 / Code Examples | 文言効果が薄い場合でも害はない（後方互換維持・カスタム上書き可）。精度向上が成功基準2の主眼のため、実画像での A/B 確認が望ましい |
| A2 | Gemini は明示的・命令的な指示文を好む | Pattern 2 / Code Examples | 同上。逆効果なら汎用プロンプトに戻すだけ |
| A3 | OCR が出力する Markdown は見出し/箇条書き/表/強調/コードの限定サブセットで実用上十分 | Don't Hand-Roll / Pattern 1 | ネスト箇条書き・脚注等が頻出すると整形が不完全に見える。MVP では「プレーンより読みやすい」を満たせば成功基準1は達成 |
| A4 | プロバイダ別テンプレートの具体文言（XML 構造/明示指示の最適形）はモデル世代で変わりうる | Pattern 2 | 文言は設定不要の定数なので変更が容易。実 API で最良文言を後追い調整可能 |

**確認手段の提案:** A1/A2/A4 は同一スキャン画像を Claude/Gemini で「汎用プロンプト vs プロバイダ別テンプレート」で実行し出力品質を目視比較する（QUAL-03 で記録した実 API 検証手順の再利用）。コスト確認ダイアログ（既存）が課金前ゲートとして機能する。

## Open Questions

1. **raw/rendered 切替 UI の要否と永続化**
   - What we know: 成功基準1は「整形表示で読みやすく」だが、原文（raw Markdown）確認手段の要否は要件に明記なし。`_save_to_file` は `.md` 保存に対応済み。
   - What's unclear: rendered 固定でよいか、raw/rendered トグルを設けるか。トグルを設けるなら設定永続化（`ocr_render_mode` 追加）するか、セッション内のみか。
   - Recommendation: 最小実装は「`markdown` プリセット時は rendered 表示、トグルは任意」。raw 確認はコピー/保存（raw 出力）で代替可能なため、まず rendered のみで成功基準1を満たし、トグルは discuss-phase でユーザー要望を確認。永続化するなら無害な設定値として `DEFAULT_SETTINGS` に追加。

2. **table プリセットの整形深度**
   - What we know: `table` プリセットは Markdown テーブルを出力するが、`tk.Text` は表セル整列が苦手。
   - What's unclear: 表を桁揃え描画するか、等幅 raw 表示で妥協するか。
   - Recommendation: MVP は等幅（`md_code` タグ相当）または raw 表示。桁揃えは過剰実装（Don't Hand-Roll）。成功基準1の主眼は `markdown` プリセットの見出し/箇条書き読みやすさ。

3. **プロバイダ別テンプレートを text/table プリセットにも用意するか**
   - What we know: 成功基準2の例示は「Claude=XML / Gemini=明示」。preset 単位の網羅は未指定。
   - Recommendation: まず全プリセット（text/table/markdown）に Claude/Gemini テンプレを用意するのが一貫的。ただし最小では `markdown` から着手し、未定義 preset は汎用フォールバックで安全に動く設計（`resolve_ocr_prompt`）なので段階導入可能。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `tkinter` / `tk.Text` タグ | V16-AI-01 整形描画 | ✓ | Tk 8.6 | — |
| `re`（標準） | Markdown サブセットパース | ✓ | 標準同梱 | — |
| `markdown` / `mistune` / `tkhtmlview`（外部） | （不採用の代替案） | ✗ | — | 標準ライブラリ実装で代替（採用方針）。導入は V14-D-01 違反のため行わない |

**Missing dependencies with no fallback:** なし（中核は全て標準ライブラリで充足）。
**Missing dependencies with fallback:** 外部 Markdown ライブラリ群は意図的に不採用。標準ライブラリ実装が正規方針。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2（+ pytest-cov 7.1.0） |
| Config file | pyproject.toml（`pythonpath`、`tests/**` で S101 除外） |
| Quick run command | `python -m pytest tests/test_md_render.py tests/test_provider_ui.py -x -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V16-AI-01 | Markdown 行種別（H1/H2/箇条書き/コード）を正しく分類 | unit | `python -m pytest tests/test_md_render.py -q` | ❌ Wave 0 |
| V16-AI-01 | インライン span（`**bold**`/`` `code` ``）を抽出 | unit | `python -m pytest tests/test_md_render.py -q` | ❌ Wave 0 |
| V16-AI-02 | `resolve_ocr_prompt` がプロバイダ別テンプレを返す | unit | `python -m pytest tests/test_provider_ui.py -q` | ✅（既存ファイルに追加） |
| V16-AI-02 / 成功基準3 | カスタムプロンプトが provider テンプレを上書きする | unit | `python -m pytest tests/test_provider_ui.py -q` | ✅（既存ファイルに追加） |
| V16-AI-02 | LMStudio/Tesseract は汎用プロンプトにフォールバック | unit | `python -m pytest tests/test_provider_ui.py -q` | ✅（既存ファイルに追加） |
| 回帰 | ja/en LANG キー対称性（新規文言追加時） | unit | `python -m pytest tests/test_lang_parity.py -q` | ✅ |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_md_render.py tests/test_provider_ui.py tests/test_lang_parity.py -x -q`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** フルスイート緑（現行 **582 件** ベースライン。ブリーフの「約490件」は更新前の数値）+ `ruff check . && ruff format .` 通過後に `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_md_render.py` — `parse_markdown` の行種別・インライン span を検証（V16-AI-01・新規）
- [ ] `tests/test_provider_ui.py` に `resolve_ocr_prompt` テスト群を追加（V16-AI-02・既存ファイル拡張）
- [ ] フレームワーク install: 不要（pytest 導入済み）

## Security Domain

> `security_enforcement: true`（config.json）・ASVS Level 1。本フェーズはローカル UI 文字列処理とプロンプト文言の追加が中心で、新規の認証・ネットワーク経路・秘匿情報の取り扱いは発生しない。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | API キー認証は既存（本フェーズ変更なし） |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | OCR 結果（外部 LLM 由来の文字列）を `tk.Text` に挿入する際、`insert` はプレーンテキスト扱いで HTML/コード実行はない。`re` パースは限定サブセットで ReDoS を避ける（`.+?`/`[^` `]+` の非貪欲・文字クラスで線形）。秘匿情報（API キー・抽出テキスト本文）はログ非出力の既存規約を維持（T-04-09/T-01-01） |
| V6 Cryptography | no | — |

### Known Threat Patterns for Tkinter + LLM 出力描画

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM 出力に制御文字/巨大行が混入し UI が固まる | Denial of Service | 行単位処理・`tk.Text` は大量テキストに耐性。必要なら行数上限は既存の `see("end")` 同様にスクロール委譲 |
| `re` の病的入力で ReDoS | Denial of Service | 非貪欲＋文字クラスで線形時間のパターンに限定（ネスト量指定子を使わない） |
| プロンプト文言や OCR 本文の意図せぬログ露出 | Information Disclosure | 既存規約踏襲: 抽出テキスト本体・プロンプト・キー値はログに出さない（`has_embedded_text`/`_sync_param_vars_from_settings` の前例） |

## Project Constraints (from CLAUDE.md)

| 制約 | 本フェーズへの適用 |
|------|------------------|
| 新規 pip 依存ゼロ（V14-D-01） | 外部 Markdown ライブラリ不採用。`tk.Text` タグ + `re` の標準ライブラリのみ |
| テーマ色は `C[]` 参照（ハードコード禁止） | `tag_configure` の foreground/background は `C["ACCENT"]`/`C["BG_PANEL"]` 等を使用 |
| フォントは `self._font(delta)` ヘルパー | 見出しタグの font も `self._font(4,"bold")` 等で生成（直値禁止） |
| LANG は ja/en 両辞書に同一キー | 新規 UI 文言は両方へ追加（`test_lang_parity.py` で担保） |
| 裸 `except:` 禁止・`except Exception as e:` | パース/描画の例外捕捉は型指定（`tk.TclError`/`ValueError` 等） |
| `# type: ignore` 無断使用禁止 | 使用しない |
| `pyproject.toml` 編集禁止 | 触らない |
| `ruff check . && ruff format .` + `pytest` 必須 | 全タスクで実行。E/F/W/I/S/B ルール準拠 |
| 純関数集約パターン（`pagination.py` 前例） | `md_render.py`（変換）と `resolve_ocr_prompt`（プロンプト）を Tk 非依存純関数に集約 |
| バージョン方針 | `APP_VERSION` は既に `v1.7.0` [VERIFIED: constants.py:12]。中間フェーズはバンプしない（MEMORY: current-milestone-ships-at-v170）。本フェーズは v1.6.0 ロードマップの最終フェーズだが、**出荷バンプはマイルストーン完了時（complete-milestone）に実施**。計画では `APP_VERSION` を変更しない。開発履歴.md への追記は実施 |

## Sources

### Primary (HIGH confidence)
- 実コード（本セッションで全読）: `pagefolio/ocr_dialog.py`（OCRDialog 全体・`_render_results_ordered`/`_on_run`/`_format_full_text`）、`pagefolio/ocr.py`（`OCR_PROMPTS`/`build_provider`/純ユーティリティ）、`pagefolio/ocr_providers.py`（4 Provider の `_build_payload`/`ocr_image_ex`）、`pagefolio/dialogs/llm_config.py`（カスタムプロンプト `ocr_custom_prompt` のデータフロー）、`pagefolio/pagination.py`（純関数集約パターン）
- 環境検証: `python -c "import tkinter"` → Tk 8.6 / 外部 md ライブラリ 3 種 import 失敗 [VERIFIED]
- `tests/`（582 件・Tk 非生成方針 [VERIFIED: grep でゼロ]）、`tests/test_provider_ui.py`/`test_pagination.py`（純関数テスト前例）
- `.planning/REQUIREMENTS.md` / `.planning/STATE.md` / `CLAUDE.md` / `.planning/config.json`

### Secondary (MEDIUM confidence)
- `tk.Text` の `tag_configure`/`tag_add` 仕様（標準ライブラリ既知 API）[CITED: docs.python.org/3/library/tkinter.html]

### Tertiary (LOW confidence)
- Claude=XML 構造 / Gemini=明示指示 が OCR 出力品質を高める、という文言設計（[ASSUMED] A1/A2/A4 — 実 API での A/B 検証推奨）

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 標準ライブラリのみ・外部依存ゼロを環境で実証
- Architecture: HIGH — 既存コードの挿入点（`_render_results_ordered`/`_on_run`/`resolve` 化）を行番号レベルで特定。`pagination.py` 純関数パターンが確立済み
- Pitfalls: HIGH — Tk 非依存テスト方針・カスタム上書き温存・Tesseract プロンプト無視は実コードで確認
- プロンプト文言の効果: LOW — A1/A2/A4 は未検証（[ASSUMED]）。実 API 比較で確定すべき

**Research date:** 2026-06-19
**Valid until:** 2026-07-19（標準ライブラリ中心で安定。プロバイダ別プロンプト最適化のベストプラクティス文言のみモデル世代で陳腐化しうる）
