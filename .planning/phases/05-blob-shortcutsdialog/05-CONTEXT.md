# Phase 5: 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正） - Context

**Gathered:** 2026-07-16
**Status:** Ready for planning

<domain>
## Phase Boundary

大量ページ PDF でもサムネイル描画が高速に保たれ（既存 `pagination.py` 窓表示の外層契約 local↔global 変換は不変）、`thumb_cache` が LRU で有界化され、Blob ライフサイクルのリークが検出可能になり、ShortcutsDialog の表示残留（WR-01）・単キー入力衝突（WR-02）が解消される。機能追加ではなく、既存機能の性能・堅牢性・既知バグの仕上げフェーズ。

対象要件: V180-PERF-01〜03（窓内サムネイルの可視範囲のみ実体化・`thumb_cache` LRU 化・`selected_pages` 不変条件の回帰テスト保証）・V180-ROBUST-01（Blob リーク検出強化 + Windows AV 衝突回帰テスト）・V180-ROBUST-03（WR-01/WR-02 解消）。

**スコープ外:** 連続スクロール型の本格仮想化＝react-window 相当のウィジェット再利用（PERF-F01・v2 送り確定済み）・ページネーション窓表示の外層契約変更・LRU 上限のユーザー設定公開・通知UX/UI一貫性監査（Phase 6）・バッチ OCR 関連（Phase 4 完了済み）。

</domain>

<decisions>
## Implementation Decisions

### 仮想化の実体化方式（PERF-01）
- **D-01:** 「可視範囲のみ実体化」は**画像遅延レンダリング型**で実現する。ウィジェット（Frame/ページ番号ラベル・イベント bind）は現行どおり窓内全生成を維持し、重い `get_pixmap` のみ可視範囲を優先実行、窓外はスクロールで見えた時にレンダリングする。ウィジェット再利用型は不採用（落とし穴2「ウィジェット再利用とキャッシュの責務混同」を構造的に回避し、PERF-F01＝v2 送りの本格仮想化との境界を明確に保つ。ウィジェット数は窓サイズ ≤100 で既に有界）。
- **D-02:** スクロール中のレンダリングは**デバウンス型**。スクロール停止後（例: 150ms 無操作）に可視範囲をレンダリングする。`thumb_cache` ヒット分はスクロール中も即時表示し、ミス時のみプレースホルダ表示（PITFALLS の UX 注意「チラつきによる別ページ誤クリック」対応）。既存 `_thumb_gen` 世代ガードと併用して陳腐化描画を破棄する。
- **D-03:** 可視範囲の描画完了後、**アイドル時間に窓内の残りを先読みレンダリングする**（可視範囲 → 窓内残りの優先度付き。現行 `after()` 連鎖の優先度付き化）。総仕事量は現行と同じだが体感を大幅改善。メモリは LRU（D-05〜D-08）で有界化されるため安全。
- **D-04:** PERF-03 の回帰テストは**プロパティ風テスト＋ユニットの二本立て**。seed 固定の `random.Random` によるランダム操作列（選択/スクロール/D&D）で 500+ ページ相当の `selected_pages` 全ページインデックス不変条件を検証する。hypothesis 等の新規依存は追加しない（V14-D-01「依存追加なし」方針と整合）。新設する pagination 純関数のユニットテストも併設。

### thumb_cache LRU 設計（PERF-02）
- **D-05:** LRU 上限は**枚数固定**（例: 最大窓サイズ 100 の 3 倍 = 300 枚程度の定数）。メモリ量換算は不採用。D-03 の先読みで窓内全件（最大100）がキャッシュに入るため、上限は必ず最大窓サイズより大きく取りスラッシングを防ぐ。
- **D-06:** 上限値は**コード内定数のみ**（例: `THUMB_CACHE_MAX`）。ユーザー設定としては公開しない（SettingsDialog への UI 追加をせず、Phase 6 の UI 一貫性監査対象を増やさない）。
- **D-07:** エビクションは**純粋 LRU**（容量到達時に最古参照分だけ自然に押し出す）。窓移動時の積極パージは不採用（窓を行き来した際の即時表示 UX を優先。上限が窓の3倍あれば直近の窓は自然に保持される）。
- **D-08:** LRU コンテナは **Tk 非依存の純ロジック層に新設**する（値は不透明オブジェクトとして扱う汎用 LRU。新規モジュールまたは `pagination.py` への追加は計画時判断）。`pagination.py`/`undo_store.py` の純ロジック層集約の系譜に沿い、Tk なしでユニットテスト可能にする。`viewer.py` の `thumb_cache` を置換するが、`_invalidate_thumb_cache` 等の既存呼び出し面は維持する。

