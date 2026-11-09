# Phase 5: 設定読込・保存失敗の通知 - Research

**Researched:** 2026-10-22  
**Domain:** 設定 JSON の障害伝播、Tk 通知、原本保護  
**Confidence:** MEDIUM — 設定の既存単体テストは実行できたが、この実行環境の Tcl 初期化が失敗し Tk トーストの実行検証は保留。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 読込失敗の表示（V110-CFG-01）

- **D-01:** 読込失敗の通知は **非モーダルのトースト** で出す。画面構築後に表示し、編集操作を止めない。
- **D-02:** 初回の設定ファイル不存在は **警告なし** で既定値から起動する。
- **D-03:** 読込失敗は **JSON 破損** と **読取不能（権限・ロック等の OSError）** を区別する。両者とも通知するが、文言を分ける。
- **D-04:** 読込失敗の通知文言は「保存済みの設定を読めず既定値で起動した」旨を伝える。技術的な詳細（例外文字列・パス）は通常表示に含めない（Phase 4 D-09 と同方針）。
- **D-05:** 読込失敗の通知は **セッション中 1 回** だけ出す（D-11 参照）。

#### 保存失敗の表示（V110-CFG-02）

- **D-06:** 保存失敗は **非モーダルのトースト** で通知する。ダイアログは使わない。
- **D-07:** 保存失敗時の文言は「保存に失敗しました。今回の変更は次回起動に残りません」の趣旨を含める。「保存しました」などの成功表示は、失敗時に出さない（成功表示への誤誘導を防ぐ）。
- **D-08:** 保存失敗時は **画面上のメモリ値を維持** する。巻き戻さない。次回起動には残らないことを通知で示す。
- **D-09:** 保存失敗は **毎回通知** する（D-11 の 1 回制限の対象外）。利用者が変更が残っていないことを毎回認識できるようにするため。

#### 既存ファイルの保護（V110-CFG-03）

- **D-10:** 読込失敗（破損・読取不能）の後、既定値で **自動保存しない**。
- **D-11:** 破損ファイルの **退避コピー（.bak 等）は作らない**。
- **D-12:** 保存途中で失敗した場合（一時ファイル `pagefolio_settings.json.tmp` の書込中の失敗）は、**一時ファイルを削除** し、元ファイルを維持する。
- **D-13:** 破損ファイルの上で利用者が設定を変更して明示的に保存した場合は **上書きを許容** する。上書き前の確認ダイアログは出さない。
- **D-14（派生決定）:** D-10 の「自動保存しない」は、終了時のウィンドウ状態保存（`_save_window_state` によるジオメトリ・サッシ位置・編集モードの保存）にも適用する。読込失敗の状態では、利用者が設定を変更していない終了時の保存で破損ファイルを上書きしない。
  - **注:** この項目は利用者の個別回答から導いた派生決定であり、明示的な回答ではない。計画時に影響範囲を確認すること（下記「Claude's Discretion」参照）。

#### 通知の集約と連打防止（V110-CFG-04）

- **D-15:** 読込失敗の通知は **セッション中 1 回** だけ表示する。
- **D-16:** 保存失敗の通知は **毎回** 表示する。連続する保存失敗でも、それぞれ通知が残るようにする。
- **D-17:** 画面再構築（`_rebuild_ui`、言語切替など）の際、**まだ表示中・未消化の通知は再表示** する。通知の状態は App 側で保持し、再構築で消えないようにする。
- **D-18:** 通知は **非モーダル** のため、ダイアログの連打は発生させない（D-06 と整合）。通知の重複表示で編集操作を妨げないこと。

### the agent's Discretion

- トーストの表示時間・位置・見た目（既存 `pagefolio/toast.py` の ToastManager を基本に使う。Phase 4 の「既存 ToastManager をそのまま使えると仮定しない」に従い、起動直後の表示可否は計画で確認する）。
- 読込失敗の種別判定の実装方法（JSON デコードエラーと OSError の判別方法）。
- `_load_settings` / `_save_settings` の失敗を呼び出し側へ伝える API（戻り値・例外・状態フラグ等）。現状は両者とも例外を `logger.debug` で握りつぶしており、呼び出し元（`app.py`, `settings.py` 利用箇所の `dialogs/settings.py`, `dialogs/shortcuts.py`, `ocr_dialog.py`, `redact_ops.py`, `viewer.py`）はいずれも失敗を判定していない。
- 通知の内部データ構造（種別・文言キー・表示済みフラグ）。日英の文言キーは `pagefolio/CLAUDE.md` の規約に従う。
- D-14 の終了時保存抑止を、どの層（`_save_window_state` 側・`_save_settings` 側）で実現するかの方式。

