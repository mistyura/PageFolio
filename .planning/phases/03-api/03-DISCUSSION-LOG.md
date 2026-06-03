# Phase 3: API 整理と回帰テスト - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 3-API 整理と回帰テスト
**Areas discussed:** REFAC-04 のスコープ範囲, setter の挙動・検証, TEST-03 の網羅・手法, テストファイル配置

---

## REFAC-04 のスコープ範囲（write のみ vs write+read）

| Option | Description | Selected |
|--------|-------------|----------|
| 完全化（write＋read） | app.py の write を setter 経由化し、dialogs の `from settings import _current_font_size` reader も getter 経由化。DEBT-04 全面解消＋import-time stale binding 修正。軽微な挙動変化を伴う。 | ✓ |
| 最小（write のみ） | app.py の直接代入のみ setter 化。ROADMAP SC-1 は満たすが dialogs の private import と stale binding が残る。挙動変化ゼロ。 | |

**User's choice:** 完全化（write＋read）
**Notes:** スカウトで判明した「dialogs が import 時に int 12 を束縛して app の書き換えを反映しない stale binding」を修正する意図を含む。dialogs のフォントサイズが実行時の最新値になる軽微な挙動変化を許容。

---

## setter の挙動・検証

| Option | Description | Selected |
|--------|-------------|----------|
| 単純代入のみ | グローバル変数をそのまま書き換えるだけ。既存挙動を完全維持。リスク最小。 | ✓ |
| クランプ検証追加 | 8〜16 等にクランプしてから代入。不正値防御になるが font_size と settings デフォルト 12 の不整合を動かしうる挙動変化を伴う。 | |

**User's choice:** 単純代入のみ
**Notes:** REFAC は挙動を変えない原則を優先。クランプはスコープ外（必要なら別タスク）。

---

## TEST-03 の網羅・手法

| Option | Description | Selected |
|--------|-------------|----------|
| 明示 import 文＋シンボル assert | 後方互換サーフェスを実 import 文として書き下し、シンボル存在を assert。壊れた箇所が一目瞭然。 | ✓ |
| importlib パラメータ化 | モジュール名・シンボル名リストを parametrize で回し動的 import＋getattr。網羅性は高いが壊れ箇所がやや抽象的。 | |

**User's choice:** 明示 import 文＋シンボル assert
**Notes:** 網羅対象は __init__ 公開サーフェス・dialogs サブパッケージ・新 lang/themes・新 setter/getter。dialogs は import のみ（インスタンス化なし）で Tk 依存を回避。

---

## import 回帰テストの配置

| Option | Description | Selected |
|--------|-------------|----------|
| 新規 tests/test_imports.py | TEST-03 を 1 ファイルに集約。責務明確で後方互換検証が一処にまとまる。 | ✓ |
| 既存ファイルに分散 | REQUIREMENTS の「tests/ 各ファイル」記述に沿うが網羅が分散し見通しが悪い。 | |

**User's choice:** 新規 tests/test_imports.py

---

## Claude's Discretion

- getter の正確な名前（`get_current_font_size()` 等）と `pagefolio/__init__.py` 公開サーフェスへの setter/getter 追加可否（既存パターンに倣い追加推奨）。
- `test_imports.py` のテスト関数分割粒度・assert の具体形。
- 実装順序（REFAC-04 → その新 import パスを TEST-03 に含める）。

## Deferred Ideas

- setter のバリデーション（クランプ）— 今回不採用。必要なら別タスク。
- 他の private モジュール状態（`themes.C` 等）の API 化 — スコープ外。
- サムネイル仮想化・暗号化 PDF・印刷・OCR 拡張 — v2。
