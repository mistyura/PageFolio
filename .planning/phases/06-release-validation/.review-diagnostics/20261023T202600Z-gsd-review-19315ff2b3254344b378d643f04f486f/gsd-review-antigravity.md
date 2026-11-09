## 06-01

### 1. 要約
`tools/build_release.py` による PyInstaller `--onedir` 公式ビルドパイプライン（私有 `spec/work/dist` staging → 検査 → 原子的昇格 → `release-report.json` 出力）と、配布同梱物（`distribution/はじめに.md` および `distribution/samples/` 2件）の正本化、ならびに `tests/test_release_build.py` による単体契約テストを構築する計画である。

### 2. 強み
- **既存 `dist/PageFolio` を汚さない隔離ビルド設計**: `.gitignore:10-12` では `!dist/PageFolio` と `!dist/PageFolio/**` が追跡対象として除外解除されており、既存の `dist/PageFolio/ocr_custom_prompt_sample.md:1-7` および `dist/PageFolio/ocr_summary_prompt_sample.md:1-26` がリポジトリに存在する。`.planning/phases/06-release-validation/06-01-PLAN.md:94` が私有作業領域 `dist/.release-work/<run-id>/` で PyInstaller を実行し、`dist/PageFolio-<APP_VERSION>/` へ原子的に昇格する設計は、既存の追跡対象ディレクトリとの衝突を完全に回避できている。
- **アプリ本体のパス解決仕様との整合**: `pagefolio/settings.py:55-61` の `_app_dir()` は `getattr(sys, "frozen", False)` 時に `os.path.dirname(sys.executable)` を返し、サンプルプロンプトや `pagefolio_settings.json` を EXE と同一階層で解決する（`docs/CONFIGURATION.md:107-112`、`pagefolio/ocr_dialog.py:1303-1305`）。`.planning/phases/06-release-validation/06-01-PLAN.md:94` が `PageFolio.exe`、`_internal/`、`はじめに.md`、サンプル2件をルート直下に配置し `pagefolio_settings.json` や `.tmp` の不在を昇格前に検査する設計は、凍結実行時の仕様と正確に一致している。
- **DoD テスト基盤のヘルパー再利用**: `.planning/phases/06-release-validation/06-01-PLAN.md:109` が `tests/test_gsd_dod.py:37-112` の `_read_utf8` / `_git_tracked_files` 等の既存検証パターンを踏襲しており、文字化け（`U+FFFD`）や CRLF/LF 差異に強い検証構造になっている。

### 3. 懸念
- **MEDIUM**: **PyInstaller `--specpath` 指定時の相対パス解決によるビルド失敗リスク**
  - 根拠: `.planning/phases/06-release-validation/06-01-PLAN.md:94` では `Python -m PyInstaller --onedir --noconsole --icon pagefolio.ico --name PageFolio（私有spec/work/distの固定argv、shell=False）` と記載されている。しかし PyInstaller は `--specpath <private_spec_dir>` を指定すると、生成される `.spec` 内のスクリプトパスや `--icon` の相対パスを `--specpath` 基準で解決するため、`pagefolio.py` や `pagefolio.ico` を相対パスで渡すと `dist/.release-work/<run-id>/spec/pagefolio.py` を探して失敗する。
- **MEDIUM**: **`06-01` と `06-02` 間での `distribution/はじめに.md` の二重定義と `must_haves.artifacts` の記載漏れ**
  - 根拠: `.planning/phases/06-release-validation/06-01-PLAN.md:10,91,94` では `06-01-01` で `distribution/はじめに.md` を作成・同梱対象としている一方、`06-01-PLAN.md:25-33` の `must_haves.artifacts` および `06-01-PLAN.md:73-78` の成果物一覧から `distribution/はじめに.md` が漏れている（`.planning/phases/06-release-validation/06-02-PLAN.md:30-32,101-106` の `06-02-02` 側にも作成・更新タスクが存在する）。また、`06-01-01` 実行時点では `pagefolio/constants.py:12` の `APP_VERSION` は `"v1.9.1"` であるため、トレーサービルドの出力先は `dist/PageFolio-v1.9.1` となる点に注意が必要である。
