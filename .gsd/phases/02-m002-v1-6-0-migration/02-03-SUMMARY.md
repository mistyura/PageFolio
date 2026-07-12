---
id: S03
parent: M002
milestone: M002
provides:
  - H1 回転プレビュー即時反映バグ（V16-QUAL-01）の原因除去修正（_rotate_selected）
  - 回転 w/h 単体テスト（90/270°入替・180°不変）— pixmap 回転反映の回帰防止アンカー
  - H1 真因の特定記録（セレクション意味論・仮説a）
  - OCRProvider.ocr_image_ex 段階導入（基底デフォルト=(ocr_image(...),False)）
  - Claude/Gemini の応答途切れ検出（stop_reason/finishReason）+ 部分テキスト保持（D-05）
  - _truncated_pages 集合 + 当該ページへの ocr_err_truncated 併記（パネル内提示・D-04）
  - 待機文言の純関数ヘルパー _build_retry_wait_message（delay→sec 反映・D-06）
  - lang.py: ocr_err_truncated 新規 + ocr_waiting_retry/_server へ {sec} 追加（ja/en parity 291）
  - キー値ログ非出力 caplog 回帰（_save_settings + Claude/Gemini ocr_image・D-11）
  - pagefolio/ ソース実キースキャン回帰（sk-ant-/AIza 不在・D-12）
  - ja/en LANG parity + {sec}/{page} format スモーク回帰（Pitfall 3）
  - 実 API 検証チェックリスト（03-VERIFICATION-REALAPI.md・D-08）
  - 3 経路キー秘匿監査チェックリスト（03-AUDIT-KEY-SECRECY.md・D-10）
  - 開発履歴.md v1.7.0 項へ Phase 3（V16-QUAL-01〜04）追記
requires: []
affects: []
key_files: []
key_decisions:
  - H1 真因はセレクション意味論（仮説a）と特定。pixmap/Canvas 層は正常（実測再確認）。
  - 修正は page_ops.py の _rotate_selected に限定。viewer.py は無改修（真因 b でないため）。
  - current が targets 外のとき min(targets) へ寄せ、3ステップ順序・窓正規化・on_page_rotate を温存。
  - A1: ocr_image_ex 段階導入を採用（戻り値タプル化/属性共有を回避し ocr_image の str 契約・全戻り値アサートを無傷で温存）。
  - A2: Claude stop_reason==max_tokens / Gemini finishReason==MAX_TOKENS を .get() 安全アクセスで検査。
  - D-05: 途切れは「成功＋警告」。部分テキストは破棄せず results に保持し ocr_err_truncated を併記。
  - D-06: delay（clamp 後の実待機秒）を待機文言生成の前へ移動し sec=round(delay) を反映。順序入替の回帰を純関数テストで防止。
  - D-04: messagebox 能動通知は採らずパネル内（text ウィジェット）提示を強化。
  - D-09: 堅牢化ロジック（clamp/バックオフ/CB/max_tokens クランプ）は既存テスト済み → 自動テストを重複追加せず実 API は手順書方式。
  - D-11: caplog はキー値非出力のみアサート、キー名出力は仕様として許容（Pitfall 4）。
  - D-12: ソーススキャンは pagefolio/ 限定で tests/ のダミーキーを誤検知しない（Pitfall 5）。
  - APP_VERSION は v1.7.0 を維持（Phase 3 は途中フェーズ・バンプは本マイルストーン完了時）。pagefolio/ 完全無改変。
patterns_established:
  - 回転 w/h テスト: set_rotation 後に _render_preview_pixmap を再取得し w/h 入替/不変を assert
  - セレクション起因の体感バグは current_page を回転対象へ整合させて原因除去する
  - 途切れ検出テスト: stop_reason/finishReason を含むモックボディで (部分テキスト, True) と保持を assert
  - 待機文言テスト: 実 delay（clamp 後）由来 round(delay) が文言に含まれ生 raw_delay（86400）が漏れないことを Tk 非依存で assert
  - 新規回帰テストファイルは test_*.py 命名・リポジトリ相対パス解決で CWD 非依存
  - GSD verify 文書は front-matter（phase/slug/status/created）+ 結果記入欄表で 02-VALIDATION.md に整合
