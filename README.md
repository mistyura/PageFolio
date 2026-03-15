# PageFolio

**PDF ページ整理ツール — Python + Tkinter 製 GUI アプリ**

A PDF page organizer built with Python + Tkinter.  
Windows 11 で動作します / Runs on Windows 11.

> 📝 このプロジェクトは [Claude Code](https://claude.ai/code)（Anthropic）を活用して開発されています。
> AI との協調開発のユースケースとして公開しています。
>
> This project is developed with [Claude Code](https://claude.ai/code) by Anthropic,
> and published as a use case of AI-assisted development.

---

## 概要 / Overview

PageFolio は PDF のページを整理・編集するための GUI ツールです。
テキスト編集や注釈追加は行いません。**ページ単位の操作に特化しています。**

PageFolio is a GUI tool for organizing and editing PDF pages.
It does **not** edit text or add annotations — it focuses on **page-level operations**.

---

## 機能 / Features

| 機能 | 説明 |
|------|------|
| 📂 ファイルを開く | 単一・複数 PDF を読み込み（複数選択時は結合） |
| 💾 保存 | 上書き保存 / 名前を付けて保存 |
| 🔄 ページ回転 | 90° / 180° / 270°、複数ページ一括対応 |
| 🗑 ページ削除 | 選択ページをまとめて削除 |
| ✂ トリミング | プレビュー上のドラッグで余白をカット |
| 📎 挿入・結合 | 別 PDF からページを挿入 / 末尾に結合 |
| 🔀 D&D 並び替え | サムネイルをドラッグ＆ドロップでページ順を変更 |
| ↩ Undo / Redo | 最大20回の取り消し・やり直し（Ctrl+Z / Ctrl+Y） |
| 🔍 プレビュー | ズーム・スクロール対応、ページ拡大表示 |
| ⚙ テーマ・フォント | ダーク / ライト / システム連動、フォントサイズ変更 |

---

## 必要環境 / Requirements

- Python 3.8 以上 / Python 3.8+
- 必要ライブラリ（初回起動時に自動インストール）/ Auto-installed on first launch:
  - `pymupdf`
  - `pillow`

---

## 起動方法 / Getting Started

```
PageFolio起動.bat をダブルクリック
Double-click PageFolio起動.bat
```

初回のみライブラリの自動インストールが行われます。
Required libraries are installed automatically on the first launch.

---

## 画面構成 / Layout

```
┌─────────────────────────────────────────────┐
│  ヘッダー（タイトル / ステータス表示）           │
├──────────┬──────────────────────┬────────────┤
│          │                      │            │
│ ページ   │   プレビュー          │  ツール    │
│ 一覧     │   （現在ページ表示）  │  パネル    │
│ サムネイル│                      │            │
│          │                      │            │
└──────────┴──────────────────────┴────────────┘
```

---

## 注意事項 / Notes

- トリミングは **現在表示中のページ** にのみ適用されます
- 回転・削除は **選択中のページ** が対象です（未選択の場合は現在ページ）
- 保存前にアプリを閉じると編集内容は失われます
- 暗号化・パスワード保護された PDF は開けない場合があります

---

## Claude Code による開発について / About AI-assisted Development

本プロジェクトは Claude Code を使った開発のユースケースとして公開しています。

- `CLAUDE.md` — Claude に渡す構造化された開発指示書
- `開発履歴.md` — 各バージョンの変更内容を記録した開発ログ

v0.1（旧 PDF Editor v1.0）から現在まで、機能追加・バグ修正・UI改善のほぼすべてを Claude Code との対話で実装してきました。

This project is published as a use case of development with Claude Code.

- `CLAUDE.md` — Structured development instructions passed to Claude
- `開発履歴.md` (Development History) — Change log for each version

---

## ライセンス / License

MIT License — see [LICENSE](LICENSE)
