# Decisions

（プロジェクト初期化時点では未記録。今後のマイルストーン作業で追記される。）

---

## Decisions Table

| # | When | Scope | Decision | Choice | Rationale | Revisable? | Made By |
|---|------|-------|----------|--------|-----------|------------|---------|
| D001 |  | architecture | pagefolio.py 単一ファイル構成からモジュール分割への移行方針 | pagefolio/ パッケージに分割。PDFEditorApp は Mixin パターンで 5 モジュールに分離。後方互換を __init__.py で維持。 | 3,136行の単一ファイルは保守性が低い。ユーザーの要望でモジュール分割を実施。Mixin パターンで PDFEditorApp を機能グループ別に分離し、各モジュールを 200-400 行に保つ。 | Yes | collaborative |
