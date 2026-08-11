---
gsd_state_version: 1.0
milestone: v1.9.0
milestone_name: 安全性・整合性の是正 + OpenAI プロバイダ追加
status: Awaiting next milestone
stopped_at: v1.9.0 マイルストーンをクローズ・アーカイブ済み。次は `/gsd-new-milestone` で次マイルストーンを定義する
last_updated: "2026-08-11T12:38:32.438Z"
last_activity: 2026-08-11
last_activity_desc: Milestone v1.9.0 shipped and archived (verified_closeout)
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 15
  completed_plans: 15
  percent: 100
current_phase: 03
current_phase_name: qa-release-gate
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-11)

**Core value:** 大きな PDF でも Undo/Redo が正しく・速く動作し、コードが読みやすく保守しやすい状態にする
**Current focus:** 次マイルストーンの定義待ち（`/gsd-new-milestone`）。候補は PROJECT.md「Next Milestone Goals」を参照

## Shipped Milestone: v1.9.0（2026-08-11・verified_closeout）

3 フェーズ / 15 プラン / 48 タスク。V190-* 全 27 要件 Complete（被覆 27/27）。
検証 3/3 passed・Nyquist COMPLIANT・セキュリティ threats_open 0・UAT 19/19 pass（issue 0）。
`APP_VERSION = v1.9.0`・テスト 1404 件グリーン・ruff クリーン。

アーカイブ: `milestones/v1.9.0-ROADMAP.md` / `milestones/v1.9.0-REQUIREMENTS.md` /
`milestones/v1.9.0-MILESTONE-AUDIT.md` / `milestones/v1.9.0-phases/`

> クローズ時の判断: 事前監査（audit-open）が検出した Phase 03 `03-UAT-RESULTS.md` [unknown]
> は誤検出（同ファイルは Plan 03-03 の成果物であり GSD の UAT セッションファイルではない。
> 実体である `03-UAT.md` は `status: complete`・19/19 pass・pending 0）。
> `v1.9.0-MILESTONE-AUDIT.md`（status: gaps_found）は Phase 2 完了時点（2026-08-11 17:03）の
> 監査であり、その 40 分後に開始した Phase 3 が指摘ギャップ（V190-QA-01/02/03）を全て解消済み。
> 以上より verified_closeout として確定した。

## Current Position

Phase: Milestone v1.9.0 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-08-11 — Milestone v1.9.0 completed and archived

## v1.9.0 Phase Map

| Phase | Name | Requirements | リスク/性質 |
|-------|------|--------------|------------|
| 1 | 保存・編集・設定の安全性是正（失敗時ロールバック担保） | V190-SAFE-01〜05, V190-CFG-01/02, V190-UNDO-01/02 | 既存機能レビュー課題 REV-01〜07 の是正。「記録後置」パターンを確立し UNDO-01/02 の安全網に構造的に流用する。P0/P1 かつ Phase 2 の前提（SAFE-03 の `off` 生成不可化） |
| 2 | OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加 | V190-CAT-01/02, V190-OAI-01〜13 | catalog 一元化（REV-08）が OpenAI 追加の requires-before。Phase 1 の SAFE-03 完了が前提。モデルラインナップ/一覧フィルタ方式は実装開始時に実キーで確認（研究 Gap） |
| 3 | 品質保証・リリースゲート | V190-QA-01〜03 | Tcl/Tk 環境修復の根本原因評価がリサーチ間で食い違い（STACK: 実機再現せず／PITFALLS: 早期対応推奨）。Phase 1/2 完了後の全テスト完走・human-verify を最終ゲートとする |

## Performance Metrics

**Velocity (v1.3.0 実績):**

- Total plans completed: 36
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
| 01 | 7 | - | - |
| 02 | 4 | - | - |
| 03 | 4 | - | - |
| 04 | 4 | - | - |
| 05 | 4 | - | - |

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
| Phase 01-api-llm P04 | 15min | 2 tasks | 3 files |
| Phase 02 P02 | 25min | 2 tasks | 9 files |
| Phase 02 P03 | 35min | 2 tasks | 6 files |
| Phase 02 P04 | 約55分 | 3 tasks | 7 files |
| Phase 03-v1-5-0 P01 | 6min | 2 tasks | 4 files |
| Phase 03-v1-5-0 P02 | 7min | 3 tasks | 4 files |
| Phase 03-v1-5-0 P03 | 7min | 3 tasks | 5 files |
| Phase 03-v1-5-0 P04 | 18min | 2 tasks | 6 files |
| Phase 04 P01 | 3min | 3 tasks | 2 files |
| Phase 04 P02 | 12min | 3 tasks | 6 files |
| Phase 04 P03 | 20min | 3 tasks | 5 files |
| Phase 04 P04 | 9min | 3 tasks | 5 files |
| Phase 01 P01 | 6min | 2 tasks | 1 files |
| Phase 01-foundation-split P03 | 5min | 2 tasks | 3 files |
| Phase 01-foundation-split P04 | 約16分 | 2 tasks | 6 files |
| Phase 02-ai P01 | 10min | 3 tasks | 4 files |
| Phase 02-ai P02 | 約20min | 2 tasks | 4 files |
| Phase 02-ai P03 | 約15min | 2 tasks | 4 files |
| Phase 02-ai P05 | 約20min | 3 tasks | 4 files |
| Phase 02-ai P06 | 約15分 | 2 tasks | 1 files |
| Phase 03-ocr-e2e P01 | 32min | 2 tasks | 4 files |
| Phase 03-ocr-e2e P02 | 約16分 | 2 tasks | 1 files |
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 04 P01 | 8min | 2 tasks | 2 files |
| Phase 04-ocr P02 | 27min | 3 tasks | 3 files |
| Phase 04 P03 | 15min | 3 tasks | 6 files |
| Phase 05 P01 | 20min | 3 tasks | 5 files |
| Phase 05 P03 | 15min | 2 tasks | 2 files |
| Phase 05 P04 | 15min | 3 tasks | 3 files |
| Phase 05 P02 | 20min | 2 tasks | 5 files |
| Phase 06-ux-ui P01 | 20min | 3 tasks | 8 files |
| Phase 06-ux-ui P02 | 17min | 3 tasks | 5 files |
| Phase 06 P03 | 20min | 3 tasks | 5 files |
| Phase 01 P01 | 71min | 3 tasks | 2 files |
| Phase 01 P02 | 約35min | 3 tasks | 9 files |
| Phase 01 P03 | 約20min | 3 tasks | 2 files |
| Phase 01 P04 | 約20min | 3 tasks | 4 files |
| Phase 01 P05 | 約20min | 3 tasks | 2 files |
| Phase 01 P06 | 約45min | 3 tasks | 3 files |
| Phase 01 P07 | 約70分 | 3 tasks | 4 files |
| Phase 02 P01 | 38min | 3 tasks | 9 files |
| Phase 02 P02 | 16min | 3 tasks | 5 files |
| Phase 02 P03 | 19min | 3 tasks | 7 files |
| Phase 02 P04 | 68min | 5 tasks | 11 files |
| Phase 03 P01 | 約20分 | 3 tasks | 3 files |
| Phase 03 P02 | 約20分 | 3 tasks | 2 files |
| Phase 03-qa-release-gate P03 | 約35分 | 5 tasks | 1 files |
| Phase 03 P04 | 約5分 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

