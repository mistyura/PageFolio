---
phase: 06-release-validation
document: uat-cards
plan: 06-05
status: cards-written-all-not-run
created: 2026-10-24
---

# Phase 6 実機受入カード(06-05)

本書は人手受入の**操作カードと回答欄の正本**。結果の機械可読な正本は [06-MANUAL-EVIDENCE.json](06-MANUAL-EVIDENCE.json)。
準備完了・build成功・人手pass・Phase完了は別の状態であり、本書のカード記載は合格・出荷承認を意味しない。全subrowは not-run から始まる。

## 受入対象と進め方

| 項目 | 内容 |
|---|---|
| 主対象(final-release-candidate) | 実配布EXE v1.10.0 / EXE sha256 `b3d4a07e94ccb9a8a82671f5191902ac86b02f8abbeaf8f16e9a9878603a8c17` |
| tree sha256 | `3436ac39cfd7a426e8a5982fa2f1e9f7bbc87ebd8176721b32d88cec1ff8489a` |
| 隔離元(直接起動しない) | `C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0` |
| 相手側tracer(technical-tracer-real-exe) | 06-01の実PyInstaller成果物 v1.9.1 / EXE sha256 `c082f6f4c35af75f07e574f2ef30f41c25e41965f7f9f17a8b65ac71e9183ba7` / run `2db21a6b3e8b4aed80d92adc3a521668`。公式旧版でも最終EXE受入済みでもない |
| 移管正本 | [06-UAT-CARRYOVER.md](06-UAT-CARRYOVER.md) / [04-WINDOWS-UAT.md](../04-startup-control/04-WINDOWS-UAT.md) |
| Phase5再利用 | [05-UAT.md](../05-config-notification/05-UAT.md) のH01〜H14と意味評価2件は参照のみ(再実施しない) |

- 進め方: 少数ずつ **Python→実EXE** の順。1回に2〜3操作まで。ケースIDと短い観察結果を受け取ってから次へ進む。
- 回答はキーボードで短く入力する(コンソールへの右クリック貼り付け/Ctrl+Vは使わない。画面やパスと完全一致する入力は一度拒否して取り直し、生入力はすべて記録する)。
- LLM設定・プロバイダは、このカードが明示した場合を除き開かない・変更しない。
- 実行担当が一時PDF・設定・fake OCR・所有PIDの準備と回収を行い、利用者はクリック・入力・UAC・目視だけを行う。配布元は直接起動せず、完全copyを起動する。
- passになるのは、利用者の原文回答(ケースID付き)・必須観測・環境/時刻/PID/session/権限/入口/commit+dirtyhash・binary hashが揃った subrow だけ。空欄補完は行わない。
- 画面記録は通知/DPI/異常を中心にし、入力先・foreground・時間上限は画面記録だけで実証とみなさずログを併用する。
- Python harnessが自動設定するstate/選択/カーソル/Undoを未改変EXEへ注入できるとは仮定しない。EXE側は人が同じ状態を作る操作と外部から観測できる結果を記し、内部Undo identity等はPython証拠欄に分ける。

## 組(G)の対応

| 組 | ケース | 担当task |
|---|---|---|
| G1 | W01, W02 | 06-05-02 |
| G2 | W03, W04 | 06-05-02 |
| G3 | W05a, W05b, W05c | 06-05-02 |
| G4 | W12a, W12b, W12c | 06-05-02 |
| G5 | X01, X02, X03 | 06-05-02 |
| G6 | X04, X05, X06 | 06-05-02 |
| G7 | W06, W07a | 06-06-01 |
| G8 | W07b, WR-01 | 06-06-01 |
| G9 | W08a, W08b | 06-06-01 |
| G10 | W08c, W08d | 06-06-01 |
| G11 | W09a, W09b | 06-06-01 |
| G12 | W09c, W09d | 06-06-01 |
| G13 | W10a, W10b | 06-06-01 |
| G14 | W11 | 06-06-01 |

## 引き継ぎ観測(06-04より)

- W05b: 実際のダブルクリック起動でのforeground(06-04は合成peerで前景成立。本受入でAPI戻りと別記)
- EXEがclose要求(WM_CLOSE)で終了せず所有handleで強制終了された観測(ocr-single/w05b-modal/X04)。合否ではなく観測として記録
- ocr-singleの補足回答はチャット中継であり、本受入では利用者本人の端末入力を記録する

## 共通の失敗時回収

想定外のダイアログ・クラッシュ・hash不一致・所有外processの接触が出たら、直ちに操作を止め(passにしない)、`stop` で所有PIDだけを回収し、最初の出力と `evidence/` を保存する。配布copy treeと原本(設定/2prompt/plugins)を再照合し、行を fail/blocked にして利用者の原文を残す。DEP-05回帰・owner_missing・通知前景不一致・Tcl警告・未分類edgeの同種再発は後続を止めて gsd-debug へ戻る。期限延長・skip・除外・負荷縮小で通さない。回答済みpassは対応hashが同じ場合だけ再利用する。

## ケースカード

## W01 最小化からの復元(通常/最大化)

- 組: G1 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W01 / 06-UAT-CARRYOVER W01 / 06-VALIDATION W01

### W01/normal@script

**W01 / 通常の大きさ / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case normal | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case normal` で隔離ownerを準備する(通常の大きさで、最小化済みの状態に整えられる)。
  2. 実行担当: `peer --entry script` で二次起動する。
  3. 利用者: 画面のPageFolio(隔離受入)が通常の大きさの状態で前面に戻ったか、ヘッダーのステータス文字が保たれているか、画面が1つだけかを目で見て答える。
- **期待**: 通常の大きさの元の状態・位置・大きさで復帰し、ステータス表示が保たれ、追加の画面が増えない。
- **必須観測**:
  - `state_before`: 最小化前の表示状態(normal=通常/zoomed=最大化)
  - `state_after`: 復帰後の表示状態
  - `geometry_match`: 最小化前後の位置・大きさが一致(外部観測の矩形と目視)
  - `status_text_kept`: ヘッダーのステータス表示が保たれている
  - `single_screen`: PageFolioの画面が1つだけ(追加の編集画面なし)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W01 / 06-UAT-CARRYOVER W01 / 06-VALIDATION W01

### W01/normal@module

**W01 / 通常の大きさ / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case normal | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case normal` で隔離ownerを準備する(通常の大きさで、最小化済みの状態に整えられる)。
  2. 実行担当: `peer --entry module` で二次起動する。
  3. 利用者: 画面のPageFolio(隔離受入)が通常の大きさの状態で前面に戻ったか、ヘッダーのステータス文字が保たれているか、画面が1つだけかを目で見て答える。
- **期待**: 通常の大きさの元の状態・位置・大きさで復帰し、ステータス表示が保たれ、追加の画面が増えない。
- **必須観測**:
  - `state_before`: 最小化前の表示状態(normal=通常/zoomed=最大化)
  - `state_after`: 復帰後の表示状態
  - `geometry_match`: 最小化前後の位置・大きさが一致(外部観測の矩形と目視)
  - `status_text_kept`: ヘッダーのステータス表示が保たれている
  - `single_screen`: PageFolioの画面が1つだけ(追加の編集画面なし)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W01 / 06-UAT-CARRYOVER W01 / 06-VALIDATION W01

### W01/normal@production-exe

**W01 / 通常の大きさ / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W01).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start` で起動し、PID・hash・foregroundを記録する。
  2. 利用者: 表示されたPageFolioを通常の大きさにして、ヘッダーのステータス文字を目で覚える(通常の場合は位置・大きさも覚える)。
  3. 利用者: 最小化する(タスクバーに残る)。
  4. 実行担当: 同じ配布copyから `peer` で二次起動し、復帰前後のwindow状態・矩形・foregroundを外部観測する。
  5. 利用者: 復帰後の状態が通常の大きさの元状態か、ステータス文字が保たれているか、画面が1つだけかを答える。
- **期待**: 実EXEが通常の大きさの元の状態で復帰し、ステータス表示が保たれ、追加の画面が増えない。復帰後の実foregroundはAPI戻りと別に記録する。
- **必須観測**:
  - `state_before`: 最小化前の表示状態(normal=通常/zoomed=最大化)
  - `state_after`: 復帰後の表示状態
  - `geometry_match`: 最小化前後の位置・大きさが一致(外部観測の矩形と目視)
  - `status_text_kept`: ヘッダーのステータス表示が保たれている
  - `single_screen`: PageFolioの画面が1つだけ(追加の編集画面なし)
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W01 / 06-UAT-CARRYOVER W01 / 06-VALIDATION W01

### W01/zoomed@script

**W01 / 最大化 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case zoomed | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case zoomed` で隔離ownerを準備する(最大化で、最小化済みの状態に整えられる)。
  2. 実行担当: `peer --entry script` で二次起動する。
  3. 利用者: 画面のPageFolio(隔離受入)が最大化の状態で前面に戻ったか、ヘッダーのステータス文字が保たれているか、画面が1つだけかを目で見て答える。
- **期待**: 最大化の元の状態・位置・大きさで復帰し、ステータス表示が保たれ、追加の画面が増えない。
- **必須観測**:
  - `state_before`: 最小化前の表示状態(normal=通常/zoomed=最大化)
  - `state_after`: 復帰後の表示状態
  - `geometry_match`: 最小化前後の位置・大きさが一致(外部観測の矩形と目視)
  - `status_text_kept`: ヘッダーのステータス表示が保たれている
  - `single_screen`: PageFolioの画面が1つだけ(追加の編集画面なし)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W01 / 06-UAT-CARRYOVER W01 / 06-VALIDATION W01

### W01/zoomed@module

**W01 / 最大化 / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case zoomed | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case zoomed` で隔離ownerを準備する(最大化で、最小化済みの状態に整えられる)。
  2. 実行担当: `peer --entry module` で二次起動する。
  3. 利用者: 画面のPageFolio(隔離受入)が最大化の状態で前面に戻ったか、ヘッダーのステータス文字が保たれているか、画面が1つだけかを目で見て答える。
- **期待**: 最大化の元の状態・位置・大きさで復帰し、ステータス表示が保たれ、追加の画面が増えない。
- **必須観測**:
  - `state_before`: 最小化前の表示状態(normal=通常/zoomed=最大化)
  - `state_after`: 復帰後の表示状態
  - `geometry_match`: 最小化前後の位置・大きさが一致(外部観測の矩形と目視)
  - `status_text_kept`: ヘッダーのステータス表示が保たれている
  - `single_screen`: PageFolioの画面が1つだけ(追加の編集画面なし)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W01 / 06-UAT-CARRYOVER W01 / 06-VALIDATION W01

### W01/zoomed@production-exe

**W01 / 最大化 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W01).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start` で起動し、PID・hash・foregroundを記録する。
  2. 利用者: 表示されたPageFolioを最大化にして、ヘッダーのステータス文字を目で覚える(通常の場合は位置・大きさも覚える)。
  3. 利用者: 最小化する(タスクバーに残る)。
  4. 実行担当: 同じ配布copyから `peer` で二次起動し、復帰前後のwindow状態・矩形・foregroundを外部観測する。
  5. 利用者: 復帰後の状態が最大化の元状態か、ステータス文字が保たれているか、画面が1つだけかを答える。
- **期待**: 実EXEが最大化の元の状態で復帰し、ステータス表示が保たれ、追加の画面が増えない。復帰後の実foregroundはAPI戻りと別に記録する。
- **必須観測**:
  - `state_before`: 最小化前の表示状態(normal=通常/zoomed=最大化)
  - `state_after`: 復帰後の表示状態
  - `geometry_match`: 最小化前後の位置・大きさが一致(外部観測の矩形と目視)
  - `status_text_kept`: ヘッダーのステータス表示が保たれている
  - `single_screen`: PageFolioの画面が1つだけ(追加の編集画面なし)
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W01 / 06-UAT-CARRYOVER W01 / 06-VALIDATION W01

