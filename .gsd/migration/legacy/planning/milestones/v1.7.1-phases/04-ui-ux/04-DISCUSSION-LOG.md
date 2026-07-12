# Phase 4: UI/UX 磨き込み + 既知バグ棚卸し - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 4-UI/UX 磨き込み + 既知バグ棚卸し
**Areas discussed:** ショートカット GUI の形, 文言/エラー監査の範囲, ダイアログ整理の程度, バグ棚卸しのソースと基準

---

## ショートカット GUI の形

| Option | Description | Selected |
|--------|-------------|----------|
| 専用ダイアログ（推奨） | SettingsDialog にボタン追加 → 専用ダイアログ（LLM設定ボタンと同型） | ✓ |
| SettingsDialog 内セクション | インライン一覧（縦長化リスク） | |
| Claude に任せる | planner/executor 判断 | |

**User's choice:** 専用ダイアログ

| Option | Description | Selected |
|--------|-------------|----------|
| 実キーキャプチャ（推奨） | 変更ボタン → 入力待ち → 実キー押下で取得 | ✓ |
| プルダウン選択式 | 修飾キーチェック＋キー Combobox | |
| テキスト直接入力 | `<Control-o>` 形式を直接入力 | |

**User's choice:** 実キーキャプチャ

| Option | Description | Selected |
|--------|-------------|----------|
| 全 11 コマンド（推奨） | cmd_map 全部・rotate 系は未割当表示で新規割当可 | ✓ |
| 既定 8 コマンドのみ | rotate 系は JSON のみ継続 | |

**User's choice:** 全 11 コマンド

| Option | Description | Selected |
|--------|-------------|----------|
| 保存時に拒否（推奨） | 重複がある間は保存不可・衝突コマンドをエラー表示 | ✓ |
| 警告のみで許可 | 警告表示するが保存可能 | |
| 入力時に即拒否 | キャプチャ瞬間に照合して取り消し | |

**User's choice:** 保存時に拒否

| Option | Description | Selected |
|--------|-------------|----------|
| 保存で即時反映（推奨） | unbind → 再バインド。バインド処理をメソッド化 | ✓ |
| 再起動後に反映 | 保存のみ・注記表示 | |

**User's choice:** 保存で即時反映

| Option | Description | Selected |
|--------|-------------|----------|
| 全体リセット＋個別解除（推奨） | 両導線・shortcuts は既定との差分のみ保存 | ✓ |
| 全体リセットのみ | ボタン 1 つだけ | |
| Claude に任せる | 実装時判断 | |

**User's choice:** 全体リセット＋個別解除

| Option | Description | Selected |
|--------|-------------|----------|
| 人間可読表記（推奨） | 「Ctrl+O」形式表示・内部は keysym・変換は純関数化 | ✓ |
| Tk keysym のまま | `<Control-o>` をそのまま表示 | |

**User's choice:** 人間可読表記

| Option | Description | Selected |
|--------|-------------|----------|
| 無効化可（推奨） | キーを外して「割当なし」にできる | ✓ |
| 常に何かしら割当 | 既定 8 コマンドは必ずキーを持つ | |

**User's choice:** 無効化可

---

## 文言/エラー監査の範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 削除（推奨） | 未使用キー 2 件を ja/en 両辞書から削除 | ✓ |
| 表示先を作って活用 | 本来の用途の表示箇所を実装 | |
| 個別判断 | planner が照合の上で判断 | |

**User's choice:** 削除（L-5 残 2 件）

| Option | Description | Selected |
|--------|-------------|----------|
| 全体スキャン（推奨） | lang.py 全キーの参照箇所を機械照合・一括検出 | ✓ |
| L-5 の 2 件のみ | 既知の 2 件に限定 | |

**User's choice:** 全体スキャン

| Option | Description | Selected |
|--------|-------------|----------|
| テスト常設（推奨） | test_lang_parity.py に全キー参照検査を追加（許可リスト付き） | ✓ |
| 今回限りの監査 | 一括検出・削除のみ | |

**User's choice:** テスト常設

| Option | Description | Selected |
|--------|-------------|----------|
| ハードコード文言の検出 | LANG 経由でない直書き文字列の検出と LANG キー化 | ✓ |
| messagebox 種別の使い分け | showerror/showwarning/showinfo の基準確立と修正 | ✓ |
| タイトル・文体の統一 | ダイアログタイトル表記ゆれ・文体統一 | ✓ |

