---
quick_id: 260607-ccz
type: execute
wave: 1
depends_on: []
files_modified:
  - pagefolio/ocr_dialog.py
  - tests/test_ocr.py
  - 開発履歴.md
autonomous: false
requirements:
  - QUICK-260607-ccz
user_setup: []

must_haves:
  truths:
    - "OCR 抽出画面（OCRDialog）にプロバイダ表示行の近くへ「⚙ LLM 設定…」ボタンが表示される"
    - "ボタンを押すと既存 LLMConfigDialog が開き、プロバイダ・モデルを変更できる"
    - "LLMConfigDialog で適用すると app.settings が更新され _save_settings で永続化される"
    - "適用直後に OCR 画面のプロバイダ表示ラベル・LM Studio 欄・セッションキー欄が再評価され、表示/非表示が切り替わる"
    - "適用直後に OCR 画面の provider インスタンスが新しい設定に合わせて再生成される"
    - "OCR 実行中（_started かつ未完了）はプロバイダ変更ボタンが無効化され、設定が書き換わらない"
    - "api_key 系の値は settings へ流入しない（既存ガード T-05-12/T-05-17 を維持）"
  artifacts:
    - path: "pagefolio/ocr_dialog.py"
      provides: "_open_llm_config メソッド・LLM 設定ボタン・適用後ライブ更新メソッド _apply_llm_settings"
      contains: "_open_llm_config"
    - path: "tests/test_ocr.py"
      provides: "ライブ更新ロジック（_apply_llm_settings 相当）の単体テスト"
      contains: "TestOcrDialogLlmConfig"
  key_links:
    - from: "pagefolio/ocr_dialog.py OCRDialog._open_llm_config"
      to: "pagefolio.dialogs.llm_config.LLMConfigDialog"
      via: "on_apply コールバック経由で LLMConfigDialog を開く"
      pattern: "LLMConfigDialog"
    - from: "pagefolio/ocr_dialog.py on_apply(_apply_llm_settings)"
      to: "pagefolio.settings._save_settings"
      via: "app.settings 更新後に _save_settings で永続化"
      pattern: "_save_settings"
    - from: "pagefolio/ocr_dialog.py _apply_llm_settings"
      to: "プロバイダ表示ラベル / LM Studio 欄(sf,mf) / セッションキー欄(_key_frame)"
      via: "pack/pack_forget による可視性再評価"
      pattern: "pack_forget"
---

<objective>
OCR 抽出画面（OCRDialog）に「⚙ LLM 設定…」ボタンを追加し、既存の LLMConfigDialog を再利用してプロバイダ・モデルを変更可能にする。適用後は OCRDialog 内のフィールド（プロバイダ表示ラベル・LM Studio 欄・セッションキー欄・provider インスタンス）をローカルにライブ更新する。

これは Phase 05-05 の UAT（human-verify）中に発見された不具合の修正。言語キー `ocr_open_llm_config` が ja/en に定義済みなのにコードから一切使われていない孤立文字列であり、「OCR 抽出画面から LLM 設定を開く」設計意図が未実装で残っていたことが根本原因。

Purpose: OCR 抽出画面を一度閉じて設定ダイアログを開き直さなくても、その場でプロバイダ・モデルを切り替えられるようにする。LM Studio で開いた OCR 画面から Claude へ（またはその逆へ）即座に切り替えられる。
Output: pagefolio/ocr_dialog.py に LLM 設定ボタンと適用後ライブ更新ロジックを追加。tests/test_ocr.py にライブ更新ロジックの単体テストを追加。開発履歴.md に追記。

実装上の重要な前提（調査で確定済み・誤情報の訂正含む）:
- 設定永続化は `app._save_settings(...)` ではなく **モジュール関数** `pagefolio.settings._save_settings(settings)` を使う（app に `_save_settings` メソッドは存在しない。app.py も `from pagefolio.settings import _save_settings` 経由で `_save_settings(self.settings)` を呼んでいる）。OCRDialog でも `from pagefolio.settings import _save_settings` を関数内 import して使う。
- `_provider_display_name()` / `_is_cloud_provider()` / `_needs_session_key()` は `self.app.settings.get("ocr_provider")` を読むため、settings 更新後に再評価すれば正しい結果を返す。
- provider 表示ラベルは現状 `_build` 内のローカルな `tk.Label(prov_row, text=self._provider_display_name(), ...)` で、後から更新できない。self 属性（例 `self._provider_value_label`）に保持するリファクタが必要。
- LM Studio 欄は `_build` 内ローカル変数 `sf`/`mf`、セッションキー欄は既存 `self._key_frame`。`sf`/`mf` も self 属性化して可視性を再評価できるようにする。
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