**v1.9.0 ロードマップ確定（2026-08-10）:**

- V190-R-01: 全 27 要件を 3 フェーズへ割当（coarse 粒度・100% 被覆・孤立要件なし）。フェーズ採番はマイルストーンごとに Phase 1 起点へリセット（プロジェクト方針）。
- V190-R-02: SAFE-01〜05・CFG-01/02・UNDO-01/02（計9要件・既存機能レビュー REV-01〜07）を **Phase 1** に統合。マイルストーン共通の受け入れ条件「失敗時は操作前の状態へ戻る」を体現する単一テーマで結束し、CFG は Phase 1 と並行実施可能・UNDO は Phase 1 の「記録後置」パターンを安全網として流用するというリサーチの依存構造を、個別フェーズに分割せず1フェーズ内の複数プランへ反映する。
- V190-R-03: CAT-01/02（catalog 一元化・REV-08）を単独フェーズ化せず **Phase 2** 内の先行プランとして OAI-01〜13 と同居させた。CAT は OpenAI 追加の requires-before だが単独では観測可能なユーザー挙動に乏しい内部構造要件のため、隣接する OpenAI 追加フェーズへ統合する方が自然（coarse 粒度の圧縮方針にも合致）。
- V190-R-04: QA-01〜03 を **Phase 3** の最終リリースゲートとして独立配置。Phase 1/2 の全コード変更が完了した後でなければ全テスト完走ゲート・human-verify の実施根拠が固まらないため。
- V190-R-05: Phase 2 は Phase 1 の V190-SAFE-03（`off` のプロバイダ生成不可化）完了を前提とする（リサーチ指摘: SAFE-03 未了のまま OpenAI を追加すると `off` 誤爆パターンが再現する構造）。

**v1.8.0 ロードマップ確定（2026-07-13）:**

- V180-R-01: 全 26 要件を 6 フェーズへ割当（coarse 粒度・100% 被覆・孤立要件なし）。フェーズ採番はマイルストーンごとに Phase 1 起点へリセット（プロジェクト方針）。26要件・4本柱構成のため coarse 既定の 2-4 より多い 6 フェーズとしたが、各フェーズは REFAC-01/02→TMPL/FALL、REFAC-03→BATCH の明示依存関係と BATCH 単独隔離方針を反映した必然的な境界であり、単一要件フェーズは作らない（REFAC-03 は QA-01 と同居させ Phase 3 を構成）。
- V180-R-02: REFAC-01（ocr_providers.py 分割）・REFAC-02（llm_config.py 分割）・ROBUST-02（`_SENSITIVE_KEYS` 中央レジストリ化）を **Phase 1** に同梱。ROBUST-02 は分割対象と同じファイル面（プロバイダ→環境変数マッピング）のため同フェーズが自然。
- V180-R-03: TMPL-01〜05・FALL-01〜03（計8要件）を **Phase 2** に集約。研究サマリの推奨（テンプレート管理→フォールバックは同一 LLM 設定ダイアログ UI を共有するため隣接配置が効率的）を採用し、coarse 粒度で1フェーズへ統合。
- V180-R-04: REFAC-03（OCRRunEngine 抽出）を QA-01（E2E モックテスト）と同居させ **Phase 3** とし、BATCH 着手の直前に配置。単体では1要件フェーズになる REFAC-03 を QA-01（抽出直後の方がテスト容易性が高い）と組み合わせることで自然な境界にした。
- V180-R-05: BATCH-01〜05 を **Phase 4** として単独隔離（PROJECT.md 確定方針）。他の柱の作業を混在させない。
- V180-R-06: PERF-01〜03・ROBUST-01・ROBUST-03（計5要件）を **Phase 5** に集約。「堅牢性強化」という機能非依存の単一テーマで結束し、BATCH（最大機能）が固まった後に回帰リスクを検証しやすい位置に配置（研究サマリの推奨に追従）。
- V180-R-07: QA-02〜04（計3要件）を **Phase 6** の最終仕上げとして配置。OCRRunEngine/堅牢性強化が完了した後の方が UI 一貫性監査・通知UX 改善の検証がしやすい。

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

（v1.4.0〜v1.8.0 の確定済み決定事項は本ファイル履歴に蓄積済み。詳細は git 履歴または各マイルストーンアーカイブを参照）

