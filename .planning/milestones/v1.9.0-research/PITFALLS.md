# Pitfalls Research — v1.9.0「安全性・整合性の是正 + OpenAI プロバイダ追加」

**Domain:** Python/Tkinter デスクトップ PDF エディタ（PyMuPDF/fitz）への安全性修正・OCRプロバイダ基盤リファクタ・OpenAI プロバイダ追加
**Researched:** 2026-08-10
**Confidence:** HIGH（PyMuPDF 公式ドキュメント・既存コードベース実装・v1.8.0 の実際の回帰事例で裏付け）

すべて `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md`（V190-REV-01〜08）と現行コード
（`pagefolio/file_ops.py`・`pagefolio/page_ops.py`・`pagefolio/ocr.py`・`pagefolio/ocr_providers/`・
`pagefolio/dialogs/llm_config/`）を突合したうえで、「既存システムへの後入れ」に固有の落とし穴のみを扱う。
一般的な PyMuPDF/Tkinter/OpenAI API の初歩的な注意点は割愛している。

> 補足: 本ファイルは gsd-core PITFALLS テンプレート（`research-project/PITFALLS.md`）に準拠しつつ、v1.9.0
> マイルストーン向けの既存プロジェクト固有の落とし穴調査として日本語で記述する（旧 v1.8.0 期リサーチ内容を置き換え）。

---

## Critical Pitfalls

### Pitfall 1: `doc.save(path)` の `encryption` 省略が「暗号化維持」ではなく「暗号化解除」になる

**What goes wrong:**
`pagefolio/file_ops.py` の `_save_as()`（688-709行）は認証済み `self.doc` を `self.doc.save(path)` で保存している。
PyMuPDF の `Document.save()` は `encryption` 引数の既定値が `PDF_ENCRYPT_NONE` であり、`PDF_ENCRYPT_KEEP` を渡さない限り
**暗号化は自動的に維持されない**。実際に既存機能レビューで「入力PDF: `needs_pass == 1` → 保存先PDF: `needs_pass == 0`」が
再現確認されている。「保存」という言葉のつくる直感（元の状態を保つはず）に反して、明示的に指定しない限り安全側に倒れない
API 設計になっている点が本質的な罠。

**Why it happens:**
`_save_file()`（通常上書き保存）では `incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP` が既に指定されているため、
「保存経路は1つ」という思い込みで `_save_as()` にも同じ配慮がされていると錯覚しやすい。しかし `_save_as()` は
別名保存という別経路であり、実装時にコピペ元にした形跡がない。同様に `_overwrite_current_file()`
（インクリメンタル保存失敗時のフォールバック、626-646行）は `self.doc.tobytes(**save_kwargs)` を使うが、
`_save_file()` のフォールバック呼び出し（673行 `self._overwrite_current_file(self.filepath)`）は
`save_kwargs` を一切渡していない。「別名保存」「フォールバック経路」という**通常パスの陰にある副経路**で
暗号化維持の指定が漏れるのが典型パターン。

**How to avoid:**
- `_save_as()` にも `pdf_has_password` が True の場合は `encryption=fitz.PDF_ENCRYPT_KEEP` を渡す（`can_save_incrementally()` が
  False になる別名保存でも `PDF_ENCRYPT_KEEP` は非インクリメンタル保存で有効）。
- `_overwrite_current_file()` の呼び出し元（`_save_file()` のフォールバック）で `pdf_has_password` に応じた
  `save_kwargs={"encryption": fitz.PDF_ENCRYPT_KEEP}` を明示的に渡す。
- 3つの保存経路（通常保存・別名保存・インクリメンタル失敗フォールバック）を**1つの共通ヘルパー**
  （例: `_build_save_kwargs(self)`）に集約し、`pdf_has_password` を単一の入力源として分岐させる。個別に
  `encryption=` を書く実装を増やさない。
- 保存後に `pdf_has_password` を実ファイルの `needs_pass` 相当で検証する（またはフラグを保存経路の分岐結果で
  明示的に更新する）ロジックも合わせて入れる（Pitfall 5 参照）。

**Warning signs:**
- 新しい保存系メソッドを追加するたびに `encryption=` を渡し忘れていないか目視確認する。
- テストで「パスワード付きPDFを開く → 別名保存 → 再度開いてパスワード要求されるか」を経路ごとに網羅していない。
- `grep -n "\.save(" pagefolio/file_ops.py` で `encryption=` を伴わない `save()` 呼び出しが残っていたら要注意。

**Phase to address:**
Phase 1（保存・編集の安全性 = V190-REV-01〜04）。この修正が完了するまで OpenAI プロバイダ追加に進まない
（既存機能レビューの判断基準どおり P0 扱い）。

---

### Pitfall 2: `authenticate()` 後は元のパスワード文字列を取得できない — 再暗号化に必要な状態設計を誤る

**What goes wrong:**
PyMuPDF は `doc.authenticate(password)` で認証に成功しても、その `password` 文字列を `doc` オブジェクトの
どこにも保持しない（`doc.is_encrypted`/`doc.needs_pass` は真偽値のみ）。したがって「暗号化維持保存」を
`PDF_ENCRYPT_KEEP` **ではなく** 独自にパスワードを再指定する方式（`encryption=AES_256, owner_pw=..., user_pw=...`）で
実装しようとすると、認証に使ったパスワード文字列をアプリ側で別途保持しておく必要があり、これを怠ると
「暗号化を維持したいのに再暗号化用のパスワードがどこにもない」という詰みに陥る。

**Why it happens:**
`_authenticate_doc()`（511行付近）はパスワード入力ダイアログの戻り値をローカル変数として使い、
`doc.authenticate()` に渡した後は破棄している可能性が高い。「認証さえ通ればあとは PyMuPDF が覚えている」という
誤解（Claude/Gemini API キーの「一度設定すれば環境変数から引ける」という他機能の感覚の持ち込み）が発生しやすい。

**How to avoid:**
- 再暗号化に**パスワード文字列そのものは不要**であることを設計の前提にする。`PDF_ENCRYPT_KEEP` は
  現在の暗号化オブジェクト（内部の暗号化辞書）をそのまま引き継ぐ方式であり、パスワードの再入力は不要。
  V190-REV-01 の対応方針は `PDF_ENCRYPT_KEEP` で完結させ、パスワード文字列の保持は行わない。
- もし将来「別のパスワードに変更して保存」のような機能を追加する場合のみ、入力時のパスワードを
  セッション変数として明示的に保持する設計が必要になる（現状の「🔒 パスワード」セクションの別名保存フローに準拠）。

**Warning signs:**
- 実装候補として `owner_pw=self._last_password` のような変数を新設しようとしたら、それは `PDF_ENCRYPT_KEEP` で
  代替できないか先に検討する。

**Phase to address:**
Phase 1（V190-REV-01）。設計判断として「`PDF_ENCRYPT_KEEP` 一本化・パスワード再指定方式は不採用」を
Key Decisions に明記しておくとよい。

---

### Pitfall 3: `incremental=True` と暗号化変更は非互換 — フォールバック経路で暗号化引数を渡し忘れる

**What goes wrong:**
`incremental=True` によるインクリメンタル保存は、暗号化方式そのものを変更する保存とは併用できない
（暗号化を「維持」する `PDF_ENCRYPT_KEEP` は可、暗号化の追加・解除・パスワード変更は不可）。
`_save_file()` は `incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP` が成功すればよいが、失敗時は
`except Exception` で握りつぶして `_overwrite_current_file(self.filepath)` にフォールバックする
（671-673行）。このフォールバックは非インクリメンタルな `tobytes()` 再生成だが、現状 `save_kwargs` を渡していないため
`encryption` 指定なしで実行される＝暗号化が解除される。「インクリメンタル失敗時は非インクリメンタルで代替」という
安全網のつもりが、暗号化の観点では安全網になっていない。

**Why it happens:**
インクリメンタル保存の失敗理由（`doc.can_save_incrementally()` が False になるケース: ページ削除・並べ替え・
XRef 構造の大幅変更等）と暗号化維持は本来無関係な概念だが、両方が「保存に失敗したら別の方法で保存する」という
同じ `except` ブロックに同居しているため、暗号化引数の伝播だけが漏れやすい。

