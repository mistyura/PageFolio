# Phase 3: 体感品質・回転プレビュー & OCR 堅牢性（プランA） - Pattern Map

**Mapped:** 2026-06-19
**Files analyzed:** 13（修正 6・新規/拡充テスト 5・新規文書 2）
**Analogs found:** 13 / 13（全ファイルに既存アナログあり — 本フェーズは net-new 機構が少なく「既存作法の踏襲」が中核）

> 本フェーズは新規ファイル/モジュールをほぼ作らない。修正対象は自分自身が最良の文脈であり、テストは既存テスト作法（`_make_stub` / caplog / `_Fake*Response`）を、文書は前フェーズ（02-pagination）の `*-VALIDATION.md` を踏襲する。各「アナログ」は同一ファイル内の確立済みパターン、または同種ファイルを指す。

---

## File Classification

| 対象ファイル | 種別 | Role | Data Flow | 最良アナログ | Match Quality |
|--------------|------|------|-----------|--------------|---------------|
| `pagefolio/viewer.py`（`_show_preview`/`_refresh_all`） | 修正 | viewer (Mixin) | request-response（同期再描画） | 同ファイル `_show_preview`（61-115）/`_refresh_all`（218-252）自身 | exact（自己整合） |
| `pagefolio/page_ops.py`（`_rotate_selected`） | 修正 | page-ops (Mixin) | transform（回転適用→再描画呼出） | 同ファイル `_rotate_selected`（80-91）自身 | exact |
| `pagefolio/ocr_providers.py`（Claude/Gemini `ocr_image`） | 修正 | provider | request-response（HTTP→JSON 解析） | Claude `ocr_image` 解析部（383-397）/ Gemini `_parse_response`（513-526） | exact |
| `pagefolio/ocr_dialog.py`（`_worker` 待機・`_finish_error`） | 修正 | dialog (表示層) | event-driven（after 連鎖・進捗反映） | 同ファイル `_worker`（1303-1343）/ `_finish_error`（1497-1528）/ `_append_resume_hint`（1530-1540） | exact |
| `pagefolio/ocr.py`（`clamp_retry_after` 受け渡し） | 修正（検証主） | ocr ヘルパー | transform（秒数クランプ） | 同ファイル `clamp_retry_after`（58-67）/`interruptible_sleep`（70-86） | exact |
| `pagefolio/lang.py`（`ocr_err_truncated` 等） | 修正 | config（言語辞書） | — | 同ファイル `ocr_waiting_retry`（346）/`ocr_resume_hint`（408） | exact |
| `tests/test_viewer.py`（回転 w/h 入替） | 拡充 | test | unit（純関数） | 同ファイル `_make_stub`（15-23）+ `TestPreviewRender`（26-） | exact |
| `tests/test_settings_keyguard.py`（caplog ログ非出力） | 拡充 | test | unit（caplog） | 同ファイル `TestSaveSettingsKeyGuard`（35-160） | exact（拡張） |
| `tests/test_ocr_providers.py`（途切れ検出・provider caplog） | 拡充 | test | unit（HTTP モック） | 同ファイル `_FakeClaudeResponse`（477）/`_FakeHTTPError`（494）/`TestClaudeProviderOcrImage`（508）/`TestGeminiProviderOcrImage`（825） | exact |
| ソース実キースキャンテスト（新規） | 新規 | test | batch（ソース走査） | RESEARCH §Pattern 5 + `tests/` 既存 pathlib なし → net-new（最小自作） | role-match（弱） |
| LANG ja/en キー一致テスト（新規・無ければ） | 新規 | test | unit | RESEARCH §Don't Hand-Roll `set(LANG['ja'])==set(LANG['en'])` | role-match |
| 実 API 検証チェックリスト文書（D-08・新規） | 新規 | doc | — | `.planning/phases/02-pagination/02-VALIDATION.md`（front-matter + 表構造） | role-match |
| 3 経路キー秘匿監査チェックリスト（D-10・新規） | 新規 | doc | — | 同上 02-VALIDATION.md | role-match |

