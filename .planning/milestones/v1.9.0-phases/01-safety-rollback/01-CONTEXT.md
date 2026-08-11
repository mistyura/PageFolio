# Phase 1: 保存・編集・設定の安全性是正（失敗時ロールバック担保） - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

保存・複数ファイル挿入・ページ複製・LLM 設定 UI 操作・Undo/Redo のいずれかが失敗しても、Document・Undo 履歴・外部ファイルが確実に操作前の状態へ戻ること、および OCR OFF が通常 OCR・バッチ OCR・プラグイン経路すべてで一貫した意味を持つことを確立する。

**対象要件（9件）:** V190-SAFE-01, V190-SAFE-02, V190-SAFE-03, V190-SAFE-04, V190-SAFE-05, V190-CFG-01, V190-CFG-02, V190-UNDO-01, V190-UNDO-02

**このフェーズに含まれないもの:**
- OpenAI プロバイダ追加・プロバイダ catalog 一元化（Phase 2）
- Tkinter 実行環境修復・保存トースト再試行時の上書き確認再表示・human-verify/UAT（Phase 3）
- Undo 記録が先置きのまま残る他 op（rotate/crop/delete 等）への水平展開（Deferred 参照）

</domain>

<decisions>
## Implementation Decisions

### 保存時の暗号化契約（V190-SAFE-01 / V190-SAFE-02）

- **D-01:** パスワード保護 PDF の「名前を付けて保存」は**無確認で常に暗号化を維持**する。`_save_as()` の `self.doc.save(path)` に `encryption=fitz.PDF_ENCRYPT_KEEP` を無条件付与する。暗号化解除は既存の「🔒 パスワード → 解除」（`_remove_password` / `save_without_password`）だけで発生させる。平文コピーが欲しいユーザーは解除メニューを使う。確認ダイアログは追加しない（「解除は明示操作でのみ」という V190-SAFE-02 の契約を弱めないため）。
- **D-02:** `_overwrite_current_file(path, **save_kwargs)` は **`encryption` 未指定時に `PDF_ENCRYPT_KEEP` を関数内で既定化**する（呼び出し側での明示は採らない）。将来この関数へ新しい保存経路が増えても平文化事故が構造的に起き得ない安全側デフォルトにするため。`_set_password`（`PDF_ENCRYPT_AES_256`）/ `_remove_password`（`PDF_ENCRYPT_NONE`）は明示的に kwargs を渡しているので影響を受けない。
- **D-03:** 保存後の `self.pdf_has_password` は**保存 kwargs から論理的に導出**する（`KEEP` → 現在値を維持 / `AES_256` → True / `NONE` → False）。単一のヘルパーに閉じ、実行時に保存先を開き直す I/O は発生させない（Core Value の大 PDF 性能を守る）。
  - ただし**回帰テスト側では保存先 PDF を実際に開いて `needs_pass` を検証**し、導出ロジックの正しさを機械保証する（レビュー推奨対応「暗号化 PDF の Save As とインクリメンタル保存失敗フォールバックの回帰テストを追加」由来・要件必達項目）。

### OCR OFF の一貫化（V190-SAFE-03）

- **D-04:** OCR プロバイダが `off` のとき、ツールメニューの「バッチOCR」項目自体を **`disabled` にして起動できなくする**（ダイアログを開いてから止めるのではなく、入口で止める）。
- **D-05:** disabled の理由は **OFF の間だけメニューラベルへ「（OCR OFF）」を併記**して伝える（Tk の disabled メニュー項目はクリックイベントを取れないため、ダイアログやツールチップでの説明は使えない）。i18n 文言を日英 1 件ずつ追加する。
- **D-06:** `build_provider()` は **`off` のみを専用例外で拒否**する（OCR 無効を表す専用例外型を新設し、`("lmstudio", "", "off")` の同列扱いから `off` を外す）。**空文字 `""` は従来どおり LM Studio として後方互換を維持**する（`ocr_provider` キーを持たない旧 `pagefolio_settings.json` のユーザーが突然 OCR を使えなくなるのを避けるため）。`None` 返却案は不採用（チェック漏れが遠い場所の AttributeError として現れるため）。 — **Reversibility:** costly — `off` を例外化すると `build_provider` の全呼び出し元（通常 OCR・バッチ OCR・フォールバック・プラグイン経路）が例外ハンドリング前提になり、Phase 2 の OpenAI 追加もこの契約の上に載る。戻すには全呼び出し元の再修正が必要。
- **D-07:** OFF ガードは「`settings["ocr_provider"]` が `off` なら OCR 実行経路に一切入らない」という単一の意味で通常 OCR・バッチ OCR・プラグイン登録プロバイダ経路すべてに適用する。バッチ OCR は起動時（D-04）と `_on_start_batch` の実行開始時の二重ガードとする。