**How to avoid:**
- `_overwrite_current_file()` の呼び出し元で必ず `save_kwargs={"encryption": fitz.PDF_ENCRYPT_KEEP}`
  （`pdf_has_password` が True のときのみ）を渡す。
- `doc.can_save_incrementally()` を保存前に確認し、False の場合は最初から非インクリメンタル経路へ分岐する
  （例外を握りつぶして分岐する現状の実装より、事前分岐のほうが「なぜフォールバックしたか」が追跡しやすい）。
- 暗号化変更を伴う保存（パスワード追加・解除）は既存どおり `incremental=False` の専用メソッド
  （`save_with_password`/`save_without_password`）に閉じ込め、通常保存経路とは混ぜない設計を崩さない。

**Warning signs:**
- `except Exception` で拾ったあとに呼ぶ保存メソッドの引数リストが、元の保存呼び出しの引数リストと
  異なっていないか（暗号化系引数が抜け落ちていないか）を diff で確認する。

**Phase to address:**
Phase 1（V190-REV-01）。回帰テストは「暗号化PDFで、意図的にインクリメンタル保存を失敗させ、フォールバック後も
暗号化が維持されること」を検証する（`can_save_incrementally()` を monkeypatch して False を返させる等）。

---

### Pitfall 4: `permissions` 省略時の既定値を確認せずに再暗号化する

**What goes wrong:**
`save_with_password()`（21-28行）は `encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password`
のみを指定し `permissions` を渡していない。PyMuPDF は `permissions` 省略時に既定の権限セットを付与するが、
その既定値がアプリの意図（例: 印刷は許可するが編集は禁止したい等）と一致するとは限らない。今回のスコープでは
既存の「パスワード付与」機能自体は変更対象ではないが、V190-REV-01 の対応で保存経路を共通ヘルパーへ統合する際に
`permissions` を一緒に触ってしまい、既存の許可されていた挙動（例:印刷可能）を意図せず変えてしまうリスクがある。

**Why it happens:**
暗号化まわりの引数を1箇所にまとめるリファクタ（Pitfall 1 の推奨策）を行う際、`owner_pw`/`user_pw`/`encryption`
だけをまとめて `permissions` の扱いを見落としやすい。`PDF_ENCRYPT_KEEP` の経路では `permissions` は無関係だが、
`save_with_password()` のような新規暗号化経路では関係してくるため、両者を同じヘルパーに混在させると事故が起きる。

**How to avoid:**
- `PDF_ENCRYPT_KEEP`（維持）と `PDF_ENCRYPT_AES_256`（新規暗号化）を**同じ共通ヘルパーに混ぜない**。
  前者は「引数追加のみ」、後者は「permissions を含む既存の意図的な設計」を保つ。
  Pitfall 1 の共通化は「維持系3経路」のみを対象にし、パスワード付与/解除の既存2経路には触れない。
- `permissions` を明示指定していない現状を変更しない場合は、その理由（既定値で問題ない）をコードコメントに残す。

**Warning signs:**
- リファクタ後に既存のパスワード付与テスト（`tests/test_password.py` の `test_do_set_password_writes_encrypted` 等）が
  権限まわりで暗黙に緩くなっていないか（テスト自体が権限を検証していない場合は追加を検討）。

**Phase to address:**
Phase 1（V190-REV-01）。リファクタ範囲を「暗号化維持のみ」に限定するスコープ判断として計画段階で明記する。

---

### Pitfall 5: `pdf_has_password` フラグと実ファイルの不整合（保存後に更新されない）

**What goes wrong:**
既存機能レビューが指摘するとおり、保存後も `self.pdf_has_password` は更新されない。暗号化維持が正しく実装できても、
UI 側のフラグが古いままだと「🔒 パスワード」セクションの表示（解除ボタンの活性/非活性、警告表示等）が
実ファイルの状態と食い違う。これは Pitfall 1〜4 を修正しても**別途対応しないと解消しない**独立した不整合源。

**Why it happens:**
`pdf_has_password` は「開いたとき」（504-506行、552行、586行）と「パスワード付与/解除操作」（724行、813行、840行）の
タイミングでのみ更新されており、「通常の保存」はこのフラグに影響しないという前提で設計されている。今回、通常保存で
暗号化維持を扱うようになると、この前提が崩れているのにフラグ更新ロジックの追加が漏れやすい。

**How to avoid:**
- 保存成功時、`pdf_has_password` を変更していない（暗号化維持のみ）ことを明示的にコード上でも保つ
  （＝そもそも変更不要なはずだが、Pitfall 1-3 の修正がフラグの意味と整合しているかテストで確認する）。
- 保存失敗・部分的な暗号化解除が発生した場合にフラグが実態と乖離しないよう、保存処理の成功パスでのみ
  フラグ確定するのではなく、必要なら保存直後に `fitz.open(path).needs_pass` で実ファイルを検証する
  回帰テストを追加する（本番コードに検証を常設するかはコスト対効果で判断）。

**Warning signs:**
- 「🔒 パスワード」セクションのUIが、暗号化PDFを保存した直後に解除ボタンの活性状態が変わらないか手動確認する
  （human-verify 項目候補）。

**Phase to address:**
Phase 1（V190-REV-01）。受け入れ条件「失敗時に Document・Undo履歴・外部ファイルが操作前の状態へ戻る」に加えて
「成功時も UI 状態（`pdf_has_password`）が実ファイルと一致する」を明記する。

---

### Pitfall 6: `_save_undo` を「実処理後」へ移すと `current_page`/`selected_pages` のスナップショットが後ろにずれる

**What goes wrong:**
V190-REV-04 は「`_save_undo` を実処理より前ではなく成功後に呼ぶ」ことを推奨しているが、これを素朴に
「`_save_undo()` の呼び出し行を try ブロックの後ろに移動するだけ」で実装すると別のバグを生む。
`_save_undo()`（132-139行）は `state["current_page"] = self.current_page` と
`state["selected_pages"] = set(self.selected_pages)` を**呼び出し時点の値**でキャプチャする。これは
「操作前の状態」を Undo で復元するために必要な値であり、操作成功後（ページ番号や選択状態が既に変わった後）に
呼ぶと、Undo 実行時に「操作前ではなく操作後のカーソル位置・選択状態」に復元されてしまう回帰を生む。

**Why it happens:**
V190-REV-04 の問題自体は「実処理より先に Undo 状態を積むと、実処理が失敗したときに不正な Undo エントリが残る」
という別の懸念（安全性）に起因するが、対応策として「後ろに移動する」だけを機械的に適用すると、
今度は「Undo に必要な "操作前スナップショット" が取れなくなる」という**別の不変条件を壊す**。
この2つの要求（安全性＝失敗時に汚れたエントリを残さない／正確性＝操作前状態をキャプチャする）は
単純な行移動では両立しない。

**How to avoid:**
- 既存の `_do_insert()`（756-790行）が使っている「先に `_save_undo()` を呼んで**仮の**エントリを積み、
  成功後に `self._undo_stack[-1]["data"][...]` を書き換えて確定し、失敗時は `self._undo_stack.pop()` で
  仮エントリを破棄する」という**既に確立されたパターン**を `_duplicate_page()` にも適用する。これなら
  `current_page`/`selected_pages` は操作前の正しい値のまま、実処理の成否だけを Undo データに反映できる。
- 「成功後に初めて `_save_undo()` を呼ぶ」方式を採る場合は、`_save_undo()` 呼び出しの**前に**
  操作前の `current_page`/`selected_pages` をローカル変数へ退避しておき、`_save_undo()` に明示的に渡せる
  ようシグネチャを拡張する（現状は `self.current_page` を直接参照するため退避が必須）。
- `page_edit`（黒塗り・モザイク）等、他の "先に `_save_undo` を呼ぶ" 系オペレーションへ波及させる場合も
  同じ注意が必要。全操作を一律に「後ろへ移動」するのではなく、操作ごとに「途中で選択/カーソルが変わるか」を
  確認してから移動可否を判断する。