## W02 二次起動後の実入力・選択・カーソル・入力先維持

- 組: G1 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/settings@script

**W02 / 設定ダイアログの入力欄 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case settings | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case settings` で隔離ownerを準備する(設定ダイアログの入力欄: unsaved input・カーソル5・選択1〜7が準備済み)。
  2. 実行担当: `peer --entry script` で二次起動し、API戻り・OS error・foregroundを記録する。
  3. 利用者: キーボードで1文字入力し、入力が設定ダイアログの入力欄に入るか、選択・カーソルが保たれているかを答える。
- **期待**: 設定ダイアログの入力欄の入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。拒否されたfocus移譲は成功と数えない。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記(拒否を実キーボードfocus復帰成功と扱わない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/settings@module

**W02 / 設定ダイアログの入力欄 / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case settings | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case settings` で隔離ownerを準備する(設定ダイアログの入力欄: unsaved input・カーソル5・選択1〜7が準備済み)。
  2. 実行担当: `peer --entry module` で二次起動し、API戻り・OS error・foregroundを記録する。
  3. 利用者: キーボードで1文字入力し、入力が設定ダイアログの入力欄に入るか、選択・カーソルが保たれているかを答える。
- **期待**: 設定ダイアログの入力欄の入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。拒否されたfocus移譲は成功と数えない。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記(拒否を実キーボードfocus復帰成功と扱わない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/settings@production-exe

**W02 / 設定ダイアログの入力欄 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W02).run
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start` で起動する(EXEへ状態は注入できない。状態は利用者が作る)。
  2. 利用者: 「⚙ 設定」を開き、入力欄の1つに文字を入れ、一部を選択してカーソルを置く(LLM設定は開かない)。
  3. 実行担当: 同じ配布copyから `peer` で二次起動し、API戻り・OS error・foregroundを外部観測する。
  4. 利用者: キーボードで1文字入力し、設定ダイアログの入力欄に入るか、選択・カーソルが保たれているかを答える。
- **期待**: 実EXEで設定ダイアログの入力欄の入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/thumb@script

**W02 / 左ペインのサムネイル欄 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case thumb | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case thumb` で隔離ownerを準備する(左ペインのサムネイル欄: 対象ページが選択済み)。
  2. 実行担当: `peer --entry script` で二次起動し、API戻り・OS error・foregroundを記録する。
  3. 利用者: キーボードで1文字入力し、入力が左ペインのサムネイル欄に入るか、選択・カーソルが保たれているかを答える。
