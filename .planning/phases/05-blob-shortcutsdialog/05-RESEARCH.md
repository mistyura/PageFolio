# Phase 5: 堅牢性強化（サムネイル仮想化 + Blobリーク検出 + ShortcutsDialog修正） - Research

**Researched:** 2026-07-16
**Domain:** 既存 Tkinter デスクトップアプリの内部堅牢性強化（サムネイル遅延レンダリング・LRU キャッシュ・Blob ライフサイクル・ショートカット発火制御）。新規外部パッケージなし・純粋にコードベース内部の改修。
**Confidence:** HIGH（全知見は本リポジトリのソースコード直接読解・実行時 Tkinter 挙動確認・既存テストパターン踏襲に基づく。外部一般知識は WebSearch で裏取り）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**仮想化の実体化方式（PERF-01）**
- **D-01:** 「可視範囲のみ実体化」は**画像遅延レンダリング型**で実現する。ウィジェット（Frame/ページ番号ラベル・イベント bind）は現行どおり窓内全生成を維持し、重い `get_pixmap` のみ可視範囲を優先実行、窓外はスクロールで見えた時にレンダリングする。ウィジェット再利用型は不採用（落とし穴2「ウィジェット再利用とキャッシュの責務混同」を構造的に回避し、PERF-F01＝v2 送りの本格仮想化との境界を明確に保つ。ウィジェット数は窓サイズ ≤100 で既に有界）。
- **D-02:** スクロール中のレンダリングは**デバウンス型**。スクロール停止後（例: 150ms 無操作）に可視範囲をレンダリングする。`thumb_cache` ヒット分はスクロール中も即時表示し、ミス時のみプレースホルダ表示（PITFALLS の UX 注意「チラつきによる別ページ誤クリック」対応）。既存 `_thumb_gen` 世代ガードと併用して陳腐化描画を破棄する。
- **D-03:** 可視範囲の描画完了後、**アイドル時間に窓内の残りを先読みレンダリングする**（可視範囲 → 窓内残りの優先度付き。現行 `after()` 連鎖の優先度付き化）。総仕事量は現行と同じだが体感を大幅改善。メモリは LRU（D-05〜D-08）で有界化されるため安全。
- **D-04:** PERF-03 の回帰テストは**プロパティ風テスト＋ユニットの二本立て**。seed 固定の `random.Random` によるランダム操作列（選択/スクロール/D&D）で 500+ ページ相当の `selected_pages` 全ページインデックス不変条件を検証する。hypothesis 等の新規依存は追加しない（V14-D-01「依存追加なし」方針と整合）。新設する pagination 純関数のユニットテストも併設。

**thumb_cache LRU 設計（PERF-02）**
- **D-05:** LRU 上限は**枚数固定**（例: 最大窓サイズ 100 の 3 倍 = 300 枚程度の定数）。メモリ量換算は不採用。D-03 の先読みで窓内全件（最大100）がキャッシュに入るため、上限は必ず最大窓サイズより大きく取りスラッシングを防ぐ。
- **D-06:** 上限値は**コード内定数のみ**（例: `THUMB_CACHE_MAX`）。ユーザー設定としては公開しない（SettingsDialog への UI 追加をせず、Phase 6 の UI 一貫性監査対象を増やさない）。
- **D-07:** エビクションは**純粋 LRU**（容量到達時に最古参照分だけ自然に押し出す）。窓移動時の積極パージは不採用（窓を行き来した際の即時表示 UX を優先。上限が窓の3倍あれば直近の窓は自然に保持される）。
- **D-08:** LRU コンテナは **Tk 非依存の純ロジック層に新設**する（値は不透明オブジェクトとして扱う汎用 LRU。新規モジュールまたは `pagination.py` への追加は計画時判断）。`pagination.py`/`undo_store.py` の純ロジック層集約の系譜に沿い、Tk なしでユニットテスト可能にする。`viewer.py` の `thumb_cache` を置換するが、`_invalidate_thumb_cache` 等の既存呼び出し面は維持する。

**ShortcutsDialog WR-01/WR-02（ROBUST-03）**
- **D-09:** WR-02 は**フォーカスガード方式**（発火側の構造的修正）で解消する。ショートカット発火時にフォーカス中ウィジェットを判定し、Entry/Spinbox/Text 等の入力系ウィジェットにフォーカスがある間は該当キーの発火を抑止する。キャプチャ時の登録拒否は行わない（登録の自由度を維持）。この方式は既定ショートカット `<Delete>`（ページ削除）/`<F5>`（モード切替）が現状持つ「Spinbox 編集中に発火しうる」既存衝突も同時に根治する。
- **D-10:** ガード対象は **Ctrl/Alt を含まないすべての組合せ**（修飾なし単キー + Shift のみの組合せ）。Shift+文字は大文字入力そのものなので入力中は抑止する。Ctrl/Alt を含む組合せ（Ctrl+O 等）は入力ウィジェットフォーカス中も従来どおり発火する。

**Blob リーク検出（ROBUST-01）**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope（4領域とも計画どおり完了。スコープ外提案は出なかった。PERF-F01＝連続スクロール型本格仮想化は既に v2 送り確定済みで本議論でも維持）
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V180-PERF-01 | 大量ページ PDF で窓内サムネイルが可視範囲のみ実体化され、描画が高速化される（既存 `pagination.py` 窓表示の外層契約は不変） | `viewer.py._build_thumbnails`/`render_next` の現行 `after()` 連鎖を解析済み（Architecture Patterns Pattern 1）。可視範囲計算は `thumb_canvas` の `yscrollcommand`/`canvasy()` を使う既存パターン（`dnd.py._dnd_dest_index`）を再利用可能と確認 |
| V180-PERF-02 | `thumb_cache` に LRU eviction が導入され、メモリ使用が有界化される | `collections.OrderedDict` ベースの LRU パターンを確認・引用（Code Examples）。現行 `thumb_cache` は無制限 dict（`viewer.py:143-154`）であることをソース確認済み |
| V180-PERF-03 | `selected_pages` 全ページインデックス不変条件・D&D・窓表示との整合が回帰テストで保証される | `pagination.py`/`dnd.py` の変換関数群を精読済み。既存テストに `random.Random` 駆動のプロパティ風テストが**まだ存在しない**ことを確認（Wave 0 gap） |
| V180-ROBUST-01 | Blob ライフサイクルのリーク検出が強化され、Windows AV スキャン衝突の回帰テストが整備される | `undo_store.py` の `FileBlob.release()`（`contextlib.suppress(OSError)` で `PermissionError` を既に握り潰す実装）を確認済み。`test_undo_stress.py` の `_make_stress_app`/`_blob_files` パターンを D-14 のテスト実装にそのまま転用可能と確認 |
| V180-ROBUST-03 | ShortcutsDialog の WR-01/WR-02 が解消される | `dialogs/shortcuts.py._start_capture`/`_end_capture` を精読し WR-01 の正確な発火条件を特定済み。Tkinter の実行時挙動を検証しWR-02 の発火メカニズムを実証済み（Common Pitfalls 参照） |
</phase_requirements>