- [Phase ?]: 後方互換 import 安全網の先行拡張: TestOcrProvidersImports は全17シンボル（private ヘルパー含む）を個別+一括の両方で package-level import 検証。既存 TestDialogsImports の記法をそのまま複製し新規パターンを持ち込まない（Wave 2/3 分割前の回帰検知装置確立・D-11）
- [Phase ?]: registry.primary_env_var() は未登録プロバイダで KeyError ではなく空文字を返す実装だったため ocr_dialog.py 側で try/except を追加せず直接呼び出しに置換
- [Phase ?]: sections.py/model_fetch.py の env var 参照を registry.env_vars_for() の単一ループへ一般化（D-09 #4/#5 完了・全参照面統合達成）
- [Phase ?]: monkeypatch 対象名前空間の断絶（Plan 02 の _detect_tesseract と同型）を _apply の遅延 import 化 + __init__.py re-export で解消
- [Phase ?]: D-01/D-02/D-03/D-04: settings.py にテンプレート CRUD 純関数（save/get/list/delete/rename/exists）を実装。delete_template はアクティブテンプレート削除を ValueError で拒否、save/rename_template は空名・重複名を ValueError で拒否（02-01）
- [Phase ?]: V180-TMPL-05: resolve_ocr_prompt/resolve_summary_prompt（ocr.py）のシグネチャは無改造。テンプレート層は load_custom_prompt/load_summary_prompt の3段解決（外部ファイル>アクティブテンプレート>設定欄）でのみ挿入（02-01）
- [Phase ?]: D-10/D-12: ocr_fallback.py（新規・Tk/fitz非依存）は next_fallback_candidate/next_summary_candidate の次候補選択のみを担う。確認ダイアログ・実際のプロバイダ切替は02-04の責務として分離（02-01）
- [Phase ?]: D-05: _has_unsaved_template_changes は外部mdファイル連動モード時のみ比較を行い、非連動モードでは常に False（確認ダイアログを出さない）
- [Phase ?]: テンプレート「保存」は常に新規名として重複拒否する設計（上書き更新はリネームの責務として分離）
- [Phase ?]: _apply の prompt_templates 収集は getattr フォールバックで既存の _apply スタブ経路との後方互換を保持
- [Phase ?]: D-13/D-15: MergeOrderDialogのListbox+上下ボタンウィジェット構成のみをTopLevelから埋め込みセクションへ移植（callback経由の親子通信は不要）
- [Phase ?]: D-14: フォールバック候補一覧は_base_fallback_providers(6種)+プラグイン登録の全実行可能プロバイダ。既知プロバイダ一覧外は読み込み時/_apply収集時の両方でホワイトリスト検証により除外（T-02-07）
- [Phase 02-ai gap closure 02-05]: CR-02（02-REVIEW.md BLOCKER・テンプレートCRUDがCancelで取り消せない）を解消。LLMConfigDialog.__init__でprompt_templates（items・各テンプレートdict含む）をcopy.deepcopyで分離しapp.settingsとの参照共有を断ち、sections.pyの3 CRUDハンドラから即時_save_settingsを除去してApply経由の一括確定へ一本化。_on_template_deleteにaskyesno削除確認も追加（02-REVIEW Fix案1+2の両方採用）
- [Phase ?]: D-07 検証をフェイク捕捉+tmp_path実ファイル読み取りの二段構えにし、behavior_unverified_items[1] の実I/O検証要求を満たした（settings._get_base_dir のみ monkeypatch）
- [Phase ?]: 新設スタブはText/Comboboxのみに限定し、既存の_SetGetVarStub（02-05）・_ButtonStub（OCR-UI-02）をテンプレートUIハンドラテストでも再利用した（重複定義回避）
- [Phase 03-01]: queue.Queue/PipelineState は OCRRunEngine.start() 内で一度だけ生成し self.queue プロパティで公開。producer（OCRDialog._render_next_page）は self._engine.queue のみを参照する（落とし穴10・T-03-02 対応）
- [Phase 03-01]: self._pstate は Engine 抽出後も vestigial 属性として維持（_clear_text/_on_run が None へリセットする既存の観測可能な挙動・既存回帰テスト TestClearResetsFatalState との後方互換のため）。実際の共有状態は self._engine（OCRRunEngine._pstate）が所有
- [Phase 03-ocr-e2e]: [Phase 03-02] E2E producer スタブは cancel_flag を自前でチェックせず consume_one の再確認契約に委ねる設計 — consume_one が各アイテム処理開始時に is_fatal()/キャンセル判定を再確認するため、producer側での重複実装を避け既存契約への信頼を優先した
- [Phase 03-ocr-e2e]: [Phase 03-02] サーキットブレーカーテストは OCRRetryableError(retry_after=0.01) で実待機を極小化 — MAX_RETRIES=3・DEFAULT_CIRCUIT_BREAKER_THRESHOLD=3 の構造をそのまま利用しつつテスト実行時間を短縮するため
- [Phase ?]: count_pending(entries) を新設し STATUS_PENDING のみを実行対象=分母として算入。STATUS_ERROR を BatchState.total_files から除外し remaining() の完了時0収束を保証（レビュー懸念6反映）
- [Phase ?]: OCRDialog のコスト確認系メソッドは継承・cross-importせず同一シグネチャ・同一挙動でコピペ移植（ocr_dialog.py無変更・レビュー懸念5）
- [Phase ?]: バッチ中止でキャンセルされたファイルはSTATUS_PENDINGへ戻し、次回実行でcount_pending経由の再処理対象とする（完了/確定失敗とは区別）
- [Phase ?]: E2EテストのTk駆動はPython 3.14のtkinter制約（ワーカースレッドからのafter()にmainloop内実行を要求）に対応しmainloop()/quit()方式を採用
- [Phase ?]: _format_pages_text は entry(BatchFileEntry)を明示引数に取る形で実装（OCRDialogの同名メソッドは単一self参照だが複数ファイル管理のため必然的差分）
- [Phase ?]: メニューバーは app.py の __init__/_rebuild_ui 双方で _build_menubar() を呼ぶ設計（テーマ切替でroot.winfo_children()が全破棄されメニューが消失するのを防ぐ・Rule2追加）
- [Phase ?]: ui_builder.py の Treeview 用 style.configure/mapは # fmt: off/on + noqa E501 で単一物理行に保持（plan acceptanceのliteral grepパターン一致のため）
- [Phase ?]: 05-01: LruCache は新規モジュール pagefolio/thumb_cache.py に配置（pagination.py は窓計算専用の責務を保つ）
- [Phase ?]: 05-01: compute_visible_range/prioritized_render_order は pagination.py へ追加し新規座標系モジュールを作らない（落とし穴1回避策）
- [Phase ?]: 05-01: D&D シミュレーションは既存 _dnd_drop の実装どおり移動後に selected_pages を clear する挙動を踏襲
- [Phase ?]: D-14② の回帰テストは delete+undo+redo+undo（計画書許可の代替案）を採用。insert 版は file_ops.py の insert_redo restore に既存のページ重複バグを発見したため対象外とし deferred-items.md へ記録（05-03）
- [Phase ?]: V180-ROBUST-03: WR-02はキャプチャ時の登録拒否ではなく発火側フォーカスガード(should_suppress_for_focused_input)で解消。Ctrl/Alt組合せは常に非抑止、修飾なし単キー/Shiftのみは入力系ウィジェットフォーカス中のみ抑止（D-09/D-10）
- [Phase ?]: 05-02: THUMB_CACHE_MAX=300はPAGE_SIZE_MAXの3倍を採用しユーザー設定UIは追加しない（D-05/D-06）
- [Phase ?]: 05-02: _build_thumbnails はprioritized_render_orderの返り値を可視件数でスライスし、可視分はafter(0)連鎖・残りはafter_idle連鎖の2チェーンに分割する実装を採用（新規座標系を作らずpagination純関数のみで完結）
- [Phase ?]: 06-01: トースト対象は保存3操作+印刷のみ（D-01/D-02）。約80箇所のmessageboxは網羅置換しない
- [Phase ?]: 06-01: 印刷の一時ファイル生成失敗とOS印刷コマンド失敗は同一カテゴリprintだが異なるLANGキー（err_print_msg/err_print_no_handler）で文言区別（レビューR1）
- [Phase ?]: 06-01: getattr(self,'_toast',None)→messageboxフォールバックをUIBuilderMixin._show_error_or_toastへ共通化（レビューR2）
- [Phase ?]: 06-02: about.pyのdelta値は実測(font_size既定12)に基づき4を採用。RESEARCH.mdのbase=10前提は誤りだったため実装時に実測で再確定
- [Phase ?]: 06-02: スクロール是正はplugin.py(ホイール未対応)とocr_dialog.py(高さクランプ欠如)の2箇所のみに限定。ui_builder.py等の静的bind方式は受容差分として監査記録に根拠付きで残す(D-11)
- [Phase ?]: 06-03: insert_redo は delete_redo 対称パターン（昇順を降順で delete_page）へ修正。修正範囲は _restore_state の insert_redo ブロックのみに限定（D-17）
- [Phase ?]: 06-03: 開発履歴.md の v1.6.1 日付誤記（2026-06-22→2026-06-23）を検出・修正。V16-D-04 が懸念した一時v1.7.0バンプの痕跡は既に解消済みと確認（D-14）
- [Phase ?]: 01-01: D-01/D-02/D-03を実装。_save_asは無条件でPDF_ENCRYPT_KEEP付与、_overwrite_current_fileはsetdefaultで既定化（明示指定は破壊しない）、pdf_has_passwordはderive_pdf_has_password単一関数で保存kwargsから論理導出（実行時I/Oなし）
- [Phase ?]: 01-01: _save_compressedの別パス保存分岐（doc.save直接呼び出し）もencryption未指定で平文化する同型バグだったため、RESEARCH.mdの対応表に明示がなくても同時是正した（V190-SAFE-01の全経路化）
- [Phase ?]: [01-02] D-06: OCRDisabledError は pagefolio/ocr_providers/errors.py に配置（既存3例外と同じ RuntimeError 継承・同一ファイル集約の precedent に揃えた）
- [Phase ?]: [01-02] D-04/D-05: バッチOCR メニューの活性制御は _update_ocr_buttons_state 末尾からの呼び出しに相乗りさせ新規配線を増やさなかった
- [Phase ?]: [01-02] ocr_dialog.py の off 分岐は build_provider を経由せず provider を保持したまま中断する設計とし、旧実装の直接構築の穴（T-01-06）を解消した
- [Phase ?]: [01-03] D-15: sections.py:_on_template_change の save_prompt_file 即時呼び出し2箇所を削除し、外部プロンプトファイルへの書き込みを dialog.py:_apply の1経路へ一本化した（dialog.py は無改造）
- [Phase ?]: [01-03] D-18: _has_unsaved_template_changes から prompt_file_exists による早期False分岐のみを削除し、未選択時ロジックには触れない最小差分にした（Pitfall 5 回避）
- [Phase ?]: [01-03] テストの書き込み監視は撤去済みシンボルではなく pagefolio.settings.save_prompt_file を横断的にモニタするスタブへ統一した
- [Phase ?]: [01-04]: D-08〜D-10/D-14 の通りに _do_insert を実装。プラン原文の『total を直書き』ではなく、delete_page が巻き戻しループ途中で失敗する部分成功ケースにも対応できるよう removed（実際に削除できた件数）を差し引いた residual を Undo state の件数フィールドへ反映する版を採用（Rule 1: 既存ページ誤削除の潜在バグ防止）。典型的な失敗系テストでは removed=0 のため計画の想定挙動と結果は同一
- [Phase ?]: [01-04]: D-11 の通り _duplicate_page の _save_undo("duplicate") を try ブロック内・実処理成功後へ移動。D-13/D-14 の通り _undo/_redo の _restore_state 失敗時は _push_evicting でスタックへ戻し _dispose_state は呼ばない（Pitfall 4 回避・履歴喪失とBlob二重解放を同時に防止）
- [Phase ?]: [01-05]: duplicate/merge/merge_resizeの4手往復回帰テスト（3件）+ 境界・隣接・順序・精度エッジ（5件）をTestAllOpsUndoRedoRoundtripへ追加（V190-UNDO-02）。既存3手往復テストは無変更。全て一発でgreen（duplicate/mergeの逆デルタはinsertと異なりインデックス再計算方式のためinsert_redoと同型の非対称復元バグは発見されず）
- [Phase ?]: [01-05]: D-12棚卸しをgrep実測（page_ops.py 13/dnd.py 2/redact_ops.py 1=計16件）で確定。PLAN.md記載の「12件」は実測と不一致のため実測値を正として記録。先置きのまま残る10 opは次マイルストーン候補として明示、本フェーズではコード変更ゼロ
- [Phase ?]: [01-05]: 開発履歴.md/APP_VERSION更新はPhase 3（V190-QA-03リリースゲート）へ委譲。既存エントリはリリース単位の書式のためマイルストーン途中での追記は書式を崩す
- [Phase ?]: [01-06]: Task 0 checkpoint:decision は方式 A（mutation ループ内で実際に適用できたページ分の逆データを蓄積し部分失敗時は _pending_inverse として remaining_state へ引き継ぐ）を採用。7 op（delete/delete_redo/page_edit/insert_undo/insert_redo/merge_resize/merge_resize_undo）へ展開し、merge_undo は old_count スカラーのみのため非該当であることをピン留めした
- [Phase ?]: [01-07]: Task 0 checkpoint:decision は option-b（mutation順序反転による構造的解消）をユーザー選択済みとして実行。page_edit の delete_page→insert_pdf 順を insert_pdf→delete_page へ反転し、doc がページ内容を失っている瞬間を構造的に排除。option-a（Blob保持方式）は未実装
- [Phase ?]: [01-07]: option-b選択に伴い警告文言は「内容が失われた可能性」ではなく「二重化または欠落している可能性」とした（err_undo/redo_restore_failed_content_at_risk）。option-bの構造上、ロールバック失敗時も旧ページはpage_i+1に必ず残存し内容喪失は起こり得ないため
- [Phase ?]: [01-07]: APP_VERSION・開発履歴.md・READMEバッジは本プランで更新せず、Phase 3（V190-QA-03リリースゲート）へ委譲（01-05/01-06と同じ既定方針の継続）
- [Phase ?]: [01-07]: merge（base op）の削除ループがinsertと同型の未保護構造（一括捕捉＋保護なし削除ループ）を持つことを棚卸しで確認。D-12方針に従いコード変更せず次マイルストーン候補として記録
- [Phase ?]: 02-01: catalog.py新設+OpenAIProvider縦スライス。is_reasoning_modelはo-series OR gpt-5ファミリ(除chat-latest)のOR判定に再設計（実データでgpt-5.1がo系以外の推論モデル真ケースと判明・レビューHIGH02-01-2対応）。default_model=gpt-5.1
- [Phase ?]: 02-02: _resolved_host_text をモジュールレベル関数として実装（既存フローズンテストスタブとの両立を優先）
- [Phase ?]: 02-02: ミューテーション検証で env_var 埋め込みだけでは msg_key 誤フォールバックを検知できないと判明し、openai専用文言の直接アサーションへ強化
- [Phase ?]: 02-03: _EXCLUDED_MODEL_MARKERSから単独imageを除外し画像生成モデルはgpt-imageという限定的マーカーで除外（レビューMEDIUM 02-03-3）。order_models_for_displayはVERIFIED_VISION_MODELSを宣言順で先頭に据える（レビューHIGH 02-03-1）
- [Phase ?]: 02-03: D-08の観測同一性をtest_on_error_matches_zero_result_fallback_of_list_modelsで固定。_on_errorのフォールバック値とlist_models()の0件合流値が完全一致することを保証（レビューMEDIUM-11）
- [Phase ?]: 02-03: sections.pyのプロバイダ一覧2箇所をcatalog.provider_names()/fallback_candidate_names()へ置換しD-03の6参照面移行が完走（V190-CAT-01完了）
- [Phase ?]: 02-04: Task1着手時に作業ツリー先行実装済みだったEFFORT_VALUES_BY_MODEL/effort_values_for_model/_sanitize_header_valueを能力マトリクスと突き合わせ検証のうえ引き継いだ
- [Phase ?]: 02-04: organization/projectの許可文字は英数字限定ではなくHTTPヘッダ値として安全な印字可能ASCII(\x21-\x7E)・長さ1-128とし、不正時は_validate_openai_idが明示エラーでApplyを中断する（黙って空文字化しない）
- [Phase ?]: 02-04: reasoning effortはClaudeのeffort_frame/ocr_effort/_EFFORT_VALUESを流用せずOpenAI専用ウィジェットとopenai_reasoning_effortキーで実装（D-15）
- [Phase ?]: 02-04: フォールバック実機手順はHTTP401がRuntimeErrorになりfatalにならないと実コード照合で判明したため、到達不能URLによるConnectionError誘発へ変更（レビューHIGH02-04-2）
- [Phase ?]: 02-04: Task3B実機確認でOpenAIのAPIキーがOCR実行時に送信されない実バグを発見。ocr_dialog.pyの_apply_llm_settings/_on_runにopenai専用elifが無く汎用else（APIキー不要前提）へ落ちていたことが原因。claude/geminiと同型elifを追加し36e7cc2で修正・回帰テスト2件追加
- [Phase ?]: 03-01: _save_file/_save_as/_save_compressedを確認・パス選択層とpath引数を取る実保存層(_do_save_*)へ分離。retry_cbはfunctools.partialで確定パスを束縛し再試行時は確認・保存先ピッカーを再表示しない（V190-QA-02/D-09〜D-11）
- [Phase ?]: 03-01: Task1(tracer)のverify完全自動通過後、mode:yolo（02-01前例と同一）を根拠に対話モードのtracerゲートを人手待ちにせずTask2へ自動続行
- [Phase ?]: 03-01: REQUIREMENTS.mdのV190-QA-02文言をD-12訂正後表現へ更新。ROADMAP.mdは計画時点で既に訂正済みのため内容確認のみ（二重書き換え回避）
- [Phase ?]: [03-02]: Task1で両症状とも0/10で非再現だったため分岐A（D-05）を採用。tests/conftest.pyへの修復コード追加はゼロ
- [Phase ?]: [03-02]: D-03の2仮説（assertion rewriting/二分探索）は再現しなかったため未検証のまま次マイルストーンへ保存。検証していないものを検証済みと書かない
- [Phase ?]: [03-02]: リリースゲートは単一プロセス完走を採用（10回連続グリーンの統計的根拠により分割実行は不要と判断）
- [Phase ?]: 遡及UAT候補14項目を現行コード照合で活き残り13項目/未実施2項目(③max_tokens・429リトライ実API検証、⑤-Claude実API出力品質)に確定し、実機目視で13項目全てpass記録（03-03・V190-QA-03充足）
- [Phase ?]: [03-04]: 開発履歴.mdのv1.9.0エントリはユーザー指示によりPhase 1〜3全体を対象として記述（03-04単体の作業内容ではない）。事実源はPhase 1/2のVERIFICATION.md・Phase 3の03-01/02/03-SUMMARY.md
- [Phase ?]: [03-04]: 開発履歴.mdの詳細節は新設せずv1.8.0/v1.8.1と同型の1段落形式を踏襲。テスト件数は本セッション実測の1398件のみを出典とした

