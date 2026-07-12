# Phase 3: 体感品質・回転プレビュー & OCR 堅牢性（プランA） - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

ページ回転のプレビュー即時反映（H1）と、OCR の堅牢性・体感品質（H2 キー秘匿監査・H5 max_tokens/429 検証・M1 エラー UX 磨き）を一括で底上げする。対象要件 V16-QUAL-01〜04。

性質の異なる 4 要件を「体感品質・堅牢性」という単一目的で束ねたフェーズ（STATE.md V16-R-03）。viewer 層の即時反映バグ修正と、OCR/エラー系の監査・検証・文言磨きが混在する。

**スコープ外:** 新しいページ操作・新 OCR プロバイダ・OCR 出力の Markdown 整形やプロバイダ別プロンプト最適化（→ Phase 4）。実 API を常時叩く CI 化。エラー提示のモーダル/バナー化（パネル内強化を採用）。

対象要件: V16-QUAL-01（H1 回転即時反映）/ V16-QUAL-02（H2 キー秘匿監査）/ V16-QUAL-03（H5 max_tokens・429 検証）/ V16-QUAL-04（M1 エラー UX）

</domain>

<decisions>
## Implementation Decisions

### H1 回転プレビュー即時反映（V16-QUAL-01）
- **D-01:** **現状は即時反映されないバグがある**（ユーザー実機確認）。`_rotate_selected` は `_invalidate_thumb_cache(targets)` → `_refresh_all()`（→ `_show_preview` で `get_pixmap` 再描画）を呼んでいるのに、回転ボタン押下でプレビューがすぐ回らず、ページ切替/再読込で初めて反映される。**原因のトレースと修正が H1 の中核**（researcher が `_refresh_all`/`_show_preview`/`set_rotation` の経路を調査）。
- **D-02:** **即時反映の対象はプレビュー（現在ページ）＋回転した選択中の全サムネイル両方**。複数選択一括回転の体感を整える。`thumb_cache` は既に `targets` で無効化済みのため、サムネイル側はキャッシュ無効化＋再描画が効く構造になっている前提。
- **D-03:** **担保は「検証可能な単位テスト＋手動 UAT」**。`_render_preview_pixmap` が回転後の page を反映する（例: 90/270° で pixmap の width/height が入れ替わる）ことを可能な範囲でテストし、最終的な「見た目の即時反映」はフェーズ内検証手順書/UAT で目視確認する。

### M1 エラーハンドリング UX（V16-QUAL-04）
- **D-04:** **エラー/警告は既存のパネル内提示（OCRDialog の結果欄・進捗ラベル）を強化する**。messagebox での能動通知は採らない（大量ページでダイアログ連発のリスク）。既存 `ocr_err_*` / `_append_resume_hint` と一貫した「状況＋次アクション」の文言・網羅性を磨く。
- **D-05:** **トークン超過による応答途切れを検出して専用文言＋次アクションを提示する**。現状プロバイダは `stop_reason`（Claude）/`finishReason`（Gemini）を検査せず、max_tokens 到達時に途切れたテキストが無言で返る。プロバイダ応答でこれらを検査し、当該ページに「応答が max_tokens で途切れた・LLM 設定で max_tokens を増やして再実行」等の専用 LANG 文言（ja/en 同一キー）を出す。**部分テキストは保持**する。
- **D-06:** **レート制限待機中の表示に待ち時間を併記する**。現行「p.X: レート制限のため待機中（リトライ n/max）」に「約 N 秒待機」（Retry-After/バックオフ秒数・`RETRY_AFTER_CAP=60s` でクランプ済の実待機値）を加え、「次アクション＝待つ」をユーザーが理解できるようにする。

### H5 max_tokens クランプ・429 リトライ検証（V16-QUAL-03）
- **D-07:** **検証は「実機相当の手順書中心」**。実 API を常時叩く方式は課金・429 再現困難で不安定なため採らない。クランプ/リトライロジックはユニット/統合テスト（モック 429・トークン超過）で自動担保し、**実 API 検証は手順書＋チェックリストを用意してユーザーが任意実行・結果記録**する。
- **D-08:** **検証手順書はフェーズ内（`.planning/phases/03-ocr-a/`）にチェックリスト形式で 1 ファイル作成**（手順・期待結果・結果記入欄）。GSD の検証フロー（UAT/VERIFICATION）と整合させ、ユーザーが実行後にチェックを埋める。開発履歴.md やテスト docstring には集約しない。
- **D-09:** **追加する自動テストはギャップのみ**。`clamp_retry_after`・サーキットブレーカー・指数バックオフ・Retry-After 優先は既にテスト済み（test_ocr.py:1860+/2357+ 等）のため重複させない。まず **max_tokens「クランプ」の実在を確認**（現状コードは settings 値の素通しに見える）し、未テストの振る舞い（クランプ境界・必要ならモック 429/トークン超過の統合ケース）のみ追加する。