- **LOW**: **Windows におけるディレクトリ入替（`os.replace`）の非原子性とロック競合**
  - 根拠: `.planning/phases/06-release-validation/06-01-PLAN.md:94,113` で「staging 成功後にのみ出力先を原子的に入れ替え」「再ビルド時のみ自社 marker 付き既存出力を backup 経由で入替」としているが、Windows の `os.replace` は非空ディレクトリ同士の上書きができず、リネーム中に Explorer やウイルス対策ソフトがハンドルを掴んでいると `PermissionError`（`WinError 5`）が発生しやすい。

### 4. 具体的提案
1. `tools/build_release.py` から PyInstaller を呼び出す際は、`--specpath`・`--workpath`・`--distpath` に加え、`--icon`（`repo_root / "pagefolio.ico"`）およびエントリポイント（`repo_root / "pagefolio.py"`）をすべて `Path.resolve()` した絶対パスで渡すことを `06-01-PLAN.md:94` に明記すること。
2. `06-01-01` では `distribution/はじめに.md` の初期正本を作成して `06-01-PLAN.md:25-33` の `must_haves.artifacts` にも含め、`06-02-02` はその内容を D-01〜D-12 の全要件で完成・検証する役割分担として明文化すること。また、トレーサービルドで生成される `dist/PageFolio-v1.9.1` が後続の `dist/PageFolio-v1.10.0` と干渉しない（またはクリーンアップされる）ことを整理すること。
3. 既存出力の backup 退避・昇格リネームには、Windows 特有の一時的ファイルロックに備えた短時間の段階的リトライ（例: 50ms〜200ms × 数回）と、昇格失敗時に backup を元の場所へ戻すロールバック処理を必ず実装すること。

### 5. 総合リスク
**LOW**

---

## 06-02

### 1. 要約
`pagefolio/constants.py` の `APP_VERSION` を `"v1.10.0"` へ更新し、`README.md`・`開発履歴.md`・`docs/DEVELOPMENT.md`・`distribution/はじめに.md` を同期させた上で、それらの整合性を検証する `tests/test_release_contract.py` を追加する計画である。

### 2. 強み
- **単一情報源（SSOT）原則の徹底**: `AGENTS.md:15-18` の規約通り、`pagefolio/constants.py:12` の `APP_VERSION`、`README.md:5` のバッジ、`開発履歴.md` を同期させ、かつ `.planning/phases/06-release-validation/06-02-PLAN.md:89` で「未実施の EXE/UAT を成功と書かない」制約を課している点は誠実で安全性が高い。
- **`docs/DEVELOPMENT.md` の手動手順との不整合解消**: 現在の `docs/DEVELOPMENT.md:190-209` は `--distpath dist` による `dist/PageFolio/` 出力と手動でのサンプルコピーを案内しており、Phase 6 の D-01/D-02（`dist/PageFolio-v1.10.0` への自動同梱と `はじめに.md` 追加）と乖離している。`.planning/phases/06-release-validation/06-02-PLAN.md:89` がこの更新をスコープに含めている点は的確である。

