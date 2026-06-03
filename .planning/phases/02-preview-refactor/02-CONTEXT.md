# Phase 2: プレビュー最適化とリファクタリング - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

ページ切り替え時のフルシリアライズ（`viewer.py:69` の `self.doc.tobytes()`）を廃止し、
`dialogs.py`（1,191 行・6 クラス）と `constants.py`（711 行）を分割して、主要モジュールを管理可能な行数にする。

スコープは **BUG-03 / REFAC-01 / REFAC-02 / TEST-02** のみ。

- BUG-03: ページ切り替え時にプレビューのシリアライズを行わない（`page.get_pixmap()` 直接呼び出し）
- REFAC-01: `dialogs.py` を `pagefolio/dialogs/` サブパッケージに分割
- REFAC-02: `constants.py` を `lang.py` / `themes.py` / `constants.py` に分割
- TEST-02: BUG-03 の回帰テスト（`_show_preview()` が `tobytes()` を呼ばないことを確認）

REFAC-04（settings 公開 API 化）/ TEST-03（import 回帰テスト）は Phase 3。新機能追加・UI/UX 変更はスコープ外。

</domain>

<decisions>
## Implementation Decisions

### BUG-03: プレビューのスレッド戦略
- **D-01:** プレビューレンダリングは **メインスレッドで `self.doc[page_idx].get_pixmap()` を同期呼び出し**する。現状の「doc 全体を `tobytes()` → ワーカースレッドで `fitz.open(stream=...)` し直して get_pixmap」方式を撤廃する。1 ページ分の pixmap 生成は全体シリアライズより遥かに軽く、fitz の `Document` をスレッドへ渡せない制約（Phase 1 D-02）も回避できる。SC-1「`doc.tobytes()` が呼ばれない」・TEST-02 をクリーンに満たす。
- **D-02:** 単一ページ小 bytes をスレッドに渡す案・ページ単位 pixmap キャッシュ案は **不採用**（前者は一時 doc で `tobytes()` を呼ぶため TEST-02 と衝突しうる、後者は Phase 2 にはオーバースペック）。
- **D-03（影響範囲メモ）:** スレッド廃止に伴い、`_preview_gen` による stale 結果破棄ロジックと「...」ローディングプレースホルダーは**同期化後に不要になる可能性が高い**。残すか撤去するかは planner/executor 裁量だが、撤去する場合は他箇所（サムネイル側 `_thumb_gen` 等）への波及がないことを確認すること。

### REFAC-02: 可変 `C` dict の置き場所
- **D-04:** `THEMES` と実行時可変 dict `C` を **`themes.py` に定義**する。`C` は `_apply_theme` が `C.update(THEMES[resolved])`（`settings.py:95`）で **in-place 更新**しており識別子が保たれるため、`constants.py` で `from pagefolio.themes import C` として **再エクスポート**すれば既存の `from pagefolio.constants import C`（および `C["BG_DARK"]` 等の全参照）はそのまま動作する。SC-3 の後方互換を満たす。
- **D-05:** 全モジュールの import を `themes` 直参照へ一斉書き換えする案は不採用（変更面が広く後方互換検証コストが高い）。再エクスポート方式で `import` の物理変更を最小化する。

### REFAC-01 / REFAC-02: 分割粒度
- **D-06:** REQUIREMENTS.md の分割案を**そのまま採用**する。
  - `dialogs/` → `__init__.py`（後方互換の再エクスポート集約）, `about.py`, `settings.py`, `plugin.py`, `merge.py`（MergeOrderDialog + MergeResizeDialog を同居）, `llm_config.py`
  - `constants.py` → `lang.py`（`LANG` 辞書 約650行）, `themes.py`（`THEMES` / `C`）, `constants.py`（`APP_VERSION` / `SETTINGS_FILE` / `PLUGINS_DIR` / `SUPPORTED_EXTENSIONS` / `IMAGE_EXTENSIONS`）
- **D-07:** 既存の公開 import 表面（`pagefolio/__init__.py` の `from pagefolio.dialogs import ...` / `from pagefolio.constants import APP_VERSION, LANG, THEMES, C`）は**維持必須**。分割後はサブパッケージ `__init__.py` と `constants.py` の再エクスポートで吸収する。

### TEST-02: 検証手法・置き場所
- **D-08:** プレビューレンダリングの中核を **Tk 非依存の純関数ヘルパー**（例: `_render_preview_pixmap(page_idx, zoom)` — page・zoom を受けて samples/size を返す）に抽出し、それを `tests/test_viewer.py`（**新規**）で単体テストする。Tk Canvas やスレッドに依存せずテストできる。`_show_preview()` 全体を Tk root 込みでテストする案・モジュールレベルで `tobytes` をスパイする案は不採用（CI/ヘッドレスで脆い・複雑）。
- **D-09:** TEST-02 は「中核ヘルパー（および `_show_preview` 経路）が `doc.tobytes()` を呼ばない」ことを `monkeypatch` で `fitz.Document.tobytes` をスパイして検証する。併せて get_pixmap で妥当なサイズの画像 samples が得られることを確認する。

