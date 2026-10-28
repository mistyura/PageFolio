---
phase: 06-release-validation
plan: "08"
subsystem: distribution
tags: [release-scope, native-build, connection-preparation]
requires:
  - phase: 06-07
    provides: W11承認と108必須/2対象外の固定監査契約
provides:
  - 単一ログインセッション保証を含む世代5の実配布候補
  - 入力freezeと実2build、保護・障害・OCR接続の原証拠
  - 履歴を保持した必須108件not-runと対象外2件not-runの台帳
affects: [06-05, 06-06]
tech-stack:
  added: []
  patterns: [旧世代保全と同一入力の実2build]
key-files:
  created: [06-08-BUILD-RAW.json, 06-08-SCOPE-FREEZE.json, 06-08-CHECKPOINT.md]
  modified: [README.md, distribution/はじめに.md, 開発履歴.md, tests/test_release_contract.py, 06-BUILD-EVIDENCE.json, 06-PROTECTION-EVIDENCE.json, 06-MANUAL-EVIDENCE.json, 06-UAT.md, 06-UAT-PREPARATION.md]
key-decisions:
  - 配布文書に単一ログインセッション保証と別セッション動作未確認を明記する。
  - 接続準備と本受入を分離し、W11以外の108行を免除しない。
requirements-completed: [V110-DIST-01, V110-DIST-02, V110-DIST-03, V110-QA-01, V110-QA-02, V110-QA-03]
completed: 2026-10-28
coverage:
  - id: scoped-distribution
    description: 文書・freeze・実2buildの同一入力
    verification:
      - kind: integration
        ref: 06-08-evidence/final-audits.json
        status: pass
    human_judgment: false
  - id: native-connection-preparation
    description: 実EXEのOCR接続と同確認画面への自動復帰
    verification:
      - kind: integration
        ref: 06-08-session-w05b-modal.json
        status: pass
    human_judgment: true
---

# Phase 06 Plan 08: 保証範囲を反映した世代5の配布準備

単一ログインセッション保証の文書を同梱し、実2buildと保護・接続準備を完了した。これは本受入や出荷承認ではない。

## 完了内容

- 文書契約のRED→GREENを実施。README/同梱ガイド/履歴に保証範囲と別セッション各1画面・同セッション復帰・元状態維持が未確認であることを記載した。
- freeze65入力digest `ae08f9422ee0010bbc827720aae0c1873552d0dd51b63ddf4960baeba036658d`。初回run `1e90bd8bfda0479f9f9593737f809306`、再build run `c04825cf60054565970f9a6a997523d3` が成功。同梱ファイル・原本保持を照合し、第三buildなし。
- 最終EXE `66be5df663e333057c5c3cde02180857f930d2433e377f69c2838432d49a19d4`、tree `b1e55ca6efa3a7bafb4dec9ea9fa2c715dfca6f538ba906632058f912f575d85`。旧世代のbinary/hash/証拠を原本のまま保持した。
- 保護3名、起動時保持3条件、更新衝突/非衝突、X01〜X05外部条件を記録。X04の初回保存失敗後の画面保持と強制回収は観測のまま残し、正常終了passへ変更していない。
- ocr-single `18986e4dd7b341bd81d4a6d4b0da8afd`、W05b `af629ccbe3514294a7814e1de2e98463` を実測。W05bは同確認HWND3867420への自動復帰・いいえ・同1POST完了を人の回答と50ms観測で照合。両runは利用者の通常終了、残存ownerなし、配布元不変。
- 31ケース110行を保持し、必須108行not-run、W11対象外2行not-run。本受入の人手passは0件のまま。

## 検証

- 文書/版/ガイド/buildの指定試験85 passed。
- build前の単一全件2232 passed / 2 warnings / 607.00秒。`native-docs-20261028`。
- 台帳確定後の指定契約192 passed / 1 warning / 49.22秒。
- 台帳確定後の単一全件 **2232 passed / 2 warnings / 513.66秒 / exit0**。failed/errors/skipped=0、151入力の前後hash不変。`06-08-evidence/native-ready-20261028`。
- 全体Ruff check・同一全140Pythonファイルのformat・再check・AST成功。07で記録した列挙時OSエラーを理由とする明示全ファイル方式を維持し、対象縮小・ルール変更なし。
- 最新品質参照でbuild-only/preparation-only/allow-pendingの全監査exit0。allow-pendingはstructural_only=true/task_ready=false、phase_complete/release_allowed=false。
- Phase04 21/21、Phase05 23/23の独立再検証を確認。CR-03は修正済み。旧原因未確定の回帰条件や本受入を解除した意味ではない。

## コミットと差分保全

- CR-03の担当差分を `e13a00b` に分離。
- 本計画の配布文書・試験・世代5の台帳/原証拠を `8e83658` に記録。
- `06-08-stage.cjs` で既存dirty/indexを保全。旧v1.10.1の別件履歴や別件製品変更は自動commitしていない。build時のcommit+dirtyhashはfreeze原文のままで、後続commitに付け替えていない。

## Deviations from Plan

- update終了直前0.948秒にfaultsを開始し、共有rawのupdate節が後から上書きされた。保存済みupdate/faults原本の共通節一致を確認し、update節を無改変で合成。両原本・出典SHA・merge_provenanceを保持し、再観測や推測値は使っていない。以後、前段完了後に次段を開始した。
- W05b初回は自動復帰後約2.4秒で利用者が観測終了前にChatGPTへ手動切替。`peer_returned_to_modal=false`と原本/補足を保持。自動復帰後10秒無操作を明示した別runだけで成立を確認した。製品・driver・期限・判定条件は変更していない。
- 2タスクの関連台帳と原証拠は、波末の全件品質完走後にまとめてコミットした。
- 原記録のCRLFと保全旧UATの末尾空行は整形せず保持。cr-at-eolで確認した通常編集ファイルのwhitespace問題0。`staged-whitespace.json`に原記録のみの検出を記録した。

## 次の実行

06-05→06-06で必須108件の本受入へ進む。共通要件の完了は後続計画・独立ゲートを待つ。W11の2行は未確認の保証対象外であり、人手passではない。出荷許可はfalse。

## Self-Check: PASSED

担当成果物・保存原本・2build・単一全件・準備監査・担当コミットを照合済み。本計画の準備は完了、本受入と出荷は未完了。
