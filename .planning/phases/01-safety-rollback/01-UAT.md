---
status: complete
phase: 01-safety-rollback
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md, 01-05-SUMMARY.md, 01-06-SUMMARY.md, 01-07-SUMMARY.md]
started: 2026-08-10T19:32:14Z
updated: 2026-08-10T19:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. コールドスタート・スモークテスト
expected: PageFolio を完全終了した状態から新規起動 → エラーなくメインウィンドウ表示 → PDF を開いてプレビュー/サムネイル表示 → 何か1操作して Undo が効く
result: pass

### 2. フルスイート不安定化の受け入れ判断（01-07 D6）
expected: |
  Phase 1 の回帰ゲートのうち、`ruff check .` / `ruff format --check .` は green、
  分割実行（`pytest -q --ignore=tests/test_ocr_pipeline.py` + `pytest -q tests/test_ocr_pipeline.py`）では 1184 件すべて green。
  ただし単一プロセスのフルスイート `pytest -q` は、01-07 が追加したテストコードが引き金となり
  `tests/test_ocr_pipeline.py::TestPipelineHardening::test_cancel_finite_time_no_deadlock` の実行中に
  Windows fatal exception 0x80000003 でプロセスが落ちることがある（6回中4回）。
  製品コードは A/B 検証で無実と確定済み（製品コード HEAD + 基準テスト → 4/4 green）で、
  引き取り先は Phase 3（V190-QA-01 テスト安定化）。
  → この状態を Phase 1 の合格条件として受け入れてよいか（当面の運用は分割実行）を判断してください。
result: pass

### 3. 「名前を付けて保存」が暗号化 PDF の暗号化を無条件で維持する
expected: 「名前を付けて保存」が暗号化 PDF の暗号化を無条件で維持する
result: pass
source: automated
coverage_id: 01-01/D1

### 4. 上書き保存（インクリメンタル失敗時のフォールバック）が暗号化を維持する
expected: 上書き保存（インクリメンタル失敗時のフォールバック）が暗号化を維持する
result: pass
source: automated
coverage_id: 01-01/D2

### 5. 縮小最適化して保存が上書き・別パスの両分岐で暗号化を維持する
expected: 縮小最適化して保存が上書き・別パスの両分岐で暗号化を維持する
result: pass
source: automated
coverage_id: 01-01/D3

### 6. パスワード付与/解除の明示指定が既定化 setdefault に上書きされない
expected: パスワード付与/解除の明示指定が既定化 setdefault に上書きされない
result: pass
source: automated
coverage_id: 01-01/D4

### 7. pdf_has_password が保存 kwargs から論理導出され、解除後の再暗号化・保存失敗時の状態不変を保証する
expected: pdf_has_password が保存 kwargs から論理導出され、解除後の再暗号化・保存失敗時の状態不変を保証する
result: pass
source: automated
coverage_id: 01-01/D5

### 8. build_provider は ocr_provider='off' のとき OCRDisabledError を送出し、空文字は後方互換で LMStudioProvider を返す
expected: build_provider は ocr_provider='off' のとき OCRDisabledError を送出し、空文字は後方互換で LMStudioProvider を返す
result: pass
source: automated
coverage_id: 01-02/D1

### 9. OCR OFF のときツールメニュー「バッチOCR」項目が disabled かつ OFF 併記ラベルになる
expected: OCR OFF のときツールメニュー「バッチOCR」項目が disabled かつ OFF 併記ラベルになり、通常プロバイダ選択時は normal・通常ラベルへ戻る
result: pass
source: automated
coverage_id: 01-02/D2

### 10. 通常 OCR（_start_ocr）は off のとき OCRDialog を生成せず OCR 無効メッセージを表示して戻る
expected: 通常 OCR（_start_ocr）は off のとき OCRDialog を生成せず OCR 無効メッセージを表示して戻る
result: pass
source: automated
coverage_id: 01-02/D3