# 修正対象の主ファイル（全体を読む）
@pagefolio/ocr_dialog.py

# LLMConfigDialog の起動パターン（手本）・契約
# settings.py _open_llm_config(158-173): LLMConfigDialog(parent, current_settings, on_apply=..., font_func=..., lang=...)
@pagefolio/dialogs/settings.py

# LLMConfigDialog コンストラクタ署名・on_apply が渡す llm_settings の内容（api_key 系を含まない）
@pagefolio/dialogs/llm_config.py
</context>

<interface_context>
## LLMConfigDialog コンストラクタ署名（pagefolio/dialogs/llm_config.py 37-44 行）

```
LLMConfigDialog(
    parent,            # tk parent（= OCRDialog の self）
    current_settings,  # dict（= self.app.settings を渡す）
    on_apply,          # def on_apply(llm_settings: dict): ...
    font_func=None,    # = self._font
    lang="ja",
)
```

- ダイアログは `grab_set()` でモーダル。`_apply()` で `self.destroy()` 後に `on_apply(llm_settings)` を呼ぶ。
- `llm_settings` に含まれるキー（llm_config.py 598-645 の `_apply`）: `ocr_provider`, `lm_studio_url`, `lm_studio_model`, `claude_model`, `ocr_effort`, `ocr_scale`, `ocr_timeout`, `ocr_max_tokens`, `ocr_temperature`, `ocr_concurrency`。
- **api_key 系キーは llm_settings に絶対に含まれない**（T-05-12 ガード）。よって `app.settings.update(llm_settings)` しても機密キーは流入しない。

## settings.py 158-173 の起動パターン（手本）

```
def _open_llm_config(self):
    from pagefolio.dialogs.llm_config import LLMConfigDialog
    lang = self.current_settings.get("lang", "ja")
    def on_apply(llm_settings):
        self.current_settings.update(llm_settings)
    LLMConfigDialog(self, self.current_settings, on_apply=on_apply,
                    font_func=self._font, lang=lang)
```

## 永続化（モジュール関数・app メソッドではない）

```
from pagefolio.settings import _save_settings   # 関数内 import
_save_settings(self.app.settings)               # 機密キー除外は _save_settings 内部で実施済み
```

## OCRDialog 側の既存ヘルパー / 属性（pagefolio/ocr_dialog.py）

- `self.app`（PDFEditorApp。`app.settings` / `app._session_api_keys` を持つ）
- `self._font`（フォントヘルパー）、`self._L`（言語辞書。`self._L["ocr_open_llm_config"]` で "⚙ LLM 設定…" を取得）
- `self._provider_display_name()`（484）, `self._is_cloud_provider()`（499）, `self._needs_session_key()`（541）— いずれも `self.app.settings.get("ocr_provider")` を読む
- provider 依存 UI: プロバイダ表示行 `prov_row`（123-138。値ラベルはローカル）、LM Studio 欄 `sf`/`mf`（171-219。ローカル変数）、セッションキー欄 `self._key_frame`（337-357。既存 self 属性）
- `self._started` / `self._done`（実行状態フラグ）、`self.run_btn`（実行ボタン）
- provider 再生成の既存ロジックは `_on_run`（660-671）にあり: claude は `build_provider(self.app.settings, api_key=...)`、それ以外は `LMStudioProvider(...)`。ライブ更新ではこの「設定からの再生成」を流用する。

## 言語キー（既存・追加不要）