**Warning signs:**
- 修正後に「複製 → Undo」で `current_page` が複製前のページに戻るか（複製後のページのままにならないか）を
  テストで確認する。既存の 4手往復テスト（Pitfall 8）に `current_page`/`selected_pages` の検証を含める。

**Phase to address:**
Phase 1（V190-REV-04）。実装時は「仮エントリ確定パターン」（`_do_insert` 方式）を第一候補として計画する。

---

### Pitfall 7: Undo Blob の二重 dispose / dispose 漏れ（confirm-after-success パターンへの書き換え時）

**What goes wrong:**
`_duplicate_page()` の Undo タイミングを Pitfall 6 のパターンで修正する際、`duplicate` op は
`_capture_page_blob()` を呼ばない単純な整数 (`pno`) データのため Blob 問題は発生しないが、他の
「実処理前に Blob をキャプチャする」op（`delete`・`page_edit`・`merge_resize` 等）に同種のタイミング変更を
将来横展開する場合は要注意。`_capture_page_blob()` で取得した Blob は `_dispose_state()`（`_undo`/`_redo`
消費時・`_push_evicting` の evict 時・`_clear_redo_stack`/`_clear_undo_stacks`）でのみ解放される契約になっている。
「実処理成功後に確定」パターンで、失敗時に仮エントリを `pop()` するだけでは、**その仮エントリが既に
`_capture_page_blob()` で確保していた Blob（tempfile）が解放されないままリークする**。逆に、確定後に
`_apply_inverse()` 等が同じ Blob を再度参照してしまうと `_undo`/`_redo` の identity 比較（183行・194行の
`if inverse.get("data") is not state.get("data")`）が崩れて二重 dispose になり得る。

**Why it happens:**
`CLAUDE.md` に明記されている「スタックへの直接 append/clear は禁止（Blob がリークする）」という制約は、
「スタックの外」で一時的に保持される仮エントリ（`_undo_stack[-1]` に積んでから `pop()` する `_do_insert` の
パターン）には直接は当てはまらないように見えるが、`pop()` で捨てる仮エントリが Blob を保持していた場合は
Blob dispose 契約の外側に出てしまう。「スタック操作」だけを注視し、「スタックに一瞬でも積まれた state が
Blob を保持していないか」を見落とすと発生する。

**How to avoid:**
- `duplicate`（Blob 不使用）以外の op へこの「後から確定」パターンを横展開する際は、仮エントリを
  `pop()` で捨てる箇所に必ず `_dispose_state(popped_state)` を呼ぶ（`_do_insert()` の失敗時分岐
  784-787行に、`insert` op は Blob を持たないため dispose が省略されている点をそのまま流用しない）。
- Blob を持つ op（`delete`・`page_edit`・`merge_resize`）に対して「先に確定量ゼロで積む → 後で確定する」
  設計を新設する場合は、確定前に例外が起きるケース・確定後に失敗するケースの両方で「誰が Blob を解放するか」を
  明文化してからコードを書く（コードコメントまたは PLAN.md の受け入れ条件に明記）。

**Warning signs:**
- Blob を使う op のタイミング変更後、Windows AV スキャン衝突安全網の既存テスト（v1.8.0 で追加済み）や
  一時ファイル数を計測する回帰テストが増減しないか確認する。
- 長時間の操作往復（数百回の Undo/Redo）でテンポラリディレクトリのファイル数が単調増加しないか確認する。

**Phase to address:**
Phase 1（V190-REV-04）だが、影響範囲は Phase 3（Undo/Redo 回帰強化・V190-REV-07 の4手往復テスト水平展開）にも
またがる。Phase 3 計画時に「Blob を伴う op へのタイミング変更は本マイルストーンでは対象外」と明示的にスコープ
判断するか、対象に含めるなら本 Pitfall の dispose 契約を PLAN.md に明記する。

---

### Pitfall 8: `_undo`/`_redo` の `pop()` → `_restore_state()` 間で例外が起きると履歴が消える

**What goes wrong:**
`_undo()`（175-186行）と `_redo()`（188-197行）は `state = self._undo_stack.pop()` で先にスタックから
取り出してから `self._restore_state(state)` を呼ぶ。`_restore_state()` 内部（`fitz` の `delete_page`/
`insert_pdf`/`set_cropbox`/`doc.select()` 等）で例外が発生すると、`pop()` 済みの `state` はどこにも
戻されずに失われる。さらに `_restore_state()` は複数ページに対してループで `delete_page`/`insert_pdf` を
呼ぶ op（`delete`・`insert_undo`・`merge` 等）があり、ループの途中で例外が起きると**一部のページだけ
処理された中途半端な Document 状態**が残る。この状態で「履歴を戻す」ことすらできない。

**Why it happens:**
「Undo/Redo は滅多に失敗しない」という前提でコードが書かれており、`pop()` → 適用という順序が
「適用が必ず成功する」ことを暗黙の前提にしている。対称デルタ設計（BUG-02 対応）によって「Undo は
本質的に安全」という認識が強化された結果、例外パスの検討が漏れている。

**How to avoid:**
- `state = stack.pop()` を `state = stack[-1]`（peek）に変え、`_restore_state()` が正常終了してから
  `stack.pop()` で確定的に取り除く（例外時は自動的にスタックに残る）方式に変更する。
- `_restore_state()` 内のループ処理（`delete`/`insert_undo`/`merge`/`page_edit` 等の複数ページ処理）は、
  「1ページ目で例外が起きたら2ページ目以降は実行しない」という現状の素朴な逐次実行のままだと、部分適用の
  検知ができない。最低限、例外発生時に「何ページ目まで処理できたか」をログへ残し、ユーザーに
  「Document が不整合な可能性がある。保存せず再度開き直すことを推奨」という警告を出す（完全なロールバックは
  この milestone のスコープ外でも、検知と警告は入れられる）。
- V190-REV-07 の受け入れ条件どおり `duplicate`/`merge`/`merge_resize` の4手往復テスト（do→undo→redo→undo）に
  加え、「`_restore_state()` の途中で例外を注入したときスタックが変化しないこと」を検証するフォールト
  インジェクションテストを追加する。

**Warning signs:**
- Undo/Redo 実行中に例外ダイアログが出た直後、もう一度 Undo/Redo を押すとアプリがクラッシュする、または
  無関係なページが削除される（V190-REV-07 の懸念どおり）。
- `_undo_stack`/`_redo_stack` の要素数が、操作回数と食い違う（テストで `len(app._undo_stack)` を
  例外注入前後で比較する）。

**Phase to address:**
Phase 3（Undo/Redo 回帰強化・V190-REV-07）。peek→確定 pop への変更は Phase 1（V190-REV-04）の
「後から確定」パターンとも構造的に類似するため、両フェーズで実装方針を揃える（同じヘルパーで対応できないか
Phase 1 計画時に検討する価値がある）。

---

### Pitfall 9: 複数ファイル挿入のトランザクション化 — `insert_pdf` 例外時に挿入元 Document が `finally` で閉じられない

**What goes wrong:**
`_do_insert()`（756-790行）は複数ファイルを順番に `self.doc.insert_pdf(src, start_at=pos)` で挿入するが、
`src = self._open_path_as_pdf(path)` で開いた挿入元 `Document` は `src.close()` がループ内の
正常系（767行）にしか置かれておらず、`insert_pdf()` 自体が例外を投げた場合は `close()` されずに
リークする（`fitz.Document` オブジェクトは C 側リソースを保持しており、ガベージコレクションに任せると
Windows でファイルハンドルが残留し得る）。加えて、2件目のファイルで失敗した場合、1件目で挿入済みの
ページはロールバックされず、`self.doc` に**部分的な挿入結果が残ったまま** Undo エントリだけが
（V190-REV-04 と同型の問題として）`num=0` で破棄される（786-787行のコメントが示唆するとおり、現状は
「不完全な insert state を破棄する」対応のみで、**挿入済みページ自体は消えない**）。

