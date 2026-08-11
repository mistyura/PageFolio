---
gsd_summary_version: 1.0
quick_id: 260812-and
slug: dod
description: フェーズ完了 DoD の機械ゲートと PROJECT.md の DoD 節を追加
date: 2026-08-12
status: complete
branch: quick/260812-and-dod
---

# Quick Summary 260812-and — フェーズ完了 DoD の機械ゲート追加

## 結果

3 プロジェクト比較（260812-9tv）の**最後の未解消差分 #4 を解消**。#1〜#5 がすべて完了した。

**loto 実装の直接移植は不可能**だったため、思想（機械ゲートで強制・空虚 PASS を許さない・アーカイブで回避させない）を維持しつつ走査の入口を再設計した。

## loto 実装が移植できなかった 3 つの前提

| # | loto の前提 | PageFolio の実態 |
|---|---|---|
| B-1 | `## Progress` 表が `Phase` 列と `Status` 列を持つ | `## Progress` は**マイルストーン単位**の表（`Milestone / Phases / Plans / Status / Shipped`）。**`Phase` 列が無い**。フェーズ内訳は `## Phases` の `<details>` 内のチェックボックス行 |
| B-2 | フェーズ番号がプロジェクト全体で連番（22→30） | **マイルストーンごとに 1 起点へリセット**（プロジェクト方針）。`03-*` は v1.6.0 / v1.7.1 / v1.8.0 / v1.9.0 の 4 箇所に存在し、番号から一意に解決できない |
| B-3 | `yaml.safe_load` が使える | **PyYAML 未インストール**（`requirements.txt` に無く `import yaml` が失敗） |

## 設計（PageFolio 版）

**走査の入口を ROADMAP パースからフェーズディレクトリ列挙へ差し替えた。** これにより B-1・B-2 が構造的に無害になる。

1. **走査対象** — ライブ `.planning/phases/*/` と、`.planning/milestones/v{X.Y.Z}-phases/*/` のうち**バージョンが v1.9.0 以上**のもの。`milestones/` 直下（`v*-phases/` を挟まない配置）は対象外
2. **要件** — 各フェーズに `*-VALIDATION.md` がちょうど 1 件、frontmatter が `status: validated`
3. **空虚 PASS ガード** — 走査件数 0 は FAIL（loto と同じ思想）
4. **レガシー除外の機械固定** — 除外集合 `{v1.4.0, v1.6.0, v1.7.1, v1.8.0}` を**実ディレクトリと突き合わせて assert**。除外を増やすには定数の明示的な書き換えが必要で、黙って増やせない
5. **PyYAML 非依存** — frontmatter の `status` スカラーだけを読む最小パーサを自前で持つ。新規依存ゼロ
6. **バージョン比較は数値タプル** — 文字列比較だと `v1.10.0 < v1.9.0` と誤判定するため。self-test で固定

## なぜ v1.9.0 以降に限定したか

既存データを全件調査した結果、**v1.9.0 以外は `status: validated` になっていない**。

| マイルストーン | フェーズ数 | VALIDATION.md の status |
|---|---|---|
| v1.4.0 | 4 | validated / validated / **complete** / **なし** |
| v1.6.0 | 4 | **なし** / **approved** / **approved** / **draft** |
| v1.7.1 | 4 | **approved** / **ready** / **draft** / **planned** |
| v1.8.0 | 6 | **approved** / **draft** / **ready** / **draft** / validated / **draft** |
| **v1.9.0** | **3** | **validated / validated / validated** |

v1.9.0 未満の `*-VALIDATION.md` は `/gsd-validate-phase` の出力ではなく別種のドキュメント（プラン検証等）で status 語彙も揃っていない。**全件を対象にするとゲートは導入直後に恒常 red になる。** 遡及的な生成・修正は行わない方針（loto の「v0.17.0 以前への遡及生成は見送り確定」と同じ判断）としたうえで、除外が抜け穴にならないよう #4 のガードを置いた。

## 変更内容

### `tests/test_gsd_dod.py`（新規・6 テスト）

