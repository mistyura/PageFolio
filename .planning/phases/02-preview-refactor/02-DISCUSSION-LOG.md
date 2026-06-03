# Phase 2: プレビュー最適化とリファクタリング - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 2-プレビュー最適化とリファクタリング
**Areas discussed:** BUG-03 スレッド戦略, C 可変 dict の置き場所, TEST-02 検証手法・置き場所, 分割粒度

---

## BUG-03 スレッド戦略

| Option | Description | Selected |
|--------|-------------|----------|
| メインスレッドで同期描画 | `self.doc[page].get_pixmap()` をそのまま。スレッド廃止。SC-1・TEST-02 をクリーンに満たす | ✓ |
| 単一ページの小 bytes をスレッドへ | 1ページ抽出→小 tobytes→従来スレッド方式。一時 doc で tobytes を呼ぶため TEST-02 と衝突しうる | |
| ページ単位 pixmap キャッシュ追加 | 再表示高速化だがキャッシュ無効化管理が増えオーバースペック | |

**User's choice:** メインスレッドで同期描画
**Notes:** 1 ページ描画は全体 tobytes より遥かに軽く、fitz の Document スレッド共有不可制約（Phase 1 D-02）も回避。同期化に伴い `_preview_gen`・ローディング「...」は不要化の可能性（CONTEXT D-03 で planner 裁量に）。

---

## C 可変 dict の置き場所

| Option | Description | Selected |
|--------|-------------|----------|
| themes.py に移し constants で再エクスポート | THEMES/C を themes.py へ。C.update() の in-place 更新で識別子保持、constants 再エクスポートで既存 import 維持 | ✓ |
| C は constants.py に残し THEMES だけ分離 | リスク最小だが分割の意義が薄い | |
| 全 import を themes 直参照に書き換え | 明快だが変更面が広く後方互換検証が重い | |

**User's choice:** themes.py に移し constants で再エクスポート
**Notes:** `settings.py:95` が `C.update(THEMES[resolved])` で in-place 更新していることを確認済み。識別子が保たれるため再エクスポートで `from pagefolio.constants import C` と `C["BG_DARK"]` 全参照が動作（SC-3）。

---

## TEST-02 検証手法・置き場所

| Option | Description | Selected |
|--------|-------------|----------|
| レンダリング中核を純関数に抽出して単体テスト | `_render_preview_pixmap` 等の Tk 非依存ヘルパーに抽出し test_viewer.py で単体テスト | ✓ |
| _show_preview 全体を Tk root + monkeypatch | 抽出不要だが CI/ヘッドレスで脆い | |
| モジュールレベルで tobytes をスパイ | 抽出なしだが Tk 依存・スレッド同期の複雑さが残る | |

**User's choice:** レンダリング中核を純関数に抽出して単体テスト
**Notes:** 既存 test_pdf_ops の「UI でなくロジックをテスト」方針と整合。monkeypatch で `fitz.Document.tobytes` をスパイし未呼び出しを検証（CONTEXT D-08/D-09）。

---

## 分割粒度

| Option | Description | Selected |
|--------|-------------|----------|
| REQUIREMENTS の案どおり採用 | dialogs→about/settings/plugin/merge/llm_config の5+__init__、constants→lang/themes/constants の3分割 | ✓ |
| merge をさらに2ファイルに分割 | MergeOrder/MergeResize を別ファイルに。細かいがファイル数増 | |
| planner 裁量に任せる | 方針のみ渡す | |

**User's choice:** REQUIREMENTS の案どおり採用
**Notes:** merge.py に MergeOrderDialog/MergeResizeDialog を同居。公開 import 表面（`pagefolio/__init__.py`）は維持必須（CONTEXT D-06/D-07）。

---

## Claude's Discretion

- 純関数ヘルパーのシグネチャ・戻り値型（samples+size タプル vs PIL Image）
- `_preview_gen` / ローディングプレースホルダーの撤去可否（撤去時は波及確認必須）
- 各 dialog/constants ファイルへのシンボル割り当ての細部（import 順・`__all__`）

## Deferred Ideas

- REFAC-04 / TEST-03 — Phase 3
- サムネイル仮想化 — v2（スコープ外）
- ページ単位 pixmap キャッシュ — 将来のパフォーマンス改善候補（今回不採用）
- `_preview_gen` 世代カウンタの完全撤去 — 同期化後の整理タスク
