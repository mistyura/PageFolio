# Phase 1: 保存・編集・設定の安全性是正（失敗時ロールバック担保） - Research

**Researched:** 2026-08-10
**Domain:** PyMuPDF (fitz) ドキュメント永続化・Undo/Redo デルタ管理・Tkinter ダイアログ状態遷移（既存コードベースの防御的リファクタリング。新規ライブラリ導入なし）
**Confidence:** HIGH（対象 9 要件すべて、実装対象コードを本セッションで直接 Read し、暗号化ストリップの根本原因は実行時テストで再現・検証済み）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**保存時の暗号化契約（V190-SAFE-01 / V190-SAFE-02）**
- **D-01:** パスワード保護 PDF の「名前を付けて保存」は**無確認で常に暗号化を維持**する。`_save_as()` の `self.doc.save(path)` に `encryption=fitz.PDF_ENCRYPT_KEEP` を無条件付与する。暗号化解除は既存の「🔒 パスワード → 解除」（`_remove_password` / `save_without_password`）だけで発生させる。確認ダイアログは追加しない。
- **D-02:** `_overwrite_current_file(path, **save_kwargs)` は **`encryption` 未指定時に `PDF_ENCRYPT_KEEP` を関数内で既定化**する（呼び出し側での明示は採らない）。`_set_password`（`PDF_ENCRYPT_AES_256`）/ `_remove_password`（`PDF_ENCRYPT_NONE`）は明示的に kwargs を渡しているので影響を受けない。
- **D-03:** 保存後の `self.pdf_has_password` は**保存 kwargs から論理的に導出**する（`KEEP` → 現在値を維持 / `AES_256` → True / `NONE` → False）。実行時 I/O は発生させない。**回帰テスト側では保存先 PDF を実際に開いて `needs_pass` を検証**する。

**OCR OFF の一貫化（V190-SAFE-03）**
- **D-04:** OCR プロバイダが `off` のとき、ツールメニューの「バッチOCR」項目自体を **`disabled` にして起動できなくする**。
- **D-05:** disabled の理由は **OFF の間だけメニューラベルへ「（OCR OFF）」を併記**して伝える。i18n 文言を日英 1 件ずつ追加する。
- **D-06:** `build_provider()` は **`off` のみを専用例外で拒否**する（OCR 無効を表す専用例外型を新設）。**空文字 `""` は従来どおり LM Studio として後方互換を維持**する。`None` 返却案は不採用。 — **Reversibility: costly**（`build_provider` の全呼び出し元が例外ハンドリング前提になり、Phase 2 の OpenAI 追加もこの契約の上に載る）。
- **D-07:** OFF ガードは「`settings["ocr_provider"]` が `off` なら OCR 実行経路に一切入らない」という単一の意味で通常 OCR・バッチ OCR・プラグイン登録プロバイダ経路すべてに適用する。バッチ OCR は起動時（D-04）と `_on_start_batch` の実行開始時の二重ガードとする。

**失敗時ロールバックの方式と通知（V190-SAFE-04 / V190-SAFE-05 / V190-UNDO-01 / V190-UNDO-02）**
- **D-08:** 複数ファイル挿入（`page_ops.py:_do_insert`）は**挿入済みページ数を追跡し、例外時に `delete_page` で巻き戻す**方式にする。一時 Document へ全入力を結合してから本体へ 1 回で反映する案・件数によるハイブリッドは不採用。
- **D-09:** 挿入元 Document は `try/finally` で**必ずクローズ**する（現状は `src.close()` が正常系にしかなく、`insert_pdf()` 例外時にリークする）。
- **D-10:** 巻き戻し自体が失敗した場合は、**警告ダイアログで残存ページ数を明示**し、**実際の挿入数を反映した Undo state は残す**。無警告で部分適用を残すことは許容しない。
- **D-11:** ページ複製（`page_ops.py:_duplicate_page`）は **`_save_undo("duplicate")` を実処理の成功後に確定**させる（現状は実処理より先に呼んでいる）。
- **D-12:** 「Undo 記録の後置」パターンの適用は**今回は要件対象の duplicate / insert の 2 経路のみ**に留める。全 op を棚卸しして「記録が先置きのままの op 一覧」を SUMMARY に記録し、次マイルストーン候補として残す。共通コンテキストマネージャの新設と全 op 一斉適用は不採用。
- **D-13:** Undo/Redo（`file_ops.py:_undo` / `_redo`）の復元失敗時は、**pop した状態をスタックへ戻したうえで messagebox のエラーダイアログでブロック通知**する。トースト・ステータスバーは不採用。
- **D-14:** スタックへ戻す際は既存の Blob ライフサイクル規約を厳守する（`_push_evicting` / `_clear_redo_stack` 経由・失敗した state の Blob は dispose しない）。あわせて `_do_insert` の例外処理にある `self._undo_stack.pop()` という直接操作も規約違反として同時に是正する。

**設定 UI の Apply/Cancel 契約（V190-CFG-01 / V190-CFG-02）**
- **D-15:** 外部プロンプトファイル（`ocr_custom_prompt.md` / `ocr_summary_prompt.md`）への書き込みを **Apply 押下時へ一本化**する（`sections.py:_on_template_change` 内の `save_prompt_file()` 即時呼び出しを撤去）。ライブ連動＋Cancel 復元案は Out of Scope。
- **D-16:** Apply 時に書き込む内容は**入力欄の現在値**とする（アクティブテンプレートの保存済み値ではない）。v1.8.0 D-07 の不変条件は「Apply 時点の入力欄内容」へ置き換わる。
- **D-17:** Apply 時に外部ファイルが存在しない場合は**新規作成しない**（`prompt_file_exists()` ガードを維持）。
- **D-18:** テンプレート切替時の未保存判定（`_has_unsaved_template_changes`）は、アクティブテンプレート選択済みの場合に**常に入力欄と `get_template()` の保存済み値を比較**する（`prompt_file_exists()` による分岐を削除し判定経路を 1 本にする）。アクティブテンプレート未選択時の既存ロジックは維持する。
- **D-19:** LLM 設定画面の外部ファイルに関する注記文言は**変更しない**（i18n 差分ゼロ）。

### Claude's Discretion
- LLM 設定 Apply 直後にツールメニューの「バッチOCR」項目を再評価する配線方法（既存の `_update_ocr_buttons_state()` と同じタイミングで再評価するのが素直）
- OCR 無効を表す専用例外の型名・配置（`ocr_providers/errors.py` に置くか `ocr.py` に置くか）
- 挿入失敗時のエラーメッセージに失敗ファイル名・成功件数をどこまで含めるか
- `duplicate` / `merge` / `merge_resize` の 4 手往復回帰テスト（V190-UNDO-02）のテストファイル配置と粒度
- プラン分割の粒度（保存系 / OCR OFF 系 / ロールバック系 / 設定 UI 系のどこで切るか）

