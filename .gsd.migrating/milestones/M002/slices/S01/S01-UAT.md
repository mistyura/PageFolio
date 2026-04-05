# S01: パッケージ構造作成 + コード分割 — UAT

**Milestone:** M002
**Written:** 2026-03-31T10:22:42.320Z

## S01 UAT: パッケージ構造作成 + コード分割\n\n- [x] `python -c \"import pagefolio; print(pagefolio.APP_VERSION)\"` → v0.9.5\n- [x] `ruff check . && ruff format --check .` → グリーン\n- [x] `pytest tests/ -v` → 78件全パス\n- [x] 全モジュール600行以下\n- [x] 循環インポートなし