### Pending Todos

- なし。v1.9.0 はクローズ済み（3フェーズ / 15プラン / 27要件すべて Complete）。次は `/gsd-new-milestone` で次マイルストーンの questioning → research → requirements → roadmap を実行する。

### Blockers/Concerns

v1.9.0 クローズ時点で次マイルストーンへ引き継ぐ未解決項目（いずれも非ブロッキング）:

- [v1.6.0 Phase 3 継続 → v1.9.0 Phase 3 で維持]: V16-QUAL-03（max_tokens/429 実機検証）は実 API 課金・レート制限誘発が必要なため「未実施（理由付き）」で維持。あわせて ⑤-Claude（Claude 実 API 出力品質・`ANTHROPIC_API_KEY` 未設定）も同様に未実施 → **次マイルストーンで実 API キーが用意でき次第消化**。消化条件は `milestones/v1.9.0-phases/03-qa-release-gate/03-UAT-RESULTS.md`「## 未実施（理由付き・D-14）」に記録済み
- [v1.9.0 コードレビュー由来・技術的負債 10 件]: Phase 1 の WR-01〜WR-06・AR-03、Phase 2 の WR-01/02・IN-01（Warning 4 / Info 6）。`page_ops.py` 側の WR-03〜WR-06 は `file_ops.py` 側で 01-07 が解消済みのパターンの水平展開であり一括で閉じやすい → **v1.10.0 候補（PROJECT.md「Next Milestone Goals」参照）**
- [v1.9.0 Phase 3 検証で Info 記録]: リポジトリルートの追跡外一時ディレクトリ `UsersshdwfAppDataLocalTemppfb/`（過去セッションの pytest basetemp 誤設定による残骸・161 ファイル）が `ruff check .`（無限定）を 31 件のエラーで汚染し、CLAUDE.md チェックリスト文言どおりの実行が失敗する。`pagefolio`/`tests` 限定なら常にクリーン → **`.gitignore` 追加または削除が望ましい**
- [v1.9.0 Phase 3・未検証のまま保存]: D-03 の2仮説（pytest assertion rewriting 後のメモリレイアウト／`tests/test_pdf_ops.py` の二分探索）は症状が再現しなかったため検証していない。再発時の調査入口として `milestones/v1.9.0-phases/03-qa-release-gate/03-TEST-ENV-INVESTIGATION.md`「## 検証しなかった仮説と理由」に保存済み