### Deferred Ideas (OUT OF SCOPE)
- Undo 記録が先置きのまま残る他 op（rotate / crop / delete / bulk_move / bulk_crop / merge 等）への「記録後置」パターン水平展開 — 棚卸し一覧を SUMMARY に記録するのみ
- Save As 時に平文コピーを作る専用導線 — 「解除は明示操作のみ」を選択したため不要
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V190-SAFE-01 | パスワード保護 PDF を「保存」「名前を付けて保存」「上書きフォールバック」いずれで実行しても暗号化維持 | `_overwrite_current_file`/`_save_as` の `encryption` 既定挙動を実行時テストで検証済み（下記「PyMuPDF 暗号化ストリップの根本原因」）。修正パターンを Code Examples に記載 |
| V190-SAFE-02 | 暗号化解除は明示操作のみ・`pdf_has_password` が実ファイルと一致 | `save_kwargs` からの論理導出方式を Architecture Patterns に記載。既存 `_set_password`/`_remove_password` の kwargs 構造を確認済み |
| V190-SAFE-03 | OCR OFF が通常/バッチ/プラグイン経路すべてで一貫 | `build_provider` の現行 3-way 判定に加え、`ocr_dialog.py` 内に**同型の重複ハードコード分岐が2箇所**存在することを特定（Common Pitfalls 参照）。全経路の呼び出しマップを記載 |
| V190-SAFE-04 | 複数ファイル挿入の途中失敗でページ数・Undo スタック不変、挿入元 Document 必ずクローズ | `_do_insert` の現行実装の 2 つのバグ（src リーク・部分挿入の無警告残留）を特定。ロールバック実装パターンを記載 |
| V190-SAFE-05 | ページ複製失敗で既存ページ・Undo スタック不変 | `_duplicate_page` の `_save_undo` 呼び出し順序を確認し、成功後確定への入替パターンを記載 |
| V190-CFG-01 | LLM 設定 Cancel で外部プロンプトファイル不変・書き込みは Apply のみ | `sections.py:_on_template_change` の即時書き込み箇所・`dialog.py:_apply` の既存書き込み箇所を特定 |
| V190-CFG-02 | テンプレート編集後の切替で常に未保存確認 | `_has_unsaved_template_changes` の `prompt_file_exists()` 分岐を特定し、削除後の単一経路化パターンを記載 |
| V190-UNDO-01 | Undo/Redo 復元失敗時に state を戻し履歴を失わない | `_undo`/`_redo` に例外処理が皆無であることを確認。Blob 破棄タイミング（成功時のみ dispose）を含めた修正パターンを記載 |
| V190-UNDO-02 | duplicate/merge/merge_resize の4手往復回帰テスト | 既存テストが3手（do→undo→redo）止まりであることを確認済み。insert の4手往復テスト（`test_insert_undo_redo_undo_roundtrip`）を雛形として提示 |
</phase_requirements>

## Summary

本フェーズは新規ライブラリを一切導入しない、既存コードベース（PyMuPDF 1.28.0 / Tkinter）に対する防御的リファクタリングである。9要件はいずれも「操作が失敗した場合に Document・Undo 履歴・外部ファイルが操作前の状態へ戻ること」という単一テーマに収束し、対象コードはすべて `pagefolio/file_ops.py`・`pagefolio/page_ops.py`・`pagefolio/ocr.py`・`pagefolio/app.py`・`pagefolio/dialogs/batch_ocr.py`・`pagefolio/dialogs/llm_config/{sections,dialog}.py` の6ファイルに閉じる。

最も重要な発見は、V190-SAFE-01/02 の根本原因を**実行時テストで再現・確認済み**であることだ。PyMuPDF 1.28.0 では、認証済み暗号化ドキュメントに対して `Document.save()` / `Document.tobytes()` を `encryption=` 引数**なし**で呼ぶと、既定で暗号化が完全に失われる（`needs_pass` が `0` になる）。`_overwrite_current_file()`（`_save_file` のインクリメンタル保存失敗時フォールバック経路）と `_save_as()` はいずれもこの引数を渡していないため、パスワード保護 PDF を保存し直すと平文化する構造的バグが実在する。D-01/D-02 の「`encryption=fitz.PDF_ENCRYPT_KEEP` を無条件・既定値として埋め込む」という決定は、この検証済み事実に対する唯一の正しい修正である。

V190-SAFE-03（OCR OFF の一貫化）は、CONTEXT.md の canonical_refs が挙げる `ocr.py:431-441` の `build_provider` 分岐だけでなく、`ocr_dialog.py` 内に**独立した同型ハードコード分岐が最低2箇所**（`_apply_llm_settings` 内 1065行目・`_on_run` 内 1506行目）存在することが本セッションのコード調査で判明した。これらは `build_provider` を経由せず `elif name in ("lmstudio", "", "off"):` で直接 `LMStudioProvider` を構築するため、`build_provider` だけを直しても OCR ダイアログ内部の provider 再生成ロジックは「off を LM Studio として動かす」旧挙動のまま残る。D-04（メニュー入口を disabled 化）による防御が機能する限り実害はないが、プランはこの重複箇所の存在を認識し、少なくとも「到達不能であることの明示的なコメント／防御的アサーション」または「重複ロジックの解消」のどちらかを選択する必要がある。

V190-SAFE-04/05・V190-UNDO-01/02 は、既存の「op 別逆デルタ + Blob ライフサイクル」という確立されたアーキテクチャの上に「例外安全性」を追加する作業である。新しいUndo機構を発明する必要はなく、既存の `_push_evicting`/`_dispose_state`/`_capture_page_blob` を正しい順序で呼ぶだけで要件を満たせる。

**Primary recommendation:** 新規ライブラリ・新規アーキテクチャパターンは導入しない。既存の「op別逆デルタ + Blobストア」「build_provider ファクトリ」「Apply/Cancel 独立トランザクション（`_apply_llm_settings_live` パターン）」という3つの確立された設計に対して、例外パスの防御を後付けする形でタスクを組む。

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PDF 暗号化維持・導出（保存3経路） | ファイル永続化層（`file_ops.py`） | — | fitz.Document の save/tobytes 呼び出しに閉じる。UI 層は関与しない |
| OCR プロバイダ生成・OFF ガード | ドメインロジック層（`ocr.py:build_provider`） | UI 層（メニュー disabled 化・`app.py`/`batch_ocr.py`） | ファクトリでの拒否（構造的安全網）とUI入口での抑止（利便性・多重防御）の二層構成 |
| 複数ファイル挿入のロールバック | ドメインロジック層（`page_ops.py:_do_insert`） | — | fitz.Document 操作とUndo デルタ構築が密結合しており分離不可 |
| Undo/Redo 復元失敗時の状態保全 | ドメインロジック層（`file_ops.py:_undo/_redo`） | UI 層（messagebox 通知） | 復元ロジックはドメイン層、通知のみUI層の責務 |
| LLM 設定 Apply/Cancel の外部ファイル同期 | UI ダイアログ層（`dialogs/llm_config/`） | 設定永続化層（`settings.py`） | ダイアログの Apply ハンドラが唯一の書き込みトリガー。ファイル I/O 自体は `settings.py` のヘルパー関数 |

## Standard Stack

本フェーズは新規パッケージを導入しない。既存依存のみを使用する。

### Core（既存・変更なし）
| Library | Version（実測） | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (`fitz`) | 1.28.0（`requirements.txt` 固定・本セッションの実行環境で確認）[VERIFIED: ローカル実行環境 `python -c "import fitz; print(fitz.__version__)"`] | PDF I/O・暗号化・ページ操作 | プロジェクト既存の唯一の PDF エンジン |
| pytest | 9.1.1（ローカル実行環境で確認）[VERIFIED: ローカル実行環境 `pytest --version`] | 回帰テスト実行 | プロジェクト既定 |
| ruff | 0.15.20（ローカル実行環境で確認）[VERIFIED: ローカル実行環境 `ruff --version`] | Lint/Format | CLAUDE.md 必須ゲート |

### Alternatives Considered
本フェーズでは代替ライブラリの検討は不要（既存コードの防御的修正のみ）。

**Installation:** 不要（新規依存なし）。

## Package Legitimacy Audit

> 本フェーズは新規外部パッケージを一切導入しない。Package Legitimacy Gate の対象パッケージなし。

**Packages removed due to [SLOP] verdict:** none（対象なし）
**Packages flagged as suspicious [SUS]:** none（対象なし）

## Architecture Patterns

### PyMuPDF 暗号化ストリップの根本原因（V190-SAFE-01/02 の核心・実行時検証済み）

**検証手順と結果**（本セッションでローカル pymupdf 1.28.0 に対して実行）:

