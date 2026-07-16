# Phase 6: 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合） - Research

**Researched:** 2026-07-16
**Domain:** Tkinter デスクトップアプリの非モーダル通知（トースト）実装・スクロール/フォント UI 監査・ドキュメント整合監査・Undo/Redo デルタ整合性バグ修正
**Confidence:** HIGH（全項目がコードベース直接確認・既存前例の実測に基づく。外部ライブラリ調査は不要）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**トースト対象エラーの線引き（QA-02）**
- **D-01:** トースト化の選定基準は「再試行ボタンが意味を持つ操作」（一時要因で失敗しうる操作）に限定する。全 messagebox（約80箇所）の網羅置換はしない。入力バリデーション系エラー（トリミング範囲過小・テンプレート名重複等）と致命的エラーは従来どおり `messagebox` モーダルを維持する。
- **D-02:** 初回対象セットは保存系＋印刷の4操作: 上書き保存（`_save_file`）・別名保存（`_save_as`）・縮小保存（`_save_compressed`）・印刷（`_print_pdf`/`_send_to_printer`）の失敗。すべてメインウィンドウ発の操作であり、AV ロック・共有違反等の一時要因で再試行が最も有効な領域。モデル一覧取得失敗は既にダイアログ内ラベル通知（非モーダル）があるため対象外。
- **D-03:** 再試行ボタンは同一操作の単純再実行のみ（ボタンは「再試行」1つ。保存失敗→同じパスへ再保存、印刷失敗→再送信）。「別名で保存」等の代替アクション併設はしない。
- **D-04:** 再試行が再び失敗した場合は同じトーストを最新エラー文言で更新して残す（回数制限なし・モーダル昇格なし）。要件どおり自動消滅もしない。

**トーストの表示形態・挙動（QA-02）**
- **D-05:** 実装方式はメインウィンドウ内オーバーレイ（`place()` でメインウィンドウ上に重ねる常駐 Frame）。`Toplevel + overrideredirect` は不採用。テーマ `C` 辞書・`_font` ヘルパーをそのまま適用し、ウィンドウ移動/最小化に自然追従させる。
- **D-06:** 表示位置は右下（トーストの業界標準位置）。
- **D-07:** 同時表示は1件のみ（新しいエラーが出たら置換）。スタック管理・レイアウト再計算は実装しない。
- **D-08:** トーストが消える条件は ①✕ボタン ②トースト経由の再試行成功 ③別経路で同一操作が成功した場合の3つ。対象操作の成功パスに dismiss 呼び出しを追加する。
- **D-09:** トースト文言は既存規約どおり `LANG` 辞書（ja/en 両方・`test_lang_parity.py` の parity 対象）経由とし、色は `C` 辞書・フォントは `_font(delta)` を使う。

**スクロールパターン/フォントスケーリング監査（QA-03）**
- **D-10:** スクロールの統一基準は v1.7.2 の llm_config パターン（Canvas + Scrollbar + 高さクランプ + 下部ボタン固定 + マウスホイール対応）を正とする。監査対象はスクロール実装を持つ8ファイル（batch_ocr / llm_config dialog・sections / merge / plugin / ocr_dialog / ui_builder / viewer）で、不一致（ホイール未対応・クランプなし等）をこの基準に寄せる。
- **D-11:** 是正は不一致箇所の個別是正のみ。`make_scrollable_frame()` 等の共通ヘルパー新設・既存動作箇所の一斉移行はしない。
- **D-12:** フォント監査の是正範囲はサイズ数値ハードコードのみ（例: `about.py` の16pt固定）。`font_size` 設定（8〜16）に追従しない箇所だけを `_font(delta)` ベースへ修正する。`ui_builder.py` の `("Segoe UI", fs±n)` は fs 連動済みのため対象外、`settings.py` のフォントプレビューラベルは意図的固定のため対象外。
- **D-13:** 再発防止はフォントのみ回帰テスト化（フォントサイズ数値ハードコードを検出するソーススキャン型テスト。`test_source_keyguard.py`/`test_lang_parity.py` の grep 型前例踏襲・意図的固定箇所は allowlist 管理）。スクロールパターンは構造的にテスト化困難なため監査記録のみ。

**開発履歴.md 整合（QA-04）**
- **D-14:** 突合先は git タグ履歴＋APP_VERSION 変更履歴＋`.planning/MILESTONES.md`。PageFolio 時代の全エントリ（v1.3.0〜v1.7.4）について日付・版番・内容の不一致を検出して修正する。V16-D-04 の痕跡もこの過程で確実に特定する。
- **D-15:** 旧 PDF Editor 時代の同名バージョン見出し（v1.7.0/v1.6.0 が新旧2回出現）は現状維持。「PDF Editor 時代（リブランディング前）」セクションで区別済み・アンカー衝突なし・歴史的記録は改変しない。
- **D-16:** 突合の結果、既に整合済みで修正不要だった場合は監査記録（確認範囲・判定根拠）をフェーズ成果物に残して V180-QA-04 を完了扱いとする。あわせて `PROJECT.md` Key Decisions の V16-D-04「⚠️ Revisit」ステータスを解消済みへ更新する。

**折り込みバグ修正（Phase 5 持ち越し）**
- **D-17:** `pagefolio/file_ops.py` の `_restore_state()` 内 `insert_redo` restore ブロックが原因の insert→undo→redo→undo（2回目）でページが重複するバグを本フェーズで修正し、undo/redo 往復の回帰テストを追加する。

