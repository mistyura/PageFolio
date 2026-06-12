---
gsd_state_version: 1.0
milestone: v1.4.0
milestone_name: OCR プロバイダ化 + クラウドAPI対応
status: Phase 06 完了（06-04 ギャップクロージャ達成）
stopped_at: 260612-shc 完了（v1.4.4 確定・マージ・リビルド・公開）
last_updated: "2026-06-12T09:00:00.000Z"
last_activity: "2026-06-12 - Completed quick task 260612-shc: claude/sharp-carson-zqfduf マージ → v1.4.4 確定 → リビルド → push/Release"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 14
  completed_plans: 13
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-06)

**Core value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする
**Current focus:** Phase 06 — gemini-provider

## Current Position

Phase: 7
Plan: Not started
Status: Phase 06 完了（06-04 ギャップクロージャ達成）
Last activity: 2026-06-10 - Completed quick task 260610-rkp: v1.4.2 安定化（M-1〜M-11）

```
[==========] v1.3.0 COMPLETE
[========  ] v1.4.0 Phase 04 ████（完了）  Phase 05 ████（完了）  Phase 06 ████（完了）  Phase 07 ░░░░
```

## Performance Metrics

**Velocity (v1.3.0 実績):**

- Total plans completed: 14
- Average duration: 約 22.5 分
- Total execution time: 約 45 分

**By Phase (v1.3.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01 | 3 | - | 約 22.5 分 |
| Phase 02 | 3 | - | - |
| Phase 03 | 2 | - | - |
| 06 | 4 | - | - |

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

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

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

### Pending Todos

- **v1.4.1 ホットフィックス（H-1〜H-5）**: v1.4.0 リリースレビューで検出した重大問題 +
  ユーザー報告（H-5: LLM 設定画面のプロバイダ切替時リサイズ不全）の修正。
  **着手時は必ず [260610-aaa-REVIEW.md](./quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md) を参照すること**
  （指摘番号・該当箇所・対応方針・着手時の注意を記載済み）。

### Blockers/Concerns

- fitz のスレッドセーフ制約（スレッドに `fitz.Document` を渡せない）: Phase 04 でスレッド境界を明確化することで対処
- Gemini Free Tier 10 RPM: Phase 06 で並列度 1 を起点に実測して調整
- Claude temperature/effort の実 API 確認: Phase 05 の完了条件として組み込み済み

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

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v2 | 暗号化 PDF 対応 | Out of scope | Init |
| v2 | 印刷機能 | Out of scope | Init |
| v2 | プラグイン API バージョン管理 | Out of scope | Init |
| v2 | OS キーストア連携（Windows Credential Manager）による APIキー永続化 | Out of scope | v1.4.0 |
| v2 | OCR 結果のページ埋め込み（検索可能 PDF 化） | Out of scope | v1.4.0 |
| v2 | プロバイダ別の詳細な実コスト計測・課金トラッキング | Out of scope | v1.4.0 |

## Session Continuity

Last session: 2026-06-12T09:00:00.000Z
Stopped at: 260612-shc 完了（v1.4.4 確定・マージ・リビルド・公開）
Resume file: None

## Operator Next Steps

- v1.4.4 確定（2026-06-12）: claude/sharp-carson-zqfduf を main へ ff マージ・PyInstaller リビルド・
  push・GitHub Release まで完了
  - 内容: ページ→画像変換（AI/LLM 読取用途）・「縮小して保存」上書き修正・
    OCR リラン/続きから再実行（リスタート）/サーキットブレーカー・OCR ヘッダー UI 改善・
    README Gemma 注意書きの実績ベース更新
  - テスト 490 件グリーン・ruff クリーン
- 次は **v1.5.0 以降（L-1〜L-6）バックログ**。詳細は REVIEW.md を参照
- **注意**:
  - クラウド OCR の推奨解像度は 1.5〜2.0（4.0 はペイロード肥大でタイムアウト誘発）
  - gemma 系の HTTP 500 はサーバ側要因で日により変動（API 仕様変更ではない）
  - H-7（Gemini gemma 400 エラー修正）は実 API キー環境での動作確認を引き続き推奨