```python
# 検証1: tobytes() を encryption 引数なしで呼ぶと暗号化が失われる
doc = fitz.open()
doc.new_page().insert_text((72, 72), "hello")
doc.save("enc.pdf", encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="secret", user_pw="secret")
doc.close()

d2 = fitz.open("enc.pdf")
d2.authenticate("secret")
data = d2.tobytes()  # encryption= 未指定
d2.close()

d3 = fitz.open(stream=data, filetype="pdf")
print(d3.needs_pass)  # => 0 （平文化した！）
```

```python
# 検証2: save() も同様。encryption=fitz.PDF_ENCRYPT_KEEP を明示すれば維持される
d2.save("out.pdf")                                   # needs_pass => 0（平文化）
d2.save("out.pdf", encryption=fitz.PDF_ENCRYPT_KEEP)  # needs_pass => 1（維持・authenticate も成功）
```

[VERIFIED: ローカル pymupdf 1.28.0 実行時テスト（本セッションで実行・上記スクリプトの出力を確認）]

**結論:** `Document.save()` / `Document.tobytes()` の `encryption` 引数の既定動作は「暗号化を保持しない」。呼び出し側が明示的に `encryption=fitz.PDF_ENCRYPT_KEEP` を渡さない限り、認証済み暗号化ドキュメントを保存し直すと平文化する。

**現行コードの該当箇所（実際に脆弱）:**

- `pagefolio/file_ops.py:636` `_overwrite_current_file`: `data = self.doc.tobytes(**save_kwargs)` — `save_kwargs` に `encryption` が含まれない全呼び出し元（`_save_file` のインクリメンタル失敗フォールバック `file_ops.py:673`、`_save_compressed` の圧縮保存 `file_ops.py:755`）で平文化する。[VERIFIED: pagefolio/file_ops.py:626-646, 673, 751-755 — `data = self.doc.tobytes(**save_kwargs)` / `self._overwrite_current_file(self.filepath)` / `save_kwargs = {"garbage": 4, "deflate": 1, "clean": 1}`]
- `pagefolio/file_ops.py:698` `_save_as`: `self.doc.save(path)` — `encryption` 引数が一切ない。[VERIFIED: pagefolio/file_ops.py:688-698 — `self.doc.save(path)`]

**対比: 既に安全な既存コード**

- `_save_file` の**インクリメンタル保存本体**（`incremental=True` の1回目の試行）は既に正しい: `pagefolio/file_ops.py:668-670` `self.doc.save(self.filepath, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)` [VERIFIED: pagefolio/file_ops.py:666-673]。インクリメンタル保存が成功する限り SAFE-01 は既に満たされている。**バグが顕在化するのはインクリメンタル保存が失敗し `_overwrite_current_file` フォールバックへ落ちたときのみ**（要件文の「上書き（インクリメンタル保存失敗時のフォールバック）」が名指ししている経路と一致）。

### PDF 保存3経路と暗号化維持の対応表

| 保存経路 | 呼び出し | 現状の `encryption` 指定 | 修正方針（D-01/D-02） |
|---------|---------|------------------------|----------------------|
| 上書き保存（インクリメンタル成功時） | `_save_file` → `self.doc.save(path, incremental=True, encryption=PDF_ENCRYPT_KEEP)` | 既に正しい | 変更不要 |
| 上書き保存（インクリメンタル失敗フォールバック） | `_save_file` → `_overwrite_current_file(self.filepath)` | 未指定（バグ） | `_overwrite_current_file` 関数内で `save_kwargs.setdefault("encryption", fitz.PDF_ENCRYPT_KEEP)` |
| 名前を付けて保存 | `_save_as` → `self.doc.save(path)` | 未指定（バグ） | `self.doc.save(path, encryption=fitz.PDF_ENCRYPT_KEEP)` を無条件付与 |
| 圧縮して保存（同一ファイル上書き時） | `_save_compressed` → `_overwrite_current_file(path, **save_kwargs)` | `_overwrite_current_file` の既定化に相乗り | `_overwrite_current_file` 側の既定化で自動的に安全化 |
| パスワード設定 | `_do_set_password` → `save_with_password` / `_overwrite_current_file(path, encryption=AES_256, ...)` | 明示指定済み | 変更不要（影響を受けない設計） |
| パスワード解除 | `_remove_password` → `save_without_password` / `_overwrite_current_file(path, encryption=NONE)` | 明示指定済み | 変更不要 |

### `pdf_has_password` の論理導出（D-03）

`save_kwargs` の `encryption` 値から `pdf_has_password` を導出するヘルパーを1箇所に集約する。実装時の分岐対応:

```python
# 概念パターン（D-03: 実行時 I/O なしの純粋な論理導出）
if encryption == fitz.PDF_ENCRYPT_NONE:
    self.pdf_has_password = False
elif encryption == fitz.PDF_ENCRYPT_AES_256:
    self.pdf_has_password = True
else:  # PDF_ENCRYPT_KEEP または未指定（＝KEEP と等価に既定化される）
    pass  # 現在値を維持（変更しない）
```

回帰テストは実際に保存先を `fitz.open()` して `needs_pass` を確認する（D-03 の追記事項）。既存 `tests/test_password.py` の `TestSetRemovePassword` クラスと同型のパターンが既に存在する（`fitz.open(out); assert reopened.needs_pass` 等）。[VERIFIED: tests/test_password.py:132-141, 152-167]

### OCR OFF ガードの経路マップ（V190-SAFE-03）

**発見: `build_provider` 以外にも "off" を扱うハードコード分岐が複数存在する**

```
grep '"off"|'"'"'off'"'"'' pagefolio/ocr_dialog.py の結果:
  859:  if name in ("lmstudio", "", "off"):        # _provider_model_name（表示専用・実害小）
  1065: elif name in ("lmstudio", "", "off"):      # _apply_llm_settings 内・provider 再生成
  1506: elif name in ("lmstudio", "", "off"):      # _on_run 内・provider 再生成
```
[VERIFIED: pagefolio/ocr_dialog.py:859, 1065-1074, 1506-1516 — 3箇所とも `elif name in ("lmstudio", "", "off"):` の分岐後に `LMStudioProvider(...)` を直接構築（`build_provider` を経由しない）]

これらは `build_provider()` を呼ばずに `LMStudioProvider` を直接構築するため、**D-06 で `build_provider` に例外を追加するだけでは `ocr_dialog.py` 内部の provider 再生成ロジックには影響しない**。実害は次の多層防御構造によって現状抑止されている:

1. `app.py:_update_ocr_buttons_state()`（334-346行目）が `ocr_provider == "off"` のとき通常 OCR ボタン群を disabled 化する（既存実装済み・変更不要）。[VERIFIED: pagefolio/app.py:334-346]
2. D-04 で「バッチOCR」メニュー項目も同様に disabled 化する（新規実装対象）。
3. `ocr_dialog.py` 自体は `OCRDialog(...)` が明示的に開かれない限り生成されない（`_start_ocr` 経由でのみ生成、かつ `_start_ocr` は `build_provider` の例外を捕捉してブロックする設計にする＝D-06/D-07 の対象）。

**結論（プランへの示唆）:** 入口（メニュー・ボタン disabled 化）が主防御線であり、`build_provider` の例外化は「入口をすり抜けた場合の構造的安全網」という位置づけになる。`ocr_dialog.py` 内の3箇所の重複ハードコード分岐は**入口ガードが機能する限り到達しない**ため必須の修正対象ではないが、D-07 の「OCR 実行経路に一切入らない」という文言を厳密に満たすには、`_start_ocr`（`ocr.py:541-618`）が `build_provider` の新例外を捕捉してダイアログを開かせない実装にすることが必須。バッチ側は `_build_provider_once`（`batch_ocr.py:592-625`）が `build_provider` を直接呼ぶため（独自の "off" 分岐を持たない）、D-06 の例外化だけで自然にガードされる。[VERIFIED: pagefolio/dialogs/batch_ocr.py:592-625 — `_check_cloud_api_key`/`_confirm_batch_cost` は "off" を `_cloud_providers = {"claude", "gemini", "runpod"}` に含めないため通過し、唯一の防波堤は `build_provider` 呼び出し自体]