### Claude's Discretion
- トーストウィジェットの内部設計（クラス構成・配置モジュール。新規 `pagefolio/toast.py` か `ui_builder.py` 内かは計画時判断。既存の純ロジック層系譜に沿えるならテスト容易性を優先）
- トーストの視覚デザイン詳細（枠線・アイコン・✕ボタンの形状・幅の上限・長文エラーの折り返し/省略）
- 再試行コールバックの受け渡し方式（`functools.partial` / ラムダ / メソッド参照）と dismiss カテゴリのキー設計
- スクロール監査の具体的な不一致判定手順と是正の適用順序
- フォントハードコード検出テストの正規表現・allowlist の管理形式
- 開発履歴.md 突合の実施手順（git タグ一覧取得方法・監査記録の記載場所＝SUMMARY か独立ファイルか）
- insert_redo バグ修正の具体的なコード変更（deferred-items.md の原因推定を検証したうえで確定）

### Deferred Ideas (OUT OF SCOPE)
- 成功/情報通知へのトースト転用 — 本フェーズはエラー通知のみ。将来トースト対象を広げる場合はスタック表示（D-07 で不採用）の再検討とセット
- スクロールの共通ヘルパー化（`make_scrollable_frame()` 等） — D-11 で不採用。将来スクロールダイアログがさらに増えた時点で再検討
- 全エラーの非モーダル化（アンチフィーチャー確定）・成功通知/情報通知へのトースト転用・スクロール共通ヘルパーの新設・フォントの `_font` ヘルパーへの全面一本化・旧 PDF Editor 時代エントリの改変・OS ネイティブ通知（Windows トースト API）連携
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V180-QA-02 | エラー時リカバリー通知が改善される（再試行アクション付き非モーダルトースト・自動消滅なし・全エラーの非モーダル化はしない） | D-02 のトースト化対象4操作を `file_ops.py`/`print_ops.py` の行番号レベルで特定（Code Examples）。表示方式（`place()` オーバーレイ）・`_rebuild_ui()` との相互作用（Pitfall 2）・LANG新規キー（D-09）を確定 |
| V180-QA-03 | UI 一貫性が監査・修正される（スクロールパターン統一・フォントスケーリング） | 対象8ファイル全件を llm_config 基準実装と比較し、不一致3件（`plugin.py` ホイール未対応・`ocr_dialog.py`/`ui_builder.py` の静的bind方式・`ocr_dialog.py` の高さクランプなし）を特定（Common Pitfalls 3/4）。フォントハードコードは `about.py:42` の1箇所のみと確定（grep網羅済み） |
| V180-QA-04 | 開発履歴.md の v1.7.0 表記整合が完了する（V16-D-04 残課題） | git タグ・MILESTONES.md・開発履歴.md 本文を突合し、現時点で不一致ゼロと確認（Summary）。D-16 の「既に整合済み」パスに該当する旨と、PROJECT.md V16-D-04 ステータス更新が必要な旨を記録 |

</phase_requirements>

## Summary

Phase 6 は 4 つの独立した作業（トースト通知・スクロール/フォント監査・開発履歴.md 整合・insert_redo バグ修正）から成る、v1.8.0 の最終仕上げフェーズである。いずれも新規外部依存を必要とせず、既存パターン（`_font`/`C`/`LANG` 規約・v1.7.2 llm_config のスクロール実装・`test_source_keyguard.py` のソーススキャン型テスト）の踏襲で完結する。

トースト通知（QA-02）は `pagefolio/file_ops.py` の3保存メソッドと `pagefolio/print_ops.py` の2印刷メソッドに対する `messagebox.showerror` 呼び出しをトースト表示に置き換える。全ての置換対象・成功パスの dismiss 挿入点をコード行レベルで特定済み（下記 Code Examples 参照）。実装方式は `self.root` 上への `place()` オーバーレイで、`_rebuild_ui()`（テーマ切替）による `root.winfo_children()` 全破棄との相互作用に注意が必要（`_build_ui()` 内で再生成する設計が必須）。

スクロール/フォント監査（QA-03）は、v1.7.2 で導入された `llm_config/dialog.py:_build_scrollable_area()` を基準パターンとして、対象8ファイルの実装を比較した結果、**明確な不一致が3件**（`plugin.py` はマウスホイール未対応、`ocr_dialog.py`/`ui_builder.py` は動的 bind_all/unbind_all ではなく静的 bind の再帰付与方式、`ocr_dialog.py` のダイアログ高さは画面高クランプなし）判明した。フォントハードコードは `about.py:42` の1箇所のみが対象（他は `_font_size`/`fs` 変数連動または意図的固定のため対象外）。

開発履歴.md 整合（QA-04）は、git タグ履歴・`.planning/MILESTONES.md`・実ファイル内容を突合した結果、**現時点で日付・版番の不一致は検出されなかった**（v1.6.0 は 2026-06-20・タグ `v1.6.0-3` と整合、v1.7.0 は 2026-07-03・タグ `v1.7.0` と整合、旧 PDF Editor 時代の同名エントリは D-15 どおり区別済み）。V16-D-04 で懸念された「一時 v1.7.0 バンプの痕跡」は既に解消済みと判定できる。この監査結果自体を成果物として記録し、PROJECT.md の V16-D-04 ステータスを解消済みへ更新する（D-16 の「既に整合済みの場合」パスに該当）。

insert_redo バグ（D-17）は `pagefolio/file_ops.py._restore_state()` の `elif op == "insert_redo":` ブロックが原因で、コード読解により根本原因・修正方法を確定済み（下記 Common Pitfalls / Code Examples 参照）。既存テスト（`test_insert_undo_redo_roundtrip`）は insert→undo→redo の3手までしか検証しておらず、4手目（2回目の undo）でのみ顕在化するため見逃されていた。

