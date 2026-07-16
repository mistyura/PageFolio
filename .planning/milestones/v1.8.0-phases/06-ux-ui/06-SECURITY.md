---
phase: 06
slug: ux-ui
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-16
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| user ↔ メインウィンドウ UI（ローカル） | トースト表示・再試行操作 | なし（デスクトップ単一プロセス、ネットワーク境界を越えるデータ経路はない） |
| user ↔ ダイアログ UI（ローカル） | スクロール操作・フォント表示（plugin.py/ocr_dialog.py/about.py） | なし（純粋な Tkinter ウィジェット配置） |
| user ↔ Undo/Redo エンジン（ローカル・fitz.Document 操作） | insert_redo の復元アクション | なし（永続化層・外部サービス・ネットワーク非関与） |
| ドキュメント記録（開発履歴.md / PROJECT.md） | 実行時コードに影響しない記録整合性のみ | なし |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01 | Information Disclosure | `ToastManager.show` が `str(e)`/`err_save_msg.format(e=e)` で例外文言（ファイルパス等を含みうる）を表示 | low | accept | 既存 `messagebox.showerror` と同一の情報を非モーダルで再表示するのみで新規の情報露出経路を追加しない | closed |
| T-06-02 | N/A | `plugin.py`/`ocr_dialog.py`/`about.py` のスクロール・フォント是正 | low | accept | スクロール/フォント是正は Tkinter ウィジェット配置のみで新規の入力面・ネットワーク経路・機密データ処理を持たない | closed |
| T-06-03 | Tampering（データ整合性） | `file_ops._restore_state` の `insert_redo` デルタ復元 | low | mitigate | `insert_redo` を `delete_redo` 対称パターンへ修正し、insert→undo→redo→undo 4手往復のページ内容整合性を回帰テスト（`tests/test_pdf_ops.py::TestInsertUndoRedo::test_insert_undo_redo_undo_roundtrip`）で担保。修正範囲を `insert_redo` ブロックのみに限定し他 op の対称性を保持（D-17）。実装・テスト合格を確認済み | closed |
| T-06-SC | Tampering | npm/pip/cargo installs | low | accept | 本フェーズは新規パッケージを一切インストールしない（RESEARCH Package Legitimacy Audit: none・[SLOP]/[SUS] なし）。標準ライブラリ tkinter のみ | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-01 | 例外文言の表示は既存 `messagebox.showerror` 経路と同一の情報量であり、トースト化によって新規の情報露出経路は追加されない。severity low・block_on=high のため非ブロッキング | Phase 06 Planner（PLAN.md threat_model） | 2026-07-16 |
| AR-06-02 | T-06-02 | スクロール/フォント是正は Tkinter ウィジェット配置の変更のみで、STRIDE 該当カテゴリなし。severity low | Phase 06 Planner（PLAN.md threat_model） | 2026-07-16 |
| AR-06-SC | T-06-SC | 本フェーズはサプライチェーン新規依存を追加しない | Phase 06 Planner（PLAN.md threat_model） | 2026-07-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-16 | 4 | 4 | 0 | /gsd-secure-phase（register_authored_at_plan_time=true, ASVS L1 — short-circuit, no auditor spawn required） |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-16