### 3. 懸念
- **MEDIUM**: **`開発履歴.md` 内の3箇所のバージョン記述構造と Phase 5 記述の更新方法が曖昧**
  - 根拠: 現在の `開発履歴.md` は、(1) 先頭の `## 未リリース — Phase 5 設定の読込・保存失敗通知（2026-10-24）`（`開発履歴.md:3-19`、ここに `全件1789 passed... H01〜H12は12 pass... Nyquistと独立検証は未実施` という古い記述がある）、(2) `## v1.9.1 — 2026-10-22`（`開発履歴.md:23`）、(3) 引用ブロック `> **最終更新**: v1.9.0 — 2026-08-11`（`開発履歴.md:37`）、(4) `## バージョン索引` テーブル（`開発履歴.md:72-80`、`v1.9.0` までしか記載がない）という構造になっている。`.planning/phases/06-release-validation/06-02-PLAN.md:89` の「最新v1.10.0節を同期する」「Phase5履歴の古い受入状況を現在の正本に照合した追記で補い、履歴自体は消さない」だけでは、`## 未リリース` 見出しを `## v1.10.0` に昇格させるのか別節を立てるのか、また `開発履歴.md:37` と `開発履歴.md:74` の索引テーブルをどう更新するのかが曖昧であり、`TestVersionAndDocs` の正規表現と齟齬を生む懸念がある。
- **LOW**: **`distribution/はじめに.md` のバージョン表記と単体テストの結合度**
  - 根拠: `.planning/phases/06-release-validation/06-02-PLAN.md:104` で `distribution/はじめに.md` に `PageFolio-v1.10.0` を明記する設計となっているため、`TestUserGuideContract` でバージョン文字列を検証する際は `pagefolio/constants.py:12` の `APP_VERSION` と連動させるのが望ましい。

### 4. 具体的提案
1. `06-02-PLAN.md:89` において、`開発履歴.md` の具体的な見出し構成（例: 先頭に `## v1.10.0 — YYYY-MM-DD ...` 節を配置し、`開発履歴.md:3-19` の Phase 5 節には `.planning/phases/05-config-notification/05-UAT.md:46-94` の最終結果「H01〜H14 + Test 1/2 の計16件 pass・Nyquist 検証済」を追記すること、および `開発履歴.md:37` の最終更新行と `開発履歴.md:74` のバージョン索引テーブルに `v1.9.1` / `v1.10.0` を反映すること）を明示すること。
2. `tests/test_release_contract.py` の `TestVersionAndDocs` では、`APP_VERSION`（`pagefolio/constants.py:12`）、`README.md:5` のバッジ、`開発履歴.md` の最新バージョントップ見出し、`distribution/はじめに.md` 内の展開フォルダ名（`f"PageFolio-{APP_VERSION}"`）の4点一致を機械的に検証すること。

### 5. 総合リスク
**LOW**

---

## 06-03

### 1. 要約
審査ツール `tools/verify_release.py`（`bundle` / `exe-smoke` / `exe-functional` / `uat-init` / `uat-validate` / `audit`）を実装し、凍結 EXE に対する機能スモーク（X01〜X06）、ローカル loopback の擬似 Ollama サーバ、Win32/UI 観測、および設定ファイル異常注入の仕組みを構築する計画である。

### 2. 強み
- **Ollama プロバイダを選定したローカル完結テストの妥当性**: `pagefolio/ocr_providers/ollama.py:19,86-156` は API キー（環境変数）を必要とせず、標準ライブラリの `urllib.request.urlopen` で `{base_url}/api/chat`（POST）および `{base_url}/api/tags`（GET）と通信する。また `pagefolio/ocr_dialog.py:1309-1311,1643-1648` は `self.settings.get("ollama_url")` と `self.settings.get("ollama_model")` を直接読み取ってプロバイダを生成するため、作業コピー側の `pagefolio_settings.json` に `ocr_provider="ollama"` と `127.0.0.1:<ephemeral_port>` を書き込む設計（`.planning/phases/06-release-validation/06-03-PLAN.md:115`）は外部通信ゼロで確実に機能する。
- **Phase 4 / Phase 5 の既存観測資産の適切な活用**: `tests/test_startup_windows.py:72-184` の Win32 ウィンドウ列挙・クラッシュ監視や `tests/config_notice_support.py:55-127` の設定ファイル検証パターンを流用し、実 EXE を改変せずに外部から検証するアプローチが明確である。

