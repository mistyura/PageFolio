# Project Research Summary

**Project:** PageFolio v1.8.0「実用性の最大化・エコシステム洗練・堅牢性強化」
**Domain:** Tkinter デスクトップ PDF エディタ（Mixin 構成 + 純ロジック層 + producer-consumer OCR パイプライン）への機能追加
**Researched:** 2026-07-13
**Confidence:** HIGH（既存コードベース .planning/codebase/CONCERNS.md・.planning/PROJECT.md を一次情報源とした curated 調査が中心。外部エコシステム知見は WebSearch で MEDIUM 裏取り）

## Executive Summary

PageFolio v1.8.0 は、既存の Mixin + 純ロジック層アーキテクチャ（pagination.py/ocr_pipeline.py/undo_store.py などの Tk/fitz 非依存層）を崩さずに、AI強化（プロンプト・テンプレートマネージャー、明示設定型プロバイダーフォールバック）・堅牢性強化（サムネイル仮想化 PERF-01、Blobライフサイクル、肥大モジュール分割）・品質保証（E2Eモックテスト、通知UX、UI一貫性監査）・バッチ複数ファイルOCR（単独フェーズ隔離）の4本柱を実装するマイルストーンである。4機能はすべて Python 3.8+ 標準ライブラリのみで実現可能であり、新規 pip 依存の追加は不要（V14-D-01「新規 pip 依存ゼロ方針」継続）。

推奨アプローチは「既存の枯れたプリミティブを拡張する」ことに一貫する。バッチ OCR は ocr_pipeline.py の producer-consumer をファイル単位でもう一段ラップし、プロバイダーフォールバックは PipelineState.fatal_msg 確定後のオーケストレーション層として追加し、サムネイル仮想化は pagination.py の窓表示の外層は不変のまま可視範囲計算のみを新規純関数層として内側に重ねる。テンプレートマネージャーは v1.7.4 の外部 md ファイル連動を「複数の名前付きスロット」へ拡張する形で後方互換を保つ。

最大のリスクは3点。(1) fitz.Document のスレッド非共有制約をバッチOCRで破ること（ファイル間逐次処理が必須、multiprocessing は導入しない）、(2) サムネイル仮想化で pagination.py の selected_pages 全ページインデックス不変条件・D&D窓またぎバグ対策を新しい座標系で再発させること、(3) プロバイダーフォールバックが「明示設定型・自動ベンダー切替なし」という確定方針を確認ダイアログ省略という近道で迂回してしまうこと。いずれも既存の原則（V14-D-05/06、V16-D-01、V14-D-03、OCR-SEC-01/UI-01）をそのまま拡張適用すれば防止できる。

## Key Findings

### Recommended Stack

新機能はすべて標準ライブラリ（queue.Queue・concurrent.futures.ThreadPoolExecutor・threading.Lock・json・os）で実現し、新規 pip 依存は追加しない。サムネイル仮想化の代替候補として tksheet（依存ゼロの軽量テーブルライブラリ）を検討したが、既存の D&D グリッドUIと操作モデルが異なり全面書き換えが必要になるため不採用。dataclasses/pydantic/asyncio/multiprocessing もそれぞれ理由付きで不採用と判断されている。

**Core technologies:**
- queue.Queue + ThreadPoolExecutor + threading.Lock: バッチOCRのファイル単位ジョブキュー・並列送信。既存 ocr_pipeline.py の PipelineState/consume_one パターンをそのまま一段拡張できる
- json + dict ベース永続化: テンプレート管理・フォールバック順の設定保存。settings.py の既存 _load_settings/_save_settings パターンと同型で一貫性を保てる
- tkinter.Canvas + 既存 pagination.py: サムネイル仮想化。窓表示（既定20・上限100件）の外層はそのまま、可視範囲のみ実体化する内層を純関数として追加する

### Expected Features