- **期待**: 左ペインのサムネイル欄の入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。拒否されたfocus移譲は成功と数えない。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記(拒否を実キーボードfocus復帰成功と扱わない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/thumb@module

**W02 / 左ペインのサムネイル欄 / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case thumb | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case thumb` で隔離ownerを準備する(左ペインのサムネイル欄: 対象ページが選択済み)。
  2. 実行担当: `peer --entry module` で二次起動し、API戻り・OS error・foregroundを記録する。
  3. 利用者: キーボードで1文字入力し、入力が左ペインのサムネイル欄に入るか、選択・カーソルが保たれているかを答える。
- **期待**: 左ペインのサムネイル欄の入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。拒否されたfocus移譲は成功と数えない。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記(拒否を実キーボードfocus復帰成功と扱わない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/thumb@production-exe

**W02 / 左ペインのサムネイル欄 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W02 --pdf edit-three-page).run
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start` で起動する(EXEへ状態は注入できない。状態は利用者が作る)。
  2. 利用者: 実行担当が用意した3ページPDFを開き、左ペインのサムネイルでページを1つ選択する。
  3. 実行担当: 同じ配布copyから `peer` で二次起動し、API戻り・OS error・foregroundを外部観測する。
  4. 利用者: キーボードで1文字入力し、左ペインのサムネイル欄に入るか、選択・カーソルが保たれているかを答える。
- **期待**: 実EXEで左ペインのサムネイル欄の入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/preview@script

**W02 / 中央のプレビュー / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case preview | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case preview` で隔離ownerを準備する(中央のプレビュー: PDFを開いたプレビューが操作先)。
  2. 実行担当: `peer --entry script` で二次起動し、API戻り・OS error・foregroundを記録する。
  3. 利用者: キーボードで1文字入力し、入力が中央のプレビューに入るか、選択・カーソルが保たれているかを答える。
- **期待**: 中央のプレビューの入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。拒否されたfocus移譲は成功と数えない。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記(拒否を実キーボードfocus復帰成功と扱わない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/preview@module

**W02 / 中央のプレビュー / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case preview | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case preview` で隔離ownerを準備する(中央のプレビュー: PDFを開いたプレビューが操作先)。
  2. 実行担当: `peer --entry module` で二次起動し、API戻り・OS error・foregroundを記録する。
  3. 利用者: キーボードで1文字入力し、入力が中央のプレビューに入るか、選択・カーソルが保たれているかを答える。
- **期待**: 中央のプレビューの入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。拒否されたfocus移譲は成功と数えない。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記(拒否を実キーボードfocus復帰成功と扱わない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

### W02/preview@production-exe

**W02 / 中央のプレビュー / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W02 --pdf edit-three-page).run
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start` で起動する(EXEへ状態は注入できない。状態は利用者が作る)。
  2. 利用者: 実行担当が用意した3ページPDFを開き、中央のプレビューをクリックして操作先にする。
  3. 実行担当: 同じ配布copyから `peer` で二次起動し、API戻り・OS error・foregroundを外部観測する。
  4. 利用者: キーボードで1文字入力し、中央のプレビューに入るか、選択・カーソルが保たれているかを答える。
- **期待**: 実EXEで中央のプレビューの入力・選択・カーソルが保たれ、実キー入力が同じ入力先へ入る。
- **必須観測**:
  - `typed_text_kept`: 入力済みの文字が残っている
  - `selection_kept`: 選択範囲が保たれている
  - `cursor_kept`: カーソル位置が保たれている
  - `input_target_kept`: 実キー入力が元の入力先(widget)に入る
  - `foreground_result`: 許可APIの戻りと実foregroundを別記
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W02 / 06-UAT-CARRYOVER W02 / 06-VALIDATION W02

## W03 未保存編集とUndo→Redo→Undo→Redoの内容

- 組: G2 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W03 / 06-UAT-CARRYOVER W03 / 06-VALIDATION W03

### W03/pdf-3page@script

**W03 / 未保存3頁PDF / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case pdf | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case pdf` で一時3ページPDFに回転/複製/削除を行った隔離ownerを準備する(未保存・メモリ上のみ)。
  2. 実行担当: `peer --entry script` で二次起動する。内部のDocument/履歴/Blob identityはPython証拠欄(harness結果)に記録する。
  3. 利用者: 復帰した同じ画面でUndo→Redo→Undo→Redoを順に実行し、各段のページ数と向きを答える。
- **期待**: 復帰後も未保存編集が見え、Undo→Redo→Undo→Redoで内容が1段ずつ往復する。
- **必須観測**:
  - `edit_visible_after_restore`: 復帰後も未保存の編集(回転/複製/削除)が画面に見える
  - `undo_1`: 1回目のUndo後のページ数・向き
  - `redo_1`: 1回目のRedo後のページ数・向き
  - `undo_2`: 2回目のUndo後のページ数・向き
  - `redo_2`: 2回目のRedo後のページ数・向き
  - `original_pdf_untouched`: 原PDFは使わず合成PDFだけを編集した
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W03 / 06-UAT-CARRYOVER W03 / 06-VALIDATION W03

### W03/pdf-3page@module

**W03 / 未保存3頁PDF / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case pdf | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case pdf` で一時3ページPDFに回転/複製/削除を行った隔離ownerを準備する(未保存・メモリ上のみ)。
  2. 実行担当: `peer --entry module` で二次起動する。内部のDocument/履歴/Blob identityはPython証拠欄(harness結果)に記録する。
  3. 利用者: 復帰した同じ画面でUndo→Redo→Undo→Redoを順に実行し、各段のページ数と向きを答える。
- **期待**: 復帰後も未保存編集が見え、Undo→Redo→Undo→Redoで内容が1段ずつ往復する。
- **必須観測**:
  - `edit_visible_after_restore`: 復帰後も未保存の編集(回転/複製/削除)が画面に見える
  - `undo_1`: 1回目のUndo後のページ数・向き
  - `redo_1`: 1回目のRedo後のページ数・向き
  - `undo_2`: 2回目のUndo後のページ数・向き
  - `redo_2`: 2回目のRedo後のページ数・向き
  - `original_pdf_untouched`: 原PDFは使わず合成PDFだけを編集した
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W03 / 06-UAT-CARRYOVER W03 / 06-VALIDATION W03

### W03/pdf-3page@production-exe

**W03 / 未保存3頁PDF / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W03 --pdf edit-three-page).run
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyと合成3ページPDF(edit-three-page)を準備し `start` する。
  2. 利用者: そのPDFを開き、1ページ目を回転・2ページ目を複製・3ページ目を削除する(保存しない)。
  3. 実行担当: `peer` で二次起動し、foregroundを外部観測する。
  4. 利用者: 復帰した同じ画面でUndo→Redo→Undo→Redoを順に実行し、各段のページ数と向きを答える(内部Undo identityは見えないのでPython証拠欄にだけ残る)。
- **期待**: 実EXEで復帰後も未保存編集が見え、4手の往復表示が1段ずつ変わる。
- **必須観測**:
  - `edit_visible_after_restore`: 復帰後も未保存の編集(回転/複製/削除)が画面に見える
  - `undo_1`: 1回目のUndo後のページ数・向き
  - `redo_1`: 1回目のRedo後のページ数・向き
  - `undo_2`: 2回目のUndo後のページ数・向き
  - `redo_2`: 2回目のRedo後のページ数・向き
  - `original_pdf_untouched`: 原PDFは使わず合成PDFだけを編集した
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W03 / 06-UAT-CARRYOVER W03 / 06-VALIDATION W03

## W04 fake OCRの進捗/完了と状態維持(1page画像PDF・並列1)

- 組: G2 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W04 / 06-UAT-CARRYOVER W04 / 06-UAT-PREPARATION fake OCR

### W04/ocr-1page@script

**W04 / 1page画像PDF・並列1 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case ocr | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case ocr` でlocal fake providerが待機中の隔離ownerを準備する(同じ実OCRDialog経路)。
  2. 実行担当: `peer --entry script` で二次起動し、待機中に復帰させる。
  3. 実行担当: 同じworkerを解放する。
  4. 利用者: 進捗表示が続いたか、完了時に結果が表示されたかを答える。
- **期待**: 待機中の同じengine/worker/run generationが保たれ、解放後に完了表示へ進む。
- **必須観測**:
  - `progress_shown`: OCR待機中の進捗(処理中)表示
  - `same_page_attempt`: 同じpage・同じattemptの処理が継続(再送なし)
  - `completed_shown`: 完了時に『PageFolio UAT 合成OCR結果』が結果欄へ表示
  - `post_count_1`: 合成サーバーのPOSTが1件(server記録)
  - `summary_not_run`: サマリは実行していない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W04 / 06-UAT-CARRYOVER W04 / 06-UAT-PREPARATION fake OCR

### W04/ocr-1page@module

**W04 / 1page画像PDF・並列1 / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case ocr | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case ocr` でlocal fake providerが待機中の隔離ownerを準備する(同じ実OCRDialog経路)。
  2. 実行担当: `peer --entry module` で二次起動し、待機中に復帰させる。
  3. 実行担当: 同じworkerを解放する。
  4. 利用者: 進捗表示が続いたか、完了時に結果が表示されたかを答える。
- **期待**: 待機中の同じengine/worker/run generationが保たれ、解放後に完了表示へ進む。
- **必須観測**:
  - `progress_shown`: OCR待機中の進捗(処理中)表示
  - `same_page_attempt`: 同じpage・同じattemptの処理が継続(再送なし)
  - `completed_shown`: 完了時に『PageFolio UAT 合成OCR結果』が結果欄へ表示
  - `post_count_1`: 合成サーバーのPOSTが1件(server記録)
  - `summary_not_run`: サマリは実行していない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W04 / 06-UAT-CARRYOVER W04 / 06-UAT-PREPARATION fake OCR

### W04/ocr-1page@production-exe

**W04 / 1page画像PDF・並列1 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W04 --pdf ocr-one-page).run
  .venv/Scripts/python.exe tests/release_uat_support.py serve-ocr --run $run --mode hold  # loopbackの合成OCR。設定は隔離copyへ書かれる
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run
  (解放) $run/release.flag を作る
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copy・1page画像PDF・loopback合成OCR(待機型)を準備して `start` する。設定は合成サーバー向けに準備済み。LLM設定・プロバイダは、このカードが明示した場合を除き開かない・変更しない。
  2. 利用者: そのPDFを開き、ページ1(唯一)だけを選択し、『🔠 現在ページをテキスト抽出』→『▶ 読み取り実行』を押す(サマリは実行しない)。
  3. 実行担当: サーバーが要求を受信して待機に入ったことを確認し、`peer` で二次起動する。
  4. 実行担当: 待機を解放する(同じrequest・attemptを完了させる)。
  5. 利用者: 待機中に進捗表示が出ていたか、完了時に『PageFolio UAT 合成OCR結果』が結果欄に出たかを答える。
- **期待**: 実EXEで待機中のOCRが二次起動後も同じ処理として継続し、完了表示に至る。POSTは1件で再送なし。06-04の接続準備回答は転用しない。
- **必須観測**:
  - `progress_shown`: OCR待機中の進捗(処理中)表示
  - `same_page_attempt`: 同じpage・同じattemptの処理が継続(再送なし)
  - `completed_shown`: 完了時に『PageFolio UAT 合成OCR結果』が結果欄へ表示
  - `post_count_1`: 合成サーバーのPOSTが1件(server記録)
  - `summary_not_run`: サマリは実行していない
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W04 / 06-UAT-CARRYOVER W04 / 06-UAT-PREPARATION fake OCR

## W05a 入れ子を閉じた外側ダイアログの入力維持

- 組: G3 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W05a / 06-UAT-CARRYOVER W05a

### W05a/nested-settings@script

**W05a / 設定→LLM設定を閉じる / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case nested | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case nested` で設定→LLM設定を開き、内側を閉じた状態を準備する。
  2. 実行担当: `peer --entry script` で二次起動する。
  3. 利用者: 外側(設定)の入力欄へキー入力し、文字・選択・カーソルが保たれているかを答える。
- **期待**: 内側を閉じた後も外側の入力・選択が保たれ、grabが残らない。
- **必須観測**:
  - `outer_input_kept`: 外側(設定)の入力欄の文字が残っている
  - `selection_kept`: 選択範囲・カーソルが保たれている
  - `grab_released_after_inner_close`: 内側を閉じた後に外側へ実キー入力できる(grabが残らない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W05a / 06-UAT-CARRYOVER W05a

### W05a/nested-settings@module

**W05a / 設定→LLM設定を閉じる / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case nested | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case nested` で設定→LLM設定を開き、内側を閉じた状態を準備する。
  2. 実行担当: `peer --entry module` で二次起動する。
  3. 利用者: 外側(設定)の入力欄へキー入力し、文字・選択・カーソルが保たれているかを答える。
- **期待**: 内側を閉じた後も外側の入力・選択が保たれ、grabが残らない。
- **必須観測**:
  - `outer_input_kept`: 外側(設定)の入力欄の文字が残っている
  - `selection_kept`: 選択範囲・カーソルが保たれている
  - `grab_released_after_inner_close`: 内側を閉じた後に外側へ実キー入力できる(grabが残らない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W05a / 06-UAT-CARRYOVER W05a

### W05a/nested-settings@production-exe

**W05a / 設定→LLM設定を閉じる / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W05a).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start` で起動する。
  2. 利用者: 「⚙ 設定」を開き入力欄に文字を入れ、このカードに限り内側の「LLM設定」を開いて何も変更せず閉じる(プロバイダは変更しない)。
  3. 実行担当: `peer` で二次起動する。
  4. 利用者: 外側の入力欄へキー入力し、文字・選択・カーソルが保たれているかを答える。
- **期待**: 実EXEで内側を閉じた後も外側の入力が保たれる。
- **必須観測**:
  - `outer_input_kept`: 外側(設定)の入力欄の文字が残っている
  - `selection_kept`: 選択範囲・カーソルが保たれている
  - `grab_released_after_inner_close`: 内側を閉じた後に外側へ実キー入力できる(grabが残らない)
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W05a / 06-UAT-CARRYOVER W05a

## W05b hold中のOCRDialog閉じる確認へ二次起動後も復帰し「いいえ」で同処理を完了

- 組: G3 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W05b / 06-UAT-CARRYOVER W05b / 06-04-SUMMARY Known Gaps 1

### W05b/ocr-close-confirm@script

**W05b / OCRDialog閉じる確認 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case native-ocr | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case native-ocr` でOCRDialog所有の確認messageboxが出た隔離ownerを準備する(自動クリックなし)。
  2. 実行担当: `peer --entry script` で二次起動する。
  3. 利用者: 確認が前面に戻っているのを確認して『いいえ』を押し、処理と入力が保たれたかを答える。
- **期待**: 確認ダイアログへ復帰し、『いいえ』でOCRDialogと処理が維持される。
- **必須観測**:
  - `modal_shown`: 『OCR 実行中です…閉じますか?』の確認が出た
  - `peer_returned_to_modal`: 二次起動後も同じ確認ダイアログが前面に戻る/残る
  - `answered_no`: 利用者が『いいえ』を押した
  - `input_and_process_kept`: OCRDialog・処理・入力が保たれた
  - `same_request_completed`: 同じrequestが完了し結果が表示された
  - `foreground_result`: API戻りと実foregroundを別記
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W05b / 06-UAT-CARRYOVER W05b / 06-04-SUMMARY Known Gaps 1

### W05b/ocr-close-confirm@module

**W05b / OCRDialog閉じる確認 / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case native-ocr | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case native-ocr` でOCRDialog所有の確認messageboxが出た隔離ownerを準備する(自動クリックなし)。
  2. 実行担当: `peer --entry module` で二次起動する。
  3. 利用者: 確認が前面に戻っているのを確認して『いいえ』を押し、処理と入力が保たれたかを答える。
- **期待**: 確認ダイアログへ復帰し、『いいえ』でOCRDialogと処理が維持される。
- **必須観測**:
  - `modal_shown`: 『OCR 実行中です…閉じますか?』の確認が出た
  - `peer_returned_to_modal`: 二次起動後も同じ確認ダイアログが前面に戻る/残る
  - `answered_no`: 利用者が『いいえ』を押した
  - `input_and_process_kept`: OCRDialog・処理・入力が保たれた
  - `same_request_completed`: 同じrequestが完了し結果が表示された
  - `foreground_result`: API戻りと実foregroundを別記
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W05b / 06-UAT-CARRYOVER W05b / 06-04-SUMMARY Known Gaps 1

### W05b/ocr-close-confirm@production-exe

**W05b / OCRDialog閉じる確認(実ダブルクリック) / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W05b --pdf ocr-one-page).run
  .venv/Scripts/python.exe tests/release_uat_support.py serve-ocr --run $run --mode hold
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  (二次起動は利用者がExplorerで隔離copyのPageFolio.exeをダブルクリック。peerコマンドは使わない)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copy・1page画像PDF・待機型合成OCRを準備して `start` する。LLM設定・プロバイダは、このカードが明示した場合を除き開かない・変更しない。
  2. 利用者: PDFを開き、ページ1を選択して『▶ 読み取り実行』を押す(待機に入る)。
  3. 利用者: OCRダイアログの『✕ 閉じる』を押し、確認ダイアログが出たら押さずに止まる。
  4. 利用者: Explorerで隔離copyの `PageFolio.exe` を実際にダブルクリックして二次起動する(合成peerでなく実操作。06-04からの持越し)。実行担当は前後のforegroundを外部観測する。
  5. 利用者: 確認ダイアログがどう見えたか(前面に戻った/PageFolio本体が前面/見えない)を答え、『いいえ』を押す。
  6. 実行担当: 待機を解放し、利用者が結果欄に『PageFolio UAT 合成OCR結果』が出たかを答える。
- **期待**: 実EXEでhold中の確認が二次起動後も維持され、『いいえ』で同じrequestが完了する。実ダブルクリック後のforegroundはAPI戻りと別に記録し、本体が前面なら観察どおり記録する。
- **必須観測**:
  - `modal_shown`: 『OCR 実行中です…閉じますか?』の確認が出た
  - `peer_returned_to_modal`: 二次起動後も同じ確認ダイアログが前面に戻る/残る
  - `answered_no`: 利用者が『いいえ』を押した
  - `input_and_process_kept`: OCRDialog・処理・入力が保たれた
  - `same_request_completed`: 同じrequestが完了し結果が表示された
  - `real_double_click_foreground`: 利用者の実ダブルクリック起動後のforeground(前景が確認ダイアログか/PageFolio本体か)。06-04の合成peerとは別記
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W05b / 06-UAT-CARRYOVER W05b / 06-04-SUMMARY Known Gaps 1

## W05c 終了確認Noと編集・排他の維持

- 組: G3 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W05c / 06-UAT-CARRYOVER W05c / 06-04-SUMMARY Known Gaps 3

### W05c/quit-no@script

**W05c / 終了確認でNo / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case native-quit | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case native-quit` で終了確認が出た隔離ownerを準備する。
  2. 実行担当: `peer --entry script` で確認中に二次起動する。
  3. 利用者: 『いいえ』を押し、編集内容と画面が保たれているかを答える。
- **期待**: Noで終了せず、編集と排他が維持される。
- **必須観測**:
  - `quit_confirm_shown`: 終了確認が出た
  - `answered_no`: 利用者が『いいえ』を押した
  - `edit_state_kept`: 編集内容・画面が保たれた
  - `owner_kept`: 排他(一次owner)が維持され、二次は一次にならない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W05c / 06-UAT-CARRYOVER W05c / 06-04-SUMMARY Known Gaps 3

### W05c/quit-no@module

**W05c / 終了確認でNo / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case native-quit | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case native-quit` で終了確認が出た隔離ownerを準備する。
  2. 実行担当: `peer --entry module` で確認中に二次起動する。
  3. 利用者: 『いいえ』を押し、編集内容と画面が保たれているかを答える。
- **期待**: Noで終了せず、編集と排他が維持される。
- **必須観測**:
  - `quit_confirm_shown`: 終了確認が出た
  - `answered_no`: 利用者が『いいえ』を押した
  - `edit_state_kept`: 編集内容・画面が保たれた
  - `owner_kept`: 排他(一次owner)が維持され、二次は一次にならない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W05c / 06-UAT-CARRYOVER W05c / 06-04-SUMMARY Known Gaps 3

### W05c/quit-no@production-exe

**W05c / 終了確認でNo / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W05c).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start` で起動する。
  2. 利用者: 何か編集(例: 3ページPDFのページ回転)をして、終了操作(ウィンドウの✕)を押す。確認が出たら押さずに止まる。
  3. 実行担当: 確認中に `peer` で二次起動し、ownerと窓を外部観測する。
  4. 利用者: 『いいえ』を押し、編集内容と画面が保たれているかを答える。
  5. 実行担当: 最後に `stop`(WM_CLOSE→必要時のみ所有handleで終了)し、終了経過(正常終了かforce終了か)を記録する。
- **期待**: 実EXEでNoにより終了せず編集と排他が維持される。回収時の終了経過は観測として記録する(合否判定ではない)。
- **必須観測**:
  - `quit_confirm_shown`: 終了確認が出た
  - `answered_no`: 利用者が『いいえ』を押した
  - `edit_state_kept`: 編集内容・画面が保たれた
  - `owner_kept`: 排他(一次owner)が維持され、二次は一次にならない
  - `stop_outcome`: 最後に回収した時の終了経過(close要求で終了した/force終了。06-04持越し観測)
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W05c / 06-UAT-CARRYOVER W05c / 06-04-SUMMARY Known Gaps 3

## W12a Python両入口・別配置の一次/二次3x3

- 組: G4 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/script-script@script

**W12a / 一次script→二次script / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=script: 既存harnessの一次起動(entry-owner-script相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をscript入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をscript入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/script-module@script

**W12a / 一次script→二次module / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=script: 既存harnessの一次起動(entry-owner-script相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をscript入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をmodule入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/script-relocated@script

**W12a / 一次script→二次relocated / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=script: 既存harnessの一次起動(entry-owner-script相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry relocated
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をscript入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をrelocated入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/module-script@module

**W12a / 一次module→二次script / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=module: 既存harnessの一次起動(entry-owner-module相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をmodule入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をscript入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/module-module@module

**W12a / 一次module→二次module / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=module: 既存harnessの一次起動(entry-owner-module相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をmodule入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をmodule入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/module-relocated@module

**W12a / 一次module→二次relocated / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=module: 既存harnessの一次起動(entry-owner-module相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry relocated
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をmodule入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をrelocated入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/relocated-script@relocated

**W12a / 一次relocated→二次script / 別配置のPython(複製pagefolio)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=relocated: 既存harnessの一次起動(entry-owner-relocated相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をrelocated入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をscript入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/relocated-module@relocated

**W12a / 一次relocated→二次module / 別配置のPython(複製pagefolio)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=relocated: 既存harnessの一次起動(entry-owner-relocated相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をrelocated入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をmodule入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

### W12a/relocated-relocated@relocated

**W12a / 一次relocated→二次relocated / 別配置のPython(複製pagefolio)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  一次=relocated: 既存harnessの一次起動(entry-owner-relocated相当)を実行担当がdriverで起動(G4で用意。現在は未準備)
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run <run> --entry relocated
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run <run>
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run <run>
  ```