## Summary

本フェーズは新機能追加ではなく、既存 4 コンポーネント（`viewer.py` サムネイル描画・`undo_store.py` Blob ライフサイクル・`dialogs/shortcuts.py` キー設定 UI・`pagination.py`/`dnd.py` 窓表示整合）に対する的を絞った堅牢性改修である。5要件はいずれも「既存の構造・契約を変えずに、内部実装だけを強化する」という一貫した方針を持ち、CONTEXT.md の全決定（D-01〜D-14）もこの方針に沿っている。

サムネイル仮想化（PERF-01〜03）は、ウィジェット（Frame/Label）は窓内全生成を維持したまま、`get_pixmap()` 呼び出しのみを可視範囲優先・デバウンス・アイドル先読みの3段構成に変える「画像遅延レンダリング型」であり、react-window 型の本格仮想化（PERF-F01）とは明確に別物である。この方式を採る最大の理由は、`selected_pages` が常に全ページインデックスで保持されるという既存の V16-D-01 不変条件を、ウィジェットのリサイクル（スロット番号への読み替え）なしに温存できる点にある。LRU 化（`thumb_cache`）は `collections.OrderedDict` で十分に実装可能で、新規依存は不要。

Blob リーク検出（ROBUST-01）は `FileBlob`/`MemBlob` に `_released` フラグと `__del__` を追加する軽量方式で、既存の `contextlib.suppress(OSError)` による `PermissionError` 握り潰しはそのまま活かせる（実装済みの安全網に、検出ログを追加するだけ）。ShortcutsDialog の2バグ（WR-01/WR-02）は、実際にソースコードと Tkinter のランタイム挙動を検証した結果、原因が明確に特定できた（後述 Common Pitfalls）。

**Primary recommendation:** 4領域とも「既存の外層契約・呼び出し面を変えずに内部実装のみ強化する」という設計を貫く。新規モジュールの濫立を避け、`pagination.py`（可視範囲純関数の追加）・`undo_store.py`（`_released`/`__del__` 追加）・`app.py`（フォーカスガード純関数の追加）という既存の Tk 非依存純ロジック層の系譜に新規ロジックを乗せる。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| サムネイル可視範囲判定・デバウンス・先読みスケジューリング | Frontend（Tkinter UI 層・`viewer.py`） | 純ロジック層（`pagination.py` の座標変換） | 描画スケジューリング自体は Tk の `after()`/Canvas API に依存するため UI 層責務。座標変換のみ純関数に切り出す（V16-D-01 踏襲） |
| `thumb_cache` LRU コンテナ | 純ロジック層（新規/`pagination.py`） | Frontend（`viewer.py` からの呼び出し） | Tk/fitz 非依存で単体テスト可能にする（`undo_store.py` の系譜） |
| `selected_pages` 全ページインデックス整合 | 純ロジック層（`pagination.py`） | Frontend（`viewer.py`/`dnd.py` の呼び出し） | 既存 V16-D-01 の対象範囲そのもの。仮想化で新たな座標系を作らないことが要 |
| Blob ライフサイクル・リーク検出 | 純ロジック層（`undo_store.py`） | Frontend（`file_ops.py` の解放呼び出し） | Tk/fitz 非依存が既に確立済み（`undo_store.py` は import 皆無）。`__del__` もこの層に閉じる |
| ShortcutsDialog 表示残留修正（WR-01） | Frontend（`dialogs/shortcuts.py`） | — | UI ウィジェットの表示状態管理そのものであり Tk 依存が本質的 |
| ショートカット発火のフォーカスガード（WR-02） | Frontend（`app.py._bind_shortcuts` の発火面） | 純ロジック層（判定純関数） | 判定ロジック（キーシムと入力系ウィジェットクラス名の突き合わせ）は Tk 非依存で切り出し可能。実際の `root.focus_get()` 呼び出しは Tk 依存 |

このフェーズはデスクトップアプリの単一プロセス内改修であり、Browser/CDN/Database 等の他階層は関与しない。

## Package Legitimacy Audit

**本フェーズでは新規外部パッケージを一切導入しない。** 全ての実装は Python 標準ライブラリ（`collections.OrderedDict`、`logging`、`sys`、`contextlib`、既存の `tkinter`/`fitz`）のみで完結する（V14-D-01「依存追加なし」方針、D-04「hypothesis 等の新規依存は追加しない」と整合）。したがって Package Legitimacy Gate（`gsd-tools query package-legitimacy check`）の対象パッケージは存在しない。

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | 対象なし（新規パッケージ導入なし） |

## Standard Stack

### Core

本フェーズは新規ライブラリを導入しない。使用するのは既存の requirements.txt 記載バージョンと Python 標準ライブラリのみ。

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | 1.28.0（`requirements.txt` 記載）/ 1.27.2.3（現行 venv インストール済み・`pip show pymupdf` で確認）[VERIFIED: ローカル pip show] | 既存の `get_pixmap()` 呼び出しは変更なし | 既存プロジェクト標準 |
| Pillow | 12.3.0（`requirements.txt`） | 既存のサムネイル画像変換は変更なし | 既存プロジェクト標準 |
| Python 標準ライブラリ `collections.OrderedDict` | 3.14 同梱 | LRU コンテナの実装基盤 | `move_to_end()`/`popitem(last=False)` で O(1) の LRU 操作が可能。追加依存ゼロ [CITED: docs.python.org/3/library/collections.html] |
| Python 標準ライブラリ `sys.is_finalizing()` | 3.14 同梱（3.4 以降） | `__del__` 内でのインタプリタ終了時誤検知抑止 | PEP 442（Safe Object Finalization）以降の標準機構 [CITED: peps.python.org/pep-0442] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `random.Random(seed)` | 標準ライブラリ | D-04 プロパティ風テストの決定的乱数列生成 | 500+ページ相当の選択/スクロール/D&D操作列をシード固定で再現する場合 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `collections.OrderedDict` ベース自作 LRU | `functools.lru_cache` | `lru_cache` は関数デコレータであり、明示的なエビクション通知・サイズ動的変更・`thumb_cache` の既存 dict 互換 API（`pop`/`clear`/`in` 判定）が要求される本用途には不向き。自作 `OrderedDict` ラッパーが妥当 |
| `__del__` + `_released` フラグ | `weakref.finalize` | D-11 で明示的に不採用と決定済み（レジストリ管理を増やさない軽量案を優先）。`weakref.finalize` は「オブジェクトが不要になった時に呼ばれる」保証がより強いが、`__slots__` に `__weakref__` 追加が必要になり、現行の軽量 `__slots__` 設計（`("path", "size")`/`("_data",)`）を変更する必要がある |
| プロパティ風テスト自作（`random.Random`） | `hypothesis` | V14-D-01「新規依存なし」方針に反するため不採用（D-04 で明示決定済み） |

