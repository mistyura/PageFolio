# Phase 3: OCR実行エンジン抽出 + E2Eテスト - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-14
**Phase:** 3-OCR実行エンジン抽出 + E2Eテスト
**Areas discussed:** 抽出境界（producerの所在）, UI通知インターフェース, 状態保持の所有権, E2Eテストの忠実度

---

## 抽出境界（producerの所在）

### Q1: producer（fitzレンダリング連鎖・_render_next_page相当）はOCRRunEngineに内包するか、呼び出し側が持ち続けるか

| Option | Description | Selected |
|--------|-------------|----------|
| 呼び出し側が保持 | ocr_pipeline.pyの既存方針（producerのスレッドモデルは規定しない）と一致。Engineはconsumerのみ提供 | ✓ |
| Engineが内包 | render用コールバックを注入する方式。利用は薄くなるがTk非依存性が崩れやすい | |

**User's choice:** 呼び出し側が保持

### Q2: OCRRunEngineのコンストラクタ（または実行メソッド）に何を渡すか

| Option | Description | Selected |
|--------|-------------|----------|
| 最小限の値渡し | provider・prompt・run_pages・concurrency・cancel_flag・コールバック群のみ | ✓ |
| 設定dict丸ごと渡し | self._active_ocr_settings相当をそのまま渡す | |

**User's choice:** 最小限の値渡し

### Q3: 新モジュールの配置

| Option | Description | Selected |
|--------|-------------|----------|
| pagefolio/ocr_engine.py（単一ファイル） | research/SUMMARY.mdの推奨名。ocr_pipeline.pyと対になる単一責務モジュール | ✓ |
| pagefolio/ocr_engine/ サブパッケージ | Phase1前例に倣うが抽出対象がクラス1つ相当のため過剰分割 | |

**User's choice:** pagefolio/ocr_engine.py（単一ファイル）

### Q4: OCRDialog側の_worker/_render_next_page等は分割後どうなるか

| Option | Description | Selected |
|--------|-------------|----------|
| 薄いラッパーメソッドとして維持 | 現状のocr_pipeline.py委譲と同じ形。メソッド名・シグネチャ維持 | ✓ |
| OCRDialogから該当メソッドを削除しEngineを直接呼ぶ | 呼び出し側の記述は簡潔になるが変更差分が大きい | |

**User's choice:** 薄いラッパーメソッドとして維持

**Notes:** この4問への回答は一貫して「既存の枯れたパターン（ocr_pipeline.pyの設計方針・consume_one委譲の形）をそのまま踏襲し、新しい抽象化を増やさない」という方向で揃った。

---

## UI通知インターフェース

### Q1: EngineからOCRDialogへの進捗/結果通知の方式

| Option | Description | Selected |
|--------|-------------|----------|
| コールバック注入方式 | consume_oneの既存on_success/on_page_error/on_retry_wait方式を踏襲 | ✓ |
| Tk非依存のイベントキュー | Engine内部queueにイベントを積み、OCRDialogがafter()ポーリング | |

**User's choice:** コールバック注入方式

### Q2: on_success/on_page_error等の個別コールバックを統合するか

| Option | Description | Selected |
|--------|-------------|----------|
| 現状の個別コールバックを維持 | on_success/on_page_error/on_fatal/on_retry_wait個別 | ✓ |
| 単一on_event(kind, payload)に統合 | 新しい抽象化層。将来のイベント種追加は容易だが変換レイヤーが増える | |

**User's choice:** 現状の個別コールバックを維持

### Q3: 統合進捗集計（_done_disp相当）は誰が持つか

| Option | Description | Selected |
|--------|-------------|----------|
| Engineが持つ | skip/render_failed/PipelineState.done_countを一元集計しコールバックで数値を渡す | ✓ |
| 呼び出し側が持つ | 現状の_done_disp()をOCRDialogに残す | |

**User's choice:** Engineが持つ

### Q4: complete/cancelled/fatalの終了理由の伝え方

| Option | Description | Selected |
|--------|-------------|----------|
| 理由別の個別コールバック | on_complete()/on_cancelled()/on_fatal(msg,kind) | ✓ |
| 単一on_finished(reason, msg, kind) | 呼び出し側の実装はif分岐が増えるがコールバック数は減る | |

**User's choice:** 理由別の個別コールバック

**Notes:** 進捗集計をEngine側に寄せた（Q3）ことで、バッチOCR（Phase4）が同じ集計ロジックを再利用できる設計になった。

---

## 状態保持の所有権

### Q1: results/errors/skipped_pages/truncated_pages/render_failed_pagesの所有権