### Deferred Ideas (OUT OF SCOPE)

- 破損設定ファイルの退避（.bak）・復旧機能 — 今回は採用しない（D-11）。将来のフェーズで扱う場合は新規要件として起票する。
- 設定ファイルの破損を起動時にダイアログで確認する方式 — 今回は非モーダルのトーストのみ。
- 起動 PDF 引数転送、最近使ったファイル復元、異常終了後の編集復旧、外部プロンプト保存失敗通知、OCR 共通化、実 API UAT — いずれも Phase 4 の保留項目を含め、今回の範囲外。

### Reviewed Todos (not folded)
None — 今回の `cross_reference_todos` は対象なし（扱いは既定）。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| V110-CFG-01 | 初回不存在は静かに既定値、破損・読取不能は画面構築後に通知 | 読込結果を設定値と別に App へ渡し、`_build_ui` 後に一度だけ表示。 [VERIFIED: .planning/REQUIREMENTS.md:45-45] |
| V110-CFG-02 | 保存失敗・次回起動に残らないことを通知し、成功誤表示を防ぐ | 保存の成否を全呼出元に伝え、UI 更新と成功表示を分離。 [VERIFIED: .planning/REQUIREMENTS.md:46-46] |
| V110-CFG-03 | 読込失敗後の自動保存と保存途中の破壊から原本を保護 | 終了時の保存抑止、既存の一時ファイル→置換を維持、失敗時 cleanup。 [VERIFIED: .planning/REQUIREMENTS.md:47-47] |
| V110-CFG-04 | 連続エラーと UI 再構築でも編集を妨げず通知を保つ | App 側の未消化通知、ToastManager 再生成後の再表示を検証。 [VERIFIED: .planning/REQUIREMENTS.md:48-48] |
</phase_requirements>

## Summary

設定の読込と保存は `pagefolio/settings.py` の `_load_settings()` と `_save_settings(settings)` に集まっている。現状、読込は例外をログへ記録して既定値を返し、保存も例外をログへ記録して呼出元に結果を返さない。コードの該当箇所は「`except Exception as e:` → `logger.debug(...)`」である。したがって UI が失敗を識別できる API を追加する必要がある。 [VERIFIED: pagefolio/settings.py:254-311] [VERIFIED: pagefolio/settings.py:314-343]

設定ファイル名の原文は「`SETTINGS_FILE = "pagefolio_settings.json"`」。パスの生成元は「`return os.path.join(_get_base_dir(), SETTINGS_FILE)`」であり、配布 EXE と開発実行で基準ディレクトリが異なる。 [VERIFIED: pagefolio/constants.py:15-15] [VERIFIED: pagefolio/settings.py:32-49]

起動時は `_load_settings()` が `_build_ui()` より前、`ToastManager` の生成は `_build_ui()` 内にある。設定通知は初期画面構築完了後に発火させる。トーストは現在「同時表示は1件のみ」「同カテゴリは文言のみ更新」「必ず再試行ボタン」「再構築で新インスタンス」という契約で、D-16/17をそのままでは満たせない。 [VERIFIED: pagefolio/app.py:148-149] [VERIFIED: pagefolio/app.py:214-216] [VERIFIED: pagefolio/ui_builder.py:184-187] [VERIFIED: pagefolio/toast.py:8-18] [VERIFIED: pagefolio/toast.py:40-55] [VERIFIED: pagefolio/toast.py:80-95]

