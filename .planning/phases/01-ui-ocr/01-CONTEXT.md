# Phase 1: 設定/UI 改善（OCR パラメータ一元化・スライダー配置） - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

OCR パラメータ設定の二重入力を解消し、設定を一意に解決できるようにする。加えてサムネイルサイズ変更スライダーを、左ペインを縮小しても常に使える位置・幅で表示する。**UI 層中心の改善であり、新しい OCR 機能やページ操作機能の追加は対象外。**

対象要件: V16-UI-01（OCR パラメータ一元化）, V16-UI-02（スライダー配置）

</domain>

<decisions>
## Implementation Decisions

### OCR パラメータ二重化の解消方式（V16-UI-01）
- **D-01:** OCR 抽出画面（`OCRDialog`）の数値パラメータ UI（scale / timeout / max_tokens / temperature、および LM Studio の url / model）は**読み取り専用表示**にする。完全撤去ではなく「現在適用される値が見える」状態を維持する（「今何が効くか」が分かる方を優先）。
- **D-02:** これらパラメータの**編集導線は「⚙ LLM 設定…」ボタン（`LLMConfigDialog`）に一元化**する。OCR 抽出画面では編集不可。OCR 画面に既存の「⚙ LLM 設定…」ボタンがあるため、新規導線の追加は不要。
- **D-03:** LLM 設定ダイアログで値を変更し OK/適用した直後、OCR 画面の読み取り専用表示も**即時反映**する。既存の `OCRDialog._apply_llm_settings`（設定適用経路）を活用して表示を再描画する。
- **D-04:** 「読み取り専用化」と「撤去」の選択は要件 V16-UI-01 の "廃止または読み取り専用化" に沿う。本フェーズでは読み取り専用化を採用。

### 一元化対象の線引き（V16-UI-01）
- **D-05:** 一元化（＝読み取り専用化）の対象は、`LLMConfigDialog` と重複している**永続的な数値パラメータに限定**する（scale / timeout / max_tokens / temperature / url / model）。
- **D-06:** OCRDialog 固有の**実行時オプションは編集可能のまま OCR 画面に残す**:
  - プロンプトプリセット（`preset_var`）
  - 埋め込みテキスト無視（`force_ocr_var`）
  - セッション API キー入力（`api_key_var`、`_session_api_keys` 経由・settings 非永続）
  これらは「実行ごとに変える値」であり二重化の対象ではない。

### サムネイルスライダーの配置（V16-UI-02）
- **D-07:** 実際の問題は「スライダーが全選択/解除ボタンと同一行（`sel_frame`, `side="right", fill="x", expand=True`）にあり、**左ペインを縮小するとボタンと幅を奪い合って細くなり操作できなくなる**」こと。位置自体はボタン付近にあるが、幅が確保されない点が課題。
- **D-08:** 目標レイアウト: 全選択/解除ボタン行の**下に独立した行**を新設し、スライダーを `fill="x"` で**全幅配置**する。ボタンと幅を競合させず、狭いペイン幅でもスライダー幅を確保する。
- **D-09:** スライダーの機能（範囲 0.5〜2.5・`thumb_zoom_var`・`_on_thumb_zoom_release` での設定保存と再描画）は従来どおり維持する。配置変更のみで挙動は変えない。

### Claude's Discretion
- 読み取り専用フィールドの見た目（`state="readonly"` / `disabled` / ラベル表示への置換など）の具体的手段は実装時に最適なものを選んでよい。ただし「現在値が読める」ことは必須（D-01）。
- スライダー独立行に倍率表示やアイコンを添えるかは任意（要件外の装飾。最小実装は配置変更のみ）。
- プロバイダ非依存パラメータ（url / model は LM Studio 固有）について、選択中プロバイダに応じて表示を出し分けるかは実装裁量。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・マイルストーン
- `.planning/ROADMAP.md` §"Phase 1: 設定/UI 改善" — Goal と Success Criteria 4 項目
- `.planning/REQUIREMENTS.md` — V16-UI-01 / V16-UI-02 の要件本文
- `.planning/PROJECT.md` §"Current Milestone: v1.6.0" — S1（OCR パラメータ一元化）/ S2（スライダー配置）の Key context