過去の懸念は全て解決済み:

  - ~~[v1.7.1 Phase 4 UAT] 人手確認7件はユーザー判断で一旦pass（実機目視未検証）~~ → v1.9.0 Phase 3（V190-QA-03）で ⑥〜⑫ として現行コード照合のうえ実機目視により正式消化。v1.4.0/v1.6.0 由来分と合わせ実施13項目すべて pass
  - ~~[06-03 defer・レビューR6] duplicate/merge/merge_resize 等の他ページ構造変更 op に対する do→undo→redo→undo 4手往復回帰テストの水平展開~~ → v1.9.0 Phase 1（01-05・V190-UNDO-02）で完了。境界・隣接・順序・精度の5エッジテストも追加
  - ~~[v1.8.0 Phase 6 由来] IN-01 保存トースト再試行時の上書き確認ダイアログ再表示~~ → v1.9.0 Phase 3（03-01・V190-QA-02）で解消。確認/パス選択層と実保存層 `_do_save_*` の分離＋`bound_doc` による doc 同一性ガード

  - ~~[v1.8.0 リリース作業で発見] フルスイート連続実行で毎回異なる2件が `_tkinter.TclError`（Tk インタプリタ生成失敗）で ERROR になる~~ → v1.9.0 Phase 3（V190-QA-01）で現行 HEAD に対し10回連続実行し 0/10 で非再現を確認。`TCL_LIBRARY`/`TK_LIBRARY` のハードコードは入れずコード変更ゼロでクローズ（`03-TEST-ENV-INVESTIGATION.md` 症状①）
  - ~~[01-07 で特定] フルスイート単一プロセス実行が `test_cancel_finite_time_no_deadlock` 実行中に `Windows fatal exception: 0x80000003`（STATUS_BREAKPOINT）でプロセスごとクラッシュ（約10回中7回）~~ → v1.9.0 Phase 3（V190-QA-01）で同じ10回連続実行にてクラッシュ 0 回。リサーチセッションの7回と合算し累計17回連続グリーン。当面の運用だった分割実行は不要になり、リリースゲートは単一プロセス `pytest -q` 完走に確定（`CLAUDE.md`「## リリースゲート」節・`03-TEST-ENV-INVESTIGATION.md` 症状②）

  - ~~fitz のスレッドセーフ制約~~ → Phase 04 でスレッド境界を明確化（ワーカーには bytes のみ渡す）
  - ~~Gemini Free Tier 10 RPM~~ → Phase 06 で並列度 1 を既定化
  - ~~Claude temperature/effort の実 API 確認~~ → Phase 05 で完了
  - ~~S3 ページネーションのインデックス整合~~ → v1.6.0 Phase 02 で `pagination.py` 純ロジック層に集約して解決
  - ~~v1.7.1 キー解決優先順の反転~~ → Phase 1 で完了（入力値→環境変数）
  - ~~v1.7.1 OCR-04 producer-consumer 一本化~~ → Phase 2 で `ocr_pipeline.py` へ一本化完了
  - ~~v1.7.1 L-1〜L-6 現行照合~~ → 各フェーズ計画時に照合済み、活き残りは全解消
  - ~~v1.7.1 PAGE-02/03・TEST-03 棚卸し→改善~~ → Phase 3/4 で棚卸し・解消完了
  - ~~[05-03 発見] pagefolio/file_ops.py の insert→undo→redo→undo（2回目の undo）でページが重複するバグ~~ → v1.8.0 Phase 6（06-03）で解消。`_restore_state` の `insert_redo` ブロックを `delete_redo` 対称パターン（降順 `delete_page`）へ修正し、4手往復回帰テストで担保（D-17）
  - ~~v1.7.1 Phase 4 follow-up: ShortcutsDialog WR-01（表示残留）/WR-02（キー衝突）~~ → v1.8.0 Phase 5（V180-ROBUST-03）で解消
  - ~~v1.8.0 Phase 6 コードレビュー WR-01/02/03（OCRダイアログ高さクランプ・プラグインダイアログスクロール再発・トースト retry_cb 取りこぼし）~~ → フェーズ検証前に `--fix` で即時修正・回帰テスト追加

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
| 260709-rel | ブランチ claude/prompt-markdown-formatting-1loozg を main へマージし v1.7.4 をリリース。pytest 880 件グリーン・ruff クリーン検証（Windows 実機）、PR #32 マージ、PyInstaller リビルド（`dist/PageFolio` 更新・起動確認済み）、注釈付きタグ `v1.7.4` 付与、GitHub Release を Latest 公開（PageFolio-v1.7.4-win64.zip + .sha256 添付） | 2026-07-09 | 0c92af4 | [260709-rel-v174-merge-release](./quick/260709-rel-v174-merge-release/) |
| 260709-oyg | README.md・CLAUDE.md・開発履歴.md を v1.7.4 の実コード状態へ同期。CLAUDE.md のモジュール構成・OCR モジュール群表・既知の制限に外部プロンプトファイル読込/非同期モデル取得/プロバイダ別タイムアウト/右ペインスクロールを反映、README.md の OCR プロバイダ列挙を6プロバイダへ更新。開発履歴.md は既に同期済みと確認（変更なし） | 2026-07-09 | 67bf570 | [260709-oyg-readme-md-claude-md-md-v1-7-4](./quick/260709-oyg-readme-md-claude-md-md-v1-7-4/) |
| 260722-gae | v1.8.1: Gemini 新世代モデル（gemini-3.6-flash / gemini-3.5-flash-lite）の OCR 400 エラー修正。`_build_generation_config` を世代ゲート化し temperature / thinkingConfig を gemini-2.x 以前のみに送信（`_model_generation` / `_is_legacy_gemini` 新設・回帰テスト 8 件・1109 件グリーン）。dist サンプルプロンプトの実在決済サービス名を架空化。リモート環境実装のため遡及 GSD 精査を 2026-07-22 に完了（[GSD-AUDIT-DIRECTIVE.md](./quick/260722-gae-gemini-api-400-error-5li33o/GSD-AUDIT-DIRECTIVE.md) status: complete・世代ゲート方式確定・RECOMMENDED_MODELS へ gemini-3.x 追加・検証/セキュリティ記録作成） | 2026-07-22 | 58c0de2 | [260722-gae-gemini-api-400-error-5li33o](./quick/260722-gae-gemini-api-400-error-5li33o/) |
| 260722-rel | PR #34（v1.8.1）マージ後のリリース作業。main ツリーとブランチ先端の diff ゼロ確認（pytest 1109 件・ruff の検証流用）、PyInstaller リビルド（`dist/PageFolio` 更新・exe 起動確認済み・サンプルプロンプト 2 ファイルは退避→復元で保全）、注釈付きタグ `v1.8.1` 付与、GitHub Release を Latest 公開（PageFolio-v1.8.1-win64.zip + .sha256 添付） | 2026-07-22 | d7aa217 | [260722-rel-v181-merge-release](./quick/260722-rel-v181-merge-release/) |
| 260810-f1u | v1.9.0向け既存機能レビュー結果を.planning/notesへ文書化 | 2026-08-10 | a553df7 | [260810-f1u-v1-9-0-planning-notes](./quick/260810-f1u-v1-9-0-planning-notes/) |
| 260811-asq | Codex 向け指示書 `AGENTS.md`・`.agents/skills/session-handoff/SKILL.md` の壊れた参照5箇所を修正（`Claude`→`Codex` 一括置換がディレクトリ名・スキル名・ドメイン名を巻き込んだ結果の未存在パス）。両ファイルを追跡対象化し、`.gsd/dispatch-isolation-sentinel.json` を `.gitignore` へ追加 | 2026-08-11 | 3f83067 | [260811-asq-agents-md-agents-skills-session-handoff-](./quick/260811-asq-agents-md-agents-skills-session-handoff-/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| ~~v2~~ | ~~暗号化 PDF 対応~~ | **Shipped v1.6.1**（パスワード付与/解除・AES-256・認証オープン） | Init |
| ~~v2~~ | ~~印刷機能~~ | **Shipped v1.6.1**（Ctrl+P・既定 PDF ハンドラ送信） | Init |
| v2 | プラグイン API バージョン管理 | Out of scope | Init |
| v2 | OS キーストア連携（Windows Credential Manager）による APIキー永続化 | Out of scope | v1.4.0 |
| v2 | OCR 結果のページ埋め込み（検索可能 PDF 化） | Out of scope | v1.4.0 |
| v2 | プロバイダ別の詳細な実コスト計測・課金トラッキング | Out of scope | v1.4.0 |
| ~~Future~~ | ~~PERF-01: サムネイル仮想化によるパフォーマンス改善（大量ページ対応）~~ | **Shipped v1.8.0 Phase 5**（V180-PERF-01〜03） | v1.7.1 |
| v2 | バッチ OCR のバックグラウンド常駐継続（Tkinter シングルループ制約） | Out of scope（v1.8.0 Future Requirements BATCH-F01・v1.9.0 でも v2 継続 V190-F-05） | v1.8.0 |
| v2 | バッチジョブの永続化（アプリ再起動を跨いだ resume） | Out of scope（v1.8.0 Future Requirements BATCH-F02） | v1.8.0 |
| v2 | プロンプトテンプレートのバージョン履歴・差分表示 | Out of scope（v1.8.0 Future Requirements TMPL-F01・v1.9.0 でも v2 継続 V190-F-04） | v1.8.0 |
| v2 | サムネイルの連続スクロール型本格仮想化（react-window 相当） | Out of scope（v1.8.0 Future Requirements PERF-F01・v1.9.0 でも v2 継続 V190-F-06） | v1.8.0 |
| v2 | OpenAI Responses API への移行（ステートフルな会話継続・agentic 機能が必要になった場合） | Out of scope（V190-F-01） | v1.9.0 |
| v2 | organization / project ID の自動検出 | Out of scope（V190-F-02） | v1.9.0 |
| v2 | セッション API キー同期ループの完全動的化（ウィジェット変数のカタログ駆動化） | Out of scope（V190-F-03） | v1.9.0 |

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

### v1.7.1 クローズ時に Acknowledge した項目（2026-07-05）

締め前監査（audit-open）で同一の4件が再検出されたが、v1.4.0・v1.6.0 クローズ時に既受容済（記録上の完了マーカー欠落のみ・実作業は出荷済み）のため、ユーザー判断で今回も受容してクローズ。closeout_type=override_closeout（4件は quick_task の記録マーカー欠落のみ。フェーズ検証は4/4 passed・要件は17/17 Complete で verified）。

| Category | Item | Status |
|----------|------|--------|
| quick_task | 260607-ccz-ocr-llm-llmconfigdialog | unknown（既受容の再掲） |
| quick_task | 260610-aaa-v140-review-fixplan | missing（既受容の再掲） |
| quick_task | 260610-qqq-review-md-260610-aaa-h-1-h-5-v1-4-1 | unknown（既受容の再掲） |
| quick_task | 260610-rkp-v1-4-2-review-md-m-1-m-11 | unknown（既受容の再掲） |

## Session Continuity

**Resume file:** None

Last session: 2026-08-11
Stopped at: v1.9.0 マイルストーンをクローズ・アーカイブ済み（verified_closeout・タグ `v1.9.0` 付与）。次は `/gsd-new-milestone`

## Operator Next Steps

- **次アクション:** `/clear` してから `/gsd-new-milestone` で次マイルストーンを定義する（questioning → research → requirements → roadmap）。候補は PROJECT.md「Next Milestone Goals」を参照
- **タグの push は未実施** — ユーザー選択によりローカルにのみ `v1.9.0` タグを作成した。リリース作業時に `git push origin v1.9.0` を実行する
- **現在ブランチは `feature/v1.9.0`** — `main` へのマージは未実施（`branching_strategy: none` のため本ワークフローでは扱わない）。リリース時に PR / マージを判断する
- サンプルプロンプト 2 ファイル（dist/PageFolio 直下のみ git 管理）が PyInstaller
  `--noconfirm` ビルドで毎回消える恒久課題 — ソースツリー側へ原本移設 + ビルド後
  コピーのスクリプト化を検討課題として保留中（260722-rel SUMMARY 参照）
- 先送り課題（260722-gae 精査項目 3 ②③）: LLM 設定ダイアログへの「新世代 Gemini では
  temperature 欄が無視される」注記（UI 変更）/ 新世代 thinking 有効時の応答時間・
  トークン消費の実測（実 API 必要）— v1.9.0 Phase 2 では合流できず次マイルストーンへ継続