| Option | Description | Selected |
|--------|-------------|----------|
| Engineが所有 | PipelineStateと同格の内部状態。バッチOCRでファイル単位に独立した結果セットを持てる | ✓ |
| OCRDialogに残す | 現状の_record_page_success/_record_page_errorをそのまま維持 | |

**User's choice:** Engineが所有

### Q2: resume判断に使うrun_pages/履歴はどちらが持つか

| Option | Description | Selected |
|--------|-------------|----------|
| 引数としてEngineに毎回渡す | resume判断（_pending_pages()相当）はOCRDialogが行い、確定run_pagesのみ渡す | ✓ |
| Engineが前回のresults/errorsを継承し判断 | Engineの責務が増える | |

**User's choice:** 引数としてEngineに毎回渡す

### Q3: Engineインスタンスのライフサイクル

| Option | Description | Selected |
|--------|-------------|----------|
| 実行ごとに新規作成 | _run_gen世代ガードと同種の安全性を構造的に得る | ✓ |
| 1つのEngineを使い回しリセットメソッドを呼ぶ | メモリ割当は減るがreset()呼び忘れリスク | |

**User's choice:** 実行ごとに新規作成

### Q4: ベースライン管理（_skip_base相当）は誰が持つか

| Option | Description | Selected |
|--------|-------------|----------|
| Engineが持つ | Q3（進捗集計をEngineが持つ）決定と一貫 | ✓ |
| 呼び出し側が持つ | OCRDialogが_skip_base/_render_failed_baseを管理 | |

**User's choice:** Engineが持つ

**Notes:** 状態保持の4問すべてで「Engineへの集約」が選ばれ、UI通知インターフェースの決定（進捗集計をEngineが持つ）と一貫した設計になった。

---

## E2Eテストの忠実度

### Q1: E2Eモックテストの実行方式

| Option | Description | Selected |
|--------|-------------|----------|
| 実スレッド実行を伴う統合テスト | threading.Threadを実際に起動しqueueを通す。最も高忠実度だがflaky化リスクに留意 | ✓ |
| 同期呼び出し中心のオーケストレーションテスト | consume_oneを直接ループで呼ぶ。test_ocr_pipeline.py流儀 | |

**User's choice:** 実スレッド実行を伴う統合テスト

### Q2: フェイクProviderの用意方針

| Option | Description | Selected |
|--------|-------------|----------|
| 既存FakeProviderパターンを再利用 | test_ocr_pipeline.py/test_ocr_providers.pyのFakeProviderを拡張 | ✓ |
| E2E専用の新規FakeProviderを作る | シナリオ固有の振る舞いを表現しやすいが重複が増える | |

**User's choice:** 既存FakeProviderパターンを再利用

### Q3: 「OCR→サマリの一気通貫フロー」のカバレッジ範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 正常系+異常系+サマリ生成までフルカバー | 複数ページ成功・エラー混在・キャンセル・fatal・サマリ生成(complete_text_ex相当)を網羅 | ✓ |
| 正常系OCR実行のみE2E化、サマリ/異常系は別途ユニットテスト | E2Eのスコープを狭め実装コストを下げる | |

**User's choice:** 正常系+異常系+サマリ生成までフルカバー

### Q4: 新規E2Eテストファイルの配置

| Option | Description | Selected |
|--------|-------------|----------|
| 新規 tests/test_ocr_engine.py | ocr_engine.pyの単体テスト + E2Eシナリオを同居。test_ocr_pipeline.pyとの対応関係が明確 | ✓ |
| 既存 tests/test_ocr_pipeline.py に追加 | ファイル数は増えないが純ロジック層テストとEngine統合テストが混在 | |

**User's choice:** 新規 tests/test_ocr_engine.py

**Notes:** E2Eテストは高忠実度（実スレッド実行・フルカバレッジ）を優先する選択で一貫。既存資産（FakeProviderパターン）の再利用によりflaky化・実装コストのリスクを抑える方針とした。

---

## Claude's Discretion

- `OCRRunEngine` クラスの詳細なメソッドシグネチャ名（`run()`/`start()` 等）・引数の型ヒント
- コールバック関数群の正確な引数順序・命名
- `PipelineState` の生成タイミング（コンストラクタ内 vs 実行メソッド呼び出し時）
- `tests/test_ocr_engine.py` 内のテストクラス構成（`TestOCRRunEngine*` の分割単位）

## Deferred Ideas

None — discussion stayed within phase scope（4領域とも計画どおり完了。スコープ外提案は出なかった）