observability_surfaces: []
drill_down_paths: []
duration: 約15分
verification_result: passed
completed_at: 2026-06-19
blocker_discovered: false
---
# S03: Ocr A

**# Phase 03 Plan 01: 体感品質・回転プレビュー即時反映（H1）Summary**

## What Happened

# Phase 03 Plan 01: 体感品質・回転プレビュー即時反映（H1）Summary

**H1 回転プレビュー即時反映バグの真因をセレクション意味論と特定し、_rotate_selected で current_page を回転対象へ寄せる原因除去で修正。90/270°入替・180°不変の回転 w/h 単体テストを回帰防止アンカーとして追加。**

## Performance

- **Duration:** 約15分
- **Started:** 2026-06-19T10:42Z
- **Completed (Task 1+2):** 2026-06-19T10:56Z
- **Tasks:** 3 完了（Task 1/2 実装＋ Task 3 human-verify 承認済み）
- **Files modified:** 2

## Accomplishments
- Task 1（調査）: H1 真因をセレクション意味論（仮説a）と静的コード解析で特定。pixmap 層が回転を即時反映することを自動アサートで再確認。
- Task 2（修正）: 回転 w/h 単体テスト 3 件（90/270°入替・180°不変）を追加し、特定した真因を原因除去で修正。
- Phase 2 窓正規化（reconcile_window_start）・世代ガード非追加の制約を温存し回帰なし。

## Task 1: H1 真因特定（静的コード解析・調査結論）

> 本環境はヘッドレス（非対話）のため `python pagefolio.py` の GUI 起動は行わず、コード経路を厳密に静的解析して真因を確定した。視覚的な最終確認は Task 3（human-verify）で実機検証する。

**自動 pixmap 検証（再確認）:** `python -c "...set_rotation(90)...get_pixmap()..."` → `600 400`（`pixmap rotation OK`）。pixmap 層は回転を正しく反映。Pitfall 1 の通り pixmap 層を疑わない。

**3 条件の切り分け（コードレベル）:**

| 条件 | targets（_get_targets） | _show_preview が描画する current_page | 即時反映 | 判定 |
|------|------------------------|--------------------------------------|----------|------|
| (a) 選択なしで現在ページ回転 | `[current_page]` | current_page（= 回転対象） | される | 正常 |
| (b) current 以外を選択して回転 | `selected_pages`（current を含まない） | current_page（= 回転対象外） | **されない** | **真因** |
| (c) スクロール状態で現在ページ回転 | `[current_page]` | current_page を anchor="nw" で再描画 | される | 正常（scroll は表示位置のみ） |

**真因（特定・1案確定）:** **仮説(a) セレクション意味論**。
`_show_preview`（viewer.py 85）は常に `page_idx = self.current_page` を描画する。`_rotate_selected` は `_get_targets()`（app.py 195-196）が返す `targets`（`selected_pages` 優先）を回転するが、ユーザーが Ctrl+クリック（`_toggle_select`, viewer.py 32-37）で `current_page` と異なるページを選択していると、回転後も `_show_preview` は回転対象外の `current_page` を描画し続け、プレビューが「回らない」ように見える。単一クリック（`_single_click`, viewer.py 381-386）は `selected_pages` をクリアし `current_page=idx` にするため、その経路では回転が反映され、症状が「選択状態によって出たり出なかったり」する点とも整合する。

**仮説(b) Canvas viewport は棄却:** `_show_preview` は毎回 `delete("all")` → `create_image(pad, pad, anchor="nw")` で回転後 pixmap を左上に再描画し、`scrollregion` も新 w/h から再計算する。回転 pixmap は必ず描画されるため、(b) は最悪でもスクロール位置の見栄え問題に留まり「回転が全く反映されない」原因にはならない。

**Task 2 修正方針（原因除去・描画追加でない）:** `_rotate_selected` で `current_page` が `targets` に含まれないとき `min(targets)`（昇順先頭）へ寄せ、回転結果が即プレビューへ反映されるようにする。3ステップ順序・`reconcile_window_start`・`on_page_rotate` 発火は温存。

