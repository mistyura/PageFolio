---
phase: 1
slug: 基盤と画像対応
status: draft
framework: tkinter
design_system: THEMES dict (pagefolio/constants.py)
created: "2026-05-04"
---

# Phase 1 — UI Design Contract

> Tkinter デスクトップアプリ向けビジュアル・インタラクション契約。
> gsd-ui-researcher が生成し、gsd-ui-checker が検証する。

---

## Design System

| 項目 | 値 |
|------|----|
| フレームワーク | Python 3.8+ Tkinter + ttk (clam テーマ) |
| デザインシステム | `pagefolio/constants.py` の `THEMES` 辞書 — dark / light の2テーマ |
| 実行時参照 | グローバル `C` 辞書（`_apply_theme()` で更新） |
| コンポーネントライブラリ | なし（ttk 標準ウィジェット + カスタムスタイル） |
| アイコンライブラリ | なし（Unicode 絵文字をラベルテキストに直接使用） |
| フォント | Segoe UI（Windows 11 標準）|
| 外部レジストリ | 非該当（Tkinter アプリにパッケージレジストリなし）|

---

## Widget Geometry (Tkinter Spacing)

> **既存コード実測値（参照専用・変更不可）**
>
> 以下のテーブルは `ui_builder.py` から抽出した既存実装の padx/pady 値の記録であり、
> スペーシング設計トークンではない。Phase 1 では新規追加レイアウトなし。
>
> **新規ウィジェットを追加する場合は、4・8・16 のいずれかを使用すること。**

| トークン | 値 (px) | 使用箇所 |
|---------|---------|---------|
| gap-xs | 2 | ボタン列内の左右間隔（`padx=2`） |
| gap-sm | 4 | サムネイルキャンバス周辺（`padx=4, pady=4`） |
| gap-md | 6 | セクション内ボタン横 padding（`padx=6`） |
| gap-lg | 8 | セクション内コンテンツ横 padding（`padx=8`） |
| gap-xl | 10 | パネルヘッダー・ボタン横 padding（`padx=10`） |
| gap-2xl | 20 | ヘッダー左右（`padx=20`） |
| section-vert | (5, 5) | セクションフレームの上下余白（`pady=5`） |
| section-head | (10, 4) | セクションヘッダー上下（`pady=(10, 4)`） |
| header-vert | 12 | ヘッダーウィジェット上下（`pady=12`） |

---

## Typography

`self._font(delta)` ヘルパーを使用する。ベースサイズは `self.font_size`（設定値 8〜16、デフォルト 10）。

行間: OS デフォルト行間を使用する（明示値なし）。

| ロール | ttk スタイル | サイズ式 | ウェイト | 用途 |
|--------|------------|---------|---------|------|
| Body | `TLabel` | `fs` | normal (400) | 通常テキスト全般 |
| Label | `Sub.TLabel` | `fs - 1` | normal (400) | ヒント・補足情報 |
| Caption | `Sub.TLabel` | `fs - 2` | normal (400) | セクション内小テキスト |
| Heading | `Title.TLabel` | `fs + 8` | bold (700) | アプリタイトル等 |
| Section | `TLabel` | `fs - 1` | bold (700) | セクション見出し（`WARNING` 色） |
| Button | `TButton` | `fs - 1` | bold (700) | 通常ボタン |
| Button Primary | `Accent.TButton` | `fs` | bold (700) | 主要アクションボタン |
| Status | `Status.TLabel` | `fs - 1` | normal (400) | ヘッダー右端ステータス |

新しいウィジェットにハードコードしたフォントサイズを指定してはならない。  
必ず `self._font(delta)` または `self._font(delta, "bold")` を使用すること。

---

## Color Contract

THEMES 辞書で定義済み。新規 UI 要素はこれらの値のみを使用すること。

### Dark テーマ（デフォルト）

| ロール | トークン | Hex | 用途 |
|--------|---------|-----|------|
| 主要背景 (60%) | `BG_DARK` | `#1a1a2e` | メインウィンドウ背景、プレビューエリア周辺 |
| 副次背景 (30%) | `BG_PANEL` | `#16213e` | ヘッダー、左サムネイルパネル、右ツールパネル |
| カード背景 | `BG_CARD` | `#0f3460` | セクションフレーム、ボタン背景 |
| アクセント (10%) | `ACCENT` | `#e94560` | 主要アクション、タイトル文字色、ボタンホバー、アクセントボタン背景 |
| テキスト主 | `TEXT_MAIN` | `#eaeaea` | 本文テキスト、ボタンラベル |
| テキスト副 | `TEXT_SUB` | `#a0a0b0` | ヒント文字、補足情報 |
| 成功 | `SUCCESS` | `#4ecca3` | ステータスバー通常メッセージ（ファイルオープン、保存完了等） |
| 警告 | `WARNING` | `#ffd460` | セクション見出し |
| 危険背景 | `DANGER_BG` | `#7c1c2e` | Danger.TButton 背景 |
| 危険文字 | `DANGER_FG` | `#ffaaaa` | Danger.TButton テキスト |
| プレビュー背景 | `PREVIEW_BG` | `#111122` | プレビューキャンバス背景 |