- **利用者操作**:
  1. 実行担当: 一次をrelocated入口で隔離起動する(同nonce・隔離設定)。
  2. 実行担当: 二次をrelocated入口で `peer` する。接続先PID/生成時刻照合・API戻りを記録する。
  3. 利用者: 画面が1つだけか、一次の状態が保たれたまま前面に戻ったかを答える。
- **期待**: 一次が1つ・二次は追加の編集画面を作らず、同じ一次へ復帰する。
- **必須観測**:
  - `one_primary_screen`: 一次の画面が1つだけで二次は編集画面を増やさない
  - `secondary_returns_to_primary`: 二次が同じ一次の画面へ復帰を依頼する
  - `state_kept`: 一次の編集状態が保たれる
  - `api_return`: 許可APIの戻り・OS error(実foregroundとは別記)
  - `actual_foreground`: 復帰後の実foreground
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12a / 06-UAT-CARRYOVER W12a / 06-VALIDATION W12a

## W12b 最終実EXEとPython/対応版tracer/別配置の双方向混在

- 組: G4 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/exe-exe-samecopy@production-exe

**W12b / EXE同士(別配置の同版copy二次) / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=最終EXE→二次=同版の別配置copy。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/exe-script@production-exe

**W12b / 一次EXE→二次Python script / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=最終EXE→二次=Python直接起動。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/script-exe@script

**W12b / 一次Python script→二次EXE / Python直接起動(python pagefolio.py)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=Python直接起動→二次=最終EXE。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/exe-module@production-exe

**W12b / 一次EXE→二次Python -m / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=最終EXE→二次=Python -m。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/module-exe@module

**W12b / 一次Python -m→二次EXE / Python -m pagefolio**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=Python -m→二次=最終EXE。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/exe-tracer@production-exe

**W12b / 一次最終EXE→二次tracer(別版) / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=最終EXE→二次=06-01技術tracer(v1.9.1実EXE)。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/tracer-exe@tracer

**W12b / 一次tracer(別版)→二次最終EXE / tracer**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=06-01技術tracer→二次=最終EXE。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/exe-relocated-copy@production-exe

**W12b / 一次EXE→二次別配置copy / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=最終EXE→二次=別配置の同版copy。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

### W12b/relocated-copy-exe@relocated-copy

**W12b / 一次別配置copy→二次EXE / relocated-copy**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W12b --role final-release-candidate  # 主対象(最終EXE)
  (相手側) prepare --role technical-tracer-real-exe / 同版copyの別run、またはPython入口を別runで用意
  .venv/Scripts/python.exe tests/release_uat_support.py start --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run <一次のrun> --with-run <二次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run <一次のrun>
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run <各run>
  ```
- **利用者操作**:
  1. 実行担当: 一次=別配置の同版copy→二次=最終EXE。tracerを使う行は、保持先・run ID・source manifest・実版・EXE hashを06-01の report から読み、起動排他/固定namespace/protocolを持つ実装であることをsource manifestと同世代の自動証拠に照合してから使う(照合できなければこの行は not-run のまま)。
  2. 実行担当: 一次を `start` し、安定後に二次を起動して、PID・生成時刻・session・foregroundを外部観測する。
  3. 利用者: 一次の画面が1つだけか、二次起動後も同じ画面が前面で元の状態が保たれているかを答える。
- **期待**: 対応する実装を持つ組み合わせで、一次1画面・同sessionの復帰・元状態維持が観測できる。同版copyは別配置の根拠だけであり、別版の互換軸はtracer行だけが担う。tracerを公式旧版や最終EXE受入済みとは扱わない。
- **必須観測**:
  - `single_primary_screen`: 一次1画面だけが見える
  - `same_session_return`: 二次は同じsessionの一次へ復帰する
  - `primary_state_kept`: 元の状態(編集/入力)が維持される
  - `api_return`: 許可APIの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `peer_identity`: 相手側の入口・hash・版を記録(subject/peer欄と一致)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12b / 06-UAT-CARRYOVER W12b / 06-05-PLAN peer_contract

## W12c Explorer/端末の実入力とAPI戻り・foregroundの別記

- 組: G4 / 担当: 06-05-02
- 出典: 04-WINDOWS-UAT W12c / 06-UAT-CARRYOVER W12c

### W12c/explorer-python@script

**W12c / Explorerのショートカット→Python / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --production --case preview  # Pythonの固定名行のみ。既存ownerがあれば送信せず停止
  Explorer用の.lnk(既知Python+同じpeer引数)は実行担当が作る。EXE行は隔離copyのPageFolio.exeを使う
  ```
- **利用者操作**:
  1. 実行担当: 既存ownerが固定production namespaceにないことを読取で確認し、一次を起動する。
  2. 利用者: Explorerのショートカット→Pythonの経路で二次起動を実際に行い、元の入力先へキー入力を続ける。
  3. 実行担当: API戻り・OS errorと実foregroundを別々に記録する(入口別)。
  4. 利用者: 入力先が保たれたか、画面が増えなかったかを答える。
- **期待**: 入口ごとにAPI戻りと実foregroundが別記され、利用者の実入力が元の入力先へ入る。ショートカットの入口を製品CLIへの試験引数追加で代替しない。
- **必須観測**:
  - `launch_route`: 起動経路(Explorerショートカット/端末)
  - `api_return`: AllowSetForegroundWindowの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `real_input_target_kept`: 利用者の実入力が元の入力先へ入る
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12c / 06-UAT-CARRYOVER W12c

### W12c/terminal-python@script

**W12c / 端末→Python / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --production --case preview  # Pythonの固定名行のみ。既存ownerがあれば送信せず停止
  Explorer用の.lnk(既知Python+同じpeer引数)は実行担当が作る。EXE行は隔離copyのPageFolio.exeを使う
  ```
- **利用者操作**:
  1. 実行担当: 既存ownerが固定production namespaceにないことを読取で確認し、一次を起動する。
  2. 利用者: 端末→Pythonの経路で二次起動を実際に行い、元の入力先へキー入力を続ける。
  3. 実行担当: API戻り・OS errorと実foregroundを別々に記録する(入口別)。
  4. 利用者: 入力先が保たれたか、画面が増えなかったかを答える。
- **期待**: 入口ごとにAPI戻りと実foregroundが別記され、利用者の実入力が元の入力先へ入る。ショートカットの入口を製品CLIへの試験引数追加で代替しない。
- **必須観測**:
  - `launch_route`: 起動経路(Explorerショートカット/端末)
  - `api_return`: AllowSetForegroundWindowの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `real_input_target_kept`: 利用者の実入力が元の入力先へ入る
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W12c / 06-UAT-CARRYOVER W12c

### W12c/explorer-exe@production-exe

**W12c / Explorerのダブルクリック→EXE / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --production --case preview  # Pythonの固定名行のみ。既存ownerがあれば送信せず停止
  Explorer用の.lnk(既知Python+同じpeer引数)は実行担当が作る。EXE行は隔離copyのPageFolio.exeを使う
  ```
- **利用者操作**:
  1. 実行担当: 既存ownerが固定production namespaceにないことを読取で確認し、一次を起動する。
  2. 利用者: Explorerのダブルクリック→EXEの経路で二次起動を実際に行い、元の入力先へキー入力を続ける。
  3. 実行担当: API戻り・OS errorと実foregroundを別々に記録する(入口別)。
  4. 利用者: 入力先が保たれたか、画面が増えなかったかを答える。
- **期待**: 入口ごとにAPI戻りと実foregroundが別記され、利用者の実入力が元の入力先へ入る。ショートカットの入口を製品CLIへの試験引数追加で代替しない。
- **必須観測**:
  - `launch_route`: 起動経路(Explorerショートカット/端末)
  - `api_return`: AllowSetForegroundWindowの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `real_input_target_kept`: 利用者の実入力が元の入力先へ入る
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W12c / 06-UAT-CARRYOVER W12c

### W12c/terminal-exe@production-exe

