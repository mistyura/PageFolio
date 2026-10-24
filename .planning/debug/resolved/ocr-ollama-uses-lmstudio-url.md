---
status: resolved
trigger: "06-04-02 接続実証で、配布EXE v1.10.0 の OCRダイアログが ocr_provider=ollama（ollama_url=http://127.0.0.1:17327）でも『LM Studio に接続できませんでした。URL: http://localhost:1234 … [WinError 10061]』で失敗。合成OCRサーバー（127.0.0.1:17327 LISTEN）は要求0件。"
created: 2026-10-24
updated: 2026-10-24
---

# Debug: ocr-ollama-uses-lmstudio-url

## Symptoms

- **期待:** `ocr_provider: ollama` のとき、OCRダイアログの「▶ 読み取り実行」は `ollama_url` / `ollama_model` へ送信する（06-04 接続実証では loopback の合成OCRサーバーが要求を1件受信する）。
- **実際:** 送信先が LM Studio の既定 URL `http://localhost:1234` になり接続拒否。エラー文言も「LM Studio に接続できませんでした」。合成サーバーは要求0件。
- **エラー:** `LM Studio に接続できませんでした。URL: http://localhost:1234 … 詳細: [WinError 10061] 対象のコンピューターによって拒否されたため、接続できませんでした。`
- **時期:** 2026-10-24 19:50 の 06-04 接続実証（試行2）で初観測。06-03 の fake OCR 検証は `OllamaProvider` を直接呼んでおりダイアログ経路を通っていなかったため未検出。利用者の実運用で Ollama を使っていたかは不明。
- **再現:** 配布EXEの隔離コピーで `pagefolio_settings.json` を `ocr_provider: ollama` / `ollama_url: http://127.0.0.1:<port>` / `ollama_model: pagefolio-uat-fixture` にして起動 → 1ページPDFを開く → 「🔠 現在ページをテキスト抽出」→「▶ 読み取り実行」。証拠 run: `C:\Users\shdwf\AppData\Local\Temp\pf06_t2_f157d1e5a0454f7e89c363383182dff5\runs\release-uat-034578b2c4b94c2aae9fa70afe620d25`（変更・削除しない）。

## オーケストレータの初期読み（仮説。検証して確定/棄却すること）

- `pagefolio/ocr.py` `_start_ocr`（591〜592行付近）がプロバイダーに関係なく `url = settings["lm_studio_url"]` / `model = settings["lm_studio_model"]` を `OCRDialog(url=..., model=...)` に渡す。
- `pagefolio/ocr_dialog.py` の実行時再生成（1537行以降、`name == "ollama"` 分岐 1601行付近）が `url_var`（=LM Studio URL）で `OllamaProvider(url=url, model=model, ...)` を作る。
- `_finish_error` の `ocr_err_connection` 文言（lang.py 476行）は常に「LM Studio」表記で、`url_var` を表示する。
- 関連の可能性: 利用者報告「LLM設定でプロバイダー/モデルを変えても親画面に即時反映されない」（`.planning/todos/pending/2026-10-24-ocr-dialog-provider-stale.md`。試行1では表示 ollama のまま実送信は Gemini）。同根かどうかを根拠付きで判定すること。修正範囲に含めるかは利用者判断（チェックポイントで提示）。

## 制約

