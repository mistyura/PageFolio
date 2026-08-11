---
gsd_summary_version: 1.0
quick_id: 260812-a8u
slug: project-md-constraints
description: PROJECT.md に Constraints 節を追加（loto/numbers と揃える）
date: 2026-08-12
status: complete
branch: quick/260812-a8u-project-md-constraints
---

# Quick Summary 260812-a8u — `.planning/PROJECT.md` に `## Constraints` 節を追加

## 結果

3 プロジェクト比較（260812-9tv）で挙げた**差分 #3 を解消**。loto/numbers と同型の `## Constraints` 節を新設し、ブランチ運用の入口を規定位置（Constraints 末尾）へ移した。

## 変更内容

### `.planning/PROJECT.md`

- `## Constraints` 節を `## Context` の直後・`## Problem Statement` の前に新設（loto/numbers の Context → Constraints 順に一致）
- 260812-9tv で暫定的に `## Context` 表へ置いていたブランチ運用ポインタを **Constraints 末尾へ移設**（重複なし・Context 表からは削除）
- 末尾 `*Last updated:*` を更新

### 記載した 9 項目（すべて `CLAUDE.md` に典拠あり）

| 項目 | 内容の要点 |
|------|-----------|
| Tech stack | Python 3.8+ / Tkinter、PyMuPDF 1.28.0 / Pillow 12.3.0 / tkinterdnd2 0.6.2、PyInstaller onedir。`pyproject.toml` 編集禁止 |
| 互換性 | Undo は操作固有のデルタ dict（full シリアライズではない）・`MAX_UNDO = 20`・`_capture_page_blob()` / `_blob_bytes()` 経由必須・スタックへの直接 `append`/`clear` 禁止 |
| スレッド制約 | UI は Tkinter メインスレッド、描画は `root.after()` チェーン + 世代カウンタ、OCR は `ThreadPoolExecutor`、fitz のスレッド制約でバッチ OCR のファイル間は逐次 |
| CropBox 安全処理 | MediaBox 内へクランプしてから `set_cropbox()`、回転表示中は `_derotate_rect` で座標変換 |
| 品質ゲート | py 編集後に ruff、コミット前に pytest、リリース判定は `CLAUDE.md`「## リリースゲート」節 |
| 言語 | コミット/PR/コメント/ユーザー応答は日本語、識別子は英語 |
| 禁止 | `pyproject.toml` 編集・裸の `except:`・無断の `# type: ignore`・テーマ色/フォントサイズのハードコード |
| Security | API キーを `pagefolio_settings.json` に保存しない（`_SENSITIVE_KEYS`）、`ocr_providers/registry.py` の標準ライブラリのみ依存制約（V180-ROBUST-02） |
| ブランチ運用（v1.10.0 以降） | `main` へ直接コミット・push しない → `## ブランチ運用` 節へのポインタ |

**新しい制約は一切発明していない**。すべて `CLAUDE.md` の既存記述（プロジェクト概要 / コーディング規約 / 作業フロー / 禁止事項 / 言語ルール / 既知の制限 / リリースゲート / Architectural Constraints）の要約であり、正本は `CLAUDE.md` 側に残している（節冒頭に明記）。

## loto / numbers との対応

| プロジェクト | Constraints の項目数 | 末尾行 |
|---|---|---|
| numbers（原典・`feature/v0.18.0`） | 8 | ブランチ運用（v0.18.0 以降） |
| loto（`main`） | 6 | ブランチ運用（v0.19.0 以降） |
| **PageFolio（本タスク）** | **9** | **ブランチ運用（v1.10.0 以降）** |

項目名・粒度は各プロジェクトの実情に合わせる（numbers は「チェーン例外漏洩の再検査」、loto は「Performance」など固有項目を持つ）。**共通の型は「末尾がブランチ運用ポインタであること」**であり、PageFolio もこれに合わせた。

## 検証

- `## Context` → `## Constraints` → `## Problem Statement` の順序を assert で確認
- ブランチ運用ポインタが Constraints 末尾に 1 つだけ存在し、`## Context` 表から消えていることを assert で確認
- 制約 9 項目の列挙を確認
- `ruff check .` → All checks passed
- `pytest -q --basetemp=...pf_pytest_tmp_a8u` → **1404 passed**（失敗 0・ERROR 0・クラッシュなし＝リリースゲート合格。症状①の再発なし）

## スコープ外

- `## フェーズ完了 DoD` 節と `tests/test_gsd_dod.py` 相当の機械ゲート（比較 #4・**loto のみ保有**。numbers は `## Definition of Done` 節を持つが機械ゲートは loto 固有）
- `claude_md_assembly` キーの追加（比較 #5）
- `CLAUDE.md` 本体の変更（Constraints はその要約であり、正本は CLAUDE.md 側）

## 申し送り

3 プロジェクト比較で挙げた差分のうち **#1・#2・#3 が解消済み**。残るは #4（`## フェーズ完了 DoD` + 機械ゲートテスト）と #5（`claude_md_assembly`）。
#4 は loto が `tests/test_gsd_dod.py` で ROADMAP の `Complete` 行と `NN-VALIDATION.md` の status の乖離を機械検知しているもので、PageFolio に導入するなら**テストコードの新規追加**を伴うためドキュメント整備より重い。次マイルストーンの要件として扱うか、単発 quick で入れるかの判断が要る。