**W12c / 端末→EXE / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --production --case preview  # Pythonの固定名行のみ。既存ownerがあれば送信せず停止
  Explorer用の.lnk(既知Python+同じpeer引数)は実行担当が作る。EXE行は隔離copyのPageFolio.exeを使う
  ```
- **利用者操作**:
  1. 実行担当: 既存ownerが固定production namespaceにないことを読取で確認し、一次を起動する。
  2. 利用者: 端末→EXEの経路で二次起動を実際に行い、元の入力先へキー入力を続ける。
  3. 実行担当: API戻り・OS errorと実foregroundを別々に記録する(入口別)。
  4. 利用者: 入力先が保たれたか、画面が増えなかったかを答える。
- **期待**: 入口ごとにAPI戻りと実foregroundが別記され、利用者の実入力が元の入力先へ入る。ショートカットの入口を製品CLIへの試験引数追加で代替しない。
- **必須観測**:
  - `launch_route`: 起動経路(Explorerショートカット/端末)
  - `api_return`: AllowSetForegroundWindowの戻り・OS error
  - `actual_foreground`: 実foreground(API戻りとは別記)
  - `real_input_target_kept`: 利用者の実入力が元の入力先へ入る
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W12c / 06-UAT-CARRYOVER W12c

## X01 設定ファイル不存在の既定起動

- 組: G5 / 担当: 06-05-02
- 出典: 05-CONTEXT D-13 / 06-VALIDATION X01 / 06-UAT-PREPARATION 設定障害

### X01/missing@production-exe

**X01 / 設定不存在 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind missing  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyで設定ファイルを置かず(overlay宣言)、`start` する。
  2. 実行担当: 起動が安定するまで設定ファイルが存在しないことを外部観測する。
  3. 利用者: 起動時に警告が出ず通常の画面になったかを答える。
  4. 実行担当: 終了後に設定ができていても、起動安定後の保存として別に記録する。
- **期待**: 警告なしで既定起動し、起動安定時までは設定ファイルがない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `settings_absent_until_stable`: 起動が安定するまで設定ファイルが存在しない(外部観測)
  - `no_warning_shown`: 起動時に警告が出ない
  - `default_launch`: 既定値で起動した
  - `exit_creation_not_failure`: 終了時の正当なwindow保存による作成は失敗として扱わない(別時点)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-13 / 06-VALIDATION X01 / 06-UAT-PREPARATION 設定障害

## X02 破損設定の非モーダル通知と原本保持

- 組: G5 / 担当: 06-05-02
- 出典: 05-CONTEXT D-13 / 06-VALIDATION X02

### X02/corrupt@production-exe

**X02 / 破損JSON / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind corrupt  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: 閉じていない不正JSONをoverlayとして置いた隔離copyを `start` する。
  2. 利用者: 通知の文言(原文)と、通知が入力先を奪っていないかを答える。
  3. 実行担当: 終了後も原本hashが起動前と一致することを外部照合する。
- **期待**: 破損用の非モーダル通知が出て既定値で起動し、原本は保持される。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `corrupt_notice_text`: 破損を示す非モーダルの通知文言(原文)
  - `original_bytes_preserved`: 破損した設定の原本bytesが前後で一致(hash)
  - `default_values_launch`: 既定値で起動した
  - `input_target_unchanged`: 通知が入力先を奪わない
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-13 / 06-VALIDATION X02

## X03 読取不能設定の別文言と保存抑止

- 組: G5 / 担当: 06-05-02
- 出典: 05-CONTEXT D-13/D-20 / 06-VALIDATION X03

### X03/unreadable@production-exe

**X03 / 読取不能(共有なしの外部handle) / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind unreadable  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: 観測側が共有なしの外部handleを保持して読取不能を作り、`start` する(成立しなければnot-run)。
  2. 利用者: 通知文言(破損と別か)と、設定の同値Applyなど明示操作で『未保存』が出るか・保存成功の表示が出ないかを答える。
  3. 実行担当: 原本hash不変と、外部handleが保たれていることを外部照合する。
- **期待**: 破損とは別の読取不能文言が出て、保存は抑止され、メモリ値は保持される。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `unreadable_notice_text`: 読取不能を示す通知文言(破損とは別の原文)
  - `original_hash_preserved`: 原本hashが前後で一致
  - `unsaved_notice_on_apply`: 明示操作で『未保存』通知が出て保存成功の偽表示がない
  - `holder_probe`: 外部handleの保持者PID/生成時刻と共有違反(32)のprobe
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-13/D-20 / 06-VALIDATION X03

## X04 保存失敗の保存元別通知(write/replace)

- 組: G6 / 担当: 06-05-02
- 出典: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

### X04/general-settings@production-exe

**X04 / 一般設定の変更 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ(外部probeで確認)、隔離copyを `start` する。
  2. 利用者: 「⚙ 設定」で一般設定を同値Applyする。
  3. 利用者: 失敗通知の文言(原文)と、操作した値が画面に残っているかを答える。write/replaceは同じ通知文なので、通知文だけから原因を断定しない。
  4. 実行担当: 元の設定hash不変・所有tmpの状態・操作/通知時刻を外部照合する。
- **期待**: 一般設定の変更で保存失敗が一つ通知され、メモリ値は残り、元の設定は変化しない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `fault_established_probe`: 外部probeで障害成立を確認(write=tmp衝突/replace=DELETE拒否32)
  - `failure_notice_text`: 保存失敗の通知文言(原文)
  - `memory_value_kept`: メモリ上の値が保持された
  - `original_hash_unchanged`: 元の設定hashが不変、所有tmpの状態
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

### X04/llm-or-external-prompt@production-exe

**X04 / LLM設定/外部プロンプトの保存 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ(外部probeで確認)、隔離copyを `start` する。
  2. 利用者: LLM設定(このカードに限り開く。プロバイダは変えない)または外部プロンプト編集で保存する。
  3. 利用者: 失敗通知の文言(原文)と、操作した値が画面に残っているかを答える。write/replaceは同じ通知文なので、通知文だけから原因を断定しない。
  4. 実行担当: 元の設定hash不変・所有tmpの状態・操作/通知時刻を外部照合する。
- **期待**: LLM設定/外部プロンプトの保存で保存失敗が一つ通知され、メモリ値は残り、元の設定は変化しない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `fault_established_probe`: 外部probeで障害成立を確認(write=tmp衝突/replace=DELETE拒否32)
  - `failure_notice_text`: 保存失敗の通知文言(原文)
  - `memory_value_kept`: メモリ上の値が保持された
  - `original_hash_unchanged`: 元の設定hashが不変、所有tmpの状態
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

### X04/shortcut@production-exe

**X04 / ショートカット設定の変更 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ(外部probeで確認)、隔離copyを `start` する。
  2. 利用者: ショートカット設定を開いて変更しApplyする。
  3. 利用者: 失敗通知の文言(原文)と、操作した値が画面に残っているかを答える。write/replaceは同じ通知文なので、通知文だけから原因を断定しない。
  4. 実行担当: 元の設定hash不変・所有tmpの状態・操作/通知時刻を外部照合する。
- **期待**: ショートカット設定の変更で保存失敗が一つ通知され、メモリ値は残り、元の設定は変化しない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `fault_established_probe`: 外部probeで障害成立を確認(write=tmp衝突/replace=DELETE拒否32)
  - `failure_notice_text`: 保存失敗の通知文言(原文)
  - `memory_value_kept`: メモリ上の値が保持された
  - `original_hash_unchanged`: 元の設定hashが不変、所有tmpの状態
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

### X04/plugin-change@production-exe

**X04 / プラグイン変更 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ(外部probeで確認)、隔離copyを `start` する。
  2. 利用者: プラグインの有効/無効を切り替える。
  3. 利用者: 失敗通知の文言(原文)と、操作した値が画面に残っているかを答える。write/replaceは同じ通知文なので、通知文だけから原因を断定しない。
  4. 実行担当: 元の設定hash不変・所有tmpの状態・操作/通知時刻を外部照合する。
- **期待**: プラグイン変更で保存失敗が一つ通知され、メモリ値は残り、元の設定は変化しない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `fault_established_probe`: 外部probeで障害成立を確認(write=tmp衝突/replace=DELETE拒否32)
  - `failure_notice_text`: 保存失敗の通知文言(原文)
  - `memory_value_kept`: メモリ上の値が保持された
  - `original_hash_unchanged`: 元の設定hashが不変、所有tmpの状態
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

### X04/ocr-conditions@production-exe

**X04 / OCR条件の変更 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ(外部probeで確認)、隔離copyを `start` する。
  2. 利用者: OCR条件(言語/並列等)を変更する。
  3. 利用者: 失敗通知の文言(原文)と、操作した値が画面に残っているかを答える。write/replaceは同じ通知文なので、通知文だけから原因を断定しない。
  4. 実行担当: 元の設定hash不変・所有tmpの状態・操作/通知時刻を外部照合する。
- **期待**: OCR条件の変更で保存失敗が一つ通知され、メモリ値は残り、元の設定は変化しない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `fault_established_probe`: 外部probeで障害成立を確認(write=tmp衝突/replace=DELETE拒否32)
  - `failure_notice_text`: 保存失敗の通知文言(原文)
  - `memory_value_kept`: メモリ上の値が保持された
  - `original_hash_unchanged`: 元の設定hashが不変、所有tmpの状態
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

### X04/tool-settings@production-exe

**X04 / ツール設定の変更 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ(外部probeで確認)、隔離copyを `start` する。
  2. 利用者: ツール設定(トリミング/モザイク粒度など)を変更する。
  3. 利用者: 失敗通知の文言(原文)と、操作した値が画面に残っているかを答える。write/replaceは同じ通知文なので、通知文だけから原因を断定しない。
  4. 実行担当: 元の設定hash不変・所有tmpの状態・操作/通知時刻を外部照合する。
- **期待**: ツール設定の変更で保存失敗が一つ通知され、メモリ値は残り、元の設定は変化しない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `fault_established_probe`: 外部probeで障害成立を確認(write=tmp衝突/replace=DELETE拒否32)
  - `failure_notice_text`: 保存失敗の通知文言(原文)
  - `memory_value_kept`: メモリ上の値が保持された
  - `original_hash_unchanged`: 元の設定hashが不変、所有tmpの状態
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

### X04/window-exit@production-exe

**X04 / ウィンドウ状態の終了時保存 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ(外部probeで確認)、隔離copyを `start` する。
  2. 利用者: ウィンドウの終了操作で終了時保存を発火させる(失敗時は初回終了を保留)。
  3. 利用者: 失敗通知の文言(原文)と、操作した値が画面に残っているかを答える。write/replaceは同じ通知文なので、通知文だけから原因を断定しない。
  4. 実行担当: 元の設定hash不変・所有tmpの状態・操作/通知時刻を外部照合する。
- **期待**: ウィンドウ状態の終了時保存で保存失敗が一つ通知され、メモリ値は残り、元の設定は変化しない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `fault_established_probe`: 外部probeで障害成立を確認(write=tmp衝突/replace=DELETE拒否32)
  - `failure_notice_text`: 保存失敗の通知文言(原文)
  - `memory_value_kept`: メモリ上の値が保持された
  - `original_hash_unchanged`: 元の設定hashが不変、所有tmpの状態
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

### X04/replace-notification@production-exe

**X04 / 置換(replace)失敗の通知 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-replace  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-replace` で障害を成立させ(外部probeで確認)、隔離copyを `start` する。
  2. 利用者: 設定を同値Applyする(読取/書込は共有・DELETE共有なしの外部handleで置換だけが失敗)。
  3. 利用者: 失敗通知の文言(原文)と、操作した値が画面に残っているかを答える。write/replaceは同じ通知文なので、通知文だけから原因を断定しない。
  4. 実行担当: 元の設定hash不変・所有tmpの状態・操作/通知時刻を外部照合する。
- **期待**: 置換(replace)失敗の通知で保存失敗が一つ通知され、メモリ値は残り、元の設定は変化しない。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `fault_established_probe`: 外部probeで障害成立を確認(write=tmp衝突/replace=DELETE拒否32)
  - `failure_notice_text`: 保存失敗の通知文言(原文)
  - `memory_value_kept`: メモリ上の値が保持された
  - `original_hash_unchanged`: 元の設定hashが不変、所有tmpの状態
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-21 / 06-VALIDATION X04

## X05 通知のFIFO・再構築残時間・終了D19/D20

- 組: G6 / 担当: 06-05-02
- 出典: 05-CONTEXT D-19/D-20/D-21 / 06-VALIDATION X05

### X05/fifo-10s@production-exe

**X05 / 同じ失敗が続いた時の10秒FIFO / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ、隔離copyを `start` する。
  2. 利用者: 同値Applyを2回行い、通知が1つずつ順に出るか・約10秒で消えるか・✕で閉じられるかを答える。
  3. 実行担当: 元hash不変・外部handleの保持・操作/通知時刻を外部照合し、終了経過(正常終了/force終了)を記録する。
- **期待**: 同じ失敗が続いた時の10秒FIFOが観測できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `events_in_order`: 2回の失敗が1つずつ順に表示
  - `visible_10s_each`: 各イベント約10秒で消える/✕で閉じられる
  - `no_merge_or_drop`: 統合・破棄・件数表示への合併がない
  - `fault_established_probe`: 外部probeで障害成立を確認
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-20/D-21 / 06-VALIDATION X05

### X05/rebuild-remaining-time@production-exe