### 3. 懸念
- **HIGH**: **`W05b`（OCR所有のネイティブ `messagebox`）を「fallback 無効＋fake OCR 応答エラー」で発火させることはコード上不可能**
  - 根拠: `.planning/phases/06-release-validation/06-03-PLAN.md:115` には「`fallbackを無効化して既存LLM/OCR UI経由で開始する。... W05bはfake OCR応答エラーから本物のOCR所有messageboxを表示し人が閉じるカードを用意する`」と記載されている。しかし、`pagefolio/ocr_dialog.py:2030-2064`（`_finish_error`）および `pagefolio/ocr_dialog.py:1946-2015`（`_render_results_ordered` / `_finish_complete`）を確認すると、OCR 実行中の通信エラーや HTTP 500 エラーはダイアログ内のテキストウィジェットと進捗ラベル（`self.progress_var`）に書き込まれるだけで、`messagebox.showerror` 等は一切呼ばれない。`_finish_error` 末尾の `self._propose_fallback(kind, msg)`（`pagefolio/ocr_dialog.py:2063`）も、`ocr_fallback_enabled` が `False` の場合は `pagefolio/ocr_dialog.py:2471-2472` で即座に `return` するため、ネイティブ `messagebox` は絶対に表示されない（なお Python ハーネス版の `tests/test_startup_windows.py:1848-1850` はテストコードから直接 `messagebox.showinfo(..., parent=state["target"])` を呼んでいたため発火していた）。
- **HIGH**: **合成3ページ PDF に埋め込みテキストがあると Vision OCR（Ollama 通信）がスキップされる**
  - 根拠: `.planning/phases/06-release-validation/06-03-PLAN.md:115` で「合成3ページPDFのOCR応答を返す」としているが、`pagefolio/ocr_dialog.py:1718-1725` の `_render_next_page` は `if not self._force_ocr and has_embedded_text(page):` を判定し、ページに埋め込みテキストが存在すると LLM API を呼ばずに埋め込みテキスト抽出で完了させてしまう（`tests/conftest.py:36` のような `page.insert_text(...)` を使うと `has_embedded_text` が真になり得る）。
- **MEDIUM**: **凍結 EXE（`--noconsole`）では `logger.debug` が出力されないため、設定失敗分類を「ログで確認」できない**
  - 根拠: `.planning/phases/06-release-validation/06-03-PLAN.md:115` に「`EXEの設定missing/corrupt/unreadable/write-fail/replace-failは隔離copyに合成JSON、外部CreateFileWのshare制限で読取/削除を拒否するlock、専有tmp衝突等を準備し、実際のエラー分類をログで確認してから使う`」とある。しかし `pagefolio/settings.py:317-319`（`_load_settings_result`）および `pagefolio/settings.py:384-388`（`_save_settings`）は `logger.debug(...)` でしかログを出さず、無改変の凍結 EXE にはファイルロガーや標準出力ハンドラが構成されていないため、外部プロセスから `logger.debug` を読むことはできない。

### 4. 具体的提案
1. **`W05b` の発火経路の修正**: 無改変の凍結 EXE で `OCRDialog` 所有のネイティブ `messagebox`（`parent=self`）を確実に表示させるため、`06-03-PLAN.md:115` の `W05b` シナリオを以下のいずれか（または両方）に変更すること。
   - **案A（推奨・実行中クローズ確認）**: `W05a` と同様に fake Ollama サーバが応答を遅延（hold）している最中に、`OCRDialog` の閉じるボタン（`WM_CLOSE` / `✕ 閉じる`）を送出して `pagefolio/ocr_dialog.py:2085-2097` の `_on_close()` → `messagebox.askyesno(self._L["confirm_title"], self._L["ocr_close_during_run"], parent=self)` を表示させる（これなら fallback 無効のまま確実に `OCRDialog` 所有のネイティブモーダルが出る）。
   - **案B（フォールバック提案モーダル）**: `W05b` 専用プロファイルとして `ocr_fallback_enabled: true` かつ `ocr_fallback_chain: ["lmstudio"]` を設定し、fake Ollama サーバが接続拒否または3回連続エラー（`CB_CONSECUTIVE_FAILURES = 3`、`pagefolio/ocr_dialog.py:74`）を返して `pagefolio/ocr_dialog.py:2497-2507` の `messagebox.askyesno(..., parent=self)` を発火させる。
