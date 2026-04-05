# S02: テスト・プラグイン・ドキュメント修正 + 最終検証

**Goal:** テスト・プラグイン・CLAUDE.md・開発履歴.md を更新し、全検証をパスする
**Demo:** After this: pytest 78件全パス + ruff グリーン + python pagefolio.py 起動確認

## Tasks
- [x] **T01: ドキュメント更新 + v0.9.6 + 最終検証パス** — CLAUDE.md・開発履歴.md・KNOWLEDGE.md をモジュール分割に合わせて更新し、最終検証を実施する
  - Estimate: 10min
  - Files: CLAUDE.md, 開発履歴.md, .gsd/KNOWLEDGE.md
  - Verify: ruff check . && ruff format --check . && pytest tests/ -v