---

## Pattern Assignments

### `pagefolio/page_ops.py` — `_rotate_selected`（page-ops, transform）

**アナログ:** 自己（80-91）。回転適用→キャッシュ無効化→再描画の順序は既に正しい。**コードの追加ではなく、`viewer.py` 側の原因除去が H1 の核**（RESEARCH Pitfall 1）。改修するとしてもこの 3 ステップ順序を壊さないこと。

```python
# 現状（pagefolio/page_ops.py 80-91）— この経路は「呼ばれているのに反映されない」
def _rotate_selected(self, deg):
    if not self._check_doc():
        return
    targets = self._get_targets()
    self._save_undo("rotate", targets=targets)
    for i in targets:
        page = self.doc[i]
        page.set_rotation((page.rotation + deg) % 360)   # pixmap は即反映（検証済）
    self._invalidate_thumb_cache(targets)                # サムネイル即時反映の土台
    self._refresh_all()                                  # → _show_preview を内包
    self._set_status(self._t("status_rotated").format(count=len(targets), deg=deg))
    self.plugin_manager.fire_event("on_page_rotate", self, targets, deg)
```

**注意（RESEARCH A3）:** plan 先頭に実機 GUI 再現タスクを置く。真因仮説 = (a) `targets` が `current_page` を含まない体感バグ、(b) Canvas scrollregion/scroll 位置。

---

### `pagefolio/viewer.py` — `_show_preview`（viewer, request-response）

**アナログ:** 自己（61-115）。同期・世代ガード非使用。

**Canvas 再描画パターン（114-115・修正候補の中心）:**
```python
self.preview_canvas.create_image(pad, pad, anchor="nw", image=photo)
self.preview_canvas.configure(scrollregion=(0, 0, w + pad * 2, h + pad * 2))
```
回転で w/h が入れ替わると scrollregion は再設定されるが、**スクロール位置（xview/yview）は保持される**。回転後に viewport が旧寸法基準のままになる可能性が原因候補。

**アンチパターン（RESEARCH）:** `_show_preview` に `_preview_gen` 世代ガードを新規追加しない（同期経路・Phase 2 窓正規化を壊す）。`_refresh_all`（218-252）の `reconcile_window_start` 呼び出し順も温存する。

**Render 純関数（50-59・テスト対象）:** `_render_preview_pixmap` は `self.doc[page_idx]` をメモリ直読みし回転を即反映。D-03 テストはこれを直接叩く。

---

### `pagefolio/ocr_providers.py` — 途切れ検出（provider, request-response）

**アナログ:** 自己の JSON 解析直後。`stop_reason`/`finishReason` は**現状未検査**（net-new はこの 1 行のみ）。

**Claude（383-397 を改修・部分テキスト保持必達）:**
```python
# 現状: 終了理由を読まず "\n".join(texts) を返す
result = json.loads(body)
texts = [block.get("text") for block in result.get("content", [])
         if block.get("type") == "text" and block.get("text")]
if not texts:
    raise RuntimeError(f"Unexpected response format: {body[:500]}")
# ↓ 追加（D-05）: truncated は max_tokens 到達。部分テキストは捨てない
truncated = result.get("stop_reason") == "max_tokens"   # [A2: 実 API で値確認]
```

**Gemini（`_parse_response` 513-526 を改修）:**
```python
candidates = body.get("candidates", [])
if not candidates:
    reason = body.get("promptFeedback", {}).get("blockReason", "unknown")
    raise RuntimeError(f"Gemini blocked: {reason}")
parts = candidates[0].get("content", {}).get("parts", [])
truncated = candidates[0].get("finishReason") == "MAX_TOKENS"   # [A2]
```