**呼び出し元一覧（`build_provider` を実際に呼ぶ箇所・grep 済み）:**

| 呼び出し元 | ファイル:行 | 現状の例外処理 |
|-----------|------------|---------------|
| `_start_ocr`（通常 OCR 起動） | `ocr.py:584-596` | `except ValueError as e:` で捕捉しエラー表示（新例外もここに追加要） |
| `_build_provider_once`（バッチ OCR 起動時プロバイダ構築） | `batch_ocr.py:612-614` | try/except なし（新例外を追加要・D-07 の「実行開始時」二重ガード） |
| `_apply_llm_settings`（OCR ダイアログ内 Apply 直後の再生成） | `ocr_dialog.py:1005-1094` | `except Exception as e:` で包括捕捉・progress_var へエラー表示のみ（"off" は分岐 1065 でここに到達しない） |
| `_on_run`（OCR ダイアログ実行開始時の再生成） | `ocr_dialog.py:1438-1524` | 例外処理なし（"off" は分岐 1506 でここに到達しない） |
| `_switch_to_fallback_provider`（フォールバック切替） | `ocr_dialog.py:2446-2458` | 例外処理なし（フォールバック候補リストは既知プロバイダのホワイトリストのため "off" は含まれない・実害なし） |

### 例外型設計の precedent（Claude's Discretion 項目への参考情報）

既存の `pagefolio/ocr_providers/errors.py` には `OCRAPIKeyError` / `OCRRetryableError` / `OCRContextLengthError` の3例外がすべて `RuntimeError` を継承し、同一ファイルに集約されている。[VERIFIED: pagefolio/ocr_providers/errors.py:1-46] 新設する OCR OFF 専用例外もこの precedent に倣い `errors.py` に配置し `RuntimeError` を継承するのが既存パターンとの一貫性が高い（`ocr.py` への配置も技術的に可能だが、`errors.py` は「OCR プロバイダ共通の例外クラス」を明示的に集約する既存の責務境界と一致する）。

### `_do_insert` のロールバック設計（V190-SAFE-04）

**現行コードの2つのバグ（本セッションで確認済み）:**

```python
# pagefolio/page_ops.py:756-790（現状）
def _do_insert(self, ordered_paths, insert_at):
    self._save_undo("insert", insert_at=insert_at)
    try:
        total = 0
        pos = insert_at
        for path in ordered_paths:
            src = self._open_path_as_pdf(path)
            self.doc.insert_pdf(src, start_at=pos)  # ← ここで例外が出ると src が close() されない
            pos += len(src)
            total += len(src)
            src.close()
        self._undo_stack[-1]["data"][1] = total
        ...
    except Exception as e:
        # バグ2: total 件が既に self.doc に挿入済みでも、ここでは
        # 巻き戻さず undo エントリを直接 pop するだけ。
        # 2番目以降のファイルで失敗した場合、1番目のファイルの挿入分が
        # ページ数に残ったまま Undo できなくなる（無警告の部分適用）。
        if self._undo_stack and self._undo_stack[-1].get("op") == "insert":
            self._undo_stack.pop()
        ...
```
[VERIFIED: pagefolio/page_ops.py:756-790 — 上記コードブロックは実ファイルから逐語転記]

- **バグ1（D-09 対象）:** `src = self._open_path_as_pdf(path)` の後、`self.doc.insert_pdf(src, start_at=pos)` が例外を送出すると `src.close()`（ループ末尾）に到達せず `src` がリークする。
- **バグ2（D-08/D-10 対象）:** ループの1〜n番目のファイルまで成功し n+1 番目で失敗した場合、既に `self.doc` へ挿入済みの1〜nファイル分のページはロールバックされず、かつ `self._undo_stack.pop()` で undo エントリ自体を消してしまうため、ユーザーは Ctrl+Z でも復旧できない「無警告の部分適用」状態に陥る。

**D-08〜D-10 の実装パターン（ページ数追跡 + delete_page 巻き戻し + try/finally）:**

```python
# 概念パターン（実装詳細はプランで確定）
def _do_insert(self, ordered_paths, insert_at):
    self._save_undo("insert", insert_at=insert_at)
    total = 0
    pos = insert_at
    try:
        for path in ordered_paths:
            src = self._open_path_as_pdf(path)
            try:
                self.doc.insert_pdf(src, start_at=pos)
                n = len(src)
                pos += n
                total += n
            finally:
                src.close()  # D-09: 例外時も必ずクローズ
        self._undo_stack[-1]["data"][1] = total
        ...（正常系の後処理）
    except Exception as e:
        # D-08: 挿入済み total 件を巻き戻す
        try:
            for _ in range(total):
                self.doc.delete_page(insert_at)
            # 巻き戻し成功: total=0 相当なので undo エントリを破棄してよい
            if self._undo_stack and self._undo_stack[-1].get("op") == "insert":
                self._undo_stack.pop()
        except Exception:
            # D-10: 巻き戻し自体が失敗 → 警告ダイアログ + 実挿入数を反映した
            # undo state を残す（pop しない。data[1] を実 total へ更新する）
            self._undo_stack[-1]["data"][1] = total
            messagebox.showwarning(..., <残存ページ数を明示するメッセージ>)
        self._invalidate_thumb_cache()
        self._refresh_all()
        messagebox.showerror(self._t("err_title"), str(e))
```

**巻き戻し方向の注意（既存パターンとの整合）:** `delete_page(insert_at)` を `total` 回繰り返す方式は、既存の `_restore_state` の `insert` op 実行（`file_ops.py:391-394`）と同一パターンである: `for _ in range(num): self.doc.delete_page(insert_at)`。[VERIFIED: pagefolio/file_ops.py:391-394 — `elif op == "insert": insert_at, num = state["data"]; for _ in range(num): self.doc.delete_page(insert_at)`] 新規ロジックを発明せず、この既存パターンを再利用できる。

### `_duplicate_page` の Undo 確定タイミング（V190-SAFE-05）

現行実装は `_save_undo("duplicate", pno=pno)` を `try:` ブロックの**外側・実処理の前**で呼んでいる。[VERIFIED: pagefolio/page_ops.py:177-193 — `self._save_undo("duplicate", pno=pno)` は183行目、`try:` は184行目から開始]

```python
def _duplicate_page(self):
    if not self._check_doc():
        return
    pno = self.current_page
    self._save_undo("duplicate", pno=pno)   # ← 実処理前に確定（バグ）
    try:
        tmp = fitz.open()
        tmp.insert_pdf(self.doc, from_page=pno, to_page=pno)
        self.doc.insert_pdf(tmp, start_at=pno + 1)
        tmp.close()
        ...
    except Exception as e:
        messagebox.showerror(self._t("err_title"), str(e))
        # ← ここで return する前に、既に「duplicate」undo エントリが
        #    積まれている。実際には複製されていないのに Ctrl+Z すると
        #    duplicate op の逆操作（pno+1 を delete_page）が走り、
        #    無関係な既存ページを誤って削除する
```

D-11 の修正は「`_save_undo` の呼び出しを `try` ブロック内・実処理成功後（例外送出可能な操作がすべて完了した後）へ移動する」。既存の `_save_undo("duplicate", pno=pno)` は `pno` の値のみを引数に取る（キャプチャ処理を伴わない軽量呼び出し）ため、成功後に呼んでもタイミング上の問題は生じない。[VERIFIED: pagefolio/file_ops.py:158-159 — `elif op == "duplicate": state["data"] = kwargs["pno"]`（Blob キャプチャなし、単純な整数代入）]

### Undo/Redo 復元失敗時の保護（V190-UNDO-01）