## Task 2: 回転 w/h テスト + 原因除去修正

- `tests/test_viewer.py` に `TestRotationReflectsInPreviewPixmap`（`test_rotate_90_swaps_wh` / `test_rotate_180_keeps_wh` / `test_rotate_270_swaps_wh`）を追加。`_make_stub` を流用し Tk 非依存で回転反映を担保（実測 600×900 → 900×600）。
- `pagefolio/page_ops.py::_rotate_selected` に「current が targets 外なら `min(targets)` へ寄せる」最小修正を追加。viewer.py は無改修。
- `_preview_gen` 世代ガードは `_show_preview` に新規追加していない（grep で viewer.py に 0 件確認）。
- `_refresh_all` は依然 `reconcile_window_start`（line 225）を `_build_thumbnails`（228）/`_show_preview`（229）の前に呼ぶ（窓正規化温存）。

**検証結果:**
- `pytest tests/test_viewer.py -k rotate -x` → 3 passed（90/270°入替・180°不変が緑）
- `pytest tests/test_viewer.py tests/test_pagination.py -x` → 76 passed（Phase 2 窓挙動の回帰なし）
- `ruff check` / `ruff format --check`（page_ops.py / test_viewer.py）→ All checks passed / already formatted

## Task Commits

各タスクは個別にアトミックコミット:

1. **Task 2 (RED アンカー): 回転 w/h 単体テスト追加** - `b3f070a` (test)
2. **Task 2 (GREEN/原因除去): H1 即時反映バグ修正** - `8714aec` (fix)

_Task 1 はコード生成のない調査タスクのため、結論を本 SUMMARY に記録（上記 Task 1 節）。_

## Task 3: 実機 UAT（human-verify チェックポイント）— APPROVED

**結果:** ✅ ユーザーにより **承認（approved）**（2026-06-19）。

`<task type="checkpoint:human-verify" gate="blocking">` の実機目視確認をユーザーが実施し、回転即時反映が正しく動作することを確認した。検証観点:

1. 単一選択回転 → 再読込・ページ送りせずプレビューがその場で回る ✅
2. 複数選択一括回転 → 現在の窓内に見えている対象サムネイルが揃って回る（窓外は D-02/Pitfall 6 通り対象外）✅
3. スクロール状態での回転 → 表示破綻なく回転後寸法で正しく表示 ✅
4. 回転後の削除・ページ送り・窓ナビ（◀▶）で Phase 2 ページネーション挙動（snap back しない・窓内不変条件）に回帰なし ✅

成功基準 V16-QUAL-01 成功基準1（回転がプレビューへ即時反映される・手動 UAT 承認）を満たした。

## Files Created/Modified
- `tests/test_viewer.py` - 回転 w/h 単体テスト 3 件（90/270°入替・180°不変）を追加
- `pagefolio/page_ops.py` - `_rotate_selected` に current を回転対象代表へ寄せる原因除去修正を追加

## Decisions Made
- H1 真因をセレクション意味論（仮説a）に1案確定し、原因除去を page_ops.py に限定した。
- viewer.py は真因(b)でないため無改修。`_preview_gen` 世代ガードは禁止事項通り追加しない。
- `current_page` の寄せ先は昇順先頭 `min(targets)`（決定的・窓追従への影響が小さい）。

## Deviations from Plan

None - plan executed exactly as written.

ヘッドレス環境のため Task 1 は GUI 起動の代わりに厳密な静的コード解析で真因を特定したが、これは実行プロンプトの指示（acceptance_criteria は自動 pixmap 検証＋真因記録のみを要求）に沿った範囲であり計画からの逸脱ではない。視覚確認は Task 3（human-verify）に委譲。

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Task 1/2 完了・コミット済み。回転 w/h テストと原因除去修正は緑・回帰なし。
- **Task 3（blocking human-verify チェックポイント）はユーザー承認済み（approved）**。実機 UAT で回転即時反映を確認済み。プラン 03-01 完了。
- 同 Wave の 03-02、Wave 2 の 03-03 は本プランと独立。Phase 3 の残プラン実行に進める。

