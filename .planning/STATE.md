---
gsd_state_version: 1.0
milestone: v1.7.1
milestone_name: 現機能ブラッシュアップ + APIキー入力欄
current_phase: 01
current_phase_name: api-llm
status: executing
stopped_at: Completed 01-03-PLAN.md
last_updated: "2026-07-04T17:06:59.776Z"
last_activity: 2026-07-04
last_activity_desc: Phase 01 execution started
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-04)

**Core value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする
**Current focus:** Phase 01 — api-llm

## Current Position

Phase: 01 (api-llm) — EXECUTING
Plan: 3 of 3
Status: Ready to execute
Last activity: 2026-07-04 — Phase 01 execution started

Progress: [░░░░░░░░░░] 0%

## v1.7.1 Phase Map

| Phase | Name | Requirements | リスク/性質 |
|-------|------|--------------|------------|
| 1 | APIキー入力欄（LLM設定への一元化） | V171-KEY-01〜04, V171-TEST-02 | LLMConfigDialog / OCRDialog / ocr.py のキー解決に閉じたまとまり。優先順反転（入力値→環境変数）＋ 非保存ガード維持 |
| 2 | OCR 磨き込み（レビュー残の現行照合と二重実装解消） | V171-OCR-01〜04 | **高リスク**: OCR-04（L-1 producer-consumer 一本化）は独立プランへ隔離。L 系は計画時に現行コード照合で活き残り確定 |
| 3 | ページ操作磨き込み + v1.5.0 回帰テスト | V171-PAGE-01〜03, V171-TEST-01 | page_ops/redact_ops 面。PAGE-02/03 は「棚卸し→改善」型（具体項目は計画時確定）。TEST-01 は同面の回帰テスト |
| 4 | UI/UX 磨き込み + 既知バグ棚卸し | V171-UIUX-01〜03, V171-TEST-03 | dialogs/lang 面。UIUX-01（ショートカット GUI）は Phase 3 の読込回帰テスト整備後。TEST-03 は最終スイープ |

## Performance Metrics

**Velocity (v1.3.0 実績):**

- Total plans completed: 17
- Average duration: 約 22.5 分
- Total execution time: 約 45 分