**Installation:** 不要（新規パッケージなし）。

**Version verification:** [VERIFIED: ローカル環境確認]
```
$ pip show pymupdf
Version: 1.27.2.3
$ python --version
Python 3.14.6
```
`requirements.txt` は `PyMuPDF==1.28.0` を指定しているが、開発 venv には 1.27.2.3 が入っている（差異は本フェーズの実装に影響しない範囲。計画時に確認事項として記録推奨）。

## Architecture Patterns

### System Architecture Diagram

```
[ユーザースクロール操作]
        │
        ▼
thumb_canvas の yscrollcommand フック（新規: D-02 デバウンス起点）
        │
        ▼
   ┌─────────────────────────┐
   │ デバウンスタイマー (150ms)│──(タイマー未満に再スクロール)──┐
   └─────────────────────────┘                              │
        │ (停止確定)                                          │
        ▼                                                    │
可視範囲計算（pagination.py 新設純関数: canvas viewport→ローカルpage範囲）
        │                                                    │
        ▼                                                    │
  ┌──────────────────────────────┐                          │
  │ thumb_cache（LRU）ヒット判定  │──ヒット→即時 Label 差替    │
  └──────────────────────────────┘                          │
        │ ミス                                                │
        ▼                                                    │
プレースホルダ維持 → get_pixmap() 実行（_thumb_gen 世代ガード付き）──┘
        │
        ▼
thumb_cache へ格納（LRU: 容量超過で最古エントリを自然エビクト）
        │
        ▼
可視範囲描画完了 → root.after_idle で窓内残り(D-03 優先度付き先読み)へ継続
        │
        ▼
[ページ選択 / D&D] → pagination.to_global/to_local のみ経由 → selected_pages（全ページindex）更新
```

```
[ショートカットキー押下]
        │
        ▼
root.bind ハンドラ発火（app.py._bind_shortcuts で登録済み）
        │
        ▼
フォーカスガード判定（新設純関数: keysym と Ctrl/Alt 有無 + 現在フォーカスウィジェットのクラス名）
        │
   ┌────┴─────┐
   │           │
Ctrl/Alt含む  Ctrl/Alt含まない
 or 非入力系   かつ 入力系ウィジェットにフォーカスあり
   │           │
   ▼           ▼
コマンド実行   抑止（何もしない）
```

### Recommended Project Structure

既存構造を維持し、新規モジュールは最小限にする（D-08 の配置は計画時判断だが、いずれの場合も既存系譜への追加）:

```
pagefolio/
├── pagination.py       # 既存。可視範囲オフセット計算の純関数を追加（D-01落とし穴1回避策）。
│                        # LRU コンテナもここに追加する場合はこのファイル内で完結させる
├── viewer.py            # 既存。_build_thumbnails/_get_thumb_photo を改修
│                        # （可視範囲優先 + デバウンス + アイドル先読み・thumb_cache→LRU差替）
├── undo_store.py         # 既存。FileBlob/MemBlob に _released フラグ + __del__ を追加
├── file_ops.py           # 既存。_dispose_state 等の解放呼び出し面は変更なし（release()経由のまま）
├── app.py                # 既存。build_keysym_from_event 等の隣にフォーカスガード純関数を追加
│                        # _bind_shortcuts の発火ラムダにガード呼び出しを挿入
├── dnd.py                # 既存。窓またぎ選択のD&D整合はここが対象（D-04テスト対象）
└── dialogs/
    └── shortcuts.py       # 既存。_start_capture の WR-01 修正（旧行の _refresh_row 復元）

tests/
├── test_pagination.py          # 既存。可視範囲純関数・LRU（配置先次第）のユニットテスト追加
├── test_viewer.py              # 既存。デバウンス/世代ガード関連のロジックテスト追加（Tk root不要な範囲）
├── test_undo_stress.py         # 既存。D-14 の3項目（AV mock/double-release/tmpdir監視）を追加
├── test_selection_invariant.py # 新規（提案名）。D-04 プロパティ風テスト（random.Random シード固定）
└── test_shortcuts_dialog.py    # 新規（提案名）。WR-01/WR-02 の回帰テスト
```

### Pattern 1: 現行の後読み優先度なしレンダリング連鎖（改修対象・現状把握）

**What:** `viewer.py._build_thumbnails` は窓範囲 `[lo, hi)` 全ページに対しプレースホルダ Frame/Label を即時生成し、`render_next(i)` を `root.after(0, ...)` で逐次呼び出して `get_pixmap()` を1枚ずつ実行する。優先順位は常に `lo→hi` の昇順で、可視範囲かどうかは考慮しない。

**When to use（現行）:** 窓サイズ ≤100 前提で許容されてきたが、大量ページかつ低スペック環境では窓先頭から末尾まで律儀にレンダリングするため、ユーザーが窓の後半（可視範囲）を見ていても先頭からのレンダリングが終わるまで表示が追いつかない。

**Example:**
```python
# Source: pagefolio/viewer.py:293-310（現行実装、改修対象）
def render_next(i):
    if self._thumb_gen != gen or not self.doc:
        return
    if i >= hi:
        return
    photo = self._get_thumb_photo(i)
    frame, lbl = placeholder_labels[i - lo]
    lbl.configure(image=photo)
    self.thumb_images.append(photo)
    self.root.after(0, lambda: render_next(i + 1))

self.root.after_idle(lambda: render_next(lo))
```

**改修方針（D-01〜D-03）:** `render_next` の呼び出し順序を「可視範囲を先に」「窓内残りは `after_idle` でアイドル時に」の2段キューへ変更する。`_thumb_gen` 世代ガードはそのまま流用可能（呼び出し順序が変わってもガード条件 `self._thumb_gen != gen` は不変）。

### Pattern 2: 可視範囲判定の既存前例（`dnd.py._dnd_dest_index`）

**What:** D&D の挿入先計算は `event.y_root` → `thumb_canvas.winfo_rooty()` で相対座標を得て `canvas.canvasy()` でスクロール位置補正した論理Y座標に変換し、各フレームの `winfo_y()`/`winfo_height()` と比較する。