### 11. バッチ OCR（_on_start_batch）は off のとき実行中 UI へ遷移せずバッチを開始しない
expected: バッチ OCR（_on_start_batch）は off のとき実行中 UI へ遷移せず（_running が False のまま）バッチを開始しない（実行開始時の二重ガード）
result: pass
source: automated
coverage_id: 01-02/D4

### 12. OCR ダイアログを開いたまま off へ切替えても provider 再生成経路が LMStudioProvider を生成しない
expected: OCR ダイアログを開いたまま LLM 設定で off へ切替えても、provider 再生成経路（_apply_llm_settings / _on_run）は LMStudioProvider を生成せず、現在の provider を保持したまま OCR 無効メッセージを表示して中断する
result: pass
source: automated
coverage_id: 01-02/D5

### 13. LLM 設定の Apply 直後に OCR ボタン群とバッチOCR メニュー項目の活性状態が再評価される
expected: LLM 設定の Apply 直後に OCR ボタン群とバッチOCR メニュー項目の活性状態が再評価される（OCRDialog LLM Settings Callback Consistency の同型是正）
result: pass
source: automated
coverage_id: 01-02/D6

### 14. テンプレート切替では外部プロンプトファイルへ一切書き込まれない
expected: テンプレート切替では外部プロンプトファイル（ocr_custom_prompt.md/ocr_summary_prompt.md）へ一切書き込まれない（複数回切替・Cancel・開く→Cancelの反復いずれも不変）
result: pass
source: automated
coverage_id: 01-03/D1

### 15. Apply が書き込む内容は入力欄の現在値である（Apply が最後の書き手）
expected: Apply が書き込む内容は入力欄の現在値であり、アクティブテンプレートの保存済み値でも外部エディタでの直近編集内容でもない
result: pass
source: automated
coverage_id: 01-03/D2

### 16. 外部プロンプトファイルが存在しない場合、Apply しても新規作成しない
expected: 外部プロンプトファイルが存在しない場合、Apply しても新規作成しない（オプトイン仕様の維持）
result: pass
source: automated
coverage_id: 01-03/D3

### 17. 編集済みテンプレートから別テンプレートへ切り替えると必ず未保存確認が出る
expected: アクティブテンプレート選択済みの状態で入力欄を編集して別テンプレートへ切り替えると、外部ファイルの有無にかかわらず未保存確認ダイアログが表示される
result: pass
source: automated
coverage_id: 01-03/D4

### 18. 未保存確認で「いいえ」を選ぶと選択と入力欄が元へ戻る
expected: 未保存確認で「いいえ」を選ぶと、選択が元のアクティブテンプレートへ戻り入力欄の内容も保持される（未選択時の既存挙動も回帰なし）
result: pass
source: automated
coverage_id: 01-03/D5

### 19. 複数ファイル挿入が途中失敗しても既存ページ・Undoスタックが操作前と一致する
expected: 複数ファイル挿入が途中のファイルで失敗しても既存ページ・Undoスタックが操作前と一致し、挿入元Documentは必ずcloseされる（1ファイル/2ファイル目失敗・空リストの境界を含む）
result: pass
source: automated
coverage_id: 01-04/D1

### 20. 巻き戻し自体が失敗した場合、警告が1回表示され実挿入数を反映した Undo state が残る
expected: 巻き戻し（delete_page）自体が失敗した場合、警告ダイアログが1回表示され、実際の挿入数を反映したUndo stateが残り、そのstateで後からundoできる
result: pass
source: automated
coverage_id: 01-04/D2

### 21. ページ複製の失敗時は不変、成功時は Undo 記録が実処理成功後にのみ確定する
expected: ページ複製が失敗した場合は既存ページ・Undoスタックが不変、成功した場合はUndo記録が実処理成功後にのみ確定する
result: pass
source: automated
coverage_id: 01-04/D3

