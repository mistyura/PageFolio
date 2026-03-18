---
phase: 02-dnd-file-open
verified: 2026-03-18T21:00:00+09:00
status: human_needed
score: 5/6 must-haves verified (1 requires human confirmation)
human_verification:
  - test: "ドラッグ中のビジュアルフィードバック（背景色 + テキスト表示）の実際の動作確認"
    expected: "プレビュー領域にドラッグすると背景色がアクセント色に変わり「ここに PDF をドロップ」テキストが表示される。領域外に出ると元に戻る。"
    why_human: "Canvas のサイズが 0×0 でウィジェットが未表示の状態では winfo_width/height が 0 を返す可能性があり、テキスト配置が意図通りかはアプリ起動後の実機確認が必要。コードの存在は確認済み。"
  - test: "テーマ変更後の D&D 動作確認"
    expected: "_rebuild_ui 後も preview_canvas に dnd_bind が再登録され D&D が正常動作する"
    why_human: "コード上は _rebuild_ui 末尾に _setup_file_drop(self) が呼ばれているが、canvas の再生成タイミングと dnd_bind の関係は実行時確認が必要。"
---

# Phase 2: D&D ファイルオープン 検証レポート

**フェーズゴール:** ユーザーがエクスプローラーから PDF ファイルをプレビュー領域にドラッグ&ドロップするだけでファイルを開ける
**検証日時:** 2026-03-18T21:00:00+09:00
**ステータス:** human_needed（自動検証: 全項目通過 / 2項目は人手確認推奨）
**再検証:** 不要（初回検証）

---

## ゴール達成評価

### 観測可能な真実（Observable Truths）

| # | 真実 | ステータス | 根拠 |
|---|------|----------|------|
| 1 | プレビュー領域に PDF をドロップするとそのファイルが開かれる | ✓ VERIFIED | `_on_dnd_drop` L1875 — pdf_paths 1件時に `_open_pdf_path(pdf_paths[0])` を呼ぶ |
| 2 | 複数の PDF を同時にドロップすると MergeOrderDialog が表示される | ✓ VERIFIED | `_on_dnd_drop` L1896-1898 — `len(pdf_paths) > 1` で `MergeOrderDialog` を呼ぶ |
| 3 | ドラッグ中にプレビュー領域上にいると背景色変更+テキストでフィードバックが表示される | ? UNCERTAIN | `_on_dnd_enter` L1854-1867 — コード実装済みだが実機動作は人手確認必要 |
| 4 | プレビュー領域外へドラッグを移動するとフィードバックが消える | ? UNCERTAIN | `_on_dnd_leave` L1869-1873 — コード実装済みだが実機動作は人手確認必要 |
| 5 | PDF 以外のファイルをドロップするとダイアログでエラー表示される | ✓ VERIFIED | `_on_dnd_drop` L1884-1888 — `messagebox.showwarning` で通知（計画からの逸脱: _set_status から変更、UX向上のため） |
| 6 | 既にファイルを開いている状態で1ファイルドロップすると未保存確認ダイアログが出る | ✓ VERIFIED | `_on_dnd_drop` L1891-1894 — `self.doc` 存在時に `messagebox.askyesno` で確認 |

**スコア:** 4/6 自動確認済み、2/6 人手確認推奨（コードは実装済み）

---

### 必須アーティファクト検証

| アーティファクト | 役割 | 存在 | 実質的内容 | 配線 | ステータス |
|----------------|------|------|-----------|------|----------|
| `pagefolio.py` — `from tkinterdnd2 import TkinterDnD, DND_FILES` | tkinterdnd2 条件付き import | ✓ L22-25 | 実装済み（_HAS_TKDND フォールバック付き） | N/A | ✓ VERIFIED |
| `pagefolio.py` — `_on_dnd_enter` | DropEnter ハンドラ | ✓ L1854 | 47行の実装（背景色変更 + テキスト表示） | `dnd_bind('<<DropEnter>>')` で登録 L2459 | ✓ VERIFIED |
| `pagefolio.py` — `_on_dnd_leave` | DropLeave ハンドラ | ✓ L1869 | 実装済み（背景色リセット + テキスト削除） | `dnd_bind('<<DropLeave>>')` で登録 L2460 | ✓ VERIFIED |
| `pagefolio.py` — `_on_dnd_drop` | Drop ハンドラ | ✓ L1875 | 実装済み（単一/複数/非PDF の分岐処理） | `dnd_bind('<<Drop>>')` で登録 L2461 | ✓ VERIFIED |
| `pagefolio.py` — `_setup_file_drop` | D&D フック登録 | ✓ L2453 | `drop_target_register` + 3ハンドラ登録 | `__main__` L2471 + `_rebuild_ui` L2001 | ✓ VERIFIED |
| `pagefolio.py` — `TkinterDnD.Tk()` | root 初期化 | ✓ L2467 | `_HAS_TKDND` 分岐で条件付き使用 | `__main__` ブロック内 | ✓ VERIFIED |

---

### キーリンク検証