**X05 / 言語切替(再構築)後の残り時間分の表示 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-write  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-write` で障害を成立させ、隔離copyを `start` する。
  2. 利用者: 通知表示中に言語を切り替え、同じ通知が現在言語で残り時間分だけ出るかを答える。
  3. 実行担当: 元hash不変・外部handleの保持・操作/通知時刻を外部照合し、終了経過(正常終了/force終了)を記録する。
- **期待**: 言語切替(再構築)後の残り時間分の表示が観測できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `language_switch_done`: 通知中に言語を切り替えた
  - `remaining_time_only`: 再構築後の通知が現在言語で残り時間分だけ表示
  - `fault_established_probe`: 外部probeで障害成立を確認
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-20/D-21 / 06-VALIDATION X05

### X05/exit-no-first-fail-second-exit@production-exe

**X05 / 終了No→初回失敗で画面維持→次の終了で保存省略(D19) / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind save-replace  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind save-replace` で障害を成立させ、隔離copyを `start` する。
  2. 利用者: 終了→確認で『いいえ』→再度終了→『はい』で初回失敗(画面が残る)→もう一度終了で保存せず終了、の各段階を答える。
  3. 実行担当: 元hash不変・外部handleの保持・操作/通知時刻を外部照合し、終了経過(正常終了/force終了)を記録する。
- **期待**: 終了No→初回失敗で画面維持→次の終了で保存省略(D19)が観測できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `exit_no_no_save`: 最初の終了でNoを押し保存を試さない
  - `first_yes_fails_and_stays`: Yesで初回保存失敗・編集画面を維持
  - `next_exit_skips_save`: 次の独立した終了は保存を省略して終了
  - `fault_established_probe`: 外部probeで障害成立を確認
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-20/D-21 / 06-VALIDATION X05

### X05/unreadable-save-suppressed@production-exe

**X05 / 読取不能時の保存抑止と終了時追加通知なし(D20) / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X ).run
  .venv/Scripts/python.exe tests/release_uat_support.py fault --run $run --kind unreadable  # 外部handle/tmp衝突を保持。成立しなければexit 3(not-run)
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run   # faultは $run/release-fault.flag で解放
  ```
- **利用者操作**:
  1. 実行担当: `fault --kind unreadable` で障害を成立させ、隔離copyを `start` する。
  2. 利用者: 読取不能の状態で同値Applyを行い『未保存』が毎回出るか、終了時に追加の失敗通知が出ずに終了できるかを答える。
  3. 実行担当: 元hash不変・外部handleの保持・操作/通知時刻を外部照合し、終了経過(正常終了/force終了)を記録する。
- **期待**: 読取不能時の保存抑止と終了時追加通知なし(D20)が観測できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `unsaved_notice_each_apply`: 明示操作で毎回『未保存』通知
  - `no_extra_notice_on_exit`: 終了時に追加の保存失敗通知が出ない
  - `exit_via_confirm`: 既存の確認を経て終了できる
  - `fault_established_probe`: 外部probeで障害成立を確認
  - `operation_time`: 操作時刻と通知時刻
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 05-CONTEXT D-19/D-20/D-21 / 06-VALIDATION X05

## X06 サンプル利用・更新保護・版表示

- 組: G6 / 担当: 06-05-02
- 出典: 06-02 同梱文書 / 06-04 保護 / 06-VALIDATION X06

### X06/sample-llm-ui-read@production-exe

**X06 / サンプルをLLM UIから外部読み込み / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X06 --pdf ocr-one-page).run  # サンプル2種は個別copy
  .venv/Scripts/python.exe tests/release_uat_support.py serve-ocr --run $run --mode hold  # OCR行のみ
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copy(サンプル2種を個別にコピーした状態)を準備し `start` する。
  2. 利用者: サンプルを `ocr_custom_prompt.md` へコピーした隔離copyで、LLM設定のプロンプトとして読み込まれるかを答える(このカードに限りLLM設定を開く。プロバイダは変えない)。
  3. 実行担当: サンプル/配布treeの前後hashと同梱report/APP_VERSIONの一致を外部照合する。
- **期待**: サンプルをLLM UIから外部読み込みが確認できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `copied_sample_loaded`: 隔離copyのサンプルを別名コピーしてLLM UIで読み込めた
  - `loaded_text_head`: 読み込まれた内容の先頭(原文)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 06-02 同梱文書 / 06-04 保護 / 06-VALIDATION X06

### X06/sample-ocr-actual-read@production-exe

**X06 / サンプルを実OCRの外部プロンプトとして読み込み / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X06 --pdf ocr-one-page).run  # サンプル2種は個別copy
  .venv/Scripts/python.exe tests/release_uat_support.py serve-ocr --run $run --mode hold  # OCR行のみ
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copy(サンプル2種を個別にコピーした状態)を準備し `start` する。
  2. 利用者: コピーしたプロンプトで1page画像PDFのOCRを実行し、結果が出るかを答える(合成サーバー・サマリなし)。
  3. 実行担当: サンプル/配布treeの前後hashと同梱report/APP_VERSIONの一致を外部照合する。
- **期待**: サンプルを実OCRの外部プロンプトとして読み込みが確認できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `prompt_used_in_request`: 合成サーバーが受信したrequestのプロンプトにコピーした文面が含まれる
  - `post_count_1`: POST1件
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 06-02 同梱文書 / 06-04 保護 / 06-VALIDATION X06

### X06/name-collision-stops@production-exe

**X06 / 既存名と衝突する時はコピーを止める / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X06 --pdf ocr-one-page).run  # サンプル2種は個別copy
  .venv/Scripts/python.exe tests/release_uat_support.py serve-ocr --run $run --mode hold  # OCR行のみ
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copy(サンプル2種を個別にコピーした状態)を準備し `start` する。
  2. 利用者: ガイドの手順に従い、同名の既存ファイルがある状態でコピーしようとして止まるかを答える(実行担当が前後hashを照合)。
  3. 実行担当: サンプル/配布treeの前後hashと同梱report/APP_VERSIONの一致を外部照合する。
- **期待**: 既存名と衝突する時はコピーを止めるが確認できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `collision_stopped_before_choice`: 同名ファイルがある時、上書きせず停止する
  - `both_files_unchanged`: 旧・新の両方のhashが不変
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 06-02 同梱文書 / 06-04 保護 / 06-VALIDATION X06

### X06/guide-update-steps@production-exe

**X06 / ガイドの更新手順 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X06 --pdf ocr-one-page).run  # サンプル2種は個別copy
  .venv/Scripts/python.exe tests/release_uat_support.py serve-ocr --run $run --mode hold  # OCR行のみ
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copy(サンプル2種を個別にコピーした状態)を準備し `start` する。
  2. 利用者: 同梱の『はじめに.md』の更新手順を読み、記載どおりにコピー・確認できたかを答える。
  3. 実行担当: サンプル/配布treeの前後hashと同梱report/APP_VERSIONの一致を外部照合する。
- **期待**: ガイドの更新手順が確認できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `guide_steps_followed`: はじめに.md の更新手順(旧フォルダーを残す/両方選択)どおりに実施できた
  - `old_folder_kept`: 旧フォルダーが残っている
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 06-02 同梱文書 / 06-04 保護 / 06-VALIDATION X06

### X06/about-version-match@production-exe

**X06 / AboutDialogの版表示がfolder/reportの版と一致 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case X06 --pdf ocr-one-page).run  # サンプル2種は個別copy
  .venv/Scripts/python.exe tests/release_uat_support.py serve-ocr --run $run --mode hold  # OCR行のみ
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copy(サンプル2種を個別にコピーした状態)を準備し `start` する。
  2. 利用者: ヘルプ/AboutでPageFolioの版を開き、表示された版を答える(メインタイトルに版を足すことは求めない)。
  3. 実行担当: サンプル/配布treeの前後hashと同梱report/APP_VERSIONの一致を外部照合する。
- **期待**: AboutDialogの版表示がfolder/reportの版と一致が確認できる。実EXE固有の新規受入。Phase5 H01〜H14の再実施ではない。固定hashの隔離copyで、06-03/06-04の外部lock・tmp衝突を根拠にする。
- **必須観測**:
  - `about_version_text`: AboutDialogに表示された版(原文)
  - `matches_folder_and_report`: フォルダー名・release-report.json・APP_VERSIONと一致
  - `title_unchanged`: メインタイトルはPageFolio固定のまま
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 06-02 同梱文書 / 06-04 保護 / 06-VALIDATION X06

## W06 他process入力中の実OS拒否・有限点滅・15秒再前面化なし

- 組: G7 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W06

### W06/foreground-denied@script

**W06 / OS拒否 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case preview | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case preview` を準備し、利用者が別processの入力欄へ切り替える。
  2. 実行担当: `peer --entry script` を行い入力を続けさせ15秒まで観測する。拒否が出なければnot-runのまま再試行。
  3. 利用者: 入力が奪われなかったか、点滅が有限か、15秒後に前面へ戻らなかったかを答える。
- **期待**: 実OS拒否時に有限の点滅だけで終わり、入力が奪われず15秒後も再前面化されない。
- **必須観測**:
  - `other_process_input_continued`: 別processの入力欄へ入力を続けられた
  - `os_denied_observed`: 実OSが前面化を拒否した(許可成功の試行は拒否に数えない)
  - `taskbar_flash_finite`: タスクバー点滅が有限(3回/250ms目安、2秒内に停止)
  - `no_refocus_after_15s`: 15秒後に再前面化されない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W06

### W06/foreground-denied@module

**W06 / OS拒否 / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case preview | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case preview` を準備し、利用者が別processの入力欄へ切り替える。
  2. 実行担当: `peer --entry module` を行い入力を続けさせ15秒まで観測する。拒否が出なければnot-runのまま再試行。
  3. 利用者: 入力が奪われなかったか、点滅が有限か、15秒後に前面へ戻らなかったかを答える。
- **期待**: 実OS拒否時に有限の点滅だけで終わり、入力が奪われず15秒後も再前面化されない。
- **必須観測**:
  - `other_process_input_continued`: 別processの入力欄へ入力を続けられた
  - `os_denied_observed`: 実OSが前面化を拒否した(許可成功の試行は拒否に数えない)
  - `taskbar_flash_finite`: タスクバー点滅が有限(3回/250ms目安、2秒内に停止)
  - `no_refocus_after_15s`: 15秒後に再前面化されない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W06

### W06/foreground-denied@production-exe

**W06 / OS拒否 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W06).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start`。利用者が別processの入力欄へ切り替える。
  2. 実行担当: `peer` で二次起動し、入力を続けさせて15秒まで外部観測する。
  3. 利用者: 同上を答える。
- **期待**: 実EXEでも実OS拒否時に有限点滅で入力が奪われない。
- **必須観測**:
  - `other_process_input_continued`: 別processの入力欄へ入力を続けられた
  - `os_denied_observed`: 実OSが前面化を拒否した(許可成功の試行は拒否に数えない)
  - `taskbar_flash_finite`: タスクバー点滅が有限(3回/250ms目安、2秒内に停止)
  - `no_refocus_after_15s`: 15秒後に再前面化されない
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W06

## W07a slowready: 5秒失効・10秒案内・遅延復帰0

- 組: G7 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W07a / 05-CONTEXT D-05/06/08

### W07a/slowready@script

**W07a / 初期化遅延(Python注入) / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case slowready | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case slowready` で初期化を6.5秒遅延し直ちに `peer`。生result/ready/auditを保存する。
  2. 利用者: 生結果を照合し、一次の通常表示と期限切れ後に前面化されなかったことを答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: 5秒失効・10秒案内・復帰0がPython注入の生結果と人手照合で一致する。
- **必須観測**:
  - `backend_expired_5000ms`: backend raw結果と5000ms失効の記録
  - `notice_10000ms`: 10秒案内の可視時間
  - `restored_count_0`: 遅延後の復帰回数が0
  - `primary_normal_display`: 一次の通常表示と期限切れ前面化の区別を人手照合
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W07a / 05-CONTEXT D-05/06/08

### W07a/cold-start-double-launch@production-exe

**W07a / 実EXEの二重起動 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W07a).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start` し、起動が終わる前に二次を連続起動する(実EXEの自然な起動時間)。
  2. 利用者: 最終的に画面が1つだけか、遅れて前面に飛んでこないかを答える。