### H2 API キー秘匿監査（V16-QUAL-02）
- **D-10:** **証跡は「回帰テスト＋監査チェックリスト文書」の両立**。設定ファイル経路は既に test_settings_keyguard.py で手厚いため、ギャップである **ログ平文露出**と**ソース埋め込み**を回帰テスト化し、並行してフェーズ内に 3 経路（設定ファイル・ソース・ログ）の監査チェックリスト文書（確認項目＋結果）を残す。
- **D-11:** **ログ非出力は caplog ベースの回帰テスト**で担保する。主要経路（`_save_settings`・各プロバイダ・`_resolve_api_key`・セッションキー入力）でログにキー値が出ないことをアサート（テスト経路の精緻化は実装裁量）。
- **D-12:** **ソース埋め込み防止は自動スキャンテスト**で担保する。ソースを走査してキーらしいパターン（`sk-ant-`・`AIza`・長い base64 リテラル等）が無いことを pytest でアサートし、将来の誤コミットを構造的に防ぐ。テストデータ内のダミーキー誤検知を避ける除外設計は実装裁量。

### Claude's Discretion
- D-06 の待機秒数の表示文言・桁丸め（「約 5 秒」「5s」等）は LANG 規約（ja/en 同一キー）に従い実装裁量。
- D-09 のモック 429/トークン超過統合ケースを「追加する/既存で足りる」の最終判断は、max_tokens クランプ実在確認の結果を見て researcher/planner が決めてよい。
- D-11 の caplog テストでカバーする具体的な関数/モジュールの粒度は実装裁量（ただし最低限 `_save_settings` と全クラウドプロバイダを含む）。
- D-12 の検出パターン・除外（テストフィクスチャ/ダミーキー）の実装方式は裁量。ただし「実キーがソースに無いことを CI で再発防止できる」ことは必須。
- 検証手順書（D-08）のファイル名・章立ては GSD 慣習に合わせて裁量。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・マイルストーン
- `.planning/ROADMAP.md` §"Phase 3: 体感品質・回転プレビュー & OCR 堅牢性（プランA）" — Goal と Success Criteria 4 項目
- `.planning/REQUIREMENTS.md` — V16-QUAL-01〜04 の要件本文
- `.planning/PROJECT.md` §"Current Milestone: v1.6.0" — プランA（H1/H2/H5/M1）の Key context・H5「実 API での検証が残課題」
- `.planning/STATE.md` §Blockers/Concerns — 「V16-QUAL-03 は実 API/実機相当の検証手順が前提・検証手順と結果記録の方法を計画時に確定」

### H1 回転即時反映（編集対象コード）
- `pagefolio/page_ops.py` §`_rotate_selected`（80-91）— `set_rotation` → `_invalidate_thumb_cache(targets)` → `_refresh_all()`。即時反映バグの起点。
- `pagefolio/viewer.py` §`_render_preview_pixmap`（50-59）/`_show_preview`（61-115）/`_refresh_all`（218-252）/`_invalidate_thumb_cache`（136-141）/`_get_thumb_photo`（143-154）— プレビュー・サムネイル再描画経路。バグの所在候補。

### M1 エラー UX（編集対象コード）
- `pagefolio/ocr_providers.py` §`OCRRetryableError`（68-）/各 provider の `ocr_image`（Claude/Gemini）— **`stop_reason`/`finishReason` 未検査**。途切れ検出をここに追加（D-05）。
- `pagefolio/ocr_dialog.py` §`_finish_error`（1497-）/`_append_resume_hint`（1530-）/エラー kind 分岐/`CB_CONSECUTIVE_FAILURES`（49）— パネル内提示の強化箇所。
- `pagefolio/ocr.py` §`clamp_retry_after`/`RETRY_AFTER_CAP`（54-67）/`run_parallel` 内の待機（273-298, 418-444）— 待機秒数を待機文言へ渡す経路（D-06）。
- `pagefolio/lang.py` §`ocr_err_*`/`ocr_waiting_retry`・`ocr_waiting_retry_server`（346-349）/`ocr_resume_hint`（408）— 新規/改訂文言（ja/en 同一キー）。

### H5 max_tokens/429 検証（対象コード・テスト）
- `pagefolio/ocr.py` §`MAX_RETRIES`（51）/`clamp_retry_after`（58-67）/max_tokens 受け渡し（520/529/535/546/552/604/663）
- `pagefolio/ocr_providers.py` §各 provider の `max_tokens`（LMStudio=-1 既定・Claude/Gemini=4096 既定）
- `tests/test_ocr.py` — 既存の max_tokens payload テスト（108-117）・run_parallel バックオフ群（629-）・clamp_retry_after（1860-）・サーキットブレーカー（2357-）。**重複回避の参照元**。

