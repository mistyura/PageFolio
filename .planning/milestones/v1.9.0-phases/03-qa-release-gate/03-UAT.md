---
status: complete
phase: 03-qa-release-gate
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md]
started: 2026-08-11T12:24:45Z
updated: 2026-08-11T12:26:18Z
---

## Current Test

[testing complete]

## Tests

### 1. 再現試行ログの一次データ記録（10回連続実行）
expected: 03-TEST-ENV-INVESTIGATION.md の「## 再現試行ログ」に10行の表があり、各行に実行コマンド・passed/failed/error 件数・クラッシュ有無・TclError 有無が一次データとして記録されている（全10回 1398 passed / 0 failed / 0 error・クラッシュなし）
result: pass
coverage_id: D1
coverage_source: 03-02-SUMMARY.md
note: coverage ブロックの verification[0].kind が `manual`（未定義値）のため自動判定できず、人手確認へ回された項目

### 2. 保存トースト再試行が確認ダイアログを経由せず黙って再保存する（保存3経路）
expected: 保存トーストの retry_cb を呼ぶと askyesno/asksaveasfilename を経由せず、前回確定した対象へ黙って再保存される（保存3経路すべて）
result: pass
source: automated
coverage_id: D1
coverage_source: 03-01-SUMMARY.md

### 3. 初回保存では従来どおり確認ダイアログ・保存先ピッカーが出る
expected: 初回の保存操作では従来どおり確認ダイアログ・保存先ピッカーが表示される（確認スキップは再試行経路にのみ適用）
result: pass
source: automated
coverage_id: D2
coverage_source: 03-01-SUMMARY.md

### 4. retry_cb は束縛時のパスにのみ書き込み、クローズ後は書き込まない
expected: トースト表示中にアプリ状態（filepath/doc）が変化しても、retry_cb は束縛時のパスにのみ書き込み、ファイルクローズ後は書き込まない
result: pass
source: automated
coverage_id: D3
coverage_source: 03-01-SUMMARY.md

### 5. V190-QA-02 のドキュメント文言と実装の一致
expected: REQUIREMENTS.md / ROADMAP.md の V190-QA-02 関連文言が実装（再試行時は確認を再表示しない）と一致している
result: pass
source: automated
coverage_id: D4
coverage_source: 03-01-SUMMARY.md

### 6. 2症状（TclError / STATUS_BREAKPOINT）が別々に結論づけられている
expected: STATUS_BREAKPOINT クラッシュと TclError セットアップ ERROR が同じ実験内で並行観測されつつ別症状として別々に結論づけられている
result: pass
source: automated
coverage_id: D2
coverage_source: 03-02-SUMMARY.md

### 7. 非再現につきコード変更ゼロで「解消済み」記録を確定
expected: 再現しなかったため pagefolio/ にも tests/ にもコード変更を入れず「現行環境では解消済み」と一次データ付きで記録して閉じた
result: pass
source: automated
coverage_id: D3
coverage_source: 03-02-SUMMARY.md

### 8. リリースゲートの合格条件が CLAUDE.md から実行可能な形で読める
expected: リリースゲートの合格条件が CLAUDE.md から実行可能な形で読め、そのコマンドが失敗0件で完走する
result: pass
source: automated
coverage_id: D4
coverage_source: 03-02-SUMMARY.md

### 9. 遡及UAT候補16項目の仕分け（実施対象/未実施/対象外）
expected: 遡及UAT候補14項目（+v1.9.0分2項目+Phase2対象外1項目）が現行コードと照合され、実施対象/未実施（理由付き）/対象外へ仕分けられた（D-13）
result: pass
source: automated
coverage_id: D1
coverage_source: 03-03-SUMMARY.md

### 10. グループ1（ショートカット・保存トースト）4項目の実機確認
expected: ShortcutsDialog 実キーキャプチャ・キー衝突拒否・保存直後反映・保存トースト再試行確認スキップの4項目がユーザーの実機目視で確認され pass
result: pass
source: automated
coverage_id: D2
coverage_source: 03-03-SUMMARY.md

### 11. グループ2（設定/LLM ダイアログ）5項目の実機確認
expected: SettingsDialog 3セクション・LLMConfigDialog 見出し順序と8プロバイダ切替・外側 Cancel 保持・拡大ポップアップ英語表示・Undo 復元失敗ブロック通知の5項目がユーザーの実機目視で確認され pass
result: pass
source: automated
coverage_id: D3
coverage_source: 03-03-SUMMARY.md

### 12. グループ3（LLM 出力・モデル切替）実施対象4項目の実機確認
expected: markdown 整形表示・Gemini 実 API 出力品質・LM Studio モデル切替反映・タイムアウト表示一致の4項目が実機目視で pass。Claude 実 API 出力品質と max_tokens/429 実 API 検証は未実施のまま維持
result: pass
source: automated
coverage_id: D4
coverage_source: 03-03-SUMMARY.md

### 13. UAT サマリの内訳が対象確定表と一致
expected: 03-UAT-RESULTS.md にサマリ節が追加され、判定内訳（pass13/fail0/未実施2/対象外1=計16）が対象確定表の行数と一致することを検算済み
result: pass
source: automated
coverage_id: D5
coverage_source: 03-03-SUMMARY.md

### 14. APP_VERSION が v1.9.0
expected: pagefolio/constants.py の APP_VERSION が v1.9.0 である（D-16）
result: pass
source: automated
coverage_id: D1
coverage_source: 03-04-SUMMARY.md

### 15. README.md のバージョンバッジが APP_VERSION と一致
expected: README.md のバージョンバッジが APP_VERSION と一致する（v1.9.0 バッジ1件・v1.8.1 バッジ0件）
result: pass
source: automated
coverage_id: D2
coverage_source: 03-04-SUMMARY.md

### 16. 開発履歴.md の最終更新ブロックが v1.9.0
expected: 開発履歴.md の最終更新ブロック引用が v1.9.0 のマイルストーンエントリになっており、旧 v1.8.1 エントリは履歴行として残っている
result: pass
source: automated
coverage_id: D3
coverage_source: 03-04-SUMMARY.md

### 17. 開発履歴.md のバージョン索引表に v1.9.0 行がある
expected: 開発履歴.md のバージョン索引表 PageFolio セクション先頭に v1.9.0 の行がある
result: pass
source: automated
coverage_id: D4
coverage_source: 03-04-SUMMARY.md

### 18. v1.9.0 エントリが Phase 1/2/3 の実際の成果を記述
expected: 開発履歴.md の v1.9.0 エントリが Phase 1/2/3 の実際の成果（catalog / OpenAI / リリースゲート・QA）を記述している
result: pass
source: automated
coverage_id: D5
coverage_source: 03-04-SUMMARY.md

### 19. バンプ後も ruff / フルテストスイートが失敗0件で完走
expected: バンプ後も ruff / フルテストスイートが失敗0件で完走する（1398 passed, 0 failed・2回実行）
result: pass
source: automated
coverage_id: D6
coverage_source: 03-04-SUMMARY.md

## Summary

total: 19
passed: 19
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