**Primary recommendation:** 4作業とも新規ライブラリ導入なし・既存パターン踏襲で実装する。トーストは `place()` オーバーレイの自前実装、スクロール/フォント監査は llm_config パターンへの個別是正、開発履歴.md は監査記録のみで完了扱い、insert_redo は delete_redo 対称パターンへの1ブロック修正。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| トースト通知の表示・状態管理 | Frontend（Tkinter メインウィンドウ） | — | デスクトップシングルプロセスアプリのため API/Backend 層は存在しない。UI 状態は `self.root` に紐づく Frame として完結する |
| 保存/印刷失敗の検知・再試行トリガ | Frontend（`file_ops.py`/`print_ops.py` Mixin） | — | `fitz.Document` 操作・OS 印刷呼び出しはすべてメインスレッド同期処理。トーストのコールバックは同一メソッドの再呼び出しで足りる |
| スクロール/フォント UI 一貫性 | Frontend（各ダイアログクラス） | — | 純粋な Tkinter ウィジェット配置の問題。ビジネスロジック層は関与しない |
| 開発履歴.md 整合監査 | ドキュメント/プロジェクト管理層 | — | git タグ・`.planning/MILESTONES.md`・`開発履歴.md` の3者間の記録整合性検証。実行時コードには影響しない |
| insert_redo デルタ整合性 | Frontend（`file_ops.py` Undo/Redo エンジン） | — | `fitz.Document` へのページ挿入/削除操作のみ。永続化層・外部サービスは関与しない |

## Standard Stack

### Core
本フェーズは新規ライブラリを一切導入しない。既存の Tkinter 標準ウィジェット（`tk.Frame`/`tk.Canvas`/`ttk.Scrollbar`/`ttk.Button`）と、プロジェクト既存の規約層（`pagefolio.constants.C`/`LANG`・`self._font`）のみで完結する。

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tkinter（標準ライブラリ） | Python 3.14.6 同梱 | トースト Frame・スクロール Canvas | CLAUDE.md の「依存追加なし方針（V14-D-01）」に準拠。Tkinter に標準トーストウィジェットは存在しないため自前実装が唯一の選択肢 `[VERIFIED: pagefolio ローカル環境 python --version]` |

### Supporting
なし（既存モジュールの改修のみ）。

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `place()` オーバーレイ Frame（D-05 確定） | `Toplevel` + `overrideredirect(True)` | フォーカス管理・タスクバー表示・マルチモニタ座標計算・最小化追従を自前実装する必要があり複雑度が大幅に増す。D-05 で明示的に不採用と確定済み |
| 個別スクロール是正（D-11 確定） | `make_scrollable_frame()` 共通ヘルパー新設 | 既存8ファイルへの一斉適用は回帰面が広く、「仕上げフェーズを軽く保つ」既存方針（Phase 3〜5）と矛盾。D-11 で不採用確定 |

**Installation:** 不要（新規パッケージなし）。

**Version verification:** 該当なし（外部パッケージ非導入のため `npm view`/`pip index versions` 等のレジストリ検証は不要）。

## Package Legitimacy Audit

本フェーズは外部パッケージを一切インストールしない（トースト実装・スクロール監査・ドキュメント整合・バグ修正のいずれも標準ライブラリ + 既存コードベースのみで完結）。Package Legitimacy Gate の対象パッケージなし。

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[ユーザー操作]
  │
  ├─ 上書き保存 (_save_file) ─┐
  ├─ 別名保存 (_save_as)     ─┤
  ├─ 縮小保存 (_save_compressed) ─┤──▶ [try: doc.save/os.replace]
  ├─ 印刷 (_print_pdf)       ─┤          │
  └─ 印刷送信 (_send_to_printer) ─┘          ├─ 成功 ──▶ _set_status() + toast.dismiss(category) 呼び出し
                                       │         （D-08: 他経路成功でも同カテゴリのトーストを消す）
                                       └─ 失敗（Exception/OSError）
                                             │
                                             ▼
                                     [ToastManager.show(category, msg, retry_cb)]
                                             │
                                             ├─ 既存トースト同カテゴリなし → 新規 Frame を place() 表示（右下）
                                             └─ 既存トーストあり → 文言更新のみ（D-07: 同時1件・D-04: 回数制限なし）
                                             │
                                             ▼
                                   [ユーザー操作: ✕ / 再試行ボタン]
                                             │
                                     ┌───────┴────────┐
                                     ▼                ▼
                              dismiss（閉じる）   retry_cb() 実行
                                                （同一操作を再実行 → 上のフローに戻る）

[_rebuild_ui()（テーマ切替）]
  │
  └─ root.winfo_children() 全破棄 → _build_ui() 再実行
        └─ ToastManager の Frame も再生成が必要（親 self.root が再生成されるため）
```

### Recommended Project Structure
```
pagefolio/
├── toast.py           # 新規（Claude's Discretion・推奨）: ToastManager クラス
│                       # place() オーバーレイ・show/dismiss/update ロジック
│                       # Tk 依存だが状態（現在表示中カテゴリ）は分離してテスト容易化を検討
├── file_ops.py         # _save_file/_save_as/_save_compressed の showerror → toast 置換
├── print_ops.py        # _print_pdf/_send_to_printer の showerror → toast 置換
├── ui_builder.py        # _build_ui() 内で ToastManager を再生成（_rebuild_ui 対応）
└── dialogs/
    ├── about.py          # font=("Segoe UI", 16, "bold") → self._font(6, "bold") 相当へ是正
    ├── plugin.py          # Canvas スクロールへ MouseWheel bind 追加
    └── llm_config/dialog.py  # 変更なし（基準実装として参照のみ）
