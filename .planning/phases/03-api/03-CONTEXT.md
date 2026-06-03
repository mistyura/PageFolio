# Phase 3: API 整理と回帰テスト - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

`settings.py` の可変モジュール変数 `_current_font_size` への **外部アクセスを公開 API 経由に置き換える**（REFAC-04）と、
REFAC-01〜04 で変わった **import パスの回帰テストを整備**する（TEST-03）。

スコープは **REFAC-04 / TEST-03** のみ。

- REFAC-04: `settings._current_font_size` への外部アクセスを公開関数経由にする。
  - **write 側:** `app.py`（:51, :348）の `_settings_mod._current_font_size = self.font_size` 直接代入を `set_current_font_size(size)` 経由に変更。
  - **read 側:** `dialogs/merge.py`（:14, :33, :213）・`dialogs/llm_config.py`（:12, :51）の `from pagefolio.settings import _current_font_size` を getter 経由に変更。
- TEST-03: REFAC-01〜04 で変更された全 import パスが壊れていないことを検証する import 回帰テストを `tests/test_imports.py`（新規）に整備。

新機能追加・UI/UX 変更・`pyproject.toml`/`ruff.toml` 変更はスコープ外。SC-3 として `ruff check . && ruff format .` がエラーなしであること。

</domain>

<decisions>
## Implementation Decisions

### REFAC-04: スコープ範囲（write + read の完全 API 化）
- **D-01:** REFAC-04 は **write 側だけでなく read 側も含めて完全に公開 API 化**する。`app.py` の直接代入を setter 経由にするだけでなく、`dialogs/merge.py` / `dialogs/llm_config.py` の `from pagefolio.settings import _current_font_size`（プライベート変数の外部 import）も **getter 経由の参照に変更**する。DEBT-04「プライベート変数への外部アクセス」を write/read 両面で全面解消する。
- **D-02（stale binding 修正の意図）:** 現状の `from pagefolio.settings import _current_font_size` は **import 時点の int 値（12）を束縛**するため、`app.py` が後から `_settings_mod._current_font_size = ...` で書き換えても dialogs 側には反映されない潜在バグがある。getter（呼び出し時に最新値を読む）に変更することでこの stale binding を修正する。これに伴い dialogs のフォントサイズが「生値（実行時の設定値）」になる **軽微な挙動変化を許容**する（これは DEBT-04 が意図する本来の正しい挙動）。
- **D-03（最小案は不採用）:** 「app.py の write のみ setter 化し dialogs の read はそのまま残す」最小案は不採用。ROADMAP SC-1 は文字通り満たせるが、dialogs の private import が残り DEBT-04 の趣旨（外部アクセス全廃）を満たさず、stale binding も未修正のままになるため。

### REFAC-04: setter の挙動
- **D-04:** `set_current_font_size(size)` は **単純代入のみ**（モジュール変数 `_current_font_size` をそのまま書き換える）。クランプ等のバリデーションは入れない。REFAC（リファクタリング）は挙動を変えないのが原則で、現状 `app.py` が渡す値をそのまま反映する挙動を完全維持する。クランプを入れると `font_size`（8〜16）と settings デフォルト 12 の不整合を動かしうる挙動変化を招くため不採用。
- **D-05（getter 命名・公開サーフェスは executor 裁量、ただし対称性推奨）:** read 側の getter 名（例: `get_current_font_size()`）と、setter/getter を `pagefolio/__init__.py` の公開サーフェスへ追加するか否かは executor 裁量。ただし既存 `__init__.py` が `_apply_theme` / `_make_font` 等の private 関数も再エクスポートしている前例に倣い、`set_current_font_size` / getter も追加して公開表面の一貫性を保つことを推奨。

