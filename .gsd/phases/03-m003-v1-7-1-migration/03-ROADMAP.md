# M003: M003: M003: M003: v1.7.1 Migration

**Vision:** PageFolio の既存コードベースに対する最適化プロジェクト。

## Slices

- [x] **S01: Api Llm** `risk:medium` `depends:[]`
  > After this: キー解決ロジックの優先順を「環境変数 → セッションキー」から「セッションキー(入力値) → 環境変数」へ反転し（V171-KEY-02 の核心・D-08 系の土台）、本フェーズの UI/ゲートが参照する新規 LANG 文言（ja/en）を先行整備する。あわせて反転仕様を固定する解決系テスト（claude/gemini の書き換え + RunPod 新設）を整備する（V171-KEY-04 の解決層・V171-TEST-02 の一部）。

- [x] **S02: Ocr** `risk:medium` `depends:[S01]`
  > After this: V171-OCR-03（L-2/L-3）を解消する。プラグイン OCR provider registry を堅牢化し、

- [x] **S03: V1 5 0** `risk:medium` `depends:[S02]`
  > After this: 画像（ロゴ等）を透かしとしてページへ追加できるようにする（V171-PAGE-01・D-01〜D-04）。既存のテキスト透かし（`_add_watermark_text`）と同一の「ボタン→ファイル選択→即適用→page_edit undo」フローを踏襲し、`page.

- [x] **S04: Ui Ux** `risk:medium` `depends:[S03]`
  > After this: ショートカット GUI 編集（V171-UIUX-01）の基盤を作る。`app.