### 失敗時ロールバックの方式と通知（V190-SAFE-04 / V190-SAFE-05 / V190-UNDO-01 / V190-UNDO-02）

- **D-08:** 複数ファイル挿入（`page_ops.py:_do_insert`）は**挿入済みページ数を追跡し、例外時に `delete_page` で巻き戻す**方式にする。一時 Document へ全入力を結合してから本体へ 1 回で反映する案は**不採用**（挿入ファイル群を丸ごとメモリに抱えるため、大量ページ投入時にピークが乗り Core Value を損なう）。件数によるハイブリッドも不採用（失敗経路が 2 本になりテスト・保守コストが倍増するため）。
- **D-09:** 挿入元 Document は `try/finally` で**必ずクローズ**する（現状は `src.close()` が正常系にしかなく、`insert_pdf()` 例外時にリークする）。
- **D-10:** 巻き戻し自体が失敗した場合（挿入は残ったが `delete_page` も例外）は、**警告ダイアログで残存ページ数を明示**し、**実際の挿入数を反映した Undo state は残す**（ユーザーに Ctrl+Z という復旧手段を残すため）。無警告で部分適用を残すことはマイルストーン共通の受け入れ条件に反するため許容しない。
- **D-11:** ページ複製（`page_ops.py:_duplicate_page`）は **`_save_undo("duplicate")` を実処理の成功後に確定**させる（現状は実処理より先に呼んでおり、複製前に例外が出ると不正な Undo 履歴が残って別ページを削除し得る）。
- **D-12:** 「Undo 記録の後置」パターンの適用は**今回は要件対象の duplicate / insert の 2 経路のみ**に留める。あわせて**全 op を棚卸しして「記録が先置きのままの op 一覧」を SUMMARY に記録**し、次マイルストーン候補として残す。共通コンテキストマネージャの新設と全 op 一斉適用は Phase 1 の変更面と回帰リスクを広げすぎるため不採用。
- **D-13:** Undo/Redo（`file_ops.py:_undo` / `_redo`）の復元失敗時は、**pop した状態をスタックへ戻したうえで messagebox のエラーダイアログでブロック通知**する。トースト・ステータスバーは不採用（復元失敗は稀かつ重大で、見落とされると壊れた前提のまま編集が続くため）。
- **D-14:** スタックへ戻す際は既存の Blob ライフサイクル規約を厳守する（`_push_evicting` / `_clear_redo_stack` 経由・失敗した state の Blob は dispose しない）。あわせて `_do_insert` の例外処理にある `self._undo_stack.pop()` という**直接操作も規約違反として同時に是正**する（Blob リーク経路）。

### 設定 UI の Apply/Cancel 契約（V190-CFG-01 / V190-CFG-02）

- **D-15:** 外部プロンプトファイル（`ocr_custom_prompt.md` / `ocr_summary_prompt.md`）への書き込みを **Apply 押下時へ一本化**する（`sections.py:_on_template_change` 内の `save_prompt_file()` 即時呼び出しを撤去）。REQUIREMENTS.md で確定済みの方針であり、ライブ連動＋Cancel 復元案は Out of Scope。
- **D-16:** Apply 時に書き込む内容は**入力欄の現在値**とする（アクティブテンプレートの保存済み値ではない）。ダイアログを閉じる瞬間に画面で見えていた内容がそのままファイルへ反映される WYSIWYG 挙動にし、テンプレートを選ばずに自由入力したケースも自然に扱えるようにする。v1.8.0 D-07 の「外部ファイル＝アクティブテンプレートのライブ編集内容」不変条件は、Apply 一本化に伴い「Apply 時点の入力欄内容」へ置き換わる。
- **D-17:** Apply 時に外部ファイルが存在しない場合は**新規作成しない**（`prompt_file_exists()` ガードを維持し、存在するファイルのみ更新する）。外部ファイルを使っていないユーザーの作業ディレクトリに md が勝手に増えるのを避け、既存のオプトイン仕様を保つため。
- **D-18:** テンプレート切替時の未保存判定（`_has_unsaved_template_changes`）は、アクティブテンプレート選択済みの場合に**常に入力欄と `get_template()` の保存済み値を比較**する（`prompt_file_exists()` による分岐を削除し判定経路を 1 本にする）。アクティブテンプレート未選択時の「自由入力の有無だけを見る」既存ロジックは維持する。外部ファイル内容を基準に加える案は判定経路が 2 本に戻り同型バグの再発余地が残るため不採用。
- **D-19:** LLM 設定画面の外部ファイルに関する注記文言は**変更しない**。「適用時に保存」という既存表示はもともと正しく、実装が文言に追いつくだけであるため i18n 差分はゼロ。

