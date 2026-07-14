# Phase 2: AI強化（プロンプト・テンプレート管理 + プロバイダーフォールバック） - Research

**Researched:** 2026-07-14
**Domain:** Tkinter デスクトップアプリの既存 LLM 設定ダイアログ（`pagefolio/dialogs/llm_config/`）への機能追加（設定永続化 CRUD + OCR実行オーケストレーションへのフォールバック層挿入）
**Confidence:** HIGH（既存コードベース直接精査が一次情報源。新規外部ライブラリ・新規 API 呼び出しなし、既存パターンの延長のみ）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### テンプレート保存モデル
- **D-01:** テンプレートは「ペア保存」方式。1テンプレート = カスタムプロンプト + サマリプロンプトの組。UI はテンプレート選択欄1つで両方が同時に切り替わる（別々の独立した一覧は不採用）。
- **D-02:** 永続化形式は `pagefolio_settings.json` 内の辞書構造（既存の `_load_settings`/`_save_settings` パターンをそのまま延長）。専用ディレクトリの個別 md ファイル方式は不採用（PITFALLS.md 落とし穴で「v1.8.0 スコープ内はベタ書き許容」とされている想定どおり）。
- **D-03:** 使用中（アクティブ）テンプレートの削除は禁止する。削除ボタンを無効化するか、削除前に他テンプレートへの切替を促す（誤操作でカスタムプロンプトが消える事故を防止）。
- **D-04:** テンプレート名の重複は保存時に拒否する。`ShortcutsDialog` の重複拒否パターン（保存時に同名があればエラー表示）を踏襲する。

#### 外部mdファイル連動との共存
- **D-05:** テンプレート切替時、外部 md ファイル（`ocr_custom_prompt.md`/`ocr_summary_prompt.md`）に未保存の変更がある場合は確認ダイアログ（`messagebox.askyesno`）を挟む。キャンセルで切替を中止する（PITFALLS.md 落とし穴6の推奨策）。
- **D-06:** ファイル連動モード（外部ファイルが存在する状態）で新規テンプレートを「保存」する際は、現在の入力欄の内容（開いた時点で外部ファイル内容が反映済み）をそのままテンプレートへコピーする。
- **D-07:** テンプレート切替後は、選択したテンプレートの内容で外部 md ファイルを上書きする（既存の「適用時に入力欄→ファイルへ書き戻し」挙動を踏襲）。外部ファイルは常に「現在アクティブなテンプレートのライブ編集内容」という位置づけを維持し、複数テンプレートの概念を外部ファイル側には持ち込まない。
- **D-08:** 外部ファイル内容と現在のテンプレート内容の不一致（外部エディタでの編集済み）を検知する専用UIは新設しない。既存の `_add_prompt_file_notice`（「ファイル連動中」注記）をそのまま流用し、D-05 の切替時確認ダイアログのみで十分とする。

#### フォールバック実行時の挙動
- **D-09:** フォールバック候補へ切替えた後、OCR は未処理ページのみ再開する。既存の resume/`_pending_pages()` 仕組みをそのまま流用し、成功済みページは保持したまま失敗/未処理ページのみ新プロバイダで再実行する。
- **D-10:** フォールバック連鎖は1回限りに制限しない。設定されたチェーンを最後まで順に辿り、各段で送信先確認ダイアログを毎回再提示する（自動連鎖送信はしない方針との整合・CR-01 パターン踏襲）。
- **D-11:** フォールバックの発火条件は `PipelineState.fatal_msg` が確定する全ケース（サーキットブレーカー発動・connection/timeout・APIキー未設定）とする。APIキー未設定を理由とするフォールバック提案時は、確認ダイアログにその理由を明示する（PITFALLS.md 落とし穴8で言及される「静かな握りつぶし」を防ぐ）。
- **D-12:** 全ページ統合サマリ生成時の失敗にも同じフォールバック順を適用する。既存の `_confirm_summary_cost` 等サマリ専用確認経路を流用し、OCR と同様の挙動にする。

#### フォールバック順設定UI
- **D-13:** フォールバック順の並び替えUIは「リスト + 上へ/下へボタン」方式。`MergeOrderDialog`（`pagefolio/dialogs/merge.py`）の `tk.Listbox` + 上へ/下へボタンパターンをそのまま流用する（ドラッグ&ドロップは不採用・実装コスト回避）。
- **D-14:** フォールバック候補には全プロバイダを一覧に含める（APIキー未設定のプロバイダも表示）。未設定のまま実行された場合は D-11 の発火条件どおり「APIキー未設定」を明示エラーとして扱い、次のフォールバック候補へ進む。
- **D-15:** フォールバック設定UIは LLM 設定ダイアログ内に新規独立セクション（例:「🔁 フォールバック」）として配置する。既存の「OCRプロバイダ選択」セクションへの埋め込みは行わない（sections.py の既存責務別 Mixin 構造をそのまま拡張）。
- **D-16:** フォールバック設定の初期表示は「有効化トグル + 順序リスト」。既定は「フォールバックなし（空リスト・トグルOFF）」で確定済み（V180-FALL-01）。トグルをONにすると順序リストが現れる構成とし、未設定ユーザーにもフォールバック機能の存在が分かりやすい形にする。

### Claude's Discretion
- テンプレートデータの settings.json 内スキーマ詳細（キー名・テンプレート辞書の具体的な構造）
- フォールバック順設定の内部データ構造（settings.json への保存キー名・リスト形式）
- 新規独立セクション（D-15）を sections.py 内のどのメソッド分割単位に配置するか
- 送信先確認ダイアログ再提示（D-10）の具体的なメッセージ文言（フォールバック理由の表示方法）

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope（4領域とも計画どおり完了。スコープ外提案は出なかった）。
`ocr_dialog.py` の分割・OCRRunEngine 抽出（Phase 3）・バッチ複数ファイル OCR（Phase 4）・自動ベンダー切替やコスト最適化ルーティング（PROJECT.md で確定除外）も本フェーズのスコープ外。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V180-TMPL-01 | ユーザーは OCR カスタム/サマリプロンプトを名前付きテンプレートとして保存できる | `## Architecture Patterns` Pattern 1（テンプレート永続化スキーマ）・`settings.py` の `_load_settings`/`_save_settings` 拡張方針 |
| V180-TMPL-02 | ユーザーはテンプレート一覧から選択して切り替えられる（LLM 設定ダイアログ） | Pattern 2（テンプレート選択 UI・combobox 流用）・`## Code Examples` |
| V180-TMPL-03 | ユーザーはテンプレートを削除・リネームできる | Pattern 1 + `ShortcutsDialog` 重複拒否パターン（D-04）・D-03（アクティブ削除禁止） |
| V180-TMPL-04 | 外部 md ファイル連動は「アクティブテンプレートのライブ編集」として共存する（書き戻し競合を起こさない） | Pattern 3（外部ファイル連動とテンプレートの関係）・Pitfall 1（落とし穴6踏襲） |
| V180-TMPL-05 | テンプレートは全プロバイダで横断共有される（`resolve_ocr_prompt` の優先順位にテンプレート層を挿入） | Pattern 4（`resolve_ocr_prompt`/`resolve_summary_prompt` への層挿入）・`## Code Examples` |
| V180-FALL-01 | ユーザーはフォールバック順を明示的に設定できる（未設定＝フォールバックしない） | Pattern 5（フォールバック順 UI・`MergeOrderDialog` パターン流用）・D-16（安全側既定） |
| V180-FALL-02 | フォールバック候補への切替が送信先確認ダイアログの再提示つきで提案される（自動送信なし） | Pattern 6（フォールバックオーケストレーション・`_finish_error`/`_on_summary_error` フック）・Pitfall 2（同意迂回防止） |
| V180-FALL-03 | フォールバック切替時、並列度・APIキー解決・レート制限設定が正しく引き継がれる | Pattern 6 + Pitfall 3（`build_provider` 再評価の必要性・プロバイダ別 `max_concurrency` 差異） |
</phase_requirements>

