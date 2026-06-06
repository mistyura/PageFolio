---
gsd_state_version: 1.0
milestone: v1.4.0
milestone_name: OCR プロバイダ化 + クラウドAPI対応
status: executing
stopped_at: 05-05-PLAN.md Task 4 human-verify 待ち
last_updated: "2026-06-07T11:00:00Z"
last_activity: 2026-06-07 -- 05-05 Task 1-3 完了（provider 中立化・コスト確認ゲート・セッションキー入力欄・waiting 進捗）・Task 4 human-verify 待ち
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 9
  completed_plans: 9
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-06)

**Core value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする
**Current focus:** Phase 05 — claude-provider-ui

## Current Position

Phase: 05 (claude-provider-ui) — EXECUTING
Plan: 4 of 5
Status: Executing Phase 05
Last activity: 2026-06-07 -- 05-04 完了（provider DD・欄切替・claude モデル更新・effort 切替・OCR ボタン無効化・human-verify approved）

```
[==========] v1.3.0 COMPLETE
[====      ] v1.4.0 Phase 04 ████（完了）  Phase 05 ░░░░  Phase 06 ░░░░  Phase 07 ░░░░
```

## Performance Metrics

**Velocity (v1.3.0 実績):**

- Total plans completed: 10
- Average duration: 約 22.5 分
- Total execution time: 約 45 分

**By Phase (v1.3.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01 | 3 | - | 約 22.5 分 |
| Phase 02 | 3 | - | - |
| Phase 03 | 2 | - | - |

*v1.4.0 フェーズ完了後に追記*
| Phase 04-provider-abstraction P01 | 3min | 2 tasks | 2 files |
| Phase 04-provider-abstraction P02 | 8min | 2 tasks | 4 files |
| Phase 04-provider-abstraction P03 | 6min | 2 tasks | 3 files |
| Phase 04-provider-abstraction P04 (gap) | 10min | 3 tasks | 4 files |
| Phase 05-claude-provider-ui P01 | 25 | 3 tasks | 2 files |
| Phase 05-claude-provider-ui P02 | 10min | 3 tasks | 3 files |
| Phase 05-claude-provider-ui P03 | 30min | 3 tasks | 3 files |
| Phase 05-claude-provider-ui P04 | 30min | 3 tasks | 3 files |

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

### Pending Todos

None.

### Blockers/Concerns

- fitz のスレッドセーフ制約（スレッドに `fitz.Document` を渡せない）: Phase 04 でスレッド境界を明確化することで対処
- Gemini Free Tier 10 RPM: Phase 06 で並列度 1 を起点に実測して調整
- Claude temperature/effort の実 API 確認: Phase 05 の完了条件として組み込み済み

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

Last session: 2026-06-06T22:52:44.941Z
Stopped at: 05-04-PLAN.md 完了
Resume file: .planning/phases/05-claude-provider-ui/05-05-PLAN.md

## Operator Next Steps

- 05-04 完了。次は 05-05（OCR ダイアログ UI 拡張 — セッションキー入力欄・コスト確認・waiting 進捗表示）
