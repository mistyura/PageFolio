---
phase: quick-260610-qqq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pagefolio/ocr.py
  - pagefolio/ocr_dialog.py
  - pagefolio/dialogs/llm_config.py
  - pagefolio/constants.py
  - tests/test_ocr.py
  - README.md
  - 開発履歴.md
  - .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md
autonomous: true
requirements: [H-1, H-2, H-3, H-4, H-5]
must_haves:
  truths:
    - "既定設定（ocr_max_tokens=-1）でも build_provider が claude/gemini に正の max_tokens（4096）を渡す"
    - "Tesseract / プラグインプロバイダ選択時に self.provider が LMStudioProvider へ置換されない"
    - "プロバイダ切替後に self.concurrency が provider.max_concurrency 以下へ再クランプされる"
    - "LLM 設定ダイアログのプロバイダ別セクションが「適用/キャンセル」ボタンより上に表示される"
    - "プロバイダ/モデル切替時にダイアログ高さが再計算されボタンが見切れない"
    - "APP_VERSION / README バッジ / 開発履歴.md が v1.4.1 で一致する"
  artifacts:
    - path: "pagefolio/ocr.py"
      provides: "build_provider の claude/gemini 分岐での max_tokens クランプ"
      contains: "build_provider"
    - path: "pagefolio/ocr_dialog.py"
      provides: "tesseract/プラグインを build_provider で再生成する _on_run / _apply_llm_settings、tesseract 表示名分岐、concurrency 再クランプ"
    - path: "pagefolio/dialogs/llm_config.py"
      provides: "セクションの before アンカー配置と切替時のダイアログ高さ再計算"
    - path: "tests/test_ocr.py"
      provides: "H-1 クランプ回帰テスト"
      contains: "build_provider"
    - path: "pagefolio/constants.py"
      provides: "APP_VERSION = v1.4.1"
      contains: "v1.4.1"
  key_links:
    - from: "pagefolio/ocr_dialog.py:_on_run"
      to: "pagefolio.ocr.build_provider"
      via: "tesseract/プラグイン分岐での provider 再生成"
      pattern: "build_provider"
    - from: "pagefolio/dialogs/llm_config.py:_on_provider_change"
      to: "self.scale_row"
      via: "pack(..., before=self.scale_row)"
      pattern: "before=self\\.scale_row"
---

<objective>
v1.4.0 リリースレビュー（260610-aaa-REVIEW.md）で検出した高優先度指摘 H-1〜H-5 を
v1.4.1 ホットフィックスとして修正する。OCR バックエンドの 2 件（H-1 max_tokens
クランプ・H-2 プロバイダ置換）と並列度再評価（H-3）、LLM 設定ダイアログの UI 崩れ
2 件（H-4 セクション配置・H-5 リサイズ不全）を解消し、バージョンを 1.4.1 に更新する。