```

### Pattern 1: トースト表示形態（メインウィンドウ内オーバーレイ）
**What:** `self.root` 直下に `place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)` で配置する常駐 `tk.Frame`。ウィンドウ移動・最小化に自動追従（`Toplevel` と異なりウィンドウマネージャの管理外）。
**When to use:** QA-02 対象の保存/印刷失敗通知のみ（D-02 で確定した4操作の失敗パスに限定）。
**Example:**
```python
# 既存パターン踏襲: pagefolio/ui_builder.py の Canvas 配置スタイルに準拠
# Source: pagefolio/dialogs/llm_config/dialog.py の C[]/self._font 参照規約
toast_frame = tk.Frame(self.root, bg=C["BG_CARD"], bd=1, relief="solid")
toast_frame.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)
tk.Label(
    toast_frame, textvariable=msg_var, bg=C["BG_CARD"], fg=C["TEXT_MAIN"],
    font=self._font(-1), wraplength=320, justify="left",
).pack(side="left", padx=(12, 4), pady=8)
ttk.Button(
    toast_frame, text=self._t("toast_retry_btn"), style="Accent.TButton",
    command=retry_cb,
).pack(side="left", padx=4)
ttk.Button(
    toast_frame, text="✕", width=2, command=dismiss_cb,
).pack(side="left", padx=(0, 8))
```

### Pattern 2: スクロール可能ダイアログ（v1.7.2 llm_config 基準・D-10 是正先）
**What:** `Canvas` + `ttk.Scrollbar` + `<Configure>` イベントによる `scrollregion` 自動更新 + `Enter`/`Leave` による `bind_all`/`unbind_all` の動的マウスホイール束縛（複数 Canvas 共存時の意図しないスクロール横取りを防止）+ 画面高クランプ + 下部ボタン固定。
**When to use:** D-10 監査対象8ファイルのうち、この基準から逸脱している箇所の是正時。
**Example:**
```python
# Source: pagefolio/dialogs/llm_config/dialog.py:101-156 (_build_scrollable_area)
def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

def _bind_wheel(_event=None):
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

def _unbind_wheel(_event=None):
    canvas.unbind_all("<MouseWheel>")

canvas.bind("<Enter>", _bind_wheel)   # マウスがこの Canvas 上にある間だけ束縛
canvas.bind("<Leave>", _unbind_wheel)  # 離れたら解除（他ウィジェットのホイールを奪わない）
```
画面高クランプの基準実装:
```python
# Source: pagefolio/dialogs/llm_config/dialog.py:159-172 (_compute_dialog_height)
def _compute_dialog_height(self):
    self.update_idletasks()
    content_h = self._body.winfo_reqheight() + self._btn_row.winfo_reqheight()
    screen_h = self.winfo_screenheight()
    max_h = max(320, screen_h - 100)
    return min(max_h, max(480, content_h + 40))
```

### Anti-Patterns to Avoid
- **`Toplevel` + `overrideredirect` トースト:** D-05 で明示不採用。フォーカス奪取・タスクバー非表示・マルチモニタ座標・最小化追従の癖が実装コストに見合わない。
- **`bind()` を子ウィジェットへ再帰的に付与する方式（`ocr_dialog.py`/`ui_builder.py` の現行実装）:** 複数スクロール領域が同一ウィンドウに存在する場合に、意図しない Canvas がホイールイベントを受け取り続けるリスクがある。llm_config の `Enter`/`Leave` 動的束縛が優れている（D-10 監査で明示すべき差分）。
- **フォントサイズの新規ハードコード:** `font=("Segoe UI", 16, "bold")` のような数値リテラルは `_font(delta, weight)` へ必ず変換する（D-12/D-13 の回帰テストで検出対象）。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| スクロール可能な UI 領域 | 独自スクロール計算・アニメーション | `Canvas` + `Scrollbar` + `scrollregion`（llm_config パターン） | Tkinter に組み込みの仮想スクロールは存在せず、この組み合わせが唯一の標準パターン。独自実装は既存8ファイルとの一貫性を損なう |
| トースト通知 | サードパーティ通知ライブラリ | 自前 `place()` Frame | Tkinter に標準トーストはなく、依存追加ゼロ方針（V14-D-01）のため軽量な自前実装が唯一の選択肢 |

**Key insight:** 本フェーズは「既存にない機能を作る」のではなく「既存パターンへの統一」がほとんどを占める。llm_config の v1.7.2 実装が既に磨き込まれた参照実装として存在するため、新規設計の余地は小さい。

## Common Pitfalls

### Pitfall 1: insert_redo の非対称復元バグ（D-17 折り込みバグの直接原因）
**What goes wrong:** `insert → undo → redo → undo`（2回目）の順で操作すると、2回目の undo 後にページが復元されるどころか挿入ページが重複してもう1枚増える（3ページ→挿入で4ページ→undo で3ページ→redo で4ページ→undo(2回目) で本来3ページに戻るべきが **5ページ** になる）。
**Why it happens:** `pagefolio/file_ops.py._restore_state()` の `elif op == "insert_redo":` ブロック（404〜407行目）が、キャプチャした bytes を `doc.insert_pdf(tmp, start_at=page_i)` で**再挿入**している。しかし対称 op（`delete`/`delete_redo` の実装パターン）に倣うなら、`insert_redo` state が undo スタックから popup されて restore される際は「前段の redo で再挿入されたページを再度取り除く」処理、すなわち **削除**（`doc.delete_page`）であるべき。`_apply_inverse` 側の逆デルタ計算自体（`elif op == "insert_redo":` 297〜304行目、`inv["op"] = "insert_undo"` + `_capture_page_blob` による現在ページのキャプチャ）は正しく、`_restore_state` 側の実行アクションのみが誤っている。
```python
# 現状（バグ）— pagefolio/file_ops.py:401-407
elif op == "insert_redo":
    for page_i, page_bytes in state["data"]:
        tmp = fitz.open(stream=self._blob_bytes(page_bytes), filetype="pdf")
        self.doc.insert_pdf(tmp, start_at=page_i)  # ← 誤り: 既にページが存在するのに再挿入
        tmp.close()

# 参考: delete_redo の対称実装（354-358行目）— これに倣うべき
elif op == "delete_redo":
    targets = sorted([page_i for page_i, _ in state["data"]], reverse=True)
    for page_i in targets:
        self.doc.delete_page(page_i)
