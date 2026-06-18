---
status: complete
phase: 01-ui-ocr
source: [01-VERIFICATION.md]
started: 2026-06-18T00:00:00Z
updated: 2026-06-18T01:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. 読み取り専用化の目視確認（SC1 / SC2）
expected: OCR 抽出画面を開くと、解像度 / タイムアウト / 最大トークン / temperature の 4 Spinbox とモデル欄が暗背景で値は読めるがスピンボタン・キー入力・選択とも編集不可。preset / 埋め込みテキスト無視 / セッション API キー欄は従来どおり編集可能。
result: pass
note: UAT で判明した不備（readonly Spinbox がスピンボタンで編集可・白地で不可読・モデル取得ボタン残存）と起動クラッシュ（_dialog_w）を修正後にパス。commits 4e60e48 / 66772b9 / 83c8660

### 2. 全プロバイダでの即時反映（D-03 / SC1）
expected: OCR 画面から「⚙ LLM 設定…」を開き、provider を claude もしくは gemini に切り替えて数値（例: timeout）を変更・適用すると、OCR 画面に戻った際に読み取り専用 Spinbox 表示が新しい値へ即時更新される（LM Studio 以外でも反映される）。
result: pass

### 3. 左ペイン縮小時のスライダー可視性（SC3）
expected: アプリ起動後に左ペインを最小幅まで縮小しても、サムネイルサイズ変更スライダーがボタン行下の独立全幅行で潰れず、全選択/解除ボタンと幅を奪い合わずに常に操作可能なまま表示される。
result: pass

### 4. スライダー操作の動作と永続化（SC4）
expected: サムネイルスライダーをドラッグしてマウスを離すとサムネイルサイズが従来どおり変化し、設定が保存される（再起動後も thumb_zoom が保持される）。
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