## Summary

本フェーズは新規外部依存を一切追加せず、既存の3つの成熟パターン——(1) `settings.py` の辞書ベース設定永続化、(2) `resolve_ocr_prompt`/`resolve_summary_prompt` の優先順位純関数、(3) `ocr_dialog.py` の producer-consumer 実行 + `PipelineState.fatal_msg` 確定後の完了処理（`_finish_error`）——を薄く拡張することで、テンプレート管理とプロバイダーフォールバックを実現する。UI 面は `pagefolio/dialogs/llm_config/sections.py` に新規セクションを追加し、`MergeOrderDialog`（リスト+上へ/下へボタン）と `ShortcutsDialog`（保存時重複拒否）という既に実戦投入済みの UI パターンをそのまま複製する。

最大の技術的難所はフォールバック側にある。現在の `OCRDialog` は `self.app.settings.get("ocr_provider", "")` を `_is_cloud_provider()`/`_confirm_cost()`/`_check_cloud_api_key()` の各所で直接参照しており、単一プロバイダの実行を前提に設計されている。フォールバック実装では「ダイアログセッション内でのみ有効な、切替後プロバイダの一時設定スナップショット」を導入し、これらのヘルパーをプロバイダ名引数対応に一般化する必要がある。ここで `self.app.settings`（グローバル永続設定辞書）を直接書き換えると、ユーザーが明示的に選んでいない「フォールバック中に使ったプロバイダ」がそのまま既定プロバイダとして `pagefolio_settings.json` に残ってしまう事故につながる（新規に発見した落とし穴・後述）。

テンプレート側の主要リスクは PITFALLS.md 落とし穴6（外部mdファイル書き戻し競合）で、CONTEXT.md の D-05〜D-08 により対策方針は既に確定している。実装時は「外部ファイル＝現在アクティブなテンプレートのライブ編集内容」という不変条件を破らないことが唯一の判断基準になる。

**Primary recommendation:** テンプレート管理は `settings.py` に `prompt_templates`（辞書: `{"active": str, "items": {name: {"custom_prompt": str, "summary_prompt": str}}}`）を追加する形で実装し、フォールバックは `pagefolio/ocr_fallback.py`（新規・Tk/fitz 非依存の純ロジック層）で「次候補選択」のみを担い、実際のプロバイダ切替・確認ダイアログ再提示は `ocr_dialog.py` の `_finish_error`/`_on_summary_error` から呼ぶオーケストレーションメソッドに実装する。プロバイダ切替は `self.app.settings` を書き換えず、ダイアログローカルなスナップショット辞書上でのみ行う。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| テンプレート CRUD UI（選択・保存・削除・リネーム） | UI Layer（`dialogs/llm_config/sections.py` 新規セクション） | Persistence Layer（`settings.py`） | 既存 `SectionsMixin` の UI 構築責務をそのまま延長。永続化ロジック自体は settings.py に閉じる |
| テンプレート名重複チェック・削除可否判定 | Persistence/Pure Logic Layer（`settings.py` 新規ヘルパー関数） | UI Layer | `ShortcutsDialog._on_save` の重複拒否と同型の純粋判定ロジック。Tk 依存にしないことでユニットテスト可能にする |
| 外部mdファイル⇄アクティブテンプレート同期 | Persistence Layer（`settings.py` の `load_prompt_file`/`save_prompt_file` 拡張） | UI Layer（切替確認ダイアログ） | 既存 V174-2 実装の直接延長。ファイル I/O は settings.py に閉じたまま |
| `resolve_ocr_prompt`/`resolve_summary_prompt` へのテンプレート層挿入 | Pure Logic Layer（`ocr.py`） | — | 既に Tk/ネットワーク非依存の純関数として確立済み。優先順位に1段追加するだけで済む |
| フォールバック順設定 UI（トグル+リスト+上下ボタン） | UI Layer（`dialogs/llm_config/sections.py` 新規セクション） | Persistence Layer | `MergeOrderDialog` の Listbox+ボタンパターンを別コンテキスト（modal Toplevel でなく埋め込みセクション）へ移植 |
| フォールバック発火判定（`fatal_msg`/`fatal_kind` 確定） | Pure Logic Layer（既存 `ocr_pipeline.PipelineState`・変更不要） | — | 既存実装がそのまま条件源になる。新規ロジックは「次候補プロバイダの選択」のみ |
| 次候補プロバイダ選択（チェーン順走査・試行済み除外） | Pure Logic Layer（新規 `ocr_fallback.py`） | — | Tk/fitz 非依存の純関数として独立させ、`pagination.py`/`ocr_pipeline.py` と同格の層にする（ユニットテスト容易性） |
| フォールバック切替オーケストレーション（確認ダイアログ再提示・provider 再構築・concurrency/APIキー再評価） | UI/Orchestration Layer（`ocr_dialog.py` の `OCRDialog` 新規メソッド） | Provider Factory Layer（`ocr.py` `build_provider`） | OCRRunEngine 未抽出（Phase 3 スコープ）のため、既存 `OCRDialog` 内に留める。`build_provider` は変更不要で複数回呼び出すだけで足りる |
| APIキー解決・並列度クランプの再評価 | Provider Factory Layer（`ocr.py` `build_provider`・`_resolve_api_key`） | — | 既存関数はプロバイダ非依存設計済み。フォールバック候補ごとに独立して呼び出すだけで正しく動く（Pitfall 3 参照） |

## Standard Stack

### Core