### Claude's Discretion

- LLM 設定 Apply 直後にツールメニューの「バッチOCR」項目を再評価する配線方法（既存の `_update_ocr_buttons_state()` と同じタイミングで再評価するのが素直。`.planning/codebase/CONCERNS.md`「OCRDialog LLM Settings Callback Consistency」と同型の課題なので、この機会に配線を揃える）
- OCR 無効を表す専用例外の型名・配置（`ocr_providers/errors.py` に置くか `ocr.py` に置くか）
- 挿入失敗時のエラーメッセージに失敗ファイル名・成功件数をどこまで含めるか
- `duplicate` / `merge` / `merge_resize` の 4 手往復回帰テスト（V190-UNDO-02）のテストファイル配置と粒度（既存 `tests/test_pdf_ops.py` の insert/delete 4 手往復テストと同型に揃えるのが素直）
- プラン分割の粒度（保存系 / OCR OFF 系 / ロールバック系 / 設定 UI 系のどこで切るか）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・スコープの一次情報
- `.planning/REQUIREMENTS.md` — V190-* 全 27 要件の定義。Phase 1 は SAFE-01〜05 / CFG-01・02 / UNDO-01・02 の 9 件。**Out of Scope 表**（Document 全体スナップショット方式・ライブ連動＋Cancel 復元案・部分適用の無警告許容など）も必読
- `.planning/ROADMAP.md` §「Phase 1」 — Goal と 5 つの Success Criteria（何が TRUE になれば完了か）
- `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md` — **本フェーズ全要件の出典**。V190-REV-01〜07 の詳細、再現手順、推奨対応、根拠となるファイル:行番号がすべてここにある。プラン作成前に §3 を通読すること

### アーキテクチャ制約（違反すると壊れる）
- `CLAUDE.md` §「既知の制限・注意事項」/ §「変更時のチェックリスト」 — Undo Blob ライフサイクル、CropBox クランプ、リント/テスト必須、日本語ルール
- `pagefolio/CLAUDE.md` — モジュールごとの責務、OCR・LLM の注意事項
- `.planning/PROJECT.md` §「Key Decisions」 — V14-D-01/02/03（urllib 直叩き・APIキー非永続・既定 `off`）、V180-D-01（registry.py 独立性）、V180-D-17（`insert_redo` 対称パターン）
- `.planning/codebase/CONCERNS.md` §「Fragile Areas」 — Undo/Redo Blob ライフサイクル管理（`_push_evicting` 経由必須・`deque.append`/`clear` 直接禁止）、OCRDialog LLM Settings Callback Consistency
- `.planning/codebase/CONCERNS.md` §「Missing Critical Features」 — duplicate/merge/merge_resize の 4 手往復テスト欠落（V190-UNDO-02 の直接の出典）

### 実装対象コード（レビューが指摘した箇所）
- `pagefolio/file_ops.py:626-646, 648-673, 688-708` — `_save_file` / `_save_as` / `_overwrite_current_file`（D-01〜D-03）
- `pagefolio/file_ops.py:175-197` — `_undo` / `_redo`（D-13・D-14）
- `pagefolio/file_ops.py:19-33, 795-845` — `save_with_password` / `save_without_password` / `_set_password` / `_remove_password`（明示操作側。D-01 の対比対象）
- `pagefolio/page_ops.py:177-193` — `_duplicate_page`（D-11）
- `pagefolio/page_ops.py:756-790` — `_do_insert`（D-08〜D-10・D-14）
- `pagefolio/ocr.py:431-441` — `build_provider` の `off` 扱い（D-06）
- `pagefolio/app.py:314-318` — `_open_batch_ocr`（D-04・D-05）
- `pagefolio/dialogs/batch_ocr.py:627-650` — `_on_start_batch`（D-07）
- `pagefolio/dialogs/llm_config/sections.py:1142-1151, 1158-1185, 1207-1247` — 外部ファイル即書き・`_has_unsaved_template_changes`・`_on_template_change`（D-15〜D-19）
- `pagefolio/dialogs/llm_config/dialog.py:445-469` — Apply ハンドラ（D-15・D-16）

