---
status: testing
phase: 04-ui-ux
source: [04-VERIFICATION.md]
started: 2026-07-05T00:00:00Z
updated: 2026-07-05T00:00:00Z
---

## Current Test

number: 1
name: SettingsDialog の「⌨ ショートカット設定…」ボタンから ShortcutsDialog を開き、各行の「変更」を押して実キーを押下し、keysym が正しくキャプチャされる（修飾キー単体 Control_L 等では確定せず待機継続する）ことを目視確認する
expected: |
  行のキー表示が押下したキーの人間可読表記（例: Ctrl+O）へ更新され、修飾キー単体では待機状態が続く
awaiting: user response

## Tests

### 1. SettingsDialog の「⌨ ショートカット設定…」ボタンから ShortcutsDialog を開き、各行の「変更」を押して実キーを押下し、keysym が正しくキャプチャされる（修飾キー単体 Control_L 等では確定せず待機継続する）ことを目視確認する
expected: 行のキー表示が押下したキーの人間可読表記（例: Ctrl+O）へ更新され、修飾キー単体では待機状態が続く
result: [pending]

### 2. 同一キーを別コマンドへ割り当てて「保存」を押し、衝突コマンド名を含むエラーダイアログが表示され保存が拒否されることを目視確認する
expected: showerror ダイアログに衝突コマンドの表示名が含まれ、settings への書き込みが行われずダイアログも閉じない
result: [pending]

### 3. ショートカットを保存した直後（ダイアログを閉じる前）に、新しいキーで実際にコマンドが起動することを目視確認する
expected: 保存ボタン押下時点で app._bind_shortcuts() が呼ばれ、新キーが即座に有効になる
result: [pending]

### 4. SettingsDialog が「外観」「操作」「AI・OCR」の3セクションで表示され、見出しの視覚的な区切り・アイコン（⚙）が意図通りであることを目視確認する
expected: 3セクションが区切り線とともに順に表示され、旧🔍アイコンが⚙に置き換わっている
result: [pending]

### 5. LLMConfigDialog を開き、「選択中プロバイダ固有の設定」「全プロバイダ共通の設定」の2見出しが正しい位置に表示され、プロバイダ切替（LM Studio/Ollama/RunPod/Claude/Gemini/Tesseract/off）で固有セクションが正しく入れ替わることを目視確認する
expected: 見出し順序が 固有見出し→固有フレーム→共通見出し→共通パラメータ という設計通りに視覚的に維持される
result: [pending]

### 6. 外側 SettingsDialog を開いた状態で「⚙ LLM 設定…」から LLMConfigDialog を開き、値を変更して「適用」を押した後、外側 SettingsDialog を「キャンセル」で閉じても、再度設定を開くと LLM 設定の変更が保持されていることを目視確認する
expected: 外側キャンセル後も LLM 設定（例: プロバイダ選択やタイムアウト値）が変更後の値のまま維持される
result: [pending]

### 7. 拡大ポップアップ（サムネイルまたはページをダブルクリック等で開く画面）を lang='en' 設定で開き、タイトル・縮小/拡大/閉じるボタンが英語で表示され日本語が一切出ないことを目視確認する
expected: ポップアップの全文言が英語（Page N / M、Zoom Out、Zoom In、Close）で表示される
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
