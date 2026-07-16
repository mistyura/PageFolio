---
phase: 05
slug: blob-shortcutsdialog
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-16
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| （なし） | 05-01/05-02: 単一プロセス内・ローカルデスクトップアプリの純ロジック/Tkinter描画層改修。ネットワーク/認証/永続化境界を跨がない | なし |
| プロセス→ファイルシステム | 05-03: undo Blob は tempfile へ平文退避（v1.7.0 から不変）。暗号化はスコープ外（V14-D-02 と整合） | ローカル一時ファイル（PDF ページバイト列） |
| キーボード入力→アプリコマンド | 05-04: ショートカットキー押下がアプリコマンド発火へ渡る境界。既存 `build_keysym_from_event`/`find_duplicate_binding` の検証を踏襲・新規入力経路は増やさない | キーイベント（keysym） |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Denial of Service | thumb_cache の無制限成長（メモリ枯渇・V180-PERF-02） | medium | mitigate | `pagefolio/thumb_cache.py` に `LruCache(maxsize)` を新設（05-01） | closed |
| T-05-02 | Tampering | selected_pages への窓ローカル添字混入（選択状態の破壊） | medium | mitigate | `pagination.py` 純関数（`to_global` 等）経由でのみ index 変換・`tests/test_selection_invariant.py`（21テスト）で不変条件を回帰検証（05-01） | closed |
| T-05-03 | Denial of Service | thumb_cache 無制限成長によるメモリ枯渇（V180-PERF-02） | medium | mitigate | `pagefolio/app.py:189` で `self.thumb_cache = LruCache(THUMB_CACHE_MAX)`（`THUMB_CACHE_MAX=300`）を配線し上限を実効化（05-02） | closed |
| T-05-04 | Tampering | selected_pages への窓ローカル添字混入（選択破壊） | medium | mitigate | `_render_visible_thumbs`/`_visible_local_range` は選択状態を書き換えず、`pagination.py` 純関数経由でのみ可視範囲・描画順序を計算（05-02） | closed |
| T-05-05 | （信頼性・STRIDE外） | デバウンス後の陳腐化描画が新しい窓を上書き | low | mitigate | `_thumb_gen` 世代ガードをデバウンスコールバック（`_render_visible_thumbs`）にも適用し gen 不一致時に破棄（`pagefolio/viewer.py:391`）（05-02） | closed |
| T-05-06 | Denial of Service | Blob 一時ファイル残留（ディスク容量枯渇） | medium | mitigate | `MemBlob`/`FileBlob` に `_released` フラグ + `__del__` によるリーク検出ログ + ベストエフォート unlink。既存 purge/atexit 二段回収と併用。tmpdir 残留監視テストで回帰検証（05-03） | closed |
| T-05-07 | Denial of Service | Windows AV スキャンによる `os.unlink` PermissionError で解放失敗 | medium | mitigate | 既存 `contextlib.suppress(OSError)` を維持（`pagefolio/undo_store.py:107`）+ purge/rmtree(ignore_errors) 二段回収。PermissionError mock 回帰テストで検証（05-03） | closed |
| T-05-08 | （信頼性・STRIDE外） | `__del__` がインタプリタ終了時に例外を伝播 | low | mitigate | `sys.is_finalizing()` 早期 return + `except Exception as e:` 握り潰し（PEP 442）を `MemBlob`/`FileBlob` 双方に実装（05-03） | closed |
| T-05-09 | Cryptography | undo Blob の平文一時ファイル退避 | low | accept | v1.7.0 から継続の設計。ローカル単一ユーザーアプリで暗号化は Out of Scope（V14-D-02 セッション限定・非永続方針と整合）。本フェーズでは変更しない | closed |
| T-05-10 | Tampering | 入力系ウィジェット編集中に修飾なし単キーショートカット（`<Delete>` 等）が誤発火しページ削除等の意図しない破壊操作を起こす | medium | mitigate | `should_suppress_for_focused_input` フォーカスガードで入力系（Entry/TEntry/Spinbox/TSpinbox/Text）フォーカス中の修飾なし発火を抑止。Ctrl/Alt 組合せは従来どおり発火（`pagefolio/app.py:91,94`）（05-04） | closed |
| T-05-11 | （信頼性・STRIDE外） | `root.focus_get()` が `None` を返すケースでガード判定が例外化 | low | mitigate | `_make_guarded_handler` 内で `focused.winfo_class() if focused else ""` により None を空文字列へフォールバックし、純関数は非入力系扱いで False を返す（`pagefolio/app.py:266-267`）（05-04） | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

**コードレビュー(`05-REVIEW.md`)関連の残課題（脅威登録外・非ブロッキング）:** WR-02（`_INPUT_WIDGET_CLASSES` が `TCombobox` を含まない）はT-05-10の緩和を無効化しない軽微な網羅性ギャップとして記録済み。次フェーズ以降での改善候補。

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-09 | undo Blob の平文一時ファイル退避は v1.7.0 から継続する設計。ローカル単一ユーザーデスクトップアプリであり、暗号化は V14-D-02（APIキー同様セッション限定・非永続方針）と整合する既存の受容済みリスク。本フェーズのスコープ（リーク検出強化）では対象外 | プロジェクト方針（V14-D-02 踏襲） | 2026-07-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-16 | 11 | 11 | 0 | orchestrator（L1 grep-depth・register_authored_at_plan_time=true・asvs_level=1 短絡ルール適用・監査エージェント未起動） |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-16