**Primary recommendation:** 設定 I/O の結果と原本保護状態を App が管理し、明示的変更の保存を1か所経由で扱う。ToastManager は表示手段として拡張し、設定通知の未消化状態は App に残す。 [ASSUMED]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| 設定 JSON の読込判定・保存・一時ファイル cleanup | ローカル設定 I/O (`settings.py`) | — | JSON の読込・書込と `os.replace` はここに集中。 [VERIFIED: pagefolio/settings.py:254-343] |
| 読込失敗状態と保存操作の判別 | App (`app.py`) | ローカル設定 I/O | App が起動順、終了時保存、明示操作を知る。 [VERIFIED: pagefolio/app.py:138-149] [VERIFIED: pagefolio/app.py:499-508] [VERIFIED: pagefolio/app.py:575-585] |
| トーストの可視化 | Tk UI (`toast.py`, `ui_builder.py`) | App | `ToastManager` はウィジェットを作り、App は再構築後も通知状態を保持する。 [VERIFIED: pagefolio/toast.py:30-55] [VERIFIED: pagefolio/ui_builder.py:184-187] [ASSUMED] |

## Project Constraints (from AGENTS.md)

- 作業は GSD フローを開始してから行い、1タスクずつ完了させる。今回の調査は親の Phase 5 計画フローの一部。 [VERIFIED: AGENTS.md:49-53] [VERIFIED: AGENTS.md:156-168]
- `pagefolio/` の Mixin 構成、内部メソッド `_`、テーマ辞書 `C["BG_DARK"]`、`self._font(delta)` を維持。引用した値は AGENTS.md の原文どおり。 [VERIFIED: AGENTS.md:27-32]
- ボタンは通常 `"TButton"`、主要 `"Accent.TButton"`、破壊的 `"Danger.TButton"`、トリミング ON `"CropOn.TButton"`。原文のスタイル名を維持する。 [VERIFIED: AGENTS.md:34-39]
- ページ変更後は `self._refresh_all()`、操作後は `self._set_status(msg)`、ファイル操作前は `self._check_doc()`。CropBox は MediaBox 内へクランプし、設定は JSON と `_save_settings()` を使う。今回の設定通知変更ではとくにステータス表示との整合を確認する。 [VERIFIED: AGENTS.md:41-47]
- Python 編集後は `ruff check . && ruff format .`、コミット前に `pytest`。`pyproject.toml` の編集、裸の `except:`、無断の `# type: ignore` を禁止。 [VERIFIED: AGENTS.md:49-59]
- `pagefolio/ocr_providers/registry.py` は `os` のみへ依存し、内部モジュールを import させない。 [VERIFIED: AGENTS.md:100-100]
- UI は Tk メインスレッドで扱い、日英の LANG 新規キーは両言語へ追加する。 [VERIFIED: AGENTS.md:143-145] [VERIFIED: pagefolio/CLAUDE.md:11-14]
- 製品コードを変更する実装 wave では `開発履歴.md` と版番号チェックリストを確認する。ただし現在のマイルストーン計画は版番号・README・開発履歴の同期を Phase 6 のゲートへ置いている。 [VERIFIED: AGENTS.md:104-110] [VERIFIED: .planning/PROJECT.md:34-34]
- Phase 作業完了時は日本語の申し送りを `.agents/skills/session-handoff/SKILL.md` の書式で出す。 [VERIFIED: AGENTS.md:114-118] [VERIFIED: .agents/skills/session-handoff/SKILL.md:1-38]
- ルート CLAUDE.md のリリースゲートは、単一プロセスのフル pytest が失敗0・ERROR0・クラッシュなしで完走すること。既知の TclError が再現した場合、単体/再実行で原因を切り分けても最初の ERROR を記録し、部分成功を合格扱いしない。 [VERIFIED: CLAUDE.md:114-150]

## Standard Stack

| Component | Version / Source | Purpose | Recommendation |
|---|---|---|---|
| Python 標準ライブラリ `json`・`os` | リポジトリ現行 | JSON 判定と既存の原子的置換 | 既存 `settings.py` を拡張し、新規パッケージを導入しない。 [VERIFIED: pagefolio/settings.py:6-8] [VERIFIED: pagefolio/settings.py:328-340] |
| Tkinter + `ToastManager` | リポジトリ現行 | 非モーダル通知 | 既存トーストを拡張し、従来の PDF 保存・印刷の再試行契約は保つ。 [VERIFIED: pagefolio/toast.py:21-30] [VERIFIED: tests/test_toast.py:60-160] |
| pytest / Ruff | 当該 `.venv`: pytest 9.1.1 / Ruff 0.17.1（2026-10-22 実測） | 機能・整形検証 | 既存テスト基盤を使う。 [VERIFIED: `.venv/Scripts/pytest.exe --version`, `.venv/Scripts/ruff.exe --version` 実行結果] |

