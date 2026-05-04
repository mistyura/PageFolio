# Phase 1: 基盤と画像対応 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 1-基盤と画像対応
**Areas discussed:** requirements.txt の範囲, ファイルダイアログ・D&D, 複数画像の同時開封, 上書き保存の挙動

---

## requirements.txt の範囲

### 含めるパッケージの範囲

| Option | Description | Selected |
|--------|-------------|----------|
| 直接依存のみ | PyMuPDF, Pillow, tkinterdnd2 の 3 つ（またはビルド用に pyinstaller を追加）。pip freeze 由来の無関係パッケージを除去。REQUIREMENTS.md の趣旨（バージョン固定）に合致 | ✓ |
| 直接依存 + dev 依存 | 上記 3 つに pytest, pytest-cov, ruff を追加。開発環境を再現したい場合に有効 | |
| 現状の pip freeze そのまま | 無関係パッケージも含めてコミット。環境再現性は高いが PageFolio 本来の依存がわかりにくい | |

**User's choice:** 直接依存のみ
**Notes:** —

### pyinstaller の扱い

| Option | Description | Selected |
|--------|-------------|----------|
| requirements.txt に含める | exe 配布はプロジェクトの重要成果物。pyinstaller を直接依存扱いしてシンプルに管理 | ✓ |
| dev 深さに並べる | pytest / ruff と同じ列に、開発時のみ必要なツールとして割り切る | |

**User's choice:** requirements.txt に含める

### pytest / ruff などの dev 依存

| Option | Description | Selected |
|--------|-------------|----------|
| 含める | pytest, pytest-cov, ruff を同じファイルに載せる。単一ファイルで開発環境を再現できる（pyproject.toml でリントルールは定義済み） | ✓ |
| 含めない | CLAUDE.md や pyproject.toml で充分と判断する場合 | |

**User's choice:** 含める

---

## ファイルダイアログ・D&D

### 「開く」ダイアログのフィルター設計

| Option | Description | Selected |
|--------|-------------|----------|
| サポートファイルをまとめる | 1 エントリー「PDF / 画像」に *.pdf;*.png;*.jpg... をまとめ、次に個別フィルター（PDF のみ, 画像のみ）も加える。まとめて開けるのでシンプル | ✓ |
| PDF / 画像を分けて表示 | PDF フィルターはそのまま、「画像ファイル」エントリーを別途追加。現在のフィルター構造を小さく変更で済む | |

**User's choice:** サポートファイルをまとめる

### 対応拡張子の範囲

| Option | Description | Selected |
|--------|-------------|----------|
| PNG/JPG/BMP/TIFF（4形式） | REQUIREMENTS.md IMG-01 に列記された形式のみ。*.jpg と *.jpeg、*.tiff と *.tif 両方を含める | ✓ |
| WebP も追加（5形式） | PyMuPDF 1.27.x は WebP をサポート。実装コスト最小限で追加可能 | |

**User's choice:** PNG/JPG/BMP/TIFF（4形式）

### D&D 画像単体ドロップ時の挙動

| Option | Description | Selected |
|--------|-------------|----------|
| PDF と同じ流れ | 画像単体ドロップ → ドキュメントがあれば置換確認ダイアログ、なければそのまま開く。追加実装可最小限 | ✓ |
| 画像は常に確認なしで開く | 画像は新規ドキュメント扱いなので置換確認をスキップ。ユーザーが意図してドロップしたのに確認が出て烈度が下がるかも | |

**User's choice:** PDF と同じ流れ

---

## 複数画像の同時開封

### 複数画像を同時選択した時の挙動

| Option | Description | Selected |
|--------|-------------|----------|
| 複数PDF と同じ流れ | MergeOrderDialog で順序確認 → 全ページを結合した 1 ドキュメントとして開く。追加実装なしで既存ダイアログを再利用 | ✓ |
| 1 枚目のみ開く | 最初のファイルだけ開き、残りは無視。シンプルだが複数選択した時に残りが消えるのは直感的でない | |

**User's choice:** 複数PDF と同じ流れ

### PDF+画像混在の場合

| Option | Description | Selected |
|--------|-------------|----------|
| 結合して開く | PDF と画像を区別せず、MergeOrderDialog フローで全てのファイルをページとして結合。実装がシンプルで一貫性が高い | ✓ |
| 第 1 ファイルのみ開く | PDF・画像混在は複雑なので最初のファイルだけ開く。しかしユーザーが意図したファイルが消える可能性あり | |

**User's choice:** 結合して開く

---

## 上書き保存の挙動

### 画像ファイルを開いている時の Ctrl+S

| Option | Description | Selected |
|--------|-------------|----------|
| 名前付け保存が起動する | Ctrl+S を押すと PDF 出力の「名前を付けて保存」ダイアログを自動起動。配布保存形式が常に PDF なので違和感なし | ✓ |
| 自動保存（.pdf に上書き） | 元ファイル名の拡張子を .pdf に変えて同じディレクトリに自動保存。ユーザー演算が少ないが、予期せぬ場所に保存されるリスクあり | |
| 警告ダイアログを表示 | 「PNG は PDF としてのみ保存できます」と警告後、名前付け保存ダイアログへ転送。明示的だがクリック数が増える | |

**User's choice:** 名前付け保存が起動する

### タイトルバー・ヘッダーの表示

| Option | Description | Selected |
|--------|-------------|----------|
| 現在の形式のまま | 画像ファイルも PDF と同じ形式でファイル名を表示。追加実装不要 | ✓ |
| 拡張子を表示に含める | 「[*] photo.png」のように、画像ファイルの場合は .png も表示する。かかるコストに対してメリットは小さい | |

**User's choice:** 現在の形式のまま

---

## Claude's Discretion

- `SUPPORTED_EXTENSIONS` と `IMAGE_EXTENSIONS` の定数名・構造（set vs. tuple vs. list）
- ファイルタイプ文字列の LANG キー命名（`filetypes_supported`, `filetypes_image` 等）

## Deferred Ideas

None — 議論はフェーズスコープ内に留まった。