**Why it happens:**
「Undo state の整合性」と「Document 自体の整合性（挿入済みページ）」は別の問題であり、V190-REV-03 の
現状パッチ（786-787行）は前者のみに対応している。トランザクション化は「全ファイル成功して初めて本体へ
反映する」という要求だが、素朴な実装だと「Undo だけ巻き戻す」対応で満足してしまい、Document 側の
部分挿入が残ったままになりがち。

**How to avoid:**
- 推奨対応どおり「一時 `Document`（`fitz.open()` の空文書）に全入力ファイルを `insert_pdf` で積み上げ、
  全件成功後に一括で本体 `self.doc` へ `insert_pdf` する」方式にする。これなら本体への変更は
  「全成功時の1回の `insert_pdf`」のみになり、途中失敗時は本体が一切変更されない（ロールバック不要になる）。
- 各ファイルの `src` は必ず `try/finally`（または `with` 相当のスコープ管理）で `close()` する。
  一時 `Document` 方式にする場合も、一時 `Document` 自体の `close()` を成功・失敗どちらの経路でも保証する。
- 一時 `Document` の構築中に失敗した場合のエラーメッセージには「何ファイル目で失敗したか」を含め、
  ユーザーが原因ファイルを特定しやすくする（UX面でも V190-REV-03 の意図に沿う）。

**Warning signs:**
- 2件目のファイルが破損 PDF 等で失敗するテストを追加し、（a）`len(self.doc)` が処理前と一致すること、
  （b）`self._undo_stack` の長さが処理前と一致すること、（c）開いたはずの `src` Document がクローズされて
  一時ファイルハンドルが残らないこと、の3点を検証する。
- Windows で大量のファイル挿入操作を繰り返した後、`tasklist`/ハンドルビューア等でファイルハンドルリークが
  ないか確認する（人手確認候補）。

**Phase to address:**
Phase 1（V190-REV-03）。一時 `Document` 方式を採用する場合、`_save_undo("insert", ...)` の呼び出しタイミングも
「一時 Document の構築完了後・本体反映の直前」に揃えることで Pitfall 6 のパターンと自然に整合する。

---

### Pitfall 10: `off` を「プロバイダ生成不可」にする変更が、既定値 `off` に依存する既存経路を壊す

**What goes wrong:**
`build_provider()`（`pagefolio/ocr.py` 414-441行）は現状 `name in ("lmstudio", "", "off")` を LM Studio
として扱っている（コメントに「"off" は Phase 5 で UI 化。Phase 4 では LM Studio として動作させ後方互換を
維持」とあり、これは v1.4.0 期の暫定実装が今もそのまま残っている）。V190-REV-02 の対応でこれを
「`off` はプロバイダ生成不可（呼び出し元でガードして例外/None を返す）」に変更すると、`off` を
経由して間接的に動いていた以下のような経路が**サイレントに壊れる、または逆に過剰にブロックされる**リスクがある。

1. **バッチOCR起動時ガード漏れ**（V190-REV-02 の主眼）: `pagefolio/dialogs/batch_ocr.py` の実行開始
   コード（627-650行付近）が `build_provider()` の戻り値を直接使っていた場合、`off` で例外/None が
   返るよう変更しても、呼び出し元でその例外/None を捕捉して「実行しない」に倒す処理が無ければ、
   単に別の未処理例外（`AttributeError` 等）としてクラッシュするだけになる。
2. **既定値 `settings.get("ocr_provider", "off")` を読む複数箇所**: `app.py`（340行 `is_ocr_on`）・
   `ocr.py`（431行 `build_provider` 内・495行/514行/543行/600行/962行/1032行/1041行）など、
   `"off"` という文字列リテラルへの `==`/`!=` 比較が広範囲に散在している。`off` の扱いを変える際に
   これら**すべての比較箇所が新しい意味論と一致しているか**を1箇所ずつ確認しないと、「OCRボタンは
   無効化されているのに `build_provider` 経由の別の呼び出し（プラグイン登録プロバイダのフォールバック
   候補一覧、送信先確認ダイアログのプレビュー等）だけは `off` を素通りする」といった**部分的な修正漏れ**が
   起きやすい。
3. **プラグイン登録プロバイダとの整合**: `PluginManager.register_ocr_provider` で追加されたサードパーティ
   プロバイダが `settings.get("ocr_provider")` に独自の名前を設定するケースでは、`off` 判定のロジックを
   `build_provider()` の先頭で一括ガードする形にしないと、プラグイン経路だけ `off` チェックをすり抜ける
   （V190-REV-02 の「OCR OFF は通常OCR・バッチOCR・プラグイン経路の全実行経路で同じ意味にする」という
   要求に反する）。
4. **既存テストの `ocr_provider` 未指定ケース**: 既存テストが `settings = {}`（`ocr_provider` キー未設定）で
   `build_provider()` を呼び、LM Studio として動くことを前提にしている場合、`""` と `"off"` を
   異なる扱いにする（`""` は後方互換で LM Studio のまま・`"off"` のみ拒否、等）判断をしないと大量のテストが
   落ちる可能性がある。

**Why it happens:**
`off` が「UIの既定値」であると同時に「LM Studio のエイリアス（後方互換）」でもあるという**二重の意味**を
1つの文字列リテラルが背負っている。これは v1.4.0 の暫定実装がそのまま温存された技術的負債（V190-REV-08 の
「プロバイダ情報の分散」とも根が同じ）であり、今回初めてこの二重の意味を分離しようとするために、
分離漏れが全箇所で起こりうる。

**How to avoid:**
- `build_provider()` を変更する前に、`grep -rn '"off"' pagefolio/` で全参照箇所を洗い出し、
  「UIの既定値としての off」と「LM Studio 後方互換としての off（空文字含む）」のどちらの意味で
  使われているかを1箇所ずつ分類する（V190-REV-08 のメタデータ一元化と合わせて実施すると効率的）。
- `build_provider()` は `off` を渡されたら明示的な例外（例: `OCRProviderOffError`）を送出し、
  呼び出し元（通常OCRボタン・バッチOCR起動時・バッチOCR実行開始時・プラグインフォールバック候補列挙）
  **すべて**でこの例外を捕捉して「実行しない」旨をユーザーに提示する。「戻り値が None」より
  「専用例外」の方が、捕捉漏れがあった場合に未処理例外としてクラッシュし、テストで検知しやすい
  （サイレントに何も起きない、より安全）。
- 空文字列 `""`（未設定）と `"off"`（明示的にOFF）を同じ扱いにするか分けるかを最初に決め、
  `PROVIDER_ENV_KEYS`/レジストリ側のメタデータに明記する（V190-REV-08 と合わせて設計）。
- 既存テスト（`tests/test_provider_ui.py` 等）で `ocr_provider` 未指定・`"off"` 明示指定の両方を
  網羅する回帰テストを先に書いてから実装に着手する（テストファースト）。

**Warning signs:**
- 実装後、`pytest -k ocr_provider` 相当のフィルタで既存テストの失敗件数が想定外に多い場合、`off` の
  意味変更が想定より広範囲に影響している兆候。
- バッチOCRダイアログを `ocr_provider="off"` の状態で開けてしまう（そもそもダイアログ表示自体を
  ブロックすべきか、実行開始時のみブロックすべきかは要件確認が必要）。

**Phase to address:**
Phase 1（V190-REV-02）だが、Phase 4（OCRプロバイダ基盤整理・V190-REV-08）と密接に関連するため、
`off` の意味論の再定義は V190-REV-08 のメタデータ一元化と同時に設計し、実装のみ Phase 1 で先行させる
（既存機能レビューの推奨反映順どおり P1 は P2 より先だが、設計の一貫性は崩さない）。

---

### Pitfall 11: 外部プロンプトファイルへの書き込みが「テンプレート切替時」と「Apply時」の二重トリガーになっている