- **期待**: 実EXEの自然な起動遅延でも画面は1つで、遅延後の不意な前面化がない。frozen hookは使わない。
- **必須観測**:
  - `single_primary_screen`: 画面が1つだけで追加の編集画面なし
  - `no_late_restore`: 遅延後に不意の前面化がない
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W07a / 05-CONTEXT D-05/06/08

## W07b busy: 失効後のqueue副作用0

- 組: G8 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W07b / 06-UAT-CARRYOVER W07b

### W07b/busy@module

**W07b / UI同期busy(Python注入) / Python -m pagefolio**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case busy | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: `start --case busy`(ready後にUI同期busy 6.5秒を注入)と `peer`。単独条件と並行負荷条件を別runで保存する。
  2. 利用者: 生結果を照合し、復帰0と副作用0を答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: 単独条件で失効・復帰0。並行負荷15609msは15.5秒上限を超えた事実を保持する。
- **必須観測**:
  - `backend_expired_5000ms`: backend raw結果と5000ms失効
  - `restored_count_0_before_after`: busy前後の復帰回数0/0
  - `expired_queue_no_side_effect`: 失効したqueueの副作用0
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W07b / 06-UAT-CARRYOVER W07b

### W07b/natural-busy@production-exe

**W07b / 実EXEの自然busy / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W07b).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを `start`。利用者が5秒以上続く実際のUI同期操作を作る(作れなければ blocked と記録し親判断へ)。
  2. 実行担当: busy中に `peer` し、失効後の挙動を外部観測する。
  3. 利用者: 失効後に不意の動作がないかを答える。
- **期待**: 実busyで失効後のqueue副作用がない。実busyを作れない場合はnot-runのまま親が準備継続か再計画を判断する。
- **必須観測**:
  - `busy_created_by_real_operation`: 人が作った実busy(例: 大きな合成PDFの保存)の内容と継続時間
  - `expired_queue_no_side_effect`: 失効後に副作用なし
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W07b / 06-UAT-CARRYOVER W07b

## W08a 初期化死亡・同時claim・引継ぎ1回

- 組: G9 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W08a

### W08a/init-death-simultaneous-claim@script

**W08a / Python注入の生結果 / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: 既存の `test_lifecycle_*`/`test_takeover_*`/`test_simultaneous_*` 経路で生ready/audit/resultを保存する(人にprocess killは依頼しない)。
  2. 利用者: 生記録を照合して答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: 初期化死亡後の同時claimで新一次が1つ・引継ぎ1回。
- **必須観測**:
  - `one_new_primary`: 新しい一次が1つだけ
  - `takeover_once`: 死亡確認後の引継ぎが1回だけ
  - `raw_result_reviewed`: 生ready/audit/resultを人手で照合
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08a

### W08a/simultaneous-launch-and-takeover@production-exe

**W08a / 実EXE同時起動 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W08a).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyを2つ同時に近く起動し、観測者が一次を外部確認する。
  2. 実行担当: 一次を所有handleで終了(外部)し、新しい起動が1つだけ新一次になることを観測する。
  3. 利用者: 画面の数と状態を答える。
- **期待**: 実EXEでも同時起動で一次は1つ、死亡後の新起動で新しい一次が1つ立つ。
- **必須観測**:
  - `one_primary_screen`: 同時起動しても一次の画面は1つ
  - `takeover_after_owner_death`: 一次を所有handleで終了した後の新起動が新しい一次になる
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W08a

## W08b 終了形態別の再起動

- 組: G9 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W08b

### W08b/lifecycle-exit-modes@script

**W08b / Python注入4形態 / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: 正常/強制/初期化例外/公開前例外の4形態の生記録を保存。
  2. 利用者: 照合して答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: 4形態いずれの後も新一次が立つ。
- **必須観測**:
  - `restart_new_primary`: 再起動で新しい一次が立つ
  - `raw_result_reviewed`: 終了形態ごとの生記録を照合
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08b

### W08b/normal-exit-relaunch@production-exe

**W08b / 実EXE通常終了 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W08b).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 利用者: 隔離copyのPageFolioを通常終了(確認でYes)し、実行担当が再起動して新一次を確認する。
  2. 利用者: 再起動後の状態を答える。
- **期待**: 通常終了後に新しい一次が立つ。
- **必須観測**:
  - `restart_new_primary`: 再起動で新しい一次が立つ
  - `raw_result_reviewed`: 終了形態ごとの生記録を照合
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W08b

### W08b/forced-kill-relaunch@production-exe

**W08b / 実EXE強制終了 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W08b).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyの一次を所有handleで強制終了し、再起動して新一次を確認する。
  2. 利用者: 再起動後の状態を答える。
- **期待**: 強制終了後に新しい一次が立つ。
- **必須観測**:
  - `restart_new_primary`: 再起動で新しい一次が立つ
  - `raw_result_reviewed`: 終了形態ごとの生記録を照合
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W08b

## W08c 終了Noのmutex保持とYes後の新一次

- 組: G10 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W08c / W05c対応

### W08c/quit-no-then-yes@script

**W08c / 終了No/Yes / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: W05cと同じ経路で終了確認No→Yesを行い、owner probeを記録する。
  2. 利用者: 各段階の画面を答える。
- **期待**: Noで排他維持、Yes後の独立起動のみ新一次。
- **必須観測**:
  - `no_keeps_mutex`: Noの間は排他(mutex)が保たれる
  - `yes_then_new_primary`: Yes後の独立起動だけが新一次
  - `linked_w05c_answer`: W05cの実No操作の回答と対応付け
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08c / W05c対応

### W08c/quit-no-then-yes@production-exe

**W08c / 終了No/Yes / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W08c).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 隔離copyで終了確認No→Yesを行い、owner probeを記録する。
  2. 利用者: 各段階の画面を答える。
- **期待**: 実EXEでもNoで排他維持、Yes後の独立起動のみ新一次。
- **必須観測**:
  - `no_keeps_mutex`: Noの間は排他(mutex)が保たれる
  - `yes_then_new_primary`: Yes後の独立起動だけが新一次
  - `linked_w05c_answer`: W05cの実No操作の回答と対応付け
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W08c / W05c対応

## W08d root消失・旧worker・released・古mapping・同時claim・OS死亡

- 組: G10 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W08d

### W08d/root-missing@script

**W08d / root消失 / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: root消失の生記録を既存試験経路で保存する。
  2. 利用者: 照合して答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: root消失が他の原因と区別して記録されている。
- **必須観測**:
  - `record_reviewed`: root消失の生record確認
  - `not_confused_with_other_cause`: OS死亡とroot消失を混同していない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08d

### W08d/worker-alive@script

**W08d / 旧worker生存 / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: 旧worker生存の生記録を既存試験経路で保存する。
  2. 利用者: 照合して答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: 旧worker生存が他の原因と区別して記録されている。
- **必須観測**:
  - `record_reviewed`: 旧worker生存の生record確認
  - `not_confused_with_other_cause`: OS死亡とroot消失を混同していない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08d

### W08d/released-mapping@script

**W08d / released公開 / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: released公開の生記録を既存試験経路で保存する。
  2. 利用者: 照合して答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: released公開が他の原因と区別して記録されている。
- **必須観測**:
  - `record_reviewed`: released公開の生record確認
  - `not_confused_with_other_cause`: OS死亡とroot消失を混同していない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08d

### W08d/stale-mapping@script

**W08d / 古mapping保持 / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: 古mapping保持の生記録を既存試験経路で保存する。
  2. 利用者: 照合して答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: 古mapping保持が他の原因と区別して記録されている。
- **必須観測**:
  - `record_reviewed`: 古mapping保持の生record確認
  - `not_confused_with_other_cause`: OS死亡とroot消失を混同していない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08d

### W08d/simultaneous-claim@script

**W08d / 同時claim / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: 同時claimの生記録を既存試験経路で保存する。
  2. 利用者: 照合して答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: 同時claimが他の原因と区別して記録されている。
- **必須観測**:
  - `record_reviewed`: 同時claimの生record確認
  - `not_confused_with_other_cause`: OS死亡とroot消失を混同していない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08d

### W08d/os-death@script

**W08d / OS process死亡 / Python直接起動(python pagefolio.py)**(証拠種別: `fault-injection`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or takeover or simultaneous" --basetemp=<新規GUID>  # 生ready/audit/resultを保存
  ```
- **利用者操作**:
  1. 実行担当: OS process死亡の生記録を既存試験経路で保存する。
  2. 利用者: 照合して答える。
  3. 実EXEにはfrozen hookがなく、この注入は届かない。注入結果はPython側の生結果(fault-injection)の人手照合に限り、実EXEの共通挙動は別行で扱う。
- **期待**: OS process死亡が他の原因と区別して記録されている。
- **必須観測**:
  - `record_reviewed`: OS process死亡の生record確認
  - `not_confused_with_other_cause`: OS死亡とroot消失を混同していない
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W08d

### W08d/os-death-forced-kill@production-exe

**W08d / 実EXE OS死亡 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W08d).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 一次を所有handleで強制終了し、owner probeと新起動を観測する。
  2. 利用者: 画面の状態を答える。
- **期待**: 実EXEでOS死亡後に古い状態が残らず新一次が立つ。
- **必須観測**:
  - `owner_gone_confirmed`: OS死亡後にownerが消えた
  - `new_primary_after_death`: 新しい起動が一次になる
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W08d

## W09a 新通知の実クリック・入力非干渉・10秒・集約

- 組: G11 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W09a

### W09a/notice-click-input-10s-aggregate@script

**W09a / Python noticeハーネス / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $n = .venv/Scripts/python.exe tests/test_startup_windows.py --uat notice | ConvertFrom-Json   # 新しい可視通知lease
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $n.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $n.run
  ```
- **利用者操作**:
  1. 実行担当: `--uat notice` で新しい可視通知leaseを準備(別runでクリックと10秒を確認)。
  2. 利用者: 別processの入力を続けたまま、閉じる領域をクリック/無操作10秒を試し答える。
- **期待**: 通知が入力を妨げず、クリックまたは10秒で閉じ、集約され残留しない。
- **必須観測**:
  - `click_closes`: 閉じる領域の実クリックで閉じる
  - `input_not_disturbed`: 別processの入力を妨げない
  - `auto_close_10s`: 無操作10秒で閉じる
  - `aggregated_single_display`: 複数peerでも同時表示は1件
  - `no_residual_15s_after_close`: 閉鎖後15秒残留なし
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W09a

### W09a/suspended-primary-notice@production-exe

**W09a / 実EXE通知(外部停止) / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W09a).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 一次EXEを所有handleで一時停止して応答不能を外部条件として作り(実busyとは別と記録)、二次起動で5秒失効→通知を出す(06-06-01でdriverを用意)。
  2. 利用者: 通知の操作を同上のとおり行い答える。
- **期待**: 実EXEの通知が同様に動作する。応答不能の作り方は外部条件として記録。
- **必須観測**:
  - `click_closes`: 閉じる領域の実クリックで閉じる
  - `input_not_disturbed`: 別processの入力を妨げない
  - `auto_close_10s`: 無操作10秒で閉じる
  - `aggregated_single_display`: 複数peerでも同時表示は1件
  - `no_residual_15s_after_close`: 閉鎖後15秒残留なし
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W09a

## W09b 実DPI 100% の通知表示

- 組: G11 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W09b

### W09b/dpi-100@script