### TEST-03: 網羅範囲と検証手法
- **D-06:** 検証手法は **明示 import 文 ＋ シンボル存在 assert**。後方互換サーフェスを実際の import 文としてテストに書き下し、import が例外を投げずシンボルが取得できることを確認する。`importlib` でモジュール名リストをパラメータ化する動的方式は不採用（壊れた箇所の読み取りがやや抽象的なため）。明示 import は「何が壊れたか」が一目瞭然。
- **D-07（網羅すべき import パス）:** 最低限カバーするパス：
  - 公開 API（REFAC-01/02 後方互換）: `from pagefolio.constants import APP_VERSION, LANG, THEMES, C`
  - dialogs サブパッケージ（REFAC-01）: `from pagefolio.dialogs import AboutDialog, SettingsDialog, PluginDialog, MergeOrderDialog, MergeResizeDialog`（および分割後の個別モジュール `pagefolio.dialogs.about` / `.settings` / `.plugin` / `.merge` / `.llm_config`）
  - 分割新モジュール（REFAC-02）: `from pagefolio.lang import LANG`、`from pagefolio.themes import THEMES, C`
  - settings 新公開 API（REFAC-04）: `from pagefolio.settings import set_current_font_size`（＋ D-05 の getter）
  - パッケージ公開サーフェス: `import pagefolio` → `pagefolio.PDFEditorApp` / `pagefolio.APP_VERSION` / `pagefolio.LANG` / `pagefolio.THEMES` / `pagefolio.C` 等が解決すること
  - planner は `pagefolio/__init__.py`（現行公開サーフェス全体）を参照し、列挙漏れがないか突き合わせること。
- **D-08（Tk 依存への留意）:** dialogs モジュールは `tkinter` を import する。回帰テストは **モジュール import のみ**（ダイアログ class の **インスタンス化はしない**）に留めれば、ヘッドレス/CI でも root 不要で安全。既存 `tests/conftest.py` の方針と整合させること。

### TEST-03: テストファイル配置
- **D-09:** import 回帰テストは **新規 `tests/test_imports.py` に集約**する。REQUIREMENTS.md の「tests/ 各ファイル」記述よりも、TEST-03（REFAC-01〜04 の後方互換検証）を 1 箇所にまとめる方が責務が明確で見通しが良い。

### Claude's Discretion
- getter の正確な名前（`get_current_font_size()` 等）と、`pagefolio/__init__.py` 公開サーフェスへの追加可否（D-05、ただし対称性のため追加推奨）。
- `test_imports.py` 内のテスト関数の分割粒度（1 関数に集約 vs パス種別ごとに分割）・assert の具体形。
- 実装順序（REFAC-04 を先に行い、その新 import パスも TEST-03 に含めるのが自然）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・トレーサビリティ
- `.planning/REQUIREMENTS.md` — REFAC-04 / TEST-03 の定義・対象行・変更方針（§リファクタリング・§テスト・§Traceability）
- `.planning/ROADMAP.md` §Phase 3 — ゴールと成功基準（3 項目: `set_current_font_size()` 存在＋app.py が直接書き換えない / import 回帰テスト存在 / pytest 全通＋ruff エラーなし）
- `.planning/PROJECT.md` §Problem Statement（DEBT-04）・§Key Decisions — プライベート変数外部アクセスの問題定義

### 対象コード（REFAC-04）
- `pagefolio/settings.py` §`_current_font_size`（:107）— 公開 setter/getter を追加する対象。可変モジュール変数（int）。
- `pagefolio/app.py`（:49–51, :346–348）— `import pagefolio.settings as _settings_mod` ＋ `_settings_mod._current_font_size = self.font_size` の直接代入 2 箇所。setter 経由へ変更する write 側。
- `pagefolio/dialogs/merge.py`（:14 import, :33・:213 で `self._font_size = _current_font_size`）— getter 経由へ変更する read 側。
- `pagefolio/dialogs/llm_config.py`（:12 import, :51 で `fs = _current_font_size`）— getter 経由へ変更する read 側。