### 既存テスト（拡張対象）
- `tests/test_password.py` — 通常保存経路の暗号化維持テストが**ない**（D-01〜D-03 の追加先）
- `tests/test_provider_ui.py:2249-2297` — 未選択状態の自由入力の未保存確認テストはあるが、選択済みテンプレート編集ケースが未カバー（D-18 の追加先）
- `tests/test_pdf_ops.py` — insert/delete の 4 手往復テストが既存。duplicate/merge/merge_resize を同型で追加する（V190-UNDO-02）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `save_with_password()` / `save_without_password()`（`file_ops.py:19-33`）: パスワード付与・解除が既に独立関数＋独立メニューに分離済み。D-01 で Save As に `PDF_ENCRYPT_KEEP` を無条件付与しても、これらの明示操作とは衝突しない
- `_overwrite_current_file()`: 「メモリへシリアライズ → close → tmp 経由 os.replace → 開き直し、失敗時は bytes から復元して再送出」というロールバック済みの実装。D-02 の既定値変更以外は触らなくてよい
- `_push_evicting` / `_clear_redo_stack` / `_dispose_state` / `_blob_bytes`（`file_ops.py`）: Undo スタック操作の正規 API。D-13・D-14 はこれらの上に載せる
- `ToastManager`（v1.8.0 QA-02・再試行アクション付き非モーダル通知）: 既存の保存失敗系で使用中。ただし本フェーズの Undo 復元失敗は D-13 で messagebox を選択したため流用しない
- `_update_ocr_buttons_state()`（`app.py`）: OCR ボタンの活性制御。D-04 のメニュー再評価はここに相乗りするのが素直

### Established Patterns
- **Undo Blob ライフサイクル規約**: スタックへの直接 `append`/`pop`/`clear` は禁止（Blob リーク）。`_do_insert` の例外処理が既にこれを破っており、D-14 で是正する
- **op 別逆デルタによる対称 Undo/Redo（BUG-02・V180-D-17）**: `doc.tobytes()` による全体スナップショットは全廃済み。ロールバック実装でこれを復活させてはならない（REQUIREMENTS.md の Out of Scope にも明記）
- **fitz メインスレッド制約（V14-D-05/06）**: `get_pixmap()` およびロールバック時の `delete_page` を含む Document 操作はメインスレッドで行う
- **i18n 文言は `pagefolio/lang.py` に日英ペアで追加**（未使用キーの回帰テストが常設・V171-D-11）
- **ダイアログ内 nested Apply は `_apply_llm_settings_live` 経由**（`_rebuild_ui()` を呼ばない・V171-D-14）。D-15/D-16 の Apply 改修はこの経路と整合させる

### Integration Points
- `app.py` のツールメニュー構築（`_open_batch_ocr` 周辺）↔ `settings["ocr_provider"]` の変更通知（D-04・D-05・裁量項目のメニュー再評価配線）
- `ocr.py:build_provider` ↔ 通常 OCR（`ocr_dialog.py` / `ocr_engine.py`）・バッチ OCR（`dialogs/batch_ocr.py`）・フォールバック（`ocr_fallback.py`）・プラグイン登録経路。D-06 の例外化は全呼び出し元に波及する
- `dialogs/llm_config/dialog.py` の Apply ハンドラ ↔ `sections.py` のテンプレート UI ↔ 外部 md ファイル I/O（D-15〜D-18）
- `page_ops.py` の編集操作 ↔ `file_ops.py` の Undo スタック（D-08〜D-14 はこの境界をまたぐ）

</code_context>

<specifics>
## Specific Ideas

- 「安全側デフォルト」を**関数の既定値として構造に埋め込む**方針が一貫して選ばれた（D-02 の `PDF_ENCRYPT_KEEP` 既定化、D-18 の判定経路 1 本化）。「呼び出し側で毎回明示」「分岐を残す」案は、いずれも今回のバグと同型の付け忘れ・見落としが再発し得るという理由で退けられている。プラン・実装でも同じ判断基準を適用すること
- 実行時コストは Core Value（大 PDF での Undo/Redo 性能）を基準に判断された。D-03（保存先の再オープン検証を採らない）と D-08（一時 Document 全件構築を採らない）はどちらもメモリ・I/O ピークを理由にした選択
- 変更面の広さは意図的に抑えられた。D-12（後置パターンを対象 op のみに留める）・D-19（文言据え置き）は「Phase 1 のフェーズ境界を守る」判断であり、planner が親切心でスコープを広げないこと

</specifics>

<deferred>
## Deferred Ideas

- **Undo 記録が先置きのまま残る他 op（rotate / crop / delete / bulk_move / bulk_crop / merge 等）への「記録後置」パターン水平展開** — 今回は棚卸し一覧を SUMMARY に記録するのみ。共通コンテキストマネージャ化を含めて次マイルストーン候補（D-12）
- **Save As 時に平文コピーを作る専用導線** — D-01 で「解除は明示操作のみ」を選択したため不要と判断。将来ユーザーから要望が出た場合に再検討

</deferred>

---

*Phase: 1-保存・編集・設定の安全性是正（失敗時ロールバック担保）*
*Context gathered: 2026-08-10*