`ocr_open_llm_config`: ja="⚙ LLM 設定…"（lang.py 342）/ en="⚙ LLM Settings…"（lang.py 689）。両辞書に定義済みのため新規追加は不要。
</interface_context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: provider 依存ラベル/欄を self 属性化し、LLM 設定ボタンとライブ更新メソッドを追加する</name>
  <files>pagefolio/ocr_dialog.py</files>
  <behavior>
    - `_open_llm_config()` 呼び出しで LLMConfigDialog が `parent=self`・`current_settings=self.app.settings`・`on_apply` 付きで生成される（実 Tkinter ではなくモジュール差し替えで検証可能な構造にする）。
    - on_apply（= `_apply_llm_settings(llm_settings)`）実行後: `self.app.settings` が llm_settings の内容で更新されている。
    - `_apply_llm_settings` 実行後: `_save_settings` が `self.app.settings` で1回呼ばれる。
    - `_apply_llm_settings` 実行後: ocr_provider が "claude" なら provider 表示ラベルが claude 表示名・LM Studio 欄(sf/mf)が非表示・セッションキー欄(_key_frame)は env 未設定なら表示。"lmstudio"/"off" なら逆。
    - 実行中（`self._started and not self._done`）に `_open_llm_config` が呼ばれても LLMConfigDialog を開かず即 return する（プロバイダ変更ガード）。
  </behavior>
  <action>
    pagefolio/ocr_dialog.py を以下のとおり改修する。CLAUDE.md 規約厳守（テーマ色は `C[...]`、フォントは `self._font(...)`、裸 except 禁止）。

    (1) provider 表示値ラベルの self 属性化:
    `_build` 内のプロバイダ表示行（現 132-138 行付近）の値ラベル（`text=self._provider_display_name()` の `tk.Label`）をローカルではなく `self._provider_value_label = tk.Label(...)` として保持する。スタイルは現状維持（fg=`C["ACCENT"]`, font=`self._font(-1, "bold")`）。

    (2) LM Studio 欄の self 属性化:
    現在ローカル変数の `sf`（サーバ欄フレーム・現 171 行）と `mf`（モデル欄フレーム・現 196 行）を `self._lmstudio_server_frame` / `self._lmstudio_model_frame` として保持する。pack 判定（`show_lmstudio_fields = not self._is_cloud_provider()`）は現状維持。後段で参照する子ウィジェット（既存の `self.model_combo` 等）はそのまま。

    (3) LLM 設定ボタンの追加:
    プロバイダ表示行（`prov_row`）内、値ラベルの右隣に「⚙ LLM 設定…」ボタンを配置する。`ttk.Button(prov_row, text=self._L["ocr_open_llm_config"], command=self._open_llm_config)` を `pack(side="left", padx=(12, 0))` で追加。CLAUDE.md のボタンスタイル規約に従い通常操作なので style は付けない（既定 "TButton"）。このボタン参照を `self._llm_config_btn` に保持する（実行中の無効化に使う）。

    (4) `_open_llm_config` メソッドの新設:
    `from pagefolio.dialogs.llm_config import LLMConfigDialog` を関数内 import（既存 `_start_ocr` も関数内 import 前例あり・循環 import 回避）。先頭で実行中ガード `if self._started and not self._done: return`。`lang = self.app.settings.get("lang", "ja")` を取得。`LLMConfigDialog(self, self.app.settings, on_apply=self._apply_llm_settings, font_func=self._font, lang=lang)` を生成する。settings.py 158-173 の手本に倣う。

    (5) `_apply_llm_settings(self, llm_settings)` メソッドの新設（ライブ更新の中核）:
      a. `self.app.settings.update(llm_settings)` で設定を反映（llm_settings に api_key 系は含まれないため T-05-12 ガード維持。settings 更新は dict.update で破壊的に行い、ダイアログ全体の `_rebuild_ui` は呼ばない）。
      b. `from pagefolio.settings import _save_settings`（関数内 import）して `_save_settings(self.app.settings)` で永続化（機密キー除外は _save_settings 内部実施済み）。
      c. プロバイダ表示ラベル更新: `self._provider_value_label.configure(text=self._provider_display_name())`。
      d. LM Studio 欄の可視性再評価: `show = not self._is_cloud_provider()` を計算し、`self._lmstudio_server_frame` / `self._lmstudio_model_frame` を `pack(fill="x", padx=16, pady=...)`（元の pady を踏襲: server は (6,2)、model は 2）または `pack_forget()` で切替。元の pack 引数（padx=16）と pady を踏襲すること。
      e. セッションキー欄の可視性再評価: `self._needs_session_key()` が True なら `self._key_frame.pack(fill="x", padx=16, pady=(4, 0))`、False なら `self._key_frame.pack_forget()`。元の pack 引数を踏襲。
      f. provider インスタンスの再生成: `_on_run`（660-671）の再生成ロジックを参考に、新しい `ocr_provider` に応じて self.provider を作り直す。claude なら `from pagefolio.ocr import build_provider, _resolve_api_key` と `from pagefolio.ocr_providers import OCRAPIKeyError` を関数内 import し、`session_keys = getattr(self.app, "_session_api_keys", {})` → `try: api_key = _resolve_api_key("claude", session_keys) except OCRAPIKeyError: api_key = ""` → `self.provider = build_provider(self.app.settings, api_key=api_key)`。それ以外（lmstudio/off）は `from pagefolio.ocr_providers import LMStudioProvider` で `self.provider = LMStudioProvider(url=self.app.settings.get("lm_studio_url", "http://localhost:1234"), model=self.app.settings.get("lm_studio_model", ""), timeout=int(self.app.settings.get("ocr_timeout", 120)), max_tokens=int(self.app.settings.get("ocr_max_tokens", -1)), temperature=float(self.app.settings.get("ocr_temperature", 0.1)))`。これにより `_fetch_models` や `_on_run` が新 provider を使う。
      g. provider 再生成で参照される provider 由来の UI 変数（`self.model_var` / `self.url_var`）も settings に合わせて更新する（lmstudio 時のみ。`self.url_var.set(...)` / `self.model_var.set(...)`）。claude 時は LM Studio 欄が非表示なので変更不要。
      h. 例外時にダイアログ自体は壊さない: f の provider 再生成は `try/except (ValueError, Exception) as e:` で囲み（裸 except 禁止）、失敗時は `logger.error(...)` + `self.progress_var.set(...)`（既存文言が無ければ簡潔な日本語メッセージ）に留め、ダイアログは閉じない。

    (6) 実行中のボタン無効化:
    `_on_run` の実行開始時（`self._started = True` の直後・現 607-609 付近）に `self._llm_config_btn.state(["disabled"])` を追加。`_clear_text`（実行状態リセット時・現 477 付近で run_btn を `!disabled` に戻している箇所）に `self._llm_config_btn.state(["!disabled"])` を追加して再有効化する。`_finish_complete` 等の完了系で run_btn を触っていない場合でも、`_clear_text` 経由で再押下可能になるため整合する（必要なら `_finish_complete` でも `!disabled` に戻してよいが、最小変更で `_clear_text` のみで足りるか確認のうえ実装）。

    ライブ更新では OCRDialog を破棄する操作（_rebuild_ui 等）は一切行わないこと（ダイアログ消失防止）。
  </action>
  <verify>
    <automated>cd C:/Users/shdwf/work/project/PageFolio; ruff check . ; ruff format --check .</automated>
  </verify>
  <done>
    - pagefolio/ocr_dialog.py に `_open_llm_config` と `_apply_llm_settings` が存在する。
    - prov_row に「⚙ LLM 設定…」ボタン（self._llm_config_btn）が追加されている。
    - provider 表示ラベル(`self._provider_value_label`)・LM Studio 欄(`self._lmstudio_server_frame`/`self._lmstudio_model_frame`)・セッションキー欄(`self._key_frame`)が self 属性として保持され、`_apply_llm_settings` から pack/pack_forget で切替えられる。
    - `_open_llm_config` が実行中ガード（`self._started and not self._done` で return）を持つ。
    - `_apply_llm_settings` が `self.app.settings.update` → `_save_settings` → provider 再生成の順で動く。
    - `ruff check .` と `ruff format --check .` がグリーン。
  </done>
