---
phase: 04-provider-abstraction
verified: 2026-06-06T12:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "CR-02: _on_run が model_var / max_tokens_var / temperature_var を読み取り LMStudioProvider を再生成する（SC-1 後方互換の復元）"
    - "CR-01: _start_ocr の build_provider 呼び出しが try/except ValueError で保護され messagebox.showerror + return でグレースフル処理される"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "ダイアログでモデルを変更してから「読み取り実行」を押し、LM Studio のログで実際に送信された model フィールドを確認する"
    expected: "ダイアログで選択したモデル名が HTTP リクエストの model フィールドに反映されている"
    why_human: "HTTP リクエストの内容を確認するには実際の LM Studio サーバへの接続が必要"
  - test: "ダイアログでタイムアウトを変更して接続を切った LM Studio に対して OCR を実行し、表示メッセージのタイムアウト秒数と実際の待機時間を比較する"
    expected: "表示される「{N}秒でタイムアウト」の N と実際の HTTP タイムアウト秒が一致する"
    why_human: "実際の HTTP タイムアウト挙動の確認は実環境での動作が必要"
---

# Phase 4: プロバイダ抽象化 検証レポート（再検証）

**フェーズゴール:** プロバイダを差し替え可能にする土台が整い、LM Studio が従来どおり動作する
**検証日時:** 2026-06-06
**ステータス:** human_needed
**再検証:** Yes — 04-04（ギャップ修正プラン）適用後の再検証

## ゴール達成状況

### 観測可能な真実（ROADMAP 成功基準）

| # | 真実 | ステータス | 根拠 |
|---|------|-----------|------|
| 1 | LM Studio で OCR を実行したとき、v1.3.0 と同じ結果・同じ UI 操作で完了する（後方互換） | VERIFIED | `_on_run`（ocr_dialog.py:459-489）が `url_var` / `model_var` / `max_tokens_var` / `temperature_var` を live 値で読み取り、`_render_next_page()` 呼び出しより前に `LMStudioProvider(url=..., model=..., timeout=self._effective_timeout, max_tokens=..., temperature=...)` として `self.provider` を再生成している。ダイアログ UI の変更が `run_parallel(self.provider, ...)` に確実に反映される。各値取得に `try/except (tk.TclError, ValueError)` でフォールバック付き。CR-02 完全修正を確認。 |
| 2 | テキストが埋め込まれたページに OCR を実行したとき、API 呼び出しが行われずに page.get_text() の結果が返される | VERIFIED | `_render_next_page`（ocr_dialog.py:518-531）が `has_embedded_text(page)` で判定し、True なら `page.get_text()` を `self.results[page_idx]` に投入して `self._skipped_pages.add(page_idx)` し `_ocr_page_indices` に追加しない。`_worker` の `run_parallel` には埋め込みページが渡されない。前回から変更なし・リグレッションなし。 |
| 3 | ワーカースレッド内で fitz.Document / get_pixmap() の直接呼び出しが一切存在しない（スレッド境界が明確） | VERIFIED | `_worker`（ocr_dialog.py:545-592）本体を全文確認済み。`fitz` / `get_pixmap` / `self.doc[` / `page_to_png_b64` の呼び出しは一切存在しない。CR-02 の修正（provider 再生成）は `_on_run`（メインスレッド）でのみ行われ、`_worker` には一切手が加えられていない。スレッド境界のリグレッションなし。 |
| 4 | 新しいプロバイダクラスをファイルに追加するだけで run_parallel() から呼び出せる（プロバイダ別並列度が受け取れる） | VERIFIED | `OCRProvider(abc.ABC)` に `ocr_image` / `list_models` 抽象メソッドと `default_concurrency=2` / `max_concurrency=8` クラス属性が定義されている（ocr_providers.py:16-55）。`run_parallel`（ocr.py:83-176）は `provider.ocr_image` と `provider.max_concurrency` のみに依存。前回から変更なし・リグレッションなし。 |

**スコア:** 4/4 真実を検証済み

### ギャップ修正の検証（CR-02 / CR-01）

#### CR-02 修正確認（ocr_dialog.py:459-489）

実装を直接確認した証拠:

- `url = self.url_var.get().strip()` — url_var 読み取り（行 462-464）
- `model = self.model_var.get().strip()` — model_var 読み取り（行 465-468）
- `raw_mt = int(self.max_tokens_var.get()); max_tokens = max(-1, min(MAX_OCR_MAX_TOKENS, raw_mt))` — max_tokens_var 読み取りとクランプ（行 469-474）
- `temperature = max(0.0, min(2.0, float(self.temperature_var.get())))` — temperature_var 読み取りとクランプ（行 475-479）
- `from pagefolio.ocr_providers import LMStudioProvider` — 関数内 import（行 481）
- `self.provider = LMStudioProvider(url=url, model=model, timeout=self._effective_timeout, max_tokens=max_tokens, temperature=temperature)` — self.provider 再生成（行 483-489）
- `self._render_next_page()` — 再生成完了後にワーカー起動（行 494）

各値取得に `except (tk.TclError, ValueError)` でフォールバック付き。裸 except なし。

#### CR-01 修正確認（ocr.py:240-251）

実装を直接確認した証拠:

- `from tkinter import messagebox` — import 追加済み（ocr.py:9）
- `try: provider = build_provider(self.settings)` — try ブロックで保護（行 241-242）
- `except ValueError as e:` — ValueError を捕捉（行 243）
- `name = self.settings.get("ocr_provider", ""); logger.error(...)` — ログ出力（行 244-245）
- `messagebox.showerror(self._t("err_title"), self._t("ocr_provider_unsupported").format(name=name), parent=self.root)` — ユーザー通知（行 246-250）
- `return` — OCRDialog を開かずに早期終了（行 251）

裸 except なし（`except ValueError as e:` のみ）。

#### lang.py の ocr_provider_unsupported 確認

- `LANG["ja"]["ocr_provider_unsupported"]`（lang.py:288-291）: `"未対応の OCR プロバイダが設定されています: {name}\n設定を確認してください。"` — 存在確認・{name} format 可能
- `LANG["en"]["ocr_provider_unsupported"]`（lang.py:616-618）: `"Unsupported OCR provider configured: {name}\nPlease check your settings."` — 存在確認・{name} format 可能

日英両辞書に揃っている。

### 必須アーティファクト

| アーティファクト | 期待内容 | ステータス | 詳細 |
|----------------|---------|-----------|------|
| `pagefolio/ocr_providers.py` | OCRProvider / OCRAPIKeyError / LMStudioProvider | VERIFIED | 193行。`class OCRProvider(abc.ABC)` / `class OCRAPIKeyError(RuntimeError)` / `class LMStudioProvider(OCRProvider)` が存在。fitz / tkinter の import なし。 |
| `pagefolio/ocr.py` | run_parallel / has_embedded_text / build_provider / _start_ocr（CR-01 保護済み） | VERIFIED | run_parallel（83行）/ has_embedded_text（59行）/ build_provider（179行）/ `from tkinter import messagebox`（9行）/ _start_ocr の try/except ValueError（241-251行）が存在。 |
| `pagefolio/ocr_dialog.py` | _on_run が UI live 値で self.provider を再生成（CR-02 修正済み） | VERIFIED | `_on_run`（433-494行）に model_var / max_tokens_var / temperature_var の読み取りと LMStudioProvider の再生成が存在。`_render_next_page()` 呼び出し前に完了。 |
| `pagefolio/lang.py` | ocr_provider_unsupported（日英）/ ocr_text_skip_notice（日英） | VERIFIED | ja:288-291行 / en:616-618行 に `ocr_provider_unsupported`（{name} プレースホルダ付き）が存在。`ocr_text_skip_notice` も前回から維持。 |
| `pagefolio/settings.py` | ocr_provider デフォルト "off" | VERIFIED | 前回から変更なし。 |
| `tests/test_ocr_providers.py` | OCRProvider / LMStudioProvider テスト群 | VERIFIED | 231 テスト全通過（pytest -q での確認を orchestrator が報告）。 |

### キーリンク検証