本フェーズは新規外部パッケージを一切導入しない（V14-D-01「新規 pip 依存ゼロ方針」継続）。既存標準ライブラリと既存プロジェクト内モジュールのみで実装する。

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tkinter`/`tkinter.ttk` | 標準ライブラリ | テンプレート/フォールバック設定 UI | 既存 `dialogs/llm_config/` と完全に同一の UI スタック |
| `json` | 標準ライブラリ | `pagefolio_settings.json` へのテンプレート/フォールバック順永続化 | 既存 `_load_settings`/`_save_settings` がそのまま使う形式 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| （追加なし） | — | — | — |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `settings.json` 内辞書構造（D-02 で確定） | `prompt_templates/` 専用ディレクトリの個別 md ファイル | ユーザー決定で不採用（D-02）。将来テンプレート数が増えた場合の I/O 走査コストは PITFALLS.md「パフォーマンストラップ」で「テンプレート50件以上」を閾値として明記済み |
| `MergeOrderDialog` の Listbox+ボタン UI パターン流用（D-13 で確定） | ドラッグ&ドロップ並び替え | ユーザー決定で不採用（D-13・実装コスト回避） |
| ダイアログローカルなプロバイダスナップショットでのフォールバック切替（本リサーチの推奨） | `self.app.settings` を直接書き換えてフォールバック先プロバイダを一時反映 | 直接書き換えは「フォールバック中に使ったプロバイダが既定設定として永続化される」事故（本リサーチで新規発見した落とし穴・後述）を誘発するため非推奨 |

**Installation:**
```bash
# 新規インストール不要（既存 requirements.txt のまま）
```

**Version verification:** 本フェーズはパッケージインストールを伴わないため、`npm view`/`pip index versions` 等のレジストリ検証は不要。既存 `requirements.txt` の固定バージョン（Tkinter は標準ライブラリのためバージョン管理対象外）を変更しない。

## Package Legitimacy Audit

**本フェーズでは外部パッケージのインストールを一切行わない。** `pagefolio_settings.json` へのテンプレート/フォールバック順永続化は既存 `json`（標準ライブラリ）を使い、UI は既存 `tkinter` スタックの延長のみで完結する。したがって Package Legitimacy Gate の実行対象パッケージは存在しない。

**Packages removed due to [SLOP] verdict:** none（対象パッケージなし）
**Packages flagged as suspicious [SUS]:** none（対象パッケージなし）

## Architecture Patterns

### System Architecture Diagram

```text
[LLM 設定ダイアログ (UI)]
  dialogs/llm_config/sections.py
  ├─ 既存: プロバイダ選択セクション / 共通パラメータセクション
  ├─ 新規: 📄 テンプレートセクション（combobox選択 + 保存/削除/リネームボタン）
  └─ 新規: 🔁 フォールバックセクション（トグル + Listbox + 上へ/下へボタン）
        │                                   │
        │ 保存/削除/リネーム/切替             │ トグルON/順序変更
        ▼                                   ▼
[settings.py 永続化層]
  _load_settings() / _save_settings()
  ├─ 新規: prompt_templates（active + items 辞書）CRUD ヘルパー
  ├─ 新規: ocr_fallback_enabled / ocr_fallback_chain（プロバイダ名リスト）
  └─ 既存: load_prompt_file/save_prompt_file/load_custom_prompt/load_summary_prompt
        │
        │ テンプレート切替時: D-05〜D-08 の確認・書き戻しフロー
        ▼
[外部 md ファイル]（ocr_custom_prompt.md / ocr_summary_prompt.md）
  「常にアクティブテンプレートのライブ編集内容」

────────────────────────────────────────────────────────────

[OCR 実行フロー (ocr_dialog.py: OCRDialog)]
  _on_run() ──▶ producer(_render_next_page) + consumer(_worker × concurrency)
                        │
                        ▼ consume_one() が ocr_pipeline.PipelineState を更新
                [PipelineState.fatal_msg 確定]
                        │ (connection / timeout / circuit_breaker)
                        ▼
                _finish_error(msg, kind)
                        │
                        ▼ 新規フック
                _propose_fallback(kind, msg)
                  ├─ ocr_fallback.py: 次候補プロバイダを純関数で選択
                  │    （試行済みプロバイダを除外・チェーン順走査）
                  ├─ 候補あり ──▶ 送信先確認ダイアログ（理由付き・D-11）再提示
                  │                 │ Yes
                  │                 ▼
                  │        ダイアログローカルな設定スナップショットで
                  │        build_provider() 再呼び出し
                  │        （self.app.settings は書き換えない）
                  │                 │
                  │                 ▼
                  │        concurrency / APIキー / model_list_timeout を
                  │        新プロバイダで再評価（Pitfall 3）
                  │                 │
                  │                 ▼
                  │        _on_run(resume=True) 相当で未処理ページのみ再実行
                  │        （_pending_pages() 既存機構を流用・D-09）
                  └─ 候補なし/拒否 ──▶ 現状の _finish_error 表示のみ（変更なし）

  同型のフックを _on_summary_error にも追加（D-12・サマリ生成にも同じ連鎖を適用）
```

### Recommended Project Structure

```
pagefolio/
├── ocr.py                          # 変更: resolve_ocr_prompt/resolve_summary_prompt にテンプレート層を挿入
├── ocr_fallback.py                 # 新規（Tk/fitz 非依存の純ロジック層）: 次候補プロバイダ選択・試行済み管理
├── ocr_dialog.py                   # 変更: _finish_error/_on_summary_error からフォールバック提案フックを追加
├── settings.py                     # 変更: prompt_templates CRUD・ocr_fallback_* デフォルト値追加
└── dialogs/
    └── llm_config/
        ├── sections.py             # 変更: テンプレート/フォールバック 新規セクション追加
        └── dialog.py               # 変更（必要なら）: _apply にテンプレート/フォールバック設定の収集を追加
