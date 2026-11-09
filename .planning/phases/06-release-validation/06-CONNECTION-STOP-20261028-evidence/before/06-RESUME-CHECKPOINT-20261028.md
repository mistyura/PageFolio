# 06-04-02 接続実証の開始直前チェックポイント

## CHECKPOINT REACHED

**Type:** human-verify  
**Gate:** blocking-human  
**Plan:** 06-04（現行世代3）  
**Progress:** 1/2 tasks complete（buildは同一性再利用。接続は未完了）

## 対象と状態

- v1.10.1、EXE SHA256 `9b3ebbce390c3b9f1752a97820a5ef81a0c39b7e148b93717b86bb47f9f5f73b`、tree SHA256 `cce2fd0a99a6f368ab271f9f0b6a212c3984a6387c7684800074434d5152ccf4`。
- build入力manifest SHA256 `dfc38fd64e1511625551daf4a50c9b411fd23cf986ed9080081a6eb2f13dc11f`、65/65一致、環境一致。追加build不要。
- 実初回run `3efb60fa80064c588ed1805b995d7394`、再build run `963ad4cb42694888bf98be93f05d1923`。配布元は起動しない。
- 根拠は`06-RESUME-CHECK-20261028.json`。親のPhase04独立再検証はpassed/current digest一致。最新品質2071件/Ruff137件を同一性再利用。
- 自動準備は`06-04g3-t2-result.json`を再利用。接続2条件は未実施。全110行not-run、06-05は既存部分実施、06-06 not-ready。

## 親担当の開始前確認と起動

利用者へ以下の操作を先に案内し、操作できる時だけ親が起動する。CLI・copy・server・PID回収は親が行う。GUIはまだ起動していない。

開始直前に`release_uat_support.probe_owner()`が空であること、build lock不存在、所有PID残存なし、EXE/hash/現行Phase04鮮度を再照合する。ownerがあれば何も送信しない。開始コマンド（repo root、interactive stdin保持）:

```powershell
.venv/Scripts/python.exe .planning/phases/06-release-validation/06-04-drivers/conn_session.py --t2 C:/Users/shdwf/AppData/Local/Temp/pf06_t2_g3_unreadable_8433fc4ee5324234931fb80ac0f310d1 --scenario ocr-single
```

親はPTYのstdinを保持し、利用者がチャットへ返す観察原文を該当input待ちへ渡せる。端末へ切り替えると観測対象のforegroundが変わるため、画面観測時と回答時を混同しない。GUI起動にnative実行の承認が必要なら実行toolの承認手続を使う。

run IDはdriverのprepare時に新規採番される。開始出力のPDFパスと`manifest.json`でID/copy/hash/環境を保存する。既存runを新規結果として使わない。

## 最初の操作: ocr-single

1. 起動したPageFolioの隔離copyでdriver出力のPDFを開く（パスはクリップボードへ入る）。唯一のページ1だけを選ぶ。LLM設定やプロバイダを変更しない。
2. 右ペイン「🔠 現在ページをテキスト抽出」からOCRダイアログを開き、「▶ 読み取り実行」を押す。サマリは実行しない。埋め込みテキスト無視はONのままでよい。
3. driverが1POST受信→peer起動→同じrequestの待機解放を行う。PageFolioへ戻ること、結果欄に「PageFolio UAT 合成OCR結果」が出ることを観察し、`ocr-single: 見えた内容／前面への復帰／異常の有無`で回答する。

「OCR TEST 0123456789」が結果として出た場合は合成接続成功にしない。接続不能・複数POST・画面不一致・通知異常などは初回停止する。

## 回答確認後の別run: w05b-modal

ocr-singleの生記録と原文回答が揃い、1受信→1解放→1完了、回収・原本不変を確認した後だけ、親が上のscenarioを`w05b-modal`に変えて起動する。2本を同時起動しない。

1. 同じ1pageの読み取り実行後、待機中のOCRダイアログで「✕ 閉じる」を押す。「OCR 実行中です…閉じますか?」が出たらボタンを押さず、表示を回答する。
2. driverのpeer後、同じ確認ダイアログへ戻ったかを回答する。別通知や親window復帰で代用しない。
3. 「いいえ」を押し、OCRダイアログ・処理・入力の維持を回答する。解放後、同じ処理で「PageFolio UAT 合成OCR結果」が表示されることを回答する。

各inputへの回答を親が逐語保存する。観測/回答不足を推測で補わない。

## 期限・回収・証拠反映

既存定数は要求受信待ち1200秒、hold上限420秒、provider timeout600秒、completed待ち60秒。今回延長しない。hold中は7分以内に操作する。期限/異常で不成立なら原本保持して停止し、同条件再試行/skipしない。

finallyで`stop(timeout=12)`、通常終了優先・失敗時診断・PID/生成時刻付き回収、server停止、owner再照合を行う。自動で閉じるため利用者の手動終了で試行を無効化しない。証拠は`t2/runs/release-uat-<id>/evidence/session-<scenario>.json`、同dirの`fake-ocr-events.jsonl`、manifest、外部観測。

親は`selftest=false`、routing-onlyではないこと、原文、1page/並列1/summaryなし、EXE/treehash、回収、source不変を精査する。W05bは同じnative modal HWND/前景、No後OCR維持、同request完了を外部観測で確認する。

**`assemble_protection.py` mainはgeneration=2固定なので実行しない。** 既存`load_session`/`build_connection` helperを読取で使い、有効と判断した接続行だけgeneration=3の現行`connection`へ追記する。元`previous_generations`/失敗履歴/未実施を保持。原本path/回答/hashを変更しない。run参照はnested generationを含めて機械同期する（`06-RESUME-CHECK-20261028.cjs --sync-refs`で対応）。

両条件の実測/回答反映後に`audit --preparation-only`を実行する。現状は接続不足でnonzeroが正しく、準備完了へしない。接続実証をW04/W05b本受入へ転記せず、06-05/Phase完了/出荷可の判断を先行しない。

## 申し送り

変更はBUILD/PROTECTION再開追補、準備カード品質参照/旧16 run参照、UAT現行版表記、再開文書、局所証拠/script。製品/tests/版/AGENTS/pyproject/index・失敗原本を保全、commitなし。旧06-01〜04 SUMMARYと06-05既存6commitは履歴として保持。
