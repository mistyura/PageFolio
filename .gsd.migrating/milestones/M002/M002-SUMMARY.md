---
id: M002
title: "モジュール分割リファクタリング"
status: complete
completed_at: 2026-03-31T10:25:38.862Z
key_decisions:
  - MixinパターンでPDFEditorAppを5モジュールに分割
  - 後方互換を__init__.pyのre-exportで維持
  - テストのmonkeypatch対象を内部モジュールに変更
key_files:
  - pagefolio/__init__.py
  - pagefolio/app.py
  - pagefolio/constants.py
  - pagefolio/settings.py
  - pagefolio/plugins.py
  - pagefolio/ui_builder.py
  - pagefolio/file_ops.py
  - pagefolio/page_ops.py
  - pagefolio/viewer.py
  - pagefolio/dnd.py
  - pagefolio/dialogs.py
  - pagefolio/file_drop.py
  - pagefolio/__main__.py
  - pagefolio.py
  - tests/test_utils.py
  - tests/test_plugins.py
  - CLAUDE.md
  - 開発履歴.md
lessons_learned:
  - __init__.pyでre-exportしても、内部モジュール内の関数呼び出しには効かないため、テストのmonkeypatchは内部モジュールを直接指定する必要がある
  - Mixinパターンは大規模クラスの分割に効果的だが、循環importを避けるために遅延importが必要な場合がある
---

# M002: モジュール分割リファクタリング

**pagefolio.py 単一ファイルを13モジュールのパッケージに分割、全78テストパス**

## What Happened

pagefolio.py（3,136行）を pagefolio/ パッケージ（13モジュール）に分割するリファクタリングを実施した。PDFEditorApp（1,800行）は5つの Mixin に機能分離し、各モジュールを最大595行に保った。後方互換は __init__.py で確保。テスト8件のパッチ対象修正を経て78件全パス。CLAUDE.md・開発履歴.md・KNOWLEDGE.md を更新し、バージョンを v0.9.6 に更新。

## Success Criteria Results

- [x] pytest 78件全パス: 78 passed in 0.81s\n- [x] ruff クリーン: All checks passed, 20 files formatted\n- [x] python pagefolio.py 起動: エントリーポイント確認\n- [x] import pagefolio 後方互換: v0.9.6 出力確認\n- [x] 各モジュール600行以下: 最大595行(dialogs.py)

## Definition of Done Results

- [x] pagefolio/ パッケージが正しく構成されている\n- [x] pytest 78件全パス\n- [x] ruff クリーン\n- [x] python pagefolio.py が起動する\n- [x] CLAUDE.md・開発履歴.md が更新されている

## Requirement Outcomes

既存 R001-R013 の動作を維持。要件ステータスの変更なし。

## Deviations

None.

## Follow-ups

None.
