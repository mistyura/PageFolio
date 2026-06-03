# Phase 1: Undo/Redo 修正 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 1-Undo/Redo 修正
**Areas discussed:** BUG-02 シリアライズ排除の設計, 対称化のリファクタ範囲, deque maxlen の適用範囲, TEST-01 の検証深度

---

## BUG-02 シリアライズ排除の設計

| Option | Description | Selected |
|--------|-------------|----------|
| 逆操作デルタ方式 | Undo 実行時、redo スタックにフル PDF ではなく「逆操作のデルタ」を積む。順方向と同じデルタ仕組みで対称化し tobytes を完全排除。fitz スレッド制約も回避。 | ✓ |
| 元ファイルから順方向再適用 | undo スタックを操作ログとして保持し、状態を元ストリームから全操作再適用で再構成。クリーンだが操作数増で遅くなりうる。 | |
| 背景スレッドで tobytes | シリアライズを daemon スレッドへ退避。fitz は Document をスレッド間共有できずクラッシュリスク高。 | |

**User's choice:** 逆操作デルタ方式（推奨）
**Notes:** 順方向はすでにデルタ方式。巻き戻しパスの tobytes が非対称設計の本質という分析に同意。

---

## 対称化のリファクタ範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 全 op 完全対称化 | 全操作に redo 逆デルタを実装。insert/merge は巻き戻し時に削除ページ bytes をキャプチャ。pdf_bytes 分岐を撤廃し全パスで tobytes 排除。成功基準#3 を完全に満たす。 | ✓ |
| 共通パス+フォールバック温存 | 主要 op を逆デルタ化しつつ insert/merge は既存 pdf_bytes フォールバックを残す。段階的・低リスクだが一部 op で tobytes が残る。 | |
| あなたに任せる | researcher/planner が op ごとの逆デルタ可能性を調査し計画時に振り分け。 | |

**User's choice:** 全 op 完全対称化（推奨）
**Notes:** delete の bytes キャプチャパターンを insert/merge に流用する方針。

---

## deque maxlen の適用範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 両スタックに maxlen | undo/redo とも deque(maxlen=MAX_UNDO)。メモリ上限が明確で一貫性が高い。redo は通常 MAX_UNDO を超えず実害なし。 | ✓ |
| undo のみ maxlen | undo のみ deque(maxlen)、redo は無制限。現状に近いが上限の扱いがスタック間で不揃い。 | |

**User's choice:** 両スタックに maxlen（推奨）
**Notes:** deque(maxlen) 化で _save_undo の手動 pop(0) トリムが不要になる点を確認。

---

## TEST-01 の検証深度

| Option | Description | Selected |
|--------|-------------|----------|
| ページ数＋内容同一性 | 挿入→Undo 後に len(doc) が戻ることに加え、残ページの同一性（テキスト/ハッシュ）も検証。redo 往復も含める。 | ✓ |
| ページ数のみ | len(doc) が戻ることだけ検証。シンプルだが内容崩れを見逃す可能性。 | |
| 全 op の往復スモーク | BUG-01 だけでなく全 op の do→undo→redo 往復を検証する test 群を整備。最も厚いが工数大。 | |

**User's choice:** ページ数＋内容同一性（推奨）
**Notes:** 全 op 往復テストは deferred として planner に検討依頼（安全網）。

---

## Claude's Discretion

- 各 op の逆デルタのデータ構造・キャプチャ実装の詳細
- 内容同一性のハッシュ方式（テキスト抽出 / pixmap バイト / page bytes）の選択
- insert/merge の redo 用 bytes キャプチャのタイミング（巻き戻し直前 vs 順方向時保持）

## Deferred Ideas

- BUG-03 / REFAC-01 / REFAC-02 — Phase 2
- REFAC-04 / TEST-03 — Phase 3
- 全 op の do→undo→redo 往復スモークテスト — 対称化リファクタの安全網として planner が Phase 1 内追加を検討