</task>

<task type="auto">
  <name>Task 2: ライブ更新ロジックの単体テストを追加し、開発履歴を更新する</name>
  <files>tests/test_ocr.py, 開発履歴.md</files>
  <action>
    (1) tests/test_ocr.py に `class TestOcrDialogLlmConfig:` を追加する。Tkinter 実ウィジェットを生成せずロジックを検証する方針（既存 `TestStartOcrCloudGate` の `types.SimpleNamespace` + メソッドを未束縛で呼ぶ手法を踏襲）。

    検証対象は `_apply_llm_settings` のロジック本体だが、`self._provider_value_label` 等の Tkinter ウィジェット呼び出しを含むため、テスト容易性を確保するために次のいずれかを採る:
      - 推奨: `OCRDialog._apply_llm_settings` を、ウィジェット操作部分を `_refresh_provider_dependent_ui()`（pack/pack_forget・configure のみ）に切り出し、settings 更新・永続化・provider 再生成のロジックを `_apply_llm_settings` に残す。テストでは `_refresh_provider_dependent_ui` をダミー（no-op）に差し替えた fake インスタンスで `_apply_llm_settings` を未束縛呼び出しし、(a) settings が更新される (b) `_save_settings` が呼ばれる (c) self.provider が新プロバイダ種別に応じて再生成される、を検証する。`_save_settings` は `monkeypatch.setattr` で呼び出し回数を記録、`build_provider` / `LMStudioProvider` も monkeypatch で差し替える。

    テストケース（最低3件）:
      - test_apply_updates_settings: llm_settings（例 `{"ocr_provider": "claude", "claude_model": "claude-opus-4-8"}`）を渡すと fake.app.settings に反映される。
      - test_apply_persists_via_save_settings: `_save_settings` が fake.app.settings 引数で1回呼ばれる。
      - test_apply_regenerates_provider_lmstudio_and_claude: ocr_provider="lmstudio" のとき LMStudioProvider、="claude" のとき build_provider 経由 provider が self.provider にセットされる（monkeypatch で生成関数を差し替え、呼び出しを確認）。
      - （任意・推奨）test_apply_does_not_leak_api_key: llm_settings に万一 api_key 系が無いことを前提に、`_save_settings` 経由で機密キーが流入しない（settings に "anthropic_api_key" 等が含まれない）ことを確認。

    `_open_llm_config` の実行中ガードもテストする（任意・推奨）: fake.`_started=True`, `_done=False` で `_open_llm_config` を呼び、LLMConfigDialog が生成されない（monkeypatch でモジュールを差し替えカウントが 0）ことを確認。

    全テストは実 Tkinter ウィンドウを生成しないこと（CI/ヘッドレス安全性・既存方針）。`pagefolio.ocr_dialog` を import して未束縛メソッド呼び出し（`OCRDialog._apply_llm_settings(fake, llm_settings)`）で検証する。

    (2) 開発履歴.md に今回の修正を追記する。既存エントリの書式に倣い、対象ファイル表（pagefolio/ocr_dialog.py の変更内容、tests/test_ocr.py のテスト追加）と修正概要を日本語で記載。位置づけは「Phase 05-05 UAT で発見された不具合の追加修正」とする。

    バージョン番号の扱い: 本修正は 05-05（v1.4.0 マイルストーン進行中）の human-verify 中に発見された不具合修正であり、独立リリースではなく **05-05 内の追加修正** として扱う。`pagefolio/constants.py` の `APP_VERSION` バンプは行わない（マイルストーン未完了のため）。開発履歴.md には「05-05 追加修正」として記録するに留める。README.md バッジ更新も不要。この判断を SUMMARY に明記すること。
  </action>
  <verify>
    <automated>cd C:/Users/shdwf/work/project/PageFolio; python -m pytest tests/test_ocr.py -x -q ; ruff check .</automated>
  </verify>
  <done>
    - tests/test_ocr.py に `TestOcrDialogLlmConfig` が追加され、settings 更新・永続化・provider 再生成（lmstudio/claude）の各テストが pass する。
    - `python -m pytest tests/test_ocr.py` がグリーン。
    - `ruff check .` がグリーン。
    - 開発履歴.md に「05-05 追加修正（OCR 画面の LLM 設定ボタン）」が追記されている。
    - APP_VERSION は変更していない（05-05 内追加修正の方針）。
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    OCRDialog にプロバイダ表示行の右隣へ「⚙ LLM 設定…」ボタンを追加。押すと既存 LLMConfigDialog が開き、プロバイダ・モデルを変更できる。適用すると app.settings 更新 + 永続化のうえ、OCR 画面のプロバイダ表示名・LM Studio 欄・セッションキー欄・provider インスタンスがその場でライブ更新される。実行中はボタン無効化。
  </what-built>
  <how-to-verify>
    1. `python pagefolio.py` でアプリを起動し、PDF を開く。
    2. OCR（読み取り）を起動して OCRDialog を開く。プロバイダ表示行の右隣に「⚙ LLM 設定…」ボタンがあることを確認する。
    3. ボタンを押し、LLMConfigDialog が開くことを確認する。
    4. プロバイダを現在と別のもの（例: lmstudio ⇄ claude）に変更し、claude ならモデルを選び、「✓ 適用」を押す。
    5. OCRDialog に戻り、(a) プロバイダ表示名が変わっている (b) claude を選んだなら LM Studio のサーバ欄/モデル欄が消える・lmstudio なら表示される (c) claude かつ環境変数 ANTHROPIC_API_KEY 未設定ならセッションキー入力欄（マスク *）が現れる、を確認する。
    6. （任意）実 OCR を実行できるなら、変更後のプロバイダで「▶ 読み取り実行」が新しい provider を使って動作することを確認する（claude 選択時はコスト確認ダイアログが出る）。
    7. OCR 実行中に「⚙ LLM 設定…」ボタンが無効化（押せない）されていることを確認する。
    8. pagefolio_settings.json に api_key 系のキーが書き込まれていないことを確認する（機密キー流入なし）。
  </how-to-verify>
  <resume-signal>問題なければ「approved」、不具合があれば症状を記載してください。</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ユーザー入力（LLMConfigDialog）→ app.settings | プロバイダ・モデル等の選択値が settings に書き込まれる |