**What goes wrong:**
`pagefolio/dialogs/llm_config/sections.py` の `_on_template_change()`（1207-1246行）は、テンプレートを
切り替えた**その瞬間**に `save_prompt_file(CUSTOM_PROMPT_FILE, custom_val)` /
`save_prompt_file(SUMMARY_PROMPT_FILE, summary_val)` を呼んで外部ファイルへ書き込む（1242-1245行、
コード内コメント「D-07: ファイル連動モードなら選択テンプレートの内容で外部ファイルを上書きする」）。
一方 `pagefolio/dialogs/llm_config/dialog.py` の `_apply()`（459-469行）でも同じ2ファイルへの書き込みを
**Apply時にも再度**行っている。つまり書き込みトリガーが2箇所あり、「Apply時へ一本化する」（V190-REV-05）
という対応方針を素朴に「`_apply()` 側だけ残して `_on_template_change()` 側を消す」とすると、今度は
**ダイアログを開いたまま複数回テンプレートを切り替えて都度プレビューしたい**という既存の「ライブ連動」
UX（D-07 のコメントが示す設計意図）を壊してしまう。逆に両方残したまま Cancel 時の復元だけ足すと、
「Apply時へ一本化」という要求そのものを満たさない。

**Why it happens:**
V190-REV-05 の推奨対応は「外部ファイルへの書き込みをApply時へ一本化する」「ライブ連動を維持する場合は、
ダイアログ開始時の内容を保持し、Cancel時に復元する」の**2つの選択肢**を併記しており、どちらを採るかで
実装がまったく異なる。この二択を意識せず「とりあえず Cancel 時に何か復元処理を足す」実装をすると、
一本化ともライブ復元とも言えない中途半端な状態（例: Cancel時に「Apply前の値」ではなく「ダイアログを
開く前の値」に戻すべきところを取り違える）になりやすい。

**How to avoid:**
- 実装前にどちらの方式を採るか PLAN.md で明記する。**ライブ連動を維持する（D-07 の意図を尊重する）**なら:
  1. ダイアログの `__init__` 時点で `CUSTOM_PROMPT_FILE`/`SUMMARY_PROMPT_FILE` の**元の内容**（存在しなければ
     None）をインスタンス変数（例: `self._orig_custom_prompt_content`）として保持する。
  2. `_on_template_change()` の書き込みはそのまま維持する（ライブプレビューのため）。
  3. `destroy()`（Cancel経路含む）で、`_apply()` が呼ばれていない場合に限り元の内容へ書き戻す
     （Apply 済みかどうかのフラグ管理が必要 — 例えば `self._applied = True` を `_apply()` の最後に立てる）。
- **一本化する**なら: `_on_template_change()` からファイル書き込みを削除し、入力欄（Tk Text ウィジェット）
  への反映のみ行う。外部ファイルへの反映は `_apply()` のみで行う。この場合、テンプレート切替の
  ライブプレビュー（外部エディタで開いた md ファイルが即座に変わる体験）は失われる点を仕様変更として
  ユーザー/PROJECT.md に明記する。
- どちらの方式でも、`destroy()` が「Apply経由」と「✕ボタン/Escキー等のCancel相当」の両方から呼ばれる
  現状の実装（149-151行 `command=self.destroy`）を踏まえ、「Apply後にdestroyが呼ばれても復元処理が
  誤って走らない」ようにフラグ管理を確実にする。

**Warning signs:**
- Cancel後、次にダイアログを開いたときに前回セッションの「切替はしたがApplyしなかった」内容が
  入力欄に残っていないか（`current_settings` のディープコピーが正しく破棄されているか）を確認する。
- 外部エディタで `ocr_custom_prompt.md` を開いた状態でテンプレート切替→Cancelを行い、ファイルの
  タイムスタンプ/内容が変わらない（一本化方式）か、Apply前の値に戻る（ライブ復元方式）かをどちらか
  一方に統一して確認する。

**Phase to address:**
Phase 2（設定UIの整合性・V190-REV-05）。実装方式の選択は `/gsd-discuss-phase` または PLAN.md 作成時に
確定させ、曖昧なまま実装に入らない。

---

### Pitfall 12: 大規模メタデータ一元化リファクタで参照面を取りこぼす／monkeypatch 対象の名前空間が断絶する（v1.8.0 で実際に発生済み）

**What goes wrong:**
V190-REV-08 は OCR プロバイダのメタデータ（表示名・クラウド種別・環境変数・既定モデル・送信先・
フォールバック可否）を7ファイルにまたがる重複から一元化する大規模リファクタである。既存機能レビューが
挙げる変更面だけでも `registry.py`・`ocr.py`（ファクトリ/クラウド判定）・`llm_config/sections.py`
（プロバイダ・フォールバック一覧）・`llm_config/dialog.py`（設定収集）・`ocr_dialog.py`（表示名/モデル/
送信先/APIキー処理）・`batch_ocr.py`（クラウド判定/コスト確認/送信先）・`lang.py`（表示文言）の7ファイル。
このクラスのリファクタで実際に起きるのは（a）grep漏れによる参照面の一部だけの書き換え、
（b）テストが `monkeypatch` している対象のモジュールパスが、リファクタ後の re-export 経由と実体モジュール
経由でずれてパッチが効かなくなる、の2種類。**後者は本プロジェクトで v1.8.0 Phase 1 の
`llm_config.py` → `llm_config/` サブパッケージ分割時に実際に発生し**、`dialog.py` の `_apply()` に
残っているコメント（454-458行）が「分割前は同一モジュール内の名前空間で monkeypatch が効いていたため、
分割後も `pagefolio.dialogs.llm_config`（パッケージ）経由の遅延 import で同じ差し替え可能性を保つ」という
形で対応した記録が残っている。今回のメタデータ一元化でも同種の断絶が高確率で再発する。

**Why it happens:**
Python の `monkeypatch.setattr(module, "func_name", fake)` は「参照している名前空間」を差し替える。
モジュール分割・関数の移動を行うと、ある呼び出し元が `from pagefolio.ocr_providers.registry import X` の
ように**直接 import**していた場合、テストが `monkeypatch.setattr("pagefolio.dialogs.llm_config.sections.X", fake)`
のように**呼び出し元モジュールの名前空間**をパッチしていると、`X` の実体がどこに定義されているかに関わらず
その名前空間経由の呼び出しだけが差し替わる。リファクタで「呼び出し元が直接 import する経路」から
「re-export 経由・遅延 import 経由」に変わると、テストが元々パッチしていた名前空間に実体が存在しなくなり、
**パッチが静かに効かなくなる**（テストがパスしてしまうため気づきにくい・逆に本番コードのバグをテストが
検出できなくなる最悪パターン）。

**How to avoid:**
- リファクタ着手前に `grep -rn "ocr_provider\|provider_name\|display_name\|cloud" pagefolio/ tests/` 相当で
  現状のプロバイダメタデータ参照箇所を一覧化し、**各参照が「値の読み取り」か「関数呼び出し」か**を分類する
  （値のインポートは名前空間問題が起きにくいが、関数の import は monkeypatch 対象になりやすい）。
- 新設するメタデータレジストリからの参照は、既存の `registry.py` 参照パターン（`from pagefolio.ocr_providers.registry
  import env_vars_for` のような直接 import）を踏襲し、`dialog.py` のコメントが示す「遅延 import 経由での
  差し替え可能性維持」パターンを新レジストリにも適用する。
- リファクタ後、既存の全テストを実行するだけでなく、**意図的に本番コードへバグを1つ注入してテストが
  落ちることを確認する**（ミューテーションテスト的な検証）。特に APIキー未設定時のエラーメッセージ・
  送信先確認ダイアログの表示内容など、`monkeypatch` に依存したテストが多い箇所は重点的に確認する。
- `registry.py` の独立性制約（標準ライブラリのみ・内部モジュール非import）は、新設する非機密メタデータ
  レジストリにも同様の制約を課すか、または明示的に「このレジストリは内部モジュールに依存してよい」と
  区別する。2つのレジストリ（機密キー用・非機密メタデータ用）の依存方向を混同すると、後者を経由して
  循環importが再発するリスクがある。