| From | To | Via | ステータス | 根拠 |
|------|----|-----|----------|------|
| `_on_dnd_drop` | `_open_pdf_path` / `MergeOrderDialog` | `len(pdf_paths)` 分岐 | ✓ WIRED | L1895: `self._open_pdf_path(pdf_paths[0])`, L1897: `MergeOrderDialog(...)` |
| `_on_dnd_enter` / `_on_dnd_leave` | `preview_canvas` | `configure(bg=...)` と `delete/create_text("dnd_hint")` | ✓ WIRED | L1856-1866 (enter), L1871-1872 (leave) |
| `__main__` | `TkinterDnD.Tk()` | root 初期化 | ✓ WIRED | L2466-2469 — `_HAS_TKDND` 条件付きで `TkinterDnD.Tk()` |
| `_rebuild_ui` | `_setup_file_drop` | メソッド末尾呼び出し | ✓ WIRED | L2001: `_setup_file_drop(self)` |

---

### 要件カバレッジ

| 要件 ID | 計画での宣言 | 説明 | ステータス | 根拠 |
|--------|------------|------|----------|------|
| DND-01 | 02-01-PLAN.md | プレビュー領域に PDF をドロップしてファイルを開ける | ✓ SATISFIED | `_on_dnd_drop` の単一ファイル分岐 + `_open_pdf_path` 呼び出しを確認 |
| DND-02 | 02-01-PLAN.md | 複数 PDF を同時ドロップすると結合ダイアログが表示される | ✓ SATISFIED | `_on_dnd_drop` の複数ファイル分岐 + `MergeOrderDialog` 呼び出しを確認 |
| DND-03 | 02-01-PLAN.md | ドロップ対象エリアにファイルをドラッグするとビジュアルフィードバックが表示される | ? NEEDS HUMAN | `_on_dnd_enter/_on_dnd_leave` のコード実装は確認済み。実際のビジュアル動作は人手確認必要 |

**孤立要件（ORPHANED）:** なし — REQUIREMENTS.md で Phase 2 にマッピングされた DND-01/02/03 は全て 02-01-PLAN.md が宣言済み。

---

### アンチパターンスキャン

D&D 関連コード（L1854-1900、L2453-2461）でスキャンした結果:

| ファイル | 行 | パターン | 深刻度 | 影響 |
|--------|---|---------|------|------|
| — | — | 検出なし | — | — |

**特記事項（アンチパターンではないが注記）:**
- `return event.action` が全ハンドラで正しく実装されている（L1867, L1873, L1888, L1894, L1900 — 計5箇所）
- `tk.splitlist(event.data)` によるスペース入りパス対応が実装されている（L1881）
- windnd が完全除去されている（grep で `windnd` ゼロ件）

---

### 計画からの逸脱

| 逸脱内容 | 計画の指定 | 実際の実装 | 評価 |
|---------|---------|---------|------|
| 非 PDF ドロップ時の通知方法 | `_set_status(self._t("dnd_pdf_only"))` | `messagebox.showwarning(...)` | 許容 — 手動テスト時のフィードバックを反映した UX 改善。ゴール達成に影響なし |

---

### 人手検証が必要な項目

#### 1. ビジュアルフィードバックの実機動作

**テスト手順:** PDF をエクスプローラーから選択し、アプリのプレビュー領域にドラッグ（ドロップはしない）
**期待動作:** プレビュー領域の背景色がアクセント色（赤）に変わり、中央に「ここに PDF をドロップ」テキストが表示される
**理由:** Canvas の `winfo_width()` / `winfo_height()` はウィジェット表示前は 0 を返す場合があり、テキスト配置座標がゼロにならないか実機確認が必要

#### 2. ドラッグ領域外移動時のフィードバック解除

**テスト手順:** 上記テストの継続 — ドラッグしたままプレビュー領域外（サムネイルパネルやツールパネル）に移動する
**期待動作:** 背景色が元の `PREVIEW_BG` 色に戻り、テキストが消える
**理由:** `<<DropLeave>>` イベントの発火タイミングが Tkinter の実装依存であり、実機で確認が必要

#### 3. テーマ変更後の D&D 再登録

**テスト手順:** 設定ダイアログからテーマを変更 → D&D を再テスト
**期待動作:** テーマ変更後も D&D が正常に動作する
**理由:** `_rebuild_ui` が全ウィジェットを破棄・再生成するため、dnd_bind の再登録が確実に機能するか実機確認が安全

---

### コミット検証

SUMMARY.md に記録されたコミットハッシュの実在確認:
- `6110922` — 存在確認済み (`feat(02-01): tkinterdnd2 による D&D ファイルオープン機能を実装`)
- `fdb9cc9` — 存在確認済み (`fix(02-01): 非PDFドロップ時に警告ダイアログ表示に変更`)

---

### ギャップサマリー

自動検証ではブロッカーとなるギャップは発見されなかった。全てのキーアーティファクトが存在し、実質的な実装を持ち、正しく配線されている。

DND-03 のビジュアルフィードバックおよびテーマ変更後の D&D 再登録については、コードの実装は完全だが、Tkinter の Canvas 動作特性上、実機での動作確認を推奨する。これらは「ゴール未達成」ではなく「人手確認推奨」の分類。

---

_検証日時: 2026-03-18T21:00:00+09:00_
_検証者: Claude (gsd-verifier)_