現行 `_undo`/`_redo` は `_restore_state` 呼び出しに一切の例外処理がない:

```python
# pagefolio/file_ops.py:175-197（現状・逐語転記）
def _undo(self):
    if not self._undo_stack:
        self._set_status(self._t("undo_empty"))
        return
    state = self._undo_stack.pop()
    inverse = self._restore_state(state)  # ← ここで例外が出ると state は失われ、
                                            #   doc は部分変更のまま残る
    if inverse.get("data") is not state.get("data"):
        self._dispose_state(state)
    self._push_evicting(self._redo_stack, inverse)
    self._set_status(self._t("undo_done"))
```
[VERIFIED: pagefolio/file_ops.py:175-186 — 上記は逐語転記（`_redo` は188-197行目に同型構造で存在）]

D-13/D-14 の実装パターン（`_undo`/`_redo` に共通適用）:

```python
def _undo(self):
    if not self._undo_stack:
        self._set_status(self._t("undo_empty"))
        return
    state = self._undo_stack.pop()
    try:
        inverse = self._restore_state(state)
    except Exception as e:
        # D-13: pop した state をスタックへ戻す（直接 append ではなく
        # 既存の _push_evicting 経由・D-14 の Blob 規約遵守）
        self._push_evicting(self._undo_stack, state)
        messagebox.showerror(self._t("err_title"), <復元失敗を伝えるメッセージ>.format(e=e))
        return
    if inverse.get("data") is not state.get("data"):
        self._dispose_state(state)
    self._push_evicting(self._redo_stack, inverse)
    self._set_status(self._t("undo_done"))
```

**注意点（Blob ライフサイクル規約との整合・D-14）:**
- `state` を戻すのは `_push_evicting(self._undo_stack, state)` 経由でなければならない。直接 `self._undo_stack.append(state)` すると、maxlen 溢れ時に最古要素が黙って evict され Blob（一時ファイル）がリークする（`_push_evicting` の docstring に明記された既存規約）。[VERIFIED: pagefolio/file_ops.py:102-111]
- `_restore_state` が例外を送出した時点で `self.doc` が部分変更されている可能性がある（`_restore_state` 内の複数ページにまたがる delete/insert ループの途中で失敗した場合）。この状態でユーザーが再度操作を行うと不整合が拡大するため、messagebox はブロッキング（`showerror` は本質的にモーダル）であることが重要（D-13 がトースト・ステータスバーを不採用にした理由と一致）。
- 例外発生時、`state` を popしてまだ `_dispose_state` していないため、Blob は解放せずそのままスタックへ戻す（上記パターンは `_dispose_state` を呼んでいない点に注意）。

### `duplicate`/`merge`/`merge_resize` の4手往復テスト雛形（V190-UNDO-02）

既存 `tests/test_pdf_ops.py` の `TestInsertUndoRedo` クラスに `test_insert_undo_redo_undo_roundtrip`（do→undo→redo→undo の4手往復、2回目の undo で重複が起きないことを検証する回帰テスト）が既に存在する。[VERIFIED: tests/test_pdf_ops.py:758-802 — メソッド全体を確認]このテストと同型のパターンを `TestAllOpsUndoRedoRoundtrip` クラス内の `test_duplicate_roundtrip`（960-986行目）・`test_merge_roundtrip`（988-1011行目）・`test_merge_resize_roundtrip`（1107-1170行目）に対して「4手目の undo」を追加する形で拡張できる。[VERIFIED: tests/test_pdf_ops.py:960-1011, 1107-1170 — いずれも現状 do→undo→redo の3手止まりであることを確認済み（4手目の `app._undo()` 呼び出しが存在しない）]