| From | To | Via | ステータス | 詳細 |
|------|----|-----|-----------|------|
| `ocr_dialog.py _on_run` | `LMStudioProvider` | url_var/model_var/max_tokens_var/temperature_var を読み取り self.provider を再生成 | WIRED | 行 481-489 で `from pagefolio.ocr_providers import LMStudioProvider` し `self.provider = LMStudioProvider(...)` を再生成 |
| `ocr_dialog.py _worker` | `run_parallel` | `run_parallel(self.provider, ...)` — _on_run で再生成済み provider を使う | WIRED | 行 569-577 で `run_parallel(self.provider, ...)` を呼び出し。再生成後の provider が使われる |
| `ocr.py _start_ocr` | `build_provider`（ValueError 防護） | try/except ValueError + messagebox.showerror + return | WIRED | 行 241-251 で保護済み。未対応プロバイダ名では Tkinter コールバックへ例外が素通りしない |
| `ocr.py build_provider` | `LMStudioProvider` | ocr_provider 設定値に基づくファクトリ生成 | WIRED | 前回から変更なし |
| `ocr.py _start_ocr` | `OCRDialog(provider=...)` | build_provider 結果を OCRDialog へ受け渡し | WIRED | 前回から変更なし |
| `ocr_dialog.py _render_next_page` | `has_embedded_text / page_to_png_b64` | メインスレッドで埋め込み判定 + レンダリング | WIRED | 前回から変更なし |

### データフロートレース（Level 4）

| アーティファクト | データ変数 | ソース | 実データが流れるか | ステータス |
|---------------|-----------|-------|-----------------|-----------|
| `OCRDialog._on_run → self.provider` | url / model / max_tokens / temperature | ダイアログ UI コントロール（url_var / model_var / max_tokens_var / temperature_var）の live 値 | ダイアログで変更した値が LMStudioProvider コンストラクタに渡される | FLOWING（CR-02 修正により HOLLOW → FLOWING に変化） |
| `OCRDialog._worker → run_parallel` | self.provider | _on_run で再生成済み LMStudioProvider | _on_run の再生成が _render_next_page() 呼び出し前に完了しており、_worker が起動する時点で新 provider が確定している | FLOWING |

### 行動スポットチェック