### 22. Undo/Redo の復元失敗時に state がスタックへ戻りブロッキング通知される
expected: Undo/Redoの復元失敗時にpopしたstateがスタックへ戻りブロッキング通知される。Blobは二重解放されず、失敗後の再試行で同じstateが正しく再消費される。空スタックはno-op
result: pass
source: automated
coverage_id: 01-04/D4

### 23. duplicate op の4手往復でページ数・digest列が操作前と一致する
expected: duplicate op の do→undo→redo→undo（4手往復）でページ数・digest列が操作前と一致する
result: pass
source: automated
coverage_id: 01-05/D1

### 24. merge op の4手往復でページ数・digest列が操作前と一致する
expected: merge op の do→undo→redo→undo（4手往復）でページ数・digest列が操作前と一致する
result: pass
source: automated
coverage_id: 01-05/D2

### 25. merge_resize op の4手往復でページ数・digest列が操作前と一致する
expected: merge_resize op の do→undo→redo→undo（4手往復）でページ数・digest列が操作前と一致する
result: pass
source: automated
coverage_id: 01-05/D3

### 26. 1ページのみの Document に対する duplicate でも4手往復が一致する
expected: 1ページのみの Document に対する duplicate でも4手往復でページ構成が一致する（boundary probe）
result: pass
source: automated
coverage_id: 01-05/D4

### 27. 先頭・末尾に隣接する位置へのマージでも4手往復後のページ順序が一致する
expected: 先頭・末尾に隣接する位置へのマージでも4手往復後のページ順序が操作前と一致する（adjacency probe）
result: pass
source: automated
coverage_id: 01-05/D5

### 28. merge_resize の4手往復後、元ページの digest列が同順で一致する
expected: merge_resize の4手往復後、元ページの digest列が操作前と同順で一致する（ordering probe）
result: pass
source: automated
coverage_id: 01-05/D6

### 29. merge_resize の4手往復後、元ページの MediaBox 幅・高さが一致する
expected: merge_resize の4手往復後、元ページの MediaBox 幅・高さが操作前と一致する（precision probe）
result: pass
source: automated
coverage_id: 01-05/D7

### 30. マージ対象ファイルが1件だけの最小入力でも4手往復が成立する
expected: マージ対象ファイルが1件だけの最小入力でも4手往復が成立する（empty probe）
result: pass
source: automated
coverage_id: 01-05/D8

### 31. D-12 棚卸し（Undo 記録が実処理より先の op 一覧）が SUMMARY に記録されている
expected: D-12 棚卸し（Undo 記録が実処理より先の op 一覧）が SUMMARY に記録され、水平展開は次マイルストーン候補として明示されている
result: pass
source: automated
coverage_id: 01-05/D9

### 32. delete の undo 部分失敗→再試行成功後の redo で全対象ページが削除される
expected: delete の undo が部分失敗→再試行成功した後に redo すると、当初 delete 対象だった全ページが削除される（Evidence 3 の再現）
result: pass
source: automated
coverage_id: 01-06/D1

### 33. delete_redo の redo 部分失敗→再試行成功後も undo/redo が正しく往復する
expected: delete_redo の redo が部分失敗→再試行成功した後に undo/redo を続けても全ページが正しく往復する
result: pass
source: automated
coverage_id: 01-06/D2

### 34. page_edit の undo 部分失敗→再試行成功後、redo/undo が正しく往復する
expected: page_edit の undo が部分失敗→再試行成功した後、redo で両ページとも編集後の内容に戻り undo で編集前に戻る
result: pass
source: automated
coverage_id: 01-06/D3

### 35. insert_undo の redo 部分失敗→再試行成功後、挿入分が完全に往復する
expected: insert_undo の redo（再挿入）が部分失敗→再試行成功後、undo/redo で挿入分が完全に往復する
result: pass
source: automated
coverage_id: 01-06/D4

### 36. insert_redo の undo 部分失敗→再試行成功後、挿入分が完全に往復する
expected: insert_redo の undo（削除）が部分失敗→再試行成功後、undo/redo で挿入分が完全に往復する
result: pass
source: automated
coverage_id: 01-06/D5