tests/
├── test_prompt_templates.py        # 新規: テンプレート CRUD 純ロジックのユニットテスト
└── test_ocr_fallback.py            # 新規: ocr_fallback.py 純ロジックのユニットテスト
```

### Pattern 1: テンプレート永続化スキーマ（settings.py 拡張）

**What:** `pagefolio_settings.json` に `prompt_templates` 辞書を追加し、`active`（現在選択中のテンプレート名。空文字は「テンプレート未選択＝従来通り設定欄のみ」を意味する）と `items`（テンプレート名→ペアのプロンプト）で構成する。
**When to use:** テンプレート CRUD 全操作（保存・選択・削除・リネーム）の唯一の情報源として使う。

```python
# Source: 既存 settings.py の _load_settings() defaults 辞書パターンを延長（社内一次情報）
# pagefolio/settings.py の _load_settings() defaults に追加するイメージ
"prompt_templates": {
    "active": "",       # 空文字 = テンプレート未選択（既存の設定欄直接編集と等価）
    "items": {},         # {"template_name": {"custom_prompt": "...", "summary_prompt": "..."}}
},
```

CRUD ヘルパーは既存 `load_prompt_file`/`save_prompt_file` と同じ関数型スタイルで settings.py に追加する（`save_template(settings, name, custom_prompt, summary_prompt)` / `delete_template(settings, name)` / `rename_template(settings, old_name, new_name)` / `list_template_names(settings)`）。すべて `settings` 辞書を引数に取り、呼び出し側が `_save_settings()` を呼ぶ既存の責務分離を踏襲する（settings.py 内で自動保存しない・既存 `_apply` が保存タイミングを制御する現行方針と一致）。

### Pattern 2: テンプレート選択 UI（既存 combobox パターン流用）

**What:** `provider_combo`（`ttk.Combobox` + `state="readonly"`）と同型のコンボボックスをテンプレートセクションに追加し、`<<ComboboxSelected>>` で D-05 の確認フロー付き切替を実行する。
**When to use:** V180-TMPL-02 の一覧選択 UI。

```python
# Source: pagefolio/dialogs/llm_config/sections.py:84-93（provider_combo の既存実装パターン）
self.template_var = tk.StringVar(value=self.current_settings.get("prompt_templates", {}).get("active", ""))
self.template_combo = ttk.Combobox(
    template_row,
    textvariable=self.template_var,
    values=list_template_names(self.current_settings),
    state="readonly",
    font=self._font(-1),
)
self.template_combo.bind("<<ComboboxSelected>>", self._on_template_change)
```

### Pattern 3: 外部mdファイル連動とテンプレートの関係（D-05〜D-08）

**What:** 外部ファイルは常に「現在アクティブなテンプレートのライブ編集内容」。テンプレート切替時のみ、未保存差分チェック→確認→書き戻しの3手順を踏む。
**When to use:** `_on_template_change` ハンドラ内。

```python
# Source: 社内一次情報（settings.py の既存 load_prompt_file/save_prompt_file/prompt_file_exists・V174-2 実装の直接延長）
def _on_template_change(self, _event=None):
    new_name = self.template_var.get()
    # D-05: 外部ファイル連動モード時、現在の入力欄内容が「保存済みテンプレート内容」
    # または「外部ファイルの最終保存内容」と一致しない場合は確認ダイアログを挟む
    current_custom = self.ocr_prompt_text.get("1.0", "end").strip()
    current_summary = self.ocr_summary_prompt_text.get("1.0", "end").strip()
    if self._has_unsaved_template_changes(current_custom, current_summary):
        if not messagebox.askyesno(
            self._L["confirm_title"],
            self._L["template_switch_discard_confirm"],
            parent=self,
        ):
            # キャンセル: コンボボックスの選択を元のアクティブテンプレートへ戻す
            self.template_var.set(self._active_template_name)
            return
    # 選択したテンプレートの内容を入力欄へ反映
    tpl = get_template(self.current_settings, new_name)
    self.ocr_prompt_text.delete("1.0", "end")
    self.ocr_prompt_text.insert("1.0", tpl["custom_prompt"])
    self.ocr_summary_prompt_text.delete("1.0", "end")
    self.ocr_summary_prompt_text.insert("1.0", tpl["summary_prompt"])
    # D-07: ファイル連動モードなら選択したテンプレートの内容で外部ファイルを上書き
    if prompt_file_exists(CUSTOM_PROMPT_FILE):
        save_prompt_file(CUSTOM_PROMPT_FILE, tpl["custom_prompt"])
    if prompt_file_exists(SUMMARY_PROMPT_FILE):
        save_prompt_file(SUMMARY_PROMPT_FILE, tpl["summary_prompt"])
    self._active_template_name = new_name
```

### Pattern 4: `resolve_ocr_prompt`/`resolve_summary_prompt` へのテンプレート層挿入（V180-TMPL-05）

**What:** 既存の優先順位（custom > provider別 > 汎用）の**最上位に手を加えず**、custom_prompt の解決元をテンプレートまで遡って決定する。`resolve_ocr_prompt` 自身のシグネチャ・優先順位ロジックは変更不要（custom_prompt の**中身**がテンプレート由来かどうかは呼び出し側の関心事）。
**When to use:** `_start_ocr`（`ocr.py`）が `load_custom_prompt(self.settings)` を呼ぶ箇所。

```python
# Source: pagefolio/ocr.py:75-101（resolve_ocr_prompt の既存実装・変更不要）
def resolve_ocr_prompt(preset, provider_name, custom_prompt=""):
    if custom_prompt:
        return custom_prompt  # ← テンプレート由来の値もここに乗るだけ
    by_provider = PROVIDER_OCR_PROMPTS.get(provider_name, {})
    if preset in by_provider:
        return by_provider[preset]
    return OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])
```

```python
# Source: 社内一次情報（settings.py の load_custom_prompt 拡張案）
def load_custom_prompt(settings):
    """有効なカスタムプロンプトを返す（外部 md ファイル > アクティブテンプレート > 設定欄）。"""
    file_content = load_prompt_file(CUSTOM_PROMPT_FILE)
    if file_content:
        return file_content
    active = settings.get("prompt_templates", {}).get("active", "")
    if active:
        tpl = settings.get("prompt_templates", {}).get("items", {}).get(active)
        if tpl and tpl.get("custom_prompt"):
            return tpl["custom_prompt"]
    return settings.get("ocr_custom_prompt", "")
```

これにより「custom > provider別 > 汎用」という既存の3段解決順は変更されず、`custom` の中身の解決元だけが「外部ファイル > テンプレート > 設定欄直接値」の3段に細分化される。全プロバイダが同じ `load_custom_prompt`/`load_summary_prompt` を呼ぶため、V180-TMPL-05「全プロバイダで横断共有」は自動的に満たされる。

### Pattern 5: フォールバック順設定 UI（`MergeOrderDialog` パターンの埋め込み移植）

**What:** `MergeOrderDialog` は独立した `tk.Toplevel`（モーダルダイアログ）だが、D-15 により本機能は LLM 設定ダイアログ内の**埋め込みセクション**として実装する。`tk.Listbox` + 上へ/下へボタンという**ウィジェット構成**のみを移植し、`Toplevel` 化・`callback` 経由の親子通信は不要（同一ダイアログ内の `self` 属性で完結する）。
**When to use:** 新規「🔁 フォールバック」セクション。

```python
# Source: pagefolio/dialogs/merge.py:143-157（_move_up/_move_down の移植元パターン）
def _fallback_move_up(self):
    sel = self.fallback_listbox.curselection()
    if not sel or sel[0] == 0:
        return
    i = sel[0]
    self._fallback_chain[i - 1], self._fallback_chain[i] = (
        self._fallback_chain[i],
        self._fallback_chain[i - 1],
    )
    self._reload_fallback_list(i - 1)
