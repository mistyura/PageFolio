---
phase: 06-release-validation
plan: "07"
subsystem: testing
tags: [release-scope, evidence-audit, W11]
requires:
  - phase: 06-04
    provides: 世代4の保護・接続準備と履歴
provides:
  - 承認済みW11の2カードだけを未確認の対象外として扱う固定監査契約
  - 全110カードを保持した必須108件と対象外2件の台帳
affects: [06-08, 06-05, 06-06]
tech-stack:
  added: []
  patterns: [固定承認と全カード集合の読取専用照合]
key-files:
  created: [06-RELEASE-SCOPE.json, 06-W11-SCOPE-APPROVAL.md]
  modified: [tests/release_uat_support.py, tests/test_release_uat_support.py, tests/test_release_contract.py, 06-MANUAL-EVIDENCE.json, 06-UAT.md]
key-decisions:
  - W11-B-20261028の2行だけをnot-run/deferredとし、他108行と品質・安全条件を必須のまま保持する。
  - 旧形式の全行必須契約を維持し、部分移行・未知scope・偽passを拒否する。
requirements-completed: [V110-QA-01, V110-QA-02]
duration: 30min
completed: 2026-10-28
coverage:
  - id: scope-audit
    description: 承認・固定集合・全modeの正負監査
    verification:
      - kind: integration
        ref: tests/test_release_uat_support.py#TestReleaseScope
        status: pass
    human_judgment: false
  - id: scope-ledger
    description: 31ケース110カードの保持と108必須/2対象外
    verification:
      - kind: unit
        ref: tests/test_release_contract.py#TestCaseCoverage
        status: pass
    human_judgment: false
---

# Phase 06 Plan 07: W11の承認済み限定scope

固定承認・全110カードを照合し、W11の未確認2行を人手passへ変換せず分離した。

## 完了内容

- `validate_release_scope` を全6監査modeと直接の手動/引渡し監査へ接続。固定ID・承認文書hash・原文・正確な2キー・台帳参照hashを検証する。
- コードに固定した31ケース/110カードで欠落・重複・余分・supersededによる必須行隠蔽を拒否する。必須/対象外/合格/未実施/失敗/blockedを別集計する。
- 旧形式は従来の全行必須。`require-pass W11` はrequired=0/deferred=2と報告し、人手passにしない。
- 既存の観測・W01保留attempt・W05b準備・世代履歴・hashを保持。実台帳の構造監査は成功、必須108件は全てnot-run、W11の2件もnot-runのまま。

## 検証

- RED 1: 承認済みfixtureが従来監査で拒否されることを確認（1 failed/3 passed）。
- GREEN 1: 新scopeと既存監査38 passed。
- RED 2: 全mode負例147 passed、実台帳未適用の追加契約1 failedを確認。
- 統合時の既存fixtureでscope参照ファイル不足を検出し、隔離copyへ承認文書とscopeを含めて修正。
- 最終の単一全件: **2231 passed / 2 warnings / 503.09秒 / exit 0**。failed/errors/skipped=0、入力151件のbefore/after不変。証拠: `06-07-evidence/native-files-20261028/`。
- 全体Ruff check/format/再check、AST成功。formatはディレクトリwalkで断続的なOSアクセス拒否が発生したため、Ruff自身の列挙した同一全140 Pythonファイル（欠落/追加0）を明示して実行した。対象縮小・ルール変更なし。元の失敗と一覧を`06-07-evidence/`に保持。

## コミットと差分の保全

製品差分: `460c01d`。既存dirty/indexを保全するため、監査コード・試験・固定承認と、HEAD台帳へ適用するscope欄だけを選択してコミットした。CR-03や世代4変更は混入させていない。選択処理は`06-07-stage.cjs`。ステージ差分チェック成功。

## Deviations from Plan

- 必須の全件pytestをまとめて完走してから、2タスクの関連差分を1つのコミットにした。既存差分の混入を避けるための選択stageを実施。
- Ruffのディレクトリ探索時OSエラーに対し、同一全140ファイルへの明示指定で同じ整形を実施。成功に置換せず元のエラーを保存した。
- PowerShell生成JSONにBOMが付いた移行前の構造監査失敗を修正し、UTF-8のscopeと参照hashを再作成した。

## 次の実行

06-08で配布文書の保証範囲、現行品質、freeze、新世代の実2build・保護・接続を実施。その後06-05→06-06で必須108件の本受入へ進む。共通要件の完了は後続計画と独立ゲートを待つ。Phase完了・出荷許可はfalse。

## Self-Check: PASSED

成果物と全件証拠を確認。製品コミットあり、固定scopeの構造監査成功。これは監査契約の完成であり、人手受入の完了ではない。