## Self-Check: PASSED

- FOUND: `.planning/phases/03-ocr-a/03-01-SUMMARY.md`
- FOUND: `tests/test_viewer.py`
- FOUND: `pagefolio/page_ops.py`
- FOUND commit: `b3f070a`（test）
- FOUND commit: `8714aec`（fix）

---
*Phase: 03-ocr-a*
*Completed (Task 1+2): 2026-06-19*

# 03-02 SUMMARY — OCR 堅牢性（応答途切れ検出・部分テキスト保持・待機秒数文言）

## 概要

V16-QUAL-04（成功基準4）を達成。OCR の応答途切れ（トークン超過）を検出してユーザーに
「状況＋次アクション」を提示し、レート制限待機表示に実待機秒数を併記した。実装は既存の
パネル内提示（OCRDialog）の作法を踏襲し、messagebox 能動通知は採らない（D-04）。

## Task 1: ocr_image_ex 段階導入 + Claude/Gemini 途切れ検出

- `OCRProvider` に非抽象メソッド `ocr_image_ex(b64_png, prompt, **kwargs) -> (text, truncated)`
  を新設。基底デフォルトは `(self.ocr_image(...), False)` で LM Studio / Tesseract は後方互換。
- Claude: HTTP 部を `_post_messages`、text 抽出を `_extract_text` に分離し、`ocr_image` と
  `ocr_image_ex` で共有。`ocr_image_ex` は `stop_reason == "max_tokens"` を検査して
  `(text, truncated)` を返す。
- Gemini: HTTP 部を `_post_generate`、途切れ判定を `_is_truncated`（`finishReason == "MAX_TOKENS"`）
  に分離。`ocr_image` の str 契約・例外規約・`_parse_response` は不変。
- 途切れは例外化せずフラグ伝搬（部分テキスト喪失を防ぐ・Pitfall 2）。
- テスト: `TestOcrImageExTruncation`（Claude/Gemini truncated 検出＋部分テキスト保持、
  stop_reason 欠落の正常系、LM Studio 基底デフォルト後方互換）6 件追加。既存 109 件は無改変で全緑。

## Task 2: _worker 伝搬・併記 + 待機秒数文言 + 待機文言の純関数抽出

- `_worker` の API 呼び出しを `text, truncated = self.provider.ocr_image_ex(...)` に変更し、
  `_record_page_success(page_idx, text, truncated=truncated)` で伝搬。
- `_record_page_success` に `truncated` 引数を追加し `_truncated_pages`（set）へ登録/解除。
  `__init__` で初期化、`_on_run` のリラン時 clear・再開時は対象ページを discard。
- `_render_results_ordered` で当該ページの部分テキスト直後に `ocr_err_truncated` を併記。
- 待機文言を純関数 `_build_retry_wait_message(wait_key, page_idx, attempt, delay)` へ抽出。
  `_worker` で `delay = clamp_retry_after(raw_delay)` を待機文言生成より前に算出し、
  `sec=round(delay)` を反映（D-06 順序入替）。`after` クロージャは生成済み文言を set するだけ。
- lang.py: `ocr_err_truncated` 新規 + `ocr_waiting_retry`/`ocr_waiting_retry_server` に `{sec}`
  追加（ja/en 同一キー・parity 291）。
- テスト: `TestRetryWaitMessage`（429 の clamp 後 sec 反映、5xx の生値 86400 非漏洩、
  ja/en×両キーの KeyError 非送出）3 件追加。

## 検証結果

- `pytest tests/test_ocr_providers.py tests/test_ocr.py` — 239 passed
- 全テスト `pytest` — 576 passed
- `ruff check . && ruff format .` — All checks passed
- LANG parity — `set(LANG['ja'])==set(LANG['en'])` OK（291 キー）

## 次プラン（03-03）への申し送り

- lang.py は本プランで確定（`{sec}` 追加・`ocr_err_truncated` 新規・parity 291）。03-03 の
  LANG parity 回帰テストはこの確定状態（291 キー）を基準にできる。