### Light テーマ（対応トークンのみ記載）

| トークン | Hex |
|---------|-----|
| `BG_DARK` | `#f0f0f5` |
| `BG_PANEL` | `#e0e0ea` |
| `BG_CARD` | `#d0d0dd` |
| `ACCENT` | `#d63050` |
| `TEXT_MAIN` | `#1a1a2e` |
| `TEXT_SUB` | `#555566` |
| `SUCCESS` | `#2a9d6a` |
| `WARNING` | `#b8860b` |
| `DANGER_BG` | `#e8c0c0` |
| `DANGER_FG` | `#7c1c2e` |
| `PREVIEW_BG` | `#c8c8d0` |

アクセント (`ACCENT`) の使用予約: タイトルラベル、`Accent.TButton` 背景、ボタンホバー状態、サムネイルパネル見出し文字。  
**他の要素にアクセントカラーを使用してはならない。**

---

## Button Style Contract

Phase 1 で新規追加・変更するボタンはなし。  
既存スタイルを参照情報として記載する。

| スタイル | 用途 | 色 |
|---------|------|----|
| `TButton` | 通常操作 | `BG_CARD` 背景 / `TEXT_MAIN` 文字 |
| `Accent.TButton` | 主要アクション（ファイルを開く等） | `ACCENT` 背景 / 白文字 |
| `Danger.TButton` | 破壊的操作（削除・終了） | `DANGER_BG` 背景 / `DANGER_FG` 文字 |
| `CropOn.TButton` | トリミングモード ON | `CROP_ON_BG` 背景 / 白文字 |

---

## Phase 1 UI Surface Area

Phase 1 で変更・追加が発生するUI要素を列挙する。

### 1. ファイルダイアログ フィルター（D-06）

`filedialog.askopenfilenames()` の `filetypes` 引数を以下の4エントリに変更する。

| 順序 | ラベル（LANG キー） | フィルター文字列 |
|-----|-----------------|----------------|
| 1（デフォルト） | `filetypes_supported` | `*.pdf;*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif` |
| 2 | `filetypes_pdf` | `*.pdf`（既存キー流用） |
| 3 | `filetypes_image` | `*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif` |
| 4 | `filetypes_all` | `*.*`（既存キー流用） |

挿入ダイアログ（`dlg_insert_title`）も同様に変更する（D-06 の範囲）。  
ただし `dlg_merge_title` は「PDF を末尾に結合」の意味合いのため **変更しない**（PDF のみでよい）。

### 2. D&D ドロップハンドラー（D-07）

`_on_dnd_drop()` の拡張子フィルターを `SUPPORTED_EXTENSIONS` 定数で置き換える。  
視覚的変化なし（既存のドロップゾーン UI に変更なし）。

**ただし** `dnd_drop_hint` / `dnd_pdf_only` の文字列は更新が必要（下記コピーライティング参照）。

### 3. 上書き保存フォールスルー（D-11）

`_save_file()` に拡張子チェックを追加。画像拡張子だった場合、確認ダイアログなしで即 `_save_as()` に転送する。  
`_save_as()` 起動時は専用ステータスメッセージを表示する（視覚的フィードバック）。

### 4. タイトルバー（D-12）

変更なし。既存の `[*] filename.png` 表示形式をそのまま維持する。

---

## Copywriting Contract

### LANG 辞書に追加する新規キー

下表のキーをすべて `LANG["ja"]` と `LANG["en"]` の両方に追加すること。  
既存キーの変更・削除は行わない。

#### ファイルタイプラベル

| キー | ja 値 | en 値 |
|-----|-------|-------|
| `filetypes_supported` | `サポートファイル` | `Supported Files` |
| `filetypes_image` | `画像ファイル` | `Image Files` |

#### ステータスメッセージ