### H2 キー秘匿監査（対象コード・テスト）
- `pagefolio/settings.py` §`_SENSITIVE_KEYS`（17-）/`_save_settings`（83-）— 機密キー除外・キー名のみログ。
- `pagefolio/ocr.py` §`_resolve_api_key`（os.environ 読み取り専用）・セッションキー（`_session_api_keys`）
- `tests/test_settings_keyguard.py` — 既存の settings-file キーガードテスト（各キー非保存・値非出力・dict 非変更）。**拡充の起点**。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_refresh_all` / `_show_preview` 経路**: 回転後の再描画は既に呼ばれている。バグは「呼ばれているのに反映されない」点にあり、修正は経路の追加ではなく原因除去になる見込み（D-01）。
- **`_invalidate_thumb_cache(targets)` + thumb_cache（全ページ index キー）**: サムネイル即時反映（D-02）の土台は既にある。
- **`ocr_err_*` / `_finish_error` の kind 分岐 / `_append_resume_hint`**: 「状況＋次アクション」文言と部分成功の再開導線が既に実装済み。M1 はこの作法を踏襲して途切れ文言（D-05）と待機秒数（D-06）を足す。
- **`clamp_retry_after` / `RETRY_AFTER_CAP=60s` / 指数バックオフ / サーキットブレーカー**: 堅牢化ロジックは実装済み＆テスト済み。H5 は新規実装ではなく検証＋ギャップ補完（D-09）。
- **`_SENSITIVE_KEYS` ガード + test_settings_keyguard.py**: 設定ファイル経路の秘匿は確立。H2 はログ/ソース経路へ拡張（D-10〜D-12）。
- **LANG（ja/en 同一キー）規約**: M1 の新規文言はこの規約に従う。

### Established Patterns
- プレビュー/サムネイル描画は `_preview_gen`/`_thumb_gen` 世代カウンタ＋`root.after` 連鎖の逐次レンダリング。回転即時反映の修正も世代ガードを壊さないこと。
- ページネーション窓（Phase 2 導入）と整合: `_refresh_all` は `reconcile_window_start` で窓正規化してから `_build_thumbnails`/`_show_preview` を呼ぶ。回転は `current_page` を移動しないため窓追従への影響は小さいが、選択サムネイル即時反映は「現在の窓内に見えているサムネイルのみ再描画される」点に留意。
- プロバイダ応答は JSON を直接パースしてテキスト抽出。途切れ検出（D-05）は抽出箇所の隣で `stop_reason`/`finishReason` を読むだけで足りる見込み。

### Integration Points
- **回転即時反映の修正は viewer/page_ops に閉じる**。OCR 系（M1/H5/H2）とは独立に進められる（並行プラン化の余地）。
- **M1 の途切れ検出はプロバイダ層 → OCRDialog 表示層へ伝搬**。`ocr_image` の戻り（テキスト）に途切れフラグをどう載せるか（戻り値拡張 or 例外/属性）は要設計。
- **H2 のログ/ソーステストは全モジュール横断**。caplog テストは provider/settings/ocr を跨ぐ。
- **H5 検証手順書はテスト（自動）と UAT（手動・実 API）の橋渡し**。GSD verify フローへ接続。

</code_context>

<specifics>
## Specific Ideas

- 回転 → その場でプレビューが回る（ページ送りや再読込を待たない）。複数選択一括回転ならサムネイルも揃って回る。
- max_tokens で切れたら「途切れました／max_tokens を増やして再実行」と当該ページに明示し、取れた分のテキストは捨てない。
- レート制限待機は「約 N 秒待機（リトライ n/max）」のように残り待ち時間が見える。
- ソースに実 API キーが紛れたら CI（pytest）で落ちる。

</specifics>

<deferred>
## Deferred Ideas

- エラーの messagebox 能動通知 → 今回はパネル内提示の強化を採用（D-04）。将来、見逃しが問題化したら能動通知を別途検討。
- トークン超過途切れの「自動 max_tokens 引き上げ再試行」→ 今回は検出＋ユーザー案内のみ（自動再試行はスコープ外）。
- 実 API 検証の CI 自動化 → 課金・不安定のため不採用。手順書＋手動実行に留める（D-07）。
- OCR 出力の Markdown 整形・プロバイダ別プロンプト最適化 → **Phase 4（プランC）**。

None outside scope beyond the above — discussion stayed within phase boundary.

</deferred>

---

*Phase: 3-体感品質・回転プレビュー & OCR 堅牢性（プランA）*
*Context gathered: 2026-06-19*
