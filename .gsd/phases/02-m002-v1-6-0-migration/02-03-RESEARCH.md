# Phase 3: 体感品質・回転プレビュー & OCR 堅牢性（プランA） - Research

**Researched:** 2026-06-19
**Domain:** Tkinter Canvas 即時再描画（PyMuPDF 回転）＋ OCR プロバイダ堅牢性（途切れ検出・待機 UX・キー秘匿監査・検証手順）
**Confidence:** HIGH（コード経路・PyMuPDF 挙動・既存テスト網羅状況をいずれも実測で確認）

## Summary

本フェーズは性質の異なる 4 要件（V16-QUAL-01〜04）を「体感品質・堅牢性」で束ねる。調査の結論は要件ごとに明確に分かれる:

- **V16-QUAL-01（H1 回転即時反映）**: PyMuPDF の `set_rotation` → `get_pixmap` は**回転を即時反映する**ことを実機で検証済み（90/270° で pixmap の width/height が入替わる）。`_render_preview_pixmap` も単体で回転後ページを正しく反映する。よって**バグは pixmap 描画層ではなく Tk Canvas 層またはセレクション意味論にある**。最有力仮説は (a) 回転対象 `targets` が `current_page` を含まないケースでプレビューが変わらない「仕様上の体感バグ」、(b) 回転で w/h が変わった際の Canvas scrollregion/スクロール位置・viewport の更新タイミング。修正は描画経路の追加ではなく原因除去であり、planner は**実機 GUI で再現条件を特定する debug/spike タスクを先頭に置くべき**。
- **V16-QUAL-04（M1 エラー UX）**: Claude `ocr_image` は `stop_reason` を、Gemini は `finishReason` を**全く検査していない**ことを確認（途切れ検出は完全に net-new）。レスポンス JSON 抽出箇所の隣に検査を追加し、途切れフラグをテキストと併せて表示層へ伝搬する。待機秒数表示（D-06）は OCRDialog `_worker`（1303-1343）の待機文言生成箇所に `delay` を渡すが、**現状 `delay` は文言生成より後で計算される**ため順序入替が必要。
- **V16-QUAL-03（H5 max_tokens/429 検証）**: max_tokens **クランプは実在し（`build_provider` の `mt = 4096 if mt <= 0 else mt`）、`TestBuildProviderMaxTokensClamp` で網羅テスト済み**。429/Retry-After/指数バックオフ/サーキットブレーカーも実装＆テスト済み。自動テストのギャップはほぼ無く、**主成果物は実 API 検証チェックリスト文書（D-08）**。net-new な自動テストは途切れ検出（D-05）に付随する分のみで足りる見込み。
- **V16-QUAL-02（H2 キー秘匿監査）**: 設定ファイル経路は `test_settings_keyguard.py` で手厚い。ギャップは (1) **ログ平文露出の caplog 回帰テスト**、(2) **ソース埋め込みの pytest 自動スキャン**、(3) **3 経路監査チェックリスト文書**。`_save_settings` はキー名のみログ・値非出力を既に実装済み（line 89-91）なので、caplog テストは「値が出ないこと」のアサートで担保できる。

**Primary recommendation:** H1 は「描画追加」ではなく「実機再現→原因特定→最小修正」。OCR 系 3 要件（M1/H5/H2）は H1 と独立に並行プラン化可能。H5 は自動テストでなく**実 API 検証手順書**が主成果物。

## User Constraints (from CONTEXT.md)

### Locked Decisions

**H1 回転プレビュー即時反映（V16-QUAL-01）**
- **D-01:** 現状は即時反映されないバグがある（ユーザー実機確認）。`_rotate_selected` は `_invalidate_thumb_cache(targets)` → `_refresh_all()`（→ `_show_preview` で `get_pixmap` 再描画）を呼んでいるのに即時反映されない。**原因のトレースと修正が H1 の中核**。
- **D-02:** 即時反映の対象はプレビュー（現在ページ）＋回転した選択中の全サムネイル両方。`thumb_cache` は `targets` で無効化済みのためサムネイル側はキャッシュ無効化＋再描画が効く前提。
- **D-03:** 担保は「検証可能な単位テスト＋手動 UAT」。`_render_preview_pixmap` が回転後の page を反映する（90/270° で width/height 入替）ことをテストし、最終的な見た目反映は手順書/UAT で目視確認。

**M1 エラーハンドリング UX（V16-QUAL-04）**
- **D-04:** エラー/警告は既存のパネル内提示（OCRDialog の結果欄・進捗ラベル）を強化する。messagebox 能動通知は採らない。
- **D-05:** トークン超過による応答途切れを検出して専用文言＋次アクションを提示。`stop_reason`（Claude）/`finishReason`（Gemini）を検査し当該ページに専用 LANG 文言（ja/en 同一キー）を出す。**部分テキストは保持**。
- **D-06:** レート制限待機中の表示に待ち時間を併記。「約 N 秒待機」（Retry-After/バックオフ秒数・`RETRY_AFTER_CAP=60s` クランプ済の実待機値）を加える。