**By Phase (v1.3.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01 | 3 | - | 約 22.5 分 |
| Phase 02 | 3 | - | - |
| Phase 03 | 2 | - | - |
| 06 | 4 | - | - |
| 07 | 1 | - | - |
| 01 | 2 | - | - |

*v1.4.0 フェーズ完了後に追記*
| Phase 04-provider-abstraction P01 | 3min | 2 tasks | 2 files |
| Phase 04-provider-abstraction P02 | 8min | 2 tasks | 4 files |
| Phase 04-provider-abstraction P03 | 6min | 2 tasks | 3 files |
| Phase 04-provider-abstraction P04 (gap) | 10min | 3 tasks | 4 files |
| Phase 05-claude-provider-ui P01 | 25 | 3 tasks | 2 files |
| Phase 05-claude-provider-ui P02 | 10min | 3 tasks | 3 files |
| Phase 05-claude-provider-ui P03 | 30min | 3 tasks | 3 files |
| Phase 05-claude-provider-ui P04 | 30min | 3 tasks | 3 files |
| Phase 06-gemini-provider P01 | 6min | 3 tasks | 4 files |
| Phase 06-gemini-provider P02 | 20min | 3 tasks | 3 files |
| Phase 06-gemini-provider P03 | 12min | 3 tasks | 9 files |
| Phase 06-gemini-provider P04 (gap) | 6min | 3 tasks | 5 files |
| Phase 01-ui-ocr P01 | 約25分 | 2 tasks | 3 files |
| Phase 01-ui-ocr P02 | 約10分 | 2 tasks | 4 files |
| Phase 02 P01 | 4min | 2 tasks | 3 files |
| Phase 02 P02 | 約12分 | 2 tasks | 4 files |
| Phase 04 P01 | 5min | 2 tasks | 2 files |
| Phase 04 P02 | 4min | 2 tasks | 2 files |
| Phase 01-api-llm P01 | 5min | 3 tasks | 3 files |
| Phase 01-api-llm P02 | 15min | 3 tasks | 4 files |
| Phase 01-api-llm P03 | 10min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

**v1.7.1 ロードマップ確定（2026-07-04）:**

- V171-R-01: 全 17 要件を 4 フェーズへ割当（coarse 粒度・100% 被覆・孤立要件なし）。フェーズ採番はマイルストーンごとに Phase 1 起点へリセット（プロジェクト方針）。
- V171-R-02: V171-TEST-02（APIキー機能のテスト）は検証対象と同居させ **Phase 1 に同梱**（KEY 系は LLMConfigDialog/OCRDialog/ocr.py のキー解決に閉じたまとまり）。
- V171-R-03: V171-OCR-04（L-1 producer-consumer 一本化）は `ocr.py`/`ocr_dialog.py` 横断の高リスク項目のため、**Phase 2 内の独立プランへ隔離**して他の OCR 磨き込みと分離実行する。
- V171-R-04: V171-TEST-01（v1.5.0 回帰テスト）は同じ page_ops 面を触る **Phase 3 に同梱**し、透かし画像対応（PAGE-01）の前提となるテキスト透かし回帰を先に固める。ショートカット読込の回帰テストを Phase 3 で整備してから Phase 4 の GUI 化（UIUX-01）へ進む順序とする。
- V171-R-05: L-1〜L-6 は v1.4.0 期レビュー由来で v1.6.0〜v1.7.0 に解消済み項目があるため、各フェーズの**計画時に現行コード照合で「活き残り」を確定**してから対象化する（成功基準にも明記）。
- V171-R-06: 「棚卸し→改善」型要件（PAGE-02/03・TEST-03）は棚卸し結果と対応項目を計画時に確定・記録し、成功基準の照合対象とする。

**v1.6.0 ロードマップ確定（2026-06-18）:**

- V16-R-01: 全 9 要件を 4 フェーズへ割当（coarse 粒度・100% 被覆・孤立要件なし）。
- V16-R-02: S3 ページネーション（V16-UI-03）は viewer/dnd/全ページインデックス整合の高リスクのため、S1/S2（UI 層中心）から切り離して **Phase 2 単独**に隔離。
- V16-R-03: プランA（H1/H2/H5/M1）は viewer 即時反映と OCR/エラー系の混在だが、いずれも「体感品質・堅牢性」という単一目的で結束するため **Phase 3 に集約**。
- V16-R-04: プランC（M3/M4）は OCRDialog/プロバイダ層中心で AI 出力品質という独立価値を持つため **Phase 4** とし、プランA 完了後（OCR 堅牢性の土台の上）に着手。

**v1.3.0 確定済み決定事項（引き継ぎ）:**

- D-01: Undo/Redo を対称デルタ方式で実装
- D-04: insert/merge は巻き戻し直前に削除ページ bytes をキャプチャして redo 用デルタに格納
- D-05: _restore_state の pdf_bytes 分岐を完全撤廃
- D-06: _undo_stack/_redo_stack の両方を deque(maxlen=MAX_UNDO) 化

**v1.4.0 確定済み決定事項:**

- V14-D-01: 実装方針は `urllib.request` 直叩き・新規 pip 依存ゼロ（公式 SDK 不採用）
- V14-D-02: APIキーは環境変数のみ・`_save_settings()` への流入ガードが最優先タスク（Phase 05 着手直前）
- V14-D-03: 既定 `ocr_provider: "off"` — 外部送信・課金を望まないユーザー向けの安全なデフォルト
- V14-D-04: `temperature` は STACK.md 優先（全モデル可）。ただし Opus 4.7/4.8 の `effort` 対応と非対応パラメータは Phase 05 実 API で検証
- V14-D-05: fitz の `get_pixmap()` はメインスレッドのみ。ワーカースレッドには bytes のみ渡す
- V14-D-06: 逐次レンダリング（レンダリング→送信→破棄）を Phase 06 で実装しメモリ一括保持を廃止
- V14-D-07: テキスト埋め込み判定 (`page.get_text()`) を Phase 04 で先行実装（低コスト・高効果）
- V14-D-08: Tesseract / PluginManager 登録フックは Phase 07（任意・最終）。スコープ調整時に切りやすい位置
- [Phase ?]: OCRProvider 抽象基底（ocr_image/list_models 抽象メソッド + default_concurrency/max_concurrency クラス属性）を pagefolio/ocr_providers.py に新設し、後続プランのインターフェース契約を確定
- [Phase 04-provider-abstraction]: EMBEDDED_TEXT_MIN_CHARS=3: 1〜2文字の誤検出を抑制しつつ典型的なページ番号テキスト以上を検出する（D-06）
- [Phase 04-provider-abstraction]: build_provider で ocr_provider='off' のとき LMStudioProvider を返す（Phase 4 後方互換・D-CONTEXT）
- [Phase 04-03]: _render_next_page を after(0) 連鎖で実装しメインスレッドレンダリング中も UI フリーズを回避（D-01）
- [Phase 04-03]: _worker docstring に禁止ワード（fitz/get_pixmap 等）を書かないルール（automated grep 誤検知防止）
- [Phase 04-03]: OCR-PROV-02・OCR-PERF-01 要件完了。Phase 4 全成功基準達成
- [Phase 04-04 CR-02]: _on_run でワーカー起動前に model_var/max_tokens_var/temperature_var/url_var の live 値で LMStudioProvider を再生成（SC-1 後方互換復元）
- [Phase 04-04 CR-01]: _start_ocr の build_provider を try/except ValueError で保護し messagebox.showerror + return でグレースフル処理（防御的堅牢化）
- [Phase 05-01]: ClaudeProvider（messages API・effort/temperature 防御・429/5xx→OCRRetryableError 変換・並列度 Claude=2）
- [Phase 05-02]: _SENSITIVE_KEYS を set 定数として定義し _save_settings でキー名のみ logger.error・値はログ非出力・除外コピーを json.dump（成功基準1・D-01・D-04）
- [Phase 05-02]: claude_model="claude-sonnet-4-6" / ocr_effort="low" を DEFAULT_SETTINGS に追加（無害な設定値・OCR-UI-01 基盤）
- [Phase 05-02]: Phase 5 文言 9 キーを ja/en 両辞書に追加（OCR-UI-01 基盤）
- [Phase 05-03]: _resolve_api_key は os.environ.get のみ（読み取り専用）・書き込み禁止（D-05）
- [Phase 05-03]: build_provider の claude 分岐は api_key を引数のみで受け取り settings には入れない（D-01/D-05）
- [Phase 05-03]: run_parallel バックオフは provider 非依存の共通層として実装（Phase 6 Gemini で再利用可能・D-14）
- [Phase 05-03]: _start_ocr の waiting on_progress は done=None で呼ぶ（完了カウントは進めない）
- [Phase 05-03]: getattr(self, '_session_api_keys', {}) でテスト経路の安全なフォールバックを確保
- [Phase 05-04]: provider Combobox values は静的リスト ['off','lmstudio','claude']（Phase 6: gemini を追加予定コメント付記）
- [Phase 05-04]: _update_ocr_buttons_state は _update_doc_buttons_state から連動呼び出し（設定変更経路をカバー）
- [Phase 05-04]: _refresh_claude_models は例外時も静的 RECOMMENDED_MODELS へフォールバック（D-08 一貫適用）
- [Phase 05-04]: effort_frame / temperature_frame の pack 順は _on_model_change 呼び出し側が担保（フレーム同士の pack_forget が互いに独立）
- [Phase 05-05]: on_progress の waiting status を 'waiting/{attempt}' 形式に変更しリトライ番号を伝搬（on_progress シグネチャ変更なし）
- [Phase 05-05]: コスト確認ダイアログは messagebox.askyesno を使用（grab_set モーダルより軽量・D-11 毎回確認）
- [Phase 05-05]: セッションキー入力欄の値は _session_api_keys に格納し settings には入れない（D-01/D-03）
- [Phase ?]: [Phase 06-01]: GeminiProvider は ClaudeProvider と同型テンプレートで実装（D-05）
- [Phase ?]: [Phase 06-01]: GEMINI_API_KEY 優先 GOOGLE_API_KEY フォールバック dual env var（D-06）
- [Phase ?]: [Phase 06-01]: thinkingConfig は generationConfig 直下 thinkingBudget=0（D-09）
- [Phase ?]: [Phase 06-01]: x-goog-api-key ヘッダー認証 URL ?key= 不使用（D-05/T-06-01）
- [Phase 06-03]: ocr_scale 既定を 2.0 → 1.5 に変更（D-11・OCR-PERF-05）。既存保存値は setdefault で据え置き
- [Phase 06-03]: gemini_model 既定 'gemini-2.5-flash' を settings.py に追加（D-08・無害な設定値）
- [Phase 06-03]: _is_cloud_provider は name in ('claude','gemini') + isinstance((ClaudeProvider, GeminiProvider)) で判定（Pitfall-F）
- [Phase 06-03]: _needs_session_key の gemini 分岐は GEMINI_API_KEY or GOOGLE_API_KEY dual env var（D-06/Pitfall-G）
- [Phase 06-03]: gemini セッションキーは _session_api_keys['gemini'] のみに格納（T-06-11・settings 非永続化）
- [Phase 06-02]: バッファ上限は concurrency+1（余裕係数 1: ワーカー飢えを防ぐ最小マージン・D-02）
- [Phase 06-02]: run_with_bounded_buffer は Tk 非依存の ocr.py モジュール関数として切り出し（D-13 テスト可能化）
- [Phase 06-02]: _worker は fitz/get_pixmap/page_to_png_b64/self.doc[ を一切使用しない（D-04 必達）
- [Phase 06-02]: 全ページ base64 一括辞書蓄積（self._images = {}）を撤廃しパイプライン化
- [Phase 06-02]: 統合プログレス（done+skipped/total）を主軸とし、レンダリング 2 段表示を廃止（D-03）
- [Phase 06-04]: _workers_remaining カウンタ（Lock 配下）で最終ワーカーのみ終了処理を呼ぶ（単一終了処理の保証・CR-01）
- [Phase 06-04]: _fatal_msg/_fatal_kind を共有属性に昇格し Lock 保護（複数ワーカーの致命的エラー報告・CR-01）
- [Phase 06-04]: DEFAULT_OCR_SCALE = 1.5 に統一し D-11 既定と整合（WR-01）
- [Phase 06-04]: _SENSITIVE_KEYS に google_api_key / GOOGLE_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY 大文字バリアントを追加（WR-03）
- [Phase 01-01]: OCRDialog の数値 Spinbox 4 種（scale/timeout/max_tokens/temperature）を state=readonly + fg=TEXT_SUB で読み取り専用化、model_combo/取得ボタンを disabled（編集導線を LLMConfigDialog へ一元化・V16-UI-01）
- [Phase 01-01]: 数値同期を独立メソッド _sync_param_vars_from_settings に切り出し、_apply_llm_settings の provider 分岐外（全プロバイダ共通箇所）から呼び claude/gemini でも即時反映（D-03）。値はログ非出力（T-01-01）
- [Phase ?]: [Phase 01-02]: サムネイルスライダーを独立 zoom_frame（全幅行）へ移設しボタンとの幅競合を解消（D-07/D-08）。範囲/変数/コールバック不変（D-09）。viewer.py/settings.py 未変更
- [Phase ?]: [Phase 01-02]: APP_VERSION を v1.6.0 へ更新し README バッジ・開発履歴.md を同期（CLAUDE.md 規約）。pyproject.toml 未編集
- [Phase ?]: [Phase 02-01]: ページネーション純ロジックを pagefolio/pagination.py に集約（Tk/fitz 非依存・8 純関数）。clamp_page_size をフェーズ内確定名に固定（W1）し 02-02/02-03 はこの名で import
- [Phase ?]: [Phase 02-01]: 純関数は page_size<=0 / n_pages<=0 でも例外を投げず安全側へ倒す（T-2-01）。window_label は文言裁量と疎結合にし、テストは数値包含で照合
- [Phase ?]: selected_pages は全ページ index 不変条件を保持し、照合側を to_global で窓変換（02-02・D-07・Pitfall 1 解消）
- [Phase 02-03]: ナビ/件数フッター（◀▶＋範囲ラベル＋件数 Spinbox state=readonly）構築・D&D local→global 換算・ja/en 同一 LANG キー・_refresh_all 正規化を reconcile_window_start へ集約
- [Phase 02-03]: 手動窓ナビと D-11 自動追従の対立はハンドラ層で解消（_move_window で窓移動後に current_page を新窓先頭へ追従＝「current は常に窓内」不変条件）。reconcile_window_start は (B) 操作による current 押し出し専用追従へ純化（UAT 項目2 修正・debug 260618-pagination-window-nav-snapback）
- [Phase ?]: [Phase 04-01]: parse_markdown 判定優先順位 code>md_h2>md_h1>bullet>通常段落・in_code フラグでフェンス内見出しを構造抑止。md_render.py は Tk/fitz 非依存純ロジック層で 04-03 が import
- [Phase ?]: [Phase 04-01]: _split_inline は **bold** のみ対応・空リスト不返却で [(text,None)] フォールバック。ReDoS 回避: 非貪欲+文字クラスのみ（線形時間）
- [Phase 04-02]: resolve_ocr_prompt 解決優先順位を custom(非空) > PROVIDER_OCR_PROMPTS[provider][preset] > OCR_PROMPTS.get(preset, OCR_PROMPTS['text']) に固定（既存 _on_run/ocr_dialog.py:1090 既定 text と一致・後方互換）
- [Phase 04-02]: PROVIDER_OCR_PROMPTS は claude(XML タグ)/gemini(明示指示) × text/table/markdown のみ定義。lmstudio/tesseract/off は汎用 OCR_PROMPTS フォールバック（Pitfall 4: Tesseract は prompt 無視）。Tk/ネットワーク非依存純関数で 04-03 が import
- [Phase 01-01]: V171-KEY-02: _resolve_api_key の優先順を session_keys(入力値) > 環境変数へ反転（claude/gemini/runpod全分岐・gemini dual env内部順序は不変）
- [Phase 01-01]: 既存の env優先固定テストは新規追加でなく書き換え・リネームで対応（Pitfall 4）。RunPod版 TestResolveApiKeyRunPod を新設
- [Phase 01-01]: llm_env_key_unset_static系ヒント文言をUI-SPEC D-11準拠へja/en同時更新（新規キー追加なし）。ocr_session_key_labelはPlan03の撤去タスクと同時削除する方針で本プランでは維持
- [Phase ?]: [Phase 01-02]: LLMConfigDialog に session_api_keys 引数を追加し複製せず参照保持。claude/gemini/runpod 各セクションへマスク付き APIキー入力欄+トグル+セッション限定注記を追加し _apply で app._session_api_keys へ同期（llm_settings 非流入維持）
- [Phase ?]: [Phase 01-02]: app.py._open_settings は getattr(self, '_session_api_keys', None) 経由で SettingsDialog へ渡す（既存 SimpleNamespace テストスタブとの後方互換のための防御的パターン）。SettingsDialog は session_api_keys を複製せず参照保持し LLMConfigDialog へ中継（RESEARCH.md Pitfall 5対応）
- [Phase ?]: [Phase 01-02]: _refresh_claude_models/_refresh_gemini_models/_refresh_runpod_models をライブ入力値優先→環境変数フォールバックへ変更（D-10）。OCRDialog経由の session_api_keys配線は Plan 03の担当範囲として明示的に対象外
- [Phase 01-03]: OCRDialogのクラウド実行ゲートを値収集なし確認専用の_check_cloud_api_keyへ一本化（RunPodのclaudeスロット誤格納バグを構造的に解消・Pitfall 1） — 撤去に伴う成功基準2の明示エラー欠落を防ぐため（Pitfall 2）
- [Phase 01-03]: OCRDialog._open_llm_configはgetattr(self.app,'_session_api_keys',None)経由でLLMConfigDialogへ配線（Plan02のapp.py._open_settingsと同じ防御的パターン。既存の完全SimpleNamespaceスタブとの後方互換）

### Pending Todos

- なし。v1.7.1 要件は [REQUIREMENTS.md](./REQUIREMENTS.md)、フェーズ割当は [ROADMAP.md](./ROADMAP.md) を参照。

### Blockers/Concerns

- [v1.7.1 Phase 1 留意]: キー解決の優先順を「入力値 → 環境変数」へ**反転**する（現行は環境変数優先・OCRDialog 側）。`_resolve_api_key` の読み取り専用原則（Phase 05-03 決定）と `_SENSITIVE_KEYS` 非保存ガード（V14-D-02）は維持したまま解決順のみ変更する。
- [v1.7.1 Phase 2 リスク]: V171-OCR-04（L-1 producer-consumer 一本化）は `ocr.py`/`ocr_dialog.py` 横断の高リスク。計画時に独立プランへ隔離し、既存 OCR テスト群（並列・キャンセル・進捗・リトライ）をグリーン維持の安全網とする。
- [v1.7.1 全般留意]: L-1〜L-6 は v1.4.0 期レビュー由来で v1.6.0〜v1.7.0 に解消済み項目がある（例: stop_reason 途切れ検出は v1.6.0 Phase 3 で実装済み）。各フェーズの計画時に現行コード照合を行い、活き残りのみを対象とする。
- [v1.7.1 Phase 3/4 留意]: PAGE-02/03・TEST-03 は「棚卸し→改善」型。棚卸し結果と対応項目を計画時に確定・記録し、成功基準の照合対象とする。
- [v1.6.0 Phase 3 継続]: V16-QUAL-03（max_tokens/429 実機検証）は実 API 前提のチェックリスト化まで完了。実機実施は未了のまま受容済み。

過去の懸念は全て解決済み:

  - ~~fitz のスレッドセーフ制約~~ → Phase 04 でスレッド境界を明確化（ワーカーには bytes のみ渡す）
  - ~~Gemini Free Tier 10 RPM~~ → Phase 06 で並列度 1 を既定化
  - ~~Claude temperature/effort の実 API 確認~~ → Phase 05 で完了
  - ~~S3 ページネーションのインデックス整合~~ → v1.6.0 Phase 02 で `pagination.py` 純ロジック層に集約して解決

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260607-ccz | OCR 抽出画面に「⚙ LLM 設定…」ボタンを追加し既存 LLMConfigDialog でプロバイダ・モデルを変更可能化（ライブ更新・05-05 UAT 発見の不具合修正） | 2026-06-07 | f210f76 | [260607-ccz-ocr-llm-llmconfigdialog](./quick/260607-ccz-ocr-llm-llmconfigdialog/) |
| 260609-aaa | v1.4.0 ビルド（PyInstaller）・git push・GitHub Release 作成（PageFolio-v1.4.0-win64.zip） | 2026-06-09 | 9888c4f | [260609-aaa-v140-build-release](./quick/260609-aaa-v140-build-release/) |
| 260610-aaa | v1.4.0 リリース内容コードレビュー・修正計画文書化（H-1〜H-4 / M-1〜M-11 / L-1〜L-6） | 2026-06-10 | - | [260610-aaa-v140-review-fixplan](./quick/260610-aaa-v140-review-fixplan/) |
| 260610-qqq | v1.4.1 ホットフィックス（H-1〜H-5）: OCR max_tokens クランプ・Tesseract プロバイダ置換防止・並列度再クランプ・LLM 設定ダイアログ UI 修正 | 2026-06-10 | 1319c12 | [260610-qqq-review-md-260610-aaa-h-1-h-5-v1-4-1](./quick/260610-qqq-review-md-260610-aaa-h-1-h-5-v1-4-1/) |
| 260610-rkp | v1.4.2 安定化（M-1〜M-11）: スレッド/ライフサイクル安定・プロバイダ API 堅牢化・UI/i18n/コスト一貫性 | 2026-06-10 | 7d68f97 | [260610-rkp-v1-4-2-review-md-m-1-m-11](./quick/260610-rkp-v1-4-2-review-md-m-1-m-11/) |
| 260610-fast | CLAUDE.md を v1.4.2 時点の構成に最新化（dialogs/ パッケージ・OCR モジュール群反映、L-6 一部対応） | 2026-06-10 | bc4323d | — |
| 260611-omi | ブランチ claude/sleepy-fermi-y2z355 を main へ fast-forward マージし v1.4.3 を確定（OCR クリア後再実行バグ H-6・Gemini gemma 400 エラー H-7・埋め込みテキスト無視オプション・429/5xx メッセージ分離・モデル名表示）。PyInstaller リビルド・ドキュメント更新 | 2026-06-11 | abfe97c | [260611-omi-claude-sleepy-fermi-y2z355-v1-4-3](./quick/260611-omi-claude-sleepy-fermi-y2z355-v1-4-3/) |
| 260612-shc | ブランチ claude/sharp-carson-zqfduf を main へ fast-forward マージし v1.4.4 を確定（ページ→画像変換・縮小保存の上書き修正・OCR リラン/続きから再実行/サーキットブレーカー・OCR ヘッダー UI 改善・README Gemma 実績更新）。PyInstaller リビルド・ドキュメント更新・push・GitHub Release | 2026-06-12 | f9ec869 | [260612-shc-sharp-carson-zqfduf-v1-4-4](./quick/260612-shc-sharp-carson-zqfduf-v1-4-4/) |
| 260622-grm | OCR テキスト抽出画面・LLM 設定ダイアログのタイムアウト上限を 600 秒 → 900 秒へ拡大（Spinbox 上限・クランプ計 4 箇所）。APP_VERSION を v1.6.1 へ更新・README/開発履歴.md 同期 | 2026-06-22 | 2bff34b | [260622-grm-great-maxwell-k67sbc-v1-6-1](./quick/260622-grm-great-maxwell-k67sbc-v1-6-1/) |
| 260623-pwp | PDF パスワード対応（付与/解除・AES-256・暗号化PDFの認証オープン）と印刷機能（Ctrl+P・既定PDFハンドラ送信）を v1.6.1 に追加。新規 `password.py`/`print_ops.py`・テスト 16 件追加（計 611 件） | 2026-06-23 | — | [260623-pwp-great-maxwell-k67sbc-password-print](./quick/260623-pwp-great-maxwell-k67sbc-password-print/) |
| 260623-rel | ブランチ claude/great-maxwell-k67sbc を main へマージし v1.6.1 をリリース。pytest 613 件グリーン・ruff クリーン検証、PyInstaller リビルド（`dist/PageFolio` 更新）、PR #25 マージ、注釈付きタグ `v1.6.1` 付与、GitHub Release を Latest 公開（PageFolio-v1.6.1-win64.zip + .sha256 添付） | 2026-06-23 | fd20608 | [260623-rel-v161-merge-release](./quick/260623-rel-v161-merge-release/) |
| 260703-svm | v1.6.5（サマリ生成の安定化・進捗UX・エラーハンドリング統一・黒塗り/モザイク）+ v1.7.0（undo デルタの UndoBlobStore ディスク退避・undo no-op 3操作/透かし rotate=45 バグ修正・120ページストレステスト自動化）を実装。pytest 707 件グリーン | 2026-07-03 | 8949f65 / 3146706 | [260703-v165-v170-stabilization-memopt](./quick/260703-v165-v170-stabilization-memopt/) |
| 260630-rel | ブランチ feature/add-ollama-runpod（Ollama・RunPod プロバイダ追加・設定画面リプレース）を main へマージし v1.6.2 をリリース。ruff クリーン・pytest 619 件グリーン検証、PR #26 マージ、注釈付きタグ `v1.6.2-1` 付与（immutable release のタグ名再利用ブロック回避で `-1` サフィックス）、GitHub Release を Latest 公開（`PageFolio-v1.6.2-win64.zip` + `.sha256` 添付）。v1.6.1/v1.6.2 を MILESTONES.md へ遡及記録 | 2026-06-30 | ae16c22 | — |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| ~~v2~~ | ~~暗号化 PDF 対応~~ | **Shipped v1.6.1**（パスワード付与/解除・AES-256・認証オープン） | Init |
| ~~v2~~ | ~~印刷機能~~ | **Shipped v1.6.1**（Ctrl+P・既定 PDF ハンドラ送信） | Init |
| v2 | プラグイン API バージョン管理 | Out of scope | Init |
| v2 | OS キーストア連携（Windows Credential Manager）による APIキー永続化 | Out of scope | v1.4.0 |
| v2 | OCR 結果のページ埋め込み（検索可能 PDF 化） | Out of scope | v1.4.0 |
| v2 | プロバイダ別の詳細な実コスト計測・課金トラッキング | Out of scope | v1.4.0 |
| Future | PERF-01: サムネイル仮想化によるパフォーマンス改善（大量ページ対応） | Future Requirements | v1.7.1 |

### v1.4.0 クローズ時に Acknowledge した未クローズ項目（2026-06-14）

実作業は v1.4.0〜v1.4.4 として出荷済み。記録上の完了マーカー欠落のため tech debt として遅延受容。

| Category | Item | Status |
|----------|------|--------|
| verification | Phase 04 04-VERIFICATION.md | human_needed |
| quick_task | 260607-ccz-ocr-llm-llmconfigdialog | unknown |
| quick_task | 260610-aaa-v140-review-fixplan | missing |
| quick_task | 260610-qqq-review-md-260610-aaa-h-1-h-5-v1-4-1 | unknown |
| quick_task | 260610-rkp-v1-4-2-review-md-m-1-m-11 | unknown |

### v1.6.0 クローズ時に Acknowledge した項目（2026-06-20）

締め前監査の 5 件をユーザー判断で受容してクローズ。Phase 04 検証は human-verify スキップ由来（コード検証済・実描画/実 API のみ未確認）。クイックタスク 4 件は v1.4.0 期の記録マーカー欠落で既受容済の再掲。

| Category | Item | Status |
|----------|------|--------|
| verification | Phase 04（04-ai-c）04-VERIFICATION.md | human_needed（markdown 整形表示・実 API 出力品質の実機目視がスキップ・コード起因ブロッカーなし） |
| quick_task | 260607-ccz-ocr-llm-llmconfigdialog | unknown（既受容・v1.4.0 期） |
| quick_task | 260610-aaa-v140-review-fixplan | missing（既受容・v1.4.0 期） |
| quick_task | 260610-qqq-review-md-260610-aaa-h-1-h-5-v1-4-1 | unknown（既受容・v1.4.0 期） |
| quick_task | 260610-rkp-v1-4-2-review-md-m-1-m-11 | unknown（既受容・v1.4.0 期） |

## Session Continuity

Last session: 2026-07-04T16:31:13.154Z
Stopped at: Completed 01-03-PLAN.md
Resume file: None

## Operator Next Steps

- Plan Phase 1 with `/gsd-plan-phase 1`（APIキー入力欄・LLM設定への一元化）
- 計画時の前提: L 系要件は現行コード照合で活き残りを確定してから対象化（V171-R-05）