**When to use:** サムネイル仮想化の可視範囲計算（D-01の可視範囲優先化）も同型の座標変換が必要になる。`thumb_canvas.yview()` が返す `(top_frac, bottom_frac)` と `thumb_inner` の総高さ・各フレームの `winfo_y()` を組み合わせれば、可視範囲に対応する窓ローカル index 区間 `[vis_lo, vis_hi)` を計算できる。

**Example:**
```python
# Source: pagefolio/dnd.py:94-106（既存の座標変換前例）
def _dnd_dest_index(self, event):
    frames = self.thumb_inner.winfo_children()
    if not frames:
        return None
    canvas_y = event.y_root - self.thumb_canvas.winfo_rooty()
    cy = self.thumb_canvas.canvasy(canvas_y)
    frame_bounds = [(fr.winfo_y(), fr.winfo_height()) for fr in frames]
    return compute_dnd_dest_index(cy, frame_bounds)
```
`compute_dnd_dest_index` は `dnd.py` モジュールレベルの Tk 非依存純関数（`frame_bounds` は呼び出し側が Tk から収集し、比較ロジックのみ純関数）。可視範囲計算も同じ分離方針（Tk 依存の座標収集は `viewer.py` 側、比較ロジックは `pagination.py` の新規純関数）を踏襲すべき（落とし穴1の回避策と一致）。

### Pattern 3: OrderedDict ベース LRU（新規実装が従うべきパターン）

**What:** `collections.OrderedDict` は挿入順を保持し、`move_to_end()` で最近使用扱いへ更新、`popitem(last=False)` で最古エントリ（先頭）を追い出せる。

**When to use:** `thumb_cache` の LRU 化（D-05〜D-08）。

**Example:**
```python
# Source: 標準ライブラリの一般的な LRU パターン
# [CITED: https://docs.python.org/3/library/collections.html]
from collections import OrderedDict

class LruCache:
    """汎用 LRU キャッシュ（値は不透明オブジェクトとして扱う・Tk/fitz非依存）。

    D-08: pagination.py への追加 or 新規モジュールは計画時判断。
    """

    def __init__(self, maxsize):
        self._maxsize = maxsize
        self._data = OrderedDict()

    def get(self, key):
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def pop(self, key, default=None):
        return self._data.pop(key, default)

    def clear(self):
        self._data.clear()

    def __contains__(self, key):
        return key in self._data
```
既存の `_invalidate_thumb_cache`（`viewer.py:136-141`）は `self.thumb_cache.pop(p, None)` / `self.thumb_cache.clear()` を呼ぶだけなので、上記 API（`pop`/`clear`/`__contains__`）を実装すれば呼び出し側は無改造で済む（D-08 の「既存呼び出し面は維持」要件を満たす）。

### Pattern 4: Blob `__del__` リーク検出（新規実装が従うべきパターン）

**What:** `_released` フラグを `__slots__` に追加し、`release()` 呼び出し時に True へ設定。`__del__` で `_released` が False のままなら警告ログ＋ベストエフォート回収。

**Example:**
```python
# Source: 設計方針は D-11/D-12/D-14 に基づく提案実装（既存 undo_store.py の拡張）
import sys

class FileBlob:
    __slots__ = ("path", "size", "_released")

    def __init__(self, path, size):
        self.path = path
        self.size = size
        self._released = False

    def load(self):
        with open(self.path, "rb") as f:
            return f.read()

    def release(self):
        if self._released:
            logger.warning("FileBlob 二重解放を検出: %s", self.path)
            return
        self._released = True
        with contextlib.suppress(OSError):
            os.unlink(self.path)

    def __del__(self):
        # D-11: インタプリタ終了時の誤検知抑止。
        # PEP 442 以降、モジュールグローバルは以前ほど強制 None 化されないが
        # sys.is_finalizing() でのガードは依然として推奨パターン
        # [CITED: https://peps.python.org/pep-0442/]
        if self._released or sys.is_finalizing():
            return
        # ロガー/os が既に破棄されている可能性を考慮し例外を握り潰す
        try:
            logger.warning("FileBlob リーク検出（未解放のまま GC）: %s", self.path)
            with contextlib.suppress(OSError):
                os.unlink(self.path)
        except Exception:
            pass
```
**注意:** `except Exception: pass`（メッセージ引数なし）はプロジェクトの「裸の except 禁止・`except Exception as e:` 必須」規約に抵触するため、計画時には `except Exception as e:` へ修正し `e` を握り潰す前提でコメントするか、`contextlib.suppress(Exception)` を使う（ただし `Exception` 全体の suppress はリンタ/規約上グレーゾーンになりうるため、計画段階で `ruff` の `S` ルール抵触有無を確認すること）。

### Pattern 5: フォーカスガード純関数（新規実装が従うべきパターン）

**What:** キーシム文字列と現在フォーカス中ウィジェットのクラス名から、発火を抑止すべきか判定する Tk 非依存純関数。

**Example:**
```python
# Source: 設計方針は D-09/D-10 に基づく提案実装（app.py の build_keysym_from_event 隣接想定）
_INPUT_WIDGET_CLASSES = {"Entry", "TEntry", "Spinbox", "TSpinbox", "Text"}


def should_suppress_for_focused_input(keysym, focused_widget_class):
    """修飾なし単キー/Shiftのみの組合せで、入力系ウィジェットにフォーカスがある間は
    発火を抑止すべきかを判定する（D-09/D-10・Tk非依存の純関数）。

    keysym: "<Delete>" 等の bind 文字列（Control/Alt を含むかどうかで判定）。
    focused_widget_class: root.focus_get().winfo_class() の戻り値（Tk依存呼び出しは
    app.py 側で行い、結果の文字列のみここへ渡す）。
    """
    if "Control" in keysym or "Alt" in keysym:
        return False
    return focused_widget_class in _INPUT_WIDGET_CLASSES
```
**実行時検証済み事実（`_bind_shortcuts` への挿入根拠）:** [VERIFIED: ローカル tkinter ランタイム確認]
```python
# 実行して確認した事実:
#   root.bind_class('Entry', '<Delete>') の既定バインドスクリプトに "break" が
#   含まれない（%W delete insert 等のみ）ため、Delete キー押下は
#   Entry の既定動作（文字削除）実行後もイベント伝播が止まらず、
#   root（トップレベル）に bind したハンドラも実行される。
#
# さらに、root にバインドしたコールバックへ渡される event オブジェクトの
# event.widget は「実際にフォーカスを持っていた元ウィジェット」を指す
# （root 自身ではない）ことを event_generate('<Delete>') で実証済み:
#   event.widget          -> '.!entry'
#   event.widget.winfo_class() -> 'Entry'
#   root.focus_get()      -> 同じ Entry ウィジェット
#
# → event.widget.winfo_class() または root.focus_get().winfo_class() の
#   どちらでも WR-02 のガード判定に使える。
```