**H5 max_tokens クランプ・429 リトライ検証（V16-QUAL-03）**
- **D-07:** 検証は「実機相当の手順書中心」。実 API 常時叩きは採らない。クランプ/リトライはユニット/統合テストで自動担保、実 API 検証は手順書＋チェックリストでユーザー任意実行・結果記録。
- **D-08:** 検証手順書はフェーズ内（`.planning/phases/03-ocr-a/`）にチェックリスト形式で 1 ファイル作成。GSD 検証フローと整合。開発履歴.md やテスト docstring には集約しない。
- **D-09:** 追加自動テストはギャップのみ。`clamp_retry_after`・サーキットブレーカー・指数バックオフ・Retry-After 優先は既にテスト済みのため重複させない。まず max_tokens「クランプ」の実在を確認し、未テストの振る舞いのみ追加。

**H2 API キー秘匿監査（V16-QUAL-02）**
- **D-10:** 証跡は「回帰テスト＋監査チェックリスト文書」の両立。設定ファイル経路は既に手厚いため、ギャップであるログ平文露出とソース埋め込みを回帰テスト化し、3 経路（設定/ソース/ログ）の監査チェックリスト文書を残す。
- **D-11:** ログ非出力は caplog ベースの回帰テストで担保。主要経路（`_save_settings`・各プロバイダ・`_resolve_api_key`・セッションキー入力）でログにキー値が出ないことをアサート。
- **D-12:** ソース埋め込み防止は自動スキャンテストで担保。キーらしいパターン（`sk-ant-`・`AIza`・長い base64）が無いことを pytest でアサート。テストフィクスチャ除外設計は裁量。

### Claude's Discretion
- D-06 の待機秒数の表示文言・桁丸め（「約 5 秒」「5s」等）は LANG 規約（ja/en 同一キー）に従い実装裁量。
- D-09 のモック 429/トークン超過統合ケースを「追加する/既存で足りる」の最終判断は、max_tokens クランプ実在確認の結果を見て researcher/planner が決めてよい。→ **本調査の結論: クランプは実在＆網羅テスト済み。net-new な統合ケースは途切れ検出（D-05）テストに付随する分で足り、429×トークン超過の追加統合ケースは不要**。
- D-11 の caplog テストでカバーする具体的な関数/モジュールの粒度は実装裁量（最低限 `_save_settings` と全クラウドプロバイダを含む）。
- D-12 の検出パターン・除外（テストフィクスチャ/ダミーキー）の実装方式は裁量。「実キーがソースに無いことを CI で再発防止できる」ことは必須。
- 検証手順書（D-08）のファイル名・章立ては GSD 慣習に合わせて裁量。

### Deferred Ideas (OUT OF SCOPE)
- エラーの messagebox 能動通知（→ パネル内提示の強化を採用 D-04）。
- トークン超過途切れの自動 max_tokens 引き上げ再試行（→ 検出＋ユーザー案内のみ）。
- 実 API 検証の CI 自動化（→ 手順書＋手動実行に留める D-07）。
- OCR 出力の Markdown 整形・プロバイダ別プロンプト最適化（→ Phase 4 プランC）。
- 新ページ操作・新 OCR プロバイダ・実 API 常時 CI 化。

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V16-QUAL-01 | ページ回転をプレビューに即時反映 | PyMuPDF 回転即時反映を実測検証（Pitfall 1）。バグは Canvas 層/セレクション意味論に局在。`tests/test_viewer.py` の `_make_stub` パターンが回転テストの土台。 |
| V16-QUAL-02 | API キー秘匿（設定/ソース/ログ）監査・回帰テスト | `test_settings_keyguard.py` が設定経路を担保済み。`_save_settings` は値非出力（line 89-91）。ギャップ=caplog ログテスト＋ソース自動スキャン＋監査文書。 |
| V16-QUAL-03 | max_tokens クランプ・429 リトライ検証・記録 | クランプ実在（`ocr.py` 530/547）＆`TestBuildProviderMaxTokensClamp` 網羅。主成果物=実 API 検証チェックリスト文書（D-08）。 |
| V16-QUAL-04 | レート制限/トークン超過/途切れ時のエラー UX | Claude=`stop_reason` 未検査・Gemini=`finishReason` 未検査（net-new 検出）。待機秒数は `_worker` で `delay` を文言へ渡す（順序入替必要）。 |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 回転プレビュー即時反映（H1） | Viewer（Tk Canvas 描画） | PageOps（回転適用） | pixmap は正しい。問題は Canvas 再描画/scrollregion/viewport。viewer.py に閉じる。 |
| 回転サムネイル即時反映（H1） | Viewer（thumb_cache + `_build_thumbnails`） | — | キャッシュ無効化は実装済み。窓内に見えるサムネイルのみ再描画される点に留意。 |
| 途切れ検出（D-05） | Provider 層（`ocr_image` レスポンス解析） | OCRDialog 表示層 | `stop_reason`/`finishReason` は API レスポンス JSON にのみ存在。検出はプロバイダ層、提示は表示層。 |
| 待機秒数表示（D-06） | OCRDialog `_worker`（実待機計算） | lang.py（文言） | 実待機値は `clamp_retry_after(raw_delay)` の結果。文言生成は同じワーカーループ内。 |
| max_tokens クランプ（H5） | `build_provider`（ocr.py） | — | 実装済み・テスト済み。検証のみ。 |
| 429/リトライ堅牢化（H5） | `run_parallel` / `_worker` 待機ループ | OCRProvider（OCRRetryableError 送出） | 実装済み・テスト済み。検証のみ。 |
| キー秘匿（H2） | settings（`_SENSITIVE_KEYS`）＋全プロバイダ | テスト層（caplog/source scan） | 設定経路は担保済み。ログ/ソースは横断テストで担保。 |

