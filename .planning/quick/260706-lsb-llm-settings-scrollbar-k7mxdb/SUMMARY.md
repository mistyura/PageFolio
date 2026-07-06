---
quick_id: 260706-lsb
slug: llm-settings-scrollbar-k7mxdb
date: 2026-07-06
status: complete
---

# Summary: LLM 設定ダイアログのスクロール対応・リサイズ許可（v1.7.2）

ブランチ: `claude/llm-settings-scrollbar-k7mxdb`
コミット: `f059e8c`（スクロール対応・リサイズ許可）/ `039d8eb`（APIキー表示切替ボタンの追加修正）
— いずれも push 済み
品質確認: `ruff check` / `ruff format` クリーン / `pytest` **859 件パス**
（実行環境に tkinter 3.11 が無く、`python3.12` の venv で pytest を実行）

[PLAN.md](./PLAN.md) の方針どおりに実装した。プランからの逸脱は、実装直後のユーザー
フィードバックで判明した「APIキー入力欄の表示切替ボタンが狭いウィンドウ幅で潰れる」
追加不具合の修正（`039d8eb`）のみ。

## 実施内容

### コミット `f059e8c`: スクロール対応・リサイズ許可

- **`_build_scrollable_area()` 新設**: 本文を `tk.Canvas` + `ttk.Scrollbar`（縦）で
  構築。`canvas.create_window` で埋め込んだ本文 Frame（`self._body`）の `<Configure>`
  で `scrollregion` を更新し、Canvas 側の `<Configure>` で本文の幅を Canvas 幅に追従
  させる。マウスホイール（`<MouseWheel>` / X11 `<Button-4>`・`<Button-5>`）は Canvas
  にカーソルが乗っている間だけ `bind_all` する方式（`<Enter>`/`<Leave>` で bind/unbind）
  で、他ウィジェットへの副作用を避けた。
- **リサイズ許可**: `resizable(False, False)` → `resizable(True, True)` +
  `minsize(420, 320)`。
- **`_compute_dialog_height()` 新設**: 「本文＋ボタン行の必要高さ」と「画面の高さ −
  100px」を比較し、小さい方を採用してダイアログ高さを画面内にクランプする。初期表示
  （`__init__`）と `_resize_to_fit`（プロバイダ/モデル切替時）の両方から呼ぶ形に統一。
- **ボタン行の下部固定**: `self._btn_row` を本文構築より先に `pack(side="bottom")`
  することで、pack のパック順による空間割り当てを利用し、スクロール領域
  （`fill="both", expand=True`）が残りの空間を使う一方でボタン行は常に画面内下部に
  表示される構成にした。
- 本文内の全ウィジェットの親を `self`（Toplevel 直下）から `self._body`
  （スクロール領域内の Frame）へ付け替え。
- `APP_VERSION` を `v1.7.1` → `v1.7.2` へ更新。README バッジ・開発履歴.md に追記。

### コミット `039d8eb`: APIキー表示切替ボタンの追加修正（H-7）

- 上記対応後、ウィンドウを狭くリサイズすると Claude/Gemini/RunPod の APIキー入力欄
  横の表示切替ボタン（👁）が潰れて見えなくなる不具合が判明。
- **原因**: 各キー行は `Label → Entry(fill="x", expand=True) → Button` の順で
  `side="left"` に pack していた。Tkinter の pack は幅不足時、後からパックされた
  ウィジェットほど優先的に切り詰められる仕様のため、先に expand で幅を確保する
  Entry の後にパックされるボタンがしわ寄せを受けて縮んでいた。
- **対応**: 3 箇所すべてのキー行で、ボタンを `pack(side="right")` で Entry より
  先にパックするよう変更。ボタンは常に必要幅（実測 47px）を確保し、幅が足りない
  場合は Entry 側のみが縮むようになった。

## 検証内容（headless / Xvfb 環境での自動チェック）

- `LLMConfigDialog` を実際に構築し `geometry()` を計測: 通常時 `540x595` 相当・
  画面高さ 400px の疑似環境では `540x320`（画面高 − 100 にクランプ）へ収まり、
  Canvas（スクロール領域）が `winfo_ismapped()` で表示されることを確認。
- ウィンドウ幅を 540 / 420 / 300px に変えて APIキー行のレイアウトを計測し、
  表示切替ボタンが常に 47px 幅を維持し、Entry 側のみが縮むことを確認
  （300px 指定時は `minsize` により 420px にクランプされることも確認）。
- `pytest` 859 件・`ruff check`/`ruff format` グリーン。

## 注意点・潜在リスク

- **GUI 実機確認は未実施**（headless 環境のため）。実際の Windows 環境（低解像度・
  高 DPI 設定）でのスクロールバー操作感・マウスホイール挙動・手動リサイズ時の
  見た目は次回確認が必要。
- `_resize_to_fit` はプロバイダ/モデル切替の都度呼ばれるため、手動リサイズ直後に
  幅は維持されるが高さは再計算される（意図した挙動だが、体感上「勝手に高さが
  変わる」と感じられる可能性はある）。
- main へのマージ・タグ・GitHub Release・PyInstaller リビルドは未実施（次セッション）。

## 実行推奨コマンド

```
ruff check . && ruff format .
pytest
```