**Warning signs:**
- リファクタ後、`pytest -q` は全件パスするが、意図的に不正な値を返すよう本番コードを一時的に壊しても
  テストが依然パスする（＝パッチが効いていない兆候）。
- IDE/`ruff` の未使用import警告が、リファクタ後の re-export モジュールで大量に出る（参照面が整理しきれて
  いない兆候）。

**Phase to address:**
Phase 4（OCRプロバイダ基盤整理・V190-REV-08）。着手前に v1.8.0 Phase 1 の `dialog.py` 454-458行の
コメントと当時のコミット（`_SENSITIVE_KEYS` 中央レジストリ化・V180-ROBUST-02）を参照し、同じ轍を踏まない
ことを計画レビュー時のチェック項目に加える。

---

### Pitfall 13: Python 3.14 + Tkinter の GUI テスト環境修復が「テスト環境だけ」の問題ではない

**What goes wrong:**
既存機能レビューでは `pytest` 実行時に24件が「アサーション失敗ではなくセットアップエラー」
（`_tkinter.TclError` で Tkinter 単体起動が失敗、`init.tcl` を読み込めない）で落ちている。この種の問題を
「`TCL_LIBRARY` 環境変数をどこかに設定すれば直る」と即断してグローバルに `os.environ["TCL_LIBRARY"] = ...`
のようなハードコードをテストコードや `conftest.py` に埋め込むと、（a）開発者のマシンごとに Python/Tcl の
インストールパスが異なるため**特定の環境専用の決め打ちパス**になり他の開発者・CI環境で再度壊れる、
（b）配布用 PyInstaller ビルド（`frozen` 実行時）が独自の Tcl/Tk バンドルを持つ場合、開発時の
`TCL_LIBRARY` 設定が本番ビルドの探索ロジックと衝突し、**開発環境のテストは直るが配布EXEでは逆に
壊れる**、という副作用を生みやすい。

**Why it happens:**
Python 3.14 は Tcl/Tk のバンドル方式やレジストリ参照の挙動が過去バージョンと変わっている場合があり、
「バージョンを跨いだ環境問題」を「コードの中で環境変数を上書きして帳尻を合わせる」対症療法で解決しようとすると、
根本原因（インストールされている Tcl/Tk のバージョン不整合、PATH解決順序、`_tkinter` モジュールが
参照する tcl86t.dll/tk86t.dll 等のバイナリ探索）に触れないまま「動いた」ように見えてしまう。

**How to avoid:**
- 修正は「テストコードから `TCL_LIBRARY` を強制上書きする」のではなく、**Python/Tcl/Tk のインストール自体を
  修復する**（Python 3.14.6 の再インストール、`tcl`/`tk` パッケージの整合性確認）ことを第一候補にする
  （既存機能レビューの「`init.tcl` 自体はPythonインストール先に存在するため、コード不具合と断定せず、
  Python/Tcl/Tk実行環境の修復後に再実行する」という判断を踏襲する）。
- どうしてもコード側で対処が必要な場合は、`frozen`（PyInstaller配布ビルド）判定と開発環境判定を分岐させ、
  開発環境限定のフォールバック（例: `sys.base_prefix` から動的に `tcl`/`init.tcl` の場所を探索する）に
  留め、配布ビルドの `_get_base_dir()` 相当のロジックには影響させない。
- GUIテスト（バッチOCR・OCRダイアログ配置・プラグインダイアログ・ショートカットダイアログ・トースト）は
  実際に `Tk()` を生成する統合テストであるため、CI環境（ヘッドレス実行）では仮想ディスプレイ
  （Windows では代替不可なため、実行環境そのものの整合性がより重要）が必要になる点も踏まえ、
  「ローカルでは直ったが CI では直っていない」を防ぐため、修復手順を `README.md`/`CLAUDE.md` レベルの
  ドキュメントとして残す（次回の環境入れ替え時に再発する可能性が高いため）。

**Warning signs:**
- 修復後、`pytest` を実行したユーザーのマシンでは通るが、別の開発者のマシン・将来のクリーンな環境
  （Python再インストール後等）で再び同じ24件が落ちる。
- 配布用 PyInstaller ビルド（EXE）の起動確認時に、開発環境では出なかった Tcl/Tk 関連のエラーが新たに出る。

**Phase to address:**
Phase 6（品質保証・持ち越し）だが、**リリースゲート**（「Tkinter環境を修復し、GUIを含む全テストが完走する
までリリースゲート合格とはしない」という既存機能レビューの判断基準）としての性質上、実際にはマイルストーン
全体を通じて早期（Phase 1 着手前後）に着手し、後続フェーズの GUI テスト（バッチOCR起動ガード・設定ダイアログ
Apply/Cancel等、いずれも Tkinter 依存）が正しく実行できる状態を先に確保しておくことが望ましい。

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| `except Exception` で保存/挿入失敗を握りつぶし、次の代替手段へ即フォールバックする | 実装が短く済み、ユーザーへは1つのエラーメッセージで済む | 暗号化引数のような「代替手段側で引き継ぐべき状態」が握りつぶしの陰で漏れる（Pitfall 1・3） | フォールバック先が元の呼び出しと**完全に同一の意味論**（暗号化・権限含む）であることを個別に確認済みの場合のみ |
| `off` を「LM Studio のエイリアス」として扱う後方互換維持コード | v1.4.0時点で UI 未実装だった `off` 相当を素早く動かせた | 「off の意味」を知らないと安全に触れないコードが5年分積み重なる（Pitfall 10） | 暫定実装であることをコード上に明記し、恒久化しない期限（次マイルストーンで解消等）を切る場合のみ |
| Undo state を実処理前に積んでから成功時に確定・失敗時に pop するパターン（`_do_insert` 方式） | 実処理の途中経過（挿入件数等）を後から確定でき、シンプルな try/except で書ける | 同パターンを機械的に横展開すると Blob dispose 契約や `current_page` スナップショットのタイミングを個別に検証しないと壊れる（Pitfall 6・7） | Blob を使わない・カーソル位置が操作中に変化しない単純な op（`duplicate` の pno のみ等）に限定する場合 |
| 外部ファイル連動を「切替のたびに書き込む」（ライブプレビュー優先）実装 | 外部エディタでの確認体験が良い | Apply/Cancel 契約と両立させるには「元の内容の保持＋Cancel時復元」という追加状態管理が必須になる（Pitfall 11） | ライブプレビューの価値がユーザーにとって高く、追加の状態管理コストを払う判断が明示的にできている場合 |

## Integration Gotchas（OpenAI プロバイダ固有）

既存の `ClaudeProvider`/`GeminiProvider`（`pagefolio/ocr_providers/`）と同じ urllib 直叩き方針
（V14-D-01 踏襲・新規 pip 依存ゼロ）で実装する前提。Claude が採用している「モデル種別ごとに
安全なパラメータ分岐（`_apply_gen_params` の3分岐: effort対応/temperature対応/両方省略）」パターンを
OpenAI 実装でも踏襲することを強く推奨する。