雛形（insert の4手往復から一般化）:
```python
def test_duplicate_undo_redo_undo_roundtrip(self, sample_pdf_doc):
    app = self._make_fake_app(sample_pdf_doc)
    original_count = len(app.doc)
    before_digests = [_page_digest(app.doc[i]) for i in range(len(app.doc))]

    # do
    app._save_undo("duplicate", pno=1)
    ...（複製実処理）
    # undo (1回目)
    app._undo()
    assert len(app.doc) == original_count
    # redo
    app._redo()
    assert len(app.doc) == original_count + 1
    # undo (2回目) ← 4手目・ここでページ重複が起きないことを検証
    app._undo()
    assert len(app.doc) == original_count
    assert [_page_digest(app.doc[i]) for i in range(len(app.doc))] == before_digests
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Undo デルタの独自シリアライズ | 新しい state 形式・全文スナップショット | 既存の op 別逆デルタ + `_capture_page_blob`/`UndoBlobStore` | `doc.tobytes()` 全廃は BUG-02（V180-D-17）で確定済みの Key Decision。Core Value（大 PDF での Undo 性能）を守るための既存設計を再利用する |
| PDF 暗号化状態の判定 | 保存直後にファイルを開き直して `needs_pass` を確認するランタイムコード | `save_kwargs` からの論理導出（D-03） | 実行時 I/O は大 PDF で遅い。回帰テストでのみ実ファイル検証を行う（D-03 の方針） |
| OCR プロバイダの多重 if 分岐の新規追加 | `ocr_dialog.py` の "off" 分岐をコピペで増やす | `build_provider()` を唯一の生成経路にし、専用例外を全呼び出し元で一律捕捉 | 既に3箇所の重複ハードコード分岐が存在し保守性を損ねている（本 RESEARCH の発見）。これ以上増やさない |
| 複数ファイル挿入のロールバック用一時 Document | 全入力ファイルを一時 Document へ結合してから1回で本体へ反映 | 挿入済みページ数を追跡し `delete_page` で巻き戻す（D-08で確定・不採用案として明記） | 一時 Document 案は大量ページ投入時にメモリピークが乗り Core Value を損なう（D-08 の理由） |

**Key insight:** 本フェーズに「新しい抽象化を追加する」タスクは存在しない。すべてのタスクは「既存の確立されたパターン（op別逆デルタ、build_provider ファクトリ、Apply/Cancel 独立トランザクション）を、例外パス・タイミングの観点で正しく適用し直す」作業である。

## Common Pitfalls

### Pitfall 1: `_overwrite_current_file` の既定化が `_set_password`/`_remove_password` を破壊しない設計にする
**What goes wrong:** `_overwrite_current_file` の関数シグネチャを変更する際、`**save_kwargs` に対して単純に `save_kwargs["encryption"] = fitz.PDF_ENCRYPT_KEEP` と書くと、`_do_set_password`/`_remove_password` が明示的に渡している `encryption=AES_256`/`encryption=NONE` を上書きしてしまう。
**Why it happens:** 「デフォルト値」と「常に上書きする値」を混同する典型的なバグパターン。
**How to avoid:** `save_kwargs.setdefault("encryption", fitz.PDF_ENCRYPT_KEEP)` を使う（`setdefault` はキーが既に存在すれば何もしない）。D-02 の記述「`encryption` 未指定時に既定化」はこの `setdefault` 意味論を指している。
**Warning signs:** `_do_set_password`/`_remove_password` の既存テスト（`tests/test_password.py::TestSetRemovePassword`）が壊れたら、上書き方式で実装してしまっている疑いがある。

### Pitfall 2: `ocr_dialog.py` 内の重複ハードコード分岐を見落として "off" ガードが不完全になる
**What goes wrong:** `build_provider()` にだけ例外を追加して満足すると、`ocr_dialog.py:1065`/`ocr_dialog.py:1506` の独立分岐（`build_provider` を経由しない `LMStudioProvider` 直接構築）が手つかずのまま残る。入口ガード（メニュー disabled 化）が機能する限り実害は出ないが、テストで「ダイアログが既に開いている状態で settings が off に変わるケース」（例: `_apply_llm_settings` 経由）を検証すると、この分岐の存在に気づかず「off なのに LM Studio として動く」挙動が仕様どおりなのかバグなのか判断がつかなくなる。
**Why it happens:** 03/04フェーズ以降で `ocr_dialog.py` に provider 再構築ロジックが複数回コピペされ、`build_provider` の一元化から漏れた（`H-2` コメントが示す通り、tesseract/プラグイン系はもともと `build_provider` へ委譲する意図だったが lmstudio/off はローカル構築のまま残った）。
**How to avoid:** プランに「`ocr_dialog.py:1065`/`1506` の3分岐を把握した上で、少なくとも Common Pitfalls に記載した多層防御構造（入口 disabled 化が主防御）で要件を満たせることを確認するタスク」を含める。統合的に解消するかは Claude's Discretion 範囲外（CONTEXT.md には明記がないため、プランナーが多層防御で十分と判断するか、追加で解消するかを決める）。
**Warning signs:** `_apply_llm_settings`/`_on_run` に対する新規テストで "off" を渡したときに `LMStudioProvider` が生成されてしまう（build_provider の新例外が飛ばない）。

### Pitfall 3: `_do_insert` 巻き戻し時の `delete_page` インデックス計算ミス
**What goes wrong:** `insert_at` から `total` ページ分挿入された状態で巻き戻す際、`for i in range(total): self.doc.delete_page(insert_at + i)` のように「ずれていくインデックス」で削除しようとすると、削除の都度後続ページが前へシフトするため2回目以降のインデックスが対象外のページを指してしまう。
**Why it happens:** `delete_page` は呼ぶたびに以降のページインデックスが1つ前へシフトする（fitz の一般的な挙動）。
**How to avoid:** 同一インデックス `insert_at` を `total` 回削除する（`for _ in range(total): self.doc.delete_page(insert_at)`）。これは既存の `_restore_state` の `insert` op undo 実装（`file_ops.py:391-394`）と同一パターンであり、そのまま踏襲すればよい。
**Warning signs:** 巻き戻し後のページ数は正しいのに、残存ページの内容（digest）が挿入前と一致しない。

### Pitfall 4: Undo/Redo 復元失敗時に `_dispose_state` を呼んでしまい二重解放になる
**What goes wrong:** `_undo`/`_restore_state` の例外処理で「失敗した state をスタックへ戻す」際、誤って `_dispose_state(state)` を先に呼んでから戻すと、state 内の Blob が解放済みになった状態でスタックに残る。次回の undo/redo でこの state を再度消費しようとすると、解放済み Blob の `load()` が不正なデータ（`FileBlob` なら既に `unlink` 済みのファイルパス、`MemBlob` なら空 bytes）を返す。
**Why it happens:** 「失敗したので片付ける」という直感的な発想が、実際には「まだ使える状態として温存する」という要件（D-13: 履歴を失わない）と逆行する。
**How to avoid:** 復元失敗時は `_dispose_state` を呼ばない。state は「まだ消費されていない」ものとして扱い、そのままのBlob参照を保持したままスタックへ戻す。
**Warning signs:** 2回連続で undo が失敗する経路をテストすると、1回目は正しくエラー表示されるが2回目で `FileNotFoundError`（tempfile 削除済み）や空データによる不正な PDF 復元が発生する。

### Pitfall 5: `_has_unsaved_template_changes` の分岐削除で「未選択時」ロジックまで壊す
**What goes wrong:** D-18 は「アクティブテンプレート選択済みの場合」の `prompt_file_exists()` 分岐削除を指示しているが、実装時に `if not self._active_template_name:` ブロック（自由入力の有無だけを見る既存ロジック・sections.py:1173-1174）まで誤って変更すると、`test_no_active_template_warns_on_unsaved_freeform_text`（既存合格テスト・test_provider_ui.py:2249-2297）が壊れる。
**Why it happens:** 関数全体を一括で書き換えようとすると、2つの独立した分岐（未選択時/選択済み時）を混同しやすい。
**How to avoid:** `_has_unsaved_template_changes`（sections.py:1158-1185）の構造を維持し、`if not (prompt_file_exists(...) or prompt_file_exists(...)): return False` の1行（1175-1179行目）だけを削除する最小差分にする。
**Warning signs:** 既存テスト `TestOnTemplateChange`（またはそれに相当するクラス）で「未選択時」系のテストが red になる。

## Code Examples

### 既存の安全な保存パターン（変更不要・参照用）
```python
# Source: pagefolio/file_ops.py:666-673（インクリメンタル保存本体・既に正しい）
try:
    self.doc.save(
        self.filepath, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP
    )
except Exception as e:
    logger.debug("incremental save 失敗、開き直して保存: %s", e)
    self._overwrite_current_file(self.filepath)  # ← ここが D-02 の修正対象
```

### 既存の Blob 生成・解放API（D-14 が乗る土台）
```python
# Source: pagefolio/file_ops.py:102-117
def _push_evicting(self, stack, state):
    """deque へ push する前に、溢れて evict される最古 state を解放する。"""
    if stack.maxlen is not None and len(stack) == stack.maxlen and stack:
        self._dispose_state(stack[0])
    stack.append(state)

def _clear_redo_stack(self):
    """redo スタックを Blob 解放付きでクリアする。"""
    for st in self._redo_stack:
        self._dispose_state(st)
    self._redo_stack.clear()
```

### 既存の Apply ハンドラでの外部ファイル書き込み（D-15〜D-17 が一本化する対象）
```python
# Source: pagefolio/dialogs/llm_config/dialog.py:445-469（_apply メソッド内・既存）
llm_settings["ocr_custom_prompt"] = self.ocr_prompt_text.get("1.0", "end").strip()
llm_settings["ocr_summary_prompt"] = self.ocr_summary_prompt_text.get("1.0", "end").strip()
# V174-2: ファイル連動モード（外部 md ファイルが既に存在する場合）は
# 入力欄の内容をファイルへ書き戻す（画面 ⇄ md の双方向同期）。
# ファイルを使わないユーザーには新規作成しない（settings のみで完結）。
from pagefolio.dialogs.llm_config import (
    prompt_file_exists as _prompt_file_exists,
)
from pagefolio.dialogs.llm_config import (
    save_prompt_file as _save_prompt_file,
)

if _prompt_file_exists(CUSTOM_PROMPT_FILE):
    _save_prompt_file(CUSTOM_PROMPT_FILE, llm_settings["ocr_custom_prompt"])
if _prompt_file_exists(SUMMARY_PROMPT_FILE):
    _save_prompt_file(SUMMARY_PROMPT_FILE, llm_settings["ocr_summary_prompt"])
```
**注記:** この Apply ハンドラ自体は既に「Apply 時に書き込む」という D-15 の方針を満たしている。修正が必要なのは `sections.py:_on_template_change`（`prompt_file_exists(CUSTOM_PROMPT_FILE): save_prompt_file(...)` を切替の都度呼んでいる箇所・1242-1245行目）の**即時書き込みを撤去**することであり、この `_apply` 側のコードは変更不要。

```python
# Source: pagefolio/dialogs/llm_config/sections.py:1240-1245（D-15 で撤去する対象）
# D-07: ファイル連動モードなら選択テンプレートの内容で外部ファイルを
# 上書きする（外部ファイル＝常にアクティブテンプレートのライブ編集内容）
if prompt_file_exists(CUSTOM_PROMPT_FILE):
    save_prompt_file(CUSTOM_PROMPT_FILE, custom_val)
if prompt_file_exists(SUMMARY_PROMPT_FILE):
    save_prompt_file(SUMMARY_PROMPT_FILE, summary_val)