**伝搬設計（要 planner 決定・RESEARCH A1）:** `ocr_image` は現在 `str` 契約。`(text, truncated)` タプル化 → `_worker`（1305）の全呼び出し改修 + `tests/test_ocr_providers.py` の戻り値アサート更新が必要。`str | tuple` 段階導入 or 新メソッドかは planner 判断。**plan 前の locked decision 化が望ましい。**

**アンチパターン:** 途切れを例外送出にしない（部分テキスト喪失・D-05 違反）。`.get()` 安全アクセスの既存作法（M-9 コメント参照）を踏襲。

---

### `pagefolio/ocr_dialog.py` — 待機秒数表示 & エラー UX（dialog, event-driven）

**アナログ:** 自己 `_worker`（1303-1343）/ `_finish_error`（1497-1528）/ `_append_resume_hint`（1530-1540）。

**待機文言（D-06）— delay 計算を文言生成の前へ（現状は順序が逆）:**
```python
# 現状（1315-1343）: 文言 set（1318-）が先、delay 計算（1342）が後
wait_key = self._retry_wait_key(e)        # 429→ocr_waiting_retry / 5xx→_server
self.after(0, lambda p=page_idx, _n=n, _k=wait_key:
    self.progress_var.set(self._L[_k].format(page=p+1, n=_n, max=MAX_RETRIES)))
...
raw_delay = e.retry_after if e.retry_after is not None else 1.0 * (2 ** (attempt - 1))
delay = clamp_retry_after(raw_delay)       # ← これを文言生成の前へ移動
interruptible_sleep(delay, self._cancel_flag.is_set)
```
改修後は `delay` を先に算出し `_L[_k].format(..., sec=round(delay))` へ渡す。`_retry_wait_key`（698-706）が返す両キー（`ocr_waiting_retry`/`ocr_waiting_retry_server`）の `.format` に `sec=` を追加すること（Pitfall 3）。

**エラー提示パターン（`_finish_error` 1497-1528）— kind 分岐 + パネル内追記:**
```python
if kind == "connection":
    user_msg = self._L["ocr_err_connection"].format(url=..., error=msg)
elif kind == "timeout":
    user_msg = self._L["ocr_err_timeout"].format(...)
elif kind == "circuit_breaker":
    user_msg = self._L["ocr_err_circuit_breaker"].format(n=CB_CONSECUTIVE_FAILURES, error=msg)
else:
    user_msg = msg
self.text.insert("end", "\n" + user_msg + "\n")   # ← messagebox でなくパネル内（D-04）
self._append_resume_hint()                         # 部分成功なら再開導線
```
途切れ注記（D-05）はこの作法を踏襲し、当該ページ行へ `ocr_err_truncated` を併記。`_append_resume_hint`（1530-1540）の `.format(n=, first=)` パターンが「状況＋次アクション」の手本。

---

### `pagefolio/ocr.py` — 待機クランプ（ocr ヘルパー, transform）

**アナログ:** 自己 `clamp_retry_after`（58-67）/ `interruptible_sleep`（70-86）。**実装済み・テスト済み。改修不要**（D-06 で D-09 値を `_worker` 文言へ渡すだけ）。新規クランプを各所で自作しない（Don't Hand-Roll）。

---

### `pagefolio/lang.py` — 新規/改訂文言（config）

**アナログ:** `ocr_waiting_retry`（346）/`ocr_resume_hint`（408）。**ja/en 両辞書に同一キーで追加**（現状 290/290 一致）。

```python
# 改訂（{sec} 追加・ocr_dialog の .format も全箇所更新）
"ocr_waiting_retry": "p.{page}: レート制限のため待機中（約 {sec} 秒・リトライ {n}/{max}）",
"ocr_waiting_retry_server": "p.{page}: サーバエラーのためリトライ中（約 {sec} 秒・{n}/{max}）",
# 新規（D-05 途切れ・部分テキストは保持済み前提の注記）
"ocr_err_truncated": "p.{page}: 応答が max_tokens で途切れました。LLM 設定で max_tokens を増やして再実行してください。",
```
en 側にも同一キーを `set(LANG['ja'])==set(LANG['en'])` が緑のまま追加。`{sec}` を片方だけに足さない（Pitfall 3・アンチパターン）。