**Package Legitimacy Audit:** 本調査は追加パッケージを推奨しない。現行の設定 I/O とトーストは `json`・`os`・`tkinter` を使用している。 [VERIFIED: pagefolio/settings.py:6-8] [VERIFIED: pagefolio/toast.py:21-23]

## Architecture Patterns

```text
起動 → settings.py 読込 → {不存在 / 成功 / 破損 / 読取不能}
                         → App が設定値と読込状態を保持
                         → 画面構築 → 設定の読込失敗だけ非モーダル通知

利用者の設定変更 → App の保存窓口 → settings.py の一時ファイル書込
                                  → {置換成功 / 失敗・一時ファイル cleanup}
                                  → App の通知状態 → ToastManager へ表示
終了 → 読込失敗が未解消なら自動保存を抑止 → 閉じる
再構築 → ToastManager 再生成 → App の未消化通知を再表示
```

このデータフローは D-01〜18 に沿った推奨設計であり、実装済みとの主張ではない。 [ASSUMED]

### 読込結果は設定辞書と分離

`_load_settings()` は既存のテスト・呼出元で辞書として使われる。たとえば既存テストは「`result = _load_settings()`」「`result["theme"] == "light"`」を確認するため、戻り値を無条件に tuple に変えると修正範囲が広がる。辞書 API を維持しつつ、App に種別つきの結果を渡す補助 API を用意する設計を推奨する。 [VERIFIED: tests/test_settings_keyguard.py:275-289] [VERIFIED: pagefolio/app.py:148-150] [ASSUMED]

読込箇所の原文は「`if os.path.exists(path):`」「`data = json.load(f)`」「`data.setdefault(k, v)`」。不存在は正常な既定値、JSON デコード失敗と `OSError` は異なる結果にする。`UnicodeDecodeError`、JSON の root が辞書でない場合、`exists` と `open` の間の競合も失敗として安全に扱うテストが必要。 [VERIFIED: pagefolio/settings.py:301-311] [ASSUMED]

### 保存の成否と明示操作

現行保存は「`tmp_path = path + ".tmp"`」「`json.dump(to_save, f, ensure_ascii=False, indent=2)`」「`os.replace(tmp_path, path)`」。同じ順番を維持し、失敗時は作成された一時ファイルだけを削除し、失敗を返す。`_SENSITIVE_KEYS = sensitive_keys()` と `to_save` コピーも維持する。 [VERIFIED: pagefolio/settings.py:25-29] [VERIFIED: pagefolio/settings.py:314-343]

呼出元は App の終了時・言語切替・プラグイン再読込・LLM 即時適用・一般設定適用、設定ダイアログ内 LLM 適用、ショートカット、OCR ダイアログ、モザイク粒度、サムネイル倍率・件数である。保存成否を各画面へ伝える共通経路を計画し、明示操作だけが読込失敗後の上書きを許す。 [VERIFIED: pagefolio/app.py:575-585] [VERIFIED: pagefolio/app.py:598-603] [VERIFIED: pagefolio/app.py:633-636] [VERIFIED: pagefolio/app.py:668-695] [VERIFIED: pagefolio/dialogs/settings.py:224-240] [VERIFIED: pagefolio/dialogs/shortcuts.py:274-286] [VERIFIED: pagefolio/ocr_dialog.py:1031-1042] [VERIFIED: pagefolio/redact_ops.py:250-261] [VERIFIED: pagefolio/viewer.py:158-185]

特に SettingsDialog 内 LLM 適用は `dialogs/settings.py` で `_save_settings(self.current_settings)` を呼び、直後の `on_llm_apply` で `app.py:_apply_llm_settings_live` が `_save_settings(self.settings)` をもう一度呼ぶ。1操作につき2回の書込と通知が生じうるので、保存責務を一方に寄せる計画を立てる。 [VERIFIED: pagefolio/dialogs/settings.py:224-240] [VERIFIED: pagefolio/app.py:668-679]

### 通知状態は App 側