### Anti-Patterns to Avoid

- **ウィジェットリサイクル型仮想化の導入:** PERF-F01（v2送り確定）と混同しない。`selected_pages` はローカルスロット番号に一切触れさせない（落とし穴1）。
- **`thumb_cache` とウィジェットスロットのキー統合:** キャッシュキーは常にページ番号のみ（落とし穴2）。ウィジェット側の再利用ロジックを仮に将来導入する場合でも画像キャッシュとは責務分離を保つ。
- **weakref レジストリでのリーク検出:** D-11 で明示的に不採用。`_released` フラグ + `__del__` のみで完結させる。
- **ShortcutsDialog のキャプチャ登録を制限する対処（WR-02）:** D-09 で明示的に不採用。発火側（フォーカスガード）で解消する。
- **`__del__` 内で例外を伝播させる:** インタプリタ終了時に `logger`/`os` が既に破棄されている可能性があるため、`__del__` 内の処理は必ず例外を握り潰す（CLAUDE.md の「裸の except 禁止」を守りつつ `except Exception as e:` で捕捉）。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LRU キャッシュのエビクション順序管理 | 独自の連結リスト + dict 実装 | `collections.OrderedDict`（`move_to_end`/`popitem(last=False)`） | 標準ライブラリで O(1) 保証済み・実装ミスのリスクがない [CITED: docs.python.org/3/library/collections.html] |
| プロパティベーステストのランダム操作生成 | 独自の擬似ランダムシーケンス生成器 | `random.Random(seed)` | 標準ライブラリで決定的再現性が保証される。`hypothesis` 相当の網羅性は不要（D-04 で明示的に依存追加なし方針） |
| インタプリタ終了検知 | 独自のグローバルフラグ+atexitフック二重管理 | `sys.is_finalizing()` | 標準ライブラリの正規サポート機構（PEP 442 以降）[CITED: peps.python.org/pep-0442] |

**Key insight:** 本フェーズは「堅牢性強化」フェーズであり、標準ライブラリの成熟した道具（`OrderedDict`・`random.Random`・`sys.is_finalizing`）で全て賄える規模の問題ばかりである。自作実装を増やすとテスト対象・保守対象が不必要に増える。

## Common Pitfalls

### Pitfall 1: WR-01 の正確な原因 — `_start_capture` の二重発火時に旧行が復元されない

**What goes wrong:** ユーザーがコマンドAのキャプチャを開始（行Aが「キーを押してください」表示になる）した後、保存/クリアせずにコマンドBの「変更」ボタンを押すと、行Aの表示が「キーを押してください」のまま永続的に残る。

**Why it happens:** `_start_capture(cmd_name)` の冒頭:
```python
def _start_capture(self, cmd_name):
    if self._capturing_cmd is not None:
        self._end_capture()          # ← unbind するだけで表示は戻さない
    self._capturing_cmd = cmd_name
    ...
```
`_end_capture()` は `<KeyPress>` の unbind と `_capturing_cmd = None` のみを行い、直前にキャプチャ中だった行（cmd_name）に対する `_refresh_row()` を呼ばない。そのため行Aのラベルは `shortcuts_capture_waiting` のテキストのまま取り残される。[VERIFIED: `pagefolio/dialogs/shortcuts.py:189-204` 読解]

**How to avoid:** `_start_capture` の冒頭で、旧 `_capturing_cmd`（None でなければ）を保持してから `_end_capture()` を呼び、その**旧コマンド名**に対して `_refresh_row()` を呼ぶ（CONTEXT.md の Discretion 欄に記載された修正方針そのもの）。

**Warning signs:** ダイアログ内で複数コマンドの「変更」ボタンを連続クリックした際に、前の行の表示が固まって見える。

---

### Pitfall 2: WR-02 の正確な発火メカニズム — Tk のイベント伝播が `break` されない

**What goes wrong:** ユーザーが本文中のウィジェット（例: 将来追加されうる Entry/Spinbox/Text）にフォーカスしている間に、修飾なし単キー（既定の `<Delete>`/`<F5>` を含む）を押すと、そのウィジェット自身の既定動作（文字削除など）と、`app.py._bind_shortcuts` が `self.root.bind(keysym, ...)` で登録したアプリケーションレベルのコマンドの**両方**が発火する。

**Why it happens:** [VERIFIED: 実行時 Tkinter 挙動確認]
- `root.bind_class('Entry', '<Delete>')` の既定バインドスクリプトを実機確認したところ、`%W delete insert`（文字削除）のみで `break` を含まない。
- Tk のイベント伝播は「ウィジェット → ウィジェットクラス → 最寄りの Toplevel → all」の順で bindtags を辿り、途中のバインドが `break` しない限り**全てのタグのバインドが実行される**。
- `app.py._bind_shortcuts` は `self.root.bind(keysym, ...)` でメインウィンドウ（最寄りの Toplevel が root 自身であるウィジェット群）に対して登録しているため、root の直接の子孫ウィジェット（別の Toplevel ダイアログ内のウィジェットは対象外）でこの衝突が起こりうる。
- 実際に `event_generate('<Delete>')` で検証したところ、root で受け取るハンドラの `event.widget` は元のフォーカスウィジェットを指し（`event.widget.winfo_class()` で `'Entry'` 等が取得できる）、`root.focus_get()` でも同じウィジェットが得られることを確認した。両方ともフォーカスガード実装の判定材料として使える。

現状、本アプリのメインウィンドウ直下に配置されている入力系ウィジェットは `page_size_spin`（`ttk.Spinbox`, `state="readonly"`）・`thumb_zoom_scale`/`mosaic_block_scale`（`ttk.Scale`）のみで Entry/Text は存在しないため、**現時点で実際にユーザーが遭遇する頻度は低い**が、コードレビュー（04-REVIEW.md）で指摘された構造的リスクは実在し、将来的なウィジェット追加（例: ページ番号ジャンプ入力欄）で即座に顕在化する。フォーカスガードは汎用的な入力系ウィジェットクラス名判定にしておくべき。

**How to avoid:** D-09/D-10 のフォーカスガード方式（Pattern 5）を `_bind_shortcuts` の発火ラムダに挿入する。Ctrl/Alt を含む組合せは常時発火を許可し、修飾なし単キー/Shiftのみの組合せは入力系ウィジェットへのフォーカス中は抑止する。