| 項目 | よくある誤り | 正しい対応 |
|------|----------------|------------|
| `max_tokens` パラメータ | 全モデルに一律 `max_tokens` を送る | `o1`/`o3`/`gpt-5` 系の reasoning モデルは `max_tokens` を受け付けず `max_completion_tokens` が必要（Chat Completions API の場合）。Claude実装の `_supports_effort()`/`_supports_temperature()` と同様の**モデル名判定関数**を用意し、reasoning系モデルには `max_completion_tokens`、非reasoning系には `max_tokens` を出し分ける。未知モデルは安全側（Claudeの「両方省略」相当）でパラメータを絞ることも検討する |
| `temperature` パラメータ | 全モデルに一律 `temperature=0.1`（既存の `ocr_temperature` 設定値）を送る | reasoning系モデルは `temperature` 固定（変更不可）で送ると 400 エラーになりうる。Gemini実装の `_is_legacy_gemini` 判定（世代番号でパラメータ送信可否を分岐する既存パターン）と同型のモデル名判定を導入する |
| 画像入力の形式 | Claude/Geminiと同じ `source.type=base64` 構造をそのまま流用する | Chat Completions API の画像入力は `content` 配列内に `{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}` という**データURL形式**であり、Claude（`source.media_type`+`data`）・Gemini（`inline_data`）とは構造が異なる。3プロバイダの payload 構築を安易に共通化しようとすると型が合わない |
| 画像サイズ/枚数上限 | サイズ/枚数チェックをせずページ画像をそのまま送信する | 総ペイロード50MB・1リクエストあたり画像枚数上限がある（値はモデル/APIバージョンで変動するため実装時に最新の公式ドキュメントを再確認する）。OCRは1ページ1画像送信のため通常は問題にならないが、将来「複数ページ一括送信」機能を足す場合に注意 |
| 429/RPM/TPM リトライ | Claude/Gemini と同じ固定バックオフだけで対応する | OpenAIの `Retry-After` ヘッダは「最小待機時間」であり、そのまま `clamp_retry_after`/`interruptible_sleep`（既存共通ヘルパー）を再利用できるが、RPM/TPM/RPD/TPDの4次元制限があるため、レート制限の原因表示（トークン超過かリクエスト回数超過か）をエラーメッセージに含めるとユーザーの理解が助かる |
| organization/project ヘッダ | 未指定でも動くと想定してヘッダを一切送らない実装にする | 個人アカウントでは省略可だが、Organization配下のプロジェクトキーを使うユーザーは `OpenAI-Organization`/`OpenAI-Project` ヘッダが必要になる場合がある。設定UIで必須にはしないが、APIキー入力欄の近くに任意入力欄として用意するか、エラーメッセージで案内する余地を設計しておく |
| ストリーミング未使用時のタイムアウト | 他プロバイダと同じ `ocr_timeout`（既定120秒）をそのまま流用する | reasoning系モデルは内部の思考トークン生成に時間がかかり、非ストリーミングでは応答が既存タイムアウトを超えやすい。`ClaudeProvider`/`GeminiProvider` が `model_list_timeout` をクラス属性でモデル一覧取得用に分離しているのと同様、OCR/サマリ本体のタイムアウトも既定値を高めに設定するか、reasoning系モデル選択時にUI上で注意書きを出す |
| `list_models` のフィルタ条件 | Claude実装の `capabilities.image_input.supported` と同じキー名をそのまま流用する | OpenAI の `/v1/models` レスポンス構造は Anthropic と異なる（`capabilities` ネスト構造ではない）。vision対応モデルの判定はモデルIDの命名規則や別エンドポイントの仕様を実装時に個別確認する必要がある |
| レスポンス形式の思い込み | Claude実装の `_extract_text`（`content` 配列から `type=="text"` を抽出する安全な `.get()` アクセス）と全く同じ構造を仮定する | Chat Completions API は `choices[0].message.content` が単純な文字列（or 新しいAPIでは配列）であり、Claudeの `content` ブロック配列とは構造が異なる。`_extract_text` 相当の関数は**プロバイダごとに個別実装**し、共通化を急がない（V190-REV-08 のメタデータ一元化とレスポンス解析ロジックの一元化を混同しない） |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| 一時 `Document`（複数ファイル挿入のトランザクション化）を全ファイル分メモリ上に保持してから本体へ反映する | 巨大PDFを多数挿入すると挿入完了までメモリ使用量が一時的に倍増する | 一時 `Document` は `insert_pdf` 完了ごとに `close()` して解放し、本体への反映は最終的な1回の `insert_pdf` のみに絞る（fitz内部でのメモリ再確保は避けられないが、無用な多重保持は避ける） | 数百MB級のPDFを複数同時挿入するユースケースで顕在化（通常のOCR/編集用途では稀） |
| `_restore_state()` のループ処理（`delete`/`insert_undo`/`merge` 等）に peek→確定 pop（Pitfall 8）を導入する際、失敗検知のために毎ページ後で `doc` の整合性チェックを挟む | Undo/Redo の体感速度が低下する（Core Value「Undo/Redo が正しく・速く動作する」に抵触） | 整合性チェックは「例外が実際に発生した場合のみ」ログ/警告を出す設計にとどめ、正常系のホットパスに追加コストを持ち込まない | 大きなPDF（数百ページ）でのUndo/Redoが要件（Core Value）のため、ここでの速度劣化は即座に問題化する |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| 暗号化維持保存の共通ヘルパー化（Pitfall 1）の際、パスワード解除操作（`save_without_password`）まで同じヘルパーに混ぜ込む | 「維持」のつもりの保存が誤って暗号化解除経路を通り、機密PDFが平文化する | 「維持系（`PDF_ENCRYPT_KEEP`）」と「変更系（解除/新規暗号化）」を関数レベルで明確に分離し、呼び出し元の条件分岐を1箇所（`pdf_has_password` の真偽）に集約する |
| OpenAI プロバイダ追加時、APIキーをエラーログや例外メッセージにそのまま含めてしまう | ログファイル/クラッシュレポート経由でのキー漏洩 | 既存の Claude/Gemini/RunPod 実装と同じ規約（キー名のみログ・値は非出力）を踏襲し、`urllib.error.HTTPError` の本文（`e.read()`）にキーが含まれるケース（一部APIはリクエストをエコーバックする）がないか実装時に確認する |
| `organization`/`project` ヘッダを設定UIの入力欄に追加する際、`_SENSITIVE_KEYS`/`registry.py` のガード対象に含め忘れる | organization ID 自体は機密度が低いが、誤って同じ入力欄にAPIキーを混入させる設計にすると settings.json への平文保存経路になりうる | 新規入力欄追加時は必ず `sensitive_keys()`（`registry.py`）の生成ロジックに新しい機密キー名（`openai_api_key` 等）が含まれることをテストで確認する（既存の3経路回帰テストパターンを踏襲） |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| OCR OFF ガードをバッチOCR起動時にのみ入れ、ダイアログを開くこと自体は許可する | ユーザーがバッチOCRダイアログでファイルを選び終えた後に初めて「OFFです」と言われ、手戻りが発生する | ダイアログを開く前（メニュー項目のトリガー時点）で `off` の場合は情報ダイアログを出してダイアログ自体を開かせない。実行開始ボタン側にも二重にガードを入れる（V190-REV-02 の推奨対応どおり「起動時と開始時」の両方） |
| 外部プロンプトファイルのCancel時復元（Pitfall 11）を、ユーザーへの明示的な通知なしに静かに行う | 「Cancelしたのに外部エディタで開いていたファイルの中身が勝手に元に戻った」と混乱する（外部ファイルはユーザーが直接編集する運用も想定されているため） | Cancel時に外部ファイルへ書き戻しが発生する場合は、ステータス表示等で「変更を破棄しました」と明示する（既存の `_set_status` パターンを踏襲） |
| Undo/Redo 復元失敗時（Pitfall 8）、エラーダイアログだけ出してUndo/Redoボタンを再度押せる状態のままにする | ユーザーが「直った」と誤解してもう一度押し、部分適用状態をさらに悪化させる | 復元失敗を検知したら、少なくともその操作セッション中は Undo/Redo ボタンを無効化し、「ファイルを保存せず再度開き直してください」という明示的な警告を出す |

## "Looks Done But Isn't" Checklist