**W09b / DPI100 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $n = .venv/Scripts/python.exe tests/test_startup_windows.py --uat notice | ConvertFrom-Json   # 新しい可視通知lease
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $n.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $n.run
  ```
- **利用者操作**:
  1. 利用者: Windowsの表示設定を100%にする(実状態)。実行担当が `--uat notice` で通知を出す。
  2. 利用者: 全文と閉じる領域が見えるかを答える。
- **期待**: 100%で通知の全文と閉じる領域が見える。
- **必須観測**:
  - `dpi_setting`: Windows表示設定が100%の実状態
  - `full_text_visible`: 通知の全文が欠けず表示
  - `close_area_visible`: 閉じる領域が見え押せる
  - `screen_record`: 通知/DPIの画面記録または写真
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W09b

### W09b/dpi-100@production-exe

**W09b / DPI100 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W09b).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 利用者: 表示設定100%の状態で、実EXEの通知を出す(W09aの外部停止方式)。
  2. 利用者: 全文と閉じる領域が見えるかを答える。
- **期待**: 実EXEでも100%で通知が正しく表示される。
- **必須観測**:
  - `dpi_setting`: Windows表示設定が100%の実状態
  - `full_text_visible`: 通知の全文が欠けず表示
  - `close_area_visible`: 閉じる領域が見え押せる
  - `screen_record`: 通知/DPIの画面記録または写真
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W09b

## W09c 実DPI 150% の通知表示

- 組: G12 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W09c

### W09c/dpi-150@script

**W09c / DPI150 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $n = .venv/Scripts/python.exe tests/test_startup_windows.py --uat notice | ConvertFrom-Json   # 新しい可視通知lease
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $n.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $n.run
  ```
- **利用者操作**:
  1. 利用者: Windowsの表示設定を150%にする(実状態)。実行担当が `--uat notice` で通知を出す。
  2. 利用者: 全文と閉じる領域が見えるかを答える。
- **期待**: 150%で通知の全文と閉じる領域が見える。
- **必須観測**:
  - `dpi_setting`: Windows表示設定が150%の実状態
  - `full_text_visible`: 通知の全文が欠けず表示
  - `close_area_visible`: 閉じる領域が見え押せる
  - `screen_record`: 通知/DPIの画面記録または写真
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W09c

### W09c/dpi-150@production-exe

**W09c / DPI150 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W09c).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 利用者: 表示設定150%の状態で、実EXEの通知を出す(W09aの外部停止方式)。
  2. 利用者: 全文と閉じる領域が見えるかを答える。
- **期待**: 実EXEでも150%で通知が正しく表示される。
- **必須観測**:
  - `dpi_setting`: Windows表示設定が150%の実状態
  - `full_text_visible`: 通知の全文が欠けず表示
  - `close_area_visible`: 閉じる領域が見え押せる
  - `screen_record`: 通知/DPIの画面記録または写真
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W09c

## W09d 実DPI 200% の通知表示

- 組: G12 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W09d

### W09d/dpi-200@script

**W09d / DPI200 / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $n = .venv/Scripts/python.exe tests/test_startup_windows.py --uat notice | ConvertFrom-Json   # 新しい可視通知lease
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $n.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $n.run
  ```
- **利用者操作**:
  1. 利用者: Windowsの表示設定を200%にする(実状態)。実行担当が `--uat notice` で通知を出す。
  2. 利用者: 全文と閉じる領域が見えるかを答える。
- **期待**: 200%で通知の全文と閉じる領域が見える。
- **必須観測**:
  - `dpi_setting`: Windows表示設定が200%の実状態
  - `full_text_visible`: 通知の全文が欠けず表示
  - `close_area_visible`: 閉じる領域が見え押せる
  - `screen_record`: 通知/DPIの画面記録または写真
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W09d

### W09d/dpi-200@production-exe

**W09d / DPI200 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W09d).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 利用者: 表示設定200%の状態で、実EXEの通知を出す(W09aの外部停止方式)。
  2. 利用者: 全文と閉じる領域が見えるかを答える。
- **期待**: 実EXEでも200%で通知が正しく表示される。
- **必須観測**:
  - `dpi_setting`: Windows表示設定が200%の実状態
  - `full_text_visible`: 通知の全文が欠けず表示
  - `close_area_visible`: 閉じる領域が見え押せる
  - `screen_record`: 通知/DPIの画面記録または写真
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W09d

## W10a UAC medium→elevated

- 組: G13 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W10a

### W10a/medium→elevated@script

**W10a / medium→elevated / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $n = .venv/Scripts/python.exe tests/test_startup_windows.py --uat notice | ConvertFrom-Json   # 新しい可視通知lease
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $n.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $n.run
  ```
- **利用者操作**:
  1. 実行担当: 一次をmediumで `start`、二次をelevatedで `peer`(UACは利用者が操作。背景helperは-WindowStyle Hidden)。
  2. 利用者: UACと画面の状態を答える。
- **期待**: 4資源が個別に記録され、権限差でも1画面に復帰する。
- **必須観測**:
  - `owner_resource`: owner/mapping/双方向pipe/新noticeの4資源を個別記録
  - `sid_luid_session`: SID/LUID/sessionの外部記録
  - `uac_operation`: 利用者が行ったUAC操作
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W10a

### W10a/medium→elevated@production-exe

**W10a / medium→elevated / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W10a).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 実EXEの一次をmedium、二次をelevatedで起動。
  2. 利用者: UACと画面の状態を答える。
- **期待**: 実EXEで同様に動作する。アカウント新設・資格情報取得・mockは行わない。
- **必須観測**:
  - `owner_resource`: owner/mapping/双方向pipe/新noticeの4資源を個別記録
  - `sid_luid_session`: SID/LUID/sessionの外部記録
  - `uac_operation`: 利用者が行ったUAC操作
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W10a

## W10b UAC elevated→medium

- 組: G13 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W10b

### W10b/elevated→medium@script

**W10b / elevated→medium / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $n = .venv/Scripts/python.exe tests/test_startup_windows.py --uat notice | ConvertFrom-Json   # 新しい可視通知lease
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $n.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $n.run
  ```
- **利用者操作**:
  1. 実行担当: 一次をelevatedで `start`、二次をmediumで `peer`(UACは利用者が操作。背景helperは-WindowStyle Hidden)。
  2. 利用者: UACと画面の状態を答える。
- **期待**: 4資源が個別に記録され、権限差でも1画面に復帰する。
- **必須観測**:
  - `owner_resource`: owner/mapping/双方向pipe/新noticeの4資源を個別記録
  - `sid_luid_session`: SID/LUID/sessionの外部記録
  - `uac_operation`: 利用者が行ったUAC操作
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W10b

### W10b/elevated→medium@production-exe

**W10b / elevated→medium / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W10b).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 実EXEの一次をelevated、二次をmediumで起動。
  2. 利用者: UACと画面の状態を答える。
- **期待**: 実EXEで同様に動作する。アカウント新設・資格情報取得・mockは行わない。
- **必須観測**:
  - `owner_resource`: owner/mapping/双方向pipe/新noticeの4資源を個別記録
  - `sid_luid_session`: SID/LUID/sessionの外部記録
  - `uac_operation`: 利用者が行ったUAC操作
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W10b

## W11 既存別sessionへの各1画面と復帰

- 組: G14 / 担当: 06-06-01
- 出典: 04-WINDOWS-UAT W11(準備不能)

### W11/other-session@script

**W11 / 別session / Python直接起動(python pagefolio.py)**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case preview | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: 既存の別Windowsアカウントがある場合のみ、共通`--namespace`で各sessionに`start`。利用者が切替(サインアウトしない)。
  2. 準備不能ならnot-run/blockedのまま。アカウント新設・資格情報取得・mockで代替しない。
- **期待**: 各sessionに1画面、同sessionへ復帰、元状態不変。準備不能は出荷停止として親へ返す。
- **必須観測**:
  - `each_session_one_screen`: 各sessionに1画面
  - `returns_to_same_session`: 二次は同sessionへ復帰
  - `origin_state_kept`: 元sessionの状態不変
  - `session_ids`: 両manifestのsession IDが異なる
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 04-WINDOWS-UAT W11(準備不能)

### W11/other-session@production-exe

**W11 / 別session / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case W11).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 同上を実EXEで行う(準備不能ならnot-run)。
- **期待**: 実EXEでも各sessionに1画面。準備不能ならnot-runで出荷停止。
- **必須観測**:
  - `each_session_one_screen`: 各sessionに1画面
  - `returns_to_same_session`: 二次は同sessionへ復帰
  - `origin_state_kept`: 元sessionの状態不変
  - `session_ids`: 両manifestのsession IDが異なる
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 04-WINDOWS-UAT W11(準備不能)

## WR-01 15609ms(並行負荷)と15140ms(単独)の保持と15.5秒契約の再評価

- 組: G8 / 担当: 06-06-01
- 出典: 06-UAT-CARRYOVER WR-01 / 04-WINDOWS-UAT W07b

### WR-01/retained-15609-15140@script

**WR-01 / 元の測定値の保持と再評価 / Python直接起動(python pagefolio.py)**(証拠種別: `manual`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  (記録の確認のみ。コマンドなし)
  ```
- **利用者操作**:
  1. 実行担当: 04-05-EVIDENCE.jsonの両値を保持したまま再評価を記録する。
  2. 利用者: 再評価結果を確認して答える。
- **期待**: 元の記録を消さず再評価する。
- **必須観測**:
  - `both_values_retained`: 並行負荷15609msと単独15140msの両方を保持
  - `contract_reevaluation`: 15.5秒契約の適合性の再評価結果
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 06-UAT-CARRYOVER WR-01 / 04-WINDOWS-UAT W07b

### WR-01/rerun-same-load@module

**WR-01 / 同負荷の再計測 / Python -m pagefolio**(証拠種別: `python-real`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case preview | ConvertFrom-Json
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry module
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
  .venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
  ```
- **利用者操作**:
  1. 実行担当: 同条件の負荷で再計測を行い経過を記録する。
  2. 利用者: 条件と結果を確認して答える。
- **期待**: 15500ms以内。超過ならfailとし、debugまたは利用者の明示承認の再計画へ。
- **必須観測**:
  - `rerun_elapsed_ms`: 同負荷再計測の経過ms
  - `within_15500ms`: 15500ms以内か(超過ならfail・出荷停止。負荷縮小/期限延長で通さない)
- **失敗時の回収**: 共通の失敗時回収に従う。harnessの `stop` で所有runだけを回収する。
- **出典**: 06-UAT-CARRYOVER WR-01 / 04-WINDOWS-UAT W07b

### WR-01/exe-second-launch-elapsed@production-exe

**WR-01 / 実EXE経過 / 実配布EXE(隔離copy。最終v1.10.0)**(証拠種別: `production-exe`)

- **状態**: not-run / 準備: 未準備(別フィールド)
- **準備コマンド**(実行担当が実行。利用者はコマンドを調べない):
  ```powershell
  $run = (.venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\Temp\pf06_final_b492037015cd42c5a57d28ca0f329773\out\PageFolio-v1.10.0" --case WR-01).run  # 完全copy・hash固定
  .venv/Scripts/python.exe tests/release_uat_support.py start --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py peer --run $run     # 二次起動(必要なカードのみ)
  .venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
  .venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
  ```
- **利用者操作**:
  1. 実行担当: 実EXEで二次起動の経過を外部測定する。
  2. 利用者: 条件を確認して答える。
- **期待**: 実EXEの経過が契約内。
- **必須観測**:
  - `elapsed_ms`: 実EXEの二次起動の経過ms
  - `condition`: 単独か並行負荷かの条件
  - `foreground_after`: 画面遷移後の実foreground(許可API戻りとは別記)
- **失敗時の回収**: 共通の失敗時回収に従う。`stop` で所有PIDだけを回収する。
- **出典**: 06-UAT-CARRYOVER WR-01 / 04-WINDOWS-UAT W07b