```

D-14 により候補一覧には全プロバイダ（`off` を除く実行可能プロバイダ: `lmstudio`/`ollama`/`runpod`/`claude`/`gemini`/`tesseract` + プラグイン登録プロバイダ）を含める。D-16 の「既定 OFF・トグルで表示」は `provider_row`/`url_section_frame` と同型の `pack`/`pack_forget` 切替で実装できる（`_on_provider_change` の既存パターンをそのまま踏襲）。

### Pattern 6: フォールバックオーケストレーション（`ocr_dialog.py` 拡張）

**What:** `_finish_error`（OCR）と `_on_summary_error`（サマリ）の末尾に、フォールバック提案フックを追加する。フックは「次候補の選択（純ロジック）」と「確認・切替・再実行（Tk/ネットワーク依存のオーケストレーション）」を分離する。
**When to use:** `PipelineState.fatal_msg` が確定した全ケース（`_finish_error` の `kind` 引数が `connection`/`timeout`/`circuit_breaker` のいずれか）、および事前の API キー未解決チェック失敗時（現状は `_check_cloud_api_key()` が `_on_run` 開始前にブロックする経路のため、フォールバック候補についても同じ事前チェックを個別に評価する必要がある。Pitfall 3 参照）。

```python
# Source: 社内一次情報（ocr_fallback.py 新設案・pagination.py と同格の純ロジック層作法）
# 「fitz/tkinter を一切 import しない」という ocr_pipeline.py の作法をそのまま踏襲する
def next_fallback_candidate(chain, tried):
    """chain（設定済みフォールバック順リスト）から、まだ試していない
    最初の候補を返す。無ければ None（D-10: 連鎖は最後まで辿る）。

    引数:
      chain: list[str]  ユーザー設定のプロバイダ名順序リスト
      tried: set[str]   このダイアログセッション内で既に試行したプロバイダ名
    """
    for name in chain:
        if name not in tried:
            return name
    return None
```

```python
# Source: 社内一次情報（ocr_dialog.py OCRDialog への追加メソッド案）
def _propose_fallback(self, kind, msg):
    """_finish_error / _on_summary_error から呼ぶフォールバック提案フック（D-11/D-12）。

    self.app.settings は一切書き換えない（フォールバック中の一時プロバイダ選択を
    永続設定へ漏らさないため・本リサーチで新規発見した落とし穴）。
    """
    if not self.app.settings.get("ocr_fallback_enabled", False):
        return  # D-16: 既定 OFF
    chain = self.app.settings.get("ocr_fallback_chain", [])
    if not self._fallback_tried:
        self._fallback_tried = {self._active_provider_name()}
    candidate = next_fallback_candidate(chain, self._fallback_tried)
    if candidate is None:
        return  # チェーン終端 or 未設定（現状の _finish_error 表示のみ）
    reason_key = {
        "connection": "fallback_reason_connection",
        "timeout": "fallback_reason_timeout",
        "circuit_breaker": "fallback_reason_circuit_breaker",
        "api_key_missing": "fallback_reason_api_key_missing",
    }.get(kind, "fallback_reason_generic")
    if not messagebox.askyesno(
        self._L["confirm_title"],
        self._L["fallback_confirm_msg"].format(
            reason=self._L[reason_key], candidate=candidate
        ),
        parent=self,
    ):
        self._fallback_tried.add(candidate)  # 拒否された候補も試行済み扱い（D-10 連鎖継続）
        return
    self._fallback_tried.add(candidate)
    self._switch_to_fallback_provider(candidate)  # build_provider 再構築・resume 再実行
```

### Anti-Patterns to Avoid

- **`self.app.settings["ocr_provider"] = candidate` によるフォールバック中の直接書き換え:** これを行うと、フォールバック実行中にユーザーが LLM 設定ダイアログを開いた場合や、次回アプリ起動時に「明示的に選んだ覚えのないプロバイダ」が既定になる。ダイアログローカルな辞書コピー（例: `self._fallback_settings = dict(self.app.settings)`）を使い、`build_provider(self._fallback_settings, ...)` に渡す形で完全に分離する。
- **フォールバック確認ダイアログの「今後表示しない」オプション追加:** `_confirm_cost`/`_confirm_summary_cost` が D-11「毎回表示する」方針を貫いているのと同じ理由（PITFALLS.md 落とし穴7）で、フォールバック確認にも「今後表示しない」チェックボックスを追加してはならない。
- **`resolve_ocr_prompt` のシグネチャ変更（テンプレート引数の追加）:** テンプレート層は `custom_prompt` 引数の**解決元**を変えるだけであり、`resolve_ocr_prompt`/`resolve_summary_prompt` 自体は変更不要。シグネチャを変えると `test_provider_ui.py` の既存テストが全滅する。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| テンプレート名の重複チェック | 独自の重複判定 UI ロジック | `ShortcutsDialog._on_save`（`find_duplicate_binding` 相当パターン）を模倣した `settings.py` 内の純粋関数 | 既に実戦投入済みで UAT 済みのパターン。新規実装は再発明コストとバグ混入リスクのみ生む |
| フォールバック順の並び替え UI | 独自のドラッグ&ドロップ実装 | `MergeOrderDialog` の Listbox + 上へ/下へボタン | D-13 で明示的に不採用と確定済み（ドラッグ&ドロップ）。既存パターンで十分 |
| フォールバック候補のプロバイダ再構築（並列度・APIキー・タイムアウト） | 独自のプロバイダ設定マージロジック | 既存 `build_provider()` ファクトリをプロバイダごとに素直に再呼び出し | `build_provider` は既にプロバイダ非依存設計（各 `elif name == "..."` 節が個別に `max_tokens` クランプ・`concurrency` 既定値を持つ）。車輪の再発明は Pitfall 3 の温床になる |
| フォールバック発火判定（connection/timeout/circuit_breaker の検出） | 独自のエラー分類ロジック | 既存 `ocr_pipeline.PipelineState.fatal_msg`/`fatal_kind`（変更不要） | v1.7.1 Phase 2 で一本化済みの成熟した状態機械。二重実装すると `_worker`/`consume_one` との整合が崩れる |

**Key insight:** 本フェーズの実装コストの大半は「新規ロジックの実装」ではなく「既存の3〜4個の成熟パターンを正しい箇所へ正しい形で複製・接続すること」にある。新規に書くべきコードは意図的に最小化されている（`ocr_fallback.py` の次候補選択関数と `settings.py` のテンプレート CRUD ヘルパーのみが真に新規）。

## Common Pitfalls

### Pitfall 1: テンプレートマネージャーが外部mdファイル連動と書き戻し競合を起こす（PITFALLS.md 落とし穴6）

**What goes wrong:** テンプレート切替のたびに無条件で外部ファイルへ上書きすると、外部エディタで編集中だった内容が消失する。
**Why it happens:** v1.7.4 の外部ファイル連動は「単一ファイル⇄単一入力欄」の単純な双方向バインディングを前提に設計されており、「複数の名前付き保存スロット」という概念を後付けすると、切替のタイミングで「今の入力欄内容」と「切替先テンプレートの内容」のどちらを正とするかが曖昧になる。
**How to avoid:** D-05〜D-08 の3段フロー（未保存差分の検知→確認ダイアログ→書き戻し）を厳守する。外部ファイルは「現在アクティブなテンプレートのライブ編集内容」という位置づけを一度も破らない。
**Warning signs:** テンプレート切替直後に外部エディタで開いていたプロンプトが消える、複数テンプレート保存後に外部ファイルの内容と選択中テンプレートの内容が食い違う。

### Pitfall 2: フォールバックが「明示同意・コスト確認」方針を確認ダイアログ省略で迂回する（PITFALLS.md 落とし穴7）

**What goes wrong:** 「失敗のたびに確認ダイアログを出すと煩わしい」という UX 上の誘惑から、フォールバック発火時のみ確認をスキップする実装になりがちである。
**Why it happens:** 実装者が善意で「体験の良さ」を優先し、確認ダイアログの再提示を省略する近道を取る。
**How to avoid:** D-10/D-11 を機械的に実装する。フォールバック連鎖の各段で必ず `messagebox.askyesno` を呼び、理由（`connection`/`timeout`/`circuit_breaker`/`api_key_missing`）を明示する。自動テストでフォールバック経路の `askyesno` 呼び出しをモックでアサートする（`## Validation Architecture` 参照）。
**Warning signs:** フォールバック発生時のログにコスト確認スキップの痕跡がある、テストでフォールバック先のコスト確認ダイアログが呼ばれていないことが分かる。

