# M002: 

## Vision
pagefolio.py 単一ファイル（3,136行）を pagefolio/ パッケージに分割し、保守性を向上させる。既存テスト78件・ruff・プラグインがすべて動作することを保証する。

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | パッケージ構造作成 + コード分割 | high | — | ✅ | pagefolio/ パッケージが存在し、python -c 'import pagefolio' が成功する |
| S02 | テスト・プラグイン・ドキュメント修正 + 最終検証 | low | S01 | ✅ | pytest 78件全パス + ruff グリーン + python pagefolio.py 起動確認 |