| テスト | 役割 |
|---|---|
| `test_completed_phases_are_validated` | 本ゲート。適用範囲の全フェーズが validated であること + 走査 0 件を FAIL |
| `test_legacy_exclusions_match_repository` | 除外集合が実リポジトリと一致すること（抜け穴封じ） |
| `test_dod_gate_detects_unvalidated_phase` | 合成ツリー self-test — draft 検知 / validated 誤検知なし / 範囲外を走査しない / v1.10.0 の版番比較 / ライブ phases / milestones 直下の除外 / 番号リセット併存 / 順序安定 |
| `test_dod_gate_rejects_empty_and_malformed` | 走査 0 件・VALIDATION.md 欠落・2 件重複・frontmatter 無し・status キー欠落を違反として扱う |
| `test_status_parser_handles_quotes_and_nesting` | PyYAML 非依存パーサの引用符処理とネスト非拾い |
| `test_milestone_version_parsing` | 版番解釈と数値タプル比較 |

### `.planning/PROJECT.md`

`## ブランチ運用` の直後・`## Key Decisions` の前に `## フェーズ完了 DoD` 節を新設（loto/numbers と同じ位置）。DoD 本文・強制点・許容条件（`nyquist_compliant: false` を許容）・適用範囲・除外理由・loto との設計差分・red 時の対処を記載。

### `CLAUDE.md`

リリースゲート節のテスト件数を 1404 → **1410** へ同期。

## 検証

- `pytest tests/test_gsd_dod.py` → 6 passed（0.18s）
- 実リポジトリに対する走査が**非空虚**であることを手動確認 — 3 件（`v1.9.0-phases/01-safety-rollback` / `02-ocr-openai-chatgpt` / `03-qa-release-gate`）、違反 0 件
- `ruff check .` → All checks passed（初回 E501 を 1 件検出したため修正済み）
- `ruff format --check .` → 91 files already formatted
- `pytest -q` → **1410 passed**（1404 + 新規 6・失敗 0・ERROR 0・クラッシュなし＝リリースゲート合格。症状①の再発なし）

## 3 プロジェクト比較の最終状態

| # | 差分 | 状態 |
|---|---|---|
| 1 | `config.json` の `git` 3 キー | ✅ 260812-9tv |
| 2 | `PROJECT.md` の `## ブランチ運用` 節 | ✅ 260812-9tv |
| 3 | `PROJECT.md` の `## Constraints` 節 | ✅ 260812-a8u |
| 4 | `## フェーズ完了 DoD` + 機械ゲート | ✅ **本タスク** |
| 5 | `claude_md_assembly` | ✅ 260812-adk |
| 6 | numbers `main` への反映 | — numbers 側の `/gsd-complete-milestone` で自動解消 |

## スコープ外

- v1.9.0 未満のフェーズへの遡及的な `VALIDATION.md` 生成・status 修正
- `.planning/ROADMAP.md` の構造変更（`## Progress` へフェーズ単位の表を追加する等）
- CI ワークフローの新設（PageFolio に `.github/workflows/` は無く、ゲートは `pytest` 経由で発火する）
- `requirements.txt` への依存追加（PyYAML 非依存で実装したため不要）

## 申し送り

- **次マイルストーン（v1.10.0）からは、フェーズを完了扱いにする前に `/gsd-validate-phase` の実走が必須**になる。走らせないまま進めると `pytest` が red になり、リリースゲートを通過できない
- ゲートが red になったら該当フェーズへ `/gsd-validate-phase <番号>` を実走する。ギャップが残っていても「Skip — mark manual-only」で `status: validated` へ昇格できる（`nyquist_compliant: false` は許容）
- **除外集合を増やしたくなった場合**は `tests/test_gsd_dod.py` の `LEGACY_EXCLUDED_MILESTONES` を明示的に書き換え、根拠を PROJECT.md の DoD 節へ記録すること。ガードがあるため黙っては増やせない
- 3 プロジェクトの整合作業はこれで完了。以降の差分は各プロジェクトが独自に進化した結果なので、揃えるかどうかは都度判断する
