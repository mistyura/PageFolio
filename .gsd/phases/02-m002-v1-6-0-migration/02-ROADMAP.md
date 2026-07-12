# M002: M002: M002: M002: v1.6.0 Migration

**Vision:** PageFolio の既存コードベースに対する最適化プロジェクト。

## Slices

- [x] **S01: Ui Ocr** `risk:medium` `depends:[]`
  > After this: OCR 抽出画面（`OCRDialog`）の永続的な数値パラメータ UI を読み取り専用化し、編集導線を「⚙ LLM 設定…」（`LLMConfigDialog`）へ一元化する。これにより「OCR 画面と LLM 設定画面のどちらの値が効くか分からない」二重化（V16-UI-01）を解消する。読み取り専用表示は現在適用される値を見える状態で維持し（完全撤去ではなく D-01/D-04 の「読み取り専用化」を採用）、LLM 設定で値を変更・適用した直後に OCR 画面の表示も即時反映する（D-03）。

- [x] **S02: Pagination** `risk:medium` `depends:[S01]`
  > After this: 本フェーズの中核である「表示窓のローカル位置 ↔ 全ページインデックス」変換を、Tkinter 非依存の純関数群として新規モジュール `pagefolio/pagination.

- [x] **S03: Ocr A** `risk:medium` `depends:[S02]`
  > After this: H1 ページ回転のプレビュー即時反映バグ（V16-QUAL-01）を「描画追加」ではなく「実機再現 → 真因特定 → 原因除去」で解消する。

- [x] **S04: Ai C** `risk:medium` `depends:[S03]`
  > After this: V16-AI-01 の純ロジック層を新設する。OCR 結果の Markdown 文字列を「行種別 + インライン span」の構造データへ変換する Tk 非依存の純関数 `parse_markdown`（および内部ヘルパー `_split_inline`）を新規モジュール `pagefolio/md_render.