### Pitfall 3: フォールバックが並列度・APIキー解決・レート制限のプロバイダ間差異を引き継いでしまう（PITFALLS.md 落とし穴8）

**What goes wrong:** 元プロバイダの `concurrency` 設定をそのままフォールバック先に渡すと、Claude（`max_concurrency=2`）や Gemini（`max_concurrency=1`・Free Tier 10 RPM 対応）へフォールバックした際に想定外の高並列度で送信し 429 を誘発する。RunPod は環境変数 `RUNPOD_API_KEY` 必須という制約を見落とすと「APIキー未設定」がフォールバック中に静かに握りつぶされる。
**Why it happens:** `build_provider` ファクトリ・`OCRProvider` 基底クラスはプロバイダ単体の生成を前提に設計されており、「フォールバックチェーン」という複数プロバイダの設定解決という新しい軸を想定していない。
**How to avoid:** フォールバックの各段で `build_provider()` をプロバイダごとに独立して呼び出し、そのプロバイダ固有の `max_concurrency`（`ocr_providers/claude.py`: 2 / `gemini.py`: 1 / `runpod.py`: 4 / `lmstudio.py`・`ollama.py`: 8）と APIキー解決規則（`_resolve_api_key`）を個別に再評価する。APIキー未設定は「次のフォールバック候補へ暗黙に進める」のではなく、明示的な `api_key_missing` 理由として確認ダイアログに表示してから次へ進む（D-11・D-14）。
**Warning signs:** フォールバック先で 429 が頻発する、RunPod へのフォールバックが無言で失敗する。

### Pitfall 4（本リサーチで新規発見）: フォールバック中の一時プロバイダ選択が `self.app.settings` を汚染し永続化される

**What goes wrong:** `OCRDialog` の既存ヘルパー（`_is_cloud_provider()`/`_confirm_cost()`/`_confirm_summary_cost()`/`_check_cloud_api_key()`）はすべて `self.app.settings.get("ocr_provider", "")` を直接参照する設計になっている。フォールバック実装で「切替後プロバイダを一時的に `self.app.settings["ocr_provider"]` へ代入し、これらの既存ヘルパーをそのまま使い回す」という近道を取ると、ユーザーが後で LLM 設定ダイアログを開いた際や `_save_settings()` が呼ばれた際に、フォールバック中に一時使用しただけのプロバイダが恒久設定として `pagefolio_settings.json` に書き込まれてしまう。
**Why it happens:** 既存の `_is_cloud_provider`/`_confirm_cost` 等は「ダイアログのライフサイクル中はプロバイダが変わらない」という単一プロバイダ前提で書かれている。フォールバックという「同一ダイアログセッション内でプロバイダが動的に変わる」新しい軸に対応させるには、これらのヘルパーを「明示的なプロバイダ名/設定スナップショットを受け取れる」形に一般化する必要があるが、既存シグネチャをそのまま使い回すと `self.app.settings` の書き換えが最も安易な実装経路に見えてしまう。
**How to avoid:** フォールバック用の設定は `self.app.settings` とは別の、ダイアログインスタンスが保持するローカル辞書（例: `self._active_ocr_settings`、初期値は `dict(self.app.settings)` のコピー）に持たせる。`build_provider()` はこのローカル辞書を渡して呼ぶ。`_is_cloud_provider`/`_confirm_cost`/`_check_cloud_api_key` は「現在のプロバイダ名」を `self.app.settings` からではなく、このローカル辞書（またはより直接的には `self.provider` インスタンスの型）から取得するよう改修する。
**Warning signs:** フォールバック実行後にアプリを再起動すると `ocr_provider` が変わっている、テストで `_save_settings()` 呼び出し後の JSON にフォールバック先プロバイダ名が残っていることが分かる。

## Code Examples

Verified patterns from the existing codebase (社内一次情報・全て実コード確認済み):

### 既存のプロンプト解決優先順位（変更不要・テンプレート層は「中身」だけを差し替える）
```python
# Source: pagefolio/ocr.py:75-101
def resolve_ocr_prompt(preset, provider_name, custom_prompt=""):
    if custom_prompt:
        return custom_prompt
    by_provider = PROVIDER_OCR_PROMPTS.get(provider_name, {})
    if preset in by_provider:
        return by_provider[preset]
    return OCR_PROMPTS.get(preset, OCR_PROMPTS["text"])
```

### 既存の重複拒否パターン（テンプレート名重複チェックの踏襲元・D-04）
```python
# Source: pagefolio/dialogs/shortcuts.py:254-270（_on_save 内の重複チェック）
for cmd_name, keysym in self._shortcuts.items():
    dup_cmd = find_duplicate_binding(self._shortcuts, cmd_name, keysym)
    if dup_cmd is not None:
        messagebox.showerror(
            self._L["err_title"],
            self._L["shortcuts_dup_error"].format(cmd=self._label_for_cmd(dup_cmd)),
        )
        return
```