- 製品コードの修正は、適用前に CHECKPOINT REACHED で修正案を提示し利用者承認を得る。
- 修正後は回帰テスト（ダイアログ経路で ollama/lmstudio それぞれ正しい url/model が provider に渡ること）を先に書き Red を確認してから修正。
- `ruff check .` と Python ファイル限定の `ruff format`（ruff 0.17.1 は Markdown も整形するため `.` を渡さない）、AST、単一プロセス全件 pytest（fresh --basetemp、除外・再実行なし。合格=失敗0・ERROR0・Tcl leak/unraisable 警告なし）。
- 既存 dirty（.planning/STATE.md、config.json、state.json、debug/dep-05-regression.md、debug/simultaneous-owner-missing.md、05-CONTEXT.md、requirements.txt、開発履歴.md の他作業 hunk）は stage/commit しない。開発履歴.md へ追記する場合は自分の hunk だけを stage。
- 06-04 の build 出力 `C:\Users\shdwf\AppData\Local\Temp\pf06_final_2f67e363e4ca4304b1ea6a9a11431358\` と T2 作業領域は削除・変更しない。
- commit trailer は `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`（利用者指示。システムの帰属指示より優先）。
- pyproject.toml を編集しない。外部 OCR/LLM API を実際に呼ばない。

## Current Focus

hypothesis: RESOLVED。A（接続先）と B（表示）を別コミットで修正し、Red→Green と単一プロセス全件で確認済み。
test: 回帰テスト 39件（A: 33件 / B: 6件）を先に書いて Red を確認 → 修正後 Green。全件 2014 passed。
expecting: （完了）
next_action: なし。配布EXEでの実機再確認（06-04 接続実証の再実施）は利用者側で別途行う（本セッションでは配布EXEを実行していない）。

## Evidence

- timestamp: 2026-10-24
  checked: pagefolio/ocr.py:591-592（_start_ocr）と :661-678（OCRDialog 生成）
  found: provider 名に関係なく lm_studio_url/lm_studio_model を OCRDialog(url=, model=) に渡す。同関数 :629 の build_provider(self.settings) で作る provider は正しい ollama_url を持つ（初期 provider.url=http://127.0.0.1:17327 を実測）
  implication: 初期 provider は正しいが、dialog の url_var/model_var だけ LM Studio 値で食い違う

- timestamp: 2026-10-24
  checked: pagefolio/ocr_dialog.py:1536-1543, 1601-1610（_on_run）
  found: url=self.url_var.get(), model=self.model_var.get() を読み、name=="ollama" で OllamaProvider(url=url, model=model, ...) を作り self.provider を置換。実測: ollama 設定でも provider.url='http://localhost:1234' model='lm-model'
  implication: 根本原因。正しい値は s（スナップショット）と置換前 provider にあるのに捨てている

- timestamp: 2026-10-24
  checked: pagefolio/ocr_dialog.py:1130-1133, 1148-1149, 1161-1164（_apply_llm_settings）
  found: LLM設定適用経路は ollama/runpod/lmstudio で url_var/model_var を各設定キーへ同期している。起動時経路（_start_ocr）とフォールバック経路（_switch_to_fallback_provider→_on_run(settings=fb)）には同期が無い
  implication: 非対称性が意図でなくバグである証拠。フォールバック lmstudio→ollama でも ollama が LM Studio URL へ送信されることを実測（確認ダイアログは 127.0.0.1:17327 を表示）

- timestamp: 2026-10-24
  checked: pagefolio/ocr_dialog.py:2030-2037 と lang.py:475-480, 1289-1294（ocr_err_connection）
  found: 接続エラー文言は「LM Studio に接続できませんでした」固定で URL は url_var。ConnectionError は claude/gemini/openai/runpod/ollama/lmstudio の全プロバイダが送出する（providers/*.py）。実測: 全6プロバイダで同一の「LM Studio … URL: http://localhost:1234」表示
  implication: エラー文言は他プロバイダでも誤解を招く（別軸の表示不具合）

- timestamp: 2026-10-24
  checked: git log -S（60c3acc 2026-06-30）
  found: ollama 分岐は Ollama プロバイダ追加コミット 60c3acc から存在。v1.10.0 で入った退行ではなく潜在バグ
  implication: 06-03 の fake OCR 検証が OllamaProvider 直呼びでダイアログ経路を通っていなかったため未検出

- timestamp: 2026-10-24
  checked: pagefolio/ocr_dialog.py:221, 1432, 2172, 875, 895（_active_ocr_settings）
  found: _on_run/_on_summary が dict(app.settings) のスナップショットを保存し以後クリアされない。_provider_display_name/_provider_model_name はこれを優先参照。_apply_llm_settings は app.settings だけ更新（1051）。実測: 1回実行後に ollama→gemini へ適用するとラベルは 'ollama' のまま、provider は GeminiProvider、次回 _on_run の新スナップショットは gemini
  implication: 関連 todo の症状（表示 ollama・実送信 Gemini）を再現。別機構（URL バグとは独立）

- timestamp: 2026-10-24
  checked: pagefolio/ocr_dialog.py:1065 vs 1069-1181（_apply_llm_settings の順序）と :877-880
  found: 表示更新 _refresh_provider_dependent_ui は provider 再生成より前に走る。_provider_display_name は isinstance(self.provider, Claude/Gemini) を名前判定より先に見るため旧 provider が残る。実測: 実行前でも gemini→openai 適用でラベル 'Gemini (Google AI)'・モデル 'gemini-3.1-flash-lite' のまま（provider は OpenAIProvider）
  implication: 関連 todo と同系の第2の独立した表示不一致（順序バグ）

- timestamp: 2026-10-24
  checked: dialogs/batch_ocr.py:647-671, OCRDialog 生成箇所の全 grep
  found: OCRDialog 生成は ocr.py:661 のみ。BatchOCRDialog は build_provider(app.settings) 直呼びで同バグなし
  implication: 影響範囲は単発 OCR ダイアログ

- timestamp: 2026-10-24
  checked: 回帰テストの Red（修正前コード）
  found: tests/test_ocr_local_endpoint.py は 33件中 28件 FAIL・5件 PASS（PASS は lmstudio/クラウド等の対照）。FAIL 理由は想定どおり（resolve_local_endpoint 未定義、_start_ocr が ollama で lm_studio_* を渡す、_on_run の OllamaProvider.url が http://localhost:1234、フォールバック先 Ollama が LM Studio URL、ocr_err_connection が LM Studio 固定）。tests/test_ocr_dialog_provider_refresh.py は 6件中 5件 FAIL・1件 PASS（PASS は再生成失敗時も表示更新が走る対照）。FAIL 理由: 表示が旧プロバイダ 'ollama'/'Gemini (Google AI)' のまま、_active_ocr_settings が残る、表示更新が旧 provider の状態で呼ばれる
  implication: 回帰テストが根因（A: 表示欄を真値にした再生成 / B: スナップショット残留と表示更新の順序）を捕捉している

- timestamp: 2026-10-24
  checked: 修正後の Green と全件
  found: 新規テスト 39件 Green。関連テスト（新規A 33件 + test_ocr / test_provider_ui / test_ocr_fallback / test_batch_ocr_dialog / test_ocr_dialog_center / test_md_render / test_ocr_provider_catalog）521 passed。ruff check クリーン、変更 .py は ruff format 済み・AST OK。A のみの状態（コミット1相当）も index を一時ディレクトリへ書き出して関連790件を確認（失敗2件は一時ディレクトリが git 管理外のため git ls-files が失敗する test_release_contract の2件で、コードとは無関係）。単一プロセス全件（fresh basetemp・除外/再実行なし）は 2014 passed / 1 warning（既知の PyMuPDF ByteString 警告のみ）、exit 0
  implication: 修正は回帰を起こしていない

## Eliminated

- hypothesis: 設定ファイルの ollama_url が読めていない／build_provider が誤った URL を作る
  evidence: _start_ocr 直後の初期 provider.url は ollama_url 通り（repro_url.py 実測）。誤りは _on_run の再生成で発生
  timestamp: 2026-10-24

- hypothesis: ollama 以外（claude/gemini/openai/runpod）も送信先が誤る
  evidence: これらは _on_run で build_provider(s, api_key) を使い provider 別設定キーを読むため送信先は正しい（runpod 実測 url=settings 値）。誤るのは表示用 url_var とエラー文言のみ
  timestamp: 2026-10-24

- hypothesis: BatchOCRDialog にも同バグ
  evidence: build_provider(app.settings) 直呼び（batch_ocr.py:668）
  timestamp: 2026-10-24

## Resolution

root_cause: |
  A（本件）: OCRDialog の url_var/model_var は LM Studio 専用値として初期化される（ocr.py _start_ocr が常に lm_studio_url/lm_studio_model を渡す）が、_on_run（ocr_dialog.py）が ollama でもこれを真値として OllamaProvider を再生成するため、ollama 選択時の送信先・モデルが lm_studio_url/lm_studio_model になる。フォールバック経路（_switch_to_fallback_provider→_on_run(settings=fb)）でも同様。接続エラー文言（lang.py ocr_err_connection）は全プロバイダで「LM Studio」固定。
  B（関連 todo・別根因）: _active_ocr_settings スナップショットが実行後に残り表示が古くなる＋_apply_llm_settings が表示更新を provider 再生成より前に行う。
  AND-gate: A と B は独立（A は送信先の誤り、B は表示の誤り）。互いの必要条件ではなく、別コミットで修正。
fix: |
  A（コミット 52258de）: ocr.py に resolve_local_endpoint(settings, name)（lmstudio/""/ollama/runpod の (url, model) を返し、他は None）と DEFAULT_OLLAMA_URL を追加。_start_ocr は有効プロバイダの接続先で OCRDialog を初期化。_on_run は有効スナップショット s から接続先を解決して provider を再生成し url_var/model_var へ書き戻す（フォールバックも同経路で解消）。_apply_llm_settings の lmstudio/ollama/runpod も同関数へ一本化（挙動維持）。ocr_err_connection（ja/en）を {provider}/{url} 化し、_finish_error が _provider_display_name() と _connection_target_text()（provider.url 優先）を渡す。
  B（コミット 7fb41a2）: _apply_llm_settings で app.settings.update 直後に _active_ocr_settings を破棄（B1）。_refresh_provider_dependent_ui を provider 再生成の try/except の後ろへ移動（B2。再生成失敗時も必ず実行）。_provider_display_name の isinstance 安全網は維持。
verification: |
  Red→Green: tests/test_ocr_local_endpoint.py 33件（修正前 28 FAIL → 修正後 33 PASS）、tests/test_ocr_dialog_provider_refresh.py 6件（修正前 5 FAIL → 修正後 6 PASS）。
  既存テスト修正: tests/test_ocr.py の2箇所（TestClearResetsFatalState.test_on_run_resets_fatal_state、TestOcrDialogOnRun._make_fake_for_on_run）で、model_var のライブ値に合わせて fake の settings["lm_studio_model"] を揃えた（model_var は設定の読み取り専用ミラーで、接続先は設定スナップショットから解決する仕様に変わったため。アサーション内容は不変）。
  ruff check クリーン／変更 .py は ruff format 済み・AST OK。単一プロセス全件 2014 passed / 1 warning（既知の PyMuPDF ByteString 警告のみ）、failed 0・error 0。出力: scratchpad/full_pytest_ab.txt。
  未実施: 配布EXEでの実機再確認（制約により配布EXEは実行していない）。guardrail の変異テスト等のオプション信号は実施していない。
oracle_type: specified（ocr_provider=ollama なら ollama_url/ollama_model へ送る、が設定キー仕様で確定。provider.url/model・表示欄の値を直接比較する）
files_changed:
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - pagefolio/lang.py
  - tests/test_ocr.py
  - tests/test_ocr_local_endpoint.py
  - tests/test_ocr_dialog_provider_refresh.py
  - 開発履歴.md