---

### `tests/test_viewer.py` — 回転 w/h 入替（test, unit）

**アナログ:** `_make_stub`（15-23）+ `TestPreviewRender`（26-）。Tk root 不要の純関数スタブを流用。

```python
# 既存 _make_stub をそのまま使用（15-23）
def _make_stub(doc):
    stub = types.SimpleNamespace(doc=doc)
    stub._render_preview_pixmap = ViewerMixin._render_preview_pixmap.__get__(stub)
    return stub

# 新規（RESEARCH VERIFIED: 600x900 → 900x600）
def test_rotate_90_swaps_wh():
    doc = fitz.open(); doc.new_page(width=400, height=600)
    s = _make_stub(doc)
    _, w0, h0 = s._render_preview_pixmap(0, 1.0)
    doc[0].set_rotation(90)
    _, w1, h1 = s._render_preview_pixmap(0, 1.0)
    assert (w1, h1) == (h0, w0)
```
`sample_pdf_doc` フィクスチャ（conftest.py）も利用可。180° で w/h 不変のケースも追加。

---

### `tests/test_settings_keyguard.py` — caplog ログ非出力（test, caplog）

**アナログ:** `TestSaveSettingsKeyGuard`（35-160）の monkeypatch（`_get_settings_path`）作法をそのまま継承し caplog を追加。

```python
def test_save_settings_does_not_log_key_value(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("pagefolio.settings._get_settings_path",
                        lambda: str(tmp_path / "s.json"))
    import logging
    with caplog.at_level(logging.DEBUG):
        _save_settings({"theme": "dark", "claude_api_key": "sk-ant-LEAK-XYZ"})
    assert "sk-ant-LEAK-XYZ" not in caplog.text   # 値非出力
    # 注意: _save_settings はキー"名"を logger.error で出す（settings.py 89-91）。
    #       「キー名が出ない」はアサートしない（Pitfall 4）。
```
ダミーキー文字列は既存テストの `sk-ant-secret-should-not-appear` 等と整合させる。

---

### `tests/test_ocr_providers.py` — 途切れ検出 & provider caplog（test, HTTP モック）

**アナログ:** `_FakeClaudeResponse`（477）/`_FakeHTTPError`（494）/`TestClaudeProviderOcrImage`（508）/`TestGeminiProviderOcrImage`（825）。既存の HTTP モック作法で `stop_reason`/`finishReason` 入りボディを流す。

- 途切れ検出: `stop_reason="max_tokens"` のレスポンスで `truncated` フラグ（or タプル第 2 要素）が立つ + 部分テキストが results に残ることをアサート。
- provider caplog: 各クラウドプロバイダ `ocr_image` 呼び出しでキー値が `caplog.text` に出ないこと（D-11）。`urlopen` を monkeypatch して `_FakeClaudeResponse` を返す既存パターンを流用。
- **伝搬方式確定後**、既存の `ocr_image` 戻り値アサート（`TestClaudeProviderOcrImage` 内）の更新が必要になりうる（A1）。

---

### ソース実キースキャンテスト（test, batch・新規）

**アナログなし（弱 role-match）:** `tests/` に pathlib 走査の前例なし。RESEARCH §Pattern 5 を最小実装。

```python
import re, pathlib
PATTERNS = [re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
            re.compile(r"AIza[A-Za-z0-9_-]{30,}")]
def test_no_real_api_keys_in_source():
    for p in pathlib.Path("pagefolio").rglob("*.py"):   # tests/ は除外（Pitfall 5）
        text = p.read_text(encoding="utf-8")
        for pat in PATTERNS:
            assert not pat.search(text), f"疑わしいキーが {p} に存在"
```
スコープを `pagefolio/` に限定（`tests/` のダミーキー誤検知回避）。閾値長は実キー長近辺。

