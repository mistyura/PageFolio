---
phase: 04-startup-control
reviewed: 2026-10-22
status: partial
baseline: abstract-six-pillars
visual_capture: not-run
overall_score: null
deferred_to: 06-release-validation
---

# Phase 4 UI監査

UI-SPECは存在しない。現行ui-review.mdはその場合に抽象6柱で監査するため、静的確認を実施した。Tk/native通知の実表示を本監査では起動していない。未観測の視覚品質に点数を付けない。最終実表示判定は承認済み06-UAT-CARRYOVERへ移管する。04-06後に独立通知経路をコードと実subprocess試験で再監査し、旧経路と同じ描画処理へ接続することを確認した。

| 柱 | 静的根拠 | 実表示判定 |
|---|---|---|
| Copywriting | lang.pyの判定不能/通信失敗/5秒応答待ちを分離。04-06の構築失敗は固定の判定不能文言へ接続し、例外本文を見せない | W09/10へ移管 |
| Visuals | native窓1件、正常復帰では追加通知なし | 未観測 |
| Color | OSのCOLOR_WINDOWとDrawFrameControlを使用 | コントラスト未観測 |
| Typography | NONCLIENTMETRICS/lfMessageFont、SystemParametersInfoForDpiを使用 | 100/150/200% DPIは未観測 |
| Spacing | dpi/96による16px margin、実文字計測で本文/閉じる領域を配置 | 切れ/クリック領域はW09へ移管 |
| Experience Design | 独立通知も同じNOACTIVATE、固定10秒、原因別集約へ到達する。新subprocess試験は表示・手動閉鎖前後のforeground HWND同一性をassert | 実入力/実クリック/OS拒否はW01〜12へ移管 |

根拠: pagefolio/startup_notice.py、pagefolio/startup_win32.py:1498〜1872、pagefolio/startup_focus.py、tests/test_startup_windows.py:280〜354。今回のconstructor/初期化/期限の名前付き25件は合格したが、native実表示のスクリーンショット・100/150/200% DPI・実クリックは未実施。A3旧primitiveの実測を新NoticeLeaseの最終視覚受入の代替にはしない。コード上の新しい製品欠陥は検出していない。UI hookは同一担当が再委任なしでインライン実施、visual captureのみnot-run。