| 動作 | コマンド | 結果 | ステータス |
|------|---------|------|-----------|
| _on_run に model_var / max_tokens_var / temperature_var / LMStudioProvider が存在する | ファイル直接読み込みで行 459-489 を確認 | model_var: True, max_tokens_var: True, temperature_var: True, LMStudioProvider: True | PASS |
| _on_run の provider 再生成が _render_next_page() より前にある | コード順序確認（行 481-489 vs 行 494） | `self.provider = LMStudioProvider(...)` が行 483-489、`self._render_next_page()` が行 494 | PASS |
| _worker に fitz / get_pixmap / self.doc[ が存在しない | _worker 本体（行 545-592）を全文確認 | fitz / get_pixmap / self.doc[ の呼び出しなし | PASS |
| _start_ocr に try / except ValueError / showerror / return が存在する | ocr.py 行 241-251 を直接確認 | try（241）/ except ValueError as e（243）/ showerror（246-250）/ return（251）すべて存在 | PASS |
| ocr_provider_unsupported が lang.py の日英両辞書に存在し {name} format 可能 | lang.py 行 288-291 / 616-618 を直接確認 | ja / en 両方に存在・{name} プレースホルダ付き | PASS |
| from tkinter import messagebox が ocr.py に存在する | ocr.py 行 9 を確認 | `from tkinter import messagebox` 存在 | PASS |
| pytest 全テスト | orchestrator 報告（231 passed） | 231 passed | PASS |
| ruff check | orchestrator 報告（exit 0） | exit 0 | PASS |
| ruff format --check | orchestrator 報告（34 files formatted） | exit 0 | PASS |

### 要件カバレッジ

| 要件 ID | ソースプラン | 説明 | ステータス | 根拠 |
|---------|------------|------|-----------|------|
| OCR-PROV-01 | 04-01 | OCRProvider 抽象基底クラスを定義し共通インターフェースを持つ | SATISFIED | OCRProvider(abc.ABC) / ocr_image / list_models / default_concurrency / max_concurrency が存在。変更なし。 |
| OCR-PROV-02 | 04-01 〜 04-04 | 既存 LM Studio OCR を LMStudioProvider 実装へリファクタし後方互換を維持 | SATISFIED | CR-02 修正により、_on_run がダイアログ UI live 値（model / max_tokens / temperature）で LMStudioProvider を再生成し run_parallel に反映する。前回 PARTIAL → 今回 SATISFIED。 |
| OCR-PROV-03 | 04-02 | run_parallel() をプロバイダ非依存に一般化し、プロバイダ別並列度を受け取れるようにする | SATISFIED | run_parallel(provider, ...) が provider.ocr_image と provider.max_concurrency のみに依存。変更なし。 |
| OCR-PERF-01 | 04-03 | テキストが埋め込まれたページは page.get_text() の結果を採用し Vision API 呼び出しをスキップする | SATISFIED | has_embedded_text(page) でメインスレッド側判定し _ocr_page_indices から除外。変更なし。 |

REQUIREMENTS.md の Traceability 表では OCR-PROV-01 / OCR-PROV-02 / OCR-PROV-03 / OCR-PERF-01 すべてが Phase 4 / Status: Complete として記載されており、実装との整合が取れている。

### アンチパターン検出

| ファイル | 行 | パターン | 重大度 | 影響 |
|---------|-----|---------|--------|------|
| `pagefolio/lang.py` | 267, 593 | `ocr_progress_skip` が定義されているが ocr_dialog.py で参照されていない | INFO | デッドな辞書エントリ（IN-02）。機能への影響なし。Phase 4 スコープ内で解決不要。 |
| `pagefolio/ocr.py` | 88 | `run_parallel` の `timeout` 引数が受け取られるが使われない | INFO | デッドパラメータ（IN-03）。呼び出し側に誤った期待を持たせる可能性。Phase 4 スコープ内で解決不要。 |

TBD / FIXME / XXX マーカー: 変更対象ファイル（ocr_dialog.py / ocr.py / lang.py）全件で 0 件。ブロッカーなし。

### 人手検証が必要な項目

#### 1. ダイアログでのモデル変更反映確認

**テスト:** LM Studio を起動した状態でモデル一覧を取得し、ダイアログで別のモデルを選択して「読み取り実行」を押す
**期待値:** LM Studio のログで実際に送信された `model` フィールドがダイアログで選択したモデル名になっている
**人手が必要な理由:** HTTP リクエストの内容確認は実際の LM Studio サーバへの接続が必要

#### 2. タイムアウト表示と実挙動の一致確認

**テスト:** タイムアウトを意図的に短い値（例: 10秒）に変更し、応答の遅い LM Studio に対して OCR を実行する
**期待値:** 表示されるタイムアウトエラーメッセージの秒数が実際に待機した秒数と一致する
**人手が必要な理由:** 実際の HTTP タイムアウト挙動は実環境での動作確認が必要

## ギャップまとめ

**再検証結果:** 前回の 2 件のギャップ（CR-02 / CR-01）はいずれも完全に修正されている。

- **CR-02（前回 BLOCKER）:** `_on_run` が `model_var` / `max_tokens_var` / `temperature_var` / `url_var` の live 値を読み取り、`_render_next_page()` 呼び出し前に `self.provider` を `LMStudioProvider` として再生成するよう修正済み。ダイアログ UI の変更が `run_parallel` に確実に反映される。SC-1 の後方互換が完全に復元された。
- **CR-01（前回 WARNING）:** `_start_ocr` 内の `build_provider` 呼び出しが `try/except ValueError as e:` で保護され、未対応プロバイダ設定値（例: `"claude"`）では `messagebox.showerror` でユーザーに通知して `return` するよう修正済み。Tkinter コールバックへの ValueError 素通りが解消された。

**残存する人手検証:** 自動検証不可の項目（実 LM Studio 接続での HTTP リクエスト内容確認・タイムアウト挙動確認）が 2 件残存する。これらはコードレベルでの証拠は十分であり、実環境確認のためのものである。

---

_検証日時: 2026-06-06_
_検証者: Claude (gsd-verifier)_