**Must have（v1.8.0 で確実に入れる最小ライン）:**
- プロンプト・テンプレートマネージャー: 名前付き保存・一覧選択・削除（CRUD最小4操作）、既存外部mdファイル連動との共存必須
- プロバイダーフォールバック: 明示順序設定 + 切替時の送信先確認再提示（既存コスト確認ダイアログ再利用）
- サムネイル仮想化: thumb_cache の LRU eviction + 大量ページでの性能回帰テスト
- エラー時リカバリー通知: 軽微エラー向け非モーダルトースト1種（再試行ボタン付き・自動消滅なし）
- バッチ複数ファイルOCR: キュー一覧 + 個別/全体進捗 + 失敗分離 + D&D投入 + 逐次処理（ダイアログ内完結・バックグラウンド常駐なし）

**Should have（差別化要素）:**
- フォールバック時の送信先確認再提示（他のLLMゲートウェイ実装には見られない独自の安全設計）
- バッチOCRの全ページ統合サマリのファイル横断拡張（v1.6.0既存資産の延長）
- プロバイダ横断でのテンプレート共有（resolve_ocr_prompt の優先順位にテンプレート層を挟む）

**Defer（v2+）:**
- バッチOCRのバックグラウンド継続（Tkinterシングルループ制約でUI設計コストが高い）
- プロンプトテンプレートのバージョン履歴・差分表示
- サムネイルの連続スクロール型本格仮想化（react-window相当への作り替え）
- 自動ベンダー切替・コスト最適化ルーティング・確認なし連鎖リトライ（プライバシー方針違反のため明確に排除）

### Architecture Approach

既存の8 Mixin構成 + Tk/fitz非依存の純ロジック層（pagination.py/ocr_pipeline.py/undo_store.py）というアーキテクチャ哲学を維持し、新機能はすべて「既存プリミティブの上に薄いオーケストレーション層を追加する」形で統合する。肥大モジュール分割（ocr_providers.py→llm_config.py→ocr_dialog.pyの順）を先行させ、OCRRunEngine として producer/consumer 駆動部をダイアログUIから抽出することで、単一ファイルOCRとバッチOCRの両方がこれを再利用できる設計にする。

**Major components:**
1. batch_queue.py（新規・純ロジック層） — ファイルキューの状態遷移管理（BatchQueueState）。ファイル単位は逐次、ファイル内は既存PipelineStateを使い回す二層構造
2. provider_fallback.py（新規・純ロジック層） — フォールバック順リストからの次候補決定（純関数）。PipelineState.fatal_msg確定後のUI層でのみ判断し、run_parallel/consume_oneには混ぜ込まない
3. thumb_virtualizer.py（新規・純ロジック層） — スクロール位置から可視ローカルindex範囲を計算する純関数。pagination.pyのto_global/to_local契約は完全不変のまま外側に重ねる
4. ocr_engine.py（新規・抽出） — OCRDialogから producer/consumer 駆動部（OCRRunEngine）を抽出し、バッチOCRと単一ファイルOCRで共用
5. settings.py拡張 — 名前付きテンプレートCRUD関数群（既存load_prompt_file/save_prompt_fileの再パラメータ化）

### Critical Pitfalls

1. サムネイル仮想化がselected_pages全ページインデックス不変条件を破壊する — 仮想化のスクロール位置計算もpagination.pyのto_global/to_localのみを通し、新規座標変換モジュールを増やさない
2. バッチOCRがfitz.Documentのスレッド間共有禁止を破る — ファイル間は逐次処理のみ許可し、fitz.open/get_pixmapはメインスレッドの単一キューで直列化
3. プロバイダーフォールバックが「明示同意・コスト確認」方針を迂回する — フォールバック発火時も送信先確認ダイアログを必ず再提示
4. テンプレートマネージャーが外部mdファイル連動（v1.7.4）と書き戻し競合を起こす — 外部mdファイルは常に「現在アクティブなテンプレートのライブ編集内容」に限定
5. 肥大モジュール分割で後方互換importが壊れる — 分割前に必ずtest_imports.pyへ後方互換importテストを追加してから着手

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: 基盤分割（肥大モジュールリファクタリング・前半）
**Rationale:** 新機能追加前にocr_providers.py（1424行）とllm_config.py（1204行）のパッケージ化を先行させ、以降のフェーズの作業対象を軽量化する
**Delivers:** pagefolio/ocr_providers/パッケージ・pagefolio/dialogs/llm_config/パッケージ（re-export で後方互換維持）
**Uses:** DEBT-01/DEBT-02前例パターン
**Avoids:** 落とし穴9（後方互換import破壊）— test_imports.py拡張を分割の一部として必須化