2. **合成 PDF の仕様明記**: `X03` / `W05a` / `W05b` で生成する合成3ページ PDF は、`has_embedded_text(page)` が必ず `False` になるよう、テキストを含まないラスタ画像（`page.insert_image`）または図形のみのページとして生成することを `06-03-PLAN.md:115` に明記すること。
3. **設定失敗分類の検証方法の精緻化**: `X04` における `missing` / `corrupt` / `unreadable` / `save-write` / `save-replace` の分類確認は、EXE の内部 `logger.debug` ではなく、(a) 注入前のハーネス側での事前検証、(b) `save-write`（既存 `.tmp` 衝突により `owned_tmp=False` のまま失敗し `.tmp` が残存：`pagefolio/settings.py:377-379,389`）と `save-replace`（対象 `pagefolio_settings.json` を外部プロセスから `CreateFileW` の `FILE_SHARE_READ | FILE_SHARE_WRITE`［`FILE_SHARE_DELETE` なし］で保持することで、起動時読込と `.tmp` 作成は成功しつつ `os.replace` のみ失敗し `.tmp` が自動削除される：`pagefolio/settings.py:381,391`）のファイルシステム状態差、(c) トースト通知文言の差によって判定するよう `06-03-PLAN.md:115` を修正すること。

### 5. 総合リスク
**HIGH**（`W05b` の発火条件および合成 PDF の埋め込みテキスト条件を修正すれば **LOW** に低減可能）

---

## 06-04

### 1. 要約
`tools/build_release.py` を用いて `dist/PageFolio-v1.10.0` の初回クリーンビルドと管理下再ビルドを実行して `06-BUILD-EVIDENCE.json` に記録し、続けて作業コピー上で `verify_release.py` の `bundle` / `exe-smoke` / `exe-functional`（X01〜X05）を実行して `06-EXE-EVIDENCE.json` を作成する計画である。

### 2. 強み
- **出荷フォルダ不汚染の原則**: `.planning/phases/06-release-validation/06-04-PLAN.md:96` において、`dist/PageFolio-v1.10.0` 本体を直接起動するのではなく、一時ディレクトリ上の作業コピーで X01〜X05 を実行し、実行前後で出荷フォルダのファイル集合と全ファイル SHA-256 が不変であることを検証する設計は、配布物のクリーンさを保証する上で非常に優れている。
- **PyInstaller の非決定性に対する現実的な配慮**: `.planning/phases/06-release-validation/06-04-PLAN.md:80` で「二つの実EXEのbit再現性は要求せず、各入力と各成果物のhashを個別に記録する」と明記しており、PE ヘッダや PYZ タイムスタンプによる不要なビルド失敗を防いでいる。

### 3. 懸念
- **HIGH**: **`06-04-01` の `<verify><automated>` が3回目のビルドを実行し、`06-BUILD-EVIDENCE.json` のハッシュ記録を破壊する**
  - 根拠: `.planning/phases/06-release-validation/06-04-PLAN.md:80` の `<action>` では、初回クリーンビルド（1回目）と管理下再ビルド（2回目）を実行し、最終成果物のハッシュを `.planning/phases/06-release-validation/06-BUILD-EVIDENCE.json` に記録する。ところが、直後の `06-04-PLAN.md:85` の `<verify><automated>` に `.venv/Scripts/python.exe tools/build_release.py --output-root dist` が指定されている。PyInstaller の生成 EXE はビルドごとにハッシュが変わるため、`<verify>` で再度 `build_release.py` を走らせると3回目のビルドが実行され、`dist/PageFolio-v1.10.0/PageFolio.exe` と `release-report.json` が上書きされて `06-BUILD-EVIDENCE.json` に記録した SHA-256 と不一致になり、後続の `06-04-02`（`06-04-PLAN.md:96`）および `06-05-01`（`06-05-PLAN.md:74`）の同一性チェックが必ず失敗する。
