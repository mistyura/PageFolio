---
phase: 04-startup-control
reviewed: 2026-10-22
status: partial
baseline: abstract-six-pillars
visual_capture: not-run
overall_score: null
deferred_to: 06-release-validation
---

## 2026-11-06 CR-02修正後の静的所見継承（現行）

Nyquist/Security後、採用判断の厳密化は検証helper/試験だけで製品UIに変更がないことを確認した。新2361件は自動回帰の証拠であり、6柱の既存静的所見のみ継承する。partial/visual_capture not-run/score null、実EXE/DPI/UAC等の未観測を維持する。

## 2026-11-06 試験時序修正後の静的UI再照合（履歴）

Nyquist/Security後に既存の抽象6柱を確認した。製品コード・文言・描画・配置は前回v3全件入力から不変なので既存静的所見を再利用する。試験のpopup出現待機は表示判定の偽陽性を防ぐが、実画面の視認性・DPI・UAC・EXEを検証したことにはならない。新全件2333件成功を自動回帰証拠とし、partial / visual_capture not-run / score nullを維持する。`04-REVALIDATION-20261106.md` 参照。

## 2026-11-05 W05c計測後の静的UI再照合

製品の文言・配置・通知描画は前回covered入力から不変。今回の試験計測は正式人手Noの観測点を増やすが、利用者のクリックや表示結果を代行しない。native全件2293件/167一意入力一致は自動回帰の証拠として使い、実画面capture、DPI100/150/200%、UAC、別session、実EXEは未実施のため`status: partial`/`visual_capture: not-run`/score nullを維持する。`04-REVALIDATION-W05C-20261105.md`参照。

## 2026-11-05 現行入力のUI再監査

UI-SPECなしの抽象6柱について、製品の文言・描画・NOACTIVATE実装と現行Windows試験の監査接続を静的に再照合した。合成fixtureの自動回帰30件を含む全件2254 passedは操作継続の自動証拠だが、実画面capture・利用者クリック・DPI100/150/200%・UAC/別session・配布EXEの視覚判定ではない。`status: partial` / `visual_capture: not-run` / `overall_score: null`を維持し、Phase06のW受入へ引き継ぐ。根拠は `04-REVALIDATION-20261105.md` とその生証拠。

# Phase 4 UI監査

## 2026-10-28 品質停止解除後の再監査（最新）

UI-SPECなしの抽象6柱を適用した。旧入力とのhash照合で製品の文言・色・書体・配置・通知描画処理が不変のため、下表のCopywriting/Visuals/Color/Typography/Spacingの静的所見を維持する。Experience Designは追加の通知API監査と9process試験を読解し、NOACTIVATE/表示・閉鎖/期限/集約に加え、禁止要求・一時的前景化・要求元未確定切替・監査欠落を不合格にすることを確認した。

最新2071件の単一全件（`.planning/debug/quality-gate-unblock-20261028/{full.json,full.xml,full-0.stdout.txt}`、Python137/137一致）と実接続/9process各1件の成功を再利用し、GUI起動・再走をしていない。実表示capture・実クリック・DPI100/150/200%・別権限/session/EXEの受入はnot-run、総合点null、status partialを維持する。新たな静的UI欠陥は検出していないが、未観測の視覚品質を合格へ上げない。承認済み `06-UAT-CARRYOVER.md` のW人手項目で継続し、UI hookはadvisoryの部分判定として独立verifierへ渡す。hashと再利用範囲は `04-GATES-CURRENT-20261028.md` / `.json` を参照。

## 2026-10-28 前回入力の再監査（履歴）

抽象6柱の静的監査を現行コードへ適用した。新しいwakeはUI部品・文言・色・書体・余白を変更しないため、Copywriting、Visuals、Color、Typography、Spacingの既存判定を維持する。Experience Designでは `pagefolio/startup_wake.py` と `pagefolio/__main__.py` の起動・終了順を読み、Tk待機解除が前面操作を呼ばずroot破棄前に停止することを確認した。`tests/test_startup_wake.py` の正負対照と実Tcl子プロセス3条件は、同一118入力の全件合格証拠（`.planning/debug/startup-wake-foreground-evidence/full-native-after-state/{run.json,pytest.txt}`）に含まれる。試験は再走していない。

実画面の視覚取得、実クリック、100/150/200% DPI、別権限の操作感は今回も未実施。総合点は付けず `status: partial` / `visual_capture: not-run` を維持し、UIゲートの未完部分は `06-UAT-CARRYOVER.md` のW項目へ引き継ぐ。これはUIゲートの部分判定であり、Nyquist・Securityの結果やPhase正式完了を代替しない。

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

## 2026-11-06 constructor同期修正後の再照合

試験同期のみの修正で製品UI変更なし。既存静的partialを再利用、追加captureなし・score nullのまま。G3旧Python受入は来歴監査で現行入力へ再利用不可となり、旧pass保存/現行not-runへ分離する。実EXEの人手観察を静的UIレビューや全件品質の代わりにしない。


## 2026-11-07 G4採取基盤変更後の差分照合

`04-REVALIDATION-G4-20261107.md` と `../04-startup-control/04-QUALITY-G4-20261107.json` を参照。単一全件2481 passed/2 warnings、174入力と追加12入力不変、Ruff/format/AST成功。変更は採取試験基盤と証拠/文書のみで、製品の実装・表示・版番号・固定EXEは不変。G4レビュー7指摘を解消。既存の静的評価と未解除リスクを維持し、正式人手受入・UI capture・出荷承認へ転用しない。独立verificationは後続で現行fingerprintを照合する。
