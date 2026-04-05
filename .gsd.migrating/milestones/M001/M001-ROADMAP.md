# M001: 

## Vision
PageFolio (v0.9.5) に対して、ユニットテストの基盤を構築する。テストが無い現状から、主要ロジック・ユーティリティ関数・PDF操作のコアパスをカバーするテストスイートを整備し、今後の機能追加・リファクタリングを安全に行える品質基盤を確立する。

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | テスト基盤 + ユーティリティ関数テスト | low | — | ✅ | pytest tests/test_utils.py が全てパスする |
| S02 | PDF操作テスト | medium | S01 | ✅ | pytest tests/test_pdf_ops.py が全てパスする |
| S03 | プラグインシステムテスト + 最終検証 | low | S01 | ✅ | pytest tests/ -v が全テストパス。ruff もクリーン |