- [ ] **暗号化維持保存:** 通常保存だけでなく「別名保存」「インクリメンタル失敗フォールバック」の**両方の副経路**でも `encryption=fitz.PDF_ENCRYPT_KEEP` が効いているか — `grep -n "\.save(\|tobytes(" pagefolio/file_ops.py` で全呼び出し箇所を洗い出して確認する
- [ ] **OCR OFF ガード:** 通常OCRボタン・バッチOCR起動時・バッチOCR実行開始時・プラグイン登録プロバイダのフォールバック候補列挙、**4経路すべて**で `off` が同じ意味になっているか（1経路だけ直して満足しない）
- [ ] **複数ファイル挿入のロールバック:** Undo スタックの整合性だけでなく、**`self.doc` 自体のページ数**も処理前と一致するか（部分挿入されたページが残っていないか）を失敗テストで確認する
- [ ] **Undo タイミング変更:** `_save_undo` の呼び出し位置を変えた op について、`current_page`/`selected_pages` が**操作前の値**のまま Undo エントリに記録されているか（操作後の値が紛れ込んでいないか）を回帰テストで確認する
- [ ] **外部プロンプトファイルのApply/Cancel:** テンプレート切替を複数回行った後にCancelした場合でも、ファイルの内容が**ダイアログを開く前の状態**に戻るか（Apply直前の状態ではなく）を確認する
- [ ] **OpenAI モデル別パラメータ:** reasoning系（`o1`/`o3`/`gpt-5`系）と非reasoning系（`gpt-4o`系）**両方**でOCRが成功するテスト（モック）があるか。片方のモデル種別でしか検証していない実装は「動いているように見えて実は特定モデルでしか動かない」典型例
- [ ] **Tkinter テスト環境修復:** ローカルで `pytest` が通っても、クリーンな別環境（別ユーザー/CI）で同じ24件が再現しないことまで確認したか（「自分のマシンでは直った」で止まらない）

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|-------------------|
| 暗号化維持保存漏れにより既に平文PDFが保存されてしまった | MEDIUM | 影響範囲（保存されたファイルの一覧）を特定し、ユーザーへ告知。当該ファイルは手動で再暗号化（「🔒 パスワード」セクションの別名保存）するよう案内。再発防止として Pitfall 1 の共通ヘルパー化と回帰テストを即座に追加 |
| Undo Blob のリーク（tempfile残留）が本番で発覚した | LOW | 既存の Windows AV スキャン衝突安全網・`atexit` purge の仕組みで多くは自然回収されるが、`_undo_blob_store` のディレクトリを手動クリーンアップするツール（既存にあれば流用、無ければ簡易スクリプト）で対応。恒久対応は Pitfall 7 の dispose 契約の明文化 |
| `off` ガード変更でバッチOCRが正当な理由で動かなくなった（過剰ブロック） | LOW | `ocr_provider` 設定値と `off` 判定ロジックの対応表をログに出す簡易デバッグモードを一時的に追加し、原因箇所を特定。Pitfall 10 のガード実装を再確認 |
| メタデータ一元化リファクタで一部のプロバイダ表示が壊れた（例: 送信先表示が空になる） | MEDIUM | 新レジストリのメタデータ定義に該当プロバイダのエントリが漏れていないか確認。旧実装（分割前のコミット）とのdiffを取り、どの参照面が移行されていないか特定する |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|--------------------|-----------------|
| 1. 暗号化保存デフォルト消失 | Phase 1（保存・編集の安全性） | 暗号化PDFを開く→別名保存/上書き/インクリメンタル失敗フォールバックの3経路すべてで再度パスワードが要求されるテスト |
| 2. authenticate後のパスワード非保持 | Phase 1 | `PDF_ENCRYPT_KEEP` 一本化方針を PLAN.md に明記し、パスワード再指定方式を採らないことをコードレビューで確認 |
| 3. incremental と暗号化変更の非互換 | Phase 1 | `can_save_incrementally()` を False にモックしフォールバック経路でも暗号化維持を検証するテスト |
| 4. permissions省略時の既定値 | Phase 1 | 暗号化維持ヘルパーとパスワード付与ヘルパーを関数分離し、既存パスワード付与テストが権限面で退行していないことを確認 |
| 5. pdf_has_passwordフラグ不整合 | Phase 1 | 保存直後の `pdf_has_password` とUI表示（🔒セクション活性状態）が実ファイルと一致することを確認（human-verify候補） |
| 6. Undoタイミング後ろ倒しの副作用 | Phase 1 | `_duplicate_page` を仮エントリ確定パターンへ書き換え、`current_page`/`selected_pages` が操作前値であることを回帰テストで検証 |
| 7. Blob二重dispose/dispose漏れ | Phase 1〜3 | Blobを伴うopへタイミング変更を横展開する場合は一時ファイル数の増減を監視するテストを追加 |
| 8. undo/redoのpop→restore間の例外 | Phase 3（Undo/Redo回帰強化） | peek→確定popへの変更＋`duplicate`/`merge`/`merge_resize`の4手往復テスト＋フォールトインジェクションテスト |
| 9. 複数ファイル挿入の非トランザクション性 | Phase 1 | 2件目失敗テストで`len(self.doc)`とUndoスタック長が処理前と一致すること、`src`のクローズ漏れがないことを確認 |
| 10. offガード変更の後方互換破壊 | Phase 1（実装）／Phase 4（設計統合） | `off`全参照箇所の洗い出しリストと、4経路（通常/バッチ起動/バッチ実行/プラグイン）すべてのガードテスト |
| 11. 外部ファイル書き込みの二重トリガー | Phase 2（設定UIの整合性） | 方式（一本化 or ライブ復元）をPLAN.md確定後、Cancel後のファイル内容が「開く前の状態」に戻ることを検証 |
| 12. メタデータ一元化の参照面取りこぼし | Phase 4（OCRプロバイダ基盤整理） | リファクタ後に本番コードへ意図的にバグを注入してテストが検知することを確認（monkeypatch生存確認） |
| 13. Tkinterテスト環境修復 | Phase 6（品質保証）だが着手はPhase 1着手前後を推奨 | クリーンな別環境でも24件のセットアップエラーが再現しないことを確認し、修復手順を文書化 |
| OpenAI固有パラメータ非互換 | OpenAIプロバイダ追加フェーズ（Phase 4後） | reasoning系/非reasoning系モデル両方でのOCR成功モックテスト、Claude実装の`_apply_gen_params`型のモデル判定分岐の単体テスト |

## Sources

- [How to Save a PDF Document with PyMuPDF: Encryption and Much More! (Artifex)](https://artifex.com/blog/how-to-save-a-pdf-document-with-pymupdf-encryption-incremental-saving) — `PDF_ENCRYPT_KEEP`/`PDF_ENCRYPT_NONE`/`PDF_ENCRYPT_AES_256` の使い分け、インクリメンタル保存可否の確認方法
- [The Basics - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/the-basics.html) — `can_save_incrementally()` と暗号化変更時の非インクリメンタル保存の必要性
- [Document - PyMuPDF - Read the Docs](https://pymupdf.readthedocs.io/en/latest/document.html) — `Document.save()` のパラメータ仕様
- [How to remove password for opening pdf? (PyMuPDF Discussion #3003)](https://github.com/pymupdf/PyMuPDF/discussions/3003) — `authenticate()` はowner passwordが必要、`PDF_ENCRYPT_NONE`での復号保存パターン
- OpenAI API: `max_tokens`→`max_completion_tokens`（reasoning系モデル）に関するコミュニティ報告・OpenAI公式ヘルプ「Controlling the length of OpenAI model responses」
- [Rate limits | OpenAI API](https://platform.openai.com/docs/guides/rate-limits) — RPM/TPM/RPD/TPDの4次元制限、`Retry-After`の扱い、organization/projectスコープ
- [Images and vision | OpenAI API](https://developers.openai.com/api/docs/guides/images-vision) — 画像入力の総ペイロード上限・枚数上限
- プロジェクト内部ソース（現行実装の実地確認）: `pagefolio/file_ops.py`（保存/Undo/Redo実装）・`pagefolio/page_ops.py`（挿入/複製）・`pagefolio/ocr.py`（`build_provider`）・`pagefolio/ocr_providers/registry.py`・`pagefolio/ocr_providers/claude.py`（モデル別パラメータ分岐の既存パターン）・`pagefolio/dialogs/llm_config/sections.py`・`pagefolio/dialogs/llm_config/dialog.py`（v1.8.0分割時のmonkeypatch名前空間断絶コメント）
- `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md`（V190-REV-01〜08の一次情報源）
- `.planning/PROJECT.md`（v1.8.0 Key Decisions の V180-D-01/D-17 等、過去の類似リファクタ・バグ修正の記録）

---
*Pitfalls research for: PageFolio v1.9.0（安全性・整合性の是正 + OpenAIプロバイダ追加）*
*Researched: 2026-08-10*