**Warning signs:** 既定ショートカットの `<Delete>`（ページ削除）や `<F5>`（モード切替）が、メインウィンドウ内の Spinbox/Scale にフォーカスがある状態で意図せず発火する（現状は Spinbox が readonly のため実害は限定的だが、キーボードナビゲーション中の誤操作の可能性はある）。

---

### Pitfall 3: 落とし穴1（PITFALLS.md）— サムネイル仮想化が `selected_pages` 不変条件を破壊する

**What goes wrong:** 可視範囲計算のための「表示開始オフセット」を、既存の `pagination.py` の `to_global`/`to_local`/`window_bounds` を経由せず独自の座標系で実装してしまうと、D&D中のスクロールやキーボードナビゲーションで選択ページと操作対象がずれる。

**Why it happens:** 仮想化の定石は「表示行番号を主語にした実装」であり、既存の「`selected_pages` は常に全ページインデックス」という規約と自然に衝突する（V16-D-01）。

**How to avoid:** 可視範囲オフセット計算用の新規純関数を `pagination.py` に追加し、既存の `window_bounds`/`to_global` と合成する形で実装する（新規座標系モジュールを作らない）。`selected_pages` へは絶対に窓ローカル添字を直接書き込まない。

**Warning signs:** D&D 中にスクロールバー/マウスホイールでウィンドウが動くケースの手動テスト、大量ページでのランダム選択＋スクロールのプロパティテスト（D-04）で不整合が出る。

**既存原則で防げるか:** 防げる。`pagination.py` への集約を徹底すること。

---

### Pitfall 4: 落とし穴2（PITFALLS.md）— `thumb_cache` と可視範囲優先度の責務混同

**What goes wrong:** 「可視範囲を先に描画する」ロジックと「LRUキャッシュのヒット/ミス判定」を1つの関数に混在させると、キャッシュのキーが「ページ番号」なのか「表示優先度スロット」なのか曖昧になる。

**Why it happens:** D-01 は「ウィジェット再利用」を明確に不採用としたが、実装時に「優先度キュー」の概念を導入する際、うっかりページ番号以外のキーで管理してしまう誘惑がある。

**How to avoid:** 可視範囲優先度は「どの順で `get_pixmap()` を呼ぶか」というスケジューリングの話に限定し、`thumb_cache`（LRU化後も）のキーは常にページ番号のみに保つ。`_thumb_gen` 世代カウンタで陳腐化した非同期描画結果を破棄する既存パターンをそのまま踏襲する。

**Warning signs:** 高速スクロール時に古いサムネイルが一瞬別ページとして表示される、キャッシュヒット率が想定より低い。

---

### Pitfall 5: `__del__` 実装がインタプリタ終了時に例外を出す

**What goes wrong:** `FileBlob.__del__` が `logger`/`os` モジュールに依存する処理を無条件に実行すると、インタプリタ終了処理の途中でモジュールが部分的に破棄されている状況下で `AttributeError`/`TypeError` 等が発生しうる。

**Why it happens:** Python 3.4 以降（PEP 442）でモジュールグローバルの強制 None 化は大幅に緩和されたが、依然として「他のオブジェクトが先に終了処理済み」「別スレッドのインタプリタが停止済み」等のケースで `__del__` 内の呼び出しが不安定になりうる。[CITED: peps.python.org/pep-0442]

**How to avoid:** `__del__` 冒頭で `sys.is_finalizing()` をチェックし、真なら早期リターンする。残りの処理も `try/except Exception as e:` で必ず囲み、例外を握り潰す（CLAUDE.md の「裸の except 禁止」規約を守りつつ捕捉する）。

**Warning signs:** テストスイート終了時やアプリ終了時に `Exception ignored in: <function FileBlob.__del__ ...>` のような警告が stderr に出る。

## Code Examples

### 既存の Blob 解放呼び出し面（変更不要・そのまま活かせる箇所）

```python
# Source: pagefolio/undo_store.py:71-74（現行実装。PermissionError は既に握り潰される）
def release(self):
    """一時ファイルを削除する。ロック等の失敗は purge/atexit に委ねる。"""
    with contextlib.suppress(OSError):
        os.unlink(self.path)
```
`PermissionError` は `OSError` のサブクラスなので、D-14 のテスト①（`os.unlink` を `PermissionError` にモック）は**現行実装でも既にクラッシュしない**。これは新規に直す必要のあるバグではなく、「既にある安全網に対する回帰テストを追加する」タスクである。

### 既存の Blob テストハーネス（D-14 がそのまま再利用できるパターン）

```python
# Source: tests/test_undo_stress.py:54-81（FakeApp パターン。新規テストもこれを踏襲可能）
def _make_stress_app(doc, max_undo=20):
    class FakeApp(fo.FileOpsMixin, ro.RedactOpsMixin):
        MAX_UNDO = max_undo

        def __init__(self, d):
            self.doc = d
            self.current_page = 0
            self.selected_pages = set()
            self._undo_stack = collections.deque(maxlen=self.MAX_UNDO)
            self._redo_stack = collections.deque(maxlen=self.MAX_UNDO)
            self._preview_gen = 0
            self._thumb_gen = 0

        def _invalidate_thumb_cache(self, *a, **kw):
            pass

        def _refresh_all(self):
            pass

        def _t(self, key):
            return key

        def _set_status(self, *a):
            pass

    app = FakeApp(doc)
    app.plugin_manager = types.SimpleNamespace(fire_event=lambda *a, **kw: None)
    return app
```

### 実 Tk root を使うテストが必要な場合の既存パターン（`test_batch_ocr_dialog.py`）

```python
# Source: tests/test_batch_ocr_dialog.py（要旨）
# モジュールスコープで tk.Tk() を1つ共有し withdraw() で非表示化、
# after() 連鎖の検証には widget.mainloop() を実際に駆動して
# predicate() が True になるかタイムアウトまでポーリングする方式。
# Python 3.14 の tkinter 制約（after() はメインスレッドの mainloop 内実行を要求）
# に対応するための確立済みパターン。デバウンスタイマー（D-02）の実際の発火を
# 検証する場合はこのパターンの流用を検討する。
@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()
```

### 純関数のみのテスト（Tk root 不要・推奨アプローチ）