### 既存のプロバイダ→環境変数レジストリ（フォールバック候補の APIキー未設定判定に流用）
```python
# Source: pagefolio/ocr_providers/registry.py:26-53
def env_vars_for(provider_name):
    return PROVIDER_ENV_KEYS.get(provider_name, ())

def primary_env_var(provider_name):
    env_vars = env_vars_for(provider_name)
    return env_vars[0] if env_vars else ""
```

### 既存の fatal 確定フロー（フォールバック提案フックの挿入点）
```python
# Source: pagefolio/ocr_dialog.py:1847-1878（_finish_error）
def _finish_error(self, msg, kind):
    if self._done:  # CR-01 冪等ガード（二重呼び出し防止）
        return
    self._done = True
    # ... user_msg 組み立て・progress_var 更新 ...
    self._append_resume_hint()
    self.cancel_btn.state(["disabled"])
    if self.results:
        self.copy_btn.state(["!disabled"])
        self.save_btn.state(["!disabled"])
    self._after_run_ui_reset()
    # ▼ 新規フック挿入点（D-11・D-12）
    self._propose_fallback(kind, msg)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| 単一の外部プロンプトファイルによるカスタムプロンプト管理（v1.7.4） | 複数の名前付きテンプレート + 外部ファイルは「アクティブテンプレートのライブ編集」として共存（本フェーズ） | v1.8.0 Phase 2 | v1.7.4 のファイル連動の**契約自体は変更しない**（V174-2 の関数群は無改造で流用）。テンプレートという新しい抽象層が上に乗るだけ |
| 単一プロバイダでの OCR 実行（プロバイダ切替はユーザーが手動で LLM 設定ダイアログを開き直す必要があった） | プロバイダーフォールバック連鎖（ダイアログセッション内で確認付き自動提案・本フェーズ） | v1.8.0 Phase 2 | 「明示設定型・自動送信なし」という PROJECT.md 確定方針を厳守した上での初の複数プロバイダ横断オーケストレーション機能 |

**Deprecated/outdated:**
- なし（既存 API・既存関数シグネチャの破壊的変更は本フェーズでは発生しない設計）

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `prompt_templates` の settings.json スキーマ（`{"active": str, "items": {name: {...}}}`）が最適な構造である | Pattern 1 | Claude's Discretion 領域として明示されているため実装時に変更可能。誤っても後方互換 `.setdefault()` パターンで移行できる（Pitfall 11「設定マイグレーション」と同型） |
| A2 | フォールバック確認ダイアログの理由表示に4種類（connection/timeout/circuit_breaker/api_key_missing）で十分である | Pattern 6 | `fatal_kind` の値が将来増えた場合、`.get(kind, "fallback_reason_generic")` のフォールバック文言でカバーされるため実害は小さい |
| A3 | `_is_cloud_provider`/`_confirm_cost`/`_check_cloud_api_key` を「現在のプロバイダ名を明示的に受け取れる」形に一般化することが、`self.app.settings` を汚染しない唯一の実用的な設計である | Pitfall 4・Architectural Responsibility Map | 計画時にこの一般化の設計判断（引数追加 vs. 新規ローカル状態属性）を確定させる必要がある。誤ると `_confirm_cost` 等の既存呼び出し元（`_on_run`/`_on_summary`）との整合が崩れる |

**If this table is empty:** N/A（3件のログ済み仮定あり）

## Open Questions

1. **フォールバック候補のプロバイダ一覧に `tesseract` を含めるべきか**
   - What we know: D-14 は「全プロバイダを一覧に含める」と明記。Tesseract はローカル完結・APIキー不要のため「APIキー未設定」フォールバックの意味では常に成功する候補になる
   - What's unclear: Tesseract は精度が大きく劣る（`tesseract_accuracy_warning` の既存注記あり）ため、クラウド LLM の連続失敗から Tesseract へフォールバックすることがユーザーにとって望ましいかは自明ではない
   - Recommendation: D-14 の文言どおり一覧には含めた上で、ユーザー自身がチェーンに追加するかどうかを選ぶ設計（一覧に出すが自動では選ばれない）で問題ない。UI 側で警告を出す必要はない（既存の Tesseract 精度注記が十分に機能する）

2. **サマリ生成のフォールバック（D-12）で `supports_text_prompt` 非対応プロバイダ（Tesseract）が候補に含まれた場合の扱い**
   - What we know: `ocr_providers.py` の `complete_text_ex`/`supports_text_prompt` は Tesseract 非対応と明記されている（CLAUDE.md 記載）
   - What's unclear: フォールバックチェーンに Tesseract が含まれている状態でサマリ生成が失敗し、次候補が Tesseract だった場合、`_propose_fallback` はどう振る舞うべきか（スキップして次へ進むべきか、確認ダイアログすら出さないべきか）
   - Recommendation: `next_fallback_candidate` の呼び出し前に `supports_text_prompt` を満たさない候補を除外するフィルタをサマリ経路にのみ適用する（OCR 経路ではフィルタ不要）。計画時に `_on_summary_error` 専用のフォールバック候補選択ロジックとして明確化する

## Environment Availability

本フェーズは既存の Tkinter デスクトップアプリ内の機能追加であり、新規外部サービス・CLI・ランタイム依存を導入しない。既存の OCR プロバイダ（LM Studio/Ollama/RunPod/Claude/Gemini/Tesseract）の可用性チェックは Phase 1 までに確立済みで、本フェーズはそれらを設定面で組み合わせるだけである。

**Skip condition applies:** 外部依存の新規追加なし（コード/設定変更のみ）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2（+ pytest-cov 7.1.0） |
| Config file | `pyproject.toml`（`[tool.pytest.ini_options]`: `testpaths = ["tests"]`） |
| Quick run command | `pytest tests/test_prompt_templates.py tests/test_ocr_fallback.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| V180-TMPL-01 | テンプレート保存（新規作成・重複拒否含む） | unit | `pytest tests/test_prompt_templates.py::TestSaveTemplate -x` | ❌ Wave 0 |
| V180-TMPL-02 | テンプレート一覧取得・選択切替 | unit | `pytest tests/test_prompt_templates.py::TestListAndSelect -x` | ❌ Wave 0 |
| V180-TMPL-03 | テンプレート削除（アクティブ削除禁止含む）・リネーム | unit | `pytest tests/test_prompt_templates.py::TestDeleteRename -x` | ❌ Wave 0 |
| V180-TMPL-04 | 外部ファイル連動の未保存差分検知・切替時書き戻し | unit | `pytest tests/test_prompt_templates.py::TestExternalFileSync -x` | ❌ Wave 0 |
| V180-TMPL-05 | `load_custom_prompt`/`load_summary_prompt` のテンプレート層解決順（外部ファイル > テンプレート > 設定欄） | unit | `pytest tests/test_provider_ui.py -k resolve_prompt -x`（既存ファイル拡張） | ✅ 既存ファイル拡張 |
| V180-FALL-01 | フォールバック未設定時に発火しない（安全側既定） | unit | `pytest tests/test_ocr_fallback.py::TestDisabledByDefault -x` | ❌ Wave 0 |
| V180-FALL-02 | フォールバック発火時に確認ダイアログが再提示される（承認/拒否分岐含む） | unit（`messagebox.askyesno` モック） | `pytest tests/test_ocr_fallback.py::TestConfirmationGate -x` | ❌ Wave 0 |
| V180-FALL-03 | フォールバック先の並列度/APIキー/タイムアウトが独立に再評価される | unit | `pytest tests/test_ocr_fallback.py::TestSettingsIsolation -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_prompt_templates.py tests/test_ocr_fallback.py -x`
- **Per wave merge:** `pytest`（フルスイート・現行 880+ 件）
- **Phase gate:** フルスイートグリーン + `ruff check . && ruff format .` 通過後に `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_prompt_templates.py` — V180-TMPL-01〜05 の純ロジックテスト（`settings.py` の新規 CRUD 関数を Tk 非依存で検証・`test_settings_keyguard.py` と同型のスタイル）
- [ ] `tests/test_ocr_fallback.py` — V180-FALL-01〜03 の純ロジックテスト（`ocr_fallback.py` の `next_fallback_candidate` を `test_ocr_pipeline.py` と同型のスタイルで検証。`OCRDialog._propose_fallback` は `messagebox.askyesno` を `monkeypatch` してアサートする形の軽量スタブテストとする）
- [ ] フレームワークインストール: 不要（pytest は既存 devDependencies に含まれる）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | no | デスクトップ単独アプリ・ユーザー認証機構なし（既存方針継続） |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 該当なし（単一ローカルユーザー前提） |
| V5 Input Validation | yes | テンプレート名の重複・空文字チェック（`ShortcutsDialog` 型の純粋バリデーション関数）、フォールバック候補プロバイダ名を既知プロバイダ一覧（`_base_providers` + プラグイン登録）に限定するホワイトリスト検証 |
| V6 Cryptography | no | 本フェーズは新規暗号化処理を追加しない（APIキーは既存 `_SENSITIVE_KEYS`/セッションメモリ方式のまま） |