---

### LANG ja/en キー一致テスト（test, unit・新規 or 既存確認）

既存に無ければ追加（Don't Hand-Roll）:
```python
from pagefolio.lang import LANG
def test_lang_keys_parity():
    assert set(LANG["ja"]) == set(LANG["en"])   # 現状 290/290
```

---

### 実 API 検証チェックリスト（D-08）/ 3 経路監査チェックリスト（D-10）— 文書

**アナログ:** `.planning/phases/02-pagination/02-VALIDATION.md`。front-matter（`phase`/`slug`/`status`/`created`）+ 「期待結果 / 結果記入欄」の表構造を踏襲。`.planning/phases/03-ocr-a/` 内に作成。GSD verify フローと整合。ファイル名/章立ては裁量（D-08/CONTEXT Claude's Discretion）。
- D-08: max_tokens クランプ・429/Retry-After の実 API 動作の手順・期待結果・記入欄。
- D-10: 3 経路（設定ファイル / ソース / ログ）の確認項目 + 結果。各経路の自動テスト ID へ相互参照。

---

## Shared Patterns

### LANG ja/en 同一キー規約
**Source:** `pagefolio/lang.py`（ja 340-414 と en 対応箇所）
**Apply to:** D-05/D-06 の全文言追加・改訂
- 両辞書に同一キーで追加。`{sec}` 等プレースホルダ追加時は `.format()` 呼び出し（`ocr_dialog.py` 1321-1325・`_retry_wait_key` 経由の両キー）を同一コミットで更新。`set(LANG['ja'])==set(LANG['en'])` テストで担保。

### キー値ログ非出力（V7 / H2）
**Source:** `pagefolio/settings.py` `_save_settings`（89-91・キー名のみ `logger.error`・値非出力）
**Apply to:** 全クラウドプロバイダ + `_save_settings` の caplog テスト
- 検査は「キー**値**が出ない」のみ。キー**名**出力は仕様。

### HTTP プロバイダ応答の安全アクセス
**Source:** `pagefolio/ocr_providers.py` Claude `ocr_image`（386-397）/ Gemini `_parse_response`（513-526）
**Apply to:** 途切れ検出の `stop_reason`/`finishReason` 読み取り
- `result.get(...)` / `candidates[0].get(...)` の `.get()` 安全アクセス。`content[0]` 決め打ち禁止（既存 M-9/Pitfall コメント）。

### after 連鎖 + 世代ガード（`_run_gen`）
**Source:** `pagefolio/ocr_dialog.py` `_worker`（M-2 コメント・1314-1315/1374/1402）
**Apply to:** 待機秒数文言・途切れ注記の進捗反映
- `self.after` 投函は世代ガード（`gen is None or gen == self._run_gen`）後のみ。`tk.TclError` を捕捉。

### テストスタブ作法
**Source:** `tests/test_viewer.py` `_make_stub`（15-23）/ `tests/test_ocr_providers.py` `_Fake*Response`（477/494）
**Apply to:** 回転テスト（純関数スタブ）/ 途切れ・caplog テスト（HTTP モック）

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| ソース実キースキャンテスト | test | batch | `tests/` に pathlib ソース走査の前例なし。RESEARCH §Pattern 5 を最小自作（標準ライブラリ `re`/`pathlib` のみ・新規依存なし）。 |

> 文書 2 種（D-08/D-10）は厳密には「コードアナログ」ではないが、前フェーズ `02-VALIDATION.md` を構造アナログとして利用可能なため No-Analog には含めない。

---

## Metadata

**Analog search scope:** `pagefolio/`（viewer/page_ops/ocr/ocr_providers/ocr_dialog/lang/settings）・`tests/`（test_viewer/test_settings_keyguard/test_ocr_providers）・`.planning/phases/02-pagination/`
**Files scanned:** 11（ソース 7・テスト 3・文書 1）
**Pattern extraction date:** 2026-06-19
