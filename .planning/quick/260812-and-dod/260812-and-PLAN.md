---
gsd_plan_version: 1.0
quick_id: 260812-and
slug: dod
description: フェーズ完了 DoD の機械ゲートと PROJECT.md の DoD 節を追加
date: 2026-08-12
mode: quick
branch: quick/260812-and-dod
---

# Quick Plan 260812-and — フェーズ完了 DoD の機械ゲート追加

3 プロジェクト比較（260812-9tv）の**最後の未解消差分 #4**。

## loto 実装の直接移植は不可能 — 事前調査の結果

loto の `tests/test_gsd_dod.py`（717 行）は `.planning/ROADMAP.md` の `## Progress` 進捗表から
`Status == Complete` の行を拾い、Phase 番号でディレクトリを解決する設計。**PageFolio には 3 つの前提が成立しない。**

| # | loto の前提 | PageFolio の実態 | 影響 |
|---|---|---|---|
| B-1 | `## Progress` 表が `Phase` 列と `Status` 列を持つ | `## Progress` は**マイルストーン単位**の表（列は `Milestone / Phases / Plans / Status / Shipped`）。**`Phase` 列が存在しない**。フェーズ単位の内訳は `## Phases` の `<details>` 内のチェックボックス行 | パーサが `Phase` セルを見つけられず AssertionError |
| B-2 | フェーズ番号がプロジェクト全体で連番（22→30） | **マイルストーンごとに Phase 1 起点へリセット**（プロジェクト方針・STATE.md 記載）。`03-*` は v1.6.0 / v1.7.1 / v1.8.0 / v1.9.0 の 4 箇所に存在 | 番号→ディレクトリの解決が原理的に一意にならない |
| B-3 | `yaml.safe_load` が使える | **PyYAML が未インストール**（`requirements.txt` に無く `import yaml` が失敗） | そのままでは import エラー |

さらに、既存データを調査した結果 **v1.9.0 以外は `status: validated` になっていない**。

| マイルストーン | フェーズ数 | VALIDATION.md の status |
|---|---|---|
| v1.4.0 | 4 | validated / validated / **complete** / **なし** |
| v1.6.0 | 4 | **なし** / **approved** / **approved** / **draft** |
| v1.7.1 | 4 | **approved** / **ready** / **draft** / **planned** |
| v1.8.0 | 6 | **approved** / **draft** / **ready** / **draft** / validated / **draft** |
| **v1.9.0** | **3** | **validated / validated / validated** |

v1.9.0 以前の `*-VALIDATION.md` は `/gsd-validate-phase` の出力ではなく別種のドキュメント（プラン検証等）で、
status 語彙も揃っていない。**そのまま全件を対象にするとゲートは導入直後に恒常 red になる。**

## 設計（PageFolio 版）

loto の「思想」（機械ゲートで強制する・空虚 PASS を許さない・アーカイブで回避させない）を維持し、
**走査の入口を ROADMAP パースからフェーズディレクトリ列挙へ差し替える**。B-2 の番号リセットが構造的に無害になる。

1. **走査対象**: ライブ `.planning/phases/*/` と、アーカイブ `.planning/milestones/v{X.Y.Z}-phases/*/` のうち
   **バージョンが v1.9.0 以上**のもの
2. **要件**: 各フェーズディレクトリに `*-VALIDATION.md` がちょうど 1 件あり、frontmatter が `status: validated` であること
3. **空虚 PASS ガード**: 走査したフェーズ件数が 0 なら FAIL（loto と同じ思想）
4. **レガシー除外の機械固定**: 除外対象を `{v1.4.0, v1.6.0, v1.7.1, v1.8.0}` とハードコードし、
   **実ディレクトリ集合と完全一致すること自体を assert** する。新しいマイルストーンが
   v1.9.0 未満の版番で現れたり、除外リストが黙って増えたりすると FAIL する
   （loto の「遡及生成は見送り確定」と同じ判断を、コメントではなくテストで固定する）
5. **PyYAML 非依存**: frontmatter から `status` スカラーだけを読む最小パーサを自前で持つ。
   新規依存を増やさない（B-3 の回避 + PageFolio の依存最小方針）
6. **self-test**: `tmp_path` の合成ツリーで「draft を検知する / validated を誤検知しない /
   走査 0 件を FAIL にする / VALIDATION.md 欠落を検知する / status キー欠落を validated と同一視しない」を固定

## タスク

### Task 1: `tests/test_gsd_dod.py` を新設

- **files**: `tests/test_gsd_dod.py`（新規）
- **action**: 上記設計で実装。ruff の `S101`（assert）は `tests/**` で除外済みのため問題ない
- **verify**: 実リポジトリに対して pass し、走査件数が 3（v1.9.0 の 3 フェーズ）であること。self-test が全件 pass
- **done**: `pytest tests/test_gsd_dod.py` がグリーン

### Task 2: `.planning/PROJECT.md` に `## フェーズ完了 DoD` 節を追加

- **files**: `.planning/PROJECT.md`
- **action**: `## ブランチ運用` の直後・`## Key Decisions` の前に新設（loto/numbers と同じ位置）。
  DoD 本文・強制点・許容条件・適用範囲・red になったときの対処・loto との設計差分を記載
- **verify**: 節が規定位置にあり、v1.9.0 以降が適用範囲であることが明記されていること
- **done**: 3 プロジェクトが同型の DoD 節を持つ

### Task 3: 検証

- **action**: `ruff check . && ruff format --check .` と `pytest`
- **done**: リリースゲート合格（テスト件数は 1404 → 増加する）

## 確定事項

- **既存 VALIDATION.md の遡及修正は行わない**（loto と同じ判断）。v1.9.0 未満は除外し、その事実をテストで固定する
- **合格条件を緩めない**: `nyquist_compliant` は一切参照しない（強制するのは「検証を走らせたこと」）
- `requirements.txt` に新規依存を追加しない

## スコープ外

- v1.9.0 未満のフェーズへの遡及的な `VALIDATION.md` 生成・status 修正
- `.planning/ROADMAP.md` の構造変更（`## Progress` にフェーズ単位の表を追加する等）
- CI ワークフローの新設（PageFolio に `.github/workflows/` は存在しない。ゲートは `pytest` 経由で発火）