`ToastManager.show` は同カテゴリ再表示でフレームを増やさず文言を更新し、異カテゴリでは古いフレームを破棄する。D-16 の「毎回通知し、それぞれ残る」は単純な同カテゴリ `show` の繰返しでは満たせない。App 側で未消化イベントを順に扱い、画面再構築後に復元する設計を推奨する。キューの上限・自動消去時間は裁量事項であり、保存失敗を静かに捨てない仕様を計画で確定する。 [VERIFIED: pagefolio/toast.py:40-55] [VERIFIED: pagefolio/ui_builder.py:184-187] [ASSUMED]

`ToastManager` は現在再試行ボタンを無条件表示し、閉じる操作は manager 内部で完結する。設定失敗に再試行ボタンを付けない表示と、閉じたイベントを App の未消化通知へ反映する機構が必要。既存の PDF 保存・印刷トーストの `retry_cb` と `dismiss(category)` のテスト契約を壊さない。 [VERIFIED: pagefolio/toast.py:40-62] [VERIFIED: pagefolio/toast.py:80-95] [VERIFIED: tests/test_toast.py:105-160]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| UI 通知 | 独立 Toplevel や modal messagebox | 既存 `ToastManager` を拡張 | 現行の UI レイアウトと再構築入口が既にある。 [VERIFIED: pagefolio/toast.py:64-95] [VERIFIED: pagefolio/ui_builder.py:184-187] |
| 設定ファイル置換 | 本体 JSON へ直接 `open(..., "w")` | 既存 `.tmp` → `os.replace` | 元ファイル保護の実装と回帰テスト資産を維持できる。 [VERIFIED: pagefolio/settings.py:328-340] |
| 機密キー除外 | 呼出元ごとの個別除外 | `_SENSITIVE_KEYS` の共通ガード | 現行の保存用コピーとキー漏洩テストを維持できる。 [VERIFIED: pagefolio/settings.py:25-29] [VERIFIED: pagefolio/settings.py:314-327] [VERIFIED: tests/test_settings_keyguard.py:65-65] |

## Common Pitfalls

1. **終了確認より前の自動保存。** `_quit()` は確認ダイアログより先に `_save_window_state()` を呼ぶ。読込失敗時の抑止がないと、利用者が終了をキャンセルしても破損設定を上書きしうる。抑止を保存前に置き、終了キャンセルもテストする。 [VERIFIED: pagefolio/app.py:499-508] [VERIFIED: pagefolio/app.py:575-585]
2. **失敗後の偽の成功表示。** `_apply_settings()` は保存の成否と無関係に `_rebuild_ui()` 後「`status_settings`」を表示する。現在の辞書定義は「`status_settings`: `設定を変更しました` / `Settings updated`」であり、保存成功との直接表現ではないが、失敗後の文脈では誤誘導の余地がある。保存失敗の通知を優先し、成功表示条件を明確にする。 [VERIFIED: pagefolio/app.py:686-695] [VERIFIED: pagefolio/lang.py:276-276] [VERIFIED: pagefolio/lang.py:1084-1084] [ASSUMED]
3. **トースト状態の消失。** `_rebuild_ui()` は root の子を全破棄し `_build_ui()` が新しい `ToastManager` を作る。再表示の基準を App に置く。 [VERIFIED: pagefolio/app.py:697-716] [VERIFIED: pagefolio/ui_builder.py:184-187]
4. **一時ファイル cleanup の例外が元の失敗を隠す。** `json.dump` または `os.replace` の失敗後に cleanup も失敗しうる。元ファイルを触らず、保存失敗を必ず呼出元へ返すテストを行う。 [VERIFIED: pagefolio/settings.py:328-343] [ASSUMED]
5. **メモリ値の巻戻し。** 既存の表示更新は保存と前後している。明示設定変更後に保存失敗しても App の設定値・UI の選択を戻さない。 [VERIFIED: pagefolio/app.py:598-603] [VERIFIED: pagefolio/app.py:686-695] [VERIFIED: pagefolio/viewer.py:158-188]

## Code Examples

現行の単体テストは `_get_settings_path` を `tmp_path` のファイルへ差し替える。次の断片は実コードの原文であり、追加テストも同じ隔離を使える。 [VERIFIED: tests/test_settings_keyguard.py:275-286]

```python
settings_path = tmp_path / "partial_settings.json"
monkeypatch.setattr(
    "pagefolio.settings._get_settings_path",
    lambda: str(settings_path),
)
result = _load_settings()
```

