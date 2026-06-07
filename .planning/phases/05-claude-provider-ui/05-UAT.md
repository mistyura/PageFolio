---
status: complete
phase: 05-claude-provider-ui
source:
  - 05-01-SUMMARY.md
  - 05-02-SUMMARY.md
  - 05-03-SUMMARY.md
  - 05-04-SUMMARY.md
  - 05-05-SUMMARY.md
started: 2026-06-07T01:41:24Z
updated: 2026-06-07T01:50:00Z
---

## Current Test

[testing complete]

## Tests

### 1. プロバイダ選択ドロップダウン
expected: LLM 設定ダイアログを開くと、プロバイダ選択ドロップダウンに off / lmstudio / claude が表示され選択できる。
result: pass

### 2. claude 選択で欄切替
expected: プロバイダで claude を選ぶと、LM Studio の URL 欄が消え、claude モデル選択欄が表示される。lmstudio に戻すと URL 欄が再表示される。
result: pass

### 3. モデル別 effort / temperature 切替
expected: claude モデルで opus / sonnet 系を選ぶと effort 欄（low〜max）が、haiku 系を選ぶと temperature 欄が表示される（モデルに応じて自動切替）。
result: pass

### 4. APIキー未設定でもモデル更新
expected: ANTHROPIC_API_KEY 未設定でも「モデル更新」ボタンを押すと静的な推奨モデルリストが表示され、「静的リスト表示中」のステータスが出る（エラーで固まらない）。
result: pass

### 5. off 時の OCR ボタン無効化
expected: プロバイダを off にして適用すると、PDF を開いても OCR ボタン（現在ページ／選択ページ）が押せない（disabled）。
result: pass

### 6. セッションキー入力欄（マスク表示）
expected: claude で OCR を実行する際、ANTHROPIC_API_KEY が環境変数に未設定なら、マスク（****）付きのセッションキー入力欄が表示される。環境変数設定済みなら入力欄は出ない。
result: pass

### 7. キー未入力で実行するとエラー
expected: claude を選び、APIキーを環境変数にもセッション欄にも入れずに OCR を実行すると、キー未設定のエラーメッセージが出て OCR は始まらない（外部送信しない）。
result: pass

### 8. コスト確認ダイアログ
expected: claude で OCR を実行すると、開始前にコスト確認ダイアログが出て、送信先・ページ数・概算コスト・プライバシー注記が表示される。
result: pass

### 9. コスト確認キャンセルで中止
expected: コスト確認ダイアログで「いいえ／キャンセル」を選ぶと OCR は開始されない。
result: pass

### 10. settings.json にAPIキーが残らない
expected: セッションキー欄に入力して OCR を実行した後、pagefolio_settings.json を開いても API キー文字列が一切書き込まれていない。
result: pass

### 11. lmstudio 後方互換
expected: プロバイダを lmstudio に戻すと、URL/モデル欄が表示され OCR ボタンも有効になり、従来どおり OCR が動作する。
result: pass

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