- **MEDIUM**: **`06-03` の懸念（合成 PDF の埋め込みテキスト・設定失敗分類の確認手段）の波及**
  - 根拠: `.planning/phases/06-release-validation/06-04-PLAN.md:96` の X03（設定・OCR ダイアログ）および X04（設定通知）は `06-03` の `exe-functional` 実装に依存するため、`06-03` で指摘した合成 PDF の画像ページ化と `CreateFileW` 共有モード制御が正しく実装されている必要がある。

### 4. 具体的提案
1. `06-04-PLAN.md:85`（Task `06-04-01`）の `<verify><automated>` を `build_release.py` の再実行ではなく、`verify_release.py bundle` または `06-BUILD-EVIDENCE.json` と `dist/PageFolio-v1.10.0/release-report.json` のハッシュ一致・2回ビルド履歴存在を検証するコマンド（例: `.venv/Scripts/python.exe tools/verify_release.py bundle --bundle-dir dist/PageFolio-v1.10.0 --build-evidence .planning/phases/06-release-validation/06-BUILD-EVIDENCE.json`）に変更すること。
2. もし `<verify>` 内で `build_release.py` を実行したい場合は、`<action>` 自体で2回実行後に `06-BUILD-EVIDENCE.json` を確定させ、`<verify>` では読み取り専用の検証コマンドのみを実行するように徹底すること。

### 5. 総合リスク
**HIGH**（`06-04-01` の `<verify>` コマンドによる再ビルド上書き問題を修正すれば **LOW**）

---

## 06-05

### 1. 要約
人間による実機 UAT（Phase 4 繰越しの `W01`〜`W12`、Phase 5 繰越しの `H01`〜`H14` + `Test 1`/`Test 2`、Phase 6 の `X06`）の記録テンプレートと実行カードを `06-PRODUCTION-UAT.md` に生成し（`06-05-01`）、ユーザーによる実機確認・記入を経て `verify_release.py uat-validate` で完了検証と上流 UAT 文書への相互リンク同期を行う（`06-05-02`）計画である。

### 2. 強み
- **AI による UAT 捏造の厳格な防止**: `.planning/phases/06-release-validation/06-05-PLAN.md:74,95` で、`06-05-01` 時点では `pending` 状態のテンプレートのみを生成し、`06-05-02` で人間が記入した実績時刻・観察メモ・証跡を `uat-validate` で機械検証する2段階構成（`checkpoint:human-verify`）としており、`.planning/phases/04-startup-control/04-WINDOWS-UAT.md:10-25` や `.planning/phases/05-config-notification/05-UAT.md:1-45` の厳格な証跡要件を満たしている。
- **別 Windows ログインセッション（`W11`）の停止ゲート明文化**: `.planning/phases/06-release-validation/06-05-PLAN.md:95,103` で、同一ユーザー別プロセスでの代用を禁止し、別 Windows アカウント／別ログオンセッションが準備できない場合は `environment-blocked` としてリリース承認を止める設計が明確である。