### 実装対象コード（本フェーズで編集する中核）
- `pagefolio/ocr_dialog.py` — `OCRDialog`。数値パラメータ Spinbox 群（scale_var:319-331 / timeout_var:339-351 / max_tokens_var:359-371 / temperature_var:386-398、url_var:259-269 / model_var:285-291）。実行時読込は `_on_run`（1041-1137 付近）、設定適用は `_apply_llm_settings`（799 付近）。残す実行時 UI: preset_var:225-241 / force_ocr_var:416-426 / api_key_var:439-449。
- `pagefolio/dialogs/llm_config.py` — `LLMConfigDialog`。一元化先の永続設定 UI（ocr_scale_var / ocr_timeout_var / ocr_max_tokens_var / ocr_temperature_var / lm_url_var / lm_model_var など）。保存は `_apply`（838-908 付近）。
- `pagefolio/ui_builder.py` §`_build_thumb_panel`（173-209）— スライダー `thumb_zoom_scale`（201-208、`sel_frame` 内 side="right"）。全選択/解除ボタンは 193-198、`hdr`「ページ一覧」ラベルは 174-189。
- `pagefolio/viewer.py` — `_on_thumb_zoom_release`（146-154、設定保存＋`_refresh_all`）/ サムネイル生成での倍率参照（137-139）。
- `pagefolio/settings.py` — `DEFAULT_SETTINGS`（ocr_scale / ocr_timeout / ocr_max_tokens / ocr_temperature / ocr_concurrency 等、45-76）と `_SENSITIVE_KEYS`（17-26）。

### 関連経緯
- `.planning/STATE.md` §"Decisions"（260607-ccz: OCR 画面へ「⚙ LLM 設定…」ボタン追加・ライブ更新の経緯）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **「⚙ LLM 設定…」ボタン + `_apply_llm_settings` 経路**: OCR 画面から `LLMConfigDialog` を開き、適用後に設定をライブ反映する仕組みが既にある（quick task 260607-ccz）。D-02/D-03 の「編集導線一元化」「即時反映」はこの既存経路を拡張して実現できる。
- **`sel_frame` レイアウト**: スライダーは既に同フレーム内にあるため、独立行（新規 `tk.Frame`）を `sel_frame` の直後に `pack(fill="x")` で追加し、スライダーを移すだけで D-08 を満たせる。
- **テーマ辞書 `C` / `self._font()`**: 新規ウィジェットも既存規約（`C["BG_PANEL"]` 等・`self._font(delta)`）に従う。

### Established Patterns
- 設定の永続化は `_save_settings()` 経由で `pagefolio_settings.json` に保存（API キーは `_SENSITIVE_KEYS` ガードで非保存）。読み取り専用化は表示のみで、保存ロジックは LLMConfig 側に集約済み。
- LANG 文言は ja/en 両辞書に同一キーで追加する（`pagefolio/lang.py`）。読み取り専用ラベルや新規文言が必要な場合はこの規約を守る。

### Integration Points
- OCRDialog の読み取り専用表示と LLMConfigDialog の永続値の間は `app.settings` を単一の真実とする。OCR 画面は settings（または LLMConfig 適用結果）を表示するだけにする。
- スライダー配置変更は `_build_thumb_panel` 内の pack 構造変更に閉じる。`thumb_zoom_var` / コールバックの参照は不変。

</code_context>

<specifics>
## Specific Ideas

- 読み取り専用表示は「グレーアウトした現在値」を想定（編集不可だが値は読める）。OCR 実行前に「今どの設定で走るか」がユーザーに見えることが重要。
- スライダーは「ボタン行の下の独立行に全幅」が確定形。狭いペインでも潰れないことが最優先。

</specifics>

<deferred>
## Deferred Ideas

- 大量ページのページネーション表示（S3 / V16-UI-03）→ **Phase 2**（高リスクのため隔離済み）。
- スライダーへの倍率数値表示・サイズアイコン等の装飾は要件外。最小実装で見送り、必要なら別途軽微タスク化。
- 回転プレビュー即時反映・OCR エラー UX（プランA）→ **Phase 3**。
- OCR 出力の Markdown 整形・プロバイダ別プロンプト（プランC）→ **Phase 4**。

None outside scope beyond the above — discussion stayed within phase boundary.

</deferred>

---

*Phase: 1-設定/UI 改善（OCR パラメータ一元化・スライダー配置）*
*Context gathered: 2026-06-18*