| キー | ja 値 | en 値 | 用途 |
|-----|-------|-------|------|
| `status_opened_image` | `開きました（画像→PDF変換）: {name}  (1ページ)` | `Opened (image→PDF): {name}  (1 page)` | 単体画像ファイルをオープン後のステータス |
| `status_image_save_as` | `画像ファイルは PDF で保存します — 保存先を選択してください` | `Image file will be saved as PDF — choose save location` | Ctrl+S を画像ファイルで押した際のステータス |

#### D&D テキスト更新

以下の既存キーは値を変更する（キー名は維持）。

| キー | 旧 ja 値 | 新 ja 値 | 旧 en 値 | 新 en 値 |
|-----|---------|---------|---------|---------|
| `dnd_drop_hint` | `ここに PDF をドロップ` | `ここに PDF / 画像をドロップ` | `Drop PDF here` | `Drop PDF or image here` |
| `dnd_pdf_only` | `PDF ファイルのみ対応しています` | `PDF または画像ファイル (PNG/JPG/BMP/TIFF) のみ対応しています` | `Only PDF files are supported` | `Only PDF or image files (PNG/JPG/BMP/TIFF) are supported` |

#### D&D 挿入ダイアログタイトル更新

| キー | 旧 ja 値 | 新 ja 値 | 旧 en 値 | 新 en 値 |
|-----|---------|---------|---------|---------|
| `dlg_insert_title` | `挿入するPDFを選択（複数可）` | `挿入するファイルを選択（PDF/画像、複数可）` | `Select PDF(s) to Insert` | `Select file(s) to insert (PDF/image)` |

### 既存ダイアログ流用（変更なし）

| ダイアログ | 流用理由 |
|-----------|---------|
| `MergeOrderDialog` | 画像ファイルも同フロー（D-09）。タイトル `merge_title` / ヒント `merge_hint` は PDF 特有表現なし |
| 置換確認 `dnd_replace_confirm` | 「現在のファイルを閉じて…」は画像でも同義。変更なし |
| 上書き保存確認 `save_confirm_msg` | 画像ファイルは `_save_as()` に転送されるためこのダイアログは表示されない |

---

## Interaction Contract

### ファイルオープンフロー（画像ファイル）

```
ユーザーがファイルダイアログで画像を選択
  └─ 単体選択 → _open_pdf_path(path) をそのまま呼ぶ（fitz が自動変換）
               → ステータス: status_opened_image
  └─ 複数選択 → _open_multiple_pdfs(paths) → MergeOrderDialog（既存フロー）

ユーザーが画像をドロップ（単体）
  └─ doc が開いている → dnd_replace_confirm ダイアログ（既存フロー、変更なし）
  └─ doc が閉じている → そのまま _open_pdf_path(path)

ユーザーが複数ファイル（PDF + 画像混在）をドロップ
  └─ MergeOrderDialog（既存フロー、変更なし）
```

### 上書き保存フロー（D-11）

```
Ctrl+S または「上書き保存」ボタン
  └─ self.filepath の拡張子が IMAGE_EXTENSIONS に含まれる
       → ステータスに status_image_save_as を表示
       → _save_as() を呼ぶ（確認ダイアログなし）
  └─ self.filepath が PDF または None
       → 既存フロー（確認ダイアログ → PDF 保存）
```

### エラーハンドリング

画像ファイルオープン失敗時は既存の `err_title` / `err_save_msg` パターンを流用する（新規エラーキー追加なし）。

---

## Constants Contract

`pagefolio/constants.py` に追加する定数。

```python
# 対応拡張子（D-05）
SUPPORTED_EXTENSIONS = frozenset({
    ".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"
})

IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"
})
```

3箇所で同一定数を参照すること（保守性確保）:
1. `_open_file()` の `filetypes` 生成
2. `_on_dnd_drop()` の拡張子フィルター
3. `_save_file()` の画像フォールスルー判定

---

## Registry Safety

非該当。本プロジェクトは Tkinter デスクトップアプリであり、  
shadcn / npm レジストリ等の外部コンポーネントレジストリを使用しない。

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS — 新規キー8件（ja/en両方）、既存キー4件の値更新
- [ ] Dimension 2 Visuals: PASS — 新規ウィジェットなし、既存スタイル継続使用
- [ ] Dimension 3 Color: PASS — 既存 THEMES dict 使用、新色追加なし
- [ ] Dimension 4 Typography: PASS — `_font(delta)` ヘルパー使用、ハードコードなし。行間は OS デフォルト
- [ ] Dimension 5 Spacing: PASS — Widget Geometry は既存コード実測値（参照専用・変更不可）。新規レイアウトなし
- [ ] Dimension 6 Registry Safety: PASS — 非該当（Tkinter アプリ）

**Approval:** pending