### 対象コード（TEST-03 の検証対象サーフェス）
- `pagefolio/__init__.py`（全体）— 後方互換の公開 import サーフェス。constants 再エクスポート（:9）・dialogs 再エクスポート（:12–18）・settings 再エクスポート（:35–44）。回帰テストの基準。
- `pagefolio/dialogs/__init__.py` — REFAC-01 のサブパッケージ再エクスポート（Phase 2 成果）。
- `pagefolio/constants.py` / `pagefolio/lang.py` / `pagefolio/themes.py` — REFAC-02 の分割後モジュール（Phase 2 成果）。`constants.py` は `lang`/`themes` からの再エクスポートで後方互換を維持。
- `tests/conftest.py` — テスト共通フィクスチャ（Tk 非依存方針・import 時の前提）。
- 既存テスト群（`tests/test_pdf_ops.py`・`test_plugins.py`・`test_utils.py`・`test_viewer.py`・`test_ocr.py`）— 既存 import パターンの参考（`import pagefolio` / `import pagefolio.X as _mod`）。

### コードベースマップ
- `.planning/codebase/CONVENTIONS.md` — テーマ色 `C["KEY"]` 参照・private プレフィックス等の命名規約（API 設計の前提）
- `.planning/codebase/TESTING.md` — 既存テスト方針（UI でなくロジックを対象・Tk 非依存）

### 前フェーズ Context
- `.planning/phases/02-preview-refactor/02-CONTEXT.md` — REFAC-01/02 の分割粒度（D-06）・再エクスポート方式（D-07）。TEST-03 が検証すべき import パスの根拠。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 既存テストの import パターン（`import pagefolio` / `from pagefolio import X` / `import pagefolio.X as _mod`、`tests/test_pdf_ops.py`・`test_utils.py` 等）が、`test_imports.py` の明示 import 文の書き方にそのまま流用できる。
- `pagefolio/__init__.py` の再エクスポートブロックが、回帰テストで「どのシンボルが公開されているべきか」の網羅リストの一次ソースになる。

### Established Patterns
- `__init__.py` は private 関数（`_apply_theme` / `_make_font` 等）も再エクスポートしている。→ `set_current_font_size` / getter を公開サーフェスへ追加するのは既存パターンと整合（D-05）。
- テストは UI ではなくロジック/構造を対象にする（Tk root を立てない）。→ TEST-03 は **import のみ・インスタンス化なし** でこの方針に整合（D-08）。
- 裸の `except:` 禁止・`except Exception as e:` ＋ logger（CLAUDE.md 禁止事項）。setter/getter は単純なので例外処理は基本不要だが、追加する場合はこの規約に従う。

### Integration Points
- `_current_font_size` の **write は app.py の 2 箇所**（初期化 :51 と設定更新 :348）、**read は dialogs の 3 箇所**（merge.py :33/:213、llm_config.py :51）。setter は app.py 側、getter は dialogs 側に閉じており、変更面は限定的。
- read 側を getter 化する際、`from pagefolio.settings import _current_font_size`（モジュール先頭）を `from pagefolio.settings import get_current_font_size`（または `import pagefolio.settings as _settings_mod` で呼び出し時参照）に変更し、**使用箇所（メソッド内）で呼び出す**ことで stale binding を解消する（D-02）。

</code_context>

<specifics>
## Specific Ideas

- REFAC-04 の核心は「`_current_font_size` という private モジュール変数を、外から **直接代入も直接 import 参照もしない** 状態にする」こと。write は setter、read は getter に一本化する。
- TEST-03 の核心は「REFAC-01〜04 の分割・再エクスポートで **既存 import 表面が一切壊れていない** ことを機械的に保証する」こと。明示 import 文で「壊れたら即わかる」テストにする。
- 副次的価値: getter 化により dialogs が **実行時の最新フォントサイズ** を反映するようになる（現状の import-time stale binding バグの解消）。

</specifics>

<deferred>
## Deferred Ideas

- setter のバリデーション（クランプ 8〜16 等）— 今回は単純代入のみ（D-04）。挙動変更を伴うため、必要になれば別タスク。
- 他の private モジュール変数・グローバル状態（`themes.C` の in-place 更新等）の API 化 — 今回スコープ外（`C` は Phase 2 で識別子保持が前提化済み、変更しない）。
- サムネイル仮想化・暗号化 PDF・印刷機能・OCR エンジン拡張 — v2（スコープ外）。

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-API 整理と回帰テスト*
*Context gathered: 2026-06-03*