Purpose: クラウド OCR（Claude/Gemini）が既定設定で 400 になる、Tesseract 選択時に
画像が外部 LM Studio へ送信される、設定ダイアログのボタンが見切れる、という
リリース直後の致命的不具合をホットフィックスで解消する。
Output: 修正済みソース 3 ファイル + 回帰テスト + バージョン更新 + REVIEW.md 完了マーク。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md
@./CLAUDE.md
@pagefolio/ocr.py
@pagefolio/ocr_dialog.py
@pagefolio/dialogs/llm_config.py
@pagefolio/constants.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: H-1/H-2/H-3 — OCR バックエンド修正（max_tokens クランプ・プロバイダ置換防止・並列度再クランプ）</name>
  <files>pagefolio/ocr.py, pagefolio/ocr_dialog.py, tests/test_ocr.py</files>
  <behavior>
    - H-1 回帰テスト（tests/test_ocr.py の build_provider 系に追加）:
      settings={"ocr_provider":"claude", "ocr_max_tokens":-1} で build_provider を呼ぶと
      返る ClaudeProvider の max_tokens == 4096。gemini でも同様に GeminiProvider.max_tokens == 4096。
      0 を渡した場合も 4096 にクランプされること（mt <= 0 の境界）。
    - H-1 既存挙動維持: ocr_max_tokens に正値（例 2048）を渡したときは claude/gemini とも
      その値（2048）がそのまま渡ること（クランプは mt <= 0 のときのみ）。
  </behavior>
  <action>
    H-1（pagefolio/ocr.py の build_provider）: claude 分岐と gemini 分岐で、現在
    `max_tokens=int(settings.get("ocr_max_tokens", 4096))` としている箇所を、いったん
    `mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))` で取得し、
    `mt = 4096 if mt <= 0 else mt` のクランプを噛ませてから ClaudeProvider / GeminiProvider
    の max_tokens に渡す。lmstudio 分岐（-1 をモデル最大値委譲として許容する）は変更しないこと。
    クランプ理由（-1 は LM Studio 専用・Anthropic/Gemini は正の整数必須）をコメントで明記する。

    H-2（pagefolio/ocr_dialog.py の _on_run 末尾分岐・879-889 行付近、および
    _apply_llm_settings の else 分岐・661-670 行付近）: 現在 `else:` で LMStudioProvider を
    無条件再生成しているため tesseract やプラグイン登録名も巻き込まれる。`else:` を
    `elif name in ("lmstudio", "", "off"):` に変更して LMStudioProvider 再生成は
    lmstudio/off/空文字に限定し、それ以外の名前（tesseract・プラグイン登録名）には
    続けて新しい最終分岐を追加して `self.provider = build_provider(self.app.settings, ...)`
    で再生成する（claude/gemini と同じく plugin_manager=getattr(self.app, "plugin_manager", None)
    を渡す）。build_provider は ocr.py から既に import 済み（_on_run）／関数内 import 済み
    （_apply_llm_settings は from pagefolio.ocr import build_provider を分岐内で追加）。
    _apply_llm_settings の except は H-2 と無関係に残してよいが、tesseract/プラグイン分岐も
    その try ブロック内に置くこと（provider 生成失敗を既存のエラー表示に乗せる）。

    H-2 表示名（pagefolio/ocr_dialog.py の _provider_display_name・505-520 行付近）:
    gemini 判定の後に `if name == "tesseract": return self._L["ocr_provider_name_tesseract"]`
    を追加する（このキーは lang.py の ja/en 両方に既存・L-5 で未使用と指摘されていたもの）。

    H-3（pagefolio/ocr_dialog.py の _on_run と _apply_llm_settings）: provider を再生成した
    各分岐の直後（全プロバイダ分岐が終わって self.provider が確定した後の共通位置が望ましい）で
    `self.concurrency = max(1, min(self.provider.max_concurrency, self.concurrency))` を
    実行し、切替後の provider の max_concurrency に合わせて並列度を再クランプする。
    _on_run では `self._render_queue = queue.Queue(maxsize=self.concurrency + 1)` の直前に
    入れること（バッファサイズが新しい concurrency を反映するように）。OCRProvider 派生は
    すべて max_concurrency クラス属性を持つ前提でよい。

    H-1/H-2/H-3 とも CLAUDE.md 規約に従い、裸 except を作らず、テーマ色・フォントは触らない。
  </action>
  <verify>
    <automated>cd "C:\Users\shdwf\work\project\PageFolio" && python -m pytest tests/test_ocr.py tests/test_ocr_providers.py tests/test_provider_ui.py -q</automated>
  </verify>
  <done>build_provider が claude/gemini で ocr_max_tokens<=0 を 4096 にクランプし正値はそのまま渡す回帰テストがパス。_on_run / _apply_llm_settings が lmstudio/off のみ LMStudioProvider・tesseract/プラグインは build_provider で再生成。_provider_display_name に tesseract 分岐あり。provider 再生成後に concurrency が再クランプされる。対象テスト全パス。</done>
</task>

<task type="auto">
  <name>Task 2: H-4/H-5 — LLM 設定ダイアログのセクション配置とリサイズ修正</name>
  <files>pagefolio/dialogs/llm_config.py</files>
  <action>
    REVIEW.md の指示どおり H-4 と H-5 を同一メソッド群（_build / _on_provider_change /
    _on_model_change）で同時に修正する。

    H-4（セクションがボタン行の下に出る）: 動的に pack されるプロバイダ別セクション
    （url_section_frame・claude_section_frame・gemini_section_frame・tesseract_section_frame・
    effort_frame・temperature_frame）が、静的な scale_row（374 行付近）以降の行（最大トークン・
    並列度・ステータス・ボタン行）より上に来るようアンカーする。まず _build 内で
    `scale_row = tk.Frame(...)` を `self.scale_row = tk.Frame(...)` に変更し（以降の参照も
    self.scale_row に置換）、self 属性として保持する。次に _on_provider_change 内の各
    `*_section_frame.pack(...)` および effort_frame / temperature_frame の `.pack(...)`
    呼び出しすべてに `before=self.scale_row` 引数を追加する（pack_forget はそのまま）。
    _on_model_change 内の effort_frame / temperature_frame の pack にも同様に
    `before=self.scale_row` を付ける。これにより全プロバイダ別セクションが scale_row より
    上（=ボタン行より上）に挿入される。

    H-5（切替時にリサイズされずボタンが見切れる）: __init__ の geometry 計算で使う幅 w を
    self 属性化する。__init__ の `w = max(540, int(fs * 44))` を `self._dialog_w = max(540, int(fs * 44))`
    にし、続く geometry 適用も self._dialog_w を使う形に修正する（h・配置式は据え置きでよい）。
    次にダイアログ高さを現在位置維持で再適用するヘルパー（例 `_resize_to_fit`）を追加する:
    `self.update_idletasks()` の後 `h = max(480, self.winfo_reqheight() + 20)`、
    `x = self.winfo_x()`、`y = self.winfo_y()`、`self.geometry(f"{self._dialog_w}x{h}+{x}+{y}")`。
    `tk.TclError` は try/except Exception で握り潰さず、ウィンドウ破棄レースに備える場合のみ
    `except tk.TclError: pass` の最小スコープで保護する。このヘルパーを _on_provider_change と
    _on_model_change の末尾で呼ぶ。_on_provider_change が内部で _on_model_change を呼ぶ
    経路（claude 選択時）では二重 geometry 適用になるが現在位置維持なので実害なし。

    変更後、resizable(False, False)（57 行）は維持してよい（ヘルパーが明示的に geometry を
    再適用するため固定サイズでも高さ追従する）。テーマ色・self._font は触らない。
  </action>
  <verify>
    <automated>cd "C:\Users\shdwf\work\project\PageFolio" && ruff check pagefolio/dialogs/llm_config.py && python -c "import ast; ast.parse(open('pagefolio/dialogs/llm_config.py', encoding='utf-8').read())"</automated>
  </verify>
  <done>scale_row が self.scale_row 化され、_on_provider_change / _on_model_change の全セクション pack が before=self.scale_row でアンカーされている。__init__ の幅が self._dialog_w に保持され、_on_provider_change / _on_model_change 末尾でダイアログ高さが現在位置維持で再計算・再適用される。ruff check と構文確認がパス。</done>