### ShortcutsDialog WR-01/WR-02（ROBUST-03）
- **D-09:** WR-02 は**フォーカスガード方式**（発火側の構造的修正）で解消する。ショートカット発火時にフォーカス中ウィジェットを判定し、Entry/Spinbox/Text 等の入力系ウィジェットにフォーカスがある間は該当キーの発火を抑止する。キャプチャ時の登録拒否は行わない（登録の自由度を維持）。この方式は既定ショートカット `<Delete>`（ページ削除）/`<F5>`（モード切替）が現状持つ「Spinbox 編集中に発火しうる」既存衝突も同時に根治する。
- **D-10:** ガード対象は **Ctrl/Alt を含まないすべての組合せ**（修飾なし単キー + Shift のみの組合せ）。Shift+文字は大文字入力そのものなので入力中は抑止する。Ctrl/Alt を含む組合せ（Ctrl+O 等）は入力ウィジェットフォーカス中も従来どおり発火する。

### Blob リーク検出（ROBUST-01）
- **D-11:** 検出機構は **`__del__` + `_released` フラグ**方式。`FileBlob`/`MemBlob` に `_released` フラグを追加し、release されないまま GC されたら `__del__` で警告ログ（リーク検出）、release の二重呼び出しも警告ログ（double-release 検出）。weakref 追跡レジストリは不採用（`__slots__` への `__weakref__` 追加とレジストリ管理を増やさない軽量案）。インタプリタ終了時の誤検知抑止（atexit purge 後は警告しない等）に配慮する。
- **D-12:** リーク検出時は**警告ログ＋ベストエフォート回収**。`logger.warning` で記録しつつ、`__del__` 内で `unlink` も試行して一時ファイルを回収する。purge/atexit の二段回収は従来どおり維持。
- **D-13:** リーク検出ロギングは**常時有効**（アプリのログ設定は WARNING レベルのため検出時は必ず記録される）。デバッグ限定トグルは設けない。長時間運用でのリーク検出という ROBUST-01 の目的に合致。
- **D-14:** Windows AV スキャン衝突の回帰テストは **CONCERNS.md の Test Coverage Path 3 項目をフルカバー**する: ① `os.unlink` を `PermissionError` に mock して release がクラッシュせず purge/rmtree で回収されること、② insert→undo→redo→undo の連鎖で double-release が起きないこと（release スパイ）、③ 既存 `test_undo_stress.py` と連動した一時ディレクトリ残留監視。

### Claude's Discretion
- WR-01（キャプチャ対象切替時の「キーを押してください」表示残留）の具体的な修正実装（`_start_capture` で旧 capturing_cmd の行を `_refresh_row` する等。挙動は成功基準で確定済み: 切替時に前行表示を元へ復元）
- デバウンスの具体的な待機時間（150ms は例示。実装時にチューニング可）
- LRU 上限の具体値（300 枚は例示。最大窓サイズ 100 超を必須条件として計画時に確定）
- LRU コンテナの配置先（新規モジュール vs `pagination.py` 追加）とクラス/関数 API 設計
- フォーカスガードの入力系ウィジェット判定方法（クラス名ベース等）と、ガード判定純関数の配置（`app.py` の既存ショートカット純関数群 `build_keysym_from_event` 等の隣が自然）
- `__del__` での終了時誤検知抑止の具体的実装（モジュールレベルフラグ・`sys.is_finalizing()` 等）
- 可視範囲判定（Canvas viewport とサムネイル座標の照合）の実装方法 — ただし落とし穴1の回避策どおり、スクロールオフセット計算は `pagination.py` の純関数として追加し、新規座標系モジュールは作らない

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・フェーズ定義
- `.planning/REQUIREMENTS.md` — V180-PERF-01〜03・V180-ROBUST-01/03 の要件文言（本フェーズの対象5要件）
- `.planning/ROADMAP.md` — Phase 5 の Goal・Success Criteria（成功基準5項目）・依存関係（Phase 4 完了後の独立堅牢性フェーズ）

### リサーチ成果物
- `.planning/research/PITFALLS.md` 落とし穴1「サムネイル仮想化が `selected_pages` 全ページインデックス不変条件を破壊する」・落とし穴2「`thumb_cache` と仮想化ウィジェット再利用の責務混同」— 本フェーズの中心的リスク2点。回避策（スクロールオフセットも `pagination.py` の純関数として追加・新規座標系を増やさない・仮想化とLRUの同時導入・世代カウンタ併用）が明記されており D-01〜D-08 の直接の根拠

### 既知課題の出典
- `.planning/codebase/CONCERNS.md` §Performance Bottlenecks「Thumbnail Cache No Eviction」（PERF-02 の出典・50枚≈2.5MB の目安）・§Tech Debt「Blob Lifecycle Management (v1.7.0)」と §Test Coverage Gaps「Blob Lifecycle Edge Cases (v1.7.0)」（ROBUST-01 の出典。D-11/D-14 の修正案・Test Coverage Path 3項目はここに明記）・§Fragile Areas「D&D Multi-Page Reordering with Window Scroll」（PERF-03 テストが守るフラジャイル領域）
- `.planning/STATE.md` §Blockers/Concerns — WR-01/WR-02 の症状記録（v1.7.1 Phase 4 コードレビュー 04-REVIEW.md 由来）

### 前フェーズの決定事項
- `.planning/phases/01-foundation-split/01-CONTEXT.md` — Tk/fitz 非依存の純ロジック層新設方針（D-08 の LRU コンテナ配置が従う系譜）