## Standard Stack

### Core（既存・新規 pip 依存ゼロ）
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | 1.27.2.x | ページ回転・pixmap レンダリング | `set_rotation`/`get_pixmap` は回転を即時反映（実測検証済み） [VERIFIED: ローカル実行] |
| Tkinter | 標準ライブラリ | Canvas プレビュー・サムネイル描画 | 既存 UI フレームワーク [CITED: CLAUDE.md] |
| pytest | 9.0.2 | 回帰テスト（caplog・ソーススキャン含む） | 既存テストランナー・`caplog` フィクスチャ標準提供 [VERIFIED: ローカル実行] |
| logging | 標準ライブラリ | キー秘匿監査の caplog 対象 | 既存ログ基盤 [CITED: CLAUDE.md] |

**Installation:** 新規依存なし（V14-D-01 新規 pip 依存ゼロ方針を継続）。

**Version verification:**
```bash
python -c "import fitz; print(fitz.VersionBind)"   # → 1.27.2.3 [VERIFIED]
python -m pytest --version                          # → pytest 9.0.2 [CITED: CLAUDE.md]
```

## Package Legitimacy Audit

本フェーズは**外部パッケージを一切追加しない**（標準ライブラリ＋既存固定依存のみ）。
新規 install なし → Package Legitimacy Gate 適用対象外。

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[H1 回転即時反映]
  rotate ボタン / キーバインド
        │ _rotate_selected(deg)  (page_ops.py 80-91)
        ▼
  page.set_rotation((rotation+deg)%360)   ← pixmap は即反映（検証済）
        │ _invalidate_thumb_cache(targets)
        ▼
  _refresh_all()  (viewer.py 218-252)
        │ reconcile_window_start で窓正規化（Phase 2）
        ├──► _build_thumbnails()  → render_next 連鎖 → _get_thumb_photo（キャッシュ再生成）
        └──► _show_preview()  (viewer.py 61-115・同期・_preview_gen 非使用)
                  │ _render_preview_pixmap(current_page, zoom)  ← 回転反映 OK
                  ▼
             Canvas: delete("all") → create_image → configure(scrollregion)
                  ▲
                  └── ★疑い: targets が current_page を含まない / scrollregion・スクロール位置

[M1 途切れ検出 + 待機 UX]
  provider.ocr_image(b64, prompt)  (ocr_providers.py)
        │ HTTP 200 → JSON parse
        │   ★Claude: result["content"][].text を結合するが stop_reason 未検査
        │   ★Gemini: candidates[0].parts[].text を結合するが finishReason 未検査
        ▼ (text[, truncated?])
  OCRDialog._worker  (ocr_dialog.py 1267-1395)
        │ OCRRetryableError → 待機文言（1319-1328） + delay 計算（1342・★順序が逆）
        ▼
  progress_var / text ウィジェット（パネル内提示）

[H5 検証] build_provider クランプ（実在）+ run_parallel/_worker 待機（実在）→ 実 API 手順書で目視確認
[H2 監査] settings(_SENSITIVE_KEYS) → caplog テスト + source scan テスト + 監査チェックリスト
```

### Pattern 1: 回転反映テストは `_make_stub` 純関数パターンを流用
**What:** `tests/test_viewer.py::_make_stub(doc)` は `types.SimpleNamespace(doc=doc)` に `_render_preview_pixmap` をバインドし Tk root 不要で呼べる。
**When to use:** D-03 の回転単体テスト（90/270° で w/h 入替）。
**Example:**
```python
# Source: tests/test_viewer.py（既存・実測で回転反映を確認）
import types, fitz
from pagefolio.viewer import ViewerMixin

def test_rotation_swaps_dimensions():
    doc = fitz.open(); doc.new_page(width=400, height=600)
    stub = types.SimpleNamespace(doc=doc)
    stub._render_preview_pixmap = ViewerMixin._render_preview_pixmap.__get__(stub)
    _, w0, h0 = stub._render_preview_pixmap(0, 1.0)   # 600 900（zoom*1.5）
    doc[0].set_rotation(90)
    _, w1, h1 = stub._render_preview_pixmap(0, 1.0)   # 900 600
    assert (w1, h1) == (h0, w0)   # [VERIFIED: ローカル実行で 600x900 → 900x600 確認]
```

### Pattern 2: 途切れ検出はレスポンス抽出箇所の隣で stop_reason/finishReason を読む
**What:** プロバイダの JSON 解析直後に終了理由を判定し、テキストと共に表示層へ運ぶ。
**When to use:** D-05。
**Example:**
```python
# Claude（ocr_providers.py 386-395 の隣・Source: 公式 docs）
result = json.loads(body)
texts = [b.get("text") for b in result.get("content", [])
         if b.get("type") == "text" and b.get("text")]
truncated = result.get("stop_reason") == "max_tokens"   # [CITED: docs.anthropic.com]
# 部分テキストは保持して返す（D-05）

