# Phase 5 — UI Review

**Audited:** 2026-10-24
**Baseline:** UI-SPECなし。抽象6-pillar基準と05-CONTEXT D-01〜D-22、05-01〜04 PLANの設定通知契約
**Screenshots:** not captured（Tkinter対象のCLI撮影手段なし。localhost:3000/5173/8080は応答なし）
**Interaction captures:** off（interaction_capture=false）
**方式:** standard code-only review。以下の点数は静的実装評価であり、独立した実画面の合格点ではない。

撮影を行っていないためcaptureディレクトリも作成していない。画像保存前のgitignore gateは未実施・撮影開始条件として維持する。Web用の375/768/1440px判定をWindows/Tkへ転用しない。`components.json`なし、registry auditは対象外。

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | 読込2種・保存失敗・保護による未保存を日英固定文で区別 |
| 2. Visuals | 3/4 | 閉鎖操作が記号だけで、説明・tooltipを持たない |
| 3. Color | 4/4 | 通知本文は既存Cテーマ参照。設定通知にaccentの追加乱用なし |
| 4. Typography | 4/4 | 通知は既存_font(-1)を使用し、設定の文字サイズへ追従 |
| 5. Spacing | 3/4 | 320px折返しと固定余白に、利用可能幅への追従処理がない |
| 6. Experience Design | 4/4 | FIFO、可視時間、再構築、modal、既存retryの分離を実装 |

**Overall: 22/24（静的評価のみ）**

4/4は対象sliceの静的監査で欠陥を検出しなかった意味。色面積60/30/10、DPI、実際の折返し、OS支援技術、見た目の階層は独立未検証で、優良な実画面の実証とはしない。

## Top 3 Priority Fixes

1. **WARNING — 閉鎖操作の意味を明示する** — `toast.py:161`の`✕`だけでは操作名の説明がない。既存の日英翻訳に合わせた閉鎖ラベルまたはtooltipを検討し、キーボードで識別・操作できることを確認する。OSの読み上げ不具合を実測したという指摘ではない。
2. **WARNING — 通知幅の境界を確認し、必要時に追従させる** — `toast.py:145`の320px固定折返しと右下16px配置にはroot幅とのクランプがない。最小対応ウィンドウ、最大設定フォント、日英、高DPIで本文と閉鎖操作を確認し、はみ出す条件ではrootの利用可能幅から折返し幅を算出する。現時点でクリッピングを目視したとはしない。
3. **未検証項目 — 出荷前の独立visual確認を残す** — H01〜H12を再実施済みと読み替えず、テーマ別の可読性・位置・重なり・フォーカス表示をPhase 6の実EXE受入と区別して記録する。これは新しいデザイン契約や本Phaseへの実装修正要求ではない。

## Detailed Findings

### Pillar 1: Copywriting（4/4）

- 適合所見: `pagefolio/lang.py:9`〜21と`:831`以降は、corrupt/unreadableの原因区別、既定値起動、設定変更が次回起動に残らないことを固定文で示す。設定値・パス・例外本文を補間しない。05-01 PLANの4キーと一致する。
- `pagefolio/app.py:672`〜683は保護による抑止と実保存失敗を別キーへ接続し、偽の保存成功通知を追加しない。PDF破棄や再起動を促す文言は検出しなかった。
- `05-UAT.md:24`以降のH01/H02は利用者による文言・編集継続確認。descriptor不明の禁止2件を解除する根拠にはしない。

### Pillar 2: Visuals（3/4）

- **WARNING V-01:** `pagefolio/toast.py:159`〜164の閉鎖ボタンは`✕`・width=2のみ。操作の説明やtooltipがなく、文脈を知らない利用者への手掛かりが弱い。既存の小さな操作なのでBLOCKERとはしない。
- `toast.py:134`〜149は既存Frameの右下overlayと左寄せ本文を維持し、設定通知はretryなし。本文と操作の構造は確認できるが、実際の視認性・画面内の焦点・下層ツールとの重なりは未検証。

### Pillar 3: Color（4/4）