| app.settings → pagefolio_settings.json（_save_settings） | 永続化境界。機密キーが流入してはならない |
| OCRDialog → 外部 API（provider 再生成後の実行） | 既存のコスト確認ゲート・セッションキー経路を維持 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-CCZ-01 | Information Disclosure | `_apply_llm_settings` の `app.settings.update(llm_settings)` → `_save_settings` | mitigate | LLMConfigDialog._apply は api_key 系を llm_settings に含めない（T-05-12 既存ガード）。さらに `_save_settings` 内部の `_SENSITIVE_KEYS` 除外が最後の砦。本修正で新たに機密キーを settings へ書く処理は追加しない |
| T-CCZ-02 | Tampering | プロバイダ変更による provider 差し替え | mitigate | 実行中（`_started and not _done`）は `_open_llm_config` で即 return しボタンも無効化。実行途中の provider すり替えを防ぐ |
| T-CCZ-03 | Denial of Service | provider 再生成時の例外 | mitigate | provider 再生成を `try/except (ValueError, Exception)` で保護し、失敗時もダイアログを破棄せず logger.error + 進捗表示に留める（裸 except 禁止） |
| T-CCZ-04 | Tampering | npm/pip/cargo installs | accept | 本修正は新規パッケージ install を一切伴わない（既存モジュールの再利用のみ）。該当なし |
</threat_model>