```python
# Source: tests/test_viewer.py:15-23（既存パターン。仮想化の純ロジック部分もこの形式で検証可能）
def _make_stub(doc):
    stub = types.SimpleNamespace(doc=doc)
    stub._render_preview_pixmap = ViewerMixin._render_preview_pixmap.__get__(stub)
    return stub
```
D-04 のプロパティ風テスト（500+ページ相当の `selected_pages` 不変条件検証）は、実際に 500 ページの `fitz.Document` を生成する必要はない。`pagination.py` の純関数群（`window_bounds`/`to_global`/`to_local` 等）と `set` 演算のみで `n_pages` を整数パラメータとしてシミュレートすれば十分（既存 `large_pdf_doc` フィクスチャは 47 ページで、500+ページの実 PDF 生成はテスト実行コストが高い）。

## State of the Art

本フェーズは既存コードベースの内部改修であり、外部エコシステムの「今どきのやり方」は該当しない。参考として、一般的な仮想化リストの設計原則との対比のみ記録する。

| Old Approach（一般的な仮想化リストの定石） | Current Approach（本フェーズの採用方式） | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ウィジェットプールによるスロットリサイクル（react-window 等） | ウィジェットは窓内全生成を維持し、画像描画のみ遅延化（D-01） | 本フェーズの D-01 決定 | 選択状態管理の複雑化を回避し、PERF-F01（本格仮想化）を将来へ明確に切り離す |

**Deprecated/outdated:** 該当なし（本フェーズで新規に何かを廃止するものはない）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | LRU 上限の具体値（300枚等）・デバウンス時間（150ms等）は CONTEXT.md の「例示」であり最終値ではない | Standard Stack / Architecture Patterns | 計画時に具体値を確定させないと実装が宙に浮く。ただし CONTEXT.md 側で既に「計画時判断」と明記されているため research 起因の risk ではない |
| A2 | `requirements.txt` の `PyMuPDF==1.28.0` と実際にインストールされている `1.27.2.3` の差異は本フェーズの実装（`get_pixmap`/`__del__`/`OrderedDict`）に影響しない | Standard Stack | 万一 PyMuPDF のマイナーバージョン差で `get_pixmap()` の挙動が変わっていた場合、可視範囲描画のタイミング調整に影響しうる（低リスク：本フェーズは呼び出し回数・順序を変えるだけで API 自体は不変） |
| A3 | メインウィンドウ直下の入力系ウィジェットは現状 `page_size_spin`（readonly）・`thumb_zoom_scale`/`mosaic_block_scale`（Scale）のみであり、Entry/Text クラスの直接の子孫ウィジェットは存在しない | Common Pitfalls (Pitfall 2) | 見落としがあった場合、フォーカスガードの実害範囲の記述が不正確になるが、ガード自体はクラス名ベースの汎用実装なので実装方針には影響しない |

**上記以外はすべてソースコード直接読解または実行時 Tkinter 挙動確認（VERIFIED）で裏取り済み。**

## Open Questions

1. **LRU コンテナの配置先（`pagination.py` 追加 vs 新規モジュール）**
   - What we know: CONTEXT.md D-08 は「新規モジュールまたは `pagination.py` への追加は計画時判断」と明記
   - What's unclear: `pagination.py` は現在「ページネーション窓表示専用」の命名になっており、汎用 LRU を同居させると責務が曖昧になる可能性がある
   - Recommendation: 新規モジュール `pagefolio/thumb_cache.py`（または `lru_cache.py`）として独立させ、`pagination.py` は窓計算のみに保つのが命名的に自然。ただし「新規モジュールを増やしすぎない」という本フェーズ全体の方針（D-01/D-11 双方が軽量案を選好）とのバランスは計画時に判断

2. **フォーカスガードを `_bind_shortcuts` のどのレイヤーに挿入するか**
   - What we know: `_bind_shortcuts` は `keysym` ごとに `lambda e, f=func: f()` を `root.bind` する。ガード判定には `event`（`e`）と `keysym` の両方が必要
   - What's unclear: 現在のラムダは `event` 引数 `e` を実質使っていない（`f()` は引数なしで呼ばれる）。ガード挿入時にラムダのシグネチャ変更が必要になる
   - Recommendation: `lambda e, f=func, ks=keysym: (None if should_suppress_for_focused_input(ks, self.root.focus_get().winfo_class() if self.root.focus_get() else "") else f())` のような形に変更する。`root.focus_get()` が `None` を返すケース（フォーカスなし）の防御が必要（実行時確認では通常フォーカスがどこかにあるが、防御的に扱うべき）

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 全実装 | ✓ | 3.14.6 [VERIFIED: ローカル `python --version`] | — |
| PyMuPDF (fitz) | サムネイル描画（変更なし） | ✓ | 1.27.2.3（インストール済み）/ 1.28.0（requirements.txt指定）[VERIFIED: ローカル `pip show`] | — |
| pytest | テスト実行 | ✓ | 9.1.1（requirements.txt） | — |
| ruff | Lint/Format | ✓ | 0.15.20（requirements.txt） | — |
| `collections.OrderedDict` | LRU実装 | ✓ | 標準ライブラリ同梱 | — |
| `sys.is_finalizing()` | `__del__` 終了時ガード | ✓ | 標準ライブラリ同梱（Python 3.4+） | — |

**Missing dependencies with no fallback:** なし。
**Missing dependencies with fallback:** なし（本フェーズは新規外部依存を導入しないため環境リスクは最小）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1（`requirements.txt`） |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`（`testpaths = ["tests"]`） |
| Quick run command | `pytest tests/test_pagination.py tests/test_viewer.py tests/test_undo_stress.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V180-PERF-01 | 可視範囲優先描画・デバウンス・アイドル先読みの純ロジック部分（座標変換・スケジューリング順序） | unit | `pytest tests/test_pagination.py -k visible -x`（新設関数名は計画時確定） | ❌ Wave 0（新設関数・新設テスト） |
| V180-PERF-02 | `thumb_cache` LRU 上限到達時のエビクション動作 | unit | `pytest tests/test_pagination.py -k lru -x`（配置先次第でファイル名変わる） | ❌ Wave 0（新設） |
| V180-PERF-03 | `selected_pages` 全ページインデックス不変条件（プロパティ風テスト） | property + unit | `pytest tests/test_selection_invariant.py -x`（新規ファイル・提案名） | ❌ Wave 0（新規ファイル） |
| V180-ROBUST-01 | Blob リーク検出ログ・Windows AV 衝突（`PermissionError` mock）・double-release 検出 | unit + stress | `pytest tests/test_undo_stress.py -x` | ✅ 既存ファイルへ3項目追加（D-14） |
| V180-ROBUST-03 | ShortcutsDialog WR-01（表示残留）・WR-02（フォーカスガード） | unit | `pytest tests/test_shortcuts_dialog.py -x`（新規ファイル・提案名） | ❌ Wave 0（`ShortcutsDialog` の単体テストがこれまで一切存在しない） |