上記の `"partial_settings.json"` は既存テストからの引用である。 [VERIFIED: tests/test_settings_keyguard.py:275-286]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | 読込結果を返す補助 API と App 保存窓口が最も小さい変更範囲。 | Architecture Patterns | 既存呼出元との互換を損ねる可能性。 |
| A2 | 保存失敗イベントを App 内で順番に扱う方式が D-16 を満たす。 | Architecture Patterns | 見た目・消去時刻の解釈次第で通知が消える。 |
| A3 | 読込失敗後に明示保存が成功したら終了時抑止状態を解除する。 | Open Questions — RESOLVED / 05-02-01 | D-14の計画上の具体化は確定。成功時だけ解除する実装の検証は未実施。 |
| A4 | `UnicodeDecodeError` と非辞書 JSON も破損系として利用者へ案内する。 | Architecture Patterns | D-03 の文言分類に追加判断が必要。 |

## Open Questions — RESOLVED（計画上の判断・実行経路）

1. **RESOLVED — D-14 の抑止解除条件。** 05-02-01 の `_persist_settings` 契約に従い、読込失敗後の自動保存抑止は明示保存が成功した時だけ解除する。失敗・抑止では保護を維持し、成功後は終了時保存を再開する。D-10/D-13/D-14 からの計画上の具体化であり、利用者の追加回答や実装済みという意味ではない。 [VERIFIED: 05-02-PLAN.md の05-02-01 behavior/action]
2. **RESOLVED — D-16 の「それぞれ通知が残る」の可視化。** 05-02-02 で App 所有の FIFO に失敗ごとの event_id を保持し、同時表示は1件、表示開始から10,000msまたは手動閉鎖で一つずつ消化する。未表示分の時間は進めず、再構築・割込みは残り時間で復元する。同文言の合併や保存成功による一括破棄はしない。 [VERIFIED: 05-01-01、05-02-02 の通知契約]
3. **RESOLVED — Tk 実行環境の選択。** sandboxでは `Cannot find a usable init.tcl`、制限外 `.venv` と専用basetempではToast 33 passed/全件ERROR 0を観測したため、実Tk検証は制限外の経路を使う。TclErrorの原因解明・非再発を意味しない。旧238 errors・6 failed、独立修復8689c27時の1635 passed/exit 0は履歴として保持する。**最新の05-REVIEWS.mdは1 failed / 1634 passed / 0 errors / 1 warning / 354.41秒 / exit 1**で、normal-entry-scriptのchild.communicate(timeout=12)期限超過が残る（原因未確定）。現在の `DEP-05-REGRESSION` は未充足。独立GSD debugと現行コード/環境での単一全件成功証拠まで実装/commitを停止し、旧成功で解除しない。正本は05-VALIDATION.md。 [VERIFIED: 05-REVIEWS.md「検証・コミット判断」、05-PLANNING-CHECKS.md、CLAUDE.md リリースゲート]
4. **RESOLVED — 要件文書と後続決定の読み分け。** REQUIREMENTS.md の原本保護は自動保存に適用し、明示的な設定変更保存は後続の CONTEXT.md D-13 に従い、確認ダイアログなしで許可する。05-01-02 と05-02-01に保護と解除の検証を分担した。 [VERIFIED: .planning/REQUIREMENTS.md:74-78、05-CONTEXT.md D-13、05-01/02-PLAN.md]

上記は計画に必要な判断の解決記録。実装の合格証拠ではなく、全件回帰依存 `DEP-05-REGRESSION` の解除も別途必要。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| `.venv/Scripts/python.exe` | pytest 実行 | ✓ | 3.15.1 | — |
| pytest | 設定・通知の検証 | ✓ | 9.1.1 | — |
| Ruff | Python 編集の必須ゲート | ✓ | 0.17.1 | — |
| Tcl/Tk runtime | 実ウィジェットの通知テスト | ✓ 制限外・専用basetempで実行可能（Toast 33 passed）。sandboxのTclError原因は未確定 | — | 過去失敗を保持。全件成功は `DEP-05-REGRESSION` の独立ゲートで判定 |

