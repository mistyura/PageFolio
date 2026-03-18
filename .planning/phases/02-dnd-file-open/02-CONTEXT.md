# Phase 2: D&D ファイルオープン - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

プレビュー領域への PDF ドロップでファイルを開く機能。複数ファイルは結合ダイアログ表示。ドラッグ中のビジュアルフィードバック。既存の windnd フックを拡張する。

</domain>

<decisions>
## Implementation Decisions

### ドロップ対象領域
- プレビュー領域（preview_canvas）のみがドロップターゲット（ファイル未オープン時も同じ）
- プレビュー領域以外（サムネイル・ツール）へのドロップは無視
- ドラッグ中にプレビュー領域上にいるかどうかでフィードバックを切り替える

### ファイルオープン時の挙動
- 既にファイルを開いている状態で1ファイルをドロップ → 現在のファイルを閉じて新しいファイルを開く（未保存なら確認ダイアログ）
- 複数ファイルドロップ → 既存の MergeOrderDialog を再利用して結合順を確認

### ビジュアルフィードバック
- ドラッグ中（プレビュー領域上）: 背景色変更 + 「ここにPDFをドロップ」テキスト表示
- ドラッグ中（プレビュー領域外）: フィードバックなし
- ドロップ後: ステータスバーに「XXX.pdf を開きました」と表示（既存の _set_status を流用）

### 複数ファイルの挙動
- 複数 PDF ドロップ → MergeOrderDialog で結合順を確認してから結合
- PDF と非 PDF が混在 → PDF のみ抽出して処理、非 PDF は無視

### PDF以外のファイル
- PDF 以外のファイルを1つだけドロップ → ステータスバーにエラー表示（「PDFファイルのみ対応しています」）
- ダイアログは出さない（うるさくならないように）

### Claude's Discretion
- windnd のフック先（root 全体のまま vs preview_canvas のみ）の技術的判断
- ドラッグ中フィードバックの具体的な背景色（テーマカラーから選択）
- フィードバック表示のタイミングとアニメーション
- 未保存確認ダイアログの実装方法（既存の確認フローがあればそれを流用）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### プロジェクト構成
- `CLAUDE.md` — コーディング規約、クラス構成、状態管理ルール
- `.planning/PROJECT.md` — 制約条件（単一ファイル構成、D&D 先はプレビュー領域と決定済み）
- `.planning/REQUIREMENTS.md` — DND-01, DND-02, DND-03 の受け入れ基準

### 既存コード
- `pagefolio.py` L2386-2398 — 既存の `_setup_file_drop()` windnd フック実装
- `pagefolio.py` L733-765 — `_build_ui()` 3ペイン PanedWindow 構成（Phase 1 で変更済み）
- `pagefolio.py` L833-843 — `preview_canvas` の構成
- `pagefolio.py` L1080-1120 付近 — `_open_pdf_path()` 既存のファイルオープン処理

### Phase 1 コンテキスト
- `.planning/phases/01-code-quality-responsive-ui/01-CONTEXT.md` — 3ペイン構成の決定事項

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_setup_file_drop()`: windnd フック — 現在 root 全体にフック、1ファイルのみ対応。拡張ベースとして利用
- `_open_pdf_path(path)`: ファイルパスから PDF を開くメソッド — D&D でもこれを呼べる
- `MergeOrderDialog`: 結合順序ダイアログ — 複数ファイルドロップ時にそのまま再利用可能
- `_set_status(msg)`: ステータスバー更新 — ドロップ後のフィードバックに流用
- `_do_open_merged(ordered_paths)`: 結合処理 — MergeOrderDialog のコールバック

### Established Patterns
- windnd は `windnd.hook_dropfiles(root, func=on_drop)` で root 全体にフック
- ファイルパスは bytes の場合があるため `decode('utf-8')` が必要
- テーマカラーは `C["KEY"]` 辞書経由で参照
- ステータスメッセージは `self._set_status()` で表示

### Integration Points
- `_setup_file_drop()` が windnd のエントリポイント — ここを書き換え
- `preview_canvas` がドロップターゲット — 座標判定でプレビュー上かどうかを判別
- `self.doc` の存在チェックで未保存確認の要否を判断

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

*Phase: 02-dnd-file-open*
*Context gathered: 2026-03-18*