### 3. 懸念
- **MEDIUM**: **`06-05-02` の前提条件である「親 workflow の `$gsd-execute-phase 04` による stale 再検証」の実行タイミング**
  - 根拠: `.planning/phases/06-release-validation/06-05-PLAN.md:91` の `<preconditions>` に「`親workflowの $gsd-execute-phase 04 による現行入力のstale再検証が完了し、04-VERIFICATIONの対象hash/鮮度が現行と一致する`」とある。現在の `.planning/phases/04-startup-control/04-VERIFICATION.md:4-7` は Phase 5 での `pagefolio/app.py` 等の変更により stale 状態にある。幸い Phase 6 の全計画（`06-01`〜`06-06`）は `04-VERIFICATION.md:6` の `covered_files`（`pagefolio/app.py`、`pagefolio/lang.py`、`pagefolio/startup_*.py`、`tests/test_startup_*.py`、`tests/test_gsd_dod.py`）を一切変更しないため、Phase 6 の実行前または `06-05-02` の前に一度 Phase 4 の再検証を完了させておけばハッシュは維持されるが、オーケストレータがこれを忘れると Wave 5 で停止する。
- **MEDIUM**: **`X06` におけるバージョン確認箇所の記述（「About/タイトルの版」）と実 UI の差異**
  - 根拠: `.planning/phases/06-release-validation/06-05-PLAN.md:95` に「`X06は... About/タイトルの版とfolder/report一致を確認する`」とあるが、PageFolio には独立した「About ダイアログ」は存在せず、`APP_VERSION` はウィンドウタイトルおよびヘッダーラベルに表示される仕様である。人間向け UAT カードに「About ダイアログを開く」と書かれるとテスターが迷う懸念がある。

### 4. 具体的提案
1. `06-05-01` が生成する `X06` の人間向け手順カードでは、「About ダイアログ」ではなく実際の表示箇所（メインウィンドウのタイトルバーおよびヘッダー領域の `v1.10.0` 表示）を確認するよう具体的に記述すること。
2. `06-03` で指摘した通り、`06-05-01` が生成する `W05b` の実行カードは、無改変 EXE で実際にネイティブ `messagebox` が発生する手順（OCR 実行中の閉じるボタン押下による確認ダイアログ、または fallback 有効時のフォールバック確認ダイアログ）を案内すること。
3. Phase 6 実行開始前（または Wave 5 突入前）に Phase 4 の stale 再検証を実施し、`.planning/phases/04-startup-control/04-VERIFICATION.md` の `input_digest` を現行ワークツリーに同期させる手順を親ワークフロー側で確実に実行すること。

### 5. 総合リスク
**MEDIUM**（人間の実機操作と別 Windows セッション準備を伴うため）

---

## 06-06

### 1. 要約
全件品質ゲート（Ruff lint/format、AST、単一全件 `pytest`）の証跡を `06-EVIDENCE.json` に固定し、`verify_release.py audit --for-handoff` で全要件・全証跡・配布フォルダ不変性を監査した上で、`06-VERIFICATION.md` とセッション終了申し送りを作成する最終計画である。

### 2. 強み
- **全入力マニフェストとビルド・UAT・品質ゲートの完全な連鎖監査**: `.planning/phases/06-release-validation/06-06-PLAN.md:83,104` が、コード・テスト・ドキュメント・ビルド成果物・UAT 証跡・品質ゲート証跡のすべてのハッシュと時刻順序（`build <= exe <= uat`）を `verify_release.py audit --for-handoff` で機械的に照合する設計になっており、検証漏れや古い証跡の混入を防ぐ仕組みとして完成度が高い。
- **長時間 pytest の安全な再利用条件の定義**: 全件 `pytest` が約4分半（`.planning/STATE.md:49` で 1789 passed in 271.22s）かかることを踏まえ、`06-06-PLAN.md:104` で全入力マニフェストが完全一致する場合の証跡再利用条件と、不一致時の再実行ルールを厳密に定めている。