<verification>
- `ruff check . && ruff format --check .` がグリーン（CLAUDE.md 規約）。
- `python -m pytest tests/test_ocr.py` がグリーン（新規 TestOcrDialogLlmConfig 含む）。
- `python -m pytest` 全体がグリーン（リグレッションなし）。
- `python -c "import ast; ast.parse(open('pagefolio/ocr_dialog.py', encoding='utf-8').read())"` で構文確認。
- 言語キー `ocr_open_llm_config` が `pagefolio/ocr_dialog.py` から参照されている（孤立文字列の解消）。
- pagefolio_settings.json に api_key 系キーが流入しない（_save_settings ガード維持）。
</verification>

<success_criteria>
1. OCRDialog のプロバイダ表示行に「⚙ LLM 設定…」ボタンが表示される。
2. ボタンから既存 LLMConfigDialog が開き、プロバイダ・モデルを変更できる。
3. 適用後、app.settings 更新 + _save_settings 永続化 + OCR 画面のプロバイダ表示名/LM Studio 欄/セッションキー欄/provider インスタンスがライブ更新される（OCRDialog は破棄されない）。
4. OCR 実行中はボタンが無効化され、プロバイダ変更が阻止される。
5. api_key 系の値が settings に流入しない（T-05-12/T-05-17 ガード維持）。
6. ruff・pytest がグリーン、開発履歴.md 追記済み、APP_VERSION は据え置き（05-05 内追加修正）。
</success_criteria>

<output>
Create `.planning/quick/260607-ccz-ocr-llm-llmconfigdialog/260607-ccz-SUMMARY.md` when done
</output>
