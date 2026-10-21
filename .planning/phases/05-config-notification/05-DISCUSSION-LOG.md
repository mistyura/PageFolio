# Phase 5: 設定読込・保存失敗の通知 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-22
**Phase:** 05-設定読込・保存失敗の通知
**Areas discussed:** 読込失敗の表示方法, 保存失敗の表示と文言, 既存ファイルの保護方針, 通知の集約と連打防止

---

## 読込失敗の表示方法

| Option | Description | Selected |
|--------|-------------|----------|
| 非モーダルのトースト | 画面構築後に通知。編集を止めない | ✓ |
| モーダルダイアログ（OK で閉じる） | 確実に気付くがダイアログが開いたままになる | |
| ステータスバーのみ | 目立たないが見落としやすい | |

**User's choice:** 非モーダルのトースト（Recommended）

## 読込失敗の区別（不存在 / 破損・読取不能）

| Option | Description | Selected |
|--------|-------------|----------|
| 破損と読取不能を区別（Recommended） | 不存在は無言、破損と読取不能は別文言 | ✓ |
| 区別せず1種類の文言 | 破損と読取不能を「読めなかった」で統一 | |

**User's choice:** JSON 破損と読取不能を区別（Recommended）

## 保存失敗の表示（メモリ上の値）

| Option | Description | Selected |
|--------|-------------|----------|
| メモリ上は維持し、次回起動に残らない旨を通知 | 作業を失わせない | ✓ |
| メモリ上も元に戻す | 画面と次回起動の状態が一致するが入力内容が消える | |

**User's choice:** メモリ上は維持し、次回起動に残らない旨を通知（Recommended）

## 保存失敗の表示方法

| Option | Description | Selected |
|--------|-------------|----------|
| 非モーダルトースト | 成功表示は失敗時に出さない | ✓ |
| モーダルダイアログ | 入力中の操作を妨げる可能性がある | |

**User's choice:** 非モーダルトースト（Recommended）

## 破損ファイルの扱い（読込失敗後）

| Option | Description | Selected |
|--------|-------------|----------|
| 自動保存しない。退避コピーも作らない | 元ファイルに触れない | ✓ |
| .bak に退避してから保存を許す | 利用者の内容を残すがファイルが増える | |

**User's choice:** 自動保存しない。退避コピーも作らない（Recommended）

## 破損ファイル上での明示保存

| Option | Description | Selected |
|--------|-------------|----------|
| 上書きする（利用者の操作なので許容） | 明示保存は許可 | ✓ |
| 保存を拒否して通知 | 破損中は保存不可 | |

**User's choice:** 上書きする（利用者の操作なので許容）

## 保存途中の失敗（一時ファイル）と上書き前の確認

| Option | Description | Selected |
|--------|-------------|----------|
| 失敗時に .tmp を削除し、元ファイルを維持（Recommended） | 元ファイルは完全な旧内容のまま | ✓ |
| 破損上書き前に確認ダイアログを出す | 「上書きしますか？」を一度出す | |

**User's choice:** 失敗時に .tmp を削除し、元ファイルを維持（Recommended）
**Follow-up:** 破損上書き前の確認 → 確認なしで上書き（Recommended）

## 同一エラーの通知回数（読込失敗）

| Option | Description | Selected |
|--------|-------------|----------|
| 同一種類はセッション中1回だけ表示（Recommended） | 連打を防ぐ | ✓ |
| 保存ごとに再通知（集約） | 頻度が高く見落としにくい | |

**User's choice:** 同一種類はセッション中1回だけ表示（Recommended）
**Follow-up:** 1回制限を保存失敗にも適用するか → 読込失敗のみ1回、保存失敗は毎回通知（Recommended）
（保存失敗を1回に絞ると、次回起動に残らないことを利用者が毎回認識できなくなるため）

## 画面再構築時の未消化通知

| Option | Description | Selected |
|--------|-------------|----------|
| 再構築後も未消化の通知を再表示（Recommended） | App 側で状態を保持 | ✓ |
| 再構築で消えてよい | 実装は単純だが見落としの恐れ | |

**User's choice:** 再構築後も未消化の通知を再表示（Recommended）

---

## Claude's Discretion

- トーストの表示時間・位置・見た目（既存 ToastManager の利用可否は計画で確認）
- 読込失敗種別の判定方法
- `_load_settings` / `_save_settings` の失敗を呼び出し側へ伝える API
- 通知の内部データ構造と文言キー
- 終了時のウィンドウ状態保存の抑止方式（CONTEXT.md D-14 は利用者回答からの派生決定。影響範囲は計画で確認）

## Deferred Ideas

- 破損設定ファイルの退避（.bak）・復旧機能
- 起動時ダイアログによる破損通知
- Phase 4 の保留項目（起動 PDF 引数転送、最近使ったファイル復元、異常終了後の編集復旧、外部プロンプト保存失敗通知、OCR 共通化、実 API UAT）