# Gemini（ocr_providers.py 518-526 _parse_response の隣・Source: 公式 docs）
cand = body.get("candidates", [{}])[0]
truncated = cand.get("finishReason") == "MAX_TOKENS"    # [CITED: ai.google.dev]
```
**伝搬設計（要 planner 決定・既存契約との両立）:** `ocr_image` は現在 `str` を返す純粋契約。途切れ情報の運び方は 2 択:
1. **戻り値拡張**（`(text, truncated)` タプル）→ `run_parallel`/`_worker`/`run_with_bounded_buffer` の全呼び出し箇所を改修。後方互換のため `tests/test_ocr_providers.py` の `ocr_image` 戻り値アサートも要更新。
2. **属性/サイドチャネル**（例: provider 側で最後の `last_truncated` を持つ、または専用例外を成功時に投げない）→ 並列実行ではスレッド競合リスク。
→ **推奨は (1) 戻り値拡張**。ただし「部分テキスト保持」と「既存テストの戻り値アサート」を壊さないよう、`OCRProvider.ocr_image` の戻り値型を `str | tuple[str, bool]` として段階導入するか、新メソッド `ocr_image_ex` を足すかは planner 判断。**この選択は plan 前に discuss/locked decision 化が望ましい（[ASSUMED] A1）**。

### Pattern 3: 待機秒数表示は delay 計算を文言生成の前へ
**What:** `_worker` の現状（1303-1343）は待機文言を 1319-1328 で set し、`delay` を 1342 で計算する。D-06 は文言に実待機秒数を含めるため**順序を入替**えて `delay` を先に算出し文言へ渡す。
**Example:**
```python
# Source: ocr_dialog.py _worker（要改修・順序入替）
raw_delay = e.retry_after if e.retry_after is not None else 1.0 * (2 ** (attempt - 1))
delay = clamp_retry_after(raw_delay)          # ← 先に計算
wait_key = self._retry_wait_key(e)
self.after(0, lambda p=page_idx, _n=attempt, _k=wait_key, _d=delay:
    self.progress_var.set(self._L[_k].format(page=p+1, n=_n, max=MAX_RETRIES, sec=round(_d))))