### 37. merge_resize の undo 部分失敗→再試行成功後、結合ページ内容が破損しない
expected: merge_resize の undo が部分失敗→再試行成功後、redo で結合ページ内容が破損せず、undo で結合前の内容に完全に戻る（Evidence 4 の再現）
result: pass
source: automated
coverage_id: 01-06/D6

### 38. merge_resize_undo の redo 部分失敗→再試行成功後、ページ構成・内容が完全に往復する
expected: merge_resize_undo の redo が部分失敗→再試行成功後、undo/redo でページ構成・内容が完全に往復する
result: pass
source: automated
coverage_id: 01-06/D7

### 39. merge_undo が本欠陥の非該当であることが往復テストで固定されている
expected: merge_undo は逆デルタが old_count スカラーのみのため本欠陥の非該当であることが、同型の往復テストで明示的に固定されている
result: pass
source: automated
coverage_id: 01-06/D8

### 40. 再試行されないまま evict/clear された state の Blob も全解放される
expected: 部分失敗を経由した state が再試行されないまま evict/clear された場合も、蓄積された逆デルタ用 Blob を含めて全解放され一時ファイルが残らない
result: pass
source: automated
coverage_id: 01-06/D9

### 41. 5手往復のどの段階でも同一 Blob の release() が2回以上呼ばれない
expected: 5手往復のどの段階でも、同一 Blob に対する release() が2回以上呼ばれない
result: pass
source: automated
coverage_id: 01-06/D10

### 42. 復元失敗直後の即時二重適用防止とブロッキング通知が退行していない
expected: cb5344e が閉じた『復元失敗直後の即時二重適用』防止と D-13 のブロッキング通知が退行していない（既存 TestUndoRedoRestoreFailure 3件・WR-01 ピンが green のまま）
result: pass
source: automated
coverage_id: 01-06/D11

### 43. ruff check / ruff format --check / pytest -q の3ゲートが green（01-06 時点）
expected: ruff check / ruff format --check / フルテストスイート(pytest -q) の3ゲートがすべて green
result: pass
source: automated
coverage_id: 01-06/D12

### 44. page_edit の中間失敗でもロールバック成功時は隣接ページの内容が失われない
expected: page_edit の undo/redo が、delete_page成功後のinsert_pdf失敗（旧設計）に相当する中間失敗を経ても、ロールバック成功時は通常の部分失敗として扱われ、doc/隣接ページの内容が失われない（Evidence B再現手順）
result: pass
source: automated
coverage_id: 01-07/D1

### 45. 復旧不能ケースで content_at_risk の強い警告が1回だけ表示され、再試行で完全復元される
expected: page_edit の中間mutationロールバックも失敗する復旧不能ケースで、専用の強い警告（content_at_risk）が1回だけ表示され、障害解消後の再試行・redo・undoの往復で内容が完全に再構成される
result: pass
source: automated
coverage_id: 01-07/D2

### 46. 一時 fitz.Document 7箇所すべてが finally で保護され AST ガードで固定されている
expected: _restore_state周辺の一時fitz.Document（tmp）7箇所すべてがfinallyで保護され、AST走査ガードで恒久的に固定されている（WR-04）
result: pass
source: automated
coverage_id: 01-07/D3

### 47. insert（base op）の削除ループが部分適用保護に乗り既存ページを過剰削除しない
expected: insert（base op）の削除ループが部分適用保護に乗り、部分失敗→再試行で挿入対象外の既存ページを過剰削除しない（WR-05）
result: pass
source: automated
coverage_id: 01-07/D4

### 48. 復旧不能経路・insert 部分失敗経路でも蓄積 Blob が一度だけ解放される
expected: 復旧不能経路・insert部分失敗経路のいずれでも蓄積Blobがevict/clear経路で確実に一度だけ解放される（二重解放ゼロ・D-14）
result: pass
source: automated
coverage_id: 01-07/D5

## Summary

total: 48
passed: 48
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