### Known Threat Patterns for Tkinter デスクトップ + LLM 外部送信

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| フォールバック発火時の同意迂回（想定外ベンダーへの無承認送信） | Tampering / Repudiation | D-10/D-11 の「毎回確認ダイアログ再提示」を機械的に実装し、`messagebox.askyesno` 呼び出しをテストでアサート（`## Validation Architecture` `TestConfirmationGate`） |
| フォールバック中の一時プロバイダ選択が永続設定へ漏洩（Pitfall 4） | Tampering | `self.app.settings` を直接書き換えず、ダイアログローカルなスナップショット辞書のみを使う設計を徹底（`## Architecture Patterns` Anti-Patterns） |
| テンプレート内容への機密情報混入（プロンプトにAPIキー等を誤って書き込むケース） | Information Disclosure | `pagefolio_settings.json` へ保存されるテンプレート内容自体は非機密前提だが、`_SENSITIVE_KEYS` ガード（`_save_settings`）は既存のまま維持し、テンプレート辞書のキー名が `_SENSITIVE_KEYS` パターン（`*_api_key` 等）と衝突しないことを設計時に確認する（PITFALLS.md セキュリティの誤り参照） |
| APIキー未設定を理由とするフォールバックの「静かな握りつぶし」 | Repudiation | D-11 により確認ダイアログへ理由（`api_key_missing`）を明示し、ログにも記録する（既存の `logger.error`/`OCRAPIKeyError` パターンを踏襲） |

## Sources

### Primary (HIGH confidence)
- `pagefolio/ocr.py`（`resolve_ocr_prompt`/`resolve_summary_prompt`/`build_provider`/`_resolve_api_key`）— 社内一次情報・直接確認
- `pagefolio/settings.py`（`load_prompt_file`/`save_prompt_file`/`load_custom_prompt`/`_load_settings`/`_save_settings`/`_SENSITIVE_KEYS`）— 社内一次情報・直接確認
- `pagefolio/ocr_pipeline.py`（`PipelineState`/`consume_one`）— 社内一次情報・直接確認
- `pagefolio/ocr_dialog.py`（`_confirm_cost`/`_confirm_summary_cost`/`_check_cloud_api_key`/`_on_run`/`_worker`/`_finish_error`/`_pending_pages`/`_can_resume`/`_is_cloud_provider`）— 社内一次情報・直接確認
- `pagefolio/dialogs/llm_config/dialog.py`・`sections.py`・`__init__.py`（LLMConfigDialog の Mixin 構成・`_apply`・`_add_prompt_file_notice`）— 社内一次情報・直接確認
- `pagefolio/dialogs/merge.py`（`MergeOrderDialog` の Listbox+上下ボタンパターン）— 社内一次情報・直接確認
- `pagefolio/dialogs/shortcuts.py`（`ShortcutsDialog` の重複拒否パターン）— 社内一次情報・直接確認
- `pagefolio/ocr_providers/registry.py`・`ocr_providers/{claude,gemini,lmstudio,ollama,runpod,tesseract}.py`（`max_concurrency`/`default_concurrency`/`env_vars_for`）— 社内一次情報・直接確認
- `.planning/research/SUMMARY.md`・`.planning/research/PITFALLS.md`（v1.8.0 マイルストーン横断リサーチ・落とし穴6/7/8）— 社内 curated 一次情報
- `.planning/phases/02-ai/02-CONTEXT.md`（D-01〜D-16 全決定事項）— ユーザー確定事項

### Secondary (MEDIUM confidence)
- なし（本フェーズは新規外部技術調査を要しないため、外部ソース参照なし）

### Tertiary (LOW confidence)
- なし

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 新規依存なし。既存 `requirements.txt`/標準ライブラリのみ
- Architecture: HIGH — 実コードベース直接精査（`ocr.py`/`settings.py`/`ocr_dialog.py`/`ocr_pipeline.py`/`dialogs/llm_config/`/`dialogs/merge.py`/`dialogs/shortcuts.py` を全て読了）に基づく
- Pitfalls: HIGH — PITFALLS.md の3件（落とし穴6/7/8）は既に一次情報源として確立済み。Pitfall 4 は本リサーチで実コード精査から新規発見し、コード根拠付きで記録

**Research date:** 2026-07-14
**Valid until:** 2026-08-13（30日・安定した社内コードベースが情報源のため長め）
