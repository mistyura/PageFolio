# Phase 1: コード品質改善とレスポンシブ UI - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

バグ修正（レイアウト関連中心）とレイアウトの完全レスポンシブ化。右パネルの見切れ解消、全3ペインを PanedWindow で分割、各パネルの最小幅保証。既存機能の動作維持が必須。

</domain>

<decisions>
## Implementation Decisions

### レイアウト構成
- 3ペイン構成: サムネイル | プレビュー | ツールを全て PanedWindow で分割
- 現在の左中 PanedWindow + 右固定 Frame を、3ペイン PanedWindow に再構築
- ヘッダー（「✦ PageFolio」+ ステータス）は現状維持（pack(fill="x") で問題なし）
- ウィンドウ最小サイズ: 800x600 を `root.minsize()` で設定

### パネルサイズ
- サムネイルパネル最小幅: 150px（現状維持）
- プレビューパネル最小幅: 300px（現状維持）
- ツールパネル最小幅: 220px（現在の固定260pxから縮小可能に）
- デフォルト比率: 20:50:30（サムネイル:プレビュー:ツール）

### バグ修正
- 既知のバグは特になし — コードレビューで Claude が探して修正
- レビュー範囲はレイアウト関連（_build_ui 周辺）を中心に
- レイアウト再構築と同時に修正できるバグを優先

### リビルド挙動
- _rebuild_ui() でパネル比率がデフォルトにリセットされるのは許容
- パネル比率は設定ファイルに保存しない（セッション内のみ）
- テーマ切替・フォント変更は頻繁ではないので、リセットで問題なし

### Claude's Discretion
- sash（ドラッグ境界線）のスタイル（色・幅）
- PanedWindow の opaqueresize 設定
- 右ペイン内部のスクロール Canvas 構成の調整方法
- レイアウト関連以外のバグ修正の優先判断

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### プロジェクト構成
- `CLAUDE.md` — コーディング規約、クラス構成、状態管理ルール、再描画ルール
- `.planning/PROJECT.md` — 制約条件（単一ファイル構成、tech stack）
- `.planning/REQUIREMENTS.md` — UI-01, UI-02, UI-03, QUAL-01 の受け入れ基準

### 既存コード
- `pagefolio.py` L720-755 — 現在の `_build_ui()` レイアウト構成（PanedWindow + 右固定パネル）
- `pagefolio.py` L846-884 — `_build_tools_scrollable()` 右ペイン Canvas スクロール構成
- `pagefolio.py` L758-793 — `_build_thumb_panel()` サムネイルパネル構成

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_build_tools_scrollable()`: 右ペインの Canvas ベーススクロール構成 — 3ペイン化後もそのまま流用可能
- `_build_thumb_panel()`: サムネイルパネル構成 — Canvas + Scrollbar で完成済み
- `_build_preview()`: プレビュー Canvas — crop ドラッグバインド含む、構成変更不要
- `_font()` ヘルパー: フォントサイズ計算 — レイアウト幅計算にも使用中

### Established Patterns
- レイアウトは `pack()` ベース（header は pack、main は pack、パネル内も pack）
- 左中は既に `tk.PanedWindow(orient="horizontal")` で分割済み
- 右パネルは `pack(side="right", fill="y")` + `pack_propagate(False)` で固定幅
- テーマ色は `C["KEY"]` 辞書経由で参照
- UI 再構築は `_rebuild_ui()` で全ウィジェット destroy → 再構築

### Integration Points
- `_build_ui()` が全レイアウトのエントリポイント — ここを書き換え
- `_rebuild_ui()` が `_build_ui()` を再呼び出し — テーマ/フォント変更時
- D&D（`_dnd_*` メソッド群）がサムネイルパネル内ウィジェットを参照 — パネル再構築時に影響
- crop 機能が `self.preview_canvas` を参照 — プレビューパネル構成変更時に影響

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-code-quality-responsive-ui*
*Context gathered: 2026-03-18*