**User's choice:** 3 点すべて（複数選択）
**Notes:** 監査結果の記録形式は Phase 2 前例（RESEARCH.md 照合表・項目×判定×根拠 file:line）を踏襲。

---

## ダイアログ整理の程度

| Option | Description | Selected |
|--------|-------------|----------|
| 掘り下げて解消（推奨） | ネスト適用は即確定・外側キャンセルは外側項目のみ・回帰テストで固定 | ✓ |
| 配置整理のみ | セマンティクスは現状維持・fragile は記録のみ | |

**User's choice:** 掘り下げて解消（ネスト同期 fragile）

| Option | Description | Selected |
|--------|-------------|----------|
| 共通/固有の分離明確化（推奨） | 共通設定とプロバイダ固有設定を見出し付きで再グルーピング・現行構造維持 | ✓ |
| スクロール化＋セクション整理 | Canvas スクロール導入 | |
| 軽微な整えのみ | 並び順・余白の微調整 | |

**User's choice:** 共通/固有の分離明確化（LLMConfigDialog）

| Option | Description | Selected |
|--------|-------------|----------|
| 見出し更新＋セクション再構成（推奨） | 「LM Studio (OCR)」改称・「外観」「操作」「AI・OCR」3 セクション再編 | ✓ |
| ボタン追加のみ | ショートカットボタンを足すだけ | |

**User's choice:** 見出し更新＋セクション再構成（SettingsDialog）

---

## バグ棚卸しのソースと基準

| Option | Description | Selected |
|--------|-------------|----------|
| CONCERNS.md の既知項目 | Known Bugs / Fragile Areas / Test Coverage Gaps から照合 | ✓ |
| 開発履歴/README の既知の制限 | CLAUDE.md・README の既知の制限から照合（意図された制限は除外） | ✓ |
| 新規コードスキャン | dialogs/lang/ui_builder 面を中心に新規探索 | ✓ |

**User's choice:** 3 ソースすべて（複数選択）＋ Phase 2 繰り越し 2 件（確定済み）

| Option | Description | Selected |
|--------|-------------|----------|
| 挙動バグ＋軽微な整理（推奨） | バグ修正＋デッドコード/重複解消。大型構造改善は記録のみ | ✓ |
| 挙動バグのみ | 見える不具合だけ修正 | |

**User's choice:** 挙動バグ＋軽微な整理

| Option | Description | Selected |
|--------|-------------|----------|
| 全件解消（推奨） | 活き残りリストは全件対象（量過多時のみプラン分割） | ✓ |
| 優先度選別 | P1 のみ解消・P2 は記録 | |
| リスト提示→ユーザー選別 | 計画段階で確認ゲート | |

**User's choice:** 全件解消

| Option | Description | Selected |
|--------|-------------|----------|
| テスト可能なものは必須（推奨） | ロジック検証可能な修正は回帰テスト必須・UI 目視系は手動確認記録 | ✓ |
| 全件テスト必須 | UI 系も FakeApp/モックで自動テスト | |

**User's choice:** テスト可能なものは必須

---

## Claude's Discretion

- ショートカットダイアログのレイアウト詳細・キーキャプチャ実装詳細（modifier 組み立て・Esc キャンセル等）
- keysym↔人間可読表記の変換関数の API 形状・置き場所
- 未使用キー検出テストの実装方式（AST or grep）と動的参照許可リスト
- messagebox 種別・文体の統一基準の具体内容（監査時に確定し RESEARCH.md に記録）
- ネスト同期解消の実装形（適用の即時 `_save_settings` 化 or 適用経路の分離）
- 新規コードスキャンの深さ・打ち切り判断

## Deferred Ideas

- ocr_dialog.py / ocr_providers.py の大型構造分割（CONCERNS.md Tech Debt）— 将来の保守性マイルストーン候補
- ショートカットのプロファイル切替・エクスポート/インポート — 需要があれば将来フェーズ
- MAX_UNDO 設定項目化・thumb_cache LRU 化など Performance/Scaling 項目 — 軽微バグではないため対象外（記録のみ）