### Phase 2: プロンプト・テンプレートマネージャー
**Rationale:** 分割後のllm_config/構造にそのまま新規UI（prompt_panel.py）を追加できる。バッチOCRより依存が少なく先行させやすい
**Delivers:** 名前付きテンプレートCRUD（settings.py拡張）・prompt_templates/ディレクトリ・テンプレート選択UI
**Addresses:** FEATURES.md「プロンプト・テンプレートマネージャー」Table Stakes
**Avoids:** 落とし穴6（外部mdファイル書き戻し競合）

### Phase 3: 明示設定型プロバイダーフォールバック
**Rationale:** Phase 2で整備したllm_config/のUI構造に、フォールバック順編集UIを同一セクションに隣接追加できる
**Delivers:** provider_fallback.py（純ロジック）・ocr.pyへのprovider_override引数追加・フォールバック確認ダイアログ統合
**Implements:** ARCHITECTURE.md (b)の設計（PipelineState.fatal_msg確定後のオーケストレーション層）
**Avoids:** 落とし穴7（同意方針迂回）・落とし穴8（設定引き継ぎミス）

### Phase 4: ocr_dialog.py分割（OCRRunEngine抽出）
**Rationale:** バッチOCRが必要とする「単一ドキュメントOCR実行エンジン」の抽出と同一作業のため、バッチOCR着手の直前に行うのが最も手戻りが少ない
**Delivers:** pagefolio/ocr_engine.py（OCRRunEngine）・縮小されたocr_dialog.py
**Avoids:** 落とし穴10（スレッド調整コード分離時のロック不整合）

### Phase 5: バッチ複数ファイルOCR（単独フェーズ隔離）
**Rationale:** PROJECT.mdで「大型機能として単独フェーズへ隔離」と確定済み。最も依存が多く最大の機能のため、先行する基盤機能が固まってから着手するのが安全
**Delivers:** batch_queue.py（純ロジック）・pagefolio/dialogs/batch_ocr.py（BatchOCRDialog）・ファイル横断サマリ
**Addresses:** FEATURES.md「バッチ複数ファイルOCR」Table Stakes全般
**Avoids:** 落とし穴3（fitzスレッド間共有違反）・落とし穴4（キャンセルスコープ不足）・落とし穴5（進捗集計二重矛盾）

### Phase 6: サムネイル仮想化（PERF-01）
**Rationale:** 他の4機能と機能的依存がなく独立して着手可能。既存pagination.py/viewer.pyの局所改修で完結する
**Delivers:** thumb_virtualizer.py（純ロジック）・viewer.pyの_build_thumbnails()/_reflow_thumbnails()変更・thumb_cacheのLRU化
**Avoids:** 落とし穴1（selected_pages不変条件破壊）・落とし穴2（thumb_cache責務混同）

### Phase 7: 品質保証（E2Eモックテスト・通知UX・UI一貫性監査）
**Rationale:** OCRRunEngine/batch_queueの抽出が完了した後の方がテスト容易性が高いため、Phase 4・5の後に厚めに配置するのが効率的
**Delivers:** 非モーダルトースト通知・E2Eモックテストスイート・UI一貫性監査
**Addresses:** FEATURES.md「エラー時リカバリー通知の改善」Table Stakes

### Phase Ordering Rationale

- モジュール分割（Phase 1・4）を新機能追加の直前に配置するのは「新機能が触るファイルを複雑化する前に土台を整える」原則に基づく
- テンプレートマネージャー→フォールバックの順序は、両者が同一UIコンポーネントを共有するため隣接配置で作業効率が上がる
- バッチOCRを単独フェーズとして他機能の後半に配置するのは、PROJECT.mdの確定方針かつ最も依存が多く最大の機能であることに基づく
- サムネイル仮想化は依存なしのため並行実施も可能だが、品質保証フェーズでのテスト厚みを考えるとPhase 5以降に置く方が回帰リスクの検証がしやすい