- 03-03 は `tests/test_ocr_providers.py` を caplog テストで触るが本プランの追加関数とは別関数のため衝突なし。
- 実 API での stop_reason/finishReason 値の最終確認は 03-03 の D-08 実機検証チェックリストで実施予定。

# 03-03 SUMMARY — キー秘匿監査回帰テスト + 実 API 検証チェックリスト

## 概要

V16-QUAL-02（キー秘匿監査）と V16-QUAL-03（max_tokens/429 実機検証）を、回帰テスト＋検証/監査
文書の両立で達成。`pagefolio/` ソースは一切改変せず「監査＝検証＋ギャップ補完」に徹した（D-09/D-10）。

## Task 1: ログ平文露出 caplog 回帰（D-11）

- `tests/test_settings_keyguard.py` に `test_api_key_value_not_logged` を追加。`_save_settings` を
  `caplog.at_level(DEBUG)` 配下で機密キー入り settings に対して呼び、キー**値**が `caplog.text` に
  出ないことのみアサート（キー名出力は仕様として許容・Pitfall 4）。
- `tests/test_ocr_providers.py` に `TestProviderKeyNotLogged`（Claude/Gemini）を追加。urlopen を
  モックしつつ `ocr_image` を caplog 配下で呼び、渡したダミーキー値がログへ出ないことを担保。

## Task 2: ソース実キースキャン + LANG parity（D-12 + Pitfall 3）

- 新規 `tests/test_source_keyguard.py::test_no_real_api_keys_in_source`: `pagefolio/` の全 `.py` を
  `rglob` し `sk-ant-[A-Za-z0-9_-]{20,}` / `AIza[A-Za-z0-9_-]{30,}` 不在を assert。`tests/` 除外で
  ダミーキー誤検知を回避（Pitfall 5）。`Path(__file__).resolve().parent.parent` でリポジトリ相対解決。
- 新規 `tests/test_lang_parity.py::test_lang_keys_parity`: `set(LANG['ja'])==set(LANG['en'])`（291）。
  併せて待機/途切れ文言の `{sec}`/`{page}` format スモークで Pitfall 3（プレースホルダ不整合）を回帰防止。

## Task 3: 検証/監査文書 + フェーズ完了ゲート

- `.planning/phases/03-ocr-a/03-VERIFICATION-REALAPI.md`（D-08）: max_tokens クランプ・429 リトライ・
  A2 実値（stop_reason/finishReason）の実 API 確認手順と結果記入欄。キー未設定時はフェーズを
  ブロックしない旨と自動テストの相互参照を明記。
- `.planning/phases/03-ocr-a/03-AUDIT-KEY-SECRECY.md`（D-10）: 設定/ソース/ログ + 環境変数/セッション
  メモリの 4 区分で確認項目と対応自動テスト ID（`TestSaveSettingsKeyGuard` / `test_no_real_api_keys_in_source`
  / `TestProviderKeyNotLogged` 等）を相互参照。
- `開発履歴.md` の v1.7.0 項へ Phase 3（V16-QUAL-01〜04）を追記（新版番行なし）。`APP_VERSION` は
  v1.7.0 を維持し constants.py / README バッジ / 開発履歴.md の 3 箇所一致を確認のみ（無改変）。

## 検証結果

- caplog（settings + プロバイダ）`-k log` — 3 passed
- ソーススキャン + LANG parity — 3 passed
- 文書存在・版番同期スモーク — `docs+version held at v1.7.0`
- pagefolio/ 配下の変更なし（git status 確認・H2 監査=検証で実装無改変）
- 全テスト `pytest` — 582 passed / `ruff check . && ruff format .` — All checks passed

## Phase 3 全体の完了状況

- 03-01（V16-QUAL-01 回転即時反映）/ 03-02（V16-QUAL-04 OCR 途切れ・待機秒数）/ 03-03（V16-QUAL-02/03
  キー秘匿監査・実 API 検証）の 3 プラン全完了。要件 V16-QUAL-01〜04 を達成。
- 実 API 検証（03-VERIFICATION-REALAPI.md）はユーザー任意実行の手動項目として残置（D-07・キー未設定でも
  フェーズ完了をブロックしない）。