interruptible_sleep(delay, self._cancel_flag.is_set)
```
**注意:** `ocr_waiting_retry`/`ocr_waiting_retry_server` の `.format()` 呼び出しは ocr_dialog.py（1321-1325）と ocr.py `run_parallel`（435 は `waiting/{attempt}` 形式で別経路）の両方にある。`{sec}` プレースホルダ追加時は**両方の `.format` 引数と ja/en 両辞書**を同時更新しないと `KeyError`/`IndexError` になる（Pitfall 3）。

### Pattern 4: caplog によるキー値非出力テスト
**What:** pytest 標準 `caplog` フィクスチャで全ハンドラのログレコードを捕捉し、キー値が現れないことをアサート。
**Example:**
```python
# Source: pytest 公式（caplog フィクスチャ）
def test_save_settings_does_not_log_key_value(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("pagefolio.settings._get_settings_path", lambda: str(tmp_path/"s.json"))
    import logging
    with caplog.at_level(logging.DEBUG):
        _save_settings({"theme": "dark", "claude_api_key": "sk-ant-LEAK-XYZ"})
    assert "sk-ant-LEAK-XYZ" not in caplog.text   # 値が出ない（key 名のみ・line 89-91）
```
**注意:** `_save_settings` はキー**名**を `logger.error` で出すため、テストは「キー名が出る」を許容し「キー**値**が出ない」のみをアサートすること（Pitfall 4）。

### Pattern 5: ソース埋め込み自動スキャン
**What:** `pagefolio/` 配下の .py を走査し、実キーパターン（`sk-ant-[A-Za-z0-9_-]{20,}` 等）が無いことをアサート。テストフィクスチャ（`tests/`）と既存の安全文字列は除外。
**Example:**
```python
# Source: D-12 設計（パターン・除外は実装裁量）
import re, pathlib
PATTERNS = [re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
            re.compile(r"AIza[A-Za-z0-9_-]{30,}")]
def test_no_real_api_keys_in_source():
    for p in pathlib.Path("pagefolio").rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        for pat in PATTERNS:
            assert not pat.search(text), f"疑わしいキーが {p} に存在"
```
**注意:** プレースホルダ（`sk-ant-secret-should-not-appear`・`AIza-gemini-secret` 等は `tests/` 内のダミー）を誤検知しないよう、スキャン対象を `pagefolio/` に限定し閾値長を実キー長（sk-ant は実際 100 字超）に設定する（Pitfall 5）。

### Anti-Patterns to Avoid
- **H1 を「描画を追加」で直そうとする**: 描画は既に呼ばれている（D-01）。原因除去であり追加ではない。まず実機再現で原因を特定せよ。
- **`_preview_gen` ガードを `_show_preview` に新規追加する**: `_show_preview` は同期で世代ガードを使っていない。安易に追加すると Phase 2 の窓正規化や既存タイミングを壊す。
- **`stop_reason` 検出を例外送出で実装する**: 途切れは成功（部分テキストあり）なので例外にすると部分テキストを失う（D-05「部分保持」違反）。
- **LANG 文言に `{sec}` を片方の辞書だけ追加**: ja/en 同時更新必須（290/290 のキー数一致が回帰テスト対象になりうる）。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 回転反映 | 独自の Matrix.preRotate 計算 | `page.set_rotation()` + `get_pixmap()` | PyMuPDF が回転を pixmap へ自動反映（検証済）。手動 preRotate は cropbox/mediabox との整合が崩れる。 |
| 待機ループ | 独自 sleep + キャンセル監視 | `interruptible_sleep` / `clamp_retry_after`（既存） | 既に 0.5s 刻みキャンセル確認・60s クランプ実装＆テスト済み。 |
| max_tokens クランプ | 各プロバイダで個別クランプ | `build_provider` の集約クランプ（既存） | 既に `mt = 4096 if mt <= 0 else mt` で一元化＆網羅テスト済み。 |
| ログ捕捉テスト | カスタム LogHandler | pytest `caplog` フィクスチャ | 標準提供・全ハンドラ捕捉・`caplog.text` で全文検索可。 |
| ja/en キー整合 | 目視チェック | `set(LANG['ja']) == set(LANG['en'])` テスト | 現状 290/290 一致。1 行で構造的に担保。 |

**Key insight:** 本フェーズの堅牢化ロジック（クランプ・バックオフ・サーキットブレーカー・キーガード）は**ほぼ全て実装済み＆テスト済み**。新規実装が必要なのは (a) H1 原因除去、(b) 途切れ検出（D-05）、(c) 待機秒数文言（D-06）、(d) ログ/ソース監査テスト（D-11/D-12）の 4 点のみ。それ以外は「検証」に徹する。

## Runtime State Inventory

> 本フェーズは rename/migration ではなくバグ修正・テスト追加・文言追加が中心。永続状態への破壊的変更は無いが、設定キーと LANG キーの追加が発生するため確認する。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `pagefolio_settings.json`: 既存キーの変更なし。`ocr_max_tokens` 既定 -1 据え置き。 | なし |
| Live service config | なし（外部サービス登録なし。OCR は実行時 API 呼び出しのみ） | なし |
| OS-registered state | なし | なし |
| Secrets/env vars | `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` を**読み取りのみ**（`_resolve_api_key` os.environ.get）。本フェーズはキー名変更なし・読取専用維持。 | なし（監査で読取専用を再確認するのみ） |
| Build artifacts | なし（pyproject.toml 編集禁止・新規パッケージなし） | なし |

**新規追加で注意が必要なもの（永続状態ではないが整合必須）:**
- **LANG キー追加（D-05 途切れ文言・D-06 待機秒数 `{sec}`）**: ja/en 両辞書に同一キーで追加（現状 290/290）。
- **既存 LANG `.format()` 呼び出し箇所の引数追加**: `ocr_waiting_retry`/`ocr_waiting_retry_server` に `{sec}` を足すなら ocr_dialog.py の `.format(page=, n=, max=)` を `.format(page=, n=, max=, sec=)` へ全箇所更新。

## Common Pitfalls

### Pitfall 1: H1 を pixmap 描画バグと誤認する
**What goes wrong:** `_render_preview_pixmap`/`get_pixmap` を疑って時間を浪費する。
**Why it happens:** 「回転がプレビューに出ない」という症状から描画層を疑うのが自然。
**How to avoid:** **実測済み: PyMuPDF は回転を即時反映する**（400×600 → 90° → 600×400、`_render_preview_pixmap` も 600×900 → 900×600）。原因は Tk Canvas 層かセレクション意味論（`targets` が `current_page` を含まない）。**実機 GUI 再現を先頭タスクにし、(a) 選択なしで現在ページ回転 / (b) 別ページを選択して回転 / (c) スクロール位置を変えて回転 の 3 条件で切り分ける**。
**Warning signs:** 「pixmap の w/h は正しいのに見た目が変わらない」=描画は成功・viewport/scroll/anchor 問題。
**Historical context:** commit `f63d975`（2026-05）で**同一症状**（回転がプレビューに反映されない）が「プレビューがディスクファイルを再読込していた」ことに起因して発生し修正済み。現在のコードはメモリ直読み（`self.doc[page_idx]`）なのでこの原因は再発しない。別原因であることに留意。

### Pitfall 2: 途切れ検出を例外化して部分テキストを失う
**What goes wrong:** `stop_reason == "max_tokens"` を `RuntimeError` 等にすると、せっかく取れた部分テキストが errors 行きになり破棄される。
**How to avoid:** 途切れは「成功＋警告」。テキストは `results` に保持し、途切れフラグだけ別途運んで当該ページに注記を併記する（D-05「部分保持」必達）。

### Pitfall 3: LANG `.format()` 引数と辞書の不整合
**What goes wrong:** `{sec}` を文言に足したが `.format()` 呼び出しに `sec=` を渡し忘れる → `KeyError`。逆に呼び出しだけ更新して文言に `{sec}` が無い → 引数は無視されるが ja/en 非対称になる。
**How to avoid:** 文言（lang.py ja/en 両方）と全 `.format()` 呼び出し箇所（ocr_dialog.py。`run_parallel` の `waiting/{attempt}` は別経路なので影響範囲を確認）を**同一コミットで**更新。ja/en キー一致テストとプレースホルダ整合を回帰で担保。

### Pitfall 4: caplog テストでキー名出力を誤判定
**What goes wrong:** `_save_settings` はキー**名**（`claude_api_key`）を `logger.error` で出すため、「キー名が出ないこと」をアサートするとテストが落ちる。
**How to avoid:** アサートは「キー**値**（`sk-ant-...`）が `caplog.text` に出ないこと」のみ。キー名出力は仕様（line 89-91）。

### Pitfall 5: ソーススキャンの誤検知・スコープ過大
**What goes wrong:** `tests/` 内のダミーキー（`sk-ant-secret-should-not-appear`・`AIza-gemini-secret`）を実キーと誤検知、または閾値長が短すぎて偽陽性。
**How to avoid:** スキャン対象を `pagefolio/` に限定し、`tests/` を除外。実キー長（sk-ant は 100 字超、AIza は 39 字）に近い閾値で正規表現を設計。

### Pitfall 6: Phase 2 窓正規化との相互作用
**What goes wrong:** 回転後 `_refresh_all` が `reconcile_window_start` で窓を動かし、サムネイル即時反映の対象が「現在の窓内に見えるサムネイルのみ」になる。窓外の選択ページは（見えていないので）再描画されない。
**Why it happens:** Phase 2 で `_build_thumbnails` は `window_bounds` 範囲のみ描画する設計。
**How to avoid:** D-02「回転した選択中の全サムネイル」は**窓内に見えている範囲**に限り即時反映される、と UAT/手順書に明記。回転は `current_page` を動かさないため窓追従への影響は小さい（CONTEXT code_context 通り）。

## Code Examples

### 回転反映の単体テスト（D-03）
```python
# Source: tests/test_viewer.py パターン拡張（VERIFIED: ローカル実行）
import types, fitz
from pagefolio.viewer import ViewerMixin

def _stub(doc):
    s = types.SimpleNamespace(doc=doc)
    s._render_preview_pixmap = ViewerMixin._render_preview_pixmap.__get__(s)
    return s

def test_rotate_90_swaps_wh():
    doc = fitz.open(); doc.new_page(width=400, height=600)
    s = _stub(doc)
    _, w0, h0 = s._render_preview_pixmap(0, 1.0)
    doc[0].set_rotation(90)
    _, w1, h1 = s._render_preview_pixmap(0, 1.0)
    assert (w1, h1) == (h0, w0)

def test_rotate_180_keeps_wh():
    doc = fitz.open(); doc.new_page(width=400, height=600)
    s = _stub(doc)
    _, w0, h0 = s._render_preview_pixmap(0, 1.0)
    doc[0].set_rotation(180)
    _, w1, h1 = s._render_preview_pixmap(0, 1.0)
    assert (w1, h1) == (w0, h0)
```

### 途切れ検出の最小実装（Claude・D-05）
```python
# Source: ocr_providers.py 386-395 改修（CITED: docs.anthropic.com Messages API）
result = json.loads(body)
texts = [b.get("text") for b in result.get("content", [])
         if b.get("type") == "text" and b.get("text")]
if not texts:
    raise RuntimeError(f"Unexpected response format: {body[:500]}")
text = "\n".join(texts)
truncated = result.get("stop_reason") == "max_tokens"  # 部分テキストは保持
return text, truncated   # ← 戻り値拡張（呼び出し側を一括改修）
```

### LANG 文言追加（D-05/D-06・ja/en 同一キー）
```python
# lang.py ja / en 両方に追加（現状 290/290 一致を維持）
# D-05 途切れ:
"ocr_err_truncated": "p.{page}: 応答が max_tokens で途切れました。LLM 設定で max_tokens を増やして再実行してください。",
# D-06 待機秒数（既存キーへ {sec} を追加・.format も全箇所更新）:
"ocr_waiting_retry": "p.{page}: レート制限のため待機中（約 {sec} 秒・リトライ {n}/{max}）",
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| プレビューをディスクから再読込 | `self.doc[page_idx]` メモリ直読み | f63d975（2026-05） | 回転・削除の未保存編集が即反映される基盤。H1 の旧原因は除去済み。 |
| `_show_preview` バックグラウンドスレッド | 同期 `_render_preview_pixmap` 純関数 | 62b8a7f（BUG-03/Phase 02-01） | プレビューは同期描画・世代ガード不使用。回転反映は同期経路で完結すべき。 |
| OCR 全ページ base64 一括保持 | producer-consumer パイプライン | Phase 06-02 | メモリ削減。途切れ検出はこの per-page ループに組み込む。 |

**Deprecated/outdated:**
- `doc.tobytes()` 経由のプレビュー: 撤廃済み（`test_render_does_not_call_tobytes` で回帰防止）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 途切れ情報の伝搬は「戻り値拡張 `(text, truncated)`」が最善 | Pattern 2 / Code Examples | 既存 `ocr_image` 戻り値契約（str）に依存する全呼び出し箇所・テストの改修範囲が広がる。discuss で伝搬方式を locked decision 化すべき。 |
| A2 | Claude の途切れは `stop_reason == "max_tokens"`、Gemini は `finishReason == "MAX_TOKENS"` | Pattern 2 | API 仕様変更や値表記差（大小文字）で検出漏れ。実 API 検証手順書（D-08）で実値を確認すべき。 |
| A3 | H1 バグの原因は Canvas viewport/scroll もしくはセレクション意味論 | Pitfall 1 | 実機再現で別原因（例: ボタンコールバックの二重発火）が判明する可能性。先頭で debug タスク必須。 |
| A4 | 待機秒数表示の改修は `_worker`（ocr_dialog.py）のみで足り、`run_parallel`（ocr.py）は実 OCR 実行経路ではない | Pattern 3 / Architecture | `run_parallel` が別経路で使われていれば二箇所改修が必要。`_worker` が実 OCR 実行であることはコード上確認済みだが UAT で要確認。 |

## Open Questions

1. **H1 の真の再現条件**
   - What we know: pixmap 層は回転を即時反映。`_show_preview` は同期。旧原因（ディスク再読込）は除去済み。
   - What's unclear: 実機で「いつ反映されないか」（選択あり時のみ？スクロール時のみ？全条件？）。
   - Recommendation: plan 先頭に実機 GUI 再現タスク（3 条件切り分け）。`gsd-debug` 相当の調査を 1 タスク確保。

2. **途切れ情報の伝搬方式（戻り値拡張 vs 属性）**
   - What we know: 戻り値拡張が素直だが改修範囲が広い。
   - What's unclear: チームの後方互換許容度。
   - Recommendation: A1 を discuss-phase で確定 or planner が「段階導入（新メソッド/型 Union）」を選択。

3. **D-09 統合ケースの要否**
   - What we know: クランプ・429・バックオフ・サーキットブレーカーは網羅テスト済み。
   - Recommendation: **追加統合ケース不要**。途切れ検出（D-05）の単体テストで net-new 振る舞いをカバーすれば十分。

## Environment Availability

> 本フェーズは主にコード/テスト/文書変更。実 API 検証（D-08）はユーザー任意・手動。

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PyMuPDF (fitz) | H1 回転テスト | ✓ | 1.27.2.3 | — |
| pytest | 全自動テスト | ✓ | 9.0.2 | — |
| ruff | リント（CLAUDE.md 必須） | ✓ | 0.15.7 | — |
| ANTHROPIC_API_KEY | H5 実 API 検証（手動・D-08 任意） | ✗（未確認・ユーザー保有） | — | 手順書に記録欄を用意・自動テストで代替担保 |
| GEMINI_API_KEY | H5 実 API 検証（手動・D-08 任意） | ✗（未確認・ユーザー保有） | — | 同上 |

**Missing dependencies with no fallback:** なし（実 API キーは D-07 により手動・任意検証。自動テストが堅牢化ロジックを担保）。
**Missing dependencies with fallback:** 実 API キー → 実 API 検証は手順書＋手動。未設定でもフェーズ完了をブロックしない（D-07/D-08）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-cov 7.1.0 |
| Config file | pyproject.toml（`pythonpath`・S101 除外設定済み・**編集禁止**） |
| Quick run command | `python -m pytest tests/test_viewer.py tests/test_settings_keyguard.py -x` |
| Full suite command | `python -m pytest`（現行ベースライン **564 件** [VERIFIED: ローカル `--co`]） |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V16-QUAL-01 | 90/270° で pixmap w/h 入替 | unit | `pytest tests/test_viewer.py -k rotate -x` | ❌ Wave 0（test_viewer.py に追加） |
| V16-QUAL-01 | 180° で w/h 不変 | unit | `pytest tests/test_viewer.py -k rotate_180 -x` | ❌ Wave 0 |
| V16-QUAL-01 | 見た目の即時反映 | manual UAT | 手順書（回転 → 即反映を目視） | ❌ 手順書要作成 |
| V16-QUAL-02 | `_save_settings` がキー値をログ非出力 | unit (caplog) | `pytest tests/test_settings_keyguard.py -k log -x` | ❌ Wave 0 |
| V16-QUAL-02 | 各クラウドプロバイダがキー値をログ非出力 | unit (caplog) | `pytest tests/test_ocr_providers.py -k log -x` | ❌ Wave 0 |
| V16-QUAL-02 | `pagefolio/` ソースに実キーパターン不在 | unit (scan) | `pytest tests -k no_real_api_keys -x` | ❌ Wave 0 |
| V16-QUAL-02 | 3 経路監査チェックリスト | doc | 監査文書（設定/ソース/ログ） | ❌ 文書要作成 |
| V16-QUAL-03 | max_tokens クランプ境界 | unit | `pytest tests/test_ocr.py -k MaxTokensClamp` | ✅ 既存（1738-1811・重複不要） |
| V16-QUAL-03 | 429/Retry-After/バックオフ/CB | unit | `pytest tests/test_ocr.py -k "Backoff or Circuit or ClampRetry"` | ✅ 既存（重複不要） |
| V16-QUAL-03 | 実 API でクランプ/429 が期待動作 | manual UAT | 検証チェックリスト文書（D-08） | ❌ 文書要作成 |
| V16-QUAL-04 | Claude `stop_reason`=max_tokens で truncated 検出 | unit | `pytest tests/test_ocr_providers.py -k truncat -x` | ❌ Wave 0 |
| V16-QUAL-04 | Gemini `finishReason`=MAX_TOKENS で truncated 検出 | unit | `pytest tests/test_ocr_providers.py -k truncat -x` | ❌ Wave 0 |
| V16-QUAL-04 | 途切れ時に部分テキスト保持 | unit | 同上（results に残ることをアサート） | ❌ Wave 0 |
| V16-QUAL-04 | 待機秒数が文言に含まれる | unit | `pytest tests/test_ocr.py -k waiting -x`（LANG `{sec}` 整合） | ❌ Wave 0 |
| V16-QUAL-04 | ja/en LANG キー一致 | unit | `set(LANG['ja'])==set(LANG['en'])` | ❌ Wave 0（無ければ追加） |

### Sampling Rate
- **Per task commit:** 変更モジュールの対象テスト（例 `pytest tests/test_viewer.py -x`）
- **Per wave merge:** `python -m pytest`（564 件全緑）
- **Phase gate:** `ruff check . && ruff format .` + `python -m pytest`（全緑）+ 開発履歴.md 追記 + APP_VERSION 同期（CLAUDE.md 完了ゲート）

### Wave 0 Gaps
- [ ] `tests/test_viewer.py` — 回転 w/h 入替テスト追加（V16-QUAL-01）
- [ ] `tests/test_settings_keyguard.py` — caplog ログ非出力テスト追加（V16-QUAL-02/D-11）
- [ ] `tests/test_ocr_providers.py` — 途切れ検出テスト＋プロバイダ caplog テスト追加（V16-QUAL-04/02）
- [ ] `tests/`（新規 or 既存）— ソース実キースキャンテスト（V16-QUAL-02/D-12）
- [ ] LANG ja/en キー一致テスト（無ければ追加・`{sec}` 整合の回帰防止）
- [ ] `.planning/phases/03-ocr-a/` — 実 API 検証チェックリスト文書（D-08）＋ 3 経路キー秘匿監査文書（D-10）
- [ ] フレームワーク install: 不要（pytest 既存）

## Security Domain

> `security_enforcement: true`（config.json で確認 [VERIFIED]）。本フェーズはキー秘匿（H2）が中核のため重点。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | API キーは環境変数 > セッションメモリのみ（`_resolve_api_key` os.environ.get 読取専用・settings 非永続化） |
| V3 Session Management | no | アプリにユーザーセッション概念なし（`_session_api_keys` はメモリ内一時保持のみ） |
| V4 Access Control | no | ローカルデスクトップアプリ・権限境界なし |
| V5 Input Validation | partial | API レスポンス JSON は `.get()` 安全アクセス・`stop_reason`/`finishReason` も同方式で検査 |
| V6 Cryptography | no | 暗号処理は実装しない（OS キーストア連携は v2 deferred） |
| V7 Error Handling & Logging | **yes** | **キー値をログ・例外メッセージ・ソースに出さない（H2 中核）**。`_save_settings` はキー名のみ・値非出力。caplog/source scan で回帰担保。 |

### Known Threat Patterns for Tkinter + urllib + クラウド OCR

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API キーが設定ファイルに平文保存 | Information Disclosure | `_SENSITIVE_KEYS` ガード（実装済・test_settings_keyguard.py 担保） |
| API キーがログに平文出力 | Information Disclosure | キー名のみログ・値非出力（実装済 line 89-91）＋ caplog 回帰テスト（D-11 net-new） |
| API キーがソースに誤コミット | Information Disclosure | pytest ソース自動スキャン（D-12 net-new・CI 再発防止） |
| 過大 Retry-After で長時間 sleep（DoS） | Denial of Service | `clamp_retry_after`（60s クランプ・実装済・テスト済） |
| サーバ全落ち時の全ページ × リトライ消化 | Denial of Service | サーキットブレーカー（連続 3 失敗で中断・実装済・テスト済） |
| 途切れレスポンスを完全成功と誤表示 | Tampering（データ完全性） | `stop_reason`/`finishReason` 検査＋ユーザー警告（D-05 net-new） |

## Sources

### Primary (HIGH confidence)
- ローカル実行: `python -c "fitz.set_rotation/get_pixmap"` — 90°/270° で pixmap w/h 入替を実測確認
- ローカル実行: `_render_preview_pixmap` 経由で回転反映を実測（600×900 → 900×600）
- ローカル実行: `python -m pytest --co` — ベースライン 564 件
- ローカル実行: `set(LANG['ja'])==set(LANG['en'])` — 290/290 一致
- ソース精読: `pagefolio/page_ops.py`・`viewer.py`・`ocr.py`・`ocr_providers.py`・`ocr_dialog.py`・`settings.py`・`lang.py`・`app.py`・`file_ops.py`
- ソース精読: `tests/test_ocr.py`（test 一覧）・`test_settings_keyguard.py`・`test_viewer.py`
- git history: `f63d975`（旧プレビュー再読込バグ）・`62b8a7f`（BUG-03 同期化）

### Secondary (MEDIUM confidence)
- Anthropic Messages API `stop_reason`（`max_tokens` 値）— 公式 docs 既知仕様（実 API 検証手順で要確認・A2）
- Gemini generateContent `finishReason`（`MAX_TOKENS` 値）— 公式 docs 既知仕様（同上・A2）

### Tertiary (LOW confidence)
- なし（本フェーズの主張は全てローカル実測または既存コード/テスト精読に基づく）

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 新規依存ゼロ・既存固定版を実測確認
- H1 原因仮説: MEDIUM — pixmap 層が正しいことは HIGH 確認だが、Tk Canvas 層の真因は実機再現待ち（A3）
- M1 途切れ検出: HIGH（未検査の事実）/ MEDIUM（API 値の正確な表記 A2）
- H5 検証状況: HIGH — クランプ実在＆網羅テストをコードとテスト一覧で確認
- H2 監査ギャップ: HIGH — 既存テスト範囲とコードのログ挙動を確認
- Pitfalls: HIGH — 実測・git history・コード根拠あり

**Research date:** 2026-06-19
**Valid until:** 2026-07-19（コードベース安定・PyMuPDF/pytest 固定版。A2 の API 値のみ実 API 検証で確定推奨）