```

## State of the Art

本フェーズは外部エコシステムのバージョンアップ対応ではなく内部バグ修正のため、該当なし。PyMuPDF 1.28.0 の `encryption` 引数の既定動作自体は本バージョン固有の新しい変更ではなく、本セッションで初めて実行時検証を行った（従来は未検証のまま「保存すれば暗号化が保たれるはず」という前提でコードが書かれていた）。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 新設する OCR OFF 専用例外は `pagefolio/ocr_providers/errors.py` に配置し `RuntimeError` を継承するのが既存パターンとの一貫性が高い（Claude's Discretion 項目であり CONTEXT.md 未確定） | Architecture Patterns「例外型設計の precedent」 | 誤っていてもプランナー/実装者が `ocr.py` 配置を選んでも機能面の実害はない（Discretion 範囲内） |
| A2 | `ocr_dialog.py:1065`/`1506` の重複ハードコード分岐は「入口ガード（D-04・既存の `_update_ocr_buttons_state`）が機能する限り到達しない」ため、本フェーズで解消必須ではない | Common Pitfalls Pitfall 2 | 誤っていれば、メニュー/ボタン以外の経路（例: 将来のショートカットキー直接呼び出しやプラグインからの直接呼び出し）で "off" が LM Studio として動作し続ける可能性がある。D-07 の文言を厳密に解釈するなら、プランでこの3分岐の解消も検討すべき |

**Assumptions Log について:** 上記2件以外の記述はすべて `[VERIFIED: <ファイルパス:行番号>]` の形で本セッション中に実ファイルを Read した内容の逐語引用、または `[VERIFIED: ローカル実行環境]` の形で本セッション中に実行したコマンド/スクリプトの出力に基づく。CONTEXT.md の D-01〜D-19 はユーザー確定済みの Locked Decision のためそのまま引用しており `[ASSUMED]` 対象ではない。

## Open Questions (RESOLVED)

> 両項目とも `/gsd-plan-phase 1` の計画時に解決済み。以下の Recommendation は当時の判断材料として残置する。

1. **`ocr_dialog.py` 内の3箇所の重複ハードコード分岐（859/1065/1506行目）を本フェーズで解消するか、多層防御構造のまま残すか**
   - **RESOLVED: 01-02-PLAN.md Task 2-(4) で解消**。1065/1506行目の分岐は「OCR ダイアログを開いたまま LLM 設定でプロバイダを `off` へ切り替える」実在経路で到達可能と判断し、本フェーズで修正＋ガード追加。表示専用の859行目のみコメント記載で据え置き（下記 Assumption A2 は「到達しない」としていたが、D-07 の厳密解釈により覆した）
   - What we know: 入口ガード（D-04・既存の `_update_ocr_buttons_state`）が機能する限り到達しない。`build_provider` の例外化（D-06）だけでバッチ OCR 経路（`_build_provider_once`）は自然にガードされる
   - What's unclear: D-07 の「OCR 実行経路に一切入らない」という文言を、`ocr_dialog.py` 内部の provider 再生成ロジックにまで厳密に適用すべきか
   - Recommendation: プランでは最低限、`_start_ocr`（`ocr.py:541-618`）が `build_provider` の新例外を捕捉して OCR ダイアログを開かせない実装を必須タスクとし、`ocr_dialog.py` 内の3分岐自体の解消は「到達不能であることをコメントで明記する」軽量タスクとして含めるか、スコープ外として次マイルストーンへ委ねるかをプラン作成時に判断する

2. **`_do_insert` の巻き戻し失敗時（D-10）の警告メッセージの具体的な i18n キー文言**
   - **RESOLVED: 01-01-PLAN.md / 01-04-PLAN.md で `warn_rollback_title` / `err_insert_rollback_failed` として文言確定**。残存ページ数と Ctrl+Z で戻せる旨のみを含め、失敗ファイル名は含めない方針でプラン側が確定
   - What we know: 「残存ページ数を明示」「実際の挿入数を反映した Undo state を残す」という要件は確定している
   - What's unclear: 具体的な文言・キー名は CONTEXT.md の Claude's Discretion 項目（「挿入失敗時のエラーメッセージに失敗ファイル名・成功件数をどこまで含めるか」）に委ねられている
   - Recommendation: `pagefolio/lang.py` の既存エラーメッセージパターン（例: `err_save_msg`）に倣い、`{count}` 系のフォーマットプレースホルダを使う簡潔な文言でよい。プラン作成時に確定する

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 実行環境全体 | ✓ | 3.14.6（ローカル確認）[VERIFIED: ローカル実行環境] | — |
| PyMuPDF (fitz) | 全 PDF 操作 | ✓ | 1.28.0（`requirements.txt` 固定・ローカル確認一致）[VERIFIED: ローカル実行環境] | — |
| pytest | 回帰テスト実行 | ✓ | 9.1.1（ローカル確認）[VERIFIED: ローカル実行環境] | — |
| ruff | Lint/Format ゲート | ✓ | 0.15.20（ローカル確認）[VERIFIED: ローカル実行環境] | — |

**Missing dependencies with no fallback:** なし
**Missing dependencies with fallback:** なし（本フェーズは全て既存環境で完結する）

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1（`tests/` 配下・Tk 非依存の `FakeApp`/`_DummyApp` パターンで Mixin を単体検証） |
| Config file | `pyproject.toml`（CLAUDE.md 禁止事項により編集不可。既存設定をそのまま使用） |
| Quick run command | `pytest tests/test_password.py tests/test_pdf_ops.py -x -q`（保存・Undo 系のみ高速確認） |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V190-SAFE-01 | `_overwrite_current_file`/`_save_as` が暗号化 PDF を暗号化維持で保存 | unit（実ファイル `needs_pass` 検証） | `pytest tests/test_password.py -x -q` | ❌ Wave 0（`_save_file`/`_save_as` 経由のケースを追加要。既存は `save_with_password`/`_do_set_password`/`_remove_password` のみカバー） |
| V190-SAFE-02 | `pdf_has_password` の保存後一致・解除は明示操作のみ | unit | `pytest tests/test_password.py -x -q` | ❌ Wave 0（`_save_as`/`_overwrite_current_file` 経由の `pdf_has_password` 導出テストを追加要） |
| V190-SAFE-03 | OCR OFF でバッチ起動不可・`build_provider("off")` が例外 | unit | `pytest tests/test_ocr.py tests/test_provider_ui.py -x -q` | ❌ Wave 0（`build_provider` の off 専用例外テスト・メニュー disabled 化テストを追加要。既存 `test_ocr_provider_default_is_off` は設定デフォルト値の確認のみ） |
| V190-SAFE-04 | 挿入途中失敗でページ数・Undo スタック不変・src クローズ | unit | `pytest tests/test_pdf_ops.py -x -q` | ❌ Wave 0（`_do_insert` の途中失敗シミュレーションテストを新規追加要） |
| V190-SAFE-05 | 複製失敗で既存ページ・Undo スタック不変 | unit | `pytest tests/test_pdf_ops.py -x -q` | ❌ Wave 0（`_duplicate_page` の例外シミュレーションテストを新規追加要） |
| V190-CFG-01 | Cancel で外部ファイル不変 | unit | `pytest tests/test_provider_ui.py -x -q` | ❌ Wave 0（Cancel 経路で `save_prompt_file` が呼ばれないことの検証テストを追加要） |
| V190-CFG-02 | テンプレート編集後の切替で常に未保存確認 | unit | `pytest tests/test_provider_ui.py -x -q` | ❌ Wave 0（選択済みテンプレート編集・非ファイル連動時の未保存確認テストを追加要。既存 `test_no_active_template_warns_on_unsaved_freeform_text` は未選択時のみカバー） |
| V190-UNDO-01 | Undo/Redo 復元失敗で state 保全 | unit | `pytest tests/test_pdf_ops.py -x -q` | ❌ Wave 0（`_restore_state` を monkeypatch で例外送出させるテストを新規追加要） |
| V190-UNDO-02 | duplicate/merge/merge_resize の4手往復 | unit | `pytest tests/test_pdf_ops.py -x -q` | ❌ Wave 0（既存の3手往復テストを4手へ拡張。雛形は `test_insert_undo_redo_undo_roundtrip` 758-802行目） |

### Sampling Rate
- **Per task commit:** `pytest tests/test_password.py tests/test_pdf_ops.py tests/test_ocr.py tests/test_provider_ui.py -x -q`
- **Per wave merge:** `pytest -x -q`（フルスイート・1109件超が目安。V190-QA-01 の Tcl/Tk フレーキー既知事象があるため red が出た場合は単体再実行で切り分ける）
- **Phase gate:** フルスイート green を `/gsd-verify-work` 前提とする

### Wave 0 Gaps
- [ ] `tests/test_password.py` — `_save_file`（インクリメンタル失敗フォールバック経由）・`_save_as` の暗号化維持テストを追加（V190-SAFE-01/02）
- [ ] `tests/test_ocr.py` または `tests/test_provider_ui.py` — `build_provider(settings={"ocr_provider": "off"})` が新例外を送出することの単体テスト（V190-SAFE-03）
- [ ] `tests/test_pdf_ops.py` — `_do_insert` 途中失敗ロールバック・`_duplicate_page` 失敗時の Undo スタック不変テスト（V190-SAFE-04/05）
- [ ] `tests/test_pdf_ops.py` — `_undo`/`_redo` 復元失敗時の state 保全テスト（`_restore_state` を monkeypatch で例外送出）（V190-UNDO-01）
- [ ] `tests/test_pdf_ops.py` — duplicate/merge/merge_resize の4手往復テスト3件追加（V190-UNDO-02）
- [ ] `tests/test_provider_ui.py` — LLM 設定 Cancel での外部ファイル不変テスト・選択済みテンプレート編集時の未保存確認テスト（V190-CFG-01/02）

*(既存テストフレームワーク・fixture パターン（`sample_pdf_doc`/`multi_pdf_files`/`_page_digest`/`_make_fake_app`/`_make_template_dialog`）はすべて流用可能。新規フレームワーク導入は不要)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 本フェーズにユーザー認証機能なし（PDF パスワードは暗号化鍵であり ASVS V2 の対象外） |
| V3 Session Management | no | 該当なし |
| V4 Access Control | no | 該当なし |
| V5 Input Validation | yes | OCR プロバイダ名（`ocr_provider` 設定値）のホワイトリスト検証（既存の `build_provider` 分岐 + プラグイン一覧照合パターンを維持） |
| V6 Cryptography（PageFolio 独自運用: PDF AES-256 暗号化の意図せぬ解除防止） | yes | PyMuPDF の `PDF_ENCRYPT_KEEP`/`PDF_ENCRYPT_AES_256`/`PDF_ENCRYPT_NONE` を明示指定する既存パターンを踏襲。鍵導出・鍵管理はユーザー入力パスワードそのもの（PyMuPDF 内部の AES-256 実装に委譲・自前実装しない） |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 保存操作による意図しない暗号化解除（Information Disclosure） | Information Disclosure | `encryption=fitz.PDF_ENCRYPT_KEEP` の無条件付与（D-01）・関数既定化（D-02）。本 RESEARCH で実行時検証済みの根本原因に対する直接的対策 |
| OCR OFF 設定にもかかわらず外部送信が発生する（Information Disclosure・意図しないデータ送信） | Information Disclosure | `build_provider` の "off" 専用例外による構造的拒否（D-06）+ UI 入口の disabled 化（D-04）の多層防御。クラウド OCR（Claude/Gemini/RunPod）は base64 画像を外部 API へ送信するため、OFF ガードの穴は直接的な情報漏洩リスクになる |
| Undo/Redo 復元失敗時の Document 部分変更状態の放置（Tampering・データ整合性喪失） | Tampering | 復元失敗時に state をスタックへ戻し、ユーザーへブロッキング通知（D-13）。放置すると気づかれないまま保存され、破損 PDF がユーザーの意図しない状態でファイルシステムに残る |

## Sources

### Primary (HIGH confidence)
- `pagefolio/file_ops.py`（本セッションで全文 Read・行番号付き逐語引用） - `_undo`/`_redo`/`_save_undo`/`_apply_inverse`/`_restore_state`/`_overwrite_current_file`/`_save_file`/`_save_as`/`_set_password`/`_remove_password`
- `pagefolio/page_ops.py`（本セッションで全文 Read） - `_duplicate_page`/`_do_insert`/`_do_merge_resize`
- `pagefolio/ocr.py`（本セッションで抜粋 Read：380-620行目） - `build_provider`/`_start_ocr`
- `pagefolio/ocr_dialog.py`（本セッションで抜粋 Read：88-186, 812-1200, 1315-1550, 2407-2460行目） - `_apply_llm_settings`/`_on_run`/`_switch_to_fallback_provider`/`_provider_model_name`
- `pagefolio/app.py`（本セッションで抜粋 Read：280-680行目） - `_open_batch_ocr`/`_update_ocr_buttons_state`/`_apply_llm_settings_live`/`_open_settings`
- `pagefolio/dialogs/batch_ocr.py`（本セッションで抜粋 Read：1-90, 590-680行目） - `_build_provider_once`/`_on_start_batch`
- `pagefolio/dialogs/llm_config/sections.py`（本セッションで抜粋 Read：60-100, 1100-1260行目） - `_has_unsaved_template_changes`/`_on_template_change`
- `pagefolio/dialogs/llm_config/dialog.py`（本セッションで抜粋 Read：1-60, 379-534行目） - `_apply`
- `pagefolio/ocr_providers/errors.py`（本セッションで全文 Read） - 既存例外クラスの precedent
- `pagefolio/undo_store.py`（本セッションで全文 Read） - `MemBlob`/`FileBlob`/`UndoBlobStore`
- `pagefolio/settings.py`（本セッションで抜粋 Read：40-149行目） - `load_prompt_file`/`prompt_file_exists`/`save_prompt_file`/`load_custom_prompt`/`load_summary_prompt`
- `pagefolio/plugins.py`（本セッションで抜粋 Read：1-30行目） - `_BUILTIN_PROVIDER_NAMES`
- `tests/test_password.py`（本セッションで全文 Read） - 既存暗号化テストパターン
- `tests/test_pdf_ops.py`（本セッションで抜粋 Read：1-90, 700-1180行目） - 既存 Undo/Redo 往復テストパターン
- `tests/test_provider_ui.py`（本セッションで抜粋 Read：2230-2300行目） - 既存テンプレート未保存確認テストパターン
- ローカル実行環境（pymupdf 1.28.0）に対する実行時検証スクリプト（本セッションで実行） - `Document.save()`/`Document.tobytes()` の `encryption` 引数既定動作

### Secondary (MEDIUM confidence)
- `.planning/phases/01-safety-rollback/01-CONTEXT.md` - ユーザー確定済み Locked Decisions（D-01〜D-19）
- `.planning/REQUIREMENTS.md` - V190-SAFE/CFG/UNDO 要件定義・Out of Scope 表

### Tertiary (LOW confidence)
- なし（本フェーズは外部情報源への依存が最小限であり、すべての技術的主張をローカルコード/実行時検証で裏付け済み）

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH - 新規依存なし、既存バージョンをローカル実行環境で直接確認
- Architecture: HIGH - 修正対象コードのほぼ全てを本セッションで直接 Read し、根本原因（PyMuPDF 暗号化ストリップ）は実行時テストで再現・検証済み
- Pitfalls: HIGH - 実コードの既存バグ（`src` リーク・部分挿入無警告残留・Undo タイミング誤り・重複ハードコード分岐）をすべて本セッションで特定・行番号付きで記録

**Research date:** 2026-08-10
**Valid until:** 60日（内部リファクタリングのため外部エコシステムの変化リスクは低いが、Phase 2（OpenAI 追加）が本フェーズの `build_provider` 契約に直接依存するため、Phase 2 着手前の再確認を推奨）