### Sampling Rate
- **Per task commit:** `pytest tests/test_pagination.py tests/test_viewer.py tests/test_undo_stress.py tests/test_shortcuts_dialog.py tests/test_selection_invariant.py -x`（該当ファイルのみ）
- **Per wave merge:** `pytest`（全件）
- **Phase gate:** `pytest` 全件グリーン + `ruff check . && ruff format .` を `/gsd-verify-work` 前に確認

### Wave 0 Gaps
- [ ] `tests/test_shortcuts_dialog.py` — WR-01/WR-02 の回帰テスト（`ShortcutsDialog` 専用のテストファイルはこれまで存在しない。`_start_capture`/`_end_capture`/`_on_capture_keypress` は実 Tk ウィジェット依存のため、`tk.Tk()` を使うか、`types.SimpleNamespace` スタブで `_key_labels`/`_shortcuts` 等の最小属性を持たせたテスト用ハーネスを新設するかは計画時判断）
- [ ] `tests/test_selection_invariant.py` — D-04 プロパティ風テスト（`random.Random(seed)` 駆動・純関数のみで 500+ ページ相当をシミュレート。実 `fitz.Document` は不要）
- [ ] `pagination.py`（または新規 LRU モジュール）への可視範囲純関数・LRU コンテナのユニットテスト（配置先確定後に対応ファイルへ追加）
- [ ] フォーカスガード純関数（`should_suppress_for_focused_input` 等）のユニットテスト（Tk非依存なので `test_shortcuts_dialog.py` か新規小テストファイルのどちらでも可）

## Security Domain

`.planning/config.json` の `security_enforcement: true`（`security_asvs_level: 1`, `security_block_on: "high"`）により本セクションを含める。ただし本フェーズはローカルデスクトップアプリの内部堅牢性改修であり、認証・セッション・ネットワーク送信・暗号化は一切扱わない。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 該当機能なし（本フェーズはOCR/APIキー等に触れない） |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 該当なし（単一ユーザーローカルアプリ） |
| V5 Input Validation | 部分的 yes | ショートカットキー入力（`build_keysym_from_event`/`find_duplicate_binding`）は既存の検証パターンをそのまま踏襲。フォーカスガードは新規の入力経路ではなく既存キー入力の発火制御のみ |
| V6 Cryptography | no | 該当なし（Blob は tempfile への平文退避のまま・v1.7.0 から変更なし） |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `thumb_cache` の無制限成長によるメモリ枯渇（DoS相当） | Denial of Service | LRU 化により上限を設ける（本フェーズの主目的そのもの・V180-PERF-02） |
| Blob 一時ファイルの残留（ディスク容量枯渇） | Denial of Service | `__del__` によるリーク検出ログ＋ベストエフォート回収（V180-ROBUST-01）。既存の `purge`/atexit 二段回収と併用 |
| `__del__` 実行スレッドの不定性（Blob が GC される瞬間のスレッドは保証されない） | （STRIDE外・信頼性の懸念） | `logging` モジュール自体はスレッドセーフ。ただし本フェーズの Blob は undo/redo スタック経由でのみ生成・参照され、いずれもメインスレッド上の操作（OCR ワーカースレッドは Blob を扱わない）であることを `file_ops.py`/`ocr_pipeline.py` の設計から確認済み。実質的にクロススレッド GC 発火のリスクは低い |

## Sources

### Primary (HIGH confidence)
- `pagefolio/viewer.py`（`ViewerMixin` 全体） - サムネイル描画・`thumb_cache`・世代ガードの現行実装を直接読解
- `pagefolio/pagination.py` - 窓表示純関数群を直接読解
- `pagefolio/undo_store.py` - `MemBlob`/`FileBlob`/`UndoBlobStore` を直接読解
- `pagefolio/file_ops.py` - Blob ライフサイクル呼び出し面（`_capture_page_blob`/`_dispose_state`/`_push_evicting`/`_clear_undo_stacks`）を直接読解
- `pagefolio/dialogs/shortcuts.py` - `ShortcutsDialog` 全体、特に `_start_capture`/`_end_capture` を直接読解し WR-01 の原因を特定
- `pagefolio/app.py` - `build_keysym_from_event`/`find_duplicate_binding`/`_bind_shortcuts`/`_default_shortcuts` を直接読解し WR-02 の発火面を特定
- `pagefolio/dnd.py` - 可視範囲計算の前例パターン（`compute_dnd_dest_index`/`_dnd_dest_index`）を直接読解
- ローカル Tkinter ランタイム実行検証（`root.bind_class('Entry', '<Delete>')` の中身確認・`event_generate` による `event.widget`/`focus_get()` の実証） - 本セッション内で実行し確認
- `tests/test_undo_stress.py`・`tests/test_viewer.py`・`tests/test_pagination.py`・`tests/test_batch_ocr_dialog.py` - 既存テストパターンの精読
- `.planning/codebase/CONCERNS.md` §Blob Lifecycle Management / §Thumbnail Cache No Eviction / §D&D Multi-Page Reordering / §Blob Lifecycle Edge Cases - 既知課題の出典確認
- `.planning/research/PITFALLS.md` 落とし穴1・2 - サムネイル仮想化の中心的リスク

### Secondary (MEDIUM confidence)
- [Python collections — Container datatypes](https://docs.python.org/3/library/collections.html) - `OrderedDict.move_to_end`/`popitem` の公式挙動確認
- [PEP 442 – Safe object finalization](https://peps.python.org/pep-0442/) - `__del__`/`sys.is_finalizing()` の設計背景
- [LRU Cache in Python using OrderedDict - GeeksforGeeks](https://www.geeksforgeeks.org/python/lru-cache-in-python-using-ordereddict/) - LRU実装パターンの一般的裏取り

### Tertiary (LOW confidence)
- なし（本フェーズの主要な知見は全て一次情報源＝自リポジトリのコードと実行時検証で確定できたため、未検証の外部情報への依存はない）

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH - 新規パッケージ導入なし、既存 requirements.txt とローカル環境を直接確認
- Architecture: HIGH - 全パターンを既存ソースコードの直接読解、または実行時 Tkinter 挙動確認で裏取り
- Pitfalls: HIGH - WR-01/WR-02 は実装コードの読解＋実行時検証で原因を確定済み（推測ではない）。落とし穴1/2 は PITFALLS.md の既存curated調査を踏襲

**Research date:** 2026-07-16
**Valid until:** 2026-08-15（30日・本フェーズはコードベース内部改修のため陳腐化リスクは低いが、`requirements.txt` のPyMuPDFバージョン差異など環境要因の再確認目安として設定）
