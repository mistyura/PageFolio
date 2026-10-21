# Project Research Summary

**Project:** PageFolio v1.10.0 多重起動防止・起動操作の改善
**Domain:** Windows 11 向け Python/Tkinter PDF エディタの起動・設定・配布品質
**Researched:** 2026-10-21
**Confidence:** MEDIUM

## Executive Summary

PageFolio は未保存の PDF 編集と OCR 処理を保持するデスクトップアプリである。今回の4要件は、同一 Windows ログインセッションでの多重起動防止、2回目の起動時に既存画面へ戻すこと、設定の読込・保存失敗の通知、再ビルド可能なサンプルプロンプト同梱である。起動時 PDF 引数の転送、前回文書の復元、OCR 共通化、実 API UAT は含めない。

起動の共通入口で Tk 生成前に固定名の `Local\` 名前付き mutex を取得し、後続起動は別名の event で既存画面へ復帰要求だけを送る構成を推奨する。一次側は Tk メインスレッドの `root.after()` で通知を確認し、最小化を解除して前面化を試みる。設定 I/O は成否を UI へ伝え、初回のファイル不存在と読込失敗を区別する。配布サンプルの正本は `dist` から独立してソース管理し、ビルド後の内容一致を検証する。

最大のリスクは、起動判定の失敗で二窓を許すこと、読込失敗後の既定値保存で元の設定を壊すこと、`--noconfirm` の再ビルドで唯一のサンプルを消すことである。失敗時は重複起動させず理由を通知し、設定原本とユーザー編集ファイルを保護する。旧版のうち本機構を搭載しない EXE との相互排他は実現できず、Windows が前面化を拒否する場合もある。この2点は採用済み要件の黙った縮小にせず、要件確定時に保証範囲と代替の視覚通知を明示して確認する。Windows 実機と配布 EXE による検証は未実施である。

## Key Findings

### Recommended Stack

新しい pip 依存を増やさず、既存の Python/Tkinter と Windows API を使う。[STACK.md](STACK.md) は公式仕様を照合しているが、PageFolio の実機統合は未検証である。

**Core technologies:**

- `ctypes.WinDLL` / `ctypes.wintypes`: 64-bit 対応の型宣言と `use_last_error=True` により Win32 API を Python/EXE 共通で呼ぶ。
- `CreateMutexW` / `CloseHandle`: `Local\` の固定製品 ID で同一セッションの所有者を決め、GUI 存続中ハンドルを保持する。版・配置・実行形態を識別名に含めない。
- `CreateEventW` / `OpenEventW` / `SetEvent`: 別名の auto-reset event で二次起動から復帰要求を送る。初期化中の公開遅れには有限回の再試行が必要。
- `WaitForSingleObject(event, 0)` と Tk `root.after()`: 前者の `0` は Win32 の非ブロッキング待機時間であり、後者の監視周期（設計例 100～250 ms）とは別である。UI 操作は Tk メインスレッドで行う。
- `ShowWindow(SW_RESTORE)` / `SetForegroundWindow`: 復元と前面化の試行に用いるが、OS による前面化拒否を考慮する。
- JSON `.tmp` 書込と `os.replace`、PyInstaller onedir: 既存の原子的保存・配布形式を維持し、保存結果と同梱結果を検査する。

### Expected Features

[FEATURES.md](FEATURES.md) の table stakes は4項目すべて採用済みである。

**Must have (v1.10.0):**

- 同一ログインセッションの1画面制限。連続・同時起動、対応版同士の別版・別配置・Python/EXE 混在、正常・強制終了後の再起動を確認する。
- 二次起動時は既存画面を復元して前面化を試み、未保存編集・Undo/Redo・OCR・モーダル操作を維持する。拒否時には利用者が気付ける表示が必要。
- 設定読込・保存の実際の失敗を通知する。初回の設定ファイル不存在は正常とし、連続失敗の通知を集約する。
- 2種のサンプルプロンプトをソース正本から再生成し、配布 EXE で参照可能にする。ユーザーの編集用プロンプトと設定は上書きしない。

**Should have (受入品質):** 判定・通信失敗の理由表示、64-bit API 型検証、前面化拒否時の視覚的手掛かり、配布サンプルのハッシュ照合。

**Defer (次版以降):** 起動 PDF 引数の引継ぎ、最近のファイル・閲覧位置復元、異常終了後の編集復旧。OCR 共通化、他の技術的負債の一括解消、実 API UAT も今回の対象外。

### Architecture Approach

[ARCHITECTURE.md](ARCHITECTURE.md) に従い、起動調停、設定 I/O、UI 通知、配布工程を責務で分ける。起動経路を `pagefolio.__main__.main()` に集約したまま、Tk 生成前の判定を追加する。後続起動では `PDFEditorApp` を作らない。

**Major components:**

1. `pagefolio/__main__.py` と新しい調停モジュール — 排他取得、二次起動の送信・終了、ハンドルの `finally` 解放。OS 資源を扱う層は UI/PDF を import しない。
2. `pagefolio/app.py` と Tk UI — 受信要求をメインスレッドで処理し、既存画面と作業状態を保持する。UI 準備後に起動時の設定診断を一度表示する。
3. `pagefolio/settings.py` と保存呼出し元 — ファイル不存在、読込失敗、保存失敗を区別した結果を返し、原本保護・機密キー非永続化・原子的置換を維持する。
4. ソース側サンプル正本とビルド工程 — 2ファイルを onedir 配布物へコピーし、存在・内容一致を検査する。編集用ファイルと設定をビルド対象から分ける。

### Critical Pitfalls

[PITFALLS.md](PITFALLS.md) の優先リスクを以下に集約する。

1. **排他判定前の Tk 生成、または API 失敗時の二重起動** — 最初に原子的に判定し、失敗は「既存あり」と区別して通知して停止する。ハンドルは終了確認キャンセル中も保持する。
2. **復帰要求の消失と前面化の誤保証** — event 公開レースを有限再試行で扱い、UI 準備後に Tk スレッドで処理する。OS 拒否時の代替表示を検証する。
3. **非対応旧版まで相互排他を保証したと誤認** — 対応版同士の保証と旧版併用の限界を要件・配布文面で明示する。
4. **設定エラーの隠蔽と原本破壊** — 初回不存在を除き可視通知し、読込失敗後の既定値自動保存で原本を置換しない。保存失敗時に成功表示を出さず、キー値を漏らさない。
5. **通知消失・連打とサンプル原本消失** — UI 構築後の通知と既存トーストとの競合を設計し、サンプルを `dist` から独立させてから `--noconfirm` ビルドを行う。

## Implications for Roadmap

前マイルストーンの最終 Phase 3 に続けて、次の3フェーズを推奨する。4件の採用要件をすべて含み、各フェーズで観測可能な受入条件を持たせる。

### Phase 4: 起動制御と既存画面への復帰

**Rationale:** 既存画面への復帰は所有者判定と通信に依存するため、同じフェーズで入口から UI まで検証する。
**Delivers:** Tk 生成前のセッション単位排他、別版・別配置・Python/EXE 対応版で共通の識別と通信、復帰要求の受信、正常・強制終了後の再起動、判定失敗の通知。
**Addresses:** 多重起動防止、既存画面の復元・前面化試行、未保存編集・OCR・モーダル状態保護。
**Avoids:** 二窓、初期化レース、ハンドルリーク、前面化の誤保証、非対応旧版への保証拡大。
**Research flag:** Windows 11 実機スパイクが必要。権限差、起動レース、前面化拒否と代替表示、64-bit ハンドル、配布 EXE の結合を計画時に詰める。

### Phase 5: 設定読込・保存失敗の通知

**Rationale:** 起動制御とは独立だが、起動時通知の UI 順序と複数保存経路の整理を一つの品質ゲートとして扱う。
**Delivers:** 設定 I/O の結果伝達、読込失敗時の原本保護、UI 完成後の一度限りの警告、保存失敗の集約通知、成功表示との整合。
**Addresses:** 読込・保存失敗の可視化、初回不存在の正常扱い、機密キー非永続化。
**Avoids:** 破損設定の上書き、連続モーダル、既存保存/印刷トーストの置換、失敗時の誤った成功表示。
**Research flag:** JSON 保存・失敗注入は標準パターンで追加調査を省ける。原本退避後に再保存を許す操作と `save_prompt_file()` の範囲は要件確定が必要。

### Phase 6: サンプル配布とリリース検証

**Rationale:** 原本保全とビルド工程を整えた後、完成した起動制御・設定通知を実際の onedir EXE で統合検証する。
**Delivers:** 2サンプルのソース正本、再現可能なビルド・コピー工程、クリーンビルドと再ビルドのハッシュ照合、ユーザーファイル保護、配布 EXE の起動確認。
**Addresses:** 再ビルド時のサンプル原本保持・同梱、Python/EXE 混在と通知のリリース検証。
**Avoids:** `--noconfirm` による唯一の原本消失、編集済みプロンプト・設定の消去、コードだけで配布動作を保証したとみなすこと。
**Research flag:** PyInstaller の基本パターンは資料化済み。実ビルド環境で成果物の配置・ハッシュ・起動を検証する必要がある。

### Phase Ordering Rationale

- 起動判定と復帰通知は一体のユーザー操作であり、片方だけでは「2回目の起動で作業へ戻る」を満たさない。
- 設定通知は複数の UI 保存経路を横断するため独立したフェーズにし、読込失敗後の原本保護を受入条件に含める。
- 最後に配布物で起動・設定通知・サンプルを統合確認し、バージョン・README・開発履歴の同期をリリースゲートで行う。

### Research Flags

**Deeper research / validation:** Phase 4 は Windows 実機で起動・IPC・前面化の結合検証が必要。Phase 6 は実際の PyInstaller onedir 再ビルドと EXE UAT が必要。追加の一般調査より実機検証を優先する。
**Standard patterns:** Phase 5 の JSON 結果 API と失敗注入、Phase 6 のハッシュ検査は既存資料と標準的な手法で計画可能。いずれも新機能の合格をコード読取だけで判定しない。

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Microsoft・Python 公式仕様を照合。PageFolio の権限混在・EXE 結合は未検証。 |
| Features | HIGH（範囲）/ MEDIUM（受入） | 採用4項目は PROJECT.md に確定。Windows での観測結果は提案段階。 |
| Architecture | MEDIUM | 現行コードの境界・保存呼出し・配布ファイルを直接確認。新しい統合方式は未実装。 |
| Pitfalls | MEDIUM | 現行コードとテストの欠落は確認済み。予防策は失敗注入・実機で要検証。 |

**Overall confidence:** MEDIUM

### Gaps to Address

- **保証範囲の確認:** 排他未実装の旧版 EXE は相互排他に参加できない。採用済み「別版」要件をどう表記するか、対応版同士の保証と旧版併用の扱いをユーザーと確認する。
- **前面化の受入:** OS が `SetForegroundWindow` を拒否する場合のタスクバー等の視覚通知と合格条件を確定する。無条件の前面化成功は保証できない。
- **設定復旧契約:** 読込失敗した原本をいつ・どの明示操作で退避または再保存可能にするか、`save_prompt_file()` の失敗を設定通知に含めるかを定める。
- **実機・配布検証:** Windows 11 で権限差、別セッション、モーダル/OCR 中、強制終了、実 EXE、2回目のビルドを確認する。現在の研究4資料はソース・文書と公式仕様の調査であり、この検証は未実施。

## Sources

### Primary (HIGH confidence)

- [PROJECT.md](../PROJECT.md) — 採用済み4項目、除外範囲、Phase 4 からの採番。
- [STACK.md](STACK.md)、[FEATURES.md](FEATURES.md)、[ARCHITECTURE.md](ARCHITECTURE.md)、[PITFALLS.md](PITFALLS.md) — 2026-10-21 の4調査。
- 現行リポジトリ: `pagefolio/__main__.py`、`pagefolio/app.py`、`pagefolio/settings.py`、`pagefolio/toast.py`、`docs/DEVELOPMENT.md`、配布中の2サンプル。責務と未実装状態の根拠。
- [Microsoft CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw)、[Kernel object namespaces](https://learn.microsoft.com/en-us/windows/win32/termserv/kernel-object-namespaces)、[SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow)、[Python ctypes](https://docs.python.org/3/library/ctypes.html) — API の仕様と制限。研究資料中の参照先も参照。

### Secondary (MEDIUM confidence)

- [引継ぎノート](../notes/GSD_HANDOFF_2026-10-21.md) — 当初の問題と受入観点。現行コード・公式仕様と突き合わせて使用。
- `docs/DEVELOPMENT.md` の手動 PyInstaller 手順と過去リリース記録 — 原本消失の経緯。新しい再ビルド工程の実動作は未検証。

### Tertiary (LOW confidence)

- `root.after()` の具体的な監視周期、前面化拒否時の最適な代替表示、設定復旧の UI は設計案であり、フェーズ計画と実機 UAT で確定する。

---
*Research completed: 2026-10-21*
*Ready for roadmap: yes — 保証範囲と前面化受入の確認事項を明示して進める*