</task>

<task type="auto">
  <name>Task 3: バージョン更新・ドキュメント追記・REVIEW.md 完了マーク・品質ゲート</name>
  <files>pagefolio/constants.py, README.md, 開発履歴.md, .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md</files>
  <action>
    バージョン更新: pagefolio/constants.py の `APP_VERSION = "v1.4.0"` を `"v1.4.1"` に変更。
    README.md のバージョンバッジ（5 行付近 `version-v1.4.0-blue`）を `version-v1.4.1-blue` に更新。
    開発履歴.md の先頭に v1.4.1 エントリを追記し、H-1〜H-5 の修正内容（既存ルール通りの日本語）を記載する。

    REVIEW.md 完了マーク: .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md の
    H-1〜H-5 各見出し（### H-1: 〜 ### H-5:）に完了マークを追記する。各見出し末尾に ✅ を付け、
    項目本文の末尾に「対応済み（v1.4.1 / commit: <ハッシュ>）」の 1 行を追加する。コミットハッシュは
    Task 1/Task 2 のコミット後に確定するため、確定したハッシュ（短縮形）を埋めること。

    H-1 注意の申し送り: REVIEW.md「着手時の注意」に従い、H-1（max_tokens）のクランプは
    コードレビューに基づく安全側の判断であり実 API（Anthropic/Gemini）での 400 再現は
    未検証である旨を SUMMARY.md の申し送りに明記すること（クランプ自体は安全側なので実施済み）。

    最後に品質ゲートを実行: `ruff check . && ruff format .` が全パス、`pytest` が全パスすることを
    確認する。format で差分が出た場合は再コミット対象に含める。
  </action>
  <verify>
    <automated>cd "C:\Users\shdwf\work\project\PageFolio" && ruff check . && ruff format --check . && python -m pytest -q</automated>
  </verify>
  <done>APP_VERSION が v1.4.1、README バッジが v1.4.1、開発履歴.md に v1.4.1 エントリあり。REVIEW.md の H-1〜H-5 に ✅ とコミットハッシュ付き完了マークあり。ruff check / format --check と pytest 全パス。SUMMARY に H-1 実 API 未検証の申し送りあり。</done>
</task>

</tasks>

<verification>
- `python -m pytest` 全件パス（H-1 回帰テスト含む）
- `ruff check . && ruff format --check .` 全パス
- build_provider: ocr_provider=claude/gemini かつ ocr_max_tokens<=0 で provider.max_tokens==4096
- _on_run / _apply_llm_settings: provider=tesseract で self.provider が TesseractProvider（LMStudioProvider でない）
- llm_config: プロバイダ切替時にプロバイダ別セクションがボタン行より上に表示・ダイアログ高さが追従
- APP_VERSION / README バッジ / 開発履歴.md が v1.4.1 で一致
- REVIEW.md の H-1〜H-5 に完了マーク
</verification>

<success_criteria>
- H-1: 既定設定（ocr_max_tokens=-1）で Claude/Gemini provider が max_tokens=4096 を持つ（回帰テストで保証）
- H-2: tesseract / プラグインプロバイダ選択時に LMStudioProvider へ置換されず、表示名に tesseract が出る
- H-3: プロバイダ切替後に concurrency が provider.max_concurrency 以下へ再クランプされる
- H-4: LLM 設定ダイアログのプロバイダ別セクションが「適用/キャンセル」より上に表示される
- H-5: プロバイダ/モデル切替時にダイアログ高さが再計算されボタンが見切れない
- バージョン v1.4.1 で 3 箇所同期・REVIEW.md に完了マーク・品質ゲート全パス
</success_criteria>

<output>
Create `.planning/quick/260610-qqq-review-md-260610-aaa-h-1-h-5-v1-4-1/260610-qqq-SUMMARY.md` when done
</output>
