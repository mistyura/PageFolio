# M003: 

## Vision
PageFolio v0.9.6 のコード品質を包括的に改善する。プラグインの不整合修正、例外処理の統一、テストカバレッジ向上、コード整理を通じて、v1.0 リリースに向けた堅牢な基盤を確立する。

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | プラグイン不整合修正 | low | — | ⬜ | plugins/page_info.py が pagefolio パッケージから正しく import し、PluginManager で検出可能 |
| S02 | 例外処理の統一・エラーハンドリング改善 | medium | S01 | ⬜ | except Exception: (as e なし) がゼロ、例外情報がログ出力される |
| S03 | テストカバレッジ強化 | medium | S01, S02 | ⬜ | settings.py 90%+、plugins.py 85%+、page_ops/file_ops のロジック部分にテスト追加 |
| S04 | ドキュメント更新・バージョンアップ | low | S01, S02, S03 | ⬜ | 開発履歴.md に全変更が記録され、バージョンが v0.9.7 に更新 |