### Research Flags

Phases likely needing deeper research during planning:
- Phase 5（バッチ複数ファイルOCR）: ファイル横断の進捗集計・2階層キャンセル・ファイル横断サマリのメモリ管理は新規パターンのため実装詳細検証が有効
- Phase 6（サムネイル仮想化）: Tkinter Canvasでのウィジェットリサイクル方式の性能特性はWeb情報がLOW確信度のため、実装前にプロトタイプ検証が望ましい

Phases with standard patterns (skip research-phase):
- Phase 1・4（モジュール分割）: DEBT-01/DEBT-02の確立済み前例をそのまま踏襲すれば良い
- Phase 2（テンプレートマネージャー）: 既存load_prompt_file/save_prompt_fileパターンの延長で完結
- Phase 3（プロバイダーフォールバック）: 既存build_provider/コスト確認ダイアログの再利用のみで実装コストは低い

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | 標準ライブラリ機能自体・PyMuPDFスレッド安全性は公式ドキュメント/Issue準拠でHIGHだが、Tkinter仮想化の具体実装例は一般Web情報中心でLOW寄り |
| Features | MEDIUM | 複数ソース間で傾向が一致する部分（トーストUX・フォールバックchain・バッチキューUX）はMEDIUM、単一ソースのみの部分はLOWと個別明記 |
| Architecture | HIGH | 実コードベース直接精査に基づく一次情報源（curated相当） |
| Pitfalls | HIGH | .planning/codebase/CONCERNS.md・.planning/PROJECT.mdを一次情報源とするcurated調査。一般原則のみMEDIUM裏取り |

**Overall confidence:** HIGH（アーキテクチャ・落とし穴は自プロジェクト資産に基づく高確信度。スタック・機能面は業界一般論の部分でMEDIUM〜LOWが混在するが、実装方針への影響は限定的）

### Gaps to Address

- サムネイル仮想化のウィジェットリサイクル方式の性能実測: 生成方式 vs リサイクル方式のどちらが実際に速いかはWeb情報のみでは判断できないため、Phase 6着手時にプロトタイプで実測してから設計確定する
- バッチOCRの永続化要否: 要件に「アプリ再起動をまたぐジョブ再開」が含まれるか未確定。STACK.mdはjsonスナップショット方式を代替案として用意しているが、FEATURES.mdのAnti-Featuresでは「過剰」と位置付けており、Phase 5計画時に要件を再確認する
- PyMuPDF 1.28.0への追随要否: 現行1.27.2.2のままで問題ないと判断しているが、次回メンテナンス時の検討事項として残っている

## Sources

### Primary (HIGH confidence)
- pagefolio/ocr_pipeline.py・pagefolio/settings.py・pagefolio/pagination.py（社内一次情報・コードベース直接確認）
- .planning/PROJECT.md・.planning/codebase/CONCERNS.md（v1.8.0マイルストーン方針・既知課題の一次情報）
- Is PyMuPDF re-entrant / thread-safe? Issue #107 pymupdf/PyMuPDF (https://github.com/pymupdf/PyMuPDF/issues/107)
- Clarification about threading Issue #1994 pymupdf/PyMuPDF (https://github.com/pymupdf/PyMuPDF/issues/1994)

### Secondary (MEDIUM confidence)
- Fallbacks (Provider Failover) liteLLM (https://docs.litellm.ai/docs/proxy/reliability)
- Batch Processing Queue AI UX Playground (https://aiuxplayground.com/pattern/batch-processing-queue/)
- Notification pattern Carbon Design System (https://carbondesignsystem.com/patterns/notification-pattern/)
- List Virtualization patterns.dev (https://www.patterns.dev/vanilla/virtual-lists/)

### Tertiary (LOW confidence)
- Understanding Tkinter Canvas Performance Limitations ancisoft.com (https://www.ancisoft.com/blog/understanding-performance-limitations-of-the-tkinter-canvas/)
- tksheet PyPI (https://pypi.org/project/tksheet/)

---
*Research completed: 2026-07-13*
*Ready for roadmap: yes*
