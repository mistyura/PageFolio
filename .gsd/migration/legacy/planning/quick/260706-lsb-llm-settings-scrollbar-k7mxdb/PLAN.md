---
quick_id: 260706-lsb
slug: llm-settings-scrollbar-k7mxdb
date: 2026-07-06
type: quick
mode: quick
status: complete
---

# Plan: LLM 設定ダイアログのスクロール対応・リサイズ許可（v1.7.2）

> 実装は同日完了 — 実施結果は [SUMMARY.md](./SUMMARY.md) を参照。

## 背景

ユーザー報告: 「PCによって、LLM設定画面が入らない。スクロールバーをつける＆画面の大きさを変えられるようにして。」

`LLMConfigDialog`（`pagefolio/dialogs/llm_config.py`）は `resizable(False, False)` で固定サイズかつ、
ダイアログ高さを常に本文の必要高さ（`winfo_reqheight()`）に合わせて再計算していた。低解像度ディスプレイや
大きめのフォントサイズ設定、複数のプロバイダ固有欄が展開された状態では、本文が画面の物理的な高さを
超えてしまい、Apply/Cancel ボタンをはじめ下部の項目に到達できなくなる不具合があった。

## 対応方針

1. **スクロール可能化**: 本文全体を `tk.Canvas` + `ttk.Scrollbar`（縦）で構築し直し、内容が画面に収まらない
   場合でもスクロールでアクセスできるようにする。マウスホイール（Windows: `<MouseWheel>`、X11:
   `<Button-4>`/`<Button-5>`）にも対応する。
2. **リサイズ許可**: `resizable(True, True)` に変更し、ユーザーが手動でウィンドウサイズを調整できるようにする
   （`minsize` で最小サイズを保証）。
3. **高さのクランプ**: ダイアログの高さは「本文＋ボタン行の必要高さ」と「画面の高さ − 余白」を比較し、
   小さい方を採用する。画面をはみ出す場合はスクロールバー経由でアクセスする。
4. **ボタン行の固定表示**: Apply/Cancel ボタン（`self._btn_row`）はスクロール領域の外に置き、
   `pack(side="bottom")` で常に画面内の下部に固定表示させる。pack はパック順に空間を割り当てるため、
   ボタン行を先にパックしてから残りをスクロール領域に割り当てる構成にする。
5. プロバイダ/モデル切替時の高さ再計算（`_resize_to_fit`）も同じクランプ処理を使うように統一する。

## 想定される変更ファイル

- `pagefolio/dialogs/llm_config.py`（本体）
- `pagefolio/constants.py`（`APP_VERSION`）
- `README.md`（バージョンバッジ）
- `開発履歴.md`（変更履歴追記）

## 検証方法

- `ruff check . && ruff format .` / `pytest` 全件グリーン。
- headless（Xvfb）環境で `LLMConfigDialog` を実際に構築し、`geometry()` の計算結果・
  スクロール領域の `winfo_ismapped()` を確認する自動チェックスクリプトで検証する
  （実機の GUI 目視確認は環境上できないため代替手段とする）。
- 画面高さを小さく設定したケース（例: 400px）でダイアログ高さが画面内にクランプされ、
  スクロールバーが機能することを確認する。