### 3. 懸念
- **LOW**: **`06-06-02` の `<verify><automated>` による全件 `pytest` の二重実行とタイムスタンプ逆転リスク**
  - 根拠: `.planning/phases/06-release-validation/06-06-PLAN.md:104` の `<action>` では、「`auditより前に06-EVIDENCEへ実commit+dirtyhash/全入力manifest/コマンド/exit/件数/時間/ログhashを記録する`」とし、その後 `verify_release.py audit --for-handoff` を実行して `06-VERIFICATION.md` を作成する。しかし `06-06-PLAN.md:107` の `<verify><automated>` に `.venv/Scripts/python.exe -m pytest -q --basetemp=...` が設定されているため、`<action>` 内で全件 `pytest` を実行した後に `<verify>` でもう一度約270秒の全件 `pytest` が走る構成になっている。

### 4. 具体的提案
1. `06-06-02`（`06-06-PLAN.md:104-109`）では、全件 `pytest` の実行結果をそのまま `06-EVIDENCE.json` に記録するラッパー（または `verify_release.py audit --for-handoff` 自体）を `<verify><automated>` の最終確認コマンドとすることで、約270秒のテストスイートが無駄に2回連続実行されるのを防ぐこと。

### 5. 総合リスク
**LOW**

---

## 横断評価

1. **エッジケースとエラー処理**
   - 設定ファイル関連の5分類（`missing` / `corrupt` / `unreadable` / `save-write` / `save-replace`）や、既存 `dist/PageFolio` の保護、出荷フォルダ `dist/PageFolio-v1.10.0` を直接起動せず作業コピーで検証する設計など、ファイルシステム周りのエッジケースは非常に丁寧に考慮されている。
   - 一方で、**無改変の凍結 EXE における `OCRDialog` の挙動**に関する2つのエッジケース（① `pagefolio/ocr_dialog.py:2030-2064,2471-2472` において fallback 無効時は OCR エラーでネイティブ `messagebox` が出ない点、② `pagefolio/ocr_dialog.py:1718-1725` において合成 PDF に埋め込みテキストがあると Vision OCR がスキップされる点）が見落とされているため、`06-03` の実装前に必ず計画を補正する必要がある。
2. **依存関係と実行順序（Wave 構成）**
   - Wave 1（`06-01` ビルド基盤）→ Wave 2（`06-02` v1.10.0 文書・契約テスト）→ Wave 3（`06-03` 審査ツール `verify_release.py`）→ Wave 4（`06-04` 実ビルドと EXE 自動検証）→ Wave 5（`06-05` 実機 UAT、および `06-06` 最終監査）の依存順序は論理的で破綻がない。
   - ただし、**`06-04-01` の `<verify><automated>` で `build_release.py` を再実行してしまう問題**（`06-04-PLAN.md:85`）は、`06-BUILD-EVIDENCE.json` に記録した EXE の SHA-256 を直後に上書き破壊して後続の `06-04-02`〜`06-06` を連鎖失敗させるため、実行前に修正が必須である。
   - また、`06-05-02` の前提条件である Phase 4 の stale 再検証（`04-VERIFICATION.md` の更新）を Wave 5 開始前までに完了させる段取りを徹底する必要がある。
3. **過剰設計・安全性・パフォーマンス**
   - `tools/build_release.py` と `tools/verify_release.py` の2スクリプトへの責務分離は明確であり、アプリ本体（`pagefolio/` 配下）のロジックには `pagefolio/constants.py:12` の `APP_VERSION = "v1.10.0"` 以外一切手を加えないため、Phase 4・Phase 5 で確立した起動制御や設定通知の安定性を損なうリスクが極めて低い。
   - パフォーマンス面では、PyInstaller ビルドと全件 `pytest`（約270秒）が重いため、`06-04-01` と `06-06-02` の `<verify>` での重複実行を排除することで実行時間を大幅に短縮できる。
4. **フェーズ目標の達成可能性**
   - 上記の指摘事項（特に `06-03` の `W05b` 発火手順・合成画像 PDF 化・設定エラー観測方法、および `06-04-01` の `<verify>` コマンド修正）を反映すれば、Phase 6 の全要件（`REL-01`、`DOC-01`、および上流繰越し UAT の完全クローズ）は確実に達成可能である。