- 適合所見: `toast.py:135`〜143の背景2箇所は`C["BG_CARD"]`、本文1箇所は`C["TEXT_MAIN"]`。通知frame内にhex/RGB直書きはなく、accent指定は既存retryの`Accent.TButton`1箇所（`:153`）だけ。設定通知は`retry_cb=None`なので追加accentボタン0個。
- `pagefolio/themes.py:12`〜15、`:28`〜31でdark/lightのトークンを共有する。実色面積の60/30/10、テーマごとの実レンダリングコントラストは未測定。コード出現数を色面積の実測と扱わない。

### Pillar 4: Typography（4/4）

- 適合所見: 通知本文のサイズ指定は`toast.py:144`の`app._font(-1)`1種類、追加weightなし。`app.py:765`〜770の既存helperがfont_sizeと最小7を適用する。設定通知のための固定fontサイズ・追加書体は導入していない。
- 既存settingsのフォントpreview（`dialogs/settings.py:148`、`:205`）は選択値のpreviewであり、任意のハードコードとは評価しない。既存UI全体のサイズ数をこのPhaseの通知違反として数えない。
- 拡大時の行高・読了時間は実画面未確認。幅に関する具体的な懸念はSpacingに集約する。

### Pillar 5: Spacing（3/4）

- **WARNING S-01:** `toast.py:136`は右下16px、`:145`はwraplength=320、`:147`は左右12/4px・上下8px、`:164`は閉鎖操作右8px。既存の4px倍数による一貫性はあるが、rootの利用可能幅やフォント拡大に合わせた再計算がない。
- 320px本文にボタンと余白が加算される構造。対応最小幅で必ず欠けるという証明はなく、実被害は未検証。Webのmobile対応を新規要求せず、既存Windowsの対応範囲で境界を確認する。

### Pillar 6: Experience Design（4/4）

- 適合所見: `app.py:519`〜532で読込は一度、保存失敗は各eventをFIFOで保持しremaining_ms=10000。D-21の長い待ち行列は利用者が受容した設計であり、統合・破棄を改善案として要求しない。
- `app.py:543`〜563、`:590`〜648はgrab中の保留、可視時間の減算、user/expiredだけの消化、既存Toast優先、現在言語での再表示を実装。100ms監視はコード上の周期であり、厳密に遅延ゼロとは記述しない。
- `app.py:575`〜580、`:879`〜900は再構築前のdispose/世代更新と再スケジュール。`toast.py:49`〜83、`:94`〜125はretryの有無・更新・カテゴリ一致dismiss・idleを分離する。
- `dialogs/settings.py:250`〜258、`ocr_dialog.py:1034`〜1042は内側LLM破棄時の外側grab復元。`dialogs/plugin.py:219`〜230は無変更rescanの非保存。`app.py:654`〜684は終了確認先行、初回失敗時保持、明示成功時flag解除。
- `05-UAT.md:24`〜35のH01〜H12は2026-10-24の利用者の明示回答による12 pass。監査者による独立操作・撮影は0件。H03のread-corruptの✕は未実施、H06の通知開始前の厳密境界は自動証拠、と同書の制限を保持する。
- `05-EVIDENCE.json:123`の1789 passed/1 warningとRuff/108ファイルformat/AST成功は既存証拠。追加試験を実行していない。Web UI safety gateのblock=falseはTkの実UI合格を意味しない。

## 出荷・独立検証の制約

本監査で新規の設定通知BLOCKERは実証しなかった。ただし、**出荷不可を維持**する。`05-04-SUMMARY.md:131`〜132のDEP-05・owner_missing・通知前景不一致・Tcl解放警告、`05-EVIDENCE.json:325`以降のdescriptor-less禁止2件、edge-probe4件は未解除。本スコアで原因解決・Phase正式完了・出荷承認に置換しない。別担当のNyquist/独立検証結果は本レポートから先取りしない。

## Files Audited

- AGENTS.md、`.agents/skills/session-handoff/SKILL.md`
- 05-01〜04 PLAN/SUMMARY、05-CONTEXT.md、05-UAT.md、05-EVIDENCE.json
- pagefolio/toast.py、pagefolio/app.py、pagefolio/ui_builder.py
- pagefolio/dialogs/settings.py、pagefolio/dialogs/plugin.py、pagefolio/ocr_dialog.py
- pagefolio/lang.py、pagefolio/themes.py、pagefolio/settings.py（関連トークン範囲）

**Recommendation Count:** 優先事項3（うちコード品質WARNING2、独立確認1）。追加の軽微推奨0。実装・テスト・共有文書は変更せず、commitは親担当。