上記は 2026-10-22 にローカル CLI と実テストで確認。単体の設定テストは一時パス指定で 19 passed。 [VERIFIED: `.venv/Scripts/python.exe --version`, `.venv/Scripts/pytest.exe --version`, `.venv/Scripts/ruff.exe --version` 実行結果] [VERIFIED: `.venv/Scripts/python.exe -m pytest tests/test_settings_keyguard.py -q -p no:cacheprovider --basetemp "$env:TEMP\pagefolio-phase5-research-settings-20261022"` 実行結果]

## Validation Architecture

検証節は設定の原文「`"nyquist_validation": true`」に従い必須。 [VERIFIED: .planning/config.json:16-21]

| Property | Value |
|---|---|
| Framework | pytest 9.1.1（現 `.venv` 実測） |
| Config file | `pyproject.toml` の `[tool.pytest.ini_options]`、`testpaths = ["tests"]`。編集禁止。 [VERIFIED: pyproject.toml:11-12] |
| Quick run | `.venv/Scripts/python.exe -m pytest tests/test_settings_keyguard.py -q -p no:cacheprovider --basetemp "$env:TEMP\pagefolio-phase5-quick-<unique>"`（実測類似コマンドは19件成功） |
| Full suite / 必須ゲート | `.\.venv\Scripts\python.exe -m pytest -q --basetemp="$env:LOCALAPPDATA\Temp\pf_pytest_tmp"`（ルート CLAUDE.md:114-122 の指定どおり、単一プロセス・失敗0/ERROR0/クラッシュなし） [VERIFIED: CLAUDE.md:114-122] |

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| V110-CFG-01 | 不存在・不正 JSON・読取 `OSError` の結果と起動後1回通知 | unit + App lifecycle | `pytest tests/test_settings_keyguard.py tests/test_config_notification.py -q` | 既存単体 ✅ / 追加 ❌ Wave 0 |
| V110-CFG-02 | 全保存元で失敗通知、メモリ値保持、成功表示抑止 | unit + integration | `pytest tests/test_config_notification.py tests/test_provider_ui.py -q` | 追加 ❌ Wave 0 |
| V110-CFG-03 | 読込失敗後の終了保存抑止、明示保存許可、write/replace 失敗で原本保護・tmp 削除 | unit + integration | `pytest tests/test_config_notification.py tests/test_settings_keyguard.py -q` | 追加 ❌ Wave 0 |
| V110-CFG-04 | 読込1回・保存毎回・再構築後未消化通知保持 | Tk widget + App state | `pytest tests/test_config_notification.py tests/test_toast.py -q` | Toast 既存 ✅ / 追加 ❌ Wave 0 |

**Test design:** 一時ファイルへ `monkeypatch` し、`json.dump`/`os.replace`/`open` の失敗点をそれぞれ注入して旧ファイル bytes と `.tmp` の有無を検証する。App 側は実ウィジェットに依存しない通知記録スタブで成否・回数・呼出順を検証し、Tk が動く環境では `tests/test_toast.py` 型の隠し root テストで見た目と閉じる操作を確認する。 [VERIFIED: tests/test_settings_keyguard.py:145-165] [VERIFIED: tests/test_toast.py:22-34] [ASSUMED]

**Sampling rate:** 各実装タスク後は対象テスト、wave 後は関連テスト、Phase gate は AGENTS.md 指定の `ruff check . && ruff format .`、構文確認、`pytest` 全件。`ruff format .` は編集を伴うため、他作業者の変更を巻き込まないよう実行時点の共有状態を確認する。 [VERIFIED: AGENTS.md:49-59] [VERIFIED: AGENTS.md:104-110]

**Gate rule:** TclError が出たら該当ファイル単体→フルスイート再実行で切り分け、最初の ERROR も記録する。再実行の部分成功、テストの除外、skip による通過はゲート合格として扱わない。 [VERIFIED: CLAUDE.md:135-150]

**Wave 0 gaps:** `tests/test_config_notification.py` 相当の障害注入・App 状態テスト、`tests/test_toast.py` の再試行なし/再構築保持の拡張。新パッケージと `pyproject.toml` 変更は不要。 [ASSUMED]

## Security Domain

設定の原文は「`"security_enforcement": true`」「`"security_asvs_level": 1`」。 [VERIFIED: .planning/config.json:42-43]