### 前例パターン（コード内）
- `pagefolio/viewer.py` — `_build_thumbnails`/`_get_thumb_photo`/`_invalidate_thumb_cache`/`_refresh_thumbs_selection_only`（D-01〜D-03 の改修対象。現行の `after()` 連鎖・`_thumb_gen` 世代ガード・窓範囲 [lo, hi) 描画の実装）
- `pagefolio/pagination.py` — `to_global`/`to_local`/`window_bounds`/`reconcile_window_start` 等の純関数群（外層契約は不変のまま、可視範囲オフセット計算の純関数を追加する拡張先）
- `pagefolio/undo_store.py` — `MemBlob`/`FileBlob`/`UndoBlobStore`（D-11〜D-13 の改修対象。`__slots__` 定義・release の OSError suppress・purge/atexit 二段回収の現行実装）
- `pagefolio/dialogs/shortcuts.py` — `ShortcutsDialog._start_capture`/`_end_capture`/`_on_capture_keypress`（WR-01 修正対象。`_MODIFIER_KEYSYMS` 定義もここ）
- `pagefolio/app.py:56-88, 202-256` — `build_keysym_from_event`/`find_duplicate_binding`（ショートカット純関数群の前例。D-09/D-10 のガード判定純関数の配置先候補）・`_default_shortcuts`（`<Delete>`/`<F5>` の修飾なし既定キー）・`_bind_shortcuts`（root.bind の発火面＝フォーカスガード挿入点）
- `tests/test_undo_stress.py` — 120ページストレステスト（D-14 ③ の連動先）
- `tests/test_viewer.py`・`tests/test_pagination.py`（存在すれば） — 窓表示/選択整合の既存回帰テスト（D-04 のプロパティ風テスト追加先の前例）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_thumb_gen` 世代カウンタ（`viewer.py`）: デバウンス後の陳腐化レンダリング破棄（D-02）にそのまま流用できる
- `pagination.py` の純関数群: 可視範囲オフセット計算の追加先。既存の `window_bounds`/`to_global` と合成する形で拡張（落とし穴1回避策どおり）
- `_invalidate_thumb_cache(pages=None)` の呼び出し面: LRU 置換後もシグネチャ維持で既存呼び出し元（ページ操作・thumb_zoom 変更）は無変更
- `UndoBlobStore.file_count()`: AV 衝突テスト・リーク不変条件検証にそのまま使えるテスト用 API
- `build_keysym_from_event` 等の Tk 非依存ショートカット純関数（`app.py`）: フォーカスガード判定も同形式の純関数として追加すればテスト容易

### Established Patterns
- `selected_pages` は常に全ページインデックス・窓変換は `pagination.py` 経由のみ（V16-D-01）: 仮想化の可視範囲計算もこの規約に従う。新規座標系モジュールは作らない
- Tk/fitz 非依存の純ロジック層集約（`pagination.py`/`ocr_pipeline.py`/`undo_store.py` の系譜）: LRU コンテナ（D-08）もこの系譜に連なる
- Blob は `_capture_page_blob()` 経由のみ・スタック直接 `append`/`clear` 禁止: リーク検出（D-11）はこの規約の破れを実行時に検出する安全網という位置づけ
- 依存追加なし方針（V14-D-01）: プロパティ風テスト（D-04）は hypothesis を使わず `random.Random(seed)` で実装

### Integration Points
- `viewer.py._build_thumbnails` の `render_next` 連鎖: 可視範囲優先 + 先読み継続の優先度付きキューへ改修（D-01/D-03）
- サムネイル Canvas のスクロールイベント（`ui_builder.py` のスクロールバインド）: デバウンス起点（D-02）
- `app.py._bind_shortcuts` の root.bind ハンドラ: フォーカスガードの挿入点（D-09）。`root.focus_get()` で入力系ウィジェット判定
- `undo_store.py` の `MemBlob`/`FileBlob`: `_released` フラグ + `__del__` 追加（D-11）。`__slots__` に `_released` を追加する必要あり

</code_context>

<specifics>
## Specific Ideas

- 全領域で「推奨＝低リスク・既存構造維持」の選択肢が一貫して採用された: ウィジェット再利用ではなく画像遅延レンダリング（D-01）、weakref レジストリではなく `_released` フラグ（D-11）、設定公開ではなく定数（D-06）。過剰実装を避け Phase 5 を「仕上げフェーズ」として軽く保つ方針
- WR-02 は「登録を制限する」のではなく「発火側を賢くする」方向で確定（D-09）。既定キー `<Delete>`/`<F5>` の潜在衝突も同時に解消するのが決め手だった
- テストは PITFALLS/CONCERNS の推奨水準をフル採用（D-04 プロパティ風・D-14 フルカバー3項目）— 堅牢性フェーズの名に相応しい検証密度を優先

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope（4領域とも計画どおり完了。スコープ外提案は出なかった。PERF-F01＝連続スクロール型本格仮想化は既に v2 送り確定済みで本議論でも維持）

</deferred>

---

*Phase: 5-堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正）*
*Context gathered: 2026-07-16*