```
**How to avoid（推奨修正）:**
```python
elif op == "insert_redo":
    # insert_redo state の restore = 前段 redo で再挿入されたページを取り除く
    # （delete_redo と対称: 昇順インデックスを降順で削除しインデックスずれを防止）
    targets = sorted([page_i for page_i, _ in state["data"]], reverse=True)
    for page_i in targets:
        self.doc.delete_page(page_i)
```
`_apply_inverse`/`_dispose_state` は変更不要（Blob 解放ロジックは既に正しく、二重解放は発生しない＝V180-ROBUST-01 観点では無害と `deferred-items.md` に記録済み・本 Pitfall はページ内容往復整合性のみに影響）。
**Warning signs:** 既存テスト `tests/test_pdf_ops.py::TestInsertUndoRedo::test_insert_undo_redo_roundtrip`（718行目）は insert→undo→redo の3手までしか検証しておらず、4手目（2回目の undo）を検証していないため見逃されていた。回帰テストは `delete+undo+redo+undo` 4手（`tests/test_undo_stress.py::TestBlobLeakDetection::test_double_release_chain_delete_undo_redo_undo` が既存の命名前例）に倣い、`insert` 版として新規追加すべき（修正後は insert 版も安全に4手検証できるようになる）。

### Pitfall 2: `_rebuild_ui()` によるトースト Frame の破棄
**What goes vertical wrong:** `app.py:_rebuild_ui()`（655〜680行目）はテーマ/フォント/言語切替時に `for w in self.root.winfo_children(): w.destroy()` で `self.root` 直下の全ウィジェットを破棄してから `_build_ui()` を再実行する。トースト Frame を `self.root` に `place()` した実装では、この破棄で参照が無効化される（`winfo_exists()` が False になる）。
**Why it happens:** `_build_menubar()` が同じ理由で `_rebuild_ui()` からも明示的に再呼び出しされている（app.py:295-303 のコメント参照）のと同型の問題。
**How to avoid:** トースト管理オブジェクト（`ToastManager` 等）は `_build_ui()`（`ui_builder.py`）内で毎回インスタンス化し直す設計にする。CONTEXT.md の記述どおり「テーマ切替でトーストが消えても再表示不要（エラー状態は破棄されて自然）」なので、状態復元は不要——単に次回 `show()` 時に新しい Frame を生成できれば十分。
**Warning signs:** テーマ切替直後に保存失敗トーストの再試行ボタンを押すと `TclError: invalid command name` 等で落ちる。

### Pitfall 3: スクロール Canvas のマウスホイール束縛漏れ（`plugin.py`）
**What goes wrong:** `pagefolio/dialogs/plugin.py`（71-88行目）は `Canvas` + `Scrollbar` + `scrollregion` 自動更新までは実装済みだが、**マウスホイールのバインドが一切ない**。スクロールバーをドラッグする以外にスクロール手段がなく、他7ファイルと操作感が不統一。
**Why it happens:** llm_config の v1.7.2 パターン確立前に書かれた実装で、以降の更新が及んでいない。
**How to avoid:** D-10 是正で `<MouseWheel>`/`<Button-4>`/`<Button-5>`（Linux 互換）を Pattern 2 の動的束縛方式で追加する。
**Warning signs:** プラグイン一覧が多い環境でマウスホイールスクロールが効かないという UAT フィードバック。

### Pitfall 4: `OCRDialog` のダイアログ高さが画面高でクランプされない
**What goes wrong:** `pagefolio/ocr_dialog.py:_center()`（197-207行目）は `h = max(680, int(fs * 56))` で高さを算出するが、`winfo_screenheight()` によるクランプが一切ない。`font_size=16` の環境では `h = 896`px となり、画面解像度が低い（例: 768px 高）と下部の「閉じる」ボタン等が画面外に出る可能性がある。
**Why it happens:** `_center()` は v1.7.2 llm_config のスクロール対応改修（H-6）以前のロジックのまま。右ペイン（`side_canvas`）自体はスクロール対応済みだが、ダイアログ全体の高さクランプは未対応。
**How to avoid:** D-10 是正時に `_compute_dialog_height()` 相当のクランプを `_center()` へ追加するか、既存の `_body`/`_btn_row` 構造差分を踏まえた等価ロジックを導入する。
**Warning signs:** 低解像度・大フォント環境で OCR ダイアログの下端が画面外に出るという UAT フィードバック。

### Pitfall 5: `about.py` のフォントサイズ完全ハードコード
**What goes wrong:** `pagefolio/dialogs/about.py:42` の `font=("Segoe UI", 16, "bold")` はユーザーのフォントサイズ設定（8〜16）を無視した固定値。`font_size` を最小の8に設定しても "PageFolio" 見出しは常時16ptで表示される。
**Why it happens:** `AboutDialog` は他要素（バージョン文字列・サブタイトル等）が `self._font(...)` を正しく使っている中、見出しラベルのみ見落とされた。
**How to avoid:** `font=self._font(6, "bold")` へ変更（`_font` のベースは10のため `10+6=16` で現状の見た目を保ちつつ設定追従化。ただし正確な delta 値はベースフォントサイズとの相対計算で planner が確定する）。
**Warning signs:** D-13 の回帰テスト（ソーススキャン型・後述）が `font=\(["']Segoe UI["'],\s*\d+` パターンで検出する。

## Code Examples

### D-02: トースト化対象の showerror 呼び出し・成功パスの dismiss 挿入点

```python
# pagefolio/file_ops.py:677-680 — 上書き保存失敗（トースト化対象）
except Exception as e:
    messagebox.showerror(
        self._t("err_save_title"), self._t("err_save_msg").format(e=e)
    )
# 成功パス（673-676行目）に dismiss("save") 相当の呼び出しを追加する
self._set_status(
    self._t("status_saved").format(name=os.path.basename(self.filepath))
)
self.plugin_manager.fire_event("on_file_save", self, self.filepath)
# ↑ ここに toast_manager.dismiss("save") を追加（D-08）

# pagefolio/file_ops.py:698-699 — 別名保存失敗（トースト化対象）
except Exception as e:
    messagebox.showerror(self._t("err_title"), str(e))
# 成功パス（694-697行目）が dismiss 挿入点

# pagefolio/file_ops.py:752-753 — 縮小保存失敗（トースト化対象）
except Exception as e:
    messagebox.showerror(self._t("err_title"), str(e))
# 成功パス（749-751行目）が dismiss 挿入点

# pagefolio/print_ops.py:76-79 — 印刷送信失敗（既定PDFハンドラなし・トースト化対象）
except OSError as e:
    logger.exception("既定アプリでのオープンにも失敗: %s", e)
    messagebox.showerror(
        self._t("err_print_title"), self._t("err_print_no_handler")
    )
# 成功パス（67行目 self._set_status(...) / 74行目）が dismiss 挿入点
```

**注意:** `_print_pdf`（36-47行目）内の一時ファイル書き出し失敗（`write_print_tempfile` の例外）も `messagebox.showerror` を使うが、D-02 は「保存系＋印刷」を1操作として扱っており、この失敗も印刷操作の失敗としてトースト化対象に含めるかは Claude's Discretion（D-02 は `_print_pdf`/`_send_to_printer` を明示指定・`write_print_tempfile` 呼び出し元の failure も同一操作の一部と解釈するのが自然）。

**入力バリデーション系（トースト化対象外・D-01 準拠）:** `_open_file`/`_open_pdf_path`/`_do_open_merged`/`_authenticate_doc`/パスワード関連メソッド（`_set_password`/`_remove_password`）の `messagebox.showerror` はファイルオープン時の一時要因ではなく、再試行の意味が薄い（同一パスへの再試行が有効でない）ため対象外のまま維持する。

### D-09: 既存 LANG キー・新規追加が必要なキー

```python
# 既存（再利用可能）— pagefolio/lang.py
"err_save_title": "保存エラー",       # 245-246行目
"err_save_msg": "保存に失敗しました:\n{e}",  # 247行目
"err_print_title": "印刷エラー",       # 84行目
"err_print_msg": "印刷に失敗しました:\n{e}",  # 85行目

# 新規追加が必要（既存に汎用「再試行」ボタンラベルなし・grep 確認済み）
"toast_retry_btn": "再試行",  # 新規・ja/en 両方に追加必須（parity テスト対象）
```

### D-13: フォントハードコード検出テストの前例パターン

```python
# Source: tests/test_source_keyguard.py（構造をそのまま流用）
import pathlib
import re

_FONT_HARDCODE_PATTERN = re.compile(r'font=\(\s*["\']Segoe UI["\']\s*,\s*\d+')
_PAGEFOLIO_DIR = pathlib.Path(__file__).resolve().parent.parent / "pagefolio"
# allowlist は現状不要（about.py:42 修正後はゼロ件が期待値）。
# 将来 fs 非連動の意図的固定が必要になった場合のみ、理由コメント付きで追加する。

def test_no_hardcoded_font_sizes():
    offenders = []
    for py in _PAGEFOLIO_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if _FONT_HARDCODE_PATTERN.search(text):
            offenders.append(str(py))
    assert not offenders, f"フォントサイズのハードコードが検出された: {offenders}"
```
このパターンは `ui_builder.py` の `font=("Segoe UI", fs)`（変数 `fs`）や `dialogs/settings.py` の `font=("Segoe UI", self.font_var.get())`/`font=("Segoe UI", size)`（変数）にはマッチしない（`\d+` は数値リテラルのみに一致）ため、D-12 で明示された除外対象（`ui_builder.py` の fs 連動箇所・`settings.py` のフォントプレビュー）に allowlist を用意する必要はない。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 静的 `bind()` の子ウィジェット再帰付与（`ocr_dialog.py`/`ui_builder.py`） | `Enter`/`Leave` による `bind_all`/`unbind_all` 動的束縛 | v1.7.2（llm_config 新設時） | 複数スクロール領域が共存する画面での意図しないホイール横取りを防止。旧2ファイルは D-10 で新パターンへ揃える候補 |
| ダイアログ高さの固定計算（`ocr_dialog.py._center()`） | `winfo_screenheight()` によるクランプ + Canvas スクロール併用 | v1.7.2（llm_config H-6） | 低解像度環境での操作不能を防止。`ocr_dialog.py` はスクロール自体は v1.7.4（D-16 相当）で対応済みだが高さクランプは未対応のまま |

**Deprecated/outdated:** なし（本フェーズはコードベース内部の一貫性是正のみで、外部エコシステムの世代交代とは無関係）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `about.py:42` の `font=self._font(6, "bold")` という delta 値がベースフォントサイズ10との組合せで現状の見た目（16pt）を再現する、という提案値 | Common Pitfalls / Pitfall 5 | 実際のベースフォントサイズが異なる環境では見た目が変わる可能性。planner/実装時に `self._font(0)[1]` の実測値で delta を確定すべき（軽微・視覚差異のみ） |
| A2 | `write_print_tempfile` 呼び出し元（`_print_pdf` 内の一時ファイル書き出し失敗）をトースト化対象に含めるかどうか | Code Examples / D-02 注記 | 対象外とした場合でも QA-02 の成功基準（軽微エラーの非モーダル化）には影響しない。含めるかは実装時の解釈判断（Claude's Discretion 範囲内） |

**このテーブルが空でない理由:** 上記2件は実測不要な設計判断（A2）または実装時に自明に確定できる数値（A1）であり、いずれもユーザー確認を要する重大な曖昧性ではない。他の全知見（トースト化対象箇所・スクロール監査結果・開発履歴.md 整合状況・insert_redo バグ原因）はコード直接読解 `[VERIFIED: ローカルコードベース]` により確認済み。

## Open Questions

1. **`ToastManager` の配置モジュール（`toast.py` 新設 vs `ui_builder.py` 内実装）**
   - What we know: CONTEXT.md で Claude's Discretion と明記。既存の「純ロジック層集約の系譜」（`pagination.py`/`ocr_pipeline.py`）に倣うなら、状態遷移（表示中カテゴリ・文言）を Tk 非依存の純関数/クラスへ分離しテスト容易性を確保する余地がある
   - What's unclear: トースト自体は Tk ウィジェット生成が本質的に必要なため、完全な Tk 非依存化は困難（純関数化できるのは「次に何を表示すべきか」の判定ロジック程度）
   - Recommendation: `pagefolio/toast.py` を新設し、`ToastManager` クラス（Tk 依存の Frame 生成部）+ 必要なら状態判定のみ純関数化。既存 Mixin 群と並列のトップレベルモジュールとして配置（`undo_store.py`/`ocr_fallback.py` と同じ粒度）

2. **`_print_pdf` の一時ファイル書き出し失敗（`write_print_tempfile` 例外）をトースト化するか**
   - What we know: D-02 は `_print_pdf`/`_send_to_printer` を明示指定。`_print_pdf` 内には2つの `messagebox.showerror` 呼び出し箇所がある（write_print_tempfile 失敗時 と `_send_to_printer` 経由の最終失敗時）
   - What's unclear: 前者（一時ファイル書き出し失敗）はディスク容量不足等でも起こりうる一時的要因であり再試行が有効な可能性が高いが、D-02 の文言は主に「AV ロック・共有違反」を印刷/保存の一時要因として挙げている
   - Recommendation: 一貫性のため `_print_pdf` 内の両方の showerror をトースト化対象に含める（同一メソッド内の分岐であり、除外すると UX が不統一になる）

## Environment Availability

該当なし（本フェーズは外部ツール・サービス・ランタイムに依存しない。既存 Python/Tkinter/PyMuPDF 環境内で完結する）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest（`pyproject.toml` の `[tool.pytest.ini_options]` 設定済み） `[VERIFIED: pyproject.toml]` |
| Config file | `pyproject.toml`（`testpaths = ["tests"]`） |
| Quick run command | `pytest tests/test_pdf_ops.py -x -q`（insert_redo 修正の対象範囲） |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V180-QA-02 | 保存/印刷失敗時にトースト表示・再試行成功で消える | unit（Tk 生成なしスタブ経由） | `pytest tests/test_toast.py -x -q` | ❌ Wave 0（新規作成） |
| V180-QA-02 | 別経路成功で同カテゴリのトーストが消える（D-08） | unit | `pytest tests/test_toast.py::TestDismissOnAlternateSuccess -x -q` | ❌ Wave 0 |
| V180-QA-03 | フォントサイズハードコード検出（D-13） | unit（ソーススキャン型） | `pytest tests/test_font_hardcode_guard.py -x -q` | ❌ Wave 0（新規作成・`test_source_keyguard.py` 準拠） |
| V180-QA-03 | スクロール監査是正後の Canvas 生成成功（回帰確認・任意） | 手動/監査記録 | — | 該当なし（構造的テスト化困難と CONTEXT.md D-13 に明記） |
| V180-QA-04 | 開発履歴.md 整合監査記録 | 監査記録（自動テストなし） | — | 該当なし |
| D-17（Phase 5 折り込みバグ） | insert→undo→redo→undo(2回目) でページ数が正しく往復する | unit | `pytest tests/test_pdf_ops.py::TestInsertUndoRedo -x -q` | 既存クラスへ追加（Wave 0 でメソッド追加） |

### Sampling Rate
- **Per task commit:** `pytest tests/test_pdf_ops.py tests/test_toast.py tests/test_font_hardcode_guard.py -x -q`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_toast.py` — トースト表示/dismiss/再試行コールバックの単体テスト（Tk 生成が必須な部分は最小限の実ウィジェット生成 or `_ButtonStub`/`_SetGetVarStub` 型の既存スタブパターン流用）
- [ ] `tests/test_font_hardcode_guard.py` — D-13 フォントハードコード検出（`test_source_keyguard.py` を直接複製・正規表現のみ差し替え）
- [ ] `tests/test_pdf_ops.py::TestInsertUndoRedo` へ4手往復テストメソッド追加（新規ファイル不要・既存クラスへの追加）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 本フェーズはローカル完結の UI/バグ修正のみ。認証機構への変更なし |
| V3 Session Management | no | セッションキー管理（`_session_api_keys`）は本フェーズで変更しない |
| V4 Access Control | no | アクセス制御機構なし（デスクトップ単独アプリ） |
| V5 Input Validation | no | トースト文言は固定 LANG キー + 既存例外メッセージの再表示のみ。新規ユーザー入力面はない |
| V6 Cryptography | no | 暗号化処理への変更なし |

### Known Threat Patterns for {stack}

本フェーズに STRIDE 該当パターンはない。トースト通知は既存 `messagebox.showerror` と同じ情報（例外メッセージ `str(e)`）を非モーダルで再表示するのみであり、新規の情報露出経路は追加しない。既存の `err_save_msg`/`err_print_msg` の `{e}` フォーマットは元々例外オブジェクトの文字列化であり、パス情報等が含まれる可能性があるが、これは既存 `messagebox` 実装からの継続動作であり本フェーズが新規に導入するリスクではない。

## Project Constraints (from CLAUDE.md)

`./CLAUDE.md` および `pagefolio/CLAUDE.md` から抽出した、本フェーズの実装が遵守すべき既定の規約:

- **メソッド命名:** 内部メソッドは `_` プレフィックス。Tk イベントハンドラは `_on_`/`_do_` プレフィックス
- **テーマ色:** グローバル定数ではなく `C["KEY"]` 辞書（例: `C["BG_DARK"]`/`C["ACCENT"]`）を使う。ハードコード hex 禁止
- **フォントサイズ:** ハードコードせず `self._font(delta)` ヘルパーを使う（本フェーズの D-12/D-13 が直接この規約の是正作業）
- **ボタンスタイル:** 通常操作は `"TButton"`、主要アクション（トーストの「再試行」ボタン等）は `"Accent.TButton"`、破壊的操作は `"Danger.TButton"`
- **再描画:** 状態変更後は `self._refresh_all()` を呼ぶ（本フェーズの操作系変更は insert_redo 修正のみでこれに該当。トースト/スクロール/フォント修正は再描画契機なし）
- **ステータス表示:** 操作完了後は `self._set_status(msg)`。トーストは `_set_status` とは別役割（軽い完了通知 vs 明示的な失敗+再試行導線）として共存させる
- **ファイル操作前の確認:** `self._check_doc()` で `self.doc` の存在を確認
- **設定保存:** `pagefolio_settings.json` へ JSON 永続化（`_save_settings()`）。本フェーズは新規設定キーを追加しない見込み
- **作業フロー:** 1タスクずつ完了させてから次のタスクへ進む。py ファイル編集後は必ず `ruff check . && ruff format .` を通す。コミット前に `pytest` を通す
- **禁止事項:** `pyproject.toml` の編集・裸の `except:`（必ず `except Exception as e:` の形）・`# type: ignore` の無断使用
- **言語ルール:** すべての返答・コミットメッセージ・PR タイトル/本文・`開発履歴.md` の記載は日本語で行う（ソースコード中の変数名・関数名・クラス名、ライブラリ/コマンド名、エラーメッセージの引用は例外）
- **既知の制限（黒塗り/モザイク/トリミング）:** `set_cropbox` によるトリミングはメタデータ変更のみ。黒塗り・モザイクは破壊的操作で `page_edit` op として undo 可能——insert_redo 修正（D-17）は同じ `_restore_state()`/`_apply_inverse()` 関数群を扱うため、他 op（`page_edit`/`bulk_crop` 等）の対称性を壊さないよう影響範囲を `insert_redo` ブロックのみに限定する
- **`pagefolio/ocr_providers/registry.py` の独立性制約:** 本フェーズの変更対象外だが、`file_ops.py`/`print_ops.py`/UI ファイル群を扱う際も同様に「他モジュールへの不要な import 依存を追加しない」設計原則を踏襲する
- **GSD Workflow Enforcement:** ファイル変更を伴う作業は GSD コマンド経由で行う（本フェーズは `/gsd-plan-phase` → `/gsd-execute-phase` の正規フロー内）

## Sources

### Primary (HIGH confidence)
- `pagefolio/file_ops.py`（ローカルコードベース直接読解）— `_save_file`/`_save_as`/`_save_compressed`/`_restore_state`/`_apply_inverse` の全ロジック
- `pagefolio/print_ops.py`（ローカルコードベース直接読解）— `_print_pdf`/`_send_to_printer`
- `pagefolio/dialogs/llm_config/dialog.py`（ローカルコードベース直接読解）— `_build_scrollable_area`/`_compute_dialog_height` 基準実装
- `pagefolio/dialogs/plugin.py`/`pagefolio/ocr_dialog.py`/`pagefolio/ui_builder.py`/`pagefolio/dialogs/batch_ocr.py`/`pagefolio/dialogs/merge.py`/`pagefolio/dialogs/llm_config/sections.py`（ローカルコードベース直接読解）— D-10 スクロール監査8ファイル全件
- `pagefolio/dialogs/about.py`/`pagefolio/dialogs/settings.py`（ローカルコードベース直接読解）— D-12 フォント監査
- `pagefolio/app.py`（ローカルコードベース直接読解）— `_rebuild_ui`/`_build_ui`/`_set_status`/メインウィンドウ構造
- `tests/test_source_keyguard.py`/`tests/test_lang_parity.py`/`tests/test_pdf_ops.py`/`tests/test_undo_stress.py`（ローカルコードベース直接読解）— 既存テストパターン・insert_redo バグの未検証範囲確認
- `.planning/phases/05-blob-shortcutsdialog/deferred-items.md`（必読・ローカル読解）— insert_redo バグの再現コード・原因推定
- `開発履歴.md`/`.planning/MILESTONES.md`/`git tag --list`（ローカル直接照合）— D-14 バージョン整合監査
- `.planning/PROJECT.md`（ローカル読解）— V16-D-04 決定事項の現在ステータス

### Secondary (MEDIUM confidence)
- `.planning/research/FEATURES.md`（Phase準備時に作成済みの既存リサーチ成果物）— トーストの Table Stakes/Anti-Features（外部ソース由来だが本フェーズでは既に検証済みの決定事項として参照のみ）

### Tertiary (LOW confidence)
なし（本フェーズは全項目をローカルコードベース直接検証で確定できたため、未検証の外部情報は含まない）。

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 新規パッケージなし、既存パターンの直接引用のみ
- Architecture: HIGH — 全対象ファイルをコード直接読解し、行番号レベルで置換箇所を特定済み
- Pitfalls: HIGH — insert_redo バグは `_apply_inverse`/`_restore_state` の対称性を実コード比較で検証し、根本原因・修正方法を確定
- 開発履歴.md整合: HIGH — git タグ・MILESTONES.md・開発履歴.md本文の3者照合を実施し、不一致ゼロを確認

**Research date:** 2026-07-16
**Valid until:** 30日（コードベース内部の静的監査結果のため、他フェーズ・他ブランチでの並行変更がなければ長期間有効。ただし insert_redo 修正は Phase 6 実装前に他コミットで file_ops.py が変更された場合は再確認が必要）