ASVS 5.0.0 は Web アプリ向け標準で、PageFolio は Windows デスクトップアプリである。ここでは設定ファイルとエラー通知に関係する章を点検の観点として使い、ASVS 準拠の宣言には用いない。最新版 5.0.0 の章番号は旧版と異なる。 [CITED: https://asvs.owasp.org/] [CITED: https://cornucopia.owasp.org/taxonomy/asvs-5.0] [VERIFIED: AGENTS.md:11-15]

| ASVS 5.0.0 Category | Applies | Standard Control |
|---|---|---|
| V2 Validation and Business Logic | yes | JSON の構文・root 形状を検証して既定値へのフォールバックを判定。 [CITED: https://cornucopia.owasp.org/taxonomy/asvs-5.0] [ASSUMED] |
| V5 File Handling | yes | 一時ファイル書込後の置換と失敗時 cleanup を維持。 [CITED: https://cornucopia.owasp.org/taxonomy/asvs-5.0] [VERIFIED: pagefolio/settings.py:328-343] |
| V13 Configuration / V14 Data Protection | yes | 読込失敗後の原本保護と `_SENSITIVE_KEYS` 除外を維持。 [CITED: https://cornucopia.owasp.org/taxonomy/asvs-5.0] [VERIFIED: pagefolio/settings.py:25-29] |
| V16 Security Logging and Error Handling | yes | 利用者向け通知に機密値・技術例外を含めず、失敗を呼出元へ伝える。 [CITED: https://cornucopia.owasp.org/taxonomy/asvs-5.0] [VERIFIED: .planning/phases/05-config-notification/05-CONTEXT.md:18-24] |
| V6 Authentication / V7 Session Management / V8 Authorization / V11 Cryptography | 今回の設定 I/O 要件には新規対象なし | 既存機能を変更しない。 [CITED: https://cornucopia.owasp.org/taxonomy/asvs-5.0] [VERIFIED: .planning/REQUIREMENTS.md:45-48] |

| Threat | STRIDE | Mitigation |
|---|---|---|
| 読込失敗後の自動保存による原本上書き | Tampering | 読込失敗状態を保持し、終了時の `_save_window_state` 保存を抑止。 [VERIFIED: pagefolio/app.py:499-508] [VERIFIED: pagefolio/app.py:575-585] [ASSUMED] |
| 保存途中の失敗による JSON 破損 | Tampering | 既存 `.tmp`→`os.replace` を維持し、失敗時に一時ファイルを cleanup。 [VERIFIED: pagefolio/settings.py:328-343] [ASSUMED] |
| API キーの設定 JSON / ログ流出 | Information Disclosure | `_SENSITIVE_KEYS` ガードとキー値をログに出さないテストを維持。 [VERIFIED: pagefolio/settings.py:25-29] [VERIFIED: tests/test_settings_keyguard.py:167-185] |

## Sources

### Primary (current repository)

- `.planning/phases/05-config-notification/05-CONTEXT.md` — D-01〜18 と裁量・除外範囲。
- `.planning/REQUIREMENTS.md:45-48`, `.planning/ROADMAP.md:163-172`, `.planning/PROJECT.md:23-34`, `.planning/phases/04-startup-control/04-CONTEXT.md:52-57` — 受入条件、境界、通知方針。
- `pagefolio/settings.py:254-343`, `pagefolio/app.py:138-149,499-508,575-722`, `pagefolio/toast.py:30-106`, `pagefolio/ui_builder.py:184-200` — 設定 I/O と UI 接続。
- `tests/test_settings_keyguard.py:65-212,275-290`, `tests/test_toast.py:22-196` — 既存回帰テスト。

### External official reference

- [OWASP ASVS 5.0.0](https://asvs.owasp.org/) — 版と Web アプリ向けの対象範囲。
- [OWASP ASVS 5.0 章一覧](https://cornucopia.owasp.org/taxonomy/asvs-5.0) — 章番号の確認。

追加パッケージを推奨していないため、今回の package legitimacy gate に対象はない。

## Metadata

**Confidence breakdown:** 設定 I/O と呼出経路 HIGH（現行ソース確認）、通知設計 MEDIUM（現行契約を確認したが新設計は推奨）、実 UI 検証 LOW（Tk 初期化不可）。  
**Research date:** 2026-10-22  
**Valid until:** Phase 5 実装時に再確認（共有作業場の変更がありうる）。