### Claude's Discretion
- 純関数ヘルパーの正確なシグネチャ・戻り値の型（samples+size のタプル vs PIL Image）は planner/executor 裁量。
- `_preview_gen` / ローディングプレースホルダーの撤去可否（D-03）は planner/executor 裁量。撤去時は波及確認必須。
- 各 dialog/constants ファイルへのシンボル割り当ての細部（import 順・`__all__` の有無）は executor 裁量。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・トレーサビリティ
- `.planning/REQUIREMENTS.md` — BUG-03 / REFAC-01 / REFAC-02 / TEST-02 の定義・対象行・分割案
- `.planning/ROADMAP.md` §Phase 2 — ゴールと成功基準（4 項目: tobytes 不使用・dialogs サブパッケージ・constants 分割・回帰テスト）
- `.planning/PROJECT.md` §Key Decisions — BUG-03 の方針メモ（`page.get_pixmap()` 直接呼び出し）

### 対象コード
- `pagefolio/viewer.py` §`_show_preview`（lines 41–127）— BUG-03 の中核。`:69` `self.doc.tobytes()` が撤廃対象。`worker()`（:83–97）でスレッド再オープン+get_pixmap、`_apply()`（:99–125）で Canvas 描画。同期化＋純関数抽出の対象。
- `pagefolio/dialogs.py`（1,191 行）— REFAC-01 の分割対象。クラス位置: AboutDialog:24 / SettingsDialog:98 / LLMConfigDialog:264 / PluginDialog:671 / MergeOrderDialog:867 / MergeResizeDialog:1045。
- `pagefolio/constants.py`（711 行）— REFAC-02 の分割対象。`THEMES`:8 / `C = dict(THEMES["dark"])`:44 / `APP_VERSION`:47 / `SETTINGS_FILE`:50 / `PLUGINS_DIR`:51 / `SUPPORTED_EXTENSIONS`:54 / `IMAGE_EXTENSIONS`:58 / `LANG`:59〜。
- `pagefolio/settings.py` §`_apply_theme`（:92–95）— `C.update(THEMES[resolved])` の in-place 更新（D-04 の前提）。`from pagefolio.constants import SETTINGS_FILE, THEMES, C`（:10）も分割で要追従。
- `pagefolio/__init__.py`（:8–35）— 公開 import 表面。`from pagefolio.constants import APP_VERSION, LANG, THEMES, C`（:9）・`from pagefolio.dialogs import (...)`（:12）の後方互換維持対象。

### コードベースマップ
- `.planning/codebase/ARCHITECTURE.md` §Threading / State Management — fitz スレッドセーフ制約・`_preview_gen`/`_thumb_gen` 世代カウンタの記述（D-01/D-03 の前提）
- `.planning/codebase/CONCERNS.md` — 既知の懸念点

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_show_preview` の `worker()` 内の純レンダリングロジック（`page.get_pixmap(matrix=...)` → `bytes(pix.samples)` → `(w, h)`）は、Tk 非依存ヘルパーへほぼそのまま抽出できる（D-08）。
- サムネイル生成（`viewer.py` のサムネイル系メソッド）が同様の fitz→PIL→Tk 変換を持つ可能性があり、純関数抽出の参考になる。planner は重複の有無を確認のこと。
- `pagefolio/__init__.py` と各サブパッケージ `__init__.py` の再エクスポートパターンが、分割後の後方互換吸収にそのまま使える。

### Established Patterns
- テーマ色は `C["KEY"]` で参照（グローバル文字列禁止）。`C` の識別子保持（in-place 更新）が全モジュールの前提。分割で `C` を別オブジェクトに作り替えてはならない（`C.clear()`/`C.update()` ベースを維持）。
- テストは UI ではなくロジックを対象にする方針（`tests/test_pdf_ops.py` 参照）。TEST-02 の純関数抽出はこの方針と整合。
- `_show_preview` は描画後に Canvas の `scrollregion` を設定する（:125）。同期化後もこの後処理は維持する。

### Integration Points
- `_apply_theme`（settings.py）は `THEMES` と `C` の双方に依存。REFAC-02 の分割時、`settings.py` の import 行（`:10`）を新モジュール構成へ追従させる。
- `_show_preview` を同期化すると呼び出し側（ページ遷移 `_prev_page`/`_next_page`/`_refresh_all` 等）から見た挙動は「即時描画」に変わる。例外時の挙動（現状 worker 内 `except` でログのみ）を同期版でも担保する（裸 except 禁止、`except Exception as e:` + logger）。

</code_context>

<specifics>
## Specific Ideas

- BUG-03 の核心は「ページ切り替えのたびにドキュメント全体を直列化しない」こと。1 ページの pixmap をメインスレッドで同期生成する最小構成をゴールとする。
- リファクタの核心は「後方互換 import 表面を一切壊さずに物理ファイルを分割する」こと。`__init__.py` / `constants.py` の再エクスポートで吸収する。

</specifics>

<deferred>
## Deferred Ideas

- REFAC-04（`settings._current_font_size` 公開 API 化）/ TEST-03（REFAC-01〜04 の import 回帰テスト）— Phase 3
- サムネイル仮想化（大規模 PDF のメモリ最適化）— v2（スコープ外）
- ページ単位 pixmap キャッシュによる再表示高速化（D-02 で今回不採用）— 将来のパフォーマンス改善候補
- `_preview_gen` 世代カウンタの完全撤去（D-03）— 同期化後に不要と確定できれば Phase 2 内、または別途整理タスクとして扱う

</deferred>

---

*Phase: 2-プレビュー最適化とリファクタリング*
*Context gathered: 2026-06-03*
